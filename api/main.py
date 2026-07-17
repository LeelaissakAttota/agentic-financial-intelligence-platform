"""
FastAPI application for Financial Research Agent.
Provides REST API for running analyses and retrieving reports.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
import uuid

from config.settings import Settings
from database import (
    init_db,
    get_session,
    get_engine,
    get_company_reports,
    get_report_by_id,
    get_agent_runs_for_report,
    persist_pipeline_result,
)
from main import run as run_pipeline
from agents.manager_agent.manager import ManagerAgent
from agents.manager_agent.schemas import TaskType
from agents.news_agent.news_agent import NewsAgent
from agents.market_agent.market_agent import MarketAgent
from agents.financial_report_agent.agent import FinancialReportAgent
from agents.sentiment_agent.agent import SentimentAgent
from agents.risk_agent.agent import RiskAgent
from agents.competitor_agent.agent import CompetitorAgent
from agents.investment_summary_agent.agent import InvestmentSummaryAgent
from llm.openrouter_client import OpenRouterClient

# Database setup
from database import init_db, get_session, get_engine
from database.models import Company, Report, AgentRun

# Global settings and engine
settings = Settings()
engine = get_engine(settings)

# Database initialization on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    init_db(settings)
    yield
    # Shutdown
    engine.dispose()

app = FastAPI(
    title="Financial Research Agent API",
    description="REST API for AI-powered financial research analysis",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API
class AnalysisRequest(BaseModel):
    """Request to start a financial analysis."""
    company: str = Field(..., description="Company name or ticker symbol")
    ticker: Optional[str] = Field(None, description="Optional ticker symbol")


class AnalysisResponse(BaseModel):
    """Response after starting analysis."""
    analysis_id: str
    company: str
    status: str
    message: str


class AgentResult(BaseModel):
    """Individual agent result."""
    status: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None


class AnalysisStatusResponse(BaseModel):
    """Analysis status response."""
    analysis_id: str
    company: str
    ticker: Optional[str]
    status: str  # pending, running, completed, failed
    results: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ReportSummary(BaseModel):
    """Report summary for history listing."""
    report_id: str
    company_name: str
    ticker: Optional[str]
    generated_at: datetime


class AgentRunSummary(BaseModel):
    """Agent run summary."""
    agent_name: str
    status: str
    tokens_used: Optional[int]
    cost_usd: Optional[float]
    timestamp: datetime


# In-memory analysis store (use Redis in production)
analysis_store: Dict[str, Dict[str, Any]] = {}


async def run_analysis_background(analysis_id: str, company: str, ticker: Optional[str]):
    """Run analysis in background."""
    analysis = analysis_store[analysis_id]
    analysis["status"] = "running"
    analysis["updated_at"] = datetime.utcnow()

    try:
        # Run the pipeline asynchronously
        llm_provider = OpenRouterClient(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )

        # Initialize ManagerAgent
        manager = ManagerAgent(llm_provider=llm_provider)

        # Register all worker agents
        manager.register_worker(TaskType.NEWS_ANALYSIS, NewsAgent(llm_provider=llm_provider))
        manager.register_worker(TaskType.MARKET_DATA, MarketAgent(llm_provider=llm_provider))
        manager.register_worker(TaskType.FINANCIAL_ANALYSIS, FinancialReportAgent(llm_provider=llm_provider))
        manager.register_worker(TaskType.SENTIMENT_ANALYSIS, SentimentAgent(llm_provider=llm_provider))
        manager.register_worker(TaskType.RISK_ANALYSIS, RiskAgent(llm_provider=llm_provider))
        manager.register_worker(TaskType.COMPETITOR_ANALYSIS, CompetitorAgent(llm_provider=llm_provider))
        manager.register_worker(TaskType.INVESTMENT_SUMMARY, InvestmentSummaryAgent(llm_provider=llm_provider))

        # Run the pipeline
        result = await manager.run(company=company, query=ticker)

        # DEBUG: Log result structure
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Manager result type: {type(result)}")
        logger.info(f"Manager result.results type: {type(result.results)}")
        logger.info(f"Manager result.results keys: {list(result.results.keys()) if result.results else 'None'}")
        for k, v in (result.results.items() if result.results else []):
            logger.info(f"  Result {k}: type={type(v)}, keys={list(v.keys()) if isinstance(v, dict) else 'N/A'}")

        # Persist to database using the global engine
        session = get_session(settings)
        try:
            logger.info("About to call persist_pipeline_result")
            persist_pipeline_result(session, result.model_dump())
            logger.info("persist_pipeline_result succeeded")
            session.commit()
        finally:
            session.close()

        analysis["status"] = "completed"
        analysis["results"] = result.model_dump()
        logger.info("result.model_dump() succeeded")
        analysis["metadata"] = {
            "completed_tasks": len([r for r in result.results.values() if isinstance(r, dict) and r.get("status") == "success"]),
            "failed_tasks": len([r for r in result.results.values() if isinstance(r, dict) and r.get("status") == "error"]),
            "total_tasks": len(result.results),
            "execution_time_seconds": 0
        }
        logger.info("Metadata calculation succeeded")
    except Exception as e:
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Analysis failed with error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        analysis["status"] = "failed"
        analysis["error"] = str(e)
    finally:
        analysis["updated_at"] = datetime.utcnow()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "financial-research-agent",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with dependency verification."""
    checks = {
        "api": "healthy",
        "database": "unknown",
        "chromadb": "unknown",
    }

    # Check database using the global engine
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception:
        checks["database"] = "unhealthy"

    # Check ChromaDB
    try:
        import requests
        response = requests.get("http://chromadb:8000/api/v1/heartbeat", timeout=5)
        if response.status_code == 200:
            checks["chromadb"] = "healthy"
        else:
            checks["chromadb"] = "unhealthy"
    except Exception:
        checks["chromadb"] = "unhealthy"

    overall = "healthy" if all(v == "healthy" for v in checks.values()) else "degraded"

    return {
        "status": overall,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/analyze", response_model=AnalysisResponse)
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Start a new financial analysis."""
    analysis_id = str(uuid.uuid4())

    analysis_store[analysis_id] = {
        "analysis_id": analysis_id,
        "company": request.company,
        "ticker": request.ticker,
        "status": "pending",
        "results": None,
        "metadata": None,
        "error": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    # Run in background
    background_tasks.add_task(run_analysis_background, analysis_id, request.company, request.ticker)

    return AnalysisResponse(
        analysis_id=analysis_id,
        company=request.company,
        status="pending",
        message="Analysis started. Poll /api/v1/analyze/{analysis_id} for status."
    )


@app.get("/api/v1/analyze/{analysis_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(analysis_id: str):
    """Get analysis status and results."""
    if analysis_id not in analysis_store:
        raise HTTPException(status_code=404, detail="Analysis not found")

    analysis = analysis_store[analysis_id]
    return AnalysisStatusResponse(**analysis)


@app.get("/api/v1/reports", response_model=List[ReportSummary])
async def list_reports(limit: int = 50):
    """List all reports from database."""
    session = get_session(settings)
    try:
        from database.models import Company, Report
        from sqlalchemy import desc

        reports = (
            session.query(Report, Company)
            .join(Company, Report.company_id == Company.id)
            .order_by(desc(Report.generated_at))
            .limit(limit)
            .all()
        )

        return [
            ReportSummary(
                report_id=r.id,
                company_name=c.name,
                ticker=c.ticker,
                generated_at=r.generated_at
            )
            for r, c in reports
        ]
    finally:
        session.close()


@app.get("/api/v1/reports/{report_id}")
async def get_report(report_id: str):
    """Get full report by ID."""
    session = get_session(settings)
    try:
        report = get_report_by_id(session, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        import json
        return json.loads(report.json_payload)
    finally:
        session.close()


@app.get("/api/v1/reports/{report_id}/agent-runs", response_model=List[AgentRunSummary])
async def get_report_agent_runs(report_id: str):
    """Get all agent runs for a report."""
    session = get_session(settings)
    try:
        runs = get_agent_runs_for_report(session, report_id)
        return [
            AgentRunSummary(
                agent_name=r.agent_name,
                status=r.status,
                tokens_used=r.tokens_used,
                cost_usd=r.cost_usd,
                timestamp=r.timestamp
            )
            for r in runs
        ]
    finally:
        session.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)