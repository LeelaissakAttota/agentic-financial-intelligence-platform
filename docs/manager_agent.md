# Manager Agent Documentation

## Overview
The Manager Agent is the central orchestrator of the AI Financial Research Analyst system. It receives user requests for company analysis, creates an execution plan, coordinates worker agents, validates their outputs, and prepares the final investment report.

## Responsibilities

### 1. Request Processing
- Accepts user queries in natural language (e.g., "Analyze NVIDIA investment opportunity")
- Extracts company identifier (name or ticker symbol) from the request
- Normalizes input for consistent processing

### 2. Task Planning
- Determines which analyses are needed based on the request
- Creates an ordered execution plan considering dependencies
- Default plan includes all standard analyses in logical sequence:
  1. News Analysis
  2. Market Data Collection
  3. Financial Analysis (RAG-based)
  4. Sentiment Analysis
  5. Competitor Analysis
  6. Risk Analysis
  7. Investment Summary

### 3. Agent Coordination
- Maintains registry of available worker agents
- Dispatches tasks to appropriate workers with necessary context
- Manages asynchronous execution where dependencies allow
- Tracks execution status and timing for each task

### 4. Result Validation
- Verifies each worker's output against predefined JSON schemas
- Ensures data integrity and consistency
- Flags invalid or incomplete responses for handling

### 5. Error Handling
- Implements graceful degradation when individual agents fail
- Continues processing with available data when possible
- Provides detailed error information for failed components
- Implements timeout mechanisms to prevent indefinite blocking

### 6. LLM Integration
- Utilizes the existing LLM Provider abstraction layer
- Routes complex reasoning tasks to PRIMARY_MODEL
- Uses FAST_MODEL for simpler, data-extraction tasks when appropriate
- Leverages Model Router for intelligent model selection

## Architecture

```
User Request → [Manager Agent] 
                │
                ├──→ Task Planning (Rule-based or LLM-assisted)
                │
                ├──→ Worker Registry Management
                │
                ├──→ Async Task Dispatcher
                │       │
                │       ├──→ [News Agent]
                │       ├──→ [Market Data Agent]
                │       ├──→ [Financial Report Agent]
                │       ├──→ [Sentiment Agent]
                │       ├──→ [Competitor Analysis Agent]
                │       ├──→ [Risk Agent]
                │       └→→ [Investment Summary Agent] ←←←←←←←←←←←←←←←←←←←←←←←
                │                                                   │
                └─────────────────────── Results Collection ◄───────┘
                                      │
                                      ▼
                                [Final Report Preparation]
```

## Data Flow

### Input
- **Type**: Natural language string
- **Examples**: 
  - `"Analyze NVIDIA"`
  - `"Is AAPL a good investment?"`
  - `"Tell me about TSLA's financial health"`
- **Processing**: Text normalization and entity extraction (to be enhanced)

### Internal Representation
- **Task Plan**: Ordered list of analysis types with metadata
- **Worker Context**: Minimal necessary data passed to each worker
- **State Tracking**: Progress monitoring and error accumulation

### Output
- **Type**: Structured ManagerAgentOutput object
- **Components**:
  - Original company identifier
  - Executed task plan
  - Results from all workers (success or error)
  - Execution metadata (timing, success/failure counts)
  - Placeholder for final synthesis (to be implemented)

## Communication Protocol

### Manager → Worker
- **Method**: `worker.run(company_id: str, context: dict)`
- **Input**: 
  - `company_id`: Normalized company identifier
  - `context`: Dictionary containing outputs from prerequisite workers
- **Output**: `WorkerResponse` object with:
  - `status`: "success" or "error"
  - `data`: Agent-specific payload (if successful)
  - `error`: Error message (if failed)
  - `usage`: Token usage and cost metrics

### Worker → Manager
- **Format**: Standardized WorkerResponse
- **Error Handling**: Returns error status with descriptive message
- **Success**: Returns validated data per agent's schema

## Model Usage Strategy

### Current Implementation (Foundation Phase)
- **Task Planning**: Rule-based (no LLM used)
- **Worker Execution**: Placeholder (workers to be implemented)
- **Future Enhancement**: 
  - Complex planning tasks → PRIMARY_MODEL
  - Simple task selection → FAST_MODEL
  - Summary generation → PRIMARY_MODEL

### Rationale
- Foundation phase focuses on establishing communication contracts
- LLM integration will be added in subsequent phases
- Current implementation validates the orchestration framework

## Error Handling & Resilience

### Failure Modes Handled
1. **Missing Workers**: 
   - When no worker is registered for a task type
   - Returns clear error message in result

2. **Worker Failures**:
   - Captures exceptions from worker execution
   - Returns error status with diagnostic information
   - Continues processing other tasks

3. **Timeouts** (Future):
   - Will implement per-agent timeout limits
   - Will return timeout error and continue

4. **Validation Failures** (Future):
   - Will validate worker outputs against JSON schemas
   - Will provide detailed validation error messages

### Graceful Degradation
- System continues execution even when individual workers fail
- Failed tasks are clearly marked in results
- Final output indicates completion percentage
- Enables partial report generation for debugging

## Implementation Notes

### Current Limitations (Foundation Phase)
- Uses fixed task sequence rather than dynamic planning
- No actual worker agent implementations (placeholders only)
- No LLM involvement in decision-making (rule-based)
- No persistent storage of execution metrics
- No real timeout or retry mechanisms

### Extension Points
1. **Dynamic Planning**: Replace `_create_task_plan` with LLM-powered version
2. **Parallel Execution**: Implement asyncio.gather() for independent tasks
3. **Enhanced Context Passing**: Share relevant outputs between dependent workers
4. **Real Worker Integration**: Replace mock workers with actual implementations
5. **Advanced Error Handling**: Add retry circuits, timeouts, fallback strategies

## Testing Strategy

### Unit Tests
- Verify correct instantiation and configuration
- Test task plan generation for various inputs
- Validate worker registration and retrieval
- Confirm successful and failed worker handling
- Check metadata tracking accuracy
- Validate error propagation and reporting

### Integration Tests (Future)
- Test with actual worker agent implementations
- Validate end-to-end data flow
- Confirm schema compliance of outputs
- Test error recovery scenarios

## Dependencies
- **Core**: Pydantic for data validation
- **LLM Layer**: Custom LLMProvider interface (already implemented)
- **Testing**: Pytest with asyncio support
- **Future**: LangGraph for workflow orchestration (planned)

## Usage Example

```python
# Initialize with LLM provider
from llm.openrouter_client import OpenRouterClient
from agents.manager_agent.manager import ManagerAgent

llm_provider = OpenRouterClient(api_key="your-key-here")
manager = ManagerAgent(llm_provider=llm_provider)

# Process a request
result = await manager.run("NVIDIA")

# Result contains:
# - company: "NVIDIA"
# - task_plan: Ordered list of tasks to execute
# - results: Dictionary mapping task names to worker outputs
# - metadata: Execution statistics and timing
```

## Next Steps
1. Implement actual worker agents (starting with News and Market Data)
2. Enhance task planning with LLM capabilities
3. Implement parallel execution where appropriate
4. Add comprehensive error handling and recovery
5. Integrate with persistence layer for execution tracking
6. Add real timeout and retry mechanisms