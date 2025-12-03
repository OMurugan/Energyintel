"""
Upstream Oil Projects Tracker View
Comprehensive project tracking dashboard
"""
from dash import dcc, html, Input, Output, callback, dash_table
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from core.data_helpers import execute_query
# from app.models import UpstreamProject, Country
# from sqlalchemy import func


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
        
        # Chart data - projects by country
        chart_df = load_projects_tracker_chart_data()
        
        # Table data - all projects
        table_df = load_projects_tracker_table_data()
    
        if chart_df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No project data available.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(height=400, plot_bgcolor='white', paper_bgcolor='white')
            return fig, [], []
        
        # Ensure 'name' and 'project_count' columns exist for the chart
        if 'name' not in chart_df.columns or 'project_count' not in chart_df.columns:
            print("Error: Expected columns 'name' and 'project_count' not found in chart DataFrame.")
            return go.Figure(), [], []
        
        # Rename columns for chart display
        chart_df = chart_df.rename(columns={'name': 'Country', 'project_count': 'Projects'})
        
        fig = px.bar(chart_df, x='Country', y='Projects', title='Projects by Country')
        fig.update_layout(height=400, plot_bgcolor='white', paper_bgcolor='white', xaxis_tickangle=-45)
        
        # Ensure table columns exist and are correctly named
        if table_df.empty:
            table_data = []
            table_columns = []
        else:
            # Rename columns for table display
            table_df = table_df.rename(columns={
                'name': 'Project',
                'country_name': 'Country',
                'status': 'Status',
                'capacity_bbl_per_day': 'Capacity (bbl/d)',
                'start_date': 'Start Date'
            })
            table_columns = [{'name': col, 'id': col} for col in table_df.columns]
            table_data = table_df.to_dict('records')
        
        return fig, table_data, table_columns


def load_projects_tracker_chart_data():
    query = """
    SELECT
        dc.country_long_name AS name,
        COUNT(fup.project_id) AS project_count
    FROM dev.dim_country dc
    JOIN dev.fact_upstream_project_tracker fup ON dc.dim_country_id = fup.country_id
    GROUP BY dc.dim_country_id, dc.country_long_name
    ORDER BY COUNT(fup.project_id) DESC
    LIMIT 15;
    """
    results = execute_query(query)
    return pd.DataFrame(results)

def load_projects_tracker_table_data():
    query = """
    SELECT
        fup.project_name AS name,
        dc.country_long_name AS country_name,
        fup.project_status AS status,
        fup.capacity_bbl_per_day AS capacity_bbl_per_day,
        fup.project_start_date AS start_date
    FROM dev.fact_upstream_project_tracker fup
    JOIN dev.dim_country dc ON fup.country_id = dc.dim_country_id
    LIMIT 100;
    """
    results = execute_query(query)
    df = pd.DataFrame(results)
    
    if not df.empty:
        df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce').dt.isoformat().fillna('N/A')
        df['status'] = df['status'].fillna('N/A')
        df['capacity_bbl_per_day'] = df['capacity_bbl_per_day'].fillna(0)
    
    return df

