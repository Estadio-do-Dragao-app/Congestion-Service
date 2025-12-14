"""
Test suite for data models
"""
import pytest
from datetime import datetime
from pydantic import ValidationError
from models import (
    CellCongestionData, 
    SectionHeatmapResponse, 
    StadiumHeatmapResponse,
    StadiumOverallHeatmapResponse,
    SectionInfo
)


class TestCellCongestionData:
    """Test CellCongestionData model"""
    
    def test_valid_cell_congestion_data(self):
        """Test creating valid cell congestion data"""
        data = CellCongestionData(
            cell_id="cell_1",
            congestion_level=0.5,
            people_count=25,
            level=0,
            capacity=50
        )
        assert data.cell_id == "cell_1"
        assert data.congestion_level == 0.5
        assert data.people_count == 25
        assert data.level == 0
        assert data.capacity == 50
        assert isinstance(data.timestamp, datetime)
    
    def test_congestion_level_boundaries(self):
        """Test congestion level validation boundaries"""
        # Valid boundary values
        data_min = CellCongestionData(cell_id="cell_1", congestion_level=0.0)
        assert data_min.congestion_level == 0.0
        
        data_max = CellCongestionData(cell_id="cell_1", congestion_level=1.0)
        assert data_max.congestion_level == 1.0
    
    def test_congestion_level_below_minimum(self):
        """Test congestion level below minimum raises error"""
        with pytest.raises(ValidationError):
            CellCongestionData(cell_id="cell_1", congestion_level=-0.1)
    
    def test_congestion_level_above_maximum(self):
        """Test congestion level above maximum raises error"""
        with pytest.raises(ValidationError):
            CellCongestionData(cell_id="cell_1", congestion_level=1.1)
    
    def test_missing_required_fields(self):
        """Test missing required fields raises error"""
        with pytest.raises(ValidationError):
            CellCongestionData(congestion_level=0.5)
    
    def test_optional_fields_default_to_none(self):
        """Test optional fields have correct defaults"""
        data = CellCongestionData(cell_id="cell_1", congestion_level=0.5, level=0)
        assert data.people_count is None
        assert data.capacity is None
    
    def test_custom_timestamp(self):
        """Test setting custom timestamp"""
        custom_time = datetime(2025, 12, 14, 12, 0, 0)
        data = CellCongestionData(
            cell_id="cell_1",
            congestion_level=0.5,
            timestamp=custom_time
        )
        assert data.timestamp == custom_time


class TestSectionHeatmapResponse:
    """Test SectionHeatmapResponse model"""
    
    def test_valid_section_heatmap(self):
        """Test creating valid section heatmap"""
        timestamp = datetime.now()
        response = SectionHeatmapResponse(
            section_id="section_A",
            congestion_level=0.7,
            timestamp=timestamp,
            people_count=100,
            capacity=150
        )
        assert response.section_id == "section_A"
        assert response.congestion_level == 0.7
        assert response.timestamp == timestamp
        assert response.people_count == 100
        assert response.capacity == 150
    
    def test_section_heatmap_with_cells(self):
        """Test section heatmap with cell data"""
        cells = [
            CellCongestionData(cell_id="cell_1", congestion_level=0.5, level=0),
            CellCongestionData(cell_id="cell_2", congestion_level=0.8, level=0)
        ]
        response = SectionHeatmapResponse(
            section_id="section_A",
            congestion_level=0.65,
            timestamp=datetime.now(),
            cells=cells
        )
        assert len(response.cells) == 2
        assert response.cells[0].cell_id == "cell_1"
        assert response.cells[1].cell_id == "cell_2"


class TestStadiumHeatmapResponse:
    """Test StadiumHeatmapResponse model"""
    
    def test_valid_stadium_heatmap(self):
        """Test creating valid stadium heatmap"""
        cells = [
            CellCongestionData(cell_id="cell_1", congestion_level=0.5, level=0),
            CellCongestionData(cell_id="cell_2", congestion_level=0.8, level=0)
        ]
        response = StadiumHeatmapResponse(
            total_cells=2,
            average_congestion=0.65,
            most_congested="cell_2",
            least_congested="cell_1",
            cells=cells
        )
        assert response.total_cells == 2
        assert response.average_congestion == 0.65
        assert response.most_congested == "cell_2"
        assert response.least_congested == "cell_1"
        assert len(response.cells) == 2
    
    def test_stadium_heatmap_default_timestamp(self):
        """Test default timestamp is generated"""
        response = StadiumHeatmapResponse(
            total_cells=0,
            average_congestion=0.0,
        )
        assert isinstance(response.timestamp, datetime)


class TestStadiumOverallHeatmapResponse:
    """Test StadiumOverallHeatmapResponse model"""
    
    def test_valid_overall_heatmap(self):
        """Test creating valid overall stadium heatmap"""
        sections = {
            "section_A": 0.5,
            "section_B": 0.8,
            "section_C": 0.3
        }
        response = StadiumOverallHeatmapResponse(
            total_sections=3,
            average_congestion=0.53,
            most_congested="section_B",
            least_congested="section_C",
            sections=sections
        )
        assert response.total_sections == 3
        assert response.average_congestion == 0.53
        assert response.most_congested == "section_B"
        assert response.least_congested == "section_C"
        assert len(response.sections) == 3
    
    def test_empty_sections(self):
        """Test heatmap with no sections"""
        response = StadiumOverallHeatmapResponse(
            total_sections=0,
            average_congestion=0.0,
            sections={}
        )
        assert response.total_sections == 0
        assert response.sections == {}
        assert response.most_congested is None
        assert response.least_congested is None


class TestSectionInfo:
    """Test SectionInfo model"""
    
    def test_valid_section_info(self):
        """Test creating valid section info"""
        timestamp = datetime.now()
        info = SectionInfo(
            section_id="section_A",
            congestion_level=0.6,
            last_update=timestamp,
            people_count=120,
            capacity=200
        )
        assert info.section_id == "section_A"
        assert info.congestion_level == 0.6
        assert info.last_update == timestamp
        assert info.people_count == 120
        assert info.capacity == 200
    
    def test_section_info_optional_fields(self):
        """Test section info with optional fields as None"""
        timestamp = datetime.now()
        info = SectionInfo(
            section_id="section_A",
            congestion_level=0.6,
            last_update=timestamp,
            people_count=None,
            capacity=None
        )
        assert info.people_count is None
        assert info.capacity is None
