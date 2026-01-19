import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import gas_europe_dashboard


dash.register_page(
    __name__,
    path="/gas/europe-dashboard",
    name="Europe World Gas Data Dashboard",
)


def layout():
    return wrap_layout("gas-europe-dashboard", gas_europe_dashboard.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/gas_europe_dashboard_callbacks.py
    return None