from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
from schemas import CellCongestionData, MAX_CELL_CAPACITY

# In-memory storage: {cell_id: {camera_id: {count, timestamp, level}}}
cell_congestion_store = defaultdict(dict)

# Configuration
CAMERA_TTL = 15  # seconds

def aggregate_cell_data(cell_id: str, level: int = 0) -> Optional[CellCongestionData]:
    """
    Aggregates data for a cell by taking the MAX count among active cameras.
    Also performs memory cleanup of stale camera entries.
    """
    cameras_data = cell_congestion_store.get(cell_id, {})
    if not cameras_data:
        return None
    
    current_time = datetime.now()
    max_people = 0
    active_cameras = []
    
    # Iterate over a list of keys to allow deletion during iteration
    for cam_id in list(cameras_data.keys()):
        data = cameras_data[cam_id]
        ts = data["timestamp"]
        
        # Check TTL
        if (current_time - ts).total_seconds() < CAMERA_TTL:
            max_people = max(max_people, data["count"])
            active_cameras.append(cam_id)
        else:
            # Memory cleanup: remove stale camera data
            del cell_congestion_store[cell_id][cam_id]
            
    if not active_cameras:
        if cell_id in cell_congestion_store and not cell_congestion_store[cell_id]:
            del cell_congestion_store[cell_id]
        return None

    congestion_level = min(max_people / MAX_CELL_CAPACITY, 1.0)
    
    return CellCongestionData(
        cell_id=cell_id,
        congestion_level=congestion_level,
        people_count=max_people,
        capacity=MAX_CELL_CAPACITY,
        level=level,
        timestamp=current_time,
        camera_id=",".join(active_cameras)
    )

def get_all_aggregated_cells() -> List[CellCongestionData]:
    """
    Utility function to get aggregated data for all tracked cells.
    """
    aggregated_cells = []
    for cell_id in list(cell_congestion_store.keys()):
        # Get the level from the internal store
        cameras = cell_congestion_store[cell_id]
        if not cameras:
            continue
            
        sample_cam = next(iter(cameras.values()))
        level = sample_cam.get("level", 0)
        
        data = aggregate_cell_data(cell_id, level=level)
        if data:
            aggregated_cells.append(data)
    return aggregated_cells
