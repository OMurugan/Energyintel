from app.dashboards.wcod import crude_comparison


def register_callbacks(app, server):
    crude_comparison.register_callbacks(app, server)

