"""
Projects by Company View
Upstream projects grouped by company
"""
from dash import dcc, html, Input, Output, callback, dash_table
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from app import db
from app.models import Company, UpstreamProject
from sqlalchemy import func


def create_layout():
    """Create the Projects by Company layout"""
    return html.Div([
        html.H3("Projects by Company", style={'marginBottom': '20px'}),
        html.Div([
            dcc.Graph(id='projects-company-chart')
        ]),
        html.Div([
            dash_table.DataTable(
                id='projects-company-table',
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'}
            )
        ], style={'marginTop': '20px'})
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Projects by Company"""
    
    @callback(
        [Output('projects-company-chart', 'figure'),
         Output('projects-company-table', 'data'),
         Output('projects-company-table', 'columns')],
        Input('current-submenu', 'data')
    )
    def update_projects_by_company(submenu):
        """Update projects by company chart and table"""
        if submenu != 'projects-company':
            return go.Figure(), [], []
        
        with server.app_context():
            results = db.session.query(
                Company.name,
                func.count(UpstreamProject.id).label('project_count')
            ).join(UpstreamProject).group_by(
                Company.id, Company.name
            ).order_by(func.count(UpstreamProject.id).desc()).limit(20).all()
            
            df = pd.DataFrame([
                {'Company': r.name, 'Projects': r.project_count}
                for r in results
            ])
        
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No project data available. Please seed UpstreamProject and Company data.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(height=400, plot_bgcolor='white', paper_bgcolor='white')
            return fig, [], []
        
        fig = px.bar(df, x='Company', y='Projects', title='Projects by Company')
        fig.update_layout(height=400, plot_bgcolor='white', paper_bgcolor='white', xaxis_tickangle=-45)
        
        columns = [{'name': col, 'id': col} for col in df.columns]
        data = df.to_dict('records')
        
        return fig, data, columns

