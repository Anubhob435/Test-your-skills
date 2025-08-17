"""
Authentication routes for UEM Placement Platform

This module provides REST API endpoints for:
- User registration
- User login
- User logout
- Profile management
"""

from flask import Blueprint, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from auth_service import AuthService, APIException
from models import User, db
import logging

logger = logging.getLogger(__name__)

# Create auth blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new UEM student
    
    Expected JSON payload:
    {
        "email": "student@uem.edu.in",
        "password": "password123",
        "name": "Student Name",
        "year": 2025,  # optional
        "branch": "CSE"  # optional
    }
    
    Returns:
        JSON response with success/error message and user data
    """
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            raise APIException("No data provided", "INVALID_REQUEST", 400)
        
        # Extract required fields
        email = data.get('email', '').strip()
        password = data.get('password', '')
        name = data.get('name', '').strip()
        year = data.get('year')
        branch = data.get('branch', '').strip() if data.get('branch') else None
        
        # Validate required fields
        if not email:
            raise APIException("Email is required", "MISSING_EMAIL", 400)
        
        if not password:
            raise APIException("Password is required", "MISSING_PASSWORD", 400)
        
        if not name:
            raise APIException("Name is required", "MISSING_NAME", 400)
        
        # Validate password strength
        is_valid_password, password_message = AuthService.validate_password_strength(password)
        if not is_valid_password:
            raise APIException(password_message, "WEAK_PASSWORD", 400)
        
        # Validate year if provided
        if year is not None:
            try:
                year = int(year)
                if year < 2020 or year > 2030:
                    raise APIException("Year must be between 2020 and 2030", "INVALID_YEAR", 400)
            except (ValueError, TypeError):
                raise APIException("Year must be a valid number", "INVALID_YEAR", 400)
        
        # Register user
        success, message, user = AuthService.register_user(email, password, name, year, branch)
        
        if not success:
            raise APIException(message, "REGISTRATION_FAILED", 400)
        
        # Generate JWT token
        token = AuthService.generate_jwt_token(user)
        
        # Log in user for session-based auth as well
        login_user(user)
        
        logger.info(f"User registered successfully: {email}")
        
        return jsonify({
            'success': True,
            'message': message,
            'user': user.to_dict(),
            'token': token
        }), 201
        
    except APIException as e:
        logger.warning(f"Registration failed: {e.message}")
        return jsonify({
            'success': False,
            'error': e.message,
            'code': e.code
        }), e.status_code
        
    except Exception as e:
        logger.error(f"Unexpected registration error: {e}")
        return jsonify({
            'success': False,
            'error': 'Registration failed. Please try again.',
            'code': 'INTERNAL_ERROR'
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user login
    
    Expected JSON payload:
    {
        "email": "student@uem.edu.in",
        "password": "password123"
    }
    
    Returns:
        JSON response with success/error message, user data, and JWT token
    """
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            raise APIException("No data provided", "INVALID_REQUEST", 400)
        
        # Extract credentials
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        # Validate required fields
        if not email:
            raise APIException("Email is required", "MISSING_EMAIL", 400)
        
        if not password:
            raise APIException("Password is required", "MISSING_PASSWORD", 400)
        
        # Authenticate user
        success, message, user, token = AuthService.authenticate_user(email, password)
        
        if not success:
            raise APIException(message, "AUTHENTICATION_FAILED", 401)
        
        # Log in user for session-based auth as well
        login_user(user)
        
        logger.info(f"User logged in successfully: {email}")
        
        return jsonify({
            'success': True,
            'message': message,
            'user': user.to_dict(),
            'token': token
        }), 200
        
    except APIException as e:
        logger.warning(f"Login failed: {e.message}")
        return jsonify({
            'success': False,
            'error': e.message,
            'code': e.code
        }), e.status_code
        
    except Exception as e:
        logger.error(f"Unexpected login error: {e}")
        return jsonify({
            'success': False,
            'error': 'Login failed. Please try again.',
            'code': 'INTERNAL_ERROR'
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """
    Logout current user
    
    Returns:
        JSON response confirming logout
    """
    try:
        user_email = current_user.email if current_user.is_authenticated else 'Unknown'
        
        # Logout user from session
        logout_user()
        
        # Clear any session data
        session.clear()
        
        logger.info(f"User logged out: {user_email}")
        
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({
            'success': False,
            'error': 'Logout failed. Please try again.',
            'code': 'LOGOUT_ERROR'
        }), 500

@auth_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """
    Get current user profile
    
    Returns:
        JSON response with user profile data
    """
    try:
        return jsonify({
            'success': True,
            'user': current_user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Profile retrieval error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve profile',
            'code': 'PROFILE_ERROR'
        }), 500

@auth_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """
    Update current user profile
    
    Expected JSON payload:
    {
        "name": "Updated Name",
        "year": 2025,
        "branch": "CSE"
    }
    
    Returns:
        JSON response with updated user data
    """
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            raise APIException("No data provided", "INVALID_REQUEST", 400)
        
        # Update allowed fields
        if 'name' in data:
            name = data['name'].strip()
            if not name or len(name) < 2:
                raise APIException("Name must be at least 2 characters long", "INVALID_NAME", 400)
            current_user.name = name
        
        if 'year' in data:
            year = data['year']
            if year is not None:
                try:
                    year = int(year)
                    if year < 2020 or year > 2030:
                        raise APIException("Year must be between 2020 and 2030", "INVALID_YEAR", 400)
                    current_user.year = year
                except (ValueError, TypeError):
                    raise APIException("Year must be a valid number", "INVALID_YEAR", 400)
        
        if 'branch' in data:
            branch = data['branch']
            current_user.branch = branch.strip() if branch else None
        
        # Save changes
        db.session.commit()
        
        logger.info(f"Profile updated for user: {current_user.email}")
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': current_user.to_dict()
        }), 200
        
    except APIException as e:
        db.session.rollback()
        logger.warning(f"Profile update failed: {e.message}")
        return jsonify({
            'success': False,
            'error': e.message,
            'code': e.code
        }), e.status_code
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected profile update error: {e}")
        return jsonify({
            'success': False,
            'error': 'Profile update failed. Please try again.',
            'code': 'INTERNAL_ERROR'
        }), 500

@auth_bp.route('/verify-token', methods=['POST'])
@jwt_required()
def verify_token():
    """
    Verify JWT token and return user info
    
    Returns:
        JSON response with user data if token is valid
    """
    try:
        # Get user ID from JWT
        user_id = get_jwt_identity()
        
        # Get user from database
        user = User.query.get(user_id)
        if not user:
            raise APIException("User not found", "USER_NOT_FOUND", 404)
        
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'token_valid': True
        }), 200
        
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return jsonify({
            'success': False,
            'error': 'Invalid token',
            'code': 'INVALID_TOKEN',
            'token_valid': False
        }), 401

# Error handlers for the auth blueprint
@auth_bp.errorhandler(APIException)
def handle_api_exception(error):
    """Handle custom API exceptions"""
    return jsonify({
        'success': False,
        'error': error.message,
        'code': error.code,
        'details': error.details
    }), error.status_code

@auth_bp.errorhandler(400)
def handle_bad_request(error):
    """Handle bad request errors"""
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'code': 'BAD_REQUEST'
    }), 400

@auth_bp.errorhandler(401)
def handle_unauthorized(error):
    """Handle unauthorized errors"""
    return jsonify({
        'success': False,
        'error': 'Unauthorized access',
        'code': 'UNAUTHORIZED'
    }), 401

@auth_bp.errorhandler(500)
def handle_internal_error(error):
    """Handle internal server errors"""
    logger.error(f"Internal server error in auth routes: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'code': 'INTERNAL_ERROR'
    }), 500