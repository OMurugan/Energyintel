from app.dashboards.wcod import gas_asia_demand_yearly


def register_callbacks(app, server):
    gas_asia_demand_yearly.register_callbacks(app, server)