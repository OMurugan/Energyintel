from app.dashboards.wcod import global_exports


def register_callbacks(app, server):
    global_exports.register_callbacks(app, server)

