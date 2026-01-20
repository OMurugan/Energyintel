from app.dashboards.analytics import gas_europe_imports_mix


def register_callbacks(app, server):
    gas_europe_imports_mix.register_callbacks(app, server)