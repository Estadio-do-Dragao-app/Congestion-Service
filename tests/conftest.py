import pytest
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(autouse=True)
def mock_mqtt():
    with patch('mqtt_handler.start_mqtt'):
        yield


@pytest.fixture(autouse=True)
def reset_mqtt_store():
    yield
    try:
        import mqtt_handler
        mqtt_handler.cell_congestion_store.clear()
    except:
        pass