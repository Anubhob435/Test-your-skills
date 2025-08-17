"""
Tests for Test Management Endpoints
Tests the test creation, retrieval, and submission functionality
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from test_setup import create_test_app, create_test_user, create_test_data
from models import db, User, Test, Question, TestAttempt, ProgressMetrics
from question_generation_service import QuestionGenerationService


class TestTestEndpoints:
    """Test class for test management endpoints"""
    
    @pytest.fixture
    def app(self):
        """Create test application"""
        return create_test_app()
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    @pytest.fixture
    def auth_headers(self, app, client):
        """Create authenticated user and return auth headers"""
        with app.app_context():
            user = create_test_user()
            
            # Login to get token
            login_response = client.post('/api/auth/login', 
                json={
                    'email': user.email,
                    'password': 'testpass123'
                })
            
            assert login_response.status_code == 200
            token = login_response.json['access_token']
            
            return {'Authorization': f'Bearer {token}'}
    
    @pytest.fixture
    def admin_headers(self, app, client):
        """Create admin user and return auth headers"""
        with app.app_context():
            user = create_test_user(email='admin@uem.edu.in', is_admin=True)
            
            # Login to get token
            login_response = client.post('/api/auth/login', 
                json={
                    'email': user.email,
                    'password': 'testpass123'
                })
            
            assert login_response.status_code == 200
            token = login_response.json['access_token']
            
            return {'Authorization': f'Bearer {token}'}
    
    @pytest.fixture
    def sample_test_data(self, app):
        """Create sample test data"""
        with app.app_context():
            return create_test_data()

    def test_generate_test_success(self, app, client, auth_headers):
        """Test successful test generation"""
        with app.app_context():
            # Mock the question generation service
            mock_result = {
                'test_id': 1,
                'company': 'TCS NQT',
                'year': 2025,
                'num_questions': 10,
                'created_at': datetime.utcnow().isoformat(),
                'from_cache': False,
                'generation_time': 30.5,
                'success': True,
                'sections': ['Quantitative Aptitude', 'Logical Reasoning']
            }
            
            with patch.object(QuestionGenerationService, 'generate_test_sync', return_value=mock_result):
                response = client.post('/api/tests/generate/TCS%20NQT',
                    json={'num_questions': 10},
                    headers=auth_headers)
                
                assert response.status_code == 201
                data = response.json
                assert data['success'] is True
                assert data['company'] == 'TCS NQT'
                assert data['num_questions'] == 10
                assert 'config' in data
                assert 'time_limit_minutes' in data['config']

    def test_generate_test_invalid_company(self, app, client, auth_headers):
        """Test test generation with invalid company name"""
        with app.app_context():
            response = client.post('/api/tests/generate/',
                json={'num_questions': 10},
                headers=auth_headers)
            
            assert response.status_code == 404  # Route not found for empty company

    def test_generate_test_invalid_question_count(self, app, client, auth_headers):
        """Test test generation with invalid question count"""
        with app.app_context():
            response = client.post('/api/tests/generate/TCS%20NQT',
                json={'num_questions': 100},  # Too many questions
                headers=auth_headers)
            
            assert response.status_code == 400
            data = response.json
            assert data['error'] is True
            assert 'question' in data['message'].lower()

    def test_generate_test_unauthorized(self, app, client):
        """Test test generation without authentication"""
        with app.app_context():
            response = client.post('/api/tests/generate/TCS%20NQT',
                json={'num_questions': 10})
            
            assert response.status_code == 401

    def test_get_test_success(self, app, client, auth_headers, sample_test_data):
        """Test successful test retrieval"""
        with app.app_context():
            test, questions = sample_test_data
            
            response = client.get(f'/api/tests/{test.id}',
                headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json
            assert data['test_id'] == test.id
            assert data['company'] == test.company
            assert data['total_questions'] == len(questions)
            assert 'sections' in data
            assert len(data['sections']) > 0
            
            # Check that answers are not included for regular users
            first_question = data['sections'][0]['questions'][0]
            assert 'correct_answer' not in first_question

    def test_get_test_with_answers_admin(self, app, client, admin_headers, sample_test_data):
        """Test test retrieval with answers for admin"""
        with app.app_context():
            test, questions = sample_test_data
            
            response = client.get(f'/api/tests/{test.id}?include_answers=true',
                headers=admin_headers)
            
            assert response.status_code == 200
            data = response.json
            
            # Check that answers are included for admin
            first_question = data['sections'][0]['questions'][0]
            assert 'correct_answer' in first_question
            assert 'explanation' in first_question

    def test_get_test_with_answers_non_admin(self, app, client, auth_headers, sample_test_data):
        """Test test retrieval with answers for non-admin (should be denied)"""
        with app.app_context():
            test, questions = sample_test_data
            
            response = client.get(f'/api/tests/{test.id}?include_answers=true',
                headers=auth_headers)
            
            assert response.status_code == 403
            data = response.json
            assert data['error'] is True
            assert 'permission' in data['message'].lower()

    def test_get_test_not_found(self, app, client, auth_headers):
        """Test retrieval of non-existent test"""
        with app.app_context():
            response = client.get('/api/tests/99999',
                headers=auth_headers)
            
            assert response.status_code == 404
            data = response.json
            assert data['error'] is True
            assert 'not found' in data['message'].lower()

    def test_get_test_section_filter(self, app, client, auth_headers, sample_test_data):
        """Test test retrieval with section filter"""
        with app.app_context():
            test, questions = sample_test_data
            
            response = client.get(f'/api/tests/{test.id}?section=Quantitative',
                headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json
            
            # Should only return questions from Quantitative Aptitude section
            for section in data['sections']:
                assert 'quantitative' in section['section_name'].lower()

    def test_submit_test_success(self, app, client, auth_headers, sample_test_data):
        """Test successful test submission"""
        with app.app_context():
            test, questions = sample_test_data
            
            # Prepare answers (some correct, some incorrect)
            answers = {}
            for i, question in enumerate(questions[:3]):  # Answer first 3 questions
                if i == 0:
                    answers[str(question.id)] = question.correct_answer  # Correct
                else:
                    # Incorrect answer (pick different option)
                    options = ['A', 'B', 'C', 'D']
                    incorrect_options = [opt for opt in options if opt != question.correct_answer]
                    answers[str(question.id)] = incorrect_options[0]
            
            submission_data = {
                'answers': answers,
                'time_taken': 1800,  # 30 minutes
                'started_at': datetime.utcnow().isoformat()
            }
            
            response = client.post(f'/api/tests/{test.id}/submit',
                json=submission_data,
                headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json
            
            assert 'attempt_id' in data
            assert data['total_questions'] == len(questions)
            assert data['score'] == 1  # Only first answer was correct
            assert data['percentage'] == 20.0  # 1/5 * 100
            assert data['time_taken'] == 1800
            assert 'results' in data
            assert 'section_scores' in data
            
            # Verify test attempt was saved
            attempt = TestAttempt.query.get(data['attempt_id'])
            assert attempt is not None
            assert attempt.score == 1
            assert attempt.total_questions == len(questions)

    def test_submit_test_no_answers(self, app, client, auth_headers, sample_test_data):
        """Test test submission without answers"""
        with app.app_context():
            test, questions = sample_test_data
            
            submission_data = {
                'time_taken': 1800
            }
            
            response = client.post(f'/api/tests/{test.id}/submit',
                json=submission_data,
                headers=auth_headers)
            
            assert response.status_code == 400
            data = response.json
            assert data['error'] is True
            assert 'answer' in data['message'].lower()

    def test_submit_test_not_found(self, app, client, auth_headers):
        """Test submission to non-existent test"""
        with app.app_context():
            submission_data = {
                'answers': {'1': 'A'},
                'time_taken': 1800
            }
            
            response = client.post('/api/tests/99999/submit',
                json=submission_data,
                headers=auth_headers)
            
            assert response.status_code == 404
            data = response.json
            assert data['error'] is True
            assert 'not found' in data['message'].lower()

    def test_get_companies_success(self, app, client, auth_headers, sample_test_data):
        """Test successful companies list retrieval"""
        with app.app_context():
            test, questions = sample_test_data
            
            response = client.get('/api/tests/companies',
                headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json
            
            assert 'companies' in data
            assert 'total_companies' in data
            assert 'supported_companies' in data
            assert len(data['companies']) > 0
            
            # Check that our test company is included
            company_names = [c['name'] for c in data['companies']]
            assert test.company in company_names
            
            # Find our test company and verify it has test_count > 0
            test_company = next(c for c in data['companies'] if c['name'] == test.company)
            assert test_company['test_count'] > 0

    def test_get_test_results_success(self, app, client, auth_headers, sample_test_data):
        """Test successful test results retrieval"""
        with app.app_context():
            test, questions = sample_test_data
            
            # Create a test attempt first
            user = User.query.filter_by(email='test@uem.edu.in').first()
            
            answers = {str(questions[0].id): questions[0].correct_answer}  # One correct answer
            
            attempt = TestAttempt(
                user_id=user.id,
                test_id=test.id,
                score=1,
                total_questions=len(questions),
                time_taken=1800,
                answers=answers,
                completed_at=datetime.utcnow()
            )
            
            db.session.add(attempt)
            db.session.commit()
            
            response = client.get(f'/api/tests/{test.id}/results/{attempt.id}',
                headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json
            
            assert data['attempt_id'] == attempt.id
            assert data['score'] == 1
            assert data['total_questions'] == len(questions)
            assert 'test_info' in data
            assert 'results' in data
            assert 'section_scores' in data

    def test_get_test_results_not_found(self, app, client, auth_headers):
        """Test retrieval of non-existent test results"""
        with app.app_context():
            response = client.get('/api/tests/99999/results/99999',
                headers=auth_headers)
            
            assert response.status_code == 404
            data = response.json
            assert data['error'] is True
            assert 'not found' in data['message'].lower()

    def test_get_test_results_wrong_user(self, app, client, sample_test_data):
        """Test retrieval of test results by wrong user"""
        with app.app_context():
            test, questions = sample_test_data
            
            # Create another user
            other_user = create_test_user(email='other@uem.edu.in')
            
            # Create test attempt for first user
            first_user = User.query.filter_by(email='test@uem.edu.in').first()
            attempt = TestAttempt(
                user_id=first_user.id,
                test_id=test.id,
                score=1,
                total_questions=len(questions),
                time_taken=1800,
                answers={},
                completed_at=datetime.utcnow()
            )
            db.session.add(attempt)
            db.session.commit()
            
            # Login as other user
            login_response = client.post('/api/auth/login', 
                json={
                    'email': other_user.email,
                    'password': 'testpass123'
                })
            
            token = login_response.json['access_token']
            other_headers = {'Authorization': f'Bearer {token}'}
            
            # Try to access first user's results
            response = client.get(f'/api/tests/{test.id}/results/{attempt.id}',
                headers=other_headers)
            
            assert response.status_code == 404  # Should not find attempt for different user

    def test_progress_metrics_update(self, app, client, auth_headers, sample_test_data):
        """Test that progress metrics are updated after test submission"""
        with app.app_context():
            test, questions = sample_test_data
            user = User.query.filter_by(email='test@uem.edu.in').first()
            
            # Submit test with some correct answers
            answers = {}
            for question in questions:
                if question.section == 'Quantitative Aptitude':
                    answers[str(question.id)] = question.correct_answer  # All correct for this section
                else:
                    # Incorrect for other sections
                    options = ['A', 'B', 'C', 'D']
                    incorrect_options = [opt for opt in options if opt != question.correct_answer]
                    answers[str(question.id)] = incorrect_options[0]
            
            submission_data = {
                'answers': answers,
                'time_taken': 1800
            }
            
            response = client.post(f'/api/tests/{test.id}/submit',
                json=submission_data,
                headers=auth_headers)
            
            assert response.status_code == 200
            
            # Check that progress metrics were created/updated
            quant_metric = ProgressMetrics.query.filter_by(
                user_id=user.id,
                subject_area='Quantitative Aptitude'
            ).first()
            
            assert quant_metric is not None
            assert quant_metric.total_attempts == 1
            # Should have 100% accuracy for Quantitative Aptitude
            assert quant_metric.accuracy_rate == 100.0

    def test_randomization_parameter(self, app, client, auth_headers, sample_test_data):
        """Test question randomization parameter"""
        with app.app_context():
            test, questions = sample_test_data
            
            # Get test without randomization
            response1 = client.get(f'/api/tests/{test.id}?randomize=false',
                headers=auth_headers)
            
            # Get test with randomization
            response2 = client.get(f'/api/tests/{test.id}?randomize=true',
                headers=auth_headers)
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            # Both should have same number of questions
            data1 = response1.json
            data2 = response2.json
            
            assert data1['total_questions'] == data2['total_questions']
            assert len(data1['sections']) == len(data2['sections'])

    def test_error_handling_database_error(self, app, client, auth_headers):
        """Test error handling for database errors"""
        with app.app_context():
            # Mock database error
            with patch('test_routes.Test.query') as mock_query:
                mock_query.get.side_effect = Exception("Database connection error")
                
                response = client.get('/api/tests/1',
                    headers=auth_headers)
                
                assert response.status_code == 500
                data = response.json
                assert data['error'] is True
                assert 'internal' in data['message'].lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])