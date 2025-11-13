"""
Projects by Country View
Upstream projects grouped by country
"""
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from app import db
from app.models import Country, UpstreamProject
from sqlalchemy import func


def create_layout():
    """Create the Projects by Country layout"""
    return html.Div([
        html.H3("Projects by Country", style={'marginBottom': '20px'}),
        dcc.Graph(id='projects-country-chart')
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Projects by Country"""
    
    @callback(
        Output('projects-country-chart', 'figure'),
        Input('current-submenu', 'data')
    )
    def update_projects_by_country(submenu):
        """Update projects by country chart"""
        if submenu != 'projects-country':
            return go.Figure()
        
        with server.app_context():
            results = db.session.query(
                Country.name,
                func.count(UpstreamProject.id).label('project_count')
            ).join(UpstreamProject).group_by(
                Country.id, Country.name
            ).order_by(func.count(UpstreamProject.id).desc()).limit(20).all()
            
            df = pd.DataFrame([
                {'Country': r.name, 'Projects': r.project_count}
                for r in results
            ])
        
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No project data available. Please seed UpstreamProject data.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return fig
        
        fig = px.bar(df, x='Country', y='Projects', title='Projects by Country')
        fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white', xaxis_tickangle=-45)
        return fig

