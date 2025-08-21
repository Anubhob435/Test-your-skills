"""
Simple test for dashboard endpoints
"""

import requests
import json

def test_dashboard_endpoints():
    """Simple test to verify dashboard endpoints are accessible"""
    base_url = "http://localhost:5000"
    
    # Test endpoints without authentication (should return 401)
    endpoints = [
        "/api/dashboard",
        "/api/companies", 
        "/api/test-history"
    ]
    
    print("Testing dashboard endpoints...")
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}")
            print(f"GET {endpoint}: Status {response.status_code}")
            
            if response.status_code == 401:
                print(f"  ✓ Correctly requires authentication")
            elif response.status_code == 404:
                print(f"  ✗ Endpoint not found - check if blueprint is registered")
            else:
                print(f"  ? Unexpected status code: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"  ✗ Cannot connect to server at {base_url}")
            print("  Make sure the Flask app is running with: python app.py")
            break
    
    print("\nDashboard endpoints test completed.")

if __name__ == "__main__":
    test_dashboard_endpoints()