from app.dashboards.wcod import imports_detail


def register_callbacks(app, server):
    imports_detail.register_callbacks(app, server)

