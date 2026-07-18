"""
Human Approval Workflow System

Supports approval gates for research workflows with:
- Approve/Reject/Request Changes/Escalate actions
- Multi-level approval chains
- Audit trail
- Integration with notification engine
"""
import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import logging

from config.settings import get_settings
from database.connection import get_session
from database.models import ApprovalRequest, ApprovalAction, User
from notifications.engine import get_notification_engine, NotificationChannel, NotificationPriority

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Approval request status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"
    ESCALATED = "escalated"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalActionType(Enum):
    """Types of approval actions."""
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"
    ESCALATE = "escalate"
    DELEGATE = "delegate"
    COMMENT = "comment"


@dataclass
class Approver:
    """Approver information."""
    user_id: str
    name: str
    email: str
    role: str
    is_required: bool = True
    order: int = 0  # For sequential approvals


@dataclass
class ApprovalActionRecord:
    """Record of an approval action."""
    action_id: str
    request_id: str
    action_type: ApprovalActionType
    user_id: str
    user_name: str
    comment: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalRequest:
    """Approval request for research workflow."""
    request_id: str
    title: str
    description: str
    request_type: str  # research_plan, report, investment_decision, etc.
    reference_id: str  # ID of the object being approved
    reference_type: str  # plan, report, thesis, etc.
    requester_id: str
    requester_name: str
    approvers: List[Approver]
    status: ApprovalStatus = ApprovalStatus.PENDING
    current_approver_index: int = 0
    actions: List[ApprovalActionRecord] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ApprovalWorkflow:
    """
    Manages human approval workflows for research processes.
    
    Features:
    - Sequential and parallel approval chains
    - Multi-level approvals (analyst -> senior analyst -> manager)
    - Escalation paths
    - Request changes with feedback
    - Audit trail
    - Integration with notification engine
    - Expiration handling
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.notification_engine = get_notification_engine()
        
        # Pending requests
        self._pending_requests: Dict[str, ApprovalRequest] = {}
        
        # Callbacks
        self.on_approval_required: Optional[Callable[[ApprovalRequest], None]] = None
        self.on_approval_completed: Optional[Callable[[ApprovalRequest], None]] = None
        self.on_approval_expired: Optional[Callable[[ApprovalRequest], None]] = None
    
    async def create_request(
        self,
        title: str,
        description: str,
        request_type: str,
        reference_id: str,
        reference_type: str,
        requester_id: str,
        requester_name: str,
        approvers: List[Dict[str, Any]],
        expires_in_hours: int = 72,
        metadata: Optional[Dict] = None
    ) -> ApprovalRequest:
        """Create a new approval request."""
        # Convert approver dicts to Approver objects
        approver_objects = []
        for i, appr in enumerate(approvers):
            approver_objects.append(Approver(
                user_id=appr["user_id"],
                name=appr.get("name", appr["user_id"]),
                email=appr.get("email", ""),
                role=appr.get("role", "approver"),
                is_required=appr.get("is_required", True),
                order=appr.get("order", i)
            ))
        
        # Sort by order
        approver_objects.sort(key=lambda a: a.order)
        
        # Calculate expiration
        from datetime import timedelta
        expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        
        request = ApprovalRequest(
            request_id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            request_type=request_type,
            reference_id=reference_id,
            reference_type=reference_type,
            requester_id=requester_id,
            requester_name=requester_name,
            approvers=approver_objects,
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        self._pending_requests[request.request_id] = request
        await self._persist_request(request)
        
        # Notify first approver(s)
        await self._notify_approvers(request)
        
        logger.info(f"Created approval request: {request.request_id} - {request.title}")
        
        if self.on_approval_required:
            await self.on_approval_required(request)
        
        return request
    
    async def process_action(
        self,
        request_id: str,
        action_type: ApprovalActionType,
        user_id: str,
        user_name: str,
        comment: str = "",
        metadata: Optional[Dict] = None
    ) -> ApprovalRequest:
        """Process an approval action."""
        request = self._pending_requests.get(request_id)
        if not request:
            # Try loading from database
            request = await self._load_request(request_id)
        
        if not request:
            raise ValueError(f"Approval request not found: {request_id}")
        
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(f"Request is not pending: {request.status.value}")
        
        # Check if user is current approver
        if request.current_approver_index >= len(request.approvers):
            raise ValueError("No more approvers in chain")
        
        current_approver = request.approvers[request.current_approver_index]
        if current_approver.user_id != user_id:
            # Check if user is in approver list but not current
            allowed = any(a.user_id == user_id for a in request.approvers)
            if not allowed:
                raise ValueError("User is not an approver for this request")
        
        # Record action
        action = ApprovalActionRecord(
            action_id=str(uuid.uuid4())[:8],
            request_id=request_id,
            action_type=action_type,
            user_id=user_id,
            user_name=user_name,
            comment=comment,
            metadata=metadata or {}
        )
        request.actions.append(action)
        request.updated_at = datetime.now()
        
        # Process based on action type
        if action_type == ApprovalActionType.APPROVE:
            await self._handle_approve(request, action)
        elif action_type == ApprovalActionType.REJECT:
            await self._handle_reject(request, action)
        elif action_type == ApprovalActionType.REQUEST_CHANGES:
            await self._handle_changes_requested(request, action)
        elif action_type == ApprovalActionType.ESCALATE:
            await self._handle_escalate(request, action)
        elif action_type == ApprovalActionType.DELEGATE:
            await self._handle_delegate(request, action, metadata)
        elif action_type == ApprovalActionType.COMMENT:
            await self._handle_comment(request, action)
        
        await self._persist_request(request)
        
        if request.status != ApprovalStatus.PENDING:
            self._pending_requests.pop(request_id, None)
            if self.on_approval_completed:
                await self.on_approval_completed(request)
        
        logger.info(f"Processed {action_type.value} for request {request_id} by {user_name}")
        return request
    
    async def _handle_approve(self, request: ApprovalRequest, action: ApprovalActionRecord):
        """Handle approval action."""
        request.current_approver_index += 1
        
        if request.current_approver_index >= len(request.approvers):
            # All approvers approved
            request.status = ApprovalStatus.APPROVED
            request.completed_at = datetime.now()
            
            # Notify requester
            await self._notify_requester(
                request,
                f"✅ Approved: {request.title}",
                f"Your request has been fully approved.\n\nApproved by: {action.user_name}\nComment: {action.comment}"
            )
        else:
            # Notify next approver
            await self._notify_approvers(request)
    
    async def _handle_reject(self, request: ApprovalRequest, action: ApprovalActionRecord):
        """Handle rejection action."""
        request.status = ApprovalStatus.REJECTED
        request.completed_at = datetime.now()
        
        # Notify requester
        await self._notify_requester(
            request,
            f"❌ Rejected: {request.title}",
            f"Your request has been rejected.\n\nRejected by: {action.user_name}\nReason: {action.comment}"
        )
    
    async def _handle_changes_requested(self, request: ApprovalRequest, action: ApprovalActionRecord):
        """Handle changes requested action."""
        request.status = ApprovalStatus.CHANGES_REQUESTED
        request.completed_at = datetime.now()
        
        # Notify requester with requested changes
        await self._notify_requester(
            request,
            f"🔄 Changes Requested: {request.title}",
            f"Changes have been requested for your request.\n\nRequested by: {action.user_name}\nRequired changes: {action.comment}"
        )
    
    async def _handle_escalate(self, request: ApprovalRequest, action: ApprovalActionRecord):
        """Handle escalation action."""
        request.status = ApprovalStatus.ESCALATED
        
        # Add escalation metadata
        escalated_to = action.metadata.get("escalated_to") if action.metadata else None
        
        if escalated_to:
            # Add escalated approver
            new_approver = Approver(
                user_id=escalated_to,
                name=action.metadata.get("escalated_name", escalated_to),
                email=action.metadata.get("escalated_email", ""),
                role="escalated_approver",
                order=len(request.approvers)
            )
            request.approvers.append(new_approver)
        
        request.updated_at = datetime.now()
        
        # Notify requester and escalated approver
        await self._notify_requester(
            request,
            f"⬆️ Escalated: {request.title}",
            f"Your request has been escalated.\n\nEscalated by: {action.user_name}\nReason: {action.comment}"
        )
        
        if escalated_to:
            await self._notify_approvers(request)
    
    async def _handle_delegate(self, request: ApprovalRequest, action: ApprovalActionRecord, metadata: Optional[Dict]):
        """Handle delegation action."""
        delegate_to = metadata.get("delegate_to") if metadata else None
        delegate_name = metadata.get("delegate_name", delegate_to) if metadata else delegate_to
        
        if delegate_to:
            # Replace current approver with delegate
            request.approvers[request.current_approver_index] = Approver(
                user_id=delegate_to,
                name=delegate_name,
                email=metadata.get("delegate_email", "") if metadata else "",
                role="delegated_approver",
                order=request.approvers[request.current_approver_index].order
            )
            request.updated_at = datetime.now()
            
            # Notify delegate
            await self._notify_approvers(request)
    
    async def _handle_comment(self, request: ApprovalRequest, action: ApprovalActionRecord):
        """Handle comment action (no state change)."""
        # Just record the comment, notify relevant parties
        await self._notify_requester(
            request,
            f"💬 Comment: {request.title}",
            f"New comment on your request:\n\nFrom: {action.user_name}\nComment: {action.comment}"
        )
    
    async def _notify_approvers(self, request: ApprovalRequest):
        """Notify current approver(s)."""
        if request.current_approver_index >= len(request.approvers):
            return
        
        approver = request.approvers[request.current_approver_index]
        
        await self.notification_engine.send(
            subject=f"📋 Approval Required: {request.title}",
            body=f"""You have a pending approval request.

**Request:** {request.title}
**Type:** {request.request_type}
**Reference:** {request.reference_type} ({request.reference_id})
**Requester:** {request.requester_name}
**Description:** {request.description}

**Action Required:** Please review and approve, reject, or request changes.

**Expires:** {request.expires_at.strftime('%Y-%m-%d %H:%M UTC') if request.expires_at else 'No expiration'}""",
            channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP, NotificationChannel.CONSOLE],
            recipient=approver.email or approver.user_id,
            priority=NotificationPriority.HIGH,
            metadata={
                "approval_request_id": request.request_id,
                "action": "approval_required"
            }
        )
    
    async def _notify_requester(self, request: ApprovalRequest, subject: str, body: str):
        """Notify the requester of status change."""
        await self.notification_engine.send(
            subject=subject,
            body=body,
            channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP, NotificationChannel.CONSOLE],
            recipient=request.requester_id,
            priority=NotificationPriority.HIGH,
            metadata={
                "approval_request_id": request.request_id,
                "status": request.status.value
            }
        )
    
    async def _persist_request(self, request: ApprovalRequest):
        """Persist approval request to database."""
        try:
            async with get_session() as db_session:
                db_request = await db_session.get(ApprovalRequestModel, request.request_id)
                if not db_request:
                    db_request = ApprovalRequestModel(request_id=request.request_id)
                    db_session.add(db_request)
                
                db_request.title = request.title
                db_request.description = request.description
                db_request.request_type = request.request_type
                db_request.reference_id = request.reference_id
                db_request.reference_type = request.reference_type
                db_request.requester_id = request.requester_id
                db_request.requester_name = request.requester_name
                db_request.approvers = json.dumps([
                    {
                        "user_id": a.user_id,
                        "name": a.name,
                        "email": a.email,
                        "role": a.role,
                        "is_required": a.is_required,
                        "order": a.order
                    }
                    for a in request.approvers
                ])
                db_request.current_approver_index = request.current_approver_index
                db_request.status = request.status.value
                db_request.actions = json.dumps([
                    {
                        "action_id": a.action_id,
                        "action_type": a.action_type.value,
                        "user_id": a.user_id,
                        "user_name": a.user_name,
                        "comment": a.comment,
                        "timestamp": a.timestamp.isoformat(),
                        "metadata": a.metadata
                    }
                    for a in request.actions
                ])
                db_request.created_at = request.created_at
                db_request.updated_at = request.updated_at
                db_request.completed_at = request.completed_at
                db_request.expires_at = request.expires_at
                db_request.metadata = json.dumps(request.metadata)
                
                await db_session.commit()
        except Exception as e:
            logger.error(f"Failed to persist approval request: {e}")
    
    async def _load_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Load approval request from database."""
        try:
            async with get_session() as db_session:
                result = await db_session.execute(
                    select(ApprovalRequestModel).where(
                        ApprovalRequestModel.request_id == request_id
                    )
                )
                db_request = result.scalar_one_or_none()
                
                if not db_request:
                    return None
                
                return ApprovalRequest(
                    request_id=db_request.request_id,
                    title=db_request.title,
                    description=db_request.description,
                    request_type=db_request.request_type,
                    reference_id=db_request.reference_id,
                    reference_type=db_request.reference_type,
                    requester_id=db_request.requester_id,
                    requester_name=db_request.requester_name,
                    approvers=[
                        Approver(**a) for a in json.loads(db_request.approvers)
                    ],
                    status=ApprovalStatus(db_request.status),
                    current_approver_index=db_request.current_approver_index,
                    actions=[
                        ApprovalActionRecord(
                            action_id=a["action_id"],
                            request_id=request_id,
                            action_type=ApprovalActionType(a["action_type"]),
                            user_id=a["user_id"],
                            user_name=a["user_name"],
                            comment=a["comment"],
                            timestamp=datetime.fromisoformat(a["timestamp"]),
                            metadata=a.get("metadata", {})
                        )
                        for a in json.loads(db_request.actions)
                    ],
                    created_at=db_request.created_at,
                    updated_at=db_request.updated_at,
                    completed_at=db_request.completed_at,
                    expires_at=db_request.expires_at,
                    metadata=json.loads(db_request.metadata) if db_request.metadata else {}
                )
        except Exception as e:
            logger.error(f"Failed to load approval request: {e}")
        
        return None
    
    async def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get approval request by ID."""
        if request_id in self._pending_requests:
            return self._pending_requests[request_id]
        return await self._load_request(request_id)
    
    async def list_pending_requests(
        self,
        user_id: Optional[str] = None,
        status: Optional[ApprovalStatus] = None
    ) -> List[ApprovalRequest]:
        """List pending approval requests."""
        requests = []
        
        # Check memory cache
        for request in self._pending_requests.values():
            if user_id:
                # Check if user is an approver
                if not any(a.user_id == user_id for a in request.approvers):
                    continue
            if status and request.status != status:
                continue
            requests.append(request)
        
        # Load from database for others
        async with get_session() as db_session:
            query = select(ApprovalRequestModel)
            
            if status:
                query = query.where(ApprovalRequestModel.status == status.value)
            
            result = await db_session.execute(query.order_by(ApprovalRequestModel.created_at.desc()))
            
            for db_request in result.scalars():
                if db_request.request_id not in self._pending_requests:
                    request = await self._load_request(db_request.request_id)
                    if request:
                        if user_id and not any(a.user_id == user_id for a in request.approvers):
                            continue
                        requests.append(request)
        
        return requests
    
    async def check_expired_requests(self) -> List[ApprovalRequest]:
        """Check for and process expired requests."""
        expired = []
        now = datetime.now()
        
        for request_id, request in list(self._pending_requests.items()):
            if request.expires_at and request.expires_at < now:
                request.status = ApprovalStatus.EXPIRED
                request.completed_at = now
                request.updated_at = now
                
                await self._persist_request(request)
                self._pending_requests.pop(request_id, None)
                expired.append(request)
                
                # Notify requester
                await self._notify_requester(
                    request,
                    f"⏰ Expired: {request.title}",
                    f"Your approval request has expired without action."
                )
                
                if self.on_approval_expired:
                    await self.on_approval_expired(request)
        
        return expired


# Database models
from sqlalchemy import Column, String, Text, DateTime, Integer
from database.connection import Base


class ApprovalRequestModel(Base):
    __tablename__ = "approval_requests"
    
    request_id = Column(String(64), primary_key=True)
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    request_type = Column(String(64), nullable=False)
    reference_id = Column(String(64), nullable=False)
    reference_type = Column(String(64), nullable=False)
    requester_id = Column(String(64), nullable=False)
    requester_name = Column(String(128), nullable=False)
    approvers = Column(Text, nullable=False)  # JSON
    current_approver_index = Column(Integer, default=0)
    status = Column(String(32), default="pending")
    actions = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    metadata = Column(Text, nullable=True)  # JSON


# Global instance
_approval_workflow: Optional[ApprovalWorkflow] = None


def get_approval_workflow() -> ApprovalWorkflow:
    """Get global approval workflow instance."""
    global _approval_workflow
    if _approval_workflow is None:
        _approval_workflow = ApprovalWorkflow()
    return _approval_workflow