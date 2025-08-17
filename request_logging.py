"""
Request logging middleware for the UEM Placement Preparation Platform.
Logs all HTTP requests with timing and user information.
"""

import time
import uuid
from flask import Flask, request, g
from flask_login import current_user
from logging_config import log_request, get_logger


class RequestLoggingMiddleware:
    """Middleware to log HTTP requests and responses"""
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.logger = get_logger(__name__)
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize the middleware with the Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_appcontext(self.teardown_request)
    
    def before_request(self):
        """Called before each request"""
        # Generate unique request ID
        g.request_id = str(uuid.uuid4())
        g.start_time = time.time()
        
        # Log request start
        self.logger.debug(f"Request started: {request.method} {request.path}", extra={
            'request_id': g.request_id,
            'method': request.method,
            'endpoint': request.endpoint,
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'content_type': request.content_type,
            'content_length': request.content_length
        })
    
    def after_request(self, response):
        """Called after each request"""
        # Calculate response time
        response_time = time.time() - g.get('start_time', time.time())
        
        # Add request ID to response headers for debugging
        response.headers['X-Request-ID'] = g.get('request_id', 'unknown')
        
        # Log the request
        log_request(request, response, response_time)
        
        # Log slow requests as warnings
        if response_time > 5.0:  # 5 seconds threshold
            self.logger.warning(f"Slow request detected: {request.method} {request.path}", extra={
                'request_id': g.request_id,
                'response_time': response_time * 1000,  # Convert to milliseconds
                'endpoint': request.endpoint,
                'status_code': response.status_code
            })
        
        return response
    
    def teardown_request(self, exception=None):
        """Called when request context is torn down"""
        if exception:
            try:
                self.logger.error(f"Request failed with exception: {str(exception)}", extra={
                    'request_id': g.get('request_id', 'unknown'),
                    'endpoint': getattr(request, 'endpoint', 'unknown'),
                    'method': getattr(request, 'method', 'unknown'),
                    'exception_type': type(exception).__name__
                })
            except RuntimeError:
                # Request context not available
                self.logger.error(f"Request failed with exception: {str(exception)}", extra={
                    'exception_type': type(exception).__name__
                })


def setup_request_logging(app: Flask):
    """Setup request logging for the Flask application"""
    middleware = RequestLoggingMiddleware(app)
    
    # Add custom request context processors
    @app.context_processor
    def inject_request_id():
        """Inject request ID into template context"""
        return {
            'request_id': g.get('request_id', 'unknown')
        }
    
    return middleware