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
FROM dev.glng_gas_demand tr
LEFT JOIN dev.dim_country dc
    ON tr.country_id = dc.dim_country_id
WHERE LOWER(dc.region) IN ('asia', 'oceania')
  AND tr.country IS NOT NULL
  AND TRIM(tr.country) <> ''
ORDER BY tr.country;
"""

QUERY_SECTORS = """
SELECT DISTINCT
    tr.sector
FROM dev.glng_gas_demand tr
LEFT JOIN dev.dim_country dc
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
FROM dev.glng_gas_demand gd
LEFT JOIN dev.dim_country dc
    ON gd.country_id = dc.dim_country_id
WHERE LOWER(dc.region) IN ('asia', 'oceania')
  AND gd.unit IN ('Mcm', 'GWh')
  AND gd.to_be_deleted = false
  AND gd.date >= DATE '2019-01-01'
  AND gd.date < DATE '2025-01-01'
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
FROM dev.glng_gas_demand gd
LEFT JOIN dev.dim_country dc
    ON gd.country_id = dc.dim_country_id
WHERE LOWER(dc.region) IN ('asia', 'oceania')
  AND gd.unit IN ('Mcm', 'GWh')
  AND gd.to_be_deleted = false
  AND gd.date >= DATE '2019-01-01'
  AND gd.date < DATE '2025-01-01'
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
    
    if df_chart.empty:
        # Fallback if DB empty
        unique_dates = []
        max_idx = 0
        date_marks = {}
        date_map_data = []
    else:
        unique_dates = sorted(df_chart['Date_Obj'].unique())
        max_idx = len(unique_dates) - 1 if unique_dates else 0
        date_map_data = [d.strftime('%-m/%-d/%Y') for d in unique_dates]
        
        # Only show Start and End Date labels
        date_marks = {
            0: {'label': '', 'style': {'display': 'none'}}, 
            max_idx: {'label': '', 'style': {'display': 'none'}}
        }

    # Initial Start/End indices
    start_idx = 0
    end_idx = max_idx

    start_date_label = date_map_data[0] if date_map_data else ""
    end_date_label = date_map_data[-1] if date_map_data else ""

    return html.Div([
        dcc.Download(id="download-asia-yearly-chart-csv"),
        dcc.Download(id="download-asia-yearly-table-csv"),
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
                        html.Button("Export to CSV", id="export-asia-yearly-chart-btn", n_clicks=0, style={
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
                            html.Button('-', id='asia-yearly-chart-toggle-year-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#add8e6', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Quarter of Date", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('+', id='asia-yearly-chart-toggle-quarter-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Month of Date", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('+', id='asia-yearly-chart-toggle-month-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Day of Year", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('+', id='asia-yearly-chart-toggle-day-btn', n_clicks=0, style={
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
                            html.Div(id='loading-trigger-yearly-chart', style={'display': 'none'}),
                            dcc.Graph(id='asia-gas-yearly-chart', config={'displayModeBar': False})
                        ],
                        id="loading-asia-yearly-chart",
                        type="circle"
                    )
                ], style={'backgroundColor': '#fff', 'padding': '10px', 'position': 'relative'}),

                # Table Container with Hierarchy Icons
                html.Div([
                    # Table Hierarchy Controls
                    html.Div([
                        html.Div([
                            html.Span("Year of Date", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('+', id='asia-yearly-table-toggle-year-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Quarter of Date", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('+', id='asia-yearly-table-toggle-quarter-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Month of Date", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('-', id='asia-yearly-table-toggle-month-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#add8e6', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Day of Year", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('+', id='asia-yearly-table-toggle-day-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center'})
                    # Removed extra closing bracket here
                    ,
                    
                    # Table Export Button
                    html.Div(dcc.Loading(
                        html.Button("Export to CSV", id="export-asia-yearly-table-btn", n_clicks=0, style={
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
                            html.Div(id='loading-trigger-yearly-table', style={'display': 'none'}),
                            html.Div(id='asia-gas-yearly-table-container')
                        ],
                        id="loading-asia-yearly-table",
                        type="circle"
                    )
                ], style={'marginTop': '20px', 'backgroundColor': '#fff', 'padding': '10px'}),
                
                # Stores for State
                dcc.Store(id='asia-yearly-table-highlight-state'), # From Clientside
                dcc.Store(id='chart-yearly-highlight-state', data=None), # Server side Highlight State
                dcc.Store(id='chart-yearly-time-level', data='YEARLY'), # Chart hierarchy state
                dcc.Store(id='table-yearly-time-level', data='MONTHLY'), # Table hierarchy state
                dcc.Store(id='store-asia-yearly-chart-data'), # Cache
                dcc.Store(id='store-asia-yearly-table-data'), # Cache
                
                # Hidden Trigger for X-Axis Click
                dcc.Input(id='axis-yearly-click-trigger', type='text', style={'display': 'none'}),
                
                html.Div(id='asia-yearly-table-dummy-output', style={'display': 'none'}),
                html.Div(id='axis-yearly-listener-output', style={'display': 'none'}) # Dedicated output
                
            ], style={'flex': '1', 'padding': '20px', 'overflowX': 'hidden', 'backgroundColor': '#fff'}),

            # Right Column: Filters Panel
            html.Div([
                html.Div([
                    # Date Range Filter
                    # Date Range Filter (Hidden as per user request for Yearly view)
                    html.Div([
                        dcc.RangeSlider(
                            id='asia-yearly-date-slider',
                            min=0,
                            max=max_idx,
                            value=[start_idx, end_idx],
                            marks=date_marks,
                            step=1,
                            updatemode='drag'
                        ),
                        html.Div(id='asia-yearly-date-label-start', children=start_date_label),
                        html.Div(id='asia-yearly-date-label-end', children=end_date_label)
                    ], style={'display': 'none'}),
                    
                    # Store unique dates as JSON and MAX Index for callback math
                    dcc.Store(id='asia-yearly-date-map', data=date_map_data),
                    dcc.Store(id='asia-yearly-date-max', data=max_idx),

                    # Unit Filter
                    html.Div([
                        html.Label("Unit", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '12px', 'marginBottom': '8px', 'display': 'block'}),
                        dcc.RadioItems(
                            id='asia-yearly-unit-filter',
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
                            id='asia-yearly-sector-filter',
                            options=[{'label': s, 'value': s} for s in all_sectors],
                            value='(All)',
                            labelStyle={'display': 'block', 'marginBottom': '4px', 'fontSize': '12px', 'color': '#333'}
                        )
                    ], style={'marginBottom': '20px', 'borderBottom': '1px solid #eee', 'paddingBottom': '10px'}),

                    # Country Filter
                    html.Div([
                        html.Label("Country", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '12px', 'marginBottom': '8px', 'display': 'block'}),
                        dcc.RadioItems(
                            id='asia-yearly-country-filter',
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
        
    ], id='gas-asia-yearly-container', style={'backgroundColor': '#ffffff', 'fontFamily': 'Arial, sans-serif'})


def build_chart(df, sector_filter, unit, country_label='(All)', time_level='MONTHLY', highlight_state=None):
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
        custom_data = []
        
        for d in unique_dates:
            val = sdf_grouped.get(d, 0)
            y_vals.append(val)
            
            # Get detailed date info for customdata
            # d is a numpy datetime64 or pandas Timestamp
            d_ts = pd.Timestamp(d)
            month_name = d_ts.strftime('%B')
            year_val = d_ts.year
            quarter_val = f"Q{d_ts.quarter}"
            day_val = d_ts.day
            
            # Get the time label used on X axis
            row_for_date = df_agg[df_agg['Date_Obj'] == d]
            time_label = row_for_date['Time_Label'].iloc[0] if not row_for_date.empty else ""
            
            # Prepare customdata: [Month, Quarter, Year, Day, Time_Label]
            custom_data.append([month_name, quarter_val, year_val, day_val, time_label])
            
            # Highlight Logic
            date_str = time_label
            if date_str:
                date_str = str(date_str).replace('\xa0', ' ').strip()
            
            op = 1.0 # Default full opacity
            lw = 0
            lc = 'rgba(0,0,0,0)' # Transparent
            
            if highlight_state:
                op = 0.3 # Default dim if highlighting active
                
                h_date = str(highlight_state.get('date')).replace('\xa0', ' ').strip() if highlight_state and highlight_state.get('date') else ""
                h_sector = str(highlight_state.get('sector')).replace('\xa0', ' ').strip() if highlight_state and highlight_state.get('sector') else ""

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

        # Text Color Logic based on Sector/Background Color
        text_color = 'black'
        if sector in ['Power', 'Household']:
            text_color = 'white'

        # Build Hover Template based on time_level
        hover_parts = []
        if time_level == 'DAILY':
            hover_parts.append("<span style='color: #777'>Day of Date:</span> <span style='color: black'>%{customdata[3]}</span>")
        if time_level in ['MONTHLY', 'DAILY']:
            hover_parts.append("<span style='color: #777'>Month of Date:</span> <span style='color: black'>%{customdata[0]}</span>")
        if time_level == 'QUARTERLY':
            hover_parts.append("<span style='color: #777'>Quarter of Date:</span> <span style='color: black'>%{customdata[1]}</span>")
        
        # Add Country if possible (we'll use a placeholder or better, fetch from state if we can)
        # For now, we'll use a generic "Country" label that will be updated by the caller if needed
        hover_parts.append("<span style='color: #777'>Country:</span> <span style='color: black'>%{customdata[5]}</span>")
        
        hover_parts.append("<span style='color: #777'>Sector:</span> <span style='color: black'>%{data.name}</span>")
        
        if time_level in ['YEARLY', 'QUARTERLY', 'MONTHLY', 'DAILY']:
            hover_parts.append("<span style='color: #777'>Year of Date:</span> <span style='color: black'>%{customdata[2]}</span>")
            
        hover_parts.append("<span style='color: #777'>Value:</span> <span style='color: black'>%{y:" + val_fmt + "}</span>")
        hover_parts.append(f"<span style='color: #777'>Unit:</span> <span style='color: black'>{unit}</span>")
        
        full_hover_template = "<br>".join(hover_parts) + "<extra></extra>"
            
        fig.add_trace(go.Bar(
            name=sector,
            x=x_axis_labels,
            y=y_vals,
            text=y_vals,
            texttemplate='%{text:.1f}' if unit == 'Billion Cubic Meter' else '%{text:.0f}',
            textposition='inside',
            textfont=dict(
                size=11,
                color=text_color
            ),
            marker=dict(
                color=COLORS.get(sector, '#ccc'),
                opacity=opacities,
                line=dict(
                    width=line_widths,
                    color=line_colors
                )
            ),
            customdata=[cd + [country_label] for cd in custom_data], # Added Country label
            hovertemplate=full_hover_template,
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial"
            )
        ))

    # Add Total Labels on top of the stack
    totals = df_agg.groupby('Date_Obj')['Value'].sum()
    total_y = []
    total_text_labels = []
    
    label_fmt = "{:,.1f}"
    if unit != 'Billion Cubic Meter':
         label_fmt = "{:,.0f}"

    for d in unique_dates:
        val = totals.get(d, 0)
        total_y.append(val)
        total_text_labels.append(label_fmt.format(val))

    fig.add_trace(go.Scatter(
        x=x_axis_labels,
        y=total_y,
        text=total_text_labels,
        mode='text',
        textposition='top center',
        textfont=dict(
            size=12,
            color='black',
            family="Arial"
        ),
        showlegend=False,
        hoverinfo='skip'
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
            id='asia-gas-yearly-demand-table',
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
                    'backgroundColor': '#f2f2f2'
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
            id='asia-gas-yearly-demand-table',
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
                    'backgroundColor': '#f2f2f2'
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
                # Determine Year and Month from col_id
                if '_Total' in col_id:
                    y_val = col_id.split('_')[0]
                    # For Total, maybe show "Year of Date" only? 
                    # But requirement says "applicable date hierarchy"
                    tooltip_text = f"**Country:** {country_name}  \n**Sector:** {sector_name}  \n**Year of Date:** {y_val}  \n**Value:** {val_fmt_func(val)}  \n**Unit:** {unit}"
                else:
                    y_val, m_val = col_id.split('_')
                    tooltip_text = f"**Month of Date:** {m_val}  \n**Country:** {country_name}  \n**Sector:** {sector_name}  \n**Year of Date:** {y_val}  \n**Value:** {val_fmt_func(val)}  \n**Unit:** {unit}"
                
                row_tooltip[col_id] = {'value': tooltip_text, 'type': 'markdown'}
        tooltip_data.append(row_tooltip)

    return html.Div([
        dash_table.DataTable(
            id='asia-gas-yearly-demand-table',
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
                    'backgroundColor': '#f2f2f2'
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
                    parts = col_id.split('_') # y, m, 1
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
            id='asia-gas-yearly-demand-table',
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
                    'backgroundColor': '#f2f2f2'
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
        [Output('chart-yearly-time-level', 'data'),
         Output('asia-yearly-chart-toggle-year-btn', 'children'),
         Output('asia-yearly-chart-toggle-quarter-btn', 'children'),
         Output('asia-yearly-chart-toggle-month-btn', 'children'),
         Output('asia-yearly-chart-toggle-day-btn', 'children')],
        [Input('asia-yearly-chart-toggle-year-btn', 'n_clicks'),
         Input('asia-yearly-chart-toggle-quarter-btn', 'n_clicks'),
         Input('asia-yearly-chart-toggle-month-btn', 'n_clicks'),
         Input('asia-yearly-chart-toggle-day-btn', 'n_clicks')],
        [State('chart-yearly-time-level', 'data')]
    )
    def chart_hierarchy_handler(y_c, q_c, m_c, d_c, current_level):
        if not ctx.triggered:
            cl = current_level or 'YEARLY'
            return (cl, 
                    '-' if cl == 'YEARLY' else '+',
                    '-' if cl == 'QUARTERLY' else '+',
                    '-' if cl == 'MONTHLY' else '+',
                    '-' if cl == 'DAILY' else '+')

        btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        new_level = 'YEARLY'
        if '-year-btn' in btn_id:
            new_level = 'YEARLY'
        elif '-quarter-btn' in btn_id:
            new_level = 'QUARTERLY'
        elif '-month-btn' in btn_id:
            new_level = 'MONTHLY'
        elif '-day-btn' in btn_id:
            new_level = 'DAILY'
            
        return (new_level,
                '-' if new_level == 'YEARLY' else '+',
                '-' if new_level == 'QUARTERLY' else '+',
                '-' if new_level == 'MONTHLY' else '+',
                '-' if new_level == 'DAILY' else '+')

    # Table Hierarchy Callbacks
    @dash_app.callback(
        [Output('table-yearly-time-level', 'data'),
         Output('asia-yearly-table-toggle-year-btn', 'children'),
         Output('asia-yearly-table-toggle-quarter-btn', 'children'),
         Output('asia-yearly-table-toggle-month-btn', 'children'),
         Output('asia-yearly-table-toggle-day-btn', 'children')],
        [Input('asia-yearly-table-toggle-year-btn', 'n_clicks'),
         Input('asia-yearly-table-toggle-quarter-btn', 'n_clicks'),
         Input('asia-yearly-table-toggle-month-btn', 'n_clicks'),
         Input('asia-yearly-table-toggle-day-btn', 'n_clicks')],
        [State('table-yearly-time-level', 'data')]
    )
    def table_hierarchy_handler(y_c, q_c, m_c, d_c, current_level):
        if not ctx.triggered:
            cl = current_level or 'MONTHLY'
            return (cl, 
                    '-' if cl == 'YEARLY' else '+',
                    '-' if cl == 'QUARTERLY' else '+',
                    '-' if cl == 'MONTHLY' else '+',
                    '-' if cl == 'DAILY' else '+')

        btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        new_level = 'MONTHLY'  # Changed default to MONTHLY
        if '-year-btn' in btn_id:
            new_level = 'YEARLY'
        elif '-quarter-btn' in btn_id:
            new_level = 'QUARTERLY'
        elif '-month-btn' in btn_id:
            new_level = 'MONTHLY'
        elif '-day-btn' in btn_id:
            new_level = 'DAILY'
            
        return (new_level,
                '-' if new_level == 'YEARLY' else '+',
                '-' if new_level == 'QUARTERLY' else '+',
                '-' if new_level == 'MONTHLY' else '+',
                '-' if new_level == 'DAILY' else '+')

    # 0. Data Fetching Callback
    @dash_app.callback(
        [Output('store-asia-yearly-chart-data', 'data'),
         Output('store-asia-yearly-table-data', 'data'),
         Output('loading-trigger-yearly-chart', 'children'),
         Output('loading-trigger-yearly-table', 'children')],
        Input('asia-yearly-country-filter', 'value')
    )
    def fetch_asia_data(country):
        # This callback MUST run to populate stores.
        df_chart = load_chart_data(country)
        df_table = load_table_data(country)
        
        # We return records. Date objects will be strings.
        # df_chart has Date_Obj column.
        return df_chart.to_dict('records'), df_table.to_dict('records'), "", ""

    # 1. Main Update Callback
    
    @dash_app.callback(
        [Output('asia-gas-yearly-chart', 'figure'),
         Output('chart-yearly-highlight-state', 'data'),
         Output('asia-gas-yearly-chart', 'clickData')],
        [Input('asia-yearly-unit-filter', 'value'),
         Input('asia-yearly-sector-filter', 'value'),
         Input('store-asia-yearly-chart-data', 'data'),
         Input('asia-yearly-date-slider', 'value'),
         Input('asia-gas-yearly-chart', 'clickData'),
         Input('axis-yearly-click-trigger', 'value'),
         Input('chart-yearly-time-level', 'data'),
         Input('asia-yearly-country-filter', 'value')],
        [State('asia-yearly-date-map', 'data'),
         State('chart-yearly-highlight-state', 'data')]
    )
    def update_chart(unit, sector, chart_data, date_range_idx, clickData, axis_click_raw, 
                    chart_time_level, country, date_map, current_highlight):
        try:
            # 0. Determine Trigger
            triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
            
            # 1. Resolve Highlight State Change
            highlight_state = current_highlight # Default keep current
            
            # If Filters or Time Levels changed, clear highlight
            if triggered_id in ['asia-yearly-unit-filter', 'asia-yearly-sector-filter', 'store-asia-yearly-chart-data', 'asia-yearly-date-slider', 
                               'chart-yearly-time-level']:
                highlight_state = None
                
            # If Chart Bar Clicked -> Toggle Bar Selection
            elif triggered_id == 'asia-gas-yearly-chart':
                if not clickData:
                    return no_update, no_update, no_update

                if clickData and 'points' in clickData:
                    point = clickData['points'][0]
                    clicked_date = point.get('x')
                    
                    # Try to get sector from data.name, fallback to curveNumber
                    clicked_sector = point.get('data', {}).get('name')
                    if not clicked_sector:
                        try:
                            curve_num = point.get('curveNumber')
                            sectors_to_plot = SECTOR_ORDER if sector == '(All)' else [sector]
                            if curve_num is not None and 0 <= curve_num < len(sectors_to_plot):
                                clicked_sector = sectors_to_plot[curve_num]
                        except:
                            pass
                    
                    # Robust String Cleaning & Lowercase for matching
                    if clicked_date:
                        clicked_date = str(clicked_date).replace('\xa0', ' ').strip()
                    if clicked_sector:
                        clicked_sector = str(clicked_sector).replace('\xa0', ' ').strip()
                    
                    if clicked_date and clicked_sector:
                        # Prepare for comparison
                        c_date_lower = clicked_date.lower()
                        c_sector_lower = clicked_sector.lower()
                        
                        current_date = str(highlight_state.get('date')).replace('\xa0', ' ').strip() if highlight_state and highlight_state.get('date') else ""
                        current_sector = str(highlight_state.get('sector')).replace('\xa0', ' ').strip() if highlight_state and highlight_state.get('sector') else ""
                        
                        # Toggle Logic (Case Insensitive)
                        if (highlight_state and 
                            highlight_state.get('type') == 'bar' and 
                            current_date.lower() == c_date_lower and 
                            current_sector.lower() == c_sector_lower):
                            highlight_state = None
                        else:
                            highlight_state = {
                                'type': 'bar',
                                'date': clicked_date,   # Store original case for display/matching if needed, but comparisons should remain robust
                                'sector': clicked_sector
                            }
            
            # If Axis Clicked (Simulated) -> Month Selection
            elif triggered_id == 'axis-yearly-click-trigger':
                if axis_click_raw:
                    # Parse "Month YYYY|TIMESTAMP" -> "Month YYYY"
                    axis_click_date = axis_click_raw.split('|')[0].replace('\xa0', ' ').strip()
                    
                    current_date = str(highlight_state.get('date')).replace('\xa0', ' ').strip() if highlight_state and highlight_state.get('date') else ""
                    
                    if (highlight_state and 
                        highlight_state.get('type') == 'month' and 
                        current_date.lower() == axis_click_date.lower()):
                        highlight_state = None
                    else:
                        highlight_state = {
                            'type': 'month',
                            'date': axis_click_date,
                            'sector': None
                        }
            
            # 2. Resolve Data Range
            start_date = None
            end_date = None
            if date_map and date_range_idx:
                try:
                    start_date_str = date_map[date_range_idx[0]]
                    end_date_str = date_map[date_range_idx[1]]
                    start_date = pd.to_datetime(start_date_str)
                    end_date = pd.to_datetime(end_date_str)
                except:
                    pass
            
            # 3. LOAD from Store
            if chart_data is None:
                return no_update, no_update, None
                
            df_chart = pd.DataFrame(chart_data)
            
            # Post-processing: Restore Dates
            if not df_chart.empty and 'Date_Obj' in df_chart.columns:
                df_chart['Date_Obj'] = pd.to_datetime(df_chart['Date_Obj'])
            
            # 4. FILTER
            if not df_chart.empty:
                df_chart = df_chart[df_chart['Unit'] == unit]

            if sector != '(All)':
                if not df_chart.empty:
                    df_chart = df_chart[df_chart['Sector'] == sector]

            if start_date and end_date:
                if not df_chart.empty:
                    # In yearly dashboard, the slider points are Jan 1st. 
                    # We extend the end_date to the end of that year to be inclusive of all data within that year.
                    adj_end = end_date + pd.offsets.YearEnd(0)
                    df_chart = df_chart[(df_chart['Date_Obj'] >= start_date) & (df_chart['Date_Obj'] <= adj_end)]
                    
            # 5. Build Chart
            if df_chart.empty:
                fig = go.Figure()
            else:
                fig = build_chart(df_chart, sector, unit, country, chart_time_level or 'MONTHLY', highlight_state)
            
            return fig, highlight_state, None

        except Exception as e:
            print(f"Error in update_chart: {e}")
            fig = go.Figure()
            fig.update_layout(title=f"Error: {str(e)}")
            return fig, no_update, None

    @dash_app.callback(
        Output('asia-gas-yearly-table-container', 'children'),
        [Input('asia-yearly-unit-filter', 'value'),
         Input('asia-yearly-sector-filter', 'value'),
         Input('store-asia-yearly-table-data', 'data'),
         Input('asia-yearly-date-slider', 'value'),
         Input('table-yearly-time-level', 'data')],
        [State('asia-yearly-date-map', 'data')]
    )
    def update_table(unit, sector, table_data, date_range_idx, table_time_level, date_map):
        try:
            # 1. Resolve Data Range
            start_date = None
            end_date = None
            if date_map and date_range_idx:
                try:
                    start_date_str = date_map[date_range_idx[0]]
                    end_date_str = date_map[date_range_idx[1]]
                    start_date = pd.to_datetime(start_date_str)
                    end_date = pd.to_datetime(end_date_str)
                except:
                    pass
            
            # 2. LOAD from Store
            if table_data is None:
                return no_update
                
            df_table = pd.DataFrame(table_data)
            
            # Post-processing: Restore Dates
            if not df_table.empty and 'Date_Obj' in df_table.columns:
                df_table['Date_Obj'] = pd.to_datetime(df_table['Date_Obj'])

            # 3. FILTER
            if not df_table.empty:
                df_table = df_table[df_table['Unit'] == unit]

            if sector != '(All)':
                if not df_table.empty:
                    df_table = df_table[df_table['Sector'] == sector]

            if start_date and end_date:
                if not df_table.empty:
                    # In yearly dashboard, the slider points are Jan 1st. 
                    # We extend the end_date to the end of that year to be inclusive of all monthly data within that year.
                    adj_end = end_date + pd.offsets.YearEnd(0)
                    df_table = df_table[(df_table['Date_Obj'] >= start_date) & (df_table['Date_Obj'] <= adj_end)]
                    
            # 4. Build Table
            if df_table.empty:
                table_comp = html.Div("Data error or empty for selection")
            else:
                table_comp = build_table(df_table, sector, unit, table_time_level or 'MONTHLY')
                
            return table_comp

        except Exception as e:
            print(f"Error in update_table: {e}")
            return html.Div(f"Error: {str(e)}")

    # 2. Clientside Callback for tooltips text transformation on Slider (No Op, just for output)
    # 2. Clientside Callback for updating Slider Date Labels
    dash_app.clientside_callback(
        """
        function(value, date_map) {
            if (!date_map || !value) return ["", ""];
            return [date_map[value[0]], date_map[value[1]]];
        }
        """,
        [Output('asia-yearly-date-label-start', 'children'),
         Output('asia-yearly-date-label-end', 'children')],
        Input('asia-yearly-date-slider', 'value'),
        State('asia-yearly-date-map', 'data')
    )

    # 3. Clientside Callback for Table Highlighting (Reused exactly)
    dash_app.clientside_callback(
        """
        function(n_data, columns, current_state) {
            try {
                const tableId = 'asia-gas-yearly-demand-table';
                
                let style = document.getElementById('asia-gas-yearly-styles');
                if (!style) {
                    style = document.createElement('style');
                    style.id = 'asia-gas-yearly-styles';
                    document.head.appendChild(style);
                }
                
                style.innerHTML = `
                    .asia-yearly-col-selected { background-color: #cfe8ef !important; }
                    .asia-yearly-row-selected { background-color: #cfe8ef !important; }
                    .asia-yearly-dimmed { opacity: 0.3 !important; }
                    
                    .asia-yearly-col-selection-active td[data-dash-column="Country"], 
                    .asia-yearly-col-selection-active td[data-dash-column="Sector"] { 
                        opacity: 1 !important; 
                        background-color: transparent !important; 
                    }
                    
                    .asia-yearly-row-selection-active tr.asia-yearly-row-highlighted td {
                        opacity: 1 !important;
                        background-color: #cfe8ef !important;
                        color: black !important;
                    }

                    .asia-yearly-row-selection-active tr:not(.asia-yearly-row-trip-wire) td {
                        opacity: 0.3 !important;
                    }

                    th.asia-yearly-col-selected { background-color: #cfe8ef !important; }
                `;

                if (!window.asiaGasYearlyState) {
                    window.asiaGasYearlyState = { 
                        selectedColumnId: null,
                        selectedRowIndices: null 
                    };
                }

                function clearAll(spreadsheet) {
                    spreadsheet.classList.remove('asia-yearly-col-selection-active');
                    spreadsheet.classList.remove('asia-yearly-row-selection-active');
                    
                    const selected = spreadsheet.querySelectorAll('.asia-yearly-col-selected, .asia-yearly-dimmed, .asia-yearly-row-highlighted, .asia-yearly-row-trip-wire');
                    selected.forEach(el => {
                        el.classList.remove('asia-yearly-col-selected');
                        el.classList.remove('asia-yearly-dimmed');
                        el.classList.remove('asia-yearly-row-highlighted');
                        el.classList.remove('asia-yearly-row-trip-wire');
                    });
                }
                
                function applyState(spreadsheet, n_data) {
                    clearAll(spreadsheet);

                    if (window.asiaGasYearlyState.selectedColumnId) {
                        const targetIds = window.asiaGasYearlyState.selectedColumnId.split(',');
                        if (targetIds.length === 0) return;

                        spreadsheet.classList.add('asia-yearly-col-selection-active');

                        targetIds.forEach(id => {
                            const ths = spreadsheet.querySelectorAll(`th[data-dash-column="${id}"]`);
                            ths.forEach(th => th.classList.add('asia-yearly-col-selected'));
                        });

                        const allCells = spreadsheet.querySelectorAll('td[data-dash-column]');
                        allCells.forEach(cell => {
                            const cId = cell.getAttribute('data-dash-column');
                            if (cId === 'Country' || cId === 'Sector') return;

                            if (targetIds.includes(cId)) {
                                cell.classList.add('asia-yearly-col-selected');
                            } else {
                                cell.classList.add('asia-yearly-dimmed');
                            }
                        });
                        return;
                    }

                    if (window.asiaGasYearlyState.selectedRowIndices) {
                        const [start, end] = window.asiaGasYearlyState.selectedRowIndices.split('_').map(Number);
                        
                        spreadsheet.classList.add('asia-yearly-row-selection-active');
                        
                        const tbodies = spreadsheet.querySelectorAll('tbody');
                        
                        tbodies.forEach(tbody => {
                            const rows = tbody.querySelectorAll('tr');
                            rows.forEach((row, idx) => {
                                if (idx >= start && idx <= end) {
                                    row.classList.add('asia-yearly-row-highlighted');
                                    row.classList.add('asia-yearly-row-trip-wire');
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
                    
                    if (spreadsheet && (window.asiaGasYearlyState.selectedColumnId || window.asiaGasYearlyState.selectedRowIndices)) {
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
                            
                            if (window.asiaGasYearlyState.selectedColumnId === selectionKey) {
                                window.asiaGasYearlyState.selectedColumnId = null;
                            } else {
                                window.asiaGasYearlyState.selectedColumnId = selectionKey;
                                window.asiaGasYearlyState.selectedRowIndices = null; 
                            }
                            applyState(spreadsheet, n_data);
                            return;
                        }
                        
                        const cell = e.target.closest('td[data-dash-column]');
                        if (cell) {
                             const row = cell.closest('tr');
                             const tbody = row.closest('tbody');
                             const rows = Array.from(tbody.querySelectorAll('tr'));
                             const idx = rows.indexOf(row);
                             
                             const start = idx; 
                             const end = idx; 
                             
                             const newKey = `${start}_${end}`;
                             
                             if (window.asiaGasYearlyState.selectedRowIndices === newKey) {
                                  window.asiaGasYearlyState.selectedRowIndices = null;
                             } else {
                                  window.asiaGasYearlyState.selectedRowIndices = newKey;
                                  window.asiaGasYearlyState.selectedColumnId = null;
                             }
                             applyState(spreadsheet, n_data);
                        }
                    });
                }
                
                // Clear state when table structure changes significantly
                if (window.asiaGasYearlyState && columns) {
                    const currentCols = columns.map(c => c.id).join(',');
                    if (window.asiaGasYearlyState.lastColumnStructure !== currentCols) {
                        window.asiaGasYearlyState.selectedColumnId = null;
                        window.asiaGasYearlyState.selectedRowIndices = null;
                        window.asiaGasYearlyState.lastColumnStructure = currentCols;
                    }
                }
                
                setTimeout(setupTable, 500); 
                return window.asiaGasYearlyState.selectedColumnId || ""; 

            } catch(e) { 
                console.error('Table highlighting error:', e); 
                return ""; 
            }
        }
        """,
        Output('asia-yearly-table-highlight-state', 'data'),
        Input('asia-gas-yearly-demand-table', 'data'),
        State('asia-gas-yearly-demand-table', 'columns'),
        State('asia-yearly-table-highlight-state', 'data')
    )

    # 4. Clientside Callback to attach X-Axis Click Listeners
    # Attaches listener to Plotly Axis Labels and updates 'axis-yearly-click-trigger'
    dash_app.clientside_callback(
        """
        function(fig_data) {
            // Wait for plot to render
            setTimeout(function() {
                try {
                    const graph = document.getElementById('asia-gas-yearly-chart');
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
                                
                                const input = document.getElementById('axis-yearly-click-trigger');
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
        Output('axis-yearly-listener-output', 'children'), # Dedicated output
        Input('asia-gas-yearly-chart', 'figure')
    )

    # 5. Export Callbacks
    @dash_app.callback(
        Output("download-asia-yearly-chart-csv", "data"),
        Input("export-asia-yearly-chart-btn", 'n_clicks'),
        [State('asia-yearly-unit-filter', 'value'),
         State('asia-yearly-sector-filter', 'value'),
         State('asia-yearly-country-filter', 'value'),
         State('asia-yearly-date-slider', 'value'),
         State('asia-yearly-date-map', 'data')],
        prevent_initial_call=True
    )
    def export_asia_chart_data(n_clicks, unit, sector, country, date_range_idx, date_map):
        if not n_clicks:
            return no_update

        try:
            start_date = None
            end_date = None
            if date_range_idx and date_map:
                try:
                    start_date_str = date_map[date_range_idx[0]]
                    end_date_str = date_map[date_range_idx[1]]
                    start_date = pd.to_datetime(start_date_str)
                    end_date = pd.to_datetime(end_date_str)
                except:
                    pass

            # Load data using the country filter
            df = load_chart_data(country)
            
            if df.empty:
                return no_update

            # Apply filters manually to match dashboard view
            if unit:
                df = df[df['Unit'] == unit]
            
            if sector != '(All)':
                df = df[df['Sector'] == sector]
                
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
        Output("download-asia-yearly-table-csv", "data"),
        Input("export-asia-yearly-table-btn", 'n_clicks'),
        [State('asia-yearly-unit-filter', 'value'),
         State('asia-yearly-sector-filter', 'value'),
         State('asia-yearly-country-filter', 'value'),
         State('asia-yearly-date-slider', 'value'),
         State('asia-yearly-date-map', 'data')],
        prevent_initial_call=True
    )
    def export_asia_table_data(n_clicks, unit, sector, country, date_range_idx, date_map):
        if not n_clicks:
            return no_update

        try:
            start_date = None
            end_date = None
            if date_range_idx and date_map:
                try:
                    start_date_str = date_map[date_range_idx[0]]
                    end_date_str = date_map[date_range_idx[1]]
                    start_date = pd.to_datetime(start_date_str)
                    end_date = pd.to_datetime(end_date_str)
                except:
                    pass

            df = load_table_data(country)
            
            if df.empty:
                return no_update

            if unit:
                df = df[df['Unit'] == unit]
            
            if sector != '(All)':
                df = df[df['Sector'] == sector]
                
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