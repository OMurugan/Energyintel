"""
Upstream Oil Projects Tracker View
Comprehensive project tracking dashboard
"""
from dash import dcc, html, Input, Output, callback, dash_table
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from app import db
from app.models import UpstreamProject, Country
from sqlalchemy import func


def create_layout():
    """Create the Projects Tracker layout"""
    return html.Div([
        html.H3("Upstream Oil Projects Tracker", style={'marginBottom': '20px'}),
        html.Div([
            html.Div([
                dcc.Graph(id='projects-tracker-chart')
            ], className='col-md-12'),
        ], className='row'),
        html.Div([
            dash_table.DataTable(
                id='projects-tracker-table',
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
                page_size=20
            )
        ], style={'marginTop': '20px'})
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Projects Tracker"""
    
    @callback(
        [Output('projects-tracker-chart', 'figure'),
         Output('projects-tracker-table', 'data'),
         Output('projects-tracker-table', 'columns')],
        Input('current-submenu', 'data')
    )
    def update_projects_tracker(submenu):
        """Update projects tracker chart and table"""
        if submenu != 'projects-tracker':
            return go.Figure(), [], []
        
        with server.app_context():
            # Chart data - projects by country
            chart_results = db.session.query(
                Country.name,
                func.count(UpstreamProject.id).label('project_count')
            ).join(UpstreamProject).group_by(
                Country.id, Country.name
            ).order_by(func.count(UpstreamProject.id).desc()).limit(15).all()
            
            chart_df = pd.DataFrame([
                {'Country': r.name, 'Projects': r.project_count}
                for r in chart_results
            ])
            
            # Table data - all projects
            table_results = db.session.query(
                UpstreamProject.name,
                Country.name.label('country_name'),
                UpstreamProject.status,
                UpstreamProject.capacity_bbl_per_day,
                UpstreamProject.start_date
            ).join(Country).limit(100).all()
            
            table_df = pd.DataFrame([
                {
                    'Project': r.name,
                    'Country': r.country_name,
                    'Status': r.status or 'N/A',
                    'Capacity (bbl/d)': r.capacity_bbl_per_day or 0,
                    'Start Date': r.start_date.isoformat() if r.start_date else 'N/A'
                }
                for r in table_results
            ])
        
        if chart_df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No project data available. Please seed UpstreamProject data.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(height=400, plot_bgcolor='white', paper_bgcolor='white')
            return fig, [], []
        
        fig = px.bar(chart_df, x='Country', y='Projects', title='Projects by Country')
        fig.update_layout(height=400, plot_bgcolor='white', paper_bgcolor='white', xaxis_tickangle=-45)
        
        columns = [{'name': col, 'id': col} for col in table_df.columns] if not table_df.empty else []
        data = table_df.to_dict('records') if not table_df.empty else []
        
        return fig, data, columns

