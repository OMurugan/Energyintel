"""
Exports Dashboard
Focused view on export metrics
"""
import dash
from dash import dcc, html, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from core.data_helpers import execute_query
from datetime import datetime, timedelta


def create_exports_dashboard(dash_app, server, url_base_pathname):
    """Create exports-focused dashboard"""
    # dash_app = dash.Dash(
    #     __name__,
    #     server=server,
    #     url_base_pathname=url_base_pathname,
    #     external_stylesheets=[
    #         'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
    #         'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
    #     ],
    #     suppress_callback_exceptions=True
    # )

    dash_app.layout = create_layout()
    register_callbacks(dash_app, server)

