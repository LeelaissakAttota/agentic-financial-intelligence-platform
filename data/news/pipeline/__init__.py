"""
News Processing Pipeline

Main pipeline that integrates all news processing components:
- Provider management
- HTML cleaning
- Duplicate detection
- Quality scoring
- Article enrichment
- Entity extraction
- Company intelligence
- News summarization
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from data.news.schemas import NewsArticle, NewsAgentInput, NewsAgentOutput, WorkerResponse, NewsSummary
from data.news.providers import get_news_provider
from data.news.providers.base import NewsProviderBase
from data.news.pipeline.html_cleaner import clean_html
from data.news.pipeline.duplicate_detector import DuplicateDetector, deduplicate_articles
from data.news.pipeline.quality_scorer import QualityScorer, score_quality, QualityConfig

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for news processing pipeline."""
    # Provider settings
    finnhub_key: Optional[str] = None
    alpha_vantage_key: Optional[str] = None
    newsapi_key: Optional[str] = None
    
    # Fetch settings
    lookback_hours: int = 24
    max_articles_per_provider: int = 50
    min_providers: int = 2
    
    # Processing settings
    enable_html_cleaning: bool = True
    enable_deduplication: bool = True
    enable_quality_scoring: bool = True
    min_quality_score: float = 0.3
    min_relevance_score: float = 0.3
    
    # Deduplication settings
    title_similarity_threshold: float = 0.80
    content_fingerprint_threshold: float = 0.85
    
    # Quality settings
    quality_config: Optional[QualityConfig] = None
    
    # HTML cleaning settings
    html_max_length: int = 5000
    html_keep_links: bool = True
    html_keep_images: bool = False
    
    # Performance
    max_concurrent_providers: int = 5
    provider_timeout: int = 30


class NewsPipeline:
    """
    Main news processing pipeline.
    
    Flow:
    1. Fetch articles from multiple providers concurrently
    2. Clean HTML content (if enabled)
    3. Deduplicate articles
    4. Score quality
    5. Filter by relevance and quality
    6. Rank and return top articles
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        
        # Core pipeline components
        self.provider: Optional[NewsProviderBase] = None
        self.duplicate_detector = DuplicateDetector({
            'title_similarity_threshold': self.config.title_similarity_threshold,
            'content_fingerprint_threshold': self.config.content_fingerprint_threshold,
        })
        self.quality_scorer = QualityScorer(self.config.quality_config)
        
    async def _get_provider(self) -> NewsProviderBase:
        """Get or create provider instance."""
        if self.provider is None:
            self.provider = get_news_provider(
                finnhub_key=self.config.finnhub_key,
                alpha_vantage_key=self.config.alpha_vantage_key,
                newsapi_key=self.config.newsapi_key
            )
        return self.provider
    
    async def process(
        self,
        company: str,
        ticker: Optional[str] = None,
        lookback_hours: Optional[int] = None,
        max_articles: Optional[int] = None,
        min_relevance: Optional[float] = None
    ) -> NewsAgentOutput:
        """
        Process news for a company through the full pipeline.
        
        Args:
            company: Company name
            ticker: Optional stock ticker
            lookback_hours: How far back to fetch (default from config)
            max_articles: Max articles to return (default from config)
            min_relevance: Minimum relevance threshold (default from config)
            
        Returns:
            NewsAgentOutput with processed articles and summary
        """
        lookback = lookback_hours or self.config.lookback_hours
        max_art = max_articles or self.config.max_articles_per_provider
        min_rel = min_relevance or self.config.min_relevance_score
        
        logger.info(f"Starting news pipeline for {company} ({ticker}) - lookback: {lookback}h")
        
        provider = await self._get_provider()
        articles = await provider.fetch_news(
            company=company,
            ticker=ticker,
            lookback_hours=lookback,
            max_articles=max_art
        )
        
        logger.info(f"Fetched {len(articles)} raw articles from providers")
        
        if not articles:
            return self._empty_output(company, ticker, lookback)
        
        # Step 2: Clean HTML content
        if self.config.enable_html_cleaning:
            articles = await self._clean_articles(articles)
        
        # Step 3: Deduplicate
        if self.config.enable_deduplication:
            articles = deduplicate_articles(articles, {
                'title_similarity_threshold': self.config.title_similarity_threshold,
                'content_fingerprint_threshold': self.config.content_fingerprint_threshold,
            })
            logger.info(f"After deduplication: {len(articles)} articles")
        
        # Step 4: Quality scoring
        if self.config.enable_quality_scoring:
            articles = self._score_and_filter_quality(articles)
            logger.info(f"After quality filtering: {len(articles)} articles")
        
        # Step 5: Filter by relevance
        articles = [a for a in articles if a.relevance_score >= min_rel]
        logger.info(f"After relevance filtering: {len(articles)} articles")
        
        # Step 6: Rank and limit
        articles = self._rank_articles(articles)[:max_articles]
        
        # Generate summary
        summary = await self._generate_summary(company, ticker, articles, lookback)
        
        return NewsAgentOutput(
            company=company,
            ticker=ticker,
            articles=articles,
            summary=summary,
            generated_at=datetime.utcnow(),
            lookback_hours=lookback,
            total_fetched=len(articles),
            sources_used=list(set(a.source.value for a in articles))
        )
    
    async def _get_provider(self) -> NewsProviderBase:
        """Get or create provider instance."""
        if self.provider is None:
            self.provider = get_news_provider(
                finnhub_key=self.config.finnhub_key,
                alpha_vantage_key=self.config.alpha_vantage_key,
                newsapi_key=self.config.newsapi_key
            )
        return self.provider
    
    async def _clean_articles(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Clean HTML content from articles."""
        cleaned = []
        for article in articles:
            if article.content:
                try:
                    cleaned_content = clean_html(article.content, {
                        'max_length': self.config.html_max_length,
                        'keep_links': self.config.html_keep_links,
                        'keep_images': self.config.html_keep_images,
                    })
                    article.content = cleaned_content
                except Exception as e:
                    logger.warning(f"HTML cleaning failed for article: {e}")
            cleaned.append(article)
        return cleaned
    
    def _score_and_filter_quality(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Score quality and filter low-quality articles."""
        filtered = []
        for article in articles:
            quality = self.quality_scorer.score(article)
            article.metadata = article.metadata or {}
            article.metadata['quality_score'] = quality.overall
            article.metadata['quality_details'] = quality.details
            
            if quality.overall >= self.config.min_quality_score:
                filtered.append(article)
            else:
                logger.debug(f"Filtered low quality article: {article.title[:50]} (score: {quality.overall:.2f})")
        return filtered
    
    def _rank_articles(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Rank articles by composite score."""
        def rank_key(article: NewsArticle) -> float:
            return article.metadata.get('composite_score', article.relevance_score)
        return sorted(articles, key=rank_key, reverse=True)
    
    async def _generate_summary(
        self,
        company: str,
        ticker: Optional[str],
        articles: List[NewsArticle],
        lookback_hours: int
    ) -> Optional[NewsSummary]:
        """Generate news summary."""
        from data.news.schemas import NewsSummary, SentimentLabel, CompanyMention, EventDetection
        from datetime import timedelta
        
        if not articles:
            return None
        
        # Sentiment aggregation
        sentiments = [a.sentiment for a in articles if a.sentiment]
        if sentiments:
            avg_score = sum(s.score for s in sentiments) / len(sentiments)
            pos = sum(1 for s in sentiments if s.label == SentimentLabel.POSITIVE)
            neg = sum(1 for s in sentiments if s.label == SentimentLabel.NEGATIVE)
            neu = sum(1 for s in sentiments if s.label == SentimentLabel.NEUTRAL)
            
            if avg_score > 0.15:
                overall = SentimentLabel.POSITIVE
            elif avg_score < -0.15:
                overall = SentimentLabel.NEGATIVE
            else:
                overall = SentimentLabel.NEUTRAL
        else:
            avg_score = 0.0
            pos = neg = neu = 0
            overall = SentimentLabel.NEUTRAL
        
        # Category counts
        category_counts = {}
        for article in articles:
            if article.category:
                cat = article.category.value
                category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Top events
        all_events = []
        for article in articles:
            all_events.extend(article.events)
        top_events = sorted(all_events, key=lambda e: e.confidence, reverse=True)[:10]
        
        # Related companies
        company_mentions = {}
        for article in articles:
            for cm in article.companies:
                if cm.ticker:
                    key = cm.ticker
                    if key not in company_mentions:
                        company_mentions[key] = CompanyMention(name=cm.name, ticker=cm.ticker, mention_count=0)
                    company_mentions[key].mention_count += cm.mention_count
        
        related_companies = sorted(
            company_mentions.values(),
            key=lambda c: c.mention_count,
            reverse=True
        )[:10]
        
        # Top articles by composite score
        top_articles = sorted(
            articles,
            key=lambda a: a.metadata.get('composite_score', a.relevance_score),
            reverse=True
        )[:5]
        
        # Source counts
        source_counts = {}
        for article in articles:
            src = article.source.value
            source_counts[src] = source_counts.get(src, 0) + 1
        
        return NewsSummary(
            company=company,
            ticker=ticker,
            period_start=datetime.utcnow() - timedelta(hours=lookback_hours),
            period_end=datetime.utcnow(),
            total_articles=len(articles),
            overall_sentiment=overall,
            sentiment_score=avg_score,
            sentiment_distribution={"positive": pos, "negative": neg, "neutral": neu},
            category_counts=category_counts,
            top_events=top_events,
            related_companies=related_companies,
            top_articles=top_articles,
            source_counts=source_counts,
            avg_importance=sum(a.importance_score for a in articles) / len(articles) if articles else 0,
            avg_market_impact=sum(a.market_impact_score for a in articles) / len(articles) if articles else 0,
            avg_relevance=sum(a.relevance_score for a in articles) / len(articles) if articles else 0,
        )
    
    def _empty_output(self, company: str, ticker: Optional[str], lookback: int) -> NewsAgentOutput:
        """Return empty output for no articles case."""
        from data.news.schemas import NewsSummary, SentimentLabel
        return NewsAgentOutput(
            company=company,
            ticker=ticker,
            articles=[],
            summary=NewsSummary(
                company=company,
                ticker=ticker,
                period_start=datetime.utcnow(),
                period_end=datetime.utcnow(),
                total_articles=0,
                overall_sentiment=SentimentLabel.NEUTRAL,
                sentiment_score=0.0,
            ),
            generated_at=datetime.utcnow(),
            lookback_hours=lookback,
            total_fetched=0,
            sources_used=[]
        )
    
    async def close(self):
        """Close provider connections."""
        if self.provider:
            await self.provider.close_all()
            self.provider = None


# Convenience function
async def run_news_pipeline(
    company: str,
    ticker: Optional[str] = None,
    config: Optional[PipelineConfig] = None,
    **kwargs
) -> NewsAgentOutput:
    """Run the news pipeline with given configuration."""
    pipeline = NewsPipeline(config)
    try:
        return await pipeline.process(company, ticker, **kwargs)
    finally:
        await pipeline.close()


# Backward compatibility exports
from data.news.pipeline.html_cleaner import clean_html
from data.news.pipeline.duplicate_detector import DuplicateDetector, deduplicate_articles
from data.news.pipeline.quality_scorer import QualityScorer, score_quality, QualityConfig

__all__ = [
    # Core pipeline
    "NewsPipeline",
    "PipelineConfig",
    "run_news_pipeline",
    
    # Components
    "clean_html",
    "DuplicateDetector",
    "deduplicate_articles",
    "QualityScorer",
    "score_quality",
    "QualityConfig",
]