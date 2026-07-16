"""
Custom exceptions for the LLM layer to maintain provider-agnostic error handling.
"""
class LLMError(Exception):
    """Base exception for all LLM related errors."""
    pass

class LLMProviderError(LLMError):
    """Raised when the provider returns an API error."""
    pass

class LLMTimeoutError(LLMError):
    """Raised when the LLM request times out."""
    pass

class LLMParseError(LLMError):
    """Raised when the LLM output cannot be parsed as JSON."""
    pass

class LLMAuthenticationError(LLMError):
    """Raised when API keys are invalid or missing."""
    pass
