# PHASE 5 — Testing Plan

General validation criteria applied to every test company:
- All 8 report sections present in the merged output (no silent drops)
- Every numeric market figure traces back to the raw input, never invented
- Every RAG-sourced claim carries a `chunk_id`
- `investment_summary.disclaimer` is always present
- Total end-to-end run completes and writes a report file to `data/reports/`
- No unhandled exceptions; failed sub-agents degrade to `data_unavailable`, not a crash

---

## Test Company 1 — NVIDIA
**Input:** `"Analyze NVIDIA"`

**Agent workflow:**
Manager → resolves ticker `NVDA` → fans out to News, Market, Financial
Report (RAG on a fixture 10-K excerpt), Competitor (AMD, Intel) →
Sentiment (consumes News) → Risk (consumes News+Market+Financial+Competitor)
→ Investment Summary (consumes everything) → Manager merges.

**Expected output:** Full `InvestmentReport` JSON with NVIDIA-specific
narrative referencing AI/data-center chip demand as a likely theme.

**Validation criteria:**
- Competitor table includes AMD and Intel
- Risk list includes at least one "Competitive" category item
- Sentiment score and label are internally consistent (e.g., score > 0 ⇒ label "Positive")

---

## Test Company 2 — Tesla
**Input:** `"Analyze Tesla"`

**Agent workflow:** Same pipeline; Competitor Agent should resolve to
auto/EV peers (e.g., Ford, BYD, Rivian — whichever fixture set is
configured) rather than reusing NVIDIA's competitor set — this is the
key regression check for this test (competitor resolution must be
company-aware, not hardcoded).

**Expected output:** Full report with automotive-sector framing.

**Validation criteria:**
- Competitor names differ from Test 1's competitor names
- Risk Agent surfaces at least one "Regulatory" risk (EV incentives/
  emissions policy is a natural fit for a fixture headline)
- Report generation does not reuse any cached NVIDIA values (cache-key
  correctness check via the `database.AgentRun` table)

---

## Test Company 3 — Apple
**Input:** `"Analyze Apple"`

**Agent workflow:** Same pipeline; this run specifically stress-tests
the Financial Report RAG Agent with a longer fixture 10-K excerpt
(multi-segment revenue breakdown: iPhone/Services/Wearables) to confirm
retrieval picks the correct chunk per question rather than always
returning the first chunk.

**Expected output:** Full report with segment-level financial detail
in `annual_report_analysis`.

**Validation criteria:**
- `segment_breakdown` finding cites a different `chunk_id` than
  `revenue_growth_yoy` (proves retrieval is question-specific, not
  static)
- Investment Summary references at least one specific catalyst tied to
  a named product segment, not a generic statement

---

## Cross-run regression check
After all 3 companies are tested, diff their `AgentRun` DB records and
confirm:
- No two companies share identical `sentiment_score`, `risk` lists, or
  `comparison_table` (a sure sign of a caching/parameter bug)
- Token/cost logs show 3 distinct, plausible totals (not one repeated
  fixed number)
