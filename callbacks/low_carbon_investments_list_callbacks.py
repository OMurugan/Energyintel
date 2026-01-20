from app.dashboards.analytics import low_carbon_investments_list


def register_callbacks(app, server):
    low_carbon_investments_list.register_callbacks(app, server)