"""Custom exceptions for the Sentiment Agent."""


class SentimentAgentError(Exception):
    """Base exception for all Sentiment Agent errors."""
    pass


class SentimentAgentInputError(SentimentAgentError):
    """Raised when input validation fails."""
    pass


class SentimentAgentLLMError(SentimentAgentError):
    """Raised when LLM call fails."""
    pass


class SentimentAgentValidationError(SentimentAgentError):
    """Raised when output validation fails."""
    pass