"""
Integration test for complete authentication system
"""

import unittest
import json
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import db, User
from config import TestingConfig
from auth_routes import auth_bp
from auth_middleware import AuthMiddleware

class TestAuthIntegration(unittest.TestCase):
    """Integration test for authentication system"""
    
    def setUp(self):
        """Set up test app and database"""
        # Create a fresh Flask app for testing
        self.app = Flask(__name__)
        self.app.config.from_object(TestingConfig)
        
        # Initialize extensions
        db.init_app(self.app)
        
        # Register blueprint
        self.app.register_blueprint(auth_bp)
        
        # Initialize middleware
        AuthMiddleware(self.app)
        
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after tests"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_complete_auth_flow(self):
        """Test complete authentication flow"""
        with self.app.app_context():
            # 1. Register a new user
            register_data = {
                'email': 'student@uem.edu.in',
                'password': 'password123',
                'name': 'Test Student',
                'year': 2025,
                'branch': 'CSE'
            }
            
            response = self.client.post('/api/auth/register',
                                      data=json.dumps(register_data),
                                      content_type='application/json')
            
            self.assertEqual(response.status_code, 201)
            register_result = json.loads(response.data)
            self.assertTrue(register_result['success'])
            self.assertIn('token', register_result)
            
            # 2. Login with the registered user
            login_data = {
                'email': 'student@uem.edu.in',
                'password': 'password123'
            }
            
            response = self.client.post('/api/auth/login',
                                      data=json.dumps(login_data),
                                      content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            login_result = json.loads(response.data)
            self.assertTrue(login_result['success'])
            self.assertIn('token', login_result)
            
            # 3. Access profile with token
            token = login_result['token']
            headers = {'Authorization': f'Bearer {token}'}
            
            response = self.client.get('/api/auth/profile', headers=headers)
            self.assertEqual(response.status_code, 200)
            
            profile_result = json.loads(response.data)
            self.assertTrue(profile_result['success'])
            self.assertEqual(profile_result['user']['email'], 'student@uem.edu.in')
            
            # 4. Update profile
            update_data = {
                'name': 'Updated Student Name',
                'year': 2024
            }
            
            response = self.client.put('/api/auth/profile',
                                     data=json.dumps(update_data),
                                     content_type='application/json',
                                     headers=headers)
            
            self.assertEqual(response.status_code, 200)
            update_result = json.loads(response.data)
            self.assertTrue(update_result['success'])
            self.assertEqual(update_result['user']['name'], 'Updated Student Name')
            self.assertEqual(update_result['user']['year'], 2024)
            
            # 5. Verify token
            response = self.client.post('/api/auth/verify-token', headers=headers)
            self.assertEqual(response.status_code, 200)
            
            verify_result = json.loads(response.data)
            self.assertTrue(verify_result['success'])
            self.assertTrue(verify_result['token_valid'])
    
    def test_invalid_operations(self):
        """Test various invalid operations"""
        with self.app.app_context():
            # 1. Try to register with invalid email
            register_data = {
                'email': 'student@gmail.com',
                'password': 'password123',
                'name': 'Test Student'
            }
            
            response = self.client.post('/api/auth/register',
                                      data=json.dumps(register_data),
                                      content_type='application/json')
            
            self.assertEqual(response.status_code, 400)
            
            # 2. Try to login with non-existent user
            login_data = {
                'email': 'nonexistent@uem.edu.in',
                'password': 'password123'
            }
            
            response = self.client.post('/api/auth/login',
                                      data=json.dumps(login_data),
                                      content_type='application/json')
            
            self.assertEqual(response.status_code, 401)
            
            # 3. Try to access profile without token
            response = self.client.get('/api/auth/profile')
            self.assertEqual(response.status_code, 302)  # Redirect to login
            
            # 4. Try to verify invalid token
            headers = {'Authorization': 'Bearer invalid_token'}
            response = self.client.post('/api/auth/verify-token', headers=headers)
            self.assertEqual(response.status_code, 401)

if __name__ == '__main__':
    unittest.main()