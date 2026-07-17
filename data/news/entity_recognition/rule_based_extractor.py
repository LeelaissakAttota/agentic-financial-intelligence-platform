"""
Rule-based Financial Entity Extractor

Uses regex patterns to extract financial entities from text including:
- Stock tickers (e.g., AAPL, MSFT, BRK.B)
- Money amounts (e.g., $1.2B, $500M, €1.5B)
- Percentages (e.g., 5.2%, 12.5%)
- Dates (financial quarters, fiscal years)
- Financial metric patterns (revenue, EPS, EBITDA, etc.)
- Currency codes
- SEC filing references
"""

import re
import logging
from typing import List, Optional, Dict, Any, Pattern
from dataclasses import dataclass, field
from datetime import datetime

from data.news.entity_recognition.schemas import (
    Entity, EntityType, EntitySubType, ConfidenceLevel
)

logger = logging.getLogger(__name__)


@dataclass
class RegexPattern:
    """A compiled regex pattern with metadata."""
    pattern: Pattern
    entity_type: EntityType
    sub_type: Optional[EntitySubType] = None
    confidence: float = 0.8
    description: str = ""
    group_name: str = "match"
    normalize_fn: Optional[callable] = None


class RuleBasedExtractor:
    """
    Rule-based financial entity extraction using compiled regex patterns.
    
    Extracts:
    - Stock tickers (NYSE, NASDAQ, etc.)
    - Money/currency amounts
    - Percentages
    - Dates (quarters, fiscal years, specific dates)
    - Financial metrics (revenue, EPS, EBITDA, etc.)
    - SEC filing references (8-K, 10-Q, 10-K, etc.)
    - Currency codes (USD, EUR, GBP, etc.)
    - Basis points
    - Price targets
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._patterns: List[RegexPattern] = []
        self._compile_patterns()
        
    def _compile_patterns(self) -> None:
        """Compile all regex patterns."""
        
        # ============================================================
        # STOCK TICKERS
        # ============================================================
        
        # Standard tickers: 1-5 uppercase letters, optionally with .A/.B
        ticker_pattern = re.compile(
            r'\b(?:'  # Word boundary, non-capturing group
            r'[A-Z]{1,5}(?:\.[A-Z])?'  # Standard ticker: AAPL, BRK.A, BRK.B
            r'|[A-Z]{1,4}\.[A-Z]{1,2}'  # With exchange suffix: AAPL.US, MSFT.O
            r')\b'
        )
        self._patterns.append(RegexPattern(
            pattern=ticker_pattern,
            entity_type=EntityType.TICKER,
            sub_type=EntitySubType.US_EQUITY,
            confidence=0.9,
            description="Standard stock ticker symbols"
        ))
        
        # Ticker with exchange prefix
        exchange_ticker = re.compile(
            r'\b(?:NYSE|NASDAQ|AMEX|ARCA|BATS|TSX|LSE|TSE|HKEX|SSE|SZSE|ASX|SGX|BSE|NSE|KRX|TADAWUL):\s*[A-Z]{1,5}(?:\.[A-Z])?\b'
        )
        self._patterns.append(RegexPattern(
            pattern=exchange_ticker,
            entity_type=EntityType.TICKER,
            sub_type=EntitySubType.US_EQUITY,
            confidence=0.95,
            description="Exchange-prefixed ticker symbols"
        ))
        
        # Ticker in parentheses after company name
        paren_ticker = re.compile(
            r'\((?:NYSE|NASDAQ|TSX|LSE|HKEX|ASX|SGX|BSE|NSE|KRX):\s*([A-Z]{1,5}(?:\.[A-Z])?)\)'
        )
        self._patterns.append(RegexPattern(
            pattern=paren_ticker,
            entity_type=EntityType.TICKER,
            sub_type=EntitySubType.US_EQUITY,
            confidence=0.95,
            description="Ticker in parentheses with exchange"
        ))
        
        # Ticker after colon
        colon_ticker = re.compile(
            r'(?:ticker|symbol|trading\s+(?:as|under))\s*:\s*([A-Z]{1,5}(?:\.[A-Z])?)\b'
        )
        self._patterns.append(RegexPattern(
            pattern=colon_ticker,
            entity_type=EntityType.TICKER,
            sub_type=EntitySubType.US_EQUITY,
            confidence=0.9,
            description="Ticker after colon"
        ))
        
        # ============================================================
        # MONEY/CURRENCY AMOUNTS
        # ============================================================
        
        # $1.2B, $500M, $1.2 billion, $500 million, $1,200,000,000
        money_pattern = re.compile(
            r'(?:'  # Non-capturing group for currency symbols
            r'(?:\$|USD|EUR|GBP|JPY|CNY|CAD|AUD|CHF|HKD|SGD|INR|KRW|BRL|MXN|ZAR|SEK|NOK|DKK|TRY|PLN|CZK|HUF|ILS|CLP|COP|PEN|ARS|VND|THB|MYR|PHP|IDR|TWD)\s*'
            r')'
            r'(?:'  # Amount patterns
            r'(?:\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*'  # Number with optional commas/decimals
            r'(?:billion|million|thousand|trillion|bn|mm|mn|m|k|B|M|K|T|MM|BB|tril?)\b'  # Scale words
            r'|'  # OR
            r'(?:\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\b'  # Plain number
            r')'
        )
        self._patterns.append(RegexPattern(
            pattern=money_pattern,
            entity_type=EntityType.MONEY,
            sub_type=EntitySubType.CURRENCY,
            confidence=0.85,
            description="Monetary amounts with currency symbols"
        ))
        
        # ============================================================
        # PERCENTAGES
        # ============================================================
        
        percent_pattern = re.compile(
            r'(?:\d+(?:\.\d+)?|\d*\.\d+)\s*%'
        )
        self._patterns.append(RegexPattern(
            pattern=percent_pattern,
            entity_type=EntityType.PERCENTAGE,
            sub_type=None,
            confidence=0.95,
            description="Percentage values"
        ))
        
        # Basis points
        bps_pattern = re.compile(
            r'(?:\d+(?:\.\d+)?|\d*\.\d+)\s*(?:bps|basis\s+points?|bp)\b'
        )
        self._patterns.append(RegexPattern(
            pattern=bps_pattern,
            entity_type=EntityType.PERCENTAGE,
            sub_type=EntitySubType.BASIS_POINTS,
            confidence=0.9,
            description="Basis points"
        ))
        
        # ============================================================
        # DATES - Financial Quarters
        # ============================================================
        
        quarter_pattern = re.compile(
            r'\b(?:Q[1-4]|quarter\s+[1-4]|1st\s+quarter|2nd\s+quarter|3rd\s+quarter|4th\s+quarter)\s+(?:FY|Fiscal\s+Year\s+)?\d{2,4}\b'
        )
        self._patterns.append(RegexPattern(
            pattern=quarter_pattern,
            entity_type=EntityType.DATE,
            sub_type=EntitySubType.FINANCIAL_QUARTER,
            confidence=0.9,
            description="Financial quarters"
        ))
        
        # Fiscal years
        fiscal_year = re.compile(
            r'\b(?:FY|Fiscal\s+Year|fiscal\s+year)\s+\d{2,4}\b'
        )
        self._patterns.append(RegexPattern(
            pattern=fiscal_year,
            entity_type=EntityType.DATE,
            sub_type=EntitySubType.FISCAL_YEAR,
            confidence=0.9,
            description="Fiscal year references"
        ))
        
        # Calendar years in financial context
        calendar_year = re.compile(
            r'\b(?:20\d{2}|19\d{2})\b'
        )
        self._patterns.append(RegexPattern(
            pattern=calendar_year,
            entity_type=EntityType.DATE,
            sub_type=EntitySubType.CALENDAR_YEAR,
            confidence=0.6,
            description="Calendar years (low confidence, needs context)"
        ))
        
        # Specific dates (MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD)
        date_pattern = re.compile(
            r'\b(?:\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})\b'
        )
        self._patterns.append(RegexPattern(
            pattern=date_pattern,
            entity_type=EntityType.DATE,
            sub_type=EntitySubType.SPECIFIC_DATE,
            confidence=0.85,
            description="Specific dates"
        ))
        
        # Month names with year
        month_year = re.compile(
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b'
        )
        self._patterns.append(RegexPattern(
            pattern=month_year,
            entity_type=EntityType.DATE,
            sub_type=EntitySubType.MONTH_YEAR,
            confidence=0.85,
            description="Month and year"
        ))
        
        # ============================================================
        # FINANCIAL METRICS
        # ============================================================
        
        # Revenue
        revenue_pattern = re.compile(
            r'\b(?:revenue|sales|turnover|net\s+sales|total\s+revenue|gross\s+revenue)\s*(?:of|was|were|is|at|:|\$)?\s*[\$\d]',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=revenue_pattern,
            entity_type=EntityType.METRIC,
            sub_type=EntitySubType.REVENUE,
            confidence=0.8,
            description="Revenue mentions"
        ))
        
        # EPS
        eps_pattern = re.compile(
            r'\b(?:EPS|earnings\s+per\s+share|diluted\s+EPS|basic\s+EPS|adjusted\s+EPS|GAAP\s+EPS|non-GAAP\s+EPS)\s*(?:of|was|were|is|at|:|\$)?\s*[\$\d]',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=eps_pattern,
            entity_type=EntityType.METRIC,
            sub_type=EntitySubType.EPS,
            confidence=0.9,
            description="EPS mentions"
        ))
        
        # EBITDA
        ebitda_pattern = re.compile(
            r'\b(?:EBITDA|adjusted\s+EBITDA|EBITDA\s+margin)\s*(?:of|was|were|is|at|:|\$)?\s*[\$\d]',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=ebitda_pattern,
            entity_type=EntityType.METRIC,
            sub_type=EntitySubType.EBITDA,
            confidence=0.9,
            description="EBITDA mentions"
        ))
        
        # Profit/Income
        profit_pattern = re.compile(
            r'\b(?:net\s+income|net\s+profit|operating\s+income|operating\s+profit|gross\s+profit|gross\s+income|pre-tax\s+income|pre-tax\s+profit|profit\s+before\s+tax|income\s+before\s+tax)\s*(?:of|was|were|is|at|:|\$)?\s*[\$\d]',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=profit_pattern,
            entity_type=EntityType.METRIC,
            sub_type=EntitySubType.NET_INCOME,
            confidence=0.85,
            description="Profit/Income mentions"
        ))
        
        # Margins
        margin_pattern = re.compile(
            r'\b(?:gross\s+margin|operating\s+margin|net\s+margin|profit\s+margin|EBITDA\s+margin)\s*(?:of|was|were|is|at|:)?\s*\d+(?:\.\d+)?\s*%',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=margin_pattern,
            entity_type=EntityType.METRIC,
            sub_type=EntitySubType.MARGIN,
            confidence=0.9,
            description="Margin mentions"
        ))
        
        # Cash Flow
        cash_flow_pattern = re.compile(
            r'\b(?:free\s+cash\s+flow|FCF|operating\s+cash\s+flow|OCF|net\s+cash|cap\s*ex|capital\s+expenditure|capex)\s*(?:of|was|were|is|at|:|\$)?\s*[\$\d]',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=cash_flow_pattern,
            entity_type=EntityType.METRIC,
            sub_type=EntitySubType.FREE_CASH_FLOW,
            confidence=0.85,
            description="Cash flow mentions"
        ))
        
        # Balance Sheet
        balance_sheet_pattern = re.compile(
            r'\b(?:total\s+assets|total\s+liabilities|shareholders?\s+equity|book\s+value|tangible\s+book|debt|total\s+debt|net\s+debt|cash\s+and\s+equivalents|cash\s+position)\s*(?:of|was|were|is|at|:|\$)?\s*[\$\d]',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=balance_sheet_pattern,
            entity_type=EntityType.METRIC,
            sub_type=EntitySubType.TOTAL_ASSETS,
            confidence=0.8,
            description="Balance sheet metrics"
        ))
        
        # Valuation
        valuation_pattern = re.compile(
            r'\b(?:market\s+cap|market\s+capitalization|enterprise\s+value|EV|P/E|PE\s+ratio|PEG|price\s+to\s+earnings|price\s+to\s+sales|price\s+to\s+book|EV/EBITDA|EV/Revenue)\s*(?:of|was|were|is|at|:)?\s*[\$\d]',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=valuation_pattern,
            entity_type=EntityType.METRIC,
            sub_type=EntitySubType.MARKET_CAP,
            confidence=0.85,
            description="Valuation metrics"
        ))
        
        # Dividends
        dividend_pattern = re.compile(
            r'\b(?:dividend|dividend\s+yield|quarterly\s+dividend|annual\s+dividend|dividend\s+per\s+share|DPS)\s*(?:of|was|were|is|at|:|\$)?\s*[\$\d]',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=dividend_pattern,
            entity_type=EntityType.METRIC,
            sub_type=EntitySubType.DIVIDEND,
            confidence=0.85,
            description="Dividend mentions"
        ))
        
        # Buyback
        buyback_pattern = re.compile(
            r'\b(?:share\s+buyback|stock\s+buyback|repurchase|buyback\s+program|share\s+repurchase)\s*(?:of|was|were|is|at|:|\$)?\s*[\$\d]',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=buyback_pattern,
            entity_type=EntityType.METRIC,
            sub_type=EntitySubType.BUYBACK,
            confidence=0.85,
            description="Buyback mentions"
        ))
        
        # Guidance
        guidance_pattern = re.compile(
            r'\b(?:guidance|outlook|forecast|projection|estimate|target|expects?|anticipates?|projects?)\s*(?:for|of|:)?\s*[\$\d]',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=guidance_pattern,
            entity_type=EntityType.METRIC,
            sub_type=EntitySubType.GUIDANCE,
            confidence=0.75,
            description="Guidance mentions"
        ))
        
        # Analyst Ratings
        rating_pattern = re.compile(
            r'\b(?:buy|sell|hold|overweight|underweight|outperform|underperform|strong\s+buy|strong\s+sell|neutral|equal\s+weight|market\s+perform|sector\s+perform|target\s+price|price\s+target)\b',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=rating_pattern,
            entity_type=EntityType.METRIC,
            sub_type=EntitySubType.ANALYST_RATING,
            confidence=0.85,
            description="Analyst ratings"
        ))
        
        # Upgrade/Downgrade
        upgrade_downgrade = re.compile(
            r'\b(?:upgraded?|downgraded?|raised?|lowered?|initiated?|resumed?|reiterated?)\s+(?:to|from)?\s*(?:buy|sell|hold|overweight|underweight|outperform|underperform|strong\s+buy|strong\s+sell|neutral)',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=upgrade_downgrade,
            entity_type=EntityType.EVENT,
            sub_type=EntitySubType.ANALYST_RATING,
            confidence=0.9,
            description="Rating changes"
        ))
        
        # ============================================================
        # SEC FILING REFERENCES
        # ============================================================
        
        sec_filing = re.compile(
            r'\b(?:8-K|10-K|10-Q|S-1|S-3|S-4|424B[1-5]|DEF\s+14A|13[DG]|13F|144|Form\s+(?:8-K|10-K|10-Q|S-1|S-3|S-4|4|8|11|13|15|18|20|40|424|DEF))\b',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=sec_filing,
            entity_type=EntityType.EVENT,
            sub_type=EntitySubType.REGULATORY_FILING,
            confidence=0.95,
            description="SEC filing references"
        ))
        
        # ============================================================
        # CURRENCY CODES
        # ============================================================
        
        currency_code = re.compile(
            r'\b(?:USD|EUR|GBP|JPY|CNY|CAD|AUD|CHF|HKD|SGD|INR|KRW|BRL|MXN|ZAR|SEK|NOK|DKK|TRY|PLN|CZK|HUF|ILS|CLP|COP|PEN|ARS|VND|THB|MYR|PHP|IDR|TWD|RUB|SAR|AED|QAR|KWD|BHD|OMR|JOD|LBP|EGP|PKR|BDT|LKR|NPR|MUR|MAD|TND|DZD|KES|UGX|TZS|ZMW|BWP|NAD|SZL|LSL|MWK|GHS|NGN|XOF|XAF|CDF|ETB|KMF|DJF|ERN|SOS|SDG|SSP|STN|CVE|KMF|MGA|KYD|BMD|BSD|BBD|BZD|XCD|ANG|AWG|SRD|GYD|HTG|JMD|KYD|TTD|VEF|PYG|UYU|BOB|CLF|COU|UYI|UYW|CHE|CHW|CLF|COU|MXV|UYI|UYW|XAU|XAG|XPT|XPD|XDR|XTS|XBB|XBC|XBD|ZWL)\b'
        )
        self._patterns.append(RegexPattern(
            pattern=currency_code,
            entity_type=EntityType.CURRENCY,
            sub_type=None,
            confidence=0.9,
            description="ISO currency codes"
        ))
        
        # ============================================================
        # PRICE TARGETS
        # ============================================================
        
        price_target = re.compile(
            r'\b(?:price\s+target|target\s+price|PT)\s*(?:of|at|:|\$)?\s*\$?\d+(?:\.\d+)?',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=price_target,
            entity_type=EntityType.METRIC,
            sub_type=EntitySubType.PRICE_TARGET,
            confidence=0.9,
            description="Price targets"
        ))
        
        # ============================================================
        # CREDIT RATINGS
        # ============================================================
        
        credit_rating = re.compile(
            r'\b(?:AAA|AA\+|AA|AA\-|A\+|A|A\-|BBB\+|BBB|BBB\-|BB\+|BB|BB\-|B\+|B|B\-|CCC\+|CCC|CCC\-|CC|C|D|NR|WR|Aaa|Aa1|Aa2|Aa3|A1|A2|A3|Baa1|Baa2|Baa3|Ba1|Ba2|Ba3|B1|B2|B3|Caa1|Caa2|Caa3|Ca|C)\s+(?:rating|outlook|credit|debt|bond)',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=credit_rating,
            entity_type=EntityType.METRIC,
            sub_type=EntitySubType.CREDIT_RATING,
            confidence=0.95,
            description="Credit ratings"
        ))
        
        # ============================================================
        # EARNINGS EVENTS
        # ============================================================
        
        earnings_event = re.compile(
            r'\b(?:earnings\s+call|earnings\s+presentation|quarterly\s+call|Q[1-4]\s+earnings|annual\s+meeting|shareholder\s+meeting|investor\s+day|analyst\s+day|capital\s+markets\s+day)\b',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=earnings_event,
            entity_type=EntityType.EVENT,
            sub_type=EntitySubType.EARNINGS_RELEASE,
            confidence=0.9,
            description="Earnings events"
        ))
        
        # ============================================================
        # M&A TERMS
        # ============================================================
        
        ma_terms = re.compile(
            r'\b(?:merger|acquisition|acquire|acquired|takeover|buyout|tender\s+offer|hostile\s+bid|friendly\s+merger|all\s+stock|all\s+cash|cash\s+and\s+stock|stock\s+for\s+stock|asset\s+sale|divestiture|spin[-\s]?off|split[-\s]?off|carve[-\s]?out|joint\s+venture|strategic\s+partnership|strategic\s+alliance)\b',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=ma_terms,
            entity_type=EntityType.EVENT,
            sub_type=EntitySubType.MERGER_ACQUISITION,
            confidence=0.85,
            description="M&A terminology"
        ))
        
        # ============================================================
        # STOCK SPLIT
        # ============================================================
        
        stock_split = re.compile(
            r'\b(?:stock\s+split|share\s+split|reverse\s+split|forward\s+split|split\s+ratio|for\s+\d+\s+split|\d+[-\s]?for[-\s]?\d+)\b',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=stock_split,
            entity_type=EntityType.EVENT,
            sub_type=EntitySubType.STOCK_SPLIT,
            confidence=0.9,
            description="Stock splits"
        ))
        
        # ============================================================
        # IPO
        # ============================================================
        
        ipo_pattern = re.compile(
            r'\b(?:IPO|initial\s+public\s+offering|going\s+public|listing|direct\s+listing|SPAC|blank\s+check|de-SPAC|SPAC\s+merger)\b',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=ipo_pattern,
            entity_type=EntityType.EVENT,
            sub_type=EntitySubType.IPO,
            confidence=0.9,
            description="IPO references"
        ))
        
        # ============================================================
        # BANKRUPTCY
        # ============================================================
        
        bankruptcy = re.compile(
            r'\b(?:bankruptcy|Chapter\s+11|Chapter\s+7|Chapter\s+13|insolvency|liquidation|restructuring|reorganization|debtor\s+in\s+possession|DIP\s+financing|creditor\s+committee)\b',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=bankruptcy,
            entity_type=EntityType.EVENT,
            sub_type=EntitySubType.BANKRUPTCY,
            confidence=0.9,
            description="Bankruptcy references"
        ))
        
        # ============================================================
        # LAWSUIT/LITIGATION
        # ============================================================
        
        lawsuit = re.compile(
            r'\b(?:lawsuit|litigation|sued|sues|suing|legal\s+action|class\s+action|securities\s+fraud|patent\s+infringement|antitrust|regulatory\s+investigation|DOJ|SEC\s+investigation|CFTC|FTC|state\s+AG|attorney\s+general)\b',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=lawsuit,
            entity_type=EntityType.EVENT,
            sub_type=EntitySubType.LAWSUIT,
            confidence=0.85,
            description="Lawsuit references"
        ))
        
        # ============================================================
        # PRODUCT LAUNCHES
        # ============================================================
        
        product_launch = re.compile(
            r'\b(?:launches?|launched|introducing|introduces?|unveils?|unveiled|releases?|released|announces?|announced)\s+(?:new\s+)?(?:product|service|platform|feature|device|model|version)\b',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=product_launch,
            entity_type=EntityType.EVENT,
            sub_type=EntitySubType.PRODUCT_LAUNCH,
            confidence=0.8,
            description="Product launches"
        ))
        
        # ============================================================
        # PARTNERSHIP
        # ============================================================
        
        partnership = re.compile(
            r'\b(?:partnership|partner\s+with|collaboration|collaborates?|alliance|strategic\s+alliance|joint\s+venture|JV|memorandum\s+of\s+understanding|MOU|letter\s+of\s+intent|LOI)\b',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=partnership,
            entity_type=EntityType.EVENT,
            sub_type=EntitySubType.PARTNERSHIP,
            confidence=0.8,
            description="Partnerships"
        ))
        
        # ============================================================
        # REGULATION/POLICY
        # ============================================================
        
        regulation = re.compile(
            r'\b(?:regulation|regulatory|policy|legislation|bill|act|law|rule|directive|guideline|compliance|basel\s+[IV]|dodd[-\s]?frank|sarbanes[-\s]?oxley|mi[f]?[di]?[di]?|gdpr|ccpa|sox|volcker\s+rule|stress\s+test|CCAR|DFAST|capital\s+requirement|liquidity\s+coverage|net\s+stable\s+funding)\b',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=regulation,
            entity_type=EntityType.EVENT,
            sub_type=EntitySubType.REGULATION,
            confidence=0.75,
            description="Regulatory references"
        ))
        
        # ============================================================
        # INTEREST RATE DECISIONS
        # ============================================================
        
        rate_decision = re.compile(
            r'\b(?:interest\s+rate|fed\s+funds\s+rate|discount\s+rate|federal\s+funds|policy\s+rate|repo\s+rate|reverse\s+repo|SOFR|LIBOR|EURIBOR|SONIA|ESTR|TONA|SARON)\s*(?:decision|hike|cut|increase|decrease|raise|lower|hold|unchanged|pause|pivot)\b',
            re.IGNORECASE
        )
        self._patterns.append(RegexPattern(
            pattern=rate_decision,
            entity_type=EntityType.EVENT,
            sub_type=EntitySubType.INTEREST_RATE_DECISION,
            confidence=0.9,
            description="Interest rate decisions"
        ))
        
        logger.info(f"Compiled {len(self._patterns)} regex patterns")
        
    def extract(self, text: str) -> List[Entity]:
        """
        Extract entities from text using regex patterns.
        
        Args:
            text: Input text to extract entities from
            
        Returns:
            List of extracted entities
        """
        entities = []
        
        for pattern_obj in self._patterns:
            matches = pattern_obj.pattern.finditer(text)
            for match in matches:
                # Get matched text
                matched_text = match.group(pattern_obj.group_name) if pattern_obj.group_name != "match" else match.group(0)
                matched_text = matched_text or match.group(0)
                
                start_char = match.start()
                end_char = match.end()
                
                # Normalize if function provided
                normalized = matched_text
                if pattern_obj.normalize_fn:
                    try:
                        normalized = pattern_obj.normalize_fn(matched_text)
                    except Exception:
                        pass
                
                # Create entity
                entity = Entity(
                    text=matched_text,
                    entity_type=pattern_obj.entity_type,
                    sub_type=pattern_obj.sub_type,
                    confidence=pattern_obj.confidence,
                    normalized_value=normalized,
                    start_char=start_char,
                    end_char=end_char,
                    validation_method="regex",
                    metadata={"pattern_description": pattern_obj.description}
                )
                
                entities.append(entity)
                
        # Sort by position
        entities.sort(key=lambda e: (e.start_char, e.end_char))
        
        return entities
        
    def extract_by_type(self, text: str, entity_type: EntityType) -> List[Entity]:
        """Extract entities of a specific type."""
        all_entities = self.extract(text)
        return [e for e in all_entities if e.entity_type == entity_type]
        
    def get_patterns(self) -> List[RegexPattern]:
        """Get all compiled patterns."""
        return self._patterns.copy()
        
    def add_pattern(self, pattern: RegexPattern) -> None:
        """Add a custom pattern."""
        self._patterns.append(pattern)
        
    def remove_pattern(self, description: str) -> bool:
        """Remove a pattern by description."""
        for i, p in enumerate(self._patterns):
            if p.description == description:
                self._patterns.pop(i)
                return True
        return False


# Singleton instance
_rule_extractor: Optional[RuleBasedExtractor] = None


def get_rule_extractor(config: Optional[Dict[str, Any]] = None) -> RuleBasedExtractor:
    """Get or create the default rule-based extractor."""
    global _rule_extractor
    if _rule_extractor is None:
        _rule_extractor = RuleBasedExtractor(config)
    return _rule_extractor