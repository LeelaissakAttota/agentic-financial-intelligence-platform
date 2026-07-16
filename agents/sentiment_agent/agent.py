"""Sentiment Analysis Agent - Analyzes market sentiment from news, social, and analyst sources."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from llm.base_client import BaseLLMClient
from llm.json_utils import extract_json
from llm.model_registry import resolve_model, Complexity

from .schemas import (
    SentimentAgentInput,
    SentimentAgentOutput,
    NewsItemIn,
    SocialItemIn,
    AnalystOpinionIn,
    SentimentDistribution,
    BySource,
    DivergenceFlag,
)
from .prompts import SYSTEM_PROMPT
from .exceptions import (
    SentimentAgentError,
    SentimentAgentInputError,
    SentimentAgentLLMError,
    SentimentAgentValidationError,
)
from agents.manager_agent.schemas import WorkerResponse
from agents.manager_agent.manager import BaseWorkerAgent

logger = logging.getLogger(__name__)


class SentimentAgent(BaseWorkerAgent):
    """Sentiment Analysis Agent for financial research."""

    def __init__(
        self,
        llm_provider,
    ):
        """
        Initialize the Sentiment Agent.

        Args:
            llm_provider: LLM provider for generating responses
        """
        super().__init__(agent_name="sentiment_agent")
        self.llm_provider = llm_provider

    async def run(
        self,
        company: str,
        context: Dict[str, Any] = None,
    ) -> WorkerResponse:
        """
        Execute the sentiment analysis workflow.

        Args:
            company: Company name to analyze
            context: Optional context with sentiment data from other agents
                Expected keys:
                - news_items: List of news articles with impact
                - social_items: List of social media sentiment
                - analyst_opinions: List of analyst opinions

        Returns:
            WorkerResponse with sentiment analysis results
        """
        try:
            # Validate input
            if not company:
                raise SentimentAgentInputError("Company name is required")

            # Extract sentiment data from context
            news_items = context.get("news_items", []) if context else []
            social_items = context.get("social_items", []) if context else []
            analyst_opinions = context.get("analyst_opinions", []) if context else []

            # Build input data
            input_data = SentimentAgentInput(
                company=company,
                as_of_date=datetime.utcnow().strftime("%Y-%m-%d"),
                news_items=[NewsItemIn(**item) for item in news_items],
                social_items=[SocialItemIn(**item) for item in social_items],
                analyst_opinions=[AnalystOpinionIn(**item) for item in analyst_opinions],
            )

            # Build user prompt
            user_prompt = self._build_user_prompt(input_data)

            # Define response schema for structured output
            response_schema = self._get_response_schema()

            # Resolve model from registry
            resolution = resolve_model("sentiment_agent", "simple")
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
                raise SentimentAgentValidationError("LLM returned empty content")

            # Add missing required fields from input data
            content["company"] = company
            content["generated_at"] = datetime.utcnow().isoformat()

            # Validate output schema
            try:
                output = SentimentAgentOutput(**content)
            except Exception as e:
                logger.error(f"Output validation failed: {e}")
                raise SentimentAgentValidationError(f"Output validation failed: {str(e)}")

            # Return in WorkerResponse format
            return WorkerResponse(
                status="success",
                data=output.model_dump(),
                usage=usage.to_dict() if usage and hasattr(usage, 'to_dict') else usage
            )

        except SentimentAgentError as e:
            logger.error(f"SentimentAgent failed: {e}")
            return WorkerResponse(
                status="error",
                error=str(e),
                data=None,
                usage=None
            )
        except Exception as e:
            logger.error(f"SentimentAgent failed: {e}")
            return WorkerResponse(
                status="error",
                error=f"Sentiment agent failed: {str(e)}",
                data=None,
                usage=None
            )

    def _build_user_prompt(self, input_data: SentimentAgentInput) -> str:
        """Build the user prompt for the LLM."""
        parts = [
            f"Analyze sentiment for {input_data.company} as of {input_data.as_of_date}.",
            "",
        ]

        # News section
        if input_data.news_items:
            parts.append("=== NEWS ITEMS ===")
            for item in input_data.news_items:
                parts.append(f"- {item.title} (Impact: {item.impact}, Date: {item.date})")
            parts.append("")

        # Social section
        if input_data.social_items:
            parts.append("=== SOCIAL MEDIA ===")
            for item in input_data.social_items:
                parts.append(f"- {item.platform}: {item.text_summary} (Sentiment: {item.sentiment}, Date: {item.date})")
            parts.append("")

        # Analyst section
        if input_data.analyst_opinions:
            parts.append("=== ANALYST OPINIONS ===")
            for item in input_data.analyst_opinions:
                parts.append(f"- {item.firm}: {item.rating} - {item.note_summary} (Date: {item.date})")
            parts.append("")

        if not input_data.news_items and not input_data.social_items and not input_data.analyst_opinions:
            parts.append("No sentiment data available from any source.")
            parts.append("")

        parts.append("Provide your analysis in the required JSON format.")

        return "\n".join(parts)

    def _get_response_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for structured LLM output."""
        return {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "enum": ["sentiment_agent"]},
                "company": {"type": "string"},
                "generated_at": {"type": "string", "format": "date-time"},
                "by_source": {
                    "type": "object",
                    "properties": {
                        "news": {
                            "type": "object",
                            "properties": {
                                "positive": {"type": "number", "minimum": 0, "maximum": 1},
                                "negative": {"type": "number", "minimum": 0, "maximum": 1},
                                "neutral": {"type": "number", "minimum": 0, "maximum": 1}
                            },
                            "required": ["positive", "negative", "neutral"]
                        },
                        "social": {
                            "type": "object",
                            "properties": {
                                "positive": {"type": "number", "minimum": 0, "maximum": 1},
                                "negative": {"type": "number", "minimum": 0, "maximum": 1},
                                "neutral": {"type": "number", "minimum": 0, "maximum": 1}
                            },
                            "required": ["positive", "negative", "neutral"]
                        },
                        "analyst_opinions": {
                            "type": "object",
                            "properties": {
                                "positive": {"type": "number", "minimum": 0, "maximum": 1},
                                "negative": {"type": "number", "minimum": 0, "maximum": 1},
                                "neutral": {"type": "number", "minimum": 0, "maximum": 1}
                            },
                            "required": ["positive", "negative", "neutral"]
                        }
                    },
                    "required": ["news", "social", "analyst_opinions"]
                },
                "overall": {
                    "type": "object",
                    "properties": {
                        "positive": {"type": "number", "minimum": 0, "maximum": 1},
                        "negative": {"type": "number", "minimum": 0, "maximum": 1},
                        "neutral": {"type": "number", "minimum": 0, "maximum": 1}
                    },
                    "required": ["positive", "negative", "neutral"]
                },
                "overall_market_emotion": {
                    "type": "string",
                    "enum": ["Euphoric", "Optimistic", "Cautiously Optimistic", "Neutral", "Cautious", "Pessimistic", "Fearful"]
                },
                "emotion_rationale": {"type": "string"},
                "drivers": {"type": "array", "items": {"type": "string"}},
                "divergence_flag": {
                    "type": "object",
                    "properties": {
                        "detected": {"type": "boolean"},
                        "description": {"type": "string"}
                    },
                    "required": ["detected", "description"]
                },
                "confidence": {"type": "string", "enum": ["High", "Medium", "Low"]}
            },
            "required": [
                "agent", "company", "generated_at", "by_source", "overall",
                "overall_market_emotion", "emotion_rationale", "drivers",
                "divergence_flag", "confidence"
            ]
        }


# Synchronous wrapper for testing
def run_sentiment_agent_sync(
    llm_provider,
    company: str,
    context: Dict[str, Any] = None,
) -> WorkerResponse:
    """Synchronous wrapper for the SentimentAgent for testing."""
    import asyncio
    agent = SentimentAgent(llm_provider=llm_provider)
    return asyncio.run(agent.run(company, context))