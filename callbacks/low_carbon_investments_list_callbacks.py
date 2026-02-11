from app.dashboards.low_carbon_investment_analytics import low_carbon_investments_list


def register_callbacks(app, server):
    low_carbon_investments_list.register_callbacks(app, server)