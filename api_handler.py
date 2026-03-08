from fastapi import FastAPI, HTTPException
from typing import Dict, List, Optional
from datetime import datetime

from schemas import CellCongestionData, SectionHeatmapResponse, StadiumHeatmapResponse

app = FastAPI(title="Smart Stadium Congestion Service API",
              description="API for managing and retrieving congestion data in a smart stadium environment.",
              version="1.0.0")

# Importar do handler para ter acesso ao store real e lógica de agregação
from mqtt_handler import cell_congestion_store, aggregate_cell_data, start_mqtt

@app.on_event("startup")
async def startup_event():
    """Initialize MQTT connection on startup"""
    print("=" * 60)
    print("Smart Stadium Congestion Service - Starting Up")
    print("=" * 60)
    
    start_mqtt()
    
    print("[STARTUP] MQTT Handler initialized")
    print("[STARTUP] API Documentation: http://0.0.0.0:8000/docs")
    print("=" * 60 + "\n")

@app.get("/heatmap/cell/{cell_id}", response_model=SectionHeatmapResponse)
async def get_cell_heatmap(cell_id: str):
    """
    Get heatmap data for a specific cell (Aggregated across cameras)
    """
    data = aggregate_cell_data(cell_id, level=0)
    
    if not data:
        raise HTTPException(status_code=404, detail=f"No active camera data found for cell: {cell_id}")
    
    return SectionHeatmapResponse(
        section_id=cell_id,
        congestion_level=data.congestion_level,
        timestamp=data.timestamp,
        people_count=data.people_count,
        capacity=data.capacity,
        cells=[data]
    )

@app.get("/heatmap/stadium/cells", response_model=StadiumHeatmapResponse)
async def get_stadium_cell_heatmap():
    """
    Get aggregated heatmap data for the entire stadium.
    """
    aggregated_cells = []
    
    for cell_id in list(cell_congestion_store.keys()):
        # Obtemos o level a partir do store interno
        sample_cam = next(iter(cell_congestion_store[cell_id].values()))
        level = sample_cam.get("level", 0)
        
        data = aggregate_cell_data(cell_id, level=level)
        if data:
            aggregated_cells.append(data)
    
    if not aggregated_cells:
        raise HTTPException(status_code=404, detail="No active congestion data available")
    
    total_cells = len(aggregated_cells)
    avg_congestion = sum(c.congestion_level for c in aggregated_cells) / total_cells if total_cells > 0 else 0
    
    return StadiumHeatmapResponse(
        cells=aggregated_cells,
        total_cells=total_cells,
        average_congestion=avg_congestion,
        timestamp=datetime.now()
    )

@app.get("/sections", response_model=List[SectionHeatmapResponse])
async def list_sections():
    """
    List all tracked cells with their aggregated data.
    """
    sections = []
    for cell_id in list(cell_congestion_store.keys()):
        sample_cam = next(iter(cell_congestion_store[cell_id].values()))
        level = sample_cam.get("level", 0)
        
        data = aggregate_cell_data(cell_id, level=level)
        if data:
            sections.append(SectionHeatmapResponse(
                section_id=cell_id,
                congestion_level=data.congestion_level,
                timestamp=data.timestamp,
                people_count=data.people_count,
                capacity=data.capacity,
                cells=[data]
            ))
    
    sections.sort(key=lambda x: x.congestion_level, reverse=True)
    return sections

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "tracked_cells": len(cell_congestion_store),
        "service": "Smart Stadium Congestion Service (Aggregated)"
    }
