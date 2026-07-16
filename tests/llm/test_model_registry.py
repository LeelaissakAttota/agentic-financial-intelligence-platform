"""
Unit tests for llm.model_registry module.
Tests the ModelRegistry and model resolution logic.
"""
import pytest
from pathlib import Path

from llm.model_registry import (
    ModelRegistry,
    ModelResolution,
    get_registry,
    resolve_model,
)
from llm.pricing import get_loader


class TestModelRegistry:
    """Tests for the ModelRegistry class."""

    def test_loads_yaml_successfully(self):
        """ModelRegistry should load model_registry.yaml without errors."""
        registry = ModelRegistry()
        assert registry._agent_models is not None
        assert len(registry._agent_models) > 0

    def test_default_complexities_exist(self):
        """Complexity defaults should be configured."""
        registry = ModelRegistry()
        assert "complex" in registry._complexity_defaults
        assert "medium" in registry._complexity_defaults
        assert "simple" in registry._complexity_defaults

    def test_known_agents_loaded(self):
        """Known agents from registry should be loaded."""
        registry = ModelRegistry()
        expected_agents = {
            "manager_agent", "risk_agent", "investment_summary_agent",
            "news_agent", "market_agent", "financial_report_agent",
            "sentiment_agent", "competitor_agent"
        }
        for agent in expected_agents:
            assert agent in registry._agent_models, f"Agent {agent} not found"

    def test_settings_aliases_loaded(self):
        """Settings aliases should be loaded."""
        registry = ModelRegistry()
        assert "primary_model" in registry._settings_aliases
        assert "fast_model" in registry._settings_aliases
        assert registry._settings_aliases["primary_model"] == "anthropic/claude-sonnet-5"
        assert registry._settings_aliases["fast_model"] == "anthropic/claude-3-haiku"

    def test_resolve_model_agent_explicit(self):
        """Agent with explicit complexity mapping should resolve correctly."""
        registry = ModelRegistry()
        resolution = registry.resolve_model("risk_agent", "complex")
        assert resolution.model == "anthropic/claude-sonnet-5"
        assert resolution.provider == "openrouter"
        assert "risk_agent" in resolution.reason
        assert resolution.complexity == "complex"

    def test_resolve_model_agent_simple(self):
        """Simple complexity agent should resolve to haiku."""
        registry = ModelRegistry()
        resolution = registry.resolve_model("news_agent", "simple")
        assert resolution.model == "anthropic/claude-3-haiku"
        assert resolution.provider == "openrouter"
        assert "news_agent" in resolution.reason

    def test_resolve_model_agent_medium(self):
        """Medium complexity agent should resolve to sonnet-5."""
        registry = ModelRegistry()
        resolution = registry.resolve_model("market_agent", "medium")
        assert resolution.model == "anthropic/claude-sonnet-5"
        assert resolution.provider == "openrouter"

    def test_resolve_model_fallback_to_complexity_default(self):
        """Agent without explicit mapping should fall back to complexity default."""
        registry = ModelRegistry()
        # Use an unknown agent
        resolution = registry.resolve_model("unknown_agent", "simple")
        assert resolution.model == "anthropic/claude-3-haiku"
        assert "fallback" in resolution.reason.lower() or "default" in resolution.reason.lower()

    def test_resolve_model_no_complexity_defaults_to_medium(self):
        """When no complexity specified, should use medium default."""
        registry = ModelRegistry()
        resolution = registry.resolve_model("risk_agent", None)
        assert resolution.model == "anthropic/claude-sonnet-5"

    def test_resolve_settings_alias(self):
        """Settings aliases should resolve to models."""
        registry = ModelRegistry()
        assert registry.get_settings_model("primary_model") == "anthropic/claude-sonnet-5"
        assert registry.get_settings_model("fast_model") == "anthropic/claude-3-haiku"
        assert registry.get_settings_model("unknown_alias") == "unknown_alias"

    def test_get_agent_complexities(self):
        """Get available complexities for an agent."""
        registry = ModelRegistry()
        complexities = registry.get_agent_complexities("risk_agent")
        assert "complex" in complexities

    def test_get_all_agents(self):
        """Get all registered agents."""
        registry = ModelRegistry()
        agents = registry.get_all_agents()
        assert len(agents) >= 8
        assert "manager_agent" in agents
        assert "news_agent" in agents

    def test_get_all_complexities(self):
        """Get all configured complexity levels."""
        registry = ModelRegistry()
        complexities = registry.get_all_complexities()
        assert "simple" in complexities
        assert "medium" in complexities
        assert "complex" in complexities


class TestGlobalFunctions:
    """Tests for global helper functions."""

    def test_get_registry_singleton(self):
        """get_registry should return same instance."""
        registry1 = get_registry()
        registry2 = get_registry()
        assert registry1 is registry2

    def test_resolve_model_global_function(self):
        """Global resolve_model function should work."""
        resolution = resolve_model("news_agent", "simple")
        assert resolution.model == "anthropic/claude-3-haiku"
        assert resolution.provider == "openrouter"
        assert isinstance(resolution, ModelResolution)

    def test_resolve_model_returns_model_resolution(self):
        """resolve_model should return ModelResolution dataclass."""
        resolution = resolve_model("manager_agent", "complex")
        assert isinstance(resolution, ModelResolution)
        assert hasattr(resolution, 'model')
        assert hasattr(resolution, 'provider')
        assert hasattr(resolution, 'reason')
        assert hasattr(resolution, 'complexity')


class TestModelResolution:
    """Tests for ModelResolution dataclass."""

    def test_model_resolution_structure(self):
        """ModelResolution should have all required fields."""
        resolution = ModelResolution(
            model="test-model",
            provider="test-provider",
            reason="test reason",
            complexity="complex"
        )
        assert resolution.model == "test-model"
        assert resolution.provider == "test-provider"
        assert resolution.reason == "test reason"
        assert resolution.complexity == "complex"


class TestPricingIntegration:
    """Tests ensuring model registry works with pricing system."""

    def test_registry_provider_matches_pricing(self):
        """Registry resolved provider should match pricing loader."""
        registry = ModelRegistry()
        loader = get_loader()

        for agent in ["risk_agent", "news_agent", "market_agent"]:
            for complexity in ["simple", "medium", "complex"]:
                resolution = registry.resolve_model(agent, complexity)
                pricing = loader.get_model(resolution.model)
                # Provider from registry should match pricing loader
                assert resolution.provider == pricing.provider, \
                    f"Provider mismatch for {resolution.model}: {resolution.provider} vs {pricing.provider}"

    def test_resolved_models_exist_in_pricing(self):
        """All resolved models should exist in pricing configuration."""
        registry = ModelRegistry()
        loader = get_loader()

        for agent in registry.get_all_agents():
            for complexity in ["simple", "medium", "complex"]:
                resolution = registry.resolve_model(agent, complexity)
                canonical = loader.resolve_model(resolution.model)
                assert canonical != "default" or resolution.model == "default", \
                    f"Model {resolution.model} not found in pricing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])