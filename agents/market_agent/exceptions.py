"""
Market Analysis Agent - Custom Exceptions
"""

class MarketAgentError(Exception):
    """Base exception for Market Agent errors."""
    pass


class MarketAgentInputError(MarketAgentError):
    """Raised when input validation fails."""
    pass


class MarketAgentDataError(MarketAgentError):
    """Raised when market data retrieval fails."""
    pass


class MarketAgentLLMError(MarketAgentError):
    """Raised when LLM call fails."""
    pass


class MarketAgentParseError(MarketAgentError):
    """Raised when LLM response cannot be parsed."""
    pass


class MarketAgentValidationError(MarketAgentError):
    """Raised when output validation fails."""
    pass