"""
OpenRouter implementation of the LLMProvider using OpenAI-compatible API.
Now inherits from BaseLLMClient for shared retry, error handling, and JSON extraction.
"""
import logging
from typing import Any, Dict, Optional

from openai import AsyncOpenAI, OpenAI

from .base_client import BaseLLMClient
from .token_tracker import LLMUsage
from .cost_tracker import CostTracker
from .exceptions import LLMProviderError, LLMParseError, LLMAuthenticationError, LLMTimeoutError

logger = logging.getLogger(__name__)


class OpenRouterClient(BaseLLMClient):
    """OpenRouter client with shared base functionality."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        max_retries: int = 3,
        base_delay: float = 1.0,
        timeout: float = 60.0,
    ):
        super().__init__(max_retries=max_retries, base_delay=base_delay, timeout=timeout)
        # Sync client for backward compatibility
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )
        # Async client for new async API
        self.async_client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )

    def _send_message_sync(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a basic text message via OpenRouter (sync)."""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                **kwargs
            )
            usage = self._track_usage_openrouter(response)
            return {
                "content": response.choices[0].message.content,
                "usage": usage,
                "model": response.model,
            }
        except Exception as e:
            self._handle_exception(e)

    async def _send_message_async(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a basic text message via OpenRouter (async)."""
        try:
            response = await self.async_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                **kwargs
            )
            usage = self._track_usage_openrouter(response)
            return {
                "content": response.choices[0].message.content,
                "usage": usage,
                "model": response.model,
            }
        except Exception as e:
            self._handle_exception(e)

    def _generate_json_sync(
        self,
        system_prompt: str,
        user_message: str,
        response_schema: Any,
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a message requesting structured JSON output via OpenRouter (sync)."""
        # OpenRouter supports response_format=json_object natively
        enhanced_system_prompt = f"{system_prompt}\n\nIMPORTANT: Return ONLY valid JSON. Schema: {response_schema}"

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": enhanced_system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
                **kwargs
            )

            content = response.choices[0].message.content

            # Parse JSON response
            try:
                parsed_json = self._extract_json(content)
            except Exception as e:
                raise LLMParseError(f"Failed to parse OpenRouter JSON response: {str(e)}")

            usage = self._track_usage_openrouter(response)
            return {
                "content": parsed_json,
                "usage": usage,
                "model": response.model,
            }
        except LLMParseError:
            raise
        except Exception as e:
            self._handle_exception(e)

    async def _generate_json_async(
        self,
        system_prompt: str,
        user_message: str,
        response_schema: Any,
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a message requesting structured JSON output via OpenRouter (async)."""
        # OpenRouter supports response_format=json_object natively
        enhanced_system_prompt = f"{system_prompt}\n\nIMPORTANT: Return ONLY valid JSON. Schema: {response_schema}"

        try:
            response = await self.async_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": enhanced_system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
                **kwargs
            )

            content = response.choices[0].message.content

            # Parse JSON response
            try:
                parsed_json = self._extract_json(content)
            except Exception as e:
                raise LLMParseError(f"Failed to parse OpenRouter JSON response: {str(e)}")

            usage = self._track_usage_openrouter(response)
            return {
                "content": parsed_json,
                "usage": usage,
                "model": response.model,
            }
        except LLMParseError:
            raise
        except Exception as e:
            self._handle_exception(e)

    def _track_usage_openrouter(self, response: Any) -> LLMUsage:
        """Extract token usage and cost from OpenRouter response."""
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        model = response.model

        cost = CostTracker.calculate_cost(model, prompt_tokens, completion_tokens)

        return LLMUsage(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=cost,
            provider="openrouter",
        )

    def _handle_exception(self, e: Exception):
        """Map OpenRouter exceptions to our custom exception hierarchy."""
        err_msg = str(e).lower()
        if "api_key" in err_msg or "unauthorized" in err_msg or "401" in err_msg:
            raise LLMAuthenticationError(f"OpenRouter Authentication failed: {str(e)}")
        if "timeout" in err_msg:
            raise LLMTimeoutError(f"OpenRouter request timed out: {str(e)}")
        raise LLMProviderError(f"OpenRouter API error: {str(e)}")

    # Sync track_usage for backward compatibility
    def track_usage(self, response: Any) -> LLMUsage:
        return self._track_usage_openrouter(response)