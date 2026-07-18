"""
Autonomous Research Engine Module
Provides AI thesis generation, evidence ranking, multi-agent debate,
confidence scoring, contradiction detection, and research synthesis.
"""

from .thesis_generator import ThesisGenerator, get_thesis_generator
from .evidence_ranker import EvidenceRanker, get_evidence_ranker
from .agent_debate import AgentDebate, get_agent_debate
from .confidence_scorer import ConfidenceScorer, get_confidence_scorer
from .contradiction_detector import ContradictionDetector, get_contradiction_detector
from .research_synthesizer import ResearchSynthesizer, get_research_synthesizer

__all__ = [
    "ThesisGenerator",
    "get_thesis_generator",
    "EvidenceRanker",
    "get_evidence_ranker",
    "AgentDebate",
    "get_agent_debate",
    "ConfidenceScorer",
    "get_confidence_scorer",
    "ContradictionDetector",
    "get_contradiction_detector",
    "ResearchSynthesizer",
    "get_research_synthesizer",
]

__version__ = "1.0.0-phase9"