import os

# Client broker configuration (for publishing congestion data to clients)
CLIENT_BROKER = os.getenv("MQTT_BROKER", "localhost")
CLIENT_PORT = int(os.getenv("MQTT_PORT", "1885"))
CLIENT_TOPIC = os.getenv("CLIENT_TOPIC", "stadium/services/congestion")

# Simulator broker configuration (for receiving events from stadium simulator)
SIMULATOR_BROKER = os.getenv("SIMULATOR_BROKER", "localhost")
SIMULATOR_PORT = int(os.getenv("SIMULATOR_PORT", "1883"))
SIMULATOR_TOPIC = os.getenv("SIMULATOR_TOPIC", "stadium/events/congestion")