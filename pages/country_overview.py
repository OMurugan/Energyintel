import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import country_overview


dash.register_page(
    __name__,
    path="/country-overview",
    name="Country Overview",
)


def layout():
    return wrap_layout("country-overview", country_overview.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/country_overview_callbacks.py
    return None


