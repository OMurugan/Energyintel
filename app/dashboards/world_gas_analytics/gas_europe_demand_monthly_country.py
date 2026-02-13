"""
European Gas Demand - Monthly Demand by Country
Monthly gas demand analytics by country with interactive map, charts, and tables
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, dash_table, State, ALL, ctx, no_update, callback_context
from datetime import datetime, timedelta
import time
from core.data_helpers import execute_query
from core.country_mappings import COUNTRY_TO_ISO, get_iso_code
from .shared_map_utils import (
    create_choropleth_map, 
    get_mapbox_config, 
    load_world_geojson,
    create_empty_map,
    handle_map_click_reset,
    MAP_BACKGROUND_COLOR as SHARED_MAP_BACKGROUND_COLOR,
    MAP_LAND_COLOR as SHARED_MAP_LAND_COLOR
)

# Cache configuration - now includes sector-specific caching
_cached_data = {}
_cache_timestamp = {}
CACHE_DURATION = 300  # 5 minutes cache

# Helper functions for date slider
def _format_date_for_display(date):
    """Format date as 'MM/DD/YYYY' (e.g., '1/1/2019')"""
    if pd.isna(date) or date is None:
        return ""
    if isinstance(date, str):
        date = pd.to_datetime(date, errors='coerce')
    if pd.isna(date):
        return ""
    return date.strftime('%-m/%-d/%Y')  # Remove leading zeros

def _index_to_date(index, date_list):
    """Convert slider index to date"""
    if not date_list or index < 0 or index >= len(date_list):
        return pd.Timestamp('2018-01-01')
    return date_list[int(index)]

def _date_to_index(date, date_list):
    """Convert date to slider index"""
    if not date_list:
        return 0
    if isinstance(date, str):
        date = pd.to_datetime(date, errors='coerce')
    if pd.isna(date):
        return 0
    # Find closest date index
    try:
        idx = date_list.index(date)
        return idx
    except ValueError:
        # Find closest date
        for i, d in enumerate(date_list):
            if d >= date:
                return i
        return len(date_list) - 1

# Color palette for countries - matching live server reference
COUNTRY_COLORS = {
    'Austria': '#4472C4',           # Dark blue
    'Belgium': '#70ADD8',           # Light blue
    'Bulgaria': '#FF8C00',          # Orange
    'Croatia': '#FFB366',           # Light orange
    'Czech Republic': '#228B22',    # Green
    'Denmark': '#90EE90',           # Light green
    'Estonia': '#B8860B',           # Dark goldenrod
    'Finland': '#F0E68C',           # Khaki/light yellow
    'France': '#008B8B',            # Dark cyan/teal
    'Germany': '#40E0D0',           # Turquoise
    'Greece': '#DC143C',            # Crimson red
    'Hungary': '#FF69B4',           # Hot pink
    'Italy': '#696969',             # Dim gray
    'Latvia': '#A0A0A0',            # Gray
    'Lithuania': '#DA70D6',         # Orchid
    'Luxembourg': '#FFB6C1',        # Light pink
    'Netherlands': '#8B008B',       # Dark magenta
    'Poland': '#DDA0DD',            # Plum
    'Portugal': '#8B4513',          # Saddle brown
    'Romania': '#D2B48C',           # Tan
    'Serbia': '#4472C4',            # Dark blue (same as Austria)
    'Slovakia': '#87CEEB',          # Sky blue
    'Slovenia': '#FF8C00',          # Orange (same as Bulgaria)
    'United Kingdom': '#FFB366',    # Light orange
    'Spain': '#228B22',             # Green (same as Czech Republic)
    'Sweden': '#90EE90',            # Light green (same as Denmark)
}

# Professional map color scale matching the live source dashboard
# Blue-green gradient as seen in the reference screenshot
MAP_COLOR_SCALE = [
    (0.0, '#f0f9ff'),  # Very light blue for lowest values
    (0.2, '#bae6fd'),  # Light blue
    (0.4, '#7dd3fc'),  # Medium light blue
    (0.6, '#38bdf8'),  # Medium blue
    (0.8, '#0ea5e9'),  # Darker blue
    (1.0, '#0284c7')   # Darkest blue for highest values
]

# Granularity Button Styles (from yearly dashboard)
GRAN_BTN_CONTAINER_STYLE = {
    'display': 'flex',
    'alignItems': 'center',
    'marginRight': '10px'
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

def hex_to_rgba(hex_color, opacity):
    """Convert hex color to rgba with specified opacity"""
    hex_color = hex_color.lstrip('#')
    lv = len(hex_color)
    rgb = tuple(int(hex_color[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
    return f'rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {opacity})'

def _iso_for_country(country):
    """Return ISO Alpha-3 code for a country, using centralized mapping."""
    # Manual patches for missing codes
    if country == 'Luxembourg': return 'LUX'
    if country == 'Czechia': return 'CZE'
    if country == 'Moldova': return 'MDA'
    if country == 'Republic of Moldova': return 'MDA'
    
    return get_iso_code(country)

def get_all_countries_with_coordinates():
    """Get all countries from dim_country with their coordinates and ISO codes for labels and map"""
    try:
        # For now, return empty DataFrame since we don't have access to dim_country table
        # This can be enhanced later if database access is available
        return pd.DataFrame(columns=['Country', 'ISO_Code', 'Latitude', 'Longitude'])
    except Exception as e:
        print(f"Error getting all countries with coordinates: {e}")
        return pd.DataFrame(columns=['Country', 'ISO_Code', 'Latitude', 'Longitude'])

def load_data(selected_sector=None):
    """Load and preprocess data from database with caching"""
    global _cached_data, _cache_timestamp
    
    # Create cache key based on sector
    cache_key = selected_sector or 'All'
    
    # Check if we have valid cached data for this sector
    current_time = time.time()
    if (cache_key in _cached_data and 
        cache_key in _cache_timestamp and 
        (current_time - _cache_timestamp[cache_key]) < CACHE_DURATION):
        print(f"Using cached data for sector: {cache_key}")
        return _cached_data[cache_key]
    
    try:
        # Import database query function
        from core.data_helpers import execute_query
        
        # Build sector filter condition
        if selected_sector and selected_sector != 'All':
            sector_condition = f"AND p.sector = '{selected_sector}'"
        else:
            sector_condition = "AND p.sector IN ('Industrial', 'Household', 'Power')"
        
        # Map Query: Replacement of csv file Europe Map_Demand by Year_data.csv
        map_query = f"""
        SELECT
            p.country AS "Country",
            EXTRACT(YEAR FROM p.date) AS "Year of Date",
            CASE 
                WHEN p.unit = 'Mcm' THEN 'Million Cubic Meter'
                WHEN p.unit = 'GWh' THEN 'Gigawatt-hour'
                ELSE p.unit
            END AS "Unit",
            q.latitude AS "Latitude",
            q.longitude AS "Longitude",
            ROUND(SUM(p.value), 6) AS "Value"
        FROM glng_gas_demand p
        LEFT JOIN dim_country q
        ON q.dim_country_id = p.country_id
        WHERE LOWER(q.region) = 'europe' 
        AND q.latitude IS NOT NULL 
        {sector_condition}
        GROUP BY
            p.country,
            EXTRACT(YEAR FROM p.date),
            CASE 
                WHEN p.unit = 'Mcm' THEN 'Million Cubic Meter'
                WHEN p.unit = 'GWh' THEN 'Gigawatt-hour'
                ELSE p.unit
            END,
            q.latitude,
            q.longitude
        ORDER BY
            p.country DESC,
            EXTRACT(YEAR FROM p.date) DESC;
        """
        
        # Chart Query Day of Month: Replacement of csv file Europe Line Chart_Total Demand by Country_data.csv
        chart_query = f"""
        SELECT
            DATE_TRUNC('month', p.date)::date AS "Day of Date",
            p.country AS "Country",
            CASE 
                WHEN p.unit = 'Mcm' THEN 'Million Cubic Meter'
                WHEN p.unit = 'GWh' THEN 'Gigawatt-hour'
                ELSE p.unit
            END AS "Unit",
            ROUND(SUM(p.value), 2) AS "Value"
        FROM glng_gas_demand p
        LEFT JOIN dim_country q
        ON q.dim_country_id = p.country_id
        WHERE LOWER(q.region) = 'europe'
        AND q.latitude IS NOT NULL
        {sector_condition}
        GROUP BY
            DATE_TRUNC('month', p.date),
            p.country,
            CASE 
                WHEN p.unit = 'Mcm' THEN 'Million Cubic Meter'
                WHEN p.unit = 'GWh' THEN 'Gigawatt-hour'
                ELSE p.unit
            END
        ORDER BY
            "Day of Date",
            "Country";
        """
        
        # Datatable Query: Replacement of csv file Europe Table_Total Demand by Country_data.csv
        table_query = f"""
        SELECT
            p.country AS "Country",
            EXTRACT(YEAR FROM p.date) AS "Year of Date",
            CONCAT('Q', EXTRACT(QUARTER FROM p.date)) AS "Quarter of Date",
            TO_CHAR(p.date, 'FMMonth') AS "Month of Date",
            1 AS "Day of Date",
            CASE 
                WHEN p.unit = 'Mcm' THEN 'Million Cubic Meter'
                WHEN p.unit = 'GWh' THEN 'Gigawatt-hour'
                ELSE p.unit
            END AS "Unit",
            ROUND(SUM(p.value), 6) AS "Value",
            DATE_TRUNC('month', p.date) AS month_sort
        FROM glng_gas_demand p
        LEFT JOIN dim_country q
        ON q.dim_country_id = p.country_id
        WHERE LOWER(q.region) = 'europe'
        AND q.latitude IS NOT NULL
        {sector_condition}
        GROUP BY
            p.country,
            EXTRACT(YEAR FROM p.date),
            EXTRACT(QUARTER FROM p.date),
            TO_CHAR(p.date, 'FMMonth'),
            DATE_TRUNC('month', p.date),
            CASE 
                WHEN p.unit = 'Mcm' THEN 'Million Cubic Meter'
                WHEN p.unit = 'GWh' THEN 'Gigawatt-hour'
                ELSE p.unit
            END
        ORDER BY
            p.country,
            month_sort DESC;
        """
        
        print("Executing database queries...")
        
        # Execute queries using centralized data helpers
        map_rows = execute_query(map_query)
        chart_rows = execute_query(chart_query)
        table_rows = execute_query(table_query)
        
        if not map_rows or not chart_rows or not table_rows:
            print("WARNING: One or more database queries returned no data")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        # Convert to DataFrames
        map_df = pd.DataFrame(map_rows)
        chart_df = pd.DataFrame(chart_rows)
        table_df = pd.DataFrame(table_rows)
        
        print(f"Queries returned - Map: {len(map_df)} rows, Chart: {len(chart_df)} rows, Table: {len(table_df)} rows")
        
        if map_df.empty or chart_df.empty or table_df.empty:
            print("WARNING: One or more database queries returned empty data")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        # Process map data
        map_df['Date'] = pd.to_datetime(map_df['Year of Date'], format='%Y')
        # Rename columns to match expected format
        map_df = map_df.rename(columns={
            'Latitude': 'Latitude (generated)',
            'Longitude': 'Longitude (generated)'
        })
        
        # Process chart data
        chart_df['Date'] = pd.to_datetime(chart_df['Day of Date'], errors='coerce')
        chart_df = chart_df.dropna(subset=['Date'])
        
        # Process table data
        # Create proper Date column from Year and Month
        table_df['Date'] = pd.to_datetime(
            table_df['Year of Date'].astype(str) + '-' + table_df['Month of Date'].astype(str), 
            format='%Y-%B', 
            errors='coerce'
        )
        table_df = table_df.dropna(subset=['Date'])
        
        # Add sector information based on the filter used
        sector_label = selected_sector if selected_sector and selected_sector != 'All' else 'Total'
        for df in [map_df, chart_df, table_df]:
            if 'Sector' not in df.columns:
                df['Sector'] = sector_label
        
        print(f"SUCCESS: Processed {len(map_df)} map rows, {len(chart_df)} chart rows and {len(table_df)} table rows from database")
        
        # Cache the results for this sector
        _cached_data[cache_key] = (map_df, chart_df, table_df)
        _cache_timestamp[cache_key] = current_time
        
        return _cached_data[cache_key]
        
    except Exception as e:
        print(f"CRITICAL: Database query failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Return cached data if available, even if expired
        if cache_key in _cached_data:
            print("Returning expired cached data due to database error")
            return _cached_data[cache_key]
        
        # If no cached data available, return empty DataFrames
        print("No cached data available, returning empty DataFrames")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def create_layout():
    """Create the European Monthly Demand by Country layout"""
    map_df, chart_df, table_df = load_data()
    
    if map_df.empty and chart_df.empty and table_df.empty:
        return html.Div([
            html.H1("European Gas Demand - Data Loading Issue", style={
                'color': '#fe5000', 'fontSize': '20px', 'fontWeight': 'bold',
                'fontFamily': 'Arial, sans-serif', 'margin': '25px 0 15px 40px'
            }),
            html.Div("Database connection issue. Please check database connectivity and try again.", 
                    style={'padding': '50px', 'color': 'red', 'fontSize': '16px'})
        ])

    # Get available options for filters
    all_countries = []
    for df in [map_df, chart_df, table_df]:
        if not df.empty and 'Country' in df.columns:
            all_countries.extend(df['Country'].unique())
    countries = sorted(list(set(all_countries)))
    
    # Get available sectors - add all required options
    sectors = ['All', 'Household', 'Industrial', 'Power']
    
    # Get available units - add both options
    units = ['Million Cubic Meter', 'Gigawatt-hour']
    
    # Get date range and create sorted date list
    all_dates = []
    for df in [map_df, chart_df, table_df]:
        if not df.empty and 'Date' in df.columns:
            all_dates.extend(df['Date'].dropna())
    
    if all_dates:
        unique_dates = sorted(list(set(all_dates)))
        min_date_val = unique_dates[0]
        max_date_val = unique_dates[-1]
        date_list = unique_dates
        
        # Set default range to 2019-2026 (8 years) - ensure we get the full range
        default_start_date = pd.Timestamp('2019-01-01')
        default_end_date = pd.Timestamp('2026-12-31')
        
        # Find indices for default range - be more flexible with date matching
        default_start_index = 0
        default_end_index = len(date_list) - 1
        
        # Find the closest date to 2019-01-01 or later
        for i, date in enumerate(date_list):
            if date.year >= 2019:
                default_start_index = i
                break
        
        # Find the closest date to 2026-12-31 or earlier
        for i in range(len(date_list) - 1, -1, -1):
            if date_list[i].year <= 2026:
                default_end_index = i
                break
                
        # If we couldn't find 2019-2026 range, use full range
        if default_start_index >= default_end_index:
            default_start_index = 0
            default_end_index = len(date_list) - 1
            
        print(f"Date range: {len(date_list)} dates from {min_date_val} to {max_date_val}")
        print(f"Default range: indices {default_start_index}-{default_end_index} ({date_list[default_start_index]} to {date_list[default_end_index]})")
    else:
        min_date_val = pd.Timestamp('2018-01-01')
        max_date_val = pd.Timestamp('2025-12-31')
        date_list = []
        default_start_index = 0
        default_end_index = 0

    return html.Div([
        # Store components for tracking filter states and granularity
        dcc.Store(id='country-filter-previous-demand', data={'all_selected': True}),
        dcc.Store(id='selected-countries-store-demand', data=countries),
        dcc.Store(id='demand-date-list-store', data=[d.isoformat() for d in date_list] if date_list else []),
        dcc.Store(id='chart-granularity-store-demand', data='month'),  # Default to month for chart
        dcc.Store(id='table-granularity-store-demand', data='month'),  # Default to month for table
        dcc.Store(id='chart-selection-store-demand', data=None),  # For chart highlighting
        
        # Download components
        dcc.Download(id="download-demand-map-csv"),
        dcc.Download(id="download-demand-chart-csv"),
        dcc.Download(id="download-demand-table-csv"),
        
        # Clientside callback trigger for hover highlighting
        html.Div(id='gas-demand-hover-trigger', style={'display': 'none'}),
        
        html.Div([
            # Side Filter Panel (on the right)
            html.Div([
                html.Div([
                    # Date Filter - Range Slider Style (matching reference design)
                    html.Label("Date", style={
                        'fontFamily': 'Arial',
                        'fontSize': '14px',
                        'lineHeight': '12px',
                        'color': '#2c3e50',
                        'fontWeight': 'bold',
                        'fontStyle': 'normal',
                        'textDecoration': 'none',
                        'marginBottom': '2px'
                    }),
                    html.Div([
                        html.Div([
                            html.Label(
                                id="demand-date-range-start-label",
                                children='1/1/2019',  # Default start date
                                style={'display': 'inline-block', 'color': '#1b365d', 'fontSize': '11px', 'fontFamily': 'Arial', 'lineHeight': '12px', 'fontWeight': 'bold'}
                            ),
                            html.Label(
                                id="demand-date-range-end-label",
                                children='12/31/2026',  # Default end date
                                style={'float': 'right', 'color': '#1b365d', 'fontSize': '11px', 'fontFamily': 'Arial', 'lineHeight': '28px', 'fontWeight': 'bold'}
                            ),
                        ], style={'width': '100%', 'marginBottom': '2px', 'position': 'relative'}),
                        html.Div([
                            dcc.RangeSlider(
                                id="demand-date-range-slider",
                                min=0,
                                max=len(date_list) - 1 if date_list else 0,
                                step=1,
                                value=[default_start_index, default_end_index],  # Default to 2019-2026 range
                                marks=None,
                                allowCross=False,
                            ),
                        ], style={'width': '100%', 'margin': '0', 'padding': '0'}),
                    ], style={'width': '100%', 'position': 'relative', 'marginBottom': '10px'}),
                    
                    # Unit Filter
                    html.Label("Unit", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '13px', 'marginBottom': '10px'}),
                    dcc.RadioItems(
                        id='unit-radio-demand',
                        options=[{'label': f' {unit}', 'value': unit} for unit in units],
                        value=units[0] if units else 'Million Cubic Meter',
                        inputStyle={'marginRight': '8px'},
                        labelStyle={'display': 'block', 'marginBottom': '4px', 'fontSize': '12px', 'cursor': 'pointer'},
                        style={'marginBottom': '20px'}
                    ),
                    
                    # Sector Filter
                    html.Label("Sector", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '13px', 'marginBottom': '10px'}),
                    dcc.RadioItems(
                        id='sector-radio-demand',
                        options=[{'label': f' {sector}', 'value': sector} for sector in sectors],
                        value='All',
                        inputStyle={'marginRight': '8px'},
                        labelStyle={'display': 'block', 'marginBottom': '4px', 'fontSize': '12px', 'cursor': 'pointer'},
                        style={'marginBottom': '20px'}
                    ),
                    
                    # Country Filter
                    html.Label("Country", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '13px', 'marginBottom': '10px'}),
                    dcc.Checklist(
                        id='country-checklist-demand',
                        options=[{'label': ' (All)', 'value': '(All)'}] + [{'label': f' {c}', 'value': c} for c in countries],
                        value=['(All)'] + countries,  # Start with all selected
                        inputStyle={'marginRight': '8px'},
                        labelStyle={'display': 'block', 'marginBottom': '4px', 'fontSize': '12px', 'cursor': 'pointer'},
                        style={                            
                            'overflowY': 'auto',
                            'padding': '6px',
                            'border': '1px solid #e0e0e0',
                            'borderRadius': '6px',
                            'background': 'white',
                            'marginBottom': '20px'
                        }
                    ),
                    
                    # Country Legend
                    html.Label("Country Legend", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '13px', 'marginBottom': '10px'}),
                    html.Div(
                        id='country-legend-container-demand',
                        children=[],  # Will be populated by callback
                        style={'overflowY': 'auto', 'marginBottom': '15px'}
                    ),
                
                ], style={'padding': '10px', 'backgroundColor': '#fcfcfc', 'borderLeft': '1px solid #eee', 'minHeight': '500px'})
            ], style={'float': 'right'}),

            # Main content area
            html.Div([
                # Header section
                html.Div([
                    html.Div([
                        html.H1("European Gas Demand - Monthly Demand by Country", style={
                            'color': '#fe5000', 'fontSize': '20px', 'fontWeight': 'bold',
                            'fontFamily': 'Arial, sans-serif', 'margin': '25px 0 15px 0'
                        }),
                    ], style={'flex': '1'}),
                    html.Div([                        
                        
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'padding': '0 10px', 'marginBottom': '20px'}),
                
                # Map and Chart Side by Side Section
                html.Div([
                    # Left Side - Europe Map
                    html.Div([
                        html.Div([
                            html.H3(id="europe-map-title", children="Natural Gas Demand", style={
                                'color': '#1b365d', 'fontSize': '16px', 'fontWeight': 'bold',
                                'marginBottom': '15px', 'textAlign': 'left', 'flex': '1'
                            }),
                            html.Button(
                                "Export to CSV",
                                id="export-demand-map-btn",
                                n_clicks=0,
                                style={
                                    "backgroundColor": "white",
                                    "color": "#2c3e50",
                                    "border": "1px solid #dee2e6",
                                    "padding": "4px 8px",
                                    "borderRadius": "4px",
                                    "cursor": "pointer",
                                    "fontSize": "11px",
                                    "fontWeight": "normal",
                                    "marginBottom": "10px",
                                    "marginRight": "10px",
                                },
                            )
                        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '5px'}),
                        html.Div([
                            dcc.Loading(
                                id="loading-map-demand",
                                type="circle",
                                children=dcc.Graph(
                                    id='europe-map-demand', 
                                    config={
                                        'displayModeBar': True,
                                        'displaylogo': False,
                                        'modeBarButtons': [
                                            ['toImage', 'resetViewMapbox', 'resetGeo']
                                        ],
                                        'scrollZoom': True,
                                        'doubleClick': 'reset',
                                        'toImageButtonOptions': {
                                            'format': 'png',
                                            'filename': 'europe_gas_demand_map',
                                            'height': 700,
                                            'width': 1200,
                                            'scale': 2
                                        }
                                    }
                                )
                            )
                        ], style={'position': 'relative'}),
                    ], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top', 'marginRight': '0%'}),
                    
                    # Right Side - Line Chart
                    html.Div([
                        # Chart Granularity Buttons with Export CSV
                        html.Div([
                            html.Div([
                                html.Div([
                                    html.Span("Yr of Dt", title="Year of Date", style={'fontSize': '11px', 'marginRight': '5px', 'cursor': 'help'}),
                                    html.Button('+', id='chart-toggle-year-btn-demand', n_clicks=0, style=GRAN_BTN_INACTIVE)
                                ], style=GRAN_BTN_CONTAINER_STYLE),
                                html.Div([
                                    html.Span("Qtr of Dt", title="Quarter of Date", style={'fontSize': '11px', 'marginRight': '5px', 'cursor': 'help'}),
                                    html.Button('+', id='chart-toggle-quarter-btn-demand', n_clicks=0, style=GRAN_BTN_INACTIVE)
                                ], style=GRAN_BTN_CONTAINER_STYLE),
                                html.Div([
                                    html.Span("Mth of Dt", title="Month of Date", style={'fontSize': '11px', 'marginRight': '5px', 'cursor': 'help'}),
                                    html.Button('-', id='chart-toggle-month-btn-demand', n_clicks=0, style=GRAN_BTN_ACTIVE)
                                ], style=GRAN_BTN_CONTAINER_STYLE),
                                html.Div([
                                    html.Span("Day of Dt", title="Day of Date", style={'fontSize': '11px', 'marginRight': '5px', 'cursor': 'help'}),
                                    html.Button('+', id='chart-toggle-day-btn-demand', n_clicks=0, style=GRAN_BTN_INACTIVE)
                                ], style=GRAN_BTN_CONTAINER_STYLE),
                            ], style={'display': 'flex', 'flex': '1'}),
                            html.Button(
                                "Export to CSV",
                                id="export-demand-chart-btn",
                                n_clicks=0,
                                style={
                                    "backgroundColor": "white",
                                    "color": "#2c3e50",
                                    "border": "1px solid #dee2e6",
                                    "padding": "4px 8px",
                                    "borderRadius": "4px",
                                    "cursor": "pointer",
                                    "fontSize": "11px",
                                    "fontWeight": "normal",
                                    "marginLeft": "10px",
                                },
                            )
                        ], style={'display': 'flex', 'alignItems': 'center', 'padding': '5px', 'backgroundColor': '#f8f9fa', 'marginBottom': '10px', 'borderRadius': '4px'}),
                        
                        html.Div([
                            dcc.Loading(
                                id="loading-chart-demand",
                                type="circle",
                                children=dcc.Graph(
                                    id='europe-chart-demand', 
                                    config={
                                        'displayModeBar': True,
                                        'displaylogo': False,
                                        'modeBarButtons': [
                                            ['toImage', 'resetScale2d']
                                        ],
                                        'toImageButtonOptions': {
                                            'format': 'png',
                                            'filename': 'europe_gas_demand_chart',
                                            'height': 700,
                                            'width': 1200,
                                            'scale': 2
                                        }
                                    }
                                )
                            )
                        ], style={'position': 'relative'}),
                    ], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top', 'marginLeft': '0%'}),
                ], style={'marginBottom': '30px', 'width': '100%'}),
                
                # Table Section
                html.Div([
                    # Table Granularity Buttons with Export CSV
                    html.Div([
                        html.Div([
                            html.Div([
                                html.Span("Year of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                                html.Button('+', id='table-toggle-year-btn-demand', n_clicks=0, style=GRAN_BTN_INACTIVE)
                            ], style=GRAN_BTN_CONTAINER_STYLE),
                            html.Div([
                                html.Span("Quarter of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                                html.Button('+', id='table-toggle-quarter-btn-demand', n_clicks=0, style=GRAN_BTN_INACTIVE)
                            ], style=GRAN_BTN_CONTAINER_STYLE),
                            html.Div([
                                html.Span("Month of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                                html.Button('-', id='table-toggle-month-btn-demand', n_clicks=0, style=GRAN_BTN_ACTIVE)
                            ], style=GRAN_BTN_CONTAINER_STYLE),
                            html.Div([
                                html.Span("Day of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                                html.Button('+', id='table-toggle-day-btn-demand', n_clicks=0, style=GRAN_BTN_INACTIVE)
                            ], style=GRAN_BTN_CONTAINER_STYLE),
                        ], style={'display': 'flex', 'flex': '1'}),
                        html.Button(
                            "Export to CSV",
                            id="export-demand-table-btn",
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
                                "marginLeft": "10px",
                            },
                        )
                    ], style={'display': 'flex', 'alignItems': 'center', 'padding': '10px', 'backgroundColor': '#f8f9fa', 'marginBottom': '15px', 'borderRadius': '4px'}),
                    
                    dcc.Loading(
                        id="loading-table-demand",
                        type="circle",
                        children=html.Div(
                            id='europe-table-demand'
                        )
                    ),
                    
                ], style={'width': '100%'}),  # table section close
                
            ], style={'marginRight': '150px', 'padding': '0 10px'})  # main content close
        ])  # outer container close - closes html.Div([ from line 452
    ], className='tab-content', style={'backgroundColor': '#ffffff', 'minHeight': '100vh'})  # closes return html.Div([ from line 435


def register_callbacks(dash_app, server):
    """Register all callbacks for the European Gas Demand dashboard"""
    
    # Chart Granularity Toggle
    @dash_app.callback(
        [Output('chart-granularity-store-demand', 'data'),
         Output('chart-toggle-year-btn-demand', 'children'),
         Output('chart-toggle-quarter-btn-demand', 'children'),
         Output('chart-toggle-month-btn-demand', 'children'),
         Output('chart-toggle-day-btn-demand', 'children'),
         Output('chart-toggle-year-btn-demand', 'style'),
         Output('chart-toggle-quarter-btn-demand', 'style'),
         Output('chart-toggle-month-btn-demand', 'style'),
         Output('chart-toggle-day-btn-demand', 'style')],
        [Input('chart-toggle-year-btn-demand', 'n_clicks'),
         Input('chart-toggle-quarter-btn-demand', 'n_clicks'),
         Input('chart-toggle-month-btn-demand', 'n_clicks'),
         Input('chart-toggle-day-btn-demand', 'n_clicks')],
        [State('chart-granularity-store-demand', 'data')]
    )
    def toggle_chart_granularity(y_c, q_c, m_c, d_c, current_gran):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
        btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
        new_gran = current_gran
        
        if btn_id == 'chart-toggle-year-btn-demand': new_gran = 'year'
        elif btn_id == 'chart-toggle-quarter-btn-demand': new_gran = 'quarter'
        elif btn_id == 'chart-toggle-month-btn-demand': new_gran = 'month'
        elif btn_id == 'chart-toggle-day-btn-demand': new_gran = 'day'
        
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
        [Output('table-granularity-store-demand', 'data'),
         Output('table-toggle-year-btn-demand', 'children'),
         Output('table-toggle-quarter-btn-demand', 'children'),
         Output('table-toggle-month-btn-demand', 'children'),
         Output('table-toggle-day-btn-demand', 'children'),
         Output('table-toggle-year-btn-demand', 'style'),
         Output('table-toggle-quarter-btn-demand', 'style'),
         Output('table-toggle-month-btn-demand', 'style'),
         Output('table-toggle-day-btn-demand', 'style')],
        [Input('table-toggle-year-btn-demand', 'n_clicks'),
         Input('table-toggle-quarter-btn-demand', 'n_clicks'),
         Input('table-toggle-month-btn-demand', 'n_clicks'),
         Input('table-toggle-day-btn-demand', 'n_clicks')],
        [State('table-granularity-store-demand', 'data')]
    )
    def toggle_table_granularity(y_c, q_c, m_c, d_c, current_gran):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
        btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
        new_gran = current_gran
        
        if btn_id == 'table-toggle-year-btn-demand': new_gran = 'year'
        elif btn_id == 'table-toggle-quarter-btn-demand': new_gran = 'quarter'
        elif btn_id == 'table-toggle-month-btn-demand': new_gran = 'month'
        elif btn_id == 'table-toggle-day-btn-demand': new_gran = 'day'
        
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

    # Handle Chart Selection for highlighting
    @dash_app.callback(
        [Output('chart-selection-store-demand', 'data'),
         Output('europe-chart-demand', 'clickData')],
        [Input('europe-chart-demand', 'clickData'),
         Input('chart-granularity-store-demand', 'data'),
         Input('unit-radio-demand', 'value'),
         Input('sector-radio-demand', 'value'),
         Input('selected-countries-store-demand', 'data')],
        State('chart-selection-store-demand', 'data'),
        prevent_initial_call=True
    )
    def toggle_chart_selection(click_data, granularity, unit, sector, countries, current_sel):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update
            
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Reset selection on filter changes
        if trigger_id != 'europe-chart-demand':
            return None, None
            
        if not click_data or 'points' not in click_data or len(click_data['points']) == 0:
            return no_update, no_update
            
        point = click_data['points'][0]
        
        # Extract country from customdata (which we set in the chart)
        country = None
        if 'customdata' in point and point['customdata'] and len(point['customdata']) > 0:
            country = point['customdata'][0]  # First element is country name
        
        if not country:
            return no_update, no_update
        
        x_value = point.get('x', '')
        
        new_sel = {
            'country': country,
            'x_value': x_value,
            'granularity': granularity
        }
        
        # Toggle logic - if same country is clicked, clear selection
        if current_sel and current_sel.get('country') == country:
            return None, None
            
        return new_sel, None
    
    # Clientside callback for hover highlighting (similar to country_profile.py)
    dash_app.clientside_callback(
        """
        function(hoverData, figure) {
            if (!figure || !figure.data) {
                return window.dash_clientside.no_update;
            }
            
            // Create a copy of the figure
            let newFig = JSON.parse(JSON.stringify(figure));
            let hoveredISO = null;
            
            // Extract hovered country ISO from hover data
            if (hoverData && hoverData.points && hoverData.points.length > 0) {
                let point = hoverData.points[0];
                let trace = newFig.data[point.curveNumber];
                
                if (trace) {
                    // Case 1: Hovering over choropleth (country area)
                    if (trace.name === 'countries' && point.customdata) {
                        hoveredISO = point.customdata;
                    }
                }
            }
            
            // Remove existing hover highlights
            newFig.data = newFig.data.filter(t => t && t.name !== 'hover_highlight');
            
            // If no active country hover, return the cleaned figure
            if (!hoveredISO || hoveredISO === '__BACKGROUND_CLICK__') {
                return newFig;
            }
            
            // Add hover highlight for the hovered country
            if (newFig.layout && newFig.layout.mapbox) {
                // Mapbox version
                newFig.data.push({
                    type: 'choroplethmapbox',
                    geojson: newFig.data[0].geojson, // Use same geojson as main trace
                    locations: [hoveredISO],
                    z: [1],
                    featureidkey: 'id',
                    colorscale: [[0, 'rgba(70, 130, 180, 0.3)'], [1, 'rgba(70, 130, 180, 0.3)']],
                    showscale: false,
                    hoverinfo: 'skip',
                    marker: {
                        line: {
                            color: 'rgba(70, 130, 180, 0.9)',
                            width: 2
                        },
                        opacity: 0.3
                    },
                    name: 'hover_highlight'
                });
            } else {
                // Geo version
                newFig.data.push({
                    type: 'choropleth',
                    locations: [hoveredISO],
                    z: [1],
                    locationmode: 'ISO-3',
                    colorscale: [[0, 'rgba(70, 130, 180, 0.3)'], [1, 'rgba(70, 130, 180, 0.3)']],
                    showscale: false,
                    hoverinfo: 'skip',
                    marker: {
                        line: {
                            color: 'rgba(70, 130, 180, 0.9)',
                            width: 2
                        },
                        opacity: 0.3
                    },
                    name: 'hover_highlight'
                });
            }
            
            return newFig;
        }
        """,
        Output('europe-map-demand', 'figure', allow_duplicate=True),
        [Input('europe-map-demand', 'hoverData')],
        [State('europe-map-demand', 'figure')],
        prevent_initial_call=True
    )
    
    # Clientside callback for line chart hover behavior (show dots at hover x-position on all lines)
    dash_app.clientside_callback(
        """
        function(hoverData, figure) {
            if (!figure || !figure.data) {
                return window.dash_clientside.no_update;
            }
            
            // Create a copy of the figure
            let newFig = JSON.parse(JSON.stringify(figure));
            let hoveredX = null;
            
            // Extract hovered x-value from hover data
            if (hoverData && hoverData.points && hoverData.points.length > 0) {
                hoveredX = hoverData.points[0].x;
            }
            
            // Update marker visibility based on hover x-position
            for (let i = 0; i < newFig.data.length; i++) {
                let trace = newFig.data[i];
                if (trace.type === 'scatter') {
                    if (hoveredX !== null) {
                        // Show markers at the hovered x-position for all lines
                        let markerSizes = [];
                        for (let j = 0; j < trace.x.length; j++) {
                            if (trace.x[j] === hoveredX) {
                                // Show marker at this x-position
                                markerSizes.push(8);
                            } else {
                                // Hide marker at other x-positions
                                markerSizes.push(0);
                            }
                        }
                        trace.marker.size = markerSizes;
                        trace.mode = 'lines+markers';
                    } else {
                        // No hover - show markers only on selected lines (if any)
                        if (trace.line && trace.line.width > 2) {
                            // Selected line - show all markers
                            let markerSizes = [];
                            for (let j = 0; j < trace.x.length; j++) {
                                markerSizes.push(8);
                            }
                            trace.marker.size = markerSizes;
                            trace.mode = 'lines+markers';
                        } else {
                            // Non-selected line - hide all markers
                            let markerSizes = [];
                            for (let j = 0; j < trace.x.length; j++) {
                                markerSizes.push(0);
                            }
                            trace.marker.size = markerSizes;
                            trace.mode = 'lines';
                        }
                    }
                }
            }
            
            return newFig;
        }
        """,
        Output('europe-chart-demand', 'figure', allow_duplicate=True),
        [Input('europe-chart-demand', 'hoverData')],
        [State('europe-chart-demand', 'figure')],
        prevent_initial_call=True
    )
    
    # Update date labels based on range slider selection
    @dash_app.callback(
        [Output('demand-date-range-start-label', 'children'),
         Output('demand-date-range-end-label', 'children')],
        [Input('demand-date-range-slider', 'value')],
        [State('demand-date-list-store', 'data')]
    )
    def update_date_labels(slider_range, date_list_iso):
        """Update date labels based on range slider values."""
        if not date_list_iso or not slider_range or len(slider_range) != 2:
            return '1/1/2019', '10/1/2025'
        
        # Convert ISO strings back to datetime objects
        date_list = [pd.to_datetime(d) for d in date_list_iso]
        
        start_date = _index_to_date(slider_range[0], date_list)
        end_date = _index_to_date(slider_range[1], date_list)
        
        return _format_date_for_display(start_date), _format_date_for_display(end_date)
    
    # Callback to handle "All" checkbox logic for countries
    @dash_app.callback(
        [Output('country-checklist-demand', 'value'),
         Output('country-filter-previous-demand', 'data', allow_duplicate=True)],
        Input('country-checklist-demand', 'value'),
        [State('country-filter-previous-demand', 'data')],
        prevent_initial_call=True,
    )
    def handle_country_checklist(selection, country_state):
        """Toggle '(All)' checkbox to select/deselect every country"""
        map_df, chart_df, table_df = load_data()  # Use default sector for country list
        
        # Get all available countries
        all_countries = []
        for df in [map_df, chart_df, table_df]:
            if not df.empty and 'Country' in df.columns:
                all_countries.extend(df['Country'].unique())
        countries = sorted(list(set(all_countries)))
        
        if not countries:
            return selection or [], {'all_selected': False}
        
        selection = selection or []
        state = country_state or {'all_selected': False}
        all_selected = bool(state.get('all_selected'))
        selected_set = set(selection)
        has_all = '(All)' in selected_set
        countries_set = set(countries)
        
        # User unchecked "(All)" => clear all countries
        if all_selected and not has_all and len(selection) == len(countries):
            return [], {'all_selected': False}
        
        # User checked "(All)" => select all countries
        if has_all and not all_selected:
            return ['(All)'] + countries, {'all_selected': True}
        
        # User manually selected all countries without "(All)" => add "(All)"
        if not has_all and selected_set == countries_set:
            return ['(All)'] + countries, {'all_selected': True}
        
        # Regular multi-select - ensure "(All)" is not included if not all countries are selected
        cleaned = [v for v in selection if v != '(All)']
        
        # If all countries are manually selected, add "(All)"
        if set(cleaned) == countries_set:
            return ['(All)'] + cleaned, {'all_selected': True}
        
        return cleaned, {'all_selected': False}

    # Update country legend
    @dash_app.callback(
        [Output('country-legend-container-demand', 'children'),
         Output('selected-countries-store-demand', 'data')],
        [Input('country-checklist-demand', 'value'),
         Input({'type': 'legend-item-demand', 'index': ALL}, 'n_clicks')],
        [State('selected-countries-store-demand', 'data')]
    )
    def update_country_legend(selected_countries, legend_clicks, current_selected):
        """Update country legend and handle legend clicks"""
        map_df, chart_df, table_df = load_data()  # Use default sector for country list
        
        # Get all available countries
        all_countries = []
        for df in [map_df, chart_df, table_df]:
            if not df.empty and 'Country' in df.columns:
                all_countries.extend(df['Country'].unique())
        available_countries = sorted(list(set(all_countries)))
        
        if not available_countries:
            return [], []
        
        # Handle country selection logic based on trigger
        trigger_id = ctx.triggered[0]['prop_id'] if ctx.triggered else '.'
        
        # Default to using checklist value if not triggered by legend
        # or if it's the initial load
        if 'legend-item-demand' not in trigger_id:
            # When triggered by checklist, use the checklist value directly
            if not selected_countries:
                current_selected = []  # Allow empty selection
            elif '(All)' in selected_countries:
                # If (All) is selected, select all countries
                current_selected = available_countries.copy()
            else:
                # Use the checklist selection as-is (filter out any invalid countries)
                current_selected = [c for c in selected_countries if c in available_countries]
        else:
            # If triggered by legend, use the stored state as the baseline
            # Ensure current_selected is a list
            if current_selected is None:
                current_selected = available_countries.copy()
        
        # Handle legend item clicks
        if 'legend-item-demand' in trigger_id:
            import json
            prop_data = json.loads(trigger_id.split('.')[0])
            clicked_country = available_countries[prop_data['index']] if prop_data['index'] < len(available_countries) else None
            
            if clicked_country:
                # If the clicked country is the ONLY currently selected one, toggle back to ALL
                if len(current_selected) == 1 and clicked_country in current_selected:
                    current_selected = available_countries.copy()
                else:
                    # Otherwise, select ONLY this country
                    current_selected = [clicked_country]
        
        # Create legend items
        legend_items = []
        for i, country in enumerate(available_countries):
            is_selected = country in current_selected
            legend_items.append(
                html.Div([
                    html.Div(
                        style={
                            'width': '12px',
                            'height': '12px',
                            'backgroundColor': COUNTRY_COLORS.get(country, '#cccccc'),
                            'display': 'inline-block',
                            'marginRight': '8px',
                            'borderRadius': '2px',
                            'opacity': 1.0 if is_selected else 0.3,
                        }
                    ),
                    html.Span(
                        country,
                        style={
                            'fontSize': '12px',
                            'color': '#333' if is_selected else '#999',
                            'fontWeight': 'normal' if is_selected else 'normal',
                        }
                    )
                ], 
                id={'type': 'legend-item-demand', 'index': i},
                style={
                    'display': 'flex',
                    'alignItems': 'center',
                    'marginBottom': '6px',
                    'cursor': 'pointer',
                    'padding': '2px 4px',
                    'borderRadius': '3px',
                    'backgroundColor': '#f8f9fa' if is_selected else 'transparent',
                },
                n_clicks=0
                )
            )
        
        return legend_items, current_selected

    # Update map title with latest year
    @dash_app.callback(
        Output('europe-map-title', 'children'),
        [Input('sector-radio-demand', 'value'),
         Input('demand-date-range-slider', 'value')],
        [State('demand-date-list-store', 'data')]
    )
    def update_map_title(selected_sector, slider_range, date_list_iso):
        """Update map title to show the latest year within the selected date range"""
        try:
            map_df, chart_df, table_df = load_data(selected_sector)
            
            if map_df.empty:
                return "Natural Gas Demand"
            
            # Apply date filter first
            filtered_df = map_df.copy()
            if slider_range and len(slider_range) == 2 and date_list_iso:
                date_list = [pd.to_datetime(d) for d in date_list_iso]
                start_date = _index_to_date(slider_range[0], date_list)
                end_date = _index_to_date(slider_range[1], date_list)
                filtered_df = filtered_df[(filtered_df['Date'] >= start_date) & (filtered_df['Date'] <= end_date)]
            
            # Get the latest year within the filtered range
            if not filtered_df.empty and 'Year of Date' in filtered_df.columns:
                latest_year = int(filtered_df['Year of Date'].max())
                return f"Natural Gas Demand - {latest_year}"
            else:
                return "Natural Gas Demand"
        except Exception as e:
            print(f"Error updating map title: {e}")
            return "Natural Gas Demand"

    # Update Europe Map
    @dash_app.callback(
        Output('europe-map-demand', 'figure'),
        [Input('demand-date-range-slider', 'value'),
         Input('unit-radio-demand', 'value'),
         Input('sector-radio-demand', 'value'),
         Input('selected-countries-store-demand', 'data')],
        [State('demand-date-list-store', 'data')]
    )
    def update_europe_map(slider_range, selected_unit, selected_sector, selected_countries, date_list_iso):
        """Update the Europe map visualization using shared map utilities"""
        map_df, chart_df, table_df = load_data(selected_sector)
        
        if map_df.empty:
            return create_empty_map("No map data available", height=700)
        
        # Filter data
        filtered_df = map_df.copy()
        
        # First apply date filter using range slider
        if slider_range and len(slider_range) == 2 and date_list_iso:
            date_list = [pd.to_datetime(d) for d in date_list_iso]
            start_date = _index_to_date(slider_range[0], date_list)
            end_date = _index_to_date(slider_range[1], date_list)
            filtered_df = filtered_df[(filtered_df['Date'] >= start_date) & (filtered_df['Date'] <= end_date)]
        
        # Apply unit filter
        if selected_unit and 'Unit' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Unit'] == selected_unit]
        
        # Note: Sector filtering is now handled at the database level in load_data()
        
        # Check for empty country selection
        has_selection = selected_countries is not None and len(selected_countries) > 0
        
        if selected_countries is not None and len(selected_countries) == 0:
             return create_empty_map("No countries selected", height=700)
        
        # Filter by selected countries if not (All)
        if selected_countries and '(All)' not in selected_countries:
            filtered_df = filtered_df[filtered_df['Country'].isin(selected_countries)]
        
        # We also do NOT restrict to the latest year anymore, to ensures that ALL data 
        # within the selected date range is aggregated and displayed.
        # This solves the issue of missing countries that might not have data in the absolute latest month.
        
        if filtered_df.empty:
            return create_empty_map("No data available", height=700)
        
        # Aggregate data by country (sum values across years if multiple)
        agg_df = filtered_df.groupby(['Country', 'Latitude (generated)', 'Longitude (generated)', 'Year of Date']).agg({
            'Value': 'sum'
        }).reset_index()
        
        # Store original country names BEFORE normalization for ISO code lookup
        agg_df['Country_DB_Original'] = agg_df['Country'].copy()
        
        # Create mapping from country names to ISO-3 codes using _iso_for_country function
        agg_df['ISO_Code'] = agg_df['Country_DB_Original'].apply(_iso_for_country)
        
        # Filter out any countries without valid ISO-3 codes
        agg_df = agg_df.dropna(subset=['ISO_Code']).copy()
        
        # Ensure ISO codes are strings and exactly 3 characters
        if not agg_df.empty:
            agg_df['ISO_Code'] = agg_df['ISO_Code'].astype(str)
            agg_df = agg_df[agg_df['ISO_Code'].str.len() == 3].copy()
        
        if agg_df.empty:
            return create_empty_map("No countries with valid ISO codes for map display", height=700)
        
        # Prepare data for the shared map utility
        locations = agg_df['ISO_Code'].astype(str).tolist()
        # Use the original Country column (not Country_DB_Original) to match with filter data
        country_names = agg_df['Country'].tolist()  # This should match the filter country names
        z_values = agg_df['Value'].tolist()
        max_volume = max(z_values) if z_values else 1
        
        
        # Create hover text with structured format matching the professional design
        hover_text = agg_df.apply(
            lambda row: (
                f"<span style='color: #666666; font-family: Arial, sans-serif;'>Country: </span>"
                f"<span style='color: #000000; font-weight: bold;'>{row['Country']}</span><br>"
                f"<span style='color: #666666; font-family: Arial, sans-serif;'>Year of Date: </span>"
                f"<span style='color: #000000; font-weight: bold;'>{int(row.get('Year of Date', 2024))}</span><br>"
                f"<span style='color: #666666; font-family: Arial, sans-serif;'>Value: </span>"
                f"<span style='color: #000000; font-weight: bold;'>{row['Value']:,.1f}</span><br>"
                f"<span style='color: #666666; font-family: Arial, sans-serif;'>Unit: </span>"
                f"<span style='color: #000000; font-weight: bold;'>{selected_unit}</span>"
            ),
            axis=1,
        ).tolist()
        
        # Get country coordinates for labels
        all_countries_df = get_all_countries_with_coordinates()
        countries_in_map = agg_df['Country'].tolist()  # Use original Country column
        countries_df = None
        if not all_countries_df.empty:
            countries_df = all_countries_df[all_countries_df['Country'].isin(countries_in_map)].copy()
        
        # Determine selection parameters for visual styling
        selected_iso = None
        other_isos = None
        single_selected_country = None
        
        # Get ALL available countries from the original map_df (before filtering)
        all_available_countries = map_df['Country'].unique().tolist()
        
        # Create a mapping of all countries to their ISO codes from the ORIGINAL data
        # This is needed to get ISOs for countries that were filtered out
        all_country_iso_map = {}
        temp_df = map_df.copy()
        # Apply same processing as agg_df to get ISO codes
        temp_df['Country_DB_Original'] = temp_df['Country'].copy()
        temp_df['ISO_Code'] = temp_df['Country_DB_Original'].apply(_iso_for_country)
        temp_df = temp_df.dropna(subset=['ISO_Code'])
        temp_df['ISO_Code'] = temp_df['ISO_Code'].astype(str)
        temp_df = temp_df[temp_df['ISO_Code'].str.len() == 3]
        for _, row in temp_df[['Country', 'ISO_Code']].drop_duplicates().iterrows():
            all_country_iso_map[row['Country']] = row['ISO_Code']
        
        # Check if we have a subset of countries selected (not all)
        if selected_countries and len(selected_countries) == 1 and '(All)' not in selected_countries:
            # Single country selected - use single selection mode
            single_selected_country = selected_countries[0]
            
            # Find the ISO code for the selected country
            if single_selected_country in agg_df['Country'].values:
                selected_iso = agg_df.loc[agg_df['Country'] == single_selected_country, 'ISO_Code'].iloc[0]
                
                # Get all other ISOs from ALL available countries (not just filtered ones)
                other_isos = [all_country_iso_map[country] for country in all_available_countries 
                             if country != single_selected_country and country in all_country_iso_map]
                
                print(f"DEBUG MAP: Single country selected: {single_selected_country}, ISO: {selected_iso}")
                print(f"DEBUG MAP: Other ISOs to dim: {other_isos}")
        elif selected_countries and len(selected_countries) > 1 and len(selected_countries) < len(all_available_countries):
            # Multiple countries selected (but not all) - dim the non-selected ones
            other_isos = [all_country_iso_map[country] for country in all_available_countries 
                         if country not in selected_countries and country in all_country_iso_map]
        
        print(f"DEBUG MAP: Calling create_choropleth_map with selected_country={single_selected_country}, selected_iso={selected_iso}")
        
        # Create the map using shared utilities
        fig = create_choropleth_map(
            locations=locations,
            z_values=z_values,
            colorscale=MAP_COLOR_SCALE,
            hover_text=hover_text,
            selected_country=single_selected_country,
            selected_iso=selected_iso,
            other_isos=other_isos,
            countries_df=countries_df,
            height=700,
            zmin=0,
            zmax=max_volume,
            country_names=country_names
        )
        
        # Add custom margin and UI revision for gas demand
        fig.update_layout(
            margin=dict(l=20, r=20, t=20, b=80),
            uirevision='gas-demand-map',
            hovermode='closest',  # Enable hover mode for better country interaction
            hoverlabel=dict(
                bgcolor="white",
                bordercolor="#cccccc",
                font=dict(
                    family="Arial, sans-serif",
                    size=12,
                    color="black"
                ),
                align="left",
                namelength=0  # Hide trace name
            )
        )
        
        # Focus on Europe region by adjusting the map center and zoom
        use_mapbox, _, mapbox_layout = get_mapbox_config()
        if use_mapbox:
            # Create a copy of mapbox_layout and override center and zoom for Europe focus
            europe_mapbox_layout = mapbox_layout.copy()
            europe_mapbox_layout.update({
                'center': dict(lat=54, lon=15),  # Center on Europe
                'zoom': 2.8  # Zoom level for Europe focus
            })
            fig.update_layout(mapbox=europe_mapbox_layout)
        else:
            # Geo fallback with Europe focus
            fig.update_layout(
                geo=dict(
                    scope='europe',
                    projection_type='natural earth',
                    showframe=False,
                    showcoastlines=True,
                    coastlinecolor='rgb(204, 204, 204)',
                    showland=True,
                    landcolor='rgb(243, 243, 243)',
                    showocean=True,
                    oceancolor='white',
                    showlakes=True,
                    lakecolor='white',
                    showrivers=False,
                    showcountries=True,
                    countrycolor='rgb(204, 204, 204)',
                    lonaxis_range=[-12, 35],
                    lataxis_range=[35, 72],
                    center=dict(lat=54, lon=15),
                )
            )
        
        # Add copyright annotation
        copyright_text = "© 2025 Mapbox © OpenStreetMap" if use_mapbox else "© 2025 Natural Earth"
        fig.add_annotation(
            text=copyright_text,
            xref="paper", yref="paper",
            x=0.01, y=0.01,
            showarrow=False,
            font=dict(size=10, color='#666'),
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='rgba(255,255,255,0.8)'
        )
        
        return fig

    # Update Line Chart
    @dash_app.callback(
        Output('europe-chart-demand', 'figure'),
        [Input('demand-date-range-slider', 'value'),
         Input('unit-radio-demand', 'value'),
         Input('sector-radio-demand', 'value'),
         Input('selected-countries-store-demand', 'data'),
         Input('chart-granularity-store-demand', 'data'),
         Input('chart-selection-store-demand', 'data')],
        [State('demand-date-list-store', 'data')]
    )
    def update_europe_chart(slider_range, selected_unit, selected_sector, selected_countries, granularity, selection, date_list_iso):
        """Update the Europe line chart visualization with granularity support and highlighting"""
        
        if not selected_countries or len(selected_countries) == 0:
            return go.Figure().add_annotation(text="No countries selected", 
                                            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Use database query with granularity support (same approach as yearly dashboard)
        unit_map = {'Million Cubic Meter': 'Mcm', 'Gigawatt-hour': 'GWh'}
        db_unit = unit_map.get(selected_unit, 'Mcm')
        
        # Build sector filter - convert to list for SQL query
        if selected_sector and selected_sector != 'All':
            selected_sectors = [selected_sector]
        else:
            selected_sectors = ['Industrial', 'Household', 'Power']
        
        # SQL Query with parameterized granularity (same pattern as yearly dashboard)
        query = """
        SELECT
            gd.country AS "Country",
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
            CASE 
                WHEN gd.unit = 'Mcm' THEN 'Million Cubic Meter'
                WHEN gd.unit = 'GWh' THEN 'Gigawatt-hour'
                ELSE gd.unit
            END AS "Unit",
            ROUND(SUM(gd.value), 2) AS "Value"
        FROM glng_gas_demand gd
        LEFT JOIN dim_country dc ON gd.country_id = dc.dim_country_id
        WHERE LOWER(dc.region) = 'europe'
          AND dc.latitude IS NOT NULL
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
            gd.country,
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
            CASE 
                WHEN gd.unit = 'Mcm' THEN 'Million Cubic Meter'
                WHEN gd.unit = 'GWh' THEN 'Gigawatt-hour'
                ELSE gd.unit
            END
        ORDER BY
            "Country",
            EXTRACT(YEAR FROM gd.date),
            "Quarter of Date",
            "Month Num",
            "Day of Date";
        """
        
        # Parameters for the query (same pattern as yearly dashboard)
        params = {
            'granularity': granularity,
            'selected_sectors': selected_sectors,
            'selected_countries': selected_countries,
            'unit': db_unit
        }
        
        try:
            results = execute_query(query, params)
            df = pd.DataFrame(results)
        except Exception as e:
            print(f"Error executing chart query: {e}")
            return go.Figure().add_annotation(text="Database query error", 
                                            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

        if df.empty:
            return go.Figure().add_annotation(text="No data available for selected filters", 
                                            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Process data similar to yearly dashboard
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce').fillna(0).astype(float)
        df['Year Count'] = df['Year of Date'].fillna('').astype(str)
        df['Quarter Label'] = df['Quarter of Date'].fillna('').astype(str)
        
        # Map Month Num to Name
        month_map_num = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April', 
            5: 'May', 6: 'June', 7: 'July', 8: 'August', 
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }
        df['Month Label'] = df['Month Num'].map(month_map_num)
        
        if granularity == 'month' or granularity == 'day':
            df['Month Label'] = df['Month Label'].fillna('Unknown')
        else:
            df['Month Label'] = df['Month Label'].fillna('')

        df['Day Label'] = df['Day of Date'].apply(lambda l: str(int(l)) if pd.notnull(l) and str(l) != '' else '')

        # Create proper date column for line chart
        if granularity == 'year':
            df['Date'] = pd.to_datetime(df['Year of Date'], format='%Y')
        elif granularity == 'quarter':
            # For quarters, use the first month of each quarter
            quarter_to_month = {'Q1': '01', 'Q2': '04', 'Q3': '07', 'Q4': '10'}
            df['Date'] = df.apply(lambda row: pd.to_datetime(f"{row['Year Count']}-{quarter_to_month.get(row['Quarter Label'], '01')}-01"), axis=1)
        elif granularity == 'month':
            df['Date'] = pd.to_datetime(df['Year Count'] + '-' + df['Month Label'], format='%Y-%B', errors='coerce')
        elif granularity == 'day':
            df['Date'] = pd.to_datetime(df['Year Count'] + '-' + df['Month Num'].astype(str) + '-' + df['Day Label'], format='%Y-%m-%d', errors='coerce')
        
        # Drop rows with invalid dates
        df = df.dropna(subset=['Date'])
        
        # Apply date filter using range slider
        if slider_range and len(slider_range) == 2 and date_list_iso:
            date_list = [pd.to_datetime(d) for d in date_list_iso]
            start_date = _index_to_date(slider_range[0], date_list)
            end_date = _index_to_date(slider_range[1], date_list)
            df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
        
        if df.empty:
            return go.Figure().add_annotation(text="No data available for selected date range", 
                                            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Create line chart with highlighting support
        fig = go.Figure()
        
        for country in selected_countries:
            country_df = df[df['Country'] == country]
            if country_df.empty:
                continue
            
            # Sort by date for proper line connections
            country_df = country_df.sort_values('Date')
            
            # Determine line style based on selection
            line_color = COUNTRY_COLORS.get(country, '#cccccc')
            line_width = 2
            opacity = 1.0
            marker_sizes = [0] * len(country_df)  # Hide markers by default (array)
            
            # Apply highlighting if there's a selection
            if selection:
                selected_country = selection.get('country', '')
                if country == selected_country:
                    # Highlighted line - make it more prominent
                    line_width = 4
                    opacity = 1.0
                    marker_sizes = [8] * len(country_df)  # Show larger markers on selected line
                else:
                    # Dimmed line
                    opacity = 0.3
                    line_width = 1
                    marker_sizes = [0] * len(country_df)  # Keep markers hidden on dimmed lines
            
            # Create custom hover data
            hover_text = []
            for _, row in country_df.iterrows():
                if granularity == 'year':
                    date_str = f"Year {int(row['Year of Date'])}"
                elif granularity == 'quarter':
                    date_str = f"{row['Quarter Label']} {int(row['Year of Date'])}"
                elif granularity == 'month':
                    date_str = f"{row['Month Label']} {int(row['Year of Date'])}"
                elif granularity == 'day':
                    date_str = f"{row['Month Label']} {int(row['Day of Date'])}, {int(row['Year of Date'])}"
                else:
                    date_str = str(row['Date'])
                
                hover_text.append(
                    f"<span style='color: #666666; font-family: Arial, sans-serif;'>Country: </span>"
                    f"<span style='color: #000000; font-weight: bold;'>{country}</span><br>"
                    f"<span style='color: #666666; font-family: Arial, sans-serif;'>Date: </span>"
                    f"<span style='color: #000000; font-weight: bold;'>{date_str}</span><br>"
                    f"<span style='color: #666666; font-family: Arial, sans-serif;'>Value: </span>"
                    f"<span style='color: #000000; font-weight: bold;'>{row['Value']:,.2f}</span><br>"
                    f"<span style='color: #666666; font-family: Arial, sans-serif;'>Unit: </span>"
                    f"<span style='color: #000000; font-weight: bold;'>{selected_unit}</span>"
                )
            
            # Add trace with markers only visible on hover or when selected
            fig.add_trace(go.Scatter(
                x=country_df['Date'],
                y=country_df['Value'],
                mode='lines+markers',
                name=country,
                line=dict(color=line_color, width=line_width),
                marker=dict(
                    size=marker_sizes,  # Array of marker sizes
                    color=line_color,
                    line=dict(color='white', width=1)  # White border around markers
                ),
                opacity=opacity,
                hoverinfo='text',
                hovertext=hover_text,
                customdata=[[country, granularity, selected_unit]] * len(country_df),
                hoverlabel=dict(
                    bgcolor="white",
                    bordercolor="#cccccc",
                    font=dict(
                        family="Arial, sans-serif",
                        size=12,
                        color="black"
                    ),
                    align="left"
                ),
                # Show markers on hover
                hoveron='points+fills'
            ))
        
        # Update layout
        fig.update_layout(
            height=700,
            margin=dict(l=60, r=20, t=20, b=40),  # Increased left margin from 20 to 60 for Y-axis labels
            paper_bgcolor='white',
            plot_bgcolor='white',
            xaxis_title="",
            yaxis_title="",
            showlegend=False,
            hoverlabel=dict(
                bgcolor="white",
                bordercolor="#cccccc",
                font=dict(
                    family="Arial, sans-serif",
                    size=12,
                    color="black"
                ),
                align="left"
            )
        )
        
        # Set x-axis range to show the full selected date range
        if slider_range and len(slider_range) == 2 and date_list_iso:
            date_list = [pd.to_datetime(d) for d in date_list_iso]
            start_date = _index_to_date(slider_range[0], date_list)
            end_date = _index_to_date(slider_range[1], date_list)
            fig.update_xaxes(range=[start_date, end_date])
        
        return fig

    # Update Table
    @dash_app.callback(
        Output('europe-table-demand', 'children'),
        [Input('demand-date-range-slider', 'value'),
         Input('unit-radio-demand', 'value'),
         Input('sector-radio-demand', 'value'),
         Input('selected-countries-store-demand', 'data'),
         Input('table-granularity-store-demand', 'data')],
        [State('demand-date-list-store', 'data')]
    )
    def update_europe_table(slider_range, selected_unit, selected_sector, selected_countries, table_granularity, date_list_iso):
        """Update the Europe data table with granularity support"""
        
        if not selected_countries or len(selected_countries) == 0:
            return html.Div("No countries selected", style={'padding': '20px', 'textAlign': 'center'})
        
        # Use database query with granularity support (same approach as yearly dashboard)
        unit_map = {'Million Cubic Meter': 'Mcm', 'Gigawatt-hour': 'GWh'}
        db_unit = unit_map.get(selected_unit, 'Mcm')
        
        # Build sector filter - convert to list for SQL query
        if selected_sector and selected_sector != 'All':
            selected_sectors = [selected_sector]
        else:
            selected_sectors = ['Industrial', 'Household', 'Power']
        
        # SQL Query with parameterized granularity - aggregate by Country only (no Sector breakdown)
        query = """
        SELECT
            gd.country                                AS "Country",
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

        FROM glng_gas_demand gd
        JOIN dim_country dc
            ON gd.country_id = dc.dim_country_id

        /* Dynamic time bucket */
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
          AND dc.latitude IS NOT NULL
          AND gd.unit = :unit
          AND gd.sector = ANY(:selected_sectors)
          AND dc.country_long_name = ANY(:selected_countries)
          AND gd.to_be_deleted = false
          AND EXTRACT(YEAR FROM gd.date) >= 2019
          AND EXTRACT(YEAR FROM gd.date) < 2025

        GROUP BY
            gd.country,
            period

        ORDER BY
            "Year of Date" DESC,
            "Quarter of Date",
            "Month of Date",
            "Day of Date",
            "Country";
        """
        
        # Parameters for the query (same pattern as yearly dashboard)
        params = {
            'granularity': table_granularity,
            'selected_sectors': selected_sectors,
            'selected_countries': selected_countries,
            'unit': db_unit,
            'display_unit': selected_unit
        }
        
        try:
            results = execute_query(query, params)
            df = pd.DataFrame(results)
        except Exception as e:
            return html.Div(f"Error loading table data: {e}")
        
        if df.empty:
            return html.Div("No data found")

        # Apply date filter using range slider (after getting data from DB)
        if slider_range and len(slider_range) == 2 and date_list_iso:
            date_list = [pd.to_datetime(d) for d in date_list_iso]
            start_date = _index_to_date(slider_range[0], date_list)
            end_date = _index_to_date(slider_range[1], date_list)
            
            # Ensure _period_sort is datetime and handle timezone awareness
            df['_period_sort'] = pd.to_datetime(df['_period_sort'])
            
            # Make dates timezone-aware if _period_sort is timezone-aware
            if df['_period_sort'].dt.tz is not None:
                start_date = pd.Timestamp(start_date).tz_localize('UTC')
                end_date = pd.Timestamp(end_date).tz_localize('UTC')
            
            # Filter by the period column
            df = df[(df['_period_sort'] >= start_date) & (df['_period_sort'] <= end_date)]
        
        if df.empty:
            return html.Div("No data available for selected date range", style={'padding': '20px', 'textAlign': 'center'})

        # Determine active hierarchy levels based on data (same logic as yearly dashboard)
        levels = ['Year of Date']
        if df['Quarter of Date'].notna().any(): 
            levels.append('Quarter of Date')
        
        # If we have daily data, we use the combined 'Day of Date' label as the bottom level
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
        
        # Build the columns hierarchy
        # Use _period_sort for reliable time sorting (Year DESC, then internal time ASC)
        time_cols_df = df[levels + ['_period_sort']].drop_duplicates()
        
        # We want Year to be DESC, but Quarters/Months/Days within the year to be ASC
        time_cols_df = time_cols_df.sort_values(
            by=['Year of Date', '_period_sort'],
            ascending=[False, True]
        )
        
        # Create list of tuples for columns
        cols_tuples = [tuple(row[l] for l in levels) for _, row in time_cols_df.iterrows()]
        
        # Pivot the data by Country only (no Sector)
        pivot_df = df.pivot_table(
            index=['Country'],
            columns=levels,
            values='Value',
            aggfunc='sum'
        )
        
        # Ensure pivot_df columns match cols_tuples order and structure
        if len(levels) == 1:
            pivot_df = pivot_df.reindex(columns=[t[0] for t in cols_tuples])
        else:
            pivot_df = pivot_df.reindex(columns=pd.MultiIndex.from_tuples(cols_tuples))
        
        # Build HTML Table with hierarchical headers
        thead_rows = []
        num_header_rows = len(levels)
        
        # Build hierarchical headers
        header_rows_content = [[] for _ in range(num_header_rows)]
        
        for depth in range(num_header_rows):
            current_vals_at_depth = [t[depth] for t in cols_tuples]
            
            # Group consecutive values
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
                grouped.append((curr_val, count))  # Add the last group
            
            # Create THs
            for label, span in grouped:
                header_rows_content[depth].append(
                    html.Th(label, colSpan=span, style={'textAlign': 'center', 'border': '1px solid #ddd', 'padding': '5px', 'backgroundColor': '#f9f9f9'})
                )
        
        # First header row (Country and top-level time headers, plus Total column)
        first_header_row_ths = [
            html.Th("Country", rowSpan=num_header_rows, style={'position': 'sticky', 'left': 0, 'zIndex': 20, 'backgroundColor': 'white', 'border': '1px solid #ddd', 'padding': '8px', 'width': '120px', 'minWidth': '120px'})
        ] + header_rows_content[0] + [
            html.Th("Total", rowSpan=num_header_rows, style={'textAlign': 'center', 'border': '1px solid #ddd', 'padding': '8px', 'backgroundColor': '#f9f9f9', 'fontWeight': 'bold'})
        ]
        thead_rows.append(html.Tr(first_header_row_ths))
        
        # Subsequent header rows (only time headers)
        for i in range(1, num_header_rows):
            thead_rows.append(html.Tr(header_rows_content[i]))
        
        # Table Body
        tbody_rows = []
        
        # Sort countries alphabetically
        pivot_df = pivot_df.sort_index()
        
        # Iterate through each country
        for country in pivot_df.index:
            row_cells = []
            
            # Country Cell
            row_cells.append(html.Td(country, 
                                    style={'position': 'sticky', 'left': 0, 'zIndex': 10, 'backgroundColor': 'white', 'fontWeight': 'bold', 'border': '1px solid #ddd', 'padding': '8px', 'width': '120px', 'minWidth': '120px'}))
            
            # Data Cells
            row_total = 0
            try:
                series = pivot_df.loc[country]
                
                # Iterate through our defined sorted columns (cols_tuples)
                for col_tuple in cols_tuples:
                    col_key = col_tuple if len(levels) > 1 else col_tuple[0]
                    
                    val = series.get(col_key, 0)
                    
                    # Handle NaN
                    if pd.isna(val): 
                        val = 0
                    else:
                        row_total += val
                    
                    row_cells.append(html.Td(f"{val:,.0f}" if val != 0 else "-", 
                                            style={'textAlign': 'right', 'border': '1px solid #ddd', 'padding': '5px'}))
                    
            except KeyError:
                # Handle missing data
                for i in range(len(cols_tuples)):
                    row_cells.append(html.Td("-", style={'textAlign': 'right', 'border': '1px solid #ddd', 'padding': '5px'}))
            
            # Add Total column at the end
            row_cells.append(html.Td(f"{row_total:,.0f}" if row_total != 0 else "-", 
                                    style={'textAlign': 'right', 'border': '1px solid #ddd', 'padding': '5px', 'fontWeight': 'bold', 'backgroundColor': '#f9f9f9'}))
            
            tbody_rows.append(html.Tr(row_cells))

        return html.Div(
            html.Table(
                [html.Thead(thead_rows), html.Tbody(tbody_rows)],
                style={'borderCollapse': 'collapse', 'width': '100%', 'fontFamily': 'Arial', 'fontSize': '12px'}
            ),
            style={'overflowX': 'auto', 'maxWidth': '100%', 'width': '100%'}
        )

    # Export Map CSV
    @dash_app.callback(
        Output("download-demand-map-csv", "data"),
        Input("export-demand-map-btn", "n_clicks"),
        [State('demand-date-range-slider', 'value'),
         State('unit-radio-demand', 'value'),
         State('sector-radio-demand', 'value'),
         State('selected-countries-store-demand', 'data'),
         State('demand-date-list-store', 'data')],
        prevent_initial_call=True,
    )
    def export_map_csv(n_clicks, slider_range, selected_unit, selected_sector, selected_countries, date_list_iso):
        """Export map data to CSV"""
        if n_clicks == 0:
            return no_update
        
        map_df, chart_df, table_df = load_data(selected_sector)
        
        if map_df.empty:
            return no_update
        
        # Apply same filters as the map
        filtered_df = map_df.copy()
        
        if slider_range and len(slider_range) == 2 and date_list_iso:
            date_list = [pd.to_datetime(d) for d in date_list_iso]
            start_date = _index_to_date(slider_range[0], date_list)
            end_date = _index_to_date(slider_range[1], date_list)
            filtered_df = filtered_df[(filtered_df['Date'] >= start_date) & (filtered_df['Date'] <= end_date)]
        
        if selected_unit and 'Unit' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Unit'] == selected_unit]
        
        if selected_sector and selected_sector != 'All' and 'Sector' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Sector'] == selected_sector]
        
        if selected_countries:
            filtered_df = filtered_df[filtered_df['Country'].isin(selected_countries)]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"europe_gas_demand_map_{timestamp}.csv"
        
        return dcc.send_data_frame(filtered_df.to_csv, filename, index=False)

    # Export Chart CSV
    @dash_app.callback(
        Output("download-demand-chart-csv", "data"),
        Input("export-demand-chart-btn", "n_clicks"),
        [State('demand-date-range-slider', 'value'),
         State('unit-radio-demand', 'value'),
         State('sector-radio-demand', 'value'),
         State('selected-countries-store-demand', 'data'),
         State('demand-date-list-store', 'data')],
        prevent_initial_call=True,
    )
    def export_chart_csv(n_clicks, slider_range, selected_unit, selected_sector, selected_countries, date_list_iso):
        """Export chart data to CSV"""
        if n_clicks == 0:
            return no_update
        
        map_df, chart_df, table_df = load_data(selected_sector)
        
        if chart_df.empty:
            return no_update
        
        # Apply same filters as the chart
        filtered_df = chart_df.copy()
        
        if slider_range and len(slider_range) == 2 and date_list_iso:
            date_list = [pd.to_datetime(d) for d in date_list_iso]
            start_date = _index_to_date(slider_range[0], date_list)
            end_date = _index_to_date(slider_range[1], date_list)
            filtered_df = filtered_df[(filtered_df['Date'] >= start_date) & (filtered_df['Date'] <= end_date)]
        
        if selected_unit and 'Unit' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Unit'] == selected_unit]
        
        if selected_sector and selected_sector != 'All' and 'Sector' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Sector'] == selected_sector]
        
        if selected_countries:
            filtered_df = filtered_df[filtered_df['Country'].isin(selected_countries)]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"europe_gas_demand_chart_{timestamp}.csv"
        
        return dcc.send_data_frame(filtered_df.to_csv, filename, index=False)

    # Export Table CSV
    @dash_app.callback(
        Output("download-demand-table-csv", "data"),
        Input("export-demand-table-btn", "n_clicks"),
        [State('demand-date-range-slider', 'value'),
         State('unit-radio-demand', 'value'),
         State('sector-radio-demand', 'value'),
         State('selected-countries-store-demand', 'data'),
         State('demand-date-list-store', 'data')],
        prevent_initial_call=True,
    )
    def export_table_csv(n_clicks, slider_range, selected_unit, selected_sector, selected_countries, date_list_iso):
        """Export table data to CSV"""
        if n_clicks == 0:
            return no_update
        
        map_df, chart_df, table_df = load_data(selected_sector)
        
        if table_df.empty:
            return no_update
        
        # Apply same filters as the table
        filtered_df = table_df.copy()
        
        if slider_range and len(slider_range) == 2 and date_list_iso:
            date_list = [pd.to_datetime(d) for d in date_list_iso]
            start_date = _index_to_date(slider_range[0], date_list)
            end_date = _index_to_date(slider_range[1], date_list)
            filtered_df = filtered_df[(filtered_df['Date'] >= start_date) & (filtered_df['Date'] <= end_date)]
        
        if selected_unit and 'Unit' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Unit'] == selected_unit]
        
        if selected_sector and selected_sector != 'All' and 'Sector' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Sector'] == selected_sector]
        
        if selected_countries:
            filtered_df = filtered_df[filtered_df['Country'].isin(selected_countries)]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"europe_gas_demand_table_{timestamp}.csv"
        
        return dcc.send_data_frame(filtered_df.to_csv, filename, index=False)

    # Map click interaction to update country selection
    @dash_app.callback(
        Output('country-checklist-demand', 'value', allow_duplicate=True),
        Output('country-filter-previous-demand', 'data', allow_duplicate=True),
        Input('europe-map-demand', 'clickData'),
        State('country-checklist-demand', 'value'),
        State('country-checklist-demand', 'options'),
        prevent_initial_call=True
    )
    def handle_map_click(clickData, current_selection, options):
        """Handle map clicks to update country selection using shared utility"""
        if not clickData:
            return no_update, no_update
            
        try:
            print(f"DEBUG: Map clicked! clickData: {clickData}")
            
            # Extract all country options (excluding "(All)")
            # This ensures we pass the exact available countries to the reset handler
            all_countries = []
            if options:
                all_countries = [opt['value'] for opt in options if opt['value'] != '(All)']
            
            # Fallback: If options didn't give us countries (e.g. state issue), load from data
            if not all_countries:
                print("DEBUG: Options empty or missing countries, reloading from data")
                map_df, chart_df, table_df = load_data()  # Use default sector for country list
                countries_set = set()
                for df in [map_df, chart_df, table_df]:
                    if not df.empty and 'Country' in df.columns:
                        countries_set.update(df['Country'].unique())
                all_countries = sorted(list(countries_set))
                
            if not all_countries:
                print("DEBUG: Could not determine available countries")
                return no_update, no_update
            
            # Enhanced background click detection
            point = clickData.get("points", [{}])[0]
            print(f"DEBUG: Point data: {point}")
            
            is_background_click = False
            clicked_country = None
            
            # Check for background click markers
            if "customdata" in point and point["customdata"]:
                print(f"DEBUG: customdata found: {point['customdata']}")
                if isinstance(point["customdata"], list) and len(point["customdata"]) > 0:
                    if point["customdata"][0] == "__BACKGROUND_CLICK__":
                        is_background_click = True
                        print("DEBUG: Background click detected via customdata list")
                    else:
                        clicked_country = point["customdata"][0]
                        print(f"DEBUG: Country clicked via customdata: {clicked_country}")
                elif point["customdata"] == "__BACKGROUND_CLICK__":
                    is_background_click = True
                    print("DEBUG: Background click detected via customdata string")
                else:
                    clicked_country = point["customdata"]
                    print(f"DEBUG: Country clicked via customdata string: {clicked_country}")
            
            # Check trace name for background layers
            if "curveNumber" in point and not is_background_click and not clicked_country:
                try:
                    # Get the trace from the figure if available
                    trace_name = ""
                    if "data" in point:
                        trace_name = point.get("data", {}).get("name", "")
                    
                    print(f"DEBUG: Trace name: {trace_name}")
                    
                    # Check if it's a background layer
                    if trace_name in ["ocean_grid", "world_background", "atlantic_fill", 
                                     "pacific_west_fill", "pacific_east_fill", "ocean_background", 
                                     "background_fill", "europe_background_fill"]:
                        is_background_click = True
                        print(f"DEBUG: Background click detected via trace name: {trace_name}")
                except (KeyError, IndexError, AttributeError) as e:
                    print(f"DEBUG: Error checking trace name: {e}")
            
            # If background click detected, reset to all countries
            if is_background_click:
                print("DEBUG: Background/ocean click detected - resetting to all countries")
                new_selection = ['(All)'] + all_countries
                new_state = {'all_selected': True}
                return new_selection, new_state
            
            # Determine current state
            current_selection = current_selection or []
            resolved_countries = [c for c in current_selection if c != '(All)' and c in all_countries]
            
            print(f"DEBUG: Current selection: {current_selection}")
            print(f"DEBUG: Resolved countries: {resolved_countries}")
            print(f"DEBUG: Clicked country: {clicked_country}")
            print(f"DEBUG: Is background click: {is_background_click}")
            
            # If exactly one country is selected, ANY click should reset to all
            if len(resolved_countries) == 1:
                selected_country_name = resolved_countries[0]
                
                # If clicked the same country, reset to all
                if clicked_country == selected_country_name:
                    print(f"DEBUG: Same country clicked ({clicked_country}) - resetting to all")
                    new_selection = ['(All)'] + all_countries
                    new_state = {'all_selected': True}
                    return new_selection, new_state
                
                # If clicked a different valid country (including dimmed countries), reset to all
                if clicked_country and clicked_country in all_countries and clicked_country != selected_country_name:
                    print(f"DEBUG: Different country clicked ({clicked_country}) - resetting to all (was dimmed)")
                    new_selection = ['(All)'] + all_countries
                    new_state = {'all_selected': True}
                    return new_selection, new_state
                
                # If clicked something else (ocean, unrecognized area, or no country detected), reset to all
                # This is the catch-all for any click when a single country is selected
                print(f"DEBUG: Other click while single country selected - resetting to all")
                new_selection = ['(All)'] + all_countries
                new_state = {'all_selected': True}
                return new_selection, new_state
            
            # If all countries are shown (or multiple countries selected)
            # Clicking a valid country selects only that country
            if clicked_country and clicked_country in all_countries:
                print(f"DEBUG: Country clicked while all shown - selecting only {clicked_country}")
                new_selection = [clicked_country]
                new_state = {'all_selected': False}
                return new_selection, new_state
            
            # If clicked something unrecognized when all countries shown, keep current selection
            print("DEBUG: Unrecognized click - keeping current selection")
            return no_update, no_update
            
        except Exception as e:
            print(f"Map click error: {e}")
            import traceback
            traceback.print_exc()
            return no_update, no_update

    # Map Home Button - Reset map view
    @dash_app.callback(
        Output('europe-map-demand', 'figure', allow_duplicate=True),
        Input('map-home-btn-demand', 'n_clicks'),
        State('europe-map-demand', 'figure'),
        prevent_initial_call=True
    )
    def reset_map_view(n_clicks, current_figure):
        """Reset map to default view"""
        if not n_clicks or not current_figure:
            return no_update
        
        # Reset the map layout to default zoom and center
        if 'layout' in current_figure and 'mapbox' in current_figure['layout']:
            current_figure['layout']['mapbox']['zoom'] = 3
            current_figure['layout']['mapbox']['center'] = {'lat': 54, 'lon': 15}
        
        return current_figure
    
    # Chart Home Button - Reset chart selection
    @dash_app.callback(
        Output('chart-selection-store-demand', 'data', allow_duplicate=True),
        Input('chart-home-btn-demand', 'n_clicks'),
        prevent_initial_call=True
    )
    def reset_chart_selection(n_clicks):
        """Reset chart selection (clear highlighting)"""
        if not n_clicks:
            return no_update
        return None
    
    # Map Camera Button - Download map as image
    dash_app.clientside_callback(
        """
        function(n_clicks) {
            if (n_clicks) {
                // Trigger Plotly's download image functionality
                var mapElement = document.getElementById('europe-map-demand');
                if (mapElement) {
                    Plotly.downloadImage(mapElement, {
                        format: 'png',
                        width: 1200,
                        height: 700,
                        filename: 'europe_gas_demand_map'
                    });
                }
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('gas-demand-hover-trigger', 'children', allow_duplicate=True),
        Input('map-camera-btn-demand', 'n_clicks'),
        prevent_initial_call=True
    )
    
    # Chart Camera Button - Download chart as image
    dash_app.clientside_callback(
        """
        function(n_clicks) {
            if (n_clicks) {
                // Trigger Plotly's download image functionality
                var chartElement = document.getElementById('europe-chart-demand');
                if (chartElement) {
                    Plotly.downloadImage(chartElement, {
                        format: 'png',
                        width: 1200,
                        height: 700,
                        filename: 'europe_gas_demand_chart'
                    });
                }
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('gas-demand-hover-trigger', 'children', allow_duplicate=True),
        Input('chart-camera-btn-demand', 'n_clicks'),
        prevent_initial_call=True
    )
