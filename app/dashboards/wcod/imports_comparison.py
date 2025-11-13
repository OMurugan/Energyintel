"""
Imports - Country Comparison View
Compare imports across countries
"""
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from app import db
from app.models import Country, Imports
from sqlalchemy import func


def create_layout():
    """Create the Imports - Country Comparison layout"""
    return html.Div([
        html.H3("Imports - Country Comparison", style={'marginBottom': '20px'}),
        dcc.Graph(id='imports-comparison-chart')
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Imports - Country Comparison"""
    
    @callback(
        Output('imports-comparison-chart', 'figure'),
        Input('current-submenu', 'data')
    )
    def update_imports_comparison(submenu):
        """Update imports comparison chart"""
        if submenu != 'imports-comparison':
            return go.Figure()
        
        with server.app_context():
            latest_date = db.session.query(func.max(Imports.date)).scalar()
            if not latest_date:
                return go.Figure()
            
            results = db.session.query(
                Country.name,
                Country.region,
                func.sum(Imports.imports_bbl).label('imports')
            ).join(Imports).filter(
                Imports.date == latest_date
            ).group_by(Country.id, Country.name, Country.region).order_by(
                func.sum(Imports.imports_bbl).desc()
            ).limit(15).all()
            
            df = pd.DataFrame([
                {'Country': r.name, 'Region': r.region or 'Unknown', 'Imports (bbl)': r.imports}
                for r in results
            ])
        
        if df.empty:
            return go.Figure()
        
        fig = px.bar(df, x='Country', y='Imports (bbl)', color='Region', 
                    title='Top 15 Countries by Imports (Comparison)')
        fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white', xaxis_tickangle=-45)
        return fig

