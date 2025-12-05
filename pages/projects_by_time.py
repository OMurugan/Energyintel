import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import projects_by_time


dash.register_page(
    __name__,
    path="/projects-by-time",
    name="Projects by Time",
)


def layout():
    return wrap_layout("projects-time", projects_by_time.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/projects_by_time_callbacks.py
    return None


