"""Shared helpers for Dash page definitions."""

from dash import dcc, html


def wrap_layout(submenu_slug: str, inner_layout) -> html.Div:
    """
    Wrap a page layout with a consistent current-submenu store.

    Args:
        submenu_slug: Identifier expected by callbacks that check current-submenu.
        inner_layout: The Dash layout returned by the view module.

    Returns:
        html.Div containing the store and provided layout.
    """
    return html.Div(
        [
            dcc.Store(id="current-submenu", data=submenu_slug),
            inner_layout,
        ]
    )


