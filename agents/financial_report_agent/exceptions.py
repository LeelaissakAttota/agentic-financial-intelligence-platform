"""
Custom exceptions for the Financial Report Agent.
"""

class FinancialReportAgentError(Exception):
    """Base exception for all Financial Report Agent errors."""
    pass


class FinancialReportInputError(FinancialReportAgentError):
    """Raised when input validation fails."""
    pass


class FinancialReportLLMError(FinancialReportAgentError):
    """Raised when LLM call fails."""
    pass


class FinancialReportValidationError(FinancialReportAgentError):
    """Raised when LLM response fails validation."""
    pass