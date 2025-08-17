"""
Service Configuration for all interconnected services
"""
import os

# Determine if we're in production or local environment
IS_PRODUCTION = os.getenv('SERVER_IP', '') == '174.138.55.42' or os.getenv('ENV', '') == 'production'

# Service URLs
if IS_PRODUCTION:
    # Production URLs
    BASE_URL = 'http://174.138.55.42'
    API_URL = 'https://app.cuwapp.com'
    AUTH_URL = 'https://auth.cuwapp.com'
    ADMIN_URL = 'https://admin.cuwapp.com'
    LANDING_URL = 'https://www.cuwapp.com'
    INSTANCE_MANAGER_URL = f'{BASE_URL}:8002'
    
    # WAHA URLs
    WAHA_FREE_URL = f'{BASE_URL}:4500'
    WAHA_PAID_URL_BASE = f'{BASE_URL}:4501'
    
    # WebSocket URLs
    WS_URL = f'ws://174.138.55.42:8000'
else:
    # Local development URLs
    BASE_URL = 'http://localhost'
    API_URL = f'{BASE_URL}:8000'
    AUTH_URL = f'{BASE_URL}:5502'
    ADMIN_URL = f'{BASE_URL}:8001'
    LANDING_URL = f'{BASE_URL}:10210'
    INSTANCE_MANAGER_URL = f'{BASE_URL}:8002'
    
    # WAHA URLs
    WAHA_FREE_URL = f'{BASE_URL}:4500'
    WAHA_PAID_URL_BASE = f'{BASE_URL}:4501'
    
    # WebSocket URLs
    WS_URL = 'wss://app.cuwapp.com'

# WAHA Pool Configuration
WAHA_MAX_SESSIONS_PER_INSTANCE = int(os.environ.get('WAHA_MAX_SESSIONS_PER_INSTANCE', '10'))  # Default 10 sessions per WAHA instance

# WAHA Base URL - can be localhost, Docker machine IP, or domain
WAHA_BASE_URL = os.environ.get('WAHA_BASE_URL', 'http://localhost')  # Change this to your Docker machine IP

# CORS settings
CORS_ORIGINS = [
    "https://www.cuwapp.com",
    "https://auth.cuwapp.com",
    "https://app.cuwapp.com",
    "https://admin.cuwapp.com",
    "http://localhost:10210",
    "http://174.138.55.42:5500",
    "http://174.138.55.42:5502",
    "http://174.138.55.42:8000",
    "http://174.138.55.42:8001",
    "http://174.138.55.42:10210",
]

# Export all configurations
SERVICE_CONFIG = {
    'api_url': API_URL,
    'auth_url': AUTH_URL,
    'admin_url': ADMIN_URL,
    'landing_url': LANDING_URL,
    'instance_manager_url': INSTANCE_MANAGER_URL,
    'waha_free_url': WAHA_FREE_URL,
    'waha_paid_url_base': WAHA_PAID_URL_BASE,
    'ws_url': WS_URL,
    'cors_origins': CORS_ORIGINS,
    'is_production': IS_PRODUCTION
}
