"""
Research API Endpoints

FastAPI endpoints for autonomous research workflows.
"""
import asyncio
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from agents.research_planner.agent import create_research_plan, ExecutionPlan
from workflows.orchestrator import execute_research_plan, get_orchestrator
from memory.research_memory import get_memory_store, ResearchSession
from reports.generator import generate_report, Report, ReportType, ReportFormat
from approval.workflow import get_approval_workflow, ApprovalRequest, ApprovalActionType
from watchlists.manager import get_watchlist_manager, WatchlistData, AlertRuleData
from notifications.engine import get_notification_engine, NotificationChannel, NotificationPriority
from config.settings import get_settings

router = APIRouter(prefix="/api/v1/research", tags=["research"])


# Request/Response Models
class ResearchStartRequest(BaseModel):
    company: str = Field(..., description="Company name or ticker")
    query: str = Field(..., description="Research question or objective")
    auto_approve: bool = Field(False, description="Skip human approval")
    custom_context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ResearchStartResponse(BaseModel):
    research_id: str
    status: str
    message: str
    plan: Optional[Dict[str, Any]] = None


class WatchlistCreateRequest(BaseModel):
    name: str
    description: str = ""
    type: str = "personal"
    owner_id: str
    companies: Optional[List[str]] = None


class AlertRuleCreateRequest(BaseModel):
    watchlist_id: str
    name: str
    description: str
    conditions: Dict[str, Any]
    severity: str = "warning"
    channels: Optional[List[str]] = None
    company: Optional[str] = None
    cooldown_minutes: int = 60


class ApprovalActionRequest(BaseModel):
    action: str  # approve, reject, request_changes, escalate, delegate, comment
    user_id: str
    user_name: str
    comment: str = ""
    metadata: Optional[Dict[str, Any]] = None


class ReportGenerateRequest(BaseModel):
    report_type: str
    company: str
    session_id: Optional[str] = None
    format: str = "markdown"
    custom_data: Optional[Dict[str, Any]] = None


# Dependency
async def get_orchestrator_dep():
    return get_orchestrator()


@router.post("/start", response_model=ResearchStartResponse)
async def start_research(
    request: ResearchStartRequest,
    background_tasks: BackgroundTasks,
    orchestrator = Depends(get_orchestrator_dep)
):
    """
    Start autonomous research workflow.
    
    Creates execution plan and optionally begins execution.
    """
    try:
        # Create execution plan
        plan = await create_research_plan(request.query, request.company, request.custom_context)
        
        # Convert to dict for response
        plan_dict = {
            "plan_id": plan.plan_id,
            "company": plan.company,
            "query": plan.query,
            "complexity": plan.complexity.value,
            "estimated_duration_seconds": plan.estimated_total_duration,
            "steps": [
                {
                    "step_id": step.step_id,
                    "agent_type": step.agent_type.value,
                    "dependencies": step.dependencies,
                    "parallel_group": step.parallel_group,
                    "estimated_duration_seconds": step.estimated_duration_seconds,
                    "priority": step.priority
                }
                for step in plan.steps
            ]
        }
        
        # Store research session
        memory_store = get_memory_store()
        session = await memory_store.create_session(company=request.company, query=request.query, plan_id=plan.plan_id)
        
        research_id = session.session_id
        
        if request.auto_approve:
            # Execute immediately in background
            background_tasks.add_task(
                _execute_research_background,
                research_id,
                plan,
                request.company
            )
            return ResearchStartResponse(
                research_id=research_id,
                status="executing",
                message="Research started with auto-approval",
                plan=plan_dict
            )
        else:
            # Create approval request
            approval = get_approval_workflow()
            await approval.create_request(
                title=f"Research Plan: {request.company}",
                description=f"Research query: {request.query}\n\nPlan includes {len(plan.steps)} steps across {len(set(s.parallel_group for s in plan.steps if s.parallel_group))} parallel groups.",
                request_type="research_plan",
                reference_id=research_id,
                reference_type="plan",
                requester_id="system",
                requester_name="Automated Research",
                approvers=[
                    {"user_id": "analyst", "name": "Senior Analyst", "role": "analyst", "order": 0}
                ],
                expires_in_hours=24
            )
            return ResearchStartResponse(
                research_id=research_id,
                status="pending_approval",
                message="Research plan created, awaiting human approval",
                plan=plan_dict
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start research: {str(e)}")


async def _execute_research_background(research_id: str, plan: ExecutionPlan, company: str):
    """Background task to execute research plan."""
    orchestrator = get_orchestrator()
    
    async def progress_callback(execution, step_result):
        memory_store = get_memory_store()
        session = await memory_store.get_session(research_id)
        if session:
            session.results[f"step_{step_result.step_id}"] = {
                "status": step_result.status.value,
                "agent": step_result.agent_type.value,
                "duration": step_result.duration_seconds
            }
            await memory_store.store_session(session)
    
    execution = await orchestrator.execute_plan(plan, progress_callback)
    
    # Update final session status
    memory_store = get_memory_store()
    session = await memory_store.get_session(research_id)
    if session:
        session.status = execution.status
        session.results = execution.get_step_results(execution)
        session.completed_at = execution.completed_at
        session.duration_seconds = execution.total_duration_seconds
        if execution.error:
            session.error = execution.error
        await memory_store.store_session(session)


@router.get("/{research_id}")
async def get_research_status(research_id: str):
    """Get research execution status and results."""
    memory_store = get_memory_store()
    session = await memory_store.get_session(research_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Research not found")
    
    return {
        "research_id": session.session_id,
        "company": session.company,
        "query": session.query,
        "status": session.status,
        "plan_id": session.plan_id,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "duration_seconds": session.duration_seconds,
        "results": session.results,
        "conclusions": session.conclusions,
        "error": session.error
    }


@router.get("/history")
async def get_research_history(
    company: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    status: Optional[str] = Query(None)
):
    """Get research history."""
    memory_store = get_memory_store()
    sessions = await memory_store.get_recent_sessions(company, limit)
    
    if status:
        sessions = [s for s in sessions if s.status == status]
    
    return {
        "research_history": [
            {
                "research_id": s.session_id,
                "company": s.company,
                "query": s.query,
                "status": s.status,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "duration_seconds": s.duration_seconds
            }
            for s in sessions
        ]
    }


@router.get("/status")
async def get_system_status():
    """Get overall system status."""
    orchestrator = get_orchestrator()
    active = len(orchestrator._executions)
    
    return {
        "active_research": active,
        "max_parallel": orchestrator.max_parallel,
        "timestamp": datetime.now().isoformat()
    }


# Watchlist Endpoints
watchlist_router = APIRouter(prefix="/api/v1/watchlists", tags=["watchlists"])


@watchlist_router.post("/", response_model=WatchlistData)
async def create_watchlist(request: WatchlistCreateRequest):
    """Create a new watchlist."""
    manager = get_watchlist_manager()
    
    from watchlists.manager import WatchlistType
    wl_type = WatchlistType(request.type)
    
    watchlist = await manager.create_watchlist(
        name=request.name,
        description=request.description,
        type=wl_type,
        owner_id=request.owner_id,
        initial_companies=request.companies
    )
    return watchlist


@watchlist_router.get("/")
async def list_watchlists(owner_id: Optional[str] = Query(None)):
    """List watchlists."""
    manager = get_watchlist_manager()
    watchlists = await manager.list_watchlists(owner_id)
    return {"watchlists": watchlists}


@watchlist_router.get("/{watchlist_id}")
async def get_watchlist(watchlist_id: str):
    """Get watchlist details."""
    manager = get_watchlist_manager()
    watchlist = await manager.get_watchlist(watchlist_id)
    
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    
    return watchlist


@watchlist_router.post("/{watchlist_id}/companies")
async def add_company_to_watchlist(
    watchlist_id: str,
    company: str,
    ticker: Optional[str] = None,
    notes: str = "",
    target_price: Optional[float] = None,
    stop_loss: Optional[float] = None
):
    """Add company to watchlist."""
    manager = get_watchlist_manager()
    success = await manager.add_company(
        watchlist_id, company, ticker, notes,
        target_price=target_price, stop_loss=stop_loss
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add company")
    
    return {"success": True, "message": f"Added {company} to watchlist"}


@watchlist_router.delete("/{watchlist_id}/companies/{company}")
async def remove_company_from_watchlist(watchlist_id: str, company: str):
    """Remove company from watchlist."""
    manager = get_watchlist_manager()
    success = await manager.remove_company(watchlist_id, company)
    
    if not success:
        raise HTTPException(status_code=404, detail="Company not found in watchlist")
    
    return {"success": True, "message": f"Removed {company} from watchlist"}


@watchlist_router.post("/{watchlist_id}/alerts")
async def create_alert_rule(watchlist_id: str, request: AlertRuleCreateRequest):
    """Create alert rule for watchlist."""
    manager = get_watchlist_manager()
    
    from notifications.engine import NotificationPriority
    severity = NotificationPriority(request.severity)
    channels = [NotificationChannel(c) for c in request.channels] if request.channels else None
    
    rule = await manager.add_alert_rule(
        watchlist_id=watchlist_id,
        name=request.name,
        description=request.description,
        conditions=request.conditions,
        severity=severity,
        channels=channels,
        company=request.company,
        cooldown_minutes=request.cooldown_minutes
    )
    
    return rule


# Approval Endpoints
approval_router = APIRouter(prefix="/api/v1/approval", tags=["approval"])


@approval_router.get("/{request_id}")
async def get_approval_request(request_id: str):
    """Get approval request details."""
    approval = get_approval_workflow()
    request = await approval.get_request(request_id)
    
    if not request:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    return request


@approval_router.post("/{request_id}/action")
async def process_approval_action(request_id: str, action: ApprovalActionRequest):
    """Process approval action."""
    approval = get_approval_workflow()
    
    try:
        action_type = ApprovalActionType(action.action)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action.action}")
    
    request = await approval.process_action(
        request_id=request_id,
        action_type=action_type,
        user_id=action.user_id,
        user_name=action.user_name,
        comment=action.comment,
        metadata=action.metadata
    )
    
    return request


@approval_router.get("/")
async def list_approval_requests(
    user_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """List approval requests."""
    approval = get_approval_workflow()
    
    status_enum = None
    if status:
        from approval.workflow import ApprovalStatus
        try:
            status_enum = ApprovalStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    requests = await approval.list_pending_requests(user_id, status_enum)
    return {"requests": requests}


# Reports Endpoints
reports_router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@reports_router.post("/generate", response_model=Report)
async def generate_report_endpoint(request: ReportGenerateRequest):
    """Generate a report."""
    try:
        report_type = ReportType(request.report_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid report type: {request.report_type}")
    
    try:
        report_format = ReportFormat(request.format)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid format: {request.format}")
    
    report = await generate_report(
        report_type=report_type,
        company=request.company,
        session_id=request.session_id,
        custom_data=request.custom_data,
        format=report_format
    )
    
    return report


@reports_router.get("/")
async def list_reports(
    company: Optional[str] = Query(None),
    limit: int = Query(20, le=100)
):
    """List generated reports."""
    # This would query a reports table in the database
    return {"reports": []}


# Export all routers
__all__ = ["router", "watchlist_router", "approval_router", "reports_router"]