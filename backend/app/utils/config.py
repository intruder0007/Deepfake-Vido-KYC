"""
Configuration settings for KYC Verification System
"""
import os
from pathlib import Path

# Get base directory
BASE_DIR = Path(__file__).parent.parent.parent

class Config:
    """Base configuration"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    # File upload settings
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    TEMP_FOLDER = os.path.join(BASE_DIR, 'temp')
    ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}
    
    # Video processing
    TARGET_FPS = 30
    TARGET_RESOLUTION = (640, 480)
    
    # Detection thresholds
    LIVENESS_THRESHOLD = 0.5
    DEEPFAKE_THRESHOLD = 0.6
    CONFIDENCE_THRESHOLD = 0.7
    
    # Alert settings
    ALERT_EMAIL_ENABLED = os.environ.get('ALERT_EMAIL_ENABLED', 'false').lower() == 'true'
    ALERT_SLACK_ENABLED = os.environ.get('ALERT_SLACK_ENABLED', 'false').lower() == 'true'
    
    # Email configuration (if enabled)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = os.environ.get('MAIL_PORT', 587)
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@kyc-verification.com')
    
    # Slack webhook (if enabled)
    SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')
    
    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///kyc_verification.db')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.path.join(BASE_DIR, 'logs', 'kyc_verification.log')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'


# Create directories
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.TEMP_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(Config.LOG_FILE), exist_ok=True)
