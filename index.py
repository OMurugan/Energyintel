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

# Import callback registrars (one per dashboard)
from callbacks import (
    country_overview_callbacks,
    country_profile_callbacks,
    crude_overview_callbacks,
    crude_profile_callbacks,
    crude_comparison_callbacks,
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


def _page_href(page: dict) -> str:
    """Return a link href that respects the configured routes prefix."""
    relative = page.get("relative_path")
    if relative:
        return relative

    prefix = getattr(app_mod, "ROUTES_PREFIX", "") or ""
    path = page["path"]
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{prefix}{path.lstrip('/')}" if prefix else path


def _build_nav_links():
    """Generate navigation links from Dash page registry."""
    links = []
    for page in sorted(page_registry.values(), key=lambda p: p["path"]):
        links.append(
            dcc.Link(
                page["name"],
                href=_page_href(page),
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


