#!/usr/bin/env python3
"""
Demonstration script for the error handling and logging system.
Shows various error scenarios and how they are handled.
"""

import os
import sys
import tempfile
from flask import Flask, request, jsonify

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ExternalServiceError, InvalidEmailDomainError,
    DatabaseError, RateLimitError
)
from error_utils import (
    validate_uem_email, validate_required_fields, validate_field_length,
    retry_external_api_call, validate_json_request
)
from logging_config import setup_logging, get_logger
from error_handlers import register_error_handlers


def create_demo_app():
    """Create a demo Flask app with error handling"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'demo-secret-key'
    app.config['DEBUG'] = True
    app.config['LOG_LEVEL'] = 'DEBUG'
    app.config['LOG_DIR'] = tempfile.mkdtemp()
    
    # Setup logging and error handlers
    setup_logging(app)
    register_error_handlers(app)
    
    logger = get_logger(__name__)
    
    @app.route('/demo/validation-error')
    def demo_validation_error():
        """Demonstrate validation error"""
        raise ValidationError(
            message="Invalid email format",
            field="email",
            value="invalid-email"
        )
    
    @app.route('/demo/authentication-error')
    def demo_authentication_error():
        """Demonstrate authentication error"""
        raise AuthenticationError("Invalid credentials provided")
    
    @app.route('/demo/authorization-error')
    def demo_authorization_error():
        """Demonstrate authorization error"""
        raise AuthorizationError("Admin privileges required")
    
    @app.route('/demo/resource-not-found')
    def demo_resource_not_found():
        """Demonstrate resource not found error"""
        raise ResourceNotFoundError("User", 12345)
    
    @app.route('/demo/external-service-error')
    def demo_external_service_error():
        """Demonstrate external service error"""
        import requests
        original_error = requests.ConnectionError("Connection timeout")
        raise ExternalServiceError(
            service_name="Google Search",
            message="Service temporarily unavailable",
            original_error=original_error
        )
    
    @app.route('/demo/database-error')
    def demo_database_error():
        """Demonstrate database error"""
        raise DatabaseError(
            message="Failed to insert record",
            operation="INSERT",
            original_error=Exception("Unique constraint violation")
        )
    
    @app.route('/demo/rate-limit-error')
    def demo_rate_limit_error():
        """Demonstrate rate limit error"""
        raise RateLimitError(
            limit=100,
            window="hour",
            retry_after=3600
        )
    
    @app.route('/demo/email-validation', methods=['POST'])
    @validate_json_request(required_fields=['email'])
    def demo_email_validation(json_data):
        """Demonstrate email validation"""
        email = json_data['email']
        
        try:
            validate_uem_email(email)
            return jsonify({
                'success': True,
                'message': f'Valid UEM email: {email}'
            })
        except InvalidEmailDomainError as e:
            raise e
    
    @app.route('/demo/field-validation', methods=['POST'])
    @validate_json_request(required_fields=['name', 'password'])
    def demo_field_validation(json_data):
        """Demonstrate field validation"""
        name = json_data['name']
        password = json_data['password']
        
        validate_field_length(name, 'name', min_length=2, max_length=50)
        validate_field_length(password, 'password', min_length=8, max_length=128)
        
        return jsonify({
            'success': True,
            'message': 'All fields are valid'
        })
    
    @app.route('/demo/external-api-retry')
    @retry_external_api_call(max_retries=2, delay=0.1)
    def demo_external_api_retry():
        """Demonstrate external API retry mechanism"""
        import random
        import requests
        
        # Simulate random failures
        if random.random() < 0.7:  # 70% chance of failure
            raise requests.ConnectionError("Simulated connection error")
        
        return jsonify({
            'success': True,
            'message': 'API call succeeded after retries'
        })
    
    @app.route('/demo/success')
    def demo_success():
        """Demonstrate successful request logging"""
        logger.info("Successful request processed")
        return jsonify({
            'success': True,
            'message': 'Request processed successfully'
        })
    
    return app


def run_demo():
    """Run the error handling demonstration"""
    print("🚀 Starting Error Handling and Logging Demo")
    print("=" * 50)
    
    app = create_demo_app()
    
    print(f"📁 Log files will be created in: {app.config['LOG_DIR']}")
    print("\n📋 Available demo endpoints:")
    print("  GET  /demo/validation-error      - ValidationError")
    print("  GET  /demo/authentication-error  - AuthenticationError")
    print("  GET  /demo/authorization-error   - AuthorizationError")
    print("  GET  /demo/resource-not-found    - ResourceNotFoundError")
    print("  GET  /demo/external-service-error - ExternalServiceError")
    print("  GET  /demo/database-error        - DatabaseError")
    print("  GET  /demo/rate-limit-error      - RateLimitError")
    print("  POST /demo/email-validation      - Email validation (JSON: {\"email\": \"test@uem.edu.in\"})")
    print("  POST /demo/field-validation      - Field validation (JSON: {\"name\": \"John\", \"password\": \"password123\"})")
    print("  GET  /demo/external-api-retry    - External API retry mechanism")
    print("  GET  /demo/success               - Successful request")
    print("\n🌐 Server starting on http://localhost:5001")
    print("💡 Try the endpoints with curl or a REST client to see error handling in action!")
    print("\nExample commands:")
    print("  curl http://localhost:5001/demo/validation-error")
    print("  curl -X POST -H 'Content-Type: application/json' -d '{\"email\":\"test@gmail.com\"}' http://localhost:5001/demo/email-validation")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        app.run(host='0.0.0.0', port=5001, debug=True)
    except KeyboardInterrupt:
        print("\n\n👋 Demo server stopped")
        print(f"📁 Check log files in: {app.config['LOG_DIR']}")


if __name__ == '__main__':
    run_demo()