"""
Custom exception classes for the UEM Placement Preparation Platform.
Provides structured error handling with appropriate HTTP status codes and error messages.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional


class BaseAPIException(Exception):
    """Base exception class for all API-related errors"""
    
    def __init__(self, message: str, code: str, status_code: int = 400, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response"""
        return {
            'error': True,
            'message': self.message,
            'code': self.code,
            'details': self.details,
            'timestamp': self.timestamp
        }


class AuthenticationError(BaseAPIException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=401,
            details=details
        )


class AuthorizationError(BaseAPIException):
    """Raised when user lacks permission for requested action"""
    
    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=403,
            details=details
        )


class ValidationError(BaseAPIException):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        details = {}
        if field:
            details['field'] = field
        if value is not None:
            details['value'] = str(value)
        
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class ResourceNotFoundError(BaseAPIException):
    """Raised when requested resource is not found"""
    
    def __init__(self, resource_type: str, resource_id: Any = None):
        message = f"{resource_type} not found"
        details = {'resource_type': resource_type}
        
        if resource_id is not None:
            message += f" with ID: {resource_id}"
            details['resource_id'] = str(resource_id)
        
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=404,
            details=details
        )


class DuplicateResourceError(BaseAPIException):
    """Raised when attempting to create a resource that already exists"""
    
    def __init__(self, resource_type: str, field: str, value: Any):
        super().__init__(
            message=f"{resource_type} with {field} '{value}' already exists",
            code="DUPLICATE_RESOURCE",
            status_code=409,
            details={
                'resource_type': resource_type,
                'field': field,
                'value': str(value)
            }
        )


class ExternalServiceError(BaseAPIException):
    """Raised when external service (Google Search, Gemini) fails"""
    
    def __init__(self, service_name: str, message: str = None, original_error: Exception = None):
        error_message = message or f"{service_name} service is currently unavailable"
        details = {'service': service_name}
        
        if original_error:
            details['original_error'] = str(original_error)
        
        super().__init__(
            message=error_message,
            code="EXTERNAL_SERVICE_ERROR",
            status_code=503,
            details=details
        )


class DatabaseError(BaseAPIException):
    """Raised when database operations fail"""
    
    def __init__(self, message: str = "Database operation failed", operation: str = None, original_error: Exception = None):
        details = {}
        if operation:
            details['operation'] = operation
        if original_error:
            details['original_error'] = str(original_error)
        
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=500,
            details=details
        )


class RateLimitError(BaseAPIException):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, limit: int, window: str, retry_after: int = None):
        message = f"Rate limit exceeded: {limit} requests per {window}"
        details = {
            'limit': limit,
            'window': window
        }
        
        if retry_after:
            message += f". Try again in {retry_after} seconds"
            details['retry_after'] = retry_after
        
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details
        )


class InvalidEmailDomainError(ValidationError):
    """Raised when email domain is not @uem.edu.in"""
    
    def __init__(self, email: str):
        super().__init__(
            message="Only @uem.edu.in email addresses are allowed",
            field="email",
            value=email
        )
        self.code = "INVALID_EMAIL_DOMAIN"


class TestNotAvailableError(BaseAPIException):
    """Raised when test is not available for taking"""
    
    def __init__(self, test_id: int, reason: str = "Test is not available"):
        super().__init__(
            message=reason,
            code="TEST_NOT_AVAILABLE",
            status_code=400,
            details={'test_id': test_id, 'reason': reason}
        )


class TestAlreadyCompletedError(BaseAPIException):
    """Raised when user tries to retake a completed test"""
    
    def __init__(self, test_id: int, attempt_id: int):
        super().__init__(
            message="Test has already been completed",
            code="TEST_ALREADY_COMPLETED",
            status_code=400,
            details={
                'test_id': test_id,
                'attempt_id': attempt_id
            }
        )


class QuestionGenerationError(BaseAPIException):
    """Raised when question generation fails"""
    
    def __init__(self, company: str, stage: str, original_error: Exception = None):
        message = f"Failed to generate questions for {company} at stage: {stage}"
        details = {
            'company': company,
            'stage': stage
        }
        
        if original_error:
            details['original_error'] = str(original_error)
        
        super().__init__(
            message=message,
            code="QUESTION_GENERATION_ERROR",
            status_code=500,
            details=details
        )


class ConfigurationError(BaseAPIException):
    """Raised when application configuration is invalid"""
    
    def __init__(self, config_key: str, message: str = None):
        error_message = message or f"Invalid configuration for {config_key}"
        
        super().__init__(
            message=error_message,
            code="CONFIGURATION_ERROR",
            status_code=500,
            details={'config_key': config_key}
        )