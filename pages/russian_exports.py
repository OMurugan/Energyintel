import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import russian_exports


dash.register_page(
    __name__,
    path="/trade/russian-exports",
    name="Russian Exports",
)


def layout():
    return wrap_layout("russian-exports", russian_exports.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/russian_exports_callbacks.py
    return None


