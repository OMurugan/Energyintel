from app.dashboards.russia_analytics import crude_seaborne

def register_callbacks(app, server):
    crude_seaborne.register_callbacks(app, server)
