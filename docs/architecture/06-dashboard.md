# Dashboard Architecture
## Agentic Financial Intelligence Platform

---

## Overview

The platform provides two dashboard interfaces:
1. **Streamlit Dashboard** (`dashboard/app.py`) - Main research interface with 10+ tabs
2. **AI Copilot Dashboard** (`dashboard/copilot.py`) - Conversational interface with 5 specialized tabs

Both are built with **Streamlit** for rapid development and interactive visualizations.

---

## Streamlit Dashboard (Main)

### Architecture
```
dashboard/
├── app.py              # Main entry point, routing, session state
├── components.py       # Reusable UI components (charts, tables, forms)
└── copilot.py          # AI Copilot interface (separate page)
```

### Tab Structure (10+ Tabs)

| Tab | Purpose | Key Components |
|-----|---------|----------------|
| **Overview** | Market snapshot, portfolio summary | Metrics cards, sparklines, alerts |
| **Research** | Autonomous research workflow | Plan visualization, agent status, results |
| **Documents** | SEC filings, earnings, reports | Document browser, RAG query, citations |
| **News** | News intelligence | Timeline, sentiment, entities, events |
| **Market Data** | Quotes, technicals, fundamentals | Charts, indicators, comparison |
| **Portfolio** | Positions, risk, rebalancing | Holdings table, risk metrics, optimizer |
| **Patterns** | Pattern detection | Pattern list, backtest results, signals |
| **Alerts** | Alert engine | Active alerts, rules, history, channels |
| **Analytics** | Advanced analytics | Factor models, Monte Carlo, attribution |
| **Memory** | Cross-agent memory | Memory browser, search, insights |
| **Settings** | Configuration | API keys, providers, notifications |

### Session State Management
```python
# Persistent state across reruns
if 'research_plan' not in st.session_state:
    st.session_state.research_plan = None
if 'agent_outputs' not in st.session_state:
    st.session_state.agent_outputs = {}
if 'selected_company' not in st.session_state:
    st.session_state.selected_company = "NVDA"
```

### Real-time Updates (Polling)
```python
# Auto-refresh for long-running operations
import time
from streamlit_autorefresh import st_autorefresh

# Refresh every 5 seconds during research
if st.session_state.research_status == "running":
    st_autorefresh(interval=5000, key="research_refresh")
```

### Key Components (`dashboard/components.py`)

#### Charts
```python
def render_candlestick_chart(data: pd.DataFrame, title: str):
    """Interactive candlestick with volume."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(...))
    fig.add_trace(go.Bar(...), row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

def render_sentiment_timeline(events: List[Event]):
    """Timeline with sentiment color coding."""
    # Green/Red bubbles for positive/negative events
```

#### Tables
```python
def render_holdings_table(positions: List[Position]):
    """Editable portfolio holdings with inline editing."""
    df = pd.DataFrame([p.to_dict() for p in positions])
    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    return edited

def render_alert_table(alerts: List[Alert]):
    """Alert table with severity badges and actions."""
    # Color-coded severity, dismiss buttons
```

#### Forms
```python
def render_watchlist_form(existing: Optional[Watchlist] = None):
    """Create/edit watchlist with type selector."""
    # Watchlist type, name, companies, alert rules

def render_alert_rule_form():
    """Alert rule builder with condition builder UI."""
    # Condition type, parameters, severity, channels
```

---

## AI Copilot Dashboard (Phase 8)

### Architecture
```
dashboard/copilot.py
```

### 5 Specialized Tabs

| Tab | Purpose | Key Features |
|-----|---------|--------------|
| **Chat** | Conversational interface | Streaming responses, agent cards, tool calls |
| **Workflow** | Plan visualization | Dependency graph, parallel waves, progress |
| **Decisions** | Decision confidence | Gauge, Bear/Base/Bull, risk factors |
| **Evidence** | Source documents | Citations, excerpts, relevance scores |
| **Tools** | Tool execution | Parameter forms, live results, history |

### Chat Tab
```python
def render_chat_tab():
    """Main conversational interface."""
    
    # Sidebar: Session management
    with st.sidebar:
        render_session_sidebar()
        render_agent_status_cards()
        render_token_cost_tracker()
    
    # Main: Chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "citations" in msg:
                render_citations(msg["citations"])
    
    # Input
    if prompt := st.chat_input("Ask me anything about financial research..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Stream response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            async for chunk in copilot_agent.stream_chat(prompt):
                full_response += chunk
                response_placeholder.markdown(full_response + "▌")
            response_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
```

### Workflow Tab
```python
def render_workflow_tab():
    """Visualize execution plan and progress."""
    
    plan = st.session_state.get('execution_plan')
    if not plan:
        st.info("No active plan. Create one in Chat tab.")
        return
    
    # Dependency graph
    st.subheader("Execution Plan")
    render_dependency_graph(plan)
    
    # Parallel waves
    for i, wave in enumerate(plan.waves):
        with st.expander(f"Wave {i+1}: {', '.join(wave.agent_types)}"):
            for step in wave.steps:
                status = get_step_status(step.step_id)
                render_step_card(step, status)
    
    # Progress bar
    completed = sum(1 for s in plan.steps if s.status == "completed")
    total = len(plan.steps)
    st.progress(completed / total, text=f"{completed}/{total} steps completed")
```

### Decisions Tab
```python
def render_decisions_tab():
    """Show decision confidence and alternatives."""
    
    decision = st.session_state.get('last_decision')
    if not decision:
        st.info("No decision available.")
        return
    
    # Confidence gauge
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Confidence", f"{decision.confidence*100:.0f}%")
    with col2:
        st.metric("Risk Level", decision.risk_level)
    with col3:
        st.metric("Model Used", decision.model_used)
    
    # Bear/Base/Bull scenarios
    st.subheader("Scenarios")
    for scenario in decision.scenarios:
        with st.expander(f"{scenario.name} ({scenario.probability*100:.0f}%)"):
            st.write(scenario.description)
            st.metric("Expected Return", f"{scenario.expected_return:.1f}%")
    
    # Risk factors
    st.subheader("Risk Factors")
    for risk in decision.risk_factors:
        severity_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}[risk.severity]
        st.write(f"{severity_color} **{risk.factor}**: {risk.description}")
        if risk.mitigation:
            st.caption(f"Mitigation: {risk.mitigation}")
```

### Evidence Tab
```python
def render_evidence_tab():
    """Display source documents with excerpts."""
    
    evidence = st.session_state.get('last_evidence', [])
    
    for ev in evidence:
        with st.expander(f"{ev.source_type} - {ev.citation}"):
            st.write(f"**Relevance**: {ev.relevance_score*100:.0f}%")
            st.write(f"**Source**: {ev.source}")
            st.write(f"**Excerpt**: {ev.excerpt}")
            if ev.url:
                st.link_button("View Source", ev.url)
```

### Tools Tab
```python
def render_tools_tab():
    """Interactive tool execution panel."""
    
    # Available tools
    tools = get_available_tools()
    
    selected_tool = st.selectbox(
        "Select Tool",
        tools,
        format_func=lambda t: f"{t.category} - {t.name}"
    )
    
    # Dynamic parameter form
    if selected_tool:
        params = render_tool_parameter_form(selected_tool)
        
        if st.button("Execute Tool"):
            with st.spinner("Executing..."):
                result = await tool_executor.execute(
                    selected_tool.name, params
                )
            st.json(result)
            st.session_state.tool_history.append({
                "tool": selected_tool.name,
                "params": params,
                "result": result,
                "timestamp": datetime.now()
            })
    
    # History
    with st.expander("Execution History"):
        for exec in reversed(st.session_state.tool_history):
            st.caption(f"{exec['timestamp']} - {exec['tool']}")
            st.json(exec['result'])
```

### Sidebar Components
```python
def render_session_sidebar():
    """Session management in sidebar."""
    st.selectbox("Session", sessions, on_change=switch_session)
    if st.button("New Session"):
        create_new_session()

def render_agent_status_cards():
    """Agent status indicators."""
    for agent in AGENTS:
        health = get_agent_health(agent)
        status_emoji = "🟢" if health.healthy else "🔴"
        st.caption(f"{status_emoji} {agent.name}")

def render_token_cost_tracker():
    """Token usage and cost tracking."""
    usage = st.session_state.get('token_usage', {})
    st.metric("Session Tokens", f"{usage.get('total', 0):,}")
    st.metric("Session Cost", f"${usage.get('cost_usd', 0):.4f}")
    st.metric("Avg Latency", f"{usage.get('avg_latency_ms', 0):.0f}ms")
```

---

## State Synchronization

### Between Tabs
```python
# Shared state keys
SHARED_STATE_KEYS = [
    'selected_company',
    'research_plan',
    'execution_plan',
    'agent_outputs',
    'last_decision',
    'last_evidence',
    'tool_history',
    'token_usage'
]

# Initialize all shared keys
for key in SHARED_STATE_KEYS:
    if key not in st.session_state:
        st.session_state[key] = default_value(key)
```

### WebSocket Integration (Future)
```python
# Placeholder for real-time updates
async def websocket_listener():
    """Listen for server-sent events."""
    async with websockets.connect(WS_URL) as ws:
        async for message in ws:
            event = json.loads(message)
            handle_realtime_event(event)
```

---

## Performance Optimization

### Caching
```python
@st.cache_data(ttl=300)
def get_market_data(ticker: str) -> pd.DataFrame:
    """Cached market data fetch."""
    return fetch_market_data(ticker)

@st.cache_data(ttl=60)
def get_research_status(research_id: str) -> ResearchStatus:
    """Cached status polling."""
    return api_client.get_research_status(research_id)
```

### Lazy Loading
```python
# Only load heavy components when tab is active
if st.session_state.active_tab == "analytics":
    render_analytics_tab()  # Heavy computations
```

---

## Configuration

### Streamlit Config (`.streamlit/config.toml`)
```toml
[server]
port = 8501
address = "0.0.0.0"
maxUploadSize = 200
enableCORS = true
enableXsrfProtection = true

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

### Theme Customization
```python
# Custom CSS injection
st.markdown("""
<style>
    .stMetric { background: #f0f2f6; padding: 1rem; border-radius: 0.5rem; }
    .stAlert { border-radius: 0.5rem; }
    .stButton > button { border-radius: 0.5rem; }
</style>
""", unsafe_allow_html=True)
```

---

## Deployment

### Docker
```dockerfile
# In Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY dashboard/ ./dashboard/
EXPOSE 8501
CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501"]
```

### Docker Compose
```yaml
streamlit:
  build: .
  command: streamlit run dashboard/app.py --server.port=8501
  ports:
    - "8501:8501"
  environment:
    - API_URL=http://api:8000
  depends_on:
    - api
```

---

*Document Version: 1.0*  
*Last Updated: 2026-07-18*  
*Platform: Agentic Financial Intelligence Platform v1.7.0-phase8*