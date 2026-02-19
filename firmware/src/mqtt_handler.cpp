#include "mqtt_handler.h"
#include "config.h"
#include "secrets.h"

#include <WiFiClientSecure.h>
#include <PubSubClient.h>

static WiFiClientSecure s_wifiClient;
static PubSubClient     s_mqtt(s_wifiClient);
static unsigned long    s_lastAttemptMs = 0;

//Private

static void attemptConnect() {
    s_wifiClient.setCACert(ca_cert_pem);
    s_wifiClient.setCertificate(client_cert_pem);
    s_wifiClient.setPrivateKey(client_key_pem);
    s_wifiClient.setHandshakeTimeout(20);

    String clientId = "CARE-GW-TEST";
    Serial.printf("[MQTT] Connecting as %s... ", clientId.c_str());

    if (s_mqtt.connect(clientId.c_str())) {
        Serial.println("OK");
    } else {
        Serial.printf("FAIL (rc=%d)\n", s_mqtt.state());
        char errBuf[160];
        int err = s_wifiClient.lastError(errBuf, sizeof(errBuf));
        Serial.printf("[MQTT][TLS] lastError=%d detail=%s\n", err, errBuf);
    }
}

//Public API

void mqtt_init(const char* server, int port) {
    s_mqtt.setServer(server, port);
}

void mqtt_handle() {
    if (s_mqtt.connected()) {
        s_mqtt.loop();
        return;
    }
    unsigned long now = millis();
    if (now - s_lastAttemptMs >= MQTT_RECONNECT_INTERVAL_MS) {
        s_lastAttemptMs = now;
        attemptConnect();
    }
}

bool mqtt_publish(const char* topic, const char* payload) {
    if (!s_mqtt.connected()) return false;
    return s_mqtt.publish(topic, payload);
}

bool mqtt_isConnected() { return s_mqtt.connected(); }
