"""
Shared Dash application instance for Dash Pages.
This module avoids name collisions with the existing app/ package.
"""

import os
from typing import Optional

from dash import Dash
import dash_bootstrap_components as dbc
from dash_embedded import Embeddable


def _normalize_prefix(raw_prefix: Optional[str]) -> str:
    """Return a routes prefix that starts/ends with '/' or empty if not set."""
    if not raw_prefix:
        return ""
    prefix = raw_prefix.strip()
    if not prefix:
        return ""
    if not prefix.startswith("/"):
        prefix = f"/{prefix}"
    if not prefix.endswith("/"):
        prefix = f"{prefix}/"
    return prefix


# Read optional prefix for link generation only (not for Dash binding)
_raw_prefix = os.getenv("DASH_ROUTES_PATHNAME_PREFIX", "")
ROUTES_PREFIX = _normalize_prefix(_raw_prefix)

# Remove env vars so Dash always binds at root and avoids invalid values.
os.environ.pop("DASH_ROUTES_PATHNAME_PREFIX", None)
os.environ.pop("DASH_REQUESTS_PATHNAME_PREFIX", None)

# Single global Dash instance with Dash Pages enabled
app = Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",  # explicitly point to the pages package
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    plugins=[Embeddable(origins="*")],
    # Force root binding; prefix is handled only in generated links.
    routes_pathname_prefix="/",
    requests_pathname_prefix=None,
)

# Expose server for gunicorn
server = app.server


