import dash
from pages._utils import wrap_layout
from app.dashboards.analytics import product_exports


dash.register_page(
    __name__,
    path="/product-exports",
    name="Product Exports",
)


def layout():
    return wrap_layout("product-exports", product_exports.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/product_exports_callbacks.py
    return None
