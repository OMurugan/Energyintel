"""
Crude Carbon Intensity View
Carbon intensity metrics for different crude types
"""
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from app import db
from app.models import Crude, Country


def create_layout():
    """Create the Crude Carbon Intensity layout"""
    return html.Div([
        html.H3("Crude Carbon Intensity", style={'marginBottom': '20px'}),
        dcc.Graph(id='crude-carbon-chart')
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Crude Carbon Intensity"""
    
    @callback(
        Output('crude-carbon-chart', 'figure'),
        Input('current-submenu', 'data')
    )
    def update_crude_carbon(submenu):
        """Update crude carbon intensity chart"""
        if submenu != 'crude-carbon':
            return go.Figure()
        
        with server.app_context():
            results = db.session.query(
                Crude.name,
                Country.name.label('country_name'),
                Crude.carbon_intensity
            ).join(Country).filter(Crude.carbon_intensity.isnot(None)).all()
            
            df = pd.DataFrame([
                {
                    'Crude': r.name,
                    'Country': r.country_name,
                    'Carbon Intensity': r.carbon_intensity
                }
                for r in results
            ])
        
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No carbon intensity data available. Please seed Crude data with carbon intensity.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return fig
        
        fig = px.bar(df, x='Crude', y='Carbon Intensity', color='Country', 
                    title='Crude Carbon Intensity by Type')
        fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white', xaxis_tickangle=-45)
        return fig

