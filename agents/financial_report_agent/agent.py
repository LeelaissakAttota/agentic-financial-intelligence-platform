"""
Financial Report RAG Agent Implementation.

Analyzes financial statements using RAG to answer structured financial questions.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from llm.base_client import BaseLLMClient
from llm.json_utils import extract_json
from llm.model_registry import resolve_model, Complexity

from .schemas import (
    FinancialReportInput,
    FinancialReportOutput,
    DocumentContext,
    Finding,
    RetrievedChunk,
)
from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from .exceptions import (
    FinancialReportAgentError,
    FinancialReportInputError,
    FinancialReportLLMError,
    FinancialReportValidationError,
)
from agents.manager_agent.schemas import WorkerResponse
from agents.manager_agent.manager import BaseWorkerAgent

logger = logging.getLogger(__name__)


class FinancialReportAgent(BaseWorkerAgent):
    """Financial Report RAG Agent - Analyzes financial statements using RAG."""

    def __init__(
        self,
        llm_provider,
    ):
        """
        Initialize the Financial Report Agent.

        Args:
            llm_provider: LLM provider for generating responses
        """
        super().__init__(agent_name="financial_report_agent")
        self.llm_provider = llm_provider

    async def run(
        self,
        company: str,
        context: Dict[str, Any] = None,
    ) -> WorkerResponse:
        """
        Generate a financial report analysis for a company.

        Args:
            company: Company name or ticker symbol
            context: Optional context with additional parameters:
                - ticker: Stock ticker symbol (defaults to company)
                - question_set: List of question keys to answer (defaults to standard set)
                - fiscal_year: Optional fiscal year filter
                - fiscal_quarter: Optional fiscal quarter filter

        Returns:
            WorkerResponse with FinancialReportOutput data
        """
        try:
            # Extract parameters from context with defaults
            context = context or {}
            ticker = context.get("ticker", company)
            question_set = context.get("question_set", [
                "revenue_trends",
                "profitability",
                "liquidity",
                "solvency",
                "cash_flow",
                "growth_prospects",
                "risk_factors",
                "management_discussion"
            ])
            fiscal_year = context.get("fiscal_year")
            fiscal_quarter = context.get("fiscal_quarter")

            # Validate input
            if not company or not ticker:
                raise FinancialReportInputError("Company and ticker are required")
            if not question_set:
                raise FinancialReportInputError("Question set cannot be empty")

            # Import here to avoid circular imports
            from rag.retriever import retrieve
            from rag.vector_store import create_vector_store

            # Build retrieval query from first question
            primary_question = question_set[0] if question_set else "financial analysis"

            # Create vector store for retrieval using default config
            # Defaults to persist_dir="./data/processed/chroma" (resolves to /app/data/processed/chroma in container)
            # and collection_name="financial_reports"
            store = create_vector_store(None)

            # Retrieve relevant chunks for the question set
            retrieved_chunks = retrieve(
                store,
                question_key=question_set[0],
                question_text=f"Financial analysis for {company} ({ticker})",
                fiscal_year=fiscal_year,
                fiscal_quarter=fiscal_quarter,
                top_k=8,
                final_k=4
            )

            # Convert to RetrievedChunk schema
            retrieved_chunks_data = []
            for chunk in retrieved_chunks:
                retrieved_chunks_data.append(RetrievedChunk(
                    chunk_id=chunk.get("chunk_id", ""),
                    text=chunk.get("document", ""),
                    doc_type=chunk.get("metadata", {}).get("doc_type", "10-K"),
                    fiscal_year=chunk.get("metadata", {}).get("fiscal_year") or "",
                    fiscal_quarter=chunk.get("metadata", {}).get("fiscal_quarter"),
                    section=chunk.get("metadata", {}).get("section") or "",
                    page_number=chunk.get("metadata", {}).get("page_number") or 0,
                    similarity_score=chunk.get("score") or 0.0
                ))

            # Build input
            input_data = FinancialReportInput(
                company=company,
                ticker=ticker,
                question_set=question_set,
                retrieved_chunks=retrieved_chunks_data
            )

            # Build context from retrieved chunks
            context_text = self._format_context(input_data)
            user_prompt = USER_PROMPT_TEMPLATE.format(
                company=company,
                ticker=ticker,
                question_set="\n".join(f"- {q}" for q in question_set),
                context=context_text
            )

            # Define response schema for structured output
            response_schema = {
                "type": "object",
                "properties": {
                    "findings": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string"},
                                "chunk_id": {"type": ["string", "null"]},
                                "conflict_note": {"type": ["string", "null"]}
                            },
                            "required": ["value", "chunk_id"]
                        }
                    },
                    "document_context": {
                        "type": "object",
                        "properties": {
                            "doc_types_used": {"type": "array", "items": {"type": "string"}},
                            "fiscal_year": {"type": ["string", "null"]},
                            "fiscal_quarter": {"type": ["integer", "null"]}
                        },
                        "required": ["doc_types_used", "fiscal_year", "fiscal_quarter"]
                    },
                    "confidence": {"type": "string", "enum": ["High", "Medium", "Low"]}
                },
                "required": ["findings", "document_context", "confidence"]
            }

            # Resolve model from registry
            resolution = resolve_model("financial_report_agent", "complex")
            model = resolution.model

            # Call LLM with structured output
            llm_result = await self.llm_provider.agenerate_json(
                system_prompt=SYSTEM_PROMPT,
                user_message=user_prompt,
                response_schema=response_schema,
                model=model
            )

            # Parse and validate output
            content = llm_result.get("content", {})
            usage = llm_result.get("usage")

            # Validate that required fields are present
            if "findings" not in content:
                raise FinancialReportValidationError("LLM response missing required 'findings' field")
            if "document_context" not in content:
                raise FinancialReportValidationError("LLM response missing required 'document_context' field")
            if "confidence" not in content:
                raise FinancialReportValidationError("LLM response missing required 'confidence' field")

            # Build findings
            findings = {}
            for question_key, finding_data in content.get("findings", {}).items():
                findings[question_key] = Finding(
                    value=finding_data.get("value", "not found in provided document"),
                    chunk_id=finding_data.get("chunk_id"),
                    conflict_note=finding_data.get("conflict_note")
                )

            # Build document context
            doc_context_data = content.get("document_context", {})
            doc_types = doc_context_data.get("doc_types_used", [])
            if not doc_types and hasattr(input_data, 'retrieved_chunks'):
                doc_types = list(set(chunk.doc_type for chunk in input_data.retrieved_chunks))

            document_context = DocumentContext(
                doc_types_used=doc_types,
                fiscal_year=doc_context_data.get("fiscal_year"),
                fiscal_quarter=doc_context_data.get("fiscal_quarter")
            )

            # Build output
            output = FinancialReportOutput(
                company=company,
                document_context=document_context,
                findings=findings,
                confidence=content.get("confidence", "Medium"),
                generated_at=datetime.utcnow()
            )

            return WorkerResponse(
                status="success",
                data=output.model_dump(),
                usage=usage.to_dict() if usage and hasattr(usage, 'to_dict') else usage
            )

        except FinancialReportAgentError as e:
            logger.error(f"FinancialReportAgent failed: {e}")
            return WorkerResponse(
                status="error",
                error=str(e),
                data=None,
                usage=None
            )
        except Exception as e:
            logger.error(f"FinancialReportAgent failed: {e}")
            return WorkerResponse(
                status="error",
                error=f"Financial report agent failed: {e}",
                data=None,
                usage=None
            )

    def _format_context(self, input_data: FinancialReportInput) -> str:
        """Format retrieved chunks into context text for the prompt."""
        if not input_data.retrieved_chunks:
            return "No document excerpts available."

        context_parts = []
        for chunk in input_data.retrieved_chunks:
            context_parts.append(
                f"[Chunk {chunk.chunk_id}] "
                f"Doc: {chunk.doc_type}, "
                f"Year: {chunk.fiscal_year}, "
                f"Quarter: {chunk.fiscal_quarter or 'N/A'}, "
                f"Section: {chunk.section or 'N/A'}, "
                f"Page: {chunk.page_number or 'N/A'}\n"
                f"{chunk.text}\n"
            )

        return "\n---\n".join(context_parts)


# Synchronous wrapper for testing
def run_financial_report_agent_sync(
    llm_provider,
    company: str,
    context: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Synchronous wrapper for the FinancialReportAgent for testing."""
    import asyncio
    agent = FinancialReportAgent(llm_provider=llm_provider)
    return asyncio.run(agent.run(company, context))