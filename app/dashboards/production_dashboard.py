"""
Production Dashboard
Focused view on production metrics
"""
import dash
from dash import dcc, html, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from core.data_helpers import execute_query
from datetime import datetime, timedelta


def create_production_dashboard(server, url_base_pathname):
    """Create production-focused dashboard"""
    dash_app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname=url_base_pathname,
        external_stylesheets=[
            'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
            'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
        ],
        suppress_callback_exceptions=True
    )

    dash_app.layout = html.Div([
        html.Div([
            html.H1("Production Dashboard", className="mb-4"),
        ], className="container-fluid", style={'padding': '30px', 'background': 'white', 'marginBottom': '20px'}),
        
        html.Div([
            html.Div([
                dcc.Graph(id='production-heatmap'),
                dcc.Graph(id='production-regional-breakdown'),
            ], className='container-fluid', style={'padding': '30px'})
        ])
    ], style={'background': '#f5f5f5', 'minHeight': '100vh'})
    
    @callback(
        Output('production-heatmap', 'figure'),
        Input('production-heatmap', 'id')
    )
    def update_heatmap(_):
        """Update production heatmap"""
        df = load_production_heatmap_data()
        
        if df.empty:
            return go.Figure()
        
        # Ensure 'Country', 'Region', 'Production' columns exist
        required_cols = ['name', 'region', 'production']
        for col in required_cols:
            if col not in df.columns:
                print(f"Error: Expected column '{col}' not found in DataFrame.")
                return go.Figure()
        df = df.rename(columns={'name': 'Country', 'region': 'Region', 'production': 'Production'})
        
        fig = px.treemap(
            df,
            path=['Region', 'Country'],
            values='Production',
            title='Production by Region and Country',
            color='Production',
            color_continuous_scale='Blues'
        )
        
        fig.update_layout(height=600)
        return fig
    
    @callback(
        Output('production-regional-breakdown', 'figure'),
        Input('production-regional-breakdown', 'id')
    )
    def update_regional_breakdown(_):
        """Update regional breakdown"""
        df = load_production_regional_breakdown_data()
        
        if df.empty:
            return go.Figure()
        
        # Ensure 'Region' and 'Production' columns exist
        required_cols = ['region', 'production']
        for col in required_cols:
            if col not in df.columns:
                print(f"Error: Expected column '{col}' not found in DataFrame.")
                return go.Figure()
        df = df.rename(columns={'region': 'Region', 'production': 'Production'})
        
        fig = px.pie(
            df,
            values='Production',
            names='Region',
            title='Production by Region'
        )
        
        fig.update_layout(height=500)
        return fig
    
    return dash_app

