"""
Copilot Agent - AI Assistant for Financial Research.

Provides natural language interface for autonomous financial research workflows.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, AsyncGenerator
import logging

from agents.research_planner.agent import (
    ResearchPlannerAgent, ExecutionPlan, ExecutionStep, AgentType, QueryComplexity,
    create_research_plan
)
from workflows.orchestrator import WorkflowOrchestrator, execute_research_plan
from memory.research_memory import get_memory_store, ResearchSession, ResearchMemory, MemoryType
from tools.registry import get_tool_executor, get_tool_registry, ToolCategory
from config.settings import get_settings
from llm.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)


class CopilotMode(str, Enum):
    """Operating modes for the copilot."""
    PLAN_ONLY = "plan_only"          # Only create plan, don't execute
    AUTO_EXECUTE = "auto_execute"    # Create plan and execute automatically
    INTERACTIVE = "interactive"      # Step-by-step with user confirmation
    CONSULTING = "consulting"        # Advisory mode, answer questions


class ConversationRole(str, Enum):
    """Conversation message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


@dataclass
class ConversationMessage:
    """Single message in conversation."""
    role: ConversationRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


@dataclass
class CopilotContext:
    """Context for copilot operations."""
    session_id: str
    user_id: str
    company: Optional[str] = None
    current_plan: Optional[ExecutionPlan] = None
    conversation_history: List[ConversationMessage] = field(default_factory=list)
    active_watchlists: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    mode: CopilotMode = CopilotMode.AUTO_EXECUTE


class CopilotAgent:
    """
    Main Copilot Agent for Financial Research.

    Capabilities:
    - Natural language understanding for research requests
    - Dynamic plan creation and execution
    - Tool orchestration across all agents
    - Memory and context management
    - Conversational interface
    - Proactive monitoring and alerts
    """

    def __init__(self):
        self.settings = get_settings()
        self.llm = OpenRouterClient()
        self.research_planner = ResearchPlannerAgent()
        self.workflow_orchestrator = WorkflowOrchestrator()
        self.memory_store = get_memory_store()
        self.tool_executor = get_tool_executor()
        self.tool_registry = get_tool_registry()

        # Active sessions
        self.sessions: Dict[str, CopilotContext] = {}

        # System prompt
        self.system_prompt = """You are an expert AI Financial Research Copilot. You help users conduct comprehensive financial research through natural language.

Your capabilities:
1. PLANNING: Break down complex research questions into structured execution plans
2. EXECUTION: Orchestrate multiple specialized AI agents (14+ types) to gather and analyze data
3. TOOLS: Access 15+ financial research tools including SEC filings, news, market data, risk analysis, competitive intelligence, portfolio management, pattern detection, and more
4. MEMORY: Persistent cross-session knowledge with 7 memory types
5. MONITORING: Watchlists with 10+ alert condition types and multi-channel notifications
6. REPORTING: Generate 8 types of professional reports in Markdown, HTML, or JSON

Specialized agents available:
- Financial Document Agent: SEC filings, earnings transcripts, RAG analysis
- Sentiment Agent: Multi-source sentiment with source credibility weighting
- Risk Agent: VaR/CVaR, stress testing, multi-category risk assessment
- Competitive Agent: Peer benchmarking and positioning
- News Agent: 6 providers, event detection, entity extraction
- Market Data Agent: Real-time quotes, technicals, fundamentals
- Investment Summary Agent: Multi-agent synthesis and thesis formulation
- Knowledge Graph Agent: Entity relationships, centrality, communities
- Portfolio Agent: Positions, risk metrics, 5 rebalancing strategies
- Patterns Agent: 10 pattern types with backtesting
- Alerts Agent: 30+ alert types, 5 channels, deduplication
- Analytics Agent: Fama-French, Monte Carlo, attribution, scenarios
- Historical Agent: Trend analysis, company evolution, peer comparison
- Cross-Agent Memory: Knowledge sharing, supersession, linking

When users ask for research:
1. Understand their goal and company of interest
2. Create or retrieve an execution plan
3. Execute tools in optimal order (parallel where possible)
4. Synthesize results into actionable insights
5. Offer follow-up: reports, watchlists, deeper analysis

Be concise, cite sources, and always provide confidence levels.
"""

    async def create_session(
        self,
        user_id: str,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> CopilotContext:
        """Create new copilot session."""
        session_id = str(uuid.uuid4())[:8]
        context = CopilotContext(
            session_id=session_id,
            user_id=user_id,
            **(initial_context or {})
        )
        self.sessions[session_id] = context
        return context

    def get_session(self, session_id: str) -> Optional[CopilotContext]:
        """Get existing session."""
        return self.sessions.get(session_id)

    async def process_message(
        self,
        session_id: str,
        message: str,
        stream: bool = False
    ) -> AsyncGenerator[str, None] | str:
        """Process user message and return response."""
        context = self.get_session(session_id)
        if not context:
            return "Session not found. Please create a new session."

        # Add user message to history
        context.conversation_history.append(ConversationMessage(
            role=ConversationRole.USER,
            content=message
        ))

        # Extract company if mentioned
        company = await self._extract_company(message, context)
        if company:
            context.company = company

        # Determine intent
        intent = await self._classify_intent(message, context)

        # Handle based on intent
        if intent == "research_request":
            response = await self._handle_research_request(message, context)
        elif intent == "plan_request":
            response = await self._handle_plan_request(message, context)
        elif intent == "tool_request":
            response = await self._handle_tool_request(message, context)
        elif intent == "report_request":
            response = await self._handle_report_request(message, context)
        elif intent == "watchlist_request":
            response = await self._handle_watchlist_request(message, context)
        elif intent == "memory_request":
            response = await self._handle_memory_request(message, context)
        elif intent == "status_request":
            response = await self._handle_status_request(message, context)
        else:
            response = await self._handle_conversational(message, context)

        # Add assistant response to history
        context.conversation_history.append(ConversationMessage(
            role=ConversationRole.ASSISTANT,
            content=response
        ))

        # Trim history if too long
        if len(context.conversation_history) > 50:
            context.conversation_history = context.conversation_history[-50:]

        if stream:
            # Stream word by word
            async def stream_response():
                for word in response.split():
                    yield word + " "
                    await asyncio.sleep(0.02)
            return stream_response()

        return response

    async def _extract_company(self, message: str, context: CopilotContext) -> Optional[str]:
        """Extract company name/ticker from message."""
        # Check if already in context
        if context.company:
            return context.company

        # Use LLM to extract
        prompt = f"""
Extract the company name or ticker symbol from this message. Return ONLY the company/ticker or "NONE".

Message: {message}

Company/Ticker:
"""
        response = await self.llm.agenerate_json(prompt)
        company = response.get("company", "NONE")
        return company if company != "NONE" else None

    async def _classify_intent(self, message: str, context: CopilotContext) -> str:
        """Classify user intent."""
        prompt = f"""
Classify the user's intent. Return ONLY one of these categories:

1. research_request - Full research analysis request
2. plan_request - Just create a plan, don't execute
3. tool_request - Execute specific tool
4. report_request - Generate a report
5. watchlist_request - Manage watchlists/alerts
6. memory_request - Query or store memory
7. status_request - Check execution status
8. conversational - General chat/question

Context: Company={context.company}, Mode={context.mode.value}
Message: {message}

Intent:
"""
        response = await self.llm.agenerate_json(prompt)
        return response.get("intent", "conversational")

    async def _handle_research_request(self, message: str, context: CopilotContext) -> str:
        """Handle full research request."""
        company = context.company or await self._extract_company(message, context)
        if not company:
            return "Please specify which company you'd like me to research."

        # Create research plan
        plan = await create_research_plan(message, company, {"session_id": context.session_id})

        context.current_plan = plan

        # Execute based on mode
        if context.mode == CopilotMode.PLAN_ONLY:
            return self._format_plan(plan)

        elif context.mode == CopilotMode.INTERACTIVE:
            return f"I've created a research plan for {company} with {len(plan.steps)} steps across {len(set(s.parallel_group for s in plan.steps if s.parallel_group))} parallel groups. Estimated duration: {plan.estimated_total_duration}s. Should I proceed with execution?"

        else:  # AUTO_EXECUTE
            # Store session
            session = await self.memory_store.create_session(
                company=company,
                query=message,
                plan_id=plan.plan_id
            )
            context.session_id = session.session_id

            # Execute plan
            execution = await self.workflow_orchestrator.execute_plan(plan)

            # Store results
            session.status = execution.status
            session.results = execution.get_step_results(execution)
            session.completed_at = execution.completed_at
            session.duration_seconds = execution.total_duration_seconds
            if execution.error:
                session.error = execution.error
            await self.memory_store.store_session(session)

            # Generate summary
            return self._format_execution_results(execution, plan)

    async def _handle_plan_request(self, message: str, context: CopilotContext) -> str:
        """Handle plan-only request."""
        company = context.company or await self._extract_company(message, context)
        if not company:
            return "Please specify which company you'd like me to create a plan for."

        plan = await create_research_plan(message, company, {"session_id": context.session_id})
        context.current_plan = plan
        return self._format_plan(plan)

    def _format_plan(self, plan: ExecutionPlan) -> str:
        """Format execution plan for display."""
        lines = [
            f"## Research Plan: {plan.company}",
            f"**Query**: {plan.query}",
            f"**Complexity**: {plan.complexity.value}",
            f"**Estimated Duration**: {plan.estimated_total_duration}s",
            f"**Steps**: {len(plan.steps)}",
            ""
        ]

        # Group by parallel group
        groups = {}
        for step in plan.steps:
            group = step.parallel_group or "sequential"
            if group not in groups:
                groups[group] = []
            groups[group].append(step)

        for group_name, steps in groups.items():
            lines.append(f"### {group_name.replace('_', ' ').title()}")
            for step in steps:
                deps = f" (depends on: {', '.join(step.dependencies)})" if step.dependencies else ""
                lines.append(f"- **{step.step_id}**: {step.agent_type.value} - ~{step.estimated_duration_seconds}s{deps}")
            lines.append("")

        return "\n".join(lines)

    def _format_execution_results(self, execution, plan: ExecutionPlan) -> str:
        """Format execution results."""
        lines = [
            f"## Research Complete: {plan.company}",
            f"**Status**: {execution.status}",
            f"**Duration**: {execution.total_duration_seconds:.1f}s",
            f"**Steps Completed**: {execution.completed_steps}/{execution.total_steps}",
            ""
        ]

        if execution.error:
            lines.append(f"**Error**: {execution.error}")
            lines.append("")

        # Step results
        lines.append("### Step Results")
        for step_id, result in execution.step_results.items():
            status_icon = "✅" if result.status.value == "completed" else "❌"
            lines.append(f"{status_icon} **{step_id}** ({result.agent_type.value}): {result.duration_seconds:.1f}s")
            if result.error:
                lines.append(f"   Error: {result.error}")

        lines.append("")

        # Generate insights from results
        insights = self._generate_insights(execution, plan)
        if insights:
            lines.append("### Key Insights")
            lines.extend(insights)

        return "\n".join(lines)

    def _generate_insights(self, execution, plan: ExecutionPlan) -> List[str]:
        """Generate insights from execution results."""
        insights = []

        # Check for high-priority findings
        for step_id, result in execution.step_results.items():
            if result.result and isinstance(result.result, dict):
                data = result.result
                # Financial health
                if "financial_metrics" in data:
                    metrics = data["financial_metrics"]
                    if isinstance(metrics, dict):
                        pe = metrics.get("pe_ratio")
                        if pe and pe > 50:
                            insights.append(f"⚠️ High P/E ratio ({pe:.1f}) - potential overvaluation")
                        elif pe and pe < 10:
                            insights.append(f"💡 Low P/E ratio ({pe:.1f}) - potential undervaluation")

                # Risk
                if "risk_scores" in data:
                    risk = data["risk_scores"]
                    if isinstance(risk, dict):
                        overall = risk.get("overall")
                        if overall and overall > 7:
                            insights.append(f"🔴 High overall risk score ({overall}/10)")

                # Sentiment
                if "sentiment_score" in data:
                    sent = data["sentiment_score"]
                    if sent < -0.5:
                        insights.append(f"📉 Negative sentiment ({sent:.2f})")
                    elif sent > 0.5:
                        insights.append(f"📈 Positive sentiment ({sent:.2f})")

                # Patterns
                if "patterns" in data:
                    patterns = data["patterns"]
                    if patterns:
                        insights.append(f"📊 {len(patterns)} technical patterns detected")

        return insights

    async def _handle_tool_request(self, message: str, context: CopilotContext) -> str:
        """Handle specific tool execution request."""
        # Determine which tool to use
        tools = self.tool_registry.get_all_tools()
        tool_names = [t.name for t in tools]

        prompt = f"""
User wants to execute a specific tool. Available tools: {', '.join(tool_names)}

Message: {message}

Return JSON with:
- tool_name: name of tool to execute
- parameters: dict of parameters
- reason: why this tool
"""
        response = await self.llm.agenerate_json(prompt)
        tool_name = response.get("tool_name")
        parameters = response.get("parameters", {})

        if not tool_name or tool_name not in tool_names:
            return f"Could not determine which tool to use. Available: {', '.join(tool_names[:5])}..."

        # Add company context if available
        if context.company and "company" not in parameters:
            parameters["company"] = context.company
        if context.company and "ticker" not in parameters:
            parameters["ticker"] = context.company

        # Execute tool
        execution = await self.tool_executor.execute(tool_name, parameters)
        return self._format_tool_result(execution)

    def _format_tool_result(self, execution) -> str:
        """Format tool execution result."""
        if execution.status == TaskStatus.FAILED:
            return f"❌ Tool **{execution.tool_name}** failed: {execution.error}"

        lines = [
            f"✅ Tool **{execution.tool_name}** completed in {execution.duration_seconds:.1f}s",
            ""
        ]

        if execution.result:
            # Format key results
            if isinstance(execution.result, dict):
                for key, value in list(execution.result.items())[:5]:
                    if isinstance(value, (str, int, float)):
                        lines.append(f"- **{key}**: {value}")
                    elif isinstance(value, list) and len(value) <= 5:
                        lines.append(f"- **{key}**: {', '.join(str(v) for v in value)}")
                    elif isinstance(value, dict):
                        lines.append(f"- **{key}**: {json.dumps(value)[:200]}...")

        return "\n".join(lines)

    async def _handle_report_request(self, message: str, context: CopilotContext) -> str:
        """Handle report generation request."""
        # Determine report type
        report_types = [
            "executive_summary", "analyst_report", "investment_thesis",
            "company_snapshot", "industry_analysis", "daily_briefing",
            "weekly_briefing", "monthly_intelligence"
        ]

        prompt = f"""
User wants to generate a report. Available types: {', '.join(report_types)}

Message: {message}

Return JSON with:
- report_type: one of the above
- company: company name/ticker
- session_id: optional, for using existing research
- format: markdown, html, or json
"""
        response = await self.llm.agenerate_json(prompt)
        report_type = response.get("report_type", "analyst_report")
        company = response.get("company", context.company)
        session_id = response.get("session_id", context.session_id)
        format = response.get("format", "markdown")

        if not company:
            return "Please specify which company for the report."

        # Import report generator
        from reports.generator import generate_report, ReportType, ReportFormat

        try:
            report = await generate_report(
                report_type=ReportType(report_type),
                company=company,
                session_id=session_id if session_id != context.session_id else None,
                format=ReportFormat(format)
            )

            return f"## Report Generated: {report.title}\n\n{report.content[:3000]}...\n\n[Full report available via API]"
        except Exception as e:
            return f"Failed to generate report: {e}"

    async def _handle_watchlist_request(self, message: str, context: CopilotContext) -> str:
        """Handle watchlist/alert management."""
        from watchlists.manager import get_watchlist_manager, WatchlistType

        manager = get_watchlist_manager()

        prompt = f"""
User wants to manage watchlists. Message: {message}

Return JSON with action and parameters:
- action: create, list, get, add_company, remove_company, create_alert, list_alerts
- name, description, type, owner_id, companies, etc. as needed
"""
        response = await self.llm.agenerate_json(prompt)
        action = response.get("action", "list")

        try:
            if action == "create":
                wl_type = WatchlistType(response.get("type", "personal"))
                watchlist = await manager.create_watchlist(
                    name=response.get("name", "New Watchlist"),
                    description=response.get("description", ""),
                    type=wl_type,
                    owner_id=response.get("owner_id", context.user_id),
                    initial_companies=response.get("companies")
                )
                return f"Created watchlist: {watchlist.name} ({watchlist.watchlist_id})"

            elif action == "list":
                watchlists = await manager.list_watchlists(response.get("owner_id", context.user_id))
                if not watchlists:
                    return "No watchlists found."
                lines = ["## Your Watchlists"]
                for wl in watchlists:
                    lines.append(f"- **{wl.name}** ({wl.type.value}) - {len(wl.companies)} companies")
                return "\n".join(lines)

            elif action == "add_company":
                watchlist_id = response.get("watchlist_id")
                company = response.get("company")
                ticker = response.get("ticker")
                success = await manager.add_company(watchlist_id, company, ticker)
                return f"{'Added' if success else 'Failed to add'} {company} to watchlist"

            elif action == "create_alert":
                from notifications.engine import NotificationPriority, NotificationChannel
                watchlist_id = response.get("watchlist_id")
                channels = [NotificationChannel(c) for c in response.get("channels", ["console"])]
                severity = NotificationPriority(response.get("severity", "warning"))

                rule = await manager.add_alert_rule(
                    watchlist_id=watchlist_id,
                    name=response.get("name", "Alert"),
                    description=response.get("description", ""),
                    conditions=response.get("conditions", {}),
                    severity=severity,
                    channels=channels,
                    company=response.get("company"),
                    cooldown_minutes=response.get("cooldown_minutes", 60)
                )
                return f"Created alert rule: {rule.name} ({rule.rule_id})"

            else:
                return f"Action '{action}' not yet implemented in conversational mode."

        except Exception as e:
            return f"Watchlist operation failed: {e}"

    async def _handle_memory_request(self, message: str, context: CopilotContext) -> str:
        """Handle memory query/store request."""
        prompt = f"""
User wants to interact with research memory. Message: {message}

Return JSON with:
- action: store, retrieve, search
- company: company name
- query: search query (for retrieve/search)
- memory_type: session, conclusion, source, agent_output, follow_up, report, insight
- content: content to store (for store)
"""
        response = await self.llm.agenerate_json(prompt)
        action = response.get("action", "retrieve")
        company = response.get("company", context.company)

        if not company:
            return "Please specify a company for memory operations."

        try:
            if action == "store":
                memory_id = await self.memory_store.store_agent_output(
                    company=company,
                    agent_type=response.get("memory_type", "copilot"),
                    output=response.get("content", {}),
                    session_id=context.session_id
                )
                return f"Stored memory: {memory_id}"

            elif action == "retrieve":
                memories = await self.memory_store.retrieve_memories(
                    company=company,
                    query=response.get("query"),
                    limit=response.get("limit", 10)
                )
                if not memories:
                    return "No memories found."
                lines = [f"## Memories for {company}"]
                for mem in memories:
                    lines.append(f"- **{mem.memory_type.value}** ({mem.confidence:.0%}): {str(mem.content)[:200]}")
                return "\n".join(lines)

            else:
                return f"Action '{action}' not yet implemented."

        except Exception as e:
            return f"Memory operation failed: {e}"

    async def _handle_status_request(self, message: str, context: CopilotContext) -> str:
        """Handle status check request."""
        if not context.current_plan:
            return "No active research plan in this session."

        lines = [
            f"## Session Status",
            f"**Session**: {context.session_id}",
            f"**Company**: {context.company or 'Not specified'}",
            f"**Mode**: {context.mode.value}",
            f"**Plan**: {context.current_plan.plan_id if context.current_plan else 'None'}",
            f"**Steps**: {len(context.current_plan.steps) if context.current_plan else 0}",
            ""
        ]

        # Recent tool executions
        executions = self.tool_executor.get_recent_executions(10)
        if executions:
            lines.append("### Recent Tool Executions")
            for exec in executions[:5]:
                status_icon = "✅" if execution.status == TaskStatus.COMPLETED else "❌"
                lines.append(f"{status_icon} {exec.tool_name} - {exec.duration_seconds:.1f}s")

        return "\n".join(lines)

    async def _handle_conversational(self, message: str, context: CopilotContext) -> str:
        """Handle general conversational messages."""
        # Build context for LLM
        history = "\n".join([
            f"{msg.role.value}: {msg.content}"
            for msg in context.conversation_history[-10:]
        ])

        prompt = f"""You are a Financial Research Copilot. Answer the user's question conversationally.

Context:
- Company: {context.company or 'None specified'}
- Active Plan: {context.current_plan.plan_id if context.current_plan else 'None'}
- Mode: {context.mode.value}

Recent Conversation:
{history}

User: {message}

Provide a helpful, concise response. If they ask about financial concepts, explain clearly. If they want research, guide them to make a research request."""

        response = await self.llm.agenerate(prompt)
        return response

    # Public API methods

    async def execute_plan(self, session_id: str, plan: ExecutionPlan) -> Any:
        """Execute a research plan."""
        context = self.get_session(session_id)
        if not context:
            raise ValueError("Session not found")

        execution = await self.workflow_orchestrator.execute_plan(plan)
        return execution

    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools as schemas."""
        return self.tool_registry.get_tool_schemas()

    async def create_watchlist(
        self,
        session_id: str,
        name: str,
        companies: List[str],
        watchlist_type: str = "personal"
    ) -> Any:
        """Create a watchlist for the session."""
        from watchlists.manager import get_watchlist_manager, WatchlistType
        manager = get_watchlist_manager()
        context = self.get_session(session_id)
        if not context:
            raise ValueError("Session not found")

        wl_type = WatchlistType(watchlist_type)
        return await manager.create_watchlist(
            name=name,
            description=f"Watchlist for {context.company}",
            type=wl_type,
            owner_id=context.user_id,
            initial_companies=companies
        )

    async def generate_report(
        self,
        session_id: str,
        report_type: str,
        format: str = "markdown"
    ) -> Any:
        """Generate a report from session research."""
        from reports.generator import generate_report, ReportType, ReportFormat
        context = self.get_session(session_id)
        if not context:
            raise ValueError("Session not found")

        return await generate_report(
            report_type=ReportType(report_type),
            company=context.company,
            session_id=context.session_id,
            format=ReportFormat(format)
        )


# Global instance
_copilot_agent: Optional[CopilotAgent] = None


def get_copilot_agent() -> CopilotAgent:
    """Get global copilot agent instance."""
    global _copilot_agent
    if _copilot_agent is None:
        _copilot_agent = CopilotAgent()
    return _copilot_agent