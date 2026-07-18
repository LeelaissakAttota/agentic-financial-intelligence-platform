"""
Collaboration System - Multi-agent coordination and knowledge sharing.

Enables agents to share findings, coordinate on complex tasks, and
maintain shared context across the research workflow.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import logging

from memory.research_memory import get_memory_store, ResearchMemory, MemoryType
from config.settings import get_settings

logger = logging.getLogger(__name__)


class CollaborationType(str, Enum):
    """Types of agent collaboration."""
    SEQUENTIAL = "sequential"      # Output of one feeds into next
    PARALLEL = "parallel"          # Multiple agents work simultaneously
    CONSENSUS = "consensus"        # Multiple agents vote on result
    HIERARCHICAL = "hierarchical"  # Manager agent coordinates workers
    FEEDBACK_LOOP = "feedback_loop"  # Iterative refinement


class CoordinationSignal(str, Enum):
    """Signals for inter-agent coordination."""
    START_TASK = "start_task"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    NEED_INPUT = "need_input"
    PROVIDE_OUTPUT = "provide_output"
    REQUEST_CLARIFICATION = "request_clarification"
    SHARE_FINDING = "share_finding"
    CONFLICT_DETECTED = "conflict_detected"
    CONSENSUS_REACHED = "consensus_reached"
    ESCALATE = "escalate"


@dataclass
class AgentMessage:
    """Message between agents."""
    message_id: str
    sender: str
    recipient: str
    signal: CoordinationSignal
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None


@dataclass
class SharedFinding:
    """A finding shared between agents."""
    finding_id: str
    source_agent: str
    finding_type: str  # fact, insight, risk, opportunity, conflict
    content: Dict[str, Any]
    confidence: float
    tags: List[str] = field(default_factory=list)
    related_findings: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    validated_by: List[str] = field(default_factory=list)
    supersedes: Optional[str] = None


@dataclass
class CollaborationSession:
    """A collaboration session between multiple agents."""
    session_id: str
    participants: List[str]
    collaboration_type: CollaborationType
    goal: str
    context: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    messages: List[AgentMessage] = field(default_factory=list)
    shared_findings: List[SharedFinding] = field(default_factory=list)
    status: str = "active"
    result: Optional[Dict[str, Any]] = None


class AgentMailbox:
    """Message queue for an agent."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.inbox: List[AgentMessage] = []
        self.outbox: List[AgentMessage] = []
        self.subscriptions: Set[CoordinationSignal] = set()

    def send(self, recipient: str, signal: CoordinationSignal, payload: Dict[str, Any],
             correlation_id: Optional[str] = None, reply_to: Optional[str] = None) -> AgentMessage:
        """Send a message to another agent."""
        message = AgentMessage(
            message_id=str(uuid.uuid4())[:8],
            sender=self.agent_name,
            recipient=recipient,
            signal=signal,
            payload=payload,
            correlation_id=correlation_id,
            reply_to=reply_to
        )
        self.outbox.append(message)
        return message

    def receive(self, message: AgentMessage):
        """Receive a message from another agent."""
        self.inbox.append(message)

    def get_messages(self, signal: Optional[CoordinationSignal] = None) -> List[AgentMessage]:
        """Get messages, optionally filtered by signal."""
        if signal:
            return [m for m in self.inbox if m.signal == signal]
        return self.inbox.copy()

    def clear_processed(self):
        """Clear processed messages."""
        self.inbox.clear()


class CollaborationCoordinator:
    """
    Coordinates multi-agent collaboration sessions.

    Features:
    - Session management
    - Message routing
    - Finding aggregation
    - Conflict detection and resolution
    - Consensus building
    """

    def __init__(self):
        self.settings = get_settings()
        self.memory_store = get_memory_store()
        self.mailboxes: Dict[str, AgentMailbox] = {}
        self.sessions: Dict[str, CollaborationSession] = {}
        self.shared_knowledge: Dict[str, SharedFinding] = {}

    def register_agent(self, agent_name: str) -> AgentMailbox:
        """Register an agent with the coordinator."""
        if agent_name not in self.mailboxes:
            self.mailboxes[agent_name] = AgentMailbox(agent_name)
        return self.mailboxes[agent_name]

    def get_mailbox(self, agent_name: str) -> Optional[AgentMailbox]:
        """Get agent's mailbox."""
        return self.mailboxes.get(agent_name)

    def send_message(self, sender: str, recipient: str, signal: CoordinationSignal,
                     payload: Dict[str, Any], correlation_id: Optional[str] = None,
                     reply_to: Optional[str] = None) -> bool:
        """Route a message between agents."""
        sender_box = self.get_mailbox(sender)
        recipient_box = self.get_mailbox(recipient)

        if not sender_box or not recipient_box:
            logger.warning(f"Agent not registered: sender={sender}, recipient={recipient}")
            return False

        message = sender_box.send(recipient, signal, payload, correlation_id, reply_to)
        recipient_box.receive(message)

        # Log to session if part of one
        if correlation_id and correlation_id in self.sessions:
            self.sessions[correlation_id].messages.append(message)

        return True

    def broadcast(self, sender: str, signal: CoordinationSignal,
                  payload: Dict[str, Any], recipients: List[str]) -> int:
        """Send message to multiple agents."""
        count = 0
        for recipient in recipients:
            if self.send_message(sender, recipient, signal, payload):
                count += 1
        return count

    def create_session(
        self,
        participants: List[str],
        collaboration_type: CollaborationType,
        goal: str,
        context: Dict[str, Any]
    ) -> CollaborationSession:
        """Create a new collaboration session."""
        session = CollaborationSession(
            session_id=str(uuid.uuid4())[:8],
            participants=participants,
            collaboration_type=collaboration_type,
            goal=goal,
            context=context
        )

        # Register all participants
        for p in participants:
            self.register_agent(p)

        self.sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[CollaborationSession]:
        """Get session by ID."""
        return self.sessions.get(session_id)

    def share_finding(self, finding: SharedFinding):
        """Share a finding with relevant agents."""
        self.shared_knowledge[finding.finding_id] = finding

        # Store in memory for persistence
        asyncio.create_task(self._persist_finding(finding))

        # Notify relevant agents
        logger.info(f"Finding shared: {finding.finding_id} by {finding.source_agent}")

    async def _persist_finding(self, finding: SharedFinding):
        """Persist finding to memory store."""
        try:
            await self.memory_store.store_agent_output(
                company=finding.content.get("company", "unknown"),
                agent_type=finding.source_agent,
                output={
                    "finding_id": finding.finding_id,
                    "finding_type": finding.finding_type,
                    "content": finding.content,
                    "confidence": finding.confidence,
                    "tags": finding.tags,
                    "validated_by": finding.validated_by
                }
            )
        except Exception as e:
            logger.error(f"Failed to persist finding: {e}")

    def detect_conflicts(self, findings: List[SharedFinding]) -> List[Dict[str, Any]]:
        """Detect conflicting findings."""
        conflicts = []
        for i, f1 in enumerate(findings):
            for f2 in findings[i+1:]:
                if self._are_conflicting(f1, f2):
                    conflicts.append({
                        "finding_1": f1.finding_id,
                        "finding_2": f2.finding_id,
                        "type": "contradiction",
                        "description": f"Conflicting {f1.finding_type} findings: {f1.source_agent} vs {f2.source_agent}"
                    })
        return conflicts

    def _are_conflicting(self, f1: SharedFinding, f2: SharedFinding) -> bool:
        """Check if two findings conflict."""
        # Same type, different sources, opposite conclusions
        if f1.finding_type != f2.finding_type or f1.source_agent == f2.source_agent:
            return False

        # Check for opposing sentiment/conclusions
        c1 = str(f1.content).lower()
        c2 = str(f2.content).lower()

        # Simple conflict detection - could be enhanced
        positive_terms = ["bullish", "positive", "buy", "strong", "growth", "outperform"]
        negative_terms = ["bearish", "negative", "sell", "weak", "decline", "underperform"]

        f1_pos = any(t in c1 for t in positive_terms)
        f1_neg = any(t in c1 for t in negative_terms)
        f2_pos = any(t in c2 for t in positive_terms)
        f2_neg = any(t in c2 for t in negative_terms)

        return (f1_pos and f2_neg) or (f1_neg and f2_pos)

    def build_consensus(self, findings: List[SharedFinding]) -> Dict[str, Any]:
        """Build consensus from multiple findings."""
        if not findings:
            return {"consensus": None, "agreement": 0.0}

        # Group by finding type
        by_type = {}
        for f in findings:
            if f.finding_type not in by_type:
                by_type[f.finding_type] = []
            by_type[f.finding_type].append(f)

        consensus = {}
        total_agreement = 0.0

        for ftype, group in by_type.items():
            # Weight by confidence
            weighted_sum = sum(f.confidence for f in group)
            avg_confidence = weighted_sum / len(group)

            # Check agreement direction
            sentiments = []
            for f in group:
                content = str(f.content).lower()
                if any(t in content for t in ["bullish", "positive", "buy", "strong", "growth"]):
                    sentiments.append(1)
                elif any(t in content for t in ["bearish", "negative", "sell", "weak", "decline"]):
                    sentiments.append(-1)
                else:
                    sentiments.append(0)

            agreement = len(set(sentiments)) == 1 if sentiments else False

            consensus[ftype] = {
                "agreement": agreement,
                "avg_confidence": avg_confidence,
                "count": len(group),
                "sentiment": sum(sentiments) / len(sentiments) if sentiments else 0
            }
            total_agreement += avg_confidence

        return {
            "consensus": consensus,
            "overall_agreement": total_agreement / len(by_type) if by_type else 0.0,
            "participants": len(findings)
        }

    def get_shared_knowledge(self, tags: Optional[List[str]] = None) -> List[SharedFinding]:
        """Get shared knowledge, optionally filtered by tags."""
        findings = list(self.shared_knowledge.values())
        if tags:
            findings = [f for f in findings if any(t in f.tags for t in tags)]
        return sorted(findings, key=lambda f: f.created_at, reverse=True)


# Global instance
_coordinator: Optional[CollaborationCoordinator] = None


def get_collaboration_coordinator() -> CollaborationCoordinator:
    """Get global collaboration coordinator."""
    global _coordinator
    if _coordinator is None:
        _coordinator = CollaborationCoordinator()
    return _coordinator