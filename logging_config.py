"""
Logging configuration for the UEM Placement Preparation Platform.
Provides structured logging with different levels and formatters for development and production.
"""

import os
import logging
import logging.handlers
from datetime import datetime, timezone
from typing import Dict, Any
import json


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created, timezone.utc).isoformat().replace('+00:00', 'Z'),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'ip_address'):
            log_entry['ip_address'] = record.ip_address
        if hasattr(record, 'endpoint'):
            log_entry['endpoint'] = record.endpoint
        if hasattr(record, 'method'):
            log_entry['method'] = record.method
        if hasattr(record, 'status_code'):
            log_entry['status_code'] = record.status_code
        if hasattr(record, 'response_time'):
            log_entry['response_time'] = record.response_time
        
        return json.dumps(log_entry)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for development console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors"""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        
        # Build log message
        log_message = f"{color}[{timestamp}] {record.levelname:8} {record.name}:{record.lineno} - {record.getMessage()}{reset}"
        
        # Add exception information if present
        if record.exc_info:
            log_message += f"\n{self.formatException(record.exc_info)}"
        
        return log_message


def setup_logging(app):
    """Setup logging configuration for the Flask application"""
    
    # Get configuration
    debug_mode = app.config.get('DEBUG', False)
    log_level = app.config.get('LOG_LEVEL', 'INFO' if not debug_mode else 'DEBUG')
    log_dir = app.config.get('LOG_DIR', 'logs')
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler for development
    if debug_mode:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(ColoredFormatter())
        root_logger.addHandler(console_handler)
    
    # File handler for application logs
    app_log_file = os.path.join(log_dir, 'app.log')
    file_handler = logging.handlers.RotatingFileHandler(
        app_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    
    if debug_mode:
        # Use simple format for development
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        # Use JSON format for production
        file_formatter = JSONFormatter()
    
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Error log file for errors and above
    error_log_file = os.path.join(log_dir, 'error.log')
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_handler)
    
    # Access log file for HTTP requests
    access_log_file = os.path.join(log_dir, 'access.log')
    access_handler = logging.handlers.RotatingFileHandler(
        access_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(JSONFormatter())
    
    # Create access logger
    access_logger = logging.getLogger('access')
    access_logger.setLevel(logging.INFO)
    access_logger.addHandler(access_handler)
    access_logger.propagate = False
    
    # Security log file for security events
    security_log_file = os.path.join(log_dir, 'security.log')
    security_handler = logging.handlers.RotatingFileHandler(
        security_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10  # Keep more security logs
    )
    security_handler.setLevel(logging.WARNING)
    security_handler.setFormatter(JSONFormatter())
    
    # Create security logger
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.WARNING)
    security_logger.addHandler(security_handler)
    security_logger.propagate = False
    
    # Suppress noisy third-party loggers in production
    if not debug_mode:
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
    
    app.logger.info("Logging configuration initialized")
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(name)


def log_request(request, response, response_time: float = None):
    """Log HTTP request details"""
    access_logger = logging.getLogger('access')
    
    # Create log record with extra fields
    extra = {
        'method': request.method,
        'endpoint': request.endpoint or request.path,
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', ''),
        'status_code': response.status_code,
        'content_length': response.content_length or 0
    }
    
    if response_time is not None:
        extra['response_time'] = round(response_time * 1000, 2)  # Convert to milliseconds
    
    # Add user ID if available
    try:
        from flask_login import current_user
        if current_user.is_authenticated:
            extra['user_id'] = current_user.id
    except:
        pass
    
    message = f"{request.method} {request.path} - {response.status_code}"
    access_logger.info(message, extra=extra)


def log_security_event(event_type: str, details: Dict[str, Any], user_id: int = None, ip_address: str = None):
    """Log security-related events"""
    security_logger = logging.getLogger('security')
    
    extra = {
        'event_type': event_type,
        'details': details
    }
    
    if user_id:
        extra['user_id'] = user_id
    if ip_address:
        extra['ip_address'] = ip_address
    
    message = f"Security event: {event_type}"
    security_logger.warning(message, extra=extra)


def log_database_operation(operation: str, table: str, record_id: Any = None, user_id: int = None):
    """Log database operations for audit trail"""
    logger = logging.getLogger('database')
    
    extra = {
        'operation': operation,
        'table': table
    }
    
    if record_id is not None:
        extra['record_id'] = str(record_id)
    if user_id:
        extra['user_id'] = user_id
    
    message = f"Database {operation} on {table}"
    if record_id is not None:
        message += f" (ID: {record_id})"
    
    logger.info(message, extra=extra)


def log_external_api_call(service: str, endpoint: str, status_code: int = None, response_time: float = None, error: str = None):
    """Log external API calls"""
    logger = logging.getLogger('external_api')
    
    extra = {
        'service': service,
        'endpoint': endpoint
    }
    
    if status_code is not None:
        extra['status_code'] = status_code
    if response_time is not None:
        extra['response_time'] = round(response_time * 1000, 2)  # Convert to milliseconds
    if error:
        extra['error'] = error
    
    message = f"API call to {service}: {endpoint}"
    if status_code:
        message += f" - {status_code}"
    
    if error:
        logger.error(message, extra=extra)
    else:
        logger.info(message, extra=extra)