"""
Pytest configuration and shared fixtures
"""
import pytest
import sys
import os
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(autouse=True)
def mock_mqtt():
    """Mock MQTT before any imports"""
    with patch('mqtt_handler.start_mqtt'):
        yield


@pytest.fixture(autouse=True)
def reset_mqtt_handler():
    """Reset MQTT handler state between tests"""
    yield
    # Cleanup after test
    try:
        import mqtt_handler
        mqtt_handler.cell_congestion_store = None
    except:
        pass


@pytest.fixture(autouse=True)
def reset_api_handler():
    """Reset API handler state between tests"""
    yield
    # Cleanup after test
    try:
        import api_handler
        api_handler.cell_congestion_store.clear()
        api_handler.first_update_time = None
    except:
        pass
    api_handler.cell_congestion_store.clear()
    api_handler.first_update_time = None
