from app.dashboards.wcod import imports_comparison


def register_callbacks(app, server):
    imports_comparison.register_callbacks(app, server)

