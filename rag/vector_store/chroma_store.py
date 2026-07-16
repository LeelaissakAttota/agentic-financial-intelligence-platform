"""
ChromaDB Vector Store for Financial Documents.

Provides persistent vector storage with hybrid search (vector + BM25),
metadata filtering, and retrieval capabilities.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import chromadb
from chromadb.config import Settings
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result from the vector store."""
    id: str
    document: str
    metadata: dict
    distance: float
    score: float  # 1 - distance for cosine similarity
    
    # Rerank score if available
    rerank_score: Optional[float] = None


@dataclass
class SearchResponse:
    """Response from a vector search query."""
    results: list[SearchResult]
    query: str
    total_found: int
    search_time_ms: float
    metadata_filter: Optional[dict] = None


class ChromaVectorStore:
    """ChromaDB vector store for financial document embeddings."""
    
    def __init__(
        self,
        persist_dir: str | Path = "./data/processed/chroma",
        collection_name: str = "financial_reports",
        embedding_dim: int = 1024,
        distance_metric: str = "cosine",
        **chroma_kwargs,
    ):
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self.distance_metric = distance_metric
        
        # Ensure persist directory exists
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
                **chroma_kwargs,
            ),
        )
        
        # Get or create collection
        self.collection = self._get_or_create_collection()
        
        # Stats
        self._stats = {
            "total_adds": 0,
            "total_queries": 0,
            "total_query_time_ms": 0,
        }
    
    def _get_or_create_collection(self):
        """Get existing collection or create new one."""
        try:
            collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=None,  # We provide embeddings manually
            )
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except Exception:
            # Create new collection
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={
                    "hnsw:space": self.distance_metric,
                    "embedding_dim": self.embedding_dim,
                },
                embedding_function=None,
            )
            logger.info(f"Created new collection: {self.collection_name}")
        
        return collection
    
    def add(
        self,
        documents: list[str],
        embeddings: list[list[float]] | np.ndarray,
        metadatas: list[dict],
        ids: Optional[list[str]] = None,
    ) -> list[str]:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of document texts
            embeddings: List of embedding vectors
            metadatas: List of metadata dicts
            ids: Optional list of IDs (generated if not provided)
            
        Returns:
            List of document IDs
        """
        if not documents:
            return []
        
        # Validate inputs
        n = len(documents)
        if len(embeddings) != n:
            raise ValueError(f"Embeddings count ({len(embeddings)}) != documents count ({n})")
        if len(metadatas) != n:
            raise ValueError(f"Metadatas count ({len(metadatas)}) != documents count ({n})")
        
        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in range(n)]
        elif len(ids) != n:
            raise ValueError(f"IDs count ({len(ids)}) != documents count ({n})")
        
        # Convert embeddings to list if numpy
        if isinstance(embeddings, np.ndarray):
            embeddings = embeddings.tolist()
        
        # Ensure metadata values are Chroma-compatible (str, int, float, bool)
        clean_metadatas = []
        for meta in metadatas:
            clean = {}
            for k, v in meta.items():
                if v is None:
                    clean[k] = ""
                elif isinstance(v, (str, int, float, bool)):
                    clean[k] = v
                else:
                    clean[k] = str(v)
            clean_metadatas.append(clean)
        
        # Add to collection
        start = time.time()
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=clean_metadatas,
            ids=ids,
        )
        
        elapsed = (time.time() - start) * 1000
        self._stats["total_adds"] += n
        logger.debug(f"Added {n} documents in {elapsed:.1f}ms")
        
        return ids
    
    def add_chunks(
        self,
        chunks: list[dict],
        embeddings: list[list[float]] | np.ndarray,
    ) -> list[str]:
        """
        Add document chunks with standardized metadata.
        
        Expected chunk format:
        {
            "text": "...",
            "company": "NVIDIA",
            "document_type": "10k",
            "fiscal_year": 2024,
            "fiscal_quarter": None,
            "section": "Item 7 - MD&A",
            "section_type": "mdna",
            "page_start": 42,
            "page_end": 45,
            "chunk_index": 0,
            "token_count": 450,
        }
        """
        documents = [c["text"] for c in chunks]
        metadatas = []
        
        for chunk in chunks:
            meta = {
                "company": chunk.get("company", ""),
                "document_type": chunk.get("document_type", ""),
                "fiscal_year": chunk.get("fiscal_year"),
                "fiscal_quarter": chunk.get("fiscal_quarter"),
                "section": chunk.get("section", ""),
                "section_type": chunk.get("section_type", ""),
                "page_start": chunk.get("page_start", 0),
                "page_end": chunk.get("page_end", 0),
                "chunk_index": chunk.get("chunk_index", 0),
                "token_count": chunk.get("token_count", 0),
                "source_document": chunk.get("source_document", ""),
            }
            metadatas.append(meta)
        
        return self.add(documents, embeddings, metadatas)
    
    def search(
        self,
        query_embedding: list[float] | np.ndarray,
        n_results: int = 10,
        where: Optional[dict] = None,
        where_document: Optional[dict] = None,
    ) -> SearchResponse:
        """
        Search for similar documents.
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Metadata filter (ChromaDB where clause)
            where_document: Document content filter
            
        Returns:
            SearchResponse with results
        """
        start = time.time()
        
        # Convert to list if numpy
        if isinstance(query_embedding, np.ndarray):
            query_embedding = query_embedding.tolist()
        
        # Execute query
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=["documents", "metadatas", "distances"],
        )
        
        elapsed = (time.time() - start) * 1000
        self._stats["total_queries"] += 1
        self._stats["total_query_time_ms"] += elapsed
        
        # Parse results
        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i]
                # Convert distance to similarity score (for cosine)
                if self.distance_metric == "cosine":
                    score = 1.0 - distance
                else:
                    score = 1.0 / (1.0 + distance)
                
                search_results.append(SearchResult(
                    id=doc_id,
                    document=results["documents"][0][i],
                    metadata=results["metadatas"][0][i],
                    distance=distance,
                    score=score,
                ))
        
        return SearchResponse(
            results=search_results,
            query="",  # Not stored in vector search
            total_found=len(search_results),
            search_time_ms=elapsed,
            metadata_filter=where,
        )
    
    def hybrid_search(
        self,
        query_embedding: list[float] | np.ndarray,
        query_text: str,
        n_results: int = 20,
        where: Optional[dict] = None,
        alpha: float = 0.5,
    ) -> SearchResponse:
        """
        Hybrid search combining vector similarity and BM25 (keyword).
        
        Note: ChromaDB doesn't natively support BM25 yet. This is a placeholder
        for future implementation or can be combined with external BM25 index.
        """
        # For now, just do vector search
        # TODO: Implement proper hybrid search with BM25
        response = self.search(
            query_embedding=query_embedding,
            n_results=n_results,
            where=where,
        )
        response.query = query_text
        return response
    
    def get_by_ids(self, ids: list[str]) -> list[SearchResult]:
        """Retrieve documents by their IDs."""
        results = self.collection.get(
            ids=ids,
            include=["documents", "metadatas"],
        )
        
        search_results = []
        if results["ids"]:
            for i, doc_id in enumerate(results["ids"]):
                search_results.append(SearchResult(
                    id=doc_id,
                    document=results["documents"][i],
                    metadata=results["metadatas"][i],
                    distance=0.0,
                    score=1.0,
                ))
        
        return search_results
    
    def get_by_company(
        self,
        company: str,
        limit: int = 100,
        document_type: Optional[str] = None,
    ) -> list[SearchResult]:
        """Get all chunks for a specific company."""
        where = {"company": company}
        if document_type:
            where["document_type"] = document_type
        
        results = self.collection.get(
            where=where,
            limit=limit,
            include=["documents", "metadatas"],
        )
        
        search_results = []
        if results["ids"]:
            for i, doc_id in enumerate(results["ids"]):
                search_results.append(SearchResult(
                    id=doc_id,
                    document=results["documents"][i],
                    metadata=results["metadatas"][i],
                    distance=0.0,
                    score=1.0,
                ))
        
        return search_results
    
    def delete_by_company(self, company: str) -> int:
        """Delete all documents for a company."""
        results = self.collection.get(where={"company": company}, include=[])
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            deleted = len(results["ids"])
            logger.info(f"Deleted {deleted} documents for company: {company}")
            return deleted
        return 0
    
    def delete_by_document(self, source_document: str) -> int:
        """Delete all chunks from a specific source document."""
        results = self.collection.get(where={"source_document": source_document}, include=[])
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            deleted = len(results["ids"])
            logger.info(f"Deleted {deleted} chunks for document: {source_document}")
            return deleted
        return 0
    
    def count(self, where: Optional[dict] = None) -> int:
        """Count documents in collection (with optional filter)."""
        if where:
            results = self.collection.get(where=where, include=[])
            return len(results["ids"])
        return self.collection.count()
    
    def get_stats(self) -> dict:
        """Get collection statistics."""
        total = self.collection.count()
        
        # Get unique companies
        results = self.collection.get(include=["metadatas"], limit=total)
        companies = set()
        doc_types = set()
        
        for meta in results["metadatas"]:
            if meta.get("company"):
                companies.add(meta["company"])
            if meta.get("document_type"):
                doc_types.add(meta["document_type"])
        
        return {
            "total_chunks": total,
            "unique_companies": len(companies),
            "companies": sorted(companies),
            "document_types": sorted(doc_types),
            "collection_name": self.collection_name,
            "persist_dir": str(self.persist_dir),
            "operations": self._stats,
        }
    
    def reset(self):
        """Delete and recreate the collection."""
        self.client.delete_collection(self.collection_name)
        self.collection = self._get_or_create_collection()
        self._stats = {
            "total_adds": 0,
            "total_queries": 0,
            "total_query_time_ms": 0,
        }
        logger.info(f"Reset collection: {self.collection_name}")

    def close(self):
        """Close the ChromaDB client and release SQLite locks."""
        # ChromaDB doesn't have an explicit close, but we can try to release the client
        # The client holds a reference to the SQLite connection
        self.client = None
        self.collection = None
        logger.info("Closed ChromaDB client")


def create_vector_store(config: Optional[dict] = None) -> ChromaVectorStore:
    """Factory function to create ChromaVectorStore from config."""
    if config is None:
        config = {}
    
    vector_config = config.get("vector_store", {})
    chroma_config = config.get("chroma", {})
    
    return ChromaVectorStore(
        persist_dir=vector_config.get("persist_dir", "./data/processed/chroma"),
        collection_name=vector_config.get("collection_name", "financial_reports"),
        embedding_dim=vector_config.get("embedding_dim", 1024),
        distance_metric=vector_config.get("distance_metric", "cosine"),
        **chroma_config,
    )