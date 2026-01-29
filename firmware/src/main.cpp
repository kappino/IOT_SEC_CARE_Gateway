/*
 * PROJECT: Secure IoT Gateway for Healthcare
 * BASED ON: Industrial Shields MQTT over TLS Architecture
 * ADAPTED FOR: ESP32 Native Hardware Encryption
 */

 #include <WiFi.h>
 #include <WiFiClientSecure.h>
 #include <PubSubClient.h>

 #include "ca_cert.h"
 #include "client_cert.h"
 #include "client_key.h"

 