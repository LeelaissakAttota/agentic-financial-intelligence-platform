"""
News Aggregator - Multi-source collection, deduplication, ranking, and relevance scoring
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple, Any
from collections import defaultdict
import hashlib
import re

from data.news.schemas import (
    NewsArticle, NewsSource, NewsCategory, SentimentLabel, 
    ArticleSentiment, CompanyMention, PersonMention, EventDetection
)
from data.news.providers import get_news_provider, CompositeNewsProvider
from data.news.pipeline.duplicate_detector import DuplicateDetector, deduplicate_articles
from data.news.pipeline.quality_scorer import QualityScorer, QualityConfig
from data.news.pipeline.credibility_scorer import CredibilityScorer, CredibilityConfig
from data.news.pipeline.freshness_scorer import FreshnessScorer, FreshnessConfig
from data.news.entity_recognition import (
    get_entity_extractor, ExtractionPipelineConfig,
    EntityType, EntitySubType, Entity, EntityRelationship
)

logger = logging.getLogger(__name__)


@dataclass
class AggregatorConfig:
    """Configuration for news aggregator."""
    # Provider settings
    finnhub_key: Optional[str] = None
    alpha_vantage_key: Optional[str] = None
    newsapi_key: Optional[str] = None
    
    # Fetch settings
    lookback_hours: int = 24
    max_articles_per_provider: int = 50
    min_providers: int = 2
    
    # Deduplication settings
    title_similarity_threshold: float = 0.80
    content_fingerprint_threshold: float = 0.85
    enable_deduplication: bool = True
    
    # Quality settings
    enable_quality_scoring: bool = True
    min_quality_score: float = 0.3
    quality_config: Optional[QualityConfig] = None
    
    # Credibility settings
    enable_credibility_scoring: bool = True
    credibility_config: Optional[CredibilityConfig] = None
    
    # Freshness settings
    enable_freshness_scoring: bool = True
    freshness_config: Optional[FreshnessConfig] = None
    
    # Entity extraction
    enable_entity_extraction: bool = True
    entity_config: Optional[ExtractionPipelineConfig] = None
    
    # Relevance scoring
    enable_relevance_scoring: bool = True
    min_relevance_score: float = 0.3
    
    # Ranking weights
    weight_importance: float = 0.25
    weight_market_impact: float = 0.20
    weight_freshness: float = 0.15
    weight_relevance: float = 0.20
    weight_quality: float = 0.10
    weight_credibility: float = 0.10
    
    # Performance
    max_concurrent_providers: int = 5
    provider_timeout: int = 30


@dataclass
class ArticleEnrichment:
    """Enriched article with all computed scores and extracted entities."""
    article: NewsArticle
    quality_score: float = 0.0
    credibility_score: float = 0.0
    freshness_score: float = 0.0
    relevance_score: float = 0.0
    importance_score: float = 0.0
    market_impact_score: float = 0.0
    composite_score: float = 0.0
    entities: List[Entity] = field(default_factory=list)
    relationships: List[EntityRelationship] = field(default_factory=list)
    deduplicated: bool = False
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None


class CompanyRelevanceScorer:
    """Scores article relevance to a target company."""
    
    def __init__(self, target_company: str, target_ticker: Optional[str] = None):
        self.target_company = target_company.lower()
        self.target_ticker = target_ticker.upper() if target_ticker else None
        
        # Build keyword variations
        self.keywords = [self.target_company]
        if self.target_ticker:
            self.keywords.extend([self.target_ticker, f"${self.target_ticker}"])
            
        # Common company name variations
        self._add_variations()
        
        # Compile regex for exact matching
        self._compile_patterns()
        
    def _add_variations(self):
        """Add common variations of company name."""
        company = self.target_company
        words = company.split()
        
        # Add without common suffixes
        suffixes = ['inc', 'incorporated', 'corp', 'corporation', 'company', 'co', 'ltd', 'limited', 'llc', 'plc']
        for suffix in suffixes:
            if company.endswith(f' {suffix}'):
                self.keywords.append(company[:-len(suffix)-1].strip())
                break
                
        # Add acronym if multi-word
        if len(words) > 1:
            acronym = ''.join(w[0] for w in words if w[0].isupper())
            if len(acronym) > 1:
                self.keywords.append(acronym)
                
    def _compile_patterns(self):
        """Compile regex patterns for matching."""
        self.patterns = []
        for kw in self.keywords:
            # Word boundary pattern
            pattern = r'\b' + re.escape(kw) + r'\b'
            self.patterns.append(re.compile(pattern, re.IGNORECASE))
            
    def score_relevance(self, article: NewsArticle) -> float:
        """Score article relevance to target company (0-1)."""
        if not self.keywords:
            return 0.0
            
        text = f"{article.title} {article.summary} {article.content or ''}".lower()
        
        # Count keyword occurrences
        total_matches = 0
        for kw in self.keywords:
            # Use regex for word boundaries
            matches = len(re.findall(r'\b' + re.escape(kw.lower()) + r'\b', text))
            total_matches += matches
            
        # Score based on frequency and position
        if total_matches == 0:
            return 0.0
            
        # Position bonus (title/early in text)
        position_bonus = 0.0
        title_text = article.title.lower()
        for kw in self.keywords:
            if re.search(r'\b' + re.escape(kw.lower()) + r'\b', title_text):
                position_bonus = 0.3
                break
                
        # Frequency score (capped)
        freq_score = min(total_matches / 10.0, 0.7)
        
        # Entity extraction bonus
        entity_bonus = 0.0
        if article.companies:
            for cm in article.companies:
                if cm.ticker and self.target_ticker and cm.ticker == self.target_ticker:
                    entity_bonus = 0.2
                    break
                if cm.name.lower() == self.target_company:
                    entity_bonus = 0.2
                    break
                    
        total = freq_score + position_bonus + entity_bonus
        return min(total, 1.0)


class ImportanceRanker:
    """Ranks articles by composite importance score."""
    
    def __init__(self, config: AggregatorConfig):
        self.config = config
        
    def calculate_composite_score(self, enrichment: ArticleEnrichment) -> float:
        """Calculate composite importance score."""
        weights = {
            'importance': self.config.weight_importance,
            'market_impact': self.config.weight_market_impact,
            'freshness': self.config.weight_freshness,
            'relevance': self.config.weight_relevance,
            'quality': self.config.weight_quality,
            'credibility': self.config.weight_credibility,
        }
        
        score = (
            enrichment.importance_score * weights['importance'] +
            enrichment.market_impact_score * weights['market_impact'] +
            enrichment.freshness_score * weights['freshness'] +
            enrichment.relevance_score * weights['relevance'] +
            enrichment.quality_score * weights['quality'] +
            enrichment.credibility_score * weights['credibility']
        )
        
        return min(score, 1.0)


class SourceCredibilityManager:
    """Manages source credibility scores."""
    
    # Tier 1: Primary financial sources (highest credibility)
    TIER_1_SOURCES = {
        NewsSource.REUTERS: 1.0,
        NewsSource.BLOOMBERG: 1.0,
        NewsSource.FINANCIAL_TIMES: 0.95,
        NewsSource.WALL_STREET_JOURNAL: 0.95,
        NewsSource.NEWSAPI: 0.9,  # Aggregates tier 1
    }
    
    # Tier 2: Major financial news
    TIER_2_SOURCES = {
        NewsSource.CNBC: 0.85,
        NewsSource.MARKETWATCH: 0.8,
        NewsSource.REUTERS: 0.85,
        NewsSource.BENZINGA: 0.75,
        NewsSource.SEEKING_ALPHA: 0.7,
        NewsSource.YAHOO_FINANCE: 0.7,
    }
    
    # Tier 3: Other sources
    TIER_3_SOURCES = {
        NewsSource.FINNHUB: 0.7,
        NewsSource.ALPHA_VANTAGE: 0.7,
        NewsSource.GOOGLE_NEWS: 0.6,
        NewsSource.UNKNOWN: 0.5,
    }
    
    @classmethod
    def get_source_credibility(cls, source: NewsSource) -> float:
        """Get base credibility score for a source."""
        if source in cls.TIER_1_SOURCES:
            return cls.TIER_1_SOURCES[source]
        elif source in cls.TIER_2_SOURCES:
            return cls.TIER_2_SOURCES[source]
        elif source in cls.TIER_3_SOURCES:
            return cls.TIER_3_SOURCES[source]
        return 0.5
    
    @classmethod
    def get_all_sources(cls) -> Dict[NewsSource, float]:
        """Get all source credibility scores."""
        all_scores = {}
        all_scores.update(cls.TIER_1_SOURCES)
        all_scores.update(cls.TIER_2_SOURCES)
        all_scores.update(cls.TIER_3_SOURCES)
        return all_scores


class NewsAggregator:
    """
    Main news aggregator that orchestrates multi-source collection,
    deduplication, scoring, and ranking.
    """
    
    def __init__(self, config: Optional[AggregatorConfig] = None):
        self.config = config or AggregatorConfig()
        self.provider: Optional[CompositeNewsProvider] = None
        
        # Initialize scorers
        self.duplicate_detector = DuplicateDetector({
            'title_similarity_threshold': self.config.title_similarity_threshold,
            'content_fingerprint_threshold': self.config.content_fingerprint_threshold,
        })
        self.quality_scorer = QualityScorer(self.config.quality_config)
        self.credibility_scorer = CredibilityScorer(self.config.credibility_config)
        self.freshness_scorer = FreshnessScorer(self.config.freshness_config)
        
        # Entity extractor (lazy)
        self._entity_extractor = None
        
        # Relevance scorer (set per request)
        self._relevance_scorer: Optional[CompanyRelevanceScorer] = None
        self._importance_ranker: Optional[ImportanceRanker] = None
        
    async def _get_provider(self) -> CompositeNewsProvider:
        """Get or create provider instance."""
        if self.provider is None:
            self.provider = get_news_provider(
                finnhub_key=self.config.finnhub_key,
                alpha_vantage_key=self.config.alpha_vantage_key,
                newsapi_key=self.config.newsapi_key
            )
        return self.provider
        
    async def _get_entity_extractor(self):
        """Get or create entity extractor."""
        if self._entity_extractor is None and self.config.enable_entity_extraction:
            self._entity_extractor = await get_entity_extractor(
                self.config.entity_config or ExtractionPipelineConfig(
                    enable_local_ner=False,  # Keep fast by default
                    enable_llm_validation=False
                )
            )
        return self._entity_extractor
        
    async def aggregate(
        self,
        company: str,
        ticker: Optional[str] = None,
        lookback_hours: Optional[int] = None,
        max_articles: Optional[int] = None,
        min_relevance: Optional[float] = None,
        sources: Optional[List[NewsSource]] = None
    ) -> List[ArticleEnrichment]:
        """
        Aggregate news from all sources for a company.
        
        Args:
            company: Target company name
            ticker: Optional stock ticker
            lookback_hours: Hours to look back
            max_articles: Max articles to return
            min_relevance: Minimum relevance threshold
            sources: Optional specific sources to use
            
        Returns:
            List of enriched articles sorted by composite score
        """
        lookback = lookback_hours or self.config.lookback_hours
        max_art = max_articles or self.config.max_articles_per_provider
        min_rel = min_relevance or self.config.min_relevance_score
        
        logger.info(f"Starting news aggregation for {company} ({ticker}) - lookback: {lookback}h")
        
        # Initialize scorers
        self._relevance_scorer = CompanyRelevanceScorer(company, ticker)
        self._importance_ranker = ImportanceRanker(self.config)
        
        # Step 1: Fetch from all providers
        provider = await self._get_provider()
        raw_articles = await provider.fetch_news(
            company=company,
            ticker=ticker,
            lookback_hours=lookback,
            max_articles=max_art
        )
        
        logger.info(f"Fetched {len(raw_articles)} raw articles from providers")
        
        if not raw_articles:
            return []
            
        # Step 2: Deduplicate
        if self.config.enable_deduplication:
            raw_articles = deduplicate_articles(raw_articles, {
                'title_similarity_threshold': self.config.title_similarity_threshold,
                'content_fingerprint_threshold': self.config.content_fingerprint_threshold,
            })
            logger.info(f"After deduplication: {len(raw_articles)} articles")
            
        # Step 3: Enrich articles
        enrichments = await self._enrich_articles(raw_articles, company, ticker)
        
        # Step 4: Filter by relevance
        if self.config.enable_relevance_scoring:
            enrichments = [e for e in enrichments if e.relevance_score >= min_rel]
            logger.info(f"After relevance filtering: {len(enrichments)} articles")
            
        # Step 5: Calculate composite scores and rank
        for enrichment in enrichments:
            enrichment.composite_score = self._importance_ranker.calculate_composite_score(enrichment)
            
        # Sort by composite score
        enrichments.sort(key=lambda e: e.composite_score, reverse=True)
        
        # Limit results
        enrichments = enrichments[:max_art]
        
        logger.info(f"Aggregation complete: {len(enrichments)} final articles for {company}")
        return enrichments
        
    async def _enrich_articles(
        self,
        articles: List[NewsArticle],
        company: str,
        ticker: Optional[str]
    ) -> List[ArticleEnrichment]:
        """Enrich articles with all scores and entity extraction."""
        enrichments = []
        
        for article in articles:
            enrichment = ArticleEnrichment(article=article)
            
            # Quality scoring
            if self.config.enable_quality_scoring:
                quality = self.quality_scorer.score(article)
                enrichment.quality_score = quality.overall
                article.metadata = article.metadata or {}
                article.metadata['quality_score'] = quality.overall
                article.metadata['quality_details'] = quality.details
                
            # Credibility scoring
            if self.config.enable_credibility_scoring:
                cred = self.credibility_scorer.score(article)
                enrichment.credibility_score = cred.overall
                article.metadata['credibility_score'] = cred.overall
                article.metadata['credibility_details'] = cred.details
                
            # Freshness scoring
            if self.config.enable_freshness_scoring:
                fresh = self.freshness_scorer.score(article)
                enrichment.freshness_score = fresh.overall
                article.freshness_score = fresh.overall
                
            # Relevance scoring
            if self.config.enable_relevance_scoring and self._relevance_scorer:
                rel = self._relevance_scorer.score_relevance(article)
                enrichment.relevance_score = rel
                article.relevance_score = rel
                
            # Importance scoring
            enrichment.importance_score = self._calculate_importance(article)
            article.importance_score = enrichment.importance_score
            
            # Market impact scoring
            enrichment.market_impact_score = self._calculate_market_impact(article)
            article.market_impact_score = enrichment.market_impact_score
            
            # Entity extraction
            if self.config.enable_entity_extraction:
                entity_extractor = await self._get_entity_extractor()
                if entity_extractor:
                    try:
                        result = await entity_extractor.extract(article.content or f"{article.title} {article.summary}")
                        enrichment.entities = result.entities
                        enrichment.relationships = result.relationships
                        
                        # Update article with extracted entities
                        self._update_article_with_entities(article, result.entities)
                    except Exception as e:
                        logger.warning(f"Entity extraction failed: {e}")
                        
            enrichments.append(enrichment)
            
        return enrichments
        
    def _update_article_with_entities(self, article: NewsArticle, entities: List[Entity]):
        """Update article with extracted entities."""
        for entity in entities:
            if entity.entity_type == EntityType.COMPANY:
                cm = CompanyMention(
                    name=entity.text,
                    ticker=entity.ticker,
                    mention_count=1,
                    is_primary=(entity.text.lower() == entity.normalized_value.lower() if entity.normalized_value else False)
                )
                if not any(c.ticker == cm.ticker for c in article.companies):
                    article.companies.append(cm)
                    
            elif entity.entity_type == EntityType.PERSON:
                pm = PersonMention(
                    name=entity.text,
                    role=entity.metadata.get('role') if entity.metadata else None,
                    company=entity.metadata.get('company') if entity.metadata else None
                )
                if not any(p.name == pm.name for p in article.people):
                    article.people.append(pm)
                    
            elif entity.entity_type == EntityType.TICKER:
                if entity.ticker and entity.ticker not in article.tickers:
                    article.tickers.append(entity.ticker)
                    
            # Events from entity relationships
            # (Could be expanded to extract events from relationships)
            
    def _calculate_importance(self, article: NewsArticle) -> float:
        """Calculate article importance score."""
        score = 0.0
        
        # Length factor (longer articles often more important)
        content_len = len(article.content or '') + len(article.summary or '')
        if content_len > 2000:
            score += 0.3
        elif content_len > 1000:
            score += 0.2
        elif content_len > 500:
            score += 0.1
            
        # Number of entities mentioned
        entity_count = len(article.companies) + len(article.people) + len(article.tickers)
        score += min(entity_count * 0.05, 0.3)
        
        # Events detected
        event_count = len(article.events)
        score += min(event_count * 0.1, 0.2)
        
        # Source tier bonus
        if article.source in SourceCredibilityManager.TIER_1_SOURCES:
            score += 0.2
        elif article.source in SourceCredibilityManager.TIER_2_SOURCES:
            score += 0.1
            
        return min(score, 1.0)
        
    def _calculate_market_impact(self, article: NewsArticle) -> float:
        """Calculate potential market impact score."""
        score = 0.0
        
        # High-impact categories
        high_impact_categories = {
            NewsCategory.EARNINGS: 0.3,
            NewsCategory.GUIDANCE: 0.3,
            NewsCategory.MERGERS_ACQUISITIONS: 0.4,
            NewsCategory.IPO: 0.3,
            NewsCategory.BANKRUPTCY: 0.4,
            NewsCategory.REGULATORY: 0.25,
            NewsCategory.LAWSUIT: 0.25,
            NewsCategory.ANALYST_RATING: 0.2,
            NewsCategory.DIVIDEND: 0.15,
            NewsCategory.SHARE_BUYBACK: 0.2,
            NewsCategory.PRODUCT_LAUNCH: 0.15,
        }
        
        if article.category in high_impact_categories:
            score += high_impact_categories[article.category]
            
        # Sentiment extremity
        if article.sentiment:
            score += abs(article.sentiment.score) * 0.2
            
        # Primary company focus
        primary_companies = [c for c in article.companies if c.is_primary]
        if primary_companies:
            score += 0.15
            
        # Ticker mentions
        if article.tickers:
            score += 0.1
            
        return min(score, 1.0)
        
    async def close(self):
        """Close provider connections."""
        if self.provider:
            await self.provider.close_all()
            self.provider = None
            
        # Close entity extractor if needed
        # (Entity extractor is shared, don't close here)


# Convenience function
async def aggregate_news(
    company: str,
    ticker: Optional[str] = None,
    config: Optional[AggregatorConfig] = None,
    **kwargs
) -> List[ArticleEnrichment]:
    """Convenience function for news aggregation."""
    aggregator = NewsAggregator(config)
    try:
        return await aggregator.aggregate(company, ticker, **kwargs)
    finally:
        await aggregator.close()