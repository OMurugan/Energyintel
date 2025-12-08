from app.dashboards.wcod import crude_overview


def register_callbacks(app, server):
    crude_overview.register_callbacks(app, server)

