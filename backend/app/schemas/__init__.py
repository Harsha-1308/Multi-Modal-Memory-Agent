from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SeedMemory(BaseModel):
    text: str


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1)
    project_type: str = "code"
    description: str = ""
    seed_memories: Optional[List[SeedMemory]] = None


class ProjectResponse(BaseModel):
    project_id: str
    name: str
    project_type: str
    description: str
    hindsight_bank_id: str
    created_at: str
    updated_at: str


class ChatCreate(BaseModel):
    name: str = Field(..., min_length=1)


class ChatSettingsUpdate(BaseModel):
    memory_enabled: bool


class ChatResponse(BaseModel):
    chat_id: str
    project_id: str
    name: str
    memory_enabled: bool
    created_at: str
    updated_at: str


class MessageItem(BaseModel):
    message_id: str
    role: str
    content: str
    created_at: str


class MemoryStatus(BaseModel):
    enabled: bool
    mode: str
    status: str


class EvidenceBlock(BaseModel):
    source_evidence: List[Any] = Field(default_factory=list)
    learning_evidence: Dict[str, Any] = Field(default_factory=dict)
    learning_state: Optional[Dict[str, Any]] = None
    understanding: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    message: MessageItem
    memory: MemoryStatus
    evidence: EvidenceBlock
    attachments: List[Any] = Field(default_factory=list)
    user_message_id: Optional[str] = None


class EvidenceResponse(BaseModel):
    evidence_id: str
    project_id: str
    chat_id: str
    message_id: Optional[str] = None
    kind: str
    original_filename: str
    mime_type: str
    storage_key: str
    sha256: str
    size_bytes: int
    user_description: Optional[str] = None
    semantic_description: Optional[str] = None
    combined_understanding: Optional[str] = None
    canonical_memory_id: Optional[int] = None
    created_at: str


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
