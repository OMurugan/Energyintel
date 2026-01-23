"""
Shared Dash application instance for Dash Pages.
This module avoids name collisions with the existing app/ package.
"""

import os
from flask import request
from dash import Dash
import dash_bootstrap_components as dbc
from dash_embedded import Embeddable
from flask_cors import CORS

# Get configuration from environment
requests_pathname_prefix = os.environ.get('DASH_ROUTES_PATHNAME_PREFIX', '/')
host_app_origin = os.environ.get('HOST_APP_ORIGIN', 'https://www.energyintel.com')

# Single global Dash instance with Dash Pages enabled
app = Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",  # explicitly point to the pages package
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    plugins=[Embeddable(origins="*")],
    requests_pathname_prefix=requests_pathname_prefix,
)

# Expose server for gunicorn
server = app.server

# CRITICAL: Configure Flask secret key for sessions
server.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')
print(f"DEBUG: Flask secret key configured: {'*' * len(server.secret_key)}")

# Configure CORS for embedded access
# Allow the host application to access the Dash app when embedded
cors_origins = [
    "https://www.energyintel.com",  # Main host application
    "https://energyintel.com",      # Alternative domain
    # "http://localhost:3000",       # Development server
    # "http://localhost:8080",       # Alternative development port
]

# Configure CORS with specific settings for embedded Dash apps
CORS(
    server,
    origins=cors_origins,
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type", 
        "Authorization", 
        "X-API-Token",
        "X-Requested-With",
        "Accept",
        "Origin",
        "x-csrftoken",  # Add CSRF token header
        "X-CSRFToken",  # Alternative CSRF header format
        "embedded"      # Add embedded header for Dash embedded apps
    ],
    supports_credentials=True,  # Important for authentication cookies/tokens
    max_age=86400,  # Cache preflight requests for 24 hours
    vary_header=True,  # Ensure Vary header is properly set
    automatic_options=True,  # Automatically handle OPTIONS requests
)

# Add specific route for _resources endpoint to handle CORS properly
@server.route('/_resources', methods=['GET', 'OPTIONS'])
@server.route('//_resources', methods=['GET', 'OPTIONS'])  # Handle double slash case
def handle_resources():
    """Handle _resources endpoint with proper CORS support."""
    if request.method == 'OPTIONS':
        # Handle preflight request
        response = server.make_response()
        origin = request.headers.get('Origin')
        if origin and (origin in cors_origins or any(origin.endswith(domain) for domain in ['.energyintel.com'])):
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-API-Token,X-Requested-With,Accept,Origin,x-csrftoken,X-CSRFToken,embedded')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            response.headers.add('Access-Control-Max-Age', '86400')
        return response
    else:
        # Handle GET request - return empty JSON or redirect as needed
        # This endpoint is typically used by Dash for embedded resources
        response = server.make_response({'status': 'ok'})
        origin = request.headers.get('Origin')
        if origin and (origin in cors_origins or any(origin.endswith(domain) for domain in ['.energyintel.com'])):
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

# Additional CORS middleware for specific Dash routes that might not be covered by flask-cors
@server.after_request
def after_request(response):
    # Add CORS headers for all responses
    origin = None
    # Get the origin from the request using Flask's request object
    try:
        request_origin = request.headers.get('Origin')
        if request_origin and request_origin in cors_origins:
            origin = request_origin
        elif request_origin and any(request_origin.endswith(domain) for domain in ['.energyintel.com']):
            origin = request_origin
    except RuntimeError:
        # Outside of request context, skip CORS headers
        pass
    
    if origin:
        # Check if CORS header already exists to avoid duplication
        existing_origin = response.headers.get('Access-Control-Allow-Origin')
        if not existing_origin:
            response.headers.add('Access-Control-Allow-Origin', origin)
        elif existing_origin != origin:
            # Replace with the correct origin if different
            response.headers['Access-Control-Allow-Origin'] = origin
        
        # Always ensure CSRF and embedded headers are included - this is critical
        existing_headers = response.headers.get('Access-Control-Allow-Headers', '')
        required_headers = ['x-csrftoken', 'embedded']
        missing_headers = []
        
        for req_header in required_headers:
            if req_header.lower() not in existing_headers.lower():
                missing_headers.append(req_header)
        
        if missing_headers:
            if existing_headers:
                # Append missing headers to existing ones
                response.headers['Access-Control-Allow-Headers'] = f"{existing_headers},{','.join(missing_headers)}"
            else:
                # Set new headers list with all required headers
                all_headers = 'Content-Type,Authorization,X-API-Token,X-Requested-With,Accept,Origin,x-csrftoken,X-CSRFToken,embedded'
                response.headers['Access-Control-Allow-Headers'] = all_headers
        
        # Add other CORS headers only if not already present
        if not response.headers.get('Access-Control-Allow-Credentials'):
            response.headers.add('Access-Control-Allow-Credentials', 'true')
        if not response.headers.get('Access-Control-Allow-Methods'):
            response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        if not response.headers.get('Access-Control-Max-Age'):
            response.headers.add('Access-Control-Max-Age', '86400')  # 24 hours
    
    # Add additional security headers for embedded content
    if not response.headers.get('X-Content-Type-Options'):
        response.headers.add('X-Content-Type-Options', 'nosniff')
    if not response.headers.get('X-Frame-Options'):
        response.headers.add('X-Frame-Options', 'ALLOW-FROM https://www.energyintel.com')
    if not response.headers.get('Referrer-Policy'):
        response.headers.add('Referrer-Policy', 'strict-origin-when-cross-origin')
    
    return response

# Initialize authentication (optional - can be disabled via env var)
# Note: For testing overlay functionality, we're using custom TokenAuth instead of EmbeddedAuth
_auth_instance = None
is_embedded = os.environ.get('IS_EMBEDDED', 'false').lower() == 'true'
enable_auth = os.environ.get('ENABLE_AUTH', 'false').lower() == 'true'

# CRITICAL: Add immediate authentication check before any processing
@server.before_request
def immediate_auth_check():
    """Immediate authentication check - runs before everything else."""
    from flask import request, redirect
    
    # Skip for OPTIONS and static assets
    if request.method == 'OPTIONS':
        return None
        
    path = request.path.lower()
    static_paths = [
        '/_dash-layout',
        '/_dash-dependencies', 
        '/_dash-component-suites/',
        '/_dash-update-component',
        '_reload-hash',
        '/assets/', 
        '/_favicon.ico', 
        '/static/',
        '/health',
        '/_resources',
        '/portal'
    ]
    
    if any(x in path for x in static_paths):
        return None
    
    print(f"🚨 IMMEDIATE AUTH CHECK: {request.path}")
    print(f"🚨 Host: {request.host}")
    print(f"🚨 Environment: {os.environ.get('DASH_ENV')}")
    
    # Check environment
    dash_env = os.environ.get('DASH_ENV', '').lower()
    
    # CRITICAL: In development mode, bypass ALL authentication
    if dash_env == 'development':
        print("🚨 Development mode - bypassing ALL immediate auth")
        return None
    
    # Production mode - check authentication
    if (dash_env == 'production' or not dash_env) and request.host and 'data.energyintel.com' in request.host:
        print("🚨 PRODUCTION + data.energyintel.com - checking auth")
        
        # Check for embedded access (stricter check)
        is_embedded_access = False
        if request.referrer:
            ref_low = request.referrer.lower()
            if ('energyintel.com' in ref_low or 'www.energyintel.com' in ref_low) and \
               'data.energyintel.com' not in ref_low:
                is_embedded_access = True
        
        if is_embedded_access:
            print(f"🚨 Embedded access from {request.referrer} - allowing")
            return None
        
        # Check for tokens
        production_tokens = ['pelcro.user.auth.token', 'kcToken', 'kcIdToken']
        tokens_found = 0
        
        for token_name in production_tokens:
            token_value = request.cookies.get(token_name)
            if token_value and len(token_value) > 10:
                tokens_found += 1
        
        print(f"🚨 Tokens found: {tokens_found}")
        
        if tokens_found == 0:
            print("🚨 NO TOKENS - IMMEDIATE BLOCK")
            portal_url = os.environ.get('PORTAL_URL', 'https://data.energyintel.com').rstrip('/') + "/portal"
            print(f"🚨 IMMEDIATE REDIRECT TO: {portal_url}")
            return redirect(portal_url)
    
    return None

# Force use of custom TokenAuth for testing overlay functionality
# This will replace EmbeddedAuth with our custom authentication that includes overlay
if enable_auth:
    # Use custom TokenAuth for testing overlay functionality
    from auth import init_auth
    _auth_instance = init_auth(app)
    # Store auth instance reference for utils to access
    server._auth_instance = _auth_instance
    print("DEBUG: Using custom TokenAuth with overlay functionality")
elif is_embedded:
    # For now, also use custom TokenAuth in embedded mode for testing
    from auth import init_auth
    _auth_instance = init_auth(app)
    # Store auth instance reference for utils to access
    server._auth_instance = _auth_instance
    print("DEBUG: Using custom TokenAuth in embedded mode for testing")
else:
    # No authentication - store None to indicate auth is disabled
    server._auth_instance = None
    print("DEBUG: Authentication disabled")
