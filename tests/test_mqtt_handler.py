"""
Test suite for MQTT handler
"""
import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime
from schemas import CellCongestionData
import mqtt_handler
import store

@pytest.fixture
def clear_store():
    store.cell_congestion_store.clear()
    yield
    store.cell_congestion_store.clear()

class TestOnMessage:
    @patch('mqtt_handler.publish_to_clients')
    def test_crowd_density_event_valid(self, mock_publish, clear_store):
        payload = {
            "event_type": "crowd_density",
            "level": 1,
            "timestamp": datetime.now().isoformat(),
            "total_people": 50,
            "metadata": {"camera_id": "cam_test"},
            "grid_data": [
                {"cell_id": "cell_A", "x": 1.0, "y": 2.0, "count": 20},
                {"x": 5.0, "y": 5.0, "count": 30}
            ]
        }
        msg = Mock()
        msg.payload = json.dumps(payload).encode()

        mqtt_handler.on_message(None, None, msg)

        assert "cell_A" in store.cell_congestion_store
        assert "cell_1_5_5" in store.cell_congestion_store
        assert mock_publish.call_count == 2

    def test_invalid_json(self, clear_store, capsys):
        msg = Mock()
        msg.payload = b"not json"
        mqtt_handler.on_message(None, None, msg)
        captured = capsys.readouterr()
        assert "Error processing message" in captured.out

    @patch('mqtt_handler.publish_to_clients')
    def test_missing_required_fields(self, mock_publish, clear_store, capsys):
        payload = {"event_type": "crowd_density"} # Missing grid_data, etc.
        msg = Mock()
        msg.payload = json.dumps(payload).encode()
        
        mqtt_handler.on_message(None, None, msg)
        captured = capsys.readouterr()
        assert "Error processing message" in captured.out
        assert mock_publish.call_count == 0

class TestPublishToClients:
    @patch('mqtt_handler.client_publisher')
    def test_publish_success(self, mock_publisher, capsys):
        data = CellCongestionData(
            cell_id="test",
            congestion_level=0.6,
            people_count=30,
            level=0,
            camera_id="cam1",
            timestamp=datetime.now()
        )
        mqtt_handler.publish_to_clients(data)
        mock_publisher.publish.assert_called_once()
        args, kwargs = mock_publisher.publish.call_args
        assert "test" in args[1]

    @patch('mqtt_handler.client_publisher')
    def test_publish_error(self, mock_publisher, capsys):
        mock_publisher.publish.side_effect = Exception("Broken")
        data = CellCongestionData(
            cell_id="test",
            congestion_level=0.5,
            level=0,
            camera_id="cam1",
            people_count=25,
            timestamp=datetime.now()
        )
        mqtt_handler.publish_to_clients(data)
        captured = capsys.readouterr()
        assert "Error publishing" in captured.out