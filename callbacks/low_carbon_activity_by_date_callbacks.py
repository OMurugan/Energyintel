from app.dashboards.analytics import low_carbon_activity_by_date


def register_callbacks(app, server):
    low_carbon_activity_by_date.register_callbacks(app, server)