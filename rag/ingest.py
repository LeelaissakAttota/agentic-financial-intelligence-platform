"""
Document processing workflow for annual reports / 10-K / 10-Q filings.
See docs/AGENT_PROMPTS.md (Financial Report RAG Agent design note) for
the full rationale.

Workflow:
  1. LOAD          pypdf extracts text per page, preserving page numbers.
  2. SECTION-TAG    Detect standard section headers (Item 1A. Risk
                    Factors, Item 7. MD&A, Item 8. Financial Statements,
                    Balance Sheet, Income Statement, Cash Flow
                    Statement, Notes to Financial Statements).
  3. CHUNK          ~800 tokens, ~100 token overlap. EXCEPTION: financial
                    statement tables are kept as one chunk per table,
                    never split mid-row.
  4. TAG METADATA   company, ticker, doc_type, fiscal_year,
                    fiscal_quarter, section, page_number, chunk_id.
  5. EMBED + STORE  see embeddings.py / vector_store.py.

TODO (Day 4 of docs/ROADMAP.md).
"""

from typing import Literal, Optional


def ingest_document(
    path: str,
    company: str,
    ticker: str,
    doc_type: Literal["10-K", "10-Q", "annual_report"],
    fiscal_year: str,
    fiscal_quarter: Optional[int] = None,
) -> int:
    """Load, section-tag, chunk, embed, and store a filing.
    Returns number of chunks ingested."""
    raise NotImplementedError


def detect_section(page_text: str) -> str:
    """Regex/heading-pattern based section detector.
    Returns one of: 'Business', 'Risk Factors', 'MD&A',
    'Income Statement', 'Balance Sheet', 'Cash Flow Statement',
    'Notes to Financial Statements', 'Other'."""
    raise NotImplementedError


def is_table_chunk(page_text: str) -> bool:
    """Heuristic check so table-like content is never split mid-row."""
    raise NotImplementedError
