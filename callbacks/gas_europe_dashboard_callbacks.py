from app.dashboards.world_gas_analytics import gas_europe_dashboard


def register_callbacks(app, server):
    gas_europe_dashboard.register_callbacks(app, server)