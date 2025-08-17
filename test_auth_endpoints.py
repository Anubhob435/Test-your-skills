"""
Test file for authentication endpoints
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

class TestAuthEndpoints(unittest.TestCase):
    """Test cases for authentication endpoints"""
    
    def setUp(self):
        """Set up test client and database"""
        app.config.from_object(TestingConfig)
        self.app = app
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after tests"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_register_valid_user(self):
        """Test successful user registration"""
        data = {
            'email': 'test@uem.edu.in',
            'password': 'password123',
            'name': 'Test User',
            'year': 2025,
            'branch': 'CSE'
        }
        
        response = self.client.post('/api/auth/register', 
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        
        response_data = json.loads(response.data)
        self.assertTrue(response_data['success'])
        self.assertIn('user', response_data)
        self.assertIn('token', response_data)
        self.assertEqual(response_data['user']['email'], 'test@uem.edu.in')
    
    def test_register_invalid_email(self):
        """Test registration with invalid email"""
        data = {
            'email': 'test@gmail.com',
            'password': 'password123',
            'name': 'Test User'
        }
        
        response = self.client.post('/api/auth/register',
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
        self.assertIn('Only @uem.edu.in emails are allowed', response_data['error'])
    
    def test_register_weak_password(self):
        """Test registration with weak password"""
        data = {
            'email': 'test@uem.edu.in',
            'password': '123',
            'name': 'Test User'
        }
        
        response = self.client.post('/api/auth/register',
                                  data=json.dumps(data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
        self.assertIn('Password must be at least 6 characters', response_data['error'])
    
    def test_register_missing_fields(self):
        """Test registration with missing required fields"""
        # Missing email
        data = {'password': 'password123', 'name': 'Test User'}
        response = self.client.post('/api/auth/register',
                                  data=json.dumps(data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        # Missing password
        data = {'email': 'test@uem.edu.in', 'name': 'Test User'}
        response = self.client.post('/api/auth/register',
                                  data=json.dumps(data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        # Missing name
        data = {'email': 'test@uem.edu.in', 'password': 'password123'}
        response = self.client.post('/api/auth/register',
                                  data=json.dumps(data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
    
    def test_login_valid_user(self):
        """Test successful user login"""
        # First register a user
        register_data = {
            'email': 'test@uem.edu.in',
            'password': 'password123',
            'name': 'Test User'
        }
        
        self.client.post('/api/auth/register',
                        data=json.dumps(register_data),
                        content_type='application/json')
        
        # Now login
        login_data = {
            'email': 'test@uem.edu.in',
            'password': 'password123'
        }
        
        response = self.client.post('/api/auth/login',
                                  data=json.dumps(login_data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.data)
        self.assertTrue(response_data['success'])
        self.assertIn('user', response_data)
        self.assertIn('token', response_data)
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        # Register a user first
        register_data = {
            'email': 'test@uem.edu.in',
            'password': 'password123',
            'name': 'Test User'
        }
        
        self.client.post('/api/auth/register',
                        data=json.dumps(register_data),
                        content_type='application/json')
        
        # Try login with wrong password
        login_data = {
            'email': 'test@uem.edu.in',
            'password': 'wrongpassword'
        }
        
        response = self.client.post('/api/auth/login',
                                  data=json.dumps(login_data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
        
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
        self.assertIn('Invalid email or password', response_data['error'])
    
    def test_login_nonexistent_user(self):
        """Test login with non-existent user"""
        login_data = {
            'email': 'nonexistent@uem.edu.in',
            'password': 'password123'
        }
        
        response = self.client.post('/api/auth/login',
                                  data=json.dumps(login_data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
        
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
        self.assertIn('Invalid email or password', response_data['error'])
    
    def test_duplicate_registration(self):
        """Test registration with duplicate email"""
        data = {
            'email': 'test@uem.edu.in',
            'password': 'password123',
            'name': 'Test User'
        }
        
        # First registration
        response1 = self.client.post('/api/auth/register',
                                   data=json.dumps(data),
                                   content_type='application/json')
        self.assertEqual(response1.status_code, 201)
        
        # Second registration with same email
        response2 = self.client.post('/api/auth/register',
                                   data=json.dumps(data),
                                   content_type='application/json')
        self.assertEqual(response2.status_code, 400)
        
        response_data = json.loads(response2.data)
        self.assertFalse(response_data['success'])
        self.assertIn('User with this email already exists', response_data['error'])

if __name__ == '__main__':
    unittest.main()