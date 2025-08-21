#!/usr/bin/env python3
"""
Simple test for test generation functionality
"""

from unittest.mock import patch, MagicMock
from test_setup import create_test_app, create_test_user, create_test_data

def test_generation_with_mock():
    """Test test generation with mocked services"""
    app = create_test_app()
    
    with app.app_context():
        # Create test user
        user = create_test_user()
        print(f'✓ Created test user: {user.email}')
        
        with app.test_client() as client:
            # Login
            login_response = client.post('/api/auth/login', 
                json={'email': user.email, 'password': 'testpass123'})
            
            token = login_response.json['token']
            headers = {'Authorization': f'Bearer {token}'}
            
            # Mock the question generation service
            mock_result = {
                'test_id': 1,
                'company': 'TCS NQT',
                'year': 2025,
                'num_questions': 10,
                'created_at': '2025-01-17T10:30:00Z',
                'from_cache': False,
                'generation_time': 30.5,
                'success': True,
                'sections': ['Quantitative Aptitude', 'Logical Reasoning']
            }
            
            with patch('test_routes.question_service.generate_test_sync', return_value=mock_result):
                # Test generation
                response = client.post('/api/tests/generate/TCS%20NQT',
                    json={'num_questions': 10},
                    headers=headers)
                
                print(f'✓ Test generation response: {response.status_code}')
                
                if response.status_code == 201:
                    data = response.json
                    print(f'✓ Generated test for: {data["company"]}')
                    print(f'✓ Test ID: {data["test_id"]}')
                    print(f'✓ Number of questions: {data["num_questions"]}')
                    print(f'✓ Sections: {data["sections"]}')
                    return True
                else:
                    print(f'✗ Generation failed: {response.json}')
                    return False

def test_with_real_data():
    """Test with real test data"""
    app = create_test_app()
    
    with app.app_context():
        # Create test user and test data
        user = create_test_user()
        test, questions = create_test_data()
        
        print(f'✓ Created test data: {test.company} with {len(questions)} questions')
        
        with app.test_client() as client:
            # Login
            login_response = client.post('/api/auth/login', 
                json={'email': user.email, 'password': 'testpass123'})
            
            token = login_response.json['token']
            headers = {'Authorization': f'Bearer {token}'}
            
            # Test retrieval
            response = client.get(f'/api/tests/{test.id}', headers=headers)
            print(f'✓ Test retrieval response: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json
                print(f'✓ Retrieved test: {data["company"]}')
                print(f'✓ Total questions: {data["total_questions"]}')
                print(f'✓ Sections: {[s["section_name"] for s in data["sections"]]}')
                
                # Test submission
                answers = {}
                for section in data['sections']:
                    for question in section['questions'][:2]:  # Answer first 2 questions
                        answers[str(question['id'])] = 'B'  # Always answer B
                
                submission_data = {
                    'answers': answers,
                    'time_taken': 1800
                }
                
                response = client.post(f'/api/tests/{test.id}/submit',
                    json=submission_data,
                    headers=headers)
                
                print(f'✓ Test submission response: {response.status_code}')
                
                if response.status_code == 200:
                    result_data = response.json
                    print(f'✓ Score: {result_data["score"]}/{result_data["total_questions"]}')
                    print(f'✓ Percentage: {result_data["percentage"]}%')
                    print(f'✓ Attempt ID: {result_data["attempt_id"]}')
                    
                    # Test results retrieval
                    response = client.get(f'/api/tests/{test.id}/results/{result_data["attempt_id"]}',
                        headers=headers)
                    
                    print(f'✓ Results retrieval response: {response.status_code}')
                    
                    if response.status_code == 200:
                        print('✓ All test operations completed successfully!')
                        return True
                    else:
                        print(f'✗ Results retrieval failed: {response.json}')
                        return False
                else:
                    print(f'✗ Submission failed: {response.json}')
                    return False
            else:
                print(f'✗ Retrieval failed: {response.json}')
                return False

if __name__ == '__main__':
    print("=" * 60)
    print("Testing Test Generation and Management")
    print("=" * 60)
    
    try:
        print("\n1. Testing with mocked generation service...")
        success1 = test_generation_with_mock()
        
        print("\n2. Testing with real test data...")
        success2 = test_with_real_data()
        
        if success1 and success2:
            print("\n🎉 All test management functionality is working!")
        else:
            print("\n❌ Some tests failed.")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)