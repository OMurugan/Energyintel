import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import projects_by_company


dash.register_page(
    __name__,
    path="/projects-by-company",
    name="Projects by Company",
)


def layout():
    return wrap_layout("projects-company", projects_by_company.create_layout())


def init_callbacks(app, server):
    projects_by_company.register_callbacks(app, server)


