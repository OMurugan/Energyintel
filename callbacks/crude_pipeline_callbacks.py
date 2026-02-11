from app.dashboards.russia_analytics import crude_pipeline


def register_callbacks(app, server):
    crude_pipeline.register_callbacks(app, server)