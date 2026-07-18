"""
Copilot Conversation Management - Multi-turn conversation handling.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

from copilot.assistant import (
    ConversationManager, ConversationMessage, ConversationSession,
    MessageRole, ConversationStatus, get_conversation_manager
)
from config.settings import get_settings

logger = logging.getLogger(__name__)


class ConversationContext:
    """Enhanced conversation context with financial domain awareness."""

    def __init__(self):
        self.manager = get_conversation_manager()

    def start_financial_research(
        self,
        user_id: str,
        company: str,
        initial_question: str
    ) -> ConversationSession:
        """Start a financial research conversation."""
        session = self.manager.create_session(user_id, f"Research: {company}")

        # Add system message with financial context
        system_msg = ConversationMessage(
            message_id=str(uuid.uuid4())[:8],
            role=MessageRole.SYSTEM,
            content=f"""Financial Research Session for {company}

You are an AI Financial Research Copilot. This conversation is focused on financial research for {company}.

Guidelines:
1. All responses should be relevant to financial analysis
2. Cite sources when making claims
3. Use appropriate financial terminology
4. Provide confidence levels for recommendations
5. Consider risk factors in all analyses
6. Suggest follow-up research when appropriate

Initial Question: {initial_question}
""",
            metadata={"company": company, "research_type": "financial"}
        )
        self.manager.add_message(session.session_id, system_msg)

        # Add user's initial question
        user_msg = ConversationMessage(
            message_id=str(uuid.uuid4())[:8],
            role=MessageRole.USER,
            content=initial_question,
            metadata={"company": company}
        )
        self.manager.add_message(session.session_id, user_msg)

        return session

    def add_research_result(
        self,
        session_id: str,
        agent_type: str,
        result: Dict[str, Any],
        confidence: float
    ) -> bool:
        """Add research agent result to conversation."""
        msg = ConversationMessage(
            message_id=str(uuid.uuid4())[:8],
            role=MessageRole.TOOL,
            content=f"{agent_type} Analysis Complete:\n{json.dumps(result, indent=2)[:2000]}",
            metadata={
                "agent_type": agent_type,
                "confidence": confidence,
                "result_keys": list(result.keys())
            }
        )
        return self.manager.add_message(session_id, msg)

    def add_follow_up_question(
        self,
        session_id: str,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add user follow-up question."""
        msg = ConversationMessage(
            message_id=str(uuid.uuid4())[:8],
            role=MessageRole.USER,
            content=question,
            metadata=context or {}
        )
        return self.manager.add_message(session_id, msg)

    def get_research_context(
        self,
        session_id: str,
        max_messages: int = 20
    ) -> Dict[str, Any]:
        """Get relevant research context from conversation."""
        session = self.manager.get_session(session_id)
        if not session:
            return {}

        recent = self.manager.get_recent_messages(session_id, max_messages)

        # Extract financial context
        companies = set()
        agents_used = set()
        topics = set()
        findings = []

        for msg in recent:
            if msg.metadata:
                if "company" in msg.metadata:
                    companies.add(msg.metadata["company"])
                if "agent_type" in msg.metadata:
                    agents_used.add(msg.metadata["agent_type"])

        return {
            "session_id": session_id,
            "companies": list(companies),
            "agents_consulted": list(agents_used),
            "message_count": len(session.messages),
            "recent_messages": [
                {
                    "role": m.role.value,
                    "content": m.content[:500],
                    "metadata": m.metadata
                }
                for m in recent
            ]
        }

    def summarize_research_session(self, session_id: str) -> Optional[str]:
        """Generate summary of research session."""
        session = self.manager.get_session(session_id)
        if not session or len(session.messages) < 3:
            return None

        # Extract key findings
        findings = []
        companies = set()

        for msg in session.messages:
            if msg.metadata and msg.metadata.get("agent_type"):
                findings.append(f"{msg.metadata['agent_type']}: completed")
            if msg.metadata and msg.metadata.get("company"):
                companies.add(msg.metadata["company"])

        summary = f"""Research Session Summary:
- Companies analyzed: {', '.join(companies) or 'None'}
- Agents consulted: {len(findings)}
- Total messages: {len(session.messages)}
- Key findings: {'; '.join(findings[:5])}
- Status: {session.status.value}
"""

        session.summary = summary
        return summary


# Global instance
_conversation_context: Optional[ConversationContext] = None


def get_conversation_context() -> ConversationContext:
    """Get global conversation context."""
    global _conversation_context
    if _conversation_context is None:
        _conversation_context = ConversationContext()
    return _conversation_context