"""
Error handlers for the UEM Placement Preparation Platform.
Provides centralized error handling with proper logging and JSON responses.
"""

import logging
import traceback
from flask import Flask, request, jsonify, render_template
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
import requests

from exceptions import (
    BaseAPIException, AuthenticationError, AuthorizationError,
    ValidationError, ResourceNotFoundError, ExternalServiceError,
    DatabaseError, RateLimitError
)
from logging_config import log_security_event


def register_error_handlers(app: Flask):
    """Register all error handlers with the Flask application"""
    
    logger = logging.getLogger(__name__)
    
    @app.errorhandler(BaseAPIException)
    def handle_api_exception(error: BaseAPIException):
        """Handle custom API exceptions"""
        logger.warning(f"API Exception: {error.code} - {error.message}", extra={
            'error_code': error.code,
            'status_code': error.status_code,
            'details': error.details,
            'endpoint': request.endpoint,
            'method': request.method,
            'ip_address': request.remote_addr
        })
        
        # Log security events for authentication/authorization errors
        if isinstance(error, (AuthenticationError, AuthorizationError)):
            log_security_event(
                event_type=error.code,
                details={
                    'message': error.message,
                    'endpoint': request.endpoint,
                    'method': request.method
                },
                ip_address=request.remote_addr
            )
        
        return jsonify(error.to_dict()), error.status_code
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        """Handle validation errors with detailed field information"""
        logger.info(f"Validation Error: {error.message}", extra={
            'field': error.details.get('field'),
            'value': error.details.get('value'),
            'endpoint': request.endpoint,
            'method': request.method
        })
        
        return jsonify(error.to_dict()), error.status_code
    
    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(error: SQLAlchemyError):
        """Handle SQLAlchemy database errors"""
        logger.error(f"Database Error: {str(error)}", extra={
            'error_type': type(error).__name__,
            'endpoint': request.endpoint,
            'method': request.method
        })
        
        # Rollback the session
        try:
            from models import db
            db.session.rollback()
        except Exception as rollback_error:
            logger.error(f"Failed to rollback session: {rollback_error}")
        
        # Check for specific database errors
        if isinstance(error, IntegrityError):
            # Handle unique constraint violations
            error_message = "A record with this information already exists"
            if "email" in str(error.orig).lower():
                error_message = "An account with this email already exists"
            
            db_error = DatabaseError(
                message=error_message,
                operation="INSERT/UPDATE",
                original_error=error
            )
        else:
            db_error = DatabaseError(
                message="Database operation failed",
                original_error=error
            )
        
        return jsonify(db_error.to_dict()), db_error.status_code
    
    @app.errorhandler(InvalidTokenError)
    def handle_invalid_token(error: InvalidTokenError):
        """Handle JWT token errors"""
        logger.warning(f"Invalid JWT Token: {str(error)}", extra={
            'endpoint': request.endpoint,
            'method': request.method,
            'ip_address': request.remote_addr
        })
        
        log_security_event(
            event_type="INVALID_TOKEN",
            details={
                'error': str(error),
                'endpoint': request.endpoint,
                'method': request.method
            },
            ip_address=request.remote_addr
        )
        
        auth_error = AuthenticationError("Invalid or expired token")
        return jsonify(auth_error.to_dict()), auth_error.status_code
    
    @app.errorhandler(ExpiredSignatureError)
    def handle_expired_token(error: ExpiredSignatureError):
        """Handle expired JWT tokens"""
        logger.info(f"Expired JWT Token: {str(error)}", extra={
            'endpoint': request.endpoint,
            'method': request.method,
            'ip_address': request.remote_addr
        })
        
        auth_error = AuthenticationError("Token has expired")
        return jsonify(auth_error.to_dict()), auth_error.status_code
    
    @app.errorhandler(requests.RequestException)
    def handle_requests_error(error: requests.RequestException):
        """Handle external API request errors"""
        logger.error(f"External API Error: {str(error)}", extra={
            'error_type': type(error).__name__,
            'endpoint': request.endpoint,
            'method': request.method
        })
        
        # Determine which service failed based on the URL or context
        service_name = "External Service"
        if hasattr(error, 'request') and error.request:
            url = error.request.url
            if 'perplexity' in url.lower():
                service_name = "Perplexity AI"
            elif 'gemini' in url.lower() or 'google' in url.lower():
                service_name = "Google Gemini"
        
        external_error = ExternalServiceError(
            service_name=service_name,
            original_error=error
        )
        return jsonify(external_error.to_dict()), external_error.status_code
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 Not Found errors"""
        logger.info(f"404 Not Found: {request.path}", extra={
            'endpoint': request.endpoint,
            'method': request.method,
            'ip_address': request.remote_addr
        })
        
        # Return JSON for API endpoints, HTML for web pages
        if request.path.startswith('/api/'):
            not_found_error = ResourceNotFoundError("Endpoint", request.path)
            return jsonify(not_found_error.to_dict()), 404
        else:
            return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def handle_forbidden(error):
        """Handle 403 Forbidden errors"""
        logger.warning(f"403 Forbidden: {request.path}", extra={
            'endpoint': request.endpoint,
            'method': request.method,
            'ip_address': request.remote_addr
        })
        
        log_security_event(
            event_type="ACCESS_DENIED",
            details={
                'endpoint': request.endpoint,
                'method': request.method,
                'path': request.path
            },
            ip_address=request.remote_addr
        )
        
        # Return JSON for API endpoints, HTML for web pages
        if request.path.startswith('/api/'):
            auth_error = AuthorizationError("Access denied")
            return jsonify(auth_error.to_dict()), 403
        else:
            return render_template('errors/403.html'), 403
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle 405 Method Not Allowed errors"""
        logger.info(f"405 Method Not Allowed: {request.method} {request.path}", extra={
            'endpoint': request.endpoint,
            'method': request.method,
            'ip_address': request.remote_addr
        })
        
        validation_error = ValidationError(
            message=f"Method {request.method} not allowed for this endpoint",
            field="method",
            value=request.method
        )
        return jsonify(validation_error.to_dict()), 405
    
    @app.errorhandler(413)
    def handle_payload_too_large(error):
        """Handle 413 Payload Too Large errors"""
        logger.warning(f"413 Payload Too Large: {request.path}", extra={
            'endpoint': request.endpoint,
            'method': request.method,
            'content_length': request.content_length,
            'ip_address': request.remote_addr
        })
        
        validation_error = ValidationError(
            message="Request payload is too large",
            field="content_length",
            value=request.content_length
        )
        return jsonify(validation_error.to_dict()), 413
    
    @app.errorhandler(429)
    def handle_rate_limit(error):
        """Handle 429 Too Many Requests errors"""
        logger.warning(f"429 Rate Limit Exceeded: {request.path}", extra={
            'endpoint': request.endpoint,
            'method': request.method,
            'ip_address': request.remote_addr
        })
        
        log_security_event(
            event_type="RATE_LIMIT_EXCEEDED",
            details={
                'endpoint': request.endpoint,
                'method': request.method,
                'path': request.path
            },
            ip_address=request.remote_addr
        )
        
        rate_limit_error = RateLimitError(
            limit=100,  # Default limit
            window="hour",
            retry_after=3600
        )
        return jsonify(rate_limit_error.to_dict()), 429
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 Internal Server Error"""
        logger.error(f"500 Internal Server Error: {str(error)}", extra={
            'endpoint': request.endpoint,
            'method': request.method,
            'ip_address': request.remote_addr,
            'traceback': traceback.format_exc()
        })
        
        # Rollback the session
        try:
            from models import db
            db.session.rollback()
        except Exception as rollback_error:
            logger.error(f"Failed to rollback session: {rollback_error}")
        
        # Return JSON for API endpoints, HTML for web pages
        if request.path.startswith('/api/'):
            internal_error = DatabaseError("An unexpected error occurred")
            return jsonify(internal_error.to_dict()), 500
        else:
            return render_template('errors/500.html'), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        """Handle generic HTTP exceptions"""
        logger.warning(f"HTTP Exception {error.code}: {error.description}", extra={
            'status_code': error.code,
            'endpoint': request.endpoint,
            'method': request.method,
            'ip_address': request.remote_addr
        })
        
        # Return JSON for API endpoints, HTML for web pages
        if request.path.startswith('/api/'):
            api_error = BaseAPIException(
                message=error.description or f"HTTP {error.code} error",
                code=f"HTTP_{error.code}",
                status_code=error.code
            )
            return jsonify(api_error.to_dict()), error.code
        else:
            # Try to render custom error template, fallback to default
            try:
                return render_template(f'errors/{error.code}.html'), error.code
            except:
                return render_template('errors/generic.html', error=error), error.code
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        """Handle any unexpected errors"""
        logger.critical(f"Unexpected Error: {str(error)}", extra={
            'error_type': type(error).__name__,
            'endpoint': request.endpoint,
            'method': request.method,
            'ip_address': request.remote_addr,
            'traceback': traceback.format_exc()
        })
        
        # Rollback the session
        try:
            from models import db
            db.session.rollback()
        except Exception as rollback_error:
            logger.error(f"Failed to rollback session: {rollback_error}")
        
        # Return JSON for API endpoints, HTML for web pages
        if request.path.startswith('/api/'):
            internal_error = DatabaseError("An unexpected error occurred")
            return jsonify(internal_error.to_dict()), 500
        else:
            return render_template('errors/500.html'), 500
    
    logger.info("Error handlers registered successfully")