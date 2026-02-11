"""
Europe World Gas Data Dashboard
Comprehensive European gas analytics dashboard
"""
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


def create_layout():
    """Create the Europe Gas Dashboard layout"""
    return html.Div([
        # Coming Soon Content
        html.Div([
            html.Div([
                # Icon
                html.Div([
                    html.I(className="fas fa-fire", style={
                        'fontSize': '80px',
                        'color': '#fe5000',
                        'marginBottom': '30px'
                    })
                ], style={'textAlign': 'center'}),
                
                # Title
                html.H2("Europe World Gas Data Dashboard", style={
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
                    "We're developing a comprehensive European gas analytics dashboard. ",
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
                        html.Li("Real-time European gas market data", style={'marginBottom': '10px'}),
                        html.Li("Interactive pipeline flow visualizations", style={'marginBottom': '10px'}),
                        html.Li("Gas demand and supply analytics", style={'marginBottom': '10px'}),
                        html.Li("LNG terminal tracking and analysis", style={'marginBottom': '10px'}),
                        html.Li("Country-specific gas trade insights", style={'marginBottom': '10px'})
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
    """Register all callbacks for Europe Gas Dashboard"""
    # No callbacks needed for coming soon page
    pass