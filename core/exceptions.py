from typing import Any, Dict, List, Optional


class PolarisException(Exception):
    """Base exception class for Polaris Agent"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.error_code = self.__class__.__name__

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class PlannerException(PolarisException):
    """Base exception for planner-related errors"""

    pass


class PlanGenerationError(PlannerException):
    """Error occurred during plan generation"""

    pass


class PlanValidationError(PlannerException):
    """Plan validation failed"""

    pass


class ConfidenceError(PlannerException):
    """Confidence calculation error"""

    pass


class ExecutorException(PolarisException):
    """Base exception for executor-related errors"""

    pass


class ExecutionError(ExecutorException):
    """Error occurred during plan execution"""

    def __init__(
        self,
        message: str,
        node_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.node_id = node_id


class ToolExecutionError(ExecutorException):
    """Error occurred during tool execution"""

    def __init__(
        self,
        message: str,
        tool_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.tool_id = tool_id


class SandboxError(ExecutorException):
    """Error occurred in sandbox"""

    pass


class MemoryException(PolarisException):
    """Base exception for memory-related errors"""

    pass


class MemoryNotFoundError(MemoryException):
    """Memory item not found"""

    def __init__(self, message: str, memory_id: Optional[str] = None):
        super().__init__(message, {"memory_id": memory_id})
        self.memory_id = memory_id


class MemoryStorageError(MemoryException):
    """Memory storage error"""

    pass


class GatewayException(PolarisException):
    """Base exception for gateway-related errors"""

    pass


class InvalidRequestError(GatewayException):
    """Invalid request error"""

    pass


class AuthenticationError(GatewayException):
    """Authentication error"""

    pass


class AuthorizationError(GatewayException):
    """Authorization error"""

    pass


class RateLimitError(GatewayException):
    """Rate limit exceeded"""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message, {"retry_after": retry_after})
        self.retry_after = retry_after


class AlignException(PolarisException):
    """Base exception for align-related errors"""

    pass


class SafetyViolationError(AlignException):
    """Safety policy violation"""

    def __init__(self, message: str, violation_type: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.violation_type = violation_type


class ContentFilterError(AlignException):
    """Content filter error"""

    pass


class ConfigurationException(PolarisException):
    """Configuration error"""

    pass


class ConfigurationMissingError(ConfigurationException):
    """Required configuration missing"""

    def __init__(self, message: str, config_key: str):
        super().__init__(message, {"config_key": config_key})
        self.config_key = config_key


class ResourceException(PolarisException):
    """Resource-related exception"""

    pass


class ResourceNotFoundError(ResourceException):
    """Resource not found"""

    pass


class ResourceExhaustedError(ResourceException):
    """Resource exhausted"""

    pass


class TimeoutException(PolarisException):
    """Operation timed out"""

    def __init__(self, message: str, timeout_seconds: float):
        super().__init__(message, {"timeout_seconds": timeout_seconds})
        self.timeout_seconds = timeout_seconds


class RetryableException(PolarisException):
    """Base class for retryable exceptions"""

    pass


def exception_handler_factory() -> Dict[str, Any]:
    """Factory for exception handling configuration"""
    return {
        "retryable_exceptions": [
            TimeoutException,
            ResourceExhaustedError,
        ],
        "retry_count": 3,
        "retry_delay": 1.0,
        "backoff_multiplier": 2.0,
    }
