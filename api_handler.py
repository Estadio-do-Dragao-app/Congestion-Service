from fastapi import FastAPI, HTTPException
from typing import Dict, List, Optional
from collections import defaultdict
from datetime import datetime

from models import CellCongestionData, SectionHeatmapResponse, StadiumHeatmapResponse, SectionInfo

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
            "GET /heatmap/section/{section_id}": "Get heatmap for specific section",
            "GET /heatmap/stadium": "Get heatmap for entire stadium",
            "GET /sections": "List all tracked sections",
            "DELETE /section/{section_id}": "Clear data for a specific section",
            "DELETE /stadium": "Clear all stadium data"
        }
    }

@app.post("/congestion", response_model=dict, status_code=201)
async def submit_cell_congestion_data(data: CellCongestionData):
    """
    Receive cell congestion data from the emulator
    
    This endpoint allows the emulator to submit real-time congestion information
    for different sections of the stadium.
    """
    global first_update_time
    
    # Store the congestion data
    cell_congestion_store[data.section_id] = data
    
    # Track first update time
    if first_update_time is None:
        first_update_time = datetime.now()
    
    return {
        "message": "Cell Congestion data received successfully",
        "section_id": data.section_id,
        "congestion_level": data.congestion_level,
        "timestamp": data.timestamp
    }

@app.get("/heatmap/section/{section_id}", response_model=SectionHeatmapResponse)
async def get_section_heatmap(section_id: str):
    """
    Get heatmap data for a specific section
    
    Returns current congestion level and details for the specified stadium section.
    """
    if section_id not in cell_congestion_store:
        raise HTTPException(status_code=404, detail=f"No data found for section: {section_id}")
    
    data = cell_congestion_store[section_id]
    
    return SectionHeatmapResponse(
        section_id=data.section_id,
        congestion_level=data.congestion_level,
        timestamp=data.timestamp,
        people_count=data.people_count,
        capacity=data.capacity
    )

@app.get("/heatmap/stadium", response_model=StadiumHeatmapResponse)
async def get_stadium_heatmap():
    """
    Get aggregated heatmap data for the entire stadium
    
    Returns congestion levels across all sections,
    providing a comprehensive view of the stadium's current state.
    """
    if not cell_congestion_store:
        raise HTTPException(status_code=404, detail="No congestion data available for the stadium")
    
    # Build sections dictionary
    sections_data = {
        section_id: data.congestion_level 
        for section_id, data in cell_congestion_store.items()
    }
    
    # Calculate statistics
    total_sections = len(sections_data)
    average_congestion = sum(sections_data.values()) / total_sections if total_sections > 0 else 0.0
    
    # Find most and least congested sections
    most_congested = max(sections_data.items(), key=lambda x: x[1])[0] if sections_data else None
    least_congested = min(sections_data.items(), key=lambda x: x[1])[0] if sections_data else None
    
    return StadiumHeatmapResponse(
        sections=sections_data,
        total_sections=total_sections,
        average_congestion=average_congestion,
        most_congested=most_congested,
        least_congested=least_congested
    )

@app.get("/sections", response_model=List[SectionInfo])
async def list_sections():
    """
    List all tracked sections with their current data
    
    Returns information about all sections currently being monitored,
    including congestion levels and capacity information.
    """
    if not cell_congestion_store:
        return []
    
    sections_info = []
    for section_id, data in cell_congestion_store.items():
        sections_info.append(SectionInfo(
            section_id=section_id,
            congestion_level=data.congestion_level,
            last_update=data.timestamp,
            people_count=data.people_count,
            capacity=data.capacity
        ))
    
    # Sort by congestion level (highest first)
    sections_info.sort(key=lambda x: x.congestion_level, reverse=True)
    
    return sections_info

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
        "timestamp": datetime.now(),
        "tracked_sections": len(cell_congestion_store),
        "average_congestion": sum(data.congestion_level for data in cell_congestion_store.values()) / len(cell_congestion_store) if cell_congestion_store else 0.0,
        "service_uptime": (datetime.now() - first_update_time).total_seconds() if first_update_time else 0
    }

