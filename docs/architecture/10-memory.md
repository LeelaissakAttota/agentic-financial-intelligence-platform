# Memory Architecture
## Agentic Financial Intelligence Platform

---

## Overview

The platform implements a **three-generation memory system** that has evolved across phases:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MEMORY SYSTEM EVOLUTION                                │
├─────────────────────┬─────────────────────┬─────────────────────────────────┤
│      PHASE 5        │      PHASE 7        │           PHASE 8               │
│ Cross-Agent Memory  │ Research Memory     │ Enhanced Memory                 │
├─────────────────────┼─────────────────────┼─────────────────────────────────┤
│ 9 Memory Types      │ 7 Memory Types      │ 5 Scopes                        │
│ 5 Scopes            │ Session-scoped      │ 5 Importance Levels             │
│ Supersession        │ pgvector-ready      │ Auto-pruning                    │
│ Bidirectional Link  │ Company-scoped      │ Preference Learning             │
│ TTL/Expiration      │ Cross-session       │ Decision History                │
│ Confidence Score    │ Access Tracking     │ Tool Analytics                  │
│                     │                     │ Conversation Memory             │
└─────────────────────┴─────────────────────┴─────────────────────────────────┘
```

**All layers share PostgreSQL backend with pgvector extension for semantic search.**

---

## Phase 5: Cross-Agent Memory

### Location
- Module: `data/memory/cross_agent_memory.py`
- Table: `agent_memory` (PostgreSQL)

### Memory Types (9)
```python
class MemoryType(str, Enum):
    FACT = "fact"                    # Verifiable facts
    INSIGHT = "insight"              # Analytical insights
    RISK = "risk"                    # Risk factors
    OPPORTUNITY = "opportunity"      # Opportunities
    PATTERN = "pattern"              # Detected patterns
    ALERT = "alert"                  # Triggered alerts
    PORTFOLIO = "portfolio"          # Portfolio-related
    ENTITY = "entity"                # Entity information
    RELATIONSHIP = "relationship"    # Entity relationships
```

### Scopes (5)
```python
class MemoryScope(str, Enum):
    GLOBAL = "global"                # System-wide knowledge
    COMPANY = "company"              # Company-specific
    SECTOR = "sector"                # Sector/industry
    PORTFOLIO = "portfolio"          # Portfolio-specific
    USER = "user"                    # User-specific
```

### Data Model
```python
@dataclass
class MemoryEntry:
    memory_id: str
    memory_type: MemoryType
    scope: MemoryScope
    scope_key: str                    # e.g., "NVDA", "technology", "portfolio_123"
    content: Dict[str, Any]           # Structured content
    confidence: float = 1.0           # 0.0 - 1.0
    source_agent: str                 # Originating agent
    supersedes_id: Optional[str]      # Replaces another memory
    linked_memories: List[str]        # Bidirectional links
    tags: List[str]                   # For categorization
    access_count: int = 0
    last_accessed: Optional[datetime]
    expires_at: Optional[datetime]    # TTL expiration
    created_at: datetime
    updated_at: datetime
```

### Key Features

#### Supersession (Memory Updates)
```python
# When new information contradicts/updates old
new_memory = MemoryEntry(
    memory_type=MemoryType.FACT,
    scope=MemoryScope.COMPANY,
    scope_key="NVDA",
    content={"revenue_fy2024": 60_900_000_000},
    supersedes_id="old_memory_id"  # Marks old as superseded
)
```

#### Bidirectional Linking
```python
# Link related memories
memory1.linked_memories.append(memory2.memory_id)
memory2.linked_memories.append(memory1.memory_id)
```

#### Access Tracking & TTL
```python
# Automatic expiration
expires_at = datetime.utcnow() + timedelta(days=30)

# Access count for importance ranking
memory.access_count += 1
memory.last_accessed = datetime.utcnow()
```

### Store Interface
```python
class CrossAgentMemoryStore:
    async def store_memory(self, entry: MemoryEntry) -> str
    async def retrieve_memories(
        self,
        scope: MemoryScope,
        scope_key: str,
        memory_types: List[MemoryType] = None,
        min_confidence: float = 0.0,
        limit: int = 10
    ) -> List[MemoryEntry]
    
    async def search_memories(
        self,
        query: str,
        scope: MemoryScope = None,
        limit: int = 10
    ) -> List[MemoryEntry]  # pgvector semantic search ready
    
    async def supersede_memory(self, old_id: str, new_entry: MemoryEntry) -> str
    async def link_memories(self, id1: str, id2: str)
    async def cleanup_expired() -> int
```

---

## Phase 7: Research Memory

### Location
- Module: `memory/research_memory.py`
- Table: `research_sessions` + session-scoped memory

### Memory Types (7)
```python
class ResearchMemoryType(str, Enum):
    SESSION = "session"           # Full research session context
    CONCLUSION = "conclusion"     # Final conclusions
    SOURCE = "source"             # Source documents/evidence
    AGENT_OUTPUT = "agent_output" # Individual agent results
    FOLLOW_UP = "follow_up"       # Follow-up questions
    REPORT = "report"             # Generated reports
    INSIGHT = "insight"           # Key insights
```

### Session-Scoped Design
```python
@dataclass
class ResearchMemoryEntry:
    memory_id: str
    session_id: str
    memory_type: ResearchMemoryType
    company: str
    content: Dict[str, Any]
    confidence: float
    source_agent: Optional[str]
    tags: List[str]
    access_count: int = 0
    last_accessed: Optional[datetime]
    expires_at: Optional[datetime]  # Default 24h TTL
    created_at: datetime
```

### Cross-Session Retrieval
```python
async def retrieve_memories(
    self,
    company: str,
    memory_types: List[ResearchMemoryType] = None,
    min_confidence: float = 0.0,
    limit: int = 20
) -> List[ResearchMemoryEntry]:
    """
    Retrieve memories across ALL sessions for a company.
    Ordered by confidence (desc) then recency.
    """
```

### pgvector Integration (Ready)
```sql
-- Schema includes vector column for semantic search
ALTER TABLE research_memory ADD COLUMN embedding vector(1024);
CREATE INDEX idx_research_memory_embedding ON research_memory 
USING ivfflat (embedding vector_cosine_ops);
```

---

## Phase 8: Enhanced Memory

### Location
- Module: `memory/enhanced.py`
- Tables: `long_term_memory`, `conversation_memory`, `user_preferences`, `decision_history`, `tool_usage_analytics`

### Scopes (5) with Importance Levels (5)

```python
class MemoryScope(str, Enum):
    GLOBAL = "global"          # System-wide facts
    USER = "user"              # User-specific
    SESSION = "session"        # Active conversation
    COMPANY = "company"        # Company knowledge
    AGENT = "agent"            # Agent learnings

class ImportanceLevel(str, Enum):
    CRITICAL = "critical"      # Never prune
    HIGH = "high"              # Prune last
    MEDIUM = "medium"          # Normal pruning
    LOW = "low"                # Prune early
    EPHEMERAL = "ephemeral"    # Auto-expire quickly
```

### Memory Modules

#### 1. Long-Term Memory (`long_term_memory`)
```python
@dataclass
class LongTermMemoryEntry:
    memory_id: str
    scope: MemoryScope
    scope_key: str
    content: Dict[str, Any]
    memory_type: str            # fact, insight, pattern, risk, etc.
    importance: ImportanceLevel
    confidence: float = 1.0
    access_count: int = 0
    last_accessed: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    tags: List[str] = field(default_factory=list)
    source: str = "system"      # system, user, agent, copilot
    supersedes_id: Optional[str]
    linked_memories: List[str] = field(default_factory=list)
```

#### 2. Conversation Memory (`conversation_memory`)
```python
@dataclass
class ConversationMemoryEntry:
    conversation_id: str
    user_id: str
    session_id: Optional[str]
    messages: List[Dict]        # Full message history
    topics: List[str]           # Extracted topics
    entities_mentioned: List[str]  # Companies, people, concepts
    decisions_made: List[str]   # Decision IDs
    tools_used: List[str]
    agents_consulted: List[str]
    summary: Optional[str]      # Auto-generated summary
    sentiment: Optional[float]  # Overall sentiment
    message_count: int = 0
    created_at: datetime
    updated_at: datetime
```

#### 3. User Preferences (`user_preferences`)
```python
@dataclass
class UserPreferences:
    user_id: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    # Structure:
    # {
    #   "companies": ["NVDA", "TSLA"],  # Preferred companies
    #   "reports": ["analyst_report", "executive_summary"],
    #   "agents": ["risk", "competitive"],
    #   "ui": {"theme": "dark", "compact": true},
    #   "notifications": {"email": true, "slack": false}
    # }
    interaction_patterns: Dict[str, Any] = field(default_factory=dict)
    # {
    #   "avg_session_length_min": 15,
    #   "preferred_time": "morning",
    #   "query_complexity": "moderate"
    # }
    preferred_companies: List[str] = field(default_factory=list)
    preferred_report_types: List[str] = field(default_factory=list)
    preferred_agents: List[str] = field(default_factory=list)
    notification_preferences: Dict[str, bool] = field(default_factory=dict)
    ui_preferences: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5       # Learning confidence
    last_updated: datetime
    interaction_count: int = 0
```

#### 4. Decision History (`decision_history`)
```python
@dataclass
class DecisionHistoryEntry:
    decision_id: str
    user_id: str
    session_id: Optional[str]
    question: str
    decision_type: str
    conclusion: str
    confidence: float
    outcome: Optional[str] = None      # Actual outcome
    outcome_accuracy: Optional[float]  # 0.0 - 1.0
    feedback: Optional[str] = None
    created_at: datetime
```

#### 5. Tool Usage Analytics (`tool_usage_analytics`)
```python
@dataclass
class ToolUsageEntry:
    tool_name: str
    category: str
    parameters: Dict[str, Any]
    result_summary: Dict[str, Any]
    success: bool
    duration_ms: float
    tokens_used: int
    cost_usd: float
    timestamp: datetime
```

### Auto-Pruning System

```python
class MemoryPruner:
    """Automatic memory pruning based on importance, TTL, and access frequency."""
    
    PRUNING_RULES = {
        ImportanceLevel.CRITICAL:   {"ttl_days": None,    "min_access": 0},
        ImportanceLevel.HIGH:       {"ttl_days": 365,     "min_access": 1},
        ImportanceLevel.MEDIUM:     {"ttl_days": 90,      "min_access": 2},
        ImportanceLevel.LOW:        {"ttl_days": 30,      "min_access": 1},
        ImportanceLevel.EPHEMERAL:  {"ttl_days": 7,       "min_access": 0},
    }
    
    async def prune(self, scope: MemoryScope = None) -> PruningResult:
        """
        Prune memories based on:
        1. TTL expiration
        2. Importance level thresholds
        3. Access frequency (low access = prune first)
        4. Storage quota (if exceeded)
        """
```

### Preference Learning

```python
class PreferenceLearner:
    """Automatically learn user preferences from interactions."""
    
    async def learn_from_interaction(
        self,
        user_id: str,
        interaction: InteractionEvent
    ):
        """
        Updates preferences based on:
        - Companies queried → preferred_companies
        - Report types generated → preferred_report_types
        - Agents used → preferred_agents
        - UI settings changed → ui_preferences
        - Notification actions → notification_preferences
        """
```

### Decision Outcome Tracking

```python
async def record_decision_outcome(
    self,
    decision_id: str,
    outcome: str,
    accuracy: float,        # 0.0 - 1.0
    feedback: str = ""
):
    """Track decision accuracy for continuous improvement."""
```

### Tool Analytics

```python
async def get_tool_analytics(
    self,
    user_id: str = None,
    session_id: str = None,
    timeframe_days: int = 30
) -> ToolAnalytics:
    """Returns usage, success rates, cost, duration by tool/category."""
```

---

## Cross-Layer Integration

### Memory Access Patterns

| Operation | Phase 5 | Phase 7 | Phase 8 |
|-----------|---------|---------|---------|
| Store agent output | ✅ | ✅ | ✅ |
| Retrieve by company | ✅ | ✅ | ✅ |
| Cross-session query | ❌ | ✅ | ✅ |
| Semantic search | Ready (pgvector) | Ready | ✅ |
| User preferences | ❌ | ❌ | ✅ |
| Decision tracking | ❌ | ❌ | ✅ |
| Tool analytics | ❌ | ❌ | ✅ |
| Preference learning | ❌ | ❌ | ✅ |
| Auto-pruning | TTL only | TTL only | Full |

### Unified Access (Future)
```python
class UnifiedMemoryFacade:
    """Single interface for all memory layers."""
    
    async def store(self, entry: UnifiedMemoryEntry) -> str
    async def retrieve(
        self,
        query: str = None,
        company: str = None,
        user_id: str = None,
        session_id: str = None,
        memory_types: List[str] = None,
        scopes: List[MemoryScope] = None,
        limit: int = 20
    ) -> List[UnifiedMemoryEntry]
```

---

## Database Schema Summary

| Table | Phase | Purpose |
|-------|-------|---------|
| `agent_memory` | 5 | Cross-agent shared memory |
| `research_sessions` | 7 | Session metadata |
| `research_memory` | 7 | Session-scoped research memory |
| `copilot_sessions` | 8 | Copilot session metadata |
| `conversations` | 8 | Chat conversations |
| `conversation_messages` | 8 | Message history |
| `decision_history` | 8 | Decision audit trail |
| `tool_executions` | 8 | Tool usage tracking |
| `workflow_executions` | 8 | Workflow tracking |
| `long_term_memory` | 8 | Enhanced long-term |
| `conversation_memory` | 8 | Conversation context |
| `user_preferences` | 8 | Learned preferences |
| `decision_history` | 8 | Outcome tracking |
| `tool_usage_analytics` | 8 | Tool analytics |

---

## Configuration

```python
# config/memory.py
class MemorySettings(BaseSettings):
    # Phase 5
    cross_agent_ttl_days: int = 30
    cross_agent_max_per_company: int = 1000
    
    # Phase 7
    research_session_ttl_hours: int = 24
    research_memory_max_per_session: int = 500
    
    # Phase 8
    ltm_global_ttl_days: int = 365
    ltm_user_ttl_days: int = 180
    ltm_session_ttl_hours: int = 24
    ltm_company_ttl_days: int = 90
    ltm_agent_ttl_days: int = 30
    
    conversation_memory_ttl_hours: int = 48
    conversation_max_messages: int = 100
    
    preference_learning_enabled: bool = True
    preference_min_interactions: int = 5
    
    decision_tracking_enabled: bool = True
    
    tool_analytics_retention_days: int = 90
    
    # Pruning
    auto_prune_enabled: bool = True
    prune_schedule_cron: str = "0 3 * * *"  # Daily 3 AM
    storage_quota_mb: int = 10000
    
    # pgvector
    pgvector_enabled: bool = False  # Enable when pgvector installed
    embedding_dimension: int = 1024
```

---

*Document Version: 1.0*  
*Last Updated: 2026-07-18*  
*Platform: Agentic Financial Intelligence Platform v1.7.0-phase8*