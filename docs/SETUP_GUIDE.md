# PHASE 4 — Environment Setup Guide

## 1. Python environment
```bash
cd financial_research_agent
python3.12 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 2. API key configuration
```bash
cp .env.example .env
# then edit .env and set:
#   ANTHROPIC_API_KEY=sk-ant-...
```
Verify the config loads correctly:
```bash
python -c "from config.settings import Settings; print(Settings().model_dump())"
```

## 3. Database setup (PostgreSQL via Docker — recommended for testing)
```bash
docker compose up -d postgres chromadb
```
`docker-compose.yml` (to be added at project root) should define:
- `postgres` service (image `postgres:16`, port 5432, uses the `.env` creds)
- `chromadb` service (image `chromadb/chroma`, persisted volume mapped to
  `./data/processed/chroma`)

Run migrations (once `database/models.py` has real tables):
```bash
alembic upgrade head
```

If you'd rather skip Docker for a quick local test, set:
```
POSTGRES_HOST=sqlite   # a lightweight fallback flag your connection.py can check
```
and use a local SQLite file for early testing — same SQLAlchemy models apply.

## 4. Run commands

**End-to-end test run (CLI):**
```bash
python main.py --company "NVIDIA"
```

**Dashboard (debug console):**
```bash
streamlit run dashboard/app.py
```

**API server:**
```bash
uvicorn main:app --reload --port 8000
```

**Run automated tests:**
```bash
pytest -m "not integration"     # fast, mocked, no API cost
pytest -m integration           # real Claude API calls
pytest --cov=agents --cov=rag   # with coverage
```

## 5. Installation sanity checklist
- [ ] `python -c "import anthropic, langgraph, langchain, chromadb, fastapi, streamlit"` runs clean
- [ ] `.env` has a valid `ANTHROPIC_API_KEY`
- [ ] `docker compose ps` shows `postgres` and `chromadb` healthy
- [ ] `pytest -m "not integration"` passes
- [ ] `python main.py --company "NVIDIA"` produces a file in `data/reports/`
