"""Competitor Intelligence Agent Package."""

from .agent import CompetitorAgent, run_competitor_agent_sync
from .schemas import (
    CompetitorAgentInput,
    CompetitorAgentOutput,
    CompetitorMetricsIn,
    ComparisonRow,
    RankedEntry,
)
from .exceptions import (
    CompetitorAgentError,
    CompetitorAgentInputError,
    CompetitorAgentLLMError,
    CompetitorAgentValidationError,
)

__all__ = [
    "CompetitorAgent",
    "run_competitor_agent_sync",
    "CompetitorAgentInput",
    "CompetitorAgentOutput",
    "CompetitorMetricsIn",
    "ComparisonRow",
    "RankedEntry",
    "CompetitorAgentError",
    "CompetitorAgentInputError",
    "CompetitorAgentLLMError",
    "CompetitorAgentValidationError",
]