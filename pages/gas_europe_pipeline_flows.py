import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import gas_europe_pipeline_flows


dash.register_page(
    __name__,
    path="/gas/europe-pipeline-flows",
    name="European Gas Trade - Pipeline Flows to Europe",
)


def layout():
    return wrap_layout("gas-europe-pipeline-flows", gas_europe_pipeline_flows.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/gas_europe_pipeline_flows_callbacks.py
    return None