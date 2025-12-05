import dash
from pages._utils import wrap_layout
from app.dashboards.wcod import country_profile


dash.register_page(
    __name__,
    path="/country-profile",
    name="Country Profile",
)


def layout():
    return wrap_layout("country-profile", country_profile.create_layout())


def init_callbacks(app, server):
    # Callbacks are registered via callbacks/country_profile_callbacks.py
    return None


