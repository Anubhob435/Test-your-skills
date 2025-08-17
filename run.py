#!/usr/bin/env python3
"""
Development server runner for UEM Placement Preparation Platform
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set development environment
os.environ['FLASK_ENV'] = 'development'

if __name__ == '__main__':
    from app import app
    
    # Run the application
    app.run(
        debug=True,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000))
    )