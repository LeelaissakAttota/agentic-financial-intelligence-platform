"""PostgreSQL engine/session setup, reading from config.settings.
TODO (Day 1)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def get_engine(settings):
    url = (
        f"postgresql+psycopg2://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )
    return create_engine(url)


def get_session_factory(engine):
    return sessionmaker(bind=engine)
