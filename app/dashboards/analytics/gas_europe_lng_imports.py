import pandas as pd
import plotly.express as px
from dash import dcc, html, Input, Output, dash_table, State, ALL, ctx
import os
from datetime import datetime, timedelta
import psycopg2
from sqlalchemy import create_engine
import time

# Database connection - using existing config infrastructure with proper connection management
_engine = None

def get_db_connection():
    """Get database connection using existing config with singleton pattern"""
    global _engine
    if _engine is None:
        try:
            # Import your existing config infrastructure
            import sys
            sys.path.append('/var/www/projects/energyintel/energy')
            from core.data_helpers import get_db_connection_string
            
            # Create engine with proper connection pooling settings
            _engine = create_engine(
                get_db_connection_string(),
                pool_size=5,           # Smaller pool size
                max_overflow=10,       # Allow some overflow
                pool_recycle=3600,     # Recycle connections after 1 hour
                pool_pre_ping=True,    # Validate connections before use
                pool_timeout=30,       # Timeout for getting connection from pool
                echo=False
            )
        except Exception as e:
            print(f"Database connection error: {e}")
            return None
    return _engine

# Database connection - using existing config infrastructure with proper connection management
_engine = None
_cached_data = None
_cache_timestamp = None
CACHE_DURATION = 300  # 5 minutes cache

def get_db_connection():
    """Get database connection using existing config with singleton pattern"""
    global _engine
    if _engine is None:
        try:
            # Import your existing config infrastructure
            import sys
            sys.path.append('/var/www/projects/energyintel/energy')
            from core.data_helpers import get_db_connection_string
            
            # Create engine with proper connection pooling settings
            _engine = create_engine(
                get_db_connection_string(),
                pool_size=5,           # Smaller pool size
                max_overflow=10,       # Allow some overflow
                pool_recycle=3600,     # Recycle connections after 1 hour
                pool_pre_ping=True,    # Validate connections before use
                pool_timeout=30,       # Timeout for getting connection from pool
                echo=False
            )
        except Exception as e:
            print(f"Database connection error: {e}")
            return None
    return _engine

def dispose_db_connection():
    """Dispose of database connection and clear cache"""
    global _engine, _cached_data, _cache_timestamp
    if _engine:
        _engine.dispose()
        _engine = None
    _cached_data = None
    _cache_timestamp = None
    print("Database connection disposed and cache cleared")

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
        engine = get_db_connection()
        if not engine:
            print("ERROR: Could not establish database connection")
            return pd.DataFrame(), pd.DataFrame()
        
        # Chart data query
        chart_query = """
        SELECT 
            TO_CHAR(make_date(EXTRACT(YEAR FROM date)::int,EXTRACT(MONTH FROM date)::int,1),'FMMonth YYYY') AS "Month of Date",
            flow_type,
            target_country,
            pointlabel AS "Point",
            ROUND(SUM("flow_mcm/d") / 1000.0, 3) AS flows_bcm
        FROM dev.european_gas_trade
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
        
        # Use connection context manager to ensure proper cleanup
        with engine.connect() as connection:
            chart_df = pd.read_sql(chart_query, connection)
        
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
    max_date_val = chart_df['Date'].max() if not chart_df.empty and 'Date' in chart_df.columns else pd.Timestamp('2026-01-01')

    return html.Div([
        # Store components for tracking previous filter values
        dcc.Store(id='country-filter-previous', data={'all_selected': True}),  # Initialize with all selected
        dcc.Store(id='terminal-filter-previous', data={'all_selected': True}),  # Initialize with all selected
        dcc.Store(id='selected-terminals-store', data=[]),
        
        # Header
        html.Div([
            html.H1("LNG Imports By Terminal - All - Billion Cubic Meters (v2)", style={
                'color': '#fe5000', 'fontSize': '20px', 'fontWeight': 'bold',
                'fontFamily': 'Arial, sans-serif', 'margin': '25px 0 15px 40px'
            }),
        ]),

        html.Div([
            # Side Filter Panel (on the right)
            html.Div([
                html.Div([
                    html.Label("Country", style={'fontWeight': 'normal', 'color': '#555', 'fontSize': '13px'}),
                    dcc.Checklist(
                        id='country-checklist',
                        options=[{'label': ' (All)', 'value': '(All)'}] + [{'label': f' {c}', 'value': c} for c in countries],
                        value=['(All)'] + countries,  # Start with all selected
                        inputStyle={'marginRight': '8px'},
                        labelStyle={'display': 'block', 'marginBottom': '4px', 'fontSize': '12px', 'cursor': 'pointer'},
                        style={
                            'maxHeight': '180px',
                            'overflowY': 'auto',
                            'padding': '6px',
                            'border': '1px solid #e0e0e0',
                            'borderRadius': '6px',
                            'background': 'white',
                        }
                    ),
                    
                    html.Label("Regasification Terminal", style={'fontWeight': 'normal', 'color': '#555', 'fontSize': '13px', 'marginTop': '15px'}),
                    dcc.Checklist(
                        id='terminal-checklist',
                        options=[{'label': ' (All)', 'value': '(All)'}] + [{'label': f' {t}', 'value': t} for t in terminals],
                        value=['(All)'] + terminals,  # Start with all selected
                        inputStyle={'marginRight': '8px'},
                        labelStyle={'display': 'block', 'marginBottom': '4px', 'fontSize': '12px', 'cursor': 'pointer'},
                        style={
                            'maxHeight': '180px',
                            'overflowY': 'auto',
                            'padding': '6px',
                            'border': '1px solid #e0e0e0',
                            'borderRadius': '6px',
                            'background': 'white',
                        }
                    ),
                    
                    html.Label("Start Date", style={'fontWeight': 'normal', 'color': '#555', 'fontSize': '13px'}),
                    dcc.Input(
                        id='start-date-input',
                        type='text',
                        value=min_date_val.strftime('%-m/%-d/%Y') if pd.notnull(min_date_val) else "1/1/2021",
                        style={'width': '90%', 'marginBottom': '15px', 'padding': '5px', 'border': '1px solid #ccc', 'fontSize': '12px'}
                    ),
                    
                    html.Label("End Date", style={'fontWeight': 'normal', 'color': '#555', 'fontSize': '13px'}),
                    dcc.Input(
                        id='end-date-input',
                        type='text',
                        value=max_date_val.strftime('%-m/%-d/%Y') if pd.notnull(max_date_val) else "1/1/2026",
                        style={'width': '90%', 'marginBottom': '15px', 'padding': '5px', 'border': '1px solid #ccc', 'fontSize': '12px'}
                    ),
                    
                    html.Label("Point", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '13px', 'marginBottom': '10px'}),
                    html.Div(
                        id='point-legend-container',
                        children=[],  # Will be populated by callback
                        style={'maxHeight': '300px', 'overflowY': 'auto', 'marginBottom': '15px'}
                    ),
                
                    # Hidden store to track selected terminals
                    dcc.Store(id='selected-terminals-store', data=[]),
                ], style={'padding': '20px', 'backgroundColor': '#fcfcfc', 'borderLeft': '1px solid #eee', 'minHeight': '500px'})
            ], style={'width': '230px', 'float': 'right'}),

            # Main content area
            html.Div([
                dcc.Loading(
                    id="loading-chart",
                    type="circle",
                    children=dcc.Graph(id='lng-imports-chart', config={'displayModeBar': False})
                ),
                
                html.Div([
                    html.H2("LNG Imports By Terminal- Billion Cubic Meters", style={
                        'color': '#fe5000', 'fontSize': '18px', 'fontWeight': 'bold',
                        'marginTop': '30px', 'marginBottom': '20px'
                    }),
                    dcc.Loading(
                        id="loading-table",
                        type="circle",
                        children=html.Div(id='lng-imports-table-container')
                    )
                ], style={'padding': '0 20px'})
            ], style={'marginRight': '240px'})
        ], style={'overflow': 'hidden'})
    ], className='tab-content', style={'backgroundColor': '#ffffff', 'minHeight': '100vh', 'fontFamily': 'Arial, sans-serif'})

def register_callbacks(dash_app, server):

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
                    'padding': '2px 4px',
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
         Input('selected-terminals-store', 'data')]
    )
    def update_dashboard(selected_countries, selected_terminals, start_date, end_date, selected_points):
        try:
            chart_df_orig, table_df_orig = load_data()
            if chart_df_orig.empty:
                return px.bar(title="Error: Data not loaded"), html.Div("Data error")

            chart_df = chart_df_orig.copy()
            table_df = table_df_orig.copy()
            
            # --- Robust Date Filtering ---
            try:
                start_dt = pd.to_datetime(start_date, errors='coerce')
                end_dt = pd.to_datetime(end_date, errors='coerce')
                
                if pd.notnull(start_dt):
                    chart_df = chart_df[chart_df['Date'] >= start_dt]
                    table_df = table_df[table_df['Date'] >= start_dt]
                if pd.notnull(end_dt):
                    # Ensure we include the entire month of the end date
                    adjusted_end_dt = end_dt + pd.offsets.MonthEnd(0)
                    chart_df = chart_df[chart_df['Date'] <= adjusted_end_dt]
                    table_df = table_df[table_df['Date'] <= adjusted_end_dt]
            except Exception as e:
                print(f"Date conversion error: {e}")

            # --- Multi-select Filtering ---
            if not selected_countries: 
                selected_countries = []
            if isinstance(selected_countries, str): 
                selected_countries = [selected_countries]
            
            # Handle country filtering
            if not selected_countries or (selected_countries and '(All)' not in selected_countries and len(selected_countries) == 0):
                # Empty selection - show no data
                chart_df = chart_df.iloc[0:0]  # Empty dataframe with same structure
                table_df = table_df.iloc[0:0]
            elif selected_countries and '(All)' not in selected_countries:
                # Specific countries selected - filter data
                chart_df = chart_df[chart_df['Point'].isin(table_df_orig[table_df_orig['Target Country'].isin(selected_countries)]['Point'].unique())]
                table_df = table_df[table_df['Target Country'].isin(selected_countries)]
                
            if not selected_terminals: 
                selected_terminals = []
            if isinstance(selected_terminals, str): 
                selected_terminals = [selected_terminals]

            # Handle terminal filtering
            if not selected_terminals or (selected_terminals and '(All)' not in selected_terminals and len(selected_terminals) == 0):
                # Empty selection - show no data
                chart_df = chart_df.iloc[0:0]  # Empty dataframe with same structure
                table_df = table_df.iloc[0:0]
            elif selected_terminals and '(All)' not in selected_terminals:
                # Specific terminals selected - filter data
                chart_df = chart_df[chart_df['Point'].isin(selected_terminals)]
                table_df = table_df[table_df['Point'].isin(selected_terminals)]

            # --- Point Legend Visual Emphasis (don't filter data) ---
            selected_points_for_chart = selected_points if selected_points and len(selected_points) < len(chart_df['Point'].unique()) else []

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
                    chart_df['Month_Label'] = chart_df['Date'].dt.strftime('%b %y')
                    
                    unique_labels = chart_df.sort_values('Date')['Month_Label'].unique()
                    
                    fig = px.bar(
                        chart_df, 
                        x='Month_Label', 
                        y='flows_bcm', 
                        color='Point',
                        color_discrete_map=TERMINAL_COLORS,
                        category_orders={'Month_Label': unique_labels},
                        title=""  # Explicitly set empty title
                    )
                    
                    # Apply opacity based on legend selection
                    if selected_points_for_chart:
                        for trace in fig.data:
                            if hasattr(trace, 'name') and trace.name not in selected_points_for_chart:
                                trace.opacity = 0.3
                            else:
                                trace.opacity = 1.0
                    
                    fig.update_layout(
                        barmode='stack',
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        title={'text': "", 'x': 0.5},  # Explicitly set title
                        xaxis={
                            'tickangle': -90, 
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
                        margin={'t': 20, 'b': 80, 'l': 60, 'r': 30},  # Increased bottom and left margins
                        height=450,
                        showlegend=False
                    )
                except Exception as chart_error:
                    print(f"Chart creation error: {chart_error}")
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
                # Check if empty due to no selections
                empty_countries = not selected_countries or (selected_countries and '(All)' not in selected_countries and len(selected_countries) == 0)
                empty_terminals = not selected_terminals or (selected_terminals and '(All)' not in selected_terminals and len(selected_terminals) == 0)
                
                if empty_countries:
                    message = "No countries selected - please select countries to view data"
                elif empty_terminals:
                    message = "No terminals selected - please select terminals to view data"
                else:
                    message = "No table data found for selected filters"
                
                table_output = html.Div(message, style={'padding': '20px', 'textAlign': 'center', 'color': '#666', 'fontSize': '14px'})
            else:
                # Pivot and group
                pivot_table = table_df.pivot_table(
                    index=['Month of Date', 'Date'], 
                    columns=['Target Country', 'Point'], 
                    values='flows_bcm', 
                    aggfunc='sum'
                ).reset_index()
                
                pivot_table = pivot_table.sort_values('Date', ascending=False)
                
                # Construct columns for dash_table
                columns = [{"name": ["", "Month of Date"], "id": "Month of Date"}]
                
                for country in sorted(table_df['Target Country'].unique()):
                    terminals_in_country = sorted(table_df[table_df['Target Country'] == country]['Point'].unique())
                    for term in terminals_in_country:
                        col_id = f"{country}_{term}"
                        columns.append({"name": [country, term], "id": col_id})
                
                data_rows = []
                for _, row in pivot_table.iterrows():
                    d = {"Month of Date": row["Month of Date"]}
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
                        {'if': {'column_id': 'Month of Date'}, 'textAlign': 'left', 'minWidth': '130px'}
                    ],
                    style_data_conditional=[
                        {'if': {'row_index': 'odd'}, 'backgroundColor': '#f9f9f9'}
                    ],
                    fixed_rows={'headers': True}
                )

            return fig, table_output
            
        except Exception as outer_e:
            print(f"DASHBOARD CALLBACK ERROR: {outer_e}")
            return px.bar(title="Dashboard error - check logs"), html.Div(f"Error: {outer_e}")