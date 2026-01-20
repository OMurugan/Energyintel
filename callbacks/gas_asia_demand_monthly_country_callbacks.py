from app.dashboards.analytics import gas_asia_demand_monthly_country


def register_callbacks(app, server):
    gas_asia_demand_monthly_country.register_callbacks(app, server)