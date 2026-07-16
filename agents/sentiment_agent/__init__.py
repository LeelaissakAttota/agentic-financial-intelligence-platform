"""Sentiment Analysis Agent Package."""

from .agent import SentimentAgent, run_sentiment_agent_sync
from .schemas import (
    SentimentAgentInput,
    SentimentAgentOutput,
    NewsItemIn,
    SocialItemIn,
    AnalystOpinionIn,
    SentimentDistribution,
    BySource,
    DivergenceFlag,
)
from .exceptions import (
    SentimentAgentError,
    SentimentAgentInputError,
    SentimentAgentLLMError,
    SentimentAgentValidationError,
)

__all__ = [
    "SentimentAgent",
    "run_sentiment_agent_sync",
    "SentimentAgentInput",
    "SentimentAgentOutput",
    "NewsItemIn",
    "SocialItemIn",
    "AnalystOpinionIn",
    "SentimentDistribution",
    "BySource",
    "DivergenceFlag",
    "SentimentAgentError",
    "SentimentAgentInputError",
    "SentimentAgentLLMError",
    "SentimentAgentValidationError",
]