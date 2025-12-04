"""
Country Profile Dashboard
Detailed view for individual country analysis
"""
import dash
from dash import dcc, html, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from core.data_helpers import execute_query
from datetime import datetime, timedelta


def create_country_profile_dashboard(server, url_base_pathname):
    """Create country profile dashboard"""
    dash_app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname=url_base_pathname,
        external_stylesheets=[
            'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
            'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
        ],
        suppress_callback_exceptions=True
    )
    
    # Get list of countries for dropdown
    country_df = load_country_options()
    country_options = [{'label': row['name'], 'value': row['id']} for _, row in country_df.iterrows()] if not country_df.empty else []
    default_country = country_options[0]['value'] if country_options else None
    
    dash_app.layout = html.Div([
        html.Div([
            html.H1(
                "Country Profile Dashboard",
                className="mb-4",
                style={'color': '#2c3e50', 'fontWeight': '600'}
            ),
            html.P(
                "Detailed analysis of crude oil data by country",
                style={'color': '#7f8c8d', 'marginBottom': '30px'}
            )
        ], className="container-fluid", style={'padding': '30px', 'background': 'white', 'marginBottom': '20px'}),
        
        html.Div([
            html.Div([
                html.Label("Select Country:", style={'fontWeight': '500', 'marginBottom': '8px'}),
                dcc.Dropdown(
                    id='country-select',
                    options=country_options,
                    value=default_country,
                    clearable=False,
                    style={'marginBottom': '30px'}
                )
            ], className='col-md-6'),
        ], className='row', style={'marginBottom': '30px'}),
        
        html.Div([
            # KPI Cards
            html.Div([
                html.Div(id='country-kpi-production', className='kpi-card'),
                html.Div(id='country-kpi-exports', className='kpi-card'),
                html.Div(id='country-kpi-imports', className='kpi-card'),
                html.Div(id='country-kpi-reserves', className='kpi-card'),
            ], className='row', style={'marginBottom': '30px'}),
            
            # Charts
            html.Div([
                html.Div([
                    dcc.Graph(id='country-production-trend')
                ], className='col-md-6', style={'marginBottom': '20px'}),
                
                html.Div([
                    dcc.Graph(id='country-exports-trend')
                ], className='col-md-6', style={'marginBottom': '20px'}),
            ], className='row'),
            
            html.Div([
                html.Div([
                    dcc.Graph(id='country-trade-balance')
                ], className='col-md-12', style={'marginBottom': '20px'}),
            ], className='row'),
        ], className='container-fluid', style={'padding': '30px'})
    ], style={'background': '#f5f5f5', 'minHeight': '100vh'})
    
    @callback(
        [Output('country-kpi-production', 'children'),
         Output('country-kpi-exports', 'children'),
         Output('country-kpi-imports', 'children'),
         Output('country-kpi-reserves', 'children')],
        [Input('country-select', 'value')]
    )
    def update_country_kpis(country_id):
        """Update country-specific KPIs"""
        if not country_id:
            return [html.Div()] * 4
        
        latest_prod, latest_exports, latest_imports, latest_reserves = load_country_kpis_data(country_id)
        
        kpi_prod = html.Div([
            html.Div(f"{latest_prod:,.0f}", className='kpi-value'),
            html.Div("Latest Production (bbl)", className='kpi-label'),
        ])
        
        kpi_exports = html.Div([
            html.Div(f"{latest_exports:,.0f}", className='kpi-value'),
            html.Div("Latest Exports (bbl)", className='kpi-label'),
        ])
        
        kpi_imports = html.Div([
            html.Div(f"{latest_imports:,.0f}", className='kpi-value'),
            html.Div("Latest Imports (bbl)", className='kpi-label'),
        ])
        
        kpi_reserves = html.Div([
            html.Div(f"{latest_reserves:,.0f}", className='kpi-value'),
            html.Div("Latest Reserves (bbl)", className='kpi-label'),
        ])
        
        return kpi_prod, kpi_exports, kpi_imports, kpi_reserves
    
    @callback(
        Output('country-production-trend', 'figure'),
        [Input('country-select', 'value')]
    )
    def update_country_production_trend(country_id):
        """Update country production trend"""
        if not country_id:
            return go.Figure()
        
        df = load_country_production_trend_data(country_id)
        
        if df.empty:
            return go.Figure()
        
        country_name = get_country_name_from_id(country_id)
        fig = px.line(
            df,
            x='date',
            y='production',
            title=f'{country_name} - Production Trend',
            markers=True
        )
        
        fig.update_traces(line_color='#3498db', line_width=2)
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=400
        )
        
        return fig
    
    @callback(
        Output('country-exports-trend', 'figure'),
        [Input('country-select', 'value')]
    )
    def update_country_exports_trend(country_id):
        """Update country exports trend"""
        if not country_id:
            return go.Figure()
        
        df = load_country_exports_trend_data(country_id)
        
        if df.empty:
            return go.Figure()
        
        country_name = get_country_name_from_id(country_id)
        fig = px.line(
            df,
            x='date',
            y='exports',
            title=f'{country_name} - Exports Trend',
            markers=True
        )
        
        fig.update_traces(line_color='#27ae60', line_width=2)
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=400
        )
        
        return fig
    
    @callback(
        Output('country-trade-balance', 'figure'),
        [Input('country-select', 'value')]
    )
    def update_trade_balance(country_id):
        """Update trade balance chart"""
        if not country_id:
            return go.Figure()
        
        exports_df, imports_df = load_country_trade_balance_data(country_id)
        country_name = get_country_name_from_id(country_id)
        
        fig = go.Figure()
        
        if not exports_df.empty:
            fig.add_trace(go.Scatter(
                x=exports_df['date'],
                y=exports_df['exports'],
                name='Exports',
                line=dict(color='#27ae60', width=2)
            ))
        
        if not imports_df.empty:
            fig.add_trace(go.Scatter(
                x=imports_df['date'],
                y=imports_df['imports'],
                name='Imports',
                line=dict(color='#e74c3c', width=2)
            ))
        
        fig.update_layout(
            title=f'{country_name} - Trade Balance (Exports vs Imports)',
            xaxis_title='Date',
            yaxis_title='Volume (bbl)',
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=400
        )
        
        return fig
    
    return dash_app

