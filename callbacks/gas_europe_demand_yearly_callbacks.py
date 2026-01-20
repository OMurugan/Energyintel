from app.dashboards.analytics import gas_europe_demand_yearly


def register_callbacks(app, server):
    gas_europe_demand_yearly.register_callbacks(app, server)