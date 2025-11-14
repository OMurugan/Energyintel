"""
Crude Comparison View
Compare two crude types side by side
"""
from dash import dcc, html, Input, Output, callback, dash_table
from app import db
from app.models import Crude


def create_layout(server):
    """Create the Crude Comparison layout"""
    with server.app_context():
        crudes = Crude.query.order_by(Crude.name).all()
        crude_options = [{'label': f"{c.name} ({c.country.name if c.country else 'Unknown'})", 'value': c.id} for c in crudes]

    return html.Div([
        html.H3("Crude Comparison", style={'marginBottom': '20px'}),
        html.Div([
            html.Div([
                html.Label("Select Crude 1:", style={'fontWeight': '500', 'marginBottom': '8px'}),
                dcc.Dropdown(
                    id='crude-compare-1',
                    options=crude_options if crude_options else [],
                    clearable=False,
                    style={'marginBottom': '20px'}
                )
            ], className='col-md-6'),
            html.Div([
                html.Label("Select Crude 2:", style={'fontWeight': '500', 'marginBottom': '8px'}),
                dcc.Dropdown(
                    id='crude-compare-2',
                    options=crude_options if crude_options else [],
                    clearable=False,
                    style={'marginBottom': '20px'}
                )
            ], className='col-md-6'),
        ], className='row'),
        html.Div(id='crude-comparison-content')
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Crude Comparison"""

    @callback(
        Output('crude-comparison-content', 'children'),
        [Input('crude-compare-1', 'value'),
         Input('crude-compare-2', 'value')]
    )
    def update_crude_comparison(crude1_id, crude2_id):
        """Update crude comparison content"""
        if not crude1_id or not crude2_id:
            return html.Div("Please select both crudes to compare")

        with server.app_context():
            crude1 = Crude.query.get(crude1_id)
            crude2 = Crude.query.get(crude2_id)

            if not crude1 or not crude2:
                return html.Div("One or both crudes not found")

        comparison_data = [
            {'Property': 'Name', f'{crude1.name}': crude1.name, f'{crude2.name}': crude2.name},
            {'Property': 'Country', f'{crude1.name}': crude1.country.name if crude1.country else 'N/A', f'{crude2.name}': crude2.country.name if crude2.country else 'N/A'},
            {'Property': 'Grade', f'{crude1.name}': crude1.grade or 'N/A', f'{crude2.name}': crude2.grade or 'N/A'},
            {'Property': 'API Gravity', f'{crude1.name}': crude1.api_gravity or 'N/A', f'{crude2.name}': crude2.api_gravity or 'N/A'},
            {'Property': 'Sulfur Content (%)', f'{crude1.name}': crude1.sulfur_content or 'N/A', f'{crude2.name}': crude2.sulfur_content or 'N/A'},
            {'Property': 'Carbon Intensity', f'{crude1.name}': crude1.carbon_intensity or 'N/A', f'{crude2.name}': crude2.carbon_intensity or 'N/A'},
        ]

        return html.Div([
            dash_table.DataTable(
                data=comparison_data,
                columns=[{'name': 'Property', 'id': 'Property'}, 
                        {'name': crude1.name, 'id': f'{crude1.name}'},
                        {'name': crude2.name, 'id': f'{crude2.name}'}],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'}
            )
        ])