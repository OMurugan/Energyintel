"""
Price Scorecard for Key World Oil Grades View
Price scorecard table for key crude grades
"""
from dash import dcc, html, Input, Output, callback, dash_table
import pandas as pd
from app import db
from app.models import Crude, CrudePrice, Country
from sqlalchemy import func


def create_layout():
    """Create the Price Scorecard layout"""
    return html.Div([
        html.H3("Price Scorecard for Key World Oil Grades", style={'marginBottom': '20px'}),
        dash_table.DataTable(
            id='price-scorecard-table',
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'}
        )
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Price Scorecard"""
    
    @callback(
        [Output('price-scorecard-table', 'data'),
         Output('price-scorecard-table', 'columns')],
        Input('current-submenu', 'data')
    )
    def update_price_scorecard(submenu):
        """Update price scorecard table"""
        if submenu != 'price-scorecard':
            return [], []
        
        with server.app_context():
            latest_date = db.session.query(func.max(CrudePrice.date)).scalar()
            if not latest_date:
                return [], []
            
            results = db.session.query(
                Crude.name,
                Country.name.label('country_name'),
                CrudePrice.price_usd_bbl,
                CrudePrice.benchmark
            ).join(Crude).join(Country).filter(
                CrudePrice.date == latest_date
            ).limit(20).all()
            
            df = pd.DataFrame([
                {
                    'Crude': r.name,
                    'Country': r.country_name,
                    'Price (USD/bbl)': r.price_usd_bbl or 0,
                    'Benchmark': r.benchmark or 'N/A'
                }
                for r in results
            ])
        
        if df.empty:
            return [], []
        
        columns = [{'name': col, 'id': col} for col in df.columns]
        data = df.to_dict('records')
        return data, columns

