import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, dash_table, State, ALL, ctx, no_update, callback_context
import os
from datetime import datetime, timedelta
import time

# Cache configuration
_cached_data = None
_cache_timestamp = None
CACHE_DURATION = 300  # 5 minutes cache

# Button Styles for Granularity Toggles
GRAN_BTN_CONTAINER_STYLE = {
    'display': 'flex',
    'alignItems': 'center',
    'marginRight': '20px'
}

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

def load_data():
    """Load and preprocess data from database query with caching"""
    global _cached_data, _cache_timestamp
    
    # Check if we have valid cached data
    current_time = time.time()
    if (_cached_data is not None and 
        _cache_timestamp is not None and 
        (current_time - _cache_timestamp) < CACHE_DURATION):
        print("Using cached data")
        return _cached_data
    
    try:
        # Import database query function
        from core.data_helpers import execute_query
        
        # Chart data query
        chart_query = """
        SELECT 
            TO_CHAR(make_date(EXTRACT(YEAR FROM date)::int,EXTRACT(MONTH FROM date)::int,1),'FMMonth YYYY') AS "Month of Date",
            flow_type,
            target_country,
            pointlabel AS "Point",
            ROUND(SUM("flow_mcm/d") / 1000.0, 3) AS flows_bcm
        FROM european_gas_trade
        WHERE flow_type = 'LNG'
        GROUP BY 
            EXTRACT(YEAR FROM date),
            EXTRACT(MONTH FROM date),
            flow_type,
            pointlabel,
            source_country,
            target_country
        ORDER BY 
            EXTRACT(YEAR FROM date),
            EXTRACT(MONTH FROM date),
            pointlabel
        """
        
        print("Executing database query...")
        
        # Execute query using centralized data helpers
        rows = execute_query(chart_query)
        if not rows:
            print("WARNING: Database query returned no data")
            return pd.DataFrame(), pd.DataFrame()
        
        chart_df = pd.DataFrame(rows)
        
        print(f"Query returned {len(chart_df)} rows")
        
        # For table data, use the same query but with different grouping if needed
        table_df = chart_df.copy()
        
        if chart_df.empty:
            print("WARNING: Database query returned no data")
            return pd.DataFrame(), pd.DataFrame()
        
        # Add proper date column for filtering
        chart_df['Date'] = pd.to_datetime(chart_df['Month of Date'], format='%B %Y', errors='coerce')
        table_df['Date'] = pd.to_datetime(table_df['Month of Date'], format='%B %Y', errors='coerce')
        
        # Clean up any failed parses
        chart_df = chart_df.dropna(subset=['Date'])
        table_df = table_df.dropna(subset=['Date'])
        
        # Rename target_country to match existing code expectations
        chart_df = chart_df.rename(columns={'target_country': 'Target Country'})
        table_df = table_df.rename(columns={'target_country': 'Target Country'})
        
        print(f"SUCCESS: Processed {len(chart_df)} chart rows and {len(table_df)} table rows from database")
        
        # Cache the results
        _cached_data = (chart_df, table_df)
        _cache_timestamp = current_time
        
        return chart_df, table_df
        
    except Exception as e:
        print(f"CRITICAL: Database query failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Return cached data if available, even if expired
        if _cached_data is not None:
            print("Returning expired cached data due to database error")
            return _cached_data
        
        return pd.DataFrame(), pd.DataFrame()

# Custom Color Palette - Exact names from database
TERMINAL_COLORS = {
    'Alexandroupolis': '#1b365d',
    'Baltic Energy Gate': '#7a8ec9',
    'Barcelona': '#007ba7',
    'Bilbao': '#595959',
    'Brunsbuettel Hafen FSRU': '#ff5000',
    'Cartagena': '#2c3e50',
    'Croatia LNG': '#a0522d',
    'Dunkerque LNG / PEG North': '#1b365d',
    'Eems Energy Terminal': '#7a8ec9',
    'Fos (Tonkin/Cavaou)': '#ff5000',
    'Gate Terminal (I)': '#c5d9a1',
    'Hamina LNG': '#007ba7',
    'Huelva': '#5489b4',
    'Inkoo LNG (FI)': '#2c3e50',
    'Isle of Grain': '#5489b4',
    'Klaipeda (LNG)': '#a6a6a6',
    'Le Havre FSRU': '#bf5700',
    'LNG Cavarzere': '#595959',
    'LNG Livorno': '#1b365d',
    'LNG Panigaglia': '#7a8ec9',
    'LNG Piombino': '#ff5000',
    'Milford Haven': '#c5d9a1',
    'Montoir de Bretagne': '#007ba7',
    'Reganosa': '#a6a6a6',
    'Revithoussa': '#5489b4',
    'Sagunto': '#bf5700',
    'Sines': '#a6a6a6',
    'Swinoujscie': '#bf5700',
    'Wilhelmshaven LNG': '#a0522d',
    'Zeebrugge LNG': '#595959',
}

def create_layout():
    """Create the European LNG Imports layout"""
    chart_df, table_df = load_data()
    
    if chart_df.empty or table_df.empty:
        return html.Div([
            html.H1("LNG Imports By Terminal - Database Connection Issue", style={
                'color': '#fe5000', 'fontSize': '20px', 'fontWeight': 'bold',
                'fontFamily': 'Arial, sans-serif', 'margin': '25px 0 15px 40px'
            }),
            html.Div("Data could not be loaded from database. Check server logs for details.", 
                    style={'padding': '50px', 'color': 'red', 'fontSize': '16px'})
        ])

    countries = sorted(table_df['Target Country'].unique()) if 'Target Country' in table_df.columns else []
    terminals = sorted(chart_df['Point'].unique()) if 'Point' in chart_df.columns else []
    
    min_date_val = chart_df['Date'].min() if not chart_df.empty and 'Date' in chart_df.columns else pd.Timestamp('2021-01-01')
    max_date_val = chart_df['Date'].max() if not chart_df.empty and 'Date' in chart_df.columns else pd.Timestamp('2026-02-05')
    
    # Calculate default date range: most recent 5 years
    default_end_date = max_date_val
    default_start_date = max_date_val - pd.DateOffset(years=5)
    
    # Format dates for display (YYYY-MM-DD)
    default_start_date_str = default_start_date.strftime('%Y-%m-%d')
    default_end_date_str = default_end_date.strftime('%Y-%m-%d')

    return html.Div(id='lng-dashboard-container', children=[
        # Store components for tracking previous filter values and granularity
        dcc.Store(id='country-filter-previous', data={'all_selected': True}),  # Initialize with all selected
        dcc.Store(id='terminal-filter-previous', data={'all_selected': True}),  # Initialize with all selected
        dcc.Store(id='selected-terminals-store', data=[]),
        dcc.Store(id='lng-chart-granularity-store', data='month'),  # Chart granularity
        dcc.Store(id='lng-table-granularity-store', data='month'),  # Table granularity
        dcc.Store(id='lng-chart-selection', data=None),  # For chart click selection
        
        # Download components
        dcc.Download(id="download-lng-chart-csv"),
        dcc.Download(id="download-lng-table-csv"),
        
        # Store for table highlight state
        dcc.Store(id='lng-table-highlight-state'),
        
        # Store for dropdown visibility states
        dcc.Store(id='lng-country-dropdown-open', data=False),
        dcc.Store(id='lng-terminal-dropdown-open', data=False),
        
        html.Div([
            # Side Filter Panel (on the right)
            html.Div([
                
                html.Div([
                    html.Div([
                        html.Label("Country", style={'fontSize': '11px', 'color': '#666', 'marginBottom': '4px', 'display': 'block', 'fontFamily': 'Arial, sans-serif'}),
                        html.Div([
                            html.Div([
                                html.Span("(All)", id='lng-country-label'),
                                html.Span("▼", style={'fontSize': '8px', 'color': '#666'})
                            ], id='lng-country-dropdown', style={
                                'border': '1px solid #ccc',
                                'borderRadius': '3px',
                                'padding': '5px 10px',
                                'fontSize': '12px',
                                'fontFamily': 'Arial, sans-serif',
                                'backgroundColor': 'white',
                                'marginBottom': '5px',
                                'display': 'flex',
                                'justifyContent': 'space-between',
                                'alignItems': 'center',
                                'cursor': 'pointer'
                            }),
                        ], id='lng-country-trigger', n_clicks=0, style={'cursor': 'pointer'}),
                        html.Div([
                            dcc.Checklist(
                                id='country-checklist',
                                options=[{'label': '(All)', 'value': '(All)'}] + [{'label': c, 'value': c} for c in countries],
                                value=['(All)'] + countries,
                                labelStyle={
                                    'display': 'block',
                                    'fontSize': '11px',
                                    'color': '#333',
                                    'fontFamily': 'Arial, sans-serif',
                                    'marginBottom': '3px'
                                }
                            )
                        ], id='lng-country-container', style={
                            'display': 'none', 
                            'padding': '5px 10px', 
                            'marginTop': '-5px',
                            'border': '1px solid #ccc',
                            'borderRadius': '3px',
                            'maxHeight': '200px',
                            'overflowY': 'auto',
                            'backgroundColor': '#fff',
                            'position': 'absolute',
                            'zIndex': '1000',
                            'width': '100%',
                            'borderTop': '0px'
                        })
                    ], style={'flex': '1', 'position': 'relative', 'marginBottom': '15px'}),
                    
                    html.Div([
                        html.Label("Regasification Terminal", style={'fontSize': '11px', 'color': '#666', 'marginBottom': '4px', 'display': 'block', 'fontFamily': 'Arial, sans-serif'}),
                        html.Div([
                            html.Div([
                                html.Span("(All)", id='lng-terminal-label'),
                                html.Span("▼", style={'fontSize': '8px', 'color': '#666'})
                            ], id='lng-terminal-dropdown', style={
                                'border': '1px solid #ccc',
                                'borderRadius': '3px',
                                'padding': '5px 10px',
                                'fontSize': '12px',
                                'fontFamily': 'Arial, sans-serif',
                                'backgroundColor': 'white',
                                'marginBottom': '5px',
                                'display': 'flex',
                                'justifyContent': 'space-between',
                                'alignItems': 'center',
                                'cursor': 'pointer'
                            }),
                        ], id='lng-terminal-trigger', n_clicks=0, style={'cursor': 'pointer'}),
                        html.Div([
                            dcc.Checklist(
                                id='terminal-checklist',
                                options=[{'label': '(All)', 'value': '(All)'}] + [{'label': t, 'value': t} for t in terminals],
                                value=['(All)'] + terminals,
                                labelStyle={
                                    'display': 'block',
                                    'fontSize': '11px',
                                    'color': '#333',
                                    'fontFamily': 'Arial, sans-serif',
                                    'marginBottom': '3px'
                                }
                            )
                        ], id='lng-terminal-container', style={
                            'display': 'none', 
                            'padding': '5px 10px', 
                            'marginTop': '-5px',
                            'border': '1px solid #ccc',
                            'borderRadius': '3px',
                            'maxHeight': '200px',
                            'overflowY': 'auto',
                            'backgroundColor': '#fff',
                            'position': 'absolute',
                            'zIndex': '1000',
                            'width': '100%',
                            'borderTop': '0px'
                        })
                    ], style={'flex': '1', 'position': 'relative', 'marginBottom': '15px'}),               
                    
                    
                    html.Label("Start Date", style={'fontWeight': 'normal', 'fontSize': '12px', 'color': '#333'}),
                    dcc.Input(
                        id='start-date-input',
                        type='text',
                        value=default_start_date_str,
                        placeholder='YYYY-MM-DD',
                        min='2019-01-01',  # Also set standard HTML attribute
                        max='2030-12-31',
                        style={'width': '100%', 'padding': '4px', 'fontSize': '12px', 'border': '1px solid #ccc', 'borderRadius': '4px', 'marginBottom': '5px'}
                    ),
                    html.Label("End Date", style={'fontWeight': 'normal', 'fontSize': '12px', 'color': '#333'}),
                    dcc.Input(
                        id='end-date-input',
                        type='text',
                        value=default_end_date_str,
                        placeholder='YYYY-MM-DD',
                        min='2019-01-01',
                        max='2030-12-31',
                        style={'width': '100%', 'padding': '4px', 'fontSize': '12px', 'border': '1px solid #ccc', 'borderRadius': '4px', 'marginBottom': '10px'}
                    ),
                    
                    html.Label("Point", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '13px', 'marginBottom': '10px'}),
                    html.Div(
                        id='point-legend-container',
                        children=[],  # Will be populated by callback
                        style={'overflowY': 'auto', 'marginBottom': '15px'}
                    ),
                
                    # Hidden store to track selected terminals
                    dcc.Store(id='selected-terminals-store', data=[]),
                ], style={'padding': '20px', 'backgroundColor': '#fcfcfc', 'borderLeft': '1px solid #eee', 'minHeight': '500px'})
            ], style={'width': '230px', 'float': 'right'}),

            # Main content area
            html.Div([
                # Header section moved here
                html.Div([
                    html.Div([
                        html.H1(id="lng-imports-title", children="LNG Imports By Terminal - All - Billion Cubic Meters", style={
                            'color': '#fe5000', 'fontSize': '20px', 'fontWeight': 'bold',
                            'fontFamily': 'Arial, sans-serif', 'margin': '25px 0 15px 0'
                        }),
                    ], style={'flex': '1'}),
                    html.Div([
                        html.Button(
                            "Export to CSV",
                            id="export-lng-chart-btn",
                            n_clicks=0,
                            style={
                                "backgroundColor": "white",
                                "color": "#2c3e50",
                                "border": "1px solid #dee2e6",
                                "padding": "6px 12px",
                                "borderRadius": "4px",
                                "cursor": "pointer",
                                "fontSize": "12px",
                                "fontWeight": "normal",
                                "marginRight": "10px",
                            },
                        )
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'padding': '0 20px', 'marginBottom': '10px'}),
                
                # Chart Granularity Buttons
                html.Div([
                    html.Div([
                        html.Span("Year of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                        html.Button('+', id='lng-chart-toggle-year-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                    ], style=GRAN_BTN_CONTAINER_STYLE),
                    html.Div([
                        html.Span("Quarter of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                        html.Button('+', id='lng-chart-toggle-quarter-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                    ], style=GRAN_BTN_CONTAINER_STYLE),
                    html.Div([
                        html.Span("Month of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                        html.Button('-', id='lng-chart-toggle-month-btn', n_clicks=0, style=GRAN_BTN_ACTIVE)
                    ], style=GRAN_BTN_CONTAINER_STYLE),
                    html.Div([
                        html.Span("Day of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                        html.Button('+', id='lng-chart-toggle-day-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                    ], style=GRAN_BTN_CONTAINER_STYLE),
                ], style={'display': 'flex', 'padding': '10px 20px', 'backgroundColor': '#f8f9fa'}),
                
                dcc.Loading(
                    id="loading-chart",
                    type="circle",
                    children=dcc.Graph(id='lng-imports-chart', config={'displayModeBar': False})
                ),
                
                html.Div([
                    html.Div([
                        html.H2("LNG Imports By Terminal- Billion Cubic Meters", style={
                            'color': '#fe5000', 'fontSize': '18px', 'fontWeight': 'bold',
                            'marginTop': '30px', 'marginBottom': '20px'
                        }),
                    ], style={'flex': '1'}),
                    html.Div([
                        html.Button(
                            "Export to CSV",
                            id="export-lng-table-btn",
                            n_clicks=0,
                            style={
                                "backgroundColor": "white",
                                "color": "#2c3e50",
                                "border": "1px solid #dee2e6",
                                "padding": "6px 12px",
                                "borderRadius": "4px",
                                "cursor": "pointer",
                                "fontSize": "12px",
                                "fontWeight": "normal",
                            },
                        )
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'padding': '0 20px'}),
                
                # Table Granularity Buttons
                html.Div([
                    html.Div([
                        html.Span("Year of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                        html.Button('+', id='lng-table-toggle-year-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                    ], style=GRAN_BTN_CONTAINER_STYLE),
                    html.Div([
                        html.Span("Quarter of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                        html.Button('+', id='lng-table-toggle-quarter-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                    ], style=GRAN_BTN_CONTAINER_STYLE),
                    html.Div([
                        html.Span("Month of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                        html.Button('-', id='lng-table-toggle-month-btn', n_clicks=0, style=GRAN_BTN_ACTIVE)
                    ], style=GRAN_BTN_CONTAINER_STYLE),
                    html.Div([
                        html.Span("Day of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                        html.Button('+', id='lng-table-toggle-day-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                    ], style=GRAN_BTN_CONTAINER_STYLE),
                ], style={'display': 'flex', 'padding': '10px 20px', 'backgroundColor': '#fff'}),
                
                html.Div([
                    dcc.Loading(
                        id="loading-table",
                        type="circle",
                        children=html.Div(id='lng-imports-table-container')
                    )
                ], style={'padding': '0 20px'}),
                
                # Source info
                html.P("Source: Energy Intelligence, Transmission System Operators, Entsog, Federal Agencies",
                       style={'fontSize': '10px', 'color': '#666', 'fontStyle': 'italic', 'paddingLeft': '20px', 'marginTop': '20px'})
                
            ], style={'marginRight': '240px'})
        ], style={'overflow': 'hidden'})
    ], className='tab-content', style={'backgroundColor': '#ffffff', 'minHeight': '100vh', 'fontFamily': 'Arial, sans-serif'})

def register_callbacks(dash_app, server):

    # Clientside callback to convert text inputs to date inputs (bypasses Dash validation)
    dash_app.clientside_callback(
        """
        function() {
            setTimeout(function() {
                const startInput = document.getElementById('start-date-input');
                const endInput = document.getElementById('end-date-input');
                
                if (startInput && startInput.type === 'text') {
                    startInput.type = 'date';
                    const minDate = startInput.getAttribute('data-min') || '2019-01-01';
                    const maxDate = new Date().toISOString().split('T')[0];
                    startInput.min = minDate;
                    startInput.max = maxDate;
                }
                
                if (endInput && endInput.type === 'text') {
                    endInput.type = 'date';
                    const minDate = endInput.getAttribute('data-min') || '2019-01-01';
                    const maxDate = new Date().toISOString().split('T')[0];
                    endInput.min = minDate;
                    endInput.max = maxDate;
                }
            }, 100);
            return null;
        }
        """,
        Output('lng-table-highlight-state', 'data', allow_duplicate=True),
        Input('start-date-input', 'id'),
        prevent_initial_call='initial_duplicate'
    )

    # Clientside callback to handle dropdown toggling and click-outside logic
    dash_app.clientside_callback(
        """
        function(n_country, n_terminal, n_container, style_country, style_terminal) {
            var ctx = dash_clientside.callback_context;
            if (!ctx.triggered || ctx.triggered.length === 0) {
                return [style_country, style_terminal];
            }
            
            var triggered_id = ctx.triggered[0].prop_id.split('.')[0];
            
            // Base style for open state (Container)
            var base_style = {
                'padding': '5px 10px', 
                'marginTop': '-5px',
                'border': '1px solid #ccc',
                'borderRadius': '3px',
                'maxHeight': '200px',
                'overflowY': 'auto',
                'backgroundColor': '#fff',
                'position': 'absolute',
                'zIndex': '1000',
                'width': '100%',
                'borderTop': '0px',
                'display': 'block'
            };
            
            var closed_style = Object.assign({}, base_style, {'display': 'none'});
            
            // Handle null/undefined styles
            style_country = style_country || closed_style;
            style_terminal = style_terminal || closed_style;
            
            // If container was clicked (checking for outside clicks)
            if (triggered_id === 'lng-dashboard-container') {
                var is_trigger_click = false;
                ctx.triggered.forEach(function(t) {
                    if (t.prop_id.indexOf('trigger') !== -1) {
                        is_trigger_click = true;
                    }
                });
                
                if (is_trigger_click) {
                    // Let trigger logic handle it
                } else {
                    // Check if click was inside one of our structures
                    var e = window.event;
                    if (e) {
                         var target = e.target;
                         var closest = target.closest('#lng-country-trigger, #lng-country-container, #lng-terminal-trigger, #lng-terminal-container');
                         if (closest) {
                             return [style_country, style_terminal];
                         } else {
                            // Clicked outside. Close all.
                            return [closed_style, closed_style];
                         }
                    }
                }
            }
            
            // Toggle Logic
            var new_country = (style_country && style_country.display === 'block') ? style_country : closed_style;
            var new_terminal = (style_terminal && style_terminal.display === 'block') ? style_terminal : closed_style;
            
            var clicked_country = ctx.triggered.some(t => t.prop_id.startsWith('lng-country-trigger'));
            var clicked_terminal = ctx.triggered.some(t => t.prop_id.startsWith('lng-terminal-trigger'));
            
            if (clicked_country) {
                new_country = (style_country && style_country.display === 'block') ? closed_style : base_style;
            } else if (clicked_terminal) {
                new_terminal = (style_terminal && style_terminal.display === 'block') ? closed_style : base_style;
            } else if (triggered_id === 'lng-dashboard-container') {
                 return [closed_style, closed_style];
            }
            
            return [new_country, new_terminal];
        }
        """,
        [Output('lng-country-container', 'style'),
         Output('lng-terminal-container', 'style')],
        [Input('lng-country-trigger', 'n_clicks'),
         Input('lng-terminal-trigger', 'n_clicks'),
         Input('lng-dashboard-container', 'n_clicks')],
        [State('lng-country-container', 'style'),
         State('lng-terminal-container', 'style')]
    )
    @dash_app.callback(
        Output('lng-country-label', 'children'),
        Input('country-checklist', 'value')
    )
    def update_country_label(selected_countries):
        if not selected_countries:
            return '(None)'
        if '(All)' in selected_countries:
            return '(All)'
        if len(selected_countries) == 1:
            return selected_countries[0]
        return f'({len(selected_countries)} selected)'

    # Callback to update Terminal label based on selection
    @dash_app.callback(
        Output('lng-terminal-label', 'children'),
        Input('terminal-checklist', 'value')
    )
    def update_terminal_label(selected_terminals):
        if not selected_terminals:
            return '(None)'
        if '(All)' in selected_terminals:
            return '(All)'
        if len(selected_terminals) == 1:
            return selected_terminals[0]
        return f'({len(selected_terminals)} selected)'

    # Close Country dropdown when selection changes
    @dash_app.callback(
        Output('lng-country-dropdown-open', 'data', allow_duplicate=True),
        Input('country-checklist', 'value'),
        prevent_initial_call=True
    )
    def close_country_dropdown_on_selection(selected_countries):
        return False

    # Close Terminal dropdown when selection changes
    @dash_app.callback(
        Output('lng-terminal-dropdown-open', 'data', allow_duplicate=True),
        Input('terminal-checklist', 'value'),
        prevent_initial_call=True
    )
    def close_terminal_dropdown_on_selection(selected_terminals):
        return False

    # Chart Granularity Toggle
    @dash_app.callback(
        [Output('lng-chart-granularity-store', 'data'),
         Output('lng-chart-toggle-year-btn', 'children'),
         Output('lng-chart-toggle-quarter-btn', 'children'),
         Output('lng-chart-toggle-month-btn', 'children'),
         Output('lng-chart-toggle-day-btn', 'children'),
         Output('lng-chart-toggle-year-btn', 'style'),
         Output('lng-chart-toggle-quarter-btn', 'style'),
         Output('lng-chart-toggle-month-btn', 'style'),
         Output('lng-chart-toggle-day-btn', 'style')],
        [Input('lng-chart-toggle-year-btn', 'n_clicks'),
         Input('lng-chart-toggle-quarter-btn', 'n_clicks'),
         Input('lng-chart-toggle-month-btn', 'n_clicks'),
         Input('lng-chart-toggle-day-btn', 'n_clicks')],
        [State('lng-chart-granularity-store', 'data')]
    )
    def toggle_chart_granularity(y_c, q_c, m_c, d_c, current_gran):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
        btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
        new_gran = current_gran
        
        if btn_id == 'lng-chart-toggle-year-btn': new_gran = 'year'
        elif btn_id == 'lng-chart-toggle-quarter-btn': new_gran = 'quarter'
        elif btn_id == 'lng-chart-toggle-month-btn': new_gran = 'month'
        elif btn_id == 'lng-chart-toggle-day-btn': new_gran = 'day'
        
        return (
            new_gran,
            '-' if new_gran == 'year' else '+',
            '-' if new_gran == 'quarter' else '+',
            '-' if new_gran == 'month' else '+',
            '-' if new_gran == 'day' else '+',
            GRAN_BTN_ACTIVE if new_gran == 'year' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'quarter' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'month' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'day' else GRAN_BTN_INACTIVE
        )

    # Table Granularity Toggle
    @dash_app.callback(
        [Output('lng-table-granularity-store', 'data'),
         Output('lng-table-toggle-year-btn', 'children'),
         Output('lng-table-toggle-quarter-btn', 'children'),
         Output('lng-table-toggle-month-btn', 'children'),
         Output('lng-table-toggle-day-btn', 'children'),
         Output('lng-table-toggle-year-btn', 'style'),
         Output('lng-table-toggle-quarter-btn', 'style'),
         Output('lng-table-toggle-month-btn', 'style'),
         Output('lng-table-toggle-day-btn', 'style')],
        [Input('lng-table-toggle-year-btn', 'n_clicks'),
         Input('lng-table-toggle-quarter-btn', 'n_clicks'),
         Input('lng-table-toggle-month-btn', 'n_clicks'),
         Input('lng-table-toggle-day-btn', 'n_clicks')],
        [State('lng-table-granularity-store', 'data')]
    )
    def toggle_table_granularity(y_c, q_c, m_c, d_c, current_gran):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
        btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
        new_gran = current_gran
        
        if btn_id == 'lng-table-toggle-year-btn': new_gran = 'year'
        elif btn_id == 'lng-table-toggle-quarter-btn': new_gran = 'quarter'
        elif btn_id == 'lng-table-toggle-month-btn': new_gran = 'month'
        elif btn_id == 'lng-table-toggle-day-btn': new_gran = 'day'
        
        return (
            new_gran,
            '-' if new_gran == 'year' else '+',
            '-' if new_gran == 'quarter' else '+',
            '-' if new_gran == 'month' else '+',
            '-' if new_gran == 'day' else '+',
            GRAN_BTN_ACTIVE if new_gran == 'year' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'quarter' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'month' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'day' else GRAN_BTN_INACTIVE
        )

    # Handle Chart Selection (Click to highlight)
    @dash_app.callback(
        [Output('lng-chart-selection', 'data'),
         Output('lng-imports-chart', 'clickData')],
        [Input('lng-imports-chart', 'clickData'),
         Input('lng-chart-granularity-store', 'data'),
         Input('country-checklist', 'value'),
         Input('terminal-checklist', 'value')],
        State('lng-chart-selection', 'data'),
        prevent_initial_call=True
    )
    def toggle_chart_selection(click_data, gran, countries, terminals, current_sel):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update
            
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Reset on filter changes
        if trigger_id != 'lng-imports-chart':
            return None, None
            
        if not click_data:
            return no_update, no_update
            
        point = click_data['points'][0]
        if 'customdata' not in point:
            return no_update, no_update
            
        cdata = point['customdata']
        # customdata format: [Terminal, Time_Label, x_pos]
        terminal = cdata[0] if len(cdata) > 0 else None
        x_pos = cdata[2] if len(cdata) > 2 else point.get('x')
        
        if not terminal or x_pos is None:
            return no_update, no_update
        
        new_sel = {
            'terminal': terminal,
            'x_pos': x_pos
        }
        
        # Toggle logic - if clicking the same bar, deselect it
        if current_sel and current_sel.get('terminal') == terminal and current_sel.get('x_pos') == x_pos:
            print(f"DEBUG: Deselecting bar - Terminal: {terminal}, x_pos: {x_pos}")
            return None, None
        
        print(f"DEBUG: Selecting bar - Terminal: {terminal}, x_pos: {x_pos}")
        return new_sel, None

    # Update title based on country selection
    @dash_app.callback(
        Output('lng-imports-title', 'children'),
        Input('country-checklist', 'value')
    )
    def update_title(selected_countries):
        """Update title based on selected countries"""
        try:
            if not selected_countries:
                # No countries selected at all
                return "LNG Imports By Terminal - None - Billion Cubic Meters"
            elif '(All)' in selected_countries:
                # All countries selected
                return "LNG Imports By Terminal - All - Billion Cubic Meters"
            
            # Filter out '(All)' if it exists
            countries = [c for c in selected_countries if c != '(All)']
            
            if len(countries) == 0:
                # Only '(All)' was selected but filtered out, or empty after filtering
                return "LNG Imports By Terminal - None - Billion Cubic Meters"
            elif len(countries) <= 3:
                # Show all country names for 3 or fewer countries
                country_list = ", ".join(sorted(countries))
                return f"LNG Imports By Terminal - {country_list} - Billion Cubic Meters"
            else:
                # Show first 3 countries and "X more" for more than 3 countries
                first_three = sorted(countries)[:3]
                remaining_count = len(countries) - 3
                country_list = ", ".join(first_three)
                return f"LNG Imports By Terminal - {country_list} and {remaining_count} more - Billion Cubic Meters"
                
        except Exception as e:
            print(f"Error updating title: {e}")
            return "LNG Imports By Terminal - All - Billion Cubic Meters"

    # Callback to handle "All" checkbox logic for countries (based on reference implementation)
    @dash_app.callback(
        [Output('country-checklist', 'value'),
         Output('country-filter-previous', 'data', allow_duplicate=True)],
        Input('country-checklist', 'value'),
        [State('country-filter-previous', 'data')],
        prevent_initial_call=True,
    )
    def handle_country_checklist(selection, country_state):
        """Toggle '(All)' checkbox to select/deselect every country"""
        chart_df, table_df = load_data()
        if table_df.empty: 
            return selection or [], {'all_selected': False}
        
        countries = sorted(table_df['Target Country'].unique()) if 'Target Country' in table_df.columns else []
        
        selection = selection or []
        state = country_state or {'all_selected': False}
        all_selected = bool(state.get('all_selected'))
        selected_set = set(selection)
        has_all = '(All)' in selected_set
        countries_set = set(countries)
        
        # User unchecked "(All)" while everything else stayed checked => clear all
        if all_selected and not has_all and selected_set == countries_set:
            return [], {'all_selected': False}
        
        # User clicked "(All)" to select everything
        if has_all and not all_selected:
            return ['(All)'] + countries, {'all_selected': True}
        
        # User manually reached full selection without "(All)" checked
        if not has_all and selected_set == countries_set:
            return ['(All)'] + countries, {'all_selected': True}
        
        # Regular multi-select - drop "(All)" if present
        cleaned = [v for v in selection if v != '(All)']
        return cleaned, {'all_selected': False}

    # Callback to handle "All" checkbox logic for terminals
    @dash_app.callback(
        [Output('terminal-checklist', 'value'),
         Output('terminal-filter-previous', 'data', allow_duplicate=True)],
        Input('terminal-checklist', 'value'),
        [State('terminal-filter-previous', 'data')],
        prevent_initial_call=True,
    )
    def handle_terminal_checklist(selection, terminal_state):
        """Toggle '(All)' checkbox to select/deselect every terminal"""
        chart_df, table_df = load_data()
        if chart_df.empty: 
            return selection or [], {'all_selected': False}
        
        terminals = sorted(chart_df['Point'].unique()) if 'Point' in chart_df.columns else []
        
        selection = selection or []
        state = terminal_state or {'all_selected': False}
        all_selected = bool(state.get('all_selected'))
        selected_set = set(selection)
        has_all = '(All)' in selected_set
        terminals_set = set(terminals)
        
        # User unchecked "(All)" while everything else stayed checked => clear all
        if all_selected and not has_all and selected_set == terminals_set:
            return [], {'all_selected': False}
        
        # User clicked "(All)" to select everything
        if has_all and not all_selected:
            return ['(All)'] + terminals, {'all_selected': True}
        
        # User manually reached full selection without "(All)" checked
        if not has_all and selected_set == terminals_set:
            return ['(All)'] + terminals, {'all_selected': True}
        
        # Regular multi-select - drop "(All)" if present
        cleaned = [v for v in selection if v != '(All)']
        return cleaned, {'all_selected': False}

    # Update terminal options based on country selection
    @dash_app.callback(
        Output('terminal-checklist', 'options'),
        Input('country-checklist', 'value')
    )
    def update_terminal_options(selected_countries):
        _, table_df = load_data()
        if table_df.empty: return [{'label': ' (All)', 'value': '(All)'}]
        
        if not selected_countries: 
            selected_countries = []
        if isinstance(selected_countries, str): 
            selected_countries = [selected_countries]
            
        # If "(All)" is selected or nothing is selected, show all terminals
        if not selected_countries or '(All)' in selected_countries:
            terminals = sorted(table_df['Point'].unique())
        else:
            # Show terminals only for selected countries
            terminals = sorted(table_df[table_df['Target Country'].isin(selected_countries)]['Point'].unique())
        
        return [{'label': ' (All)', 'value': '(All)'}] + [{'label': f' {t}', 'value': t} for t in terminals]

    @dash_app.callback(
        [Output('point-legend-container', 'children'),
         Output('selected-terminals-store', 'data')],
        [Input('country-checklist', 'value'),
         Input('terminal-checklist', 'value'),
         Input({'type': 'legend-item', 'index': ALL}, 'n_clicks')],
        [State('selected-terminals-store', 'data')]
    )
    def update_point_legend(selected_countries, selected_terminals, legend_clicks, current_selected):
        chart_df, table_df = load_data()
        if chart_df.empty: 
            return [], []
        
        # Get available terminals based on filters
        filtered_df = chart_df.copy()
        
        # Handle empty country selection
        if not selected_countries or (selected_countries and '(All)' not in selected_countries and len(selected_countries) == 0):
            # Empty country selection - no terminals available
            available_terminals = []
        elif selected_countries and '(All)' not in selected_countries:
            # Filter by specific countries
            if not table_df.empty:
                country_points = table_df[table_df['Target Country'].isin(selected_countries)]['Point'].unique()
                filtered_df = filtered_df[filtered_df['Point'].isin(country_points)]
        
        # Handle empty terminal selection
        if not selected_terminals or (selected_terminals and '(All)' not in selected_terminals and len(selected_terminals) == 0):
            # Empty terminal selection - no terminals available
            available_terminals = []
        elif selected_terminals and '(All)' not in selected_terminals:
            # Filter by specific terminals
            filtered_df = filtered_df[filtered_df['Point'].isin(selected_terminals)]
        
        # Get available terminals from filtered data (if not already set to empty)
        if 'available_terminals' not in locals():
            available_terminals = sorted(filtered_df['Point'].unique()) if not filtered_df.empty else []
        
        # Handle legend item clicks
        if ctx.triggered and ctx.triggered[0]['prop_id'] != '.':
            triggered_id = ctx.triggered[0]['prop_id']
            if 'legend-item' in triggered_id:
                # Extract terminal name from the triggered component
                import json
                prop_data = json.loads(triggered_id.split('.')[0])
                clicked_terminal = available_terminals[prop_data['index']] if prop_data['index'] < len(available_terminals) else None
                
                if clicked_terminal:
                    # If the clicked terminal is the only selected one, select all (toggle off)
                    if len(current_selected) == 1 and clicked_terminal in current_selected:
                        current_selected = available_terminals.copy()
                    else:
                        # Otherwise, select only the clicked terminal
                        current_selected = [clicked_terminal]
        
        # If no terminals selected or all are selected, keep all selected
        if not current_selected or len(current_selected) == len(available_terminals):
            current_selected = available_terminals.copy()
        
        # Create legend items
        legend_items = []
        for i, terminal in enumerate(available_terminals):
            is_selected = terminal in current_selected
            legend_items.append(
                html.Div([
                    html.Div(
                        style={
                            'width': '12px',
                            'height': '12px',
                            'backgroundColor': TERMINAL_COLORS.get(terminal, '#cccccc'),
                            'display': 'inline-block',
                            'marginRight': '8px',
                            'verticalAlign': 'middle',
                            'border': '1px solid #ddd',
                            'opacity': '1' if is_selected else '0.3'
                        }
                    ),
                    html.Span(
                        terminal,
                        style={
                            'fontSize': '11px',
                            'color': '#333' if is_selected else '#ccc',
                            'verticalAlign': 'middle',
                            'cursor': 'pointer',
                            'userSelect': 'none',
                            'fontWeight': 'normal' if is_selected else '300'
                        }
                    )
                ],
                id={'type': 'legend-item', 'index': i},
                style={
                    'display': 'flex',
                    'alignItems': 'center',
                    'marginBottom': '4px',
                    'padding': '0px 4px',
                    'borderRadius': '3px',
                    'cursor': 'pointer',
                    'backgroundColor': 'transparent'
                },
                n_clicks=0
            )
        )
        
        return legend_items, current_selected

    @dash_app.callback(
        [Output('lng-imports-chart', 'figure'),
         Output('lng-imports-table-container', 'children')],
        [Input('country-checklist', 'value'),
         Input('terminal-checklist', 'value'),
         Input('start-date-input', 'value'),
         Input('end-date-input', 'value'),
         Input('selected-terminals-store', 'data'),
         Input('lng-chart-granularity-store', 'data'),
         Input('lng-table-granularity-store', 'data'),
         Input('lng-chart-selection', 'data')]
    )
    def update_dashboard(selected_countries, selected_terminals, start_date, end_date, selected_points, chart_granularity, table_granularity, selection):
        try:
            chart_df_orig, table_df_orig = load_data()
            if chart_df_orig.empty:
                return px.bar(title="Error: Data not loaded"), html.Div("Data error")

            chart_df = chart_df_orig.copy()
            table_df = table_df_orig.copy()
            
            # --- Robust Date Filtering (applies to both chart and table) ---
            date_filter_applied = False
            start_dt = None
            end_dt = None
            
            try:
                start_dt = pd.to_datetime(start_date, errors='coerce') if start_date else None
                end_dt = pd.to_datetime(end_date, errors='coerce') if end_date else None
                
                print(f"DEBUG: Date inputs - start_date: {start_date}, end_date: {end_date}")
                print(f"DEBUG: Parsed dates - start_dt: {start_dt}, end_dt: {end_dt}")
                print(f"DEBUG: Original data shape: {chart_df.shape}")
                
                if start_dt and pd.notnull(start_dt):
                    chart_df = chart_df[chart_df['Date'] >= start_dt]
                    table_df = table_df[table_df['Date'] >= start_dt]
                    date_filter_applied = True
                    print(f"DEBUG: After start date filter: {chart_df.shape}")
                    
                if end_dt and pd.notnull(end_dt):
                    # Ensure we include the entire month of the end date
                    adjusted_end_dt = end_dt + pd.offsets.MonthEnd(0)
                    chart_df = chart_df[chart_df['Date'] <= adjusted_end_dt]
                    table_df = table_df[table_df['Date'] <= adjusted_end_dt]
                    date_filter_applied = True
                    print(f"DEBUG: After end date filter (adjusted to {adjusted_end_dt}): {chart_df.shape}")
                    
                print(f"DEBUG: Date filter applied: {date_filter_applied}")
                    
            except Exception as e:
                print(f"Date conversion error: {e}")
                import traceback
                traceback.print_exc()
                # Reset variables on error
                start_dt = None
                end_dt = None
                date_filter_applied = False

            # --- Country and Terminal Filtering (CHART ONLY) ---
            if not selected_countries: 
                selected_countries = []
            if isinstance(selected_countries, str): 
                selected_countries = [selected_countries]
            
            # Handle country filtering for CHART only
            if not selected_countries or (selected_countries and '(All)' not in selected_countries and len(selected_countries) == 0):
                # Empty selection - show no chart data
                chart_df = chart_df.iloc[0:0]  # Empty dataframe with same structure
            elif selected_countries and '(All)' not in selected_countries:
                # Specific countries selected - filter chart data only
                chart_df = chart_df[chart_df['Point'].isin(table_df_orig[table_df_orig['Target Country'].isin(selected_countries)]['Point'].unique())]
                
            if not selected_terminals: 
                selected_terminals = []
            if isinstance(selected_terminals, str): 
                selected_terminals = [selected_terminals]

            # Handle terminal filtering for CHART only
            if not selected_terminals or (selected_terminals and '(All)' not in selected_terminals and len(selected_terminals) == 0):
                # Empty selection - show no chart data
                chart_df = chart_df.iloc[0:0]  # Empty dataframe with same structure
            elif selected_terminals and '(All)' not in selected_terminals:
                # Specific terminals selected - filter chart data only
                chart_df = chart_df[chart_df['Point'].isin(selected_terminals)]

            # --- Point Legend Filter (visual emphasis for chart, data filter for table) ---
            selected_points_for_chart = selected_points if selected_points and len(selected_points) < len(chart_df['Point'].unique()) else []
            
            # Apply Point legend filter to TABLE data only (not chart data)
            if selected_points_for_chart:
                table_df = table_df[table_df['Point'].isin(selected_points_for_chart)]

            # --- Chart Rendering ---
            if chart_df.empty:
                # Check if empty due to no selections
                empty_countries = not selected_countries or (selected_countries and '(All)' not in selected_countries and len(selected_countries) == 0)
                empty_terminals = not selected_terminals or (selected_terminals and '(All)' not in selected_terminals and len(selected_terminals) == 0)
                
                if empty_countries:
                    title_text = "No countries selected"
                elif empty_terminals:
                    title_text = "No terminals selected"
                else:
                    title_text = "No data matches selected filters"
                
                fig = px.bar(title="")
                fig.update_layout(
                    xaxis={'visible': False}, 
                    yaxis={'visible': False},
                    title={'text': title_text, 'x': 0.5, 'font': {'size': 16, 'color': '#666'}},
                    margin={'t': 40, 'b': 40, 'l': 40, 'r': 40},
                    height=450,
                    annotations=[
                        dict(
                            text=title_text,
                            xref="paper", yref="paper",
                            x=0.5, y=0.5,
                            xanchor='center', yanchor='middle',
                            font=dict(size=18, color='#999'),
                            showarrow=False
                        )
                    ]
                )
            else:
                try:
                    chart_df = chart_df.sort_values('Date')
                    
                    # Apply granularity grouping
                    if chart_granularity == 'year':
                        chart_df['Time_Label'] = chart_df['Date'].dt.strftime('%Y')
                        chart_df['Time_Sort'] = chart_df['Date'].dt.year
                    elif chart_granularity == 'quarter':
                        chart_df['Time_Label'] = chart_df['Date'].dt.to_period('Q').astype(str)
                        chart_df['Time_Sort'] = chart_df['Date'].dt.to_period('Q').apply(lambda x: x.start_time)
                    elif chart_granularity == 'day':
                        chart_df['Time_Label'] = chart_df['Date'].dt.strftime('%Y-%m-%d')
                        chart_df['Time_Sort'] = chart_df['Date']
                    else:  # month (default)
                        chart_df['Time_Label'] = chart_df['Date'].dt.strftime('%b %y')
                        chart_df['Time_Sort'] = chart_df['Date']
                    
                    # Group by time and terminal
                    chart_df = chart_df.groupby(['Time_Label', 'Time_Sort', 'Point'], as_index=False)['flows_bcm'].sum()
                    chart_df = chart_df.sort_values('Time_Sort')
                    
                    # Create x-axis positions
                    unique_times = chart_df.sort_values('Time_Sort')[['Time_Label', 'Time_Sort']].drop_duplicates()
                    unique_times['x_pos'] = range(len(unique_times))
                    chart_df = chart_df.merge(unique_times[['Time_Label', 'x_pos']], on='Time_Label', how='left')
                    
                    # Create chart title with date range info if filtering is applied
                    chart_title = ""
                    if date_filter_applied:
                        date_range_text = ""
                        if start_dt and end_dt:
                            date_range_text = f" ({start_dt.strftime('%b %Y')} - {end_dt.strftime('%b %Y')})"
                        elif start_dt:
                            date_range_text = f" (from {start_dt.strftime('%b %Y')})"
                        elif end_dt:
                            date_range_text = f" (until {end_dt.strftime('%b %Y')})"
                        chart_title = f"Filtered Data{date_range_text}"
                    
                    # Build stacked bar chart with highlighting
                    fig = go.Figure()
                    
                    for terminal in sorted(chart_df['Point'].unique()):
                        terminal_df = chart_df[chart_df['Point'] == terminal]
                        
                        # Prepare customdata for tooltip: [Terminal, Time_Label, x_pos]
                        custom_data = []
                        for _, row in terminal_df.iterrows():
                            custom_data.append([row['Point'], row['Time_Label'], row['x_pos']])
                        
                        # Determine colors and borders based on selection
                        colors = []
                        line_colors = []
                        line_widths = []
                        
                        base_color = TERMINAL_COLORS.get(terminal, '#cccccc')
                        
                        # Convert hex to RGB for opacity calculations
                        r = int(base_color[1:3], 16)
                        g = int(base_color[3:5], 16)
                        b = int(base_color[5:7], 16)
                        
                        for _, row in terminal_df.iterrows():
                            x_pos = row['x_pos']
                            
                            # Determine if this bar is selected
                            is_selected = False
                            has_selection = selection is not None
                            
                            if has_selection:
                                # Check if this specific bar is selected
                                if (selection.get('terminal') == terminal and 
                                    selection.get('x_pos') == x_pos):
                                    is_selected = True
                            
                            # Apply opacity based on Point legend selection
                            is_dimmed_by_legend = selected_points_for_chart and terminal not in selected_points_for_chart
                            
                            if not has_selection:
                                # No selection - normal or dimmed by legend
                                if is_dimmed_by_legend:
                                    colors.append(f'rgba({r}, {g}, {b}, 0.3)')
                                else:
                                    colors.append(base_color)
                                line_colors.append('rgba(0,0,0,0)')
                                line_widths.append(0)
                            elif is_selected:
                                # Selected bar - highlighted with black border
                                colors.append(base_color)
                                line_colors.append('black')
                                line_widths.append(3)
                            else:
                                # Not selected - dimmed significantly
                                colors.append(f'rgba({r}, {g}, {b}, 0.15)')
                                line_colors.append('rgba(0,0,0,0)')
                                line_widths.append(0)
                        
                        fig.add_trace(go.Bar(
                            name=terminal,
                            x=terminal_df['x_pos'],
                            y=terminal_df['flows_bcm'].tolist(),
                            marker=dict(
                                color=colors,
                                line=dict(color=line_colors, width=line_widths)
                            ),
                            text=terminal_df['flows_bcm'].apply(lambda v: f"{v:.2f}" if v != 0 else ""),
                            textposition='inside',
                            insidetextanchor='middle',
                            textfont=dict(color='white', size=9),
                            customdata=custom_data,
                            hovertemplate=(
                                "<span style='color: #666'>Terminal:</span> %{customdata[0]}<br>"
                                "<span style='color: #666'>Period:</span> %{customdata[1]}<br>"
                                "<span style='color: #666'>Value:</span> %{y:,.3f} BCM<extra></extra>"
                            )
                        ))
                    
                    fig.update_layout(
                        barmode='stack',
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        title={'text': chart_title, 'x': 0.5, 'font': {'size': 14, 'color': '#666'}},
                        xaxis={
                            'tickvals': unique_times['x_pos'],
                            'ticktext': unique_times['Time_Label'],
                            'tickangle': -90 if chart_granularity in ['month', 'day'] else 0,
                            'showgrid': True, 
                            'gridcolor': '#f5f5f5', 
                            'type': 'category',
                            'title': ''
                        },
                        yaxis={
                            'showgrid': True, 
                            'gridcolor': '#f5f5f5', 
                            'title': 'Billion Cubic Meters',
                            'rangemode': 'tozero'
                        },
                        margin={'t': 40 if chart_title else 20, 'b': 100 if chart_granularity in ['month', 'day'] else 60, 'l': 60, 'r': 30},
                        height=450,
                        showlegend=False
                    )
                except Exception as chart_error:
                    print(f"Chart creation error: {chart_error}")
                    import traceback
                    traceback.print_exc()
                    fig = px.bar(title="Chart creation error")
                    fig.update_layout(
                        title={'text': f"Chart error: {str(chart_error)}", 'x': 0.5},
                        xaxis={'visible': False}, 
                        yaxis={'visible': False},
                        margin={'t': 40, 'b': 40, 'l': 40, 'r': 40},
                        height=450
                    )

            # --- Table Rendering ---
            if table_df.empty:
                # Table is only empty if Point legend filter results in no data or date filters exclude all data
                message = "No table data found for selected filters"
                table_output = html.Div(message, style={'padding': '20px', 'textAlign': 'center', 'color': '#666', 'fontSize': '14px'})
            else:
                try:
                    # Apply table granularity grouping
                    if table_granularity == 'year':
                        table_df['Time_Label'] = table_df['Date'].dt.strftime('%Y')
                        table_df['Time_Sort'] = table_df['Date'].dt.year
                    elif table_granularity == 'quarter':
                        table_df['Time_Label'] = table_df['Date'].dt.to_period('Q').astype(str)
                        table_df['Time_Sort'] = table_df['Date'].dt.to_period('Q').apply(lambda x: x.start_time)
                    elif table_granularity == 'day':
                        table_df['Time_Label'] = table_df['Date'].dt.strftime('%Y-%m-%d')
                        table_df['Time_Sort'] = table_df['Date']
                    else:  # month (default)
                        table_df['Time_Label'] = table_df['Month of Date']
                        table_df['Time_Sort'] = table_df['Date']
                    
                    # Group by time, country, and terminal
                    table_df = table_df.groupby(['Time_Label', 'Time_Sort', 'Target Country', 'Point'], as_index=False)['flows_bcm'].sum()
                    
                    # Pivot and group
                    pivot_table = table_df.pivot_table(
                        index=['Time_Label', 'Time_Sort'], 
                        columns=['Target Country', 'Point'], 
                        values='flows_bcm', 
                        aggfunc='sum'
                    ).reset_index()
                    
                    pivot_table = pivot_table.sort_values('Time_Sort', ascending=False)
                    
                    # Construct columns for dash_table
                    columns = [{"name": ["", ""], "id": "Time_Label"}]
                    
                    for country in sorted(table_df['Target Country'].unique()):
                        terminals_in_country = sorted(table_df[table_df['Target Country'] == country]['Point'].unique())
                        for term in terminals_in_country:
                            col_id = f"{country}_{term}"
                            columns.append({"name": [country, term], "id": col_id})
                    
                    data_rows = []
                    for _, row in pivot_table.iterrows():
                        time_val = row["Time_Label"]
                        # specific fix for MultiIndex columns causing Series return
                        if hasattr(time_val, 'iloc'):
                            time_val = time_val.iloc[0]
                        d = {"Time_Label": str(time_val)}
                        for col in columns[1:]:
                            c_name, t_name = col["name"]
                            try:
                                val = row.get((c_name, t_name))
                                # Values are already rounded in the query, just format for display
                                d[col["id"]] = f"{val:.3f}" if (pd.notnull(val) and val != 0) else "0.000"
                            except:
                                d[col["id"]] = "0.000"
                        data_rows.append(d)

                    table_output = dash_table.DataTable(
                        id='lng-imports-data-table',
                        columns=columns,
                        data=data_rows,
                        merge_duplicate_headers=True,
                        style_table={'overflowX': 'auto', 'border': '1px solid #ddd'},
                        style_header={
                            'backgroundColor': '#fdfdfd',
                            'fontWeight': 'bold',
                            'border': '1px solid #eee',
                            'textAlign': 'center',
                            'fontSize': '12px',
                            'padding': '5px'
                        },
                        style_cell={
                            'border': '1px solid #f0f0f0',
                            'padding': '5px 10px',
                            'textAlign': 'right',
                            'fontFamily': 'Arial, sans-serif',
                            'fontSize': '11px',
                            'minWidth': '80px'
                        },
                        style_cell_conditional=[
                            {'if': {'column_id': 'Time_Label'}, 'textAlign': 'left', 'minWidth': '130px'}
                        ],
                        style_data_conditional=[
                            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f9f9f9'}
                        ],
                        fixed_rows={'headers': True}
                    )
                except Exception as table_error:
                    print(f"Table creation error: {table_error}")
                    import traceback
                    traceback.print_exc()
                    table_output = html.Div(f"Table error: {str(table_error)}", style={'padding': '20px', 'color': 'red'})

            return fig, table_output
            
        except Exception as outer_e:
            print(f"DASHBOARD CALLBACK ERROR: {outer_e}")
            return px.bar(title="Dashboard error - check logs"), html.Div(f"Error: {outer_e}")

    # CSV Export Callbacks
    @dash_app.callback(
        Output("download-lng-chart-csv", "data"),
        Input("export-lng-chart-btn", "n_clicks"),
        [State('country-checklist', 'value'),
         State('terminal-checklist', 'value'),
         State('start-date-input', 'value'),
         State('end-date-input', 'value')],
        prevent_initial_call=True,
    )
    def export_chart_data(n_clicks, selected_countries, selected_terminals, start_date, end_date):
        """Export chart data to CSV."""
        if n_clicks == 0:
            return no_update
            
        try:
            chart_df_orig, _ = load_data()
            if chart_df_orig.empty:
                return no_update

            chart_df = chart_df_orig.copy()
            
            # Apply same filtering logic as the chart
            try:
                start_dt = pd.to_datetime(start_date, errors='coerce') if start_date else None
                end_dt = pd.to_datetime(end_date, errors='coerce') if end_date else None
                
                if start_dt and pd.notnull(start_dt):
                    chart_df = chart_df[chart_df['Date'] >= start_dt]
                if end_dt and pd.notnull(end_dt):
                    adjusted_end_dt = end_dt + pd.offsets.MonthEnd(0)
                    chart_df = chart_df[chart_df['Date'] <= adjusted_end_dt]
            except Exception as e:
                print(f"Date conversion error in export: {e}")

            # Country filtering
            if not selected_countries: 
                selected_countries = []
            if isinstance(selected_countries, str): 
                selected_countries = [selected_countries]
            
            if not selected_countries or (selected_countries and '(All)' not in selected_countries and len(selected_countries) == 0):
                chart_df = chart_df.iloc[0:0]
            elif selected_countries and '(All)' not in selected_countries:
                # Get table data for country-terminal mapping
                _, table_df_orig = load_data()
                if not table_df_orig.empty:
                    country_points = table_df_orig[table_df_orig['Target Country'].isin(selected_countries)]['Point'].unique()
                    chart_df = chart_df[chart_df['Point'].isin(country_points)]
                
            # Terminal filtering
            if not selected_terminals: 
                selected_terminals = []
            if isinstance(selected_terminals, str): 
                selected_terminals = [selected_terminals]

            if not selected_terminals or (selected_terminals and '(All)' not in selected_terminals and len(selected_terminals) == 0):
                chart_df = chart_df.iloc[0:0]
            elif selected_terminals and '(All)' not in selected_terminals:
                chart_df = chart_df[chart_df['Point'].isin(selected_terminals)]

            if chart_df.empty:
                return no_update
                
            # Prepare export data - sort by date and clean up columns
            export_df = chart_df.sort_values('Date')[['Month of Date', 'Point', 'Target Country', 'flows_bcm']].copy()
            export_df = export_df.rename(columns={
                'Month of Date': 'Month',
                'Point': 'Terminal',
                'Target Country': 'Country',
                'flows_bcm': 'Flows (BCM)'
            })
            
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"lng_imports_chart_{timestamp}.csv"
            return dcc.send_data_frame(export_df.to_csv, filename, index=False)
            
        except Exception as e:
            print(f"Error exporting chart data: {e}")
            return no_update

    @dash_app.callback(
        Output("download-lng-table-csv", "data"),
        Input("export-lng-table-btn", "n_clicks"),
        [State('country-checklist', 'value'),
         State('terminal-checklist', 'value'),
         State('start-date-input', 'value'),
         State('end-date-input', 'value'),
         State('selected-terminals-store', 'data')],
        prevent_initial_call=True,
    )
    def export_table_data(n_clicks, selected_countries, selected_terminals, start_date, end_date, selected_points):
        """Export table data to CSV."""
        if n_clicks == 0:
            return no_update
            
        try:
            chart_df_orig, table_df_orig = load_data()
            if table_df_orig.empty:
                return no_update

            table_df = table_df_orig.copy()
            
            # Apply same filtering logic as the table
            try:
                start_dt = pd.to_datetime(start_date, errors='coerce') if start_date else None
                end_dt = pd.to_datetime(end_date, errors='coerce') if end_date else None
                
                if start_dt and pd.notnull(start_dt):
                    table_df = table_df[table_df['Date'] >= start_dt]
                if end_dt and pd.notnull(end_dt):
                    adjusted_end_dt = end_dt + pd.offsets.MonthEnd(0)
                    table_df = table_df[table_df['Date'] <= adjusted_end_dt]
            except Exception as e:
                print(f"Date conversion error in table export: {e}")

            # Apply Point legend filter to table data (same as in main callback)
            selected_points_for_chart = selected_points if selected_points and len(selected_points) < len(chart_df_orig['Point'].unique()) else []
            if selected_points_for_chart:
                table_df = table_df[table_df['Point'].isin(selected_points_for_chart)]

            if table_df.empty:
                return no_update
                
            # Create pivot table same as in main callback
            pivot_table = table_df.pivot_table(
                index=['Month of Date', 'Date'], 
                columns=['Target Country', 'Point'], 
                values='flows_bcm', 
                aggfunc='sum'
            ).reset_index()
            
            pivot_table = pivot_table.sort_values('Date', ascending=False)
            
            # Flatten the multi-level columns for CSV export
            export_df = pivot_table.copy()
            
            # Rename columns to be more CSV-friendly
            new_columns = ['Month of Date']
            for col in export_df.columns[2:]:  # Skip 'Month of Date' and 'Date'
                if isinstance(col, tuple) and len(col) == 2:
                    country, terminal = col
                    new_columns.append(f"{country} - {terminal}")
                else:
                    new_columns.append(str(col))
            
            # Apply new column names
            export_df.columns = ['Month of Date', 'Date'] + new_columns[1:]
            
            # Drop the Date column (keep only Month of Date for export)
            export_df = export_df.drop(columns=['Date'])
            
            # Fill NaN values with 0 and format numbers
            for col in export_df.columns[1:]:  # Skip 'Month of Date'
                export_df[col] = export_df[col].fillna(0).round(3)
            
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"lng_imports_table_{timestamp}.csv"
            return dcc.send_data_frame(export_df.to_csv, filename, index=False)
            
        except Exception as e:
            print(f"Error exporting table data: {e}")
            return no_update

    # Clientside Callback for Table Column/Row Highlighting (Robust Version)
    dash_app.clientside_callback(
        """
        function(table_children) {
            try {
                const tableId = 'lng-imports-data-table';
                const baseStyleId = 'lng-imports-table-base-css';
                const dynamicStyleId = 'lng-imports-table-dynamic-highlight-css';
                
                // 1. Inject Base CSS if not present
                if (!document.getElementById(baseStyleId)) {
                    const style = document.createElement('style');
                    style.id = baseStyleId;
                    style.innerHTML = `
                        #${tableId} .dash-spreadsheet-container {
                            cursor: pointer;
                        }
                        #${tableId} .dash-spreadsheet-container td {
                            transition: all 0.2s ease;
                        }
                        /* Base selection state: dim normal data cells */
                        #${tableId} .dash-spreadsheet-container.selection-active td {
                            color: #ccc !important;
                            background-color: transparent !important;
                        }
                        /* Keep Time_Label column clear and undimmed */
                        #${tableId} .dash-spreadsheet-container.selection-active td[data-dash-column="Time_Label"] {
                            color: #666 !important;
                            opacity: 1 !important;
                        }
                        /* Highlight for selected column header */
                        #${tableId} .dash-spreadsheet-container th.column-header-selected {
                            background-color: #0075A8 !important;
                            color: white !important;
                        }
                    `;
                    document.head.appendChild(style);
                }
                
                // 2. Set up click listener on the table
                const setupTable = () => {
                    const tableEl = document.getElementById(tableId);
                    if (!tableEl) {
                        setTimeout(setupTable, 100);
                        return;
                    }
                    
                    const container = tableEl.querySelector('.dash-spreadsheet-container');
                    if (!container) {
                        setTimeout(setupTable, 100);
                        return;
                    }
                    
                    // Reset state if table re-rendered
                    if (table_children) {
                         // clear previous internal state if needed, but Dash might handle DOM replacement
                    }

                    if (container.dataset.highlightEnhanced === 'true') return;
                    
                    container.dataset.highlightEnhanced = 'true';
                    
                    container.addEventListener('click', function(e) {
                        const header = e.target.closest('th[data-dash-column]');
                        const cell = e.target.closest('td[data-dash-column]');
                        
                        if (!header && !cell) return;
                        
                        const columnId = (header || cell).getAttribute('data-dash-column');
                        const rowIndex = cell ? cell.getAttribute('data-dash-row') : null;
                        
                        if (columnId === 'Time_Label' && !rowIndex) return;
                        
                        const isHeader = !!header;
                        const headerRow = isHeader ? header.closest('tr') : null;
                        const thead = isHeader ? header.closest('thead') : null;
                        const headerRows = thead ? Array.from(thead.querySelectorAll('tr')) : [];
                        const headerIndex = headerRow ? headerRows.indexOf(headerRow) : -1;
                        
                        // Toggle logic
                        const selectionKey = isHeader ? (columnId + '_' + headerIndex) : (columnId + '_' + rowIndex);
                        if (container.dataset.lastSelection === selectionKey) {
                            container.dataset.lastSelection = '';
                            container.classList.remove('selection-active');
                            container.querySelectorAll('.column-header-selected').forEach(el => el.classList.remove('column-header-selected'));
                            const dynStyle = document.getElementById(dynamicStyleId);
                            if (dynStyle) dynStyle.remove();
                            return;
                        }
                        container.dataset.lastSelection = selectionKey;
                        
                        // Clear existing header highlights
                        container.querySelectorAll('.column-header-selected').forEach(el => el.classList.remove('column-header-selected'));
                        
                        // Apply highlighting
                        container.classList.add('selection-active');
                        
                        let targetColumnIds = [columnId];
                        let highlightRow = rowIndex;
                        
                        // Discovery logic for child columns if a parent header is clicked
                        if (isHeader) {
                            const colspan = parseInt(header.getAttribute('colspan') || header.colSpan || '1');
                            
                            if (colspan > 1) {
                                // Robust Discovery: Find the data row that actually contains this column
                                const parentId = header.getAttribute('data-dash-column');
                                const allTbodies = Array.from(container.querySelectorAll('tbody'));
                                
                                let targetRow = null;
                                let startIdx = -1;
                                let leafIds = [];
    
                                // Search for the row containing our start column
                                for (let tbody of allTbodies) {
                                    const row = tbody.querySelector('tr');
                                    if (!row) continue;
                                    
                                    const cells = Array.from(row.querySelectorAll('td'));
                                    const ids = cells.map(td => td.getAttribute('data-dash-column'));
                                    const idx = ids.indexOf(parentId);
                                    
                                    if (idx !== -1) {
                                        targetRow = row;
                                        startIdx = idx;
                                        leafIds = ids;
                                        break;
                                    }
                                }
                                
                                if (targetRow && startIdx !== -1) {
                                    const endIdx = Math.min(startIdx + colspan, leafIds.length);
                                    targetColumnIds = leafIds.slice(startIdx, endIdx);
                                } else {
                                    // Fallback if rows not found (e.g. empty table)
                                    targetColumnIds = [columnId];
                                }
                            } else {
                                // Single column header clicked
                                header.classList.add('column-header-selected');
                            }
                        }
                        
                        // Generate Dynamic CSS for high contrast highlights
                        let dynamicStyles = '';
                        
                        // 1. Column(s) Highlighting
                        if (targetColumnIds.length > 0) {
                            targetColumnIds.forEach(id => {
                                dynamicStyles += `
                                    #${tableId} .dash-spreadsheet-container td[data-dash-column="${id}"] {
                                        background-color: #e1f0ff !important;
                                        color: #1b365d !important;
                                        font-weight: 600 !important;
                                    }
                                `;
                            });
                        }
                        
                        // 2. Row Highlighting
                        if (highlightRow !== null) {
                            dynamicStyles += `
                                #${tableId} .dash-spreadsheet-container tr:has(td[data-dash-row="${highlightRow}"]) td {
                                    background-color: #e1f0ff !important;
                                    color: #1b365d !important;
                                    font-weight: 600 !important;
                                }
                            `;
                            // 3. Active Cell with intense border and background
                            dynamicStyles += `
                                #${tableId} .dash-spreadsheet-container td[data-dash-column="${columnId}"][data-dash-row="${highlightRow}"] {
                                    border: 2px solid #fe5000 !important;
                                    border-radius: 2px;
                                    z-index: 10 !important;
                                    position: relative;
                                }
                                /* Special highlight for the Time_Label (first) cell in the selected row */
                                #${tableId} .dash-spreadsheet-container td[data-dash-column="Time_Label"][data-dash-row="${highlightRow}"] {
                                    background-color: #b3d9ff !important;
                                    color: #1b365d !important;
                                    font-weight: bold !important;
                                }
                            `;
                        }
                        
                        let dynStyle = document.getElementById(dynamicStyleId);
                        if (!dynStyle) {
                            dynStyle = document.createElement('style');
                            dynStyle.id = dynamicStyleId;
                            document.head.appendChild(dynStyle);
                        }
                        dynStyle.innerHTML = dynamicStyles;
                    });
                };
                
                setupTable();
                // Re-apply if necessary (though Dash usually handles it via the callback input)
                return ""; 
            } catch(e) { 
                console.error('LNG table highlighting error:', e); 
                return ""; 
            }
        }
        """,
        Output('lng-table-highlight-state', 'data'),
        Input('lng-imports-table-container', 'children'),
        prevent_initial_call=False
    )