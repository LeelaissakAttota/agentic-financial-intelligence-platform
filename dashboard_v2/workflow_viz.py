"""
Workflow Visualization
Live workflow visualization for the Enterprise Dashboard v2.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class StepStatus(str, Enum):
    """Individual step status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class WorkflowStep:
    """Single step in a workflow."""
    step_id: str
    name: str
    description: str = ""
    agent_type: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: float = 300.0
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowExecution:
    """Workflow execution instance."""
    execution_id: str
    workflow_id: str
    name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    steps: Dict[str, WorkflowStep] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step: Optional[str] = None
    progress: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowDefinition:
    """Workflow template definition."""
    workflow_id: str
    name: str
    description: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowVisualization:
    """
    Live workflow visualization for real-time monitoring.
    Provides:
    - DAG visualization of workflow steps
    - Real-time progress updates
    - Step-level detail drill-down
    - Execution history
    - Bottleneck identification
    """
    
    def __init__(self):
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._executions: Dict[str, WorkflowExecution] = {}
        self._active_executions: Dict[str, asyncio.Task] = {}
        self._callbacks: List[Callable] = []
    
    def register_workflow(self, workflow: WorkflowDefinition) -> None:
        """Register a workflow definition."""
        self._workflows[workflow.workflow_id] = workflow
        logger.info(f"Registered workflow: {workflow.workflow_id} ({workflow.name})")
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get workflow definition by ID."""
        return self._workflows.get(workflow_id)
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all registered workflows."""
        return [
            {
                "workflow_id": w.workflow_id,
                "name": w.name,
                "description": w.description,
                "version": w.version,
                "step_count": len(w.steps),
                "tags": w.tags
            }
            for w in self._workflows.values()
        ]
    
    async def start_execution(
        self,
        workflow_id: str,
        context: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Start a new workflow execution."""
        
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            logger.error(f"Workflow not found: {workflow_id}")
            return None
        
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        
        # Create execution instance
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            name=workflow.name,
            context=context or {},
            metadata=parameters or {}
        )
        
        # Initialize steps from workflow definition
        for step_def in workflow.steps:
            execution.steps[step_def.step_id] = WorkflowStep(
                step_id=step_def.step_id,
                name=step_def.name,
                description=step_def.description,
                agent_type=step_def.agent_type,
                dependencies=list(step_def.dependencies),
                parameters=step_def.parameters,
                max_retries=step_def.max_retries,
                timeout=step_def.timeout,
                metadata=step_def.metadata
            )
        
        self._executions[execution_id] = execution
        
        # Start execution
        task = asyncio.create_task(self._run_execution(execution))
        self._active_executions[execution_id] = task
        
        logger.info(f"Started workflow execution: {execution_id} ({workflow_id})")
        return execution_id
    
    async def _run_execution(self, execution: WorkflowExecution) -> None:
        """Run workflow execution with dependency resolution."""
        
        execution.status = WorkflowStatus.RUNNING
        execution.started_at = datetime.utcnow()
        await self._notify_callbacks("started", execution)
        
        try:
            # Build dependency graph
            step_graph = {step_id: set(step.dependencies) for step_id, step in execution.steps.items()}
            completed = set()
            running = set()
            
            while True:
                # Find ready steps
                ready = []
                for step_id, step in execution.steps.items():
                    if step.status != StepStatus.PENDING:
                        continue
                    if all(dep in completed for dep in step.dependencies):
                        ready.append(step_id)
                
                if not ready and not running:
                    break  # All done or deadlock
                
                if not ready:
                    # Wait for running steps
                    await asyncio.sleep(0.5)
                    continue
                
                # Start ready steps
                for step_id in ready:
                    step = execution.steps[step_id]
                    running.add(step_id)
                    execution.current_step = step_id
                    asyncio.create_task(self._run_step(execution, step))
                
                # Wait for at least one to complete
                while running:
                    await asyncio.sleep(0.5)
                    still_running = set()
                    for step_id in running:
                        step = execution.steps[step_id]
                        if step.status in [StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED]:
                            running.remove(step_id)
                            if step.status == StepStatus.COMPLETED:
                                completed.add(step_id)
                        else:
                            still_running.add(step_id)
                    running = still_running
                
                # Update progress
                execution.progress = len(completed) / len(execution.steps) if execution.steps else 1.0
                await self._notify_callbacks("progress", execution)
            
            # Check final status
            failed_steps = [s for s in execution.steps.values() if s.status == StepStatus.FAILED]
            if failed_steps:
                execution.status = WorkflowStatus.FAILED
            else:
                execution.status = WorkflowStatus.COMPLETED
            
            execution.completed_at = datetime.utcnow()
            execution.progress = 1.0
            await self._notify_callbacks("completed", execution)
            
        except asyncio.CancelledError:
            execution.status = WorkflowStatus.CANCELLED
            execution.completed_at = datetime.utcnow()
            raise
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.completed_at = datetime.utcnow()
            logger.error(f"Execution failed: {e}")
        finally:
            await self._notify_callbacks("completed", execution)
            self._active_executions.pop(execution.execution_id, None)
    
    async def _run_step(self, execution: WorkflowExecution, step: WorkflowStep) -> None:
        """Execute a single workflow step."""
        
        step.status = StepStatus.RUNNING
        step.started_at = datetime.utcnow()
        
        try:
            # In production, would call actual agent
            # For now, simulate work
            await asyncio.sleep(0.1)  # Simulate work
            
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.utcnow()
            step.result = {"status": "success", "output": f"Step {step.name} completed"}
            
        except asyncio.CancelledError:
            step.status = StepStatus.FAILED
            step.error = "Cancelled"
            raise
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            step.retry_count += 1
            
            if step.retry_count < step.max_retries:
                step.status = StepStatus.RETRYING
                await asyncio.sleep(2 ** step.retry_count)  # Exponential backoff
                # Would retry here
            else:
                step.completed_at = datetime.utcnow()
    
    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get execution by ID."""
        return self._executions.get(execution_id)
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution status for visualization."""
        
        execution = self._executions.get(execution_id)
        if not execution:
            return None
        
        return {
            "execution_id": execution.execution_id,
            "workflow_id": execution.workflow_id,
            "name": execution.name,
            "status": execution.status.value,
            "progress": execution.progress,
            "current_step": execution.current_step,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "steps": {
                step_id: {
                    "step_id": step.step_id,
                    "name": step.name,
                    "status": step.status.value,
                    "progress": step.progress,
                    "started_at": step.started_at.isoformat() if step.started_at else None,
                    "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                    "error": step.error,
                    "retry_count": step.retry_count
                }
                for step_id, step in execution.steps.items()
            }
        }
    
    def get_execution_dag(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get DAG representation for visualization."""
        
        execution = self._executions.get(execution_id)
        if not execution:
            return None
        
        nodes = []
        edges = []
        
        for step_id, step in execution.steps.items():
            nodes.append({
                "id": step.step_id,
                "label": step.name,
                "status": step.status.value,
                "agent_type": step.agent_type,
                "progress": step.progress
            })
            
            for dep in step.dependencies:
                edges.append({
                    "source": dep,
                    "target": step.step_id
                })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "execution_id": execution.execution_id,
            "overall_progress": execution.progress
        }
    
    def list_executions(self, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List workflow executions."""
        
        executions = list(self._executions.values())
        
        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]
        
        return [
            {
                "execution_id": e.execution_id,
                "workflow_id": e.workflow_id,
                "name": e.name,
                "status": e.status.value,
                "progress": e.progress,
                "started_at": e.started_at.isoformat() if e.started_at else None,
                "completed_at": e.completed_at.isoformat() if e.completed_at else None
            }
            for e in sorted(executions, key=lambda e: e.created_at, reverse=True)
        ]
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        
        if execution_id in self._active_executions:
            self._active_executions[execution_id].cancel()
            return True
        return False
    
    def register_callback(self, callback: Callable) -> None:
        """Register callback for execution events."""
        self._callbacks.append(callback)
    
    async def _notify_callbacks(self, event: str, execution: WorkflowExecution) -> None:
        """Notify registered callbacks."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event, execution)
                else:
                    callback(event, execution)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "registered_workflows": len(self._workflows),
            "total_executions": len(self._executions),
            "active_executions": len(self._active_executions),
            "completed_executions": sum(1 for e in self._executions.values() if e.status == WorkflowStatus.COMPLETED),
            "failed_executions": sum(1 for e in self._executions.values() if e.status == WorkflowStatus.FAILED),
            "running_executions": len(self._active_executions)
        }


# Global workflow visualization instance
_workflow_visualization: Optional[WorkflowVisualization] = None


def get_workflow_visualization() -> WorkflowVisualization:
    global _workflow_visualization
    if _workflow_visualization is None:
        _workflow_visualization = WorkflowVisualization()
    return _workflow_visualization


async def close_workflow_visualization() -> None:
    global _workflow_visualization
    if _workflow_visualization:
        # Cancel active executions
        for task in _workflow_visualization._active_executions.values():
            task.cancel()
        _workflow_visualization = None