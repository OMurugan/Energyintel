import dash
from pages._utils import wrap_layout
from app.dashboards.world_gas_analytics import gas_europe_demand_yearly


dash.register_page(
    __name__,
    path="/gas/europe-demand-yearly",
    name="European Gas Demand - Yearly Demand",
)


def layout():
    return wrap_layout("gas-europe-demand-yearly", gas_europe_demand_yearly.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/gas_europe_demand_yearly_callbacks.py
    return None