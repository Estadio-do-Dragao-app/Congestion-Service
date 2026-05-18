import json
import ssl
import paho.mqtt.client as mqtt
from schemas import CellCongestionData, CrowdDensityEvent
from mqtt_configs import (
    SIMULATOR_BROKER, SIMULATOR_PORT, SIMULATOR_TOPIC,
    CLIENT_BROKER, CLIENT_PORT, CLIENT_TOPIC,
    MQTT_USER, MQTT_PASS, MQTT_CA_CERT,
)
from datetime import datetime
from typing import Optional
from store import cell_congestion_store, aggregate_cell_data


def _configure_mqtt_tls(client: mqtt.Client) -> None:
    """Apply credentials and TLS to a paho Client.

    If MQTT_CA_CERT points to a readable file, enables MQTTS (port 8883).
    Otherwise, falls back to authenticated plain MQTT (port 1883).
    Credentials are always set.
    """
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    if MQTT_CA_CERT:
        try:
            client.tls_set(
                ca_certs=MQTT_CA_CERT,
                tls_version=ssl.PROTOCOL_TLS_CLIENT,
            )
            client.tls_insecure_set(False)
        except Exception as exc:  # pragma: no cover
            print(f"[MQTT][TLS] Warning: could not configure TLS — {exc}")


def _get_cell_id(cell_item, level: int) -> str:
    """Generate a consistent cell ID from coordinates or provided ID"""
    if cell_item.cell_id:
        return cell_item.cell_id
    
    # Format coordinates to match previous behavior (no .0 for integers)
    x_str = f"{int(cell_item.x)}" if cell_item.x == int(cell_item.x) else f"{cell_item.x}"
    y_str = f"{int(cell_item.y)}" if cell_item.y == int(cell_item.y) else f"{cell_item.y}"
    return f"cell_{level}_{x_str}_{y_str}"

def _process_crowd_density_event(event: CrowdDensityEvent):
    """Process grid data and update store for a crowd density event"""
    print(f"[MQTT] Processing crowd_density event from {event.metadata.get('camera_id', 'unknown')}")
    
    cam_id = event.metadata.get('camera_id', 'unknown_cam')
    timestamp = datetime.now() 
    level = event.level
    
    updated_cells = []
    
    for cell_item in event.grid_data:
        cell_id = _get_cell_id(cell_item, level)
        
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

def on_message(client, userdata, msg):
    """Process incoming MQTT messages with Pydantic validation"""
    try:
        payload = msg.payload.decode('utf-8')
        data_dict = json.loads(payload)

        # Use Pydantic model for validation
        event = CrowdDensityEvent.model_validate(data_dict)
        
        if event.event_type == 'crowd_density':
            _process_crowd_density_event(event)

    except Exception as e:
        print(f"[SIMULATOR] Error processing message: {e}")

def publish_to_clients(congestion_data: CellCongestionData):
    """Publish congestion data to client broker"""
    try:
        payload = congestion_data.model_dump_json()
        client_publisher.publish(CLIENT_TOPIC, payload, qos=1)
        print(f"[CLIENT] Published to {CLIENT_TOPIC}: {congestion_data.cell_id} (congestion: {congestion_data.congestion_level:.2f})")
    except Exception as e:
        print(f"[CLIENT] Error publishing: {e}")

# Clients Setup
simulator_client = mqtt.Client(client_id="congestion_service_receiver")
simulator_client.on_message = on_message
_configure_mqtt_tls(simulator_client)

client_publisher = mqtt.Client(client_id="congestion_service_publisher")
_configure_mqtt_tls(client_publisher)


def start_mqtt(sim_client=None, pub_client=None):
    """Start MQTT clients"""
    sim_client = sim_client or simulator_client
    pub_client = pub_client or client_publisher
    try:
        sim_client.connect(SIMULATOR_BROKER, SIMULATOR_PORT, 60)
        sim_client.subscribe(SIMULATOR_TOPIC)
        sim_client.loop_start()
        
        pub_client.connect(CLIENT_BROKER, CLIENT_PORT, 60)
        pub_client.loop_start()
        print("[MQTT] Services Started")
    except Exception as e:
        print(f"[MQTT] Failed to start: {e}")

def stop_mqtt(sim_client=None, pub_client=None):
    """Stop MQTT clients"""
    sim_client = sim_client or simulator_client
    pub_client = pub_client or client_publisher
    sim_client.loop_stop()
    sim_client.disconnect()
    pub_client.loop_stop()
    pub_client.disconnect()
    print("[MQTT] Services Stopped")