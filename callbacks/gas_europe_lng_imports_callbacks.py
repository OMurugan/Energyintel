from app.dashboards.wcod import gas_europe_lng_imports


def register_callbacks(app, server):
    gas_europe_lng_imports.register_callbacks(app, server)