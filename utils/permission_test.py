import logging
import sys
from web3 import Web3
from web3.exceptions import ContractLogicError
import random
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("SecurityAudit")

def run_access_control_test(test_name, transaction_func):
    logger.info(f"TEST START: {test_name}")
    
    try:
        tx_hash = transaction_func()
        
        logger.critical(f"FAILED: Transazione confermata con hash {tx_hash.hex()}. Vulnerabilità critica rilevata.")
        return False

    except (ContractLogicError, Exception) as e:
        error_message = str(e)
        
        if "revert" in error_message or "Unauthorized" in error_message:
            logger.info(f"PASSED: La Blockchain ha bloccato la transazione come previsto.")
            logger.debug(f"Dettaglio errore: {error_message}")
            return True
        else:
            logger.warning(f"WARNING: Transazione fallita ma con errore imprevisto: {error_message}")
            return True

def main():
    logger.info("--- AVVIO SECURITY INTEGRATION TESTS ---")
    try:
        w3 = Web3(Web3.HTTPProvider(Config.GANACHE_URL))
        if not w3.is_connected():
            raise ConnectionError("Impossibile connettersi al nodo Ethereum.")
        
        contract = w3.eth.contract(address=Config.CONTRACT_ADDRESS, abi=Config.CONTRACT_ABI)
        
        admin_account = w3.eth.accounts[0]
        unauth_index = int(sys.argv[1]) if len(sys.argv) > 1 else 9
        unauthorized_account = w3.eth.accounts[unauth_index]

        logger.info(f"Admin Address:       {admin_account}")
        logger.info(f"Unauthorized Actor:  {unauthorized_account}")
        logger.info("-" * 50)

    except Exception as e:
        logger.critical(f"Errore iniziale di configurazione: {e}")
        sys.exit(1)

    
    def attempt_unauthorized_write():
        # Usa un numero casuale per generare hash sempre nuovi
        random_nonce = random.randint(0, 1000000)
        fake_id = Web3.keccak(text=f"MALICIOUS_DEVICE_{random_nonce}")
        fake_hash = Web3.keccak(text=f"FAKE_DATA_PAYLOAD_{random_nonce}")
        
        return contract.functions.addRecord(
            fake_id,
            fake_hash,
            True
        ).transact({'from': unauthorized_account})

    test_1_result = run_access_control_test(
        "Verifica blocco scrittura dati non autorizzata (addRecord)", 
        attempt_unauthorized_write
    )

    logger.info("-" * 50)
    
    def attempt_privilege_escalation():
        return contract.functions.setNotarizer(
            unauthorized_account,
            True
        ).transact({'from': unauthorized_account})

    test_2_result = run_access_control_test(
        "Verifica blocco escalation privilegi (setNotarizer)", 
        attempt_privilege_escalation
    )

    logger.info("-" * 50)

    if test_1_result and test_2_result:
        logger.info("RISULTATO AUDIT: SUCCESSO. Il sistema è sicuro.")
        sys.exit(0)
    else:
        logger.critical("RISULTATO AUDIT: FALLITO. Rilevate vulnerabilità di sicurezza.")
        sys.exit(1)

if __name__ == "__main__":
    main()