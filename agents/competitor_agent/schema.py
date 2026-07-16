"""Pydantic schemas for the Competitor Intelligence Agent's
input/output contract. See docs/AGENT_PROMPTS.md and the design note
for the full JSON shape and worked testing examples.
"""

from datetime import datetime
from typing import Literal, Optional, Union

from pydantic import BaseModel


class CompetitorMetricsIn(BaseModel):
    name: str
    revenue_ttm: Optional[str] = None
    revenue_growth_yoy_pct: Optional[float] = None
    market_share_pct: Optional[float] = None
    technology_notes: Optional[str] = None
    known_risks: list[str] = []


class CompetitorAgentInput(BaseModel):
    company: str
    ticker: str
    segment: str
    target_metrics: CompetitorMetricsIn
    competitors: list[CompetitorMetricsIn]


class ComparisonRow(BaseModel):
    name: str
    revenue_ttm: Union[str, float]
    revenue_growth_yoy_pct: Union[float, str]  # numeric or "not available"
    market_share_pct: Union[float, str]
    technology_summary: str
    competitive_advantage: str
    key_risks: list[str]


class RankedEntry(BaseModel):
    rank: int
    name: str
    reasoning: str


class CompetitorAgentOutput(BaseModel):
    agent: str = "competitor_agent"
    company: str
    generated_at: datetime
    segment: str
    comparison_table: list[ComparisonRow]
    positioning_narrative: str
    ranked_by_strength: list[RankedEntry]
    confidence: Literal["High", "Medium", "Low"]