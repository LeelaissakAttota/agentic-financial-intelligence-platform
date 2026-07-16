# LLM Architecture Documentation

## Overview
The LLM layer is designed as a provider-agnostic gateway. Instead of depending on a specific SDK (like Anthropic or OpenAI), the system uses a **Provider Pattern**. This allows the project to switch back-ends (e.g., from OpenRouter to direct API or local LLMs) by simply adding a new provider class.

## Architecture Flow
`Agents` $\rightarrow$ `ModelRouter` $\rightarrow$ `LLMProvider (Interface)` $\rightarrow$ `OpenRouterClient` $\rightarrow$ `OpenRouter API`

## Component Breakdown

### 1. Model Router (`model_router.py`)
The router prevents unnecessary costs by splitting tasks into two tiers:
- **Complex Reasoning**: Uses `PRIMARY_MODEL` (e.g., Claude 3.5 Sonnet). Used for final synthesis and risk analysis.
- **Simple Tasks**: Uses `FAST_MODEL` (e.g., Claude 3 Haiku). Used for news summarization and data cleaning.

### 2. Provider Interface (`llm_provider.py`)
An Abstract Base Class (ABC) that enforces a strict contract:
- `send_message()`: Standard text I/O.
- `generate_json()`: Forces structured output.
- `track_usage()`: Standardizes token and cost reporting across different providers.

### 3. OpenRouter Client (`openrouter_client.py`)
The current active implementation. It leverages OpenRouter's unified API to access various models.
- **JSON Mode**: Utilizes `response_format={"type": "json_object"}`.
- **Error Handling**: Maps OpenRouter errors to internal `LLMError` types.

### 4. Token & Cost Tracking
- **TokenTracker**: Captures raw usage data per request.
- **CostTracker**: Maps model IDs to current pricing to provide real-time financial auditing of the agent's operations.

## Future-Proofing
To add a new provider (e.g., Local Llama via Ollama):
1. Create `llm/ollama_client.py` inheriting from `LLMProvider`.
2. Implement the three required methods.
3. Update `LLM_PROVIDER` in `.env` and the instantiation logic in the main entry point.
