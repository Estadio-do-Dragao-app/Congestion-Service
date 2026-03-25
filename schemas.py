from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional
import uuid

# --- Shared Base / Constants ---
MAX_CELL_CAPACITY = 50

class GridCell(BaseModel):
    x: float
    y: float
    count: int = Field(..., ge=0)
    cell_id: Optional[str] = None

class CrowdDensityEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "crowd_density"
    timestamp: datetime
    level: int
    grid_data: List[GridCell]
    total_people: int = Field(..., ge=0)
    metadata: Dict[str, str]

class CellCongestionData(BaseModel):
    """Congestion data for individual cells"""
    cell_id: str
    congestion_level: float = Field(..., ge=0, le=1)
    people_count: int = Field(..., ge=0)
    level: int
    capacity: int = MAX_CELL_CAPACITY
    timestamp: datetime
    camera_id: str  # Critical for multi-camera aggregation

class SectionHeatmapResponse(BaseModel):
    """Heatmap data for a specific section"""
    section_id: str
    congestion_level: float
    timestamp: datetime
    people_count: int
    capacity: int
    cells: List[CellCongestionData]

class StadiumHeatmapResponse(BaseModel):
    """Heatmap data for the entire stadium"""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_cells: int
    average_congestion: float
    cells: List[CellCongestionData]
