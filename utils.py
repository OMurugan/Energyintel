import os

# Specify the deployed URL path where the Dash app will be embedded
# on the host application.
# For example, if the Dash app is embedded on https://acme.com/analytics, then this would be '/analytics'.
# If the Dash app is embedded on the "home page" at https://acme.com/, then this would be `/`.
HOST_APP_PATHNAME = os.environ.get('HOST_APP_PATHNAME', '/')

def get_relative_path(path):
    """
    Return a path that is prefixed with the app's requests_pathname_prefix.
    Use this method when specifying the `href` in `dcc.Link` or `html.A`.
    This is the standard Dash function for handling relative paths in embedded contexts.
    """
    from app_instance import app
    return app.get_relative_path(path)


def strip_relative_path(path):
    """
    Strip the app's requests_pathname_prefix from the beginning of the path.
    Use this method when parsing `pathname` supplied by the `dcc.Location` component.
    This is the standard Dash function for handling relative paths in embedded contexts.
    """
    from app_instance import app
    return app.strip_relative_path(path)


# work arounds for handling the redirect of pages in dash-app
def get_host_relative_path(path):
    """
     Return a path that is prefixed with `HOST_APP_PATHNAME`.
     Use this method when specifying the `href` in `dcc.Link` or `html.A`.
     ```
     # Consider HOST_APP_PATHNAME='/analytics'
     >>> get_host_relative_path('/weekly-report')
     '/analytics/weekly-report'
     >>> get_host_relative_path('/weekly-report/monday/')
     'analytics/weekly-report/monday'
     ```
     """
    if HOST_APP_PATHNAME == "/" and path == "":
        return "/"
    elif HOST_APP_PATHNAME != "/" and path == "":
        return HOST_APP_PATHNAME
    elif not path.startswith("/"):
        raise Exception(
            "Paths that aren't prefixed with a leading / are not supported.\n"
            + "You supplied: {}".format(path)
        )
    return "/".join([HOST_APP_PATHNAME.rstrip("/"), path.lstrip("/")])

def strip_host_relative_path(path):
    """
     Strip the `HOST_APP_PATHNAME` from the beginning of the path.
     Use this method when parsing `pathname` supplied by the `dcc.Location` component.
     ```
     # Consider HOST_APP_PATHNAME='/analytics'
     >>> strip_host_relative_path('/analytics/weekly-report')
     'weekly-report'
     >>> strip_host_relative_path('/analytics/weekly-report/monday/')
     'weekly-report/monday'
     >>> strip_host_relative_path(None)
     None
     ```
     """
    if path is None:
        return None
    elif (
        HOST_APP_PATHNAME != "/" and not path.startswith(HOST_APP_PATHNAME.rstrip("/"))
    ) or (HOST_APP_PATHNAME == "/" and not path.startswith("/")):
        raise Exception(
            "Paths that aren't prefixed with a leading "
            + "HOST_APP_PATHNAME are not supported.\n"
            + "You supplied: {} and HOST_APP_PATHNAME was {}".format(
                path, HOST_APP_PATHNAME
            )
        )
    elif HOST_APP_PATHNAME != "/" and path.startswith(HOST_APP_PATHNAME.rstrip("/")):
        path = path.replace(
            # handle the case where the path might be `/my-dash-app`
            # but the HOST_APP_PATHNAME is `/my-dash-app/`
            HOST_APP_PATHNAME.rstrip("/"),
            "",
            1,
        )
        return path.strip("/")
    else: return path.strip("/")

def embedded_asset_url(resource):
    """
    Return a complete URL that specifies the location of a file (resource) inside
    the assets folder of your Dash app.
    Use this method when constructing any path that uses a file from assets, like the `src` attribute of
    `html.Img`
    ```
    # If the Dash app was deployed on a Dash Enterprise instance with the domain dash.acme.com
    # and the name of the app was "weekly-report"
    >>> embedded_asset_url('logo.png')
    https://dash.acme.com/weekly-report/assets/logo.png
    ```
    """
    if 'DASH_DOMAIN_BASE' in os.environ:
        # Assume the app is deployed or in a workspace
        if os.getenv('DASH_ENTERPRISE_ENV', '').upper() == 'WORKSPACE':
            # Get asset URL from the app running inside the workspace
            asset_str = 'https://{domain}/workspace/view/workspace-{app_name}/assets/{resource}'
        else:
            asset_str = 'https://{domain}/{app_name}/assets/{resource}'
        return asset_str.format(
            domain=os.environ['DASH_DOMAIN_BASE'],
            app_name=os.environ['DASH_APP_NAME'],
            resource=resource
        )
    # Assume running on localhost:8050
    # This will not work when running locally with gunicorn unless
    # you use `gunicorn app:server -b localhost:8050`
    return 'http://localhost:8050/assets/{resource}'.format(
        resource=resource
    )


# ============================================================================
# EMBEDDED MODE DETECTION
# ============================================================================

def is_embedded_mode():
    """
    Detect if the app is running in embedded mode.
    This checks for various indicators of embedded usage.
    
    Returns:
        True if running in embedded mode, False otherwise
    """
    try:
        from flask import request
        
        # Check for embedded-specific headers or referrers
        if request:
            # Check if request comes from an iframe or embedded context
            referer = request.headers.get('Referer', '')
            user_agent = request.headers.get('User-Agent', '')
            
            # Check for embedded indicators
            if 'dash-embedded' in user_agent.lower():
                return True
            
            # Check if referer is from a different domain (indicating embedding)
            if referer and not referer.startswith(request.host_url):
                return True
            
            # Check for specific embedded query parameters
            if request.args.get('embedded') == 'true':
                return True
                
            # Check for X-Forwarded-For or other proxy headers that might indicate embedding
            if request.headers.get('X-Embedded-Mode') == 'true':
                return True
            
            # Check for iframe-specific headers
            if request.headers.get('Sec-Fetch-Dest') == 'iframe':
                return True
                
    except (RuntimeError, AttributeError):
        # Outside of request context or Flask not available
        pass
    
    # Check environment variable for embedded mode
    return os.environ.get('EMBEDDED_MODE', 'false').lower() == 'true'


def set_embedded_mode(enabled=True):
    """
    Programmatically set embedded mode.
    
    Args:
        enabled: True to enable embedded mode, False to disable
    """
    os.environ['EMBEDDED_MODE'] = 'true' if enabled else 'false'


# ============================================================================
# EMBEDDED AUTHENTICATION UTILITIES
# ============================================================================

def get_auth_instance():
    """
    Get the authentication instance from the app.
    Returns None if authentication is not enabled.
    """
    try:
        from app_instance import app
        return getattr(app.server, '_auth_instance', None)
    except (ImportError, AttributeError):
        return None


def is_authenticated():
    """
    Check if the current user is authenticated in token-based context.
    Returns True if authenticated, False otherwise.
    """
    auth = get_auth_instance()
    if auth is None:
        # Authentication not enabled, allow access
        return True
    
    try:
        from flask import g
        return hasattr(g, 'current_user') and g.current_user is not None
    except RuntimeError:
        # Outside of request context
        return False


def get_current_user():
    """
    Get the current authenticated user in token-based context.
    Returns username if authenticated, None otherwise.
    """
    auth = get_auth_instance()
    if auth is None:
        return None
    
    try:
        from flask import g
        return getattr(g, 'current_user', None)
    except RuntimeError:
        # Outside of request context
        return None


def get_auth_login_url(next_path=None):
    """
    Get the authentication URL for token-based auth.
    Since we use tokens, this returns info about token usage.
    
    Args:
        next_path: Optional path to redirect to after auth
        
    Returns:
        Info URL about token authentication
    """
    base_url = get_relative_path('/')
    if next_path:
        return f"{base_url}?token=your-token-here&next={get_relative_path(next_path)}"
    else:
        return f"{base_url}?token=your-token-here"


def get_auth_logout_url():
    """
    Get the logout URL for token-based authentication.
    For token auth, this just removes the token parameter.
    
    Returns:
        Base URL without token
    """
    return get_relative_path('/')


def require_auth_embedded(redirect_to_login=True):
    """
    Decorator to require authentication for embedded Dash callbacks.
    Updated for token-based authentication.
    
    Args:
        redirect_to_login: If True, prevent update. If False, raise exception.
        
    Usage:
        @require_auth_embedded()
        @app.callback(...)
        def my_callback(...):
            # This callback requires authentication
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not is_authenticated():
                if redirect_to_login:
                    from dash import no_update
                    from dash.exceptions import PreventUpdate
                    # In embedded context, we can't redirect directly
                    # The parent application should handle authentication
                    raise PreventUpdate
                else:
                    raise PermissionError("Authentication token required")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def get_user_permissions():
    """
    Get permissions for the current authenticated user.
    Returns a list of permissions or empty list if not authenticated.
    """
    auth = get_auth_instance()
    if auth is None:
        return ['read', 'write', 'admin']  # Default permissions when auth disabled
    
    try:
        from flask import g
        return getattr(g, 'user_permissions', [])
    except RuntimeError:
        # Outside of request context
        return []


def has_permission(permission_name):
    """
    Check if the current user has a specific permission.
    
    Args:
        permission_name: Name of the permission to check
        
    Returns:
        True if user has permission, False otherwise
    """
    permissions = get_user_permissions()
    return permission_name in permissions or 'admin' in permissions


def get_embedded_auth_status():
    """
    Get comprehensive authentication status for token-based context.
    
    Returns:
        Dictionary containing authentication information:
        {
            'is_authenticated': bool,
            'user': str or None,
            'permissions': list,
            'login_url': str,
            'logout_url': str,
            'auth_method': str
        }
    """
    return {
        'is_authenticated': is_authenticated(),
        'user': get_current_user(),
        'permissions': get_user_permissions(),
        'login_url': get_auth_login_url(),
        'logout_url': get_auth_logout_url(),
        'auth_method': 'token'
    }


def create_auth_component():
    """
    Create a Dash component that displays token-based authentication status.
    Useful for embedding in page layouts.
    Only shows authentication UI when authentication is enabled.
    
    Returns:
        Dash HTML component showing auth status, or empty div if auth disabled
    """
    from dash import html, dcc
    
    # Check if authentication is enabled
    auth_enabled = os.environ.get('ENABLE_AUTH', 'false').lower() == 'true'
    
    if not auth_enabled:
        # Authentication is disabled, return empty component
        return html.Div()
    
    auth_status = get_embedded_auth_status()
    
    if auth_status['is_authenticated']:
        permissions_text = ', '.join(auth_status['permissions']) if auth_status['permissions'] else 'None'
        return html.Div([
            html.Span(f"🔑 Authenticated as: {auth_status['user']}", 
                     style={'marginRight': '15px', 'color': '#28a745', 'fontWeight': 'bold'}),
            html.Span(f"Permissions: {permissions_text}", 
                     style={'marginRight': '15px', 'color': '#6c757d', 'fontSize': '12px'}),
            html.Span("(Token-based auth)", 
                     style={'color': '#6c757d', 'fontSize': '11px', 'fontStyle': 'italic'})
        ], style={'padding': '10px', 'backgroundColor': '#d4edda', 'borderRadius': '4px', 'border': '1px solid #c3e6cb'})
    else:
        return html.Div([
            html.Span("🔒 Token authentication required", 
                     style={'marginRight': '10px', 'color': '#dc3545', 'fontWeight': 'bold'}),
            html.Span("Add ?token=your-token to URL", 
                     style={'color': '#6c757d', 'fontSize': '12px', 'fontStyle': 'italic'})
        ], style={'padding': '10px', 'backgroundColor': '#f8d7da', 'borderRadius': '4px', 'border': '1px solid #f5c6cb'})


# ============================================================================
# EMBEDDED NAVIGATION UTILITIES
# ============================================================================

def create_embedded_nav_link(path, text, **kwargs):
    """
    Create a navigation link that works properly in embedded context.
    
    Args:
        path: The path to link to
        text: The link text
        **kwargs: Additional properties for the Link component
        
    Returns:
        dcc.Link component with proper embedded path handling
    """
    from dash import dcc
    
    default_style = {
        'padding': '8px 12px', 
        'textDecoration': 'none',
        'color': '#007bff'
    }
    
    # Merge provided style with defaults
    style = kwargs.pop('style', {})
    final_style = {**default_style, **style}
    
    return dcc.Link(
        text,
        href=get_relative_path(path),
        style=final_style,
        refresh=True,  # Force full navigation for embedded context
        **kwargs
    )


def get_page_breadcrumbs(current_path):
    """
    Generate breadcrumb navigation for the current page.
    
    Args:
        current_path: Current page path
        
    Returns:
        List of breadcrumb items
    """
    from dash import html
    
    # Strip the relative path to get clean path
    clean_path = strip_relative_path(current_path) or ""
    
    # Split path into segments
    segments = [seg for seg in clean_path.split('/') if seg]
    
    breadcrumbs = [
        html.A('Home', href=get_relative_path('/'), 
               style={'textDecoration': 'none', 'color': '#007bff'})
    ]
    
    # Build breadcrumbs for each segment
    current_path_build = ""
    for segment in segments:
        current_path_build += f"/{segment}"
        breadcrumbs.append(html.Span(' / ', style={'margin': '0 5px'}))
        breadcrumbs.append(
            html.A(segment.replace('-', ' ').title(), 
                   href=get_relative_path(current_path_build),
                   style={'textDecoration': 'none', 'color': '#007bff'})
        )
    
    return html.Div(breadcrumbs, style={'padding': '10px', 'fontSize': '14px'})


# ============================================================================
# ROUTING UTILITIES FOR HOST APP INTEGRATION
# ============================================================================

def display_content(pathname):
    """
    Handle routing for both embedded and standalone modes.
    
    When called from the host app (CMS), it strips the "/wcod-country" suffix from the path.
    When accessed directly (run locally or through dash enterprise), it retains "/wcod-country" prefix.
    
    Args:
        pathname: The current URL pathname
        
    Returns:
        Processed pathname for routing
    """
    if pathname is None:
        return "/"
    
    # Check if we're in embedded mode (called from host app)
    if is_embedded_mode():
        # Strip "/wcod-country" suffix if present when embedded
        if pathname.endswith("/wcod-country"):
            return pathname[:-len("/wcod-country")] or "/"
        # Also handle cases where the path might be just "/wcod-country"
        elif pathname == "/wcod-country":
            return "/"
    
    # For standalone mode (direct access), keep the original path
    return pathname


def get_wcod_country_path(base_path):
    """
    Generate the appropriate path for wcod-country pages based on mode.
    
    Args:
        base_path: The base path (e.g., "/country-overview")
        
    Returns:
        Full path with or without wcod-country suffix based on mode
    """
    if is_embedded_mode():
        # In embedded mode, don't add the suffix
        return base_path
    else:
        # In standalone mode, add the suffix if not already present
        if not base_path.endswith("/wcod-country"):
            # Handle root path specially
            if base_path == "/":
                return "/wcod-country"
            else:
                return f"{base_path}/wcod-country"
        return base_path
