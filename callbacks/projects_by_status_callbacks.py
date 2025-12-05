from app.dashboards.wcod import projects_by_status


def register_callbacks(app, server):
    projects_by_status.register_callbacks(app, server)

