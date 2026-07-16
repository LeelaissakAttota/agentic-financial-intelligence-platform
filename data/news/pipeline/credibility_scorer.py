"""
Credibility Scorer for News Articles

Evaluates source credibility and article trustworthiness.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional, Any

from data.news.schemas import NewsArticle, NewsSource

logger = logging.getLogger(__name__)


@dataclass
class CredibilityConfig:
    """Configuration for credibility scoring."""
    pass


@dataclass
class CredibilityScore:
    """Detailed credibility score breakdown."""
    overall: float  # 0.0 - 1.0
    source_tier: float
    source_reliability: float
    author_credibility: float
    publication_history: float
    transparency: float
    details: Dict[str, Any]


class CredibilityScorer:
    """
    Scores article and source credibility.
    
    Dimensions:
    - Source Tier (40%): Tier 1 (Reuters, Bloomberg, FT, WSJ) = 1.0
      Tier 2 (CNBC, MarketWatch, etc.) = 0.8
      Tier 3 (Financial APIs) = 0.7
      Tier 4 (RSS, unknown) = 0.5
    - Source Reliability (20%): Historical accuracy, corrections policy
    - Author Credibility (15%): Byline presence, expertise indicators
    - Publication History (15%): Age of outlet, reputation
    - Transparency (10%): Corrections, sponsorship disclosure, methodology
    """
    
    # Source tier definitions
    TIER_1_SOURCES = {
        NewsSource.REUTERS,
        NewsSource.BLOOMBERG,
        NewsSource.FINANCIAL_TIMES,
        NewsSource.WALL_STREET_JOURNAL,
        NewsSource.BARRONS,
    }
    
    TIER_2_SOURCES = {
        NewsSource.CNBC,
        NewsSource.MARKETWATCH,
        NewsSource.REUTERS,  # Also tier 1 but here for completeness
    }
    
    TIER_3_SOURCES = {
        NewsSource.YAHOO_FINANCE,
        NewsSource.FINNHUB,
        NewsSource.ALPHA_VANTAGE,
        NewsSource.NEWSAPI,
    }
    
    TIER_4_SOURCES = {
        NewsSource.GOOGLE_NEWS,
        NewsSource.MARKETWATCH,
        NewsSource.CNBC,
        NewsSource.SEEKING_ALPHA,
        NewsSource.MOTLEY_FOOL,
        NewsSource.ZACKS,
        NewsSource.TIPRANKS,
        NewsSource.BENZINGA,
    }
    
    # Source reliability scores (based on historical fact-checking)
    SOURCE_RELIABILITY = {
        NewsSource.REUTERS: 0.98,
        NewsSource.BLOOMBERG: 0.97,
        NewsSource.FINANCIAL_TIMES: 0.96,
        NewsSource.WALL_STREET_JOURNAL: 0.95,
        NewsSource.BARRONS: 0.93,
        NewsSource.CNBC: 0.88,
        NewsSource.MARKETWATCH: 0.85,
        NewsSource.YAHOO_FINANCE: 0.82,
        NewsSource.FINNHUB: 0.80,
        NewsSource.ALPHA_VANTAGE: 0.80,
        NewsSource.NEWSAPI: 0.78,
        NewsSource.GOOGLE_NEWS: 0.70,
        NewsSource.SEEKING_ALPHA: 0.65,
        NewsSource.MOTLEY_FOOL: 0.60,
        NewsSource.ZACKS: 0.70,
        NewsSource.TIPRANKS: 0.65,
        NewsSource.BENZINGA: 0.60,
    }
    
    # Publication age (years) - older = more established
    PUBLICATION_AGE = {
        NewsSource.REUTERS: 170,  # Founded 1851
        NewsSource.WALL_STREET_JOURNAL: 130,  # 1889
        NewsSource.FINANCIAL_TIMES: 135,  # 1888
        NewsSource.BLOOMBERG: 40,  # 1981
        NewsSource.BARRONS: 100,  # 1921
        NewsSource.CNBC: 35,  # 1989
        NewsSource.MARKETWATCH: 25,  # 1997
        NewsSource.YAHOO_FINANCE: 25,  # 1997
        NewsSource.REUTERS: 170,
    }
    
    def __init__(self, config: Optional[CredibilityConfig] = None):
        self.config = config or CredibilityConfig()
    
    def score(self, article: NewsArticle) -> CredibilityScore:
        """
        Calculate comprehensive credibility score for article.
        
        Returns CredibilityScore with overall and component scores.
        """
        source_tier = self._score_source_tier(article.source)
        source_reliability = self._score_source_reliability(article.source)
        author_cred = self._score_author_credibility(article)
        pub_history = self._score_publication_history(article.source)
        transparency = self._score_transparency(article)
        
        # Weighted overall score
        overall = (
            source_tier * 0.40 +
            source_reliability * 0.20 +
            author_cred * 0.15 +
            pub_history * 0.15 +
            transparency * 0.10
        )
        
        return CredibilityScore(
            overall=round(overall, 3),
            source_tier=round(source_tier, 3),
            source_reliability=round(source_reliability, 3),
            author_credibility=round(author_cred, 3),
            publication_history=round(pub_history, 3),
            transparency=round(transparency, 3),
            details={
                "source": article.source.value,
                "source_name": article.source_name,
                "has_author": bool(article.author),
                "author_name": article.author,
                "source_tier_label": self._get_tier_label(article.source),
            }
        )
    
    def _score_source_tier(self, source: NewsSource) -> float:
        """Score based on source tier."""
        if source in self.TIER_1_SOURCES:
            return 1.0
        elif source in self.TIER_2_SOURCES:
            return 0.8
        elif source in self.TIER_3_SOURCES:
            return 0.7
        elif source in self.TIER_4_SOURCES:
            return 0.5
        else:
            return 0.4  # Unknown sources
    
    def _score_source_reliability(self, source: NewsSource) -> float:
        """Score based on historical reliability."""
        return self.SOURCE_RELIABILITY.get(source, 0.5)
    
    def _score_author_credibility(self, article: NewsArticle) -> float:
        """Score author credibility."""
        if not article.author:
            return 0.3  # No byline
        
        # Basic checks
        score = 0.5  # Base for having an author
        
        # Check for financial journalism indicators
        author_lower = article.author.lower()
        
        # Staff reporter indicators
        if any(word in author_lower for word in ['staff', 'reporter', 'correspondent', 'journalist']):
            score += 0.2
        
        # Financial expertise indicators
        if any(word in author_lower for word in ['finance', 'markets', 'investing', 'equity', 'analyst']):
            score += 0.2
        
        # Senior/lead indicators
        if any(word in author_lower for word in ['senior', 'lead', 'chief', 'editor']):
            score += 0.1
        
        return min(score, 1.0)
    
    def _score_publication_history(self, source: NewsSource) -> float:
        """Score based on publication age/reputation."""
        age = self.PUBLICATION_AGE.get(source, 0)
        
        if age >= 100:
            return 1.0
        elif age >= 50:
            return 0.9
        elif age >= 25:
            return 0.8
        elif age >= 10:
            return 0.7
        elif age >= 5:
            return 0.6
        else:
            return 0.5
    
    def _score_transparency(self, article: NewsArticle) -> float:
        """Score transparency indicators."""
        score = 0.5  # Base
        
        # Has corrections/updates policy (inferred from source)
        if article.source in self.TIER_1_SOURCES:
            score += 0.3
        elif article.source in self.TIER_2_SOURCES:
            score += 0.2
        
        # Sponsored content disclosure (check metadata)
        if article.metadata:
            if article.metadata.get('sponsored') is False:
                score += 0.1
            if article.metadata.get('corrections_policy'):
                score += 0.1
        
        # Methodology disclosure for analysis pieces
        content = article.content or ""
        if any(word in content.lower() for word in ['methodology', 'how we calculated', 'data source:', 'source:']):
            score += 0.1
        
        return min(score, 1.0)
    
    def _get_tier_label(self, source: NewsSource) -> str:
        """Get human-readable tier label."""
        if source in self.TIER_1_SOURCES:
            return "tier_1_premium"
        elif source in self.TIER_2_SOURCES:
            return "tier_2_established"
        elif source in self.TIER_3_SOURCES:
            return "tier_3_data_provider"
        elif source in self.TIER_4_SOURCES:
            return "tier_4_aggregator"
        else:
            return "tier_5_unknown"


def score_credibility(article: NewsArticle, config: Optional[CredibilityConfig] = None) -> CredibilityScore:
    """Convenience function to score article credibility."""
    scorer = CredibilityScorer(config)
    return scorer.score(article)