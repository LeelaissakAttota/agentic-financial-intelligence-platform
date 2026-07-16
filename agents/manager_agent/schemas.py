from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class TaskType(str, Enum):
    """Types of tasks the Manager Agent can dispatch."""
    NEWS_ANALYSIS = "news_analysis"
    MARKET_DATA = "market_data"
    FINANCIAL_ANALYSIS = "financial_analysis"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    RISK_ANALYSIS = "risk_analysis"
    INVESTMENT_SUMMARY = "investment_summary"


class ManagerAgentInput(BaseModel):
    """Input received by the Manager Agent from the user or API."""
    company: str = Field(..., description="Company name or ticker symbol to analyze")
    query: Optional[str] = Field(None, description="Optional natural language query")


class TaskPlan(BaseModel):
    """Plan of tasks to execute for a given company analysis request."""
    company: str = Field(..., description="Company name or ticker symbol")
    tasks: List[TaskType] = Field(..., description="List of task types to execute in order")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional planning metadata")


class WorkerResponse(BaseModel):
    """Standardized response structure from worker agents."""
    status: str = Field(..., description="Status of the worker execution: 'success' or 'error'")
    data: Optional[Dict[str, Any]] = Field(None, description="Result data from the worker agent")
    error: Optional[str] = Field(None, description="Error message if status is 'error'")
    usage: Optional[Dict[str, Any]] = Field(None, description="Token usage and cost information")


class ManagerAgentOutput(BaseModel):
    """Output produced by the Manager Agent after coordinating workers."""
    company: str = Field(..., description="Company analyzed")
    task_plan: TaskPlan = Field(..., description="The execution plan that was followed")
    results: Dict[str, Any] = Field(..., description="Results from each worker agent, keyed by task type")
    summary: Optional[Dict[str, Any]] = Field(None, description="Summary of execution (to be filled by Investment Summary Agent)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata (timing, token usage, etc.)")
    error: Optional[str] = Field(None, description="Error message if the manager agent failed")