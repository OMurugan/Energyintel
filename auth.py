"""
JWT-based authentication middleware for embedded Dash applications.
Supports both simple tokens and HS512 JWT tokens as used by the client.
"""

import os
import functools
import os
import time
import json
import hmac
import hashlib
import base64
import jwt
from flask import Flask, request, g, jsonify, Response
from functools import wraps

class TokenAuth:
    """JWT and token-based authentication for embedded Dash apps."""
    
    def __init__(self, app):
        self.app = app
        self.server = app.server
        
        # Token configuration
        self.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
        # Client's JWT secret key - should match the host app's SECRET_KEY
        self.jwt_secret = os.environ.get('EMBEDDED_SECRET_KEY', 'secret_key')
        # QUICK EXPIRATION FOR TESTING: 15 minutes instead of 24 hours
        self.token_expiry = int(os.environ.get('TOKEN_EXPIRY_MINUTES', '15')) * 60  # 15 minutes for testing
        
        # Add before_request and after_request handlers
        self.server.before_request(self._check_token_auth)
        self.server.after_request(self._set_auth_cookie)
        
        # Load valid tokens after initialization
        self.valid_tokens = self._load_valid_tokens()
        print(f"DEBUG: Loaded {len(self.valid_tokens)} valid tokens including admin JWT")
    
    def _load_valid_tokens(self):
        """Load valid tokens from environment or use defaults."""
        # For testing, remove non-expiring tokens to force expiry testing
        # Default tokens for development/demo
        default_tokens = {
            # 'admin-token-123': {
            #     'user': 'admin',
            #     'permissions': ['read', 'write', 'admin'],
            #     'expires': None  # Never expires
            # },
            # 'user-token-456': {
            #     'user': 'user',
            #     'permissions': ['read'],
            #     'expires': None  # Never expires
            # }
        }
        
        # Load custom tokens from environment if provided
        custom_tokens_str = os.environ.get('VALID_TOKENS', '')
        custom_tokens = {}
        if custom_tokens_str:
            try:
                # Format: token1:user1:perm1,perm2;token2:user2:perm3
                for token_config in custom_tokens_str.split(';'):
                    if ':' in token_config:
                        token, config = token_config.split(':', 1)
                        user_config = config.split(':', 1)
                        
                        # Parse permissions
                        if len(user_config) > 1:
                            user, perms = user_config[0], user_config[1]
                        else:
                            user = user_config[0]
                            perms = ['read']  # Default permissions
                        
                        custom_tokens[token] = {
                            'user': user,
                            'permissions': perms.split(','),
                            'expires': None  # Never expires for simple tokens
                        }
            except Exception as e:
                print(f"DEBUG: Error parsing custom tokens: {e}")
                custom_tokens = {}
        
        # Generate JWT token for admin user (for testing)
        admin_jwt_token = self._generate_admin_jwt_token()
        
        # Add JWT token to valid tokens
        valid_tokens = default_tokens.copy()
        valid_tokens.update(custom_tokens)
        valid_tokens[admin_jwt_token] = {
            'user': 'admin',
            'permissions': ['read', 'write', 'admin'],
            'expires': time.time() + self.token_expiry  # Will expire based on token_expiry setting
        }
        
        print(f"DEBUG: Loaded {len(valid_tokens)} valid tokens including admin JWT")
        return valid_tokens
    
    def _generate_session_token(self):
        """Generate a new session token with expiry."""
        try:
            import jwt
            import time
            
            # JWT payload for session
            payload = {
                'username': 'user',
                'userId': 'session-user',
                'permissions': ['read', 'write'],
                'iat': int(time.time()),  # Issued at
                'exp': int(time.time()) + self.token_expiry,  # Expires at
                'iss': 'DASH EMBEDDED',  # Issuer
                'aud': 'energyintel-dash-app',  # Audience
                'session_id': f"session_{int(time.time())}"  # Unique session ID
            }
            
            # Generate JWT token
            token = jwt.encode(
                payload,
                self.jwt_secret,
                algorithm='HS512'
            )
            
            # Store token in valid tokens with expiry
            self.valid_tokens[token] = {
                'user': 'user',
                'permissions': ['read', 'write'],
                'expires': time.time() + self.token_expiry
            }
            
            print(f"DEBUG: Generated session token (expires in {self.token_expiry//60} minutes)")
            return token
            
        except Exception as e:
            print(f"DEBUG: Error generating session token: {e}")
            return None
    
    def _generate_admin_jwt_token(self):
        """Generate a JWT token for admin user."""
        try:
            import jwt
            import time
            
            # JWT payload
            payload = {
                'username': 'admin',
                'userId': 'admin',
                'permissions': ['read', 'write', 'admin'],
                'iat': int(time.time()),  # Issued at
                'exp': int(time.time()) + self.token_expiry,  # Expires at
                'iss': 'DASH EMBEDDED',  # Issuer
                'aud': 'energyintel-dash-app'  # Audience
            }
            
            # Generate JWT token
            token = jwt.encode(
                payload,
                self.jwt_secret,
                algorithm='HS512'
            )
            
            print(f"DEBUG: Generated admin JWT token (expires in {self.token_expiry//60} minutes)")
            return token
            
        except Exception as e:
            print(f"DEBUG: Error generating JWT token: {e}")
            return None
    
    def _base64_url_decode(self, data):
        """Decode base64url encoded data."""
        # Add padding if needed
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
        
        # Replace URL-safe characters
        data = data.replace('-', '+').replace('_', '/')
        
        try:
            return base64.b64decode(data)
        except Exception:
            return None
    
    def _verify_jwt_signature(self, token_parts, secret):
        """Verify JWT signature using HMAC SHA-512."""
        if len(token_parts) != 3:
            return False
        
        header_b64, payload_b64, signature_b64 = token_parts
        
        # Create the data to sign
        data = f"{header_b64}.{payload_b64}"
        
        try:
            # Create HMAC SHA-512 signature
            signature = hmac.new(
                secret.encode('utf-8'),
                data.encode('utf-8'),
                hashlib.sha512
            ).digest()
            
            # Encode signature as base64url
            expected_signature = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')
            
            # Compare signatures
            return hmac.compare_digest(signature_b64, expected_signature)
        except Exception as e:
            print(f"JWT signature verification error: {e}")
            return False
    
    def _validate_jwt_token(self, token):
        """Validate JWT token and extract payload."""
        try:
            # Split token into parts
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            header_b64, payload_b64, signature_b64 = parts
            
            # Decode header
            header_data = self._base64_url_decode(header_b64)
            if not header_data:
                return None
            
            header = json.loads(header_data.decode('utf-8'))
            
            # Check algorithm
            if header.get('alg') != 'HS512':
                print(f"Unsupported JWT algorithm: {header.get('alg')}")
                return None
            
            # Verify signature
            if not self._verify_jwt_signature(parts, self.jwt_secret):
                print("JWT signature verification failed")
                return None
            
            # Decode payload
            payload_data = self._base64_url_decode(payload_b64)
            if not payload_data:
                return None
            
            payload = json.loads(payload_data.decode('utf-8'))
            
            # Check expiration with better logging
            if 'exp' in payload:
                exp_time = payload['exp']
                current_time = time.time()
                
                # For testing, remove buffer to test exact expiry
                # buffer_time = 300  # 5 minutes
                buffer_time = 0  # No buffer for testing
                if current_time > (exp_time + buffer_time):
                    print(f"JWT token expired. Current: {current_time}, Expired: {exp_time}, Buffer: {buffer_time}")
                    return None
                else:
                    # Log token is still valid
                    time_remaining = exp_time - current_time
                    print(f"JWT token valid. Time remaining: {time_remaining:.0f} seconds")
            
            # Return user info based on JWT payload
            return {
                'user': payload.get('username', payload.get('userId', 'jwt_user')),
                'permissions': ['read', 'write'],  # Default permissions for JWT users
                'expires': payload.get('exp'),
                'jwt_payload': payload
            }
            
        except Exception as e:
            print(f"JWT validation error: {e}")
            return None
    
    def _check_token_auth(self):
        """Check token authentication before serving pages."""
        print(f"DEBUG: _check_token_auth called for path: {request.path}")
        
        # Skip authentication for OPTIONS requests (CORS preflight) - this must be first
        if request.method == 'OPTIONS':
            print("DEBUG: Skipping auth for OPTIONS request")
            return
        
        # Skip auth for static assets, dash internal routes, and health checks
        # We use a broad check to ensure Dash internal AJAX doesn't get blocked
        path = request.path.lower()
        whitelist = [
            # '/_dash-',
            '/_dash-layout',
            '/_dash-dependencies', 
            '/_dash-component-suites/',
            '/_dash-update-component',
            '_reload-hash',
            '/assets/', 
            '/_favicon.ico', 
            '/static/',
            '/health',
            '/_resources'  # Add _resources endpoint to whitelist
        ]
        
        if any(x in path for x in whitelist):
            print(f"DEBUG: Path {path} is whitelisted, skipping auth")
            return
        
        # NEW: Allow initial page load without authentication
        # Check if this is an initial page load (no cookies, no localStorage, no session)
        if self._is_initial_page_load():
            print("DEBUG: Initial page load detected, creating new token")
            # Generate new token for this session
            new_token = self._generate_session_token()
            if new_token:
                # Set the new token to be used for this request
                g.session_token = new_token
                g.is_initial_load = True
                # Set cookie for future requests
                g.set_auth_cookie = new_token
                print(f"DEBUG: Created new session token: {new_token[:20]}...")
            return
        
        # For subsequent requests, check authentication
        print("DEBUG: Subsequent request, checking authentication...")
        
        # Get all potential tokens from various sources
        print("DEBUG: Extracting tokens from request...")
        potential_tokens = self._extract_tokens()
        print(f"DEBUG: Found {len(potential_tokens)} potential tokens")
        
        token_info = None
        valid_token = None
        
        # Try each token found until one works
        for i, token in enumerate(potential_tokens):
            print(f"DEBUG: Trying token {i+1}: {token[:20]}...")
            # Try JWT validation
            token_info = self._validate_jwt_token(token)
            if not token_info:
                # Fallback to simple tokens (admin-token-123 etc)
                token_info = self._validate_simple_token(token)
            
            if token_info:
                print(f"DEBUG: Token {i+1} is valid!")
                valid_token = token
                break
            else:
                print(f"DEBUG: Token {i+1} is invalid")
        
        if not token_info:
            print("DEBUG: No valid token found, returning auth error")
            return self._auth_error("Invalid or expired token")
        
        # Store user info in Flask's g object for use in callbacks
        g.current_user = token_info['user']
        g.user_permissions = token_info['permissions']
        g.token = valid_token
        g.jwt_payload = token_info.get('jwt_payload')
        
        # If token was provided in query string, flag it to be set as cookie
        if request.args.get('token'):
            g.set_auth_cookie = token
    
    def _is_initial_page_load(self):
        """Check if this is an initial page load or a returning user."""
        # Check for existing authentication indicators
        has_cookies = False
        has_url_token = False
        
        # Check for existing cookies
        cookies = request.cookies
        if cookies and cookies.get('auth_token'):
            has_cookies = True
            print(f"DEBUG: Found existing auth_token cookie")
        
        # Check for URL token
        if request.args.get('token') or request.args.get('auth_token'):
            has_url_token = True
            print(f"DEBUG: Found URL token parameter")
        
        # Check for Authorization header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            print(f"DEBUG: Found Authorization header")
            return False  # This is a subsequent request with token
        
        # Initial load = no existing auth indicators
        is_initial = not has_cookies and not has_url_token
        
        if is_initial:
            print("DEBUG: No auth indicators found, treating as initial page load")
        else:
            print("DEBUG: Found existing auth indicators, treating as subsequent request")
            
        return is_initial
            
    def _set_auth_cookie(self, response):
        """Set authentication cookie if a token was provided in the request."""
        if hasattr(g, 'set_auth_cookie'):
            # Set cookie for 15 minutes (matching token expiry for testing)
            response.set_cookie(
                'auth_token', 
                g.set_auth_cookie,
                max_age=15 * 60,  # 15 minutes for testing
                httponly=True,
                samesite='None', # Required for cross-site iframes
                secure=True      # Required when samesite=None
            )
        
        # NEW: Inject auth overlay if needed
        if hasattr(g, 'show_auth_overlay') and g.show_auth_overlay:
            print("DEBUG: Injecting auth overlay into Dash app response")
            self._inject_auth_overlay(response)
        
        # Add CORS headers for authentication responses (only if not already set)
        origin = None
        request_origin = request.headers.get('Origin')
        allowed_origins = [
            'https://www.energyintel.com',
            'https://energyintel.com'
            # 'http://localhost:3000',
            # 'http://localhost:8080'
        ]
        
        if request_origin and request_origin in allowed_origins:
            origin = request_origin
        elif request_origin and any(request_origin.endswith(domain) for domain in ['.energyintel.com']):
            origin = request_origin
        
        if origin:
            # Check if CORS header already exists to avoid duplication
            existing_origin = response.headers.get('Access-Control-Allow-Origin')
            if not existing_origin:
                response.headers.add('Access-Control-Allow-Origin', origin)
            elif existing_origin != origin:
                # Replace with the correct origin if different
                response.headers['Access-Control-Allow-Origin'] = origin
            
            # Add other CORS headers only if not already present
            if not response.headers.get('Access-Control-Allow-Credentials'):
                response.headers.add('Access-Control-Allow-Credentials', 'true')
            if not response.headers.get('Vary'):
                response.headers.add('Vary', 'Origin')
        
        return response
    
    def _extract_tokens(self):
        """Extract all potential tokens from request sources."""
        tokens = []
        
        # 1. Check query parameter FIRST (explicit user intent)
        query_token = request.args.get('token')
        if query_token:
            tokens.append(query_token)
            
        # 2. Check Authorization header (Bearer token)
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            tokens.append(auth_header[7:])
        
        # 3. Check X-API-Token header
        api_token = request.headers.get('X-API-Token')
        if api_token:
            tokens.append(api_token)
        
        # 4. Check cookies
        for cookie_name in ['auth_token', 'kcToken', 'pelcro.user.auth.token']:
            t = request.cookies.get(cookie_name)
            if t:
                tokens.append(t)
        
        # 5. Check for default token in environment
        default_token = os.environ.get('DEFAULT_AUTH_TOKEN')
        if default_token:
            tokens.append(default_token)
            
        return tokens
    
    def _validate_simple_token(self, token):
        """Validate simple string tokens (fallback method)."""
        if token in self.valid_tokens:
            token_info = self.valid_tokens[token]
            
            # Check expiry if set
            if token_info.get('expires'):
                if time.time() > token_info['expires']:
                    return None  # Token expired
            
            return token_info
        
        return None
    
    def _auth_error(self, message):
        """Return authentication error response."""
        if request.path.startswith('/api/') or request.is_json:
            # For API requests, return JSON error with token refresh info
            error_response = {
                'error': 'Authentication required',
                'message': message,
                'auth_methods': [
                    'Authorization: Bearer <jwt-token>',
                    'X-API-Token: <token>',
                    '?token=<token>',
                    'Cookie: auth_token=<token>'
                ],
                'token_refresh_required': True  # Indicate token refresh is needed
            }
            return jsonify(error_response), 401
        else:
            # For web requests, check if this is an initial page load or subsequent request
            is_initial_load = getattr(g, 'is_initial_load', False)
            
            if is_initial_load:
                print("DEBUG: Initial page load with auth error, allowing Dash app to load normally")
                # For initial loads, let the Dash app load normally
                # Don't interfere with the normal Dash rendering process
                # The JavaScript will handle showing overlay if needed
                return None  # Let the normal Dash app handle the response
            else:
                print("DEBUG: Subsequent request with auth error, injecting overlay into Dash app")
                # For subsequent requests, we need to inject the overlay into the Dash app response
                # This will be handled by the after_request hook
                g.show_auth_overlay = True
                return None  # Let the normal Dash app handle the response
    
    def _get_page_content_with_auth_check(self):
        """Return the actual page content with JavaScript auth checking."""
        # This should return the actual Dash app layout
        # We'll inject JavaScript to handle authentication checking
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Energy Intelligence - Authentication Check</title>
            <style>
                body { margin: 0; padding: 0; font-family: Arial, sans-serif; }
                .auth-overlay.hidden { display: none; }
            </style>
        </head>
        <body>
            <!-- The actual Dash app content will be loaded here -->
            <div id="react-root">
                <div style="text-align: center; padding: 50px; color: #666;">
                    <p>Loading Energy Intelligence Dashboard...</p>
                </div>
            </div>
            
            <!-- Authentication Overlay (hidden by default) -->
            <div id="auth-overlay" class="auth-overlay hidden">
                <div class="auth-modal">
                    <div class="auth-icon">🔐</div>
                    <div class="auth-title">Lost Connection to Dash App</div>
                    <div class="auth-message">
                        Reconnect now to keep your filters and any changes.
                    </div>
                    <button onclick="handleReconnect()" class="reconnect-btn">
                        🔄 Reconnect
                    </button>
                </div>
            </div>
            
            <script>
                // Check authentication after page loads
                window.addEventListener('load', function() {{
                    console.log('Page loaded, checking authentication...');
                    
                    // Check if we have valid authentication
                    const hasValidAuth = checkForValidToken();
                    
                    if (!hasValidAuth) {{
                        console.log('No valid authentication, showing overlay');
                        document.getElementById('auth-overlay').classList.remove('hidden');
                    }} else {{
                        console.log('Valid authentication found, loading app normally');
                        // Load the actual Dash app
                        loadDashApp();
                    }}
                }});
                
                function checkForValidToken() {{
                    // Check URL parameters
                    const urlParams = new URLSearchParams(window.location.search);
                    if (urlParams.get('token') || urlParams.get('auth_token')) {{
                        return true;
                    }}
                    
                    // Check cookies
                    const cookies = document.cookie.split(';');
                    for (let cookie of cookies) {{
                        const [name, value] = cookie.trim().split('=');
                        if (name === 'pelcro.user.auth.token' && value) {{
                            return true;
                        }}
                    }}
                    
                    // Check localStorage
                    if (typeof localStorage !== 'undefined') {{
                        if (localStorage.getItem('auth_token') || localStorage.getItem('jwt_token')) {{
                            return true;
                        }}
                    }}
                    
                    return false;
                }}
                
                function loadDashApp() {{
                    // Load the actual Dash application
                    // This would typically be handled by Dash's normal loading process
                    console.log('Loading Dash application...');
                    // The Dash app should already be loading via normal mechanisms
                }}
                
                function handleReconnect() {{
                    console.log('Starting token refresh process...');
                    
                    // Show loading state
                    const button = document.querySelector('.reconnect-btn');
                    button.innerHTML = '🔄 Reconnecting...';
                    button.disabled = true;
                    
                    // Clear all authentication data
                    clearAllAuthData();
                    
                    // Attempt token refresh
                    refreshTokenAndReload();
                }}
                
                function clearAllAuthData() {{
                    console.log('Clearing authentication data...');
                    
                    // Clear localStorage
                    if (typeof localStorage !== 'undefined') {{
                        localStorage.removeItem('auth_token');
                        localStorage.removeItem('user_token');
                        localStorage.removeItem('jwt_token');
                        localStorage.removeItem('dash_auth_token');
                    }}
                    
                    // Clear sessionStorage
                    if (typeof sessionStorage !== 'undefined') {{
                        sessionStorage.removeItem('auth_token');
                        sessionStorage.removeItem('user_token');
                        sessionStorage.removeItem('jwt_token');
                        sessionStorage.removeItem('dash_auth_token');
                    }}
                    
                    // Clear cookies
                    document.cookie.split(";").forEach(function(c) {{ 
                        const cookieName = c.split("=")[0].trim();
                        if (cookieName) {{
                            document.cookie = cookieName + "=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/";
                        }}
                    }});
                }}
                
                function refreshTokenAndReload() {{
                    console.log('Attempting to refresh token...');
                    
                    // Get current URL without token parameters
                    const url = new URL(window.location.href);
                    url.searchParams.delete('token');
                    url.searchParams.delete('auth_token');
                    url.searchParams.delete('jwt_token');
                    
                    // Reload with clean URL
                    window.location.href = url.toString();
                }}
            </script>
            
            <!-- Add overlay styles -->
            <style>
                .auth-overlay {{
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0, 0, 0, 0.7);
                    z-index: 9999;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    backdrop-filter: blur(5px);
                }}
                
                .auth-modal {{
                    background: white;
                    padding: 30px;
                    border-radius: 12px;
                    max-width: 500px;
                    width: 90%;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                    text-align: center;
                }}
                
                .auth-icon {{ font-size: 48px; margin-bottom: 20px; color: #dc3545; }}
                .auth-title {{ font-size: 24px; font-weight: bold; margin-bottom: 15px; color: #333; }}
                .auth-message {{ font-size: 16px; color: #666; margin-bottom: 25px; line-height: 1.5; }}
                .reconnect-btn {{ 
                    display: inline-block; 
                    background-color: #007bff; 
                    color: white; 
                    padding: 12px 30px; 
                    text-decoration: none; 
                    border-radius: 6px; 
                    font-weight: bold; 
                    font-size: 16px;
                    transition: all 0.3s ease;
                    border: none;
                    cursor: pointer;
                }}
                
                .reconnect-btn:hover {{ 
                    background-color: #0056b3; 
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(0, 123, 255, 0.3);
                }}
            </style>
        </body>
        </html>
        ''', 200  # Return 200 OK to allow page to load
    
    def _get_page_content_with_overlay(self, message):
        """Return the page content with overlay shown on top."""
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Energy Intelligence - Token Refresh Required</title>
            <style>
                body {{ 
                    margin: 0; 
                    padding: 0; 
                    font-family: Arial, sans-serif; 
                }}
                
                /* Overlay styles */
                .auth-overlay {{
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0, 0, 0, 0.7);
                    z-index: 9999;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    backdrop-filter: blur(5px);
                }}
                
                .auth-modal {{
                    background: white;
                    padding: 30px;
                    border-radius: 12px;
                    max-width: 500px;
                    width: 90%;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                    text-align: center;
                }}
                
                .auth-icon {{
                    font-size: 48px;
                    margin-bottom: 20px;
                    color: #dc3545;
                }}
                
                .auth-title {{
                    font-size: 24px;
                    font-weight: bold;
                    margin-bottom: 15px;
                    color: #333;
                }}
                
                .auth-message {{
                    font-size: 16px;
                    color: #666;
                    margin-bottom: 25px;
                    line-height: 1.5;
                }}
                
                .reconnect-btn {{ 
                    display: inline-block; 
                    background-color: #007bff; 
                    color: white; 
                    padding: 12px 30px; 
                    text-decoration: none; 
                    border-radius: 6px; 
                    font-weight: bold; 
                    font-size: 16px;
                    transition: all 0.3s ease;
                    border: none;
                    cursor: pointer;
                }}
                
                .reconnect-btn:hover {{ 
                    background-color: #0056b3; 
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(0, 123, 255, 0.3);
                }}
                
                .auth-details {{
                    margin-top: 20px;
                    padding: 15px;
                    background: #f8f9fa;
                    border-radius: 6px;
                    font-size: 14px;
                    color: #6c757d;
                }}
            </style>
        </head>
        <body>
            <!-- Main page content will be here -->
            <div id="main-content">
                <!-- The actual Dash app content should be loaded here -->
                <div style="text-align: center; padding: 50px; color: #666;">
                    <p>Loading Energy Intelligence Dashboard...</p>
                </div>
            </div>
            
            <!-- Authentication Overlay -->
            <div id="auth-overlay" class="auth-overlay">
                <div class="auth-modal">
                    <div class="auth-icon">🔐</div>
                    <div class="auth-title">Lost Connection to Dash App</div>
                    <div class="auth-message">
                        Reconnect now to keep your filters and any changes.
                    </div>
                    <button onclick="handleReconnect()" class="reconnect-btn">
                        🔄 Reconnect
                    </button>
                    <div class="auth-details">
                        Your session has expired. Clicking Reconnect will refresh your authentication 
                        while preserving your current page state and filters.
                    </div>
                </div>
            </div>
            
            <script>
                // Token refresh and reconnection logic
                function handleReconnect() {{
                    console.log('Starting token refresh process...');
                    
                    // Show loading state
                    const button = document.querySelector('.reconnect-btn');
                    const originalText = button.innerHTML;
                    button.innerHTML = '🔄 Reconnecting...';
                    button.disabled = true;
                    
                    // Clear all authentication data
                    clearAllAuthData();
                    
                    // Attempt token refresh
                    refreshTokenAndReload();
                }}
                
                function clearAllAuthData() {{
                    console.log('Clearing authentication data...');
                    
                    // Clear localStorage
                    if (typeof localStorage !== 'undefined') {{
                        localStorage.removeItem('auth_token');
                        localStorage.removeItem('user_token');
                        localStorage.removeItem('jwt_token');
                        localStorage.removeItem('dash_auth_token');
                    }}
                    
                    // Clear sessionStorage
                    if (typeof sessionStorage !== 'undefined') {{
                        sessionStorage.removeItem('auth_token');
                        sessionStorage.removeItem('user_token');
                        sessionStorage.removeItem('jwt_token');
                        sessionStorage.removeItem('dash_auth_token');
                    }}
                    
                    // Clear cookies
                    clearAllCookies();
                }}
                
                function clearAllCookies() {{
                    const cookiesToClear = [
                        'pelcro.unique.id',
                        'pelcro_first_touch_utm_source', 
                        '_gid',
                        '_ga',
                        'twk_uuid_6137215f649e0a0a5cd4fb0f',
                        'pelcro.user.auth.token',
                        '_ga_19TPJV33X4',
                        'auth_token',
                        'dash_auth_token'
                    ];
                    
                    cookiesToClear.forEach(function(name) {{
                        document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;domain=.energyintel.com";
                        document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/";
                        document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;domain=energyintel.com";
                    }});
                    
                    // Clear all remaining cookies
                    document.cookie.split(";").forEach(function(c) {{ 
                        const cookieName = c.split("=")[0].trim();
                        if (cookieName) {{
                            document.cookie = cookieName + "=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;domain=.energyintel.com";
                            document.cookie = cookieName + "=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/";
                            document.cookie = cookieName + "=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;domain=energyintel.com";
                        }}
                    }});
                }}
                
                function refreshTokenAndReload() {{
                    console.log('Attempting to refresh token...');
                    
                    // Get current URL without token parameters
                    const url = new URL(window.location.href);
                    url.searchParams.delete('token');
                    url.searchParams.delete('auth_token');
                    url.searchParams.delete('jwt_token');
                    
                    // Try to get new token from parent window (for embedded apps)
                    if (window.parent && window.parent !== window) {{
                        console.log('Attempting to get token from parent window...');
                        // Post message to parent requesting new token
                        window.parent.postMessage({{
                            type: 'REQUEST_TOKEN_REFRESH',
                            origin: window.location.origin
                        }}, '*');
                        
                        // Wait for token response
                        window.addEventListener('message', function(event) {{
                            if (event.data.type === 'TOKEN_REFRESH_RESPONSE') {{
                                if (event.data.token) {{
                                    console.log('Received new token from parent');
                                    url.searchParams.set('token', event.data.token);
                                }}
                                // Reload with new token (or without if none provided)
                                window.location.href = url.toString();
                            }}
                        }});
                        
                        // Fallback: reload after 3 seconds if no response
                        setTimeout(function() {{
                            console.log('No token response from parent, reloading...');
                            window.location.href = url.toString();
                        }}, 3000);
                    }} else {{
                        // Not embedded, just reload clean
                        console.log('Not embedded, reloading clean URL...');
                        window.location.href = url.toString();
                    }}
                }}
                
                // Auto-hide overlay if page loads successfully
                window.addEventListener('load', function() {{
                    console.log('Page loaded, checking authentication state...');
                    
                    // Check if this is an initial page load
                    const isInitialLoad = !checkForExistingAuth();
                    console.log('Is initial load:', isInitialLoad);
                    
                    if (isInitialLoad) {{
                        console.log('Initial page load detected, hiding overlay');
                        document.getElementById('auth-overlay').classList.add('hidden');
                        return;
                    }}
                    
                    // For subsequent loads, check for valid token
                    const hasToken = checkForValidToken();
                    if (hasToken) {{
                        console.log('Valid token found, hiding overlay');
                        document.getElementById('auth-overlay').classList.add('hidden');
                    }} else {{
                        console.log('No valid token found, showing overlay');
                        document.getElementById('auth-overlay').classList.remove('hidden');
                    }}
                }});
                
                function checkForExistingAuth() {{
                    // Check if there are any existing authentication indicators
                    // This helps determine if it's an initial page load or subsequent request
                    
                    // Check cookies
                    const cookies = document.cookie.split(';');
                    for (let cookie of cookies) {{
                        const [name, value] = cookie.trim().split('=');
                        if (['pelcro.user.auth.token', 'auth_token', 'kcToken'].includes(name) && value) {{
                            return true;
                        }}
                    }}
                    
                    // Check localStorage
                    if (typeof localStorage !== 'undefined') {{
                        if (localStorage.getItem('auth_token') || localStorage.getItem('jwt_token')) {{
                            return true;
                        }}
                    }}
                    
                    // Check sessionStorage
                    if (typeof sessionStorage !== 'undefined') {{
                        if (sessionStorage.getItem('auth_token') || sessionStorage.getItem('jwt_token')) {{
                            return true;
                        }}
                    }}
                    
                    // Check URL parameters
                    const urlParams = new URLSearchParams(window.location.search);
                    if (urlParams.get('token') || urlParams.get('auth_token') || urlParams.get('jwt_token')) {{
                        return true;
                    }}
                    
                    return false;
                }}
                
                function checkForValidToken() {{
                    // Check URL parameters
                    const urlParams = new URLSearchParams(window.location.search);
                    if (urlParams.get('token') || urlParams.get('auth_token')) {{
                        return true;
                    }}
                    
                    // Check cookies
                    const cookies = document.cookie.split(';');
                    for (let cookie of cookies) {{
                        const [name, value] = cookie.trim().split('=');
                        if (name === 'pelcro.user.auth.token' && value) {{
                            return true;
                        }}
                    }}
                    
                    // Check localStorage
                    if (typeof localStorage !== 'undefined') {{
                        if (localStorage.getItem('auth_token') || localStorage.getItem('jwt_token')) {{
                            return true;
                        }}
                    }}
                    
                    return false;
                }}
            </script>
        </body>
        </html>
        ''', 401
    
    def get_current_user(self):
        """Get the current authenticated user."""
        return getattr(g, 'current_user', None)
    
    def get_user_permissions(self):
        """Get permissions for the current user."""
        return getattr(g, 'user_permissions', [])
    
    def get_jwt_payload(self):
        """Get JWT payload if authenticated via JWT."""
        return getattr(g, 'jwt_payload', None)
    
    def has_permission(self, permission):
        """Check if current user has a specific permission."""
        permissions = self.get_user_permissions()
        return permission in permissions or 'admin' in permissions
    
    def require_permission(self, permission):
        """Decorator to require a specific permission."""
        def decorator(f):
            @functools.wraps(f)
            def decorated_function(*args, **kwargs):
                if not self.has_permission(permission):
                    return jsonify({'error': f'Permission required: {permission}'}), 403
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def generate_token(self, user, permissions, expires_in_hours=None):
        """Generate a new token for a user (utility method)."""
        import secrets
        import string
        
        # Generate a secure random token
        alphabet = string.ascii_letters + string.digits
        token = ''.join(secrets.choice(alphabet) for _ in range(32))
        
        # Calculate expiry if specified
        expires = None
        if expires_in_hours:
            expires = time.time() + (expires_in_hours * 3600)
        
        # Add to valid tokens
        self.valid_tokens[token] = {
            'user': user,
            'permissions': permissions,
            'expires': expires
        }
        
        return token
    
    def _inject_auth_overlay(self, response):
        """Inject the authentication overlay into the Dash app response."""
        if response.status_code != 200:
            return
        
        # Only inject into HTML responses
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' not in content_type:
            return
        
        try:
            # Get the response content
            content = response.get_data(as_text=True)
            
            # Check if it's a Dash app response
            if 'react-root' in content or 'Dash' in content:
                # Inject the overlay HTML and JavaScript
                overlay_html = self._get_overlay_html()
                overlay_js = self._get_overlay_javascript()
                
                # Insert the overlay before the closing body tag
                if '</body>' in content:
                    content = content.replace('</body>', overlay_html + '</body>')
                
                # Insert the JavaScript before the closing body tag (after overlay)
                if '</body>' in content:
                    content = content.replace('</body>', overlay_js + '</body>')
                
                # Update the response
                response.set_data(content)
                response.headers['Content-Length'] = len(content.encode('utf-8'))
                
                print("DEBUG: Successfully injected auth overlay into Dash app response")
            else:
                print("DEBUG: Not a Dash app response, skipping overlay injection")
                
        except Exception as e:
            print(f"DEBUG: Error injecting overlay: {e}")
    
    def _get_overlay_html(self):
        """Get the overlay HTML to inject."""
        return '''
        <!-- Reconnect Popup Modal -->
        <div id="reconnect-modal" class="reconnect-modal" style="display: none;">
            <div class="reconnect-backdrop"></div>
            <div class="reconnect-content">
                <div class="reconnect-header">
                    <div class="reconnect-icon">🔐</div>
                    <h3>Session Expired</h3>
                    <button class="reconnect-close" onclick="hideReconnectModal()">✕</button>
                </div>
                <div class="reconnect-body">
                    <p>Your session has expired. Please reconnect to continue using the dashboard.</p>
                    <p class="reconnect-subtitle">Reconnecting will preserve your current filters and page state.</p>
                </div>
                <div class="reconnect-footer">
                    <button class="reconnect-btn-primary" onclick="handleReconnect()">
                        🔄 Reconnect Now
                    </button>
                    <button class="reconnect-btn-secondary" onclick="hideReconnectModal()">
                        Dismiss
                    </button>
                </div>
            </div>
        </div>
        
        <!-- Toast Container -->
        <div id="toast-container" class="toast-container"></div>
        '''
    
    def _get_overlay_javascript(self):
        """Get the overlay JavaScript to inject."""
        return '''
        <script>
        // Authentication toast and reconnect modal functionality
        (function() {
            console.log('Initializing auth toast and reconnect modal...');
            
            // Toast management using dash-bootstrap-components approach
            function showToast(message, type = 'warning', duration = 5000) {{
                const container = document.getElementById('toast-container');
                if (!container) return;
                
                // Create toast element similar to dbc.Toast
                const toastId = 'toast-' + Date.now();
                const toast = document.createElement('div');
                toast.id = toastId;
                toast.className = 'toast show';
                toast.setAttribute('role', 'alert');
                toast.setAttribute('aria-live', 'assertive');
                toast.setAttribute('aria-atomic', 'true');
                
                // Set styles similar to dbc.Toast
                toast.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 9999;
                    min-width: 350px;
                    max-width: 400px;
                    background: white;
                    border-radius: 0.375rem;
                    box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
                    border-left: 4px solid ${{getBorderColor(type)}};
                    opacity: 0;
                    transform: translateX(100%);
                    transition: all 0.3s ease;
                `;
                
                // Get icon based on type
                const icon = getToastIcon(type);
                
                toast.innerHTML = `
                    <div class="toast-header" style="
                        display: flex;
                        align-items: center;
                        padding: 0.75rem 0.75rem 0.5rem;
                        border-bottom: 1px solid rgba(0, 0, 0, 0.05);
                        background: rgba(0, 0, 0, 0.03);
                    ">
                        <strong class="me-auto" style="
                            color: ${{getTextColor(type)}};
                            font-size: 0.875rem;
                        ">${{getToastTitle(type)}}</strong>
                        <small style="color: #6c757d; font-size: 0.75rem;">just now</small>
                        <button type="button" class="btn-close" onclick="hideToast('${{toastId}}')" style="
                            background: none;
                            border: none;
                            font-size: 1.25rem;
                            color: #000;
                            opacity: 0.5;
                            cursor: pointer;
                            padding: 0;
                            margin-left: 0.75rem;
                        ">×</button>
                    </div>
                    <div class="toast-body" style="
                        padding: 0.75rem;
                        color: #333;
                        font-size: 0.875rem;
                    ">
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="font-size: 1.25rem;">${{icon}}</span>
                            <span>${{message}}</span>
                        </div>
                    </div>
                `;
                
                container.appendChild(toast);
                
                // Animate in
                setTimeout(() => {{
                    toast.style.opacity = '1';
                    toast.style.transform = 'translateX(0)';
                }}, 100);
                
                // Auto-hide after duration
                if (duration > 0) {{
                    setTimeout(() => {{
                        hideToast(toastId);
                    }}, duration);
                }}
                
                return toastId;
            }}
            
            function getToastIcon(type) {{
                const icons = {{
                    'warning': '⚠️',
                    'danger': '❌',
                    'success': '✅',
                    'info': 'ℹ️',
                    'primary': '🔐'
                }};
                return icons[type] || icons.info;
            }}
            
            function getToastTitle(type) {{
                const titles = {{
                    'warning': 'Warning',
                    'danger': 'Error',
                    'success': 'Success',
                    'info': 'Info',
                    'primary': 'Authentication'
                }};
                return titles[type] || titles.info;
            }}
            
            function getBorderColor(type) {{
                const colors = {{
                    'warning': '#ffc107',
                    'danger': '#dc3545',
                    'success': '#28a745',
                    'info': '#007bff',
                    'primary': '#007bff'
                }};
                return colors[type] || colors.info;
            }}
            
            function getTextColor(type) {{
                const colors = {{
                    'warning': '#856404',
                    'danger': '#721c24',
                    'success': '#155724',
                    'info': '#0c5460',
                    'primary': '#004085'
                }};
                return colors[type] || colors.info;
            }}
            
            function hideToast(toastId) {{
                const toast = document.getElementById(toastId);
                if (toast) {{
                    toast.style.opacity = '0';
                    toast.style.transform = 'translateX(100%)';
                    
                    setTimeout(() => {{
                        if (toast.parentElement) {{
                            toast.parentElement.removeChild(toast);
                        }}
                    }}, 300);
                }}
            }}
            
            // Check if we need to show reconnect modal
            function checkAuthAndShowModal() {{
                console.log('Checking authentication state...');
                
                // Check if this is an initial page load
                const isInitialLoad = !checkForExistingAuth();
                console.log('Is initial load:', isInitialLoad);
                
                if (isInitialLoad) {{
                    console.log('Initial page load detected, hiding modal');
                    hideReconnectModal();
                    return;
                }}
                
                // For subsequent loads, check for valid token
                const hasToken = checkForValidToken();
                if (hasToken) {{
                    console.log('Valid token found, hiding modal');
                    hideReconnectModal();
                }} else {{
                    console.log('No valid token found, showing modal and toast');
                    showReconnectModal();
                    showToast('Session expired. Please reconnect to continue.', 'warning', 8000);
                }}
            }}
            
            function showReconnectModal() {{
                const modal = document.getElementById('reconnect-modal');
                if (modal) {{
                    modal.style.display = 'flex';
                    modal.style.opacity = '0';
                    
                    // Animate in
                    setTimeout(() => {{
                        modal.style.transition = 'all 0.3s ease';
                        modal.style.opacity = '1';
                    }}, 100);
                    
                    console.log('Reconnect modal shown');
                }}
            }}
            
            function hideReconnectModal() {{
                const modal = document.getElementById('reconnect-modal');
                if (modal) {{
                    modal.style.transition = 'all 0.3s ease';
                    modal.style.opacity = '0';
                    
                    setTimeout(() => {{
                        modal.style.display = 'none';
                    }}, 300);
                    
                    console.log('Reconnect modal hidden');
                }}
            }}
            
            // Monitor for token expiry during active session
            function monitorTokenExpiry() {{
                console.log('Starting token expiry monitoring...');
                
                // Check every 30 seconds
                setInterval(() => {{
                    const hasValidToken = checkForValidToken();
                    if (!hasValidToken) {{
                        console.log('Token expired during active session, showing modal and toast');
                        showReconnectModal();
                        showToast('Session expired. Please reconnect to continue.', 'warning', 8000);
                    }}
                }}, 30000);
                
                // Also check after any user interaction
                document.addEventListener('click', () => {{
                    setTimeout(() => {{
                        const hasValidToken = checkForValidToken();
                        if (!hasValidToken) {{
                            console.log('Token expired after user interaction, showing modal and toast');
                            showReconnectModal();
                            showToast('Session expired. Please reconnect to continue.', 'warning', 8000);
                        }}
                    }}, 1000);
                }});
                
                // Check after any API calls
                const originalFetch = window.fetch;
                window.fetch = function(...args) {{
                    return originalFetch.apply(this, args).then(response => {{
                        if (response.status === 401) {{
                            console.log('401 response detected, showing modal and toast');
                            showReconnectModal();
                            showToast('Session expired. Please reconnect to continue.', 'warning', 8000);
                        }}
                        return response;
                    }}).catch(error => {{
                        console.log('Fetch error:', error);
                        return error;
                    }});
                }};
            }}
            
            function checkForExistingAuth() {{
                // Check if there are any existing authentication indicators
                const cookies = document.cookie.split(';');
                for (let cookie of cookies) {{
                    const [name, value] = cookie.trim().split('=');
                    if (['pelcro.user.auth.token', 'auth_token', 'kcToken'].includes(name) && value) {{
                        return true;
                    }}
                }}
                
                if (typeof localStorage !== 'undefined') {{
                    if (localStorage.getItem('auth_token') || localStorage.getItem('jwt_token')) {{
                        return true;
                    }}
                }}
                
                if (typeof sessionStorage !== 'undefined') {{
                    if (sessionStorage.getItem('auth_token') || sessionStorage.getItem('jwt_token')) {{
                        return true;
                    }}
                }}
                
                const urlParams = new URLSearchParams(window.location.search);
                if (urlParams.get('token') || urlParams.get('auth_token') || urlParams.get('jwt_token')) {{
                    return true;
                }}
                
                return false;
            }}
            
            function checkForValidToken() {{
                const urlParams = new URLSearchParams(window.location.search);
                if (urlParams.get('token') || urlParams.get('auth_token')) {{
                    return true;
                }}
                
                const cookies = document.cookie.split(';');
                for (let cookie of cookies) {{
                    const [name, value] = cookie.trim().split('=');
                    if (name === 'pelcro.user.auth.token' && value) {{
                        return true;
                    }}
                }}
                
                if (typeof localStorage !== 'undefined') {{
                    if (localStorage.getItem('auth_token') || localStorage.getItem('jwt_token')) {{
                        return true;
                    }}
                }}
                
                return false;
            }}
            
            function handleReconnect() {{
                console.log('Starting token refresh process...');
                
                const button = document.querySelector('.reconnect-btn');
                const originalText = button.innerHTML;
                button.innerHTML = '🔄 Reconnecting...';
                button.disabled = true;
                
                clearAllAuthData();
                generateNewTokenAndReload();
            }}
            
            function generateNewTokenAndReload() {{
                console.log('Generating new token...');
                
                // Make request to get new token
                fetch(window.location.href, {{
                    method: 'GET',
                    headers: {{
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache'
                    }}
                }})
                .then(response => {{
                    if (response.ok) {{
                        console.log('New token generated, reloading page...');
                        window.location.reload();
                    }} else {{
                        console.log('Failed to generate new token, reloading anyway...');
                        window.location.reload();
                    }}
                }})
                .catch(error => {{
                    console.log('Error generating token:', error);
                    window.location.reload();
                }});
            }}
            
                }}
                
                // Check cookies
                const cookies = document.cookie.split(';');
                for (let cookie of cookies) {{
                    const [name, value] = cookie.trim().split('=');
                    if (['pelcro.user.auth.token', 'auth_token', 'kcToken'].includes(name) && value) {{
                        // Simple validation - just check if token exists and is not empty
                        if (value && value.length > 10) {{
                            return true;
                        }}
                    }}
                }}
                
                return false;
            }}
            
            // Check auth when page loads
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', () => {{
                    checkAuthAndShowModal();
                    monitorTokenExpiry();
                }});
            }} else {{
                checkAuthAndShowModal();
                monitorTokenExpiry();
            }}
            
            // Also check after a short delay to handle dynamic content
            setTimeout(() => {{
                checkAuthAndShowModal();
                monitorTokenExpiry();
            }}, 1000);
            
            // Make functions globally available
            window.handleReconnect = handleReconnect;
            window.showReconnectModal = showReconnectModal;
            window.hideReconnectModal = hideReconnectModal;
            window.showToast = showToast;
            window.hideToast = hideToast;
            window.checkAuthAndShowModal = checkAuthAndShowModal;
        }})();
        </script>
        
        <style>
        /* Reconnect Modal Styles */
        .reconnect-modal {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: all 0.3s ease;
        }}
        
        .reconnect-backdrop {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(2px);
        }}
        
        .reconnect-content {{
            position: relative;
            background: white;
            border-radius: 12px;
            max-width: 450px;
            width: 90%;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
            transform: scale(0.9);
            transition: all 0.3s ease;
        }}
        
        .reconnect-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 24px 24px 16px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .reconnect-icon {{
            font-size: 32px;
            margin-right: 12px;
        }}
        
        .reconnect-header h3 {{
            margin: 0;
            font-size: 20px;
            font-weight: 600;
            color: #333;
            flex: 1;
        }}
        
        .reconnect-close {{
            background: none;
            border: none;
            font-size: 20px;
            color: #999;
            cursor: pointer;
            padding: 4px;
            border-radius: 4px;
            transition: all 0.2s ease;
        }}
        
        .reconnect-close:hover {{
            background: #f8f9fa;
            color: #666;
        }}
        
        .reconnect-body {{
            padding: 20px 24px;
            text-align: center;
        }}
        
        .reconnect-body p {{
            margin: 0 0 12px;
            color: #666;
            font-size: 16px;
            line-height: 1.5;
        }}
        
        .reconnect-subtitle {{
            font-size: 14px !important;
            color: #999 !important;
            margin-bottom: 0 !important;
        }}
        
        .reconnect-footer {{
            display: flex;
            gap: 12px;
            padding: 0 24px 24px;
            justify-content: center;
        }}
        
        .reconnect-btn-primary {{
            background-color: #007bff;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            min-width: 120px;
        }}
        
        .reconnect-btn-primary:hover {{
            background-color: #0056b3;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
        }}
        
        .reconnect-btn-secondary {{
            background: #6c757d;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            min-width: 120px;
        }}
        
        .reconnect-btn-secondary:hover {{
            background: #5a6268;
            transform: translateY(-1px);
        }}
        
        /* Toaster Widget Styles */
        .toaster-container {{
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
            pointer-events: none;
        }}
        
        .toaster-toast {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            padding: 16px;
            min-width: 300px;
            max-width: 400px;
            display: flex;
            align-items: center;
            gap: 12px;
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.3s ease;
            pointer-events: auto;
        }}
        
        .toaster-toast.show {{
            opacity: 1;
            transform: translateX(0);
        }}
        
        .toaster-toast.hide {{
            opacity: 0;
            transform: translateX(100%);
        }}
        
        .toaster-icon {{
            font-size: 20px;
            flex-shrink: 0;
        }}
        
        .toaster-message {{
            flex: 1;
            font-size: 14px;
            color: #333;
            line-height: 1.4;
        }}
        
        .toaster-close {{
            background: none;
            border: none;
            color: #999;
            font-size: 16px;
            cursor: pointer;
            padding: 2px;
            border-radius: 2px;
            transition: color 0.2s ease;
            flex-shrink: 0;
        }}
        
        .toaster-close:hover {{
            color: #666;
        }}
        
        .toaster-session {{
            border-left: 4px solid #dc3545;
        }}
        
        .toaster-info {{
            border-left: 4px solid #007bff;
        }}
        
        .toaster-success {{
            border-left: 4px solid #28a745;
        }}
        
        .toaster-warning {{
            border-left: 4px solid #ffc107;
        }}
        
        .toaster-error {{
            border-left: 4px solid #dc3545;
        }}
        
        @media (max-width: 768px) {{
            .reconnect-content {{
                margin: 20px;
                width: calc(100% - 40px);
            }}
            
            .reconnect-header, .reconnect-body, .reconnect-footer {{
                padding-left: 20px;
                padding-right: 20px;
            }}
            
            .toaster-container {{
                top: 10px;
                right: 10px;
                left: 10px;
            }}
            
            .toaster-toast {{
                min-width: auto;
                max-width: none;
            }}
        }}
        </style>
        '''


def init_auth(app):
    """Initialize JWT and token-based authentication for the Dash app."""
    return TokenAuth(app)