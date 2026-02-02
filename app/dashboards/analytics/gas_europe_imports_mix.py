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

# Database connection
_engine = None

def get_db_connection():
    """Get database connection using existing config with singleton pattern"""
    global _engine
    if _engine is None:
        try:
            from core.data_helpers import get_db_connection_string
            _engine = create_engine(
                get_db_connection_string(),
                pool_size=5,
                max_overflow=10,
                pool_recycle=3600,
                pool_pre_ping=True,
                pool_timeout=30,
                echo=False
            )
        except Exception as e:
            print(f"Database connection error: {e}")
            return None
    return _engine

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

def load_data(query, params=None):
    """Execute query and return DataFrame"""
    engine = get_db_connection()
    if not engine:
        return pd.DataFrame()
    try:
        with engine.connect() as connection:
            df = pd.read_sql(text(query), connection, params=params)
        return df
    except Exception as e:
        print(f"Query error: {e}")
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
                        'position': 'absolute', 'top': '40px', 'left': '60px', 'zIndex': '10'
                    }),

                    dcc.Loading(dcc.Graph(id='chart-1', config={'displayModeBar': False}, figure={}))
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
                        'position': 'absolute', 'top': '40px', 'left': '60px', 'zIndex': '10'
                    }),

                    dcc.Loading(dcc.Graph(id='chart-2', config={'displayModeBar': False}, figure={}))
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
                    dcc.Loading(dcc.Graph(id='chart-3', config={'displayModeBar': False}, figure={}))
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
                        children=dash_table.DataTable(
                            id='gas-imports-mix-table',
                            fixed_rows={'headers': True},
                            merge_duplicate_headers=True,
                            style_table={
                                'overflowX': 'auto',
                                'overflowY': 'auto',
                                'maxHeight': '650px',
                                'border': '1px solid #9ca3af'
                            },
                            style_cell={
                                'textAlign': 'right',
                                'padding': '6px 8px',
                                'fontSize': '11px',
                                'fontFamily': 'Lato, sans-serif',
                                'color': 'rgb(27, 54, 93)',
                                'border': 'none',
                                'borderRight': '1px solid #9ca3af',
                                'minWidth': '60px',
                                'width': '60px',
                                'whiteSpace': 'nowrap',
                                'overflow': 'hidden',
                                'textOverflow': 'ellipsis'
                            },
                            style_header={
                                'backgroundColor': '#ffffff',
                                'fontWeight': 'bold',
                                'fontFamily': 'Lato, sans-serif',
                                'color': 'rgb(27, 54, 93)',
                                'border': 'none',
                                'borderRight': '1px solid #9ca3af',
                                'borderBottom': '1px solid #9ca3af',
                                'textAlign': 'center',
                                'padding': '6px',
                                'position': 'sticky',
                                'top': 0,
                                'zIndex': 200
                            },
                            style_data={
                                'border': 'none',
                                'borderRight': '1px solid #9ca3af',
                                'whiteSpace': 'nowrap',
                                'fontFamily': 'Lato, sans-serif',
                                'color': 'rgb(27, 54, 93)',
                                'overflow': 'hidden',
                                'textOverflow': 'ellipsis'
                            },
                            style_data_conditional=[
                                {
                                    'if': {'row_index': 'odd'},
                                    'backgroundColor': '#f1f5f9'
                                }
                            ],
                            style_cell_conditional=[
                                {
                                    'if': {'column_id': 'Month'},
                                    'textAlign': 'left',
                                    'fontWeight': 'bold',
                                    'backgroundColor': '#f8fafc',
                                    'minWidth': '100px',
                                    'width': '100px',
                                    'position': 'sticky',
                                    'left': 0,
                                    'zIndex': 100,
                                    'borderRight': '1px solid #9ca3af',
                                    'color': 'rgb(27, 54, 93)'
                                }
                            ],
                            style_header_conditional=[
                                {
                                    'if': {'header_index': 0},
                                    'backgroundColor': '#d1d7de',
                                    'color': 'rgb(27, 54, 93)',
                                    'borderRight': '1px solid #9ca3af',
                                    'borderBottom': '1px solid #9ca3af'
                                },
                                {
                                    'if': {'header_index': 0, 'column_id': 'Month'},
                                    'position': 'sticky',
                                    'left': 0,
                                    'zIndex': 301,
                                    'backgroundColor': '#d1d7de',
                                    'borderRight': '1px solid #9ca3af'
                                },
                                {
                                    'if': {'header_index': 1, 'column_id': 'Month'},
                                    'position': 'sticky',
                                    'left': 0,
                                    'zIndex': 300,
                                    'backgroundColor': '#ffffff',
                                    'borderRight': '1px solid #9ca3af'
                                }
                            ],
                            sort_action='native',
                            filter_action='native',
                            tooltip_duration=None
                        )
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
                            type='date',
                            value='2021-01-01',
                            max=datetime.now().strftime('%Y-%m-%d'),
                            style={'width': '100%', 'padding': '4px', 'fontSize': '12px', 'border': '1px solid #ccc', 'borderRadius': '4px'}
                        ),
                    ], style={'marginBottom': '10px'}),

                    html.Div([
                        html.Label("End Date", style={'fontWeight': 'normal', 'fontSize': '12px', 'color': '#333'}),
                        dcc.Input(
                            id='end-date-picker',
                            type='date',
                            value=datetime.now().strftime('%Y-%m-%d'),
                            max=datetime.now().strftime('%Y-%m-%d'),
                            style={'width': '100%', 'padding': '4px', 'fontSize': '12px', 'border': '1px solid #ccc', 'borderRadius': '4px'}
                        ),
                    ], style={'marginBottom': '20px'}),

                    html.Div([
                        html.Label("Gas Origin", style={'fontWeight': 'normal', 'fontSize': '13px', 'color': '#333'}),
                        html.Div(id='gas-origin-legend-container', style={'maxHeight': '400px', 'overflowY': 'auto', 'border': '1px solid #eee', 'padding': '8px', 'backgroundColor': 'white'})
                    ], style={'marginBottom': '20px'}),

                    dcc.Store(id='selected-origins-store'),
                    dcc.Store(id='chart1-selection', data=None),
                    dcc.Store(id='chart2-selection', data=None),
                    dcc.Store(id='chart3-selection', data=None),
                    dcc.Store(id='chart1-agg-state', data='YEARLY'),
                    dcc.Store(id='chart2-agg-state', data='MONTHLY'),
                    dcc.Store(id='table-highlight-state', data=None),
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
    
    # Callback to handle legend item clicks
    @dash_app.callback(
        Output('selected-origins-store', 'data', allow_duplicate=True),
        Input({'type': 'origin-legend-item', 'index': ALL}, 'n_clicks'),
        [State('selected-origins-store', 'data')],
        prevent_initial_call=True
    )
    def handle_legend_click(n_clicks, current_selected):
        if not ctx.triggered or not current_selected:
            return no_update
            
        triggered_id = ctx.triggered_id
        if not triggered_id or triggered_id == '':
            return no_update
            
        clicked_origin = triggered_id['index']
        selected = list(current_selected)
        
        if clicked_origin == '(All)':
            # If All is clicked, we toggle between selecting everything or just the first item
            # But usually Tableau behavior is: Click "All" -> Select all
            if '(All)' in selected:
                # If All was selected, maybe we keep it as is or deselect all but first
                # For simplicity: Always select all if "All" is clicked and not fully selected
                return selected # We'll handle this in the UI callback to reset if needed
            else:
                return ['(All)'] # UI callback will expand this
        
        if '(All)' in selected:
            # If clicking a specific origin while "All" is active, 
            # we switch to only that origin
            return [clicked_origin]
            
        if clicked_origin in selected:
            if len(selected) > 1:
                selected.remove(clicked_origin)
            else:
                # If it's the only one, maybe don't allow deselect or switch to All
                return ['(All)']
        else:
            selected.append(clicked_origin)
            
        return selected

    # Callback to handle "(All)" logic for data flows
    @dash_app.callback(
        Output('selected-origins-store', 'data', allow_duplicate=True),
        Input('selected-origins-store', 'data'),
        State('gas-origin-legend-container', 'children'),
        prevent_initial_call=True
    )
    def sync_all_origins(selected, legend_children):
        if not selected or not legend_children: return selected
        
        # Get all possible origins from legend items (excluding All)
        all_possible = []
        for child in legend_children:
            idx = child['props']['id']['index']
            if idx != '(All)':
                all_possible.append(idx)
        
        if '(All)' in selected and len(selected) == 1:
            return ['(All)'] + all_possible
            
        if set(selected).issuperset(set(all_possible)) and '(All)' not in selected:
            return ['(All)'] + all_possible
            
        if '(All)' in selected and len(selected) > 1 and len(selected) < len(all_possible) + 1:
            return [s for s in selected if s != '(All)']
            
        return selected

    # Similar logic for Flow Type 1 and 2
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
         State('selected-origins-store', 'data'),
         State('flow-type-2', 'value'),
         State('chart2-agg-state', 'data')],
        prevent_initial_call=True
    )
    def export_chart2_csv(n_clicks, country, start_date, end_date, origins, flow2, agg_mode):
        if n_clicks is None or n_clicks == 0:
            return no_update

        where_clause, country_clause, params, origins_filtered, _, f2_filtered = get_query_params(country, start_date, end_date, origins, [], flow2)
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
        FROM european_gas_trade tr {where_clause} {country_clause} AND tr.source_country IN :origins AND LOWER(tr.flow_type) IN :flow_types
        GROUP BY 1, 2
        ORDER BY 1;
        """
        df = load_data(c2_query, {**params, 'origins': tuple(origins_filtered), 'flow_types': tuple(f2_filtered)})
        return dcc.send_data_frame(df.to_csv, "monthly_gas_imports_by_source.csv", index=False)

    # Export callback for Chart 3
    @dash_app.callback(
        Output("download-chart3-csv", "data"),
        Input("export-chart3-btn", "n_clicks"),
        [State('country-dropdown', 'value'),
         State('start-date-picker', 'value'),
         State('end-date-picker', 'value'),
         State('selected-origins-store', 'data')],
        prevent_initial_call=True
    )
    def export_chart3_csv(n_clicks, country, start_date, end_date, origins):
        if n_clicks is None or n_clicks == 0:
            return no_update

        where_clause, country_clause, params, origins_filtered, _, _ = get_query_params(country, start_date, end_date, origins, [], [])

        c3_query = f"""
        SELECT tr.date AS "Date", tr.flow_type AS "Type", SUM(tr."flow_mcm/d") / 1000.0 AS "Billion Cubic Meters"
        FROM european_gas_trade tr {where_clause} {country_clause} AND tr.source_country IN :origins
        GROUP BY 1, 2
        ORDER BY 1;
        """
        df = load_data(c3_query, {**params, 'origins': tuple(origins_filtered)})
        return dcc.send_data_frame(df.to_csv, "all_gas_imports_daily.csv", index=False)

    # Export callback for Table
    @dash_app.callback(
        Output("download-table-csv-unique", "data"),
        Input("export-table-btn", "n_clicks"),
        [State('country-dropdown', 'value'),
         State('start-date-picker', 'value'),
         State('end-date-picker', 'value'),
         State('selected-origins-store', 'data')],
        prevent_initial_call=True
    )
    def export_table_csv(n_clicks, country, start_date, end_date, origins):
        if n_clicks is None or n_clicks == 0:
            return no_update

        where_clause, country_clause, params, origins_filtered, _, _ = get_query_params(country, start_date, end_date, origins, [], [])
        
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
        AND tr.source_country IN :origins
        GROUP BY 1, 2, 3, 4
        ORDER BY 1 DESC;
        """
        df = load_data(table_query, {**params, 'origins': tuple(origins_filtered)})
        
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
        [Output('gas-origin-legend-container', 'children'),
         Output('selected-origins-store', 'data', allow_duplicate=True)],
        [Input('country-dropdown', 'value'),
         Input('selected-origins-store', 'data')],
        prevent_initial_call='initial_duplicate'
    )
    def update_origin_legend(country, selected):
        # 1. If Country changed (or first load), we reset selection to 'All' for that country
        if not ctx.triggered_id or ctx.triggered_id == 'country-dropdown':
            query = "SELECT DISTINCT source_country FROM european_gas_trade tr WHERE source_country IS NOT NULL AND TRIM(source_country) <> ''"
            params = {}
            if country and country != '(All)':
                query += " AND tr.target_country = :country"
                params['country'] = country
            query += " ORDER BY source_country;"
            df = load_data(query, params)
            origins = df['source_country'].tolist() if not df.empty else []
            selected = ['(All)'] + origins
            # We return selected here to update the store, and we'll build UI below
        
        # 2. Build UI based on 'selected' and 'country'
        query = "SELECT DISTINCT source_country FROM european_gas_trade tr WHERE source_country IS NOT NULL AND TRIM(source_country) <> ''"
        params = {}
        if country and country != '(All)':
            query += " AND tr.target_country = :country"
            params['country'] = country
        query += " ORDER BY source_country;"
        df = load_data(query, params)
        origins = df['source_country'].tolist() if not df.empty else []
        
        if not selected:
            selected = ['(All)'] + origins

        items = []
        is_all_selected = '(All)' in (selected or [])
        

        for i, origin in enumerate(origins):
            is_sel = origin in (selected or [])
            # Use consistent color mapping function
            m_color = get_consistent_color_for_origin(origin)
            
            items.append(html.Div([
                html.Div(style={
                    'width': '12px', 'height': '12px', 'backgroundColor': m_color, 
                    'marginRight': '8px', 'opacity': 1.0 if is_sel else 0.2,
                    'border': '1px solid #eee'
                }),
                html.Span(origin, style={
                    'fontSize': '11px', 
                    'fontWeight': 'normal',
                    'color': '#333' if is_sel else '#999'
                })
            ], id={'type': 'origin-legend-item', 'index': origin}, 
               style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '4px', 'cursor': 'pointer'}))
               
        return items, selected

    # Selection callback for Chart 3 (Lines)
    @dash_app.callback(
        [Output('chart1-selection', 'data'),
         Output('chart2-selection', 'data'),
         Output('chart3-selection', 'data'),
         Output('chart-1', 'clickData'),
         Output('chart-2', 'clickData'),
         Output('chart-3', 'clickData')],
        [Input('chart-1', 'clickData'),
         Input('chart-2', 'clickData'),
         Input('chart-3', 'clickData'),
         Input('chart1-agg-state', 'data'),
         Input('chart2-agg-state', 'data')],
        [State('chart1-selection', 'data'),
         State('chart2-selection', 'data'),
         State('chart3-selection', 'data')]
    )
    def update_chart_selections(c1_click, c2_click, c3_click, agg1, agg2, s1, s2, s3):
        triggered_id = str(ctx.triggered_id)
        if not triggered_id or triggered_id == 'None': return no_update

        # 2. Reset only Chart 1 selection if its granularity changes
        if 'chart1-agg-state' in triggered_id:
            if s1 is None:
                return no_update, no_update, no_update, no_update, no_update, no_update
            return None, no_update, no_update, None, no_update, no_update

        # 3. Reset only Chart 2 selection if its granularity changes
        if 'chart2-agg-state' in triggered_id:
            if s2 is None:
                return no_update, no_update, no_update, no_update, no_update, no_update
            return no_update, None, no_update, no_update, None, no_update

        # 2. Handle Chart 1 Click
        if triggered_id == 'chart-1':
            if not c1_click: return no_update
            cdata = c1_click['points'][0].get('customdata', [])
            if not cdata or len(cdata) < 3: return no_update
            
            val = str(cdata[0]) # Year
            flow = str(cdata[1])
            ctype = str(cdata[2])
            
            # Toggle logic
            if ctype == "YEAR_CLICK":
                if s1 and s1.get('mode') == 'year' and str(s1.get('year')) == val:
                    return None, no_update, no_update, None, no_update, no_update
                return {'mode': 'year', 'year': val}, no_update, no_update, None, no_update, no_update
            else:
                if s1 and s1.get('mode') == 'bar' and str(s1.get('year')) == val and str(s1.get('flow')) == flow:
                    return None, no_update, no_update, None, no_update, no_update
                return {'mode': 'bar', 'year': val, 'flow': flow}, no_update, no_update, None, no_update, no_update

        # 3. Handle Chart 2 Click
        if triggered_id == 'chart-2':
            if not c2_click or 'points' not in c2_click: return no_update
            
            # Get click data
            point = c2_click['points'][0]
            customdata = point.get('customdata', [])
            
            if customdata and len(customdata) >= 3:
                x_label = str(customdata[0]).strip()
                origin = str(customdata[1]).strip()
                click_type = str(customdata[2])
                
                if click_type == 'BAR_CLICK':
                    new_sel = {'mode': 'bar', 'origin': origin, 'label': x_label}
                    
                    # Toggle logic
                    if isinstance(s2, dict) and s2.get('mode') == 'bar' and \
                       str(s2.get('origin')).strip() == origin and str(s2.get('label')).strip() == x_label:
                        return no_update, None, no_update, no_update, None, no_update
                    
                    return no_update, new_sel, no_update, no_update, None, no_update
                    
                elif click_type == 'LABEL_CLICK':
                    date_str = str(customdata[1])
                    new_sel = {'mode': 'month', 'month': date_str, 'label': x_label}
                    
                    # Toggle logic
                    if isinstance(s2, dict) and s2.get('mode') == 'month' and s2.get('month') == date_str:
                        return no_update, None, no_update, no_update, None, no_update
                        
                    return no_update, new_sel, no_update, no_update, None, no_update
                    
            elif customdata and len(customdata) >= 2:
                # Fallback for simpler customdata
                x_label = str(customdata[0]).strip()
                second_param = str(customdata[1]).strip()
                
                if not second_param: # Likely month
                    try:
                        raw_x = str(point.get('x'))
                        if raw_x:
                            clicked_date = pd.to_datetime(raw_x).strftime('%Y-%m-%d')
                            new_sel = {'mode': 'month', 'month': clicked_date, 'label': x_label}
                            if isinstance(s2, dict) and s2.get('mode') == 'month' and s2.get('month') == clicked_date:
                                return no_update, None, no_update, no_update, None, no_update
                            return no_update, new_sel, no_update, no_update, None, no_update
                    except: pass
                else: # Likely origin
                    new_sel = {'mode': 'bar', 'origin': second_param, 'label': x_label}
                    if isinstance(s2, dict) and s2.get('mode') == 'bar' and \
                       str(s2.get('origin')).strip() == second_param and str(s2.get('label')).strip() == x_label:
                        return no_update, None, no_update, no_update, None, no_update
                    return no_update, new_sel, no_update, no_update, None, no_update
            
            return no_update, None, no_update, no_update, None, no_update

        # 4. Handle Chart 3 Click
        if triggered_id == 'chart-3':
            if not c3_click: return no_update
            clicked_f = c3_click['points'][0].get('fullData', {}).get('name')
            if s3 == clicked_f:
                return no_update, no_update, None, no_update, no_update, None
            return no_update, no_update, clicked_f, no_update, no_update, None
            
        return no_update

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
                        elif sel1.get('mode') == 'bar':
                            if ry_str == str(sel1.get('year')).strip() and flow_name == sel1.get('flow'):
                                is_sel = True
                            else:
                                is_dim = True
                    
                    colors.append(base_color if not is_dim else '#f2f2f2')
                    line_widths.append(1.5 if is_sel and sel1 and sel1['mode'] == 'bar' else 0)
                    line_colors.append('#333' if is_sel and sel1 and sel1['mode'] == 'bar' else 'rgba(0,0,0,0)')

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

            x_axis_config = dict(title="", tickfont=dict(size=11, color='#666'), showgrid=False)
            if agg_mode == 'DATE':
                x_axis_config.update(type='date', tickformat='%d %b %y', nticks=10)
            else:
                x_axis_config.update(type='category')

            fig1.update_layout(
                barmode='group', plot_bgcolor='white', paper_bgcolor='white', showlegend=False,
                margin=dict(t=50 if agg_mode == 'YEARLY' else 32, b=40 if agg_mode == 'DATE' else 20, l=50, r=20), height=350,
                xaxis=x_axis_config,
                yaxis=dict(showgrid=True, gridcolor='#f2f2f2', title="", ticksuffix="   ", tickfont=dict(size=11), visible=True),
                bargap=0.05 if agg_mode == 'DATE' else 0.3, 
                bargroupgap=0 if agg_mode == 'DATE' else 0.05,
                hoverlabel=dict(bgcolor="white", font_size=11, font_color="#777", font_family="Lato, sans-serif", bordercolor="#ddd")
            )
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
         Input('selected-origins-store', 'data'),
         Input('chart2-selection', 'data'),
         Input('chart2-agg-state', 'data')]
    )
    def update_chart_2(country, start_date, end_date, origins, sel2, agg_mode):
        try:
            where_clause, country_clause, params, origins_filtered, _, _ = get_query_params(country, start_date, end_date, origins, [], [])
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
            FROM european_gas_trade tr {where_clause} {country_clause} AND tr.source_country IN :origins 
            GROUP BY 1, 2
            ORDER BY 1;
            """
            c2_df = load_data(c2_query, {**params, 'origins': tuple(origins_filtered)})
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
                
                for j, x_label in enumerate(x_order):
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
                for j, x_label in enumerate(x_order):
                    customdata.append([x_label, origin, 'BAR_CLICK'])
                
                fig2.add_trace(go.Bar(
                    x=x_vals, y=y_vals, name=origin, 
                    marker=dict(color=colors, line=dict(width=line_widths, color=line_colors)), 
                    hovertemplate="Origin: <span style='color:black'><b>"+origin+"</b></span><br>Date: <span style='color:black'><b>%{customdata[0]}</b></span><br>Flow (BCM): <span style='color:black'><b>%{y:.3f}</b></span><extra></extra>",
                    customdata=customdata
                ))

            # footer labels trace (yaxis2) - for month label clicks
            footer_text = x_order if agg_mode != 'DATE' else ["" for _ in x_order]
            
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
                textposition='inside', insidetextanchor='middle', textangle=-90 if agg_mode not in ['YEARLY', 'DATE'] else 0, 
                textfont=dict(size=10, color='#777', family='Lato, sans-serif'),
                hoverinfo='none', showlegend=False,
                customdata=footer_customdata
            ))

            x_axis_config = dict(showgrid=False, showticklabels=(agg_mode == 'DATE'), anchor='y2')
            if agg_mode == 'DATE':
                x_axis_config.update(type='date', tickformat='%d %b %y', nticks=10, tickfont=dict(size=9, color='#777'))
            else:
                x_axis_config.update(type='category', showticklabels=False)

            fig2.update_layout(
                barmode='stack', plot_bgcolor='white', paper_bgcolor='white', showlegend=False,
                margin=dict(t=10, b=30 if agg_mode == 'DATE' else 0, l=40, r=2), height=360,
                xaxis=x_axis_config,
                yaxis=dict(
                    showgrid=True, gridcolor='#f2f2f2', 
                    tickfont=dict(size=11, color='#666'), 
                    domain=[0.15, 1]
                ),
                yaxis2=dict(domain=[0, 0.15], visible=(agg_mode != 'DATE'), showticklabels=False, fixedrange=True, range=[0, 1]),
                bargap=0 if agg_mode == 'DATE' else 0.02, 
                hoverlabel=dict(bgcolor="white", font_size=11, font_color="#777", font_family="Lato, sans-serif", bordercolor="#ddd")
            )
            return fig2
        except Exception as e:
            print(f"Chart 2 error: {e}")
            return go.Figure()

    # Chart 1 Granularity Handler
    @dash_app.callback(
        [Output('chart1-agg-state', 'data'),
         Output('chart1-toggle-year-btn', 'children'),
         Output('chart1-toggle-quarter-btn', 'children'),
         Output('chart1-toggle-month-btn', 'children'),
         Output('chart1-toggle-day-btn', 'children')],
        [Input('chart1-toggle-year-btn', 'n_clicks'),
         Input('chart1-toggle-quarter-btn', 'n_clicks'),
         Input('chart1-toggle-month-btn', 'n_clicks'),
         Input('chart1-toggle-day-btn', 'n_clicks')],
        [State('chart1-agg-state', 'data')]
    )
    def chart1_granularity_handler(y_c, q_c, m_c, d_c, current_gran):
        if not ctx.triggered:
            cg = current_gran or 'YEARLY'
            return (cg, 
                    '-' if cg == 'YEARLY' else '+',
                    '-' if cg == 'QUARTERLY' else '+',
                    '-' if cg == 'MONTHLY' else '+',
                    '-' if cg == 'DATE' else '+')

        btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        new_gran = 'YEARLY'
        if 'year' in btn_id: new_gran = 'YEARLY'
        elif 'quarter' in btn_id: new_gran = 'QUARTERLY'
        elif 'month' in btn_id: new_gran = 'MONTHLY'
        elif 'day' in btn_id: new_gran = 'DATE'
            
        return (new_gran,
                '-' if new_gran == 'YEARLY' else '+',
                '-' if new_gran == 'QUARTERLY' else '+',
                '-' if new_gran == 'MONTHLY' else '+',
                '-' if new_gran == 'DATE' else '+')

    # Chart 2 Granularity Handler
    @dash_app.callback(
        [Output('chart2-agg-state', 'data'),
         Output('chart2-toggle-year-btn', 'children'),
         Output('chart2-toggle-quarter-btn', 'children'),
         Output('chart2-toggle-month-btn', 'children'),
         Output('chart2-toggle-day-btn', 'children')],
        [Input('chart2-toggle-year-btn', 'n_clicks'),
         Input('chart2-toggle-quarter-btn', 'n_clicks'),
         Input('chart2-toggle-month-btn', 'n_clicks'),
         Input('chart2-toggle-day-btn', 'n_clicks')],
        [State('chart2-agg-state', 'data')]
    )
    def chart2_granularity_handler(y_c, q_c, m_c, d_c, current_gran):
        if not ctx.triggered:
            cg = current_gran or 'MONTHLY'
            return (cg, 
                    '-' if cg == 'YEARLY' else '+',
                    '-' if cg == 'QUARTERLY' else '+',
                    '-' if cg == 'MONTHLY' else '+',
                    '-' if cg == 'DATE' else '+')

        btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        new_gran = 'MONTHLY'
        if 'year' in btn_id: new_gran = 'YEARLY'
        elif 'quarter' in btn_id: new_gran = 'QUARTERLY'
        elif 'month' in btn_id: new_gran = 'MONTHLY'
        elif 'day' in btn_id: new_gran = 'DATE'
            
        return (new_gran,
                '-' if new_gran == 'YEARLY' else '+',
                '-' if new_gran == 'QUARTERLY' else '+',
                '-' if new_gran == 'MONTHLY' else '+',
                '-' if new_gran == 'DATE' else '+')

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
        [Output('gas-imports-mix-table', 'data'),
         Output('gas-imports-mix-table', 'columns'),
         Output('gas-imports-mix-table', 'tooltip_data')],
        [Input('country-dropdown', 'value'),
         Input('start-date-picker', 'value'),
         Input('end-date-picker', 'value'),
         Input('selected-origins-store', 'data')],
    )
    def update_table(country, start_date, end_date, origins):
        where_clause, country_clause, params, origins_filtered, _, _ = get_query_params(country, start_date, end_date, origins, [], [])
        if not origins_filtered: 
            return [], [], []

        t_query = f"""
        SELECT TO_CHAR(DATE_TRUNC('month', tr.date), 'FMMonth YYYY') AS "Month of Date", DATE_TRUNC('month', tr.date) as "month_raw",
        tr.source_country AS "Gas Origin", tr.target_country AS "Target Country", SUM(tr."flow_mcm/d") / 1000.0 AS flows_bcm
        FROM european_gas_trade tr {where_clause} {country_clause} AND tr.source_country IN :origins GROUP BY 1, 2, 3, 4 ORDER BY 2 DESC;
        """
        table_df = load_data(t_query, {**params, 'origins': tuple(origins_filtered)})
        if table_df.empty: 
            return [], [], []

        pivot = table_df.pivot_table(index=['month_raw', 'Month of Date'], columns=['Gas Origin', 'Target Country'], values='flows_bcm', aggfunc='sum').fillna(0).sort_index(level=0, ascending=False)
        cols = [{"name": ["Gasflows to Europe", "Month"], "id": "Month"}]
        cuo = sorted(table_df['Gas Origin'].unique())
        for origin_idx, origin in enumerate(cuo):
            tcs = sorted(table_df[table_df['Gas Origin'] == origin]['Target Country'].unique())
            for target in tcs:
                # Add unique zero-width spaces (\u200b) to prevent merging identical names across parents
                unique_target = target + ("\u200b" * origin_idx)
                cols.append({"name": [origin, unique_target], "id": f"{origin}_{target}"})
        
        rows = []
        for (m_raw, m_name), row in pivot.iterrows():
            curr = {"Month": m_name}
            for c in cols[1:]:
                # Data is in pivot under (Origin, OriginalTarget). Column name has unique_target.
                orig_parent, unique_child = c['name']
                real_child = unique_child.replace('\u200b', '')
                val = row.get((orig_parent, real_child), 0)
                curr[c['id']] = f"{val:.3f}"
            rows.append(curr)
        
        # Tooltip data
        tooltip_data = []
        for row in rows:
            tooltip_row = {}
            for col in cols:
                col_id = col['id']
                if col_id in row:
                    val = str(row[col_id])
                    if val and val != '0.000':
                        tooltip_row[col_id] = {
                            'value': val,
                            'type': 'text'
                        }
            tooltip_data.append(tooltip_row)
        
        return rows, cols, tooltip_data


    # Clean Clientside Table Highlighting (Based on price_scorecard.py)
    dash_app.clientside_callback(
        """
        function(n_data, columns, current_state) {
            try {
                if (!window.gasImportsState) {
                    window.gasImportsState = {
                        selectedColumnId: null,
                        selectedRowIndex: null,
                        lastTableSignature: null
                    };
                }

                const tableId = 'gas-imports-mix-table';
                
                function clearAllColumnSelections(spreadsheet) {
                    if (!spreadsheet) return;
                    const selectedHeaders = spreadsheet.querySelectorAll('th.column-selected');
                    selectedHeaders.forEach(header => {
                        header.classList.remove('column-selected');
                        
                        // Restore original header styling
                        const columnId = header.getAttribute('data-dash-column');
                        const headerRow = header.closest('tr');
                        const thead = header.closest('thead');
                        let headerIndex = -1;
                        
                        if (thead && headerRow) {
                            const headerRows = Array.from(thead.querySelectorAll('tr')).filter(tr => 
                                tr.querySelector('th[data-dash-column]') !== null
                            );
                            headerIndex = headerRows.indexOf(headerRow);
                        }
                        
                        // Reset to original background color based on header level and column
                        if (columnId === 'Month') {
                            // Month header has special styling based on header level
                            if (headerIndex === 0) {
                                header.style.backgroundColor = '#d1d7de';
                            } else {
                                header.style.backgroundColor = '#ffffff';
                            }
                        } else {
                            // Regular headers
                            if (headerIndex === 0) {
                                header.style.backgroundColor = '#d1d7de';
                            } else {
                                header.style.backgroundColor = '#ffffff';
                            }
                        }
                        
                        header.style.color = 'rgb(27, 54, 93)';
                        header.style.fontWeight = 'bold'; // Headers are always bold
                    });
                    
                    const selectedCells = spreadsheet.querySelectorAll('td.column-cell-selected');
                    selectedCells.forEach(cell => {
                        cell.classList.remove('column-cell-selected');
                        
                        const columnId = cell.getAttribute('data-dash-column');
                        
                        if (columnId === 'Month') {
                            // Restore Month column special styling
                            cell.style.backgroundColor = '#f8fafc';
                            cell.style.fontWeight = 'bold';
                            cell.style.color = 'rgb(27, 54, 93)';
                            cell.style.textAlign = 'left';
                        } else {
                            // Restore regular data cell styling
                            const row = cell.closest('tr');
                            const rowIndex = row ? Array.from(row.parentNode.children).indexOf(row) : 0;
                            
                            // Restore alternating row colors (odd rows have #f1f5f9)
                            if (rowIndex % 2 === 1) {
                                cell.style.backgroundColor = '#f1f5f9';
                            } else {
                                cell.style.backgroundColor = '';
                            }
                            
                            cell.style.fontWeight = 'normal'; // Data cells are normal weight
                            cell.style.color = 'rgb(27, 54, 93)';
                        }
                        
                        cell.style.opacity = '1';
                    });
                    
                    if (spreadsheet.classList.contains('column-selection-active')) {
                        const allDataCells = spreadsheet.querySelectorAll('td[data-dash-column]:not([data-dash-column="Month"])');
                        allDataCells.forEach(cell => {
                            cell.style.opacity = '1';
                            
                            // Restore original alternating row colors for all cells
                            const row = cell.closest('tr');
                            const rowIndex = row ? Array.from(row.parentNode.children).indexOf(row) : 0;
                            
                            if (rowIndex % 2 === 1) {
                                cell.style.backgroundColor = '#f1f5f9';
                            } else {
                                cell.style.backgroundColor = '';
                            }
                        });
                        
                        // Ensure Month column cells always have their special styling
                        const monthCells = spreadsheet.querySelectorAll('td[data-dash-column="Month"]');
                        monthCells.forEach(cell => {
                            cell.style.backgroundColor = '#f8fafc';
                            cell.style.fontWeight = 'bold';
                            cell.style.color = 'rgb(27, 54, 93)';
                            cell.style.textAlign = 'left';
                            cell.style.opacity = '1';
                        });
                        
                        // Also reset any headers that might have had their opacity changed
                        const allHeaders = spreadsheet.querySelectorAll('th[data-dash-column]:not([data-dash-column="Month"])');
                        allHeaders.forEach(header => {
                            header.style.opacity = '1';
                            
                            // Ensure headers also get their original styling back
                            if (!header.classList.contains('column-selected')) {
                                const headerRow = header.closest('tr');
                                const thead = header.closest('thead');
                                let headerIndex = -1;
                                
                                if (thead && headerRow) {
                                    const headerRows = Array.from(thead.querySelectorAll('tr')).filter(tr => 
                                        tr.querySelector('th[data-dash-column]') !== null
                                    );
                                    headerIndex = headerRows.indexOf(headerRow);
                                }
                                
                                // Reset to original background color based on header level
                                if (headerIndex === 0) {
                                    header.style.backgroundColor = '#d1d7de';
                                } else {
                                    header.style.backgroundColor = '#ffffff';
                                }
                                
                                header.style.color = 'rgb(27, 54, 93)';
                                header.style.fontWeight = 'bold';
                            }
                        });
                        
                        // Ensure Month headers also get their styling back
                        const monthHeaders = spreadsheet.querySelectorAll('th[data-dash-column="Month"]');
                        monthHeaders.forEach(header => {
                            if (!header.classList.contains('column-selected')) {
                                const headerRow = header.closest('tr');
                                const thead = header.closest('thead');
                                let headerIndex = -1;
                                
                                if (thead && headerRow) {
                                    const headerRows = Array.from(thead.querySelectorAll('tr')).filter(tr => 
                                        tr.querySelector('th[data-dash-column]') !== null
                                    );
                                    headerIndex = headerRows.indexOf(headerRow);
                                }
                                
                                if (headerIndex === 0) {
                                    header.style.backgroundColor = '#d1d7de';
                                } else {
                                    header.style.backgroundColor = '#ffffff';
                                }
                                
                                header.style.color = 'rgb(27, 54, 93)';
                                header.style.fontWeight = 'bold';
                            }
                            header.style.opacity = '1';
                        });
                    }
                    spreadsheet.classList.remove('column-selection-active');
                }

                function clearAllRowSelections(spreadsheet) {
                    if (!spreadsheet) return;
                    const selectedRows = spreadsheet.querySelectorAll('tr.row-selected');
                    selectedRows.forEach(row => { row.classList.remove('row-selected'); });
                    
                    const cellsWithProperties = spreadsheet.querySelectorAll('td.row-cell-selected, th.row-cell-selected');
                    cellsWithProperties.forEach(cell => {
                        cell.classList.remove('row-cell-selected');
                        
                        if (cell.tagName === 'TD') {
                            const columnId = cell.getAttribute('data-dash-column');
                            
                            if (columnId === 'Month') {
                                // Restore Month column special styling
                                cell.style.backgroundColor = '#f8fafc';
                                cell.style.fontWeight = 'bold';
                                cell.style.color = 'rgb(27, 54, 93)';
                                cell.style.textAlign = 'left';
                            } else {
                                // Restore regular data cell styling
                                const row = cell.closest('tr');
                                const rowIndex = row ? Array.from(row.parentNode.children).indexOf(row) : 0;
                                
                                // Restore alternating row colors (odd rows have #f1f5f9)
                                if (rowIndex % 2 === 1) {
                                    cell.style.backgroundColor = '#f1f5f9';
                                } else {
                                    cell.style.backgroundColor = '';
                                }
                                
                                cell.style.fontWeight = 'normal';
                                cell.style.color = 'rgb(27, 54, 93)';
                            }
                        } else if (cell.tagName === 'TH') {
                            // Restore original header styling
                            const headerRow = cell.closest('tr');
                            const thead = cell.closest('thead');
                            let headerIndex = -1;
                            
                            if (thead && headerRow) {
                                const headerRows = Array.from(thead.querySelectorAll('tr')).filter(tr => 
                                    tr.querySelector('th[data-dash-column]') !== null
                                );
                                headerIndex = headerRows.indexOf(headerRow);
                            }
                            
                            // Reset to original background color based on header level
                            if (headerIndex === 0) {
                                cell.style.backgroundColor = '#d1d7de';
                            } else {
                                cell.style.backgroundColor = '#ffffff';
                            }
                            
                            cell.style.fontWeight = 'bold';
                            cell.style.color = 'rgb(27, 54, 93)';
                        }
                    });

                    const allTableCells = spreadsheet.querySelectorAll('td, th');
                    allTableCells.forEach(cell => {
                        cell.style.opacity = '1';
                        
                        // Restore original styling for all cells
                        if (cell.tagName === 'TD') {
                            const columnId = cell.getAttribute('data-dash-column');
                            
                            if (columnId === 'Month') {
                                // Ensure Month column always has its special styling
                                cell.style.backgroundColor = '#f8fafc';
                                cell.style.fontWeight = 'bold';
                                cell.style.color = 'rgb(27, 54, 93)';
                                cell.style.textAlign = 'left';
                            } else {
                                // Restore regular data cell styling
                                const row = cell.closest('tr');
                                const rowIndex = row ? Array.from(row.parentNode.children).indexOf(row) : 0;
                                
                                if (rowIndex % 2 === 1) {
                                    cell.style.backgroundColor = '#f1f5f9';
                                } else {
                                    cell.style.backgroundColor = '';
                                }
                                
                                cell.style.fontWeight = 'normal';
                                cell.style.color = 'rgb(27, 54, 93)';
                            }
                        } else if (cell.tagName === 'TH') {
                            const columnId = cell.getAttribute('data-dash-column');
                            const headerRow = cell.closest('tr');
                            const thead = cell.closest('thead');
                            let headerIndex = -1;
                            
                            if (thead && headerRow) {
                                const headerRows = Array.from(thead.querySelectorAll('tr')).filter(tr => 
                                    tr.querySelector('th[data-dash-column]') !== null
                                );
                                headerIndex = headerRows.indexOf(headerRow);
                            }
                            
                            if (columnId === 'Month') {
                                // Month header has special styling based on header level
                                if (headerIndex === 0) {
                                    cell.style.backgroundColor = '#d1d7de';
                                } else {
                                    cell.style.backgroundColor = '#ffffff';
                                }
                                cell.style.fontWeight = 'bold';
                                cell.style.color = 'rgb(27, 54, 93)';
                            } else {
                                // Regular headers
                                if (headerIndex === 0) {
                                    cell.style.backgroundColor = '#d1d7de';
                                } else {
                                    cell.style.backgroundColor = '#ffffff';
                                }
                                cell.style.fontWeight = 'bold';
                                cell.style.color = 'rgb(27, 54, 93)';
                            }
                        }
                    });

                    spreadsheet.classList.remove('row-selection-active');
                }

                function getCellValue(cell) {
                    const text = cell.textContent || cell.innerText || '';
                    return text.trim();
                }

                function enhanceTable() {
                    const tableEl = document.getElementById(tableId);
                    if (!tableEl) return;
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    if (!spreadsheet) return;
                    
                    const headers = spreadsheet.querySelectorAll('th[data-dash-column]');
                    if (headers.length === 0) return;
                    
                    let tableSignature = '';
                    const topRow = spreadsheet.querySelector('thead tr');
                    if (topRow) {
                        const topHeaders = Array.from(topRow.querySelectorAll('th')).slice(0, 5);
                        tableSignature = topHeaders.map(h => h.textContent.trim()).join('|') + '|' + headers.length;
                    } else tableSignature = headers.length.toString();
                    
                    const signatureChanged = window.gasImportsState.lastTableSignature !== tableSignature;
                    if (signatureChanged) {
                        spreadsheet.dataset.gasImportsEnhanced = 'false';
                        if (spreadsheet._gasImportsClickHandler) {
                            spreadsheet.removeEventListener('click', spreadsheet._gasImportsClickHandler, true);
                            spreadsheet._gasImportsClickHandler = null;
                        }
                        clearAllColumnSelections(spreadsheet);
                        clearAllRowSelections(spreadsheet);
                        window.gasImportsState.lastTableSignature = tableSignature;
                    }
                    
                    if (spreadsheet.dataset.gasImportsEnhanced === 'true' && !signatureChanged) {
                        return;
                    }

                    spreadsheet.dataset.gasImportsEnhanced = 'true';
                    
                    if (spreadsheet._gasImportsClickHandler) {
                        spreadsheet.removeEventListener('click', spreadsheet._gasImportsClickHandler, true);
                    }
                    
                    const clickHandler = function(event) {
                        const clickedSpreadsheet = event.target.closest('.dash-spreadsheet-container') || spreadsheet;
                        if (!clickedSpreadsheet) return;
                        
                        let header = event.target.closest('th[data-dash-column]');
                        
                        if (!header) {
                            const thead = event.target.closest('thead');
                            if (thead) {
                                const allHeaders = thead.querySelectorAll('th[data-dash-column]');
                                for (let h of allHeaders) {
                                    if (h.contains(event.target) || h === event.target) {
                                        header = h;
                                        break;
                                    }
                                }
                            }
                        }
                        
                        if (header) {
                            event.stopPropagation();
                            
                            const columnId = header.getAttribute('data-dash-column');
                            if (!columnId || columnId === 'Month') return;
                            
                            const headerRow = header.closest('tr');
                            const thead = header.closest('thead');
                            let headerIndex = -1;
                            let headerRows = [];
                            
                            // Get all header rows - try multiple methods
                            if (thead) {
                                headerRows = Array.from(thead.querySelectorAll('tr'));
                            } else {
                                // Fallback: find header rows in the spreadsheet
                                headerRows = Array.from(clickedSpreadsheet.querySelectorAll('tr')).filter(tr => 
                                    tr.querySelector('th') !== null
                                );
                            }
                            
                            // Filter to rows that actually contain column headers (not just any th)
                            const dataHeaderRows = headerRows.filter(tr => tr.querySelector('th[data-dash-column]') !== null);
                            
                            if (headerRow) {
                                headerIndex = dataHeaderRows.indexOf(headerRow);
                                if (headerIndex === -1) {
                                    // Try with all header rows if not found in data header rows
                                    headerIndex = headerRows.indexOf(headerRow);
                                }
                            }
                            
                            // Use data header rows for calculations
                            const totalHeaderRows = dataHeaderRows.length;
                            const isBottomHeader = (headerIndex >= 0 && totalHeaderRows > 0 && headerIndex === totalHeaderRows - 1);
                            const isTopHeader = (headerIndex === 0);
                            
                            const selectionKey = columnId + '_' + headerIndex;
                            const alreadySelected = (window.gasImportsState && window.gasImportsState.selectedColumnId === selectionKey);
                            
                            clearAllColumnSelections(clickedSpreadsheet);
                            clearAllRowSelections(clickedSpreadsheet);
                            
                            if (alreadySelected) {
                                if (window.gasImportsState) {
                                    window.gasImportsState.selectedColumnId = null;
                                }
                                return false;
                            }
                            
                            if (window.gasImportsState) {
                                window.gasImportsState.selectedColumnId = selectionKey;
                            }
                            
                            if (isTopHeader) {
                                // Top header - find all columns under this header
                                const topHeaderText = header.textContent.trim();
                                const columnIds = new Set();
                                
                                // Primary method: Use columns metadata to find matching columns
                                if (columns) {
                                    const matchingColumns = columns.filter(c => 
                                        c.name && c.name[0] === topHeaderText && c.id !== 'Month'
                                    );
                                    matchingColumns.forEach(col => {
                                        columnIds.add(col.id);
                                    });
                                }
                                
                                // Enhanced fallback: use colspan and comprehensive position detection
                                if (columnIds.size === 0) {
                                    const colspan = header.getAttribute('colspan') || header.colSpan;
                                    const spanCount = colspan ? parseInt(colspan) : 1;
                                    
                                    if (spanCount > 1) {
                                        // Method 1: Position-based detection using header row structure
                                        const topRow = dataHeaderRows[0];
                                        const allTopRowCells = Array.from(topRow.querySelectorAll('th'));
                                        let clickedCellIndex = -1;
                                        
                                        // Find the exact position of clicked header
                                        for (let i = 0; i < allTopRowCells.length; i++) {
                                            if (allTopRowCells[i] === header) {
                                                clickedCellIndex = i;
                                                break;
                                            }
                                        }
                                        
                                        if (clickedCellIndex >= 0) {
                                            // Calculate data column start position
                                            let dataColumnStart = 0;
                                            for (let i = 0; i < clickedCellIndex; i++) {
                                                const cell = allTopRowCells[i];
                                                const cellColId = cell.getAttribute('data-dash-column');
                                                if (cellColId === 'Month') continue;
                                                const cellColspan = parseInt(cell.getAttribute('colspan') || cell.colSpan || '1');
                                                dataColumnStart += cellColspan;
                                            }
                                            
                                            // Get ordered column IDs from bottom row headers
                                            const bottomRow = dataHeaderRows[dataHeaderRows.length - 1];
                                            if (bottomRow) {
                                                const allBottomHeaders = Array.from(bottomRow.querySelectorAll('th[data-dash-column]'));
                                                const dataColumnHeaders = allBottomHeaders.filter(h => {
                                                    const colId = h.getAttribute('data-dash-column');
                                                    return colId && colId !== 'Month';
                                                });
                                                
                                                // Add columns in the span range
                                                for (let i = dataColumnStart; i < dataColumnStart + spanCount && i < dataColumnHeaders.length; i++) {
                                                    const colId = dataColumnHeaders[i].getAttribute('data-dash-column');
                                                    if (colId) {
                                                        columnIds.add(colId);
                                                    }
                                                }
                                            }
                                        }
                                        
                                        // Method 2: If still no columns found, try visual bounds detection
                                        if (columnIds.size === 0) {
                                            try {
                                                const headerRect = header.getBoundingClientRect();
                                                const headerLeft = headerRect.left;
                                                const headerRight = headerRect.right;
                                                
                                                const bottomRow = dataHeaderRows[dataHeaderRows.length - 1];
                                                if (bottomRow) {
                                                    const allBottomHeaders = Array.from(bottomRow.querySelectorAll('th[data-dash-column]'));
                                                    
                                                    allBottomHeaders.forEach(bottomHeader => {
                                                        const colId = bottomHeader.getAttribute('data-dash-column');
                                                        if (colId && colId !== 'Month') {
                                                            const bottomRect = bottomHeader.getBoundingClientRect();
                                                            const bottomCenter = bottomRect.left + (bottomRect.width / 2);
                                                            
                                                            // Check if this bottom header is within the bounds of the top header
                                                            if (bottomCenter >= headerLeft - 5 && bottomCenter <= headerRight + 5) {
                                                                columnIds.add(colId);
                                                            }
                                                        }
                                                    });
                                                    
                                                }
                                            } catch (e) {
                                                // Visual bounds detection failed, continue
                                            }
                                        }
                                    } else {
                                        // Single column header
                                        columnIds.add(columnId);
                                    }
                                }
                                
                                // Fallback: if still no columns found, try to find by header text matching
                                if (columnIds.size === 0) {
                                    // Look for any headers in lower levels that might be related
                                    const allHeaders = clickedSpreadsheet.querySelectorAll('th[data-dash-column]');
                                    allHeaders.forEach(h => {
                                        const colId = h.getAttribute('data-dash-column');
                                        if (colId && colId !== 'Month') {
                                            // Check if this header is visually under the clicked header
                                            try {
                                                const hRect = h.getBoundingClientRect();
                                                const headerRect = header.getBoundingClientRect();
                                                
                                                if (hRect.top > headerRect.top && 
                                                    hRect.left >= headerRect.left - 10 && 
                                                    hRect.right <= headerRect.right + 10) {
                                                    columnIds.add(colId);
                                                }
                                            } catch (e) {
                                                // Ignore positioning errors
                                            }
                                        }
                                    });
                                }
                                
                                // Highlight clicked header
                                header.classList.add('column-selected');
                                header.style.backgroundColor = '#b3d9ff';
                                header.style.color = '#1b365d';
                                header.style.fontWeight = 'bold';
                                
                                // Highlight child headers and data cells
                                if (columnIds.size > 0) {
                                    columnIds.forEach(colId => {
                                        // Highlight ALL headers with this column ID (including second-level headers)
                                        const childHeaders = clickedSpreadsheet.querySelectorAll(`th[data-dash-column="${colId}"]`);
                                        childHeaders.forEach(childHeader => {
                                            childHeader.classList.add('column-selected');
                                            childHeader.style.backgroundColor = '#b3d9ff';
                                            childHeader.style.color = '#1b365d';
                                            childHeader.style.fontWeight = 'bold';
                                        });
                                        
                                        const dataCells = clickedSpreadsheet.querySelectorAll(`td[data-dash-column="${colId}"]`);
                                        dataCells.forEach(cell => {
                                            cell.classList.add('column-cell-selected');
                                            cell.style.backgroundColor = '#b3d9ff';
                                            cell.style.fontWeight = '600';
                                            cell.style.color = '#1b365d';
                                            cell.style.opacity = '1';
                                        });
                                    });
                                    
                                    clickedSpreadsheet.classList.add('column-selection-active');
                                    
                                    // Dim other columns
                                    const allDataCells = clickedSpreadsheet.querySelectorAll('td[data-dash-column]:not([data-dash-column="Month"])');
                                    allDataCells.forEach(cell => {
                                        const cellColId = cell.getAttribute('data-dash-column');
                                        if (!columnIds.has(cellColId)) {
                                            cell.style.opacity = '0.3';
                                        }
                                    });
                                }
                            } else {
                                // Bottom header - single column
                                header.classList.add('column-selected');
                                header.style.backgroundColor = '#b3d9ff';
                                header.style.color = '#1b365d';
                                header.style.fontWeight = 'bold';
                                
                                const columnCells = clickedSpreadsheet.querySelectorAll(`td[data-dash-column="${columnId}"]`);
                                columnCells.forEach(cell => {
                                    cell.classList.add('column-cell-selected');
                                    cell.style.backgroundColor = '#b3d9ff';
                                    cell.style.fontWeight = '600';
                                    cell.style.color = '#1b365d';
                                    cell.style.opacity = '1';
                                });
                                
                                clickedSpreadsheet.classList.add('column-selection-active');
                                
                                const allDataCells = clickedSpreadsheet.querySelectorAll('td[data-dash-column]:not([data-dash-column="Month"])');
                                allDataCells.forEach(cell => {
                                    if (!cell.classList.contains('column-cell-selected')) {
                                        cell.style.opacity = '0.3';
                                    }
                                });
                            }
                            return false;
                        }
                        
                        // Handle Month cell clicks for row highlighting
                        const monthCell = event.target.closest('td[data-dash-column="Month"]');
                        if (monthCell) {
                            event.stopPropagation();
                            const cellValue = getCellValue(monthCell);
                            const row = monthCell.closest('tr');
                            if (!row) return;
                            
                            const rowIndex = row.getAttribute('data-dash-row') || Array.from(row.parentNode.children).indexOf(row).toString();

                            clearAllColumnSelections(clickedSpreadsheet);
                            
                            if (window.gasImportsState && window.gasImportsState.selectedRowIndex === ('Month_' + rowIndex + '_' + cellValue)) {
                                clearAllRowSelections(clickedSpreadsheet);
                                window.gasImportsState.selectedRowIndex = null;
                                return;
                            }

                            clearAllRowSelections(clickedSpreadsheet);
                            
                            const allRows = Array.from(clickedSpreadsheet.querySelectorAll('tbody tr'));
                            const currentRowIndex = allRows.indexOf(row);
                            
                            let startIndex = currentRowIndex;
                            let firstLabelCell = monthCell;

                            if (cellValue === "") {
                                for (let i = currentRowIndex; i >= 0; i--) {
                                    const cell = allRows[i].querySelector('td[data-dash-column="Month"]');
                                    if (getCellValue(cell) !== "") {
                                        startIndex = i;
                                        firstLabelCell = cell;
                                        break;
                                    }
                                }
                            }
                            
                            let endIndex = allRows.length - 1;
                            for (let i = startIndex + 1; i < allRows.length; i++) {
                                const val = getCellValue(allRows[i].querySelector('td[data-dash-column="Month"]'));
                                if (val !== "") {
                                    endIndex = i - 1;
                                    break;
                                }
                            }

                            const targetRows = allRows.slice(startIndex, endIndex + 1);

                            targetRows.forEach(r => {
                                r.classList.add('row-selected');
                                r.querySelectorAll('td').forEach(c => {
                                    const cColId = c.getAttribute('data-dash-column');
                                    if (cColId !== 'Month') {
                                        c.classList.add('row-cell-selected');
                                        c.style.backgroundColor = '#b3d9ff';
                                        c.style.fontWeight = '600';
                                        c.style.opacity = '1';
                                    }
                                    if (c === firstLabelCell) {
                                        c.classList.add('row-cell-selected');
                                        c.style.backgroundColor = '#b3d9ff';
                                        c.style.fontWeight = 'bold';
                                        c.style.opacity = '1';
                                    }
                                });
                            });

                            allRows.forEach(r => {
                                if (!r.classList.contains('row-selected')) {
                                    r.querySelectorAll('td').forEach(c => c.style.opacity = '0.3');
                                }
                            });
                            clickedSpreadsheet.classList.add('row-selection-active');
                            window.gasImportsState.selectedRowIndex = 'Month_' + rowIndex + '_' + cellValue;
                            return;
                        }
                        
                        // Clear selections on data cell click
                        const cell = event.target.closest('td[data-dash-column]');
                        if (cell) {
                            const columnId = cell.getAttribute('data-dash-column');
                            if (columnId && columnId !== 'Month') {
                                clearAllColumnSelections(clickedSpreadsheet);
                                clearAllRowSelections(clickedSpreadsheet);
                                if (window.gasImportsState) {
                                    window.gasImportsState.selectedColumnId = null;
                                    window.gasImportsState.selectedRowIndex = null;
                                }
                            }
                        }
                    };
                    
                    spreadsheet._gasImportsClickHandler = clickHandler;
                    spreadsheet.addEventListener('click', spreadsheet._gasImportsClickHandler, true);
                }
                
                // Outside click handler
                if (!window.gasImportsOutsideClickHandler) {
                    window.gasImportsOutsideClickHandler = function(event) {
                        const tableEl = document.getElementById(tableId);
                        if (!tableEl) return;
                        const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                        if (!spreadsheet) return;
                        
                        if (!spreadsheet.contains(event.target)) {
                            clearAllColumnSelections(spreadsheet);
                            clearAllRowSelections(spreadsheet);
                            if (window.gasImportsState) {
                                window.gasImportsState.selectedColumnId = null;
                                window.gasImportsState.selectedRowIndex = null;
                            }
                        }
                    };
                    document.addEventListener('click', window.gasImportsOutsideClickHandler);
                }

                function tryEnhance() {
                    const tableEl = document.getElementById(tableId);
                    if (!tableEl) return false;
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    if (!spreadsheet) return false;
                    
                    if (spreadsheet.querySelectorAll('th').length === 0) return false;
                    
                    enhanceTable();
                    return true;
                }

                if (!tryEnhance()) {
                    setTimeout(() => {
                        if (!tryEnhance()) {
                            setTimeout(() => {
                                if (!tryEnhance()) {
                                    setTimeout(tryEnhance, 1000);
                                }
                            }, 300);
                        }
                    }, 100);
                }
                
                if (!window.gasImportsObserver) {
                    window.gasImportsObserver = new MutationObserver(function(mutations) {
                        const tableEl = document.getElementById(tableId);
                        if (tableEl) {
                            const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                            if (spreadsheet && spreadsheet.dataset.gasImportsEnhanced !== 'true') {
                                tryEnhance();
                            }
                        }
                    });
                    window.gasImportsObserver.observe(document.body, { childList: true, subtree: true });
                }

            } catch (err) { 
                console.error('Gas imports highlighting error:', err); 
            }
            return "";
        }
        """,
        Output('table-side-dummy-output', 'children'),
        Input('gas-imports-mix-table', 'data'),
        [State('gas-imports-mix-table', 'columns'),
         State('table-highlight-state', 'data')]
    )
