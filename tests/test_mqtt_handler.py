"""
Test suite for MQTT handler
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
import json
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
from models import CellCongestionData
import mqtt_handler


@pytest.fixture
def mock_store():
    """Create a mock store dictionary"""
    return {}


@pytest.fixture
def mock_mqtt_client():
    """Create a mock MQTT client"""
    return Mock()


@pytest.fixture
def mock_message():
    """Create a mock MQTT message"""
    msg = Mock()
    msg.topic = "test/topic"
    return msg


class TestOnSimulatorConnect:
    """Test on_simulator_connect callback"""
    
    def test_successful_connection(self, mock_mqtt_client, capsys):
        """Test successful connection to simulator broker"""
        mqtt_handler.on_simulator_connect(mock_mqtt_client, None, None, 0)
        
        # Check that subscribe was called
        mock_mqtt_client.subscribe.assert_called_once()
        
        # Check output
        captured = capsys.readouterr()
        assert "[SIMULATOR] Connected to broker" in captured.out
        assert "[SIMULATOR] Subscribed to topic" in captured.out
    
    def test_failed_connection(self, mock_mqtt_client, capsys):
        """Test failed connection to simulator broker"""
        mqtt_handler.on_simulator_connect(mock_mqtt_client, None, None, 1)
        
        # Check that subscribe was NOT called
        mock_mqtt_client.subscribe.assert_not_called()
        
        # Check output
        captured = capsys.readouterr()
        assert "[SIMULATOR] Connection failed with code 1" in captured.out


class TestOnClientConnect:
    """Test on_client_connect callback"""
    
    def test_successful_connection(self, mock_mqtt_client, capsys):
        """Test successful connection to client broker"""
        mqtt_handler.on_client_connect(mock_mqtt_client, None, None, 0)
        
        captured = capsys.readouterr()
        assert "[CLIENT] Connected to broker" in captured.out
    
    def test_failed_connection(self, mock_mqtt_client, capsys):
        """Test failed connection to client broker"""
        mqtt_handler.on_client_connect(mock_mqtt_client, None, None, 5)
        
        captured = capsys.readouterr()
        assert "[CLIENT] Connection failed with code 5" in captured.out


class TestProcessGridCell:
    """Test process_grid_cell helper function"""
    
    def test_process_cell_with_cell_id(self):
        """Test processing cell data with explicit cell_id"""
        cell_data = {
            "cell_id": "test_cell",
            "count": 25
        }
        timestamp = datetime.now().isoformat()
        
        result = mqtt_handler.process_grid_cell(cell_data, level=0, timestamp=timestamp)
        
        assert isinstance(result, CellCongestionData)
        assert result.cell_id == "test_cell"
        assert result.people_count == 25
        assert result.congestion_level == 0.5  # 25/50
        assert result.capacity == 50
        assert result.level == 0
    
    def test_process_cell_without_cell_id(self):
        """Test processing cell data without explicit cell_id (generates from x,y)"""
        cell_data = {
            "x": 5,
            "y": 10,
            "count": 10
        }
        timestamp = datetime.now().isoformat()
        
        result = mqtt_handler.process_grid_cell(cell_data, level=2, timestamp=timestamp)
        
        assert result.cell_id == "cell_2_5_10"
        assert result.people_count == 10
        assert result.level == 2
    
    def test_process_cell_max_capacity(self):
        """Test processing cell at max capacity"""
        cell_data = {
            "cell_id": "full_cell",
            "count": 60  # Over capacity
        }
        timestamp = datetime.now().isoformat()
        
        result = mqtt_handler.process_grid_cell(cell_data, level=0, timestamp=timestamp)
        
        # Congestion should be capped at 1.0
        assert result.congestion_level == 1.0
        assert result.people_count == 60
    
    def test_process_cell_zero_count(self):
        """Test processing cell with zero count"""
        cell_data = {
            "cell_id": "empty_cell",
            "count": 0
        }
        timestamp = datetime.now().isoformat()
        
        result = mqtt_handler.process_grid_cell(cell_data, level=0, timestamp=timestamp)
        
        assert result.congestion_level == 0.0
        assert result.people_count == 0


class TestProcessCrowdDensityEvent:
    """Test process_crowd_density_event helper function"""
    
    @patch('mqtt_handler.publish_to_clients')
    def test_process_crowd_density_event(self, mock_publish, mock_store, capsys):
        """Test processing crowd density event"""
        mqtt_handler.cell_congestion_store = mock_store
        
        data_dict = {
            "event_type": "crowd_density",
            "level": 1,
            "timestamp": datetime.now().isoformat(),
            "grid_data": [
                {"cell_id": "cell_1", "count": 10},
                {"cell_id": "cell_2", "count": 30},
                {"x": 0, "y": 0, "count": 20}
            ]
        }
        
        mqtt_handler.process_crowd_density_event(data_dict)
        
        # Check that cells were stored
        assert len(mock_store) == 3
        assert "cell_1" in mock_store
        assert "cell_2" in mock_store
        assert "cell_1_0_0" in mock_store
        
        # Check publish was called for each cell
        assert mock_publish.call_count == 3
        
        # Check output
        captured = capsys.readouterr()
        assert "[SIMULATOR] Received crowd_density event with 3 cells" in captured.out
        assert "[SIMULATOR] Processed and stored 3 cells" in captured.out
    
    @patch('mqtt_handler.publish_to_clients')
    def test_process_empty_grid_data(self, mock_publish, mock_store, capsys):
        """Test processing event with empty grid_data"""
        mqtt_handler.cell_congestion_store = mock_store
        
        data_dict = {
            "event_type": "crowd_density",
            "grid_data": []
        }
        
        mqtt_handler.process_crowd_density_event(data_dict)
        
        assert len(mock_store) == 0
        mock_publish.assert_not_called()


class TestProcessLegacyCongestionData:
    """Test process_legacy_congestion_data helper function"""
    
    @patch('mqtt_handler.publish_to_clients')
    def test_process_legacy_data_with_timestamp(self, mock_publish, mock_store, capsys):
        """Test processing legacy data format with timestamp"""
        mqtt_handler.cell_congestion_store = mock_store
        
        data_dict = {
            "cell_id": "legacy_cell",
            "congestion_level": 0.6,
            "people_count": 30,
            "level": 0,
            "timestamp": datetime.now()
        }
        
        mqtt_handler.process_legacy_congestion_data(data_dict)
        
        assert "legacy_cell" in mock_store
        assert mock_store["legacy_cell"].congestion_level == 0.6
        mock_publish.assert_called_once()
    
    @patch('mqtt_handler.publish_to_clients')
    def test_process_legacy_data_without_timestamp(self, mock_publish, mock_store, capsys):
        """Test processing legacy data format without timestamp (adds default)"""
        mqtt_handler.cell_congestion_store = mock_store
        
        data_dict = {
            "cell_id": "legacy_cell_2",
            "congestion_level": 0.4,
            "level": 0
        }
        
        mqtt_handler.process_legacy_congestion_data(data_dict)
        
        assert "legacy_cell_2" in mock_store
        assert isinstance(mock_store["legacy_cell_2"].timestamp, datetime)
        mock_publish.assert_called_once()
    
    @patch('mqtt_handler.publish_to_clients')
    def test_process_legacy_data_store_not_initialized(self, mock_publish, capsys):
        """Test processing legacy data when store is None"""
        mqtt_handler.cell_congestion_store = None
        
        data_dict = {
            "cell_id": "test_cell",
            "congestion_level": 0.5,
            "level": 0
        }
        
        mqtt_handler.process_legacy_congestion_data(data_dict)
        
        # Should not publish if store is None
        mock_publish.assert_not_called()
        
        # Check warning message
        captured = capsys.readouterr()
        assert "[SIMULATOR] Warning: Storage not initialized yet" in captured.out


class TestOnMessage:
    """Test on_message callback"""
    
    @patch('mqtt_handler.process_crowd_density_event')
    def test_on_message_crowd_density(self, mock_process_crowd, mock_mqtt_client, mock_message):
        """Test on_message with crowd_density event"""
        payload_data = {
            "event_type": "crowd_density",
            "grid_data": [{"cell_id": "cell_1", "count": 10}]
        }
        mock_message.payload = json.dumps(payload_data).encode('utf-8')
        
        mqtt_handler.on_message(mock_mqtt_client, None, mock_message)
        
        mock_process_crowd.assert_called_once()
        call_args = mock_process_crowd.call_args[0][0]
        assert call_args["event_type"] == "crowd_density"
    
    @patch('mqtt_handler.process_legacy_congestion_data')
    def test_on_message_legacy_format(self, mock_process_legacy, mock_mqtt_client, mock_message):
        """Test on_message with legacy format"""
        payload_data = {
            "cell_id": "cell_1",
            "congestion_level": 0.5,
            "level": 0
        }
        mock_message.payload = json.dumps(payload_data).encode('utf-8')
        
        mqtt_handler.on_message(mock_mqtt_client, None, mock_message)
        
        mock_process_legacy.assert_called_once()
        call_args = mock_process_legacy.call_args[0][0]
        assert call_args["cell_id"] == "cell_1"
    
    def test_on_message_invalid_json(self, mock_mqtt_client, mock_message, capsys):
        """Test on_message with invalid JSON"""
        mock_message.payload = b"invalid json"
        
        mqtt_handler.on_message(mock_mqtt_client, None, mock_message)
        
        captured = capsys.readouterr()
        assert "[SIMULATOR] JSON decode error" in captured.out
    
    def test_on_message_exception_handling(self, mock_mqtt_client, mock_message, capsys):
        """Test on_message handles exceptions gracefully"""
        payload_data = {
            "cell_id": "test",
            "congestion_level": "invalid"  # Should cause validation error
        }
        mock_message.payload = json.dumps(payload_data).encode('utf-8')
        
        mqtt_handler.on_message(mock_mqtt_client, None, mock_message)
        
        captured = capsys.readouterr()
        assert "[SIMULATOR] Error processing message" in captured.out


class TestPublishToClients:
    """Test publish_to_clients function"""
    
    @patch('mqtt_handler.client_publisher')
    def test_publish_successful(self, mock_publisher, capsys):
        """Test successful publish to client broker"""
        data = CellCongestionData(
            cell_id="test_cell",
            congestion_level=0.7,
            level=0
        )
        
        mqtt_handler.publish_to_clients(data)
        
        # Check that publish was called
        mock_publisher.publish.assert_called_once()
        call_args = mock_publisher.publish.call_args
        assert call_args[1]["qos"] == 1
        
        # Check output
        captured = capsys.readouterr()
        assert "[CLIENT] Published to topic" in captured.out
        assert "test_cell" in captured.out
    
    @patch('mqtt_handler.client_publisher')
    def test_publish_error_handling(self, mock_publisher, capsys):
        """Test publish error handling"""
        mock_publisher.publish.side_effect = Exception("Connection error")
        
        data = CellCongestionData(
            cell_id="test_cell",
            congestion_level=0.7,
            level=0
        )
        
        mqtt_handler.publish_to_clients(data)
        
        captured = capsys.readouterr()
        assert "[CLIENT] Error publishing" in captured.out


class TestStartMQTT:
    @patch('mqtt_handler.CLIENT_PORT', 1885)
    @patch('mqtt_handler.CLIENT_BROKER', 'localhost')
    @patch('mqtt_handler.SIMULATOR_PORT', 1883)
    @patch('mqtt_handler.SIMULATOR_BROKER', 'localhost')
    @patch('mqtt_handler.client_publisher')
    @patch('mqtt_handler.simulator_client')
    def test_start_mqtt_successful(self, mock_sim_client, mock_client_pub):
        """Test successful MQTT startup"""
        from mqtt_handler import start_mqtt
        mock_store = {}
        
        start_mqtt(mock_store)
        
        mock_sim_client.connect.assert_called_once_with('localhost', 1883, 60)
        mock_sim_client.loop_start.assert_called_once()
        mock_client_pub.connect.assert_called_once_with('localhost', 1885, 60)
        mock_client_pub.loop_start.assert_called_once()

    @patch('mqtt_handler.CLIENT_PORT', 1885)
    @patch('mqtt_handler.CLIENT_BROKER', 'localhost')
    @patch('mqtt_handler.SIMULATOR_PORT', 1883)
    @patch('mqtt_handler.SIMULATOR_BROKER', 'localhost')
    @patch('mqtt_handler.client_publisher')
    @patch('mqtt_handler.simulator_client')
    def test_start_mqtt_connection_error(self, mock_sim_client, mock_client_pub, capsys):
        """Test MQTT startup with connection error"""
        from mqtt_handler import start_mqtt
        mock_store = {}
        mock_sim_client.connect.side_effect = Exception("Connection refused")
        
        start_mqtt(mock_store)
        
        captured = capsys.readouterr()
        error_output = captured.out + captured.err
        # A mensagem de erro é impressa pela função start_mqtt
        assert "[MQTT] Failed to start" in error_output


class TestMQTTClients:
    """Test MQTT client initialization"""
    
    def test_simulator_client_callbacks(self):
        """Test simulator client has correct callbacks"""
        assert mqtt_handler.simulator_client.on_connect == mqtt_handler.on_simulator_connect
        assert mqtt_handler.simulator_client.on_message == mqtt_handler.on_message
    
    def test_client_publisher_callbacks(self):
        """Test client publisher has correct callbacks"""
        assert mqtt_handler.client_publisher.on_connect == mqtt_handler.on_client_connect


class TestIntegration:
    """Integration tests for MQTT handler"""
    
    @patch('mqtt_handler.publish_to_clients')
    def test_full_message_processing_flow(self, mock_publish, mock_mqtt_client, mock_message, mock_store):
        """Test complete message processing flow"""
        mqtt_handler.cell_congestion_store = mock_store
        
        # Create a complete crowd_density event
        payload_data = {
            "event_type": "crowd_density",
            "level": 0,
            "timestamp": datetime.now().isoformat(),
            "grid_data": [
                {"cell_id": "cell_A1", "count": 15},
                {"cell_id": "cell_A2", "count": 35},
                {"x": 2, "y": 3, "count": 25}
            ]
        }
        mock_message.payload = json.dumps(payload_data).encode('utf-8')
        
        # Process the message
        mqtt_handler.on_message(mock_mqtt_client, None, mock_message)
        
        # Verify storage
        assert len(mock_store) == 3
        assert mock_store["cell_A1"].people_count == 15
        assert mock_store["cell_A2"].people_count == 35
        assert mock_store["cell_0_2_3"].people_count == 25
        
        # Verify congestion calculations
        assert mock_store["cell_A1"].congestion_level == 0.3
        assert mock_store["cell_A2"].congestion_level == 0.7
        assert mock_store["cell_0_2_3"].congestion_level == 0.5
        
        # Verify publishing
        assert mock_publish.call_count == 3
