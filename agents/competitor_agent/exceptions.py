"""Custom exceptions for the Competitor Agent."""


class CompetitorAgentError(Exception):
    """Base exception for all Competitor Agent errors."""
    pass


class CompetitorAgentInputError(CompetitorAgentError):
    """Raised when input validation fails."""
    pass


class CompetitorAgentLLMError(CompetitorAgentError):
    """Raised when LLM call fails."""
    pass


class CompetitorAgentValidationError(CompetitorAgentError):
    """Raised when output validation fails."""
    pass