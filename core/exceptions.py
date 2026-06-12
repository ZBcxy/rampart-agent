from typing import Any, Dict, Optional


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



class PlanGenerationError(PlannerException):
    """Error occurred during plan generation"""



class PlanValidationError(PlannerException):
    """Plan validation failed"""



class ConfidenceError(PlannerException):
    """Confidence calculation error"""



class ExecutorException(PolarisException):
    """Base exception for executor-related errors"""



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



class MemoryException(PolarisException):
    """Base exception for memory-related errors"""



class MemoryNotFoundError(MemoryException):
    """Memory item not found"""

    def __init__(self, message: str, memory_id: Optional[str] = None):
        super().__init__(message, {"memory_id": memory_id})
        self.memory_id = memory_id


class MemoryStorageError(MemoryException):
    """Memory storage error"""



class GatewayException(PolarisException):
    """Base exception for gateway-related errors"""



class InvalidRequestError(GatewayException):
    """Invalid request error"""



class AuthenticationError(GatewayException):
    """Authentication error"""



class AuthorizationError(GatewayException):
    """Authorization error"""



class RateLimitError(GatewayException):
    """Rate limit exceeded"""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message, {"retry_after": retry_after})
        self.retry_after = retry_after


class AlignException(PolarisException):
    """Base exception for align-related errors"""



class SafetyViolationError(AlignException):
    """Safety policy violation"""

    def __init__(self, message: str, violation_type: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.violation_type = violation_type


class ContentFilterError(AlignException):
    """Content filter error"""



class ConfigurationException(PolarisException):
    """Configuration error"""



class ConfigurationMissingError(ConfigurationException):
    """Required configuration missing"""

    def __init__(self, message: str, config_key: str):
        super().__init__(message, {"config_key": config_key})
        self.config_key = config_key


class ResourceException(PolarisException):
    """Resource-related exception"""



class ResourceNotFoundError(ResourceException):
    """Resource not found"""



class ResourceExhaustedError(ResourceException):
    """Resource exhausted"""



class TimeoutException(PolarisException):
    """Operation timed out"""

    def __init__(self, message: str, timeout_seconds: float):
        super().__init__(message, {"timeout_seconds": timeout_seconds})
        self.timeout_seconds = timeout_seconds


class RetryableException(PolarisException):
    """Base class for retryable exceptions"""



class FailureAttributionException(PolarisException):
    """Base exception for failure attribution errors."""


class UnclassifiedFailureError(FailureAttributionException):
    """Failure could not be classified into a known category."""


class InsufficientEvidenceError(FailureAttributionException):
    """Insufficient evidence to confidently classify the failure."""


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
