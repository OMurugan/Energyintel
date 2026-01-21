from app.dashboards.analytics import product_output


def register_callbacks(app, server):
    product_output.register_callbacks(app, server)