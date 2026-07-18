"""
Automated Report Generation System

Generates professional financial research reports in multiple formats:
- Executive Summary
- Analyst Report
- Investment Thesis
- Company Snapshot
- Industry Analysis
- Daily/Weekly/Monthly Briefings

Supports Markdown, HTML, JSON export, and PDF-ready formatting.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from memory.research_memory import get_memory_store, ResearchSession, MemoryType

logger = logging.getLogger(__name__)


class ReportType(Enum):
    """Types of reports."""
    EXECUTIVE_SUMMARY = "executive_summary"
    ANALYST_REPORT = "analyst_report"
    INVESTMENT_THESIS = "investment_thesis"
    COMPANY_SNAPSHOT = "company_snapshot"
    INDUSTRY_ANALYSIS = "industry_analysis"
    DAILY_BRIEFING = "daily_briefing"
    WEEKLY_BRIEFING = "weekly_briefing"
    MONTHLY_INTELLIGENCE = "monthly_intelligence"
    CUSTOM = "custom"


class ReportFormat(Enum):
    """Output formats."""
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    PDF = "pdf"  # Requires additional conversion


@dataclass
class ReportSection:
    """A section of a report."""
    title: str
    content: str
    order: int
    subsections: List["ReportSection"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportData:
    """Complete data for report generation."""
    report_id: str
    report_type: ReportType
    company: str
    title: str
    subtitle: str
    generated_at: datetime
    sections: List[ReportSection]
    metadata: Dict[str, Any] = field(default_factory=dict)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    disclaimer: str = ""


@dataclass
class Report:
    """Generated report."""
    report_id: str
    report_type: ReportType
    format: ReportFormat
    content: str
    generated_at: datetime
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReportGenerator:
    """
    Automated report generator with template support.
    
    Features:
    - Multiple report types
    - Template-based generation
    - Multiple output formats
    - Source citation management
    - Automated section assembly
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        self.settings = get_settings()
        self.memory_store = get_memory_store()
        
        # Setup Jinja2 environment
        if templates_dir:
            template_path = Path(templates_dir)
        else:
            template_path = Path(__file__).parent / "templates"
        
        template_path.mkdir(exist_ok=True)
        
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_path)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Ensure default templates exist
        self._create_default_templates(template_path)
    
    def _create_default_templates(self, template_path: Path):
        """Create default report templates."""
        
        # Base HTML template
        base_html = """{# Base report template #}
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ report.title }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 40px 20px; color: #333; }
        h1 { color: #1a1a2e; border-bottom: 3px solid #16213e; padding-bottom: 10px; }
        h2 { color: #16213e; margin-top: 30px; border-bottom: 1px solid #e0e0e0; padding-bottom: 5px; }
        h3 { color: #0f3460; }
        .meta { color: #666; font-size: 0.9em; margin-bottom: 30px; }
        .section { margin-bottom: 30px; }
        .source { font-size: 0.8em; color: #888; margin-top: 5px; }
        .disclaimer { background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 5px; margin-top: 40px; font-size: 0.85em; }
        .metric { display: inline-block; background: #f8f9fa; padding: 10px 20px; margin: 5px; border-radius: 5px; border-left: 4px solid #16213e; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background: #1a1a2e; color: white; }
    </style>
</head>
<body>
    <h1>{{ report.title }}</h1>
    {% if report.subtitle %}<h2>{{ report.subtitle }}</h2>{% endif %}
    <div class="meta">
        <strong>Company:</strong> {{ report.company }} | 
        <strong>Generated:</strong> {{ report.generated_at.strftime('%Y-%m-%d %H:%M UTC') }} | 
        <strong>Type:</strong> {{ report.report_type.value }}
    </div>
    
    {% for section in report.sections %}
        <div class="section">
            <h2>{{ section.title }}</h2>
            {{ section.content | safe }}
            {% if section.subsections %}
                {% for sub in section.subsections %}
                    <h3>{{ sub.title }}</h3>
                    {{ sub.content | safe }}
                {% endfor %}
            {% endif %}
        </div>
    {% endfor %}
    
    {% if report.sources %}
        <h2>Sources & Citations</h2>
        <ol>
        {% for source in report.sources %}
            <li class="source">{{ source }}</li>
        {% endfor %}
        </ol>
    {% endif %}
    
    {% if report.disclaimer %}
        <div class="disclaimer">
            <strong>Disclaimer:</strong> {{ report.disclaimer }}
        </div>
    {% endif %}
</body>
</html>"""
        
        (template_path / "base.html").write_text(base_html)
        
        # Markdown template
        md_template = """# {{ report.title }}

{% if report.subtitle %}## {{ report.subtitle }}{% endif %}

**Company:** {{ report.company }} | **Generated:** {{ report.generated_at.strftime('%Y-%m-%d %H:%M UTC') }} | **Type:** {{ report.report_type.value }}

---

{% for section in report.sections %}
## {{ section.title }}

{{ section.content }}

{% if section.subsections %}
{% for sub in section.subsections %}
### {{ sub.title }}

{{ sub.content }}

{% endfor %}
{% endif %}

{% endfor %}

{% if report.sources %}
## Sources & Citations

{% for source in report.sources %}
- {{ source }}
{% endfor %}
{% endif %}

{% if report.disclaimer %}
---

> **Disclaimer:** {{ report.disclaimer }}
{% endif %}"""
        
        (template_path / "report.md").write_text(md_template)
        
        logger.info(f"Created default templates in {template_path}")
    
    async def generate_report(
        self,
        report_type: ReportType,
        company: str,
        session_id: Optional[str] = None,
        custom_data: Optional[Dict[str, Any]] = None,
        format: ReportFormat = ReportFormat.MARKDOWN,
        sections: Optional[List[str]] = None
    ) -> Report:
        """
        Generate a report from research data.
        
        Args:
            report_type: Type of report to generate
            company: Company name/ticker
            session_id: Optional specific research session
            custom_data: Additional data to include
            format: Output format
            sections: Specific sections to include (None = all)
            
        Returns:
            Generated Report object
        """
        report_id = str(uuid.uuid4())[:8]
        
        # Gather data
        data = await self._gather_report_data(
            report_type, company, session_id, custom_data
        )
        
        # Build sections based on report type
        sections = self._build_sections(report_type, data, sections)
        
        # Create report data object
        report_data = ReportData(
            report_id=report_id,
            report_type=report_type,
            company=company,
            title=self._get_report_title(report_type, company),
            subtitle=self._get_report_subtitle(report_type, data),
            generated_at=datetime.now(),
            sections=sections,
            metadata={
                "session_id": session_id,
                "custom_data_keys": list(custom_data.keys()) if custom_data else [],
                "generator_version": "1.0"
            },
            sources=data.get("sources", []),
            disclaimer=self._get_disclaimer(report_type)
        )
        
        # Render based on format
        if format == ReportFormat.MARKDOWN:
            content = await self._render_markdown(report_data)
        elif format == ReportFormat.HTML:
            content = await self._render_html(report_data)
        elif format == ReportFormat.JSON:
            content = await self._render_json(report_data)
        else:
            content = await self._render_markdown(report_data)
        
        # Save to file
        output_dir = Path("output/reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        ext = {"markdown": "md", "html": "html", "json": "json"}.get(format.value, "md")
        file_path = output_dir / f"{report_id}_{company}_{report_type.value}.{ext}"
        file_path.write_text(content)
        
        return Report(
            report_id=report_id,
            report_type=report_type,
            format=format,
            content=content,
            generated_at=datetime.now(),
            file_path=str(file_path),
            metadata=report_data.metadata
        )
    
    async def _gather_report_data(
        self,
        report_type: ReportType,
        company: str,
        session_id: Optional[str],
        custom_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Gather all data needed for report."""
        data = {
            "company": company,
            "report_type": report_type,
            "custom_data": custom_data or {},
            "sources": [],
            "conclusions": [],
            "agent_outputs": {}
        }
        
        # Get session data if provided
        if session_id:
            session = await self.memory_store.get_session(session_id)
            if session:
                data["session"] = session
                data["results"] = session.results
                data["conclusions"] = session.conclusions
                data["steps"] = session.steps
        
        # Get relevant memories
        memories = await self.memory_store.retrieve_memories(
            company=company,
            memory_types=[
                MemoryType.CONCLUSION,
                MemoryType.INSIGHT,
                MemoryType.REPORT
            ],
            limit=20
        )
        
        for mem in memories:
            if mem.memory_type == MemoryType.CONCLUSION:
                data["conclusions"].append(mem.content)
            elif mem.memory_type == MemoryType.AGENT_OUTPUT:
                agent = mem.source_agent or "unknown"
                data["agent_outputs"][agent] = mem.content
            data["sources"].append({
                "type": mem.memory_type.value,
                "content": str(mem.content)[:200],
                "agent": mem.source_agent,
                "confidence": mem.confidence
            })
        
        # Get recent sessions for context
        recent_sessions = await self.memory_store.get_recent_sessions(company, limit=5)
        data["recent_sessions"] = recent_sessions
        
        return data
    
    def _build_sections(
        self,
        report_type: ReportType,
        data: Dict[str, Any],
        requested_sections: Optional[List[str]] = None
    ) -> List[ReportSection]:
        """Build report sections based on type and data."""
        sections = []
        
        # Define section builders for each report type
        builders = {
            ReportType.EXECUTIVE_SUMMARY: self._build_executive_summary_sections,
            ReportType.ANALYST_REPORT: self._build_analyst_report_sections,
            ReportType.INVESTMENT_THESIS: self._build_investment_thesis_sections,
            ReportType.COMPANY_SNAPSHOT: self._build_company_snapshot_sections,
            ReportType.INDUSTRY_ANALYSIS: self._build_industry_analysis_sections,
            ReportType.DAILY_BRIEFING: self._build_daily_briefing_sections,
            ReportType.WEEKLY_BRIEFING: self._build_weekly_briefing_sections,
            ReportType.MONTHLY_INTELLIGENCE: self._build_monthly_intelligence_sections,
        }
        
        builder = builders.get(report_type, self._build_default_sections)
        all_sections = builder(data)
        
        # Filter sections if requested
        if requested_sections:
            all_sections = [s for s in all_sections if s.title in requested_sections]
        
        return all_sections
    
    def _build_executive_summary_sections(self, data: Dict) -> List[ReportSection]:
        """Build executive summary sections."""
        return [
            ReportSection(
                title="Key Findings",
                content=self._format_key_findings(data),
                order=1
            ),
            ReportSection(
                title="Financial Highlights",
                content=self._format_financial_highlights(data),
                order=2
            ),
            ReportSection(
                title="Risk Assessment",
                content=self._format_risk_assessment(data),
                order=3
            ),
            ReportSection(
                title="Recommendation",
                content=self._format_recommendation(data),
                order=4
            ),
        ]
    
    def _build_analyst_report_sections(self, data: Dict) -> List[ReportSection]:
        """Build full analyst report sections."""
        return [
            ReportSection(
                title="Executive Summary",
                content=self._format_executive_summary(data),
                order=1
            ),
            ReportSection(
                title="Company Overview",
                content=self._format_company_overview(data),
                order=2
            ),
            ReportSection(
                title="Financial Analysis",
                content=self._format_financial_analysis(data),
                order=3
            ),
            ReportSection(
                title="Valuation",
                content=self._format_valuation(data),
                order=4
            ),
            ReportSection(
                title="Competitive Positioning",
                content=self._format_competitive_positioning(data),
                order=5
            ),
            ReportSection(
                title="Risk Factors",
                content=self._format_risk_factors(data),
                order=6
            ),
            ReportSection(
                title="Catalysts & Outlook",
                content=self._format_catalysts_outlook(data),
                order=7
            ),
            ReportSection(
                title="Recommendation & Price Target",
                content=self._format_recommendation_target(data),
                order=8
            ),
        ]
    
    def _build_investment_thesis_sections(self, data: Dict) -> List[ReportSection]:
        """Build investment thesis sections."""
        return [
            ReportSection(
                title="Thesis Statement",
                content=self._format_thesis_statement(data),
                order=1
            ),
            ReportSection(
                title="Key Drivers",
                content=self._format_key_drivers(data),
                order=2
            ),
            ReportSection(
                title="Financial Evidence",
                content=self._format_financial_evidence(data),
                order=3
            ),
            ReportSection(
                title="Risk Analysis",
                content=self._format_thesis_risks(data),
                order=4
            ),
            ReportSection(
                title="Scenario Analysis",
                content=self._format_scenarios(data),
                order=5
            ),
            ReportSection(
                title="Conclusion",
                content=self._format_thesis_conclusion(data),
                order=6
            ),
        ]
    
    def _build_company_snapshot_sections(self, data: Dict) -> List[ReportSection]:
        """Build company snapshot sections."""
        return [
            ReportSection(
                title="Quick Facts",
                content=self._format_quick_facts(data),
                order=1
            ),
            ReportSection(
                title="Recent Performance",
                content=self._format_recent_performance(data),
                order=2
            ),
            ReportSection(
                title="Key Metrics",
                content=self._format_key_metrics(data),
                order=3
            ),
            ReportSection(
                title="Latest News & Events",
                content=self._format_latest_news(data),
                order=4
            ),
        ]
    
    def _build_industry_analysis_sections(self, data: Dict) -> List[ReportSection]:
        """Build industry analysis sections."""
        return [
            ReportSection(
                title="Industry Overview",
                content=self._format_industry_overview(data),
                order=1
            ),
            ReportSection(
                title="Market Size & Growth",
                content=self._format_market_size(data),
                order=2
            ),
            ReportSection(
                title="Competitive Landscape",
                content=self._format_competitive_landscape(data),
                order=3
            ),
            ReportSection(
                title="Key Trends",
                content=self._format_key_trends(data),
                order=4
            ),
            ReportSection(
                title="Regulatory Environment",
                content=self._format_regulatory(data),
                order=5
            ),
            ReportSection(
                title="Outlook",
                content=self._format_industry_outlook(data),
                order=6
            ),
        ]
    
    def _build_daily_briefing_sections(self, data: Dict) -> List[ReportSection]:
        """Build daily briefing sections."""
        return [
            ReportSection(title="Market Overview", content=self._format_market_overview(data), order=1),
            ReportSection(title="Key Movers", content=self._format_key_movers(data), order=2),
            ReportSection(title="News Highlights", content=self._format_news_highlights(data), order=3),
            ReportSection(title="Watchlist Alerts", content=self._format_watchlist_alerts(data), order=4),
        ]
    
    def _build_weekly_briefing_sections(self, data: Dict) -> List[ReportSection]:
        """Build weekly briefing sections."""
        return [
            ReportSection(title="Weekly Market Summary", content=self._format_weekly_summary(data), order=1),
            ReportSection(title="Sector Performance", content=self._format_sector_performance(data), order=2),
            ReportSection(title="Earnings Highlights", content=self._format_earnings_highlights(data), order=3),
            ReportSection(title="Macro Events", content=self._format_macro_events(data), order=4),
            ReportSection(title="Watchlist Review", content=self._format_watchlist_review(data), order=5),
            ReportSection(title="Upcoming Catalysts", content=self._format_upcoming_catalysts(data), order=6),
        ]
    
    def _build_monthly_intelligence_sections(self, data: Dict) -> List[ReportSection]:
        """Build monthly intelligence report sections."""
        return [
            ReportSection(title="Monthly Market Review", content=self._format_monthly_review(data), order=1),
            ReportSection(title="Portfolio Performance", content=self._format_portfolio_performance(data), order=2),
            ReportSection(title="Strategic Themes", content=self._format_strategic_themes(data), order=3),
            ReportSection(title="Deep Dive Analyses", content=self._format_deep_dives(data), order=4),
            ReportSection(title="Risk Dashboard", content=self._format_risk_dashboard(data), order=5),
            ReportSection(title="Forward Outlook", content=self._format_forward_outlook(data), order=6),
        ]
    
    def _build_default_sections(self, data: Dict) -> List[ReportSection]:
        """Build default sections."""
        return [
            ReportSection(title="Overview", content=self._format_overview(data), order=1),
            ReportSection(title="Analysis", content=self._format_analysis(data), order=2),
            ReportSection(title="Conclusions", content=self._format_conclusions(data), order=3),
        ]
    
    # Section formatting methods (simplified for brevity)
    def _format_key_findings(self, data: Dict) -> str:
        findings = data.get("conclusions", [])
        if not findings:
            return "No key findings available from recent research."
        return "\n".join([f"- {f}" for f in findings[:5]])
    
    def _format_financial_highlights(self, data: Dict) -> str:
        outputs = data.get("agent_outputs", {})
        financial = outputs.get("financial_document", {})
        if isinstance(financial, dict):
            return f"**Revenue:** {financial.get('revenue', 'N/A')}\n**Net Income:** {financial.get('net_income', 'N/A')}\n**EPS:** {financial.get('eps', 'N/A')}"
        return "Financial highlights not available."
    
    def _format_risk_assessment(self, data: Dict) -> str:
        outputs = data.get("agent_outputs", {})
        risk = outputs.get("risk", {})
        if isinstance(risk, dict):
            return f"**Overall Risk:** {risk.get('overall_risk', 'N/A')}\n**Key Risks:** {risk.get('key_risks', 'N/A')}"
        return "Risk assessment not available."
    
    def _format_recommendation(self, data: Dict) -> str:
        outputs = data.get("agent_outputs", {})
        summary = outputs.get("investment_summary", {})
        if isinstance(summary, dict):
            return f"**Recommendation:** {summary.get('recommendation', 'N/A')}\n**Price Target:** {summary.get('price_target', 'N/A')}\n**Rationale:** {summary.get('rationale', 'N/A')}"
        return "Investment recommendation not available."
    
    def _format_executive_summary(self, data: Dict) -> str:
        return self._format_key_findings(data)
    
    def _format_company_overview(self, data: Dict) -> str:
        return f"**Company:** {data.get('company', 'N/A')}\n\nCompany overview will be populated from research data."
    
    def _format_financial_analysis(self, data: Dict) -> str:
        return "Detailed financial analysis will be populated from financial document agent and market data agent outputs."
    
    def _format_valuation(self, data: Dict) -> str:
        return "Valuation analysis including DCF, comparables, and precedent transactions."
    
    def _format_competitive_positioning(self, data: Dict) -> str:
        outputs = data.get("agent_outputs", {})
        comp = outputs.get("competitive", {})
        if isinstance(comp, dict):
            return str(comp)
        return "Competitive positioning analysis not available."
    
    def _format_risk_factors(self, data: Dict) -> str:
        return "Comprehensive risk factor analysis including market, credit, operational, and liquidity risks."
    
    def _format_catalysts_outlook(self, data: Dict) -> str:
        return "Key catalysts and forward-looking outlook based on news, events, and management guidance."
    
    def _format_recommendation_target(self, data: Dict) -> str:
        return self._format_recommendation(data)
    
    def _format_thesis_statement(self, data: Dict) -> str:
        return "Investment thesis statement will be synthesized from all agent outputs."
    
    def _format_key_drivers(self, data: Dict) -> str:
        return "Key investment drivers identified from research."
    
    def _format_financial_evidence(self, data: Dict) -> str:
        return "Financial evidence supporting the thesis."
    
    def _format_thesis_risks(self, data: Dict) -> str:
        return "Risk factors specific to the investment thesis."
    
    def _format_scenarios(self, data: Dict) -> str:
        return "Bull, base, and bear case scenarios with probabilities."
    
    def _format_thesis_conclusion(self, data: Dict) -> str:
        return "Final thesis conclusion and conviction level."
    
    def _format_quick_facts(self, data: Dict) -> str:
        company = data.get("company", "N/A")
        return f"**Company:** {company}\n**Snapshot generated:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
    
    def _format_recent_performance(self, data: Dict) -> str:
        return "Recent price performance and key events."
    
    def _format_key_metrics(self, data: Dict) -> str:
        return "Key financial and operational metrics."
    
    def _format_latest_news(self, data: Dict) -> str:
        outputs = data.get("agent_outputs", {})
        news = outputs.get("news", {})
        if isinstance(news, dict):
            return str(news)
        return "Latest news and events not available."
    
    def _format_industry_overview(self, data: Dict) -> str:
        return "Industry overview and structure."
    
    def _format_market_size(self, data: Dict) -> str:
        return "Market size, growth rates, and TAM/SAM/SOM analysis."
    
    def _format_competitive_landscape(self, data: Dict) -> str:
        return "Competitive landscape with key players and market share."
    
    def _format_key_trends(self, data: Dict) -> str:
        return "Key industry trends and drivers."
    
    def _format_regulatory(self, data: Dict) -> str:
        return "Regulatory environment and upcoming changes."
    
    def _format_industry_outlook(self, data: Dict) -> str:
        return "Industry outlook and investment implications."
    
    def _format_market_overview(self, data: Dict) -> str:
        return "Daily market overview with key indices and sentiment."
    
    def _format_key_movers(self, data: Dict) -> str:
        return "Top gainers/losers and unusual activity."
    
    def _format_news_highlights(self, data: Dict) -> str:
        return "Top news stories impacting markets."
    
    def _format_watchlist_alerts(self, data: Dict) -> str:
        return "Watchlist alerts and triggered signals."
    
    def _format_weekly_summary(self, data: Dict) -> str:
        return "Weekly market summary with key themes."
    
    def _format_sector_performance(self, data: Dict) -> str:
        return "Sector rotation and performance analysis."
    
    def _format_earnings_highlights(self, data: Dict) -> str:
        return "Notable earnings reports and surprises."
    
    def _format_macro_events(self, data: Dict) -> str:
        return "Macroeconomic events and policy changes."
    
    def _format_watchlist_review(self, data: Dict) -> str:
        return "Watchlist performance and alerts review."
    
    def _format_upcoming_catalysts(self, data: Dict) -> str:
        return "Upcoming events and catalysts for watchlist companies."
    
    def _format_monthly_review(self, data: Dict) -> str:
        return "Monthly market review with attribution."
    
    def _format_portfolio_performance(self, data: Dict) -> str:
        return "Portfolio performance and attribution analysis."
    
    def _format_strategic_themes(self, data: Dict) -> str:
        return "Strategic investment themes for the month."
    
    def _format_deep_dives(self, data: Dict) -> str:
        return "Deep dive analyses on selected topics."
    
    def _format_risk_dashboard(self, data: Dict) -> str:
        return "Risk dashboard with key metrics and alerts."
    
    def _format_forward_outlook(self, data: Dict) -> str:
        return "Forward-looking outlook and positioning."
    
    def _format_overview(self, data: Dict) -> str:
        return f"Overview for {data.get('company', 'N/A')}."
    
    def _format_analysis(self, data: Dict) -> str:
        return "Analysis section."
    
    def _format_conclusions(self, data: Dict) -> str:
        conclusions = data.get("conclusions", [])
        if conclusions:
            return "\n".join([f"- {c}" for c in conclusions])
        return "No conclusions available."
    
    def _get_report_title(self, report_type: ReportType, company: str) -> str:
        titles = {
            ReportType.EXECUTIVE_SUMMARY: f"{company} - Executive Summary",
            ReportType.ANALYST_REPORT: f"{company} - Equity Research Report",
            ReportType.INVESTMENT_THESIS: f"{company} - Investment Thesis",
            ReportType.COMPANY_SNAPSHOT: f"{company} - Company Snapshot",
            ReportType.INDUSTRY_ANALYSIS: f"{company} - Industry Analysis",
            ReportType.DAILY_BRIEFING: f"Daily Market Briefing - {datetime.now().strftime('%Y-%m-%d')}",
            ReportType.WEEKLY_BRIEFING: f"Weekly Market Briefing - Week of {datetime.now().strftime('%Y-%m-%d')}",
            ReportType.MONTHLY_INTELLIGENCE: f"Monthly Intelligence Report - {datetime.now().strftime('%B %Y')}",
            ReportType.CUSTOM: f"{company} - Custom Report",
        }
        return titles.get(report_type, f"{company} - Report")
    
    def _get_report_subtitle(self, report_type: ReportType, data: Dict) -> str:
        subtitles = {
            ReportType.EXECUTIVE_SUMMARY: "Key findings and recommendation",
            ReportType.ANALYST_REPORT: "Comprehensive equity research analysis",
            ReportType.INVESTMENT_THESIS: "Investment rationale and conviction",
            ReportType.COMPANY_SNAPSHOT: "Quick reference for key metrics and news",
            ReportType.INDUSTRY_ANALYSIS: "Sector landscape and competitive dynamics",
            ReportType.DAILY_BRIEFING: "Markets, movers, and news",
            ReportType.WEEKLY_BRIEFING: "Week in review and forward look",
            ReportType.MONTHLY_INTELLIGENCE: "Strategic themes and portfolio insights",
        }
        return subtitles.get(report_type, "")
    
    def _get_disclaimer(self, report_type: ReportType) -> str:
        return (
            "This report is generated by an AI-powered financial research platform "
            "for informational purposes only. It does not constitute investment advice. "
            "Past performance is not indicative of future results. All investments carry risk. "
            "Please conduct your own due diligence and consult with a qualified financial advisor "
            "before making investment decisions."
        )
    
    async def _render_markdown(self, report: ReportData) -> str:
        """Render report as Markdown."""
        template = self.jinja_env.get_template("report.md")
        return template.render(report=report)
    
    async def _render_html(self, report: ReportData) -> str:
        """Render report as HTML."""
        template = self.jinja_env.get_template("base.html")
        return template.render(report=report)
    
    async def _render_json(self, report: ReportData) -> str:
        """Render report as JSON."""
        return json.dumps({
            "report_id": report.report_id,
            "report_type": report.report_type.value,
            "company": report.company,
            "title": report.title,
            "subtitle": report.subtitle,
            "generated_at": report.generated_at.isoformat(),
            "sections": [
                {
                    "title": s.title,
                    "content": s.content,
                    "order": s.order,
                    "subsections": [
                        {"title": sub.title, "content": sub.content, "order": sub.order}
                        for sub in s.subsections
                    ]
                }
                for s in report.sections
            ],
            "sources": report.sources,
            "disclaimer": report.disclaimer,
            "metadata": report.metadata
        }, indent=2)


# Convenience function
async def generate_report(
    report_type: ReportType,
    company: str,
    session_id: Optional[str] = None,
    custom_data: Optional[Dict] = None,
    format: ReportFormat = ReportFormat.MARKDOWN
) -> Report:
    """Generate a report."""
    generator = ReportGenerator()
    return await generator.generate_report(report_type, company, session_id, custom_data, format)