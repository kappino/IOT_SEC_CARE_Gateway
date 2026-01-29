#ifndef SECRETS_H
#define SECRETS_H

// --- WIFI ---
const char* WIFI_SSID = "YOUR_SSID_HERE";
const char* WIFI_PASS = "YOUR_PASSWORD_HERE";

// --- MQTT ---
const char* MQTT_SERVER = "192.168.1.100";
const int MQTT_PORT = 8883;

// --- CERTIFICATI ---
const char* ca_cert_pem = R"EOF(
-----BEGIN CERTIFICATE-----
... PASTE YOUR CA CERT HERE ...
-----END CERTIFICATE-----
)EOF";

const char* client_cert_pem = R"EOF(
-----BEGIN CERTIFICATE-----
... PASTE YOUR CLIENT CERT HERE ...
-----END CERTIFICATE-----
)EOF";

const char* client_key_pem = R"EOF(
-----BEGIN RSA PRIVATE KEY-----
... PASTE YOUR PRIVATE KEY HERE ...
-----END RSA PRIVATE KEY-----
)EOF";

#endif