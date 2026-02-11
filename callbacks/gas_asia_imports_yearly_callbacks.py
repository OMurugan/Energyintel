from app.dashboards.world_gas_analytics import gas_asia_imports_yearly


def register_callbacks(app, server):
    gas_asia_imports_yearly.register_callbacks(app, server)