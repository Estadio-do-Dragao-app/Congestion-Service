import pytest
from datetime import datetime, timedelta
import store
from schemas import MAX_CELL_CAPACITY

@pytest.fixture
def clear_store():
    store.cell_congestion_store.clear()
    yield
    store.cell_congestion_store.clear()

class TestAggregateCellData:
    def test_no_data(self, clear_store):
        result = store.aggregate_cell_data("nonexistent", level=0)
        assert result is None

    def test_single_camera_data(self, clear_store):
        store.cell_congestion_store["cell_1"]["cam1"] = {
            "count": 25,
            "timestamp": datetime.now(),
            "level": 0
        }
        result = store.aggregate_cell_data("cell_1", level=0)
        assert result is not None
        assert result.cell_id == "cell_1"
        assert result.people_count == 25
        assert result.congestion_level == 25/MAX_CELL_CAPACITY

    def test_multiple_cameras_max(self, clear_store):
        store.cell_congestion_store["cell_1"]["cam1"] = {"count": 10, "timestamp": datetime.now(), "level": 0}
        store.cell_congestion_store["cell_1"]["cam2"] = {"count": 40, "timestamp": datetime.now(), "level": 0}
        result = store.aggregate_cell_data("cell_1", level=0)
        assert result.people_count == 40
        assert result.congestion_level == 40/MAX_CELL_CAPACITY

    def test_stale_data_removal(self, clear_store):
        stale_time = datetime.now() - timedelta(seconds=store.CAMERA_TTL + 1)
        store.cell_congestion_store["cell_1"]["cam1"] = {"count": 10, "timestamp": stale_time, "level": 0}
        result = store.aggregate_cell_data("cell_1", level=0)
        assert result is None
        assert "cell_1" not in store.cell_congestion_store

class TestGetAllAggregatedCells:
    def test_empty_store(self, clear_store):
        assert store.get_all_aggregated_cells() == []

    def test_populated_store(self, clear_store):
        store.cell_congestion_store["cell_1"]["cam1"] = {"count": 20, "timestamp": datetime.now(), "level": 1}
        store.cell_congestion_store["cell_2"]["cam1"] = {"count": 30, "timestamp": datetime.now(), "level": 2}
        
        results = store.get_all_aggregated_cells()
        assert len(results) == 2
        ids = [r.cell_id for r in results]
        assert "cell_1" in ids
        assert "cell_2" in ids

    def test_get_all_with_empty_entry(self, clear_store):
        # Manually insert an empty dict for a cell
        store.cell_congestion_store["empty_cell"] = {}
        store.cell_congestion_store["active_cell"]["cam1"] = {"count": 10, "timestamp": datetime.now(), "level": 0}
        
        results = store.get_all_aggregated_cells()
        assert len(results) == 1
        assert results[0].cell_id == "active_cell"
        # Verify empty cell was cleaned up
        assert "empty_cell" not in store.cell_congestion_store
