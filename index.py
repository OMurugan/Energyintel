"""Dash Pages router and layout."""

from dash import dcc, html, page_container, page_registry, Input, Output
import app_instance as app_mod

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
        links.append(
            dcc.Link(
                page["name"],
                href=page["path"],
                className="nav-link",
                refresh=True,  # force full navigation to avoid history.pushState issues in embeds
                style={"padding": "8px 12px", "textDecoration": "none"},
            )
        )
    return links


def _home_href() -> str:
    """Return home link respecting any configured routes prefix."""
    prefix = getattr(app_mod, "ROUTES_PREFIX", "") or ""
    return prefix or "/"


_init_callbacks()

# Base nav styling
NAV_STYLE = {
    "display": "flex",
    "gap": "8px",
    "padding": "12px 16px",
    "backgroundColor": "#f8f9fa",
    "borderBottom": "1px solid #e0e0e0",
}

# Global layout with a fullscreen loader around page content
app_mod.app.layout = html.Div(
    [
        dcc.Location(id="url"),
        dcc.Loading(
            id="global-loading",
            type="circle",
            fullscreen=True,
            children=page_container,
        ),
    ]
)


app_mod.app.layout = html.Div(
    [
        dcc.Location(id="url"),
        html.Nav(
            [
                dcc.Link(
                    "Go Back",
                    href=_home_href(),
                    className="nav-link",
                    refresh=True,
                    style={"padding": "8px 12px", "textDecoration": "none"},
                )
            ],
            id="back-link-container",
            style=NAV_STYLE,
        ),
        dcc.Loading(
            id="global-loading-nav",
            type="circle",
            fullscreen=True,
            children=page_container,
        ),
    ]
)


@app_mod.app.callback(
    Output("back-link-container", "style"),
    Input("url", "pathname"),
)
def _toggle_back_link(pathname: str):
    """Hide the Go Back link when already on the home page."""
    if pathname in ("/", "", None):
        return {**NAV_STYLE, "display": "none"}
    return NAV_STYLE


