"""
Russian Exports by Terminal and Exporting Company View
Detailed Russian exports data
"""
from dash import dcc, html, Input, Output, callback, dash_table
import plotly.graph_objects as go
import pandas as pd
from app import db
from app.models import Country, Exports
from sqlalchemy import func


def create_layout():
    """Create the Russian Exports layout"""
    return html.Div([
        html.H3("Russian Exports by Terminal and Exporting Company", style={'marginBottom': '20px'}),
        html.Div([
            dcc.Graph(id='russian-exports-chart')
        ]),
        html.Div([
            dash_table.DataTable(
                id='russian-exports-table',
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'}
            )
        ], style={'marginTop': '20px'})
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Russian Exports"""
    
    @callback(
        [Output('russian-exports-chart', 'figure'),
         Output('russian-exports-table', 'data'),
         Output('russian-exports-table', 'columns')],
        Input('current-submenu', 'data')
    )
    def update_russian_exports(submenu):
        """Update Russian exports chart and table"""
        if submenu != 'russian-exports':
            return go.Figure(), [], []
        
        with server.app_context():
            russia = Country.query.filter_by(code='RUS').first()
            if not russia:
                fig = go.Figure()
                fig.add_annotation(
                    text="Russia not found in database. Please seed country data.",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
                fig.update_layout(height=400, plot_bgcolor='white', paper_bgcolor='white')
                return fig, [], []
            
            latest_date = db.session.query(func.max(Exports.date)).scalar()
            if not latest_date:
                return go.Figure(), [], []
            
            results = db.session.query(
                func.sum(Exports.exports_bbl).label('total_exports')
            ).filter(
                Exports.country_id == russia.id,
                Exports.date == latest_date
            ).scalar() or 0
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=['Russia'],
            y=[results],
            name='Total Exports',
            marker_color='#e74c3c'
        ))
        fig.update_layout(
            title='Russian Exports (Latest Period)',
            height=400,
            plot_bgcolor='white',
            paper_bgcolor='white',
            yaxis_title='Exports (bbl)'
        )
        
        table_data = [{'Country': 'Russia', 'Exports (bbl)': results, 'Date': latest_date.isoformat() if latest_date else 'N/A'}]
        columns = [{'name': 'Country', 'id': 'Country'}, 
                  {'name': 'Exports (bbl)', 'id': 'Exports (bbl)'},
                  {'name': 'Date', 'id': 'Date'}]
        
        return fig, table_data, columns

