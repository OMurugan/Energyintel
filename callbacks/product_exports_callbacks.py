from app.dashboards.analytics import product_exports


def register_callbacks(app, server):
    product_exports.register_callbacks(app, server)