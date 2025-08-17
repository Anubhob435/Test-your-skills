#!/usr/bin/env python3
"""
Test script to verify the setup is working correctly
Also includes helper functions for testing
"""

import os
import tempfile
from datetime import datetime
from flask import Flask
from models import db, User, Test, Question, TestAttempt, ProgressMetrics


def create_test_app():
    """Create a test Flask application with in-memory database"""
    app = Flask(__name__)
    
    # Test configuration
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Initialize extensions
    db.init_app(app)
    
    # Initialize Flask-Login
    from flask_login import LoginManager
    from flask_jwt_extended import JWTManager
    
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    jwt = JWTManager(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # Import and register blueprints
    from auth_routes import auth_bp
    from test_routes import test_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(test_bp)
    
    # Initialize authentication middleware
    from auth_middleware import AuthMiddleware
    auth_middleware = AuthMiddleware(app)
    
    with app.app_context():
        db.create_all()
    
    return app


def create_test_user(email='test@uem.edu.in', name='Test User', is_admin=False):
    """Create a test user"""
    from auth_service import AuthService
    
    user = User(
        email=email,
        name=name,
        year=2025,
        branch='Computer Science',
        is_admin=is_admin
    )
    user.set_password('testpass123')
    
    db.session.add(user)
    db.session.commit()
    
    return user


def create_test_data():
    """Create sample test data for testing"""
    # Create a test
    test = Test(
        company='TCS NQT',
        year=2025,
        pattern_data='{"sections": ["Quantitative Aptitude", "Logical Reasoning"]}'
    )
    
    db.session.add(test)
    db.session.flush()  # Get test ID
    
    # Create sample questions
    questions = []
    
    # Quantitative Aptitude questions
    for i in range(3):
        question = Question(
            test_id=test.id,
            section='Quantitative Aptitude',
            question_text=f'What is {i+1} + {i+1}?',
            options=[str((i+1)*2-1), str((i+1)*2), str((i+1)*2+1), str((i+1)*2+2)],
            correct_answer='B',  # Second option is always correct
            explanation=f'The answer is {(i+1)*2}',
            difficulty='easy'
        )
        questions.append(question)
        db.session.add(question)
    
    # Logical Reasoning questions
    for i in range(2):
        question = Question(
            test_id=test.id,
            section='Logical Reasoning',
            question_text=f'If A > B and B > C, then A ? C',
            options=['A < C', 'A > C', 'A = C', 'Cannot determine'],
            correct_answer='B',  # A > C
            explanation='Since A > B and B > C, by transitivity A > C',
            difficulty='medium'
        )
        questions.append(question)
        db.session.add(question)
    
    db.session.commit()
    
    return test, questions

def test_imports():
    """Test that all imports work correctly"""
    print("Testing imports...")
    
    try:
        from app import app
        print("✓ Flask app imported successfully")
        
        from models import User, Test, Question, TestAttempt, ProgressMetrics
        print("✓ Models imported successfully")
        
        from config import config
        print("✓ Config imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False

def test_health_endpoint():
    """Test the health endpoint"""
    print("\nTesting health endpoint...")
    
    try:
        from app import app
        
        with app.test_client() as client:
            response = client.get('/health')
            data = response.get_json()
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {data}")
            
            if response.status_code == 200 and data.get('status') == 'healthy':
                print("✓ Health endpoint working correctly")
                return True
            else:
                print("✗ Health endpoint not working correctly")
                return False
                
    except Exception as e:
        print(f"✗ Health endpoint error: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    print("\nTesting database connection...")
    
    try:
        from app import app
        from models import db, User
        
        with app.app_context():
            # Test basic query
            user_count = User.query.count()
            print(f"✓ Database connected - User count: {user_count}")
            
            # Test admin user exists
            admin_user = User.query.filter_by(email='admin@uem.edu.in').first()
            if admin_user:
                print("✓ Admin user found in database")
            else:
                print("✗ Admin user not found in database")
            
            return True
            
    except Exception as e:
        print(f"✗ Database connection error: {e}")
        return False

def test_templates():
    """Test that templates render correctly"""
    print("\nTesting template rendering...")
    
    try:
        from app import app
        
        with app.test_client() as client:
            response = client.get('/')
            
            if response.status_code == 200:
                print("✓ Index template renders successfully")
                return True
            else:
                print(f"✗ Index template error - Status: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"✗ Template rendering error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("UEM Placement Platform - Setup Verification")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_health_endpoint,
        test_database_connection,
        test_templates
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Setup is working correctly.")
        print("\nYou can now run the application with:")
        print("  python run.py")
        print("  or")
        print("  python app.py")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    print("=" * 50)

if __name__ == '__main__':
    main()