"""
Research Planner Agent

LLM-driven dynamic task planning based on query complexity.
Decomposes research requests into agent execution plans with dependencies.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid

from agents.manager_agent.manager import BaseWorkerAgent
from llm.openrouter_client import OpenRouterClient
from config.settings import get_settings


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Task:
    """Research task definition."""
    task_id: str
    task_type: str
    company: str
    query: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Result of a task execution."""
    task_id: str
    status: TaskStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class QueryComplexity(Enum):
    """Query complexity levels."""
    SIMPLE = "simple"           # Single agent, direct answer
    MODERATE = "moderate"       # 2-3 agents, some dependencies
    COMPLEX = "complex"         # 4+ agents, complex dependencies
    COMPREHENSIVE = "comprehensive"  # Full pipeline, deep research


class AgentType(Enum):
    """Available agent types."""
    FINANCIAL_DOCUMENT = "financial_document"
    SENTIMENT = "sentiment"
    RISK = "risk"
    COMPETITIVE = "competitive"
    NEWS = "news"
    MARKET_DATA = "market_data"
    INVESTMENT_SUMMARY = "investment_summary"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    PORTFOLIO = "portfolio"
    PATTERNS = "patterns"
    ALERTS = "alerts"
    ANALYTICS = "analytics"
    HISTORICAL = "historical"
    CROSS_AGENT_MEMORY = "cross_agent_memory"


@dataclass
class ExecutionStep:
    """Single step in execution plan."""
    step_id: str
    agent_type: AgentType
    task: Task
    dependencies: List[str] = field(default_factory=list)  # step_ids this depends on
    parallel_group: Optional[str] = None  # For parallel execution
    estimated_duration_seconds: int = 30
    priority: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """Complete execution plan for a research query."""
    plan_id: str
    query: str
    company: str
    complexity: QueryComplexity
    steps: List[ExecutionStep]
    estimated_total_duration: int
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResearchPlannerAgent(BaseWorkerAgent):
    """
    LLM-driven research planner that:
    1. Analyzes query complexity
    2. Determines required agents
    3. Creates dependency-aware execution plan
    4. Supports parallel execution groups
    """

    def __init__(self):
        super().__init__("research_planner")
        self.llm = OpenRouterClient()
        self.settings = get_settings()

        # Agent capabilities mapping
        self.agent_capabilities = {
            AgentType.FINANCIAL_DOCUMENT: {
                "description": "SEC filings, earnings transcripts, financial reports analysis",
                "keywords": ["financial", "earnings", "10-k", "10-q", "sec", "filing", "report", "revenue", "profit", "balance sheet", "cash flow"],
                "outputs": ["financial_metrics", "ratio_analysis", "filing_insights"]
            },
            AgentType.SENTIMENT: {
                "description": "Market sentiment from news, social media, analyst opinions",
                "keywords": ["sentiment", "bullish", "bearish", "opinion", "analyst", "social", "twitter", "reddit", "mood"],
                "outputs": ["sentiment_score", "sentiment_distribution", "key_drivers"]
            },
            AgentType.RISK: {
                "description": "Multi-category risk assessment (market, credit, operational, liquidity)",
                "keywords": ["risk", "var", "cvar", "volatility", "drawdown", "credit", "liquidity", "operational", "stress test"],
                "outputs": ["risk_scores", "var_cvar", "risk_factors", "mitigation"]
            },
            AgentType.COMPETITIVE: {
                "description": "Peer comparison and competitive positioning",
                "keywords": ["competitor", "peer", "comparison", "benchmark", "market share", "positioning", "advantage"],
                "outputs": ["peer_comparison", "competitive_advantages", "market_position"]
            },
            AgentType.NEWS: {
                "description": "Financial news aggregation, events, entity extraction",
                "keywords": ["news", "event", "announcement", "merger", "acquisition", "lawsuit", "regulation", "product launch"],
                "outputs": ["news_summary", "key_events", "entity_mentions", "sentiment_trends"]
            },
            AgentType.MARKET_DATA: {
                "description": "Real-time market data, technical indicators, fundamentals",
                "keywords": ["price", "technical", "rsi", "macd", "moving average", "volume", "quote", "fundamental", "valuation"],
                "outputs": ["technical_analysis", "fundamental_valuation", "market_trends"]
            },
            AgentType.INVESTMENT_SUMMARY: {
                "description": "Multi-agent synthesis and investment thesis formulation",
                "keywords": ["thesis", "recommendation", "target price", "catalyst", "investment", "synthesis"],
                "outputs": ["investment_thesis", "price_target", "catalyst_timeline", "recommendation"]
            },
            AgentType.KNOWLEDGE_GRAPH: {
                "description": "Entity relationships, graph traversal, centrality analysis",
                "keywords": ["relationship", "network", "connection", "entity", "graph", "centrality", "community"],
                "outputs": ["entity_relationships", "centrality_scores", "communities", "paths"]
            },
            AgentType.PORTFOLIO: {
                "description": "Position management, risk metrics, rebalancing strategies",
                "keywords": ["portfolio", "position", "allocation", "rebalance", "weight", "var", "sharpe", "drawdown"],
                "outputs": ["portfolio_metrics", "risk_analysis", "rebalancing_recommendations"]
            },
            AgentType.PATTERNS: {
                "description": "Pattern detection (trend, seasonal, support/resistance, regime change)",
                "keywords": ["pattern", "trend", "seasonal", "support", "resistance", "breakout", "regime", "cycle", "anomaly"],
                "outputs": ["detected_patterns", "pattern_signals", "backtest_results"]
            },
            AgentType.ALERTS: {
                "description": "Alert rules, notifications, monitoring",
                "keywords": ["alert", "monitor", "notify", "threshold", "trigger", "watchlist"],
                "outputs": ["alert_rules", "triggered_alerts", "notification_config"]
            },
            AgentType.ANALYTICS: {
                "description": "Advanced analytics (Fama-French, Monte Carlo, attribution, scenarios)",
                "keywords": ["factor", "fama", "french", "monte carlo", "attribution", "scenario", "correlation", "rolling"],
                "outputs": ["factor_exposure", "monte_carlo_results", "attribution", "scenario_analysis"]
            },
            AgentType.HISTORICAL: {
                "description": "Historical trends, company evolution, peer comparison over time",
                "keywords": ["historical", "trend", "evolution", "trajectory", "peer", "benchmark", "time series", "mann-kendall"],
                "outputs": ["trend_analysis", "evolution_tracking", "peer_comparison"]
            },
            AgentType.CROSS_AGENT_MEMORY: {
                "description": "Cross-agent knowledge sharing, fact supersession, memory linking",
                "keywords": ["memory", "knowledge", "recall", "previous", "history", "context", "supersede"],
                "outputs": ["relevant_memories", "knowledge_links", "context_summary"]
            }
        }

    async def _analyze_query_complexity(self, query: str, company: str) -> QueryComplexity:
        """Analyze query complexity using LLM."""
        prompt = f"""
Analyze the complexity of this financial research query:

Company: {company}
Query: {query}

Classify as one of:
- SIMPLE: Single aspect, direct answer (e.g., "What is NVDA's current P/E ratio?")
- MODERATE: 2-3 aspects, some synthesis (e.g., "Compare NVDA vs AMD financials and sentiment")
- COMPLEX: Multiple aspects, deep analysis (e.g., "Full investment thesis for NVDA with risk assessment")
- COMPREHENSIVE: Full research pipeline, all agents (e.g., "Complete equity research report for NVDA")

Consider:
1. Number of distinct analytical dimensions
2. Need for synthesis across agents
3. Depth of analysis required
4. Time horizon (current vs historical vs forward-looking)

Return ONLY the classification: SIMPLE, MODERATE, COMPLEX, or COMPREHENSIVE
"""
        response = await self.llm.agenerate_json(prompt)
        complexity_str = response.get("classification", "MODERATE").upper()
        return QueryComplexity(complexity_str.lower())

    async def _determine_required_agents(self, query: str, company: str, complexity: QueryComplexity) -> List[AgentType]:
        """Determine which agents are needed based on query and complexity."""
        # Use LLM to select agents
        agent_descriptions = "\n".join([
            f"- {agent.value}: {cap['description']}"
            for agent, cap in self.agent_capabilities.items()
        ])

        prompt = f"""
Given this research query, select the MOST RELEVANT agents from the available list.

Company: {company}
Query: {query}
Complexity: {complexity.value}

Available agents:
{agent_descriptions}

Select agents that are DIRECTLY RELEVANT to answering this query.
For SIMPLE: 1-2 agents
For MODERATE: 2-4 agents
For COMPLEX: 4-6 agents
For COMPREHENSIVE: 6+ agents (full pipeline)

Return ONLY a JSON array of agent type strings, e.g., ["financial_document", "sentiment", "risk"]
"""
        response = await self.llm.agenerate_json(prompt)
        agent_strings = response.get("agents", [])

        # Map strings to AgentType enum
        selected = []
        for agent_str in agent_strings:
            try:
                selected.append(AgentType(agent_str))
            except ValueError:
                pass

        # Ensure minimum agents for complexity
        min_agents = {
            QueryComplexity.SIMPLE: 1,
            QueryComplexity.MODERATE: 2,
            QueryComplexity.COMPLEX: 4,
            QueryComplexity.COMPREHENSIVE: 6
        }

        if len(selected) < min_agents[complexity]:
            # Add default agents
            defaults = [
                AgentType.FINANCIAL_DOCUMENT,
                AgentType.SENTIMENT,
                AgentType.RISK,
                AgentType.NEWS,
                AgentType.MARKET_DATA,
                AgentType.INVESTMENT_SUMMARY,
                AgentType.COMPETITIVE,
                AgentType.PATTERNS
            ]
            for default in defaults:
                if default not in selected and len(selected) < min_agents[complexity]:
                    selected.append(default)

        return selected[:min(len(selected), 12)]  # Cap at 12

    def _create_execution_steps(self, agents: List[AgentType], query: str, company: str) -> List[ExecutionStep]:
        """Create execution steps with dependencies."""
        steps = []

        # Define agent dependencies (which agents should run before others)
        dependency_map = {
            AgentType.FINANCIAL_DOCUMENT: [],
            AgentType.NEWS: [],
            AgentType.MARKET_DATA: [],
            AgentType.SENTIMENT: [AgentType.NEWS],  # Sentiment needs news
            AgentType.RISK: [AgentType.FINANCIAL_DOCUMENT, AgentType.MARKET_DATA],  # Risk needs financials + market
            AgentType.COMPETITIVE: [AgentType.FINANCIAL_DOCUMENT, AgentType.MARKET_DATA],
            AgentType.PATTERNS: [AgentType.MARKET_DATA],
            AgentType.ANALYTICS: [AgentType.FINANCIAL_DOCUMENT, AgentType.MARKET_DATA],
            AgentType.HISTORICAL: [AgentType.FINANCIAL_DOCUMENT],
            AgentType.KNOWLEDGE_GRAPH: [AgentType.FINANCIAL_DOCUMENT, AgentType.NEWS],
            AgentType.PORTFOLIO: [AgentType.FINANCIAL_DOCUMENT, AgentType.RISK, AgentType.MARKET_DATA],
            AgentType.ALERTS: [AgentType.NEWS, AgentType.MARKET_DATA],
            AgentType.CROSS_AGENT_MEMORY: [],  # Can run anytime
            AgentType.INVESTMENT_SUMMARY: [  # Synthesis runs last
                AgentType.FINANCIAL_DOCUMENT,
                AgentType.SENTIMENT,
                AgentType.RISK,
                AgentType.COMPETITIVE,
                AgentType.NEWS,
                AgentType.MARKET_DATA
            ]
        }

        step_id_map = {}
        for i, agent in enumerate(agents):
            step_id = f"step_{i}_{agent.value}"
            step_id_map[agent] = step_id

            deps = [step_id_map[dep] for dep in dependency_map.get(agent, []) if dep in step_id_map]

            # Group parallel agents (those with no mutual dependencies)
            parallel_group = None
            if agent in [AgentType.FINANCIAL_DOCUMENT, AgentType.NEWS, AgentType.MARKET_DATA]:
                parallel_group = "data_collection"
            elif agent in [AgentType.SENTIMENT, AgentType.PATTERNS]:
                parallel_group = "analysis_1"
            elif agent in [AgentType.RISK, AgentType.COMPETITIVE]:
                parallel_group = "analysis_2"

            step = ExecutionStep(
                step_id=step_id,
                agent_type=agent,
                task=Task(
                    task_id=step_id,
                    task_type=agent.value,
                    company=company,
                    query=query,
                    context={}
                ),
                dependencies=deps,
                parallel_group=parallel_group,
                estimated_duration_seconds=self._estimate_duration(agent),
                priority=self._get_priority(agent)
            )
            steps.append(step)

        return steps

    def _estimate_duration(self, agent: AgentType) -> int:
        """Estimate duration in seconds for each agent."""
        durations = {
            AgentType.FINANCIAL_DOCUMENT: 60,
            AgentType.NEWS: 30,
            AgentType.MARKET_DATA: 15,
            AgentType.SENTIMENT: 30,
            AgentType.RISK: 45,
            AgentType.COMPETITIVE: 45,
            AgentType.PATTERNS: 30,
            AgentType.ANALYTICS: 60,
            AgentType.HISTORICAL: 45,
            AgentType.KNOWLEDGE_GRAPH: 30,
            AgentType.PORTFOLIO: 30,
            AgentType.ALERTS: 15,
            AgentType.CROSS_AGENT_MEMORY: 10,
            AgentType.INVESTMENT_SUMMARY: 30
        }
        return durations.get(agent, 30)

    def _get_priority(self, agent: AgentType) -> int:
        """Get priority (lower = higher priority)."""
        priorities = {
            AgentType.FINANCIAL_DOCUMENT: 1,
            AgentType.NEWS: 1,
            AgentType.MARKET_DATA: 1,
            AgentType.SENTIMENT: 2,
            AgentType.PATTERNS: 2,
            AgentType.RISK: 3,
            AgentType.COMPETITIVE: 3,
            AgentType.ANALYTICS: 4,
            AgentType.HISTORICAL: 4,
            AgentType.KNOWLEDGE_GRAPH: 4,
            AgentType.PORTFOLIO: 5,
            AgentType.ALERTS: 5,
            AgentType.CROSS_AGENT_MEMORY: 1,
            AgentType.INVESTMENT_SUMMARY: 10  # Always last
        }
        return priorities.get(agent, 5)

    async def create_plan(self, query: str, company: str, context: Optional[Dict] = None) -> ExecutionPlan:
        """Create complete execution plan for a research query."""
        # Analyze complexity
        complexity = await self._analyze_query_complexity(query, company)

        # Determine required agents
        agents = await self._determine_required_agents(query, company, complexity)

        # Create execution steps
        steps = self._create_execution_steps(agents, query, company)

        # Estimate total duration (considering parallel execution)
        parallel_groups = {}
        for step in steps:
            if step.parallel_group:
                if step.parallel_group not in parallel_groups:
                    parallel_groups[step.parallel_group] = []
                parallel_groups[step.parallel_group].append(step.estimated_duration_seconds)

        # Total = sequential + max of each parallel group
        sequential_duration = sum(
            s.estimated_duration_seconds for s in steps if not s.parallel_group
        )
        parallel_duration = sum(
            max(durations) for durations in parallel_groups.values()
        )
        total_duration = sequential_duration + parallel_duration

        plan = ExecutionPlan(
            plan_id=str(uuid.uuid4())[:8],
            query=query,
            company=company,
            complexity=complexity,
            steps=steps,
            estimated_total_duration=total_duration,
            metadata=context or {}
        )

        return plan

    async def run(self, company: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute planning for a research request."""
        query = context.get("query", f"Analyze {company}")

        plan = await self.create_plan(query, company, context)

        return {
            "plan_id": plan.plan_id,
            "company": company,
            "query": query,
            "complexity": plan.complexity.value,
            "estimated_duration_seconds": plan.estimated_total_duration,
            "steps": [
                {
                    "step_id": step.step_id,
                    "agent_type": step.agent_type.value,
                    "dependencies": step.dependencies,
                    "parallel_group": step.parallel_group,
                    "estimated_duration_seconds": step.estimated_duration_seconds,
                    "priority": step.priority
                }
                for step in plan.steps
            ],
            "metadata": plan.metadata
        }


# Convenience function
async def create_research_plan(query: str, company: str, context: Optional[Dict] = None) -> ExecutionPlan:
    """Create a research execution plan."""
    planner = ResearchPlannerAgent()
    return await planner.create_plan(query, company, context)