"""
Test file for authentication middleware and decorators
"""

import unittest
import json
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, User
from config import TestingConfig
from auth_middleware import jwt_required_custom, admin_required, get_current_user
from flask import Blueprint, jsonify

# Create test blueprint for testing decorators
test_bp = Blueprint('test', __name__, url_prefix='/test')

@test_bp.route('/protected')
@jwt_required_custom()
def protected_route():
    user = get_current_user()
    return jsonify({
        'success': True,
        'message': 'Access granted',
        'user_id': user.id if user else None
    })

@test_bp.route('/admin-only')
@admin_required
def admin_only_route():
    user = get_current_user()
    return jsonify({
        'success': True,
        'message': 'Admin access granted',
        'user_id': user.id if user else None
    })

@test_bp.route('/optional-auth')
@jwt_required_custom(optional=True)
def optional_auth_route():
    user = get_current_user()
    return jsonify({
        'success': True,
        'message': 'Route accessed',
        'authenticated': user is not None,
        'user_id': user.id if user else None
    })

class TestAuthMiddleware(unittest.TestCase):
    """Test cases for authentication middleware and decorators"""
    
    def setUp(self):
        """Set up test client and database"""
        app.config.from_object(TestingConfig)
        app.register_blueprint(test_bp)
        self.app = app
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
            
            # Create test users
            self.regular_user = User(
                email='user@uem.edu.in',
                name='Regular User',
                is_admin=False
            )
            self.regular_user.set_password('password123')
            
            self.admin_user = User(
                email='admin@uem.edu.in',
                name='Admin User',
                is_admin=True
            )
            self.admin_user.set_password('password123')
            
            db.session.add(self.regular_user)
            db.session.add(self.admin_user)
            db.session.commit()
    
    def tearDown(self):
        """Clean up after tests"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def get_auth_token(self, email, password):
        """Helper method to get authentication token"""
        login_data = {
            'email': email,
            'password': password
        }
        
        response = self.client.post('/api/auth/login',
                                  data=json.dumps(login_data),
                                  content_type='application/json')
        
        if response.status_code == 200:
            response_data = json.loads(response.data)
            return response_data.get('token')
        return None
    
    def test_protected_route_without_token(self):
        """Test accessing protected route without token"""
        response = self.client.get('/test/protected')
        
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['code'], 'AUTHENTICATION_REQUIRED')
    
    def test_protected_route_with_valid_token(self):
        """Test accessing protected route with valid token"""
        # Get token for regular user
        token = self.get_auth_token('user@uem.edu.in', 'password123')
        self.assertIsNotNone(token)
        
        # Access protected route with token
        headers = {'Authorization': f'Bearer {token}'}
        response = self.client.get('/test/protected', headers=headers)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertTrue(response_data['success'])
        self.assertIsNotNone(response_data['user_id'])
    
    def test_protected_route_with_invalid_token(self):
        """Test accessing protected route with invalid token"""
        headers = {'Authorization': 'Bearer invalid_token'}
        response = self.client.get('/test/protected', headers=headers)
        
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['code'], 'INVALID_TOKEN')
    
    def test_admin_route_with_regular_user(self):
        """Test accessing admin route with regular user token"""
        # Get token for regular user
        token = self.get_auth_token('user@uem.edu.in', 'password123')
        self.assertIsNotNone(token)
        
        # Try to access admin route
        headers = {'Authorization': f'Bearer {token}'}
        response = self.client.get('/test/admin-only', headers=headers)
        
        self.assertEqual(response.status_code, 403)
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['code'], 'INSUFFICIENT_PRIVILEGES')
    
    def test_admin_route_with_admin_user(self):
        """Test accessing admin route with admin user token"""
        # Get token for admin user
        token = self.get_auth_token('admin@uem.edu.in', 'password123')
        self.assertIsNotNone(token)
        
        # Access admin route
        headers = {'Authorization': f'Bearer {token}'}
        response = self.client.get('/test/admin-only', headers=headers)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertTrue(response_data['success'])
        self.assertIsNotNone(response_data['user_id'])
    
    def test_optional_auth_without_token(self):
        """Test optional auth route without token"""
        response = self.client.get('/test/optional-auth')
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertTrue(response_data['success'])
        self.assertFalse(response_data['authenticated'])
        self.assertIsNone(response_data['user_id'])
    
    def test_optional_auth_with_token(self):
        """Test optional auth route with token"""
        # Get token for regular user
        token = self.get_auth_token('user@uem.edu.in', 'password123')
        self.assertIsNotNone(token)
        
        # Access optional auth route with token
        headers = {'Authorization': f'Bearer {token}'}
        response = self.client.get('/test/optional-auth', headers=headers)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertTrue(response_data['success'])
        self.assertTrue(response_data['authenticated'])
        self.assertIsNotNone(response_data['user_id'])
    
    def test_malformed_auth_header(self):
        """Test with malformed authorization header"""
        # Missing 'Bearer' prefix
        headers = {'Authorization': 'invalid_format_token'}
        response = self.client.get('/test/protected', headers=headers)
        
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
    
    def test_empty_auth_header(self):
        """Test with empty authorization header"""
        headers = {'Authorization': ''}
        response = self.client.get('/test/protected', headers=headers)
        
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])

if __name__ == '__main__':
    unittest.main()