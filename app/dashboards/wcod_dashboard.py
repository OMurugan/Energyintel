"""
World Crude Oil Data (WCoD) Dashboard
Comprehensive dashboard with all tabs and sub-menus matching Energy Intelligence website
"""
import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
from urllib.parse import parse_qs
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from flask import current_app
from app import create_dash_app
from app.models import (
    Country, Production, Exports, Reserves, Imports,
    Crude, CrudePrice, UpstreamProject, Company
)
from app import db
from sqlalchemy import func, extract, and_, or_
from datetime import datetime, timedelta

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


def create_wcod_dashboard(server, url_base_pathname):
    """Create comprehensive WCoD dashboard with tab navigation"""
    dash_app = create_dash_app(server, url_base_pathname)
    
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
        
        # Header Navigation (hidden for country profile iframe)
        html.Div(id='header-container', children=[
            html.Nav([
                html.Div([
                    html.A(
                        "Energy Intelligence",
                        href="/",
                        className="navbar-brand",
                        style={
                            'fontWeight': '600',
                            'fontSize': '1.5rem',
                            'color': '#fff',
                            'textDecoration': 'none'
                        }
                    ),
                    html.Div([
                        html.A("Home", href="/", className="nav-link", style={'color': '#b0b0b0', 'textDecoration': 'none', 'margin': '0 0.5rem'}),
                        html.A("News", href="/news", className="nav-link", style={'color': '#b0b0b0', 'textDecoration': 'none', 'margin': '0 0.5rem'}),
                        html.A("Data", href="/data", className="nav-link", style={'color': '#b0b0b0', 'textDecoration': 'none', 'margin': '0 0.5rem'}),
                        html.A("WCoD", href="/wcod/", className="nav-link", style={'color': '#fff', 'textDecoration': 'none', 'margin': '0 0.5rem', 'fontWeight': '600'}),
                        html.A("Research", href="/research", className="nav-link", style={'color': '#b0b0b0', 'textDecoration': 'none', 'margin': '0 0.5rem'}),
                        html.A("Services", href="/services", className="nav-link", style={'color': '#b0b0b0', 'textDecoration': 'none', 'margin': '0 0.5rem'}),
                        html.A("About", href="/about", className="nav-link", style={'color': '#b0b0b0', 'textDecoration': 'none', 'margin': '0 0.5rem'}),
                        html.A("Contact", href="/contact", className="nav-link", style={'color': '#b0b0b0', 'textDecoration': 'none', 'margin': '0 0.5rem'}),
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginLeft': 'auto'})
                ], style={'display': 'flex', 'alignItems': 'center', 'width': '100%', 'maxWidth': '1200px', 'margin': '0 auto', 'padding': '0 20px'})
            ], style={'background': '#1a1a1a', 'padding': '1rem 0', 'marginBottom': '0'}),
            
            # Page Header
            html.Div([
                html.H1(
                    "World Crude Oil Data",
                    className="mb-2",
                    style={'color': '#2c3e50', 'fontWeight': '600', 'fontSize': '32px'}
                ),
                html.P(
                    "Crude fundamentals, including production, trade, quality and pricing data.",
                    style={'color': '#7f8c8d', 'marginBottom': '20px', 'fontSize': '16px'}
                )
            ], className="container-fluid", style={'padding': '30px', 'background': 'white', 'marginBottom': '0'})
        ]),  # Close header-container
        
        # Filter & Search Section Header
        html.Div([
            html.Div([
                html.H2(
                    "Filter & Search",
                    style={
                        'fontSize': '14px',
                        'fontWeight': '600',
                        'color': '#666666',
                        'textTransform': 'uppercase',
                        'letterSpacing': '0.5px',
                        'margin': '0',
                        'padding': '16px 30px 12px 30px',
                        'lineHeight': '1.2'
                    }
                )
            ], style={'background': '#e5e5e5', 'borderBottom': 'none', 'margin': '0', 'padding': '0'})
        ], className="container-fluid", style={'padding': '0', 'background': '#e5e5e5', 'width': '100%', 'margin': '0'}),
        
        # Tab Navigation - matching Image 1 design (white tabs with rounded corners on light gray background)
        html.Div([
            html.Div([
                dcc.Link(
                    html.Div([
                        html.Img(
                            src="https://www.energyintel.com/styleguide/assets/tabs/svgs/globe_inactive.svg",
                            id="tab-icon-country",
                            style={
                                'height': '40px',
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
                        'padding': '15px 40px',
                        'cursor': 'pointer',
                        'height': '100%'
                    }),
                    href='/wcod/',
                    id='tab-link-country',
                    style={'textDecoration': 'none', 'transition': 'all 0.2s ease'}
                ),
                dcc.Link(
                    html.Div([
                        html.Img(
                            src="https://www.energyintel.com/styleguide/assets/tabs/svgs/oil_inactive.svg",
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
                        'padding': '15px 40px',
                        'cursor': 'pointer',
                        'height': '100%'
                    }),
                    href='/wcod/crude-overview',
                    id='tab-link-crude',
                    style={'textDecoration': 'none', 'transition': 'all 0.2s ease'}
                ),
                dcc.Link(
                    html.Div([
                        html.Img(
                            src="https://www.energyintel.com/styleguide/assets/tabs/svgs/trade_inactive.svg",
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
                        'padding': '15px 40px',
                        'cursor': 'pointer',
                        'height': '100%'
                    }),
                    href='/wcod/trade/imports-country-detail',
                    id='tab-link-trade',
                    style={'textDecoration': 'none', 'transition': 'all 0.2s ease'}
                ),
                dcc.Link(
                    html.Div([
                        html.Img(
                            src="https://www.energyintel.com/styleguide/assets/tabs/svgs/prices_inactive.svg",
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
                        'padding': '15px 40px',
                        'cursor': 'pointer',
                        'height': '100%'
                    }),
                    href='/wcod/prices/global-crude-prices',
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
                        'padding': '15px 40px',
                        'cursor': 'pointer',
                        'height': '100%'
                    }),
                    href='/wcod/upstream-projects/projects-by-country',
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
                        'padding': '15px 40px',
                        'cursor': 'pointer',
                        'height': '100%'
                    }),
                    href='/wcod-upstream-oil-projects-tracker-methodology',
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
        ], className='row', style={'margin': '0', 'background': 'white'}),
        
        # Main Content Area
        html.Div([
            html.Div([
                html.Div(id='tab-content', style={'background': 'white', 'minHeight': '600px'})
            ], className='col-md-12', style={'padding': '24px', 'background': '#f8f9fa'})
        ], className='row', style={'margin': '0', 'background': 'white'}),
        
        # Store for current sub-menu selection
        dcc.Store(id='current-submenu', data='country-overview'),
        
        # Footer (hidden for country profile iframe)
        html.Div(id='footer-container', children=[
            html.Footer([
                html.Div([
                    html.Div([
                        html.H5("Energy Intelligence", style={'color': '#fff', 'marginBottom': '15px'}),
                        html.P("Comprehensive energy data and analysis platform.", style={'color': '#b0b0b0', 'fontSize': '14px'})
                    ], className='col-md-4'),
                    html.Div([
                        html.H5("Quick Links", style={'color': '#fff', 'marginBottom': '15px'}),
                        html.Ul([
                            html.Li(html.A("Data", href="/data", style={'color': '#b0b0b0', 'textDecoration': 'none'})),
                            html.Li(html.A("WCoD", href="/wcod/", style={'color': '#b0b0b0', 'textDecoration': 'none'})),
                            html.Li(html.A("Research", href="/research", style={'color': '#b0b0b0', 'textDecoration': 'none'})),
                        ], style={'listStyle': 'none', 'padding': '0'})
                    ], className='col-md-4'),
                    html.Div([
                        html.H5("Contact", style={'color': '#fff', 'marginBottom': '15px'}),
                        html.P("info@energyintel.com", style={'color': '#b0b0b0', 'fontSize': '14px'})
                    ], className='col-md-4'),
                ], className='row', style={'maxWidth': '1200px', 'margin': '0 auto', 'padding': '0 20px'}),
                html.Hr(style={'background': '#333', 'margin': '2rem 0 1rem', 'border': 'none', 'height': '1px'}),
                html.Div([
                    html.P("© 2024 Energy Intelligence. All rights reserved.", 
                           style={'color': '#b0b0b0', 'textAlign': 'center', 'fontSize': '14px', 'margin': '0'})
                ])
            ], style={'background': '#1a1a1a', 'color': '#b0b0b0', 'padding': '3rem 0 1rem', 'marginTop': '4rem'})
        ])
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
    @callback(
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
            '/wcod-country-overview',
            '/wcod/crude-overview',
            '/wcod-crude-profile',
            '/wcod-crude-comparison',
            '/wcod-crude-quality-comparison',
            '/wcod-crude-carbon-intensity',
            '/wcod/trade/',
            '/wcod/prices/',
            '/wcod/upstream-projects/'
        ]
        is_wcod_path = pathname_str.startswith('/wcod') or pathname_str.startswith('/wcod-')
        should_hide = (bool(is_iframe) or embed_flag) and (is_wcod_path or any(page in pathname_str for page in iframe_pages))
        if should_hide:
            return {'display': 'none'}, {'display': 'none'}
        return {'display': 'block'}, {'display': 'block'}
    
    # Callback to handle URL routing - runs on initial load to set correct tab/submenu from URL
    @callback(
        [Output('main-tabs', 'value'),
         Output('current-submenu', 'data', allow_duplicate=True)],
        [Input('url', 'pathname'),
         Input('url', 'search')],
        prevent_initial_call='initial_duplicate'  # Required when using allow_duplicate=True
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
            '/wcod-country-overview': ('country-tab', 'country-profile'),
            # Crude tab
            '/wcod/crude-overview': ('crude-tab', 'crude-overview'),
            '/wcod-crude-profile': ('crude-tab', 'crude-profile'),
            '/wcod-crude-comparison': ('crude-tab', 'crude-comparison'),
            '/wcod-crude-quality-comparison': ('crude-tab', 'crude-quality'),
            '/wcod-crude-carbon-intensity': ('crude-tab', 'crude-carbon'),
            # Trade tab
            '/wcod/trade/imports-country-detail': ('trade-tab', 'imports-detail'),
            '/wcod/trade/imports-country-comparison': ('trade-tab', 'imports-comparison'),
            '/wcod/trade/global-exports': ('trade-tab', 'global-exports'),
            '/wcod/trade/russian-exports-by-terminal-and-exporting-company': ('trade-tab', 'russian-exports'),
            # Prices tab
            '/wcod/prices/global-crude-prices': ('prices-tab', 'global-prices'),
            '/wcod/prices/price-scorecard-for-key-world-oil-grades': ('prices-tab', 'price-scorecard'),
            '/wcod/prices/gross-product-worth-and-margins': ('prices-tab', 'gpw-margins'),
            # Upstream Projects tab
            '/wcod/upstream-projects/projects-by-country': ('projects-tab', 'projects-country'),
            '/wcod/upstream-projects/projects-by-company': ('projects-tab', 'projects-company'),
            '/wcod/upstream-projects/projects-by-time': ('projects-tab', 'projects-time'),
            '/wcod-upstream-projects/projects-by-status': ('projects-tab', 'projects-status'),
            '/wcod-upstream-projects-related-articles': ('projects-tab', 'projects-latest'),
            # Methodology tab
            '/wcod-upstream-oil-projects-tracker-methodology': ('methodology-tab', 'projects-tracker'),
            '/wcod-carbon-intensity-methodology': ('methodology-tab', 'projects-carbon'),
        }
        
        tab, submenu = url_mapping.get(effective_pathname, ('country-tab', 'country-overview'))
        return tab, submenu
    
    # Callback to highlight active tab - runs on initial load and when tab changes
    @callback(
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
            'height': '75px',
            'transform': 'translateY(0)'
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
            'padding': '10px',
            'transform': 'translateY(-4px)'
        }
        
        # Icon sources - switch between active and inactive SVGs (using external URLs)
        country_icon = 'https://www.energyintel.com/styleguide/assets/tabs/svgs/globe_active.svg' if active_tab == 'country-tab' else 'https://www.energyintel.com/styleguide/assets/tabs/svgs/globe_inactive.svg'
        crude_icon = 'https://www.energyintel.com/styleguide/assets/tabs/svgs/oil_active.svg' if active_tab == 'crude-tab' else 'https://www.energyintel.com/styleguide/assets/tabs/svgs/oil_inactive.svg'
        trade_icon = 'https://www.energyintel.com/styleguide/assets/tabs/svgs/trade_active.svg' if active_tab == 'trade-tab' else 'https://www.energyintel.com/styleguide/assets/tabs/svgs/trade_inactive.svg'
        prices_icon = 'https://www.energyintel.com/styleguide/assets/tabs/svgs/prices_active.svg' if active_tab == 'prices-tab' else 'https://www.energyintel.com/styleguide/assets/tabs/svgs/prices_inactive.svg'
        
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
    @callback(
        Output('submenu-container', 'children'),
        [Input('main-tabs', 'value'),
         Input('url', 'pathname'),
         Input('current-submenu', 'data')],
        prevent_initial_call=False
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
                '/wcod-crude-quality-comparison': 'crude-quality',
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
        # Create URL paths for each submenu item - matching exact user-provided URLs
        url_paths = {
            'country-overview': '/wcod/',
            'country-profile': '/wcod-country-overview',
            'crude-overview': '/wcod/crude-overview',
            'crude-profile': '/wcod-crude-profile',
            'crude-comparison': '/wcod-crude-comparison',
            'crude-quality': '/wcod-crude-quality-comparison',
            'crude-carbon': '/wcod-crude-carbon-intensity',
            'imports-detail': '/wcod/trade/imports-country-detail',
            'imports-comparison': '/wcod/trade/imports-country-comparison',
            'global-exports': '/wcod/trade/global-exports',
            'russian-exports': '/wcod/trade/russian-exports-by-terminal-and-exporting-company',
            'global-prices': '/wcod/prices/global-crude-prices',
            'price-scorecard': '/wcod/prices/price-scorecard-for-key-world-oil-grades',
            'gpw-margins': '/wcod/prices/gross-product-worth-and-margins',
            'projects-country': '/wcod/upstream-projects/projects-by-country',
            'projects-company': '/wcod/upstream-projects/projects-by-company',
            'projects-time': '/wcod/upstream-projects/projects-by-time',
            'projects-status': '/wcod-upstream-projects/projects-by-status',
            'projects-latest': '/wcod-upstream-projects-related-articles',
            'projects-tracker': '/wcod-upstream-oil-projects-tracker-methodology',
            'projects-carbon': '/wcod-carbon-intensity-methodology',
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
                    href=url_paths.get(item['value'], '/wcod/'),
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
    @callback(
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
                elif '/wcod-crude-quality-comparison' in effective_page:
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
            if submenu == 'projects-country':
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
    @callback(
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
            'country-overview': '/wcod/',
            'country-profile': '/wcod-country-overview',
            'crude-overview': '/wcod/crude-overview',
            'crude-profile': '/wcod-crude-profile',
            'crude-comparison': '/wcod-crude-comparison',
            'crude-quality': '/wcod-crude-quality-comparison',
            'crude-carbon': '/wcod-crude-carbon-intensity',
            'imports-detail': '/wcod/trade/imports-country-detail',
            'imports-comparison': '/wcod/trade/imports-country-comparison',
            'global-exports': '/wcod/trade/global-exports',
            'russian-exports': '/wcod/trade/russian-exports-by-terminal-and-exporting-company',
            'global-prices': '/wcod/prices/global-crude-prices',
            'price-scorecard': '/wcod/prices/price-scorecard-for-key-world-oil-grades',
            'gpw-margins': '/wcod/prices/gross-product-worth-and-margins',
            'projects-country': '/wcod/upstream-projects/projects-by-country',
            'projects-company': '/wcod/upstream-projects/projects-by-company',
            'projects-time': '/wcod/upstream-projects/projects-by-time',
            'projects-status': '/wcod-upstream-projects/projects-by-status',
            'projects-latest': '/wcod-upstream-projects-related-articles',
            'projects-tracker': '/wcod-upstream-oil-projects-tracker-methodology',
            'projects-carbon': '/wcod-carbon-intensity-methodology',
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
                href=url_paths.get(item['value'], '/wcod/'),
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
        return country_profile.create_layout(server)
    
    def render_crude_overview():
        """Crude Overview view"""
        return crude_overview.create_layout()
    
    def render_crude_profile():
        """Crude Profile view"""
        return crude_profile.create_layout(server)
    
    def render_crude_comparison():
        """Crude Comparison view"""
        return crude_comparison.create_layout(server)
    
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
    country_overview.register_callbacks(dash_app, server)
    country_profile.register_callbacks(dash_app, server)
    crude_overview.register_callbacks(dash_app, server)
    crude_profile.register_callbacks(dash_app, server)
    crude_comparison.register_callbacks(dash_app)
    crude_quality.register_callbacks(dash_app, server)
    crude_carbon.register_callbacks(dash_app, server)
    imports_detail.register_callbacks(dash_app, server)
    imports_comparison.register_callbacks(dash_app, server)
    global_exports.register_callbacks(dash_app, server)
    russian_exports.register_callbacks(dash_app, server)
    global_prices.register_callbacks(dash_app, server)
    price_scorecard.register_callbacks(dash_app, server)
    gpw_margins.register_callbacks(dash_app, server)
    projects_by_country.register_callbacks(dash_app, server)
    projects_by_company.register_callbacks(dash_app, server)
    projects_by_time.register_callbacks(dash_app, server)
    projects_by_status.register_callbacks(dash_app, server)
    projects_latest.register_callbacks(dash_app, server)
    projects_tracker.register_callbacks(dash_app, server)
    projects_carbon.register_callbacks(dash_app, server)
    
    # All callbacks are now registered from individual modules above
    
    return dash_app
