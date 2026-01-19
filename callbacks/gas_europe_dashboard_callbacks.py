from app.dashboards.wcod import gas_europe_dashboard


def register_callbacks(app, server):
    gas_europe_dashboard.register_callbacks(app, server)