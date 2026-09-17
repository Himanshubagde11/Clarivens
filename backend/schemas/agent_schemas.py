"""
Clarivens AI Agent — Pydantic Schemas.

All request/response schemas for the agent API endpoints.
Strict validation prevents malformed or oversized inputs.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator
import re


# ============================================================
# Session
# ============================================================

class CreateSessionRequest(BaseModel):
    project_id: Optional[int] = Field(None, description="Active project context (authenticated users)")


class SessionResponse(BaseModel):
    session_id: str
    state: str
    role: str
    project_id: Optional[int] = None
    agent_version: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================
# Chat
# ============================================================

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="User message")
    session_id: Optional[str] = Field(None, description="Existing session UUID")
    project_id: Optional[int] = Field(None, description="Active project ID (authenticated users)")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        # Strip leading/trailing whitespace
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        return v


class ToolResultPublic(BaseModel):
    tool: str
    summary: str


class ChatResponse(BaseModel):
    session_id: str
    message: str
    intent: str
    state: str
    suggested_actions: list[str] = []
    requires_lead_capture: bool = False
    requires_file_upload: bool = False
    project_id: Optional[int] = None
    tool_results: list[ToolResultPublic] = []
    # Token count for transparency (not sensitive)
    tokens_used: int = 0


# ============================================================
# Feedback
# ============================================================

VALID_RATINGS = {"helpful", "not_helpful", "incorrect", "excellent", "missing_info"}


class FeedbackRequest(BaseModel):
    session_id: str = Field(..., description="Session UUID")
    message_id: int = Field(..., description="Message ID to give feedback on")
    rating: str = Field(..., description="helpful | not_helpful | incorrect | excellent | missing_info")
    correction: Optional[str] = Field(None, max_length=1000, description="Optional correction text")

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: str) -> str:
        if v not in VALID_RATINGS:
            raise ValueError(f"rating must be one of: {', '.join(VALID_RATINGS)}")
        return v


class FeedbackResponse(BaseModel):
    success: bool
    message: str


# ============================================================
# Session History
# ============================================================

class MessagePublic(BaseModel):
    id: int
    role: str
    content: str
    intent: Optional[str] = None
    tokens_used: Optional[int] = None
    created_at: str

    class Config:
        from_attributes = True


class SessionHistoryResponse(BaseModel):
    session_id: str
    state: str
    messages: list[MessagePublic]
    total_messages: int


# ============================================================
# Lead Capture
# ============================================================

class LeadCaptureRequest(BaseModel):
    session_id: str
    name: Optional[str] = Field(None, max_length=200)
    email: str = Field(..., max_length=255)
    company: Optional[str] = Field(None, max_length=200)
    industry: Optional[str] = Field(None, max_length=100)
    requirement: Optional[str] = Field(None, max_length=1000)
    dataset_available: Optional[bool] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email address")
        return v


class LeadCaptureResponse(BaseModel):
    success: bool
    message: str
    lead_id: Optional[int] = None


# ============================================================
# Project Context
# ============================================================

class ProjectContextResponse(BaseModel):
    project_id: int
    name: str
    status: str
    has_results: bool
    available_analyses: list[str]


# ============================================================
# Agent Status
# ============================================================

class AgentStatusResponse(BaseModel):
    status: str
    version: str
    primary_model: str
    fast_model: str
    enabled: bool


# ============================================================
# Admin — Knowledge
# ============================================================

class KnowledgeChunkRequest(BaseModel):
    title: str = Field(..., max_length=200)
    content: str = Field(..., max_length=8000)
    category: str = Field(..., max_length=50)
    tags: Optional[list[str]] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid = {"service", "methodology", "faq", "industry", "pricing", "sop", "case_study"}
        if v not in valid:
            raise ValueError(f"category must be one of: {', '.join(valid)}")
        return v


class KnowledgeChunkResponse(BaseModel):
    id: int
    title: str
    category: str
    kb_version: str
    created_at: str

    class Config:
        from_attributes = True
