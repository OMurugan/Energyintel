from app.dashboards.world_gas_analytics import gas_asia_imports_mix


def register_callbacks(app, server):
    gas_asia_imports_mix.register_callbacks(app, server)