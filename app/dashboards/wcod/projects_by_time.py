"""
Projects by Time View
Upstream projects over time
"""
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from app import db
from app.models import UpstreamProject
from sqlalchemy import func, extract


def create_layout():
    """Create the Projects by Time layout"""
    return html.Div([
        html.H3("Projects by Time", style={'marginBottom': '20px'}),
        html.Div([
            html.Label("Time Range:", style={'fontWeight': '500', 'marginBottom': '8px'}),
            dcc.Dropdown(
                id='projects-time-range',
                options=[
                    {'label': 'All Time', 'value': 'all'},
                    {'label': 'Last 5 Years', 'value': '5y'},
                    {'label': 'Last 10 Years', 'value': '10y'},
                ],
                value='all',
                clearable=False,
                style={'marginBottom': '20px', 'width': '300px'}
            )
        ]),
        html.Div([
            dcc.Graph(id='projects-time-chart')
        ])
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Projects by Time"""
    
    @callback(
        Output('projects-time-chart', 'figure'),
        [Input('current-submenu', 'data'),
         Input('projects-time-range', 'value')]
    )
    def update_projects_by_time(submenu, time_range):
        """Update projects by time chart"""
        if submenu != 'projects-time':
            return go.Figure()
        
        with server.app_context():
            query = db.session.query(
                extract('year', UpstreamProject.start_date).label('year'),
                func.count(UpstreamProject.id).label('project_count')
            ).filter(UpstreamProject.start_date.isnot(None))
            
            if time_range == '5y':
                cutoff_date = datetime.now().date() - timedelta(days=365*5)
                query = query.filter(UpstreamProject.start_date >= cutoff_date)
            elif time_range == '10y':
                cutoff_date = datetime.now().date() - timedelta(days=365*10)
                query = query.filter(UpstreamProject.start_date >= cutoff_date)
            
            results = query.group_by(
                extract('year', UpstreamProject.start_date)
            ).order_by(extract('year', UpstreamProject.start_date)).all()
            
            df = pd.DataFrame([
                {'Year': int(r.year), 'Projects': r.project_count}
                for r in results if r.year
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
        
        fig = px.line(df, x='Year', y='Projects', markers=True, title='Projects by Time')
        fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
        return fig

