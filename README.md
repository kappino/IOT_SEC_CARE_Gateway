# IOT_SEC_CARE_Gateway

## TLS Certificate Setup (Python Client + ESP32 Client)

This project uses mutual TLS (mTLS) with:
- one CA (`ca-cert.pem`)
- one server certificate for Mosquitto (`server-cert.pem`, `server-key.pem`)
- two client certificates:
  - Python bridge (`python-client-cert.pem`, `python-client-key.pem`)
  - ESP32 firmware (`esp32-client-cert.pem`, `esp32-client-key.pem`)

## 1) Create certificates

Run in WSL:

```bash
mkdir -p /home/enzo/certs_creator/test
cd /home/enzo/certs_creator/test
```

### 1.1 Create CA

```bash
openssl genrsa -out ca-key.pem 2048
openssl req -x509 -new -nodes -key ca-key.pem -sha256 -days 3650 -out ca-cert.pem
```

### 1.2 Create server cert (with IP SAN)

```bash
cat > server-ext.cnf << 'EOF'
subjectAltName=IP:192.168.137.1,DNS:192.168.137.1
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
EOF

openssl genrsa -out server-key.pem 2048
openssl req -new -key server-key.pem -out server.csr
openssl x509 -req -in server.csr -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out server-cert.pem -days 365 -sha256 \
  -extfile server-ext.cnf
```

### 1.3 Create client certs (Python + ESP32)

```bash
cat > client-ext.cnf << 'EOF'
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=clientAuth
EOF

# Python client
openssl genrsa -out python-client-key.pem 2048
openssl req -new -key python-client-key.pem -out python-client.csr \
  -subj "/C=IT/ST=Italy/O=CARE/CN=python-client"
openssl x509 -req -in python-client.csr -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out python-client-cert.pem -days 365 -sha256 \
  -extfile client-ext.cnf

# ESP32 client
openssl genrsa -out esp32-client-key.pem 2048
openssl req -new -key esp32-client-key.pem -out esp32-client.csr \
  -subj "/C=IT/ST=Italy/O=CARE/CN=esp32-client"
openssl x509 -req -in esp32-client.csr -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out esp32-client-cert.pem -days 365 -sha256 \
  -extfile client-ext.cnf
```

Generate RSA key format for ESP32 compatibility:

```bash
openssl rsa -traditional -in esp32-client-key.pem -out esp32-client-key-rsa.pem
```

## 2) Verify certificates

```bash
openssl verify -CAfile ca-cert.pem server-cert.pem
openssl verify -CAfile ca-cert.pem python-client-cert.pem
openssl verify -CAfile ca-cert.pem esp32-client-cert.pem
openssl x509 -in server-cert.pem -noout -ext subjectAltName
```

Expected:
- all `verify` commands return `OK`
- `server-cert.pem` contains `IP Address:192.168.137.1`

## 3) Update Mosquitto certs

Copy into the Mosquitto cert folder (example path):

```bash
cp server-cert.pem /mnt/c/Progetti/CARE_Lab/mosquitto/config/certs/server-cert.pem
cp server-key.pem /mnt/c/Progetti/CARE_Lab/mosquitto/config/certs/server-key.pem
cp ca-cert.pem /mnt/c/Progetti/CARE_Lab/mosquitto/config/certs/ca-cert.pem
```

Restart broker:

```bash
docker restart care_broker
```

## 4) Backend (Python bridge) config

`backend/config.py` must point to:
- `CA_CERT -> ca-cert.pem`
- `CLIENT_CERT -> python-client-cert.pem`
- `CLIENT_KEY -> python-client-key.pem`

## 5) Firmware (ESP32) certs

`firmware/src/secrets.cpp` must embed:
- `ca_cert_pem` from `ca-cert.pem`
- `client_cert_pem` from `esp32-client-cert.pem`
- `client_key_pem` from `esp32-client-key-rsa.pem`

Then flash clean:

```bash
pio run -t clean
pio run -t upload
```

## 6) Quick runtime checks

- Backend logs should show MQTT connected and subscribed.
- Mosquitto logs should show:
  - `u'python-client'` for bridge
  - `u'esp32-client'` for firmware

## 7) Common errors

- `CERTIFICATE_VERIFY_FAILED` / IP mismatch:
  - server cert missing SAN with the broker IP.
- ESP32 `lastError=-9984`:
  - wrong CA/cert/key in `secrets.cpp`, or stale firmware flash.
- ESP32 `PADLOCK - Input data should be aligned`:
  - use `esp32-client-key-rsa.pem` (`BEGIN RSA PRIVATE KEY`).
- Mosquitto `not authorised` with `use_identity_as_username true`:
  - client certificate must include `CN=...`.

## 8) Quick IP change guide

If hotspot/router IP changes, you usually do **not** need to regenerate CA or client certs.
Regenerate only the **server certificate** with the new IP in SAN.

Example new IP: `192.168.55.1`

### 8.1 Regenerate server cert only

```bash
cd /home/enzo/certs_creator/test

cat > server-ext.cnf << 'EOF'
subjectAltName=IP:192.168.55.1,DNS:192.168.55.1
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
EOF

openssl genrsa -out server-key.pem 2048
openssl req -new -key server-key.pem -out server.csr
openssl x509 -req -in server.csr -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out server-cert.pem -days 365 -sha256 \
  -extfile server-ext.cnf

openssl verify -CAfile ca-cert.pem server-cert.pem
openssl x509 -in server-cert.pem -noout -ext subjectAltName
```

### 8.2 Deploy to broker and restart

```bash
cp server-cert.pem /mnt/c/Progetti/CARE_Lab/mosquitto/config/certs/server-cert.pem
cp server-key.pem /mnt/c/Progetti/CARE_Lab/mosquitto/config/certs/server-key.pem
docker restart care_broker
```

### 8.3 Update app endpoints

- Backend: set `MQTT_BROKER` to new IP (or export env var).
- ESP32: set `MQTT_SERVER` in `firmware/src/secrets.cpp`, then reflash:

```bash
pio run -t clean
pio run -t upload
```

### 8.4 What does NOT change

- `ca-cert.pem`
- `python-client-cert.pem` / `python-client-key.pem`
- `esp32-client-cert.pem` / `esp32-client-key*.pem`
