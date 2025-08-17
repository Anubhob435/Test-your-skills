# Error Handling and Logging System

This document describes the comprehensive error handling and logging system implemented for the UEM Placement Preparation Platform.

## Overview

The error handling system provides:
- **Custom Exception Classes**: Structured error types with consistent formatting
- **Centralized Error Handlers**: Flask error handlers for all error types
- **Comprehensive Logging**: Multi-level logging with JSON formatting for production
- **Request Tracking**: Request ID tracking and performance monitoring
- **Security Logging**: Security event tracking and audit trails
- **Error Templates**: User-friendly error pages for web interface

## Components

### 1. Custom Exceptions (`exceptions.py`)

#### Base Exception Class
```python
from exceptions import BaseAPIException

# Create custom error
error = BaseAPIException(
    message="Something went wrong",
    code="CUSTOM_ERROR",
    status_code=400,
    details={'field': 'value'}
)

# Convert to JSON response
return jsonify(error.to_dict()), error.status_code
```

#### Available Exception Types

| Exception | Status Code | Use Case |
|-----------|-------------|----------|
| `ValidationError` | 400 | Input validation failures |
| `AuthenticationError` | 401 | Login/token failures |
| `AuthorizationError` | 403 | Permission denied |
| `ResourceNotFoundError` | 404 | Missing resources |
| `DuplicateResourceError` | 409 | Unique constraint violations |
| `RateLimitError` | 429 | Rate limiting |
| `ExternalServiceError` | 503 | External API failures |
| `DatabaseError` | 500 | Database operation failures |
| `InvalidEmailDomainError` | 400 | Non-UEM email addresses |

#### Example Usage
```python
from exceptions import ValidationError, InvalidEmailDomainError

# Validation error with field details
raise ValidationError(
    message="Password too short",
    field="password",
    value="123"
)

# Email domain validation
if not email.endswith('@uem.edu.in'):
    raise InvalidEmailDomainError(email)
```

### 2. Error Utilities (`error_utils.py`)

#### Validation Functions
```python
from error_utils import validate_uem_email, validate_required_fields, validate_field_length

# Email validation
validate_uem_email("student@uem.edu.in")  # Returns True or raises InvalidEmailDomainError

# Required fields validation
data = {'name': 'John', 'email': 'john@uem.edu.in'}
validate_required_fields(data, ['name', 'email', 'password'])  # Raises ValidationError if missing

# Field length validation
validate_field_length("password123", "password", min_length=8, max_length=20)
```

#### Decorators
```python
from error_utils import require_authentication, require_admin, retry_external_api_call

@require_authentication
def protected_endpoint():
    """Requires user to be logged in"""
    pass

@require_admin
def admin_endpoint():
    """Requires admin privileges"""
    pass

@retry_external_api_call(max_retries=3, delay=1.0)
def call_external_api():
    """Automatically retries on network failures"""
    pass

@validate_json_request(required_fields=['email', 'password'])
def register_user(json_data):
    """Validates JSON request data"""
    email = json_data['email']
    password = json_data['password']
```

### 3. Logging Configuration (`logging_config.py`)

#### Log Levels and Files

| Logger | File | Level | Purpose |
|--------|------|-------|---------|
| Root | `app.log` | INFO+ | General application logs |
| Error | `error.log` | ERROR+ | Error and critical events |
| Access | `access.log` | INFO | HTTP request logs |
| Security | `security.log` | WARNING+ | Security events |

#### Logging Functions
```python
from logging_config import get_logger, log_security_event, log_external_api_call

# Get logger instance
logger = get_logger(__name__)
logger.info("Application started")

# Log security events
log_security_event(
    event_type="FAILED_LOGIN",
    details={'email': 'user@uem.edu.in'},
    user_id=123,
    ip_address='192.168.1.1'
)

# Log external API calls
log_external_api_call(
    service="Perplexity AI",
    endpoint="/api/search",
    status_code=200,
    response_time=1.5
)
```

#### JSON Log Format (Production)
```json
{
  "timestamp": "2025-01-17T10:30:00Z",
  "level": "ERROR",
  "logger": "auth_service",
  "message": "Login failed for user",
  "module": "auth_service",
  "function": "authenticate_user",
  "line": 45,
  "user_id": 123,
  "ip_address": "192.168.1.1",
  "endpoint": "auth.login"
}
```

### 4. Error Handlers (`error_handlers.py`)

Error handlers are automatically registered and provide consistent JSON responses for API endpoints and HTML pages for web routes.

#### API Error Response Format
```json
{
  "error": true,
  "message": "Human-readable error message",
  "code": "ERROR_CODE",
  "details": {
    "field": "specific field that caused error",
    "value": "invalid value"
  },
  "timestamp": "2025-01-17T10:30:00Z"
}
```

### 5. Request Logging (`request_logging.py`)

Automatically logs all HTTP requests with:
- Request ID for tracking
- Response time measurement
- User information (if authenticated)
- Slow request detection (>5 seconds)

#### Request Log Example
```json
{
  "timestamp": "2025-01-17T10:30:00Z",
  "level": "INFO",
  "logger": "access",
  "message": "POST /api/auth/login - 200",
  "method": "POST",
  "endpoint": "auth.login",
  "ip_address": "192.168.1.1",
  "status_code": 200,
  "response_time": 245.5,
  "user_id": 123
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Minimum log level |
| `LOG_DIR` | `logs` | Directory for log files |

### Flask Configuration
```python
# config.py
class Config:
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_DIR = os.environ.get('LOG_DIR', 'logs')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
```

## Error Templates

User-friendly error pages are provided for web interface:
- `templates/errors/404.html` - Page not found
- `templates/errors/403.html` - Access denied
- `templates/errors/500.html` - Server error
- `templates/errors/generic.html` - Generic error template

## Security Features

### Security Event Logging
All security-related events are logged to `security.log`:
- Failed login attempts
- Unauthorized access attempts
- Rate limit violations
- Invalid token usage
- Admin privilege escalation attempts

### Rate Limiting
Basic rate limiting is implemented:
```python
from error_utils import rate_limit

@rate_limit(requests_per_minute=60)
def api_endpoint():
    """Limited to 60 requests per minute per IP"""
    pass
```

## Testing

Run the error handling tests:
```bash
python -m pytest test_error_handling.py -v
```

## Demo

Run the interactive demo to see error handling in action:
```bash
python demo_error_handling.py
```

This starts a demo server on `http://localhost:5001` with various endpoints that demonstrate different error scenarios.

## Integration

The error handling system is automatically integrated into the main Flask application:

```python
# app.py
from logging_config import setup_logging
from error_handlers import register_error_handlers
from request_logging import setup_request_logging

# Setup logging first
setup_logging(app)

# Register error handlers
register_error_handlers(app)

# Setup request logging
setup_request_logging(app)
```

## Best Practices

### 1. Use Appropriate Exception Types
```python
# Good
raise ValidationError("Invalid email format", field="email", value=email)

# Avoid
raise Exception("Something went wrong")
```

### 2. Include Context in Errors
```python
# Good
raise ResourceNotFoundError("User", user_id)

# Avoid
raise ResourceNotFoundError("Not found")
```

### 3. Log Security Events
```python
# Always log security-related events
log_security_event(
    event_type="FAILED_LOGIN",
    details={'email': email, 'reason': 'invalid_password'},
    ip_address=request.remote_addr
)
```

### 4. Use Decorators for Common Patterns
```python
# Use decorators for validation
@validate_json_request(required_fields=['email', 'password'])
@require_authentication
def update_profile(json_data):
    pass
```

### 5. Handle External API Failures Gracefully
```python
@retry_external_api_call(max_retries=3)
def call_perplexity_api():
    try:
        # API call
        pass
    except requests.RequestException as e:
        raise ExternalServiceError("Perplexity AI", original_error=e)
```

## Monitoring and Alerting

### Log Analysis
- Monitor `error.log` for application errors
- Monitor `security.log` for security incidents
- Track response times in `access.log`
- Set up alerts for critical errors

### Key Metrics to Monitor
- Error rate by endpoint
- Response time percentiles
- Failed authentication attempts
- Rate limit violations
- External service failures

## Production Considerations

1. **Log Rotation**: Logs are automatically rotated (10MB max, 5 backups)
2. **Performance**: JSON logging adds minimal overhead
3. **Security**: Sensitive data is not logged
4. **Storage**: Monitor log directory disk usage
5. **Alerting**: Set up monitoring for critical errors

This error handling system provides robust, production-ready error management with comprehensive logging and monitoring capabilities.