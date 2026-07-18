"""
Cross-Agent Semantic Intelligence Module
Provides vector similarity search, memory retrieval, cross-agent knowledge sharing,
semantic evidence lookup, and context ranking for the platform.
"""

from .embeddings import EmbeddingService, get_embedding_service
from .vector_store import VectorStore, get_vector_store
from .memory_retrieval import MemoryRetrieval, get_memory_retrieval
from .knowledge_sharing import KnowledgeSharing, get_knowledge_sharing
from .evidence_lookup import EvidenceLookup, get_evidence_lookup
from .context_ranker import ContextRanker, get_context_ranker

__all__ = [
    "EmbeddingService",
    "get_embedding_service",
    "VectorStore",
    "get_vector_store",
    "MemoryRetrieval",
    "get_memory_retrieval",
    "KnowledgeSharing",
    "get_knowledge_sharing",
    "EvidenceLookup",
    "get_evidence_lookup",
    "ContextRanker",
    "get_context_ranker",
]

__version__ = "1.0.0-phase9"