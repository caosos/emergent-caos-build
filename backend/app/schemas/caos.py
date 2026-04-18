from datetime import datetime, timezone
from typing import Literal
import uuid

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SessionCreate(BaseModel):
    user_email: str
    title: str


class SessionRecord(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_email: str
    title: str
    summary: str | None = None
    last_message_preview: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class MessageCreate(BaseModel):
    session_id: str
    role: Literal["system", "user", "assistant"]
    content: str
    metadata_tags: list[str] = Field(default_factory=list)
    inference_provider: str | None = None


class MessageRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: Literal["system", "user", "assistant"]
    content: str
    metadata_tags: list[str] = Field(default_factory=list)
    inference_provider: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class MemoryEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    tags: list[str] = Field(default_factory=list)
    scope: str = "profile"
    source: str = "user_trigger"
    created_at: datetime = Field(default_factory=utc_now)


class MemorySaveRequest(BaseModel):
    user_email: str
    content: str
    tags: list[str] = Field(default_factory=list)


class UserProfileUpsertRequest(BaseModel):
    user_email: str
    preferred_name: str | None = None
    assistant_name: str = "Aria"
    environment_name: str = "CAOS"


class UserProfileRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_email: str
    preferred_name: str | None = None
    assistant_name: str = "Aria"
    environment_name: str = "CAOS"
    structured_memory: list[MemoryEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ContextPrepareRequest(BaseModel):
    user_email: str
    session_id: str
    query: str
    hot_head: int = 10
    hot_tail: int = 20
    memory_limit: int = 5


class ContextStats(BaseModel):
    total_messages: int
    removed_duplicates: int
    removed_low_signal: int
    final_messages: int
    estimated_chars_before: int
    estimated_chars_after: int
    reduction_ratio: float


class ContextPrepareResponse(BaseModel):
    session_id: str
    query: str
    sanitized_history: list[MessageRecord]
    injected_memories: list[MemoryEntry]
    stats: ContextStats
    receipt: dict


class ChatRequest(BaseModel):
    user_email: str
    session_id: str
    content: str
    provider: str = "openai"
    model: str = "gpt-5.2"
    hot_head: int = 10
    hot_tail: int = 20
    memory_limit: int = 5


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    assistant_message: MessageRecord
    sanitized_history: list[MessageRecord]
    injected_memories: list[MemoryEntry]
    receipt: dict
    wcw_used_estimate: int
    wcw_budget: int


class ReceiptRecord(BaseModel):
    id: str
    session_id: str
    assistant_message_id: str
    source_message_ids: list[str] = Field(default_factory=list)
    provider: str
    model: str
    retrieval_terms: list[str] = Field(default_factory=list)
    selected_memory_ids: list[str] = Field(default_factory=list)
    previous_receipt_id: str | None = None
    previous_summary_id: str | None = None
    previous_seed_id: str | None = None
    lineage_depth: int = 0
    reduction_ratio: float = 0.0
    final_message_count: int = 0
    wcw_used_estimate: int = 0
    wcw_budget: int = 0
    created_at: datetime


class SummaryRecord(BaseModel):
    id: str
    session_id: str
    source_user_excerpt: str
    summary: str
    source_message_ids: list[str] = Field(default_factory=list)
    previous_summary_id: str | None = None
    lineage_depth: int = 0
    created_at: datetime


class SeedRecord(BaseModel):
    id: str
    session_id: str
    topics: list[str] = Field(default_factory=list)
    seed_text: str
    selected_memory_ids: list[str] = Field(default_factory=list)
    source_message_ids: list[str] = Field(default_factory=list)
    previous_seed_id: str | None = None
    previous_summary_id: str | None = None
    lineage_depth: int = 0
    created_at: datetime


class SessionArtifactsResponse(BaseModel):
    receipts: list[ReceiptRecord] = Field(default_factory=list)
    summaries: list[SummaryRecord] = Field(default_factory=list)
    seeds: list[SeedRecord] = Field(default_factory=list)


class ContinuityResponse(BaseModel):
    session_id: str
    latest_summary: SummaryRecord | None = None
    latest_seed: SeedRecord | None = None
    latest_receipt: ReceiptRecord | None = None
    lineage_depth: int = 0


class UserFileRecord(BaseModel):
    id: str
    user_email: str
    session_id: str | None = None
    name: str
    kind: str
    mime_type: str
    size: int
    url: str | None = None
    storage_path: str | None = None
    created_at: datetime


class LinkCreateRequest(BaseModel):
    user_email: str
    url: str
    label: str
    session_id: str | None = None


class TTSRequest(BaseModel):
    text: str
    voice: str = "nova"
    speed: float = 1.0
    model: str = "tts-1-hd"


class TTSResponse(BaseModel):
    audio_base64: str
    content_type: str
    voice: str
    model: str
    speed: float


class TranscriptionResponse(BaseModel):
    text: str