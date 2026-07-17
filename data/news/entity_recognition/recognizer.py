"""
Financial Entity Recognizer

Uses spaCy NLP with custom financial patterns and dictionaries for entity extraction.
Supports companies, tickers, people, money, percentages, dates, indices, crypto, commodities, and more.
"""

import re
import logging
from typing import List, Optional, Dict, Any, Set, Tuple, Pattern
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

import spacy
from spacy.matcher import Matcher, PhraseMatcher
from spacy.tokens import Doc, Span, Token
from spacy.language import Language

from data.news.entity_recognition.schemas import (
    Entity, EntityType, EntitySubType, EntityRelation, EntityContext,
    ExtractionResult,
    EntityType, EntitySubType,
    COMMON_TICKER_PATTERNS, COMMON_MONEY_PATTERNS,
    COMMON_PERCENTAGE_PATTERNS, COMMON_DATE_PATTERNS,
    COMPANY_SUFFIXES, MAJOR_EXCHANGES, MAJOR_INDICES,
    CENTRAL_BANKS, REGULATORS, CRYPTOCURRENCIES, COMMODITIES,
)

logger = logging.getLogger(__name__)


@dataclass
class RecognizerConfig:
    """Configuration for the entity recognizer."""
    spacy_model: str = "en_core_web_lg"
    use_gpu: bool = False
    confidence_threshold: float = 0.7
    max_entities_per_doc: int = 500
    enable_coreference: bool = False
    custom_patterns: Dict[str, List[str]] = field(default_factory=dict)
    custom_dictionaries: Dict[str, List[str]] = field(default_factory=dict)
    cache_enabled: bool = True


class FinancialEntityRecognizer:
    """
    Financial entity recognizer using spaCy with custom patterns.
    
    Extracts: companies, tickers, people, money, percentages, dates,
    indices, crypto, commodities, regulators, exchanges, events, and more.
    """
    
    def __init__(self, config: Optional[RecognizerConfig] = None):
        self.config = config or RecognizerConfig()
        self.nlp: Optional[Language] = None
        self.matcher: Optional[Matcher] = None
        self.phrase_matcher: Optional[PhraseMatcher] = None
        self._patterns_initialized = False
        self._cache: Dict[str, ExtractionResult] = {}
        
    def initialize(self) -> None:
        """Initialize spaCy pipeline and custom patterns."""
        if self._patterns_initialized:
            return
            
        logger.info(f"Loading spaCy model: {self.config.spacy_model}")
        
        # Load spaCy model
        try:
            self.nlp = spacy.load(self.config.spacy_model)
        except OSError:
            logger.warning(f"Model {self.config.spacy_model} not found, downloading...")
            spacy.cli.download(self.config.spacy_model)
            self.nlp = spacy.load(self.config.spacy_model)
            
        # Disable unused pipeline components for speed
        disabled = ["parser", "lemmatizer"]
        if not self.config.enable_coreference:
            disabled.append("coref")
            
        for component in disabled:
            if component in self.nlp.pipe_names:
                self.nlp.remove_pipe(component)
                
        # Initialize matchers
        self.matcher = Matcher(self.nlp.vocab)
        self.phrase_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        
        # Initialize patterns
        self._initialize_patterns()
        self._initialize_phrase_patterns()
        
        # Add custom spaCy pipeline component
        if "financial_entity_recognizer" not in self.nlp.pipe_names:
            self.nlp.add_pipe("financial_entity_recognizer", last=True)
            
        self._patterns_initialized = True
        logger.info("Financial entity recognizer initialized successfully")
        
    def _initialize_patterns(self) -> None:
        """Initialize regex-based patterns for the Matcher."""
        if not self.nlp:
            return
            
        # Ticker patterns
        ticker_patterns = [
            [{"TEXT": {"REGEX": r"^\$[A-Z]{1,5}$"}}],
            [{"TEXT": {"REGEX": r"^[A-Z]{1,5}\.[A-Z]{1,3}$"}}],
            [{"TEXT": {"REGEX": r"^[A-Z]{1,5}$"}, 
              "RIGHT_ID": "ticker", "RIGHT_ATTR": "TEXT"},
             {"LOWER": {"IN": ["stock", "shares", "share", "equity", "ticker"]},
              "LEFT_ID": "ticker", "REL_OP": ">"}],
        ]
        self.matcher.add("TICKER", ticker_patterns)
        
        # Money patterns
        money_patterns = [
            [{"TEXT": {"REGEX": r"^\$\d+(?:[,.]\d+)*(?:\s*(?:billion|million|trillion|[kmbt]))?$"}}],
            [{"TEXT": {"REGEX": r"^\d+(?:[,.]\d+)*\s*(?:billion|million|trillion|[kmbt])\s*(?:USD|EUR|GBP|dollars?|euros?|pounds?)$"}}],
            [{"LOWER": {"IN": ["usd", "eur", "gbp", "jpy", "cny", "cad", "aud", "chf"]}},
             {"LIKE_NUM": True}],
            [{"TEXT": {"REGEX": r"^\$\d+(?:[,.]\d+)*$"}}],
        ]
        self.matcher.add("MONEY", money_patterns)
        
        # Percentage patterns
        pct_patterns = [
            [{"TEXT": {"REGEX": r"^\d+(?:\.\d+)?%$"}}],
            [{"LIKE_NUM": True}, {"LOWER": "%"}],
            [{"LIKE_NUM": True}, {"LOWER": "percent"}],
            [{"LIKE_NUM": True}, {"LOWER": "percentage"}, {"LOWER": "points?"}],
        ]
        self.matcher.add("PERCENTAGE", pct_patterns)
        
        # Date patterns
        date_patterns = [
            [{"TEXT": {"REGEX": r"^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}$"}}],
            [{"TEXT": {"REGEX": r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$"}}],
            [{"TEXT": {"REGEX": r"^\d{4}[/-]\d{1,2}[/-]\d{1,2}$"}}],
            [{"TEXT": {"REGEX": r"^Q[1-4]\s+\d{4}$"}}],
            [{"TEXT": {"REGEX": r"^(?:FY|Fiscal Year)\s+\d{4}$"}}],
        ]
        self.matcher.add("DATE", date_patterns)
        
        # Company with suffix
        company_patterns = []
        for suffix in COMPANY_SUFFIXES:
            company_patterns.append([
                {"IS_ALPHA": True, "OP": "+"},
                {"TEXT": {"REGEX": f"^{re.escape(suffix)}\\.?$"}},
            ])
        self.matcher.add("COMPANY", company_patterns)
        
        # Exchange patterns
        exchange_patterns = [
            [{"TEXT": {"REGEX": r"^(?:NYSE|NASDAQ|AMEX|ARCA|BATS|IEX|LSE|TSX|TSXV|CSE|TSE|HKEX|SSE|SZSE|EURONEXT|XETRA|FWB|STO|OMX|ASX|SGX|BSE|NSE|KRX|TADAWUL|QSE|ADX|DFM)$"}}],
        ]
        self.matcher.add("EXCHANGE", exchange_patterns)
        
        # Index patterns
        index_patterns = [
            [{"TEXT": {"REGEX": r"^(?:S&P\s+500|SP500|SPX|S&P500|Dow\s+Jones|DJIA|Dow|DJI|NASDAQ|NASDAQ\s+100|NDX|QQQ|Russell\s+2000|RUT|R2000|VIX|CBOE\s+VIX|FTSE\s+100|FTSE|UKX|DAX|CAC\s+40|CAC|FCHI|NIKKEI\s+225|NIKKEI|N225|HANG\s+SENG|HSI|SHANGHAI\s+COMPOSITE|SSEC|STOXX\s+600|SXXP|MSCI\s+WORLD|MSCI\s+EMERGING)$"}}],
        ]
        self.matcher.add("INDEX", index_patterns)
        
        # Central bank patterns
        cb_patterns = [
            [{"TEXT": {"REGEX": r"^(?:FED|FEDERAL\s+RESERVE|THE\s+FED|ECB|EUROPEAN\s+CENTRAL\s+BANK|BOE|BANK\s+OF\s+ENGLAND|BOJ|BANK\s+OF\s+JAPAN|PBOC|PEOPLES\s+BANK\s+OF\s+CHINA|BOC|BANK\s+OF\s+CANADA|RBA|RESERVE\s+BANK\s+OF\s+AUSTRALIA|RBNZ|RESERVE\s+BANK\s+OF\s+NEW\s+ZEALAND|SNB|SWISS\s+NATIONAL\s+BANK|RBI|RESERVE\s+BANK\s+OF\s+INDIA|BCB|CENTRAL\s+BANK\s+OF\s+BRAZIL|SARB|SOUTH\s+AFRICAN\s+RESERVE\s+BANK)$"}}],
        ]
        self.matcher.add("CENTRAL_BANK", cb_patterns)
        
        # Regulator patterns
        reg_patterns = [
            [{"TEXT": {"REGEX": r"^(?:SEC|CFTC|FINRA|OCC|FDIC|FCA|ESMA|FSA|CSRC|SEBI|MAS|HKMA)$"}}],
        ]
        self.matcher.add("REGULATOR", reg_patterns)
        
        # Cryptocurrency patterns
        crypto_patterns = [
            [{"TEXT": {"REGEX": r"^(?:BTC|BITCOIN|ETH|ETHEREUM|USDT|TETHER|BNB|BINANCE\s+COIN|SOL|SOLANA|XRP|RIPPLE|ADA|CARDANO|DOGE|DOGECOIN|MATIC|POLYGON|DOT|POLKADOT|SHIB|SHIBA\s+INU|AVAX|AVALANCHE|LTC|LITECOIN|LINK|CHAINLINK|UNI|UNISWAP|ATOM|COSMOS|XLM|STELLAR|BCH|BITCOIN\s+CASH|ETC|ETHEREUM\s+CLASSIC|FIL|FILECOIN|NEAR|APT|APTOS|SUI|OP|OPTIMISM|ARB|ARBITRUM|ARB|FILECOIN)$"}}],
        ]
        self.matcher.add("CRYPTOCURRENCY", crypto_patterns)
        
        # Commodity patterns
        comm_patterns = [
            [{"TEXT": {"REGEX": r"^(?:GOLD|XAU|GLD|SILVER|XAG|SLV|OIL|WTI|BRENT|CRUDE|NATURAL\s+GAS|NG|HENRY\s+HUB|COPPER|HG|PLATINUM|XPT|PALLADIUM|XPD|CORN|ZC|WHEAT|ZW|SOYBEANS|ZS|COFFEE|KC|SUGAR|SB|COTTON|CT|COCOA|CC|LIVE\s+CATTLE|LE|LEAN\s+HOGS|HE)$"}}],
        ]
        self.matcher.add("COMMODITY", comm_patterns)
        
        # Event patterns (multi-word)
        event_patterns = []
        events = [
            "earnings release", "earnings announcement", "quarterly earnings",
            "merger", "acquisition", "merger and acquisition", "M&A",
            "IPO", "initial public offering", "direct listing",
            "secondary offering", "follow-on offering",
            "stock split", "reverse stock split",
            "dividend announcement", "dividend increase", "dividend cut",
            "buyback", "share buyback", "share repurchase",
            "guidance", "forward guidance", "guidance raise", "guidance cut",
            "analyst rating", "upgrade", "downgrade", "price target",
            "regulatory filing", "8-K", "10-K", "10-Q", "13F",
            "lawsuit", "sec investigation", "class action",
            "product launch", "product announcement",
            "partnership", "strategic partnership", "joint venture",
            "restructuring", "reorganization",
            "layoffs", "layoff", "job cuts", "workforce reduction",
            "bankruptcy", "chapter 11", "chapter 7",
        ]
        for event in events:
            words = event.split()
            if len(words) == 1:
                event_patterns.append([{"LOWER": event}])
            else:
                pattern = [{"LOWER": w} for w in words]
                event_patterns.append(pattern)
        self.matcher.add("EVENT", event_patterns)
        
        # Sector patterns
        sector_patterns = []
        sectors = [
            "technology", "tech", "software", "semiconductors", "semis",
            "healthcare", "pharma", "biotech", "biotechnology",
            "financial", "financials", "banking", "insurance", "fintech",
            "energy", "oil", "gas", "renewable", "clean energy",
            "consumer", "retail", "e-commerce", "ecommerce",
            "industrial", "manufacturing", "aerospace", "defense",
            "materials", "chemicals", "mining", "metals",
            "real estate", "REIT", "property",
            "utilities", "telecom", "telecommunications",
            "transportation", "logistics", "shipping",
            "media", "entertainment", "gaming",
            "automotive", "auto", "EV", "electric vehicles",
        ]
        for sector in sectors:
            words = sector.split()
            if len(words) == 1:
                sector_patterns.append([{"LOWER": sector}])
            else:
                sector_patterns.append([{"LOWER": w} for w in words])
        self.matcher.add("SECTOR", sector_patterns)
        
        # Person title patterns
        title_patterns = [
            [{"LOWER": {"IN": ["ceo", "cfo", "cto", "coo", "cmo", "cio", "ciso"]}}],
            [{"LOWER": {"IN": ["president", "chairman", "chairwoman", "chairperson"]}}],
            [{"LOWER": "vice"}, {"LOWER": "president"}],
            [{"LOWER": "executive"}, {"LOWER": {"IN": ["director", "vice", "chairman"]}}],
            [{"LOWER": {"IN": ["analyst", "strategist"]}}],
            [{"LOWER": "portfolio"}, {"LOWER": "manager"}],
            [{"LOWER": {"IN": ["founder", "co-founder", "cofounder"]}}],
        ]
        self.matcher.add("PERSON_TITLE", title_patterns)
        
        logger.info("Regex patterns initialized")
        
    def _initialize_phrase_patterns(self) -> None:
        """Initialize phrase-based patterns using PhraseMatcher."""
        if not self.nlp:
            return
            
        # Known companies
        companies = [
            "Apple", "Microsoft", "Amazon", "Google", "Alphabet",
            "Meta", "Facebook", "Tesla", "NVIDIA", "Nvidia",
            "Berkshire Hathaway", "JPMorgan Chase", "JPMorgan",
            "Visa", "Mastercard", "Walmart", "UnitedHealth",
            "Johnson & Johnson", "Procter & Gamble", "P&G",
            "Home Depot", "Disney", "Bank of America", "BoA",
            "Goldman Sachs", "Morgan Stanley", "Citigroup", "Citi",
            "Wells Fargo", "Netflix", "Adobe", "Salesforce",
            "Oracle", "Intel", "AMD", "Cisco", "IBM",
            "Qualcomm", "Broadcom", "Texas Instruments", "TI",
            "ServiceNow", "Shopify", "Square", "Block",
            "PayPal", "Zoom", "Slack", "Atlassian", "Datadog",
            "Snowflake", "CrowdStrike", "Zscaler", "Okta",
            "MongoDB", "Elastic", "Confluent", "HashiCorp",
            "Coinbase", "Robinhood", "Affirm", "SoFi",
            "Palantir", "Airbnb", "Uber", "Lyft", "DoorDash",
            "Pinterest", "Snap", "Twitter", "X Corp",
            "TikTok", "ByteDance", "Tencent", "Alibaba",
            "Baidu", "JD.com", "Meituan", "Pinduoduo",
            "Toyota", "Volkswagen", "Volkswagen Group",
            "Ford", "General Motors", "GM", "Stellantis",
            "Mercedes-Benz", "Mercedes", "BMW", "Honda",
            "Hyundai", "Kia", "BYD", "NIO", "XPeng",
            "Li Auto", "Lucid", "Rivian", "Fisker",
            "ExxonMobil", "Exxon", "Chevron", "Shell",
            "BP", "TotalEnergies", "Total", "ConocoPhillips",
            "Saudi Aramco", "Aramco", "PetroChina",
            "Pfizer", "Moderna", "Johnson & Johnson", "J&J",
            "Merck", "AbbVie", "Amgen", "Gilead", "Biogen",
            "Regeneron", "Vertex", "Eli Lilly", "Lilly",
            "AstraZeneca", "Novartis", "Roche", "Sanofi",
            "GSK", "Sanofi", "Takeda", "Bristol Myers",
        ]
        
        company_patterns = [self.nlp.make_doc(c) for c in companies]
        self.phrase_matcher.add("KNOWN_COMPANY", company_patterns)
        
        # Known people
        people = [
            "Elon Musk", "Tim Cook", "Satya Nadella", "Sundar Pichai",
            "Mark Zuckerberg", "Jeff Bezos", "Andy Jassy",
            "Warren Buffett", "Charlie Munger",
            "Jamie Dimon", "David Solomon", "Jane Fraser",
            "Jensen Huang", "Lisa Su", "Pat Gelsinger",
            "Mary Barra", "Herbert Diess", "Ola Källenius",
            "Bernard Arnault", "Larry Ellison", "Larry Page", "Sergey Brin",
            "Bill Gates", "Steve Ballmer",
            "Cathie Wood", "Michael Burry", "Ray Dalio",
            "Jerome Powell", "Christine Lagarde", "Andrew Bailey",
            "Kazuo Ueda", "Yi Gang", "Tiff Macklem",
        ]
        
        people_patterns = [self.nlp.make_doc(p) for p in people]
        self.phrase_matcher.add("KNOWN_PERSON", people_patterns)
        
        logger.info("Phrase patterns initialized")
        
    def extract(self, text: str, context: Optional[EntityContext] = None) -> ExtractionResult:
        """
        Extract financial entities from text.
        
        Args:
            text: Input text to analyze
            context: Optional context for the extraction
            
        Returns:
            ExtractionResult with entities and relations
        """
        if not self._patterns_initialized:
            self.initialize()
            
        # Check cache
        if self.config.cache_enabled:
            cache_key = hashlib.md5(text.encode()).hexdigest()
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                cached.metadata["cached"] = True
                return cached
                
        start_time = datetime.utcnow()
        
        # Process with spaCy
        doc = self.nlp(text)
        
        # Extract entities from spaCy NER
        entities = self._extract_spacy_entities(doc)
        
        # Extract entities from custom matchers
        custom_entities = self._extract_custom_entities(doc)
        entities.extend(custom_entities)
        
        # Post-process: deduplicate, normalize, filter
        entities = self._post_process_entities(entities, doc)
        
        # Extract relations
        relations = self._extract_relations(doc, entities)
        
        # Create result
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        result = ExtractionResult(
            text=text,
            entities=entities,
            relations=relations,
            processing_time_ms=processing_time,
            model_version=f"spacy-{self.config.spacy_model}-financial-v1",
            metadata={
                "entity_count": len(entities),
                "relation_count": len(relations),
                "text_length": len(text),
            }
        )
        
        # Cache result
        if self.config.cache_enabled:
            self._cache[cache_key] = result
            
        return result
        
    def _extract_spacy_entities(self, doc: Doc) -> List[Entity]:
        """Extract entities from spaCy's built-in NER."""
        entities = []
        
        type_mapping = {
            "ORG": EntityType.ORGANIZATION,
            "PERSON": EntityType.PERSON,
            "GPE": EntityType.LOCATION,
            "LOC": EntityType.LOCATION,
            "DATE": EntityType.DATE,
            "TIME": EntityType.DATE,
            "MONEY": EntityType.MONEY,
            "PERCENT": EntityType.PERCENTAGE,
            "CARDINAL": EntityType.METRIC,
            "ORDINAL": EntityType.METRIC,
            "QUANTITY": EntityType.METRIC,
            "PRODUCT": EntityType.PRODUCT,
            "EVENT": EntityType.EVENT,
            "WORK_OF_ART": EntityType.PRODUCT,
            "LAW": EntityType.LEGAL_ENTITY,
            "LANGUAGE": EntityType.ORGANIZATION,
            "NORP": EntityType.ORGANIZATION,
            "FAC": EntityType.LOCATION,
        }
        
        for ent in doc.ents:
            entity_type = type_mapping.get(ent.label_, EntityType.ORGANIZATION)
            
            # Special handling for certain types
            if ent.label_ == "ORG":
                # Check if it's a known company
                entity_type = EntityType.COMPANY
            elif ent.label_ == "PERSON":
                # Check for titles
                entity_type = EntityType.PERSON
            elif ent.label_ == "MONEY":
                entity_type = EntityType.MONEY
            elif ent.label_ == "PERCENT":
                entity_type = EntityType.PERCENTAGE
                
            entity = Entity(
                text=ent.text,
                entity_type=entity_type,
                start_char=ent.start_char,
                end_char=ent.end_char,
                confidence=0.85,  # spaCy default confidence
                normalized_value=ent.text,
                metadata={"spacy_label": ent.label_},
            )
            
            # Try to normalize
            self._normalize_entity(entity, ent)
            
            entities.append(entity)
            
        return entities
        
    def _extract_custom_entities(self, doc: Doc) -> List[Entity]:
        """Extract entities using custom matchers."""
        entities = []
        
        # Matcher-based extraction
        if self.matcher:
            matches = self.matcher(doc)
            for match_id, start, end in matches:
                label = self.nlp.vocab.strings[match_id]
                span = doc[start:end]
                
                entity_type = self._map_matcher_label_to_type(label)
                sub_type = self._map_matcher_label_to_subtype(label)
                
                entity = Entity(
                    text=span.text,
                    entity_type=entity_type,
                    sub_type=sub_type,
                    start_char=span.start_char,
                    end_char=span.end_char,
                    confidence=0.9,
                    normalized_value=span.text,
                    metadata={"matcher_label": label},
                )
                
                self._normalize_entity(entity, span)
                entities.append(entity)
                
        # Phrase matcher extraction
        if self.phrase_matcher:
            matches = self.phrase_matcher(doc)
            for match_id, start, end in matches:
                label = self.nlp.vocab.strings[match_id]
                span = doc[start:end]
                
                if label == "KNOWN_COMPANY":
                    entity_type = EntityType.COMPANY
                    sub_type = EntitySubType.PUBLIC_COMPANY
                elif label == "KNOWN_PERSON":
                    entity_type = EntityType.PERSON
                    sub_type = EntitySubType.EXECUTIVE
                else:
                    entity_type = EntityType.ORGANIZATION
                    sub_type = None
                    
                entity = Entity(
                    text=span.text,
                    entity_type=entity_type,
                    sub_type=sub_type,
                    start_char=span.start_char,
                    end_char=span.end_char,
                    confidence=0.95,
                    normalized_value=span.text,
                    metadata={"phrase_matcher_label": label},
                )
                
                # Add known metadata
                if label == "KNOWN_COMPANY":
                    entity.metadata["known_company"] = True
                    entity.canonical_name = span.text
                elif label == "KNOWN_PERSON":
                    entity.metadata["known_person"] = True
                    
                entities.append(entity)
                
        return entities
        
    def _map_matcher_label_to_type(self, label: str) -> EntityType:
        """Map matcher label to entity type."""
        mapping = {
            "TICKER": EntityType.TICKER,
            "MONEY": EntityType.MONEY,
            "PERCENTAGE": EntityType.PERCENTAGE,
            "DATE": EntityType.DATE,
            "COMPANY": EntityType.COMPANY,
            "EXCHANGE": EntityType.EXCHANGE,
            "INDEX": EntityType.INDEX,
            "CENTRAL_BANK": EntityType.CENTRAL_BANK,
            "REGULATOR": EntityType.REGULATOR,
            "CRYPTOCURRENCY": EntityType.CRYPTOCURRENCY,
            "COMMODITY": EntityType.COMMODITY,
            "EVENT": EntityType.EVENT,
            "SECTOR": EntityType.SECTOR,
            "PERSON_TITLE": EntityType.PERSON,
        }
        return mapping.get(label, EntityType.ORGANIZATION)
        
    def _map_matcher_label_to_subtype(self, label: str) -> Optional[EntitySubType]:
        """Map matcher label to entity sub-type."""
        mapping = {
            "PERSON_TITLE": EntitySubType.EXECUTIVE,
        }
        return mapping.get(label)
        
    def _normalize_entity(self, entity: Entity, span: Span) -> None:
        """Normalize entity value and add metadata."""
        text = entity.text.strip()
        
        if entity.entity_type == EntityType.TICKER:
            # Normalize ticker
            entity.normalized_value = text.replace("$", "").upper()
            entity.ticker = entity.normalized_value
            entity.canonical_name = text
            
        elif entity.entity_type == EntityType.MONEY:
            # Extract numeric value and currency
            entity.normalized_value = text
            # Extract numeric value
            money_match = re.search(r'[\d,]+\.?\d*', text.replace(",", ""))
            if money_match:
                entity.numeric_value = float(money_match.group())
            # Extract currency
            if text.startswith("$"):
                entity.currency = "USD"
            elif text.startswith("€"):
                entity.currency = "EUR"
            elif text.startswith("£"):
                entity.currency = "GBP"
            elif "USD" in text.upper():
                entity.currency = "USD"
            elif "EUR" in text.upper():
                entity.currency = "EUR"
            elif "GBP" in text.upper():
                entity.currency = "GBP"
                
        elif entity.entity_type == EntityType.PERCENTAGE:
            # Extract numeric value
            entity.normalized_value = text
            pct_match = re.search(r'[\d.]+', text)
            if pct_match:
                entity.numeric_value = float(pct_match.group())
            entity.unit = "%"
                
        elif entity.entity_type == EntityType.DATE:
            entity.normalized_value = text
            
        elif entity.entity_type == EntityType.TICKER:
            entity.normalized_value = text.replace("$", "").upper()
            entity.ticker = entity.normalized_value
            
        elif entity.entity_type == EntityType.COMPANY:
            entity.canonical_name = text
            # Check for ticker in text
            ticker_match = re.search(r'\$([A-Z]{1,5})\b', text)
            if ticker_match:
                entity.ticker = ticker_match.group(1)
                
        elif entity.entity_type == EntityType.INDEX:
            entity.canonical_name = text
            
        elif entity.entity_type == EntityType.CRYPTOCURRENCY:
            entity.normalized_value = text.upper()
            entity.ticker = text.upper()
            
        elif entity.entity_type == EntityType.COMMODITY:
            entity.canonical_name = text
            
        # Add context from span
        if span.sent:
            entity.metadata["sentence"] = span.sent.text
            
    def _post_process_entities(self, entities: List[Entity], doc: Doc) -> List[Entity]:
        """Post-process entities: deduplicate, merge, filter."""
        if not entities:
            return []
            
        # Sort by start position
        entities.sort(key=lambda e: (e.start_char, -e.confidence))
        
        # Deduplicate overlapping entities (keep higher confidence)
        deduplicated = []
        for entity in entities:
            overlap = False
            for existing in deduplicated:
                if (entity.start_char < existing.end_char and 
                    entity.end_char > existing.start_char):
                    # Overlap detected
                    if entity.confidence > existing.confidence:
                        # Replace existing with higher confidence
                        deduplicated.remove(existing)
                    else:
                        overlap = True
                        break
            if not overlap:
                deduplicated.append(entity)
                
        # Filter by confidence threshold
        filtered = [e for e in deduplicated if e.confidence >= self.config.confidence_threshold]
        
        # Limit number of entities
        if len(filtered) > self.config.max_entities_per_doc:
            filtered = filtered[:self.config.max_entities_per_doc]
            
        # Add canonical names for companies
        for entity in filtered:
            if entity.entity_type == EntityType.COMPANY and not entity.canonical_name:
                entity.canonical_name = entity.text
            if entity.entity_type == EntityType.TICKER and not entity.ticker:
                entity.ticker = entity.text.replace("$", "").upper()
                
        return filtered
        
    def _extract_relations(self, doc: Doc, entities: List[Entity]) -> List[EntityRelation]:
        """Extract relationships between entities."""
        relations = []
        
        # Map entity IDs to entities
        entity_map = {e.id: e for e in entities}
        
        # Simple proximity-based relations
        for i, ent1 in enumerate(entities):
            for ent2 in entities[i+1:]:
                # Check proximity
                distance = abs(ent1.start_char - ent2.start_char)
                if distance > 200:
                    continue
                    
                # Determine relation type based on entity types
                relation_type = self._infer_relation_type(entities[i], ent2)
                if relation_type:
                    confidence = max(0.5, 1.0 - (distance / 200))
                    relation = EntityRelation(
                        source_entity_id=entities[i].id,
                        target_entity_id=ent2.id,
                        relation_type=relation_type,
                        confidence=confidence,
                        metadata={"distance_chars": distance},
                    )
                    relations.append(relation)
                    
        # Dependency-based relations (using spaCy's dependency parse)
        for token in doc:
            if token.dep_ in ("nsubj", "dobj", "pobj", "attr", "appos"):
                head_ent = self._find_entity_for_token(entities, token.head)
                child_ent = self._find_entity_for_token(entities, token)
                if head_ent and child_ent and head_ent.id != child_ent.id:
                    relation_type = self._map_dep_to_relation(token.dep_)
                    if relation_type:
                        relation = EntityRelation(
                            source_entity_id=head_ent.id,
                            target_entity_id=child_ent.id,
                            relation_type=relation_type,
                            confidence=0.7,
                            metadata={"dependency": token.dep_},
                        )
                        relations.append(relation)
                        
        return relations
        
    def _find_entity_for_token(self, entities: List[Entity], token) -> Optional[Entity]:
        """Find entity that contains the given token."""
        for entity in entities:
            if entity.start_char <= token.idx < entity.end_char:
                return entity
        return None
        
    def _infer_relation_type(self, ent1: Entity, ent2: Entity) -> Optional[str]:
        """Infer relation type from entity types."""
        type_pair = (ent1.entity_type, ent2.entity_type)
        
        # Company - Person relations
        if ent1.entity_type == EntityType.COMPANY and ent2.entity_type == EntityType.PERSON:
            return "has_executive"
        if ent1.entity_type == EntityType.PERSON and ent2.entity_type == EntityType.COMPANY:
            return "works_at"
            
        # Company - Ticker
        if (ent1.entity_type == EntityType.COMPANY and ent2.entity_type == EntityType.TICKER) or \
           (ent1.entity_type == EntityType.TICKER and ent2.entity_type == EntityType.COMPANY):
            return "has_ticker"
            
        # Company - Money/Percentage
        if ent1.entity_type == EntityType.COMPANY and ent2.entity_type in (EntityType.MONEY, EntityType.PERCENTAGE):
            return "reports"
        if ent2.entity_type == EntityType.COMPANY and ent1.entity_type in (EntityType.MONEY, EntityType.PERCENTAGE):
            return "reported_by"
            
        # Company - Event
        if ent1.entity_type == EntityType.COMPANY and ent2.entity_type == EntityType.EVENT:
            return "involved_in"
        if ent2.entity_type == EntityType.COMPANY and ent1.entity_type == EntityType.EVENT:
            return "involves"
            
        # Person - Title
        if ent1.entity_type == EntityType.PERSON and ent2.entity_type == EntityType.PERSON and ent2.sub_type == EntitySubType.EXECUTIVE:
            return "has_title"
            
        return None
        
    def _map_dep_to_relation(self, dep: str) -> Optional[str]:
        """Map spaCy dependency to relation type."""
        mapping = {
            "nsubj": "subject_of",
            "dobj": "object_of",
            "pobj": "object_of_preposition",
            "attr": "attribute_of",
            "appos": "apposition_of",
            "compound": "compound_with",
            "nmod": "modifier_of",
            "amod": "adjectival_modifier_of",
            "advmod": "adverbial_modifier_of",
        }
        return mapping.get(dep)
        
    def extract_batch(self, texts: List[str], contexts: Optional[List[EntityContext]] = None) -> List[ExtractionResult]:
        """Extract entities from multiple texts efficiently."""
        if contexts is None:
            contexts = [None] * len(texts)
            
        results = []
        for text, context in zip(texts, contexts):
            result = self.extract(text, context)
            results.append(result)
        return results
        
    def clear_cache(self) -> None:
        """Clear the extraction cache."""
        self._cache.clear()
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self._cache),
            "cache_enabled": self.config.cache_enabled,
        }


# Convenience function
def extract_entities(text: str, config: Optional[RecognizerConfig] = None) -> ExtractionResult:
    """Convenience function for single extraction."""
    recognizer = FinancialEntityRecognizer(config)
    return recognizer.extract(text)


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test text
    test_text = """
    Apple Inc. (AAPL) reported record quarterly revenue of $89.5 billion, 
    up 8% year-over-year. CEO Tim Cook highlighted strong iPhone 15 sales 
    and Services growth. The company's Services revenue reached an all-time 
    high of $21.2 billion. The stock rose 2.5% in after-hours trading on 
    NASDAQ. The Federal Reserve's latest decision on interest rates may 
    impact tech stocks. Bitcoin (BTC) traded at $45,000. Gold futures 
    reached $2,100. The S&P 500 gained 1.2%.
    """
    
    recognizer = FinancialEntityRecognizer()
    result = recognizer.extract(test_text)
    
    print(f"Entities found: {len(result.entities)}")
    print(f"Relations found: {len(result.relations)}")
    print(f"Processing time: {result.processing_time_ms:.1f}ms")
    print()
    
    for entity in result.entities:
        print(f"  {entity.text} ({entity.entity_type.value}", end="")
        if entity.sub_type:
            print(f", {entity.sub_type.value}", end="")
        print(f") - confidence: {entity.confidence:.2f}")
        if entity.numeric_value is not None:
            print(f"    value: {entity.numeric_value} {entity.unit or entity.currency or ''}")
        if entity.ticker:
            print(f"    ticker: {entity.ticker}")
        if entity.canonical_name:
            print(f"    canonical: {entity.canonical_name}")
            
    print("\nRelations:")
    for rel in result.relations:
        src = next((e for e in result.entities if e.id == rel.source_entity_id), None)
        tgt = next((e for e in result.entities if e.id == rel.target_entity_id), None)
        if src and tgt:
            print(f"  {src.text} --[{rel.relation_type}]--> {tgt.text} (conf: {rel.confidence:.2f})")