from datetime import datetime
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

# Data Models

class CellCongestionData(BaseModel):
    """Congestion data for individual cells within a section"""
    cell_id: str = Field(..., description="Identifier for the cell within the section")
    congestion_level: float = Field(..., ge=0, le=1, description="Congestion level from 0 (empty) to 1 (full capacity)")
    people_count: Optional[int] = Field(None, description="Actual number of people in the cell")
    level: int = Field(0, description="Floor level of the cell")
    capacity: Optional[int] = Field(None, description="Maximum capacity of the cell")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the data was recorded")

class SectionHeatmapResponse(BaseModel):
    """Heatmap data for a specific section"""
    section_id: str = Field(..., description="Section identifier")
    congestion_level: float = Field(..., description="Current congestion level")
    timestamp: datetime = Field(..., description="When the data was last updated")
    people_count: Optional[int] = Field(None, description="Number of people")
    capacity: Optional[int] = Field(None, description="Section capacity")
    cells: Optional[List[CellCongestionData]] = Field(None, description="Detailed cell-level congestion data")

class StadiumOverallHeatmapResponse(BaseModel):
    """Heatmap data for the entire stadium based on sections"""

    timestamp: datetime = Field(default_factory=datetime.now, description="When the heatmap was generated")
    total_sections: int = Field(..., description="Total number of sections")
    average_congestion: float = Field(..., description="Average congestion across all sections")
    most_congested: Optional[str] = Field(None, description="ID of the most congested section")
    least_congested: Optional[str] = Field(None, description="ID of the least congested section")
    sections: Dict[str, float] = Field(..., description="Dictionary mapping section_id to congestion_level")

class StadiumHeatmapResponse(BaseModel):
    """Heatmap data for the entire stadium based on cells"""

    timestamp: datetime = Field(default_factory=datetime.now, description="When the heatmap was generated")
    total_cells: int = Field(..., description="Total number of cells in the stadium")
    average_congestion: float = Field(..., description="Average congestion across all cells")
    most_congested: Optional[str] = Field(None, description="ID of the most congested cell")
    least_congested: Optional[str] = Field(None, description="ID of the least congested cell")
    cells: Optional[List[CellCongestionData]] = Field(None, description="Detailed cell-level congestion data")
    
class SectionInfo(BaseModel):
    """Detailed information about a section"""
    section_id: str
    congestion_level: float
    last_update: datetime
    people_count: Optional[int]
    capacity: Optional[int]

