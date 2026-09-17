import os
import secrets
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Application ---
    app_name: str = "Clarivens AI Analytics Platform"
    environment: str = "development"

    # --- Database ---
    database_url: str = "sqlite:///./clarivens.db"

    # --- URLs & CORS ---
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:8000", "https://clarivens.clarivens-io.workers.dev"]

    # --- Authentication ---
    # No default — must be set in environment. Generated with: secrets.token_hex(32)
    jwt_secret: str = ""
    jwt_access_token_expire_minutes: int = 60

    # Entra External ID / OIDC (production)
    auth_issuer: str = ""
    auth_client_id: str = ""
    auth_client_secret: str = ""

    # --- AI / Gemini API ---
    # Put your Gemini API Key in your production environment variables / .env
    gemini_api_key: str = ""

    # --- Storage ---
    storage_backend: str = "local"  # local | azure
    azure_storage_account: str = ""
    azure_storage_container: str = "clarivens-data"
    azure_storage_connection_string: str = ""
    max_upload_size_mb: int = 50

    # --- Azure Service Bus ---
    azure_service_bus_connection: str = ""
    azure_service_bus_queue: str = "clarivens-jobs"
    job_backend: str = "memory"  # memory | azure_service_bus

    # --- Azure Key Vault ---
    azure_key_vault_url: str = ""

    # --- Monitoring ---
    applicationinsights_connection_string: str = ""

    # --- Payment ---
    payment_provider: str = "mock"
    payment_secret: str = ""

    # --- Clarivens AI Agent ---
    agent_enabled: bool = True
    agent_version: str = "1.0.0"
    agent_primary_model: str = "gemini-2.5-flash"
    agent_fast_model: str = "gemini-2.5-flash"
    # Max conversation turns before session is considered stale
    agent_max_session_messages: int = 50
    # Requests per minute per session (rate limit)
    agent_rate_limit_per_minute: int = 20
    # Knowledge base version tag
    agent_knowledge_version: str = "1.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def is_production(self) -> bool:
        return self.environment == "production"

    def get_jwt_secret(self) -> str:
        """
        Returns the JWT secret. In production, this MUST be set in the environment.
        For local dev, generates a warning if not set (uses a temporary random secret
        which will invalidate all tokens on restart).
        """
        if self.jwt_secret:
            return self.jwt_secret
        if self.is_production():
            raise ValueError(
                "JWT_SECRET must be set in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        # Development fallback: random per-process (tokens invalidate on restart)
        import warnings
        warnings.warn(
            "[Clarivens] JWT_SECRET not set — using ephemeral random secret. "
            "Set JWT_SECRET in .env for persistent sessions.",
            stacklevel=2,
        )
        return secrets.token_hex(32)


settings = Settings()
