// Configuration for admin panel
const CONFIG = {
    // Use environment-specific URLs
    API_URL: window.location.hostname === 'localhost' 
        ? 'https://app.cuwapp.com' 
        :'https://app.cuwapp.com',
    
    AUTH_URL: window.location.hostname === 'localhost'
        ? 'https://auth.cuwapp.com'
        : 'https://auth.cuwapp.com',
    
    LANDING_URL: window.location.hostname === 'localhost'
        ? 'http://localhost:10210'
        : 'https://www.cuwapp.com',
    
    ADMIN_URL: window.location.hostname === 'localhost'
        ? 'https://admin.cuwapp.com'
        : 'https://admin.cuwapp.com',
    
    // WebSocket URL for real-time updates
    WS_URL: window.location.hostname === 'localhost'
        ? 'ws://localhost:8000'
        : 'wss://app.cuwapp.com'
};

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}
