#!/usr/bin/env python3
"""
Database validation script for UEM Placement Preparation Platform
Validates all models, relationships, indexes, and constraints
"""

import os
import sys
from flask import Flask
from sqlalchemy import inspect, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import app and models
from app import app
from models import db, User, Test, Question, TestAttempt, ProgressMetrics

def validate_tables():
    """Validate that all required tables exist"""
    print("Validating database tables...")
    
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        required_tables = ['users', 'tests', 'questions', 'test_attempts', 'progress_metrics']
        
        for table in required_tables:
            if table in existing_tables:
                print(f"✓ Table '{table}' exists")
            else:
                print(f"✗ Table '{table}' missing")
                return False
    
    return True

def validate_indexes():
    """Validate that all required indexes exist"""
    print("\nValidating database indexes...")
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Expected indexes for each table
        expected_indexes = {
            'users': ['ix_users_email'],
            'tests': ['ix_tests_company', 'ix_tests_year', 'ix_tests_created_at'],
            'questions': ['ix_questions_test_id', 'ix_questions_section', 'ix_questions_difficulty', 'ix_questions_topic'],
            'test_attempts': ['ix_test_attempts_user_id', 'ix_test_attempts_test_id', 'ix_test_attempts_score', 'ix_test_attempts_started_at', 'ix_test_attempts_completed_at'],
            'progress_metrics': ['ix_progress_metrics_user_id']
        }
        
        all_indexes_valid = True
        
        for table, indexes in expected_indexes.items():
            table_indexes = [idx['name'] for idx in inspector.get_indexes(table)]
            
            for index in indexes:
                if index in table_indexes:
                    print(f"✓ Index '{index}' exists on table '{table}'")
                else:
                    print(f"✗ Index '{index}' missing on table '{table}'")
                    all_indexes_valid = False
        
        return all_indexes_valid

def validate_foreign_keys():
    """Validate that all foreign key relationships exist"""
    print("\nValidating foreign key relationships...")
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Expected foreign keys
        expected_fks = {
            'questions': [('test_id', 'tests', 'id')],
            'test_attempts': [('user_id', 'users', 'id'), ('test_id', 'tests', 'id')],
            'progress_metrics': [('user_id', 'users', 'id')]
        }
        
        all_fks_valid = True
        
        for table, fks in expected_fks.items():
            table_fks = inspector.get_foreign_keys(table)
            
            for fk_column, ref_table, ref_column in fks:
                fk_exists = any(
                    fk['constrained_columns'] == [fk_column] and 
                    fk['referred_table'] == ref_table and 
                    fk['referred_columns'] == [ref_column]
                    for fk in table_fks
                )
                
                if fk_exists:
                    print(f"✓ Foreign key '{fk_column}' -> '{ref_table}.{ref_column}' exists on table '{table}'")
                else:
                    print(f"✗ Foreign key '{fk_column}' -> '{ref_table}.{ref_column}' missing on table '{table}'")
                    all_fks_valid = False
        
        return all_fks_valid

def validate_model_methods():
    """Validate that model methods work correctly"""
    print("\nValidating model methods...")
    
    with app.app_context():
        try:
            # Test User model methods
            test_user = User(
                email="test@uem.edu.in",
                name="Test User",
                year=2025,
                branch="Computer Science"
            )
            test_user.set_password("testpass123")
            
            # Validate password methods
            if test_user.check_password("testpass123"):
                print("✓ User password hashing/checking works")
            else:
                print("✗ User password hashing/checking failed")
                return False
            
            # Validate email validation
            if test_user.is_uem_email():
                print("✓ UEM email validation works")
            else:
                print("✗ UEM email validation failed")
                return False
            
            # Test to_dict method
            user_dict = test_user.to_dict()
            if isinstance(user_dict, dict) and 'email' in user_dict:
                print("✓ User to_dict method works")
            else:
                print("✗ User to_dict method failed")
                return False
            
            # Test Test model methods
            test_test = Test(company="Test Company", year=2025)
            test_data = {"sections": ["Aptitude", "Reasoning"]}
            test_test.set_pattern_data(test_data)
            
            if test_test.get_pattern_data() == test_data:
                print("✓ Test pattern data methods work")
            else:
                print("✗ Test pattern data methods failed")
                return False
            
            # Test Question model
            test_question = Question(
                test_id=1,
                section="Aptitude",
                question_text="Test question?",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation="Test explanation"
            )
            
            question_dict = test_question.to_dict()
            if isinstance(question_dict, dict) and 'question_text' in question_dict:
                print("✓ Question to_dict method works")
            else:
                print("✗ Question to_dict method failed")
                return False
            
            # Test TestAttempt model
            test_attempt = TestAttempt(
                user_id=1,
                test_id=1,
                score=8,
                total_questions=10
            )
            
            if test_attempt.calculate_percentage() == 80.0:
                print("✓ TestAttempt percentage calculation works")
            else:
                print("✗ TestAttempt percentage calculation failed")
                return False
            
            # Test ProgressMetrics model
            test_progress = ProgressMetrics(
                user_id=1,
                subject_area="Aptitude",
                accuracy_rate=75.0,
                total_attempts=5
            )
            
            progress_dict = test_progress.to_dict()
            if isinstance(progress_dict, dict) and 'accuracy_rate' in progress_dict:
                print("✓ ProgressMetrics to_dict method works")
            else:
                print("✗ ProgressMetrics to_dict method failed")
                return False
            
            return True
            
        except Exception as e:
            print(f"✗ Model method validation failed: {e}")
            return False

def validate_database_connection():
    """Validate database connection and basic operations"""
    print("\nValidating database connection...")
    
    with app.app_context():
        try:
            # Test basic connection
            result = db.session.execute(text('SELECT 1')).scalar()
            if result == 1:
                print("✓ Database connection successful")
            else:
                print("✗ Database connection failed")
                return False
            
            # Test transaction capability with a new session
            with db.engine.connect() as conn:
                trans = conn.begin()
                trans.rollback()
            print("✓ Database transaction capability verified")
            
            return True
            
        except Exception as e:
            print(f"✗ Database connection validation failed: {e}")
            return False

def run_sample_queries():
    """Run sample queries to test database performance"""
    print("\nRunning sample queries...")
    
    with app.app_context():
        try:
            # Test if we can query each table
            user_count = User.query.count()
            test_count = Test.query.count()
            question_count = Question.query.count()
            attempt_count = TestAttempt.query.count()
            progress_count = ProgressMetrics.query.count()
            
            print(f"✓ Users: {user_count}")
            print(f"✓ Tests: {test_count}")
            print(f"✓ Questions: {question_count}")
            print(f"✓ Test Attempts: {attempt_count}")
            print(f"✓ Progress Metrics: {progress_count}")
            
            return True
            
        except Exception as e:
            print(f"✗ Sample queries failed: {e}")
            return False

def main():
    """Main validation function"""
    print("=" * 60)
    print("UEM Placement Preparation Platform")
    print("Database Validation Script")
    print("=" * 60)
    
    # Get database info
    with app.app_context():
        db_url = app.config.get('SQLALCHEMY_DATABASE_URI')
        print(f"Database URL: {db_url}")
        print()
    
    # Run all validations
    validations = [
        ("Database Connection", validate_database_connection),
        ("Tables", validate_tables),
        ("Indexes", validate_indexes),
        ("Foreign Keys", validate_foreign_keys),
        ("Model Methods", validate_model_methods),
        ("Sample Queries", run_sample_queries)
    ]
    
    all_passed = True
    
    for validation_name, validation_func in validations:
        print(f"\n{'-' * 40}")
        print(f"Running {validation_name} Validation")
        print(f"{'-' * 40}")
        
        if not validation_func():
            all_passed = False
            print(f"✗ {validation_name} validation FAILED")
        else:
            print(f"✓ {validation_name} validation PASSED")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("Database is properly configured and ready for use.")
    else:
        print("❌ SOME VALIDATIONS FAILED!")
        print("Please check the errors above and fix the issues.")
        sys.exit(1)
    print("=" * 60)

if __name__ == '__main__':
    main()