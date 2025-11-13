"""
Gross Product Worth and Margins View
GPW and margins analysis for crude types
"""
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from app import db
from app.models import Crude, CrudePrice
from sqlalchemy import func


def create_layout():
    """Create the GPW Margins layout"""
    return html.Div([
        html.H3("Gross Product Worth and Margins", style={'marginBottom': '20px'}),
        dcc.Graph(id='gpw-margins-chart')
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for GPW Margins"""
    
    @callback(
        Output('gpw-margins-chart', 'figure'),
        Input('current-submenu', 'data')
    )
    def update_gpw_margins(submenu):
        """Update GPW and margins chart"""
        if submenu != 'gpw-margins':
            return go.Figure()
        
        with server.app_context():
            latest_date = db.session.query(func.max(CrudePrice.date)).scalar()
            if not latest_date:
                fig = go.Figure()
                fig.add_annotation(
                    text="No price data available. Please seed CrudePrice data.",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
                fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
                return fig
            
            results = db.session.query(
                Crude.name,
                CrudePrice.gross_product_worth,
                CrudePrice.margin
            ).join(CrudePrice).filter(
                CrudePrice.date == latest_date
            ).limit(15).all()
            
            df = pd.DataFrame([
                {
                    'Crude': r.name,
                    'GPW': r.gross_product_worth or 0,
                    'Margin': r.margin or 0
                }
                for r in results
            ])
        
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No GPW/margin data available.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return fig
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(x=df['Crude'], y=df['GPW'], name='Gross Product Worth'),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(x=df['Crude'], y=df['Margin'], name='Margin', mode='lines+markers'),
            secondary_y=True,
        )
        fig.update_xaxes(title_text="Crude Type", tickangle=-45)
        fig.update_yaxes(title_text="GPW", secondary_y=False)
        fig.update_yaxes(title_text="Margin", secondary_y=True)
        fig.update_layout(
            title='Gross Product Worth and Margins',
            height=500,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return fig

