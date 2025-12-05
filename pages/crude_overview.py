import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import crude_overview


dash.register_page(
    __name__,
    path="/crude-overview",
    name="Crude Overview",
)


def layout():
    return wrap_layout("crude-overview", crude_overview.create_layout())


def init_callbacks(app, server):
    crude_overview.register_callbacks(app, server)


