"""
Projects by Country View
Upstream projects grouped by country
"""
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from core.data_helpers import execute_query
# from app.models import Country, UpstreamProject
# from sqlalchemy import func


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
        
        # Use pre-loaded data or load new data
        df = load_projects_by_country_data()
        
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No project data available.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return fig
        
        # Ensure 'name' and 'project_count' columns exist and are correctly named
        if 'name' not in df.columns or 'project_count' not in df.columns:
            print("Error: Expected columns 'name' and 'project_count' not found in DataFrame.")
            return go.Figure()
        
        # Rename columns for display
        df = df.rename(columns={'name': 'Country', 'project_count': 'Projects'})
        
        fig = px.bar(df, x='Country', y='Projects', title='Projects by Country')
        fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white', xaxis_tickangle=-45)
        return fig


def load_projects_by_country_data():
    query = """
    SELECT
        dc.country_long_name AS name,
        COUNT(fup.project_id) AS project_count
    FROM dev.dim_country dc
    JOIN dev.fact_upstream_project_tracker fup ON dc.dim_country_id = fup.country_id
    GROUP BY dc.dim_country_id, dc.country_long_name
    ORDER BY COUNT(fup.project_id) DESC
    LIMIT 20;
    """
    results = execute_query(query)
    return pd.DataFrame(results)

