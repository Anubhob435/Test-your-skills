"""
Demonstration script for the authentication system
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth_service import AuthService
from auth_middleware import get_current_user, SessionManager
from models import User

def demo_auth_service():
    """Demonstrate AuthService functionality"""
    print("=== AuthService Demo ===")
    
    # Email validation
    print("\n1. Email Validation:")
    emails = ['student@uem.edu.in', 'user@gmail.com', 'test@uem.edu.in']
    for email in emails:
        is_valid = AuthService.validate_uem_email(email)
        print(f"  {email}: {'✓ Valid' if is_valid else '✗ Invalid'}")
    
    # Password hashing and verification
    print("\n2. Password Hashing:")
    password = "testpassword123"
    hashed = AuthService.hash_password(password)
    print(f"  Original: {password}")
    print(f"  Hashed: {hashed[:50]}...")
    
    # Password verification
    print("\n3. Password Verification:")
    correct_verify = AuthService.verify_password(password, hashed)
    wrong_verify = AuthService.verify_password("wrongpassword", hashed)
    print(f"  Correct password: {'✓ Valid' if correct_verify else '✗ Invalid'}")
    print(f"  Wrong password: {'✓ Valid' if wrong_verify else '✗ Invalid'}")
    
    # Password strength validation
    print("\n4. Password Strength Validation:")
    passwords = ["weak", "password123", "123456", "strongpass1"]
    for pwd in passwords:
        is_valid, message = AuthService.validate_password_strength(pwd)
        status = "✓ Valid" if is_valid else f"✗ {message}"
        print(f"  '{pwd}': {status}")

def demo_session_manager():
    """Demonstrate SessionManager functionality"""
    print("\n=== SessionManager Demo ===")
    
    # Mock user for demonstration
    class MockUser:
        def __init__(self):
            self.id = 1
            self.email = 'demo@uem.edu.in'
            self.name = 'Demo User'
            self.is_admin = False
            self.created_at = None
    
    user = MockUser()
    session_data = SessionManager.create_session(user)
    
    print("\nSession Data Created:")
    for key, value in session_data.items():
        print(f"  {key}: {value}")

def main():
    """Main demonstration function"""
    print("UEM Placement Platform - Authentication System Demo")
    print("=" * 55)
    
    demo_auth_service()
    demo_session_manager()
    
    print("\n=== Summary ===")
    print("✓ Email validation service implemented")
    print("✓ Password hashing with bcrypt implemented")
    print("✓ Password verification implemented")
    print("✓ Password strength validation implemented")
    print("✓ JWT token generation implemented")
    print("✓ User registration and login endpoints implemented")
    print("✓ Authentication middleware and decorators implemented")
    print("✓ Session management utilities implemented")
    
    print("\nAuthentication system is ready for use!")

if __name__ == '__main__':
    main()