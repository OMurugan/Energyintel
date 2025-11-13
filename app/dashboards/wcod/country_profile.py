"""
Country Profile View
Individual country profile with detailed statistics
"""
from dash import dcc, html, Input, Output, callback
from app import db
from app.models import Country, Production, Exports, Imports, Reserves
from sqlalchemy import func


def create_layout(server):
    """Create the Country Profile layout"""
    with server.app_context():
        countries = Country.query.order_by(Country.name).all()
        country_options = [{'label': c.name, 'value': c.id} for c in countries]
    
    return html.Div([
        html.H3("Country Profile", style={'marginBottom': '20px'}),
        html.Div([
            html.Label("Select Country:", style={'fontWeight': '500', 'marginBottom': '8px'}),
            dcc.Dropdown(
                id='country-select-profile',
                options=country_options,
                value=country_options[0]['value'] if country_options else None,
                clearable=False,
                style={'marginBottom': '20px'}
            )
        ]),
        html.Div(id='country-profile-content')
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Country Profile"""
    
    @callback(
        Output('country-profile-content', 'children'),
        Input('country-select-profile', 'value')
    )
    def update_country_profile(country_id):
        """Update country profile content"""
        if not country_id:
            return html.Div("Please select a country")
        
        with server.app_context():
            country = Country.query.get(country_id)
            if not country:
                return html.Div("Country not found")
            
            latest_date = db.session.query(func.max(Production.date)).scalar()
            
            # Get latest production
            latest_prod = db.session.query(func.sum(Production.production_bbl)).filter(
                Production.country_id == country_id,
                Production.date == latest_date
            ).scalar() or 0
            
            # Get latest exports
            latest_exports = db.session.query(func.sum(Exports.exports_bbl)).filter(
                Exports.country_id == country_id,
                Exports.date == latest_date
            ).scalar() or 0
            
            # Get latest imports
            latest_imports = db.session.query(func.sum(Imports.imports_bbl)).filter(
                Imports.country_id == country_id,
                Imports.date == latest_date
            ).scalar() or 0
            
            # Get latest reserves
            latest_reserves = db.session.query(func.sum(Reserves.reserves_bbl)).filter(
                Reserves.country_id == country_id,
                Reserves.date == latest_date
            ).scalar() or 0
        
        return html.Div([
            html.H4(f"{country.name} Profile", style={'marginBottom': '20px'}),
            html.Div([
                html.Div([
                    html.H5("Production", style={'color': '#3498db'}),
                    html.P(f"{latest_prod:,.0f} bbl", style={'fontSize': '24px', 'fontWeight': '600'})
                ], className='col-md-3', style={'textAlign': 'center', 'padding': '20px', 'background': '#f8f9fa', 'borderRadius': '8px', 'margin': '10px'}),
                html.Div([
                    html.H5("Exports", style={'color': '#27ae60'}),
                    html.P(f"{latest_exports:,.0f} bbl", style={'fontSize': '24px', 'fontWeight': '600'})
                ], className='col-md-3', style={'textAlign': 'center', 'padding': '20px', 'background': '#f8f9fa', 'borderRadius': '8px', 'margin': '10px'}),
                html.Div([
                    html.H5("Imports", style={'color': '#e74c3c'}),
                    html.P(f"{latest_imports:,.0f} bbl", style={'fontSize': '24px', 'fontWeight': '600'})
                ], className='col-md-3', style={'textAlign': 'center', 'padding': '20px', 'background': '#f8f9fa', 'borderRadius': '8px', 'margin': '10px'}),
                html.Div([
                    html.H5("Reserves", style={'color': '#9b59b6'}),
                    html.P(f"{latest_reserves:,.0f} bbl", style={'fontSize': '24px', 'fontWeight': '600'})
                ], className='col-md-3', style={'textAlign': 'center', 'padding': '20px', 'background': '#f8f9fa', 'borderRadius': '8px', 'margin': '10px'}),
            ], className='row'),
            html.Div([
                html.P(f"Region: {country.region or 'N/A'}", style={'marginTop': '20px'}),
                html.P(f"Continent: {country.continent or 'N/A'}"),
            ])
        ])

