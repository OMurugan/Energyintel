"""
Country Profile Dashboard
Detailed view for individual country analysis
"""
import dash
from dash import dcc, html, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from flask import current_app
from app import create_dash_app
from app.models import Country, Production, Exports, Reserves, Imports
from app import db
from sqlalchemy import func, extract
from datetime import datetime, timedelta


def create_country_profile_dashboard(server, url_base_pathname):
    """Create country profile dashboard"""
    dash_app = create_dash_app(server, url_base_pathname)
    
    # Get list of countries for dropdown (within app context)
    try:
        with server.app_context():
            countries = Country.query.order_by(Country.name).all()
            country_options = [{'label': c.name, 'value': c.id} for c in countries]
            default_country = country_options[0]['value'] if country_options else None
    except Exception:
        country_options = []
        default_country = None
    
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
        
        country = Country.query.get(country_id)
        if not country:
            return [html.Div()] * 4
        
        latest_date = db.session.query(func.max(Production.date)).scalar()
        
        # Production
        latest_prod = db.session.query(
            func.sum(Production.production_bbl)
        ).filter(
            Production.country_id == country_id,
            Production.date == latest_date
        ).scalar() or 0
        
        kpi_prod = html.Div([
            html.Div(f"{latest_prod:,.0f}", className='kpi-value'),
            html.Div("Latest Production (bbl)", className='kpi-label'),
        ])
        
        # Exports
        latest_exports = db.session.query(
            func.sum(Exports.exports_bbl)
        ).filter(
            Exports.country_id == country_id,
            Exports.date == latest_date
        ).scalar() or 0
        
        kpi_exports = html.Div([
            html.Div(f"{latest_exports:,.0f}", className='kpi-value'),
            html.Div("Latest Exports (bbl)", className='kpi-label'),
        ])
        
        # Imports
        latest_imports = db.session.query(
            func.sum(Imports.imports_bbl)
        ).filter(
            Imports.country_id == country_id,
            Imports.date == latest_date
        ).scalar() or 0
        
        kpi_imports = html.Div([
            html.Div(f"{latest_imports:,.0f}", className='kpi-value'),
            html.Div("Latest Imports (bbl)", className='kpi-label'),
        ])
        
        # Reserves
        latest_reserves = db.session.query(
            func.sum(Reserves.reserves_bbl)
        ).filter(
            Reserves.country_id == country_id,
            Reserves.date == latest_date
        ).scalar() or 0
        
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
        
        start_date = datetime.now().date() - timedelta(days=365*5)
        
        results = db.session.query(
            Production.date,
            func.sum(Production.production_bbl).label('production')
        ).filter(
            Production.country_id == country_id,
            Production.date >= start_date
        ).group_by(Production.date).order_by(Production.date).all()
        
        df = pd.DataFrame([
            {'Date': r.date, 'Production (bbl)': r.production}
            for r in results
        ])
        
        if df.empty:
            return go.Figure()
        
        country = Country.query.get(country_id)
        fig = px.line(
            df,
            x='Date',
            y='Production (bbl)',
            title=f'{country.name} - Production Trend',
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
        
        start_date = datetime.now().date() - timedelta(days=365*5)
        
        results = db.session.query(
            Exports.date,
            func.sum(Exports.exports_bbl).label('exports')
        ).filter(
            Exports.country_id == country_id,
            Exports.date >= start_date
        ).group_by(Exports.date).order_by(Exports.date).all()
        
        df = pd.DataFrame([
            {'Date': r.date, 'Exports (bbl)': r.exports}
            for r in results
        ])
        
        if df.empty:
            return go.Figure()
        
        country = Country.query.get(country_id)
        fig = px.line(
            df,
            x='Date',
            y='Exports (bbl)',
            title=f'{country.name} - Exports Trend',
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
        
        start_date = datetime.now().date() - timedelta(days=365*2)
        
        exports_data = db.session.query(
            Exports.date,
            func.sum(Exports.exports_bbl).label('exports')
        ).filter(
            Exports.country_id == country_id,
            Exports.date >= start_date
        ).group_by(Exports.date).order_by(Exports.date).all()
        
        imports_data = db.session.query(
            Imports.date,
            func.sum(Imports.imports_bbl).label('imports')
        ).filter(
            Imports.country_id == country_id,
            Imports.date >= start_date
        ).group_by(Imports.date).order_by(Imports.date).all()
        
        country = Country.query.get(country_id)
        
        fig = go.Figure()
        
        if exports_data:
            fig.add_trace(go.Scatter(
                x=[r.date for r in exports_data],
                y=[r.exports for r in exports_data],
                name='Exports',
                line=dict(color='#27ae60', width=2)
            ))
        
        if imports_data:
            fig.add_trace(go.Scatter(
                x=[r.date for r in imports_data],
                y=[r.imports for r in imports_data],
                name='Imports',
                line=dict(color='#e74c3c', width=2)
            ))
        
        fig.update_layout(
            title=f'{country.name} - Trade Balance (Exports vs Imports)',
            xaxis_title='Date',
            yaxis_title='Volume (bbl)',
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=400
        )
        
        return fig
    
    return dash_app

