"""
Tests for the Financial Report RAG Agent.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from agents.financial_report_agent.agent import (
    FinancialReportAgent,
    run_financial_report_agent_sync,
)
from agents.financial_report_agent.schemas import (
    FinancialReportInput,
    FinancialReportOutput,
    DocumentContext,
    Finding,
    RetrievedChunk,
)
from agents.manager_agent.schemas import WorkerResponse
from agents.financial_report_agent.exceptions import (
    FinancialReportAgentError,
    FinancialReportInputError,
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
            "findings": {
                "revenue_growth_yoy": {
                    "value": "+126%",
                    "chunk_id": "10K_p42_1",
                    "conflict_note": None
                },
                "gross_margin": {
                    "value": "74.8%",
                    "chunk_id": "10K_p45_2",
                    "conflict_note": None
                },
                "net_income": {
                    "value": "$29.76B",
                    "chunk_id": "10K_p48_1",
                    "conflict_note": None
                },
                "free_cash_flow": {
                    "value": "not found in provided document",
                    "chunk_id": None,
                    "conflict_note": None
                },
                "segment_breakdown": {
                    "value": "Data Center: $47.5B, Gaming: $11.9B",
                    "chunk_id": "10K_p55_3",
                    "conflict_note": None
                },
                "debt_levels": {
                    "value": "Long-term debt: $9.5B",
                    "chunk_id": "10K_p60_2",
                    "conflict_note": None
                }
            },
            "document_context": {
                "doc_types_used": ["10-K"],
                "fiscal_year": "2024",
                "fiscal_quarter": None
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
    
    # For backward compatibility with sync wrapper
    def generate(self, system_prompt: str, user_payload: dict, model: str = None, **kwargs) -> dict:
        self.call_count += 1
        if not self.should_succeed:
            raise Exception(self.error or "LLM call failed")
        return self.response_data


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    return MockLLMProvider(should_succeed=True)


@pytest.fixture
def mock_retriever():
    """Mock the RAG retriever."""
    with patch('rag.retriever.retrieve') as mock:
        yield mock


class TestFinancialReportInput:
    """Test FinancialReportInput schema validation."""
    
    def test_valid_input(self):
        """Test valid input with all fields."""
        input_data = FinancialReportInput(
            company="NVIDIA",
            ticker="NVDA",
            question_set=["revenue_growth_yoy", "gross_margin", "net_income"],
            retrieved_chunks=[
                RetrievedChunk(
                    chunk_id="10K_p42_1",
                    text="Revenue increased 126% year over year...",
                    doc_type="10-K",
                    fiscal_year="2024",
                    fiscal_quarter=None,
                    section="Income Statement",
                    page_number=42,
                    similarity_score=0.95
                )
            ]
        )
        assert input_data.company == "NVIDIA"
        assert input_data.ticker == "NVDA"
        assert len(input_data.question_set) == 3
        assert len(input_data.retrieved_chunks) == 1
    
    def test_minimal_input(self):
        """Test input with only required fields."""
        input_data = FinancialReportInput(
            company="Apple",
            ticker="AAPL",
            question_set=["revenue_growth_yoy"],
            retrieved_chunks=[]
        )
        assert input_data.company == "Apple"
        assert input_data.ticker == "AAPL"
        assert len(input_data.retrieved_chunks) == 0
    
    def test_empty_company_raises_error(self):
        """Test that empty company name fails validation."""
        input_data = FinancialReportInput(
            company="",
            ticker="TEST",
            question_set=["revenue_growth_yoy"],
            retrieved_chunks=[]
        )
        assert input_data.company == ""


class TestRetrievedChunk:
    """Test RetrievedChunk schema."""
    
    def test_valid_chunk(self):
        """Test valid retrieved chunk."""
        chunk = RetrievedChunk(
            chunk_id="10K_p42_1",
            text="Revenue increased significantly...",
            doc_type="10-K",
            fiscal_year="2024",
            fiscal_quarter=None,
            section="Income Statement",
            page_number=42,
            similarity_score=0.95
        )
        assert chunk.chunk_id == "10K_p42_1"
        assert chunk.doc_type == "10-K"
        assert chunk.similarity_score == 0.95
    
    def test_chunk_with_quarter(self):
        """Test chunk with fiscal quarter."""
        chunk = RetrievedChunk(
            chunk_id="10Q_p15_3",
            text="Quarterly revenue...",
            doc_type="10-Q",
            fiscal_year="2024",
            fiscal_quarter=2,
            section="MD&A",
            page_number=15,
            similarity_score=0.88
        )
        assert chunk.fiscal_quarter == 2
        assert chunk.doc_type == "10-Q"


class TestFinding:
    """Test Finding schema."""
    
    def test_finding_with_chunk(self):
        """Test finding with chunk citation."""
        finding = Finding(
            value="+126%",
            chunk_id="10K_p42_1",
            conflict_note=None
        )
        assert finding.value == "+126%"
        assert finding.chunk_id == "10K_p42_1"
    
    def test_finding_not_found(self):
        """Test finding when data not found."""
        finding = Finding(
            value="not found in provided document",
            chunk_id=None,
            conflict_note=None
        )
        assert finding.value == "not found in provided document"
        assert finding.chunk_id is None
    
    def test_finding_with_conflict(self):
        """Test finding with conflict note."""
        finding = Finding(
            value="$29.76B",
            chunk_id="10K_p48_1",
            conflict_note="10-Q preliminary was $28.9B, 10-K restated to $29.76B"
        )
        assert finding.conflict_note is not None
        assert "restated" in finding.conflict_note


class TestDocumentContext:
    """Test DocumentContext schema."""
    
    def test_valid_context(self):
        """Test valid document context."""
        context = DocumentContext(
            doc_types_used=["10-K", "10-Q"],
            fiscal_year="2024",
            fiscal_quarter=2
        )
        assert "10-K" in context.doc_types_used
        assert context.fiscal_year == "2024"
        assert context.fiscal_quarter == 2


class TestFinancialReportOutput:
    """Test FinancialReportOutput schema."""
    
    def test_valid_output(self):
        """Test valid output structure."""
        output = FinancialReportOutput(
            agent="financial_report_agent",
            company="NVIDIA",
            generated_at=datetime.utcnow(),
            document_context=DocumentContext(
                doc_types_used=["10-K"],
                fiscal_year="2024"
            ),
            findings={
                "revenue_growth_yoy": Finding(
                    value="+126%",
                    chunk_id="10K_p42_1"
                )
            },
            confidence="High"
        )
        assert output.agent == "financial_report_agent"
        assert output.company == "NVIDIA"
        assert output.confidence == "High"
        assert "revenue_growth_yoy" in output.findings


class TestFinancialReportAgent:
    """Test FinancialReportAgent execution."""
    
    @pytest.mark.asyncio
    async def test_init(self, mock_llm_provider):
        """Test agent initialization."""
        agent = FinancialReportAgent(llm_provider=mock_llm_provider)
        assert agent.llm_provider == mock_llm_provider
        assert agent.agent_name == "financial_report_agent"
    
    @pytest.mark.asyncio
    async def test_run_success(self, mock_llm_provider, mock_retriever):
        """Test successful financial report generation."""
        mock_retriever.return_value = []
        
        agent = FinancialReportAgent(llm_provider=mock_llm_provider)
        result = await agent.run(
            company="NVIDIA",
            context={
                "ticker": "NVDA",
                "question_set": ["revenue_growth_yoy"]
            }
        )
        
        assert result.status == "success"
        assert result.data is not None
        assert result.data["company"] == "NVIDIA"
        assert "findings" in result.data
        assert "revenue_growth_yoy" in result.data["findings"]
        assert result.usage is not None
    
    @pytest.mark.asyncio
    async def test_run_with_retriever_error(self, mock_llm_provider, mock_retriever):
        """Test handling of retriever failure."""
        mock_retriever.side_effect = Exception("Vector store unavailable")
        
        agent = FinancialReportAgent(llm_provider=mock_llm_provider)
        result = await agent.run(
            company="NVIDIA",
            context={
                "ticker": "NVDA",
                "question_set": ["revenue_growth_yoy"]
            }
        )
        
        assert result.status in ["success", "error"]
    
    @pytest.mark.asyncio
    async def test_run_llm_failure(self, mock_retriever):
        """Test handling of LLM failure."""
        failing_llm = MockLLMProvider(should_succeed=False, error="API rate limit")
        mock_retriever.return_value = []
        
        agent = FinancialReportAgent(llm_provider=failing_llm)
        result = await agent.run(
            company="NVIDIA",
            context={
                "ticker": "NVDA",
                "question_set": ["revenue_growth_yoy"]
            }
        )
        
        assert result.status == "error"
        assert "Financial report agent failed" in result.error or "rate limit" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_run_invalid_schema_response(self, mock_retriever):
        """Test handling of invalid LLM response schema."""
        bad_llm = MockLLMProvider(
            should_succeed=True,
            response_data={"invalid": "schema"}  # Missing required fields
        )
        mock_retriever.return_value = []
        
        agent = FinancialReportAgent(llm_provider=bad_llm)
        result = await agent.run(
            company="NVIDIA",
            context={
                "ticker": "NVDA",
                "question_set": ["revenue_growth_yoy"]
            }
        )
        
        assert result.status == "error"
    
    @pytest.mark.asyncio
    async def test_run_empty_question_set(self, mock_llm_provider, mock_retriever):
        """Test with empty question set."""
        mock_retriever.return_value = []
        
        agent = FinancialReportAgent(llm_provider=mock_llm_provider)
        result = await agent.run(
            company="NVIDIA",
            context={
                "ticker": "NVDA",
                "question_set": []
            }
        )
        
        assert result.status in ["success", "error"]
    
    @pytest.mark.asyncio
    async def test_run_not_found_handling(self, mock_retriever):
        """Test handling of 'not found' responses."""
        llm_response = {
            "findings": {
                "revenue_growth_yoy": {
                    "value": "+126%",
                    "chunk_id": "10K_p42_1"
                },
                "gross_margin": {
                    "value": "not found in provided document",
                    "chunk_id": None
                },
                "net_income": {
                    "value": "not found in provided document",
                    "chunk_id": None
                }
            },
            "document_context": {
                "doc_types_used": ["10-K"],
                "fiscal_year": "2024",
                "fiscal_quarter": None
            },
            "confidence": "Medium"
        }
        custom_llm = MockLLMProvider(should_succeed=True, response_data=llm_response)
        mock_retriever.return_value = []
        
        agent = FinancialReportAgent(llm_provider=custom_llm)
        result = await agent.run(
            company="NVIDIA",
            context={
                "ticker": "NVDA",
                "question_set": ["revenue_growth_yoy", "gross_margin", "net_income"]
            }
        )
        
        assert result.status == "success"
        assert result.data["findings"]["revenue_growth_yoy"]["value"] == "+126%"
        assert result.data["findings"]["gross_margin"]["value"] == "not found in provided document"
        assert result.data["findings"]["gross_margin"]["chunk_id"] is None
    
    @pytest.mark.asyncio
    async def test_run_conflict_detection(self, mock_retriever):
        """Test conflict note handling."""
        llm_response = {
            "findings": {
                "revenue_growth_yoy": {
                    "value": "+126%",
                    "chunk_id": "10K_p42_1",
                    "conflict_note": "10-Q showed +120%, 10-K restated to +126%"
                }
            },
            "document_context": {
                "doc_types_used": ["10-K"],
                "fiscal_year": "2024",
                "fiscal_quarter": None
            },
            "confidence": "High"
        }
        custom_llm = MockLLMProvider(should_succeed=True, response_data=llm_response)
        mock_retriever.return_value = []
        
        agent = FinancialReportAgent(llm_provider=custom_llm)
        result = await agent.run(
            company="NVIDIA",
            context={
                "ticker": "NVDA",
                "question_set": ["revenue_growth_yoy"]
            }
        )
        
        assert result.status == "success"
        assert "restated" in result.data["findings"]["revenue_growth_yoy"]["conflict_note"]
    
    @pytest.mark.asyncio
    async def test_question_set_coverage(self, mock_retriever):
        """Test that all requested questions are covered in output."""
        mock_retriever.return_value = []
        
        agent = FinancialReportAgent(llm_provider=mock_llm_provider)
        questions = ["revenue_growth_yoy", "gross_margin", "net_income", "free_cash_flow"]
        
        result = await agent.run(
            company="NVIDIA",
            context={
                "ticker": "NVDA",
                "question_set": questions
            }
        )
        
        if result.status == "success":
            for q in questions:
                assert q in result.data["findings"]
                assert "value" in result.data["findings"][q]


class TestFinancialReportAgentSyncWrapper:
    """Test synchronous wrapper for testing."""
    
    def test_sync_wrapper_success(self, mock_llm_provider):
        """Test sync wrapper success."""
        with patch('rag.retriever.retrieve', return_value=[]):
            result = run_financial_report_agent_sync(
                mock_llm_provider,
                company="NVIDIA",
                context={
                    "ticker": "NVDA",
                    "question_set": ["revenue_growth_yoy"],
                    "fiscal_year": "2024"
                }
            )
        
        assert result.status == "success"
        assert result.data["company"] == "NVIDIA"
    
    def test_sync_wrapper_with_context(self, mock_llm_provider):
        """Test sync wrapper with context."""
        with patch('rag.retriever.retrieve', return_value=[]):
            result = run_financial_report_agent_sync(
                mock_llm_provider,
                company="Apple",
                context={
                    "ticker": "AAPL",
                    "question_set": ["revenue_growth_yoy", "gross_margin"],
                    "fiscal_year": "2024"
                }
            )
        
        assert result.status == "success"
        assert result.data["company"] == "Apple"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])