"""
Global Exports View
Global exports overview by country and region
"""
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from app import db
from app.models import Country, Exports
from sqlalchemy import func


def create_layout():
    """Create the Global Exports layout"""
    return html.Div([
        html.H3("Global Exports", style={'marginBottom': '20px'}),
        dcc.Graph(id='global-exports-chart')
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Global Exports"""
    
    @callback(
        Output('global-exports-chart', 'figure'),
        Input('current-submenu', 'data')
    )
    def update_global_exports(submenu):
        """Update global exports chart"""
        if submenu != 'global-exports':
            return go.Figure()
        
        with server.app_context():
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
                {'Country': r.name, 'Region': r.region or 'Unknown', 'Exports (bbl)': r.exports}
                for r in results
            ])
        
        if df.empty:
            return go.Figure()
        
        fig = px.bar(df, x='Country', y='Exports (bbl)', color='Region', title='Global Exports by Country')
        fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white', xaxis_tickangle=-45)
        return fig

