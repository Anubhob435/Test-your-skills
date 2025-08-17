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
from security_utils import (
    csrf_protect, sanitize_input, validate_json_input, 
    rate_limit_by_user, SecurityValidator, SecurityAuditor,
    require_https, limiter
)
import logging

logger = logging.getLogger(__name__)

# Create auth blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Web page routes (without /api prefix)
web_auth_bp = Blueprint('web_auth', __name__)

@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per minute")
@csrf_protect
@sanitize_input(['email', 'name', 'branch'])
@validate_json_input(required_fields=['email', 'password', 'name'], optional_fields=['year', 'branch'])
@require_https
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
@limiter.limit("10 per minute")
@csrf_protect
@sanitize_input(['email'])
@validate_json_input(required_fields=['email', 'password'])
@require_https
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
            # Log failed authentication attempt
            SecurityAuditor.log_failed_authentication(email, request.remote_addr)
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
@csrf_protect
@sanitize_input(['name', 'branch'])
@validate_json_input(optional_fields=['name', 'year', 'branch'])
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

# Web page routes for login/register forms
from flask import render_template, redirect, url_for, flash

@web_auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page - GET shows form, POST processes login
    """
    if request.method == 'GET':
        # Show login form
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('auth/login.html')
    
    # Handle POST request (form submission)
    try:
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('auth/login.html')
        
        # Authenticate user
        success, message, user, token = AuthService.authenticate_user(email, password)
        
        if not success:
            SecurityAuditor.log_failed_authentication(email, request.remote_addr)
            flash(message, 'error')
            return render_template('auth/login.html')
        
        # Log in user for session-based auth
        login_user(user)
        flash('Login successful!', 'success')
        
        # Redirect to dashboard or next page
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        flash('Login failed. Please try again.', 'error')
        return render_template('auth/login.html')


@web_auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Registration page - GET shows form, POST processes registration
    """
    if request.method == 'GET':
        # Show registration form
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('auth/register.html')
    
    # Handle POST request (form submission)
    try:
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        name = request.form.get('name', '').strip()
        year = request.form.get('year')
        branch = request.form.get('branch', '').strip() if request.form.get('branch') else None
        
        # Validate required fields
        if not email:
            flash('Email is required.', 'error')
            return render_template('auth/register.html')
        
        if not password:
            flash('Password is required.', 'error')
            return render_template('auth/register.html')
        
        if not name:
            flash('Name is required.', 'error')
            return render_template('auth/register.html')
        
        # Validate password strength
        is_valid_password, password_message = AuthService.validate_password_strength(password)
        if not is_valid_password:
            flash(password_message, 'error')
            return render_template('auth/register.html')
        
        # Validate year if provided
        if year:
            try:
                year = int(year)
                if year < 2020 or year > 2030:
                    flash('Year must be between 2020 and 2030.', 'error')
                    return render_template('auth/register.html')
            except (ValueError, TypeError):
                flash('Year must be a valid number.', 'error')
                return render_template('auth/register.html')
        
        # Register user
        success, message, user = AuthService.register_user(email, password, name, year, branch)
        
        if not success:
            flash(message, 'error')
            return render_template('auth/register.html')
        
        # Log in user for session-based auth
        login_user(user)
        flash('Registration successful! Welcome to UEM Placement Platform.', 'success')
        
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        flash('Registration failed. Please try again.', 'error')
        return render_template('auth/register.html')


@web_auth_bp.route('/logout')
@login_required
def logout():
    """
    Logout user and redirect to home page
    """
    try:
        user_email = current_user.email if current_user.is_authenticated else 'Unknown'
        logout_user()
        session.clear()
        
        flash('You have been logged out successfully.', 'success')
        logger.info(f"User logged out: {user_email}")
        
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        flash('Logout failed. Please try again.', 'error')
        return redirect(url_for('index'))