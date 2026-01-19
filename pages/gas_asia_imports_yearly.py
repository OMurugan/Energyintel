import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import gas_asia_imports_yearly


dash.register_page(
    __name__,
    path="/gas/asia-imports-yearly",
    name="Asian Gas Trade - Yearly Imports by Origin",
)


def layout():
    return wrap_layout("gas-asia-imports-yearly", gas_asia_imports_yearly.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/gas_asia_imports_yearly_callbacks.py
    return None