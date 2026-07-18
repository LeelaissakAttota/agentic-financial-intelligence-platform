"""
Consensus Building - Multi-agent agreement and decision making.

Implements various consensus mechanisms for agents to agree on
findings, recommendations, and decisions.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

from config.settings import get_settings

logger = logging.getLogger(__name__)


class ConsensusMethod(str, Enum):
    """Methods for reaching consensus."""
    MAJORITY = "majority"           # Simple majority vote
    WEIGHTED = "weighted"           # Weighted by agent confidence/expertise
    UNANIMOUS = "unanimous"         # Requires full agreement
    THRESHOLD = "threshold"         # Minimum agreement percentage
    RANKED_CHOICE = "ranked_choice" # Ranked choice voting
    BORDA_COUNT = "borda_count"     # Borda count method
    CONDORCET = "condorcet"         # Condorcet method


class VoteType(str, Enum):
    """Types of votes agents can cast."""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"
    MODIFY = "modify"               # Approve with modifications


@dataclass
class AgentVote:
    """Single agent's vote."""
    agent_id: str
    agent_type: str
    vote: VoteType
    confidence: float              # 0-1 confidence in vote
    reasoning: Optional[str] = None
    modifications: Optional[Dict[str, Any]] = None
    weight: float = 1.0            # Voting weight
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConsensusProposal:
    """Proposal for consensus."""
    proposal_id: str
    title: str
    description: str
    proposed_by: str
    options: List[str]             # Options to vote on
    required_quorum: float = 0.5   # Minimum participation
    consensus_threshold: float = 0.6  # Agreement threshold
    method: ConsensusMethod = ConsensusMethod.WEIGHTED
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsensusResult:
    """Result of consensus process."""
    proposal_id: str
    consensus_reached: bool
    winning_option: Optional[str]
    agreement_score: float         # 0-1 level of agreement
    votes: List[AgentVote]
    participation_rate: float
    method_used: ConsensusMethod
    completed_at: datetime
    dissenting_agents: List[str] = field(default_factory=list)
    minority_report: Optional[str] = None


class ConsensusBuilder:
    """
    Builds consensus among multiple agents.

    Supports multiple voting methods and provides detailed
    analysis of agreement levels and dissenting views.
    """

    def __init__(self):
        self.settings = get_settings()
        self.active_proposals: Dict[str, ConsensusProposal] = {}
        self.vote_history: Dict[str, List[AgentVote]] = {}
        self.results: Dict[str, ConsensusResult] = {}

    def create_proposal(
        self,
        title: str,
        description: str,
        proposed_by: str,
        options: List[str],
        required_quorum: float = 0.5,
        consensus_threshold: float = 0.6,
        method: ConsensusMethod = ConsensusMethod.WEIGHTED,
        deadline_hours: int = 24
    ) -> ConsensusProposal:
        """Create a new consensus proposal."""
        proposal = ConsensusProposal(
            proposal_id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            proposed_by=proposed_by,
            options=options,
            required_quorum=required_quorum,
            consensus_threshold=consensus_threshold,
            method=method,
            deadline=datetime.now().replace(hour=23, minute=59) if deadline_hours > 0 else None
        )

        self.active_proposals[proposal.proposal_id] = proposal
        self.vote_history[proposal.proposal_id] = []

        logger.info(f"Created consensus proposal: {proposal.proposal_id} - {title}")
        return proposal

    def cast_vote(
        self,
        proposal_id: str,
        agent_id: str,
        agent_type: str,
        vote: VoteType,
        confidence: float,
        reasoning: Optional[str] = None,
        modifications: Optional[Dict[str, Any]] = None,
        weight: float = 1.0
    ) -> bool:
        """Cast a vote on a proposal."""
        proposal = self.active_proposals.get(proposal_id)
        if not proposal:
            logger.warning(f"Proposal not found: {proposal_id}")
            return False

        # Check deadline
        if proposal.deadline and datetime.now() > proposal.deadline:
            logger.warning(f"Voting deadline passed for {proposal_id}")
            return False

        # Check if agent already voted
        existing_votes = [v for v in self.vote_history[proposal_id] if v.agent_id == agent_id]
        if existing_votes:
            logger.warning(f"Agent {agent_id} already voted on {proposal_id}")
            return False

        # Validate vote option
        if vote in [VoteType.APPROVE, VoteType.REJECT] and len(proposal.options) > 1:
            # For multi-option, vote should specify which option
            pass  # In full implementation, would validate option selection

        agent_vote = AgentVote(
            agent_id=agent_id,
            agent_type=agent_type,
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
            modifications=modifications,
            weight=weight
        )

        self.vote_history[proposal_id].append(agent_vote)
        logger.info(f"Vote cast: {agent_id} -> {vote.value} on {proposal_id}")
        return True

    def get_votes(self, proposal_id: str) -> List[AgentVote]:
        """Get all votes for a proposal."""
        return self.vote_history.get(proposal_id, [])

    def check_quorum(self, proposal_id: str, total_agents: int) -> bool:
        """Check if quorum is met."""
        proposal = self.active_proposals.get(proposal_id)
        if not proposal:
            return False

        votes = self.vote_history.get(proposal_id, [])
        participation = len(votes) / total_agents if total_agents > 0 else 0
        return participation >= proposal.required_quorum

    def calculate_consensus(self, proposal_id: str, total_agents: int) -> ConsensusResult:
        """Calculate consensus result for a proposal."""
        proposal = self.active_proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal not found: {proposal_id}")

        votes = self.vote_history.get(proposal_id, [])

        if not votes:
            return ConsensusResult(
                proposal_id=proposal_id,
                consensus_reached=False,
                winning_option=None,
                agreement_score=0.0,
                votes=[],
                participation_rate=0.0,
                method_used=proposal.method,
                completed_at=datetime.now()
            )

        # Calculate based on method
        if proposal.method == ConsensusMethod.MAJORITY:
            result = self._majority_vote(proposal, votes)
        elif proposal.method == ConsensusMethod.WEIGHTED:
            result = self._weighted_vote(proposal, votes)
        elif proposal.method == ConsensusMethod.UNANIMOUS:
            result = self._unanimous_vote(proposal, votes)
        elif proposal.method == ConsensusMethod.THRESHOLD:
            result = self._threshold_vote(proposal, votes)
        elif proposal.method == ConsensusMethod.RANKED_CHOICE:
            result = self._ranked_choice_vote(proposal, votes)
        elif proposal.method == ConsensusMethod.BORDA_COUNT:
            result = self._borda_count(proposal, votes)
        else:
            result = self._weighted_vote(proposal, votes)

        # Check quorum
        participation_rate = len(votes) / max(1, len(set(v.agent_id for v in votes)))
        if participation_rate < proposal.required_quorum:
            result.consensus_reached = False

        result.participation_rate = participation_rate
        result.method_used = proposal.method
        result.completed_at = datetime.now()

        # Identify dissenting agents
        if result.winning_option:
            result.dissenting_agents = [
                v.agent_id for v in votes
                if v.vote == VoteType.REJECT and v.confidence > 0.5
            ]

        self.results[proposal_id] = result
        return result

    def _majority_vote(self, proposal: ConsensusProposal, votes: List[AgentVote]) -> ConsensusResult:
        """Simple majority vote."""
        option_votes = {opt: 0 for opt in proposal.options}

        for vote in votes:
            if vote.vote == VoteType.APPROVE:
                # Assume first option if not specified
                option = vote.modifications.get("option", proposal.options[0]) if vote.modifications else proposal.options[0]
                if option in option_votes:
                    option_votes[option] += 1
            elif vote.vote == VoteType.REJECT:
                pass  # Rejection doesn't count for options

        if option_votes:
            winner = max(option_votes, key=option_votes.get)
            total = sum(option_votes.values())
            agreement = option_votes[winner] / total if total > 0 else 0
        else:
            winner = None
            agreement = 0.0

        return ConsensusResult(
            proposal_id=proposal.proposal_id,
            consensus_reached=agreement >= proposal.consensus_threshold,
            winning_option=winner,
            agreement_score=agreement,
            votes=votes,
            participation_rate=0.0,
            method_used=ConsensusMethod.MAJORITY,
            completed_at=datetime.now()
        )

    def _weighted_vote(self, proposal: ConsensusProposal, votes: List[AgentVote]) -> ConsensusResult:
        """Weighted vote by agent confidence and weight."""
        option_scores = {opt: 0.0 for opt in proposal.options}
        total_weight = 0.0

        for vote in votes:
            weight = vote.weight * vote.confidence
            total_weight += weight

            if vote.vote == VoteType.APPROVE:
                option = vote.modifications.get("option", proposal.options[0]) if vote.modifications else proposal.options[0]
                if option in option_scores:
                    option_scores[option] += weight

        if option_scores:
            winner = max(option_scores, key=option_scores.get)
            agreement = option_scores[winner] / total_weight if total_weight > 0 else 0
        else:
            winner = None
            agreement = 0.0

        return ConsensusResult(
            proposal_id=proposal.proposal_id,
            consensus_reached=agreement >= proposal.consensus_threshold,
            winning_option=winner,
            agreement_score=agreement,
            votes=votes,
            participation_rate=0.0,
            method_used=ConsensusMethod.WEIGHTED,
            completed_at=datetime.now()
        )

    def _unanimous_vote(self, proposal: ConsensusProposal, votes: List[AgentVote]) -> ConsensusResult:
        """Require unanimous agreement."""
        all_approve = all(v.vote == VoteType.APPROVE for v in votes)

        if all_approve:
            winner = votes[0].modifications.get("option", proposal.options[0]) if votes[0].modifications else proposal.options[0]
            agreement = 1.0
        else:
            winner = None
            agreement = 0.0

        return ConsensusResult(
            proposal_id=proposal.proposal_id,
            consensus_reached=all_approve,
            winning_option=winner,
            agreement_score=agreement,
            votes=votes,
            participation_rate=0.0,
            method_used=ConsensusMethod.UNANIMOUS,
            completed_at=datetime.now()
        )

    def _threshold_vote(self, proposal: ConsensusProposal, votes: List[AgentVote]) -> ConsensusResult:
        """Threshold-based voting."""
        approve_count = sum(1 for v in votes if v.vote == VoteType.APPROVE)
        total = len(votes)
        agreement = approve_count / total if total > 0 else 0

        winner = proposal.options[0] if agreement >= proposal.consensus_threshold else None

        return ConsensusResult(
            proposal_id=proposal.proposal_id,
            consensus_reached=agreement >= proposal.consensus_threshold,
            winning_option=winner,
            agreement_score=agreement,
            votes=votes,
            participation_rate=0.0,
            method_used=ConsensusMethod.THRESHOLD,
            completed_at=datetime.now()
        )

    def _ranked_choice_vote(self, proposal: ConsensusProposal, votes: List[AgentVote]) -> ConsensusResult:
        """Ranked choice (instant runoff) voting."""
        # Simplified - would need full ranked choice implementation
        return self._weighted_vote(proposal, votes)

    def _borda_count(self, proposal: ConsensusProposal, votes: List[AgentVote]) -> ConsensusResult:
        """Borda count voting."""
        scores = {opt: 0 for opt in proposal.options}

        for vote in votes:
            if vote.vote == VoteType.APPROVE and vote.modifications:
                ranking = vote.modifications.get("ranking", [])
                for i, option in enumerate(ranking):
                    if option in scores:
                        scores[option] += len(proposal.options) - i

        winner = max(scores, key=scores.get) if scores else None
        total = sum(scores.values())
        agreement = scores[winner] / total if total > 0 and winner else 0

        return ConsensusResult(
            proposal_id=proposal.proposal_id,
            consensus_reached=agreement >= proposal.consensus_threshold,
            winning_option=winner,
            agreement_score=agreement,
            votes=votes,
            participation_rate=0.0,
            method_used=ConsensusMethod.BORDA_COUNT,
            completed_at=datetime.now()
        )

    def get_result(self, proposal_id: str) -> Optional[ConsensusResult]:
        """Get consensus result."""
        return self.results.get(proposal_id)

    def close_proposal(self, proposal_id: str) -> bool:
        """Close a proposal and finalize results."""
        if proposal_id not in self.active_proposals:
            return False

        # Calculate final result if not already done
        if proposal_id not in self.results:
            # Would need total_agents - using vote count as proxy
            self.calculate_consensus(proposal_id, len(self.vote_history[proposal_id]))

        del self.active_proposals[proposal_id]
        return True


class ConsensusAnalyzer:
    """Analyzes consensus patterns and dissent."""

    def __init__(self, builder: ConsensusBuilder):
        self.builder = builder

    def analyze_dissent(self, proposal_id: str) -> Dict[str, Any]:
        """Analyze dissenting votes."""
        result = self.builder.get_result(proposal_id)
        if not result:
            return {"error": "No result found"}

        dissenting = [v for v in result.votes if v.agent_id in result.dissenting_agents]

        return {
            "dissent_count": len(dissenting),
            "dissent_rate": len(dissenting) / len(result.votes) if result.votes else 0,
            "dissenting_agents": [v.agent_id for v in dissenting],
            "dissent_reasons": [v.reasoning for v in dissenting if v.reasoning],
            "avg_dissent_confidence": sum(v.confidence for v in dissenting) / len(dissenting) if dissenting else 0,
            "dissent_modifications": [v.modifications for v in dissenting if v.modifications]
        }

    def analyze_agreement_quality(self, proposal_id: str) -> Dict[str, Any]:
        """Analyze quality of agreement."""
        result = self.builder.get_result(proposal_id)
        if not result:
            return {"error": "No result found"}

        votes = result.votes
        if not votes:
            return {"error": "No votes"}

        # Confidence distribution
        confidences = [v.confidence for v in votes]
        avg_confidence = sum(confidences) / len(confidences)

        # Agreement strength
        agreement_strength = result.agreement_score

        # Participation
        participation = result.participation_rate

        return {
            "agreement_strength": agreement_strength,
            "avg_confidence": avg_confidence,
            "confidence_distribution": {
                "high": sum(1 for c in confidences if c > 0.8),
                "medium": sum(1 for c in confidences if 0.5 <= c <= 0.8),
                "low": sum(1 for c in confidences if c < 0.5)
            },
            "participation_rate": participation,
            "consensus_quality": "strong" if agreement_strength > 0.8 and avg_confidence > 0.7 and participation > 0.8
                                    else "moderate" if agreement_strength > 0.6 and avg_confidence > 0.5
                                    else "weak"
        }

    def generate_minority_report(self, proposal_id: str) -> Optional[str]:
        """Generate minority report from dissenting views."""
        result = self.builder.get_result(proposal_id)
        if not result or not result.dissenting_agents:
            return None

        dissenting_votes = [v for v in result.votes if v.agent_id in result.dissenting_agents]

        report = f"MINORITY REPORT - Proposal: {proposal_id}\n"
        report += f"Consensus: {result.winning_option} ({result.agreement_score:.0%} agreement)\n"
        report += f"Dissenting: {len(dissenting_votes)} of {len(result.votes)} agents\n\n"

        for vote in dissenting_votes:
            report += f"Agent: {vote.agent_id} ({vote.agent_type})\n"
            report += f"  Vote: {vote.vote.value}\n"
            report += f"  Confidence: {vote.confidence:.0%}\n"
            if vote.reasoning:
                report += f"  Reasoning: {vote.reasoning}\n"
            if vote.modifications:
                report += f"  Proposed modifications: {vote.modifications}\n"
            report += "\n"

        return report


# Global instances
_consensus_builder: Optional[ConsensusBuilder] = None
_consensus_analyzer: Optional[ConsensusAnalyzer] = None


def get_consensus_builder() -> ConsensusBuilder:
    """Get global consensus builder."""
    global _consensus_builder
    if _consensus_builder is None:
        _consensus_builder = ConsensusBuilder()
    return _consensus_builder


def get_consensus_analyzer() -> ConsensusAnalyzer:
    """Get global consensus analyzer."""
    global _consensus_analyzer
    if _consensus_analyzer is None:
        _consensus_analyzer = ConsensusAnalyzer(get_consensus_builder())
    return _consensus_analyzer