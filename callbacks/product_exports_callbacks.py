# Import the product_exports module to register its @callback decorated functions
from app.dashboards.analytics import product_exports


def register_callbacks(app, server):
    # Callbacks are already registered via @callback decorators in product_exports.py
    # when the module is imported above. This function exists for consistency.
    pass