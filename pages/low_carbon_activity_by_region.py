import dash
from pages._utils import wrap_layout
from app.dashboards.analytics import low_carbon_activity_by_region


dash.register_page(
    __name__,
    path="/low-carbon/activity-by-region",
    name="Activity by Region",
)


def layout():
    return wrap_layout("low-carbon-activity-by-region", low_carbon_activity_by_region.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/low_carbon_activity_by_region_callbacks.py
    return None