"""Custom exceptions for the Risk Agent."""


class RiskAgentError(Exception):
    """Base exception for all Risk Agent errors."""
    pass


class RiskAgentInputError(RiskAgentError):
    """Raised when input validation fails."""
    pass


class RiskAgentLLMError(RiskAgentError):
    """Raised when LLM call fails."""
    pass


class RiskAgentValidationError(RiskAgentError):
    """Raised when output validation fails."""
    pass