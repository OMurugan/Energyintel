import dash
from pages._utils import wrap_layout
from app.dashboards.analytics import gas_europe_demand_monthly_country


dash.register_page(
    __name__,
    path="/gas/europe-demand-monthly-country",
    name="European Gas Demand - Monthly Demand by Country",
)


def layout():
    return wrap_layout("gas-europe-demand-monthly-country", gas_europe_demand_monthly_country.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/gas_europe_demand_monthly_country_callbacks.py
    return None