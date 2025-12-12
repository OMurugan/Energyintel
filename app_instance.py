"""
Shared Dash application instance for Dash Pages.
This module avoids name collisions with the existing app/ package.
"""

from dash import Dash
import dash_bootstrap_components as dbc
from dash_embedded import Embeddable

# Single global Dash instance with Dash Pages enabled
app = Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",  # explicitly point to the pages package
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    plugins=[Embeddable(origins="*")],
)

# Expose server for gunicorn
server = app.server
