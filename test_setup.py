#!/usr/bin/env python3
"""
Test script to verify the setup is working correctly
"""

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