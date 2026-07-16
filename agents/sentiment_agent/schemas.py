"""Pydantic schemas for the Sentiment Analysis Agent's input/output contract.
See docs/AGENT_PROMPTS.md and the design note for the full JSON shape and worked testing examples.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class NewsItemIn(BaseModel):
    title: str
    impact: Literal["positive", "negative", "neutral"]
    date: str


class SocialItemIn(BaseModel):
    platform: str
    text_summary: str
    sentiment: Literal["positive", "negative", "neutral"]
    date: str


class AnalystOpinionIn(BaseModel):
    firm: str
    rating: str
    note_summary: str
    date: str


class SentimentAgentInput(BaseModel):
    company: str
    as_of_date: str
    news_items: list[NewsItemIn] = []
    social_items: list[SocialItemIn] = []
    analyst_opinions: list[AnalystOpinionIn] = []


class SentimentDistribution(BaseModel):
    positive: float
    negative: float
    neutral: float

    @field_validator("neutral")
    @classmethod
    def sums_to_one(cls, v, info):
        total = v + info.data.get("positive", 0) + info.data.get("negative", 0)
        if abs(total - 1.0) > 0.02:
            raise ValueError(f"positive+negative+neutral must sum to 1.0, got {total}")
        return v


class BySource(BaseModel):
    news: SentimentDistribution
    social: SentimentDistribution
    analyst_opinions: SentimentDistribution


class DivergenceFlag(BaseModel):
    detected: bool
    description: str


class SentimentAgentOutput(BaseModel):
    agent: str = "sentiment_agent"
    company: str
    generated_at: datetime
    by_source: BySource
    overall: SentimentDistribution
    overall_market_emotion: Literal[
        "Euphoric", "Optimistic", "Cautiously Optimistic", "Neutral",
        "Cautious", "Pessimistic", "Fearful",
    ]
    emotion_rationale: str
    drivers: list[str]
    divergence_flag: DivergenceFlag
    confidence: Literal["High", "Medium", "Low"]