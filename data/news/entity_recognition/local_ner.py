"""
Local NER Extractor for Financial Entities

Uses spaCy NLP pipeline with custom financial entity patterns for named entity recognition.
Supports companies, people, organizations, locations, dates, money, percentages, and custom financial entities.
"""

import logging
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass
import asyncio

from data.news.entity_recognition.schemas import (
    Entity, EntityType, EntitySubType, ConfidenceLevel
)

logger = logging.getLogger(__name__)


@dataclass
class SpacyNERConfig:
    """Configuration for spaCy NER."""
    model_name: str = "en_core_web_lg"
    enable_components: List[str] = None
    disable_components: List[str] = None
    custom_patterns: Dict[str, List[Dict]] = None
    min_confidence: float = 0.5
    
    def __post_init__(self):
        if self.enable_components is None:
            self.enable_components = ["ner", "tagger", "parser", "attribute_ruler"]
        if self.disable_components is None:
            self.disable_components = ["tok2vec"]


class LocalNerExtractor:
    """
    Local NER extractor using spaCy.
    
    Extracts:
    - Organizations (companies, institutions)
    - Persons (executives, analysts, investors)
    - Locations (countries, cities, exchanges)
    - Dates (financial periods, specific dates)
    - Money amounts
    - Percentages
    - Custom financial entities via patterns
    """
    
    # Mapping from spaCy entity labels to our EntityType
    SPACY_TO_ENTITY_TYPE = {
        "ORG": EntityType.COMPANY,
        "PERSON": EntityType.PERSON,
        "GPE": EntityType.COUNTRY,  # Geopolitical entity
        "LOC": EntityType.CITY,
        "DATE": EntityType.DATE,
        "MONEY": EntityType.MONEY,
        "PERCENT": EntityType.PERCENTAGE,
        "CARDINAL": None,  # Generic numbers
        "ORDINAL": None,
        "TIME": EntityType.DATE,
        "NORP": EntityType.COUNTRY,  # Nationalities/religious/political groups
        "FAC": EntityType.EXCHANGE,  # Facilities
        "PRODUCT": EntityType.PRODUCT,
        "EVENT": EntityType.EVENT,
        "LAW": EntityType.REGULATOR,
        "LANGUAGE": None,
        "WORK_OF_ART": None,
    }
    
    # Sub-type mappings for specific entity types
    ENTITY_SUBTYPE_HINTS = {
        EntityType.COMPANY: {
            "inc": EntitySubType.PUBLIC_COMPANY,
            "corp": EntitySubType.PUBLIC_COMPANY,
            "corporation": EntitySubType.PUBLIC_COMPANY,
            "ltd": EntitySubType.PRIVATE_COMPANY,
            "llc": EntitySubType.PRIVATE_COMPANY,
            "lp": EntitySubType.PRIVATE_COMPANY,
            "llp": EntitySubType.PRIVATE_COMPANY,
            "plc": EntitySubType.PUBLIC_COMPANY,
            "group": EntitySubType.HOLDING_COMPANY,
            "holding": EntitySubType.HOLDING_COMPANY,
            "bank": EntitySubType.BANK,
            "fund": EntitySubType.INVESTMENT_FUND,
            "trust": EntitySubType.INVESTMENT_FUND,
            "capital": EntitySubType.VENTURE_CAPITAL,
            "ventures": EntitySubType.VENTURE_CAPITAL,
            "partners": EntitySubType.PRIVATE_EQUITY,
            "asset": EntitySubType.ASSET_MANAGER,
            "management": EntitySubType.ASSET_MANAGER,
            "advisors": EntitySubType.ASSET_MANAGER,
            "securities": EntitySubType.BROKER_DEALER,
            "broker": EntitySubType.BROKER_DEALER,
            "exchange": EntitySubType.STOCK_EXCHANGE,
            "clearing": EntitySubType.CLEARING_HOUSE,
            "depository": EntitySubType.CUSTODIAN,
            "insurance": EntitySubType.INSURANCE_COMPANY,
            "reinsurance": EntitySubType.INSURANCE_COMPANY,
        },
        EntityType.PERSON: {
            "ceo": EntitySubType.CEO,
            "cfo": EntitySubType.CFO,
            "cto": EntitySubType.CXO,
            "coo": EntitySubType.CXO,
            "president": EntitySubType.PRESIDENT,
            "chairman": EntitySubType.CHAIRMAN,
            "founder": EntitySubType.FOUNDER,
            "co-founder": EntitySubType.FOUNDER,
            "cofounder": EntitySubType.FOUNDER,
            "investor": EntitySubType.INVESTOR,
            "analyst": EntitySubType.ANALYST,
            "portfolio manager": EntitySubType.PORTFOLIO_MANAGER,
            "fund manager": EntitySubType.PORTFOLIO_MANAGER,
            "director": EntitySubType.DIRECTOR,
            "board": EntitySubType.DIRECTOR,
        },
    }
    
    def __init__(self, config: Optional[SpacyNERConfig] = None):
        self.config = config or SpacyNERConfig()
        self._nlp = None
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize spaCy pipeline asynchronously."""
        if self._initialized:
            return
            
        try:
            import spacy
            from spacy.pipeline import EntityRuler
            
            # Load model
            self._nlp = spacy.load(self.config.model_name)
            
            # Add custom entity ruler for financial patterns
            if "entity_ruler" not in self._nlp.pipe_names:
                ruler = self._nlp.add_pipe("entity_ruler", before="ner")
            else:
                ruler = self._nlp.get_pipe("entity_ruler")
                
            # Add financial patterns
            patterns = self._get_financial_patterns()
            ruler.add_patterns(patterns)
            
            self._initialized = True
            logger.info(f"Local NER initialized with model: {self.config.model_name}")
            
        except OSError:
            logger.warning(f"spaCy model {self.config.model_name} not found. Attempting to download...")
            await self._download_model()
            await self.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize spaCy NER: {e}")
            raise
            
    async def _download_model(self) -> None:
        """Download spaCy model."""
        import subprocess
        import sys
        
        result = subprocess.run([
            sys.executable, "-m", "spacy", "download", self.config.model_name
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to download spaCy model: {result.stderr}")
            
        logger.info(f"Downloaded spaCy model: {self.config.model_name}")
        
    def _get_financial_patterns(self) -> List[Dict]:
        """Get financial entity patterns for entity ruler."""
        patterns = []
        
        # Stock tickers
        patterns.extend([
            {"label": "TICKER", "pattern": [{"TEXT": {"REGEX": r"^[A-Z]{1,5}(\.[A-Z])?$"}}]},
            {"label": "TICKER", "pattern": [{"LOWER": "nyse"}, {"TEXT": ":"}, {"TEXT": {"REGEX": r"^[A-Z]{1,5}(\.[A-Z])?$"}}]},
            {"label": "TICKER", "pattern": [{"LOWER": "nasdaq"}, {"TEXT": ":"}, {"TEXT": {"REGEX": r"^[A-Z]{1,5}(\.[A-Z])?$"}}]},
            {"label": "TICKER", "pattern": [{"TEXT": "("}, {"LOWER": "nyse"}, {"TEXT": ":"}, {"TEXT": {"REGEX": r"^[A-Z]{1,5}(\.[A-Z])?$"}}, {"TEXT": ")"}]},
            {"label": "TICKER", "pattern": [{"TEXT": "("}, {"LOWER": "nasdaq"}, {"TEXT": ":"}, {"TEXT": {"REGEX": r"^[A-Z]{1,5}(\.[A-Z])?$"}}, {"TEXT": ")"}]},
        ])
        
        # Financial metrics
        metric_terms = [
            "revenue", "sales", "turnover", "eps", "earnings per share",
            "ebitda", "ebit", "operating income", "net income", "net profit",
            "gross profit", "gross margin", "operating margin", "net margin",
            "free cash flow", "fcf", "operating cash flow", "ocf",
            "total assets", "total liabilities", "shareholders equity", "book value",
            "market cap", "market capitalization", "enterprise value", "ev",
            "pe ratio", "price to earnings", "peg ratio", "price to book",
            "dividend", "dividend yield", "buyback", "share repurchase",
            "guidance", "outlook", "forecast", "estimate", "target price", "price target",
        ]
        
        for term in metric_terms:
            words = term.split()
            pattern = [{"LOWER": w} for w in words]
            patterns.append({"label": "METRIC", "pattern": pattern})
            
        # Event types
        event_terms = [
            "earnings release", "earnings call", "quarterly earnings",
            "merger", "acquisition", "takeover", "buyout",
            "ipo", "initial public offering", "direct listing", "spac",
            "stock split", "reverse split", "dividend announcement",
            "buyback announcement", "guidance", "analyst day",
            "investor day", "capital markets day", "bankruptcy",
            "chapter 11", "chapter 7", "restructuring",
            "lawsuit", "litigation", "sec investigation", "doj investigation",
            "product launch", "partnership", "strategic alliance", "joint venture",
            "interest rate decision", "fed meeting", "fomc",
            "inflation report", "cpi", "ppi", "gdp", "nonfarm payrolls",
            "credit rating", "upgrade", "downgrade", "rating outlook",
        ]
        
        for term in event_terms:
            words = term.split()
            pattern = [{"LOWER": w} for w in words]
            patterns.append({"label": "EVENT", "pattern": pattern})
            
        # Currencies
        currencies = [
            "usd", "eur", "gbp", "jpy", "cny", "cad", "aud", "chf",
            "hkd", "sgd", "inr", "krw", "brl", "mxn", "zar",
        ]
        for curr in currencies:
            patterns.append({"label": "CURRENCY", "pattern": [{"LOWER": curr}]})
            
        # Exchanges
        exchanges = [
            "nyse", "nasdaq", "amex", "arca", "bats", "iex",
            "lse", "tsx", "tsxv", "cse", "tse", "hkex",
            "sse", "szse", "euronext", "xetra", "db",
            "asx", "sgx", "bse", "nse", "krx", "tadawul",
        ]
        for exch in exchanges:
            patterns.append({"label": "EXCHANGE", "pattern": [{"LOWER": exch}]})
            
        # Indices
        indices = [
            "s&p 500", "sp500", "spx", "dow jones", "djia", "dow",
            "nasdaq composite", "nasdaq 100", "ndx", "qqq",
            "russell 2000", "rut", "vix", "ftse 100", "ftse",
            "dax", "cac 40", "cac", "nikkei 225", "nikkei",
            "hang seng", "hsi", "shanghai composite", "ssec",
            "stoxx 600", "stoxx", "msci world", "msci emerging",
        ]
        for idx in indices:
            words = idx.split()
            pattern = [{"LOWER": w} for w in words]
            patterns.append({"label": "INDEX", "pattern": pattern})
            
        # Central banks
        central_banks = [
            "federal reserve", "fed", "fomc", "ecb", "european central bank",
            "bank of england", "boe", "bank of japan", "boj",
            "people's bank of china", "pboc", "bank of canada", "boc",
            "reserve bank of australia", "rba", "reserve bank of new zealand", "rbnz",
            "swiss national bank", "snb", "reserve bank of india", "rbi",
            "central bank of brazil", "bcb", "south african reserve bank", "sarb",
        ]
        for cb in central_banks:
            words = cb.split()
            pattern = [{"LOWER": w} for w in words]
            patterns.append({"label": "CENTRAL_BANK", "pattern": pattern})
            
        # Regulators
        regulators = [
            "sec", "securities and exchange commission", "cftc", "commodity futures trading commission",
            "finra", "financial industry regulatory authority", "occ", "office of the comptroller of the currency",
            "fdic", "federal deposit insurance corporation", "fca", "financial conduct authority",
            "esma", "european securities and markets authority", "fsa", "financial services agency",
            "csrc", "china securities regulatory commission", "sebi", "securities and exchange board of india",
            "mas", "monetary authority of singapore", "hkma", "hong kong monetary authority",
        ]
        for reg in regulators:
            words = reg.split()
            pattern = [{"LOWER": w} for w in words]
            patterns.append({"label": "REGULATOR", "pattern": pattern})
            
        # Cryptocurrencies
        crypto = [
            "bitcoin", "btc", "ethereum", "eth", "tether", "usdt", "bnb", "binance coin",
            "solana", "sol", "xrp", "ripple", "cardano", "ada", "dogecoin", "doge",
            "polygon", "matic", "polkadot", "dot", "shiba inu", "shib", "avalanche", "avax",
            "litecoin", "ltc", "chainlink", "link", "uniswap", "uni", "cosmos", "atom",
            "stellar", "xlm", "bitcoin cash", "bch", "ethereum classic", "etc", "filecoin", "fil",
            "near protocol", "near", "aptos", "apt", "sui", "optimism", "op", "arbitrum", "arb",
        ]
        for c in crypto:
            patterns.append({"label": "CRYPTOCURRENCY", "pattern": [{"LOWER": c}]})
            
        # Commodities
        commodities = [
            "gold", "silver", "crude oil", "wti", "brent", "natural gas", "copper",
            "platinum", "palladium", "corn", "wheat", "soybeans", "coffee", "sugar",
            "cotton", "cocoa", "live cattle", "lean hogs",
        ]
        for comm in commodities:
            words = comm.split()
            pattern = [{"LOWER": w} for w in words]
            patterns.append({"label": "COMMODITY", "pattern": pattern})
            
        # Sectors
        sectors = [
            "technology", "healthcare", "financial", "energy", "consumer",
            "industrial", "materials", "utilities", "real estate", "communication",
            "consumer discretionary", "consumer staples", "information technology",
        ]
        for sector in sectors:
            words = sector.split()
            pattern = [{"LOWER": w} for w in words]
            patterns.append({"label": "SECTOR", "pattern": pattern})
            
        return patterns
        
    def _map_spacy_entity(self, ent) -> Optional[Entity]:
        """Map spaCy entity to our Entity schema."""
        entity_type = self.SPACY_TO_ENTITY_TYPE.get(ent.label_)
        if entity_type is None:
            return None
            
        # Determine sub-type
        sub_type = None
        text_lower = ent.text.lower()
        
        if entity_type in self.ENTITY_SUBTYPE_HINTS:
            for hint, sub in self.ENTITY_SUBTYPE_HINTS[entity_type].items():
                if hint in text_lower:
                    sub_type = sub
                    break
                    
        # Confidence based on entity length and context
        confidence = 0.75
        if len(ent.text) > 2:
            confidence = 0.8
        if ent.label_ in ["ORG", "PERSON", "GPE"]:
            confidence = 0.85
            
        entity = Entity(
            text=ent.text,
            entity_type=entity_type,
            sub_type=sub_type,
            confidence=confidence,
            start_char=ent.start_char,
            end_char=ent.end_char,
            normalized_value=ent.text,
            validation_method="spacy_ner"
        )
        
        # Add spaCy metadata
        entity.metadata["spacy_label"] = ent.label_
        entity.metadata["spacy_kb_id"] = ent.kb_id_ if hasattr(ent, 'kb_id_') else None
        
        return entity
        
    def _merge_entities(self, entities: List[Entity]) -> List[Entity]:
        """Merge overlapping entities, keeping higher confidence ones."""
        if not entities:
            return []
            
        # Sort by start position, then by confidence (descending)
        entities.sort(key=lambda e: (e.start_char, -e.confidence))
        
        merged = []
        current = entities[0]
        
        for next_ent in entities[1:]:
            # Check for overlap
            if next_ent.start_char < current.end_char:
                # Overlapping - keep higher confidence
                if next_ent.confidence > current.confidence:
                    current = next_ent
                # If same confidence, prefer longer entity
                elif next_ent.confidence == current.confidence:
                    if (next_ent.end_char - next_ent.start_char) > (current.end_char - current.start_char):
                        current = next_ent
            else:
                # No overlap, add current and move to next
                merged.append(current)
                current = next_ent
                
        merged.append(current)
        return merged
        
    async def extract(self, text: str) -> List[Entity]:
        """
        Extract entities from text using spaCy NER.
        
        Args:
            text: Input text to extract entities from
            
        Returns:
            List of extracted entities
        """
        if not self._initialized:
            await self.initialize()
            
        # Run spaCy in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        doc = await loop.run_in_executor(None, self._nlp, text)
        
        entities = []
        for ent in doc.ents:
            entity = self._map_spacy_entity(ent)
            if entity:
                entities.append(entity)
                
        # Merge overlapping entities
        entities = self._merge_entities(entities)
        
        return entities
        
    def extract_sync(self, text: str) -> List[Entity]:
        """Synchronous version of extract."""
        if not self._initialized:
            import spacy
            self._nlp = spacy.load(self.config.model_name)
            ruler = self._nlp.add_pipe("entity_ruler", before="ner")
            patterns = self._get_financial_patterns()
            ruler.add_patterns(patterns)
            self._initialized = True
            
        doc = self._nlp(text)
        
        entities = []
        for ent in doc.ents:
            entity = self._map_spacy_entity(ent)
            if entity:
                entities.append(entity)
                
        entities = self._merge_entities(entities)
        return entities
        
    def add_custom_patterns(self, patterns: List[Dict]) -> None:
        """Add custom patterns to the entity ruler."""
        if self._initialized and "entity_ruler" in self._nlp.pipe_names:
            ruler = self._nlp.get_pipe("entity_ruler")
            ruler.add_patterns(patterns)
            
    def get_supported_labels(self) -> List[str]:
        """Get list of supported entity labels."""
        return list(self.SPACY_TO_ENTITY_TYPE.keys())


# Singleton instance
_local_ner_extractor: Optional[LocalNerExtractor] = None


async def get_local_ner_extractor(config: Optional[SpacyNERConfig] = None) -> LocalNerExtractor:
    """Get or create the default local NER extractor."""
    global _local_ner_extractor
    if _local_ner_extractor is None:
        _local_ner_extractor = LocalNerExtractor(config)
        await _local_ner_extractor.initialize()
    return _local_ner_extractor