"""
Quality Scorer for News Articles

Evaluates article quality based on multiple dimensions:
- Content completeness
- Structural quality
- Information density
- Writing quality indicators
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any

from data.news.schemas import NewsArticle, NewsSource

logger = logging.getLogger(__name__)


@dataclass
class QualityConfig:
    """Configuration for quality scoring."""
    min_title_length: int = 10
    max_title_length: int = 150
    min_summary_length: int = 50
    min_content_length: int = 200
    ideal_content_length: int = 2000
    require_author: bool = False
    require_published_at: bool = True
    require_source: bool = True


@dataclass
class QualityScore:
    """Detailed quality score breakdown."""
    overall: float  # 0.0 - 1.0
    completeness: float
    structure: float
    information_density: float
    writing_quality: float
    details: Dict[str, Any]


class QualityScorer:
    """
    Scores article quality based on multiple dimensions.
    
    Dimensions:
    - Completeness (30%): Has title, summary, content, author, published_at, source
    - Structure (25%): Title length, summary length, paragraph structure
    - Information Density (25%): Entity count, number count, quote presence
    - Writing Quality (20%): Readability, no clickbait, proper capitalization
    """
    
    # High-quality financial sources
    PREMIUM_SOURCES = {
        NewsSource.REUTERS, NewsSource.BLOOMBERG,
        NewsSource.FINANCIAL_TIMES, NewsSource.WALL_STREET_JOURNAL,
        NewsSource.BARRONS
    }
    
    # Good sources
    GOOD_SOURCES = {
        NewsSource.CNBC, NewsSource.MARKETWATCH,
        NewsSource.ALPHA_VANTAGE, NewsSource.FINNHUB,
        NewsSource.YAHOO_FINANCE
    }
    
    # Clickbait patterns
    CLICKBAIT_PATTERNS = [
        r'\b(shocking|unbelievable|amazing|incredible|mind.?blowing)\b',
        r'\b(you won.?t believe|what happens next|the truth about)\b',
        r'\b(secret|hidden|exposed|revealed)\b',
        r'[!?]{2,}',  # Multiple exclamation/question marks
        r'\b\d+\s*(things|reasons|signs|ways|facts)\b',
    ]
    
    def __init__(self, config: Optional[QualityConfig] = None):
        self.config = config or QualityConfig()
        self._compile_patterns()
    
    def _compile_patterns(self):
        self.clickbait_regex = [re.compile(p, re.IGNORECASE) for p in self.CLICKBAIT_PATTERNS]
    
    def score(self, article: NewsArticle) -> QualityScore:
        """
        Calculate comprehensive quality score for article.
        
        Returns QualityScore with overall and component scores.
        """
        completeness = self._score_completeness(article)
        structure = self._score_structure(article)
        info_density = self._score_information_density(article)
        writing = self._score_writing_quality(article)
        
        # Weighted overall score
        overall = (
            completeness * 0.30 +
            structure * 0.25 +
            info_density * 0.25 +
            writing * 0.20
        )
        
        return QualityScore(
            overall=round(overall, 3),
            completeness=round(completeness, 3),
            structure=round(structure, 3),
            information_density=round(info_density, 3),
            writing_quality=round(writing, 3),
            details={
                "title_length": len(article.title) if article.title else 0,
                "summary_length": len(article.summary) if article.summary else 0,
                "content_length": len(article.content) if article.content else 0,
                "has_author": bool(article.author),
                "has_published_at": bool(article.published_at),
                "source_tier": self._get_source_tier(article.source),
                "clickbait_detected": self._is_clickbait(article.title or ""),
                "paragraph_count": len((article.content or "").split('\n\n')) if article.content else 0,
                "number_count": len(re.findall(r'\b\d+(?:[.,]\d+)?\b', article.content or "")),
                "dollar_amount_count": len(re.findall(r'\$\d+(?:[.,]\d+)?[BMK]?\b', article.content or "")),
                "percentage_count": len(re.findall(r'\b\d+(?:[.]\d+)?%\b', article.content or "")),
            }
        )
    
    def _score_completeness(self, article: NewsArticle) -> float:
        """Score content completeness (0-1)."""
        score = 0.0
        max_score = 0.0
        
        # Title (required)
        max_score += 1.0
        if article.title and len(article.title) >= self.config.min_title_length:
            score += 1.0
        
        # Summary (required)
        max_score += 1.0
        if article.summary and len(article.summary) >= self.config.min_summary_length:
            score += 1.0
        
        # Content (optional but important)
        max_score += 1.0
        if article.content and len(article.content) >= self.config.min_content_length:
            score += 1.0
        elif article.content:
            score += 0.5
        
        # Author
        if self.config.require_author:
            max_score += 1.0
            if article.author:
                score += 1.0
        
        # Published date
        if self.config.require_published_at:
            max_score += 1.0
            if article.published_at:
                score += 1.0
        
        # Source
        if self.config.require_source:
            max_score += 1.0
            if article.source:
                score += 1.0
        
        return score / max_score if max_score > 0 else 0.0
    
    def _score_structure(self, article: NewsArticle) -> float:
        """Score structural quality (0-1)."""
        scores = []
        
        # Title length
        if article.title:
            title_len = len(article.title)
            if self.config.min_title_length <= title_len <= self.config.max_title_length:
                scores.append(1.0)
            elif title_len < self.config.min_title_length:
                scores.append(0.3)
            else:
                scores.append(0.7)  # Long but not terrible
        
        # Summary length
        if article.summary:
            sum_len = len(article.summary)
            if sum_len >= self.config.min_summary_length:
                scores.append(min(1.0, sum_len / 300))
            else:
                scores.append(0.3)
        
        # Content structure (paragraphs)
        if article.content:
            paragraphs = [p.strip() for p in article.content.split('\n\n') if p.strip()]
            if len(paragraphs) >= 3:
                scores.append(1.0)
            elif len(paragraphs) >= 1:
                scores.append(0.6)
            else:
                scores.append(0.3)
        
        # Source quality bonus
        source_bonus = self._get_source_quality_bonus(article.source)
        scores.append(source_bonus)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _score_information_density(self, article: NewsArticle) -> float:
        """Score information density (0-1)."""
        text = f"{article.title or ''} {article.summary or ''} {article.content or ''}"
        
        if not text.strip():
            return 0.0
        
        scores = []
        
        # Number/financial data presence
        numbers = len(re.findall(r'\b\d+(?:[.,]\d+)?\b', text))
        dollar_amounts = len(re.findall(r'\$\d+(?:[.,]\d+)?[BMK]?\b', text))
        percentages = len(re.findall(r'\b\d+(?:[.]\d+)?%\b', text))
        
        # Normalize: expect at least a few numbers in financial news
        financial_density = min(1.0, (numbers + dollar_amounts * 2 + percentages) / 10)
        scores.append(financial_density)
        
        # Entity mentions (companies, tickers)
        tickers = len(re.findall(r'\$[A-Z]{1,5}\b', text))
        company_suffixes = len(re.findall(r'\b(?:Inc|Corp|Ltd|LLC|Co|Group|Holdings|Technologies|Systems)\.?\b', text))
        entity_density = min(1.0, (tickers + company_suffixes) / 5)
        scores.append(entity_density)
        
        # Quote presence
        has_quotes = bool(re.search(r'["\'][\w\s]{10,}["\']', text))
        scores.append(1.0 if has_quotes else 0.3)
        
        # Specific financial terms
        financial_terms = len(re.findall(
            r'\b(?:earnings|revenue|profit|loss|EPS|guidance|forecast|outlook|dividend|buyback|acquisition|merger|IPO|analyst|rating|target|estimate|beat|miss)\b',
            text, re.IGNORECASE
        ))
        term_density = min(1.0, financial_terms / 8)
        scores.append(term_density)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _score_writing_quality(self, article: NewsArticle) -> float:
        """Score writing quality (0-1)."""
        scores = []
        
        # Check for clickbait
        clickbait = self._is_clickbait(article.title or "")
        scores.append(0.0 if clickbait else 1.0)
        
        # Capitalization consistency
        title = article.title or ""
        if title:
            # Check if title case or sentence case (not all caps, not all lower)
            if title.isupper():
                scores.append(0.3)
            elif title.islower():
                scores.append(0.5)
            else:
                scores.append(1.0)
        
        # Readability (average sentence length)
        content = article.content or ""
        if content:
            sentences = re.split(r'[.!?]+', content)
            sentences = [s.strip() for s in sentences if s.strip()]
            if sentences:
                avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
                # Ideal: 15-25 words per sentence
                if 10 <= avg_len <= 30:
                    scores.append(1.0)
                elif 5 <= avg_len <= 40:
                    scores.append(0.7)
                else:
                    scores.append(0.4)
        
        # No excessive formatting artifacts
        if content:
            artifacts = len(re.findall(r'[\n\r\t]{3,}| {5,}|\t', content))
            scores.append(max(0.3, 1.0 - artifacts * 0.1))
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _is_clickbait(self, title: str) -> bool:
        """Check if title appears to be clickbait."""
        for pattern in self.clickbait_regex:
            if pattern.search(title):
                return True
        return False
    
    def _get_source_tier(self, source: NewsSource) -> str:
        """Get source tier label."""
        if source in self.PREMIUM_SOURCES:
            return "premium"
        elif source in self.GOOD_SOURCES:
            return "good"
        else:
            return "standard"
    
    def _get_source_quality_bonus(self, source: NewsSource) -> float:
        """Get quality bonus based on source tier."""
        if source in self.PREMIUM_SOURCES:
            return 1.0
        elif source in self.GOOD_SOURCES:
            return 0.8
        else:
            return 0.6


def score_quality(article: NewsArticle, config: Optional[QualityConfig] = None) -> QualityScore:
    """Convenience function to score article quality."""
    scorer = QualityScorer(config)
    return scorer.score(article)