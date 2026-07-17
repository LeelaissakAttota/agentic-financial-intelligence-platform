"""
Company Resolver for Financial Entity Recognition

Resolves company mentions to canonical entities with full metadata.
Handles aliases, subsidiaries, and corporate hierarchy.
"""

import logging
from typing import Optional, Dict, List, Any, Set, Tuple
from dataclasses import dataclass, field
import re
from difflib import SequenceMatcher

from data.news.entity_recognition.schemas import (
    Entity, EntityType, EntitySubType, CompanyResolution
)
from data.news.entity_recognition.dictionary import (
    FinancialDictionary, DictionaryEntry, get_financial_dictionary
)
from data.news.entity_recognition.ticker_resolver import get_ticker_resolver

logger = logging.getLogger(__name__)


@dataclass
class CompanyMatch:
    """Result of company resolution."""
    canonical_name: str
    ticker: Optional[str] = None
    cik: Optional[str] = None
    lei: Optional[str] = None
    isin: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    confidence: float = 0.0
    match_type: str = "exact"  # exact, alias, fuzzy, partial, subsidiary
    metadata: Dict[str, Any] = field(default_factory=dict)
    matched_text: str = ""
    
    def to_resolution(self) -> CompanyResolution:
        """Convert to CompanyResolution schema."""
        return CompanyResolution(
            canonical_name=self.canonical_name,
            ticker=self.ticker,
            cik=self.cik,
            lei=self.lei,
            isin=self.isin,
            exchange=self.exchange,
            sector=self.sector,
            industry=self.industry,
            country=self.country,
            confidence=self.confidence,
            match_type=self.match_type,
            metadata=self.metadata,
            matched_text=self.matched_text,
        )


class CompanyResolver:
    """
    Resolves company mentions to canonical entities.
    
    Handles:
    - Exact name matches (Apple Inc. -> Apple Inc.)
    - Common aliases (Apple -> Apple Inc., Google -> Alphabet Inc.)
    - Partial matches (Microsoft -> Microsoft Corporation)
    - Subsidiary resolution (YouTube -> Alphabet Inc.)
    - Fuzzy matching for typos/OCR errors
    - Former names (Facebook -> Meta Platforms Inc.)
    """
    
    # Common corporate suffixes to normalize
    CORPORATE_SUFFIXES = [
        'inc', 'incorporated', 'corp', 'corporation', 'company', 'co',
        'ltd', 'limited', 'plc', 'llc', 'llp', 'lp', 'gp',
        'gmbh', 'ag', 'sa', 'nv', 'bv', 'se', 'spa', 'srl',
        'holdings', 'holding', 'group', 'gr', 'intl', 'international',
        'technologies', 'technology', 'tech', 'systems', 'solutions',
        'services', 'svcs', 'enterprises', 'enterprise', 'ventures',
        'capital', 'partners', 'partner', 'associates', 'assoc',
    ]
    
    # Known subsidiary relationships
    SUBSIDIARIES = {
        "youtube": "Alphabet Inc.",
        "google": "Alphabet Inc.",
        "waymo": "Alphabet Inc.",
        "deepmind": "Alphabet Inc.",
        "android": "Alphabet Inc.",
        "chrome": "Alphabet Inc.",
        "gmail": "Alphabet Inc.",
        "google cloud": "Alphabet Inc.",
        "google ads": "Alphabet Inc.",
        "google play": "Alphabet Inc.",
        "instagram": "Meta Platforms Inc.",
        "whatsapp": "Meta Platforms Inc.",
        "oculus": "Meta Platforms Inc.",
        "reality labs": "Meta Platforms Inc.",
        "facebook": "Meta Platforms Inc.",
        "threads": "Meta Platforms Inc.",
        "aws": "Amazon.com Inc.",
        "amazon web services": "Amazon.com Inc.",
        "prime video": "Amazon.com Inc.",
        "alexa": "Amazon.com Inc.",
        "kindle": "Amazon.com Inc.",
        "audible": "Amazon.com Inc.",
        "zappos": "Amazon.com Inc.",
        "whole foods": "Amazon.com Inc.",
        "ring": "Amazon.com Inc.",
        "blink": "Amazon.com Inc.",
        "pillpack": "Amazon.com Inc.",
        "xbox": "Microsoft Corporation",
        "azure": "Microsoft Corporation",
        "office": "Microsoft Corporation",
        "windows": "Microsoft Corporation",
        "linkedin": "Microsoft Corporation",
        "github": "Microsoft Corporation",
        "activision blizzard": "Microsoft Corporation",
        "bethesda": "Microsoft Corporation",
        "minecraft": "Microsoft Corporation",
        "iphone": "Apple Inc.",
        "ipad": "Apple Inc.",
        "mac": "Apple Inc.",
        "apple watch": "Apple Inc.",
        "airpods": "Apple Inc.",
        "apple tv": "Apple Inc.",
        "apple music": "Apple Inc.",
        "icloud": "Apple Inc.",
        "app store": "Apple Inc.",
        "tesla": "Tesla Inc.",
        "spacex": "SpaceX",  # Private
        "starlink": "SpaceX",
        "neuralink": "Neuralink",  # Private
        "the boring company": "The Boring Company",  # Private
    }
    
    # Former names
    FORMER_NAMES = {
        "facebook": "Meta Platforms Inc.",
        "google": "Alphabet Inc.",
        "alphabet": "Alphabet Inc.",
        "daimler": "Mercedes-Benz Group AG",
        "fiat chrysler": "Stellantis N.V.",
        "fca": "Stellantis N.V.",
        "psa": "Stellantis N.V.",
        "kroger": "The Kroger Co.",
        "kraft heinz": "The Kraft Heinz Company",
        "dowdupont": "Dow Inc. / DuPont de Nemours",
        "united technologies": "RTX Corporation",
        "utc": "RTX Corporation",
        "raytheon": "RTX Corporation",
        "l3harris": "L3Harris Technologies Inc.",
        "northrop grumman": "Northrop Grumman Corporation",
        "lockheed martin": "Lockheed Martin Corporation",
        "boeing": "The Boeing Company",
    }
    
    def __init__(self, dictionary: Optional[FinancialDictionary] = None):
        self.dictionary = dictionary or get_financial_dictionary()
        self.dictionary.initialize()
        self.ticker_resolver = get_ticker_resolver(self.dictionary)
        
        # Build lookup indexes
        self._name_to_entry: Dict[str, DictionaryEntry] = {}
        self._alias_to_entry: Dict[str, DictionaryEntry] = {}
        self._normalized_to_entry: Dict[str, DictionaryEntry] = {}
        
        self._build_indexes()
        
    def _build_indexes(self) -> None:
        """Build lookup indexes from dictionary."""
        for entry in self.dictionary.get_all_companies():
            # Canonical name
            self._name_to_entry[entry.canonical_name.lower()] = entry
            
            # Normalized name (without suffixes)
            normalized = self._normalize_company_name(entry.canonical_name)
            self._normalized_to_entry[normalized] = entry
            
            # Aliases
            for alias in entry.aliases:
                self._alias_to_entry[alias.lower()] = entry
                self._alias_to_entry[self._normalize_company_name(alias)] = entry
                
        # Add subsidiary mappings
        for sub, parent in self.SUBSIDIARIES.items():
            parent_entry = self.dictionary.lookup_company(parent)
            if parent_entry:
                self._alias_to_entry[sub.lower()] = parent_entry
                
        # Add former names
        for former, current in self.FORMER_NAMES.items():
            current_entry = self.dictionary.lookup_company(current)
            if current_entry:
                self._alias_to_entry[former.lower()] = current_entry
                
        logger.info(f"Built company indexes: {len(self._name_to_entry)} names, {len(self._alias_to_entry)} aliases")
        
    def _normalize_company_name(self, name: str) -> str:
        """Normalize company name by removing suffixes and special chars."""
        if not name:
            return ""
            
        name = name.lower().strip()
        
        # Remove common punctuation
        name = re.sub(r'[.,&\'`]', '', name)
        name = name.replace('-', ' ')
        
        # Remove corporate suffixes
        words = name.split()
        filtered = []
        for word in words:
            if word not in self.CORPORATE_SUFFIXES:
                filtered.append(word)
                
        return ' '.join(filtered).strip()
        
    def resolve(self, text: str) -> Optional[CompanyMatch]:
        """
        Resolve a company mention to canonical entity.
        
        Args:
            text: Company name or mention
            
        Returns:
            CompanyMatch with resolved entity or None
        """
        if not text:
            return None
            
        original_text = text
        text = text.strip()
        text_lower = text.lower()
        
        # Try exact canonical match
        entry = self._name_to_entry.get(text_lower)
        if entry:
            return self._create_match(entry, text, "exact", 0.98)
            
        # Try exact alias match
        entry = self._alias_to_entry.get(text_lower)
        if entry:
            return self._create_match(entry, text, "alias", 0.95)
            
        # Try normalized match
        normalized = self._normalize_company_name(text)
        entry = self._normalized_to_entry.get(normalized)
        if entry:
            return self._create_match(entry, text, "normalized", 0.9)
            
        # Try partial match (company name contained in text or vice versa)
        entry = self._partial_match(text_lower)
        if entry:
            return self._create_match(entry, text, "partial", 0.8)
            
        # Try fuzzy match
        entry = self._fuzzy_match(text_lower)
        if entry:
            return self._create_match(entry, text, "fuzzy", 0.7)
            
        # Try ticker resolution
        ticker_match = self.ticker_resolver.resolve(text)
        if ticker_match and ticker_match.canonical_name:
            entry = self.dictionary.lookup_company(ticker_match.canonical_name)
            if entry:
                return self._create_match(entry, text, "ticker", ticker_match.confidence)
                
        logger.debug(f"Could not resolve company: {original_text}")
        return None
        
    def _create_match(
        self, 
        entry: DictionaryEntry, 
        matched_text: str, 
        match_type: str, 
        confidence: float
    ) -> CompanyMatch:
        """Create a CompanyMatch from a dictionary entry."""
        return CompanyMatch(
            canonical_name=entry.canonical_name,
            ticker=entry.ticker,
            cik=entry.cik,
            lei=entry.lei,
            isin=entry.isin,
            exchange=entry.exchange,
            sector=entry.sector,
            industry=entry.industry,
            country=entry.country,
            confidence=confidence,
            match_type=match_type,
            metadata=entry.metadata.copy(),
            matched_text=matched_text,
        )
        
    def _partial_match(self, text: str) -> Optional[DictionaryEntry]:
        """Try partial matching - text contains company name or vice versa."""
        # Check if any known name is contained in text
        for name, entry in self._name_to_entry.items():
            if name in text or text in name:
                # Require reasonable overlap
                if len(name) >= 4 and len(text) >= 4:
                    ratio = SequenceMatcher(None, name, text).ratio()
                    if ratio > 0.6:
                        return entry
                        
        # Check aliases
        for alias, entry in self._alias_to_entry.items():
            if alias in text or text in alias:
                if len(alias) >= 4 and len(text) >= 4:
                    ratio = SequenceMatcher(None, alias, text).ratio()
                    if ratio > 0.6:
                        return entry
                        
        return None
        
    def _fuzzy_match(self, text: str) -> Optional[DictionaryEntry]:
        """Fuzzy match using sequence similarity."""
        best_match = None
        best_ratio = 0.0
        
        # Search canonical names
        for name, entry in self._name_to_entry.items():
            if abs(len(name) - len(text)) > 5:
                continue
            ratio = SequenceMatcher(None, name, text).ratio()
            if ratio > best_ratio and ratio > 0.8:
                best_ratio = ratio
                best_match = entry
                
        # Search aliases
        for alias, entry in self._alias_to_entry.items():
            if abs(len(alias) - len(text)) > 5:
                continue
            ratio = SequenceMatcher(None, alias, text).ratio()
            if ratio > best_ratio and ratio > 0.8:
                best_ratio = ratio
                best_match = entry
                
        return best_match
        
    def resolve_batch(self, texts: List[str]) -> List[Optional[CompanyMatch]]:
        """Resolve multiple company mentions."""
        return [self.resolve(t) for t in texts]
        
    def create_entity_from_company(
        self, 
        text: str, 
        start_char: int, 
        end_char: int,
        match: Optional[CompanyMatch] = None
    ) -> Entity:
        """Create an Entity from a company mention."""
        if match is None:
            match = self.resolve(text)
            
        if match:
            entity = Entity(
                text=text,
                entity_type=EntityType.COMPANY,
                sub_type=EntitySubType.PUBLIC_COMPANY if match.ticker else EntitySubType.PRIVATE_COMPANY,
                confidence=match.confidence,
                normalized_value=match.canonical_name,
                canonical_name=match.canonical_name,
                ticker=match.ticker,
                cik=match.cik,
                lei=match.lei,
                isin=match.isin,
                start_char=start_char,
                end_char=end_char,
                validation_method="company_resolver",
                metadata=match.metadata
            )
            entity.metadata["resolution"] = {
            "canonical_name": match.canonical_name,
            "ticker": match.ticker,
            "cik": match.cik,
            "lei": match.lei,
            "isin": match.isin,
            "exchange": match.exchange,
            "sector": match.sector,
            "industry": match.industry,
            "country": match.country,
            "confidence": match.confidence,
            "match_type": match.match_type,
            "metadata": match.metadata,
            "matched_text": match.matched_text
        }
            entity.metadata["match_type"] = match.match_type
        else:
            # No resolution found
            entity = Entity(
                text=text,
                entity_type=EntityType.COMPANY,
                confidence=0.5,
                normalized_value=text,
                start_char=start_char,
                end_char=end_char,
                validation_method="company_resolver",
                metadata={"unresolved": True}
            )
            
        return entity
        
    def get_company_hierarchy(self, canonical_name: str) -> Dict[str, Any]:
        """Get company hierarchy info (parent, subsidiaries)."""
        entry = self.dictionary.lookup_company(canonical_name)
        if not entry:
            return {}
            
        # Find subsidiaries
        subsidiaries = []
        for sub, parent in self.SUBSIDIARIES.items():
            if parent == canonical_name:
                subsidiaries.append(sub)
                
        return {
            "canonical_name": canonical_name,
            "ticker": entry.ticker,
            "subsidiaries": subsidiaries,
            "sector": entry.sector,
            "industry": entry.industry,
            "country": entry.country,
            "exchange": entry.exchange,
        }


# Singleton instance
_company_resolver: Optional[CompanyResolver] = None


def get_company_resolver(dictionary: Optional[FinancialDictionary] = None) -> CompanyResolver:
    """Get or create the default company resolver."""
    global _company_resolver
    if _company_resolver is None:
        _company_resolver = CompanyResolver(dictionary)
    return _company_resolver