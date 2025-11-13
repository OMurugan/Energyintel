"""
Carbon Intensity View
Carbon intensity metrics for upstream projects
"""
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from app import db
from app.models import UpstreamProject, Country
from sqlalchemy import func


def create_layout():
    """Create the Carbon Intensity layout"""
    return html.Div([
        html.H3("Carbon Intensity", style={'marginBottom': '20px'}),
        dcc.Graph(id='projects-carbon-chart')
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Carbon Intensity"""
    
    @callback(
        Output('projects-carbon-chart', 'figure'),
        Input('current-submenu', 'data')
    )
    def update_projects_carbon(submenu):
        """Update projects carbon intensity chart"""
        if submenu != 'projects-carbon':
            return go.Figure()
        
        with server.app_context():
            results = db.session.query(
                Country.name,
                func.avg(UpstreamProject.carbon_intensity).label('avg_carbon')
            ).join(UpstreamProject).filter(
                UpstreamProject.carbon_intensity.isnot(None)
            ).group_by(Country.id, Country.name).all()
            
            df = pd.DataFrame([
                {'Country': r.name, 'Avg Carbon Intensity': r.avg_carbon or 0}
                for r in results
            ])
        
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No carbon intensity data available. Please seed UpstreamProject data with carbon intensity.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return fig
        
        fig = px.bar(df, x='Country', y='Avg Carbon Intensity', 
                    title='Average Carbon Intensity by Country')
        fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white', xaxis_tickangle=-45)
        return fig

