"""
Test suite for data models
"""
import pytest
from datetime import datetime
from pydantic import ValidationError
from schemas import (
    CellCongestionData,
    SectionHeatmapResponse,
    StadiumHeatmapResponse,
)


class TestCellCongestionData:
    def test_valid_cell_congestion_data(self):
        data = CellCongestionData(
            cell_id="cell_1",
            congestion_level=0.5,
            people_count=25,
            level=0,
            capacity=50,
            camera_id="cam1",
            timestamp=datetime.now()
        )
        assert data.cell_id == "cell_1"
        assert data.congestion_level == 0.5
        assert data.people_count == 25
        assert data.level == 0
        assert data.capacity == 50
        assert data.camera_id == "cam1"
        assert isinstance(data.timestamp, datetime)

    def test_congestion_level_boundaries(self):
        data_min = CellCongestionData(
            cell_id="cell_1", congestion_level=0.0, camera_id="cam1",
            people_count=0, level=0, timestamp=datetime.now()
        )
        assert data_min.congestion_level == 0.0

        data_max = CellCongestionData(
            cell_id="cell_1", congestion_level=1.0, camera_id="cam1",
            people_count=50, level=0, timestamp=datetime.now()
        )
        assert data_max.congestion_level == 1.0

    def test_congestion_level_below_minimum(self):
        with pytest.raises(ValidationError):
            CellCongestionData(
                cell_id="cell_1", congestion_level=-0.1, camera_id="cam1",
                people_count=0, level=0, timestamp=datetime.now()
            )

    def test_congestion_level_above_maximum(self):
        with pytest.raises(ValidationError):
            CellCongestionData(
                cell_id="cell_1", congestion_level=1.1, camera_id="cam1",
                people_count=0, level=0, timestamp=datetime.now()
            )

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            CellCongestionData(congestion_level=0.5, camera_id="cam1")
        with pytest.raises(ValidationError):
            CellCongestionData(cell_id="cell_1", congestion_level=0.5)

    def test_custom_timestamp(self):
        custom_time = datetime(2025, 12, 14, 12, 0, 0)
        data = CellCongestionData(
            cell_id="cell_1",
            congestion_level=0.5,
            camera_id="cam1",
            people_count=10,
            level=0,
            timestamp=custom_time
        )
        assert data.timestamp == custom_time


class TestSectionHeatmapResponse:
    def test_valid_section_heatmap(self):
        timestamp = datetime.now()
        response = SectionHeatmapResponse(
            section_id="section_A",
            congestion_level=0.7,
            timestamp=timestamp,
            people_count=100,
            capacity=150,
            cells=[]
        )
        assert response.section_id == "section_A"
        assert response.congestion_level == 0.7
        assert response.timestamp == timestamp
        assert response.people_count == 100
        assert response.capacity == 150

    def test_section_heatmap_with_cells(self):
        cells = [
            CellCongestionData(
                cell_id="cell_1", congestion_level=0.5, level=0, camera_id="cam1",
                people_count=25, timestamp=datetime.now()
            ),
            CellCongestionData(
                cell_id="cell_2", congestion_level=0.8, level=0, camera_id="cam2",
                people_count=40, timestamp=datetime.now()
            )
        ]
        response = SectionHeatmapResponse(
            section_id="section_A",
            congestion_level=0.65,
            timestamp=datetime.now(),
            people_count=65,
            capacity=100, 
            cells=cells
        )
        assert len(response.cells) == 2


class TestStadiumHeatmapResponse:
    def test_valid_stadium_heatmap(self):
        cells = [
            CellCongestionData(
                cell_id="cell_1", congestion_level=0.5, level=0, camera_id="cam1",
                people_count=25, timestamp=datetime.now()
            ),
            CellCongestionData(
                cell_id="cell_2", congestion_level=0.8, level=0, camera_id="cam2",
                people_count=40, timestamp=datetime.now()
            )
        ]
        response = StadiumHeatmapResponse(
            total_cells=2,
            average_congestion=0.65,
            cells=cells
        )
        assert response.total_cells == 2
        assert response.average_congestion == 0.65
        assert len(response.cells) == 2

    def test_stadium_heatmap_default_timestamp(self):
        response = StadiumHeatmapResponse(
            total_cells=0,
            average_congestion=0.0,
            cells=[]
        )
        assert isinstance(response.timestamp, datetime)