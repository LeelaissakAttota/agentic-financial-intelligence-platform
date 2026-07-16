"""
Unit tests for async LLM client support.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio

from llm.llm_provider import LLMProvider
from llm.base_client import BaseLLMClient
from llm.exceptions import (
    LLMProviderError,
    LLMAuthenticationError,
    LLMTimeoutError,
    LLMParseError,
)


class ConcreteAsyncTestClient(BaseLLMClient):
    """Concrete implementation for testing async base class."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._send_message_calls = []
        self._generate_json_calls = []
        self.async_send_message_calls = []
        self.async_generate_json_calls = []
        self.should_fail = False
        self.fail_exception = None
        self.return_value = {"content": "test", "usage": None}
    
    # Sync implementations (required by abstract base)
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
    
    # Async implementations
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


class TestLLMProviderAsyncInterface:
    """Tests for LLMProvider async interface."""

    def test_llm_provider_has_async_methods(self):
        """LLMProvider should have async abstract methods."""
        assert hasattr(LLMProvider, 'asend_message')
        assert hasattr(LLMProvider, 'agenerate_json')
        # Should still have sync methods
        assert hasattr(LLMProvider, 'send_message')
        assert hasattr(LLMProvider, 'generate_json')

    def test_cannot_instantiate_without_async_impl(self):
        """Should not be able to instantiate without async implementations."""
        class IncompleteClient(LLMProvider):
            def send_message(self, *args, **kwargs):
                pass
            def generate_json(self, *args, **kwargs):
                pass
            def track_usage(self, *args, **kwargs):
                pass
            # Missing async methods
        
        with pytest.raises(TypeError, match="abstract methods"):
            IncompleteClient()


class TestBaseLLMClientAsync:
    """Tests for BaseLLMClient async functionality."""

    @pytest.fixture
    def client(self):
        return ConcreteAsyncTestClient(max_retries=2, base_delay=0.01)

    @pytest.mark.asyncio
    async def test_asend_message_calls_async_impl(self, client):
        """asend_message should delegate to _send_message_async."""
        result = await client.asend_message("sys", "user", "model", temperature=0.5)
        
        assert len(client.async_send_message_calls) == 1
        call = client.async_send_message_calls[0]
        assert call[0] == "sys"
        assert call[1] == "user"
        assert call[2] == "model"
        assert call[3] == {"temperature": 0.5}
        assert result == {"content": "test", "usage": None}

    @pytest.mark.asyncio
    async def test_agenerate_json_calls_async_impl(self, client):
        """agenerate_json should delegate to _generate_json_async."""
        schema = {"type": "object"}
        result = await client.agenerate_json("sys", "user", schema, "model", temperature=0.1)
        
        assert len(client.async_generate_json_calls) == 1
        call = client.async_generate_json_calls[0]
        assert call[0] == "sys"
        assert call[1] == "user"
        assert call[2] == schema
        assert call[3] == "model"
        assert result == {"content": {"key": "value"}, "usage": None}

    @pytest.mark.asyncio
    async def test_async_retry_on_transient_failure(self, client):
        """Async methods should retry on transient failures."""
        client.should_fail = True
        client.fail_exception = LLMProviderError("Transient error")
        
        call_count = [0]
        
        async def counting_async(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise LLMProviderError("Transient error")
            # Second call should succeed - return directly without calling original
            return {"content": "test", "usage": None}
        
        client._send_message_async = counting_async
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await client.asend_message("sys", "user", "model")
        
        assert result == {"content": "test", "usage": None}
        assert call_count[0] == 2
        assert mock_sleep.call_count == 1

    @pytest.mark.asyncio
    async def test_async_retry_exhausted_raises(self, client):
        """After max retries, should raise the last exception."""
        client.should_fail = True
        client.fail_exception = LLMProviderError("Persistent error")
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(LLMProviderError, match="Persistent error"):
                await client.asend_message("sys", "user", "model")

    @pytest.mark.asyncio
    async def test_no_async_retry_on_auth_error(self, client):
        """Authentication errors should not be retried in async."""
        client.should_fail = True
        client.fail_exception = LLMAuthenticationError("Invalid key")
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(LLMAuthenticationError):
                await client.asend_message("sys", "user", "model")
            mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_async_retry_on_timeout_error(self, client):
        """Timeout errors should not be retried in async."""
        client.should_fail = True
        client.fail_exception = LLMTimeoutError("Timed out")
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(LLMTimeoutError):
                await client.asend_message("sys", "user", "model")
            mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_async_retry_on_parse_error(self, client):
        """Parse errors should not be retried in async."""
        client.should_fail = True
        client.fail_exception = LLMParseError("Bad JSON")
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(LLMParseError):
                await client.agenerate_json("sys", "user", {}, "model")
            mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_exponential_backoff_timing(self, client):
        """Async retry delays should follow exponential backoff."""
        client.max_retries = 3
        client.base_delay = 1.0
        client.should_fail = True
        client.fail_exception = LLMProviderError("Error")
        
        sleep_times = []
        async def capture_sleep(t):
            sleep_times.append(t)
        
        with patch('asyncio.sleep', side_effect=capture_sleep):
            with pytest.raises(LLMProviderError):
                await client.asend_message("sys", "user", "model")
        
        # Delays: 1.0, 2.0 (base_delay * 2^attempt)
        assert sleep_times == [1.0, 2.0]

    @pytest.mark.asyncio
    async def test_model_resolution_in_async(self, client):
        """Async methods should use _resolve_model."""
        client._resolve_model = lambda m: f"resolved-{m}"
        
        await client.asend_message("sys", "user", "test-model")
        
        call = client.async_send_message_calls[0]
        assert call[2] == "resolved-test-model"

    @pytest.mark.asyncio
    async def test_sync_and_async_independent(self, client):
        """Sync and async methods should work independently."""
        # Call sync
        client.send_message("sys", "user", "model")
        
        # Call async
        await client.asend_message("sys", "user", "model")
        
        assert len(client._send_message_calls) == 1
        assert len(client.async_send_message_calls) == 1


class TestClaudeClientAsync:
    """Tests for ClaudeClient async methods."""

    @pytest.mark.asyncio
    async def test_claude_client_has_async_methods(self):
        """ClaudeClient should have async public methods."""
        from llm.claude_client import ClaudeClient
        
        # Check methods exist (even if not fully implemented yet)
        assert hasattr(ClaudeClient, 'asend_message')
        assert hasattr(ClaudeClient, 'agenerate_json')

    @pytest.mark.asyncio
    async def test_claude_client_async_openrouter_mode(self):
        """Test async with OpenRouter mode."""
        # This test requires the async implementation
        pass

    @pytest.mark.asyncio
    async def test_claude_client_async_direct_mode(self):
        """Test async with direct Anthropic mode."""
        # This test requires the async implementation
        pass


class TestOpenRouterClientAsync:
    """Tests for OpenRouterClient async methods."""

    @pytest.mark.asyncio
    async def test_openrouter_client_has_async_methods(self):
        """OpenRouterClient should have async public methods."""
        from llm.openrouter_client import OpenRouterClient
        
        assert hasattr(OpenRouterClient, 'asend_message')
        assert hasattr(OpenRouterClient, 'agenerate_json')


# Helper to run async tests without pytest-asyncio if needed
if __name__ == "__main__":
    import asyncio
    pytest.main([__file__, "-v"])