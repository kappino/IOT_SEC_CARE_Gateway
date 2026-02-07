import sqlite3
from datetime import datetime
from config import Config, logger

class DatabaseManager:
    def __init__(self):
        self.db_name = Config.DB_NAME
        self._init_db()

    def _init_db(self):
        """Crea la tabella se non esiste"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS patient_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        device_id TEXT,
                        payload TEXT,
                        data_hash TEXT,
                        tx_hash TEXT,
                        status TEXT
                    )
                """)
        except Exception as e:
            logger.error(f"Errore inizializzazione DB: {e}")

    def save_record(self, device_id, payload, data_hash, tx_hash, status):
        """Salva il record in modo sicuro"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                conn.execute("""
                    INSERT INTO patient_records
                    (timestamp, device_id, payload, data_hash, tx_hash, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (datetime.utcnow().isoformat(), device_id, payload, data_hash, tx_hash, status))
            logger.info(f"Dato salvato su DB locale (ID: {device_id})")
        except Exception as e:
            logger.error(f"Errore scrittura DB: {e}")