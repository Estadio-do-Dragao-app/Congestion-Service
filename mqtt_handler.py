import json
import paho.mqtt.client as mqtt
from models import CellCongestionData
from mqtt_configs import BROKER, PORT, TOPIC


def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with result code {rc}")
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    pass

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

def start_mqtt():
    client.connect(BROKER, PORT, 60)
    client.loop_start()