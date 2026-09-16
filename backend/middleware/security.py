"""
Security headers middleware for Clarivens.
Injects standard security headers on every response.
Request ID is generated per-request for tracing.
"""
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from backend.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses.
    CSP is configured to allow the existing Clarivens fonts/styles without
    breaking the approved UI.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Attach a unique request ID for log tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)

        # --- Core security headers ---
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["X-Request-ID"] = request_id

        # HSTS — only set on production (HTTPS)
        if settings.is_production():
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content-Security-Policy
        # Allows: inline styles (required for existing CSS), Google Fonts,
        # EmailJS CDN, formspree, same-origin scripts.
        # Does NOT allow eval() or external scripts from unknown origins.
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdn.emailjs.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: blob:",
            "connect-src 'self' https://formspree.io https://api.emailjs.com",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self' https://formspree.io",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        return response
