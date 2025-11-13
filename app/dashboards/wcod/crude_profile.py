"""
Crude Profile View
Individual crude type profile with detailed specifications
"""
from dash import dcc, html, Input, Output, callback
from app import db
from app.models import Crude, Country


def create_layout(server):
    """Create the Crude Profile layout"""
    with server.app_context():
        crudes = Crude.query.order_by(Crude.name).all()
        crude_options = [{'label': f"{c.name} ({c.country.name if c.country else 'Unknown'})", 'value': c.id} for c in crudes]
    
    return html.Div([
        html.H3("Crude Profile", style={'marginBottom': '20px'}),
        html.Div([
            html.Label("Select Crude Type:", style={'fontWeight': '500', 'marginBottom': '8px'}),
            dcc.Dropdown(
                id='crude-select-profile',
                options=crude_options if crude_options else [{'label': 'No crudes available', 'value': None}],
                value=crude_options[0]['value'] if crude_options else None,
                clearable=False,
                style={'marginBottom': '20px'}
            )
        ]),
        html.Div(id='crude-profile-content')
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Crude Profile"""
    
    @callback(
        Output('crude-profile-content', 'children'),
        Input('crude-select-profile', 'value')
    )
    def update_crude_profile(crude_id):
        """Update crude profile content"""
        if not crude_id:
            return html.Div("Please select a crude type")
        
        with server.app_context():
            crude = Crude.query.get(crude_id)
            if not crude:
                return html.Div("Crude not found")
        
        return html.Div([
            html.H4(f"{crude.name} Profile", style={'marginBottom': '20px'}),
            html.Div([
                html.Div([
                    html.P(f"Country: {crude.country.name if crude.country else 'N/A'}", style={'fontSize': '16px'}),
                    html.P(f"Grade: {crude.grade or 'N/A'}", style={'fontSize': '16px'}),
                    html.P(f"API Gravity: {crude.api_gravity or 'N/A'}", style={'fontSize': '16px'}),
                    html.P(f"Sulfur Content: {crude.sulfur_content or 'N/A'}%", style={'fontSize': '16px'}),
                    html.P(f"Carbon Intensity: {crude.carbon_intensity or 'N/A'}", style={'fontSize': '16px'}),
                ], style={'padding': '20px', 'background': '#f8f9fa', 'borderRadius': '8px'})
            ])
        ])

