import uvicorn
from api_handler import app

if __name__ == "__main__":
    # The MQTT initialization is now handled by FastAPI's startup event in api_handler.py
    # This ensures it works both when running directly and when run by Docker/Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
