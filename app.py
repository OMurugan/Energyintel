"""
Main Dash Enterprise application entry point
Migrated from Flask-based Dash implementation
"""
import os
from dotenv import load_dotenv
from dash_embedded import Embeddable
from core.raw_data import load_all_data
from app.dashboards.wcod_dashboard import create_wcod_dashboard

# Load environment variables from .env file
load_dotenv()

# Load data at startup
load_all_data()

# ======================= Dash App =======================
# Create the WCoD dashboard (which creates the Dash app)
# Pass None for server to create standalone app
app = create_wcod_dashboard(server=None, url_base_pathname='/')

# Add Dash Enterprise embedding support
app.plugins = [Embeddable(origins="*")]

# Expose server for gunicorn
server = app.server

if __name__ == "__main__":
    app.run(
        debug=os.getenv("DASH_DEBUG"),
        port=os.getenv("PORT"),
        host=os.getenv("HOST"),
    )
