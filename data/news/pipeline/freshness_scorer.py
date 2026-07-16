"""
Freshness Scorer for News Articles

Scores articles based on recency with configurable decay curves.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from data.news.schemas import NewsArticle

logger = logging.getLogger(__name__)


@dataclass
class FreshnessConfig:
    """Configuration for freshness scoring."""
    # Time windows (in hours)
    breaking_window: int = 1       # 0-1h = breaking
    very_fresh_window: int = 6     # 1-6h = very fresh
    fresh_window: int = 24         # 6-24h = fresh
    recent_window: int = 72        # 24-72h = recent
    stale_window: int = 168        # 72-168h = stale (1 week)
    # Beyond stale_window = very stale
    
    # Scores for each window
    breaking_score: float = 1.0
    very_fresh_score: float = 0.9
    fresh_score: float = 0.7
    recent_score: float = 0.5
    stale_score: float = 0.3
    very_stale_score: float = 0.1
    
    # Decay function: "step" or "exponential" or "linear"
    decay_mode: str = "step"
    
    # For exponential decay: half-life in hours
    half_life_hours: float = 12.0
    
    # For linear decay: score at max_age
    max_age_hours: int = 720  # 30 days
    min_score: float = 0.05


class FreshnessScorer:
    """
    Scores article freshness based on publication time.
    
    Supports multiple decay modes:
    - Step function (discrete windows)
    - Exponential decay (continuous)
    - Linear decay (continuous)
    """
    
    def __init__(self, config: Optional[FreshnessConfig] = None):
        self.config = config or FreshnessConfig()
    
    def score(self, article: NewsArticle) -> float:
        """
        Calculate freshness score for article (0.0 - 1.0).
        
        Higher score = more recent.
        """
        if not article.published_at:
            logger.debug("Article missing published_at, returning minimum freshness")
            return self.config.min_score
        
        age_hours = self._calculate_age_hours(article.published_at)
        
        if self.config.decay_mode == "step":
            return self._step_score(age_hours)
        elif self.config.decay_mode == "exponential":
            return self._exponential_score(age_hours)
        elif self.config.decay_mode == "linear":
            return self._linear_score(age_hours)
        else:
            logger.warning(f"Unknown decay mode: {self.config.decay_mode}, using step")
            return self._step_score(age_hours)
    
    def _calculate_age_hours(self, published_at: datetime) -> float:
        """Calculate age of article in hours."""
        now = datetime.utcnow()
        if published_at.tzinfo is not None:
            # Convert to UTC if timezone-aware
            published_at = published_at.replace(tzinfo=None)
        delta = now - published_at
        return max(0, delta.total_seconds() / 3600)
    
    def _step_score(self, age_hours: float) -> float:
        """Step function scoring based on time windows."""
        if age_hours <= self.config.breaking_window:
            return self.config.breaking_score
        elif age_hours <= self.config.very_fresh_window:
            return self.config.very_fresh_score
        elif age_hours <= self.config.fresh_window:
            return self.config.fresh_score
        elif age_hours <= self.config.recent_window:
            return self.config.recent_score
        elif age_hours <= self.config.stale_window:
            return self.config.stale_score
        else:
            return self.config.very_stale_score
    
    def _exponential_score(self, age_hours: float) -> float:
        """Exponential decay scoring."""
        # Score = initial_score * 0.5^(age/half_life)
        # Normalized so fresh (0h) = 1.0
        if age_hours <= 0:
            return 1.0
        
        score = 2 ** (-age_hours / self.config.half_life_hours)
        return max(score, self.config.min_score)
    
    def _linear_score(self, age_hours: float) -> float:
        """Linear decay scoring."""
        if age_hours <= 0:
            return 1.0
        elif age_hours >= self.config.max_age_hours:
            return self.config.min_score
        else:
            # Linear interpolation from 1.0 to min_score
            progress = age_hours / self.config.max_age_hours
            return 1.0 - (progress * (1.0 - self.config.min_score))
    
    def get_category(self, article: NewsArticle) -> str:
        """Get freshness category label."""
        if not article.published_at:
            return "unknown"
        
        age_hours = self._calculate_age_hours(article.published_at)
        
        if age_hours <= self.config.breaking_window:
            return "breaking"
        elif age_hours <= self.config.very_fresh_window:
            return "very_fresh"
        elif age_hours <= self.config.fresh_window:
            return "fresh"
        elif age_hours <= self.config.recent_window:
            return "recent"
        elif age_hours <= self.config.stale_window:
            return "stale"
        else:
            return "very_stale"
    
    def score_with_details(self, article: NewsArticle) -> Dict[str, Any]:
        """Get score with detailed breakdown."""
        if not article.published_at:
            return {
                "score": self.config.min_score,
                "age_hours": None,
                "category": "unknown",
                "published_at": None
            }
        
        age_hours = self._calculate_age_hours(article.published_at)
        score = self.score(article)
        category = self.get_category(article)
        
        return {
            "score": round(score, 3),
            "age_hours": round(age_hours, 1),
            "category": category,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "decay_mode": self.config.decay_mode
        }


def score_freshness(article: NewsArticle, config: Optional[FreshnessConfig] = None) -> float:
    """Convenience function to score article freshness."""
    scorer = FreshnessScorer(config)
    return scorer.score(article)