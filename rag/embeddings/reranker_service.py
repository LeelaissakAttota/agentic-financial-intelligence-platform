"""
Reranker Service for Financial Document Retrieval.

Uses cross-encoder models (BGE-Reranker) for improved retrieval quality.
"""

import logging
import time
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


class RerankerService:
    """Cross-encoder reranker for improving retrieval results."""
    
    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: str = "cuda",
        batch_size: int = 16,
        max_length: int = 512,
    ):
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.max_length = max_length
        
        self._model = None
        self._tokenizer = None
        
        # Stats
        self._stats = {
            "total_reranks": 0,
            "total_pairs": 0,
            "total_time_ms": 0,
        }
    
    def _load_model(self):
        """Lazy load the cross-encoder model."""
        if self._model is not None:
            return
        
        try:
            from sentence_transformers import CrossEncoder
            
            logger.info(f"Loading reranker model: {self.model_name} on {self.device}")
            start = time.time()
            
            self._model = CrossEncoder(
                self.model_name,
                device=self.device,
                max_length=self.max_length,
                trust_remote_code=True,
            )
            
            load_time = (time.time() - start) * 1000
            logger.info(f"Reranker model loaded in {load_time:.0f}ms")
            
        except ImportError:
            raise RuntimeError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load reranker model: {e}")
    
    def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: Optional[int] = None,
    ) -> list[tuple[int, float]]:
        """
        Rerank documents by relevance to query.
        
        Args:
            query: Query string
            documents: List of document texts
            top_k: Return only top k results (None for all)
            
        Returns:
            List of (original_index, score) tuples sorted by score descending
        """
        self._load_model()
        
        if not documents:
            return []
        
        start = time.time()
        
        # Prepare pairs for cross-encoder
        pairs = [(query, doc) for doc in documents]
        
        # Get scores
        scores = self._model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        
        # Create ranked results
        results = list(enumerate(scores))
        results.sort(key=lambda x: x[1], reverse=True)
        
        if top_k:
            results = results[:top_k]
        
        elapsed = (time.time() - start) * 1000
        self._stats["total_reranks"] += 1
        self._stats["total_pairs"] += len(documents)
        self._stats["total_time_ms"] += elapsed
        
        logger.debug(f"Reranked {len(documents)} docs in {elapsed:.1f}ms")
        
        return results
    
    def rerank_with_scores(
        self,
        query: str,
        documents: list[dict],  # Each dict has 'text' key
        top_k: Optional[int] = None,
        score_threshold: float = 0.0,
    ) -> list[dict]:
        """
        Rerank documents with scores and metadata.
        
        Args:
            query: Query string
            documents: List of dicts with 'text' key
            top_k: Return top k results
            score_threshold: Minimum score to include
            
        Returns:
            Reranked documents with added 'rerank_score' key
        """
        if not documents:
            return []
        
        texts = [doc.get("text", "") for doc in documents]
        results = self.rerank(query, texts, top_k=top_k)
        
        reranked = []
        for orig_idx, score in results:
            if score >= score_threshold:
                doc = documents[orig_idx].copy()
                doc["rerank_score"] = float(score)
                reranked.append(doc)
        
        return reranked
    
    def get_stats(self) -> dict:
        """Get service statistics."""
        stats = self._stats.copy()
        if stats["total_reranks"] > 0:
            stats["avg_time_ms"] = stats["total_time_ms"] / stats["total_reranks"]
        else:
            stats["avg_time_ms"] = 0
        return stats
    
    def reset_stats(self):
        """Reset statistics."""
        self._stats = {
            "total_reranks": 0,
            "total_pairs": 0,
            "total_time_ms": 0,
        }


def create_reranker_service(config: Optional[dict] = None) -> RerankerService:
    """Factory function to create RerankerService from config."""
    if config is None:
        config = {}
    
    reranker_config = config.get("reranker", {})
    
    return RerankerService(
        model_name=reranker_config.get("model", "BAAI/bge-reranker-v2-m3"),
        device=reranker_config.get("device", "cuda"),
        batch_size=reranker_config.get("batch_size", 16),
        max_length=reranker_config.get("max_length", 512),
    )