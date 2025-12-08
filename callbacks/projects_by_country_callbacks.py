from app.dashboards.wcod import projects_by_country


def register_callbacks(app, server):
    projects_by_country.register_callbacks(app, server)

