import json
import paho.mqtt.client as mqtt
from schemas import CellCongestionData, CrowdDensityEvent
from mqtt_configs import SIMULATOR_BROKER, SIMULATOR_PORT, SIMULATOR_TOPIC, CLIENT_BROKER, CLIENT_PORT, CLIENT_TOPIC
from datetime import datetime
from typing import Optional
from store import cell_congestion_store, aggregate_cell_data

def on_message(client, userdata, msg):
    """Process incoming MQTT messages with Pydantic validation"""
    try:
        payload = msg.payload.decode('utf-8')
        data_dict = json.loads(payload)

        # Use Pydantic model for validation
        event = CrowdDensityEvent.model_validate(data_dict)
        
        if event.event_type == 'crowd_density':
            print(f"[MQTT] Processing crowd_density event from {event.metadata.get('camera_id', 'unknown')}")
            
            cam_id = event.metadata.get('camera_id', 'unknown_cam')
            timestamp = datetime.now() 
            level = event.level
            
            updated_cells = []
            
            for cell_item in event.grid_data:
                cell_id = cell_item.cell_id
                if not cell_id:
                    # Format coordinates to match previous behavior (no .0 for integers)
                    x_str = f"{int(cell_item.x)}" if cell_item.x == int(cell_item.x) else f"{cell_item.x}"
                    y_str = f"{int(cell_item.y)}" if cell_item.y == int(cell_item.y) else f"{cell_item.y}"
                    cell_id = f"cell_{level}_{x_str}_{y_str}"
                
                # Update nested store
                cell_congestion_store[cell_id][cam_id] = {
                    "count": cell_item.count,
                    "timestamp": timestamp,
                    "level": level
                }
                updated_cells.append(cell_id)
            
            # Publish updates for each modified cell
            for cid in updated_cells:
                agg_data = aggregate_cell_data(cid, level)
                if agg_data:
                    publish_to_clients(agg_data)

    except Exception as e:
        print(f"[SIMULATOR] Error processing message: {e}")

def publish_to_clients(congestion_data: CellCongestionData):
    """Publish congestion data to client broker"""
    try:
        payload = congestion_data.model_dump_json()
        client_publisher.publish(CLIENT_TOPIC, payload, qos=1)
        print(f"[CLIENT] Published to {CLIENT_TOPIC}: {congestion_data.cell_id} (congestion: {congestion_data.congestion_level:.2f})")
    except Exception as e:
        print(f"[CLIENT] ❌ Error publishing: {e}")

# Clients Setup
simulator_client = mqtt.Client(client_id="congestion_service_receiver")
simulator_client.on_message = on_message

client_publisher = mqtt.Client(client_id="congestion_service_publisher")

def start_mqtt():
    """Start MQTT clients"""
    try:
        simulator_client.connect(SIMULATOR_BROKER, SIMULATOR_PORT, 60)
        simulator_client.subscribe(SIMULATOR_TOPIC)
        simulator_client.loop_start()
        
        client_publisher.connect(CLIENT_BROKER, CLIENT_PORT, 60)
        client_publisher.loop_start()
        print("[MQTT] Services Started")
    except Exception as e:
        print(f"[MQTT] Failed to start: {e}")

def stop_mqtt():
    """Stop MQTT clients"""
    simulator_client.loop_stop()
    simulator_client.disconnect()
    client_publisher.loop_stop()
    client_publisher.disconnect()
    print("[MQTT] Services Stopped")