# Manager Agent Exceptions

class ManagerAgentError(Exception):
    """Base exception for Manager Agent errors."""
    pass

class TaskPlanningError(ManagerAgentError):
    """Raised when task planning fails."""
    pass

class AgentCommunicationError(ManagerAgentError):
    """Raised when communication with a worker agent fails."""
    pass

class ValidationError(ManagerAgentError):
    """Raised when response validation fails."""
    pass

class ConfigurationError(ManagerAgentError):
    """Raised when agent configuration is invalid."""
    pass