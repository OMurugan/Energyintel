import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, dash_table, State, ctx, ALL, no_update, callback
import os
from datetime import datetime
from sqlalchemy import create_engine, text
import time
import numpy as np
import hashlib

MONTH_ORDER = [
    'January', 'February', 'March', 'April', 'May', 'June', 
    'July', 'August', 'September', 'October', 'November', 'December'
]

EI_DARK_BLUE = "#1b365d"

def generate_timeline_data(years, mode='MONTHLY'):
    """
    Generate timeline mapping, labels, and separators for a set of years based on aggregation mode.
    Modes: 'MONTHLY', 'QUARTERLY', 'YEARLY', 'DATE'
    """
    timeline = []
    year_annotations = []
    month_separators = []
    year_separators = []
    year_centers = [] 
    
    current_global_x = 0
    num_years = len(years)
    mode = (mode or 'MONTHLY').upper()

    # If mode is DATE, we technically want the same 12-slot structure as MONTHLY,
    # but with different labeling (short_label='1' for the tick, but we still need the month name for the header).
    # The chart callbacks will handle the visual distinction (tick vs annotation).
    # So we can merge DATE logic into the standard loop but setting a flag.
    
    active_mode = mode
    is_date_mode = False
    
    if mode == 'DATE':
        active_mode = 'MONTHLY'
        is_date_mode = True
        
    if True: # Indentation wrapper to match previous structure
        if active_mode == 'MONTHLY':
            slots_per_year = 12
            slot_width = 1.0
            sub_labels = MONTH_ORDER
        elif active_mode == 'QUARTERLY':
            slots_per_year = 4
            slot_width = 1.0
            sub_labels = ['Q1', 'Q2', 'Q3', 'Q4']
        elif active_mode == 'YEARLY':
            slots_per_year = 1
            slot_width = 1.0 
            sub_labels = [''] 
        else: # Fallback to Monthly
            slots_per_year = 12
            slot_width = 1.0
            sub_labels = MONTH_ORDER
            active_mode = 'MONTHLY'
            
        for y_idx, y in enumerate(years):
            year_width = slots_per_year * slot_width
            year_center = current_global_x + (year_width / 2)
            year_centers.append({'year': y, 'x': year_center, 'width': year_width})
            
            year_annotations.append(dict(
                 x=year_center, y=0.5, xref="x", yref="y2",
                 text=f"<b>{y}</b>", showarrow=False, font=dict(size=14, color="black"),
                 xanchor="center", yanchor="middle"
            ))
            
            for s_idx, label in enumerate(sub_labels):
                final_label = label
                if active_mode == 'MONTHLY':
                    m_name = label
                    if num_years == 1:
                        short_label = m_name
                    elif num_years == 2:
                        two_year_mapping = {"September": "Septem..", "November": "Novem..", "December": "Decem.."}
                        short_label = two_year_mapping.get(m_name, m_name)
                    elif num_years <= 6:
                         mapping = {
                            "January": "Ja..", "February": "Fe..", "March": "Ma..",
                            "April": "Ap..", "May": "Ma..", "June": "Ju..",
                            "July": "Ju..", "August": "Au..", "September": "Se..",
                            "October": "Oc..", "November": "No..", "December": "De.."
                        }
                         short_label = mapping.get(m_name, m_name[:3] + "..")
                    else:
                        ultra_mapping = {
                            "January": "J", "February": "F", "March": "M",
                            "April": "A", "May": "M", "June": "J",
                            "July": "J", "August": "A", "September": "S",
                            "October": "O", "November": "N", "December": "D"
                        }
                        short_label = ultra_mapping.get(m_name, m_name[0])
                    final_label = short_label
                
                item = {
                    'year': y,
                    'x_pos': current_global_x + (slot_width / 2),
                    'short_label': final_label, # Used for Month Header (y3)
                    'full_label': label 
                }
                
                # Tick Label Logic: If DATE mode, tick is "1"
                if is_date_mode:
                    item['tick_label'] = '1'
                else:
                    item['tick_label'] = ''

                if active_mode == 'MONTHLY':
                    item['month_name'] = label
                    item['month_idx'] = s_idx
                elif active_mode == 'QUARTERLY':
                    item['quarter'] = label
                
                timeline.append(item)
                
                # Separators
                line_x = current_global_x + slot_width
                
                if s_idx < len(sub_labels) - 1:
                    month_separators.append(dict(
                        type="line", x0=line_x, x1=line_x, y0=0, y1=0.88, 
                        xref="x", yref="paper", line=dict(color="#999999", width=1),
                        layer='below'
                    ))
                
                current_global_x += slot_width

            # Year Separator
            if y_idx < len(years) - 1:
                sep_x = current_global_x
                y_sep = dict(
                    type="line", x0=sep_x, x1=sep_x, y0=0, y1=1,
                    xref="x", yref="paper", line=dict(color="#000000", width=1),
                    layer='below'
                )
                year_separators.append(y_sep)
                month_separators.append(y_sep) 
                
                current_global_x += (0.5 if active_mode == 'MONTHLY' else 0.25)
    
    df = pd.DataFrame(timeline)
    return df, year_annotations, month_separators, year_separators, num_years, year_centers

# Constants
LNG_COLOR = '#1f77b4'  # Blue
PIPELINE_COLOR = '#ff7f0e'  # Orange
TITLE_COLOR = '#fe5000'

# Standard Tableau-like color palette for Gas Origins
COLOR_PALETTE = px.colors.qualitative.T10 + px.colors.qualitative.Alphabet

# Explicit color mapping for key Gas Origins to match Image 1
GAS_ORIGIN_COLORS = {
    'Algeria': '#7681c6',
    'Austria': '#9ecde4',
    'Azerbaijan': '#bfd391',
    'Belgium': '#7882c4',
    'Bulgaria': '#565656',
    'Croatia': '#a3952d',
    'Czech Republic': '#efc85e',
    'Denmark': '#428d8f',
    'Finland': '#88b5aa',
    'France': '#df5858',
    'Germany': '#4c4c4c',
    'Greece': '#726863',
    'Hungary': '#b5a9a1',
    'Ireland': '#d07093',
    'Italy': '#f8bcd1',
    'Joint Baltic Zone EE/LV': '#9e6c93',
    'Libya': '#9a9a9a',
    'Lithuania': '#98715b',
    'LNG': '#006699',
    'Luxembourg': '#e4af95',
    'Moldova': '#4b71aa',
    'Morocco': '#9ecce4',
    'Netherlands': '#f3841a',
    'Norway': '#263e6a',
    'Poland': '#569f4d',
    'Portugal': '#86d079',
    'Romania': '#b4972b',
    'Russia': '#c74d28',
    'Serbia': '#469692',
    'Slovakia': '#80bab4',
    'Slovenia': '#e9595a',
    'Spain': '#b7afa9',
    'Switzerland': '#444444',
    'United Kingdom': '#d17094',
}

def get_consistent_color_for_origin(origin):
    """Get a consistent color for a gas origin, ensuring the same origin always gets the same color"""
    # First check if we have a predefined color
    if origin in GAS_ORIGIN_COLORS:
        return GAS_ORIGIN_COLORS[origin]
    
    # For origins not in the predefined mapping, use a hash-based approach
    # to ensure the same origin always gets the same color regardless of order
    hash_value = int(hashlib.md5(origin.encode()).hexdigest(), 16)
    color_index = hash_value % len(COLOR_PALETTE)
    return COLOR_PALETTE[color_index]

def hex_to_rgba(h, a):
    """Convert hex color to rgba string."""
    if not h: return f'rgba(0,0,0,{a})'
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join([c*2 for c in h])
    rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({rgb[0]},{rgb[1]},{rgb[2]},{a})'

# Simple in-memory cache for data queries to prevent redundant DB hits during highlighting
_DATA_CACHE = {}

def load_data(query, params=None):
    """Execute query and return DataFrame with basic caching"""
    # Create a hashable key from query and params
    param_key = tuple(sorted(params.items())) if params else ()
    cache_key = hashlib.md5(f"{query}{param_key}".encode()).hexdigest()
    
    if cache_key in _DATA_CACHE:
        # Check if cache is still fresh (e.g., within last 5 minutes)
        cached_val, timestamp = _DATA_CACHE[cache_key]
        if (time.time() - timestamp) < 300: # 5 minutes
            return cached_val.copy()

    try:
        from core.data_helpers import execute_query
        rows = execute_query(query, params)
        df = pd.DataFrame(rows) if rows else pd.DataFrame()
        
        # Store in cache
        _DATA_CACHE[cache_key] = (df, time.time())
        return df.copy()
    except Exception as e:
        print(f"Database query error: {e}")
        return pd.DataFrame()

def create_layout():
    """Create the European Gas Imports Mix layout"""
    # Initial data for filters
    country_query = """
    SELECT DISTINCT tr.target_country
    FROM european_gas_trade tr
    WHERE tr.target_country IS NOT NULL AND TRIM(tr.target_country) <> ''
    ORDER BY tr.target_country;
    """
    countries_df = load_data(country_query)
    countries = countries_df['target_country'].tolist() if not countries_df.empty else []

    origin_query = """
    SELECT DISTINCT tr.source_country
    FROM european_gas_trade tr
    WHERE tr.source_country IS NOT NULL AND TRIM(tr.source_country) <> ''
    ORDER BY tr.source_country;
    """
    origins_df = load_data(origin_query)
    origins = origins_df['source_country'].tolist() if not origins_df.empty else []

    return html.Div([
        # Main Container
        html.Div([
            # Left/Center: Charts Area
            html.Div([
                # Chart 1
                html.Div([
                    html.Div([
                        html.H2("European Gas Imports - Pipeline vs. LNG - Billion Cubic Meters",
                                style={'color': TITLE_COLOR, 'fontSize': '18px', 'marginBottom': '0px', 'fontFamily': 'Lato, sans-serif'}),
                        html.Button("Export to CSV", id="export-chart1-btn", n_clicks=0, style={
                            "backgroundColor": "white",
                            "color": "#2c3e50",
                            "border": "1px solid #dee2e6",
                            "padding": "6px 12px",
                            "borderRadius": "4px",
                            "cursor": "pointer",
                            "fontSize": "12px",
                            "fontWeight": "normal",
                        })
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
                    
                    # Chart 1 Granularity Controls
                    html.Div([
                        html.Div([
                            html.Span("Year of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                            html.Button('+', id='chart1-toggle-year-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#add8e6', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Quarter of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                            html.Button('+', id='chart1-toggle-quarter-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Month of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                            html.Button('+', id='chart1-toggle-month-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Day of Year", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                            html.Button('+', id='chart1-toggle-day-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center'})
                    ], style={
                        'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#f8f9fa', 
                        'padding': '5px 10px', 'borderRadius': '4px', 'marginBottom': '0px',
                        'position': 'relative', 'top': '0px', 'left': '20px', 'zIndex': '10'
                    }),

                    dcc.Loading(dcc.Graph(id='chart-1', config={'displayModeBar': False}, figure={'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 350}}))
                ], style={'marginBottom': '30px', 'backgroundColor': 'white', 'padding': '10px', 'position': 'relative'}),

                # Chart 2
                html.Div([
                    html.Div([
                        html.H2("All Monthly Gas Imports by Source-Billion Cubic Meters",
                                style={'color': TITLE_COLOR, 'fontSize': '18px', 'marginBottom': '0px', 'fontFamily': 'Lato, sans-serif'}),
                        html.Button("Export to CSV", id="export-chart2-btn", n_clicks=0, style={
                            "backgroundColor": "white",
                            "color": "#2c3e50",
                            "border": "1px solid #dee2e6",
                            "padding": "6px 12px",
                            "borderRadius": "4px",
                            "cursor": "pointer",
                            "fontSize": "12px",
                            "fontWeight": "normal",
                        })
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
                    
                    # Chart 2 Granularity Controls
                    html.Div([
                        html.Div([
                            html.Span("Year of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                            html.Button('+', id='chart2-toggle-year-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#add8e6', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Quarter of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                            html.Button('+', id='chart2-toggle-quarter-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Month of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                            html.Button('+', id='chart2-toggle-month-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#add8e6', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Day of Year", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                            html.Button('+', id='chart2-toggle-day-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center'})
                    ], style={
                        'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#f8f9fa', 
                        'padding': '5px 10px', 'borderRadius': '4px', 'marginBottom': '0px',
                        'position': 'relative', 'top': '0px', 'left': '20px', 'zIndex': '10'
                    }),

                    dcc.Loading(dcc.Graph(id='chart-2', config={'displayModeBar': False}, figure={'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 360}}))
                ], style={'marginBottom': '30px', 'backgroundColor': 'white', 'padding': '10px', 'position': 'relative'}),

                # Chart 3
                html.Div([
                    html.Div([
                        html.H2("All Gas Imports Daily - Pipeline vs. LNG - Billion Cubic Meters",
                                style={'color': TITLE_COLOR, 'fontSize': '18px', 'marginBottom': '0px', 'fontFamily': 'Lato, sans-serif'}),
                        html.Button("Export to CSV", id="export-chart3-btn", n_clicks=0, style={
                            "backgroundColor": "white",
                            "color": "#2c3e50",
                            "border": "1px solid #dee2e6",
                            "padding": "6px 12px",
                            "borderRadius": "4px",
                            "cursor": "pointer",
                            "fontSize": "12px",
                            "fontWeight": "normal",
                        })
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
                    dcc.Loading(dcc.Graph(id='chart-3', config={'displayModeBar': False}, figure={'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 280}}))
                ], style={'marginBottom': '30px', 'backgroundColor': 'white', 'padding': '10px'}),

                # Chart 4 (Table)
                html.Div([
                    html.Div([
                        html.H2("Gas Flows to Europe by Country and Source-Billion Cubic Meters",
                                style={'color': TITLE_COLOR, 'fontSize': '18px', 'marginBottom': '0px', 'fontFamily': 'Lato, sans-serif'}),
                        html.Button("Export to CSV", id="export-table-btn", n_clicks=0, style={
                            "backgroundColor": "white",
                            "color": "#2c3e50",
                            "border": "1px solid #dee2e6",
                            "padding": "6px 12px",
                            "borderRadius": "4px",
                            "cursor": "pointer",
                            "fontSize": "12px",
                            "fontWeight": "normal",
                        })
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
                    dcc.Loading(
                        id="loading-gas-table",
                        type="default",
                        children=html.Div(id='gas-imports-mix-table-container')
                    )
                ], style={'marginBottom': '30px', 'marginTop': '20px', 'backgroundColor': 'white', 'padding': '10px'}),
                
                # Source info
                html.P("Source: Energy Intelligence, Transmission System Operators, Federal Agencies",
                       style={'fontSize': '10px', 'color': '#666', 'fontStyle': 'italic', 'paddingLeft': '10px'})

            ], style={'flex': '1', 'padding': '10px', 'minWidth': '0'}),

            # Right Side Panel: Filters
            html.Div([
                html.Div([
                    html.Div([
                        html.Label("Country", style={'fontWeight': 'normal', 'fontSize': '13px', 'color': '#333'}),
                        dcc.Dropdown(
                            id='country-dropdown',
                            options=[{'label': '(All)', 'value': '(All)'}] + [{'label': c, 'value': c} for c in countries],
                            value='(All)',
                            clearable=False,
                            style={'fontSize': '12px'}
                        ),
                    ], style={'marginBottom': '15px'}),

                    html.Div([
                        html.Label("Start Date", style={'fontWeight': 'normal', 'fontSize': '12px', 'color': '#333'}),
                        dcc.Input(
                            id='start-date-picker',
                            type='text',
                            value=(datetime.now().replace(year=datetime.now().year - 4, month=1, day=1)).strftime('%Y-%m-%d'),
                            placeholder='YYYY-MM-DD',
                            style={'width': '100%', 'padding': '4px', 'fontSize': '12px', 'border': '1px solid #ccc', 'borderRadius': '4px'}
                        ),
                    ], style={'marginBottom': '10px'}),

                    html.Div([
                        html.Label("End Date", style={'fontWeight': 'normal', 'fontSize': '12px', 'color': '#333'}),
                        dcc.Input(
                            id='end-date-picker',
                            type='text',
                            value=datetime.now().strftime('%Y-%m-%d'),
                            placeholder='YYYY-MM-DD',
                            style={'width': '100%', 'padding': '4px', 'fontSize': '12px', 'border': '1px solid #ccc', 'borderRadius': '4px'}
                        ),
                    ], style={'marginBottom': '20px'}),

                    html.Div([
                        html.Label("Gas Origin", style={'fontWeight': 'normal', 'fontSize': '13px', 'color': '#333'}),
                        html.Div(id='gas-origin-legend-container', style={'maxHeight': '400px', 'overflowY': 'auto', 'border': '1px solid #eee', 'padding': '8px', 'backgroundColor': 'white'})
                    ], style={'marginBottom': '20px'}),

                    dcc.Store(id='chart1-selection', data=None),
                    dcc.Store(id='chart2-selection', data=None),
                    dcc.Store(id='chart3-selection', data=None),
                    dcc.Store(id='chart1-agg-state', data='YEARLY'),
                    dcc.Store(id='chart2-agg-state', data='MONTHLY'),
                    html.Div(id='table-side-dummy-output', style={'display': 'none'}),
                    dcc.Download(id="download-chart1-csv"),
                    dcc.Download(id="download-chart2-csv"),
                    dcc.Download(id="download-chart3-csv"),
                    dcc.Download(id="download-table-csv-unique"),

                    html.Div([
                        html.Label("Flow Type", style={'fontWeight': 'normal', 'fontSize': '13px', 'color': '#333'}),
                        dcc.Checklist(
                            id='flow-type-1',
                            options=[{'label': ' (All)', 'value': '(All)'}, {'label': ' LNG', 'value': 'lng'}, {'label': ' pipeline', 'value': 'pipeline'}],
                            value=['(All)', 'lng', 'pipeline'],
                            labelStyle={'display': 'block', 'fontSize': '11px', 'marginBottom': '2px'},
                            style={'marginBottom': '20px'}
                        ),
                    ]),

                    html.Div([
                        html.Label("Flow Type", style={'fontWeight': 'normal', 'fontSize': '13px', 'color': '#333'}),
                        dcc.Checklist(
                            id='flow-type-2',
                            options=[{'label': ' (All)', 'value': '(All)'}, {'label': ' LNG', 'value': 'LNG'}, {'label': ' pipeline', 'value': 'pipeline'}],
                            value=['(All)', 'LNG', 'pipeline'],
                            labelStyle={'display': 'block', 'fontSize': '11px', 'marginBottom': '2px'},
                            style={'marginBottom': '20px'}
                        ),
                    ], style={'marginTop': '180px'}),

                    # Legend for LNG/Pipeline
                    html.Div([
                        html.Label("Flow Type", style={'fontWeight': 'bold', 'fontSize': '12px', 'color': '#333', 'marginBottom': '5px', 'display': 'block'}),
                        html.Div([
                            html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': LNG_COLOR, 'display': 'inline-block', 'marginRight': '8px'}),
                            html.Span("LNG", style={'fontSize': '11px'})
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '4px'}),
                        html.Div([
                            html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': PIPELINE_COLOR, 'display': 'inline-block', 'marginRight': '8px'}),
                            html.Span("pipeline", style={'fontSize': '11px'})
                        ], style={'display': 'flex', 'alignItems': 'center'})
                    ], style={'marginTop': '10px'})

                ], style={'padding': '15px', 'backgroundColor': '#fcfcfc', 'borderLeft': '1px solid #eee', 'minHeight': '100vh'})
            ], style={'width': '210px', 'position': 'sticky', 'top': '0'})

        ], style={'display': 'flex', 'flexDirection': 'row', 'width': '100%', 'maxWidth': '100%', 'margin': '0'})
    ], style={'backgroundColor': '#ffffff', 'fontFamily': 'Lato, sans-serif'})

def register_callbacks(dash_app, server):
    
    # Clientside callback to convert text inputs to date inputs (bypasses Dash validation)
    dash_app.clientside_callback(
        """
        function() {
            setTimeout(function() {
                const startInput = document.getElementById('start-date-picker');
                const endInput = document.getElementById('end-date-picker');
                
                if (startInput && startInput.type === 'text') {
                    startInput.type = 'date';
                    startInput.max = new Date().toISOString().split('T')[0];
                }
                
                if (endInput && endInput.type === 'text') {
                    endInput.type = 'date';
                    endInput.max = new Date().toISOString().split('T')[0];
                }
            }, 100);
            return null;
        }
        """,
        Output('table-side-dummy-output', 'children', allow_duplicate=True),
        Input('start-date-picker', 'id'),
        prevent_initial_call='initial_duplicate'
    )
    
    # Callback to handle "(All)" logic for data flows
    @dash_app.callback(
        Output('flow-type-1', 'value'),
        Input('flow-type-1', 'value'),
        prevent_initial_call=True
    )
    def handle_flow1_all(selected):
        all_vals = ['lng', 'pipeline']
        if not selected: return []
        if '(All)' in selected and selected[-1] == '(All)': return ['(All)'] + all_vals
        if '(All)' in selected and len(selected) < 3: return [v for v in selected if v != '(All)']
        if '(All)' not in selected and len(selected) == 2: return ['(All)'] + all_vals
        return selected

    @dash_app.callback(
        Output('flow-type-2', 'value'),
        Input('flow-type-2', 'value'),
        prevent_initial_call=True
    )
    def handle_flow2_all(selected):
        all_vals = ['LNG', 'pipeline']
        if not selected: return []
        if '(All)' in selected and selected[-1] == '(All)': return ['(All)'] + all_vals
        if '(All)' in selected and len(selected) < 3: return [v for v in selected if v != '(All)']
        if '(All)' not in selected and len(selected) == 2: return ['(All)'] + all_vals
        return selected

    # Export callback for Chart 1
    @dash_app.callback(
        Output("download-chart1-csv", "data"),
        Input("export-chart1-btn", "n_clicks"),
        [State('country-dropdown', 'value'),
         State('start-date-picker', 'value'),
         State('end-date-picker', 'value'),
         State('flow-type-1', 'value'),
         State('chart1-agg-state', 'data')],
        prevent_initial_call=True
    )
    def export_chart1_csv(n_clicks, country, start_date, end_date, flow1, agg_mode):
        if n_clicks is None or n_clicks == 0:
            return no_update
        
        where_clause, country_clause, params, _, f1_filtered, _ = get_query_params(country, start_date, end_date, [], flow1, [])
        agg_mode = (agg_mode or 'YEARLY').upper()

        if agg_mode == 'YEARLY':
            time_sql = "EXTRACT(YEAR FROM tr.date)::int AS \"Year\""
        elif agg_mode == 'QUARTERLY':
            time_sql = "DATE_TRUNC('quarter', tr.date) AS \"Quarter\""
        else: # MONTHLY
            time_sql = "DATE_TRUNC('month', tr.date) AS \"Month\""

        c1_query = f"""
        SELECT {time_sql}, tr.flow_type AS "Type", SUM(tr."flow_mcm/d") / 1000.0 AS "Billion Cubic Meters"
        FROM european_gas_trade tr {where_clause} {country_clause} AND LOWER(tr.flow_type) IN :flow_types
        GROUP BY 1, 2
        ORDER BY 1;
        """
        df = load_data(c1_query, {**params, 'flow_types': tuple(f1_filtered)})
        return dcc.send_data_frame(df.to_csv, "european_gas_imports_pipeline_vs_lng.csv", index=False)

    # Export callback for Chart 2
    @dash_app.callback(
        Output("download-chart2-csv", "data"),
        Input("export-chart2-btn", "n_clicks"),
        [State('country-dropdown', 'value'),
         State('start-date-picker', 'value'),
         State('end-date-picker', 'value'),
         State('flow-type-2', 'value'),
         State('chart2-agg-state', 'data')],
        prevent_initial_call=True
    )
    def export_chart2_csv(n_clicks, country, start_date, end_date, flow2, agg_mode):
        if n_clicks is None or n_clicks == 0:
            return no_update

        where_clause, country_clause, params, _, _, f2_filtered = get_query_params(country, start_date, end_date, [], [], flow2)
        agg_mode = (agg_mode or 'MONTHLY').upper()

        if agg_mode == 'YEARLY':
            time_sql = "EXTRACT(YEAR FROM tr.date)::int AS \"Year\""
        elif agg_mode == 'QUARTERLY':
            time_sql = "DATE_TRUNC('quarter', tr.date) AS \"Quarter\""
        elif agg_mode == 'DATE':
            time_sql = "tr.date AS \"Date\""
        else: # MONTHLY
            time_sql = "DATE_TRUNC('month', tr.date) AS \"Month\""

        c2_query = f"""
        SELECT {time_sql}, tr.source_country AS "Gas Origin", SUM(tr."flow_mcm/d") / 1000.0 AS "Billion Cubic Meters"
        FROM european_gas_trade tr {where_clause} {country_clause} AND LOWER(tr.flow_type) IN :flow_types
        AND tr.source_country IS NOT NULL AND TRIM(tr.source_country) <> ''
        GROUP BY 1, 2
        ORDER BY 1;
        """
        df = load_data(c2_query, {**params, 'flow_types': tuple(f2_filtered)})
        return dcc.send_data_frame(df.to_csv, "monthly_gas_imports_by_source.csv", index=False)

    # Export callback for Chart 3
    @dash_app.callback(
        Output("download-chart3-csv", "data"),
        Input("export-chart3-btn", "n_clicks"),
        [State('country-dropdown', 'value'),
         State('start-date-picker', 'value'),
         State('end-date-picker', 'value')],
        prevent_initial_call=True
    )
    def export_chart3_csv(n_clicks, country, start_date, end_date):
        if n_clicks is None or n_clicks == 0:
            return no_update

        where_clause, country_clause, params, _, _, _ = get_query_params(country, start_date, end_date, [], [], [])

        c3_query = f"""
        SELECT tr.date AS "Date", tr.flow_type AS "Type", SUM(tr."flow_mcm/d") / 1000.0 AS "Billion Cubic Meters"
        FROM european_gas_trade tr {where_clause} {country_clause}
        GROUP BY 1, 2
        ORDER BY 1;
        """
        df = load_data(c3_query, params)
        return dcc.send_data_frame(df.to_csv, "all_gas_imports_daily.csv", index=False)

    # Export callback for Table
    @dash_app.callback(
        Output("download-table-csv-unique", "data"),
        Input("export-table-btn", "n_clicks"),
        [State('country-dropdown', 'value'),
         State('start-date-picker', 'value'),
         State('end-date-picker', 'value')],
        prevent_initial_call=True
    )
    def export_table_csv(n_clicks, country, start_date, end_date):
        if n_clicks is None or n_clicks == 0:
            return no_update

        where_clause, country_clause, params, _, _, _ = get_query_params(country, start_date, end_date, [], [], [])
        
        # We need the pivoted table data
        table_query = f"""
        SELECT 
            DATE_TRUNC('month', tr.date) AS month_raw,
            TO_CHAR(DATE_TRUNC('month', tr.date), 'Month YYYY') AS "Month",
            tr.source_country AS "Origin", 
            tr.target_country AS "Destination", 
            SUM(tr."flow_mcm/d") / 1000.0 AS "Billion Cubic Meters"
        FROM european_gas_trade tr 
        {where_clause} 
        {country_clause}
        AND tr.source_country IS NOT NULL AND TRIM(tr.source_country) <> ''
        GROUP BY 1, 2, 3, 4
        ORDER BY 1 DESC;
        """
        df = load_data(table_query, params)
        
        pivot = df.pivot_table(
            index=['Month'], 
            columns=['Origin', 'Destination'], 
            values='Billion Cubic Meters', 
            aggfunc='sum'
        ).fillna(0)
        
        # Flatten columns for CSV
        pivot.columns = [f'{c[0]} -> {c[1]}' for c in pivot.columns]
        pivot.reset_index(inplace=True)
        
        return dcc.send_data_frame(pivot.to_csv, "gas_flows_to_europe_matrix.csv", index=False)

    @dash_app.callback(
        Output('gas-origin-legend-container', 'children'),
        Input('country-dropdown', 'value')
    )
    def update_origin_legend(country):
        # Build UI based on 'country'
        query = "SELECT DISTINCT source_country FROM european_gas_trade tr WHERE source_country IS NOT NULL AND TRIM(source_country) <> ''"
        params = {}
        if country and country != '(All)':
            query += " AND tr.target_country = :country"
            params['country'] = country
        query += " ORDER BY source_country;"
        df = load_data(query, params)
        origins = df['source_country'].tolist() if not df.empty else []
        
        items = []
        for origin in origins:
            # Use consistent color mapping function
            m_color = get_consistent_color_for_origin(origin)
            
            items.append(html.Div([
                html.Div(style={
                    'width': '12px', 'height': '12px', 'backgroundColor': m_color, 
                    'marginRight': '8px', 'opacity': 1.0,
                    'border': '1px solid #eee'
                }),
                html.Span(origin, style={
                    'fontSize': '11px', 
                    'fontWeight': 'normal',
                    'color': '#333'
                })
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '4px', 'cursor': 'default'}))
               
        return items

    # Selection callback for Chart 3 (Lines)
    @dash_app.callback(
        [Output('chart3-selection', 'data'),
         Output('chart-3', 'clickData')],
        [Input('chart-3', 'clickData')],
        [State('chart3-selection', 'data')]
    )
    def update_chart3_selection(c3_click, s3):
        if not c3_click: return no_update
        clicked_f = c3_click['points'][0].get('fullData', {}).get('name')
        if s3 == clicked_f:
            return None, None
        return clicked_f, None

    # Shared logic helper to reduce code duplication in separate callbacks
    def get_query_params(country, start_date, end_date, origins, flow1, flow2):
        today = datetime.now()
        def parse_dt(d_str, default):
            if not d_str: return default
            try: return pd.to_datetime(d_str, format='%Y-%m-%d')
            except:
                try: return pd.to_datetime(d_str, dayfirst=True)
                except: return default

        start_dt = parse_dt(start_date, pd.to_datetime('2021-01-01'))
        end_dt = parse_dt(end_date, today)
        if end_dt > today: end_dt = today

        # Basic filtering
        where_clause = "WHERE tr.date >= :start AND tr.date <= :end"
        params = {'start': start_dt, 'end': end_dt}
        
        country_clause = ""
        if country and country != '(All)':
            country_clause = " AND tr.target_country = :country"
            params['country'] = country
            
        # Clean specific filters
        of = [o for o in (origins or []) if o != '(All)']
        f1 = [f.lower() for f in (flow1 or []) if f != '(All)']
        f2 = [f.lower() for f in (flow2 or []) if f != '(All)']

        return where_clause, country_clause, params, of, f1, f2

    # CALLBACK 1: Chart 1 Only
    @dash_app.callback(
        Output('chart-1', 'figure'),
        [Input('country-dropdown', 'value'),
         Input('start-date-picker', 'value'),
         Input('end-date-picker', 'value'),
         Input('flow-type-1', 'value'),
         Input('chart1-selection', 'data'),
         Input('chart1-agg-state', 'data')]
    )
    def update_chart_1(country, start_date, end_date, flow1, sel1, agg_mode):
        try:
            where_clause, country_clause, params, _, f1_filtered, _ = get_query_params(country, start_date, end_date, [], flow1, [])
            agg_mode = (agg_mode or 'YEARLY').upper()

            # Mode-specific SQL aggregation
            if agg_mode == 'YEARLY':
                time_sql = "EXTRACT(YEAR FROM tr.date)::int AS \"grp_key\""
                label_fmt = lambda r: str(int(r['grp_key']))
            elif agg_mode == 'QUARTERLY':
                time_sql = "DATE_TRUNC('quarter', tr.date) AS \"grp_key\""
                label_fmt = lambda r: f"Q{(r['grp_key'].month-1)//3 + 1} {r['grp_key'].year}"
            elif agg_mode == 'DATE':
                time_sql = "tr.date AS \"grp_key\""
                label_fmt = lambda r: r['grp_key'].strftime('%d %b %y')
            else: # MONTHLY
                time_sql = "DATE_TRUNC('month', tr.date) AS \"grp_key\""
                label_fmt = lambda r: r['grp_key'].strftime('%b %y')

            c1_query = f"""
            SELECT {time_sql}, LOWER(tr.flow_type) AS "FlowType", SUM(tr."flow_mcm/d") / 1000.0 AS flow_bcm
            FROM european_gas_trade tr {where_clause} {country_clause} AND LOWER(tr.flow_type) IN :flow1 
            GROUP BY 1, 2
            ORDER BY 1;
            """
            # Smooth transition
            if not f1_filtered:
                if ctx.triggered_id in ['country-dropdown', 'start-date-picker', 'end-date-picker']:
                    return no_update
                return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 300}}
            
            c1_df = load_data(c1_query, {**params, 'flow1': tuple(f1_filtered)})
            if c1_df.empty: return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 350}}
            
            # Ensure grp_key is handled correctly for formatting/sorting
            if agg_mode == 'YEARLY':
                c1_df['grp_key_dt'] = pd.to_datetime(c1_df['grp_key'].astype(str) + '-01-01')
            else:
                c1_df['grp_key_dt'] = pd.to_datetime(c1_df['grp_key'])
                
            c1_df['x_label'] = c1_df.apply(label_fmt, axis=1)
            
            c1_grouped = c1_df.groupby(['grp_key_dt', 'x_label', 'FlowType'])['flow_bcm'].sum().reset_index()
            x_order = c1_df.sort_values('grp_key_dt')['x_label'].unique()
            
            fig1 = go.Figure()
            GREY_OUT = '#e0e0e0'
            flow_map = {'pipeline': 'Pipeline', 'lng': 'LNG'}
            
            for ft_key, flow_name in flow_map.items():
                if ft_key not in f1_filtered: continue
                
                subset = c1_grouped[c1_grouped['FlowType'] == ft_key]
                subset = subset.set_index('x_label').reindex(x_order).reset_index().fillna({'flow_bcm': 0})
                
                base_color = PIPELINE_COLOR if ft_key == 'pipeline' else LNG_COLOR
                colors = []
                line_widths = []
                line_colors = []
                
                for _, row in subset.iterrows():
                    is_dim = False
                    is_sel = False
                    ry_str = str(row['x_label']).strip()
                    if sel1:
                        if sel1.get('mode') == 'year':
                            if ry_str != str(sel1.get('year')).strip(): is_dim = True
                            else: is_sel = True
                        elif sel1.get('mode') == 'label':
                            # For QUARTERLY/MONTHLY mode label clicks
                            if ry_str != str(sel1.get('label')).strip(): is_dim = True
                            else: is_sel = True
                        elif sel1.get('mode') == 'bar':
                            if ry_str == str(sel1.get('year')).strip() and flow_name == sel1.get('flow'):
                                is_sel = True
                            else:
                                is_dim = True
                    
                    colors.append(base_color if not is_dim else '#f2f2f2')
                    line_widths.append(1.5 if is_sel and sel1 and sel1['mode'] in ['bar', 'label'] else 0)
                    line_colors.append('#333' if is_sel and sel1 and sel1['mode'] in ['bar', 'label'] else 'rgba(0,0,0,0)')

                fig1.add_trace(go.Bar(
                    name=flow_name, x=subset['grp_key_dt'] if agg_mode == 'DATE' else subset['x_label'], 
                    y=subset['flow_bcm'], 
                    marker=dict(color=colors, line=dict(width=line_widths, color=line_colors)),
                    text=subset['flow_bcm'].apply(lambda x: f"{x:.1f}" if x > 1 else ""), textposition='outside',
                    customdata=subset.apply(lambda r: [r['x_label'], flow_name, "BAR_CLICK"], axis=1),
                    hovertemplate="Flow Type: <span style='color:black'><b>"+flow_name+"</b></span><br>Date: <span style='color:black'><b>%{customdata[0]}</b></span><br>Flow (BCM): <span style='color:black'><b>%{y:.1f}</b></span><extra></extra>"
                ))

            # Year Headers matching Image 1 structure
            if agg_mode == 'YEARLY':
                # Shift header area up to avoid overlap with bar labels (which go up to ~550)
                HEADER_Y_BOTTOM = 640
                HEADER_Y_TOP = 710
                LABEL_Y = 675
                
                fig1.update_layout(xaxis=dict(showticklabels=False))
                fig1.add_trace(go.Scatter(
                    x=x_order, y=[LABEL_Y] * len(x_order), mode='text', 
                    text=[f"<b>{x}</b>" for x in x_order],
                    textposition='middle center', textfont=dict(size=13, color='#333'),
                    customdata=[[x, "", "YEAR_CLICK"] for x in x_order], showlegend=False, hoverinfo='none', marker=dict(opacity=0)
                ))
                
                # Add "Year of Date" label above the grid center
                fig1.add_annotation(
                    x=(len(x_order)-1)/2, y=LABEL_Y + 45, xref='x', yref='y',
                    text="Year of Date", showarrow=False,
                    font=dict(size=11, color='#666')
                )
                
                # Set range to fit header, but keep ticks visible only up to 600
                fig1.update_yaxes(range=[0, LABEL_Y + 70], tickvals=[0, 100, 200, 300, 400, 500, 600])
                
                # Header horizontal lines
                fig1.add_shape(type="line", x0=-0.5, x1=len(x_order)-0.5, y0=HEADER_Y_TOP, y1=HEADER_Y_TOP, line=dict(color="#d1d7de", width=1.5))
                fig1.add_shape(type="line", x0=-0.5, x1=len(x_order)-0.5, y0=HEADER_Y_BOTTOM, y1=HEADER_Y_BOTTOM, line=dict(color="#333", width=1.2))
                
                # Vertical separators between years
                for i in range(len(x_order) + 1):
                    x_pos = i - 0.5
                    fig1.add_shape(type="line", x0=x_pos, x1=x_pos, y0=0, y1=HEADER_Y_TOP, line=dict(color="#dee2e6", width=1), layer='below')
            else:
                # For QUARTERLY, MONTHLY, and DATE modes, add clickable footer labels
                footer_text = x_order if agg_mode != 'DATE' else ["" for _ in x_order]
                
                # Determine footer label colors based on selection
                footer_colors = []
                for x_label in x_order:
                    if sel1 and sel1.get('mode') == 'label' and str(x_label).strip() == str(sel1.get('label')).strip():
                        footer_colors.append('rgba(0,0,0,0.1)')  # Slightly more visible for selected
                    else:
                        footer_colors.append('rgba(0,0,0,0.03)')  # Normal transparency
                
                # Create customdata for footer labels
                footer_customdata = []
                for i, x_label in enumerate(x_order):
                    # Get the corresponding datetime for this x_label
                    corresponding_dt = c1_grouped[c1_grouped['x_label'] == x_label]['grp_key_dt'].iloc[0] if len(c1_grouped[c1_grouped['x_label'] == x_label]) > 0 else None
                    date_str = corresponding_dt.strftime('%Y-%m-%d') if corresponding_dt else ''
                    footer_customdata.append([x_label, date_str, 'LABEL_CLICK'])
                
                # Add footer label trace using a secondary y-axis
                fig1.add_trace(go.Bar(
                    x=x_order, y=[1] * len(x_order),
                    yaxis='y2', marker=dict(color=footer_colors, line=dict(width=0)),
                    text=footer_text, 
                    textposition='inside', insidetextanchor='middle', textangle=-90 if agg_mode in ['QUARTERLY', 'MONTHLY'] else 0, 
                    textfont=dict(size=11 if agg_mode == 'MONTHLY' else 10, color='#000000' if agg_mode == 'MONTHLY' else '#777', family='Lato, sans-serif'),
                    constraintext='none', cliponaxis=False,
                    hoverinfo='none', showlegend=False,
                    customdata=footer_customdata
                ))

            x_axis_config = dict(title="", tickfont=dict(size=11, color='#666'), showgrid=False)
            if agg_mode == 'DATE':
                x_axis_config.update(type='date', tickformat='%d %b %y', nticks=10)
            else:
                x_axis_config.update(type='category')
                if agg_mode != 'YEARLY':
                    # Hide x-axis tick labels when we have footer labels
                    x_axis_config.update(showticklabels=False)

            # Update layout with conditional y2 axis for footer labels
            layout_config = dict(
                barmode='group', plot_bgcolor='white', paper_bgcolor='white', showlegend=False,
                margin=dict(t=50 if agg_mode == 'YEARLY' else 32, b=40 if agg_mode == 'DATE' else 20, l=50, r=20), height=350,
                xaxis=x_axis_config,
                yaxis=dict(showgrid=True, gridcolor='#f2f2f2', title="", ticksuffix="   ", tickfont=dict(size=11), visible=True),
                bargap=0.05 if agg_mode == 'DATE' else 0.3, 
                bargroupgap=0 if agg_mode == 'DATE' else 0.05,
                hoverlabel=dict(bgcolor="white", font_size=11, font_color="#777", font_family="Lato, sans-serif", bordercolor="#ddd")
            )
            
            # Add y2 axis for footer labels in non-YEARLY modes
            if agg_mode != 'YEARLY':
                footer_h = 0.3 if agg_mode == 'MONTHLY' else 0.12
                layout_config['yaxis']['domain'] = [footer_h, 1]
                layout_config['yaxis2'] = dict(domain=[0, footer_h], visible=(agg_mode != 'DATE'), showticklabels=False, fixedrange=True, range=[0, 1])
            
            fig1.update_layout(**layout_config)
            return fig1
        except Exception as e:
            print(f"Chart 1 error: {e}")
            return go.Figure()

    # CALLBACK 2: Chart 2 Only
    @dash_app.callback(
        Output('chart-2', 'figure'),
        [Input('country-dropdown', 'value'),
         Input('start-date-picker', 'value'),
         Input('end-date-picker', 'value'),
         Input('chart2-selection', 'data'),
         Input('chart2-agg-state', 'data')]
    )
    def update_chart_2(country, start_date, end_date, sel2, agg_mode):
        try:
            where_clause, country_clause, params, _, _, _ = get_query_params(country, start_date, end_date, [], [], [])
            agg_mode = (agg_mode or 'MONTHLY').upper()

            # Mode-specific SQL aggregation
            if agg_mode == 'YEARLY':
                time_sql = "EXTRACT(YEAR FROM tr.date)::int AS \"grp_key\""
                label_fmt = lambda r: str(int(r['grp_key']))
            elif agg_mode == 'QUARTERLY':
                time_sql = "DATE_TRUNC('quarter', tr.date) AS \"grp_key\""
                label_fmt = lambda r: f"Q{(r['grp_key'].month-1)//3 + 1} {r['grp_key'].year}"
            elif agg_mode == 'DATE':
                time_sql = "tr.date AS \"grp_key\""
                label_fmt = lambda r: r['grp_key'].strftime('%d %b %y')
            else: # MONTHLY
                time_sql = "DATE_TRUNC('month', tr.date) AS \"grp_key\""
                label_fmt = lambda r: r['grp_key'].strftime('%b %y')

            c2_query = f"""
            SELECT {time_sql}, tr.source_country AS "Gas Origin", SUM(tr."flow_mcm/d") / 1000.0 AS flow_bcm
            FROM european_gas_trade tr {where_clause} {country_clause}
            AND tr.source_country IS NOT NULL AND TRIM(tr.source_country) <> ''
            GROUP BY 1, 2
            ORDER BY 1;
            """
            c2_df = load_data(c2_query, params)
            if c2_df.empty: 
                return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 360}}
            
            # Ensure grp_key is handled correctly for formatting/sorting
            if agg_mode == 'YEARLY':
                c2_df['grp_key_dt'] = pd.to_datetime(c2_df['grp_key'].astype(str) + '-01-01')
            else:
                c2_df['grp_key_dt'] = pd.to_datetime(c2_df['grp_key'])
                
            # Mode-specific label formatting (Vectorized)
            if agg_mode == 'YEARLY':
                c2_df['x_label'] = c2_df['grp_key'].astype(str)
            elif agg_mode == 'QUARTERLY':
                c2_df['x_label'] = 'Q' + ((c2_df['grp_key_dt'].dt.month - 1) // 3 + 1).astype(str) + ' ' + c2_df['grp_key_dt'].dt.year.astype(str)
            elif agg_mode == 'DATE':
                c2_df['x_label'] = c2_df['grp_key_dt'].dt.strftime('%d %b %y')
            else: # MONTHLY
                c2_df['x_label'] = c2_df['grp_key_dt'].dt.strftime('%b %y')

            # Create pivot table for fast trace generation
            pivot = c2_df.pivot_table(index='grp_key_dt', columns='Gas Origin', values='flow_bcm', aggfunc='sum').fillna(0)
            pivot = pivot.sort_index()
            
            # Map labels for non-date modes
            label_map = c2_df.set_index('grp_key_dt')['x_label'].to_dict()
            x_order = [label_map[ts] for ts in pivot.index]
            
            fig2 = go.Figure()
            unique_origins = sorted(pivot.columns, reverse=True)
            
            # --- Selection Logic ---
            selected_month = None
            selected_origin = None
            selected_bar = None # {origin, label}
            
            if sel2:
                if isinstance(sel2, dict):
                    if sel2.get('mode') == 'bar':
                        selected_bar = {'origin': sel2.get('origin'), 'label': sel2.get('label')}
                    elif sel2.get('mode') == 'month':
                        selected_month = sel2.get('label')
                else:
                    # Backward compatibility for legend click
                    if sel2 in unique_origins:
                        selected_origin = sel2
                    else:
                        # Try to match as a date - convert sel2 to find matching month
                        try:
                            selected_dt = pd.to_datetime(sel2)
                            # Find the corresponding x_label by matching year and month
                            for i, ts in enumerate(pivot.index):
                                if ts.year == selected_dt.year and ts.month == selected_dt.month:
                                    selected_month = x_order[i]
                                    break
                        except:
                            # If sel2 is not a date, try to match it directly as x_label
                            if sel2 in x_order:
                                selected_month = sel2
            
            # --- Main Data Trace (with highlighting) ---
            x_vals = pivot.index if agg_mode == 'DATE' else x_order
            DIM_COLOR = '#f2f2f2'
            
            for i, origin in enumerate(unique_origins):
                y_vals = pivot[origin].values
                # Use consistent color mapping function
                base_color = get_consistent_color_for_origin(origin)
                
                colors = []
                line_widths = []
                line_colors = []
                
                # Use appropriate iteration based on mode
                iter_list = list(pivot.index) if agg_mode == 'DATE' else x_order
                
                for j, x_item in enumerate(iter_list):
                    # For DATE mode, x_item is a datetime; for others, it's a label string
                    x_label = x_order[j] if agg_mode != 'DATE' else x_item.strftime('%d %b %y')
                    
                    is_dim = False
                    is_sel = False
                    
                    if selected_bar:
                        bar_origin = str(selected_bar.get('origin', '')).strip()
                        bar_label = str(selected_bar.get('label', '')).strip()
                        if str(origin).strip() == bar_origin and str(x_label).strip() == bar_label:
                            is_sel = True
                        else:
                            is_dim = True
                    elif selected_month:
                        if str(x_label).strip() == str(selected_month).strip():
                            is_sel = True
                        else:
                            is_dim = True
                    elif selected_origin:
                        if str(origin).strip() == str(selected_origin).strip():
                            is_sel = True
                        else:
                            is_dim = True
                    
                    if is_dim:
                        colors.append(DIM_COLOR)
                        line_widths.append(0)
                        line_colors.append('rgba(0,0,0,0)')
                    elif is_sel:
                        colors.append(base_color)
                        # Only show border if it was an explicit bar click
                        line_widths.append(1.5 if selected_bar else 0)
                        line_colors.append('#333' if selected_bar else 'rgba(0,0,0,0)')
                    else:
                        # No selection active
                        colors.append(base_color)
                        line_widths.append(0)
                        line_colors.append('rgba(0,0,0,0)')
                
                # Create customdata for both bar clicks and origin identification
                customdata = []
                for j, x_item in enumerate(iter_list):
                    x_label = x_order[j] if agg_mode != 'DATE' else x_item.strftime('%d %b %y')
                    customdata.append([x_label, origin, 'BAR_CLICK'])
                
                fig2.add_trace(go.Bar(
                    x=x_vals, y=y_vals, name=origin, 
                    marker=dict(color=colors, line=dict(width=line_widths, color=line_colors)), 
                    hovertemplate="Origin: <span style='color:black'><b>"+origin+"</b></span><br>Date: <span style='color:black'><b>%{customdata[0]}</b></span><br>Flow (BCM): <span style='color:black'><b>%{y:.3f}</b></span><extra></extra>",
                    customdata=customdata
                ))

            # footer labels trace (yaxis2) - for month label clicks - only add if not in DATE mode
            if agg_mode != 'DATE':
                footer_text = x_order
                
                # Determine footer label colors based on selection
                footer_colors = []
                for x_label in x_order:
                    if selected_month and x_label == selected_month:
                        footer_colors.append('rgba(0,0,0,0.1)')  # Slightly more visible for selected
                    elif selected_bar and x_label == selected_bar['label']:
                        footer_colors.append('rgba(0,0,0,0.08)')
                    else:
                        footer_colors.append('rgba(0,0,0,0.03)')  # Normal transparency
                
                # Create customdata for footer labels with proper date mapping
                footer_customdata = []
                for i, x_label in enumerate(x_order):
                    # Get the corresponding datetime for this x_label
                    corresponding_dt = list(pivot.index)[i]
                    date_str = corresponding_dt.strftime('%Y-%m-%d')
                    footer_customdata.append([x_label, date_str, 'LABEL_CLICK'])
                
                fig2.add_trace(go.Bar(
                    x=x_vals, y=[1] * len(x_vals),
                    yaxis='y2', marker=dict(color=footer_colors, line=dict(width=0)),
                    text=footer_text, 
                    textposition='inside', insidetextanchor='middle', textangle=-90 if agg_mode not in ['YEARLY'] else 0, 
                    textfont=dict(size=11 if agg_mode == 'MONTHLY' else 10, color='#000000' if agg_mode == 'MONTHLY' else '#777', family='Lato, sans-serif'),
                    constraintext='none', cliponaxis=False,
                    hoverinfo='none', showlegend=False,
                    customdata=footer_customdata
                ))

            x_axis_config = dict(showgrid=False, showticklabels=(agg_mode == 'DATE'), anchor='y2' if agg_mode != 'DATE' else 'y')
            if agg_mode == 'DATE':
                # Set range to match data to remove grey space after values
                min_date = pivot.index.min()
                max_date = pivot.index.max()
                x_axis_config.update(type='date', tickformat='%d %b %y', nticks=10, tickfont=dict(size=9, color='#777'), range=[min_date, max_date])
            else:
                x_axis_config.update(type='category', showticklabels=False)

            # Determine Y-axis config based on granularity
            y_range = [0, 60]
            y_dtick = 20
            
            if agg_mode == 'YEARLY':
                y_range = [0, 800]
                y_dtick = 200
            elif agg_mode == 'QUARTERLY':
                y_range = [0, 200]
                y_dtick = 50
            elif agg_mode == 'DATE':
                y_range = [0, 3]
                y_dtick = 1
            
            # Configure layout based on mode
            layout_config = {
                'barmode': 'stack',
                'plot_bgcolor': 'white',
                'paper_bgcolor': 'white',
                'showlegend': False,
                'margin': dict(t=10, b=30 if agg_mode == 'DATE' else 0, l=40, r=2),
                'height': 360,
                'xaxis': x_axis_config,
                'yaxis': dict(
                    showgrid=True,
                    gridcolor='#f2f2f2',
                    tickfont=dict(size=11, color='#666'),
                    domain=[0, 1] if agg_mode == 'DATE' else [0.3 if agg_mode == 'MONTHLY' else 0.15, 1],
                    tick0=0,
                    dtick=y_dtick,
                    range=y_range,
                    rangemode='tozero',
                    fixedrange=True
                ),
                'bargap': 0 if agg_mode == 'DATE' else 0.02,
                'hoverlabel': dict(bgcolor="white", font_size=11, font_color="#777", font_family="Lato, sans-serif", bordercolor="#ddd")
            }
            
            # Only add yaxis2 if not in DATE mode
            if agg_mode != 'DATE':
                layout_config['yaxis2'] = dict(
                    domain=[0, 0.3 if agg_mode == 'MONTHLY' else 0.15],
                    visible=True,
                    showticklabels=False,
                    fixedrange=True,
                    range=[0, 1]
                )
            
            fig2.update_layout(**layout_config)
            return fig2
        except Exception as e:
            print(f"Chart 2 error: {e}")
            return go.Figure()

    # Chart 1 State Manager (Granularity + Selections)
    # Merging both avoids chain reactions and solves "Duplicate callback outputs"
    @dash_app.callback(
        [Output('chart1-agg-state', 'data'),
         Output('chart1-selection', 'data'),
         Output('chart1-toggle-year-btn', 'children'),
         Output('chart1-toggle-quarter-btn', 'children'),
         Output('chart1-toggle-month-btn', 'children'),
         Output('chart1-toggle-day-btn', 'children')],
        [Input('chart1-toggle-year-btn', 'n_clicks'),
         Input('chart1-toggle-quarter-btn', 'n_clicks'),
         Input('chart1-toggle-month-btn', 'n_clicks'),
         Input('chart1-toggle-day-btn', 'n_clicks'),
         Input('chart-1', 'clickData')],
        [State('chart1-agg-state', 'data'),
         State('chart1-selection', 'data')]
    )
    def chart1_state_manager(y_c, q_c, m_c, d_c, c1_click, current_gran, s1):
        tr = ctx.triggered_id
        if not tr or tr == 'None':
            cg = current_gran or 'YEARLY'
            return cg, no_update, ('-' if cg == 'YEARLY' else '+'), ('-' if cg == 'QUARTERLY' else '+'), ('-' if cg == 'MONTHLY' else '+'), ('-' if cg == 'DATE' else '+')

        # Handle Chart 1 Click
        if tr == 'chart-1':
            if not c1_click or 'points' not in c1_click: return [no_update]*6
            cdata = c1_click['points'][0].get('customdata', [])
            if not cdata or len(cdata) < 3: return [no_update]*6
            
            val = str(cdata[0]) # Year/Label
            flow = str(cdata[1])
            ctype = str(cdata[2])
            
            new_s1 = s1
            if ctype == "YEAR_CLICK":
                if s1 and s1.get('mode') == 'year' and str(s1.get('year')) == val:
                    new_s1 = None
                else:
                    new_s1 = {'mode': 'year', 'year': val}
            elif ctype == "LABEL_CLICK":
                # Handle footer label clicks in QUARTERLY/MONTHLY modes
                if s1 and s1.get('mode') == 'label' and str(s1.get('label')) == val:
                    new_s1 = None
                else:
                    new_s1 = {'mode': 'label', 'label': val}
            else: # BAR_CLICK
                if s1 and s1.get('mode') == 'bar' and str(s1.get('year')) == val and str(s1.get('flow')) == flow:
                    new_s1 = None
                else:
                    new_s1 = {'mode': 'bar', 'year': val, 'flow': flow}
            
            # Use no_update for granularity to prevent double load on click
            # Use no_update for granularity to prevent double load on click
            return no_update, new_s1, no_update, no_update, no_update, no_update

        # Handle Granularity Buttons
        new_gran = 'YEARLY'
        if 'year' in tr: new_gran = 'YEARLY'
        elif 'quarter' in tr: new_gran = 'QUARTERLY'
        elif 'month' in tr: new_gran = 'MONTHLY'
        elif 'day' in tr: new_gran = 'DATE'
        
        if new_gran == current_gran:
            return [no_update]*6
            
        return new_gran, None, ('-' if new_gran == 'YEARLY' else '+'), ('-' if new_gran == 'QUARTERLY' else '+'), ('-' if new_gran == 'MONTHLY' else '+'), ('-' if new_gran == 'DATE' else '+')

    # Independent reset callback for Chart 1
    @dash_app.callback(
        Output('chart-1', 'clickData'),
        Input('chart-1', 'clickData')
    )
    def reset_chart1_click(clickData):
        if clickData:
            return None
        return no_update

    # Chart 2 State Manager (Granularity + Selections)
    # Merging both avoids chain reactions and solves "Duplicate callback outputs"
    @dash_app.callback(
        [Output('chart2-agg-state', 'data'),
         Output('chart2-selection', 'data'),
         Output('chart2-toggle-year-btn', 'children'),
         Output('chart2-toggle-quarter-btn', 'children'),
         Output('chart2-toggle-month-btn', 'children'),
         Output('chart2-toggle-day-btn', 'children')],
        [Input('chart2-toggle-year-btn', 'n_clicks'),
         Input('chart2-toggle-quarter-btn', 'n_clicks'),
         Input('chart2-toggle-month-btn', 'n_clicks'),
         Input('chart2-toggle-day-btn', 'n_clicks'),
         Input('chart-2', 'clickData')],
        [State('chart2-agg-state', 'data'),
         State('chart2-selection', 'data')]
    )
    def chart2_state_manager(y_c, q_c, m_c, d_c, c2_click, current_gran, s2):
        tr = ctx.triggered_id
        if not tr or tr == 'None':
            cg = current_gran or 'MONTHLY'
            return cg, no_update, ('-' if cg == 'YEARLY' else '+'), ('-' if cg == 'QUARTERLY' else '+'), ('-' if cg == 'MONTHLY' else '+'), ('-' if cg == 'DATE' else '+')

        # Handle Chart 2 Click
        if tr == 'chart-2':
            if not c2_click or 'points' not in c2_click: return [no_update]*6
            point = c2_click['points'][0]
            customdata = point.get('customdata', [])
            
            new_s2 = s2
            if customdata and len(customdata) >= 3:
                x_label = str(customdata[0]).strip()
                origin = str(customdata[1]).strip()
                click_type = str(customdata[2])
                
                if click_type == 'BAR_CLICK':
                    if isinstance(s2, dict) and s2.get('mode') == 'bar' and \
                       str(s2.get('origin')).strip() == origin and str(s2.get('label')).strip() == x_label:
                        new_s2 = None
                    else:
                        new_s2 = {'mode': 'bar', 'origin': origin, 'label': x_label}
                elif click_type == 'LABEL_CLICK':
                    date_str = str(customdata[1])
                    if isinstance(s2, dict) and s2.get('mode') == 'month' and s2.get('month') == date_str:
                        new_s2 = None
                    else:
                        new_s2 = {'mode': 'month', 'month': date_str, 'label': x_label}
            
            # Use no_update for granularity to prevent double load on click
            # Use no_update for granularity to prevent double load on click
            return no_update, new_s2, no_update, no_update, no_update, no_update

        # Handle Granularity Buttons
        new_gran = 'MONTHLY'
        if 'year' in tr: new_gran = 'YEARLY'
        elif 'quarter' in tr: new_gran = 'QUARTERLY'
        elif 'month' in tr: new_gran = 'MONTHLY'
        elif 'day' in tr: new_gran = 'DATE'
        
        if new_gran == current_gran:
            return [no_update]*6
            
        return new_gran, None, ('-' if new_gran == 'YEARLY' else '+'), ('-' if new_gran == 'QUARTERLY' else '+'), ('-' if new_gran == 'MONTHLY' else '+'), ('-' if new_gran == 'DATE' else '+')

    # Independent reset callback for Chart 2
    @dash_app.callback(
        Output('chart-2', 'clickData'),
        Input('chart-2', 'clickData')
    )
    def reset_chart2_click(clickData):
        if clickData:
            return None
        return no_update

    # CALLBACK 3: Chart 3 Only
    @dash_app.callback(
        Output('chart-3', 'figure'),
        [Input('country-dropdown', 'value'),
         Input('start-date-picker', 'value'),
         Input('end-date-picker', 'value'),
         Input('flow-type-2', 'value'),
         Input('chart3-selection', 'data')]
    )
    def update_chart_3(country, start_date, end_date, flow2, sel3):
        where_clause, country_clause, params, _, _, flow2_filtered = get_query_params(country, start_date, end_date, [], [], flow2)
        
        # Smooth transition
        if not flow2_filtered:
            if ctx.triggered_id in ['country-dropdown', 'start-date-picker', 'end-date-picker']:
                return no_update
            return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 280}}

        c3_query = f"""
        SELECT tr.date AS "Day of Date", INITCAP(LOWER(tr.flow_type)) AS "FlowName", SUM(tr."flow_mcm/d") / 1000.0 AS flows_bcm
        FROM european_gas_trade tr {where_clause} {country_clause} AND LOWER(tr.flow_type) IN :flow2 GROUP BY 1, 2 ORDER BY 1;
        """
        c3_df = load_data(c3_query, {**params, 'flow2': tuple(flow2_filtered)})
        fig3 = go.Figure()
        if c3_df.empty: return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 280}}
        flow_names = sorted(c3_df['FlowName'].unique())
        
        # Determine current highlight category
        tgt = sel3

        # Z-order: Put active line on top
        if tgt:
            matches = [f for f in flow_names if f.upper() == tgt.upper()]
            if matches:
                 m = matches[0]
                 flow_names.remove(m)
                 flow_names.append(m)

        for fn in flow_names:
            sub = c3_df[c3_df['FlowName'] == fn]
            bc = LNG_COLOR if fn.upper() == 'LNG' else PIPELINE_COLOR
            is_dim = False
            if tgt and fn.upper() != tgt.upper(): is_dim = True
            
            m_color = hex_to_rgba(bc, 0.1) if is_dim else bc
            line_width = 3.0 if not is_dim else 1.2

            fig3.add_trace(go.Scatter(
                x=sub['Day of Date'], y=sub['flows_bcm'], name=fn, 
                mode='lines', 
                line=dict(color=m_color, width=line_width, shape='spline'),
                hovertemplate="Flow Type: <span style='color:black'><b>"+fn+"</b></span><br>Date: <span style='color:black'><b>%{x|%d %b %y}</b></span><br>Flow (BCM): <span style='color:black'><b>%{y:.4f}</b></span><extra></extra>"
            ))
        
        fig3.update_layout(
            plot_bgcolor='white', paper_bgcolor='white', height=280,
            showlegend=False, hovermode='closest',
            margin=dict(t=10, b=40, l=40, r=10),
            hoverlabel=dict(bgcolor="white", font_size=11, font_color="#777", font_family="Lato, sans-serif", bordercolor="#ddd")
        )
        fig3.update_xaxes(tickformat="%d-%b-%y", dtick="M4", showgrid=False, tickfont=dict(size=9, color='#666'))
        fig3.update_yaxes(showgrid=True, gridcolor='#f5f5f5', rangemode='tozero', tickfont=dict(size=10, color='#666'))
        return fig3

    # Table callback with enhanced highlighting support
    @dash_app.callback(
        Output('gas-imports-mix-table-container', 'children'),
        [Input('country-dropdown', 'value'),
         Input('start-date-picker', 'value'),
         Input('end-date-picker', 'value')],
    )
    def update_table(country, start_date, end_date):
        where_clause, country_clause, params, _, _, _ = get_query_params(country, start_date, end_date, [], [], [])

        t_query = f"""
        SELECT TO_CHAR(DATE_TRUNC('month', tr.date), 'FMMonth YYYY') AS "Month of Date", DATE_TRUNC('month', tr.date) as "month_raw",
        tr.source_country AS "Gas Origin", tr.target_country AS "Target Country", SUM(tr."flow_mcm/d") / 1000.0 AS flows_bcm
        FROM european_gas_trade tr {where_clause} {country_clause} 
        AND tr.source_country IS NOT NULL AND TRIM(tr.source_country) <> ''
        GROUP BY 1, 2, 3, 4 ORDER BY 2 DESC;
        """
        table_df = load_data(t_query, params)
        if table_df.empty: 
            return html.Div("No data found")

        pivot = table_df.pivot_table(index=['month_raw', 'Month of Date'], columns=['Gas Origin', 'Target Country'], values='flows_bcm', aggfunc='sum').fillna(0).sort_index(level=0, ascending=False)
        
        # Build Table Structure
        thead_rows = []
        
        # Border and Color Constants
        BORDER_STYLE = '1px solid #e5e7eb'  # Light gray border
        HEADER_BG = '#f9fafb'               # Very light gray for headers
        STICKY_BG = '#ffffff'               # White for sticky columns
        TEXT_COLOR = '#374151'              # Dark gray text
        
        # Header Row 1: "Gasflows to Europe" (spans 1), Origins (span dynamic)
        header_row_1 = [
            html.Th("Gasflows to Europe", rowSpan=2, style={'position': 'sticky', 'left': 0, 'zIndex': 20, 'backgroundColor': HEADER_BG, 'border': BORDER_STYLE, 'padding': '8px', 'width': '120px', 'minWidth': '120px', 'color': TEXT_COLOR, 'fontWeight': 'bold'})
        ]
        
        # Header Row 2: Targets
        header_row_2 = []
        
        unique_origins = sorted(table_df['Gas Origin'].unique())
        
        for origin in unique_origins:
            targets = sorted(table_df[table_df['Gas Origin'] == origin]['Target Country'].unique())
            if not targets: continue
            
            # Add Origin Header (spans number of targets)
            header_row_1.append(html.Th(origin, colSpan=len(targets), style={'textAlign': 'center', 'border': BORDER_STYLE, 'padding': '5px', 'backgroundColor': HEADER_BG, 'fontWeight': 'bold', 'color': TEXT_COLOR}))
            
            # Add Target Headers
            for target in targets:
                header_row_2.append(html.Th(target, style={'textAlign': 'center', 'border': BORDER_STYLE, 'padding': '5px', 'backgroundColor': HEADER_BG, 'fontWeight': 'bold', 'color': TEXT_COLOR}))
                
        thead_rows.append(html.Tr(header_row_1))
        thead_rows.append(html.Tr(header_row_2))
        
        # Table Body
        tbody_rows = []
        
        # Iterate rows
        for i, ((m_raw, m_name), row) in enumerate(pivot.iterrows()):
            row_cells = []
            
            # Month Cell (Sticky)
            row_cells.append(html.Td(m_name, 
                                    style={'position': 'sticky', 'left': 0, 'zIndex': 10, 'backgroundColor': STICKY_BG, 'fontWeight': 'bold', 'border': BORDER_STYLE, 'padding': '8px', 'width': '120px', 'minWidth': '120px', 'textAlign': 'left', 'color': TEXT_COLOR}))
            
            # Data Cells
            # Alternating rows can be very subtle or just white
            bg_color = '#ffffff' 
            
            for origin in unique_origins:
                targets = sorted(table_df[table_df['Gas Origin'] == origin]['Target Country'].unique())
                for target in targets:
                    val = row.get((origin, target), 0)
                    row_cells.append(html.Td(f"{val:.3f}" if val != 0 else "0.000", 
                                            style={'textAlign': 'right', 'border': BORDER_STYLE, 'padding': '5px', 'backgroundColor': bg_color, 'color': TEXT_COLOR}))
            
            tbody_rows.append(html.Tr(row_cells))
            
        return html.Div(
            html.Table(
                [html.Thead(thead_rows), html.Tbody(tbody_rows)],
                style={'borderCollapse': 'collapse', 'width': '100%', 'fontFamily': 'Lato, sans-serif', 'fontSize': '12px', 'color': TEXT_COLOR}
            ),
            style={'overflowX': 'auto', 'maxWidth': '100%', 'width': '100%', 'maxHeight': '650px', 'border': BORDER_STYLE}
        )



