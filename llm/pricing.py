"""
Pricing module for LLM cost calculation.
Loads model pricing from YAML configuration.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import yaml


@dataclass
class ModelPricing:
    """Pricing information for a single model."""
    provider: str
    input_cost_per_million: float
    output_cost_per_million: float
    context_window: int
    aliases: List[str]

    def matches(self, model_name: str) -> bool:
        """Check if model_name matches this model or its aliases."""
        if model_name == self.canonical_name:
            return True
        return model_name in self.aliases

    @property
    def canonical_name(self) -> str:
        """The canonical name is the key used in the pricing dict."""
        # This will be set by the loader
        return getattr(self, '_canonical_name', '')


class PricingLoader:
    """Loads and manages model pricing from YAML configuration."""

    def __init__(self, pricing_file: Optional[Path] = None):
        """
        Initialize the pricing loader.
        
        Args:
            pricing_file: Path to pricing.yaml. Defaults to llm/pricing.yaml.
        """
        if pricing_file is None:
            pricing_file = Path(__file__).parent / "pricing.yaml"
        
        self._pricing_file = pricing_file
        self._models: Dict[str, ModelPricing] = {}
        self._alias_map: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Load pricing from YAML file."""
        if not self._pricing_file.exists():
            raise FileNotFoundError(f"Pricing file not found: {self._pricing_file}")

        with open(self._pricing_file, 'r') as f:
            data = yaml.safe_load(f)

        if not data or 'models' not in data:
            raise ValueError("Invalid pricing.yaml: missing 'models' key")

        self._models = {}
        self._alias_map = {}

        for canonical_name, model_data in data['models'].items():
            pricing = ModelPricing(
                provider=model_data.get('provider', 'unknown'),
                input_cost_per_million=float(model_data.get('input_cost_per_million', 1.0)),
                output_cost_per_million=float(model_data.get('output_cost_per_million', 3.0)),
                context_window=int(model_data.get('context_window', 4096)),
                aliases=model_data.get('aliases', [])
            )
            pricing._canonical_name = canonical_name
            self._models[canonical_name] = pricing

            # Register aliases
            for alias in pricing.aliases:
                self._alias_map[alias.lower()] = canonical_name

    def resolve_model(self, model_name: Optional[str]) -> str:
        """
        Resolve a model name to its canonical name.
        
        Args:
            model_name: Model name or alias
            
        Returns:
            Canonical model name, or 'default' if not found
        """
        if not model_name:
            return "default"
        
        model_lower = model_name.lower()
        
        # Check exact match first
        if model_name in self._models:
            return model_name
        
        # Check alias map
        if model_lower in self._alias_map:
            return self._alias_map[model_lower]
        
        # Check case-insensitive exact match
        for canonical in self._models:
            if canonical.lower() == model_lower:
                return canonical
        
        return "default"

    def get_model(self, model_name: str) -> ModelPricing:
        """Get ModelPricing for a model name (resolves aliases)."""
        canonical = self.resolve_model(model_name)
        return self._models[canonical]

    @property
    def models(self) -> Dict[str, ModelPricing]:
        """Get all loaded models."""
        return self._models.copy()


# Global singleton instance
_loader: Optional[PricingLoader] = None


def get_loader() -> PricingLoader:
    """Get the global PricingLoader instance."""
    global _loader
    if _loader is None:
        _loader = PricingLoader()
    return _loader


def calculate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """
    Calculate cost for a model invocation.
    
    Args:
        model: Model name or alias
        prompt_tokens: Number of prompt/input tokens
        completion_tokens: Number of completion/output tokens
        
    Returns:
        Cost in USD
    """
    loader = get_loader()
    canonical = loader.resolve_model(model)
    pricing = loader.get_model(canonical)
    
    input_cost = (prompt_tokens / 1_000_000) * pricing.input_cost_per_million
    output_cost = (completion_tokens / 1_000_000) * pricing.output_cost_per_million
    
    return round(input_cost + output_cost, 6)


def get_context_window(model: str) -> int:
    """Get the context window for a model."""
    loader = get_loader()
    pricing = loader.get_model(model)
    return pricing.context_window