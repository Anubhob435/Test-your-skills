#!/usr/bin/env python3
"""
Simple test to verify test endpoints work
"""

from test_setup import create_test_app, create_test_user

def test_basic_functionality():
    """Test basic endpoint functionality"""
    app = create_test_app()
    
    with app.app_context():
        # Create test user
        user = create_test_user()
        print(f'✓ Created test user: {user.email}')
        
        with app.test_client() as client:
            # Test companies endpoint without auth (should fail)
            response = client.get('/api/tests/companies')
            print(f'✓ Companies endpoint without auth: {response.status_code} (expected 401)')
            
            # Test login
            login_response = client.post('/api/auth/login', 
                json={'email': user.email, 'password': 'testpass123'})
            print(f'✓ Login response: {login_response.status_code}')
            
            if login_response.status_code == 200:
                token = login_response.json['token']
                headers = {'Authorization': f'Bearer {token}'}
                
                # Test companies endpoint with auth
                response = client.get('/api/tests/companies', headers=headers)
                print(f'✓ Companies endpoint with auth: {response.status_code}')
                
                if response.status_code == 200:
                    data = response.json
                    print(f'✓ Total companies available: {data.get("total_companies", 0)}')
                    print(f'✓ Supported companies: {len(data.get("supported_companies", []))}')
                else:
                    print(f'✗ Error: {response.json}')
                    
                # Test non-existent test retrieval
                response = client.get('/api/tests/99999', headers=headers)
                print(f'✓ Non-existent test retrieval: {response.status_code} (expected 404)')
                
                print('\n✓ All basic tests passed!')
                return True
            else:
                print(f'✗ Login failed: {login_response.json}')
                return False

if __name__ == '__main__':
    print("=" * 50)
    print("Testing Test Management Endpoints")
    print("=" * 50)
    
    try:
        success = test_basic_functionality()
        if success:
            print("\n🎉 Test endpoints are working correctly!")
        else:
            print("\n❌ Some tests failed.")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 50)