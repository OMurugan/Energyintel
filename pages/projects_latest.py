import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import projects_latest


dash.register_page(
    __name__,
    path="/projects-latest",
    name="Projects Latest",
)


def layout():
    return wrap_layout("projects-latest", projects_latest.create_layout())


def init_callbacks(app, server):
    projects_latest.register_callbacks(app, server)


