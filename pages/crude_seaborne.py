import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import crude_seaborne


dash.register_page(
    __name__,
    path="/crude-seaborne",
    name="Crude Seaborne",
)


def layout():
    return wrap_layout("crude-seaborne", crude_seaborne.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/crude_seaborne_callbacks.py
    return None
