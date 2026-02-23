# IOT_SEC_CARE_Gateway: Sicurezza e PKI

Questa documentazione definisce l'architettura di sicurezza e le procedure di *hardening* crittografico per il progetto **IOT_SEC_CARE_Gateway**. 

L'infrastruttura implementa un modello **Zero-Trust** basato su **Mutual TLS (mTLS) v1.2/v1.3**, garantendo confidenzialità, integrità e *Non-Repudiation* a livello di trasporto. La validazione X.509 bidirezionale previene attacchi di tipo *Man-in-the-Middle* (MitM) e *Rogue Device Impersonation*.

### Architettura della Public Key Infrastructure (PKI)
Il sistema utilizza una CA (Certification Authority) privata offline che firma e gestisce l'intero trust crittografico:
* **1 CA Root:** `ca-cert.pem`
* **1 Server Certificate (MQTT Broker):** `server-cert.pem` (con estensione SAN per binding IP rigoroso).
* **2 Client Certificates (Endpoint Auth):**  `python-client-cert.pem` (per il Bridge Backend)
  * `esp32-client-cert.pem` (per il Firmware Edge)

---

## Indice
1. [Creazione dei Certificati (PKI Setup)](#1-creazione-dei-certificati-pki-setup)
2. [Verifica Crittografica](#2-verifica-crittografica)
3. [Deploy sul Broker Mosquitto](#3-deploy-sul-broker-mosquitto)
4. [Configurazione Backend (Python Bridge)](#4-configurazione-backend-python-bridge)
5. [Configurazione Firmware (ESP32)](#5-configurazione-firmware-esp32)
6. [Controlli a Runtime](#6-controlli-a-runtime)
7. [Troubleshooting & Codici di Errore](#7-troubleshooting--codici-di-errore)
8. [Procedura Rapida: Cambio IP del Broker](#8-procedura-rapida-cambio-ip-del-broker)

---

## 1) Creazione dei Certificati (PKI Setup)

Eseguire i seguenti comandi all'interno dell'ambiente WSL/Linux:

```bash
mkdir -p /home/enzo/certs_creator/test
cd /home/enzo/certs_creator/test
```
### 1.1 Generazione della Certification Authority (CA)

Inizializza la chiave privata della CA e il certificato Root (validità 10 anni).
```bash

openssl genrsa -out ca-key.pem 2048
openssl req -x509 -new -nodes -key ca-key.pem -sha256 -days 3650 -out ca-cert.pem
```
### 1.2 Generazione Certificato Server (con IP SAN)

La libreria mbedTLS dell'ESP32 esige la presenza dell'IP nel campo Subject Alternative Name (SAN) e l'estensione serverAuth.
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
### 1.3 Generazione Certificati Client (Python + ESP32)

Ogni endpoint richiede l'estensione clientAuth per l'autenticazione mTLS.
```bash

cat > client-ext.cnf << 'EOF'
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=clientAuth
EOF

# -------------------------
# Endpoint 1: Python Bridge
# -------------------------
openssl genrsa -out python-client-key.pem 2048
openssl req -new -key python-client-key.pem -out python-client.csr \
  -subj "/C=IT/ST=Italy/O=CARE/CN=python-client"
openssl x509 -req -in python-client.csr -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out python-client-cert.pem -days 365 -sha256 \
  -extfile client-ext.cnf

# -------------------------
# Endpoint 2: ESP32 Gateway
# -------------------------
openssl genrsa -out esp32-client-key.pem 2048
openssl req -new -key esp32-client-key.pem -out esp32-client.csr \
  -subj "/C=IT/ST=Italy/O=CARE/CN=esp32-client"
openssl x509 -req -in esp32-client.csr -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out esp32-client-cert.pem -days 365 -sha256 \
  -extfile client-ext.cnf
```
Workaround mbedTLS: Generazione del formato RSA tradizionale per la chiave privata dell'ESP32 (previene errori di allineamento e memoria).
```bash

openssl rsa -traditional -in esp32-client-key.pem -out esp32-client-key-rsa.pem
```
## 2) Verifica Crittografica

Validazione della catena di trust e controllo dell'estensione SAN.
```bash

openssl verify -CAfile ca-cert.pem server-cert.pem
openssl verify -CAfile ca-cert.pem python-client-cert.pem
openssl verify -CAfile ca-cert.pem esp32-client-cert.pem
openssl x509 -in server-cert.pem -noout -ext subjectAltName
```
Expected Output:

    Tutti i comandi verify devono restituire OK.

    L'ultimo comando deve stampare IP Address:192.168.137.1.

## 3) Deploy sul Broker Mosquitto

Copia dei payload crittografici nella directory esposta al container Docker del broker.
```bash

cp server-cert.pem /mnt/c/Progetti/CARE_Lab/mosquitto/config/certs/server-cert.pem
cp server-key.pem /mnt/c/Progetti/CARE_Lab/mosquitto/config/certs/server-key.pem
cp ca-cert.pem /mnt/c/Progetti/CARE_Lab/mosquitto/config/certs/ca-cert.pem
```
Riavvio del servizio per caricare il nuovo contesto TLS in memoria:
```bash

docker restart care_broker
```
## 4) Configurazione Backend (Python Bridge)

Il file backend/config.py deve puntare ai path corretti dei certificati client:

    CA_CERT -> ca-cert.pem

    CLIENT_CERT -> python-client-cert.pem

    CLIENT_KEY -> python-client-key.pem

## 5) Configurazione Firmware (ESP32)

Aprire il file sorgente firmware/src/secrets.cpp e sovrascrivere le costanti stringa inserendo il contenuto testuale esatto dei file .pem:

    ca_cert_pem <- Contenuto di ca-cert.pem

    client_cert_pem <- Contenuto di esp32-client-cert.pem

    client_key_pem <- Contenuto di esp32-client-key-rsa.pem (Attenzione: usare la versione RSA)

Successivamente, pulire la build ed eseguire il flash:
```bash

pio run -t clean
pio run -t upload
```

## 6) Controlli a Runtime

   Backend Logs: Il bridge Python deve mostrare [INFO] bridge: TLS Attivato con verifica certificato e l'iscrizione ai topic confermata.

   Mosquitto Logs: Verificare le identità X.509 estratte dalle ACL del broker:

        Connessione bridge: New client connected... as python-client

        Connessione edge: New client connected... as esp32-client

## 7) Troubleshooting & Codici di Errore

   CERTIFICATE_VERIFY_FAILED (Python) / Disallineamento IP:

        Causa: Il certificato del server non ha il campo SAN configurato con l'IP attuale del broker.

   ESP32 lastError=-9984 (X509 - Certificate verification failed):

        Causa: Mismatch della CA, certificato server mancante dell'estensione serverAuth, oppure firmware obsoleto (non riflashato dopo l'update di secrets.cpp).

   ESP32 PADLOCK - Input data should be aligned:

        Causa: La chiave privata passata a mbedTLS non è nel formato legacy corretto. Utilizzare esclusivamente esp32-client-key-rsa.pem (che inizia con BEGIN RSA PRIVATE KEY).

   Mosquitto "not authorised" (con use_identity_as_username true):

        Causa: Il certificato client è privo del campo CN (Common Name) richiesto per mappare l'utente nelle regole ACL.

## 8) Procedura Rapida: Cambio IP del Broker

Se l'indirizzo IP del gateway/hotspot cambia (es. da 192.168.137.1 a 192.168.55.1), NON è necessario rigenerare la CA o i certificati client. È sufficiente rigenerare e sostituire esclusivamente il certificato del server aggiornando il campo SAN.
### 8.1 Rigenerazione del Server Certificate
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

# Verifica rapida
openssl verify -CAfile ca-cert.pem server-cert.pem
openssl x509 -in server-cert.pem -noout -ext subjectAltName
```
### 8.2 Deploy e Riavvio
```bash

cp server-cert.pem /mnt/c/Progetti/CARE_Lab/mosquitto/config/certs/server-cert.pem
cp server-key.pem /mnt/c/Progetti/CARE_Lab/mosquitto/config/certs/server-key.pem
docker restart care_broker
```
### 8.3 Aggiornamento degli Endpoint

  Backend: Aggiornare la variabile MQTT_BROKER (es. tramite export .env) con il nuovo IP.

  SP32: Aggiornare la costante MQTT_SERVER in firmware/src/secrets.cpp e rieseguire il flash:
    ```bash

    pio run -t clean
    pio run -t upload
    ```
