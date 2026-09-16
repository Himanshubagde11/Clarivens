"""
Standardized error responses for Clarivens API.
Never exposes stack traces, internal paths, or DB details.
"""
from typing import Optional, Any
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# -- Pre-defined error helpers --

def not_found(resource: str = "Resource", request_id: Optional[str] = None) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "error": {
                "code": f"{resource.upper().replace(' ', '_')}_NOT_FOUND",
                "message": f"The requested {resource.lower()} could not be found.",
                "request_id": request_id,
            }
        },
    )


def forbidden(request_id: Optional[str] = None) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={
            "error": {
                "code": "ACCESS_DENIED",
                "message": "You do not have permission to access this resource.",
                "request_id": request_id,
            }
        },
    )


def unauthorized(request_id: Optional[str] = None) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Authentication is required.",
                "request_id": request_id,
            }
        },
    )


def bad_request(message: str, code: str = "BAD_REQUEST", request_id: Optional[str] = None) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
            }
        },
    )


def internal_error(request_id: Optional[str] = None) -> HTTPException:
    """Generic 500 — never expose internal details."""
    return HTTPException(
        status_code=500,
        detail={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "request_id": request_id,
            }
        },
    )


# -- FastAPI Exception Handlers --

async def clarivens_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        payload = exc.detail
        if request_id and not payload["error"].get("request_id"):
            payload["error"]["request_id"] = request_id
        return JSONResponse(status_code=exc.status_code, content=payload)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
                "request_id": request_id,
            }
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The request payload failed input validation rules.",
                "details": exc.errors(),
                "request_id": request_id,
            }
        },
    )


async def rate_limit_exception_handler(request: Request, exc: Any) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Rate limit exceeded. Please throttle your requests.",
                "request_id": request_id,
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.error(f"[Unhandled Exception] request_id={request_id}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "A server error occurred. Our team has been notified.",
                "request_id": request_id,
            }
        },
    )
