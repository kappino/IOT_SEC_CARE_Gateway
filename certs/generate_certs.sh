#!/usr/bin/env bash
# ==============================================================================
# Private Offline PKI Setup for IoT Zero-Trust Architecture
# Generates Root CA, Server Certificate (with IP SAN), and Client Certificates.
# ==============================================================================

set -euo pipefail

BROKER_IP="${1:-127.0.0.1}"
CERTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[+] Generating PKI certificates in: ${CERTS_DIR}"
echo "[+] Target MQTT Broker IP / SAN:   ${BROKER_IP}"

cd "${CERTS_DIR}"

# 1. Root Certificate Authority (CA)
echo "[1/4] Generating Private Root CA (4096-bit RSA)..."
openssl genrsa -out ca-key.pem 4096
openssl req -x509 -new -nodes -key ca-key.pem -sha256 -days 3650 -out ca-cert.pem \
  -subj "/C=IT/ST=Campania/O=CARE-Security/CN=CARE-Root-CA"

# 2. Server Certificate (Broker Mosquitto)
echo "[2/4] Generating Server Certificate with IP SAN..."
cat > server-ext.cnf << EOF
subjectAltName=IP:${BROKER_IP},DNS:localhost
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
EOF

openssl genrsa -out server-key.pem 2048
openssl req -new -key server-key.pem -out server.csr \
  -subj "/C=IT/ST=Campania/O=CARE-Security/CN=care-mqtt-broker"
openssl x509 -req -in server.csr -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out server-cert.pem -days 365 -sha256 \
  -extfile server-ext.cnf
rm server.csr server-ext.cnf

# 3. Python Backend Client Certificate
echo "[3/4] Generating Python Bridge Client Certificate..."
cat > client-ext.cnf << 'EOF'
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=clientAuth
EOF

openssl genrsa -out python-client-key.pem 2048
openssl req -new -key python-client-key.pem -out python-client.csr \
  -subj "/C=IT/ST=Campania/O=CARE-Security/CN=python-client"
openssl x509 -req -in python-client.csr -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out python-client-cert.pem -days 365 -sha256 \
  -extfile client-ext.cnf
rm python-client.csr

# 4. ESP32 Edge Device Client Certificate
echo "[4/4] Generating ESP32 Client Certificate and RSA Traditional Key..."
openssl genrsa -out esp32-client-key.pem 2048
openssl req -new -key esp32-client-key.pem -out esp32-client.csr \
  -subj "/C=IT/ST=Campania/O=CARE-Security/CN=esp32-client"
openssl x509 -req -in esp32-client.csr -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out esp32-client-cert.pem -days 365 -sha256 \
  -extfile client-ext.cnf
rm esp32-client.csr client-ext.cnf

# mbedTLS alignment requirement: traditional RSA format without password
openssl rsa -traditional -in esp32-client-key.pem -out esp32-client-key-rsa.pem

echo "[✓] PKI generation complete! Verifying chain:"
openssl verify -CAfile ca-cert.pem server-cert.pem
openssl verify -CAfile ca-cert.pem python-client-cert.pem
openssl verify -CAfile ca-cert.pem esp32-client-cert.pem
echo "[✓] All certificates verified successfully against Root CA."
