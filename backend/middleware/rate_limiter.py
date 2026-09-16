"""
Rate limiting middleware for Clarivens using slowapi.
Provides rate limits for sensitive and compute-intensive endpoints.
Falls back gracefully if slowapi is not available.
"""
import logging
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    # Key by IP or authenticated user ID if present
    def get_identifier(request: Request) -> str:
        # If user is authenticated, use their ID or token header, otherwise remote IP
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[:25]
        return get_remote_address(request)

    limiter = Limiter(key_func=get_identifier, default_limits=["120/minute"])
    SLOWAPI_AVAILABLE = True

except ImportError:
    SLOWAPI_AVAILABLE = False
    limiter = None
    logger.warning("[Clarivens] slowapi not installed. Rate limiting will be simulated or disabled.")


# Specific limit definitions
LIMIT_UPLOAD = "10/minute"
LIMIT_AI = "15/minute"
LIMIT_AUTH = "20/minute"
LIMIT_PROJECTS = "30/minute"
LIMIT_GENERAL = "120/minute"
