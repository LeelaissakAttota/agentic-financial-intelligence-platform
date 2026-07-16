"""
Retrieval workflow used by financial_report_agent. See docs/AGENT_PROMPTS.md
(Financial Report RAG Agent design note) for the full rationale.

Workflow:
  1. Embed the question.
  2. Optional metadata pre-filter (doc_type/fiscal_year/fiscal_quarter)
     when the question specifies a period.
  3. Similarity search, top_k=8 candidates.
  4. Lightweight re-rank: boost chunks whose section tag matches the
     question category (e.g., revenue questions -> boost "Income
     Statement" / "MD&A" chunks).
  5. Truncate to top 4 after re-rank.
"""

from typing import Optional

from .vector_store import VectorStore
from .embeddings import create_embedding_service, create_reranker_service

# Maps question keys (see docs/AGENT_PROMPTS.md question_set) to the
# section(s) that should be boosted during re-rank.
SECTION_BOOST_MAP = {
    "revenue_growth_yoy": ["Income Statement", "MD&A"],
    "gross_margin": ["Income Statement"],
    "net_income": ["Income Statement"],
    "free_cash_flow": ["Cash Flow Statement"],
    "segment_breakdown": ["Notes to Financial Statements"],
    "debt_levels": ["Balance Sheet"],
}


def retrieve(
    store: "VectorStore",
    question_key: str,
    question_text: str,
    fiscal_year: Optional[str] = None,
    fiscal_quarter: Optional[int] = None,
    top_k: int = 8,
    final_k: int = 4,
) -> list[dict]:
    """Returns final_k RetrievedChunk-shaped dicts, section-boosted and
    truncated, ready to pass to the Financial Report RAG Agent."""
    # Initialize embedding and reranker services with proper config for container paths
    embedding_config = {
        "embedding": {
            "cache_dir": "/app/data/processed/embedding_cache",
            "cache_enabled": True
        }
    }
    embedding_service = create_embedding_service(embedding_config)
    reranker_service = create_reranker_service()
    
    # Build metadata filter
    metadata_filter = {}
    if fiscal_year:
        metadata_filter["fiscal_year"] = fiscal_year
    if fiscal_quarter:
        metadata_filter["fiscal_quarter"] = fiscal_quarter
    
    # Embed the question
    query_embedding = embedding_service.embed_query(question_text)
    
    # Perform vector search
    search_results = store.search(
        query_embedding=query_embedding,
        n_results=top_k,
        where=metadata_filter if metadata_filter else None,
    )
    
    # Convert to chunk dicts
    chunks = []
    for result in search_results.results:
        chunk_dict = {
            "chunk_id": result.id,
            "document": result.document,
            "metadata": result.metadata,
            "score": result.score,
        }
        chunks.append(chunk_dict)
    
    # Section-aware re-ranking
    boost_sections = SECTION_BOOST_MAP.get(question_key, [])
    if boost_sections:
        for chunk in chunks:
            section = chunk.get("metadata", {}).get("section", "")
            if any(boost_section.lower() in section.lower() for boost_section in boost_sections):
                chunk["score"] = chunk["score"] * 1.2  # Boost score by 20%
    
    # Sort by score and take top final_k
    chunks.sort(key=lambda x: x.get("score", 0), reverse=True)
    chunks = chunks[:final_k]
    
    # Convert to RetrievedChunk-shaped dicts
    result_chunks = []
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        result_chunks.append({
            "chunk_id": chunk.get("chunk_id", ""),
            "document": chunk.get("document", ""),
            "metadata": metadata,
            "score": chunk.get("score", 0.0),
        })
    
    return result_chunks