from app.dashboards.wcod import gas_europe_demand_monthly_country


def register_callbacks(app, server):
    gas_europe_demand_monthly_country.register_callbacks(app, server)