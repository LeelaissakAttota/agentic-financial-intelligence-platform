"""
Market Analysis Agent Package
"""

from .market_agent import MarketAgent, run_market_agent_sync
from .schemas import (
    MarketAgentInput,
    MarketAgentOutput,
    WorkerResponse,
    PriceMovementAnalysis,
    TechnicalAnalysis,
    FinancialAnalysis,
    MarketTrendsAnalysis,
    TechnicalIndicators,
    FinancialMetrics,
    MarketContext,
)
from .prompts import (
    SYSTEM_PROMPT,
    PRICE_MOVEMENT_PROMPT,
    TECHNICAL_PROMPT,
    FINANCIAL_PROMPT,
    MARKET_TRENDS_PROMPT,
)
from .exceptions import (
    MarketAgentError,
    MarketAgentInputError,
    MarketAgentDataError,
    MarketAgentLLMError,
    MarketAgentParseError,
    MarketAgentValidationError,
)

__all__ = [
    "MarketAgent",
    "run_market_agent_sync",
    "MarketAgentInput",
    "MarketAgentOutput",
    "WorkerResponse",
    "PriceMovementAnalysis",
    "TechnicalAnalysis",
    "FinancialAnalysis",
    "MarketTrendsAnalysis",
    "TechnicalIndicators",
    "FinancialMetrics",
    "MarketContext",
    "SYSTEM_PROMPT",
    "PRICE_MOVEMENT_PROMPT",
    "TECHNICAL_PROMPT",
    "FINANCIAL_PROMPT",
    "MARKET_TRENDS_PROMPT",
    "MarketAgentError",
    "MarketAgentInputError",
    "MarketAgentDataError",
    "MarketAgentLLMError",
    "MarketAgentParseError",
    "MarketAgentValidationError",
]