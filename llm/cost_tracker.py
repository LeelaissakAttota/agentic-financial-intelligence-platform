"""
Logic for calculating costs based on model usage.
Now uses PricingLoader for external pricing configuration.
"""
from typing import Dict
from .pricing import get_loader, calculate_cost


class CostTracker:
    # Pricing per 1M tokens (input, output) - DEPRECATED: Use pricing.yaml instead
    # Kept for backward compatibility
    MODEL_PRICES: Dict[str, Dict[str, float]] = {
        "anthropic/claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
        "anthropic/claude-3-haiku": {"input": 0.25, "output": 1.25},
        "google/gemini-flash-1.5": {"input": 0.075, "output": 0.30},
        "default": {"input": 1.00, "output": 3.00}
    }

    @staticmethod
    def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate cost based on model usage.
        
        Now delegates to PricingLoader for external configuration.
        Falls back to hardcoded MODEL_PRICES for backward compatibility.
        """
        # Use new pricing system
        return calculate_cost(model, prompt_tokens, completion_tokens)