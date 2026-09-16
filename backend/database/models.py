"""
SQLAlchemy ORM models for Clarivens.
Designed for PostgreSQL (also compatible with SQLite for local dev).

Multi-tenant structure:
  User → Organization (via Membership) → Project → Dataset → AnalysisResult
"""
import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, ForeignKey,
    DateTime, Text, JSON, Enum, Index, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from backend.database.database import Base


# ============================================================
# Enums
# ============================================================

class MembershipRole(str, PyEnum):
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"


class ProjectStatus(str, PyEnum):
    created = "created"
    uploaded = "uploaded"
    queued = "queued"
    processing = "processing"
    profiling = "profiling"
    cleaning = "cleaning"
    eda = "eda"
    ai_analysis = "ai_analysis"
    ml_analysis = "ml_analysis"
    report_generation = "report_generation"
    completed = "completed"
    failed = "failed"


class JobStatus(str, PyEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class PaymentStatus(str, PyEnum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


# ============================================================
# Models
# ============================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth users
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    # For Entra External ID: store the external subject ID
    external_id = Column(String(255), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="owner")
    orders = relationship("Order", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")


class Organization(Base):
    """
    Tenant isolation unit. Every project belongs to an organization.
    Users access projects through Organization membership.
    """
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    memberships = relationship("Membership", back_populates="organization", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="organization")


class Membership(Base):
    """Links Users to Organizations with a role."""
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Enum(MembershipRole), default=MembershipRole.member, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="memberships")
    organization = relationship("Organization", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),
        Index("ix_membership_user_org", "user_id", "organization_id"),
    )


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    status = Column(
        Enum(ProjectStatus),
        default=ProjectStatus.created,
        nullable=False,
        index=True,
    )
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="projects")
    organization = relationship("Organization", back_populates="projects")
    datasets = relationship("Dataset", back_populates="project", cascade="all, delete-orphan")
    jobs = relationship("ProcessingJob", back_populates="project", cascade="all, delete-orphan")
    results = relationship("AnalysisResult", back_populates="project", cascade="all, delete-orphan")


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    # Safe storage name (UUID-based) — never the original filename
    storage_name = Column(String(255), nullable=False)
    # Original filename for display purposes only (never used as a path)
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=True)  # Full blob/file path
    file_type = Column(String(10), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    row_count = Column(Integer, nullable=True)
    column_count = Column(Integer, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="datasets")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False)  # UUID
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    job_type = Column(String(50), default="full_pipeline", nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.pending, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    # Only store non-sensitive log metadata — no raw data, no secrets
    logs = Column(Text, nullable=True)

    project = relationship("Project", back_populates="jobs")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    result_type = Column(String(50), nullable=False)  # profile | cleaning | eda | insights | ml | report
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="results")

    __table_args__ = (
        Index("ix_result_project_type", "project_id", "result_type"),
    )


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    service_name = Column(String(100), nullable=False)
    package_name = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.pending, nullable=False)
    idempotency_key = Column(String(100), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="orders")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(String(255), unique=True, index=True, nullable=True)
    status = Column(String(50), nullable=False)
    provider = Column(String(50), default="mock", nullable=False)
    processed_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    order = relationship("Order", back_populates="payments")


class AuditLog(Base):
    """
    Immutable audit trail. Never stores passwords, tokens, or raw datasets.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(100), nullable=True)
    status = Column(String(20), default="success", nullable=False)
    request_id = Column(String(36), nullable=True)
    detail = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_event_created", "event", "created_at"),
    )
