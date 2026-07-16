"""
Abstract Base Class for LLM Providers.
Defines the interface that all specific clients (OpenRouter, Anthropic, etc.) must implement.
Now includes both sync and async methods.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from .token_tracker import LLMUsage


class LLMProvider(ABC):
    """Abstract base class for LLM providers.
    
    Both sync and async methods are provided. Sync methods are kept for 
    backward compatibility; async methods are preferred for new code.
    """
    
    @abstractmethod
    def send_message(
        self, 
        system_prompt: str, 
        user_message: str, 
        model: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Send a basic text message and return response.
        
        Args:
            system_prompt: System prompt
            user_message: User message
            model: Model name
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            Dict with 'content', 'usage', and optionally 'model' keys
        """
        pass
    
    @abstractmethod
    def generate_json(
        self, 
        system_prompt: str, 
        user_message: str, 
        response_schema: Any, 
        model: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Send a message specifically requesting JSON output.
        
        Args:
            system_prompt: System prompt
            user_message: User message
            response_schema: JSON schema for structured output
            model: Model name
            **kwargs: Additional parameters
            
        Returns:
            Dict with 'content' (parsed JSON) and 'usage' keys
        """
        pass
    
    @abstractmethod
    def track_usage(self, response: Any) -> LLMUsage:
        """Extract token usage and cost from provider response.
        
        Args:
            response: Provider-specific response object
            
        Returns:
            LLMUsage with token counts and cost
        """
        pass
    
    # ============ ASYNC METHODS ============
    
    @abstractmethod
    async def asend_message(
        self, 
        system_prompt: str, 
        user_message: str, 
        model: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Async version of send_message.
        
        Args:
            system_prompt: System prompt
            user_message: User message
            model: Model name
            **kwargs: Additional parameters
            
        Returns:
            Dict with 'content', 'usage', and optionally 'model' keys
        """
        pass
    
    @abstractmethod
    async def agenerate_json(
        self, 
        system_prompt: str, 
        user_message: str, 
        response_schema: Any, 
        model: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Async version of generate_json.
        
        Args:
            system_prompt: System prompt
            user_message: User message
            response_schema: JSON schema for structured output
            model: Model name
            **kwargs: Additional parameters
            
        Returns:
            Dict with 'content' (parsed JSON) and 'usage' keys
        """
        pass