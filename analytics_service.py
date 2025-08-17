"""
Analytics Service for UEM Placement Platform
Handles progress tracking, weak area identification, and performance analysis
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, desc, and_
from models import db, User, Test, Question, TestAttempt, ProgressMetrics
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service class for calculating user progress and analytics"""
    
    @staticmethod
    def calculate_user_progress(user_id: int) -> Dict:
        """
        Calculate comprehensive progress metrics for a user
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary containing progress metrics
        """
        try:
            user = User.query.get(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")
            
            # Get all test attempts for the user
            attempts = TestAttempt.query.filter_by(user_id=user_id).all()
            
            if not attempts:
                return {
                    'user_id': user_id,
                    'total_tests': 0,
                    'average_score': 0,
                    'total_time_spent': 0,
                    'improvement_trend': 0,
                    'subject_performance': {},
                    'recent_performance': [],
                    'strengths': [],
                    'weaknesses': []
                }
            
            # Calculate basic metrics
            total_tests = len(attempts)
            total_score = sum(attempt.score for attempt in attempts)
            total_questions = sum(attempt.total_questions for attempt in attempts)
            average_score = (total_score / total_questions * 100) if total_questions > 0 else 0
            total_time_spent = sum(attempt.time_taken or 0 for attempt in attempts)
            
            # Calculate improvement trend (last 5 vs first 5 tests)
            improvement_trend = AnalyticsService._calculate_improvement_trend(attempts)
            
            # Get subject-wise performance
            subject_performance = AnalyticsService._get_subject_performance(user_id)
            
            # Get recent performance (last 10 tests)
            recent_performance = AnalyticsService._get_recent_performance(attempts)
            
            # Identify strengths and weaknesses
            strengths, weaknesses = AnalyticsService._identify_strengths_weaknesses(subject_performance)
            
            return {
                'user_id': user_id,
                'total_tests': total_tests,
                'average_score': round(average_score, 2),
                'total_time_spent': total_time_spent,
                'improvement_trend': improvement_trend,
                'subject_performance': subject_performance,
                'recent_performance': recent_performance,
                'strengths': strengths,
                'weaknesses': weaknesses,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating user progress for user {user_id}: {str(e)}")
            raise
    
    @staticmethod
    def _calculate_improvement_trend(attempts: List[TestAttempt]) -> float:
        """Calculate improvement trend based on test attempts"""
        if len(attempts) < 2:
            return 0
        
        # Sort attempts by date
        sorted_attempts = sorted(attempts, key=lambda x: x.started_at)
        
        # Compare first half vs second half performance
        mid_point = len(sorted_attempts) // 2
        first_half = sorted_attempts[:mid_point]
        second_half = sorted_attempts[mid_point:]
        
        if not first_half or not second_half:
            return 0
        
        # Calculate average percentage for each half
        first_avg = sum(a.calculate_percentage() for a in first_half) / len(first_half)
        second_avg = sum(a.calculate_percentage() for a in second_half) / len(second_half)
        
        return round(second_avg - first_avg, 2)
    
    @staticmethod
    def _get_subject_performance(user_id: int) -> Dict:
        """Get performance metrics by subject area"""
        progress_metrics = ProgressMetrics.query.filter_by(user_id=user_id).all()
        
        subject_performance = {}
        for metric in progress_metrics:
            subject_performance[metric.subject_area] = {
                'accuracy_rate': round(metric.accuracy_rate, 2),
                'total_attempts': metric.total_attempts,
                'last_updated': metric.last_updated.isoformat()
            }
        
        return subject_performance
    
    @staticmethod
    def _get_recent_performance(attempts: List[TestAttempt]) -> List[Dict]:
        """Get recent performance data for trend analysis"""
        # Sort by date and get last 10 attempts
        sorted_attempts = sorted(attempts, key=lambda x: x.started_at, reverse=True)[:10]
        
        recent_performance = []
        for attempt in reversed(sorted_attempts):  # Reverse to show chronological order
            recent_performance.append({
                'date': attempt.started_at.strftime('%Y-%m-%d'),
                'score': round(attempt.calculate_percentage(), 2),
                'company': attempt.test.company if attempt.test else 'Unknown',
                'time_taken': attempt.time_taken
            })
        
        return recent_performance
    
    @staticmethod
    def _identify_strengths_weaknesses(subject_performance: Dict) -> Tuple[List[str], List[str]]:
        """Identify user's strengths and weaknesses based on subject performance"""
        if not subject_performance:
            return [], []
        
        # Sort subjects by accuracy rate
        sorted_subjects = sorted(
            subject_performance.items(),
            key=lambda x: x[1]['accuracy_rate'],
            reverse=True
        )
        
        # Top 3 subjects are strengths, bottom 3 are weaknesses
        strengths = [subject for subject, _ in sorted_subjects[:3] if sorted_subjects[0][1]['accuracy_rate'] >= 70]
        weaknesses = [subject for subject, _ in sorted_subjects[-3:] if sorted_subjects[-1][1]['accuracy_rate'] < 60]
        
        return strengths, weaknesses
    
    @staticmethod
    def get_weak_areas(user_id: int) -> List[Dict]:
        """
        Identify specific weak areas for targeted improvement
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of weak areas with improvement suggestions
        """
        try:
            # Get subject performance
            subject_performance = AnalyticsService._get_subject_performance(user_id)
            
            weak_areas = []
            for subject, performance in subject_performance.items():
                if performance['accuracy_rate'] < 60:  # Below 60% is considered weak
                    # Get specific topics within this subject that are weak
                    weak_topics = AnalyticsService._get_weak_topics_in_subject(user_id, subject)
                    
                    weak_areas.append({
                        'subject': subject,
                        'accuracy_rate': performance['accuracy_rate'],
                        'total_attempts': performance['total_attempts'],
                        'weak_topics': weak_topics,
                        'improvement_suggestion': AnalyticsService._generate_improvement_suggestion(subject, performance['accuracy_rate'])
                    })
            
            return sorted(weak_areas, key=lambda x: x['accuracy_rate'])
            
        except Exception as e:
            logger.error(f"Error identifying weak areas for user {user_id}: {str(e)}")
            return []
    
    @staticmethod
    def _get_weak_topics_in_subject(user_id: int, subject: str) -> List[Dict]:
        """Get weak topics within a specific subject"""
        # For now, return empty list as this requires complex JSON querying
        # This can be implemented later with proper database-specific JSON functions
        return []
        
        weak_topics = []
        for topic, attempts, accuracy in topic_performance:
            if accuracy and accuracy < 50:  # Below 50% accuracy
                weak_topics.append({
                    'topic': topic,
                    'accuracy': round(accuracy, 2),
                    'attempts': attempts
                })
        
        return sorted(weak_topics, key=lambda x: x['accuracy'])
    
    @staticmethod
    def _generate_improvement_suggestion(subject: str, accuracy_rate: float) -> str:
        """Generate improvement suggestions based on subject and performance"""
        suggestions = {
            'Quantitative Aptitude': {
                'low': 'Focus on basic arithmetic and number systems. Practice daily calculations.',
                'medium': 'Work on advanced topics like probability and permutations.',
                'high': 'Fine-tune speed and accuracy with timed practice sessions.'
            },
            'Logical Reasoning': {
                'low': 'Start with basic pattern recognition and simple logical sequences.',
                'medium': 'Practice syllogisms and analytical reasoning problems.',
                'high': 'Focus on complex reasoning puzzles and time management.'
            },
            'Verbal Ability': {
                'low': 'Build vocabulary and practice basic grammar rules.',
                'medium': 'Work on reading comprehension and sentence correction.',
                'high': 'Practice advanced verbal reasoning and critical thinking.'
            },
            'Programming': {
                'low': 'Review basic programming concepts and syntax.',
                'medium': 'Practice data structures and algorithm problems.',
                'high': 'Focus on optimization and complex problem-solving.'
            }
        }
        
        # Determine performance level
        if accuracy_rate < 40:
            level = 'low'
        elif accuracy_rate < 70:
            level = 'medium'
        else:
            level = 'high'
        
        return suggestions.get(subject, {}).get(level, 'Practice regularly and focus on understanding concepts.')
    
    @staticmethod
    def generate_recommendations(user_id: int) -> Dict:
        """
        Generate personalized AI recommendations based on user performance
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary containing personalized recommendations
        """
        try:
            progress = AnalyticsService.calculate_user_progress(user_id)
            weak_areas = AnalyticsService.get_weak_areas(user_id)
            
            recommendations = {
                'priority_areas': [],
                'study_plan': [],
                'practice_suggestions': [],
                'time_allocation': {},
                'next_steps': []
            }
            
            # Priority areas (top 3 weakest subjects)
            if weak_areas:
                recommendations['priority_areas'] = [
                    {
                        'subject': area['subject'],
                        'current_accuracy': area['accuracy_rate'],
                        'target_accuracy': min(area['accuracy_rate'] + 20, 85),
                        'estimated_time': '2-3 weeks'
                    }
                    for area in weak_areas[:3]
                ]
            
            # Generate study plan
            recommendations['study_plan'] = AnalyticsService._generate_study_plan(progress, weak_areas)
            
            # Practice suggestions
            recommendations['practice_suggestions'] = AnalyticsService._generate_practice_suggestions(progress)
            
            # Time allocation
            recommendations['time_allocation'] = AnalyticsService._generate_time_allocation(weak_areas)
            
            # Next steps
            recommendations['next_steps'] = AnalyticsService._generate_next_steps(progress, weak_areas)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations for user {user_id}: {str(e)}")
            return {}
    
    @staticmethod
    def _generate_study_plan(progress: Dict, weak_areas: List[Dict]) -> List[Dict]:
        """Generate a structured study plan"""
        study_plan = []
        
        if weak_areas:
            for i, area in enumerate(weak_areas[:3]):  # Focus on top 3 weak areas
                study_plan.append({
                    'week': i + 1,
                    'focus_subject': area['subject'],
                    'daily_time': '45-60 minutes',
                    'activities': [
                        f'Review {area["subject"]} fundamentals',
                        'Practice 10-15 questions daily',
                        'Take 1 mock test',
                        'Analyze mistakes and review explanations'
                    ],
                    'goal': f'Improve accuracy from {area["accuracy_rate"]}% to {min(area["accuracy_rate"] + 15, 80)}%'
                })
        
        return study_plan
    
    @staticmethod
    def _generate_practice_suggestions(progress: Dict) -> List[str]:
        """Generate specific practice suggestions"""
        suggestions = []
        
        if progress['total_tests'] < 5:
            suggestions.append('Take more practice tests to establish baseline performance')
        
        if progress['average_score'] < 60:
            suggestions.append('Focus on accuracy over speed initially')
            suggestions.append('Review fundamental concepts before attempting advanced questions')
        
        if progress['improvement_trend'] < 0:
            suggestions.append('Analyze recent mistakes to identify recurring error patterns')
            suggestions.append('Consider changing study approach or seeking additional help')
        
        suggestions.extend([
            'Practice daily for consistent improvement',
            'Time yourself during practice sessions',
            'Review explanations for both correct and incorrect answers'
        ])
        
        return suggestions
    
    @staticmethod
    def _generate_time_allocation(weak_areas: List[Dict]) -> Dict:
        """Generate recommended time allocation for different subjects"""
        if not weak_areas:
            return {'balanced_practice': '30 minutes per subject'}
        
        total_time = 120  # 2 hours daily
        allocation = {}
        
        # Allocate more time to weaker areas
        for i, area in enumerate(weak_areas[:4]):  # Top 4 weak areas
            if i == 0:  # Weakest area gets most time
                allocation[area['subject']] = '45 minutes'
            elif i == 1:
                allocation[area['subject']] = '30 minutes'
            else:
                allocation[area['subject']] = '20 minutes'
        
        allocation['revision'] = '15 minutes'
        allocation['mock_tests'] = '2-3 times per week'
        
        return allocation
    
    @staticmethod
    def _generate_next_steps(progress: Dict, weak_areas: List[Dict]) -> List[str]:
        """Generate immediate next steps for the user"""
        next_steps = []
        
        if progress['total_tests'] == 0:
            next_steps.append('Take your first practice test to establish baseline')
        elif progress['total_tests'] < 3:
            next_steps.append('Complete at least 3 practice tests for better analysis')
        
        if weak_areas:
            next_steps.append(f'Start focused practice on {weak_areas[0]["subject"]}')
            next_steps.append('Review fundamental concepts in your weakest areas')
        
        if progress['improvement_trend'] > 0:
            next_steps.append('Continue current study approach - you\'re improving!')
        
        next_steps.extend([
            'Set daily practice goals and track progress',
            'Schedule regular mock tests to monitor improvement'
        ])
        
        return next_steps
    
    @staticmethod
    def update_progress_metrics(user_id: int, test_attempt: TestAttempt) -> None:
        """
        Update progress metrics after a test attempt
        
        Args:
            user_id: ID of the user
            test_attempt: TestAttempt object containing test results
        """
        try:
            # Get all questions from the test to analyze by section
            questions = Question.query.filter_by(test_id=test_attempt.test_id).all()
            user_answers = test_attempt.get_answers()
            
            # Group questions by section
            sections = {}
            for question in questions:
                if question.section not in sections:
                    sections[question.section] = {'correct': 0, 'total': 0}
                
                sections[question.section]['total'] += 1
                
                # Check if user answered correctly
                user_answer = user_answers.get(str(question.id))
                if user_answer == question.correct_answer:
                    sections[question.section]['correct'] += 1
            
            # Update or create progress metrics for each section
            for section, results in sections.items():
                progress_metric = ProgressMetrics.query.filter_by(
                    user_id=user_id,
                    subject_area=section
                ).first()
                
                if progress_metric:
                    # Update existing metric
                    progress_metric.update_metrics(results['correct'], results['total'])
                else:
                    # Create new metric
                    accuracy_rate = (results['correct'] / results['total']) * 100
                    progress_metric = ProgressMetrics(
                        user_id=user_id,
                        subject_area=section,
                        accuracy_rate=accuracy_rate,
                        total_attempts=1,
                        last_updated=datetime.utcnow()
                    )
                    db.session.add(progress_metric)
            
            db.session.commit()
            logger.info(f"Updated progress metrics for user {user_id}")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating progress metrics for user {user_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_leaderboard(limit: int = 50) -> List[Dict]:
        """
        Get leaderboard data with privacy protection
        
        Args:
            limit: Maximum number of users to return
            
        Returns:
            List of leaderboard entries
        """
        try:
            # Calculate average scores for all users
            leaderboard_query = db.session.query(
                User.id,
                User.name,
                User.year,
                User.branch,
                func.count(TestAttempt.id).label('total_tests'),
                func.avg(TestAttempt.score / TestAttempt.total_questions * 100).label('avg_score'),
                func.sum(TestAttempt.time_taken).label('total_time')
            ).join(
                TestAttempt, User.id == TestAttempt.user_id
            ).group_by(
                User.id, User.name, User.year, User.branch
            ).having(
                func.count(TestAttempt.id) >= 3  # Minimum 3 tests for leaderboard
            ).order_by(
                desc('avg_score')
            ).limit(limit).all()
            
            leaderboard = []
            for rank, entry in enumerate(leaderboard_query, 1):
                leaderboard.append({
                    'rank': rank,
                    'name': entry.name.split()[0] + ' ' + entry.name.split()[-1][0] + '.',  # Privacy protection
                    'year': entry.year,
                    'branch': entry.branch,
                    'total_tests': entry.total_tests,
                    'average_score': round(entry.avg_score, 2),
                    'total_time_hours': round((entry.total_time or 0) / 3600, 1)
                })
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Error generating leaderboard: {str(e)}")
            return []