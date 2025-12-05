import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import projects_by_status


dash.register_page(
    __name__,
    path="/projects-by-status",
    name="Projects by Status",
)


def layout():
    return wrap_layout("projects-status", projects_by_status.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/projects_by_status_callbacks.py
    return None


