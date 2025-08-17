"""
Simple test for authentication middleware functionality
"""

import unittest
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth_middleware import (
    jwt_required_custom, admin_required, get_current_user, 
    AuthMiddleware, SessionManager
)
from auth_service import AuthService

class TestAuthMiddlewareComponents(unittest.TestCase):
    """Test individual components of auth middleware"""
    
    def test_auth_service_integration(self):
        """Test that AuthService functions work correctly"""
        # Test email validation
        self.assertTrue(AuthService.validate_uem_email('test@uem.edu.in'))
        self.assertFalse(AuthService.validate_uem_email('test@gmail.com'))
        
        # Test password hashing
        password = 'testpassword123'
        hashed = AuthService.hash_password(password)
        self.assertIsNotNone(hashed)
        self.assertNotEqual(password, hashed)
        
        # Test password verification
        self.assertTrue(AuthService.verify_password(password, hashed))
        self.assertFalse(AuthService.verify_password('wrongpassword', hashed))
    
    def test_password_strength_validation(self):
        """Test password strength validation"""
        # Valid passwords
        valid, msg = AuthService.validate_password_strength('password123')
        self.assertTrue(valid)
        
        # Invalid passwords
        valid, msg = AuthService.validate_password_strength('short')
        self.assertFalse(valid)
        self.assertIn('at least 6 characters', msg)
        
        valid, msg = AuthService.validate_password_strength('password')
        self.assertFalse(valid)
        self.assertIn('contain at least one number', msg)
        
        valid, msg = AuthService.validate_password_strength('123456')
        self.assertFalse(valid)
        self.assertIn('contain at least one letter', msg)
    
    def test_session_manager(self):
        """Test SessionManager utility functions"""
        # Test session creation (mock user object)
        class MockUser:
            def __init__(self):
                self.id = 1
                self.email = 'test@uem.edu.in'
                self.name = 'Test User'
                self.is_admin = False
                self.created_at = None
        
        user = MockUser()
        session_data = SessionManager.create_session(user)
        
        self.assertEqual(session_data['user_id'], 1)
        self.assertEqual(session_data['email'], 'test@uem.edu.in')
        self.assertEqual(session_data['name'], 'Test User')
        self.assertFalse(session_data['is_admin'])
    
    def test_auth_middleware_initialization(self):
        """Test AuthMiddleware can be initialized"""
        middleware = AuthMiddleware()
        self.assertIsNotNone(middleware)
        
        # Test with app parameter as None
        middleware_with_none = AuthMiddleware(None)
        self.assertIsNotNone(middleware_with_none)

if __name__ == '__main__':
    unittest.main()