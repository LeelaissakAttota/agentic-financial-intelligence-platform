"""Investment Summary Agent - Synthesizes all agent outputs into final investment thesis."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from llm.model_registry import resolve_model, Complexity
from llm.base_client import BaseLLMClient

from .schema import (
    InvestmentSummaryInput,
    InvestmentSummaryOutput,
    SourcedPoint,
    DISCLAIMER_TEXT,
)
from .prompts import SYSTEM_PROMPT
from agents.manager_agent.schemas import WorkerResponse
from agents.manager_agent.manager import BaseWorkerAgent

logger = logging.getLogger(__name__)


class InvestmentSummaryAgent(BaseWorkerAgent):
    """Investment Summary Agent - Final synthesis agent."""

    def __init__(
        self,
        llm_provider: BaseLLMClient,
    ):
        """
        Initialize the Investment Summary Agent.

        Args:
            llm_provider: LLM provider for generating responses
        """
        super().__init__(agent_name="investment_summary_agent")
        self.llm_provider = llm_provider

    async def run(
        self,
        company: str,
        context: Dict[str, Any] = None,
    ) -> WorkerResponse:
        """
        Execute the investment summary synthesis workflow.

        Args:
            company: Company name to analyze
            context: Optional context with findings from all upstream agents
                Expected keys:
                - news_findings: dict from NewsAgent
                - market_findings: dict from MarketAgent
                - financial_findings: dict from FinancialReportAgent
                - competitor_findings: dict from CompetitorAgent
                - sentiment_findings: dict from SentimentAgent
                - risk_findings: dict from RiskAgent

        Returns:
            WorkerResponse with investment summary results
        """
        try:
            # Validate input
            if not company:
                raise ValueError("Company name is required")

            # Extract findings from context
            context = context or {}
            news_findings = context.get("news_findings", {})
            market_findings = context.get("market_findings", {})
            financial_findings = context.get("financial_findings", {})
            competitor_findings = context.get("competitor_findings", {})
            sentiment_findings = context.get("sentiment_findings", {})
            risk_findings = context.get("risk_findings", {})

            # Build input data
            input_data = InvestmentSummaryInput(
                company=company,
                ticker=context.get("ticker", ""),
                news_findings=news_findings,
                market_findings=market_findings,
                financial_findings=financial_findings,
                competitor_findings=competitor_findings,
                sentiment_findings=sentiment_findings,
                risk_findings=risk_findings,
                data_gaps=context.get("data_gaps", []),
            )

            # Build user prompt
            user_prompt = self._build_user_prompt(input_data)

            # Define response schema for structured output
            response_schema = self._get_response_schema()

            # Resolve model from registry
            resolution = resolve_model("investment_summary_agent", "complex")
            model = resolution.model

            # Call LLM with structured output
            llm_result = await self.llm_provider.agenerate_json(
                system_prompt=SYSTEM_PROMPT,
                user_message=user_prompt,
                response_schema=response_schema,
                model=model,
            )

            # Parse and validate output
            content = llm_result.get("content", {})
            usage = llm_result.get("usage")

            if not content:
                raise ValueError("LLM returned empty content")

            # Add missing required fields
            content["company"] = company
            content["generated_at"] = datetime.utcnow().isoformat()
            content["disclaimer"] = "This report is for informational purposes only and does not constitute financial advice."

            # Validate output schema
            try:
                output = InvestmentSummaryOutput(**content)
            except Exception as e:
                logger.error(f"Output validation failed: {e}")
                raise ValueError(f"Output validation failed: {str(e)}")

            # Return in WorkerResponse format
            return WorkerResponse(
                status="success",
                data=output.model_dump(),
                usage=usage.to_dict() if usage and hasattr(usage, 'to_dict') else usage
            )

        except ValueError as e:
            logger.error(f"InvestmentSummaryAgent input error: {e}")
            return WorkerResponse(
                status="error",
                error=str(e),
                data=None,
                usage=None
            )
        except Exception as e:
            logger.error(f"InvestmentSummaryAgent failed: {e}")
            return WorkerResponse(
                status="error",
                error=f"Investment summary agent failed: {str(e)}",
                data=None,
                usage=None
            )

    def _build_user_prompt(self, input_data: InvestmentSummaryInput) -> str:
        """Build the user prompt for the LLM."""
        parts = [
            f"Synthesize an investment summary for {input_data.company} ({input_data.ticker}).",
            "",
        ]

        # Helper to safely convert findings to string
        def format_findings(findings: Any, section_name: str) -> List[str]:
            section_parts = [f"=== {section_name} ==="]
            if not findings:
                return []
            if isinstance(findings, dict):
                for key, value in findings.items():
                    section_parts.append(f"{key}: {value}")
            elif isinstance(findings, list):
                for item in findings:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            section_parts.append(f"{k}: {v}")
                    else:
                        section_parts.append(str(item))
            else:
                section_parts.append(str(findings))
            section_parts.append("")
            return section_parts

        # News section
        parts.extend(format_findings(input_data.news_findings, "NEWS FINDINGS"))

        # Market section
        parts.extend(format_findings(input_data.market_findings, "MARKET FINDINGS"))

        # Financial section
        parts.extend(format_findings(input_data.financial_findings, "FINANCIAL FINDINGS"))

        # Competitor section
        parts.extend(format_findings(input_data.competitor_findings, "COMPETITOR FINDINGS"))

        # Sentiment section
        parts.extend(format_findings(input_data.sentiment_findings, "SENTIMENT FINDINGS"))

        # Risk section
        parts.extend(format_findings(input_data.risk_findings, "RISK FINDINGS"))

        # Data gaps
        if input_data.data_gaps:
            parts.append("=== DATA GAPS ===")
            for gap in input_data.data_gaps:
                parts.append(f"- {gap}")
            parts.append("")

        if not any([
            input_data.news_findings, input_data.market_findings,
            input_data.financial_findings, input_data.competitor_findings,
            input_data.sentiment_findings, input_data.risk_findings
        ]):
            parts.append("No upstream findings available.")
            parts.append("")

        parts.append("Provide your investment summary in the required JSON format.")

        return "\n".join(parts)

    def _get_response_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for structured LLM output."""
        return {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "enum": ["investment_summary_agent"]},
                "company": {"type": "string"},
                "generated_at": {"type": "string", "format": "date-time"},
                "executive_summary": {"type": "string"},
                "strengths": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "point": {"type": "string"},
                            "source": {"type": "string", "enum": ["news", "market", "financial_report", "competitor", "sentiment", "risk"]}
                        },
                        "required": ["point", "source"]
                    }
                },
                "weaknesses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "point": {"type": "string"},
                            "source": {"type": "string", "enum": ["news", "market", "financial_report", "competitor", "sentiment", "risk"]}
                        },
                        "required": ["point", "source"]
                    }
                },
                "growth_potential": {"type": "string"},
                "risks_summary": {"type": "string"},
                "final_ai_opinion": {"type": "string"},
                "disclaimer": {"type": "string", "enum": ["This report is for informational purposes only and does not constitute financial advice."]},
                "data_gaps_noted": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "string", "enum": ["High", "Medium", "Low"]}
            },
            "required": [
                "agent", "company", "generated_at", "executive_summary",
                "strengths", "weaknesses", "growth_potential", "risks_summary",
                "final_ai_opinion", "disclaimer", "data_gaps_noted", "confidence"
            ]
        }


# Synchronous wrapper for testing
def run_investment_summary_agent_sync(
    llm_provider: BaseLLMClient,
    company: str,
    context: Dict[str, Any] = None,
) -> WorkerResponse:
    """Synchronous wrapper for the InvestmentSummaryAgent for testing."""
    import asyncio
    agent = InvestmentSummaryAgent(llm_provider=llm_provider)
    return asyncio.run(agent.run(company, context))