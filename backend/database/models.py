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
    queued = "queued"
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


# ============================================================
# Clarivens AI Agent — New Models (appended, nothing above changed)
# ============================================================

class ConversationState(str, PyEnum):
    discovery = "discovery"
    requirement_analysis = "requirement_analysis"
    service_match = "service_match"
    package_match = "package_match"
    data_request = "data_request"
    data_analysis = "data_analysis"
    result_explanation = "result_explanation"
    report = "report"
    follow_up = "follow_up"
    lead_capture = "lead_capture"


class AgentRole(str, PyEnum):
    visitor = "visitor"
    client = "client"
    analyst = "analyst"
    admin = "admin"


class ServiceCategory(str, PyEnum):
    data_services = "data_services"
    analytics = "analytics"
    bi = "bi"
    ai_ml = "ai_ml"
    forecasting = "forecasting"
    enterprise = "enterprise"


class ServiceCatalog(Base):
    """
    Clarivens service taxonomy — configurable from admin, never hardcoded in prompts.
    """
    __tablename__ = "service_catalog"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(Enum(ServiceCategory), nullable=False, index=True)
    description = Column(Text, nullable=False)
    short_description = Column(String(300), nullable=True)
    # JSON list of feature strings
    features = Column(JSON, nullable=True)
    # Keywords for intent matching
    keywords = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    packages = relationship("ServicePackage", back_populates="service", cascade="all, delete-orphan")


class ServicePackage(Base):
    """
    Packages under a service — all pricing comes from here, never from the LLM.
    """
    __tablename__ = "service_packages"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("service_catalog.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    # JSON: {"rows": 100000, "datasets": 3, "turnaround_days": 5}
    limits = Column(JSON, nullable=True)
    # JSON list of included feature strings
    features = Column(JSON, nullable=True)
    # JSON list of available add-on strings
    addons = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    service = relationship("ServiceCatalog", back_populates="packages")


class AgentSession(Base):
    """
    One session per visitor/client conversation.
    Anonymous sessions have user_id = NULL.
    """
    __tablename__ = "agent_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, index=True, nullable=False)  # UUID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    role = Column(Enum(AgentRole), default=AgentRole.visitor, nullable=False)
    state = Column(Enum(ConversationState), default=ConversationState.discovery, nullable=False)
    # Structured requirements extracted from conversation
    requirements = Column(JSON, nullable=True)
    # Detected industry, dataset info, etc.
    context = Column(JSON, nullable=True)
    agent_version = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    messages = relationship("AgentMessage", back_populates="session", cascade="all, delete-orphan")
    tool_calls = relationship("AgentToolCall", back_populates="session", cascade="all, delete-orphan")
    feedback = relationship("AgentFeedback", back_populates="session", cascade="all, delete-orphan")
    memory = relationship("AgentMemory", back_populates="session", cascade="all, delete-orphan")
    metrics = relationship("AgentMetric", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_agent_session_user", "user_id", "is_active"),
    )


class AgentMessage(Base):
    """
    Every message in a session — user, assistant, or system.
    """
    __tablename__ = "agent_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    # role: user | assistant | system | tool
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    # Detected intent for this message
    intent = Column(String(50), nullable=True)
    # Tool calls made while generating this response (JSON array)
    tool_calls_json = Column(JSON, nullable=True)
    # Token usage for this message
    tokens_used = Column(Integer, nullable=True)
    model_used = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    session = relationship("AgentSession", back_populates="messages")
    feedback_items = relationship("AgentFeedback", back_populates="message", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_agent_message_session", "session_id", "created_at"),
    )


class AgentToolCall(Base):
    """
    Audit log of every tool call made by the agent.
    Never stores raw dataset contents.
    """
    __tablename__ = "agent_tool_calls"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(Integer, ForeignKey("agent_messages.id", ondelete="CASCADE"), nullable=True, index=True)
    tool_name = Column(String(100), nullable=False, index=True)
    # Sanitized args (no secrets, no raw data)
    args_json = Column(JSON, nullable=True)
    # Sanitized result summary
    result_summary = Column(String(500), nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    # low | medium | high
    risk_level = Column(String(20), default="low", nullable=False)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    session = relationship("AgentSession", back_populates="tool_calls")

    __table_args__ = (
        Index("ix_tool_call_session_tool", "session_id", "tool_name"),
    )


class AgentFeedback(Base):
    """
    Structured user feedback on agent responses.
    Used for the continuous learning pipeline.
    """
    __tablename__ = "agent_feedback"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(Integer, ForeignKey("agent_messages.id", ondelete="CASCADE"), nullable=True, index=True)
    # helpful | not_helpful | incorrect | excellent | missing_info
    rating = Column(String(30), nullable=False)
    # Optional free-text correction/comment
    correction = Column(Text, nullable=True)
    # Detected intent at time of feedback
    intent = Column(String(50), nullable=True)
    agent_version = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    session = relationship("AgentSession", back_populates="feedback")
    message = relationship("AgentMessage", back_populates="feedback_items")

    __table_args__ = (
        Index("ix_feedback_session_rating", "session_id", "rating"),
    )


class AgentMemory(Base):
    """
    Key-value long-term memory per session/user.
    Stores extracted requirements, industry, dataset info.
    """
    __tablename__ = "agent_memory"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    # e.g. "industry", "business_problem", "dataset_type", "requirements"
    key = Column(String(100), nullable=False)
    # JSON value
    value = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    session = relationship("AgentSession", back_populates="memory")

    __table_args__ = (
        UniqueConstraint("session_id", "key", name="uq_memory_session_key"),
        Index("ix_agent_memory_session_key", "session_id", "key"),
    )


class AgentKnowledge(Base):
    """
    Versioned knowledge base — Clarivens services, methodology, FAQs, SOPs.
    Used for RAG retrieval. No vector DB needed initially (keyword search).
    """
    __tablename__ = "agent_knowledge"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    content = Column(Text, nullable=False)
    # service | methodology | faq | industry | pricing | sop | case_study
    category = Column(String(50), nullable=False, index=True)
    # Tags for keyword search
    tags = Column(JSON, nullable=True)
    # Knowledge base version: e.g. "1.0"
    kb_version = Column(String(20), default="1.0", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        Index("ix_knowledge_category_version", "category", "kb_version"),
    )


class AgentVersion(Base):
    """
    Versioned agent configuration — every production deployment is recorded.
    """
    __tablename__ = "agent_versions"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(20), nullable=False, unique=True)  # e.g. "1.0.0"
    primary_model = Column(String(100), nullable=False)
    fast_model = Column(String(100), nullable=False)
    prompt_version = Column(String(20), nullable=True)
    knowledge_version = Column(String(20), nullable=True)
    tool_version = Column(String(20), nullable=True)
    policy_version = Column(String(20), nullable=True)
    # evaluation scores JSON
    eval_scores = Column(JSON, nullable=True)
    # draft | staging | production | deprecated
    status = Column(String(20), default="draft", nullable=False, index=True)
    release_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    activated_at = Column(DateTime, nullable=True)


class AgentMetric(Base):
    """
    Per-session usage and performance metrics.
    Used for cost optimization and quality monitoring.
    """
    __tablename__ = "agent_metrics"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    total_messages = Column(Integer, default=0, nullable=False)
    total_tool_calls = Column(Integer, default=0, nullable=False)
    total_tokens_in = Column(Integer, default=0, nullable=False)
    total_tokens_out = Column(Integer, default=0, nullable=False)
    # Estimated cost in USD
    estimated_cost_usd = Column(Float, default=0.0, nullable=False)
    # Average response latency ms
    avg_latency_ms = Column(Float, nullable=True)
    # Service ultimately recommended
    recommended_service = Column(String(100), nullable=True)
    # Whether a lead was created
    led_to_lead = Column(Boolean, default=False, nullable=False)
    # Whether an order was created
    led_to_order = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    session = relationship("AgentSession", back_populates="metrics")

    __table_args__ = (
        Index("ix_agent_metric_session", "session_id"),
    )


class Lead(Base):
    """
    Visitor leads captured by the AI agent during service discovery.
    """
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(200), nullable=True)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    company = Column(String(200), nullable=True)
    industry = Column(String(100), nullable=True)
    business_type = Column(String(100), nullable=True)
    business_problem = Column(Text, nullable=True)
    requirement = Column(Text, nullable=True)
    # Recommended service at time of lead capture
    recommended_service = Column(String(100), nullable=True)
    recommended_package = Column(String(100), nullable=True)
    recommended_budget = Column(String(100), nullable=True)
    timeline = Column(String(100), nullable=True)
    # new | contacted | converted | closed
    status = Column(String(30), default="new", nullable=False, index=True)
    dataset_available = Column(Boolean, nullable=True)
    source = Column(String(50), default="ai_agent", nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        Index("ix_lead_email_status", "email", "status"),
    )
