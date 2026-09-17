"""
Structured audit logging for Clarivens.
Tracks security-relevant events without logging secrets or raw data.
"""
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any, Dict

logger = logging.getLogger("clarivens.audit")


class AuditStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


class AuditEvent(str, Enum):
    # Auth
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGIN_FAILED = "LOGIN_FAILED"
    TOKEN_REFRESH = "TOKEN_REFRESH"

    # Projects
    PROJECT_CREATED = "PROJECT_CREATED"
    PROJECT_DELETED = "PROJECT_DELETED"
    PROJECT_ACCESSED = "PROJECT_ACCESSED"

    # Datasets
    DATASET_UPLOADED = "DATASET_UPLOADED"
    DATASET_DELETED = "DATASET_DELETED"
    DATASET_ACCESSED = "DATASET_ACCESSED"
    UPLOAD_REJECTED = "UPLOAD_REJECTED"

    # Analysis
    ANALYSIS_STARTED = "ANALYSIS_STARTED"
    ANALYSIS_COMPLETED = "ANALYSIS_COMPLETED"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"

    # Reports
    REPORT_CREATED = "REPORT_CREATED"
    REPORT_DOWNLOADED = "REPORT_DOWNLOADED"

    # Payments
    PAYMENT_CREATED = "PAYMENT_CREATED"
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"
    PAYMENT_FAILED = "PAYMENT_FAILED"

    # Security
    PERMISSION_DENIED = "PERMISSION_DENIED"
    PERMISSION_CHANGED = "PERMISSION_CHANGED"
    RATE_LIMITED = "RATE_LIMITED"


def log_event(
    event: AuditEvent,
    *,
    user_id: Optional[Any] = None,
    org_id: Optional[Any] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    status: Any = "success",
    request_id: Optional[str] = None,
    detail: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """
    Emit a structured audit log entry.
    """
    status_str = status.value if isinstance(status, AuditStatus) else str(status)
    event_str = event.value if isinstance(event, AuditEvent) else str(event)

    entry_meta = dict(metadata or {})
    for k, v in kwargs.items():
        if k == "details" and isinstance(v, dict):
            entry_meta.update(v)
        else:
            entry_meta[k] = v

    entry = {
        "audit": True,
        "event": event_str,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status_str,
        "user_id": str(user_id) if user_id else "anonymous",
        "org_id": str(org_id) if org_id else "none",
        "resource_type": resource_type,
        "resource_id": str(resource_id) if resource_id else (str(kwargs.get("project_id")) if kwargs.get("project_id") else None),
        "request_id": request_id or str(uuid.uuid4()),
        "detail": detail or error_message or str(kwargs.get("details") or ""),
        "metadata": entry_meta if entry_meta else None,
    }

    # Clean out None
    entry = {k: v for k, v in entry.items() if v is not None}

    if status_str in ["failure", "denied"]:
        logger.warning("AUDIT: %s", entry)
    else:
        logger.info("AUDIT: %s", entry)


# Alias
def log_audit_event(event: AuditEvent, status: Any = AuditStatus.SUCCESS, **kwargs):
    return log_event(event=event, status=status, **kwargs)
