/**
 * Session Check - Verifies cache validity against Clerk session
 * This script periodically checks if the cached user is still valid
 */

(function() {
    // Check session validity every 30 seconds
    const SESSION_CHECK_INTERVAL = 30000;
    
    async function checkSessionValidity() {
        const cachedUser = UserCache.getUser();
        
        if (cachedUser && cachedUser.isLoggedIn) {
            try {
                // Try to verify the session with a simple API call
                const response = await fetch('/api/users/subscription/' + cachedUser.id, {
                    headers: {
                        'Authorization': `Bearer ${cachedUser.token || 'test_token'}`
                    }
                });
                
                if (response.status === 401) {
                    // Session is invalid, clear cache
                    console.log('Session expired, clearing cache...');
                    UserCache.clearUser();
                    
                    // Show notification if available
                    if (typeof app !== 'undefined' && app.showToast) {
                        app.showToast('Session expired. Please sign in again.', 'warning');
                    }
                    
                    // Reload to update UI
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                }
            } catch (error) {
                console.error('Session check error:', error);
            }
        }
    }
    
    // Start checking after page loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            setInterval(checkSessionValidity, SESSION_CHECK_INTERVAL);
        });
    } else {
        setInterval(checkSessionValidity, SESSION_CHECK_INTERVAL);
    }
    
    // Also check on window focus
    window.addEventListener('focus', checkSessionValidity);
})();