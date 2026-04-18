from fastapi import APIRouter

from app.schemas.caos import MemoryWorkersResponse
from app.services.memory_worker_service import list_lane_workers, rebuild_lane_workers


router = APIRouter(prefix="/caos/memory/workers", tags=["caos-memory-workers"])


@router.get("/{user_email}", response_model=MemoryWorkersResponse)
async def get_memory_workers(user_email: str):
    workers = await list_lane_workers(user_email)
    return MemoryWorkersResponse(user_email=user_email, workers=workers)


@router.post("/{user_email}/rebuild", response_model=MemoryWorkersResponse)
async def rebuild_memory_workers(user_email: str):
    workers = await rebuild_lane_workers(user_email)
    return MemoryWorkersResponse(user_email=user_email, workers=workers)