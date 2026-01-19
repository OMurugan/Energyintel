import os

import dash
from dash import html, dcc
import app_instance as app_mod
import utils as utils


dash.register_page(
    __name__,
    path="/",
    name="Home",
)


SECTIONS = [
    {
        "title": "Country",
        "path": "/country-overview",
        "links": [
            ("Country Overview", "/country-overview"),
            ("Country Profile", "/country-profile"),
        ],
    },
    {
        "title": "Crude",
        "path": "/crude-overview",
        "links": [
            ("Crude Overview", "/crude-overview"),
            ("Crude Profile", "/crude-profile"),
            ("Crude Comparison", "/crude-comparison"),
            ("Crude Quality Comparison", "/crude-quality-comparison"),
            ("Crude Carbon Intensity", "/crude-carbon"),
        ],
    },
    {
        "title": "Trade",
        "path": "/trade/imports-country-detail",
        "links": [
            ("Imports - Country Detail", "/trade/imports-country-detail"),
            ("Imports - Country Comparison", "/trade/imports-country-comparison"),
            ("Global Exports", "/trade/global-exports"),
            ("Russian Exports by Terminal and Exporting Company", "/trade/russian-exports"),
        ],
    },
    {
        "title": "Prices",
        "path": "/prices/global-crude-prices",
        "links": [
            ("Global Crude Prices", "/prices/global-crude-prices"),
            ("Price Scorecard for Key World Oil Grades", "/prices/price-scorecard"),
            ("Gross Product Worth and Margins", "/prices/gross-product-worth-and-margins"),
        ],
    },
    {
        "title": "Upstream Projects",
        "path": "/projects-by-country",
        "links": [
            ("Projects by Country", "/projects-by-country"),
            ("Projects by Company", "/projects-by-company"),
            ("Projects by Time", "/projects-by-time"),
            ("Projects by Status", "/projects-by-status"),
            ("Latest Updates", "/projects-latest"),           
        ],
    },
    {
        "title": "Methodology",
        "path": "/projects-tracker",
        "links": [
            ("Upstream Oil Projects Tracker", "/projects-tracker"),
            ("Carbon Intensity", "/projects-carbon"),
        ],
    },

    {
        "title": "Russian Analytics",
        "path": "/crude-seaborne",
        "links": [
            ("Crude Seaborne", "/crude-seaborne"),
            ("Crude Pipeline", "/crude-pipeline"),
            ("Product Output", "/product-output"),
            ("Product Exports", "/product-exports"),
        ],
    },
]


def layout():
    # Check if authentication is enabled
    auth_enabled = os.environ.get('ENABLE_AUTH', 'false').lower() == 'true'
    
    # Only show authentication components if auth is enabled
    auth_info = html.Div()
    
    # if auth_enabled:
    #     # Get authentication status
    #     auth_status = utils.get_embedded_auth_status()
        
    #     # Create token-based authentication info section
    #     if auth_status['is_authenticated']:
    #         permissions_list = auth_status['permissions'] if auth_status['permissions'] else []
    #         auth_info = html.Div([
    #             html.H4("🔑 Authentication Status"),
    #             html.P(f"✅ Authenticated as: {auth_status['user']}", style={'color': '#28a745', 'fontWeight': 'bold'}),
    #             html.P(f"🛡️ Permissions: {', '.join(permissions_list) if permissions_list else 'None'}"),
    #             html.P("🔗 Authentication Method: Token-based", style={'color': '#6c757d', 'fontSize': '14px'}),
    #             html.Hr(),
    #             html.H5("Token Information:"),
    #             html.Ul([
    #                 html.Li("Your token is valid and active"),
    #                 html.Li("Token-based authentication is stateless"),
    #                 html.Li("Include token in requests via URL parameter, header, or cookie"),
    #             ], style={'fontSize': '14px', 'color': '#6c757d'})
    #         ], style={'backgroundColor': '#d4edda', 'padding': '15px', 'borderRadius': '8px', 'border': '1px solid #c3e6cb'})
    #     else:
    #         auth_info = html.Div([
    #             html.H4("🔒 Authentication Required"),
    #             html.P("❌ No valid authentication token provided", style={'color': '#dc3545', 'fontWeight': 'bold'}),
    #             html.Hr(),
    #             html.H5("How to authenticate:"),
    #             html.P("Provide your authentication token using one of these methods:"),
    #             html.Ul([
    #                 html.Li(html.Code("?token=your-token-here")),
    #                 html.Li(html.Code("Authorization: Bearer your-token-here")),
    #                 html.Li(html.Code("X-API-Token: your-token-here")),
    #                 html.Li(html.Code("Cookie: auth_token=your-token-here")),
    #             ]),
    #             html.Div([
    #                 html.H6("Demo Tokens:"),
    #                 html.P([
    #                     html.Strong("Admin: "), 
    #                     html.Code("admin-token-123"),
    #                     html.Br(),
    #                     html.Strong("User: "), 
    #                     html.Code("user-token-456")
    #                 ]),
    #                 # html.P([
    #                 #     html.Strong("Try: "), 
    #                 #     html.A("Click here with admin token", 
    #                 #            href="?token=admin-token-123",
    #                 #            style={'color': '#007bff'})
    #                 # ])
    #             ], style={'backgroundColor': '#e7f3ff', 'padding': '10px', 'borderRadius': '4px', 'marginTop': '10px'})
    #         ], style={'backgroundColor': '#f8d7da', 'padding': '15px', 'borderRadius': '8px', 'border': '1px solid #f5c6cb'})
    
    return html.Div([
        html.H2("EnergyIntel Dash Pages"),
        
        # Token-based authentication status (only if auth enabled)
        auth_info,
        
        # html.H3("Dashboard Navigation"),
        html.P("Main tabs and relevant page links:"),
        
        # Simple list of sections
        html.Div([
            html.Div([
                html.H4(
                    utils.create_embedded_nav_link(section["path"], section["title"])
                ),
                html.Ul([
                    html.Li(
                        utils.create_embedded_nav_link(href, name)
                    )
                    for name, href in section["links"]
                ])
            ])
            for section in SECTIONS
        ]),
        
        # Simple utilities info
        # html.Hr(),
        # html.H4("Embedded Utilities"),
        # html.P("This page demonstrates embedded token-based authentication and navigation utilities."),
        # html.Ul([
        #     html.Li("Token-based authentication (no sessions)" if auth_enabled else "Authentication is disabled"),
        #     html.Li("All navigation links use embedded path utilities"),
        #     html.Li("Stateless authentication via tokens" if auth_enabled else "Authentication features are disabled"),
        #     html.Li("Multiple token authentication methods supported" if auth_enabled else "No authentication UI when disabled"),
        # ]),
        # html.P("Authentication is token-based. Include your token in requests for access." if auth_enabled else "To enable authentication, set ENABLE_AUTH=true in your environment variables.")
    ])


def init_callbacks(app, server):
    # No callbacks for the home page
    return None


