"""
Copilot Dashboard - Streamlit component for AI Copilot interface.

Provides chat interface, active agent monitoring, workflow visualization,
decision confidence, and cost tracking.
"""
import streamlit as st
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

# Import copilot components
from copilot.agent import (
    CopilotAgent, CopilotContext, CopilotMode, ConversationMessage, ConversationRole,
    get_copilot_agent
)
from agents.research_planner.agent import ExecutionPlan, ExecutionStep, AgentType, QueryComplexity
from api.copilot_endpoints import SessionCreateRequest


def init_session_state():
    """Initialize Streamlit session state for copilot."""
    if "copilot_initialized" not in st.session_state:
        st.session_state.copilot_initialized = True
        st.session_state.current_session_id = None
        st.session_state.current_company = None
        st.session_state.messages = []
        st.session_state.agent_status = {}
        st.session_state.workflow_status = None
        st.session_state.decision_confidence = 0.0
        st.session_state.total_tokens = 0
        st.session_state.total_cost = 0.0
        st.session_state.active_plan = None
        st.session_state.tool_history = []


def render_copilot_header():
    """Render copilot dashboard header."""
    st.markdown("""
    <style>
    .copilot-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .metric-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .agent-active {
        background: #dcfce7;
        border-left: 4px solid #22c55e;
        padding: 0.5rem 1rem;
        margin: 0.25rem 0;
        border-radius: 4px;
    }
    .agent-pending {
        background: #fef9c3;
        border-left: 4px solid #eab308;
        padding: 0.5rem 1rem;
        margin: 0.25rem 0;
        border-radius: 4px;
    }
    .agent-completed {
        background: #f1f5f9;
        border-left: 4px solid #64748b;
        padding: 0.5rem 1rem;
        margin: 0.25rem 0;
        border-radius: 4px;
    }
    .confidence-high { color: #22c55e; font-weight: bold; }
    .confidence-medium { color: #eab308; font-weight: bold; }
    .confidence-low { color: #ef4444; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="copilot-header">
        <h1>🤖 AI Financial Research Copilot</h1>
        <p>Conversational interface for autonomous financial research</p>
    </div>
    """, unsafe_allow_html=True)


def render_session_selector(copilot: CopilotAgent):
    """Render session management controls."""
    st.sidebar.header("📋 Session Management")

    # Create new session
    with st.sidebar.expander("➕ New Session", expanded=st.session_state.current_session_id is None):
        user_id = st.text_input("User ID", value="analyst_001")
        company = st.text_input("Company (optional)", placeholder="e.g., NVIDIA, AAPL, MSFT")
        mode = st.selectbox(
            "Mode",
            options=[m.value for m in CopilotMode],
            index=0,
            format_func=lambda x: x.replace("_", " ").title()
        )

        if st.button("Create Session", type="primary", use_container_width=True):
            context = asyncio.run(copilot.create_session(user_id, {
                "company": company if company else None,
                "mode": CopilotMode(mode)
            }))
            st.session_state.current_session_id = context.session_id
            st.session_state.current_company = company
            st.session_state.messages = []
            st.rerun()

    # Current session info
    if st.session_state.current_session_id:
        st.sidebar.success(f"Active: {st.session_state.current_session_id}")
        if st.session_state.current_company:
            st.sidebar.info(f"Company: {st.session_state.current_company}")

        if st.sidebar.button("End Session", use_container_width=True):
            asyncio.run(copilot.orchestrator.close_session(st.session_state.current_session_id))
            st.session_state.current_session_id = None
            st.session_state.current_company = None
            st.session_state.messages = []
            st.rerun()

    # List existing sessions
    with st.sidebar.expander("📂 Previous Sessions"):
        sessions = list(copilot.sessions.values())
        if sessions:
            for session in sessions[-10:]:
                status_emoji = "🟢" if session.status.value == "active" else "🔴"
                if st.button(f"{status_emoji} {session.session_id} - {session.company or 'General'}",
                            key=f"session_{session.session_id}", use_container_width=True):
                    st.session_state.current_session_id = session.session_id
                    st.session_state.current_company = session.company
                    st.session_state.messages = session.conversation_history
                    st.rerun()
        else:
            st.info("No previous sessions")


def render_chat_interface(copilot: CopilotAgent):
    """Render main chat interface."""
    if not st.session_state.current_session_id:
        st.info("👈 Create a session from the sidebar to start")
        return

    st.subheader(f"💬 Chat - {st.session_state.current_company or 'General'}")

    # Display messages
    for msg in st.session_state.messages:
        with st.chat_message(msg.role.value):
            st.markdown(msg.content)
            if msg.metadata:
                with st.expander("Details"):
                    st.json(msg.metadata)

    # Chat input
    prompt = st.chat_input("Ask about financial research, request analysis, or start a workflow...")
    if prompt:
        # Add user message
        user_msg = ConversationMessage(
            role=ConversationRole.USER,
            content=prompt
        )
        st.session_state.messages.append(user_msg)

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = asyncio.run(copilot.process_message(
                    st.session_state.current_session_id, prompt
                ))

            assistant_msg = ConversationMessage(
                role=ConversationRole.ASSISTANT,
                content=response
            )
            st.session_state.messages.append(assistant_msg)
            st.markdown(response)


def render_agent_monitor():
    """Render active agent monitoring panel."""
    st.sidebar.header("🔍 Active Agents")

    if not st.session_state.current_session_id:
        st.sidebar.info("No active session")
        return

    # Simulate agent status (in real implementation, get from workflow orchestrator)
    agents = [
        ("Financial Documents", "financial_document", "completed"),
        ("News Intelligence", "news", "completed"),
        ("Market Data", "market_data", "completed"),
        ("Sentiment Analysis", "sentiment", "running"),
        ("Risk Assessment", "risk", "pending"),
        ("Competitive Intel", "competitive", "pending"),
        ("Patterns", "patterns", "pending"),
        ("Investment Summary", "investment_summary", "pending"),
    ]

    for name, agent_type, status in agents:
        css_class = f"agent-{status}"
        st.sidebar.markdown(f"""
        <div class="{css_class}">
            <strong>{name}</strong><br>
            <small>Status: {status.title()}</small>
        </div>
        """, unsafe_allow_html=True)


def render_workflow_visualization():
    """Render workflow execution visualization."""
    if not st.session_state.current_session_id or not st.session_state.active_plan:
        return

    st.subheader("📊 Workflow Execution")

    plan = st.session_state.active_plan

    # Progress bar
    total = len(plan.steps)
    completed = sum(1 for s in plan.steps if s.status.value == "completed")
    progress = completed / total if total > 0 else 0

    st.progress(progress, text=f"Progress: {completed}/{total} steps completed")

    # Step timeline
    for i, step in enumerate(plan.steps):
        status_icons = {
            "pending": "⏳",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌",
            "skipped": "⏭️"
        }
        icon = status_icons.get(step.status.value, "❓")

        col1, col2, col3 = st.columns([0.5, 3, 1])
        with col1:
            st.write(f"{icon}")
        with col2:
            st.write(f"**{step.agent_type.value.replace('_', ' ').title()}**")
            if step.dependencies:
                st.caption(f"Depends on: {', '.join(step.dependencies)}")
        with col3:
            if step.status.value == "completed" and step.result:
                st.caption(f"{step.result.get('duration_seconds', 0):.1f}s")

    # Parallel group visualization
    if plan.parallel_groups:
        st.write("**Parallel Groups:**")
        for group, step_ids in plan.parallel_groups.items():
            st.write(f"🔀 {group}: {', '.join(step_ids)}")


def render_decision_confidence():
    """Render decision confidence and explanation panel."""
    st.subheader("🎯 Decision Confidence")

    # Mock data - in real implementation, get from decision history
    confidence_data = {
        "overall": 0.87,
        "factors": [
            ("Data Quality", 0.92, "High-quality SEC filings and real-time market data"),
            ("Analyst Consensus", 0.85, "15 analysts with narrow price target range"),
            ("Risk Factors", 0.78, "Moderate market risk, low credit risk"),
            ("Catalyst Certainty", 0.80, "Earnings date confirmed, guidance likely")
        ],
        "alternatives": [
            ("Bull Case", 0.15, "Strong beat on AI demand, raise guidance"),
            ("Base Case", 0.65, "In-line results, steady guidance"),
            ("Bear Case", 0.20, "Weak demand signal, lower guidance")
        ]
    }

    # Overall confidence
    conf = confidence_data["overall"]
    conf_class = "confidence-high" if conf > 0.8 else "confidence-medium" if conf > 0.6 else "confidence-low"
    st.markdown(f'<div class="{conf_class}" style="font-size: 2rem;">{conf:.0%} Confidence</div>', unsafe_allow_html=True)

    st.markdown("### Contributing Factors")
    for name, score, desc in confidence_data["factors"]:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.progress(score, text=f"{name}: {desc}")
        with col2:
            cls = "confidence-high" if score > 0.8 else "confidence-medium" if score > 0.6 else "confidence-low"
            st.markdown(f'<span class="{cls}">{score:.0%}</span>', unsafe_allow_html=True)

    st.markdown("### Alternative Scenarios")
    for name, prob, desc in confidence_data["alternatives"]:
        st.write(f"**{name}** ({prob:.0%}): {desc}")


def render_explainability_panel():
    """Render explainability panel with evidence and sources."""
    st.subheader("📚 Evidence & Sources")

    # Evidence table
    evidence = [
        {"Source": "NVDA 10-K FY2024", "Type": "SEC Filing", "Relevance": "High", "Excerpt": "Revenue grew 126% YoY driven by Data Center segment"},
        {"Source": "NVDA Q4 Earnings Call", "Type": "Transcript", "Relevance": "High", "Excerpt": "CEO: 'AI demand continues to exceed supply'"},
        {"Source": "Bloomberg Analyst Survey", "Type": "Analyst", "Relevance": "Medium", "Excerpt": "Mean PT: $875, Range: $750-$1,100"},
        {"Source": "Yahoo Finance News", "Type": "News", "Relevance": "Medium", "Excerpt": "New Blackwell GPU architecture announced"},
        {"Source": "Risk Metrics Calculation", "Type": "Internal", "Relevance": "High", "Excerpt": "VaR 95%: -3.2%, CVaR: -4.8%"},
    ]

    for item in evidence:
        with st.expander(f"{item['Source']} ({item['Type']}) - Relevance: {item['Relevance']}"):
            st.write(f"**Excerpt:** {item['Excerpt']}")

    st.markdown("### Risk Assessment")
    risks = [
        ("Market Risk", "High", "Beta 1.8, correlated with NASDAQ"),
        ("Concentration Risk", "Medium", "80% revenue from Data Center"),
        ("Competition Risk", "Medium", "AMD MI300, custom ASICs from hyperscalers"),
        ("Regulatory Risk", "Low", "Export controls manageable"),
        ("Key Person Risk", "Low", "Strong management bench"),
    ]

    for risk, level, desc in risks:
        color = "🔴" if level == "High" else "🟡" if level == "Medium" else "🟢"
        st.write(f"{color} **{risk}** ({level}): {desc}")


def render_token_cost_tracker():
    """Render token usage and cost tracking."""
    st.sidebar.header("💰 Usage Tracking")

    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("Tokens Used", f"{st.session_state.total_tokens:,}")
    with col2:
        st.metric("Cost (USD)", f"${st.session_state.total_cost:.4f}")

    # Detailed breakdown
    with st.sidebar.expander("📊 Breakdown"):
        st.write("**By Agent:**")
        agents_cost = {
            "Financial Docs": 0.045,
            "News": 0.018,
            "Market Data": 0.012,
            "Sentiment": 0.015,
            "Risk": 0.028,
            "Competitive": 0.022,
            "Patterns": 0.018,
            "Investment Summary": 0.035
        }
        for agent, cost in agents_cost.items():
            st.write(f"  {agent}: ${cost:.4f}")

        st.write("**By Model:**")
        st.write("  Claude 3.5 Sonnet: $0.12")
        st.write("  GPT-4o: $0.08")
        st.write("  DeepSeek: $0.02")


def render_copilot_dashboard():
    """Main dashboard render function."""
    init_session_state()
    render_copilot_header()

    # Initialize copilot
    copilot = get_copilot_agent()

    # Sidebar
    render_session_selector(copilot)
    render_agent_monitor()
    render_token_cost_tracker()

    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💬 Chat", "📊 Workflow", "🎯 Decisions", "📚 Evidence", "⚙️ Tools"
    ])

    with tab1:
        render_chat_interface(copilot)

    with tab2:
        render_workflow_visualization()

    with tab3:
        render_decision_confidence()

    with tab4:
        render_explainability_panel()

    with tab5:
        render_tools_panel(copilot)


def render_tools_panel(copilot: CopilotAgent):
    """Render available tools panel."""
    st.subheader("🔧 Available Tools")

    registry = get_tool_registry()
    tools = registry.get_all_tools()

    # Group by category
    categories = {}
    for tool in tools:
        if tool.category not in categories:
            categories[tool.category] = []
        categories[tool.category].append(tool)

    for category, cat_tools in categories.items():
        with st.expander(f"{category.value.replace('_', ' ').title()} ({len(cat_tools)})"):
            for tool in cat_tools:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{tool.name}**")
                    st.caption(tool.description)
                with col2:
                    if st.button("Run", key=f"run_{tool.name}"):
                        # Show parameter form
                        st.session_state[f"show_params_{tool.name}"] = True

                # Parameter form
                if st.session_state.get(f"show_params_{tool.name}", False):
                    with st.form(f"params_{tool.name}"):
                        params = {}
                        for param_name, param_info in tool.parameters.items():
                            if param_info.get("type") == "string":
                                params[param_name] = st.text_input(param_name, key=f"{tool.name}_{param_name}")
                            elif param_info.get("type") == "integer":
                                params[param_name] = st.number_input(param_name, key=f"{tool.name}_{param_name}")
                            elif param_info.get("type") == "array":
                                params[param_name] = st.text_area(param_name + " (JSON array)", key=f"{tool.name}_{param_name}")
                        if st.form_submit_button("Execute"):
                            # Execute tool
                            executor = get_tool_executor()
                            execution = asyncio.run(executor.execute(tool.name, params))
                            if execution.result:
                                st.success("Completed")
                                st.json(execution.result)
                            else:
                                st.error(f"Failed: {execution.error}")
                            st.session_state[f"show_params_{tool.name}"] = False
                            st.rerun()


# Streamlit entry point
if __name__ == "__main__":
    render_copilot_dashboard()