"""
Delegation System - Task delegation between agents.

Enables agents to delegate subtasks to other agents based on
capabilities, workload, and specialization.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

from agents.manager_agent.schemas import Task, TaskResult, TaskStatus
from agents.research_planner.agent import AgentType
from config.settings import get_settings

logger = logging.getLogger(__name__)


class DelegationStatus(str, Enum):
    """Status of a delegation."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DelegationRequest:
    """Request to delegate a task to another agent."""
    delegation_id: str
    delegator: str
    delegatee: str
    task: Task
    reason: str
    priority: int = 1
    deadline: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)
    status: DelegationStatus = DelegationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[TaskResult] = None
    error: Optional[str] = None


@dataclass
class AgentCapability:
    """Agent capability profile for delegation decisions."""
    agent_name: str
    agent_type: AgentType
    specializations: List[str]
    current_load: int = 0
    max_concurrent: int = 3
    avg_completion_time: Dict[str, float] = field(default_factory=dict)
    success_rate: float = 1.0
    supported_task_types: List[str] = field(default_factory=list)


class DelegationManager:
    """Manages task delegation between agents."""

    def __init__(self):
        self.settings = get_settings()
        self.pending_delegations: Dict[str, DelegationRequest] = {}
        self.active_delegations: Dict[str, DelegationRequest] = {}
        self.completed_delegations: Dict[str, DelegationRequest] = {}
        self.agent_capabilities: Dict[str, AgentCapability] = {}
        self._initialize_capabilities()

    def _initialize_capabilities(self):
        """Initialize agent capability profiles."""
        capabilities = {
            "financial_document": AgentCapability(
                agent_name="financial_document",
                agent_type=AgentType.FINANCIAL_DOCUMENT,
                specializations=["sec_filings", "earnings_transcripts", "financial_reports", "ratio_analysis"],
                max_concurrent=2,
                avg_completion_time={"financial_analysis": 60, "filing_review": 45},
                success_rate=0.95,
                supported_task_types=["financial_analysis", "filing_review", "earnings_analysis"]
            ),
            "sentiment": AgentCapability(
                agent_name="sentiment",
                agent_type=AgentType.SENTIMENT,
                specializations=["news_sentiment", "social_sentiment", "analyst_sentiment", "divergence_detection"],
                max_concurrent=3,
                avg_completion_time={"sentiment_analysis": 30, "divergence_check": 15},
                success_rate=0.92,
                supported_task_types=["sentiment_analysis", "divergence_check"]
            ),
            "risk": AgentCapability(
                agent_name="risk",
                agent_type=AgentType.RISK,
                specializations=["var_cvar", "stress_testing", "market_risk", "credit_risk", "liquidity_risk"],
                max_concurrent=2,
                avg_completion_time={"risk_assessment": 45, "stress_test": 60},
                success_rate=0.90,
                supported_task_types=["risk_assessment", "stress_test", "var_calculation"]
            ),
            "competitive": AgentCapability(
                agent_name="competitive",
                agent_type=AgentType.COMPETITIVE,
                specializations=["peer_comparison", "benchmarking", "market_positioning", "competitive_advantage"],
                max_concurrent=2,
                avg_completion_time={"peer_analysis": 45, "benchmarking": 30},
                success_rate=0.93,
                supported_task_types=["peer_analysis", "benchmarking", "positioning"]
            ),
            "news": AgentCapability(
                agent_name="news",
                agent_type=AgentType.NEWS,
                specializations=["news_aggregation", "event_detection", "entity_extraction", "sentiment_trends"],
                max_concurrent=3,
                avg_completion_time={"news_collection": 30, "event_analysis": 20},
                success_rate=0.94,
                supported_task_types=["news_collection", "event_analysis", "entity_extraction"]
            ),
            "market_data": AgentCapability(
                agent_name="market_data",
                agent_type=AgentType.MARKET_DATA,
                specializations=["technical_analysis", "fundamental_valuation", "real_time_quotes", "historical_data"],
                max_concurrent=4,
                avg_completion_time={"technical_analysis": 15, "fundamental_analysis": 20},
                success_rate=0.96,
                supported_task_types=["technical_analysis", "fundamental_analysis", "quote_retrieval"]
            ),
            "investment_summary": AgentCapability(
                agent_name="investment_summary",
                agent_type=AgentType.INVESTMENT_SUMMARY,
                specializations=["thesis_formulation", "price_targeting", "catalyst_identification", "synthesis"],
                max_concurrent=1,
                avg_completion_time={"thesis_generation": 30, "synthesis": 45},
                success_rate=0.95,
                supported_task_types=["thesis_generation", "synthesis", "price_targeting"]
            ),
            "knowledge_graph": AgentCapability(
                agent_name="knowledge_graph",
                agent_type=AgentType.KNOWLEDGE_GRAPH,
                specializations=["entity_relationships", "graph_traversal", "centrality_analysis", "community_detection"],
                max_concurrent=2,
                avg_completion_time={"graph_query": 20, "centrality": 30, "community": 45},
                success_rate=0.90,
                supported_task_types=["graph_query", "centrality_analysis", "community_detection"]
            ),
            "portfolio": AgentCapability(
                agent_name="portfolio",
                agent_type=AgentType.PORTFOLIO,
                specializations=["position_management", "risk_metrics", "rebalancing", "monte_carlo", "attribution"],
                max_concurrent=2,
                avg_completion_time={"portfolio_analysis": 30, "rebalancing": 45, "monte_carlo": 60},
                success_rate=0.92,
                supported_task_types=["portfolio_analysis", "rebalancing", "monte_carlo", "attribution"]
            ),
            "patterns": AgentCapability(
                agent_name="patterns",
                agent_type=AgentType.PATTERNS,
                specializations=["trend_detection", "support_resistance", "breakout_detection", "regime_change"],
                max_concurrent=3,
                avg_completion_time={"pattern_detection": 30, "backtest": 45},
                success_rate=0.88,
                supported_task_types=["pattern_detection", "backtest"]
            ),
            "alerts": AgentCapability(
                agent_name="alerts",
                agent_type=AgentType.ALERTS,
                specializations=["alert_creation", "alert_evaluation", "notification_routing", "deduplication"],
                max_concurrent=4,
                avg_completion_time={"alert_creation": 10, "alert_evaluation": 5},
                success_rate=0.97,
                supported_task_types=["alert_creation", "alert_evaluation", "notification"]
            ),
            "analytics": AgentCapability(
                agent_name="analytics",
                agent_type=AgentType.ANALYTICS,
                specializations=["factor_models", "monte_carlo", "attribution", "scenario_analysis", "correlation"],
                max_concurrent=2,
                avg_completion_time={"factor_analysis": 45, "monte_carlo": 60, "attribution": 30, "scenario": 45},
                success_rate=0.90,
                supported_task_types=["factor_analysis", "monte_carlo", "attribution", "scenario", "correlation"]
            ),
            "historical": AgentCapability(
                agent_name="historical",
                agent_type=AgentType.HISTORICAL,
                specializations=["trend_analysis", "company_evolution", "peer_comparison", "mann_kendall"],
                max_concurrent=2,
                avg_completion_time={"trend_analysis": 45, "evolution": 60, "peer_comparison": 30},
                success_rate=0.91,
                supported_task_types=["trend_analysis", "evolution", "peer_comparison"]
            ),
            "cross_agent_memory": AgentCapability(
                agent_name="cross_agent_memory",
                agent_type=AgentType.CROSS_AGENT_MEMORY,
                specializations=["knowledge_retrieval", "memory_linking", "supersession", "context_provision"],
                max_concurrent=5,
                avg_completion_time={"memory_retrieval": 10, "context_provision": 5},
                success_rate=0.99,
                supported_task_types=["memory_retrieval", "context_provision", "knowledge_linking"]
            )
        }

        for name, cap in capabilities.items():
            self.agent_capabilities[name] = cap

    def find_best_delegate(
        self,
        task_type: str,
        required_specializations: Optional[List[str]] = None,
        exclude_agents: Optional[List[str]] = None
    ) -> Optional[str]:
        """Find the best agent to delegate a task to."""
        exclude = set(exclude_agents or [])
        candidates = []

        for name, cap in self.agent_capabilities.items():
            if name in exclude:
                continue

            # Check if agent supports this task type
            if task_type not in cap.supported_task_types:
                continue

            # Check specializations
            if required_specializations:
                if not all(spec in cap.specializations for spec in required_specializations):
                    continue

            # Check capacity
            if cap.current_load >= cap.max_concurrent:
                continue

            # Score candidate
            score = (
                cap.success_rate * 0.4 +
                (1.0 - cap.current_load / cap.max_concurrent) * 0.3 +
                (1.0 / (1 + cap.avg_completion_time.get(task_type, 30))) * 0.3
            )

            candidates.append((name, score))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def create_delegation(
        self,
        delegator: str,
        delegatee: str,
        task: Task,
        reason: str,
        priority: int = 1,
        deadline: Optional[datetime] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> DelegationRequest:
        """Create a new delegation request."""
        delegation = DelegationRequest(
            delegation_id=str(uuid.uuid4())[:8],
            delegator=delegator,
            delegatee=delegatee,
            task=task,
            reason=reason,
            priority=priority,
            deadline=deadline,
            context=context or {}
        )

        self.pending_delegations[delegation.delegation_id] = delegation

        # Update agent load
        if delegatee in self.agent_capabilities:
            self.agent_capabilities[delegatee].current_load += 1

        logger.info(f"Delegation created: {delegation.delegation_id} from {delegator} to {delegatee}")
        return delegation

    def accept_delegation(self, delegation_id: str) -> bool:
        """Accept a pending delegation."""
        delegation = self.pending_delegations.get(delegation_id)
        if not delegation:
            return False

        delegation.status = DelegationStatus.ACCEPTED
        delegation.accepted_at = datetime.now()
        del self.pending_delegations[delegation_id]
        self.active_delegations[delegation_id] = delegation

        logger.info(f"Delegation accepted: {delegation_id}")
        return True

    def reject_delegation(self, delegation_id: str, reason: str) -> bool:
        """Reject a pending delegation."""
        delegation = self.pending_delegations.get(delegation_id)
        if not delegation:
            return False

        delegation.status = DelegationStatus.REJECTED
        delegation.error = reason
        del self.pending_delegations[delegation_id]
        self.completed_delegations[delegation_id] = delegation

        # Release agent load
        if delegation.delegatee in self.agent_capabilities:
            self.agent_capabilities[delegation.delegatee].current_load = max(
                0, self.agent_capabilities[delegation.delegatee].current_load - 1
            )

        logger.info(f"Delegation rejected: {delegation_id} - {reason}")
        return True

    def complete_delegation(self, delegation_id: str, result: TaskResult) -> bool:
        """Mark delegation as completed with result."""
        delegation = self.active_delegations.get(delegation_id)
        if not delegation:
            return False

        delegation.status = DelegationStatus.COMPLETED
        delegation.completed_at = datetime.now()
        delegation.result = result

        del self.active_delegations[delegation_id]
        self.completed_delegations[delegation_id] = delegation

        # Release agent load
        if delegation.delegatee in self.agent_capabilities:
            self.agent_capabilities[delegation.delegatee].current_load = max(
                0, self.agent_capabilities[delegation.delegatee].current_load - 1
            )

        logger.info(f"Delegation completed: {delegation_id}")
        return True

    def fail_delegation(self, delegation_id: str, error: str) -> bool:
        """Mark delegation as failed."""
        delegation = self.active_delegations.get(delegation_id)
        if not delegation:
            return False

        delegation.status = DelegationStatus.FAILED
        delegation.completed_at = datetime.now()
        delegation.error = error

        del self.active_delegations[delegation_id]
        self.completed_delegations[delegation_id] = delegation

        # Release agent load
        if delegation.delegatee in self.agent_capabilities:
            self.agent_capabilities[delegation.delegatee].current_load = max(
                0, self.agent_capabilities[delegation.delegatee].current_load - 1
            )

        logger.info(f"Delegation failed: {delegation_id} - {error}")
        return True

    def get_delegation(self, delegation_id: str) -> Optional[DelegationRequest]:
        """Get delegation by ID."""
        for d in [self.pending_delegations, self.active_delegations, self.completed_delegations]:
            if delegation_id in d:
                return d[delegation_id]
        return None

    def get_agent_load(self, agent_name: str) -> Dict[str, Any]:
        """Get current load for an agent."""
        cap = self.agent_capabilities.get(agent_name)
        if not cap:
            return {"error": "Agent not found"}

        return {
            "agent": agent_name,
            "current_load": cap.current_load,
            "max_concurrent": cap.max_concurrent,
            "utilization": cap.current_load / cap.max_concurrent if cap.max_concurrent > 0 else 0,
            "success_rate": cap.success_rate
        }

    def get_pending_for_agent(self, agent_name: str) -> List[DelegationRequest]:
        """Get pending delegations for an agent."""
        return [
            d for d in self.pending_delegations.values()
            if d.delegatee == agent_name
        ]

    def get_active_for_agent(self, agent_name: str) -> List[DelegationRequest]:
        """Get active delegations for an agent."""
        return [
            d for d in self.active_delegations.values()
            if d.delegatee == agent_name
        ]


# Global instance
_delegation_manager: Optional[DelegationManager] = None


def get_delegation_manager() -> DelegationManager:
    """Get global delegation manager."""
    global _delegation_manager
    if _delegation_manager is None:
        _delegation_manager = DelegationManager()
    return _delegation_manager