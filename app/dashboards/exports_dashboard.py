"""
Exports Dashboard
Focused view on export metrics
"""
import dash
from dash import dcc, html, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from flask import current_app
from app import create_dash_app
from app.models import Country, Exports
from app import db
from sqlalchemy import func
from datetime import datetime, timedelta


def create_exports_dashboard(server, url_base_pathname):
    """Create exports-focused dashboard"""
    dash_app = create_dash_app(server, url_base_pathname)
    
    dash_app.layout = html.Div([
        html.Div([
            html.H1("Exports Dashboard", className="mb-4"),
        ], className="container-fluid", style={'padding': '30px', 'background': 'white', 'marginBottom': '20px'}),
        
        html.Div([
            html.Div([
                dcc.Graph(id='exports-by-country'),
                dcc.Graph(id='exports-trend-global'),
            ], className='container-fluid', style={'padding': '30px'})
        ])
    ], style={'background': '#f5f5f5', 'minHeight': '100vh'})
    
    @callback(
        Output('exports-by-country', 'figure'),
        Input('exports-by-country', 'id')
    )
    def update_exports_by_country(_):
        """Update exports by country chart"""
        latest_date = db.session.query(func.max(Exports.date)).scalar()
        if not latest_date:
            return go.Figure()
        
        results = db.session.query(
            Country.name,
            Country.region,
            func.sum(Exports.exports_bbl).label('exports')
        ).join(Exports).filter(
            Exports.date == latest_date
        ).group_by(Country.id, Country.name, Country.region).order_by(
            func.sum(Exports.exports_bbl).desc()
        ).limit(20).all()
        
        df = pd.DataFrame([
            {'Country': r.name, 'Region': r.region or 'Unknown', 'Exports': r.exports}
            for r in results
        ])
        
        if df.empty:
            return go.Figure()
        
        fig = px.bar(
            df,
            x='Country',
            y='Exports',
            color='Region',
            title='Top 20 Countries by Exports',
            labels={'Exports': 'Exports (bbl)', 'Country': 'Country'}
        )
        
        fig.update_layout(height=500, xaxis_tickangle=-45)
        return fig
    
    @callback(
        Output('exports-trend-global', 'figure'),
        Input('exports-trend-global', 'id')
    )
    def update_exports_trend(_):
        """Update global exports trend"""
        start_date = datetime.now().date() - timedelta(days=365*5)
        
        results = db.session.query(
            Exports.date,
            func.sum(Exports.exports_bbl).label('total_exports')
        ).filter(
            Exports.date >= start_date
        ).group_by(Exports.date).order_by(Exports.date).all()
        
        df = pd.DataFrame([
            {'Date': r.date, 'Exports': r.total_exports}
            for r in results
        ])
        
        if df.empty:
            return go.Figure()
        
        fig = px.line(
            df,
            x='Date',
            y='Exports',
            title='Global Exports Trend',
            markers=True
        )
        
        fig.update_traces(line_color='#27ae60', line_width=2)
        fig.update_layout(height=500)
        return fig
    
    return dash_app

