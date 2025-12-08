from app.dashboards.wcod import price_scorecard


def register_callbacks(app, server):
    price_scorecard.register_callbacks(app, server)

