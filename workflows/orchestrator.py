"""
Workflow Orchestration Engine

Manages execution of research plans with dependency resolution,
parallel execution, error handling, and progress tracking.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable
import uuid
import logging

from agents.manager_agent.manager import BaseWorkerAgent
from agents.research_planner.agent import ExecutionPlan, ExecutionStep, AgentType, Task, TaskStatus, TaskResult
from llm.openrouter_client import OpenRouterClient
from config.settings import get_settings
from memory.research_memory import get_memory_store


logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """Execution step status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """Result of a single execution step."""
    step_id: str
    agent_type: AgentType
    status: StepStatus
    result: Optional[TaskResult] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanExecution:
    """Tracks execution of a complete plan."""
    plan_id: str
    plan: ExecutionPlan
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration_seconds: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Context passed between steps
    shared_context: Dict[str, Any] = field(default_factory=dict)
    
    # Progress tracking
    completed_steps: int = 0
    total_steps: int = 0
    progress_callback: Optional[Callable] = None


class WorkflowOrchestrator:
    """
    Orchestrates execution of research plans.
    
    Features:
    - Dependency resolution with topological sort
    - Parallel execution of independent steps
    - Error handling and retry logic
    - Context passing between steps
    - Progress tracking and callbacks
    - Memory integration for cross-agent knowledge
    """
    
    def __init__(
        self,
        max_parallel: int = 4,
        default_timeout: int = 300,
        max_retries: int = 2
    ):
        self.max_parallel = max_parallel
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.settings = get_settings()
        self.memory_store = get_memory_store()
        
        # Agent instances cache
        self._agent_cache: Dict[AgentType, BaseWorkerAgent] = {}
        
        # Execution tracking
        self._executions: Dict[str, PlanExecution] = {}
        
        # Progress callbacks
        self._progress_callbacks: List[Callable] = []
    
    def register_progress_callback(self, callback: Callable[[PlanExecution, StepResult], None]):
        """Register callback for progress updates."""
        self._progress_callbacks.append(callback)
    
    def _get_agent(self, agent_type: AgentType) -> BaseWorkerAgent:
        """Get or create agent instance."""
        if agent_type not in self._agent_cache:
            self._agent_cache[agent_type] = self._create_agent(agent_type)
        return self._agent_cache[agent_type]
    
    def _create_agent(self, agent_type: AgentType) -> BaseWorkerAgent:
        """Create agent instance based on type."""
        # Import agents dynamically to avoid circular imports
        agent_map = {
            AgentType.FINANCIAL_DOCUMENT: "agents.financial_report_agent.agent.FinancialReportAgent",
            AgentType.SENTIMENT: "agents.sentiment_agent.agent.SentimentAnalysisAgent",
            AgentType.RISK: "agents.risk_agent.agent.RiskAssessmentAgent",
            AgentType.COMPETITIVE: "agents.competitive_intelligence_agent.agent.CompetitiveIntelligenceAgent",
            AgentType.NEWS: "agents.news_agent.agent.NewsIntelligenceAgent",
            AgentType.MARKET_DATA: "agents.market_data_agent.market_agent.MarketAgent",
            AgentType.INVESTMENT_SUMMARY: "agents.investment_summary_agent.agent.InvestmentSummaryAgent",
        }
        
        agent_path = agent_map.get(agent_type)
        if agent_path:
            module_path, class_name = agent_path.rsplit(".", 1)
            module = __import__(module_path, fromlist=[class_name])
            agent_class = getattr(module, class_name)
            return agent_class()
        
        # Fallback to base agent
        from agents.base_worker_agent import BaseWorkerAgent
        return BaseWorkerAgent(agent_type.value)
    
    def _resolve_dependencies(self, plan: ExecutionPlan) -> List[List[ExecutionStep]]:
        """
        Resolve execution order using topological sort.
        Returns list of execution waves (steps that can run in parallel).
        """
        steps = {step.step_id: step for step in plan.steps}
        step_deps = {step.step_id: set(step.dependencies) for step in plan.steps}
        
        # Topological sort to get execution order
        completed = set()
        waves = []
        
        while len(completed) < len(steps):
            # Find steps with all dependencies met
            ready = []
            for step_id, step in steps.items():
                if step_id in completed:
                    continue
                if step_deps[step_id].issubset(completed):
                    ready.append(step)
            
            if not ready:
                # Circular dependency or error
                remaining = set(steps.keys()) - completed
                logger.warning(f"Circular dependency detected for: {remaining}")
                # Add remaining as final wave
                ready = [steps[sid] for sid in remaining]
            
            # Sort by priority
            ready.sort(key=lambda s: s.priority)
            waves.append(ready)
            completed.update(s.step_id for s in ready)
        
        return waves
    
    async def execute_plan(
        self,
        plan: ExecutionPlan,
        progress_callback: Optional[Callable] = None
    ) -> PlanExecution:
        """
        Execute a complete research plan.
        
        Args:
            plan: The execution plan to run
            progress_callback: Optional callback(execution, step_result) for progress
            
        Returns:
            PlanExecution with all results
        """
        execution = PlanExecution(
            plan_id=plan.plan_id,
            plan=plan,
            total_steps=len(plan.steps),
            progress_callback=progress_callback
        )
        
        self._executions[plan.plan_id] = execution
        execution.status = "running"
        execution.started_at = datetime.now()
        
        logger.info(f"Starting execution of plan {plan.plan_id} with {len(plan.steps)} steps")
        
        try:
            # Resolve execution waves
            waves = self._resolve_dependencies(plan)
            
            # Execute each wave
            for wave_idx, wave in enumerate(waves):
                logger.info(f"Executing wave {wave_idx + 1}/{len(waves)}: {len(wave)} steps")
                
                # Execute steps in parallel within wave
                semaphore = asyncio.Semaphore(self.max_parallel)
                
                async def execute_step(step: ExecutionStep) -> StepResult:
                    async with semaphore:
                        return await self._execute_step(step, execution)
                
                # Run all steps in wave concurrently
                tasks = [execute_step(step) for step in wave]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for step, result in zip(wave, results):
                    if isinstance(result, Exception):
                        step_result = StepResult(
                            step_id=step.step_id,
                            agent_type=step.agent_type,
                            status=StepStatus.FAILED,
                            error=str(result)
                        )
                    else:
                        step_result = result
                    
                    execution.step_results[step.step_id] = step_result
                    execution.completed_steps += 1
                    
                    # Update shared context with step results
                    if step_result.result and step_result.result.data:
                        execution.shared_context[f"{step.agent_type.value}_output"] = step_result.result.data
                    
                    # Store in memory for cross-agent access
                    if step_result.result and step_result.result.data:
                        await self.memory_store.store_agent_output(
                            company=plan.company,
                            agent_type=step.agent_type.value,
                            output=step_result.result.data,
                            session_id=execution.plan_id
                        )
                    
                    # Call progress callbacks
                    if progress_callback:
                        await progress_callback(execution, step_result)
                    for cb in self._progress_callbacks:
                        await cb(execution, step_result)
                
                # Check for critical failures
                failed_critical = any(
                    r.status == StepStatus.FAILED and 
                    execution.plan.steps[execution.plan.steps.index(next(s for s in execution.plan.steps if s.step_id == r.step_id))].priority <= 3
                    for r in execution.step_results.values()
                )
                
                if failed_critical:
                    logger.warning(f"Critical step failed in wave {wave_idx + 1}")
                    # Continue with remaining waves but log
        
        except Exception as e:
            logger.error(f"Plan execution failed: {e}")
            execution.error = str(e)
            execution.status = "failed"
        
        finally:
            execution.completed_at = datetime.now()
            if execution.started_at:
                execution.total_duration_seconds = (
                    execution.completed_at - execution.started_at
                ).total_seconds()
            
            if execution.status != "failed":
                execution.status = "completed"
            
            logger.info(
                f"Plan {plan.plan_id} {execution.status} in "
                f"{execution.total_duration_seconds:.1f}s "
                f"({execution.completed_steps}/{execution.total_steps} steps)"
            )
        
        return execution
    
    async def _execute_step(
        self,
        step: ExecutionStep,
        execution: PlanExecution
    ) -> StepResult:
        """Execute a single step."""
        agent = self._get_agent(step.agent_type)
        
        # Prepare task with shared context
        task = step.task
        task.context = {**task.context, **execution.shared_context}
        
        step_result = StepResult(
            step_id=step.step_id,
            agent_type=step.agent_type,
            status=StepStatus.RUNNING,
            started_at=datetime.now()
        )
        
        logger.info(f"Executing step {step.step_id} ({step.agent_type.value})")
        
        # Retry logic
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retry {attempt}/{self.max_retries} for step {step.step_id}")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    agent.run(task.company, task.context),
                    timeout=self.default_timeout
                )
                
                # Convert to TaskResult if needed
                if isinstance(result, dict):
                    task_result = TaskResult(
                        task_id=task.task_id,
                        status=TaskStatus.COMPLETED,
                        data=result,
                        metadata={"agent": step.agent_type.value}
                    )
                else:
                    task_result = result
                
                step_result.status = StepStatus.COMPLETED
                step_result.result = task_result
                step_result.completed_at = datetime.now()
                step_result.duration_seconds = (
                    step_result.completed_at - step_result.started_at
                ).total_seconds()
                
                logger.info(f"Step {step.step_id} completed in {step_result.duration_seconds:.1f}s")
                return step_result
                
            except asyncio.TimeoutError:
                last_error = f"Timeout after {self.default_timeout}s"
                logger.warning(f"Step {step.step_id} timed out (attempt {attempt + 1})")
            except Exception as e:
                last_error = str(e)
                logger.error(f"Step {step.step_id} failed: {e}")
        
        # All retries failed
        step_result.status = StepStatus.FAILED
        step_result.error = last_error
        step_result.completed_at = datetime.now()
        step_result.duration_seconds = (
            step_result.completed_at - step_result.started_at
        ).total_seconds()
        
        return step_result
    
    async def execute_step_by_step_id(
        self,
        plan: ExecutionPlan,
        step_id: str
    ) -> StepResult:
        """Execute a single step by ID (for manual/retry execution)."""
        step = next((s for s in plan.steps if s.step_id == step_id), None)
        if not step:
            raise ValueError(f"Step not found: {step_id}")
        
        execution = PlanExecution(plan_id=plan.plan_id, plan=plan)
        return await self._execute_step(step, execution)
    
    def get_execution(self, plan_id: str) -> Optional[PlanExecution]:
        """Get execution by plan ID."""
        return self._executions.get(plan_id)
    
    def get_step_result(self, plan_id: str, step_id: str) -> Optional[StepResult]:
        """Get result of a specific step."""
        execution = self._executions.get(plan_id)
        if execution:
            return execution.step_results.get(step_id)
        return None
    
    def get_execution_summary(self, plan_id: str) -> Dict[str, Any]:
        """Get summary of plan execution."""
        execution = self._executions.get(plan_id)
        if not execution:
            return {"error": "Execution not found"}
        
        return {
            "plan_id": execution.plan_id,
            "status": execution.status,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "total_duration_seconds": execution.total_duration_seconds,
            "completed_steps": execution.completed_steps,
            "total_steps": execution.total_steps,
            "progress_pct": (execution.completed_steps / execution.total_steps * 100) if execution.total_steps > 0 else 0,
            "step_results": {
                step_id: {
                    "status": result.status.value,
                    "agent_type": result.agent_type.value,
                    "duration_seconds": result.duration_seconds,
                    "error": result.error
                }
                for step_id, result in execution.step_results.items()
            },
            "error": execution.error
        }


# Convenience function
async def execute_research_plan(
    plan: ExecutionPlan,
    progress_callback: Optional[Callable] = None
) -> PlanExecution:
    """Execute a research plan."""
    orchestrator = WorkflowOrchestrator()
    return await orchestrator.execute_plan(plan, progress_callback)