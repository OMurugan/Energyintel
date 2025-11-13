"""
Global Crude Prices View
Global crude oil pricing data
"""
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
from app import db
from app.models import CrudePrice


def create_layout():
    """Create the Global Crude Prices layout"""
    return html.Div([
        html.H3("Global Crude Prices", style={'marginBottom': '20px'}),
        dcc.Graph(id='global-prices-chart')
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Global Crude Prices"""
    
    @callback(
        Output('global-prices-chart', 'figure'),
        Input('current-submenu', 'data')
    )
    def update_global_prices(submenu):
        """Update global prices chart"""
        if submenu != 'global-prices':
            return go.Figure()
        
        # Placeholder - will need CrudePrice data
        fig = go.Figure()
        fig.add_annotation(
            text="Price data will be displayed here once CrudePrice data is available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
        return fig

