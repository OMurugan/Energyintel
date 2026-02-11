import dash
from pages._utils import wrap_layout
from app.dashboards.world_gas_analytics import gas_europe_lng_imports


dash.register_page(
    __name__,
    path="/gas/europe-lng-imports",
    name="European Gas Trade - LNG Imports by Terminal",
)


def layout():
    return wrap_layout("gas-europe-lng-imports", gas_europe_lng_imports.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/gas_europe_lng_imports_callbacks.py
    return None