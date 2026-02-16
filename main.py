"""
KYC Verification System - Main Entry Point
"""
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from app.app import app

if __name__ == '__main__':
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=os.environ.get('FLASK_ENV') == 'development'
    )
