"""
Enterprise Dashboard v2
Real-time, interactive dashboard with live agent monitoring, knowledge graph explorer,
research workspace, and live workflow visualization.
"""

from .components import DashboardComponents, get_dashboard_components
from .layout import DashboardLayout, get_dashboard_layout
from .realtime import RealtimeDashboard, get_realtime_dashboard
from .workspace import ResearchWorkspace, get_research_workspace
from .graph_explorer import GraphExplorer, get_graph_explorer
from .workflow_viz import WorkflowVisualization, get_workflow_visualization

__all__ = [
    "DashboardComponents",
    "get_dashboard_components",
    "DashboardLayout",
    "get_dashboard_layout",
    "RealtimeDashboard",
    "get_realtime_dashboard",
    "ResearchWorkspace",
    "get_research_workspace",
    "GraphExplorer",
    "get_graph_explorer",
    "WorkflowVisualization",
    "get_workflow_visualization",
]

__version__ = "1.0.0-phase9"