import sqlite3
import hashlib
import logging
from web3 import Web3

GANACHE_URL = "http://127.0.0.1:7545"
CONTRACT_ADDRESS = "0xYOUR_CONTRACT_ADDRESS"
DB_NAME = "medical_data_lake.db"

ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "name": "registry",
        "outputs": [
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "bytes32", "name": "deviceId", "type": "bytes32"},
            {"internalType": "bytes32", "name": "dataHash", "type": "bytes32"},
            {"internalType": "bool", "name": "critical", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
if not w3.is_connected():
    raise RuntimeError("Ethereum node not reachable")

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def get_last_local_record():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, device_id, payload, data_hash, tx_hash
        FROM patient_records
        ORDER BY id DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    conn.close()
    return row


def get_onchain_record(record_id: int):
    try:
        return contract.functions.registry(record_id).call()
    except Exception:
        return None

def verify_last_record():
    logging.info("Starting integrity verification")

    local_record = get_last_local_record()
    if not local_record:
        logging.error("No records found in local database")
        return False

    record_id, device_id, payload, stored_hash, tx_hash = local_record

    recalculated_hash = sha256_hex(payload)

    onchain_record = get_onchain_record(record_id)
    if not onchain_record:
        logging.error("Unable to retrieve on-chain record")
        return False

    onchain_hash_hex = onchain_record[2].hex()

    if recalculated_hash == onchain_hash_hex:
        logging.info(
            "Integrity check passed | record_id=%s device=%s",
            record_id, device_id
        )
        return True
    else:
        logging.warning(
            "Integrity check failed | record_id=%s device=%s",
            record_id, device_id
        )
        logging.warning("Local hash:   %s", recalculated_hash)
        logging.warning("On-chain hash:%s", onchain_hash_hex)
        return False

if __name__ == "__main__":
    success = verify_last_record()
    if not success:
        exit(1)
