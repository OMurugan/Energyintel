from app.dashboards.wcod import gas_asia_imports_yearly


def register_callbacks(app, server):
    gas_asia_imports_yearly.register_callbacks(app, server)