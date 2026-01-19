from app.dashboards.wcod import gas_europe_demand_yearly


def register_callbacks(app, server):
    gas_europe_demand_yearly.register_callbacks(app, server)