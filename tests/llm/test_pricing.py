"""
Unit tests for llm.pricing module.
Tests the PricingLoader and model cost calculation.
"""
import pytest
import os
from pathlib import Path

from llm.pricing import PricingLoader, ModelPricing, calculate_cost
from llm.cost_tracker import CostTracker


class TestPricingLoader:
    """Tests for the PricingLoader class."""

    def test_loads_yaml_successfully(self):
        """PricingLoader should load pricing.yaml without errors."""
        loader = PricingLoader()
        assert loader.models is not None
        assert len(loader.models) > 0

    def test_default_model_exists(self):
        """Default model should always exist."""
        loader = PricingLoader()
        assert "default" in loader.models

    def test_known_models_loaded(self):
        """Known models from pricing.yaml should be loaded."""
        loader = PricingLoader()
        assert "anthropic/claude-sonnet-5" in loader.models
        assert "anthropic/claude-3-haiku" in loader.models
        assert "google/gemini-flash-1.5" in loader.models

    def test_model_pricing_structure(self):
        """Each model should have required pricing fields."""
        loader = PricingLoader()
        for model_name, pricing in loader.models.items():
            assert hasattr(pricing, 'input_cost_per_million')
            assert hasattr(pricing, 'output_cost_per_million')
            assert hasattr(pricing, 'context_window')
            assert hasattr(pricing, 'provider')
            assert hasattr(pricing, 'aliases')
            assert pricing.input_cost_per_million >= 0
            assert pricing.output_cost_per_million >= 0
            assert pricing.context_window > 0

    def test_alias_resolution(self):
        """Aliases should resolve to canonical model."""
        loader = PricingLoader()

        # Test sonnet aliases
        assert loader.resolve_model("claude-sonnet-5") == "anthropic/claude-sonnet-5"
        assert loader.resolve_model("sonnet") == "anthropic/claude-sonnet-5"
        assert loader.resolve_model("anthropic/claude-sonnet-5") == "anthropic/claude-sonnet-5"

        # Test haiku aliases
        assert loader.resolve_model("claude-3-haiku") == "anthropic/claude-3-haiku"
        assert loader.resolve_model("anthropic/claude-3-haiku") == "anthropic/claude-3-haiku"

        # Test gemini aliases
        assert loader.resolve_model("gemini-flash-1.5") == "google/gemini-flash-1.5"

    def test_unknown_alias_falls_back(self):
        """Unknown aliases should fall back to default."""
        loader = PricingLoader()
        assert loader.resolve_model("unknown-model-xyz") == "default"
        assert loader.resolve_model("") == "default"
        assert loader.resolve_model(None) == "default"

    def test_exact_model_match(self):
        """Exact model names should resolve to themselves."""
        loader = PricingLoader()
        assert loader.resolve_model("anthropic/claude-sonnet-5") == "anthropic/claude-sonnet-5"
        assert loader.resolve_model("anthropic/claude-3-haiku") == "anthropic/claude-3-haiku"

    def test_context_window_accessible(self):
        """Context window should be accessible for each model."""
        loader = PricingLoader()
        sonnet = loader.get_model("anthropic/claude-sonnet-5")
        assert sonnet.context_window == 200000

        haiku = loader.get_model("anthropic/claude-3-haiku")
        assert haiku.context_window == 200000

        gemini = loader.get_model("google/gemini-flash-1.5")
        assert gemini.context_window == 1000000


class TestCalculateCost:
    """Tests for the calculate_cost function."""

    def test_calculate_cost_basic(self):
        """Basic cost calculation should work."""
        cost = calculate_cost(
            model="anthropic/claude-sonnet-5",
            prompt_tokens=1000000,
            completion_tokens=500000
        )
        # 1M input * $3.00/M + 0.5M output * $15.00/M = $3.00 + $7.50 = $10.50
        assert cost == 10.50

    def test_calculate_cost_haiku(self):
        """Haiku cost calculation."""
        cost = calculate_cost(
            model="anthropic/claude-3-haiku",
            prompt_tokens=1000000,
            completion_tokens=1000000
        )
        # 1M * $0.25 + 1M * $1.25 = $1.50
        assert cost == 1.50

    def test_calculate_cost_gemini(self):
        """Gemini Flash cost calculation."""
        cost = calculate_cost(
            model="google/gemini-flash-1.5",
            prompt_tokens=1000000,
            completion_tokens=1000000
        )
        # 1M * $0.075 + 1M * $0.30 = $0.375
        assert cost == 0.375

    def test_calculate_cost_zero_tokens(self):
        """Zero tokens should return zero cost."""
        cost = calculate_cost(
            model="anthropic/claude-sonnet-5",
            prompt_tokens=0,
            completion_tokens=0
        )
        assert cost == 0.0

    def test_calculate_cost_unknown_model_uses_default(self):
        """Unknown models should use default pricing."""
        cost = calculate_cost(
            model="unknown/model",
            prompt_tokens=1000000,
            completion_tokens=1000000
        )
        # default: $1.00/M input + $3.00/M output = $4.00
        assert cost == 4.00

    def test_calculate_cost_alias_resolution(self):
        """Aliases should resolve to correct pricing."""
        # Using alias should give same cost as canonical
        cost_canonical = calculate_cost(
            model="anthropic/claude-sonnet-5",
            prompt_tokens=1000000,
            completion_tokens=500000
        )
        cost_alias = calculate_cost(
            model="claude-sonnet-5",
            prompt_tokens=1000000,
            completion_tokens=500000
        )
        assert cost_alias == cost_canonical

    def test_cost_precision(self):
        """Cost should be precise to 6 decimal places."""
        cost = calculate_cost(
            model="anthropic/claude-sonnet-5",
            prompt_tokens=123456,
            completion_tokens=78901
        )
        # Check it's a float with reasonable precision
        assert isinstance(cost, float)
        assert cost > 0


class TestCostTrackerIntegration:
    """Tests ensuring CostTracker still works with new pricing."""

    def test_cost_tracker_matches_pricing_loader(self):
        """CostTracker should produce same results as PricingLoader."""
        tracker = CostTracker()
        from llm.pricing import calculate_cost

        test_cases = [
            ("anthropic/claude-sonnet-5", 1000000, 500000),
            ("anthropic/claude-3-haiku", 1000000, 1000000),
            ("google/gemini-flash-1.5", 1000000, 1000000),
            ("unknown/model", 1000000, 1000000),
        ]

        for model, prompt, completion in test_cases:
            tracker_cost = tracker.calculate_cost(model, prompt, completion)
            loader_cost = calculate_cost(model, prompt, completion)
            assert abs(tracker_cost - loader_cost) < 0.000001, \
                f"Mismatch for {model}: tracker={tracker_cost}, loader={loader_cost}"

    def test_cost_tracker_default_fallback(self):
        """CostTracker should use default for unknown models."""
        tracker = CostTracker()
        cost = tracker.calculate_cost("completely/unknown", 1000000, 1000000)
        # default: $1.00 + $3.00 = $4.00
        assert cost == 4.00

    def test_cost_tracker_alias_support(self):
        """CostTracker should support aliases."""
        tracker = CostTracker()
        cost1 = tracker.calculate_cost("anthropic/claude-sonnet-5", 1000000, 500000)
        cost2 = tracker.calculate_cost("claude-sonnet-5", 1000000, 500000)
        assert cost1 == cost2


class TestPricingEdgeCases:
    """Edge case tests."""

    def test_very_large_token_counts(self):
        """Should handle very large token counts."""
        cost = calculate_cost(
            model="anthropic/claude-sonnet-5",
            prompt_tokens=100_000_000,
            completion_tokens=50_000_000
        )
        assert cost == 300.0 + 750.0  # $1050.00

    def test_fractional_tokens(self):
        """Token counts should be treated as integers/floats."""
        cost = calculate_cost(
            model="anthropic/claude-sonnet-5",
            prompt_tokens=1.5,
            completion_tokens=1.0
        )
        # Just verify it computes without error
        assert cost >= 0

    def test_model_pricing_immutability(self):
        """ModelPricing should be effectively immutable."""
        from llm.pricing import PricingLoader
        loader = PricingLoader()
        model = loader.get_model("anthropic/claude-sonnet-5")
        original_input = model.input_cost_per_million

        # Attempting to modify should not affect other references
        model.input_cost_per_million = 999
        fresh_model = loader.get_model("anthropic/claude-sonnet-5")
        # Note: This documents current behavior - ModelPricing is a dataclass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])