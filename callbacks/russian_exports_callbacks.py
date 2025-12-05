from app.dashboards.wcod import russian_exports


def register_callbacks(app, server):
    russian_exports.register_callbacks(app, server)

