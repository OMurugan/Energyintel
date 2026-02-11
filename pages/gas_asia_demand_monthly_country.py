import dash
from pages._utils import wrap_layout
from app.dashboards.world_gas_analytics import gas_asia_demand_monthly_country


dash.register_page(
    __name__,
    path="/gas/asia-demand-monthly-country",
    name="Asian Gas Demand - Monthly Demand by Country",
)


def layout():
    return wrap_layout("gas-asia-demand-monthly-country", gas_asia_demand_monthly_country.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/gas_asia_demand_monthly_country_callbacks.py
    return None