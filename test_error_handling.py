"""
Tests for error handling and logging functionality.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
from flask import Flask
from flask_login import login_user

from app import app
from models import db, User
from exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ExternalServiceError, InvalidEmailDomainError
)
from error_utils import (
    validate_uem_email, validate_required_fields, validate_field_length,
    require_authentication, require_admin
)


class TestCustomExceptions:
    """Test custom exception classes"""
    
    def test_base_api_exception(self):
        """Test BaseAPIException functionality"""
        from exceptions import BaseAPIException
        
        error = BaseAPIException(
            message="Test error",
            code="TEST_ERROR",
            status_code=400,
            details={'field': 'test'}
        )
        
        assert error.message == "Test error"
        assert error.code == "TEST_ERROR"
        assert error.status_code == 400
        assert error.details == {'field': 'test'}
        assert 'timestamp' in error.to_dict()
        
        error_dict = error.to_dict()
        assert error_dict['error'] is True
        assert error_dict['message'] == "Test error"
        assert error_dict['code'] == "TEST_ERROR"
    
    def test_authentication_error(self):
        """Test AuthenticationError"""
        error = AuthenticationError("Invalid credentials")
        
        assert error.message == "Invalid credentials"
        assert error.code == "AUTHENTICATION_ERROR"
        assert error.status_code == 401
    
    def test_validation_error(self):
        """Test ValidationError"""
        error = ValidationError(
            message="Invalid email",
            field="email",
            value="invalid@example.com"
        )
        
        assert error.message == "Invalid email"
        assert error.code == "VALIDATION_ERROR"
        assert error.status_code == 400
        assert error.details['field'] == "email"
        assert error.details['value'] == "invalid@example.com"
    
    def test_resource_not_found_error(self):
        """Test ResourceNotFoundError"""
        error = ResourceNotFoundError("User", 123)
        
        assert "User not found with ID: 123" in error.message
        assert error.code == "RESOURCE_NOT_FOUND"
        assert error.status_code == 404
        assert error.details['resource_type'] == "User"
        assert error.details['resource_id'] == "123"
    
    def test_external_service_error(self):
        """Test ExternalServiceError"""
        original_error = Exception("Connection timeout")
        error = ExternalServiceError(
            service_name="Perplexity AI",
            message="Service unavailable",
            original_error=original_error
        )
        
        assert error.message == "Service unavailable"
        assert error.code == "EXTERNAL_SERVICE_ERROR"
        assert error.status_code == 503
        assert error.details['service'] == "Perplexity AI"
        assert error.details['original_error'] == "Connection timeout"
    
    def test_invalid_email_domain_error(self):
        """Test InvalidEmailDomainError"""
        error = InvalidEmailDomainError("student@gmail.com")
        
        assert "Only @uem.edu.in email addresses are allowed" in error.message
        assert error.code == "INVALID_EMAIL_DOMAIN"
        assert error.details['field'] == "email"
        assert error.details['value'] == "student@gmail.com"


class TestErrorUtils:
    """Test error utility functions"""
    
    def test_validate_uem_email_valid(self):
        """Test UEM email validation with valid email"""
        assert validate_uem_email("student@uem.edu.in") is True
    
    def test_validate_uem_email_invalid(self):
        """Test UEM email validation with invalid email"""
        with pytest.raises(InvalidEmailDomainError):
            validate_uem_email("student@gmail.com")
        
        with pytest.raises(InvalidEmailDomainError):
            validate_uem_email("student@uem.edu.com")
        
        with pytest.raises(InvalidEmailDomainError):
            validate_uem_email("")
        
        with pytest.raises(InvalidEmailDomainError):
            validate_uem_email(None)
    
    def test_validate_required_fields_valid(self):
        """Test required fields validation with valid data"""
        data = {'name': 'John', 'email': 'john@uem.edu.in', 'password': 'secret'}
        required_fields = ['name', 'email', 'password']
        
        # Should not raise any exception
        validate_required_fields(data, required_fields)
    
    def test_validate_required_fields_missing(self):
        """Test required fields validation with missing fields"""
        data = {'name': 'John', 'email': 'john@uem.edu.in'}
        required_fields = ['name', 'email', 'password']
        
        with pytest.raises(ValidationError) as exc_info:
            validate_required_fields(data, required_fields)
        
        assert "Missing required fields: password" in str(exc_info.value)
    
    def test_validate_required_fields_empty(self):
        """Test required fields validation with empty values"""
        data = {'name': 'John', 'email': '', 'password': None}
        required_fields = ['name', 'email', 'password']
        
        with pytest.raises(ValidationError) as exc_info:
            validate_required_fields(data, required_fields)
        
        error_message = str(exc_info.value)
        assert "email" in error_message
        assert "password" in error_message
    
    def test_validate_field_length_valid(self):
        """Test field length validation with valid lengths"""
        # Should not raise any exception
        validate_field_length("password123", "password", min_length=8, max_length=20)
        validate_field_length("test", "name", min_length=2)
        validate_field_length("short", "description", max_length=10)
    
    def test_validate_field_length_too_short(self):
        """Test field length validation with too short value"""
        with pytest.raises(ValidationError) as exc_info:
            validate_field_length("123", "password", min_length=8)
        
        assert "must be at least 8 characters long" in str(exc_info.value)
    
    def test_validate_field_length_too_long(self):
        """Test field length validation with too long value"""
        with pytest.raises(ValidationError) as exc_info:
            validate_field_length("this is a very long string", "name", max_length=10)
        
        assert "must be no more than 10 characters long" in str(exc_info.value)


class TestErrorHandlers:
    """Test Flask error handlers"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.test_client() as client:
            with app.app_context():
                db.create_all()
                yield client
                db.drop_all()
    
    def test_404_error_api_endpoint(self, client):
        """Test 404 error for API endpoints"""
        response = client.get('/api/nonexistent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == "RESOURCE_NOT_FOUND"
        assert "Endpoint not found" in data['message']
    
    def test_404_error_web_page(self, client):
        """Test 404 error for web pages"""
        response = client.get('/nonexistent-page')
        
        assert response.status_code == 404
        assert b'Page Not Found' in response.data
    
    def test_405_method_not_allowed(self, client):
        """Test 405 Method Not Allowed error"""
        # Assuming /api/auth/login only accepts POST
        response = client.get('/api/auth/login')
        
        assert response.status_code == 405
        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == "VALIDATION_ERROR"
        assert "Method GET not allowed" in data['message']
    
    def test_validation_error_handling(self, client):
        """Test validation error handling"""
        # Send invalid JSON to registration endpoint
        response = client.post('/api/auth/register',
                             data='invalid json',
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == "VALIDATION_ERROR"


class TestLogging:
    """Test logging functionality"""
    
    def test_logging_configuration(self):
        """Test that logging is properly configured"""
        import logging
        
        # Check that loggers exist
        app_logger = logging.getLogger('app')
        access_logger = logging.getLogger('access')
        security_logger = logging.getLogger('security')
        
        assert app_logger is not None
        assert access_logger is not None
        assert security_logger is not None
    
    @patch('logging_config.log_security_event')
    def test_security_event_logging(self, mock_log_security):
        """Test security event logging"""
        from logging_config import log_security_event
        
        log_security_event(
            event_type="FAILED_LOGIN",
            details={'email': 'test@uem.edu.in'},
            user_id=123,
            ip_address='192.168.1.1'
        )
        
        mock_log_security.assert_called_once_with(
            event_type="FAILED_LOGIN",
            details={'email': 'test@uem.edu.in'},
            user_id=123,
            ip_address='192.168.1.1'
        )
    
    def test_json_formatter(self):
        """Test JSON log formatter"""
        from logging_config import JSONFormatter
        import logging
        
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert data['level'] == 'INFO'
        assert data['message'] == 'Test message'
        assert data['logger'] == 'test'
        assert 'timestamp' in data


if __name__ == '__main__':
    pytest.main([__file__])