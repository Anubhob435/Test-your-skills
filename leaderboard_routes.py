"""
Leaderboard Routes for UEM Placement Platform
Handles leaderboard display, filtering, and user position tracking
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from analytics_service import AnalyticsService
import logging

logger = logging.getLogger(__name__)

# Create blueprint
leaderboard_bp = Blueprint('leaderboard', __name__, url_prefix='/api/leaderboard')

@leaderboard_bp.route('/', methods=['GET'])
@login_required
def get_leaderboard():
    """
    Get leaderboard data with optional filtering and pagination
    
    Query Parameters:
        - page: Page number (default: 1)
        - limit: Items per page (default: 50, max: 100)
        - company: Filter by company name
        - year: Filter by student year
        - branch: Filter by student branch
    """
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 50, type=int), 100)  # Max 100 per page
        company_filter = request.args.get('company')
        year_filter = request.args.get('year', type=int)
        branch_filter = request.args.get('branch')
        
        # Validate page number
        if page < 1:
            page = 1
        
        # Get leaderboard data
        leaderboard_data = AnalyticsService.get_leaderboard(
            limit=limit,
            page=page,
            company_filter=company_filter,
            year_filter=year_filter,
            branch_filter=branch_filter
        )
        
        return jsonify({
            'success': True,
            'data': leaderboard_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch leaderboard data',
            'message': str(e)
        }), 500

@leaderboard_bp.route('/position', methods=['GET'])
@login_required
def get_user_position():
    """
    Get current user's position in leaderboard with nearby competitors
    
    Query Parameters:
        - company: Filter by company name
        - year: Filter by student year
        - branch: Filter by student branch
    """
    try:
        # Get query parameters
        company_filter = request.args.get('company')
        year_filter = request.args.get('year', type=int)
        branch_filter = request.args.get('branch')
        
        # Get user position data
        position_data = AnalyticsService.get_user_leaderboard_position(
            user_id=current_user.id,
            company_filter=company_filter,
            year_filter=year_filter,
            branch_filter=branch_filter
        )
        
        return jsonify({
            'success': True,
            'data': position_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching user position for user {current_user.id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch user position',
            'message': str(e)
        }), 500

@leaderboard_bp.route('/filters', methods=['GET'])
@login_required
def get_leaderboard_filters():
    """
    Get available filter options for leaderboard
    """
    try:
        filters = AnalyticsService.get_leaderboard_filters()
        
        return jsonify({
            'success': True,
            'data': filters
        })
        
    except Exception as e:
        logger.error(f"Error fetching leaderboard filters: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch filter options',
            'message': str(e)
        }), 500

@leaderboard_bp.route('/stats', methods=['GET'])
@login_required
def get_leaderboard_stats():
    """
    Get general leaderboard statistics
    """
    try:
        from models import db, User, TestAttempt
        from sqlalchemy import func
        
        # Get basic statistics
        stats_query = db.session.query(
            func.count(func.distinct(User.id)).label('total_participants'),
            func.count(TestAttempt.id).label('total_tests_taken'),
            func.avg(TestAttempt.score / TestAttempt.total_questions * 100).label('platform_average'),
            func.max(TestAttempt.score / TestAttempt.total_questions * 100).label('highest_score')
        ).join(TestAttempt, User.id == TestAttempt.user_id).first()
        
        # Get top performer (anonymized)
        top_performer = db.session.query(
            User.name,
            User.year,
            User.branch,
            func.avg(TestAttempt.score / TestAttempt.total_questions * 100).label('avg_score')
        ).join(TestAttempt, User.id == TestAttempt.user_id).group_by(
            User.id, User.name, User.year, User.branch
        ).having(
            func.count(TestAttempt.id) >= 3
        ).order_by(
            func.avg(TestAttempt.score / TestAttempt.total_questions * 100).desc()
        ).first()
        
        stats = {
            'total_participants': stats_query.total_participants or 0,
            'total_tests_taken': stats_query.total_tests_taken or 0,
            'platform_average': round(stats_query.platform_average or 0, 2),
            'highest_score': round(stats_query.highest_score or 0, 2),
            'top_performer': {
                'name': AnalyticsService._anonymize_name(top_performer.name) if top_performer else 'N/A',
                'year': top_performer.year if top_performer else None,
                'branch': top_performer.branch if top_performer else None,
                'score': round(top_performer.avg_score, 2) if top_performer else 0
            } if top_performer else None
        }
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"Error fetching leaderboard stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch leaderboard statistics',
            'message': str(e)
        }), 500

# Frontend route for leaderboard page
@leaderboard_bp.route('/page')
@login_required
def leaderboard_page():
    """Render the leaderboard page"""
    return render_template('leaderboard.html')