"""
Latest Updates View
Latest upstream project updates
"""
from dash import dcc, html, Input, Output, callback, dash_table
import pandas as pd
from core.data_helpers import execute_query
# from app.models import UpstreamProject, Country


def create_layout():
    """Create the Latest Updates layout"""
    return html.Div([
        html.H3("Latest Updates", style={'marginBottom': '20px'}),
        dash_table.DataTable(
            id='projects-latest-table',
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'}
        )
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Latest Updates"""
    
    @callback(
        [Output('projects-latest-table', 'data'),
         Output('projects-latest-table', 'columns')],
        Input('current-submenu', 'data')
    )
    def update_projects_latest(submenu):
        """Update projects latest updates table"""
        if submenu != 'projects-latest':
            return [], []
        
        # Use pre-loaded data or load new data
        df = load_projects_latest_data()
    
        if df.empty:
            return [], []
        
        # Ensure columns exist and are correctly named
        required_cols = ['name', 'country_name', 'status', 'start_date', 'update_date']
        for col in required_cols:
            if col not in df.columns:
                print(f"Error: Expected column '{col}' not found in DataFrame.")
                return [], []
        
        # Rename columns for display
        df = df.rename(columns={
            'name': 'Project',
            'country_name': 'Country',
            'status': 'Status',
            'start_date': 'Start Date',
            'update_date': 'Last Update'
        })
        
        columns = [{'name': col, 'id': col} for col in df.columns]
        data = df.to_dict('records')
        return data, columns


def load_projects_latest_data():
    query = """
    SELECT
        fup.project_name AS name,
        dc.country_long_name AS country_name,
        fup.project_status AS status,
        fup.project_start_date AS start_date,
        fup.last_update_date AS update_date
    FROM dev.fact_upstream_project_tracker fup
    JOIN dev.dim_country dc ON fup.country_id = dc.dim_country_id
    ORDER BY fup.last_update_date DESC
    LIMIT 50;
    """
    results = execute_query(query)
    df = pd.DataFrame(results)
    
    if not df.empty:
        df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce').dt.isoformat().fillna('N/A')
        df['update_date'] = pd.to_datetime(df['update_date'], errors='coerce').dt.isoformat().fillna('N/A')
        df['status'] = df['status'].fillna('N/A')
    
    return df

