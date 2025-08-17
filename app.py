import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
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

# Initialize extensions
from models import db
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
jwt = JWTManager(app)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import models after db initialization
from models import User, Test, Question, TestAttempt, ProgressMetrics

# Import and register blueprints
from auth_routes import auth_bp
from test_routes import test_bp
app.register_blueprint(auth_bp)
app.register_blueprint(test_bp)

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

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': 'connected' if db.session.execute(db.text('SELECT 1')).scalar() == 1 else 'disconnected'
    })

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found', 'message': 'The requested resource was not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    logger.error(f'Server Error: {error}')
    return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred'}), 500

@app.errorhandler(403)
def forbidden_error(error):
    return jsonify({'error': 'Forbidden', 'message': 'You do not have permission to access this resource'}), 403

if __name__ == '__main__':
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        logger.info("Database tables created successfully")
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))