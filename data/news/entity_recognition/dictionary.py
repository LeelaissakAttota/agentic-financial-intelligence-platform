"""
Dictionary Lookup for Financial Entity Recognition

Provides fast dictionary-based lookup for known financial entities including
companies, tickers, executives, products, exchanges, indices, and more.
"""

import json
import logging
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from pathlib import Path
import threading

from data.news.entity_recognition.schemas import (
    Entity, EntityType, EntitySubType,
)

logger = logging.getLogger(__name__)


@dataclass
class DictionaryEntry:
    """Single entry in the entity dictionary."""
    canonical_name: str
    entity_type: str
    sub_type: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    ticker: Optional[str] = None
    cik: Optional[str] = None
    lei: Optional[str] = None
    isin: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def all_names(self) -> List[str]:
        """Get all names including canonical and aliases."""
        return [self.canonical_name] + self.aliases
    
    def matches(self, text: str) -> bool:
        """Check if text matches this entry."""
        text_lower = text.lower().strip()
        for name in self.all_names():
            if name.lower() == text_lower:
                return True
        return False
    
    def to_entity(self, text: str, start_char: int, end_char: int, 
                  confidence: float = 0.95) -> 'Entity':
        """Create Entity from this dictionary entry."""
        from data.news.entity_recognition.schemas import Entity, EntityType, EntitySubType
        
        entity = Entity(
            text=text,
            entity_type=EntityType(self.entity_type),
            sub_type=EntitySubType(self.sub_type) if self.sub_type else None,
            confidence=confidence,
            normalized_value=self.canonical_name,
            canonical_name=self.canonical_name,
            ticker=self.ticker,
            cik=self.cik,
            lei=self.lei,
            isin=self.isin,
        )
        
        if self.sub_type:
            try:
                entity.sub_type = EntitySubType(self.sub_type)
            except ValueError:
                pass
                
        entity.metadata.update(self.metadata)
        entity.metadata["dictionary_match"] = True
        entity.metadata["dictionary_key"] = self.canonical_name
        
        return entity


class FinancialDictionary:
    """
    Thread-safe financial entity dictionary with fast lookups.
    
    Supports companies, tickers, people, products, exchanges, indices,
    cryptocurrencies, commodities, regulators, and more.
    """
    
    def __init__(self):
        self._companies: Dict[str, 'DictionaryEntry'] = {}
        self._tickers: Dict[str, 'DictionaryEntry'] = {}
        self._people: Dict[str, 'DictionaryEntry'] = {}
        self._products: Dict[str, 'DictionaryEntry'] = {}
        self._exchanges: Dict[str, 'DictionaryEntry'] = {}
        self._indices: Dict[str, 'DictionaryEntry'] = {}
        self._crypto: Dict[str, 'DictionaryEntry'] = {}
        self._commodities: Dict[str, 'DictionaryEntry'] = {}
        self._regulators: Dict[str, 'DictionaryEntry'] = {}
        self._central_banks: Dict[str, 'DictionaryEntry'] = {}
        self._sectors: Dict[str, 'DictionaryEntry'] = {}
        self._events: Dict[str, 'DictionaryEntry'] = {}
        
        self._name_to_entry: Dict[str, 'DictionaryEntry'] = {}
        self._lock = threading.RLock()
        self._initialized = False
        
    def initialize(self) -> None:
        """Load all dictionary data."""
        with self._lock:
            if self._initialized:
                return
                
            self._load_builtin_data()
            self._build_name_index()
            self._initialized = True
            logger.info("Financial dictionary initialized")
            
    def _load_builtin_data(self) -> None:
        """Load built-in financial entity data."""
        
        # Major Companies
        companies = [
            DictionaryEntry(
                canonical_name="Apple Inc.",
                entity_type="company",
                sub_type="public_company",
                aliases=["Apple", "Apple Computer", "Apple Inc"],
                ticker="AAPL",
                cik="0000320193",
                lei="HWUPKR0MPOU8FGXBT394",
                isin="US0378331005",
                exchange="NASDAQ",
                sector="technology",
                industry="consumer_electronics",
                country="US",
                metadata={"market_cap_tier": "mega", "sp500": True, "dow_jones": True}
            ),
            DictionaryEntry(
                canonical_name="Microsoft Corporation",
                entity_type="company",
                sub_type="public_company",
                aliases=["Microsoft", "MSFT", "MS"],
                ticker="MSFT",
                cik="0000789019",
                lei="INR2EJN1ERAN0W5ZP974",
                isin="US5949181045",
                exchange="NASDAQ",
                sector="technology",
                industry="software",
                country="US",
                metadata={"market_cap_tier": "mega", "sp500": True, "dow_jones": True}
            ),
            DictionaryEntry(
                canonical_name="Amazon.com Inc.",
                entity_type="company",
                sub_type="public_company",
                aliases=["Amazon", "Amazon.com", "AWS"],
                ticker="AMZN",
                cik="0001018724",
                lei="ZXTILKJKG63JELOEG630",
                isin="US0231351067",
                exchange="NASDAQ",
                sector="technology",
                industry="ecommerce",
                country="US",
                metadata={"market_cap_tier": "mega", "sp500": True}
            ),
            DictionaryEntry(
                canonical_name="Alphabet Inc.",
                entity_type="company",
                sub_type="public_company",
                aliases=["Alphabet", "Google", "GOOGL", "GOOG"],
                ticker="GOOGL",
                cik="0001652044",
                lei="549300610H0J7D7QYJ23",
                isin="US02079K3059",
                exchange="NASDAQ",
                sector="technology",
                industry="internet_services",
                country="US",
                metadata={"market_cap_tier": "mega", "sp500": True}
            ),
            DictionaryEntry(
                canonical_name="Meta Platforms Inc.",
                entity_type="company",
                sub_type="public_company",
                aliases=["Meta", "Facebook", "FB", "Meta Platforms"],
                ticker="META",
                cik="0001326801",
                lei="BQ4BK80H8X3Y7K8V9J23",
                isin="US30303M1027",
                exchange="NASDAQ",
                sector="technology",
                industry="social_media",
                country="US",
                metadata={"market_cap_tier": "mega", "sp500": True}
            ),
            DictionaryEntry(
                canonical_name="NVIDIA Corporation",
                entity_type="company",
                sub_type="public_company",
                aliases=["NVIDIA", "Nvidia", "NVDA"],
                ticker="NVDA",
                cik="0001045810",
                lei="549300YK8L6J7D7QYJ23",
                isin="US67066G1040",
                exchange="NASDAQ",
                sector="technology",
                industry="semiconductors",
                country="US",
                metadata={"market_cap_tier": "mega", "sp500": True, "ai_focus": True}
            ),
            DictionaryEntry(
                canonical_name="Tesla Inc.",
                entity_type="company",
                sub_type="public_company",
                aliases=["Tesla", "TSLA", "Tesla Motors"],
                ticker="TSLA",
                cik="0001318605",
                lei="549300YK8L6J7D7QYJ23",
                isin="US88160R1014",
                exchange="NASDAQ",
                sector="automotive",
                industry="electric_vehicles",
                country="US",
                metadata={"market_cap_tier": "large", "sp500": True, "ev_focus": True}
            ),
            DictionaryEntry(
                canonical_name="Berkshire Hathaway Inc.",
                entity_type="company",
                sub_type="public_company",
                aliases=["Berkshire Hathaway", "BRK.A", "BRK.B", "Berkshire"],
                ticker="BRK.A",
                cik="0001067983",
                lei="549300YK8L6J7D7QYJ23",
                isin="US0846707026",
                exchange="NYSE",
                sector="financial",
                industry="conglomerate",
                country="US",
                metadata={"market_cap_tier": "large", "sp500": True}
            ),
            DictionaryEntry(
                canonical_name="JPMorgan Chase & Co.",
                entity_type="company",
                sub_type="public_company",
                aliases=["JPMorgan Chase", "JPMorgan", "JPM", "Chase"],
                ticker="JPM",
                cik="0000019617",
                lei="8I5DZWZKVSZI1NUHU748",
                isin="US46625H1005",
                exchange="NYSE",
                sector="financial",
                industry="banking",
                country="US",
                metadata={"market_cap_tier": "large", "sp500": True, "dow_jones": True, "sifi": True}
            ),
            DictionaryEntry(
                canonical_name="Visa Inc.",
                entity_type="company",
                sub_type="public_company",
                aliases=["Visa", "V"],
                ticker="V",
                cik="0001403161",
                lei="549300YK8L6J7D7QYJ23",
                isin="US92826C8394",
                exchange="NYSE",
                sector="financial",
                industry="payment_processing",
                country="US",
                metadata={"market_cap_tier": "large", "sp500": True, "dow_jones": True}
            ),
        ]
        
        for company in companies:
            self.add_company(company)
            
        # People (executives, investors, analysts)
        people = [
            DictionaryEntry(
                canonical_name="Elon Musk",
                entity_type="person",
                sub_type="ceo",
                aliases=["Elon Musk", "Musk"],
                metadata={"companies": ["Tesla Inc.", "SpaceX", "X Corp."], "net_worth_billion": 200}
            ),
            DictionaryEntry(
                canonical_name="Tim Cook",
                entity_type="person",
                sub_type="ceo",
                aliases=["Tim Cook", "Timothy Cook"],
                metadata={"companies": ["Apple Inc."]}
            ),
            DictionaryEntry(
                canonical_name="Satya Nadella",
                entity_type="person",
                sub_type="ceo",
                aliases=["Satya Nadella", "Satya Narayana Nadella"],
                metadata={"companies": ["Microsoft Corporation"]}
            ),
            DictionaryEntry(
                canonical_name="Sundar Pichai",
                entity_type="person",
                sub_type="ceo",
                aliases=["Sundar Pichai", "Pichai Sundararajan"],
                metadata={"companies": ["Alphabet Inc.", "Google"]}
            ),
            DictionaryEntry(
                canonical_name="Mark Zuckerberg",
                entity_type="person",
                sub_type="ceo",
                aliases=["Mark Zuckerberg", "Mark Elliot Zuckerberg"],
                metadata={"companies": ["Meta Platforms Inc.", "Facebook"]}
            ),
            DictionaryEntry(
                canonical_name="Jeff Bezos",
                entity_type="person",
                sub_type="founder",
                aliases=["Jeff Bezos", "Jeffrey Bezos"],
                metadata={"companies": ["Amazon.com Inc.", "Blue Origin"]}
            ),
            DictionaryEntry(
                canonical_name="Andy Jassy",
                entity_type="person",
                sub_type="ceo",
                aliases=["Andy Jassy", "Andrew Jassy"],
                metadata={"companies": ["Amazon.com Inc."]}
            ),
            DictionaryEntry(
                canonical_name="Warren Buffett",
                entity_type="person",
                sub_type="investor",
                aliases=["Warren Buffett", "Warren Edward Buffett"],
                metadata={"companies": ["Berkshire Hathaway Inc."], "net_worth_billion": 100}
            ),
            DictionaryEntry(
                canonical_name="Charlie Munger",
                entity_type="person",
                sub_type="investor",
                aliases=["Charlie Munger", "Charles Munger"],
                metadata={"companies": ["Berkshire Hathaway Inc."]}
            ),
            DictionaryEntry(
                canonical_name="Jamie Dimon",
                entity_type="person",
                sub_type="ceo",
                aliases=["Jamie Dimon", "James Dimon"],
                metadata={"companies": ["JPMorgan Chase & Co."]}
            ),
            DictionaryEntry(
                canonical_name="David Solomon",
                entity_type="person",
                sub_type="ceo",
                aliases=["David Solomon", "David M. Solomon"],
                metadata={"companies": ["Goldman Sachs Group Inc."]}
            ),
            DictionaryEntry(
                canonical_name="Jane Fraser",
                entity_type="person",
                sub_type="ceo",
                aliases=["Jane Fraser"],
                metadata={"companies": ["Citigroup Inc."]}
            ),
            DictionaryEntry(
                canonical_name="Jensen Huang",
                entity_type="person",
                sub_type="ceo",
                aliases=["Jensen Huang", "Jen-Hsun Huang"],
                metadata={"companies": ["NVIDIA Corporation"]}
            ),
            DictionaryEntry(
                canonical_name="Lisa Su",
                entity_type="person",
                sub_type="ceo",
                aliases=["Lisa Su"],
                metadata={"companies": ["Advanced Micro Devices Inc."]}
            ),
            DictionaryEntry(
                canonical_name="Pat Gelsinger",
                entity_type="person",
                sub_type="ceo",
                aliases=["Pat Gelsinger", "Patrick Gelsinger"],
                metadata={"companies": ["Intel Corporation"]}
            ),
        ]
        
        for person in people:
            self.add_person(person)
            
        # Exchanges
        exchanges = [
            DictionaryEntry(
                canonical_name="New York Stock Exchange",
                entity_type="exchange",
                aliases=["NYSE", "New York Stock Exchange", "The Big Board"],
                metadata={"country": "US", "timezone": "America/New_York", "currency": "USD"}
            ),
            DictionaryEntry(
                canonical_name="NASDAQ",
                entity_type="exchange",
                aliases=["NASDAQ", "NASDAQ Stock Market"],
                metadata={"country": "US", "timezone": "America/New_York", "currency": "USD"}
            ),
            DictionaryEntry(
                canonical_name="London Stock Exchange",
                entity_type="exchange",
                aliases=["LSE", "London Stock Exchange"],
                metadata={"country": "UK", "timezone": "Europe/London", "currency": "GBP"}
            ),
            DictionaryEntry(
                canonical_name="Tokyo Stock Exchange",
                entity_type="exchange",
                aliases=["TSE", "Tokyo Stock Exchange"],
                metadata={"country": "JP", "timezone": "Asia/Tokyo", "currency": "JPY"}
            ),
            DictionaryEntry(
                canonical_name="Hong Kong Exchanges and Clearing",
                entity_type="exchange",
                aliases=["HKEX", "Hong Kong Exchanges", "Hong Kong Stock Exchange"],
                metadata={"country": "HK", "timezone": "Asia/Hong_Kong", "currency": "HKD"}
            ),
            DictionaryEntry(
                canonical_name="Shanghai Stock Exchange",
                entity_type="exchange",
                aliases=["SSE", "Shanghai Stock Exchange"],
                metadata={"country": "CN", "timezone": "Asia/Shanghai", "currency": "CNY"}
            ),
            DictionaryEntry(
                canonical_name="Euronext",
                entity_type="exchange",
                aliases=["EURONEXT", "Euronext Paris", "Euronext Amsterdam", "Euronext Brussels", "Euronext Lisbon", "Euronext Dublin"],
                metadata={"country": "EU", "currency": "EUR"}
            ),
            DictionaryEntry(
                canonical_name="Deutsche Borse",
                entity_type="exchange",
                aliases=["XETRA", "Frankfurt Stock Exchange", "Deutsche Boerse", "Deutsche Boerse Xetra"],
                metadata={"country": "DE", "timezone": "Europe/Berlin", "currency": "EUR"}
            ),
        ]
        
        for exchange in exchanges:
            self.add_exchange(exchange)
            
        # Indices
        indices = [
            DictionaryEntry(
                canonical_name="S&P 500",
                entity_type="index",
                aliases=["S&P 500", "SP500", "SPX", "S&P500", "Standard & Poor's 500"],
                metadata={"country": "US", "constituents": 500, "weighting": "market_cap"}
            ),
            DictionaryEntry(
                canonical_name="Dow Jones Industrial Average",
                entity_type="index",
                aliases=["Dow Jones", "DJIA", "Dow", "DJI", "Dow Jones Industrial Average", "The Dow"],
                metadata={"country": "US", "constituents": 30, "weighting": "price"}
            ),
            DictionaryEntry(
                canonical_name="NASDAQ Composite",
                entity_type="index",
                aliases=["NASDAQ", "NASDAQ Composite", "COMP"],
                metadata={"country": "US", "constituents": 3000, "weighting": "market_cap"}
            ),
            DictionaryEntry(
                canonical_name="NASDAQ 100",
                entity_type="index",
                aliases=["NASDAQ 100", "NDX", "QQQ"],
                metadata={"country": "US", "constituents": 100, "weighting": "modified_market_cap"}
            ),
            DictionaryEntry(
                canonical_name="Russell 2000",
                entity_type="index",
                aliases=["Russell 2000", "RUT", "R2000"],
                metadata={"country": "US", "constituents": 2000, "weighting": "market_cap"}
            ),
            DictionaryEntry(
                canonical_name="CBOE Volatility Index",
                entity_type="index",
                aliases=["VIX", "CBOE VIX", "Volatility Index", "Fear Index"],
                metadata={"country": "US", "type": "volatility"}
            ),
            DictionaryEntry(
                canonical_name="FTSE 100",
                entity_type="index",
                aliases=["FTSE 100", "FTSE", "UKX", "Footsie"],
                metadata={"country": "UK", "constituents": 100, "weighting": "market_cap"}
            ),
            DictionaryEntry(
                canonical_name="DAX",
                entity_type="index",
                aliases=["DAX", "DAX 30", "GDAXI", "DAX 40"],
                metadata={"country": "DE", "constituents": 40, "weighting": "market_cap"}
            ),
            DictionaryEntry(
                canonical_name="CAC 40",
                entity_type="index",
                aliases=["CAC 40", "CAC", "FCHI", "CAC40"],
                metadata={"country": "FR", "constituents": 40, "weighting": "market_cap"}
            ),
            DictionaryEntry(
                canonical_name="Nikkei 225",
                entity_type="index",
                aliases=["Nikkei 225", "Nikkei", "N225", "NIKKEI"],
                metadata={"country": "JP", "constituents": 225, "weighting": "price"}
            ),
            DictionaryEntry(
                canonical_name="Hang Seng Index",
                entity_type="index",
                aliases=["Hang Seng", "HSI", "Hang Seng Index"],
                metadata={"country": "HK", "constituents": 50, "weighting": "market_cap"}
            ),
        ]
        
        for index in indices:
            self.add_index(index)
            
        # Central Banks
        central_banks = [
            DictionaryEntry(
                canonical_name="Federal Reserve",
                entity_type="central_bank",
                aliases=["Fed", "Federal Reserve", "The Fed", "FOMC"],
                metadata={"country": "US", "currency": "USD"}
            ),
            DictionaryEntry(
                canonical_name="European Central Bank",
                entity_type="central_bank",
                aliases=["ECB", "European Central Bank", "Eurosystem"],
                metadata={"region": "Eurozone", "currency": "EUR"}
            ),
            DictionaryEntry(
                canonical_name="Bank of England",
                entity_type="central_bank",
                aliases=["BoE", "Bank of England", "Old Lady of Threadneedle Street"],
                metadata={"country": "UK", "currency": "GBP"}
            ),
            DictionaryEntry(
                canonical_name="Bank of Japan",
                entity_type="central_bank",
                aliases=["BoJ", "Bank of Japan", "Nichigin"],
                metadata={"country": "JP", "currency": "JPY"}
            ),
            DictionaryEntry(
                canonical_name="People's Bank of China",
                entity_type="central_bank",
                aliases=["PBOC", "People's Bank of China", "PBC"],
                metadata={"country": "CN", "currency": "CNY"}
            ),
        ]
        
        for cb in central_banks:
            self.add_central_bank(cb)
            
        # Regulators
        regulators = [
            DictionaryEntry(
                canonical_name="Securities and Exchange Commission",
                entity_type="regulator",
                aliases=["SEC", "Securities and Exchange Commission"],
                metadata={"country": "US"}
            ),
            DictionaryEntry(
                canonical_name="Commodity Futures Trading Commission",
                entity_type="regulator",
                aliases=["CFTC", "Commodity Futures Trading Commission"],
                metadata={"country": "US"}
            ),
            DictionaryEntry(
                canonical_name="Financial Industry Regulatory Authority",
                entity_type="regulator",
                aliases=["FINRA", "Financial Industry Regulatory Authority"],
                metadata={"country": "US"}
            ),
            DictionaryEntry(
                canonical_name="Financial Conduct Authority",
                entity_type="regulator",
                aliases=["FCA", "Financial Conduct Authority"],
                metadata={"country": "UK"}
            ),
            DictionaryEntry(
                canonical_name="European Securities and Markets Authority",
                entity_type="regulator",
                aliases=["ESMA", "European Securities and Markets Authority"],
                metadata={"region": "EU"}
            ),
        ]
        
        for reg in regulators:
            self.add_regulator(reg)
            
        # Cryptocurrencies
        crypto = [
            DictionaryEntry(
                canonical_name="Bitcoin",
                entity_type="cryptocurrency",
                sub_type="coin",
                aliases=["BTC", "Bitcoin", "XBT"],
                metadata={"symbol": "BTC", "type": "coin", "layer": "L1"}
            ),
            DictionaryEntry(
                canonical_name="Ethereum",
                entity_type="cryptocurrency",
                sub_type="coin",
                aliases=["ETH", "Ethereum", "Ether"],
                metadata={"symbol": "ETH", "type": "coin", "layer": "L1"}
            ),
            DictionaryEntry(
                canonical_name="Tether",
                entity_type="cryptocurrency",
                sub_type="stablecoin",
                aliases=["USDT", "Tether"],
                metadata={"symbol": "USDT", "type": "stablecoin", "peg": "USD"}
            ),
            DictionaryEntry(
                canonical_name="BNB",
                entity_type="cryptocurrency",
                sub_type="coin",
                aliases=["BNB", "Binance Coin", "Binance"],
                metadata={"symbol": "BNB", "type": "coin", "exchange": "Binance"}
            ),
            DictionaryEntry(
                canonical_name="Solana",
                entity_type="cryptocurrency",
                sub_type="coin",
                aliases=["SOL", "Solana"],
                metadata={"symbol": "SOL", "type": "coin", "layer": "L1"}
            ),
            DictionaryEntry(
                canonical_name="XRP",
                entity_type="cryptocurrency",
                sub_type="coin",
                aliases=["XRP", "Ripple", "XRP Ledger"],
                metadata={"symbol": "XRP", "type": "coin", "company": "Ripple Labs"}
            ),
            DictionaryEntry(
                canonical_name="Cardano",
                entity_type="cryptocurrency",
                sub_type="coin",
                aliases=["ADA", "Cardano"],
                metadata={"symbol": "ADA", "type": "coin", "layer": "L1"}
            ),
            DictionaryEntry(
                canonical_name="Dogecoin",
                entity_type="cryptocurrency",
                sub_type="coin",
                aliases=["DOGE", "Dogecoin"],
                metadata={"symbol": "DOGE", "type": "coin", "meme": True}
            ),
        ]
        
        for c in crypto:
            self.add_crypto(c)
            
        # Commodities
        commodities = [
            DictionaryEntry(
                canonical_name="Gold",
                entity_type="commodity",
                aliases=["Gold", "XAU", "GLD"],
                metadata={"symbol": "XAU", "type": "precious_metal", "currency": "USD"}
            ),
            DictionaryEntry(
                canonical_name="Silver",
                entity_type="commodity",
                aliases=["Silver", "XAG", "SLV"],
                metadata={"symbol": "XAG", "type": "precious_metal", "currency": "USD"}
            ),
            DictionaryEntry(
                canonical_name="Crude Oil WTI",
                entity_type="commodity",
                aliases=["WTI", "Crude Oil", "West Texas Intermediate", "CL", "Oil"],
                metadata={"symbol": "CL", "type": "energy", "grade": "WTI"}
            ),
            DictionaryEntry(
                canonical_name="Brent Crude",
                entity_type="commodity",
                aliases=["Brent", "Brent Crude", "Brent Oil", "CO", "Brent"],
                metadata={"symbol": "CO", "type": "energy", "grade": "Brent"}
            ),
            DictionaryEntry(
                canonical_name="Natural Gas",
                entity_type="commodity",
                aliases=["Natural Gas", "NG", "Henry Hub", "HH", "Nat Gas"],
                metadata={"symbol": "NG", "type": "energy", "hub": "Henry Hub"}
            ),
            DictionaryEntry(
                canonical_name="Copper",
                entity_type="commodity",
                aliases=["Copper", "HG", "Dr. Copper"],
                metadata={"symbol": "HG", "type": "base_metal"}
            ),
        ]
        
        for comm in commodities:
            self.add_commodity(comm)
            
        # Sectors
        sectors = [
            ("technology", "technology"),
            ("healthcare", "healthcare"),
            ("financial", "financial"),
            ("energy", "energy"),
            ("consumer", "consumer"),
            ("industrial", "industrial"),
            ("materials", "materials"),
            ("utilities", "utilities"),
            ("real_estate", "real_estate"),
            ("communication", "communication"),
        ]
        
        for name, sub_type in sectors:
            entry = DictionaryEntry(
                canonical_name=name.capitalize(),
                entity_type="sector",
                sub_type=sub_type,
                aliases=[name, name.capitalize()],
                metadata={"sector": name}
            )
            self.add_sector(entry)
            
        # Events
        events = [
            ("earnings_release", "earnings release"),
            ("merger_acquisition", "merger and acquisition"),
            ("ipo", "initial public offering"),
            ("secondary_offering", "secondary offering"),
            ("stock_split", "stock split"),
            ("dividend_announcement", "dividend announcement"),
            ("buyback_announcement", "buyback announcement"),
            ("guidance", "guidance"),
            ("analyst_rating", "analyst rating"),
            ("regulatory_filing", "regulatory filing"),
            ("lawsuit", "lawsuit"),
            ("product_launch", "product launch"),
            ("partnership", "partnership"),
            ("restructuring", "restructuring"),
            ("layoffs", "layoffs"),
            ("bankruptcy", "bankruptcy"),
        ]
        
        for sub_type, name in events:
            entry = DictionaryEntry(
                canonical_name=name.replace("_", " ").title(),
                entity_type="event",
                sub_type=sub_type,
                aliases=[name.replace("_", " "), name.replace("_", "-")],
                metadata={"event_type": sub_type}
            )
            self.add_event(entry)
        
        logger.info(f"Loaded {len(companies)} companies, {len(people)} people, {len(exchanges)} exchanges, {len(indices)} indices, {len(central_banks)} central banks, {len(regulators)} regulators, {len(crypto)} crypto, {len(commodities)} commodities, {len(sectors)} sectors, {len(events)} events")
        
    def _build_name_index(self) -> None:
        """Build name-to-entry index for fast lookups."""
        self._name_to_entry.clear()
        
        for entry_dict in [self._companies, self._tickers, self._people, 
                           self._products, self._exchanges, self._indices,
                           self._crypto, self._commodities, self._regulators,
                           self._central_banks, self._sectors, self._events]:
            for entry in entry_dict.values():
                for name in entry.all_names():
                    key = name.lower().strip()
                    self._name_to_entry[key] = entry
                    
        logger.info(f"Built name index with {len(self._name_to_entry)} entries")
        
    def add_company(self, entry: 'DictionaryEntry') -> None:
        """Add a company entry."""
        with self._lock:
            self._companies[entry.canonical_name.lower()] = entry
            if entry.ticker:
                self._tickers[entry.ticker.upper()] = entry
                
    def add_ticker(self, ticker: str, company_name: str) -> None:
        """Add a ticker mapping."""
        with self._lock:
            entry = DictionaryEntry(
                canonical_name=ticker.upper(),
                entity_type="ticker",
                aliases=[ticker.upper()],
                metadata={"company_name": company_name}
            )
            self._tickers[ticker.upper()] = entry
            
    def add_person(self, entry: 'DictionaryEntry') -> None:
        """Add a person entry."""
        with self._lock:
            self._people[entry.canonical_name.lower()] = entry
            
    def add_product(self, entry: 'DictionaryEntry') -> None:
        """Add a product entry."""
        with self._lock:
            self._products[entry.canonical_name.lower()] = entry
            
    def add_exchange(self, entry: 'DictionaryEntry') -> None:
        """Add an exchange entry."""
        with self._lock:
            self._exchanges[entry.canonical_name.lower()] = entry
            
    def add_index(self, entry: 'DictionaryEntry') -> None:
        """Add an index entry."""
        with self._lock:
            self._indices[entry.canonical_name.lower()] = entry
            
    def add_crypto(self, entry: 'DictionaryEntry') -> None:
        """Add a cryptocurrency entry."""
        with self._lock:
            self._crypto[entry.canonical_name.lower()] = entry
            # Also add ticker
            for alias in entry.aliases:
                if len(alias) <= 10 and alias.isupper():
                    self._tickers[alias] = entry
                    
    def add_commodity(self, entry: 'DictionaryEntry') -> None:
        """Add a commodity entry."""
        with self._lock:
            self._commodities[entry.canonical_name.lower()] = entry
            
    def add_regulator(self, entry: 'DictionaryEntry') -> None:
        """Add a regulator entry."""
        with self._lock:
            self._regulators[entry.canonical_name.lower()] = entry
            
    def add_central_bank(self, entry: 'DictionaryEntry') -> None:
        """Add a central bank entry."""
        with self._lock:
            self._central_banks[entry.canonical_name.lower()] = entry
            
    def add_sector(self, entry: 'DictionaryEntry') -> None:
        """Add a sector entry."""
        with self._lock:
            self._sectors[entry.canonical_name.lower()] = entry
            
    def add_event(self, entry: 'DictionaryEntry') -> None:
        """Add an event entry."""
        with self._lock:
            self._events[entry.canonical_name.lower()] = entry
            
    def lookup(self, text: str) -> Optional['DictionaryEntry']:
        """Look up an entity by text (case-insensitive)."""
        with self._lock:
            if not self._initialized:
                self.initialize()
            return self._name_to_entry.get(text.lower().strip())
            
    def lookup_company(self, text: str) -> Optional['DictionaryEntry']:
        """Look up a company by name."""
        with self._lock:
            if not self._initialized:
                self.initialize()
            return self._companies.get(text.lower().strip())
            
    def lookup_ticker(self, ticker: str) -> Optional['DictionaryEntry']:
        """Look up a ticker."""
        with self._lock:
            if not self._initialized:
                self.initialize()
            return self._tickers.get(ticker.upper().strip())
            
    def lookup_person(self, name: str) -> Optional['DictionaryEntry']:
        """Look up a person by name."""
        with self._lock:
            if not self._initialized:
                self.initialize()
            return self._people.get(name.lower().strip())
            
    def lookup_exchange(self, name: str) -> Optional['DictionaryEntry']:
        """Look up an exchange."""
        with self._lock:
            if not self._initialized:
                self.initialize()
            return self._exchanges.get(name.lower().strip())
            
    def lookup_index(self, name: str) -> Optional['DictionaryEntry']:
        """Look up an index."""
        with self._lock:
            if not self._initialized:
                self.initialize()
            return self._indices.get(name.lower().strip())
            
    def lookup_crypto(self, name: str) -> Optional['DictionaryEntry']:
        """Look up a cryptocurrency."""
        with self._lock:
            if not self._initialized:
                self.initialize()
            return self._crypto.get(name.lower().strip())
            
    def lookup_commodity(self, name: str) -> Optional['DictionaryEntry']:
        """Look up a commodity."""
        with self._lock:
            if not self._initialized:
                self.initialize()
            return self._commodities.get(name.lower().strip())
            
    def lookup_regulator(self, name: str) -> Optional['DictionaryEntry']:
        """Look up a regulator."""
        with self._lock:
            if not self._initialized:
                self.initialize()
            return self._regulators.get(name.lower().strip())
            
    def lookup_central_bank(self, name: str) -> Optional['DictionaryEntry']:
        """Look up a central bank."""
        with self._lock:
            if not self._initialized:
                self.initialize()
            return self._central_banks.get(name.lower().strip())
            
    def lookup_sector(self, name: str) -> Optional['DictionaryEntry']:
        """Look up a sector."""
        with self._lock:
            if not self._initialized:
                self.initialize()
            return self._sectors.get(name.lower().strip())
            
    def lookup_event(self, name: str) -> Optional['DictionaryEntry']:
        """Look up an event type."""
        with self._lock:
            if not self._initialized:
                self.initialize()
            return self._events.get(name.lower().strip())
            
    def get_all_companies(self) -> List['DictionaryEntry']:
        """Get all company entries."""
        with self._lock:
            return list(self._companies.values())
            
    def get_all_tickers(self) -> List['DictionaryEntry']:
        """Get all ticker entries."""
        with self._lock:
            return list(self._tickers.values())
            
    def get_all_people(self) -> List['DictionaryEntry']:
        """Get all people entries."""
        with self._lock:
            return list(self._people.values())
            
    def get_all_exchanges(self) -> List['DictionaryEntry']:
        """Get all exchange entries."""
        with self._lock:
            return list(self._exchanges.values())
            
    def get_all_indices(self) -> List['DictionaryEntry']:
        """Get all index entries."""
        with self._lock:
            return list(self._indices.values())
            
    def get_all_crypto(self) -> List['DictionaryEntry']:
        """Get all cryptocurrency entries."""
        with self._lock:
            return list(self._crypto.values())
            
    def get_all_commodities(self) -> List['DictionaryEntry']:
        """Get all commodity entries."""
        with self._lock:
            return list(self._commodities.values())
            
    def get_all_regulators(self) -> List['DictionaryEntry']:
        """Get all regulator entries."""
        with self._lock:
            return list(self._regulators.values())
            
    def get_all_central_banks(self) -> List['DictionaryEntry']:
        """Get all central bank entries."""
        with self._lock:
            return list(self._central_banks.values())
            
    def get_all_sectors(self) -> List['DictionaryEntry']:
        """Get all sector entries."""
        with self._lock:
            return list(self._sectors.values())
            
    def get_all_events(self) -> List['DictionaryEntry']:
        """Get all event entries."""
        with self._lock:
            return list(self._events.values())
            
    def search(self, query: str, limit: int = 10) -> List['DictionaryEntry']:
        """Search for entries matching query."""
        with self._lock:
            if not self._initialized:
                self.initialize()
            query_lower = query.lower().strip()
            results = []
            for key, entry in self._name_to_entry.items():
                if query_lower in key:
                    results.append(entry)
                    if len(results) >= limit:
                        break
            return results


# Module-level singleton instance
_financial_dictionary: Optional[FinancialDictionary] = None


def get_financial_dictionary() -> FinancialDictionary:
    """Get or create the global FinancialDictionary instance."""
    global _financial_dictionary
    if _financial_dictionary is None:
        _financial_dictionary = FinancialDictionary()
        _financial_dictionary.initialize()
    return _financial_dictionary