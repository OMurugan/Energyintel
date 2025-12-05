import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import projects_tracker


dash.register_page(
    __name__,
    path="/projects-tracker",
    name="Projects Tracker",
)


def layout():
    return wrap_layout("projects-tracker", projects_tracker.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/projects_tracker_callbacks.py
    return None


