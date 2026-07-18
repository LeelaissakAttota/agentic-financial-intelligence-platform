"""
Decision Engine - Core reasoning and decision-making system.

Implements multi-step reasoning, evidence aggregation, and
explainable decision making for financial analysis.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable
import logging

from config.settings import get_settings
from llm.openrouter_client import OpenRouterClient
from explainability.engine import get_explainability_engine, ExplanationType, Explanation
from collaboration.coordinator import get_collaboration_coordinator, SharedFinding, KnowledgeSource
from tools.registry import get_tool_executor, ToolCategory

logger = logging.getLogger(__name__)


class DecisionType(str, Enum):
    """Types of decisions the engine can make."""
    INVESTMENT_RECOMMENDATION = "investment_recommendation"
    RISK_ASSESSMENT = "risk_assessment"
    PORTFOLIO_ACTION = "portfolio_action"
    ALERT_TRIGGER = "alert_trigger"
    RESEARCH_PRIORITY = "research_priority"
    TOOL_SELECTION = "tool_selection"
    AGENT_DELEGATION = "agent_delegation"


class ReasoningStepType(str, Enum):
    """Types of reasoning steps."""
    EVIDENCE_GATHERING = "evidence_gathering"
    HYPOTHESIS_FORMATION = "hypothesis_formation"
    EVIDENCE_EVALUATION = "evidence_evaluation"
    ALTERNATIVE_CONSIDERATION = "alternative_consideration"
    RISK_ANALYSIS = "risk_analysis"
    SYNTHESIS = "synthesis"
    CONCLUSION = "conclusion"


@dataclass
class ReasoningStep:
    """Single step in reasoning chain."""
    step_id: str
    step_type: ReasoningStepType
    description: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    confidence: float
    evidence_ids: List[str] = field(default_factory=list)
    tool_calls: List[str] = field(default_factory=list)
    agent_interactions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0


@dataclass
class DecisionContext:
    """Context for a decision."""
    decision_id: str
    decision_type: DecisionType
    question: str
    company: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    available_tools: List[str] = field(default_factory=list)
    available_agents: List[str] = field(default_factory=list)
    deadline: Optional[datetime] = None
    max_cost_usd: Optional[float] = None


@dataclass
class DecisionResult:
    """Result of a decision process."""
    decision_id: str
    decision_type: DecisionType
    question: str
    conclusion: str
    confidence: float
    reasoning_chain: List[ReasoningStep]
    evidence_ids: List[str]
    alternatives_considered: List[Dict[str, Any]]
    risk_factors: List[Dict[str, Any]]
    assumptions: List[Dict[str, Any]]
    explanation: Optional[Explanation] = None
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


class ReasoningEngine:
    """
    Implements multi-step reasoning for financial decisions.

    Uses chain-of-thought style internal planning with:
    - Evidence gathering from multiple sources
    - Hypothesis formation and testing
    - Alternative scenario consideration
    - Risk factor analysis
    - Synthesis into final conclusion
    """

    def __init__(self):
        self.settings = get_settings()
        self.llm = OpenRouterClient()
        self.tool_executor = get_tool_executor()
        self.explainability = get_explainability_engine()
        self.collaboration = get_collaboration_coordinator()

        # Reasoning templates
        self.reasoning_templates = {
            DecisionType.INVESTMENT_RECOMMENDATION: self._investment_reasoning_template,
            DecisionType.RISK_ASSESSMENT: self._risk_assessment_template,
            DecisionType.PORTFOLIO_ACTION: self._portfolio_action_template,
        }

    async def reason(
        self,
        context: DecisionContext,
        max_steps: int = 10,
        max_duration_seconds: float = 60.0
    ) -> DecisionResult:
        """
        Execute multi-step reasoning process.

        Args:
            context: Decision context with question and constraints
            max_steps: Maximum reasoning steps
            max_duration_seconds: Timeout for reasoning

        Returns:
            DecisionResult with conclusion and full reasoning chain
        """
        start_time = datetime.now()
        reasoning_chain = []
        all_evidence_ids = []
        step_count = 0

        # Initialize state
        state = {
            "question": context.question,
            "company": context.company,
            "evidence": [],
            "hypotheses": [],
            "evaluated_hypotheses": [],
            "alternatives": [],
            "risks": [],
            "assumptions": [],
            "current_step": 0
        }

        # Execute reasoning steps
        while step_count < max_steps:
            step_start = datetime.now()

            # Check timeout
            if (datetime.now() - start_time).total_seconds() > max_duration_seconds:
                logger.warning(f"Reasoning timeout for {context.decision_id}")
                break

            # Determine next reasoning step
            next_step = await self._determine_next_step(state, context, step_count)

            if next_step is None:
                # Reasoning complete
                break

            # Execute step
            step_result = await self._execute_reasoning_step(next_step, state, context)

            # Update state
            state.update(step_result.get("state_updates", {}))
            all_evidence_ids.extend(step_result.get("evidence_ids", []))

            # Record step
            reasoning_chain.append(ReasoningStep(
                step_id=str(uuid.uuid4())[:8],
                step_type=next_step,
                description=step_result.get("description", ""),
                input_data=step_result.get("input_data", {}),
                output_data=step_result.get("output_data", {}),
                confidence=step_result.get("confidence", 0.5),
                evidence_ids=step_result.get("evidence_ids", []),
                tool_calls=step_result.get("tool_calls", []),
                agent_interactions=step_result.get("agent_interactions", []),
                duration_ms=(datetime.now() - step_start).total_seconds() * 1000
            ))

            step_count += 1

        # Synthesize final conclusion
        conclusion = await self._synthesize_conclusion(state, context)

        # Build alternatives
        alternatives = self._build_alternatives(state, conclusion)

        # Identify risks and assumptions
        risks = self._extract_risks(state)
        assumptions = self._extract_assumptions(state)

        # Generate explanation
        explanation = await self.explainability.explain_recommendation(
            question=context.question,
            recommendation=conclusion["conclusion"],
            confidence=conclusion["confidence"],
            evidence_ids=all_evidence_ids,
            company=context.company,
            session_id=context.session_id
        )

        # Prepare execution metadata
        execution_metadata = {
            "total_steps": len(reasoning_chain),
            "total_duration_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "tools_used": list(set(
                t for step in reasoning_chain for t in step.tool_calls
            )),
            "agents_consulted": list(set(
                a for step in reasoning_chain for a in step.agent_interactions
            )),
            "evidence_collected": len(all_evidence_ids)
        }

        return DecisionResult(
            decision_id=context.decision_id,
            decision_type=context.decision_type,
            question=context.question,
            conclusion=conclusion["conclusion"],
            confidence=conclusion["confidence"],
            reasoning_chain=reasoning_chain,
            evidence_ids=all_evidence_ids,
            alternatives_considered=alternatives,
            risk_factors=risks,
            assumptions=assumptions,
            explanation=explanation,
            execution_metadata=execution_metadata
        )

    async def _determine_next_step(
        self,
        state: Dict[str, Any],
        context: DecisionContext,
        step_count: int
    ) -> Optional[ReasoningStepType]:
        """Determine next reasoning step based on current state."""

        # Step progression logic
        if step_count == 0:
            return ReasoningStepType.EVIDENCE_GATHERING
        elif step_count == 1 and state.get("evidence"):
            return ReasoningStepType.HYPOTHESIS_FORMATION
        elif step_count == 2 and state.get("hypotheses"):
            return ReasoningStepType.EVIDENCE_EVALUATION
        elif step_count == 3 and state.get("evaluated_hypotheses"):
            return ReasoningStepType.ALTERNATIVE_CONSIDERATION
        elif step_count == 4 and state.get("alternatives"):
            return ReasoningStepType.RISK_ANALYSIS
        elif step_count >= 5:
            return ReasoningStepType.SYNTHESIS

        return None

    async def _execute_reasoning_step(
        self,
        step_type: ReasoningStepType,
        state: Dict[str, Any],
        context: DecisionContext
    ) -> Dict[str, Any]:
        """Execute a single reasoning step."""

        if step_type == ReasoningStepType.EVIDENCE_GATHERING:
            return await self._gather_evidence(state, context)

        elif step_type == ReasoningStepType.HYPOTHESIS_FORMATION:
            return await self._form_hypotheses(state, context)

        elif step_type == ReasoningStepType.EVIDENCE_EVALUATION:
            return await self._evaluate_evidence(state, context)

        elif step_type == ReasoningStepType.ALTERNATIVE_CONSIDERATION:
            return await self._consider_alternatives(state, context)

        elif step_type == ReasoningStepType.RISK_ANALYSIS:
            return await self._analyze_risks(state, context)

        elif step_type == ReasoningStepType.SYNTHESIS:
            return await self._synthesize_findings(state, context)

        return {}

    async def _gather_evidence(self, state: Dict, context: DecisionContext) -> Dict:
        """Gather evidence from multiple sources."""
        evidence_ids = []
        tool_calls = []
        agent_interactions = []

        # Determine which tools to use based on question
        tool_plan = await self._plan_evidence_gathering(context)

        for tool_name in tool_plan:
            try:
                execution = await self.tool_executor.execute(
                    tool_name,
                    {"company": context.company} if context.company else {}
                )

                if execution.result:
                    # Store evidence
                    evidence = self.explainability.evidence_collector.extract_from_tool_result(
                        tool_name, execution.result, context.company or "unknown"
                    )
                    evidence_ids.extend([e.evidence_id for e in evidence])

                tool_calls.append(tool_name)
                agent_interactions.append(execution.category.value)

            except Exception as e:
                logger.warning(f"Tool {tool_name} failed: {e}")

        # Also query collaboration knowledge
        findings = self.collaboration.get_shared_knowledge(
            tags=[context.company] if context.company else None
        )
        for finding in findings[:5]:
            # Store as evidence
            pass  # Would extract evidence IDs

        return {
            "state_updates": {"evidence": evidence_ids},
            "evidence_ids": evidence_ids,
            "tool_calls": tool_calls,
            "agent_interactions": agent_interactions,
            "description": f"Gathered evidence from {len(tool_calls)} tools",
            "confidence": 0.8,
            "input_data": {"tool_plan": tool_plan},
            "output_data": {"evidence_collected": len(evidence_ids)}
        }

    async def _plan_evidence_gathering(self, context: DecisionContext) -> List[str]:
        """Plan which tools to use for evidence gathering."""
        # Use LLM to determine relevant tools
        tools = self.tool_executor.get_recent_executions()

        prompt = f"""
        Given this financial research question, select the most relevant tools from available categories:

        Question: {context.question}
        Company: {context.company or 'Not specified'}
        Available tools: Financial Documents, Sentiment, Risk, Competitive, News, Market Data, Investment Summary, Knowledge Graph, Portfolio, Patterns, Alerts, Analytics, Historical, Memory

        Return JSON array of tool names to use, in priority order.
        """

        try:
            response = await self.llm.agenerate_json(prompt)
            return response.get("tools", ["analyze_financial_documents", "get_market_data", "get_financial_news"])
        except Exception:
            return ["analyze_financial_documents", "get_market_data", "get_financial_news", "analyze_sentiment", "assess_risk"]

    async def _form_hypotheses(self, state: Dict, context: DecisionContext) -> Dict:
        """Form initial hypotheses based on evidence."""
        # Use LLM to generate hypotheses
        evidence_summary = f"Evidence collected: {len(state.get('evidence', []))} items"

        prompt = f"""
        Based on this evidence, form 3-5 testable hypotheses about: {context.question}

        Company: {context.company or 'Not specified'}
        Evidence: {evidence_summary}

        Return JSON array of hypotheses with:
        - hypothesis: statement
        - supporting_evidence: list of evidence types needed
        - confidence: initial confidence 0-1
        - test_method: how to test
        """

        try:
            response = await self.llm.agenerate_json(prompt)
            hypotheses = response.get("hypotheses", [])
            return {
                "state_updates": {"hypotheses": hypotheses},
                "description": f"Formed {len(hypotheses)} hypotheses",
                "confidence": 0.7,
                "input_data": {"evidence_count": len(state.get('evidence', []))},
                "output_data": {"hypotheses": hypotheses}
            }
        except Exception:
            return {"state_updates": {"hypotheses": []}}

    async def _evaluate_evidence(self, state: Dict, context: DecisionContext) -> Dict:
        """Evaluate evidence against hypotheses."""
        hypotheses = state.get("hypotheses", [])
        evaluated = []

        for hyp in hypotheses:
            # Use LLM to evaluate
            prompt = f"""
            Evaluate this hypothesis against available evidence:

            Hypothesis: {hyp.get('hypothesis', '')}
            Evidence available: {len(state.get('evidence', []))} items

            Return JSON with:
            - hypothesis: original hypothesis
            - support_score: 0-1 how well evidence supports
            - contradicting_evidence: any evidence that contradicts
            - confidence: updated confidence 0-1
            """

            try:
                response = await self.llm.agenerate_json(prompt)
                evaluated.append(response)
            except Exception:
                evaluated.append({"hypothesis": hyp, "support_score": 0.5, "confidence": 0.5})

        return {
            "state_updates": {"evaluated_hypotheses": evaluated},
            "description": f"Evaluated {len(hypotheses)} hypotheses",
            "confidence": 0.7,
            "input_data": {"hypotheses": len(hypotheses)},
            "output_data": {"evaluated": len(evaluated)}
        }

    async def _consider_alternatives(self, state: Dict, context: DecisionContext) -> Dict:
        """Consider alternative scenarios."""
        evaluated = state.get("evaluated_hypotheses", [])

        prompt = f"""
        Given these evaluated hypotheses, generate alternative scenarios:

        Hypotheses: {json.dumps(evaluated)}

        Generate 3 alternatives: bear case, base case, bull case
        For each: name, description, probability, key drivers, impact
        """

        try:
            response = await self.llm.agenerate_json(prompt)
            alternatives = response.get("alternatives", [])
            return {
                "state_updates": {"alternatives": alternatives},
                "description": f"Generated {len(alternatives)} alternative scenarios",
                "confidence": 0.7,
                "input_data": {"hypotheses_evaluated": len(evaluated)},
                "output_data": {"alternatives": alternatives}
            }
        except Exception:
            return {"state_updates": {"alternatives": []}}

    async def _analyze_risks(self, state: Dict, context: DecisionContext) -> Dict:
        """Analyze risk factors."""
        # Use risk assessment tool
        try:
            execution = await self.tool_executor.execute(
                "assess_risk",
                {"company": context.company} if context.company else {}
            )
            risk_result = execution.result or {}
        except Exception:
            risk_result = {}

        # Also extract from hypotheses
        risks = []
        for hyp in state.get("evaluated_hypotheses", []):
            if hyp.get("support_score", 0) < 0.4:
                risks.append({
                    "risk": f"Low support for hypothesis: {hyp.get('hypothesis', '')}",
                    "severity": "medium",
                    "likelihood": 1 - hyp.get("confidence", 0.5)
                })

        return {
            "state_updates": {"risks": risks},
            "description": f"Identified {len(risks)} risk factors",
            "confidence": 0.7,
            "input_data": {"hypotheses": len(state.get('evaluated_hypotheses', []))},
            "output_data": {"risks": risks}
        }

    async def _synthesize_findings(self, state: Dict, context: DecisionContext) -> Dict:
        """Synthesize all findings into coherent picture."""
        evaluated = state.get("evaluated_hypotheses", [])
        alternatives = state.get("alternatives", [])
        risks = state.get("risks", [])

        prompt = f"""
        Synthesize these findings into a coherent conclusion:

        Evaluated Hypotheses: {json.dumps(evaluated)}
        Alternatives: {json.dumps(alternatives)}
        Risks: {json.dumps(risks)}

        Return JSON with:
        - synthesis: integrated narrative
        - key_findings: list of most important findings
        - confidence: overall confidence 0-1
        - recommendation: if applicable
        """

        try:
            response = await self.llm.agenerate_json(prompt)
            return {
                "state_updates": {"synthesis": response},
                "description": "Synthesized findings into conclusion",
                "confidence": 0.8,
                "input_data": {"evaluated": len(evaluated), "alternatives": len(alternatives)},
                "output_data": response
            }
        except Exception:
            return {"state_updates": {"synthesis": {}}}

    async def _synthesize_conclusion(self, state: Dict, context: DecisionContext) -> Dict:
        """Generate final conclusion."""
        synthesis = state.get("synthesis", {})
        evaluated = state.get("evaluated_hypotheses", [])
        alternatives = state.get("alternatives", [])

        # Determine conclusion based on decision type
        if context.decision_type == DecisionType.INVESTMENT_RECOMMENDATION:
            conclusion_text = synthesis.get("recommendation", "Hold - insufficient evidence for strong conviction")
            confidence = synthesis.get("confidence", 0.6)
        elif context.decision_type == DecisionType.RISK_ASSESSMENT:
            conclusion_text = f"Risk Level: {synthesis.get('risk_level', 'Medium')} - {synthesis.get('narrative', 'Mixed risk factors')}"
            confidence = synthesis.get("confidence", 0.6)
        else:
            conclusion_text = synthesis.get("synthesis", "Analysis complete")
            confidence = synthesis.get("confidence", 0.6)

        return {
            "conclusion": conclusion_text,
            "confidence": confidence
        }

    def _build_alternatives(self, state: Dict, conclusion: Dict) -> List[Dict]:
        """Build alternative scenarios from reasoning."""
        return state.get("alternatives", [
            {"name": "Bear Case", "probability": 0.2, "description": "Negative outcome"},
            {"name": "Base Case", "probability": 0.6, "description": "Expected outcome"},
            {"name": "Bull Case", "probability": 0.2, "description": "Positive outcome"}
        ])

    def _extract_risks(self, state: Dict) -> List[Dict]:
        """Extract risk factors from reasoning state."""
        return state.get("risks", [])

    def _extract_assumptions(self, state: Dict) -> List[Dict]:
        """Extract key assumptions from reasoning state."""
        assumptions = []

        # From hypotheses
        for hyp in state.get("evaluated_hypotheses", []):
            assumptions.append({
                "assumption": hyp.get("hypothesis", ""),
                "confidence": hyp.get("confidence", 0.5),
                "if_wrong": "Recommendation would change significantly"
            })

        return assumptions


class DecisionEngine:
    """
    Main Decision Engine for financial decisions.

    Orchestrates reasoning, tool execution, and explanation generation.
    """

    def __init__(self):
        self.settings = get_settings()
        self.reasoning_engine = ReasoningEngine()
        self.active_decisions: Dict[str, DecisionResult] = {}

    async def make_decision(
        self,
        question: str,
        decision_type: DecisionType,
        company: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None,
        preferences: Optional[Dict[str, Any]] = None,
        max_steps: int = 10,
        timeout_seconds: float = 60.0
    ) -> DecisionResult:
        """
        Make a financial decision with full reasoning.

        Args:
            question: The decision question
            decision_type: Type of decision
            company: Company context
            user_id: User making request
            session_id: Session ID
            constraints: Decision constraints
            preferences: User preferences
            max_steps: Maximum reasoning steps
            timeout_seconds: Timeout

        Returns:
            DecisionResult with conclusion and full reasoning
        """
        context = DecisionContext(
            decision_id=str(uuid.uuid4())[:8],
            decision_type=decision_type,
            question=question,
            company=company,
            user_id=user_id,
            session_id=session_id,
            constraints=constraints or {},
            preferences=preferences or {}
        )

        result = await self.reasoning_engine.reason(
            context,
            max_steps=max_steps,
            max_duration_seconds=timeout_seconds
        )

        self.active_decisions[result.decision_id] = result
        return result

    async def get_decision(self, decision_id: str) -> Optional[DecisionResult]:
        """Get decision by ID."""
        return self.active_decisions.get(decision_id)

    async def explain_decision(self, decision_id: str) -> Optional[Explanation]:
        """Get explanation for a decision."""
        result = self.active_decisions.get(decision_id)
        if result and result.explanation:
            return result.explanation
        return None

    def list_decisions(self, session_id: Optional[str] = None) -> List[DecisionResult]:
        """List decisions, optionally filtered by session."""
        if session_id:
            return [d for d in self.active_decisions.values() if d.execution_metadata.get("session_id") == session_id]
        return list(self.active_decisions.values())


# Global instance
_decision_engine: Optional[DecisionEngine] = None


def get_decision_engine() -> DecisionEngine:
    """Get global decision engine."""
    global _decision_engine
    if _decision_engine is None:
        _decision_engine = DecisionEngine()
    return _decision_engine