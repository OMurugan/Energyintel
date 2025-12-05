import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import gpw_margins


dash.register_page(
    __name__,
    path="/gpw-margins",
    name="GPW Margins",
)


def layout():
    return wrap_layout("gpw-margins", gpw_margins.create_layout())


def init_callbacks(app, server):
    gpw_margins.register_callbacks(app, server)


