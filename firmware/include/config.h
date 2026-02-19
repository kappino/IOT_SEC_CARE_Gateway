#pragma once

// BLE
#define BLE_DEVICE_NAME         "CARE_BLE_Gateway"
#define SERVICE_UUID            "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID     "beb5483e-36e1-4688-b7f5-ea07361b26a8"

// Security
#define DEVICE_LIMIT            3
#define MUTEX_WAIT_TICKS        10

// MQTT 
#define MQTT_RECONNECT_INTERVAL_MS  5000
#define MQTT_CLIENT_ID_PREFIX       "CARE-GW-"
#define MQTT_TOPIC_DATA             "care/gateway/data"

// LED
#define INTERNAL_LED            2
#define LED_BLINK_MS            50