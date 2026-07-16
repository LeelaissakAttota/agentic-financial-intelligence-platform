"""
Claude client implementation for the Financial Research Agent.
Supports both direct Anthropic API and OpenRouter (which serves Anthropic models).
Now inherits from BaseLLMClient for shared retry, error handling, and JSON extraction.
"""
import json
import logging
import os
import time
from typing import Any, Dict, Optional

from .base_client import BaseLLMClient
from .token_tracker import LLMUsage
from .cost_tracker import CostTracker
from .exceptions import LLMProviderError, LLMParseError, LLMAuthenticationError, LLMTimeoutError

logger = logging.getLogger(__name__)

# Default models for different tiers
CLAUDE_SYNTHESIS_MODEL = "claude-3-5-sonnet-20241022"
CLAUDE_LIGHT_MODEL = "claude-3-haiku-20240307"

# OpenRouter model mappings
OPENROUTER_CLAUDE_SYNTHESIS = "anthropic/claude-sonnet-5"
OPENROUTER_CLAUDE_LIGHT = "anthropic/claude-3-haiku"


class ClaudeClient(BaseLLMClient):
    """Anthropic Claude API client with retry handling and structured output support.

    Automatically detects if using OpenRouter (base_url contains 'openrouter.ai')
    and uses OpenAI-compatible SDK for better compatibility.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 60.0,
    ):
        # Support both direct Anthropic API and OpenRouter (which serves Anthropic models)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        self.base_url = base_url or os.getenv("OPENROUTER_BASE_URL") or os.getenv("ANTHROPIC_BASE_URL")
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

        # Detect if using OpenRouter
        self._is_openrouter = "openrouter.ai" in (self.base_url or "")

        # Initialize appropriate clients
        if self._is_openrouter:
            from openai import OpenAI, AsyncOpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
            self._async_client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
            # Use OpenRouter model names
            self._synthesis_model = OPENROUTER_CLAUDE_SYNTHESIS
            self._light_model = OPENROUTER_CLAUDE_LIGHT
        else:
            import anthropic
            self._client = anthropic.Anthropic(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
            self._async_client = anthropic.AsyncAnthropic(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
            # Use direct Anthropic model names
            self._synthesis_model = CLAUDE_SYNTHESIS_MODEL
            self._light_model = CLAUDE_LIGHT_MODEL

        # Initialize base class (sets up cost tracker)
        super().__init__(max_retries=max_retries, base_delay=retry_delay, timeout=timeout)

    def _resolve_model(self, model: Optional[str]) -> str:
        """Resolve model name, handling 'synthesis' and 'light' aliases."""
        if model is None:
            return self._synthesis_model
        elif model == "synthesis":
            return self._synthesis_model
        elif model == "light":
            return self._light_model
        return model

    # ==================== SYNC IMPLEMENTATIONS ====================

    def _send_message_sync(
        self,
        system_prompt: str,
        user_message: str,
        model: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Send a basic text message and return response with usage tracking."""
        model = self._resolve_model(model)
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                if self._is_openrouter:
                    # Use OpenAI-compatible API for OpenRouter
                    response = self._client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message},
                        ],
                        max_tokens=kwargs.get("max_tokens", 4096),
                        temperature=kwargs.get("temperature", 0.1),
                    )

                    usage = self._track_usage_openrouter(response)
                    return {
                        "content": response.choices[0].message.content if response.choices else "",
                        "usage": usage,
                        "model": response.model,
                    }
                else:
                    # Use Anthropic SDK for direct API
                    import anthropic
                    response = self._client.messages.create(
                        model=model,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_message}],
                        max_tokens=kwargs.get("max_tokens", 4096),
                        temperature=kwargs.get("temperature", 0.1),
                    )

                    usage = self.track_usage(response)
                    return {
                        "content": response.content[0].text if response.content else "",
                        "usage": usage,
                        "model": response.model,
                    }

            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))

        # All retries exhausted
        raise LLMProviderError(f"Claude error after {self.max_retries} retries: {last_exception}")

    async def _send_message_async(
        self,
        system_prompt: str,
        user_message: str,
        model: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Send a basic text message and return response with usage tracking (async)."""
        model = self._resolve_model(model)
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                if self._is_openrouter:
                    # Use OpenAI-compatible async API for OpenRouter
                    response = await self._async_client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message},
                        ],
                        max_tokens=kwargs.get("max_tokens", 4096),
                        temperature=kwargs.get("temperature", 0.1),
                    )

                    usage = self._track_usage_openrouter(response)
                    return {
                        "content": response.choices[0].message.content if response.choices else "",
                        "usage": usage,
                        "model": response.model,
                    }
                else:
                    # Use Anthropic async SDK for direct API
                    import anthropic
                    response = await self._async_client.messages.create(
                        model=model,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_message}],
                        max_tokens=kwargs.get("max_tokens", 4096),
                        temperature=kwargs.get("temperature", 0.1),
                    )

                    usage = self.track_usage(response)
                    return {
                        "content": response.content[0].text if response.content else "",
                        "usage": usage,
                        "model": response.model,
                    }

            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))

        # All retries exhausted
        raise LLMProviderError(f"Claude error after {self.max_retries} retries: {last_exception}")

    def _generate_json_sync(
        self,
        system_prompt: str,
        user_message: str,
        response_schema: Any,
        model: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Send a message requesting structured JSON output."""
        model = self._resolve_model(model)

        # Build enhanced system prompt with JSON schema instructions
        schema_str = json.dumps(response_schema, indent=2) if isinstance(response_schema, dict) else str(response_schema)
        enhanced_system_prompt = (
            f"{system_prompt}\n\n"
            f"IMPORTANT: Return ONLY valid JSON matching this schema:\n{schema_str}\n"
            f"Do not include any explanatory text, markdown, or code fences."
        )

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                if self._is_openrouter:
                    # OpenRouter supports response_format=json_object
                    response = self._client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": enhanced_system_prompt},
                            {"role": "user", "content": user_message},
                        ],
                        response_format={"type": "json_object"},
                        max_tokens=kwargs.get("max_tokens", 4096),
                        temperature=kwargs.get("temperature", 0.1),
                    )

                    content = response.choices[0].message.content if response.choices else ""

                    # Parse JSON response using base class extractor
                    try:
                        parsed_json = self._extract_json(content)
                    except Exception as e:
                        raise LLMParseError(f"Failed to parse JSON response: {str(e)}")

                    usage = self._track_usage_openrouter(response)
                    return {
                        "content": parsed_json,
                        "usage": usage,
                        "model": response.model,
                    }
                else:
                    # Direct Anthropic API - no native JSON mode, use prompt engineering
                    import anthropic
                    response = self._client.messages.create(
                        model=model,
                        system=enhanced_system_prompt,
                        messages=[{"role": "user", "content": user_message}],
                        max_tokens=kwargs.get("max_tokens", 4096),
                        temperature=kwargs.get("temperature", 0.1),
                    )

                    content = response.content[0].text if response.content else ""

                    # Parse JSON response using base class extractor
                    try:
                        parsed_json = self._extract_json(content)
                    except Exception as e:
                        # Try to extract from markdown fences
                        if "```json" in content:
                            start = content.find("```json") + 7
                            end = content.find("```", start)
                            if end > start:
                                json_str = content[start:end].strip()
                                try:
                                    parsed_json = json.loads(json_str)
                                except json.JSONDecodeError:
                                    raise LLMParseError(f"Failed to parse JSON from markdown: {str(e)}")
                            else:
                                raise LLMParseError(f"Failed to parse JSON response: {str(e)}")
                        else:
                            raise LLMParseError(f"Failed to parse JSON response: {str(e)}")

                    usage = self.track_usage(response)
                    return {
                        "content": parsed_json,
                        "usage": usage,
                        "model": response.model,
                    }

            except LLMParseError:
                # Don't retry parse errors
                raise
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))

        raise LLMProviderError(f"Claude error after {self.max_retries} retries: {last_exception}")

    async def _generate_json_async(
        self,
        system_prompt: str,
        user_message: str,
        response_schema: Any,
        model: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Send a message requesting structured JSON output (async)."""
        model = self._resolve_model(model)

        # Build enhanced system prompt with JSON schema instructions
        schema_str = json.dumps(response_schema, indent=2) if isinstance(response_schema, dict) else str(response_schema)
        enhanced_system_prompt = (
            f"{system_prompt}\n\n"
            f"IMPORTANT: Return ONLY valid JSON matching this schema:\n{schema_str}\n"
            f"Do not include any explanatory text, markdown, or code fences."
        )

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                if self._is_openrouter:
                    # OpenRouter supports response_format=json_object
                    response = await self._async_client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": enhanced_system_prompt},
                            {"role": "user", "content": user_message},
                        ],
                        response_format={"type": "json_object"},
                        max_tokens=kwargs.get("max_tokens", 4096),
                        temperature=kwargs.get("temperature", 0.1),
                    )

                    content = response.choices[0].message.content if response.choices else ""

                    # Parse JSON response using base class extractor
                    try:
                        parsed_json = self._extract_json(content)
                    except Exception as e:
                        raise LLMParseError(f"Failed to parse JSON response: {str(e)}")

                    usage = self._track_usage_openrouter(response)
                    return {
                        "content": parsed_json,
                        "usage": usage,
                        "model": response.model,
                    }
                else:
                    # Direct Anthropic API - no native JSON mode, use prompt engineering
                    import anthropic
                    response = await self._async_client.messages.create(
                        model=model,
                        system=enhanced_system_prompt,
                        messages=[{"role": "user", "content": user_message}],
                        max_tokens=kwargs.get("max_tokens", 4096),
                        temperature=kwargs.get("temperature", 0.1),
                    )

                    content = response.content[0].text if response.content else ""

                    # Parse JSON response using base class extractor
                    try:
                        parsed_json = self._extract_json(content)
                    except Exception as e:
                        # Try to extract from markdown fences
                        if "```json" in content:
                            start = content.find("```json") + 7
                            end = content.find("```", start)
                            if end > start:
                                json_str = content[start:end].strip()
                                try:
                                    parsed_json = json.loads(json_str)
                                except json.JSONDecodeError:
                                    raise LLMParseError(f"Failed to parse JSON from markdown: {str(e)}")
                            else:
                                raise LLMParseError(f"Failed to parse JSON response: {str(e)}")
                        else:
                            raise LLMParseError(f"Failed to parse JSON response: {str(e)}")

                    usage = self.track_usage(response)
                    return {
                        "content": parsed_json,
                        "usage": usage,
                        "model": response.model,
                    }

            except LLMParseError:
                # Don't retry parse errors
                raise
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))

        raise LLMProviderError(f"Claude error after {self.max_retries} retries: {last_exception}")

    def _track_usage_openrouter(self, response: Any) -> LLMUsage:
        """Extract token usage and cost from OpenRouter/OpenAI-compatible response."""
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

    def track_usage(self, response: Any) -> LLMUsage:
        """Extract token usage and cost from Anthropic response."""
        # Anthropic response has usage with input_tokens and output_tokens
        prompt_tokens = response.usage.input_tokens
        completion_tokens = response.usage.output_tokens
        model = response.model

        # Use CostTracker with Anthropic model naming
        cost = CostTracker.calculate_cost(model, prompt_tokens, completion_tokens)

        return LLMUsage(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=cost,
            provider="anthropic",
        )

    def _handle_exception(self, e: Exception):
        """Map exceptions to our custom hierarchy."""
        err_msg = str(e).lower()
        if "api_key" in err_msg or "unauthorized" in err_msg or "401" in err_msg:
            raise LLMAuthenticationError(f"Claude Authentication failed: {str(e)}")
        if "timeout" in err_msg:
            raise LLMTimeoutError(f"Claude request timed out: {str(e)}")
        raise LLMProviderError(f"Claude API error: {str(e)}")

    # Backward compatibility method
    def generate(
        self,
        system_prompt: str,
        user_payload: Any,
        model: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Compatibility method for test_claude_connection.py.

        Accepts system_prompt and user_payload (dict or str), sends message,
        returns parsed JSON content.
        """
        # Convert user_payload to string if it's a dict
        if isinstance(user_payload, dict):
            import json
            user_message = json.dumps(user_payload)
        else:
            user_message = str(user_payload)

        response = self.send_message(system_prompt, user_message, model=model, **kwargs)
        content = response["content"]

        # Parse JSON from content (may be in markdown fences)
        import json
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try extracting from markdown fences
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end > start:
                    json_str = content[start:end].strip()
                    return json.loads(json_str)
            raise LLMParseError(f"Failed to parse JSON from response: {content[:200]}")


# Backward compatibility alias
Claude = ClaudeClient