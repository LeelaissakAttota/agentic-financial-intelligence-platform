"""
Dashboard Layout
Layout management for the Enterprise Dashboard v2 with responsive grid system.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)


class LayoutType(str, Enum):
    """Dashboard layout types."""
    GRID = "grid"
    FLEX = "flex"
    MASONRY = "masonry"
    FIXED = "fixed"


class Breakpoint(str, Enum):
    """Responsive breakpoints."""
    XS = "xs"      # < 600px
    SM = "sm"      # 600-960px
    MD = "md"      # 960-1280px
    LG = "lg"      # 1280-1920px
    XL = "xl"      # > 1920px


@dataclass
class GridPosition:
    """Position in grid layout."""
    x: int
    y: int
    width: int
    height: int
    min_width: int = 1
    min_height: int = 1
    max_width: Optional[int] = None
    max_height: Optional[int] = None


@dataclass
class ResponsivePosition:
    """Responsive position for different breakpoints."""
    base: GridPosition
    overrides: Dict[str, GridPosition] = field(default_factory=dict)  # breakpoint -> position


@dataclass
class LayoutConfig:
    """Dashboard layout configuration."""
    layout_type: LayoutType = LayoutType.GRID
    columns: int = 12
    row_height: int = 50  # pixels
    margin: int = 10  # pixels
    container_padding: int = 20
    breakpoints: Dict[str, int] = field(default_factory=lambda: {
        "xs": 0,
        "sm": 600,
        "md": 960,
        "lg": 1280,
        "xl": 1920
    })
    compact_type: str = "vertical"  # vertical, horizontal, none
    prevent_collision: bool = True
    auto_size: bool = True
    maintain_aspect_ratio: bool = False


@dataclass
class LayoutItem:
    """Item in the layout."""
    component_id: str
    position: ResponsivePosition
    static: bool = False  # Cannot be moved/resized
    is_draggable: bool = True
    is_resizable: bool = True
    min_width: int = 1
    min_height: int = 1
    max_width: Optional[int] = None
    max_height: Optional[int] = None


class DashboardLayout:
    """
    Dashboard layout manager with responsive grid system.
    Supports drag-and-drop, resizing, and responsive breakpoints.
    """
    
    def __init__(self, config: Optional[LayoutConfig] = None):
        self.config = config or LayoutConfig()
        self._items: Dict[str, LayoutItem] = {}
        self._layout_history: List[Dict[str, Any]] = []
        self._current_breakpoint: Breakpoint = Breakpoint.LG
        self._container_width: int = 1920
        self._callbacks: List[callable] = []
    
    def set_container_width(self, width: int) -> None:
        """Set container width and update breakpoint."""
        self._container_width = width
        new_breakpoint = self._calculate_breakpoint(width)
        if new_breakpoint != self._current_breakpoint:
            self._current_breakpoint = new_breakpoint
            self._apply_breakpoint()
            logger.info(f"Breakpoint changed to: {new_breakpoint.value}")
    
    def _calculate_breakpoint(self, width: int) -> Breakpoint:
        """Calculate breakpoint from width."""
        if width >= self.config.breakpoints.get("xl", 1920):
            return Breakpoint.XL
        elif width >= self.config.breakpoints.get("lg", 1280):
            return Breakpoint.LG
        elif width >= self.config.breakpoints.get("md", 960):
            return Breakpoint.MD
        elif width >= self.config.breakpoints.get("sm", 600):
            return Breakpoint.SM
        return Breakpoint.XS
    
    def _apply_breakpoint(self) -> None:
        """Apply responsive positions for current breakpoint."""
        for item in self._items.values():
            pos = item.position.overrides.get(self._current_breakpoint.value)
            if pos:
                item.position.base = pos
    
    def add_item(self, item: LayoutItem) -> bool:
        """Add a layout item."""
        if item.component_id in self._items:
            logger.warning(f"Item {item.component_id} already exists")
            return False
        
        # Check for collisions
        if self.config.prevent_collision:
            if self._check_collision(item):
                logger.warning(f"Collision detected for {item.component_id}")
                # Try to find free position
                item.position = self._find_free_position(item)
        
        self._items[item.component_id] = item
        self._record_layout_change("add", item.component_id)
        self._notify_change()
        return True
    
    def remove_item(self, component_id: str) -> bool:
        """Remove a layout item."""
        if component_id not in self._items:
            return False
        
        del self._items[component_id]
        self._record_layout_change("remove", component_id)
        self._notify_change()
        return True
    
    def update_item_position(self, component_id: str, position: GridPosition) -> bool:
        """Update item position."""
        if component_id not in self._items:
            return False
        
        item = self._items[component_id]
        
        if item.static:
            logger.warning(f"Cannot move static item {component_id}")
            return False
        
        # Validate position
        if not self._validate_position(position):
            return False
        
        # Check collision
        if self.config.prevent_collision:
            temp_pos = item.position.base
            item.position.base = position
            if self._check_collision(item, exclude_id=component_id):
                item.position.base = temp_pos
                return False
            item.position.base = temp_pos
        
        # Update position
        item.position.base = position
        self._record_layout_change("move", component_id, position)
        self._notify_change()
        return True
    
    def update_item_size(self, component_id: str, width: int, height: int) -> bool:
        """Update item size."""
        if component_id not in self._items:
            return False
        
        item = self._items[component_id]
        
        if item.static:
            return False
        
        # Validate size
        if width < item.min_width or height < item.min_height:
            return False
        if item.max_width and width > item.max_width:
            return False
        if item.max_height and height > item.max_height:
            return False
        
        new_pos = GridPosition(
            x=item.position.base.x,
            y=item.position.base.y,
            width=width,
            height=height
        )
        
        return self.update_item_position(component_id, new_pos)
    
    def _validate_position(self, position: GridPosition) -> bool:
        """Validate grid position."""
        if position.x < 0 or position.y < 0:
            return False
        if position.x + position.width > self.config.columns:
            return False
        if position.width < 1 or position.height < 1:
            return False
        return True
    
    def _check_collision(self, item: LayoutItem, exclude_id: Optional[str] = None) -> bool:
        """Check if item collides with others."""
        pos = item.position.base
        item_rect = {
            "x1": pos.x,
            "y1": pos.y,
            "x2": pos.x + pos.width,
            "y2": pos.y + pos.height
        }
        
        for other_id, other_item in self._items.items():
            if other_id == exclude_id or other_id == item.component_id:
                continue
            
            other_pos = other_item.position.base
            other_rect = {
                "x1": other_pos.x,
                "y1": other_pos.y,
                "x2": other_pos.x + other_pos.width,
                "y2": other_pos.y + other_pos.height
            }
            
            # Check overlap
            if not (item_rect["x2"] <= other_rect["x1"] or
                    item_rect["x1"] >= other_rect["x2"] or
                    item_rect["y2"] <= other_rect["y1"] or
                    item_rect["y1"] >= other_rect["y2"]):
                return True
        
        return False
    
    def _find_free_position(self, item: LayoutItem) -> ResponsivePosition:
        """Find a free position for an item."""
        pos = item.position.base
        width = pos.width
        height = pos.height
        
        # Try positions from top-left
        for y in range(self._get_max_y() + 1):
            for x in range(self.config.columns - width + 1):
                test_pos = GridPosition(x=x, y=y, width=width, height=height)
                test_item = LayoutItem(
                    component_id="test",
                    position=ResponsivePosition(base=test_pos),
                    min_width=width,
                    min_height=height
                )
                
                if not self._check_collision(test_item):
                    return ResponsivePosition(base=test_pos)
        
        # Fallback: place below everything
        max_y = self._get_max_y()
        return ResponsivePosition(base=GridPosition(x=0, y=max_y + 1, width=width, height=height))
    
    def _get_max_y(self) -> int:
        """Get maximum y coordinate of all items."""
        max_y = 0
        for item in self._items.values():
            pos = item.position.base
            max_y = max(max_y, pos.y + pos.height)
        return max_y
    
    def compact_layout(self, direction: str = "vertical") -> None:
        """Compact layout by removing gaps."""
        if direction == "vertical":
            self._compact_vertical()
        elif direction == "horizontal":
            self._compact_horizontal()
    
    def _compact_vertical(self) -> None:
        """Compact layout vertically."""
        # Sort items by y position
        sorted_items = sorted(
            self._items.values(),
            key=lambda item: (item.position.base.y, item.position.base.x)
        )
        
        for item in sorted_items:
            if item.static:
                continue
            
            # Try to move item up as far as possible
            current_y = item.position.base.y
            new_y = 0
            
            for test_y in range(current_y):
                test_pos = GridPosition(
                    x=item.position.base.x,
                    y=test_y,
                    width=item.position.base.width,
                    height=item.position.base.height
                )
                
                test_item = LayoutItem(
                    component_id="test",
                    position=ResponsivePosition(base=test_pos),
                    min_width=item.position.base.width,
                    min_height=item.position.base.height
                )
                
                if not self._check_collision(test_item):
                    new_y = test_y
                else:
                    break
            
            if new_y < current_y:
                new_pos = GridPosition(
                    x=item.position.base.x,
                    y=new_y,
                    width=item.position.base.width,
                    height=item.position.base.height
                )
                item.position.base = new_pos
    
    def _compact_horizontal(self) -> None:
        """Compact layout horizontally."""
        # Similar to vertical but for x-axis
        pass
    
    def auto_arrange(self, algorithm: str = "pack") -> None:
        """Automatically arrange items."""
        if algorithm == "pack":
            self._pack_algorithm()
        elif algorithm == "grid":
            self._grid_algorithm()
    
    def _pack_algorithm(self) -> None:
        """Pack items tightly using bin packing."""
        # Sort by area (largest first)
        sorted_items = sorted(
            [item for item in self._items.values() if not item.static],
            key=lambda i: i.position.base.width * i.position.base.height,
            reverse=True
        )
        
        for item in sorted_items:
            item.position = self._find_free_position(item)
    
    def _grid_algorithm(self) -> None:
        """Arrange items in a regular grid."""
        items = [item for item in self._items.values() if not item.static]
        if not items:
            return
        
        # Calculate grid dimensions
        n = len(items)
        cols = int(np.ceil(np.sqrt(n)))
        rows = int(np.ceil(n / cols))
        
        item_width = max(1, self.config.columns // cols)
        item_height = max(1, 10)  # Default row height
        
        for i, item in enumerate(items):
            col = i % cols
            row = i // cols
            new_pos = GridPosition(
                x=col * item_width,
                y=row * item_height,
                width=item_width,
                height=item_height
            )
            item.position.base = new_pos
    
    def get_layout(self, breakpoint: Optional[Breakpoint] = None) -> Dict[str, Any]:
        """Get layout as dictionary."""
        bp = breakpoint or self._current_breakpoint
        
        layout = []
        for item in self._items.values():
            pos = item.position.overrides.get(bp.value, item.position.base)
            layout.append({
                "component_id": item.component_id,
                "x": pos.x,
                "y": pos.y,
                "w": pos.width,
                "h": pos.height,
                "static": item.static,
                "draggable": item.is_draggable,
                "resizable": item.is_resizable,
                "minW": item.min_width,
                "minH": item.min_height,
                "maxW": item.max_width,
                "maxH": item.max_height
            })
        
        return {
            "layout": layout,
            "config": {
                "columns": self.config.columns,
                "rowHeight": self.config.row_height,
                "margin": self.config.margin,
                "containerPadding": self.config.container_padding,
                "breakpoints": self.config.breakpoints,
                "compactType": self.config.compact_type,
                "currentBreakpoint": self._current_breakpoint.value
            }
        }
    
    def load_layout(self, layout_data: Dict[str, Any]) -> None:
        """Load layout from dictionary."""
        self._items.clear()
        
        for item_data in layout_data.get("layout", []):
            pos = GridPosition(
                x=item_data["x"],
                y=item_data["y"],
                width=item_data["w"],
                height=item_data["h"]
            )
            
            item = LayoutItem(
                component_id=item_data["component_id"],
                position=ResponsivePosition(base=pos),
                static=item_data.get("static", False),
                is_draggable=item_data.get("draggable", True),
                is_resizable=item_data.get("resizable", True),
                min_width=item_data.get("minW", 1),
                min_height=item_data.get("minH", 1),
                max_width=item_data.get("maxW"),
                max_height=item_data.get("maxH")
            )
            
            self._items[item.component_id] = item
        
        # Load config if present
        if "config" in layout_data:
            cfg = layout_data["config"]
            self.config.columns = cfg.get("columns", self.config.columns)
            self.config.row_height = cfg.get("rowHeight", self.config.row_height)
            self.config.margin = cfg.get("margin", self.config.margin)
            self.config.container_padding = cfg.get("containerPadding", self.config.container_padding)
            if "currentBreakpoint" in cfg:
                self._current_breakpoint = Breakpoint(cfg["currentBreakpoint"])
    
    def export_layout(self) -> str:
        """Export layout as JSON string."""
        return json.dumps(self.get_layout(), indent=2)
    
    def import_layout(self, json_str: str) -> bool:
        """Import layout from JSON string."""
        try:
            data = json.loads(json_str)
            self.load_layout(data)
            return True
        except Exception as e:
            logger.error(f"Failed to import layout: {e}")
            return False
    
    def register_callback(self, callback: callable) -> None:
        """Register layout change callback."""
        self._callbacks.append(callback)
    
    def _notify_change(self) -> None:
        """Notify callbacks of layout change."""
        layout = self.get_layout()
        for callback in self._callbacks:
            try:
                callback(layout)
            except Exception as e:
                logger.error(f"Layout callback error: {e}")
    
    def _record_layout_change(self, action: str, component_id: str, position: Optional[GridPosition] = None) -> None:
        """Record layout change for history/undo."""
        self._layout_history.append({
            "action": action,
            "component_id": component_id,
            "position": {
                "x": position.x,
                "y": position.y,
                "w": position.width,
                "h": position.height
            } if position else None,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep last 100 changes
        if len(self._layout_history) > 100:
            self._layout_history = self._layout_history[-100:]
    
    def undo(self) -> bool:
        """Undo last layout change."""
        if not self._layout_history:
            return False
        
        last = self._layout_history.pop()
        
        if last["action"] == "add":
            self.remove_item(last["component_id"])
        elif last["action"] == "remove":
            # Would need to store full item data for proper undo
            pass
        elif last["action"] == "move" and last["position"]:
            pos = GridPosition(**last["position"])
            self.update_item_position(last["component_id"], pos)
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_items": len(self._items),
            "static_items": sum(1 for i in self._items.values() if i.static),
            "current_breakpoint": self._current_breakpoint.value,
            "container_width": self._container_width,
            "max_y": self._get_max_y(),
            "layout_changes": len(self._layout_history)
        }


# Global layout instance
_dashboard_layout: Optional[DashboardLayout] = None


def get_dashboard_layout(config: Optional[LayoutConfig] = None) -> DashboardLayout:
    global _dashboard_layout
    if _dashboard_layout is None:
        _dashboard_layout = DashboardLayout(config)
    return _dashboard_layout


async def close_dashboard_layout() -> None:
    global _dashboard_layout
    if _dashboard_layout:
        _dashboard_layout = None