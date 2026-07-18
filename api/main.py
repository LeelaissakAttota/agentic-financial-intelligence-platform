"""
FastAPI application for Financial Research Agent.

Provides REST API for running analyses and retrieving reports.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
import uuid

from config.settings import Settings, get_settings
from config.logging import setup_logging, get_logger
from config.logging import set_request_id, set_correlation_id, start_execution_timer
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

# New Phase 7 imports
from agents.research_planner.agent import create_research_plan, ExecutionPlan
from workflows.orchestrator import execute_research_plan, get_orchestrator
from memory.research_memory import get_memory_store, ResearchSession
from reports.generator import generate_report, Report, ReportType, ReportFormat
from approval.workflow import get_approval_workflow, ApprovalRequest, ApprovalActionType
from watchlists.manager import get_watchlist_manager, WatchlistData, AlertRuleData
from notifications.engine import get_notification_engine, NotificationChannel, NotificationPriority
from config.settings import get_settings

# Import new research router
from api.research_endpoints import router as research_router

# Monitoring & Middleware
from monitoring.metrics import (
    get_metrics,
    get_content_type,
    register_health_check,
    REQUEST_COUNT,
    REQUEST_LATENCY,
    REQUEST_IN_PROGRESS,
    ERROR_COUNT
)
from middleware.logging_middleware import RequestLoggingMiddleware
from middleware.rate_limit import RateLimitMiddleware, InMemoryRateLimiter
from middleware.circuit_breaker import circuit_breaker_registry, CircuitBreakerConfig

# Database setup
from database import init_db, get_session, get_engine
from database.models import Company, Report, AgentRun

# Global settings and engine
settings = get_settings()
engine = get_engine(settings)

# Setup structured logging
setup_logging(
    level=settings.log_level,
    format_type=settings.log_format,
    log_file=settings.log_file,
    max_size=settings.log_max_size,
    backup_count=settings.log_backup_count
)

logger = get_logger(__name__)

# Initialize rate limiter
rate_limiter = InMemoryRateLimiter(
    default_limit=settings.rate_limit_requests,
    default_window=settings.rate_limit_window
)

# Database initialization on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Application starting up")
    init_db(settings)
    
    # Register health checks
    register_health_check("database", check_database_health)
    register_health_check("chromadb", check_chromadb_health)
    register_health_check("llm", check_llm_health)
    
    # Start background metrics update
    asyncio.create_task(update_system_metrics())
    
    yield
    
    # Shutdown
    logger.info("Application shutting down")
    engine.dispose()
    # Close circuit breakers
    await circuit_breaker_registry.reset_all()


async def check_database_health() -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "message": "Database connection OK"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}


async def check_chromadb_health() -> Dict[str, Any]:
    """Check ChromaDB connectivity."""
    try:
        import requests
        response = requests.get(
            f"http://{settings.chroma_host}:{settings.chroma_port}/api/v1/heartbeat",
            timeout=5
        )
        if response.status_code == 200:
            return {"status": "healthy", "message": "ChromaDB connection OK"}
        return {"status": "unhealthy", "message": f"ChromaDB returned {response.status_code}"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}


async def check_llm_health() -> Dict[str, Any]:
    """Check LLM provider connectivity."""
    try:
        # Quick test with a simple prompt
        client = OpenRouterClient(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url
        )
        # Just verify we can create the client
        return {"status": "healthy", "message": "LLM client initialized"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}


async def update_system_metrics():
    """Background task to update system metrics."""
    import psutil
    from monitoring.metrics import MEMORY_USAGE, CPU_USAGE
    
    while True:
        try:
            process = psutil.Process()
            mem = process.memory_info()
            MEMORY_USAGE.labels(type="rss").set(mem.rss)
            MEMORY_USAGE.labels(type="vms").set(mem.vms)
            CPU_USAGE.set(process.cpu_percent(interval=0.1))
        except Exception:
            pass
        await asyncio.sleep(30)


app = FastAPI(
    title="Financial Research Agent API",
    description="REST API for AI-powered financial research analysis",
    version="1.5.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Include new research routes
app.include_router(research_router)

# ==================== Middleware Stack (Order Matters!) ====================

# 1. Security Headers (outermost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Rate Limiting
app.add_middleware(
    RateLimitMiddleware,
    limiter=rate_limiter,
    exclude_paths={
        "/health",
        "/health/detailed",
        "/health/live",
        "/health/ready",
        "/metrics",
        "/favicon.ico",
        "/docs",
        "/redoc",
        "/openapi.json"
    }
)

# 3. Request/Response Logging
app.add_middleware(
    RequestLoggingMiddleware,
    exclude_paths={
        "/health",
        "/health/detailed",
        "/health/live",
        "/health/ready",
        "/metrics",
        "/favicon.ico"
    },
    log_request_body=settings.log_request_body if hasattr(settings, 'log_request_body') else False,
    log_response_body=settings.log_response_body if hasattr(settings, 'log_response_body') else False,
    max_body_size=settings.max_log_body_size if hasattr(settings, 'max_log_body_size') else 10000
)

# ==================== Pydantic Models ====================
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
        logger.error(f"Analysis failed with error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        analysis["status"] = "failed"
        analysis["error"] = str(e)
    finally:
        analysis["updated_at"] = datetime.utcnow()


# ==================== Health Check Endpoints ====================
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "financial-research-agent",
        "version": "1.4.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe."""
    # Quick dependency checks
    checks = {}
    
    # Database
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception:
        checks["database"] = "unhealthy"
    
    overall = "ready" if all(v == "healthy" for v in checks.values()) else "not_ready"
    return {"status": overall, "checks": checks}


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with all dependency verification."""
    from monitoring.metrics import get_health_status
    return await get_health_status()


# ==================== Metrics Endpoint ====================
@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=get_metrics(),
        media_type=get_content_type()
    )


# ==================== Circuit Breaker Status ====================
@app.get("/admin/circuit-breakers")
async def get_circuit_breakers():
    """Get status of all circuit breakers (admin only)."""
    return circuit_breaker_registry.get_all_stats()


@app.post("/admin/circuit-breakers/{name}/reset")
async def reset_circuit_breaker(name: str):
    """Reset a specific circuit breaker (admin only)."""
    if circuit_breaker_registry.remove(name):
        return {"message": f"Circuit breaker '{name}' reset"}
    raise HTTPException(status_code=404, detail="Circuit breaker not found")


@app.post("/admin/circuit-breakers/reset-all")
async def reset_all_circuit_breakers():
    """Reset all circuit breakers (admin only)."""
    await circuit_breaker_registry.reset_all()
    return {"message": "All circuit breakers reset"}


# ==================== Analysis Endpoints ====================
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


# ==================== Report Endpoints ====================
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


# ==================== Admin Endpoints ====================
@app.get("/admin/stats")
async def get_admin_stats():
    """Get application statistics (admin only)."""
    from monitoring.metrics import generate_performance_report
    
    session = get_session(settings)
    try:
        from sqlalchemy import func
        
        # Database stats
        companies_count = session.query(func.count(Company.id)).scalar()
        reports_count = session.query(func.count(Report.id)).scalar()
        agent_runs_count = session.query(func.count(AgentRun.id)).scalar()
        
        return {
            "database": {
                "companies": companies_count,
                "reports": reports_count,
                "agent_runs": agent_runs_count
            },
            "in_memory": {
                "active_analyses": len([a for a in analysis_store.values() if a["status"] in ("pending", "running")]),
                "completed_analyses": len([a for a in analysis_store.values() if a["status"] == "completed"]),
                "failed_analyses": len([a for a in analysis_store.values() if a["status"] == "failed"])
            },
            "performance": generate_performance_report()
        }
    finally:
        session.close()


@app.post("/admin/clear-analysis-store")
async def clear_analysis_store():
    """Clear in-memory analysis store (admin only)."""
    global analysis_store
    count = len(analysis_store)
    analysis_store.clear()
    return {"message": f"Cleared {count} analyses from store"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)