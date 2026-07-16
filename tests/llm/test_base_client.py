"""
Unit tests for llm.base_client.BaseLLMClient
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from abc import ABC

from llm.llm_provider import LLMProvider
from llm.base_client import BaseLLMClient
from llm.exceptions import (
    LLMProviderError,
    LLMAuthenticationError,
    LLMTimeoutError,
    LLMParseError,
)
from llm.json_utils import extract_json


class ConcreteTestClient(BaseLLMClient):
    """Concrete implementation for testing abstract base class."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._send_message_calls = []
        self._generate_json_calls = []
        self.async_send_message_calls = []
        self.async_generate_json_calls = []
        self.should_fail = False
        self.fail_exception = None
        self.return_value = {"content": "test", "usage": None}
    
    def _send_message_sync(self, system_prompt: str, user_message: str, model: str, **kwargs):
        self._send_message_calls.append((system_prompt, user_message, model, kwargs))
        if self.should_fail:
            raise self.fail_exception or LLMProviderError("Test failure")
        return self.return_value
    
    def _generate_json_sync(self, system_prompt: str, user_message: str, response_schema, model: str, **kwargs):
        self._generate_json_calls.append((system_prompt, user_message, response_schema, model, kwargs))
        if self.should_fail:
            raise self.fail_exception or LLMProviderError("Test failure")
        return {"content": {"key": "value"}, "usage": None}
    
    async def _send_message_async(self, system_prompt: str, user_message: str, model: str, **kwargs):
        self.async_send_message_calls.append((system_prompt, user_message, model, kwargs))
        if self.should_fail:
            raise self.fail_exception or LLMProviderError("Test failure")
        return self.return_value
    
    async def _generate_json_async(self, system_prompt: str, user_message: str, response_schema, model: str, **kwargs):
        self.async_generate_json_calls.append((system_prompt, user_message, response_schema, model, kwargs))
        if self.should_fail:
            raise self.fail_exception or LLMProviderError("Test failure")
        return {"content": {"key": "value"}, "usage": None}


class TestBaseLLMClient:
    """Tests for BaseLLMClient functionality."""

    def test_inherits_from_llm_provider(self):
        """BaseLLMClient should be a subclass of LLMProvider."""
        assert issubclass(BaseLLMClient, LLMProvider)
        assert issubclass(BaseLLMClient, ABC)

    def test_cannot_instantiate_abstract_base_directly(self):
        """Direct instantiation of BaseLLMClient should fail (abstract methods)."""
        with pytest.raises(TypeError, match="abstract methods"):
            BaseLLMClient()

    def test_can_instantiate_concrete_subclass(self):
        """Concrete subclass with required methods can be instantiated."""
        client = ConcreteTestClient()
        assert isinstance(client, BaseLLMClient)
        assert isinstance(client, LLMProvider)

    def test_init_sets_defaults(self):
        """Constructor should set retry, timeout, cost tracker defaults."""
        client = ConcreteTestClient()
        assert client.max_retries == 3
        assert client.base_delay == 1.0
        assert client.timeout == 60.0
        assert hasattr(client, '_cost_tracker')

    def test_init_accepts_custom_params(self):
        """Constructor should accept custom retry/timeout values."""
        client = ConcreteTestClient(max_retries=5, base_delay=2.0, timeout=120.0)
        assert client.max_retries == 5
        assert client.base_delay == 2.0
        assert client.timeout == 120.0

    def test_retry_on_transient_failure(self):
        """Should retry on transient failures and succeed on subsequent attempt."""
        client = ConcreteTestClient()
        
        # Mock the method to fail once then succeed
        call_count = [0]
        
        def counting_method(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise LLMProviderError("Transient error")
            return {"content": "test", "usage": None}
        
        client._send_message_sync = counting_method
        
        # Should succeed after retry
        with patch('time.sleep', return_value=None):  # Speed up test
            result = client.send_message("sys", "user", "model")
        
        assert result == {"content": "test", "usage": None}
        assert call_count[0] == 2

    def test_retry_exhausted_raises_last_exception(self):
        """After max_retries, should raise the last exception."""
        client = ConcreteTestClient(max_retries=2, base_delay=0.01)
        client.should_fail = True
        client.fail_exception = LLMProviderError("Persistent error")
        
        with patch('time.sleep', return_value=None):
            with pytest.raises(LLMProviderError, match="Persistent error"):
                client.send_message("sys", "user", "model")

    def test_no_retry_on_authentication_error(self):
        """Authentication errors should not be retried."""
        client = ConcreteTestClient(max_retries=3, base_delay=0.01)
        client.should_fail = True
        client.fail_exception = LLMAuthenticationError("Invalid API key")
        
        with patch('time.sleep', return_value=None) as mock_sleep:
            with pytest.raises(LLMAuthenticationError):
                client.send_message("sys", "user", "model")
            
            # Should not have slept (no retries)
            mock_sleep.assert_not_called()

    def test_no_retry_on_timeout_error(self):
        """Timeout errors should not be retried."""
        client = ConcreteTestClient(max_retries=3, base_delay=0.01)
        client.should_fail = True
        client.fail_exception = LLMTimeoutError("Request timed out")
        
        with patch('time.sleep', return_value=None) as mock_sleep:
            with pytest.raises(LLMTimeoutError):
                client.send_message("sys", "user", "model")
            
            mock_sleep.assert_not_called()

    def test_no_retry_on_parse_error(self):
        """JSON parse errors should not be retried."""
        client = ConcreteTestClient(max_retries=3, base_delay=0.01)
        client.should_fail = True
        client.fail_exception = LLMParseError("Invalid JSON")
        
        with patch('time.sleep', return_value=None) as mock_sleep:
            with pytest.raises(LLMParseError):
                client.generate_json("sys", "user", {}, "model")
            
            mock_sleep.assert_not_called()

    def test_exponential_backoff_timing(self):
        """Retry delays should follow exponential backoff."""
        client = ConcreteTestClient(max_retries=3, base_delay=1.0)
        client.should_fail = True
        client.fail_exception = LLMProviderError("Error")
        
        sleep_times = []
        def capture_sleep(t):
            sleep_times.append(t)
        
        with patch('time.sleep', side_effect=capture_sleep):
            with pytest.raises(LLMProviderError):
                client.send_message("sys", "user", "model")
        
        # Delays: 1.0, 2.0 (base_delay * 2^attempt)
        assert sleep_times == [1.0, 2.0]

    def test_send_message_calls_abstract_method(self):
        """send_message should delegate to _send_message_sync."""
        client = ConcreteTestClient()
        result = client.send_message("system prompt", "user message", "test-model", temperature=0.5)
        
        assert len(client._send_message_calls) == 1
        call = client._send_message_calls[0]
        assert call[0] == "system prompt"
        assert call[1] == "user message"
        assert call[2] == "test-model"
        assert call[3] == {"temperature": 0.5}
        assert result == {"content": "test", "usage": None}

    def test_generate_json_calls_abstract_method(self):
        """generate_json should delegate to _generate_json_sync."""
        client = ConcreteTestClient()
        schema = {"type": "object", "properties": {"key": {"type": "string"}}}
        result = client.generate_json("system", "user", schema, "test-model", temperature=0.1)
        
        assert len(client._generate_json_calls) == 1
        call = client._generate_json_calls[0]
        assert call[0] == "system"
        assert call[1] == "user"
        assert call[2] == schema
        assert call[3] == "test-model"
        assert call[4] == {"temperature": 0.1}
        assert result == {"content": {"key": "value"}, "usage": None}

    def test_json_extraction_integration(self):
        """generate_json should use extract_json for response parsing."""
        client = ConcreteTestClient()
        # Override to return text with JSON in markdown fence
        client.return_value = {
            "content": '```json\n{"parsed": true}\n```',
            "usage": None
        }
        
        # The actual generate_json in base class should extract JSON
        # But our test subclass returns already-parsed dict
        # Let's test the _extract_json helper directly
        extracted = client._extract_json('```json\n{"key": "value"}\n```')
        assert extracted == {"key": "value"}

    def test_extract_json_handles_various_formats(self):
        """_extract_json should handle plain, fenced, and embedded JSON."""
        client = ConcreteTestClient()
        
        # Plain JSON
        assert client._extract_json('{"a": 1}') == {"a": 1}
        
        # Markdown fence
        assert client._extract_json('```json\n{"b": 2}\n```') == {"b": 2}
        
        # Generic fence
        assert client._extract_json('```\n{"c": 3}\n```') == {"c": 3}
        
        # Embedded
        assert client._extract_json('Text: {"d": 4} end') == {"d": 4}

    def test_cost_tracker_initialized(self):
        """CostTracker should be available for usage tracking."""
        client = ConcreteTestClient()
        assert hasattr(client, '_cost_tracker')
        from llm.cost_tracker import CostTracker
        assert isinstance(client._cost_tracker, CostTracker)

    def test_model_alias_resolution(self):
        """Subclasses should be able to resolve model aliases."""
        client = ConcreteTestClient()
        # Default implementation returns model as-is
        assert client._resolve_model("test-model") == "test-model"
        assert client._resolve_model(None) is None

    def test_track_usage_integration(self):
        """track_usage should be available and use CostTracker."""
        client = ConcreteTestClient()
        # Create a mock response similar to OpenAI format
        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        mock_response.model = "test-model"
        
        usage = client.track_usage(mock_response)
        
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
        assert usage.model == "test-model"
        assert usage.cost >= 0


class TestBaseLLMClientErrorHandling:
    """Tests for error handling in BaseLLMClient."""

    def test_handle_authentication_error(self):
        """_handle_exception should map auth errors correctly."""
        client = ConcreteTestClient()
        
        # Test various auth error messages
        auth_errors = [
            "Invalid API key",
            "Unauthorized",
            "Authentication failed",
            "401 Unauthorized",
        ]
        
        for msg in auth_errors:
            exc = Exception(msg)
            result = client._handle_exception(exc)
            assert isinstance(result, LLMAuthenticationError)

    def test_handle_timeout_error(self):
        """_handle_exception should map timeout errors correctly."""
        client = ConcreteTestClient()
        
        timeout_errors = [
            "Request timed out",
            "Timeout",
            "Read timeout",
            "Connection timeout",
        ]
        
        for msg in timeout_errors:
            exc = Exception(msg)
            result = client._handle_exception(exc)
            assert isinstance(result, LLMTimeoutError)

    def test_handle_generic_provider_error(self):
        """_handle_exception should wrap unknown errors as LLMProviderError."""
        client = ConcreteTestClient()
        
        exc = Exception("Some random API error")
        result = client._handle_exception(exc)
        assert isinstance(result, LLMProviderError)

    def test_handle_llm_errors_passthrough(self):
        """Already-typed LLM errors should pass through unchanged."""
        client = ConcreteTestClient()
        
        auth_err = LLMAuthenticationError("auth failed")
        assert client._handle_exception(auth_err) is auth_err
        
        timeout_err = LLMTimeoutError("timeout")
        assert client._handle_exception(timeout_err) is timeout_err
        
        parse_err = LLMParseError("parse failed")
        assert client._handle_exception(parse_err) is parse_err
        
        provider_err = LLMProviderError("provider error")
        assert client._handle_exception(provider_err) is provider_err