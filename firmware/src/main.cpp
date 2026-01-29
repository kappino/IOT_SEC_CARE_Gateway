/*
 * PROJECT: Secure IoT Gateway for CARE Project
 * BASED ON: Industrial Shields MQTT over TLS Architecture
 * ADAPTED FOR: ESP32 Native Hardware Encryption
 */

 #include <WiFi.h>
 #include <WiFiClientSecure.h>
 #include <PubSubClient.h>

 #include "secrets.h"

#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

WiFiClientSecure espClient;
PubSubClient client(espClient);

const char* topic_data = "care/gateway/data";

void reconnect() {
    while (!client.connected()) {
        Serial.print("[MQTT] Tentativo di connessione TLS...");
        String clientId = "ESP32-Gateway-";
        clientId += String(random(0xffff),HEX);

        if (client.connect(clientId.c_str())) {
            Serial.println("Connesso!");
        } else {
            Serial.print("fallito, rc=");
            Serial.print(client.state());
            Serial.println(" riprovo in 5s");
            
            char err_buff[100];
            espClient.lastError(err_buff,100);
            Serial.printf("[TLS Error] %s\n",err_buff);

            delay(5000);
        }
    }
}


void setup() {
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
    Serial.begin(115200);

    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.print("Connessione WiFi");
    while(WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi Connesso");

    espClient.setCACert(ca_cert_pem);
    espClient.setCertificate(client_cert_pem);
    espClient.setPrivateKey(client_key_pem);

    client.setServer(MQTT_SERVER,MQTT_PORT);

}

void loop() {
    if (!client.connected()) reconnect();

    client.loop();

    // Esempio: Invio dati ogni 5 secondi (simulazione)
    static unsigned long lastMsg = 0;
    if (millis() - lastMsg > 5000) {
        lastMsg = millis();
        
        String payload = "BPM: " + String(random(60, 100));
        Serial.print("[TX] ");
        Serial.println(payload);
        
        client.publish(topic_data, payload.c_str());
    }
}