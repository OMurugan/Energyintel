from app.dashboards.wcod import crude_carbon


def register_callbacks(app, server):
    crude_carbon.register_callbacks(app, server)

