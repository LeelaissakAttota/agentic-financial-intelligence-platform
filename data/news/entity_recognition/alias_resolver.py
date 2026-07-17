"""
Alias Resolver for Financial Entity Recognition

Resolves entity aliases and alternate names to canonical forms.
Handles company aliases, ticker aliases, person name variations, etc.
"""

import logging
import re
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from data.news.entity_recognition.schemas import (
    Entity, EntityType, EntitySubType, AliasResolution
)
from data.news.entity_recognition.dictionary import (
    FinancialDictionary, DictionaryEntry, get_financial_dictionary
)

logger = logging.getLogger(__name__)


@dataclass
class AliasMatch:
    """Result of alias resolution."""
    alias: str
    canonical_name: str
    entity_type: EntityType
    sub_type: Optional[EntitySubType] = None
    confidence: float = 0.0
    match_type: str = "exact"  # exact, fuzzy, pattern, learned
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_resolution(self) -> AliasResolution:
        """Convert to AliasResolution schema."""
        return AliasResolution(
            alias=self.alias,
            canonical_name=self.canonical_name,
            entity_type=self.entity_type,
            sub_type=self.sub_type,
            confidence=self.confidence,
            match_type=self.match_type,
            metadata=self.metadata,
        )


class AliasResolver:
    """
    Resolves entity aliases to canonical forms.
    
    Handles:
    - Company aliases (Apple -> Apple Inc., GOOGL -> Alphabet Inc.)
    - Ticker aliases (AAPL.US -> AAPL, BRK.B -> BRK.B)
    - Person name variations (Tim Cook -> Timothy Cook)
    - Exchange aliases (NYSE -> New York Stock Exchange)
    - Index aliases (S&P 500 -> SP500 -> SPX)
    - Crypto aliases (BTC -> Bitcoin, ETH -> Ethereum)
    - Currency aliases (USD -> US Dollar, $ -> USD)
    """
    
    # Common abbreviation patterns
    ABBREVIATION_PATTERNS = {
        "corporation": ["corp", "corpn"],
        "incorporated": ["inc", "incorp"],
        "company": ["co", "coy"],
        "limited": ["ltd", "ltd."],
        "international": ["intl", "int'l"],
        "technologies": ["tech", "techs"],
        "technology": ["tech"],
        "solutions": ["sol", "slns"],
        "systems": ["sys", "syss"],
        "services": ["svcs", "svc"],
        "enterprises": ["ent", "ents"],
        "holdings": ["hldgs", "hldg"],
        "capital": ["cap", "capl"],
        "partners": ["ptr", "ptrs"],
        "associates": ["assoc", "assocs"],
        "management": ["mgmt", "mgt"],
        "investment": ["inv", "invmt"],
        "financial": ["fin", "fncl"],
        "bank": ["bk", "bnk"],
        "national": ["natl", "ntl"],
        "federal": ["fed", "fdl"],
        "association": ["assn", "assoc"],
        "organization": ["org", "orgn"],
        "government": ["gov", "govt"],
        "department": ["dept", "dpt"],
        "administration": ["admin", "admn"],
        "commission": ["comm", "commn"],
        "committee": ["cmte", "cmtee"],
        "corporation": ["corp", "corp."],
        "incorporated": ["inc", "inc."],
        "limited": ["ltd", "ltd."],
    }
    
    # Reverse mapping
    ABBREVIATION_REVERSE = {}
    for full, abbrevs in ABBREVIATION_PATTERNS.items():
        for abbrev in abbrevs:
            ABBREVIATION_REVERSE[abbrev] = full
    
    # Known person name variations
    PERSON_VARIATIONS = {
        "tim cook": ["timothy cook", "t. cook"],
        "satya nadella": ["satya narayana nadella", "s. nadella"],
        "sundar pichai": ["pichai sundararajan", "s. pichai"],
        "mark zuckerberg": ["mark elliot zuckerberg", "m. zuckerberg"],
        "jeff bezos": ["jeffrey bezos", "j. bezos"],
        "andy jassy": ["andrew jassy", "a. jassy"],
        "warren buffett": ["warren edward buffett", "w. buffett"],
        "charlie munger": ["charles munger", "c. munger"],
        "jamie dimon": ["james dimon", "j. dimon"],
        "david solomon": ["david m. solomon", "d. solomon"],
        "jane fraser": ["j. fraser"],
        "jensen huang": ["jen-hsun huang", "j. huang"],
        "lisa su": ["l. su"],
        "pat gelsinger": ["patrick gelsinger", "p. gelsinger"],
        "mary barra": ["mary teresa barra", "m. barra"],
        "elont musk": ["elon musk", "e. musk"],
    }
    
    def __init__(self, dictionary: Optional[FinancialDictionary] = None):
        self.dictionary = dictionary or get_financial_dictionary()
        self.dictionary.initialize()
        
        # Build alias indexes
        self._alias_to_canonical: Dict[str, Tuple[str, EntityType, Optional[EntitySubType]]] = {}
        self._canonical_to_aliases: Dict[str, Set[str]] = defaultdict(set)
        
        self._build_alias_indexes()
        
    def _build_alias_indexes(self) -> None:
        """Build alias lookup indexes from dictionary."""
        # Company aliases
        for entry in self.dictionary.get_all_companies():
            canonical = entry.canonical_name
            entity_type = EntityType.COMPANY
            sub_type = EntitySubType(entry.sub_type) if entry.sub_type else EntitySubType.PUBLIC_COMPANY
            
            # Add canonical name to itself
            self._alias_to_canonical[canonical.lower()] = (canonical, entity_type, sub_type)
            self._canonical_to_aliases[canonical.lower()].add(canonical.lower())
            
            # Add all aliases
            for alias in entry.all_names():
                self._alias_to_canonical[alias.lower()] = (canonical, entity_type, sub_type)
                self._canonical_to_aliases[canonical.lower()].add(alias.lower())
                
        # Ticker aliases
        for entry in self.dictionary.get_all_tickers():
            canonical = entry.canonical_name
            entity_type = EntityType.TICKER
            sub_type = EntitySubType.US_EQUITY
            
            self._alias_to_canonical[canonical.lower()] = (canonical, entity_type, sub_type)
            self._canonical_to_aliases[canonical.lower()].add(canonical.lower())
            
        # People aliases
        for entry in self.dictionary.get_all_people():
            canonical = entry.canonical_name
            entity_type = EntityType.PERSON
            sub_type = EntitySubType(entry.sub_type) if entry.sub_type else None
            
            self._alias_to_canonical[canonical.lower()] = (canonical, entity_type, sub_type)
            self._canonical_to_aliases[canonical.lower()].add(canonical.lower())
            
            for alias in entry.aliases:
                self._alias_to_canonical[alias.lower()] = (canonical, entity_type, sub_type)
                self._canonical_to_aliases[canonical.lower()].add(alias.lower())
                
        # Exchange aliases
        for entry in self.dictionary.get_all_exchanges():
            canonical = entry.canonical_name
            entity_type = EntityType.EXCHANGE
            
            self._alias_to_canonical[canonical.lower()] = (canonical, entity_type, None)
            self._canonical_to_aliases[canonical.lower()].add(canonical.lower())
            
            for alias in entry.aliases:
                self._alias_to_canonical[alias.lower()] = (canonical, entity_type, None)
                self._canonical_to_aliases[canonical.lower()].add(alias.lower())
                
        # Index aliases
        for entry in self.dictionary.get_all_indices():
            canonical = entry.canonical_name
            entity_type = EntityType.INDEX
            
            self._alias_to_canonical[canonical.lower()] = (canonical, entity_type, None)
            self._canonical_to_aliases[canonical.lower()].add(canonical.lower())
            
            for alias in entry.aliases:
                self._alias_to_canonical[alias.lower()] = (canonical, entity_type, None)
                self._canonical_to_aliases[canonical.lower()].add(alias.lower())
                
        # Crypto aliases
        for entry in self.dictionary.get_all_crypto():
            canonical = entry.canonical_name
            entity_type = EntityType.CRYPTOCURRENCY
            sub_type = EntitySubType(entry.sub_type) if entry.sub_type else EntitySubType.COIN
            
            self._alias_to_canonical[canonical.lower()] = (canonical, entity_type, sub_type)
            self._canonical_to_aliases[canonical.lower()].add(canonical.lower())
            
            for alias in entry.aliases:
                self._alias_to_canonical[alias.lower()] = (canonical, entity_type, sub_type)
                self._canonical_to_aliases[canonical.lower()].add(alias.lower())
                
        # Commodity aliases
        for entry in self.dictionary.get_all_commodities():
            canonical = entry.canonical_name
            entity_type = EntityType.COMMODITY
            
            self._alias_to_canonical[canonical.lower()] = (canonical, entity_type, None)
            self._canonical_to_aliases[canonical.lower()].add(canonical.lower())
            
            for alias in entry.aliases:
                self._alias_to_canonical[alias.lower()] = (canonical, entity_type, None)
                self._canonical_to_aliases[canonical.lower()].add(alias.lower())
                
        # Add abbreviation expansions
        self._add_abbreviation_aliases()
        
        # Add person name variations
        self._add_person_variations()
        
        logger.info(f"Built alias indexes: {len(self._alias_to_canonical)} aliases, {len(self._canonical_to_aliases)} canonical entities")
        
    def _add_abbreviation_aliases(self) -> None:
        """Add abbreviation-based aliases for companies."""
        for entry in self.dictionary.get_all_companies():
            canonical = entry.canonical_name.lower()
            
            # Generate abbreviated versions
            words = canonical.split()
            if len(words) > 1:
                # Acronym from first letters
                acronym = ''.join(w[0] for w in words if w not in ['inc', 'corp', 'corporation', 'company', 'co', 'ltd', 'limited', 'plc', 'llc', 'group', 'holdings', 'the', 'and', 'of', '&'])
                if len(acronym) >= 2:
                    self._alias_to_canonical[acronym] = (entry.canonical_name, EntityType.COMPANY, EntitySubType.PUBLIC_COMPANY)
                    self._canonical_to_aliases[canonical].add(acronym)
                    
                # Shortened versions (remove common suffixes)
                suffix_removed = canonical
                for suffix in [' inc', ' inc.', ' corp', ' corp.', ' corporation', ' company', ' co', ' co.', ' ltd', ' ltd.', ' limited', ' plc', ' llc', ' llp', ' lp', ' group', ' holdings', ' holding', ' technologies', ' technology', ' solutions', ' systems', ' services', ' enterprises', ' international', ' intl']:
                    if canonical.endswith(suffix):
                        shortened = canonical[:-len(suffix)]
                        if len(shortened) > 2:
                            self._alias_to_canonical[shortened] = (entry.canonical_name, EntityType.COMPANY, EntitySubType.PUBLIC_COMPANY)
                            self._canonical_to_aliases[canonical].add(shortened)
                            break
                            
    def _add_person_variations(self) -> None:
        """Add person name variations."""
        for canonical, variations in self.PERSON_VARIATIONS.items():
            for entry in self.dictionary.get_all_people():
                if entry.canonical_name.lower() == canonical:
                    entity_type = EntityType.PERSON
                    sub_type = EntitySubType(entry.sub_type) if entry.sub_type else None
                    for var in variations:
                        self._alias_to_canonical[var.lower()] = (entry.canonical_name, entity_type, sub_type)
                        self._canonical_to_aliases[canonical].add(var.lower())
                    break
                    
    def resolve(self, alias: str) -> Optional[AliasMatch]:
        """
        Resolve an alias to its canonical form.
        
        Args:
            alias: Alias text to resolve
            
        Returns:
            AliasMatch with canonical entity or None
        """
        if not alias:
            return None
            
        alias_lower = alias.strip().lower()
        
        # Direct lookup
        if alias_lower in self._alias_to_canonical:
            canonical, entity_type, sub_type = self._alias_to_canonical[alias_lower]
            return AliasMatch(
                alias=alias,
                canonical_name=canonical,
                entity_type=entity_type,
                sub_type=sub_type,
                confidence=0.95,
                match_type="exact"
            )
            
        # Try without common prefixes/suffixes
        cleaned = self._clean_alias(alias_lower)
        if cleaned != alias_lower and cleaned in self._alias_to_canonical:
            canonical, entity_type, sub_type = self._alias_to_canonical[cleaned]
            return AliasMatch(
                alias=alias,
                canonical_name=canonical,
                entity_type=entity_type,
                sub_type=sub_type,
                confidence=0.85,
                match_type="cleaned"
            )
            
        # Try abbreviation expansion
        expanded = self._expand_abbreviations(alias_lower)
        if expanded != alias_lower and expanded in self._alias_to_canonical:
            canonical, entity_type, sub_type = self._alias_to_canonical[expanded]
            return AliasMatch(
                alias=alias,
                canonical_name=canonical,
                entity_type=entity_type,
                sub_type=sub_type,
                confidence=0.8,
                match_type="abbreviation"
            )
            
        # Try fuzzy match
        fuzzy_match = self._fuzzy_match(alias_lower)
        if fuzzy_match:
            canonical, entity_type, sub_type = fuzzy_match
            return AliasMatch(
                alias=alias,
                canonical_name=canonical,
                entity_type=entity_type,
                sub_type=sub_type,
                confidence=0.7,
                match_type="fuzzy"
            )
            
        return None
        
    def _clean_alias(self, alias: str) -> str:
        """Clean alias by removing common noise."""
        # Remove parenthetical content
        alias = re.sub(r'\s*\([^)]*\)', '', alias)
        
        # Remove quotes
        alias = alias.strip('\'"')
        
        # Remove trailing punctuation
        alias = alias.rstrip('.,;:!?')
        
        # Remove common prefixes
        prefixes = ['the ', 'a ', 'an ', 'new ']
        for prefix in prefixes:
            if alias.startswith(prefix):
                alias = alias[len(prefix):]
                
        return alias.strip()
        
    def _expand_abbreviations(self, alias: str) -> str:
        """Expand common abbreviations in alias."""
        words = alias.split()
        expanded = []
        for word in words:
            # Remove trailing punctuation
            word_clean = word.rstrip('.,')
            if word_clean in self.ABBREVIATION_REVERSE:
                expanded.append(self.ABBREVIATION_REVERSE[word_clean])
            else:
                expanded.append(word)
        return ' '.join(expanded)
        
    def _fuzzy_match(self, alias: str) -> Optional[Tuple[str, EntityType, Optional[EntitySubType]]]:
        """Fuzzy match alias to canonical."""
        best_match = None
        best_score = 0.0
        
        for known_alias, (canonical, entity_type, sub_type) in self._alias_to_canonical.items():
            if abs(len(known_alias) - len(alias)) > 3:
                continue
                
            # Simple character overlap score
            score = self._similarity_score(alias, known_alias)
            if score > best_score and score > 0.8:
                best_score = score
                best_match = (canonical, entity_type, sub_type)
                
        return best_match
        
    def _similarity_score(self, s1: str, s2: str) -> float:
        """Calculate similarity score between two strings."""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, s1, s2).ratio()
        
    def get_all_aliases(self, canonical_name: str) -> List[str]:
        """Get all aliases for a canonical entity."""
        return list(self._canonical_to_aliases.get(canonical_name.lower(), set()))
        
    def get_canonical(self, alias: str) -> Optional[str]:
        """Get canonical name for an alias."""
        match = self.resolve(alias)
        return match.canonical_name if match else None
        
    def resolve_batch(self, aliases: List[str]) -> List[Optional[AliasMatch]]:
        """Resolve multiple aliases."""
        return [self.resolve(a) for a in aliases]
        
    def create_entity_from_alias(
        self, 
        text: str, 
        start_char: int, 
        end_char: int,
        match: Optional[AliasMatch] = None
    ) -> Entity:
        """Create an Entity from an alias mention."""
        if match is None:
            match = self.resolve(text)
            
        if match:
            entity = Entity(
                text=text,
                entity_type=match.entity_type,
                sub_type=match.sub_type,
                confidence=match.confidence,
                normalized_value=match.canonical_name,
                canonical_name=match.canonical_name,
                start_char=start_char,
                end_char=end_char,
                validation_method="alias_resolver",
                metadata=match.metadata
            )
            entity.metadata["resolution"] = {
            "alias": match.alias,
            "canonical_name": match.canonical_name,
            "entity_type": match.entity_type.value,
            "sub_type": match.sub_type.value if match.sub_type else None,
            "confidence": match.confidence,
            "match_type": match.match_type,
            "metadata": match.metadata
        }
        else:
            entity = Entity(
                text=text,
                entity_type=EntityType.UNKNOWN,
                confidence=0.3,
                normalized_value=text,
                start_char=start_char,
                end_char=end_char,
                validation_method="alias_resolver",
                metadata={"unresolved": True}
            )
            
        return entity
        
    def add_alias(self, alias: str, canonical_name: str, entity_type: EntityType, 
                  sub_type: Optional[EntitySubType] = None) -> None:
        """Add a custom alias mapping."""
        self._alias_to_canonical[alias.lower()] = (canonical_name, entity_type, sub_type)
        self._canonical_to_aliases[canonical_name.lower()].add(alias.lower())


# Singleton instance
_alias_resolver: Optional[AliasResolver] = None


def get_alias_resolver(dictionary: Optional[FinancialDictionary] = None) -> AliasResolver:
    """Get or create the default alias resolver."""
    global _alias_resolver
    if _alias_resolver is None:
        _alias_resolver = AliasResolver(dictionary)
    return _alias_resolver