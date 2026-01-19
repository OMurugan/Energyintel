import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import product_output


dash.register_page(
    __name__,
    path="/product-output",
    name="Product Output",
)


def layout():
    return wrap_layout("product-output", product_output.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/product_output_callbacks.py
    return None
