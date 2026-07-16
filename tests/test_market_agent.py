"""
Tests for the Market Analysis Agent.
"""

import pytest
from unittest.mock import MagicMock

from agents.market_agent.market_agent import MarketAgent, run_market_agent_sync
from agents.market_agent.schemas import (
    MarketAgentInput,
    MarketAgentOutput,
    PriceMovementAnalysis,
    TechnicalAnalysis,
    FinancialAnalysis,
    MarketTrendsAnalysis,
    WorkerResponse,
)
from agents.market_agent.exceptions import MarketAgentError, MarketAgentInputError
from data.market_data.market_data_provider import get_market_data, CompleteMarketData
from llm.llm_provider import LLMProvider


class MockLLMProvider:
    """Mock LLM provider for testing."""
    
    def __init__(self, should_succeed: bool = True, response_data: dict = None, error: str = None):
        self.should_succeed = should_succeed
        self.response_data = response_data or {
            "price_movement": {
                "trend_direction": "bullish",
                "position_in_range": "middle",
                "volume_trend": "stable",
                "key_observations": ["Price up 2%", "Volume normal"]
            },
            "technical_analysis": {
                "rsi_interpretation": "RSI at 65 - neutral",
                "moving_averages": "Price above SMA50",
                "macd_interpretation": "MACD bullish",
                "bollinger_bands": "Within bands",
                "overall_signal": "bullish"
            },
            "financial_analysis": {
                "valuation_assessment": "fairly_valued",
                "profitability": "strong",
                "growth_profile": "high_growth",
                "financial_health": "strong",
                "key_observations": ["PE: 35", "ROE: 45%"]
            },
            "market_trends": {
                "sector_performance": "outperforming",
                "relative_strength": "strong",
                "institutional_sentiment": "bullish",
                "analyst_sentiment": "bullish",
                "key_observations": ["Beta 1.7", "Inst own 80%"]
            },
            "overall_narrative": "NVDA shows strong momentum...",
            "confidence": "High"
        }
        self.error = error
        self.call_count = 0
    
    def generate_json(self, system_prompt: str, user_message: str, response_schema: dict, model: str, **kwargs) -> dict:
        self.call_count += 1
        if not self.should_succeed:
            raise Exception(self.error or "LLM call failed")
        
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
def market_agent(mock_llm_provider):
    """Create a MarketAgent instance with mock LLM provider."""
    return MarketAgent(llm_provider=mock_llm_provider)


class TestMarketAgentInput:
    """Test MarketAgentInput schema validation."""
    
    def test_valid_symbol(self):
        """Test valid symbol input."""
        input_data = MarketAgentInput(symbol="NVDA")
        assert input_data.symbol == "NVDA"
    
    def test_symbol_lowercase(self):
        """Test that symbol is converted to uppercase."""
        input_data = MarketAgentInput(symbol="nvda")
        assert input_data.symbol == "NVDA"
    
    def test_with_company_name(self):
        """Test input with company name."""
        input_data = MarketAgentInput(symbol="AAPL", company_name="Apple Inc.")
        assert input_data.symbol == "AAPL"
        assert input_data.company_name == "Apple Inc."
    
    def test_empty_symbol_raises_error(self):
        """Test that empty symbol raises validation error."""
        with pytest.raises(Exception):
            MarketAgentInput(symbol="")


class TestMarketAgentSchemas:
    """Test Market Agent output schemas."""
    
    def test_price_movement_analysis(self):
        """Test PriceMovementAnalysis schema."""
        analysis = PriceMovementAnalysis(
            trend_direction="bullish",
            position_in_range="near_high",
            volume_trend="increasing",
            key_observations=["Price up 5%", "Volume 2x avg"]
        )
        assert analysis.trend_direction == "bullish"
        assert analysis.position_in_range == "near_high"
    
    def test_technical_analysis(self):
        """Test TechnicalAnalysis schema."""
        analysis = TechnicalAnalysis(
            rsi_interpretation="RSI at 72 - overbought",
            moving_averages="Price above all MAs",
            macd_interpretation="MACD above signal",
            bollinger_bands="Near upper band",
            overall_signal="bullish"
        )
        assert analysis.overall_signal == "bullish"
    
    def test_financial_analysis(self):
        """Test FinancialAnalysis schema."""
        analysis = FinancialAnalysis(
            valuation_assessment="overvalued",
            profitability="strong",
            growth_profile="high_growth",
            financial_health="strong",
            key_observations=["PE: 50", "Margin: 30%"]
        )
        assert analysis.valuation_assessment == "overvalued"
        assert analysis.profitability == "strong"
    
    def test_market_trends_analysis(self):
        """Test MarketTrendsAnalysis schema."""
        analysis = MarketTrendsAnalysis(
            sector_performance="outperforming",
            relative_strength="strong",
            institutional_sentiment="bullish",
            analyst_sentiment="bullish",
            key_observations=["Sector up 5%"]
        )
        assert analysis.sector_performance == "outperforming"
        assert analysis.relative_strength == "strong"
    
    def test_worker_response_success(self):
        """Test WorkerResponse success format."""
        response = WorkerResponse(
            status="success",
            data={"symbol": "NVDA", "price": 875},
            usage={"model": "test", "total_tokens": 150}
        )
        assert response.status == "success"
        assert response.data["symbol"] == "NVDA"
        assert response.error is None
    
    def test_worker_response_error(self):
        """Test WorkerResponse error format."""
        response = WorkerResponse(
            status="error",
            error="API rate limit",
            data=None
        )
        assert response.status == "error"
        assert response.error == "API rate limit"


class TestMarketAgent:
    """Test MarketAgent execution."""
    
    @pytest.mark.asyncio
    async def test_run_success(self, market_agent):
        """Test successful market agent run."""
        result = await market_agent.run("NVDA")
        
        assert result.status == "success"
        assert result.data is not None
        assert result.data["symbol"] == "NVDA"
        assert "price_movement" in result.data
        assert "technical_analysis" in result.data
        assert "financial_analysis" in result.data
        assert "market_trends" in result.data
        assert "overall_narrative" in result.data
        assert "confidence" in result.data
    
    @pytest.mark.asyncio
    async def test_run_with_lowercase_symbol(self, market_agent):
        """Test run with lowercase symbol."""
        result = await market_agent.run("nvda")
        
        assert result.status == "success"
        assert result.data["symbol"] == "NVDA"
    
    @pytest.mark.asyncio
    async def test_run_with_context(self, market_agent):
        """Test run with additional context."""
        result = await market_agent.run("NVDA", {"query": "focus on AI"})
        
        assert result.status == "success"
        assert result.data["symbol"] == "NVDA"
    
    @pytest.mark.asyncio
    async def test_run_llm_failure(self):
        """Test handling of LLM failure - should fall back to fallback analysis."""
        failing_llm = MockLLMProvider(should_succeed=False, error="API rate limit exceeded")
        agent = MarketAgent(llm_provider=failing_llm)
        
        result = await agent.run("NVDA")
        
        # Should succeed with fallback analysis
        assert result.status == "success"
        assert result.data is not None
        assert "price_movement" in result.data
    
    @pytest.mark.asyncio
    async def test_run_llm_returns_empty(self, mock_llm_provider):
        """Test handling when LLM returns minimal data."""
        mock_llm_provider.response_data = {
            "price_movement": {
                "trend_direction": "neutral",
                "position_in_range": "middle",
                "volume_trend": "stable",
                "key_observations": []
            },
            "technical_analysis": {
                "rsi_interpretation": "N/A",
                "moving_averages": "N/A",
                "macd_interpretation": "N/A",
                "bollinger_bands": "N/A",
                "overall_signal": "neutral"
            },
            "financial_analysis": {
                "valuation_assessment": "insufficient_data",
                "profitability": "insufficient_data",
                "growth_profile": "insufficient_data",
                "financial_health": "insufficient_data",
                "key_observations": []
            },
            "market_trends": {
                "sector_performance": "in_line",
                "relative_strength": "neutral",
                "institutional_sentiment": "neutral",
                "analyst_sentiment": "neutral",
                "key_observations": []
            },
            "overall_narrative": "Insufficient data for analysis.",
            "confidence": "Low"
        }
        
        agent = MarketAgent(llm_provider=mock_llm_provider)
        result = await agent.run("NVDA")
        
        assert result.status == "success"
        assert result.data["confidence"] == "Low"


class TestMarketAgentSyncWrapper:
    """Test synchronous wrapper for testing."""
    
    def test_run_sync_success(self, mock_llm_provider):
        """Test synchronous wrapper success."""
        result = run_market_agent_sync(mock_llm_provider, "NVDA")
        
        assert result.status == "success"
        assert result.data["symbol"] == "NVDA"
    
    def test_run_sync_with_different_symbol(self, mock_llm_provider):
        """Test synchronous wrapper with different symbol."""
        result = run_market_agent_sync(mock_llm_provider, "AAPL")
        
        assert result.status == "success"
        assert result.data["symbol"] == "AAPL"


class TestMarketDataProvider:
    """Test the market data provider."""
    
    def test_get_nvda_data(self):
        """Test getting NVDA market data."""
        data = get_market_data("NVDA", seed=42)
        
        assert isinstance(data, CompleteMarketData)
        assert data.symbol == "NVDA"
        assert data.company_name == "NVIDIA Corporation"
        assert data.current_price > 0
        assert data.week_52_high > data.week_52_low
        assert len(data.price_data) > 0
        assert data.technical_indicators is not None
        assert data.financial_metrics is not None
        assert data.market_context is not None
        assert data.market_context.sector == "Technology"
    
    def test_get_aapl_data(self):
        """Test getting AAPL market data."""
        data = get_market_data("AAPL", seed=42)
        
        assert data.symbol == "AAPL"
        assert data.company_name == "Apple Inc."
        assert data.market_context.sector == "Technology"
    
    def test_get_unknown_symbol(self):
        """Test getting data for unknown symbol."""
        data = get_market_data("UNKNOWN", seed=42)
        
        assert data.symbol == "UNKNOWN"
        assert data.current_price > 0
    
    def test_price_data_structure(self):
        """Test price data has correct structure."""
        data = get_market_data("NVDA", seed=42)
        
        price_point = data.price_data[-1]
        assert hasattr(price_point, "date")
        assert hasattr(price_point, "open")
        assert hasattr(price_point, "high")
        assert hasattr(price_point, "low")
        assert hasattr(price_point, "close")
        assert hasattr(price_point, "volume")
    
    def test_technical_indicators_calculated(self):
        """Test technical indicators are calculated."""
        data = get_market_data("NVDA", seed=42)
        
        ti = data.technical_indicators
        # With 252 days of data, all indicators should be available
        assert ti.rsi_14 is not None
        assert ti.sma_20 is not None
        assert ti.sma_50 is not None
        assert ti.sma_200 is not None
        assert ti.macd is not None
        assert ti.bollinger_upper is not None
        assert ti.bollinger_lower is not None
    
    def test_financial_metrics_populated(self):
        """Test financial metrics are populated."""
        data = get_market_data("NVDA", seed=42)
        
        fm = data.financial_metrics
        assert fm.pe_ratio is not None
        assert fm.forward_pe is not None
        assert fm.eps is not None
        assert fm.revenue is not None
        assert fm.profit_margin is not None
        assert fm.roe is not None
        assert fm.beta is not None
    
    def test_market_context_populated(self):
        """Test market context is populated."""
        data = get_market_data("NVDA", seed=42)
        
        mc = data.market_context
        assert mc.sector == "Technology"
        assert mc.industry == "Semiconductors"
        assert mc.sector_performance_1m is not None
        assert mc.institutional_ownership is not None
        assert mc.analyst_rating is not None


class TestMarketAgentExceptions:
    """Test Market Agent custom exceptions."""
    
    def test_base_exception(self):
        """Test base exception."""
        with pytest.raises(MarketAgentError):
            raise MarketAgentError("Test error")
    
    def test_input_error(self):
        """Test input error."""
        with pytest.raises(MarketAgentInputError):
            raise MarketAgentInputError("Invalid input")
    
    def test_inheritance(self):
        """Test exception inheritance."""
        assert issubclass(MarketAgentInputError, MarketAgentError)
        assert issubclass(MarketAgentInputError, Exception)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
