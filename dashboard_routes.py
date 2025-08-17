"""
Dashboard Routes for UEM Placement Platform
Handles dashboard data, user statistics, and test history endpoints
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required
from sqlalchemy import func, desc
from sqlalchemy.exc import SQLAlchemyError

from models import db, User, Test, TestAttempt, ProgressMetrics
from auth_middleware import jwt_required_custom, get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api')

@dashboard_bp.route('/dashboard', methods=['GET'])
@jwt_required_custom()
def get_dashboard_data():
    """
    Get comprehensive dashboard data for the current user
    
    GET /api/dashboard
    
    Response:
    {
        "user_info": {
            "name": "Student Name",
            "email": "student@uem.edu.in",
            "year": 2025,
            "branch": "CSE"
        },
        "statistics": {
            "total_tests_taken": 15,
            "average_score": 78.5,
            "best_score": 95.0,
            "total_time_spent": 7200,
            "tests_this_week": 3,
            "improvement_trend": "positive"
        },
        "recent_attempts": [
            {
                "attempt_id": 123,
                "test_id": 45,
                "company": "TCS NQT",
                "score": 18,
                "total_questions": 20,
                "percentage": 90.0,
                "completed_at": "2025-01-17T10:30:00Z",
                "time_taken": 3600
            }
        ],
        "progress_by_subject": [
            {
                "subject": "Quantitative Aptitude",
                "accuracy_rate": 85.5,
                "total_attempts": 8,
                "trend": "improving"
            }
        ],
        "recommended_companies": [
            {
                "company": "Infosys",
                "reason": "Based on your strong performance in logical reasoning",
                "difficulty_match": "medium"
            }
        ],
        "available_companies": [
            {
                "name": "TCS NQT",
                "test_count": 3,
                "user_attempts": 2,
                "best_score": 85.0,
                "supported": true
            }
        ]
    }
    """
    try:
        current_user = get_current_user()
        
        # Get user's test attempts
        user_attempts = TestAttempt.query.filter_by(user_id=current_user.id).all()
        
        # Calculate basic statistics
        total_tests = len(user_attempts)
        if total_tests > 0:
            total_score = sum(attempt.score for attempt in user_attempts)
            total_questions = sum(attempt.total_questions for attempt in user_attempts)
            average_score = (total_score / total_questions * 100) if total_questions > 0 else 0
            best_score = max(attempt.calculate_percentage() for attempt in user_attempts)
            total_time_spent = sum(attempt.time_taken or 0 for attempt in user_attempts)
        else:
            average_score = 0
            best_score = 0
            total_time_spent = 0
        
        # Calculate tests this week
        week_ago = datetime.utcnow() - timedelta(days=7)
        tests_this_week = TestAttempt.query.filter(
            TestAttempt.user_id == current_user.id,
            TestAttempt.completed_at >= week_ago
        ).count()
        
        # Calculate improvement trend
        improvement_trend = "stable"
        if total_tests >= 3:
            recent_attempts = sorted(user_attempts, key=lambda x: x.completed_at or datetime.min)
            recent_scores = [attempt.calculate_percentage() for attempt in recent_attempts[-3:]]
            if len(recent_scores) >= 2:
                if recent_scores[-1] > recent_scores[0]:
                    improvement_trend = "positive"
                elif recent_scores[-1] < recent_scores[0]:
                    improvement_trend = "negative"
        
        # Get recent attempts (last 5)
        recent_attempts_query = TestAttempt.query.filter_by(user_id=current_user.id)\
            .order_by(desc(TestAttempt.completed_at))\
            .limit(5)\
            .all()
        
        recent_attempts = []
        for attempt in recent_attempts_query:
            test = Test.query.get(attempt.test_id)
            recent_attempts.append({
                'attempt_id': attempt.id,
                'test_id': attempt.test_id,
                'company': test.company if test else 'Unknown',
                'score': attempt.score,
                'total_questions': attempt.total_questions,
                'percentage': round(attempt.calculate_percentage(), 1),
                'completed_at': attempt.completed_at.isoformat() if attempt.completed_at else None,
                'time_taken': attempt.time_taken
            })
        
        # Get progress by subject
        progress_metrics = ProgressMetrics.query.filter_by(user_id=current_user.id).all()
        progress_by_subject = []
        
        for metric in progress_metrics:
            # Calculate trend (simplified - could be enhanced with historical data)
            trend = "stable"
            if metric.accuracy_rate > 75:
                trend = "strong"
            elif metric.accuracy_rate > 50:
                trend = "improving"
            else:
                trend = "needs_work"
            
            progress_by_subject.append({
                'subject': metric.subject_area,
                'accuracy_rate': round(metric.accuracy_rate, 1),
                'total_attempts': metric.total_attempts,
                'trend': trend,
                'last_updated': metric.last_updated.isoformat() if metric.last_updated else None
            })
        
        # Get recommended companies based on user performance
        recommended_companies = _get_recommended_companies(current_user, progress_metrics)
        
        # Get available companies with user statistics
        available_companies = _get_available_companies_with_stats(current_user)
        
        # Prepare response
        dashboard_data = {
            'user_info': {
                'name': current_user.name,
                'email': current_user.email,
                'year': current_user.year,
                'branch': current_user.branch,
                'member_since': current_user.created_at.isoformat() if current_user.created_at else None
            },
            'statistics': {
                'total_tests_taken': total_tests,
                'average_score': round(average_score, 1),
                'best_score': round(best_score, 1),
                'total_time_spent': total_time_spent,
                'tests_this_week': tests_this_week,
                'improvement_trend': improvement_trend
            },
            'recent_attempts': recent_attempts,
            'progress_by_subject': progress_by_subject,
            'recommended_companies': recommended_companies,
            'available_companies': available_companies
        }
        
        logger.info(f"Dashboard data retrieved for user {current_user.id}")
        
        return jsonify(dashboard_data), 200
        
    except SQLAlchemyError as e:
        logger.error(f"Database error getting dashboard data: {e}")
        return jsonify({
            'error': True,
            'message': 'Database error',
            'code': 'DATABASE_ERROR'
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error getting dashboard data: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@dashboard_bp.route('/companies', methods=['GET'])
@jwt_required_custom()
def get_companies():
    """
    Get list of available companies with enhanced user statistics
    
    GET /api/companies
    
    Query Parameters:
    - include_stats: boolean (default: true) - Include user-specific statistics
    - sort_by: string (default: 'name') - Sort by 'name', 'attempts', 'score'
    
    Response:
    {
        "companies": [
            {
                "name": "TCS NQT",
                "test_count": 3,
                "latest_test": "2025-01-17T10:30:00Z",
                "supported": true,
                "user_stats": {
                    "attempts": 2,
                    "best_score": 85.0,
                    "average_score": 78.5,
                    "last_attempt": "2025-01-16T14:30:00Z"
                },
                "difficulty_level": "medium",
                "recommended": true
            }
        ],
        "total_companies": 16,
        "user_summary": {
            "companies_attempted": 5,
            "total_attempts": 15,
            "favorite_company": "TCS NQT"
        }
    }
    """
    try:
        current_user = get_current_user()
        
        # Get query parameters
        include_stats = request.args.get('include_stats', 'true').lower() == 'true'
        sort_by = request.args.get('sort_by', 'name')
        
        # Get all companies with test statistics
        companies_data = _get_available_companies_with_stats(current_user, include_user_stats=include_stats)
        
        # Sort companies based on sort_by parameter
        if sort_by == 'attempts':
            companies_data.sort(key=lambda x: x.get('user_stats', {}).get('attempts', 0), reverse=True)
        elif sort_by == 'score':
            companies_data.sort(key=lambda x: x.get('user_stats', {}).get('best_score', 0), reverse=True)
        else:  # default to name
            companies_data.sort(key=lambda x: x['name'])
        
        # Calculate user summary
        user_attempts = TestAttempt.query.filter_by(user_id=current_user.id).all()
        companies_attempted = set()
        company_attempt_counts = {}
        
        for attempt in user_attempts:
            test = Test.query.get(attempt.test_id)
            if test:
                companies_attempted.add(test.company)
                company_attempt_counts[test.company] = company_attempt_counts.get(test.company, 0) + 1
        
        favorite_company = None
        if company_attempt_counts:
            favorite_company = max(company_attempt_counts.items(), key=lambda x: x[1])[0]
        
        user_summary = {
            'companies_attempted': len(companies_attempted),
            'total_attempts': len(user_attempts),
            'favorite_company': favorite_company
        }
        
        response_data = {
            'companies': companies_data,
            'total_companies': len(companies_data),
            'user_summary': user_summary
        }
        
        logger.info(f"Companies list retrieved for user {current_user.id}")
        
        return jsonify(response_data), 200
        
    except SQLAlchemyError as e:
        logger.error(f"Database error getting companies: {e}")
        return jsonify({
            'error': True,
            'message': 'Database error',
            'code': 'DATABASE_ERROR'
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error getting companies: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@dashboard_bp.route('/test-history', methods=['GET'])
@jwt_required_custom()
def get_test_history():
    """
    Get detailed test history for the current user
    
    GET /api/test-history
    
    Query Parameters:
    - page: int (default: 1) - Page number for pagination
    - per_page: int (default: 10) - Items per page (max 50)
    - company: string (optional) - Filter by company name
    - date_from: string (optional) - Filter from date (ISO format)
    - date_to: string (optional) - Filter to date (ISO format)
    
    Response:
    {
        "attempts": [
            {
                "attempt_id": 123,
                "test_id": 45,
                "company": "TCS NQT",
                "score": 18,
                "total_questions": 20,
                "percentage": 90.0,
                "time_taken": 3600,
                "started_at": "2025-01-17T09:30:00Z",
                "completed_at": "2025-01-17T10:30:00Z",
                "section_scores": {
                    "Quantitative Aptitude": {"score": 7, "total": 8, "percentage": 87.5}
                }
            }
        ],
        "pagination": {
            "page": 1,
            "per_page": 10,
            "total": 25,
            "pages": 3,
            "has_next": true,
            "has_prev": false
        },
        "summary": {
            "total_attempts": 25,
            "companies_count": 5,
            "average_score": 78.5,
            "best_performance": {
                "company": "Infosys",
                "percentage": 95.0,
                "date": "2025-01-15T14:30:00Z"
            }
        }
    }
    """
    try:
        current_user = get_current_user()
        
        # Get query parameters
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(50, max(1, int(request.args.get('per_page', 10))))
        company_filter = request.args.get('company')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Build query
        query = TestAttempt.query.filter_by(user_id=current_user.id)
        
        # Apply filters
        if company_filter:
            # Join with Test table to filter by company
            query = query.join(Test).filter(Test.company.ilike(f'%{company_filter}%'))
        
        if date_from:
            try:
                date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                query = query.filter(TestAttempt.completed_at >= date_from_obj)
            except ValueError:
                return jsonify({
                    'error': True,
                    'message': 'Invalid date_from format. Use ISO format.',
                    'code': 'INVALID_DATE_FORMAT'
                }), 400
        
        if date_to:
            try:
                date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                query = query.filter(TestAttempt.completed_at <= date_to_obj)
            except ValueError:
                return jsonify({
                    'error': True,
                    'message': 'Invalid date_to format. Use ISO format.',
                    'code': 'INVALID_DATE_FORMAT'
                }), 400
        
        # Order by completion date (most recent first)
        query = query.order_by(desc(TestAttempt.completed_at))
        
        # Paginate results
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Format attempts data
        attempts = []
        for attempt in pagination.items:
            test = Test.query.get(attempt.test_id)
            
            # Calculate section scores (simplified - could be enhanced with stored data)
            section_scores = _calculate_section_scores_for_attempt(attempt)
            
            attempts.append({
                'attempt_id': attempt.id,
                'test_id': attempt.test_id,
                'company': test.company if test else 'Unknown',
                'score': attempt.score,
                'total_questions': attempt.total_questions,
                'percentage': round(attempt.calculate_percentage(), 1),
                'time_taken': attempt.time_taken,
                'started_at': attempt.started_at.isoformat() if attempt.started_at else None,
                'completed_at': attempt.completed_at.isoformat() if attempt.completed_at else None,
                'section_scores': section_scores
            })
        
        # Calculate summary statistics
        all_attempts = TestAttempt.query.filter_by(user_id=current_user.id).all()
        total_attempts = len(all_attempts)
        
        if total_attempts > 0:
            companies_set = set()
            total_percentage = 0
            best_attempt = None
            best_percentage = 0
            
            for attempt in all_attempts:
                test = Test.query.get(attempt.test_id)
                if test:
                    companies_set.add(test.company)
                
                percentage = attempt.calculate_percentage()
                total_percentage += percentage
                
                if percentage > best_percentage:
                    best_percentage = percentage
                    best_attempt = attempt
            
            average_score = total_percentage / total_attempts
            
            best_performance = None
            if best_attempt:
                best_test = Test.query.get(best_attempt.test_id)
                best_performance = {
                    'company': best_test.company if best_test else 'Unknown',
                    'percentage': round(best_percentage, 1),
                    'date': best_attempt.completed_at.isoformat() if best_attempt.completed_at else None
                }
        else:
            companies_set = set()
            average_score = 0
            best_performance = None
        
        summary = {
            'total_attempts': total_attempts,
            'companies_count': len(companies_set),
            'average_score': round(average_score, 1),
            'best_performance': best_performance
        }
        
        # Prepare pagination info
        pagination_info = {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
        
        response_data = {
            'attempts': attempts,
            'pagination': pagination_info,
            'summary': summary
        }
        
        logger.info(f"Test history retrieved for user {current_user.id} (page {page})")
        
        return jsonify(response_data), 200
        
    except ValueError as e:
        return jsonify({
            'error': True,
            'message': f'Invalid parameter: {str(e)}',
            'code': 'INVALID_PARAMETER'
        }), 400
    except SQLAlchemyError as e:
        logger.error(f"Database error getting test history: {e}")
        return jsonify({
            'error': True,
            'message': 'Database error',
            'code': 'DATABASE_ERROR'
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error getting test history: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

# Helper functions

def _get_recommended_companies(user, progress_metrics):
    """Generate company recommendations based on user performance"""
    recommendations = []
    
    # Simple recommendation logic - can be enhanced with ML
    strong_subjects = [m for m in progress_metrics if m.accuracy_rate > 75]
    weak_subjects = [m for m in progress_metrics if m.accuracy_rate < 50]
    
    # Company recommendations based on subject strengths
    company_subject_mapping = {
        'TCS NQT': ['Quantitative Aptitude', 'Logical Reasoning'],
        'Infosys': ['Logical Reasoning', 'Verbal Ability'],
        'Capgemini': ['Quantitative Aptitude', 'Technical Skills'],
        'Wipro': ['Logical Reasoning', 'Technical Skills'],
        'Accenture': ['Verbal Ability', 'Logical Reasoning']
    }
    
    for company, required_subjects in company_subject_mapping.items():
        strong_match = any(m.subject_area in required_subjects for m in strong_subjects)
        if strong_match:
            reason = f"Based on your strong performance in {', '.join(required_subjects)}"
            recommendations.append({
                'company': company,
                'reason': reason,
                'difficulty_match': 'medium',
                'confidence': 'high' if len([m for m in strong_subjects if m.subject_area in required_subjects]) > 1 else 'medium'
            })
    
    # Limit to top 3 recommendations
    return recommendations[:3]

def _get_available_companies_with_stats(user, include_user_stats=True):
    """Get companies with user-specific statistics"""
    # Supported companies list
    SUPPORTED_COMPANIES = [
        'TCS NQT', 'Infosys', 'Capgemini', 'Wipro', 'Accenture', 
        'Cognizant', 'HCL', 'Tech Mahindra', 'IBM', 'Microsoft',
        'Amazon', 'Google', 'Deloitte', 'EY', 'KPMG', 'PwC'
    ]
    
    # Get test statistics from database
    company_stats = db.session.query(
        Test.company,
        func.count(Test.id).label('test_count'),
        func.max(Test.created_at).label('latest_test')
    ).group_by(Test.company).all()
    
    companies = []
    
    for stat in company_stats:
        company_data = {
            'name': stat.company,
            'test_count': stat.test_count,
            'latest_test': stat.latest_test.isoformat() if stat.latest_test else None,
            'supported': stat.company in SUPPORTED_COMPANIES,
            'difficulty_level': 'medium',  # Default - could be enhanced
            'recommended': False  # Will be set based on user performance
        }
        
        if include_user_stats:
            user_stats = _get_user_company_stats(user, stat.company)
            company_data['user_stats'] = user_stats
            
            # Mark as recommended if user has good performance
            if user_stats['attempts'] > 0 and user_stats['average_score'] > 70:
                company_data['recommended'] = True
        
        companies.append(company_data)
    
    # Add supported companies that don't have tests yet
    existing_companies = {stat.company for stat in company_stats}
    for company in SUPPORTED_COMPANIES:
        if company not in existing_companies:
            company_data = {
                'name': company,
                'test_count': 0,
                'latest_test': None,
                'supported': True,
                'difficulty_level': 'medium',
                'recommended': False
            }
            
            if include_user_stats:
                company_data['user_stats'] = {
                    'attempts': 0,
                    'best_score': 0,
                    'average_score': 0,
                    'last_attempt': None
                }
            
            companies.append(company_data)
    
    return companies

def _get_user_company_stats(user, company_name):
    """Get user statistics for a specific company"""
    # Get user's attempts for this company
    attempts = db.session.query(TestAttempt)\
        .join(Test)\
        .filter(Test.company == company_name, TestAttempt.user_id == user.id)\
        .all()
    
    if not attempts:
        return {
            'attempts': 0,
            'best_score': 0,
            'average_score': 0,
            'last_attempt': None
        }
    
    percentages = [attempt.calculate_percentage() for attempt in attempts]
    best_score = max(percentages)
    average_score = sum(percentages) / len(percentages)
    last_attempt = max(attempts, key=lambda x: x.completed_at or datetime.min)
    
    return {
        'attempts': len(attempts),
        'best_score': round(best_score, 1),
        'average_score': round(average_score, 1),
        'last_attempt': last_attempt.completed_at.isoformat() if last_attempt.completed_at else None
    }

def _calculate_section_scores_for_attempt(attempt):
    """Calculate section-wise scores for a test attempt"""
    # This is a simplified version - in a real implementation,
    # you might want to store section scores directly
    test = Test.query.get(attempt.test_id)
    if not test:
        return {}
    
    questions = test.questions
    user_answers = attempt.get_answers()
    section_scores = {}
    
    for question in questions:
        section = question.section
        if section not in section_scores:
            section_scores[section] = {'correct': 0, 'total': 0}
        
        section_scores[section]['total'] += 1
        
        question_id_str = str(question.id)
        user_answer = user_answers.get(question_id_str, '').strip().upper()
        correct_answer = question.correct_answer.strip().upper()
        
        if user_answer == correct_answer:
            section_scores[section]['correct'] += 1
    
    # Format for response
    formatted_scores = {}
    for section, scores in section_scores.items():
        percentage = (scores['correct'] / scores['total'] * 100) if scores['total'] > 0 else 0
        formatted_scores[section] = {
            'score': scores['correct'],
            'total': scores['total'],
            'percentage': round(percentage, 1)
        }
    
    return formatted_scores

# Error handlers for the blueprint
@dashboard_bp.errorhandler(404)
def dashboard_not_found(error):
    return jsonify({
        'error': True,
        'message': 'Dashboard endpoint not found',
        'code': 'ENDPOINT_NOT_FOUND'
    }), 404

@dashboard_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'error': True,
        'message': 'Method not allowed',
        'code': 'METHOD_NOT_ALLOWED'
    }), 405