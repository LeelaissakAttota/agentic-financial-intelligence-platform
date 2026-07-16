"""Pydantic schemas for the Investment Summary Agent's input/output
contract. See docs/AGENT_PROMPTS.md and the design note for the full
JSON shape and worked testing examples."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

DISCLAIMER_TEXT = (
    "This report is for informational purposes only and does not "
    "constitute financial advice."
)


class InvestmentSummaryInput(BaseModel):
    company: str
    ticker: str
    news_findings: dict
    market_findings: dict
    financial_findings: dict
    competitor_findings: dict
    sentiment_findings: dict
    risk_findings: dict
    data_gaps: list[str] = []


class SourcedPoint(BaseModel):
    point: str
    source: Literal["news", "market", "financial_report", "competitor", "sentiment", "risk"]


class InvestmentSummaryOutput(BaseModel):
    agent: str = "investment_summary_agent"
    company: str
    generated_at: datetime
    executive_summary: str
    strengths: list[SourcedPoint]
    weaknesses: list[SourcedPoint]
    growth_potential: str
    risks_summary: str
    final_ai_opinion: str
    disclaimer: Literal[
        "This report is for informational purposes only and does not constitute financial advice."
    ] = DISCLAIMER_TEXT
    data_gaps_noted: list[str] = []
    confidence: Literal["High", "Medium", "Low"]
