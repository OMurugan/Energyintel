import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import crude_comparison


dash.register_page(
    __name__,
    path="/crude-comparison",
    name="Crude Comparison",
)


def layout():
    return wrap_layout("crude-comparison", crude_comparison.create_layout(None))


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/crude_comparison_callbacks.py
    return None


