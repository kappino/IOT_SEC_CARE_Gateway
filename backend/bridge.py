import json
import threading
import queue
import hmac
import hashlib
import ssl
import paho.mqtt.client as mqtt
import os
from config import Config, logger
from database import DatabaseManager
from blockchain import BlockchainNotary

class IoTBridge:
    def __init__(self):
        self.db = DatabaseManager()
        self.bc = BlockchainNotary()
        
        self.message_queue = queue.Queue(maxsize=200)
        self.running = True

    def start(self):
        """Avvia il worker thread e il client MQTT"""
        worker = threading.Thread(target=self._process_queue, daemon=True)
        worker.start()
        
        self._start_mqtt()

    def _start_mqtt(self):
        client = mqtt.Client(client_id="iot-bridge-modular", protocol=mqtt.MQTTv311)
        broker_host = Config.MQTT_BROKER_HOSTNAME or Config.MQTT_BROKER
        
        tls_files = [Config.CA_CERT, Config.CLIENT_CERT, Config.CLIENT_KEY]
        missing_files = [p for p in tls_files if not os.path.exists(p)]
        if missing_files:
            raise FileNotFoundError(f"File TLS mancanti: {', '.join(missing_files)}")

        logger.info("Configurazione Contesto SSL Sicuro...")
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=Config.CA_CERT)
        context.load_cert_chain(certfile=Config.CLIENT_CERT, keyfile=Config.CLIENT_KEY)
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        client.tls_set_context(context)
        logger.info("TLS Attivato con verifica certificato.")
        
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        
        logger.info(f"Connessione MQTT a {broker_host}...")
        client.connect(broker_host, Config.MQTT_PORT)

        client.loop_forever()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Iscrizione al topic: {Config.MQTT_TOPIC}")
            client.subscribe(Config.MQTT_TOPIC)
        else:
            logger.error(f"Errore connessione MQTT: {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode()
            self.message_queue.put_nowait(payload)
        except queue.Full:
            logger.warning("Coda piena: messaggio MQTT scartato")
        except Exception as e:
            logger.error(f"Errore parsing MQTT: {e}")

    def _process_queue(self):
        logger.info("Worker Thread avviato e in attesa...")
        
        while self.running:
            payload_str = None
            try:
                #Prelevo dalla coda
                payload_str = self.message_queue.get(timeout=1)
                
                # Parsing
                data = json.loads(payload_str)
                device_id = data.get("id", "UNKNOWN")
                ts = data.get("ts")
                value_raw = data.get("value")
                value = float(value_raw or 0)
                signature = data.get("sig")

                if not device_id or not signature or ts is None or value_raw is None:
                    logger.warning("Payload incompleto: firma o timestamp mancante")
                    self.message_queue.task_done()
                    continue

                signed_payload = f"{device_id}{ts}{value_raw}"
                expected_sig = hmac.new(
                    Config.HMAC_SECRET.encode("utf-8"),
                    signed_payload.encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()

                if not hmac.compare_digest(expected_sig, signature):
                    logger.warning("HMAC non valida: messaggio scartato")
                    self.message_queue.task_done()
                    continue
                
                # Logica gestione eventi critici
                is_critical = value > 120 or value < 50
                status_label = "CRITICAL" if is_critical else "NORMAL"
                
                logger.info(f"Processing Msg | Device: {device_id} | Val: {value}")

                # Notarizzazione
                tx_hash, data_hash = self.bc.notarize(device_id, payload_str, is_critical)

                # Scrittura su db
                final_status = status_label
                if tx_hash in ["ERROR", "UNAUTHORIZED", "CONTRACT_ERROR", "DUPLICATE_ON_CHAIN"]:
                    final_status = f"{status_label}_CHAIN_FAIL"
                
                self.db.save_record(device_id, payload_str, data_hash, tx_hash, final_status)

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Errore nel Worker: {e}")
            finally:
                if payload_str is not None:
                    self.message_queue.task_done()
