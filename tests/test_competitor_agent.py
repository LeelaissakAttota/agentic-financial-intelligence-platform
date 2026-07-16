"""
Tests for the Competitor Intelligence Agent.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from agents.competitor_agent.agent import (
    CompetitorAgent,
    run_competitor_agent_sync,
)
from agents.competitor_agent.schemas import (
    CompetitorAgentInput,
    CompetitorAgentOutput,
    CompetitorMetricsIn,
    ComparisonRow,
    RankedEntry,
)
from agents.manager_agent.schemas import WorkerResponse
from agents.competitor_agent.exceptions import (
    CompetitorAgentError,
    CompetitorAgentInputError,
    CompetitorAgentLLMError,
    CompetitorAgentValidationError,
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
            "segment": "AI Chips",
            "comparison_table": [
                {
                    "name": "NVIDIA",
                    "revenue_ttm": "60.9B",
                    "revenue_growth_yoy_pct": 126.0,
                    "market_share_pct": 80.0,
                    "technology_summary": "Hopper/Blackwell architecture, CUDA ecosystem",
                    "competitive_advantage": "Software moat via CUDA, leading performance per watt",
                    "key_risks": ["Export controls", "Customer concentration"]
                },
                {
                    "name": "AMD",
                    "revenue_ttm": "22.7B",
                    "revenue_growth_yoy_pct": 10.0,
                    "market_share_pct": 15.0,
                    "technology_summary": "MI300 series, ROCm ecosystem",
                    "competitive_advantage": "Strong x86 integration, open software stack",
                    "key_risks": ["Software ecosystem maturity", "Manufacturing capacity"]
                },
                {
                    "name": "Intel",
                    "revenue_ttm": "54.2B",
                    "revenue_growth_yoy_pct": -14.0,
                    "market_share_pct": 3.0,
                    "technology_summary": "Gaudi3, Xe architecture",
                    "competitive_advantage": "Foundry control, x86 ecosystem",
                    "key_risks": ["Execution delays", "Foundry losses"]
                }
            ],
            "positioning_narrative": "NVIDIA dominates the AI chip market with ~80% share, driven by its CUDA software moat and performance leadership. AMD is a distant second but gaining traction with MI300. Intel lags significantly in AI accelerators despite foundry control.",
            "ranked_by_strength": [
                {"rank": 1, "name": "NVIDIA", "reasoning": "Market leader with strongest software moat and performance"},
                {"rank": 2, "name": "AMD", "reasoning": "Strong product roadmap and open ecosystem, but behind on software maturity"},
                {"rank": 3, "name": "Intel", "reasoning": "Early stage in AI accelerators, execution challenges persist"}
            ],
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


class TestCompetitorAgentInput:
    """Test CompetitorAgentInput schema validation."""

    def test_valid_input_all_fields(self):
        """Test valid input with all fields populated."""
        input_data = CompetitorAgentInput(
            company="NVIDIA",
            ticker="NVDA",
            segment="AI Chips",
            target_metrics=CompetitorMetricsIn(
                name="NVIDIA",
                revenue_ttm="60.9B",
                revenue_growth_yoy_pct=126.0,
                market_share_pct=80.0,
                technology_notes="Hopper/Blackwell, CUDA",
                known_risks=["Export controls"]
            ),
            competitors=[
                CompetitorMetricsIn(
                    name="AMD",
                    revenue_ttm="22.7B",
                    revenue_growth_yoy_pct=10.0,
                    market_share_pct=15.0,
                    technology_notes="MI300, ROCm",
                    known_risks=["Software maturity"]
                ),
                CompetitorMetricsIn(
                    name="Intel",
                    revenue_ttm="54.2B",
                    revenue_growth_yoy_pct=-14.0,
                    market_share_pct=3.0,
                    technology_notes="Gaudi3, Xe",
                    known_risks=["Execution delays"]
                )
            ]
        )
        assert input_data.company == "NVIDIA"
        assert input_data.ticker == "NVDA"
        assert input_data.segment == "AI Chips"
        assert len(input_data.competitors) == 2

    def test_minimal_input(self):
        """Test input with only required fields."""
        input_data = CompetitorAgentInput(
            company="TestCo",
            ticker="TEST",
            segment="Test Segment",
            target_metrics=CompetitorMetricsIn(name="TestCo"),
            competitors=[]
        )
        assert input_data.company == "TestCo"
        assert input_data.competitors == []

    def test_empty_company_raises_error(self):
        """Test that empty company name fails validation."""
        input_data = CompetitorAgentInput(
            company="",
            ticker="TEST",
            segment="Test",
            target_metrics=CompetitorMetricsIn(name="TestCo"),
            competitors=[]
        )
        assert input_data.company == ""


class TestComparisonRow:
    """Test ComparisonRow schema."""

    def test_valid_row(self):
        """Test valid comparison row."""
        row = ComparisonRow(
            name="NVIDIA",
            revenue_ttm="60.9B",
            revenue_growth_yoy_pct=126.0,
            market_share_pct=80.0,
            technology_summary="Leading architecture",
            competitive_advantage="CUDA moat",
            key_risks=["Export controls"]
        )
        assert row.name == "NVIDIA"
        assert row.revenue_growth_yoy_pct == 126.0

    def test_row_with_not_available(self):
        """Test row with 'not available' string values."""
        row = ComparisonRow(
            name="Startup",
            revenue_ttm="not available",
            revenue_growth_yoy_pct="not available",
            market_share_pct="not available",
            technology_summary="Emerging tech",
            competitive_advantage="Niche focus",
            key_risks=["Funding"]
        )
        assert row.revenue_ttm == "not available"
        assert row.revenue_growth_yoy_pct == "not available"


class TestRankedEntry:
    """Test RankedEntry schema."""

    def test_valid_entry(self):
        """Test valid ranked entry."""
        entry = RankedEntry(
            rank=1,
            name="NVIDIA",
            reasoning="Market leader with software moat"
        )
        assert entry.rank == 1
        assert entry.name == "NVIDIA"


class TestCompetitorAgentOutput:
    """Test CompetitorAgentOutput schema."""

    def test_valid_output(self):
        """Test valid complete output."""
        output = CompetitorAgentOutput(
            agent="competitor_agent",
            company="NVIDIA",
            generated_at=datetime.utcnow(),
            segment="AI Chips",
            comparison_table=[
                ComparisonRow(
                    name="NVIDIA",
                    revenue_ttm="60.9B",
                    revenue_growth_yoy_pct=126.0,
                    market_share_pct=80.0,
                    technology_summary="Hopper/Blackwell",
                    competitive_advantage="CUDA moat",
                    key_risks=["Export controls"]
                )
            ],
            positioning_narrative="NVIDIA dominates...",
            ranked_by_strength=[
                RankedEntry(rank=1, name="NVIDIA", reasoning="Leader")
            ],
            confidence="High"
        )
        assert output.company == "NVIDIA"
        assert output.confidence == "High"
        assert len(output.comparison_table) == 1
        assert len(output.ranked_by_strength) == 1


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    return MockLLMProvider(should_succeed=True)

@pytest.fixture
def mock_context():
    """Create mock context with competitor data."""
    return {
        "company": "NVIDIA",
        "ticker": "NVDA",
        "segment": "AI Chips",
        "target_metrics": {
            "name": "NVIDIA",
            "revenue_ttm": "60.9B",
            "revenue_growth_yoy_pct": 126.0,
            "market_share_pct": 80.0,
            "technology_notes": "Hopper/Blackwell, CUDA",
            "known_risks": ["Export controls"]
        },
        "competitors": [
            {
                "name": "AMD",
                "revenue_ttm": "22.7B",
                "revenue_growth_yoy_pct": 10.0,
                "market_share_pct": 15.0,
                "technology_notes": "MI300, ROCm",
                "known_risks": ["Software maturity"]
            },
            {
                "name": "Intel",
                "revenue_ttm": "54.2B",
                "revenue_growth_yoy_pct": -14.0,
                "market_share_pct": 3.0,
                "technology_notes": "Gaudi3, Xe",
                "known_risks": ["Execution delays"]
            }
        ]
    }


class TestCompetitorAgent:
    """Test CompetitorAgent execution."""

    @pytest.mark.asyncio
    async def test_init(self, mock_llm_provider):
        """Test agent initialization."""
        agent = CompetitorAgent(llm_provider=mock_llm_provider)
        assert agent.llm_provider == mock_llm_provider
        assert agent.agent_name == "competitor_agent"

    @pytest.mark.asyncio
    async def test_run_success(self, mock_llm_provider, mock_context):
        """Test successful competitor analysis."""
        agent = CompetitorAgent(llm_provider=mock_llm_provider)
        result = await agent.run(company="NVIDIA", context=mock_context)

        assert isinstance(result, WorkerResponse)
        assert result.status == "success"
        assert result.data is not None
        assert result.data["company"] == "NVIDIA"
        assert "comparison_table" in result.data
        assert "positioning_narrative" in result.data
        assert "ranked_by_strength" in result.data
        assert result.usage is not None
        assert mock_llm_provider.agenerate_json_called

    @pytest.mark.asyncio
    async def test_run_no_competitors(self, mock_llm_provider):
        """Test with empty competitors list."""
        context = {
            "company": "SoloCorp",
            "ticker": "SOLO",
            "segment": "Test",
            "target_metrics": {"name": "SoloCorp"},
            "competitors": []
        }
        agent = CompetitorAgent(llm_provider=mock_llm_provider)
        result = await agent.run(company="SoloCorp", context=context)

        assert result.status == "success"
        assert result.data["company"] == "SoloCorp"

    @pytest.mark.asyncio
    async def test_run_missing_optional_context(self, mock_llm_provider):
        """Test with missing optional context keys."""
        context = {"company": "TestCo", "ticker": "TEST"}
        agent = CompetitorAgent(llm_provider=mock_llm_provider)
        result = await agent.run(company="TestCo", context=context)

        assert result.status == "success"
        assert result.data["company"] == "TestCo"

    @pytest.mark.asyncio
    async def test_run_llm_failure(self, mock_context):
        """Test handling of LLM failure."""
        failing_llm = MockLLMProvider(should_succeed=False, error="API rate limit")
        agent = CompetitorAgent(llm_provider=failing_llm)
        result = await agent.run(company="NVIDIA", context=mock_context)

        assert result.status == "error"
        assert "rate limit" in result.error.lower() or "llm" in result.error.lower()
        assert result.data is None

    @pytest.mark.asyncio
    async def test_run_invalid_schema_response(self, mock_context):
        """Test handling of invalid LLM response schema."""
        bad_llm = MockLLMProvider(
            should_succeed=True,
            response_data={"invalid": "schema"}
        )
        agent = CompetitorAgent(llm_provider=bad_llm)
        result = await agent.run(company="NVIDIA", context=mock_context)

        assert result.status == "error"
        assert "validation" in result.error.lower() or "schema" in result.error.lower()
        assert result.data is None

    @pytest.mark.asyncio
    async def test_run_empty_company(self, mock_llm_provider, mock_context):
        """Test handling of empty company name."""
        agent = CompetitorAgent(llm_provider=mock_llm_provider)
        result = await agent.run(company="", context=mock_context)

        assert result.status == "error"
        assert "company" in result.error.lower()

    @pytest.mark.asyncio
    async def test_confidence_scoring(self, mock_llm_provider, mock_context):
        """Test that confidence is properly assigned."""
        agent = CompetitorAgent(llm_provider=mock_llm_provider)
        result = await agent.run(company="NVIDIA", context=mock_context)

        assert result.status == "success"
        assert result.data["confidence"] in ["High", "Medium", "Low"]


class TestCompetitorAgentSyncWrapper:
    """Test synchronous wrapper for testing."""

    def test_sync_wrapper_success(self, mock_llm_provider):
        """Test sync wrapper success."""
        result = run_competitor_agent_sync(
            mock_llm_provider,
            company="NVIDIA",
            context={
                "company": "NVIDIA",
                "ticker": "NVDA",
                "segment": "AI Chips",
                "target_metrics": {"name": "NVIDIA"},
                "competitors": []
            }
        )

        assert result.status == "success"
        assert result.data["company"] == "NVIDIA"

    def test_sync_wrapper_with_competitors(self, mock_llm_provider):
        """Test sync wrapper with full competitor data."""
        result = run_competitor_agent_sync(
            mock_llm_provider,
            company="NVIDIA",
            context={
                "company": "NVIDIA",
                "ticker": "NVDA",
                "segment": "AI Chips",
                "target_metrics": {
                    "name": "NVIDIA",
                    "revenue_ttm": "60.9B",
                    "revenue_growth_yoy_pct": 126.0
                },
                "competitors": [
                    {"name": "AMD", "revenue_ttm": "22.7B", "revenue_growth_yoy_pct": 10.0}
                ]
            }
        )

        assert result.status == "success"
        assert result.data["company"] == "NVIDIA"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])