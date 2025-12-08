"""
Single Dash application entry point using Dash Pages.
All routing is handled via dash.page_container and page modules in /pages.
"""

import os
import sys
from dotenv import load_dotenv

from core.raw_data import load_all_data

# Load environment variables from .env file
load_dotenv()

# Load data at startup and fail fast on connection errors
try:
    load_all_data()
except Exception as e:
    print(f"Database connection error: {e}")
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
