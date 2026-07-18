"""
AI Planning Agent - Task decomposition and execution planning.

Breaks down high-level research goals into executable task plans
with dependencies, resource estimation, and optimization.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import logging

from agents.research_planner.agent import (
    ResearchPlannerAgent, ExecutionPlan, ExecutionStep, AgentType, QueryComplexity
)
from llm.openrouter_client import OpenRouterClient
from config.settings import get_settings

logger = logging.getLogger(__name__)


class TaskPriority(str, Enum):
    """Task priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


@dataclass
class PlanningTask:
    """Individual task in a plan."""
    task_id: str
    name: str
    description: str
    agent_type: AgentType
    dependencies: List[str] = field(default_factory=list)
    parallel_group: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    estimated_duration_seconds: int = 30
    estimated_cost_usd: float = 0.0
    required_inputs: Dict[str, Any] = field(default_factory=dict)
    expected_outputs: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class ExecutionPlan:
    """Complete execution plan with metadata."""
    plan_id: str
    goal: str
    company: str
    complexity: QueryComplexity
    tasks: List[PlanningTask]
    created_at: datetime = field(default_factory=datetime.now)
    estimated_total_duration: int = 0
    estimated_total_cost: float = 0.0
    parallel_groups: Dict[str, List[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_ready_tasks(self, completed_task_ids: Set[str]) -> List[PlanningTask]:
        """Get tasks whose dependencies are all satisfied."""
        ready = []
        for task in self.tasks:
            if task.status != TaskStatus.PENDING:
                continue
            if all(dep in completed_task_ids for dep in task.dependencies):
                ready.append(task)
        return ready

    def get_parallel_waves(self) -> List[List[PlanningTask]]:
        """Get execution waves (tasks that can run in parallel)."""
        waves = []
        remaining = {t.task_id: t for t in self.tasks}
        completed = set()

        while remaining:
            wave = []
            for task_id, task in list(remaining.items()):
                if all(dep in completed for dep in task.dependencies):
                    wave.append(task)
            if not wave:
                # Circular dependency or error - add remaining as final wave
                wave = list(remaining.values())
            for task in wave:
                completed.add(task.task_id)
                del remaining[task.task_id]
            waves.append(wave)

        return waves


class PlanningAgent:
    """AI-driven planning agent for research workflows."""

    def __init__(self):
        self.settings = get_settings()
        self.llm = OpenRouterClient()
        self.research_planner = ResearchPlannerAgent()

        # Agent capability mapping
        self.agent_capabilities = {
            AgentType.FINANCIAL_DOCUMENT: {
                "description": "SEC filings, earnings transcripts, financial reports analysis",
                "keywords": ["financial", "earnings", "10-k", "10-q", "sec", "filing", "report", "revenue", "profit", "balance sheet", "cash flow"],
                "outputs": ["financial_metrics", "ratio_analysis", "filing_insights"],
                "avg_duration": 60,
                "avg_cost": 0.05
            },
            AgentType.SENTIMENT: {
                "description": "Market sentiment from news, social media, analyst opinions",
                "keywords": ["sentiment", "bullish", "bearish", "opinion", "analyst", "social", "twitter", "reddit", "mood"],
                "outputs": ["sentiment_score", "sentiment_distribution", "key_drivers"],
                "avg_duration": 30,
                "avg_cost": 0.02
            },
            AgentType.RISK: {
                "description": "Multi-category risk assessment (market, credit, operational, liquidity)",
                "keywords": ["risk", "var", "cvar", "volatility", "drawdown", "credit", "liquidity", "operational", "stress test"],
                "outputs": ["risk_scores", "var_cvar", "risk_factors", "mitigation"],
                "avg_duration": 45,
                "avg_cost": 0.03
            },
            AgentType.COMPETITIVE: {
                "description": "Peer comparison and competitive positioning",
                "keywords": ["competitor", "peer", "comparison", "benchmark", "market share", "positioning", "advantage"],
                "outputs": ["peer_comparison", "competitive_advantages", "market_position"],
                "avg_duration": 45,
                "avg_cost": 0.03
            },
            AgentType.NEWS: {
                "description": "Financial news aggregation, events, entity extraction",
                "keywords": ["news", "event", "announcement", "merger", "acquisition", "lawsuit", "regulation", "product launch"],
                "outputs": ["news_summary", "key_events", "entity_mentions", "sentiment_trends"],
                "avg_duration": 30,
                "avg_cost": 0.02
            },
            AgentType.MARKET_DATA: {
                "description": "Real-time market data, technical indicators, fundamentals",
                "keywords": ["price", "technical", "rsi", "macd", "moving average", "volume", "quote", "fundamental", "valuation"],
                "outputs": ["technical_analysis", "fundamental_valuation", "market_trends"],
                "avg_duration": 15,
                "avg_cost": 0.01
            },
            AgentType.INVESTMENT_SUMMARY: {
                "description": "Multi-agent synthesis and investment thesis formulation",
                "keywords": ["thesis", "recommendation", "target price", "catalyst", "investment", "synthesis"],
                "outputs": ["investment_thesis", "price_target", "catalyst_timeline", "recommendation"],
                "avg_duration": 30,
                "avg_cost": 0.03
            },
            AgentType.KNOWLEDGE_GRAPH: {
                "description": "Entity relationships, graph traversal, centrality analysis",
                "keywords": ["relationship", "network", "connection", "entity", "graph", "centrality", "community"],
                "outputs": ["entity_relationships", "centrality_scores", "communities", "paths"],
                "avg_duration": 30,
                "avg_cost": 0.02
            },
            AgentType.PORTFOLIO: {
                "description": "Position management, risk metrics, rebalancing strategies",
                "keywords": ["portfolio", "position", "allocation", "rebalance", "weight", "var", "sharpe", "drawdown"],
                "outputs": ["portfolio_metrics", "risk_analysis", "rebalancing_recommendations"],
                "avg_duration": 30,
                "avg_cost": 0.02
            },
            AgentType.PATTERNS: {
                "description": "Pattern detection (trend, seasonal, support/resistance, regime change)",
                "keywords": ["pattern", "trend", "seasonal", "support", "resistance", "breakout", "regime", "cycle", "anomaly"],
                "outputs": ["detected_patterns", "pattern_signals", "backtest_results"],
                "avg_duration": 30,
                "avg_cost": 0.02
            },
            AgentType.ALERTS: {
                "description": "Alert rules, notifications, monitoring",
                "keywords": ["alert", "monitor", "notify", "threshold", "trigger", "watchlist"],
                "outputs": ["alert_rules", "triggered_alerts", "notification_config"],
                "avg_duration": 15,
                "avg_cost": 0.01
            },
            AgentType.ANALYTICS: {
                "description": "Advanced analytics (Fama-French, Monte Carlo, attribution, scenarios)",
                "keywords": ["factor", "fama", "french", "monte carlo", "attribution", "scenario", "correlation", "rolling"],
                "outputs": ["factor_exposure", "monte_carlo_results", "attribution", "scenario_analysis"],
                "avg_duration": 60,
                "avg_cost": 0.05
            },
            AgentType.HISTORICAL: {
                "description": "Historical trends, company evolution, peer comparison over time",
                "keywords": ["historical", "trend", "evolution", "trajectory", "peer", "benchmark", "time series", "mann-kendall"],
                "outputs": ["trend_analysis", "evolution_tracking", "peer_comparison"],
                "avg_duration": 45,
                "avg_cost": 0.03
            },
            AgentType.CROSS_AGENT_MEMORY: {
                "description": "Cross-agent knowledge sharing, fact supersession, memory linking",
                "keywords": ["memory", "knowledge", "recall", "previous", "history", "context", "supersede"],
                "outputs": ["relevant_memories", "knowledge_links", "context_summary"],
                "avg_duration": 10,
                "avg_cost": 0.005
            }
        }

    async def create_plan(
        self,
        goal: str,
        company: str,
        context: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> ExecutionPlan:
        """Create detailed execution plan from high-level goal."""
        # Use research planner for initial complexity analysis and agent selection
        research_plan = await self.research_planner.create_plan(goal, company, context)

        # Enhance with detailed task planning
        tasks = self._create_detailed_tasks(research_plan, context, constraints)

        # Calculate estimates
        total_duration = sum(t.estimated_duration_seconds for t in tasks)
        total_cost = sum(t.estimated_cost_usd for t in tasks)

        # Build parallel groups
        parallel_groups = {}
        for task in tasks:
            if task.parallel_group:
                if task.parallel_group not in parallel_groups:
                    parallel_groups[task.parallel_group] = []
                parallel_groups[task.parallel_group].append(task.task_id)

        plan = ExecutionPlan(
            plan_id=str(uuid.uuid4())[:8],
            goal=goal,
            company=company,
            complexity=research_plan.complexity,
            tasks=tasks,
            estimated_total_duration=total_duration,
            estimated_total_cost=total_cost,
            parallel_groups=parallel_groups,
            metadata={
                "context": context or {},
                "constraints": constraints or {},
                "research_plan_id": research_plan.plan_id
            }
        )

        return plan

    def _create_detailed_tasks(
        self,
        research_plan,
        context: Optional[Dict[str, Any]],
        constraints: Optional[Dict[str, Any]]
    ) -> List[PlanningTask]:
        """Create detailed planning tasks from research plan steps."""
        tasks = []
        step_id_map = {}

        # First pass: create tasks
        for step in research_plan.steps:
            capability = self.agent_capabilities.get(step.agent_type, {})
            task = PlanningTask(
                task_id=step.step_id,
                name=f"{step.agent_type.value.replace('_', ' ').title()} Analysis",
                description=f"Execute {step.agent_type.value} analysis for {research_plan.company}",
                agent_type=step.agent_type,
                dependencies=step.dependencies.copy(),
                parallel_group=step.parallel_group,
                priority=self._map_priority(step.priority),
                estimated_duration_seconds=capability.get("avg_duration", step.estimated_duration_seconds),
                estimated_cost_usd=capability.get("avg_cost", 0.02),
                required_inputs={
                    "company": research_plan.company,
                    "query": research_plan.query,
                    "context": context or {}
                },
                expected_outputs=capability.get("outputs", [])
            )
            tasks.append(task)
            step_id_map[step.step_id] = task

        # Second pass: resolve dependencies and add cross-agent memory tasks
        if len(tasks) > 3:
            # Add cross-agent memory task at the beginning
            memory_task = PlanningTask(
                task_id="step_0_cross_agent_memory",
                name="Cross-Agent Memory Retrieval",
                description="Retrieve relevant prior research and knowledge",
                agent_type=AgentType.CROSS_AGENT_MEMORY,
                dependencies=[],
                parallel_group="data_collection",
                priority=TaskPriority.HIGH,
                estimated_duration_seconds=10,
                estimated_cost_usd=0.005,
                required_inputs={"company": research_plan.company, "query": research_plan.query},
                expected_outputs=["relevant_memories", "knowledge_links", "context_summary"]
            )
            tasks.insert(0, memory_task)
            # Add dependency on memory task for first wave
            for task in tasks[1:]:
                if task.parallel_group == "data_collection" and not task.dependencies:
                    task.dependencies.append(memory_task.task_id)

        return tasks

    def _map_priority(self, priority: int) -> TaskPriority:
        """Map numeric priority to enum."""
        if priority <= 2:
            return TaskPriority.CRITICAL
        elif priority <= 4:
            return TaskPriority.HIGH
        elif priority <= 6:
            return TaskPriority.MEDIUM
        return TaskPriority.LOW

    async def optimize_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Optimize plan for cost, time, or quality."""
        # Merge redundant tasks
        # Reorder for better parallelism
        # Apply constraints (budget, time limits)
        return plan

    async def estimate_resources(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Estimate resources needed for plan."""
        return {
            "total_duration_seconds": plan.estimated_total_duration,
            "parallel_duration_seconds": self._estimate_parallel_duration(plan),
            "total_cost_usd": plan.estimated_total_cost,
            "llm_calls": len(plan.tasks),
            "tokens_estimate": sum(t.estimated_duration_seconds * 100 for t in plan.tasks),
            "agents_used": list(set(t.agent_type.value for t in plan.tasks))
        }

    def _estimate_parallel_duration(self, plan: ExecutionPlan) -> int:
        """Estimate duration with parallel execution."""
        waves = plan.get_parallel_waves() if hasattr(plan, 'get_parallel_waves') else []
        total = 0
        for wave in waves:
            if wave:
                total += max(t.estimated_duration_seconds for t in wave)
        return total


# Convenience function
async def create_research_plan(
    goal: str,
    company: str,
    context: Optional[Dict[str, Any]] = None,
    constraints: Optional[Dict[str, Any]] = None
) -> ExecutionPlan:
    """Create a research execution plan."""
    planner = PlanningAgent()
    return await planner.create_plan(goal, company, context, constraints)