"""Central typed configuration, loaded from .env."""

from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # ==================== Environment ====================
    environment: str = Field(default="development", description="development, staging, production")
    debug: bool = Field(default=False, description="Enable debug mode")

    # ==================== LLM Provider Config ====================
    llm_provider: str = Field(default="openrouter", description="openrouter, anthropic, openai")

    # OpenRouter Config
    openrouter_api_key: str = Field(default="", description="OpenRouter API key")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", description="OpenRouter base URL")
    primary_model: str = Field(default="anthropic/claude-3.5-sonnet", description="Primary model for complex tasks")
    fast_model: str = Field(default="anthropic/claude-3-haiku", description="Fast model for simple tasks")
    max_tokens: int = Field(default=4096, description="Max tokens per request")
    temperature: float = Field(default=0.1, description="LLM temperature")

    # Retry/Timeout Settings
    llm_timeout: int = Field(default=60, description="LLM request timeout in seconds")
    llm_max_retries: int = Field(default=3, description="Max retries for LLM calls")
    llm_retry_delay: float = Field(default=1.0, description="Initial retry delay in seconds")

    # ==================== Database Config ====================
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="financial_research_agent", description="PostgreSQL database name")
    postgres_user: str = Field(default="postgres", description="PostgreSQL username")
    postgres_password: str = Field(default="", description="PostgreSQL password")
    postgres_pool_min: int = Field(default=5, description="Min connection pool size")
    postgres_pool_max: int = Field(default=20, description="Max connection pool size")
    postgres_pool_timeout: int = Field(default=30, description="Pool acquire timeout in seconds")

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # ==================== ChromaDB Vector Store ====================
    chroma_host: str = Field(default="localhost", description="ChromaDB host")
    chroma_port: int = Field(default=8000, description="ChromaDB port")
    chroma_persist_dir: str = Field(default="./data/processed/chroma", description="ChromaDB persist directory")
    chroma_collection_name: str = Field(default="financial_reports", description="ChromaDB collection name")
    chroma_tenant: str = Field(default="default_tenant", description="ChromaDB tenant")
    chroma_database: str = Field(default="default_database", description="ChromaDB database")

    # ==================== RAG Configuration ====================
    embedding_model: str = Field(default="BAAI/bge-m3", description="Embedding model name")
    embedding_device: str = Field(default="cuda", description="Embedding device: cuda, cpu, mps")
    embedding_batch_size: int = Field(default=32, description="Embedding batch size")
    embedding_instruction: str = Field(default="Represent this financial document for retrieval:", description="Embedding instruction")

    # Chunking
    chunk_size: int = Field(default=512, description="Chunk size in tokens")
    chunk_overlap: int = Field(default=50, description="Chunk overlap in tokens")
    min_chunk_size: int = Field(default=100, description="Minimum chunk size")

    # Retrieval
    retrieval_top_k: int = Field(default=20, description="Top K for retrieval")
    retrieval_rerank_top_k: int = Field(default=10, description="Top K after reranking")
    retrieval_score_threshold: float = Field(default=0.5, description="Minimum relevance score")

    # Reranker
    reranker_model: str = Field(default="BAAI/bge-reranker-v2-m3", description="Reranker model name")
    reranker_device: str = Field(default="cuda", description="Reranker device")
    reranker_batch_size: int = Field(default=16, description="Reranker batch size")

    # Caching
    embedding_cache_dir: str = Field(default="./data/processed/embedding_cache", description="Embedding cache directory")
    embedding_cache_enabled: bool = Field(default=True, description="Enable embedding cache")
    embedding_cache_ttl: int = Field(default=86400, description="Cache TTL in seconds (24h)")

    # ==================== Logging ====================
    log_level: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR")
    log_format: str = Field(default="json", description="Log format: json, text")
    log_file: Optional[str] = Field(default=None, description="Log file path (optional)")
    log_max_size: int = Field(default=10485760, description="Max log file size in bytes (10MB)")
    log_backup_count: int = Field(default=5, description="Number of backup log files")

    # ==================== Monitoring ====================
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=9090, description="Prometheus metrics port")
    metrics_path: str = Field(default="/metrics", description="Prometheus metrics endpoint")

    # ==================== Rate Limiting ====================
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Requests per window")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    rate_limit_burst: int = Field(default=20, description="Burst allowance")

    # ==================== Circuit Breaker ====================
    circuit_breaker_enabled: bool = Field(default=True, description="Enable circuit breaker")
    circuit_breaker_failure_threshold: int = Field(default=5, description="Failures before opening")
    circuit_breaker_recovery_timeout: int = Field(default=30, description="Recovery timeout in seconds")
    circuit_breaker_half_open_max_calls: int = Field(default=3, description="Max calls in half-open state")

    # ==================== Cache ====================
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_max_connections: int = Field(default=10, description="Max Redis connections")
    cache_default_ttl: int = Field(default=300, description="Default cache TTL in seconds")

    # ==================== Security ====================
    api_key_enabled: bool = Field(default=False, description="Enable API key authentication")
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    cors_enabled: bool = Field(default=True, description="Enable CORS")
    cors_origins: str = Field(default="*", description="Allowed CORS origins (comma-separated)")

    # ==================== Report Output ====================
    report_output_dir: str = Field(default="./data/reports", description="Report output directory")
    report_retention_days: int = Field(default=30, description="Report retention in days")

    # ==================== Worker Configuration ====================
    worker_concurrency: int = Field(default=4, description="Max concurrent worker tasks")
    worker_queue_size: int = Field(default=100, description="Worker queue size")
    worker_timeout: int = Field(default=300, description="Worker task timeout in seconds")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


# For backward compatibility
settings = get_settings()