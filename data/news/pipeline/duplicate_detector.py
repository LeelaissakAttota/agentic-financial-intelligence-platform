"""
Duplicate Article Detector for News Pipeline

Detects and marks duplicate articles using multiple strategies:
- Exact content hash matching
- Title similarity (fuzzy matching)
- URL canonicalization
- Content fingerprinting
"""

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse, parse_qs, urlunparse

import difflib

from data.news.schemas import NewsArticle

logger = logging.getLogger(__name__)


@dataclass
class DuplicateResult:
    """Result of duplicate detection."""
    is_duplicate: bool
    original_hash: Optional[str] = None
    similarity: float = 0.0
    reason: str = ""


class DuplicateDetector:
    """
    Detects duplicate news articles using multiple strategies.

    Strategies (in order):
    1. Exact content hash match
    2. Title fuzzy matching (80%+ similarity)
    3. URL canonicalization match
    4. Content fingerprint match (60%+ similarity)
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.title_similarity_threshold = self.config.get('title_similarity_threshold', 0.80)
        self.content_fingerprint_threshold = self.config.get('content_fingerprint_threshold', 0.50)
        self.max_title_length = self.config.get('max_title_length', 200)

        # Tracking sets
        self._seen_hashes: Set[str] = set()
        self._seen_titles: List[str] = []
        self._seen_urls: Set[str] = set()
        self._seen_fingerprints: Dict[str, str] = {}  # fingerprint -> hash
    
    def reset(self) -> None:
        """Reset all tracking state."""
        self._seen_hashes.clear()
        self._seen_titles.clear()
        self._seen_urls.clear()
        self._seen_fingerprints.clear()
    
    def check(self, article: NewsArticle) -> DuplicateResult:
        """
        Check if article is a duplicate.
        
        Returns DuplicateResult with details.
        """
        # 1. Exact content hash
        if article.content_hash and article.content_hash in self._seen_hashes:
            return DuplicateResult(
                is_duplicate=True,
                original_hash=article.content_hash,
                similarity=1.0,
                reason="exact_content_hash"
            )
        
        # 2. URL canonicalization
        canonical_url = self._canonicalize_url(article.url)
        if canonical_url in self._seen_urls:
            return DuplicateResult(
                is_duplicate=True,
                original_hash=article.content_hash,
                similarity=1.0,
                reason="canonical_url"
            )
        
        # 3. Title fuzzy matching
        title_result = self._check_title_similarity(article.title)
        if title_result.is_duplicate:
            return title_result
        
        # 4. Content fingerprint (similarity-based)
        fingerprint_text = self._generate_fingerprint_text(article)
        fingerprint_result = self._check_fingerprint_similarity(fingerprint_text)
        if fingerprint_result.is_duplicate:
            return fingerprint_result
        
        # Generate hash for storage
        fingerprint_hash = hashlib.sha256(fingerprint_text.encode()).hexdigest()[:16]
        
        # Not a duplicate - register it
        self._register(article, canonical_url, fingerprint_text)
        
        return DuplicateResult(is_duplicate=False)
    
    def _check_title_similarity(self, title: str) -> DuplicateResult:
        """Check title against seen titles using fuzzy matching."""
        if not title or not self._seen_titles:
            return DuplicateResult(is_duplicate=False)
        
        # Clean title for comparison
        clean_title = self._clean_title(title)
        
        for seen_title in self._seen_titles:
            similarity = self._title_similarity(clean_title, seen_title)
            if similarity >= self.title_similarity_threshold:
                return DuplicateResult(
                    is_duplicate=True,
                    original_hash=None,
                    similarity=similarity,
                    reason="title_similarity"
                )
        
        return DuplicateResult(is_duplicate=False)
    
    def _clean_title(self, title: str) -> str:
        """Clean title for comparison."""
        # Remove common prefixes/suffixes
        title = re.sub(r'^\[.*?\]\s*', '', title)  # [Category] prefix
        title = re.sub(r'\s*[-|:]\s*[A-Z][a-z]+(?:\s[A-Z][a-z]+)*$', '', title)  # Source suffix
        title = re.sub(r'\s+', ' ', title).strip().lower()
        return title[:self.max_title_length]
    
    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate title similarity using difflib."""
        return difflib.SequenceMatcher(None, title1, title2).ratio()
    
    def _canonicalize_url(self, url: str) -> str:
        """
        Canonicalize URL for comparison.
        
        Removes tracking parameters, normalizes domain, etc.
        """
        try:
            parsed = urlparse(url)
            
            # Normalize domain (remove www)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Remove tracking query parameters
            tracking_params = {
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'fbclid', 'gclid', 'ref', 'source', 'campaign', 'medium',
                'share', 'platform', 'app', 'device', 'ref_src', 'ref_url'
            }
            
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            filtered_params = {
                k: v for k, v in query_params.items()
                if k.lower() not in tracking_params
            }
            
            # Reconstruct query string
            new_query = '&'.join(
                f"{k}={'&'.join(v) if len(v) > 1 else v[0]}"
                for k, v in sorted(filtered_params.items())
            )
            
            # Rebuild URL without fragment
            canonical = urlunparse((
                parsed.scheme.lower(),
                domain,
                parsed.path.rstrip('/'),
                parsed.params,
                new_query,
                ''  # Remove fragment
            ))
            
            return canonical
            
        except Exception as e:
            logger.debug(f"URL canonicalization failed: {e}")
            return url
    
    def _generate_fingerprint(self, article: NewsArticle) -> str:
        """
        Generate content fingerprint for near-duplicate detection.
        
        Uses summary + content (excluding title for content-focused comparison).
        """
        parts = []
        # Skip title - focus on content
        if article.summary:
            parts.append(article.summary[:300])
        if article.content:
            parts.append(article.content[:500])
        
        combined = ' '.join(parts).lower()
        # Remove non-alphanumeric
        combined = re.sub(r'[^a-z0-9\s]', '', combined)
        # Normalize whitespace
        combined = re.sub(r'\s+', ' ', combined).strip()
        
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    def _generate_fingerprint_text(self, article: NewsArticle) -> str:
        """Generate raw text for fingerprint similarity comparison.
        
        Uses summary + content (excluding title for content-focused comparison).
        Title similarity is checked separately.
        """
        parts = []
        if article.summary:
            parts.append(article.summary[:300])
        if article.content:
            parts.append(article.content[:500])
        
        combined = ' '.join(parts).lower()
        # Remove non-alphanumeric
        combined = re.sub(r'[^a-z0-9\s]', '', combined)
        # Normalize whitespace
        combined = re.sub(r'\s+', ' ', combined).strip()
        
        return combined
    
    def _check_fingerprint_similarity(self, fingerprint_text: str) -> DuplicateResult:
        """Check fingerprint against seen fingerprints using similarity."""
        if not fingerprint_text or not self._seen_fingerprints:
            return DuplicateResult(is_duplicate=False)
        
        # Skip fingerprint check for very short content (likely just generic summaries)
        if len(fingerprint_text) < 10:
            return DuplicateResult(is_duplicate=False)
        
        for seen_text, seen_hash in self._seen_fingerprints.items():
            similarity = difflib.SequenceMatcher(None, fingerprint_text, seen_text).ratio()
            if similarity >= self.content_fingerprint_threshold:
                return DuplicateResult(
                    is_duplicate=True,
                    original_hash=seen_hash,
                    similarity=similarity,
                    reason="content_fingerprint"
                )
        
        return DuplicateResult(is_duplicate=False)
    
    def _register(
        self,
        article: NewsArticle,
        canonical_url: str,
        fingerprint_text: str
    ) -> None:
        """Register article as seen."""
        if article.content_hash:
            self._seen_hashes.add(article.content_hash)
        
        self._seen_titles.append(self._clean_title(article.title))
        # Keep only recent titles to prevent memory growth
        if len(self._seen_titles) > 1000:
            self._seen_titles = self._seen_titles[-500:]
        
        self._seen_urls.add(canonical_url)
        
        if fingerprint_text:
            fingerprint_hash = hashlib.sha256(fingerprint_text.encode()).hexdigest()[:16]
            self._seen_fingerprints[fingerprint_text] = fingerprint_hash
    
    def get_stats(self) -> dict:
        """Get detector statistics."""
        return {
            "seen_hashes": len(self._seen_hashes),
            "seen_titles": len(self._seen_titles),
            "seen_urls": len(self._seen_urls),
            "seen_fingerprints": len(self._seen_fingerprints)
        }


def deduplicate_articles(articles: List[NewsArticle], config: Optional[dict] = None) -> List[NewsArticle]:
    """
    Remove duplicates from a list of articles.
    
    Returns list with is_duplicate flag set and duplicate_of populated.
    """
    detector = DuplicateDetector(config)
    unique = []
    
    for article in articles:
        # Generate fingerprint text for this article
        fingerprint_text = detector._generate_fingerprint_text(article)
        result = detector.check(article)
        if result.is_duplicate:
            article.is_duplicate = True
            article.duplicate_of = result.original_hash
            article.metadata = article.metadata or {}
            article.metadata['duplicate_reason'] = result.reason
            article.metadata['duplicate_similarity'] = result.similarity
        else:
            unique.append(article)
    
    logger.info(f"Deduplication: {len(articles)} -> {len(unique)} articles ({len(articles) - len(unique)} duplicates removed)")
    return unique