import dash
from pages._utils import wrap_layout
from app.dashboards.analytics import gas_europe_imports_mix


dash.register_page(
    __name__,
    path="/gas/europe-imports-mix",
    name="European Gas Trade - Gas Imports Mix by Country",
)


def layout():
    return wrap_layout("gas-europe-imports-mix", gas_europe_imports_mix.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/gas_europe_imports_mix_callbacks.py
    return None