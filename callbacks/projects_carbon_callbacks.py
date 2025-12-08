from app.dashboards.wcod import projects_carbon


def register_callbacks(app, server):
    projects_carbon.register_callbacks(app, server)

