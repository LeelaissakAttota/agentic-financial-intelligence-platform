"""Pydantic schemas for the Risk Management Agent's input/output
contract. See docs/AGENT_PROMPTS.md and the design note for the full
JSON shape, weighting formula, and worked testing examples."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

CATEGORY_WEIGHTS = {
    "market_risk": 0.20,
    "company_risk": 0.30,
    "financial_risk": 0.30,
    "valuation_risk": 0.20,
}


class RiskAgentInput(BaseModel):
    company: str
    news_findings: dict
    market_findings: dict
    financial_findings: dict
    competitor_findings: dict


class RiskFactor(BaseModel):
    factor: str
    source: Literal["news", "market", "financial_report", "competitor"]
    justification: str


class RiskCategory(BaseModel):
    category_score: Optional[int] = None  # 0-100, null if no usable data
    severity: Optional[Literal["Low", "Medium", "High"]] = None
    risk_factors: list[RiskFactor]


class RiskCategories(BaseModel):
    market_risk: RiskCategory
    company_risk: RiskCategory
    financial_risk: RiskCategory
    valuation_risk: RiskCategory


class RiskAgentOutput(BaseModel):
    agent: str = "risk_agent"
    company: str
    generated_at: datetime
    categories: RiskCategories
    overall_risk_score: int
    overall_severity: Literal["Low", "Medium", "High"]
    risk_explanation: str
    confidence: Literal["High", "Medium", "Low"]


def severity_for_score(score: int) -> str:
    """0-33 Low, 34-66 Medium, 67-100 High. See Test 4 in the design
    note for the boundary-consistency regression check."""
    if score <= 33:
        return "Low"
    if score <= 66:
        return "Medium"
    return "High"
