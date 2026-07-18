"""
Copilot API Endpoints - REST API for AI Copilot functionality.
"""
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from copilot.agent import (
    CopilotAgent, CopilotContext, CopilotMode, ConversationMessage, ConversationRole,
    get_copilot_agent
)
from agents.research_planner.agent import ExecutionPlan, create_research_plan
from workflows.orchestrator import execute_research_plan, get_orchestrator
from memory.research_memory import get_memory_store, ResearchSession
from reports.generator import generate_report, Report, ReportType, ReportFormat
from watchlists.manager import get_watchlist_manager, WatchlistData, AlertRuleData
from notifications.engine import get_notification_engine, NotificationChannel, NotificationPriority
from approval.workflow import get_approval_workflow, ApprovalRequest, ApprovalActionType
from tools.registry import get_tool_registry, ToolCategory
from config.settings import get_settings

router = APIRouter(prefix="/api/v1/copilot", tags=["copilot"])


# Request/Response Models

class SessionCreateRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    company: Optional[str] = Field(None, description="Initial company context")
    mode: CopilotMode = Field(CopilotMode.AUTO_EXECUTE, description="Operating mode")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")


class SessionCreateResponse(BaseModel):
    session_id: str
    user_id: str
    company: Optional[str]
    mode: CopilotMode
    created_at: datetime


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    stream: bool = Field(False, description="Stream response")


class ChatResponse(BaseModel):
    response: str
    session_id: str
    company: Optional[str]
    tokens_used: int
    metadata: Dict[str, Any] = {}


class PlanRequest(BaseModel):
    goal: str = Field(..., description="Research goal")
    company: str = Field(..., description="Company name or ticker")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    constraints: Optional[Dict[str, Any]] = Field(None, description="Constraints (budget, time)")


class PlanResponse(BaseModel):
    plan_id: str
    goal: str
    company: str
    complexity: str
    estimated_duration_seconds: int
    estimated_cost_usd: float
    steps: List[Dict[str, Any]]
    parallel_groups: Dict[str, List[str]]


class ExecutePlanRequest(BaseModel):
    plan: PlanResponse
    auto_approve: bool = Field(False, description="Skip human approval")


class ExecutePlanResponse(BaseModel):
    execution_id: str
    status: str
    started_at: datetime
    message: str


class ReportGenerateRequest(BaseModel):
    report_type: str = Field(..., description="Type of report to generate")
    company: str = Field(..., description="Company name or ticker")
    session_id: Optional[str] = Field(None, description="Research session to use")
    format: str = Field("markdown", description="Output format")


class ReportGenerateResponse(BaseModel):
    report: Report


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


class ToolExecuteRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]


class ToolExecuteResponse(BaseModel):
    execution_id: str
    tool_name: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_seconds: float


class HistoryResponse(BaseModel):
    history: List[ConversationMessage]


class StatusResponse(BaseModel):
    session_id: str
    company: Optional[str]
    mode: CopilotMode
    plan: Optional[Dict[str, Any]]
    recent_executions: List[Dict[str, Any]]


# Dependency

async def get_copilot() -> CopilotAgent:
    return get_copilot_agent()


async def get_orchestrator_dep():
    return get_orchestrator()


# Session Endpoints

@router.post("/sessions", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session(request: SessionCreateRequest, copilot: CopilotAgent = Depends(get_copilot)):
    """Create a new copilot session."""
    context = await copilot.create_session(request.user_id, {
        "company": request.company,
        "mode": request.mode,
        "preferences": request.preferences or {}
    })
    return SessionCreateResponse(
        session_id=context.session_id,
        user_id=context.user_id,
        company=context.company,
        mode=context.mode,
        created_at=datetime.now()
    )


@router.get("/sessions/{session_id}", response_model=CopilotContext)
async def get_session(session_id: str, copilot: CopilotAgent = Depends(get_copilot)):
    """Get session details."""
    context = copilot.get_session(session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Session not found")
    return context


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, copilot: CopilotAgent = Depends(get_copilot)):
    """Delete/end a session."""
    context = copilot.get_session(session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Session not found")

    # Archive in memory store
    memory_store = get_memory_store()
    if context.session_id:
        session = await memory_store.get_session(context.session_id)
        if session:
            session.status = "archived"
            await memory_store.store_session(session)

    del copilot.sessions[session_id]
    return {"message": "Session ended", "session_id": session_id}


# Chat Endpoint

@router.post("/sessions/{session_id}/chat", response_model=ChatResponse)
async def chat(
    session_id: str,
    request: ChatRequest,
    copilot: CopilotAgent = Depends(get_copilot)
):
    """Send a message to the copilot and get response."""
    context = copilot.get_session(session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Session not found")

    response = await copilot.process_message(session_id, request.message, request.stream)

    if request.stream:
        # For streaming, we'd return a StreamingResponse
        # For now, return full response
        pass

    return ChatResponse(
        response=response,
        session_id=session_id,
        company=context.company,
        tokens_used=len(response) // 4,  # Rough estimate
        metadata={"mode": context.mode.value}
    )


# Planning Endpoints

@router.post("/sessions/{session_id}/plan", response_model=PlanResponse)
async def create_plan(
    session_id: str,
    request: PlanRequest,
    copilot: CopilotAgent = Depends(get_copilot)
):
    """Create a research execution plan."""
    context = copilot.get_session(session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Session not found")

    if request.company:
        context.company = request.company

    plan = await create_research_plan(request.goal, request.company, {
        "session_id": session_id,
        "context": request.context,
        "constraints": request.constraints
    })

    context.current_plan = plan

    return PlanResponse(
        plan_id=plan.plan_id,
        goal=plan.goal,
        company=plan.company,
        complexity=plan.complexity.value,
        estimated_duration_seconds=plan.estimated_total_duration,
        estimated_cost_usd=plan.estimated_total_cost if hasattr(plan, 'estimated_total_cost') else 0.0,
        steps=[
            {
                "step_id": step.step_id,
                "agent_type": step.agent_type.value,
                "dependencies": step.dependencies,
                "parallel_group": step.parallel_group,
                "estimated_duration_seconds": step.estimated_duration_seconds,
                "priority": step.priority
            }
            for step in plan.steps
        ],
        parallel_groups=plan.get_parallel_groups() if hasattr(plan, 'get_parallel_groups') else {}
    )


@router.post("/sessions/{session_id}/execute", response_model=ExecutePlanResponse)
async def execute_plan(
    session_id: str,
    background_tasks: BackgroundTasks,
    request: ExecutePlanRequest,
    copilot: CopilotAgent = Depends(get_copilot)
):
    """Execute a research plan."""
    context = copilot.get_session(session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Session not found")

    if not context.current_plan:
        raise HTTPException(status_code=400, detail="No plan to execute")

    # Convert request to ExecutionPlan
    plan = context.current_plan

    if request.auto_approve:
        # Execute immediately in background
        execution_id = str(uuid.uuid4())[:8]
        background_tasks.add_task(_execute_plan_background, session_id, plan, execution_id)
        return ExecutePlanResponse(
            execution_id=execution_id,
            status="started",
            started_at=datetime.now(),
            message="Plan execution started in background"
        )
    else:
        # Create approval request
        approval = get_approval_workflow()
        await approval.create_request(
            title=f"Research Plan: {plan.company}",
            description=f"Execute research plan with {len(plan.steps)} steps for {plan.company}",
            request_type="research_execution",
            reference_id=session_id,
            reference_type="plan",
            requester_id=context.user_id,
            requester_name="Copilot User",
            approvers=[
                {"user_id": "analyst", "name": "Senior Analyst", "role": "analyst", "order": 0}
            ],
            expires_in_hours=24
        )
        return ExecutePlanResponse(
            execution_id="pending_approval",
            status="pending_approval",
            started_at=datetime.now(),
            message="Plan submitted for approval"
        )


async def _execute_plan_background(session_id: str, plan: ExecutionPlan, execution_id: str):
    """Background task to execute plan."""
    copilot = get_copilot_agent()
    context = copilot.get_session(session_id)
    if not context:
        return

    try:
        execution = await copilot.execute_plan(session_id, plan)

        # Store results
        memory_store = get_memory_store()
        session = await memory_store.get_session(context.session_id)
        if session:
            session.status = execution.status
            session.results = execution.get_step_results(execution)
            session.completed_at = execution.completed_at
            session.duration_seconds = execution.total_duration_seconds
            if execution.error:
                session.error = execution.error
            await memory_store.store_session(session)

    except Exception as e:
        logger.error(f"Background execution failed: {e}")


# Tool Endpoints

@router.get("/tools", response_model=List[Dict[str, Any]])
async def list_tools(category: Optional[ToolCategory] = Query(None)):
    """List all available tools."""
    registry = get_tool_registry()
    tools = registry.get_all_tools()

    if category:
        tools = [t for t in tools if t.category == category]

    return [t.__dict__ for t in tools]


@router.get("/tools/{tool_name}")
async def get_tool(tool_name: str):
    """Get tool definition."""
    registry = get_tool_registry()
    tool = registry.get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool.__dict__


@router.post("/tools/execute", response_model=ToolExecuteResponse)
async def execute_tool(request: ToolExecuteRequest):
    """Execute a specific tool."""
    from tools.registry import get_tool_executor
    executor = get_tool_executor()

    execution = await executor.execute(request.tool_name, request.parameters)

    return ToolExecuteResponse(
        execution_id=execution.execution_id,
        tool_name=execution.tool_name,
        status=execution.status.value,
        result=execution.result,
        error=execution.error,
        duration_seconds=execution.duration_seconds
    )


# Report Endpoints

@router.post("/reports/generate", response_model=ReportGenerateResponse)
async def generate_report_endpoint(request: ReportGenerateRequest):
    """Generate a research report."""
    try:
        report = await generate_report(
            report_type=ReportType(request.report_type),
            company=request.company,
            session_id=request.session_id,
            format=ReportFormat(request.format)
        )
        return ReportGenerateResponse(report=report)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {e}")


@router.get("/reports", response_model=List[Dict[str, Any]])
async def list_reports(company: Optional[str] = Query(None), limit: int = Query(20, le=100)):
    """List generated reports."""
    # In production, would query database
    return []


# Watchlist Endpoints

@router.post("/watchlists", response_model=WatchlistData)
async def create_watchlist(request: WatchlistCreateRequest):
    """Create a new watchlist."""
    from watchlists.manager import get_watchlist_manager, WatchlistType
    manager = get_watchlist_manager()

    wl_type = WatchlistType(request.type)
    watchlist = await manager.create_watchlist(
        name=request.name,
        description=request.description,
        type=wl_type,
        owner_id=request.owner_id,
        initial_companies=request.companies
    )
    return watchlist


@router.get("/watchlists", response_model=List[WatchlistData])
async def list_watchlists(owner_id: Optional[str] = Query(None)):
    """List watchlists."""
    manager = get_watchlist_manager()
    return await manager.list_watchlists(owner_id)


@router.get("/watchlists/{watchlist_id}", response_model=WatchlistData)
async def get_watchlist(watchlist_id: str):
    """Get watchlist details."""
    manager = get_watchlist_manager()
    watchlist = await manager.get_watchlist(watchlist_id)
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return watchlist


@router.post("/watchlists/{watchlist_id}/companies")
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
    return {"message": f"Added {company} to watchlist"}


@router.delete("/watchlists/{watchlist_id}/companies/{company}")
async def remove_company_from_watchlist(watchlist_id: str, company: str):
    """Remove company from watchlist."""
    manager = get_watchlist_manager()
    success = await manager.remove_company(watchlist_id, company)
    if not success:
        raise HTTPException(status_code=404, detail="Company not found in watchlist")
    return {"message": f"Removed {company} from watchlist"}


@router.post("/watchlists/{watchlist_id}/alerts", response_model=AlertRuleData)
async def create_alert_rule(watchlist_id: str, request: AlertRuleCreateRequest):
    """Create alert rule for watchlist."""
    from notifications.engine import NotificationPriority, NotificationChannel
    manager = get_watchlist_manager()

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

@router.get("/approval/{request_id}", response_model=ApprovalRequest)
async def get_approval_request(request_id: str):
    """Get approval request details."""
    approval = get_approval_workflow()
    request = await approval.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return request


@router.post("/approval/{request_id}/action")
async def process_approval_action(
    request_id: str,
    action: str,
    user_id: str,
    user_name: str,
    comment: str = "",
    metadata: Optional[Dict[str, Any]] = None
):
    """Process approval action."""
    approval = get_approval_workflow()

    try:
        action_type = ApprovalActionType(action)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}")

    request = await approval.process_action(
        request_id=request_id,
        action_type=action_type,
        user_id=user_id,
        user_name=user_name,
        comment=comment,
        metadata=metadata
    )

    return request


@router.get("/approval", response_model=List[ApprovalRequest])
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
    return requests


# History & Status

@router.get("/sessions/{session_id}/history", response_model=HistoryResponse)
async def get_conversation_history(session_id: str, limit: int = Query(50, le=100)):
    """Get conversation history."""
    copilot = get_copilot_agent()
    context = copilot.get_session(session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Session not found")

    return HistoryResponse(history=context.conversation_history[-limit:])


@router.get("/sessions/{session_id}/status", response_model=StatusResponse)
async def get_session_status(session_id: str):
    """Get session status."""
    copilot = get_copilot_agent()
    context = copilot.get_session(session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get recent tool executions
    from tools.registry import get_tool_executor
    executor = get_tool_executor()
    executions = executor.get_recent_executions(10)

    plan_info = None
    if context.current_plan:
        plan_info = {
            "plan_id": context.current_plan.plan_id,
            "company": context.current_plan.company,
            "steps": len(context.current_plan.steps),
            "complexity": context.current_plan.complexity.value
        }

    return StatusResponse(
        session_id=session_id,
        company=context.company,
        mode=context.mode,
        plan=plan_info,
        recent_executions=[
            {
                "tool_name": e.tool_name,
                "status": e.status.value,
                "duration_seconds": e.duration_seconds,
                "completed_at": e.completed_at.isoformat() if e.completed_at else None
            }
            for e in executions
        ]
    )


# System Endpoints

@router.get("/tools/categories")
async def get_tool_categories():
    """Get tool categories."""
    return [{"value": c.value, "label": c.value.replace("_", " ").title()} for c in ToolCategory]


@router.get("/modes")
async def get_copilot_modes():
    """Get available copilot modes."""
    return [{"value": m.value, "label": m.value.replace("_", " ").title()} for m in CopilotMode]


@router.get("/report-types")
async def get_report_types():
    """Get available report types."""
    return [{"value": r.value, "label": r.value.replace("_", " ").title()} for r in ReportType]


@router.get("/health")
async def copilot_health():
    """Copilot health check."""
    return {
        "status": "healthy",
        "active_sessions": len(get_copilot_agent().sessions),
        "tools_available": len(get_tool_registry().get_all_tools()),
        "timestamp": datetime.now().isoformat()
    }


# Export router
__all__ = ["router"]