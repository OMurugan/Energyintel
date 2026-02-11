from app.dashboards.world_gas_analytics import gas_asia_demand_yearly


def register_callbacks(app, server):
    gas_asia_demand_yearly.register_callbacks(app, server)