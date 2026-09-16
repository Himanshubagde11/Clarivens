"""
Structured logging setup for Clarivens.
Outputs JSON-structured logs compatible with Azure Application Insights.
"""
import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON for structured log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include exception info if present (without exposing full traceback in prod)
        if record.exc_info:
            log_entry["exception_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None

        # Include any extra fields set on the record
        for key in ("request_id", "user_id", "org_id", "audit", "event"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val

        return json.dumps(log_entry, default=str)


def configure_logging(level: str = "INFO") -> None:
    """
    Configure root logger with JSON formatting.
    Call once at application startup.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers = [handler]

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
