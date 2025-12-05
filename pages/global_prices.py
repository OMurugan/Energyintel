import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import global_prices


dash.register_page(
    __name__,
    path="/prices/global-crude-prices",
    name="Global Crude Prices",
)


def layout():
    return wrap_layout("global-prices", global_prices.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/global_prices_callbacks.py
    return None


