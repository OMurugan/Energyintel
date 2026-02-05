"""
Single Dash application entry point using Dash Pages.
All routing is handled via dash.page_container and page modules in /pages.
Uses EmbeddedAuth for authentication like the client demo.
"""

import builtins
import logging
import os
import sys
from dotenv import load_dotenv

from core.raw_data import load_all_data


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

# Initialize authentication based on ENABLE_AUTH and EMBEDDED_MODE environment variables
enable_auth = os.getenv("ENABLE_AUTH", "false").lower() == "true"
embedded_mode = os.getenv("EMBEDDED_MODE", "false").lower() == "true"
dash_env = os.getenv("DASH_ENV", "").lower()

print(f"DEBUG: Authentication Configuration:")
print(f"DEBUG: - ENABLE_AUTH: {enable_auth}")
print(f"DEBUG: - EMBEDDED_MODE: {embedded_mode}")
print(f"DEBUG: - DASH_ENV: '{dash_env}'")

if enable_auth and embedded_mode:
    print("DEBUG: MODE: EMBEDDED AUTHENTICATION (ENABLE_AUTH=true, EMBEDDED_MODE=true)")
    print("DEBUG: - JWT Bearer token authentication required")
    print("DEBUG: - Only embedded applications with valid JWT can access")
    
    # Use EmbeddedAuth for embedded JWT authentication
    from dash_embedded import EmbeddedAuth
    
    secret_key = os.getenv("EMBEDDED_SECRET_KEY", "secret_key")
    claims = {"iss": "DASH EMBEDDED"}
    
    # Initialize EmbeddedAuth for embedded access
    auth = EmbeddedAuth([app], secret_key, claims, algorithm="HS512")
    
    print("DEBUG: EmbeddedAuth initialized successfully")
    print(f"DEBUG: Secret key: {'*' * len(secret_key)}")
    print(f"DEBUG: Claims: {claims}")
    
elif enable_auth and not embedded_mode:
    print("DEBUG: MODE: DIRECT AUTHENTICATION (ENABLE_AUTH=true, EMBEDDED_MODE=false)")
    print("DEBUG: - Dash Enterprise user authentication")
    print("DEBUG: - Users must be logged into Dash Enterprise")
    print("DEBUG: - Direct access to https://data.energyintel.com/wcod-country/ allowed")
    
    # Use custom authentication for direct access
    from auth import TokenAuth
    auth = TokenAuth(app)
    
    print("DEBUG: Direct access authentication initialized")
    
elif not enable_auth and embedded_mode:
    print("DEBUG: MODE: EMBEDDED NO AUTH (ENABLE_AUTH=false, EMBEDDED_MODE=true)")
    print("DEBUG: - Embedded mode without authentication")
    print("DEBUG: - All embedded requests allowed without JWT")
    print("DEBUG: WARNING: This mode provides no security - use only for testing")
    
    # No authentication but still embedded mode
    print("DEBUG: No authentication initialized - embedded mode only")
    
elif not enable_auth and not embedded_mode:
    print("DEBUG: MODE: OPEN ACCESS (ENABLE_AUTH=false, EMBEDDED_MODE=false)")
    print("DEBUG: - No authentication required")
    print("DEBUG: - Direct access to https://data.energyintel.com/wcod-country/ allowed")
    print("DEBUG: - All users can access without authentication")
    print("DEBUG: WARNING: This mode provides no security - use only for testing or internal networks")
    
    # No authentication at all
    print("DEBUG: No authentication initialized - open access mode")
    
else:
    # Fallback based on DASH_ENV for backward compatibility
    if dash_env == "production":
        print("DEBUG: FALLBACK: PRODUCTION MODE - Initializing EmbeddedAuth")
        
        from dash_embedded import EmbeddedAuth
        
        secret_key = os.getenv("EMBEDDED_SECRET_KEY", "secret_key")
        claims = {"iss": "DASH EMBEDDED"}
        
        auth = EmbeddedAuth([app], secret_key, claims, algorithm="HS512")
        print("DEBUG: Fallback EmbeddedAuth initialized")
        
    elif dash_env == "development":
        print("DEBUG: FALLBACK: DEVELOPMENT MODE - All authentication disabled")
        print("DEBUG: All requests allowed without authentication checks")
    else:
        print(f"DEBUG: FALLBACK: Unknown environment '{dash_env}' - defaulting to no auth")
        print("DEBUG: No authentication initialized")

# Import index to register layout, navigation, and callbacks
import index  # noqa: E402,F401

if __name__ == "__main__":
    app.run(
        debug=os.getenv("DASH_DEBUG"),
        port=os.getenv("PORT"),
        host=os.getenv("HOST", "0.0.0.0"),
    )