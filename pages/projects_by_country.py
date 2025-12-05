import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import projects_by_country


dash.register_page(
    __name__,
    path="/projects-by-country",
    name="Projects by Country",
)


def layout():
    return wrap_layout("projects-country", projects_by_country.create_layout())


def init_callbacks(app, server):
    projects_by_country.register_callbacks(app, server)


