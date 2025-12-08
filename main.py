import uvicorn
from api_handler import app, cell_congestion_store
from mqtt_handler import start_mqtt

if __name__ == "__main__":
    print("=" * 60)
    print("Smart Stadium Congestion Service")
    print("=" * 60)
    
    # Start MQTT handler with reference to storage
    print("\n[STARTUP] Initializing MQTT Handler...")
    start_mqtt(cell_congestion_store)
    
    # Start FastAPI server
    print("[STARTUP] Starting FastAPI Server...")
    print("[STARTUP] API available at: http://localhost:8000")
    print("[STARTUP] API Documentation: http://localhost:8000/docs")
    print("\n" + "=" * 60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
