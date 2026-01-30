import asyncio
import hmac
import hashlib
import json
import time
from bleak import BleakClient, BleakScanner

HMAC_SECRET = "care_shared_secret_32bytes"
DEVICE_NAME = "CARE_BLE_Gateway"
CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
SENSOR_ID = "MoveSense_01"

async def generate_signed_payload(value):
    ts = int(time.time())
    payload_str = f"{SENSOR_ID}{ts}{value}"
    
    key_bytes = bytes(HMAC_SECRET, 'utf-8')
    msg_bytes = bytes(payload_str, 'utf-8')
    signature = hmac.new(key_bytes, msg_bytes, hashlib.sha256).hexdigest()
    
    packet = {
        "id": SENSOR_ID,
        "ts": ts,
        "value": str(value),
        "sig": signature
    }
    return json.dumps(packet)

async def main():
    print(f"--- RICERCA DEL GATEWAY: {DEVICE_NAME} ---")
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: d.name and d.name == DEVICE_NAME
    )

    if not device:
        print(f"Errore: Dispositivo '{DEVICE_NAME}' non trovato")
        print("Assicurati che l'ESP32 sia acceso")
        return

    print(f"Trovato: {device.address}. Connessione in corso...")

    async with BleakClient(device) as client:
        print(f"Connesso: {client.is_connected}")
        
        while True:
            try:
                val_input = input("\nInserisci valore BPM (o 'q' per uscire): ")
                if val_input.lower() == 'q': break
                
                json_payload = await generate_signed_payload(val_input)
                print(f"Invio Payload: {json_payload}")
                
                await client.write_gatt_char(CHARACTERISTIC_UUID, json_payload.encode('utf-8'))
                print("Scrittura completata!")
                
            except Exception as e:
                print(f"Errore durante l'invio: {e}")
                break

    print("Disconnesso")

if __name__ == "__main__":
    asyncio.run(main())