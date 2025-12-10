"""Callback registrar for the Crude Quality Comparison dashboard."""

from app.dashboards.wcod import crude_quality


def register_callbacks(app, server):
    """Register all callbacks defined in the crude_quality module."""
    crude_quality.register_callbacks(app, server)

