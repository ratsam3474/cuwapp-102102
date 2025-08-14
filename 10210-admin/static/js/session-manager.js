/**
 * Session Manager - Client-side session management with plan-based timeouts
 * Free plan: 1-hour timeout with warnings
 * Paid plans: Persistent sessions
 */

class SessionManager {
    constructor() {
        this.token = localStorage.getItem('session_token');
        this.userInfo = null;
        this.warningShown = false;
        this.checkInterval = null;
        this.countdownInterval = null;
        
        // Start session monitoring if token exists
        if (this.token) {
            this.startSessionMonitoring();
        }
    }
    
    /**
     * Set session token and start monitoring
     */
    setToken(token, userInfo) {
        this.token = token;
        this.userInfo = userInfo;
        localStorage.setItem('session_token', token);
        
        if (userInfo) {
            localStorage.setItem('user_info', JSON.stringify(userInfo));
        }
        
        this.startSessionMonitoring();
    }
    
    /**
     * Get current session token
     */
    getToken() {
        return this.token;
    }
    
    /**
     * Get authorization header
     */
    getAuthHeader() {
        return this.token ? { 'Authorization': `Bearer ${this.token}` } : {};
    }
    
    /**
     * Start monitoring session status
     */
    startSessionMonitoring() {
        // Clear any existing intervals
        this.stopSessionMonitoring();
        
        // Initial validation
        this.validateSession();
        
        // Check session every 30 seconds
        this.checkInterval = setInterval(() => {
            this.validateSession();
        }, 30000);
    }
    
    /**
     * Stop monitoring session
     */
    stopSessionMonitoring() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
        
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
            this.countdownInterval = null;
        }
    }
    
    /**
     * Validate current session
     */
    async validateSession() {
        if (!this.token) return;
        
        try {
            const response = await fetch('/api/auth/session/validate', {
                headers: this.getAuthHeader()
            });
            
            const data = await response.json();
            
            if (!data.valid) {
                // Session expired
                this.handleSessionExpired(data);
            } else {
                // Update user info
                this.userInfo = {
                    user_id: data.user_id,
                    email: data.email,
                    plan_type: data.plan_type,
                    time_remaining: data.time_remaining
                };
                
                // Check for warning (free plan approaching timeout)
                if (data.warning && !this.warningShown) {
                    this.showTimeoutWarning(data.warning);
                }
                
                // Update UI with session info
                this.updateSessionUI();
            }
        } catch (error) {
            console.error('Session validation error:', error);
        }
    }
    
    /**
     * Show timeout warning for free plan users
     */
    showTimeoutWarning(warning) {
        this.warningShown = true;
        
        // Create warning banner
        const banner = document.createElement('div');
        banner.id = 'session-warning-banner';
        banner.className = 'session-warning-banner';
        banner.innerHTML = `
            <div class="warning-content">
                <span class="warning-icon">⚠️</span>
                <div class="warning-text">
                    <strong>Session Expiring Soon!</strong>
                    <p>${warning.message}</p>
                    <p class="countdown" id="session-countdown">Time remaining: ${warning.minutes_remaining} minutes</p>
                </div>
                <div class="warning-actions">
                    <button onclick="sessionManager.upgradeNow()" class="btn-upgrade">Upgrade Now</button>
                    <button onclick="sessionManager.dismissWarning()" class="btn-dismiss">Dismiss</button>
                </div>
            </div>
        `;
        
        document.body.prepend(banner);
        
        // Start countdown
        this.startCountdown(warning.minutes_remaining);
        
        // Add styles if not already added
        if (!document.getElementById('session-manager-styles')) {
            const styles = document.createElement('style');
            styles.id = 'session-manager-styles';
            styles.textContent = `
                .session-warning-banner {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    background: linear-gradient(135deg, #ff6b6b, #ff8787);
                    color: white;
                    padding: 15px;
                    z-index: 10000;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                    animation: slideDown 0.3s ease-out;
                }
                
                @keyframes slideDown {
                    from { transform: translateY(-100%); }
                    to { transform: translateY(0); }
                }
                
                .warning-content {
                    max-width: 1200px;
                    margin: 0 auto;
                    display: flex;
                    align-items: center;
                    gap: 20px;
                }
                
                .warning-icon {
                    font-size: 32px;
                }
                
                .warning-text {
                    flex: 1;
                }
                
                .warning-text strong {
                    font-size: 18px;
                    margin-bottom: 5px;
                    display: block;
                }
                
                .warning-text p {
                    margin: 5px 0;
                    font-size: 14px;
                }
                
                .countdown {
                    font-weight: bold;
                    font-size: 16px;
                }
                
                .warning-actions {
                    display: flex;
                    gap: 10px;
                }
                
                .warning-actions button {
                    padding: 8px 20px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-weight: bold;
                    transition: all 0.3s;
                }
                
                .btn-upgrade {
                    background: white;
                    color: #ff6b6b;
                }
                
                .btn-upgrade:hover {
                    background: #f8f8f8;
                    transform: scale(1.05);
                }
                
                .btn-dismiss {
                    background: rgba(255,255,255,0.2);
                    color: white;
                }
                
                .btn-dismiss:hover {
                    background: rgba(255,255,255,0.3);
                }
                
                .session-expired-modal {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0,0,0,0.8);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 10001;
                }
                
                .expired-content {
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    max-width: 500px;
                    text-align: center;
                }
                
                .expired-content h2 {
                    color: #ff6b6b;
                    margin-bottom: 20px;
                }
                
                .expired-content p {
                    margin: 15px 0;
                    color: #666;
                }
                
                .expired-actions {
                    display: flex;
                    gap: 15px;
                    justify-content: center;
                    margin-top: 25px;
                }
                
                .expired-actions button {
                    padding: 12px 30px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-weight: bold;
                    font-size: 16px;
                    transition: all 0.3s;
                }
                
                .btn-login {
                    background: #4CAF50;
                    color: white;
                }
                
                .btn-login:hover {
                    background: #45a049;
                }
                
                .btn-upgrade-now {
                    background: #ff6b6b;
                    color: white;
                }
                
                .btn-upgrade-now:hover {
                    background: #ff5252;
                }
            `;
            document.head.appendChild(styles);
        }
    }
    
    /**
     * Start countdown timer
     */
    startCountdown(minutes) {
        let seconds = minutes * 60;
        
        this.countdownInterval = setInterval(() => {
            seconds--;
            
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            
            const countdownEl = document.getElementById('session-countdown');
            if (countdownEl) {
                countdownEl.textContent = `Time remaining: ${mins}:${secs.toString().padStart(2, '0')}`;
            }
            
            if (seconds <= 0) {
                clearInterval(this.countdownInterval);
                this.handleSessionExpired({
                    reason: 'free_plan_timeout',
                    message: 'Your session has expired after 1 hour (Free plan limit)'
                });
            }
        }, 1000);
    }
    
    /**
     * Handle session expiration
     */
    handleSessionExpired(data) {
        // Clear token
        this.token = null;
        localStorage.removeItem('session_token');
        localStorage.removeItem('user_info');
        
        // Stop monitoring
        this.stopSessionMonitoring();
        
        // Remove warning banner if exists
        const banner = document.getElementById('session-warning-banner');
        if (banner) {
            banner.remove();
        }
        
        // Show expiration modal
        const modal = document.createElement('div');
        modal.className = 'session-expired-modal';
        modal.innerHTML = `
            <div class="expired-content">
                <h2>⏰ Session Expired</h2>
                <p><strong>${data.message || 'Your session has expired'}</strong></p>
                ${data.reason === 'free_plan_timeout' ? `
                    <p>Free plan users have a 1-hour session limit.</p>
                    <p>Upgrade to Starter plan or higher for unlimited session time!</p>
                ` : ''}
                <div class="expired-actions">
                    <button onclick="sessionManager.login()" class="btn-login">Login Again</button>
                    ${data.reason === 'free_plan_timeout' ? `
                        <button onclick="sessionManager.upgradeNow()" class="btn-upgrade-now">Upgrade Plan</button>
                    ` : ''}
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
    
    /**
     * Dismiss warning banner
     */
    dismissWarning() {
        const banner = document.getElementById('session-warning-banner');
        if (banner) {
            banner.style.animation = 'slideUp 0.3s ease-out';
            setTimeout(() => banner.remove(), 300);
        }
    }
    
    /**
     * Navigate to upgrade page
     */
    upgradeNow() {
        window.location.href = '/checkout.html';
    }
    
    /**
     * Navigate to login page
     */
    login() {
        window.location.href = '/login.html';
    }
    
    /**
     * Logout current session
     */
    async logout() {
        if (this.token) {
            try {
                await fetch('/api/auth/logout', {
                    method: 'POST',
                    headers: this.getAuthHeader()
                });
            } catch (error) {
                console.error('Logout error:', error);
            }
        }
        
        // Clear local data
        this.token = null;
        this.userInfo = null;
        localStorage.removeItem('session_token');
        localStorage.removeItem('user_info');
        
        // Stop monitoring
        this.stopSessionMonitoring();
        
        // Redirect to login
        window.location.href = '/login.html';
    }
    
    /**
     * Update UI with session information
     */
    updateSessionUI() {
        // Update user info display if element exists
        const userInfoEl = document.getElementById('user-info');
        if (userInfoEl && this.userInfo) {
            userInfoEl.innerHTML = `
                <span class="user-email">${this.userInfo.email}</span>
                <span class="user-plan">${this.userInfo.plan_type} Plan</span>
                ${this.userInfo.plan_type === 'free' ? 
                    `<span class="session-time">${this.userInfo.time_remaining}</span>` : 
                    '<span class="session-persistent">Persistent Session</span>'
                }
            `;
        }
    }
    
    /**
     * Make authenticated API request
     */
    async apiRequest(url, options = {}) {
        const headers = {
            ...this.getAuthHeader(),
            ...options.headers
        };
        
        const response = await fetch(url, {
            ...options,
            headers
        });
        
        // Check for session expiration
        if (response.status === 401) {
            const data = await response.json();
            if (data.error === 'session_timeout' || data.expired) {
                this.handleSessionExpired(data);
                throw new Error('Session expired');
            }
        }
        
        return response;
    }
}

// Create global instance
const sessionManager = new SessionManager();

// Export for use in other modules
window.sessionManager = sessionManager;