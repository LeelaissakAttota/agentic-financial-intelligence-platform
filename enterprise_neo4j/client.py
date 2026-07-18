"""
Neo4j Client - Connection management and session handling for Neo4j graph database.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from dataclasses import dataclass
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable, AuthError

logger = logging.getLogger(__name__)


@dataclass
class Neo4jConfig:
    """Neo4j connection configuration."""
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"
    max_connection_pool_size: int = 50
    connection_timeout: float = 30.0
    max_retry_time: float = 30.0


class Neo4jClient:
    """
    Async Neo4j client with connection pooling, health checks, and session management.
    """
    
    def __init__(self, config: Optional[Neo4jConfig] = None):
        self.config = config or self._load_config_from_env()
        self._driver: Optional[AsyncDriver] = None
        self._initialized = False
    
    @staticmethod
    def _load_config_from_env() -> Neo4jConfig:
        """Load configuration from environment variables."""
        return Neo4jConfig(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            username=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
            database=os.getenv("NEO4J_DATABASE", "neo4j"),
            max_connection_pool_size=int(os.getenv("NEO4J_MAX_POOL_SIZE", "50")),
            connection_timeout=float(os.getenv("NEO4J_CONNECTION_TIMEOUT", "30.0")),
        )
    
    async def initialize(self) -> None:
        """Initialize the Neo4j driver and verify connection."""
        if self._initialized:
            return
        
        try:
            self._driver = AsyncGraphDatabase.driver(
                self.config.uri,
                auth=(self.config.username, self.config.password),
                max_connection_pool_size=self.config.max_connection_pool_size,
                connection_timeout=self.config.connection_timeout,
                max_retry_time=self.config.max_retry_time,
            )
            
            # Verify connectivity
            await self._driver.verify_connectivity()
            self._initialized = True
            logger.info(f"Neo4j client initialized: {self.config.uri}/{self.config.database}")
            
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            raise
        except AuthError as e:
            logger.error(f"Neo4j authentication failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j client: {e}")
            raise
    
    async def close(self) -> None:
        """Close the driver and release resources."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            self._initialized = False
            logger.info("Neo4j client closed")
    
    @asynccontextmanager
    async def session(self, **kwargs) -> AsyncSession:
        """Get a Neo4j session with automatic cleanup."""
        if not self._initialized:
            await self.initialize()
        
        session = self._driver.session(
            database=self.config.database,
            **kwargs
        )
        try:
            yield session
        finally:
            await session.close()
    
    async def execute_query(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results as list of dictionaries."""
        async with self.session() as session:
            result = await session.run(query, parameters or {}, **kwargs)
            records = []
            async for record in result:
                records.append(dict(record))
            return records
    
    async def execute_write(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Execute a write transaction."""
        async with self.session() as session:
            return await session.execute_write(
                lambda tx: tx.run(query, parameters or {}, **kwargs)
            )
    
    async def execute_read(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Execute a read transaction."""
        async with self.session() as session:
            result = await session.execute_read(
                lambda tx: tx.run(query, parameters or {}, **kwargs)
            )
            records = []
            async for record in result:
                records.append(dict(record))
            return records
    
    async def health_check(self) -> bool:
        """Check if Neo4j is reachable and responsive."""
        try:
            if not self._initialized:
                await self.initialize()
            await self._driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return False
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized


# Global client instance
_neo4j_client: Optional[Neo4jClient] = None


def get_neo4j_client(config: Optional[Neo4jConfig] = None) -> Neo4jClient:
    """Get or create the global Neo4j client instance."""
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient(config)
    return _neo4j_client


async def close_neo4j_client() -> None:
    """Close the global Neo4j client."""
    global _neo4j_client
    if _neo4j_client:
        await _neo4j_client.close()
        _neo4j_client = None