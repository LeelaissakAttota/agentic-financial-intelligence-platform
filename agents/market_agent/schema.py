"""Pydantic schemas for the Market Data Agent's input/output contract.
See docs/AGENT_PROMPTS.md and the Market Data Agent design note for
the full JSON shape and worked testing examples."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class PriceMovement(BaseModel):
    current_price: float
    change_pct_1d: float
    change_pct_30d: float
    fifty_two_week_high: float = Field(alias="52_week_high")
    fifty_two_week_low: float = Field(alias="52_week_low")
    avg_volume_30d: int
    volume_today: int

    class Config:
        populate_by_name = True


class TechnicalIndicators(BaseModel):
    rsi_14: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None


class FinancialMetrics(BaseModel):
    pe_ratio: Optional[float] = None
    pe_ratio_5y_avg: Optional[float] = None
    pb_ratio: Optional[float] = None
    eps_ttm: Optional[float] = None
    dividend_yield_pct: Optional[float] = None


class MarketTrends(BaseModel):
    sector: Optional[str] = None
    sector_index_change_30d_pct: Optional[float] = None
    stock_change_30d_pct: Optional[float] = None
    peer_avg_change_30d_pct: Optional[float] = None


class MarketAgentInput(BaseModel):
    company: str
    ticker: str
    as_of_date: str
    price_movement: PriceMovement
    technical_indicators: TechnicalIndicators
    financial_metrics: FinancialMetrics
    market_trends: MarketTrends


class RawMetrics(BaseModel):
    price_movement: PriceMovement
    technical_indicators: TechnicalIndicators
    financial_metrics: FinancialMetrics
    market_trends: MarketTrends


class MarketAnalysis(BaseModel):
    price_movement: str
    technical_indicators: str
    financial_metrics: str
    market_trends: str


class MarketAgentOutput(BaseModel):
    agent: str = "market_agent"
    company: str
    generated_at: datetime
    raw_metrics: RawMetrics
    analysis: MarketAnalysis
    overall_narrative: str
    confidence: Literal["High", "Medium", "Low"]
