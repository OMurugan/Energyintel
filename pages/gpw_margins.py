import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import gpw_margins


dash.register_page(
    __name__,
    path="/prices/gross-product-worth-and-margins",
    name="Gross Product Worth and Margins",
)


def layout():
    return wrap_layout("gpw-margins", gpw_margins.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/gpw_margins_callbacks.py
    return None


