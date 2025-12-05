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
    # Callbacks are registered via callbacks/projects_by_company_callbacks.py
    return None


