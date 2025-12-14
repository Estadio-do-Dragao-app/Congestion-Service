"""
Test suite for API handler endpoints
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    """Create test client"""
    # Mock the MQTT startup to prevent it from running
    with patch('mqtt_handler.start_mqtt'):
        from starlette.testclient import TestClient
        from api_handler import app
        
        client = TestClient(app)
        yield client


@pytest.fixture
def cell_congestion_store():
    """Get reference to the store"""
    from api_handler import cell_congestion_store
    return cell_congestion_store


@pytest.fixture
def clear_store(cell_congestion_store):
    """Clear the congestion store before each test"""
    cell_congestion_store.clear()
    yield
    cell_congestion_store.clear()


@pytest.fixture
def sample_cell_data():
    """Sample cell congestion data"""
    return {
        "cell_id": "cell_1",
        "congestion_level": 0.5,
        "people_count": 25,
        "level": 0,
        "capacity": 50
    }


@pytest.fixture
def populate_store(cell_congestion_store):
    """Populate store with sample data"""
    from models import CellCongestionData
    
    cell_congestion_store.clear()
    for i in range(5):
        data = CellCongestionData(
            cell_id=f"cell_{i}",
            congestion_level=i * 0.2,
            people_count=i * 10,
            level=0,
            capacity=50
        )
        cell_congestion_store[data.cell_id] = data
    yield
    cell_congestion_store.clear()


class TestRootEndpoint:
    """Test root endpoint"""
    
    def test_root_returns_service_info(self, client):
        """Test root endpoint returns service information"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Smart Stadium Congestion Service"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data


class TestSubmitCongestionData:
    """Test POST /congestion endpoint"""
    
    def test_submit_valid_congestion_data(self, client, clear_store, sample_cell_data):
        """Test submitting valid congestion data"""
        response = client.post("/congestion", json=sample_cell_data)
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Cell Congestion data received successfully"
        assert data["cell_id"] == "cell_1"
        assert data["congestion_level"] == 0.5
        assert "timestamp" in data
    
    def test_submit_stores_data(self, client, clear_store, sample_cell_data, cell_congestion_store):
        """Test that submitted data is stored"""
        client.post("/congestion", json=sample_cell_data)
        assert "cell_1" in cell_congestion_store
        assert cell_congestion_store["cell_1"].cell_id == "cell_1"
    
    def test_submit_invalid_congestion_level(self, client, clear_store):
        """Test submitting invalid congestion level"""
        invalid_data = {
            "cell_id": "cell_1",
            "congestion_level": 1.5,  # Invalid: > 1.0
            "level": 0
        }
        response = client.post("/congestion", json=invalid_data)
        assert response.status_code == 422
    
    def test_submit_missing_required_field(self, client, clear_store):
        """Test submitting data with missing required field"""
        invalid_data = {
            "congestion_level": 0.5
            # Missing cell_id
        }
        response = client.post("/congestion", json=invalid_data)
        assert response.status_code == 422
    
    def test_submit_updates_existing_cell(self, client, clear_store, sample_cell_data, cell_congestion_store):
        """Test submitting data for existing cell updates it"""
        # First submission
        client.post("/congestion", json=sample_cell_data)
        
        # Second submission with different data
        updated_data = sample_cell_data.copy()
        updated_data["congestion_level"] = 0.8
        updated_data["people_count"] = 40
        
        response = client.post("/congestion", json=updated_data)
        assert response.status_code == 201
        assert cell_congestion_store["cell_1"].congestion_level == 0.8
        assert cell_congestion_store["cell_1"].people_count == 40


class TestGetCellHeatmap:
    """Test GET /heatmap/cell/{cell_id} endpoint"""
    
    def test_get_existing_cell(self, client, populate_store):
        """Test getting heatmap for existing cell"""
        response = client.get("/heatmap/cell/cell_1")
        assert response.status_code == 200
        data = response.json()
        assert data["section_id"] == "cell_1"
        assert "congestion_level" in data
        assert "timestamp" in data
    
    def test_get_nonexistent_cell(self, client, clear_store):
        """Test getting heatmap for non-existent cell"""
        response = client.get("/heatmap/cell/nonexistent")
        assert response.status_code == 404
        assert "No data found for cell" in response.json()["detail"]


class TestGetStadiumCellHeatmap:
    """Test GET /heatmap/stadium/cells endpoint"""
    
    def test_get_stadium_heatmap_with_data(self, client, populate_store):
        """Test getting stadium cell heatmap with data"""
        response = client.get("/heatmap/stadium/cells")
        assert response.status_code == 200
        data = response.json()
        assert data["total_cells"] == 5
        assert "average_congestion" in data
        assert "most_congested" in data
        assert "least_congested" in data
        assert len(data["cells"]) == 5
    
    def test_get_stadium_heatmap_empty(self, client, clear_store):
        """Test getting stadium cell heatmap when empty"""
        response = client.get("/heatmap/stadium/cells")
        assert response.status_code == 404
        assert "No congestion data available" in response.json()["detail"]
    
    def test_average_congestion_calculation(self, client, populate_store):
        """Test that average congestion is calculated correctly"""
        response = client.get("/heatmap/stadium/cells")
        data = response.json()
        # Expected average: (0.0 + 0.2 + 0.4 + 0.6 + 0.8) / 5 = 0.4
        assert data["average_congestion"] == pytest.approx(0.4, 0.01)
    
    def test_most_and_least_congested(self, client, populate_store):
        """Test most and least congested cells are identified"""
        response = client.get("/heatmap/stadium/cells")
        data = response.json()
        assert data["most_congested"] == "cell_4"  # 0.8 congestion
        assert data["least_congested"] == "cell_0"  # 0.0 congestion


class TestGetStadiumSectionsHeatmap:
    """Test GET /heatmap/stadium/sections endpoint"""
    
    def test_get_sections_heatmap_with_data(self, client, populate_store):
        """Test getting stadium sections heatmap with data"""
        response = client.get("/heatmap/stadium/sections")
        assert response.status_code == 200
        data = response.json()
        assert data["total_sections"] == 5
        assert len(data["sections"]) == 5
        assert "average_congestion" in data
    
    def test_get_sections_heatmap_empty(self, client, clear_store):
        """Test getting stadium sections heatmap when empty"""
        response = client.get("/heatmap/stadium/sections")
        assert response.status_code == 404
    
    def test_sections_dictionary_format(self, client, populate_store):
        """Test that sections are returned as dictionary"""
        response = client.get("/heatmap/stadium/sections")
        data = response.json()
        sections = data["sections"]
        assert isinstance(sections, dict)
        assert "cell_0" in sections
        assert sections["cell_0"] == 0.0


class TestListSections:
    """Test GET /sections endpoint"""
    
    def test_list_sections_with_data(self, client, populate_store):
        """Test listing sections with data"""
        response = client.get("/sections")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        assert all("section_id" in item for item in data)
        assert all("congestion_level" in item for item in data)
    
    def test_list_sections_empty(self, client, clear_store):
        """Test listing sections when empty"""
        response = client.get("/sections")
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_sections_sorted_by_congestion(self, client, populate_store):
        """Test that sections are sorted by congestion level (highest first)"""
        response = client.get("/sections")
        data = response.json()
        # Should be sorted highest to lowest
        assert data[0]["section_id"] == "cell_4"  # 0.8
        assert data[-1]["section_id"] == "cell_0"  # 0.0


class TestClearCellData:
    """Test DELETE /cell/{cell_id} endpoint"""
    
    def test_clear_existing_cell(self, client, populate_store, cell_congestion_store):
        """Test clearing data for existing cell"""
        assert "cell_1" in cell_congestion_store
        response = client.delete("/cell/cell_1")
        assert response.status_code == 200
        assert "cleared successfully" in response.json()["message"]
        assert "cell_1" not in cell_congestion_store
    
    def test_clear_nonexistent_cell(self, client, clear_store):
        """Test clearing data for non-existent cell"""
        response = client.delete("/cell/nonexistent")
        assert response.status_code == 404
        assert "Cell not found" in response.json()["detail"]


class TestClearSectionData:
    """Test DELETE /section/{section_id} endpoint"""
    
    def test_clear_existing_section(self, client, populate_store, cell_congestion_store):
        """Test clearing data for existing section"""
        assert "cell_2" in cell_congestion_store
        response = client.delete("/section/cell_2")
        assert response.status_code == 200
        assert "cleared successfully" in response.json()["message"]
        assert "cell_2" not in cell_congestion_store
    
    def test_clear_nonexistent_section(self, client, clear_store):
        """Test clearing data for non-existent section"""
        response = client.delete("/section/nonexistent")
        assert response.status_code == 404
        assert "Section not found" in response.json()["detail"]


class TestClearAllData:
    """Test DELETE /stadium endpoint"""
    
    def test_clear_all_data(self, client, populate_store, cell_congestion_store):
        """Test clearing all stadium data"""
        assert len(cell_congestion_store) == 5
        response = client.delete("/stadium")
        assert response.status_code == 200
        data = response.json()
        assert data["sections_cleared"] == 5
        assert len(cell_congestion_store) == 0
    
    def test_clear_all_data_when_empty(self, client, clear_store):
        """Test clearing all data when already empty"""
        response = client.delete("/stadium")
        assert response.status_code == 200
        data = response.json()
        assert data["sections_cleared"] == 0


class TestHealthCheck:
    """Test GET /health endpoint"""
    
    def test_health_check_with_data(self, client, populate_store):
        """Test health check with data in store"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["tracked_cells"] == 5
        assert "average_congestion" in data
        assert "service_uptime" in data
    
    def test_health_check_empty(self, client, clear_store):
        """Test health check when store is empty"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["tracked_cells"] == 0
        assert data["average_congestion"] == 0.0
    
    def test_health_check_average_calculation(self, client, populate_store):
        """Test health check calculates average correctly"""
        response = client.get("/health")
        data = response.json()
        # Expected average: (0.0 + 0.2 + 0.4 + 0.6 + 0.8) / 5 = 0.4
        assert data["average_congestion"] == pytest.approx(0.4, 0.01)


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_multiple_submissions_same_cell(self, client, clear_store, sample_cell_data, cell_congestion_store):
        """Test multiple submissions for the same cell"""
        for i in range(10):
            data = sample_cell_data.copy()
            data["congestion_level"] = i * 0.1
            client.post("/congestion", json=data)
        
        # Should only have one entry for cell_1
        assert len(cell_congestion_store) == 1
        assert cell_congestion_store["cell_1"].congestion_level == 0.9
    
    def test_max_congestion_level(self, client, clear_store):
        """Test cell with maximum congestion level"""
        data = {
            "cell_id": "full_cell",
            "congestion_level": 1.0,
            "level": 0
        }
        response = client.post("/congestion", json=data)
        assert response.status_code == 201
    
    def test_min_congestion_level(self, client, clear_store):
        """Test cell with minimum congestion level"""
        data = {
            "cell_id": "empty_cell",
            "congestion_level": 0.0,
            "level": 0
        }
        response = client.post("/congestion", json=data)
        assert response.status_code == 201
    
    def test_single_cell_heatmap(self, client, clear_store, cell_congestion_store):
        """Test stadium heatmap with single cell"""
        from models import CellCongestionData
        
        data = CellCongestionData(
            cell_id="only_cell",
            congestion_level=0.5,
            level=0
        )
        cell_congestion_store["only_cell"] = data
        
        response = client.get("/heatmap/stadium/cells")
        assert response.status_code == 200
        result = response.json()
        assert result["total_cells"] == 1
        assert result["average_congestion"] == 0.5
        assert result["most_congested"] == "only_cell"
        assert result["least_congested"] == "only_cell"
