"""
JWT-based authentication middleware for embedded Dash applications.
Supports both simple tokens and HS512 JWT tokens as used by the client.
"""

import os
import json
import time
import jwt
from flask import Flask, request, g, jsonify, Response, redirect, url_for
from functools import wraps
from urllib.parse import urlencode

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
        
        # Production authentication URLs
        self.auth_base_url = os.environ.get('AUTH_BASE_URL', 'https://data.energyintel.com')
        self.portal_url = os.environ.get('PORTAL_URL', 'https://data.energyintel.com')
        self.realm = os.environ.get('AUTH_REALM', 'dash')
        self.client_id = os.environ.get('AUTH_CLIENT_ID', 'dash-app')
        
        # Environment detection will be done during request processing
        self.is_local = None
        self.is_production = None
        
        print(f"DEBUG: Authentication system initialized")
        
        # CRITICAL: Add before_request and after_request handlers with explicit registration
        print(f"DEBUG: Registering authentication handlers...")
        self.server.before_request(self._check_token_auth)
        self.server.after_request(self._set_auth_cookie)
        
        # ADDITIONAL: Register as a Flask route handler to ensure it's always called
        @self.server.before_request
        def force_auth_check():
            """Force authentication check on every request."""
            return self._check_token_auth()
        
        print(f"DEBUG: Authentication handlers registered successfully")
        
        # Load valid tokens after initialization
        self.valid_tokens = self._load_valid_tokens()
        print(f"DEBUG: Loaded {len(self.valid_tokens)} valid tokens including admin JWT")
    
    def _is_direct_access(self):
        """Check if this is direct access to data.energyintel.com."""
        if not request.host:
            return False
            
        # Check for direct access indicators
        direct_indicators = [
            'data.energyintel.com' in request.host,
            'auth-data.energyintel.com' in request.host
        ]
        
        is_direct = any(direct_indicators)
        if is_direct:
            print(f"DEBUG: Direct access detected to host: {request.host}")
        return is_direct
    
    def _is_embedded_access(self):
        """Check if this is embedded access from energyintel.com (main website)."""
        if not request.host:
            return False
            
        # Check for embedded access indicators
        embedded_indicators = [
            # Host-based detection (direct access to energyintel.com)
            'energyintel.com' in request.host and 'data.energyintel.com' not in request.host,
            'www.energyintel.com' in request.host,
            
            # Referrer-based detection (iframe from energyintel.com to data.energyintel.com)
            (request.referrer and 
             ('energyintel.com' in request.referrer or 'www.energyintel.com' in request.referrer)),
            
            # Header-based detection
            request.headers.get('X-Embedded-Mode') == 'true',
            request.headers.get('X-Parent-Domain') and 'energyintel.com' in request.headers.get('X-Parent-Domain', '')
        ]
        
        is_embedded = any(embedded_indicators)
        if is_embedded:
            print(f"DEBUG: Embedded access detected from host: {request.host}, referrer: {request.referrer}")
        return is_embedded
    
    def _is_local_environment(self):
        """Detect if running in local development environment."""
        # DASH_ENV=development always takes precedence
        dash_env = os.environ.get('DASH_ENV', '').lower()
        if dash_env == 'development':
            print("DEBUG: DASH_ENV=development - confirmed local environment")
            return True
        
        # If DASH_ENV=production, never treat as local regardless of host
        if dash_env == 'production':
            print("DEBUG: DASH_ENV=production - confirmed production environment")
            return False
        
        # If DASH_ENV is not set, use host-based detection
        if not request.host:
            return False
            
        # Check for local development indicators
        local_indicators = [
            'localhost' in request.host,
            '127.0.0.1' in request.host,
            '0.0.0.0' in request.host,
            ':8050' in request.host,
            ':8051' in request.host,
            ':8000' in request.host,
            ':3000' in request.host,
            ':5000' in request.host
        ]
        
        is_local = any(local_indicators)
        if is_local:
            print(f"DEBUG: Local environment detected from host: {request.host}")
        else:
            print(f"DEBUG: Not local environment, host: {request.host}")
        
        return is_local
    
    def _get_auth_redirect_url(self, redirect_uri=None):
        """Generate authentication redirect URL for production environment."""
        if not redirect_uri:
            # Use the current URL as redirect target
            redirect_uri = request.url
        
        # Ensure redirect_uri uses HTTPS
        if redirect_uri.startswith('http://'):
            redirect_uri = redirect_uri.replace('http://', 'https://', 1)
        
        # Build OpenID Connect auth URL
        auth_params = {
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'openid profile email',
            'state': os.urandom(16).hex()  # CSRF protection
        }
        
        auth_url = f"{self.auth_base_url}/auth/realms/{self.realm}/protocol/openid-connect/auth?{urlencode(auth_params)}"
        print(f"DEBUG: Generated auth redirect URL: {auth_url}")
        return auth_url
    
    def _redirect_to_auth(self, redirect_uri=None):
        """Redirect user to authentication page."""
        if self.is_local:
            print("DEBUG: Local environment - not redirecting to auth")
            return None

        # In production, redirect to portal first (data.energyintel.com/portal)
        # The portal will handle the authentication flow
        portal_url = self.portal_url.rstrip('/') + "/portal"
        print(f"DEBUG: Redirecting to portal: {portal_url}")
        return redirect(portal_url)
    
    def _redirect_to_portal(self):
        """Redirect user to portal page for authentication."""
        print("DEBUG: Redirecting to portal for authentication")
        
        # In production, redirect to portal (data.energyintel.com/portal)
        portal_url = self.portal_url.rstrip('/') + "/portal"
        print(f"DEBUG: Redirecting to portal: {portal_url}")
        return redirect(portal_url)
    
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
        print(f"DEBUG: ==========================================")
        print(f"DEBUG: AUTHENTICATION CHECK TRIGGERED")
        print(f"DEBUG: Path: {request.path}")
        print(f"DEBUG: Host: {request.host}")
        print(f"DEBUG: Method: {request.method}")
        print(f"DEBUG: Headers: {dict(request.headers)}")
        print(f"DEBUG: Cookies: {dict(request.cookies)}")
        print(f"DEBUG: ==========================================")
        
        # CRITICAL: Clean up expired sessions first
        self._invalidate_expired_sessions()
        
        # Skip authentication for OPTIONS requests (CORS preflight) - this must be first
        if request.method == 'OPTIONS':
            print("DEBUG: Skipping auth for OPTIONS request")
            return None
        
        # PRODUCTION FIX: Better environment detection with fallbacks
        dash_env = os.environ.get('DASH_ENV', '').lower()
        enable_auth = os.environ.get('ENABLE_AUTH', 'true').lower()
        embedded_mode = os.environ.get('EMBEDDED_MODE', 'true').lower()
        
        print(f"DEBUG: Environment: {dash_env}")
        print(f"DEBUG: Enable Auth: {enable_auth}")
        print(f"DEBUG: Embedded Mode: {embedded_mode}")
        
        # PRODUCTION FIX: If environment is not properly set, use other indicators
        if not dash_env:
            # Try to detect production environment from host or other indicators
            if request.host and 'data.energyintel.com' in request.host:
                dash_env = 'production'
                print(f"DEBUG: PRODUCTION detected from host: {request.host}")
            elif enable_auth == 'true' and embedded_mode == 'true':
                dash_env = 'production'
                print(f"DEBUG: PRODUCTION detected from auth settings")
            else:
                dash_env = 'development'
                print(f"DEBUG: Defaulting to DEVELOPMENT due to unclear environment")
        
        # CRITICAL: In development mode, bypass ALL authentication checks
        if dash_env == 'development':
            print("DEBUG: DASH_ENV=development - completely bypassing authentication for ALL requests")
            return None
        
        # PRODUCTION FIX: Handle embedded mode more intelligently
        if embedded_mode == 'true':
            print("DEBUG: 🔗 EMBEDDED MODE DETECTED - Using embedded authentication logic")
            return self._handle_embedded_authentication()
        
        # CRITICAL: Check for callback requests and validate session
        if self._is_callback_request():
            print("DEBUG: 🔄 CALLBACK REQUEST DETECTED - Validating session")
            if not self._validate_callback_authentication():
                print("DEBUG: ❌ CALLBACK AUTHENTICATION FAILED - BLOCKING REQUEST")
                return self._handle_callback_auth_failure()
            else:
                print("DEBUG: ✅ CALLBACK AUTHENTICATION SUCCESS")
                return None  # Allow callback to proceed
        
        # Skip auth for static assets, dash internal routes, and health checks
        path = request.path.lower()
        whitelist = [
            '/_dash-layout',
            '/_dash-dependencies', 
            '/_dash-component-suites/',
            '/_dash-update-component',
            '/_reload-hash',  # Dash hot reload endpoint
            '_reload-hash',
            '/assets/', 
            '/_favicon.ico', 
            '/static/',
            '/health',
            '/_resources',
            '/portal',      # Explicitly whitelist portal to prevent redirect loops
            '/portal/'
        ]
        
        if any(x in path for x in whitelist):
            print(f"DEBUG: Path {path} is whitelisted, skipping auth")
            return None
        
        # CRITICAL: For any non-whitelisted path, we MUST check authentication
        print(f"DEBUG: ⚠️  NON-WHITELISTED PATH DETECTED: {path}")
        print(f"DEBUG: ⚠️  THIS PATH REQUIRES AUTHENTICATION CHECK")
        
        # CRITICAL: Check if this is data.energyintel.com - if so, ALWAYS require auth
        if request.host and 'data.energyintel.com' in request.host:
            print(f"DEBUG: 🚨 PRODUCTION HOST DETECTED: {request.host}")
            print(f"DEBUG: 🚨 ENFORCING PRODUCTION AUTHENTICATION")
            
            # Check for embedded access (stricter check to avoid self-referrer bypass)
            is_embedded = False
            if request.referrer:
                ref_low = request.referrer.lower()
                # Must be from energyintel.com but NOT from data.energyintel.com
                if ('energyintel.com' in ref_low or 'www.energyintel.com' in ref_low) and \
                   'data.energyintel.com' not in ref_low:
                    is_embedded = True
            
            if is_embedded:
                print(f"DEBUG: Embedded access from trusted referrer ({request.referrer}) - allowing")
                return None
            
            # Check for production tokens
            production_tokens = ['pelcro.user.auth.token', 'kcToken', 'kcIdToken']
            tokens_found = 0
            
            for token_name in production_tokens:
                token_value = request.cookies.get(token_name)
                if token_value and len(token_value) > 10:
                    tokens_found += 1
            
            print(f"DEBUG: 🚨 Production tokens found: {tokens_found}")
            
            if tokens_found == 0:
                print("DEBUG: 🚨🚨🚨 NO PRODUCTION TOKENS - BLOCKING ACCESS IMMEDIATELY 🚨🚨🚨")
                portal_url = "https://data.energyintel.com/portal"
                print(f"DEBUG: 🚨🚨🚨 REDIRECTING TO: {portal_url} 🚨🚨🚨")
                return redirect(portal_url)
            else:
                print(f"DEBUG: ✅ Found {tokens_found} production tokens - allowing access")
                return None
        
        # Determine access context for other hosts
        is_direct = self._is_direct_access()
        is_embedded = self._is_embedded_access()
        is_local = self._is_local_environment()
        
        print(f"DEBUG: Access context - Direct: {is_direct}, Embedded: {is_embedded}, Local: {is_local}")
        
        # Priority logic: Embedded access takes precedence over direct access
        if is_embedded:
            print(f"DEBUG: Embedded access from trusted referrer ({request.referrer}) - allowing")
            return None  # Allow request to continue
        
        # CRITICAL: In production, direct access MUST be authenticated
        elif is_direct and dash_env == 'production':
            print("DEBUG: 🚨 PRODUCTION - Direct access to data.energyintel.com requires authentication")
            print("DEBUG: 🚨 CHECKING AUTHENTICATION NOW...")
            auth_result = self._handle_production_authentication()
            if auth_result is not None:
                print("DEBUG: 🚨 BLOCKING REQUEST - Authentication failed, returning redirect")
                print(f"DEBUG: 🚨 REDIRECT RESPONSE: {auth_result}")
                return auth_result  # This should block the request
            else:
                print("DEBUG: ✅ Authentication successful, allowing request to continue")
                return None  # Allow request to continue
        
        # Local development environment
        elif is_local and dash_env != 'production':
            print("DEBUG: Local development environment - using development authentication")
            return self._handle_local_authentication()
        
        # Default: treat as production for security
        else:
            print("DEBUG: 🚨 DEFAULT CASE - treating as production and requiring authentication")
            print("DEBUG: 🚨 THIS IS A SECURITY-CRITICAL PATH")
            auth_result = self._handle_production_authentication()
            if auth_result is not None:
                print("DEBUG: 🚨 BLOCKING REQUEST - Default authentication failed, returning redirect")
                print(f"DEBUG: 🚨 REDIRECT RESPONSE: {auth_result}")
                return auth_result  # This should block the request
            else:
                print("DEBUG: ✅ Default authentication successful, allowing request to continue")
                return None  # Allow request to continue
        
    def _extract_production_tokens(self):
        """Extract production tokens from request sources."""
        tokens = []
        
        # Check production tokens in priority order
        production_token_names = [
            'pelcro.user.auth.token',  # Main production token from Pelcro
            'kcToken',                # Keycloak access token
            'kcIdToken'               # Keycloak ID token
        ]
        
        # Check cookies for production tokens
        for cookie_name in production_token_names:
            token_value = request.cookies.get(cookie_name)
            if token_value and len(token_value) > 10:  # Basic validation
                print(f"DEBUG: Found production token in cookie: {cookie_name}")
                tokens.append(token_value)
        
        # Check query parameter
        query_token = request.args.get('token')
        if query_token and len(query_token) > 10:
            print(f"DEBUG: Found production token in query parameter")
            tokens.append(query_token)
        
        # Check Authorization header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token_value = auth_header[7:]
            if len(token_value) > 10:
                print(f"DEBUG: Found production token in Authorization header")
                tokens.append(token_value)
        
        # Check X-API-Token header
        api_token = request.headers.get('X-API-Token')
        if api_token and len(api_token) > 10:
            print(f"DEBUG: Found production token in X-API-Token header")
            tokens.append(api_token)
        
        print(f"DEBUG: Extracted {len(tokens)} production tokens from request")
        
        # CRITICAL: If no tokens found in production, this is a security issue
        if len(tokens) == 0:
            print("DEBUG: ❌ SECURITY ALERT: No production tokens found in request!")
            print("DEBUG: ❌ This request should be BLOCKED immediately!")
            
        return tokens
    
    def _is_callback_request(self):
        """Check if this is a Dash callback request that requires authentication."""
        # Dash callback requests have specific characteristics
        path = request.path.lower()
        
        # Internal Dash endpoints that should not require session validation
        internal_endpoints = [
            '/_reload-hash',
            '/_dash-layout',
            '/_dash-dependencies',
            '/_dash-component-suites/',
            '/assets/',
            '/_favicon.ico',
            '/static/',
            '/_resources'
        ]
        
        # Skip callback validation for internal endpoints
        if any(endpoint in path for endpoint in internal_endpoints):
            return False
        
        # EMERGENCY FIX: Be more lenient with callback detection
        # Only treat as user callback if it's clearly a user interaction
        callback_indicators = [
            # Path-based detection for user callbacks
            '/_dash-update-component' in request.path and request.method == 'POST',
            
            # ONLY require strict validation for POST requests with specific patterns
            (request.method == 'POST' and 
             request.is_json and 
             '/_dash-update-component' in request.path and
             request.headers.get('X-CSRFToken') is not None and 
             request.headers.get('X-CSRFToken') != 'undefined')
        ]
        
        is_callback = any(callback_indicators)
        
        if is_callback:
            print(f"DEBUG: 🔄 USER CALLBACK REQUEST DETECTED")
            print(f"DEBUG: 🔄 Path: {request.path}")
            print(f"DEBUG: 🔄 Method: {request.method}")
            print(f"DEBUG: 🔄 Content-Type: {request.headers.get('Content-Type')}")
            print(f"DEBUG: 🔄 Is JSON: {request.is_json}")
            print(f"DEBUG: 🔄 CSRF Token: {request.headers.get('X-CSRFToken')}")
        
        return is_callback
    
    def _handle_callback_auth_failure(self):
        """Handle authentication failure for callback requests."""
        print("DEBUG: ❌ CALLBACK AUTHENTICATION FAILED")
        
        # For callback requests, return JSON error instead of redirect
        error_response = {
            'error': 'Authentication expired',
            'message': 'Your session has expired. Please refresh the page to continue.',
            'code': 'SESSION_EXPIRED',
            'action': 'REFRESH_PAGE'
        }
        
        response = jsonify(error_response)
        response.status_code = 401
        
        # Add CORS headers for callback responses
        origin = request.headers.get('Origin')
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
        
        print(f"DEBUG: ❌ RETURNING CALLBACK AUTH FAILURE: {error_response}")
        return response
    
    def _handle_local_authentication(self):
        """Handle authentication for local development environment."""
        print("DEBUG: Handling local development authentication")
        
        # In local development, we can be more permissive
        # But still check for basic authentication if enabled
        dash_env = os.environ.get('DASH_ENV', '').lower()
        
        if dash_env == 'development':
            print("DEBUG: Development environment - bypassing authentication")
            return None  # Allow all requests in development
        
        # For local but not development, use production-like authentication
        return self._handle_production_authentication()
    
    def _handle_production_authentication(self):
        """Handle authentication for production environment (data.energyintel.com)."""
        print("DEBUG: Handling production authentication")
        
        # Extract production tokens from request
        potential_tokens = self._extract_production_tokens()
        print(f"DEBUG: Found {len(potential_tokens)} production tokens")
        
        token_info = None
        valid_token = None
        
        # Try each token found until one works
        for i, token in enumerate(potential_tokens):
            print(f"DEBUG: Trying production token {i+1}: {token[:20]}...")
            
            # Try JWT validation for production tokens
            token_info = self._validate_production_jwt_token(token)
            if token_info:
                print(f"DEBUG: Production token {i+1} is valid!")
                valid_token = token
                break
            else:
                print(f"DEBUG: Production token {i+1} is invalid or expired")
        
        if not token_info:
            print("DEBUG: No valid production token found, BLOCKING REQUEST and redirecting to portal")
            # CRITICAL: Return redirect response to block the request
            portal_url = self.portal_url.rstrip('/') + "/portal"
            print(f"DEBUG: BLOCKING ACCESS - Redirecting to portal: {portal_url}")
            return redirect(portal_url)
        
        # Store user info in Flask's g object for use in callbacks
        g.current_user = token_info['user']
        g.user_permissions = token_info['permissions']
        g.token = valid_token
        g.jwt_payload = token_info.get('jwt_payload')
        
        print(f"DEBUG: Production authentication successful for user: {token_info['user']}")
        return None  # Allow request to continue
    
    def _validate_production_jwt_token(self, token):
        """Validate production JWT tokens from Keycloak/Pelcro with strict expiry checking."""
        try:
            import jwt
            import time
            import base64
            import json
            import hmac
            import hashlib
            
            # Try to decode the token to check if it's a valid JWT
            try:
                # First, try to decode without verification to check structure and expiry
                payload = jwt.decode(token, options={"verify_signature": False})
                print(f"DEBUG: JWT payload structure: {list(payload.keys())}")
                
                # CRITICAL: Strict token expiry checking with 10-minute TTL enforcement
                if 'exp' in payload:
                    current_time = time.time()
                    token_exp = payload['exp']
                    issued_at = payload.get('iat', current_time - 3600)  # Default to 1 hour ago if not present
                    
                    print(f"DEBUG: Token expiry check - Current: {current_time}, Expires: {token_exp}, Issued: {issued_at}")
                    
                    # CRITICAL: Enforce 10-minute TTL from CMS
                    max_token_age = 10 * 60  # 10 minutes in seconds
                    token_age = current_time - issued_at
                    
                    print(f"DEBUG: Token age: {token_age:.0f} seconds (max allowed: {max_token_age} seconds)")
                    
                    # Check if token has exceeded the 10-minute TTL
                    if token_age > max_token_age:
                        print(f"DEBUG: ❌ TOKEN EXCEEDED 10-MINUTE TTL")
                        print(f"DEBUG: ❌ Token age: {token_age:.0f} seconds")
                        print(f"DEBUG: ❌ Max allowed: {max_token_age} seconds")
                        print(f"DEBUG: ❌ Exceeded by: {token_age - max_token_age:.0f} seconds")
                        return None
                    
                    # Also check the standard expiry time
                    if current_time > token_exp:
                        print(f"DEBUG: ❌ PRODUCTION JWT TOKEN EXPIRED (standard expiry)")
                        print(f"DEBUG: ❌ Current time: {current_time}")
                        print(f"DEBUG: ❌ Token expired at: {token_exp}")
                        print(f"DEBUG: ❌ Expired {current_time - token_exp:.0f} seconds ago")
                        return None
                    
                    time_remaining = min(token_exp - current_time, max_token_age - token_age)
                    print(f"DEBUG: ✅ Production JWT token valid. Time remaining: {time_remaining:.0f} seconds")
                    
                    # CRITICAL: If token expires in less than 60 seconds, treat as expired for security
                    if time_remaining < 60:
                        print(f"DEBUG: ⚠️  Token expires in {time_remaining:.0f} seconds - treating as expired for security")
                        return None
                
                # CRITICAL: Check for required claims and scopes
                user_id = payload.get('sub', payload.get('userId', payload.get('username', 'production_user')))
                
                # Check for WCOD-specific scopes if present
                scopes = payload.get('scope', payload.get('scopes', []))
                if isinstance(scopes, str):
                    scopes = scopes.split(' ')
                
                print(f"DEBUG: Token scopes: {scopes}")
                
                # CRITICAL: Validate dashboard-specific access
                dashboard_scope = self._validate_dashboard_scope(payload, scopes)
                if not dashboard_scope:
                    print(f"DEBUG: ❌ Token does not have required dashboard scope")
                    return None
                
                # CRITICAL: Store token in session for callback validation
                self._store_session_token(token, payload)
                
                return {
                    'user': user_id,
                    'permissions': ['read', 'write'],
                    'expires': payload.get('exp'),
                    'jwt_payload': payload,
                    'scopes': scopes,
                    'dashboard_scope': dashboard_scope,
                    'token_age': token_age,
                    'max_age': max_token_age
                }
                
            except jwt.DecodeError:
                print("DEBUG: Token is not a valid JWT, trying as simple token")
                # If it's not a JWT, treat as simple token with expiry check
                return self._validate_simple_token_with_expiry(token)
                
        except Exception as e:
            print(f"DEBUG: Production JWT validation error: {e}")
            return None
    
    def _validate_dashboard_scope(self, payload, scopes):
        """Validate that the token has access to the current dashboard."""
        # Get current dashboard from request path
        current_path = request.path.lower()
        
        # Map paths to required scopes
        dashboard_scopes = {
            '/wcod-country/': 'wcod-country',
            '/wcod-crude/': 'wcod-crude',
            '/energy-dashboard/': 'energy-dashboard',
            '/oil-markets/': 'oil-markets'
        }
        
        required_scope = None
        for path_prefix, scope in dashboard_scopes.items():
            if current_path.startswith(path_prefix):
                required_scope = scope
                break
        
        if not required_scope:
            print(f"DEBUG: No specific scope required for path: {current_path}")
            return True  # Allow access if no specific scope is required
        
        # Check if token has the required scope
        if required_scope in scopes:
            print(f"DEBUG: ✅ Token has required scope: {required_scope}")
            return required_scope
        
        # Check for admin or global access scopes
        admin_scopes = ['admin', 'global-access', 'all-dashboards']
        for admin_scope in admin_scopes:
            if admin_scope in scopes:
                print(f"DEBUG: ✅ Token has admin scope: {admin_scope}")
                return admin_scope
        
        print(f"DEBUG: ❌ Token missing required scope: {required_scope}")
        print(f"DEBUG: ❌ Available scopes: {scopes}")
        return False
    
    def _store_session_token(self, token, payload):
        """Store token in session for callback validation."""
        try:
            # Store in Flask session for callback validation
            from flask import session
            session['auth_token'] = token
            session['auth_payload'] = payload
            session['auth_timestamp'] = time.time()
            
            # Also store in g for current request
            g.session_token = token
            g.session_payload = payload
            
            print(f"DEBUG: ✅ Stored session token for user: {payload.get('sub', 'unknown')}")
            
        except Exception as e:
            print(f"DEBUG: ⚠️  Failed to store session token: {e}")
    
    def _validate_callback_authentication(self):
        """Validate authentication for callback requests with emergency leniency."""
        try:
            # EMERGENCY FIX: For production callbacks, be more lenient
            # Check if user has ANY valid production token, not just unexpired session
            
            # First, try the strict session validation
            from flask import session
            session_token = session.get('auth_token')
            session_payload = session.get('auth_payload')
            session_timestamp = session.get('auth_timestamp')
            
            if session_token and session_payload and session_timestamp:
                current_time = time.time()
                session_age = current_time - session_timestamp
                max_session_age = 15 * 60  # EMERGENCY: Extend to 15 minutes for callbacks
                
                if session_age <= max_session_age:
                    # Validate the stored token with more lenient rules
                    token_info = self._validate_production_jwt_token_lenient(session_token)
                    if token_info:
                        print(f"DEBUG: ✅ Callback authentication valid via session, age: {session_age:.0f} seconds")
                        return True
            
            # EMERGENCY FALLBACK: Check for any valid production token in request
            print(f"DEBUG: 🚨 EMERGENCY CALLBACK AUTH - Checking production tokens directly")
            
            # Extract production tokens from request
            potential_tokens = self._extract_production_tokens()
            
            for i, token in enumerate(potential_tokens):
                print(f"DEBUG: 🚨 Trying emergency callback token {i+1}")
                
                # Use lenient validation for callbacks
                token_info = self._validate_production_jwt_token_lenient(token)
                if token_info:
                    print(f"DEBUG: ✅ EMERGENCY: Callback allowed with production token {i+1}")
                    # Store in session for future use
                    session['auth_token'] = token
                    session['auth_payload'] = token_info.get('jwt_payload', {})
                    session['auth_timestamp'] = time.time()
                    return True
            
            print(f"DEBUG: ❌ EMERGENCY: No valid tokens found for callback")
            return False
            
        except Exception as e:
            print(f"DEBUG: ❌ Emergency callback authentication error: {e}")
            return False
    
    def _invalidate_expired_sessions(self):
        """Invalidate expired sessions and tokens."""
        try:
            from flask import session
            
            # Check and clear expired session data
            session_timestamp = session.get('auth_timestamp')
            if session_timestamp:
                current_time = time.time()
                session_age = current_time - session_timestamp
                max_session_age = 10 * 60  # 10 minutes
                
                if session_age > max_session_age:
                    print(f"DEBUG: 🧹 Clearing expired session (age: {session_age:.0f} seconds)")
                    session.clear()
            
            # Clean up expired tokens from valid_tokens
            current_time = time.time()
            expired_tokens = []
            
            for token, token_info in self.valid_tokens.items():
                if token_info.get('expires') and current_time > token_info['expires']:
                    expired_tokens.append(token)
            
            for token in expired_tokens:
                print(f"DEBUG: 🧹 Removing expired token from valid_tokens")
                del self.valid_tokens[token]
            
            if expired_tokens:
                print(f"DEBUG: 🧹 Cleaned up {len(expired_tokens)} expired tokens")
                
        except Exception as e:
            print(f"DEBUG: ⚠️  Error during session cleanup: {e}")
    
    def _validate_simple_token_with_expiry(self, token):
        """Validate simple tokens with expiry checking."""
        if token in self.valid_tokens:
            token_info = self.valid_tokens[token]
            
            # CRITICAL: Check expiry if set
            if token_info.get('expires'):
                import time
                current_time = time.time()
                token_exp = token_info['expires']
                
                if current_time > token_exp:
                    print(f"DEBUG: ❌ Simple token expired {current_time - token_exp:.0f} seconds ago")
                    # Remove expired token
                    del self.valid_tokens[token]
                    return None
                else:
                    time_remaining = token_exp - current_time
                    print(f"DEBUG: ✅ Simple token valid. Time remaining: {time_remaining:.0f} seconds")
            
            return token_info
        
        return None
    
    def _validate_production_jwt_token_lenient(self, token):
        """EMERGENCY: Lenient validation for callbacks - allows slightly expired tokens."""
        try:
            import jwt
            import time
            import base64
            import json
            import hmac
            import hashlib
            
            # Handle base64 encoded tokens first
            if not token.count('.') == 2:
                try:
                    decoded_bytes = base64.b64decode(token)
                    token = decoded_bytes.decode('utf-8')
                except:
                    pass
            
            # Try to decode the token to check if it's a valid JWT
            try:
                # First, try to decode without verification to check structure and expiry
                payload = jwt.decode(token, options={"verify_signature": False})
                print(f"DEBUG: 🚨 EMERGENCY JWT validation - payload structure: {list(payload.keys())}")
                
                # PRODUCTION FIX: For live production tokens, be more lenient with TTL
                if 'exp' in payload:
                    current_time = time.time()
                    token_exp = payload['exp']
                    issued_at = payload.get('iat', current_time - 3600)
                    
                    print(f"DEBUG: 🚨 EMERGENCY Token expiry check - Current: {current_time}, Expires: {token_exp}, Issued: {issued_at}")
                    
                    # Check if token is actually expired (standard expiry)
                    if current_time > token_exp:
                        print(f"DEBUG: ❌ EMERGENCY: Token actually expired")
                        return None
                    
                    # PRODUCTION FIX: For live tokens that are not actually expired, allow them
                    # even if they exceed our TTL policy, but flag them for refresh
                    token_age = current_time - issued_at
                    max_token_age = 10 * 60  # 10 minutes normal limit
                    emergency_max_age = 24 * 60 * 60  # 24 hours for live production tokens
                    
                    print(f"DEBUG: 🚨 EMERGENCY Token age: {token_age:.0f} seconds")
                    
                    if token_age > emergency_max_age:
                        print(f"DEBUG: ❌ EMERGENCY: Token too old even for production ({token_age:.0f}s > {emergency_max_age}s)")
                        return None
                    
                    # Check if this is a Pelcro token (production system)
                    is_pelcro_token = (
                        payload.get('iss', '').startswith('https://www.pelcro.com') or
                        'pelcro' in payload.get('iss', '').lower()
                    )
                    
                    if is_pelcro_token and token_age > max_token_age:
                        print(f"DEBUG: ✅ EMERGENCY: Pelcro production token allowed despite TTL ({token_age:.0f}s old)")
                        print(f"DEBUG: ✅ EMERGENCY: Token not actually expired, valid until {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(token_exp))}")
                        
                        # Allow the token but flag for refresh
                        time_remaining = token_exp - current_time
                        print(f"DEBUG: ✅ EMERGENCY: Time remaining: {time_remaining:.0f} seconds ({time_remaining/3600:.1f} hours)")
                    else:
                        time_remaining = token_exp - current_time
                        print(f"DEBUG: ✅ EMERGENCY: Token valid for callback. Time remaining: {time_remaining:.0f} seconds")
                
                # Get user info
                user_id = payload.get('sub', payload.get('userId', payload.get('username', 'production_user')))
                
                # Get scopes
                scopes = payload.get('scope', payload.get('scopes', []))
                if isinstance(scopes, str):
                    scopes = scopes.split(' ')
                
                print(f"DEBUG: 🚨 EMERGENCY Token scopes: {scopes}")
                
                return {
                    'user': user_id,
                    'permissions': ['read', 'write'],
                    'expires': payload.get('exp'),
                    'jwt_payload': payload,
                    'scopes': scopes,
                    'emergency_access': True,  # Flag to indicate this was emergency access
                    'token_age': token_age if 'iat' in payload else 0,
                    'is_pelcro_token': is_pelcro_token if 'iat' in payload else False
                }
                
            except jwt.DecodeError:
                print("DEBUG: 🚨 EMERGENCY: Token is not a valid JWT, trying as simple token")
                return self._validate_simple_token_with_expiry(token)
                
        except Exception as e:
            print(f"DEBUG: 🚨 EMERGENCY JWT validation error: {e}")
            return None

    def _handle_embedded_authentication(self):
        """Handle authentication for embedded mode (EMBEDDED_MODE=true)."""
        print("DEBUG: 🔗 Handling embedded authentication")
        
        # In embedded mode, we need to be more flexible about authentication
        # This is typically used when the app is embedded in an iframe from energyintel.com
        
        # Check if this is a callback request first
        if self._is_callback_request():
            print("DEBUG: 🔗 EMBEDDED CALLBACK REQUEST - Validating session")
            if not self._validate_callback_authentication():
                print("DEBUG: ❌ EMBEDDED CALLBACK AUTHENTICATION FAILED")
                return self._handle_callback_auth_failure()
            else:
                print("DEBUG: ✅ EMBEDDED CALLBACK AUTHENTICATION SUCCESS")
                return None  # Allow callback to proceed
        
        # Skip authentication for static assets and whitelisted paths
        path = request.path.lower()
        whitelist = [
            '/_dash-layout',
            '/_dash-dependencies', 
            '/_dash-component-suites/',
            '/_dash-update-component',
            '/_reload-hash',
            '_reload-hash',
            '/assets/', 
            '/_favicon.ico', 
            '/static/',
            '/health',
            '/_resources',
            '/portal',
            '/portal/'
        ]
        
        if any(x in path for x in whitelist):
            print(f"DEBUG: 🔗 EMBEDDED: Path {path} is whitelisted, skipping auth")
            return None
        
        # Check for embedded access from trusted referrer
        is_embedded_access = False
        if request.referrer:
            ref_low = request.referrer.lower()
            # Must be from energyintel.com but NOT from data.energyintel.com (to avoid self-referrer bypass)
            if ('energyintel.com' in ref_low or 'www.energyintel.com' in ref_low) and \
               'data.energyintel.com' not in ref_low:
                is_embedded_access = True
                print(f"DEBUG: 🔗 EMBEDDED ACCESS from trusted referrer: {request.referrer}")
        
        # Check for embedded mode headers
        if request.headers.get('X-Embedded-Mode') == 'true' or \
           request.headers.get('X-Parent-Domain') and 'energyintel.com' in request.headers.get('X-Parent-Domain', ''):
            is_embedded_access = True
            print(f"DEBUG: 🔗 EMBEDDED ACCESS via headers")
        
        # If this is embedded access from trusted source, allow it
        if is_embedded_access:
            print("DEBUG: 🔗 EMBEDDED: Trusted embedded access - allowing without token check")
            return None  # Allow request to continue
        
        # For non-embedded access in embedded mode, check tokens with refresh handling
        print("DEBUG: 🔗 EMBEDDED: Non-embedded access detected - checking authentication with refresh support")
        
        # PRODUCTION FIX: Use token refresh handler for better user experience
        try:
            from token_refresh_handler import token_refresh_handler
            
            # Check if this is a refresh callback
            if token_refresh_handler.is_refresh_callback():
                print("DEBUG: 🔗 EMBEDDED: Handling token refresh callback")
                refresh_result = token_refresh_handler.handle_refresh_callback()
                if refresh_result:
                    return refresh_result  # Redirect if refresh incomplete
            
            # Check tokens and handle refresh if needed
            refresh_result = token_refresh_handler.check_and_handle_token_refresh()
            if refresh_result:
                print("DEBUG: 🔗 EMBEDDED: Token refresh required - redirecting")
                return refresh_result  # Redirect for token refresh
            
            print("DEBUG: 🔗 EMBEDDED: Token refresh check passed - proceeding with validation")
            
        except ImportError:
            print("DEBUG: 🔗 EMBEDDED: Token refresh handler not available - using fallback")
        
        # Extract production tokens from request
        potential_tokens = self._extract_production_tokens()
        print(f"DEBUG: 🔗 EMBEDDED: Found {len(potential_tokens)} production tokens")
        
        token_info = None
        valid_token = None
        
        # Try each token found until one works (use lenient validation for embedded mode)
        for i, token in enumerate(potential_tokens):
            print(f"DEBUG: 🔗 EMBEDDED: Trying production token {i+1}: {token[:20]}...")
            
            # Use lenient validation for embedded mode
            token_info = self._validate_production_jwt_token_lenient(token)
            if token_info:
                print(f"DEBUG: 🔗 EMBEDDED: Production token {i+1} is valid!")
                valid_token = token
                break
            else:
                print(f"DEBUG: 🔗 EMBEDDED: Production token {i+1} is invalid or expired")
        
        if not token_info:
            print("DEBUG: 🔗 EMBEDDED: No valid production token found")
            
            # In embedded mode, if no valid token, redirect to portal
            portal_url = self.portal_url.rstrip('/') + "/portal"
            print(f"DEBUG: 🔗 EMBEDDED: Redirecting to portal: {portal_url}")
            return redirect(portal_url)
        
        # Store user info in Flask's g object for use in callbacks
        g.current_user = token_info['user']
        g.user_permissions = token_info['permissions']
        g.token = valid_token
        g.jwt_payload = token_info.get('jwt_payload')
        
        print(f"DEBUG: 🔗 EMBEDDED: Authentication successful for user: {token_info['user']}")
        return None  # Allow request to continue

    
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
        
        # 4. Check cookies - prioritize production tokens
        # Production tokens from Keycloak/Pelcro
        production_tokens = [
            'pelcro.user.auth.token',  # Main production token
            'kcToken',                # Keycloak access token
            'kcIdToken'               # Keycloak ID token
        ]
        
        # Development tokens
        development_tokens = [
            'auth_token',
            'pelcro.user.auth.token'  # Also check for consistency
        ]
        
        # Check production tokens first
        for cookie_name in production_tokens:
            t = request.cookies.get(cookie_name)
            if t:
                print(f"DEBUG: Found production token: {cookie_name}")
                tokens.append(t)
        
        # Then check development tokens
        for cookie_name in development_tokens:
            t = request.cookies.get(cookie_name)
            if t:
                print(f"DEBUG: Found development token: {cookie_name}")
                tokens.append(t)
        
        # 5. Check for default token in environment
        default_token = os.environ.get('DEFAULT_AUTH_TOKEN')
        if default_token:
            tokens.append(default_token)
            
        print(f"DEBUG: Extracted {len(tokens)} tokens from request")
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
        """Return authentication error response with context-aware behavior."""
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
            # For web requests, check access context and handle accordingly
            is_embedded = self._is_embedded_access()
            is_direct = self._is_direct_access()
            is_local = self._is_local_environment()
            
            print(f"DEBUG: Access context - Embedded: {is_embedded}, Direct: {is_direct}, Local: {is_local}")
            
            if is_embedded:
                # Embedded access from energyintel.com - no redirect, allow app to load
                print("DEBUG: Embedded access from energyintel.com - allowing app to load without redirect")
                return None  # Let the normal Dash app handle the response
            
            elif is_direct:
                # Direct access to data.energyintel.com - authentication required
                print("DEBUG: Direct access to data.energyintel.com - redirecting to authentication")
                return self._redirect_to_auth()
            
            elif is_local:
                # Local development - use overlay approach
                print("DEBUG: Local environment - using overlay approach")
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
            
            else:
                # Default behavior - treat as local for safety
                print("DEBUG: Unknown context - defaulting to local overlay approach")
                is_initial_load = getattr(g, 'is_initial_load', False)
                
                if is_initial_load:
                    return None  # Let the normal Dash app handle the response
                else:
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
    auth_instance = TokenAuth(app)
    
    # CRITICAL: Add an additional before_request handler to ensure authentication is checked
    @app.server.before_request
    def enforce_authentication():
        """Additional authentication enforcement."""
        from flask import request
        
        # Skip for OPTIONS and whitelisted paths
        if request.method == 'OPTIONS':
            return None
            
        path = request.path.lower()
        whitelist = [
            '/_dash-layout',
            '/_dash-dependencies', 
            '/_dash-component-suites/',
            '/_dash-update-component',
            '_reload-hash',
            '/assets/', 
            '/_favicon.ico', 
            '/static/',
            '/health',
            '/_resources'
        ]
        
        if any(x in path for x in whitelist):
            return None
        
        # For all other paths, ensure authentication is checked
        print(f"DEBUG: � ADDITIONAL AUTH ENFORCEMENT for: {path}")
        
        # Check environment
        dash_env = os.environ.get('DASH_ENV', '').lower()
        if dash_env == 'production':
            # Check if this is direct access to data.energyintel.com
            if request.host and 'data.energyintel.com' in request.host:
                # Check for embedded access
                is_embedded = (request.referrer and 
                             ('energyintel.com' in request.referrer or 'www.energyintel.com' in request.referrer))
                
                if not is_embedded:
                    print(f"DEBUG: � DIRECT ACCESS TO PRODUCTION - Checking tokens")
                    
                    # Extract tokens
                    tokens = []
                    production_token_names = ['pelcro.user.auth.token', 'kcToken', 'kcIdToken']
                    
                    for cookie_name in production_token_names:
                        token_value = request.cookies.get(cookie_name)
                        if token_value and len(token_value) > 10:
                            tokens.append(token_value)
                    
                    if len(tokens) == 0:
                        print(f"DEBUG: 🚨 NO PRODUCTION TOKENS - BLOCKING ACCESS IMMEDIATELY")
                        portal_url = os.environ.get('PORTAL_URL', 'https://data.energyintel.com').rstrip('/') + "/portal"
                        print(f"DEBUG: 🚨 ENFORCED REDIRECT TO: {portal_url}")
                        from flask import redirect
                        return redirect(portal_url)
                    else:
                        print(f"DEBUG: ✅ Found {len(tokens)} tokens, allowing access")
        
        return None
    
    return auth_instance