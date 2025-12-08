from app.dashboards.wcod import projects_latest


def register_callbacks(app, server):
    projects_latest.register_callbacks(app, server)

