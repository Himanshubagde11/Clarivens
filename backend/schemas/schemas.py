"""
Pydantic v2 request and response schemas for Clarivens API.
All API I/O is validated through these models — no raw dicts exposed.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
import re


# ============================================================
# Project Schemas
# ============================================================

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("name")
    @classmethod
    def name_no_special(cls, v: str) -> str:
        if not re.match(r"^[\w\s\-\.]+$", v):
            raise ValueError("Project name may only contain letters, numbers, spaces, hyphens, and dots.")
        return v.strip()


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: str
    owner_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectStatusResponse(BaseModel):
    project: ProjectResponse
    results: List[Dict[str, Any]]


# ============================================================
# Dataset / Upload Schemas
# ============================================================

class UploadResponse(BaseModel):
    message: str
    dataset_id: int
    job_id: str
    status: str = "queued"


# ============================================================
# Job Schemas
# ============================================================

class JobStatus(BaseModel):
    job_id: str
    status: str
    project_id: int
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ============================================================
# Analysis Result Schemas
# ============================================================

class AnalysisResultItem(BaseModel):
    type: str
    data: Dict[str, Any]


# ============================================================
# Auth Schemas
# ============================================================

class TokenRequest(BaseModel):
    username: str = Field(..., description="User email address")
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserCreate(BaseModel):
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=12, description="Minimum 12 characters")
    name: str = Field(..., min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Enter a valid email address.")
        return v


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    is_active: bool

    model_config = {"from_attributes": True}


# ============================================================
# Health Check Schema
# ============================================================

class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str = "1.0.0"
