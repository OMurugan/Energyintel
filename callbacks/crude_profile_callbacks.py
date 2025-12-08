from app.dashboards.wcod import crude_profile


def register_callbacks(app, server):
    # crude_profile register_callbacks only expects the app
    crude_profile.register_callbacks(app)

