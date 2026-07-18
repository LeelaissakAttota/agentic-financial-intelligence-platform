"""
Watchlist Manager

Manages user-defined watchlists with companies, alert rules, and real-time monitoring.
"""
import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import logging

from database.connection import get_session
from database.models import Watchlist, WatchlistItem, AlertRule, Alert
from config.settings import get_settings
from agents.research_planner.agent import AgentType


logger = logging.getLogger(__name__)


class WatchlistType(Enum):
    """Types of watchlists."""
    PERSONAL = "personal"
    PORTFOLIO = "portfolio"
    SECTOR = "sector"
    THEMATIC = "thematic"
    COMPETITOR = "competitor"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class WatchlistItemData:
    """Data for a watchlist item."""
    company: str
    ticker: Optional[str] = None
    added_at: datetime = field(default_factory=datetime.now)
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    position_size: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WatchlistData:
    """Complete watchlist data."""
    watchlist_id: str
    name: str
    description: str
    type: WatchlistType
    owner_id: str
    items: List[WatchlistItemData] = field(default_factory=list)
    alert_rules: List["AlertRuleData"] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertRuleData:
    """Alert rule configuration."""
    rule_id: str
    watchlist_id: str
    name: str
    description: str
    company: Optional[str] = None  # None = all companies in watchlist
    conditions: Dict[str, Any] = field(default_factory=dict)
    severity: AlertSeverity = AlertSeverity.WARNING
    channels: List[str] = field(default_factory=list)  # email, slack, webhook, in_app
    cooldown_minutes: int = 60
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0


class WatchlistManager:
    """
    Manages watchlists, items, and alert rules.
    
    Features:
    - Create/manage watchlists
    - Add/remove companies
    - Define alert rules with conditions
    - Real-time monitoring integration
    - Multi-channel notifications
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._watchlists: Dict[str, WatchlistData] = {}
        self._alert_callbacks: List[Callable] = []
    
    async def create_watchlist(
        self,
        name: str,
        description: str,
        type: WatchlistType,
        owner_id: str,
        initial_companies: Optional[List[str]] = None
    ) -> WatchlistData:
        """Create a new watchlist."""
        watchlist = WatchlistData(
            watchlist_id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            type=type,
            owner_id=owner_id
        )
        
        if initial_companies:
            for company in initial_companies:
                watchlist.items.append(WatchlistItemData(company=company))
        
        self._watchlists[watchlist.watchlist_id] = watchlist
        await self._persist_watchlist(watchlist)
        
        logger.info(f"Created watchlist: {watchlist.name} ({watchlist.watchlist_id})")
        return watchlist
    
    async def get_watchlist(self, watchlist_id: str) -> Optional[WatchlistData]:
        """Get watchlist by ID."""
        if watchlist_id in self._watchlists:
            return self._watchlists[watchlist_id]
        
        # Load from database
        return await self._load_watchlist(watchlist_id)
    
    async def list_watchlists(self, owner_id: Optional[str] = None) -> List[WatchlistData]:
        """List all watchlists, optionally filtered by owner."""
        # Ensure loaded
        await self._load_all_watchlists()
        
        if owner_id:
            return [w for w in self._watchlists.values() if w.owner_id == owner_id]
        return list(self._watchlists.values())
    
    async def add_company(
        self,
        watchlist_id: str,
        company: str,
        ticker: Optional[str] = None,
        notes: str = "",
        tags: Optional[List[str]] = None,
        target_price: Optional[float] = None,
        stop_loss: Optional[float] = None
    ) -> bool:
        """Add a company to a watchlist."""
        watchlist = await self.get_watchlist(watchlist_id)
        if not watchlist:
            return False
        
        # Check if already exists
        for item in watchlist.items:
            if item.company.lower() == company.lower():
                return False
        
        item = WatchlistItemData(
            company=company,
            ticker=ticker,
            notes=notes,
            tags=tags or [],
            target_price=target_price,
            stop_loss=stop_loss
        )
        
        watchlist.items.append(item)
        watchlist.updated_at = datetime.now()
        await self._persist_watchlist(watchlist)
        
        logger.info(f"Added {company} to watchlist {watchlist_id}")
        return True
    
    async def remove_company(self, watchlist_id: str, company: str) -> bool:
        """Remove a company from a watchlist."""
        watchlist = await self.get_watchlist(watchlist_id)
        if not watchlist:
            return False
        
        watchlist.items = [
            item for item in watchlist.items
            if item.company.lower() != company.lower()
        ]
        watchlist.updated_at = datetime.now()
        await self._persist_watchlist(watchlist)
        
        return True
    
    async def add_alert_rule(
        self,
        watchlist_id: str,
        name: str,
        description: str,
        conditions: Dict[str, Any],
        severity: AlertSeverity = AlertSeverity.WARNING,
        channels: Optional[List[str]] = None,
        company: Optional[str] = None,
        cooldown_minutes: int = 60
    ) -> AlertRuleData:
        """Add an alert rule to a watchlist."""
        watchlist = await self.get_watchlist(watchlist_id)
        if not watchlist:
            raise ValueError(f"Watchlist not found: {watchlist_id}")
        
        rule = AlertRuleData(
            rule_id=str(uuid.uuid4())[:8],
            watchlist_id=watchlist_id,
            name=name,
            description=description,
            company=company,
            conditions=conditions,
            severity=severity,
            channels=channels or ["in_app"],
            cooldown_minutes=cooldown_minutes
        )
        
        watchlist.alert_rules.append(rule)
        watchlist.updated_at = datetime.now()
        await self._persist_watchlist(watchlist)
        
        logger.info(f"Added alert rule: {rule.name} to watchlist {watchlist_id}")
        return rule
    
    async def evaluate_alerts(
        self,
        watchlist_id: str,
        market_data: Dict[str, Any],
        news_data: Optional[List[Dict]] = None,
        agent_outputs: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Evaluate all alert rules against current data."""
        watchlist = await self.get_watchlist(watchlist_id)
        if not watchlist:
            return []
        
        triggered = []
        
        for rule in watchlist.alert_rules:
            if not rule.is_active:
                continue
            
            # Check cooldown
            if rule.last_triggered:
                elapsed = (datetime.now() - rule.last_triggered).total_seconds() / 60
                if elapsed < rule.cooldown_minutes:
                    continue
            
            # Determine which companies to check
            companies_to_check = []
            if rule.company:
                companies_to_check = [rule.company]
            else:
                companies_to_check = [item.company for item in watchlist.items]
            
            for company in companies_to_check:
                company_data = market_data.get(company, {})
                
                # Evaluate conditions
                if self._evaluate_conditions(rule.conditions, company_data, news_data, agent_outputs):
                    alert = {
                        "alert_id": str(uuid.uuid4())[:8],
                        "rule_id": rule.rule_id,
                        "watchlist_id": watchlist_id,
                        "company": company,
                        "name": rule.name,
                        "description": rule.description,
                        "severity": rule.severity.value,
                        "triggered_at": datetime.now().isoformat(),
                        "data": company_data,
                        "channels": rule.channels
                    }
                    triggered.append(alert)
                    
                    # Update rule stats
                    rule.last_triggered = datetime.now()
                    rule.trigger_count += 1
        
        if triggered:
            watchlist.updated_at = datetime.now()
            await self._persist_watchlist(watchlist)
            
            # Notify callbacks
            for alert in triggered:
                for callback in self._alert_callbacks:
                    try:
                        await callback(alert)
                    except Exception as e:
                        logger.error(f"Alert callback failed: {e}")
        
        return triggered
    
    def _evaluate_conditions(
        self,
        conditions: Dict[str, Any],
        market_data: Dict[str, Any],
        news_data: Optional[List[Dict]],
        agent_outputs: Optional[Dict[str, Any]]
    ) -> bool:
        """Evaluate alert conditions against data."""
        for condition_type, condition_value in conditions.items():
            if condition_type == "price_above":
                if market_data.get("current_price", 0) <= condition_value:
                    return False
            elif condition_type == "price_below":
                if market_data.get("current_price", 0) >= condition_value:
                    return False
            elif condition_type == "price_change_pct":
                change = market_data.get("price_change_pct", 0)
                if abs(change) < condition_value:
                    return False
            elif condition_type == "volume_spike":
                volume_ratio = market_data.get("volume", 0) / max(market_data.get("avg_volume", 1), 1)
                if volume_ratio < condition_value:
                    return False
            elif condition_type == "rsi_above":
                if market_data.get("rsi", 50) <= condition_value:
                    return False
            elif condition_type == "rsi_below":
                if market_data.get("rsi", 50) >= condition_value:
                    return False
            elif condition_type == "news_sentiment":
                if news_data:
                    avg_sentiment = sum(n.get("sentiment", 0) for n in news_data) / len(news_data)
                    if avg_sentiment < condition_value:
                        return False
            elif condition_type == "news_count":
                if news_data and len(news_data) < condition_value:
                    return False
            elif condition_type == "agent_signal":
                # Check specific agent output
                agent_name = condition_value.get("agent")
                signal = condition_value.get("signal")
                if agent_outputs and agent_name in agent_outputs:
                    agent_data = agent_outputs[agent_name]
                    if agent_data.get("signal") != signal:
                        return False
                else:
                    return False
            elif condition_type == "custom":
                # Custom lambda/eval condition
                pass
        
        return True
    
    def register_alert_callback(self, callback: Callable[[Dict], None]):
        """Register callback for alert notifications."""
        self._alert_callbacks.append(callback)
    
    async def _persist_watchlist(self, watchlist: WatchlistData):
        """Persist watchlist to database."""
        async with get_session() as db_session:
            # Upsert watchlist
            db_watchlist = await db_session.get(Watchlist, watchlist.watchlist_id)
            if not db_watchlist:
                db_watchlist = Watchlist(watchlist_id=watchlist.watchlist_id)
                db_session.add(db_watchlist)
            
            db_watchlist.name = watchlist.name
            db_watchlist.description = watchlist.description
            db_watchlist.type = watchlist.type.value
            db_watchlist.owner_id = watchlist.owner_id
            db_watchlist.is_active = watchlist.is_active
            db_watchlist.created_at = watchlist.created_at
            db_watchlist.updated_at = watchlist.updated_at
            db_watchlist.metadata = watchlist.metadata
            
            # Sync items
            existing_items = {item.company: item for item in db_watchlist.items}
            new_items = {item.company: item for item in watchlist.items}
            
            # Remove deleted
            for company in set(existing_items) - set(new_items):
                await db_session.delete(existing_items[company])
            
            # Update or add
            for company, item in new_items.items():
                if company in existing_items:
                    db_item = existing_items[company]
                else:
                    db_item = WatchlistItem(company=company)
                    db_watchlist.items.append(db_item)
                
                db_item.ticker = item.ticker
                db_item.notes = item.notes
                db_item.tags = item.tags
                db_item.target_price = item.target_price
                db_item.stop_loss = item.stop_loss
                db_item.position_size = item.position_size
                db_item.metadata = item.metadata
            
            # Sync alert rules
            existing_rules = {rule.rule_id: rule for rule in db_watchlist.alert_rules}
            new_rules = {rule.rule_id: rule for rule in watchlist.alert_rules}
            
            for rule_id in set(existing_rules) - set(new_rules):
                await db_session.delete(existing_rules[rule_id])
            
            for rule_id, rule in new_rules.items():
                if rule_id in existing_rules:
                    db_rule = existing_rules[rule_id]
                else:
                    db_rule = AlertRule(rule_id=rule_id)
                    db_watchlist.alert_rules.append(db_rule)
                
                db_rule.name = rule.name
                db_rule.description = rule.description
                db_rule.company = rule.company
                db_rule.conditions = rule.conditions
                db_rule.severity = rule.severity.value
                db_rule.channels = rule.channels
                db_rule.cooldown_minutes = rule.cooldown_minutes
                db_rule.is_active = rule.is_active
                db_rule.last_triggered = rule.last_triggered
                db_rule.trigger_count = rule.trigger_count
            
            await db_session.commit()
    
    async def _load_watchlist(self, watchlist_id: str) -> Optional[WatchlistData]:
        """Load watchlist from database."""
        async with get_session() as db_session:
            result = await db_session.execute(
                select(Watchlist).where(Watchlist.watchlist_id == watchlist_id)
            )
            db_watchlist = result.scalar_one_or_none()
            
            if not db_watchlist:
                return None
            
            watchlist = WatchlistData(
                watchlist_id=db_watchlist.watchlist_id,
                name=db_watchlist.name,
                description=db_watchlist.description,
                type=WatchlistType(db_watchlist.type),
                owner_id=db_watchlist.owner_id,
                is_active=db_watchlist.is_active,
                created_at=db_watchlist.created_at,
                updated_at=db_watchlist.updated_at,
                metadata=db_watchlist.metadata or {}
            )
            
            # Load items
            for db_item in db_watchlist.items:
                watchlist.items.append(WatchlistItemData(
                    company=db_item.company,
                    ticker=db_item.ticker,
                    notes=db_item.notes,
                    tags=db_item.tags or [],
                    target_price=db_item.target_price,
                    stop_loss=db_item.stop_loss,
                    position_size=db_item.position_size,
                    metadata=db_item.metadata or {}
                ))
            
            # Load alert rules
            for db_rule in db_watchlist.alert_rules:
                watchlist.alert_rules.append(AlertRuleData(
                    rule_id=db_rule.rule_id,
                    watchlist_id=db_rule.watchlist_id,
                    name=db_rule.name,
                    description=db_rule.description,
                    company=db_rule.company,
                    conditions=db_rule.conditions or {},
                    severity=AlertSeverity(db_rule.severity),
                    channels=db_rule.channels or [],
                    cooldown_minutes=db_rule.cooldown_minutes,
                    is_active=db_rule.is_active,
                    last_triggered=db_rule.last_triggered,
                    trigger_count=db_rule.trigger_count
                ))
            
            self._watchlists[watchlist_id] = watchlist
            return watchlist
    
    async def _load_all_watchlists(self):
        """Load all watchlists into cache."""
        async with get_session() as db_session:
            result = await db_session.execute(select(Watchlist))
            for db_watchlist in result.scalars():
                if db_watchlist.watchlist_id not in self._watchlists:
                    await self._load_watchlist(db_watchlist.watchlist_id)


# Global instance
_watchlist_manager: Optional[WatchlistManager] = None


def get_watchlist_manager() -> WatchlistManager:
    """Get global watchlist manager."""
    global _watchlist_manager
    if _watchlist_manager is None:
        _watchlist_manager = WatchlistManager()
    return _watchlist_manager