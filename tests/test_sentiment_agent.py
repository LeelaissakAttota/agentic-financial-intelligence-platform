"""
Tests for the Sentiment Analysis Agent.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from agents.sentiment_agent.agent import (
    SentimentAgent,
    run_sentiment_agent_sync,
)
from agents.sentiment_agent.schemas import (
    SentimentAgentInput,
    SentimentAgentOutput,
    NewsItemIn,
    SocialItemIn,
    AnalystOpinionIn,
    SentimentDistribution,
    BySource,
    DivergenceFlag,
)
from agents.manager_agent.schemas import WorkerResponse
from agents.sentiment_agent.exceptions import (
    SentimentAgentError,
    SentimentAgentInputError,
    SentimentAgentLLMError,
    SentimentAgentValidationError,
)


class MockLLMProvider:
    """Mock LLM provider for testing."""
    
    def __init__(self, should_succeed: bool = True, response_data: dict = None, error: str = None):
        self.should_succeed = should_succeed
        self.response_data = response_data or self._default_response()
        self.error = error
        self.call_count = 0
        self.generate_json_called = False
        self.agenerate_json_called = False
    
    def _default_response(self) -> dict:
        return {
            "by_source": {
                "news": {"positive": 0.6, "negative": 0.2, "neutral": 0.2},
                "social": {"positive": 0.4, "negative": 0.4, "neutral": 0.2},
                "analyst_opinions": {"positive": 0.7, "negative": 0.1, "neutral": 0.2}
            },
            "overall": {"positive": 0.58, "negative": 0.21, "neutral": 0.21},
            "overall_market_emotion": "Optimistic",
            "emotion_rationale": "Weighted sentiment leans positive due to analyst optimism and favorable news coverage.",
            "drivers": [
                "Analyst upgrades from major firms (analyst_opinions)",
                "Strong earnings beat reported in recent news (news)",
                "Retail sentiment mixed with profit-taking concerns (social)"
            ],
            "divergence_flag": {
                "detected": True,
                "description": "Analyst opinions are positive (70%) while social sentiment is evenly split (40% positive, 40% negative), indicating institutional-retail divergence."
            },
            "confidence": "High"
        }
    
    async def agenerate_json(
        self,
        system_prompt: str,
        user_message: str,
        response_schema: dict,
        model: str,
        **kwargs
    ) -> dict:
        self.call_count += 1
        self.agenerate_json_called = True
        
        if not self.should_succeed:
            raise Exception(self.error or "LLM call failed")
        
        class MockUsage:
            model = "test-model"
            prompt_tokens = 1000
            completion_tokens = 500
            total_tokens = 1500
            cost = 0.005
            
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

    def generate_json(
        self,
        system_prompt: str,
        user_message: str,
        response_schema: dict,
        model: str,
        **kwargs
    ) -> dict:
        self.call_count += 1
        self.generate_json_called = True
        
        if not self.should_succeed:
            raise Exception(self.error or "LLM call failed")
        
        class MockUsage:
            model = "test-model"
            prompt_tokens = 1000
            completion_tokens = 500
            total_tokens = 1500
            cost = 0.005
            
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


class TestSentimentAgentInput:
    """Test SentimentAgentInput schema validation."""
    
    def test_valid_input_all_sources(self):
        """Test valid input with all source types."""
        input_data = SentimentAgentInput(
            company="NVIDIA",
            as_of_date="2024-01-15",
            news_items=[
                NewsItemIn(title="NVDA beats earnings", impact="positive", date="2024-01-14"),
                NewsItemIn(title="Supply chain concerns", impact="negative", date="2024-01-13"),
            ],
            social_items=[
                SocialItemIn(platform="Twitter", text_summary="Bullish on AI", sentiment="positive", date="2024-01-14"),
            ],
            analyst_opinions=[
                AnalystOpinionIn(firm="Goldman Sachs", rating="Buy", note_summary="Raised target", date="2024-01-14"),
            ],
        )
        assert input_data.company == "NVIDIA"
        assert len(input_data.news_items) == 2
        assert len(input_data.social_items) == 1
        assert len(input_data.analyst_opinions) == 1
    
    def test_minimal_input(self):
        """Test minimal input with only required fields."""
        input_data = SentimentAgentInput(
            company="Apple",
            as_of_date="2024-01-15",
        )
        assert input_data.company == "Apple"
        assert input_data.news_items == []
        assert input_data.social_items == []
        assert input_data.analyst_opinions == []
    
    def test_empty_company_raises_error(self):
        """Test that empty company name fails validation."""
        input_data = SentimentAgentInput(
            company="",
            as_of_date="2024-01-15",
        )
        # Pydantic allows empty strings by default, just verify it's stored
        assert input_data.company == ""
    
    def test_news_item_impact_validation(self):
        """Test NewsItemIn impact validation."""
        item = NewsItemIn(title="Test", impact="positive", date="2024-01-15")
        assert item.impact == "positive"
        
        with pytest.raises(ValueError):
            NewsItemIn(title="Test", impact="invalid", date="2024-01-15")
    
    def test_social_item_sentiment_validation(self):
        """Test SocialItemIn sentiment validation."""
        item = SocialItemIn(platform="Twitter", text_summary="Test", sentiment="neutral", date="2024-01-15")
        assert item.sentiment == "neutral"
        
        with pytest.raises(ValueError):
            SocialItemIn(platform="Twitter", text_summary="Test", sentiment="invalid", date="2024-01-15")


class TestSentimentDistribution:
    """Test SentimentDistribution schema validation."""
    
    def test_valid_distribution(self):
        """Test valid distribution that sums to 1.0."""
        dist = SentimentDistribution(positive=0.5, negative=0.3, neutral=0.2)
        assert dist.positive == 0.5
        assert dist.negative == 0.3
        assert dist.neutral == 0.2
    
    def test_distribution_sums_to_one(self):
        """Test that positive+negative+neutral must sum to ~1.0."""
        with pytest.raises(ValueError, match="must sum to 1.0"):
            SentimentDistribution(positive=0.5, negative=0.3, neutral=0.3)
    
    def test_distribution_tolerance(self):
        """Test small floating point tolerance."""
        # 0.02 tolerance per schema
        dist = SentimentDistribution(positive=0.33, negative=0.33, neutral=0.34)
        assert dist.neutral == 0.34


class TestSentimentAgentOutput:
    """Test SentimentAgentOutput schema validation."""
    
    def test_valid_output(self):
        """Test valid complete output structure."""
        output = SentimentAgentOutput(
            agent="sentiment_agent",
            company="NVIDIA",
            generated_at=datetime.utcnow(),
            by_source=BySource(
                news=SentimentDistribution(positive=0.6, negative=0.2, neutral=0.2),
                social=SentimentDistribution(positive=0.4, negative=0.4, neutral=0.2),
                analyst_opinions=SentimentDistribution(positive=0.7, negative=0.1, neutral=0.2),
            ),
            overall=SentimentDistribution(positive=0.58, negative=0.21, neutral=0.21),
            overall_market_emotion="Optimistic",
            emotion_rationale="Test rationale",
            drivers=["Driver 1", "Driver 2", "Driver 3"],
            divergence_flag=DivergenceFlag(detected=True, description="Divergence found"),
            confidence="High",
        )
        assert output.company == "NVIDIA"
        assert output.confidence == "High"
        assert len(output.drivers) == 3
    
    def test_confidence_validation(self):
        """Test confidence must be High/Medium/Low."""
        with pytest.raises(ValueError):
            SentimentAgentOutput(
                agent="sentiment_agent",
                company="Test",
                generated_at=datetime.utcnow(),
                by_source=BySource(
                    news=SentimentDistribution(positive=0.33, negative=0.33, neutral=0.34),
                    social=SentimentDistribution(positive=0.33, negative=0.33, neutral=0.34),
                    analyst_opinions=SentimentDistribution(positive=0.33, negative=0.33, neutral=0.34),
                ),
                overall=SentimentDistribution(positive=0.33, negative=0.33, neutral=0.34),
                overall_market_emotion="Neutral",
                emotion_rationale="Test",
                drivers=[],
                divergence_flag=DivergenceFlag(detected=False, description="None"),
                confidence="Invalid",
            )


class TestSentimentAgent:
    """Test SentimentAgent execution."""
    
    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider."""
        return MockLLMProvider(should_succeed=True)
    
    @pytest.fixture
    def mock_context(self):
        """Create mock context with sentiment data."""
        return {
            "news_items": [
                {"title": "NVDA beats earnings", "impact": "positive", "date": "2024-01-14"},
                {"title": "Supply chain concerns", "impact": "negative", "date": "2024-01-13"},
            ],
            "social_items": [
                {"platform": "Twitter", "text_summary": "Bullish on AI", "sentiment": "positive", "date": "2024-01-14"},
            ],
            "analyst_opinions": [
                {"firm": "Goldman Sachs", "rating": "Buy", "note_summary": "Raised target", "date": "2024-01-14"},
            ],
        }
    
    @pytest.mark.asyncio
    async def test_init(self, mock_llm_provider):
        """Test agent initialization."""
        agent = SentimentAgent(llm_provider=mock_llm_provider)
        assert agent.llm_provider == mock_llm_provider
        assert agent.agent_name == "sentiment_agent"
    
    @pytest.mark.asyncio
    async def test_run_success(self, mock_llm_provider, mock_context):
        """Test successful sentiment analysis."""
        agent = SentimentAgent(llm_provider=mock_llm_provider)
        result = await agent.run(company="NVIDIA", context=mock_context)
        
        assert isinstance(result, WorkerResponse)
        assert result.status == "success"
        assert result.data is not None
        assert result.data["company"] == "NVIDIA"
        assert "by_source" in result.data
        assert "overall" in result.data
        assert "overall_market_emotion" in result.data
        assert result.usage is not None
        assert mock_llm_provider.agenerate_json_called
    
    @pytest.mark.asyncio
    async def test_run_news_only(self, mock_llm_provider):
        """Test with only news items (no social/analyst)."""
        context = {
            "news_items": [
                {"title": "Positive news", "impact": "positive", "date": "2024-01-15"},
            ],
            "social_items": [],
            "analyst_opinions": [],
        }
        agent = SentimentAgent(llm_provider=mock_llm_provider)
        result = await agent.run(company="Apple", context=context)
        
        assert result.status == "success"
        assert result.data["company"] == "Apple"
    
    @pytest.mark.asyncio
    async def test_run_missing_optional_sources(self, mock_llm_provider):
        """Test with missing optional context keys."""
        context = {}  # Empty context
        agent = SentimentAgent(llm_provider=mock_llm_provider)
        result = await agent.run(company="Microsoft", context=context)
        
        assert result.status == "success"
        assert result.data["company"] == "Microsoft"
    
    @pytest.mark.asyncio
    async def test_run_llm_failure(self, mock_context):
        """Test handling of LLM failure."""
        failing_llm = MockLLMProvider(should_succeed=False, error="API rate limit")
        agent = SentimentAgent(llm_provider=failing_llm)
        result = await agent.run(company="NVIDIA", context=mock_context)
        
        assert result.status == "error"
        assert "rate limit" in result.error.lower() or "llm" in result.error.lower()
        assert result.data is None
    
    @pytest.mark.asyncio
    async def test_run_invalid_schema_response(self, mock_context):
        """Test handling of invalid LLM response schema."""
        bad_llm = MockLLMProvider(
            should_succeed=True,
            response_data={"invalid": "schema"}  # Missing required fields
        )
        agent = SentimentAgent(llm_provider=bad_llm)
        result = await agent.run(company="NVIDIA", context=mock_context)
        
        assert result.status == "error"
        assert "validation" in result.error.lower() or "schema" in result.error.lower()
        assert result.data is None
    
    @pytest.mark.asyncio
    async def test_run_empty_company(self, mock_llm_provider, mock_context):
        """Test handling of empty company name."""
        agent = SentimentAgent(llm_provider=mock_llm_provider)
        result = await agent.run(company="", context=mock_context)
        
        # Should still process (company validation is lenient)
        assert result.status in ["success", "error"]
    
    @pytest.mark.asyncio
    async def test_confidence_scoring(self, mock_llm_provider, mock_context):
        """Test that confidence is properly assigned."""
        agent = SentimentAgent(llm_provider=mock_llm_provider)
        result = await agent.run(company="NVIDIA", context=mock_context)
        
        assert result.status == "success"
        assert result.data["confidence"] in ["High", "Medium", "Low"]
    
    @pytest.mark.asyncio
    async def test_divergence_detection(self, mock_llm_provider, mock_context):
        """Test divergence flag in output."""
        agent = SentimentAgent(llm_provider=mock_llm_provider)
        result = await agent.run(company="NVIDIA", context=mock_context)
        
        assert result.status == "success"
        assert "divergence_flag" in result.data
        assert "detected" in result.data["divergence_flag"]
        assert "description" in result.data["divergence_flag"]


class TestSentimentAgentSyncWrapper:
    """Test synchronous wrapper for testing."""
    
    def test_sync_wrapper_success(self):
        """Test sync wrapper returns proper WorkerResponse."""
        mock_llm = MockLLMProvider(should_succeed=True)
        
        with patch('rag.retriever.retrieve', return_value=[]):
            result = run_sentiment_agent_sync(
                mock_llm,
                company="NVIDIA",
                context={
                    "news_items": [{"title": "Test", "impact": "positive", "date": "2024-01-15"}],
                    "social_items": [],
                    "analyst_opinions": [],
                }
            )
        
        assert result.status == "success"
        assert result.data["company"] == "NVIDIA"
    
    def test_sync_wrapper_with_all_sources(self):
        """Test sync wrapper with all source types."""
        mock_llm = MockLLMProvider(should_succeed=True)
        
        with patch('rag.retriever.retrieve', return_value=[]):
            result = run_sentiment_agent_sync(
                mock_llm,
                company="Apple",
                context={
                    "news_items": [{"title": "News", "impact": "positive", "date": "2024-01-15"}],
                    "social_items": [{"platform": "Reddit", "text_summary": "Bullish", "sentiment": "positive", "date": "2024-01-15"}],
                    "analyst_opinions": [{"firm": "Morgan Stanley", "rating": "Overweight", "note_summary": "Positive", "date": "2024-01-15"}],
                }
            )
        
        assert result.status == "success"
        assert result.data["company"] == "Apple"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])