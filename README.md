# Congestion-Service

A real-time congestion monitoring service for smart stadiums that receives congestion events from the Stadium-Event-Generator via MQTT and publishes congestion data to connected clients through its own MQTT broker.

## 🏗️ Architecture

```
Stadium-Event-Generator → [MQTT Port 1883] → Congestion Service
                                                    ↓
                                           [MQTT Port 1885]
                                                    ↓
                                                Clients
```

The service:
1. **Receives** congestion events from Stadium-Event-Generator broker (port 1883) on `stadium/events/congestion`
2. **Processes** and stores congestion data per cell
3. **Publishes** congestion updates to clients via its own broker (port 1885) on `stadium/services/congestion`
4. **Exposes** REST API for querying current congestion status

## 🚀 Quick Start

### Prerequisites
- Stadium-Event-Generator must be running (provides MQTT broker on port 1883)
- Docker and Docker Compose installed

### Option 1: Docker Compose (Recommended)

```bash
# Start the Stadium-Event-Generator first (if not already running)
cd ../Stadium-Event-Generator
docker-compose up -d

# Start Congestion-Service with its own Mosquitto broker
cd ../Congestion-Service
docker-compose up -d

# View logs
docker-compose logs -f congestion-service

# Stop the service
docker-compose down
```

### Option 2: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure Stadium-Event-Generator broker is running on port 1883

# Start Congestion-Service's own Mosquitto broker (in separate terminal)
docker run -p 1885:1883 -p 9003:9001 eclipse-mosquitto:2.0

# Run the service
python main.py
```

## 📡 MQTT Brokers & Topics

### Simulator Broker (Port 1883 - Stadium-Event-Generator)
| Topic | Direction | Description |
|-------|-----------|-------------|
| `stadium/events/congestion` | Simulator → Congestion Service | Congestion events from stadium |

### Client Broker (Port 1885 - Congestion Service)
| Topic | Direction | Description |
|-------|-----------|-------------|
| `stadium/services/congestion` | Congestion Service → Clients | Real-time congestion updates |

### WebSocket Ports
- Client connections: `ws://localhost:9003`
- Simulator broker: `ws://localhost:9001`

## 🔌 Client Connection Example

```python
import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to Congestion Service")
        client.subscribe("stadium/services/congestion")

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    print(f"Cell {data['cell_id']}: {data['congestion_level']}% congestion")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Connect to Congestion-Service client broker
client.connect("localhost", 1885, 60)
client.loop_forever()
```

## 🌐 REST API

The service also exposes a REST API for querying congestion data:

- `GET /health` - Health check
- `GET /heatmap/stadium/cells` - Get congestion data for all stadium cells
- `GET /heatmap/cell/{cell_id}` - Get congestion data for a specific cell
- `GET /sections` - Get congestion data aggregated by stadium section

## 📦 Project Structure

```
Congestion-Service/
├── main.py              # Main FastAPI application
├── api_handler.py       # REST API endpoints
├── mqtt_handler.py      # Dual MQTT broker handler
├── mqtt_configs.py      # MQTT configuration
├── models.py            # Data models
├── requirements.txt     # Dependencies
├── docker-compose.yml   # Docker Compose configuration
├── Dockerfile           # Docker image
└── mosquitto/          # Mosquitto broker configuration
    ├── config/
    │   └── mosquitto.conf
    ├── data/
    └── log/
```

## 🔧 Configuration

Environment variables (set in `docker-compose.yml` or `.env`):

- `SIMULATOR_BROKER` - Hostname of Stadium-Event-Generator broker (default: `localhost`)
- `SIMULATOR_PORT` - Port of Stadium-Event-Generator broker (default: `1883`)
- `MQTT_BROKER` - Hostname of Congestion-Service's own broker (default: `mosquitto`)
- `MQTT_PORT` - Internal port for Congestion-Service broker (default: `1883`, mapped to external `1885`)

## 📝 Notes

- The service maintains dual MQTT connections: one for receiving simulator events, one for publishing to clients
- Congestion data is stored in-memory for quick API access
- All brokers allow anonymous connections for development purposes
- Production deployments should implement authentication and authorization
