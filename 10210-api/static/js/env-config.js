/**
 * Environment Configuration for Static Files
 * This file provides environment-based URLs for all static HTML/JS files
 * It detects the current environment and provides the appropriate URLs
 */

(function() {
    // Detect current environment based on hostname
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    
    // Check if we're in production or development
    const isProduction = hostname.includes('cuwapp.com') || 
                        hostname === '34.173.85.56' ||
                        hostname === '34.133.143.67';
    
    const isDevelopment = hostname === 'localhost' || 
                         hostname === '127.0.0.1' ||
                         hostname.startsWith('192.168.');
    
    // Define environment-specific configurations
    const configs = {
        production: {
            API_GATEWAY_URL: 'https://app.cuwapp.com',
            AUTH_SERVICE_URL: 'https://auth.cuwapp.com',
            LANDING_PAGE_URL: 'https://cuwapp.com',
            ADMIN_SERVICE_URL: 'https://admin.cuwapp.com',
            WAHA_URL: 'http://34.133.143.67:4500',
            NEW_SERVER_IP: '34.173.85.56',
            WAHA_VM_IP: '34.133.143.67',
            USER_VM_IP: '34.173.85.56'
        },
        development: {
            API_GATEWAY_URL: `${protocol}//${hostname}:8000`,
            AUTH_SERVICE_URL: `${protocol}//${hostname}:5502`,
            LANDING_PAGE_URL: `${protocol}//${hostname}:5500`,
            ADMIN_SERVICE_URL: `${protocol}//${hostname}:8005`,
            WAHA_URL: `${protocol}//${hostname}:4500`,
            NEW_SERVER_IP: hostname,
            WAHA_VM_IP: hostname,
            USER_VM_IP: hostname
        }
    };
    
    // Select configuration based on environment
    let config;
    if (isProduction) {
        config = configs.production;
    } else if (isDevelopment) {
        config = configs.development;
    } else {
        // Default to production URLs for unknown environments
        config = configs.production;
    }
    
    // Override with any values from sessionStorage or localStorage
    const storedConfig = {};
    
    // Check sessionStorage first (higher priority)
    if (typeof sessionStorage !== 'undefined') {
        Object.keys(config).forEach(key => {
            const stored = sessionStorage.getItem(key);
            if (stored) {
                storedConfig[key] = stored;
            }
        });
    }
    
    // Check localStorage as fallback
    if (typeof localStorage !== 'undefined') {
        Object.keys(config).forEach(key => {
            if (!storedConfig[key]) {
                const stored = localStorage.getItem(key);
                if (stored) {
                    storedConfig[key] = stored;
                }
            }
        });
    }
    
    // Merge stored values with defaults
    const finalConfig = { ...config, ...storedConfig };
    
    // Expose configuration globally
    window.ENV = finalConfig;
    
    // Helper function to get a config value
    window.getEnvConfig = function(key, defaultValue) {
        return window.ENV[key] || defaultValue;
    };
    
    // Helper function to build API URL
    window.buildApiUrl = function(endpoint) {
        const baseUrl = window.ENV.API_GATEWAY_URL;
        if (endpoint.startsWith('/')) {
            return baseUrl + endpoint;
        }
        return baseUrl + '/' + endpoint;
    };
    
    // Helper function to build auth URL
    window.buildAuthUrl = function(endpoint) {
        const baseUrl = window.ENV.AUTH_SERVICE_URL;
        if (endpoint.startsWith('/')) {
            return baseUrl + endpoint;
        }
        return baseUrl + '/' + endpoint;
    };
    
    // Log configuration in development
    if (isDevelopment && console && console.log) {
        console.log('Environment Configuration Loaded:', window.ENV);
    }
})();