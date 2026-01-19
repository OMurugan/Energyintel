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
    {
        "title": "World Gas Analytics Tool",
        "path": "/gas/europe-dashboard",
        "links": [
            # ("Europe World Gas Data Dashboard", "/gas/europe-dashboard"),
            ("European Gas Trade - Pipeline Flows to Europe", "/gas/europe-pipeline-flows"),
            ("European Gas Trade - Pipeline Flows by Country", "/gas/europe-pipeline-flows-country"),
            ("European Gas Trade - Gas Imports Mix by Country", "/gas/europe-imports-mix"),
            ("European Gas Trade - LNG Imports by Terminal", "/gas/europe-lng-imports"),
            ("European Gas Demand - Yearly Demand", "/gas/europe-demand-yearly"),
            ("European Gas Demand - Monthly Demand by Country", "/gas/europe-demand-monthly-country"),
            ("European Gas Demand - Monthly Demand by Sector", "/gas/europe-demand-monthly-sector"),
            # ("Asia World Gas Dashboard", "/gas/asia-dashboard"),
            ("Asian Gas Demand - Yearly Gas Demand", "/gas/asia-demand-yearly"),
            ("Asian Gas Demand - Monthly Demand by Country", "/gas/asia-demand-monthly-country"),
            ("Asian Gas Demand - Monthly Demand by Sector", "/gas/asia-demand-monthly-sector"),
            ("Asian Gas Trade - Gas Import Mix by Country", "/gas/asia-imports-mix"),
            ("Asian Gas Trade - Yearly Imports by Origin", "/gas/asia-imports-yearly"),
        ],
    },
    {
        "title": "Low-Carbon Investment Analytics Tool",
        "path": "/low-carbon/dashboard",
        "links": [
            # ("Low-Carbon Investment Dashboard", "/low-carbon/dashboard"),
            ("List of Tracked Investments", "/low-carbon/investments-list"),
            ("Activity by Date Announced", "/low-carbon/activity-by-date"),
            ("Activity by Region", "/low-carbon/activity-by-region"),
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


