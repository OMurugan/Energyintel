import dash
from pages._utils import wrap_layout
from app.dashboards.world_gas_analytics import gas_asia_demand_yearly


dash.register_page(
    __name__,
    path="/gas/asia-demand-yearly",
    name="Asian Gas Demand - Yearly Gas Demand",
)


def layout():
    return wrap_layout("gas-asia-demand-yearly", gas_asia_demand_yearly.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/gas_asia_demand_yearly_callbacks.py
    return None