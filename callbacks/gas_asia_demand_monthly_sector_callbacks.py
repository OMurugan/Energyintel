from app.dashboards.analytics import gas_asia_demand_monthly_sector


def register_callbacks(app, server):
    gas_asia_demand_monthly_sector.register_callbacks(app, server)