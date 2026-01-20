from app.dashboards.analytics import gas_europe_pipeline_flows_country


def register_callbacks(app, server):
    gas_europe_pipeline_flows_country.register_callbacks(app, server)