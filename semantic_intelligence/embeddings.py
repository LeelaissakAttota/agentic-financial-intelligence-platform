"""
Embedding Service - Generates and manages embeddings for semantic search.
"""

import asyncio
import logging
import hashlib
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingModel(str, Enum):
    """Supported embedding models."""
    BGE_M3 = "bge-m3"
    BGE_LARGE = "bge-large-en-v1.5"
    BGE_BASE = "bge-base-en-v1.5"
    E5_LARGE = "e5-large-v2"
    E5_BASE = "e5-base-v2"
    MINILM_L6 = "all-MiniLM-L6-v2"
    MINILM_L12 = "all-MiniLM-L12-v2"
    MPNET = "all-mpnet-base-v2"
    OPENAI_ADA = "text-embedding-ada-002"
    OPENAI_3_SMALL = "text-embedding-3-small"
    OPENAI_3_LARGE = "text-embedding-3-large"


@dataclass
class EmbeddingConfig:
    """Configuration for embedding service."""
    model: EmbeddingModel = EmbeddingModel.BGE_M3
    batch_size: int = 32
    max_length: int = 512
    normalize: bool = True
    device: str = "auto"  # auto, cpu, cuda
    cache_enabled: bool = True
    cache_ttl_hours: int = 24
    api_key: Optional[str] = None
    api_base: Optional[str] = None


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    embeddings: np.ndarray  # Shape: (n_texts, embedding_dim)
    model: EmbeddingModel
    dimensions: int
    processing_time_ms: float
    token_count: int
    cached: bool = False


class EmbeddingService:
    """
    Service for generating text embeddings using various models.
    Supports local models (sentence-transformers) and API-based models (OpenAI).
    """
    
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        self._model = None
        self._embedding_dim = None
        self._cache: Dict[str, np.ndarray] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize the embedding model."""
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            try:
                if self.config.model in [EmbeddingModel.OPENAI_ADA, EmbeddingModel.OPENAI_3_SMALL, EmbeddingModel.OPENAI_3_LARGE]:
                    await self._init_openai()
                else:
                    await self._init_sentence_transformers()
                
                self._initialized = True
                logger.info(f"Embedding service initialized with model: {self.config.model.value}")
                
            except Exception as e:
                logger.error(f"Failed to initialize embedding service: {e}")
                raise
    
    async def _init_openai(self) -> None:
        """Initialize OpenAI embedding client."""
        try:
            import openai
            self._openai_client = openai.AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base
            )
            
            # Determine dimensions based on model
            dim_map = {
                EmbeddingModel.OPENAI_ADA: 1536,
                EmbeddingModel.OPENAI_3_SMALL: 1536,
                EmbeddingModel.OPENAI_3_LARGE: 3072,
            }
            self._embedding_dim = dim_map.get(self.config.model, 1536)
            
        except ImportError:
            raise RuntimeError("openai package required for OpenAI embeddings. Install with: pip install openai")
    
    async def _init_sentence_transformers(self) -> None:
        """Initialize sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            import torch
            
            # Determine device
            if self.config.device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                device = self.config.device
            
            model_name = self.config.model.value
            self._model = SentenceTransformer(model_name, device=device)
            
            # Get embedding dimension
            self._embedding_dim = self._model.get_sentence_embedding_dimension()
            
            logger.info(f"Loaded sentence-transformers model: {model_name} on {device} (dim={self._embedding_dim})")
            
        except ImportError:
            raise RuntimeError("sentence-transformers package required. Install with: pip install sentence-transformers")
    
    async def embed_texts(
        self,
        texts: List[str],
        use_cache: bool = True,
        show_progress: bool = False
    ) -> EmbeddingResult:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed
            use_cache: Whether to use cache
            show_progress: Show progress bar for large batches
            
        Returns:
            EmbeddingResult with embeddings and metadata
        """
        if not self._initialized:
            await self.initialize()
        
        start_time = datetime.utcnow()
        total_tokens = 0
        
        # Check cache
        cached_embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        if use_cache and self.config.cache_enabled:
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                if cache_key in self._cache:
                    cached_embeddings.append((i, self._cache[cache_key]))
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))
        
        # Generate embeddings for uncached texts
        new_embeddings = np.zeros((len(texts), self._embedding_dim), dtype=np.float32)
        
        # Fill cached embeddings
        for idx, emb in cached_embeddings:
            new_embeddings[idx] = emb
        
        if uncached_texts:
            # Process in batches
            batch_embeddings = await self._embed_batch(uncached_texts, show_progress)
            
            for i, (orig_idx, emb) in enumerate(zip(uncached_indices, batch_embeddings)):
                new_embeddings[orig_idx] = emb
                
                # Cache if enabled
                if use_cache and self.config.cache_enabled:
                    cache_key = self._get_cache_key(texts[orig_idx])
                    self._cache[cache_key] = emb
                    self._cache_timestamps[cache_key] = datetime.utcnow()
            
            total_tokens = sum(len(t.split()) for t in uncached_texts)  # Approximate
        else:
            total_tokens = 0
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return EmbeddingResult(
            embeddings=new_embeddings,
            model=self.config.model,
            dimensions=self._embedding_dim,
            processing_time_ms=processing_time,
            token_count=total_tokens,
            cached=len(cached_embeddings) > 0
        )
    
    async def _embed_batch(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> np.ndarray:
        """Embed a batch of texts."""
        if self.config.model in [EmbeddingModel.OPENAI_ADA, EmbeddingModel.OPENAI_3_SMALL, EmbeddingModel.OPENAI_3_LARGE]:
            return await self._embed_openai(texts)
        else:
            return await self._embed_sentence_transformers(texts, show_progress)
    
    async def _embed_openai(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using OpenAI API."""
        # Process in batches for API limits
        batch_size = min(self.config.batch_size, 100)
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            response = await self._openai_client.embeddings.create(
                model=self.config.model.value,
                input=batch,
                encoding_format="float"
            )
            
            batch_embeddings = np.array([e.embedding for e in response.data], dtype=np.float32)
            all_embeddings.append(batch_embeddings)
        
        return np.vstack(all_embeddings)
    
    async def _embed_sentence_transformers(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> np.ndarray:
        """Generate embeddings using sentence-transformers."""
        loop = asyncio.get_event_loop()
        
        def encode():
            return self._model.encode(
                texts,
                batch_size=self.config.batch_size,
                max_length=self.config.max_length,
                normalize_embeddings=self.config.normalize,
                show_progress_bar=show_progress,
                convert_to_numpy=True
            )
        
        embeddings = await loop.run_in_executor(None, encode)
        return embeddings.astype(np.float32)
    
    async def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query text."""
        result = await self.embed_texts([query])
        return result.embeddings[0]
    
    async def embed_document(
        self,
        text: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ) -> List[np.ndarray]:
        """Embed a long document by chunking."""
        # Simple chunking by characters (in production, use proper text splitter)
        chunks = []
        for i in range(0, len(text), chunk_size - chunk_overlap):
            chunk = text[i:i + chunk_size]
            if len(chunk.strip()) > 50:  # Skip tiny chunks
                chunks.append(chunk)
        
        if not chunks:
            return []
        
        result = await self.embed_texts(chunks)
        return list(result.embeddings)
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        content = f"{self.config.model.value}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    def clear_cache(self) -> None:
        """Clear embedding cache."""
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.info("Embedding cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "model": self.config.model.value,
            "dimensions": self._embedding_dim,
            "cache_enabled": self.config.cache_enabled
        }
    
    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return self._embedding_dim
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized


# Global embedding service instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service(config: Optional[EmbeddingConfig] = None) -> EmbeddingService:
    """Get or create the global embedding service."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(config)
    return _embedding_service


async def close_embedding_service() -> None:
    """Close the global embedding service."""
    global _embedding_service
    if _embedding_service:
        _embedding_service.clear_cache()
        _embedding_service = None