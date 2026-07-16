"""Central typed configuration, loaded from .env."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM Provider Config
    llm_provider: str = "openrouter"
    
    # OpenRouter Config
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    primary_model: str = "anthropic/claude-3.5-sonnet"
    fast_model: str = "anthropic/claude-3-haiku"
    max_tokens: int = 4096
    
    # Database config
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "financial_research_agent"
    postgres_user: str = "postgres"
    postgres_password: str = ""
    
    # ChromaDB Vector Store
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_persist_dir: str = "./data/processed/chroma"
    chroma_collection_name: str = "financial_reports"
    
    # RAG Configuration
    # Embedding Model
    embedding_model: str = "BAAI/bge-m3"
    embedding_device: str = "cuda"  # cuda, cpu, mps
    embedding_batch_size: int = 32
    embedding_instruction: str = "Represent this financial document for retrieval:"
    
    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 50
    min_chunk_size: int = 100
    
    # Retrieval
    retrieval_top_k: int = 20
    retrieval_rerank_top_k: int = 10
    retrieval_score_threshold: float = 0.5
    
    # Reranker
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_device: str = "cuda"
    reranker_batch_size: int = 16
    
    # Caching
    embedding_cache_dir: str = "./data/processed/embedding_cache"
    embedding_cache_enabled: bool = True
    
    environment: str = "testing"
    log_level: str = "INFO"
    report_output_dir: str = "./data/reports"


    class Config:
        env_file = ".env"
