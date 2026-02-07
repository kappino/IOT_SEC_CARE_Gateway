from bridge import IoTBridge
from config import logger
import sys

def main():
    print(r"""
     ___      _____   ___       _    _            
    |_ _|___ |_   _| | _ )_ _(_)__| |__ _ ___ 
     | |/ _ \  | |   | _ \ '_| / _` / _` / -_)
    |___\___/  |_|   |___/_| |_\__,_\__, \___|
                                    |___/     
    Modular Medical Data Notary v2.0
    """)
    
    bridge = IoTBridge()
    
    try:
        bridge.start()
    except KeyboardInterrupt:
        logger.info("🛑 Spegnimento manuale richiesto.")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Errore fatale: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()