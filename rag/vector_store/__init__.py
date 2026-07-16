"""
RAG Vector Store Package - ChromaDB vector storage for financial documents.
"""

from .chroma_store import ChromaVectorStore, SearchResult, SearchResponse, create_vector_store

# Alias for backward compatibility
VectorStore = ChromaVectorStore

__all__ = [
    "ChromaVectorStore",
    "VectorStore",
    "SearchResult",
    "SearchResponse",
    "create_vector_store",
]