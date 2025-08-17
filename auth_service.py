"""
Authentication Service for UEM Placement Platform

This module provides authentication utilities including:
- UEM email validation
- Password hashing and verification
- JWT token management
- User registration and login logic
"""

import re
import bcrypt
from flask_jwt_extended import create_access_token, decode_token
from datetime import datetime, timedelta
from models import User, db
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class AuthService:
    """Service class for handling authentication operations"""
    
    @staticmethod
    def validate_uem_email(email: str) -> bool:
        """
        Validate that email belongs to UEM domain (@uem.edu.in)
        
        Args:
            email (str): Email address to validate
            
        Returns:
            bool: True if email is valid UEM email, False otherwise
        """
        if not email or not isinstance(email, str):
            return False
        
        # Basic email format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False
        
        # Check UEM domain
        return email.lower().endswith('@uem.edu.in')
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt
        
        Args:
            password (str): Plain text password
            
        Returns:
            str: Hashed password
        """
        if not password:
            raise ValueError("Password cannot be empty")
        
        # Generate salt and hash password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Verify password against hash
        
        Args:
            password (str): Plain text password
            hashed_password (str): Hashed password from database
            
        Returns:
            bool: True if password matches, False otherwise
        """
        if not password or not hashed_password:
            return False
        
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'), 
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    @staticmethod
    def generate_jwt_token(user: User) -> str:
        """
        Generate JWT token for user
        
        Args:
            user (User): User object
            
        Returns:
            str: JWT token
        """
        additional_claims = {
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "is_admin": user.is_admin
        }
        
        return create_access_token(
            identity=user.id,
            additional_claims=additional_claims
        )
    
    @staticmethod
    def register_user(email: str, password: str, name: str, year: int = None, branch: str = None) -> tuple:
        """
        Register a new user
        
        Args:
            email (str): User email (must be UEM domain)
            password (str): User password
            name (str): User full name
            year (int, optional): Academic year
            branch (str, optional): Academic branch
            
        Returns:
            tuple: (success: bool, message: str, user: User or None)
        """
        try:
            # Validate email
            if not AuthService.validate_uem_email(email):
                return False, "Invalid email. Only @uem.edu.in emails are allowed.", None
            
            # Check if user already exists
            existing_user = User.query.filter_by(email=email.lower()).first()
            if existing_user:
                return False, "User with this email already exists.", None
            
            # Validate password
            if not password or len(password) < 6:
                return False, "Password must be at least 6 characters long.", None
            
            # Validate name
            if not name or len(name.strip()) < 2:
                return False, "Name must be at least 2 characters long.", None
            
            # Hash password
            hashed_password = AuthService.hash_password(password)
            
            # Create new user
            user = User(
                email=email.lower().strip(),
                password_hash=hashed_password,
                name=name.strip(),
                year=year,
                branch=branch.strip() if branch else None
            )
            
            # Save to database
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"New user registered: {email}")
            return True, "User registered successfully.", user
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {e}")
            return False, "Registration failed. Please try again.", None
    
    @staticmethod
    def authenticate_user(email: str, password: str) -> tuple:
        """
        Authenticate user login
        
        Args:
            email (str): User email
            password (str): User password
            
        Returns:
            tuple: (success: bool, message: str, user: User or None, token: str or None)
        """
        try:
            # Validate inputs
            if not email or not password:
                return False, "Email and password are required.", None, None
            
            # Find user
            user = User.query.filter_by(email=email.lower().strip()).first()
            if not user:
                return False, "Invalid email or password.", None, None
            
            # Verify password
            if not AuthService.verify_password(password, user.password_hash):
                return False, "Invalid email or password.", None, None
            
            # Generate JWT token
            token = AuthService.generate_jwt_token(user)
            
            logger.info(f"User authenticated: {email}")
            return True, "Login successful.", user, token
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False, "Authentication failed. Please try again.", None, None
    
    @staticmethod
    def validate_password_strength(password: str) -> tuple:
        """
        Validate password strength
        
        Args:
            password (str): Password to validate
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        if not password:
            return False, "Password is required."
        
        if len(password) < 6:
            return False, "Password must be at least 6 characters long."
        
        if len(password) > 128:
            return False, "Password must be less than 128 characters."
        
        # Check for at least one letter and one number
        has_letter = any(c.isalpha() for c in password)
        has_number = any(c.isdigit() for c in password)
        
        if not has_letter:
            return False, "Password must contain at least one letter."
        
        if not has_number:
            return False, "Password must contain at least one number."
        
        return True, "Password is valid."


class APIException(Exception):
    """Custom exception for API errors"""
    
    def __init__(self, message: str, code: str, status_code: int = 400, details: dict = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)