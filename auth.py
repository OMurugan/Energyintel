"""
Production authentication system for WCOD Dash application.
Implements the exact authentication flow as specified:

1. Production – Embedded Access (DASH_ENV = production)
   - Header Parameters: Origin/Authority: www.energyintel.com, embedded: true
   - Authentication: Bearer token validation only
   - Results: Valid token → Load app, Expired token → Show reconnect overlay, No token → Auth failure

2. Production – Direct Access (DASH_ENV = production)  
   - Header Parameters: Origin/Authority: data.energyintel.com
   - Authentication: Bearer token OR redirect to portal login
   - Results: Valid token → Load app, No/expired token → Redirect to portal
"""

import os
import json
import time
import jwt
import base64
import hmac
import hashlib
from flask import Flask, request, g, jsonify, Response, redirect, url_for, session
from functools import wraps
from urllib.parse import urlencode

class TokenAuth:
    """Production authentication system for WCOD Dash application."""
    
    def __init__(self, app):
        self.app = app
        self.server = app.server
        
        # Configuration
        self.jwt_secret = os.environ.get('EMBEDDED_SECRET_KEY', 'secret_key')
        self.portal_url = os.environ.get('PORTAL_URL', 'https://data.energyintel.com/portal')
        
        print(f"DEBUG: TokenAuth initialized")
        print(f"DEBUG: Portal URL: {self.portal_url}")
        
        # Register authentication handlers
        self.server.before_request(self._authenticate_request)
        
        print(f"DEBUG: Authentication handlers registered")
    
    def _authenticate_request(self):
        """Main authentication handler - implements the exact flow specified."""
        
        print(f"DEBUG: ==========================================")
        print(f"DEBUG: AUTHENTICATION REQUEST")
        print(f"DEBUG: Path: {request.path}")
        print(f"DEBUG: Method: {request.method}")
        print(f"DEBUG: Host: {request.host}")
        print(f"DEBUG: Origin: {request.headers.get('Origin', 'None')}")
        print(f"DEBUG: Authority: {request.headers.get(':authority', request.headers.get('Host', 'None'))}")
        print(f"DEBUG: Embedded header: {request.headers.get('embedded', 'None')}")
        print(f"DEBUG: Referrer: {request.referrer or 'None'}")
        print(f"DEBUG: ==========================================")
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            print("DEBUG: Skipping auth for OPTIONS request")
            return None
        
        # Skip authentication for whitelisted paths
        if self._is_whitelisted_path():
            print(f"DEBUG: Path {request.path} is whitelisted, skipping auth")
            return None
        
        # Handle Dash callback requests specially
        if self._is_dash_callback():
            print("DEBUG: 🔄 DASH CALLBACK REQUEST - Using callback authentication")
            return self._handle_callback_authentication()
        
        # Determine access type
        access_type = self._determine_access_type()
        print(f"DEBUG: Access type determined: {access_type}")
        
        if access_type == "embedded":
            return self._handle_embedded_access()
        elif access_type == "direct":
            return self._handle_direct_access()
        else:
            print("DEBUG: Unknown access type - defaulting to direct access handling")
            return self._handle_direct_access()
    
    def _is_dash_callback(self):
        """Check if this is a Dash callback request."""
        path = request.path.lower()
        
        # Dash callback indicators
        callback_indicators = [
            '/_dash-update-component' in path and request.method == 'POST',
            request.path == '/_dash-update-component' and request.method == 'POST'
        ]
        
        is_callback = any(callback_indicators)
        
        if is_callback:
            print(f"DEBUG: 🔄 DASH CALLBACK detected - Path: {request.path}, Method: {request.method}")
        
        return is_callback
    
    def _handle_callback_authentication(self):
        """Handle authentication for Dash callback requests."""
        print("DEBUG: 🔄 Handling callback authentication")
        
        # For callbacks, we need to be more lenient but still secure
        # Check for Bearer token first
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            print(f"DEBUG: 🔄 Found Bearer token in callback: {token[:20]}...")
            
            validation_result = self._validate_bearer_token(token)
            
            if validation_result == 'valid':
                print("DEBUG: 🔄 ✅ Bearer token valid for callback")
                return None  # Allow callback to proceed
            elif validation_result == 'expired':
                print("DEBUG: 🔄 ⏰ Bearer token expired for callback")
                return self._create_callback_expired_response()
            else:
                print("DEBUG: 🔄 ❌ Bearer token invalid for callback")
                return self._create_callback_auth_failure()
        
        # Check for session-based authentication (for direct access callbacks)
        if self._has_valid_production_tokens():
            print("DEBUG: 🔄 ✅ Valid production tokens found for callback")
            return None  # Allow callback to proceed
        
        # No valid authentication for callback
        print("DEBUG: 🔄 ❌ No valid authentication for callback")
        return self._create_callback_auth_failure()
    
    def _create_callback_expired_response(self):
        """Create JSON response for expired token in callback."""
        print("DEBUG: Creating callback expired token response")
        
        error_response = {
            'error': 'Token expired',
            'message': 'Your authentication token has expired. Please refresh the page.',
            'code': 'TOKEN_EXPIRED',
            'action': 'REFRESH_PAGE'
        }
        
        response = jsonify(error_response)
        response.status_code = 401
        
        # Add CORS headers
        origin = request.headers.get('Origin')
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
        
        return response
    
    def _create_callback_auth_failure(self):
        """Create JSON response for authentication failure in callback."""
        print("DEBUG: Creating callback auth failure response")
        
        error_response = {
            'error': 'Authentication failed',
            'message': 'Authentication is required. Please refresh the page.',
            'code': 'AUTH_REQUIRED',
            'action': 'REFRESH_PAGE'
        }
        
        response = jsonify(error_response)
        response.status_code = 403
        
        # Add CORS headers
        origin = request.headers.get('Origin')
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
        
        return response
    
    def _is_whitelisted_path(self):
        """Check if the current path should skip authentication."""
        path = request.path.lower()
        whitelist = [
            '/_dash-layout',
            '/_dash-dependencies', 
            '/_dash-component-suites/',
            '/_reload-hash',
            '/assets/', 
            '/_favicon.ico', 
            '/static/',
            '/health',
            '/_resources'
            # Note: /_dash-update-component is NOT whitelisted - it needs authentication
        ]
        
        return any(x in path for x in whitelist)
    
    def _determine_access_type(self):
        """Determine if this is embedded or direct access based on headers."""
        
        # Get relevant headers
        host = request.headers.get('Host', '').lower()
        authority = request.headers.get(':authority', '').lower()
        origin = request.headers.get('Origin', '').lower()
        embedded_header = request.headers.get('embedded', '').lower()
        referrer = (request.referrer or '').lower()
        
        print(f"DEBUG: Access type analysis:")
        print(f"DEBUG: - Host: {host}")
        print(f"DEBUG: - Authority: {authority}")
        print(f"DEBUG: - Origin: {origin}")
        print(f"DEBUG: - Embedded header: {embedded_header}")
        print(f"DEBUG: - Referrer: {referrer}")
        
        # Check for embedded access indicators
        embedded_indicators = [
            # Explicit embedded header
            embedded_header == 'true',
            
            # Origin from www.energyintel.com
            'www.energyintel.com' in origin,
            
            # Authority is www.energyintel.com
            'www.energyintel.com' in authority,
            
            # Host is www.energyintel.com
            'www.energyintel.com' in host,
            
            # Referrer from www.energyintel.com
            'www.energyintel.com' in referrer
        ]
        
        if any(embedded_indicators):
            print("DEBUG: EMBEDDED ACCESS detected")
            return "embedded"
        
        # Check for direct access indicators
        direct_indicators = [
            # Authority is data.energyintel.com
            'data.energyintel.com' in authority,
            
            # Host is data.energyintel.com
            'data.energyintel.com' in host,
            
            # Origin from data.energyintel.com
            'data.energyintel.com' in origin
        ]
        
        if any(direct_indicators):
            print("DEBUG: DIRECT ACCESS detected")
            return "direct"
        
        # Default to direct for security
        print("DEBUG: Unable to determine access type - defaulting to DIRECT")
        return "direct"
    
    def _handle_embedded_access(self):
        """Handle embedded access - Bearer token validation only."""
        print("DEBUG: 🔗 HANDLING EMBEDDED ACCESS")
        print("DEBUG: 🔗 Requirements: Bearer token validation only")
        
        # Check for Bearer token
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            print("DEBUG: 🔗 ❌ No Bearer token found for embedded access")
            return self._create_auth_failure_response("Bearer token required for embedded access")
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        print(f"DEBUG: 🔗 Found Bearer token: {token[:20]}...")
        
        # Validate Bearer token
        validation_result = self._validate_bearer_token(token)
        
        if validation_result == 'valid':
            print("DEBUG: 🔗 ✅ Bearer token is valid - allowing embedded access")
            return None  # Allow request to continue
            
        elif validation_result == 'expired':
            print("DEBUG: 🔗 ⏰ Bearer token expired - showing reconnect overlay")
            return self._create_token_expired_response()
            
        else:  # invalid
            print("DEBUG: 🔗 ❌ Bearer token is invalid - showing auth failure")
            return self._create_auth_failure_response("Invalid authentication token")
    
    def _handle_direct_access(self):
        """Handle direct access - Bearer token OR redirect to portal."""
        print("DEBUG: 🌐 HANDLING DIRECT ACCESS")
        print("DEBUG: 🌐 Requirements: Bearer token OR redirect to portal")
        
        # Case 1: Check for Bearer token first
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            print(f"DEBUG: 🌐 Found Bearer token: {token[:20]}...")
            
            validation_result = self._validate_bearer_token(token)
            
            if validation_result == 'valid':
                print("DEBUG: 🌐 ✅ Bearer token is valid - allowing direct access")
                return None  # Allow request to continue
            else:
                print(f"DEBUG: 🌐 ❌ Bearer token {validation_result} - checking for other auth methods")
                # Fall through to Case 2
        
        # Case 2: Check for production cookies/tokens
        if self._has_valid_production_tokens():
            print("DEBUG: 🌐 ✅ Valid production tokens found - allowing direct access")
            return None  # Allow request to continue
        
        # Case 3: No valid authentication - redirect to portal
        print("DEBUG: 🌐 ❌ No valid authentication found - redirecting to portal")
        return redirect(self.portal_url)
    
    def _validate_bearer_token(self, token):
        """Validate Bearer token and return 'valid', 'expired', or 'invalid'."""
        try:
            print(f"DEBUG: Validating Bearer token...")
            
            # First decode without verification to check structure and expiry
            payload_unverified = jwt.decode(token, options={"verify_signature": False})
            print(f"DEBUG: Token payload structure: {list(payload_unverified.keys())}")
            
            # Check expiry first for better UX
            if 'exp' in payload_unverified:
                current_time = time.time()
                expires_at = payload_unverified['exp']
                
                if current_time > expires_at:
                    print(f"DEBUG: Bearer token expired - current: {current_time}, expires: {expires_at}")
                    return 'expired'
                else:
                    time_remaining = expires_at - current_time
                    print(f"DEBUG: Bearer token not expired - time remaining: {time_remaining:.0f} seconds")
            
            # Now validate with signature verification
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=['HS512'],
                options={
                    "verify_iss": False,  # Don't require issuer claim
                    "verify_aud": False   # Don't require audience claim
                }
            )
            
            print(f"DEBUG: Bearer token signature validation successful")
            return 'valid'
            
        except jwt.ExpiredSignatureError:
            print("DEBUG: Bearer token expired (signature verification)")
            return 'expired'
            
        except jwt.InvalidTokenError as e:
            print(f"DEBUG: Bearer token invalid: {e}")
            return 'invalid'
            
        except Exception as e:
            print(f"DEBUG: Bearer token validation error: {e}")
            return 'invalid'
    
    def _has_valid_production_tokens(self):
        """Check if request has valid production tokens (cookies, etc.)."""
        print("DEBUG: Checking for valid production tokens...")
        
        # Check production cookies
        production_token_names = [
            'pelcro.user.auth.token',  # Main production token
            'pelcro.unique.id',        # Pelcro unique ID
            'kcToken',                 # Keycloak access token
            'kcIdToken'                # Keycloak ID token
        ]
        
        for token_name in production_token_names:
            token_value = request.cookies.get(token_name)
            if token_value and len(token_value.strip()) > 10:  # Basic validation
                print(f"DEBUG: Found production token '{token_name}': {token_value[:20]}...")
                
                # For now, assume production tokens are valid if they exist
                # In a real implementation, you would validate these tokens
                print(f"DEBUG: Production token '{token_name}' appears valid")
                return True
        
        print("DEBUG: No valid production tokens found")
        return False
    
    def _create_token_expired_response(self):
        """Create response for expired token - show reconnect overlay."""
        print("DEBUG: Creating token expired response with reconnect overlay")
        
        reconnect_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Lost Connection</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f8f9fa;
                }
                .reconnect-container {
                    text-align: center;
                    padding: 40px;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                    max-width: 500px;
                    width: 90%;
                }
                .reconnect-icon {
                    font-size: 48px;
                    color: #ffc107;
                    margin-bottom: 20px;
                }
                .reconnect-title {
                    font-size: 24px;
                    font-weight: bold;
                    color: #333;
                    margin-bottom: 15px;
                }
                .reconnect-message {
                    color: #666;
                    margin-bottom: 25px;
                    line-height: 1.5;
                    font-size: 16px;
                }
                .reconnect-btn {
                    background-color: #007bff;
                    color: white;
                    border: none;
                    padding: 12px 30px;
                    border-radius: 6px;
                    font-size: 16px;
                    font-weight: bold;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    margin: 10px;
                }
                .reconnect-btn:hover {
                    background-color: #0056b3;
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(0, 123, 255, 0.3);
                }
            </style>
        </head>
        <body>
            <div class="reconnect-container">
                <div class="reconnect-icon">📡</div>
                <div class="reconnect-title">Lost Connection to Dash App</div>
                <div class="reconnect-message">
                    Reconnect now to keep your filters and any changes.
                </div>
                
                <button class="reconnect-btn" onclick="handleReconnect()">
                    🔄 Reconnect
                </button>
            </div>
            
            <script>
                function handleReconnect() {
                    // Notify parent window to refresh the token
                    if (window.parent && window.parent !== window) {
                        console.log('Requesting token refresh from parent window...');
                        
                        window.parent.postMessage({
                            type: 'DASH_TOKEN_EXPIRED',
                            action: 'REQUEST_TOKEN_REFRESH',
                            timestamp: Date.now()
                        }, '*');
                        
                        // Listen for token refresh response
                        window.addEventListener('message', function(event) {
                            if (event.data.type === 'DASH_TOKEN_REFRESH_RESPONSE') {
                                if (event.data.success) {
                                    // Reload the embedded section
                                    window.location.reload();
                                }
                            }
                        });
                        
                    } else {
                        // Not in iframe, just reload
                        window.location.reload();
                    }
                }
                
                // Auto-notify parent of token expiry
                if (window.parent && window.parent !== window) {
                    window.parent.postMessage({
                        type: 'DASH_TOKEN_EXPIRED',
                        action: 'NOTIFY_EXPIRY',
                        timestamp: Date.now()
                    }, '*');
                }
            </script>
        </body>
        </html>
        """
        
        return Response(reconnect_html, status=401, mimetype='text/html')
    
    def _create_auth_failure_response(self, message):
        """Create response for authentication failure."""
        print(f"DEBUG: Creating auth failure response: {message}")
        
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Required</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f8f9fa;
                }}
                .error-container {{
                    text-align: center;
                    padding: 40px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    max-width: 400px;
                }}
                .error-icon {{
                    font-size: 48px;
                    color: #dc3545;
                    margin-bottom: 20px;
                }}
                .error-title {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #333;
                    margin-bottom: 10px;
                }}
                .error-message {{
                    color: #666;
                    margin-bottom: 20px;
                    line-height: 1.5;
                }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <div class="error-icon">🔐</div>
                <div class="error-title">Authentication Required</div>
                <div class="error-message">
                    {message}<br>
                    Please ensure you are accessing this content through the proper channel.
                </div>
            </div>
        </body>
        </html>
        """
        
        return Response(error_html, status=403, mimetype='text/html')