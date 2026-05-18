from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from typing import List, Optional
from datetime import datetime
from contextlib import asynccontextmanager
import os
import secrets

from schemas import SectionHeatmapResponse, CampusHeatmapResponse
from store import aggregate_cell_data, get_all_aggregated_cells, cell_congestion_store
from mqtt_handler import start_mqtt, stop_mqtt
from prometheus_fastapi_instrumentator import Instrumentator

API_KEY = os.getenv("API_KEY", "dragao_secret_key_2026")
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: Optional[str] = Security(_api_key_header)):
    if api_key and secrets.compare_digest(api_key, API_KEY):
        return api_key
    raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing API key")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application"""
    print("=" * 60)
    print("Smart Campus Congestion Service - Starting Up")
    print("=" * 60)
    
    start_mqtt()
    
    print("[STARTUP] MQTT Handler initialized")
    print("[STARTUP] API Documentation: http://0.0.0.0:8000/docs")  # NOSONAR
    print("=" * 60 + "\n")
    
    yield
    
    print("\n" + "=" * 60)
    print("Smart Campus Congestion Service - Shutting Down")
    stop_mqtt()
    print("=" * 60)

app = FastAPI(
    title="Smart Campus Congestion Service API",
    description="API for managing and retrieving congestion data in a smart campus environment.",
    version="1.1.0",
    lifespan=lifespan
)

# Instrument the app and expose the /metrics endpoint
Instrumentator().instrument(app).expose(app)

@app.get(
    "/heatmap/cell/{cell_id}",
    response_model=SectionHeatmapResponse,
    responses={404: {"description": "No active camera data found for the cell"}}
)
async def get_cell_heatmap(cell_id: str, _: str = Depends(get_api_key)):
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

@app.get(
    "/heatmap/stadium/cells",
    response_model=CampusHeatmapResponse,
    responses={404: {"description": "No active congestion data available"}}
)
async def get_stadium_cell_heatmap(_: str = Depends(get_api_key)):
    """
    Get aggregated heatmap data for the entire campus.
    Note: Endpoint path kept as /stadium/ to maintain backward compatibility.
    """
    aggregated_cells = get_all_aggregated_cells()
    
    if not aggregated_cells:
        raise HTTPException(status_code=404, detail="No active congestion data available")
    
    total_cells = len(aggregated_cells)
    avg_congestion = sum(c.congestion_level for c in aggregated_cells) / total_cells if total_cells > 0 else 0
    
    return CampusHeatmapResponse(
        cells=aggregated_cells,
        total_cells=total_cells,
        average_congestion=avg_congestion,
        timestamp=datetime.now()
    )

@app.get("/sections", response_model=List[SectionHeatmapResponse])
async def list_sections(_: str = Depends(get_api_key)):
    """
    List all tracked cells with their aggregated data.
    """
    aggregated_cells = get_all_aggregated_cells()
    
    sections = [
        SectionHeatmapResponse(
            section_id=data.cell_id,
            congestion_level=data.congestion_level,
            timestamp=data.timestamp,
            people_count=data.people_count,
            capacity=data.capacity,
            cells=[data]
        )
        for data in aggregated_cells
    ]
    
    sections.sort(key=lambda x: x.congestion_level, reverse=True)
    return sections

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "tracked_cells": len(cell_congestion_store),
        "service": "Smart Campus Congestion Service (Aggregated)"
    }
