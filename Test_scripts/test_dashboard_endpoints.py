"""
Test Dashboard Endpoints
Tests for dashboard routes functionality
"""

import pytest
import json
from datetime import datetime, timedelta
from app import app
from models import db, User, Test, Question, TestAttempt, ProgressMetrics
from auth_service import AuthService

class TestDashboardEndpoints:
    """Test class for dashboard endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        
        with app.test_client() as client:
            with app.app_context():
                db.create_all()
                yield client
                db.drop_all()
    
    @pytest.fixture
    def test_user(self, client):
        """Create a test user"""
        with app.app_context():
            user = User(
                email='test@uem.edu.in',
                name='Test User',
                year=2025,
                branch='CSE'
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            return user
    
    @pytest.fixture
    def test_data(self, client, test_user):
        """Create test data including tests and attempts"""
        with app.app_context():
            # Create test
            test = Test(
                company='TCS NQT',
                year=2025,
                pattern_data='{"sections": ["Quantitative Aptitude", "Logical Reasoning"]}'
            )
            db.session.add(test)
            db.session.flush()
            
            # Create questions
            questions = [
                Question(
                    test_id=test.id,
                    section='Quantitative Aptitude',
                    question_text='What is 2+2?',
                    options=['3', '4', '5', '6'],
                    correct_answer='4',
                    explanation='Basic addition',
                    difficulty='easy'
                ),
                Question(
                    test_id=test.id,
                    section='Logical Reasoning',
                    question_text='If A > B and B > C, then?',
                    options=['A > C', 'A < C', 'A = C', 'Cannot determine'],
                    correct_answer='A > C',
                    explanation='Transitive property',
                    difficulty='medium'
                )
            ]
            
            for question in questions:
                db.session.add(question)
            
            db.session.flush()
            
            # Create test attempt
            attempt = TestAttempt(
                user_id=test_user.id,
                test_id=test.id,
                score=2,
                total_questions=2,
                time_taken=1800,
                answers={'1': '4', '2': 'A > C'},
                started_at=datetime.utcnow() - timedelta(hours=1),
                completed_at=datetime.utcnow()
            )
            db.session.add(attempt)
            
            # Create progress metrics
            progress = ProgressMetrics(
                user_id=test_user.id,
                subject_area='Quantitative Aptitude',
                accuracy_rate=85.0,
                total_attempts=3
            )
            db.session.add(progress)
            
            db.session.commit()
            
            return {
                'test': test,
                'questions': questions,
                'attempt': attempt,
                'progress': progress
            }
    
    def get_auth_headers(self, user):
        """Get authentication headers for user"""
        token = AuthService.generate_jwt_token(user)
        return {'Authorization': f'Bearer {token}'}
    
    def test_get_dashboard_data_success(self, client, test_user, test_data):
        """Test successful dashboard data retrieval"""
        headers = self.get_auth_headers(test_user)
        
        response = client.get('/api/dashboard', headers=headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Check user info
        assert 'user_info' in data
        assert data['user_info']['name'] == 'Test User'
        assert data['user_info']['email'] == 'test@uem.edu.in'
        
        # Check statistics
        assert 'statistics' in data
        assert data['statistics']['total_tests_taken'] == 1
        assert data['statistics']['average_score'] == 100.0  # 2/2 * 100
        
        # Check recent attempts
        assert 'recent_attempts' in data
        assert len(data['recent_attempts']) == 1
        assert data['recent_attempts'][0]['company'] == 'TCS NQT'
        
        # Check progress by subject
        assert 'progress_by_subject' in data
        assert len(data['progress_by_subject']) == 1
        assert data['progress_by_subject'][0]['subject'] == 'Quantitative Aptitude'
        
        # Check available companies
        assert 'available_companies' in data
        assert len(data['available_companies']) > 0
    
    def test_get_dashboard_data_unauthorized(self, client):
        """Test dashboard data retrieval without authentication"""
        response = client.get('/api/dashboard')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] is True
    
    def test_get_companies_success(self, client, test_user, test_data):
        """Test successful companies retrieval"""
        headers = self.get_auth_headers(test_user)
        
        response = client.get('/api/companies', headers=headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Check response structure
        assert 'companies' in data
        assert 'total_companies' in data
        assert 'user_summary' in data
        
        # Check user summary
        assert data['user_summary']['companies_attempted'] == 1
        assert data['user_summary']['total_attempts'] == 1
        assert data['user_summary']['favorite_company'] == 'TCS NQT'
        
        # Check companies data
        tcs_company = next((c for c in data['companies'] if c['name'] == 'TCS NQT'), None)
        assert tcs_company is not None
        assert tcs_company['test_count'] == 1
        assert 'user_stats' in tcs_company
        assert tcs_company['user_stats']['attempts'] == 1
    
    def test_get_companies_with_sorting(self, client, test_user, test_data):
        """Test companies retrieval with sorting"""
        headers = self.get_auth_headers(test_user)
        
        # Test sort by attempts
        response = client.get('/api/companies?sort_by=attempts', headers=headers)
        assert response.status_code == 200
        
        # Test sort by score
        response = client.get('/api/companies?sort_by=score', headers=headers)
        assert response.status_code == 200
        
        # Test sort by name (default)
        response = client.get('/api/companies?sort_by=name', headers=headers)
        assert response.status_code == 200
    
    def test_get_test_history_success(self, client, test_user, test_data):
        """Test successful test history retrieval"""
        headers = self.get_auth_headers(test_user)
        
        response = client.get('/api/test-history', headers=headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Check response structure
        assert 'attempts' in data
        assert 'pagination' in data
        assert 'summary' in data
        
        # Check attempts data
        assert len(data['attempts']) == 1
        attempt = data['attempts'][0]
        assert attempt['company'] == 'TCS NQT'
        assert attempt['percentage'] == 100.0
        assert 'section_scores' in attempt
        
        # Check pagination
        assert data['pagination']['total'] == 1
        assert data['pagination']['page'] == 1
        
        # Check summary
        assert data['summary']['total_attempts'] == 1
        assert data['summary']['companies_count'] == 1
        assert data['summary']['average_score'] == 100.0
    
    def test_get_test_history_with_filters(self, client, test_user, test_data):
        """Test test history retrieval with filters"""
        headers = self.get_auth_headers(test_user)
        
        # Test company filter
        response = client.get('/api/test-history?company=TCS', headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['attempts']) == 1
        
        # Test date filter
        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
        tomorrow = (datetime.utcnow() + timedelta(days=1)).isoformat()
        
        response = client.get(f'/api/test-history?date_from={yesterday}&date_to={tomorrow}', headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['attempts']) == 1
        
        # Test pagination
        response = client.get('/api/test-history?page=1&per_page=5', headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['pagination']['per_page'] == 5
    
    def test_get_test_history_invalid_date(self, client, test_user):
        """Test test history with invalid date format"""
        headers = self.get_auth_headers(test_user)
        
        response = client.get('/api/test-history?date_from=invalid-date', headers=headers)
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] is True
        assert 'date_from' in data['message']
    
    def test_get_test_history_unauthorized(self, client):
        """Test test history retrieval without authentication"""
        response = client.get('/api/test-history')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] is True

if __name__ == '__main__':
    pytest.main([__file__, '-v'])