"""
ChromaDB wrapper. One persistent collection per ticker:
`financial_docs_<ticker>`, with metadata filterable by doc_type,
fiscal_year, fiscal_quarter, and section (see ingest.py for the
metadata schema this collection expects).

TODO (Day 4 of docs/ROADMAP.md).
"""

from typing import Optional


class VectorStore:
    def __init__(self, persist_dir: str, ticker: str):
        self.persist_dir = persist_dir
        self.collection_name = f"financial_docs_{ticker}"

    def add(self, chunks: list[dict]) -> None:
        """Each chunk dict: {chunk_id, text, embedding, metadata}."""
        raise NotImplementedError

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 8,
        metadata_filter: Optional[dict] = None,
    ) -> list[dict]:
        """metadata_filter e.g. {"fiscal_year": "2026", "fiscal_quarter": 3}"""
        raise NotImplementedError
