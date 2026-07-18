"""
Tool System - Unified interface for all financial research tools.

Provides consistent tool interface, execution tracking, and result formatting.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import logging

from planning.agent import Task, TaskResult, TaskStatus
from agents.financial_document_agent.agent import FinancialDocumentAgent
from agents.sentiment_analysis_agent.agent import SentimentAnalysisAgent
from agents.risk_assessment_agent.agent import RiskAssessmentAgent
from agents.competitive_intelligence_agent.agent import CompetitiveIntelligenceAgent
from agents.news_agent.agent import NewsAgent
from agents.market_data_agent.market_agent import MarketDataAgent
from agents.investment_summary_agent.agent import InvestmentSummaryAgent
from data.knowledge_graph.graph import KnowledgeGraph
from data.portfolio.portfolio import PortfolioManager
from data.patterns.patterns import PatternDetector
from data.alerts.alerts import AlertEngine
from data.analytics.analytics import AnalyticsEngine
from data.intelligence.historical import HistoricalIntelligence
from data.memory.cross_agent_memory import CrossAgentMemory

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """Categories of available tools."""
    FINANCIAL_DOCS = "financial_documents"
    SENTIMENT = "sentiment"
    RISK = "risk"
    COMPETITIVE = "competitive"
    NEWS = "news"
    MARKET_DATA = "market_data"
    INVESTMENT = "investment"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    PORTFOLIO = "portfolio"
    PATTERNS = "patterns"
    ALERTS = "alerts"
    ANALYTICS = "analytics"
    HISTORICAL = "historical"
    MEMORY = "memory"


@dataclass
class ToolDefinition:
    """Definition of an available tool."""
    name: str
    category: ToolCategory
    description: str
    parameters: Dict[str, Any]
    required_params: List[str]
    returns: Dict[str, Any]
    estimated_duration_seconds: int = 30
    estimated_cost_usd: float = 0.02
    agent_type: Optional[str] = None


@dataclass
class ToolExecution:
    """Record of a tool execution."""
    execution_id: str
    tool_name: str
    category: ToolCategory
    parameters: Dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0


class ToolRegistry:
    """Registry of all available tools."""

    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self._register_core_tools()

    def _register_core_tools(self):
        """Register all core financial research tools."""
        tools = [
            ToolDefinition(
                name="analyze_financial_documents",
                category=ToolCategory.FINANCIAL_DOCS,
                description="Analyze SEC filings (10-K, 10-Q), earnings transcripts, and financial reports",
                parameters={
                    "company": {"type": "string", "description": "Company name or ticker"},
                    "questions": {"type": "array", "items": {"type": "string"}, "description": "Specific questions to answer"},
                    "filing_types": {"type": "array", "items": {"type": "string"}, "description": "Types of filings to analyze"},
                    "fiscal_year": {"type": "integer", "description": "Fiscal year to analyze"},
                    "fiscal_quarter": {"type": "integer", "description": "Fiscal quarter to analyze"}
                },
                required_params=["company"],
                returns={"financial_metrics": "object", "ratio_analysis": "object", "findings": "array", "citations": "array"},
                estimated_duration_seconds=60,
                estimated_cost_usd=0.05,
                agent_type="financial_document"
            ),
            ToolDefinition(
                name="analyze_sentiment",
                category=ToolCategory.SENTIMENT,
                description="Analyze market sentiment from news, social media, and analyst opinions",
                parameters={
                    "company": {"type": "string", "description": "Company name or ticker"},
                    "timeframe_days": {"type": "integer", "description": "Timeframe in days", "default": 30},
                    "sources": {"type": "array", "items": {"type": "string"}, "description": "Sentiment sources"}
                },
                required_params=["company"],
                returns={"sentiment_score": "number", "distribution": "object", "key_drivers": "array", "confidence": "string"},
                estimated_duration_seconds=30,
                estimated_cost_usd=0.02,
                agent_type="sentiment"
            ),
            ToolDefinition(
                name="assess_risk",
                category=ToolCategory.RISK,
                description="Multi-category risk assessment (market, credit, operational, liquidity)",
                parameters={
                    "company": {"type": "string", "description": "Company name or ticker"},
                    "risk_categories": {"type": "array", "items": {"type": "string"}, "description": "Risk categories to assess"},
                    "portfolio_context": {"type": "object", "description": "Portfolio context for risk"}
                },
                required_params=["company"],
                returns={"risk_scores": "object", "var_cvar": "object", "risk_factors": "array", "mitigation": "array"},
                estimated_duration_seconds=45,
                estimated_cost_usd=0.03,
                agent_type="risk"
            ),
            ToolDefinition(
                name="analyze_competitive_position",
                category=ToolCategory.COMPETITIVE,
                description="Peer comparison and competitive positioning analysis",
                parameters={
                    "company": {"type": "string", "description": "Company name or ticker"},
                    "peers": {"type": "array", "items": {"type": "string"}, "description": "Specific peers to compare"},
                    "metrics": {"type": "array", "items": {"type": "string"}, "description": "Metrics to compare"}
                },
                required_params=["company"],
                returns={"peer_comparison": "object", "advantages": "array", "disadvantages": "array", "market_position": "string"},
                estimated_duration_seconds=45,
                estimated_cost_usd=0.03,
                agent_type="competitive"
            ),
            ToolDefinition(
                name="get_financial_news",
                category=ToolCategory.NEWS,
                description="Aggregated financial news with sentiment, events, and entity extraction",
                parameters={
                    "company": {"type": "string", "description": "Company name or ticker"},
                    "timeframe_days": {"type": "integer", "description": "Timeframe in days", "default": 7},
                    "categories": {"type": "array", "items": {"type": "string"}, "description": "News categories"}
                },
                required_params=["company"],
                returns={"articles": "array", "sentiment_trends": "object", "key_events": "array", "entities": "array"},
                estimated_duration_seconds=30,
                estimated_cost_usd=0.02,
                agent_type="news"
            ),
            ToolDefinition(
                name="get_market_data",
                category=ToolCategory.MARKET_DATA,
                description="Real-time market data, technical indicators, and fundamentals",
                parameters={
                    "ticker": {"type": "string", "description": "Stock ticker symbol"},
                    "timeframe": {"type": "string", "description": "Timeframe (1d, 1w, 1m, 3m, 1y)", "default": "1m"},
                    "indicators": {"type": "array", "items": {"type": "string"}, "description": "Technical indicators to calculate"}
                },
                required_params=["ticker"],
                returns={"quote": "object", "technical_indicators": "object", "fundamentals": "object", "historical": "array"},
                estimated_duration_seconds=15,
                estimated_cost_usd=0.01,
                agent_type="market_data"
            ),
            ToolDefinition(
                name="generate_investment_thesis",
                category=ToolCategory.INVESTMENT,
                description="Synthesize multi-agent insights into investment thesis",
                parameters={
                    "company": {"type": "string", "description": "Company name or ticker"},
                    "context": {"type": "object", "description": "Context from other agents"},
                    "thesis_type": {"type": "string", "description": "Type of thesis (bull, bear, neutral)"}
                },
                required_params=["company", "context"],
                returns={"thesis": "string", "price_target": "number", "catalysts": "array", "recommendation": "string", "confidence": "string"},
                estimated_duration_seconds=30,
                estimated_cost_usd=0.03,
                agent_type="investment_summary"
            ),
            ToolDefinition(
                name="query_knowledge_graph",
                category=ToolCategory.KNOWLEDGE_GRAPH,
                description="Query entity relationships and graph analytics",
                parameters={
                    "entity": {"type": "string", "description": "Entity to query"},
                    "query_type": {"type": "string", "description": "Type of query (neighbors, paths, centrality, community)"},
                    "depth": {"type": "integer", "description": "Traversal depth", "default": 2}
                },
                required_params=["entity", "query_type"],
                returns={"entities": "array", "relationships": "array", "metrics": "object"},
                estimated_duration_seconds=30,
                estimated_cost_usd=0.02,
                agent_type="knowledge_graph"
            ),
            ToolDefinition(
                name="manage_portfolio",
                category=ToolCategory.PORTFOLIO,
                description="Portfolio management, risk metrics, and rebalancing",
                parameters={
                    "action": {"type": "string", "description": "Action (analyze, rebalance, add_position, risk_metrics)"},
                    "portfolio_id": {"type": "string", "description": "Portfolio identifier"},
                    "parameters": {"type": "object", "description": "Action-specific parameters"}
                },
                required_params=["action", "portfolio_id"],
                returns={"metrics": "object", "recommendations": "array", "positions": "array"},
                estimated_duration_seconds=30,
                estimated_cost_usd=0.02,
                agent_type="portfolio"
            ),
            ToolDefinition(
                name="detect_patterns",
                category=ToolCategory.PATTERNS,
                description="Detect technical and statistical patterns in price data",
                parameters={
                    "ticker": {"type": "string", "description": "Stock ticker"},
                    "pattern_types": {"type": "array", "items": {"type": "string"}, "description": "Pattern types to detect"},
                    "lookback_days": {"type": "integer", "description": "Lookback period", "default": 252}
                },
                required_params=["ticker"],
                returns={"patterns": "array", "signals": "array", "backtest": "object"},
                estimated_duration_seconds=30,
                estimated_cost_usd=0.02,
                agent_type="patterns"
            ),
            ToolDefinition(
                name="configure_alerts",
                category=ToolCategory.ALERTS,
                description="Create and manage alert rules for monitoring",
                parameters={
                    "action": {"type": "string", "description": "Action (create, update, delete, list, evaluate)"},
                    "watchlist_id": {"type": "string", "description": "Watchlist identifier"},
                    "rule": {"type": "object", "description": "Alert rule configuration"}
                },
                required_params=["action"],
                returns={"rules": "array", "triggered": "array", "status": "string"},
                estimated_duration_seconds=15,
                estimated_cost_usd=0.01,
                agent_type="alerts"
            ),
            ToolDefinition(
                name="run_analytics",
                category=ToolCategory.ANALYTICS,
                description="Advanced analytics: Fama-French, Monte Carlo, attribution, scenarios",
                parameters={
                    "analysis_type": {"type": "string", "description": "Type (factor, monte_carlo, attribution, scenario, correlation)"},
                    "parameters": {"type": "object", "description": "Analysis-specific parameters"},
                    "portfolio_id": {"type": "string", "description": "Portfolio identifier (optional)"}
                },
                required_params=["analysis_type", "parameters"],
                returns={"results": "object", "visualization_data": "object", "interpretation": "string"},
                estimated_duration_seconds=60,
                estimated_cost_usd=0.05,
                agent_type="analytics"
            ),
            ToolDefinition(
                name="analyze_historical_trends",
                category=ToolCategory.HISTORICAL,
                description="Historical trend analysis and company evolution tracking",
                parameters={
                    "company": {"type": "string", "description": "Company name or ticker"},
                    "analysis_type": {"type": "string", "description": "Type (trend, evolution, peer_comparison)"},
                    "metrics": {"type": "array", "items": {"type": "string"}, "description": "Metrics to analyze"},
                    "lookback_years": {"type": "integer", "description": "Years to look back", "default": 5}
                },
                required_params=["company", "analysis_type"],
                returns={"trends": "array", "evolution": "object", "peer_comparison": "object"},
                estimated_duration_seconds=45,
                estimated_cost_usd=0.03,
                agent_type="historical"
            ),
            ToolDefinition(
                name="access_memory",
                category=ToolCategory.MEMORY,
                description="Cross-agent memory retrieval and knowledge sharing",
                parameters={
                    "action": {"type": "string", "description": "Action (store, retrieve, link, supersede)"},
                    "company": {"type": "string", "description": "Company context"},
                    "memory_type": {"type": "string", "description": "Type of memory"},
                    "content": {"type": "object", "description": "Memory content"},
                    "query": {"type": "string", "description": "Query for retrieval"}
                },
                required_params=["action"],
                returns={"memories": "array", "links": "array", "context": "string"},
                estimated_duration_seconds=10,
                estimated_cost_usd=0.005,
                agent_type="cross_agent_memory"
            )
        ]

        for tool in tools:
            self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get tool definition by name."""
        return self.tools.get(name)

    def get_tools_by_category(self, category: ToolCategory) -> List[ToolDefinition]:
        """Get all tools in a category."""
        return [t for t in self.tools.values() if t.category == category]

    def get_all_tools(self) -> List[ToolDefinition]:
        """Get all tool definitions."""
        return list(self.tools.values())

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAI-compatible function schemas."""
        schemas = []
        for tool in self.tools.values():
            schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": tool.parameters,
                        "required": tool.required_params
                    }
                }
            }
            schemas.append(schema)
        return schemas


class ToolExecutor:
    """Executes tools and tracks execution."""

    def __init__(self):
        self.registry = ToolRegistry()
        self.executions: Dict[str, ToolExecution] = {}
        self._agents: Dict[str, Any] = {}

    def _get_agent(self, agent_type: str):
        """Get or create agent instance."""
        if agent_type in self._agents:
            return self._agents[agent_type]

        agent_map = {
            "financial_document": FinancialDocumentAgent(),
            "sentiment": SentimentAnalysisAgent(),
            "risk": RiskAssessmentAgent(),
            "competitive": CompetitiveIntelligenceAgent(),
            "news": NewsAgent(),
            "market_data": MarketDataAgent(),
            "investment_summary": InvestmentSummaryAgent(),
            "knowledge_graph": KnowledgeGraph(),
            "portfolio": PortfolioManager(),
            "patterns": PatternDetector(),
            "alerts": AlertEngine(),
            "analytics": AnalyticsEngine(),
            "historical": HistoricalIntelligence(),
            "cross_agent_memory": CrossAgentMemory()
        }

        agent = agent_map.get(agent_type)
        if agent:
            self._agents[agent_type] = agent
        return agent

    async def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolExecution:
        """Execute a tool and return result."""
        tool = self.registry.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        execution = ToolExecution(
            execution_id=str(uuid.uuid4())[:8],
            tool_name=tool_name,
            category=tool.category,
            parameters=parameters,
            started_at=datetime.now()
        )
        self.executions[execution.execution_id] = execution

        try:
            # Map tool to agent method
            result = await self._dispatch_tool(tool, parameters, context)

            execution.completed_at = datetime.now()
            execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
            execution.status = TaskStatus.COMPLETED
            execution.result = result

            logger.info(f"Tool {tool_name} executed successfully in {execution.duration_seconds:.2f}s")
            return execution

        except Exception as e:
            execution.completed_at = datetime.now()
            execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
            execution.status = TaskStatus.FAILED
            execution.error = str(e)
            logger.error(f"Tool {tool_name} failed: {e}")
            return execution

    async def _dispatch_tool(
        self,
        tool: ToolDefinition,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Dispatch tool to appropriate agent."""
        agent = self._get_agent(tool.agent_type) if tool.agent_type else None

        if not agent:
            raise ValueError(f"No agent found for tool: {tool.name}")

        # Execute based on tool category
        if tool.category == ToolCategory.FINANCIAL_DOCS:
            task = Task(
                task_id=tool.name,
                task_type="financial_analysis",
                company=parameters.get("company", ""),
                context=parameters
            )
            result = await agent.run(parameters.get("company", ""), task.context)
            return result

        elif tool.category == ToolCategory.SENTIMENT:
            result = await agent.run(parameters.get("company", ""), parameters)
            return result

        elif tool.category == ToolCategory.RISK:
            result = await agent.run(parameters.get("company", ""), parameters)
            return result

        elif tool.category == ToolCategory.COMPETITIVE:
            result = await agent.run(parameters.get("company", ""), parameters)
            return result

        elif tool.category == ToolCategory.NEWS:
            result = await agent.run(parameters.get("company", ""), parameters)
            return result

        elif tool.category == ToolCategory.MARKET_DATA:
            # Market agent needs ticker
            ticker = parameters.get("ticker", "")
            result = await agent.run(ticker, parameters)
            return result

        elif tool.category == ToolCategory.INVESTMENT:
            result = await agent.run(parameters.get("company", ""), parameters.get("context", {}))
            return result

        elif tool.category == ToolCategory.KNOWLEDGE_GRAPH:
            # Knowledge graph queries
            query_type = parameters.get("query_type", "neighbors")
            if query_type == "neighbors":
                result = await agent.get_neighbors(parameters.get("entity", ""), parameters.get("depth", 2))
            elif query_type == "shortest_path":
                result = await agent.get_shortest_path(
                    parameters.get("source", ""),
                    parameters.get("target", "")
                )
            elif query_type == "centrality":
                result = await agent.calculate_centrality()
            elif query_type == "community":
                result = await agent.detect_communities()
            else:
                result = {"error": f"Unknown query type: {query_type}"}
            return result

        elif tool.category == ToolCategory.PORTFOLIO:
            action = parameters.get("action", "analyze")
            portfolio_id = parameters.get("portfolio_id", "default")
            params = parameters.get("parameters", {})

            if action == "analyze":
                result = await agent.analyze_portfolio(portfolio_id)
            elif action == "rebalance":
                result = await agent.rebalance_portfolio(portfolio_id, params.get("strategy", "equal_weight"))
            elif action == "risk_metrics":
                result = await agent.calculate_risk_metrics(portfolio_id)
            elif action == "add_position":
                result = await agent.add_position(portfolio_id, params)
            else:
                result = {"error": f"Unknown portfolio action: {action}"}
            return result

        elif tool.category == ToolCategory.PATTERNS:
            result = await agent.detect_patterns(
                parameters.get("ticker", ""),
                parameters.get("lookback_days", 252)
            )
            return result

        elif tool.category == ToolCategory.ALERTS:
            action = parameters.get("action", "list")
            watchlist_id = parameters.get("watchlist_id", "default")

            if action == "create":
                result = await agent.add_alert_rule(watchlist_id, parameters.get("rule", {}))
            elif action == "evaluate":
                result = await agent.evaluate_alerts(watchlist_id)
            else:
                result = await agent.list_alerts(watchlist_id)
            return result

        elif tool.category == ToolCategory.ANALYTICS:
            analysis_type = parameters.get("analysis_type", "factor")
            params = parameters.get("parameters", {})

            if analysis_type == "factor":
                result = await agent.run_factor_analysis(params)
            elif analysis_type == "monte_carlo":
                result = await agent.run_monte_carlo(params)
            elif analysis_type == "attribution":
                result = await agent.run_attribution_analysis(params)
            elif analysis_type == "scenario":
                result = await agent.run_scenario_analysis(params)
            elif analysis_type == "correlation":
                result = await agent.calculate_rolling_correlation(params)
            else:
                result = {"error": f"Unknown analysis type: {analysis_type}"}
            return result

        elif tool.category == ToolCategory.HISTORICAL:
            result = await agent.analyze_company_evolution(
                parameters.get("company", ""),
                parameters.get("metrics", []),
                parameters.get("lookback_years", 5)
            )
            return result

        elif tool.category == ToolCategory.MEMORY:
            action = parameters.get("action", "retrieve")

            if action == "retrieve":
                result = await agent.retrieve_memories(
                    parameters.get("company", ""),
                    parameters.get("query", "")
                )
            elif action == "store":
                result = await agent.store_memory(
                    parameters.get("company", ""),
                    parameters.get("memory_type", "insight"),
                    parameters.get("content", {}),
                    parameters.get("source_agent", "copilot")
                )
            else:
                result = {"error": f"Unknown memory action: {action}"}
            return result

        else:
            raise ValueError(f"Unknown tool category: {tool.category}")

    def get_execution(self, execution_id: str) -> Optional[ToolExecution]:
        """Get execution record."""
        return self.executions.get(execution_id)

    def get_recent_executions(self, limit: int = 20) -> List[ToolExecution]:
        """Get recent executions."""
        sorted_exec = sorted(
            self.executions.values(),
            key=lambda e: e.started_at,
            reverse=True
        )
        return sorted_exec[:limit]


# Global instances
_tool_registry: Optional[ToolRegistry] = None
_tool_executor: Optional[ToolExecutor] = None


def get_tool_registry() -> ToolRegistry:
    """Get global tool registry."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry


def get_tool_executor() -> ToolExecutor:
    """Get global tool executor."""
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolExecutor()
    return _tool_executor