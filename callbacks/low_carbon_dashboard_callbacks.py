from app.dashboards.low_carbon_investment_analytics import low_carbon_dashboard


def register_callbacks(app, server):
    low_carbon_dashboard.register_callbacks(app, server)