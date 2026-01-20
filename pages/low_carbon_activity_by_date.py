import dash
from pages._utils import wrap_layout
from app.dashboards.analytics import low_carbon_activity_by_date


dash.register_page(
    __name__,
    path="/low-carbon/activity-by-date",
    name="Activity by Date Announced",
)


def layout():
    return wrap_layout("low-carbon-activity-by-date", low_carbon_activity_by_date.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/low_carbon_activity_by_date_callbacks.py
    return None