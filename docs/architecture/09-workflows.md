# Workflows Architecture
## Agentic Financial Intelligence Platform

---

## Overview

The platform implements sophisticated workflow orchestration for autonomous financial research. The workflow system (Phase 7) combined with the AI Copilot (Phase 8) enables complex, multi-step research processes with dependency management, parallel execution, and human-in-the-loop approval.

---

## Research Workflow Engine (Phase 7)

### Core Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      RESEARCH WORKFLOW ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  USER REQUEST                                                               │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────┐  │
│  │  RESEARCH       │────▶│  WORKFLOW       │────▶│  TASK               │  │
│  │  PLANNER        │     │  ORCHESTRATOR   │     │  ORCHESTRATOR       │  │
│  │  (Agent)        │     │  (Engine)       │     │  (Execution)        │  │
│  └─────────────────┘     └─────────────────┘     └─────────────────────┘  │
│       │                         │                         │                │
│       ▼                         ▼                         ▼                │
│  Execution Plan           Topological Sort           Parallel Waves       │
│  • Steps                  • Dependency Graph        • Wave 1 (Data)      │
│  • Dependencies           • Parallel Groups         • Wave 2 (Analysis)  │
│  • Agent Selection        • Retry Policy            • Wave 3 (Synthesis) │
│  • Duration Estimate      • Progress Callbacks      • Context Prop.      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Research Planner Agent

**Location**: `agents/research_planner/agent.py`

```python
class ResearchPlannerAgent(BaseWorkerAgent):
    """LLM-driven dynamic task planning based on query complexity."""
    
    async def run(self, company: str, context: Dict[str, Any]) -> ExecutionPlan:
        """
        Generate execution plan from research query.
        
        Process:
        1. Analyze query complexity (4 levels)
        2. Select relevant agents from 14 available
        3. Build dependency graph
        4. Identify parallel execution groups
        5. Estimate duration per step
        """
        
        # 1. Complexity Analysis
        complexity = await self._analyze_complexity(query)
        # SIMPLE | MODERATE | COMPLEX | COMPREHENSIVE
        
        # 2. Dynamic Agent Selection
        selected_agents = self._select_agents(complexity, query)
        # Chooses from: financial_document, sentiment, risk, competitive,
        #                news, market_data, investment_summary, knowledge_graph,
        #                portfolio, patterns, alerts, analytics, historical, cross_agent_memory
        
        # 3. Build Execution Plan
        plan = ExecutionPlan(
            steps=[
                ExecutionStep(
                    step_id="step_1",
                    agent_type=AgentType.FINANCIAL_DOCUMENT,
                    task=Task(task_type="analyze_filings", company=company, query=query),
                    dependencies=[],
                    estimated_duration_seconds=60,
                    priority=1
                ),
                ExecutionStep(
                    step_id="step_2",
                    agent_type=AgentType.NEWS,
                    task=Task(task_type="analyze_news", company=company, query=query),
                    dependencies=[],
                    estimated_duration_seconds=30,
                    priority=1
                ),
                # ... more steps with dependencies
            ],
            parallel_groups={
                "data_collection": ["step_1", "step_2", "step_3"],
                "analysis_1": ["step_4", "step_5"],
                "analysis_2": ["step_6", "step_7"],
                "synthesis": ["step_8"]
            },
            total_estimated_duration_seconds=180
        )
        
        return plan
```

**Complexity Levels**:
| Level | Agents | Parallel Groups | Est. Duration |
|-------|--------|-----------------|---------------|
| SIMPLE | 3-4 | 1 | 60-90s |
| MODERATE | 5-7 | 2 | 90-180s |
| COMPLEX | 8-10 | 3 | 180-300s |
| COMPREHENSIVE | 11-14 | 4 | 300-600s |

---

### Workflow Orchestrator

**Location**: `workflows/orchestrator.py`

```python
class WorkflowOrchestrator:
    """Execute research plans with topological sort and parallel waves."""
    
    def __init__(self, max_concurrency: int = 4):
        self.max_concurrency = max_concurrency
        self.manager_agent = ManagerAgent()
        self.memory_store = get_memory_store()
    
    async def execute_plan(
        self,
        plan: ExecutionPlan,
        progress_callback: Optional[Callable] = None
    ) -> PlanExecution:
        """
        Execute plan with:
        - Topological sort for dependency resolution
        - Parallel wave execution with bounded concurrency
        - Retry with exponential backoff
        - Context propagation between steps
        - Memory integration for cross-agent sharing
        """
        
        # 1. Build dependency graph
        graph = self._build_dependency_graph(plan.steps)
        
        # 2. Topological sort into waves
        waves = self._topological_sort(graph)
        # waves = [
        #   ["step_1", "step_2", "step_3"],  # Wave 1: parallel (no deps)
        #   ["step_4", "step_5"],             # Wave 2: depends on wave 1
        #   ["step_6", "step_7"],             # Wave 3: depends on wave 2
        #   ["step_8"]                        # Wave 4: depends on wave 3
        # ]
        
        # 3. Execute waves sequentially
        execution = PlanExecution(plan_id=plan.plan_id, status="running")
        
        for wave_idx, wave in enumerate(waves):
            # Update progress
            if progress_callback:
                await progress_callback(f"Wave {wave_idx + 1}/{len(waves)}", wave_idx / len(waves))
            
            # Execute wave steps in parallel (bounded)
            semaphore = asyncio.Semaphore(self.max_concurrency)
            tasks = [
                self._execute_step_with_semaphore(semaphore, step_id, plan, execution)
                for step_id in wave
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 4. Handle results, retries, failures
            for step_id, result in zip(wave, results):
                if isinstance(result, Exception):
                    await self._handle_step_failure(step_id, result, plan, execution)
                else:
                    # Store in memory for dependent steps
                    await self._store_step_result(step_id, result)
                    
                    # Propagate context to dependent steps
                    await self._propagate_context(step_id, result, plan, execution)
        
        execution.status = "completed"
        return execution
    
    async def _execute_step_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        step_id: str,
        plan: ExecutionPlan,
        execution: PlanExecution
    ) -> TaskResult:
        """Execute single step with concurrency control and retry."""
        async with semaphore:
            step = next(s for s in plan.steps if s.step_id == step_id)
            
            # Build context from dependencies
            context = self._build_step_context(step, execution)
            
            # Retry logic
            for attempt in range(step.max_retries + 1):
                try:
                    agent = self.manager_agent.get_agent(step.agent_type)
                    result = await agent.run(
                        company=step.task.company,
                        query=step.task.query,
                        context=context
                    )
                    
                    return TaskResult(
                        step_id=step_id,
                        status=TaskStatus.COMPLETED,
                        data=result,
                        execution_time_seconds=time.time() - start
                    )
                    
                except TransientError as e:
                    if attempt < step.max_retries:
                        wait_time = 60 * (2 ** attempt)  # 1m, 2m, 4m
                        await asyncio.sleep(wait_time)
                        continue
                    raise
            
            return TaskResult(
                step_id=step_id,
                status=TaskStatus.FAILED,
                error=str(e)
            )
```

### Execution Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        WORKFLOW EXECUTION FLOW                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PLAN CREATED                                                               │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────┐                                                           │
│  │  WAVE 1     │ ──▶ step_1 (Financial Doc)  ─┐                            │
│  │  (Parallel) │    step_2 (News)             ├──▶ Store in Memory         │
│  └─────────────┘    step_3 (Market Data)      ─┘                            │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────┐                                                           │
│  │  WAVE 2     │ ──▶ step_4 (Sentiment)  ─┐                                │
│  │  (Parallel) │    step_5 (Risk)         ├──▶ Context Propagation        │
│  └─────────────┘                           ─┘                                │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────┐                                                           │
│  │  WAVE 3     │ ──▶ step_6 (Competitive) ─┐                                │
│  │  (Parallel) │    step_7 (Patterns)      ├──▶ Context Propagation        │
│  └─────────────┘                           ─┘                                │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────┐                                                           │
│  │  WAVE 4     │ ──▶ step_8 (Investment Summary)                           │
│  │  (Synthesis)│                                                             │
│  └─────────────┘                                                             │
│       │                                                                      │
│       ▼                                                                      │
│  EXECUTION COMPLETE                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Human Approval Workflow (Phase 7)

### Approval Chain
```python
# approval/workflow.py

class ApprovalWorkflow:
    """Sequential approval chains with escalation."""
    
    async def create_approval_request(
        self,
        action: ApprovalAction,  # APPROVE, REJECT, REQUEST_CHANGES, ESCALATE, DELEGATE, COMMENT
        resource_type: str,
        resource_id: str,
        requester_id: str,
        chain: List[ApprovalStep] = None
    ) -> ApprovalRequest:
        """
        Create approval request with configurable chain.
        
        Default chain: Analyst → Senior Analyst → Manager
        Escalation: Auto-add next level with 24h timeout
        Delegation: Transfer to another user with context
        """
        
        if chain is None:
            chain = [
                ApprovalStep(role="analyst", required=True),
                ApprovalStep(role="senior_analyst", required=True),
                ApprovalStep(role="manager", required=False)  # Optional
            ]
        
        request = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            requester_id=requester_id,
            chain=chain,
            current_step=0,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=72)
        )
        
        # Notify first approver
        await self.notification_engine.send(
            channel=NotificationChannel.EMAIL,
            recipient=chain[0].approver_id,
            template="approval_request",
            data={"request": request}
        )
        
        return request
    
    async def process_action(
        self,
        request_id: str,
        approver_id: str,
        action: ApprovalAction,
        comment: str = ""
    ) -> ApprovalRequest:
        """Process approval action with chain progression."""
        
        request = await self.get_request(request_id)
        current_step = request.chain[request.current_step]
        
        # Validate approver
        if current_step.approver_id != approver_id:
            raise PermissionError("Not authorized for this step")
        
        # Record action
        request.audit_trail.append(AuditEntry(
            step=request.current_step,
            approver_id=approver_id,
            action=action,
            comment=comment,
            timestamp=datetime.utcnow()
        ))
        
        if action == ApprovalAction.APPROVE:
            # Move to next step or complete
            request.current_step += 1
            if request.current_step >= len(request.chain):
                request.status = ApprovalStatus.APPROVED
                await self._execute_approved_action(request)
            else:
                # Notify next approver
                await self._notify_next_approver(request)
                
        elif action == ApprovalAction.REJECT:
            request.status = ApprovalStatus.REJECTED
            await self._notify_rejection(request)
            
        elif action == ApprovalAction.ESCALATE:
            # Add escalation step
            request.chain.insert(
                request.current_step + 1,
                ApprovalStep(role="escalated_manager", required=True)
            )
            await self._notify_escalation(request)
            
        elif action == ApprovalAction.DELEGATE:
            # Transfer to another user
            current_step.approver_id = comment  # delegate_id in comment
            await self._notify_delegation(request)
        
        return request
```

---

## AI Copilot Workflows (Phase 8)

### Copilot Agent Orchestration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      COPILOT WORKFLOW ORCHESTRATION                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  USER MESSAGE                                                               │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    COPILOT AGENT                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │   │
│  │  │  INTENT     │─▶│  CONTEXT    │─▶│  PLANNING   │─▶│  TOOL     │  │   │
│  │  │  CLASSIFIER │  │  BUILDER    │  │  (Optional) │  │  SELECTOR │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                              │                      │              │
│       ▼                              ▼                      ▼              │
│  ┌─────────────┐              ┌─────────────┐        ┌─────────────┐     │
│  │ CONVERSATION│              │ TASK        │        │ TOOL        │     │
│  │ MANAGER     │              │ PLANNER     │        │ REGISTRY    │     │
│  └─────────────┘              └─────────────┘        └─────────────┘     │
│       │                              │                      │              │
│       ▼                              ▼                      ▼              │
│  Response /              Execution Plan              Tool Execution       │
│  Plan Request            (if needed)                 (15 tools)           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Intent Classification
```python
# copilot/agent.py

class CopilotAgent:
    """Main copilot orchestrator with intent classification."""
    
    INTENTS = {
        "research": "Full autonomous research workflow",
        "plan": "Create execution plan only",
        "tool": "Execute specific tool",
        "report": "Generate report",
        "watchlist": "Watchlist management",
        "memory": "Memory queries",
        "status": "System status",
        "conversational": "General chat"
    }
    
    async def classify_intent(self, message: str, context: ConversationContext) -> Intent:
        """Classify user intent using LLM."""
        
        prompt = f"""
        Classify the user's intent:
        
        Message: "{message}"
        Context: {json.dumps(context.to_dict(), default=str)}
        
        Available intents: {', '.join(self.INTENTS.keys())}
        
        Return JSON: {{"intent": "...", "confidence": 0.0-1.0, "entities": {{...}}}}
        """
        
        response = await self.llm.agenerate_json(prompt)
        return Intent(**response)
    
    async def process_message(
        self,
        message: str,
        session_id: str,
        mode: ExecutionMode = ExecutionMode.AUTO_EXECUTE
    ) -> CopilotResponse:
        """Main message processing pipeline."""
        
        # 1. Get/create session
        session = await self.get_or_create_session(session_id)
        
        # 2. Classify intent
        intent = await self.classify_intent(message, session.context)
        
        # 3. Route based on intent
        if intent.intent == "research":
            return await self._handle_research(message, session, mode)
        elif intent.intent == "plan":
            return await self._handle_plan(message, session)
        elif intent.intent == "tool":
            return await self._handle_tool(message, session)
        elif intent.intent == "report":
            return await self._handle_report(message, session)
        elif intent.intent == "watchlist":
            return await self._handle_watchlist(message, session)
        elif intent.intent == "memory":
            return await self._handle_memory(message, session)
        elif intent.intent == "status":
            return await self._handle_status(session)
        else:
            return await self._handle_conversational(message, session)
```

### Task Planning & Execution
```python
# planning/agent.py

class PlanningAgent:
    """Create execution plans from high-level goals."""
    
    async def create_plan(
        self,
        goal: str,
        context: Dict[str, Any],
        mode: ExecutionMode = ExecutionMode.AUTO_EXECUTE
    ) -> ExecutionPlan:
        """
        LLM-driven planning with:
        - Goal decomposition
        - Dependency analysis
        - Agent selection
        - Duration estimation
        """
        
        # 1. Analyze goal complexity
        complexity = await self._analyze_complexity(goal, context)
        
        # 2. Select agents (from 14 available)
        selected_agents = self._select_agents(complexity, goal, context)
        
        # 3. Build dependency graph
        steps = await self._build_steps(selected_agents, goal, context)
        
        # 4. Identify parallel groups
        parallel_groups = self._identify_parallel_groups(steps)
        
        # 5. Estimate durations
        for step in steps:
            step.estimated_duration_seconds = self._estimate_duration(
                step.agent_type, step.task
            )
        
        # 6. Calculate total estimate
        total = self._calculate_total_duration(steps, parallel_groups)
        
        return ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            goal=goal,
            complexity=complexity,
            steps=steps,
            parallel_groups=parallel_groups,
            estimated_duration_seconds=total,
            mode=mode,
            created_at=datetime.utcnow()
        )
    
    async def execute_plan(
        self,
        plan: ExecutionPlan,
        session: CopilotSession
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """Execute plan with real-time event streaming."""
        
        orchestrator = WorkflowOrchestrator(max_concurrency=4)
        
        async for event in orchestrator.execute_plan_streaming(plan):
            # Emit events for dashboard
            yield event
            
            # Store in session
            session.execution_events.append(event)
            
            # Check for human approval requirements
            if event.requires_approval:
                approval_request = await self._create_approval_request(event)
                yield ExecutionEvent(
                    type="approval_required",
                    data=approval_request
                )
                
                # Wait for approval (with timeout)
                result = await self._wait_for_approval(approval_request)
                if not result.approved:
                    yield ExecutionEvent(type="execution_cancelled", data=result)
                    return
        
        yield ExecutionEvent(type="completed", data={"plan_id": plan.plan_id})
```

---

## Multi-Agent Collaboration (Phase 8)

### Collaboration Patterns

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MULTI-AGENT COLLABORATION PATTERNS                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. SEQUENTIAL PIPELINE                                                     │
│     Agent A ──▶ Agent B ──▶ Agent C                                         │
│     (Output of A feeds B, output of B feeds C)                             │
│                                                                             │
│  2. PARALLEL FAN-OUT                                                        │
│           ┌──▶ Agent B                                                      │
│     Agent A                                    (All receive same input)     │
│           └──▶ Agent C                                                      │
│                                                                             │
│  3. MAP-REDUCE                                                              │
│     Agent A ──▶ [Agent B1, Agent B2, Agent B3] ──▶ Agent C                 │
│     (Split work, parallel process, aggregate)                              │
│                                                                             │
│  4. CONSENSUS BUILDING                                                      │
│     Agent A ──▶ [Agent B1, Agent B2, Agent B3] ──▶ Consensus ──▶ Output   │
│     (Voting, weighted, threshold, unanimous)                               │
│                                                                             │
│  5. DELEGATION                                                              │
│     Agent A ──▶ (decides) ──▶ Delegates to Agent B/C based on capability  │
│                                                                             │
│  6. KNOWLEDGE SHARING                                                       │
│     Agent A ──▶ Shared Memory ──▶ Agent B (reads A's findings)             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Collaboration Coordinator
```python
# collaboration/coordinator.py

class CollaborationCoordinator:
    """Coordinate multi-agent workflows with messaging and knowledge sharing."""
    
    def __init__(self):
        self.mailboxes: Dict[str, AgentMailbox] = {}
        self.sessions: Dict[str, CollaborationSession] = {}
        self.knowledge_aggregator = KnowledgeAggregator()
    
    async def start_collaboration(
        self,
        session_id: str,
        participants: List[str],
        goal: str,
        pattern: CollaborationPattern = CollaborationPattern = CollaborationPattern.SEQUENTIAL
    ) -> CollaborationSession:
        """Start multi-agent collaboration session."""
        
        session = CollaborationSession(
            session_id=session_id,
            participants=participants,
            goal=goal,
            pattern=pattern,
            created_at=datetime.utcnow()
        )
        
        # Create mailboxes for each participant
        for agent_id in participants:
            self.mailboxes[agent_id] = AgentMailbox(agent_id=agent_id)
        
        self.sessions[session_id] = session
        
        # Start pattern-specific coordination
        if pattern == CollaborationPattern.SEQUENTIAL:
            asyncio.create_task(self._run_sequential(session))
        elif pattern == CollaborationPattern.CONSENSUS:
            asyncio.create_task(self._run_consensus(session))
        elif pattern == CollaborationPattern.DELEGATION:
            asyncio.create_task(self._run_delegation(session))
        
        return session
    
    async def _run_sequential(self, session: CollaborationSession):
        """Run sequential pipeline."""
        context = {}
        
        for agent_id in session.participants:
            # Send message with accumulated context
            message = CoordinationMessage(
                message_id=str(uuid.uuid4()),
                sender_id="coordinator",
                recipient_id=agent_id,
                signal=CoordinationSignal.REQUEST_ANALYSIS,
                payload={
                    "goal": session.goal,
                    "context": context,
                    "previous_findings": session.findings
                }
            )
            
            await self.mailboxes[agent_id].send(message)
            
            # Wait for response
            response = await self.mailboxes[agent_id].receive_response(timeout=300)
            
            # Accumulate findings
            session.findings[agent_id] = response.payload
            context[agent_id] = response.payload
            
            # Check for conflicts
            conflicts = self._detect_conflicts(session.findings)
            if conflicts:
                await self._resolve_conflicts(session, conflicts)
        
        session.status = "completed"
    
    async def _run_consensus(self, session: CollaborationSession):
        """Run consensus-building collaboration."""
        
        # Phase 1: Independent analysis
        for agent_id in session.participants:
            message = CoordinationMessage(
                sender_id="coordinator",
                recipient_id=agent_id,
                signal=CoordinationSignal.REQUEST_ANALYSIS,
                payload={"goal": session.goal, "independent": True}
            )
            await self.mailboxes[agent_id].send(message)
        
        # Collect independent analyses
        analyses = {}
        for agent_id in session.participants:
            response = await self.mailboxes[agent_id].receive_response(timeout=300)
            analyses[agent_id] = response.payload
        
        # Phase 2: Share findings
        for agent_id in session.participants:
            share_msg = CoordinationMessage(
                sender_id="coordinator",
                recipient_id=agent_id,
                signal=CoordinationSignal.SHARE_FINDINGS,
                payload={"all_analyses": analyses}
            )
            await self.mailboxes[agent_id].send(share_msg)
        
        # Phase 3: Build consensus
        consensus_builder = ConsensusBuilder()
        consensus = await consensus_builder.build_consensus(
            analyses=analyses,
            method=ConsensusMethod.WEIGHTED_VOTING,
            weights=self._get_agent_weights(session.participants)
        )
        
        session.consensus = consensus
        session.status = "completed"
    
    def _detect_conflicts(self, findings: Dict[str, Any]) -> List[Conflict]:
        """Detect conflicts between agent findings."""
        conflicts = []
        
        # Sentiment conflict
        sentiments = {k: v.get("sentiment") for k, v in findings.items() if v.get("sentiment")}
        if len(set(sentiments.values())) > 1:
            conflicts.append(Conflict(
                type=ConflictType.SENTIMENT_OPPOSITION,
                agents=list(sentiments.keys()),
                details=sentiments
            ))
        
        # Recommendation conflict
        recommendations = {k: v.get("recommendation") for k, v in findings.items() 
                          if v.get("recommendation")}
        if len(set(recommendations.values())) > 1:
            conflicts.append(Conflict(
                type=ConflictType.RECOMMENDATION_CONTRADICTION,
                agents=list(recommendations.keys()),
                details=recommendations
            ))
        
        return conflicts
```

---

## Event-Driven Architecture

### Coordination Signals
```python
# collaboration/coordinator.py

class CoordinationSignal(str, Enum):
    """Signals for inter-agent communication."""
    REQUEST_ANALYSIS = "request_analysis"
    SHARE_FINDINGS = "share_findings"
    REQUEST_CLARIFICATION = "request_clarification"
    PROVIDE_EVIDENCE = "provide_evidence"
    CONFLICT_DETECTED = "conflict_detected"
    CONFLICT_RESOLVED = "conflict_resolved"
    CONSENSUS_REACHED = "consensus_reached"
    DELEGATION_REQUEST = "delegation_request"
    DELEGATION_ACCEPTED = "delegation_accepted"
    STATUS_UPDATE = "status_update"
```

### Message Format
```python
@dataclass
class CoordinationMessage:
    message_id: str
    sender_id: str
    recipient_id: str
    signal: CoordinationSignal
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None  # For request-response
    requires_response: bool = False
    response_timeout_seconds: int = 300
```

---

## Workflow Monitoring

### Execution Events
```python
# workflows/orchestrator.py

class ExecutionEventType(str, Enum):
    PLAN_STARTED = "plan_started"
    WAVE_STARTED = "wave_started"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    STEP_RETRYING = "step_retrying"
    CONTEXT_PROPAGATED = "context_propagated"
    MEMORY_STORED = "memory_stored"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RECEIVED = "approval_received"
    PLAN_COMPLETED = "plan_completed"
    PLAN_FAILED = "plan_failed"

@dataclass
class ExecutionEvent:
    event_id: str
    plan_id: str
    type: ExecutionEventType
    timestamp: datetime
    step_id: Optional[str] = None
    wave_index: Optional[int] = None
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

# Real-time streaming to dashboard
async def execute_plan_streaming(self, plan: ExecutionPlan) -> AsyncGenerator[ExecutionEvent, None]:
    """Stream execution events for real-time dashboard updates."""
    
    yield ExecutionEvent(
        type=ExecutionEventType.PLAN_STARTED,
        plan_id=plan.plan_id,
        data={"total_steps": len(plan.steps), "waves": len(plan.waves)}
    )
    
    for wave_idx, wave in enumerate(plan.waves):
        yield ExecutionEvent(
            type=ExecutionEventType.WAVE_STARTED,
            plan_id=plan.plan_id,
            wave_index=wave_idx,
            data={"steps": wave}
        )
        
        # Execute wave steps...
        for step_id in wave:
            yield ExecutionEvent(
                type=ExecutionEventType.STEP_STARTED,
                plan_id=plan.plan_id,
                step_id=step_id,
                data={"agent_type": step.agent_type}
            )
            
            # ... execution logic ...
            
            if success:
                yield ExecutionEvent(
                    type=ExecutionEventType.STEP_COMPLETED,
                    plan_id=plan.plan_id,
                    step_id=step_id,
                    data={"result": result, "duration_ms": duration}
                )
            else:
                yield ExecutionEvent(
                    type=ExecutionEventType.STEP_FAILED,
                    plan_id=plan.plan_id,
                    step_id=step_id,
                    data={"error": error, "attempt": attempt}
                )
```

---

## Configuration

### Workflow Settings
```yaml
# config/workflow.yaml
workflow:
  # Orchestrator
  max_concurrency: 4
  default_retry_attempts: 3
  retry_base_delay_seconds: 60
  max_retry_delay_seconds: 300
  
  # Planning
  complexity_thresholds:
    simple_max_agents: 4
    moderate_max_agents: 7
    complex_max_agents: 10
    comprehensive_max_agents: 14
  
  # Duration estimates (seconds per agent type)
  duration_estimates:
    financial_document: 60
    sentiment: 30
    risk: 45
    competitive: 45
    news: 30
    market_data: 15
    investment_summary: 30
    knowledge_graph: 30
    portfolio: 30
    patterns: 30
    alerts: 15
    analytics: 60
    historical: 45
    cross_agent_memory: 10
  
  # Approval
  approval:
    default_chain:
      - role: analyst
        required: true
      - role: senior_analyst
        required: true
      - role: manager
        required: false
    expiration_hours: 72
    escalation_hours: 24
    notification_channels: ["email", "slack", "in_app"]
  
  # Memory
  memory:
    auto_store_agent_outputs: true
    memory_types:
      - session
      - conclusion
      - source
      - agent_output
      - follow_up
      - report
      - insight
    cross_session_retrieval: true
    company_scoped_queries: true
```

---

*Document Version: 1.0*  
*Last Updated: 2026-07-18*  
*Platform: Agentic Financial Intelligence Platform v1.7.0-phase8*