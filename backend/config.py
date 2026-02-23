import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(module)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("IoT_Bridge")

class Config:
    # Blockchain
    GANACHE_URL = "http://127.0.0.1:7545"
    CONTRACT_ADDRESS = "0x55E3065D41c5705f26105C3Bdf8F1C146174Fcd2"
    
    # Database
    DB_NAME = "medical_data_lake.db"

    #MQTT
    MQTT_BROKER = os.getenv("MQTT_BROKER", "192.168.137.1")
    MQTT_BROKER_HOSTNAME = os.getenv("MQTT_BROKER_HOSTNAME")
    MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
    MQTT_TOPIC = os.getenv("MQTT_TOPIC", "care/gateway/data")
    
    # Certificati
    WSL_PATH = r"\\wsl.localhost\kali-linux\home\enzo\certs_creator\test"
    CA_CERT = os.path.join(WSL_PATH, "ca-cert.pem")
    CLIENT_CERT = os.path.join(WSL_PATH, "python-client-cert.pem")
    CLIENT_KEY = os.path.join(WSL_PATH, "python-client-key.pem")

    HMAC_SECRET = os.getenv("HMAC_SECRET", "care_shared_secret_32bytes")

    CONTRACT_ABI = [
	{
		"inputs": [],
		"stateMutability": "nonpayable",
		"type": "constructor"
	},
	{
		"inputs": [],
		"name": "DuplicateDataHash",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "InvalidAddress",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "InvalidPayload",
		"type": "error"
	},
	{
		"inputs": [],
		"name": "Unauthorized",
		"type": "error"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			},
			{
				"indexed": True,
				"internalType": "bytes32",
				"name": "deviceId",
				"type": "bytes32"
			},
			{
				"indexed": False,
				"internalType": "bytes32",
				"name": "dataHash",
				"type": "bytes32"
			},
			{
				"indexed": False,
				"internalType": "bool",
				"name": "critical",
				"type": "bool"
			},
			{
				"indexed": True,
				"internalType": "address",
				"name": "notarizer",
				"type": "address"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "timestamp",
				"type": "uint256"
			}
		],
		"name": "DataNotarized",
		"type": "event"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "address",
				"name": "notarizer",
				"type": "address"
			},
			{
				"indexed": False,
				"internalType": "bool",
				"name": "enabled",
				"type": "bool"
			}
		],
		"name": "NotarizerUpdated",
		"type": "event"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "address",
				"name": "previousOwner",
				"type": "address"
			},
			{
				"indexed": True,
				"internalType": "address",
				"name": "newOwner",
				"type": "address"
			}
		],
		"name": "OwnershipTransferred",
		"type": "event"
	},
	{
		"inputs": [
			{
				"internalType": "bytes32",
				"name": "deviceId",
				"type": "bytes32"
			},
			{
				"internalType": "bytes32",
				"name": "dataHash",
				"type": "bytes32"
			},
			{
				"internalType": "bool",
				"name": "critical",
				"type": "bool"
			}
		],
		"name": "addRecord",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "bytes32",
				"name": "",
				"type": "bytes32"
			}
		],
		"name": "dataHashUsed",
		"outputs": [
			{
				"internalType": "bool",
				"name": "",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"name": "notarizers",
		"outputs": [
			{
				"internalType": "bool",
				"name": "",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "owner",
		"outputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "recordCount",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"name": "registry",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "timestamp",
				"type": "uint256"
			},
			{
				"internalType": "bytes32",
				"name": "deviceId",
				"type": "bytes32"
			},
			{
				"internalType": "bytes32",
				"name": "dataHash",
				"type": "bytes32"
			},
			{
				"internalType": "bool",
				"name": "critical",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "notarizer",
				"type": "address"
			},
			{
				"internalType": "bool",
				"name": "enabled",
				"type": "bool"
			}
		],
		"name": "setNotarizer",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "newOwner",
				"type": "address"
			}
		],
		"name": "transferOwnership",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	}
]
