"""
Single Dash application entry point using Dash Pages.
All routing is handled via dash.page_container and page modules in /pages.
"""

import builtins
import logging
import os
import sys
from dotenv import load_dotenv

from core.raw_data import load_all_data
from dash_embedded import EmbeddedAuth


# Configure logging early
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    # filename="energy.log",
    # filemode="a",
)
logger = logging.getLogger(__name__)


# Redirect any leftover print statements to logging so legacy code is captured.
_orig_print = builtins.print


def _redirect_print(*args, **kwargs):
    # If print is targeting a non-stdout/stderr file (e.g., logging's StringIO),
    # bypass redirection to avoid duplicating traceback lines.
    target = kwargs.get("file")
    if target is not None and target not in (sys.stdout, sys.stderr):
        return _orig_print(*args, **kwargs)

    # Always print to stdout/stderr first so output is immediately visible
    _orig_print(*args, **kwargs)
    
    # Also log the message for log file capture
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "")
    msg = sep.join(str(a) for a in args) + end
    msg = msg.rstrip("\n")
    lvl = logging.INFO
    lower = msg.lower().lstrip()
    if lower.startswith(("debug", "dbg")):
        lvl = logging.DEBUG
    elif lower.startswith(("warning", "warn")):
        lvl = logging.WARNING
    elif lower.startswith(("error", "err", "exception", "traceback")):
        lvl = logging.ERROR
    elif lower.startswith(("critical", "fatal")):
        lvl = logging.CRITICAL
    logger.log(lvl, msg)


builtins.print = _redirect_print

# Load environment variables from .env file
load_dotenv()

# Load data at startup. If DB is unreachable, log and continue so CSV-backed
# pages can still work.
try:
    load_all_data()
except Exception as e:
    logger.error("Startup data load failed (continuing without DB): %s", e)

# Import the shared Dash instance
from app_instance import app, server  # noqa: E402

# 🚨🚨🚨 CRITICAL: EMERGENCY AUTHENTICATION FIX 🚨🚨🚨
# This MUST run and WILL block unauthorized access
print("🚨🚨🚨 APPLYING EMERGENCY AUTHENTICATION FIX 🚨🚨🚨")

@server.before_request
def EMERGENCY_AUTH_BLOCK():
    """EMERGENCY AUTHENTICATION - BLOCKS ALL UNAUTHORIZED ACCESS"""
    from flask import request, redirect
    
    # Skip static assets and whitelisted paths
    if request.path.startswith(('/_dash-', '/assets/', '/static/', '/_favicon.ico', '/health', '/portal')):
        return None
    
    # Get environment - default to production for security
    dash_env = os.environ.get('DASH_ENV', 'production').lower()
    
    print(f"🚨🚨🚨 EMERGENCY AUTH CHECK 🚨🚨🚨")
    print(f"🚨 Path: {request.path}")
    print(f"🚨 Host: {request.host}")
    print(f"🚨 Environment: {dash_env}")
    print(f"🚨 Method: {request.method}")
    print(f"🚨 Cookies: {dict(request.cookies)}")
    
    # CRITICAL: In development mode, bypass ALL authentication
    if dash_env == 'development':
        print("🚨 DEVELOPMENT MODE - BYPASSING ALL EMERGENCY AUTH")
        return None
    
    # For production, check authentication
    if request.host and 'data.energyintel.com' in request.host:
        print("🚨 PRODUCTION ACCESS TO data.energyintel.com")
        
        # Check for embedded access (stricter check)
        is_embedded = False
        if request.referrer:
            ref_low = request.referrer.lower()
            if ('energyintel.com' in ref_low or 'www.energyintel.com' in ref_low) and \
               'data.energyintel.com' not in ref_low:
                is_embedded = True
        
        if is_embedded:
            print(f"🚨 EMBEDDED ACCESS from {request.referrer} - ALLOWING")
            return None
        
        # Check for authentication tokens
        tokens = []
        
        # Check cookies
        cookie_tokens = ['pelcro.user.auth.token', 'kcToken', 'kcIdToken']
        for cookie_name in cookie_tokens:
            token_value = request.cookies.get(cookie_name)
            if token_value and len(token_value) > 10:
                tokens.append(f"cookie:{cookie_name}")
        
        # Check headers
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer ') and len(auth_header) > 20:
            tokens.append("header:Authorization")
        
        # Check query parameters
        query_token = request.args.get('token')
        if query_token and len(query_token) > 10:
            tokens.append("query:token")
        
        print(f"🚨 TOKENS FOUND: {tokens}")
        
        if len(tokens) == 0:
            print("🚨🚨🚨 NO TOKENS - EMERGENCY BLOCK 🚨🚨🚨")
            portal_url = "https://data.energyintel.com/portal"
            print(f"🚨🚨🚨 EMERGENCY REDIRECT TO: {portal_url} 🚨🚨🚨")
            return redirect(portal_url, code=302)
        else:
            print(f"🚨 FOUND {len(tokens)} TOKENS - ALLOWING ACCESS")
            return None
    
    # For all other hosts, allow
    print("🚨 NON-PRODUCTION HOST - ALLOWING")
    return None

print("🚨🚨🚨 EMERGENCY AUTHENTICATION FIX APPLIED 🚨🚨🚨")

# Skip EmbeddedAuth initialization for testing custom TokenAuth overlay functionality
# if os.getenv("IS_EMBEDDED"):
#     secret_key = os.getenv("EMBEDDED_SECRET_KEY", "secret_key")
#     claims = {"iss": "DASH EMBEDDED"}
#     auth = EmbeddedAuth([app], secret_key, claims, algorithm="HS512")

# Import index to register layout, navigation, and callbacks
import index  # noqa: E402,F401

if __name__ == "__main__":
    app.run(
        debug=os.getenv("DASH_DEBUG"),
        port=os.getenv("PORT"),
        host=os.getenv("HOST", "0.0.0.0"),
    )