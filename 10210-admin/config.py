"""
WhatsApp Agent Configuration
Modify these settings according to your setup
"""

import os
from typing import Optional

class Config:
    """Application configuration"""
    
    # ==================== WAHA SERVER SETTINGS ====================
    
    # WAHA server base URL
    WAHA_BASE_URL: str = os.getenv("WAHA_BASE_URL", "http://localhost:4500")
    
    # WAHA API key (if authentication is enabled)
    WAHA_API_KEY: Optional[str] = os.getenv("WAHA_API_KEY", None)
    
    # Request timeout in seconds
    WAHA_TIMEOUT: int = int(os.getenv("WAHA_TIMEOUT", "30"))
    
    # ==================== FASTAPI SERVER SETTINGS ====================
    
    # Server host (0.0.0.0 for all interfaces, 127.0.0.1 for localhost only)
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    # Server port
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Debug mode (auto-reload on code changes)
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # Log level (DEBUG, INFO, WARNING, ERROR)
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # ==================== APPLICATION SETTINGS ====================
    
    # Application title
    APP_TITLE: str = "WhatsApp Agent"
    
    # Application description
    APP_DESCRIPTION: str = "Professional WhatsApp Management Dashboard"
    
    # Application version
    APP_VERSION: str = "1.0.0"
    
    # Maximum file upload size (in bytes) - 50MB default
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "52428800"))
    
    # Session status polling interval (in milliseconds)
    POLLING_INTERVAL: int = int(os.getenv("POLLING_INTERVAL", "2000"))
    
    # Auto-refresh interval for dashboard (in milliseconds)
    AUTO_REFRESH_INTERVAL: int = int(os.getenv("AUTO_REFRESH_INTERVAL", "30000"))
    
    # ==================== SECURITY SETTINGS ====================
    
    # Enable CORS (Cross-Origin Resource Sharing)
    ENABLE_CORS: bool = os.getenv("ENABLE_CORS", "True").lower() == "true"
    
    # Allowed origins for CORS (use ["*"] for all origins in development)
    CORS_ORIGINS: list = ["*"] if DEBUG else ["https://app.cuwapp.com"]
    
    # Enable API key authentication (for your own API endpoints)
    ENABLE_AUTH: bool = os.getenv("ENABLE_AUTH", "False").lower() == "true"
    
    # API key for your endpoints (generate a secure key for production)
    API_KEY: Optional[str] = os.getenv("API_KEY", None)
    
    # ==================== FEATURE FLAGS ====================
    
    # Enable file upload functionality
    ENABLE_FILE_UPLOAD: bool = os.getenv("ENABLE_FILE_UPLOAD", "True").lower() == "true"
    
    # Enable screenshot functionality
    ENABLE_SCREENSHOTS: bool = os.getenv("ENABLE_SCREENSHOTS", "True").lower() == "true"
    
    # Enable group management
    ENABLE_GROUP_MANAGEMENT: bool = os.getenv("ENABLE_GROUP_MANAGEMENT", "True").lower() == "true"
    
    # Enable contact management
    ENABLE_CONTACT_MANAGEMENT: bool = os.getenv("ENABLE_CONTACT_MANAGEMENT", "True").lower() == "true"
    
    # Enable message broadcasting
    ENABLE_BROADCASTING: bool = os.getenv("ENABLE_BROADCASTING", "True").lower() == "true"
    
    # ==================== DIRECTORY SETTINGS ====================
    
    # Static files directory
    STATIC_DIR: str = "static"
    
    # Upload directory
    UPLOAD_DIR: str = "static/uploads"
    
    # Logs directory
    LOG_DIR: str = "logs"
    
    # ==================== UI SETTINGS ====================
    
    # Default theme (light/dark)
    DEFAULT_THEME: str = os.getenv("DEFAULT_THEME", "light")
    
    # Enable animations
    ENABLE_ANIMATIONS: bool = os.getenv("ENABLE_ANIMATIONS", "True").lower() == "true"
    
    # Default language
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "en")
    
    # ==================== WEBHOOK SETTINGS ====================
    
    # Default webhook URL for new sessions
    DEFAULT_WEBHOOK_URL: Optional[str] = os.getenv("DEFAULT_WEBHOOK_URL", None)
    
    # Webhook events to subscribe to
    DEFAULT_WEBHOOK_EVENTS: list = [
        "message",
        "message.reaction",
        "session.status",
        "group.v2.join",
        "group.v2.leave"
    ]
    
    # ==================== RATE LIMITING ====================
    
    # Enable rate limiting
    ENABLE_RATE_LIMITING: bool = os.getenv("ENABLE_RATE_LIMITING", "True").lower() == "true"
    
    # Requests per minute per IP
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # ==================== BACKUP SETTINGS ====================
    
    # Enable automatic session backups
    ENABLE_AUTO_BACKUP: bool = os.getenv("ENABLE_AUTO_BACKUP", "False").lower() == "true"
    
    # Backup directory
    BACKUP_DIR: str = "backups"
    
    # Backup interval in hours
    BACKUP_INTERVAL_HOURS: int = int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))
    
    # ==================== NOTIFICATION SETTINGS ====================
    
    # Enable desktop notifications
    ENABLE_DESKTOP_NOTIFICATIONS: bool = os.getenv("ENABLE_DESKTOP_NOTIFICATIONS", "True").lower() == "true"
    
    # Enable sound notifications
    ENABLE_SOUND_NOTIFICATIONS: bool = os.getenv("ENABLE_SOUND_NOTIFICATIONS", "False").lower() == "true"
    
    # ==================== HELPER METHODS ====================
    
    @classmethod
    def get_waha_config(cls) -> dict:
        """Get WAHA client configuration"""
        return {
            "base_url": cls.WAHA_BASE_URL,
            "api_key": cls.WAHA_API_KEY,
            "timeout": cls.WAHA_TIMEOUT
        }
    
    @classmethod
    def get_server_config(cls) -> dict:
        """Get FastAPI server configuration"""
        return {
            "host": cls.HOST,
            "port": cls.PORT,
            "reload": cls.DEBUG,
            "log_level": cls.LOG_LEVEL.lower()
        }
    
    @classmethod
    def get_cors_config(cls) -> dict:
        """Get CORS configuration"""
        return {
            "allow_origins": cls.CORS_ORIGINS,
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"]
        }
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production mode"""
        return not cls.DEBUG
    
    @classmethod
    def get_upload_config(cls) -> dict:
        """Get file upload configuration"""
        return {
            "enabled": cls.ENABLE_FILE_UPLOAD,
            "max_size": cls.MAX_UPLOAD_SIZE,
            "upload_dir": cls.UPLOAD_DIR
        }

# Environment-specific configurations
class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    ENABLE_CORS = True
    CORS_ORIGINS = ["*"]

class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    LOG_LEVEL = "INFO"
    ENABLE_CORS = True
    CORS_ORIGINS = ["https://yourdomain.com"]  # Update with your domain
    ENABLE_AUTH = True
    ENABLE_RATE_LIMITING = True

class TestingConfig(Config):
    """Testing environment configuration"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    WAHA_BASE_URL = "http://localhost:4500"  # Test WAHA instance

# Get configuration based on environment
def get_config() -> Config:
    """Get configuration based on environment variable"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionConfig()
    elif env == "testing":
        return TestingConfig()
    else:
        return DevelopmentConfig()

# Global configuration instance
config = get_config()