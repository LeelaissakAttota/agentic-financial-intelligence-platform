import pytest
from unittest.mock import AsyncMock, MagicMock
from agents.manager_agent.manager import ManagerAgent
from agents.manager_agent.schemas import TaskType, ManagerAgentInput, TaskPlan, WorkerResponse, ManagerAgentOutput
from llm.llm_provider import LLMProvider


class MockWorkerAgent:
    """Mock worker agent for testing."""
    
    def __init__(self, agent_name: str, should_succeed: bool = True):
        self.agent_name = agent_name
        self.should_succeed = should_succeed
    
    async def run(self, company: str, context: dict) -> WorkerResponse:
        if self.should_succeed:
            return WorkerResponse(
                status="success",
                data={"test": f"data_from_{self.agent_name}"},
                usage={"model": "test_model", "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost_usd": 0.001}
            )
        else:
            return WorkerResponse(
                status="error",
                error=f"Simulated error from {self.agent_name}",
                usage={"model": "test_model", "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost_usd": 0.001}
            )


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    mock = MagicMock(spec=LLMProvider)
    return mock


@pytest.fixture
def manager_agent(mock_llm_provider):
    """Create a ManagerAgent instance with mock LLM provider."""
    return ManagerAgent(llm_provider=mock_llm_provider)


@pytest.mark.asyncio
async def test_manager_agent_receives_company_analysis_request(manager_agent):
    """Test that ManagerAgent accepts a company analysis request."""
    # Arrange
    company = "NVIDIA"
    query = "Analyze NVIDIA for investment"
    
    # Act
    # We won't actually run it since we need workers registered, but we can test initialization
    assert manager_agent.llm_provider is not None
    assert len(manager_agent._workers) == 0


@pytest.mark.asyncio
async def test_manager_agent_creates_task_plan(manager_agent):
    """Test that ManagerAgent creates a proper task plan."""
    # Arrange
    company = "AAPL"
    
    # Act
    plan = manager_agent._create_task_plan(company)
    
    # Assert
    assert isinstance(plan, TaskPlan)
    assert plan.company == company
    assert len(plan.tasks) == 7  # All standard tasks
    assert TaskType.NEWS_ANALYSIS in plan.tasks
    assert TaskType.MARKET_DATA in plan.tasks
    assert TaskType.FINANCIAL_ANALYSIS in plan.tasks
    assert TaskType.SENTIMENT_ANALYSIS in plan.tasks
    assert TaskType.COMPETITOR_ANALYSIS in plan.tasks
    assert TaskType.RISK_ANALYSIS in plan.tasks
    assert TaskType.INVESTMENT_SUMMARY in plan.tasks
    assert plan.metadata["planning_method"] == "standard_sequence"


@pytest.mark.asyncio
async def test_manager_agent_registers_workers(manager_agent):
    """Test that ManagerAgent can register worker agents."""
    # Arrange
    mock_worker = MockWorkerAgent("test_worker")
    task_type = TaskType.NEWS_ANALYSIS
    
    # Act
    manager_agent.register_worker(task_type, mock_worker)
    
    # Assert
    assert task_type in manager_agent._workers
    assert manager_agent._workers[task_type] == mock_worker


@pytest.mark.asyncio
async def test_manager_agent_processes_successful_workers(manager_agent):
    """Test ManagerAgent handling of successful worker responses."""
    # Arrange
    company = "MSFT"
    mock_worker = MockWorkerAgent("test_worker", should_succeed=True)
    manager_agent.register_worker(TaskType.NEWS_ANALYSIS, mock_worker)
    
    # Act
    result = await manager_agent.run(company)
    
    # Assert
    assert isinstance(result, ManagerAgentOutput)
    assert result.company == company
    assert result.task_plan.company == company
    assert TaskType.NEWS_ANALYSIS.value in result.results
    
    # Check that the worker returned success
    news_result = result.results[TaskType.NEWS_ANALYSIS.value]
    assert news_result["status"] == "success"
    assert news_result["data"]["test"] == "data_from_test_worker"
    assert result.metadata["completed_tasks"] == 1
    assert result.metadata["failed_tasks"] == 0


@pytest.mark.asyncio
async def test_manager_agent_handles_failed_workers(manager_agent):
    """Test ManagerAgent handling of failed worker responses."""
    # Arrange
    company = "TSLA"
    mock_worker = MockWorkerAgent("failing_worker", should_succeed=False)
    manager_agent.register_worker(TaskType.MARKET_DATA, mock_worker)
    
    # Act
    result = await manager_agent.run(company)
    
    # Assert
    assert isinstance(result, ManagerAgentOutput)
    assert result.company == company
    assert TaskType.MARKET_DATA.value in result.results
    
    # Check that the worker returned error
    market_result = result.results[TaskType.MARKET_DATA.value]
    assert market_result["status"] == "error"
    assert "Simulated error from failing_worker" in market_result["error"]
    assert result.metadata["completed_tasks"] == 0
    assert result.metadata["failed_tasks"] == 1


@pytest.mark.asyncio
async def test_manager_agent_handles_missing_workers(manager_agent):
    """Test ManagerAgent when no workers are registered - tasks without workers are skipped."""
    # Arrange
    company = "GOOGL"
    
    # Act
    result = await manager_agent.run(company)
    
    # Assert
    assert isinstance(result, ManagerAgentOutput)
    assert result.company == company
    # No tasks should have results since no workers registered - they are skipped
    assert len(result.results) == 0
    
    assert result.metadata["completed_tasks"] == 0
    assert result.metadata["failed_tasks"] == 0  # Skipped tasks don't count as failed
    # Total tasks in plan is still 7
    assert result.metadata["total_tasks"] == 7


@pytest.mark.asyncio
async def test_manager_agent_tracks_execution_metadata(manager_agent):
    """Test that ManagerAgent properly tracks execution metadata."""
    # Arrange
    company = "AMZN"
    mock_worker = MockWorkerAgent("test_worker", should_succeed=True)
    manager_agent.register_worker(TaskType.NEWS_ANALYSIS, mock_worker)
    
    # Act
    result = await manager_agent.run(company)
    
    # Assert
    assert "start_time" in result.metadata
    assert "end_time" in result.metadata
    assert "execution_time_seconds" in result.metadata
    assert result.metadata["execution_time_seconds"] >= 0
    assert result.metadata["agent"] == "manager_agent"
    assert result.metadata["total_tasks"] == 7  # Total tasks in plan
    assert result.metadata["completed_tasks"] == 1
    assert result.metadata["failed_tasks"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
