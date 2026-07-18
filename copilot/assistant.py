"""
AI Copilot - Natural Language Financial Assistant

Provides conversational interface for financial research with multi-turn
conversation support, session management, and streaming responses.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional
import logging

from config.settings import get_settings
from llm.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)


class MessageRole(str, Enum):
    """Message roles in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ConversationStatus(str, Enum):
    """Conversation status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    ERROR = "error"


@dataclass
class ConversationMessage:
    """Single message in conversation."""
    message_id: str
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


@dataclass
class ConversationSession:
    """Conversation session with context management."""
    session_id: str
    user_id: str
    title: str = ""
    status: ConversationStatus = ConversationStatus.ACTIVE
    messages: List[ConversationMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    summary: Optional[str] = None
    token_count: int = 0
    max_tokens: int = 8000


@dataclass
class CopilotResponse:
    """Response from copilot with metadata."""
    content: str
    session_id: str
    message_id: str
    tokens_used: int
    model: str
    latency_ms: float
    tool_calls: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConversationManager:
    """Manages conversation sessions and history."""

    def __init__(self):
        self.sessions: Dict[str, ConversationSession] = {}
        self.max_context_tokens = 8000
        self.max_history_messages = 50

    def create_session(self, user_id: str, title: str = "") -> ConversationSession:
        """Create new conversation session."""
        session = ConversationSession(
            session_id=str(uuid.uuid4())[:8],
            user_id=user_id,
            title=title or f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        self.sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get session by ID."""
        return self.sessions.get(session_id)

    def add_message(self, session_id: str, message: ConversationMessage) -> bool:
        """Add message to session."""
        session = self.get_session(session_id)
        if not session:
            return False

        session.messages.append(message)
        session.updated_at = datetime.now()
        session.token_count += self._estimate_tokens(message.content)

        # Trim if needed
        self._trim_context(session)

        return True

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation."""
        return len(text) // 4

    def _trim_context(self, session: ConversationSession):
        """Trim context to fit within limits."""
        if session.token_count <= session.max_tokens:
            return

        # Keep system message, remove oldest user/assistant pairs
        while session.token_count > session.max_tokens and len(session.messages) > 2:
            removed = session.messages.pop(1)  # Keep system message at index 0
            session.token_count -= self._estimate_tokens(removed.content)

    def get_recent_messages(self, session_id: str, limit: int = 20) -> List[ConversationMessage]:
        """Get recent messages for context."""
        session = self.get_session(session_id)
        if not session:
            return []
        return session.messages[-limit:]

    def archive_session(self, session_id: str) -> bool:
        """Archive a session."""
        session = self.get_session(session_id)
        if session:
            session.status = ConversationStatus.ARCHIVED
            return True
        return False

    def summarize_session(self, session_id: str) -> Optional[str]:
        """Generate conversation summary."""
        session = self.get_session(session_id)
        if not session or len(session.messages) < 3:
            return None

        # Extract key topics and decisions
        user_messages = [m.content for m in session.messages if m.role == MessageRole.USER]
        return f"Conversation with {len(user_messages)} user queries about financial research"


class CopilotAssistant:
    """Main AI Copilot for financial research conversations."""

    def __init__(self):
        self.settings = get_settings()
        self.llm = OpenRouterClient()
        self.conversation_manager = ConversationManager()

        # System prompt for financial research
        self.system_prompt = """You are an expert AI Financial Research Copilot. You help users with:

1. Financial analysis and research planning
2. Market data interpretation
3. Company analysis (SEC filings, earnings, news)
4. Risk assessment and portfolio insights
5. Investment thesis development
6. Competitive intelligence

You have access to specialized tools for:
- Real-time market data
- Financial document analysis (SEC filings, earnings)
- News aggregation and sentiment
- Knowledge graph queries
- Pattern detection
- Risk analytics
- Portfolio management

Always provide:
- Clear, actionable insights
- Source citations when using tools
- Confidence levels for recommendations
- Risk considerations
- Follow-up suggestions

Be concise but thorough. Use structured responses with sections when appropriate."""

    async def chat(
        self,
        user_id: str,
        message: str,
        session_id: Optional[str] = None,
        stream: bool = False
    ) -> CopilotResponse:
        """Process a chat message and return response."""
        # Get or create session
        if session_id:
            session = self.conversation_manager.get_session(session_id)
            if not session:
                session = self.conversation_manager.create_session(user_id)
        else:
            session = self.conversation_manager.create_session(user_id)

        # Add user message
        user_msg = ConversationMessage(
            message_id=str(uuid.uuid4())[:8],
            role=MessageRole.USER,
            content=message
        )
        self.conversation_manager.add_message(session.session_id, user_msg)

        # Build context
        context = self._build_context(session)

        # Generate response
        start_time = datetime.now()
        response_content = await self._generate_response(context, stream)

        # Add assistant message
        assistant_msg = ConversationMessage(
            message_id=str(uuid.uuid4())[:8],
            role=MessageRole.ASSISTANT,
            content=response_content
        )
        self.conversation_manager.add_message(session.session_id, assistant_msg)

        latency_ms = (datetime.now() - start_time).total_seconds() * 1000

        return CopilotResponse(
            content=response_content,
            session_id=session.session_id,
            message_id=assistant_msg.message_id,
            tokens_used=session.token_count,
            model=self.settings.openrouter_model,
            latency_ms=latency_ms
        )

    async def chat_stream(
        self,
        user_id: str,
        message: str,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream chat response."""
        # Get or create session
        if session_id:
            session = self.conversation_manager.get_session(session_id)
            if not session:
                session = self.conversation_manager.create_session(user_id)
        else:
            session = self.conversation_manager.create_session(user_id)

        # Add user message
        user_msg = ConversationMessage(
            message_id=str(uuid.uuid4())[:8],
            role=MessageRole.USER,
            content=message
        )
        self.conversation_manager.add_message(session.session_id, user_msg)

        # Build context and stream
        context = self._build_context(session)

        full_response = ""
        async for chunk in self._stream_response(context):
            full_response += chunk
            yield chunk

        # Add assistant message
        assistant_msg = ConversationMessage(
            message_id=str(uuid.uuid4())[:8],
            role=MessageRole.ASSISTANT,
            content=full_response
        )
        self.conversation_manager.add_message(session.session_id, assistant_msg)

    def _build_context(self, session: ConversationSession) -> List[Dict[str, str]]:
        """Build message context for LLM."""
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add conversation summary if available
        if session.summary:
            messages.append({
                "role": "system",
                "content": f"Conversation summary: {session.summary}"
            })

        # Add recent messages
        recent = self.conversation_manager.get_recent_messages(
            session.session_id, limit=20
        )
        for msg in recent:
            messages.append({
                "role": msg.role.value,
                "content": msg.content
            })

        return messages

    async def _generate_response(self, context: List[Dict[str, str]], stream: bool) -> str:
        """Generate response from LLM."""
        response = await self.llm.agenerate_json(
            prompt="\n".join([f"{m['role']}: {m['content']}" for m in context]),
            system_prompt="",
            temperature=0.3,
            max_tokens=2000
        )
        return response.get("response", "I apologize, but I couldn't generate a response.")

    async def _stream_response(self, context: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """Stream response from LLM."""
        # Simplified streaming - in production would use actual streaming
        response = await self._generate_response(context, True)
        # Yield in chunks
        for i in range(0, len(response), 50):
            yield response[i:i+50]
            await asyncio.sleep(0.01)

    async def generate_followup_questions(self, session_id: str) -> List[str]:
        """Generate follow-up questions based on conversation."""
        session = self.conversation_manager.get_session(session_id)
        if not session or len(session.messages) < 2:
            return []

        # Use LLM to generate follow-ups
        recent = self.conversation_manager.get_recent_messages(session_id, 10)
        context = "\n".join([f"{m.role.value}: {m.content}" for m in recent])

        prompt = f"""Based on this financial research conversation, suggest 3 relevant follow-up questions:

{context}

Return JSON array of questions."""
        response = await self.llm.agenerate_json(prompt)
        return response.get("questions", [])


# Global instances
_conversation_manager: Optional[ConversationManager] = None
_copilot_assistant: Optional[CopilotAssistant] = None


def get_conversation_manager() -> ConversationManager:
    """Get global conversation manager."""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager


def get_copilot_assistant() -> CopilotAssistant:
    """Get global copilot assistant."""
    global _copilot_assistant
    if _copilot_assistant is None:
        _copilot_assistant = CopilotAssistant()
    return _copilot_assistant