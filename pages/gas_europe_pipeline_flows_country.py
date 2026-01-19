import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import gas_europe_pipeline_flows_country


dash.register_page(
    __name__,
    path="/gas/europe-pipeline-flows-country",
    name="European Gas Trade - Pipeline Flows by Country",
)


def layout():
    return wrap_layout("gas-europe-pipeline-flows-country", gas_europe_pipeline_flows_country.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/gas_europe_pipeline_flows_country_callbacks.py
    return None