"""
Tests for Leaderboard API Endpoints
"""

import pytest
import unittest
import json
from datetime import datetime, timedelta
from models import db, User, Test, Question, TestAttempt
from test_setup import create_test_app

class TestLeaderboardEndpoints(unittest.TestCase):
    """Test cases for leaderboard API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.app = create_test_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Register leaderboard blueprint
        from leaderboard_routes import leaderboard_bp
        self.app.register_blueprint(leaderboard_bp)
        
        self.client = self.app.test_client()
        
        # Create test users
        self.users = []
        for i in range(3):
            user = User(
                email=f'student{i+1}@uem.edu.in',
                name=f'Test Student {i+1}',
                year=2024,
                branch='CSE'
            )
            user.set_password('password123')
            db.session.add(user)
            self.users.append(user)
        
        # Create test with questions
        self.test = Test(
            company='TCS NQT',
            year=2025,
            pattern_data='{"sections": ["Quantitative", "Logical"]}'
        )
        db.session.add(self.test)
        db.session.commit()
        
        # Create questions
        for i in range(10):
            question = Question(
                test_id=self.test.id,
                section='Quantitative' if i < 5 else 'Logical',
                question_text=f'Test question {i+1}',
                options=['A', 'B', 'C', 'D'],
                correct_answer='A',
                explanation='Test explanation'
            )
            db.session.add(question)
        
        db.session.commit()
        
        # Create test attempts (3 per user to qualify for leaderboard)
        scores = [8, 7, 6]  # Out of 10 questions
        for i, user in enumerate(self.users):
            for attempt_num in range(3):
                attempt = TestAttempt(
                    user_id=user.id,
                    test_id=self.test.id,
                    score=scores[i] + attempt_num * 0.5,
                    total_questions=10,
                    time_taken=1800 - (i * 100),
                    answers={'1': 'A', '2': 'B'},
                    started_at=datetime.utcnow() - timedelta(days=attempt_num),
                    completed_at=datetime.utcnow() - timedelta(days=attempt_num) + timedelta(hours=1)
                )
                db.session.add(attempt)
        
        db.session.commit()
    
    def tearDown(self):
        """Clean up after tests"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def login_user(self, user_id):
        """Helper method to login a user for testing"""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['_fresh'] = True
    
    def test_get_leaderboard_endpoint(self):
        """Test GET /api/leaderboard/ endpoint"""
        # Login as first user
        self.login_user(self.users[0].id)
        
        response = self.client.get('/api/leaderboard/')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        leaderboard_data = data['data']
        self.assertIn('leaderboard', leaderboard_data)
        self.assertIn('pagination', leaderboard_data)
        
        # Should have all 3 users
        self.assertEqual(len(leaderboard_data['leaderboard']), 3)
        
        # Check first entry structure
        first_entry = leaderboard_data['leaderboard'][0]
        required_fields = ['rank', 'name', 'year', 'branch', 'total_tests', 'average_score']
        for field in required_fields:
            self.assertIn(field, first_entry)
    
    def test_get_leaderboard_with_pagination(self):
        """Test leaderboard endpoint with pagination parameters"""
        self.login_user(self.users[0].id)
        
        # Test with limit parameter
        response = self.client.get('/api/leaderboard/?limit=2&page=1')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        leaderboard_data = data['data']
        
        # Should have only 2 users
        self.assertEqual(len(leaderboard_data['leaderboard']), 2)
        
        # Check pagination info
        pagination = leaderboard_data['pagination']
        self.assertEqual(pagination['current_page'], 1)
        self.assertEqual(pagination['per_page'], 2)
        self.assertTrue(pagination['has_next'])
        self.assertFalse(pagination['has_prev'])
    
    def test_get_leaderboard_with_filters(self):
        """Test leaderboard endpoint with filter parameters"""
        self.login_user(self.users[0].id)
        
        # Test company filter
        response = self.client.get('/api/leaderboard/?company=TCS NQT')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Test year filter
        response = self.client.get('/api/leaderboard/?year=2024')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Test branch filter
        response = self.client.get('/api/leaderboard/?branch=CSE')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
    
    def test_get_user_position_endpoint(self):
        """Test GET /api/leaderboard/position endpoint"""
        self.login_user(self.users[0].id)
        
        response = self.client.get('/api/leaderboard/position')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        position_data = data['data']
        self.assertIn('user_position', position_data)
        self.assertIn('nearby_competitors', position_data)
        
        # User should have a position (since they have 3+ tests)
        self.assertIsNotNone(position_data['user_position'])
        self.assertGreater(position_data['user_position'], 0)
    
    def test_get_leaderboard_filters_endpoint(self):
        """Test GET /api/leaderboard/filters endpoint"""
        self.login_user(self.users[0].id)
        
        response = self.client.get('/api/leaderboard/filters')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        filters = data['data']
        self.assertIn('companies', filters)
        self.assertIn('years', filters)
        self.assertIn('branches', filters)
        
        # Should contain our test data
        self.assertIn('TCS NQT', filters['companies'])
        self.assertIn(2024, filters['years'])
        self.assertIn('CSE', filters['branches'])
    
    def test_get_leaderboard_stats_endpoint(self):
        """Test GET /api/leaderboard/stats endpoint"""
        self.login_user(self.users[0].id)
        
        response = self.client.get('/api/leaderboard/stats')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        stats = data['data']
        required_fields = ['total_participants', 'total_tests_taken', 'platform_average', 'highest_score']
        for field in required_fields:
            self.assertIn(field, stats)
        
        # Should have 3 participants
        self.assertEqual(stats['total_participants'], 3)
        
        # Should have 9 total tests (3 users × 3 tests each)
        self.assertEqual(stats['total_tests_taken'], 9)
    
    def test_unauthorized_access(self):
        """Test that endpoints require authentication"""
        # Don't login any user
        
        endpoints = [
            '/api/leaderboard/',
            '/api/leaderboard/position',
            '/api/leaderboard/filters',
            '/api/leaderboard/stats'
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            # Should redirect to login or return 401
            self.assertIn(response.status_code, [302, 401])
    
    def test_leaderboard_page_endpoint(self):
        """Test GET /api/leaderboard/page endpoint"""
        self.login_user(self.users[0].id)
        
        response = self.client.get('/api/leaderboard/page')
        self.assertEqual(response.status_code, 200)
        
        # Should return HTML content
        self.assertIn(b'html', response.data.lower())

if __name__ == '__main__':
    pytest.main([__file__])