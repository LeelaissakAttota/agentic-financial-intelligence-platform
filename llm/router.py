"""
Routes a task to the appropriate model tier.
DEPRECATED: Use ModelRegistry.resolve_model() instead.
"""
import warnings
from typing import Literal, Optional

from .model_registry import get_registry, resolve_model, Complexity


# Agent groups for routing
SYNTHESIS_AGENTS = {"manager_agent", "risk_agent", "investment_summary_agent"}
LIGHT_AGENTS = {"news_agent", "market_agent"}
FINANCIAL_REPORT_AGENTS = {"financial_report_agent"}
COMPETITOR_AGENTS = {"competitor_agent"}
SENTIMENT_AGENTS = {"sentiment_agent"}


def model_for(agent_name: str, settings) -> str:
    """
    DEPRECATED: Routes a task to the appropriate model tier.
    
    Use ModelRegistry.resolve_model() instead.
    """
    warnings.warn(
        "router.model_for() is deprecated. Use ModelRegistry.resolve_model() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    registry = get_registry()
    
    # Determine complexity based on agent group
    if agent_name in SYNTHESIS_AGENTS:
        complexity = Complexity.COMPLEX
    elif agent_name in LIGHT_AGENTS:
        complexity = Complexity.SIMPLE
    else:
        complexity = Complexity.COMPLEX
    
    resolution = resolve_model(agent_name, complexity)
    return resolution.model