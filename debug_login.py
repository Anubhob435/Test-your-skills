#!/usr/bin/env python3
"""
Debug login response
"""

from test_setup import create_test_app, create_test_user

def debug_login():
    """Debug login response"""
    app = create_test_app()
    
    with app.app_context():
        # Create test user
        user = create_test_user()
        print(f'Created test user: {user.email}')
        
        with app.test_client() as client:
            # Test login
            login_response = client.post('/api/auth/login', 
                json={'email': user.email, 'password': 'testpass123'})
            print(f'Login status: {login_response.status_code}')
            print(f'Login response: {login_response.json}')

if __name__ == '__main__':
    debug_login()