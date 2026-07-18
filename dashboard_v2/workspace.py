"""
Research Workspace
Interactive research workspace for the Enterprise Dashboard v2.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class WorkspaceMode(str, Enum):
    """Research workspace modes."""
    EXPLORATION = "exploration"      # Free-form exploration
    ANALYSIS = "analysis"            # Structured analysis
    REPORTING = "reporting"          # Report generation
    COLLABORATION = "collaboration"  # Team collaboration


class PanelType(str, Enum):
    """Types of workspace panels."""
    QUERY_BUILDER = "query_builder"
    RESULTS_VIEWER = "results_viewer"
    EVIDENCE_PANEL = "evidence_panel"
    THESIS_BUILDER = "thesis_builder"
    NOTE_TAKING = "note_taking"
    SOURCE_MANAGER = "source_manager"
    VISUALIZATION = "visualization"
    EXPORT_PANEL = "export_panel"


@dataclass
class WorkspacePanel:
    """Panel in the research workspace."""
    panel_id: str
    panel_type: PanelType
    title: str
    position: Dict[str, int]  # x, y, width, height
    state: Dict[str, Any] = field(default_factory=dict)
    visible: bool = True
    minimized: bool = False


@dataclass
class ResearchQuery:
    """Research query with parameters."""
    query_id: str
    text: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "pending"  # pending, running, completed, failed
    results: Optional[Dict[str, Any]] = None


@dataclass
class ResearchNote:
    """Research note or annotation."""
    note_id: str
    content: str
    author: str
    tags: List[str] = field(default_factory=list)
    linked_entities: List[str] = field(default_factory=list)
    linked_evidence: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WorkspaceSession:
    """Research workspace session."""
    session_id: str
    name: str
    mode: WorkspaceMode = WorkspaceMode.EXPLORATION
    panels: List[WorkspacePanel] = field(default_factory=list)
    queries: List[ResearchQuery] = field(default_factory=list)
    notes: List[ResearchNote] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResearchWorkspace:
    """
    Interactive research workspace for collaborative financial research.
    Provides query building, evidence review, thesis building, and reporting.
    """
    
    def __init__(self):
        self._sessions: Dict[str, WorkspaceSession] = {}
        self._active_session: Optional[str] = None
        self._query_history: List[ResearchQuery] = []
        self._shared_notes: Dict[str, List[ResearchNote]] = defaultdict(list)
    
    def create_session(
        self,
        name: str,
        mode: WorkspaceMode = WorkspaceMode.EXPLORATION,
        template: Optional[str] = None
    ) -> WorkspaceSession:
        """Create a new research session."""
        
        session_id = f"ws_{datetime.utcnow().timestamp()}"
        
        # Default panels based on mode
        panels = self._get_default_panels(mode)
        
        session = WorkspaceSession(
            session_id=session_id,
            name=name,
            mode=mode,
            panels=panels
        )
        
        if template:
            self._apply_template(session, template)
        
        self._sessions[session_id] = session
        self._active_session = session_id
        
        logger.info(f"Created workspace session: {session_id} ({mode.value})")
        return session
    
    def _get_default_panels(self, mode: WorkspaceMode) -> List[WorkspacePanel]:
        """Get default panels for a workspace mode."""
        
        base_panels = [
            WorkspacePanel(
                panel_id="query_builder",
                panel_type=PanelType.QUERY_BUILDER,
                title="Query Builder",
                position={"x": 0, "y": 0, "width": 400, "height": 300}
            ),
            WorkspacePanel(
                panel_id="results_viewer",
                panel_type=PanelType.RESULTS_VIEWER,
                title="Results",
                position={"x": 400, "y": 0, "width": 600, "height": 300}
            ),
            WorkspacePanel(
                panel_id="evidence_panel",
                panel_type=PanelType.EVIDENCE_PANEL,
                title="Evidence",
                position={"x": 0, "y": 300, "width": 500, "height": 400}
            ),
        ]
        
        if mode == WorkspaceMode.ANALYSIS:
            base_panels.append(WorkspacePanel(
                panel_id="thesis_builder",
                panel_type=PanelType.THESIS_BUILDER,
                title="Thesis Builder",
                position={"x": 500, "y": 300, "width": 500, "height": 400}
            ))
        elif mode == WorkspaceMode.REPORTING:
            base_panels.extend([
                WorkspacePanel(
                    panel_id="thesis_builder",
                    panel_type=PanelType.THESIS_BUILDER,
                    title="Thesis Builder",
                    position={"x": 500, "y": 300, "width": 500, "height": 400}
                ),
                WorkspacePanel(
                    panel_id="export_panel",
                    panel_type=PanelType.EXPORT_PANEL,
                    title="Export",
                    position={"x": 0, "y": 700, "width": 1000, "height": 200}
                )
            ])
        elif mode == WorkspaceMode.COLLABORATION:
            base_panels.append(WorkspacePanel(
                panel_id="note_taking",
                panel_type=PanelType.NOTE_TAKING,
                title="Notes",
                position={"x": 500, "y": 300, "width": 500, "height": 400}
            ))
        
        return base_panels
    
    def _apply_template(self, session: WorkspaceSession, template: str) -> None:
        """Apply a template to the session."""
        # Template logic would go here
        pass
    
    def get_session(self, session_id: str) -> Optional[WorkspaceSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)
    
    def get_active_session(self) -> Optional[WorkspaceSession]:
        """Get the currently active session."""
        if self._active_session:
            return self._sessions.get(self._active_session)
        return None
    
    def set_active_session(self, session_id: str) -> bool:
        """Set the active session."""
        if session_id in self._sessions:
            self._active_session = session_id
            return True
        return False
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions."""
        return [
            {
                "session_id": s.session_id,
                "name": s.name,
                "mode": s.mode.value,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "query_count": len(s.queries),
                "note_count": len(s.notes)
            }
            for s in self._sessions.values()
        ]
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            if self._active_session == session_id:
                self._active_session = next(iter(self._sessions.keys()), None)
            return True
        return False
    
    # Query management
    
    def create_query(
        self,
        session_id: str,
        text: str,
        parameters: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Optional[ResearchQuery]:
        """Create a new research query."""
        
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        query = ResearchQuery(
            query_id=f"q_{datetime.utcnow().timestamp()}",
            text=text,
            parameters=parameters or {},
            filters=filters or {}
        )
        
        session.queries.append(query)
        self._query_history.append(query)
        session.updated_at = datetime.utcnow()
        
        return query
    
    def update_query(
        self,
        session_id: str,
        query_id: str,
        **kwargs
    ) -> bool:
        """Update a research query."""
        
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        for query in session.queries:
            if query.query_id == query_id:
                for key, value in kwargs.items():
                    if hasattr(query, key):
                        setattr(query, key, value)
                query.updated_at = datetime.utcnow()
                session.updated_at = datetime.utcnow()
                return True
        
        return False
    
    def get_query(self, session_id: str, query_id: str) -> Optional[ResearchQuery]:
        """Get a query by ID."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        for query in session.queries:
            if query.query_id == query_id:
                return query
        return None
    
    def delete_query(self, session_id: str, query_id: str) -> bool:
        """Delete a query."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session.queries = [q for q in session.queries if q.query_id != query_id]
        session.updated_at = datetime.utcnow()
        return True
    
    # Note management
    
    def create_note(
        self,
        session_id: str,
        content: str,
        author: str,
        tags: Optional[List[str]] = None,
        linked_entities: Optional[List[str]] = None,
        linked_evidence: Optional[List[str]] = None
    ) -> Optional[ResearchNote]:
        """Create a research note."""
        
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        note = ResearchNote(
            note_id=f"note_{datetime.utcnow().timestamp()}",
            content=content,
            author=author,
            tags=tags or [],
            linked_entities=linked_entities or [],
            linked_evidence=linked_evidence or []
        )
        
        session.notes.append(note)
        session.updated_at = datetime.utcnow()
        
        # Also add to shared notes if tagged for sharing
        if "shared" in (tags or []):
            self._shared_notes[session_id].append(note)
        
        return note
    
    def update_note(
        self,
        session_id: str,
        note_id: str,
        **kwargs
    ) -> bool:
        """Update a research note."""
        
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        for note in session.notes:
            if note.note_id == note_id:
                for key, value in kwargs.items():
                    if hasattr(note, key):
                        setattr(note, key, value)
                note.updated_at = datetime.utcnow()
                session.updated_at = datetime.utcnow()
                return True
        
        return False
    
    def delete_note(self, session_id: str, note_id: str) -> bool:
        """Delete a research note."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session.notes = [n for n in session.notes if n.note_id != note_id]
        session.updated_at = datetime.utcnow()
        return True
    
    def get_shared_notes(self, session_id: str) -> List[ResearchNote]:
        """Get shared notes for a session."""
        return self._shared_notes.get(session_id, [])
    
    # Panel management
    
    def add_panel(self, session_id: str, panel: WorkspacePanel) -> bool:
        """Add a panel to a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session.panels.append(panel)
        session.updated_at = datetime.utcnow()
        return True
    
    def update_panel(
        self,
        session_id: str,
        panel_id: str,
        **kwargs
    ) -> bool:
        """Update a panel."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        for panel in session.panels:
            if panel.panel_id == panel_id:
                for key, value in kwargs.items():
                    if hasattr(panel, key):
                        setattr(panel, key, value)
                session.updated_at = datetime.utcnow()
                return True
        return False
    
    def remove_panel(self, session_id: str, panel_id: str) -> bool:
        """Remove a panel from a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session.panels = [p for p in session.panels if p.panel_id != panel_id]
        session.updated_at = datetime.utcnow()
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get workspace statistics."""
        return {
            "total_sessions": len(self._sessions),
            "active_session": self._active_session,
            "total_queries": len(self._query_history),
            "total_notes": sum(len(s.notes) for s in self._sessions.values()),
            "shared_notes": sum(len(n) for n in self._shared_notes.values()),
            "sessions_by_mode": {
                mode.value: sum(1 for s in self._sessions.values() if s.mode == mode)
                for mode in WorkspaceMode
            }
        }


# Global research workspace instance
_research_workspace: Optional[ResearchWorkspace] = None


def get_research_workspace() -> ResearchWorkspace:
    global _research_workspace
    if _research_workspace is None:
        _research_workspace = ResearchWorkspace()
    return _research_workspace


async def close_research_workspace() -> None:
    global _research_workspace
    if _research_workspace:
        _research_workspace = None