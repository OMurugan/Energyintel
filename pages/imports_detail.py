import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import imports_detail


dash.register_page(
    __name__,
    path="/trade/imports-country-detail",
    name="Imports - Country Detail",
)


def layout():
    return wrap_layout("imports-detail", imports_detail.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/imports_detail_callbacks.py
    return None


