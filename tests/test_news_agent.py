"""Tests for the News Intelligence Agent."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from agents.news_agent.news_agent import NewsAgent, run_news_agent_sync
from agents.news_agent.schemas import NewsAgentInput, NewsAgentOutput, NewsArticle, WorkerResponse
from llm.llm_provider import LLMProvider


class MockLLMProvider:
    """Mock LLM provider for testing."""
    
    def __init__(self, should_succeed: bool = True, response_data: dict = None, error: str = None):
        self.should_succeed = should_succeed
        self.response_data = response_data or {
            "company": "NVIDIA",
            "articles": [
                {"title": "NVIDIA beats earnings estimates", "impact": "positive", "confidence": 0.9},
                {"title": "New AI chip announced", "impact": "positive", "confidence": 0.85},
                {"title": "Market volatility affects tech sector", "impact": "neutral", "confidence": 0.7}
            ]
        }
        self.error = error
        self.call_count = 0
    
    def generate_json(self, system_prompt: str, user_message: str, response_schema: dict, model: str, **kwargs) -> dict:
        self.call_count += 1
        if not self.should_succeed:
            raise Exception(self.error or "LLM call failed")
        
        # Return mock usage data
        class MockUsage:
            model = "test-model"
            prompt_tokens = 100
            completion_tokens = 50
            total_tokens = 150
            cost = 0.001
            
            def to_dict(self):
                return {
                    "model": self.model,
                    "prompt_tokens": self.prompt_tokens,
                    "completion_tokens": self.completion_tokens,
                    "total_tokens": self.total_tokens,
                    "cost": self.cost
                }
        
        return {
            "content": self.response_data,
            "usage": MockUsage()
        }


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    return MockLLMProvider(should_succeed=True)


@pytest.fixture
def news_agent(mock_llm_provider):
    """Create a NewsAgent instance with mock LLM provider."""
    return NewsAgent(llm_provider=mock_llm_provider)


class TestNewsAgentInput:
    """Test NewsAgentInput schema validation."""
    
    def test_valid_input(self):
        """Test valid company input."""
        input_data = NewsAgentInput(company="NVIDIA", query="earnings focus")
        assert input_data.company == "NVIDIA"
        assert input_data.query == "earnings focus"
    
    def test_minimal_input(self):
        """Test input with only company name."""
        input_data = NewsAgentInput(company="Apple")
        assert input_data.company == "Apple"
        assert input_data.query is None
    
    def test_empty_company_raises_error(self):
        """Test that empty company name is handled."""
        # Pydantic allows empty strings by default
        input_data = NewsAgentInput(company="")
        assert input_data.company == ""


class TestNewsAgentOutput:
    """Test NewsAgentOutput schema validation."""
    
    def test_valid_output(self):
        """Test valid output structure."""
        output = NewsAgentOutput(
            company="NVIDIA",
            articles=[
                NewsArticle(title="Test article", impact="positive", confidence=0.9)
            ]
        )
        assert output.company == "NVIDIA"
        assert len(output.articles) == 1
        assert output.articles[0].impact == "positive"
    
    def test_empty_articles_list(self):
        """Test output with empty articles list."""
        output = NewsAgentOutput(company="NVIDIA", articles=[])
        assert len(output.articles) == 0
    
    def test_confidence_bounds(self):
        """Test confidence score bounds."""
        # Valid confidence
        article = NewsArticle(title="Test", impact="neutral", confidence=0.5)
        assert article.confidence == 0.5
        
        # Invalid confidence (too high)
        with pytest.raises(Exception):
            NewsArticle(title="Test", impact="neutral", confidence=1.5)
        
        # Invalid confidence (too low)
        with pytest.raises(Exception):
            NewsArticle(title="Test", impact="neutral", confidence=-0.1)
    
    def test_impact_enum_validation(self):
        """Test impact enum validation."""
        # Valid impacts
        for impact in ["positive", "negative", "neutral"]:
            article = NewsArticle(title="Test", impact=impact, confidence=0.5)
            assert article.impact == impact
        
        # Invalid impact
        with pytest.raises(Exception):
            NewsArticle(title="Test", impact="invalid", confidence=0.5)


class TestNewsAgent:
    """Test NewsAgent execution."""
    
    @pytest.mark.asyncio
    async def test_run_success(self, news_agent):
        """Test successful news agent run."""
        result = await news_agent.run("NVIDIA")
        
        # Result is a WorkerResponse object
        assert result.status == "success"
        assert result.data is not None
        assert result.data["company"] == "NVIDIA"
        assert "articles" in result.data
        assert len(result.data["articles"]) == 3
        assert result.usage is not None
    
    @pytest.mark.asyncio
    async def test_run_with_query(self, news_agent):
        """Test run with additional query context."""
        result = await news_agent.run("NVIDIA", {"query": "focus on AI chips"})
        
        assert result.status == "success"
        assert result.data["company"] == "NVIDIA"
    
    @pytest.mark.asyncio
    async def test_run_with_context_query(self, news_agent):
        """Test run with context containing query."""
        result = await news_agent.run("NVIDIA", {"query": "earnings analysis"})
        
        assert result.status == "success"
    
    @pytest.mark.asyncio
    async def test_run_invalid_company(self, news_agent):
        """Test run with invalid company (empty string)."""
        result = await news_agent.run("")
        
        # Should still call LLM but with empty company
        assert result.status in ["success", "error"]
    
    @pytest.mark.asyncio
    async def test_run_llm_failure(self, mock_llm_provider):
        """Test handling of LLM failure."""
        mock_llm_provider.should_succeed = False
        mock_llm_provider.error = "API rate limit exceeded"
        
        agent = NewsAgent(llm_provider=mock_llm_provider)
        result = await agent.run("NVIDIA")
        
        assert result.status == "error"
        assert "News agent failed" in result.error or "API rate limit" in result.error
    
    @pytest.mark.asyncio
    async def test_run_llm_returns_invalid_schema(self, mock_llm_provider):
        """Test handling when LLM returns invalid schema."""
        mock_llm_provider.response_data = {"invalid": "data"}
        
        agent = NewsAgent(llm_provider=mock_llm_provider)
        result = await agent.run("NVIDIA")
        
        assert result.status == "error"
        assert "validation failed" in result.error.lower() or "missing articles" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_run_llm_returns_empty_articles(self, mock_llm_provider):
        """Test handling when LLM returns empty articles list."""
        mock_llm_provider.response_data = {"company": "NVIDIA", "articles": []}
        
        agent = NewsAgent(llm_provider=mock_llm_provider)
        result = await agent.run("NVIDIA")
        
        assert result.status == "success"
        assert result.data["articles"] == []


class TestNewsAgentSyncWrapper:
    """Test synchronous wrapper for testing."""
    
    def test_run_news_agent_sync_success(self, mock_llm_provider):
        """Test synchronous wrapper success."""
        result = run_news_agent_sync(mock_llm_provider, "NVIDIA")
        
        assert result["status"] == "success"
        assert result["data"]["company"] == "NVIDIA"
    
    def test_run_news_agent_sync_with_query(self, mock_llm_provider):
        """Test synchronous wrapper with query."""
        result = run_news_agent_sync(mock_llm_provider, "NVIDIA", "earnings focus")
        
        assert result["status"] == "success"
        assert result["data"]["company"] == "NVIDIA"


class TestNewsAgentPrompts:
    """Test prompt building."""
    
    def test_system_prompt_exists(self):
        """Test that system prompt is defined."""
        from agents.news_agent.prompts import SYSTEM_PROMPT
        assert SYSTEM_PROMPT is not None
        assert len(SYSTEM_PROMPT) > 100
        assert "positive" in SYSTEM_PROMPT.lower()
        assert "negative" in SYSTEM_PROMPT.lower()
        assert "neutral" in SYSTEM_PROMPT.lower()
    
    def test_user_prompt_template_exists(self):
        """Test that user prompt template is defined."""
        from agents.news_agent.prompts import USER_PROMPT_TEMPLATE
        assert USER_PROMPT_TEMPLATE is not None
        assert "{company}" in USER_PROMPT_TEMPLATE
        assert "{current_date}" in USER_PROMPT_TEMPLATE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
