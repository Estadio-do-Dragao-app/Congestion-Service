"""
Test suite for MQTT handler (real implementation)
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime
from schemas import CellCongestionData
import mqtt_handler


@pytest.fixture
def clear_store():
    mqtt_handler.cell_congestion_store.clear()
    yield
    mqtt_handler.cell_congestion_store.clear()


class TestAggregateCellData:
    def test_no_data(self, clear_store):
        result = mqtt_handler.aggregate_cell_data("nonexistent", level=0)
        assert result is None

    def test_single_camera_data(self, clear_store):
        mqtt_handler.cell_congestion_store["cell_1"]["cam1"] = {
            "count": 25,
            "timestamp": datetime.now(),
            "level": 0
        }
        result = mqtt_handler.aggregate_cell_data("cell_1", level=0)
        assert result is not None
        assert result.cell_id == "cell_1"
        assert result.people_count == 25
        assert result.congestion_level == 25/50
        assert result.level == 0

    def test_multiple_cameras_max(self, clear_store):
        mqtt_handler.cell_congestion_store["cell_1"]["cam1"] = {"count": 30, "timestamp": datetime.now(), "level": 0}
        mqtt_handler.cell_congestion_store["cell_1"]["cam2"] = {"count": 45, "timestamp": datetime.now(), "level": 0}
        result = mqtt_handler.aggregate_cell_data("cell_1", level=0)
        assert result.people_count == 45
        assert result.congestion_level == 45/50

    def test_stale_data_removal(self, clear_store):
        from datetime import timedelta
        stale_time = datetime.now() - timedelta(seconds=20)
        mqtt_handler.cell_congestion_store["cell_1"]["cam1"] = {"count": 10, "timestamp": stale_time, "level": 0}
        result = mqtt_handler.aggregate_cell_data("cell_1", level=0)
        assert result is None
        assert "cell_1" not in mqtt_handler.cell_congestion_store or not mqtt_handler.cell_congestion_store["cell_1"]


class TestOnMessage:
    @patch('mqtt_handler.publish_to_clients')
    def test_crowd_density_event(self, mock_publish, clear_store):
        payload = {
            "event_type": "crowd_density",
            "level": 1,
            "metadata": {"camera_id": "cam_test"},
            "grid_data": [
                {"cell_id": "cell_A", "count": 20},
                {"x": 5, "y": 5, "count": 30}
            ]
        }
        msg = Mock()
        msg.payload = json.dumps(payload).encode()

        mqtt_handler.on_message(None, None, msg)

        assert "cell_A" in mqtt_handler.cell_congestion_store
        assert "cell_1_5_5" in mqtt_handler.cell_congestion_store
        assert mock_publish.call_count == 2

    def test_invalid_json(self, clear_store, capsys):
        msg = Mock()
        msg.payload = b"not json"
        mqtt_handler.on_message(None, None, msg)
        captured = capsys.readouterr()
        assert "Error processing message" in captured.out


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
        assert kwargs['qos'] == 1
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