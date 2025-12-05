from app.dashboards.wcod import country_overview


def register_callbacks(app, server):
    country_overview.register_callbacks(app, server)

