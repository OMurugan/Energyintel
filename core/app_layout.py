"""
Main application layout
Adapted from wcod_dashboard for Dash Enterprise
"""
from app.dashboards.wcod_dashboard import create_wcod_dashboard

# Create the dashboard to get its layout
# Pass None for server to create standalone app
_wcod_dash = create_wcod_dashboard(server=None, url_base_pathname='/')

# Extract the layout
layout = _wcod_dash.layout

