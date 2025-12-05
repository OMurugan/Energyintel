import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import imports_comparison


dash.register_page(
    __name__,
    path="/imports-comparison",
    name="Imports Comparison",
)


def layout():
    return wrap_layout("imports-comparison", imports_comparison.create_layout())


def init_callbacks(app, server):
    imports_comparison.register_callbacks(app, server)


