/*
 * PROJECT: Secure IoT Gateway for CARE Project
 * BASED ON: Industrial Shields MQTT over TLS Architecture
 * ADAPTED FOR: ESP32 Native Hardware Encryption
 */

 #include <WiFi.h>
 #include <WiFiClientSecure.h>
 #include <PubSubClient.h>

#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include <esp_task_wdt.h>
#include <ArduinoJson.h>
#include "mbedtls/md.h"

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include "secrets.h"

// --- CONFIG ---
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

#define PAIRING_WINDOW_MS 60000

#define INTERNAL_LED 33 
#define EXTERNAL_LED 4

const char* topic_data = "care/gateway/data";

// --- GLOBALS ---

WiFiClientSecure espClient;
PubSubClient mqtt(espClient);

BLEServer* pServer;
BLECharacteristic* pCharacteristic;

int connectionCount = 0;
const int MAX_CONNECTIONS = 3;

struct DeviceState {
    String id;
    long lastTs;
};
static DeviceState devices[5];
static int deviceCount = 0;

unsigned long lastMqttAttemp = 0;

void pulseFlash() {
    ledcWrite(0, 2); delay(50); ledcWrite(0, 0);
}


bool verifyHMAC(const String& payload) {

    StaticJsonDocument<256> doc;
    if (deserializeJson(doc, payload)) return false;

    String id       = doc["id"].as<String>();
    long ts         = doc["ts"];
    String value    = doc["value"].as<String>();
    const char* sig = doc["sig"];

    if (!id || !sig) return false;

    DeviceState* dev = nullptr;
    for (int i=0;i<deviceCount;i++) {
        if (devices[i].id == id) {
            dev = &devices[i];
            break;
        }
    }

    if(!dev) {
        if (deviceCount >= 3) return false;
        devices[deviceCount++] = {String(id),0};
        dev = &devices[deviceCount -1];
    }

    if (ts <= dev->lastTs) {
        Serial.println("[SEC] Replay Detected");
        return false;
    }

    String data = id + String(ts) + value;

    uint8_t hmacResult[32];
    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);
    mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1);
    mbedtls_md_hmac_starts(&ctx, (const uint8_t*)HMAC_SECRET, strlen(HMAC_SECRET));
    mbedtls_md_hmac_update(&ctx, (const uint8_t*)data.c_str(), data.length());
    mbedtls_md_hmac_finish(&ctx, hmacResult);
    mbedtls_md_free(&ctx);
    char hex[65];
    for (int i = 0; i < 32; i++)
        sprintf(hex + i * 2, "%02x", hmacResult[i]);
    hex[64] = '\0';

    if (strcmp(hex, sig) == 0) {
        dev->lastTs = ts;
        return true;
    } else {
        Serial.printf("[SEC] Firma Errata!\nCalc: %s\nRx:   %s\n", hex, sig);
        return false;
    }
    return strcmp(hex, sig) == 0;
}

class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
        connectionCount++;
        Serial.printf("[BLE] Device Connected! Total: %d\n", connectionCount);      
        digitalWrite(INTERNAL_LED, LOW); 
        if (connectionCount < MAX_CONNECTIONS) pServer->startAdvertising();
    }

    void onDisconnect(BLEServer* pServer) {
        connectionCount--;
        if (connectionCount < 0) connectionCount = 0;
        Serial.printf("Client Disconnected. Total: %d\n",connectionCount);
        if (connectionCount == 0) digitalWrite(INTERNAL_LED,HIGH);
        pServer->startAdvertising();
    }
};

class MyCallbacks: public BLECharacteristicCallbacks {
    unsigned long lastReceiveTime = 0;
    
    void onWrite(BLECharacteristic* pCharacteristic) {
      String receivedMessage = pCharacteristic->getValue().c_str();
      
      if (receivedMessage.length() > 0 && millis() - lastReceiveTime > 200) {
        lastReceiveTime = millis();
        
        Serial.println("====================");
        Serial.print(" Msg: ");
        Serial.println(receivedMessage);

        if (!verifyHMAC(receivedMessage)) {
            Serial.println("[SEC] Invalid HMAC - dropped");
            return;
        }
        
        if (mqtt.connected()) {
            mqtt.publish(topic_data, receivedMessage.c_str());
            Serial.println(" [MQTT] Forwarded");
        }
        Serial.println("====================");

        pulseFlash();
      }
    }
};

void connectWiFi() {
    WiFi.begin(WIFI_SSID,WIFI_PASS);
    int retry = 0;
    while (WiFi.status() != WL_CONNECTED && retry++ < 30) {
        delay(500);
        Serial.print(".");
    }

    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("\n[WiFi] FAILED - reboot");
        ESP.restart();
    }

    Serial.println("\n[WiFi] Connected");
}

void handleMQTT() {
    if (mqtt.connected()) {
        mqtt.loop();
        return;
    }

    unsigned long now = millis();
    if (now - lastMqttAttemp > 5000) {
        lastMqttAttemp = now;
        Serial.print("[MQTT] Connecting...");
        String cid = "CARE-GW-" + String(random(0xffff), HEX);
        if (mqtt.connect(cid.c_str())) {
            Serial.println("OK");
            pulseFlash();
        } else {
            Serial.println("FAIL");
        }
    }
}

void setup() {
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
    esp_task_wdt_init(30, true); esp_task_wdt_add(NULL);
    Serial.begin(115200);

    pinMode(INTERNAL_LED, OUTPUT); digitalWrite(INTERNAL_LED, HIGH);
    ledcSetup(0, 5000, 8); ledcAttachPin(EXTERNAL_LED, 0); ledcWrite(0, 0);

    connectWiFi();

    espClient.setCACert(ca_cert_pem);
    espClient.setCertificate(client_cert_pem);
    espClient.setPrivateKey(client_key_pem);

    mqtt.setServer(MQTT_SERVER,MQTT_PORT);

    Serial.println("\nBLE Secure Server Starting...");
    BLEDevice::init("CARE_BLE_Gateway"); 
    BLEDevice::setEncryptionLevel(ESP_BLE_SEC_ENCRYPT);
    
    BLESecurity *pSecurity = new BLESecurity();
    pSecurity->setAuthenticationMode(ESP_LE_AUTH_REQ_SC_BOND);
    pSecurity->setCapability(ESP_IO_CAP_NONE); 
    pSecurity->setInitEncryptionKey(ESP_BLE_ENC_KEY_MASK | ESP_BLE_ID_KEY_MASK);

    pServer = BLEDevice::createServer(); 
    pServer->setCallbacks(new MyServerCallbacks());
    BLEService* pService = pServer->createService(SERVICE_UUID); 
    
    pCharacteristic = pService->createCharacteristic( 
        CHARACTERISTIC_UUID,
        BLECharacteristic::PROPERTY_WRITE
    );
    pCharacteristic->setAccessPermissions(ESP_GATT_PERM_WRITE_ENCRYPTED);
    pCharacteristic->setCallbacks(new MyCallbacks());
    pService->start(); 
    
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->setScanResponse(true);
    
    BLEDevice::startAdvertising();

    Serial.println("[SYS] READY - Pairing Window Open");
}

void loop() {
    esp_task_wdt_reset();
    handleMQTT();
    
    delay(20);
}