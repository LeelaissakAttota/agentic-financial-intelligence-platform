# Manager Agent Implementation

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any

from .schemas import TaskType, ManagerAgentInput, TaskPlan, WorkerResponse, ManagerAgentOutput
from llm.llm_provider import LLMProvider
from abc import ABC, abstractmethod


class BaseWorkerAgent(ABC):
    """Abstract base class for all worker agents."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    @abstractmethod
    async def run(self, company: str, context: Dict[str, Any]) -> WorkerResponse:
        """Execute the agent's analysis for the given company.

        Args:
            company: Company name or ticker symbol
            context: Results from prerequisite agents (if any)

        Returns:
            WorkerResponse containing the agent's output or error information
        """
        pass


class ManagerAgent:
    """Orchestrator agent that coordinates the financial research workflow."""

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
        self._workers: Dict[TaskType, BaseWorkerAgent] = {}

    def register_worker(self, task_type: TaskType, worker: BaseWorkerAgent) -> None:
        """Register a worker agent for a specific task type.

        Args:
            task_type: The type of task this worker handles
            worker: The worker agent instance
        """
        self._workers[task_type] = worker

    async def run(self, company: str, query: Optional[str] = None) -> ManagerAgentOutput:
        """Execute the full analysis workflow for a company.

        Args:
            company: Company name or ticker symbol to analyze
            query: Optional ticker symbol providing additional context

        Returns:
            ManagerAgentOutput containing the execution plan, results, and metadata
        """
        import logging
        logger = logging.getLogger(__name__)
        start_time = datetime.utcnow()

        # Create execution plan
        task_plan = self._create_task_plan(company, query)

        # Initialize results container
        results: Dict[str, Any] = {}
        execution_metadata = {
            "start_time": start_time.isoformat(),
            "agent": "manager_agent",
            "planning_method": "rule_based",
            "total_tasks": len(task_plan.tasks),
            "completed_tasks": 0,
            "failed_tasks": 0
        }

        # Use query as ticker if provided
        ticker = query if query else None

        # Execute tasks in order (respecting dependencies implicitly through order)
        # Only execute tasks that have registered workers
        for task_type in task_plan.tasks:
            worker = self._workers.get(task_type)

            if worker is None:
                # No worker registered for this task type - skip it
                continue

            try:
                # Execute worker agent with context from previous results
                # In a full implementation, we would pass relevant prior results as context
                context = {"previous_results": results}

                # Add ticker for market agent
                if task_type == TaskType.MARKET_DATA and ticker:
                    context["ticker"] = ticker

                # For MarketAgent, pass ticker as the first argument via context
                if task_type == TaskType.MARKET_DATA and ticker:
                    context["symbol"] = ticker

                # For InvestmentSummaryAgent, provide properly mapped context
                if task_type == TaskType.INVESTMENT_SUMMARY:
                    context = self._map_context_for_investment_summary(results)

                logger.info(f"Starting worker: {worker.agent_name} (task_type: {task_type.value})")
                worker_result = await worker.run(
                    company,
                    context
                )
                logger.info(f"Worker {worker.agent_name} returned: type={type(worker_result)}, is_none={worker_result is None}")

                # DEBUG: Check for None return
                if worker_result is None:
                    logger.error(f"ERROR: Worker {worker.agent_name} returned None!")
                    worker_result = WorkerResponse(
                        status="error",
                        error=f"Worker {worker.agent_name} returned None instead of WorkerResponse"
                    )

                # Store result
                results[task_type.value] = worker_result.dict()

                if worker_result.status == "success":
                    execution_metadata["completed_tasks"] += 1
                else:
                    execution_metadata["failed_tasks"] += 1

            except Exception as e:
                # Handle unexpected exceptions
                error_msg = f"Worker agent {worker.agent_name} failed unexpectedly: {str(e)}"
                logger.error(f"Exception in worker {worker.agent_name}: {e}", exc_info=True)
                results[task_type.value] = WorkerResponse(
                    status="error",
                    error=error_msg
                ).dict()
                execution_metadata["failed_tasks"] += 1

        end_time = datetime.utcnow()
        execution_metadata.update({
            "end_time": end_time.isoformat(),
            "execution_time_seconds": (end_time - start_time).total_seconds()
        })

        # TODO: In a full implementation, we would generate a summary using the Investment Summary Agent
        # For now, we leave summary as None and note it's pending

        return ManagerAgentOutput(
            company=company,
            task_plan=task_plan,
            results=results,
            summary=None,  # Placeholder for future implementation
            metadata=execution_metadata
        )

    def _map_context_for_investment_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Map worker results to the context keys expected by InvestmentSummaryAgent.

        Args:
            results: Dictionary of worker results keyed by task type value

        Returns:
            Context dictionary with keys matching InvestmentSummaryAgent expectations
        """
        context = {"ticker": ""}  # Will be populated from first available result

        # Extract ticker from first available result
        for key in ["news_analysis", "market_data", "financial_analysis",
                    "sentiment_analysis", "competitor_analysis", "risk_analysis"]:
            if key in results:
                data = results[key].get("data", {})
                if data and "ticker" in data:
                    context["ticker"] = data["ticker"]
                    break

        # Map task type values to expected context keys
        mapping = {
            "news_analysis": "news_findings",
            "market_data": "market_findings",
            "financial_analysis": "financial_findings",
            "competitor_analysis": "competitor_findings",
            "sentiment_analysis": "sentiment_findings",
            "risk_analysis": "risk_findings",
        }

        for task_key, context_key in mapping.items():
            if task_key in results:
                worker_response = results[task_key]
                if worker_response.get("status") == "success":
                    context[context_key] = worker_response.get("data") or {}
                else:
                    context[context_key] = {}
            else:
                context[context_key] = {}

        # Add data gaps for any failed or missing agents
        data_gaps = []
        for task_key, context_key in mapping.items():
            if task_key not in results:
                data_gaps.append(f"{context_key}: Worker not registered")
            elif results[task_key].get("status") != "success":
                data_gaps.append(f"{context_key}: {results[task_key].get('error', 'Failed')}")

        if data_gaps:
            context["data_gaps"] = data_gaps

        return context

    def _create_task_plan(self, company: str, query: Optional[str] = None) -> TaskPlan:
        """Create an execution plan based on the company and query.

        In the current implementation, we use a fixed order of tasks.
        In a more advanced implementation, this could use the LLM to dynamically
        determine which tasks are needed and in what order based on the query.

        Args:
            company: Company name or ticker symbol
            query: Optional natural language query

        Returns:
            TaskPlan defining the execution order
        """
        # Standard order of execution for comprehensive analysis
        # Note: Some tasks could run in parallel, but we maintain order for simplicity
        # and to ensure dependencies are met (e.g., sentiment analysis needs news)
        tasks = [
            TaskType.NEWS_ANALYSIS,
            TaskType.MARKET_DATA,
            TaskType.FINANCIAL_ANALYSIS,
            TaskType.SENTIMENT_ANALYSIS,
            TaskType.COMPETITOR_ANALYSIS,
            TaskType.RISK_ANALYSIS,
            TaskType.INVESTMENT_SUMMARY
        ]

        # TODO: In future enhancements, we could:
        # 1. Use LLM to analyze query and determine which tasks are necessary
        # 2. Identify opportunities for parallel execution
        # 3. Adjust order based on dependencies (e.g., sentiment analysis after news)

        return TaskPlan(
            company=company,
            tasks=tasks,
            metadata={
                "planning_method": "standard_sequence",
                "query_provided": query is not None,
                "total_tasks": len(tasks)
            }
        )