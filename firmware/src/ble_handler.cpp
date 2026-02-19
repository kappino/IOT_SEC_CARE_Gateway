#include "ble_handler.h"
#include "config.h"

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

//Module state

static bool               s_connected   = false;
static SemaphoreHandle_t  s_mutex       = nullptr;
static String*            s_msgBuffer   = nullptr;
static volatile bool*     s_flagNewData = nullptr;

//BLE Server callbacks

class ServerCallbacks : public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) override {
        s_connected = true;
        Serial.println("[BLE] Device connected");
    }
    void onDisconnect(BLEServer* pServer) override {
        s_connected = false;
        Serial.println("[BLE] Device disconnected — restarting advertising");
        pServer->startAdvertising();
    }
};

//BLE Characteristic callbacks
class CharCallbacks : public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic* pChar) override {
        std::string raw = pChar->getValue();
        if (raw.empty()) return;

        if (xSemaphoreTake(s_mutex, (TickType_t)MUTEX_WAIT_TICKS) == pdTRUE) {
            *s_msgBuffer   = String(raw.c_str());
            *s_flagNewData = true;
            xSemaphoreGive(s_mutex);
        } else {
            Serial.println("[BLE] Mutex timeout — packet dropped");
        }
    }
};

//Public API

void ble_init(SemaphoreHandle_t mutex, String* msgBuffer, volatile bool* flagNewData) {
    s_mutex       = mutex;
    s_msgBuffer   = msgBuffer;
    s_flagNewData = flagNewData;

    BLEDevice::init(BLE_DEVICE_NAME);

    BLESecurity* pSecurity = new BLESecurity();
    pSecurity->setAuthenticationMode(ESP_LE_AUTH_REQ_SC_BOND);
    pSecurity->setCapability(ESP_IO_CAP_NONE);
    pSecurity->setInitEncryptionKey(ESP_BLE_ENC_KEY_MASK | ESP_BLE_ID_KEY_MASK);

    BLEServer* pServer = BLEDevice::createServer();
    pServer->setCallbacks(new ServerCallbacks());

    BLEService*        pService = pServer->createService(SERVICE_UUID);
    BLECharacteristic* pChar    = pService->createCharacteristic(
        CHARACTERISTIC_UUID, BLECharacteristic::PROPERTY_WRITE
    );
    pChar->setAccessPermissions(ESP_GATT_PERM_WRITE_ENCRYPTED);
    pChar->setCallbacks(new CharCallbacks());

    pService->start();

    BLEAdvertising* pAdv = BLEDevice::getAdvertising();
    pAdv->addServiceUUID(SERVICE_UUID);
    pAdv->setScanResponse(true);
    BLEDevice::startAdvertising();

    Serial.println("[BLE] Advertising started");
}

bool ble_isConnected() { return s_connected; }