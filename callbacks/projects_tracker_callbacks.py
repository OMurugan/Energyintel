from app.dashboards.wcod import projects_tracker


def register_callbacks(app, server):
    projects_tracker.register_callbacks(app, server)

