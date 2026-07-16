"""Custom exceptions for the News Agent."""

class NewsAgentError(Exception):
    """Base exception for News Agent errors."""
    pass


class NewsAgentInputError(NewsAgentError):
    """Raised when input validation fails."""
    pass


class NewsAgentLLMError(NewsAgentError):
    """Raised when LLM call fails."""
    pass


class NewsAgentParseError(NewsAgentError):
    """Raised when LLM response cannot be parsed."""
    pass


class NewsAgentValidationError(NewsAgentError):
    """Raised when output validation fails."""
    pass
