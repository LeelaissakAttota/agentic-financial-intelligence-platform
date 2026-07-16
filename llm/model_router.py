"""
Model Router - routes requests to appropriate model based on complexity.
DEPRECATED: Use ModelRegistry.resolve_model() instead.
"""
import warnings
from typing import Literal, Any

from .model_registry import get_registry, resolve_model, Complexity
from .llm_provider import LLMProvider


class ModelRouter:
    """
    DEPRECATED: Routes requests to the appropriate model based on task complexity.
    
    This class is maintained for backward compatibility.
    Use ModelRegistry.resolve_model() for new code.
    """

    def __init__(self, provider: LLMProvider):
        warnings.warn(
            "ModelRouter is deprecated. Use ModelRegistry.resolve_model() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.provider = provider

    def get_model(self, complexity: Literal["complex", "simple"]) -> str:
        """
        DEPRECATED: Returns the correct model string from settings based on complexity.
        Use ModelRegistry.resolve_model() instead.
        """
        warnings.warn(
            "ModelRouter.get_model() is deprecated. Use ModelRegistry.resolve_model() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        # Map complexity to ModelRegistry complexity
        if complexity == "complex":
            reg_complexity = Complexity.COMPLEX
        else:
            reg_complexity = Complexity.SIMPLE
        
        resolution = resolve_model("manager_agent", reg_complexity)
        return resolution.model

    def call(self, complexity: Literal["complex", "simple"], system_prompt: str, user_message: str, **kwargs):
        """DEPRECATED: Use ModelRegistry with provider directly."""
        warnings.warn(
            "ModelRouter.call() is deprecated. Use provider directly with ModelRegistry.",
            DeprecationWarning,
            stacklevel=2
        )
        model = self.get_model(complexity)
        return self.provider.send_message(system_prompt, user_message, model=model, **kwargs)

    def call_json(self, complexity: Literal["complex", "simple"], system_prompt: str, user_message: str, schema: Any, **kwargs):
        """DEPRECATED: Use ModelRegistry with provider directly."""
        warnings.warn(
            "ModelRouter.call_json() is deprecated. Use provider directly with ModelRegistry.",
            DeprecationWarning,
            stacklevel=2
        )
        model = self.get_model(complexity)
        return self.provider.generate_json(system_prompt, user_message, schema, model=model, **kwargs)