from app.dashboards.wcod import gpw_margins


def register_callbacks(app, server):
    gpw_margins.register_callbacks(app, server)

