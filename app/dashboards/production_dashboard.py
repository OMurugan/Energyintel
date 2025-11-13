"""
Production Dashboard
Focused view on production metrics
"""
import dash
from dash import dcc, html, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from flask import current_app
from app import create_dash_app
from app.models import Country, Production
from app import db
from sqlalchemy import func, extract
from datetime import datetime, timedelta


def create_production_dashboard(server, url_base_pathname):
    """Create production-focused dashboard"""
    dash_app = create_dash_app(server, url_base_pathname)
    
    dash_app.layout = html.Div([
        html.Div([
            html.H1("Production Dashboard", className="mb-4"),
        ], className="container-fluid", style={'padding': '30px', 'background': 'white', 'marginBottom': '20px'}),
        
        html.Div([
            html.Div([
                dcc.Graph(id='production-heatmap'),
                dcc.Graph(id='production-regional-breakdown'),
            ], className='container-fluid', style={'padding': '30px'})
        ])
    ], style={'background': '#f5f5f5', 'minHeight': '100vh'})
    
    @callback(
        Output('production-heatmap', 'figure'),
        Input('production-heatmap', 'id')
    )
    def update_heatmap(_):
        """Update production heatmap"""
        latest_date = db.session.query(func.max(Production.date)).scalar()
        if not latest_date:
            return go.Figure()
        
        results = db.session.query(
            Country.name,
            Country.region,
            func.sum(Production.production_bbl).label('production')
        ).join(Production).filter(
            Production.date == latest_date
        ).group_by(Country.id, Country.name, Country.region).all()
        
        df = pd.DataFrame([
            {'Country': r.name, 'Region': r.region or 'Unknown', 'Production': r.production}
            for r in results
        ])
        
        if df.empty:
            return go.Figure()
        
        fig = px.treemap(
            df,
            path=['Region', 'Country'],
            values='Production',
            title='Production by Region and Country',
            color='Production',
            color_continuous_scale='Blues'
        )
        
        fig.update_layout(height=600)
        return fig
    
    @callback(
        Output('production-regional-breakdown', 'figure'),
        Input('production-regional-breakdown', 'id')
    )
    def update_regional_breakdown(_):
        """Update regional breakdown"""
        latest_date = db.session.query(func.max(Production.date)).scalar()
        if not latest_date:
            return go.Figure()
        
        results = db.session.query(
            Country.region,
            func.sum(Production.production_bbl).label('production')
        ).join(Production).filter(
            Production.date == latest_date
        ).group_by(Country.region).order_by(
            func.sum(Production.production_bbl).desc()
        ).all()
        
        df = pd.DataFrame([
            {'Region': r.region or 'Unknown', 'Production': r.production}
            for r in results
        ])
        
        if df.empty:
            return go.Figure()
        
        fig = px.pie(
            df,
            values='Production',
            names='Region',
            title='Production by Region'
        )
        
        fig.update_layout(height=500)
        return fig
    
    return dash_app

