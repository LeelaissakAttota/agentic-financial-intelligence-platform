"""
Streamlit Dashboard for AI Financial Research Analyst Agent.

Features:
- Company input with ticker support
- Run analysis button triggering API
- Agent result tabs: News, Market, Financial, Sentiment, Risk, Competitor, Investment Summary
- Citations display
- Confidence scores
- Report history
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import Settings
from database import get_company_reports, get_report_by_id, get_session, init_db

st.set_page_config(
    page_title="AI Financial Research Analyst",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1e3a8a;
        margin-bottom: 1rem;
    }
    .confidence-high { color: #059669; font-weight: 600; }
    .confidence-medium { color: #d97706; font-weight: 600; }
    .confidence-low { color: #dc2626; font-weight: 600; }
    .status-success { color: #059669; }
    .status-error { color: #dc2626; }
    .status-running { color: #2563eb; }
    .status-queued { color: #6b7280; }
    .citation-box {
        background-color: #f8fafc;
        border-left: 4px solid #3b82f6;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 0 0.5rem 0.5rem 0;
        font-size: 0.875rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e5e7eb;
    }
    .agent-tab-content {
        padding: 1rem 0;
    }
    .error-message {
        background-color: #fef2f2;
        border: 1px solid #fecaca;
        color: #991b1b;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .running-indicator {
        display: inline-block;
        width: 8px;
        height: 8px;
        background-color: #2563eb;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.4; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)


# API Configuration
API_BASE_URL = "http://financial-research-api:8000"


@st.cache_data(ttl=60)
def load_report_history() -> List[Dict[str, Any]]:
    """Load recent reports from database."""
    try:
        settings = Settings()
        init_db(settings)
        session = get_session(settings)
        try:
            from database.models import Company, Report
            companies = session.query(Company).all()
            reports = []
            for company in companies:
                company_reports = get_company_reports(session, company.id, limit=10)
                for r in company_reports:
                    reports.append({
                        "id": r.id,
                        "company_name": company.name,
                        "ticker": company.ticker,
                        "generated_at": r.generated_at,
                        "report_id": r.id
                    })
            return sorted(reports, key=lambda x: x["generated_at"], reverse=True)
        finally:
            session.close()
    except Exception as e:
        st.error(f"Failed to load report history: {e}")
        return []


@st.cache_data(ttl=60)
def load_report_details(report_id: str) -> Optional[Dict[str, Any]]:
    """Load full report details from database."""
    try:
        settings = Settings()
        session = get_session(settings)
        try:
            report = get_report_by_id(session, report_id)
            if report:
                return json.loads(report.json_payload)
            return None
        finally:
            session.close()
    except Exception as e:
        st.error(f"Failed to load report: {e}")
        return None


def render_confidence_badge(confidence: str) -> str:
    """Render confidence score as colored badge."""
    if not confidence:
        return ""
    conf_lower = confidence.lower()
    if conf_lower == "high":
        return '<span class="confidence-high">● High</span>'
    elif conf_lower == "medium":
        return '<span class="confidence-medium">● Medium</span>'
    elif conf_lower == "low":
        return '<span class="confidence-low">● Low</span>'
    return f'<span>{confidence}</span>'


def render_status_badge(status: str) -> str:
    """Render status as colored badge."""
    status_lower = status.lower()
    if status_lower == "success":
        return '<span class="status-success">✓ Success</span>'
    elif status_lower == "error":
        return '<span class="status-error">✗ Error</span>'
    elif status_lower == "running":
        return '<span class="status-running"><span class="running-indicator"></span>Running</span>'
    elif status_lower == "queued":
        return '<span class="status-queued">⏳ Queued</span>'
    return f'<span>{status}</span>'


def render_citations(data: Dict[str, Any], title: str = "Citations") -> None:
    """Render citations from agent output."""
    if not data:
        return
    
    citations = []
    
    # Look for common citation fields
    if isinstance(data, dict):
        # Financial report agent has findings with chunk_ids
        if "findings" in data:
            for key, finding in data["findings"].items():
                if isinstance(finding, dict) and "chunk_id" in finding:
                    citations.append(f"**{key}**: Chunk {finding['chunk_id']}")
        
        # News/market agents might have sources
        if "sources" in data:
            for src in data["sources"]:
                citations.append(str(src))
        
        # Document context
        if "document_context" in data:
            ctx = data["document_context"]
            if "doc_types_used" in ctx:
                citations.append(f"Document types: {', '.join(ctx['doc_types_used'])}")
    
    if citations:
        with st.expander(f"📎 {title} ({len(citations)})"):
            for cite in citations:
                st.markdown(f'<div class="citation-box">{cite}</div>', unsafe_allow_html=True)


def render_agent_tab(tab_name: str, result: Dict[str, Any]) -> None:
    """Render a single agent's results in a tab."""
    status = result.get("status", "unknown")
    data = result.get("data")
    error = result.get("error")
    usage = result.get("usage")
    
    # Status and confidence
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.markdown(f"**Status:** {render_status_badge(status)}", unsafe_allow_html=True)
    with col2:
        if data and "confidence" in data:
            st.markdown(f"**Confidence:** {render_confidence_badge(data['confidence'])}", unsafe_allow_html=True)
    with col3:
        if usage and "total_tokens" in usage:
            st.metric("Tokens", usage["total_tokens"])
    
    if error:
        st.markdown(f'<div class="error-message">Error: {error}</div>', unsafe_allow_html=True)
        return
    
    if not data:
        st.info("No data returned")
        return
    
    # Render based on agent type
    if tab_name == "News Analysis":
        render_news_data(data)
    elif tab_name == "Market Data":
        render_market_data(data)
    elif tab_name == "Financial Report":
        render_financial_data(data)
    elif tab_name == "Sentiment Analysis":
        render_sentiment_data(data)
    elif tab_name == "Risk Analysis":
        render_risk_data(data)
    elif tab_name == "Competitor Analysis":
        render_competitor_data(data)
    elif tab_name == "Investment Summary":
        render_investment_summary(data)
    else:
        # Generic JSON display
        st.json(data)
    
    # Citations
    render_citations(data, f"{tab_name} Citations")


def render_news_data(data: Dict[str, Any]) -> None:
    """Render news analysis data."""
    if "articles" in data:
        st.subheader(f"📰 Articles Found: {len(data['articles'])}")
        for article in data["articles"]:
            with st.expander(f"{article.get('title', 'Untitled')} ({article.get('source', 'Unknown')})"):
                st.write(f"**Impact:** {article.get('impact', 'N/A')}")
                st.write(f"**Date:** {article.get('date', 'N/A')}")
                st.write(f"**Summary:** {article.get('summary', 'N/A')}")
                if article.get('url'):
                    st.link_button("Read Full Article", article['url'])
    
    if "summary" in data:
        st.subheader("📋 Summary")
        st.write(data["summary"])


def render_market_data(data: Dict[str, Any]) -> None:
    """Render market data."""
    if "price" in data:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Price", f"${data['price']:,.2f}")
        with col2:
            change = data.get("change_24h", 0)
            st.metric("24h Change", f"{change:+.2f}%")
        with col3:
            st.metric("Volume", f"{data.get('volume', 0):,.0f}")
    
    if "technical_indicators" in data:
        st.subheader("📈 Technical Indicators")
        for indicator, value in data["technical_indicators"].items():
            st.write(f"**{indicator}:** {value}")
    
    if "summary" in data:
        st.subheader("📋 Market Summary")
        st.write(data["summary"])


def render_financial_data(data: Dict[str, Any]) -> None:
    """Render financial report data."""
    if "findings" in data:
        st.subheader("🔍 Key Findings")
        for question, finding in data["findings"].items():
            with st.expander(question):
                if isinstance(finding, dict):
                    st.write(f"**Answer:** {finding.get('value', 'N/A')}")
                    if finding.get("chunk_id"):
                        st.caption(f"Source chunk: {finding['chunk_id']}")
                    if finding.get("conflict_note"):
                        st.warning(f"Conflict: {finding['conflict_note']}")
                else:
                    st.write(finding)
    
    if "document_context" in data:
        ctx = data["document_context"]
        st.subheader("📄 Document Context")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Fiscal Year:** {ctx.get('fiscal_year', 'N/A')}")
            st.write(f"**Fiscal Quarter:** {ctx.get('fiscal_quarter', 'N/A')}")
        with col2:
            st.write(f"**Doc Types:** {', '.join(ctx.get('doc_types_used', []))}")


def render_sentiment_data(data: Dict[str, Any]) -> None:
    """Render sentiment analysis data."""
    if "overall_market_emotion" in data:
        st.subheader("🎭 Overall Market Emotion")
        st.markdown(f"### {data['overall_market_emotion']}")
    
    if "by_source" in data:
        st.subheader("📊 Sentiment by Source")
        cols = st.columns(3)
        sources = ["news", "social", "analyst_opinions"]
        for i, src in enumerate(sources):
            if src in data["by_source"]:
                s = data["by_source"][src]
                with cols[i]:
                    st.metric(
                        src.capitalize(),
                        f"+{s.get('positive', 0):.0%} / {s.get('negative', 0):.0%}",
                        delta=f"Neutral: {s.get('neutral', 0):.0%}"
                    )
    
    if "drivers" in data:
        st.subheader("🎯 Key Drivers")
        for driver in data["drivers"]:
            st.write(f"• {driver}")
    
    if "divergence_flag" in data:
        flag = data["divergence_flag"]
        if flag.get("detected"):
            st.warning(f"⚠️ Divergence Detected: {flag.get('description')}")


def render_risk_data(data: Dict[str, Any]) -> None:
    """Render risk analysis data."""
    if "overall_risk_score" in data:
        score = data["overall_risk_score"]
        severity = data.get("overall_severity", "Unknown")
        color = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}.get(severity, "⚪")
        st.subheader(f"{color} Overall Risk Score: {score}/100 ({severity})")
    
    if "categories" in data:
        st.subheader("📂 Risk Categories")
        for cat_name, cat_data in data["categories"].items():
            with st.expander(f"{cat_name.replace('_', ' ').title()}: {cat_data.get('category_score', 'N/A')}/100"):
                st.write(f"**Severity:** {cat_data.get('severity', 'N/A')}")
                if "risk_factors" in cat_data:
                    for factor in cat_data["risk_factors"]:
                        st.write(f"• **{factor.get('factor', 'N/A')}** ({factor.get('source', 'N/A')})")
                        st.caption(factor.get("justification", ""))
    
    if "risk_explanation" in data:
        st.subheader("📝 Risk Explanation")
        st.write(data["risk_explanation"])


def render_competitor_data(data: Dict[str, Any]) -> None:
    """Render competitor analysis data."""
    if "comparison_table" in data:
        st.subheader("📊 Comparison Table")
        import pandas as pd
        df = pd.DataFrame(data["comparison_table"])
        st.dataframe(df, use_container_width=True)
    
    if "ranked_by_strength" in data:
        st.subheader("🏆 Ranked by Competitive Strength")
        for i, entry in enumerate(data["ranked_by_strength"], 1):
            st.write(f"{i}. **{entry.get('name', 'N/A')}** — {entry.get('reasoning', 'N/A')}")
    
    if "positioning_narrative" in data:
        st.subheader("📖 Positioning Narrative")
        st.write(data["positioning_narrative"])


def render_investment_summary(data: Dict[str, Any]) -> None:
    """Render investment summary data."""
    if "executive_summary" in data:
        st.subheader("📋 Executive Summary")
        st.write(data["executive_summary"])
    
    col1, col2 = st.columns(2)
    with col1:
        if "strengths" in data:
            st.subheader("✅ Strengths")
            for s in data["strengths"]:
                st.write(f"• {s}")
    with col2:
        if "weaknesses" in data:
            st.subheader("❌ Weaknesses")
            for w in data["weaknesses"]:
                st.write(f"• {w}")
    
    if "growth_potential" in data:
        st.subheader("📈 Growth Potential")
        st.write(data["growth_potential"])
    
    if "risks_summary" in data:
        st.subheader("⚠️ Risks Summary")
        st.write(data["risks_summary"])
    
    if "final_ai_opinion" in data:
        st.subheader("🤖 Final AI Opinion")
        st.info(data["final_ai_opinion"])
    
    if "disclaimer" in data:
        st.caption(data["disclaimer"])


def run_analysis_via_api(company: str, ticker: Optional[str] = None) -> str:
    """Start analysis via API and return analysis ID."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/analyze",
            json={"company": company, "ticker": ticker},
            timeout=30
        )
        response.raise_for_status()
        return response.json()["analysis_id"]
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API server. Make sure the API is running on port 8000.")
        return None
    except Exception as e:
        st.error(f"Failed to start analysis: {e}")
        return None


def poll_analysis_status(analysis_id: str) -> Optional[Dict[str, Any]]:
    """Poll analysis status until complete."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/analyze/{analysis_id}", timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to poll status: {e}")
        return None


# =============================================================================
# MAIN DASHBOARD
# =============================================================================

def main():
    st.markdown('<h1 class="main-header">📊 AI Financial Research Analyst</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # Company input
        company = st.text_input(
            "Company Name",
            placeholder="e.g., NVIDIA",
            help="Enter the company name to analyze"
        )
        
        ticker = st.text_input(
            "Ticker Symbol (Optional)",
            placeholder="e.g., NVDA",
            help="Optional ticker for more precise data"
        )
        
        # Run button
        if st.button("🚀 Run Analysis", type="primary", use_container_width=True, disabled=not company):
            analysis_id = run_analysis_via_api(company, ticker if ticker else None)
            if analysis_id:
                st.session_state.current_analysis_id = analysis_id
                st.session_state.current_company = company
                st.rerun()
        
        st.divider()
        
        # Report History
        st.header("📚 Report History")
        reports = load_report_history()
        
        if reports:
            for report in reports[:10]:
                with st.expander(f"{report['company_name']} ({report['ticker'] or 'N/A'}) - {report['generated_at'].strftime('%Y-%m-%d %H:%M')}"):
                    if st.button("View Report", key=f"view_{report['id']}"):
                        st.session_state.selected_report_id = report['id']
                        st.rerun()
        else:
            st.info("No reports yet. Run an analysis to generate your first report.")
    
    # Main content area
    tab_main, tab_history = st.tabs(["🔬 Analysis", "📜 History"])
    
    with tab_main:
        # Check for running analysis
        if "current_analysis_id" in st.session_state:
            analysis_id = st.session_state.current_analysis_id
            
            # Poll for results
            with st.spinner("Analysis running..."):
                status_placeholder = st.empty()
                progress_bar = st.progress(0)
                
                max_polls = 60  # 5 minutes max
                for i in range(max_polls):
                    result = poll_analysis_status(analysis_id)
                    if result:
                        status = result.get("status", "unknown")
                        progress = min((i + 1) / max_polls, 1.0)
                        progress_bar.progress(progress)
                        
                        if status == "completed":
                            status_placeholder.success("✅ Analysis Complete!")
                            display_results(result)
                            break
                        elif status == "failed":
                            if result is None:
                                status_placeholder.error("❌ Analysis Failed: Unknown error (no result data)")
                                break
                            metadata = result.get("metadata") or {}
                            error_msg = metadata.get("error", "Unknown error")
                            status_placeholder.error(f"❌ Analysis Failed: {error_msg}")
                            break
                        else:
                            status_placeholder.info(f"⏳ Status: {status}...")
                    
                    time.sleep(5)
                else:
                    status_placeholder.warning("⏱️ Analysis taking longer than expected. Check back later.")
            
            if st.button("🔄 Clear & Run New Analysis"):
                del st.session_state.current_analysis_id
                del st.session_state.current_company
                st.rerun()
        else:
            # Welcome screen
            st.markdown("""
            ## Welcome to the AI Financial Research Analyst
            
            This system uses a multi-agent architecture to perform comprehensive financial analysis:
            
            | Agent | Purpose |
            |-------|---------|
            | 📰 **News Analysis** | Analyzes recent news for sentiment and impact |
            | 📈 **Market Data** | Retrieves and analyzes market/technical data |
            | 📊 **Financial Report** | RAG-based analysis of 10-K/10-Q filings |
            | 😊 **Sentiment Analysis** | Synthesizes sentiment from news, social, analysts |
            | ⚠️ **Risk Analysis** | 4-category risk scoring (market, company, financial, valuation) |
            | 🏢 **Competitor Analysis** | Competitive positioning and comparison |
            | 🎯 **Investment Summary** | Final synthesis with thesis and recommendation |
            
            **To get started:** Enter a company name in the sidebar and click **Run Analysis**.
            """)
    
    with tab_history:
        st.header("📜 Report History")
        
        reports = load_report_history()
        if reports:
            # Search/filter
            search = st.text_input("🔍 Search reports", placeholder="Filter by company name...")
            
            filtered = reports
            if search:
                filtered = [r for r in reports if search.lower() in r['company_name'].lower()]
            
            for report in filtered:
                with st.expander(f"{report['company_name']} ({report['ticker'] or 'N/A'}) - {report['generated_at'].strftime('%Y-%m-%d %H:%M')}"):
                    if st.button("Load Full Report", key=f"load_{report['id']}"):
                        full_report = load_report_details(report['id'])
                        if full_report:
                            st.session_state.historical_report = full_report
                            st.rerun()
        else:
            st.info("No historical reports found.")
    
    # Display historical report if selected
    if "historical_report" in st.session_state:
        st.divider()
        st.subheader(f"📄 Historical Report: {st.session_state.historical_report.get('company', 'Unknown')}")
        display_results(st.session_state.historical_report)
        if st.button("Close Historical Report"):
            del st.session_state.historical_report
            st.rerun()


def display_results(result: Dict[str, Any]) -> None:
    """Display analysis results in tabs."""
    st.subheader(f"📊 Analysis Results: {result.get('company', 'Unknown')}")
    
    # Metadata
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Company", result.get("company", "N/A"))
    with col2:
        st.metric("Status", result.get("status", "N/A"))
    with col3:
        metadata = result.get("metadata") or {}
        completed = metadata.get("completed_tasks", 0)
        total = metadata.get("total_tasks", 0)
        st.metric("Tasks Completed", f"{completed}/{total}")
    
    # Agent results tabs
    results = result.get("results", {})
    if results:
        tab_names = [
            "News Analysis",
            "Market Data",
            "Financial Report",
            "Sentiment Analysis",
            "Risk Analysis",
            "Competitor Analysis",
            "Investment Summary"
        ]
        
        tabs = st.tabs(tab_names)
        for tab, name in zip(tabs, tab_names):
            with tab:
                agent_key = name.lower().replace(" ", "_")
                if agent_key in results:
                    render_agent_tab(name, results[agent_key])
                else:
                    st.info(f"No data for {name}")


if __name__ == "__main__":
    main()