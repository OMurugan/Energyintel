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
        # Coming Soon Content
        html.Div([
            html.Div([
                # Icon
                html.Div([
                    html.I(className="fas fa-leaf", style={
                        'fontSize': '80px',
                        'color': '#28a745',
                        'marginBottom': '30px'
                    })
                ], style={'textAlign': 'center'}),
                
                # Title
                html.H2("Carbon Intensity Analytics", style={
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
                    "We're developing advanced carbon intensity analytics to help you track and analyze ",
                    "environmental impact metrics across upstream oil projects. This feature will include:"
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
                        html.Li("Carbon intensity metrics by project and region", style={'marginBottom': '10px'}),
                        html.Li("Environmental impact trend analysis", style={'marginBottom': '10px'}),
                        html.Li("Comparative carbon footprint assessments", style={'marginBottom': '10px'}),
                        html.Li("Sustainability benchmarking tools", style={'marginBottom': '10px'}),
                        html.Li("ESG reporting and compliance tracking", style={'marginBottom': '10px'})
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
                
                # Environmental Focus Note
                html.Div([
                    html.P([
                        html.I(className="fas fa-globe-americas", style={
                            'color': '#28a745',
                            'marginRight': '10px'
                        }),
                        "Supporting sustainable energy practices through data-driven insights"
                    ], style={
                        'textAlign': 'center',
                        'fontSize': '14px',
                        'color': '#28a745',
                        'fontFamily': 'Lato, sans-serif',
                        'fontWeight': '600',
                        'margin': '0'
                    })
                ], style={
                    'backgroundColor': '#d4edda',
                    'padding': '15px',
                    'borderRadius': '6px',
                    'border': '1px solid #c3e6cb',
                    'marginBottom': '30px'
                }),
                
                # Contact Info
                html.P([
                    "This environmental analytics dashboard will be available soon."
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
    """Register all callbacks for Carbon Intensity"""
    # No callbacks needed for coming soon page
    pass


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

