import json
import paho.mqtt.client as mqtt
from schemas import CellCongestionData
from mqtt_configs import SIMULATOR_BROKER, SIMULATOR_PORT, SIMULATOR_TOPIC, CLIENT_BROKER, CLIENT_PORT, CLIENT_TOPIC
from datetime import datetime, timezone
from typing import Optional, Dict
from collections import defaultdict

# In-memory storage: {cell_id: {camera_id: {count, timestamp, level}}}
cell_congestion_store = defaultdict(dict)
CAMERA_TTL = 30  # seconds

def aggregate_cell_data(cell_id: str, level: int = 0) -> Optional[CellCongestionData]:
    """
    Aggregates data for a cell by taking the MAX count among active cameras.
    Also PERFORMS MEMORY CLEANUP (GC) of stale camera entries.
    """
    cameras_data = cell_congestion_store.get(cell_id, {})
    if not cameras_data:
        return None
    
    current_time = datetime.now()
    max_people = 0
    active_cameras = []
    
    # Iterate over a list of keys to allow deletion during iteration
    for cam_id in list(cameras_data.keys()):
        data = cameras_data[cam_id]
        # Handle both string and datetime timestamps
        ts = data["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        
        # Check TTL
        if (current_time - ts.replace(tzinfo=None)).total_seconds() < CAMERA_TTL:
            # RED TEAM FIX: Using MAX instead of SUM to avoid double counting in FOV overlaps
            max_people = max(max_people, data["count"])
            active_cameras.append(cam_id)
        else:
            # MEMORY LEAK FIX: Explicitly remove stale camera data
            del cell_congestion_store[cell_id][cam_id]
            
    if not active_cameras:
        if cell_id in cell_congestion_store and not cell_congestion_store[cell_id]:
            del cell_congestion_store[cell_id]
        return None

    # Calculate congestion based on aggregated max
    max_capacity = 50
    congestion_level = min(max_people / max_capacity, 1.0)
    
    return CellCongestionData(
        cell_id=cell_id,
        congestion_level=congestion_level,
        people_count=max_people,
        capacity=max_capacity,
        level=level,
        timestamp=current_time,
        camera_id=",".join(active_cameras)
    )

def on_message(client, userdata, msg):
    """Process incoming MQTT messages with strict validation"""
    try:
        payload = msg.payload.decode('utf-8')
        topic = msg.topic
        print(f"[MQTT] Received message on topic: {topic}")
        print(f"[MQTT] Payload: {payload}")
        data_dict = json.loads(payload)

        
        # Validation and Storage logic
        if data_dict.get('event_type') == 'crowd_density':
            print(f"[MQTT] Processing crowd_density event")
            grid_data = data_dict.get('grid_data', [])
            cam_id = data_dict.get('metadata', {}).get('camera_id', 'unknown_cam')
            timestamp = datetime.now() # Use local arrival time for TTL consistency
            level = data_dict.get('level', 0)
            
            for cell_item in grid_data:
                cell_id = cell_item.get('cell_id')
                if not cell_id:
                    x, y = cell_item.get('x', 0), cell_item.get('y', 0)
                    cell_id = f"cell_{level}_{x}_{y}"
                
                count = cell_item.get('count', 0)
                
                # Update nested store
                cell_congestion_store[cell_id][cam_id] = {
                    "count": count,
                    "timestamp": timestamp,
                    "level": level
                }
                
                # Trigger aggregation and publish
                agg_data = aggregate_cell_data(cell_id, level)
                if agg_data:
                    publish_to_clients(agg_data)

    except Exception as e:
        print(f"[SIMULATOR] Poison Pill / Error: {e}")

def publish_to_clients(congestion_data: CellCongestionData):
    """Publish congestion data to client broker"""
    try:
        payload = congestion_data.model_dump_json()
        print(f"🔥 [CLIENT] Publishing: {payload[:150]}...")
        client_publisher.publish(CLIENT_TOPIC, payload, qos=1)
        print(f"[CLIENT] ✅ Published to {CLIENT_TOPIC}: {congestion_data.cell_id} (congestion: {congestion_data.congestion_level:.2f}, level: {congestion_data.level})")
    except Exception as e:
        print(f"[CLIENT] ❌ Error publishing: {e}")

# Clients Setup
simulator_client = mqtt.Client(client_id="congestion_service_receiver")
simulator_client.on_message = on_message

client_publisher = mqtt.Client(client_id="congestion_service_publisher")

def start_mqtt(store=None):
    """Start MQTT clients"""
    # global cell_congestion_store # Store is now internal to maintain integrity
    try:
        simulator_client.connect(SIMULATOR_BROKER, SIMULATOR_PORT, 60)
        simulator_client.subscribe(SIMULATOR_TOPIC)
        simulator_client.loop_start()
        
        client_publisher.connect(CLIENT_BROKER, CLIENT_PORT, 60)
        client_publisher.loop_start()
        print("[MQTT] Services Started (Reliability Fixed)")
    except Exception as e:
        print(f"[MQTT] Failed to start: {e}")