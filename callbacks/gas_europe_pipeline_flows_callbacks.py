from app.dashboards.wcod import gas_europe_pipeline_flows


def register_callbacks(app, server):
    gas_europe_pipeline_flows.register_callbacks(app, server)