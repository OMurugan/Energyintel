import os
import pandas as pd
from dash import dcc, html, dash_table, Input, Output, State, callback, callback_context, no_update
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from core.data_helpers import execute_query

# Data paths
DATA_DIR = "/home/ranjini/Documents/projects/energy-intelligence/Energyintel/app/dashboards/data/europe_gas_data_yearly"
CHART_DATA_PATH = os.path.join(DATA_DIR, "YoY Europe_data.csv")
TABLE_DATA_PATH = os.path.join(DATA_DIR, "Yoy table Europe_data.csv")

# Color mapping to match the reference image
SECTOR_COLORS = {
    'Power': '#bf5227',
    'Industrial': '#c0cf95',
    'Household': '#0075a8'
}

def hex_to_rgba(hex_color, opacity):
    hex_color = hex_color.lstrip('#')
    lv = len(hex_color)
    rgb = tuple(int(hex_color[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
    return f'rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {opacity})'

# Button Styles
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

def load_data():
    try:
        # Load chart data - keeping CSV for now if needed or can be removed if chart is fully SQL
        # Actually user said "remove the csv file of bar chart" in previous prompts, but we did that in update_chart.
        # Now user says "remove the csv ogf table".
        # So we can probably remove load_data entirely if we don't need it.
        # But let's check if df_chart_raw is used elsewhere.
        # It seems only used in update_chart if we fallback (which we don't anymore).
        # So I will return empty DFs.
        pass
        
        return pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_chart_raw, df_table_raw = load_data()

def create_layout():
    """Create the European Yearly Demand layout"""
    # Units and Sectors are now partially derived or fixed based on the query,
    # but for filters we might still want to load them once or keep them manual.
    units = ['Million Cubic Meter', 'GWh'] # Common units
    sectors = ['Household', 'Industrial', 'Power']
    
    # We still need countries for the table, which might still use CSV or also switch to SQL.
    # The user only asked to "remove the csv file of bar chart", so I'll keep table CSV for now if needed,
    # but I'll check if I can get countries from SQL easily.
    try:
        country_query = "SELECT DISTINCT country_long_name FROM dev.dim_country WHERE LOWER(region) = 'europe' ORDER BY 1"
        country_results = execute_query(country_query)
        countries = [r['country_long_name'] for r in country_results]
    except:
        countries = []

    return html.Div([
        dcc.Store(id='gas-europe-granularity-store', data='year'),
        dcc.Store(id='gas-europe-table-granularity-store', data='month'),
        dcc.Store(id='gas-demand-chart-selection', data=None),
        dcc.Download(id="gas-demand-europe-download-chart-csv"),
        dcc.Download(id="gas-demand-europe-download-table-csv"),
        
        # Header
        html.Div([
            html.H1(id='gas-demand-title', 
                    children="European Natural Gas Demand - Million Cubic Meter",
                    style={'color': '#fe5000', 'fontSize': '24px', 'fontWeight': 'normal', 
                           'fontFamily': 'Arial, sans-serif', 'margin': '0', 'padding': '10px 20px'})
        ], style={'borderBottom': '1px solid #ddd', 'backgroundColor': '#fff'}),

        html.Div([
            # Main Content (Left)
            html.Div([
                html.Div([
                    # Buttons Area
                    html.Div([
                        html.Div([
                            html.Span("Year of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                            html.Button('-', id='gas-europe-toggle-year-btn', n_clicks=0, style=GRAN_BTN_ACTIVE)
                        ], style=GRAN_BTN_CONTAINER_STYLE),
                        html.Div([
                            html.Span("Quarter of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                            html.Button('+', id='gas-europe-toggle-quarter-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                        ], style=GRAN_BTN_CONTAINER_STYLE),
                        html.Div([
                            html.Span("Month of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                            html.Button('+', id='gas-europe-toggle-month-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                        ], style=GRAN_BTN_CONTAINER_STYLE),
                        html.Div([
                            html.Span("Day of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                            html.Button('+', id='gas-europe-toggle-day-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                        ], style=GRAN_BTN_CONTAINER_STYLE),
                    ], style={'display': 'flex', 'padding': '10px 20px', 'backgroundColor': '#f8f9fa', 'alignItems': 'center'}),

                    html.Button("Export to CSV", id="gas-demand-europe-export-chart-csv-btn", 
                                style={**EXPORT_BTN_STYLE, 'position': 'absolute', 'top': '10px', 'right': '20px'}),

                    # Chart Area
                    html.Div([
                        dcc.Loading(
                            id='loading-gas-demand-chart',
                            type='circle',
                            children=dcc.Graph(id='gas-demand-chart', config={'displayModeBar': False})
                        )
                    ], style={'padding': '20px'}),
                ], style={'position': 'relative'}),
                
                # Table Area
                html.Div([
                    # Table Buttons Area
                    html.Div([
                        html.Div([
                            html.Span("Year of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                            html.Button('+', id='gas-europe-table-toggle-year-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                        ], style=GRAN_BTN_CONTAINER_STYLE),
                        html.Div([
                            html.Span("Quarter of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                            html.Button('+', id='gas-europe-table-toggle-quarter-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                        ], style=GRAN_BTN_CONTAINER_STYLE),
                        html.Div([
                            html.Span("Month of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                            html.Button('-', id='gas-europe-table-toggle-month-btn', n_clicks=0, style=GRAN_BTN_ACTIVE)
                        ], style=GRAN_BTN_CONTAINER_STYLE),
                        html.Div([
                            html.Span("Day of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                            html.Button('+', id='gas-europe-table-toggle-day-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                        ], style=GRAN_BTN_CONTAINER_STYLE),
                    ], style={'display': 'flex', 'padding': '10px 0', 'backgroundColor': '#fff', 'alignItems': 'center'}),
                    
                    html.Button("Export to CSV", id="gas-demand-europe-export-table-csv-btn", 
                                style={**EXPORT_BTN_STYLE, 'position': 'absolute', 'top': '10px', 'right': '20px'}),
                    
                    html.Div(id='gas-demand-table-container')
                ], style={'padding': '20px', 'overflowX': 'auto', 'maxHeight': '600px', 'overflowY': 'auto', 'position': 'relative'})
            ], style={'width': '80%', 'display': 'inline-block', 'verticalAlign': 'top'}),

            # Filters Sidebar (Right)
            html.Div([
                # Unit Filter
                html.Div([
                    html.Label("Unit", style={'fontWeight': 'bold', 'color': '#777', 'fontSize': '12px'}),
                    dcc.RadioItems(
                        id='unit-filter',
                        options=[{'label': u, 'value': u} for u in units],
                        value='Million Cubic Meter',
                        labelStyle={'display': 'block', 'fontSize': '12px', 'color': '#555'}
                    )
                ], style={'marginBottom': '20px'}),

                # Sector Filter
                html.Div([
                    html.Label("Sector", style={'fontWeight': 'bold', 'color': '#777', 'fontSize': '12px'}),
                    dcc.Checklist(
                        id='sector-filter-all',
                        options=[{'label': '(All)', 'value': 'all'}],
                        value=['all'],
                        labelStyle={'display': 'block', 'fontSize': '12px', 'color': '#555'}
                    ),
                    dcc.Checklist(
                        id='sector-filter',
                        options=[{'label': s, 'value': s} for s in sectors],
                        value=sectors,
                        labelStyle={'display': 'block', 'fontSize': '12px', 'color': '#555', 'marginLeft': '10px'}
                    )
                ], style={'marginBottom': '20px'}),

                # Country Filter
                html.Div([
                    html.Label("Country", style={'fontWeight': 'bold', 'color': '#777', 'fontSize': '12px'}),
                    dcc.Checklist(
                        id='country-filter-all',
                        options=[{'label': '(All)', 'value': 'all'}],
                        value=['all'],
                        labelStyle={'display': 'block', 'fontSize': '12px', 'color': '#555'}
                    ),
                    html.Div([
                        dcc.Checklist(
                            id='country-filter',
                            options=[{'label': c, 'value': c} for c in countries],
                            value=countries,
                            labelStyle={'display': 'block', 'fontSize': '12px', 'color': '#555', 'marginLeft': '10px'}
                        )
                    ], style={'maxHeight': '400px', 'overflowY': 'auto'}),
                ], style={'marginBottom': '20px'}),
                
                # Legend
                html.Div([
                    html.Label("Sector", style={'fontWeight': 'bold', 'color': '#777', 'fontSize': '12px'}),
                    html.Div([
                        html.Div([
                            html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': SECTOR_COLORS['Power'], 'display': 'inline-block', 'marginRight': '5px'}),
                            html.Span("Power", style={'fontSize': '12px', 'color': '#555'})
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px'}),
                        html.Div([
                            html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': SECTOR_COLORS['Industrial'], 'display': 'inline-block', 'marginRight': '5px'}),
                            html.Span("Industrial", style={'fontSize': '12px', 'color': '#555'})
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px'}),
                        html.Div([
                            html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': SECTOR_COLORS['Household'], 'display': 'inline-block', 'marginRight': '5px'}),
                            html.Span("Household", style={'fontSize': '12px', 'color': '#555'})
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px'}),
                    ])
                ], style={'borderTop': '2px solid #eee', 'paddingTop': '10px'})

            ], style={'width': '20%', 'display': 'inline-block', 'verticalAlign': 'top', 
                      'padding': '20px', 'backgroundColor': '#fff', 'borderLeft': '1px solid #ddd', 'minHeight': '100vh'})
        ], style={'display': 'flex'})
    ], style={'backgroundColor': '#fff', 'minHeight': '100vh', 'fontFamily': 'Arial, sans-serif'})

def register_callbacks(dash_app, server):
    
    # Granularity Toggle
    @dash_app.callback(
        [Output('gas-europe-granularity-store', 'data'),
         Output('gas-europe-toggle-year-btn', 'children'),
         Output('gas-europe-toggle-quarter-btn', 'children'),
         Output('gas-europe-toggle-month-btn', 'children'),
         Output('gas-europe-toggle-day-btn', 'children'),
         Output('gas-europe-toggle-year-btn', 'style'),
         Output('gas-europe-toggle-quarter-btn', 'style'),
         Output('gas-europe-toggle-month-btn', 'style'),
         Output('gas-europe-toggle-day-btn', 'style')],
        [Input('gas-europe-toggle-year-btn', 'n_clicks'),
         Input('gas-europe-toggle-quarter-btn', 'n_clicks'),
         Input('gas-europe-toggle-month-btn', 'n_clicks'),
         Input('gas-europe-toggle-day-btn', 'n_clicks')],
        [State('gas-europe-granularity-store', 'data')]
    )
    def toggle_granularity(y_c, q_c, m_c, d_c, current_gran):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
        btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
        new_gran = current_gran
        
        if btn_id == 'gas-europe-toggle-year-btn': new_gran = 'year'
        elif btn_id == 'gas-europe-toggle-quarter-btn': new_gran = 'quarter'
        elif btn_id == 'gas-europe-toggle-month-btn': new_gran = 'month'
        elif btn_id == 'gas-europe-toggle-day-btn': new_gran = 'day'
        
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
        [Output('gas-europe-table-granularity-store', 'data'),
         Output('gas-europe-table-toggle-year-btn', 'children'),
         Output('gas-europe-table-toggle-quarter-btn', 'children'),
         Output('gas-europe-table-toggle-month-btn', 'children'),
         Output('gas-europe-table-toggle-day-btn', 'children'),
         Output('gas-europe-table-toggle-year-btn', 'style'),
         Output('gas-europe-table-toggle-quarter-btn', 'style'),
         Output('gas-europe-table-toggle-month-btn', 'style'),
         Output('gas-europe-table-toggle-day-btn', 'style')],
        [Input('gas-europe-table-toggle-year-btn', 'n_clicks'),
         Input('gas-europe-table-toggle-quarter-btn', 'n_clicks'),
         Input('gas-europe-table-toggle-month-btn', 'n_clicks'),
         Input('gas-europe-table-toggle-day-btn', 'n_clicks')],
        [State('gas-europe-table-granularity-store', 'data')]
    )
    def toggle_table_granularity(y_c, q_c, m_c, d_c, current_gran):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
        btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
        new_gran = current_gran
        
        if btn_id == 'gas-europe-table-toggle-year-btn': new_gran = 'year'
        elif btn_id == 'gas-europe-table-toggle-quarter-btn': new_gran = 'quarter'
        elif btn_id == 'gas-europe-table-toggle-month-btn': new_gran = 'month'
        elif btn_id == 'gas-europe-table-toggle-day-btn': new_gran = 'day'
        
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


    # Sector filter sync
    @dash_app.callback(
        [Output('sector-filter', 'value'),
         Output('sector-filter-all', 'value')],
        [Input('sector-filter', 'value'),
         Input('sector-filter-all', 'value')],
        State('sector-filter', 'options'),
        prevent_initial_call=True
    )
    def sync_sector_filters(selected, all_selected, options):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update
            
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'sector-filter-all':
            if 'all' in all_selected:
                return [o['value'] for o in options], ['all']
            else:
                return [], []
        else:
            if len(selected) == len(options):
                return no_update, ['all']
            else:
                return no_update, []

    # Country filter sync
    @dash_app.callback(
        [Output('country-filter', 'value'),
         Output('country-filter-all', 'value')],
        [Input('country-filter', 'value'),
         Input('country-filter-all', 'value')],
        State('country-filter', 'options'),
        prevent_initial_call=True
    )
    def sync_country_filters(selected, all_selected, options):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update
            
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'country-filter-all':
            if 'all' in all_selected:
                return [o['value'] for o in options], ['all']
            else:
                return [], []
        else:
            if len(selected) == len(options):
                return no_update, ['all']
            else:
                return no_update, []

    # Update Title
    @dash_app.callback(
        Output('gas-demand-title', 'children'),
        Input('unit-filter', 'value')
    )
    def update_title(unit):
        return f"European Natural Gas Demand - {unit}"

    # Handle Chart Selection
    @dash_app.callback(
        [Output('gas-demand-chart-selection', 'data'),
         Output('gas-demand-chart', 'clickData')],
        [Input('gas-demand-chart', 'clickData'),
         Input('gas-europe-granularity-store', 'data'),
         Input('unit-filter', 'value'),
         Input('sector-filter', 'value'),
         Input('country-filter', 'value')],
        State('gas-demand-chart-selection', 'data'),
        prevent_initial_call=True
    )
    def toggle_chart_selection(click_data, gran, unit, sectors, countries, current_sel):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update
            
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Reset on filter changes
        if trigger_id != 'gas-demand-chart':
            return None, None
            
        if not click_data:
            return no_update, no_update
            
        point = click_data['points'][0]
        # Our customdata is [Sector, Year of Date, Unit]
        # We also need x_pos to be sure about the time slot
        if 'customdata' not in point:
            return no_update, no_update
            
        cdata = point['customdata']
        sector = cdata[0]
        year = cdata[1]
        x_pos = point['x']
        
        new_sel = {
            'sector': sector,
            'year': year,
            'x_pos': x_pos
        }
        
        # Toggle logic
        if current_sel and current_sel == new_sel:
            return None, None
            
        return new_sel, None

    @dash_app.callback(
        Output('gas-demand-chart', 'figure'),
        [Input('unit-filter', 'value'),
         Input('sector-filter', 'value'),
         Input('country-filter', 'value'),
         Input('gas-europe-granularity-store', 'data'),
         Input('gas-demand-chart-selection', 'data')]
    )
    def update_chart(unit, selected_sectors, selected_countries, granularity, selection):
        if not selected_sectors or not selected_countries:
            return go.Figure()

        unit_map = {'Million Cubic Meter': 'Mcm', 'GWh': 'GWh'}
        db_unit = unit_map.get(unit, 'Mcm')

        # SQL Query from user
        query = """
        SELECT
            'In' AS "In / Out of Sector Set Europe",
            EXTRACT(YEAR FROM gd.date)::int AS "Year of Date",
            CASE
                WHEN :granularity IN ('quarter','month','day')
                THEN 'Q' || EXTRACT(QUARTER FROM gd.date)::int
                ELSE NULL
            END AS "Quarter of Date",
            CASE
                WHEN :granularity IN ('month','day')
                THEN EXTRACT(MONTH FROM gd.date)::int
                ELSE NULL
            END AS "Month Num",
            CASE
                WHEN :granularity = 'day'
                THEN EXTRACT(DAY FROM gd.date)::int
                ELSE NULL
            END AS "Day of Date",
            gd.sector AS "Sector",
            :display_unit AS "Unit",
            ROUND(SUM(gd.value) / 1000.0, 9) AS "Value"
        FROM dev.glng_gas_demand gd
        LEFT JOIN dev.dim_country dc ON gd.country_id = dc.dim_country_id
        WHERE LOWER(dc.region) = 'europe'
          AND gd.unit = :unit
          AND gd.sector = ANY(:selected_sectors)
          AND dc.country_long_name = ANY(:selected_countries)
          AND gd.to_be_deleted = false
          AND EXTRACT(YEAR FROM gd.date) >= 2019
          AND EXTRACT(YEAR FROM gd.date) < 2025
        GROUP BY
            CASE
                WHEN :granularity = 'year'    THEN DATE_TRUNC('year', gd.date)
                WHEN :granularity = 'quarter' THEN DATE_TRUNC('quarter', gd.date)
                WHEN :granularity = 'month'   THEN DATE_TRUNC('month', gd.date)
                WHEN :granularity = 'day'     THEN DATE_TRUNC('day', gd.date)
            END,
            EXTRACT(YEAR FROM gd.date),
            CASE
                WHEN :granularity IN ('quarter','month','day')
                THEN 'Q' || EXTRACT(QUARTER FROM gd.date)::int
                ELSE NULL
            END,
            CASE
                WHEN :granularity IN ('month','day')
                THEN EXTRACT(MONTH FROM gd.date)::int
                ELSE NULL
            END,
            CASE
                WHEN :granularity = 'day'
                THEN EXTRACT(DAY FROM gd.date)::int
                ELSE NULL
            END,
            gd.sector
        ORDER BY
            "Year of Date" ASC,
            "Quarter of Date",
            "Month Num",
            "Day of Date",
            "Sector";
        """
        
        params = {
            'granularity': granularity,
            'selected_sectors': list(selected_sectors),
            'selected_countries': list(selected_countries),
            'unit': db_unit,
            'display_unit': unit
        }
        
        try:
            results = execute_query(query, params)
            df = pd.DataFrame(results)
        except Exception as e:
            print(f"Error executing query: {e}")
            return go.Figure()

        if df.empty:
            return go.Figure()

        # Ensure numeric and categorical types
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce').fillna(0).astype(float)
        df['Year Count'] = df['Year of Date'].fillna('').astype(str)
        df['Quarter Label'] = df['Quarter of Date'].fillna('').astype(str)
        
        # Map Month Num to Name
        month_map_num = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April', 
            5: 'May', 6: 'June', 7: 'July', 8: 'August', 
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }
        # If Month Num is null (e.g. quarterly view), this maps to NaN
        df['Month Label'] = df['Month Num'].map(month_map_num)
        
        # Fallback if needed (though logic suggests keeping them separate)
        # If Month Label is NaN, it's likely Year/Quarter view.
        # But for 'Monthly' view, it MUST be populated.
        if granularity == 'month' or granularity == 'day':
             df['Month Label'] = df['Month Label'].fillna('Unknown')
        else:
             df['Month Label'] = df['Month Label'].fillna('')

        # Debug
        if granularity == 'month':
            print("DEBUG MONTH DATA FRAME:")
            print(df[['Year Count', 'Quarter Label', 'Month Num', 'Month Label']].head(10))

        # If month is missing in text, use Quarter/Year to avoid total collapse (only for chart grouping labels if needed?)
        # Actually, for multicategory, we want robust labels.
        # For 'Quarter' view, Month Label is empty string.
        
        df['Day Label'] = df['Day of Date'].apply(lambda l: str(int(l)) if pd.notnull(l) and str(l) != '' else '')

        # Categorical orders for robust sorting
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        df['Month_Cat'] = pd.Categorical(df['Month Label'], categories=month_order, ordered=True)
        quarter_order = ['Q1', 'Q2', 'Q3', 'Q4']
        df['Quarter_Cat'] = pd.Categorical(df['Quarter Label'], categories=quarter_order, ordered=True)
        df['Sector'] = pd.Categorical(df['Sector'], categories=['Household', 'Industrial', 'Power'], ordered=True)
        
        # Unified sorting
        df = df.sort_values(['Year Count', 'Quarter_Cat', 'Month_Cat', 'Day Label', 'Sector'])

        # Compute Month Initials for Daily view
        if granularity == 'day':
            month_map = {
                'January': 'J..', 'February': 'F..', 'March': 'M..', 'April': 'A..',
                'May': 'M..', 'June': 'J..', 'July': 'J..', 'August': 'A..',
                'September': 'S..', 'October': 'O..', 'November': 'N..', 'December': 'D..'
            }
            df['Month Init'] = df['Month Label'].map(month_map).fillna(df['Month Label'])


        if granularity == 'day':
            month_map_short = {
                'January': 'J..', 'February': 'F..', 'March': 'M..', 'April': 'A..',
                'May': 'M..', 'June': 'J..', 'July': 'J..', 'August': 'A..',
                'September': 'S..', 'October': 'O..', 'November': 'N..', 'December': 'D..'
            }
            df['Month Init'] = df['Month Label'].map(month_map_short).fillna(df['Month Label'])

        # Prepare Timeline and x-positions
        # We need a sorted list of unique time units for the x-axis
        timeline_cols = ['Year of Date']
        if granularity != 'year':
            timeline_cols.append('Quarter_Cat')
        if granularity in ['month', 'day']:
            timeline_cols.append('Month_Cat')
        if granularity == 'day':
            timeline_cols.append('Day Label')
            
        timeline_df = df[timeline_cols].drop_duplicates().sort_values(timeline_cols)
        timeline_df['x_pos'] = range(len(timeline_df))
        
        # Merge back to main df
        df = df.merge(timeline_df, on=timeline_cols, how='left')

        # Chart Construction
        fig = go.Figure()
        
        # 1. Main Data Traces (Stacked Bars)
        for sector in ['Household', 'Industrial', 'Power']:
            sector_df = df[df['Sector'] == sector]
            if sector_df.empty: continue
            
            # Prepare customdata for tooltip: [Sector, Year of Date, Unit]
            custom_data = sector_df[['Sector', 'Year of Date', 'Unit']].values
            
            # Determine colors and borders based on selection
            colors = []
            line_colors = []
            line_widths = []
            
            for _, row in sector_df.iterrows():
                base_color = SECTOR_COLORS[sector]
                is_selected = (
                    selection and 
                    selection['sector'] == sector and 
                    selection['x_pos'] == row['x_pos']
                )
                
                if not selection:
                    # No selection - normal style
                    colors.append(base_color)
                    line_colors.append('rgba(0,0,0,0)')
                    line_widths.append(0)
                elif is_selected:
                    # Selected bar - highlighted
                    colors.append(base_color)
                    line_colors.append('black')
                    line_widths.append(2)
                else:
                    # Not selected - dimmed
                    colors.append(hex_to_rgba(base_color, 0.2))
                    line_colors.append('rgba(0,0,0,0)')
                    line_widths.append(0)

            fig.add_trace(go.Bar(
                name=sector,
                x=sector_df['x_pos'],
                y=sector_df['Value'].tolist(),
                marker=dict(
                    color=colors,
                    line=dict(color=line_colors, width=line_widths)
                ),
                text=sector_df['Value'].apply(lambda l: f"{l:.2f}" if l != 0 else ""),
                textposition='inside',
                insidetextanchor='middle',
                textfont=dict(color='white', size=9),
                customdata=custom_data,
                hovertemplate=(
                    "<span style='color: #666'>Sector:</span> %{customdata[0]}<br>"
                    "<span style='color: #666'>Year of Date:</span> %{customdata[1]}<br>"
                    "<span style='color: #666'>Value:</span> %{y:,.2f}<br>"
                    "<span style='color: #666'>Unit:</span> %{customdata[2]}<extra></extra>"
                )
            ))

        # 2. Header Traces (Top Labels)
        # Year Headers (Top-most)
        year_blocks = timeline_df.groupby('Year of Date')['x_pos'].agg(['min', 'max', 'count']).reset_index()
        fig.add_trace(go.Bar(
            x=(year_blocks['min'] + year_blocks['max']) / 2,
            y=[1] * len(year_blocks),
            width=year_blocks['count'],
            yaxis='y2',
            marker=dict(color='#f8f9fa', line=dict(color='#ddd', width=1)),
            text=year_blocks['Year of Date'],
            textposition='inside',
            textfont=dict(color='#333', size=12, family="Arial Bold"),
            hoverinfo='none',
            showlegend=False
        ))

        # Quarter Headers (below Year)
        if granularity != 'year':
            q_blocks = timeline_df.groupby(['Year of Date', 'Quarter_Cat'])['x_pos'].agg(['min', 'max', 'count']).reset_index()
            fig.add_trace(go.Bar(
                x=(q_blocks['min'] + q_blocks['max']) / 2,
                y=[1] * len(q_blocks),
                width=q_blocks['count'],
                yaxis='y3',
                marker=dict(color='white', line=dict(color='#eee', width=1)),
                text=q_blocks['Quarter_Cat'],
                textposition='inside',
                textfont=dict(color='#666', size=11),
                hoverinfo='none',
                showlegend=False
            ))

        # 3. Bottom Axis Labels
        if granularity == 'quarter':
            ticktext = timeline_df['Quarter_Cat']
        elif granularity == 'month':
            ticktext = timeline_df['Month_Cat']
        elif granularity == 'day':
            ticktext = timeline_df['Day Label']
            # Add Month Level for Day view
            m_blocks = timeline_df.groupby(['Year of Date', 'Month_Cat'])['x_pos'].agg(['min', 'max', 'count']).reset_index()
            # We need the initials for the text
            m_blocks['Month Init'] = m_blocks['Month_Cat'].map(month_map_short)
            
            fig.add_trace(go.Bar(
                x=(m_blocks['min'] + m_blocks['max']) / 2,
                y=[1] * len(m_blocks),
                width=m_blocks['count'],
                yaxis='y4',
                marker=dict(color='white', line=dict(color='#f0f0f0', width=0.5)),
                text=m_blocks['Month Init'],
                textposition='inside',
                textfont=dict(color='#999', size=9),
                hoverinfo='none',
                showlegend=False
            ))
        else:
            ticktext = timeline_df['Year of Date']

        # 4. Vertical Separators (Shapes)
        shapes = []
        # Year separators
        for i in range(len(year_blocks) - 1):
            sep_x = year_blocks.iloc[i]['max'] + 0.5
            shapes.append(dict(
                type="line", x0=sep_x, x1=sep_x, y0=0, y1=1,
                xref="x", yref="paper", line=dict(color="#666", width=2)
            ))
        
        # Quarter separators (if month/day view)
        if granularity in ['month', 'day']:
            for i in range(len(q_blocks) - 1):
                sep_x = q_blocks.iloc[i]['max'] + 0.5
                shapes.append(dict(
                    type="line", x0=sep_x, x1=sep_x, y0=0, y1=0.85,
                    xref="x", yref="paper", line=dict(color="#ddd", width=1, dash='dot')
                ))

        # Month separators (only for day view)
        if granularity == 'day':
            for i in range(len(m_blocks) - 1):
                sep_x = m_blocks.iloc[i]['max'] + 0.5
                shapes.append(dict(
                    type="line", x0=sep_x, x1=sep_x, y0=0, y1=0.77,
                    xref="x", yref="paper", line=dict(color="#eee", width=1, dash='dash')
                ))

        # Dynamic domains
        if granularity == 'day':
            main_domain = [0, 0.77]
            y2_domain = [0.92, 1]
            y3_domain = [0.85, 0.92]
            y4_domain = [0.77, 0.85]
        else:
            main_domain = [0, 0.85]
            y2_domain = [0.93, 1]
            y3_domain = [0.85, 0.93]
            y4_domain = [0, 0] # Invisible

        fig.update_layout(
            barmode='stack',
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(
                tickvals=timeline_df['x_pos'],
                ticktext=ticktext,
                title='', 
                showgrid=False,
                linecolor='#ddd',
                tickfont=dict(size=10, color='#333'),
                automargin=True,
                range=[-0.5, len(timeline_df) - 0.5]
            ),
            yaxis=dict(
                domain=main_domain,
                title='', 
                showgrid=True, 
                gridcolor='#eee', 
                showline=True, 
                linecolor='#ddd', 
                zeroline=True, 
                zerolinecolor='#ddd',
                tickfont=dict(size=10, color='#333')
            ),
            yaxis2=dict(
                domain=y2_domain,
                showgrid=False, showline=False, showticklabels=False,
                zeroline=False, fixedrange=True
            ),
            yaxis3=dict(
                domain=y3_domain,
                showgrid=False, showline=False, showticklabels=False,
                zeroline=False, fixedrange=True
            ),
            yaxis4=dict(
                domain=y4_domain,
                showgrid=False, showline=False, showticklabels=False,
                zeroline=False, fixedrange=True
            ),
            shapes=shapes,
            margin=dict(t=10, b=50, l=50, r=20),
            showlegend=False,
            height=500,
            font=dict(family="Arial, sans-serif"),
            bargap=0.2,
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial",
                bordercolor="#ddd",
                font_color="#333",
                align="left"
            )
        )
        
        # Ensure text labels show correctly
        if granularity == 'year':
            fig.update_traces(
                texttemplate='%{text}',
                textposition='inside',
                insidetextanchor='middle',
                textfont=dict(color='white', size=11)
            )

        return fig

    # Export Chart Data
    @dash_app.callback(
        Output("gas-demand-europe-download-chart-csv", "data"),
        Input("gas-demand-europe-export-chart-csv-btn", "n_clicks"),
        [State('unit-filter', 'value'),
         State('sector-filter', 'value'),
         State('country-filter', 'value'),
         State('gas-europe-granularity-store', 'data')]
    )
    def export_chart_csv(n_clicks, unit, selected_sectors, selected_countries, granularity):
        if not n_clicks or not selected_sectors or not selected_countries:
            return no_update
            
        unit_map = {'Million Cubic Meter': 'Mcm', 'GWh': 'GWh'}
        db_unit = unit_map.get(unit, 'Mcm')

        query = """
        SELECT
            EXTRACT(YEAR FROM gd.date)::int AS "Year of Date",
            CASE
                WHEN :granularity IN ('quarter','month','day')
                THEN 'Q' || EXTRACT(QUARTER FROM gd.date)::int
                ELSE NULL
            END AS "Quarter of Date",
            CASE
                WHEN :granularity IN ('month','day')
                THEN TO_CHAR(gd.date, 'FMMonth')
                ELSE NULL
            END AS "Month of Date",
            CASE
                WHEN :granularity = 'day'
                THEN EXTRACT(DAY FROM gd.date)::int
                ELSE NULL
            END AS "Day of Date",
            gd.sector AS "Sector",
            :display_unit AS "Unit",
            ROUND(SUM(gd.value) / 1000.0, 3) AS "Value"
        FROM dev.glng_gas_demand gd
        LEFT JOIN dev.dim_country dc ON gd.country_id = dc.dim_country_id
        WHERE LOWER(dc.region) = 'europe'
          AND gd.unit = :unit
          AND gd.sector = ANY(:selected_sectors)
          AND dc.country_long_name = ANY(:selected_countries)
          AND gd.to_be_deleted = false
          AND EXTRACT(YEAR FROM gd.date) >= 2019
          AND EXTRACT(YEAR FROM gd.date) < 2025
        GROUP BY 1, 2, 3, 4, 5, 6
        ORDER BY 1, 2, 
                 CASE 
                    WHEN :granularity IN ('month','day') 
                    THEN MIN(EXTRACT(MONTH FROM gd.date)) 
                    ELSE 0 
                 END,
                 CASE 
                    WHEN :granularity = 'day' 
                    THEN MIN(EXTRACT(DAY FROM gd.date)) 
                    ELSE 0 
                 END
        """
        
        params = {
            'granularity': granularity,
            'unit': db_unit,
            'display_unit': unit,
            'selected_sectors': selected_sectors,
            'selected_countries': selected_countries
        }
        
        try:
            results = execute_query(query, params)
            df = pd.DataFrame(results)
            if df.empty: 
                return dcc.send_string("No data found for the selected filters.", "no_data.txt")
            
            df = df.dropna(axis=1, how='all')
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"european_gas_demand_chart_{timestamp}.csv"
            return dcc.send_data_frame(df.to_csv, filename, index=False)
        except Exception as e:
            error_msg = f"Error exporting chart csv: {str(e)}"
            print(error_msg)
            return dcc.send_string(error_msg, "chart_export_error.txt")

    # Export Table Data
    @dash_app.callback(
        Output("gas-demand-europe-download-table-csv", "data"),
        Input("gas-demand-europe-export-table-csv-btn", "n_clicks"),
        [State('unit-filter', 'value'),
         State('sector-filter', 'value'),
         State('country-filter', 'value'),
         State('gas-europe-table-granularity-store', 'data')]
    )
    def export_table_csv(n_clicks, unit, selected_sectors, selected_countries, granularity):
        if not n_clicks or not selected_sectors or not selected_countries:
            return no_update
            
        unit_map = {'Million Cubic Meter': 'Mcm', 'GWh': 'GWh'}
        db_unit = unit_map.get(unit, 'Mcm')

        query = """
        SELECT
            gd.country                                AS "Country",
            gd.sector                                 AS "Sector",
            EXTRACT(YEAR FROM gd.date)::int           AS "Year",
            CASE WHEN :granularity IN ('quarter','month','day') THEN 'Q' || EXTRACT(QUARTER FROM gd.date)::int ELSE NULL END AS "Quarter",
            CASE WHEN :granularity IN ('month','day') THEN TO_CHAR(gd.date, 'FMMonth') ELSE NULL END AS "Month",
            CASE WHEN :granularity = 'day' THEN TO_CHAR(gd.date, 'FMMonth DD') ELSE NULL END AS "Day",
            :display_unit                             AS "Unit",
            ROUND(SUM(gd.value), 2)                   AS "Value"
        FROM dev.glng_gas_demand gd
        JOIN dev.dim_country dc ON gd.country_id = dc.dim_country_id
        WHERE LOWER(dc.region) = 'europe'
          AND gd.unit = :unit
          AND gd.sector = ANY(:selected_sectors)
          AND dc.country_long_name = ANY(:selected_countries)
          AND gd.to_be_deleted = false
          AND EXTRACT(YEAR FROM gd.date) >= 2019
          AND EXTRACT(YEAR FROM gd.date) < 2025
        GROUP BY 1, 2, 3, 4, 5, 6, 7
        ORDER BY 3 DESC, 1, 2
        """
        
        params = {
            'granularity': granularity,
            'unit': db_unit,
            'display_unit': unit,
            'selected_sectors': selected_sectors,
            'selected_countries': selected_countries
        }
        
        try:
            results = execute_query(query, params)
            df = pd.DataFrame(results)
            if df.empty: 
                return dcc.send_string("No data found for the selected filters.", "no_data.txt")
            
            df = df.dropna(axis=1, how='all')
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"european_gas_demand_table_{timestamp}.csv"
            return dcc.send_data_frame(df.to_csv, filename, index=False)
        except Exception as e:
            error_msg = f"Error exporting table csv: {str(e)}"
            print(error_msg)
            return dcc.send_string(error_msg, "table_export_error.txt")

    # Update Table
    @dash_app.callback(
        Output('gas-demand-table-container', 'children'),
        [Input('unit-filter', 'value'),
         Input('sector-filter', 'value'),
         Input('country-filter', 'value'),
         Input('gas-europe-table-granularity-store', 'data')]
    )
    def update_table(unit, selected_sectors, selected_countries, granularity):
        if not selected_sectors or not selected_countries:
            return html.Div("Please select at least one sector and country")

        unit_map = {'Million Cubic Meter': 'Mcm', 'GWh': 'GWh'}
        db_unit = unit_map.get(unit, 'Mcm')

        # SQL Query
        query = """
        SELECT
            gd.country                                AS "Country",
            gd.sector                                 AS "Sector",
            period                                    AS "_period_sort",

            EXTRACT(YEAR FROM period)::int            AS "Year of Date",

            /* Quarter */
            CASE
                WHEN :granularity IN ('quarter','day')
                THEN 'Q' || EXTRACT(QUARTER FROM period)::int
                ELSE NULL
            END AS "Quarter of Date",

            /* Month */
            CASE
                WHEN :granularity IN ('month','day')
                THEN TO_CHAR(period, 'FMMonth')
                ELSE NULL
            END AS "Month of Date",

            /* Day */
            CASE
                WHEN :granularity = 'day'
                THEN TO_CHAR(period, 'FMMonth FMDD')
                ELSE NULL
            END AS "Day of Date",

            :display_unit                             AS "Unit",
            ROUND(SUM(gd.value), 9)                   AS "Value"

        FROM dev.glng_gas_demand gd
        JOIN dev.dim_country dc
            ON gd.country_id = dc.dim_country_id

        /* 🔹 dynamic time bucket */
        CROSS JOIN LATERAL (
            SELECT
                CASE
                    WHEN :granularity = 'year'    THEN DATE_TRUNC('year', gd.date)
                    WHEN :granularity = 'quarter' THEN DATE_TRUNC('quarter', gd.date)
                    WHEN :granularity = 'month'   THEN DATE_TRUNC('month', gd.date)
                    WHEN :granularity = 'day'     THEN DATE_TRUNC('day', gd.date)
                END AS period
        ) t

        WHERE LOWER(dc.region) = 'europe'
          AND gd.unit = :unit
          AND gd.to_be_deleted = false
          AND gd.sector = ANY(:selected_sectors)
          AND dc.country_long_name = ANY(:selected_countries)
          AND EXTRACT(YEAR FROM gd.date) >= 2019
          AND EXTRACT(YEAR FROM gd.date) < 2025

        GROUP BY
            gd.country,
            gd.sector,
            period

        ORDER BY
            "Year of Date" DESC,
            "Quarter of Date",
            "Month of Date",
            "Day of Date",
            "Country",
            "Sector";
        
        """
        
        params = {
            'granularity': granularity, 
            'unit': db_unit, 
            'display_unit': unit,
            'selected_sectors': selected_sectors,
            'selected_countries': selected_countries
        }
        
        try:
            results = execute_query(query, params)
            df = pd.DataFrame(results)
        except Exception as e:
            return html.Div(f"Error loading table data: {e}")
        
        if df.empty:
            return html.Div("No data found")

        # Determine active hierarchy levels based on data
        levels = ['Year of Date']
        if df['Quarter of Date'].notna().any(): levels.append('Quarter of Date')
        
        # If we have daily data, we use the combined 'Month Day' label as the bottom level
        # and skip the independent 'Month' level for a cleaner hierarchy.
        if df['Day of Date'].notna().any():
            levels.append('Day of Date')
        elif df['Month of Date'].notna().any():
            levels.append('Month of Date')
        
        # Sort levels specifically (Month map needed for sorting)
        month_order = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
            'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        
        # We need to pivot to get columns: Year -> Quarter -> Month -> Day
        # Index: Country, Sector
        
        # 1. Build the columns hierarchy
        # Use _period_sort for reliable time sorting (Year DESC, then internal time ASC)
        time_cols_df = df[levels + ['_period_sort']].drop_duplicates()
        
        # We want Year to be DESC, but Quarters/Months/Days within the year to be ASC
        time_cols_df = time_cols_df.sort_values(
            by=['Year of Date', '_period_sort'],
            ascending=[False, True]
        )
        
        # Create list of tuples for columns
        cols_tuples = [tuple(row[l] for l in levels) for _, row in time_cols_df.iterrows()]
        
        # 2. Pivot the data
        pivot_df = df.pivot_table(
            index=['Country', 'Sector'],
            columns=levels,
            values='Value',
            aggfunc='sum'
        )
        
        # Ensure pivot_df columns match cols_tuples order and structure
        # If levels has only one element, cols_tuples elements are single values, not tuples.
        # pd.MultiIndex.from_tuples expects tuples.
        if len(levels) == 1:
            pivot_df = pivot_df.reindex(columns=[t[0] for t in cols_tuples])
        else:
            pivot_df = pivot_df.reindex(columns=pd.MultiIndex.from_tuples(cols_tuples))
        
        # 3. Build HTML Table
        # Headers
        
        thead_rows = []
        
        num_header_rows = len(levels)
        
        # Fixed headers (Country, Sector)
        # They span all header rows
        
        # Recursive function to build headers
        # This is tricky for simple logic.
        # Let's do a loop for each header row.
        
        # We need a list of (label, colspan) for each row.
        
        # We also need to account for the pivot columns matching exactly.
        # Let's work with the flat list of `cols_tuples` which represents the leaf nodes (bottom level columns).
        
        # Build a tree to calculate colspans
        # tree = { '2019': { 'Q1': { 'Jan': {}, 'Feb': {} }, 'Q2': ... } }
        
        # Simplified Hierarchical Header Construction
        # We iterate cols_tuples.
        # For Row 0 (Years):
        # We count consecutive occurrences of same Year.
        # [2019, 2019, 2019, 2020, 2020...] -> 2019 (3), 2020 (2)
        
        header_rows_content = [[] for _ in range(num_header_rows)]
        
        for depth in range(num_header_rows):
            current_vals_at_depth = [t[depth] for t in cols_tuples]
            
            # Group consecutive
            grouped = []
            if current_vals_at_depth:
                curr_val = current_vals_at_depth[0]
                count = 0
                for v in current_vals_at_depth:
                    if v == curr_val:
                        count += 1
                    else:
                        grouped.append((curr_val, count))
                        curr_val = v
                        count = 1
                grouped.append((curr_val, count)) # Add the last group
            
            # Create THs
            for label, span in grouped:
                header_rows_content[depth].append(
                    html.Th(label, colSpan=span, style={'textAlign': 'center', 'border': '1px solid #ddd', 'padding': '5px', 'backgroundColor': '#f9f9f9'})
                )
                
        # Combine Fixed + Dynamic
        # Only first row gets fixed headers
        
        # First header row (Country, Sector, and top-level time headers)
        first_header_row_ths = [
            html.Th("Country", rowSpan=num_header_rows, style={'position': 'sticky', 'left': 0, 'zIndex': 20, 'backgroundColor': 'white', 'border': '1px solid #ddd', 'padding': '8px', 'width': '120px', 'minWidth': '120px'}),
            html.Th("Sector", rowSpan=num_header_rows, style={'position': 'sticky', 'left': '100px', 'zIndex': 20, 'backgroundColor': 'white', 'border': '1px solid #ddd', 'padding': '8px'})
        ] + header_rows_content[0]
        thead_rows.append(html.Tr(first_header_row_ths))
        
        # Subsequent header rows (only time headers)
        for i in range(1, num_header_rows):
            thead_rows.append(html.Tr(header_rows_content[i]))
            
        # Table Body
        tbody_rows = []
        
        # Get unique countries and sectors
        # pivot_df index is (Country, Sector)
        # We need to sort index
        pivot_df = pivot_df.sort_index()
        
        # Group by Country
        for country, country_grp in pivot_df.groupby(level=0):
            # Sort sectors
            sector_order = {'Household': 1, 'Industrial': 2, 'Power': 3}
            # country_grp is DataFrame with MultiIndex (Country, Sector), Country is constant
            # Sort by the second level of the index (Sector) using the custom order
            country_grp = country_grp.sort_index(level=1, key=lambda idx: idx.map(lambda x: sector_order.get(x, 99)))
            
            sectors = country_grp.index.get_level_values(1).unique()
            first_sector = True
            
            country_subtotal_vals = [0] * len(cols_tuples)
            
            for sector in sectors:
                row_cells = []
                # Country Cell (RowSpan)
                if first_sector:
                    row_cells.append(html.Td(country, rowSpan=len(sectors)+1, 
                                            style={'position': 'sticky', 'left': 0, 'zIndex': 10, 'backgroundColor': 'white', 'fontWeight': 'bold', 'border': '1px solid #ddd', 'verticalAlign': 'top', 'padding': '8px', 'width': '120px', 'minWidth': '120px'}))
                    
                # Sector Cell
                row_cells.append(html.Td(sector, style={'position': 'sticky', 'left': '100px', 'zIndex': 10, 'backgroundColor': 'white', 'border': '1px solid #ddd', 'padding': '8px'}))
                
                # Data Cells
                try:
                    # Accessing pivot with tuple (Country, Sector)
                    # pivot columns are MultiIndex if len(levels) > 1, otherwise single index
                    series = country_grp.loc[(country, sector)]
                    
                    # Iterate through our defined sorted columns (cols_tuples)
                    for i, col_tuple in enumerate(cols_tuples):
                        # col_key needs to match the pivot_df's column structure
                        col_key = col_tuple if len(levels) > 1 else col_tuple[0]
                        
                        val = series.get(col_key, 0)
                        
                        # Handle NaN
                        if pd.isna(val): val = 0
                        
                        country_subtotal_vals[i] += val
                        
                        row_cells.append(html.Td(f"{val:,.0f}" if val != 0 else "-", 
                                                style={'textAlign': 'right', 'border': '1px solid #ddd', 'padding': '5px'}))
                        
                except KeyError:
                    # This should ideally not happen if data and pivot are consistent
                    pass
                
                tbody_rows.append(html.Tr(row_cells))
                first_sector = False
                
            # Total Row for Country
            total_cells = [
                html.Td("Total", style={'fontWeight': 'bold', 'textAlign': 'left', 'backgroundColor': '#f2f2f2', 'border': '1px solid #ddd', 'position': 'sticky', 'left': '100px', 'zIndex': 10, 'padding': '8px'})
            ]
            for v in country_subtotal_vals:
                total_cells.append(html.Td(f"{v:,.0f}" if v != 0 else "-", 
                                            style={'fontWeight': 'bold', 'textAlign': 'right', 'backgroundColor': '#f2f2f2', 'border': '1px solid #ddd', 'padding': '5px'}))
            
            tbody_rows.append(html.Tr(total_cells))

        return html.Table(
            [html.Thead(thead_rows), html.Tbody(tbody_rows)],
            style={'borderCollapse': 'collapse', 'width': '100%', 'fontFamily': 'Arial', 'fontSize': '12px'}
        )