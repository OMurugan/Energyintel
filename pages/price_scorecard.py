import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import price_scorecard


dash.register_page(
    __name__,
    path="/prices/price-scorecard",
    name="Price Scorecard",
)


def layout():
    return wrap_layout("price-scorecard", price_scorecard.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/price_scorecard_callbacks.py
    return None


