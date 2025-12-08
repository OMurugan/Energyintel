from app.dashboards.wcod import global_prices


def register_callbacks(app, server):
    global_prices.register_callbacks(app, server)

