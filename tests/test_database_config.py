"""
Test database configuration for Phase 5 integration tests.
Provides correct PostgreSQL connection strings for integration tests.
"""
import os

# Test database configuration - uses the same database as the main application
TEST_DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
TEST_DB_PORT = os.getenv("POSTGRES_PORT", "5432")
TEST_DB_NAME = os.getenv("POSTGRES_DB", "financial_research_agent")
TEST_DB_USER = os.getenv("POSTGRES_USER", "postgres")
TEST_DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

# Connection string for tests
TEST_DATABASE_DSN = f"postgresql://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{TEST_DB_HOST}:{TEST_DB_PORT}/{TEST_DB_NAME}"

# Export for use in tests
__all__ = ["TEST_DATABASE_DSN", "TEST_DB_HOST", "TEST_DB_PORT", "TEST_DB_NAME", "TEST_DB_USER", "TEST_DB_PASSWORD"]