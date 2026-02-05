"""
Asian Gas Demand - Monthly Demand by Country
Monthly gas demand analytics by country with interactive map, charts, and tables
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, dash_table, State, ALL, ctx, no_update
import os
from datetime import datetime, timedelta
import time
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
        return pd.Timestamp('2019-01-01')
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

# Color palette for Asian countries - professional color scheme
COUNTRY_COLORS = {
    'Vietnam': '#4472C4',           # Dark blue
    'Thailand': '#70ADD8',          # Light blue
    'Taiwan': '#FF8C00',            # Orange
    'South Korea': '#FFB366',       # Light orange
    'Singapore': '#228B22',         # Green
    'Philippines': '#90EE90',       # Light green
    'Pakistan': '#B8860B',          # Dark goldenrod
    'New Zealand': '#F0E68C',       # Khaki/light yellow
    'Malaysia': '#008B8B',          # Dark cyan/teal
    'Japan': '#40E0D0',             # Turquoise
    'India': '#DC143C',             # Crimson red
    'China': '#FF69B4',             # Hot pink
    'Indonesia': '#696969',         # Dim gray
    'Bangladesh': '#A0A0A0',        # Gray
    'Myanmar': '#DA70D6',           # Orchid
    'Brunei': '#FFB6C1',            # Light pink
    'Sri Lanka': '#8B008B',         # Dark magenta
    'Cambodia': '#DDA0DD',          # Plum
    'Laos': '#8B4513',              # Saddle brown
    'Mongolia': '#D2B48C',          # Tan
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

def _iso_for_country(country):
    """Return ISO Alpha-3 code for a country, using centralized mapping with Asian country additions."""
    # Add missing Asian countries to the mapping
    asian_additions = {
        'Taiwan': 'TWN',
        'New Zealand': 'NZL',
    }
    
    # Check Asian additions first
    if country in asian_additions:
        return asian_additions[country]
    
    # Use centralized mapping
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
            sector_condition = "AND p.sector IN ('Household', 'Industrial', 'Other', 'Power')"
        
        # Map Query: Replacement of csv file Asia Map_Demand by Year_data.csv
        map_query = f"""
        SELECT
            p.country AS "Country",
            EXTRACT(YEAR FROM p.date) AS "Year of Date",
            CASE 
                WHEN p.unit = 'Mcm' THEN 'Billion Cubic Meter'
                WHEN p.unit = 'GWh' THEN 'Gigawatt-hour'
                ELSE p.unit
            END AS "Unit",
            q.latitude AS "Latitude",
            q.longitude AS "Longitude",
            CASE 
                WHEN p.unit = 'Mcm' THEN ROUND(SUM(p.value) / 1000.0, 6)
                ELSE ROUND(SUM(p.value), 6)
            END AS "Value"
        FROM dev.glng_gas_demand p
        LEFT JOIN dim_country q
        ON q.dim_country_id = p.country_id
        WHERE LOWER(q.region) = 'asia' 
        AND q.latitude IS NOT NULL 
        {sector_condition}
        GROUP BY
            p.country,
            EXTRACT(YEAR FROM p.date),
            CASE 
                WHEN p.unit = 'Mcm' THEN 'Billion Cubic Meter'
                WHEN p.unit = 'GWh' THEN 'Gigawatt-hour'
                ELSE p.unit
            END,
            q.latitude,
            q.longitude,
            p.unit
        ORDER BY
            p.country DESC,
            EXTRACT(YEAR FROM p.date) DESC;
        """
        
        # Chart Query Day of Month: Replacement of csv file Asia Line Chart_Total Demand by Country_data.csv
        chart_query = f"""
        SELECT
            DATE_TRUNC('month', p.date)::date AS "Day of Date",
            p.country AS "Country",
            CASE 
                WHEN p.unit = 'Mcm' THEN 'Billion Cubic Meter'
                WHEN p.unit = 'GWh' THEN 'Gigawatt-hour'
                ELSE p.unit
            END AS "Unit",
            CASE 
                WHEN p.unit = 'Mcm' THEN ROUND(SUM(p.value) / 1000.0, 3)
                ELSE ROUND(SUM(p.value), 2)
            END AS "Value"
        FROM dev.glng_gas_demand p
        LEFT JOIN dim_country q
        ON q.dim_country_id = p.country_id
        WHERE LOWER(q.region) = 'asia'
        AND q.latitude IS NOT NULL
        {sector_condition}
        GROUP BY
            DATE_TRUNC('month', p.date),
            p.country,
            CASE 
                WHEN p.unit = 'Mcm' THEN 'Billion Cubic Meter'
                WHEN p.unit = 'GWh' THEN 'Gigawatt-hour'
                ELSE p.unit
            END,
            p.unit
        ORDER BY
            "Day of Date",
            "Country";
        """
        
        # Datatable Query: Replacement of csv file Total Gas Demand by Country_data.csv
        table_query = f"""
        SELECT
            p.country AS "Country",
            EXTRACT(YEAR FROM p.date) AS "Year of Date",
            CONCAT('Q', EXTRACT(QUARTER FROM p.date)) AS "Quarter of Date",
            TO_CHAR(p.date, 'FMMonth') AS "Month of Date",
            1 AS "Day of Date",
            CASE 
                WHEN p.unit = 'Mcm' THEN 'Billion Cubic Meter'
                WHEN p.unit = 'GWh' THEN 'Gigawatt-hour'
                ELSE p.unit
            END AS "Unit",
            CASE 
                WHEN p.unit = 'Mcm' THEN ROUND(SUM(p.value) / 1000.0, 6)
                ELSE ROUND(SUM(p.value), 6)
            END AS "Value",
            DATE_TRUNC('month', p.date) AS month_sort
        FROM dev.glng_gas_demand p
        LEFT JOIN dim_country q
        ON q.dim_country_id = p.country_id
        WHERE LOWER(q.region) = 'asia'
        AND q.latitude IS NOT NULL
        {sector_condition}
        GROUP BY
            p.country,
            EXTRACT(YEAR FROM p.date),
            EXTRACT(QUARTER FROM p.date),
            TO_CHAR(p.date, 'FMMonth'),
            DATE_TRUNC('month', p.date),
            CASE 
                WHEN p.unit = 'Mcm' THEN 'Billion Cubic Meter'
                WHEN p.unit = 'GWh' THEN 'Gigawatt-hour'
                ELSE p.unit
            END,
            p.unit
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
        
        print("Falling back to CSV data loading...")
        
        # Fallback to original CSV loading
        try:
            # Get the directory path
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, '..', 'data', 'Asian-Gas-Demand-Monthly-Demand-by-Country')
            
            # Load the three CSV files
            map_file = os.path.join(data_dir, 'Asia Map_Demand by Year_data.csv')
            chart_file = os.path.join(data_dir, 'Asia Line Chart_Total Demand by Country_data.csv')
            table_file = os.path.join(data_dir, 'Total Gas Demand by Country_data.csv')
            
            # Load map data (annual data by country)
            map_df = pd.read_csv(map_file)
            map_df['Date'] = pd.to_datetime(map_df['Year of Date'], format='%Y')
            # Convert unit names to match database output
            if 'adjusted_unit' in map_df.columns:
                map_df['Unit'] = map_df['adjusted_unit'].replace({'Mcm': 'Billion Cubic Meter'})
                # Convert Mcm values to Bcm by dividing by 1000
                map_df['Value'] = map_df.apply(
                    lambda row: row['adjusted_unit_value'] / 1000.0 if row['adjusted_unit'] == 'Mcm' 
                    else row['adjusted_unit_value'], axis=1
                )
            else:
                map_df['Unit'] = 'Billion Cubic Meter'
                map_df['Value'] = map_df.get('adjusted_unit_value', 0)
            
            # Load chart data (monthly time series)
            chart_df = pd.read_csv(chart_file)
            chart_df['Date'] = pd.to_datetime(chart_df['Day of Date'], errors='coerce')
            chart_df = chart_df.dropna(subset=['Date'])
            # Convert unit names to match database output
            if 'adjusted_unit' in chart_df.columns:
                chart_df['Unit'] = chart_df['adjusted_unit'].replace({'Mcm': 'Billion Cubic Meter'})
                # Convert Mcm values to Bcm by dividing by 1000
                chart_df['Value'] = chart_df.apply(
                    lambda row: row['adjusted_unit_value'] / 1000.0 if row['adjusted_unit'] == 'Mcm' 
                    else row['adjusted_unit_value'], axis=1
                )
            else:
                chart_df['Unit'] = 'Billion Cubic Meter'
                chart_df['Value'] = chart_df.get('adjusted_unit_value', 0)
            
            # Load table data (monthly breakdown)
            table_df = pd.read_csv(table_file)
            table_df['Date'] = pd.to_datetime(table_df['Year of Date'].astype(str) + '-' + 
                                             table_df['Month of Date'].astype(str), 
                                             format='%Y-%B', errors='coerce')
            table_df = table_df.dropna(subset=['Date'])
            # Convert unit names to match database output
            if 'adjusted_unit' in table_df.columns:
                table_df['Unit'] = table_df['adjusted_unit'].replace({'Mcm': 'Billion Cubic Meter'})
                # Convert Mcm values to Bcm by dividing by 1000
                table_df['Value'] = table_df.apply(
                    lambda row: row['adjusted_unit_value'] / 1000.0 if row['adjusted_unit'] == 'Mcm' 
                    else row['adjusted_unit_value'], axis=1
                )
            else:
                table_df['Unit'] = 'Billion Cubic Meter'
                table_df['Value'] = table_df.get('adjusted_unit_value', 0)
            
            # Add sector information (assuming all data is total demand)
            for df in [map_df, chart_df, table_df]:
                if 'Sector' not in df.columns:
                    df['Sector'] = 'Total'
            
            # Cache the data
            _cached_data[cache_key] = (map_df, chart_df, table_df)
            _cache_timestamp[cache_key] = current_time
            print(f"Fallback CSV data loaded and cached. Map: {len(map_df)} rows, Chart: {len(chart_df)} rows, Table: {len(table_df)} rows")
            
            return _cached_data[cache_key]
            
        except Exception as csv_error:
            print(f"Error loading CSV fallback data: {csv_error}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def create_layout():
    """Create the Asian Monthly Demand by Country layout"""
    map_df, chart_df, table_df = load_data()
    
    if map_df.empty and chart_df.empty and table_df.empty:
        return html.Div([
            html.H1("Asian Gas Demand - Data Loading Issue", style={
                'color': '#fe5000', 'fontSize': '20px', 'fontWeight': 'bold',
                'fontFamily': 'Arial, sans-serif', 'margin': '25px 0 15px 40px'
            }),
            html.Div("Data could not be loaded from CSV files. Check file paths and data integrity.", 
                    style={'padding': '50px', 'color': 'red', 'fontSize': '16px'})
        ])

    # Get available options for filters
    all_countries = []
    for df in [map_df, chart_df, table_df]:
        if not df.empty and 'Country' in df.columns:
            all_countries.extend(df['Country'].unique())
    countries = sorted(list(set(all_countries)))
    
    # Get available sectors - add all required options
    sectors = ['All', 'Household', 'Industrial', 'Other', 'Power']
    
    # Get available units - add both options
    units = ['Billion Cubic Meter', 'Gigawatt-hour']
    
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
        
        # Set default range to 2019-2025 (7 years) - ensure we get the full range
        default_start_date = pd.Timestamp('2019-01-01')
        default_end_date = pd.Timestamp('2025-12-31')
        
        # Find indices for default range - be more flexible with date matching
        default_start_index = 0
        default_end_index = len(date_list) - 1
        
        # Find the closest date to 2019-01-01 or later
        for i, date in enumerate(date_list):
            if date.year >= 2019:
                default_start_index = i
                break
        
        # Find the closest date to 2025-12-31 or earlier
        for i in range(len(date_list) - 1, -1, -1):
            if date_list[i].year <= 2025:
                default_end_index = i
                break
                
        # If we couldn't find 2019-2025 range, use full range
        if default_start_index >= default_end_index:
            default_start_index = 0
            default_end_index = len(date_list) - 1
            
        print(f"Date range: {len(date_list)} dates from {min_date_val} to {max_date_val}")
        print(f"Default range: indices {default_start_index}-{default_end_index} ({date_list[default_start_index]} to {date_list[default_end_index]})")
    else:
        min_date_val = pd.Timestamp('2019-01-01')
        max_date_val = pd.Timestamp('2025-12-31')
        date_list = []
        default_start_index = 0
        default_end_index = 0

    return html.Div([
        # Store components for tracking filter states
        dcc.Store(id='country-filter-previous-asia-demand', data={'all_selected': True}),
        dcc.Store(id='selected-countries-store-asia-demand', data=countries),
        dcc.Store(id='asia-demand-date-list-store', data=[d.isoformat() for d in date_list] if date_list else []),
        
        # Download components
        dcc.Download(id="download-asia-demand-map-csv"),
        dcc.Download(id="download-asia-demand-chart-csv"),
        dcc.Download(id="download-asia-demand-table-csv"),
        
        # Clientside callback trigger for hover highlighting
        html.Div(id='gas-asia-demand-hover-trigger', style={'display': 'none'}),
        
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
                                id="asia-demand-date-range-start-label",
                                children='1/1/2019',  # Default start date
                                style={'display': 'inline-block', 'color': '#1b365d', 'fontSize': '11px', 'fontFamily': 'Arial', 'lineHeight': '12px', 'fontWeight': 'bold'}
                            ),
                            html.Label(
                                id="asia-demand-date-range-end-label",
                                children='12/31/2025',  # Default end date
                                style={'float': 'right', 'color': '#1b365d', 'fontSize': '11px', 'fontFamily': 'Arial', 'lineHeight': '28px', 'fontWeight': 'bold'}
                            ),
                        ], style={'width': '100%', 'marginBottom': '2px', 'position': 'relative'}),
                        html.Div([
                            dcc.RangeSlider(
                                id="asia-demand-date-range-slider",
                                min=0,
                                max=len(date_list) - 1 if date_list else 0,
                                step=1,
                                value=[default_start_index, default_end_index],  # Default to 2019-2025 range
                                marks=None,
                                allowCross=False,
                            ),
                        ], style={'width': '100%', 'margin': '0', 'padding': '0'}),
                    ], style={'width': '100%', 'position': 'relative', 'marginBottom': '10px'}),
                    
                    # Unit Filter
                    html.Label("Unit", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '13px', 'marginBottom': '10px'}),
                    dcc.RadioItems(
                        id='unit-radio-asia-demand',
                        options=[{'label': f' {unit}', 'value': unit} for unit in units],
                        value=units[0] if units else 'Billion Cubic Meter',
                        inputStyle={'marginRight': '8px'},
                        labelStyle={'display': 'block', 'marginBottom': '4px', 'fontSize': '12px', 'cursor': 'pointer'},
                        style={'marginBottom': '20px'}
                    ),
                    
                    # Sector Filter
                    html.Label("Sector", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '13px', 'marginBottom': '10px'}),
                    dcc.RadioItems(
                        id='sector-radio-asia-demand',
                        options=[{'label': f' {sector}', 'value': sector} for sector in sectors],
                        value='All',
                        inputStyle={'marginRight': '8px'},
                        labelStyle={'display': 'block', 'marginBottom': '4px', 'fontSize': '12px', 'cursor': 'pointer'},
                        style={'marginBottom': '20px'}
                    ),
                    
                    # Country Filter
                    html.Label("Country", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '13px', 'marginBottom': '10px'}),
                    dcc.Checklist(
                        id='country-checklist-asia-demand',
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
                        id='country-legend-container-asia-demand',
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
                        html.H1("Asian Gas Demand - Monthly Demand by Country", style={
                            'color': '#fe5000', 'fontSize': '20px', 'fontWeight': 'bold',
                            'fontFamily': 'Arial, sans-serif', 'margin': '25px 0 15px 0'
                        }),
                    ], style={'flex': '1'}),
                    html.Div([                        
                        
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'padding': '0 10px', 'marginBottom': '20px'}),
                
                # Map and Chart Side by Side Section
                html.Div([
                    # Left Side - Asia Map
                    html.Div([
                        html.Div([
                            html.H3("Asia Map – Demand by Year", style={
                                'color': '#1b365d', 'fontSize': '16px', 'fontWeight': 'bold',
                                'marginBottom': '15px', 'textAlign': 'center', 'flex': '1'
                            }),
                            html.Button(
                                "Export Map CSV",
                                id="export-asia-demand-map-btn",
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
                                },
                            )
                        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '5px'}),
                        dcc.Loading(
                            id="loading-map-asia-demand",
                            type="circle",
                            children=dcc.Graph(
                                id='asia-map-demand', 
                                config={
                                    'displayModeBar': False,
                                    'scrollZoom': True,
                                    'doubleClick': 'reset'
                                }
                            )
                        ),
                    ], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top', 'marginRight': '0%'}),
                    
                    # Right Side - Line Chart
                    html.Div([
                        html.Div([
                            html.H3("Asia Line Chart – Total Demand by Country", style={
                                'color': '#1b365d', 'fontSize': '16px', 'fontWeight': 'bold',
                                'marginBottom': '15px', 'textAlign': 'center', 'flex': '1'
                            }),
                            html.Button(
                                "Export Chart CSV",
                                id="export-asia-demand-chart-btn",
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
                                },
                            )
                        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '5px'}),
                        dcc.Loading(
                            id="loading-chart-asia-demand",
                            type="circle",
                            children=dcc.Graph(id='asia-chart-demand', config={'displayModeBar': False})
                        ),
                    ], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top', 'marginLeft': '0%'}),
                ], style={'marginBottom': '30px', 'width': '100%'}),
                
                # Table Section
                html.Div([
                    html.Div([
                        html.H3("Asia Table – Total Gas Demand by Country", style={
                            'color': '#1b365d', 'fontSize': '16px', 'fontWeight': 'bold',
                            'marginTop': '30px', 'marginBottom': '15px'
                        }),
                    ], style={'flex': '1'}),
                    html.Div([
                        html.Button(
                            "Export Table CSV",
                            id="export-asia-demand-table-btn",
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
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'padding': '0 10px', 'marginBottom': '15px'}),
                
                dcc.Loading(
                    id="loading-table-asia-demand",
                    type="circle",
                    children=html.Div(id='asia-table-demand')
                ),
                
            ], style={'marginRight': '150px', 'padding': '0 10px'})  # Increased margin and reduced padding
        ])
    ], className='tab-content', style={'backgroundColor': '#ffffff', 'minHeight': '100vh'})


def register_callbacks(dash_app, server):
    """Register all callbacks for the Asian Gas Demand dashboard"""
    
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
        Output('asia-map-demand', 'figure', allow_duplicate=True),
        [Input('asia-map-demand', 'hoverData')],
        [State('asia-map-demand', 'figure')],
        prevent_initial_call=True
    )
    
    # Update date labels based on range slider selection
    @dash_app.callback(
        [Output('asia-demand-date-range-start-label', 'children'),
         Output('asia-demand-date-range-end-label', 'children')],
        [Input('asia-demand-date-range-slider', 'value')],
        [State('asia-demand-date-list-store', 'data')]
    )
    def update_date_labels(slider_range, date_list_iso):
        """Update date labels based on range slider values."""
        if not date_list_iso or not slider_range or len(slider_range) != 2:
            return '1/1/2019', '12/31/2025'
        
        # Convert ISO strings back to datetime objects
        date_list = [pd.to_datetime(d) for d in date_list_iso]
        
        start_date = _index_to_date(slider_range[0], date_list)
        end_date = _index_to_date(slider_range[1], date_list)
        
        return _format_date_for_display(start_date), _format_date_for_display(end_date)
    
    # Callback to handle "All" checkbox logic for countries
    @dash_app.callback(
        [Output('country-checklist-asia-demand', 'value'),
         Output('country-filter-previous-asia-demand', 'data', allow_duplicate=True)],
        Input('country-checklist-asia-demand', 'value'),
        [State('country-filter-previous-asia-demand', 'data')],
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
        if all_selected and not has_all:
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
        [Output('country-legend-container-asia-demand', 'children'),
         Output('selected-countries-store-asia-demand', 'data')],
        [Input('country-checklist-asia-demand', 'value'),
         Input({'type': 'legend-item-asia-demand', 'index': ALL}, 'n_clicks')],
        [State('selected-countries-store-asia-demand', 'data')]
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
        if 'legend-item-asia-demand' not in trigger_id:
            if not selected_countries or (selected_countries and '(All)' not in selected_countries and len(selected_countries) == 0):
                current_selected = []  # Allow empty selection
            elif selected_countries and '(All)' not in selected_countries:
                current_selected = [c for c in selected_countries if c in available_countries]
            else:
                current_selected = available_countries.copy()
        else:
            # If triggered by legend, use the stored state as the baseline
            # Ensure current_selected is a list
            if current_selected is None:
                current_selected = available_countries.copy()
        
        # Handle legend item clicks
        if 'legend-item-asia-demand' in trigger_id:
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
                id={'type': 'legend-item-asia-demand', 'index': i},
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

    # Update Asia Map
    @dash_app.callback(
        Output('asia-map-demand', 'figure'),
        [Input('asia-demand-date-range-slider', 'value'),
         Input('unit-radio-asia-demand', 'value'),
         Input('sector-radio-asia-demand', 'value'),
         Input('selected-countries-store-asia-demand', 'data')],
        [State('asia-demand-date-list-store', 'data')]
    )
    def update_asia_map(slider_range, selected_unit, selected_sector, selected_countries, date_list_iso):
        """Update the Asia map visualization using shared map utilities"""
        map_df, chart_df, table_df = load_data(selected_sector)
        
        if map_df.empty:
            return create_empty_map("No map data available", height=700)
        
        # Filter data
        filtered_df = map_df.copy()
        
        # Apply date filter using range slider
        if slider_range and len(slider_range) == 2 and date_list_iso:
            date_list = [pd.to_datetime(d) for d in date_list_iso]
            start_date = _index_to_date(slider_range[0], date_list)
            end_date = _index_to_date(slider_range[1], date_list)
            filtered_df = filtered_df[(filtered_df['Date'] >= start_date) & (filtered_df['Date'] <= end_date)]
        
        # Apply unit filter
        if selected_unit and 'Unit' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Unit'] == selected_unit]
        
        # Note: Sector filtering is now handled at the database level in load_data()
        
        # Apply country filter - handle empty selection properly
        if selected_countries is not None:
            print(f"Map update - selected_countries: {selected_countries}")
            if len(selected_countries) == 0:
                # No countries selected - return empty map
                return create_empty_map("No countries selected", height=700)
            else:
                # Filter by selected countries
                print(f"Filtering map data by countries: {selected_countries}")
                print(f"Available countries in data: {filtered_df['Country'].unique().tolist()}")
                filtered_df = filtered_df[filtered_df['Country'].isin(selected_countries)]
                print(f"Filtered data shape: {filtered_df.shape}")
        
        if filtered_df.empty:
            return create_empty_map("No data available for selected filters", height=700)
        
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
        
        print(f"Map country names: {country_names}")
        print(f"Map locations (ISO): {locations}")
        
        # Create hover text with structured format matching the professional design
        hover_text = agg_df.apply(
            lambda row: (
                f"<span style='color: #666666; font-family: Arial, sans-serif;'>Country: </span>"
                f"<span style='color: #000000; font-weight: bold;'>{row['Country']}</span><br>"
                f"<span style='color: #666666; font-family: Arial, sans-serif;'>Year of Date: </span>"
                f"<span style='color: #000000; font-weight: bold;'>{int(row.get('Year of Date', 2025))}</span><br>"
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
        
        # Determine selection parameters
        selected_iso = None
        other_isos = None
        single_selected_country = None
        
        # Check if only one country is selected (not all countries)
        if selected_countries and len(selected_countries) == 1:
            single_selected_country = selected_countries[0]
            
            # Find the ISO code for the selected country
            if single_selected_country in agg_df['Country'].values:  # Use original Country column
                selected_iso = agg_df.loc[agg_df['Country'] == single_selected_country, 'ISO_Code'].iloc[0]
                other_isos = [iso for iso in locations if iso != selected_iso]
                print(f"Map selection: {single_selected_country} (ISO: {selected_iso}), dimming {len(other_isos)} other countries")
        
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
        
        # Add country hover layer for outline highlighting (similar to country profile)
        use_mapbox, _, mapbox_layout = get_mapbox_config()
        geojson = load_world_geojson()
        
        # Add country hover layer for better interaction (similar to country_profile.py)
        if use_mapbox and geojson and locations:
            # Get all unique countries for hover layer
            unique_countries = list(set(country_names))
            unique_isos = []
            valid_countries = []
            
            # Map country names to ISO codes for hover layer
            for country in unique_countries:
                iso = _iso_for_country(country)
                if iso:
                    unique_isos.append(iso)
                    valid_countries.append(country)
            
            if unique_isos:
                # Add country choropleth layer for hover interactions
                country_values = [1] * len(unique_isos)  # Uniform values for consistent hover
                
                # Create dynamic hover text with actual data for each country
                country_hover_text = []
                for country in valid_countries:
                    # Get actual data for this country from the aggregated data
                    country_data = agg_df[agg_df['Country'] == country]
                    if not country_data.empty:
                        value = country_data.iloc[0]['Value']
                        year = int(country_data.iloc[0]['Year of Date'])
                        
                        hover_text = (
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Country: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>{country}</span><br>"
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Year of Date: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>{year}</span><br>"
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Value: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>{value:,.1f}</span><br>"
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Unit: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>{selected_unit}</span>"
                        )
                    else:
                        # Fallback if no data found
                        year = 2025
                            
                        hover_text = (
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Country: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>{country}</span><br>"
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Year of Date: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>{year}</span><br>"
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Value: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>No data</span><br>"
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Unit: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>{selected_unit}</span>"
                        )
                    country_hover_text.append(hover_text)
                
                fig.add_trace(
                    go.Choroplethmapbox(
                        geojson=geojson,
                        locations=unique_isos,
                        z=country_values,
                        featureidkey="id",
                        colorscale=[[0, 'rgba(200, 230, 200, 0.6)'], [1, 'rgba(200, 230, 200, 0.6)']],
                        showscale=False,
                        hoverinfo="text",
                        hovertext=country_hover_text,
                        hoverlabel=dict(
                            bgcolor="white", 
                            font_size=13, 
                            font_color="#333", 
                            bordercolor="#ccc", 
                            font_family="Arial"
                        ),
                        customdata=valid_countries,
                        marker_line_color="white",
                        marker_line_width=1,
                        marker_opacity=0.6,
                        name="countries"  # Same name as main choropleth for consistent handling
                    )
                )
        elif not use_mapbox and locations:
            # Fallback geo hover layer
            unique_countries = list(set(country_names))
            unique_isos = []
            valid_countries = []
            
            for country in unique_countries:
                iso = _iso_for_country(country)
                if iso:
                    unique_isos.append(iso)
                    valid_countries.append(country)
            
            if unique_isos:
                country_values = [1] * len(unique_isos)
                
                # Create dynamic hover text with actual data for each country
                country_hover_text = []
                for country in valid_countries:
                    # Get actual data for this country from the aggregated data
                    country_data = agg_df[agg_df['Country'] == country]
                    if not country_data.empty:
                        value = country_data.iloc[0]['Value']
                        year = int(country_data.iloc[0]['Year of Date'])
                        
                        hover_text = (
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Country: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>{country}</span><br>"
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Year of Date: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>{year}</span><br>"
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Value: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>{value:,.1f}</span><br>"
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Unit: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>{selected_unit}</span>"
                        )
                    else:
                        # Fallback if no data found
                        year = 2025
                            
                        hover_text = (
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Country: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>{country}</span><br>"
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Year of Date: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>{year}</span><br>"
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Value: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>No data</span><br>"
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Unit: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>{selected_unit}</span>"
                        )
                    country_hover_text.append(hover_text)
                
                fig.add_trace(
                    go.Choropleth(
                        locations=unique_isos,
                        z=country_values,
                        locationmode='ISO-3',
                        colorscale=[[0, 'rgba(200, 230, 200, 0.6)'], [1, 'rgba(200, 230, 200, 0.6)']],
                        showscale=False,
                        hoverinfo="text",
                        hovertext=country_hover_text,
                        hoverlabel=dict(
                            bgcolor="white", 
                            font_size=13, 
                            font_color="#333", 
                            bordercolor="#ccc", 
                            font_family="Arial"
                        ),
                        customdata=valid_countries,
                        marker_line_width=1,
                        marker_line_color='white',
                        marker_opacity=0.6,
                        name="countries"
                    )
                )
        
        # Add custom margin and UI revision for gas demand
        fig.update_layout(
            margin=dict(l=20, r=20, t=20, b=80),
            uirevision='gas-asia-demand-map',
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
        
        # Focus on Asia region by adjusting the map center and zoom
        use_mapbox, _, mapbox_layout = get_mapbox_config()
        if use_mapbox:
            # Create a copy of mapbox_layout and override center and zoom for Asia focus
            asia_mapbox_layout = mapbox_layout.copy()
            asia_mapbox_layout.update({
                'center': dict(lat=25, lon=110),  # Center on Asia
                'zoom': 2.5  # Zoom level for Asia focus
            })
            fig.update_layout(mapbox=asia_mapbox_layout)
        else:
            # Geo fallback with Asia focus
            fig.update_layout(
                geo=dict(
                    scope='asia',
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
                    lonaxis_range=[60, 150],
                    lataxis_range=[-10, 55],
                    center=dict(lat=25, lon=110),
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
        Output('asia-chart-demand', 'figure'),
        [Input('asia-demand-date-range-slider', 'value'),
         Input('unit-radio-asia-demand', 'value'),
         Input('sector-radio-asia-demand', 'value'),
         Input('selected-countries-store-asia-demand', 'data')],
        [State('asia-demand-date-list-store', 'data')]
    )
    def update_asia_chart(slider_range, selected_unit, selected_sector, selected_countries, date_list_iso):
        """Update the Asia line chart visualization"""
        map_df, chart_df, table_df = load_data(selected_sector)
        
        if chart_df.empty:
            return go.Figure().add_annotation(text="No chart data available", 
                                            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Filter data
        filtered_df = chart_df.copy()
        
        # Apply date filter using range slider
        if slider_range and len(slider_range) == 2 and date_list_iso:
            date_list = [pd.to_datetime(d) for d in date_list_iso]
            start_date = _index_to_date(slider_range[0], date_list)
            end_date = _index_to_date(slider_range[1], date_list)
            filtered_df = filtered_df[(filtered_df['Date'] >= start_date) & (filtered_df['Date'] <= end_date)]
        
        # Apply unit filter
        if selected_unit and 'Unit' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Unit'] == selected_unit]
        
        # Note: Sector filtering is now handled at the database level in load_data()
        
        # Apply country filter - handle empty selection properly
        if selected_countries is not None:
            print(f"Chart update - selected_countries: {selected_countries}")
            if len(selected_countries) == 0:
                # No countries selected - return empty chart
                return go.Figure().add_annotation(text="No countries selected", 
                                                xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            else:
                # Filter by selected countries
                print(f"Filtering chart data by countries: {selected_countries}")
                print(f"Available countries in chart data: {filtered_df['Country'].unique().tolist()}")
                filtered_df = filtered_df[filtered_df['Country'].isin(selected_countries)]
                print(f"Filtered chart data shape: {filtered_df.shape}")
        
        if filtered_df.empty:
            return go.Figure().add_annotation(text="No data available for selected filters", 
                                            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Create line chart
        fig = px.line(
            filtered_df,
            x='Date',
            y='Value',
            color='Country',
            color_discrete_map=COUNTRY_COLORS,
            title='',
            hover_data={'Date': False, 'Value': False, 'Country': False}  # Hide default hover data
        )
        
        # Add custom hover template for professional formatting
        for trace in fig.data:
            trace.hovertemplate = (
                "<span style='color: #666666; font-family: Arial, sans-serif;'>Country: </span>"
                "<span style='color: #000000; font-weight: bold;'>%{fullData.name}</span><br>"
                "<span style='color: #666666; font-family: Arial, sans-serif;'>Month of Date: </span>"
                "<span style='color: #000000; font-weight: bold;'>%{x|%d %b %Y}</span><br>"
                "<span style='color: #666666; font-family: Arial, sans-serif;'>Value: </span>"
                "<span style='color: #000000; font-weight: bold;'>%{y:,.2f}</span><br>"
                "<span style='color: #666666; font-family: Arial, sans-serif;'>Unit: </span>"
                "<span style='color: #000000; font-weight: bold;'>" + selected_unit + "</span>"
                "<extra></extra>"  # Remove trace box
            )
        
        # Update layout
        fig.update_layout(
            height=700,  # Set minimum height to 700px
            margin=dict(l=20, r=20, t=20, b=40),
            paper_bgcolor='white',
            plot_bgcolor='white',
            xaxis_title="",  # Remove x-axis title
            yaxis_title="",  # Remove y-axis title
            showlegend=False,  # Remove legend from chart
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
        
        # Update line opacity based on selection
        for trace in fig.data:
            country = trace.name
            if country not in selected_countries:
                trace.opacity = 0.3
        
        return fig

    # Update Table
    @dash_app.callback(
        Output('asia-table-demand', 'children'),
        [Input('asia-demand-date-range-slider', 'value'),
         Input('unit-radio-asia-demand', 'value'),
         Input('sector-radio-asia-demand', 'value'),
         Input('selected-countries-store-asia-demand', 'data')],
        [State('asia-demand-date-list-store', 'data')]
    )
    def update_asia_table(slider_range, selected_unit, selected_sector, selected_countries, date_list_iso):
        """Update the Asia data table"""
        map_df, chart_df, table_df = load_data(selected_sector)
        
        if table_df.empty:
            return html.Div("No table data available", style={'padding': '20px', 'textAlign': 'center'})
        
        # Filter data
        filtered_df = table_df.copy()
        
        # Apply date filter using range slider
        if slider_range and len(slider_range) == 2 and date_list_iso:
            date_list = [pd.to_datetime(d) for d in date_list_iso]
            start_date = _index_to_date(slider_range[0], date_list)
            end_date = _index_to_date(slider_range[1], date_list)
            filtered_df = filtered_df[(filtered_df['Date'] >= start_date) & (filtered_df['Date'] <= end_date)]
        
        # Apply unit filter
        if selected_unit and 'Unit' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Unit'] == selected_unit]
        
        # Note: Sector filtering is now handled at the database level in load_data()
        
        # Apply country filter - handle empty selection properly
        if selected_countries is not None:
            if len(selected_countries) == 0:
                # No countries selected - return empty table
                return html.Div("No countries selected", style={'padding': '20px', 'textAlign': 'center'})
            else:
                # Filter by selected countries
                filtered_df = filtered_df[filtered_df['Country'].isin(selected_countries)]
        
        if filtered_df.empty:
            return html.Div("No data available for selected filters", style={'padding': '20px', 'textAlign': 'center'})
        
        # Create pivot table with Year-Month structure
        if 'Month of Date' in filtered_df.columns and 'Year of Date' in filtered_df.columns:
            # Create a proper date column for sorting
            filtered_df['YearMonth'] = filtered_df['Year of Date'].astype(str) + '-' + filtered_df['Month of Date'].astype(str)
            filtered_df['SortDate'] = pd.to_datetime(filtered_df['Year of Date'].astype(str) + '-' + filtered_df['Month of Date'].astype(str), format='%Y-%B', errors='coerce')
            
            # Sort by date descending (most recent first)
            filtered_df = filtered_df.sort_values('SortDate', ascending=False)
            
            # Create pivot table
            pivot_df = filtered_df.pivot_table(
                index='Country',
                columns=['Year of Date', 'Month of Date'],
                values='Value',
                aggfunc='sum',
                fill_value=0
            ).reset_index()
            
            # Create hierarchical columns for DataTable
            columns = [{"name": ["", "Country"], "id": "Country", "type": "text"}]
            
            # Get unique years and months in sorted order
            year_month_pairs = []
            if not filtered_df.empty:
                temp_df = filtered_df[['Year of Date', 'Month of Date', 'SortDate']].drop_duplicates()
                temp_df = temp_df.sort_values('SortDate', ascending=False)
                year_month_pairs = [(row['Year of Date'], row['Month of Date']) for _, row in temp_df.iterrows()]
            
            # Group by year for header structure
            year_groups = {}
            for year, month in year_month_pairs:
                if year not in year_groups:
                    year_groups[year] = []
                year_groups[year].append(month)
            
            # Prepare data for the table
            data = []
            for _, row in pivot_df.iterrows():
                record = {"Country": row["Country"]}
                country_grand_total = 0
                
                # Add columns for each year with months and year total
                for year in sorted(year_groups.keys(), reverse=True):  # Most recent year first
                    year_total = 0
                    
                    # Add month columns for this year
                    for month in year_groups[year]:
                        col_id = f"{year}_{month}".replace(' ', '_')
                        try:
                            # Access the multi-level column
                            value = row[(year, month)] if (year, month) in row.index else 0
                            value = value if pd.notna(value) and value != 0 else 0
                            record[col_id] = value if value != 0 else None
                            year_total += value
                        except (KeyError, IndexError):
                            record[col_id] = None
                    
                    # Add year total column
                    year_total_col_id = f"{year}_Total"
                    record[year_total_col_id] = year_total if year_total != 0 else None
                    country_grand_total += year_total
                
                # Add grand total column
                record["Grand_Total"] = country_grand_total if country_grand_total != 0 else None
                data.append(record)
            
            # Create columns with hierarchical headers
            for year in sorted(year_groups.keys(), reverse=True):  # Most recent year first
                # Add month columns
                for month in year_groups[year]:
                    col_id = f"{year}_{month}".replace(' ', '_')
                    columns.append({
                        "name": [str(year), month],
                        "id": col_id,
                        "type": "numeric",
                        "format": {"specifier": ",.0f"}
                    })
                
                # Add year total column
                year_total_col_id = f"{year}_Total"
                columns.append({
                    "name": [str(year), "Total"],
                    "id": year_total_col_id,
                    "type": "numeric",
                    "format": {"specifier": ",.0f"}
                })
            
            # Add grand total column
            columns.append({
                "name": ["", "Grand Total"],
                "id": "Grand_Total",
                "type": "numeric",
                "format": {"specifier": ",.0f"}
            })
            
            # Calculate Grand Total row (sum of each column)
            grand_total_row = {"Country": "Grand Total"}
            
            # Calculate totals for month columns
            for year in sorted(year_groups.keys(), reverse=True):
                # Calculate totals for each month in this year
                for month in year_groups[year]:
                    col_id = f"{year}_{month}".replace(' ', '_')
                    total = sum([record.get(col_id, 0) or 0 for record in data])
                    grand_total_row[col_id] = total if total != 0 else None
                
                # Calculate total for year total column
                year_total_col_id = f"{year}_Total"
                total = sum([record.get(year_total_col_id, 0) or 0 for record in data])
                grand_total_row[year_total_col_id] = total if total != 0 else None
            
            # Calculate grand total column
            total = sum([record.get("Grand_Total", 0) or 0 for record in data])
            grand_total_row["Grand_Total"] = total if total != 0 else None
            
            # Add Grand Total row to data
            data.append(grand_total_row)
            
        else:
            # Fallback to simple aggregation
            pivot_df = filtered_df.groupby('Country').agg({'Value': 'sum'}).reset_index()
            columns = [
                {"name": ["", "Country"], "id": "Country", "type": "text"},
                {"name": ["", "Total"], "id": "Value", "type": "numeric", "format": {"specifier": ",.0f"}}
            ]
            data = pivot_df.to_dict('records')
        
        return dash_table.DataTable(
            data=data,
            columns=columns,
            style_cell={
                'textAlign': 'left',
                'fontSize': '12px',
                'fontFamily': 'Arial, sans-serif',
                'padding': '8px',
                'border': '1px solid #e0e0e0',
                'maxWidth': '120px',
                'overflow': 'hidden',
                'textOverflow': 'ellipsis',
            },
            style_header={
                'backgroundColor': '#f8f9fa',
                'fontWeight': 'bold',
                'color': '#1b365d',
                'border': '1px solid #dee2e6',
                'textAlign': 'center'
            },
            style_data={
                'backgroundColor': 'white',
                'color': '#333',
                'textAlign': 'right'
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#f8f9fa'
                },
                {
                    'if': {'column_id': 'Country'},
                    'textAlign': 'left',
                    'fontWeight': 'bold'
                },
                # Style Total columns
                {
                    'if': {'column_id': {'regex': r'.*_Total'}},
                    'backgroundColor': '#e8f4f8',
                    'fontWeight': 'bold'
                },
                # Style Grand Total column
                {
                    'if': {'column_id': 'Grand_Total'},
                    'backgroundColor': '#d4edda',
                    'fontWeight': 'bold'
                },
                # Style Grand Total row
                {
                    'if': {'filter_query': '{Country} = "Grand Total"'},
                    'backgroundColor': '#d4edda',
                    'fontWeight': 'bold'
                }
            ],
            merge_duplicate_headers=True,
            sort_action="native",
            page_size=20,
            style_table={'overflowX': 'auto'}
        )

    # Export Map CSV
    @dash_app.callback(
        Output("download-asia-demand-map-csv", "data"),
        Input("export-asia-demand-map-btn", "n_clicks"),
        [State('asia-demand-date-range-slider', 'value'),
         State('unit-radio-asia-demand', 'value'),
         State('sector-radio-asia-demand', 'value'),
         State('selected-countries-store-asia-demand', 'data'),
         State('asia-demand-date-list-store', 'data')],
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
        filename = f"asia_gas_demand_map_{timestamp}.csv"
        
        return dcc.send_data_frame(filtered_df.to_csv, filename, index=False)

    # Export Chart CSV
    @dash_app.callback(
        Output("download-asia-demand-chart-csv", "data"),
        Input("export-asia-demand-chart-btn", "n_clicks"),
        [State('asia-demand-date-range-slider', 'value'),
         State('unit-radio-asia-demand', 'value'),
         State('sector-radio-asia-demand', 'value'),
         State('selected-countries-store-asia-demand', 'data'),
         State('asia-demand-date-list-store', 'data')],
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
        filename = f"asia_gas_demand_chart_{timestamp}.csv"
        
        return dcc.send_data_frame(filtered_df.to_csv, filename, index=False)

    # Export Table CSV
    @dash_app.callback(
        Output("download-asia-demand-table-csv", "data"),
        Input("export-asia-demand-table-btn", "n_clicks"),
        [State('asia-demand-date-range-slider', 'value'),
         State('unit-radio-asia-demand', 'value'),
         State('sector-radio-asia-demand', 'value'),
         State('selected-countries-store-asia-demand', 'data'),
         State('asia-demand-date-list-store', 'data')],
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
        filename = f"asia_gas_demand_table_{timestamp}.csv"
        
        return dcc.send_data_frame(filtered_df.to_csv, filename, index=False)

    # Map click interaction to update country selection
    @dash_app.callback(
        Output('country-checklist-asia-demand', 'value', allow_duplicate=True),
        Output('country-filter-previous-asia-demand', 'data', allow_duplicate=True),
        Input('asia-map-demand', 'clickData'),
        State('country-checklist-asia-demand', 'value'),
        State('country-checklist-asia-demand', 'options'),
        prevent_initial_call=True
    )
    def handle_map_click(clickData, current_selection, options):
        """Handle map clicks to update country selection using shared utility"""
        if not clickData:
            return no_update, no_update
            
        try:
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
            
            # Use shared helper to determine new selection
            new_selection = handle_map_click_reset(
                clickData, 
                current_selection, 
                all_countries,
                all_value='(All)'
            )
            
            # Determine new state to prevent conflict with checklist callback
            # If (All) is in selection, we are in all_selected mode
            is_all_selected = '(All)' in new_selection
            new_state = {'all_selected': is_all_selected}
            
            return new_selection, new_state
            
        except Exception as e:
            print(f"Map click error: {e}")
            return no_update, no_update