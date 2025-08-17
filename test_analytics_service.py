"""
Unit tests for AnalyticsService
"""

import unittest
from datetime import datetime, timedelta
from flask import Flask
from models import db, User, Test, Question, TestAttempt, ProgressMetrics
from analytics_service import AnalyticsService
from config import config

class TestAnalyticsService(unittest.TestCase):
    """Test cases for AnalyticsService"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = Flask(__name__)
        self.app.config.from_object(config['testing'])
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.init_app(self.app)
        db.create_all()
        
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
        
        # Store IDs for later use
        self.test_user_id = self.test_user.id
        self.test_test_id = self.test_test.id
        
        # Create test questions
        self.questions = []
        sections = ['Quantitative Aptitude', 'Logical Reasoning', 'Verbal Ability']
        for i, section in enumerate(sections):
            for j in range(5):  # 5 questions per section
                question = Question(
                    test_id=self.test_test.id,
                    section=section,
                    question_text=f'Test question {i*5 + j + 1}',
                    options=['A', 'B', 'C', 'D'],
                    correct_answer='A',
                    topic=f'Topic {j + 1}'
                )
                self.questions.append(question)
                db.session.add(question)
        
        db.session.commit()
    
    def tearDown(self):
        """Clean up test environment"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_calculate_user_progress_no_attempts(self):
        """Test progress calculation with no test attempts"""
        progress = AnalyticsService.calculate_user_progress(self.test_user_id)
        
        self.assertEqual(progress['user_id'], self.test_user_id)
        self.assertEqual(progress['total_tests'], 0)
        self.assertEqual(progress['average_score'], 0)
        self.assertEqual(progress['improvement_trend'], 0)
        self.assertEqual(len(progress['strengths']), 0)
        self.assertEqual(len(progress['weaknesses']), 0)
    
    def test_calculate_user_progress_with_attempts(self):
        """Test progress calculation with test attempts"""
        # Create test attempts
        attempt1 = TestAttempt(
            user_id=self.test_user_id,
            test_id=self.test_test_id,
            score=8,  # 8 out of 15 questions correct
            total_questions=15,
            time_taken=1800,
            answers={'1': 'A', '2': 'B', '3': 'A'},
            started_at=datetime.utcnow() - timedelta(days=10),
            completed_at=datetime.utcnow() - timedelta(days=10)
        )
        
        attempt2 = TestAttempt(
            user_id=self.test_user_id,
            test_id=self.test_test_id,
            score=12,  # 12 out of 15 questions correct
            total_questions=15,
            time_taken=1600,
            answers={'1': 'A', '2': 'A', '3': 'A'},
            started_at=datetime.utcnow() - timedelta(days=5),
            completed_at=datetime.utcnow() - timedelta(days=5)
        )
        
        db.session.add(attempt1)
        db.session.add(attempt2)
        db.session.commit()
        
        progress = AnalyticsService.calculate_user_progress(self.test_user_id)
        
        self.assertEqual(progress['user_id'], self.test_user_id)
        self.assertEqual(progress['total_tests'], 2)
        self.assertAlmostEqual(progress['average_score'], 66.67, places=1)  # (8+12)/(15+15)*100
        self.assertEqual(progress['total_time_spent'], 3400)
        self.assertGreater(progress['improvement_trend'], 0)  # Should show improvement
    
    def test_get_weak_areas(self):
        """Test weak area identification"""
        # Create progress metrics with weak areas
        weak_metric = ProgressMetrics(
            user_id=self.test_user_id,
            subject_area='Quantitative Aptitude',
            accuracy_rate=45.0,  # Below 60% threshold
            total_attempts=5
        )
        
        strong_metric = ProgressMetrics(
            user_id=self.test_user_id,
            subject_area='Logical Reasoning',
            accuracy_rate=85.0,  # Above 60% threshold
            total_attempts=3
        )
        
        db.session.add(weak_metric)
        db.session.add(strong_metric)
        db.session.commit()
        
        weak_areas = AnalyticsService.get_weak_areas(self.test_user_id)
        
        self.assertEqual(len(weak_areas), 1)
        self.assertEqual(weak_areas[0]['subject'], 'Quantitative Aptitude')
        self.assertEqual(weak_areas[0]['accuracy_rate'], 45.0)
        self.assertIn('improvement_suggestion', weak_areas[0])
    
    def test_generate_recommendations(self):
        """Test recommendation generation"""
        # Create some test data
        attempt = TestAttempt(
            user_id=self.test_user_id,
            test_id=self.test_test_id,
            score=10,
            total_questions=15,
            time_taken=1800,
            answers={'1': 'A', '2': 'B'},
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        db.session.add(attempt)
        db.session.commit()
        
        recommendations = AnalyticsService.generate_recommendations(self.test_user_id)
        
        self.assertIn('priority_areas', recommendations)
        self.assertIn('study_plan', recommendations)
        self.assertIn('practice_suggestions', recommendations)
        self.assertIn('time_allocation', recommendations)
        self.assertIn('next_steps', recommendations)
    
    def test_update_progress_metrics(self):
        """Test progress metrics update after test attempt"""
        # Create test attempt
        attempt = TestAttempt(
            user_id=self.test_user_id,
            test_id=self.test_test_id,
            score=10,
            total_questions=15,
            time_taken=1800,
            answers={
                str(self.questions[0].id): 'A',  # Correct
                str(self.questions[1].id): 'B',  # Incorrect
                str(self.questions[5].id): 'A',  # Correct
                str(self.questions[6].id): 'A',  # Correct
                str(self.questions[10].id): 'A', # Correct
            },
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        db.session.add(attempt)
        db.session.commit()
        
        # Update progress metrics
        AnalyticsService.update_progress_metrics(self.test_user_id, attempt)
        
        # Check if progress metrics were created
        metrics = ProgressMetrics.query.filter_by(user_id=self.test_user_id).all()
        self.assertGreater(len(metrics), 0)
        
        # Check specific metrics
        quant_metric = ProgressMetrics.query.filter_by(
            user_id=self.test_user_id,
            subject_area='Quantitative Aptitude'
        ).first()
        self.assertIsNotNone(quant_metric)
        self.assertEqual(quant_metric.total_attempts, 1)
    
    def test_get_leaderboard(self):
        """Test leaderboard generation"""
        # Create additional users and test attempts
        user2 = User(
            email='user2@uem.edu.in',
            name='User Two',
            year=2024,
            branch='ECE'
        )
        user2.set_password('testpass')
        db.session.add(user2)
        db.session.commit()
        
        user2_id = user2.id
        
        # Create multiple test attempts for both users
        for i in range(3):  # Minimum 3 tests required for leaderboard
            attempt1 = TestAttempt(
                user_id=self.test_user_id,
                test_id=self.test_test_id,
                score=10 + i,
                total_questions=15,
                time_taken=1800,
                started_at=datetime.utcnow() - timedelta(days=i),
                completed_at=datetime.utcnow() - timedelta(days=i)
            )
            
            attempt2 = TestAttempt(
                user_id=user2_id,
                test_id=self.test_test_id,
                score=8 + i,
                total_questions=15,
                time_taken=2000,
                started_at=datetime.utcnow() - timedelta(days=i),
                completed_at=datetime.utcnow() - timedelta(days=i)
            )
            
            db.session.add(attempt1)
            db.session.add(attempt2)
        
        db.session.commit()
        
        leaderboard = AnalyticsService.get_leaderboard(10)
        
        self.assertGreater(len(leaderboard), 0)
        self.assertLessEqual(len(leaderboard), 10)
        
        # Check leaderboard structure
        if leaderboard:
            entry = leaderboard[0]
            self.assertIn('rank', entry)
            self.assertIn('name', entry)
            self.assertIn('average_score', entry)
            self.assertIn('total_tests', entry)
            
            # Check privacy protection (name should be abbreviated)
            self.assertNotEqual(entry['name'], 'Test User')  # Should be abbreviated
    
    def test_improvement_trend_calculation(self):
        """Test improvement trend calculation"""
        # Create test attempts with improving scores
        attempts = []
        for i in range(6):
            attempt = TestAttempt(
                user_id=self.test_user_id,
                test_id=self.test_test_id,
                score=5 + i,  # Improving scores: 5, 6, 7, 8, 9, 10
                total_questions=15,
                time_taken=1800,
                started_at=datetime.utcnow() - timedelta(days=6-i),
                completed_at=datetime.utcnow() - timedelta(days=6-i)
            )
            attempts.append(attempt)
            db.session.add(attempt)
        
        db.session.commit()
        
        # Calculate improvement trend
        trend = AnalyticsService._calculate_improvement_trend(attempts)
        
        # Should show positive improvement
        self.assertGreater(trend, 0)
    
    def test_invalid_user_id(self):
        """Test handling of invalid user ID"""
        with self.app.app_context():
            with self.assertRaises(ValueError):
                AnalyticsService.calculate_user_progress(99999)

if __name__ == '__main__':
    unittest.main()