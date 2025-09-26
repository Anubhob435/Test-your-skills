import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import logging
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Import configuration
from config import config

# Get configuration based on environment
config_name = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config.get(config_name, config['default']))

# Setup logging first
from logging_config import setup_logging
setup_logging(app)
logger = logging.getLogger(__name__)

# Initialize extensions
from models import db
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
jwt = JWTManager(app)
CORS(app)

# Setup error handlers
from error_handlers import register_error_handlers
register_error_handlers(app)

# Setup request logging
from request_logging import setup_request_logging
setup_request_logging(app)

# Initialize security measures
from security_utils import init_security, security_middleware, setup_security_logging
init_security(app)
setup_security_logging()

# Add security middleware
app.before_request(security_middleware)

# Import models after db initialization
from models import User, Test, Question, TestAttempt, ProgressMetrics

# Import and register blueprints
from auth_routes import auth_bp, web_auth_bp
from test_routes import test_bp
from dashboard_routes import dashboard_bp
from profile_routes import profile_bp
from leaderboard_routes import leaderboard_bp
from admin_routes import admin_bp
app.register_blueprint(auth_bp)
app.register_blueprint(web_auth_bp)
app.register_blueprint(test_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(leaderboard_bp)
app.register_blueprint(admin_bp)

# Initialize authentication middleware
from auth_middleware import AuthMiddleware
auth_middleware = AuthMiddleware(app)

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Basic route for testing
@app.route('/')
def index():
    return render_template('index.html')

# Style test route
@app.route('/test-styles')
def test_styles():
    return render_template('test-styles.html')

# Dashboard route
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# Test history route
@app.route('/test-history')
@login_required
def test_history():
    return render_template('test-history.html')

# Profile route
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

# Leaderboard route
@app.route('/leaderboard')
@login_required
def leaderboard():
    return render_template('leaderboard.html')

# Test interface route
@app.route('/test/<int:test_id>')
@login_required
def test_interface(test_id):
    """Render test interface page with actual test data"""
    try:
        # Fetch test from database
        test = Test.query.get(test_id)
        if not test:
            flash('Test not found', 'error')
            return redirect(url_for('dashboard'))
        
        # Get question count
        question_count = Question.query.filter_by(test_id=test_id).count()
        
        # Prepare test data for template
        test_data = {
            'id': test.id,
            'company': test.company,
            'year': test.year,
            'total_questions': question_count,
            'time_limit': 3600,  # 1 hour in seconds
            'sections': []  # Will be loaded via API
        }
        
        return render_template('test.html', test=test_data)
        
    except Exception as e:
        logger.error(f"Error loading test interface for test {test_id}: {e}")
        flash('Error loading test', 'error')
        return redirect(url_for('dashboard'))

# Test results route
@app.route('/test/<int:test_id>/results/<int:attempt_id>')
@login_required
def test_results(test_id, attempt_id):
    """Render test results page with actual data"""
    try:
        # Fetch test attempt from database
        attempt = TestAttempt.query.get(attempt_id)
        if not attempt:
            flash('Test attempt not found', 'error')
            return redirect(url_for('dashboard'))
        
        # Verify the attempt belongs to the current user
        if attempt.user_id != current_user.id:
            flash('Access denied', 'error')
            return redirect(url_for('dashboard'))
        
        # Fetch test data
        test = Test.query.get(test_id)
        if not test or test.id != attempt.test_id:
            flash('Test not found', 'error')
            return redirect(url_for('dashboard'))
        
        # Prepare data for template
        test_data = {
            'id': test.id,
            'company': test.company,
            'year': test.year
        }
        
        attempt_data = {
            'id': attempt.id,
            'score': attempt.score,
            'total_questions': attempt.total_questions,
            'time_taken': attempt.time_taken,
            'percentage': (attempt.score / attempt.total_questions * 100) if attempt.total_questions > 0 else 0,
            'completed_at': attempt.completed_at,
            'answers': attempt.answers or {}
        }
        
        return render_template('results.html', test=test_data, attempt=attempt_data)
        
    except Exception as e:
        logger.error(f"Error loading test results for attempt {attempt_id}: {e}")
        flash('Error loading results', 'error')
        return redirect(url_for('dashboard'))

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': 'connected' if db.session.execute(db.text('SELECT 1')).scalar() == 1 else 'disconnected'
    })

# Error handlers are now registered in error_handlers.py

if __name__ == '__main__':
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        logger.info("Database tables created successfully")
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))