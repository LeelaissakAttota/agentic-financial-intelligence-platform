"""
Copilot Prompt Templates - Standardized prompts for financial research.
"""
from typing import Dict, List, Any


# System prompt for the main copilot
COPILOT_SYSTEM_PROMPT = """You are an expert AI Financial Research Copilot. You help users conduct comprehensive financial research through natural language.

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

Be concise, cite sources, and always provide confidence levels."""


# Research planning prompts
RESEARCH_PLANNING_PROMPT = """Analyze this financial research request and create an execution plan.

User Request: {question}
Company: {company}
Context: {context}

Determine:
1. Query complexity (simple/moderate/complex/expert)
2. Required agents (select from: financial_document, sentiment, risk, competitive, news, market_data, investment_summary, knowledge_graph, portfolio, patterns, alerts, analytics, historical, cross_agent_memory)
3. Execution order with dependencies
4. Parallel execution groups
5. Estimated duration and cost

Return JSON with:
- complexity: one of [simple, moderate, complex, expert]
- agents: array of agent types
- steps: array of {step_id, agent_type, dependencies[], parallel_group?, estimated_duration_seconds, priority}
- estimated_total_duration: seconds
- estimated_cost_usd: dollars"""


# Tool selection prompt
TOOL_SELECTION_PROMPT = """Select the most relevant tools for this financial research task.

Task: {task_description}
Company: {company}
Available Tools:
{tool_list}

Consider:
- Task requirements and data needed
- Tool capabilities and limitations
- Cost and latency tradeoffs
- Information already available

Return JSON array of tool names in priority order with reasoning."""


# Investment thesis generation
INVESTMENT_THESIS_PROMPT = """Generate an investment thesis based on multi-agent research findings.

Company: {company}
Research Findings:
{findings}

Structure the thesis with:
1. Executive Summary (2-3 sentences)
2. Investment Recommendation (Buy/Hold/Sell with confidence)
3. Key Investment Drivers (3-5 bullet points)
4. Financial Analysis Summary
5. Competitive Position
6. Risk Assessment
7. Valuation & Price Target
8. Catalyst Timeline
9. Alternative Scenarios (Bear/Base/Bull)
10. Confidence Level

Format as structured JSON with all sections."""


# Risk assessment explanation
RISK_EXPLANATION_PROMPT = """Explain this risk assessment in clear, actionable terms.

Company: {company}
Risk Category: {risk_category}
Assessment: {assessment}
Confidence: {confidence}
Evidence: {evidence}

Provide:
1. Risk Level (Critical/High/Medium/Low)
2. Key Risk Drivers (3-5)
3. Potential Impact
4. Mitigation Strategies
4. Monitoring Recommendations
5. Confidence Assessment

Format as structured JSON."""


# Consensus building prompt
CONSENSUS_PROMPT = """Build consensus from multiple agent findings.

Question: {question}
Agent Findings:
{agent_findings}

Agreement Level: {agreement_level}

Determine:
1. Consensus conclusion
2. Level of agreement (0-1)
3. Key points of agreement
4. Points of disagreement
5. Minority viewpoints
6. Confidence in consensus

Format as structured JSON."""


# Conflict resolution prompt
CONFLICT_RESOLUTION_PROMPT = """Resolve conflicting findings from multiple agents.

Company: {company}
Conflicting Views:
{conflicting_views}

Evidence Available:
{evidence}

Resolve by:
1. Identifying source of conflict
2. Evaluating evidence quality
3. Determining most reliable finding
4. Explaining resolution rationale
5. Confidence in resolution

Format as structured JSON."""


# Report generation prompts
REPORT_PROMPTS = {
    "executive_summary": """Generate an executive summary report.

Company: {company}
Key Findings: {findings}
Recommendation: {recommendation}
Confidence: {confidence}

Format as concise executive summary (1 page max).""",

    "analyst_report": """Generate a full analyst report.

Company: {company}
Research Findings: {findings}
Investment Thesis: {thesis}
Risk Assessment: {risk}
Valuation: {valuation}

Format as professional analyst report with all standard sections.""",

    "company_snapshot": """Generate a company snapshot.

Company: {company}
Key Metrics: {metrics}
Recent News: {news}
Financial Health: {health}
Outlook: {outlook}

Format as 1-2 page snapshot.""",

    "daily_briefing": """Generate daily market briefing.

Date: {date}
Market Summary: {market}
Key Movers: {movers}
Sector News: {sector_news}
Economic Events: {events}

Format as concise daily briefing.""",

    "weekly_briefing": """Generate weekly intelligence briefing.

Week: {week}
Market Recap: {recap}
Sector Performance: {sectors}
Key Events: {events}
Upcoming Catalysts: {catalysts}

Format as weekly intelligence report.""",

    "monthly_intelligence": """Generate monthly intelligence report.

Month: {month}
Market Trends: {trends}
Sector Rotation: {rotation}
Macro Themes: {themes}
Portfolio Implications: {implications}

Format as comprehensive monthly report."""
}


# Conversation prompts
CONVERSATION_PROMPTS = {
    "extract_company": """Extract the company name or ticker from this message.

Message: {message}

Return ONLY the company/ticker or "NONE".""",

    "classify_intent": """Classify the user's intent.

Message: {message}
Context: {context}

Categories:
1. research_request - Full research analysis
2. plan_request - Create plan only
3. tool_request - Execute specific tool
4. report_request - Generate report
5. watchlist_request - Manage watchlists
6. memory_request - Query/store memory
7. status_request - Check status
8. conversational - General chat

Return ONLY the category.""",

    "generate_followup": """Generate 3 relevant follow-up questions.

Conversation: {conversation}
Context: {context}

Return JSON array of questions.""",

    "summarize_session": """Summarize this research session.

Session: {session}
Messages: {messages}

Provide concise summary with key findings."""
}


# Decision reasoning prompts
DECISION_REASONING_PROMPTS = {
    "evidence_gathering": """Plan evidence gathering for this decision.

Decision: {question}
Company: {company}
Type: {decision_type}

Available tools: {tools}

Return JSON array of tools to use with parameters.""",

    "hypothesis_formation": """Form testable hypotheses.

Question: {question}
Evidence: {evidence}

Return JSON array of hypotheses with confidence and test methods.""",

    "evidence_evaluation": """Evaluate evidence against hypothesis.

Hypothesis: {hypothesis}
Evidence: {evidence}

Return JSON with support_score, contradicting_evidence, updated_confidence.""",

    "alternative_consideration": """Generate alternative scenarios.

Evaluated hypotheses: {hypotheses}

Return JSON with bear/base/bull cases.""",

    "risk_analysis": """Identify risk factors.

Findings: {findings}
Hypotheses: {hypotheses}

Return JSON array of risks with severity and likelihood.""",

    "synthesis": """Synthesize findings into conclusion.

Evaluated hypotheses: {hypotheses}
Alternatives: {alternatives}
Risks: {risks}

Return JSON with synthesis, key_findings, confidence, recommendation."""
}


# Explanation prompts
EXPLANATION_PROMPTS = {
    "recommendation": """Explain this investment recommendation.

Company: {company}
Recommendation: {recommendation}
Confidence: {confidence}
Evidence: {evidence}

Provide:
1. 2-3 sentence summary
2. Detailed explanation with citations
3. Key risk factors
4. Main assumptions
5. Alternative scenarios (bear/base/bull)
6. What would change the recommendation

Format as structured response.""",

    "risk_assessment": """Explain this risk assessment.

Company: {company}
Risk: {risk_category}
Assessment: {assessment}
Confidence: {confidence}
Evidence: {evidence}

Provide clear explanation of risk level, drivers, and mitigations.""",

    "consensus": """Explain how consensus was reached.

Question: {question}
Consensus: {consensus}
Agreement: {agreement}
Agents: {agents}
Evidence: {evidence}

Explain agreement/disagreement points."""
}


# Tool parameter prompts
TOOL_PARAM_PROMPTS = {
    "analyze_financial_documents": "Analyze SEC filings and financial reports for {company}. Questions: {questions}. Filing types: {filing_types}. Fiscal year: {fiscal_year}.",
    "analyze_sentiment": "Analyze market sentiment for {company} over {timeframe_days} days from sources: {sources}.",
    "assess_risk": "Assess {risk_categories} risk for {company}. Portfolio context: {portfolio_context}.",
    "analyze_competitive_position": "Compare {company} with peers: {peers}. Metrics: {metrics}.",
    "get_financial_news": "Get financial news for {company} from last {timeframe_days} days. Categories: {categories}.",
    "get_market_data": "Get market data for {ticker} with timeframe {timeframe}. Indicators: {indicators}.",
    "generate_investment_thesis": "Generate investment thesis for {company} with context: {context}. Thesis type: {thesis_type}.",
    "query_knowledge_graph": "Query knowledge graph for {entity}. Query type: {query_type}. Depth: {depth}.",
    "manage_portfolio": "Portfolio action: {action} for portfolio {portfolio_id}. Parameters: {parameters}.",
    "detect_patterns": "Detect patterns for {ticker}. Pattern types: {pattern_types}. Lookback: {lookback_days} days.",
    "configure_alerts": "Alert action: {action} for watchlist {watchlist_id}. Rule: {rule}.",
    "run_analytics": "Analytics type: {analysis_type}. Parameters: {parameters}. Portfolio: {portfolio_id}.",
    "analyze_historical_trends": "Analyze historical trends for {company}. Type: {analysis_type}. Metrics: {metrics}. Lookback: {lookback_years} years.",
    "access_memory": "Memory action: {action} for {company}. Query: {query}. Memory type: {memory_type}."
}


def get_prompt(template_name: str, **kwargs) -> str:
    """Get formatted prompt by name."""
    # Check all prompt dictionaries
    all_prompts = {
        "copilot_system": COPILOT_SYSTEM_PROMPT,
        "research_planning": RESEARCH_PLANNING_PROMPT,
        "tool_selection": TOOL_SELECTION_PROMPT,
        "investment_thesis": INVESTMENT_THESIS_PROMPT,
        "risk_explanation": RISK_EXPLANATION_PROMPT,
        "consensus": CONSENSUS_PROMPT,
        "conflict_resolution": CONFLICT_RESOLUTION_PROMPT,
        **REPORT_PROMPTS,
        **CONVERSATION_PROMPTS,
        **DECISION_REASONING_PROMPTS,
        **EXPLANATION_PROMPTS,
        **TOOL_PARAM_PROMPTS
    }

    template = all_prompts.get(template_name)
    if not template:
        raise ValueError(f"Prompt template not found: {template_name}")

    return template.format(**kwargs)


# Export all prompt templates
__all__ = [
    "COPILOT_SYSTEM_PROMPT",
    "RESEARCH_PLANNING_PROMPT",
    "TOOL_SELECTION_PROMPT",
    "INVESTMENT_THESIS_PROMPT",
    "RISK_EXPLANATION_PROMPT",
    "CONSENSUS_PROMPT",
    "CONFLICT_RESOLUTION_PROMPT",
    "REPORT_PROMPTS",
    "CONVERSATION_PROMPTS",
    "DECISION_REASONING_PROMPTS",
    "EXPLANATION_PROMPTS",
    "TOOL_PARAM_PROMPTS",
    "get_prompt"
]