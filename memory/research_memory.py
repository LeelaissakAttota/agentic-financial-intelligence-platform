"""
Research Memory System

Persistent storage and retrieval of research sessions, conclusions,
agent outputs, and cross-session knowledge.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import logging

from database.connection import get_session
from database.models import ResearchSession, ResearchMemory, Company, Report
from config.settings import get_settings
from sqlalchemy import select, text, func


logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of research memory."""
    SESSION = "session"
    CONCLUSION = "conclusion"
    SOURCE = "source"
    AGENT_OUTPUT = "agent_output"
    FOLLOW_UP = "follow_up"
    REPORT = "report"
    INSIGHT = "insight"


@dataclass
class ResearchMemory:
    """A single memory entry."""
    memory_id: str
    memory_type: MemoryType
    company: str
    content: Dict[str, Any]
    source_agent: Optional[str] = None
    session_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchSession:
    """Complete research session with all outputs."""
    session_id: str
    company: str
    query: str
    plan_id: Optional[str] = None
    status: str = "pending"
    steps: List[Dict[str, Any]] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    conclusions: List[str] = field(default_factory=list)
    reports: List[str] = field(default_factory=list)  # Report IDs
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    error: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


class ResearchMemoryStore:
    """
    Persistent research memory with vector search capabilities.
    
    Stores:
    - Research sessions with full context
    - Agent outputs and conclusions
    - Sources and citations
    - Follow-up questions
    - Generated reports
    - Embeddings for semantic retrieval
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._memory_cache: Dict[str, ResearchMemory] = {}
        self._session_cache: Dict[str, ResearchSession] = {}
    
    async def store_session(self, session: ResearchSession) -> str:
        """Store a research session."""
        self._session_cache[session.session_id] = session
        
        # Also persist to database
        async with get_session() as db_session:
            db_session.add(ResearchSessionModel(
                session_id=session.session_id,
                company=session.company,
                query=session.query,
                plan_id=session.plan_id,
                status=session.status,
                steps=json.dumps(session.steps),
                results=json.dumps(session.results),
                conclusions=json.dumps(session.conclusions),
                reports=json.dumps(session.reports),
                started_at=session.started_at,
                completed_at=session.completed_at,
                duration_seconds=session.duration_seconds,
                error=session.error,
                metadata=json.dumps(session.metadata)
            ))
            await db_session.commit()
        
        logger.info(f"Stored research session: {session.session_id}")
        return session.session_id
    
    async def get_session(self, session_id: str) -> Optional[ResearchSession]:
        """Retrieve a research session."""
        # Check cache first
        if session_id in self._session_cache:
            return self._session_cache[session_id]
        
        # Load from database
        async with get_session() as db_session:
            result = await db_session.execute(
                select(ResearchSessionModel).where(
                    ResearchSessionModel.session_id == session_id
                )
            )
            db_session_obj = result.scalar_one_or_none()
            
            if db_session_obj:
                session = ResearchSession(
                    session_id=db_session_obj.session_id,
                    company=db_session_obj.company,
                    query=db_session_obj.query,
                    plan_id=db_session_obj.plan_id,
                    status=db_session_obj.status,
                    steps=json.loads(db_session_obj.steps) if db_session_obj.steps else [],
                    results=json.loads(db_session_obj.results) if db_session_obj.results else {},
                    conclusions=json.loads(db_session_obj.conclusions) if db_session_obj.conclusions else [],
                    reports=json.loads(db_session_obj.reports) if db_session_obj.reports else [],
                    started_at=db_session_obj.started_at,
                    completed_at=db_session_obj.completed_at,
                    duration_seconds=db_session_obj.duration_seconds,
                    error=db_session_obj.error,
                    metadata=json.loads(db_session_obj.metadata) if db_session_obj.metadata else {}
                )
                self._session_cache[session_id] = session
                return session
        
        return None
    
    async def store_memory(self, memory: ResearchMemory) -> str:
        """Store a memory entry."""
        self._memory_cache[memory.memory_id] = memory
        
        # Persist to database
        async with get_session() as db_session:
            db_session.add(ResearchMemoryModel(
                memory_id=memory.memory_id,
                memory_type=memory.memory_type.value,
                company=memory.company,
                content=json.dumps(memory.content),
                source_agent=memory.source_agent,
                session_id=memory.session_id,
                tags=json.dumps(memory.tags),
                confidence=memory.confidence,
                created_at=memory.created_at,
                updated_at=memory.updated_at,
                access_count=memory.access_count,
                last_accessed=memory.last_accessed,
                metadata=json.dumps(memory.metadata)
            ))
            await db_session.commit()
        
        return memory.memory_id
    
    async def retrieve_memories(
        self,
        company: str,
        query: Optional[str] = None,
        memory_types: Optional[List[MemoryType]] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[ResearchMemory]:
        """Retrieve relevant memories for a company/query."""
        # Build query
        conditions = ["company = :company"]
        params = {"company": company}
        
        if memory_types:
            placeholders = ",".join([f":mt{i}" for i in range(len(memory_types))])
            conditions.append(f"memory_type IN ({placeholders})")
            for i, mt in enumerate(memory_types):
                params[f"mt{i}"] = mt.value
        
        if tags:
            # Tags are stored as JSON array, use JSON functions
            for tag in tags:
                conditions.append(f"JSON_CONTAINS(tags, :tag{tag})")
                params[f"tag{tag}"] = f'"{tag}"'
        
        query_str = f"""
            SELECT * FROM research_memory 
            WHERE {' AND '.join(conditions)}
            ORDER BY confidence DESC, created_at DESC
            LIMIT :limit
        """
        params["limit"] = limit
        
        async with get_session() as db_session:
            result = await db_session.execute(text(query_str), params)
            rows = result.fetchall()
            
            memories = []
            for row in rows:
                memory = ResearchMemory(
                    memory_id=row.memory_id,
                    memory_type=MemoryType(row.memory_type),
                    company=row.company,
                    content=json.loads(row.content),
                    source_agent=row.source_agent,
                    session_id=row.session_id,
                    tags=json.loads(row.tags) if row.tags else [],
                    confidence=row.confidence,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    access_count=row.access_count,
                    last_accessed=row.last_accessed,
                    metadata=json.loads(row.metadata) if row.metadata else {}
                )
                # Update access stats
                await self._update_access_stats(memory.memory_id)
                memories.append(memory)
            
            return memories
    
    async def _update_access_stats(self, memory_id: str):
        """Update access count and last accessed time."""
        async with get_session() as db_session:
            await db_session.execute(
                text("""
                    UPDATE research_memory 
                    SET access_count = access_count + 1, 
                        last_accessed = :now 
                    WHERE memory_id = :mid
                """),
                {"now": datetime.now(), "mid": memory_id}
            )
            await db_session.commit()
    
    async def store_agent_output(
        self,
        company: str,
        agent_type: str,
        output: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> str:
        """Store agent output as memory."""
        memory = ResearchMemory(
            memory_id=str(uuid.uuid4())[:8],
            memory_type=MemoryType.AGENT_OUTPUT,
            company=company,
            content={
                "agent_type": agent_type,
                "output": output
            },
            source_agent=agent_type,
            session_id=session_id,
            tags=[agent_type, company.lower()],
            confidence=1.0
        )
        
        return await self.store_memory(memory)
    
    async def store_conclusion(
        self,
        company: str,
        conclusion: str,
        source_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        confidence: float = 1.0,
        tags: Optional[List[str]] = None
    ) -> str:
        """Store a research conclusion."""
        memory = ResearchMemory(
            memory_id=str(uuid.uuid4())[:8],
            memory_type=MemoryType.CONCLUSION,
            company=company,
            content={
                "conclusion": conclusion,
                "source_agent": source_agent
            },
            source_agent=source_agent,
            session_id=session_id,
            tags=tags or ["conclusion", company.lower()],
            confidence=confidence
        )
        
        return await self.store_memory(memory)
    
    async def get_recent_sessions(
        self,
        company: Optional[str] = None,
        limit: int = 10
    ) -> List[ResearchSession]:
        """Get recent research sessions."""
        conditions = []
        params = {}
        
        if company:
            conditions.append("company = :company")
            params["company"] = company
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        query_str = f"""
            SELECT * FROM research_sessions 
            {where_clause}
            ORDER BY started_at DESC
            LIMIT :limit
        """
        params["limit"] = limit
        
        async with get_session() as db_session:
            result = await db_session.execute(text(query_str), params)
            rows = result.fetchall()
            
            sessions = []
            for row in rows:
                session = ResearchSession(
                    session_id=row.session_id,
                    company=row.company,
                    query=row.query,
                    plan_id=row.plan_id,
                    status=row.status,
                    steps=json.loads(row.steps) if row.steps else [],
                    results=json.loads(row.results) if row.results else {},
                    conclusions=json.loads(row.conclusions) if row.conclusions else [],
                    reports=json.loads(row.reports) if row.reports else [],
                    started_at=row.started_at,
                    completed_at=row.completed_at,
                    duration_seconds=row.duration_seconds,
                    error=row.error,
                    metadata=json.loads(row.metadata) if row.metadata else {}
                )
                sessions.append(session)
            
            return sessions
    
    async def search_by_embedding(
        self,
        embedding: List[float],
        company: Optional[str] = None,
        limit: int = 5
    ) -> List[ResearchMemory]:
        """Search memories by vector similarity (requires pgvector)."""
        # This would use pgvector for semantic search
        # For now, return recent memories as fallback
        return await self.retrieve_memories(
            company=company or "",
            limit=limit
        )


# Global instance
_memory_store: Optional[ResearchMemoryStore] = None


def get_memory_store() -> ResearchMemoryStore:
    """Get global memory store instance."""
    global _memory_store
    if _memory_store is None:
        _memory_store = ResearchMemoryStore()
    return _memory_store