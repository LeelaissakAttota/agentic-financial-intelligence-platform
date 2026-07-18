"""
Multi-Agent Debate - Structured debate framework for research consensus.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

from .thesis_generator import ThesisComponent, ThesisType, ThesisConfidence

logger = logging.getLogger(__name__)


class DebateRole(str, Enum):
    """Roles in the debate."""
    PROPOSER = "proposer"           # Presents the thesis
    SKEPTIC = "skeptic"             # Challenges the thesis
    MODERATOR = "moderator"         # Ensures fair process
    MEDIATOR = "mediator"           # Finds common ground
    VALIDATOR = "validator"         # Validates claims with evidence


class DebatePhase(str, Enum):
    """Phases of the debate."""
    OPENING = "opening"             # Initial positions
    REBUTTAL = "rebuttal"           # Responses to challenges
    EVIDENCE_REVIEW = "evidence_review"  # Deep dive into evidence
    SYNTHESIS = "synthesis"         # Finding common ground
    VOTING = "voting"               # Final positions
    CONCLUSION = "conclusion"       # Final output


@dataclass
class DebatePosition:
    """Position taken by a participant."""
    participant_id: str
    role: DebateRole
    stance: str  # "support", "oppose", "neutral"
    thesis_components: List[ThesisComponent] = field(default_factory=list)
    key_arguments: List[str] = field(default_factory=list)
    evidence_cited: List[str] = field(default_factory=list)
    confidence: float = 0.5
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DebateRound:
    """Single round of debate."""
    round_number: int
    phase: DebatePhase
    participants: List[str]
    arguments: Dict[str, str] = field(default_factory=dict)  # participant_id -> argument
    evidence_presented: Dict[str, List[str]] = field(default_factory=dict)  # participant_id -> evidence_ids
    challenges: List[Dict[str, Any]] = field(default_factory=list)
    responses: Dict[str, str] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


@dataclass
class DebateResult:
    """Result of a debate session."""
    debate_id: str
    thesis: str
    participants: List[str]
    rounds: List[DebateRound]
    final_positions: Dict[str, DebatePosition]
    consensus_reached: bool
    consensus_thesis: Optional[str] = None
    confidence: float = 0.0
    dissenting_views: List[str] = field(default_factory=list)
    key_agreements: List[str] = field(default_factory=list)
    key_disagreements: List[str] = field(default_factory=list)
    completed_at: datetime = field(default_factory=datetime.utcnow)


class MultiAgentDebate:
    """
    Structured multi-agent debate for research consensus.
    Implements formal debate structure with roles, phases, and voting.
    """
    
    def __init__(self):
        self._debates: Dict[str, DebateResult] = {}
        self._active_debates: Dict[str, asyncio.Task] = {}
        
        # Debate configuration
        self.max_rounds = 5
        self.max_participants = 6
        self.time_per_round = 60  # seconds
        self.voting_threshold = 0.66  # 2/3 majority for consensus
    
    async def conduct_debate(
        self,
        thesis: str,
        participants: List[Dict[str, Any]],  # [{"agent_id": "x", "role": "proposer/skeptic/..."}]
        evidence: Dict[str, List],  # From evidence lookup
        max_rounds: Optional[int] = None
    ) -> DebateResult:
        """Conduct a structured debate on a thesis."""
        
        debate_id = f"debate_{datetime.utcnow().timestamp()}"
        max_rounds = max_rounds or self.max_rounds
        
        # Validate participants
        if len(participants) > self.max_participants:
            raise ValueError(f"Maximum {self.max_participants} participants allowed")
        
        required_roles = {DebateRole.PROPOSER, DebateRole.SKEPTIC}
        participant_roles = {p["role"] for p in participants}
        if not required_roles.issubset(participant_roles):
            raise ValueError(f"Debate requires at least proposer and skeptic roles")
        
        # Initialize positions
        positions = {}
        for p in participants:
            positions[p["agent_id"]] = DebatePosition(
                participant_id=p["agent_id"],
                role=DebateRole(p["role"]),
                stance="support" if p["role"] == "proposer" else "oppose"
            )
        
        # Create debate record
        debate = DebateResult(
            debate_id=debate_id,
            thesis=thesis,
            participants=[p["agent_id"] for p in participants],
            rounds=[],
            final_positions=positions
        )
        
        # Conduct debate rounds
        for round_num in range(1, max_rounds + 1):
            round_result = await self._conduct_round(
                debate_id, round_num, positions, evidence, thesis
            )
            debate.rounds.append(round_result)
            
            # Check for early consensus
            if self._check_consensus(positions):
                debate.consensus_reached = True
                break
        
        # Final voting
        await self._final_voting(debate, positions, evidence)
        
        # Calculate final confidence
        debate.confidence = self._calculate_confidence(debate, positions)
        
        # Extract agreements/disagreements
        debate.key_agreements, debate.key_disagreements = self._extract_agreements_disagreements(debate.rounds)
        debate.dissenting_views = self._extract_dissenting_views(positions)
        
        if debate.consensus_reached:
            debate.consensus_thesis = self._synthesize_consensus(thesis, positions, evidence)
        
        self._debates[debate_id] = debate
        return debate
    
    async def _conduct_round(
        self,
        debate_id: str,
        round_num: int,
        positions: Dict[str, DebatePosition],
        evidence: Dict[str, List],
        thesis: str
    ) -> DebateRound:
        """Conduct a single debate round."""
        
        # Determine phase
        if round_num == 1:
            phase = DebatePhase.OPENING
        elif round_num == 2:
            phase = DebatePhase.REBUTTAL
        elif round_num == 3:
            phase = DebatePhase.EVIDENCE_REVIEW
        elif round_num == 4:
            phase = DebatePhase.SYNTHESIS
        else:
            phase = DebatePhase.CONCLUSION
        
        round_obj = DebateRound(
            round_number=round_num,
            phase=phase,
            participants=list(positions.keys())
        )
        
        # Each participant makes their case
        for participant_id, position in positions.items():
            if position.role == DebateRole.PROPOSER:
                argument = await self._generate_proposer_argument(position, thesis, evidence, round_num)
            elif position.role == DebateRole.SKEPTIC:
                argument = await self._generate_skeptic_argument(position, thesis, evidence, round_num)
            elif position.role == DebateRole.VALIDATOR:
                argument = await self._generate_validator_argument(position, thesis, evidence, round_num)
            elif position.role == DebateRole.MODERATOR:
                argument = await self._generate_moderator_argument(position, thesis, evidence, round_num)
            else:
                argument = await self._generate_general_argument(position, thesis, evidence, round_num)
            
            round_obj.arguments[participant_id] = argument
        
        # Participants respond to each other (rebuttal phase)
        if round_num >= 2:
            for participant_id, position in positions.items():
                response = await self._generate_rebuttal(position, round_obj.arguments, round_num)
                round_obj.responses[participant_id] = response
        
        # Evidence review
        if phase == DebatePhase.EVIDENCE_REVIEW:
            for participant_id, position in positions.items():
                cited = await self._cite_evidence(position, evidence, thesis)
                round_obj.evidence_presented[participant_id] = cited
                position.evidence_cited.extend(cited)
        
        # Update positions based on round
        for participant_id, position in positions.items():
            position.updated_at = datetime.utcnow()
        
        round_obj.completed_at = datetime.utcnow()
        return round_obj
    
    async def _generate_proposer_argument(
        self,
        position: DebatePosition,
        thesis: str,
        evidence: Dict[str, List],
        round_num: int
    ) -> str:
        """Generate proposer's argument."""
        if round_num == 1:
            # Opening statement
            supporting = evidence.get("supporting", [])
            key_points = [e.evidence.summary for e in supporting[:3] if e.evidence]
            
            return (
                f"I propose the thesis: {thesis}. "
                f"Key supporting evidence: {'; '.join(key_points)}. "
                f"This thesis is well-supported by {len(supporting)} pieces of evidence."
            )
        else:
            # Rebuttal or reinforcement
            challenges = [r for p, r in position.thesis_components if p.role == DebateRole.SKEPTIC]
            return (
                f"Reinforcing thesis: {thesis}. "
                f"Addressing {len(challenges)} challenges raised. "
                f"Evidence remains compelling: {len(position.evidence_cited)} citations."
            )
    
    async def _generate_skeptic_argument(
        self,
        position: DebatePosition,
        thesis: str,
        evidence: Dict[str, List],
        round_num: int
    ) -> str:
        """Generate skeptic's argument."""
        if round_num == 1:
            # Opening challenge
            opposing = evidence.get("opposing", [])
            key_challenges = [e.evidence.summary for e in opposing[:3] if e.evidence]
            
            return (
                f"I challenge the thesis: {thesis}. "
                f"Key concerns: {'; '.join(key_challenges)}. "
                f"Found {len(opposing)} pieces of contradictory evidence."
            )
        else:
            # Rebuttal
            return (
                f"Maintaining skepticism on: {thesis}. "
                f"Proposer's rebuttal insufficient. "
                f"Need stronger evidence for {len(position.key_arguments)} key claims."
            )
    
    async def _generate_validator_argument(
        self,
        position: DebatePosition,
        thesis: str,
        evidence: Dict[str, List],
        round_num: int
    ) -> str:
        """Generate validator's argument."""
        all_evidence = []
        for ev_list in evidence.values():
            all_evidence.extend([e for e in ev_list if e.evidence])
        
        validated = sum(1 for e in all_evidence if e.evidence.confidence > 0.7)
        total = len(all_evidence)
        
        return (
            f"Evidence validation: {validated}/{total} sources meet confidence threshold. "
            f"Methodology review: evidence quality is {'high' if validated/total > 0.7 else 'moderate'}. "
            f"Recommendation: {'support' if validated/total > 0.6 else 'caution'}."
        )
    
    async def _generate_moderator_argument(
        self,
        position: DebatePosition,
        thesis: str,
        evidence: Dict[str, List],
        round_num: int
    ) -> str:
        """Generate moderator's argument."""
        support_count = len(evidence.get("supporting", []))
        oppose_count = len(evidence.get("opposing", []))
        
        return (
            f"Moderating: {support_count} supporting, {oppose_count} opposing evidence pieces. "
            f"Ensuring fair process. Both sides present arguments clearly."
        )
    
    async def _generate_general_argument(
        self,
        position: DebatePosition,
        thesis: str,
        evidence: Dict[str, List],
        round_num: int
    ) -> str:
        """Generate general participant argument."""
        return f"Participant {position.participant_id} ({position.role.value}) provides input on: {thesis}"
    
    async def _generate_rebuttal(
        self,
        position: DebatePosition,
        round_arguments: Dict[str, str],
        round_num: int
    ) -> str:
        """Generate rebuttal to other arguments."""
        other_args = {pid: arg for pid, arg in round_arguments.items() if pid != position.participant_id}
        
        if not other_args:
            return "No opposing arguments to address."
        
        if position.role == DebateRole.SKEPTIC:
            return "Proposer's arguments do not adequately address the fundamental concerns raised."
        elif position.role == DebateRole.PROPOSER:
            return "Skeptic's concerns are acknowledged but outweighed by the preponderance of evidence."
        
        return f"Reviewed {len(other_args)} arguments. Position updated based on new information."
    
    async def _cite_evidence(
        self,
        position: DebatePosition,
        evidence: Dict[str, List],
        thesis: str
    ) -> List[str]:
        """Select evidence to cite."""
        all_ev = []
        for ev_list in evidence.values():
            all_ev.extend([e for e in ev_list if e.evidence])
        
        # Sort by relevance and confidence
        all_ev.sort(key=lambda x: x.relevance_score * x.evidence.confidence, reverse=True)
        
        # Return top 5 evidence IDs
        return [e.evidence.id for e in all_ev[:5]]
    
    def _check_consensus(self, positions: Dict[str, DebatePosition]) -> bool:
        """Check if consensus has been reached."""
        stances = [p.stance for p in positions.values()]
        support_count = stances.count("support")
        total = len(stances)
        
        if total == 0:
            return False
        
        return support_count / total >= self.voting_threshold
    
    async def _final_voting(
        self,
        debate: DebateResult,
        positions: Dict[str, DebatePosition],
        evidence: Dict[str, List]
    ) -> None:
        """Conduct final voting."""
        # Each participant votes
        votes = {}
        for participant_id, position in positions.items():
            # Position stance becomes vote
            votes[participant_id] = position.stance
        
        # Calculate consensus
        support = sum(1 for v in votes.values() if v == "support")
        oppose = sum(1 for v in votes.values() if v == "oppose")
        neutral = sum(1 for v in votes.values() if v == "neutral")
        
        debate.consensus_reached = support / len(votes) >= self.voting_threshold
    
    def _calculate_confidence(
        self,
        debate: DebateResult,
        positions: Dict[str, DebatePosition]
    ) -> float:
        """Calculate overall debate confidence."""
        # Base confidence from proposer
        proposer = next((p for p in positions.values() if p.role == DebateRole.PROPOSER), None)
        base_confidence = proposer.confidence if proposer else 0.5
        
        # Adjust for consensus
        if debate.consensus_reached:
            base_confidence = min(0.95, base_confidence + 0.15)
        else:
            base_confidence = max(0.3, base_confidence - 0.1)
        
        # Adjust for evidence quality
        validator = next((p for p in positions.values() if p.role == DebateRole.VALIDATOR), None)
        if validator:
            base_confidence = (base_confidence + validator.confidence) / 2
        
        return base_confidence
    
    def _extract_agreements_disagreements(
        self,
        rounds: List[DebateRound]
    ) -> Tuple[List[str], List[str]]:
        """Extract key agreements and disagreements from debate rounds."""
        agreements = []
        disagreements = []
        
        for round_obj in rounds:
            # Look for agreement/disagreement language in arguments
            for participant, argument in round_obj.arguments.items():
                arg_lower = argument.lower()
                if any(word in arg_lower for word in ["agree", "concede", "acknowledge", "valid point"]):
                    agreements.append(f"{participant}: {argument[:200]}")
                if any(word in arg_lower for word in ["disagree", "challenge", "refute", "incorrect"]):
                    disagreements.append(f"{participant}: {argument[:200]}")
        
        return agreements[:5], disagreements[:5]
    
    def _extract_dissenting_views(self, positions: Dict[str, DebatePosition]) -> List[str]:
        """Extract dissenting views from final positions."""
        dissenting = []
        for pid, pos in positions.items():
            if pos.stance == "oppose":
                dissenting.append(f"{pid} ({pos.role.value}): {pos.key_arguments[0] if pos.key_arguments else 'Opposes thesis'}")
        return dissenting
    
    def _synthesize_consensus(
        self,
        thesis: str,
        positions: Dict[str, DebatePosition],
        evidence: Dict[str, List]
    ) -> str:
        """Synthesize consensus thesis from debate."""
        # Take proposer's thesis and modify based on valid skeptic points
        base_thesis = thesis
        
        # Get valid challenges from skeptic
        skeptic = next((p for p in positions.values() if p.role == DebateRole.SKEPTIC), None)
        if skeptic and skeptic.key_arguments:
            valid_challenges = [arg for arg in skeptic.key_arguments if "evidence" in arg.lower() or "data" in arg.lower()]
            if valid_challenges:
                base_thesis += f" With caveats: {'; '.join(valid_challenges[:2])}"
        
        return base_thesis
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_debates": len(self._debates),
            "active_debates": len(self._active_debates),
            "config": {
                "max_rounds": self.max_rounds,
                "max_participants": self.max_participants,
                "voting_threshold": self.voting_threshold
            }
        }


# Global multi-agent debate instance
_multi_agent_debate: Optional[MultiAgentDebate] = None


def get_agent_debate() -> MultiAgentDebate:
    global _multi_agent_debate
    if _multi_agent_debate is None:
        _multi_agent_debate = MultiAgentDebate()
    return _multi_agent_debate


async def close_agent_debate() -> None:
    global _multi_agent_debate
    if _multi_agent_debate:
        _multi_agent_debate = None