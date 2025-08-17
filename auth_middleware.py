"""
Authentication middleware and decorators for UEM Placement Platform

This module provides:
- JWT token validation middleware
- Authentication decorators for protected routes
- User session management utilities
- Admin role checking decorators
"""

from functools import wraps
from flask import request, jsonify, g, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from flask_login import current_user
from models import User
import logging

logger = logging.getLogger(__name__)

class AuthMiddleware:
    """Middleware class for handling authentication"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with Flask app"""
        app.before_request(self.load_user_from_token)
    
    def load_user_from_token(self):
        """Load user from JWT token if present in request headers"""
        # Skip for auth endpoints and static files
        if (request.endpoint and 
            (request.endpoint.startswith('auth.') or 
             request.endpoint.startswith('static') or
             request.endpoint in ['health_check', 'index'])):
            return
        
        # Check for Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            try:
                # Verify JWT token
                verify_jwt_in_request()
                user_id = get_jwt_identity()
                
                # Load user and store in g for request context
                user = User.query.get(user_id)
                if user:
                    g.current_user = user
                    g.jwt_claims = get_jwt()
                else:
                    g.current_user = None
                    g.jwt_claims = None
                    
            except Exception as e:
                logger.warning(f"JWT token validation failed: {e}")
                g.current_user = None
                g.jwt_claims = None


def jwt_required_custom(optional=False):
    """
    Custom JWT required decorator that works with both JWT and session auth
    
    Args:
        optional (bool): If True, authentication is optional
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is authenticated via session (Flask-Login)
            if current_user.is_authenticated:
                return f(*args, **kwargs)
            
            # Check JWT token
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                if optional:
                    return f(*args, **kwargs)
                return jsonify({
                    'success': False,
                    'error': 'Authentication required',
                    'code': 'AUTHENTICATION_REQUIRED'
                }), 401
            
            try:
                # Verify JWT token
                verify_jwt_in_request()
                user_id = get_jwt_identity()
                
                # Load user
                user = User.query.get(user_id)
                if not user:
                    if optional:
                        return f(*args, **kwargs)
                    return jsonify({
                        'success': False,
                        'error': 'Invalid token - user not found',
                        'code': 'INVALID_TOKEN'
                    }), 401
                
                # Store user in g for access in route
                g.current_user = user
                g.jwt_claims = get_jwt()
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.warning(f"JWT authentication failed: {e}")
                if optional:
                    return f(*args, **kwargs)
                return jsonify({
                    'success': False,
                    'error': 'Invalid or expired token',
                    'code': 'INVALID_TOKEN'
                }), 401
        
        return decorated_function
    return decorator


def admin_required(f):
    """
    Decorator to require admin privileges
    
    Args:
        f: Function to decorate
        
    Returns:
        Decorated function that checks for admin privileges
    """
    @wraps(f)
    @jwt_required_custom()
    def decorated_function(*args, **kwargs):
        # Get current user (from session or JWT)
        user = None
        if current_user.is_authenticated:
            user = current_user
        elif hasattr(g, 'current_user') and g.current_user:
            user = g.current_user
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTHENTICATION_REQUIRED'
            }), 401
        
        if not user.is_admin:
            return jsonify({
                'success': False,
                'error': 'Admin privileges required',
                'code': 'INSUFFICIENT_PRIVILEGES'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def uem_email_required(f):
    """
    Decorator to ensure user has valid UEM email
    
    Args:
        f: Function to decorate
        
    Returns:
        Decorated function that checks for UEM email
    """
    @wraps(f)
    @jwt_required_custom()
    def decorated_function(*args, **kwargs):
        # Get current user (from session or JWT)
        user = None
        if current_user.is_authenticated:
            user = current_user
        elif hasattr(g, 'current_user') and g.current_user:
            user = g.current_user
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTHENTICATION_REQUIRED'
            }), 401
        
        if not user.is_uem_email():
            return jsonify({
                'success': False,
                'error': 'UEM email required',
                'code': 'INVALID_EMAIL_DOMAIN'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_current_user():
    """
    Get current authenticated user from session or JWT
    
    Returns:
        User object or None if not authenticated
    """
    # Check Flask-Login session first
    if current_user.is_authenticated:
        return current_user
    
    # Check JWT user in g
    if hasattr(g, 'current_user') and g.current_user:
        return g.current_user
    
    return None


def get_jwt_claims():
    """
    Get JWT claims for current request
    
    Returns:
        Dict of JWT claims or None
    """
    if hasattr(g, 'jwt_claims'):
        return g.jwt_claims
    return None


def validate_api_key(api_key_header='X-API-Key'):
    """
    Decorator to validate API key for external integrations
    
    Args:
        api_key_header (str): Header name for API key
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = request.headers.get(api_key_header)
            expected_key = current_app.config.get('API_KEY')
            
            if not expected_key:
                # If no API key is configured, skip validation
                return f(*args, **kwargs)
            
            if not api_key or api_key != expected_key:
                return jsonify({
                    'success': False,
                    'error': 'Invalid API key',
                    'code': 'INVALID_API_KEY'
                }), 401
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def rate_limit_by_user(max_requests=100, window_seconds=3600):
    """
    Decorator to implement rate limiting per user
    
    Args:
        max_requests (int): Maximum requests allowed
        window_seconds (int): Time window in seconds
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                # If no user, apply rate limiting by IP
                client_ip = request.remote_addr
                rate_limit_key = f"rate_limit_ip_{client_ip}"
            else:
                rate_limit_key = f"rate_limit_user_{user.id}"
            
            # Note: This is a basic implementation
            # In production, you'd want to use Redis or similar for rate limiting
            # For now, we'll just log and continue
            logger.info(f"Rate limit check for key: {rate_limit_key}")
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


class SessionManager:
    """Utility class for managing user sessions"""
    
    @staticmethod
    def create_session(user):
        """
        Create session data for user
        
        Args:
            user (User): User object
            
        Returns:
            dict: Session data
        """
        return {
            'user_id': user.id,
            'email': user.email,
            'name': user.name,
            'is_admin': user.is_admin,
            'login_time': user.created_at.isoformat() if user.created_at else None
        }
    
    @staticmethod
    def clear_session():
        """Clear current session data"""
        from flask import session
        session.clear()
    
    @staticmethod
    def is_session_valid():
        """
        Check if current session is valid
        
        Returns:
            bool: True if session is valid
        """
        return current_user.is_authenticated
    
    @staticmethod
    def refresh_session(user):
        """
        Refresh session for user
        
        Args:
            user (User): User object
        """
        # This would typically update last activity time
        # For now, we'll just log the refresh
        logger.info(f"Session refreshed for user: {user.email}")


# Error handlers for authentication errors
def handle_auth_error(error):
    """Handle authentication errors"""
    return jsonify({
        'success': False,
        'error': 'Authentication failed',
        'code': 'AUTH_ERROR',
        'message': str(error)
    }), 401


def handle_permission_error(error):
    """Handle permission errors"""
    return jsonify({
        'success': False,
        'error': 'Insufficient permissions',
        'code': 'PERMISSION_ERROR',
        'message': str(error)
    }), 403