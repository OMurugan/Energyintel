import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import crude_quality


dash.register_page(
    __name__,
    path="/crude-quality-comparison",
    name="Crude Quality Comparison",
)


def layout():
    return wrap_layout("crude-quality", crude_quality.create_layout())


def init_callbacks(app, server):
    # crude_quality module does not expose register_callbacks; nothing to initialize
    return None


