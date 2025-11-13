"""
Latest Updates View
Latest upstream project updates
"""
from dash import dcc, html, Input, Output, callback, dash_table
import pandas as pd
from app import db
from app.models import UpstreamProject, Country


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
        
        with server.app_context():
            results = db.session.query(
                UpstreamProject.name,
                Country.name.label('country_name'),
                UpstreamProject.status,
                UpstreamProject.start_date,
                UpstreamProject.update_date
            ).join(Country).order_by(
                UpstreamProject.update_date.desc()
            ).limit(50).all()
            
            df = pd.DataFrame([
                {
                    'Project': r.name,
                    'Country': r.country_name,
                    'Status': r.status or 'N/A',
                    'Start Date': r.start_date.isoformat() if r.start_date else 'N/A',
                    'Last Update': r.update_date.isoformat() if r.update_date else 'N/A'
                }
                for r in results
            ])
        
        if df.empty:
            return [], []
        
        columns = [{'name': col, 'id': col} for col in df.columns]
        data = df.to_dict('records')
        return data, columns

