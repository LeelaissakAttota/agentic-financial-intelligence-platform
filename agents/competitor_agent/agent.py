"""Competitor Intelligence Agent - Analyzes competitive positioning using Market and Financial data."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from llm.base_client import BaseLLMClient
from llm.json_utils import extract_json
from llm.model_registry import resolve_model, Complexity

from .schemas import (
    CompetitorAgentInput,
    CompetitorAgentOutput,
    CompetitorMetricsIn,
    ComparisonRow,
    RankedEntry,
)
from .prompts import SYSTEM_PROMPT
from agents.manager_agent.schemas import WorkerResponse
from agents.manager_agent.manager import BaseWorkerAgent

logger = logging.getLogger(__name__)


class CompetitorAgent(BaseWorkerAgent):
    """Competitor Intelligence Agent for financial research."""

    def __init__(
        self,
        llm_provider,
    ):
        """
        Initialize the Competitor Agent.

        Args:
            llm_provider: LLM provider for generating responses
        """
        super().__init__(agent_name="competitor_agent")
        self.llm_provider = llm_provider

    async def run(
        self,
        company: str,
        context: Dict[str, Any] = None,
    ) -> WorkerResponse:
        """
        Execute the competitor analysis workflow.

        Args:
            company: Company name to analyze
            context: Optional context with competitor data from MarketAgent and FinancialReportAgent
                Expected keys:
                - company, ticker, segment, target_metrics, competitors

        Returns:
            WorkerResponse with competitor analysis results
        """
        try:
            # Validate input
            if not company:
                raise ValueError("Company name is required")

            # Extract competitor data from context
            context = context or {}
            company_name = context.get("company", company)
            ticker = context.get("ticker", "")
            segment = context.get("segment", "General")
            target_metrics = context.get("target_metrics", {})
            competitors = context.get("competitors", [])

            # Build input data
            input_data = CompetitorAgentInput(
                company=company_name,
                ticker=ticker,
                segment=segment,
                target_metrics=CompetitorMetricsIn(**target_metrics) if target_metrics else CompetitorMetricsIn(name=company_name),
                competitors=[CompetitorMetricsIn(**c) for c in competitors],
            )

            # Build user prompt
            user_prompt = self._build_user_prompt(input_data)

            # Define response schema for structured output
            response_schema = self._get_response_schema()

            # Resolve model from registry
            resolution = resolve_model("competitor_agent", "complex")
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
            content["company"] = company_name
            content["generated_at"] = datetime.utcnow().isoformat()

            # Validate output schema
            try:
                output = CompetitorAgentOutput(**content)
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
            logger.error(f"CompetitorAgent input error: {e}")
            return WorkerResponse(
                status="error",
                error=str(e),
                data=None,
                usage=None
            )
        except Exception as e:
            logger.error(f"CompetitorAgent failed: {e}")
            return WorkerResponse(
                status="error",
                error=f"Competitor agent failed: {str(e)}",
                data=None,
                usage=None
            )

    def _build_user_prompt(self, input_data: CompetitorAgentInput) -> str:
        """Build the user prompt for the LLM."""
        parts = [
            f"Analyze competitive positioning for {input_data.company} ({input_data.ticker}) in the {input_data.segment} segment.",
            "",
        ]

        # Target company section
        parts.append("=== TARGET COMPANY ===")
        parts.append(f"Name: {input_data.target_metrics.name}")
        parts.append(f"Revenue TTM: {input_data.target_metrics.revenue_ttm or 'not available'}")
        parts.append(f"Revenue Growth YoY: {input_data.target_metrics.revenue_growth_yoy_pct if input_data.target_metrics.revenue_growth_yoy_pct is not None else 'not available'}%")
        parts.append(f"Market Share: {input_data.target_metrics.market_share_pct if input_data.target_metrics.market_share_pct is not None else 'not available'}%")
        parts.append(f"Technology: {input_data.target_metrics.technology_notes or 'not available'}")
        parts.append(f"Known Risks: {', '.join(input_data.target_metrics.known_risks) if input_data.target_metrics.known_risks else 'none'}")
        parts.append("")

        # Competitors section
        if input_data.competitors:
            parts.append("=== COMPETITORS ===")
            for i, comp in enumerate(input_data.competitors, 1):
                parts.append(f"Competitor {i}: {comp.name}")
                parts.append(f"  Revenue TTM: {comp.revenue_ttm or 'not available'}")
                parts.append(f"  Revenue Growth YoY: {comp.revenue_growth_yoy_pct if comp.revenue_growth_yoy_pct is not None else 'not available'}%")
                parts.append(f"  Market Share: {comp.market_share_pct if comp.market_share_pct is not None else 'not available'}%")
                parts.append(f"  Technology: {comp.technology_notes or 'not available'}")
                parts.append(f"  Known Risks: {', '.join(comp.known_risks) if comp.known_risks else 'none'}")
                parts.append("")
        else:
            parts.append("No competitor data available.")
            parts.append("")

        parts.append("Provide your analysis in the required JSON format.")

        return "\n".join(parts)

    def _get_response_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for structured LLM output."""
        return {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "enum": ["competitor_agent"]},
                "company": {"type": "string"},
                "generated_at": {"type": "string", "format": "date-time"},
                "segment": {"type": "string"},
                "comparison_table": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "revenue_ttm": {"type": ["string", "number"]},
                            "revenue_growth_yoy_pct": {"type": ["number", "string"]},
                            "market_share_pct": {"type": ["number", "string"]},
                            "technology_summary": {"type": "string"},
                            "competitive_advantage": {"type": "string"},
                            "key_risks": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["name", "revenue_ttm", "revenue_growth_yoy_pct", "market_share_pct", "technology_summary", "competitive_advantage", "key_risks"]
                    }
                },
                "positioning_narrative": {"type": "string"},
                "ranked_by_strength": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rank": {"type": "integer"},
                            "name": {"type": "string"},
                            "reasoning": {"type": "string"}
                        },
                        "required": ["rank", "name", "reasoning"]
                    }
                },
                "confidence": {"type": "string", "enum": ["High", "Medium", "Low"]}
            },
            "required": [
                "agent", "company", "generated_at", "segment", "comparison_table",
                "positioning_narrative", "ranked_by_strength", "confidence"
            ]
        }


# Synchronous wrapper for testing
def run_competitor_agent_sync(
    llm_provider,
    company: str,
    context: Dict[str, Any] = None,
) -> WorkerResponse:
    """Synchronous wrapper for the CompetitorAgent for testing."""
    import asyncio
    agent = CompetitorAgent(llm_provider=llm_provider)
    return asyncio.run(agent.run(company, context))