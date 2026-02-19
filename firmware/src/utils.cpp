#include "utils.h"

#include <WiFi.h>
#include "time.h"

void wifi_connectAndSyncTime(const char* ssid, const char* password) {
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    delay(100);

    Serial.printf("[WiFi] Connecting to %s", ssid);
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\n[WiFi] Connected — IP: %s\n", WiFi.localIP().toString().c_str());

    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    Serial.print("[NTP]  Syncing");
    time_t now = time(nullptr);
    while (now < 8 * 3600 * 2) {
        delay(500);
        Serial.print(".");
        now = time(nullptr);
    }
    struct tm ti;
    gmtime_r(&now, &ti);
    Serial.printf("\n[NTP]  Time: %s", asctime(&ti));
}

void led_blink(uint8_t pin, uint16_t durationMs) {
    digitalWrite(pin, HIGH);
    delay(durationMs);
    digitalWrite(pin, LOW);
}