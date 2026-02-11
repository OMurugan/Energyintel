import dash
from pages._utils import wrap_layout
from app.dashboards.world_gas_analytics import gas_asia_dashboard


dash.register_page(
    __name__,
    path="/gas/asia-dashboard",
    name="Asia World Gas Dashboard",
)


def layout():
    return wrap_layout("gas-asia-dashboard", gas_asia_dashboard.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/gas_asia_dashboard_callbacks.py
    return None