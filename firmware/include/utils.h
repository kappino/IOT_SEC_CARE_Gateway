#pragma once
#include <Arduino.h>

void wifi_connectAndSyncTime(const char* ssid, const char* password);
void led_blink(uint8_t pin, uint16_t durationMs);