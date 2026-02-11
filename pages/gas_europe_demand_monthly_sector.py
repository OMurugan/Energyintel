import dash
from pages._utils import wrap_layout
from app.dashboards.world_gas_analytics import gas_europe_demand_monthly_sector


dash.register_page(
    __name__,
    path="/gas/europe-demand-monthly-sector",
    name="European Gas Demand - Monthly Demand by Sector",
)


def layout():
    return wrap_layout("gas-europe-demand-monthly-sector", gas_europe_demand_monthly_sector.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/gas_europe_demand_monthly_sector_callbacks.py
    return None