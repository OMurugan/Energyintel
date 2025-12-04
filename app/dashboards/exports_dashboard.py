"""
Exports Dashboard
Focused view on export metrics
"""
import dash
from dash import dcc, html, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from core.data_helpers import execute_query
from datetime import datetime, timedelta


def create_exports_dashboard(server, url_base_pathname):
    """Create exports-focused dashboard"""
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
            html.H1("Exports Dashboard", className="mb-4"),
        ], className="container-fluid", style={'padding': '30px', 'background': 'white', 'marginBottom': '20px'}),
        
        html.Div([
            html.Div([
                dcc.Graph(id='exports-by-country'),
                dcc.Graph(id='exports-trend-global'),
            ], className='container-fluid', style={'padding': '30px'})
        ])
    ], style={'background': '#f5f5f5', 'minHeight': '100vh'})
    
    @callback(
        Output('exports-by-country', 'figure'),
        Input('exports-by-country', 'id')
    )
    def update_exports_by_country(_):
        """Update exports by country chart"""
        df = load_exports_by_country_data()
        
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No data available. Please seed Exports and Country data.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return fig
        
        # Ensure 'Country', 'Region', 'Exports' columns exist
        required_cols = ['name', 'region', 'exports']
        for col in required_cols:
            if col not in df.columns:
                print(f"Error: Expected column '{col}' not found in DataFrame.")
                return go.Figure()
        df = df.rename(columns={'name': 'Country', 'region': 'Region', 'exports': 'Exports'})
        
        fig = px.bar(
            df,
            x='Country',
            y='Exports',
            color='Region',
            title='Top 20 Countries by Exports',
            labels={'Exports': 'Exports (bbl)', 'Country': 'Country'}
        )
        
        fig.update_layout(height=500, xaxis_tickangle=-45)
        return fig
    
    @callback(
        Output('exports-trend-global', 'figure'),
        Input('exports-trend-global', 'id')
    )
    def update_exports_trend(_):
        """
        Update global exports trend
        """
        df = load_exports_trend_data()
        
        if df.empty:
            return go.Figure()
        
        # Ensure 'date' and 'total_exports' columns exist
        if 'date' not in df.columns or 'total_exports' not in df.columns:
            print("Error: Expected columns 'date' and 'total_exports' not found in DataFrame.")
            return go.Figure()
        df = df.rename(columns={'date': 'Date', 'total_exports': 'Exports'})
        
        fig = px.line(
            df,
            x='Date',
            y='Exports',
            title='Global Exports Trend',
            markers=True
        )
        
        fig.update_traces(line_color='#27ae60', line_width=2)
        fig.update_layout(height=500)
        return fig
    
    return dash_app

