"""
JWT-based authentication middleware for embedded Dash applications.
Supports both simple tokens and HS512 JWT tokens as used by the client.
"""

import os
import functools
import hashlib
import hmac
import time
import json
import base64
from flask import request, jsonify, g
import utils as utils


class TokenAuth:
    """JWT and token-based authentication for embedded Dash apps."""
    
    def __init__(self, app):
        self.app = app
        self.server = app.server
        
        # Token configuration
        self.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
        # Client's JWT secret key - should match the host app's SECRET_KEY
        self.jwt_secret = os.environ.get('EMBEDDED_SECRET_KEY', 'secret_key')
        self.valid_tokens = self._load_valid_tokens()
        self.token_expiry = int(os.environ.get('TOKEN_EXPIRY_HOURS', '24')) * 3600  # Convert to seconds
        
        # Add before_request handler
        self.server.before_request(self._check_token_auth)
    
    def _load_valid_tokens(self):
        """Load valid tokens from environment or use defaults."""
        # Default tokens for development/demo
        default_tokens = {
            'admin-token-123': {
                'user': 'admin',
                'permissions': ['read', 'write', 'admin'],
                'expires': None  # Never expires
            },
            'user-token-456': {
                'user': 'user',
                'permissions': ['read'],
                'expires': None  # Never expires
            }
        }
        
        # Load custom tokens from environment if provided
        custom_tokens_str = os.environ.get('VALID_TOKENS', '')
        if custom_tokens_str:
            try:
                # Format: token1:user1:perm1,perm2;token2:user2:perm3
                custom_tokens = {}
                for token_config in custom_tokens_str.split(';'):
                    if ':' in token_config:
                        parts = token_config.split(':')
                        if len(parts) >= 2:
                            token = parts[0]
                            user = parts[1]
                            permissions = parts[2].split(',') if len(parts) > 2 else ['read']
                            custom_tokens[token] = {
                                'user': user,
                                'permissions': permissions,
                                'expires': None
                            }
                return custom_tokens
            except Exception as e:
                print(f"Error parsing custom tokens: {e}, using defaults")
        
        return default_tokens
    
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
            
            # Check expiration
            if 'exp' in payload:
                if time.time() > payload['exp']:
                    print("JWT token expired")
                    return None
            
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
        # Skip auth for static assets
        if request.path.startswith('/_dash') or request.path.startswith('/assets'):
            return
        
        # Get token from various sources
        token = self._extract_token()
        
        if not token:
            return self._auth_error("No authentication token provided")
        
        # Try JWT validation first, then fallback to simple tokens
        token_info = self._validate_jwt_token(token)
        if not token_info:
            token_info = self._validate_simple_token(token)
        
        if not token_info:
            return self._auth_error("Invalid or expired token")
        
        # Store user info in Flask's g object for use in callbacks
        g.current_user = token_info['user']
        g.user_permissions = token_info['permissions']
        g.token = token
        g.jwt_payload = token_info.get('jwt_payload')
    
    def _extract_token(self):
        """Extract token from request headers, query params, or cookies."""
        # Check Authorization header (Bearer token)
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Check X-API-Token header
        api_token = request.headers.get('X-API-Token')
        if api_token:
            return api_token
        
        # Check cookie first (more reliable for embedded contexts)
        cookie_token = request.cookies.get('auth_token')
        if cookie_token:
            return cookie_token
        
        # Check for default token in environment (for development)
        default_token = os.environ.get('DEFAULT_AUTH_TOKEN')
        if default_token:
            return default_token
        
        # Check query parameter last (can cause issues with Dash Pages)
        query_token = request.args.get('token')
        if query_token:
            return query_token
        
        return None
    
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
            return jsonify({
                'error': 'Authentication required',
                'message': message,
                'auth_methods': [
                    'Authorization: Bearer <jwt-token>',
                    'X-API-Token: <token>',
                    '?token=<token>',
                    'Cookie: auth_token=<token>'
                ]
            }), 401
        else:
            # For web requests, return a simple HTML page with token info
            return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Required - Energy Intelligence</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                    .auth-container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .error {{ color: #dc3545; margin-bottom: 20px; }}
                    .method {{ background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 4px; font-family: monospace; }}
                    .token-example {{ background: #e7f3ff; padding: 15px; border-radius: 4px; margin: 15px 0; }}
                </style>
            </head>
            <body>
                <div class="auth-container">
                    <h2>🔐 Authentication Required</h2>
                    <div class="error">{message}</div>
                    
                    <h3>How to authenticate:</h3>
                    <p>Provide your authentication token using one of these methods:</p>
                    
                    <div class="method">Authorization: Bearer &lt;jwt-token&gt;</div>
                    <div class="method">X-API-Token: &lt;token&gt;</div>
                    <div class="method">?token=&lt;token&gt;</div>
                    <div class="method">Cookie: auth_token=&lt;token&gt;</div>
                    
                    <div class="token-example">
                        <h4>Demo Tokens:</h4>
                        <p><strong>Admin access:</strong> admin-token-123</p>
                        <p><strong>User access:</strong> user-token-456</p>
                        <p><strong>JWT tokens:</strong> Generated by embedded applications</p>
                        <p><em>Example:</em> <code>?token=admin-token-123</code></p>
                    </div>
                </div>
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


def init_auth(app):
    """Initialize JWT and token-based authentication for the Dash app."""
    return TokenAuth(app)