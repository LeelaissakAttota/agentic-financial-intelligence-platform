"""
Embedding Service for Financial Documents.

Generates embeddings using ChromaDB's default embedding function
(which uses ONNX-based all-MiniLM-L6-v2 model) - no external dependencies.
"""

import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np

# Import ChromaDB embedding functions and create custom one with container-friendly path
import chromadb.utils.embedding_functions as embedding_functions
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

logger = logging.getLogger(__name__)

# Custom embedding function that uses container-writable path for ONNX model cache
class ContainerONNXEmbeddingFunction(ONNXMiniLM_L6_V2):
    """Custom ONNX embedding function with container-friendly download path."""
    DOWNLOAD_PATH = "/app/data/processed/onnx_models/all-MiniLM-L6-v2"


class EmbeddingCache:
    """Disk-based cache for embeddings using SHA256 content hashes."""

    def __init__(self, cache_dir: str | Path = "./data/processed/embedding_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, np.ndarray] = {}
        self._stats = {"hits": 0, "misses": 0}

    def _make_key(self, text: str, model_name: str) -> str:
        """Generate cache key from text and model."""
        content = f"{model_name}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_path(self, key: str) -> Path:
        """Get cache file path for key."""
        # Use first 2 chars as subdirectory for better filesystem performance
        subdir = self.cache_dir / key[:2]
        subdir.mkdir(exist_ok=True)
        return subdir / f"{key}.npy"

    def get(self, text: str, model_name: str) -> Optional[np.ndarray]:
        """Retrieve cached embedding."""
        key = self._make_key(text, model_name)

        # Check memory cache first
        if key in self._memory_cache:
            self._stats["hits"] += 1
            return self._memory_cache[key]

        # Check disk cache
        path = self._get_path(key)
        if path.exists():
            try:
                embedding = np.load(path)
                self._memory_cache[key] = embedding
                self._stats["hits"] += 1
                return embedding
            except Exception as e:
                logger.warning(f"Failed to load cached embedding: {e}")

        self._stats["misses"] += 1
        return None

    def set(self, text: str, model_name: str, embedding: np.ndarray):
        """Store embedding in cache."""
        key = self._make_key(text, model_name)

        # Store in memory
        self._memory_cache[key] = embedding

        # Store on disk
        path = self._get_path(key)
        try:
            np.save(path, embedding)
        except Exception as e:
            logger.warning(f"Failed to save embedding to cache: {e}")

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": hit_rate,
            "memory_entries": len(self._memory_cache),
        }

    def clear(self):
        """Clear all caches."""
        self._memory_cache.clear()
        self._stats = {"hits": 0, "misses": 0}
        # Note: we don't delete disk cache to preserve it across runs


class EmbeddingService:
    """Generates embeddings using ChromaDB's default embedding function."""

    def __init__(
        self,
        model_name: str = "chromadb_default",
        device: str = "cpu",
        batch_size: int = 32,
        instruction: str = "Represent this financial document for retrieval:",
        cache_enabled: bool = True,
        cache_dir: Optional[str] = None,
    ):
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.instruction = instruction

        self._embedding_fn = None
        self._dimension = 384  # all-MiniLM-L6-v2 dimension

        # Cache
        self.cache = EmbeddingCache(cache_dir) if cache_enabled else None

        # Stats
        self._stats = {
            "total_embeddings": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_time_ms": 0,
        }

    def _load_embedding_fn(self):
        """Lazy load ChromaDB's default embedding function."""
        if self._embedding_fn is not None:
            return

        try:
            logger.info("Loading ChromaDB default embedding function (all-MiniLM-L6-v2)")
            start = time.time()

            # Use our custom embedding function with container-friendly ONNX model cache path
            self._embedding_fn = ContainerONNXEmbeddingFunction()

            load_time = (time.time() - start) * 1000
            logger.info(f"Embedding function loaded in {load_time:.0f}ms")

        except Exception as e:
            raise RuntimeError(f"Failed to load ChromaDB embedding function: {e}")

    def _prepare_texts(self, texts: list[str]) -> list[str]:
        """Add instruction prefix to texts."""
        if self.instruction and "bge" in self.model_name.lower():
            return [f"{self.instruction} {text}" for text in texts]
        return texts

    def embed(self, texts: str | list[str]) -> np.ndarray:
        """
        Generate embeddings for text(s).

        Args:
            texts: Single text or list of texts

        Returns:
            Embeddings array of shape (n_texts, embedding_dim)
        """
        self._load_embedding_fn()

        # Normalize input
        if isinstance(texts, str):
            texts = [texts]
            single = True
        else:
            single = False

        if not texts:
            return np.array([]).reshape(0, self.get_dimension())

        # Check cache for each text
        uncached_texts = []
        uncached_indices = []
        results = [None] * len(texts)

        if self.cache:
            for i, text in enumerate(texts):
                cached = self.cache.get(text, self.model_name)
                if cached is not None:
                    results[i] = cached
                    self._stats["cache_hits"] += 1
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
                    self._stats["cache_misses"] += 1
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))
            self._stats["cache_misses"] += len(texts)

        # Generate embeddings for uncached texts
        if uncached_texts:
            start = time.time()

            # Prepare with instruction
            prepared = self._prepare_texts(uncached_texts)

            # Generate embeddings using ChromaDB's default function
            embeddings = self._embedding_fn(prepared)

            elapsed = (time.time() - start) * 1000
            self._stats["total_time_ms"] += elapsed

            # Store in cache and results
            for idx, embedding in zip(uncached_indices, embeddings):
                text = texts[idx]
                results[idx] = np.array(embedding, dtype=np.float32)
                if self.cache:
                    self.cache.set(text, self.model_name, np.array(embedding, dtype=np.float32))

            self._stats["total_embeddings"] += len(uncached_texts)

        result_array = np.array(results)

        return result_array[0] if single else result_array

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for documents (alias for embed)."""
        return self.embed(texts)

    def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for a query."""
        # For BGE-M3, queries should also use instruction
        return self.embed(query)

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension

    def get_stats(self) -> dict:
        """Get service statistics."""
        stats = self._stats.copy()
        if stats["total_embeddings"] > 0:
            stats["avg_time_ms"] = stats["total_time_ms"] / stats["total_embeddings"]
        else:
            stats["avg_time_ms"] = 0

        if self.cache:
            stats["cache"] = self.cache.get_stats()

        return stats

    def reset_stats(self):
        """Reset statistics."""
        self._stats = {
            "total_embeddings": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_time_ms": 0,
        }

    def warmup(self, sample_texts: list[str] = None):
        """Warm up the model with sample texts."""
        if sample_texts is None:
            sample_texts = [
                "This is a sample financial document for warming up the embedding model.",
                "Revenue increased by 15% year over year.",
                "Risk factors include market volatility and regulatory changes.",
            ]

        logger.info("Warming up embedding model...")
        self.embed(sample_texts)
        logger.info("Warmup complete")


def create_embedding_service(config: Optional[dict] = None) -> EmbeddingService:
    """Factory function to create EmbeddingService from config."""
    if config is None:
        config = {}

    embedding_config = config.get("embedding", {})

    # Provide default cache_dir if not specified
    cache_dir = embedding_config.get("cache_dir")
    if cache_dir is None:
        cache_dir = "/app/data/processed/embedding_cache"

    return EmbeddingService(
        model_name=embedding_config.get("model", "chromadb_default"),
        device=embedding_config.get("device", "cpu"),
        batch_size=embedding_config.get("batch_size", 32),
        instruction=embedding_config.get(
            "instruction",
            "Represent this financial document for retrieval:"
        ),
        cache_enabled=embedding_config.get("cache_enabled", True),
        cache_dir=cache_dir,
    )