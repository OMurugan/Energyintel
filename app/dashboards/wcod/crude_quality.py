"""
Crude Quality Comparison View
Compare crude quality metrics across different types
"""
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from app import db
from app.models import Crude


def create_layout():
    """Create the Crude Quality Comparison layout"""
    return html.Div([
        html.H3("Crude Quality Comparison", style={'marginBottom': '20px'}),
        dcc.Graph(id='crude-quality-chart')
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Crude Quality Comparison"""
    
    @callback(
        Output('crude-quality-chart', 'figure'),
        Input('current-submenu', 'data')
    )
    def update_crude_quality(submenu):
        """Update crude quality comparison chart"""
        if submenu != 'crude-quality':
            return go.Figure()
        
        with server.app_context():
            results = db.session.query(
                Crude.name,
                Crude.api_gravity,
                Crude.sulfur_content
            ).all()
            
            df = pd.DataFrame([
                {
                    'Crude': r.name,
                    'API Gravity': r.api_gravity or 0,
                    'Sulfur Content (%)': r.sulfur_content or 0
                }
                for r in results
            ])
        
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No crude data available. Please seed Crude data.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return fig
        
        fig = px.scatter(df, x='API Gravity', y='Sulfur Content (%)', text='Crude', 
                        title='Crude Quality Comparison (API Gravity vs Sulfur Content)')
        fig.update_traces(textposition="top center")
        fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
        return fig

