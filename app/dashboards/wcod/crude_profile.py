"""
Crude Profile View
Individual crude type profile with detailed specifications
"""
from dash import dcc, html, Input, Output
from app import db, create_dash_app
from app.models import Crude, Country


def create_layout(server):
    """Create the Crude Profile layout"""
    # Don't query database at layout creation time - do it in a callback instead
    return html.Div([
        html.H3("Crude Profile", style={'marginBottom': '20px'}),
        html.Div([
            html.Label("Select Crude Type:", style={'fontWeight': '500', 'marginBottom': '8px'}),
            dcc.Dropdown(
                id='crude-select-profile',
                options=[],  # Will be populated by callback
                value=None,
                clearable=False,
                style={'marginBottom': '20px'}
            )
        ]),
        html.Div(id='crude-profile-content')
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Crude Profile"""
    
    @dash_app.callback(
        Output('crude-select-profile', 'options'),
        Output('crude-select-profile', 'value'),
        Input('crude-select-profile', 'id'),  # Trigger on initial load
        prevent_initial_call=False
    )
    def load_crude_options(_):
        """Load crude options from database"""
        try:
            with server.app_context():
                crudes = Crude.query.order_by(Crude.name).all()
                crude_options = [{'label': f"{c.name} ({c.country.name if c.country else 'Unknown'})", 'value': c.id} for c in crudes]
                default_value = crude_options[0]['value'] if crude_options else None
                return crude_options, default_value
        except Exception as e:
            print(f"Error loading crudes: {e}")
            return [{'label': 'Database connection error', 'value': None}], None
    
    @dash_app.callback(
        Output('crude-profile-content', 'children'),
        Input('crude-select-profile', 'value')
    )
    def update_crude_profile(crude_id):
        """Update crude profile content"""
        if not crude_id:
            return html.Div("Please select a crude type")
        
        try:
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
        except Exception as e:
            print(f"Error loading crude profile: {e}")
            return html.Div(f"Error loading crude profile: {str(e)}", style={'color': 'red', 'padding': '20px'})


# ------------------------------------------------------------------------------
# DASH APP CREATION
# ------------------------------------------------------------------------------
def create_crude_profile_dashboard(server, url_base_pathname="/dash/crude-profile/"):
    """Create the Crude Profile dashboard"""
    dash_app = create_dash_app(server, url_base_pathname)
    dash_app.layout = create_layout(server)
    register_callbacks(dash_app, server)
    return dash_app

