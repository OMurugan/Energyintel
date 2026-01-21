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

        # Header Row
        html.Div([
            html.Div([
                html.H3(id='seaborne-title', style={
                    'color': EI_ORANGE,
                    'fontWeight': 'bold',
                    'fontSize': '24px',
                    'margin': '0',
                    'fontFamily': 'Lato, sans-serif'
                })
            ], style={'flex': '1'}),
            
            # Year Selector (Moved to a position that will be 'inbetween' top elements conceptually)
            html.Div([
                dcc.RadioItems(
                    id='seaborne-year-selector',
                    options=[
                        {'label': '2022', 'value': 2022},
                        {'label': '2023', 'value': 2023},
                        {'label': '2024', 'value': 2024},
                        {'label': '2025', 'value': 2025},
                    ],
                    value=2025,
                    style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'display': 'flex', 'gap': '15px'},
                    labelStyle={'display': 'inline-block', 'margin': '0', 'cursor': 'pointer'}
                )
            ], style={'marginRight': '380px', 'paddingTop': '10px'}) # Offset to align 'between' map and right tables
        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px', 'padding': '0 15px'}),

        # Main Content "Single Rectangle" Container
        html.Div([
            # Left Column (Map and Bar Chart)
            html.Div([
                # Map
                html.Div([
                    dcc.Loading(
                        id='loading-seaborne-map',
                        type='circle',
                        children=dcc.Graph(
                            id='seaborne-map',
                            style={'height': '380px'},
                            config={'displayModeBar': False}
                        )
                    )
                ], style={'marginBottom': '0'}),

                # Bar Chart
                html.Div([
                    dcc.Loading(
                        id='loading-seaborne-bar-chart',
                        type='circle',
                        children=dcc.Graph(
                            id='seaborne-bar-chart',
                            style={'height': '320px'},
                            config={'displayModeBar': False}
                        )
                    )
                ], style={'marginTop': '-20px'}) # Tightly pack chart under map
            ], style={'width': '64%', 'paddingRight': '15px', 'borderRight': '1px solid #eee'}),

            # Right Column (Tables)
            html.Div([
                # Average Exports Table
                html.Div([
                    html.Div([
                        html.H4("AVERAGE SEABORNE EXPORTS BY", style={'color': EI_ORANGE, 'fontSize': '15px', 'fontWeight': 'bold', 'margin': '0'}),
                        html.H4("LOADING PORT ('000 b/d)", style={'color': EI_ORANGE, 'fontSize': '15px', 'fontWeight': 'bold', 'margin': '0'}),
                    ], style={'marginBottom': '8px'}),

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
                        style_table={'height': '260px', 'overflowY': 'auto'},
                        style_header={'backgroundColor': 'white', 'fontWeight': 'bold', 'borderBottom': '1px solid #ddd', 'color': EI_DARK_BLUE, 'fontSize': '11px'},
                        style_cell={'padding': '3px 6px', 'fontSize': '10px', 'fontFamily': 'Lato, sans-serif', 'border': 'none', 'textAlign': 'right', 'color': '#333'},
                        style_cell_conditional=[{'if': {'column_id': 'loading_port'}, 'textAlign': 'left', 'minWidth': '110px'}],
                        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f9f9f9'}]
                    )
                ], style={'marginBottom': '20px', 'padding': '5px'}),

                # YOY Change Table
                html.Div([
                    html.H4("YOY % CHANGE BY LOADING PORT", style={'color': EI_ORANGE, 'fontSize': '15px', 'fontWeight': 'bold', 'marginBottom': '8px'}),
                    dash_table.DataTable(
                        id='yoy-change-table',
                        style_table={'height': '360px', 'overflowY': 'auto', 'overflowX': 'auto'},
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
                        css=[{'selector': 'td[data-dash-column="period"]', 'rule': 'writing-mode: vertical-rl; transform: rotate(180deg); white-space: nowrap; height: auto; text-align: center; vertical-align: middle;'}]
                    )
                ], style={'padding': '5px'})
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

    @callback(
        Output('seaborne-title', 'children'),
        Input('seaborne-year-selector', 'value')
    )
    def update_title(year):
        return f"{year} SEABORNE CRUDE EXPORTS BY MAIN LOADING PORT"

    @callback(
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

    @callback(
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
        FROM dev.russia_master_data ru
        LEFT JOIN dev.dim_ports po
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
    @callback(
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
            FROM dev.russia_master_data ru
            JOIN dev.dim_ports po ON ru.destination = po.port_name
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

    @callback(
        Output('seaborne-bar-chart', 'figure'),
        Input('seaborne-year-selector', 'value')
    )
    def update_bar_chart(selected_year):
        query = """
        SELECT
            EXTRACT(YEAR FROM date)::int AS year,
            EXTRACT(MONTH FROM date)::int AS month,
            SUM(vol_kbpd) AS total_vol
        FROM dev.russia_master_data
        WHERE type = 'Seaborne' AND EXTRACT(YEAR FROM date) > 2021
        GROUP BY year, month
        ORDER BY year, month;
        """
        try:
            results = execute_query(query)
            df = pd.DataFrame(results)
            if df.empty:
                return go.Figure()

            full_month_map = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June', 
                              7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'}
            df['full_month'] = df['month'].map(full_month_map)
            
            month_map = {1: 'Ja..', 2: 'Fe..', 3: 'M..', 4: 'A..', 5: 'M..', 6: 'Ju..', 
                         7: 'Ju..', 8: 'A..', 9: 'Se..', 10: 'O..', 11: 'N..', 12: 'D..'}
            df['month_label'] = df['month'].map(month_map)
            
            # Create unique x coordinates to prevent Plotly multi-category squishing
            df['x_idx'] = range(len(df))
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=df['x_idx'],
                y=df['total_vol'],
                marker_color='#f28e2b',
                width=0.8,
                hovertext=[
                    f"Date: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>{row['full_month']} {row['year']}</b><br>"
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
                    ticktext=df['month_label'],
                    tickfont=dict(size=9, color='#666'),
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
                font=dict(family="Lato, sans-serif"),
                bargap=0.15
            )
            
            # Add vertical lines and year annotations
            shapes = []
            annotations = []
            
            years = sorted(df['year'].unique())
            for year in years:
                year_data = df[df['year'] == year]
                if not year_data.empty:
                    # Start and end indices for this year
                    start_idx = year_data['x_idx'].min()
                    end_idx = year_data['x_idx'].max()
                    center_idx = (start_idx + end_idx) / 2
                    
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
                    
                    # Year label at the top
                    annotations.append(dict(
                        x=center_idx,
                        y=1.08,
                        xref="x",
                        yref="paper",
                        text=f"<b>{year}</b>",
                        showarrow=False,
                        font=dict(size=13, color=EI_DARK_BLUE)
                    ))
            
            fig.update_layout(shapes=shapes, annotations=annotations)
            
            return fig
        except Exception as e:
            print(f"Error loading bar chart: {e}")
            return go.Figure()

    @callback(
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
            ROUND(AVG(ru.vol_kbpd)) AS total_vol
        FROM dev.russia_master_data ru
        JOIN dev.dim_ports po ON ru.destination = po.port_name
        WHERE ru.type = 'Seaborne' AND EXTRACT(YEAR FROM ru.date) = :year
        GROUP BY po.port_name, po.latitude, po.longitude, ru.country;
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
                        f"Exports ('000 b/d): &nbsp;&nbsp;<b>{int(row['total_vol']):,}</b>"
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
