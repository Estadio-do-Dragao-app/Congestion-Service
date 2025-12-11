import json
import paho.mqtt.client as mqtt
from models import CellCongestionData
from mqtt_configs import SIMULATOR_BROKER, SIMULATOR_PORT, SIMULATOR_TOPIC, CLIENT_BROKER, CLIENT_PORT, CLIENT_TOPIC
from datetime import datetime

# Will import after app is created to avoid circular imports
cell_congestion_store = None

def on_simulator_connect(client, userdata, flags, rc):
    """Handle MQTT connection to simulator broker"""
    if rc == 0:
        print(f"[SIMULATOR] Connected to broker at {SIMULATOR_BROKER}:{SIMULATOR_PORT}")
        client.subscribe(SIMULATOR_TOPIC)
        print(f"[SIMULATOR] Subscribed to topic: {SIMULATOR_TOPIC}")
    else:
        print(f"[SIMULATOR] Connection failed with code {rc}")

def on_client_connect(client, userdata, flags, rc):
    """Handle MQTT connection to client broker"""
    if rc == 0:
        print(f"[CLIENT] Connected to broker at {CLIENT_BROKER}:{CLIENT_PORT}")
    else:
        print(f"[CLIENT] Connection failed with code {rc}")

def on_message(client, userdata, msg):
    """Process incoming MQTT messages with congestion data from simulator"""
    try:
        # Decode the payload
        payload = msg.payload.decode('utf-8')
        data_dict = json.loads(payload)
        
        # Check if this is a crowd_density event from the simulator
        if data_dict.get('event_type') == 'crowd_density':
            # Extract grid_data array
            grid_data = data_dict.get('grid_data', [])
            timestamp = data_dict.get('timestamp', datetime.now().isoformat())
            
            print(f"[SIMULATOR] Received crowd_density event with {len(grid_data)} cells")
            
            # Process each cell in the grid
            for cell_data in grid_data:
                cell_id = cell_data.get('cell_id')
                count = cell_data.get('count', 0)
                
                # Calculate congestion level (0-1 scale)
                # Assuming max 50 people per cell as full capacity
                max_capacity = 50
                congestion_level = min(count / max_capacity, 1.0)
                
                # Create CellCongestionData object
                congestion_data = CellCongestionData(
                    cell_id=cell_id,
                    congestion_level=congestion_level,
                    people_count=count,
                    capacity=max_capacity,
                    timestamp=timestamp
                )
                
                # Store in the shared dictionary
                if cell_congestion_store is not None:
                    cell_congestion_store[cell_id] = congestion_data
                    
                    # Publish to client broker for client consumption
                    publish_to_clients(congestion_data)
                    
            print(f"[SIMULATOR] Processed and stored {len(grid_data)} cells")
        else:
            # Try to parse as direct CellCongestionData (for backwards compatibility)
            if 'timestamp' not in data_dict:
                data_dict['timestamp'] = datetime.now()
            
            congestion_data = CellCongestionData(**data_dict)
            
            # Store in the shared dictionary
            if cell_congestion_store is not None:
                cell_congestion_store[congestion_data.cell_id] = congestion_data
                print(f"[SIMULATOR] Stored congestion data - Cell: {congestion_data.cell_id}, Level: {congestion_data.congestion_level}")
                
                # Publish to client broker for client consumption
                publish_to_clients(congestion_data)
            else:
                print(f"[SIMULATOR] Warning: Storage not initialized yet")
        
    except json.JSONDecodeError as e:
        print(f"[SIMULATOR] JSON decode error: {e}")
    except Exception as e:
        print(f"[SIMULATOR] Error processing message: {e}")
        import traceback
        traceback.print_exc()

def publish_to_clients(congestion_data: CellCongestionData):
    """Publish congestion data to client broker"""
    try:
        payload = congestion_data.model_dump_json()
        client_publisher.publish(CLIENT_TOPIC, payload, qos=1)
        print(f"[CLIENT] Published to topic: {CLIENT_TOPIC} (cell={congestion_data.cell_id}, level={congestion_data.congestion_level:.2f})")
    except Exception as e:
        print(f"[CLIENT] Error publishing: {e}")

# Create separate MQTT clients for simulator and client connections
simulator_client = mqtt.Client(client_id="congestion_service_receiver")
simulator_client.on_connect = on_simulator_connect
simulator_client.on_message = on_message

client_publisher = mqtt.Client(client_id="congestion_service_publisher")
client_publisher.on_connect = on_client_connect

def start_mqtt(store):
    """Start MQTT clients and connect to both brokers"""
    global cell_congestion_store
    cell_congestion_store = store
    
    try:
        # Connect to simulator broker (to receive congestion events)
        simulator_client.connect(SIMULATOR_BROKER, SIMULATOR_PORT, 60)
        simulator_client.loop_start()
        print(f"[SIMULATOR] Client started, connecting to {SIMULATOR_BROKER}:{SIMULATOR_PORT}")
        
        # Connect to client broker (to publish congestion data)
        client_publisher.connect(CLIENT_BROKER, CLIENT_PORT, 60)
        client_publisher.loop_start()
        print(f"[CLIENT] Publisher started, connecting to {CLIENT_BROKER}:{CLIENT_PORT}")
    except Exception as e:
        print(f"[MQTT] Failed to start: {e}")