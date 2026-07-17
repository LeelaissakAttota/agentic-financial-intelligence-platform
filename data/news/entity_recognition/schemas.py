"""
Financial Entity Recognition Schemas

Defines entity types and schemas for financial news entity extraction.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
from datetime import datetime


class EntityType(str, Enum):
    """Types of financial entities that can be extracted."""
    COMPANY = "company"
    TICKER = "ticker"
    PERSON = "person"
    MONEY = "money"
    PERCENTAGE = "percentage"
    DATE = "date"
    INDEX = "index"
    CURRENCY = "currency"
    COMMODITY = "commodity"
    CRYPTOCURRENCY = "cryptocurrency"
    SECTOR = "sector"
    REGULATOR = "regulator"
    EXCHANGE = "exchange"
    FINANCIAL_INSTRUMENT = "financial_instrument"
    ECONOMIC_INDICATOR = "economic_indicator"
    CENTRAL_BANK = "central_bank"
    GOVERNMENT_ENTITY = "government_entity"
    LEGAL_ENTITY = "legal_entity"
    EVENT = "event"
    LOCATION = "location"
    ORGANIZATION = "organization"
    PRODUCT = "product"
    TECHNOLOGY = "technology"
    METRIC = "metric"
    COUNTRY = "country"
    CITY = "city"
    INDUSTRY = "industry"
    FUND = "fund"
    UNKNOWN = "unknown"


class EntitySubType(str, Enum):
    """Sub-types for more granular classification."""
    # Company sub-types
    PUBLIC_COMPANY = "public_company"
    PRIVATE_COMPANY = "private_company"
    SUBSIDIARY = "subsidiary"
    JOINT_VENTURE = "joint_venture"
    STARTUP = "startup"
    HOLDING_COMPANY = "holding_company"
    INVESTMENT_FUND = "investment_fund"
    VENTURE_CAPITAL = "venture_capital"
    PRIVATE_EQUITY = "private_equity"
    ASSET_MANAGER = "asset_manager"
    BROKER_DEALER = "broker_dealer"
    CLEARING_HOUSE = "clearing_house"
    CUSTODIAN = "custodian"
    INSURANCE_COMPANY = "insurance_company"
    BANK = "bank"
    
    # Person sub-types
    CEO = "ceo"
    CFO = "cfo"
    CTO = "cto"
    CXO = "cxo"
    PRESIDENT = "president"
    CHAIRMAN = "chairman"
    FOUNDER = "founder"
    CO_FOUNDER = "co_founder"
    INVESTOR = "investor"
    ANALYST = "analyst"
    PORTFOLIO_MANAGER = "portfolio_manager"
    DIRECTOR = "director"
    
    # Ticker sub-types
    US_EQUITY = "us_equity"
    INTERNATIONAL_EQUITY = "international_equity"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    OPTION = "option"
    FUTURE = "future"
    WARRANT = "warrant"
    RIGHT = "right"
    UNIT = "unit"
    PREFERRED = "preferred"
    
    # Money sub-types
    REVENUE = "revenue"
    PROFIT = "profit"
    NET_INCOME = "net_income"
    OPERATING_INCOME = "operating_income"
    EBITDA = "ebitda"
    EPS = "eps"
    MARKET_CAP = "market_cap"
    ENTERPRISE_VALUE = "enterprise_value"
    INVESTMENT = "investment"
    FUNDING = "funding"
    DIVIDEND = "dividend"
    BUYBACK = "buyback"
    DEBT = "debt"
    CASH = "cash"
    ASSETS = "assets"
    LIABILITIES = "liabilities"
    FREE_CASH_FLOW = "free_cash_flow"
    PRICE_TARGET = "price_target"
    
    # Percentage sub-types
    GROWTH_RATE = "growth_rate"
    MARGIN = "margin"
    YIELD = "yield"
    RETURN = "return"
    CHANGE = "change"
    VOLATILITY = "volatility"
    BASIS_POINTS = "basis_points"
    
    # Currency sub-types
    CURRENCY = "currency"
    
    # Date sub-types
    EARNINGS_DATE = "earnings_date"
    EX_DIVIDEND_DATE = "ex_dividend_date"
    ANNOUNCEMENT_DATE = "announcement_date"
    EFFECTIVE_DATE = "effective_date"
    EXPIRATION_DATE = "expiration_date"
    FISCAL_YEAR = "fiscal_year"
    FINANCIAL_QUARTER = "financial_quarter"
    CALENDAR_YEAR = "calendar_year"
    MONTH_YEAR = "month_year"
    SPECIFIC_DATE = "specific_date"
    
    # Event sub-types
    EARNINGS_RELEASE = "earnings_release"
    MERGER_ACQUISITION = "merger_acquisition"
    IPO = "ipo"
    SECONDARY_OFFERING = "secondary_offering"
    STOCK_SPLIT = "stock_split"
    DIVIDEND_ANNOUNCEMENT = "dividend_announcement"
    BUYBACK_ANNOUNCEMENT = "buyback_announcement"
    GUIDANCE = "guidance"
    ANALYST_RATING = "analyst_rating"
    REGULATORY_FILING = "regulatory_filing"
    LAWSUIT = "lawsuit"
    PRODUCT_LAUNCH = "product_launch"
    PARTNERSHIP = "partnership"
    RESTRUCTURING = "restructuring"
    LAYOFFS = "layoffs"
    BANKRUPTCY = "bankruptcy"
    INTEREST_RATE_DECISION = "interest_rate_decision"
    INFLATION = "inflation"
    ECONOMIC_REPORT = "economic_report"
    CREDIT_RATING_CHANGE = "credit_rating_change"
    
    # Metric sub-types
    REVENUE_METRIC = "revenue"
    EPS_METRIC = "eps"
    EBITDA_METRIC = "ebitda"
    NET_INCOME_METRIC = "net_income"
    OPERATING_INCOME_METRIC = "operating_income"
    GROSS_MARGIN = "gross_margin"
    OPERATING_MARGIN = "operating_margin"
    NET_MARGIN = "net_margin"
    FREE_CASH_FLOW_METRIC = "free_cash_flow"
    TOTAL_ASSETS = "total_assets"
    TOTAL_DEBT = "total_debt"
    MARKET_CAP_METRIC = "market_cap"
    ENTERPRISE_VALUE_METRIC = "enterprise_value"
    PE_RATIO = "pe_ratio"
    PEG_RATIO = "peg_ratio"
    DIVIDEND_YIELD = "dividend_yield"
    CREDIT_RATING = "credit_rating"
    
    # Cryptocurrency sub-types
    COIN = "coin"
    TOKEN = "token"
    STABLECOIN = "stablecoin"
    DEFI_TOKEN = "defi_token"
    NFT = "nft"
    
    # Index sub-types
    MARKET_INDEX = "market_index"
    SECTOR_INDEX = "sector_index"
    VOLATILITY_INDEX = "volatility_index"
    
    # Regulatory sub-types
    SECURITIES_REGULATOR = "securities_regulator"
    BANKING_REGULATOR = "banking_regulator"
    COMMODITIES_REGULATOR = "commodities_regulator"
    
    # Regulation sub-types
    REGULATION = "regulation"
    
    # Country sub-types
    SOVEREIGN = "sovereign"
    
    # City sub-types
    FINANCIAL_CENTER = "financial_center"
    
    # Industry sub-types
    SECTOR = "sector"
    INDUSTRY_GROUP = "industry_group"
    INDUSTRY = "industry"
    SUB_INDUSTRY = "sub_industry"
    
    # Product sub-types
    HARDWARE = "hardware"
    SOFTWARE = "software"
    SERVICE = "service"
    PLATFORM = "platform"
    
    # Commodity sub-types
    PRECIOUS_METAL = "precious_metal"
    BASE_METAL = "base_metal"
    ENERGY = "energy"
    AGRICULTURE = "agriculture"
    LIVESTOCK = "livestock"
    
    # Fund sub-types
    HEDGE_FUND = "hedge_fund"
    PENSION_FUND = "pension_fund"
    SOVEREIGN_WEALTH_FUND = "sovereign_wealth_fund"
    
    # Exchange sub-types
    STOCK_EXCHANGE = "stock_exchange"
    CRYPTO_EXCHANGE = "crypto_exchange"
    FUTURES_EXCHANGE = "futures_exchange"
    OPTIONS_EXCHANGE = "options_exchange"


class RelationshipType(str, Enum):
    """Types of relationships between entities."""
    # Company relationships
    HAS_CEO = "has_ceo"
    HAS_CFO = "has_cfo"
    HAS_EXECUTIVE = "has_executive"
    HAS_FOUNDER = "has_founder"
    HAS_TICKER = "has_ticker"
    LISTED_ON = "listed_on"
    HEADQUARTERED_IN = "headquartered_in"
    OPERATES_IN = "operates_in"
    PRODUCES = "produces"
    COMPETES_WITH = "competes_with"
    PARTNERS_WITH = "partners_with"
    SUBSIDIARY_OF = "subsidiary_of"
    PARENT_OF = "parent_of"
    ACQUIRED = "acquired"
    ACQUIRED_BY = "acquired_by"
    MERGED_WITH = "merged_with"
    INVESTED_IN = "invested_in"
    INVESTED_BY = "invested_by"
    REPORTED = "reported"
    INVOLVED_IN = "involved_in"
    SUPPLIES = "supplies"
    CUSTOMER_OF = "customer_of"
    
    # Person relationships
    WORKS_AT = "works_at"
    FOUNDED = "founded"
    INVESTED_IN_PERSON = "invested_in"
    SERVES_ON_BOARD = "serves_on_board"
    FORMER_EMPLOYEE = "former_employee"
    
    # Ticker relationships
    TRADES_ON = "trades_on"
    COMPONENT_OF = "component_of"
    TRACKS = "tracks"
    
    # Financial relationships
    DENOMINATED_IN = "denominated_in"
    PEGGED_TO = "pegged_to"
    CONVERTIBLE_TO = "convertible_to"
    UNDERLYING = "underlying"
    DERIVATIVE_OF = "derivative_of"
    
    # Index relationships
    HAS_COMPONENT = "has_component"
    WEIGHTS = "weights"
    
    # General
    RELATED_TO = "related_to"
    MENTIONED_WITH = "mentioned_with"
    SAME_AS = "same_as"
    ALIAS_OF = "alias_of"


class ConfidenceLevel(str, Enum):
    """Confidence levels for extracted entities."""
    VERY_HIGH = "very_high"   # 0.9 - 1.0
    HIGH = "high"             # 0.75 - 0.9
    MEDIUM = "medium"         # 0.6 - 0.75
    LOW = "low"               # 0.4 - 0.6
    VERY_LOW = "very_low"     # 0.0 - 0.4


class ValidationMethod(str, Enum):
    """Method used to validate an entity."""
    REGEX = "regex"
    DICTIONARY = "dictionary"
    LOCAL_NER = "local_ner"
    LLM = "llm"
    RULE_BASED = "rule_based"
    HYBRID = "hybrid"
    TICKER_RESOLVER = "ticker_resolver"
    COMPANY_RESOLVER = "company_resolver"
    ALIAS_RESOLVER = "alias_resolver"
    CROSS_REFERENCE = "cross_reference"
    MANUAL = "manual"


@dataclass
class Entity:
    """Represents a recognized financial entity."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    entity_type: EntityType = EntityType.UNKNOWN
    sub_type: Optional[EntitySubType] = None
    start_char: int = 0
    end_char: int = 0
    confidence: float = 0.0
    normalized_value: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Relationships
    related_entities: List[str] = field(default_factory=list)
    
    # Normalization
    canonical_name: Optional[str] = None
    ticker: Optional[str] = None
    cik: Optional[str] = None
    lei: Optional[str] = None
    isin: Optional[str] = None
    
    # For money/percentage entities
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    currency: Optional[str] = None
    timeframe: Optional[str] = None
    
    # Validation
    validation_method: Optional[ValidationMethod] = None
    validation_details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def entity_id(self) -> str:
        return self.id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary."""
        return {
            "id": self.id,
            "text": self.text,
            "entity_type": self.entity_type.value,
            "sub_type": self.sub_type.value if self.sub_type else None,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "confidence": self.confidence,
            "normalized_value": self.normalized_value,
            "metadata": self.metadata,
            "related_entities": self.related_entities,
            "canonical_name": self.canonical_name,
            "ticker": self.ticker,
            "cik": self.cik,
            "lei": self.lei,
            "isin": self.isin,
            "numeric_value": self.numeric_value,
            "unit": self.unit,
            "currency": self.currency,
            "timeframe": self.timeframe,
            "validation_method": self.validation_method.value if self.validation_method else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        """Create entity from dictionary."""
        entity = cls(
            id=data.get("id", str(uuid.uuid4())),
            text=data.get("text", ""),
            entity_type=EntityType(data.get("entity_type", "unknown")),
            start_char=data.get("start_char", 0),
            end_char=data.get("end_char", 0),
            confidence=data.get("confidence", 0.0),
            normalized_value=data.get("normalized_value"),
            metadata=data.get("metadata", {}),
            related_entities=data.get("related_entities", []),
            canonical_name=data.get("canonical_name"),
            ticker=data.get("ticker"),
            cik=data.get("cik"),
            lei=data.get("lei"),
            isin=data.get("isin"),
            numeric_value=data.get("numeric_value"),
            unit=data.get("unit"),
            currency=data.get("currency"),
            timeframe=data.get("timeframe"),
        )
        if data.get("sub_type"):
            entity.sub_type = EntitySubType(data["sub_type"])
        if data.get("validation_method"):
            entity.validation_method = ValidationMethod(data["validation_method"])
        return entity


@dataclass
class EntityRelationship:
    """Represents a relationship between two entities."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_entity_id: str = ""
    target_entity_id: str = ""
    relationship_type: RelationshipType = RelationshipType.RELATED_TO
    confidence: float = 0.0
    evidence: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "relationship_type": self.relationship_type.value,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityRelationship":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            source_entity_id=data.get("source_entity_id", ""),
            target_entity_id=data.get("target_entity_id", ""),
            relationship_type=RelationshipType(data.get("relationship_type", "related_to")),
            confidence=data.get("confidence", 0.0),
            evidence=data.get("evidence", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class EntityExtractionResult:
    """Result of entity extraction from text."""
    text: str = ""
    entities: List[Entity] = field(default_factory=list)
    relationships: List[EntityRelationship] = field(default_factory=list)
    entities_by_type: Dict[EntityType, List[Entity]] = field(default_factory=dict)
    confidence_summary: Dict[str, Any] = field(default_factory=dict)
    extraction_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    text_length: int = 0
    config_used: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text[:1000] if len(self.text) > 1000 else self.text,
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
            "entities_by_type": {
                k.value: [e.to_dict() for e in v] 
                for k, v in self.entities_by_type.items()
            },
            "confidence_summary": self.confidence_summary,
            "extraction_time_ms": self.extraction_time_ms,
            "metadata": self.metadata,
            "text_length": self.text_length,
        }


@dataclass
class ExtractionConfig:
    """Configuration for entity extraction."""
    confidence_threshold: float = 0.5
    entity_types: Optional[List[EntityType]] = None
    enable_relationships: bool = True
    max_entities: int = 500
    max_relationships: int = 200
    llm_validation_threshold: float = 0.7
    include_context: bool = True
    context_window: int = 200


# Confidence factor classes
@dataclass
class ConfidenceFactor:
    """A single confidence factor."""
    signal: str
    weight: float
    value: float
    description: str
    
    @property
    def contribution(self) -> float:
        return self.weight * self.value


@dataclass
class ConfidenceFactors:
    """Breakdown of confidence calculation."""
    base_confidence: float = 0.0
    method_bonus: float = 0.0
    dictionary_bonus: float = 0.0
    llm_bonus: float = 0.0
    context_bonus: float = 0.0
    cross_ref_bonus: float = 0.0
    position_bonus: float = 0.0
    duplicate_penalty: float = 0.0
    final_confidence: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.VERY_LOW

    def dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "base_confidence": self.base_confidence,
            "method_bonus": self.method_bonus,
            "dictionary_bonus": self.dictionary_bonus,
            "llm_bonus": self.llm_bonus,
            "context_bonus": self.context_bonus,
            "cross_ref_bonus": self.cross_ref_bonus,
            "position_bonus": self.position_bonus,
            "duplicate_penalty": self.duplicate_penalty,
            "final_confidence": self.final_confidence,
            "confidence_level": self.confidence_level.value
        }


# Type aliases
EntityID = str
Position = tuple[int, int]

# For backward compatibility
CompanyResolution = None
TickerResolution = None
AliasResolution = None
ExtractionPipelineConfig = None