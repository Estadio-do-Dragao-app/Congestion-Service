import pytest
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(autouse=True)
def mock_mqtt(request):
    # Do not mock MQTT for mqtt_handler lifecycle tests
    if "test_mqtt_handler.py" in request.node.nodeid:
        yield
    else:
        with patch('mqtt_handler.start_mqtt'), patch('mqtt_handler.stop_mqtt'):
            yield


@pytest.fixture(autouse=True)
def reset_store():
    yield
    try:
        import store
        store.cell_congestion_store.clear()
    except:
        pass