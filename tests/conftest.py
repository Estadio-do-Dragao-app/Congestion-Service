"""
Pytest configuration and shared fixtures
"""
import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(autouse=True)
def reset_mqtt_handler():
    """Reset MQTT handler state between tests"""
    import mqtt_handler
    mqtt_handler.cell_congestion_store = None
    yield
    mqtt_handler.cell_congestion_store = None


@pytest.fixture(autouse=True)
def reset_api_handler():
    """Reset API handler state between tests"""
    import api_handler
    api_handler.cell_congestion_store.clear()
    api_handler.first_update_time = None
    yield
    api_handler.cell_congestion_store.clear()
    api_handler.first_update_time = None
