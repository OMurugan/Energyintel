import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import imports_comparison


dash.register_page(
    __name__,
    path="/trade/imports-country-comparison",
    name="Imports - Country Comparison",
)


def layout():
    return wrap_layout("imports-comparison", imports_comparison.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/imports_comparison_callbacks.py
    return None


