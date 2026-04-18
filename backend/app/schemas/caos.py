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