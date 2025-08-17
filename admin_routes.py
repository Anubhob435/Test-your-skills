"""
Admin routes for UEM Placement Platform

This module provides REST API endpoints for admin functionality:
- Admin authentication and session management
- Student analytics and monitoring
- Manual test creation and management
- Admin dashboard data
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from auth_middleware import admin_required, get_current_user
from auth_service import AuthService, APIException
from models import User, Test, Question, TestAttempt, ProgressMetrics, db
from analytics_service import AnalyticsService
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Create admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Admin Authentication Routes

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    """
    Admin login page and authentication
    
    GET: Display admin login form
    POST: Process admin login credentials
    """
    if request.method == 'GET':
        # Check if already logged in as admin
        if current_user.is_authenticated and current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        
        return render_template('admin/login.html')
    
    try:
        # Get form data or JSON data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        # Validate required fields
        if not email or not password:
            error_msg = "Email and password are required"
            if request.is_json:
                return jsonify({
                    'success': False,
                    'error': error_msg,
                    'code': 'MISSING_CREDENTIALS'
                }), 400
            else:
                flash(error_msg, 'error')
                return render_template('admin/login.html')
        
        # Authenticate user
        success, message, user, token = AuthService.authenticate_user(email, password)
        
        if not success:
            if request.is_json:
                return jsonify({
                    'success': False,
                    'error': message,
                    'code': 'AUTHENTICATION_FAILED'
                }), 401
            else:
                flash(message, 'error')
                return render_template('admin/login.html')
        
        # Check if user is admin
        if not user.is_admin:
            error_msg = "Admin privileges required"
            if request.is_json:
                return jsonify({
                    'success': False,
                    'error': error_msg,
                    'code': 'INSUFFICIENT_PRIVILEGES'
                }), 403
            else:
                flash(error_msg, 'error')
                return render_template('admin/login.html')
        
        # Log in user
        login_user(user)
        
        logger.info(f"Admin logged in: {email}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Admin login successful',
                'user': user.to_dict(),
                'token': token,
                'redirect_url': url_for('admin.dashboard')
            }), 200
        else:
            flash('Admin login successful', 'success')
            return redirect(url_for('admin.dashboard'))
        
    except Exception as e:
        logger.error(f"Admin login error: {e}")
        error_msg = 'Login failed. Please try again.'
        
        if request.is_json:
            return jsonify({
                'success': False,
                'error': error_msg,
                'code': 'INTERNAL_ERROR'
            }), 500
        else:
            flash(error_msg, 'error')
            return render_template('admin/login.html')

@admin_bp.route('/logout', methods=['POST'])
@admin_required
def admin_logout():
    """Admin logout"""
    try:
        user_email = current_user.email if current_user.is_authenticated else 'Unknown'
        logout_user()
        
        logger.info(f"Admin logged out: {user_email}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Admin logged out successfully',
                'redirect_url': url_for('admin.admin_login')
            }), 200
        else:
            flash('Logged out successfully', 'success')
            return redirect(url_for('admin.admin_login'))
        
    except Exception as e:
        logger.error(f"Admin logout error: {e}")
        return jsonify({
            'success': False,
            'error': 'Logout failed',
            'code': 'LOGOUT_ERROR'
        }), 500

# Admin Dashboard Routes

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """
    Admin dashboard with overview analytics
    """
    try:
        # Get dashboard statistics
        stats = get_admin_dashboard_stats()
        
        if request.is_json:
            return jsonify({
                'success': True,
                'stats': stats
            }), 200
        else:
            return render_template('admin/dashboard.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Admin dashboard error: {e}")
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'Failed to load dashboard',
                'code': 'DASHBOARD_ERROR'
            }), 500
        else:
            flash('Failed to load dashboard', 'error')
            return render_template('admin/dashboard.html', stats={})

@admin_bp.route('/api/dashboard-stats')
@admin_required
def api_dashboard_stats():
    """
    API endpoint for admin dashboard statistics
    """
    try:
        stats = get_admin_dashboard_stats()
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Dashboard stats API error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve dashboard statistics',
            'code': 'STATS_ERROR'
        }), 500

# Student Management Routes

@admin_bp.route('/api/students')
@admin_required
def api_students():
    """
    Get list of students with pagination and filtering
    """
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        search = request.args.get('search', '').strip()
        branch = request.args.get('branch', '').strip()
        year = request.args.get('year', type=int)
        
        # Build query
        query = User.query.filter_by(is_admin=False)
        
        if search:
            query = query.filter(
                db.or_(
                    User.name.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%')
                )
            )
        
        if branch:
            query = query.filter(User.branch.ilike(f'%{branch}%'))
        
        if year:
            query = query.filter(User.year == year)
        
        # Order by creation date (newest first)
        query = query.order_by(User.created_at.desc())
        
        # Paginate
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        students = []
        for user in pagination.items:
            student_data = user.to_dict()
            
            # Add additional statistics
            total_attempts = TestAttempt.query.filter_by(user_id=user.id).count()
            avg_score = db.session.query(db.func.avg(TestAttempt.score)).filter_by(user_id=user.id).scalar()
            
            student_data.update({
                'total_attempts': total_attempts,
                'average_score': round(avg_score, 2) if avg_score else 0,
                'last_activity': get_user_last_activity(user.id)
            })
            
            students.append(student_data)
        
        return jsonify({
            'success': True,
            'students': students,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Students API error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve students',
            'code': 'STUDENTS_ERROR'
        }), 500

@admin_bp.route('/api/students/<int:student_id>')
@admin_required
def api_student_detail(student_id):
    """
    Get detailed information about a specific student
    """
    try:
        student = User.query.filter_by(id=student_id, is_admin=False).first()
        if not student:
            return jsonify({
                'success': False,
                'error': 'Student not found',
                'code': 'STUDENT_NOT_FOUND'
            }), 404
        
        # Get student's test attempts with test company info
        attempts = db.session.query(TestAttempt, Test).join(Test).filter(
            TestAttempt.user_id == student_id
        ).order_by(TestAttempt.started_at.desc()).all()
        
        # Get progress metrics
        progress = AnalyticsService.calculate_user_progress(student_id)
        
        # Get weak areas
        weak_areas = AnalyticsService.get_weak_areas(student_id)
        
        student_data = student.to_dict()
        
        # Format test attempts with company info
        formatted_attempts = []
        for attempt, test in attempts:
            attempt_data = attempt.to_dict()
            attempt_data['test_company'] = test.company
            attempt_data['test_year'] = test.year
            formatted_attempts.append(attempt_data)
        
        student_data.update({
            'test_attempts': formatted_attempts,
            'progress': progress,
            'weak_areas': weak_areas,
            'total_attempts': len(attempts),
            'average_score': sum(attempt.score for attempt, test in attempts) / len(attempts) if attempts else 0
        })
        
        return jsonify({
            'success': True,
            'student': student_data
        }), 200
        
    except Exception as e:
        logger.error(f"Student detail API error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve student details',
            'code': 'STUDENT_DETAIL_ERROR'
        }), 500

# Test Management Routes

@admin_bp.route('/api/tests')
@admin_required
def api_tests():
    """
    Get list of tests with pagination
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        company = request.args.get('company', '').strip()
        
        query = Test.query
        
        if company:
            query = query.filter(Test.company.ilike(f'%{company}%'))
        
        query = query.order_by(Test.created_at.desc())
        
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        tests = []
        for test in pagination.items:
            # Create test data manually to avoid JSON issues
            test_data = {
                'id': test.id,
                'company': test.company,
                'year': test.year,
                'created_at': test.created_at.isoformat() if test.created_at else None,
                'question_count': Question.query.filter_by(test_id=test.id).count()
            }
            
            # Add attempt statistics
            attempt_count = TestAttempt.query.filter_by(test_id=test.id).count()
            avg_score = db.session.query(db.func.avg(TestAttempt.score)).filter_by(test_id=test.id).scalar()
            
            test_data.update({
                'attempt_count': attempt_count,
                'average_score': round(avg_score, 2) if avg_score else 0
            })
            
            tests.append(test_data)
        
        return jsonify({
            'success': True,
            'tests': tests,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Tests API error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve tests',
            'code': 'TESTS_ERROR'
        }), 500

@admin_bp.route('/api/tests', methods=['POST'])
@admin_required
def api_create_test():
    """
    Create a new test manually
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided',
                'code': 'INVALID_REQUEST'
            }), 400
        
        # Validate required fields
        company = data.get('company', '').strip()
        year = data.get('year', 2025)
        questions_data = data.get('questions', [])
        
        if not company:
            return jsonify({
                'success': False,
                'error': 'Company name is required',
                'code': 'MISSING_COMPANY'
            }), 400
        
        if not questions_data or not isinstance(questions_data, list):
            return jsonify({
                'success': False,
                'error': 'Questions are required',
                'code': 'MISSING_QUESTIONS'
            }), 400
        
        # Create test
        test = Test(
            company=company,
            year=year,
            pattern_data=data.get('pattern_data', '{}')
        )
        
        db.session.add(test)
        db.session.flush()  # Get test ID
        
        # Create questions
        for q_data in questions_data:
            question = Question(
                test_id=test.id,
                section=q_data.get('section', 'General'),
                question_text=q_data.get('question_text', ''),
                options=q_data.get('options', []),
                correct_answer=q_data.get('correct_answer', ''),
                explanation=q_data.get('explanation', ''),
                difficulty=q_data.get('difficulty', 'medium'),
                topic=q_data.get('topic', '')
            )
            db.session.add(question)
        
        db.session.commit()
        
        logger.info(f"Admin created test: {company} {year} (ID: {test.id})")
        
        # Refresh the test object to get the questions
        db.session.refresh(test)
        
        return jsonify({
            'success': True,
            'message': 'Test created successfully',
            'test': {
                'id': test.id,
                'company': test.company,
                'year': test.year,
                'question_count': len(test.questions),
                'created_at': test.created_at.isoformat() if test.created_at else None
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Create test API error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to create test',
            'code': 'CREATE_TEST_ERROR'
        }), 500

# Analytics Routes

@admin_bp.route('/api/analytics/overview')
@admin_required
def api_analytics_overview():
    """
    Get platform analytics overview
    """
    try:
        analytics = get_platform_analytics()
        return jsonify({
            'success': True,
            'analytics': analytics
        }), 200
        
    except Exception as e:
        logger.error(f"Analytics overview API error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve analytics',
            'code': 'ANALYTICS_ERROR'
        }), 500

# Helper Functions

def get_admin_dashboard_stats():
    """Get statistics for admin dashboard"""
    try:
        # Basic counts
        total_students = User.query.filter_by(is_admin=False).count()
        total_tests = Test.query.count()
        total_attempts = TestAttempt.query.count()
        
        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_registrations = User.query.filter(
            User.created_at >= week_ago,
            User.is_admin == False
        ).count()
        
        recent_attempts = TestAttempt.query.filter(
            TestAttempt.started_at >= week_ago
        ).count()
        
        # Average scores
        avg_score = db.session.query(db.func.avg(TestAttempt.score)).scalar()
        
        # Popular companies (top 5)
        popular_companies = db.session.query(
            Test.company,
            db.func.count(TestAttempt.id).label('attempt_count')
        ).join(TestAttempt).group_by(Test.company).order_by(
            db.func.count(TestAttempt.id).desc()
        ).limit(5).all()
        
        return {
            'total_students': total_students,
            'total_tests': total_tests,
            'total_attempts': total_attempts,
            'recent_registrations': recent_registrations,
            'recent_attempts': recent_attempts,
            'average_score': round(avg_score, 2) if avg_score else 0,
            'popular_companies': [
                {'company': company, 'attempts': count}
                for company, count in popular_companies
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return {}

def get_user_last_activity(user_id):
    """Get user's last activity timestamp"""
    try:
        last_attempt = TestAttempt.query.filter_by(user_id=user_id).order_by(
            TestAttempt.started_at.desc()
        ).first()
        
        if last_attempt:
            return last_attempt.started_at.isoformat()
        
        # If no test attempts, return registration date
        user = User.query.get(user_id)
        if user and user.created_at:
            return user.created_at.isoformat()
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting user last activity: {e}")
        return None

def get_platform_analytics():
    """Get comprehensive platform analytics"""
    try:
        # User analytics
        total_users = User.query.filter_by(is_admin=False).count()
        active_users = db.session.query(TestAttempt.user_id).distinct().count()
        
        # Test analytics
        total_tests = Test.query.count()
        total_questions = Question.query.count()
        total_attempts = TestAttempt.query.count()
        
        # Performance analytics
        avg_score = db.session.query(db.func.avg(TestAttempt.score)).scalar()
        completion_rate = (TestAttempt.query.filter(TestAttempt.completed_at.isnot(None)).count() / 
                          max(total_attempts, 1)) * 100
        
        # Time-based analytics (last 30 days)
        month_ago = datetime.utcnow() - timedelta(days=30)
        monthly_registrations = User.query.filter(
            User.created_at >= month_ago,
            User.is_admin == False
        ).count()
        
        monthly_attempts = TestAttempt.query.filter(
            TestAttempt.started_at >= month_ago
        ).count()
        
        return {
            'users': {
                'total': total_users,
                'active': active_users,
                'monthly_registrations': monthly_registrations
            },
            'tests': {
                'total_tests': total_tests,
                'total_questions': total_questions,
                'total_attempts': total_attempts,
                'monthly_attempts': monthly_attempts
            },
            'performance': {
                'average_score': round(avg_score, 2) if avg_score else 0,
                'completion_rate': round(completion_rate, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting platform analytics: {e}")
        return {}

# Error handlers for admin blueprint
@admin_bp.errorhandler(403)
def handle_forbidden(error):
    """Handle forbidden access"""
    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Admin privileges required',
            'code': 'INSUFFICIENT_PRIVILEGES'
        }), 403
    else:
        flash('Admin privileges required', 'error')
        return redirect(url_for('admin.admin_login'))

@admin_bp.errorhandler(401)
def handle_unauthorized(error):
    """Handle unauthorized access"""
    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Authentication required',
            'code': 'AUTHENTICATION_REQUIRED'
        }), 401
    else:
        return redirect(url_for('admin.admin_login'))