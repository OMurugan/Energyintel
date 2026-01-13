"""
Shared Dash application instance for Dash Pages.
This module avoids name collisions with the existing app/ package.
"""

import os
from dash import Dash
import dash_bootstrap_components as dbc
from dash_embedded import Embeddable

# Get configuration from environment
requests_pathname_prefix = os.environ.get('DASH_ROUTES_PATHNAME_PREFIX', '/')
host_app_origin = os.environ.get('HOST_APP_ORIGIN', 'http://127.0.0.1:8001')

# Single global Dash instance with Dash Pages enabled
app = Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",  # explicitly point to the pages package
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    plugins=[Embeddable(origins=[host_app_origin, 'localhost:8001', '127.0.0.1:8001'])],  # Support multiple origins
    requests_pathname_prefix=requests_pathname_prefix,
)

# Expose server for gunicorn
server = app.server

# Initialize authentication (optional - can be disabled via env var)
_auth_instance = None
if os.environ.get('ENABLE_AUTH', 'false').lower() == 'true':
    from auth import init_auth
    _auth_instance = init_auth(app)
    # Store auth instance reference for utils to access
    server._auth_instance = _auth_instance
