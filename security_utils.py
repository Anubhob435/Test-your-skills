"""
Security utilities for UEM Placement Platform

This module provides comprehensive security measures including:
- CSRF protection
- Input sanitization and validation
- Rate limiting
- SQL injection prevention
- XSS protection
- Security headers
"""

import re
import bleach
import html
from functools import wraps
from flask import request, jsonify, current_app, g
from flask_wtf.csrf import CSRFProtect, validate_csrf, generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import BadRequest
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import redis
import json

logger = logging.getLogger(__name__)

# Initialize CSRF protection
csrf = CSRFProtect()

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per hour", "100 per minute"]
)

class SecurityConfig:
    """Security configuration constants"""
    
    # Rate limiting defaults
    DEFAULT_RATE_LIMIT = "100 per minute"
    AUTH_RATE_LIMIT = "10 per minute"
    API_RATE_LIMIT = "200 per hour"
    
    # Input validation
    MAX_INPUT_LENGTH = 10000
    MAX_EMAIL_LENGTH = 254
    MAX_NAME_LENGTH = 100
    MAX_PASSWORD_LENGTH = 128
    
    # Allowed HTML tags for sanitization
    ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li']
    ALLOWED_ATTRIBUTES = {}
    
    # Security headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:;"
    }


class InputSanitizer:
    """Utility class for input sanitization and validation"""
    
    @staticmethod
    def sanitize_html(input_text: str) -> str:
        """
        Sanitize HTML input to prevent XSS attacks
        
        Args:
            input_text (str): Raw HTML input
            
        Returns:
            str: Sanitized HTML
        """
        if not input_text:
            return ""
        
        # Use bleach to sanitize HTML
        sanitized = bleach.clean(
            input_text,
            tags=SecurityConfig.ALLOWED_TAGS,
            attributes=SecurityConfig.ALLOWED_ATTRIBUTES,
            strip=True
        )
        
        return sanitized
    
    @staticmethod
    def sanitize_text(input_text: str) -> str:
        """
        Sanitize plain text input
        
        Args:
            input_text (str): Raw text input
            
        Returns:
            str: Sanitized text
        """
        if not input_text:
            return ""
        
        # Remove HTML tags and escape special characters
        sanitized = html.escape(input_text.strip())
        
        return sanitized
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email format and length
        
        Args:
            email (str): Email to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not email or len(email) > SecurityConfig.MAX_EMAIL_LENGTH:
            return False
        
        # Basic email regex pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_name(name: str) -> bool:
        """
        Validate name format and length
        
        Args:
            name (str): Name to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not name or len(name) > SecurityConfig.MAX_NAME_LENGTH:
            return False
        
        # Allow letters, spaces, hyphens, and apostrophes
        pattern = r"^[a-zA-Z\s\-']+$"
        return bool(re.match(pattern, name.strip()))
    
    @staticmethod
    def validate_password(password: str) -> tuple:
        """
        Validate password strength and format
        
        Args:
            password (str): Password to validate
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        if not password:
            return False, "Password is required"
        
        if len(password) < 6:
            return False, "Password must be at least 6 characters long"
        
        if len(password) > SecurityConfig.MAX_PASSWORD_LENGTH:
            return False, f"Password must be less than {SecurityConfig.MAX_PASSWORD_LENGTH} characters"
        
        # Check for at least one letter and one number
        has_letter = any(c.isalpha() for c in password)
        has_number = any(c.isdigit() for c in password)
        
        if not has_letter:
            return False, "Password must contain at least one letter"
        
        if not has_number:
            return False, "Password must contain at least one number"
        
        # Check for dangerous characters that might indicate injection attempts
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '{', '}']
        if any(char in password for char in dangerous_chars):
            return False, "Password contains invalid characters"
        
        return True, "Password is valid"
    
    @staticmethod
    def validate_input_length(input_text: str, max_length: int = None) -> bool:
        """
        Validate input length
        
        Args:
            input_text (str): Input to validate
            max_length (int): Maximum allowed length
            
        Returns:
            bool: True if valid length, False otherwise
        """
        if not input_text:
            return True
        
        max_len = max_length or SecurityConfig.MAX_INPUT_LENGTH
        return len(input_text) <= max_len
    
    @staticmethod
    def detect_sql_injection(input_text: str) -> bool:
        """
        Detect potential SQL injection patterns
        
        Args:
            input_text (str): Input to check
            
        Returns:
            bool: True if potential injection detected, False otherwise
        """
        if not input_text:
            return False
        
        # Common SQL injection patterns
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
            r"(--|#|/\*|\*/)",
            r"(\bxp_cmdshell\b)",
            r"(\bsp_executesql\b)",
            r"(';|';\s*--)",
            r"(\bunion\s+select\b)",
            r"(\binto\s+outfile\b)",
            r"(\bload_file\b)"
        ]
        
        input_lower = input_text.lower()
        for pattern in sql_patterns:
            if re.search(pattern, input_lower, re.IGNORECASE):
                logger.warning(f"Potential SQL injection detected: {pattern}")
                return True
        
        return False


class RateLimiter:
    """Enhanced rate limiting with Redis backend"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
    
    def is_rate_limited(self, key: str, limit: int, window: int) -> tuple:
        """
        Check if request is rate limited
        
        Args:
            key (str): Rate limit key (user ID, IP, etc.)
            limit (int): Maximum requests allowed
            window (int): Time window in seconds
            
        Returns:
            tuple: (is_limited: bool, remaining: int, reset_time: int)
        """
        if not self.redis_client:
            # Fallback to in-memory tracking (not recommended for production)
            return False, limit, 0
        
        try:
            current_time = int(datetime.utcnow().timestamp())
            window_start = current_time - window
            
            # Use Redis sorted set to track requests
            pipe = self.redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, window)
            
            results = pipe.execute()
            current_requests = results[1]
            
            if current_requests >= limit:
                remaining = 0
                reset_time = current_time + window
                return True, remaining, reset_time
            else:
                remaining = limit - current_requests - 1
                reset_time = current_time + window
                return False, remaining, reset_time
                
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Fail open - allow request if rate limiting fails
            return False, limit, 0


def init_security(app):
    """
    Initialize security measures for Flask app
    
    Args:
        app: Flask application instance
    """
    # Initialize CSRF protection
    csrf.init_app(app)
    
    # Initialize rate limiter
    limiter.init_app(app)
    
    # Add security headers to all responses
    @app.after_request
    def add_security_headers(response):
        for header, value in SecurityConfig.SECURITY_HEADERS.items():
            response.headers[header] = value
        return response
    
    # Add CSRF token to template context
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf())


def csrf_protect(f):
    """
    Decorator to add CSRF protection to routes
    
    Args:
        f: Function to decorate
        
    Returns:
        Decorated function with CSRF protection
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            try:
                validate_csrf(request.headers.get('X-CSRFToken') or 
                            request.form.get('csrf_token'))
            except Exception as e:
                logger.warning(f"CSRF validation failed: {e}")
                return jsonify({
                    'success': False,
                    'error': 'CSRF token validation failed',
                    'code': 'CSRF_ERROR'
                }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def sanitize_input(fields: List[str] = None):
    """
    Decorator to sanitize input data
    
    Args:
        fields (List[str]): List of fields to sanitize
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.is_json:
                data = request.get_json() or {}
            else:
                data = request.form.to_dict()
            
            # Sanitize specified fields or all fields
            fields_to_sanitize = fields or data.keys()
            
            for field in fields_to_sanitize:
                if field in data and isinstance(data[field], str):
                    # Check for SQL injection
                    if InputSanitizer.detect_sql_injection(data[field]):
                        logger.warning(f"SQL injection attempt detected in field: {field}")
                        return jsonify({
                            'success': False,
                            'error': 'Invalid input detected',
                            'code': 'INVALID_INPUT'
                        }), 400
                    
                    # Sanitize the input
                    data[field] = InputSanitizer.sanitize_text(data[field])
                    
                    # Validate length
                    if not InputSanitizer.validate_input_length(data[field]):
                        return jsonify({
                            'success': False,
                            'error': 'Input too long',
                            'code': 'INPUT_TOO_LONG'
                        }), 400
            
            # Store sanitized data in g for access in route
            g.sanitized_data = data
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def validate_json_input(required_fields: List[str] = None, optional_fields: List[str] = None):
    """
    Decorator to validate JSON input
    
    Args:
        required_fields (List[str]): Required fields
        optional_fields (List[str]): Optional fields
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Content-Type must be application/json',
                    'code': 'INVALID_CONTENT_TYPE'
                }), 400
            
            try:
                data = request.get_json()
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': 'Invalid JSON format',
                    'code': 'INVALID_JSON'
                }), 400
            
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Request body is required',
                    'code': 'MISSING_BODY'
                }), 400
            
            # Check required fields
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return jsonify({
                        'success': False,
                        'error': f'Missing required fields: {", ".join(missing_fields)}',
                        'code': 'MISSING_FIELDS'
                    }), 400
            
            # Check for unexpected fields
            allowed_fields = set((required_fields or []) + (optional_fields or []))
            if allowed_fields:
                unexpected_fields = [field for field in data.keys() if field not in allowed_fields]
                if unexpected_fields:
                    return jsonify({
                        'success': False,
                        'error': f'Unexpected fields: {", ".join(unexpected_fields)}',
                        'code': 'UNEXPECTED_FIELDS'
                    }), 400
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def rate_limit_by_user(limit: str = SecurityConfig.DEFAULT_RATE_LIMIT):
    """
    Decorator for user-based rate limiting
    
    Args:
        limit (str): Rate limit string (e.g., "10 per minute")
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from auth_middleware import get_current_user
            
            user = get_current_user()
            if user:
                key = f"rate_limit_user_{user.id}"
            else:
                key = f"rate_limit_ip_{request.remote_addr}"
            
            # Apply rate limiting using flask-limiter
            return limiter.limit(limit, key_func=lambda: key)(f)(*args, **kwargs)
        
        return decorated_function
    return decorator


class SecurityValidator:
    """Utility class for security validation"""
    
    @staticmethod
    def validate_user_input(data: Dict[str, Any]) -> tuple:
        """
        Comprehensive validation of user input
        
        Args:
            data (Dict): Input data to validate
            
        Returns:
            tuple: (is_valid: bool, errors: List[str])
        """
        errors = []
        
        # Check for common security issues
        for key, value in data.items():
            if isinstance(value, str):
                # Check for SQL injection
                if InputSanitizer.detect_sql_injection(value):
                    errors.append(f"Invalid characters in field: {key}")
                
                # Check length
                if not InputSanitizer.validate_input_length(value):
                    errors.append(f"Field too long: {key}")
        
        # Validate specific fields
        if 'email' in data:
            if not InputSanitizer.validate_email(data['email']):
                errors.append("Invalid email format")
        
        if 'name' in data:
            if not InputSanitizer.validate_name(data['name']):
                errors.append("Invalid name format")
        
        if 'password' in data:
            is_valid, message = InputSanitizer.validate_password(data['password'])
            if not is_valid:
                errors.append(message)
        
        return len(errors) == 0, errors
    
    @staticmethod
    def log_security_event(event_type: str, details: Dict[str, Any]):
        """
        Log security events for monitoring
        
        Args:
            event_type (str): Type of security event
            details (Dict): Event details
        """
        security_logger = logging.getLogger('security')
        security_logger.warning(f"Security Event: {event_type}", extra={
            'event_type': event_type,
            'details': details,
            'timestamp': datetime.utcnow().isoformat(),
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None
        })


# Security middleware
def security_middleware():
    """Middleware to apply security checks to all requests"""
    
    # Check for suspicious patterns in request
    if request.method in ['POST', 'PUT', 'PATCH']:
        # Check request size
        if request.content_length and request.content_length > SecurityConfig.MAX_INPUT_LENGTH:
            return jsonify({
                'success': False,
                'error': 'Request too large',
                'code': 'REQUEST_TOO_LARGE'
            }), 413
        
        # Check for suspicious headers
        suspicious_headers = ['X-Forwarded-For', 'X-Real-IP']
        for header in suspicious_headers:
            if header in request.headers:
                value = request.headers[header]
                if InputSanitizer.detect_sql_injection(value):
                    SecurityValidator.log_security_event('SUSPICIOUS_HEADER', {
                        'header': header,
                        'value': value
                    })
                    return jsonify({
                        'success': False,
                        'error': 'Suspicious request detected',
                        'code': 'SUSPICIOUS_REQUEST'
                    }), 400


def setup_security_logging():
    """Setup security-specific logging"""
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.WARNING)
    
    # Create security log handler
    handler = logging.FileHandler('logs/security.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    security_logger.addHandler(handler)
    
    return security_logger


# SQL injection prevention utilities
class SQLSafeQuery:
    """Utility class for SQL injection prevention"""
    
    @staticmethod
    def safe_like_query(column, value: str):
        """
        Create safe LIKE query with parameterized values
        
        Args:
            column: SQLAlchemy column
            value (str): Search value
            
        Returns:
            SQLAlchemy filter expression
        """
        # Escape special characters and sanitize
        safe_value = value.replace('%', '\\%').replace('_', '\\_')
        safe_value = InputSanitizer.sanitize_text(safe_value)
        return column.like(f'%{safe_value}%')
    
    @staticmethod
    def validate_order_by(order_field: str, allowed_fields: List[str]) -> str:
        """
        Validate ORDER BY field to prevent injection
        
        Args:
            order_field (str): Field to order by
            allowed_fields (List[str]): List of allowed field names
            
        Returns:
            str: Safe field name or default
        """
        if order_field in allowed_fields:
            return order_field
        return allowed_fields[0] if allowed_fields else 'id'
    
    @staticmethod
    def validate_limit_offset(limit: Any, offset: Any) -> tuple:
        """
        Validate LIMIT and OFFSET values
        
        Args:
            limit: Limit value
            offset: Offset value
            
        Returns:
            tuple: (safe_limit: int, safe_offset: int)
        """
        try:
            safe_limit = min(int(limit) if limit else 50, 1000)  # Max 1000 records
            safe_offset = max(int(offset) if offset else 0, 0)
            return safe_limit, safe_offset
        except (ValueError, TypeError):
            return 50, 0


# CSRF token utilities
class CSRFTokenManager:
    """Utility class for CSRF token management"""
    
    @staticmethod
    def generate_token():
        """Generate CSRF token"""
        return generate_csrf()
    
    @staticmethod
    def validate_token(token: str) -> bool:
        """
        Validate CSRF token
        
        Args:
            token (str): CSRF token to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            validate_csrf(token)
            return True
        except Exception:
            return False


# Security decorators for common patterns
def require_https(f):
    """
    Decorator to require HTTPS for sensitive endpoints
    
    Args:
        f: Function to decorate
        
    Returns:
        Decorated function that requires HTTPS
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_secure and current_app.config.get('ENV') == 'production':
            return jsonify({
                'success': False,
                'error': 'HTTPS required',
                'code': 'HTTPS_REQUIRED'
            }), 400
        
        return f(*args, **kwargs)
    
    return decorated_function


def validate_content_type(allowed_types: List[str] = None):
    """
    Decorator to validate request content type
    
    Args:
        allowed_types (List[str]): List of allowed content types
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not allowed_types:
                return f(*args, **kwargs)
            
            content_type = request.content_type
            if content_type not in allowed_types:
                return jsonify({
                    'success': False,
                    'error': f'Content-Type must be one of: {", ".join(allowed_types)}',
                    'code': 'INVALID_CONTENT_TYPE'
                }), 400
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


# Security audit utilities
class SecurityAuditor:
    """Utility class for security auditing"""
    
    @staticmethod
    def audit_request(request_data: Dict[str, Any]):
        """
        Audit incoming request for security issues
        
        Args:
            request_data (Dict): Request data to audit
            
        Returns:
            Dict: Audit results
        """
        issues = []
        
        # Check for common attack patterns
        for key, value in request_data.items():
            if isinstance(value, str):
                if InputSanitizer.detect_sql_injection(value):
                    issues.append(f"Potential SQL injection in {key}")
                
                # Check for XSS patterns
                xss_patterns = ['<script', 'javascript:', 'onload=', 'onerror=']
                if any(pattern in value.lower() for pattern in xss_patterns):
                    issues.append(f"Potential XSS in {key}")
        
        return {
            'has_issues': len(issues) > 0,
            'issues': issues,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def log_failed_authentication(email: str, ip_address: str):
        """
        Log failed authentication attempt
        
        Args:
            email (str): Email used in failed attempt
            ip_address (str): IP address of attempt
        """
        SecurityValidator.log_security_event('FAILED_AUTH', {
            'email': email,
            'ip_address': ip_address,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @staticmethod
    def log_suspicious_activity(activity_type: str, details: Dict[str, Any]):
        """
        Log suspicious activity
        
        Args:
            activity_type (str): Type of suspicious activity
            details (Dict): Activity details
        """
        SecurityValidator.log_security_event('SUSPICIOUS_ACTIVITY', {
            'activity_type': activity_type,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        })