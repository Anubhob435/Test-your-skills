"""
Utility functions for error handling and validation in the UEM Placement Preparation Platform.
"""

import functools
import time
from typing import Callable, Any, Dict, Optional
from flask import request
from flask_login import current_user
import requests

from exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    ExternalServiceError, DatabaseError, RateLimitError,
    InvalidEmailDomainError
)
from logging_config import get_logger, log_security_event, log_external_api_call


logger = get_logger(__name__)


def validate_uem_email(email: str) -> bool:
    """
    Validate that email belongs to UEM domain
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if valid UEM email
        
    Raises:
        InvalidEmailDomainError: If email domain is not @uem.edu.in
    """
    if not email or not email.endswith('@uem.edu.in'):
        raise InvalidEmailDomainError(email)
    return True


def validate_required_fields(data: Dict[str, Any], required_fields: list) -> None:
    """
    Validate that all required fields are present in data
    
    Args:
        data: Dictionary containing form/JSON data
        required_fields: List of required field names
        
    Raises:
        ValidationError: If any required field is missing
    """
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(
            message=f"Missing required fields: {', '.join(missing_fields)}",
            field="required_fields",
            value=missing_fields
        )


def validate_field_length(value: str, field_name: str, min_length: int = None, max_length: int = None) -> None:
    """
    Validate field length constraints
    
    Args:
        value: Value to validate
        field_name: Name of the field for error reporting
        min_length: Minimum allowed length
        max_length: Maximum allowed length
        
    Raises:
        ValidationError: If length constraints are violated
    """
    if value is None:
        value = ''
    
    length = len(value)
    
    if min_length is not None and length < min_length:
        raise ValidationError(
            message=f"{field_name} must be at least {min_length} characters long",
            field=field_name,
            value=length
        )
    
    if max_length is not None and length > max_length:
        raise ValidationError(
            message=f"{field_name} must be no more than {max_length} characters long",
            field=field_name,
            value=length
        )


def require_authentication(f: Callable) -> Callable:
    """
    Decorator to require user authentication
    
    Args:
        f: Function to decorate
        
    Returns:
        Decorated function that checks authentication
        
    Raises:
        AuthenticationError: If user is not authenticated
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            log_security_event(
                event_type="UNAUTHENTICATED_ACCESS_ATTEMPT",
                details={
                    'endpoint': request.endpoint,
                    'method': request.method,
                    'path': request.path
                },
                ip_address=request.remote_addr
            )
            raise AuthenticationError("Authentication required")
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f: Callable) -> Callable:
    """
    Decorator to require admin privileges
    
    Args:
        f: Function to decorate
        
    Returns:
        Decorated function that checks admin status
        
    Raises:
        AuthenticationError: If user is not authenticated
        AuthorizationError: If user is not an admin
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            raise AuthenticationError("Authentication required")
        
        if not getattr(current_user, 'is_admin', False):
            log_security_event(
                event_type="UNAUTHORIZED_ADMIN_ACCESS_ATTEMPT",
                details={
                    'endpoint': request.endpoint,
                    'method': request.method,
                    'path': request.path
                },
                user_id=current_user.id,
                ip_address=request.remote_addr
            )
            raise AuthorizationError("Admin privileges required")
        
        return f(*args, **kwargs)
    return decorated_function


def retry_external_api_call(max_retries: int = 3, delay: float = 1.0, backoff_factor: float = 2.0):
    """
    Decorator to retry external API calls with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Factor to multiply delay by for each retry
        
    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    start_time = time.time()
                    result = f(*args, **kwargs)
                    response_time = time.time() - start_time
                    
                    # Log successful API call
                    service_name = kwargs.get('service_name', f.__name__)
                    endpoint = kwargs.get('endpoint', 'unknown')
                    log_external_api_call(
                        service=service_name,
                        endpoint=endpoint,
                        status_code=200,
                        response_time=response_time
                    )
                    
                    return result
                    
                except requests.RequestException as e:
                    last_exception = e
                    
                    # Log failed attempt
                    service_name = kwargs.get('service_name', f.__name__)
                    endpoint = kwargs.get('endpoint', 'unknown')
                    log_external_api_call(
                        service=service_name,
                        endpoint=endpoint,
                        error=str(e)
                    )
                    
                    if attempt < max_retries:
                        logger.warning(f"API call failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}")
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(f"API call failed after {max_retries + 1} attempts: {str(e)}")
                
                except Exception as e:
                    # Don't retry for non-network errors
                    logger.error(f"Non-retryable error in API call: {str(e)}")
                    raise
            
            # All retries exhausted
            service_name = kwargs.get('service_name', f.__name__)
            raise ExternalServiceError(
                service_name=service_name,
                message=f"Service unavailable after {max_retries + 1} attempts",
                original_error=last_exception
            )
        
        return wrapper
    return decorator


def handle_database_errors(f: Callable) -> Callable:
    """
    Decorator to handle database errors consistently
    
    Args:
        f: Function to decorate
        
    Returns:
        Decorated function with database error handling
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            # Import here to avoid circular imports
            from models import db
            
            try:
                db.session.rollback()
            except Exception as rollback_error:
                logger.error(f"Failed to rollback database session: {rollback_error}")
            
            # Re-raise the original exception to be handled by error handlers
            raise
    
    return wrapper


def validate_json_request(required_fields: list = None, optional_fields: list = None):
    """
    Decorator to validate JSON request data
    
    Args:
        required_fields: List of required field names
        optional_fields: List of optional field names (for documentation)
        
    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                raise ValidationError(
                    message="Request must contain valid JSON",
                    field="content_type",
                    value=request.content_type
                )
            
            data = request.get_json()
            if data is None:
                raise ValidationError(
                    message="Request body must contain valid JSON",
                    field="json_data"
                )
            
            if required_fields:
                validate_required_fields(data, required_fields)
            
            # Add validated data to kwargs
            kwargs['json_data'] = data
            return f(*args, **kwargs)
        
        return wrapper
    return decorator


def rate_limit(requests_per_minute: int = 60):
    """
    Simple rate limiting decorator (in-memory, not suitable for production)
    
    Args:
        requests_per_minute: Maximum requests per minute per IP
        
    Returns:
        Decorator function
    """
    # This is a simple in-memory rate limiter
    # In production, use Redis or a proper rate limiting service
    request_counts = {}
    
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            client_ip = request.remote_addr
            current_time = time.time()
            
            # Clean old entries (older than 1 minute)
            cutoff_time = current_time - 60
            request_counts[client_ip] = [
                timestamp for timestamp in request_counts.get(client_ip, [])
                if timestamp > cutoff_time
            ]
            
            # Check rate limit
            if len(request_counts.get(client_ip, [])) >= requests_per_minute:
                log_security_event(
                    event_type="RATE_LIMIT_EXCEEDED",
                    details={
                        'endpoint': request.endpoint,
                        'method': request.method,
                        'requests_per_minute': requests_per_minute
                    },
                    ip_address=client_ip
                )
                raise RateLimitError(
                    limit=requests_per_minute,
                    window="minute",
                    retry_after=60
                )
            
            # Add current request
            if client_ip not in request_counts:
                request_counts[client_ip] = []
            request_counts[client_ip].append(current_time)
            
            return f(*args, **kwargs)
        
        return wrapper
    return decorator