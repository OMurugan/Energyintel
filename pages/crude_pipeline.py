import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import crude_pipeline


dash.register_page(
    __name__,
    path="/crude-pipeline",
    name="Crude Pipeline",
)


def layout():
    return wrap_layout("crude-pipeline", crude_pipeline.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/crude_pipeline_callbacks.py
    return None
