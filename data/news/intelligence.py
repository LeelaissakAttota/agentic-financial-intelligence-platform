"""
Company News Intelligence - Extract financial entities and events from news articles
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Set, Any, Tuple
from collections import defaultdict

from data.news.schemas import (
    NewsArticle, NewsCategory, NewsSource, SentimentLabel,
    ArticleSentiment, CompanyMention, PersonMention, EventDetection,
    NewsCategory as EventType
)
from data.news.entity_recognition import (
    get_entity_extractor, ExtractionPipelineConfig,
    EntityType, EntitySubType, RelationshipType, Entity,
    FinancialEntityExtractor, EntityExtractionResult
)

logger = logging.getLogger(__name__)


# Financial event patterns
EARNINGS_PATTERNS = [
    r'\b(earnings|results|quarterly|Q[1-4]\s*\d{2,4})\b',
    r'\b(revenue|sales|profit|EPS|earnings per share)\b',
    r'\b(beat|miss|exceeded|fell short|guidance)\b',
    r'\b(quarter|fiscal)\s+(year|Q[1-4])\b',
]

MERGER_ACQUISITION_PATTERNS = [
    r'\b(merger|acquisition|acquire|buyout|takeover)\b',
    r'\b(merger of equals|hostile bid|tender offer)\b',
    r'\b(spin.?off|divestiture|asset sale)\b',
]

PRODUCT_LAUNCH_PATTERNS = [
    r'\b(launch|unveil|introduce|debut|release|announce)\b',
    r'\b(new product|next.?gen|next generation)\b',
    r'\b(platform|service|solution|feature)\b',
]

PARTNERSHIP_PATTERNS = [
    r'\b(partnership|collaboration|alliance|joint venture)\b',
    r'\b(strategic partnership|technology partnership)\b',
    r'\b(partner with|team up with|work with)\b',
]

LAWSUIT_PATTERNS = [
    r'\b(lawsuit|litigation|sued|legal action)\b',
    r'\b(class action|patent infringement|antitrust)\b',
    r'\b(settlement|settled|court ruling)\b',
]

REGULATORY_PATTERNS = [
    r'\b(SEC|FTC|DOJ|CFTC|FDA|regulator|regulation)\b',
    r'\b(investigation|probe|enforcement|compliance)\b',
    r'\b(fine|penalty|sanction|consent order)\b',
]

MANAGEMENT_CHANGE_PATTERNS = [
    r'\b(CEO|CFO|CTO|COO|president|chairman)\b',
    r'\b(appointed|resigned|retired|stepped down|named)\b',
    r'\b(new|former|interim)\s+(CEO|CFO|CTO)\b',
]

DIVIDEND_PATTERNS = [
    r'\b(dividend|dividends|payout|yield)\b',
    r'\b(declared|increased|cut|suspended)\b',
    r'\b(ex.?dividend|record date|payment date)\b',
]

STOCK_SPLIT_PATTERNS = [
    r'\b(stock split|reverse split|share split)\b',
    r'\b(\d+[-:]?for[-:]?\d+)\b',
]

INSIDER_TRADING_PATTERNS = [
    r'\b(insider|executive|director)\b.*\b(bought|sold|purchased|sold)\b',
    r'\b(Form 4|SEC Form 4|Section 16)\b',
]

ANALYST_RATING_PATTERNS = [
    r'\b(upgrade|downgrade|initiated|reiterated)\b',
    r'\b(buy|sell|hold|overweight|underweight|outperform|underperform)\b',
    r'\b(price target|target price)\s*\$?\d+',
]

@dataclass
class IntelligenceConfig:
    """Configuration for news intelligence extraction."""
    # Entity extraction
    enable_entity_extraction: bool = True
    extraction_confidence_threshold: float = 0.5
    
    # Event detection
    enable_event_detection: bool = True
    event_confidence_threshold: float = 0.4
    
    # Specific event types
    detect_earnings: bool = True
    detect_mergers: bool = True
    detect_products: bool = True
    detect_partnerships: bool = True
    detect_lawsuits: bool = True
    detect_regulatory: bool = True
    detect_management_changes: bool = True
    detect_dividends: bool = True
    detect_splits: bool = True
    detect_insider_trading: bool = True
    detect_analyst_ratings: bool = True
    
    # Company resolution
    resolve_company_names: bool = True
    resolve_tickers: bool = True
    resolve_people: bool = True
    
    # Enrichment
    enrich_with_metadata: bool = True
    calculate_impact_scores: bool = True


@dataclass
class CompanyIntelligence:
    """Intelligence extracted for a company."""
    name: str
    ticker: Optional[str] = None
    mention_count: int = 0
    is_primary: bool = False
    sentiment: Optional[float] = None  # -1 to 1
    
    # Events
    earnings_events: List[EventDetection] = field(default_factory=list)
    ma_events: List[EventDetection] = field(default_factory=list)
    product_events: List[EventDetection] = field(default_factory=list)
    partnership_events: List[EventDetection] = field(default_factory=list)
    lawsuit_events: List[EventDetection] = field(default_factory=list)
    regulatory_events: List[EventDetection] = field(default_factory=list)
    management_events: List[EventDetection] = field(default_factory=list)
    dividend_events: List[EventDetection] = field(default_factory=list)
    split_events: List[EventDetection] = field(default_factory=list)
    insider_events: List[EventDetection] = field(default_factory=list)
    analyst_events: List[EventDetection] = field(default_factory=list)
    
    # People
    executives: List[PersonMention] = field(default_factory=list)
    
    # Products
    products: List[str] = field(default_factory=list)
    
    # Metadata
    sources: Set[str] = field(default_factory=set)
    first_mention: Optional[datetime] = None
    last_mention: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "ticker": self.ticker,
            "mention_count": self.mention_count,
            "is_primary": self.is_primary,
            "sentiment": self.sentiment,
            "events": {
                "earnings": len(self.earnings_events),
                "mergers_acquisitions": len(self.ma_events),
                "product_launches": len(self.product_events),
                "partnerships": len(self.partnership_events),
                "lawsuits": len(self.lawsuit_events),
                "regulatory": len(self.regulatory_events),
                "management_changes": len(self.management_events),
                "dividends": len(self.dividend_events),
                "stock_splits": len(self.split_events),
                "insider_trading": len(self.insider_events),
                "analyst_ratings": len(self.analyst_events),
            },
            "executives": [p.name for p in self.executives],
            "products": self.products,
            "sources": list(self.sources),
            "first_mention": self.first_mention.isoformat() if self.first_mention else None,
            "last_mention": self.last_mention.isoformat() if self.last_mention else None,
        }


@dataclass
class ArticleIntelligence:
    """Full intelligence extracted from an article."""
    article: NewsArticle
    companies: List[CompanyIntelligence] = field(default_factory=list)
    people: List[PersonMention] = field(default_factory=list)
    products: List[str] = field(default_factory=list)
    events: List[EventDetection] = field(default_factory=list)
    key_metrics: Dict[str, Any] = field(default_factory=dict)
    risk_factors: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "article": {
                "title": self.article.title,
                "url": self.article.url,
                "source": self.article.source.value,
                "published_at": self.article.published_at.isoformat(),
            },
            "companies": [c.to_dict() for c in self.companies],
            "people": [{"name": p.name, "role": p.role, "company": p.company} for p in self.people],
            "products": self.products,
            "events": [
                {
                    "type": e.event_type.value,
                    "confidence": e.confidence,
                    "details": e.details
                } for e in self.events
            ],
            "key_metrics": self.key_metrics,
            "risk_factors": self.risk_factors,
            "opportunities": self.opportunities,
            "summary": self.summary,
        }


class FinancialEventDetector:
    """Detects specific financial events from article text."""
    
    def __init__(self, config: IntelligenceConfig):
        self.config = config
        self._compile_patterns()
        
    def _compile_patterns(self):
        """Compile regex patterns for event detection."""
        self.patterns = {}
        
        if self.config.detect_earnings:
            self.patterns['earnings'] = [
                re.compile(p, re.IGNORECASE) for p in EARNINGS_PATTERNS
            ]
        if self.config.detect_mergers:
            self.patterns['ma'] = [
                re.compile(p, re.IGNORECASE) for p in MERGER_ACQUISITION_PATTERNS
            ]
        if self.config.detect_products:
            self.patterns['product'] = [
                re.compile(p, re.IGNORECASE) for p in PRODUCT_LAUNCH_PATTERNS
            ]
        if self.config.detect_partnerships:
            self.patterns['partnership'] = [
                re.compile(p, re.IGNORECASE) for p in PARTNERSHIP_PATTERNS
            ]
        if self.config.detect_lawsuits:
            self.patterns['lawsuit'] = [
                re.compile(p, re.IGNORECASE) for p in LAWSUIT_PATTERNS
            ]
        if self.config.detect_regulatory:
            self.patterns['regulatory'] = [
                re.compile(p, re.IGNORECASE) for p in REGULATORY_PATTERNS
            ]
        if self.config.detect_management_changes:
            self.patterns['management'] = [
                re.compile(p, re.IGNORECASE) for p in MANAGEMENT_CHANGE_PATTERNS
            ]
        if self.config.detect_dividends:
            self.patterns['dividend'] = [
                re.compile(p, re.IGNORECASE) for p in DIVIDEND_PATTERNS
            ]
        if self.config.detect_splits:
            self.patterns['split'] = [
                re.compile(p, re.IGNORECASE) for p in STOCK_SPLIT_PATTERNS
            ]
        if self.config.detect_insider_trading:
            self.patterns['insider'] = [
                re.compile(p, re.IGNORECASE) for p in INSIDER_TRADING_PATTERNS
            ]
        if self.config.detect_analyst_ratings:
            self.patterns['analyst'] = [
                re.compile(p, re.IGNORECASE) for p in ANALYST_RATING_PATTERNS
            ]
            
    def detect_events(
        self, 
        title: str, 
        summary: str, 
        content: Optional[str] = None
    ) -> List[EventDetection]:
        """Detect financial events from article text."""
        text = f"{title} {summary}"
        if content:
            text += f" {content[:2000]}"  # Limit content for performance
            
        events = []
        
        # Map pattern categories to event types
        event_mapping = {
            'earnings': NewsCategory.EARNINGS,
            'ma': NewsCategory.MERGERS_ACQUISITIONS,
            'product': NewsCategory.PRODUCT_LAUNCH,
            'partnership': NewsCategory.PARTNERSHIP,
            'lawsuit': NewsCategory.LAWSUIT,
            'regulatory': NewsCategory.REGULATORY,
            'management': NewsCategory.MANAGEMENT_CHANGE,
            'dividend': NewsCategory.DIVIDEND,
            'split': NewsCategory.STOCK_SPLIT,
            'insider': NewsCategory.INSIDER_TRADING,
            'analyst': NewsCategory.ANALYST_RATING,
        }
        
        for category, patterns in self.patterns.items():
            matches = 0
            matched_phrases = []
            
            for pattern in patterns:
                found = pattern.findall(text)
                if found:
                    matches += len(found)
                    matched_phrases.extend(found if isinstance(found, list) else [found])
                    
            if matches > 0:
                # Calculate confidence based on match count and context
                confidence = min(0.5 + (matches * 0.1), 0.95)
                
                event = EventDetection(
                    event_type=event_mapping[category],
                    confidence=confidence,
                    details={
                        "matched_phrases": matched_phrases[:10],  # Limit
                        "match_count": matches,
                        "context_snippet": self._extract_context(text, patterns[0]) if matched_phrases else ""
                    }
                )
                events.append(event)
                
        return events
    
    def _extract_context(self, text: str, pattern: re.Pattern, window: int = 100) -> str:
        """Extract context around first match."""
        match = pattern.search(text)
        if match:
            start = max(0, match.start() - window)
            end = min(len(text), match.end() + window)
            return text[start:end]
        return ""


class CompanyResolver:
    """Resolves company mentions to canonical entities."""
    
    def __init__(self):
        self._company_aliases = self._load_aliases()
        self._ticker_map = self._load_ticker_map()
        
    def _load_aliases(self) -> Dict[str, str]:
        """Load company name aliases."""
        return {
            "google": "Alphabet Inc.",
            "alphabet": "Alphabet Inc.",
            "meta": "Meta Platforms Inc.",
            "facebook": "Meta Platforms Inc.",
            "microsoft": "Microsoft Corporation",
            "msft": "Microsoft Corporation",
            "apple": "Apple Inc.",
            "aapl": "Apple Inc.",
            "amazon": "Amazon.com Inc.",
            "amzn": "Amazon.com Inc.",
            "tesla": "Tesla Inc.",
            "tsla": "Tesla Inc.",
            "nvidia": "NVIDIA Corporation",
            "nvda": "NVIDIA Corporation",
            "berkshire": "Berkshire Hathaway Inc.",
            "brk.a": "Berkshire Hathaway Inc.",
            "brk.b": "Berkshire Hathaway Inc.",
            "jpmorgan": "JPMorgan Chase & Co.",
            "jpm": "JPMorgan Chase & Co.",
            "goldman": "Goldman Sachs Group Inc.",
            "gs": "Goldman Sachs Group Inc.",
        }
        
    def _load_ticker_map(self) -> Dict[str, str]:
        """Load ticker to company mapping."""
        return {
            "AAPL": "Apple Inc.",
            "MSFT": "Microsoft Corporation",
            "GOOGL": "Alphabet Inc.",
            "GOOG": "Alphabet Inc.",
            "AMZN": "Amazon.com Inc.",
            "TSLA": "Tesla Inc.",
            "NVDA": "NVIDIA Corporation",
            "META": "Meta Platforms Inc.",
            "BRK.A": "Berkshire Hathaway Inc.",
            "BRK.B": "Berkshire Hathaway Inc.",
            "JPM": "JPMorgan Chase & Co.",
            "GS": "Goldman Sachs Group Inc.",
        }
        
    def resolve_company(self, mention: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolve company mention to (canonical_name, ticker).
        Returns (None, None) if not recognized.
        """
        mention_lower = mention.lower().strip()
        
        # Check ticker map first
        if mention.upper() in self._ticker_map:
            return self._ticker_map[mention.upper()], mention.upper()
            
        # Check aliases
        for alias, canonical in self._company_aliases.items():
            if alias in mention_lower or mention_lower in alias:
                # Find ticker for canonical
                ticker = next((t for t, c in self._ticker_map.items() if c == canonical), None)
                return canonical, ticker
                
        return None, None
        
    def resolve_person(self, name: str, context: str = "") -> Optional[PersonMention]:
        """Resolve person mention to known executive."""
        known_executives = {
            "tim cook": {"role": "CEO", "company": "Apple Inc."},
            "satya nadella": {"role": "CEO", "company": "Microsoft Corporation"},
            "sundar pichai": {"role": "CEO", "company": "Alphabet Inc."},
            "andy jassy": {"role": "CEO", "company": "Amazon.com Inc."},
            "elon musk": {"role": "CEO", "company": "Tesla Inc."},
            "jensen huang": {"role": "CEO", "company": "NVIDIA Corporation"},
            "mark zuckerberg": {"role": "CEO", "company": "Meta Platforms Inc."},
            "warren buffett": {"role": "CEO", "company": "Berkshire Hathaway Inc."},
            "jamie dimon": {"role": "CEO", "company": "JPMorgan Chase & Co."},
            "david solomon": {"role": "CEO", "company": "Goldman Sachs Group Inc."},
        }
        
        name_lower = name.lower().strip()
        if name_lower in known_executives:
            info = known_executives[name_lower]
            return PersonMention(
                name=name,
                role=info["role"],
                company=info["company"],
                mention_count=1
            )
        return None


class CompanyNewsIntelligence:
    """Main class for extracting company intelligence from news."""
    
    def __init__(self, config: Optional[IntelligenceConfig] = None):
        self.config = config or IntelligenceConfig()
        self.event_detector = FinancialEventDetector(self.config)
        self.company_resolver = CompanyResolver()
        self.entity_extractor: Optional[FinancialEntityExtractor] = None
        
    async def _get_entity_extractor(self) -> FinancialEntityExtractor:
        """Get or create entity extractor."""
        if self.entity_extractor is None:
            extractor_config = ExtractionPipelineConfig(
                enable_rule_based=True,
                enable_dictionary=True,
                enable_local_ner=False,
                enable_llm_validation=False,
            )
            self.entity_extractor = await get_entity_extractor(extractor_config)
        return self.entity_extractor
        
    async def extract_intelligence(self, article: NewsArticle) -> ArticleIntelligence:
        """Extract full intelligence from an article."""
        text = f"{article.title} {article.summary}"
        if article.content:
            text += f" {article.content[:3000]}"
            
        intelligence = ArticleIntelligence(article=article)
        
        # 1. Detect events
        if self.config.enable_event_detection:
            intelligence.events = self.event_detector.detect_events(
                article.title, article.summary, article.content
            )
            
        # 2. Extract entities using entity recognition
        if self.config.enable_entity_extraction:
            extractor = await self._get_entity_extractor()
            result = await extractor.extract(text)
            
            # Process entities into company intelligence
            intelligence.companies = self._process_entities(result, article)
            
            # Extract people
            intelligence.people = self._extract_people(result, article)
            
            # Extract products
            intelligence.products = self._extract_products(result)
            
        # 3. Resolve companies
        if self.config.resolve_company_names:
            intelligence.companies = self._resolve_companies(intelligence.companies, article)
            
        # 4. Extract key metrics
        if self.config.enrich_with_metadata:
            intelligence.key_metrics = self._extract_key_metrics(article, intelligence)
            
        # 5. Identify risks and opportunities
        intelligence.risk_factors = self._identify_risks(article, intelligence)
        intelligence.opportunities = self._identify_opportunities(article, intelligence)
        
        # 6. Generate summary
        intelligence.summary = self._generate_article_summary(article, intelligence)
        
        return intelligence
        
    def _process_entities(self, result: EntityExtractionResult, article: NewsArticle) -> List[CompanyIntelligence]:
        """Process extracted entities into company intelligence."""
        companies: Dict[str, CompanyIntelligence] = {}
        
        for entity in result.entities:
            if entity.entity_type == EntityType.COMPANY:
                name = entity.canonical_name or entity.text
                ticker = entity.ticker
                
                key = ticker or name
                if key not in companies:
                    companies[key] = CompanyIntelligence(
                        name=name,
                        ticker=ticker,
                        mention_count=0,
                        is_primary=False
                    )
                    
                ci = companies[key]
                ci.mention_count += 1
                
                # Track sources
                ci.sources.add(article.source.value)
                
                # Track time range
                if not ci.first_mention or article.published_at < ci.first_mention:
                    ci.first_mention = article.published_at
                if not ci.last_mention or article.published_at > ci.last_mention:
                    ci.last_mention = article.published_at
                    
                # Check if primary (in title)
                if ci.name.lower() in article.title.lower() or (ci.ticker and ci.ticker in article.title):
                    ci.is_primary = True
                    
        return list(companies.values())
        
    def _extract_people(self, result: EntityExtractionResult, article: NewsArticle) -> List[PersonMention]:
        """Extract person mentions."""
        people = []
        for entity in result.entities:
            if entity.entity_type == EntityType.PERSON:
                person = self.company_resolver.resolve_person(entity.text)
                if person:
                    people.append(person)
                else:
                    # Add as unknown person
                    people.append(PersonMention(
                        name=entity.text,
                        role=entity.sub_type.value if entity.sub_type else None,
                        mention_count=1
                    ))
        return people
        
    def _extract_products(self, result: EntityExtractionResult) -> List[str]:
        """Extract product mentions."""
        products = []
        for entity in result.entities:
            if entity.entity_type in [EntityType.PRODUCT, EntityType.TECHNOLOGY]:
                products.append(entity.text)
        return products
        
    def _resolve_companies(self, companies: List[CompanyIntelligence], article: NewsArticle) -> List[CompanyIntelligence]:
        """Resolve company names to canonical forms."""
        for ci in companies:
            canonical, ticker = self.company_resolver.resolve_company(ci.name)
            if canonical:
                ci.name = canonical
            if ticker and not ci.ticker:
                ci.ticker = ticker
        return companies
        
    def _extract_key_metrics(
        self, 
        article: NewsArticle, 
        intelligence: ArticleIntelligence
    ) -> Dict[str, Any]:
        """Extract key financial metrics from article."""
        metrics = {}
        
        # Market impact
        metrics["market_impact_score"] = article.market_impact_score
        metrics["importance_score"] = article.importance_score
        metrics["relevance_score"] = article.relevance_score
        metrics["freshness_score"] = article.freshness_score
        
        # Sentiment
        if article.sentiment:
            metrics["sentiment_score"] = article.sentiment.score
            metrics["sentiment_label"] = article.sentiment.label.value
            metrics["sentiment_confidence"] = article.sentiment.confidence
            
        # Event counts
        event_counts = defaultdict(int)
        for event in intelligence.events:
            event_counts[event.event_type.value] += 1
        metrics["event_counts"] = dict(event_counts)
        
        # Company count
        metrics["company_count"] = len(intelligence.companies)
        metrics["primary_company_count"] = sum(1 for c in intelligence.companies if c.is_primary)
        
        # Source credibility
        metrics["source"] = article.source.value
        metrics["source_name"] = article.source_name
        
        return metrics
        
    def _identify_risks(
        self, 
        article: NewsArticle, 
        intelligence: ArticleIntelligence
    ) -> List[str]:
        """Identify risk factors from article."""
        risks = []
        
        # Negative sentiment
        if article.sentiment and article.sentiment.label == SentimentLabel.NEGATIVE:
            risks.append(f"Negative sentiment ({article.sentiment.score:.2f})")
            
        # Risk event types
        risk_event_types = {
            NewsCategory.LAWSUIT: "Legal proceedings",
            NewsCategory.REGULATORY: "Regulatory action",
            NewsCategory.BANKRUPTCY: "Bankruptcy risk",
            NewsCategory.LAYOFFS: "Workforce reduction",
            NewsCategory.SHORT_REPORT: "Short seller report",
        }
        
        for event in intelligence.events:
            if event.event_type in risk_event_types:
                risks.append(risk_event_types[event.event_type])
                
        # Financial distress signals
        text = f"{article.title} {article.summary}".lower()
        distress_signals = {
            "debt": "High debt mentioned",
            "loss": "Losses reported",
            "miss": "Earnings miss",
            "cut": "Guidance/dividend cut",
            "downgrade": "Analyst downgrade",
        }
        
        for signal, description in distress_signals.items():
            if signal in text:
                risks.append(description)
                
        return list(set(risks))  # Deduplicate
        
    def _identify_opportunities(
        self, 
        article: NewsArticle, 
        intelligence: ArticleIntelligence
    ) -> List[str]:
        """Identify opportunities from article."""
        opportunities = []
        
        # Positive sentiment
        if article.sentiment and article.sentiment.label == SentimentLabel.POSITIVE:
            opportunities.append(f"Positive sentiment ({article.sentiment.score:.2f})")
            
        # Opportunity event types
        opportunity_events = {
            NewsCategory.EARNINGS: "Earnings beat potential",
            NewsCategory.GUIDANCE: "Positive guidance",
            NewsCategory.PRODUCT_LAUNCH: "New product revenue",
            NewsCategory.PARTNERSHIP: "Strategic partnership",
            NewsCategory.MERGERS_ACQUISITIONS: "Acquisition synergy",
            NewsCategory.ANALYST_RATING: "Analyst upgrade",
            NewsCategory.DIVIDEND: "Dividend increase",
            NewsCategory.SHARE_BUYBACK: "Share buyback program",
        }
        
        for event in intelligence.events:
            if event.event_type in opportunity_events:
                opportunities.append(opportunity_events[event.event_type])
                
        # Growth signals
        text = f"{article.title} {article.summary}".lower()
        growth_signals = {
            "growth": "Growth mentioned",
            "expand": "Expansion plans",
            "invest": "Investment announced",
            "record": "Record performance",
            "strong": "Strong results",
        }
        
        for signal, description in growth_signals.items():
            if signal in text:
                opportunities.append(description)
                
        return list(set(opportunities))
        
    def _generate_article_summary(
        self, 
        article: NewsArticle, 
        intelligence: ArticleIntelligence
    ) -> str:
        """Generate concise article summary."""
        parts = []
        
        # Primary companies
        primary_companies = [c for c in intelligence.companies if c.is_primary]
        if primary_companies:
            company_names = ", ".join(c.name for c in primary_companies[:3])
            parts.append(f"Focus: {company_names}")
            
        # Key events
        if intelligence.events:
            event_types = list(set(e.event_type.value for e in intelligence.events))
            parts.append(f"Events: {', '.join(event_types[:3])}")
            
        # Sentiment
        if article.sentiment:
            parts.append(f"Sentiment: {article.sentiment.label.value} ({article.sentiment.score:.2f})")
            
        # Market impact
        if article.market_impact_score > 0.5:
            parts.append(f"High market impact ({article.market_impact_score:.2f})")
            
        return ". ".join(parts) + "." if parts else article.summary[:200]
        

async def extract_company_intelligence(
    articles: List[NewsArticle],
    config: Optional[IntelligenceConfig] = None
) -> Dict[str, Any]:
    """Extract intelligence from multiple articles."""
    intel = CompanyNewsIntelligence(config)
    results = []
    
    for article in articles:
        try:
            article_intel = await intel.extract_intelligence(article)
            results.append(article_intel.to_dict())
        except Exception as e:
            logger.error(f"Failed to extract intelligence from {article.title}: {e}")
            continue
            
    # Aggregate by company
    company_aggregate = defaultdict(lambda: {
        "mention_count": 0,
        "articles": [],
        "events": [],
        "sentiment_scores": [],
        "sources": set(),
        "executives": [],
        "products": set(),
    })
    
    for result in results:
        for company in result.get("companies", []):
            key = company["ticker"] or company["name"]
            agg = company_aggregate[key]
            agg["mention_count"] += company["mention_count"]
            agg["articles"].append(result["article"]["title"])
            agg["events"].extend(company["events"])
            agg["sources"].update(company["sources"])
            if company.get("sentiment"):
                agg["sentiment_scores"].append(company["sentiment"])
            agg["executives"].extend(company.get("executives", []))
            agg["products"].update(company.get("products", []))
            
    # Convert to regular dict with computed fields
    output = {}
    for key, agg in company_aggregate.items():
        avg_sentiment = sum(agg["sentiment_scores"]) / len(agg["sentiment_scores"]) if agg["sentiment_scores"] else 0
        output[key] = {
            "name": key,
            "total_mentions": agg["mention_count"],
            "article_count": len(agg["articles"]),
            "avg_sentiment": avg_sentiment,
            "event_summary": defaultdict(int),
            "executives": list(set(agg["executives"])),
            "products": list(agg["products"]),
            "sources": list(agg["sources"]),
        }
        for event in agg["events"]:
            agg["event_summary"][event["type"]] += 1
        output[key]["event_summary"] = dict(agg["event_summary"])
        
    return {
        "articles": results,
        "companies": output,
        "total_articles": len(articles),
        "total_companies": len(company_aggregate),
    }