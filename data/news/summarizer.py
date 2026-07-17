"""
News Summarization - Generate executive summaries, positive/negative events, opportunities, risks
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Set, Tuple
from collections import defaultdict, Counter
import re

from data.news.schemas import (
    NewsArticle, NewsSummary, NewsCategory, SentimentLabel,
    ArticleSentiment, CompanyMention, PersonMention, EventDetection,
    NewsCategory as EventType
)
from data.news.intelligence import ArticleIntelligence, CompanyIntelligence

logger = logging.getLogger(__name__)


@dataclass
class SummarizationConfig:
    """Configuration for news summarization."""
    # LLM settings
    use_llm: bool = True
    llm_model: str = "google/gemini-2.0-flash-exp:free"
    max_tokens: int = 2000
    temperature: float = 0.3
    
    # Summary settings
    max_executive_summary_length: int = 500
    max_bullet_points: int = 10
    min_event_confidence: float = 0.5
    
    # Event categorization
    positive_categories: List[NewsCategory] = field(default_factory=lambda: [
        NewsCategory.EARNINGS,
        NewsCategory.GUIDANCE,
        NewsCategory.PRODUCT_LAUNCH,
        NewsCategory.PARTNERSHIP,
        NewsCategory.DIVIDEND,
        NewsCategory.SHARE_BUYBACK,
        NewsCategory.ANALYST_RATING,
        NewsCategory.IPO,
    ])
    
    negative_categories: List[NewsCategory] = field(default_factory=lambda: [
        NewsCategory.LAWSUIT,
        NewsCategory.REGULATORY,
        NewsCategory.LAYOFFS,
        NewsCategory.BANKRUPTCY,
        NewsCategory.SHORT_REPORT,
        NewsCategory.INSIDER_TRADING,
        NewsCategory.MANAGEMENT_CHANGE,
    ])
    
    # Risk/opportunity keywords
    risk_keywords: List[str] = field(default_factory=lambda: [
        "risk", "risky", "concern", "concerning", "challenge", "difficult",
        "decline", "decrease", "loss", "miss", "cut", "downgrade",
        "investigation", "probe", "lawsuit", "litigation", "fine", "penalty",
        "bankruptcy", "default", "liquidity", "solvency", "debt",
    ])
    
    opportunity_keywords: List[str] = field(default_factory=lambda: [
        "opportunity", "opportunities", "growth", "expand", "expansion",
        "invest", "investment", "record", "strong", "beat", "exceed",
        "upgrade", "outperform", "partnership", "acquisition", "merger",
        "new product", "launch", "innovation", "breakthrough", "milestone",
    ])


@dataclass
class NewsSummaryResult:
    """Complete news summarization result."""
    # Executive summary
    executive_summary: str
    
    # Sentiment overview
    overall_sentiment: SentimentLabel
    sentiment_score: float
    sentiment_distribution: Dict[str, int]
    
    # Key events
    positive_events: List[Dict[str, Any]] = field(default_factory=list)
    negative_events: List[Dict[str, Any]] = field(default_factory=list)
    neutral_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Risks and opportunities
    risks: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    
    # Company focus
    primary_companies: List[Dict[str, Any]] = field(default_factory=list)
    
    # Key metrics
    total_articles: int = 0
    time_period: Dict[str, str] = field(default_factory=dict)
    source_breakdown: Dict[str, int] = field(default_factory=dict)
    category_breakdown: Dict[str, int] = field(default_factory=dict)
    
    # Metadata
    generated_at: datetime = field(default_factory=datetime.utcnow)
    lookback_hours: int = 0
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "executive_summary": self.executive_summary,
            "overall_sentiment": self.overall_sentiment.value,
            "sentiment_score": self.sentiment_score,
            "sentiment_distribution": self.sentiment_distribution,
            "positive_events": self.positive_events,
            "negative_events": self.negative_events,
            "neutral_events": self.neutral_events,
            "risks": self.risks,
            "opportunities": self.opportunities,
            "primary_companies": self.primary_companies,
            "total_articles": self.total_articles,
            "time_period": self.time_period,
            "source_breakdown": self.source_breakdown,
            "category_breakdown": self.category_breakdown,
            "generated_at": self.generated_at.isoformat(),
            "lookback_hours": self.lookback_hours,
            "confidence": self.confidence,
        }


class EventClassifier:
    """Classifies events as positive, negative, or neutral."""
    
    def __init__(self, config: SummarizationConfig):
        self.config = config
        self.positive_categories = set(config.positive_categories)
        self.negative_categories = set(config.negative_categories)
        
    def classify(self, event: EventDetection, article_sentiment: Optional[ArticleSentiment] = None) -> str:
        """Classify event as positive, negative, or neutral."""
        # Primary: event category
        if event.event_type in self.positive_categories:
            return "positive"
        if event.event_type in self.negative_categories:
            return "negative"
            
        # Secondary: article sentiment
        if article_sentiment:
            if article_sentiment.label == SentimentLabel.POSITIVE:
                return "positive"
            elif article_sentiment.label == SentimentLabel.NEGATIVE:
                return "negative"
                
        # Tertiary: event confidence (higher = more definitive)
        if event.confidence > 0.8:
            # Use sentiment score if available
            if article_sentiment and abs(article_sentiment.score) > 0.3:
                return "positive" if article_sentiment.score > 0 else "negative"
                
        return "neutral"


class RiskOpportunityExtractor:
    """Extracts risks and opportunities from articles and intelligence."""
    
    def __init__(self, config: SummarizationConfig):
        self.config = config
        self.risk_keywords = [k.lower() for k in config.risk_keywords]
        self.opportunity_keywords = [k.lower() for k in config.opportunity_keywords]
        
    def extract_from_text(self, text: str) -> Tuple[List[str], List[str]]:
        """Extract risks and opportunities from text."""
        text_lower = text.lower()
        risks = []
        opportunities = []
        
        # Check risk keywords
        for keyword in self.risk_keywords:
            if keyword in text_lower:
                # Extract context around keyword
                context = self._extract_context(text_lower, keyword)
                if context and context not in risks:
                    risks.append(context)
                    
        # Check opportunity keywords
        for keyword in self.opportunity_keywords:
            if keyword in text_lower:
                context = self._extract_context(text_lower, keyword)
                if context and context not in opportunities:
                    opportunities.append(context)
                    
        return risks[:20], opportunities[:20]  # Limit
        
    def _extract_context(self, text: str, keyword: str, window: int = 80) -> str:
        """Extract sentence context around keyword."""
        idx = text.find(keyword)
        if idx == -1:
            return keyword
            
        # Find sentence boundaries
        start = max(0, text.rfind('.', 0, idx) + 1)
        end = text.find('.', idx)
        if end == -1:
            end = min(len(text), idx + window)
            
        sentence = text[start:end].strip()
        if len(sentence) > 200:
            sentence = sentence[:200] + "..."
        return sentence
        
    def extract_from_events(
        self, 
        events: List[EventDetection], 
        articles: List[NewsArticle]
    ) -> Tuple[List[str], List[str]]:
        """Extract risks and opportunities from events and articles."""
        risks = set()
        opportunities = set()
        
        # From events
        for event in events:
            event_text = f"{event.event_type.value} {event.details.get('context_snippet', '')}"
            if event.confidence > 0.6:
                if event.event_type in [NewsCategory.LAWSUIT, NewsCategory.REGULATORY, 
                                         NewsCategory.BANKRUPTCY, NewsCategory.LAYOFFS]:
                    risks.add(f"{event.event_type.value}: {event.details.get('context_snippet', '')[:150]}")
                elif event.event_type in [NewsCategory.EARNINGS, NewsCategory.GUIDANCE,
                                          NewsCategory.PRODUCT_LAUNCH, NewsCategory.PARTNERSHIP]:
                    opportunities.add(f"{event.event_type.value}: {event.details.get('context_snippet', '')[:150]}")
                    
        # From article text
        for article in articles:
            full_text = f"{article.title} {article.summary}"
            if article.content:
                full_text += f" {article.content[:1000]}"
                
            r, o = self.extract_from_text(full_text)
            risks.update(r)
            opportunities.update(o)
            
        return list(risks)[:15], list(opportunities)[:15]


class ExecutiveSummaryGenerator:
    """Generates executive summary from news intelligence."""
    
    def __init__(self, config: SummarizationConfig):
        self.config = config
        
    def generate(
        self,
        articles: List[NewsArticle],
        intelligence_results: List[ArticleIntelligence],
        company_intelligence: Dict[str, CompanyIntelligence],
        sentiment_summary: Dict[str, Any],
        top_events: List[EventDetection]
    ) -> str:
        """Generate executive summary."""
        parts = []
        
        # Opening: overall assessment
        total_articles = len(articles)
        if total_articles == 0:
            return "No news articles found for the specified period."
            
        sentiment = sentiment_summary.get("overall", SentimentLabel.NEUTRAL)
        score = sentiment_summary.get("score", 0.0)
        
        parts.append(
            f"Analysis of {total_articles} news articles over the past period "
            f"shows {sentiment.value} sentiment (score: {score:.2f})."
        )
        
        # Primary companies
        primary_companies = [
            (name, ci) for name, ci in company_intelligence.items() 
            if ci.is_primary or ci.mention_count > 2
        ]
        if primary_companies:
            company_names = ", ".join(name for name, _ in primary_companies[:5])
            parts.append(f"Primary focus: {company_names}.")
            
        # Key events summary
        event_counts = Counter()
        for intel in intelligence_results:
            for event in intel.events:
                event_counts[event.event_type.value] += 1
                
        if event_counts:
            top_event_types = event_counts.most_common(3)
            events_str = ", ".join(f"{etype} ({count})" for etype, count in top_event_types)
            parts.append(f"Key events: {events_str}.")
            
        # Sentiment detail
        dist = sentiment_summary.get("distribution", {})
        if dist:
            parts.append(
                f"Sentiment distribution: "
                f"{dist.get('positive', 0)} positive, "
                f"{dist.get('negative', 0)} negative, "
                f"{dist.get('neutral', 0)} neutral."
            )
            
        # Market impact
        high_impact = sum(1 for a in articles if a.market_impact_score > 0.6)
        if high_impact:
            parts.append(f"{high_impact} articles indicate high market impact potential.")
            
        # Combine and trim
        summary = " ".join(parts)
        if len(summary) > self.config.max_executive_summary_length:
            summary = summary[:self.config.max_executive_summary_length] + "..."
            
        return summary


class NewsSummarizer:
    """Main news summarization engine."""
    
    def __init__(self, config: Optional[SummarizationConfig] = None):
        self.config = config or SummarizationConfig()
        self.event_classifier = EventClassifier(self.config)
        self.risk_extractor = RiskOpportunityExtractor(self.config)
        self.summary_generator = ExecutiveSummaryGenerator(self.config)
        
    async def summarize(
        self,
        articles: List[NewsArticle],
        intelligence_results: List[ArticleIntelligence],
        company_intelligence: Dict[str, CompanyIntelligence],
        lookback_hours: int = 24
    ) -> NewsSummaryResult:
        """Generate comprehensive news summary."""
        if not articles:
            return NewsSummaryResult(
                executive_summary="No news articles found for the specified period.",
                overall_sentiment=SentimentLabel.NEUTRAL,
                sentiment_score=0.0,
                sentiment_distribution={},
                total_articles=0,
                lookback_hours=lookback_hours
            )
            
        logger.info(f"Generating summary for {len(articles)} articles")
        
        # 1. Sentiment aggregation
        sentiment_summary = self._aggregate_sentiment(articles)
        
        # 2. Classify events
        positive_events = []
        negative_events = []
        neutral_events = []
        
        all_events = []
        for intel in intelligence_results:
            all_events.extend(intel.events)
            
        for intel in intelligence_results:
            for event in intel.events:
                # Find corresponding article for sentiment
                article = next((a for a in articles if a.title == intel.article.title), None)
                article_sentiment = article.sentiment if article else None
                
                classification = self.event_classifier.classify(event, article_sentiment)
                event_dict = {
                    "type": event.event_type.value,
                    "confidence": event.confidence,
                    "details": event.details,
                    "article_title": intel.article.title,
                    "source": intel.article.source.value,
                    "published_at": intel.article.published_at.isoformat(),
                }
                
                if classification == "positive":
                    positive_events.append(event_dict)
                elif classification == "negative":
                    negative_events.append(event_dict)
                else:
                    neutral_events.append(event_dict)
                    
        # 3. Extract risks and opportunities
        risks, opportunities = self.risk_extractor.extract_from_events(
            all_events, articles
        )
        
        # 4. Primary companies
        primary_companies = [
            {
                "name": name,
                "ticker": ci.ticker,
                "mention_count": ci.mention_count,
                "is_primary": ci.is_primary,
                "avg_sentiment": ci.sentiment,
                "event_summary": ci.to_dict()["events"],
                "sources": list(ci.sources),
            }
            for name, ci in company_intelligence.items()
            if ci.is_primary or ci.mention_count >= 2
        ]
        primary_companies.sort(key=lambda c: c["mention_count"], reverse=True)
        
        # 5. Generate executive summary
        # Calculate sentiment summary
        sentiments = [a.sentiment for a in articles if a.sentiment]
        if sentiments:
            avg_score = sum(s.score for s in sentiments) / len(sentiments)
            if avg_score > 0.15:
                overall = SentimentLabel.POSITIVE
            elif avg_score < -0.15:
                overall = SentimentLabel.NEGATIVE
            else:
                overall = SentimentLabel.NEUTRAL
        else:
            avg_score = 0.0
            overall = SentimentLabel.NEUTRAL
            
        sentiment_summary = {
            "overall": overall,
            "score": avg_score,
            "distribution": {
                "positive": sum(1 for s in sentiments if s.label == SentimentLabel.POSITIVE),
                "negative": sum(1 for s in sentiments if s.label == SentimentLabel.NEGATIVE),
                "neutral": sum(1 for s in sentiments if s.label == SentimentLabel.NEUTRAL),
            }
        }
        
        executive_summary = self.summary_generator.generate(
            articles, intelligence_results, company_intelligence,
            sentiment_summary, all_events
        )
        
        # 6. Build result
        # Source breakdown
        source_counts = Counter(a.source.value for a in articles)
        
        # Category breakdown
        category_counts = Counter()
        for a in articles:
            if a.category:
                category_counts[a.category.value] += 1
                
        # Time period
        if articles:
            period_start = min(a.published_at for a in articles)
            period_end = max(a.published_at for a in articles)
        else:
            period_start = period_end = datetime.utcnow()
            
        return NewsSummaryResult(
            executive_summary=executive_summary,
            overall_sentiment=sentiment_summary["overall"],
            sentiment_score=sentiment_summary["score"],
            sentiment_distribution=sentiment_summary["distribution"],
            positive_events=positive_events[:self.config.max_bullet_points],
            negative_events=negative_events[:self.config.max_bullet_points],
            neutral_events=neutral_events[:self.config.max_bullet_points],
            risks=risks[:self.config.max_bullet_points],
            opportunities=opportunities[:self.config.max_bullet_points],
            primary_companies=primary_companies[:10],
            total_articles=len(articles),
            time_period={
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
            },
            source_breakdown=dict(source_counts),
            category_breakdown=dict(category_counts),
            lookback_hours=lookback_hours,
            confidence=self._calculate_confidence(articles, intelligence_results)
        )
        
    def _aggregate_sentiment(self, articles: List[NewsArticle]) -> Dict[str, Any]:
        """Aggregate sentiment across articles."""
        sentiments = [a.sentiment for a in articles if a.sentiment]
        
        if not sentiments:
            return {
                "overall": SentimentLabel.NEUTRAL,
                "score": 0.0,
                "distribution": {"positive": 0, "negative": 0, "neutral": 0}
            }
            
        avg_score = sum(s.score for s in sentiments) / len(sentiments)
        
        if avg_score > 0.15:
            overall = SentimentLabel.POSITIVE
        elif avg_score < -0.15:
            overall = SentimentLabel.NEGATIVE
        else:
            overall = SentimentLabel.NEUTRAL
            
        return {
            "overall": overall,
            "score": avg_score,
            "distribution": {
                "positive": sum(1 for s in sentiments if s.label == SentimentLabel.POSITIVE),
                "negative": sum(1 for s in sentiments if s.label == SentimentLabel.NEGATIVE),
                "neutral": sum(1 for s in sentiments if s.label == SentimentLabel.NEUTRAL),
            }
        }
        
    def _calculate_confidence(
        self, 
        articles: List[NewsArticle], 
        intelligence_results: List[ArticleIntelligence]
    ) -> float:
        """Calculate overall confidence in the summary."""
        if not articles:
            return 0.0
            
        factors = []
        
        # Article count factor
        article_factor = min(len(articles) / 20.0, 1.0)
        factors.append(article_factor)
        
        # Average article quality
        quality_scores = []
        for a in articles:
            if a.metadata and 'quality_score' in a.metadata:
                quality_scores.append(a.metadata['quality_score'])
        if quality_scores:
            factors.append(sum(quality_scores) / len(quality_scores))
            
        # Source diversity
        unique_sources = len(set(a.source for a in articles))
        source_factor = min(unique_sources / 5.0, 1.0)
        factors.append(source_factor)
        
        # Intelligence extraction success rate
        if intelligence_results:
            success_rate = len([i for i in intelligence_results if i.events or i.companies]) / len(intelligence_results)
            factors.append(success_rate)
            
        return sum(factors) / len(factors) if factors else 0.5


async def summarize_news(
    articles: List[NewsArticle],
    intelligence_results: List[ArticleIntelligence],
    company_intelligence: Dict[str, CompanyIntelligence],
    config: Optional[SummarizationConfig] = None,
    lookback_hours: int = 24
) -> NewsSummaryResult:
    """Convenience function for news summarization."""
    summarizer = NewsSummarizer(config)
    return await summarizer.summarize(
        articles, intelligence_results, company_intelligence, lookback_hours
    )