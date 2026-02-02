from paho.mqtt import client as mqtt
import sqlite3
import hashlib
import json
import os
from web3 import Web3
from datetime import datetime

GANACHE_URL = "http://127.0.0.1:7545"
CONTRACT_ADDRESS = "0xdE451736E6FE99DB5F4F84306829a7871CCeD4D0"

ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "id", "type": "uint256"},
            {"indexed": False, "internalType": "bytes32", "name": "deviceId", "type": "bytes32"},
            {"indexed": False, "internalType": "bool", "name": "critical", "type": "bool"}
        ],
        "name": "DataNotarized",
        "type": "event"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "_deviceId", "type": "bytes32"},
            {"internalType": "bytes32", "name": "_dataHash", "type": "bytes32"},
            {"internalType": "bool", "name": "_critical", "type": "bool"}
        ],
        "name": "addRecord",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
if not w3.is_connected():
    raise RuntimeError("Unable to connect to Ethereum node")

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)
account = w3.eth.accounts[0]

MQTT_BROKER = "192.168.5.37"
MQTT_PORT = 8883
MQTT_TOPIC = "care/gateway/data"

wsl_path = r"\\wsl.localhost\kali-linux\home\enzo\certs_lab"

CA_CERT = os.path.join(wsl_path, "ca-cert.pem")
CLIENT_CERT = os.path.join(wsl_path, "client-cert.pem")
CLIENT_KEY = os.path.join(wsl_path, "client-key.pem")

# =====================================================
# OFF-CHAIN STORAGE (SQLITE)
# =====================================================

DB_NAME = "medical_data_lake.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS patient_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            device_id TEXT,
            payload TEXT,
            data_hash TEXT,
            tx_hash TEXT,
            status TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def save_record(device_id, payload, data_hash, tx_hash, status):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO patient_records
        (timestamp, device_id, payload, data_hash, tx_hash, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.utcnow().isoformat(),
            device_id,
            payload,
            data_hash,
            tx_hash,
            status
        )
    )
    conn.commit()
    conn.close()


def sha256_bytes32(data: str) -> bytes:
    return hashlib.sha256(data.encode()).digest()


def device_id_bytes32(device_id: str) -> bytes:
    return hashlib.sha256(device_id.encode()).digest()

def notarize(device_id: str, payload: str, critical: bool):
    data_hash = sha256_bytes32(payload)
    dev_id = device_id_bytes32(device_id)

    tx = contract.functions.addRecord(
        dev_id,
        data_hash,
        critical
    ).transact({"from": account})

    receipt = w3.eth.wait_for_transaction_receipt(tx)
    return receipt.transactionHash.hex(), data_hash.hex()


def on_message(client, userdata, msg):
    payload_str = msg.payload.decode()

    try:
        data = json.loads(payload_str)

        device_id = data["id"]
        value = float(data["value"])

        critical = value > 120 or value < 50
        status = "CRITICAL" if critical else "NORMAL"

        tx_hash, data_hash = notarize(device_id, payload_str, critical)

        save_record(
            device_id=device_id,
            payload=payload_str,
            data_hash=data_hash,
            tx_hash=tx_hash,
            status=status
        )

    except Exception as e:
        print(f"Processing error: {e}")


if __name__ == "__main__":
    init_db()

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION1,
        client_id="iot-blockchain-bridge"
    )

    client.tls_set(
        ca_certs=CA_CERT,
        certfile=CLIENT_CERT,
        keyfile=CLIENT_KEY
    )

    client.tls_insecure_set(True)

    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT)
    client.subscribe(MQTT_TOPIC)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        client.disconnect()
