#pragma once
#include <Arduino.h>

void mqtt_init(const char* server, int port);
void mqtt_handle();
bool mqtt_publish(const char* topic, const char* payload);
bool mqtt_isConnected();