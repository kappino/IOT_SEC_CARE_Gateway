# Secure-by-Design IoT Healthcare Architecture
### Zero-Trust mTLS Hardening & Blockchain-Anchored Auditability

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Security: mTLS v1.3](https://img.shields.io/badge/Security-mTLS_v1.3_%7C_Zero--Trust-success)](https://en.wikipedia.org/wiki/Mutual_authentication)
[![Platform: ESP32](https://img.shields.io/badge/Hardware-ESP32_%7C_mbedTLS-orange)](https://www.espressif.com/)
[![Blockchain: Solidity](https://img.shields.io/badge/Blockchain-Solidity_%7C_EVM-363636?logo=solidity)](https://soliditylang.org/)
[![Container: Docker](https://img.shields.io/badge/Container-Docker_%7C_Mosquitto-2496ed?logo=docker)](https://mosquitto.org/)

An end-to-end, defense-in-depth security architecture designed to protect sensitive biomedical IoT telemetry against **Device Impersonation**, **MAC Spoofing**, **Man-in-the-Middle (MitM)**, and **Unauthorized Data Tampering**.

Developed in collaboration with research activities surrounding assistive robotic frameworks (PNRR **Age-IT**), this repository provides a production-grade implementation of hardware-enforced **Mutual TLS (mTLS v1.3)**, source-level **HMAC-SHA256 signatures**, and **Ethereum Smart Contract notarization** for GDPR-compliant non-repudiation.

---

## 🏛️ Architectural Overview

```
 +-----------------------------------------------------------------------------------+
 | 1. EDGE LAYER (Biomedical Wearable & Ingestion)                                  |
 |                                                                                   |
 |  [ Medical Sensor ]  ---- BLE Advertisements ---->  [ ESP32 Security Gateway ]    |
 |  (Pulse Oximeter)    (Payload + HMAC-SHA256 Key)     (mbedTLS Crypto Core)        |
 +-----------------------------------------------------------------------------------+
                                         │
                               mTLS v1.3 Encrypted Pipe
                       (Bidirectional X.509 Certificate Validation)
                                         ▼
 +-----------------------------------------------------------------------------------+
 | 2. TRANSPORT & INGESTION LAYER (Zero-Trust Broker)                                |
 |                                                                                   |
 |  [ Docker Mosquitto Broker ] <====== Granular ACL Enforced ======> [ Python Ingest]|
 |  - Force clientAuth                                                 (Bridge Core) |
 |  - Map Common Name (CN) to MQTT Identity                                          |
 +-----------------------------------------------------------------------------------+
                                         │
                                         ▼
 +-----------------------------------------------------------------------------------+
 | 3. PERSISTENCE & DISTRIBUTED TRUST LAYER (Auditability & Non-Repudiation)         |
 |                                                                                   |
 |        ┌──────────────────────────────┴──────────────────────────────┐            |
 |        ▼                                                             ▼            |
 |  [ Local Medical Data Lake ]                            [ Ethereum EVM / Ganache ]|
 |  (Encrypted SQLite Storage)                             (HealthNotary.sol)        |
 |  Raw vitals, metadata, timestamp                        SHA-256 Digest & DeviceID |
 |                                                         *Zero Plaintext PII*      |
 +-----------------------------------------------------------------------------------+
```

---

## 🎯 Threat Model & Attack Simulation (PoC)

In standard e-health architectures, gateway hubs blindly trust BLE sensors using static MAC address filtering.

* **Vulnerability Demonstrated:** Using an off-the-shelf ESP32 board (*"Evil ESP32"*), we successfully spoofed the public MAC address of a commercial pulse oximeter (Jumper 500F) and transmitted forged vitals simulating cardiac arrest (180 BPM) that were naively ingested by unhardened gateways.
* **Countermeasures Deployed in this Architecture:**
  1. **Source Authentication:** Payloads lacking valid cryptographic **HMAC-SHA256 signatures** calculated with a pre-shared device key are dropped at the edge before cloud dispatch.
  2. **Zero-Trust Mutual TLS:** Rogue devices attempting to connect to the broker are rejected during the TLS handshake due to the absence of a signed X.509 client certificate.
  3. **Access Control Lists (ACL):** Even compromised clients cannot access unauthorized topics; permissions are strictly mapped to the Common Name (CN) verified by the broker.
  4. **Blockchain Notarization:** Database administrators or malicious insiders cannot alter historical telemetry undetected; any record's hash must match the immutable on-chain fingerprint recorded in `HealthNotary.sol`.

---

## 🛡️ Security Verification Matrix

| Threat Vector | Attack Scenario | Traditional IoT Gateway | Our Hardened Architecture |
| :--- | :--- | :---: | :---: |
| **BLE MAC Spoofing** | Rogue board clones sensor MAC | ❌ **Compromised** (Ingested) | ✅ **Blocked** (Invalid HMAC signature dropped) |
| **Network Sniffing** | Wireshark promiscuous capture | ❌ **Plaintext Leaked** | ✅ **Blocked** (mTLS v1.3 AES-GCM encrypted) |
| **Rogue Broker MitM** | Attacker redirects DNS/IP | ❌ **Compromised** | ✅ **Blocked** (Broker cert verified with IP SAN) |
| **Client Impersonation** | Unauthorized MQTT client injects data | ❌ **Compromised** | ✅ **Blocked** (Dropped at handshake: no clientAuth) |
| **Database Tampering** | Malicious DB update / Ransomware | ❌ **Undetected** | ✅ **Detected** (On-chain hash audit fails) |

---

## 📜 Smart Contract: `HealthNotary.sol`

The notarization layer runs as an EVM smart contract (`blockchain/HealthNotary.sol`) optimized for low gas consumption and GDPR compliance:

* **Zero Plaintext PII:** Patient identifiers and health parameters are **never stored on-chain**. Only the `bytes32` cryptographic digest (`SHA-256(payload)`) and anonymized `bytes32 deviceId` are recorded.
* **Non-Repudiation & Timestamps:** Transactions automatically seal the block timestamp and the cryptographic identity of the authorized `notarizer` account.
* **Anti-Collision Guard:** Custom error `DuplicateDataHash` reverts attempts to re-notarize identical records or replay attack packets.
* **Role-Based Access Control (RBAC):** Restricts record creation strictly to verified gateway ingest bridges using custom `Unauthorized` errors.

---

## 🚀 Quick Start Guide

### Prerequisites
* **Docker & Docker Compose**
* **Python 3.10+** (with `pip`)
* **PlatformIO CLI / VSCode Extension** (for ESP32 firmware)
* **Local Ethereum Node** ([Ganache](https://trufflesuite.com/ganache/) or Hardhat)

---

### 1. Generate Private PKI Hierarchy
Execute the included automated certificate provisioning script:

```bash
chmod +x certs/generate_certs.sh
./certs/generate_certs.sh 127.0.0.1
```

This creates:
* `certs/ca-cert.pem` (4096-bit Offline Root CA)
* `certs/server-cert.pem` & `server-key.pem` (Broker certificate with IP SAN)
* `certs/python-client-cert.pem` & `python-client-key.pem` (Backend client)
* `certs/esp32-client-cert.pem` & `esp32-client-key-rsa.pem` (ESP32 mbedTLS RSA key)

---

### 2. Start the Hardened MQTT Broker
Launch the preconfigured Eclipse Mosquitto container with mTLS v1.3:

```bash
cd docker
docker compose up -d
```

---

### 3. Configure and Run Backend Bridge & Auditor

1. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
2. Install Python dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Start the asynchronous ingestion bridge:
   ```bash
   python backend/main.py
   ```
4. Run the interactive Blockchain Integrity Auditor:
   ```bash
   python utils/audit.py
   ```

---

### 4. Deploy ESP32 Firmware
1. Copy the configuration template:
   ```bash
   cp firmware/src/secrets.cpp.example firmware/src/secrets.cpp
   ```
2. Insert your WiFi credentials and paste the generated PEM certificates into `firmware/src/secrets.cpp`.
3. Build and upload using PlatformIO:
   ```bash
   cd firmware
   pio run --target upload
   ```

---

## 📁 Repository Structure

```
├── backend/                  # Asynchronous Ingestion & Processing Bridge
│   ├── blockchain.py         # Web3 Ethereum Notarization Provider
│   ├── bridge.py             # Multithreaded MQTT Client with SSL Context
│   ├── config.py             # Environment-aware Configuration Loader
│   ├── database.py           # SQLite Data Lake Persistence Manager
│   └── main.py               # Application Entrypoint
├── blockchain/               # Smart Contracts
│   └── HealthNotary.sol      # Solidity Notarization Contract (EVM)
├── certs/                    # PKI Utilities
│   └── generate_certs.sh     # Automated OpenSSL PKI Generation Pipeline
├── docker/                   # Deployment Infrastructure
│   ├── docker-compose.yml    # Containerized Mosquitto Broker
│   ├── mosquitto.conf        # Zero-Trust mTLS v1.3 Hardened Broker Config
│   └── mosquitto.acl         # Principle of Least Privilege Access Control List
├── firmware/                 # ESP32 Microcontroller Firmware (PlatformIO)
│   ├── include/              # Header Definitions & Configuration
│   └── src/                  # BLE Ingestion, HMAC Verification & mbedTLS MQTT
├── utils/                    # Verification & Security Audit Tools
│   ├── audit.py              # Interactive CLI for Database vs Blockchain Audit
│   ├── ble_script.py         # BLE Peripheral Telemetry Simulator
│   └── permission_test.py    # MQTT ACL Permission Unit Tests
├── .env.example              # Environment Configuration Template
└── README.md
```

---

## 📄 License
This project is licensed under the **Apache 2.0 License** - see the [LICENSE](LICENSE) file for details.
