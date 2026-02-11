from app.dashboards.world_gas_analytics import gas_asia_demand_monthly_country


def register_callbacks(app, server):
    gas_asia_demand_monthly_country.register_callbacks(app, server)