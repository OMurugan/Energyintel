from app.dashboards.analytics import low_carbon_activity_by_region


def register_callbacks(app, server):
    low_carbon_activity_by_region.register_callbacks(app, server)