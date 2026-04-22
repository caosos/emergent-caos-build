from datetime import datetime, timezone
from typing import Literal
import uuid

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SessionCreate(BaseModel):
    user_email: str
    title: str
    lane: str = "general"


class SessionRecord(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_email: str
    title: str
    title_source: Literal["user", "auto"] = "user"
    lane: str = "general"
    summary: str | None = None
    last_message_preview: str | None = None
    is_flagged: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SessionUpdate(BaseModel):
    title: str | None = None
    is_flagged: bool | None = None
    lane: str | None = None


class SessionDeleteResponse(BaseModel):
    session_id: str
    deleted: bool = True


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
    latency_ms: int | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class MemoryEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    tags: list[str] = Field(default_factory=list)
    bin_name: str = "general"
    scope: str = "profile"
    source: str = "user_trigger"
    priority: int = 50
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class MemorySaveRequest(BaseModel):
    user_email: str
    content: str
    tags: list[str] = Field(default_factory=list)
    bin_name: str = "general"
    priority: int = 50


class MemoryUpdateRequest(BaseModel):
    user_email: str
    content: str | None = None
    tags: list[str] | None = None
    bin_name: str | None = None
    priority: int | None = None


class MemoryDeleteResponse(BaseModel):
    ok: bool = True
    deleted_id: str


class GlobalInfoEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_email: str
    lane: str = "global"
    subject_bins: list[str] = Field(default_factory=list)
    retrieval_terms: list[str] = Field(default_factory=list)
    snippet: str
    source_session_id: str
    source_message_id: str
    hits: int = 1
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class GlobalInfoBinResponse(BaseModel):
    user_email: str
    entries: list[GlobalInfoEntry] = Field(default_factory=list)


class UserProfileUpsertRequest(BaseModel):
    user_email: str
    preferred_name: str | None = None
    assistant_name: str = "Aria"
    environment_name: str = "CAOS"
    date_of_birth: str | None = None
    full_name: str | None = None
    role: str | None = None


class RuntimePreferences(BaseModel):
    portability_mode: Literal["portable"] = "portable"
    key_source: Literal["universal", "custom", "hybrid"] = "hybrid"
    default_provider: str = "openai"
    default_model: str = "gpt-5.2"
    enabled_providers: list[str] = Field(default_factory=lambda: ["openai", "anthropic", "gemini", "xai"])


class RuntimeProviderRecord(BaseModel):
    provider: str
    label: str
    default_model: str
    available: bool = True
    requires_custom_key: bool = False
    key_status: Literal["ready", "needs-key"] = "ready"


class RuntimeSettingsUpsertRequest(BaseModel):
    user_email: str
    key_source: Literal["universal", "custom", "hybrid"] = "hybrid"
    default_provider: str = "openai"
    default_model: str = "gpt-5.2"
    enabled_providers: list[str] = Field(default_factory=lambda: ["openai", "anthropic", "gemini", "xai"])


class RuntimeSettingsResponse(BaseModel):
    user_email: str
    key_source: Literal["universal", "custom", "hybrid"]
    default_provider: str
    default_model: str
    enabled_providers: list[str] = Field(default_factory=list)
    provider_catalog: list[RuntimeProviderRecord] = Field(default_factory=list)


class VoicePreferences(BaseModel):
    stt_primary_model: str = "whisper-1"
    stt_fallback_model: str = "whisper-1"
    stt_language: str = "en"
    tts_model: str = "tts-1"
    tts_voice: str = "nova"
    tts_speed: float = 1.0


class VoiceSettingsUpsertRequest(BaseModel):
    user_email: str
    stt_primary_model: str = "whisper-1"
    stt_fallback_model: str = "whisper-1"
    stt_language: str = "en"
    tts_model: str = "tts-1"
    tts_voice: str = "nova"
    tts_speed: float = 1.0


class VoiceSettingsResponse(BaseModel):
    user_email: str
    voice_preferences: VoicePreferences


class UserProfileRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_email: str
    preferred_name: str | None = None
    assistant_name: str = "Aria"
    environment_name: str = "CAOS"
    date_of_birth: str | None = None
    full_name: str | None = None
    role: str | None = None
    structured_memory: list[MemoryEntry] = Field(default_factory=list)
    runtime_preferences: RuntimePreferences = Field(default_factory=RuntimePreferences)
    voice_preferences: VoicePreferences = Field(default_factory=VoicePreferences)
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
    provider: str | None = None
    model: str | None = None
    hot_head: int = 10
    hot_tail: int = 20
    memory_limit: int = 5
    history_token_budget: int = 2200


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    assistant_message: MessageRecord
    sanitized_history: list[MessageRecord]
    injected_memories: list[MemoryEntry]
    receipt: dict
    provider: str
    model: str
    lane: str = "general"
    subject_bins: list[str] = Field(default_factory=list)
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
    selected_summary_ids: list[str] = Field(default_factory=list)
    selected_seed_ids: list[str] = Field(default_factory=list)
    selected_worker_ids: list[str] = Field(default_factory=list)
    selected_personal_fact_ids: list[str] = Field(default_factory=list)
    selected_general_memory_ids: list[str] = Field(default_factory=list)
    selected_global_cache_ids: list[str] = Field(default_factory=list)
    lane: str = "general"
    subject_bins: list[str] = Field(default_factory=list)
    rehydration_order: list[str] = Field(default_factory=list)
    global_bin_status: str = "empty"
    previous_receipt_id: str | None = None
    previous_summary_id: str | None = None
    previous_seed_id: str | None = None
    lineage_depth: int = 0
    token_source: str = "local_tokenizer_fallback"
    history_tokens: int = 0
    memory_tokens: int = 0
    continuity_tokens: int = 0
    global_cache_tokens: int = 0
    active_context_tokens: int = 0
    system_prompt_tokens: int = 0
    user_message_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    session_prompt_tokens_total: int = 0
    session_completion_tokens_total: int = 0
    session_total_tokens: int = 0
    retained_messages: list[dict] = Field(default_factory=list)
    dropped_messages: list[dict] = Field(default_factory=list)
    compressed_messages: list[dict] = Field(default_factory=list)
    budget_trimmed_messages: list[dict] = Field(default_factory=list)
    reused_memories: list[dict] = Field(default_factory=list)
    reused_continuity: list[dict] = Field(default_factory=list)
    retained_message_count: int = 0
    dropped_message_count: int = 0
    compressed_message_count: int = 0
    budget_trimmed_count: int = 0
    history_budget_tokens: int = 0
    history_tokens_before_budget: int = 0
    history_tokens_after_budget: int = 0
    personal_facts_count: int = 0
    general_memory_count: int = 0
    global_cache_count: int = 0
    reused_memory_count: int = 0
    reused_continuity_count: int = 0
    retention_explanation: list[str] = Field(default_factory=list)
    reduction_ratio: float = 0.0
    final_message_count: int = 0
    wcw_used_estimate: int = 0
    wcw_budget: int = 0
    continuity_chars: int = 0
    estimated_context_chars: int = 0
    created_at: datetime


class SummaryRecord(BaseModel):
    id: str
    session_id: str
    lane: str = "general"
    source_user_excerpt: str
    summary: str
    subject_bins: list[str] = Field(default_factory=list)
    source_message_ids: list[str] = Field(default_factory=list)
    previous_summary_id: str | None = None
    lineage_depth: int = 0
    created_at: datetime


class SeedRecord(BaseModel):
    id: str
    session_id: str
    lane: str = "general"
    topics: list[str] = Field(default_factory=list)
    seed_text: str
    subject_bins: list[str] = Field(default_factory=list)
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


class LaneWorkerRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_email: str
    lane: str = "general"
    subject_bins: list[str] = Field(default_factory=list)
    summary_text: str
    source_session_ids: list[str] = Field(default_factory=list)
    source_summary_ids: list[str] = Field(default_factory=list)
    source_seed_ids: list[str] = Field(default_factory=list)
    refreshed_at: datetime = Field(default_factory=utc_now)


class MemoryWorkersResponse(BaseModel):
    user_email: str
    workers: list[LaneWorkerRecord] = Field(default_factory=list)


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
    model_used: str = "whisper-1"
    fallback_used: bool = False