"""
Asian Gas Demand - Monthly Demand by Sector
Recreated Tableau dashboard for Asian gas demand by sector and country.
Strict separation of CSV usage (Removed) -> Now Database Driven.
"""
import pandas as pd
import numpy as np
from dash import dcc, html, dash_table, Input, Output, State, no_update
from dash import callback_context as ctx
import plotly.graph_objects as go
import os
import re
from datetime import datetime
from sqlalchemy import text
from core.data_helpers import get_db_engine

# --- Configuration ---
COLORS = {
    'Industrial': '#B7D28B', # Light Green
    'Power': '#CC5521',      # Orange
    'Household': '#006FAD',  # Blue
    'Other': '#1D8F91'       # Teal
}

# Stack Order: Bottom -> Top
SECTOR_ORDER = ['Industrial', 'Power', 'Household', 'Other']

# --- Database Queries ---

QUERY_COUNTRIES = """
SELECT DISTINCT
    tr.country
FROM glng_gas_demand tr
LEFT JOIN dim_country dc
    ON tr.country_id = dc.dim_country_id
WHERE LOWER(dc.region) IN ('asia', 'oceania')
  AND tr.country IS NOT NULL
  AND TRIM(tr.country) <> ''
ORDER BY tr.country;
"""

QUERY_SECTORS = """
SELECT DISTINCT
    tr.sector
FROM glng_gas_demand tr
LEFT JOIN dim_country dc
    ON tr.country_id = dc.dim_country_id
WHERE LOWER(dc.region) IN ('asia', 'oceania')
  AND tr.sector IS NOT NULL
  AND TRIM(tr.sector) <> ''
ORDER BY tr.sector;
"""

# Base Chart Query (User Provided)
QUERY_CHART_BASE = """
SELECT
    TO_CHAR(DATE_TRUNC('month', gd.date), 'FMMonth YYYY') AS "Month of Date",
    gd.sector AS "Sector",
    CASE
        WHEN gd.unit = 'Mcm' THEN 'Billion Cubic Meter'
        WHEN gd.unit = 'GWh' THEN 'Gigawatt-hour'
    END AS "Unit",
    ROUND(
        SUM(
            CASE
                WHEN gd.unit = 'Mcm' THEN gd.value / 1000.0
                WHEN gd.unit = 'GWh' THEN gd.value
            END
        ),
        9
    ) AS "Value"
FROM glng_gas_demand gd
LEFT JOIN dim_country dc
    ON gd.country_id = dc.dim_country_id
WHERE LOWER(dc.region) IN ('asia', 'oceania')
  AND gd.unit IN ('Mcm', 'GWh')
  AND gd.to_be_deleted = false
  AND gd.date >= DATE '2019-01-01'
  AND gd.date <= CURRENT_DATE
  {country_filter}
GROUP BY
    DATE_TRUNC('month', gd.date),
    gd.sector,
    gd.unit
ORDER BY
    DATE_TRUNC('month', gd.date),
    gd.sector,
    "Unit";
"""

# Base Table Query (User Provided)
QUERY_TABLE_BASE = """
SELECT
    TO_CHAR(DATE_TRUNC('month', gd.date), 'FMMonth YYYY') AS "Month of Date",
    gd.sector AS "Sector",
    gd.country AS "Country",
    CASE
        WHEN gd.unit = 'Mcm' THEN 'Billion Cubic Meter'
        WHEN gd.unit = 'GWh' THEN 'Gigawatt-hour'
    END AS "Unit",
    ROUND(
        SUM(
            CASE
                WHEN gd.unit = 'Mcm' THEN gd.value / 1000.0
                WHEN gd.unit = 'GWh' THEN gd.value
            END
        ),
        9
    ) AS "Value"
FROM glng_gas_demand gd
LEFT JOIN dim_country dc
    ON gd.country_id = dc.dim_country_id
WHERE LOWER(dc.region) IN ('asia', 'oceania')
  AND gd.unit IN ('Mcm', 'GWh')
  AND gd.to_be_deleted = false
  AND gd.date >= DATE '2019-01-01'
  AND gd.date <= CURRENT_DATE
  {country_filter}
GROUP BY
    DATE_TRUNC('month', gd.date),
    gd.sector,
    gd.unit,
    gd.country
ORDER BY
    DATE_TRUNC('month', gd.date),
    gd.sector,
    "Unit";
"""


# Helper functions for date slider
def _format_date_for_display(date):
    """Format date as 'YYYY-MM-DD' (e.g., '2019-01-01')"""
    if pd.isna(date) or date is None:
        return ""
    if isinstance(date, str):
        date = pd.to_datetime(date, errors='coerce')
    if pd.isna(date):
        return ""
    return date.strftime('%Y-%m-%d')

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

# --- Data Loading ---

def get_db_options():
    """Fetch dropdown options from DB."""
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            countries = pd.read_sql(text(QUERY_COUNTRIES), conn)['country'].tolist()
            sectors = pd.read_sql(text(QUERY_SECTORS), conn)['sector'].tolist()
        return sorted(countries), sorted(sectors)
    except Exception as e:
        print(f"Error fetching DB options: {e}")
        return [], []

def aggregate_chart_data_by_time_level(df, time_level):
    """Aggregate chart data based on time hierarchy level."""
    if df.empty:
        return df
    
    df = df.copy()
    
    if time_level == 'YEARLY':
        df['Time_Group'] = df['Date_Obj'].dt.year.astype(str)
        df['Time_Label'] = df['Date_Obj'].dt.year.astype(str)
    elif time_level == 'QUARTERLY':
        df['Time_Group'] = df['Date_Obj'].dt.to_period('Q').astype(str)
        df['Time_Label'] = df['Date_Obj'].dt.to_period('Q').astype(str)
    elif time_level == 'DAILY':
        df['Time_Group'] = df['Date_Obj'].dt.strftime('%B %Y')
        df['Time_Label'] = df['Date_Obj'].dt.strftime('%B 1, %Y')
    else:  # MONTHLY (default)
        df['Time_Group'] = df['Date_Obj'].dt.strftime('%B %Y')
        df['Time_Label'] = df['Date_Obj'].dt.strftime('%B %Y')
    
    # Aggregate by time group and sector
    aggregated = df.groupby(['Time_Group', 'Time_Label', 'Sector', 'Unit'])['Value'].sum().reset_index()
    
    # Add back Date_Obj for sorting
    if time_level == 'YEARLY':
        aggregated['Date_Obj'] = pd.to_datetime(aggregated['Time_Group'] + '-01-01')
    elif time_level == 'QUARTERLY':
        aggregated['Date_Obj'] = aggregated['Time_Group'].apply(lambda x: pd.Period(x).start_time)
    else:  # MONTHLY or DAILY
        aggregated['Date_Obj'] = pd.to_datetime(aggregated['Time_Group'], format='%B %Y')
    
    return aggregated

def aggregate_table_data_by_time_level(df, time_level):
    """Aggregate table data based on time hierarchy level."""
    if df.empty:
        return df
    
    df = df.copy()
    
    if time_level == 'YEARLY':
        # Group by year only
        df['Time_Group'] = df['Date_Obj'].dt.year
        df['Time_Period'] = df['Date_Obj'].dt.year.astype(str)
    elif time_level == 'QUARTERLY':
        # Group by year and quarter
        df['Time_Group'] = df['Date_Obj'].dt.to_period('Q')
        df['Time_Period'] = df['Date_Obj'].dt.to_period('Q').astype(str)
        df['Year'] = df['Date_Obj'].dt.year
        df['Quarter'] = 'Q' + df['Date_Obj'].dt.quarter.astype(str)
    elif time_level == 'DAILY':
        # Group by year, month, and day
        df['Time_Group'] = df['Date_Obj'].dt.date
        df['Time_Period'] = df['Date_Obj'].dt.strftime('%Y-%m-%d')
        df['Year'] = df['Date_Obj'].dt.year
        df['Month'] = df['Date_Obj'].dt.strftime('%B')
        df['Day'] = df['Date_Obj'].dt.day
    else:  # MONTHLY (default)
        # Keep existing monthly structure
        return df
    
    # Aggregate the data
    group_cols = ['Country', 'Sector', 'Unit', 'Time_Group', 'Time_Period']
    if time_level == 'QUARTERLY':
        group_cols.extend(['Year', 'Quarter'])
    elif time_level == 'DAILY':
        group_cols.extend(['Year', 'Month', 'Day'])
    
    aggregated = df.groupby(group_cols)['adjusted_unit_value'].sum().reset_index()
    
    return aggregated

def load_chart_data(country_filter=None):
    """
    Load data for the CHART using SQL.
    Applies Country filter in SQL if specified.
    """
    try:
        engine = get_db_engine()
        
        sql = QUERY_CHART_BASE
        params = {}
        
        # Inject Country Filter
        if country_filter and country_filter != '(All)':
            sql = sql.replace("{country_filter}", "AND gd.country = :selected_country")
            params['selected_country'] = country_filter
        else:
            sql = sql.replace("{country_filter}", "")
            
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params)
        
        if df.empty:
            return pd.DataFrame()

        # Post-process for consistency
        # Parse 'Month of Date' column (FMMonth YYYY) -> Date_Obj
        df['Date_Obj'] = pd.to_datetime(df['Month of Date'], format='%B %Y')
        df['Year'] = df['Date_Obj'].dt.year
        df['Month'] = df['Date_Obj'].dt.strftime('%B')
        
        return df
    except Exception as e:
        print(f"Error loading chart data: {e}")
        return pd.DataFrame()

def load_table_data(country_filter=None):
    """
    Load data for the TABLE using SQL.
    Applies Country filter in SQL if specified.
    """
    try:
        engine = get_db_engine()
        
        sql = QUERY_TABLE_BASE
        params = {}
        
        # Inject Country Filter
        if country_filter and country_filter != '(All)':
            sql = sql.replace("{country_filter}", "AND gd.country = :selected_country")
            params['selected_country'] = country_filter
        else:
            # Remove the specific country filter line if present in template or placeholder
            sql = sql.replace("{country_filter}", "")
            
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params)
            
        if df.empty:
            return pd.DataFrame()
            
        # Post-process
        # Split Month of Date (January 2022) into Month Name and Year for table pivoting
        df['Date_Obj'] = pd.to_datetime(df['Month of Date'], format='%B %Y')
        df['Year of Date'] = df['Date_Obj'].dt.year
        df['Month of Date'] = df['Date_Obj'].dt.strftime('%B') # Just month name for existing Logic
        
        # Rename 'Value' to 'adjusted_unit_value' if that's what build_table expects
        df.rename(columns={'Value': 'adjusted_unit_value'}, inplace=True)
        
        return df
    except Exception as e:
        print(f"Error loading table data: {e}")
        return pd.DataFrame()


# --- UI Components ---

def create_layout():
    # Load initial data options
    all_countries, all_sectors = get_db_options()
    all_sectors = ['(All)'] + all_sectors
    all_countries = sorted(all_countries)
    
    # Load initial Chart data (All countries) to setup Date slider
    df_chart = load_chart_data(country_filter='(All)')
    
    unique_dates = []
    if not df_chart.empty:
        unique_dates = sorted(df_chart['Date_Obj'].unique())
        
    if unique_dates:
        min_date_val = unique_dates[0]
        max_date_val = unique_dates[-1]
        date_list = unique_dates
        
        # Default range: Most recent 8 years
        default_end_date = max_date_val
        default_start_date = max_date_val - pd.DateOffset(years=8)
        if default_start_date < min_date_val:
            default_start_date = min_date_val
            
        # Find indices
        default_start_index = _date_to_index(default_start_date, date_list)
        default_end_index = _date_to_index(default_end_date, date_list)
        
        # Strings for display
        min_date_str = _format_date_for_display(min_date_val)
        max_date_str = _format_date_for_display(max_date_val)
        default_start_date_str = _format_date_for_display(default_start_date)
        default_end_date_str = _format_date_for_display(default_end_date)
        
        date_list_store = [d.isoformat() for d in date_list]
    else:
        # Fallback
        date_list = []
        date_list_store = []
        min_date_str = '2019-01-01'
        max_date_str = '2025-12-31'
        default_start_date_str = '2019-01-01'
        default_end_date_str = '2025-12-31'
        default_start_index = 0
        default_end_index = 0

    return html.Div([
        # Store for dates
        dcc.Store(id='asia-sector-date-list-store', data=date_list_store),
        dcc.Store(id='min-date', data=min_date_str),
        dcc.Store(id='max-date', data=max_date_str),
        
        dcc.Download(id="download-asia-chart-csv"),
        dcc.Download(id="download-asia-table-csv"),
        
        # Anchor for clientside callback
        html.Div(id='asia-sector-date-picker-enhancer-anchor', style={'display': 'none'}),
        # Header Row
        html.Div([
            html.H1("All Gas Demand", style={
                'color': '#FF6B00', 
                'fontSize': '24px', 
                'margin': '0', 
                'padding': '15px 25px',
                'fontWeight': 'bold',
                'fontFamily': 'Arial, sans-serif'
            }),
        ], style={'backgroundColor': '#ffffff', 'borderBottom': '1px solid #ddd'}),

        # Main Content Row
        html.Div([
            # Left Column: Charts and Tables
            html.Div([
                # Chart Container with Hierarchy Icons
                html.Div([
                    # Chart Export Button
                    html.Div(dcc.Loading(
                        html.Button("Export to CSV", id="export-asia-chart-btn", n_clicks=0, style={
                            "backgroundColor": "white",
                            "color": "#2c3e50",
                            "border": "1px solid #dee2e6",
                            "padding": "6px 12px",
                            "borderRadius": "4px",
                            "cursor": "pointer",
                            "fontSize": "12px",
                            "fontWeight": "normal",
                        })
                    ), style={'position': 'absolute', 'top': '15px', 'right': '20px', 'zIndex': '10'}),

                    # Chart Hierarchy Controls
                    html.Div([
                        html.Div([
                            html.Span("Year of Date", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('+', id='asia-chart-toggle-year-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Quarter of Date", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('+', id='asia-chart-toggle-quarter-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Month of Date", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('-', id='asia-chart-toggle-month-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#add8e6', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Day of Year", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('+', id='asia-chart-toggle-day-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center'})
                    ], style={
                        'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#f8f9fa', 
                        'padding': '5px 10px', 'borderRadius': '4px', 'marginBottom': '10px',
                        'position': 'absolute', 'top': '15px', 'left': '60px', 'zIndex': '10'
                    }),

                    dcc.Loading(
                        [
                            html.Div(id='loading-trigger-chart', style={'display': 'none'}),
                            dcc.Graph(id='asia-gas-monthly-chart', config={'displayModeBar': False})
                        ],
                        id="loading-asia-chart",
                        type="circle"
                    )
                ], style={'backgroundColor': '#fff', 'padding': '10px', 'position': 'relative'}),

                # Table Container with Hierarchy Icons
                html.Div([
                    # Table Hierarchy Controls
                    html.Div([
                        html.Div([
                            html.Span("Year of Date", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('+', id='asia-table-toggle-year-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Quarter of Date", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('+', id='asia-table-toggle-quarter-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Month of Date", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('-', id='asia-table-toggle-month-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#add8e6', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Day of Year", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('+', id='asia-table-toggle-day-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center'})
                    # Removed extra closing bracket here
                    ,
                    
                    # Table Export Button
                    html.Div(dcc.Loading(
                        html.Button("Export to CSV", id="export-asia-table-btn", n_clicks=0, style={
                            "backgroundColor": "white",
                            "color": "#2c3e50",
                            "border": "1px solid #dee2e6",
                            "padding": "6px 12px",
                            "borderRadius": "4px",
                            "cursor": "pointer",
                            "fontSize": "12px",
                            "fontWeight": "normal",
                        })
                    ), style={'marginLeft': 'auto'}) # Push to right
                    ], style={
                        'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#f8f9fa', 
                        'padding': '5px 10px', 'borderRadius': '4px', 'marginBottom': '10px'
                    }),

                    dcc.Loading(
                        [
                            html.Div(id='loading-trigger-table', style={'display': 'none'}),
                            html.Div(id='asia-gas-monthly-table-container')
                        ],
                        id="loading-asia-table",
                        type="circle"
                    )
                ], style={'marginTop': '20px', 'backgroundColor': '#fff', 'padding': '10px'}),
                
                # Footer
                html.Div([
                    html.Span("Source: Energy Intelligence.", style={
                        'fontSize': '10px',
                        'color': '#666',
                        'fontStyle': 'italic'
                    })
                ], style={
                    'backgroundColor': '#fff',
                    'padding': '10px 20px',
                    'marginTop': '3px'
                }),

                
                # Stores for State
                dcc.Store(id='asia-table-highlight-state'), # From Clientside
                dcc.Store(id='chart-highlight-state', data=None), # Server side Highlight State
                dcc.Store(id='chart-time-level', data='MONTHLY'), # Chart hierarchy state
                dcc.Store(id='table-time-level', data='MONTHLY'), # Table hierarchy state - changed to MONTHLY
                dcc.Store(id='store-asia-chart-data'), # Cache
                dcc.Store(id='store-asia-table-data'), # Cache
                
                # Hidden Trigger for X-Axis Click
                dcc.Input(id='axis-click-trigger', type='text', style={'display': 'none'}),
                
                html.Div(id='asia-table-dummy-output', style={'display': 'none'}),
                html.Div(id='axis-listener-output', style={'display': 'none'}) # Dedicated output
                
            ], style={'flex': '1', 'padding': '20px', 'overflowX': 'hidden', 'backgroundColor': '#fff'}),

            # Right Column: Filters Panel
            html.Div([
                html.Div([
                    # Date Range Filter
                    html.Div([
                        html.Label("Date", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '12px', 'marginBottom': '8px', 'display': 'block'}),
                        
                        # Date Inputs
                        html.Div([
                            dcc.Input(
                                id='asia-sector-start-date',
                                type='date',
                                value=default_start_date_str,
                                min=min_date_str,
                                max=max_date_str,
                                placeholder='YYYY-MM-DD',
                                style={
                                    'width': '65px',
                                    'height': '28px',
                                    'fontSize': '11px',
                                    'fontFamily': 'Arial, sans-serif',
                                    'border': '1px solid #ccc',
                                    'padding': '0 2px',
                                    'color': '#333',
                                    'cursor': 'pointer'
                                }
                            ),
                            dcc.Input(
                                id='asia-sector-end-date',
                                type='date',
                                value=default_end_date_str,
                                min=min_date_str,
                                max=max_date_str,
                                placeholder='YYYY-MM-DD',
                                style={
                                    'width': '65px',
                                    'height': '28px',
                                    'fontSize': '11px',
                                    'fontFamily': 'Arial, sans-serif',
                                    'border': '1px solid #ccc',
                                    'padding': '0 2px',
                                    'color': '#333',
                                    'cursor': 'pointer'
                                }
                            ),
                        ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '10px', 'alignItems': 'center'}),

                        # Relative Container for Slider
                        html.Div([
                            dcc.RangeSlider(
                                id='asia-date-slider',
                                min=0,
                                max=len(date_list) - 1 if date_list else 0,
                                value=[default_start_index, default_end_index],
                                step=1,
                                marks=None,
                                allowCross=False,
                                className='custom-range-slider'
                            ),
                        ], style={'position': 'relative', 'padding': '0', 'marginTop': '0px'}) 
                        
                    ], style={'marginBottom': '20px', 'borderBottom': '1px solid #eee', 'paddingBottom': '20px'}),
                    


                    # Unit Filter
                    html.Div([
                        html.Label("Unit", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '12px', 'marginBottom': '8px', 'display': 'block'}),
                        dcc.RadioItems(
                            id='asia-unit-filter',
                            options=[
                                {'label': 'Billion Cubic Meter', 'value': 'Billion Cubic Meter'},
                                {'label': 'Gigawatt-hour', 'value': 'Gigawatt-hour'}
                            ],
                            value='Billion Cubic Meter',
                            labelStyle={'display': 'block', 'marginBottom': '4px', 'fontSize': '12px', 'color': '#333'}
                        )
                    ], style={'marginBottom': '20px', 'borderBottom': '1px solid #eee', 'paddingBottom': '10px'}),

                    # Sector Filter (Radio)
                    html.Div([
                        html.Label("Sector", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '12px', 'marginBottom': '8px', 'display': 'block'}),
                        dcc.RadioItems(
                            id='asia-sector-filter',
                            options=[{'label': s, 'value': s} for s in all_sectors],
                            value='(All)',
                            labelStyle={'display': 'block', 'marginBottom': '4px', 'fontSize': '12px', 'color': '#333'}
                        )
                    ], style={'marginBottom': '20px', 'borderBottom': '1px solid #eee', 'paddingBottom': '10px'}),

                    # Country Filter
                    html.Div([
                        html.Label("Country", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '12px', 'marginBottom': '8px', 'display': 'block'}),
                        dcc.RadioItems(
                            id='asia-country-filter',
                            options=[{'label': '(All)', 'value': '(All)'}] + [{'label': c, 'value': c} for c in all_countries],
                            value='(All)',
                            labelStyle={'display': 'block', 'marginBottom': '3px', 'fontSize': '12px', 'color': '#333'}
                        )
                    ], style={'marginBottom': '30px'}),

                    # Sector Legend
                    html.Div([
                        html.Label("Sector", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '12px', 'marginBottom': '10px', 'display': 'block'}),
                        html.Div([
                            html.Div([
                                html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': COLORS[s], 'marginRight': '8px', 'display': 'inline-block'}),
                                html.Span(s, style={'fontSize': '12px', 'color': '#555'})
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px'})
                            for s in reversed(SECTOR_ORDER)
                        ])
                    ], style={'borderTop': '2px solid #eee', 'paddingTop': '15px'})

                ], style={
                    'backgroundColor': '#ffffff',
                    'padding': '15px',
                    'fontSize': '14px'
                })
            ], style={'width': '220px', 'backgroundColor': '#fff', 'borderLeft': '1px solid #ddd', 'minHeight': '100vh'})
        ], style={'display': 'flex', 'minHeight': 'calc(100vh - 55px)'}),
        
        # Clientside helper to format tooltip
    ], id='gas-asia-monthly-container', style={'backgroundColor': '#ffffff', 'fontFamily': 'Arial, sans-serif'})


def build_chart(df, sector_filter, unit, time_level='MONTHLY', highlight_state=None):
    # Aggregate data based on time level
    df_agg = aggregate_chart_data_by_time_level(df, time_level)
    
    # Sort by Date
    df_agg = df_agg.sort_values('Date_Obj')
    
    unique_dates = df_agg['Date_Obj'].unique()
    # Use Time_Label for X axis ticks
    x_axis_labels = df_agg['Time_Label'].unique().tolist()
    
    # Generate tick text with conditional formatting
    tick_texts = []
    for i, d in enumerate(unique_dates):
        d_str = df_agg[df_agg['Date_Obj'] == d]['Time_Label'].iloc[0]
        is_selected = False
        if highlight_state and highlight_state.get('date') == d_str:
            is_selected = True
        
        if is_selected:
            # Highlight style matching Image 1 (Blue background)
            tick_texts.append(f"<span style='font-weight:bold; color:#000000; background-color:#cfe8ef;'>{d_str}</span>")
        else:
            tick_texts.append(d_str)

    fig = go.Figure()
    
    # Determine format
    val_fmt = ",.1f" if unit == 'Billion Cubic Meter' else ",.0f"
    
    # Stacked Bar Chart
    sectors_to_plot = SECTOR_ORDER if sector_filter == '(All)' else [sector_filter]
    
    for sector in sectors_to_plot:
        # Filter for sector
        sdf = df_agg[df_agg['Sector'] == sector]
        
        # Group by Date
        sdf_grouped = sdf.groupby('Date_Obj')['Value'].sum()
        
        y_vals = []
        opacities = []
        line_widths = []
        line_colors = []
        
        for d in unique_dates:
            val = sdf_grouped.get(d, 0)
            y_vals.append(val)
            
            # Highlight Logic
            date_str = df_agg[df_agg['Date_Obj'] == d]['Time_Label'].iloc[0] if len(df_agg[df_agg['Date_Obj'] == d]) > 0 else ""
            if date_str:
                date_str = str(date_str).replace('\xa0', ' ').strip()
            
            op = 1.0 # Default full opacity
            lw = 0
            lc = 'rgba(0,0,0,0)' # Transparent
            
            if highlight_state:
                op = 0.3 # Default dim if highlighting active
                
                h_date = str(highlight_state.get('date')).replace('\xa0', ' ').strip() if highlight_state.get('date') else ""
                h_sector = str(highlight_state.get('sector')).replace('\xa0', ' ').strip() if highlight_state.get('sector') else ""

                if highlight_state.get('type') == 'month':
                    # Highlight entire stack for date
                    if h_date.lower() == date_str.lower():
                        op = 1.0
                        
                elif highlight_state.get('type') == 'bar':
                    # Highlight specific segment
                    if h_date.lower() == date_str.lower() and h_sector.lower() == sector.lower():
                        op = 1.0
                        lw = 2
                        lc = 'black' # Black border for selected segment
            
            opacities.append(op)
            line_widths.append(lw)
            line_colors.append(lc)

        fig.add_trace(go.Bar(
            name=sector,
            x=x_axis_labels,
            y=y_vals,
            marker=dict(
                color=COLORS.get(sector, '#ccc'),
                opacity=opacities,
                line=dict(
                    width=line_widths,
                    color=line_colors
                )
            ),
            hovertemplate=(
                "<span style='color: #777'>Sector:</span> <span style='color: black'>%{data.name}</span><br>" +
                "<span style='color: #777'>Date:</span> <span style='color: black'>%{x}</span><br>" +
                "<span style='color: #777'>Value:</span> <span style='color: black'>%{y:" + val_fmt + "}</span><br>" +
                f"<span style='color: #777'>Unit:</span> <span style='color: black'>{unit}</span>" +
                "<extra></extra>"
            ),
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial"
            )
        ))

    fig.update_layout(
        barmode='stack',
        xaxis=dict(
            title='',
            showgrid=False,
            showline=True,
            linecolor='#ccc',
            tickangle=-90,
            tickfont=dict(size=10, color='#999'),
            tickmode='array',
            tickvals=x_axis_labels,
            ticktext=tick_texts
        ),
        yaxis=dict(
            title='',
            showgrid=False,
            showline=False,
            zeroline=True,
            zerolinecolor='#ccc',
            tickfont=dict(size=10, color='#999')
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(t=30, b=80, l=40, r=10),
        height=500,
        showlegend=False,
        clickmode='event',
        bargap=0.2
    )

    return fig


def build_table(df, sector_filter, unit, time_level='YEARLY'):
    if df.empty:
        return html.Div("No data found.", style={'padding': '20px', 'textAlign': 'center'})

    # Handle different time levels
    if time_level == 'YEARLY':
        return build_yearly_table(df, sector_filter, unit)
    elif time_level == 'QUARTERLY':
        return build_quarterly_table(df, sector_filter, unit)
    elif time_level == 'DAILY':
        return build_daily_table(df, sector_filter, unit)
    else:  # MONTHLY (default)
        return build_monthly_table(df, sector_filter, unit)

def build_yearly_table(df, sector_filter, unit):
    """Build table with yearly columns."""
    years = sorted(df['Year of Date'].unique(), reverse=True)
    countries = sorted(df['Country'].unique())
    table_sector_order = ['Household', 'Industrial', 'Other', 'Power']
    
    if sector_filter != '(All)':
        sectors_to_show = [sector_filter]
    else:
        sectors_to_show = table_sector_order
    
    table_data = []
    for country in countries:
        country_df = df[df['Country'] == country]
        
        is_first_sector = True
        for sector in sectors_to_show:
            sector_df = country_df[country_df['Sector'] == sector]
            if sector_df.empty and sector_filter == '(All)':
               continue
                
            row = {
                'Country': country if is_first_sector else "", 
                'Sector': sector,
                'Country_Full': country
            }
            is_first_sector = False
            
            for y in years:
                year_df = sector_df[sector_df['Year of Date'] == y]
                year_total = year_df['adjusted_unit_value'].sum()
                row[str(y)] = year_total
            table_data.append(row)
            
        if sector_filter == '(All)':
            t_row = {
                'Country': "", 
                'Sector': 'Total',
                'Country_Full': country
            }
            for y in years:
                y_df = country_df[country_df['Year of Date'] == y]
                y_total = y_df['adjusted_unit_value'].sum()
                t_row[str(y)] = y_total
            table_data.append(t_row)

    fmt = ',.1f' if unit == 'Billion Cubic Meter' else ',.0f'
    
    columns = [
        {'name': 'Country', 'id': 'Country'},
        {'name': 'Sector', 'id': 'Sector'}
    ]
    
    data_col_ids = []
    
    for y in years:
        columns.append({
            'name': str(y), 
            'id': str(y), 
            'type': 'numeric', 
            'format': {'specifier': fmt}
        })
        data_col_ids.append(str(y))

    # Generate tooltip data
    tooltip_data = []
    val_fmt_func = (lambda v: f"{v:,.1f}") if unit == 'Billion Cubic Meter' else (lambda v: f"{v:,.0f}")
    
    for row in table_data:
        row_tooltip = {}
        country_name = row.get('Country_Full', '')
        sector_name = row.get('Sector', '')
        
        for col_id in data_col_ids:
            if col_id in row:
                val = row[col_id]
                y_val = col_id
                tooltip_text = f"**Country:** {country_name}  \n**Sector:** {sector_name}  \n**Year of Date:** {y_val}  \n**Value:** {val_fmt_func(val)}  \n**Unit:** {unit}"
                row_tooltip[col_id] = {'value': tooltip_text, 'type': 'markdown'}
        tooltip_data.append(row_tooltip)


    return html.Div([
        dash_table.DataTable(
            id='asia-gas-demand-table',
            data=table_data,
            columns=columns,
            tooltip_data=tooltip_data,
            tooltip_delay=0,
            tooltip_duration=None,
            css=[{
                'selector': '.dash-table-tooltip',
                'rule': 'background-color: white !important; color: black !important; border: 1px solid #777 !important; border-radius: 2px !important; font-family: Arial, sans-serif !important; font-size: 12px !important; padding: 8px !important; box-shadow: 2px 2px 5px rgba(0,0,0,0.1) !important; opacity: 1 !important; text-align: left !important; min-width: 150px !important;'
            }, {
                'selector': '.dash-table-tooltip strong',
                'rule': 'color: #777 !important; font-weight: normal !important; display: inline-block; margin-right: 5px;'
            }],
            fixed_rows={'headers': True},
            fixed_columns={'headers': True, 'data': 2},
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
            style_header_conditional=[
                {'if': {'column_id': ['Country', 'Sector']}, 'textAlign': 'left'},
                {'if': {'column_id': 'Sector'}, 'borderRight': '1px solid #ccc'},
            ],
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#fafbfc'
                },
                {
                    'if': {'filter_query': '{Sector} eq "Total"'},
                    'fontWeight': 'bold',
                    'color': '#000',
                    'borderBottom': '2px solid #aaa',
                    'borderTop': '1px solid #eee'
                },
                {
                    'if': {'column_id': 'Country'},
                    'textAlign': 'left',
                    'fontWeight': 'bold',
                    'minWidth': '120px',
                    'color': '#333'
                },
                {
                    'if': {'column_id': 'Sector'},
                    'textAlign': 'left',
                    'paddingLeft': '8px',
                    'minWidth': '100px',
                    'borderRight': '1px solid #ccc'
                }
            ],
            style_as_list_view=False,
        )
    ], style={'backgroundColor': '#fff', 'paddingBottom': '40px'})

def build_quarterly_table(df, sector_filter, unit):
    """Build table with quarterly columns."""
    years = sorted(df['Year of Date'].unique(), reverse=True)
    countries = sorted(df['Country'].unique())
    table_sector_order = ['Household', 'Industrial', 'Other', 'Power']
    
    if sector_filter != '(All)':
        sectors_to_show = [sector_filter]
    else:
        sectors_to_show = table_sector_order
    
    # Get quarters for each year
    quarters_map = {}
    for y in years:
        year_df = df[df['Year of Date'] == y]
        quarters = sorted(year_df['Date_Obj'].dt.quarter.unique())
        quarters_map[y] = [f'Q{q}' for q in quarters]
    
    table_data = []
    for country in countries:
        country_df = df[df['Country'] == country]
        
        is_first_sector = True
        for sector in sectors_to_show:
            sector_df = country_df[country_df['Sector'] == sector]
            if sector_df.empty and sector_filter == '(All)':
               continue
                
            row = {
                'Country': country if is_first_sector else "", 
                'Sector': sector,
                'Country_Full': country
            }
            is_first_sector = False
            
            for y in years:
                year_quarters = quarters_map[y]
                year_df = sector_df[sector_df['Year of Date'] == y]
                year_total = 0
                for q in year_quarters:
                    q_num = int(q[1])
                    quarter_df = year_df[year_df['Date_Obj'].dt.quarter == q_num]
                    val = quarter_df['adjusted_unit_value'].sum()
                    row[f"{y}_{q}"] = val
                    year_total += val
                row[f"{y}_Total"] = year_total
            table_data.append(row)
            
        if sector_filter == '(All)':
            t_row = {
                'Country': "", 
                'Sector': 'Total',
                'Country_Full': country
            }
            for y in years:
                year_quarters = quarters_map[y]
                y_df = country_df[country_df['Year of Date'] == y]
                y_total = 0
                for q in year_quarters:
                    q_num = int(q[1])
                    quarter_df = y_df[y_df['Date_Obj'].dt.quarter == q_num]
                    val = quarter_df['adjusted_unit_value'].sum()
                    t_row[f"{y}_{q}"] = val
                    y_total += val
                t_row[f"{y}_Total"] = y_total
            table_data.append(t_row)

    fmt = ',.1f' if unit == 'Billion Cubic Meter' else ',.0f'
    
    columns = [
        {'name': ['\u00A0', 'Country'], 'id': 'Country'},
        {'name': ['\u00A0', 'Sector'], 'id': 'Sector'}
    ]
    
    data_col_ids = []
    
    for y in years:
        year_quarters = quarters_map[y]
        for q in year_quarters:
            col_id = f"{y}_{q}"
            columns.append({
                'name': [str(y), q], 
                'id': col_id, 
                'type': 'numeric', 
                'format': {'specifier': fmt}
            })
            data_col_ids.append(col_id)
            
        columns.append({
            'name': [str(y), 'Total'], 
            'id': f"{y}_Total", 
            'type': 'numeric', 
            'format': {'specifier': fmt}
        })
        data_col_ids.append(f"{y}_Total")

    # Generate tooltip data
    tooltip_data = []
    val_fmt_func = (lambda v: f"{v:,.1f}") if unit == 'Billion Cubic Meter' else (lambda v: f"{v:,.0f}")
    
    for row in table_data:
        row_tooltip = {}
        country_name = row.get('Country_Full', '')
        sector_name = row.get('Sector', '')
        
        for col_id in data_col_ids:
            if col_id in row:
                val = row[col_id]
                if '_Total' in col_id:
                    y_val = col_id.split('_')[0]
                    tooltip_text = f"**Country:** {country_name}  \n**Sector:** {sector_name}  \n**Year of Date:** {y_val}  \n**Value:** {val_fmt_func(val)}  \n**Unit:** {unit}"
                else:
                    y_val, q_val = col_id.split('_')
                    tooltip_text = f"**Quarter of Date:** {q_val}  \n**Country:** {country_name}  \n**Sector:** {sector_name}  \n**Year of Date:** {y_val}  \n**Value:** {val_fmt_func(val)}  \n**Unit:** {unit}"
                
                row_tooltip[col_id] = {'value': tooltip_text, 'type': 'markdown'}
        tooltip_data.append(row_tooltip)

    return html.Div([
        dash_table.DataTable(
            id='asia-gas-demand-table',
            data=table_data,
            columns=columns,
            tooltip_data=tooltip_data,
            tooltip_delay=0,
            tooltip_duration=None,
            css=[{
                'selector': '.dash-table-tooltip',
                'rule': 'background-color: white !important; color: black !important; border: 1px solid #777 !important; border-radius: 2px !important; font-family: Arial, sans-serif !important; font-size: 12px !important; padding: 8px !important; box-shadow: 2px 2px 5px rgba(0,0,0,0.1) !important; opacity: 1 !important; text-align: left !important; min-width: 150px !important;'
            }, {
                'selector': '.dash-table-tooltip strong',
                'rule': 'color: #777 !important; font-weight: normal !important; display: inline-block; margin-right: 5px;'
            }],
            merge_duplicate_headers=True,
            fixed_rows={'headers': True},
            fixed_columns={'headers': True, 'data': 2},
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
            style_header_conditional=[
                {'if': {'header_index': 0, 'column_id': data_col_ids}, 'borderBottom': '1px solid #d0d0d0'},
                {'if': {'header_index': 0, 'column_id': data_col_ids}, 'textAlign': 'center'},
                {'if': {'header_index': 1, 'column_id': data_col_ids}, 'borderTop': '1px solid #d0d0d0'},
                {'if': {'header_index': 1, 'column_id': data_col_ids}, 'borderBottom': '1px solid #ccc'},
                {'if': {'column_id': ['Country', 'Sector']}, 'textAlign': 'left'},
                {'if': {'column_id': 'Sector'}, 'borderRight': '1px solid #ccc'},
                {'if': {'column_id': [f"{y}_Total" for y in years]}, 'borderRight': '1px solid #ccc'},
            ],
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#fafbfc'
                },
                {
                    'if': {'filter_query': '{Sector} eq "Total"'},
                    'fontWeight': 'bold',
                    'color': '#000',
                    'borderBottom': '2px solid #aaa',
                    'borderTop': '1px solid #eee'
                },
                {
                    'if': {'column_id': 'Country'},
                    'textAlign': 'left',
                    'fontWeight': 'bold',
                    'minWidth': '120px',
                    'color': '#333'
                },
                {
                    'if': {'column_id': 'Sector'},
                    'textAlign': 'left',
                    'paddingLeft': '8px',
                    'minWidth': '100px',
                    'borderRight': '1px solid #ccc'
                },
                {
                    'if': {'column_id': [f"{y}_Total" for y in years]},
                    'borderRight': '1px solid #ccc'
                }
            ],
            style_as_list_view=False,
        )
    ], style={'backgroundColor': '#fff', 'paddingBottom': '40px'})

def build_monthly_table(df, sector_filter, unit):
    """Build table with monthly columns (original implementation)."""
    years = sorted(df['Year of Date'].unique(), reverse=True)
    months_ref = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    
    def month_sort_key(m):
        try:
            return months_ref.index(m)
        except:
            return -1

    active_months_map = {}
    for y in years:
        m_in_data = df[df['Year of Date'] == y]['Month of Date'].unique().tolist()
        m_in_data.sort(key=month_sort_key, reverse=True)
        active_months_map[y] = m_in_data

    countries = sorted(df['Country'].unique())
    table_sector_order = ['Household', 'Industrial', 'Other', 'Power']
    
    if sector_filter != '(All)':
        sectors_to_show = [sector_filter]
    else:
        sectors_to_show = table_sector_order
    
    table_data = []
    for country in countries:
        country_df = df[df['Country'] == country]
        
        is_first_sector = True
        for sector in sectors_to_show:
            sector_df = country_df[country_df['Sector'] == sector]
            if sector_df.empty and sector_filter == '(All)':
               continue
                
            row = {
                'Country': country if is_first_sector else "", 
                'Sector': sector,
                'Country_Full': country
            }
            is_first_sector = False
            
            for y in years:
                year_months = active_months_map[y]
                year_df = sector_df[sector_df['Year of Date'] == y]
                year_total = 0
                for m in year_months:
                    val = year_df[year_df['Month of Date'] == m]['adjusted_unit_value'].sum()
                    row[f"{y}_{m}"] = val
                    year_total += val
                row[f"{y}_Total"] = year_total
            table_data.append(row)
            
        if sector_filter == '(All)':
            t_row = {
                'Country': "", 
                'Sector': 'Total',
                'Country_Full': country
            }
            for y in years:
                y_df = country_df[country_df['Year of Date'] == y]
                year_months = active_months_map[y]
                y_total = 0
                for m in year_months:
                    val = y_df[y_df['Month of Date'] == m]['adjusted_unit_value'].sum()
                    t_row[f"{y}_{m}"] = val
                    y_total += val
                t_row[f"{y}_Total"] = y_total
            table_data.append(t_row)

    fmt = ',.1f' if unit == 'Billion Cubic Meter' else ',.0f'
    
    columns = [
        {'name': ['\u00A0', 'Country'], 'id': 'Country'},
        {'name': ['\u00A0', 'Sector'], 'id': 'Sector'}
    ]
    
    data_col_ids = []
    
    for y in years:
        year_months = active_months_map[y]
        for m in year_months:
            col_id = f"{y}_{m}"
            columns.append({
                'name': [str(y), m], 
                'id': col_id, 
                'type': 'numeric', 
                'format': {'specifier': fmt}
            })
            data_col_ids.append(col_id)
            
        columns.append({
            'name': [str(y), 'Total'], 
            'id': f"{y}_Total", 
            'type': 'numeric', 
            'format': {'specifier': fmt}
        })
        data_col_ids.append(f"{y}_Total")

    # Generate tooltip data
    tooltip_data = []
    val_fmt_func = (lambda v: f"{v:,.1f}") if unit == 'Billion Cubic Meter' else (lambda v: f"{v:,.0f}")
    
    for row in table_data:
        row_tooltip = {}
        country_name = row.get('Country_Full', '')
        sector_name = row.get('Sector', '')
        
        for col_id in data_col_ids:
            if col_id in row:
                val = row[col_id]
                if '_Total' in col_id:
                    y_val = col_id.split('_')[0]
                    tooltip_text = f"**Country:** {country_name}  \n**Sector:** {sector_name}  \n**Year of Date:** {y_val}  \n**Value:** {val_fmt_func(val)}  \n**Unit:** {unit}"
                else:
                    y_val, m_val = col_id.split('_')
                    tooltip_text = f"**Month of Date:** {m_val}  \n**Country:** {country_name}  \n**Sector:** {sector_name}  \n**Year of Date:** {y_val}  \n**Value:** {val_fmt_func(val)}  \n**Unit:** {unit}"
                
                row_tooltip[col_id] = {'value': tooltip_text, 'type': 'markdown'}
        tooltip_data.append(row_tooltip)

    return html.Div([
        dash_table.DataTable(
            id='asia-gas-demand-table',
            data=table_data,
            columns=columns,
            tooltip_data=tooltip_data,
            tooltip_delay=0,
            tooltip_duration=None,
            css=[{
                'selector': '.dash-table-tooltip',
                'rule': 'background-color: white !important; color: black !important; border: 1px solid #777 !important; border-radius: 2px !important; font-family: Arial, sans-serif !important; font-size: 12px !important; padding: 8px !important; box-shadow: 2px 2px 5px rgba(0,0,0,0.1) !important; opacity: 1 !important; text-align: left !important; min-width: 150px !important;'
            }, {
                'selector': '.dash-table-tooltip strong',
                'rule': 'color: #777 !important; font-weight: normal !important; display: inline-block; margin-right: 5px;'
            }],
            merge_duplicate_headers=True,
            fixed_rows={'headers': True},
            fixed_columns={'headers': True, 'data': 2},
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
            style_header_conditional=[
                {'if': {'header_index': 0, 'column_id': data_col_ids}, 'borderBottom': '1px solid #d0d0d0'},
                {'if': {'header_index': 0, 'column_id': data_col_ids}, 'textAlign': 'center'},
                {'if': {'header_index': 1, 'column_id': data_col_ids}, 'borderTop': '1px solid #d0d0d0'},
                {'if': {'header_index': 1, 'column_id': data_col_ids}, 'borderBottom': '1px solid #ccc'},
                {'if': {'column_id': ['Country', 'Sector']}, 'zIndex': 999, 'textAlign': 'left'},
                {'if': {'header_index': 0, 'column_id': ['Country', 'Sector']}, 
                 'backgroundColor': '#ffffff', 
                 'borderBottom': '1px solid #d0d0d0', 
                 'borderTop': 'none',
                 'borderRight': 'none'},
                {'if': {'header_index': 1, 'column_id': ['Country', 'Sector']}, 
                 'backgroundColor': '#ffffff', 
                 'borderTop': 'none', 
                 'borderBottom': '1px solid #ccc'}, 
                {'if': {'column_id': 'Sector'}, 'borderRight': '1px solid #ccc'},
                {'if': {'column_id': [f"{y}_Total" for y in years]}, 'borderRight': '1px solid #ccc'},
            ],
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#fafbfc'
                },
                {
                    'if': {'filter_query': '{Sector} eq "Total"'},
                    'fontWeight': 'bold',
                    'color': '#000',
                    'borderBottom': '2px solid #aaa',
                    'borderTop': '1px solid #eee'
                },
                {
                    'if': {'column_id': 'Country'},
                    'textAlign': 'left',
                    'fontWeight': 'bold',
                    'minWidth': '120px',
                    'color': '#333'
                },
                {
                    'if': {'column_id': 'Sector'},
                    'textAlign': 'left',
                    'paddingLeft': '8px',
                    'minWidth': '100px',
                    'borderRight': '1px solid #ccc'
                },
                {
                    'if': {'column_id': [f"{y}_Total" for y in years]},
                    'borderRight': '1px solid #ccc'
                }
            ],
            style_as_list_view=False,
        )
    ], style={'backgroundColor': '#fff', 'paddingBottom': '40px'})

def build_daily_table(df, sector_filter, unit):
    """Build table like monthly table but with '1' under each month header."""
    years = sorted(df['Year of Date'].unique(), reverse=True)
    months_ref = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    
    def month_sort_key(m):
        try:
            return months_ref.index(m)
        except:
            return -1

    active_months_map = {}
    for y in years:
        m_in_data = df[df['Year of Date'] == y]['Month of Date'].unique().tolist()
        m_in_data.sort(key=month_sort_key, reverse=True)
        active_months_map[y] = m_in_data

    countries = sorted(df['Country'].unique())
    table_sector_order = ['Household', 'Industrial', 'Other', 'Power']
    
    if sector_filter != '(All)':
        sectors_to_show = [sector_filter]
    else:
        sectors_to_show = table_sector_order
    
    table_data = []
    for country in countries:
        country_df = df[df['Country'] == country]
        
        is_first_sector = True
        for sector in sectors_to_show:
            sector_df = country_df[country_df['Sector'] == sector]
            if sector_df.empty and sector_filter == '(All)':
               continue
                
            row = {
                'Country': country if is_first_sector else "", 
                'Sector': sector,
                'Country_Full': country
            }
            is_first_sector = False
            
            for y in years:
                year_months = active_months_map[y]
                year_df = sector_df[sector_df['Year of Date'] == y]
                year_total = 0
                for m in year_months:
                    val = year_df[year_df['Month of Date'] == m]['adjusted_unit_value'].sum()
                    row[f"{y}_{m}_1"] = val  # Add _1 to column name
                    year_total += val
                row[f"{y}_Total"] = year_total
            table_data.append(row)
            
        if sector_filter == '(All)':
            t_row = {
                'Country': "", 
                'Sector': 'Total',
                'Country_Full': country
            }
            for y in years:
                y_df = country_df[country_df['Year of Date'] == y]
                year_months = active_months_map[y]
                y_total = 0
                for m in year_months:
                    val = y_df[y_df['Month of Date'] == m]['adjusted_unit_value'].sum()
                    t_row[f"{y}_{m}_1"] = val  # Add _1 to column name
                    y_total += val
                t_row[f"{y}_Total"] = y_total
            table_data.append(t_row)

    fmt = ',.1f' if unit == 'Billion Cubic Meter' else ',.0f'
    
    # 3-level headers: Year -> Month -> "1"
    columns = [
        {'name': ['\u00A0', '\u00A0', 'Country'], 'id': 'Country'},
        {'name': ['\u00A0', '\u00A0', 'Sector'], 'id': 'Sector'}
    ]
    
    data_col_ids = []
    
    for y in years:
        year_months = active_months_map[y]
        for i, m in enumerate(year_months):
            col_id = f"{y}_{m}_1"
            # Use zero-width space to prevent merging of '1' headers across months
            header_day = '1' + ('\u200b' * (i + 1))
            columns.append({
                'name': [str(y), m, header_day],
                'id': col_id, 
                'type': 'numeric', 
                'format': {'specifier': fmt}
            })
            data_col_ids.append(col_id)

        # Append Total column last (Right side of the year)
        columns.append({
            'name': [str(y), 'Total', '\u00A0'], 
            'id': f"{y}_Total", 
            'type': 'numeric', 
            'format': {'specifier': fmt}
        })
        data_col_ids.append(f"{y}_Total")

    # Generate tooltip data
    tooltip_data = []
    val_fmt_func = (lambda v: f"{v:,.1f}") if unit == 'Billion Cubic Meter' else (lambda v: f"{v:,.0f}")
    
    for row in table_data:
        row_tooltip = {}
        country_name = row.get('Country_Full', '')
        sector_name = row.get('Sector', '')
        
        for col_id in data_col_ids:
            if col_id in row:
                val = row[col_id]
                if '_Total' in col_id:
                    y_val = col_id.split('_')[0]
                    tooltip_text = f"**Country:** {country_name}  \n**Sector:** {sector_name}  \n**Year of Date:** {y_val}  \n**Value:** {val_fmt_func(val)}  \n**Unit:** {unit}"
                elif col_id.endswith('_1'):
                    parts = col_id.split('_')
                    y_val = parts[0]
                    m_val = parts[1]
                    d_val = parts[2]
                    tooltip_text = f"**Day of Date:** {d_val}  \n**Month of Date:** {m_val}  \n**Country:** {country_name}  \n**Sector:** {sector_name}  \n**Year of Date:** {y_val}  \n**Value:** {val_fmt_func(val)}  \n**Unit:** {unit}"
                else:
                    tooltip_text = f"Value: {val_fmt_func(val)}"
                
                row_tooltip[col_id] = {'value': tooltip_text, 'type': 'markdown'}
        tooltip_data.append(row_tooltip)

    return html.Div([
        dash_table.DataTable(
            id='asia-gas-demand-table',
            data=table_data,
            columns=columns,
            tooltip_data=tooltip_data,
            tooltip_delay=0,
            tooltip_duration=None,
            css=[{
                'selector': '.dash-table-tooltip',
                'rule': 'background-color: white !important; color: black !important; border: 1px solid #777 !important; border-radius: 2px !important; font-family: Arial, sans-serif !important; font-size: 12px !important; padding: 8px !important; box-shadow: 2px 2px 5px rgba(0,0,0,0.1) !important; opacity: 1 !important; text-align: left !important; min-width: 150px !important;'
            }, {
                'selector': '.dash-table-tooltip strong',
                'rule': 'color: #777 !important; font-weight: normal !important; display: inline-block; margin-right: 5px;'
            }],
            merge_duplicate_headers=True,
            fixed_rows={'headers': True},
            fixed_columns={'headers': True, 'data': 2},
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
                'textAlign': 'center',
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
            style_header_conditional=[
                {'if': {'header_index': 0, 'column_id': data_col_ids}, 'borderBottom': '1px solid #d0d0d0'},
                {'if': {'header_index': 0, 'column_id': data_col_ids}, 'textAlign': 'center'},
                {'if': {'header_index': 1, 'column_id': data_col_ids}, 'borderTop': '1px solid #d0d0d0'},
                {'if': {'header_index': 1, 'column_id': data_col_ids}, 'borderBottom': '1px solid #ccc'},
                {'if': {'header_index': 2, 'column_id': data_col_ids}, 'borderTop': '1px solid #d0d0d0'},
                {'if': {'header_index': 2, 'column_id': data_col_ids}, 'borderBottom': '1px solid #ccc'},
                {'if': {'column_id': ['Country', 'Sector']}, 'zIndex': 999, 'textAlign': 'left'},
                {'if': {'header_index': 0, 'column_id': ['Country', 'Sector']}, 
                 'backgroundColor': '#ffffff', 
                 'borderBottom': '1px solid #d0d0d0', 
                 'borderTop': 'none'},
                {'if': {'header_index': 1, 'column_id': ['Country', 'Sector']}, 
                 'backgroundColor': '#ffffff', 
                 'borderTop': 'none', 
                 'borderBottom': '1px solid #ccc'}, 
                {'if': {'header_index': 2, 'column_id': ['Country', 'Sector']}, 
                 'backgroundColor': '#ffffff', 
                 'borderTop': 'none', 
                 'borderBottom': '1px solid #ccc'}, 
                {'if': {'column_id': 'Sector'}, 'borderRight': '2px solid #ccc'},
                {'if': {'column_id': [f"{y}_Total" for y in years]}, 'borderRight': '1px solid #ccc'},
            ],
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#fafbfc'
                },
                {
                    'if': {'filter_query': '{Sector} eq "Total"'},
                    'fontWeight': 'bold',
                    'color': '#000',
                    'borderBottom': '2px solid #aaa',
                    'borderTop': '1px solid #eee'
                },
                {
                    'if': {'column_id': 'Country'},
                    'textAlign': 'left',
                    'fontWeight': 'bold',
                    'minWidth': '120px',
                    'color': '#333'
                },
                {
                    'if': {'column_id': 'Sector'},
                    'textAlign': 'left',
                    'paddingLeft': '8px',
                    'minWidth': '100px',
                    'borderRight': '1px solid #ccc'
                },
                {
                    'if': {'column_id': [f"{y}_Total" for y in years]},
                    'borderRight': '1px solid #ccc'
                }
            ],
            style_as_list_view=False,
        )
    ], style={'backgroundColor': '#fff', 'paddingBottom': '40px'})

def register_callbacks(dash_app, server):
    # Chart Hierarchy Callbacks
    @dash_app.callback(
        [Output('chart-time-level', 'data'),
         Output('asia-chart-toggle-year-btn', 'children'),
         Output('asia-chart-toggle-quarter-btn', 'children'),
         Output('asia-chart-toggle-month-btn', 'children'),
         Output('asia-chart-toggle-day-btn', 'children')],
        [Input('asia-chart-toggle-year-btn', 'n_clicks'),
         Input('asia-chart-toggle-quarter-btn', 'n_clicks'),
         Input('asia-chart-toggle-month-btn', 'n_clicks'),
         Input('asia-chart-toggle-day-btn', 'n_clicks')],
        [State('chart-time-level', 'data')]
    )
    def chart_hierarchy_handler(y_c, q_c, m_c, d_c, current_level):
        if not ctx.triggered:
            cl = current_level or 'MONTHLY'
            return (cl, 
                    '-' if cl == 'YEARLY' else '+',
                    '-' if cl == 'QUARTERLY' else '+',
                    '-' if cl == 'MONTHLY' else '+',
                    '-' if cl == 'DAILY' else '+')

        btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        new_level = 'MONTHLY'
        if 'year' in btn_id:
            new_level = 'YEARLY'
        elif 'quarter' in btn_id:
            new_level = 'QUARTERLY'
        elif 'month' in btn_id:
            new_level = 'MONTHLY'
        elif 'day' in btn_id:
            new_level = 'DAILY'
            
        return (new_level,
                '-' if new_level == 'YEARLY' else '+',
                '-' if new_level == 'QUARTERLY' else '+',
                '-' if new_level == 'MONTHLY' else '+',
                '-' if new_level == 'DAILY' else '+')

    # Table Hierarchy Callbacks
    @dash_app.callback(
        [Output('table-time-level', 'data'),
         Output('asia-table-toggle-year-btn', 'children'),
         Output('asia-table-toggle-quarter-btn', 'children'),
         Output('asia-table-toggle-month-btn', 'children'),
         Output('asia-table-toggle-day-btn', 'children')],
        [Input('asia-table-toggle-year-btn', 'n_clicks'),
         Input('asia-table-toggle-quarter-btn', 'n_clicks'),
         Input('asia-table-toggle-month-btn', 'n_clicks'),
         Input('asia-table-toggle-day-btn', 'n_clicks')],
        [State('table-time-level', 'data')]
    )
    def table_hierarchy_handler(y_c, q_c, m_c, d_c, current_level):
        if not ctx.triggered:
            cl = current_level or 'MONTHLY'  # Changed default to MONTHLY
            return (cl, 
                    '-' if cl == 'YEARLY' else '+',
                    '-' if cl == 'QUARTERLY' else '+',
                    '-' if cl == 'MONTHLY' else '+',
                    '-' if cl == 'DAILY' else '+')

        btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        new_level = 'MONTHLY'  # Changed default to MONTHLY
        if 'year' in btn_id:
            new_level = 'YEARLY'
        elif 'quarter' in btn_id:
            new_level = 'QUARTERLY'
        elif 'month' in btn_id:
            new_level = 'MONTHLY'
        elif 'day' in btn_id:
            new_level = 'DAILY'
            
        return (new_level,
                '-' if new_level == 'YEARLY' else '+',
                '-' if new_level == 'QUARTERLY' else '+',
                '-' if new_level == 'MONTHLY' else '+',
                '-' if new_level == 'DAILY' else '+')

    # 0. Data Fetching Callback
    @dash_app.callback(
        [Output('store-asia-chart-data', 'data'),
         Output('store-asia-table-data', 'data')],
        Input('asia-country-filter', 'value')
    )
    def fetch_asia_data(country):
        # This callback MUST run to populate stores.
        df_chart = load_chart_data(country)
        df_table = load_table_data(country)
        
        # We return records. Date objects will be strings.
        # df_chart has Date_Obj column.
        return df_chart.to_dict('records'), df_table.to_dict('records')

    # Clientside callback to enhance date picker styling (remove default calendar icon but keep functionality)
    dash_app.clientside_callback(
        """
        function(n_clicks) {
            const style = document.createElement('style');
            style.innerHTML = `
                /* Hide default calendar icon for date inputs */
                input[type="date"]::-webkit-inner-spin-button,
                input[type="date"]::-webkit-calendar-picker-indicator {
                    display: none;
                    -webkit-appearance: none;
                }
                
                /* Ensure entire input is clickable to open picker */
                input[type="date"] {
                    position: relative;
                }
                
                input[type="date"]::-webkit-calendar-picker-indicator {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    width: auto;
                    height: auto;
                    color: transparent;
                    background: transparent;
                }
            `;
            document.head.appendChild(style);
            
            // Add click listener to open picker programmatically if needed
            setTimeout(function() {
                const startInput = document.getElementById('asia-sector-start-date');
                const endInput = document.getElementById('asia-sector-end-date');
                
                if (startInput) {
                    startInput.addEventListener('click', function(e) {
                        try {
                            this.showPicker();
                        } catch (error) {
                            console.log('showPicker not supported');
                        }
                    });
                }
                
                if (endInput) {
                    endInput.addEventListener('click', function(e) {
                        try {
                            this.showPicker();
                        } catch (error) {
                            console.log('showPicker not supported');
                        }
                    });
                }
            }, 1000);
            
            return null;
        }
        """,
        Output('asia-sector-date-picker-enhancer-anchor', 'children'),
        Input('asia-sector-date-picker-enhancer-anchor', 'id')
    )

    # Helper functions for date conversion
    def _index_to_date(index, date_list):
        if 0 <= index < len(date_list):
            return date_list[index]
        return None

    def _date_to_index(date_str, date_list):
        try:
            dt = pd.to_datetime(date_str)
            # Find the exact match first
            for i, d in enumerate(date_list):
                if d == dt:
                    return i
            # If not exact match, find closest
            diffs = [abs((d - dt).days) for d in date_list]
            return diffs.index(min(diffs))
        except:
            return 0 # Fallback

    def _format_date_for_display(dt_obj):
        if dt_obj:
            return dt_obj.strftime('%Y-%m-%d')
        return None

    # Sync date controls (Inputs <-> Slider)
    @dash_app.callback(
        [Output('asia-sector-start-date', 'value'),
         Output('asia-sector-end-date', 'value'),
         Output('asia-date-slider', 'value')],
        [Input('asia-sector-start-date', 'value'),
         Input('asia-sector-end-date', 'value'),
         Input('asia-date-slider', 'value')],
        [State('asia-sector-date-list-store', 'data')], # This should be the list of all possible dates for the slider
        prevent_initial_call=True
    )
    def sync_date_controls(start_str, end_str, slider_val, date_list):
        from dash import callback_context
        
        if not callback_context.triggered or not date_list:
            return no_update, no_update, no_update
            
        trigger_id = callback_context.triggered[0]['prop_id']
        
        # Convert date list strings back to Timestamps
        dates = [pd.to_datetime(d) for d in date_list]
        
        if 'asia-date-slider' in trigger_id:
            # Slider moved -> Update inputs
            start_idx, end_idx = slider_val
            new_start = _index_to_date(start_idx, dates)
            new_end = _index_to_date(end_idx, dates)
            
            return _format_date_for_display(new_start), _format_date_for_display(new_end), no_update
            
        else:
            # Input changed -> Update slider
            if not start_str or not end_str:
                return no_update, no_update, no_update
                
            start_idx = _date_to_index(start_str, dates)
            end_idx = _date_to_index(end_str, dates)
            
            # Ensure start <= end
            if start_idx > end_idx:
                if 'start-date' in trigger_id:
                    end_idx = start_idx
                    end_str = start_str
                else:
                    start_idx = end_idx
                    start_str = end_str
            
            return start_str, end_str, [start_idx, end_idx]

    @dash_app.callback(
        [Output('asia-gas-monthly-chart', 'figure'),
         Output('loading-trigger-chart', 'children'),
         Output('chart-highlight-state', 'data')], # Update highlight state
        [Input('store-asia-chart-data', 'data'),
         Input('asia-sector-start-date', 'value'),
         Input('asia-sector-end-date', 'value'),
         Input('asia-unit-filter', 'value'),
         Input('asia-sector-filter', 'value'),
         Input('chart-time-level', 'data'),
         Input('asia-gas-monthly-chart', 'clickData'),
         Input('asia-table-highlight-state', 'data'), # Listen to table click
         Input('axis-click-trigger', 'value')], # Listen to axis click
         [State('min-date', 'data'),
         State('max-date', 'data')]
    )
    def update_chart(data, start_date_str, end_date_str, unit, sector_filter, time_level, click_data, table_highlight, axis_click, min_date_store, max_date_store):
        try:
            # Determine Trigger and Highlight State
            trigger_id = ctx.triggered[0]['prop_id'] if ctx.triggered else None
            
            highlight_state = None
            
            # Priority: Axis Click > Chart Click > Table Click
            if trigger_id == 'axis-click-trigger.value' and axis_click:
                 # Parse axis click: "Date: <date>"
                 parts = axis_click.split(': ')
                 if len(parts) == 2:
                     highlight_state = {'date': parts[1], 'type': 'month'}
            elif trigger_id == 'asia-gas-monthly-chart.clickData' and click_data:
                 # Chart Click logic
                 point = click_data['points'][0]
                 # If clicked on a bar segment
                 date_str = point['x']
                 # We need to map curve number to sector manually or get from point data
                 sector = point.get('data', {}).get('name')
                 
                 highlight_state = {'date': date_str, 'sector': sector, 'type': 'bar'}
                 
            elif table_highlight:
                 # Sync from Table
                 highlight_state = table_highlight

            if not data:
                return go.Figure(), "", highlight_state

            df = pd.DataFrame(data)
            # Reconstruct Date
            if 'Date_Obj' not in df.columns:
                df['Date_Obj'] = pd.to_datetime(df['Month of Date'], format='%B %Y')
            else:
                 df['Date_Obj'] = pd.to_datetime(df['Date_Obj'])

            # Convert input strings to datetime (timezone naive)
            if not start_date_str or not end_date_str:
                 if min_date_store:
                     start_date = pd.to_datetime(min_date_store).tz_localize(None)
                     end_date = pd.to_datetime(max_date_store).tz_localize(None)
                 else:
                     return go.Figure(), "", highlight_state
            else:
                start_date = pd.to_datetime(start_date_str).tz_localize(None)
                end_date = pd.to_datetime(end_date_str).tz_localize(None)
                
            # Ensure DataFrame dates are timezone-naive
            if df['Date_Obj'].dt.tz is not None:
                 df['Date_Obj'] = df['Date_Obj'].dt.tz_localize(None)

            # Filter Data by Date inputs
            df_filtered = df[(df['Date_Obj'] >= start_date) & (df['Date_Obj'] <= end_date)].copy()
            
            fig = build_chart(df_filtered, sector_filter, unit, time_level, highlight_state)
            
            return fig, "", highlight_state
            
        except Exception as e:
            print(f"Error in update_chart: {e}")
            fig = go.Figure()
            fig.update_layout(title=f"Error: {str(e)}")
            return fig, no_update, None


    @dash_app.callback(
        [Output('asia-gas-monthly-table-container', 'children'),
         Output('loading-trigger-table', 'children')],
        [Input('store-asia-table-data', 'data'),
         Input('asia-sector-start-date', 'value'),
         Input('asia-sector-end-date', 'value'),
         Input('asia-unit-filter', 'value'),
         Input('asia-sector-filter', 'value'),
         Input('table-time-level', 'data')],
         [State('min-date', 'data'),
         State('max-date', 'data')]
    )
    def update_table(data, start_date_str, end_date_str, unit, sector_filter, time_level, min_date_store, max_date_store):
        try:
            if not data:
                return html.Div("No data available."), ""

            df = pd.DataFrame(data)
            # Reconstruct Date
            if 'Date_Obj' not in df.columns:
                df['Date_Obj'] = pd.to_datetime(df['Month of Date'], format='%B %Y')
            else:
                 df['Date_Obj'] = pd.to_datetime(df['Date_Obj'])

            # Convert input strings to datetime (timezone naive)
            if not start_date_str or not end_date_str:
                 if min_date_store:
                     start_date = pd.to_datetime(min_date_store).tz_localize(None)
                     end_date = pd.to_datetime(max_date_store).tz_localize(None)
                 else:
                     return html.Div("No data available."), ""
            else:
                start_date = pd.to_datetime(start_date_str).tz_localize(None)
                end_date = pd.to_datetime(end_date_str).tz_localize(None)
                
            # Ensure DataFrame dates are timezone-naive
            if df['Date_Obj'].dt.tz is not None:
                 df['Date_Obj'] = df['Date_Obj'].dt.tz_localize(None)

            # Filter Data by Date
            df_filtered = df[(df['Date_Obj'] >= start_date) & (df['Date_Obj'] <= end_date)].copy()
            
            table = build_table(df_filtered, sector_filter, unit, time_level)
            
            return table, ""
            
        except Exception as e:
            print(f"Error in update_table: {e}")
            return html.Div(f"Error: {str(e)}"), ""



    # 3. Clientside Callback for Table Highlighting (Reused exactly)
    dash_app.clientside_callback(
        """
        function(n_data, columns, current_state) {
            try {
                const tableId = 'asia-gas-demand-table';
                
                let style = document.getElementById('asia-gas-styles');
                if (!style) {
                    style = document.createElement('style');
                    style.id = 'asia-gas-styles';
                    document.head.appendChild(style);
                }
                
                style.innerHTML = `
                    .asia-col-selected { background-color: #cfe8ef !important; }
                    .asia-row-selected { background-color: #cfe8ef !important; }
                    .asia-dimmed { opacity: 0.3 !important; }
                    
                    .asia-col-selection-active td[data-dash-column="Country"], 
                    .asia-col-selection-active td[data-dash-column="Sector"] { 
                        opacity: 1 !important; 
                        background-color: transparent !important; 
                    }
                    
                    .asia-row-selection-active tr.asia-row-highlighted td {
                        opacity: 1 !important;
                        background-color: #cfe8ef !important;
                        color: black !important;
                    }

                    .asia-row-selection-active tr:not(.asia-row-trip-wire) td {
                        opacity: 0.3 !important;
                    }

                    th.asia-col-selected { background-color: #cfe8ef !important; }
                `;

                if (!window.asiaGasState) {
                    window.asiaGasState = { 
                        selectedColumnId: null,
                        selectedRowIndices: null 
                    };
                }

                function clearAll(spreadsheet) {
                    spreadsheet.classList.remove('asia-col-selection-active');
                    spreadsheet.classList.remove('asia-row-selection-active');
                    
                    const selected = spreadsheet.querySelectorAll('.asia-col-selected, .asia-dimmed, .asia-row-highlighted, .asia-row-trip-wire');
                    selected.forEach(el => {
                        el.classList.remove('asia-col-selected');
                        el.classList.remove('asia-dimmed');
                        el.classList.remove('asia-row-highlighted');
                        el.classList.remove('asia-row-trip-wire');
                    });
                }
                
                function applyState(spreadsheet, n_data) {
                    clearAll(spreadsheet);

                    if (window.asiaGasState.selectedColumnId) {
                        const targetIds = window.asiaGasState.selectedColumnId.split(',');
                        if (targetIds.length === 0) return;

                        spreadsheet.classList.add('asia-col-selection-active');

                        targetIds.forEach(id => {
                            const ths = spreadsheet.querySelectorAll(`th[data-dash-column="${id}"]`);
                            ths.forEach(th => th.classList.add('asia-col-selected'));
                        });

                        const allCells = spreadsheet.querySelectorAll('td[data-dash-column]');
                        allCells.forEach(cell => {
                            const cId = cell.getAttribute('data-dash-column');
                            if (cId === 'Country' || cId === 'Sector') return;

                            if (targetIds.includes(cId)) {
                                cell.classList.add('asia-col-selected');
                            } else {
                                cell.classList.add('asia-dimmed');
                            }
                        });
                        return;
                    }

                    if (window.asiaGasState.selectedRowIndices) {
                        const [start, end] = window.asiaGasState.selectedRowIndices.split('_').map(Number);
                        
                        spreadsheet.classList.add('asia-row-selection-active');
                        
                        const tbodies = spreadsheet.querySelectorAll('tbody');
                        
                        tbodies.forEach(tbody => {
                            const rows = tbody.querySelectorAll('tr');
                            rows.forEach((row, idx) => {
                                if (idx >= start && idx <= end) {
                                    row.classList.add('asia-row-highlighted');
                                    row.classList.add('asia-row-trip-wire');
                                }
                            });
                        });
                    }
                }

                function setupTable() {
                    const tableEl = document.getElementById(tableId);
                    if (!tableEl) {
                        // Table not ready yet, try again later
                        setTimeout(setupTable, 100);
                        return;
                    }
                    
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    if (!spreadsheet) {
                        // Spreadsheet not ready yet, try again later
                        setTimeout(setupTable, 100);
                        return;
                    }
                    
                    if (spreadsheet && (window.asiaGasState.selectedColumnId || window.asiaGasState.selectedRowIndices)) {
                        applyState(spreadsheet, n_data);
                    }
                    
                    if (spreadsheet.dataset.enhanced === 'true') return;

                    spreadsheet.dataset.enhanced = 'true';
                    
                    spreadsheet.addEventListener('click', function(e) {
                        const header = e.target.closest('th[data-dash-column]');
                        if (header) {
                            e.stopPropagation();
                            const colId = header.getAttribute('data-dash-column');
                            if (colId === 'Country' || colId === 'Sector') return;

                            const headerContent = header.innerText.trim();
                            let isYearHeader = /^\d{4}$/.test(headerContent);
                            let targetIds = [];
                            if (isYearHeader && columns) {
                                columns.forEach(c => {
                                    if (c.id && c.id.startsWith(headerContent + '_')) targetIds.push(c.id);
                                });
                            } else {
                                targetIds.push(colId);
                            }

                            const selectionKey = targetIds.join(',');
                            
                            if (window.asiaGasState.selectedColumnId === selectionKey) {
                                window.asiaGasState.selectedColumnId = null;
                            } else {
                                window.asiaGasState.selectedColumnId = selectionKey;
                                window.asiaGasState.selectedRowIndices = null; 
                            }
                            applyState(spreadsheet, n_data);
                            return;
                        }
                        
                        const cell = e.target.closest('td[data-dash-column]');
                        if (cell) {
                             const colId = cell.getAttribute('data-dash-column');
                             
                             // Only allow row highlighting for Country or Sector columns
                             if (colId !== 'Country' && colId !== 'Sector') {
                                 return; // Ignore clicks on data cells
                             }
                             
                             const row = cell.closest('tr');
                             const tbody = row.closest('tbody');
                             const rows = Array.from(tbody.querySelectorAll('tr'));
                             const idx = rows.indexOf(row);
                             
                             let start = idx;
                             let end = idx;
                             
                             if (colId === 'Country') {
                                 // Get the country name from the clicked cell
                                 const countryName = cell.innerText.trim();
                                 
                                 if (countryName) {
                                     // Find all rows for this country (including sectors and Total)
                                     start = idx;
                                     end = idx;
                                     
                                     // Look ahead to find all rows until we hit another country or end
                                     for (let i = idx + 1; i < rows.length; i++) {
                                         const nextRow = rows[i];
                                         const nextCountryCell = nextRow.querySelector('td[data-dash-column="Country"]');
                                         if (nextCountryCell && nextCountryCell.innerText.trim()) {
                                             // Found next country, stop here
                                             break;
                                         }
                                         end = i;
                                     }
                                 }
                             }
                             // If Sector column clicked, just highlight that single row (start = end = idx)
                             
                             const newKey = `${start}_${end}`;
                             
                             if (window.asiaGasState.selectedRowIndices === newKey) {
                                  window.asiaGasState.selectedRowIndices = null;
                             } else {
                                  window.asiaGasState.selectedRowIndices = newKey;
                                  window.asiaGasState.selectedColumnId = null;
                             }
                             applyState(spreadsheet, n_data);
                        }
                    });
                }
                
                // Clear state when table structure changes significantly
                if (window.asiaGasState && columns) {
                    const currentCols = columns.map(c => c.id).join(',');
                    if (window.asiaGasState.lastColumnStructure !== currentCols) {
                        window.asiaGasState.selectedColumnId = null;
                        window.asiaGasState.selectedRowIndices = null;
                        window.asiaGasState.lastColumnStructure = currentCols;
                    }
                }
                
                setTimeout(setupTable, 500); 
                return window.asiaGasState.selectedColumnId || ""; 

            } catch(e) { 
                console.error('Table highlighting error:', e); 
                return ""; 
            }
        }
        """,
        Output('asia-table-highlight-state', 'data'),
        Input('asia-gas-demand-table', 'data'),
        State('asia-gas-demand-table', 'columns'),
        State('asia-table-highlight-state', 'data')
    )

    # 4. Clientside Callback to attach X-Axis Click Listeners
    # Attaches listener to Plotly Axis Labels and updates 'axis-click-trigger'
    dash_app.clientside_callback(
        """
        function(fig_data) {
            // Wait for plot to render
            setTimeout(function() {
                try {
                    const graph = document.getElementById('asia-gas-monthly-chart');
                    if (!graph) return;
                    
                    // Target the groups 'g.xtick' to catch clicks on the general area
                    const ticks = graph.querySelectorAll('g.xtick');
                    
                    if (ticks.length === 0) return;
                    
                    ticks.forEach(t => {
                        t.style.cursor = 'pointer'; 
                        t.style.pointerEvents = 'all'; 
                        
                        // Prevent attaching multiple times if re-running
                        if (t.getAttribute('data-click-attached')) return;
                        t.setAttribute('data-click-attached', 'true');
                        
                        t.addEventListener('click', function(e) {
                            // Find the text content. It might be in a child 'text' element or 'tspan'
                            const textEl = t.querySelector('text');
                            if (textEl) {
                                let dateStr = textEl.textContent; 
                                // Remove any zero-width spaces or artifacts if present
                                dateStr = dateStr.replace(/[\\u200B\\u00A0]/g, ''); 
                                
                                const input = document.getElementById('axis-click-trigger');
                                if (input) {
                                    const payload = dateStr + "|" + Date.now();
                                    
                                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                                    nativeInputValueSetter.call(input, payload);
                                    input.dispatchEvent(new Event('input', { bubbles: true }));
                                }
                            }
                        });
                    });
                } catch(e) { console.error("Axis listener error:", e); }
            }, 1000); 
            return window.dash_clientside.no_update;
        }
        """,
        Output('axis-listener-output', 'children'), # Dedicated output
        Input('asia-gas-monthly-chart', 'figure')
    )

    # 5. Export Callbacks
    @dash_app.callback(
        Output("download-asia-chart-csv", "data"),
        Input("export-asia-chart-btn", 'n_clicks'),
        [State('asia-unit-filter', 'value'),
         State('asia-sector-filter', 'value'),
         State('asia-country-filter', 'value'),
         State('asia-sector-start-date', 'value'),
         State('asia-sector-end-date', 'value'),
         State('min-date', 'data'),
         State('max-date', 'data')],
        prevent_initial_call=True
    )
    def export_asia_chart_data(n_clicks, unit, sector, country, start_date_str, end_date_str, min_date_store, max_date_store):
        if not n_clicks:
            return no_update

        try:
            # Convert input strings to datetime (timezone naive)
            if not start_date_str or not end_date_str:
                 if min_date_store:
                     start_date = pd.to_datetime(min_date_store).tz_localize(None)
                     end_date = pd.to_datetime(max_date_store).tz_localize(None)
                 else:
                     return no_update
            else:
                start_date = pd.to_datetime(start_date_str).tz_localize(None)
                end_date = pd.to_datetime(end_date_str).tz_localize(None)

            # Load data using the country filter
            df = load_chart_data(country)
            
            if df.empty:
                return no_update

            # Apply filters manually to match dashboard view
            if unit:
                df = df[df['Unit'] == unit]
            
            if sector != '(All)':
                df = df[df['Sector'] == sector]
                
            # Ensure DataFrame dates are timezone-naive
            if 'Date_Obj' in df.columns:
                 df['Date_Obj'] = pd.to_datetime(df['Date_Obj'])
                 if df['Date_Obj'].dt.tz is not None:
                     df['Date_Obj'] = df['Date_Obj'].dt.tz_localize(None)
                
            if start_date and end_date:
                df = df[(df['Date_Obj'] >= start_date) & (df['Date_Obj'] <= end_date)]
            
            # Drop internal columns
            cols_to_drop = ['Date_Obj', 'Year', 'Month', 'Year of Date', 'Month of Date']
            df = df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors='ignore')
            
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"asia_gas_demand_chart_{timestamp}.csv"
            
            return dcc.send_data_frame(df.to_csv, filename, index=False)

        except Exception as e:
            print(f"Error exporting chart data: {e}")
            return no_update

    @dash_app.callback(
        Output("download-asia-table-csv", "data"),
        Input("export-asia-table-btn", 'n_clicks'),
        [State('asia-unit-filter', 'value'),
         State('asia-sector-filter', 'value'),
         State('asia-country-filter', 'value'),
         State('asia-sector-start-date', 'value'),
         State('asia-sector-end-date', 'value'),
         State('min-date', 'data'),
         State('max-date', 'data')],
        prevent_initial_call=True
    )
    def export_asia_table_data(n_clicks, unit, sector, country, start_date_str, end_date_str, min_date_store, max_date_store):
        if not n_clicks:
            return no_update

        try:
            # Convert input strings to datetime (timezone naive)
            if not start_date_str or not end_date_str:
                 if min_date_store:
                     start_date = pd.to_datetime(min_date_store).tz_localize(None)
                     end_date = pd.to_datetime(max_date_store).tz_localize(None)
                 else:
                     return no_update
            else:
                start_date = pd.to_datetime(start_date_str).tz_localize(None)
                end_date = pd.to_datetime(end_date_str).tz_localize(None)

            df = load_table_data(country)
            
            if df.empty:
                return no_update

            if unit:
                df = df[df['Unit'] == unit]
            
            if sector != '(All)':
                df = df[df['Sector'] == sector]
                
            # Ensure DataFrame dates are timezone-naive
            if 'Date_Obj' in df.columns:
                 df['Date_Obj'] = pd.to_datetime(df['Date_Obj'])
                 if df['Date_Obj'].dt.tz is not None:
                     df['Date_Obj'] = df['Date_Obj'].dt.tz_localize(None)
                
            if start_date and end_date:
                df = df[(df['Date_Obj'] >= start_date) & (df['Date_Obj'] <= end_date)]
            
            # Drop internal columns
            cols_to_drop = ['Date_Obj', 'Year', 'Month', 'Year of Date', 'Month of Date']
            df = df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors='ignore')
            
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"asia_gas_demand_table_{timestamp}.csv"
            
            return dcc.send_data_frame(df.to_csv, filename, index=False)


        except Exception as e:
            print(f"Error exporting table data: {e}")
            return no_update