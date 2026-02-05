/**
 * Client-side Bearer Token Validator for Embedded Dash App
 * Validates Bearer token expiration and handles reconnection
 */

class EmbeddedTokenValidator {
    constructor() {
        this.token = null;
        this.checkInterval = null;
        this.checkIntervalMs = 10000; // Check every 10 seconds (more frequent for testing)
        this.warningThresholdMs = 300000; // Warn 5 minutes before expiry
        this.isEmbedded = this.detectEmbeddedEnvironment();
        this.initialized = false;
        
        console.log('[TokenValidator] Initialized - Embedded:', this.isEmbedded);
        console.log('[TokenValidator] Current URL:', window.location.href);
        console.log('[TokenValidator] Parent window:', window.parent !== window ? 'Different' : 'Same');
        
        // Always initialize for testing purposes, but be more aggressive about embedded detection
        this.init();
    }
    
    detectEmbeddedEnvironment() {
        // Check if running in embedded environment
        try {
            const isInIframe = window.parent !== window;
            const hostname = window.location.hostname;
            const referrer = document.referrer;
            const userAgent = navigator.userAgent;
            
            console.log('[TokenValidator] Environment check:');
            console.log('  - In iframe:', isInIframe);
            console.log('  - Hostname:', hostname);
            console.log('  - Referrer:', referrer);
            console.log('  - User Agent:', userAgent);
            
            // More flexible embedded detection - assume embedded if any of these conditions are met
            const isEmbedded = (
                isInIframe ||  // In an iframe
                hostname === 'data.energyintel.com' ||  // Production domain
                hostname === 'localhost' ||  // Local testing
                referrer.includes('www.energyintel.com') ||  // Referred from main site
                referrer.includes('energyintel.com') ||  // Any energyintel domain
                window.location.search.includes('bearer_token') ||  // Token in URL (testing)
                localStorage.getItem('dash_bearer_token') ||  // Token in storage
                sessionStorage.getItem('dash_bearer_token')  // Token in session storage
            );
            
            console.log('[TokenValidator] Embedded environment detected:', isEmbedded);
            return isEmbedded;
        } catch (e) {
            console.error('[TokenValidator] Error detecting embedded environment:', e);
            // Default to embedded for safety
            return true;
        }
    }
    
    init() {
        if (this.initialized) {
            console.log('[TokenValidator] Already initialized, skipping');
            return;
        }
        
        console.log('[TokenValidator] Starting token validation initialization');
        this.initialized = true;
        
        // Setup parent communication first
        this.setupParentCommunication();
        
        // Try to extract token from various sources
        this.extractTokenFromSources();
        
        // Request token from parent window if in iframe
        if (window.parent !== window) {
            this.requestTokenFromParent();
        }
        
        // Start validation after a short delay to allow token to be set
        setTimeout(() => {
            if (this.token) {
                console.log('[TokenValidator] Token found, starting validation');
                this.validateToken();
                this.startPeriodicValidation();
            } else {
                console.log('[TokenValidator] No token received, requesting again...');
                if (window.parent !== window) {
                    this.requestTokenFromParent();
                }
                
                // Try again after another delay
                setTimeout(() => {
                    if (this.token) {
                        this.validateToken();
                        this.startPeriodicValidation();
                    } else {
                        console.warn('[TokenValidator] Still no token - this may be normal for direct access');
                        // For testing, show a subtle indicator
                        if (window.location.hostname === 'localhost') {
                            this.showTokenNeededIndicator();
                        }
                    }
                }, 3000);
            }
        }, 1000);
    }
    
    extractTokenFromSources() {
        console.log('[TokenValidator] Extracting token from various sources...');
        
        // 1. Check localStorage
        const storedToken = localStorage.getItem('dash_bearer_token');
        if (storedToken) {
            console.log('[TokenValidator] Found token in localStorage');
            this.setToken(storedToken);
            return;
        }
        
        // 2. Check sessionStorage
        const sessionToken = sessionStorage.getItem('dash_bearer_token');
        if (sessionToken) {
            console.log('[TokenValidator] Found token in sessionStorage');
            this.setToken(sessionToken);
            return;
        }
        
        // 3. Check if token is in URL parameters (for testing)
        const urlParams = new URLSearchParams(window.location.search);
        const urlToken = urlParams.get('bearer_token');
        if (urlToken) {
            console.log('[TokenValidator] Found token in URL parameters');
            this.setToken(urlToken);
            return;
        }
        
        console.log('[TokenValidator] No token found in local sources');
    }
    
    showTokenNeededIndicator() {
        // Show a small indicator that token is needed (for debugging)
        const indicator = document.createElement('div');
        indicator.id = 'token-needed-indicator';
        indicator.innerHTML = `
            <div style="
                position: fixed;
                top: 10px;
                right: 10px;
                background: #ffc107;
                color: #000;
                padding: 8px 12px;
                border-radius: 4px;
                font-size: 12px;
                z-index: 9999;
                font-family: Arial, sans-serif;
                cursor: pointer;
            " onclick="this.remove()">
                ⚠️ Bearer token needed for validation
            </div>
        `;
        document.body.appendChild(indicator);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            const el = document.getElementById('token-needed-indicator');
            if (el) el.remove();
        }, 10000);
    }
    
    setToken(token) {
        if (!token) {
            console.log('[TokenValidator] No token provided');
            return;
        }
        
        // Clean token format
        if (token.startsWith('Bearer ')) {
            token = token.replace('Bearer ', '');
        }
        
        this.token = token;
        console.log('[TokenValidator] Token set, validating...');
        
        // Validate immediately
        this.validateToken();
        
        // Start periodic validation if not already running
        if (!this.checkInterval) {
            this.startPeriodicValidation();
        }
    }
    
    async validateToken() {
        if (!this.token) {
            console.log('[TokenValidator] No token to validate');
            return { valid: false, reason: 'no_token' };
        }
        
        try {
            // Use server-side validation endpoint
            const response = await fetch('/api/validate-token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`
                },
                body: JSON.stringify({ token: this.token })
            });
            
            const result = await response.json();
            
            console.log(`[TokenValidator] Server validation result:`, result);
            
            if (result.valid) {
                if (result.time_until_expiry && result.time_until_expiry <= this.warningThresholdMs / 1000) {
                    console.log(`[TokenValidator] Token expiring soon (${result.time_until_expiry}s)`);
                    this.handleTokenExpiringSoon(result.time_until_expiry);
                }
                return result;
            } else {
                if (result.reason === 'expired') {
                    console.log('[TokenValidator] Token expired');
                    this.handleTokenExpired();
                } else {
                    console.log('[TokenValidator] Token invalid:', result.reason);
                }
                return result;
            }
            
        } catch (error) {
            console.error('[TokenValidator] Error validating token:', error);
            
            // Fallback to client-side validation
            return this.validateTokenClientSide();
        }
    }
    
    validateTokenClientSide() {
        try {
            // Decode JWT token (without verification - just to check expiry)
            const payload = this.decodeJWT(this.token);
            
            if (!payload.exp) {
                console.log('[TokenValidator] Token has no expiry claim');
                return { valid: true, reason: 'no_expiry' };
            }
            
            const currentTime = Math.floor(Date.now() / 1000);
            const expiryTime = payload.exp;
            const timeUntilExpiry = expiryTime - currentTime;
            
            console.log(`[TokenValidator] Client-side: Token expires in ${timeUntilExpiry} seconds`);
            
            if (timeUntilExpiry <= 0) {
                console.log('[TokenValidator] Client-side: Token expired');
                this.handleTokenExpired();
                return { valid: false, reason: 'expired' };
            }
            
            if (timeUntilExpiry <= this.warningThresholdMs / 1000) {
                console.log(`[TokenValidator] Client-side: Token expiring soon (${timeUntilExpiry}s)`);
                this.handleTokenExpiringSoon(timeUntilExpiry);
                return { valid: true, reason: 'expiring_soon', timeUntilExpiry };
            }
            
            return { valid: true, reason: 'valid', timeUntilExpiry };
            
        } catch (error) {
            console.error('[TokenValidator] Client-side validation error:', error);
            return { valid: false, reason: 'invalid' };
        }
    }
    
    decodeJWT(token) {
        // Simple JWT decoder (no signature verification)
        const parts = token.split('.');
        if (parts.length !== 3) {
            throw new Error('Invalid JWT format');
        }
        
        const payload = parts[1];
        const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
        return JSON.parse(decoded);
    }
    
    handleTokenExpired() {
        console.log('[TokenValidator] Handling expired token');
        
        // Stop periodic validation
        this.stopPeriodicValidation();
        
        // Show reconnect overlay
        this.showReconnectOverlay();
        
        // Notify parent window
        this.notifyParent({
            type: 'DASH_TOKEN_EXPIRED',
            action: 'TOKEN_EXPIRED',
            timestamp: Date.now()
        });
    }
    
    handleTokenExpiringSoon(timeUntilExpiry) {
        console.log(`[TokenValidator] Token expiring in ${timeUntilExpiry} seconds`);
        
        // Notify parent window to refresh token
        this.notifyParent({
            type: 'DASH_TOKEN_EXPIRING',
            action: 'REQUEST_TOKEN_REFRESH',
            timeUntilExpiry: timeUntilExpiry,
            timestamp: Date.now()
        });
    }
    
    showReconnectOverlay() {
        // Remove existing overlay if present
        this.hideReconnectOverlay();
        
        // Create and show the reconnect overlay
        const overlay = document.createElement('div');
        overlay.id = 'dash-reconnect-overlay';
        overlay.innerHTML = `
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.8);
                z-index: 10000;
                display: flex;
                justify-content: center;
                align-items: center;
                font-family: Arial, sans-serif;
            ">
                <div style="
                    background: white;
                    padding: 40px;
                    border-radius: 12px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                    text-align: center;
                    max-width: 500px;
                    width: 90%;
                ">
                    <div style="font-size: 48px; margin-bottom: 20px;">📡</div>
                    <h2 style="margin: 0 0 15px 0; color: #333;">Lost Connection to Dash App</h2>
                    <p style="color: #666; margin-bottom: 25px; line-height: 1.5;">
                        Reconnect now to keep your filters and any changes.
                    </p>
                    <button id="dash-reconnect-btn" style="
                        background-color: #007bff;
                        color: white;
                        border: none;
                        padding: 12px 30px;
                        border-radius: 6px;
                        font-size: 16px;
                        font-weight: bold;
                        cursor: pointer;
                        transition: all 0.3s ease;
                    ">
                        🔄 Reconnect
                    </button>
                    <div id="dash-status-message" style="
                        margin-top: 20px;
                        padding: 10px;
                        border-radius: 4px;
                        font-size: 14px;
                        display: none;
                    "></div>
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        // Add click handler
        document.getElementById('dash-reconnect-btn').onclick = () => {
            this.handleReconnectClick();
        };
    }
    
    handleReconnectClick() {
        const btn = document.getElementById('dash-reconnect-btn');
        
        btn.disabled = true;
        btn.innerHTML = '🔄 Reconnecting...';
        
        this.showStatus('Refreshing authentication token...', 'info');
        
        // Request token refresh from parent
        this.notifyParent({
            type: 'DASH_TOKEN_EXPIRED',
            action: 'REQUEST_TOKEN_REFRESH',
            timestamp: Date.now()
        });
        
        // Timeout after 10 seconds
        setTimeout(() => {
            if (btn && btn.disabled) {
                this.showStatus('Token refresh timeout. Reloading...', 'info');
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            }
        }, 10000);
    }
    
    showStatus(message, type = 'info') {
        const statusEl = document.getElementById('dash-status-message');
        if (statusEl) {
            statusEl.textContent = message;
            statusEl.className = `status-${type}`;
            statusEl.style.display = 'block';
            
            // Style based on type
            if (type === 'success') {
                statusEl.style.backgroundColor = '#d4edda';
                statusEl.style.color = '#155724';
                statusEl.style.border = '1px solid #c3e6cb';
            } else if (type === 'error') {
                statusEl.style.backgroundColor = '#f8d7da';
                statusEl.style.color = '#721c24';
                statusEl.style.border = '1px solid #f5c6cb';
            } else {
                statusEl.style.backgroundColor = '#d1ecf1';
                statusEl.style.color = '#0c5460';
                statusEl.style.border = '1px solid #bee5eb';
            }
        }
    }
    
    hideReconnectOverlay() {
        const overlay = document.getElementById('dash-reconnect-overlay');
        if (overlay) {
            overlay.remove();
        }
    }
    
    startPeriodicValidation() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
        }
        
        this.checkInterval = setInterval(() => {
            this.validateToken();
        }, this.checkIntervalMs);
        
        console.log(`[TokenValidator] Started periodic validation (${this.checkIntervalMs}ms)`);
    }
    
    stopPeriodicValidation() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
            console.log('[TokenValidator] Stopped periodic validation');
        }
    }
    
    setupParentCommunication() {
        window.addEventListener('message', (event) => {
            console.log('[TokenValidator] Received message:', event.data);
            
            if (event.data.type === 'DASH_TOKEN_REFRESH_RESPONSE') {
                console.log('[TokenValidator] Received token refresh response:', event.data);
                
                if (event.data.success && event.data.token) {
                    // Update token
                    this.setToken(event.data.token);
                    
                    // Hide overlay
                    this.hideReconnectOverlay();
                    
                    // Restart periodic validation
                    this.startPeriodicValidation();
                    
                    console.log('[TokenValidator] Token refreshed successfully');
                } else {
                    this.showStatus('Token refresh failed. Please try again.', 'error');
                    
                    const btn = document.getElementById('dash-reconnect-btn');
                    if (btn) {
                        btn.disabled = false;
                        btn.innerHTML = '🔄 Reconnect';
                    }
                }
            } else if (event.data.type === 'DASH_TOKEN_UPDATE') {
                console.log('[TokenValidator] Received token update from parent');
                this.setToken(event.data.token);
            } else if (event.data.type === 'DASH_TOKEN_RESPONSE') {
                console.log('[TokenValidator] Received token from parent');
                if (event.data.token) {
                    this.setToken(event.data.token);
                } else {
                    console.log('[TokenValidator] No token received from parent');
                }
            } else if (event.data.type === 'DASH_TOKEN_STATUS_REQUEST') {
                // Handle token status request (for testing)
                console.log('[TokenValidator] Token status requested');
                this.validateToken().then(status => {
                    this.notifyParent({
                        type: 'DASH_TOKEN_STATUS_RESPONSE',
                        status: status,
                        timestamp: Date.now()
                    });
                });
            } else if (event.data.type === 'DASH_SHOW_OVERLAY_MANUAL') {
                // Handle manual overlay show (for testing)
                console.log('[TokenValidator] Manual overlay show requested');
                this.showReconnectOverlay();
            } else if (event.data.type === 'DASH_TOKEN_CLEAR') {
                // Handle token clear (for testing)
                console.log('[TokenValidator] Token clear requested');
                this.token = null;
                this.stopPeriodicValidation();
                localStorage.removeItem('dash_bearer_token');
                sessionStorage.removeItem('dash_bearer_token');
            }
        });
    }
    
    requestTokenFromParent() {
        console.log('[TokenValidator] Requesting token from parent window');
        
        this.notifyParent({
            type: 'DASH_TOKEN_REQUEST',
            action: 'REQUEST_CURRENT_TOKEN',
            timestamp: Date.now()
        });
    }
    
    notifyParent(message) {
        if (window.parent && window.parent !== window) {
            console.log('[TokenValidator] Notifying parent:', message);
            window.parent.postMessage(message, '*');
        }
    }
    
    // Public methods for manual token management
    updateToken(newToken) {
        console.log('[TokenValidator] Manual token update');
        this.setToken(newToken);
    }
    
    async getCurrentTokenStatus() {
        return await this.validateToken();
    }
    
    destroy() {
        console.log('[TokenValidator] Destroying validator');
        this.stopPeriodicValidation();
        this.hideReconnectOverlay();
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('[TokenValidator] DOM loaded, initializing...');
        window.dashTokenValidator = new EmbeddedTokenValidator();
    });
} else {
    console.log('[TokenValidator] DOM already ready, initializing immediately...');
    window.dashTokenValidator = new EmbeddedTokenValidator();
}

// Export for manual usage
window.EmbeddedTokenValidator = EmbeddedTokenValidator;

// Add a simple indicator that the script has loaded
console.log('[TokenValidator] Script loaded successfully at', new Date().toISOString());

// Add to window for debugging
window.tokenValidatorLoaded = true;

// Global helper function for manual token testing
window.setDashBearerToken = function(token) {
    console.log('[Global] Setting Bearer token manually:', token ? 'Token provided' : 'No token');
    if (window.dashTokenValidator) {
        window.dashTokenValidator.updateToken(token);
    } else {
        // Store for later initialization
        localStorage.setItem('dash_bearer_token', token);
        console.log('[Global] Token stored in localStorage for later initialization');
    }
};

// Global helper function to check token status
window.checkDashTokenStatus = async function() {
    if (window.dashTokenValidator) {
        const status = await window.dashTokenValidator.getCurrentTokenStatus();
        console.log('[Global] Current token status:', status);
        return status;
    } else {
        console.log('[Global] Token validator not initialized');
        return { valid: false, reason: 'validator_not_initialized' };
    }
};

// Global helper function to force show reconnect overlay (for testing)
window.showDashReconnectOverlay = function() {
    if (window.dashTokenValidator) {
        window.dashTokenValidator.showReconnectOverlay();
        console.log('[Global] Reconnect overlay shown manually');
    } else {
        console.log('[Global] Token validator not initialized');
    }
};