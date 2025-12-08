"""
Carbon Intensity View
Carbon intensity metrics for upstream projects
"""
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from core.data_helpers import execute_query
# from app.models import UpstreamProject, Country
# from sqlalchemy import func


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
        
        # Use pre-loaded data or load new data
        df = load_projects_carbon_data()
        
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No carbon intensity data available.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return fig
        
        # Ensure 'name' and 'avg_carbon' columns exist and are correctly named
        if 'name' not in df.columns or 'avg_carbon' not in df.columns:
            print("Error: Expected columns 'name' and 'avg_carbon' not found in DataFrame.")
            return go.Figure()
        
        # Rename columns for display
        df = df.rename(columns={'name': 'Country', 'avg_carbon': 'Avg Carbon Intensity'})
        
        fig = px.bar(df, x='Country', y='Avg Carbon Intensity', 
                    title='Average Carbon Intensity by Country')
        fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white', xaxis_tickangle=-45)
        return fig


def load_projects_carbon_data():
    query = """
    SELECT
        dc.country_long_name AS name,
        AVG(CAST(fup.carbon_intensity AS NUMERIC)) AS avg_carbon
    FROM dim_country dc
    JOIN fact_upstream_project_tracker fup ON dc.dim_country_id = fup.country_id
    WHERE fup.carbon_intensity IS NOT NULL AND fup.carbon_intensity != ''
    GROUP BY dc.dim_country_id, dc.country_long_name;
    """
    results = execute_query(query)
    # Ensure 'avg_carbon' is numeric and handle potential None values
    df = pd.DataFrame(results)
    if not df.empty and 'avg_carbon' in df.columns:
        df['avg_carbon'] = pd.to_numeric(df['avg_carbon'], errors='coerce').fillna(0)
    return df

