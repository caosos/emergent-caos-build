from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
import logging
from pydantic import BaseModel, Field, ConfigDict
from typing import List
import uuid
from datetime import datetime, timezone

from app.config import settings
from app.db import client, db
from app.routes.auth import router as auth_router
from app.routes.caos import router as caos_router
from app.routes.health import router as health_router
from app.routes.memory_profile import router as memory_profile_router
from app.routes.memory_workers import router as memory_workers_router
from app.services.object_storage import init_storage
from app.startup import ensure_indexes

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks


@api_router.get("/caos/contract")
async def caos_contract():
    return {
        "runtime": "fastapi-python",
        "isolation_boundary": "session_id",
        "memory_pipeline": ["ingest", "sanitize", "compress", "retrieve", "inject", "receipt"],
        "notes": "Session isolation is canonical. Cross-session memory leakage is forbidden.",
    }

# Include the router in the main app
app.include_router(api_router)
app.include_router(auth_router, prefix="/api")
app.include_router(health_router, prefix="/api")
app.include_router(caos_router, prefix="/api")
app.include_router(memory_profile_router, prefix="/api")
app.include_router(memory_workers_router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    # Browsers reject `*` when allow_credentials=True. If the configured origins
    # contain "*", we switch to `allow_origin_regex=".*"` which echoes the caller
    # origin and keeps credentials working. Otherwise use the explicit list.
    allow_origin_regex=".*" if "*" in settings.cors_origins else None,
    allow_origins=[] if "*" in settings.cors_origins else settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def on_startup():
    # Create MongoDB indexes (idempotent) + bootstrap Emergent object storage.
    await ensure_indexes()
    init_storage()


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()