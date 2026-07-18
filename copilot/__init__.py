"""Copilot Package - AI Financial Research Assistant."""
from copilot.assistant import (
    CopilotAssistant,
    ConversationManager,
    ConversationSession,
    ConversationMessage,
    MessageRole,
    ConversationStatus,
    CopilotResponse,
    get_conversation_manager,
    get_copilot_assistant
)
from copilot.conversation import (
    ConversationContext,
    get_conversation_context
)
from copilot.prompts import (
    COPILOT_SYSTEM_PROMPT,
    RESEARCH_PLANNING_PROMPT,
    TOOL_SELECTION_PROMPT,
    INVESTMENT_THESIS_PROMPT,
    RISK_EXPLANATION_PROMPT,
    CONSENSUS_PROMPT,
    CONFLICT_RESOLUTION_PROMPT,
    REPORT_PROMPTS,
    CONVERSATION_PROMPTS,
    DECISION_REASONING_PROMPTS,
    EXPLANATION_PROMPTS,
    TOOL_PARAM_PROMPTS,
    get_prompt
)

__all__ = [
    "CopilotAssistant",
    "ConversationManager",
    "ConversationSession",
    "ConversationMessage",
    "MessageRole",
    "ConversationStatus",
    "CopilotResponse",
    "get_conversation_manager",
    "get_copilot_assistant",
    "ConversationContext",
    "get_conversation_context",
    "COPILOT_SYSTEM_PROMPT",
    "RESEARCH_PLANNING_PROMPT",
    "TOOL_SELECTION_PROMPT",
    "INVESTMENT_THESIS_PROMPT",
    "RISK_EXPLANATION_PROMPT",
    "CONSENSUS_PROMPT",
    "CONFLICT_RESOLUTION_PROMPT",
    "REPORT_PROMPTS",
    "CONVERSATION_PROMPTS",
    "DECISION_REASONING_PROMPTS",
    "EXPLANATION_PROMPTS",
    "TOOL_PARAM_PROMPTS",
    "get_prompt"
]