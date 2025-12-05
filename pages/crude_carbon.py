import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import crude_carbon


dash.register_page(
    __name__,
    path="/crude-carbon",
    name="Crude Carbon Intensity",
)


def layout():
    return wrap_layout("crude-carbon", crude_carbon.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/crude_carbon_callbacks.py
    return None


