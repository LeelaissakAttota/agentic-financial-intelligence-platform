"""Pydantic schemas for the Manager Agent's input/output contract.
See docs/AGENT_PROMPTS.md and the Manager Agent design note for the
full JSON shape and worked testing examples."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class Constraints(BaseModel):
    max_agents: Optional[int] = None
    skip_rag: bool = False


class ManagerInput(BaseModel):
    user_query: str
    requested_depth: Literal["full", "quick", "custom"] = "full"
    requested_sections: Optional[list[str]] = None
    constraints: Constraints = Constraints()


class ExecutionPlan(BaseModel):
    resolved_depth: Literal["full", "quick", "custom"]
    agents_dispatched: list[str]
    execution_order: list[list[str]]  # tiers, respecting dependencies
    reasoning: str


class AgentStatus(BaseModel):
    agent: str
    status: Literal["success", "data_unavailable", "failed"]
    duration_ms: int


class ManagerOutput(BaseModel):
    agent: str = "manager_agent"
    company: str
    ticker: str
    generated_at: datetime
    execution_plan: ExecutionPlan
    sections: dict[str, dict]
    agent_status: list[AgentStatus]
    warnings: list[str] = []
