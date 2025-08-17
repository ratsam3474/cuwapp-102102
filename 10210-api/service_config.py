"""
Service Configuration for all interconnected services
"""
import os

# Determine if we're in production or local environment
IS_PRODUCTION = os.getenv('ENV', 'development') == 'production'

# Get environment variables with defaults
NEW_SERVER_IP = os.getenv('NEW_SERVER_IP', '34.173.85.56')
WAHA_VM_EXTERNAL_IP = os.getenv('WAHA_VM_EXTERNAL_IP', '34.133.143.67')

# Service URLs from environment
if IS_PRODUCTION:
    # Production URLs from environment variables
    API_URL = os.getenv('API_GATEWAY_URL', 'https://app.cuwapp.com')
    AUTH_URL = os.getenv('AUTH_SERVICE_URL', 'https://auth.cuwapp.com')
    ADMIN_URL = os.getenv('ADMIN_SERVICE_URL', 'https://admin.cuwapp.com')
    LANDING_URL = os.getenv('LANDING_PAGE_URL', 'https://cuwapp.com')
    
    # Microservices
    INSTANCE_MANAGER_URL = os.getenv('CONTAINER_MANAGER_URL', 
                                     'https://container-manager-337193391523.us-central1.run.app')
    
    # WAHA URLs
    WAHA_FREE_URL = f'http://{WAHA_VM_EXTERNAL_IP}:4500'
    WAHA_PAID_URL_BASE = f'http://{WAHA_VM_EXTERNAL_IP}:4501'
    
    # WebSocket URLs
    WS_PROTOCOL = 'wss' if API_URL.startswith('https') else 'ws'
    WS_URL = f'{WS_PROTOCOL}://app.cuwapp.com'
else:
    # Local development URLs
    BASE_URL = 'http://localhost'
    API_URL = f'{BASE_URL}:8000'
    AUTH_URL = f'{BASE_URL}:5502'
    ADMIN_URL = f'{BASE_URL}:8005'
    LANDING_URL = f'{BASE_URL}:5500'
    INSTANCE_MANAGER_URL = f'{BASE_URL}:8002'
    
    # WAHA URLs
    WAHA_FREE_URL = f'{BASE_URL}:4500'
    WAHA_PAID_URL_BASE = f'{BASE_URL}:4501'
    
    # WebSocket URLs
    WS_URL = f'ws://localhost:8000'

# WAHA Pool Configuration
WAHA_MAX_SESSIONS_PER_INSTANCE = int(os.environ.get('WAHA_MAX_SESSIONS_PER_INSTANCE', '10'))

# WAHA Base URL from environment
WAHA_BASE_URL = os.environ.get('WAHA_BASE_URL', f'http://{WAHA_VM_EXTERNAL_IP}' if IS_PRODUCTION else 'http://localhost')

# CORS settings - dynamically built from environment
CORS_ORIGINS = []

# Add production domains
if IS_PRODUCTION:
    CORS_ORIGINS.extend([
        os.getenv('LANDING_PAGE_URL', 'https://cuwapp.com'),
        os.getenv('AUTH_SERVICE_URL', 'https://auth.cuwapp.com'),
        os.getenv('API_GATEWAY_URL', 'https://app.cuwapp.com'),
        os.getenv('ADMIN_SERVICE_URL', 'https://admin.cuwapp.com'),
        f"http://{NEW_SERVER_IP}:5500",
        f"http://{NEW_SERVER_IP}:5502",
        f"http://{NEW_SERVER_IP}:8000",
        f"http://{NEW_SERVER_IP}:8005",
    ])
else:
    # Local development origins
    CORS_ORIGINS.extend([
        "http://localhost:5500",
        "http://localhost:5502",
        "http://localhost:8000",
        "http://localhost:8005",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:5502",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8005",
    ])

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
