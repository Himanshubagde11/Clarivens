"""
Authentication & authorization dependencies for Clarivens.

Currently implements local JWT authentication.
Designed to be swapped for Microsoft Entra External ID (OIDC) by
changing get_current_user() to validate Entra-issued tokens instead.

IMPORTANT: No mock users. Every protected endpoint requires a real
authenticated user identity.
"""
import logging
from typing import Optional
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.database import get_db
from backend.database import models
from backend.core.errors import unauthorized, forbidden

logger = logging.getLogger(__name__)

# OAuth2 scheme — token extracted from Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

# Optional: only import jose if available (graceful degradation for dev)
try:
    from jose import JWTError, jwt
    JOSE_AVAILABLE = True
except ImportError:
    JOSE_AVAILABLE = False
    logger.warning(
        "[Clarivens Auth] python-jose not installed. "
        "Install with: pip install python-jose[cryptography]. "
        "Authentication will be disabled in development mode."
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a JWT access token."""
    if not JOSE_AVAILABLE:
        raise RuntimeError("python-jose is required for JWT token creation.")

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.get_jwt_secret(), algorithm="HS256")


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Validates the JWT token and returns the authenticated User.

    In development (JOSE not installed or no token), raises 401.
    In production, this should be replaced/extended with Entra External ID
    token validation against the OIDC discovery endpoint.
    """
    request_id = getattr(request.state, "request_id", None)

    if not token:
        raise unauthorized(request_id)

    if not JOSE_AVAILABLE:
        raise unauthorized(request_id)

    try:
        secret = settings.get_jwt_secret()
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise unauthorized(request_id)
    except JWTError:
        raise unauthorized(request_id)

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise unauthorized(request_id)

    return user


def get_current_user_project(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
) -> models.Project:
    """
    IDOR protection: validates that the authenticated user owns or has
    access to the requested project.

    User A CANNOT access User B's project — even by guessing a project ID.
    Returns the project only if access is confirmed.
    """
    request_id = getattr(request.state, "request_id", None) if request else None

    project = db.query(models.Project).filter(models.Project.id == project_id).first()

    if project is None:
        # Return 404 not 403 to avoid leaking that the project exists
        from backend.core.errors import not_found
        raise not_found("Project", request_id)

    # Check ownership
    if project.owner_id != current_user.id:
        # Log the access attempt for audit
        logger.warning(
            "IDOR attempt: user %s tried to access project %s owned by user %s",
            current_user.id,
            project_id,
            project.owner_id,
        )
        # Return 404 not 403 — don't confirm project existence to unauthorized users
        from backend.core.errors import not_found
        raise not_found("Project", request_id)

    return project
