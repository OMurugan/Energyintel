import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, dash_table, State, callback, ctx, no_update
from core.data_helpers import execute_query
from app.dashboards.wcod.shared_map_utils import (
    create_choropleth_map, handle_map_click_reset, load_world_geojson
)

# Color Palette
EI_ORANGE = "#ff6600"
EI_DARK_BLUE = "#1b365d"
EI_LIGHT_BLUE = "#e8f4f8"

# Origin colors based on Fig 1 (approximate colors from legend images)
ORIGIN_COLORS = {
    'Algeria': '#0070c0',
    'Angola': '#363d4e',
    'Australia': '#945d41',
    'Belgium': '#5b9bd5',
    'Bolivia': '#a5a5a5',
    'Brunei': '#4f81bd',
    'Cameroon': '#b7b7b7',
    'Canada': '#c0504d',
    'China': '#953735',
    'Egypt': '#ff6600',
    'Equatorial Guinea': '#1f497d',
    'France': '#0070c0',
    'Germany': '#515151',
    'Guinea': '#3d4552',
    'India': '#c0504d',
    'Indonesia': '#ed7d31',
    'Iran': '#945d41',
    'Japan': '#ff3300',
    'Kazakhstan': '#555555',
    'Malaysia': '#70adad',
    'Mauritania': '#ed7d31',
    'Mozambique': '#555555',
    'Myanmar': '#5b9bd5',
    'Netherlands': '#1f497d',
    'Nigeria': '#7281bc',
    'Norway': '#7281bc',
    'Oman': '#c5d487',
    'Others': '#c5d487',
    'Papua New Guinea': '#0070c0',
    'Peru': '#303742',
    'Philippines': '#16365d',
    'Qatar': '#16365d',
    'Republic of the Congo': '#7281bc',
    'Russia': '#4682B4',
    'Saudi Arabia': '#0070c0',
    'Senegal': '#303742',
    'Singapore': '#c5d487',
    'South Africa': '#a5a5a5',
    'South Korea': '#0070c0',
    'Spain': '#5b9bd5',
    'Thailand': '#a5a5a5',
    'Timor-Leste': '#a5a5a5',
    'Trinidad and Tobago': '#555555',
    'Turkey': '#945d41',
    'Turkmenistan': '#c5e0b4',
    'United Arab Emirates': '#5b9bd5',
    'United Kingdom': '#a5a5a5',
    'United States': '#c6531d',
    'Uzbekistan': '#16365d'
}

# Button Styles from European Dashboard
GRAN_BTN_CONTAINER_STYLE = {
    'display': 'flex',
    'align-items': 'center',
    'margin-right': '20px'
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

EXPORT_BTN_STYLE = {
    'backgroundColor': 'white',
    'color': '#1b365d',
    'border': '1px solid #ddd',
    'padding': '4px 8px',
    'borderRadius': '4px',
    'fontSize': '11px',
    'cursor': 'pointer',
    'zIndex': '1000'
}

def create_asia_period_selector():
    """Helper to create granularity selectors for Asian Imports chart"""
    return html.Div([
        html.Div([
            html.Span("Year of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
            html.Button('-', id='asia-toggle-year-btn', n_clicks=0, style=GRAN_BTN_ACTIVE)
        ], style=GRAN_BTN_CONTAINER_STYLE),
        
        html.Div([
            html.Span("Quarter of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
            html.Button('+', id='asia-toggle-quarter-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
        ], style=GRAN_BTN_CONTAINER_STYLE),
        
        html.Div([
            html.Span("Month of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
            html.Button('+', id='asia-toggle-month-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
        ], style=GRAN_BTN_CONTAINER_STYLE),

        html.Div([
            html.Span("Day of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
            html.Button('+', id='asia-toggle-day-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
        ], style=GRAN_BTN_CONTAINER_STYLE)
    ], style={
        'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#f8f9fa', 
        'padding': '10px 20px', 'width': 'fit-content'
    })

def create_asia_table_period_selector():
    """Helper to create granularity selectors for Asian Imports table"""
    return html.Div([
        html.Div([
            html.Span("Year of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
            html.Button('-', id='asia-imports-table-toggle-year-btn', n_clicks=0, style=GRAN_BTN_ACTIVE)
        ], style=GRAN_BTN_CONTAINER_STYLE),
        
        html.Div([
            html.Span("Quarter of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
            html.Button('+', id='asia-imports-table-toggle-quarter-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
        ], style=GRAN_BTN_CONTAINER_STYLE),
        
        html.Div([
            html.Span("Month of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
            html.Button('+', id='asia-imports-table-toggle-month-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
        ], style=GRAN_BTN_CONTAINER_STYLE),

        html.Div([
            html.Span("Day of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
            html.Button('+', id='asia-imports-table-toggle-day-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
        ], style=GRAN_BTN_CONTAINER_STYLE)
    ], style={
        'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#fff', 
        'padding': '10px 0', 'width': 'fit-content'
    })

def create_layout():
    """Create the Asian Yearly Imports layout"""
    return html.Div([
        # Selection stores
        dcc.Store(id='gas-asia-period-store', data='YEARLY'),
        dcc.Store(id='asia-chart-granularity-store', data='year'),
        dcc.Store(id='asia-table-granularity-store', data='YEARLY'),
        
        # Download components
        dcc.Download(id="download-asia-imports-chart-csv"),
        dcc.Download(id="download-asia-imports-map-csv"),
        dcc.Download(id="download-asia-imports-table-csv"),
        
        # Main container with Flexbox for Content and Sidebar
        html.Div([
            
            # Content Area (Left side)
            html.Div([
                # Top Row: Chart and Map
                html.Div([
                    # Chart Section
                    html.Div([
                        html.H3(id='asia-imports-origin-chart-title', children="All Imports by Origin (Bcm)", style={
                            'color': EI_ORANGE, 'fontSize': '18px', 'fontWeight': 'normal', 
                            'margin': '10px 0', 'fontFamily': 'Lato, sans-serif'
                        }),
                        html.Div([
                            # Granularity Selector for Chart
                            create_asia_period_selector(),
                            html.Button("Export to CSV", id="export-asia-imports-chart-csv-btn", style=EXPORT_BTN_STYLE)
                        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
                        
                        dcc.Loading(
                            id='loading-asia-imports-chart',
                            type='circle',
                            color=EI_ORANGE,
                            children=dcc.Graph(
                                id='asia-imports-bar-chart',
                                style={'height': '500px'},
                                config={'displayModeBar': False}
                            )
                        )
                    ], id='asia-chart-container', style={'width': '50%', 'padding': '10px', 'backgroundColor': 'white'}),
                    
                    # Map Section
                    html.Div([
                        html.H3(id='asia-imports-yearly-map-title', children="All Imports by Origin (Bcm) - 2025", style={
                            'color': EI_ORANGE, 'fontSize': '18px', 'fontWeight': 'normal', 
                            'margin': '10px 0', 'fontFamily': 'Lato, sans-serif'
                        }),
                        html.Div([
                           html.Button("Export to CSV", id="export-asia-imports-map-csv-btn", style=EXPORT_BTN_STYLE)
                        ], style={'textAlign': 'right', 'marginBottom': '10px'}),
                        dcc.Loading(
                            id='loading-asia-imports-yearly-map',
                            type='circle',
                            color=EI_ORANGE,
                            children=dcc.Graph(
                                id='asia-imports-yearly-map',
                                style={'height': '500px'},
                                config={'displayModeBar': False}
                            )
                        )
                    ], id='asia-map-container', style={'width': '50%', 'padding': '10px', 'backgroundColor': 'white'}),
                ], style={'display': 'flex', 'flexDirection': 'row', 'marginBottom': '20px'}),
                
                # Bottom Row: Table
                html.Div([
                    html.H3(id='asia-table-title', children="Total Annual Imports by Destination Bcm - All", style={
                        'color': EI_ORANGE, 'fontSize': '18px', 'fontWeight': 'normal', 
                        'margin': '10px 0', 'fontFamily': 'Lato, sans-serif'
                    }),
                    html.Div([
                        create_asia_table_period_selector(),
                        html.Button("Export to CSV", id="export-asia-imports-table-csv-btn", style=EXPORT_BTN_STYLE)
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
                    dcc.Loading(
                        id='loading-asia-imports-table',
                        type='circle',
                        color=EI_ORANGE,
                        children=html.Div(id='asia-imports-table-container')
                    )
                ], style={'padding': '10px', 'backgroundColor': 'white'})
                
            ], style={'flex': '1', 'minWidth': '0'}),
            
            # Sidebar Filter (Right side)
            html.Div([
                html.Div([
                    # Unit Filter
                    html.Label("Unit", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': '#777', 'marginTop': '10px'}),
                    dcc.RadioItems(
                        id='asia-unit-filter',
                        options=[{'label': ' Bcm', 'value': 'Bcm'}, {'label': ' GWh', 'value': 'GWh'}],
                        value='Bcm',
                        labelStyle={'display': 'block', 'fontSize': '12px', 'color': '#555', 'marginBottom': '5px'}
                    ),
                    
                    # Flow Type Filter
                    html.Label("Flow Type", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': '#777', 'marginTop': '20px'}),
                    dcc.RadioItems(
                        id='asia-flow-type-filter',
                        options=[
                            {'label': ' (All)', 'value': ' '},
                            {'label': ' LNG', 'value': 'lng'},
                            {'label': ' Pipeline', 'value': 'natural gas'}
                        ],
                        value=' ',
                        labelStyle={'display': 'block', 'fontSize': '12px', 'color': '#555', 'marginBottom': '5px'}
                    ),
                    
                    # Destination Dropdown
                    html.Label("Destination", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': '#777', 'marginTop': '20px'}),
                    dcc.Dropdown(
                        id='asia-destination-dropdown',
                        options=[{'label': '(All)', 'value': '(All)'}],
                        value='(All)',
                        clearable=False,
                        style={'fontSize': '12px', 'marginBottom': '10px'}
                    ),
                    
                    # Origin Dropdown
                    html.Label("Origin", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': '#777', 'marginTop': '20px'}),
                    dcc.Dropdown(
                        id='asia-origin-dropdown',
                        options=[{'label': '(All)', 'value': '(All)'}],
                        value='(All)',
                        clearable=False,
                        style={'fontSize': '12px', 'marginBottom': '10px'}
                    ),
                    
                    # Legend Area
                    html.Div([
                        html.Label("Origin", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': '#777', 'marginTop': '20px', 'display': 'block'}),
                        html.Div(id='asia-origin-legend-items', style={'maxHeight': '400px', 'overflowY': 'auto', 'padding': '5px'})
                    ])
                    
                ], style={'padding': '15px', 'backgroundColor': '#fcfcfc', 'borderLeft': '1px solid #eee', 'height': '100%'})
            ], style={'width': '220px', 'minWidth': '220px'})
            
        ], style={'display': 'flex', 'padding': '10px'})
    ], className='tab-content', style={'backgroundColor': '#ffffff', 'minHeight': '100vh'})

def register_callbacks(dash_app, server):
    """Register all callbacks for Asian Yearly Imports"""
    
    @dash_app.callback(
        [Output('asia-destination-dropdown', 'options'),
         Output('asia-origin-dropdown', 'options')],
        [Input('asia-unit-filter', 'value')]
    )
    def update_filter_options(_):
        print("Asia: update_filter_options started")
        # Query destinations directly from dim_country for performance
        dest_query = """
        SELECT DISTINCT country_long_name as target_country
        FROM dim_country
        WHERE LOWER(region) IN ('asia', 'oceania')
        ORDER BY target_country;
        """
        # Query origins from dim_country (global origins)
        origin_query = """
        SELECT DISTINCT country_long_name as source_country
        FROM dim_country
        WHERE country_long_name IS NOT NULL
        ORDER BY source_country;
        """
        
        try:
            dest_results = execute_query(dest_query)
            origin_results = execute_query(origin_query)
            
            dest_options = [{'label': '(All)', 'value': '(All)'}] + \
                           [{'label': r['target_country'], 'value': r['target_country']} for r in dest_results]
            origin_options = [{'label': '(All)', 'value': '(All)'}] + \
                            [{'label': r['source_country'], 'value': r['source_country']} for r in origin_results]
            
            print(f"Asia: options loaded. Dests: {len(dest_options)}, Origins: {len(origin_options)}")
            return dest_options, origin_options
        except Exception as e:
            print(f"Error loading filter options: {e}")
            return no_update, no_update

    @dash_app.callback(
        [Output('asia-chart-granularity-store', 'data'),
         Output('asia-toggle-year-btn', 'children'),
         Output('asia-toggle-quarter-btn', 'children'),
         Output('asia-toggle-month-btn', 'children'),
         Output('asia-toggle-day-btn', 'children'),
         Output('asia-toggle-year-btn', 'style'),
         Output('asia-toggle-quarter-btn', 'style'),
         Output('asia-toggle-month-btn', 'style'),
         Output('asia-toggle-day-btn', 'style')],
        [Input('asia-toggle-year-btn', 'n_clicks'),
         Input('asia-toggle-quarter-btn', 'n_clicks'),
         Input('asia-toggle-month-btn', 'n_clicks'),
         Input('asia-toggle-day-btn', 'n_clicks')],
        [State('asia-chart-granularity-store', 'data')]
    )
    def toggle_asia_chart_granularity(y_c, q_c, m_c, d_c, current_gran):
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
        btn_id = ctx.triggered_id
        new_gran = current_gran
        
        if btn_id == 'asia-toggle-year-btn': new_gran = 'year'
        elif btn_id == 'asia-toggle-quarter-btn': new_gran = 'quarter'
        elif btn_id == 'asia-toggle-month-btn': new_gran = 'month'
        elif btn_id == 'asia-toggle-day-btn': new_gran = 'day'
        
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

    @dash_app.callback(
        [Output('asia-table-granularity-store', 'data'),
         Output('asia-imports-table-toggle-year-btn', 'children'),
         Output('asia-imports-table-toggle-quarter-btn', 'children'),
         Output('asia-imports-table-toggle-month-btn', 'children'),
         Output('asia-imports-table-toggle-day-btn', 'children'),
         Output('asia-imports-table-toggle-year-btn', 'style'),
         Output('asia-imports-table-toggle-quarter-btn', 'style'),
         Output('asia-imports-table-toggle-month-btn', 'style'),
         Output('asia-imports-table-toggle-day-btn', 'style')],
        [Input('asia-imports-table-toggle-year-btn', 'n_clicks'),
         Input('asia-imports-table-toggle-quarter-btn', 'n_clicks'),
         Input('asia-imports-table-toggle-month-btn', 'n_clicks'),
         Input('asia-imports-table-toggle-day-btn', 'n_clicks')],
        [State('asia-table-granularity-store', 'data')]
    )
    def toggle_asia_table_granularity(y, q, m, d, current_gran):
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
        
        btn_id = ctx.triggered_id
        new_gran = current_gran
        
        if btn_id == 'asia-imports-table-toggle-year-btn': new_gran = 'YEARLY'
        elif btn_id == 'asia-imports-table-toggle-quarter-btn': new_gran = 'QUARTERLY'
        elif btn_id == 'asia-imports-table-toggle-month-btn': new_gran = 'MONTHLY'
        elif btn_id == 'asia-imports-table-toggle-day-btn': new_gran = 'DAILY'
        
        return (
            new_gran,
            '-' if new_gran == 'YEARLY' else '+',
            '-' if new_gran == 'QUARTERLY' else '+',
            '-' if new_gran == 'MONTHLY' else '+',
            '-' if new_gran == 'DAILY' else '+',
            GRAN_BTN_ACTIVE if new_gran == 'YEARLY' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'QUARTERLY' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'MONTHLY' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'DAILY' else GRAN_BTN_INACTIVE
        )

    @dash_app.callback(
        [Output('asia-imports-bar-chart', 'figure'),
         Output('asia-imports-origin-chart-title', 'children'),
         Output('asia-chart-container', 'style'),
         Output('asia-map-container', 'style')],
        [Input('asia-unit-filter', 'value'),
         Input('asia-flow-type-filter', 'value'),
         Input('asia-origin-dropdown', 'value'),
         Input('asia-destination-dropdown', 'value'),
         Input('asia-chart-granularity-store', 'data')]
    )
    def update_asia_bar_chart(unit, flow_type, origin, destination, granularity):
        chart_title = f"All Imports by Origin ({unit})"
        # Default styles (50/50 split)
        chart_style = {'width': '50%', 'padding': '10px', 'backgroundColor': 'white'}
        map_style = {'width': '50%', 'padding': '10px', 'backgroundColor': 'white'}
        
        # Unit and Scale
        chart_data_unit = 'Mcm' if unit == 'Bcm' else 'GWh'
        chart_scale = 1000.0 if unit == 'Bcm' else 1.0
        
        # Broaden chart for Month/Day views
        if granularity in ('month', 'day'):
            chart_style['width'] = '75%'
            map_style['width'] = '25%'

        try:
            # Re-generate clauses using f-strings for maximum compatibility (like table callback)
            f_flow_clause = f"AND tr.flow_type = '{flow_type}'" if flow_type != ' ' else ""
            f_origin_clause = f"AND tr.source_country = '{origin}'" if origin != '(All)' else ""
            f_dest_clause = f"AND tr.target_country = '{destination}'" if destination != '(All)' else ""

            query = f"""
            SELECT
                EXTRACT(YEAR FROM tr.date)::int AS "Year of Date",
                CASE
                    WHEN '{granularity}' IN ('quarter', 'month', 'day') 
                    THEN 'Q' || EXTRACT(QUARTER FROM tr.date)::int 
                    ELSE NULL 
                END AS "Quarter of Date",
                CASE
                    WHEN '{granularity}' IN ('month', 'day') 
                    THEN TO_CHAR(tr.date, 'Mon') 
                    ELSE NULL 
                END AS "Month of Date",
                CASE
                    WHEN '{granularity}' = 'day' 
                    THEN EXTRACT(DAY FROM tr.date)::int 
                    ELSE NULL 
                END AS "Day of Date",
                tr.target_country  AS "Destination",
                tr.source_country  AS "Origin",
                '{unit}'           AS "Unit",
                ROUND(SUM(tr.value / {chart_scale}), 9) AS "Value"
            FROM glng_gas_trade tr
            LEFT JOIN dim_country co ON co.dim_country_id = tr.target_country_id
            WHERE tr.unit = '{chart_data_unit}'
              AND (LOWER(co.region) IN ('asia', 'oceania') OR co.country_long_name IS NULL)
              AND EXTRACT(YEAR FROM tr.date) >= 2019
              {f_flow_clause}
              {f_origin_clause}
              {f_dest_clause}
            GROUP BY
                EXTRACT(YEAR FROM tr.date),
                CASE
                    WHEN '{granularity}' IN ('quarter', 'month', 'day') 
                    THEN 'Q' || EXTRACT(QUARTER FROM tr.date)::int 
                    ELSE NULL 
                END,
                CASE
                    WHEN '{granularity}' IN ('month', 'day') 
                    THEN TO_CHAR(tr.date, 'Mon') 
                    ELSE NULL 
                END,
                CASE
                    WHEN '{granularity}' = 'day' 
                    THEN EXTRACT(DAY FROM tr.date)::int 
                    ELSE NULL 
                END,
                tr.target_country,
                tr.source_country
            ORDER BY
                "Year of Date" ASC, 
                "Quarter of Date" ASC, 
                "Month of Date" ASC, 
                "Day of Date" ASC, 
                "Value" DESC;
            """
            
            results = execute_query(query)
            df = pd.DataFrame(results)
            if df.empty: return go.Figure(), chart_style, map_style

            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
            df = df.dropna(subset=['Value', 'Destination', 'Origin']).copy()
            if df.empty: return go.Figure(), chart_style, map_style

            # 1. Filter to Top 8 Destinations
            top_dest = df.groupby('Destination')['Value'].sum().sort_values(ascending=False).head(8).index.tolist()
            df = df[df['Destination'].isin(top_dest)].copy()
            if df.empty: return go.Figure(), chart_style, map_style

            # 2. Origin grouping
            origin_vols = df.groupby('Origin')['Value'].sum().sort_values(ascending=False)
            top_origins = origin_vols.head(15).index.tolist()
            df['Origin_Plot'] = df['Origin'].apply(lambda x: x if x in top_origins else 'Others')

            # 3. Faceting Key (Hierarchical)
            def create_facet_label(row):
                yr = row['Year of Date']
                q = row['Quarter of Date']
                m = row['Month of Date']
                d = row['Day of Date']
                return f"{yr}|{q or ''}|{m or ''}|{d or ''}"

            df['Facet_Key'] = df.apply(create_facet_label, axis=1)

            # Sorting
            time_cols = ['Year of Date', 'Quarter of Date', 'Month of Date', 'Day of Date']
            time_order = df[time_cols + ['Facet_Key']].drop_duplicates()
            month_map = {m: i for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])}
            time_order['Month_Num'] = time_order['Month of Date'].map(month_map).fillna(0)
            time_order = time_order.sort_values(['Year of Date', 'Quarter of Date', 'Month_Num', 'Day of Date'])
            facet_categories = time_order['Facet_Key'].tolist()

            chart_df = df.groupby(['Facet_Key'] + time_cols + ['Destination', 'Origin_Plot', 'Unit'], dropna=False)['Value'].sum().reset_index()

            # Spacing
            f_spacing = 0.003 if granularity in ('month', 'day') else 0.012

            # Create Chart
            fig = px.bar(
                chart_df,
                x='Destination',
                y='Value',
                color='Origin_Plot',
                facet_col='Facet_Key',
                facet_col_spacing=f_spacing,
                color_discrete_map=ORIGIN_COLORS,
                category_orders={'Destination': top_dest, 'Facet_Key': facet_categories},
                hover_data=['Year of Date', 'Quarter of Date', 'Month of Date', 'Day of Date', 'Unit'],
                template='plotly_white'
            )

            # Fallback for missing colors (like Fig 1/2)
            fig.update_traces(marker_line_width=0)

            # Tooltip Fig 3 / 4 style
            def get_hovertemplate(gran):
                base = "Origin: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>%{fullData.name}</b><br>"
                base += "Destination: &nbsp;&nbsp;&nbsp;&nbsp;<b>%{x}</b><br>"
                base += "Year of Date: &nbsp;&nbsp;<b>%{customdata[0]}</b><br>"
                if gran in ('quarter', 'month', 'day'):
                    base += "Quarter: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>%{customdata[1]}</b><br>"
                if gran in ('month', 'day'):
                    base += "Month: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>%{customdata[2]}</b><br>"
                if gran == 'day':
                    base += "Day: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>%{customdata[3]}</b><br>"
                base += "Unit: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>%{customdata[4]}</b><br>"
                base += "Value: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>%{y:,.0f}</b><extra></extra>"
                return base

            fig.update_traces(hovertemplate=get_hovertemplate(granularity))

            # Spacing for triple headers
            t_margin = 135 if granularity in ('month', 'day') else (120 if granularity == 'quarter' else 110)
            
            fig.update_layout(
                margin=dict(l=60, r=20, t=t_margin, b=120),
                showlegend=False,
                height=550,
                font=dict(family="Lato, sans-serif"),
                barmode='stack',
                xaxis_title=None,
                yaxis_title=None,
                yaxis=dict(autorange=True)
            )

            fig.update_xaxes(type='category', tickangle=-90, tickfont=dict(size=9), title=None, gridcolor='#f0f0f0')
            fig.update_yaxes(tickformat="~s", gridcolor='#f0f0f0', nticks=10)
            # Replace lowercase 'k' with 'K' in ticks if possible? 
            # Actually ~s is automatic. Let's try .3s or similar.

            # Triple Headers Logic (Fig 2 sketch)
            seen_years = {}
            seen_quarters = {}
            def format_annotation(a):
                if not a.text: return
                try:
                    full_val = a.text.split("=")[-1]
                    parts = full_val.split("|")
                    if len(parts) < 3: return
                    yr, q, m = parts[0], parts[1], parts[2]
                    
                    label = ""
                    # Row 1: Year
                    if yr not in seen_years:
                        label += f"<b>{yr}</b><br>"
                        seen_years[yr] = True
                    else:
                        label += "<br>" 

                    # Row 2: Quarter
                    q_key = f"{yr}-{q}"
                    if q and q_key not in seen_quarters:
                        label += f"<b>{q}</b><br>"
                        seen_quarters[q_key] = True
                    elif q:
                        label += "<br>"
                    
                    # Row 3: Month
                    if granularity == 'month': label += f"{m}"
                    elif granularity == 'quarter': label += ""
                    elif granularity == 'year': label = f"<b>{yr}</b>"

                    a.update(text=label, font=dict(size=9, color=EI_DARK_BLUE), y=1.02, yanchor='bottom')
                except:
                    pass

            fig.for_each_annotation(format_annotation)
            return fig, chart_title, chart_style, map_style
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return go.Figure(), chart_title, chart_style, map_style

    @dash_app.callback(
        [Output('asia-imports-yearly-map', 'figure'),
         Output('asia-imports-yearly-map-title', 'children'),
         Output('asia-origin-dropdown', 'value', allow_duplicate=True)],
        [Input('asia-unit-filter', 'value'),
         Input('asia-flow-type-filter', 'value'),
         Input('asia-destination-dropdown', 'value'),
         Input('asia-origin-dropdown', 'value'),
         Input('asia-imports-yearly-map', 'clickData')],
        [State('asia-origin-dropdown', 'options')],
        prevent_initial_call='initial_duplicate'
    )
    def update_asia_map(unit, flow_type, dest, origins, click_data, origin_options):
        title = f"All Imports by Origin ({unit}) - 2025"
        # 1. Handle Map Reset
        if ctx.triggered_id == 'asia-imports-yearly-map':
            all_origin_vals = [opt['value'] for opt in origin_options]
            new_origins = handle_map_click_reset(click_data, origins, all_origin_vals, "(All)")
            if new_origins != origins:
                # If reset, handle_map_click_reset returns the new (All) list
                # But we need to update the dropdown value
                # Usually we just return '(All)' if it was a reset to all
                if '(All)' in new_origins:
                    return no_update, no_update, '(All)'
                return no_update, no_update, new_origins

        # 2. Build Query for 2025
        # Convert Unit
        data_unit = 'Mcm' if unit == 'Bcm' else 'GWh'
        scale = 1000.0 if unit == 'Bcm' else 1.0

        flow_clause = ""
        if flow_type == 'lng': flow_clause = "AND tr.flow_type = 'lng'"
        elif flow_type == 'natural gas': flow_clause = "AND tr.flow_type = 'natural gas'"
        
        origin_clause = ""
        if origins and "(All)" not in origins:
            if isinstance(origins, list):
                origin_clause = "AND tr.source_country = ANY(:origins)"
            else:
                origin_clause = f"AND tr.source_country = '{origins}'"
            
        dest_clause = ""
        if dest and "(All)" not in dest:
            dest_clause = "AND tr.target_country = :dest"

        query = f"""
        SELECT 
            tr.source_country as origin,
            SUM(tr.value / {scale}) as total_value
        FROM glng_gas_trade tr
        LEFT JOIN dim_country co ON co.dim_country_id = tr.target_country_id
        WHERE EXTRACT(YEAR FROM tr.date) = 2025
          AND tr.unit = '{data_unit}'
          AND (LOWER(co.region) IN ('asia', 'oceania') OR co.country_long_name IS NULL)
          {flow_clause}
          {origin_clause}
          {dest_clause}
        GROUP BY origin
        """
        
        try:
            results = execute_query(query, {'origins': [origins] if isinstance(origins, str) else origins, 'dest': dest})
            df = pd.DataFrame(results)
            
            if df.empty:
                from app.dashboards.wcod.shared_map_utils import create_empty_map
                return create_empty_map("No data available for 2025", height=500), title, no_update

            # Ensure numeric and rename for convenience
            df['Value'] = df['total_value'].astype(float)
            
            # Get ISO codes
            iso_query = "SELECT country_long_name as origin, country_code FROM dim_country WHERE country_code IS NOT NULL"
            iso_results = execute_query(iso_query)
            iso_map = {r['origin']: r['country_code'] for r in iso_results}
            
            df['iso'] = df['origin'].map(iso_map)
            df = df.dropna(subset=['iso'])
            
            if df.empty:
                from app.dashboards.wcod.shared_map_utils import create_empty_map
                return create_empty_map("No geographic data for these origins", height=500), title, no_update

            geojson = load_world_geojson()
            
            # 1. Colorscale (Blue tones to match Fig 1)
            colorscale = [[0, '#e3f2fd'], [0.1, '#bbdefb'], [0.4, '#64b5f6'], [0.7, '#2196f3'], [1, '#1b365d']]
            
            # 2. Selection handling
            selected_name = None
            selected_iso = None
            other_isos = []
            
            if origins and "(All)" not in origins:
                if isinstance(origins, list) and len(origins) == 1:
                    selected_name = origins[0]
                    selected_iso = iso_map.get(selected_name)
                elif isinstance(origins, str):
                    selected_name = origins
                    selected_iso = iso_map.get(selected_name)
                
                if selected_iso:
                    other_isos = [iso for iso in df['iso'].tolist() if iso != selected_iso]

            fig = go.Figure()

            # Add background click layer for reset behavior
            from app.dashboards.wcod.shared_map_utils import add_background_click_layer
            add_background_click_layer(fig, selected_name, use_mapbox=True)

            # Main Choropleth Layer
            fig.add_trace(go.Choroplethmapbox(
                geojson=geojson,
                locations=df['iso'],
                z=df['Value'],
                colorscale=colorscale,
                showscale=False,
                marker_opacity=0.8,
                marker_line_width=0.5,
                marker_line_color='white',
                # Custom Hover Template
                hovertemplate=(
                    "Origin: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>%{customdata[0]}</b><br>"
                    "Year of Date: &nbsp;&nbsp;<b>2025</b><br>"
                    "Value: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>%{z:,.2f}</b><br>"
                    f"Unit: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>{unit}</b><extra></extra>"
                ),
                customdata=df[['origin']].values.tolist(),
                name="countries"
            ))

            # Add Selection Highlight (dim others)
            if selected_iso:
                from app.dashboards.wcod.shared_map_utils import add_selection_highlight
                add_selection_highlight(fig, geojson, selected_iso, selected_name, other_isos, use_mapbox=True)

            # Layout adjustments for Mapbox
            fig.update_layout(
                mapbox=dict(
                    style='carto-positron',
                    center=dict(lat=20, lon=100),
                    zoom=1.2
                ),
                margin=dict(l=0, r=0, t=0, b=0),
                height=500,
                hoverlabel=dict(
                    bgcolor="white",
                    bordercolor="#ccc",
                    font=dict(size=12, color="#333", family="Lato, sans-serif"),
                    align="left"
                )
            )
            
            return fig, title, no_update
            
        except Exception as e:
            print(f"Asia ERROR: update_asia_map failed: {e}")
            import traceback
            traceback.print_exc()
            from app.dashboards.wcod.shared_map_utils import create_error_figure
            return create_error_figure(str(e), height=500), title, no_update

    @dash_app.callback(
        [Output('asia-imports-table-container', 'children'),
         Output('asia-table-title', 'children')],
        [Input('asia-unit-filter', 'value'),
         Input('asia-flow-type-filter', 'value'),
         Input('asia-origin-dropdown', 'value'),
         Input('asia-destination-dropdown', 'value'),
         Input('asia-table-granularity-store', 'data')]
    )
    def update_asia_table(unit, flow_type, origin, destination, granularity):
        print(f"Asia: update_asia_table started: {unit}, {flow_type}, {origin}, {destination}, {granularity}")
        
        # 1. Build Query
        dest_clause = ""
        if destination != '(All)':
            dest_clause = f"AND tr.target_country = '{destination}'"

        origin_clause = ""
        if origin != '(All)':
            origin_clause = f"AND tr.source_country = '{origin}'"

        flow_clause = ""
        if flow_type != ' ':
            flow_clause = f"AND tr.flow_type = '{flow_type}'"

        data_unit = 'Mcm' if unit == 'Bcm' else 'GWh'
        scale = 1000.0 if unit == 'Bcm' else 1.0

        query = f"""
        WITH params AS (
            SELECT '{granularity}'::text AS period   -- DAILY | MONTHLY | QUARTERLY | YEARLY
        ),
        base AS (
            SELECT
                tr.target_country                                      AS "Destination",

                EXTRACT(YEAR FROM tr.date)::int                        AS "Year of Date",

                CASE
                    WHEN p.period IN ('QUARTERLY', 'MONTHLY', 'DAILY')
                    THEN 'Q' || EXTRACT(QUARTER FROM tr.date)::int
                END                                                    AS "Quarter of Date",

                CASE
                    WHEN p.period IN ('MONTHLY', 'DAILY')
                    THEN TO_CHAR(tr.date, 'FMMonth')
                END                                                    AS "Month of Date",

                CASE
                    WHEN p.period = 'DAILY'
                    THEN EXTRACT(DAY FROM tr.date)::int
                END                                                    AS "Day of Date",

                '{unit}'                                               AS "Unit",

                tr.value / {scale}                                     AS bcm_value

            FROM glng_gas_trade tr
            LEFT JOIN dim_country co
                ON co.dim_country_id = tr.target_country_id
            CROSS JOIN params p

            WHERE tr.unit = '{data_unit}'
              AND LOWER(co.region) IN ('asia', 'oceania')
              AND EXTRACT(YEAR FROM tr.date) >= 2019
              {dest_clause}
              {origin_clause}
              {flow_clause}
        )

        SELECT
            "Destination",
            "Year of Date",
            "Quarter of Date",
            "Month of Date",
            "Day of Date",
            "Unit",
            ROUND(SUM(bcm_value), 9) AS "Value"

        FROM base
        GROUP BY
            "Destination",
            "Year of Date",
            "Quarter of Date",
            "Month of Date",
            "Day of Date",
            "Unit"

        ORDER BY
            "Destination" ASC,
            "Year of Date" DESC;
        """
        
        try:
            results = execute_query(query)
            print(f"Asia: table query returned {len(results)} rows")
            df = pd.DataFrame(results)
            if df.empty:
                return html.Div("No data available", style={'color': '#666', 'padding': '20px'}), f"Total Annual Imports by Destination {unit}"

            # Ensure Value is numeric
            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
            
            # Month sorting helper
            month_map = {m: i for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'])}
            df['Month_Num'] = df['Month of Date'].map(month_map).fillna(0)

            # Determine pivot columns based on granularity
            pivot_index = 'Destination'
            if granularity == 'YEARLY':
                pivot_cols = ['Year of Date']
                sort_cols = ['Year of Date']
            elif granularity == 'QUARTERLY':
                pivot_cols = ['Year of Date', 'Quarter of Date']
                sort_cols = ['Year of Date', 'Quarter of Date']
            elif granularity == 'MONTHLY':
                pivot_cols = ['Year of Date', 'Quarter of Date', 'Month of Date']
                sort_cols = ['Year of Date', 'Quarter of Date', 'Month_Num']
            elif granularity == 'DAILY':
                pivot_cols = ['Year of Date', 'Quarter of Date', 'Month of Date', 'Day of Date']
                sort_cols = ['Year of Date', 'Quarter of Date', 'Month_Num', 'Day of Date']
            
            # Sort before pivoting to ensure column order
            df = df.sort_values(sort_cols, ascending=[False] + [True] * (len(sort_cols)-1))
            
            # Pivot
            pivot_df = df.pivot_table(index=pivot_index, columns=pivot_cols, values='Value', aggfunc='sum')
            
            # Flatten columns for DataTable
            # If multi-level, columns will be a MultiIndex
            if len(pivot_cols) > 1:
                # We need to construct columns carefully
                # Expected structure is something that DataTable can consume or we pre-format headers
                # Dash DataTable supports multi-header via 'name' as a list
                
                # Sort columns descending by Year, then Ascending by Q/M/D? Reference Fig 2/3 shows:
                # 2025 (Q1, Q2..), 2024..
                # Actually typically time goes Left to Right or Right to Left.
                # User request: "2025, 2024, 2023..." (Descending Year)
                # Within Year: "Q1, Q2, Q3, Q4" (Ascending Quarter?)
                # Looking at Fig3 provided in prompt:
                # 2025 (Q1, Q2, Q3, Q4) | 2024 (Q1, Q2...)
                # It seems years are descending, but sub-periods are ascending.
                
                # Let's sort the columns explicitly
                # We can't easily sort a MultiIndex with mixed directions (Desc Year, Asc Quarter)
                # So we sort the flattened tuples
                
                col_tuples = pivot_df.columns.to_list()
                
                def sort_key(tup):
                    # Year is index 0 (desc), others are asc
                    yr = tup[0]
                    rest = tup[1:]
                    # We want to reverse year for sorting? 
                    # Easier: negate year for sort if it's int
                    return (-int(yr),) + rest 
                
                # Note: Month is string, so we need month num for sorting if using MONTHLY/DAILY
                # But here we only have the strings in the column usage
                # We might need to re-sort carefully
                 
                # Re-sorting logic:
                # Extract unique combinations from df sorted by `sort_cols` earlier
                unique_cols_df = df[list(set(pivot_cols + sort_cols))].drop_duplicates().sort_values(by=sort_cols, ascending=[False] + [True] * (len(sort_cols)-1))
                sorted_cols = [tuple(row[col] for col in pivot_cols) for _, row in unique_cols_df.iterrows()]
                
                # Filter to only those present in pivot (though they should match)
                sorted_cols = [c for c in sorted_cols if c in pivot_df.columns]
                
                pivot_df = pivot_df[sorted_cols]
                
                # Destination Header with padding
                dest_header = [""] * (len(pivot_cols) - 1) + ["Destination"]
                dt_columns = [{'name': dest_header, 'id': 'Destination'}]
                
                for col_tuple in sorted_cols:
                    # col_tuple is (Year, Quarter, Month...)
                    # We build the name list. All elements must be strings.
                    name_list = [str(x) for x in col_tuple]
                    # col_id must be a clean string to avoid tooltip issues
                    col_id = "col_" + "_".join([str(x).replace(" ", "") for x in col_tuple])
                    dt_columns.append({'name': name_list, 'id': col_id})
            
            else:
                # Single level (YEARLY)
                # Sort columns descending
                cols = sorted(pivot_df.columns.tolist(), reverse=True)
                pivot_df = pivot_df[cols]
                dt_columns = [{'name': 'Destination', 'id': 'Destination'}] + \
                             [{'name': str(col), 'id': "col_" + str(col)} for col in cols]

            # Re-map pivot_df columns to match dt_columns IDs
            if len(pivot_cols) > 1:
                pivot_df.columns = ["col_" + "_".join([str(x).replace(" ", "") for x in c]) for c in pivot_df.columns]
            else:
                pivot_df.columns = ["col_" + str(c) for c in pivot_df.columns]
                
            pivot_df = pivot_df.reset_index()
            data = pivot_df.to_dict('records')
            
            # Format values
            for row in data:
                for k, v in row.items():
                    if k != 'Destination' and pd.notnull(v):
                        try:
                            # Use comma separator for thousands
                            val_float = float(v)
                            # If it's a whole number, don't show decimals (GWh usually large)
                            if val_float == int(val_float):
                                row[k] = f"{int(val_float):,}"
                            else:
                                row[k] = f"{val_float:,.2f}"
                        except:
                            pass
                    if pd.isnull(v):
                         row[k] = ""

            # 4. Generate Tooltips
            tooltip_data = []
            for row in data:
                row_tooltips = {}
                dest = row.get('Destination', '')
                for col in dt_columns:
                    col_id = col['id']
                    if col_id == 'Destination':
                        continue
                        
                    val = row.get(col_id, '')
                    if val == "":
                        continue
                    
                    # Tooltip construction
                    tooltip_text = f"Destination: {dest}  \n"
                    
                    if isinstance(col['name'], list):
                        for i, name_val in enumerate(col['name']):
                            if name_val == "": continue
                            label = pivot_cols[i]
                            tooltip_text += f"{label}: {name_val}  \n"
                    else:
                        tooltip_text += f"Year of Date: {col['name']}  \n"
                    
                    tooltip_text += f"Unit: {unit}  \n"
                    tooltip_text += f"Value: {val}"
                    
                    row_tooltips[col_id] = {'value': tooltip_text, 'type': 'markdown'}
                tooltip_data.append(row_tooltips)
            
            # Construct DataTable
            table = dash_table.DataTable(
                data=data,
                columns=dt_columns,
                tooltip_data=tooltip_data,
                tooltip_delay=0,
                tooltip_duration=None,
                merge_duplicate_headers=True,
                fixed_rows={'headers': True},
                fixed_columns={'headers': True, 'data': 1},
                style_table={
                    'minWidth': '100%', 
                    'height': '600px', 
                    'overflowY': 'auto', 
                    'overflowX': 'auto', 
                    'border': '1px solid #ddd'
                },
                style_header={
                    'backgroundColor': '#ffffff',
                    'fontWeight': 'bold',
                    'textAlign': 'right',
                    'fontSize': '11px',
                    'border': 'none', 
                    'color': '#333',
                    'height': '25px',
                    'padding': '2px'
                },
                style_cell={
                    'padding': '0px 5px',
                    'fontSize': '11px',
                    'fontFamily': 'Arial, sans-serif',
                    'border': 'none', 
                    'minWidth': '70px',
                    'backgroundColor': '#fff',
                    'color': '#777',
                    'height': 'auto',
                    'textAlign': 'right'
                },
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#f9f9f9'}
                ],
                css=[{
                    'selector': '.dash-table-tooltip',
                    'rule': 'background-color: white !important; color: #333 !important; border: 1px solid #ccc !important; font-family: Arial, sans-serif !important; border-radius: 2px !important; padding: 10px !important; box-shadow: 2px 2px 8px rgba(0,0,0,0.1) !important; z-index: 1000 !important; visibility: visible !important; opacity: 1 !important; text-align: left !important; min-width: 150px !important;'
                }]
            )
            
            print(f"Asia Table: data rows={len(data)}, tooltip_data rows={len(tooltip_data)}")
            if tooltip_data:
                print(f"Asia Table: Sample tooltip keys: {list(tooltip_data[0].keys())}")
                print(f"Asia Table: Sample data keys: {list(data[0].keys())}")
            
            return table, f"Total Annual Imports by Destination {unit} - {granularity.title()}"

        except Exception as e:
            print(f"Error in update_asia_table: {e}")
            import traceback
            traceback.print_exc()
            return html.Div(f"Error loading table: {e}"), "Error"


    @dash_app.callback(
        Output('asia-origin-legend-items', 'children'),
        Input('asia-imports-bar-chart', 'figure')
    )
    def update_asia_legend(fig):
        print("Asia: update_asia_legend started")
        
        # Show all origins from our color map to match Fig 1's comprehensive legend
        sorted_origins = sorted(ORIGIN_COLORS.keys())
        
        items = []
        for origin in sorted_origins:
            color = ORIGIN_COLORS.get(origin, '#ccc')
            items.append(html.Div([
                html.Div(style={
                    'width': '10px', 'height': '10px', 'backgroundColor': color, 'marginRight': '6px', 'flexShrink': '0'
                }),
                html.Span(origin, style={'fontSize': '10px', 'color': '#333', 'whiteSpace': 'nowrap', 'overflow': 'hidden', 'textOverflow': 'ellipsis'})
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '2px'}))
        
        return items

    # --- Export Callbacks ---

    @dash_app.callback(
        Output("download-asia-imports-chart-csv", "data"),
        Input("export-asia-imports-chart-csv-btn", "n_clicks"),
        [State('asia-unit-filter', 'value'),
         State('asia-flow-type-filter', 'value'),
         State('asia-origin-dropdown', 'value'),
         State('asia-destination-dropdown', 'value'),
         State('asia-chart-granularity-store', 'data')],
        prevent_initial_call=True
    )
    def export_asia_chart_csv(n_clicks, unit, flow_type, origin, destination, granularity):
        if not n_clicks: return no_update
        
        chart_data_unit = 'Mcm' if unit == 'Bcm' else 'GWh'
        chart_scale = 1000.0 if unit == 'Bcm' else 1.0
        
        f_flow_clause = f"AND tr.flow_type = '{flow_type}'" if flow_type != ' ' else ""
        f_origin_clause = f"AND tr.source_country = '{origin}'" if origin != '(All)' else ""
        f_dest_clause = f"AND tr.target_country = '{destination}'" if destination != '(All)' else ""

        query = f"""
        SELECT
            EXTRACT(YEAR FROM tr.date)::int AS "Year of Date",
            CASE WHEN '{granularity}' IN ('quarter', 'month', 'day') THEN 'Q' || EXTRACT(QUARTER FROM tr.date)::int END AS "Quarter of Date",
            CASE WHEN '{granularity}' IN ('month', 'day') THEN TO_CHAR(tr.date, 'Mon') END AS "Month of Date",
            CASE WHEN '{granularity}' = 'day' THEN EXTRACT(DAY FROM tr.date)::int END AS "Day of Date",
            tr.target_country  AS "Destination",
            tr.source_country  AS "Origin",
            '{unit}'           AS "Unit",
            ROUND(SUM(tr.value / {chart_scale}), 9) AS "Value"
        FROM glng_gas_trade tr
        LEFT JOIN dim_country co ON co.dim_country_id = tr.target_country_id
        WHERE tr.unit = '{chart_data_unit}'
          AND (LOWER(co.region) IN ('asia', 'oceania') OR co.country_long_name IS NULL)
          AND EXTRACT(YEAR FROM tr.date) >= 2019
          {f_flow_clause}
          {f_origin_clause}
          {f_dest_clause}
        GROUP BY 1, 2, 3, 4, 5, 6, 7
        ORDER BY 1, 2, 3, 4, 8 DESC;
        """
        try:
            results = execute_query(query)
            df = pd.DataFrame(results)
            if df.empty: return dcc.send_string("No data found", "no_data.txt")
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            return dcc.send_data_frame(df.to_csv, f"asia_gas_imports_chart_{timestamp}.csv", index=False)
        except Exception as e:
            return dcc.send_string(f"Error: {e}", "error.txt")

    @dash_app.callback(
        Output("download-asia-imports-map-csv", "data"),
        Input("export-asia-imports-map-csv-btn", "n_clicks"),
        [State('asia-unit-filter', 'value'),
         State('asia-flow-type-filter', 'value'),
         State('asia-destination-dropdown', 'value'),
         State('asia-origin-dropdown', 'value')],
        prevent_initial_call=True
    )
    def export_asia_map_csv(n_clicks, unit, flow_type, dest, origins):
        if not n_clicks: return no_update
        data_unit = 'Mcm' if unit == 'Bcm' else 'GWh'
        scale = 1000.0 if unit == 'Bcm' else 1.0
        
        flow_clause = f"AND tr.flow_type = '{flow_type}'" if flow_type != ' ' else ""
        origin_clause = ""
        if origins and "(All)" not in origins:
            if isinstance(origins, list): origin_clause = "AND tr.source_country = ANY(:origins)"
            else: origin_clause = f"AND tr.source_country = '{origins}'"
        dest_clause = f"AND tr.target_country = :dest" if dest and "(All)" not in dest else ""

        query = f"""
        SELECT 
            tr.source_country as "Origin",
            '2025' as "Year",
            '{unit}' as "Unit",
            SUM(tr.value / {scale}) as "Total Value"
        FROM glng_gas_trade tr
        LEFT JOIN dim_country co ON co.dim_country_id = tr.target_country_id
        WHERE EXTRACT(YEAR FROM tr.date) = 2025
          AND tr.unit = '{data_unit}'
          AND (LOWER(co.region) IN ('asia', 'oceania') OR co.country_long_name IS NULL)
          {flow_clause}
          {origin_clause}
          {dest_clause}
        GROUP BY 1, 2, 3
        """
        try:
            results = execute_query(query, {'origins': [origins] if isinstance(origins, str) else origins, 'dest': dest})
            df = pd.DataFrame(results)
            if df.empty: return dcc.send_string("No data found", "no_data.txt")
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            return dcc.send_data_frame(df.to_csv, f"asia_gas_imports_map_{timestamp}.csv", index=False)
        except Exception as e:
            return dcc.send_string(f"Error: {e}", "error.txt")

    @dash_app.callback(
        Output("download-asia-imports-table-csv", "data"),
        Input("export-asia-imports-table-csv-btn", "n_clicks"),
        [State('asia-unit-filter', 'value'),
         State('asia-flow-type-filter', 'value'),
         State('asia-origin-dropdown', 'value'),
         State('asia-destination-dropdown', 'value'),
         State('asia-table-granularity-store', 'data')],
        prevent_initial_call=True
    )
    def export_asia_table_csv(n_clicks, unit, flow_type, origin, destination, granularity):
        if not n_clicks: return no_update
        
        dest_clause = f"AND tr.target_country = '{destination}'" if destination != '(All)' else ""
        origin_clause = f"AND tr.source_country = '{origin}'" if origin != '(All)' else ""
        flow_clause = f"AND tr.flow_type = '{flow_type}'" if flow_type != ' ' else ""
        data_unit = 'Mcm' if unit == 'Bcm' else 'GWh'
        scale = 1000.0 if unit == 'Bcm' else 1.0

        query = f"""
        SELECT
            tr.target_country                                      AS "Destination",
            EXTRACT(YEAR FROM tr.date)::int                        AS "Year of Date",
            CASE WHEN '{granularity}' IN ('QUARTERLY', 'MONTHLY', 'DAILY') THEN 'Q' || EXTRACT(QUARTER FROM tr.date)::int END AS "Quarter of Date",
            CASE WHEN '{granularity}' IN ('MONTHLY', 'DAILY') THEN TO_CHAR(tr.date, 'FMMonth') END AS "Month of Date",
            CASE WHEN '{granularity}' = 'DAILY' THEN EXTRACT(DAY FROM tr.date)::int END AS "Day of Date",
            '{unit}'                                               AS "Unit",
            ROUND(SUM(tr.value / {scale}), 9)                      AS "Value"
        FROM glng_gas_trade tr
        LEFT JOIN dim_country co ON co.dim_country_id = tr.target_country_id
        WHERE tr.unit = '{data_unit}'
          AND LOWER(co.region) IN ('asia', 'oceania')
          AND EXTRACT(YEAR FROM tr.date) >= 2019
          {dest_clause}
          {origin_clause}
          {flow_clause}
        GROUP BY 1, 2, 3, 4, 5, 6
        ORDER BY 1 ASC, 2 DESC;
        """
        try:
            results = execute_query(query)
            df = pd.DataFrame(results)
            if df.empty: return dcc.send_string("No data found", "no_data.txt")
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            return dcc.send_data_frame(df.to_csv, f"asia_gas_imports_table_{timestamp}.csv", index=False)
        except Exception as e:
            return dcc.send_string(f"Error: {e}", "error.txt")