"""
Base LLM Client with shared retry logic, JSON extraction, and error handling.
Now includes async-first design with sync wrappers for backward compatibility.
"""
import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .llm_provider import LLMProvider
from .token_tracker import LLMUsage
from .cost_tracker import CostTracker
from .exceptions import (
    LLMError,
    LLMProviderError,
    LLMAuthenticationError,
    LLMTimeoutError,
    LLMParseError,
)
from .json_utils import extract_json

logger = logging.getLogger(__name__)


class BaseLLMClient(LLMProvider):
    """
    Base class for LLM provider clients.

    Provides:
    - Exponential backoff retry logic (sync and async)
    - JSON extraction from responses
    - Standardized error handling
    - Cost tracking integration
    - Timeout handling
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        timeout: float = 60.0,
    ):
        """
        Initialize base client.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
            timeout: Request timeout in seconds
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.timeout = timeout
        self._cost_tracker = CostTracker()

    def _resolve_model(self, model: Optional[str]) -> Optional[str]:
        """
        Resolve model alias to actual model name.
        Subclasses can override to provide custom alias resolution.
        """
        return model

    def _extract_json(self, text: str) -> Any:
        """
        Extract JSON from LLM response text.

        Uses the shared json_utils.extract_json function.

        Args:
            text: Raw response text from LLM

        Returns:
            Parsed JSON object

        Raises:
            LLMParseError: If no valid JSON found
        """
        try:
            return extract_json(text)
        except ValueError as e:
            raise LLMParseError(f"Failed to extract JSON: {e}")

    def _handle_exception(self, exc: Exception) -> LLMError:
        """
        Map exception to appropriate LLM error type.

        Args:
            exc: Original exception

        Returns:
            Typed LLMError
        """
        # Pass through already-typed LLM errors
        if isinstance(exc, LLMError):
            return exc

        error_msg = str(exc).lower()

        # Authentication errors
        if any(keyword in error_msg for keyword in [
            "api_key", "apikey", "api key", "unauthorized", "401",
            "authentication", "invalid key", "access denied"
        ]):
            return LLMAuthenticationError(f"Authentication failed: {exc}")

        # Timeout errors
        if any(keyword in error_msg for keyword in [
            "timeout", "timed out", "read timeout", "connection timeout", "deadline exceeded"
        ]):
            return LLMTimeoutError(f"Request timed out: {exc}")

        # JSON parse errors (if we can detect them)
        if any(keyword in error_msg for keyword in [
            "json", "parse", "decode", "invalid json", "malformed"
        ]):
            return LLMParseError(f"Failed to parse response: {exc}")

        # Generic provider error
        return LLMProviderError(f"Provider error: {exc}")

    def _with_retry(self, func, *args, **kwargs):
        """
        Execute function with exponential backoff retry.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func

        Raises:
            LLMError: After max retries exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)

            except LLMError as e:
                last_exception = e
                # Don't retry authentication, timeout, or parse errors
                if isinstance(e, (LLMAuthenticationError, LLMTimeoutError, LLMParseError)):
                    logger.warning(f"Non-retryable error: {e}")
                    raise

                # Log retryable error
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} attempts failed. Last error: {e}")

        # All retries exhausted
        raise last_exception

    async def _async_with_retry(self, func, *args, **kwargs):
        """
        Execute async function with exponential backoff retry.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func

        Raises:
            LLMError: After max retries exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)

            except LLMError as e:
                last_exception = e
                # Don't retry authentication, timeout, or parse errors
                if isinstance(e, (LLMAuthenticationError, LLMTimeoutError, LLMParseError)):
                    logger.warning(f"Non-retryable error: {e}")
                    raise

                # Log retryable error
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} attempts failed. Last error: {e}")

        # All retries exhausted
        raise last_exception

    # Abstract methods that subclasses MUST implement (sync versions)

    @abstractmethod
    def _send_message_sync(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a message and return response.

        Args:
            system_prompt: System prompt
            user_message: User message
            model: Model name
            **kwargs: Additional parameters

        Returns:
            Dict with 'content' and 'usage' keys
        """
        pass

    @abstractmethod
    def _generate_json_sync(
        self,
        system_prompt: str,
        user_message: str,
        response_schema: Any,
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate JSON response using structured output.

        Args:
            system_prompt: System prompt
            user_message: User message
            response_schema: JSON schema for response
            model: Model name
            **kwargs: Additional parameters

        Returns:
            Dict with 'content' (parsed JSON) and 'usage' keys
        """
        pass

    # Async abstract methods that subclasses SHOULD implement

    @abstractmethod
    async def _send_message_async(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Async version of _send_message_sync.

        Args:
            system_prompt: System prompt
            user_message: User message
            model: Model name
            **kwargs: Additional parameters

        Returns:
            Dict with 'content' and 'usage' keys
        """
        pass

    @abstractmethod
    async def _generate_json_async(
        self,
        system_prompt: str,
        user_message: str,
        response_schema: Any,
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Async version of _generate_json_sync.

        Args:
            system_prompt: System prompt
            user_message: User message
            response_schema: JSON schema for response
            model: Model name
            **kwargs: Additional parameters

        Returns:
            Dict with 'content' (parsed JSON) and 'usage' keys
        """
        pass

    # Public sync API methods (with retry logic) - BACKWARD COMPATIBLE

    def send_message(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a message with retry logic.

        Args:
            system_prompt: System prompt
            user_message: User message
            model: Model name
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Dict with 'content' and 'usage' keys
        """
        resolved_model = self._resolve_model(model)
        return self._with_retry(
            self._send_message_sync,
            system_prompt, user_message, resolved_model, **kwargs
        )

    def generate_json(
        self,
        system_prompt: str,
        user_message: str,
        response_schema: Any,
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate structured JSON response with retry logic.

        Args:
            system_prompt: System prompt
            user_message: User message
            response_schema: JSON schema for response
            model: Model name
            **kwargs: Additional parameters

        Returns:
            Dict with 'content' (parsed JSON) and 'usage' keys
        """
        resolved_model = self._resolve_model(model)
        return self._with_retry(
            self._generate_json_sync,
            system_prompt, user_message, response_schema, resolved_model, **kwargs
        )

    def track_usage(self, response: Any) -> LLMUsage:
        """
        Extract token usage and cost from provider response.
        Default implementation for OpenAI-compatible responses.
        Subclasses can override for provider-specific formats.

        Args:
            response: Provider response object

        Returns:
            LLMUsage with token counts and cost
        """
        # Default: OpenAI-compatible response format
        prompt_tokens = getattr(response.usage, 'prompt_tokens', 0)
        completion_tokens = getattr(response.usage, 'completion_tokens', 0)
        total_tokens = getattr(response.usage, 'total_tokens', prompt_tokens + completion_tokens)
        model = getattr(response, 'model', 'unknown')

        cost = self._cost_tracker.calculate_cost(model, prompt_tokens, completion_tokens)

        return LLMUsage(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            provider=self.__class__.__name__.replace('Client', '').lower()
        )

    # Public async API methods (with retry logic) - NEW

    async def asend_message(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Async send a message with retry logic.

        Args:
            system_prompt: System prompt
            user_message: User message
            model: Model name
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Dict with 'content' and 'usage' keys
        """
        resolved_model = self._resolve_model(model)
        return await self._async_with_retry(
            self._send_message_async,
            system_prompt, user_message, resolved_model, **kwargs
        )

    async def agenerate_json(
        self,
        system_prompt: str,
        user_message: str,
        response_schema: Any,
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Async generate structured JSON response with retry logic.

        Args:
            system_prompt: System prompt
            user_message: User message
            response_schema: JSON schema for response
            model: Model name
            **kwargs: Additional parameters

        Returns:
            Dict with 'content' (parsed JSON) and 'usage' keys
        """
        resolved_model = self._resolve_model(model)
        return await self._async_with_retry(
            self._generate_json_async,
            system_prompt, user_message, response_schema, resolved_model, **kwargs
        )