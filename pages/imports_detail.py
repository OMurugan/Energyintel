import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import imports_detail


dash.register_page(
    __name__,
    path="/imports-detail",
    name="Imports Detail",
)


def layout():
    return wrap_layout("imports-detail", imports_detail.create_layout())


def init_callbacks(app, server):
    imports_detail.register_callbacks(app, server)


