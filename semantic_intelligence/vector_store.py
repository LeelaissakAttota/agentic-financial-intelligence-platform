"""
Vector Store - Vector database operations for semantic similarity search.
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


class VectorStoreBackend(str, Enum):
    """Supported vector store backends."""
    CHROMADB = "chromadb"
    FAISS = "faiss"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    QDRANT = "qdrant"
    IN_MEMORY = "in_memory"


@dataclass
class VectorStoreConfig:
    """Configuration for vector store."""
    backend: VectorStoreBackend = VectorStoreBackend.CHROMADB
    collection_name: str = "financial_knowledge"
    persist_directory: str = "./data/chromadb"
    embedding_dimension: int = 1024
    distance_metric: str = "cosine"  # cosine, euclidean, dot_product
    
    # ChromaDB specific
    chromadb_host: Optional[str] = None
    chromadb_port: int = 8000
    
    # Pinecone specific
    pinecone_api_key: Optional[str] = None
    pinecone_environment: Optional[str] = None
    pinecone_index: Optional[str] = None
    
    # Weaviate specific
    weaviate_url: Optional[str] = None
    weaviate_api_key: Optional[str] = None
    
    # Qdrant specific
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None


@dataclass
class VectorDocument:
    """Document stored in vector store."""
    id: str
    embedding: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)
    content: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SearchResult:
    """Result of vector similarity search."""
    id: str
    score: float
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None


@dataclass
class SearchQuery:
    """Vector search query."""
    query_embedding: np.ndarray
    top_k: int = 10
    filter_metadata: Optional[Dict[str, Any]] = None
    min_score: float = 0.0
    include_embeddings: bool = False


class VectorStore:
    """
    Abstract vector store interface with multiple backend support.
    """
    
    def __init__(self, config: Optional[VectorStoreConfig] = None):
        self.config = config or VectorStoreConfig()
        self._client = None
        self._collection = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the vector store."""
        if self._initialized:
            return
        
        try:
            if self.config.backend == VectorStoreBackend.CHROMADB:
                await self._init_chromadb()
            elif self.config.backend == VectorStoreBackend.FAISS:
                await self._init_faiss()
            elif self.config.backend == VectorStoreBackend.IN_MEMORY:
                await self._init_in_memory()
            else:
                raise NotImplementedError(f"Backend {self.config.backend} not implemented")
            
            self._initialized = True
            logger.info(f"Vector store initialized: {self.config.backend.value}")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    async def _init_chromadb(self) -> None:
        """Initialize ChromaDB client."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            if self.config.chromadb_host:
                # Remote ChromaDB
                self._client = chromadb.HttpClient(
                    host=self.config.chromadb_host,
                    port=self.config.chromadb_port
                )
            else:
                # Local persistent ChromaDB
                self._client = chromadb.PersistentClient(
                    path=self.config.persist_directory,
                    settings=Settings(anonymized_telemetry=False)
                )
            
            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=self.config.collection_name,
                metadata={"hnsw:space": self.config.distance_metric}
            )
            
            logger.info(f"ChromaDB collection '{self.config.collection_name}' ready")
            
        except ImportError:
            raise RuntimeError("chromadb package required. Install with: pip install chromadb")
    
    async def _init_faiss(self) -> None:
        """Initialize FAISS index."""
        try:
            import faiss
            
            # Create FAISS index
            if self.config.distance_metric == "cosine":
                # For cosine similarity, use inner product with normalized vectors
                self._index = faiss.IndexFlatIP(self.config.embedding_dimension)
            elif self.config.distance_metric == "euclidean":
                self._index = faiss.IndexFlatL2(self.config.embedding_dimension)
            else:
                self._index = faiss.IndexFlatIP(self.config.embedding_dimension)
            
            # Storage for metadata
            self._metadata_store: Dict[int, Dict[str, Any]] = {}
            self._content_store: Dict[int, str] = {}
            self._id_to_index: Dict[str, int] = {}
            self._next_index = 0
            
            logger.info(f"FAISS index created (dim={self.config.embedding_dimension})")
            
        except ImportError:
            raise RuntimeError("faiss package required. Install with: pip install faiss-cpu")
    
    async def _init_in_memory(self) -> None:
        """Initialize in-memory vector store."""
        self._vectors: Dict[str, VectorDocument] = {}
        self._initialized = True
        logger.info("In-memory vector store initialized")
    
    async def add_documents(self, documents: List[VectorDocument]) -> List[str]:
        """Add documents to the vector store."""
        if not self._initialized:
            await self.initialize()
        
        if self.config.backend == VectorStoreBackend.CHROMADB:
            return await self._add_chromadb(documents)
        elif self.config.backend == VectorStoreBackend.FAISS:
            return await self._add_faiss(documents)
        elif self.config.backend == VectorStoreBackend.IN_MEMORY:
            return await self._add_in_memory(documents)
        else:
            raise NotImplementedError(f"Backend {self.config.backend} not implemented")
    
    async def _add_chromadb(self, documents: List[VectorDocument]) -> List[str]:
        """Add documents to ChromaDB."""
        ids = [doc.id for doc in documents]
        embeddings = [doc.embedding.tolist() for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        contents = [doc.content for doc in documents]
        
        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=contents
        )
        
        return ids
    
    async def _add_faiss(self, documents: List[VectorDocument]) -> List[str]:
        """Add documents to FAISS index."""
        ids = []
        embeddings = []
        
        for doc in documents:
            idx = self._next_index
            self._next_index += 1
            
            self._id_to_index[doc.id] = idx
            self._metadata_store[idx] = doc.metadata
            self._content_store[idx] = doc.content
            embeddings.append(doc.embedding)
            ids.append(doc.id)
        
        # Normalize for cosine similarity
        if self.config.distance_metric == "cosine":
            embeddings_array = np.array(embeddings, dtype=np.float32)
            norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
            embeddings_array = embeddings_array / (norms + 1e-10)
            self._index.add(embeddings_array)
        else:
            self._index.add(np.array(embeddings, dtype=np.float32))
        
        return ids
    
    async def _add_in_memory(self, documents: List[VectorDocument]) -> List[str]:
        """Add documents to in-memory store."""
        ids = []
        for doc in documents:
            self._vectors[doc.id] = doc
            ids.append(doc.id)
        return ids
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search for similar vectors."""
        if not self._initialized:
            await self.initialize()
        
        if self.config.backend == VectorStoreBackend.CHROMADB:
            return await self._search_chromadb(query)
        elif self.config.backend == VectorStoreBackend.FAISS:
            return await self._search_faiss(query)
        elif self.config.backend == VectorStoreBackend.IN_MEMORY:
            return await self._search_in_memory(query)
        else:
            raise NotImplementedError(f"Backend {self.config.backend} not implemented")
    
    async def _search_chromadb(self, query: SearchQuery) -> List[SearchResult]:
        """Search ChromaDB."""
        results = self._collection.query(
            query_embeddings=[query.query_embedding.tolist()],
            n_results=query.top_k,
            where=query.filter_metadata,
            include=["documents", "metadatas", "distances", "embeddings"] if query.include_embeddings else ["documents", "metadatas", "distances"]
        )
        
        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i]
                # Convert distance to similarity score
                if self.config.distance_metric == "cosine":
                    score = 1 - distance
                else:
                    score = 1 / (1 + distance)
                
                if score >= query.min_score:
                    search_results.append(SearchResult(
                        id=doc_id,
                        score=score,
                        content=results["documents"][0][i],
                        metadata=results["metadatas"][0][i],
                        embedding=np.array(results["embeddings"][0][i]) if query.include_embeddings and results.get("embeddings") else None
                    ))
        
        return search_results
    
    async def _search_faiss(self, query: SearchQuery) -> List[SearchResult]:
        """Search FAISS index."""
        # Normalize query for cosine
        query_vec = query.query_embedding.astype(np.float32).reshape(1, -1)
        if self.config.distance_metric == "cosine":
            norm = np.linalg.norm(query_vec)
            if norm > 0:
                query_vec = query_vec / norm
        
        # Search
        distances, indices = self._index.search(query_vec, query.top_k * 2)  # Get more for filtering
        
        search_results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1 or idx not in self._metadata_store:
                continue
            
            # Convert distance to score
            if self.config.distance_metric == "cosine":
                score = float(dist)  # Already normalized, higher is better
            else:
                score = 1 / (1 + float(dist))
            
            if score < query.min_score:
                continue
            
            metadata = self._metadata_store.get(idx, {})
            
            # Apply metadata filter
            if query.filter_metadata:
                match = all(
                    metadata.get(k) == v for k, v in query.filter_metadata.items()
                )
                if not match:
                    continue
            
            search_results.append(SearchResult(
                id=list(self._id_to_index.keys())[list(self._id_to_index.values()).index(idx)] if idx in self._id_to_index.values() else str(idx),
                score=score,
                content=self._content_store.get(idx, ""),
                metadata=metadata,
                embedding=None  # FAISS doesn't store embeddings by default
            ))
            
            if len(search_results) >= query.top_k:
                break
        
        return search_results
    
    async def _search_in_memory(self, query: SearchQuery) -> List[SearchResult]:
        """Search in-memory store."""
        query_vec = query.query_embedding
        query_norm = np.linalg.norm(query_vec)
        if query_norm > 0:
            query_vec = query_vec / query_norm
        
        results = []
        for doc_id, doc in self._vectors.items():
            # Apply filter
            if query.filter_metadata:
                match = all(
                    doc.metadata.get(k) == v for k, v in query.filter_metadata.items()
                )
                if not match:
                    continue
            
            # Compute similarity
            doc_vec = doc.embedding
            doc_norm = np.linalg.norm(doc_vec)
            if doc_norm > 0:
                doc_vec = doc_vec / doc_norm
            
            score = float(np.dot(query_vec, doc_vec))
            
            if score >= query.min_score:
                results.append(SearchResult(
                    id=doc_id,
                    score=score,
                    content=doc.content,
                    metadata=doc.metadata,
                    embedding=doc.embedding if query.include_embeddings else None
                ))
        
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:query.top_k]
    
    async def get_document(self, doc_id: str) -> Optional[VectorDocument]:
        """Get a document by ID."""
        if not self._initialized:
            await self.initialize()
        
        if self.config.backend == VectorStoreBackend.CHROMADB:
            results = self._collection.get(ids=[doc_id], include=["documents", "metadatas", "embeddings"])
            if results["ids"]:
                return VectorDocument(
                    id=results["ids"][0],
                    embedding=np.array(results["embeddings"][0]),
                    metadata=results["metadatas"][0],
                    content=results["documents"][0]
                )
        elif self.config.backend == VectorStoreBackend.IN_MEMORY:
            return self._vectors.get(doc_id)
        elif self.config.backend == VectorStoreBackend.FAISS:
            if doc_id in self._id_to_index:
                idx = self._id_to_index[doc_id]
                return VectorDocument(
                    id=doc_id,
                    embedding=np.zeros(self.config.embedding_dimension),  # Not stored
                    metadata=self._metadata_store.get(idx, {}),
                    content=self._content_store.get(idx, "")
                )
        
        return None
    
    async def delete_documents(self, doc_ids: List[str]) -> bool:
        """Delete documents by IDs."""
        if not self._initialized:
            await self.initialize()
        
        try:
            if self.config.backend == VectorStoreBackend.CHROMADB:
                self._collection.delete(ids=doc_ids)
            elif self.config.backend == VectorStoreBackend.IN_MEMORY:
                for doc_id in doc_ids:
                    self._vectors.pop(doc_id, None)
            elif self.config.backend == VectorStoreBackend.FAISS:
                # FAISS doesn't support deletion easily, mark as deleted
                for doc_id in doc_ids:
                    if doc_id in self._id_to_index:
                        idx = self._id_to_index.pop(doc_id)
                        self._metadata_store.pop(idx, None)
                        self._content_store.pop(idx, None)
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return False
    
    async def update_document(self, doc_id: str, embedding: Optional[np.ndarray] = None,
                            metadata: Optional[Dict[str, Any]] = None,
                            content: Optional[str] = None) -> bool:
        """Update a document."""
        # For simplicity, delete and re-add
        await self.delete_documents([doc_id])
        
        existing = await self.get_document(doc_id)
        if not existing:
            return False
        
        new_doc = VectorDocument(
            id=doc_id,
            embedding=embedding if embedding is not None else existing.embedding,
            metadata=metadata if metadata is not None else existing.metadata,
            content=content if content is not None else existing.content,
            updated_at=datetime.utcnow()
        )
        
        await self.add_documents([new_doc])
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        if self.config.backend == VectorStoreBackend.CHROMADB and self._collection:
            count = self._collection.count()
        elif self.config.backend == VectorStoreBackend.IN_MEMORY:
            count = len(self._vectors)
        elif self.config.backend == VectorStoreBackend.FAISS:
            count = self._index.ntotal if hasattr(self, '_index') else 0
        else:
            count = 0
        
        return {
            "backend": self.config.backend.value,
            "collection": self.config.collection_name,
            "document_count": count,
            "embedding_dimension": self.config.embedding_dimension,
            "distance_metric": self.config.distance_metric,
            "initialized": self._initialized
        }


# Global vector store instance
_vector_store: Optional[VectorStore] = None


def get_vector_store(config: Optional[VectorStoreConfig] = None) -> VectorStore:
    """Get or create the global vector store."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(config)
    return _vector_store


async def close_vector_store() -> None:
    """Close the global vector store."""
    global _vector_store
    if _vector_store:
        _vector_store = None