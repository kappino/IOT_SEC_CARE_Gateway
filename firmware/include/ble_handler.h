#pragma once
#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>

void ble_init(SemaphoreHandle_t mutex, String* msgBuffer, volatile bool* flagNewData);
bool ble_isConnected();