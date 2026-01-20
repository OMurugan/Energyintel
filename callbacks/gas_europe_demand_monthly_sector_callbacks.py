from app.dashboards.analytics import gas_europe_demand_monthly_sector


def register_callbacks(app, server):
    gas_europe_demand_monthly_sector.register_callbacks(app, server)