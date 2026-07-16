# Demo Video Script - Financial Research Agent

## Video Overview
- **Duration:** 4-5 minutes
- **Target Audience:** AI Engineers, Quantitative Researchers, Hiring Managers
- **Tone:** Professional, technical, demonstrating real capability
- **Format:** Screen recording + narration + animations

---

## Scene Breakdown

### Scene 1: Problem Introduction (30 seconds)
**Visual:** Split screen showing "Traditional Research" vs "Agentic AI Research"
- Left side: Analyst drowning in PDFs, multiple browser tabs, Excel sheets
- Right side: Clean terminal/dashboard with "Analyze NVIDIA" command
- Timeline overlay: "Traditional: 4-8 hours" → "Agentic: 3-5 minutes"

**Narration:**
> "Financial research is fundamentally broken. Analysts spend 80% of their time collecting data and only 20% analyzing it. They manually parse hundreds of pages of SEC filings, juggle dozens of browser tabs, and stitch together fragmented insights. What if an AI could do the collection, synthesis, and drafting autonomously—leaving the analyst to focus purely on judgment?"

**On-screen text:**
- ❌ Manual data collection: 4-8 hours
- ❌ Fragmented sources, no audit trail
- ❌ Knowledge lost after project ends
- ✅ Autonomous agents: 3-5 minutes
- ✅ Citation-backed, auditable
- ✅ Persistent organizational memory

---

### Scene 2: Architecture Explanation (60 seconds)
**Visual:** Animated architecture diagram (from README) building layer by layer
1. User Query enters at top
2. Planner Agent appears, creates DAG
3. Three parallel branches: Data, Web, Document agents
4. Converge at Analysis Agent
4. RAG Knowledge Agent enriches
5. Report Generation produces output
6. Memory Agent stores insights

**Narration:**
> "The system uses a planner-executor architecture built on LangGraph. A planner agent decomposes your research request into a directed acyclic graph of tasks. Three specialized agents execute in parallel: a Financial Data agent hitting APIs and databases, a Web Research agent searching and extracting credible sources, and a Document Intelligence agent parsing PDFs—SEC filings, earnings transcripts, analyst reports—into a vector store. Their findings converge at the Analysis Agent, which performs quantitative reasoning. A RAG agent retrieves grounded evidence for every claim. Finally, a Report Generator produces a professional, citation-backed report, and a Memory Agent stores everything for future queries."

**On-screen annotations:**
- 🔄 Parallel execution = 3x speedup
- 🔍 RAG grounding = zero hallucinations
- 🧠 Memory = compounding intelligence
- 📋 Citations = audit-ready

---

### Scene 3: Live Demo - User Query (45 seconds)
**Visual:** Streamlit dashboard recording
1. User types: "Analyze NVIDIA's competitive moat in AI accelerators"
2. Clicks "Run Research"
3. Real-time agent status panel shows: Planning → Data Agent (running) → Web Agent (running) → Document Agent (running) → Analysis → RAG → Report

**Narration:**
> "Let's see it in action. I'll ask for a competitive analysis of NVIDIA's AI accelerator moat. The planner immediately creates a research plan. Notice how all three collection agents run in parallel—market data, web intelligence, and SEC filings. This parallelism alone cuts research time by 60%."

**On-screen highlights:**
- ✨ Natural language input
- 📋 Auto-generated research plan
- ⚡ Parallel agent execution
- 📊 Real-time progress monitoring

---

### Scene 4: Agents Collecting Information (60 seconds)
**Visual:** Split view showing each agent's live output
- **Data Agent:** Real-time price, fundamentals, peer comparison table building
- **Web Agent:** Search results with credibility scores (Tier 1/2/3 badges)
- **Document Agent:** PDF parsing progress, section extraction (Risk Factors, MD&A, Financial Statements)

**Narration:**
> "Each agent specializes. The Data Agent pulls real-time fundamentals, technical indicators, and builds peer comparison matrices automatically. The Web Agent searches with credibility-weighted queries—it prioritizes SEC filings and tier-1 financial press over blogs. The Document Agent is parsing NVIDIA's latest 10-K and earnings transcripts, extracting sections like Risk Factors, MD&A, and segment financials, chunking them, and embedding them into our vector store."

**On-screen callouts:**
- 📊 200+ data points auto-collected
- 🏷️ Source credibility scoring
- 📄 50+ document chunks indexed
- 🔍 Semantic search ready

---

### Scene 5: RAG Retrieval & Analysis (45 seconds)
**Visual:** RAG agent in action
- Query: "What are NVIDIA's key competitive advantages in AI chips?"
- Vector search animation → Re-ranking → Top 10 chunks selected
- Analysis Agent: DCF model building, margin trend analysis, moat assessment
- Evidence assembly: Each claim linked to source chunk with page number

**Narration:**
> "Now the RAG agent retrieves the most relevant evidence. It doesn't just do keyword search—it uses BGE-M3 embeddings for semantic similarity, then a cross-encoder re-ranker for precision. The Analysis Agent builds a DCF model, analyzes gross margin trends over 10 quarters, and assesses moat durability across switching costs, network effects, and IP. Every quantitative claim and qualitative assessment is tied to a specific source chunk with page references."

**On-screen:**
- 🔍 Semantic + keyword hybrid search
- 🎯 Cross-encoder re-ranking
- 📈 Auto-generated DCF + comps
- 📎 Inline citations with page refs

---

### Scene 6: Final Report Generation (45 seconds)
**Visual:** Report viewer showing final output
- Professional PDF with cover page, table of contents
- Executive Summary with key thesis bullets
- Valuation section with DCF, comps, football field chart
- Risk matrix with probability/impact
- Appendix with full citations and source links
- Export options: PDF, HTML, Markdown, PowerPoint

**Narration:**
> "The Report Generator assembles everything into a publication-ready equity research report. Notice the executive summary with investment thesis bullets. The valuation section has a DCF model with sensitivity table, comparable company analysis, and a football field chart. Every number has an inline citation you can click to see the source document. The risk matrix quantifies probability and impact. And it exports to PDF, HTML, Markdown, or PowerPoint for your investment committee."

**On-screen:**
- 📄 25-page professional report
- 📎 47 inline citations
- 📊 Auto-generated charts & tables
- 📥 Multi-format export

---

### Scene 7: Memory & Future Queries (30 seconds)
**Visual:** Memory dashboard showing stored research
- Previous NVIDIA research appears in history
- New query: "How does AMD compare?"
- System retrieves relevant prior chunks, shows "Based on previous research..."
- Demonstrates compounding knowledge

**Narration:**
> "But the real power is what happens next. The Memory Agent has stored the entire research artifact—findings, citations, reasoning traces. When I ask for an AMD comparison, the system doesn't start from scratch. It retrieves relevant context from the NVIDIA research, identifies overlapping sources, and builds on prior work. This compounding intelligence means your 10th report is faster and deeper than your first."

---

### Scene 8: Future Roadmap & Closing (30 seconds)
**Visual:** Roadmap timeline animation
- Q1: Real-time monitoring, Voice interface
- Q2: Multi-company comparison, Portfolio integration
- Q3: Team collaboration, Custom agents
- Q4: Predictive models, Self-improving agents

**Narration:**
> "This is just the beginning. Our roadmap includes real-time market monitoring with automated alerts, voice-driven research, portfolio-level intelligence, and eventually self-improving agents that learn from every analyst interaction. The Financial Research Agent isn't just a tool—it's an AI research analyst that gets smarter with every report."

**Final screen:**
```
FINANCIAL RESEARCH AGENT
github.com/yourusername/financial-research-agent

⭐ Star if useful  •  🐛 Report issues  •  💡 Contribute
```

---

## Recording Tips

### Technical Setup
- **Resolution:** 1920x1080 (scale UI to 150% for readability)
- **Frame Rate:** 30 fps minimum
- **Audio:** External microphone (Blue Yeti or similar)
- **Screen Recorder:** OBS Studio (free) or Camtasia

### Narration Best Practices
- Record in quiet environment
- Speak at 150-160 words per minute
- Pause 2 seconds between scenes for editing
- Do 2-3 takes per scene, pick best

### Post-Production
- Add subtle zoom/pan on key UI elements
- Use 0.5s crossfade transitions
- Add subtle background music (low volume, corporate/tech)
- Include captions for accessibility
- Add GitHub URL watermark in corner

### File Output
- **Format:** MP4 (H.264)
- **Bitrate:** 10-15 Mbps
- **Upload:** YouTube (unlisted or public), embed in README

---

## Alternative: Short Demo (60 seconds)

For social media / quick overview:

| Time | Content |
|------|---------|
| 0-5s | Problem: "Research takes hours" |
| 5-15s | Solution: Agent architecture animation |
| 15-35s | Live demo: Query → Parallel agents → Report |
| 35-50s | RAG citations + Memory demo |
| 50-60s | GitHub link + Star CTA |

---

## Demo Data Preparation

Prepare these for consistent recording:
```python
# companies_demo.py
DEMO_COMPANIES = [
    {"ticker": "NVDA", "name": "NVIDIA", "sector": "Semiconductors"},
    {"ticker": "AAPL", "name": "Apple", "sector": "Technology"},
    {"ticker": "TSLA", "name": "Tesla", "sector": "Automotive"},
]

DEMO_QUERIES = [
    "Analyze NVIDIA's competitive moat in AI accelerators",
    "Compare Apple's services revenue growth vs hardware",
    "Assess Tesla's FSD progress and regulatory risks",
]
```

Pre-cache API responses for demo to avoid rate limits and ensure consistent timing.