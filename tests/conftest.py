"""
Test database configuration for Phase 5 tests.
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

# Alternative: if you want a separate test database
# TEST_DATABASE_DSN = "postgresql://postgres:postgres@localhost:5432/financial_research_test"

def get_test_dsn():
    """Get the test database DSN."""
    return TEST_DATABASE_DSN

def is_database_available():
    """Check if PostgreSQL is available for testing."""
    import asyncpg
    import asyncio
    
    async def check():
        try:
            conn = await asyncpg.connect(TEST_DATABASE_DSN)
            await conn.close()
            return True
        except Exception:
            return False
    
    return asyncio.run(check())