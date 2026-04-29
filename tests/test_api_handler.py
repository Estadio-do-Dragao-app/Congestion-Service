import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def client():
    with patch('mqtt_handler.start_mqtt'):
        from api_handler import app
        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture
def clear_store():
    import mqtt_handler
    mqtt_handler.cell_congestion_store.clear()
    yield
    mqtt_handler.cell_congestion_store.clear()


@pytest.fixture
def populate_store(clear_store):
    import mqtt_handler
    for i in range(5):
        cell_id = f"cell_{i}"
        cam_id = f"cam_{i}"
        mqtt_handler.cell_congestion_store[cell_id][cam_id] = {
            "count": i * 10,
            "timestamp": datetime.now(),
            "level": 0
        }
    yield
    mqtt_handler.cell_congestion_store.clear()


class TestGetCellHeatmap:
    def test_get_existing_cell(self, client, populate_store):
        response = client.get("/heatmap/cell/cell_1")
        assert response.status_code == 200
        data = response.json()
        assert data["section_id"] == "cell_1"
        assert "congestion_level" in data
        assert "timestamp" in data
        assert "cells" in data
        assert len(data["cells"]) == 1

    def test_get_nonexistent_cell(self, client, clear_store):
        response = client.get("/heatmap/cell/nonexistent")
        assert response.status_code == 404
        assert "No active camera data found" in response.json()["detail"]


class TestGetStadiumCellHeatmap:
    def test_get_stadium_heatmap_with_data(self, client, populate_store):
        response = client.get("/heatmap/stadium/cells")
        assert response.status_code == 200
        data = response.json()
        assert data["total_cells"] == 5
        assert "average_congestion" in data
        assert len(data["cells"]) == 5

    def test_get_stadium_heatmap_empty(self, client, clear_store):
        response = client.get("/heatmap/stadium/cells")
        assert response.status_code == 404
        assert "No active congestion data available" in response.json()["detail"]


class TestListSections:
    def test_list_sections_with_data(self, client, populate_store):
        response = client.get("/sections")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        assert all("section_id" in item for item in data)
        assert all("congestion_level" in item for item in data)

    def test_list_sections_empty(self, client, clear_store):
        response = client.get("/sections")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_sections_sorted_by_congestion(self, client, populate_store):
        response = client.get("/sections")
        data = response.json()
        levels = [item["congestion_level"] for item in data]
        assert levels == sorted(levels, reverse=True)


class TestHealthCheck:
    def test_health_check_with_data(self, client, populate_store):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["tracked_cells"] == 5
        assert data["service"] == "Smart Stadium Congestion Service (Aggregated)"

    def test_health_check_empty(self, client, clear_store):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["tracked_cells"] == 0