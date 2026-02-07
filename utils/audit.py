import sqlite3
import hashlib
import logging
import getpass
import time
from web3 import Web3
from colorama import Fore, Style, init
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.config import Config

# Inizializza colorama
init(autoreset=True)

# Database Utenti
USERS_DB = {
    "admin": {"pass": "admin123", "role": "ADMIN"},
    "auditor": {"pass": "audit2024", "role": "AUDITOR"},
}

try:
    w3 = Web3(Web3.HTTPProvider(Config.GANACHE_URL))
    if not w3.is_connected():
        raise RuntimeError("Nodo Ethereum irraggiungibile")
    
    contract = w3.eth.contract(address=Config.CONTRACT_ADDRESS, abi=Config.CONTRACT_ABI)
    OWNER_ACCOUNT = w3.eth.accounts[0] 

except Exception as e:
    print(f"{Fore.RED}[CRITICAL ERROR] Blockchain connection failed: {e}")
    exit(1)


def clear_screen():
    """Pulisce la console (Windows/Linux/Mac)"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(role="N/A"):
    """Stampa l'intestazione standard del sistema"""
    clear_screen()
    print(Fore.CYAN + "╔══════════════════════════════════════════════════════════════╗")
    print(Fore.CYAN + "║            MEDICAL BLOCKCHAIN AUDIT SYSTEM v2.0              ║")
    print(Fore.CYAN + "╠══════════════════════════════════════════════════════════════╣")
    print(Fore.CYAN + f"║  User: {Fore.YELLOW}{role.ljust(15)}{Fore.CYAN} |  Status: {Fore.GREEN}CONNECTED{Fore.CYAN}                         ║")
    print(Fore.CYAN + "╚══════════════════════════════════════════════════════════════╝")
    print("")

def pause():
    """Mette in pausa per permettere la lettura dell'output"""
    print("\n" + Fore.LIGHTBLACK_EX + "-" * 62)
    input(f"{Fore.WHITE} >> Premi {Fore.GREEN}INVIO{Fore.WHITE} per tornare al menu principale...")

def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def login():
    clear_screen()
    print(Fore.CYAN + "╔══════════════════════════════════════════════════════════════╗")
    print(Fore.CYAN + "║                   SYSTEM LOGIN REQUIRED                      ║")
    print(Fore.CYAN + "╚══════════════════════════════════════════════════════════════╝")
    print("")
    user = input("Username: ")
    password = getpass.getpass("Password: ")

    if user in USERS_DB and USERS_DB[user]["pass"] == password:
        return USERS_DB[user]["role"]
    else:
        print(f"\n{Fore.RED}[ERROR] Credenziali non valide.")
        time.sleep(1.5)
        return None

def verify_record_integrity(role):
    print_header(role)
    print(f"{Fore.WHITE}--- VERIFICA INTEGRITA' DATI ---\n")
    
    record_id = input(f"{Fore.YELLOW}Inserisci ID Record da verificare: {Fore.RESET}")
    print(f"\n{Fore.CYAN}[INFO] Analisi record ID: {record_id} in corso...")

    try:
        conn = sqlite3.connect(Config.DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT payload, data_hash FROM patient_records WHERE id=?", (record_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            print(f"{Fore.RED}[ERROR] Record non trovato nel Database Locale.")
            return

        payload, local_hash = row
        calc_hash = sha256_hex(payload)
        
        onchain_data = contract.functions.registry(int(record_id)).call()
        if onchain_data[0] == 0:
            print(f"{Fore.RED}[ERROR] Record non trovato su Blockchain.")
            return
            
        onchain_hash = onchain_data[2].hex()

        # Output Risultati
        print(f"\n{Fore.WHITE}RISULTATI ANALISI:")
        print(f"{Fore.WHITE}Hash Calcolato (DB): {Fore.LIGHTBLUE_EX}{calc_hash}")
        print(f"{Fore.WHITE}Hash Immutabile (BC):{Fore.LIGHTBLUE_EX}{onchain_hash}")

        print("-" * 62)

        if calc_hash == onchain_hash:
            print(f"{Fore.GREEN}[OK] INTEGRITA' CONFERMATA")
            print(f"{Fore.GREEN}     Il dato corrisponde perfettamente alla notarizzazione.")
        else:
            print(f"{Fore.RED}[CRITICAL] ATTENZIONE: DATI MANOMESSI!")
            print(f"{Fore.RED}           Rilevata discrepanza tra DB locale e Blockchain.")

    except Exception as e:
        print(f"{Fore.RED}[EXCEPTION] Errore durante la verifica: {e}")

def manage_notarizers(role):
    print_header(role)
    print(f"{Fore.WHITE}--- GESTIONE NOTARIZER (GATEWAYS) ---\n")
    
    target_address = input(f"{Fore.YELLOW}Inserisci indirizzo Ethereum Gateway: {Fore.RESET}").strip()
    
    if not w3.is_address(target_address):
        print(f"\n{Fore.RED}[ERROR] Formato indirizzo Ethereum non valido.")
        return

    print(f"\n{Fore.WHITE}Seleziona azione:")
    print(f" [1] {Fore.GREEN}ABILITA{Fore.RESET} permessi di scrittura")
    print(f" [2] {Fore.RED}REVOCA{Fore.RESET} permessi di scrittura")
    choice = input("\nScelta: ")
    
    is_enabled = True if choice == '1' else False
    status_str = "ABILITATO" if is_enabled else "DISABILITATO"
    
    print(f"\n{Fore.WHITE}Stai per impostare {target_address} come {Fore.YELLOW}{status_str}{Fore.WHITE}.")
    confirm = input("Confermi la transazione? (y/n): ")
    
    if confirm.lower() != 'y':
        print(f"\n{Fore.YELLOW}[INFO] Operazione annullata dall'utente.")
        return

    try:
        print(f"\n{Fore.CYAN}[INFO] Invio transazione alla Blockchain in corso...")
        
        tx_hash = contract.functions.setNotarizer(
            target_address, 
            is_enabled
        ).transact({'from': OWNER_ACCOUNT})
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            print(f"\n{Fore.GREEN}[OK] Transazione confermata.")
            print(f"{Fore.GREEN}     Block Number: {receipt.blockNumber}")
            print(f"{Fore.GREEN}     Stato aggiornato con successo.")
        else:
            print(f"\n{Fore.RED}[ERROR] La transazione e' stata rifiutata (Revert).")

    except Exception as e:
        print(f"\n{Fore.RED}[EXCEPTION] Errore Blockchain: {e}")


if __name__ == "__main__":
    current_role = login()
    
    if not current_role:
        exit(1)

    while True:
        # 1. Pulisce e mostra Header
        print_header(current_role)

        # 2. Mostra il Menu
        print(f"{Fore.WHITE}Seleziona un'operazione:")
        print(f" [1] {Fore.CYAN}Verifica Integrita' Dati (tramite ID)")
        
        if current_role == "ADMIN":
            print(f" [2] {Fore.MAGENTA}Gestione Notarizer (Admin Only)")
        
        print(f" [q] {Fore.RED}Esci")
        
        print(Fore.CYAN + "╚══════════════════════════════════════════════════════════════╝")
        
        # 3. Input Utente
        choice = input(f"\n{Fore.GREEN}➜ Scelta: {Fore.RESET}")

        # 4. Esecuzione Logica
        if choice == '1':
            verify_record_integrity(current_role)
            pause()

        elif choice == '2':
            if current_role == "ADMIN":
                manage_notarizers(current_role)
            else:
                print(f"\n{Fore.RED}[ACCESS DENIED] Richiesto livello ADMIN.")
            pause()

        elif choice.lower() == 'q':
            print(f"\n{Fore.YELLOW}[INFO] Chiusura sessione sicura...")
            time.sleep(1)
            clear_screen()
            break
        
        else:
            print(f"\n{Fore.RED}[ERROR] Scelta non valida.")
            time.sleep(1)