# PHASE 6 — Development Roadmap (Testing Phase, 5 Days)

## Day 1 — Setup and architecture testing
- Scaffold folder structure (this deliverable)
- Set up venv, install `requirements.txt`
- Configure `.env`, verify `config/settings.py` loads
- Bring up PostgreSQL + ChromaDB via Docker
- Write and pass `tests/test_settings.py` (config loads/fails correctly)
- **Exit criteria:** `pytest -m "not integration"` runs (even with 0
  real tests yet) and the environment checklist in `SETUP_GUIDE.md` is
  fully green.

## Day 2 — Claude connection testing
- Implement `llm/claude_client.py` (thin wrapper, retries, structured
  output)
- Write `tests/test_claude_connection.py` — one live "ping" call
- Validate both Sonnet and Haiku model strings resolve and return
  expected JSON-mode output
- Log token usage/cost per call to confirm logging pipeline works
- **Exit criteria:** One successful real Claude API call end-to-end,
  cost logged, response schema-validated.

## Day 3 — Agent communication testing
- Implement stub `agent.py` for all 8 agents (System prompt wired,
  Pydantic schema enforced, mocked upstream inputs accepted)
- Implement `manager_agent` fan-out/merge logic in LangGraph
- Write per-agent unit tests with mocked LLM responses
- Write `tests/test_manager_agent.py` verifying merge + `data_unavailable`
  fallback behavior
- **Exit criteria:** Manager successfully orchestrates all 7 mocked
  worker agents and produces a valid merged JSON.

## Day 4 — RAG testing
- Implement `rag/ingest.py`, `rag/embeddings.py`, `rag/vector_store.py`,
  `rag/retriever.py`
- Ingest one fixture 10-K excerpt (or NVIDIA's real public 10-K) into
  ChromaDB
- Write `tests/test_rag_pipeline.py` — fixed question set → assert
  correct chunk retrieval
- Wire `financial_report_agent` to use real retrieval instead of mocks
- **Exit criteria:** Financial Report Agent answers all 6 fixed
  questions from Phase 2's schema, citing correct `chunk_id`s, with at
  least one correctly-returned "not found in provided document".

## Day 5 — Report generation testing
- Wire `main.py` end-to-end: user query → Manager → all agents (mix of
  real Claude calls + real RAG) → merged report → written to
  `data/reports/`
- Build minimal `dashboard/app.py` to trigger a run and view sections
- Run the full Phase 5 test plan against NVIDIA, Tesla, and Apple
- Run the cross-run regression check
- Write up findings in `docs/TEST_RESULTS.md` (gaps, flaky sections,
  cost per run) as the handoff artifact into the production phase
- **Exit criteria:** All 3 companies produce valid, distinct,
  schema-complete reports; regression check passes; cost-per-run is
  known and documented.

---

### Note on Trading System integration (future, not this phase)
Keep `investment_summary_agent`'s output schema stable — that's the
only contract the Multi-Market Agentic AI Trading System needs to
consume later (e.g., as a qualitative overlay next to its existing
5-agent Strategy Council vote). No coupling is built in this phase;
this is just why the schema is kept deliberately clean and versioned.
