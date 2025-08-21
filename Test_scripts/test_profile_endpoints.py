"""
Unit tests for Profile Routes
"""

import unittest
import json
from datetime import datetime, timedelta
from flask import Flask
from flask_login import login_user
from models import db, User, Test, Question, TestAttempt, ProgressMetrics
from profile_routes import profile_bp
from auth_routes import auth_bp
from config import config

class TestProfileEndpoints(unittest.TestCase):
    """Test cases for profile endpoints"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = Flask(__name__)
        self.app.config.from_object(config['testing'])
        
        # Register blueprints
        self.app.register_blueprint(auth_bp)
        self.app.register_blueprint(profile_bp)
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.init_app(self.app)
        db.create_all()
        
        # Set up Flask-Login
        from flask_login import LoginManager
        login_manager = LoginManager()
        login_manager.init_app(self.app)
        
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))
        
        self.client = self.app.test_client()
        
        # Create test user
        self.test_user = User(
            email='test@uem.edu.in',
            name='Test User',
            year=2024,
            branch='CSE'
        )
        self.test_user.set_password('testpass')
        db.session.add(self.test_user)
        
        # Create test data
        self.test_test = Test(
            company='Test Company',
            year=2025
        )
        db.session.add(self.test_test)
        db.session.commit()
        
        # Store IDs
        self.test_user_id = self.test_user.id
        self.test_test_id = self.test_test.id
        
        # Create test questions
        sections = ['Quantitative Aptitude', 'Logical Reasoning', 'Verbal Ability']
        for i, section in enumerate(sections):
            for j in range(3):  # 3 questions per section
                question = Question(
                    test_id=self.test_test.id,
                    section=section,
                    question_text=f'Test question {i*3 + j + 1}',
                    options=['A', 'B', 'C', 'D'],
                    correct_answer='A',
                    topic=f'Topic {j + 1}'
                )
                db.session.add(question)
        
        db.session.commit()
    
    def tearDown(self):
        """Clean up test environment"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def login_user(self):
        """Helper method to log in test user"""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.test_user_id)
            sess['_fresh'] = True
    
    def test_get_user_stats_no_login(self):
        """Test stats endpoint without login"""
        response = self.client.get('/api/profile/stats')
        self.assertEqual(response.status_code, 401)
    
    def test_get_user_stats_no_data(self):
        """Test stats endpoint with no test data"""
        self.login_user()
        
        response = self.client.get('/api/profile/stats')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['total_tests'], 0)
        self.assertEqual(data['data']['average_score'], 0)
    
    def test_get_user_stats_with_data(self):
        """Test stats endpoint with test data"""
        self.login_user()
        
        # Create test attempts
        attempt1 = TestAttempt(
            user_id=self.test_user_id,
            test_id=self.test_test_id,
            score=8,
            total_questions=9,
            time_taken=1800,
            started_at=datetime.utcnow() - timedelta(days=5),
            completed_at=datetime.utcnow() - timedelta(days=5)
        )
        
        attempt2 = TestAttempt(
            user_id=self.test_user_id,
            test_id=self.test_test_id,
            score=7,
            total_questions=9,
            time_taken=1600,
            started_at=datetime.utcnow() - timedelta(days=2),
            completed_at=datetime.utcnow() - timedelta(days=2)
        )
        
        db.session.add(attempt1)
        db.session.add(attempt2)
        db.session.commit()
        
        response = self.client.get('/api/profile/stats')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['total_tests'], 2)
        self.assertAlmostEqual(data['data']['average_score'], 83.3, places=1)  # (8+7)/(9+9)*100
    
    def test_get_user_progress(self):
        """Test progress endpoint"""
        self.login_user()
        
        # Create test attempt
        attempt = TestAttempt(
            user_id=self.test_user_id,
            test_id=self.test_test_id,
            score=7,
            total_questions=9,
            time_taken=1800,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        db.session.add(attempt)
        db.session.commit()
        
        response = self.client.get('/api/profile/progress')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('user_id', data['data'])
        self.assertIn('total_tests', data['data'])
        self.assertIn('average_score', data['data'])
    
    def test_get_weak_areas(self):
        """Test weak areas endpoint"""
        self.login_user()
        
        # Create progress metrics with weak area
        weak_metric = ProgressMetrics(
            user_id=self.test_user_id,
            subject_area='Quantitative Aptitude',
            accuracy_rate=45.0,  # Below 60% threshold
            total_attempts=5
        )
        db.session.add(weak_metric)
        db.session.commit()
        
        response = self.client.get('/api/profile/weak-areas')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['subject'], 'Quantitative Aptitude')
    
    def test_get_recommendations(self):
        """Test recommendations endpoint"""
        self.login_user()
        
        response = self.client.get('/api/profile/recommendations')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('priority_areas', data['data'])
        self.assertIn('study_plan', data['data'])
        self.assertIn('practice_suggestions', data['data'])
    
    def test_get_test_history_empty(self):
        """Test test history endpoint with no data"""
        self.login_user()
        
        response = self.client.get('/api/profile/test-history')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['attempts']), 0)
        self.assertEqual(data['data']['pagination']['total'], 0)
    
    def test_get_test_history_with_data(self):
        """Test test history endpoint with data"""
        self.login_user()
        
        # Create test attempts
        for i in range(3):
            attempt = TestAttempt(
                user_id=self.test_user_id,
                test_id=self.test_test_id,
                score=7 + i,
                total_questions=9,
                time_taken=1800,
                started_at=datetime.utcnow() - timedelta(days=i),
                completed_at=datetime.utcnow() - timedelta(days=i)
            )
            db.session.add(attempt)
        
        db.session.commit()
        
        response = self.client.get('/api/profile/test-history')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['attempts']), 3)
        self.assertEqual(data['data']['pagination']['total'], 3)
    
    def test_get_test_history_pagination(self):
        """Test test history pagination"""
        self.login_user()
        
        # Create 15 test attempts
        for i in range(15):
            attempt = TestAttempt(
                user_id=self.test_user_id,
                test_id=self.test_test_id,
                score=7,
                total_questions=9,
                time_taken=1800,
                started_at=datetime.utcnow() - timedelta(days=i),
                completed_at=datetime.utcnow() - timedelta(days=i)
            )
            db.session.add(attempt)
        
        db.session.commit()
        
        # Test first page
        response = self.client.get('/api/profile/test-history?page=1&per_page=10')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['attempts']), 10)
        self.assertEqual(data['data']['pagination']['page'], 1)
        self.assertEqual(data['data']['pagination']['total'], 15)
        self.assertTrue(data['data']['pagination']['has_next'])
        
        # Test second page
        response = self.client.get('/api/profile/test-history?page=2&per_page=10')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(len(data['data']['attempts']), 5)
        self.assertEqual(data['data']['pagination']['page'], 2)
        self.assertFalse(data['data']['pagination']['has_next'])
    
    def test_profile_endpoints_exist(self):
        """Test that profile endpoints are properly registered"""
        # Test that the blueprint is registered and endpoints exist
        with self.app.test_request_context():
            # These should not raise exceptions if endpoints exist
            from flask import url_for
            try:
                url_for('profile.get_user_stats')
                url_for('profile.get_user_progress')
                url_for('profile.get_recommendations')
                url_for('profile.get_weak_areas')
                url_for('profile.get_test_history')
                self.assertTrue(True)  # All endpoints exist
            except Exception as e:
                self.fail(f"Profile endpoints not properly registered: {e}")

if __name__ == '__main__':
    unittest.main()