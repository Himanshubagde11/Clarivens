"""
Database connection for Clarivens.
Supports SQLite (local dev) and PostgreSQL (production).
Connection pooling configured for PostgreSQL.
"""
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.config import settings

logger = logging.getLogger(__name__)

IS_SQLITE = settings.database_url.startswith("sqlite")

# Connection arguments differ between SQLite and PostgreSQL
connect_args = {}
pool_kwargs = {}

if IS_SQLITE:
    # SQLite: single-thread check disabled for FastAPI's async/threadpool use
    connect_args["check_same_thread"] = False
    logger.warning(
        "[Clarivens DB] Using SQLite. "
        "Set DATABASE_URL to a PostgreSQL connection string for production."
    )
else:
    # PostgreSQL: connection pooling
    pool_kwargs = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,       # verify connections before use
        "pool_recycle": 1800,        # recycle connections every 30 minutes
    }

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    **pool_kwargs,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
