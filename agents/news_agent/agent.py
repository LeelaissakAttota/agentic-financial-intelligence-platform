"""
News Agent Adapter - Bridges real news providers to existing NewsAgent interface
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

from data.news.schemas import (
    NewsArticle, NewsSummary, NewsAgentInput, NewsAgentOutput,
    WorkerResponse, NewsCategory, SentimentLabel, CompanyMention,
    EventDetection, ArticleSentiment, NewsSource
)
from data.news.pipeline import NewsPipeline, PipelineConfig, run_news_pipeline

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
        newsapi_key: Optional[str] = None,
        pipeline_config: Optional[PipelineConfig] = None
    ):
        self.pipeline_config = pipeline_config or PipelineConfig(
            finnhub_key=finnhub_key,
            alpha_vantage_key=alpha_vantage_key,
            newsapi_key=newsapi_key,
            # Enable advanced features
            enable_aggregator=True,
            enable_intelligence=True,
            enable_summarizer=True,
        )
        
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
            
            # Run pipeline
            result = await run_news_pipeline(
                company=company,
                ticker=ticker,
                config=self.pipeline_config,
                lookback_hours=lookback_hours,
                max_articles=max_articles,
                min_relevance=min_relevance
            )
            
            if not result.articles:
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
            
            # Convert to legacy format for backward compatibility
            legacy_output = self._convert_to_legacy(result)
            
            return WorkerResponse(
                status="success",
                data=legacy_output,
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
    
    def _convert_to_legacy(self, result: NewsAgentOutput) -> Dict[str, Any]:
        """Convert new output format to legacy format for compatibility."""
        legacy_articles = []
        for article in result.articles:
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
                "confidence": article.sentiment.confidence if article.sentiment else 0.5,
                "source": article.source.value,
                "url": article.url,
                "summary": article.summary,
                "published_at": article.published_at.isoformat() if article.published_at else None,
            })
        
        return {
            "company": result.company,
            "ticker": result.ticker,
            "articles": legacy_articles,
            "summary": result.summary.model_dump() if result.summary else None,
            "generated_at": result.generated_at.isoformat(),
            "lookback_hours": result.lookback_hours,
            "total_fetched": result.total_fetched,
            "sources_used": result.sources_used
        }
    
    async def close(self):
        """Close the agent."""
        # Pipeline handles its own cleanup
        pass


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