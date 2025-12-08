from app.dashboards.wcod import country_profile


def register_callbacks(app, server):
    country_profile.register_callbacks(app, server)

