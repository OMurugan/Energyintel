import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import low_carbon_investments_list


dash.register_page(
    __name__,
    path="/low-carbon/investments-list",
    name="List of Tracked Investments",
)


def layout():
    return wrap_layout("low-carbon-investments-list", low_carbon_investments_list.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/low_carbon_investments_list_callbacks.py
    return None