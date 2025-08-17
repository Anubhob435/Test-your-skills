#!/usr/bin/env python3
"""
Database initialization script for UEM Placement Preparation Platform
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, init, migrate, upgrade
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import app and models
from app import app
from models import db, User

def init_database():
    """Initialize the database with tables"""
    print("Initializing database...")
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✓ Database tables created successfully")
            
            # Check if we can connect to the database
            result = db.session.execute(db.text('SELECT 1')).scalar()
            if result == 1:
                print("✓ Database connection verified")
            else:
                print("✗ Database connection failed")
                return False
            
            # Apply PostgreSQL-specific optimizations if using PostgreSQL
            db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            if 'postgresql' in db_url:
                print("PostgreSQL detected - applying production optimizations...")
                apply_postgresql_optimizations()
                
        except Exception as e:
            print(f"✗ Error initializing database: {e}")
            return False
    
    return True

def apply_postgresql_optimizations():
    """Apply PostgreSQL-specific optimizations and constraints"""
    try:
        # Read and execute PostgreSQL setup script
        script_path = os.path.join(os.path.dirname(__file__), 'migrations', 'postgresql_setup.sql')
        if os.path.exists(script_path):
            with open(script_path, 'r') as f:
                sql_script = f.read()
            
            # Split script into individual statements and execute
            statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
            for statement in statements:
                if statement and not statement.startswith('--'):
                    try:
                        db.session.execute(db.text(statement))
                    except Exception as e:
                        # Some statements might fail if already exist, that's okay
                        if 'already exists' not in str(e).lower():
                            print(f"Warning: PostgreSQL optimization statement failed: {e}")
            
            db.session.commit()
            print("✓ PostgreSQL optimizations applied successfully")
        else:
            print("⚠ PostgreSQL setup script not found, skipping optimizations")
            
    except Exception as e:
        print(f"⚠ Error applying PostgreSQL optimizations: {e}")
        db.session.rollback()

def create_admin_user():
    """Create a default admin user for testing"""
    print("Creating admin user...")
    
    with app.app_context():
        try:
            # Check if admin user already exists
            admin_email = "admin@uem.edu.in"
            existing_admin = User.query.filter_by(email=admin_email).first()
            
            if existing_admin:
                print(f"✓ Admin user already exists: {admin_email}")
                return True
            
            # Create admin user
            admin_user = User(
                email=admin_email,
                name="Admin User",
                year=2025,
                branch="Computer Science",
                is_admin=True
            )
            admin_user.set_password("admin123")  # Change this in production
            
            db.session.add(admin_user)
            db.session.commit()
            
            print(f"✓ Admin user created: {admin_email}")
            print("  Default password: admin123 (change this in production)")
            
        except Exception as e:
            print(f"✗ Error creating admin user: {e}")
            db.session.rollback()
            return False
    
    return True

def setup_flask_migrate():
    """Set up Flask-Migrate for database migrations"""
    print("Setting up Flask-Migrate...")
    
    try:
        # Check if migrations folder exists
        if not os.path.exists('migrations'):
            with app.app_context():
                init()
            print("✓ Flask-Migrate initialized")
        else:
            print("✓ Flask-Migrate already initialized")
            
        return True
        
    except Exception as e:
        print(f"✗ Error setting up Flask-Migrate: {e}")
        return False

def main():
    """Main initialization function"""
    print("=" * 50)
    print("UEM Placement Preparation Platform")
    print("Database Initialization Script")
    print("=" * 50)
    
    # Check environment
    env = os.environ.get('FLASK_ENV', 'development')
    db_url = app.config.get('SQLALCHEMY_DATABASE_URI')
    print(f"Environment: {env}")
    print(f"Database URL: {db_url}")
    print()
    
    # Initialize database
    if not init_database():
        print("Failed to initialize database. Exiting.")
        sys.exit(1)
    
    # Set up migrations
    if not setup_flask_migrate():
        print("Failed to set up Flask-Migrate. Continuing anyway.")
    
    # Create admin user (only in development)
    if env == 'development':
        if not create_admin_user():
            print("Failed to create admin user. Continuing anyway.")
    
    print()
    print("=" * 50)
    print("Database initialization completed successfully!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("1. Run 'python app.py' to start the development server")
    print("2. Visit http://localhost:5000 to access the application")
    if env == 'development':
        print("3. Login with admin@uem.edu.in / admin123 for admin access")

if __name__ == '__main__':
    main()