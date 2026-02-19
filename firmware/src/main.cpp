/*
 * PROJECT: Secure IoT Gateway — CARE Project
 * TARGET:  ESP32 (Server) → TicWatch E3 (Client)
 *
 * Flusso: BLE Write → verifyHMAC() → MQTT publish
 */

#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

#include "config.h"
#include "secrets.h"
#include "utils.h"
#include "ble_handler.h"
#include "mqtt_handler.h"
#include "security.h"

// Shared state

static SemaphoreHandle_t s_mutex;
static String            s_pendingPayload;
static volatile bool     s_newData = false;


void setup() {
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // Disabilita brownout detector
    Serial.begin(115200);
    pinMode(INTERNAL_LED, OUTPUT);

    s_mutex = xSemaphoreCreateMutex();

    wifi_connectAndSyncTime(WIFI_SSID, WIFI_PASS);
    mqtt_init(MQTT_SERVER, MQTT_PORT);
    ble_init(s_mutex, &s_pendingPayload, &s_newData);

    Serial.println("[SYS] Gateway ready.");
}


void loop() {
    mqtt_handle();

    // Pop atomico del messaggio BLE pendente
    String payload;
    bool   hasData = false;

    if (xSemaphoreTake(s_mutex, (TickType_t)MUTEX_WAIT_TICKS) == pdTRUE) {
        if (s_newData) {
            payload   = s_pendingPayload;
            s_newData = false;
            hasData   = true;
        }
        xSemaphoreGive(s_mutex);
    }

    if (!hasData) { delay(10); return; }

    Serial.printf("[RX] %d bytes\n", payload.length());

    VerifyResult result = verifyHMAC(payload);

    if (result == VerifyResult::OK) {
        Serial.println("[SEC] HMAC valido — forwarding");
        if (mqtt_publish(MQTT_TOPIC_DATA, payload.c_str())) {
            led_blink(INTERNAL_LED, LED_BLINK_MS);
        } else {
            Serial.println("[MQTT] Publish fallito (broker non raggiungibile?)");
        }
    } else {
        Serial.printf("[SEC] Pacchetto rifiutato: %s\n", verifyResultToString(result));
    }
}