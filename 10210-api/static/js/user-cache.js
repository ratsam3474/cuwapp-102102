/**
 * Unified User Cache System for Cuwhapp
 * Manages user authentication state across all applications
 */

const UserCache = {
    CACHE_KEY: 'cuwhapp_user_cache',
    
    /**
     * Save user data to cache
     */
    setUser: function(userData) {
        const cacheData = {
            id: userData.id,
            email: userData.email,
            username: userData.username || userData.firstName || 'User',
            firstName: userData.firstName,
            lastName: userData.lastName,
            fullName: userData.fullName,
            imageUrl: userData.imageUrl,
            phone: userData.phone,
            isLoggedIn: true,
            lastUpdated: new Date().toISOString(),
            token: userData.token
        };
        
        // Save to localStorage
        localStorage.setItem(this.CACHE_KEY, JSON.stringify(cacheData));
        
        // Also save to whatsapp_agent_user for backward compatibility
        localStorage.setItem('whatsapp_agent_user', JSON.stringify(cacheData));
        
        return cacheData;
    },
    
    /**
     * Get user data from cache
     */
    getUser: function() {
        try {
            const cached = localStorage.getItem(this.CACHE_KEY);
            if (cached) {
                const data = JSON.parse(cached);
                // Check if cache is not too old (24 hours)
                const lastUpdated = new Date(data.lastUpdated);
                const now = new Date();
                const hoursDiff = (now - lastUpdated) / (1000 * 60 * 60);
                
                if (hoursDiff < 24) {
                    return data;
                }
            }
        } catch (error) {
            console.error('Error reading user cache:', error);
        }
        return null;
    },
    
    /**
     * Check if user is logged in
     */
    isLoggedIn: function() {
        const user = this.getUser();
        return user && user.isLoggedIn;
    },
    
    /**
     * Get user email
     */
    getEmail: function() {
        const user = this.getUser();
        return user ? user.email : null;
    },
    
    /**
     * Get username
     */
    getUsername: function() {
        const user = this.getUser();
        return user ? user.username : null;
    },
    
    /**
     * Clear user cache (logout)
     */
    clearUser: function() {
        localStorage.removeItem(this.CACHE_KEY);
        localStorage.removeItem('whatsapp_agent_user');
        localStorage.removeItem('user_subscription');
    },
    
    /**
     * Update specific user fields
     */
    updateUser: function(updates) {
        const current = this.getUser();
        if (current) {
            const updated = { ...current, ...updates, lastUpdated: new Date().toISOString() };
            localStorage.setItem(this.CACHE_KEY, JSON.stringify(updated));
            localStorage.setItem('whatsapp_agent_user', JSON.stringify(updated));
            return updated;
        }
        return null;
    }
};

// Make it available globally
if (typeof window !== 'undefined') {
    window.UserCache = UserCache;
}