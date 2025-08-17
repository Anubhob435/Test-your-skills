"""
Tests for Leaderboard Service
"""

import pytest
import unittest
from datetime import datetime, timedelta
from models import db, User, Test, Question, TestAttempt, ProgressMetrics
from analytics_service import AnalyticsService
from test_setup import create_test_app

class TestLeaderboardService(unittest.TestCase):
    """Test cases for leaderboard functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.app = create_test_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create test users
        self.users = []
        for i in range(5):
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
        
        # Create test attempts with different scores
        scores = [8, 7, 6, 5, 4]  # Out of 10 questions
        for i, user in enumerate(self.users):
            for attempt_num in range(3):  # 3 attempts per user
                attempt = TestAttempt(
                    user_id=user.id,
                    test_id=self.test.id,
                    score=scores[i] + attempt_num * 0.5,  # Slight variation
                    total_questions=10,
                    time_taken=1800 - (i * 100),  # Different completion times
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
    
    def test_get_leaderboard_basic(self):
        """Test basic leaderboard functionality"""
        leaderboard_data = AnalyticsService.get_leaderboard(limit=10, page=1)
        
        # Check structure
        self.assertIn('leaderboard', leaderboard_data)
        self.assertIn('pagination', leaderboard_data)
        
        leaderboard = leaderboard_data['leaderboard']
        
        # Should have all 5 users (all have 3+ tests)
        self.assertEqual(len(leaderboard), 5)
        
        # Check if sorted by average score (descending)
        scores = [entry['average_score'] for entry in leaderboard]
        self.assertEqual(scores, sorted(scores, reverse=True))
        
        # Check first entry structure
        first_entry = leaderboard[0]
        required_fields = ['rank', 'name', 'year', 'branch', 'total_tests', 'average_score', 'total_time_hours']
        for field in required_fields:
            self.assertIn(field, first_entry)
        
        # Check privacy protection (name should be anonymized)
        self.assertTrue(first_entry['name'].endswith('.'))
    
    def test_leaderboard_pagination(self):
        """Test leaderboard pagination"""
        # Test first page with limit 2
        page1 = AnalyticsService.get_leaderboard(limit=2, page=1)
        self.assertEqual(len(page1['leaderboard']), 2)
        self.assertEqual(page1['pagination']['current_page'], 1)
        self.assertTrue(page1['pagination']['has_next'])
        self.assertFalse(page1['pagination']['has_prev'])
        
        # Test second page
        page2 = AnalyticsService.get_leaderboard(limit=2, page=2)
        self.assertEqual(len(page2['leaderboard']), 2)
        self.assertEqual(page2['pagination']['current_page'], 2)
        self.assertTrue(page2['pagination']['has_next'])
        self.assertTrue(page2['pagination']['has_prev'])
        
        # Check ranks are continuous
        self.assertEqual(page1['leaderboard'][0]['rank'], 1)
        self.assertEqual(page1['leaderboard'][1]['rank'], 2)
        self.assertEqual(page2['leaderboard'][0]['rank'], 3)
        self.assertEqual(page2['leaderboard'][1]['rank'], 4)
    
    def test_leaderboard_company_filter(self):
        """Test leaderboard filtering by company"""
        # Create another test for different company
        test2 = Test(company='Infosys', year=2025)
        db.session.add(test2)
        db.session.commit()
        
        # Add questions to new test
        for i in range(5):
            question = Question(
                test_id=test2.id,
                section='Verbal',
                question_text=f'Infosys question {i+1}',
                options=['A', 'B', 'C', 'D'],
                correct_answer='A'
            )
            db.session.add(question)
        db.session.commit()
        
        # Add attempts for first user only
        for i in range(3):
            attempt = TestAttempt(
                user_id=self.users[0].id,
                test_id=test2.id,
                score=4,
                total_questions=5,
                time_taken=900,
                completed_at=datetime.utcnow()
            )
            db.session.add(attempt)
        db.session.commit()
        
        # Test TCS filter (should have all 5 users)
        tcs_leaderboard = AnalyticsService.get_leaderboard(company_filter='TCS NQT')
        self.assertEqual(len(tcs_leaderboard['leaderboard']), 5)
        
        # Test Infosys filter (should have only 1 user)
        infosys_leaderboard = AnalyticsService.get_leaderboard(company_filter='Infosys')
        self.assertEqual(len(infosys_leaderboard['leaderboard']), 1)
    
    def test_leaderboard_year_branch_filter(self):
        """Test leaderboard filtering by year and branch"""
        # Update one user to different year and branch
        self.users[0].year = 2023
        self.users[0].branch = 'ECE'
        db.session.commit()
        
        # Test year filter
        year_2024 = AnalyticsService.get_leaderboard(year_filter=2024)
        self.assertEqual(len(year_2024['leaderboard']), 4)  # 4 users in 2024
        
        year_2023 = AnalyticsService.get_leaderboard(year_filter=2023)
        self.assertEqual(len(year_2023['leaderboard']), 1)  # 1 user in 2023
        
        # Test branch filter
        cse_branch = AnalyticsService.get_leaderboard(branch_filter='CSE')
        self.assertEqual(len(cse_branch['leaderboard']), 4)  # 4 users in CSE
        
        ece_branch = AnalyticsService.get_leaderboard(branch_filter='ECE')
        self.assertEqual(len(ece_branch['leaderboard']), 1)  # 1 user in ECE
    
    def test_get_user_leaderboard_position(self):
        """Test getting specific user's leaderboard position"""
        user_id = self.users[0].id  # Should be rank 1 (highest score)
        
        position_data = AnalyticsService.get_user_leaderboard_position(user_id)
        
        # Check structure
        self.assertIn('user_position', position_data)
        self.assertIn('user_entry', position_data)
        self.assertIn('nearby_competitors', position_data)
        self.assertIn('total_participants', position_data)
        
        # User should be at position 1
        self.assertEqual(position_data['user_position'], 1)
        
        # Should have nearby competitors
        nearby = position_data['nearby_competitors']
        self.assertGreater(len(nearby), 0)
        
        # Current user should be marked
        current_user_found = False
        for competitor in nearby:
            if competitor.get('is_current_user'):
                current_user_found = True
                break
        self.assertTrue(current_user_found)
    
    def test_user_position_not_qualified(self):
        """Test user position when user hasn't taken enough tests"""
        # Create user with only 1 test attempt
        new_user = User(
            email='newstudent@uem.edu.in',
            name='New Student',
            year=2024,
            branch='CSE'
        )
        new_user.set_password('password123')
        db.session.add(new_user)
        db.session.commit()
        
        # Add only 1 test attempt (less than required 3)
        attempt = TestAttempt(
            user_id=new_user.id,
            test_id=self.test.id,
            score=8,
            total_questions=10,
            time_taken=1800,
            completed_at=datetime.utcnow()
        )
        db.session.add(attempt)
        db.session.commit()
        
        position_data = AnalyticsService.get_user_leaderboard_position(new_user.id)
        
        # Should not have position
        self.assertIsNone(position_data['user_position'])
        self.assertIn('Complete at least 3 tests', position_data['message'])
    
    def test_anonymize_name(self):
        """Test name anonymization function"""
        # Test normal name
        self.assertEqual(AnalyticsService._anonymize_name('John Doe'), 'John D.')
        
        # Test single name
        self.assertEqual(AnalyticsService._anonymize_name('John'), 'John')
        
        # Test multiple names
        self.assertEqual(AnalyticsService._anonymize_name('John Michael Doe'), 'John D.')
        
        # Test empty name
        self.assertEqual(AnalyticsService._anonymize_name(''), 'Anonymous')
        self.assertEqual(AnalyticsService._anonymize_name(None), 'Anonymous')
    
    def test_get_leaderboard_filters(self):
        """Test getting available filter options"""
        filters = AnalyticsService.get_leaderboard_filters()
        
        # Check structure
        self.assertIn('companies', filters)
        self.assertIn('years', filters)
        self.assertIn('branches', filters)
        
        # Should have our test data
        self.assertIn('TCS NQT', filters['companies'])
        self.assertIn(2024, filters['years'])
        self.assertIn('CSE', filters['branches'])
    
    def test_leaderboard_minimum_tests_requirement(self):
        """Test that users with less than 3 tests are excluded"""
        # Create user with only 2 test attempts
        new_user = User(
            email='student6@uem.edu.in',
            name='Test Student 6',
            year=2024,
            branch='CSE'
        )
        new_user.set_password('password123')
        db.session.add(new_user)
        db.session.commit()
        
        # Add only 2 test attempts
        for i in range(2):
            attempt = TestAttempt(
                user_id=new_user.id,
                test_id=self.test.id,
                score=9,  # High score
                total_questions=10,
                time_taken=1500,
                completed_at=datetime.utcnow()
            )
            db.session.add(attempt)
        db.session.commit()
        
        leaderboard_data = AnalyticsService.get_leaderboard()
        
        # Should still have only 5 users (new user excluded due to insufficient tests)
        self.assertEqual(len(leaderboard_data['leaderboard']), 5)
        
        # Verify new user is not in leaderboard
        user_ids = [entry['user_id'] for entry in leaderboard_data['leaderboard']]
        self.assertNotIn(new_user.id, user_ids)

if __name__ == '__main__':
    pytest.main([__file__])