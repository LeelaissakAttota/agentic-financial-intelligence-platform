"""
Model Registry for unified model resolution.
Replaces duplicated routing logic across the codebase.
"""
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set
import yaml

from .pricing import get_loader


class Complexity(Enum):
    """Task complexity levels."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class ModelResolution:
    """Result of model resolution."""
    model: str
    provider: str
    reason: str
    complexity: str


class ModelRegistry:
    """Unified model resolution for agents and complexity levels."""

    def __init__(self, registry_file: Optional[Path] = None):
        """
        Initialize the model registry.
        
        Args:
            registry_file: Path to model_registry.yaml. Defaults to llm/model_registry.yaml.
        """
        if registry_file is None:
            registry_file = Path(__file__).parent / "model_registry.yaml"
        
        self._registry_file = registry_file
        self._agent_models: Dict[str, Dict[str, str]] = {}
        self._complexity_defaults: Dict[str, str] = {}
        self._settings_aliases: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Load model registry from YAML file."""
        if not self._registry_file.exists():
            raise FileNotFoundError(f"Model registry file not found: {self._registry_file}")

        with open(self._registry_file, 'r') as f:
            data = yaml.safe_load(f)

        if not data:
            raise ValueError("Invalid model_registry.yaml: empty")

        self._agent_models = data.get('agent_models', {})
        self._complexity_defaults = data.get('complexity_defaults', {})
        self._settings_aliases = data.get('settings_aliases', {})

    def resolve_model(
        self,
        agent_name: str,
        complexity: Optional[str] = None
    ) -> ModelResolution:
        """
        Resolve model for an agent and complexity.
        
        Args:
            agent_name: Name of the agent (e.g., 'news_agent', 'risk_agent')
            complexity: Task complexity ('simple', 'medium', 'complex')
            
        Returns:
            ModelResolution with model, provider, reason, and complexity
        """
        # Check agent-specific mapping
        if agent_name in self._agent_models:
            agent_mapping = self._agent_models[agent_name]
            
            # Try exact complexity match
            if complexity and complexity in agent_mapping:
                model = agent_mapping[complexity]
                return ModelResolution(
                    model=model,
                    provider=self._get_provider(model),
                    reason=f"Agent '{agent_name}' mapped to '{complexity}' model",
                    complexity=complexity or "unknown"
                )
            
            # Fallback to complexity defaults
            if complexity and complexity in self._complexity_defaults:
                model = self._complexity_defaults[complexity]
                return ModelResolution(
                    model=model,
                    provider=self._get_provider(model),
                    reason=f"Agent '{agent_name}' fallback to complexity '{complexity}' default",
                    complexity=complexity
                )
            
            # If agent has only one model, use it
            if len(agent_mapping) == 1:
                model = list(agent_mapping.values())[0]
                return ModelResolution(
                    model=model,
                    provider=self._get_provider(model),
                    reason=f"Agent '{agent_name}' has single model mapping",
                    complexity=complexity or "unknown"
                )

        # Global complexity defaults
        if complexity and complexity in self._complexity_defaults:
            model = self._complexity_defaults[complexity]
            return ModelResolution(
                model=model,
                provider=self._get_provider(model),
                reason=f"Global complexity '{complexity}' default",
                complexity=complexity
            )

        # Ultimate fallback
        fallback_model = self._complexity_defaults.get('complex', 'anthropic/claude-3.5-sonnet')
        return ModelResolution(
            model=fallback_model,
            provider=self._get_provider(fallback_model),
            reason="Fallback to complex default",
            complexity=complexity or "complex"
        )

    def _get_provider(self, model: str) -> str:
        """Get provider for a model from pricing loader."""
        try:
            loader = get_loader()
            pricing = loader.get_model(model)
            return pricing.provider
        except Exception:
            return "unknown"

    def get_settings_model(self, alias: str) -> str:
        """
        Resolve settings alias to model name.
        
        Args:
            alias: Settings alias (e.g., 'primary_model', 'fast_model')
            
        Returns:
            Model name or alias if not found
        """
        return self._settings_aliases.get(alias, alias)

    def get_agent_complexities(self, agent_name: str) -> List[str]:
        """Get available complexities for an agent."""
        if agent_name in self._agent_models:
            return list(self._agent_models[agent_name].keys())
        return []

    def get_all_agents(self) -> List[str]:
        """Get all configured agents."""
        return list(self._agent_models.keys())

    def get_all_complexities(self) -> List[str]:
        """Get all configured complexity levels."""
        return list(self._complexity_defaults.keys())


# Global singleton instance
_registry: Optional[ModelRegistry] = None


def get_registry() -> ModelRegistry:
    """Get the global ModelRegistry instance."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry


def resolve_model(
    agent_name: str,
    complexity: Optional[str] = None
) -> ModelResolution:
    """
    Resolve model for an agent and complexity.
    
    This is the main entry point for model resolution.
    Replaces model_router.ModelRouter.get_model() and router.model_for().
    
    Args:
        agent_name: Name of the agent (e.g., 'news_agent', 'risk_agent')
        complexity: Task complexity ('simple', 'medium', 'complex')
        
    Returns:
        ModelResolution with model, provider, reason, and complexity
    """
    registry = get_registry()
    return registry.resolve_model(agent_name, complexity)