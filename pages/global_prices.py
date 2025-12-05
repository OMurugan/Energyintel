import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import global_prices


dash.register_page(
    __name__,
    path="/global-prices",
    name="Global Prices",
)


def layout():
    return wrap_layout("global-prices", global_prices.create_layout())


def init_callbacks(app, server):
    global_prices.register_callbacks(app, server)


