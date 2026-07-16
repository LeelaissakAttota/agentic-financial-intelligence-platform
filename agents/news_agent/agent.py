"""
News Agent Adapter - Bridges real news providers to existing NewsAgent interface
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from data.news.schemas import (
    NewsArticle, NewsSummary, NewsAgentInput, NewsAgentOutput,
    WorkerResponse, NewsCategory, SentimentLabel, CompanyMention,
    EventDetection, ArticleSentiment, NewsSource
)
from data.news.providers import get_news_provider
from data.news.cache import get_news_cache

logger = logging.getLogger(__name__)


class NewsIntelligenceAgent:
    """
    Enterprise News Intelligence Agent using real news providers.
    
    Replaces the mock news agent with real data from:
    - Yahoo Finance
    - Finnhub
    - Alpha Vantage
    - NewsAPI
    - Google News RSS
    - Financial RSS feeds
    """
    
    def __init__(
        self,
        finnhub_key: Optional[str] = None,
        alpha_vantage_key: Optional[str] = None,
        newsapi_key: Optional[str] = None
    ):
        self.provider = get_news_provider(
            finnhub_key=finnhub_key,
            alpha_vantage_key=alpha_vantage_key,
            newsapi_key=newsapi_key
        )
        self.cache = get_news_cache()
    
    async def run(
        self,
        company: str,
        ticker: Optional[str] = None,
        lookback_hours: int = 24,
        max_articles: int = 50,
        min_relevance: float = 0.3
    ) -> WorkerResponse:
        """
        Execute news intelligence analysis for a company.
        
        Args:
            company: Company name
            ticker: Optional stock ticker
            lookback_hours: How far back to fetch news
            max_articles: Maximum articles to fetch
            min_relevance: Minimum relevance threshold
            
        Returns:
            WorkerResponse with news analysis
        """
        try:
            logger.info(f"Starting news intelligence for {company} ({ticker})")
            
            # Fetch real news articles
            articles = await self.provider.fetch_news(
                company=company,
                ticker=ticker,
                lookback_hours=lookback_hours,
                max_articles=max_articles
            )
            
            if not articles:
                logger.warning(f"No articles found for {company}")
                return WorkerResponse(
                    status="success",
                    data={
                        "company": company,
                        "ticker": ticker,
                        "articles": [],
                        "summary": None,
                        "generated_at": datetime.utcnow().isoformat(),
                        "lookback_hours": lookback_hours,
                        "total_fetched": 0,
                        "sources_used": []
                    },
                    error=None,
                    usage=None
                )
            
            # Filter by relevance
            filtered = [a for a in articles if a.relevance_score >= min_relevance]
            
            # Generate summary
            summary = await self._generate_summary(company, ticker, filtered, lookback_hours)
            
            # Prepare output
            output = NewsAgentOutput(
                company=company,
                ticker=ticker,
                articles=filtered,
                summary=summary,
                generated_at=datetime.utcnow(),
                lookback_hours=lookback_hours,
                total_fetched=len(articles),
                sources_used=list(set(a.source.value for a in filtered))
            )
            
            return WorkerResponse(
                status="success",
                data=output.model_dump(),
                error=None,
                usage=None
            )
            
        except Exception as e:
            logger.error(f"News intelligence failed for {company}: {e}")
            return WorkerResponse(
                status="error",
                data=None,
                error=f"News intelligence failed: {str(e)}",
                usage=None
            )
    
    async def _generate_summary(
        self,
        company: str,
        ticker: Optional[str],
        articles: List[NewsArticle],
        lookback_hours: int
    ) -> NewsSummary:
        """Generate aggregated news summary."""
        if not articles:
            return NewsSummary(
                company=company,
                ticker=ticker,
                period_start=datetime.utcnow() - timedelta(hours=lookback_hours),
                period_end=datetime.utcnow(),
                total_articles=0,
                overall_sentiment=SentimentLabel.NEUTRAL,
                sentiment_score=0.0,
                category_counts={}
            )
        
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
        
        # Event aggregation
        all_events = []
        for article in articles:
            all_events.extend(article.events)
        
        # Top events by confidence
        top_events = sorted(
            all_events, 
            key=lambda e: e.confidence, 
            reverse=True
        )[:10]
        
        # Related companies
        company_mentions = {}
        for article in articles:
            for cm in article.companies:
                if cm.ticker:
                    key = cm.ticker
                    if key not in company_mentions:
                        company_mentions[key] = CompanyMention(
                            name=cm.name,
                            ticker=cm.ticker,
                            mention_count=0
                        )
                    company_mentions[key].mention_count += cm.mention_count
        
        related_companies = sorted(
            company_mentions.values(),
            key=lambda c: c.mention_count,
            reverse=True
        )[:10]
        
        # Source diversity
        source_counts = {}
        for article in articles:
            src = article.source.value
            source_counts[src] = source_counts.get(src, 0) + 1
        
        # Top articles by composite score
        top_articles = sorted(
            articles,
            key=lambda a: a.metadata.get('composite_score', 0) if a.metadata else 0,
            reverse=True
        )[:5]
        
        return NewsSummary(
            company=company,
            ticker=ticker,
            period_start=datetime.utcnow() - timedelta(hours=lookback_hours),
            period_end=datetime.utcnow(),
            total_articles=len(articles),
            overall_sentiment=overall,
            sentiment_score=avg_score,
            sentiment_distribution={
                "positive": pos,
                "negative": neg,
                "neutral": neu
            },
            category_counts=category_counts,
            top_events=top_events,
            related_companies=related_companies,
            top_articles=top_articles,
            source_counts=source_counts,
            avg_importance=sum(a.importance_score for a in articles) / len(articles),
            avg_market_impact=sum(a.market_impact_score for a in articles) / len(articles),
            avg_relevance=sum(a.relevance_score for a in articles) / len(articles)
        )
    
    async def close(self):
        """Close provider connections."""
        await self.provider.close_all()


# Backward compatibility adapter for existing NewsAgent interface
class NewsAgentAdapter:
    """
    Adapter that makes NewsIntelligenceAgent compatible with 
    the existing ManagerAgent worker interface.
    """
    
    def __init__(self):
        self._agent: Optional[NewsIntelligenceAgent] = None
    
    async def _get_agent(self) -> NewsIntelligenceAgent:
        """Lazy initialization of the news agent."""
        if self._agent is None:
            import os
            self._agent = NewsIntelligenceAgent(
                finnhub_key=os.getenv('FINNHUB_API_KEY'),
                alpha_vantage_key=os.getenv('ALPHA_VANTAGE_API_KEY'),
                newsapi_key=os.getenv('NEWSAPI_KEY')
            )
        return self._agent
    
    async def run(
        self,
        company: str,
        context: Optional[Dict[str, Any]] = None
    ) -> WorkerResponse:
        """
        Run method compatible with BaseWorkerAgent interface.
        
        Args:
            company: Company name (can be name or ticker)
            context: Optional context dict with:
                - ticker: Stock ticker symbol
                - lookback_hours: Hours to look back
                - max_articles: Max articles to fetch
                - min_relevance: Minimum relevance threshold
                
        Returns:
            WorkerResponse with news analysis
        """
        context = context or {}
        
        # Extract ticker from company if needed
        ticker = context.get('ticker')
        if not ticker and len(company) <= 5 and company.isupper():
            ticker = company
            # Try to get company name - for now use company as-is
        
        lookback_hours = context.get('lookback_hours', 24)
        max_articles = context.get('max_articles', 50)
        min_relevance = context.get('min_relevance', 0.3)
        
        agent = await self._get_agent()
        
        return await agent.run(
            company=company,
            ticker=ticker,
            lookback_hours=lookback_hours,
            max_articles=max_articles,
            min_relevance=min_relevance
        )
    
    async def close(self):
        """Close the agent."""
        if self._agent:
            await self._agent.close()
            self._agent = None


# Legacy schema conversion for backward compatibility
def convert_to_legacy_format(output: NewsAgentOutput) -> Dict[str, Any]:
    """Convert new output format to legacy format for compatibility."""
    legacy_articles = []
    for article in output.articles:
        # Map sentiment label to impact
        if article.sentiment:
            if article.sentiment.label == SentimentLabel.POSITIVE:
                impact = "positive"
            elif article.sentiment.label == SentimentLabel.NEGATIVE:
                impact = "negative"
            else:
                impact = "neutral"
        else:
            impact = "neutral"
        
        legacy_articles.append({
            "title": article.title,
            "impact": impact,
            "confidence": article.sentiment.confidence if article.sentiment else 0.5
        })
    
    return {
        "company": output.company,
        "articles": legacy_articles,
        "generated_at": output.generated_at.isoformat(),
        "metadata": {
            "total_fetched": output.total_fetched,
            "sources_used": output.sources_used,
            "lookback_hours": output.lookback_hours
        }
    }


async def run_news_agent(
    company: str,
    context: Optional[Dict[str, Any]] = None
) -> WorkerResponse:
    """
    Convenience function for running news analysis.
    Compatible with existing ManagerAgent calling pattern.
    """
    adapter = NewsAgentAdapter()
    try:
        result = await adapter.run(company, context)
        return result
    finally:
        await adapter.close()


if __name__ == "__main__":
    import asyncio
    
    async def test():
        adapter = NewsAgentAdapter()
        try:
            result = await adapter.run("NVIDIA", {"ticker": "NVDA", "lookback_hours": 48})
            print(f"Status: {result.status}")
            if result.data:
                data = result.data
                print(f"Company: {data.get('company')}")
                print(f"Total articles: {data.get('total_fetched')}")
                print(f"Sources: {data.get('sources_used')}")
                if data.get('summary'):
                    print(f"Sentiment: {data['summary'].get('overall_sentiment')}")
                    print(f"Articles: {len(data.get('articles', []))}")
        finally:
            await adapter.close()
    
    asyncio.run(test())