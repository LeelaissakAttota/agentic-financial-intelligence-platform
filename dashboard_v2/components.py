"""
Dashboard Components
Reusable UI components for the Enterprise Dashboard v2.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ComponentType(str, Enum):
    """Types of dashboard components."""
    CHART = "chart"
    TABLE = "table"
    METRIC_CARD = "metric_card"
    ALERT_PANEL = "alert_panel"
    AGENT_STATUS = "agent_status"
    WORKFLOW_VIZ = "workflow_viz"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    RESEARCH_WORKSPACE = "research_workspace"
    REALTIME_FEED = "realtime_feed"
    HEATMAP = "heatmap"
    GAUGE = "gauge"
    TREE_MAP = "tree_map"
    NETWORK_GRAPH = "network_graph"


class ChartType(str, Enum):
    """Chart types for visualization."""
    LINE = "line"
    AREA = "area"
    BAR = "bar"
    HORIZONTAL_BAR = "horizontal_bar"
    SCATTER = "scatter"
    CANDLESTICK = "candlestick"
    OHLC = "ohlc"
    HEATMAP = "heatmap"
    TREEMAP = "treemap"
    SUNBURST = "sunburst"
    SANKEY = "sankey"
    NETWORK = "network"
    GAUGE = "gauge"
    BULLET = "bullet"
    WATERFALL = "waterfall"
    FUNNEL = "funnel"


@dataclass
class ComponentConfig:
    """Configuration for a dashboard component."""
    component_id: str
    component_type: ComponentType
    title: str
    position: Dict[str, int]  # x, y, width, height
    data_source: str
    refresh_interval: int = 30  # seconds
    chart_type: Optional[ChartType] = None
    options: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    interactions: List[str] = field(default_factory=list)
    visible: bool = True
    priority: int = 0


@dataclass
class ComponentData:
    """Data payload for a component."""
    component_id: str
    timestamp: datetime
    data: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    cache_ttl: int = 30


class DashboardComponent:
    """Base class for dashboard components."""
    
    def __init__(self, config: ComponentConfig):
        self.config = config
        self._data: Optional[ComponentData] = None
        self._last_update: Optional[datetime] = None
        self._callbacks: List[Callable] = []
    
    async def fetch_data(self) -> ComponentData:
        """Fetch data for the component. Override in subclasses."""
        return ComponentData(
            component_id=self.config.component_id,
            timestamp=datetime.utcnow(),
            data={}
        )
    
    async def update(self) -> None:
        """Update component data."""
        try:
            data = await self.fetch_data()
            self._data = data
            self._last_update = datetime.utcnow()
            
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    await callback(data)
                except Exception as e:
                    logger.error(f"Callback error for {self.config.component_id}: {e}")
        except Exception as e:
            logger.error(f"Error updating component {self.config.component_id}: {e}")
    
    def register_callback(self, callback: Callable) -> None:
        """Register a data update callback."""
        self._callbacks.append(callback)
    
    def get_data(self) -> Optional[ComponentData]:
        """Get current component data."""
        return self._data
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize component to dictionary."""
        return {
            "config": {
                "component_id": self.config.component_id,
                "component_type": self.config.component_type.value,
                "title": self.config.title,
                "position": self.config.position,
                "data_source": self.config.data_source,
                "refresh_interval": self.config.refresh_interval,
                "chart_type": self.config.chart_type.value if self.config.chart_type else None,
                "options": self.config.options,
                "filters": self.config.filters,
                "interactions": self.config.interactions,
                "visible": self.config.visible,
                "priority": self.config.priority
            },
            "data": self._data.data if self._data else None,
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "metadata": self._data.metadata if self._data else {}
        }


class MetricCardComponent(DashboardComponent):
    """Metric card component for KPIs."""
    
    async def fetch_data(self) -> ComponentData:
        # Would fetch from actual data source
        return ComponentData(
            component_id=self.config.component_id,
            timestamp=datetime.utcnow(),
            data={
                "value": 0,
                "delta": 0,
                "delta_percent": 0,
                "trend": "neutral",
                "unit": "",
                "format": "number"
            },
            metadata={"source": self.config.data_source}
        )


class ChartComponent(DashboardComponent):
    """Chart component for time series and other visualizations."""
    
    async def fetch_data(self) -> ComponentData:
        return ComponentData(
            component_id=self.config.component_id,
            timestamp=datetime.utcnow(),
            data={
                "series": [],
                "x_axis": [],
                "y_axis": {}
            },
            metadata={"chart_type": self.config.chart_type.value if self.config.chart_type else "line"}
        )


class TableComponent(DashboardComponent):
    """Table component for tabular data."""
    
    async def fetch_data(self) -> ComponentData:
        return ComponentData(
            component_id=self.config.component_id,
            timestamp=datetime.utcnow(),
            data={
                "columns": [],
                "rows": [],
                "pagination": {"page": 1, "page_size": 50, "total": 0},
                "sort": {"column": "", "direction": "asc"}
            },
            metadata={"source": self.config.data_source}
        )


class AlertPanelComponent(DashboardComponent):
    """Alert panel for displaying active alerts."""
    
    async def fetch_data(self) -> ComponentData:
        return ComponentData(
            component_id=self.config.component_id,
            timestamp=datetime.utcnow(),
            data={
                "alerts": [],
                "summary": {
                    "total": 0,
                    "critical": 0,
                    "warning": 0,
                    "info": 0
                }
            },
            metadata={"source": "alert_system"}
        )


class AgentStatusComponent(DashboardComponent):
    """Agent status monitoring component."""
    
    async def fetch_data(self) -> ComponentData:
        return ComponentData(
            component_id=self.config.component_id,
            timestamp=datetime.utcnow(),
            data={
                "agents": [],
                "summary": {
                    "total": 0,
                    "running": 0,
                    "idle": 0,
                    "error": 0
                }
            },
            metadata={"source": "agent_manager"}
        )


class RealtimeFeedComponent(DashboardComponent):
    """Real-time data feed component."""
    
    async def fetch_data(self) -> ComponentData:
        return ComponentData(
            component_id=self.config.component_id,
            timestamp=datetime.utcnow(),
            data={
                "feed_items": [],
                "latest_timestamp": datetime.utcnow().isoformat()
            },
            metadata={"source": "realtime_engine"}
        )


class GaugeComponent(DashboardComponent):
    """Gauge component for single value with thresholds."""
    
    async def fetch_data(self) -> ComponentData:
        return ComponentData(
            component_id=self.config.component_id,
            timestamp=datetime.utcnow(),
            data={
                "value": 0,
                "min": 0,
                "max": 100,
                "thresholds": {
                    "green": [0, 50],
                    "yellow": [50, 80],
                    "red": [80, 100]
                },
                "unit": ""
            },
            metadata={"source": self.config.data_source}
        )


# Component factory
class ComponentFactory:
    """Factory for creating dashboard components."""
    
    _component_types = {
        ComponentType.METRIC_CARD: MetricCardComponent,
        ComponentType.CHART: ChartComponent,
        ComponentType.TABLE: TableComponent,
        ComponentType.ALERT_PANEL: AlertPanelComponent,
        ComponentType.AGENT_STATUS: AgentStatusComponent,
        ComponentType.REALTIME_FEED: RealtimeFeedComponent,
        ComponentType.GAUGE: GaugeComponent,
    }
    
    @classmethod
    def create(cls, config: ComponentConfig) -> DashboardComponent:
        """Create a component from configuration."""
        component_class = cls._component_types.get(config.component_type)
        if not component_class:
            raise ValueError(f"Unknown component type: {config.component_type}")
        return component_class(config)
    
    @classmethod
    def register_type(cls, component_type: ComponentType, component_class: type) -> None:
        """Register a new component type."""
        cls._component_types[component_type] = component_class


# Global component factory instance
_component_factory = ComponentFactory()


def get_component_factory() -> ComponentFactory:
    return _component_factory


def create_component(config: ComponentConfig) -> DashboardComponent:
    """Convenience function to create a component."""
    return _component_factory.create(config)