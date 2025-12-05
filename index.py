"""Dash Pages router and layout."""

from dash import dcc, html, page_container, page_registry
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

PAGE_MODULES = [
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
]

_callbacks_initialized = False


def _init_callbacks():
    """Initialize callbacks for every page module exactly once."""
    global _callbacks_initialized
    if _callbacks_initialized:
        return

    for module in PAGE_MODULES:
        init_fn = getattr(module, "init_callbacks", None)
        if callable(init_fn):
            init_fn(app_mod.app, app_mod.server)

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


_init_callbacks()

# Debug aid: print registered page paths once at startup
# try:
#     print(
#         "Registered Dash pages:",
#         [p["path"] for p in sorted(page_registry.values(), key=lambda p: p["path"])],
#     )
# except Exception:
#     pass


# app_mod.app.layout = html.Div(
#     [
#         dcc.Location(id="url"),
#         html.Nav(
#             _build_nav_links(),
#             style={
#                 "display": "flex",
#                 "gap": "8px",
#                 "padding": "12px 16px",
#                 "backgroundColor": "#f8f9fa",
#                 "borderBottom": "1px solid #e0e0e0",
#             },
#         ),
#         page_container,
#     ]
# )


