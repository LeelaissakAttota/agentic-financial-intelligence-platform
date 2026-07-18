"""PostgreSQL engine/session setup, reading from config.settings.
TODO (Day 1)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from config.settings import get_settings

_settings = None


def get_settings_instance():
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings


def get_engine():
    """Get or create the SQLAlchemy engine."""
    settings = get_settings_instance()
    url = (
        f"postgresql+psycopg2://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )
    return create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20)


def get_session_factory(engine=None):
    """Create a session factory."""
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_session():
    """Context manager for database sessions."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    """FastAPI dependency for database sessions."""
    with get_session() as session:
        yield session