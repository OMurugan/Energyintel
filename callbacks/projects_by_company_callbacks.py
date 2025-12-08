from app.dashboards.wcod import projects_by_company


def register_callbacks(app, server):
    projects_by_company.register_callbacks(app, server)

