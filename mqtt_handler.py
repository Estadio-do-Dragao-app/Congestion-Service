import json
import paho.mqtt.client as mqtt
from models import CellCongestionData
from mqtt_configs import BROKER, PORT, TOPIC
from datetime import datetime

# Will import after app is created to avoid circular imports
cell_congestion_store = None

def on_connect(client, userdata, flags, rc):
    """Handle MQTT connection"""
    if rc == 0:
        print(f"[MQTT] Connected to broker {BROKER}:{PORT}")
        client.subscribe(TOPIC)
        print(f"[MQTT] Subscribed to topic: {TOPIC}")
    else:
        print(f"[MQTT] Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    """Process incoming MQTT messages with congestion data"""
    try:
        # Decode the payload
        payload = msg.payload.decode('utf-8')
        data_dict = json.loads(payload)
        
        # Ensure timestamp is present
        if 'timestamp' not in data_dict:
            data_dict['timestamp'] = datetime.now()
        
        # Parse into CellCongestionData model
        congestion_data = CellCongestionData(**data_dict)
        
        # Store in the shared dictionary (import happens in start_mqtt)
        if cell_congestion_store is not None:
            cell_congestion_store[congestion_data.cell_id] = congestion_data
            print(f"[MQTT] Stored data - Cell: {congestion_data.cell_id}, Congestion: {congestion_data.congestion_level}")
        else:
            print(f"[MQTT] Warning: Storage not initialized yet")
        
    except json.JSONDecodeError as e:
        print(f"[MQTT] JSON decode error: {e}")
    except Exception as e:
        print(f"[MQTT] Error processing message: {e}")

# Create MQTT client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

def start_mqtt(store):
    """Start MQTT client and connect to broker"""
    global cell_congestion_store
    cell_congestion_store = store
    
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start()
        print(f"[MQTT] Client started, connecting to {BROKER}:{PORT}...")
    except Exception as e:
        print(f"[MQTT] Failed to start MQTT: {e}")