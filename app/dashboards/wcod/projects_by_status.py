"""
Projects by Status View
Upstream projects grouped by status
"""
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from app import db
from app.models import UpstreamProject
from sqlalchemy import func


def create_layout():
    """Create the Projects by Status layout"""
    return html.Div([
        html.H3("Projects by Status", style={'marginBottom': '20px'}),
        dcc.Graph(id='projects-status-chart')
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Projects by Status"""
    
    @callback(
        Output('projects-status-chart', 'figure'),
        Input('current-submenu', 'data')
    )
    def update_projects_by_status(submenu):
        """Update projects by status chart"""
        if submenu != 'projects-status':
            return go.Figure()
        
        with server.app_context():
            results = db.session.query(
                UpstreamProject.status,
                func.count(UpstreamProject.id).label('project_count')
            ).group_by(UpstreamProject.status).all()
            
            df = pd.DataFrame([
                {'Status': r.status, 'Projects': r.project_count}
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
        
        fig = px.pie(df, values='Projects', names='Status', title='Projects by Status')
        fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
        return fig

