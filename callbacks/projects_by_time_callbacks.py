from app.dashboards.wcod import projects_by_time


def register_callbacks(app, server):
    projects_by_time.register_callbacks(app, server)

