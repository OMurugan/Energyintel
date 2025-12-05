import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import projects_carbon


dash.register_page(
    __name__,
    path="/projects-carbon",
    name="Projects Carbon",
)


def layout():
    return wrap_layout("projects-carbon", projects_carbon.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/projects_carbon_callbacks.py
    return None


