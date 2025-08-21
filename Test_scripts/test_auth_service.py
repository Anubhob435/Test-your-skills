"""
Test file for AuthService functionality
"""

import unittest
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth_service import AuthService

class TestAuthService(unittest.TestCase):
    """Test cases for AuthService"""
    
    def test_validate_uem_email_valid(self):
        """Test valid UEM email validation"""
        valid_emails = [
            'student@uem.edu.in',
            'john.doe@uem.edu.in',
            'test123@uem.edu.in',
            'user_name@uem.edu.in',
            'STUDENT@UEM.EDU.IN'  # Case insensitive
        ]
        
        for email in valid_emails:
            with self.subTest(email=email):
                self.assertTrue(AuthService.validate_uem_email(email))
    
    def test_validate_uem_email_invalid(self):
        """Test invalid email validation"""
        invalid_emails = [
            'student@gmail.com',
            'user@uem.edu.com',
            'test@uem.in',
            'invalid-email',
            '@uem.edu.in',
            'student@',
            '',
            None,
            123,
            'student@uem.edu.in.fake.com'
        ]
        
        for email in invalid_emails:
            with self.subTest(email=email):
                self.assertFalse(AuthService.validate_uem_email(email))
    
    def test_hash_password(self):
        """Test password hashing"""
        password = "testpassword123"
        hashed = AuthService.hash_password(password)
        
        # Check that hash is generated
        self.assertIsNotNone(hashed)
        self.assertIsInstance(hashed, str)
        self.assertNotEqual(password, hashed)
        self.assertTrue(len(hashed) > 0)
    
    def test_hash_password_empty(self):
        """Test hashing empty password raises error"""
        with self.assertRaises(ValueError):
            AuthService.hash_password("")
        
        with self.assertRaises(ValueError):
            AuthService.hash_password(None)
    
    def test_verify_password(self):
        """Test password verification"""
        password = "testpassword123"
        hashed = AuthService.hash_password(password)
        
        # Correct password should verify
        self.assertTrue(AuthService.verify_password(password, hashed))
        
        # Wrong password should not verify
        self.assertFalse(AuthService.verify_password("wrongpassword", hashed))
        
        # Empty inputs should return False
        self.assertFalse(AuthService.verify_password("", hashed))
        self.assertFalse(AuthService.verify_password(password, ""))
        self.assertFalse(AuthService.verify_password(None, hashed))
        self.assertFalse(AuthService.verify_password(password, None))
    
    def test_validate_password_strength(self):
        """Test password strength validation"""
        # Valid passwords
        valid_passwords = [
            "password123",
            "test123",
            "mypass1",
            "StrongPass123"
        ]
        
        for password in valid_passwords:
            with self.subTest(password=password):
                is_valid, message = AuthService.validate_password_strength(password)
                self.assertTrue(is_valid, f"Password '{password}' should be valid: {message}")
        
        # Invalid passwords
        invalid_cases = [
            ("", "Password is required."),
            (None, "Password is required."),
            ("short", "Password must be at least 6 characters long."),
            ("12345", "Password must be at least 6 characters long."),
            ("password", "Password must contain at least one number."),
            ("123456", "Password must contain at least one letter."),
            ("a" * 129, "Password must be less than 128 characters.")
        ]
        
        for password, expected_message in invalid_cases:
            with self.subTest(password=password):
                is_valid, message = AuthService.validate_password_strength(password)
                self.assertFalse(is_valid)
                self.assertEqual(message, expected_message)

if __name__ == '__main__':
    unittest.main()