import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import crude_profile


dash.register_page(
    __name__,
    path="/crude-profile",
    name="Crude Profile",
)


def layout():
    return wrap_layout("crude-profile", crude_profile.create_layout())


def init_callbacks(app, server):
    # Signature accepts only the Dash app
    crude_profile.register_callbacks(app)


