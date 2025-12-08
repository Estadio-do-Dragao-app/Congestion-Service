from fastapi import FastAPI, HTTPException
from typing import Dict, List, Optional
from datetime import datetime

from models import CellCongestionData, SectionHeatmapResponse, StadiumHeatmapResponse, StadiumOverallHeatmapResponse, SectionInfo

app = FastAPI(title="Smart Stadium Congestion Service API",
              description="API for managing and retrieving congestion data in a smart stadium environment.",
              version="1.0.0")



# In-memory storage
cell_congestion_store: Dict[str, CellCongestionData] = {}  # {section_id: CongestionData}
first_update_time: Optional[datetime] = None

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Smart Stadium Congestion Service",
        "version": "1.0.0",
        "endpoints": {
            "POST /congestion": "Submit congestion data from emulator",
            "GET /heatmap/cell/{cell_id}": "Get heatmap for specific cell",
            "GET /heatmap/stadium/cells": "Get heatmap for entire stadium (cells)",
            "GET /heatmap/stadium/sections": "Get heatmap for entire stadium (sections)",
            "GET /sections": "List all tracked cells",
            "DELETE /cell/{cell_id}": "Clear data for a specific cell",
            "DELETE /stadium": "Clear all stadium data",
            "GET /health": "Health check"
        }
    }

@app.post("/congestion", response_model=dict, status_code=201)
async def submit_cell_congestion_data(data: CellCongestionData):
    """
    Receive cell congestion data from the emulator
    
    This endpoint allows the emulator to submit real-time congestion information
    for different cells of the stadium.
    """
    global first_update_time
    
    # Store the congestion data by cell_id
    cell_congestion_store[data.cell_id] = data
    
    # Track first update time
    if first_update_time is None:
        first_update_time = datetime.now()
    
    return {
        "message": "Cell Congestion data received successfully",
        "cell_id": data.cell_id,
        "congestion_level": data.congestion_level,
        "timestamp": data.timestamp.isoformat() if hasattr(data.timestamp, 'isoformat') else str(data.timestamp)
    }

@app.get("/heatmap/cell/{cell_id}", response_model=SectionHeatmapResponse)
async def get_cell_heatmap(cell_id: str):
    """
    Get heatmap data for a specific cell
    
    Returns current congestion level and details for the specified stadium cell.
    """
    if cell_id not in cell_congestion_store:
        raise HTTPException(status_code=404, detail=f"No data found for cell: {cell_id}")
    
    data = cell_congestion_store[cell_id]
    
    return SectionHeatmapResponse(
        section_id=cell_id,
        congestion_level=data.congestion_level,
        timestamp=data.timestamp if hasattr(data, 'timestamp') else datetime.now(),
        people_count=data.people_count,
        capacity=data.capacity
    )

@app.get("/heatmap/stadium/cells", response_model=StadiumHeatmapResponse)
async def get_stadium_cell_heatmap():
    """
    Get aggregated heatmap data for the entire stadium based on cells
    
    Returns detailed congestion levels across all cells,
    providing a comprehensive view of the stadium's current state.
    """
    if not cell_congestion_store:
        raise HTTPException(status_code=404, detail="No congestion data available for the stadium")
    
    cells_data = list(cell_congestion_store.values())
    
    total_cells = len(cells_data)
    average_congestion = sum(cell.congestion_level for cell in cells_data) / total_cells if total_cells > 0 else 0.0
    
    most_congested = max(cells_data, key=lambda x: x.congestion_level).cell_id if cells_data else None
    least_congested = min(cells_data, key=lambda x: x.congestion_level).cell_id if cells_data else None
    
    return StadiumHeatmapResponse(
        cells=cells_data,
        total_cells=total_cells,
        average_congestion=average_congestion,
        most_congested=most_congested,
        least_congested=least_congested
    )

@app.get("/heatmap/stadium/sections", response_model=StadiumOverallHeatmapResponse)
async def get_stadium_sections_heatmap():
    """
    Get aggregated heatmap data for the entire stadium based on sections
    
    Returns congestion levels across all sections,
    providing an overview of the stadium's current state.
    """
    if not cell_congestion_store:
        raise HTTPException(status_code=404, detail="No congestion data available for the stadium")
    
    sections_data = list(cell_congestion_store.values())
    
    total_sections = len(sections_data)
    average_congestion = sum(section.congestion_level for section in sections_data) / total_sections if total_sections > 0 else 0.0
    
    most_congested = max(sections_data, key=lambda x: x.congestion_level).cell_id if sections_data else None
    least_congested = min(sections_data, key=lambda x: x.congestion_level).cell_id if sections_data else None
    
    sections_congestion = {section.cell_id: section.congestion_level for section in sections_data}
    
    return StadiumOverallHeatmapResponse(
        sections=sections_congestion,
        total_sections=total_sections,
        average_congestion=average_congestion,
        most_congested=most_congested,
        least_congested=least_congested
    )

@app.get("/sections", response_model=List[SectionInfo])
async def list_sections():
    """
    List all tracked cells with their current data
    
    Returns information about all cells currently being monitored,
    including congestion levels and capacity information.
    """
    if not cell_congestion_store:
        return []
    
    sections_info = []
    for cell_id, data in cell_congestion_store.items():
        sections_info.append(SectionInfo(
            section_id=cell_id,
            congestion_level=data.congestion_level,
            last_update=data.timestamp,
            people_count=data.people_count,
            capacity=data.capacity
        ))
    
    # Sort by congestion level (highest first)
    sections_info.sort(key=lambda x: x.congestion_level, reverse=True)
    
    return sections_info

@app.delete("/cell/{cell_id}")
async def clear_cell_data(cell_id: str):
    """
    Clear congestion data for a specific cell
    
    Useful for resetting a cell's data or testing purposes.
    """
    if cell_id not in cell_congestion_store:
        raise HTTPException(status_code=404, detail=f"Cell not found: {cell_id}")
    
    del cell_congestion_store[cell_id]
    
    return {
        "message": f"Data for cell {cell_id} has been cleared successfully"
    }


@app.delete("/section/{section_id}")
async def clear_section_data(section_id: str):
    """
    Clear congestion data for a specific section
    
    Useful for resetting a section's data or testing purposes.
    """
    if section_id not in cell_congestion_store:
        raise HTTPException(status_code=404, detail=f"Section not found: {section_id}")
    
    del cell_congestion_store[section_id]
    
    return {
        "message": f"Data for section {section_id} has been cleared successfully"
    }

@app.delete("/stadium")
async def clear_all_data():
    """
    Clear all congestion data for the entire stadium
    
    Resets all tracked data. Useful for starting fresh or testing.
    """
    global first_update_time
    
    section_count = len(cell_congestion_store)
    cell_congestion_store.clear()
    first_update_time = None
    
    return {
        "message": "All stadium congestion data has been cleared",
        "sections_cleared": section_count
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "tracked_cells": len(cell_congestion_store),
        "average_congestion": sum(data.congestion_level for data in cell_congestion_store.values()) / len(cell_congestion_store) if cell_congestion_store else 0.0,
        "service_uptime": (datetime.now() - first_update_time).total_seconds() if first_update_time else 0
    }