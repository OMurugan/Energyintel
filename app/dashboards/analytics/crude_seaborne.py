from dash import html, dcc, dash_table, Input, Output, callback, State
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from core.data_helpers import execute_query
import json
from app.dashboards.wcod.shared_map_utils import load_world_geojson

# Color Palette
EI_ORANGE = "#ff6600"
EI_DARK_BLUE = "#1b365d"
EI_LIGHT_BLUE = "#e8f4f8"
MAP_RUSSIA_BLUE = "#4682B4" # SteelBlue

def create_layout():
    """Create the Crude Seaborne Analytics layout"""
    return html.Div([
        # Store for time dimension visibility for Seaborne Exports
        dcc.Store(id='seaborne-time-visibility-store', data={'Quarter': False, 'Month': False, 'Day': False}),
        # Stores for table highlighting state
        dcc.Store(id='avg-exports-highlight-store', data=None),
        dcc.Store(id='yoy-change-highlight-store', data=None),
        dcc.Store(id='seaborne-bar-highlight-store', data=None),
        dcc.Store(id='seaborne-bar-granularity-store', data='MONTHLY'),

        # Header Row
        html.Div([
            html.H3(id='seaborne-title', style={
                'color': EI_ORANGE,
                'fontWeight': 'bold',
                'fontSize': '24px',
                'margin': '0',
                'fontFamily': 'Lato, sans-serif'
            })
        ], style={'marginBottom': '5px', 'padding': '0 15px'}),

        # Top Row: Map + Year Selector + Average Exports Table
        html.Div([
            # Left: Map (64%)
            html.Div([
                html.Div([
                    html.Button(
                        'Export to CSV',
                        id='btn-seaborne-map-csv',
                        n_clicks=0,
                        style={
                            'position': 'absolute', 'top': '10px', 'right': '10px', 'zIndex': '1000',
                            'backgroundColor': 'white', 'color': EI_DARK_BLUE, 'border': '1px solid #ddd',
                            'padding': '4px 8px', 'borderRadius': '4px', 'fontSize': '11px', 'cursor': 'pointer'
                        }
                    ),
                    dcc.Download(id="download-seaborne-map-csv"),
                    dcc.Loading(
                        id='loading-seaborne-map',
                        type='circle',
                        children=dcc.Graph(
                            id='seaborne-map',
                            style={'height': '380px'},
                            config={'displayModeBar': False}
                        )
                    )
                ], style={'position': 'relative'})
            ], style={'width': '64%', 'paddingRight': '10px', 'borderRight': '1px solid #eee'}),

            # Middle: Year Selector (6%)
            html.Div([
                html.Div([
                    html.Div("", style={
                        'fontSize': '12px', 
                        'fontWeight': 'bold', 
                        'color': EI_DARK_BLUE, 
                        'marginBottom': '10px',
                        'textAlign': 'center'
                    }),
                    dcc.RadioItems(
                        id='seaborne-year-selector',
                        options=[
                            {'label': '2022', 'value': 2022},
                            {'label': '2023', 'value': 2023},
                            {'label': '2024', 'value': 2024},
                            {'label': '2025', 'value': 2025},
                        ],
                        value=2025,
                        style={'fontSize': '11px', 'color': EI_DARK_BLUE},
                        labelStyle={'display': 'block', 'margin': '8px 0', 'cursor': 'pointer', 'textAlign': 'center'}
                    )
                ], style={
                    'position': 'relative',
                    'top': '0px',
                    'backgroundColor': '#f8f9fa',
                    'padding': '0px 5px',
                    'borderRadius': '4px',
                    'border': '1px solid #ddd',
                    'height': 'fit-content'
                })
            ], style={'width': '6%', 'paddingLeft': '10px', 'paddingRight': '10px'}),

            # Right: Average Exports Table (30%)
            html.Div([
                html.Div([
                    html.Div([
                        html.H4("AVERAGE SEABORNE EXPORTS BY", style={'color': EI_ORANGE, 'fontSize': '15px', 'fontWeight': 'bold', 'margin': '0'}),
                        html.H4("LOADING PORT ('000 b/d)", style={'color': EI_ORANGE, 'fontSize': '15px', 'fontWeight': 'bold', 'margin': '0'}),
                    ], style={'flex': '1'}),
                    html.Button(
                        'Export to CSV',
                        id='btn-avg-exports-csv',
                        n_clicks=0,
                        style={
                            'backgroundColor': 'white', 'color': EI_DARK_BLUE, 'border': '1px solid #ddd',
                            'padding': '2px 6px', 'borderRadius': '4px', 'fontSize': '10px', 'cursor': 'pointer'
                        }
                    ),
                    dcc.Download(id="download-avg-exports-csv")
                ], style={'display': 'flex', 'alignItems': 'flex-start', 'marginBottom': '8px'}),

                # Time Dimension Toggles
                html.Div([
                    html.Div([
                        html.Span("Quarter of Year", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                        html.Button('+', id='seaborne-toggle-quarter-btn', n_clicks=0, style={
                            'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                            'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                            'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                        })
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                    
                    html.Div([
                        html.Span("Month of Year", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                        html.Button('+', id='seaborne-toggle-month-btn', n_clicks=0, style={
                            'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                            'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                            'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                        })
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                    
                    html.Div([
                        html.Span("Day of Year", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                        html.Button('+', id='seaborne-toggle-day-btn', n_clicks=0, style={
                            'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                            'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                            'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                        })
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], style={'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#f8f9fa', 'padding': '5px 10px', 'borderRadius': '4px', 'marginBottom': '10px'}),

                dash_table.DataTable(
                    id='avg-exports-table',
                    fixed_rows={'headers': True},
                    merge_duplicate_headers=True,
                    style_table={'height': '320px', 'overflowY': 'auto'},
                    style_header={'backgroundColor': 'white', 'fontWeight': 'bold', 'borderBottom': '1px solid #ddd', 'color': EI_DARK_BLUE, 'fontSize': '11px'},
                    style_cell={'padding': '3px 6px', 'fontSize': '10px', 'fontFamily': 'Lato, sans-serif', 'border': 'none', 'textAlign': 'right', 'color': '#333'},
                    style_cell_conditional=[{'if': {'column_id': 'loading_port'}, 'textAlign': 'left', 'minWidth': '110px'}],
                    style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f9f9f9'}],
                    css=[{'selector': '.dash-spreadsheet td.highlighted', 'rule': f'background-color: {EI_LIGHT_BLUE} !important; opacity: 1 !important;'},
                         {'selector': '.highlight-mode td:not(.highlighted)', 'rule': 'opacity: 0.3; transition: opacity 0.2s;'}]
                )
            ], style={'width': '30%', 'paddingLeft': '10px'})
        ], style={
            'display': 'flex', 
            'backgroundColor': 'white', 
            'border': '1px solid #eee', 
            'padding': '10px', 
            'borderRadius': '4px',
            'marginBottom': '15px'
        }),

        # Bottom Row: Bar Chart + YOY Change Table
        html.Div([
            # Left: Bar Chart (70%)
            html.Div([
                html.Div([
                    html.Button(
                        'Export to CSV',
                        id='btn-seaborne-bar-csv',
                        n_clicks=0,
                        style={
                            'position': 'absolute', 'top': '25px', 'right': '10px', 'zIndex': '1000',
                            'backgroundColor': 'white', 'color': EI_DARK_BLUE, 'border': '1px solid #ddd',
                            'padding': '4px 8px', 'borderRadius': '4px', 'fontSize': '11px', 'cursor': 'pointer'
                        }
                    ),
                    dcc.Download(id="download-seaborne-bar-csv"),
                    
                    # Bar Chart Time Granularity Buttons
                    html.Div([
                        html.Div([
                            html.Span("Year of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                            html.Button('+', id='seaborne-bar-toggle-year-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Quarter of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                            html.Button('+', id='seaborne-bar-toggle-quarter-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Month of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                            html.Button('+', id='seaborne-bar-toggle-month-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#add8e6', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Day of Year", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                            html.Button('+', id='seaborne-bar-toggle-day-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center'})
                    ], style={
                        'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#f8f9fa', 
                        'padding': '5px 10px', 'borderRadius': '4px', 'marginBottom': '5px',
                        'position': 'absolute', 'top': '25px', 'left': '60px', 'zIndex': '1000'
                    }),

                    dcc.Loading(
                        id='loading-seaborne-bar-chart',
                        type='circle',
                        children=dcc.Graph(
                            id='seaborne-bar-chart',
                            style={'height': '320px'},
                            config={'displayModeBar': False}
                        )
                    )
                ], style={'position': 'relative'})
            ], style={'width': '70%', 'paddingRight': '15px', 'borderRight': '1px solid #eee'}),

            # Right: YOY Change Table (30%)
            html.Div([
                html.Div([
                    html.H4("YOY % CHANGE BY LOADING PORT", style={'color': EI_ORANGE, 'fontSize': '15px', 'fontWeight': 'bold', 'margin': '0', 'flex': '1'}),
                    html.Button(
                        'Export to CSV',
                        id='btn-yoy-change-csv',
                        n_clicks=0,
                        style={
                            'backgroundColor': 'white', 'color': EI_DARK_BLUE, 'border': '1px solid #ddd',
                            'padding': '2px 6px', 'borderRadius': '4px', 'fontSize': '10px', 'cursor': 'pointer'
                        }
                    ),
                    dcc.Download(id="download-yoy-change-csv")
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '8px'}),
                dash_table.DataTable(
                    id='yoy-change-table',
                    style_table={'height': '280px', 'overflowY': 'auto', 'overflowX': 'auto'},
                    fixed_rows={'headers': True},
                    style_header={'backgroundColor': 'white', 'fontWeight': 'bold', 'borderBottom': '1px solid #ddd', 'color': EI_DARK_BLUE, 'fontSize': '11px'},
                    style_cell={'padding': '3px 6px', 'fontSize': '10px', 'fontFamily': 'Lato, sans-serif', 'border': 'none', 'textAlign': 'right', 'color': '#333'},
                    style_cell_conditional=[
                        {'if': {'column_id': 'period'}, 'width': '30px', 'textAlign': 'center', 'fontWeight': 'bold'},
                        {'if': {'column_id': 'port_name'}, 'textAlign': 'left', 'minWidth': '100px'},
                        {'if': {'column_id': ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']}, 'width': '50px'}
                    ],
                    style_data_conditional=[
                        {'if': {'filter_query': '{yoy_pct} < 0'}, 'color': '#d9534f'},
                        {'if': {'row_index': 'odd'}, 'backgroundColor': '#f9f9f9'},
                        {'if': {'column_id': 'period'}, 'borderRight': '1px solid #eee'}
                    ],
                    css=[{'selector': 'td[data-dash-column="period"]', 'rule': 'writing-mode: vertical-rl; transform: rotate(180deg); white-space: nowrap; height: auto; text-align: center; vertical-align: middle;'},
                         {'selector': '.dash-spreadsheet td.highlighted', 'rule': f'background-color: {EI_LIGHT_BLUE} !important; opacity: 1 !important;'},
                         {'selector': '.highlight-mode td:not(.highlighted)', 'rule': 'opacity: 0.3; transition: opacity 0.2s;'}]
                )
            ], style={'width': '30%', 'paddingLeft': '15px'})
        ], style={
            'display': 'flex', 
            'backgroundColor': 'white', 
            'border': '1px solid #eee', 
            'padding': '10px', 
            'borderRadius': '4px',
            'marginBottom': '20px'
        }),


    ], className='tab-content', style={'padding': '15px', 'backgroundColor': 'white', 'maxWidth': '1400px', 'margin': '0 auto'})

def register_callbacks(dash_app, server):
    """Register all callbacks for Crude Seaborne Analytics"""

    @dash_app.callback(
        Output('seaborne-title', 'children'),
        Input('seaborne-year-selector', 'value')
    )
    def update_title(year):
        return f"{year} SEABORNE CRUDE EXPORTS BY MAIN LOADING PORT"

    @dash_app.callback(
        [Output('seaborne-time-visibility-store', 'data'),
         Output('seaborne-toggle-quarter-btn', 'children'),
         Output('seaborne-toggle-month-btn', 'children'),
         Output('seaborne-toggle-day-btn', 'children')],
        [Input('seaborne-toggle-quarter-btn', 'n_clicks'),
         Input('seaborne-toggle-month-btn', 'n_clicks'),
         Input('seaborne-toggle-day-btn', 'n_clicks')],
        [State('seaborne-time-visibility-store', 'data')]
    )
    def toggle_time_visibility(q_clicks, m_clicks, d_clicks, current_visibility):
        from dash import callback_context
        ctx = callback_context
        if not ctx.triggered:
            return current_visibility, '+', '+', '+'
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        new_visibility = current_visibility.copy()
        
        if button_id == 'seaborne-toggle-quarter-btn':
            new_visibility['Quarter'] = not current_visibility['Quarter']
            # If hiding quarter, must also hide month and day
            if not new_visibility['Quarter']:
                new_visibility['Month'] = False
                new_visibility['Day'] = False
        elif button_id == 'seaborne-toggle-month-btn':
            new_visibility['Month'] = not current_visibility['Month']
            # If showing month, must also show quarter
            if new_visibility['Month']:
                new_visibility['Quarter'] = True
            # If hiding month, must also hide day
            if not new_visibility['Month']:
                new_visibility['Day'] = False
        elif button_id == 'seaborne-toggle-day-btn':
            new_visibility['Day'] = not current_visibility['Day']
            # If showing day, must also show quarter and month
            if new_visibility['Day']:
                new_visibility['Quarter'] = True
                new_visibility['Month'] = True
        
        return (
            new_visibility, 
            '-' if new_visibility['Quarter'] else '+',
            '-' if new_visibility['Month'] else '+',
            '-' if new_visibility['Day'] else '+'
        )

    @dash_app.callback(
        [Output('seaborne-bar-granularity-store', 'data'),
         Output('seaborne-bar-toggle-year-btn', 'children'),
         Output('seaborne-bar-toggle-quarter-btn', 'children'),
         Output('seaborne-bar-toggle-month-btn', 'children'),
         Output('seaborne-bar-toggle-day-btn', 'children')],
        [Input('seaborne-bar-toggle-year-btn', 'n_clicks'),
         Input('seaborne-bar-toggle-quarter-btn', 'n_clicks'),
         Input('seaborne-bar-toggle-month-btn', 'n_clicks'),
         Input('seaborne-bar-toggle-day-btn', 'n_clicks')],
        [State('seaborne-bar-granularity-store', 'data')]
    )
    def toggle_bar_granularity(y_clicks, q_clicks, m_clicks, d_clicks, current_granularity):
        from dash import callback_context
        ctx = callback_context
        if not ctx.triggered:
            return current_granularity, '+', '+', '-', '+'
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        new_granularity = current_granularity
        if button_id == 'seaborne-bar-toggle-year-btn':
            new_granularity = 'YEARLY'
        elif button_id == 'seaborne-bar-toggle-quarter-btn':
            new_granularity = 'QUARTERLY'
        elif button_id == 'seaborne-bar-toggle-month-btn':
            new_granularity = 'MONTHLY'
        elif button_id == 'seaborne-bar-toggle-day-btn':
            new_granularity = 'DATE'
            
        return (
            new_granularity,
            '-' if new_granularity == 'YEARLY' else '+',
            '-' if new_granularity == 'QUARTERLY' else '+',
            '-' if new_granularity == 'MONTHLY' else '+',
            '-' if new_granularity == 'DATE' else '+'
        )

    @dash_app.callback(
        [Output('avg-exports-table', 'data'),
         Output('avg-exports-table', 'columns')],
        [Input('seaborne-year-selector', 'value'),
         Input('seaborne-time-visibility-store', 'data')]
    )
    def update_avg_exports_table(selected_year, time_visibility):
        if time_visibility is None:
            time_visibility = {'Quarter': False, 'Month': False, 'Day': False}
        
        query = """
        SELECT
            po.port_name                     AS loading_port,
            EXTRACT(YEAR FROM ru.date)::INT  AS year_of_date,
            'Q' || EXTRACT(QUARTER FROM ru.date)::INT AS quarter_of_date,
            TO_CHAR(ru.date, 'Month')        AS month_of_date,
            EXTRACT(DAY FROM ru.date)::INT   AS day_of_date,
            ru.vol_kbpd
        FROM russia_master_data ru
        LEFT JOIN dim_ports po
            ON ru.destination = po.port_name
        WHERE
            po.port_name IS NOT NULL
            AND po.port_name NOT IN ('Hungary', 'Czech Republic')
            AND ru.type = 'Seaborne'
            AND EXTRACT(YEAR FROM ru.date) IN (2025, 2024, 2023, 2022)
        ORDER BY
            po.port_name,
            year_of_date,
            quarter_of_date,
            month_of_date,
            day_of_date;
        """
        try:
            results = execute_query(query)
            df = pd.DataFrame(results)
            if df.empty:
                return [], []
            
            # Identify active dimensions
            active_time_dims = ['year_of_date']
            if time_visibility.get('Quarter'):
                active_time_dims.append('quarter_of_date')
            if time_visibility.get('Month'):
                active_time_dims.append('month_of_date')
            if time_visibility.get('Day'):
                active_time_dims.append('day_of_date')
            
            # Cleanup raw data
            if 'month_of_date' in df.columns:
                df['month_of_date'] = df['month_of_date'].str.strip()
            
            # Aggregate data
            group_cols = ['loading_port'] + active_time_dims
            agg_df = df.groupby(group_cols)['vol_kbpd'].mean().reset_index()
            agg_df['vol_kbpd'] = agg_df['vol_kbpd'].round().fillna(0).astype(int)
            
            # Pivot the data
            pivot_columns = active_time_dims
            pivot_df = agg_df.pivot_table(
                index='loading_port',
                columns=pivot_columns,
                values='vol_kbpd'
            )
            
            # Determine header depth
            num_time_levels = len(active_time_dims)
            header_depth = max(2, num_time_levels) # min 2 to keep Port below Year
            
            # Sorting logic
            month_order = {
                'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
                'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
            }
            
            data_cols = pivot_df.columns.tolist()
            def col_sort_key(c):
                # Ensure c is a tuple matching active_time_dims
                c_tuple = c if isinstance(c, tuple) else (c,)
                key = [-int(c_tuple[0])] # Year DESC
                if len(c_tuple) > 1: key.append(str(c_tuple[1])) # Quarter
                if len(c_tuple) > 2: key.append(month_order.get(c_tuple[2], 0)) # Month
                if len(c_tuple) > 3: key.append(int(c_tuple[3])) # Day
                return tuple(key)

            sorted_data_cols = sorted(data_cols, key=col_sort_key)
            
            # Build Dash DataTable columns
            # Loading Port aligns with the bottom-most level
            lp_header = [""] * (header_depth - 1) + ["Loading Port"]
            dash_columns = [{"name": lp_header, "id": "loading_port"}]
            
            for col in sorted_data_cols:
                col_tuple = col if isinstance(col, tuple) else (col,)
                # Force ID to be unique and consistent
                col_id = "_".join(map(str, col_tuple))
                
                # Build header hierarchy with constant depth
                name_parts = [""] * header_depth
                for i, val in enumerate(col_tuple):
                    if i < header_depth:
                        name_parts[i] = str(val)
                
                dash_columns.append({
                    "name": name_parts,
                    "id": col_id,
                    "type": "numeric"
                })
            
            # Build data rows
            data_rows = []
            for port, row in pivot_df.iterrows():
                item = {"loading_port": port}
                for col in sorted_data_cols:
                    col_tuple = col if isinstance(col, tuple) else (col,)
                    col_id = "_".join(map(str, col_tuple))
                    val = row[col]
                    item[col_id] = f"{int(val):,}" if pd.notnull(val) else ""
                data_rows.append(item)
            
            # Add Total row
            if data_rows:
                total_row = {"loading_port": "Total"}
                column_sums = pivot_df.sum(axis=0)
                for col in sorted_data_cols:
                    col_tuple = col if isinstance(col, tuple) else (col,)
                    col_id = "_".join(map(str, col_tuple))
                    sum_val = column_sums[col]
                    total_row[col_id] = f"{int(sum_val):,}" if pd.notnull(sum_val) else "0"
                data_rows.append(total_row)

            return data_rows, dash_columns
        except Exception as e:
            print(f"Error loading avg exports: {e}")
            import traceback
            traceback.print_exc()
            return [], []
    @dash_app.callback(
        [Output('yoy-change-table', 'data'),
         Output('yoy-change-table', 'columns')],
        Input('seaborne-year-selector', 'value')
    )
    def update_yoy_change_table(selected_year):
        query = """
        WITH monthly_avg AS (
            SELECT
                po.port_name,
                EXTRACT(YEAR FROM ru.date)::int AS yr,
                EXTRACT(MONTH FROM ru.date)::int AS mon,
                AVG(ru.vol_kbpd) AS avg_vol
            FROM russia_master_data ru
            JOIN dim_ports po ON ru.destination = po.port_name
            WHERE ru.type = 'Seaborne'
            GROUP BY po.port_name, yr, mon
        ),
        yoy AS (
            SELECT
                cur.port_name,
                cur.yr AS year,
                cur.mon,
                ROUND(
                    ((cur.avg_vol - prev.avg_vol) / NULLIF(prev.avg_vol, 0))::numeric * 100,
                    1
                ) AS yoy_pct
            FROM monthly_avg cur
            JOIN monthly_avg prev ON cur.port_name = prev.port_name
               AND cur.mon = prev.mon
               AND cur.yr = prev.yr + 1
        )
        SELECT * FROM yoy WHERE year > 2022 ORDER BY year ASC, port_name ASC, mon;
        """
        try:
            results = execute_query(query)
            df = pd.DataFrame(results)
            if df.empty:
                return [], []
            
            month_map = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June', 
                         7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'}
            df['month_name'] = df['mon'].map(month_map)
            
            # Create period label
            df['period'] = df['year'].apply(lambda x: f"{x-1}-{x}")
            
            # Pivot
            pivot_df = df.pivot_table(
                index=['period', 'port_name'], 
                columns='month_name', 
                values='yoy_pct'
            ).reset_index()
            
            # Month ordering
            active_months = sorted(df['mon'].unique())
            active_month_names = [month_map[m] for m in active_months]
            cols = ['period', 'port_name'] + active_month_names
            pivot_df = pivot_df[cols]
            
            # Sort by period ascending
            pivot_df = pivot_df.sort_values(['period', 'port_name'], ascending=[True, True])

            columns = [
                {"name": "", "id": "period"},
                {"name": "Loading Port", "id": "port_name"}
            ]
            for m_name in active_month_names:
                columns.append({"name": m_name, "id": m_name})
            
            # Merge logic for period column
            data = []
            last_period = None
            for _, row in pivot_df.iterrows():
                formatted_row = {}
                current_period = row['period']
                
                # Fig looks like it's centered or repeated. 
                # Let's show it on the first row of each group and keep others empty
                if current_period != last_period:
                    formatted_row['period'] = current_period
                else:
                    formatted_row['period'] = ""
                
                last_period = current_period
                
                for col in pivot_df.columns:
                    if col == 'period': continue
                    val = row[col]
                    if col == 'port_name':
                        # Truncate long port names like in fig
                        if val and len(val) > 13:
                            formatted_row[col] = val[:11] + ".."
                        else:
                            formatted_row[col] = val
                    elif pd.notnull(val):
                        formatted_row[col] = f"{val}%"
                    else:
                        formatted_row[col] = ""
                data.append(formatted_row)

            return data, columns
        except Exception as e:
            print(f"Error loading yoy change: {e}")
            return [], []

    from dash import clientside_callback
    clientside_callback(
        """
        function(clickData, currentStore) {
            if (!clickData || !clickData.points || clickData.points.length === 0) {
                return [currentStore, window.dash_clientside.no_update];
            }
            
            const point = clickData.points[0];
            const traceIdx = point.curveNumber;
            let newVal = null;
            let type = null;

            if (traceIdx === 0) {
                newVal = point.x;
                type = 'bar';
            } else if (traceIdx === 1) {
                const cd = point.customdata;
                newVal = Array.isArray(cd) ? cd[0] : cd;
                type = 'year';
            } else {
                return [currentStore, null];
            }

            let nextStore = {type: type, value: newVal};
            if (currentStore && currentStore.type === type) {
                const currV = String(currentStore.value).replace(/[\[\]\s]/g, '');
                const newV = String(newVal).replace(/[\[\]\s]/g, '');
                if (currV === newV) {
                    nextStore = null;
                }
            }
            
            // We return the new store state AND clear clickData to null 
            // so the next click (even if on same year) always triggers a change
            return [nextStore, null];
        }
        """,
        [Output('seaborne-bar-highlight-store', 'data'),
         Output('seaborne-bar-chart', 'clickData')],
        Input('seaborne-bar-chart', 'clickData'),
        State('seaborne-bar-highlight-store', 'data'),
        prevent_initial_call=True
    )

    @dash_app.callback(
        Output('seaborne-bar-chart', 'figure'),
        [Input('seaborne-year-selector', 'value'),
         Input('seaborne-bar-highlight-store', 'data'),
         Input('seaborne-bar-granularity-store', 'data')]
    )
    def update_bar_chart(selected_year, highlight, period):
        query = f"""
        WITH params AS (
            SELECT '{period}'::text AS period
        ),
        base AS (
            SELECT
                r.date,
                r.vol_kbpd,
                EXTRACT(YEAR FROM r.date)::int    AS year_of_date,
                EXTRACT(QUARTER FROM r.date)::int AS quarter_of_date,
                EXTRACT(MONTH FROM r.date)::int   AS month_of_date,
                p.period
            FROM russia_master_data r
            CROSS JOIN params p
            WHERE r.type = 'Seaborne'
              AND EXTRACT(YEAR FROM r.date) > 2021
        )
        SELECT
            year_of_date,
            CASE WHEN period IN ('QUARTERLY', 'MONTHLY', 'DATE') THEN quarter_of_date END AS quarter_of_date,
            CASE WHEN period IN ('MONTHLY', 'DATE') THEN month_of_date END AS month_of_date,
            CASE WHEN period = 'DATE' THEN date END AS date_of_date,
            SUM(vol_kbpd) AS total_vol
        FROM base
        GROUP BY
            year_of_date,
            CASE WHEN period IN ('QUARTERLY', 'MONTHLY', 'DATE') THEN quarter_of_date END,
            CASE WHEN period IN ('MONTHLY', 'DATE') THEN month_of_date END,
            CASE WHEN period = 'DATE' THEN date END
        ORDER BY
            year_of_date, quarter_of_date, month_of_date, date_of_date;
        """
        try:
            results = execute_query(query)
            df = pd.DataFrame(results)
            if df.empty:
                return go.Figure()

            # Define label logic based on period
            def get_label(row):
                if period == 'YEARLY':
                    return f"{row['year_of_date']}"
                if period == 'QUARTERLY':
                    return f"Q{int(row['quarter_of_date'])}"
                if period == 'MONTHLY':
                    month_abbr = {1:'Ja..', 2:'Fe..', 3:'M..', 4:'A..', 5:'M..', 6:'Ju..', 7:'Ju..', 8:'A..', 9:'Se..', 10:'O..', 11:'N..', 12:'D..'}
                    return month_abbr.get(int(row['month_of_date']), '')
                if period == 'DATE':
                    if pd.notnull(row['date_of_date']):
                        return pd.to_datetime(row['date_of_date']).strftime('%d %b')
                return ""

            def get_full_date_string(row):
                if period == 'YEARLY':
                    return f"{row['year_of_date']}"
                if period == 'QUARTERLY':
                    return f"Q{int(row['quarter_of_date'])} {row['year_of_date']}"
                if period == 'MONTHLY':
                    month_full = {1:'January', 2:'February', 3:'March', 4:'April', 5:'May', 6:'June', 7:'July', 8:'August', 9:'September', 10:'October', 11:'November', 12:'December'}
                    return f"{month_full.get(int(row['month_of_date']), '')} {row['year_of_date']}"
                if period == 'DATE':
                    if pd.notnull(row['date_of_date']):
                        return pd.to_datetime(row['date_of_date']).strftime('%d %B %Y')
                return ""

            df['label'] = df.apply(get_label, axis=1)
            df['full_label'] = df.apply(get_full_date_string, axis=1)
            
            # Create unique x coordinates
            df['x_idx'] = range(len(df))
            
            # Prepare markers and colors
            bar_colors = []
            line_widths = []
            line_colors = []
            
            def hex_to_rgba(hex_color, opacity):
                hex_color = hex_color.lstrip('#')
                if len(hex_color) == 6:
                    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                else:
                    return f'rgba(242, 142, 43, {opacity})' # Fallback
                return f'rgba({r},{g},{b},{opacity})'

            for i, row in df.iterrows():
                if not highlight:
                    # Normal State: Strong Orange for all
                    bar_colors.append(hex_to_rgba("#f28e2b", 1.0))
                    line_widths.append(0)
                    line_colors.append('rgba(0,0,0,0)')
                else:
                    is_selected = False
                    if highlight['type'] == 'bar':
                        # Use strings for index comparison
                        if str(i) == str(highlight['value']):
                            is_selected = True
                    elif highlight['type'] == 'year':
                        # Use strings for year comparison
                        if str(row['year_of_date']) == str(highlight['value']):
                            is_selected = True
                    
                    if is_selected:
                        # Highlighted State: Strong Orange with border for bars
                        bar_colors.append(hex_to_rgba("#f28e2b", 1.0))
                        line_widths.append(2 if highlight['type'] == 'bar' else 0)
                        line_colors.append('black')
                    else:
                        # Dimmed State: Faint Orange/Peach
                        bar_colors.append(hex_to_rgba("#f28e2b", 0.2))
                        line_widths.append(0)
                        line_colors.append('rgba(0,0,0,0)')

            fig = go.Figure()
            
            # Trace 0: Bars
            fig.add_trace(go.Bar(
                x=df['x_idx'],
                y=df['total_vol'],
                marker=dict(
                    color=bar_colors,
                    line=dict(color=line_colors, width=line_widths)
                ),
                width=0.8,
                hovertext=[
                    f"Date: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>{row['full_label']}</b><br>"
                    f"Volume ('000 b/d): <b>{int(row['total_vol'] if pd.notnull(row['total_vol']) else 0):,}</b>" 
                    for _, row in df.iterrows()
                ],
                hoverinfo='text',
                hoverlabel=dict(
                    bgcolor="white",
                    bordercolor="#ccc",
                    font=dict(size=12, color="#333", family="Lato, sans-serif"),
                    align="left"
                )
            ))

            # Layout adjustments
            fig.update_layout(
                margin=dict(l=60, r=20, t=60, b=40),
                paper_bgcolor='white',
                plot_bgcolor='white',
                showlegend=False,
                xaxis=dict(
                    title=None,
                    showgrid=False,
                    tickmode='array',
                    tickvals=df['x_idx'],
                    ticktext=df['label'],
                    tickfont=dict(size=9 if period != 'DATE' else 7, color='#666'),
                    fixedrange=True,
                    zeroline=True,
                    zerolinecolor='#ccc'
                ),
                yaxis=dict(
                    title=dict(text="Seaborne Crude Exp...", font=dict(size=10)),
                    showgrid=True,
                    gridcolor='#f0f0f0',
                    tickfont=dict(size=9, color='#666'),
                    range=[0, (df['total_vol'].fillna(0).max() or 1000) * 1.2],
                    fixedrange=True,
                    zeroline=True,
                    zerolinecolor='#ccc'
                ),
                yaxis2=dict(
                    overlaying='y',
                    side='right',
                    visible=False,
                    range=[0, 1.2],
                    fixedrange=True
                ),
                font=dict(family="Lato, sans-serif"),
                bargap=0.15 if period != 'DATE' else 0.05
            )
            
            # Add vertical lines and YEAR LABELS trace
            shapes = []
            
            years = sorted(df['year_of_date'].unique())
            year_labels_x = []
            year_labels_text = []
            year_labels_colors = []
            
            for year in years:
                year_data = df[df['year_of_date'] == year]
                if not year_data.empty:
                    start_idx = year_data['x_idx'].min()
                    end_idx = year_data['x_idx'].max()
                    center_idx = (start_idx + end_idx) / 2
                    
                    year_labels_x.append(center_idx)
                    year_labels_text.append(f"<b>{year}</b>")
                    
                    is_year_highlighted = highlight and highlight['type'] == 'year' and highlight['value'] == year
                    
                    # Highlight background for year if active
                    if is_year_highlighted:
                        shapes.append(dict(
                            type='rect',
                            x0=start_idx - 0.5,
                            x1=end_idx + 0.5,
                            y0=1.03,
                            y1=1.13,
                            xref='x',
                            yref='paper',
                            fillcolor='#ADD8E6', # LightBlue as per Fig 2
                            line=dict(width=0),
                            layer='below'
                        ))
                        year_labels_colors.append(EI_DARK_BLUE)
                    else:
                        year_labels_colors.append(EI_DARK_BLUE)

                    # Vertical line to separate years
                    if year != years[-1]:
                        shapes.append(dict(
                            type='line',
                            x0=end_idx + 0.5,
                            x1=end_idx + 0.5,
                            y0=0,
                            y1=1,
                            yref='paper',
                            line=dict(color='#ddd', width=1)
                        ))
            
            # Trace 1: Year Labels (Interactive)
            fig.add_trace(go.Scatter(
                x=year_labels_x,
                y=[1.08] * len(years),
                yaxis='y2',
                mode='text',
                text=year_labels_text,
                textfont=dict(size=13, color=year_labels_colors),
                hoverinfo='none',
                customdata=years # Pass raw year for callback
            ))

            fig.update_layout(shapes=shapes)
            
            return fig
        except Exception as e:
            print(f"Error loading bar chart: {e}")
            import traceback
            traceback.print_exc()
            return go.Figure()

    # CSV Export Callbacks
    @dash_app.callback(
        Output("download-seaborne-map-csv", "data"),
        Input("btn-seaborne-map-csv", "n_clicks"),
        State("seaborne-year-selector", "value"),
        prevent_initial_call=True,
    )
    def export_map_csv(n_clicks, selected_year):
        query = """
        SELECT
            po.port_name                     AS loading_port,
            EXTRACT(YEAR FROM ru.date)::INT  AS year,
            ROUND(AVG(ru.vol_kbpd))          AS average_vol_kbpd
        FROM russia_master_data ru
        JOIN dim_ports po ON ru.destination = po.port_name
        WHERE ru.type = 'Seaborne' AND EXTRACT(YEAR FROM ru.date) = :year
        GROUP BY po.port_name, year
        ORDER BY average_vol_kbpd DESC;
        """
        try:
            results = execute_query(query, {'year': selected_year})
            df = pd.DataFrame(results)
            return dcc.send_data_frame(df.to_csv, f"seaborne_map_data_{selected_year}.csv", index=False)
        except Exception as e:
            print(f"Error exporting map csv: {e}")
            return None

    @dash_app.callback(
        Output("download-seaborne-bar-csv", "data"),
        Input("btn-seaborne-bar-csv", "n_clicks"),
        State("seaborne-bar-granularity-store", "data"),
        prevent_initial_call=True,
    )
    def export_bar_csv(n_clicks, period):
        query = f"""
        WITH params AS (
            SELECT '{period}'::text AS period
        ),
        base AS (
            SELECT
                r.date,
                r.vol_kbpd,
                EXTRACT(YEAR FROM r.date)::int    AS year_of_date,
                EXTRACT(QUARTER FROM r.date)::int AS quarter_of_date,
                EXTRACT(MONTH FROM r.date)::int   AS month_of_date,
                p.period
            FROM russia_master_data r
            CROSS JOIN params p
            WHERE r.type = 'Seaborne'
              AND EXTRACT(YEAR FROM r.date) > 2021
        )
        SELECT
            year_of_date,
            CASE WHEN period IN ('QUARTERLY', 'MONTHLY', 'DATE') THEN quarter_of_date END AS quarter_of_date,
            CASE WHEN period IN ('MONTHLY', 'DATE') THEN month_of_date END AS month_of_date,
            CASE WHEN period = 'DATE' THEN date END AS date_of_date,
            SUM(vol_kbpd) AS total_vol_kbpd
        FROM base
        GROUP BY
            year_of_date,
            CASE WHEN period IN ('QUARTERLY', 'MONTHLY', 'DATE') THEN quarter_of_date END,
            CASE WHEN period IN ('MONTHLY', 'DATE') THEN month_of_date END,
            CASE WHEN period = 'DATE' THEN date END
        ORDER BY
            year_of_date, quarter_of_date, month_of_date, date_of_date;
        """
        try:
            results = execute_query(query)
            df = pd.DataFrame(results)
            # Remove empty columns (like quarter/month/date when in yearly mode)
            df.dropna(axis=1, how='all', inplace=True)
            return dcc.send_data_frame(df.to_csv, f"seaborne_bar_data_{period.lower()}.csv", index=False)
        except Exception as e:
            print(f"Error exporting bar csv: {e}")
            return None

    @dash_app.callback(
        Output("download-avg-exports-csv", "data"),
        Input("btn-avg-exports-csv", "n_clicks"),
        [State("avg-exports-table", "data"),
         State("avg-exports-table", "columns")],
        prevent_initial_call=True,
    )
    def export_avg_exports_csv(n_clicks, table_data, columns):
        if not table_data:
            return None
        df = pd.DataFrame(table_data)
        
        # Map column IDs to display names (handling MultiIndex lists)
        col_id_to_name = {}
        for col in columns:
            name = col['name']
            if isinstance(name, list):
                # Clean up empty strings and join
                name = " ".join([part for part in name if part.strip()])
            col_id_to_name[col['id']] = name
        
        df = df.rename(columns=col_id_to_name)
        return dcc.send_data_frame(df.to_csv, "average_seaborne_exports.csv", index=False)

    @dash_app.callback(
        Output("download-yoy-change-csv", "data"),
        Input("btn-yoy-change-csv", "n_clicks"),
        State("yoy-change-table", "data"),
        prevent_initial_call=True,
    )
    def export_yoy_change_csv(n_clicks, table_data):
        if not table_data:
            return None
        df = pd.DataFrame(table_data)
        # The column names are already correct in the data
        return dcc.send_data_frame(df.to_csv, "yoy_change_seaborne_exports.csv", index=False)

    @dash_app.callback(
        Output('seaborne-map', 'figure'),
        Input('seaborne-year-selector', 'value')
    )
    def update_map(selected_year):
        query = """
        SELECT
            po.port_name,
            po.latitude,
            po.longitude,
            ru.country,

            -- Average volume
            ROUND(AVG(ru.vol_kbpd)) AS total_vol,

            -- Crude mapping
            CASE
                WHEN po.port_name = 'Baltics' THEN 'Urals'
                WHEN po.port_name = 'Kozmino Bay' THEN 'ESPO Blend'
                WHEN po.port_name = 'Novorossiysk' THEN 'Urals, Siberian Light'
                WHEN po.port_name = 'DeKastri' THEN 'Sokol'
                WHEN po.port_name = 'Varandey' THEN 'Varandey'
                WHEN po.port_name = 'Prigorodnoye' THEN 'Sakhalin Blend'
                ELSE 'na'
            END AS crude,

            -- Storage capacity (000 b/d)
            CASE
                WHEN po.port_name = 'DeKastri' THEN 700
                WHEN po.port_name = 'Varandey' THEN 240
                ELSE NULL
            END AS storage_cap

        FROM russia_master_data ru
        JOIN dim_ports po
            ON ru.destination = po.port_name
        WHERE
            ru.type = 'Seaborne'
            AND EXTRACT(YEAR FROM ru.date) = :year
        GROUP BY
            po.port_name,
            po.latitude,
            po.longitude,
            ru.country;
        """
        try:
            results = execute_query(query, {'year': selected_year})
            df_map = pd.DataFrame(results) if results else pd.DataFrame()
            
            # Coordinate Fallback for Russian Ports
            ports_fallback = {
                'Sabetta': (71.27, 72.07),
                'Arctic Gates': (68.5, 48.0),
                'DeKastri': (51.45, 140.78),
                'Kozmino Bay': (42.73, 133.07),
                'Prigorodnoye': (46.61, 142.91),
                'Novorossiysk': (44.72, 37.78),
                'Korchagin': (45.4, 48.0),
                'Baltics': (59.9, 28.5),
                'Murmansk': (69.0, 33.1),
            }
            
            if not df_map.empty:
                for idx, row in df_map.iterrows():
                    if pd.isna(row['latitude']) or pd.isna(row['longitude']):
                        if row['port_name'] in ports_fallback:
                            lat, lon = ports_fallback[row['port_name']]
                            df_map.at[idx, 'latitude'] = lat
                            df_map.at[idx, 'longitude'] = lon

            geojson = load_world_geojson()
            
            fig = go.Figure()

            # 1. Shaded Russia Layer
            if geojson:
                fig.add_trace(go.Choroplethmapbox(
                    geojson=geojson,
                    locations=['RUS'], # ISO for Russia
                    z=[1],
                    colorscale=[[0, '#3a618c'], [1, '#3a618c']],
                    showscale=False,
                    marker_opacity=0.8,
                    marker_line_width=0,
                    name='countries',
                    customdata=['RUS'],
                    hoverinfo='location',
                    hovertemplate='<b>Russia</b><extra></extra>'
                ))

            # 2. Port Markers (Circles)
            # Ensure all fallback ports are present even if not in DB
            ports_fallback_list = list(ports_fallback.keys())
            if not df_map.empty:
                # Merge DB data with all fallback ports to ensure they exist
                all_ports_df = pd.DataFrame({'port_name': ports_fallback_list})
                df_ports = pd.merge(all_ports_df, df_map, on='port_name', how='left')
                df_ports['total_vol'] = df_ports['total_vol'].fillna(0)
            else:
                df_ports = pd.DataFrame({'port_name': ports_fallback_list})
                df_ports['total_vol'] = 0
            
            # Fill coordinates for all ports
            for idx, row in df_ports.iterrows():
                if pd.isna(row.get('latitude')) or pd.isna(row.get('longitude')):
                    if row['port_name'] in ports_fallback:
                        lat, lon = ports_fallback[row['port_name']]
                        df_ports.at[idx, 'latitude'] = lat
                        df_ports.at[idx, 'longitude'] = lon

            if not df_ports.empty:
                fig.add_trace(go.Scattermapbox(
                    lat=df_ports['latitude'],
                    lon=df_ports['longitude'],
                    mode='markers+text',
                    marker=go.scattermapbox.Marker(
                        size=df_ports['total_vol'].apply(lambda x: 8 + (x ** 0.5) / 1.5), # Adjusted scaling
                        color='#f28e2b',
                        symbol='circle', 
                        opacity=0.9
                    ),
                    text=df_ports['port_name'],
                    textposition='bottom center',
                    customdata=df_ports['port_name'], # For identification if needed
                    textfont=dict(size=11, color='#333', family="Lato, sans-serif"),
                    hovertext=[
                        f"Port: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>{row['port_name']}</b><br>"
                        f"Exports ('000 b/d): &nbsp;&nbsp;<b>{int(row['total_vol']):,}</b>" +
                        (f"<br>Crude: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>{row['crude']}</b>" if row.get('crude') != 'na' else "") + 
                        (f"<br>Storage Capacity (000 b/d): <b>{int(row['storage_cap'])}</b>" if pd.notnull(row.get('storage_cap')) else "")
                        for _, row in df_ports.iterrows()
                    ],
                    hoverinfo='text'
                ))

            fig.update_layout(
                mapbox=dict(
                    style='carto-positron',
                    center=dict(lat=62, lon=85),
                    zoom=1.0
                ),
                margin=dict(l=0, r=0, t=0, b=0),
                showlegend=False,
                hoverlabel=dict(
                    bgcolor="white",
                    bordercolor="#ccc",
                    font=dict(size=12, color="#333", family="Lato, sans-serif"),
                    align="left"
                )
            )

            return fig
        except Exception as e:
            print(f"Error loading map: {e}")
            return go.Figure()

    # Clientside callback for Russia hover highlight
    from dash import clientside_callback
    clientside_callback(
        """
        function(hoverData, fig) {
            if (!fig || !fig.data) return window.dash_clientside.no_update;
            
            let newFig = JSON.parse(JSON.stringify(fig));
            let hoveredRussia = false;
            
            if (hoverData && hoverData.points && hoverData.points.length > 0) {
                let point = hoverData.points[0];
                let traceIdx = point.curveNumber;
                let trace = fig.data[traceIdx];
                
                // Identify if we are hovering over Russia (via location or customdata)
                if (point.location === 'RUS' || (point.customdata && (point.customdata === 'RUS' || point.customdata[0] === 'RUS'))) {
                    hoveredRussia = true;
                } else if (trace && trace.name === 'countries') {
                    hoveredRussia = true;
                }
            }
            
            // Remove previous highlight
            newFig.data = newFig.data.filter(t => t.name !== 'hover_highlight');
            
            if (hoveredRussia) {
                // Find the countries/russia trace to copy geojson
                let russiaTrace = newFig.data.find(t => t.type === 'choroplethmapbox');
                if (russiaTrace) {
                    let highlightTrace = {
                        type: 'choroplethmapbox',
                        geojson: russiaTrace.geojson,
                        locations: ['RUS'],
                        z: [1],
                        featureidkey: russiaTrace.featureidkey || 'id',
                        colorscale: [[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0)']],
                        showscale: false,
                        marker: {
                            line: { color: 'black', width: 3 },
                            opacity: 1
                        },
                        hoverinfo: 'skip',
                        name: 'hover_highlight'
                    };
                    newFig.data.push(highlightTrace);
                }
            }
            
            return newFig;
        }
        """,
        Output('seaborne-map', 'figure', allow_duplicate=True),
        Input('seaborne-map', 'hoverData'),
        State('seaborne-map', 'figure'),
        prevent_initial_call=True
    )

    # Generic Table Highlighting Clientside Callback
    def create_table_highlighting_callback(table_id, store_id):
        clientside_callback(
            """
            function(active_cell, table_data, current_store) {
                const table_div = document.getElementById(table_id);
                if (!table_div) return window.dash_clientside.no_update;
                
                const spreadsheet = table_div.querySelector('.dash-spreadsheet-container');
                if (!spreadsheet) return window.dash_clientside.no_update;

                const clearHighlights = () => {
                    spreadsheet.classList.remove('highlight-mode');
                    spreadsheet.querySelectorAll('td').forEach(td => td.classList.remove('highlighted'));
                };

                const applyHighlight = (type, id) => {
                    spreadsheet.classList.add('highlight-mode');
                    if (type === 'row') {
                        spreadsheet.querySelectorAll(`td[data-dash-row="${id}"]`).forEach(td => td.classList.add('highlighted'));
                    } else if (type === 'cell') {
                        const [r, c] = id.split(':::');
                        spreadsheet.querySelectorAll(`td[data-dash-column="${c}"][data-dash-row="${r}"]`).forEach(td => td.classList.add('highlighted'));
                    } else if (type === 'column') {
                        // For hierarchical highlighting, id is a list of column names or a range
                        const columnIds = id.split(';;;');
                        columnIds.forEach(colId => {
                            spreadsheet.querySelectorAll(`td[data-dash-column="${colId}"]`).forEach(td => td.classList.add('highlighted'));
                        });
                    }
                };

                if (!table_div.dataset.listenerAttached) {
                    table_div.addEventListener('click', (e) => {
                        const cell = e.target.closest('td.dash-cell');
                        const header = e.target.closest('.dash-header');
                        
                        let hType = null;
                        let hId = null;

                        if (header) {
                            hType = 'column';
                            const isExportsTable = table_id.includes('avg-exports');
                            
                            if (isExportsTable) {
                                // Hierarchical logic: find all columns within the horizontal bounds of this header
                                const rect = header.getBoundingClientRect();
                                const center = rect.left + rect.width / 2;
                                
                                // We need to find all terminal columns (bottom-row headers or data cells)
                                // that fall within [rect.left, rect.right]
                                const terminalHeaders = spreadsheet.querySelectorAll('.dash-spreadsheet tr:last-child .dash-header');
                                const targetColIds = [];
                                
                                // Actually, it's easier to check the terminal headers in the bottom row of the header section
                                // or just check the first row of data cells
                                const sampleCells = spreadsheet.querySelectorAll('.dash-spreadsheet tr:first-child td.dash-cell');
                                sampleCells.forEach(td => {
                                    const cRect = td.getBoundingClientRect();
                                    const cCenter = cRect.left + cRect.width / 2;
                                    if (cCenter >= rect.left - 1 && cCenter <= rect.right + 1) {
                                        const colId = td.getAttribute('data-dash-column');
                                        if (colId && colId !== 'loading_port' && colId !== 'port_name') {
                                            targetColIds.push(colId);
                                        }
                                    }
                                });
                                
                                if (targetColIds.length === 0) {
                                    // Maybe it's the Loading Port header itself
                                    const colId = header.getAttribute('data-dash-column');
                                    if (colId) targetColIds.push(colId);
                                }
                                
                                hId = targetColIds.join(';;;');
                            } else {
                                // Single column logic for YOY table
                                hId = header.getAttribute('data-dash-column');
                            }
                        } else if (cell) {
                            const rowIdx = cell.getAttribute('data-dash-row');
                            const colId = cell.getAttribute('data-dash-column');
                            const isPortCol = colId === 'loading_port' || colId === 'port_name';
                            hType = isPortCol ? 'row' : 'cell';
                            hId = isPortCol ? rowIdx : `${rowIdx}:::${colId}`;
                        }

                        if (hType && hId) {
                            const current = JSON.parse(table_div.dataset.highlightState || '{}');
                            const same = current.type === hType && current.id == hId;
                            
                            clearHighlights();
                            if (same) {
                                table_div.dataset.highlightState = '{}';
                            } else {
                                applyHighlight(hType, hId);
                                table_div.dataset.highlightState = JSON.stringify({type: hType, id: hId});
                            }
                        }
                    });
                    table_div.dataset.listenerAttached = 'true';
                }

                setTimeout(() => {
                    const current = JSON.parse(table_div.dataset.highlightState || '{}');
                    if (current.type) {
                        clearHighlights();
                        applyHighlight(current.type, current.id);
                    }
                }, 50);

                return window.dash_clientside.no_update;
            }
            """.replace('table_id', f"'{table_id}'"),
            Output(store_id, 'data'),
            [Input(table_id, 'active_cell'),
             Input(table_id, 'data')],
            [State(store_id, 'data')]
        )

    create_table_highlighting_callback('avg-exports-table', 'avg-exports-highlight-store')
    create_table_highlighting_callback('yoy-change-table', 'yoy-change-highlight-store')
