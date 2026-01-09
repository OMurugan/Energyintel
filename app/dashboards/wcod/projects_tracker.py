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
        # Coming Soon Content
        html.Div([
            html.Div([
                # Icon
                html.Div([
                    html.I(className="fas fa-tools", style={
                        'fontSize': '80px',
                        'color': '#fe5000',
                        'marginBottom': '30px'
                    })
                ], style={'textAlign': 'center'}),
                
                # Title
                html.H2("Upstream Oil Projects Tracker", style={
                    'color': '#fe5000',
                    'textAlign': 'center',
                    'marginBottom': '20px',
                    'fontSize': '28px',
                    'fontWeight': 'bold',
                    'fontFamily': 'Lato, sans-serif'
                }),
                
                # Coming Soon Message
                html.H3("Coming Soon", style={
                    'color': '#1b365d',
                    'textAlign': 'center',
                    'marginBottom': '30px',
                    'fontSize': '24px',
                    'fontWeight': '600',
                    'fontFamily': 'Lato, sans-serif'
                }),
                
                # Description
                html.P([
                    "We're working hard to bring you a comprehensive upstream oil projects tracking dashboard. ",
                    "This feature will include:"
                ], style={
                    'textAlign': 'center',
                    'fontSize': '16px',
                    'color': '#2c3e50',
                    'marginBottom': '30px',
                    'fontFamily': 'Lato, sans-serif',
                    'lineHeight': '1.6'
                }),
                
                # Feature List
                html.Div([
                    html.Ul([
                        html.Li("Interactive project tracking and monitoring", style={'marginBottom': '10px'}),
                        html.Li("Real-time project status updates", style={'marginBottom': '10px'}),
                        html.Li("Comprehensive project details and analytics", style={'marginBottom': '10px'}),
                        html.Li("Advanced filtering and search capabilities", style={'marginBottom': '10px'}),
                        html.Li("Export functionality for project data", style={'marginBottom': '10px'})
                    ], style={
                        'listStyleType': 'none',
                        'padding': '0',
                        'fontSize': '14px',
                        'color': '#2c3e50',
                        'fontFamily': 'Lato, sans-serif'
                    })
                ], style={
                    'backgroundColor': '#f8f9fa',
                    'padding': '30px',
                    'borderRadius': '8px',
                    'border': '1px solid #dee2e6',
                    'marginBottom': '30px'
                }),
                
                # Contact Info
                html.P([
                    "Stay tuned for updates! This feature will be available soon."
                ], style={
                    'textAlign': 'center',
                    'fontSize': '14px',
                    'color': '#6c757d',
                    'fontFamily': 'Lato, sans-serif',
                    'fontStyle': 'italic'
                })
                
            ], style={
                'maxWidth': '600px',
                'margin': '0 auto',
                'padding': '60px 20px'
            })
        ], style={
            'minHeight': '70vh',
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'center',
            'backgroundColor': '#ffffff'
        })
    ], className='tab-content', style={'backgroundColor': '#ffffff', 'minHeight': '100vh'})


def register_callbacks(dash_app, server):
    """Register all callbacks for Projects Tracker"""
    # No callbacks needed for coming soon page
    pass


def load_projects_tracker_chart_data():
    query = """
    SELECT
        dc.country_long_name AS name,
        COUNT(fup.project_id) AS project_count
    FROM dim_country dc
    JOIN fact_upstream_project_tracker fup ON dc.dim_country_id = fup.country_id
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
    FROM fact_upstream_project_tracker fup
    JOIN dim_country dc ON fup.country_id = dc.dim_country_id
    LIMIT 100;
    """
    results = execute_query(query)
    df = pd.DataFrame(results)
    
    if not df.empty:
        df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce').dt.isoformat().fillna('N/A')
        df['status'] = df['status'].fillna('N/A')
        df['capacity_bbl_per_day'] = df['capacity_bbl_per_day'].fillna(0)
    
    return df

