"""Risk Management Agent - Analyzes risk across four categories using upstream agent findings."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from llm.base_client import BaseLLMClient
from llm.json_utils import extract_json
from llm.model_registry import resolve_model, Complexity

from .schema import (
    RiskAgentInput,
    RiskAgentOutput,
    RiskFactor,
    RiskCategory,
    RiskCategories,
    CATEGORY_WEIGHTS,
    severity_for_score,
)
from .prompts import SYSTEM_PROMPT
from .exceptions import (
    RiskAgentError,
    RiskAgentInputError,
    RiskAgentLLMError,
    RiskAgentValidationError,
)
from agents.manager_agent.schemas import WorkerResponse
from agents.manager_agent.manager import BaseWorkerAgent

logger = logging.getLogger(__name__)


class RiskAgent(BaseWorkerAgent):
    """Risk Management Agent for financial research."""

    def __init__(
        self,
        llm_provider,
    ):
        """
        Initialize the Risk Agent.

        Args:
            llm_provider: LLM provider for generating responses
        """
        super().__init__(agent_name="risk_agent")
        self.llm_provider = llm_provider

    async def run(
        self,
        company: str,
        context: Dict[str, Any] = None,
    ) -> WorkerResponse:
        """
        Execute the risk analysis workflow.

        Args:
            company: Company name to analyze
            context: Optional context with findings from other agents
                Expected keys:
                - news_findings: dict from NewsAgent
                - market_findings: dict from MarketAgent
                - financial_findings: dict from FinancialReportAgent
                - competitor_findings: dict from CompetitorAgent

        Returns:
            WorkerResponse with risk analysis results
        """
        try:
            # Validate input
            if not company:
                raise RiskAgentInputError("Company name is required")

            # Extract findings from context
            context = context or {}
            news_findings = context.get("news_findings", {})
            market_findings = context.get("market_findings", {})
            financial_findings = context.get("financial_findings", {})
            competitor_findings = context.get("competitor_findings", {})

            # Build input data
            input_data = RiskAgentInput(
                company=company,
                news_findings=news_findings,
                market_findings=market_findings,
                financial_findings=financial_findings,
                competitor_findings=competitor_findings,
            )

            # Build user prompt
            user_prompt = self._build_user_prompt(input_data)

            # Define response schema for structured output
            response_schema = self._get_response_schema()

            # Resolve model from registry
            resolution = resolve_model("risk_agent", "complex")
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
                raise RiskAgentValidationError("LLM returned empty content")

            # Handle LLM returning string "null" instead of JSON null
            def clean_null_values(obj):
                if isinstance(obj, dict):
                    return {k: clean_null_values(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [clean_null_values(v) for v in obj]
                elif obj == "null":
                    return None
                return obj

            content = clean_null_values(content)

            # Add missing required fields
            content["company"] = company
            content["generated_at"] = datetime.utcnow().isoformat()

            # Validate output schema
            try:
                output = RiskAgentOutput(**content)
            except Exception as e:
                logger.error(f"Output validation failed: {e}")
                raise RiskAgentValidationError(f"Output validation failed: {str(e)}")

            # Return in WorkerResponse format
            return WorkerResponse(
                status="success",
                data=output.model_dump(),
                usage=usage.to_dict() if usage and hasattr(usage, 'to_dict') else usage
            )

        except RiskAgentInputError as e:
            logger.error(f"RiskAgent input error: {e}")
            return WorkerResponse(
                status="error",
                error=str(e),
                data=None,
                usage=None
            )
        except RiskAgentValidationError as e:
            logger.error(f"RiskAgent validation error: {e}")
            return WorkerResponse(
                status="error",
                error=str(e),
                data=None,
                usage=None
            )
        except RiskAgentLLMError as e:
            logger.error(f"RiskAgent LLM error: {e}")
            return WorkerResponse(
                status="error",
                error=str(e),
                data=None,
                usage=None
            )
        except Exception as e:
            logger.error(f"RiskAgent failed: {e}")
            return WorkerResponse(
                status="error",
                error=f"Risk agent failed: {str(e)}",
                data=None,
                usage=None
            )

    def _build_user_prompt(self, input_data: RiskAgentInput) -> str:
        """Build the user prompt for the LLM."""
        parts = [
            f"Analyze risk for {input_data.company}.",
            "",
        ]

        # News section
        if input_data.news_findings:
            parts.append("=== NEWS FINDINGS ===")
            if isinstance(input_data.news_findings, dict):
                for key, value in input_data.news_findings.items():
                    parts.append(f"{key}: {value}")
            else:
                parts.append(str(input_data.news_findings))
            parts.append("")

        # Market section
        if input_data.market_findings:
            parts.append("=== MARKET FINDINGS ===")
            if isinstance(input_data.market_findings, dict):
                for key, value in input_data.market_findings.items():
                    parts.append(f"{key}: {value}")
            else:
                parts.append(str(input_data.market_findings))
            parts.append("")

        # Financial section
        if input_data.financial_findings:
            parts.append("=== FINANCIAL FINDINGS ===")
            if isinstance(input_data.financial_findings, dict):
                for key, value in input_data.financial_findings.items():
                    parts.append(f"{key}: {value}")
            else:
                parts.append(str(input_data.financial_findings))
            parts.append("")

        # Competitor section
        if input_data.competitor_findings:
            parts.append("=== COMPETITOR FINDINGS ===")
            if isinstance(input_data.competitor_findings, dict):
                for key, value in input_data.competitor_findings.items():
                    parts.append(f"{key}: {value}")
            else:
                parts.append(str(input_data.competitor_findings))
            parts.append("")

        if not any([input_data.news_findings, input_data.market_findings,
                   input_data.financial_findings, input_data.competitor_findings]):
            parts.append("No upstream findings available.")
            parts.append("")

        parts.append("Provide your risk analysis in the required JSON format.")

        return "\n".join(parts)

    def _get_response_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for structured LLM output."""
        return {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "enum": ["risk_agent"]},
                "company": {"type": "string"},
                "generated_at": {"type": "string", "format": "date-time"},
                "categories": {
                    "type": "object",
                    "properties": {
                        "market_risk": {
                            "type": "object",
                            "properties": {
                                "category_score": {"type": ["integer", "null"], "minimum": 0, "maximum": 100},
                                "severity": {"type": ["string", "null"], "enum": ["Low", "Medium", "High", "null"]},
                                "risk_factors": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "factor": {"type": "string"},
                                            "source": {"type": "string", "enum": ["news", "market", "financial_report", "competitor"]},
                                            "justification": {"type": "string"}
                                        },
                                        "required": ["factor", "source", "justification"]
                                    }
                                }
                            },
                            "required": ["category_score", "severity", "risk_factors"]
                        },
                        "company_risk": {
                            "type": "object",
                            "properties": {
                                "category_score": {"type": ["integer", "null"], "minimum": 0, "maximum": 100},
                                "severity": {"type": ["string", "null"], "enum": ["Low", "Medium", "High", "null"]},
                                "risk_factors": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "factor": {"type": "string"},
                                            "source": {"type": "string", "enum": ["news", "market", "financial_report", "competitor"]},
                                            "justification": {"type": "string"}
                                        },
                                        "required": ["factor", "source", "justification"]
                                    }
                                }
                            },
                            "required": ["category_score", "severity", "risk_factors"]
                        },
                        "financial_risk": {
                            "type": "object",
                            "properties": {
                                "category_score": {"type": ["integer", "null"], "minimum": 0, "maximum": 100},
                                "severity": {"type": ["string", "null"], "enum": ["Low", "Medium", "High", "null"]},
                                "risk_factors": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "factor": {"type": "string"},
                                            "source": {"type": "string", "enum": ["news", "market", "financial_report", "competitor"]},
                                            "justification": {"type": "string"}
                                        },
                                        "required": ["factor", "source", "justification"]
                                    }
                                }
                            },
                            "required": ["category_score", "severity", "risk_factors"]
                        },
                        "valuation_risk": {
                            "type": "object",
                            "properties": {
                                "category_score": {"type": ["integer", "null"], "minimum": 0, "maximum": 100},
                                "severity": {"type": ["string", "null"], "enum": ["Low", "Medium", "High", "null"]},
                                "risk_factors": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "factor": {"type": "string"},
                                            "source": {"type": "string", "enum": ["news", "market", "financial_report", "competitor"]},
                                            "justification": {"type": "string"}
                                        },
                                        "required": ["factor", "source", "justification"]
                                    }
                                }
                            },
                            "required": ["category_score", "severity", "risk_factors"]
                        }
                    },
                    "required": ["market_risk", "company_risk", "financial_risk", "valuation_risk"]
                },
                "overall_risk_score": {"type": "integer", "minimum": 0, "maximum": 100},
                "overall_severity": {"type": "string", "enum": ["Low", "Medium", "High"]},
                "risk_explanation": {"type": "string"},
                "confidence": {"type": "string", "enum": ["High", "Medium", "Low"]}
            },
            "required": [
                "agent", "company", "generated_at", "categories",
                "overall_risk_score", "overall_severity", "risk_explanation", "confidence"
            ]
        }


# Synchronous wrapper for testing
def run_risk_agent_sync(
    llm_provider,
    company: str,
    context: Dict[str, Any] = None,
) -> WorkerResponse:
    """Synchronous wrapper for the RiskAgent for testing."""
    import asyncio
    agent = RiskAgent(llm_provider=llm_provider)
    return asyncio.run(agent.run(company, context))