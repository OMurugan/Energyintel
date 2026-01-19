"""
European Gas Demand - Yearly Demand
Yearly gas demand analytics for Europe
"""
from dash import dcc, html


def create_layout():
    """Create the European Yearly Demand layout"""
    return html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.I(className="fas fa-chart-line", style={
                        'fontSize': '80px', 'color': '#fe5000', 'marginBottom': '30px'
                    })
                ], style={'textAlign': 'center'}),
                html.H2("European Gas Demand - Yearly Demand", style={
                    'color': '#fe5000', 'textAlign': 'center', 'marginBottom': '20px',
                    'fontSize': '28px', 'fontWeight': 'bold', 'fontFamily': 'Lato, sans-serif'
                }),
                html.H3("Coming Soon", style={
                    'color': '#1b365d', 'textAlign': 'center', 'marginBottom': '30px',
                    'fontSize': '24px', 'fontWeight': '600', 'fontFamily': 'Lato, sans-serif'
                }),
                html.P("Yearly gas demand trends and analytics coming soon.", style={
                    'textAlign': 'center', 'fontSize': '16px', 'color': '#2c3e50',
                    'marginBottom': '30px', 'fontFamily': 'Lato, sans-serif', 'lineHeight': '1.6'
                })
            ], style={'maxWidth': '600px', 'margin': '0 auto', 'padding': '60px 20px'})
        ], style={'minHeight': '70vh', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'})
    ], className='tab-content', style={'backgroundColor': '#ffffff', 'minHeight': '100vh'})


def register_callbacks(dash_app, server):
    pass