import dash
from pages._utils import wrap_layout
from app.dashboards.world_gas_analytics import gas_asia_imports_mix


dash.register_page(
    __name__,
    path="/gas/asia-imports-mix",
    name="Asian Gas Trade - Gas Import Mix by Country",
)


def layout():
    return wrap_layout("gas-asia-imports-mix", gas_asia_imports_mix.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/gas_asia_imports_mix_callbacks.py
    return None