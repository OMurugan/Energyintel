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
    filename="energy.log",
    filemode="a",
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
