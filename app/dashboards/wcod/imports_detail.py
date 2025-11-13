"""
Imports - Country Detail View
Detailed imports data by country
"""
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from app import db
from app.models import Country, Imports
from sqlalchemy import func


def create_layout():
    """Create the Imports - Country Detail layout"""
    return html.Div([
        html.H3("Imports - Country Detail", style={'marginBottom': '20px'}),
        dcc.Graph(id='imports-detail-chart')
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Imports - Country Detail"""
    
    @callback(
        Output('imports-detail-chart', 'figure'),
        Input('current-submenu', 'data')
    )
    def update_imports_detail(submenu):
        """Update imports detail chart"""
        if submenu != 'imports-detail':
            return go.Figure()
        
        with server.app_context():
            latest_date = db.session.query(func.max(Imports.date)).scalar()
            if not latest_date:
                return go.Figure()
            
            results = db.session.query(
                Country.name,
                func.sum(Imports.imports_bbl).label('imports')
            ).join(Imports).filter(
                Imports.date == latest_date
            ).group_by(Country.id, Country.name).order_by(
                func.sum(Imports.imports_bbl).desc()
            ).limit(20).all()
            
            df = pd.DataFrame([
                {'Country': r.name, 'Imports (bbl)': r.imports}
                for r in results
            ])
        
        if df.empty:
            return go.Figure()
        
        fig = px.bar(df, x='Country', y='Imports (bbl)', title='Imports by Country')
        fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white', xaxis_tickangle=-45)
        return fig

