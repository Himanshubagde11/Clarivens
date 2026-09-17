"""
Clarivens AI Agent — Memory Manager.

Manages multi-level memory:
1. Short-term: current conversation messages (AgentMessage table)
2. Session memory: key-value store for extracted requirements (AgentMemory table)
3. Session context: structured JSON (AgentSession.context)

Also manages session lifecycle: creation, retrieval, update.
"""
import uuid
import logging
import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session

from backend.database import models
from backend.config import settings

logger = logging.getLogger(__name__)


# ============================================================
# Session Management
# ============================================================

def create_session(
    db: Session,
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
    role: str = "visitor",
) -> models.AgentSession:
    """Creates a new agent session."""
    session = models.AgentSession(
        session_id=str(uuid.uuid4()),
        user_id=user_id,
        project_id=project_id,
        role=role,
        state="discovery",
        requirements={},
        context={},
        agent_version=settings.agent_version,
        is_active=True,
    )
    db.add(session)

    # Create associated metrics record
    metric = models.AgentMetric(session_id=None)  # will be linked after flush
    db.flush()  # Get session.id
    metric.session_id = session.id
    db.add(metric)
    db.commit()
    db.refresh(session)
    logger.info("[Memory] Created session %s (user=%s, role=%s)", session.session_id, user_id, role)
    return session


def get_session(db: Session, session_id: str) -> Optional[models.AgentSession]:
    """Retrieves an active session by UUID."""
    return db.query(models.AgentSession).filter(
        models.AgentSession.session_id == session_id,
        models.AgentSession.is_active == True,
    ).first()


def get_or_create_session(
    db: Session,
    session_id: Optional[str],
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
    role: str = "visitor",
) -> models.AgentSession:
    """Gets an existing session or creates a new one."""
    if session_id:
        existing = get_session(db, session_id)
        if existing:
            return existing
    return create_session(db, user_id=user_id, project_id=project_id, role=role)


def update_session_state(
    db: Session,
    session: models.AgentSession,
    new_state: str,
    requirements: Optional[dict] = None,
    context_update: Optional[dict] = None,
) -> None:
    """Updates session state and optionally merges requirements/context."""
    session.state = new_state
    if requirements:
        current_reqs = session.requirements or {}
        current_reqs.update(requirements)
        session.requirements = current_reqs
    if context_update:
        current_ctx = session.context or {}
        current_ctx.update(context_update)
        session.context = current_ctx
    session.updated_at = datetime.datetime.utcnow()
    db.commit()


# ============================================================
# Message Management
# ============================================================

def add_message(
    db: Session,
    session: models.AgentSession,
    role: str,
    content: str,
    intent: Optional[str] = None,
    tokens_used: Optional[int] = None,
    model_used: Optional[str] = None,
    tool_calls_json: Optional[list] = None,
) -> models.AgentMessage:
    """Persists a message to the conversation history."""
    message = models.AgentMessage(
        session_id=session.id,
        role=role,
        content=content,
        intent=intent,
        tokens_used=tokens_used,
        model_used=model_used,
        tool_calls_json=tool_calls_json,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_conversation_history(
    db: Session,
    session: models.AgentSession,
    max_messages: int = 20,
) -> list[dict]:
    """
    Returns the conversation history as a list of {role, content} dicts.
    Only user and assistant messages — system messages are excluded.
    Capped at max_messages to avoid token overflow.
    """
    messages = (
        db.query(models.AgentMessage)
        .filter(
            models.AgentMessage.session_id == session.id,
            models.AgentMessage.role.in_(["user", "assistant"]),
        )
        .order_by(models.AgentMessage.created_at.asc())
        .limit(max_messages)
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in messages]


def get_message_count(db: Session, session: models.AgentSession) -> int:
    """Returns total message count for a session."""
    return db.query(models.AgentMessage).filter(
        models.AgentMessage.session_id == session.id
    ).count()


# ============================================================
# Session Memory (key-value)
# ============================================================

def set_memory(
    db: Session,
    session: models.AgentSession,
    key: str,
    value: Any,
) -> None:
    """Sets or updates a memory key for a session."""
    existing = db.query(models.AgentMemory).filter(
        models.AgentMemory.session_id == session.id,
        models.AgentMemory.key == key,
    ).first()

    if existing:
        existing.value = value
        existing.updated_at = datetime.datetime.utcnow()
    else:
        mem = models.AgentMemory(
            session_id=session.id,
            key=key,
            value=value,
        )
        db.add(mem)
    db.commit()


def get_memory(
    db: Session,
    session: models.AgentSession,
    key: str,
    default: Any = None,
) -> Any:
    """Retrieves a memory value for a session."""
    mem = db.query(models.AgentMemory).filter(
        models.AgentMemory.session_id == session.id,
        models.AgentMemory.key == key,
    ).first()
    return mem.value if mem else default


def get_all_memory(db: Session, session: models.AgentSession) -> dict:
    """Returns all memory key-value pairs for a session."""
    items = db.query(models.AgentMemory).filter(
        models.AgentMemory.session_id == session.id
    ).all()
    return {m.key: m.value for m in items}


# ============================================================
# Tool Call Audit
# ============================================================

def log_tool_call(
    db: Session,
    session: models.AgentSession,
    tool_name: str,
    args: Optional[dict],
    result_summary: Optional[str],
    success: bool,
    risk_level: str = "low",
    duration_ms: Optional[int] = None,
    message_id: Optional[int] = None,
) -> None:
    """Records a tool call in the audit log."""
    call = models.AgentToolCall(
        session_id=session.id,
        message_id=message_id,
        tool_name=tool_name,
        args_json=args,
        result_summary=result_summary[:500] if result_summary else None,
        success=success,
        risk_level=risk_level,
        duration_ms=duration_ms,
    )
    db.add(call)
    db.commit()


# ============================================================
# Metrics Update
# ============================================================

def update_metrics(
    db: Session,
    session: models.AgentSession,
    tokens_in: int = 0,
    tokens_out: int = 0,
    tool_calls_delta: int = 0,
    latency_ms: Optional[float] = None,
) -> None:
    """Updates usage metrics for a session."""
    metric = db.query(models.AgentMetric).filter(
        models.AgentMetric.session_id == session.id
    ).first()
    if not metric:
        return

    metric.total_messages += 1
    metric.total_tokens_in += tokens_in
    metric.total_tokens_out += tokens_out
    metric.total_tool_calls += tool_calls_delta

    # Rough cost estimate: gemini-2.5-flash ≈ $0.075/1M input + $0.30/1M output
    cost = (tokens_in / 1_000_000 * 0.075) + (tokens_out / 1_000_000 * 0.30)
    metric.estimated_cost_usd += cost

    if latency_ms:
        # Rolling average
        n = metric.total_messages
        prev_avg = metric.avg_latency_ms or 0
        metric.avg_latency_ms = (prev_avg * (n - 1) + latency_ms) / n

    metric.updated_at = datetime.datetime.utcnow()
    db.commit()
