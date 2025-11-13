"""
Crude Overview View
Overview of crude oil types and quality data
"""
from dash import dcc, html, Input, Output, callback, dash_table
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from app import db
from app.models import Crude, Country


def create_layout():
    """Create the Crude Overview layout"""
    return html.Div([
        html.H3("Crude Overview", style={'marginBottom': '20px'}),
        html.Div([
            html.Div([
                dcc.Graph(id='crude-overview-chart')
            ], className='col-md-12'),
        ], className='row'),
        html.Div([
            dash_table.DataTable(
                id='crude-overview-table',
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'}
            )
        ], style={'marginTop': '20px'})
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Crude Overview"""
    
    @callback(
        [Output('crude-overview-chart', 'figure'),
         Output('crude-overview-table', 'data'),
         Output('crude-overview-table', 'columns')],
        Input('current-submenu', 'data')
    )
    def update_crude_overview(submenu):
        """Update crude overview chart and table"""
        if submenu != 'crude-overview':
            return go.Figure(), [], []
        
        with server.app_context():
            results = db.session.query(
                Crude.name,
                Country.name.label('country_name'),
                Crude.grade,
                Crude.api_gravity,
                Crude.sulfur_content
            ).join(Country).all()
            
            df = pd.DataFrame([
                {
                    'Crude': r.name,
                    'Country': r.country_name,
                    'Grade': r.grade or 'N/A',
                    'API Gravity': r.api_gravity or 0,
                    'Sulfur Content (%)': r.sulfur_content or 0
                }
                for r in results
            ])
        
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No crude data available. Please seed Crude data.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(height=400, plot_bgcolor='white', paper_bgcolor='white')
            return fig, [], []
        
        fig = px.bar(df, x='Crude', y='API Gravity', color='Country', title='Crude Types by API Gravity')
        fig.update_layout(height=400, plot_bgcolor='white', paper_bgcolor='white', xaxis_tickangle=-45)
        
        columns = [{'name': col, 'id': col} for col in df.columns]
        data = df.to_dict('records')
        
        return fig, data, columns

