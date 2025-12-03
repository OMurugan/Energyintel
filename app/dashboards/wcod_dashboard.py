"""
World Crude Oil Data (WCoD) Dashboard
Comprehensive dashboard with all tabs and sub-menus matching Energy Intelligence website
Migrated to standalone Dash Enterprise application
"""
import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
from dash_embedded import Embeddable
from urllib.parse import parse_qs
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ======================= URL Helper Functions =======================
def get_base_url():
    """
    Get the base URL for the application
    Constructs: http(s)://HOST or http(s)://HOST:PORT (if PORT is set)
    
    Returns:
        str: Base URL (e.g., 'http://127.0.0.1:5000' or 'http://127.0.0.1')
    """
    protocol = os.getenv('PROTOCOL', 'http')  # http or https
    host = os.getenv('HOST', '127.0.0.1')
    port = os.getenv('PORT', '').strip()  # Get PORT, strip whitespace
    
    # Remove protocol from host if it's already included
    if host.startswith('http://') or host.startswith('https://'):
        return host
    
    # Construct full URL - only include port if it's set
    if port:
        return f"{protocol}://{host}:{port}"
    else:
        return f"{protocol}://{host}"


def get_absolute_url(path):
    """
    Convert a relative path to an absolute URL
    
    Args:
        path: Relative path (e.g., '/wcod/', '/assets/images/globe_inactive.svg')
    
    Returns:
        str: Absolute URL (e.g., 'http://127.0.0.1:5000/wcod/')
    """
    base_url = get_base_url()
    # Ensure path starts with /
    if not path.startswith('/'):
        path = '/' + path
    return f"{base_url}{path}"


def get_link_href(path):
    """
    Get href for dcc.Link components
    For internal navigation in embedded Dash apps, use relative paths.
    The Dash embedded component handles internal routing.
    
    Args:
        path: Relative path (e.g., '/wcod/', '/country-overview')
    
    Returns:
        str: Relative path (e.g., '/wcod/')
    """
    if not path.startswith('/'):
        path = '/' + path
    return path

# Import individual submenu modules
from app.dashboards.wcod import (
    country_overview,
    country_profile,
    crude_overview,
    crude_profile,
    crude_comparison,
    crude_quality,
    crude_carbon,
    imports_detail,
    imports_comparison,
    global_exports,
    russian_exports,
    global_prices,
    price_scorecard,
    gpw_margins,
    projects_by_country,
    projects_by_company,
    projects_by_time,
    projects_by_status,
    projects_latest,
    projects_tracker,
    projects_carbon
)


def create_wcod_dashboard(server=None, url_base_pathname='/'):
    """
    Create comprehensive WCoD dashboard with tab navigation
    Now works standalone without Flask server dependency
    """
    # Get base URL for absolute URLs
    base_url = get_base_url()
    
    # Create Dash app standalone
    # Get the root directory (where app.py is located) for assets
    from pathlib import Path
    root_dir = Path(__file__).parent.parent.parent  # Go up from app/dashboards/wcod_dashboard.py to root
    assets_dir = root_dir / 'assets'
    
    dash_app = dash.Dash(
        __name__,
        url_base_pathname=url_base_pathname,
        plugins=[Embeddable(origins="*")],  # Add embedding support with CORS
        external_stylesheets=[
            'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
            'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
        ],
        suppress_callback_exceptions=True,
        assets_folder=str(assets_dir)  # Explicitly set assets folder to root level
    )
    
    # If server is provided, attach to it (for backward compatibility)
    if server:
        dash_app.server = server
    
    # Add route to serve static assets from assets folder
    # Dash should handle this automatically, but we'll add explicit route as fallback
    from flask import send_from_directory
    import os
    
    @dash_app.server.route('/assets/<path:path>')
    def serve_assets(path):
        """Serve static assets from assets folder"""
        # Handle nested paths like images/globe_inactive.svg
        file_path = os.path.join(str(assets_dir), path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            return send_from_directory(directory, filename)
        else:
            # Try to serve from assets_dir directly
            return send_from_directory(str(assets_dir), path)
    
    # Custom CSS for Tableau-like styling
    dash_app.index_string = '''
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>World Crude Oil Data Dashboard</title>
            {%favicon%}
            {%css%}
            <style>
                body {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    background-color: #f5f5f5;
                }
                .tab-style1 {
                    padding: 0 30px;
                }
                .kpi-card {
                    background: white;
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin-bottom: 20px;
                }
                .kpi-value {
                    font-size: 32px;
                    font-weight: 600;
                    color: #2c3e50;
                }
                .kpi-label {
                    font-size: 14px;
                    color: #7f8c8d;
                    margin-top: 8px;
                }
                .tab-content {
                    padding: 20px;
                    background: white;
                    border-radius: 8px;
                    margin-top: 0;
                }
                .submenu-item {
                    padding: 10px 15px;
                    margin: 5px;
                    background: #f8f9fa;
                    border-radius: 4px;
                    cursor: pointer;
                    transition: background 0.3s;
                }
                .submenu-item:hover {
                    background: #e9ecef;
                }
                .submenu-item.active {
                    background: #1b365d;
                    color: white;
                }
                /* Tab styling for Image 1 design - pixel perfect */
                #tab-link-country, #tab-link-crude, #tab-link-trade, 
                #tab-link-prices, #tab-link-projects, #tab-link-methodology {
                    display: inline-block;
                    background: #e5e5e5;
                    border-radius: 8px 8px 0 0;
                    margin-bottom: 0;
                    position: relative;
                    z-index: 1;
                }
                /* Icon styling */
                #tab-icon-country, #tab-icon-crude, #tab-icon-trade, #tab-icon-prices {
                    flex-shrink: 0;
                    object-fit: contain;
                }
                /* Ensure tab container has proper background */
                .tab-container {
                    background: #e5e5e5;
                    padding: 8px 8px 0 8px;
                }
                /* WCoD Header gradient background with wave patterns */
                #header-container > div:last-child {
                    position: relative;
                }
                #header-container > div:last-child::before {
                    content: '';
                    position: absolute;
                    bottom: 0;
                    left: 0;
                    width: 300px;
                    height: 150px;
                    background: 
                        radial-gradient(ellipse at 20% 80%, rgba(255,255,255,0.15) 0%, transparent 50%),
                        radial-gradient(ellipse at 60% 90%, rgba(255,255,255,0.1) 0%, transparent 50%);
                    opacity: 0.4;
                    pointer-events: none;
                }
                #header-container > div:last-child::after {
                    content: '';
                    position: absolute;
                    bottom: 0;
                    right: 0;
                    width: 300px;
                    height: 150px;
                    background: 
                        radial-gradient(ellipse at 80% 80%, rgba(255,255,255,0.15) 0%, transparent 50%),
                        radial-gradient(ellipse at 40% 90%, rgba(255,255,255,0.1) 0%, transparent 50%);
                    opacity: 0.4;
                    pointer-events: none;
                }

                .top-header .header-menu a {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                }

                /* Crude Quality Dashboard CSS */
                /* Support table scrolling - Dash handles sticky via DataTable props */
                #crude-quality-table .dash-table-container,
                #yield-volume-table .dash-table-container {
                    position: relative !important;
                    overflow-x: auto !important;
                }
                
                #crude-quality-table .dash-table-container .dash-spreadsheet-container,
                #yield-volume-table .dash-table-container .dash-spreadsheet-container {
                    overflow-x: auto !important;
                    overflow-y: auto !important;
                }
                
                #crude-quality-table table,
                #yield-volume-table table {
                    border-collapse: separate !important;
                    border-spacing: 0 !important;
                    width: 100% !important;
                }
                
                /* Ensure proper table cell borders and spacing */
                #crude-quality-table td,
                #crude-quality-table th,
                #yield-volume-table td,
                #yield-volume-table th {
                    border: 1px solid #E6E6E6 !important;
                }
                
                /* Remove top border for empty country cells to create grouping effect */
                #crude-quality-table tbody tr td:first-child:empty,
                #yield-volume-table tbody tr td:first-child:empty {
                    border-top: none !important;
                }
                
                /* Ensure table rows have consistent spacing */
                #crude-quality-table tbody tr,
                #yield-volume-table tbody tr {
                    height: auto !important;
                }
                
                /* Ensure sticky columns maintain proper background */
                #crude-quality-table .dash-table-container table thead tr th:first-child,
                #crude-quality-table .dash-table-container table tbody tr td:first-child,
                #yield-volume-table .dash-table-container table thead tr th:first-child,
                #yield-volume-table .dash-table-container table tbody tr td:first-child {
                    background-color: white !important;
                }
                
                #crude-quality-table .dash-table-container table thead tr th:nth-child(2),
                #crude-quality-table .dash-table-container table tbody tr td:nth-child(2),
                #yield-volume-table .dash-table-container table thead tr th:nth-child(2),
                #yield-volume-table .dash-table-container table tbody tr td:nth-child(2) {
                    background-color: white !important;
                }
                
                /* === Slider Handle Styles === */
                .rc-slider-handle-1 {
                    width: 10px !important;
                    height: 14px !important;
                    background: #FFFFFF !important;
                    border: 2px solid #6E6E6E !important;
                    border-radius: 0 7px 7px 0 !important;
                    margin-top: -6px !important;
                    box-shadow: none !important;
                }

                .rc-slider-handle-2 {
                    width: 10px !important;
                    height: 14px !important;
                    background: #FFFFFF !important;
                    border: 2px solid #6E6E6E !important;
                    border-radius: 7px 0 0 7px !important;
                    margin-top: -6px !important;
                    box-shadow: none !important;
                }

                .rc-slider-handle {
                    width: 10px !important;
                    height: 14px !important;
                    background-color: #FFFFFF !important;
                    border: 2px solid #6E6E6E !important;
                    margin-top: -6px !important;
                    box-shadow: none !important;
                    cursor: pointer !important;
                }

                .rc-slider-handle-1 {
                    border-radius: 7px 0 0 7px !important;
                }
                .rc-slider-handle-2 {
                    border-radius: 0 7px 7px 0 !important;
                }

                .rc-slider-handle:hover {
                    border-color: #4D4D4D !important;
                }

                .rc-slider-handle:active {
                    border-color: #3A3A3A !important;
                }

                .rc-slider-track,
                .rc-slider-track-1,
                .rc-slider-track-2,
                div[class*="rc-slider-track"] {
                    background: #6E6E6E !important;
                    height: 4px !important;
                }

                .rc-slider-rail {
                    background: #D3D3D3 !important;
                    height: 4px !important;
                }

                .rc-slider-tooltip-inner {
                    background: #ffffff !important;
                    color: black !important;
                    border: 1px solid #999 !important;
                }

                /* Dropdown Styling */
                .Select-control {
                    font-size: 12px !important;
                    height: 22px !important;
                    min-height: 22px !important;
                    border-radius: 0 !important;
                }
                
                .Select-value-label {
                    font-size: 12px !important;
                    line-height: 20px !important;
                    color: rgb(27, 54, 93) !important;
                }
                
                .Select-input {
                    font-size: 12px !important;
                    height: 20px !important;
                    line-height: 20px !important;
                    color: rgb(27, 54, 93) !important;
                }
                
                .Select-input > input {
                    font-size: 12px !important;
                    line-height: 20px !important;
                    color: rgb(27, 54, 93) !important;
                }
                
                .Select-menu-outer {
                    font-size: 12px !important;
                    border-radius: 0 !important;
                }
                
                .Select-option {
                    font-size: 12px !important;
                    padding: 4px 10px !important;
                }
                
                .Select-placeholder {
                    font-size: 12px !important;
                    line-height: 20px !important;
                    color: rgb(27, 54, 93) !important;
                }
                
                .Select--single > .Select-control .Select-value {
                    font-size: 12px !important;
                    line-height: 20px !important;
                    color: rgb(27, 54, 93) !important;
                }
                
                .Select--single > .Select-control .Select-value .Select-value-label {
                    font-size: 12px !important;
                    line-height: 20px !important;
                    color: rgb(27, 54, 93) !important;
                }
                
                #x-axis-dropdown .Select-control,
                #y-axis-dropdown .Select-control,
                #bubble-size-dropdown .Select-control {
                    font-size: 12px !important;
                    height: 22px !important;
                    min-height: 22px !important;
                    border-radius: 0 !important;
                }
                
                #x-axis-dropdown .Select-value-label,
                #y-axis-dropdown .Select-value-label,
                #bubble-size-dropdown .Select-value-label {
                    font-size: 12px !important;
                    line-height: 20px !important;
                    color: rgb(27, 54, 93) !important;
                }
                
                #x-axis-dropdown .Select-input,
                #y-axis-dropdown .Select-input,
                #bubble-size-dropdown .Select-input {
                    height: 20px !important;
                    line-height: 20px !important;
                    color: rgb(27, 54, 93) !important;
                }
                
                #x-axis-dropdown .Select-input > input,
                #y-axis-dropdown .Select-input > input,
                #bubble-size-dropdown .Select-input > input {
                    color: rgb(27, 54, 93) !important;
                }
                
                .Select-menu-outer *,
                .Select-menu *,
                .Select-option *,
                div[id*="dropdown"] .Select-menu-outer *,
                div[id*="dropdown"] .Select-menu * {
                    font-family: Arial, Helvetica, sans-serif !important;
                    font-size: 12px !important;
                }
                
                .Select-menu-outer .Select-option,
                .Select-menu .Select-option,
                div[id*="dropdown"] .Select-menu-outer .Select-option {
                    font-family: Arial, Helvetica, sans-serif !important;
                    font-size: 12px !important;
                    padding: 6px 10px !important;
                    color: #000000 !important;
                    background-color: #fff !important;
                    line-height: 1.5 !important;
                    white-space: nowrap !important;
                }
                
                .Select-menu-outer .Select-option:hover,
                .Select-menu .Select-option:hover {
                    background-color: #f0f0f0 !important;
                    color: #000000 !important;
                }
                
                .Select-menu-outer .Select-option.is-selected,
                .Select-menu .Select-option.is-selected {
                    background-color: #e6f3ff !important;
                    color: #000000 !important;
                }
                
                /* Range input fields - show as text by default, input box on hover */
                #x-range-min-input,
                #x-range-max-input,
                #y-range-min-input,
                #y-range-max-input,
                #bubble-range-min-input,
                #bubble-range-max-input {
                    border: none !important;
                    background: transparent !important;
                    padding: 0 !important;
                    font-size: 12px !important;
                    color: #1b365d !important;
                    width: auto !important;
                    min-width: 150px !important;
                    max-width: 80px !important;
                    height: 18px !important;
                    line-height: 18px !important;
                    outline: none !important;
                    box-shadow: none !important;
                    top: 0 !important;
                    vertical-align: top !important;
                    margin: 0 !important;
                }
                
                #x-range-min-input,
                #y-range-min-input,
                #bubble-range-min-input {
                    left: 0 !important;
                    text-align: left !important;
                }
                
                #x-range-max-input,
                #y-range-max-input,
                #bubble-range-max-input {
                    text-align: right !important;
                    float: right !important;
                    margin-right: 0 !important;
                    padding-right: 0 !important;
                }
                
                #x-range-min-input[type="text"],
                #x-range-min-input[type="number"],
                #x-range-max-input[type="text"],
                #x-range-max-input[type="number"],
                #y-range-min-input[type="text"],
                #y-range-min-input[type="number"],
                #y-range-max-input[type="text"],
                #y-range-max-input[type="number"],
                #bubble-range-min-input[type="text"],
                #bubble-range-min-input[type="number"],
                #bubble-range-max-input[type="text"],
                #bubble-range-max-input[type="number"] {
                    vertical-align: top !important;
                    margin: 0 !important;
                    display: inline-block !important;
                }
                
                #x-range-min-input:hover,
                #x-range-max-input:hover,
                #y-range-min-input:hover,
                #y-range-max-input:hover,
                #bubble-range-min-input:hover,
                #bubble-range-max-input:hover {
                    border: 1px solid #ccc !important;
                    background: #ffffff !important;
                    padding: 1px 3px !important;
                }
                
                #x-range-min-input:focus,
                #x-range-max-input:focus,
                #y-range-min-input:focus,
                #y-range-max-input:focus,
                #bubble-range-min-input:focus,
                #bubble-range-max-input:focus {
                    border: 1px solid #999 !important;
                    background: #ffffff !important;
                    padding: 1px 3px !important;
                }
                
                div[id*="range-slider"] {
                    margin-left: 0 !important;
                    padding-left: 0 !important;
                    margin-right: 0 !important;
                    padding-right: 0 !important;
                }
                
                .rc-slider {
                    margin-left: 0 !important;
                    padding-left: 0 !important;
                    margin-right: 0 !important;
                    padding-right: 0 !important;
                    width: 100% !important;
                    box-sizing: border-box !important;
                }
                
                .rc-slider-rail {
                    margin-left: 0 !important;
                    margin-right: 0 !important;
                    width: 100% !important;
                    box-sizing: border-box !important;
                }

                /* Russian Exports Table - Fix fixed column overflow and scrollable column clipping */
                #russian-exports-table .dash-table-container {
                    overflow: hidden !important;
                    position: relative !important;
                    width: 100% !important;
                }
                
                #russian-exports-table .dash-spreadsheet-container {
                    overflow-x: auto !important;
                    overflow-y: auto !important;
                    position: relative !important;
                    width: 100% !important;
                }
                
                /* Hide overflow from fixed column wrapper */
                #russian-exports-table .dash-table-container > div {
                    overflow: hidden !important;
                }
                
                /* Fix the border issue on fixed columns - ensure Company column has proper right border */
                #russian-exports-table .dash-table-container table thead tr th:nth-child(2),
                #russian-exports-table .dash-table-container table tbody tr td:nth-child(2) {
                    border-right: 2px solid #ddd !important;
                    position: relative !important;
                    z-index: 10 !important;
                    box-shadow: 2px 0 0 0 #fff !important;
                }
                
                /* Hide any overflow from the fixed columns container */
                #russian-exports-table .dash-table-container .dash-spreadsheet-container > div:first-child {
                    overflow: hidden !important;
                }
                
                /* Ensure scrollable columns container properly clips overflow */
                #russian-exports-table .dash-spreadsheet-container > div:last-child {
                    overflow: hidden !important;
                    position: relative !important;
                }
                
                /* Ensure the scrollable table wrapper clips properly */
                #russian-exports-table .dash-spreadsheet-container .dash-spreadsheet {
                    overflow: hidden !important;
                    width: 100% !important;
                }
                
                /* Clip scrollable columns that extend beyond viewport */
                #russian-exports-table .dash-spreadsheet-container table {
                    table-layout: auto !important;
                }
                
                /* Ensure scrollable column cells (3rd column onwards) are clipped */
                #russian-exports-table .dash-spreadsheet-container table thead tr th:nth-child(n+3),
                #russian-exports-table .dash-spreadsheet-container table tbody tr td:nth-child(n+3) {
                    overflow: hidden !important;
                    max-width: 200px !important;
                }
                /* Global Exports slider padding override */
                #global-exports-year-slider {
                    padding: 0px 0px 25px !important;
                }

            </style>
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    '''
    
    # Main layout with tabs
    dash_app.layout = html.Div([
        # Location component for URL routing
        dcc.Location(id='url', refresh=False),
        # Store to track whether dashboard is rendered inside an iframe
        dcc.Store(id='iframe-flag', data=False),
        
        # Header Navigation - REMOVED
        # Filter & Search Section Header - REMOVED
        
        # Tab Navigation - matching Image 1 design (white tabs with rounded corners on light gray background)
        html.Div([
            html.Div([
                dcc.Link(
                    html.Div([
                        html.Img(
                            src=get_absolute_url("/assets/images/globe_inactive.svg"),
                            id="tab-icon-country",
                            style={
                                'height': '35px',
                                'marginRight': '10px',
                                'display': 'inline-block',
                                'verticalAlign': 'middle'
                            }
                        ),
                        html.Span('Country', style={
                            'fontSize': '18px',
                            'fontWeight': '500',
                            'color': '#2c3e50',
                            'display': 'inline-block',
                            'verticalAlign': 'middle'
                        })
                    ], style={
                        'display': 'flex',
                        'alignItems': 'center',
                        'padding': '15px 20px',
                        'cursor': 'pointer',
                        'height': '100%'
                    }),
                    href=get_link_href('/wcod/'),
                    id='tab-link-country',
                    style={'textDecoration': 'none', 'transition': 'all 0.2s ease'}
                ),
                dcc.Link(
                    html.Div([
                        html.Img(
                            src=get_absolute_url("/assets/images/oil_inactive.svg"),
                            id='tab-icon-crude',
                            style={
                                'height': '40px',
                                'marginRight': '10px',
                                'display': 'inline-block',
                                'verticalAlign': 'middle'
                            }
                        ),
                        html.Span('Crude', style={
                            'fontSize': '18px',
                            'fontWeight': '500',
                            'color': '#2c3e50',
                            'display': 'inline-block',
                            'verticalAlign': 'middle'
                        })
                    ], style={
                        'display': 'flex',
                        'alignItems': 'center',
                        'padding': '15px 20px',
                        'cursor': 'pointer',
                        'height': '100%'
                    }),
                    href=get_link_href('/crude-overview'),
                    id='tab-link-crude',
                    style={'textDecoration': 'none', 'transition': 'all 0.2s ease'}
                ),
                dcc.Link(
                    html.Div([
                        html.Img(
                            src=get_absolute_url("/assets/images/trade_inactive.svg"),
                            id='tab-icon-trade',
                            style={
                                'height': '40px',
                                'marginRight': '10px',
                                'display': 'inline-block',
                                'verticalAlign': 'middle'
                            }
                        ),
                        html.Span('Trade', style={
                            'fontSize': '18px',
                            'fontWeight': '500',
                            'color': '#2c3e50',
                            'display': 'inline-block',
                            'verticalAlign': 'middle'
                        })
                    ], style={
                        'display': 'flex',
                        'alignItems': 'center',
                        'padding': '15px 20px',
                        'cursor': 'pointer',
                        'height': '100%'
                    }),
                    href=get_link_href('/trade/imports-country-detail'),
                    id='tab-link-trade',
                    style={'textDecoration': 'none', 'transition': 'all 0.2s ease'}
                ),
                dcc.Link(
                    html.Div([
                        html.Img(
                            src=get_absolute_url("/assets/images/prices_inactive.svg"),
                            id='tab-icon-prices',
                            style={
                                'height': '40px',
                                'marginRight': '10px',
                                'display': 'inline-block',
                                'verticalAlign': 'middle'
                            }
                        ),
                        html.Span('Prices', style={
                            'fontSize': '18px',
                            'fontWeight': '500',
                            'color': '#2c3e50',
                            'display': 'inline-block',
                            'verticalAlign': 'middle'
                        })
                    ], style={
                        'display': 'flex',
                        'alignItems': 'center',
                        'padding': '15px 20px',
                        'cursor': 'pointer',
                        'height': '100%'
                    }),
                    href=get_link_href('/prices/global-crude-prices'),
                    id='tab-link-prices',
                    style={'textDecoration': 'none', 'transition': 'all 0.2s ease'}
                ),
                dcc.Link(
                    html.Div([
                        html.Span('Upstream Projects', style={
                            'fontSize': '18px',
                            'fontWeight': '500',
                            'color': '#2c3e50',
                            'display': 'inline-block',
                            'verticalAlign': 'middle'
                        })
                    ], style={
                        'display': 'flex',
                        'alignItems': 'center',
                        'padding': '15px 20px',
                        'cursor': 'pointer',
                        'height': '100%'
                    }),
                    href=get_link_href('/upstream-projects/projects-by-country'),
                    id='tab-link-projects',
                    style={'textDecoration': 'none', 'transition': 'all 0.2s ease'}
                ),
                dcc.Link(
                    html.Div([
                        html.Span('Methodology', style={
                            'fontSize': '18px',
                            'fontWeight': '500',
                            'color': '#2c3e50',
                            'display': 'inline-block',
                            'verticalAlign': 'middle'
                        })
                    ], style={
                        'display': 'flex',
                        'alignItems': 'center',
                        'padding': '15px 20px',
                        'cursor': 'pointer',
                        'height': '100%'
                    }),
                    href=get_link_href('/upstream-oil-projects-tracker-methodology'),
                    id='tab-link-methodology',
                    style={'textDecoration': 'none', 'transition': 'all 0.2s ease'}
                ),
            ], style={
                'display': 'flex',
                'background': '#e5e5e5',
                'padding': '8px 20px 0 30px',
                'margin': '0',
                'overflowX': 'auto',
                'gap': '4px',
                'minHeight': '56px',
                'alignItems': 'flex-end'
            }, className='tab-style1'),
            # Hidden tabs component for state management
            dcc.Tabs(
                id='main-tabs',
                value='country-tab',
                children=[
                    dcc.Tab(label='Country', value='country-tab', style={'display': 'none'}),
                    dcc.Tab(label='Crude', value='crude-tab', style={'display': 'none'}),
                    dcc.Tab(label='Trade', value='trade-tab', style={'display': 'none'}),
                    dcc.Tab(label='Prices', value='prices-tab', style={'display': 'none'}),
                    dcc.Tab(label='Upstream Projects', value='projects-tab', style={'display': 'none'}),
                    dcc.Tab(label='Methodology', value='methodology-tab', style={'display': 'none'}),
                ],
                style={'display': 'none'}
            )
        ], className="container-fluid", style={'padding': '0', 'background': '#e5e5e5', 'width': '100%'}),
        
        # Sub-menu - horizontal oval buttons below tabs (matching Energy Intelligence design)
        # This will be dynamically updated by the update_submenu callback based on the active tab
        html.Div([
            html.Div([
                html.Div(id='submenu-container', children=[])
            ], className='col-md-12', style={
                'padding': '20px 30px',
                'background': '#ffffff',
                'borderBottom': '1px solid #e0e0e0'
            })
        ], className='row cover-menu', style={'margin': '0', 'background': 'white'}),
        
        # Main Content Area
        html.Div([
            html.Div([
                html.Div(id='tab-content', style={'background': 'white', 'minHeight': '600px'})
            ], className='col-md-12', style={'padding': '24px', 'background': '#f8f9fa'})
        ], className='row', style={'margin': '0', 'background': 'white'}),
        
        # Store for current sub-menu selection
        dcc.Store(id='current-submenu', data='country-overview'),
        
        # Footer - REMOVED
        # html.Div(id='footer-container', children=[...])
    ], style={'background': '#f5f5f5', 'minHeight': '100vh'})
    
    # Detect iframe rendering client-side to avoid showing duplicate headers inside embeds
    dash_app.clientside_callback(
        """
        function(href) {
            try {
                return window.self !== window.top;
            } catch (e) {
                return true;
            }
        }
        """,
        Output('iframe-flag', 'data'),
        Input('url', 'href')
    )
    
    # Callback to hide header and footer when WCoD dashboards are embedded in iframes
    @dash_app.callback(
        [Output('header-container', 'style'),
         Output('footer-container', 'style')],
        [Input('url', 'pathname'),
         Input('url', 'search'),
         Input('iframe-flag', 'data')],
        prevent_initial_call=False
    )
    def toggle_header_footer(pathname, search, is_iframe):
        """Hide header/footer for specific WCoD iframe routes when rendered inside iframe or via query flag"""
        pathname_str = str(pathname) if pathname else ''
        query_params = parse_qs(search.lstrip('?')) if search else {}
        embed_flag = False
        for key in ('iframe', 'embed', 'hide_header', 'hideHeader'):
            if key in query_params:
                value = query_params[key][0].lower()
                if value in ('1', 'true', 't', 'yes', 'y'):
                    embed_flag = True
                    break
        
        iframe_pages = [
            '/country-overview',
            '/crude-overview',
            '/crude-profile',
            '/crude-comparison',
            '/crude-quality-comparison',
            '/crude-carbon-intensity',
            '/trade/',
            '/prices/',
            '/upstream-projects/',
            # Keep old paths for backward compatibility
            '/wcod-country-overview',
            '/wcod/crude-overview',
            '/wcod-crude-profile',
            '/wcod-crude-comparison',
            '/wcod/wcod-crude-quality-comparison',
            '/wcod-crude-quality-comparison',
            '/wcod-crude-carbon-intensity',
            '/wcod/trade/',
            '/wcod/prices/',
            '/wcod/upstream-projects/'
        ]
        is_wcod_path = (pathname_str.startswith('/wcod') or pathname_str.startswith('/wcod-') or
                        pathname_str.startswith('/crude') or pathname_str.startswith('/trade') or
                        pathname_str.startswith('/prices') or pathname_str.startswith('/upstream') or
                        pathname_str.startswith('/country-overview') or pathname_str.startswith('/carbon-intensity') or
                        pathname_str.startswith('/upstream-oil'))
        should_hide = (bool(is_iframe) or embed_flag) and (is_wcod_path or any(page in pathname_str for page in iframe_pages))
        if should_hide:
            return {'display': 'none'}, {'display': 'none'}
        return {'display': 'block'}, {'display': 'block'}
    
    # Callback to handle URL routing - runs on initial load to set correct tab/submenu from URL
    @dash_app.callback(
        [Output('main-tabs', 'value'),
         Output('current-submenu', 'data', allow_duplicate=True)],
        [Input('url', 'pathname'),
         Input('url', 'search')],
        prevent_initial_call='initial_duplicate'  # Required when using allow_duplicate=True, but allows initial call
    )
    def update_from_url(pathname, search):
        """Update tabs and submenu based on URL"""
        # Check for page query parameter (used when embedded in iframe)
        page_from_query = None
        if search:
            query_params = parse_qs(search.lstrip('?'))
            if 'page' in query_params and query_params['page']:
                page_from_query = query_params['page'][0]
        
        # Use page from query parameter if available, otherwise use pathname
        effective_pathname = page_from_query if page_from_query else pathname
        
        # Normalize pathname
        if not effective_pathname:
            effective_pathname = '/wcod/'
        elif effective_pathname == '/wcod':
            effective_pathname = '/wcod/'
        
        # Map URL paths to tab and submenu - matching exact user-provided URLs
        url_mapping = {
            # Country tab - /wcod shows Country Overview
            '/wcod/': ('country-tab', 'country-overview'),
            '/wcod': ('country-tab', 'country-overview'),
            '/country-overview': ('country-tab', 'country-profile'),
            # Keep old paths for backward compatibility
            '/wcod-country-overview': ('country-tab', 'country-profile'),
            # Crude tab
            '/crude-overview': ('crude-tab', 'crude-overview'),
            '/crude-profile': ('crude-tab', 'crude-profile'),
            '/crude-comparison': ('crude-tab', 'crude-comparison'),
            '/crude-quality-comparison': ('crude-tab', 'crude-quality'),
            '/crude-carbon-intensity': ('crude-tab', 'crude-carbon'),
            # Keep old paths for backward compatibility
            '/wcod/crude-overview': ('crude-tab', 'crude-overview'),
            '/wcod-crude-profile': ('crude-tab', 'crude-profile'),
            '/wcod-crude-comparison': ('crude-tab', 'crude-comparison'),
            '/wcod/wcod-crude-quality-comparison': ('crude-tab', 'crude-quality'),
            '/wcod-crude-quality-comparison': ('crude-tab', 'crude-quality'),
            '/wcod-crude-carbon-intensity': ('crude-tab', 'crude-carbon'),
            # Trade tab
            '/trade/imports-country-detail': ('trade-tab', 'imports-detail'),
            '/trade/imports-country-comparison': ('trade-tab', 'imports-comparison'),
            '/trade/global-exports': ('trade-tab', 'global-exports'),
            '/trade/russian-exports-by-terminal-and-exporting-company': ('trade-tab', 'russian-exports'),
            # Keep old paths for backward compatibility
            '/wcod/trade/imports-country-detail': ('trade-tab', 'imports-detail'),
            '/wcod/trade/imports-country-comparison': ('trade-tab', 'imports-comparison'),
            '/wcod/trade/global-exports': ('trade-tab', 'global-exports'),
            '/wcod/trade/russian-exports-by-terminal-and-exporting-company': ('trade-tab', 'russian-exports'),
            # Prices tab
            '/prices/global-crude-prices': ('prices-tab', 'global-prices'),
            '/prices/price-scorecard-for-key-world-oil-grades': ('prices-tab', 'price-scorecard'),
            '/prices/gross-product-worth-and-margins': ('prices-tab', 'gpw-margins'),
            # Keep old paths for backward compatibility
            '/wcod/prices/global-crude-prices': ('prices-tab', 'global-prices'),
            '/wcod/prices/price-scorecard-for-key-world-oil-grades': ('prices-tab', 'price-scorecard'),
            '/wcod/prices/gross-product-worth-and-margins': ('prices-tab', 'gpw-margins'),
            # Upstream Projects tab
            '/upstream-projects/projects-by-country': ('projects-tab', 'projects-country'),
            '/upstream-projects/projects-by-company': ('projects-tab', 'projects-company'),
            '/upstream-projects/projects-by-time': ('projects-tab', 'projects-time'),
            '/upstream-projects/projects-by-status': ('projects-tab', 'projects-status'),
            '/upstream-projects-related-articles': ('projects-tab', 'projects-latest'),
            # Keep old paths for backward compatibility
            '/wcod/upstream-projects/projects-by-country': ('projects-tab', 'projects-country'),
            '/wcod/upstream-projects/projects-by-company': ('projects-tab', 'projects-company'),
            '/wcod/upstream-projects/projects-by-time': ('projects-tab', 'projects-time'),
            '/wcod-upstream-projects/projects-by-status': ('projects-tab', 'projects-status'),
            '/wcod-upstream-projects-related-articles': ('projects-tab', 'projects-latest'),
            # Methodology tab
            '/upstream-oil-projects-tracker-methodology': ('methodology-tab', 'projects-tracker'),
            '/carbon-intensity-methodology': ('methodology-tab', 'projects-carbon'),
            # Keep old paths for backward compatibility
            '/wcod-upstream-oil-projects-tracker-methodology': ('methodology-tab', 'projects-tracker'),
            '/wcod-carbon-intensity-methodology': ('methodology-tab', 'projects-carbon'),
        }
        
        tab, submenu = url_mapping.get(effective_pathname, ('country-tab', 'country-overview'))
        return tab, submenu
    
    # Callback to highlight active tab - runs on initial load and when tab changes
    @dash_app.callback(
        [Output('tab-link-country', 'style'),
         Output('tab-link-crude', 'style'),
         Output('tab-link-trade', 'style'),
         Output('tab-link-prices', 'style'),
         Output('tab-link-projects', 'style'),
         Output('tab-link-methodology', 'style'),
         Output('tab-icon-country', 'src'),
         Output('tab-icon-crude', 'src'),
         Output('tab-icon-trade', 'src'),
         Output('tab-icon-prices', 'src')],
        Input('main-tabs', 'value'),
        prevent_initial_call=False
    )
    def update_tab_styles(active_tab):
        """Update tab link styles based on active tab - matching Image 1 design"""
        # Default to country-tab if active_tab is None or not set
        if not active_tab:
            active_tab = 'country-tab'
        
        # Base style for inactive tabs - light gray background (blends with container)
        base_style = {
            'textDecoration': 'none',
            'transition': 'all 0.2s ease',
            'background': '#fff',
            'borderRadius': '8px 8px 0 0',
            'boxShadow': 'none',
            'position': 'relative',
            'zIndex': '1',
            'padding': '10px 25px',
            'height': '75px',
            'transform': 'translateY(-3px)'
        }
        
        # Active style - white background, elevated with prominent shadow (matching image)
        active_style = {
            'textDecoration': 'none',
            'transition': 'all 0.2s ease',
            'background': 'white',
            'borderRadius': '8px 8px 0 0',
            'boxShadow': '0 -3px 12px rgba(0, 0, 0, 0.15), 0 -1px 4px rgba(0, 0, 0, 0.1)',
            'position': 'relative',
            'zIndex': '2',
            'padding': '13px 35px',
            'transform': 'translateY(0px)'
        }
        
        # Icon sources - switch between active and inactive SVGs (using local assets)
        country_icon = get_absolute_url('/assets/images/globe_active.svg') if active_tab == 'country-tab' else get_absolute_url('/assets/images/globe_inactive.svg')
        crude_icon = get_absolute_url('/assets/images/oil_active.svg') if active_tab == 'crude-tab' else get_absolute_url('/assets/images/oil_inactive.svg')
        trade_icon = get_absolute_url('/assets/images/trade_active.svg') if active_tab == 'trade-tab' else get_absolute_url('/assets/images/trade_inactive.svg')
        prices_icon = get_absolute_url('/assets/images/prices_active.svg') if active_tab == 'prices-tab' else get_absolute_url('/assets/images/prices_inactive.svg')
        
        return [
            active_style if active_tab == 'country-tab' else base_style,
            active_style if active_tab == 'crude-tab' else base_style,
            active_style if active_tab == 'trade-tab' else base_style,
            active_style if active_tab == 'prices-tab' else base_style,
            active_style if active_tab == 'projects-tab' else base_style,
            active_style if active_tab == 'methodology-tab' else base_style,
            country_icon,
            crude_icon,
            trade_icon,
            prices_icon,
        ]
    
    # Callback to update sub-menu based on main tab and submenu changes
    @dash_app.callback(
        Output('submenu-container', 'children', allow_duplicate=True),
        [Input('main-tabs', 'value'),
         Input('url', 'pathname'),
         Input('current-submenu', 'data')],
        prevent_initial_call='initial_duplicate'
    )
    def update_submenu(active_tab, pathname, current_submenu):
        """Update sub-menu based on active main tab and current submenu"""
        # Default to country-tab if active_tab is None or not set
        if not active_tab:
            active_tab = 'country-tab'
        
        submenus = {
            'country-tab': [
                {'label': 'Country Overview', 'value': 'country-overview'},
                {'label': 'Country Profile', 'value': 'country-profile'},
            ],
            'crude-tab': [
                {'label': 'Crude Overview', 'value': 'crude-overview'},
                {'label': 'Crude Profile', 'value': 'crude-profile'},
                {'label': 'Crude Comparison', 'value': 'crude-comparison'},
                {'label': 'Crude Quality Comparison', 'value': 'crude-quality'},
                {'label': 'Crude Carbon Intensity', 'value': 'crude-carbon'},
            ],
            'trade-tab': [
                {'label': 'Imports - Country Detail', 'value': 'imports-detail'},
                {'label': 'Imports - Country Comparison', 'value': 'imports-comparison'},
                {'label': 'Global Exports', 'value': 'global-exports'},
                {'label': 'Russian Exports by Terminal and Exporting Company', 'value': 'russian-exports'},
            ],
            'prices-tab': [
                {'label': 'Global Crude Prices', 'value': 'global-prices'},
                {'label': 'Price Scorecard for Key World Oil Grades', 'value': 'price-scorecard'},
                {'label': 'Gross Product Worth and Margins', 'value': 'gpw-margins'},
            ],
            'projects-tab': [
                {'label': 'Projects by Country', 'value': 'projects-country'},
                {'label': 'Projects by Company', 'value': 'projects-company'},
                {'label': 'Projects by Time', 'value': 'projects-time'},
                {'label': 'Projects by Status', 'value': 'projects-status'},
                {'label': 'Latest Updates', 'value': 'projects-latest'},
            ],
            'methodology-tab': [
                {'label': 'Upstream Oil Projects Tracker', 'value': 'projects-tracker'},
                {'label': 'Carbon Intensity', 'value': 'projects-carbon'},
            ]
        }
        
        menu_items = submenus.get(active_tab, [])
        
        # Determine the correct submenu from URL if available, otherwise use current or default
        if pathname:
            # Normalize pathname
            if pathname == '/wcod':
                pathname = '/wcod/'
            
            # Map URL to submenu value
            url_to_submenu = {
                '/wcod/': 'country-overview',
                '/wcod-country-overview': 'country-profile',
                '/wcod/crude-overview': 'crude-overview',
                '/wcod-crude-profile': 'crude-profile',
                '/wcod-crude-comparison': 'crude-comparison',
                '/wcod/wcod-crude-quality-comparison': 'crude-quality',
                '/wcod-crude-quality-comparison': 'crude-quality',  # Keep old path for backward compatibility
                '/wcod-crude-carbon-intensity': 'crude-carbon',
                '/wcod/trade/imports-country-detail': 'imports-detail',
                '/wcod/trade/imports-country-comparison': 'imports-comparison',
                '/wcod/trade/global-exports': 'global-exports',
                '/wcod/trade/russian-exports-by-terminal-and-exporting-company': 'russian-exports',
                '/wcod/prices/global-crude-prices': 'global-prices',
                '/wcod/prices/price-scorecard-for-key-world-oil-grades': 'price-scorecard',
                '/wcod/prices/gross-product-worth-and-margins': 'gpw-margins',
                '/wcod/upstream-projects/projects-by-country': 'projects-country',
                '/wcod/upstream-projects/projects-by-company': 'projects-company',
                '/wcod/upstream-projects/projects-by-time': 'projects-time',
                '/wcod-upstream-projects/projects-by-status': 'projects-status',
                '/wcod-upstream-projects-related-articles': 'projects-latest',
                '/wcod-upstream-oil-projects-tracker-methodology': 'projects-tracker',
                '/wcod-carbon-intensity-methodology': 'projects-carbon',
            }
            url_submenu = url_to_submenu.get(pathname)
            if url_submenu and any(item['value'] == url_submenu for item in menu_items):
                default_value = url_submenu
            elif current_submenu and any(item['value'] == current_submenu for item in menu_items):
                default_value = current_submenu
            else:
                default_value = menu_items[0]['value'] if menu_items else 'country-overview'
        elif current_submenu and any(item['value'] == current_submenu for item in menu_items):
            default_value = current_submenu
        elif active_tab == 'country-tab':
            default_value = 'country-overview'
        else:
            default_value = menu_items[0]['value'] if menu_items else 'country-overview'
        
        # Get current submenu from store to highlight active button
        # Create URL paths for each submenu item - use relative paths for dcc.Link
        url_paths = {
            'country-overview': get_link_href('/wcod/'),
            'country-profile': get_link_href('/country-overview'),
            'crude-overview': get_link_href('/crude-overview'),
            'crude-profile': get_link_href('/crude-profile'),
            'crude-comparison': get_link_href('/crude-comparison'),
            'crude-quality': get_link_href('/crude-quality-comparison'),
            'crude-carbon': get_link_href('/crude-carbon-intensity'),
            'imports-detail': get_link_href('/trade/imports-country-detail'),
            'imports-comparison': get_link_href('/trade/imports-country-comparison'),
            'global-exports': get_link_href('/trade/global-exports'),
            'russian-exports': get_link_href('/trade/russian-exports-by-terminal-and-exporting-company'),
            'global-prices': get_link_href('/prices/global-crude-prices'),
            'price-scorecard': get_link_href('/prices/price-scorecard-for-key-world-oil-grades'),
            'gpw-margins': get_link_href('/prices/gross-product-worth-and-margins'),
            'projects-country': get_link_href('/upstream-projects/projects-by-country'),
            'projects-company': get_link_href('/upstream-projects/projects-by-company'),
            'projects-time': get_link_href('/upstream-projects/projects-by-time'),
            'projects-status': get_link_href('/upstream-projects/projects-by-status'),
            'projects-latest': get_link_href('/upstream-projects-related-articles'),
            'projects-tracker': get_link_href('/upstream-oil-projects-tracker-methodology'),
            'projects-carbon': get_link_href('/carbon-intensity-methodology'),
        }
        
        # Icons for submenu items - matching Energy Intelligence design
        submenu_icons = {
            'country-overview': '📋',
            'country-profile': '📄',
            'crude-overview': '🛢️',
            'crude-profile': '📊',
            'crude-comparison': '⚖️',
            'crude-quality': '🔬',
            'crude-carbon': '🌱',
            'imports-detail': '📥',
            'imports-comparison': '📊',
            'global-exports': '🌍',
            'russian-exports': '🇷🇺',
            'global-prices': '💰',
            'price-scorecard': '📈',
            'gpw-margins': '💵',
            'projects-country': '🗺️',
            'projects-company': '🏢',
            'projects-time': '📅',
            'projects-status': '📊',
            'projects-latest': '🆕',
            'projects-tracker': '📊',
            'projects-carbon': '🌱'
        }
        
        # Horizontal oval buttons for submenu - matching Energy Intelligence design
        if menu_items:
            submenu_html = html.Div([
                dcc.Link(
                    html.Span(item['label'], style={'fontSize': '14px'}),
                    href=url_paths.get(item['value'], get_link_href('/wcod/')),
                    id={'type': 'submenu-button', 'index': item['value']},
                    style={
                        'textDecoration': 'none',
                        'display': 'inline-block',
                        'padding': '8px 20px',
                        'margin': '0 8px 8px 0',
                        'background': '#1b365d' if item['value'] == default_value else '#f8f9fa',
                        'color': 'white' if item['value'] == default_value else '#2c3e50',
                        'border': '1px solid #ffffff' if item['value'] == default_value else '1px solid #e0e0e0',
                        'borderRadius': '20px',
                        'cursor': 'pointer',
                        'transition': 'all 0.3s',
                        'fontWeight': '500' if item['value'] == default_value else 'normal',
                        'whiteSpace': 'nowrap'
                    }
                )
                for item in menu_items
            ], style={'display': 'flex', 'flexWrap': 'wrap', 'marginBottom': '10px'})
        else:
            submenu_html = html.Div([])
        
        return submenu_html
    
    # Callback to update content based on sub-menu selection
    @dash_app.callback(
        Output('tab-content', 'children'),
        [Input('current-submenu', 'data'),
         Input('main-tabs', 'value'),
         Input('url', 'pathname'),
         Input('url', 'search')],
        prevent_initial_call=False
    )
    def update_tab_content(submenu, main_tab, pathname, search):
        """Update main content area based on sub-menu selection"""
        # Check for page query parameter (used when embedded in iframe)
        pathname_str = str(pathname) if pathname else ''
        page_from_query = None
        if search:
            query_params = parse_qs(search.lstrip('?'))
            if 'page' in query_params and query_params['page']:
                page_from_query = query_params['page'][0]
        
        # Use page from query parameter to determine which view to show if submenu is None
        effective_page = page_from_query if page_from_query else pathname_str
        
        # If pathname matches crude-carbon-intensity, ensure we render it even if submenu isn't set yet
        if '/wcod-crude-carbon-intensity' in effective_page:
            return render_crude_carbon()
        
        if main_tab == 'country-tab':
            if submenu == 'country-overview':
                return render_country_overview()
            elif submenu == 'country-profile':
                return render_country_profile()
        elif main_tab == 'crude-tab':
            # Handle None submenu on refresh - use query parameter to determine which view to show
            if submenu is None:
                # On refresh, submenu might be None, so check query parameter or pathname
                if page_from_query:
                    effective_page = page_from_query
                else:
                    effective_page = pathname_str
                
                if '/wcod-crude-carbon-intensity' in effective_page:
                    return render_crude_carbon()
                elif '/wcod/crude-overview' in effective_page:
                    return render_crude_overview()
                elif '/wcod-crude-profile' in effective_page:
                    return render_crude_profile()
                elif '/wcod-crude-comparison' in effective_page:
                    return render_crude_comparison()
                elif '/wcod/wcod-crude-quality-comparison' in effective_page or '/wcod-crude-quality-comparison' in effective_page:
                    return render_crude_quality()
                # Default to crude-overview if we can't determine
                return render_crude_overview()
            elif submenu == 'crude-overview':
                return render_crude_overview()
            elif submenu == 'crude-profile':
                return render_crude_profile()
            elif submenu == 'crude-comparison':
                return render_crude_comparison()
            elif submenu == 'crude-quality':
                return render_crude_quality()
            elif submenu == 'crude-carbon':
                return render_crude_carbon()
        elif main_tab == 'trade-tab':
            if submenu == 'imports-detail':
                return render_imports_detail()
            elif submenu == 'imports-comparison':
                return render_imports_comparison()
            elif submenu == 'global-exports':
                return render_global_exports()
            elif submenu == 'russian-exports':
                return render_russian_exports()
        elif main_tab == 'prices-tab':
            if submenu == 'global-prices':
                return render_global_prices()
            elif submenu == 'price-scorecard':
                return render_price_scorecard()
            elif submenu == 'gpw-margins':
                return render_gpw_margins()
        elif main_tab == 'projects-tab':
            # Handle None submenu on refresh - use query parameter or pathname to determine which view to show
            if submenu is None:
                # On refresh, submenu might be None, so check query parameter or pathname
                if page_from_query:
                    effective_page = page_from_query
                else:
                    effective_page = pathname_str
                
                # Check pathname to determine which projects view to render
                if '/upstream-projects/projects-by-status' in effective_page or '/wcod-upstream-projects/projects-by-status' in effective_page:
                    return render_projects_by_status()
                elif '/upstream-projects/projects-by-country' in effective_page or '/wcod/upstream-projects/projects-by-country' in effective_page:
                    return render_projects_by_country()
                elif '/upstream-projects/projects-by-company' in effective_page or '/wcod/upstream-projects/projects-by-company' in effective_page:
                    return render_projects_by_company()
                elif '/upstream-projects/projects-by-time' in effective_page or '/wcod/upstream-projects/projects-by-time' in effective_page:
                    return render_projects_by_time()
                elif '/upstream-projects-related-articles' in effective_page or '/wcod-upstream-projects-related-articles' in effective_page:
                    return render_projects_latest()
                # Default to projects-by-country if we can't determine
                return render_projects_by_country()
            elif submenu == 'projects-country':
                return render_projects_by_country()
            elif submenu == 'projects-company':
                return render_projects_by_company()
            elif submenu == 'projects-time':
                return render_projects_by_time()
            elif submenu == 'projects-status':
                return render_projects_by_status()
            elif submenu == 'projects-latest':
                return render_projects_latest()
        elif main_tab == 'methodology-tab':
            if submenu == 'projects-tracker':
                return render_projects_tracker()
            elif submenu == 'projects-carbon':
                return render_projects_carbon()
            else:
                return render_methodology()
        
        return html.Div("Content not found")
    
    # Sub-menu click handler - using pattern matching
    @dash_app.callback(
        [Output('current-submenu', 'data', allow_duplicate=True),
         Output('submenu-container', 'children', allow_duplicate=True)],
        Input({'type': 'submenu-button', 'index': dash.dependencies.ALL}, 'n_clicks'),
        [State({'type': 'submenu-button', 'index': dash.dependencies.ALL}, 'id'),
         State('main-tabs', 'value')],
        prevent_initial_call=True
    )
    def update_submenu_selection(n_clicks_list, button_ids, active_tab):
        """Handle sub-menu item clicks and update button styles"""
        ctx = dash.callback_context
        if not ctx.triggered_id:
            return dash.no_update, dash.no_update

        selected_value = None
        if isinstance(ctx.triggered_id, dict):
            triggered_index = ctx.triggered_id.get('index')
            if triggered_index is not None and button_ids:
                for idx, btn in enumerate(button_ids):
                    if btn.get('index') == triggered_index:
                        if n_clicks_list and idx < len(n_clicks_list) and n_clicks_list[idx]:
                            selected_value = triggered_index
                        break

        if not selected_value:
            return dash.no_update, dash.no_update

        # Rebuild submenu with active state
        submenus = {
            'country-tab': [
                {'label': 'Country Overview', 'value': 'country-overview'},
                {'label': 'Country Profile', 'value': 'country-profile'},
            ],
            'crude-tab': [
                {'label': 'Crude Overview', 'value': 'crude-overview'},
                {'label': 'Crude Profile', 'value': 'crude-profile'},
                {'label': 'Crude Comparison', 'value': 'crude-comparison'},
                {'label': 'Crude Quality Comparison', 'value': 'crude-quality'},
                {'label': 'Crude Carbon Intensity', 'value': 'crude-carbon'},
            ],
            'trade-tab': [
                {'label': 'Imports - Country Detail', 'value': 'imports-detail'},
                {'label': 'Imports - Country Comparison', 'value': 'imports-comparison'},
                {'label': 'Global Exports', 'value': 'global-exports'},
                {'label': 'Russian Exports by Terminal and Exporting Company', 'value': 'russian-exports'},
            ],
            'prices-tab': [
                {'label': 'Global Crude Prices', 'value': 'global-prices'},
                {'label': 'Price Scorecard for Key World Oil Grades', 'value': 'price-scorecard'},
                {'label': 'Gross Product Worth and Margins', 'value': 'gpw-margins'},
            ],
            'projects-tab': [
                {'label': 'Projects by Country', 'value': 'projects-country'},
                {'label': 'Projects by Company', 'value': 'projects-company'},
                {'label': 'Projects by Time', 'value': 'projects-time'},
                {'label': 'Projects by Status', 'value': 'projects-status'},
                {'label': 'Latest Updates', 'value': 'projects-latest'},
            ],
            'methodology-tab': [
                {'label': 'Upstream Oil Projects Tracker', 'value': 'projects-tracker'},
                {'label': 'Carbon Intensity', 'value': 'projects-carbon'},
            ]
        }
        
        menu_items = submenus.get(active_tab, [])
        url_paths = {
            'country-overview': get_link_href('/wcod/'),
            'country-profile': get_link_href('/country-overview'),
            'crude-overview': get_link_href('/crude-overview'),
            'crude-profile': get_link_href('/crude-profile'),
            'crude-comparison': get_link_href('/crude-comparison'),
            'crude-quality': get_link_href('/crude-quality-comparison'),
            'crude-carbon': get_link_href('/crude-carbon-intensity'),
            'imports-detail': get_link_href('/trade/imports-country-detail'),
            'imports-comparison': get_link_href('/trade/imports-country-comparison'),
            'global-exports': get_link_href('/trade/global-exports'),
            'russian-exports': get_link_href('/trade/russian-exports-by-terminal-and-exporting-company'),
            'global-prices': get_link_href('/prices/global-crude-prices'),
            'price-scorecard': get_link_href('/prices/price-scorecard-for-key-world-oil-grades'),
            'gpw-margins': get_link_href('/prices/gross-product-worth-and-margins'),
            'projects-country': get_link_href('/upstream-projects/projects-by-country'),
            'projects-company': get_link_href('/upstream-projects/projects-by-company'),
            'projects-time': get_link_href('/upstream-projects/projects-by-time'),
            'projects-status': get_link_href('/upstream-projects/projects-by-status'),
            'projects-latest': get_link_href('/upstream-projects-related-articles'),
            'projects-tracker': get_link_href('/upstream-oil-projects-tracker-methodology'),
            'projects-carbon': get_link_href('/carbon-intensity-methodology'),
        }
        
        # Icons for submenu items
        submenu_icons = {
            'country-overview': '📋',
            'country-profile': '📄',
            'crude-overview': '🛢️',
            'crude-profile': '📊',
            'crude-comparison': '⚖️',
            'crude-quality': '🔬',
            'crude-carbon': '🌱',
            'imports-detail': '📥',
            'imports-comparison': '📊',
            'global-exports': '🌍',
            'russian-exports': '🇷🇺',
            'global-prices': '💰',
            'price-scorecard': '📈',
            'gpw-margins': '💵',
            'projects-country': '🗺️',
            'projects-company': '🏢',
            'projects-time': '📅',
            'projects-status': '📊',
            'projects-latest': '🆕',
            'projects-tracker': '📊',
            'projects-carbon': '🌱'
        }
        
        # Horizontal oval buttons for submenu - matching Energy Intelligence design
        submenu_html = html.Div([
            dcc.Link(
                html.Span(item['label'], style={'fontSize': '14px'}),
                href=url_paths.get(item['value'], get_link_href('/wcod/')),
                id={'type': 'submenu-button', 'index': item['value']},
                style={
                    'textDecoration': 'none',
                    'display': 'inline-block',
                    'padding': '8px 20px',
                    'margin': '0 8px 8px 0',
                    'background': '#007bff' if item['value'] == selected_value else '#f8f9fa',
                    'color': 'white' if item['value'] == selected_value else '#2c3e50',
                    'border': '1px solid #007bff' if item['value'] == selected_value else '1px solid #e0e0e0',
                    'borderRadius': '20px',
                    'cursor': 'pointer',
                    'transition': 'all 0.3s',
                    'fontWeight': '500' if item['value'] == selected_value else 'normal',
                    'whiteSpace': 'nowrap'
                }
            )
            for item in menu_items
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'marginBottom': '10px'})
        
        return selected_value, submenu_html
    
    # Render functions for each view - now using individual modules
    def render_country_overview():
        """Country Overview view - matching Energy Intelligence design"""
        return country_overview.create_layout()
    
    def render_country_profile():
        """Country Profile view"""
        return country_profile.create_layout(server=None)
    
    def render_crude_overview():
        """Crude Overview view"""
        return crude_overview.create_layout()
    
    def render_crude_profile():
        """Crude Profile view"""
        return crude_profile.create_layout(server=None)
    
    def render_crude_comparison():
        """Crude Comparison view"""
        return crude_comparison.create_layout(server=None)
    
    def render_crude_quality():
        """Crude Quality Comparison view"""
        return crude_quality.create_layout()
    
    def render_crude_carbon():
        """Crude Carbon Intensity view"""
        return crude_carbon.create_layout()
    
    def render_imports_detail():
        """Imports - Country Detail view"""
        return imports_detail.create_layout()
    
    def render_imports_comparison():
        """Imports - Country Comparison view"""
        return imports_comparison.create_layout()
    
    def render_global_exports():
        """Global Exports view"""
        return global_exports.create_layout()
    
    def render_russian_exports():
        """Russian Exports by Terminal view"""
        return russian_exports.create_layout()
    
    def render_global_prices():
        """Global Crude Prices view"""
        return global_prices.create_layout()
    
    def render_price_scorecard():
        """Price Scorecard view"""
        return price_scorecard.create_layout()
    
    def render_gpw_margins():
        """Gross Product Worth and Margins view"""
        return gpw_margins.create_layout()
    
    def render_projects_by_country():
        """Projects by Country view"""
        return projects_by_country.create_layout()
    
    def render_projects_by_company():
        """Projects by Company view"""
        return projects_by_company.create_layout()
    
    def render_projects_by_time():
        """Projects by Time view"""
        return projects_by_time.create_layout()
    
    def render_projects_by_status():
        """Projects by Status view"""
        return projects_by_status.create_layout()
    
    def render_projects_latest():
        """Latest Updates view"""
        return projects_latest.create_layout()
    
    def render_projects_tracker():
        """Upstream Oil Projects Tracker view"""
        return projects_tracker.create_layout()
    
    def render_projects_carbon():
        """Carbon Intensity view"""
        return projects_carbon.create_layout()
    
    def render_methodology():
        """Methodology view"""
        return html.Div([
            html.H3("Methodology", style={'marginBottom': '20px'}),
            html.Div([
                html.P("""
                    The World Crude Oil Data (WCoD) platform provides comprehensive analysis 
                    of global crude oil markets. Our methodology ensures accurate and reliable 
                    data collection and analysis.
                """),
                html.H4("Data Sources", style={'marginTop': '30px'}),
                html.P("Data is collected from multiple authoritative sources including:"),
                html.Ul([
                    html.Li("National oil companies and government agencies"),
                    html.Li("International energy organizations"),
                    html.Li("Market intelligence and trading data"),
                    html.Li("Industry reports and publications")
                ]),
                html.H4("Data Processing", style={'marginTop': '30px'}),
                html.P("""
                    All data undergoes rigorous validation and normalization processes 
                    to ensure consistency and accuracy across different sources and time periods.
                """)
            ])
        ], className='tab-content')
    
    # Register callbacks from individual modules
    # Pass dash_app.server if server is None (for standalone mode)
    callback_server = server if server else dash_app.server
    country_overview.register_callbacks(dash_app, callback_server)
    country_profile.register_callbacks(dash_app, callback_server)
    crude_overview.register_callbacks(dash_app, callback_server)
    crude_profile.register_callbacks(dash_app)
    crude_comparison.register_callbacks(dash_app)
    crude_quality.register_callbacks(dash_app, callback_server)
    crude_carbon.register_callbacks(dash_app, callback_server)
    imports_detail.register_callbacks(dash_app, callback_server)
    imports_comparison.register_callbacks(dash_app, callback_server)
    global_exports.register_callbacks(dash_app, callback_server)
    russian_exports.register_callbacks(dash_app, callback_server)
    global_prices.register_callbacks(dash_app, callback_server)
    price_scorecard.register_callbacks(dash_app, callback_server)
    gpw_margins.register_callbacks(dash_app, callback_server)
    projects_by_country.register_callbacks(dash_app, callback_server)
    projects_by_company.register_callbacks(dash_app, callback_server)
    projects_by_time.register_callbacks(dash_app, callback_server)
    projects_by_status.register_callbacks(dash_app, callback_server)
    projects_latest.register_callbacks(dash_app, callback_server)
    projects_tracker.register_callbacks(dash_app, callback_server)
    projects_carbon.register_callbacks(dash_app, callback_server)
    
    # All callbacks are now registered from individual modules above
    
    # Clientside callback to handle dcc.Link clicks in embedded context
    # This prevents SecurityErrors when embedding from file:// by not using history.pushState directly
    dash_app.clientside_callback(
        """
        function(n_clicks, href) {
            if (!n_clicks || n_clicks === 0) {
                return window.dash_clientside.no_update;
            }
            
            // Check if the app is embedded (e.g., in an iframe from file:// origin)
            let isEmbedded = false;
            try {
                isEmbedded = window.self !== window.top;
            } catch (e) {
                isEmbedded = true;
            }

            if (isEmbedded && href) {
                // Prevent default navigation (history.pushState) for dcc.Link
                // Instead, just update the internal pathname which will trigger the main URL callback
                return href;
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('url', 'pathname', allow_duplicate=True),
        Input('tab-navigation', 'n_clicks'),
        State('url', 'href'),
        prevent_initial_call='initial_duplicate'
    )
    
    return dash_app
