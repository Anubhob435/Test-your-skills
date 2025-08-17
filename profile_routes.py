"""
Profile and Progress Routes for UEM Placement Platform
Handles user profile, progress tracking, and analytics endpoints
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from analytics_service import AnalyticsService
from models import db, User, TestAttempt, ProgressMetrics
import logging

logger = logging.getLogger(__name__)

# Create blueprint
profile_bp = Blueprint('profile', __name__, url_prefix='/api/profile')

@profile_bp.route('/progress', methods=['GET'])
@login_required
def get_user_progress():
    """
    Get comprehensive progress analytics for the current user
    
    Returns:
        JSON response with user progress data
    """
    try:
        user_id = current_user.id
        progress_data = AnalyticsService.calculate_user_progress(user_id)
        
        return jsonify({
            'success': True,
            'data': progress_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching progress for user {current_user.id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch progress data',
            'message': str(e)
        }), 500

@profile_bp.route('/weak-areas', methods=['GET'])
@login_required
def get_weak_areas():
    """
    Get weak areas and improvement suggestions for the current user
    
    Returns:
        JSON response with weak areas data
    """
    try:
        user_id = current_user.id
        weak_areas = AnalyticsService.get_weak_areas(user_id)
        
        return jsonify({
            'success': True,
            'data': weak_areas
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching weak areas for user {current_user.id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch weak areas',
            'message': str(e)
        }), 500

@profile_bp.route('/recommendations', methods=['GET'])
@login_required
def get_recommendations():
    """
    Get personalized AI recommendations for the current user
    
    Returns:
        JSON response with recommendations data
    """
    try:
        user_id = current_user.id
        recommendations = AnalyticsService.generate_recommendations(user_id)
        
        return jsonify({
            'success': True,
            'data': recommendations
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating recommendations for user {current_user.id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate recommendations',
            'message': str(e)
        }), 500

@profile_bp.route('/test-history', methods=['GET'])
@login_required
def get_test_history():
    """
    Get test history for the current user with pagination
    
    Query Parameters:
        page (int): Page number (default: 1)
        per_page (int): Items per page (default: 10)
        company (str): Filter by company (optional)
    
    Returns:
        JSON response with paginated test history
    """
    try:
        user_id = current_user.id
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        company_filter = request.args.get('company')
        
        # Build query
        query = TestAttempt.query.filter_by(user_id=user_id)
        
        if company_filter:
            query = query.join(TestAttempt.test).filter_by(company=company_filter)
        
        # Order by most recent first
        query = query.order_by(TestAttempt.started_at.desc())
        
        # Paginate
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Format results
        test_attempts = []
        for attempt in pagination.items:
            attempt_data = attempt.to_dict()
            if attempt.test:
                attempt_data['company'] = attempt.test.company
                attempt_data['test_year'] = attempt.test.year
            test_attempts.append(attempt_data)
        
        return jsonify({
            'success': True,
            'data': {
                'attempts': test_attempts,
                'pagination': {
                    'page': pagination.page,
                    'pages': pagination.pages,
                    'per_page': pagination.per_page,
                    'total': pagination.total,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching test history for user {current_user.id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch test history',
            'message': str(e)
        }), 500

@profile_bp.route('/stats', methods=['GET'])
@login_required
def get_user_stats():
    """
    Get basic user statistics
    
    Returns:
        JSON response with user statistics
    """
    try:
        user_id = current_user.id
        
        # Get basic stats
        total_tests = TestAttempt.query.filter_by(user_id=user_id).count()
        
        if total_tests > 0:
            # Calculate average score
            attempts = TestAttempt.query.filter_by(user_id=user_id).all()
            total_score = sum(attempt.score for attempt in attempts)
            total_questions = sum(attempt.total_questions for attempt in attempts)
            avg_percentage = (total_score / total_questions * 100) if total_questions > 0 else 0
            
            # Get best score
            best_attempt = max(attempts, key=lambda x: x.calculate_percentage())
            best_percentage = best_attempt.calculate_percentage()
            
            # Get total time spent
            total_time = sum(attempt.time_taken or 0 for attempt in attempts)
            
            # Get recent activity (last 7 days)
            from datetime import datetime, timedelta
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_tests = TestAttempt.query.filter(
                TestAttempt.user_id == user_id,
                TestAttempt.started_at >= week_ago
            ).count()
        else:
            avg_percentage = 0
            best_percentage = 0
            total_time = 0
            recent_tests = 0
        
        # Get subject-wise performance
        progress_metrics = ProgressMetrics.query.filter_by(user_id=user_id).all()
        subject_stats = {}
        for metric in progress_metrics:
            subject_stats[metric.subject_area] = {
                'accuracy': round(metric.accuracy_rate, 1),
                'attempts': metric.total_attempts
            }
        
        stats = {
            'total_tests': total_tests,
            'average_score': round(avg_percentage, 1),
            'best_score': round(best_percentage, 1),
            'total_time_hours': round(total_time / 3600, 1),
            'recent_activity': recent_tests,
            'subject_performance': subject_stats
        }
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching stats for user {current_user.id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch user statistics',
            'message': str(e)
        }), 500

# Frontend route for profile page
@profile_bp.route('/profile')
@login_required
def profile_page():
    """Render the user profile page"""
    return render_template('profile.html')

# Leaderboard endpoints
@profile_bp.route('/leaderboard', methods=['GET'])
@login_required
def get_leaderboard():
    """
    Get leaderboard data
    
    Query Parameters:
        limit (int): Number of entries to return (default: 50, max: 100)
    
    Returns:
        JSON response with leaderboard data
    """
    try:
        limit = min(request.args.get('limit', 50, type=int), 100)
        leaderboard_data = AnalyticsService.get_leaderboard(limit)
        
        # Find current user's position
        user_position = None
        for entry in leaderboard_data:
            if entry.get('user_id') == current_user.id:  # This would need to be added to leaderboard data
                user_position = entry['rank']
                break
        
        return jsonify({
            'success': True,
            'data': {
                'leaderboard': leaderboard_data,
                'user_position': user_position,
                'total_entries': len(leaderboard_data)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch leaderboard',
            'message': str(e)
        }), 500

# Error handlers for the blueprint
@profile_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'message': 'The requested profile endpoint was not found'
    }), 404

@profile_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred while processing your request'
    }), 500