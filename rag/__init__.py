"""
RAG Foundation Package - Core RAG infrastructure for financial document processing.

This package provides:
- Document ingestion (PDF processing, metadata extraction)
- Section-aware chunking
- Embedding generation with caching
- Vector storage with ChromaDB
- Retrieval with hybrid search and reranking
"""

from .ingestion import (
    PDFProcessor,
    ExtractedPage,
    DocumentMetadata,
    MetadataExtractor,
    FinancialMetadata,
    DocumentLoader,
    LoadedDocument,
    create_document_loader,
)

from .chunking.section_splitter import SectionDetector, SectionAwareChunker, Section, Chunk

from .embeddings import (
    EmbeddingService,
    EmbeddingCache,
    create_embedding_service,
    RerankerService,
    create_reranker_service,
)

from .vector_store import (
    ChromaVectorStore,
    SearchResult,
    SearchResponse,
    create_vector_store,
)

from .retriever import retrieve

__all__ = [
    # Ingestion
    "PDFProcessor",
    "ExtractedPage",
    "DocumentMetadata",
    "MetadataExtractor",
    "FinancialMetadata",
    "DocumentLoader",
    "LoadedDocument",
    "create_document_loader",
    # Chunking
    "SectionDetector",
    "SectionAwareChunker",
    "Section",
    "Chunk",
    # Embeddings
    "EmbeddingService",
    "EmbeddingCache",
    "create_embedding_service",
    "RerankerService",
    "create_reranker_service",
    # Vector Store
    "ChromaVectorStore",
    "SearchResult",
    "SearchResponse",
    "create_vector_store",
    # Retriever
    "retrieve",
]