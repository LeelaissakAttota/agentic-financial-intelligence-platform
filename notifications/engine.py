"""
Notification Engine

Multi-channel notification delivery with retry logic, history tracking,
and support for Email, Slack, Discord, Webhook, and Console channels.
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import logging

import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config.settings import get_settings
from database.connection import get_session
from database.models import Notification, NotificationChannel

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Supported notification channels."""
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    CONSOLE = "console"
    IN_APP = "in_app"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class NotificationTemplate:
    """Template for notification content."""
    template_id: str
    name: str
    subject_template: str
    body_template: str
    channels: List[NotificationChannel]
    variables: List[str] = field(default_factory=list)


@dataclass
class Notification:
    """A notification to be delivered."""
    notification_id: str
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    status: str = "pending"  # pending, sent, failed
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class NotificationChannelHandler:
    """Base class for channel handlers."""
    
    async def send(self, notification: Notification) -> bool:
        """Send notification. Returns True if successful."""
        raise NotImplementedError
    
    def validate_recipient(self, recipient: str) -> bool:
        """Validate recipient format for this channel."""
        return True


class EmailChannelHandler(NotificationChannelHandler):
    """Email notification handler."""
    
    def __init__(self):
        self.settings = get_settings()
        self.smtp_host = self.settings.smtp_host
        self.smtp_port = self.settings.smtp_port
        self.smtp_user = self.settings.smtp_user
        self.smtp_password = self.settings.smtp_password
        self.from_email = self.settings.from_email
        self.use_tls = self.settings.smtp_use_tls
    
    def validate_recipient(self, recipient: str) -> bool:
        return "@" in recipient and "." in recipient.split("@")[1]
    
    async def send(self, notification: Notification) -> bool:
        if not all([self.smtp_host, self.smtp_user, self.smtp_password]):
            logger.warning("Email not configured, skipping")
            return False
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = notification.subject
            msg["From"] = self.from_email
            msg["To"] = notification.recipient
            
            # Add both plain text and HTML
            text_part = MIMEText(notification.body, "plain")
            html_part = MIMEText(self._to_html(notification.body), "html")
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send via SMTP
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False
    
    def _to_html(self, text: str) -> str:
        """Convert plain text to basic HTML."""
        html = text.replace("\n", "<br>")
        html = f"<html><body><pre style='font-family: inherit;'>{html}</pre></body></html>"
        return html


class SlackChannelHandler(NotificationChannelHandler):
    """Slack webhook notification handler."""
    
    def __init__(self):
        self.settings = get_settings()
        self.webhook_url = self.settings.slack_webhook_url
    
    async def send(self, notification: Notification) -> bool:
        if not self.webhook_url:
            logger.warning("Slack webhook not configured")
            return False
        
        try:
            payload = {
                "text": notification.subject,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{notification.subject}*\n{notification.body}"
                        }
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    return resp.status == 200
                    
        except Exception as e:
            logger.error(f"Slack send failed: {e}")
            return False


class DiscordChannelHandler(NotificationChannelHandler):
    """Discord webhook notification handler."""
    
    def __init__(self):
        self.settings = get_settings()
        self.webhook_url = self.settings.discord_webhook_url
    
    async def send(self, notification: Notification) -> bool:
        if not self.webhook_url:
            logger.warning("Discord webhook not configured")
            return False
        
        try:
            color_map = {
                NotificationPriority.LOW: 0x95a5a6,
                NotificationPriority.NORMAL: 0x3498db,
                NotificationPriority.HIGH: 0xf39c12,
                NotificationPriority.CRITICAL: 0xe74c3c
            }
            
            payload = {
                "embeds": [{
                    "title": notification.subject,
                    "description": notification.body[:4000],  # Discord limit
                    "color": color_map.get(notification.priority, 0x3498db),
                    "timestamp": notification.created_at.isoformat(),
                    "footer": {"text": "Financial Research Agent"}
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    return resp.status in (200, 204)
                    
        except Exception as e:
            logger.error(f"Discord send failed: {e}")
            return False


class WebhookChannelHandler(NotificationChannelHandler):
    """Generic webhook notification handler."""
    
    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {"Content-Type": "application/json"}
    
    async def send(self, notification: Notification) -> bool:
        try:
            payload = {
                "notification_id": notification.notification_id,
                "subject": notification.subject,
                "body": notification.body,
                "priority": notification.priority.value,
                "metadata": notification.metadata,
                "created_at": notification.created_at.isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    return resp.status < 400
                    
        except Exception as e:
            logger.error(f"Webhook send failed: {e}")
            return False


class ConsoleChannelHandler(NotificationChannelHandler):
    """Console output handler for development/testing."""
    
    async def send(self, notification: Notification) -> bool:
        priority_markers = {
            NotificationPriority.LOW: "[LOW]",
            NotificationPriority.NORMAL: "[INFO]",
            NotificationPriority.HIGH: "[HIGH]",
            NotificationPriority.CRITICAL: "[CRITICAL]"
        }
        
        marker = priority_markers.get(notification.priority, "[INFO]")
        print(f"\n{marker} NOTIFICATION: {notification.subject}")
        print(f"To: {notification.recipient}")
        print(f"Body: {notification.body}")
        print("-" * 60)
        return True


class InAppChannelHandler(NotificationChannelHandler):
    """In-app notification handler (stores in database)."""
    
    async def send(self, notification: Notification) -> bool:
        try:
            async with get_session() as db_session:
                db_session.add(NotificationModel(
                    notification_id=notification.notification_id,
                    channel=notification.channel.value,
                    recipient=notification.recipient,
                    subject=notification.subject,
                    body=notification.body,
                    priority=notification.priority.value,
                    metadata=json.dumps(notification.metadata),
                    status="delivered",
                    sent_at=datetime.now()
                ))
                await db_session.commit()
            return True
        except Exception as e:
            logger.error(f"In-app notification failed: {e}")
            return False


class NotificationEngine:
    """
    Central notification engine with multi-channel support,
    retry logic, and history tracking.
    """
    
    def __init__(self):
        self.settings = get_settings()
        
        # Initialize channel handlers
        self.handlers: Dict[NotificationChannel, NotificationChannelHandler] = {
            NotificationChannel.EMAIL: EmailChannelHandler(),
            NotificationChannel.SLACK: SlackChannelHandler(),
            NotificationChannel.DISCORD: DiscordChannelHandler(),
            NotificationChannel.CONSOLE: ConsoleChannelHandler(),
            NotificationChannel.IN_APP: InAppChannelHandler()
        }
        
        # Custom webhook handlers
        self.webhook_handlers: Dict[str, WebhookChannelHandler] = {}
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delays = [60, 300, 900]  # 1min, 5min, 15min
        
        # History
        self.notification_history: List[Notification] = []
        
        # Callbacks
        self.on_notification_sent: Optional[Callable[[Notification], None]] = None
        self.on_notification_failed: Optional[Callable[[Notification], None]] = None
    
    def register_webhook(self, name: str, webhook_url: str, headers: Optional[Dict] = None):
        """Register a custom webhook handler."""
        self.webhook_handlers[name] = WebhookChannelHandler(webhook_url, headers)
        # Also add as channel
        self.handlers[NotificationChannel.WEBHOOK] = self.webhook_handlers[name]
        logger.info(f"Registered webhook: {name}")
    
    async def send(
        self,
        subject: str,
        body: str,
        channels: List[NotificationChannel],
        recipient: str = "",
        priority: NotificationPriority = NotificationPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        template_id: Optional[str] = None
    ) -> List[Notification]:
        """
        Send notification to multiple channels.
        
        Returns list of notification objects with delivery status.
        """
        notifications = []
        
        for channel in channels:
            # Skip if no recipient for email/slack
            if channel in (NotificationChannel.EMAIL, NotificationChannel.SLACK) and not recipient:
                logger.warning(f"Skipping {channel.value}: no recipient")
                continue
            
            notification = Notification(
                notification_id=str(uuid.uuid4())[:8],
                channel=channel,
                recipient=recipient or "default",
                subject=subject,
                body=body,
                priority=priority,
                metadata=metadata or {}
            )
            
            notifications.append(notification)
        
        # Send all notifications
        results = await asyncio.gather(
            *[self._send_with_retry(n) for n in notifications],
            return_exceptions=True
        )
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                notifications[i].status = "failed"
                notifications[i].error = str(result)
                logger.error(f"Notification {notifications[i].notification_id} failed: {result}")
        
        # Store in history
        self.notification_history.extend(notifications)
        
        # Persist to database
        await self._persist_notifications(notifications)
        
        return notifications
    
    async def _send_with_retry(self, notification: Notification) -> bool:
        """Send notification with retry logic."""
        handler = self.handlers.get(notification.channel)
        if not handler:
            notification.status = "failed"
            notification.error = f"No handler for channel: {notification.channel.value}"
            return False
        
        # Validate recipient
        if not handler.validate_recipient(notification.recipient):
            notification.status = "failed"
            notification.error = f"Invalid recipient for {notification.channel.value}: {notification.recipient}"
            return False
        
        for attempt in range(self.max_retries + 1):
            notification.retry_count = attempt
            
            try:
                success = await handler.send(notification)
                
                if success:
                    notification.status = "sent"
                    notification.sent_at = datetime.now()
                    
                    if self.on_notification_sent:
                        self.on_notification_sent(notification)
                    
                    logger.info(f"Notification {notification.notification_id} sent via {notification.channel.value}")
                    return True
                else:
                    if attempt < self.max_retries:
                        delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                        logger.warning(f"Notification {notification.notification_id} failed, retrying in {delay}s")
                        await asyncio.sleep(delay)
                    else:
                        notification.status = "failed"
                        notification.error = "Max retries exceeded"
                        
                        if self.on_notification_failed:
                            self.on_notification_failed(notification)
                        
                        return False
                        
            except Exception as e:
                notification.error = str(e)
                if attempt >= self.max_retries:
                    notification.status = "failed"
                    
                    if self.on_notification_failed:
                        self.on_notification_failed(notification)
                    
                    logger.error(f"Notification {notification.notification_id} failed after retries: {e}")
                    return False
                
                delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                await asyncio.sleep(delay)
        
        return False
    
    async def _persist_notifications(self, notifications: List[Notification]):
        """Persist notifications to database."""
        try:
            async with get_session() as db_session:
                for n in notifications:
                    db_session.add(NotificationModel(
                        notification_id=n.notification_id,
                        channel=n.channel.value,
                        recipient=n.recipient,
                        subject=n.subject,
                        body=n.body,
                        priority=n.priority.value,
                        metadata=json.dumps(n.metadata),
                        status=n.status,
                        error=n.error,
                        retry_count=n.retry_count,
                        created_at=n.created_at,
                        sent_at=n.sent_at
                    ))
                await db_session.commit()
        except Exception as e:
            logger.error(f"Failed to persist notifications: {e}")
    
    async def send_alert(
        self,
        alert_name: str,
        company: str,
        message: str,
        severity: NotificationPriority = NotificationPriority.WARNING,
        channels: Optional[List[NotificationChannel]] = None,
        metadata: Optional[Dict] = None
    ):
        """Send a formatted alert notification."""
        default_channels = [
            NotificationChannel.CONSOLE,
            NotificationChannel.IN_APP
        ]
        
        if self.settings.email_enabled:
            default_channels.append(NotificationChannel.EMAIL)
        if self.settings.slack_webhook_url:
            default_channels.append(NotificationChannel.SLACK)
        if self.settings.discord_webhook_url:
            default_channels.append(NotificationChannel.DISCORD)
        
        await self.send(
            subject=f"🚨 Alert: {alert_name} - {company}",
            body=message,
            channels=channels or default_channels,
            priority=severity,
            metadata={
                "alert_name": alert_name,
                "company": company,
                **(metadata or {})
            }
        )
    
    def get_history(
        self,
        channel: Optional[NotificationChannel] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Notification]:
        """Get notification history."""
        history = self.notification_history
        
        if channel:
            history = [n for n in history if n.channel == channel]
        if status:
            history = [n for n in history if n.status == status]
        
        return sorted(history, key=lambda n: n.created_at, reverse=True)[:limit]
    
    def get_failed_notifications(self, limit: int = 50) -> List[Notification]:
        """Get failed notifications for retry."""
        return [
            n for n in self.notification_history
            if n.status == "failed" and n.retry_count < self.max_retries
        ][:limit]


# Database models
from sqlalchemy import Column, String, Text, DateTime, Integer, Enum as SQLEnum
from database.connection import Base


class NotificationModel(Base):
    __tablename__ = "notifications"
    
    notification_id = Column(String(64), primary_key=True)
    channel = Column(String(32), nullable=False)
    recipient = Column(String(256), nullable=False)
    subject = Column(String(512), nullable=False)
    body = Column(Text, nullable=False)
    priority = Column(String(32), nullable=False)
    metadata = Column(Text, nullable=True)  # JSON
    status = Column(String(32), default="pending")
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    sent_at = Column(DateTime, nullable=True)


# Global instance
_notification_engine: Optional[NotificationEngine] = None


def get_notification_engine() -> NotificationEngine:
    """Get global notification engine instance."""
    global _notification_engine
    if _notification_engine is None:
        _notification_engine = NotificationEngine()
    return _notification_engine