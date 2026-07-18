"""
Enhanced Memory System - Long-term, conversation, and user preference memory.

Extends the existing research memory with:
- Long-term memory with importance scoring
- Conversation memory with session context
- User preference learning
- Decision history tracking
- Tool usage analytics
- Memory ranking and pruning
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import logging

from memory.research_memory import get_memory_store, ResearchMemory, MemoryType
from config.settings import get_settings

logger = logging.getLogger(__name__)


class MemoryScope(str, Enum):
    """Scope of memory."""
    GLOBAL = "global"           # System-wide knowledge
    USER = "user"              # Per-user preferences/history
    SESSION = "session"        # Per-session context
    COMPANY = "company"        # Per-company knowledge
    AGENT = "agent"            # Per-agent learnings


class MemoryImportance(str, Enum):
    """Importance levels for memory ranking."""
    CRITICAL = "critical"       # Never prune
    HIGH = "high"               # Prune last
    MEDIUM = "medium"           # Normal pruning
    LOW = "low"                 # Prune first
    EPHEMERAL = "ephemeral"     # Auto-expire quickly


@dataclass
class LongTermMemory:
    """Long-term memory entry with importance and access tracking."""
    memory_id: str
    scope: MemoryScope
    scope_key: str             # e.g., user_id, company, session_id
    content: Dict[str, Any]
    memory_type: str           # preference, fact, pattern, insight, decision, tool_usage
    importance: MemoryImportance = MemoryImportance.MEDIUM
    confidence: float = 1.0
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    source: str = "system"     # user, agent, system, inferred
    supersedes: Optional[str] = None  # Memory ID this replaces
    linked_memories: List[str] = field(default_factory=list)


@dataclass
class ConversationMemory:
    """Memory of a conversation session."""
    conversation_id: str
    user_id: str
    session_id: Optional[str]
    messages: List[Dict[str, Any]] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    entities_mentioned: List[str] = field(default_factory=list)
    decisions_made: List[str] = field(default_factory=list)  # Decision IDs
    tools_used: List[str] = field(default_factory=list)
    agents_consulted: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    sentiment: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    message_count: int = 0


@dataclass
class UserPreferences:
    """Learned user preferences."""
    user_id: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    interaction_patterns: Dict[str, Any] = field(default_factory=dict)
    preferred_companies: List[str] = field(default_factory=list)
    preferred_report_types: List[str] = field(default_factory=list)
    preferred_agents: List[str] = field(default_factory=list)
    notification_preferences: Dict[str, Any] = field(default_factory=dict)
    ui_preferences: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    last_updated: datetime = field(default_factory=datetime.now)
    interaction_count: int = 0


@dataclass
class DecisionHistoryEntry:
    """Entry in decision history."""
    history_id: str
    user_id: str
    session_id: Optional[str]
    decision_id: str
    question: str
    decision_type: str
    conclusion: str
    confidence: float
    outcome: Optional[str] = None  # actual outcome if known
    outcome_accuracy: Optional[float] = None
    feedback: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ToolUsageRecord:
    """Record of tool usage for analytics."""
    record_id: str
    user_id: str
    session_id: Optional[str]
    tool_name: str
    category: str
    parameters: Dict[str, Any]
    result_summary: Dict[str, Any]
    success: bool
    duration_ms: float
    tokens_used: int
    cost_usd: float
    timestamp: datetime = field(default_factory=datetime.now)


class EnhancedMemoryStore:
    """
    Enhanced memory store with multiple memory types,
    importance-based ranking, and automatic pruning.
    """

    def __init__(self):
        self.settings = get_settings()
        self.base_memory = get_memory_store()

        # In-memory stores (in production would be database)
        self.long_term: Dict[str, LongTermMemory] = {}
        self.conversations: Dict[str, ConversationMemory] = {}
        self.user_preferences: Dict[str, UserPreferences] = {}
        self.decision_history: List[DecisionHistoryEntry] = []
        self.tool_usage: List[ToolUsageRecord] = []

        # Indexes for fast lookup
        self._scope_index: Dict[str, Set[str]] = {}  # scope_key -> memory_ids
        self._user_conversations: Dict[str, Set[str]] = {}  # user_id -> conversation_ids
        self._company_memories: Dict[str, Set[str]] = {}  # company -> memory_ids

    # ==================== Long-Term Memory ====================

    async def store_long_term(
        self,
        scope: MemoryScope,
        scope_key: str,
        content: Dict[str, Any],
        memory_type: str,
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        confidence: float = 1.0,
        tags: Optional[List[str]] = None,
        source: str = "system",
        ttl_days: Optional[int] = None,
        supersedes: Optional[str] = None
    ) -> str:
        """Store long-term memory entry."""
        memory = LongTermMemory(
            memory_id=str(uuid.uuid4())[:8],
            scope=scope,
            scope_key=scope_key,
            content=content,
            memory_type=memory_type,
            importance=importance,
            confidence=confidence,
            tags=tags or [],
            source=source,
            expires_at=datetime.now() + timedelta(days=ttl_days) if ttl_days else None,
            supersedes=supersedes
        )

        # Handle supersession
        if supersedes and supersedes in self.long_term:
            old = self.long_term[supersedes]
            old.content = content
            old.updated_at = datetime.now()
            old.importance = importance
            old.confidence = confidence
            logger.info(f"Superseded memory {supersedes} with new version")
            return supersedes

        self.long_term[memory.memory_id] = memory
        self._index_memory(memory)
        return memory.memory_id

    def _index_memory(self, memory: LongTermMemory):
        """Add memory to indexes."""
        key = f"{memory.scope.value}:{memory.scope_key}"
        if key not in self._scope_index:
            self._scope_index[key] = set()
        self._scope_index[key].add(memory.memory_id)

        if memory.scope == MemoryScope.COMPANY:
            if memory.scope_key not in self._company_memories:
                self._company_memories[memory.scope_key] = set()
            self._company_memories[memory.scope_key].add(memory.memory_id)

    async def retrieve_long_term(
        self,
        scope: MemoryScope,
        scope_key: str,
        memory_type: Optional[str] = None,
        min_importance: MemoryImportance = MemoryImportance.LOW,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[LongTermMemory]:
        """Retrieve long-term memories."""
        key = f"{scope.value}:{scope_key}"
        memory_ids = self._scope_index.get(key, set())

        memories = []
        for mid in memory_ids:
            memory = self.long_term.get(mid)
            if not memory:
                continue
            if memory.expires_at and memory.expires_at < datetime.now():
                continue
            if memory_type and memory.memory_type != memory_type:
                continue
            if importance_order(memory.importance) < importance_order(min_importance):
                continue
            if tags and not all(t in memory.tags for t in tags):
                continue

            # Update access stats
            memory.access_count += 1
            memory.last_accessed = datetime.now()

            memories.append(memory)

        # Sort by importance, confidence, recency
        memories.sort(key=lambda m: (
            importance_order(m.importance),
            m.confidence,
            m.last_accessed or m.created_at
        ), reverse=True)

        return memories[:limit]

    async def search_long_term(
        self,
        query: str,
        scope: Optional[MemoryScope] = None,
        scope_key: Optional[str] = None,
        limit: int = 10
    ) -> List[LongTermMemory]:
        """Search long-term memories by content (simple keyword matching)."""
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        candidates = []
        if scope and scope_key:
            key = f"{scope.value}:{scope_key}"
            memory_ids = self._scope_index.get(key, set())
            candidates = [self.long_term[mid] for mid in memory_ids if mid in self.long_term]
        elif scope:
            # Search all memories of this scope
            candidates = [m for m in self.long_term.values() if m.scope == scope]
        else:
            candidates = list(self.long_term.values())

        results = []
        for memory in candidates:
            if memory.expires_at and memory.expires_at < datetime.now():
                continue

            # Simple keyword matching
            content_str = json.dumps(memory.content).lower()
            overlap = len(query_terms & set(content_str.split()))
            if overlap > 0:
                memory.access_count += 1
                memory.last_accessed = datetime.now()
                results.append((memory, overlap))

        # Sort by relevance
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:limit]]

    # ==================== Conversation Memory ====================

    async def create_conversation(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> ConversationMemory:
        """Create new conversation memory."""
        conv = ConversationMemory(
            conversation_id=str(uuid.uuid4())[:8],
            user_id=user_id,
            session_id=session_id
        )
        self.conversations[conv.conversation_id] = conv

        if user_id not in self._user_conversations:
            self._user_conversations[user_id] = set()
        self._user_conversations[user_id].add(conv.conversation_id)

        return conv

    async def add_conversation_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add message to conversation."""
        conv = self.conversations.get(conversation_id)
        if not conv:
            return False

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        conv.messages.append(message)
        conv.message_count += 1
        conv.updated_at = datetime.now()

        # Extract entities/topics
        # In production, would use NLP
        if conv.session_id and "company" in str(metadata).lower():
            pass  # Extract company mentions

        return True

    async def get_conversation(self, conversation_id: str) -> Optional[ConversationMemory]:
        """Get conversation by ID."""
        return self.conversations.get(conversation_id)

    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[ConversationMemory]:
        """Get user's recent conversations."""
        conv_ids = self._user_conversations.get(user_id, set())
        conversations = [self.conversations[cid] for cid in conv_ids if cid in self.conversations]
        conversations.sort(key=lambda c: c.updated_at, reverse=True)
        return conversations[:limit]

    async def summarize_conversation(self, conversation_id: str) -> Optional[str]:
        """Generate conversation summary using LLM."""
        # In production, would use LLM to summarize
        conv = self.conversations.get(conversation_id)
        if not conv or not conv.messages:
            return None

        # Simple summary
        user_msgs = [m for m in conv.messages if m["role"] == "user"]
        topics = [m["content"][:50] for m in user_msgs[:5]]

        summary = f"Conversation with {len(conv.messages)} messages. Topics: {', '.join(topics)}"
        conv.summary = summary
        return summary

    # ==================== User Preferences ====================

    async def get_user_preferences(self, user_id: str) -> UserPreferences:
        """Get or create user preferences."""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = UserPreferences(user_id=user_id)
        return self.user_preferences[user_id]

    async def update_preference(
        self,
        user_id: str,
        key: str,
        value: Any,
        confidence: float = 0.8
    ) -> UserPreferences:
        """Update a user preference."""
        prefs = await self.get_user_preferences(user_id)
        prefs.preferences[key] = {
            "value": value,
            "confidence": confidence,
            "updated_at": datetime.now().isoformat()
        }
        prefs.last_updated = datetime.now()
        prefs.interaction_count += 1
        return prefs

    async def learn_from_interaction(
        self,
        user_id: str,
        interaction: Dict[str, Any]
    ) -> UserPreferences:
        """Learn preferences from user interaction."""
        prefs = await self.get_user_preferences(user_id)
        prefs.interaction_count += 1

        # Track preferred companies
        if "company" in interaction:
            company = interaction["company"]
            if company not in prefs.preferred_companies:
                prefs.preferred_companies.append(company)
                if len(prefs.preferred_companies) > 20:
                    prefs.preferred_companies = prefs.preferred_companies[-20:]

        # Track preferred report types
        if "report_type" in interaction:
            rt = interaction["report_type"]
            if rt not in prefs.preferred_report_types:
                prefs.preferred_report_types.append(rt)

        # Track preferred agents
        if "agent" in interaction:
            agent = interaction["agent"]
            if agent not in prefs.preferred_agents:
                prefs.preferred_agents.append(agent)

        # Track UI preferences
        if "ui" in interaction:
            prefs.ui_preferences.update(interaction["ui"])

        # Track notification preferences
        if "notifications" in interaction:
            prefs.notification_preferences.update(interaction["notifications"])

        prefs.last_updated = datetime.now()
        return prefs

    # ==================== Decision History ====================

    async def record_decision(
        self,
        user_id: str,
        decision_id: str,
        question: str,
        decision_type: str,
        conclusion: str,
        confidence: float,
        session_id: Optional[str] = None
    ) -> DecisionHistoryEntry:
        """Record a decision in history."""
        entry = DecisionHistoryEntry(
            history_id=str(uuid.uuid4())[:8],
            user_id=user_id,
            session_id=session_id,
            decision_id=decision_id,
            question=question,
            decision_type=decision_type,
            conclusion=conclusion,
            confidence=confidence
        )
        self.decision_history.append(entry)
        return entry

    async def update_decision_outcome(
        self,
        decision_id: str,
        outcome: str,
        accuracy: float
    ) -> bool:
        """Update decision with actual outcome."""
        for entry in self.decision_history:
            if entry.decision_id == decision_id:
                entry.outcome = outcome
                entry.outcome_accuracy = accuracy
                return True
        return False

    async def get_decision_history(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[DecisionHistoryEntry]:
        """Get user's decision history."""
        user_decisions = [d for d in self.decision_history if d.user_id == user_id]
        user_decisions.sort(key=lambda d: d.created_at, reverse=True)
        return user_decisions[:limit]

    # ==================== Tool Usage Analytics ====================

    async def record_tool_usage(
        self,
        user_id: str,
        tool_name: str,
        category: str,
        parameters: Dict[str, Any],
        result: Dict[str, Any],
        success: bool,
        duration_ms: float,
        tokens_used: int,
        cost_usd: float,
        session_id: Optional[str] = None
    ) -> ToolUsageRecord:
        """Record tool usage for analytics."""
        record = ToolUsageRecord(
            record_id=str(uuid.uuid4())[:8],
            user_id=user_id,
            session_id=session_id,
            tool_name=tool_name,
            category=category,
            parameters=parameters,
            result_summary={"keys": list(result.keys())} if result else {},
            success=success,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
            cost_usd=cost_usd
        )
        self.tool_usage.append(record)

        # Store in long-term memory for cross-session learning
        await self.store_long_term(
            scope=MemoryScope.USER,
            scope_key=user_id,
            content={
                "tool": tool_name,
                "category": category,
                "success": success,
                "avg_duration_ms": duration_ms
            },
            memory_type="tool_usage",
            importance=MemoryImportance.LOW,
            tags=["tool_usage", tool_name, category]
        )

        return record

    async def get_tool_analytics(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get tool usage analytics for user."""
        cutoff = datetime.now() - timedelta(days=days)
        user_records = [
            r for r in self.tool_usage
            if r.user_id == user_id and r.timestamp >= cutoff
        ]

        if not user_records:
            return {"message": "No tool usage data"}

        # By tool
        by_tool = {}
        for r in user_records:
            if r.tool_name not in by_tool:
                by_tool[r.tool_name] = {"count": 0, "success_rate": 0, "avg_duration": 0, "total_cost": 0}
            by_tool[r.tool_name]["count"] += 1
            by_tool[r.tool_name]["total_cost"] += r.cost_usd
            by_tool[r.tool_name]["avg_duration"] += r.duration_ms
            if r.success:
                by_tool[r.tool_name]["success_rate"] += 1

        for tool in by_tool:
            t = by_tool[tool]
            t["success_rate"] = t["success_rate"] / t["count"]
            t["avg_duration"] = t["avg_duration"] / t["count"]

        # By category
        by_category = {}
        for r in user_records:
            if r.category not in by_category:
                by_category[r.category] = 0
            by_category[r.category] += 1

        return {
            "total_calls": len(user_records),
            "success_rate": sum(1 for r in user_records if r.success) / len(user_records),
            "total_cost": sum(r.cost_usd for r in user_records),
            "total_tokens": sum(r.tokens_used for r in user_records),
            "by_tool": by_tool,
            "by_category": by_category,
            "period_days": days
        }

    # ==================== Memory Pruning ====================

    async def prune_memories(
        self,
        max_memories_per_scope: int = 1000,
        min_importance: MemoryImportance = MemoryImportance.LOW,
        max_age_days: int = 365
    ) -> Dict[str, int]:
        """Prune old/low-importance memories."""
        pruned = 0
        expired = 0
        cutoff = datetime.now() - timedelta(days=max_age_days)

        to_remove = []
        for mid, memory in self.long_term.items():
            # Remove expired
            if memory.expires_at and memory.expires_at < datetime.now():
                to_remove.append(mid)
                expired += 1
                continue

            # Remove low importance old memories
            if (importance_order(memory.importance) <= importance_order(min_importance) and
                memory.created_at < cutoff and
                memory.access_count < 2):
                to_remove.append(mid)
                pruned += 1
                continue

        for mid in to_remove:
            memory = self.long_term.pop(mid, None)
            if memory:
                # Remove from indexes
                key = f"{memory.scope.value}:{memory.scope_key}"
                if key in self._scope_index:
                    self._scope_index[key].discard(mid)
                if memory.scope == MemoryScope.COMPANY:
                    self._company_memories[memory.scope_key].discard(mid)

        # Also prune old conversations
        conv_pruned = 0
        old_convs = [
            cid for cid, conv in self.conversations.items()
            if conv.updated_at < cutoff and conv.message_count < 3
        ]
        for cid in old_convs[:100]:  # Limit per run
            self.conversations.pop(cid, None)
            conv_pruned += 1

        return {
            "pruned_low_importance": pruned,
            "expired_removed": expired,
            "conversations_pruned": conv_pruned,
            "remaining_memories": len(self.long_term)
        }


def importance_order(importance: MemoryImportance) -> int:
    """Convert importance to numeric order."""
    order = {
        MemoryImportance.CRITICAL: 5,
        MemoryImportance.HIGH: 4,
        MemoryImportance.MEDIUM: 3,
        MemoryImportance.LOW: 2,
        MemoryImportance.EPHEMERAL: 1
    }
    return order.get(importance, 3)


# Global instance
_enhanced_memory: Optional[EnhancedMemoryStore] = None


def get_enhanced_memory() -> EnhancedMemoryStore:
    """Get global enhanced memory store."""
    global _enhanced_memory
    if _enhanced_memory is None:
        _enhanced_memory = EnhancedMemoryStore()
    return _enhanced_memory