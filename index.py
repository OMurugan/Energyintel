"""Dash Pages router and layout."""

from dash import dcc, html, page_container, page_registry, Input, Output
import app_instance as app_mod
import utils as utils

# Import page modules to register them with Dash
from pages import (
    home,
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
    projects_carbon,
    # Russian Analytics Pages
    crude_seaborne,
    crude_pipeline,
    product_output,
    product_exports,
    # Gas Analytics Pages
    gas_europe_dashboard,
    gas_europe_pipeline_flows,
    gas_europe_pipeline_flows_country,
    gas_europe_imports_mix,
    gas_europe_lng_imports,
    gas_europe_demand_yearly,
    gas_europe_demand_monthly_country,
    gas_europe_demand_monthly_sector,
    gas_asia_dashboard,
    gas_asia_demand_yearly,
    gas_asia_demand_monthly_country,
    gas_asia_demand_monthly_sector,
    gas_asia_imports_mix,
    gas_asia_imports_yearly,
    # Low-Carbon Investment Pages
    low_carbon_dashboard,
    low_carbon_investments_list,
    low_carbon_activity_by_date,
    low_carbon_activity_by_region,
)

# Import callback registrars (one per dashboard)
from callbacks import (
    country_overview_callbacks,
    country_profile_callbacks,
    crude_overview_callbacks,
    crude_profile_callbacks,
    crude_comparison_callbacks,
    crude_quality_callbacks,
    crude_carbon_callbacks,
    imports_detail_callbacks,
    imports_comparison_callbacks,
    global_exports_callbacks,
    russian_exports_callbacks,
    global_prices_callbacks,
    price_scorecard_callbacks,
    gpw_margins_callbacks,
    projects_by_country_callbacks,
    projects_by_company_callbacks,
    projects_by_time_callbacks,
    projects_by_status_callbacks,
    projects_latest_callbacks,
    projects_tracker_callbacks,
    projects_carbon_callbacks,
    # Russian Analytics Callbacks
    crude_seaborne_callbacks,
    crude_pipeline_callbacks,
    product_output_callbacks,
    product_exports_callbacks,
    # Gas Analytics Callbacks
    gas_europe_dashboard_callbacks,
    gas_europe_pipeline_flows_callbacks,
    gas_europe_pipeline_flows_country_callbacks,
    gas_europe_imports_mix_callbacks,
    gas_europe_lng_imports_callbacks,
    gas_europe_demand_yearly_callbacks,
    gas_europe_demand_monthly_country_callbacks,
    gas_europe_demand_monthly_sector_callbacks,
    gas_asia_dashboard_callbacks,
    gas_asia_demand_yearly_callbacks,
    gas_asia_demand_monthly_country_callbacks,
    gas_asia_demand_monthly_sector_callbacks,
    gas_asia_imports_mix_callbacks,
    gas_asia_imports_yearly_callbacks,
    # Low-Carbon Investment Callbacks
    low_carbon_dashboard_callbacks,
    low_carbon_investments_list_callbacks,
    low_carbon_activity_by_date_callbacks,
    low_carbon_activity_by_region_callbacks,    
)

CALLBACK_REGISTRARS = [
    country_overview_callbacks.register_callbacks,
    country_profile_callbacks.register_callbacks,
    crude_overview_callbacks.register_callbacks,
    crude_profile_callbacks.register_callbacks,
    crude_comparison_callbacks.register_callbacks,
    crude_quality_callbacks.register_callbacks,
    crude_carbon_callbacks.register_callbacks,
    imports_detail_callbacks.register_callbacks,
    imports_comparison_callbacks.register_callbacks,
    global_exports_callbacks.register_callbacks,
    russian_exports_callbacks.register_callbacks,
    global_prices_callbacks.register_callbacks,
    price_scorecard_callbacks.register_callbacks,
    gpw_margins_callbacks.register_callbacks,
    projects_by_country_callbacks.register_callbacks,
    projects_by_company_callbacks.register_callbacks,
    projects_by_time_callbacks.register_callbacks,
    projects_by_status_callbacks.register_callbacks,
    projects_latest_callbacks.register_callbacks,
    projects_tracker_callbacks.register_callbacks,
    projects_carbon_callbacks.register_callbacks,
    # Russian Analytics Callbacks
    crude_seaborne_callbacks.register_callbacks,
    crude_pipeline_callbacks.register_callbacks,
    product_output_callbacks.register_callbacks,
    product_exports_callbacks.register_callbacks,
    # Gas Analytics Callbacks
    gas_europe_dashboard_callbacks.register_callbacks,
    gas_europe_pipeline_flows_callbacks.register_callbacks,
    gas_europe_pipeline_flows_country_callbacks.register_callbacks,
    gas_europe_imports_mix_callbacks.register_callbacks,
    gas_europe_lng_imports_callbacks.register_callbacks,
    gas_europe_demand_yearly_callbacks.register_callbacks,
    gas_europe_demand_monthly_country_callbacks.register_callbacks,
    gas_europe_demand_monthly_sector_callbacks.register_callbacks,
    gas_asia_dashboard_callbacks.register_callbacks,
    gas_asia_demand_yearly_callbacks.register_callbacks,
    gas_asia_demand_monthly_country_callbacks.register_callbacks,
    gas_asia_demand_monthly_sector_callbacks.register_callbacks,
    gas_asia_imports_mix_callbacks.register_callbacks,
    gas_asia_imports_yearly_callbacks.register_callbacks,
    # Low-Carbon Investment Callbacks
    low_carbon_dashboard_callbacks.register_callbacks,
    low_carbon_investments_list_callbacks.register_callbacks,
    low_carbon_activity_by_date_callbacks.register_callbacks,
    low_carbon_activity_by_region_callbacks.register_callbacks,    
]

_callbacks_initialized = False


def _init_callbacks():
    """Initialize callbacks for every page module exactly once."""
    global _callbacks_initialized
    if _callbacks_initialized:
        return

    for registrar in CALLBACK_REGISTRARS:
        registrar(app_mod.app, app_mod.server)

    _callbacks_initialized = True


def _build_nav_links():
    """Generate navigation links from Dash page registry."""
    links = []
    for page in sorted(page_registry.values(), key=lambda p: p["path"]):
        # Use the wcod-country path helper for navigation links
        nav_path = utils.get_wcod_country_path(page["path"])
        links.append(
            utils.create_embedded_nav_link(
                nav_path,
                page["name"],
                className="nav-link",
                style={"padding": "8px 12px", "textDecoration": "none"}
            )
        )
    return links


def _home_href() -> str:
    """Return home link respecting any configured routes prefix."""
    return utils.get_relative_path("/")


def _is_embedded_mode():
    """
    Detect if the app is running in embedded mode.
    Uses the utility function from utils module.
    """
    return utils.is_embedded_mode()


def _create_header():
    """Create header with authentication status and navigation."""
    auth_component = utils.create_auth_component()
    
    return html.Div([
        # Authentication status bar
        html.Div([
            html.Div([
                html.H4("Energy Intelligence Dashboard", 
                       style={'margin': 0, 'color': '#333'}),
            ], style={'flex': 1}),
            auth_component
        ], style={
            'display': 'flex', 
            'alignItems': 'center', 
            'padding': '10px 20px',
            'backgroundColor': '#ffffff',
            'borderBottom': '2px solid #007bff',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
        }),
        
        # Navigation breadcrumbs (will be updated by callback)
        html.Div(id="breadcrumb-container", style={'padding': '5px 20px'})
    ], id="main-header")


_init_callbacks()

# Base nav styling
NAV_STYLE = {
    "display": "flex",
    "gap": "8px",
    "padding": "12px 16px",
    "backgroundColor": "#f8f9fa",
    "borderBottom": "1px solid #e0e0e0",
}

# Global layout with embedded authentication integration
app_mod.app.layout = html.Div(
    [
        dcc.Location(id="url"),
        # Header is conditionally shown based on embedded mode and page
        html.Div(id="main-header"),
        page_container,
        # Add script to set embedded mode class on body and redirect if needed
        html.Script("""
            // Set embedded mode class on body if embedded
            var isEmbedded = false;
            
            if (window.location.search.includes('embedded=true') || 
                (document.referrer && !document.referrer.startsWith(window.location.origin))) {
                document.body.classList.add('embedded-mode');
                isEmbedded = true;
            }
            
            // Handle wcod-country suffix routing for embedded mode
            if (isEmbedded && window.location.pathname.endsWith('/wcod-country')) {
                var newPath = window.location.pathname.replace('/wcod-country', '') || '/';
                if (newPath !== window.location.pathname) {
                    window.history.replaceState(null, '', newPath + window.location.search);
                }
            }
            
            // If embedded and on home page, redirect to country-overview
            if (isEmbedded && (window.location.pathname === '/' || window.location.pathname === '')) {
                // Use a small delay to ensure the page is loaded
                setTimeout(function() {
                    window.location.pathname = '/country-overview';
                }, 100);
            }
        """)
    ]
)


# Callback to update header based on current page and embedded mode
# @app_mod.app.callback(
#     Output("main-header", "children"),
#     Input("url", "pathname"),
# )
# def update_navigation_and_header(pathname):
#     """Update header visibility based on current page and embedded mode."""
    
#     # Process pathname using display_content routing function
#     processed_pathname = utils.display_content(pathname)
    
#     # Check if we're in embedded mode
#     is_embedded = _is_embedded_mode()
    
#     # Only show header on home page when NOT embedded
#     if processed_pathname == "/" and not is_embedded:
#         # Create full header for home page
#         return _create_header()
#     elif not is_embedded:
#         # Show minimal header with just breadcrumbs for other pages when not embedded
#         breadcrumbs = utils.get_page_breadcrumbs(processed_pathname)
#         return html.Div([
#             html.Div(breadcrumbs, style={'padding': '5px 20px'})
#         ])
#     else:
#         # Embedded mode - no header at all
#         return html.Div()  # Empty header


# app_mod.app.layout = html.Div(
#     [
#         dcc.Location(id="url"),
#         html.Nav(
#             [
#                 dcc.Link(
#                     "Go Back",
#                     href=_home_href(),
#                     className="nav-link",
#                     refresh=True,
#                     style={"padding": "8px 12px", "textDecoration": "none"},
#                 )
#             ],
#             id="back-link-container",
#             style=NAV_STYLE,
#         ),
#         dcc.Loading(
#             id="global-loading-nav",
#             type="circle",
#             fullscreen=True,
#             children=page_container,
#         ),
#     ]
# )


# @app_mod.app.callback(
#     Output("back-link-container", "style"),
#     Input("url", "pathname"),
# )
# def _toggle_back_link(pathname: str):
#     """Hide the Go Back link when already on the home page."""
#     if pathname in ("/", "", None):
#         return {**NAV_STYLE, "display": "none"}
#     return NAV_STYLE


