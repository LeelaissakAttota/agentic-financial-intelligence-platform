"""
Pydantic schemas for the Market Analysis Agent.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class PricePoint(BaseModel):
    """Single price data point."""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class TechnicalIndicators(BaseModel):
    """Technical analysis indicators."""
    rsi_14: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_middle: Optional[float] = None
    bollinger_lower: Optional[float] = None


class FinancialMetrics(BaseModel):
    """Fundamental financial metrics."""
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    eps: Optional[float] = None
    eps_growth: Optional[float] = None
    revenue: Optional[float] = None
    revenue_growth: Optional[float] = None
    profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    dividend_payout_ratio: Optional[float] = None
    beta: Optional[float] = None


class MarketContext(BaseModel):
    """Market/sector context data."""
    sector: str
    industry: str
    sector_performance_1m: Optional[float] = None
    sector_performance_3m: Optional[float] = None
    market_cap: Optional[float] = None
    shares_outstanding: Optional[float] = None
    float_shares: Optional[float] = None
    short_interest: Optional[float] = None
    institutional_ownership: Optional[float] = None
    analyst_rating: Optional[str] = None
    analyst_target_price: Optional[float] = None
    beta: Optional[float] = None


class MarketAgentInput(BaseModel):
    """Input for the Market Agent."""
    symbol: str = Field(..., description="Stock symbol (e.g., NVDA)")
    company_name: Optional[str] = Field(None, description="Company name")

    @field_validator('symbol', mode='before')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        return v.strip().upper()


class PriceMovementAnalysis(BaseModel):
    """Price movement narrative analysis."""
    trend_direction: str  # "bullish", "bearish", "neutral", "sideways"
    position_in_range: str  # "near_high", "near_low", "middle", "above_high", "below_low"
    volume_trend: str  # "increasing", "decreasing", "stable"
    key_observations: List[str]


class TechnicalAnalysis(BaseModel):
    """Technical indicators narrative analysis."""
    rsi_interpretation: Optional[str] = None
    moving_averages: Optional[str] = None
    macd_interpretation: Optional[str] = None
    bollinger_bands: Optional[str] = None
    overall_signal: str  # "bullish", "bearish", "neutral"


class FinancialAnalysis(BaseModel):
    """Financial metrics narrative analysis."""
    valuation_assessment: str  # "overvalued", "fairly_valued", "undervalued", "insufficient_data"
    profitability: str  # "strong", "moderate", "weak", "insufficient_data"
    growth_profile: str  # "high_growth", "moderate_growth", "slow_growth", "declining", "insufficient_data"
    financial_health: str  # "strong", "adequate", "concerning", "insufficient_data"
    key_observations: List[str]


class MarketTrendsAnalysis(BaseModel):
    """Market/sector trends narrative analysis."""
    sector_performance: str  # "outperforming", "in_line", "underperforming"
    relative_strength: str  # "strong", "neutral", "weak"
    institutional_sentiment: str  # "bullish", "neutral", "bearish"
    analyst_sentiment: str  # "bullish", "neutral", "bearish"
    key_observations: List[str]


class MarketAgentOutput(BaseModel):
    """Output from the Market Agent."""
    agent: str = "market_agent"
    symbol: str
    company_name: str
    current_price: float
    price_change: float
    price_change_pct: float
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # Raw data references
    week_52_high: float
    week_52_low: float
    avg_volume: int

    # Narrative analyses
    price_movement: PriceMovementAnalysis
    technical_analysis: TechnicalAnalysis
    financial_analysis: FinancialAnalysis
    market_trends: MarketTrendsAnalysis

    # Overall narrative
    overall_narrative: str

    # Confidence
    confidence: str  # "High", "Medium", "Low"


class WorkerResponse(BaseModel):
    """Standardized worker response compatible with Manager Agent."""
    status: str = Field(..., description="Status: 'success' or 'error'")
    data: Optional[Dict[str, Any]] = Field(None, description="Result data")
    error: Optional[str] = Field(None, description="Error message if status is 'error'")
    usage: Optional[Dict[str, Any]] = Field(None, description="Token usage and cost")
