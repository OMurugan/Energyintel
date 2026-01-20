from app.dashboards.analytics import gas_asia_dashboard


def register_callbacks(app, server):
    gas_asia_dashboard.register_callbacks(app, server)