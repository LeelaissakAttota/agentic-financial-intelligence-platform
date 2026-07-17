"""
Ticker Resolver for Financial Entity Recognition

Resolves stock tickers to canonical company entities with metadata.
Handles ticker variations, exchange suffixes, and class shares.
"""

import logging
from typing import Optional, Dict, List, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
import re

from data.news.entity_recognition.schemas import (
    Entity, EntityType, EntitySubType
)
from data.news.entity_recognition.dictionary import (
    FinancialDictionary, DictionaryEntry, get_financial_dictionary
)

logger = logging.getLogger(__name__)


@dataclass
class TickerMatch:
    """Result of ticker resolution."""
    ticker: str
    canonical_name: str
    cik: Optional[str] = None
    lei: Optional[str] = None
    isin: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    resolution_type: str = "exact"  # exact, fuzzy, alias, exchange_variant
    
    def to_entity(self, text: str, start_char: int, end_char: int) -> Entity:
        """Convert TickerMatch to Entity."""
        entity = Entity(
            text=text,
            entity_type=EntityType.TICKER,
            sub_type=self.resolution_type == "exact" and EntitySubType.US_EQUITY or None,
            confidence=self.confidence,
            normalized_value=self.canonical_name,
            canonical_name=self.canonical_name,
            ticker=self.ticker,
            cik=self.cik,
            lei=self.lei,
            isin=self.isin,
            start_char=start_char,
            end_char=end_char,
            validation_method="ticker_resolver",
            metadata=self.metadata.copy()
        )
        
        # Add resolution info
        entity.metadata["resolution"] = {
            "ticker": self.ticker,
            "canonical_name": self.canonical_name,
            "cik": self.cik,
            "lei": self.lei,
            "isin": self.isin,
            "exchange": self.exchange,
            "sector": self.sector,
            "industry": self.industry,
            "country": self.country,
            "confidence": self.confidence,
            "resolution_type": self.resolution_type,
            "metadata": self.metadata
        }
        
        return entity


class TickerResolver:
    """
    Resolves stock tickers to canonical company entities.
    
    Handles:
    - Exact ticker matches (AAPL -> Apple Inc.)
    - Class shares (BRK.A, BRK.B -> Berkshire Hathaway)
    - Exchange variants (AAPL.US, AAPL.O -> AAPL)
    - Fuzzy matching for OCR errors
    - Historical tickers
    - International ticker formats
    """
    
    # Common exchange suffixes
    EXCHANGE_SUFFIXES = {
        'US': ['US', 'O', 'N', 'A', 'B', 'P', 'Q', 'Z'],
        'CA': ['TO', 'V', 'CN'],
        'UK': ['L', 'LN'],
        'DE': ['DE', 'F', 'G'],
        'JP': ['T', 'JP', 'TKS'],
        'HK': ['HK', 'HKG'],
        'CN': ['SS', 'SZ', 'SH', 'SHE'],
        'AU': ['AX', 'AU'],
        'SG': ['SI', 'SG'],
        'IN': ['BO', 'NS', 'BSE', 'NSE'],
        'KR': ['KS', 'KQ', 'KR'],
    }
    
    # Ticker normalization patterns
    TICKER_PATTERN = re.compile(r'^[A-Z]{1,5}(\.[A-Z])?$')
    EXCHANGE_TICKER_PATTERN = re.compile(r'^[A-Z]{1,5}\.[A-Z]{1,3}$')
    
    def __init__(self, dictionary: Optional[FinancialDictionary] = None):
        self.dictionary = dictionary or get_financial_dictionary()
        self.dictionary.initialize()
        
        # Build additional indexes
        self._ticker_to_company: Dict[str, DictionaryEntry] = {}
        self._company_to_tickers: Dict[str, Set[str]] = {}
        self._isin_to_company: Dict[str, DictionaryEntry] = {}
        self._cik_to_company: Dict[str, DictionaryEntry] = {}
        self._lei_to_company: Dict[str, DictionaryEntry] = {}
        
        self._build_indexes()
        
    def _build_indexes(self) -> None:
        """Build lookup indexes from dictionary."""
        for entry in self.dictionary.get_all_companies():
            if entry.ticker:
                self._ticker_to_company[entry.ticker.upper()] = entry
                self._company_to_tickers.setdefault(entry.canonical_name.lower(), set()).add(entry.ticker.upper())
                
            if entry.isin:
                self._isin_to_company[entry.isin] = entry
            if entry.cik:
                self._cik_to_company[entry.cik] = entry
            if entry.lei:
                self._lei_to_company[entry.lei] = entry
                
        # Also add direct ticker entries
        for entry in self.dictionary.get_all_tickers():
            ticker = entry.canonical_name.upper()
            if ticker not in self._ticker_to_company:
                self._ticker_to_company[ticker] = entry
                
        logger.info(f"Built ticker indexes: {len(self._ticker_to_company)} tickers, {len(self._company_to_tickers)} companies")
        
    def resolve(self, ticker: str) -> Optional[TickerMatch]:
        """
        Resolve a ticker to canonical company entity.
        
        Args:
            ticker: Input ticker string (e.g., "AAPL", "BRK.A", "AAPL.US")
            
        Returns:
            TickerMatch with resolved entity or None if not found
        """
        if not ticker:
            return None
            
        original_ticker = ticker
        ticker = ticker.strip().upper()
        
        # Try exact match first
        match = self._exact_match(ticker)
        if match:
            return match
            
        # Try exchange variant (AAPL.US -> AAPL)
        match = self._exchange_variant_match(ticker)
        if match:
            return match
            
        # Try class shares (BRK.A -> BRK.A)
        match = self._class_share_match(ticker)
        if match:
            return match
            
        # Try fuzzy match for OCR errors
        match = self._fuzzy_match(ticker)
        if match:
            return match
            
        # Try alias match (company name -> ticker)
        match = self._alias_match(ticker)
        if match:
            return match
            
        logger.debug(f"Could not resolve ticker: {original_ticker}")
        return None
        
    def _exact_match(self, ticker: str) -> Optional[TickerMatch]:
        """Try exact ticker match."""
        entry = self._ticker_to_company.get(ticker)
        if entry:
            return TickerMatch(
                ticker=ticker,
                canonical_name=entry.canonical_name,
                cik=entry.cik,
                lei=entry.lei,
                isin=entry.isin,
                exchange=entry.exchange,
                sector=entry.sector,
                industry=entry.industry,
                country=entry.country,
                confidence=0.98,
                resolution_type="exact",
                metadata=entry.metadata.copy()
            )
        return None
        
    def _exchange_variant_match(self, ticker: str) -> Optional[TickerMatch]:
        """Match ticker with exchange suffix (e.g., AAPL.US)."""
        if not self.EXCHANGE_TICKER_PATTERN.match(ticker):
            return None
            
        base_ticker = ticker.split('.')[0]
        entry = self._ticker_to_company.get(base_ticker)
        if entry:
            return TickerMatch(
                ticker=ticker,
                canonical_name=entry.canonical_name,
                cik=entry.cik,
                lei=entry.lei,
                isin=entry.isin,
                exchange=entry.exchange,
                sector=entry.sector,
                industry=entry.industry,
                country=entry.country,
                confidence=0.95,
                resolution_type="exchange_variant",
                metadata={**entry.metadata, "original_ticker": ticker, "base_ticker": base_ticker}
            )
        return None
        
    def _class_share_match(self, ticker: str) -> Optional[TickerMatch]:
        """Match class shares (BRK.A, BRK.B)."""
        # Already handled by exact match if in dictionary
        # This handles cases like BRK.A where base is BRK
        if '.' in ticker:
            base, class_suffix = ticker.split('.', 1)
            if len(class_suffix) == 1 and class_suffix.isalpha():
                # Check if base ticker exists
                entry = self._ticker_to_company.get(base)
                if entry:
                    return TickerMatch(
                        ticker=ticker,
                        canonical_name=entry.canonical_name,
                        cik=entry.cik,
                        lei=entry.lei,
                        isin=entry.isin,
                        exchange=entry.exchange,
                        sector=entry.sector,
                        industry=entry.industry,
                        country=entry.country,
                        confidence=0.95,
                        resolution_type="class_share",
                        metadata={**entry.metadata, "class": class_suffix, "base_ticker": base}
                    )
        return None
        
    def _fuzzy_match(self, ticker: str) -> Optional[TickerMatch]:
        """Fuzzy match for OCR errors (e.g., AAP1 -> AAPL)."""
        if len(ticker) < 2 or len(ticker) > 5:
            return None
            
        # Find tickers with edit distance 1
        best_match = None
        best_distance = 2
        
        for known_ticker in self._ticker_to_company.keys():
            if abs(len(known_ticker) - len(ticker)) > 1:
                continue
                
            distance = self._levenshtein_distance(ticker, known_ticker)
            if distance < best_distance:
                best_distance = distance
                best_match = known_ticker
                
        if best_match and best_distance == 1:
            entry = self._ticker_to_company[best_match]
            return TickerMatch(
                ticker=ticker,
                canonical_name=entry.canonical_name,
                cik=entry.cik,
                lei=entry.lei,
                isin=entry.isin,
                exchange=entry.exchange,
                sector=entry.sector,
                industry=entry.industry,
                country=entry.country,
                confidence=0.7,  # Lower confidence for fuzzy match
                resolution_type="fuzzy",
                metadata={**entry.metadata, "fuzzy_match": True, "matched_ticker": best_match, "distance": best_distance}
            )
        return None
        
    def _alias_match(self, text: str) -> Optional[TickerMatch]:
        """Match company name or alias to ticker."""
        entry = self.dictionary.lookup_company(text)
        if entry and entry.ticker:
            return TickerMatch(
                ticker=entry.ticker,
                canonical_name=entry.canonical_name,
                cik=entry.cik,
                lei=entry.lei,
                isin=entry.isin,
                exchange=entry.exchange,
                sector=entry.sector,
                industry=entry.industry,
                country=entry.country,
                confidence=0.9,
                resolution_type="alias",
                metadata={**entry.metadata, "matched_alias": text}
            )
        return None
        
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
            
        if len(s2) == 0:
            return len(s1)
            
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
            
        return previous_row[-1]
        
    def resolve_batch(self, tickers: List[str]) -> List[Optional[TickerMatch]]:
        """Resolve multiple tickers."""
        return [self.resolve(t) for t in tickers]
        
    def get_all_tickers_for_company(self, company_name: str) -> List[str]:
        """Get all tickers for a company (including class shares)."""
        tickers = self._company_to_tickers.get(company_name.lower(), set())
        return list(tickers)
        
    def resolve_by_isin(self, isin: str) -> Optional[TickerMatch]:
        """Resolve by ISIN."""
        entry = self._isin_to_company.get(isin)
        if entry and entry.ticker:
            return TickerMatch(
                ticker=entry.ticker,
                canonical_name=entry.canonical_name,
                cik=entry.cik,
                lei=entry.lei,
                isin=entry.isin,
                exchange=entry.exchange,
                sector=entry.sector,
                industry=entry.industry,
                country=entry.country,
                confidence=0.99,
                resolution_type="isin",
                metadata=entry.metadata.copy()
            )
        return None
        
    def resolve_by_cik(self, cik: str) -> Optional[TickerMatch]:
        """Resolve by CIK."""
        entry = self._cik_to_company.get(cik.zfill(10))
        if entry and entry.ticker:
            return TickerMatch(
                ticker=entry.ticker,
                canonical_name=entry.canonical_name,
                cik=entry.cik,
                lei=entry.lei,
                isin=entry.isin,
                exchange=entry.exchange,
                sector=entry.sector,
                industry=entry.industry,
                country=entry.country,
                confidence=0.99,
                resolution_type="cik",
                metadata=entry.metadata.copy()
            )
        return None
        
    def resolve_by_lei(self, lei: str) -> Optional[TickerMatch]:
        """Resolve by LEI."""
        entry = self._lei_to_company.get(lei)
        if entry and entry.ticker:
            return TickerMatch(
                ticker=entry.ticker,
                canonical_name=entry.canonical_name,
                cik=entry.cik,
                lei=entry.lei,
                isin=entry.isin,
                exchange=entry.exchange,
                sector=entry.sector,
                industry=entry.industry,
                country=entry.country,
                confidence=0.99,
                resolution_type="lei",
                metadata=entry.metadata.copy()
            )
        return None
        
    def create_entity_from_ticker(self, ticker: str, text: str, 
                                   start_char: int, end_char: int) -> Optional[Entity]:
        """Create an Entity from a ticker string."""
        match = self.resolve(ticker)
        if not match:
            return None
            
        entity = Entity(
            text=text,
            entity_type=EntityType.TICKER,
            sub_type=match.resolution_type == "exact" and EntitySubType.US_EQUITY or None,
            confidence=match.confidence,
            normalized_value=match.canonical_name,
            canonical_name=match.canonical_name,
            ticker=match.ticker,
            cik=match.cik,
            lei=match.lei,
            isin=match.isin,
            start_char=start_char,
            end_char=end_char,
            validation_method="ticker_resolver",
            metadata=match.metadata
        )
        
        # Add resolution info
        entity.metadata["resolution"] = {
            "ticker": match.ticker,
            "canonical_name": match.canonical_name,
            "cik": match.cik,
            "lei": match.lei,
            "isin": match.isin,
            "exchange": match.exchange,
            "sector": match.sector,
            "industry": match.industry,
            "country": match.country,
            "confidence": match.confidence,
            "resolution_type": match.resolution_type,
            "metadata": match.metadata
        }
        
        return entity


# Singleton instance
_ticker_resolver: Optional[TickerResolver] = None


def get_ticker_resolver(dictionary: Optional[FinancialDictionary] = None) -> TickerResolver:
    """Get or create the default ticker resolver."""
    global _ticker_resolver
    if _ticker_resolver is None:
        _ticker_resolver = TickerResolver(dictionary)
    return _ticker_resolver