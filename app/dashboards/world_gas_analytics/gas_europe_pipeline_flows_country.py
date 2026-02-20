"""
European Gas Trade - Pipeline Flows by Country
Country-specific pipeline flow analytics
"""
import os
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, callback, State, dash_table, clientside_callback, no_update
from core.data_helpers import execute_query

# Color Palette
EI_ORANGE = "#ff6600"
EI_DARK_BLUE = "#1b365d"
EI_LIGHT_BLUE = "#e8f4f8"

# Granularity Button Styles
GRAN_BTN_ACTIVE = {
    'width': '18px',
    'height': '18px',
    'padding': '0',
    'border': '1px solid #007bff',
    'backgroundColor': 'white',
    'color': '#add8e6',
    'borderRadius': '3px',
    'cursor': 'pointer',
    'fontSize': '12px',
    'fontWeight': 'bold',
    'display': 'flex',
    'alignItems': 'center',
    'justifyContent': 'center'
}

GRAN_BTN_INACTIVE = {
    'width': '18px',
    'height': '18px',
    'padding': '0',
    'border': '1px solid #007bff',
    'backgroundColor': 'white',
    'color': '#007bff',
    'borderRadius': '3px',
    'cursor': 'pointer',
    'fontSize': '12px',
    'fontWeight': 'bold',
    'display': 'flex',
    'alignItems': 'center',
    'justifyContent': 'center'
}

# Qualitative colors for countries - matching the reference image
COUNTRY_COLORS = {
    'Belgium': '#4c78a8',           # Dark blue
    'Bulgaria': '#72b7b2',          # Light blue/teal
    'Denmark': '#ff9d4a',           # Orange
    'Finland': '#ffcc99',           # Light orange/peach
    'France': '#e15759',            # Red
    'Germany': '#76b7b2',           # Teal/green
    'Greece': '#b07aa1',            # Purple/pink
    'Hungary': '#9ccc65',           # Light green
    'Italy': '#1f77b4',             # Dark blue
    'Joint Baltic Zone EE/LV': '#bcbd22',  # Olive/yellow-green
    'Lithuania': '#d62728',         # Dark red/brown
    'Moldova': '#ffcc00',           # Yellow
    'Netherlands': '#2ca02c',       # Green
    'Poland': '#17becf',            # Cyan/teal
    'Romania': '#7fcdcd',           # Light teal
    'Slovakia': '#8c564b',          # Brown
    'Spain': '#636363',             # Dark gray
    'United Kingdom': '#ffff00'     # Bright yellow
}

def create_period_selector(prefix):
    """Helper to create independent period selectors for chart or table"""
    return html.Div([
        html.Div([
            html.Span("Yr of Dt", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
            html.Button('+', id=f'gas-country-toggle-year-btn-{prefix}', n_clicks=0, style=GRAN_BTN_INACTIVE)
        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
        
        html.Div([
            html.Span("Qtr of Dt", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
            html.Button('+', id=f'gas-country-toggle-quarter-btn-{prefix}', n_clicks=0, style=GRAN_BTN_INACTIVE)
        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
        
        html.Div([
            html.Span("Mth of Dt", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
            html.Button('-', id=f'gas-country-toggle-month-btn-{prefix}', n_clicks=0, style=GRAN_BTN_ACTIVE)
        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),

        html.Div([
            html.Span("Day of Dt", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
            html.Button('+', id=f'gas-country-toggle-day-btn-{prefix}', n_clicks=0, style=GRAN_BTN_INACTIVE)
        ], style={'display': 'flex', 'alignItems': 'center'})
    ], style={
        'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#f8f9fa', 
        'padding': '5px 10px', 'borderRadius': '4px', 'marginBottom': '10px',
        'width': 'fit-content'
    })

def load_data():
    """Load and preprocess data from database - using european_gas_trade table"""
    try:
        # Use the european_gas_trade table which is known to work
        query = """
        SELECT
            tr.source_country AS gas_origin,
            tr.target_country,
            tr.date AS date,
            tr."flow_mcm/d" / 1000.0 AS flows_bcm
        FROM european_gas_trade tr
        WHERE tr.source_country IN ('Algeria','Azerbaijan','Libya','Norway','Russia')
        ORDER BY tr.date;
        """
        
        results = execute_query(query, {})
        df = pd.DataFrame(results)
        
        if df.empty:
            return pd.DataFrame()
            
        # Convert types
        df['flows_bcm'] = pd.to_numeric(df['flows_bcm'], errors='coerce').fillna(0).astype(float)
        df['date'] = pd.to_datetime(df['date'])

        # AGGREGATION: Sum up flows by date, origin, and target country
        df = df.groupby(['date', 'gas_origin', 'target_country'])['flows_bcm'].sum().reset_index()
        
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def create_layout():
    """Create the European Pipeline Flows by Country layout"""
    # Initialize with default values for immediate render
    # Data loading is deferred to callbacks to prevent white screen on load
    
    # Defaults matching the query filters
    origins = ['Algeria', 'Azerbaijan', 'Libya', 'Norway', 'Russia']
    
    # Default destinations (same as fallback in callback)
    destinations = ['Belgium', 'Bulgaria', 'Denmark', 'Finland', 'France', 'Germany', 'Greece', 'Hungary', 'Italy', 'Lithuania', 'Moldova', 'Netherlands', 'Poland', 'Romania', 'Slovakia', 'Spain']
    
    # Default selection
    default_origin = 'Russia'

    return html.Div([
        # Selection stores
        dcc.Store(id='gas-country-chart-period-store', data='MONTH'),
        dcc.Store(id='gas-country-table-period-store', data='MONTH'),
        dcc.Store(id='gas-country-table-selection-store', data={'selected_column_id': None}),
        
        # Main container with Flexbox for Sidebar and Content
        html.Div([
            
            # Sidebar Filter (Right side)
            html.Div([
                html.Div([
                    html.Label("Gas Origin", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE, 'display': 'block', 'marginBottom': '8px'}),
                    dcc.RadioItems(
                        id='gas-country-origin-radio',
                        options=[{'label': ' (All)', 'value': '(All)'}] + [{'label': f' {o}', 'value': o} for o in origins],
                        value=default_origin,
                        style={'fontSize': '12px', 'color': '#333'},
                        labelStyle={'display': 'block', 'marginBottom': '4px', 'paddingLeft': '5px'}
                    ),
                    
                    html.Label("Start Date", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE, 'marginTop': '20px', 'display': 'block', 'marginBottom': '5px'}),
                    dcc.Input(
                        id='gas-country-start-date',
                        type='text',
                        value='2021-01-01',
                        placeholder='YYYY-MM-DD',
                        className='custom-date-input',
                        style={
                            'width': '100%', 'marginBottom': '10px', 'height': '28px',
                            'fontSize': '12px', 'fontFamily': 'Inter, sans-serif',
                            'border': '1px solid #999', 'borderRadius': '0px', 'padding': '0 5px', 'color': '#333'
                        }
                    ),
                    
                    html.Label("End Date", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE, 'marginBottom': '5px', 'display': 'block'}),
                    dcc.Input(
                        id='gas-country-end-date',
                        type='text',
                        value='2026-01-09',
                        placeholder='YYYY-MM-DD',
                        className='custom-date-input',
                        style={
                            'width': '100%', 'marginBottom': '20px', 'height': '28px',
                            'fontSize': '12px', 'fontFamily': 'Inter, sans-serif',
                            'border': '1px solid #999', 'borderRadius': '0px', 'padding': '0 5px', 'color': '#333'
                        }
                    ),
                    
                    # Unified Destination Filter & Legend
                    html.Label("Destination", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE, 'marginBottom': '10px', 'display': 'block'}),
                    
                    # Destination items will be populated by callback
                    html.Div(id='gas-country-dest-list'),
                    
                    # Hidden checklist for maintaining filter functionality
                    dcc.Checklist(
                        id='gas-country-dest-checklist',
                        options=[{'label': o, 'value': o} for o in destinations],
                        value=destinations[:12], # Default select first 12
                        style={'display': 'none'}
                    ),
                ], style={'padding': '0px', 'backgroundColor': 'transparent', 'height': '100%'})
            ], style={'width': '220px', 'order': '2', 'marginLeft': '25px', 'borderLeft': '1px solid #f0f0f0', 'paddingLeft': '20px'}),
            
            # Content Area (Left side)
            html.Div([
                # Chart Section with title and export button
                html.Div([
                    html.H3(id='gas-country-dynamic-title', style={
                        'color': EI_ORANGE, 'fontSize': '20px', 'fontWeight': 'bold',
                        'margin': '0 0 10px 0', 'fontFamily': 'Inter, sans-serif'
                    }),
                    html.Button(
                        "Export to CSV",
                        id="export-gas-country-chart-btn",
                        n_clicks=0,
                        style={
                            'backgroundColor': '#f8f9fa',
                            'color': '#666',
                            'border': '1px solid #ddd',
                            'padding': '6px 12px',
                            'borderRadius': '4px',
                            'fontSize': '11px',
                            'fontFamily': 'Inter, sans-serif',
                            'cursor': 'pointer',
                            'position': 'absolute',
                            'top': '10px',
                            'right': '15px'
                        }
                    )
                ], style={'position': 'relative', 'marginBottom': '10px'}),
                
                create_period_selector('chart'),
                
                dcc.Loading(
                    id='loading-gas-country-chart',
                    type='circle',
                    color=EI_ORANGE,
                    children=dcc.Graph(
                        id='gas-country-line-chart',
                        style={'height': '500px'},
                        config={'displayModeBar': False}
                    )
                ),
                
                # Table Area with header and export button
                html.Div([
                    # Table header with export button
                    html.Div([
                        html.H3("Gas Pipeline Flows to Europe-Billion Cubic Meters", style={
                            'color': EI_ORANGE, 'fontSize': '20px', 'fontWeight': 'bold',
                            'margin': '0', 'fontFamily': 'Inter, sans-serif'
                        }),
                        html.Button(
                            "Export to CSV",
                            id="export-gas-country-table-btn",
                            n_clicks=0,
                            style={
                                'backgroundColor': '#f8f9fa',
                                'color': '#666',
                                'border': '1px solid #ddd',
                                'padding': '6px 12px',
                                'borderRadius': '4px',
                                'fontSize': '11px',
                                'fontFamily': 'Inter, sans-serif',
                                'cursor': 'pointer'
                            }
                        )
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px', 'paddingTop': '10px'}),
                    
                    create_period_selector('table'),
                    
                    dcc.Loading(
                        id='loading-gas-country-table',
                        type='circle',
                        color=EI_ORANGE,
                        children=html.Div(id='gas-country-table-container', style={'marginTop': '10px'})
                    ),

                    # Footer text
                    html.Div([
                        html.P("Source: Energy Intelligence, Transmission System Operators, Federal Agencies", 
                               style={
                                   'fontSize': '10px', 
                                   'color': '#666', 
                                   'fontStyle': 'italic', 
                                   'marginTop': '10px', 
                                   'marginBottom': '0', 
                                   'fontFamily': 'Inter, sans-serif'
                               })
                    ])
                ], style={'marginTop': '20px'}),
                
                # Hidden div for clientside callback anchor
                html.Div(id='gas-country-table-enhancer-anchor', style={'display': 'none'}),
                
                # Hidden div to store selected destination for chart highlighting
                html.Div(id='gas-country-selected-destination', style={'display': 'none'}),
                
                # Interval component for monitoring destination clicks
                dcc.Interval(
                    id='gas-country-legend-interval',
                    interval=500,  # Check every 500ms
                    n_intervals=0,
                    disabled=False
                ),
                
                # Download components
                dcc.Download(id="download-gas-country-chart-csv"),
                dcc.Download(id="download-gas-country-table-csv")

            ], style={'flex': '1', 'order': '1', 'minWidth': '0', 'overflow': 'hidden'})
            
        ], style={'display': 'flex', 'padding': '15px'})
    ], className='tab-content', style={'backgroundColor': 'white', 'maxWidth': '1600px', 'margin': '0 auto'})


def register_callbacks(dash_app, server):
    """Register all callbacks for European Pipeline Flows by Country"""

    # Clientside callback to convert text inputs to date inputs (bypasses Dash validation)
    dash_app.clientside_callback(
        """
        function() {
            setTimeout(function() {
                const startInput = document.getElementById('gas-country-start-date');
                const endInput = document.getElementById('gas-country-end-date');
                
                if (startInput && startInput.type === 'text') {
                    startInput.type = 'date';
                    startInput.max = new Date().toISOString().split('T')[0];
                }
                
                if (endInput && endInput.type === 'text') {
                    endInput.type = 'date';
                    endInput.max = new Date().toISOString().split('T')[0];
                }
            }, 100);
            return null;
        }
        """,
        Output('gas-country-table-enhancer-anchor', 'children', allow_duplicate=True),
        Input('gas-country-start-date', 'id'),
        prevent_initial_call='initial_duplicate'
    )

    @dash_app.callback(
        Output('gas-country-dynamic-title', 'children'),
        Input('gas-country-origin-radio', 'value')
    )
    def update_title(selected_origin):
        if selected_origin == '(All)':
            return "All's Pipeline gas Flows to Europe -Billion Cubic Meters"
        return f"{selected_origin}'s Pipeline gas Flows to Europe -Billion Cubic Meters"

    # Chart Granularity Toggle
    @dash_app.callback(
        [Output('gas-country-chart-period-store', 'data'),
         Output('gas-country-toggle-year-btn-chart', 'children'),
         Output('gas-country-toggle-quarter-btn-chart', 'children'),
         Output('gas-country-toggle-month-btn-chart', 'children'),
         Output('gas-country-toggle-day-btn-chart', 'children'),
         Output('gas-country-toggle-year-btn-chart', 'style'),
         Output('gas-country-toggle-quarter-btn-chart', 'style'),
         Output('gas-country-toggle-month-btn-chart', 'style'),
         Output('gas-country-toggle-day-btn-chart', 'style')],
        [Input('gas-country-toggle-year-btn-chart', 'n_clicks'),
         Input('gas-country-toggle-quarter-btn-chart', 'n_clicks'),
         Input('gas-country-toggle-month-btn-chart', 'n_clicks'),
         Input('gas-country-toggle-day-btn-chart', 'n_clicks')],
        [State('gas-country-chart-period-store', 'data')]
    )
    def toggle_chart_granularity(y_c, q_c, m_c, d_c, current_gran):
        from dash import callback_context
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
        btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
        new_gran = current_gran
        
        if 'year' in btn_id: new_gran = 'YEAR'
        elif 'quarter' in btn_id: new_gran = 'QUARTER'
        elif 'month' in btn_id: new_gran = 'MONTH'
        elif 'day' in btn_id: new_gran = 'DAILY'
        
        return (
            new_gran,
            '-' if new_gran == 'YEAR' else '+',
            '-' if new_gran == 'QUARTER' else '+',
            '-' if new_gran == 'MONTH' else '+',
            '-' if new_gran == 'DAILY' else '+',
            GRAN_BTN_ACTIVE if new_gran == 'YEAR' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'QUARTER' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'MONTH' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'DAILY' else GRAN_BTN_INACTIVE
        )

    # Table Granularity Toggle
    @dash_app.callback(
        [Output('gas-country-table-period-store', 'data'),
         Output('gas-country-toggle-year-btn-table', 'children'),
         Output('gas-country-toggle-quarter-btn-table', 'children'),
         Output('gas-country-toggle-month-btn-table', 'children'),
         Output('gas-country-toggle-day-btn-table', 'children'),
         Output('gas-country-toggle-year-btn-table', 'style'),
         Output('gas-country-toggle-quarter-btn-table', 'style'),
         Output('gas-country-toggle-month-btn-table', 'style'),
         Output('gas-country-toggle-day-btn-table', 'style')],
        [Input('gas-country-toggle-year-btn-table', 'n_clicks'),
         Input('gas-country-toggle-quarter-btn-table', 'n_clicks'),
         Input('gas-country-toggle-month-btn-table', 'n_clicks'),
         Input('gas-country-toggle-day-btn-table', 'n_clicks')],
        [State('gas-country-table-period-store', 'data')]
    )
    def toggle_table_granularity(y_c, q_c, m_c, d_c, current_gran):
        from dash import callback_context
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
        btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
        new_gran = current_gran
        
        if 'year' in btn_id: new_gran = 'YEAR'
        elif 'quarter' in btn_id: new_gran = 'QUARTER'
        elif 'month' in btn_id: new_gran = 'MONTH'
        elif 'day' in btn_id: new_gran = 'DAILY'
        
        return (
            new_gran,
            '-' if new_gran == 'YEAR' else '+',
            '-' if new_gran == 'QUARTER' else '+',
            '-' if new_gran == 'MONTH' else '+',
            '-' if new_gran == 'DAILY' else '+',
            GRAN_BTN_ACTIVE if new_gran == 'YEAR' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'QUARTER' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'MONTH' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'DAILY' else GRAN_BTN_INACTIVE
        )

    # NEW CALLBACK: Update destination options based on selected gas origin
    @dash_app.callback(
        [Output('gas-country-dest-list', 'children'),
         Output('gas-country-dest-checklist', 'options'),
         Output('gas-country-dest-checklist', 'value')],
        Input('gas-country-origin-radio', 'value')
    )
    def update_destination_options(selected_origin):
        try:
            # Get available destinations for the selected origin using european_gas_trade table
            if selected_origin == '(All)':
                # If All is selected, show all destinations
                query = """
                SELECT DISTINCT tr.target_country
                FROM european_gas_trade tr
                WHERE tr.source_country IN ('Algeria','Azerbaijan','Libya','Norway','Russia')
                ORDER BY tr.target_country;
                """
                results = execute_query(query, {})
            else:
                # If specific origin is selected, show only destinations for that origin
                query = """
                SELECT DISTINCT tr.target_country
                FROM european_gas_trade tr
                WHERE tr.source_country = :selected_origin
                ORDER BY tr.target_country;
                """
                results = execute_query(query, {'selected_origin': selected_origin})
            
            if results:
                destinations = [row['target_country'] for row in results if row['target_country']]
                
                # Create clickable destination items
                dest_items = []
                for dest in destinations:
                    dest_items.append(
                        html.Div([
                            html.Div(style={
                                'width': '14px', 
                                'height': '14px', 
                                'backgroundColor': COUNTRY_COLORS.get(dest, '#ccc'), 
                                'marginRight': '10px', 
                                'borderRadius': '1px',
                                'display': 'inline-block'
                            }),
                            html.Span(dest, style={'display': 'inline-block'})
                        ], 
                        id=f'dest-item-{dest}',
                        style={
                            'display': 'flex', 
                            'alignItems': 'center', 
                            'padding': '6px 8px',
                            'cursor': 'pointer',
                            'borderRadius': '4px',
                            'marginBottom': '2px',
                            'transition': 'all 0.2s ease',
                            'fontSize': '12px',
                            'color': '#666'
                        },
                        className='destination-item',
                        **{'data-country': dest}
                        )
                    )
                
                # Create options for hidden checklist
                options = [{'label': dest, 'value': dest} for dest in destinations]
                
                # Select all available destinations by default
                return dest_items, options, destinations
            else:
                return [], [], []
                
        except Exception as e:
            print(f"Error updating destination options: {e}")
            # Fallback to default destinations
            default_destinations = ['Belgium', 'Bulgaria', 'Denmark', 'Finland', 'France', 'Germany', 'Greece', 'Hungary', 'Italy', 'Lithuania', 'Moldova', 'Netherlands', 'Poland', 'Romania', 'Slovakia', 'Spain']
            
            dest_items = []
            for dest in default_destinations:
                dest_items.append(
                    html.Div([
                        html.Div(style={
                            'width': '14px', 
                            'height': '14px', 
                            'backgroundColor': COUNTRY_COLORS.get(dest, '#ccc'), 
                            'marginRight': '10px', 
                            'borderRadius': '1px',
                            'display': 'inline-block'
                        }),
                        html.Span(dest, style={'display': 'inline-block'})
                    ], 
                    id=f'dest-item-{dest}',
                    style={
                        'display': 'flex', 
                        'alignItems': 'center', 
                        'padding': '6px 8px',
                        'cursor': 'pointer',
                        'borderRadius': '4px',
                        'marginBottom': '2px',
                        'transition': 'all 0.2s ease',
                        'fontSize': '12px',
                        'color': '#666'
                    },
                    className='destination-item',
                    **{'data-country': dest}
                    )
                )
            
            options = [{'label': dest, 'value': dest} for dest in default_destinations]
            return dest_items, options, default_destinations[:12]


    # Clientside callback for destination item clicks
    dash_app.clientside_callback(
        """
        function(children) {
            if (!children) return window.dash_clientside.no_update;
            
            setTimeout(function() {
                const destItems = document.querySelectorAll('.destination-item');
                
                destItems.forEach(function(item) {
                    // Remove existing listeners
                    item.removeEventListener('click', item._clickHandler);
                    
                    // Add click handler
                    item._clickHandler = function() {
                        const country = this.getAttribute('data-country');
                        const hiddenDiv = document.getElementById('gas-country-selected-destination');
                        
                        if (hiddenDiv) {
                            const currentSelection = hiddenDiv.textContent;
                            // Toggle selection
                            if (currentSelection === country) {
                                hiddenDiv.textContent = '';  // Deselect
                            } else {
                                hiddenDiv.textContent = country;  // Select
                            }
                        }
                    };
                    
                    item.addEventListener('click', item._clickHandler);
                });
            }, 100);
            
            return window.dash_clientside.no_update;
        }
        """,
        Output('gas-country-selected-destination', 'title'),
        Input('gas-country-dest-list', 'children')
    )

    # NEW: Clientside callback for chart clicks
    dash_app.clientside_callback(
        """
        function(clickData) {
            if (!clickData || !clickData.points || clickData.points.length === 0) {
                return window.dash_clientside.no_update;
            }
            
            const point = clickData.points[0];
            let country = null;
            
            if (point.fullData && point.fullData.name) {
                country = point.fullData.name;
            } else if (point.data && point.data.name) {
                country = point.data.name;
            }
            
            if (!country) return window.dash_clientside.no_update;
            
            const hiddenDiv = document.getElementById('gas-country-selected-destination');
            if (hiddenDiv) {
                const currentSelection = hiddenDiv.textContent.trim();
                // Toggle selection
                if (currentSelection === country) {
                    hiddenDiv.textContent = '';  // Deselect
                } else {
                    hiddenDiv.textContent = country;  // Select
                }
            }
            
            return window.dash_clientside.no_update;
        }
        """,
        Output('gas-country-selected-destination', 'accessKey'), # Dummy output
        Input('gas-country-line-chart', 'clickData')
    )

    # NEW: Clientside callback to sync sidebar highlighting with selection state
    dash_app.clientside_callback(
        """
        function(selectedCountry) {
            if (selectedCountry === undefined) return window.dash_clientside.no_update;
            
            const destItems = document.querySelectorAll('.destination-item');
            destItems.forEach(function(item) {
                const country = item.getAttribute('data-country');
                if (selectedCountry === country) {
                    item.style.backgroundColor = '#e3f2fd';
                    item.style.fontWeight = 'bold';
                    item.style.color = '#1976d2';
                    item.style.borderLeft = '3px solid #1976d2';
                } else {
                    item.style.backgroundColor = 'transparent';
                    item.style.fontWeight = 'normal';
                    item.style.color = '#666';
                    item.style.borderLeft = 'none';
                }
            });
            return window.dash_clientside.no_update;
        }
        """,
        Output('gas-country-selected-destination', 'lang'), # Dummy output
        Input('gas-country-selected-destination', 'children')
    )

    # Monitor destination selection changes
    dash_app.clientside_callback(
        """
        function(n_intervals) {
            const hiddenDiv = document.getElementById('gas-country-selected-destination');
            if (!hiddenDiv) return window.dash_clientside.no_update;
            
            const currentSelection = hiddenDiv.textContent;
            
            // Store previous selection to detect changes
            if (!window._gasCountryPrevDestSelection) {
                window._gasCountryPrevDestSelection = '';
            }
            
            // If selection changed, trigger chart update
            if (window._gasCountryPrevDestSelection !== currentSelection) {
                window._gasCountryPrevDestSelection = currentSelection;
                return currentSelection;
            }
            
            return window.dash_clientside.no_update;
        }
        """,
        Output('gas-country-selected-destination', 'children'),
        Input('gas-country-legend-interval', 'n_intervals')
    )


    @dash_app.callback(
        Output('gas-country-line-chart', 'figure'),
        [Input('gas-country-start-date', 'value'),
         Input('gas-country-end-date', 'value'),
         Input('gas-country-origin-radio', 'value'),
         Input('gas-country-dest-checklist', 'value'),
         Input('gas-country-selected-destination', 'children'),
         Input('gas-country-chart-period-store', 'data')]
    )
    def update_chart(start_date, end_date, selected_origin, selected_dests, selected_destination, chart_period):
        if not selected_origin or not selected_dests:
            return go.Figure()

        try:
            # Use the european_gas_trade table which is known to work
            query_origins = [selected_origin] if selected_origin != '(All)' else ['Algeria','Azerbaijan','Libya','Norway','Russia']

            query = f"""
            SELECT
                tr.source_country AS gas_origin,
                tr.target_country,
                tr.date AS date,
                tr."flow_mcm/d" / 1000.0 AS flows_bcm
            FROM european_gas_trade tr
            WHERE tr.source_country = ANY(:origins)
              AND tr.date >= :start_date
              AND tr.date <= :end_date
            ORDER BY tr.date;
            """
            
            results = execute_query(query, {
                'start_date': start_date,
                'end_date': end_date,
                'origins': query_origins
            })
            df = pd.DataFrame(results)
            if df.empty:
                return go.Figure()

            # Convert types
            df['flows_bcm'] = pd.to_numeric(df['flows_bcm'], errors='coerce').fillna(0).astype(float)
            df['date'] = pd.to_datetime(df['date'])
            
            # Apply destination filter
            df = df[df['target_country'].isin(selected_dests)]
            
            if df.empty:
                return go.Figure()

            # Aggregation logic
            if chart_period == 'YEAR':
                df['display_date'] = df['date'].dt.to_period('Y').dt.to_timestamp()
                hover_label = "Year of Date"
                tick_format = "%Y"
                dtick = "M12"
            elif chart_period == 'QUARTER':
                df['display_date'] = df['date'].dt.to_period('Q').dt.to_timestamp()
                hover_label = "Quarter of Date"
                tick_format = "%Y-Q%q"
                dtick = "M3"
            elif chart_period == 'MONTH':
                df['display_date'] = df['date'].dt.to_period('M').dt.to_timestamp()
                hover_label = "Month of Date"
                tick_format = "%b %y"
                dtick = "M6"
            else: # DAILY
                df['display_date'] = df['date']
                hover_label = "Day of Date"
                tick_format = "%b %d, %y"
                dtick = None # Auto

            agg_df = df.groupby(['display_date', 'gas_origin', 'target_country'])['flows_bcm'].sum().reset_index()

            fig = go.Figure()
            
            for dest in selected_dests:
                dest_df = agg_df[agg_df['target_country'] == dest].sort_values('display_date')
                if not dest_df.empty:
                    # Create custom hover text
                    hover_text = []
                    for _, row in dest_df.iterrows():
                        if chart_period == 'YEAR':
                            date_str = row['display_date'].strftime('%Y')
                        elif chart_period == 'QUARTER':
                            q = (row['display_date'].month - 1) // 3 + 1
                            date_str = f"Q{q} {row['display_date'].year}"
                        elif chart_period == 'MONTH':
                            date_str = row['display_date'].strftime('%B %Y')
                        else:
                            date_str = row['display_date'].strftime('%b %d, %Y')
                            
                        hover_text.append(
                            f"Target Country: {dest}<br>" +
                            f"{hover_label}: {date_str}<br>" +
                            f"flows_bcm: {row['flows_bcm']:.3f}"
                        )
                    
                    # Determine line styling based on selection
                    is_selected = selected_destination == dest if selected_destination else True
                    
                    # If a country is selected, make it more prominent and fade others
                    if selected_destination:
                        if is_selected:
                            line_width = 1.5
                            line_opacity = 1.0
                        else:
                            line_width = 1.5
                            line_opacity = 0.15
                    else:
                        line_width = 2.5
                        line_opacity = 0.8
                        
                    line_color = COUNTRY_COLORS.get(dest, '#999')
                    
                    fig.add_trace(go.Scatter(
                        x=dest_df['display_date'],
                        y=dest_df['flows_bcm'],
                        name=dest,
                        mode='lines',
                        line=dict(width=line_width, color=line_color),
                        opacity=line_opacity,
                        text=hover_text,
                        hovertemplate="%{text}<extra></extra>",
                        hoverlabel=dict(
                            bgcolor="white",
                            bordercolor="gray",
                            font=dict(color="black", size=12)
                        )
                    ))

            fig.update_layout(
                margin=dict(l=40, r=20, t=10, b=40),
                paper_bgcolor='white',
                plot_bgcolor='white',
                hovermode='closest',
                showlegend=False,
                xaxis=dict(
                    showgrid=True, gridcolor='#f5f5f5',
                    tickfont=dict(size=10, color='#999'),
                    tickformat=tick_format, dtick=dtick,
                    fixedrange=True,
                    range=[start_date, end_date]
                ),
                yaxis=dict(
                    showgrid=True, gridcolor='#f5f5f5',
                    tickfont=dict(size=10, color='#999'),
                    zeroline=True, zerolinecolor='#f5f5f5',
                    fixedrange=True,
                    range=[0, max(agg_df['flows_bcm'].max() * 1.2 if not agg_df.empty else 1.0, 1.0)]
                ),
                font=dict(family="Lato, sans-serif")
            )
            return fig
            
        except Exception as e:
            print(f"Error updating gas flows chart: {e}")
            import traceback
            traceback.print_exc()
            return go.Figure()

    @dash_app.callback(
        Output('gas-country-table-container', 'children'),
        [Input('gas-country-start-date', 'value'),
         Input('gas-country-end-date', 'value'),
         Input('gas-country-table-period-store', 'data')]
    )
    def update_table(start_date, end_date, table_period):
        # Default all origins as requested
        selected_origins = ['Algeria', 'Azerbaijan', 'Libya', 'Norway', 'Russia']
        
        query_origins = selected_origins.copy()
        if 'Turkey' not in query_origins:
            query_origins.append('Turkey')

        # Map UI period to SQL granularity
        time_gran = {
            'YEAR': 'YEAR',
            'QUARTER': 'QUARTER',
            'MONTH': 'MONTH',
            'DAILY': 'DAY'
        }.get(table_period, 'MONTH')

        query = f"""
        SELECT
            CASE
                WHEN :time_granularity = 'DAY' THEN tr.date
                WHEN :time_granularity = 'WEEK' THEN (date_trunc('week', tr.date + interval '1 day') - interval '1 day')::date
                WHEN :time_granularity = 'MONTH' THEN date_trunc('month', tr.date)::date
                WHEN :time_granularity = 'QUARTER' THEN date_trunc('quarter', tr.date)::date
                WHEN :time_granularity = 'YEAR' THEN date_trunc('year', tr.date)::date
            END AS "Period of Date",
            'Exporter' AS "Header_Exporter",
            tr.source_country AS gas_origin,
            'Importer' AS "Header_Importer",
            tr.target_country AS target_country,
            tr.pointlabel AS "Interconnection Point",
            ROUND(SUM(tr."flow_mcm/d") / 1000.0, 6) AS flows_bcm
        FROM european_gas_trade tr
        WHERE tr.source_country = ANY(:origins)
          AND tr.date BETWEEN :start_date AND :end_date
        GROUP BY
            "Period of Date",
            tr.source_country,
            tr.target_country,
            tr.pointlabel
        ORDER BY "Period of Date" DESC;
        """

        try:
            results = execute_query(query, {
                'start_date': start_date,
                'end_date': end_date,
                'time_granularity': time_gran,
                'origins': query_origins
            })
            df = pd.DataFrame(results)
            if df.empty:
                return html.Div("No data available for the selected filters.", style={'color': '#666', 'fontSize': '12px', 'padding': '20px'})

            # Convert types
            df['flows_bcm'] = pd.to_numeric(df['flows_bcm'], errors='coerce').fillna(0)
            df['Period of Date'] = pd.to_datetime(df['Period of Date'])

            # Mapping for Azerbaijan
            aze_points = ['Kipi', 'Nea Mesimvria', 'Strandzha 2', 'Malkoclar']
            mask_aze = (df['gas_origin'] == 'Turkey') & (df['Interconnection Point'].str.contains('|'.join(aze_points), na=False, case=False))
            df.loc[mask_aze, 'gas_origin'] = 'Azerbaijan'
            
            # Filter out Turkey if it's not Azerbaijan
            df = df[df['gas_origin'] != 'Turkey']

            # Pivot with 5 levels as requested
            pivot_df = df.pivot_table(
                index='Period of Date',
                columns=['Header_Exporter', 'gas_origin', 'Header_Importer', 'target_country', 'Interconnection Point'],
                values='flows_bcm'
            ).reset_index()
            
            # Sort by date descending
            pivot_df = pivot_df.sort_values(pivot_df.columns[0], ascending=False)

            # Sort origins
            origin_order = ['Algeria', 'Azerbaijan', 'Libya', 'Norway', 'Russia']
            
            def sort_columns_key(col):
                if col[0] == 'Period of Date':
                    return (-1, "")
                # col is (Header_Exporter, gas_origin, Header_Importer, target_country, Interconnection Point)
                origin = col[1]
                order = origin_order.index(origin) if origin in origin_order else 99
                return (order, str(col[4])) # Sort by point label

            # Determine the actual column name for the date
            date_col_name = pivot_df.columns[0]
            hier_cols = [c for c in pivot_df.columns if c != date_col_name]
            hier_cols.sort(key=sort_columns_key)
            

            # Identify first/last columns of each exporter group for group-boundary borders
            border_col_ids_first = []
            border_col_ids_last  = []
            if hier_cols:
                border_col_ids_first.append("_".join(map(str, hier_cols[0])))
            for i in range(len(hier_cols) - 1):
                if hier_cols[i][1] != hier_cols[i+1][1]:
                    border_col_ids_last.append("_".join(map(str, hier_cols[i])))
                    border_col_ids_first.append("_".join(map(str, hier_cols[i+1])))
            if hier_cols:
                border_col_ids_last.append("_".join(map(str, hier_cols[-1])))

            # Formatting based on period
            def format_period_date(dt, p):
                if pd.isnull(dt): return ""
                if p == 'YEAR': return dt.strftime('%Y')
                if p == 'MONTH': return dt.strftime('%B %Y')
                if p == 'QUARTER':
                    q = (dt.month - 1) // 3 + 1
                    return f"{dt.year} Q{q}"
                return dt.strftime('%B %d, %Y')

            table_data = []
            for _, row in pivot_df.iterrows():
                d_row = {"Period of Date": format_period_date(row[date_col_name], table_period)}
                for col in hier_cols:
                    val = row[col]
                    if pd.notnull(val):
                        try:
                            d_row["_".join(map(str, col))] = f"{float(val):.4f}"
                        except (ValueError, TypeError):
                            d_row["_".join(map(str, col))] = str(val)
                    else:
                        d_row["_".join(map(str, col))] = ""
                table_data.append(d_row)

            # ── Custom HTML Table ─────────────────────────────────────────
            # Same structure as gas_europe_pipeline_flows.py:
            # 5-level sticky header, group-border separators, data-leaf-start
            # / data-dash-column attributes for the column-highlight callback.

            def make_spans(hcols):
                spans = [[], [], [], [], []]
                for col in hcols:
                    _exp, origin, _imp, target, point = col
                    if spans[0] and spans[0][-1][0] == origin:
                        spans[0][-1][1] += 1
                    else:
                        spans[0].append([origin, 1])
                    if spans[1] and spans[1][-1][0] == origin:
                        spans[1][-1][1] += 1
                    else:
                        spans[1].append([origin, 1])
                    if spans[2] and spans[2][-1][0] == (origin, target):
                        spans[2][-1][1] += 1
                    else:
                        spans[2].append([(origin, target), 1])
                    if spans[3] and spans[3][-1][0] == (origin, target):
                        spans[3][-1][1] += 1
                    else:
                        spans[3].append([(origin, target), 1])
                    spans[4].append([(origin, target, point), 1])
                return spans

            spans = make_spans(hier_cols)
            border_first_set = set(border_col_ids_first)

            ROW_H = [28, 32, 28, 28, 28]
            def sticky_top(row_idx): return sum(ROW_H[:row_idx])

            EI_DARK_BLUE = '#1b365d'
            BASE_TH = {
                'fontFamily': 'Inter, sans-serif',
                'border': '1px solid #dee2e6',
                'padding': '6px 8px',
                'whiteSpace': 'nowrap',
                'textAlign': 'center',
                'boxSizing': 'border-box',
            }
            DATE_COL_W = '150px'
            DATA_COL_W = '100px'
            ROW_STYLES = [
                {'backgroundColor': '#e9ecef', 'color': EI_DARK_BLUE, 'fontWeight': 'bold', 'fontSize': '11px'},
                {'backgroundColor': '#f8f9fa', 'color': '#212529', 'fontSize': '13px', 'fontWeight': 'bold'},
                {'backgroundColor': '#e9ecef', 'color': EI_DARK_BLUE, 'fontWeight': 'bold', 'fontSize': '11px'},
                {'backgroundColor': 'white', 'color': EI_DARK_BLUE, 'fontWeight': 'bold', 'fontSize': '12px'},
                {'backgroundColor': 'white', 'color': '#666', 'fontSize': '11px'},
            ]

            thead_rows = []
            for row_idx in range(4):
                cells = []
                if row_idx == 0:
                    cells.append(html.Th(
                        '', rowSpan=4,
                        style={**BASE_TH, **ROW_STYLES[row_idx],
                               'position': 'sticky', 'top': f'{sticky_top(row_idx)}px',
                               'left': '0', 'zIndex': 5,
                               'minWidth': DATE_COL_W, 'width': DATE_COL_W,
                               'backgroundColor': '#e9ecef', 'borderRight': '2px solid #666'}
                    ))
                col_cursor = 0
                for label_key, cs in spans[row_idx]:
                    first_leaf_id = "_".join(map(str, hier_cols[col_cursor]))
                    is_first = first_leaf_id in border_first_set
                    display_label = label_key if isinstance(label_key, str) else label_key[1]
                    if row_idx == 0: display_label = 'Exporter'
                    if row_idx == 2: display_label = 'Importer'
                    extra_border = {'borderLeft': '2px solid #666'} if is_first else {}
                    cells.append(html.Th(
                        display_label, colSpan=cs,
                        **{'data-leaf-start': str(col_cursor), 'data-leaf-span': str(cs)},
                        style={**BASE_TH, **ROW_STYLES[row_idx],
                               'position': 'sticky', 'top': f'{sticky_top(row_idx)}px',
                               'zIndex': 3, **extra_border}
                    ))
                    col_cursor += cs
                thead_rows.append(html.Tr(cells))

            leaf_cells = [
                html.Th('Period of Date',
                        style={**BASE_TH, **ROW_STYLES[4],
                               'position': 'sticky', 'top': f'{sticky_top(4)}px',
                               'left': '0', 'zIndex': 5,
                               'minWidth': DATE_COL_W, 'width': DATE_COL_W,
                               'backgroundColor': 'white', 'borderRight': '2px solid #666',
                               'fontWeight': 'bold', 'color': EI_DARK_BLUE})
            ]
            for col in hier_cols:
                col_id = "_".join(map(str, col))
                is_first = col_id in border_first_set
                extra_border = {'borderLeft': '2px solid #666'} if is_first else {}
                leaf_cells.append(html.Th(
                    col[4], **{'data-dash-column': col_id},
                    style={**BASE_TH, **ROW_STYLES[4],
                           'position': 'sticky', 'top': f'{sticky_top(4)}px',
                           'zIndex': 3, 'minWidth': DATA_COL_W, 'width': DATA_COL_W,
                           **extra_border}
                ))
            thead_rows.append(html.Tr(leaf_cells))

            tbody_rows = []
            for row_idx_d, row in enumerate(table_data):
                is_odd = (row_idx_d % 2 == 1)
                row_bg = '#f8f9fa' if is_odd else 'white'
                td_date = html.Td(
                    row.get('Period of Date', ''),
                    **{'data-dash-column': 'Period of Date', 'data-dash-row': str(row_idx_d)},
                    style={'fontFamily': 'Inter, sans-serif', 'fontSize': '11px',
                           'padding': '6px 8px', 'border': '1px solid #dee2e6',
                           'borderRight': '2px solid #999', 'whiteSpace': 'nowrap',
                           'textAlign': 'left', 'color': '#666',
                           'position': 'sticky', 'left': '0', 'zIndex': 2,
                           'backgroundColor': row_bg,
                           'minWidth': DATE_COL_W, 'width': DATE_COL_W, 'boxSizing': 'border-box'}
                )
                data_cells = [td_date]
                for col in hier_cols:
                    col_id = "_".join(map(str, col))
                    val = row.get(col_id, '')
                    is_first = col_id in border_first_set
                    extra_border = {'borderLeft': '2px solid #666'} if is_first else {}
                    data_cells.append(html.Td(
                        val,
                        **{'data-dash-column': col_id, 'data-dash-row': str(row_idx_d)},
                        style={'fontFamily': 'Inter, sans-serif', 'fontSize': '11px',
                               'padding': '6px 8px', 'border': '1px solid #dee2e6',
                               'textAlign': 'center', 'color': '#333',
                               'backgroundColor': row_bg,
                               'minWidth': DATA_COL_W, 'width': DATA_COL_W,
                               'boxSizing': 'border-box', **extra_border}
                    ))
                tbody_rows.append(html.Tr(data_cells))

            table = html.Table(
                [html.Thead(thead_rows), html.Tbody(tbody_rows)],
                id='gas-country-data-table',
                style={'borderCollapse': 'collapse', 'width': 'max-content',
                       'minWidth': '100%', 'tableLayout': 'fixed'}
            )
            return html.Div(
                table,
                style={'overflowX': 'auto', 'overflowY': 'auto', 'height': '600px',
                       'width': '100%', 'position': 'relative', 'marginTop': '10px',
                       'border': '1px solid #dee2e6'}
            )

        except Exception as e:
            print(f"Error updating gas flows table: {e}")
            import traceback
            traceback.print_exc()
            return html.Div(f"Error loading table: {str(e)}", style={'color': 'red'})

    # Clientside callback for table highlighting (same pattern as gas_europe_pipeline_flows.py)
    dash_app.clientside_callback(
        """
        function(id) {
            const tableId = 'gas-country-data-table';
            const baseStyleId = 'gas-country-table-base-css';
            const dynamicStyleId = 'gas-country-table-dynamic-highlight-css';

            // 1. Inject Base CSS once
            if (!document.getElementById(baseStyleId)) {
                const style = document.createElement('style');
                style.id = baseStyleId;
                style.innerHTML = `
                    #${tableId} { cursor: pointer; }
                    #${tableId} td {
                        transition: background-color 0.15s ease, color 0.15s ease;
                    }
                    #${tableId}.selection-active td { color: #ccc !important; }
                    #${tableId}.selection-active td[data-dash-column="Period of Date"] {
                        color: #666 !important;
                    }
                    /* Spanning header highlight via data-gas-hl attribute */
                    #${tableId} thead th[data-gas-hl] {
                        background-color: #ddeeff !important;
                        color: #1b365d !important;
                    }
                    #${tableId} thead th[data-gas-hl="left"],
                    #${tableId} thead th[data-gas-hl="both"] {
                        border-left: 2px solid #5599dd !important;
                    }
                    #${tableId} thead th[data-gas-hl="right"],
                    #${tableId} thead th[data-gas-hl="both"] {
                        border-right: 2px solid #5599dd !important;
                    }
                `;
                document.head.appendChild(style);
            }

            function clearHighlight(tableEl) {
                tableEl.classList.remove('selection-active');
                tableEl.querySelectorAll('th[data-gas-hl]').forEach(th => th.removeAttribute('data-gas-hl'));
                const dynStyle = document.getElementById(dynamicStyleId);
                if (dynStyle) dynStyle.remove();
            }

            const setupListener = () => {
                const tableEl = document.getElementById(tableId);
                if (!tableEl) return;
                if (tableEl.dataset.highlightEnhanced === 'true') return;
                tableEl.dataset.highlightEnhanced = 'true';

                tableEl.addEventListener('click', function(e) {
                    const header     = e.target.closest('th[data-dash-column]');
                    const spanHeader = !header ? e.target.closest('th[data-leaf-start]') : null;
                    const cell       = e.target.closest('td[data-dash-column]');
                    if (!header && !spanHeader && !cell) return;

                    const thead      = tableEl.querySelector('thead');
                    const headerRows = thead ? Array.from(thead.querySelectorAll('tr')) : [];
                    const lastHRow   = headerRows.length > 0 ? headerRows[headerRows.length - 1] : null;
                    const leafThs    = lastHRow ? Array.from(lastHRow.querySelectorAll('th[data-dash-column]')) : [];
                    const leafIds    = leafThs.map(th => th.getAttribute('data-dash-column'));

                    let columnId     = null;
                    let rowIndex     = cell ? cell.getAttribute('data-dash-row') : null;
                    let targetColIds = [];

                    if (header) {
                        columnId = header.getAttribute('data-dash-column');
                        if (columnId === 'Period of Date') return;
                        targetColIds = [columnId];
                    } else if (spanHeader) {
                        const ls  = parseInt(spanHeader.getAttribute('data-leaf-start') || '0');
                        const lsp = parseInt(spanHeader.getAttribute('data-leaf-span') || '1');
                        targetColIds = leafIds.slice(ls, ls + lsp);
                        if (targetColIds.length === 0) return;
                        columnId = 'span_' + ls;
                    } else if (cell) {
                        columnId = cell.getAttribute('data-dash-column');
                        if (columnId === 'Period of Date' && !rowIndex) return;
                        targetColIds = [columnId];
                    }

                    const isHeader  = !!(header || spanHeader);
                    const clickedTh = header || spanHeader;
                    const hRow      = isHeader && clickedTh ? clickedTh.closest('tr') : null;
                    const hIdx      = hRow ? headerRows.indexOf(hRow) : -1;
                    const selKey    = isHeader
                        ? (targetColIds.join(',') + '_h' + hIdx)
                        : (columnId + '_' + rowIndex);

                    if (tableEl.dataset.lastSelection === selKey) {
                        tableEl.dataset.lastSelection = '';
                        clearHighlight(tableEl);
                        return;
                    }
                    tableEl.dataset.lastSelection = selKey;
                    clearHighlight(tableEl);
                    tableEl.classList.add('selection-active');

                    const HIGHLIGHT_BG  = '#ddeeff';
                    const HIGHLIGHT_COL = '#1b365d';
                    const BORDER_COLOR  = '#5599dd';
                    const BORDER_W      = '2px';

                    const tStartIdx = leafIds.indexOf(targetColIds[0]);
                    const tEndIdx   = leafIds.indexOf(targetColIds[targetColIds.length - 1]);

                    let dynCSS = '';

                    // A. Body (td) cells
                    targetColIds.forEach((cid, idx) => {
                        let border = '';
                        if (idx === 0)                         border += `border-left:${BORDER_W} solid ${BORDER_COLOR}!important;`;
                        if (idx === targetColIds.length - 1)   border += `border-right:${BORDER_W} solid ${BORDER_COLOR}!important;`;
                        dynCSS += `
                            #${tableId}.selection-active td[data-dash-column="${cid}"] {
                                background-color:${HIGHLIGHT_BG}!important;
                                color:${HIGHLIGHT_COL}!important;
                                font-weight:600!important;
                                ${border}
                            }
                        `;
                    });

                    // B. Leaf header row (row 4) via dynamic CSS
                    targetColIds.forEach((cid, idx) => {
                        let border = '';
                        if (idx === 0)                         border += `border-left:${BORDER_W} solid ${BORDER_COLOR}!important;`;
                        if (idx === targetColIds.length - 1)   border += `border-right:${BORDER_W} solid ${BORDER_COLOR}!important;`;
                        dynCSS += `
                            #${tableId} thead th[data-dash-column="${cid}"] {
                                background-color:${HIGHLIGHT_BG}!important;
                                color:${HIGHLIGHT_COL}!important;
                                ${border}
                            }
                        `;
                    });

                    // C. Spanning header cells (rows 0-3) via data-gas-hl attribute
                    headerRows.forEach((hrow, hrowIdx) => {
                        if (hrowIdx === headerRows.length - 1) return;
                        Array.from(hrow.querySelectorAll('th')).forEach(th => {
                            const ls  = parseInt(th.getAttribute('data-leaf-start') || '-1');
                            const lsp = parseInt(th.getAttribute('data-leaf-span')  || '1');
                            if (ls < 0) return;
                            const le = ls + lsp - 1;
                            if (Math.max(ls, tStartIdx) > Math.min(le, tEndIdx)) return;
                            const coversFirst = (tStartIdx >= ls && tStartIdx <= le);
                            const coversLast  = (tEndIdx   >= ls && tEndIdx   <= le);
                            let hlVal;
                            if (coversFirst && coversLast) hlVal = 'both';
                            else if (coversFirst)          hlVal = 'left';
                            else if (coversLast)           hlVal = 'right';
                            else                           hlVal = 'mid';
                            th.setAttribute('data-gas-hl', hlVal);
                        });
                    });

                    // D. Row + active-cell (body cell clicks only)
                    if (rowIndex !== null) {
                        dynCSS += `
                            #${tableId}.selection-active tr:has(td[data-dash-row="${rowIndex}"]) td {
                                background-color:${HIGHLIGHT_BG}!important;
                                color:${HIGHLIGHT_COL}!important;
                                font-weight:600!important;
                            }
                            #${tableId}.selection-active td[data-dash-column="${columnId}"][data-dash-row="${rowIndex}"] {
                                outline:2px solid #fe5000!important;
                                outline-offset:-2px;
                                position:relative;
                                z-index:10!important;
                            }
                            #${tableId}.selection-active td[data-dash-column="Period of Date"][data-dash-row="${rowIndex}"] {
                                background-color:#b3d9ff!important;
                                color:${HIGHLIGHT_COL}!important;
                                font-weight:bold!important;
                            }
                        `;
                    }

                    let dynStyle = document.getElementById(dynamicStyleId);
                    if (!dynStyle) {
                        dynStyle = document.createElement('style');
                        dynStyle.id = dynamicStyleId;
                        document.head.appendChild(dynStyle);
                    }
                    dynStyle.innerHTML = dynCSS;
                });
            };

            setupListener();
            if (!window._gasFlowsTableInterval_country) {
                window._gasFlowsTableInterval_country = setInterval(setupListener, 1000);
            }
            return null;
        }
        """,
        Output('gas-country-table-enhancer-anchor', 'children'),
        Input('gas-country-table-enhancer-anchor', 'id')
    )

    # CSV Export Callbacks
    @dash_app.callback(
        Output("download-gas-country-chart-csv", "data"),
        Input("export-gas-country-chart-btn", "n_clicks"),
        [State('gas-country-start-date', 'value'),
         State('gas-country-end-date', 'value'),
         State('gas-country-origin-radio', 'value'),
         State('gas-country-dest-checklist', 'value')],
        prevent_initial_call=True,
    )
    def export_chart_data(n_clicks, start_date, end_date, selected_origin, selected_dests):
        """Export chart data to CSV."""
        if n_clicks == 0:
            return no_update
            
        try:
            if not selected_origin or not selected_dests:
                return no_update
                
            # Use european_gas_trade table
            query_origins = [selected_origin] if selected_origin != '(All)' else ['Algeria','Azerbaijan','Libya','Norway','Russia']

            query = f"""
            SELECT
                tr.source_country AS gas_origin,
                tr.target_country,
                tr.date AS date,
                tr."flow_mcm/d" / 1000.0 AS flows_bcm
            FROM european_gas_trade tr
            WHERE tr.source_country = ANY(:origins)
              AND tr.date >= :start_date
              AND tr.date <= :end_date
            ORDER BY tr.date;
            """
            
            results = execute_query(query, {
                'start_date': start_date,
                'end_date': end_date,
                'origins': query_origins
            })
            df = pd.DataFrame(results)
            
            if df.empty:
                return no_update

            # Apply same transformations as chart
            df['flows_bcm'] = pd.to_numeric(df['flows_bcm'], errors='coerce').fillna(0).astype(float)
            df['date'] = pd.to_datetime(df['date'])
            
            # Apply filters
            df = df[df['target_country'].isin(selected_dests)]
            
            # Aggregate by date, origin, and target country for monthly data
            df = df.groupby(['date', 'gas_origin', 'target_country'])['flows_bcm'].sum().reset_index()
            
            # Monthly aggregation
            df['month_date'] = df['date'].dt.to_period('M').dt.to_timestamp()
            monthly_df = df.groupby(['month_date', 'gas_origin', 'target_country'])['flows_bcm'].sum().reset_index()
            
            # Prepare export data to match CSV format
            export_df = monthly_df.sort_values(['month_date', 'target_country']).copy()
            export_df['Month of Date'] = export_df['month_date'].dt.strftime('%B %Y')  # Format like "January 2021"
            export_df = export_df[['Month of Date', 'target_country', 'flows_bcm']].rename(columns={
                'target_country': 'Target Country',
                'flows_bcm': 'flows_bcm'
            })
            
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gas_pipeline_flows_country_chart_{timestamp}.csv"
            return dcc.send_data_frame(export_df.to_csv, filename, index=False)
            
        except Exception as e:
            print(f"Error exporting chart data: {e}")
            return no_update

    @dash_app.callback(
        Output("download-gas-country-table-csv", "data"),
        Input("export-gas-country-table-btn", "n_clicks"),
        [State('gas-country-start-date', 'value'),
         State('gas-country-end-date', 'value'),
         State('gas-country-table-period-store', 'data')],
        prevent_initial_call=True,
    )
    def export_table_data(n_clicks, start_date, end_date, period):
        """Export table data to CSV."""
        if n_clicks == 0:
            return no_update
            
        try:
            # Default all origins as requested
            selected_origins = ['Algeria', 'Azerbaijan', 'Libya', 'Norway', 'Russia']
            
            query_origins = selected_origins.copy()
            if 'Turkey' not in query_origins:
                query_origins.append('Turkey')

            # Map UI period to SQL granularity
            time_gran = {
                'YEAR': 'YEAR',
                'QUARTER': 'QUARTER',
                'MONTH': 'MONTH',
                'DAILY': 'DAY'
            }.get(period, 'MONTH')

            query = f"""
            SELECT
                CASE
                    WHEN :time_granularity = 'DAY' THEN tr.date
                    WHEN :time_granularity = 'WEEK' THEN (date_trunc('week', tr.date + interval '1 day') - interval '1 day')::date
                    WHEN :time_granularity = 'MONTH' THEN date_trunc('month', tr.date)::date
                    WHEN :time_granularity = 'QUARTER' THEN date_trunc('quarter', tr.date)::date
                    WHEN :time_granularity = 'YEAR' THEN date_trunc('year', tr.date)::date
                END AS "Period of Date",
                tr.source_country AS gas_origin,
                tr.target_country AS target_country,
                tr.pointlabel AS "Interconnection Point",
                ROUND(SUM(tr."flow_mcm/d") / 1000.0, 6) AS flows_bcm
            FROM european_gas_trade tr
            WHERE tr.source_country = ANY(:origins)
              AND tr.date BETWEEN :start_date AND :end_date
            GROUP BY
                "Period of Date",
                tr.source_country,
                tr.target_country,
                tr.pointlabel
            ORDER BY "Period of Date" DESC;
            """

            results = execute_query(query, {
                'start_date': start_date,
                'end_date': end_date,
                'time_granularity': time_gran,
                'origins': query_origins
            })
            df = pd.DataFrame(results)
            
            if df.empty:
                return no_update

            # Convert types
            df['flows_bcm'] = pd.to_numeric(df['flows_bcm'], errors='coerce').fillna(0)
            df['Period of Date'] = pd.to_datetime(df['Period of Date'])

            # Azerbaijan mapping
            aze_points = ['Kipi', 'Nea Mesimvria', 'Strandzha 2', 'Malkoclar']
            mask_aze = (df['gas_origin'] == 'Turkey') & (df['Interconnection Point'].str.contains('|'.join(aze_points), na=False, case=False))
            df.loc[mask_aze, 'gas_origin'] = 'Azerbaijan'
            
            # Filter out Turkey if it's not Azerbaijan
            df = df[df['gas_origin'] != 'Turkey']

            # Aggregate
            df = df.groupby(['Period of Date', 'gas_origin', 'target_country', 'Interconnection Point'])['flows_bcm'].sum().reset_index()

            # Prepare export data
            export_df = df.sort_values('Period of Date', ascending=False).copy()
            
            def format_period_date(dt, p):
                if pd.isnull(dt): return ""
                if p == 'YEAR': return dt.strftime('%Y')
                if p == 'MONTH': return dt.strftime('%B %Y')
                if p == 'QUARTER': 
                    q = (dt.month - 1) // 3 + 1
                    return f"{dt.year} Q{q}"
                return dt.strftime('%Y-%m-%d')

            export_df['Period of Date'] = export_df['Period of Date'].apply(lambda x: format_period_date(x, period))
            export_df = export_df.rename(columns={
                'Period of Date': 'Date/Period',
                'gas_origin': 'Gas Origin',
                'target_country': 'Target Country',
                'Interconnection Point': 'Interconnection Point',
                'flows_bcm': 'Flows (BCM)'
            })
            
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gas_pipeline_flows_country_table_{period}_{timestamp}.csv"
            return dcc.send_data_frame(export_df.to_csv, filename, index=False)
            
        except Exception as e:
            print(f"Error exporting table data: {e}")
            return no_update