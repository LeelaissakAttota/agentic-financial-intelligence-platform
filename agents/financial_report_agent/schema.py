"""Pydantic schemas for the Financial Report RAG Agent's input/output
contract. See docs/AGENT_PROMPTS.md and the design note for the full
JSON shape and worked testing examples."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    doc_type: Literal["10-K", "10-Q", "annual_report"]
    fiscal_year: str
    fiscal_quarter: Optional[int] = None
    section: str
    page_number: int
    similarity_score: float


class FinancialReportInput(BaseModel):
    company: str
    ticker: str
    question_set: list[str]
    retrieved_chunks: list[RetrievedChunk]


class DocumentContext(BaseModel):
    doc_types_used: list[Literal["10-K", "10-Q", "annual_report"]]
    fiscal_year: Optional[str] = None
    fiscal_quarter: Optional[int] = None


class Finding(BaseModel):
    value: str
    chunk_id: Optional[str] = None
    conflict_note: Optional[str] = None


class FinancialReportOutput(BaseModel):
    agent: str = "financial_report_agent"
    company: str
    generated_at: datetime
    document_context: DocumentContext
    findings: dict[str, Finding]
    confidence: Literal["High", "Medium", "Low"]
