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

# Configure logging early
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Redirect any leftover print statements to logging so legacy code is captured.
_orig_print = builtins.print


def _redirect_print(*args, **kwargs):
    msg = " ".join(str(a) for a in args)
    lvl = logging.INFO
    lower = msg.lower().lstrip()
    if lower.startswith(("debug", "dbg")):
        lvl = logging.DEBUG
    elif lower.startswith(("warning", "warn")):
        lvl = logging.WARNING
    elif lower.startswith(("error", "err", "exception")):
        lvl = logging.ERROR
    elif lower.startswith(("critical", "fatal")):
        lvl = logging.CRITICAL
    logger.log(lvl, msg)


builtins.print = _redirect_print

# Load environment variables from .env file
load_dotenv()

# Load data at startup and fail fast on connection errors
try:
    load_all_data()
except Exception:
    logger.exception("Database connection error during startup")
    sys.exit(1)

# Import the shared Dash instance
from app_instance import app, server  # noqa: E402

# Import index to register layout, navigation, and callbacks
import index  # noqa: E402,F401

if __name__ == "__main__":
    app.run(
        debug=os.getenv("DASH_DEBUG"),
        port=os.getenv("PORT"),
        host=os.getenv("HOST", "0.0.0.0"),
    )
