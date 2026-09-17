# Secure IoT Healthcare Architecture
### Zero-Trust mTLS v1.3 Hardening, Source HMAC Verification & EVM Notarization

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Security: mTLS v1.3](https://img.shields.io/badge/Security-mTLS_v1.3_%7C_Zero--Trust-success)](https://en.wikipedia.org/wiki/Mutual_authentication)
[![Platform: ESP32](https://img.shields.io/badge/Hardware-ESP32_%7C_mbedTLS-orange)](https://www.espressif.com/)
[![Blockchain: Solidity](https://img.shields.io/badge/Blockchain-Solidity_0.8.19_%7C_EVM-363636?logo=solidity)](https://soliditylang.org/)
[![Container: Docker](https://img.shields.io/badge/Container-Docker_%7C_Mosquitto-2496ed?logo=docker)](https://mosquitto.org/)

An end-to-end telemetry ingestion architecture for biomedical IoT edge devices, engineered to eliminate single points of compromise across the transport, processing, and persistence tiers. Developed within research on assistive robotic frameworks (PNRR **Age-IT**), this system enforces mutual identity verification, payload source authenticity, topic-level access control, and cryptographic non-repudiation.

---

## Architecture Specification

The system implements a three-tier defense model: Edge Gateway, Message Broker with Mutual TLS, and Decentralized Persistence.

```mermaid
flowchart TD
    subgraph Tier1["1. Edge Ingestion Layer"]
        BLE["BLE Peripheral<br/>(Pulse Oximeter / TicWatch E3)"]
        ESP32["ESP32 Edge Gateway<br/>(FreeRTOS + mbedTLS)"]
        BLE -->|"BLE Write<br/>[JSON Payload + HMAC-SHA256]"| ESP32
    end

    subgraph Tier2["2. Zero-Trust Transport Layer"]
        Broker["Eclipse Mosquitto 2.x<br/>(Port 8883 / TLS v1.3)"]
        ACL["Broker ACL Engine<br/>(CN-to-Username Mapping)"]
        ESP32 -->|"mTLS Client Handshake<br/>(X.509 CN: esp32-client)"| Broker
        Broker --- ACL
    end

    subgraph Tier3["3. Ingestion & Distributed Trust Layer"]
        Bridge["Python Ingestion Bridge<br/>(SSL Context + Queue Worker)"]
        DB[(Local Medical Data Lake<br/>SQLite Storage)]
        EVM["EVM Node / Ganache<br/>(HealthNotary.sol)"]

        Broker -->|"mTLS Subscribe<br/>(X.509 CN: python-client)"| Bridge
        Bridge -->|"Store Raw Telemetry + Hashes"| DB
        Bridge -->|"addRecord(deviceId, dataHash, isCritical)"| EVM
    end

    subgraph Tier4["4. Verification & Audit"]
        Auditor["Audit CLI Engine<br/>(utils/audit.py)"]
        Auditor -.->|"Compare SHA-256 Hashes"| DB
        Auditor -.->|"Verify On-Chain State"| EVM
    end
```

---

## Data Flow & Ingestion Pipeline

```mermaid
sequenceDiagram
    autonumber
    participant Sensor as BLE Peripheral
    participant Gateway as ESP32 Gateway
    participant Broker as Mosquitto (mTLS)
    participant Bridge as Python Bridge
    participant Contract as HealthNotary (EVM)
    participant DB as SQLite DB

    Sensor->>Gateway: BLE Characteristic Write (id, ts, value, sig)
    Note over Gateway: mbedTLS HMAC-SHA256 Verification
    alt Invalid HMAC Signature
        Gateway--xSensor: Drop packet (Silent discard / Error log)
    else Valid HMAC Signature
        Gateway->>Broker: MQTT PUBLISH care/gateway/data (mTLS v1.3)
        Note over Broker: Enforce TLS Client Cert + ACL (CN=esp32-client)
        Broker->>Bridge: Deliver MQTT Packet (mTLS v1.3)
        Note over Bridge: Worker Thread: Re-verify HMAC & compute SHA-256(payload)
        Bridge->>Contract: addRecord(bytes32 deviceId, bytes32 dataHash, bool critical)
        Contract-->>Bridge: Emit DataNotarized(recordId, txHash)
        Bridge->>DB: INSERT record (deviceId, payload, dataHash, txHash, status)
    end
```

---

## Threat Model & Attack Analysis

Standard healthcare gateways rely on MAC filtering for BLE peripherals and unauthenticated MQTT connections over plaintext or server-only TLS. This architecture addresses four specific attack vectors evaluated via a Proof-of-Concept (PoC) harness.

```mermaid
sequenceDiagram
    autonumber
    actor Attacker as Rogue Node / Attacker
    participant BLE_GW as ESP32 Gateway
    participant Broker as Mosquitto Broker
    participant DB as Local Database
    participant Audit as Blockchain Auditor

    rect rgb(255, 235, 235)
    Note over Attacker,BLE_GW: Vector 1: BLE MAC Address Spoofing
    Attacker->>BLE_GW: Broadcast cloned MAC with forged vitals (180 BPM)
    BLE_GW->>BLE_GW: verifyHMAC(payload, secret_key)
    BLE_GW--xAttacker: HMAC mismatch -> DROPPED at Edge
    end

    rect rgb(255, 243, 230)
    Note over Attacker,Broker: Vector 2: Rogue Broker Injection / MitM
    Attacker->>Broker: TCP Connect port 8883 (No valid client certificate)
    Broker--xAttacker: TLS Alert 42 (bad_certificate) -> Handshake Terminated
    end

    rect rgb(240, 248, 255)
    Note over Attacker,Audit: Vector 3: Insider Database Alteration
    Attacker->>DB: UPDATE records SET value=75 WHERE id=42
    Audit->>DB: Fetch record and compute local SHA-256
    Audit->>Audit: Query HealthNotary.registry(recordId)
    Audit--xAttacker: MISMATCH DETECTED (Tampering flagged)
    end
```

### Defense Matrix

| Threat Vector | Attack Mechanism | Unhardened Baseline | Implemented Defense |
| :--- | :--- | :---: | :--- |
| **BLE MAC Spoofing** | Rogue board broadcasts valid sensor MAC with forged payload | Ingested blindly | **HMAC-SHA256**: Packets without cryptographic signature signed with shared key are dropped at the FreeRTOS task level. |
| **Transport Sniffing** | Promiscuous packet capture on local LAN (Wireshark) | Plaintext readable | **TLS v1.3**: Wire traffic encrypted using ephemeral ECDHE key exchange and AES-256-GCM cipher suites. |
| **Broker Impersonation** | DNS spoofing / rogue MQTT proxy | Connected & leaked | **Server Certificate Validation**: Gateway verifies broker CA chain and IP Subject Alternative Names (SAN). |
| **Rogue Ingestion Node** | Unauthorized MQTT client publishes malicious alerts | Accepted | **Mutual TLS (mTLS)**: Broker rejects connections during TLS handshake unless a valid client cert issued by the private Root CA is presented. |
| **Privilege Escalation** | Compromised client attempts publishing to admin channels | Permitted | **Broker ACL**: Least-privilege matrix maps X.509 Common Name (`CN`) directly to topic read/write permissions. |
| **Storage Tampering** | Ransomware or privileged DBA alters SQLite telemetry history | Undetected | **EVM Notarization**: Every record is anchored by its `SHA-256` digest on-chain; `utils/audit.py` detects discrepancy. |

---

## Cryptographic & Protocol Specifications

### 1. BLE Telemetry Payload Structure

Payloads are encoded as JSON and signed using HMAC-SHA256 across `deviceId + timestamp + rawValue`:

```json
{
  "id": "OXIMETER_01",
  "ts": 1726584920,
  "value": 98.6,
  "sig": "b2f69e96f1345d24b699a756612df2f7e8a93cbdf8b3d6888497d3dfa2717013"
}
```

```
Signature Input:  "OXIMETER_01" + "1726584920" + "98.6"
Signature Output: HMAC-SHA256(Input, HMAC_SECRET)
```

### 2. X.509 Public Key Infrastructure (PKI)

The infrastructure enforces a private two-tier PKI generated via `certs/generate_certs.sh`:

* **Root CA**: 4096-bit RSA self-signed certificate (`ca-cert.pem`), 3650-day validity.
* **Broker Certificate**: 2048-bit RSA (`server-cert.pem`), signed by Root CA, with Subject Alternative Name (`IP:127.0.0.1`).
* **Gateway Client Certificate**: 2048-bit RSA (`esp32-client-cert.pem`), `CN=esp32-client`.
* **Bridge Client Certificate**: 2048-bit RSA (`python-client-cert.pem`), `CN=python-client`.

### 3. Mosquitto Access Control Lists (ACL)

Defined in `docker/mosquitto.acl`:

```
# ESP32 Gateway: Publish telemetry only
user esp32-client
topic write care/gateway/data

# Python Ingestion Bridge: Subscribe to incoming telemetry
user python-client
topic read care/gateway/data
```

---

## Smart Contract Specification (`HealthNotary.sol`)

The notarization layer runs as an EVM smart contract (`blockchain/HealthNotary.sol`) compiled with `solc 0.8.19`.

### State Storage & Memory Layout

```solidity
struct Record {
    uint256 timestamp;  // Block timestamp of notarization
    bytes32 deviceId;   // Anonymized device identifier hash
    bytes32 dataHash;   // SHA-256 digest of original raw telemetry JSON
    bool critical;      // Medical triage flag (heart rate < 50 or > 120 bpm)
}
```

### Security & Compliance Controls

* **Zero Plaintext PII (GDPR Art. 9 Compliant):** No patient health data, personal identifiers, or raw biometric measurements are stored on-chain. Only cryptographic digests (`bytes32 dataHash = sha256(payload)`) and pseudonymized IDs (`bytes32 deviceId`) are recorded.
* **Anti-Replay / Collision Check:**
  ```solidity
  if (dataHashUsed[dataHash]) revert DuplicateDataHash();
  ```
  Prevents duplicate telemetry injection or replaying intercepted packets.
* **Role-Based Access Control (RBAC):** Restricts `addRecord` execution to authorized addresses managed by the contract owner via the `onlyNotarizer` modifier.

---

## Deployment & Verification Guide

### Prerequisites
* **Docker Engine** `>= 24.0` & **Docker Compose**
* **Python** `>= 3.10`
* **PlatformIO Core** or VSCode PlatformIO extension
* **Ganache CLI / Ethereum Node**

---

### Step 1: Generate Private PKI Hierarchy

Execute the automated provisioning script to generate the Root CA and issue certificates:

```bash
chmod +x certs/generate_certs.sh
./certs/generate_certs.sh 127.0.0.1
```

Generated artifacts in `certs/`:
* `ca-cert.pem`, `ca-key.pem`
* `server-cert.pem`, `server-key.pem`
* `esp32-client-cert.pem`, `esp32-client-key-rsa.pem`
* `python-client-cert.pem`, `python-client-key.pem`

---

### Step 2: Start the Hardened MQTT Broker

Launch Eclipse Mosquitto with TLS v1.3 and certificate authentication enabled:

```bash
cd docker
docker compose up -d
```

Verify broker listener status:
```bash
docker compose logs mosquitto
# Expected output: OpenSSL support: yes, TLS 1.3 enabled, listening on port 8883
```

---

### Step 3: Configure and Run Ingestion Bridge

1. Copy and configure the environment file:
   ```bash
   cp .env.example .env
   ```

2. Install Python dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. Deploy `HealthNotary.sol` on Ganache / Local EVM node and update `CONTRACT_ADDRESS` in `.env`.

4. Start the ingestion service:
   ```bash
   python backend/main.py
   ```

---

### Step 4: Run the Integrity Audit CLI

Execute the tamper-verification engine to audit local database records against on-chain records:

```bash
python utils/audit.py
```

The auditor calculates `SHA-256` digests of local records, queries `HealthNotary.registry(recordId)` on the EVM, and reports verification status:
* `VALID`: Local hash matches on-chain fingerprint.
* `TAMPERED`: Hash mismatch indicates database alteration.
* `NOT_NOTARIZED`: Record not anchored on-chain.

---

### Step 5: Flash ESP32 Gateway Firmware

1. Initialize secrets configuration:
   ```bash
   cp firmware/src/secrets.cpp.example firmware/src/secrets.cpp
   ```

2. Paste generated `ca-cert.pem`, `esp32-client-cert.pem`, and `esp32-client-key-rsa.pem` contents into `firmware/src/secrets.cpp`.

3. Compile and flash using PlatformIO:
   ```bash
   cd firmware
   pio run --target upload
   ```

---

## Repository Layout

```
├── backend/
│   ├── blockchain.py         # Web3.py EVM interaction & transaction signing
│   ├── bridge.py             # Threaded MQTT client with SSL context & queue worker
│   ├── config.py             # Environment configuration (.env loader)
│   ├── database.py           # SQLite local persistence engine
│   ├── main.py               # Ingestion entrypoint
│   └── requirements.txt      # Python dependencies
├── blockchain/
│   └── HealthNotary.sol      # EVM smart contract (Solidity 0.8.19)
├── certs/
│   └── generate_certs.sh     # PKI generation automation script
├── docker/
│   ├── docker-compose.yml    # Mosquitto container specification
│   ├── mosquitto.conf        # TLS v1.3 & clientAuth broker configuration
│   └── mosquitto.acl         # CN-based least-privilege ACL rules
├── firmware/
│   ├── platformio.ini        # PlatformIO build configuration
│   ├── include/              # FreeRTOS task headers, config, secrets interface
│   └── src/                  # BLE GATT receiver, HMAC validation, mbedTLS MQTT
├── utils/
│   ├── audit.py              # CLI database vs blockchain integrity auditor
│   ├── ble_script.py         # BLE peripheral payload simulation script
│   └── permission_test.py    # MQTT ACL policy validation suite
├── .env.example              # Template environment variables
└── README.md
```

---

## License

This project is licensed under the [Apache 2.0 License](LICENSE).
