from fastapi import APIRouter, HTTPException

from app.schemas.caos import GlobalInfoBinResponse, MemoryDeleteResponse, MemoryEntry, MemorySaveRequest, MemoryUpdateRequest
from app.services.global_info_service import list_global_info_entries
from app.services.profile_memory_service import (
    delete_profile_memory,
    list_profile_memories,
    save_profile_memory,
    update_profile_memory,
)


router = APIRouter(prefix="/caos/memory", tags=["caos-memory"])


@router.get("", response_model=list[MemoryEntry])
async def list_memories(user_email: str, bin_name: str | None = None):
    return await list_profile_memories(user_email, bin_name)


@router.get("/global-bin", response_model=GlobalInfoBinResponse)
async def list_global_bin(user_email: str, lane: str | None = None):
    return GlobalInfoBinResponse(user_email=user_email, entries=await list_global_info_entries(user_email, lane))


@router.post("/save", response_model=MemoryEntry)
async def save_memory(input: MemorySaveRequest):
    return await save_profile_memory(input)


@router.patch("/{memory_id}", response_model=MemoryEntry)
async def update_memory(memory_id: str, input: MemoryUpdateRequest):
    try:
        return await update_profile_memory(memory_id, input)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/{memory_id}", response_model=MemoryDeleteResponse)
async def delete_memory(memory_id: str, user_email: str):
    try:
        return await delete_profile_memory(user_email, memory_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error