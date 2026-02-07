import hashlib
from web3 import Web3
from web3.exceptions import ContractLogicError
from config import Config, logger

class BlockchainNotary:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(Config.GANACHE_URL))
        if not self.w3.is_connected():
            raise ConnectionError("Impossibile connettersi al nodo Ethereum")
        
        self.contract = self.w3.eth.contract(address=Config.CONTRACT_ADDRESS, abi=Config.CONTRACT_ABI)
        self.account = self.w3.eth.accounts[0] # Assumiamo sia un Notarizer autorizzato
        logger.info(f"Connesso a Blockchain. Notarizer: {self.account}")

    def notarize(self, device_id_str, payload_str, is_critical):
        """Invia transazione allo Smart Contract e gestisce errori custom"""
        
        # Hashing dei dati (per bytes32)
        data_hash = hashlib.sha256(payload_str.encode()).digest()
        dev_id_bytes = hashlib.sha256(device_id_str.encode()).digest()
        data_hash_hex = data_hash.hex()

        try:
            # Invio Transazione
            tx = self.contract.functions.addRecord(
                dev_id_bytes,
                data_hash,
                is_critical
            ).transact({"from": self.account})

            # Attesa ricevuta
            receipt = self.w3.eth.wait_for_transaction_receipt(tx)
            
            logger.info(f"Notarizzazione confermata! TX: {receipt.transactionHash.hex()[:10]}...")
            return receipt.transactionHash.hex(), data_hash_hex

        except ContractLogicError as e:
            error_msg = str(e)
            if "DuplicateDataHash" in error_msg:
                logger.warning(f"Dato duplicato sulla Chain. Hash: {data_hash_hex[:8]}...")
                return "DUPLICATE_ON_CHAIN", data_hash_hex
            elif "Unauthorized" in error_msg:
                logger.critical("ERRORE: Account non autorizzato!")
                return "UNAUTHORIZED", data_hash_hex
            else:
                logger.error(f"Errore Contratto generico: {e}")
                return "CONTRACT_ERROR", data_hash_hex
                
        except Exception as e:
            logger.error(f"Errore Web3 critico: {e}")
            return "ERROR", data_hash_hex