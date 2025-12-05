import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import global_exports


dash.register_page(
    __name__,
    path="/global-exports",
    name="Global Exports",
)


def layout():
    return wrap_layout("global-exports", global_exports.create_layout())


def init_callbacks(app, server):
    global_exports.register_callbacks(app, server)


