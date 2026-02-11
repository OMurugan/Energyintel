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

    is_date_mode = False
    active_mode = mode
    
    if mode == 'DATE':
        active_mode = 'MONTHLY'
        is_date_mode = True
        
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
    else:
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
                'short_label': final_label,
                'full_label': label 
            }
            
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
            
            line_x = current_global_x + slot_width
            
            if s_idx < len(sub_labels) - 1:
                month_separators.append(dict(
                    type="line", x0=line_x, x1=line_x, y0=0, y1=0.88, 
                    xref="x", yref="paper", line=dict(color="#999999", width=1),
                    layer='below'
                ))
            
            current_global_x += slot_width

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
LNG_COLOR = '#1f77b4'
PIPELINE_COLOR = '#ff7f0e'
TITLE_COLOR = '#fe5000'

COLOR_PALETTE = px.colors.qualitative.T10 + px.colors.qualitative.Alphabet

GAS_ORIGIN_COLORS = {
    'Algeria': '#1f77b4', 'Angola': '#636363', 'Australia': '#d55e00',
    'Belgium': '#1f77b4', 'Bolivia': '#808080', 'Brunei': '#d55e00',
    'Cameroon': '#8b4513', 'Canada': '#00008b', 'China': '#9370db',
    'Egypt': '#ff0000', 'Equatorial Guinea': '#90ee90', 'France': '#1f77b4',
    'Germany': '#636363', 'Guinea': '#2f4f4f', 'India': '#1f77b4',
    'Indonesia': '#808080', 'Iran': '#d55e00', 'Japan': '#8b4513',
    'Kazakhstan': '#00008b', 'Malaysia': '#9370db', 'Mauritania': '#ff0000',
    'Mozambique': '#ff0000', 'Myanmar': '#90ee90', 'Netherlands': '#1f77b4',
    'Nigeria': '#636363', 'Norway': '#2f4f4f', 'Oman': '#1f77b4',
    'Others': '#808080', 'Papua New Guinea': '#d55e00', 'Peru': '#8b4513',
    'Philippines': '#00008b', 'Qatar': '#5fbfbf', 'Republic of the Congo': '#ff0000',
    'Russia': '#90ee90', 'Saudi Arabia': '#1f77b4', 'Senegal': '#2f4f4f',
    'Singapore': '#808080', 'South Africa': '#808080', 'South Korea': '#00008b',
    'Spain': '#1f77b4', 'Thailand': '#808080', 'Timor-Leste': '#d55e00',
    'Trinidad and Tobago': '#8b4513', 'Turkey': '#00008b', 'Turkmenistan': '#5fbfbf',
    'United Arab Emirates': '#ff0000', 'United Kingdom': '#90ee90',
    'United States': '#1f77b4', 'Uzbekistan': '#636363'
}

def get_consistent_color_for_origin(origin):
    """Get a consistent color for a gas origin"""
    if origin in GAS_ORIGIN_COLORS:
        return GAS_ORIGIN_COLORS[origin]
    
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
    try:
        from core.data_helpers import execute_query
        rows = execute_query(query, params)
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"Database query error: {e}")
        return pd.DataFrame()

def create_layout():
    """Create the Asian Gas Imports Mix layout"""
    # Initial data for filters
    destination_query = """
    SELECT DISTINCT tr.target_country
    FROM dev.glng_gas_trade tr
    LEFT JOIN dev.dim_country co ON co.dim_country_id = tr.target_country_id
    WHERE LOWER(co.region) IN ('asia', 'oceania')
    AND tr.target_country IS NOT NULL AND TRIM(tr.target_country) <> ''
    ORDER BY tr.target_country;
    """
    destinations_df = load_data(destination_query)
    destinations = destinations_df['target_country'].tolist() if not destinations_df.empty else []

    origin_query = """
    SELECT DISTINCT tr.source_country
    FROM dev.glng_gas_trade tr
    LEFT JOIN dev.dim_country co ON co.dim_country_id = tr.target_country_id
    WHERE LOWER(co.region) IN ('asia', 'oceania')
    AND tr.source_country IS NOT NULL AND TRIM(tr.source_country) <> ''
    ORDER BY tr.source_country;
    """
    origins_df = load_data(origin_query)
    origins = origins_df['source_country'].tolist() if not origins_df.empty else []

    date_range_query = """
    SELECT MIN(tr.date) as min_date, MAX(tr.date) as max_date
    FROM dev.glng_gas_trade tr
    LEFT JOIN dev.dim_country co ON co.dim_country_id = tr.target_country_id
    WHERE LOWER(co.region) IN ('asia', 'oceania');
    """
    date_range_df = load_data(date_range_query)
    min_date_val = date_range_df['min_date'].iloc[0] if not date_range_df.empty else pd.Timestamp('2019-01-01')
    max_date_val = date_range_df['max_date'].iloc[0] if not date_range_df.empty else pd.Timestamp.now()

    return html.Div([
        html.Div([
            # Left/Center: Charts Area
            html.Div([
                # Row 1: Two Charts Side by Side
                html.Div([
                    # Chart 1: LNG vs Pipeline Imports (Line Chart)
                    html.Div([
                        html.Div([
                            html.H2("LNG vs. Pipeline Imports (Bcm) - All",
                                    id='gas-asia-chart1-title',
                                    style={'color': TITLE_COLOR, 'fontSize': '18px', 'marginBottom': '0px', 'fontFamily': 'Lato, sans-serif'}),
                            html.Button("Export to CSV", id="gas-asia-export-chart1-btn", n_clicks=0, style={
                                "backgroundColor": "white", "color": "#2c3e50", "border": "1px solid #dee2e6",
                                "padding": "6px 12px", "borderRadius": "4px", "cursor": "pointer",
                                "fontSize": "12px", "fontWeight": "normal",
                            })
                        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
                        
                        # Chart 1 Granularity Controls
                        html.Div([
                            html.Div([
                                html.Span("Year of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                                html.Button('+', id='gas-asia-chart1-toggle-year-btn', n_clicks=0, style={
                                    'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                    'backgroundColor': 'white', 'color': '#add8e6', 'borderRadius': '3px', 'cursor': 'pointer',
                                    'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                                })
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                            
                            html.Div([
                                html.Span("Quarter of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                                html.Button('+', id='gas-asia-chart1-toggle-quarter-btn', n_clicks=0, style={
                                    'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                    'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                    'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                                })
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                            
                            html.Div([
                                html.Span("Month of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                                html.Button('+', id='gas-asia-chart1-toggle-month-btn', n_clicks=0, style={
                                    'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                    'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                    'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                                })
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                            
                            html.Div([
                                html.Span("Day of Year", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                                html.Button('+', id='gas-asia-chart1-toggle-day-btn', n_clicks=0, style={
                                    'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                    'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                    'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                                })
                            ], style={'display': 'flex', 'alignItems': 'center'})
                        ], style={
                            'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#f8f9fa', 
                            'padding': '5px 10px', 'borderRadius': '4px', 'marginBottom': '0px',
                            'position': 'absolute', 'top': '45px', 'left': '10px', 'zIndex': '10'
                        }),

                        dcc.Loading(dcc.Graph(id='gas-asia-chart-1', config={'displayModeBar': False}, figure={'layout': {}, 'data': []}))
                    ], style={'width': '45%', 'marginRight': '10px', 'backgroundColor': 'white', 'padding': '10px', 'position': 'relative'}),

                    # Chart 2: All Imports by Origin (Bar Chart)
                    html.Div([
                        html.Div([
                            html.H2("All Imports by Origin (Bcm) - All",
                                    id='gas-asia-chart2-title',
                                    style={'color': TITLE_COLOR, 'fontSize': '18px', 'marginBottom': '0px', 'fontFamily': 'Lato, sans-serif'}),
                            html.Button("Export to CSV", id="gas-asia-export-chart2-btn", n_clicks=0, style={
                                "backgroundColor": "white", "color": "#2c3e50", "border": "1px solid #dee2e6",
                                "padding": "6px 12px", "borderRadius": "4px", "cursor": "pointer",
                                "fontSize": "12px", "fontWeight": "normal",
                            })
                        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
                        
                        # Chart 2 Granularity Controls
                        html.Div([
                            html.Div([
                                html.Span("Year of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                                html.Button('+', id='gas-asia-chart2-toggle-year-btn', n_clicks=0, style={
                                    'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                    'backgroundColor': 'white', 'color': '#add8e6', 'borderRadius': '3px', 'cursor': 'pointer',
                                    'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                                })
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                            
                            html.Div([
                                html.Span("Quarter of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                                html.Button('+', id='gas-asia-chart2-toggle-quarter-btn', n_clicks=0, style={
                                    'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                    'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                    'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                                })
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                            
                            html.Div([
                                html.Span("Month of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                                html.Button('+', id='gas-asia-chart2-toggle-month-btn', n_clicks=0, style={
                                    'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                    'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                    'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                                })
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                            
                            html.Div([
                                html.Span("Day of Year", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                                html.Button('+', id='gas-asia-chart2-toggle-day-btn', n_clicks=0, style={
                                    'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                    'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                    'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                                })
                            ], style={'display': 'flex', 'alignItems': 'center'})
                        ], style={
                            'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#f8f9fa', 
                            'padding': '5px 10px', 'borderRadius': '4px', 'marginBottom': '0px',
                            'position': 'absolute', 'top': '45px', 'left': '10px', 'zIndex': '10'
                        }),

                        dcc.Loading(dcc.Graph(id='gas-asia-chart-2', config={'displayModeBar': False}, figure={'layout': {}, 'data': []}))
                    ], style={'width': '55%', 'backgroundColor': 'white', 'padding': '10px', 'position': 'relative'}),
                ], style={'display': 'flex', 'marginBottom': '30px'}),

                # Row 2: Flow Type Bar Chart
                html.Div([
                    html.Div([
                        html.H2("Pipeline vs. LNG Imports - All",
                                id='gas-asia-chart3-title',
                                style={'color': TITLE_COLOR, 'fontSize': '18px', 'marginBottom': '0px', 'fontFamily': 'Lato, sans-serif'}),
                        html.Button("Export to CSV", id="gas-asia-export-chart3-btn", n_clicks=0, style={
                            "backgroundColor": "white", "color": "#2c3e50", "border": "1px solid #dee2e6",
                            "padding": "6px 12px", "borderRadius": "4px", "cursor": "pointer",
                            "fontSize": "12px", "fontWeight": "normal",
                        })
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
                    
                    # Chart 3 Granularity Controls
                    html.Div([
                        html.Div([
                            html.Span("Year of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                            html.Button('+', id='gas-asia-chart3-toggle-year-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#add8e6', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Quarter of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                            html.Button('+', id='gas-asia-chart3-toggle-quarter-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Month of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                            html.Button('+', id='gas-asia-chart3-toggle-month-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Day of Year", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                            html.Button('+', id='gas-asia-chart3-toggle-day-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center'})
                    ], style={
                        'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#f8f9fa', 
                        'padding': '5px 10px', 'borderRadius': '4px', 'marginBottom': '0px',
                        'position': 'relative', 'top': '0px', 'left': '0px', 'zIndex': '10'
                    }),

                    dcc.Loading(dcc.Graph(id='gas-asia-chart-3', config={'displayModeBar': False}, figure={'layout': {}, 'data': []}))
                ], style={'marginBottom': '0px', 'backgroundColor': 'white', 'padding': '10px', 'position': 'relative'}),

            ], style={'flex': '1', 'padding': '10px', 'minWidth': '0'}),

            # Right Side Panel: Filters
            html.Div([
                html.Div([
                    html.Div([
                        html.Label("Flow Type", style={'fontWeight': 'normal', 'fontSize': '13px', 'color': '#333'}),
                        dcc.RadioItems(
                            id='gas-asia-flow-type-filter',
                            options=[
                                {'label': ' All', 'value': 'All'},
                                {'label': ' LNG', 'value': 'LNG'},
                                {'label': ' Pipeline', 'value': 'Pipeline'}
                            ],
                            value='All',
                            labelStyle={'display': 'block', 'fontSize': '11px', 'marginBottom': '2px'},
                            style={'marginBottom': '20px'}
                        ),
                    ]),

                    html.Div([
                        html.Label("Unit", style={'fontWeight': 'normal', 'fontSize': '13px', 'color': '#333'}),
                        dcc.RadioItems(
                            id='gas-asia-unit-filter',
                            options=[
                                {'label': ' Bcm', 'value': 'Bcm'},
                                {'label': ' GWh', 'value': 'GWh'}
                            ],
                            value='Bcm',
                            labelStyle={'display': 'block', 'fontSize': '11px', 'marginBottom': '2px'},
                            style={'marginBottom': '20px'}
                        ),
                    ]),

                    html.Div([
                        html.Label("Destination", style={'fontWeight': 'normal', 'fontSize': '13px', 'color': '#333'}),
                        dcc.Dropdown(
                            id='gas-asia-destination-dropdown',
                            options=[{'label': 'All', 'value': 'All'}] + [{'label': d, 'value': d} for d in destinations],
                            value='All',
                            clearable=False,
                            style={'fontSize': '12px'}
                        ),
                    ], style={'marginBottom': '15px'}),

                    html.Div([
                        html.Label("Start Date", style={'fontWeight': 'normal', 'fontSize': '12px', 'color': '#333'}),
                        dcc.Input(
                            id='gas-asia-start-date-picker',
                            type='text',
                            value=min_date_val.strftime('%Y-%m-%d') if pd.notnull(min_date_val) else '2019-01-01',
                            placeholder='YYYY-MM-DD',
                            min='2019-01-01',
                            max='2030-12-31',
                            style={'width': '100%', 'padding': '4px', 'fontSize': '12px', 'border': '1px solid #ccc', 'borderRadius': '4px'}
                        ),
                    ], style={'marginBottom': '10px'}),

                    html.Div([
                        html.Label("End Date", style={'fontWeight': 'normal', 'fontSize': '12px', 'color': '#333'}),
                        dcc.Input(
                            id='gas-asia-end-date-picker',
                            type='text',
                            value=max_date_val.strftime('%Y-%m-%d') if pd.notnull(max_date_val) else datetime.now().strftime('%Y-%m-%d'),
                            placeholder='YYYY-MM-DD',
                            min='2019-01-01',
                            max='2030-12-31',
                            style={'width': '100%', 'padding': '4px', 'fontSize': '12px', 'border': '1px solid #ccc', 'borderRadius': '4px'}
                        ),
                    ], style={'marginBottom': '20px'}),

                    html.Div([
                        html.Label("Origin", style={'fontWeight': 'normal', 'fontSize': '13px', 'color': '#333'}),
                        html.Div(id='gas-asia-origin-legend-container', style={
                            'maxHeight': '550px', 'overflowY': 'auto', 'border': '1px solid #eee',
                            'padding': '8px', 'backgroundColor': 'white'
                        })
                    ], style={'marginBottom': '20px'}),

                    dcc.Store(id='gas-asia-selected-origins-store'),
                    dcc.Store(id='gas-asia-chart1-agg-state', data='MONTHLY'),
                    dcc.Store(id='gas-asia-chart2-agg-state', data='MONTHLY'),
                    dcc.Store(id='gas-asia-chart3-agg-state', data='YEARLY'),
                    dcc.Store(id='gas-asia-table-agg-state', data='MONTHLY'),
                    dcc.Store(id='gas-asia-chart1-selection-store', data=None),
                    dcc.Store(id='gas-asia-chart2-selection-store', data=None),
                    dcc.Store(id='gas-asia-chart3-selection-store', data=None),
                    dcc.Download(id="gas-asia-download-chart1-csv"),
                    dcc.Download(id="gas-asia-download-chart2-csv"),
                    dcc.Download(id="gas-asia-download-chart3-csv"),
                    dcc.Download(id="gas-asia-download-table-csv"),

                ], style={'padding': '15px', 'backgroundColor': '#fcfcfc', 'borderLeft': '1px solid #eee', 'minHeight': '100vh'})
            ], style={'width': '210px', 'position': 'sticky', 'top': '0'})

        ], style={'display': 'flex', 'flexDirection': 'row', 'width': '100%', 'maxWidth': '100%', 'margin': '0'}),
        
        # Row 3: Data Table (Full Width) - Outside the flex container
        html.Div([
            html.Div([
                html.H2("Monthly LNG and Pipeline Imports by Destination (Mcm)",
                        style={'color': TITLE_COLOR, 'fontSize': '18px', 'marginBottom': '0px', 'fontFamily': 'Lato, sans-serif'}),
                html.Button("Export to CSV", id="gas-asia-export-table-btn", n_clicks=0, style={
                    "backgroundColor": "white", "color": "#2c3e50", "border": "1px solid #dee2e6",
                    "padding": "6px 12px", "borderRadius": "4px", "cursor": "pointer",
                    "fontSize": "12px", "fontWeight": "normal",
                })
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
            
            # Table Granularity Controls
            html.Div([
                html.Div([
                    html.Span("Year of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                    html.Button('+', id='gas-asia-table-toggle-year-btn', n_clicks=0, style={
                        'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                        'backgroundColor': 'white', 'color': '#add8e6', 'borderRadius': '3px', 'cursor': 'pointer',
                        'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                    })
                ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                
                html.Div([
                    html.Span("Quarter of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                    html.Button('+', id='gas-asia-table-toggle-quarter-btn', n_clicks=0, style={
                        'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                        'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                        'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                    })
                ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                
                html.Div([
                    html.Span("Month of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                    html.Button('+', id='gas-asia-table-toggle-month-btn', n_clicks=0, style={
                        'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                        'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                        'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                    })
                ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                
                html.Div([
                    html.Span("Day of Year", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                    html.Button('+', id='gas-asia-table-toggle-day-btn', n_clicks=0, style={
                        'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                        'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                        'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                    })
                ], style={'display': 'flex', 'alignItems': 'center'})
            ], style={
                'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#f8f9fa', 
                'padding': '5px 10px', 'borderRadius': '4px', 'marginBottom': '10px',
            }),
            
            dcc.Loading(
                id="loading-gas-table",
                type="circle",
                color="#f45d2d",
                children=dash_table.DataTable(
                    id='gas-asia-imports-mix-table',
                    merge_duplicate_headers=True,
                    fixed_rows={'headers': True},
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
                        'borderLeft': '1px solid #ddd',
                        'borderRight': '1px solid #ddd',
                        'borderTop': '1px solid #ddd',
                        'borderBottom': '1px solid #ddd',
                        'color': '#333',
                        'height': '25px',
                        'padding': '2px'
                    },
                    style_cell={
                        'padding': '0px 5px',
                        'fontSize': '11px',
                        'fontFamily': 'Arial, sans-serif',
                        'borderLeft': '1px solid #ddd',
                        'borderRight': '1px solid #ddd',
                        'borderTop': 'none',
                        'borderBottom': '1px solid #e0e0e0',
                        'minWidth': '70px',
                        'backgroundColor': '#fff',
                        'color': '#777',
                        'height': 'auto',
                        'textAlign': 'right'
                    },
                    style_cell_conditional=[
                        {'if': {'column_id': 'Year of Date'}, 'textAlign': 'center', 'minWidth': '60px'},
                        {'if': {'column_id': 'Quarter of Date'}, 'textAlign': 'center', 'minWidth': '50px'},
                        {'if': {'column_id': 'Month of Date'}, 'textAlign': 'left', 'minWidth': '100px'},
                        {'if': {'column_id': 'Day of Date'}, 'textAlign': 'center', 'minWidth': '50px'}
                    ],
                    style_data_conditional=[
                        {'if': {'row_index': 'odd'}, 'backgroundColor': '#f2f2f2'}
                    ],
                    style_as_list_view=False,
                    sort_action='native',
                    filter_action='native',
                    tooltip_duration=None
                )
            ),
            
            html.P("Source: Energy Intelligence",
                   style={'fontSize': '10px', 'color': '#666', 'fontStyle': 'italic', 'paddingLeft': '10px', 'marginTop': '10px'})
        ], style={'padding': '20px', 'backgroundColor': 'white', 'width': '100%'})
        
    ], style={'backgroundColor': '#ffffff', 'fontFamily': 'Lato, sans-serif'})

def register_callbacks(dash_app, server):
    
    # Clientside callback to convert text inputs to date inputs (bypasses Dash validation)
    dash_app.clientside_callback(
        """
        function() {
            setTimeout(function() {
                const startInput = document.getElementById('gas-asia-start-date-picker');
                const endInput = document.getElementById('gas-asia-end-date-picker');
                
                if (startInput && startInput.type === 'text') {
                    startInput.type = 'date';
                    const maxDate = new Date().toISOString().split('T')[0];
                    startInput.max = maxDate;
                }
                
                if (endInput && endInput.type === 'text') {
                    endInput.type = 'date';
                    const maxDate = new Date().toISOString().split('T')[0];
                    endInput.max = maxDate;
                }
            }, 100);
            return null;
        }
        """,
        Output('gas-asia-chart1-selection-store', 'data', allow_duplicate=True),
        Input('gas-asia-start-date-picker', 'id'),
        prevent_initial_call='initial_duplicate'
    )
    
    # Helper function for query parameters
    def get_query_params(destination, start_date, end_date, origins, flow_type, unit):
        today = datetime.now()
        def parse_dt(d_str, default):
            if not d_str: return default
            try: return pd.to_datetime(d_str, format='%Y-%m-%d')
            except:
                try: return pd.to_datetime(d_str, dayfirst=True)
                except: return default

        start_dt = parse_dt(start_date, pd.to_datetime('2019-01-01'))
        end_dt = parse_dt(end_date, today)
        if end_dt > today: end_dt = today

        where_clause = "WHERE tr.date >= :start AND tr.date <= :end AND tr.unit = 'Mcm'"
        params = {'start': start_dt, 'end': end_dt}
        
        # Region filter for Asia/Oceania
        region_clause = " AND LOWER(co.region) IN ('asia', 'oceania')"
        
        # Destination filter
        dest_clause = ""
        if destination and destination != 'All':
            dest_clause = " AND tr.target_country = :destination"
            params['destination'] = destination
            
        # Origin filter
        of = [o for o in (origins or []) if o != 'All']
        
        # Flow type filter
        flow_filtered = []
        if flow_type == 'All':
            flow_filtered = ['lng', 'natural gas']
        elif flow_type == 'LNG':
            flow_filtered = ['lng']
        elif flow_type == 'Pipeline':
            flow_filtered = ['natural gas']
        
        # Unit conversion
        if unit == 'GWh':
            scale = 10.55  # Mcm to GWh conversion
        else:
            scale = 1000.0  # Mcm to Bcm conversion

        return where_clause, region_clause, dest_clause, params, of, flow_filtered, scale

    # Chart 1 Click Handler for highlighting
    @dash_app.callback(
        [Output('gas-asia-chart1-selection-store', 'data'),
         Output('gas-asia-chart-1', 'clickData')],
        [Input('gas-asia-chart-1', 'clickData'),
         Input('gas-asia-flow-type-filter', 'value'),
         Input('gas-asia-unit-filter', 'value'),
         Input('gas-asia-destination-dropdown', 'value')],
        [State('gas-asia-chart1-selection-store', 'data')],
        prevent_initial_call=True
    )
    def handle_chart1_click(click_data, flow_type, unit, destination, current_selection):
        """Handle chart 1 clicks for line highlighting"""
        trigger_id = ctx.triggered_id if ctx.triggered else None
        
        # Reset selection on filter changes
        if trigger_id in ['gas-asia-flow-type-filter', 'gas-asia-unit-filter', 'gas-asia-destination-dropdown']:
            return None, None
        
        if not click_data or 'points' not in click_data:
            return no_update, no_update
        
        point = click_data['points'][0]
        clicked_flow = point.get('customdata', [None])[0] if 'customdata' in point else None
        
        if not clicked_flow:
            return no_update, no_update
        
        # Toggle selection - if same flow clicked, deselect
        if current_selection and current_selection.get('flow') == clicked_flow:
            return None, None
        
        return {'flow': clicked_flow}, None

    # Chart 2 Click Handler for bar highlighting
    @dash_app.callback(
        [Output('gas-asia-chart2-selection-store', 'data'),
         Output('gas-asia-chart-2', 'clickData')],
        [Input('gas-asia-chart-2', 'clickData'),
         Input('gas-asia-destination-dropdown', 'value'),
         Input('gas-asia-selected-origins-store', 'data'),
         Input('gas-asia-unit-filter', 'value')],
        [State('gas-asia-chart2-selection-store', 'data')],
        prevent_initial_call=True
    )
    def handle_chart2_click(click_data, destination, origins, unit, current_selection):
        """Handle chart 2 clicks for bar highlighting"""
        trigger_id = ctx.triggered_id if ctx.triggered else None
        
        # Reset selection on filter changes
        if trigger_id in ['gas-asia-destination-dropdown', 'gas-asia-selected-origins-store', 'gas-asia-unit-filter']:
            return None, None
        
        if not click_data or 'points' not in click_data:
            return no_update, no_update
        
        point = click_data['points'][0]
        clicked_origin = point.get('customdata', [None, None])[0] if 'customdata' in point else None
        clicked_date = point.get('customdata', [None, None])[1] if 'customdata' in point and len(point.get('customdata', [])) > 1 else None
        
        if not clicked_origin or not clicked_date:
            return no_update, no_update
        
        # Toggle selection - if same bar clicked, deselect
        if current_selection and current_selection.get('origin') == clicked_origin and current_selection.get('date') == clicked_date:
            return None, None
        
        return {'origin': clicked_origin, 'date': str(clicked_date)}, None

    # Chart 3 Click Handler for bar highlighting
    @dash_app.callback(
        [Output('gas-asia-chart3-selection-store', 'data'),
         Output('gas-asia-chart-3', 'clickData')],
        [Input('gas-asia-chart-3', 'clickData'),
         Input('gas-asia-destination-dropdown', 'value'),
         Input('gas-asia-flow-type-filter', 'value'),
         Input('gas-asia-unit-filter', 'value')],
        [State('gas-asia-chart3-selection-store', 'data')],
        prevent_initial_call=True
    )
    def handle_chart3_click(click_data, destination, flow_type, unit, current_selection):
        """Handle chart 3 clicks for bar highlighting"""
        trigger_id = ctx.triggered_id if ctx.triggered else None
        
        # Reset selection on filter changes
        if trigger_id in ['gas-asia-destination-dropdown', 'gas-asia-flow-type-filter', 'gas-asia-unit-filter']:
            return None, None
        
        if not click_data or 'points' not in click_data:
            return no_update, no_update
        
        point = click_data['points'][0]
        # customdata should be [flow_type, period]
        clicked_flow = point.get('customdata', [None, None])[0] if 'customdata' in point else None
        clicked_period = point.get('customdata', [None, None])[1] if 'customdata' in point and len(point.get('customdata', [])) > 1 else None
        
        if not clicked_flow or not clicked_period:
            return no_update, no_update
        
        # Toggle selection - if same bar clicked, deselect
        if current_selection and current_selection.get('flow') == clicked_flow and current_selection.get('period') == clicked_period:
            return None, None
        
        return {'flow': clicked_flow, 'period': str(clicked_period)}, None

    # Combined callback to handle legend and origin updates
    @dash_app.callback(
        [Output('gas-asia-origin-legend-container', 'children'),
         Output('gas-asia-selected-origins-store', 'data')],
        [Input('gas-asia-destination-dropdown', 'value'),
         Input({'type': 'gas-asia-origin-legend-item', 'index': ALL}, 'n_clicks')],
        [State('gas-asia-selected-origins-store', 'data')]
    )
    def update_origin_legend_and_selection(destination, n_clicks, current_selected):
        # Get available origins based on destination
        query = """
        SELECT DISTINCT source_country 
        FROM dev.glng_gas_trade tr
        LEFT JOIN dev.dim_country co ON co.dim_country_id = tr.target_country_id
        WHERE source_country IS NOT NULL AND TRIM(source_country) <> ''
        AND LOWER(co.region) IN ('asia', 'oceania')
        """
        params = {}
        if destination and destination != 'All':
            query += " AND tr.target_country = :destination"
            params['destination'] = destination
        query += " ORDER BY source_country;"
        df = load_data(query, params)
        origins = df['source_country'].tolist() if not df.empty else []
        
        # Determine what triggered the callback
        triggered_id = ctx.triggered_id
        
        # Handle destination change - reset selection to all origins
        if triggered_id == 'gas-asia-destination-dropdown':
            selected = ['All'] + origins
        # Handle legend click
        elif triggered_id and isinstance(triggered_id, dict) and triggered_id.get('type') == 'gas-asia-origin-legend-item':
            clicked_origin = triggered_id['index']
            selected = list(current_selected) if current_selected else ['All'] + origins
            
            if clicked_origin == 'All':
                # Keep current selection
                pass
            elif 'All' in selected:
                # If All is selected, switch to only clicked origin
                selected = [clicked_origin]
            elif clicked_origin in selected:
                # Deselect clicked origin
                if len(selected) > 1:
                    selected.remove(clicked_origin)
                else:
                    # If it's the only one, select all
                    selected = ['All'] + origins
            else:
                # Add clicked origin to selection
                selected.append(clicked_origin)
        else:
            # Initial load or other trigger
            selected = current_selected if current_selected else ['All'] + origins
        
        # Sync "All" logic
        all_possible = origins
        if 'All' in selected and len(selected) == 1:
            selected = ['All'] + all_possible
        elif set(selected).issuperset(set(all_possible)) and 'All' not in selected:
            selected = ['All'] + all_possible
        elif 'All' in selected and len(selected) > 1 and len(selected) < len(all_possible) + 1:
            selected = [s for s in selected if s != 'All']
        
        # Build legend items
        items = []
        for origin in origins:
            is_sel = origin in selected
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
            ], id={'type': 'gas-asia-origin-legend-item', 'index': origin}, 
               style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '4px', 'cursor': 'pointer'}))
               
        return items, selected
    
    # Update chart titles based on destination filter
    @dash_app.callback(
        [Output('gas-asia-chart1-title', 'children'),
         Output('gas-asia-chart2-title', 'children'),
         Output('gas-asia-chart3-title', 'children')],
        [Input('gas-asia-destination-dropdown', 'value'),
         Input('gas-asia-unit-filter', 'value')]
    )
    def update_chart_titles(destination, unit):
        """Update chart titles to include selected destination"""
        dest_text = destination if destination and destination != 'All' else 'All'
        
        title1 = f"LNG vs. Pipeline Imports ({unit}) - {dest_text}"
        title2 = f"All Imports by Origin ({unit}) - {dest_text}"
        title3 = f"Pipeline vs. LNG Imports - {dest_text}"
        
        return title1, title2, title3
    
    # Granularity Handlers
    @dash_app.callback(
        [Output('gas-asia-chart1-agg-state', 'data'),
         Output('gas-asia-chart1-toggle-year-btn', 'children'),
         Output('gas-asia-chart1-toggle-quarter-btn', 'children'),
         Output('gas-asia-chart1-toggle-month-btn', 'children'),
         Output('gas-asia-chart1-toggle-day-btn', 'children')],
        [Input('gas-asia-chart1-toggle-year-btn', 'n_clicks'),
         Input('gas-asia-chart1-toggle-quarter-btn', 'n_clicks'),
         Input('gas-asia-chart1-toggle-month-btn', 'n_clicks'),
         Input('gas-asia-chart1-toggle-day-btn', 'n_clicks')],
        [State('gas-asia-chart1-agg-state', 'data')]
    )
    def gas_asia_chart1_granularity_handler(y_c, q_c, m_c, d_c, current_gran):
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

    @dash_app.callback(
        [Output('gas-asia-chart2-agg-state', 'data'),
         Output('gas-asia-chart2-toggle-year-btn', 'children'),
         Output('gas-asia-chart2-toggle-quarter-btn', 'children'),
         Output('gas-asia-chart2-toggle-month-btn', 'children'),
         Output('gas-asia-chart2-toggle-day-btn', 'children')],
        [Input('gas-asia-chart2-toggle-year-btn', 'n_clicks'),
         Input('gas-asia-chart2-toggle-quarter-btn', 'n_clicks'),
         Input('gas-asia-chart2-toggle-month-btn', 'n_clicks'),
         Input('gas-asia-chart2-toggle-day-btn', 'n_clicks')],
        [State('gas-asia-chart2-agg-state', 'data')]
    )
    def gas_asia_chart2_granularity_handler(y_c, q_c, m_c, d_c, current_gran):
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

    @dash_app.callback(
        [Output('gas-asia-table-agg-state', 'data'),
         Output('gas-asia-table-toggle-year-btn', 'children'),
         Output('gas-asia-table-toggle-quarter-btn', 'children'),
         Output('gas-asia-table-toggle-month-btn', 'children'),
         Output('gas-asia-table-toggle-day-btn', 'children')],
        [Input('gas-asia-table-toggle-year-btn', 'n_clicks'),
         Input('gas-asia-table-toggle-quarter-btn', 'n_clicks'),
         Input('gas-asia-table-toggle-month-btn', 'n_clicks'),
         Input('gas-asia-table-toggle-day-btn', 'n_clicks')],
        [State('gas-asia-table-agg-state', 'data')]
    )
    def gas_asia_table_granularity_handler(y_c, q_c, m_c, d_c, current_gran):
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

    @dash_app.callback(
        [Output('gas-asia-chart3-agg-state', 'data'),
         Output('gas-asia-chart3-toggle-year-btn', 'children'),
         Output('gas-asia-chart3-toggle-quarter-btn', 'children'),
         Output('gas-asia-chart3-toggle-month-btn', 'children'),
         Output('gas-asia-chart3-toggle-day-btn', 'children')],
        [Input('gas-asia-chart3-toggle-year-btn', 'n_clicks'),
         Input('gas-asia-chart3-toggle-quarter-btn', 'n_clicks'),
         Input('gas-asia-chart3-toggle-month-btn', 'n_clicks'),
         Input('gas-asia-chart3-toggle-day-btn', 'n_clicks')],
        [State('gas-asia-chart3-agg-state', 'data')]
    )
    def gas_asia_chart3_granularity_handler(y_c, q_c, m_c, d_c, current_gran):
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

    # Chart 1: LNG vs Pipeline Line Chart with highlighting
    @dash_app.callback(
        Output('gas-asia-chart-1', 'figure'),
        [Input('gas-asia-destination-dropdown', 'value'),
         Input('gas-asia-start-date-picker', 'value'),
         Input('gas-asia-end-date-picker', 'value'),
         Input('gas-asia-flow-type-filter', 'value'),
         Input('gas-asia-unit-filter', 'value'),
         Input('gas-asia-chart1-agg-state', 'data'),
         Input('gas-asia-chart1-selection-store', 'data')]
    )
    def update_chart_1(destination, start_date, end_date, flow_type, unit, agg_mode, selection):
        try:
            where_clause, region_clause, dest_clause, params, _, flow_filtered, scale = get_query_params(
                destination, start_date, end_date, [], flow_type, unit
            )
            
            agg_mode = (agg_mode or 'MONTHLY').upper()
            
            if not flow_filtered:
                return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 
                                  'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 300}}
            
            time_sql = "DATE_TRUNC('month', tr.date)"
            if agg_mode == 'YEARLY':
                time_sql = "DATE_TRUNC('year', tr.date)"
            elif agg_mode == 'QUARTERLY':
                time_sql = "DATE_TRUNC('quarter', tr.date)"
            elif agg_mode == 'DATE':
                time_sql = "tr.date"
            
            c1_query = f"""
            WITH gas_data AS (
                SELECT
                    {time_sql} AS month_date,
                    CASE 
                        WHEN LOWER(tr.flow_type) = 'lng' THEN 'LNG'
                        WHEN LOWER(tr.flow_type) = 'natural gas' THEN 'Pipeline'
                    END AS "Flow Type",
                    ROUND(SUM(tr.value) / :scale, 4) AS "Value"
                FROM dev.glng_gas_trade tr
                LEFT JOIN dev.dim_country co ON co.dim_country_id = tr.target_country_id
                {where_clause} {region_clause} {dest_clause}
                AND LOWER(tr.flow_type) IN :flow_types
                GROUP BY {time_sql},
                    CASE 
                        WHEN LOWER(tr.flow_type) = 'lng' THEN 'LNG'
                        WHEN LOWER(tr.flow_type) = 'natural gas' THEN 'Pipeline'
                    END
            )
            SELECT month_date AS "Month of Date", "Flow Type", '{unit}' AS adjusted_unit, "Value"
            FROM gas_data
            ORDER BY month_date,
                CASE WHEN "Flow Type" = 'Pipeline' THEN 1 ELSE 2 END;
            """
            
            c1_df = load_data(c1_query, {**params, 'flow_types': tuple(flow_filtered), 'scale': scale})
            if c1_df.empty:
                return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 
                                  'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 350}}
            
            # Format display labels based on aggregation mode
            if agg_mode == 'YEARLY':
                c1_df['Display Date'] = pd.to_datetime(c1_df['Month of Date']).dt.year.astype(str)
            elif agg_mode == 'QUARTERLY':
                dt = pd.to_datetime(c1_df['Month of Date'])
                c1_df['Display Date'] = dt.dt.year.astype(str) + ' Q' + ((dt.dt.month - 1) // 3 + 1).astype(str)
            elif agg_mode == 'MONTHLY':
                dt = pd.to_datetime(c1_df['Month of Date'])
                c1_df['Display Date'] = dt.dt.strftime('%B %Y')
            elif agg_mode == 'DATE':
                dt = pd.to_datetime(c1_df['Month of Date'])
                c1_df['Display Date'] = dt.dt.strftime('%B %d, %Y')
            
            # Keep Month of Date as datetime for proper sorting
            c1_df['Month of Date'] = pd.to_datetime(c1_df['Month of Date'])

            fig1 = go.Figure()
            
            # Determine selected flow for highlighting
            selected_flow = selection.get('flow') if selection else None
            
            for flow in ['Pipeline', 'LNG']:
                subset = c1_df[c1_df['Flow Type'] == flow]
                if not subset.empty:
                    color = PIPELINE_COLOR if flow == 'Pipeline' else LNG_COLOR
                    
                    # Determine line styling based on selection
                    if selected_flow:
                        if flow == selected_flow:
                            # Highlighted line
                            line_width = 4
                            opacity = 1.0
                            marker_size = 8
                            mode = 'lines+markers'
                        else:
                            # Dimmed line
                            line_width = 1
                            opacity = 0.3
                            marker_size = 0
                            mode = 'lines'
                    else:
                        # No selection - default styling with hidden markers
                        line_width = 2
                        opacity = 1.0
                        marker_size = 0  # Hide markers by default
                        mode = 'lines'
                    
                    # Create hover text
                    hover_text = []
                    for _, row in subset.iterrows():
                        date_val = row['Display Date']
                        # Display date is already formatted correctly based on agg_mode
                        display_date = date_val
                        
                        hover_text.append(
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Flow Type: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>{flow}</span><br>"
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Date: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>{display_date}</span><br>"
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Value: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>{row['Value']:.2f}</span><br>"
                            f"<span style='color: #666666; font-family: Arial, sans-serif;'>Unit: </span>"
                            f"<span style='color: #000000; font-weight: bold;'>{unit}</span>"
                        )
                    
                    fig1.add_trace(go.Scatter(
                        name=flow,
                        x=subset['Month of Date'],
                        y=subset['Value'],
                        mode=mode,
                        line=dict(color=color, width=line_width),
                        marker=dict(
                            size=marker_size,
                            color=color,
                            line=dict(color='white', width=1)
                        ),
                        opacity=opacity,
                        hoverinfo='text',
                        hovertext=hover_text,
                        customdata=[[flow]] * len(subset),
                        hoverlabel=dict(
                            bgcolor="white",
                            bordercolor="#cccccc",
                            font=dict(family="Arial, sans-serif", size=12, color="black"),
                            align="left"
                        ),
                        hoveron='points+fills'
                    ))
            
            # X-axis configuration based on aggregation mode
            xaxis_config = dict(title='', showgrid=True, gridcolor='#e0e0e0')
            
            if agg_mode == 'YEARLY':
                xaxis_config['dtick'] = "M12"  # One tick per year
                xaxis_config['tickformat'] = '%Y'
            elif agg_mode == 'QUARTERLY':
                xaxis_config['dtick'] = "M3"  # One tick per quarter
                xaxis_config['tickformat'] = 'Q%q %Y'
            elif agg_mode == 'MONTHLY':
                # Calculate appropriate tick interval based on data range
                date_range = (c1_df['Month of Date'].max() - c1_df['Month of Date'].min()).days / 365.25
                if date_range <= 2:
                    xaxis_config['dtick'] = "M1"  # Monthly ticks for short ranges
                    xaxis_config['tickformat'] = '%b %Y'
                elif date_range <= 5:
                    xaxis_config['dtick'] = "M3"  # Quarterly ticks for medium ranges
                    xaxis_config['tickformat'] = '%b %Y'
                else:
                    xaxis_config['dtick'] = "M6"  # Semi-annual ticks for long ranges
                    xaxis_config['tickformat'] = '%b %Y'
            elif agg_mode == 'DATE':
                # For daily data, use appropriate tick spacing
                date_range = (c1_df['Month of Date'].max() - c1_df['Month of Date'].min()).days / 365.25
                if date_range <= 1:
                    xaxis_config['dtick'] = "M1"  # Monthly ticks
                    xaxis_config['tickformat'] = '%b %d, %Y'
                else:
                    xaxis_config['dtick'] = "M3"  # Quarterly ticks
                    xaxis_config['tickformat'] = '%b %d, %Y'
            
            fig1.update_layout(
                xaxis=xaxis_config,
                yaxis=dict(title='', showgrid=True, gridcolor='#e0e0e0'),
                plot_bgcolor='white',
                paper_bgcolor='white',
                height=350,
                margin=dict(l=50, r=20, t=20, b=50),
                legend=dict(x=0.01, y=0.01, xanchor='left', yanchor='bottom', bgcolor='rgba(255,255,255,0.7)'),
                hovermode='closest'
            )
            
            return fig1
            
        except Exception as e:
            print(f"Chart 1 error: {e}")
            return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}}}

    # Chart 2: All Imports by Origin Bar Chart
    @dash_app.callback(
        Output('gas-asia-chart-2', 'figure'),
        [Input('gas-asia-destination-dropdown', 'value'),
         Input('gas-asia-start-date-picker', 'value'),
         Input('gas-asia-end-date-picker', 'value'),
         Input('gas-asia-selected-origins-store', 'data'),
         Input('gas-asia-flow-type-filter', 'value'),
         Input('gas-asia-unit-filter', 'value'),
         Input('gas-asia-chart2-agg-state', 'data'),
         Input('gas-asia-chart2-selection-store', 'data')]
    )
    def update_chart_2(destination, start_date, end_date, origins, flow_type, unit, agg_mode, selection):
        try:
            where_clause, region_clause, dest_clause, params, origins_filtered, flow_filtered, scale = get_query_params(
                destination, start_date, end_date, origins, flow_type, unit
            )
            
            agg_mode = (agg_mode or 'MONTHLY').upper()
            
            if not origins_filtered or not flow_filtered:
                return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 
                                  'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 300}}
            
            time_sql = "DATE_TRUNC('month', tr.date)"
            if agg_mode == 'YEARLY':
                time_sql = "DATE_TRUNC('year', tr.date)"
            elif agg_mode == 'QUARTERLY':
                time_sql = "DATE_TRUNC('quarter', tr.date)"
            elif agg_mode == 'DATE':
                time_sql = "tr.date"
            
            c2_query = f"""
            SELECT
                {time_sql} AS month_date,
                tr.source_country AS "Origin",
                '{unit}' AS adjusted_unit,
                ROUND(SUM(tr.value) / :scale, 4) AS "Value"
            FROM dev.glng_gas_trade tr
            LEFT JOIN dev.dim_country co ON co.dim_country_id = tr.target_country_id
            {where_clause} {region_clause} {dest_clause}
            AND LOWER(tr.flow_type) IN :flow_types
            AND tr.source_country IN :origins
            GROUP BY {time_sql}, tr.source_country
            ORDER BY tr.source_country DESC, {time_sql} DESC;
            """
            
            c2_df = load_data(c2_query, {**params, 'origins': tuple(origins_filtered), 'flow_types': tuple(flow_filtered), 'scale': scale})
            if c2_df.empty:
                return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 
                                  'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 350}}
            
            # Format display labels based on aggregation mode
            if agg_mode == 'YEARLY':
                c2_df['Display Date'] = pd.to_datetime(c2_df['month_date']).dt.year.astype(str)
            elif agg_mode == 'QUARTERLY':
                dt = pd.to_datetime(c2_df['month_date'])
                c2_df['Display Date'] = dt.dt.year.astype(str) + ' Q' + ((dt.dt.month - 1) // 3 + 1).astype(str)
            elif agg_mode == 'MONTHLY':
                dt = pd.to_datetime(c2_df['month_date'])
                c2_df['Display Date'] = dt.dt.strftime('%B %Y')
            elif agg_mode == 'DATE':
                dt = pd.to_datetime(c2_df['month_date'])
                c2_df['Display Date'] = dt.dt.strftime('%B %d, %Y')
            
            # Keep Month of Date as datetime for proper sorting and axis
            c2_df['Month of Date'] = pd.to_datetime(c2_df['month_date'])

            fig2 = go.Figure()
            
            # Determine selected bar for highlighting
            selected_origin = selection.get('origin') if selection else None
            selected_date = selection.get('date') if selection else None
            
            unique_origins = c2_df['Origin'].unique()
            for origin in unique_origins:
                subset = c2_df[c2_df['Origin'] == origin]
                color = get_consistent_color_for_origin(origin)
                
                # Create hover text and customdata
                hover_text = []
                customdata = []
                marker_line_widths = []
                marker_line_colors = []
                opacities = []
                
                for _, row in subset.iterrows():
                    # Use Display Date for hover
                    display_date = row['Display Date']
                    date_val = str(row['Month of Date'])
                    
                    # Store origin and date for click detection
                    customdata.append([origin, date_val])
                    
                    # Determine if this bar is selected
                    is_selected = (selected_origin == origin and selected_date == date_val)
                    
                    # Set highlighting
                    if selection:
                        if is_selected:
                            # Selected bar - thick black stroke
                            marker_line_widths.append(1)
                            marker_line_colors.append('black')
                            opacities.append(1.0)
                        else:
                            # Dimmed bars
                            marker_line_widths.append(0)
                            marker_line_colors.append(color)
                            opacities.append(0.3)
                    else:
                        # No selection - default styling
                        marker_line_widths.append(0)
                        marker_line_colors.append(color)
                        opacities.append(1.0)
                    
                    hover_text.append(
                        f"<span style='color: #666666; font-family: Arial, sans-serif;'>Origin: </span>"
                        f"<span style='color: #000000; font-weight: bold;'>{origin}</span><br>"
                        f"<span style='color: #666666; font-family: Arial, sans-serif;'>Date: </span>"
                        f"<span style='color: #000000; font-weight: bold;'>{display_date}</span><br>"
                        f"<span style='color: #666666; font-family: Arial, sans-serif;'>Value: </span>"
                        f"<span style='color: #000000; font-weight: bold;'>{row['Value']:.2f}</span><br>"
                        f"<span style='color: #666666; font-family: Arial, sans-serif;'>Unit: </span>"
                        f"<span style='color: #000000; font-weight: bold;'>{unit}</span>"
                    )

                fig2.add_trace(go.Bar(
                    name=origin,
                    x=subset['Month of Date'],
                    y=subset['Value'],
                    marker=dict(
                        color=color,
                        line=dict(
                            color=marker_line_colors,
                            width=marker_line_widths
                        ),
                        opacity=opacities
                    ),
                    hoverinfo='text',
                    hovertext=hover_text,
                    customdata=customdata,
                    hoverlabel=dict(
                        bgcolor="white",
                        bordercolor="#cccccc",
                        font=dict(family="Arial, sans-serif", size=12, color="black"),
                        align="left"
                    ),
                    showlegend=False  # Remove legend as requested
                ))
            
            # X-axis configuration based on aggregation mode
            xaxis_config = dict(title='', showgrid=False)
            
            if agg_mode == 'YEARLY':
                xaxis_config['dtick'] = "M12"  # One tick per year
                xaxis_config['tickformat'] = '%Y'
            elif agg_mode == 'QUARTERLY':
                xaxis_config['dtick'] = "M3"  # One tick per quarter
                xaxis_config['tickformat'] = 'Q%q %Y'
            elif agg_mode == 'MONTHLY':
                # Calculate appropriate tick interval based on data range
                date_range = (c2_df['Month of Date'].max() - c2_df['Month of Date'].min()).days / 365.25
                if date_range <= 2:
                    xaxis_config['dtick'] = "M1"  # Monthly ticks for short ranges
                    xaxis_config['tickformat'] = '%b %Y'
                elif date_range <= 5:
                    xaxis_config['dtick'] = "M3"  # Quarterly ticks for medium ranges
                    xaxis_config['tickformat'] = '%b %Y'
                else:
                    xaxis_config['dtick'] = "M6"  # Semi-annual ticks for long ranges
                    xaxis_config['tickformat'] = '%b %Y'
            elif agg_mode == 'DATE':
                # For daily data, use appropriate tick spacing
                date_range = (c2_df['Month of Date'].max() - c2_df['Month of Date'].min()).days / 365.25
                if date_range <= 1:
                    xaxis_config['dtick'] = "M1"  # Monthly ticks
                    xaxis_config['tickformat'] = '%b %d, %Y'
                else:
                    xaxis_config['dtick'] = "M3"  # Quarterly ticks
                    xaxis_config['tickformat'] = '%b %d, %Y'
            
            fig2.update_layout(
                barmode='stack',
                xaxis=xaxis_config,
                yaxis=dict(title='', showgrid=True, gridcolor='#e0e0e0'),  # Remove Y-axis title
                plot_bgcolor='white',
                paper_bgcolor='white',
                height=350,
                margin=dict(l=50, r=20, t=20, b=50),
                showlegend=False,  # Ensure legend is hidden
                hovermode='closest'
            )
            
            return fig2
            
        except Exception as e:
            print(f"Chart 2 error: {e}")
            return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}}}

    # Chart 3: Pipeline vs LNG Bar Chart
    @dash_app.callback(
        Output('gas-asia-chart-3', 'figure'),
        [Input('gas-asia-destination-dropdown', 'value'),
         Input('gas-asia-start-date-picker', 'value'),
         Input('gas-asia-end-date-picker', 'value'),
         Input('gas-asia-flow-type-filter', 'value'),
         Input('gas-asia-unit-filter', 'value'),
         Input('gas-asia-chart3-agg-state', 'data'),
         Input('gas-asia-chart3-selection-store', 'data')]
    )
    def update_chart_3(destination, start_date, end_date, flow_type, unit, agg_mode, selection):
        try:
            where_clause, region_clause, dest_clause, params, _, flow_filtered, scale = get_query_params(
                destination, start_date, end_date, [], flow_type, unit
            )
            
            agg_mode = (agg_mode or 'YEARLY').upper()
            
            if not flow_filtered:
                return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 
                                  'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 300}}
            
            time_sql = "DATE_TRUNC('year', tr.date)"
            if agg_mode == 'YEARLY':
                time_sql = "DATE_TRUNC('year', tr.date)"
            elif agg_mode == 'QUARTERLY':
                time_sql = "DATE_TRUNC('quarter', tr.date)"
            elif agg_mode == 'MONTHLY':
                time_sql = "DATE_TRUNC('month', tr.date)"
            elif agg_mode == 'DATE':
                time_sql = "tr.date"
            
            c3_query = f"""
            SELECT *
            FROM (
                SELECT
                    {time_sql} AS month_date,
                    CASE 
                        WHEN LOWER(tr.flow_type) = 'lng' THEN 'LNG'
                        WHEN LOWER(tr.flow_type) = 'natural gas' THEN 'Pipeline'
                        ELSE INITCAP(LOWER(tr.flow_type))
                    END AS "Flow Type",
                    '{unit}' AS adjusted_unit,
                    ROUND(SUM(tr.value) / :scale, 3) AS "Value"
                FROM dev.glng_gas_trade tr
                LEFT JOIN dev.dim_country co ON co.dim_country_id = tr.target_country_id
                {where_clause} {region_clause} {dest_clause}
                AND LOWER(tr.flow_type) IN :flow_types
                GROUP BY {time_sql},
                    CASE 
                        WHEN LOWER(tr.flow_type) = 'lng' THEN 'LNG'
                        WHEN LOWER(tr.flow_type) = 'natural gas' THEN 'Pipeline'
                        ELSE INITCAP(LOWER(tr.flow_type))
                    END
            ) t
            ORDER BY month_date, CASE WHEN "Flow Type" = 'Pipeline' THEN 1 ELSE 2 END;
            """
            
            c3_df = load_data(c3_query, {**params, 'flow_types': tuple(flow_filtered), 'scale': scale})
            if c3_df.empty:
                return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 
                                  'plot_bgcolor': 'white', 'paper_bgcolor': 'white', 'height': 350}}
            
            # Format period labels based on aggregation mode
            c3_df['month_date'] = pd.to_datetime(c3_df['month_date'])
            
            if agg_mode == 'YEARLY':
                c3_df['Period'] = c3_df['month_date'].dt.year.astype(str)
            elif agg_mode == 'QUARTERLY':
                c3_df['Period'] = c3_df['month_date'].dt.year.astype(str) + ' Q' + ((c3_df['month_date'].dt.month - 1) // 3 + 1).astype(str)
            elif agg_mode == 'MONTHLY':
                c3_df['Period'] = c3_df['month_date'].dt.strftime('%b %Y')
            elif agg_mode == 'DATE':
                c3_df['Period'] = c3_df['month_date'].dt.strftime('%d %b %Y')
            
            # Pivot data to have Flow Type as columns
            pivot_df = c3_df.pivot(index='Period', columns='Flow Type', values='Value').reset_index()
            
            # Ensure both LNG and Pipeline columns exist
            if 'LNG' not in pivot_df.columns:
                pivot_df['LNG'] = 0
            if 'Pipeline' not in pivot_df.columns:
                pivot_df['Pipeline'] = 0
            
            # Create X-axis labels: "LNG" and "Pipeline" repeated for each period
            x_labels = []
            x_positions = []
            period_annotations = []
            vertical_separators = []
            
            for idx, period in enumerate(pivot_df['Period']):
                # Two bars per period (LNG and Pipeline)
                x_labels.extend(['LNG', 'Pipeline'])
                x_positions.extend([idx * 2, idx * 2 + 1])
                
                # Add period annotation above the bars - ROTATED VERTICALLY
                period_annotations.append(dict(
                    x=idx * 2 + 0.5,  # Center between LNG and Pipeline
                    y=1.02,  # Just above the chart
                    xref='x',
                    yref='paper',
                    text=f'<b>{period}</b>',
                    showarrow=False,
                    font=dict(size=9, color='#333'),
                    xanchor='center',
                    yanchor='bottom',
                    textangle=-90  # Rotate text vertically (top to bottom)
                ))
                
                # Add vertical separator line after each period (except the last one)
                if idx < len(pivot_df) - 1:
                    vertical_separators.append(dict(
                        type='line',
                        x0=idx * 2 + 1.5,
                        x1=idx * 2 + 1.5,
                        y0=0,
                        y1=1,
                        xref='x',
                        yref='paper',
                        line=dict(color='#cccccc', width=1)
                    ))
            
            # Combine annotations and separators
            all_shapes = vertical_separators
            
            # Create figure
            fig3 = go.Figure()
            
            # Determine selected bar for highlighting
            selected_flow = selection.get('flow') if selection else None
            selected_period = selection.get('period') if selection else None
            
            # Add LNG bars
            lng_values = []
            pipeline_values = []
            lng_x = []
            pipeline_x = []
            lng_hover = []
            pipeline_hover = []
            lng_customdata = []
            pipeline_customdata = []
            lng_colors = []
            lng_line_widths = []
            lng_line_colors = []
            pipeline_colors = []
            pipeline_line_widths = []
            pipeline_line_colors = []
            
            for idx, row in pivot_df.iterrows():
                period_str = str(row['Period'])
                
                lng_x.append(idx * 2)
                pipeline_x.append(idx * 2 + 1)
                lng_values.append(row['LNG'])
                pipeline_values.append(row['Pipeline'])
                
                # Store customdata for click detection: [flow_type, period]
                lng_customdata.append(['LNG', period_str])
                pipeline_customdata.append(['Pipeline', period_str])
                
                # Determine if this bar is selected
                lng_selected = (selected_flow == 'LNG' and selected_period == period_str)
                pipeline_selected = (selected_flow == 'Pipeline' and selected_period == period_str)
                
                # Set highlighting for LNG
                if selection:
                    if lng_selected:
                        lng_colors.append(LNG_COLOR)
                        lng_line_widths.append(1)
                        lng_line_colors.append('black')
                    else:
                        lng_colors.append(f'rgba(31, 119, 180, 0.3)')  # Dimmed LNG color
                        lng_line_widths.append(0)
                        lng_line_colors.append(LNG_COLOR)
                else:
                    lng_colors.append(LNG_COLOR)
                    lng_line_widths.append(0)
                    lng_line_colors.append(LNG_COLOR)
                
                # Set highlighting for Pipeline
                if selection:
                    if pipeline_selected:
                        pipeline_colors.append(PIPELINE_COLOR)
                        pipeline_line_widths.append(1)
                        pipeline_line_colors.append('black')
                    else:
                        pipeline_colors.append(f'rgba(255, 127, 14, 0.3)')  # Dimmed Pipeline color
                        pipeline_line_widths.append(0)
                        pipeline_line_colors.append(PIPELINE_COLOR)
                else:
                    pipeline_colors.append(PIPELINE_COLOR)
                    pipeline_line_widths.append(0)
                    pipeline_line_colors.append(PIPELINE_COLOR)
                
                # Create hover text with period information
                period_label = 'Year of Date' if agg_mode == 'YEARLY' else \
                              'Quarter of Date' if agg_mode == 'QUARTERLY' else \
                              'Month of Date' if agg_mode == 'MONTHLY' else \
                              'Day of Year'
                
                lng_hover.append(
                    f"<span style='color: #666666; font-family: Arial, sans-serif;'>Flow Type: </span>"
                    f"<span style='color: #000000; font-weight: bold;'>LNG</span><br>"
                    f"<span style='color: #666666; font-family: Arial, sans-serif;'>{period_label}: </span>"
                    f"<span style='color: #000000; font-weight: bold;'>{row['Period']}</span><br>"
                    f"<span style='color: #666666; font-family: Arial, sans-serif;'>Unit: </span>"
                    f"<span style='color: #000000; font-weight: bold;'>{unit}</span><br>"
                    f"<span style='color: #666666; font-family: Arial, sans-serif;'>Value: </span>"
                    f"<span style='color: #000000; font-weight: bold;'>{row['LNG']:.1f}</span>"
                )
                
                pipeline_hover.append(
                    f"<span style='color: #666666; font-family: Arial, sans-serif;'>Flow Type: </span>"
                    f"<span style='color: #000000; font-weight: bold;'>Pipeline</span><br>"
                    f"<span style='color: #666666; font-family: Arial, sans-serif;'>{period_label}: </span>"
                    f"<span style='color: #000000; font-weight: bold;'>{row['Period']}</span><br>"
                    f"<span style='color: #666666; font-family: Arial, sans-serif;'>Unit: </span>"
                    f"<span style='color: #000000; font-weight: bold;'>{unit}</span><br>"
                    f"<span style='color: #666666; font-family: Arial, sans-serif;'>Value: </span>"
                    f"<span style='color: #000000; font-weight: bold;'>{row['Pipeline']:.1f}</span>"
                )
            
            # Add LNG trace
            fig3.add_trace(go.Bar(
                x=lng_x,
                y=lng_values,
                name='LNG',
                marker=dict(
                    color=lng_colors,
                    line=dict(
                        color=lng_line_colors,
                        width=lng_line_widths
                    )
                ),
                customdata=lng_customdata,
                hoverinfo='text',
                hovertext=lng_hover,
                hoverlabel=dict(
                    bgcolor="white",
                    bordercolor="#cccccc",
                    font=dict(family="Arial, sans-serif", size=12, color="black"),
                    align="left"
                ),
                showlegend=False
            ))
            
            # Add Pipeline trace
            fig3.add_trace(go.Bar(
                x=pipeline_x,
                y=pipeline_values,
                name='Pipeline',
                marker=dict(
                    color=pipeline_colors,
                    line=dict(
                        color=pipeline_line_colors,
                        width=pipeline_line_widths
                    )
                ),
                customdata=pipeline_customdata,
                hoverinfo='text',
                hovertext=pipeline_hover,
                hoverlabel=dict(
                    bgcolor="white",
                    bordercolor="#cccccc",
                    font=dict(family="Arial, sans-serif", size=12, color="black"),
                    align="left"
                ),
                showlegend=False
            ))
            
            # Update layout
            fig3.update_layout(
                barmode='group',
                xaxis=dict(
                    tickmode='array',
                    tickvals=x_positions,
                    ticktext=x_labels,
                    tickfont=dict(size=9, color='#666'),
                    showgrid=False,
                    title='',
                    range=[-0.5, len(x_positions) - 0.5]  # Tight fit
                ),
                yaxis=dict(
                    title=f'{unit}',
                    showgrid=True,
                    gridcolor='#e0e0e0'
                ),
                annotations=period_annotations,
                shapes=all_shapes,
                plot_bgcolor='white',
                paper_bgcolor='white',
                height=500,
                margin=dict(l=50, r=20, t=80, b=60),  # Increased top margin for vertical text
                hovermode='closest',
                bargap=0.15,
                bargroupgap=0.05  # Smaller gap between LNG and Pipeline within a period
            )
            
            return fig3
            
        except Exception as e:
            print(f"Chart 3 error: {e}")
            return {'layout': {'xaxis': {'visible': False}, 'yaxis': {'visible': False}}}

    # Table Update
    @dash_app.callback(
        [Output('gas-asia-imports-mix-table', 'data'),
         Output('gas-asia-imports-mix-table', 'columns')],
        [Input('gas-asia-destination-dropdown', 'value'),
         Input('gas-asia-start-date-picker', 'value'),
         Input('gas-asia-end-date-picker', 'value'),
         Input('gas-asia-selected-origins-store', 'data'),
         Input('gas-asia-flow-type-filter', 'value'),
         Input('gas-asia-table-agg-state', 'data')]
    )
    def update_table(destination, start_date, end_date, origins, flow_type, agg_mode):
        try:
            where_clause, region_clause, dest_clause, params, origins_filtered, flow_filtered, _ = get_query_params(
                destination, start_date, end_date, origins, flow_type, 'Bcm'
            )
            
            agg_mode = (agg_mode or 'MONTHLY').upper()
            
            if not origins_filtered or not flow_filtered:
                return [], []

            time_sql_select = "DATE_TRUNC('month', tr.date) AS month_date"
            time_sql_group = "DATE_TRUNC('month', tr.date)"
            
            if agg_mode == 'YEARLY':
                time_sql_select = "DATE_TRUNC('year', tr.date) AS month_date"
                time_sql_group = "DATE_TRUNC('year', tr.date)"
            elif agg_mode == 'QUARTERLY':
                time_sql_select = "DATE_TRUNC('quarter', tr.date) AS month_date"
                time_sql_group = "DATE_TRUNC('quarter', tr.date)"
            elif agg_mode == 'DATE':
                time_sql_select = "tr.date AS month_date"
                time_sql_group = "tr.date"

            t_query = f"""
            SELECT
                EXTRACT(YEAR FROM tr.date) AS year,
                {time_sql_select},
                tr.target_country AS destination,
                CASE 
                    WHEN LOWER(tr.flow_type) = 'lng' THEN 'LNG'
                    WHEN LOWER(tr.flow_type) = 'natural gas' THEN 'Pipeline'
                END AS flow_type,
                SUM(tr.value) AS value_mcm
            FROM dev.glng_gas_trade tr
            LEFT JOIN dev.dim_country co ON co.dim_country_id = tr.target_country_id
            {where_clause} {region_clause} {dest_clause}
            AND LOWER(tr.flow_type) IN :flow_types
            AND tr.source_country IN :origins
            GROUP BY
                EXTRACT(YEAR FROM tr.date),
                {time_sql_group},
                tr.target_country,
                CASE 
                    WHEN LOWER(tr.flow_type) = 'lng' THEN 'LNG'
                    WHEN LOWER(tr.flow_type) = 'natural gas' THEN 'Pipeline'
                END
            ORDER BY
                year DESC,
                month_date DESC,
                destination,
                flow_type;
            """
            
            table_df = load_data(t_query, {**params, 'origins': tuple(origins_filtered), 'flow_types': tuple(flow_filtered)})
            if table_df.empty:
                return [], []

            # Format month display based on aggregation mode
            table_df['month_date'] = pd.to_datetime(table_df['month_date'])
            
            # Add Year column
            table_df['Year'] = table_df['year'].astype(int)
            
            # Add Quarter column
            table_df['Quarter'] = 'Q' + ((table_df['month_date'].dt.month - 1) // 3 + 1).astype(str)
            
            # Add Month column (full month name)
            table_df['Month_Name'] = table_df['month_date'].dt.strftime('%B')
            
            # Add Day column
            table_df['Day'] = table_df['month_date'].dt.day.astype(int)
            
            # Determine which columns to show based on aggregation mode
            if agg_mode == 'YEARLY':
                group_cols = ['Year']
                display_cols = [('Year of Date', 'Year')]
            elif agg_mode == 'QUARTERLY':
                group_cols = ['Year', 'Quarter']
                display_cols = [('Year of Date', 'Year'), ('Quarter of Date', 'Quarter')]
            elif agg_mode == 'MONTHLY':
                group_cols = ['Year', 'Month_Name']
                display_cols = [('Year of Date', 'Year'), ('Month of Date', 'Month_Name')]
            elif agg_mode == 'DATE':
                group_cols = ['Year', 'Quarter', 'Month_Name', 'Day']
                display_cols = [
                    ('Year of Date', 'Year'),
                    ('Quarter of Date', 'Quarter'),
                    ('Month of Date', 'Month_Name'),
                    ('Day of Date', 'Day')
                ]
            
            # Get unique destinations (countries) sorted
            destinations = sorted(table_df['destination'].unique())
            
            # Check which flow types each destination has data for
            dest_flow_availability = {}
            for dest in destinations:
                dest_data = table_df[table_df['destination'] == dest]
                has_pipeline = dest_data[dest_data['flow_type'] == 'Pipeline']['value_mcm'].notna().any() and \
                              (dest_data[dest_data['flow_type'] == 'Pipeline']['value_mcm'] > 0).any()
                has_lng = dest_data[dest_data['flow_type'] == 'LNG']['value_mcm'].notna().any() and \
                         (dest_data[dest_data['flow_type'] == 'LNG']['value_mcm'] > 0).any()
                dest_flow_availability[dest] = {
                    'Pipeline': has_pipeline,
                    'LNG': has_lng
                }
            
            # Create a pivot table
            pivot_data = []
            
            # Sort the dataframe to ensure recent data is first
            table_df = table_df.sort_values(['year', 'month_date'], ascending=[False, False])
            
            # Group by the appropriate columns
            group_keys = group_cols + ['month_date']
            for group_key, group in table_df.groupby(group_keys, sort=False):  # sort=False to maintain order
                row = {}
                
                # Add the display columns
                for i, (col_name, col_key) in enumerate(display_cols):
                    if isinstance(group_key, tuple):
                        row[col_name] = group_key[i]
                    else:
                        row[col_name] = group_key
                
                # Add values for each destination and flow type
                for dest in destinations:
                    dest_data = group[group['destination'] == dest]
                    
                    # Only add Pipeline column if this destination has pipeline data
                    if dest_flow_availability[dest]['Pipeline']:
                        pipeline_val = dest_data[dest_data['flow_type'] == 'Pipeline']['value_mcm']
                        row[f"{dest}_Pipeline"] = round(float(pipeline_val.iloc[0]), 2) if len(pipeline_val) > 0 and not pd.isna(pipeline_val.iloc[0]) else ''
                    
                    # Only add LNG column if this destination has LNG data
                    if dest_flow_availability[dest]['LNG']:
                        lng_val = dest_data[dest_data['flow_type'] == 'LNG']['value_mcm']
                        row[f"{dest}_LNG"] = int(round(float(lng_val.iloc[0]), 0)) if len(lng_val) > 0 and not pd.isna(lng_val.iloc[0]) else ''
                
                pivot_data.append(row)
            
            # Create two-level columns - Merge countries (top level) but prevent merging Flow Types (bottom level)
            columns = []
            
            for col_name, _ in display_cols:
                columns.append({"name": ["", col_name], "id": col_name})
            
            for dest in destinations:
                # Only add Pipeline column if this destination has pipeline data
                if dest_flow_availability[dest]['Pipeline']:
                    # Add zero-width space to "Pipeline" to make it unique and prevent merging with other "Pipeline" columns
                    columns.append({"name": [dest, "Pipeline" + "\u200B" * len(columns)], "id": f"{dest}_Pipeline"})
                # Only add LNG column if this destination has LNG data
                if dest_flow_availability[dest]['LNG']:
                    # Add zero-width space to "LNG" to make it unique and prevent merging with other "LNG" columns
                    columns.append({"name": [dest, "LNG" + "\u200B" * len(columns)], "id": f"{dest}_LNG"})
            
            return pivot_data, columns
            
        except Exception as e:
            print(f"Table error: {e}")
            import traceback
            traceback.print_exc()
            return [], []

        # Format data
        data = table_df.to_dict('records')
        
        return data, columns

    # Export callbacks
    @dash_app.callback(
        Output("gas-asia-download-chart1-csv", "data"),
        Input("gas-asia-export-chart1-btn", "n_clicks"),
        [State('gas-asia-destination-dropdown', 'value'),
         State('gas-asia-start-date-picker', 'value'),
         State('gas-asia-end-date-picker', 'value'),
         State('gas-asia-flow-type-filter', 'value'),
         State('gas-asia-unit-filter', 'value'),
         State('gas-asia-chart1-agg-state', 'data')],
        prevent_initial_call=True
    )
    def export_chart1_csv(n_clicks, destination, start_date, end_date, flow_type, unit, agg_mode):
        if n_clicks is None or n_clicks == 0:
            return no_update
        
        where_clause, region_clause, dest_clause, params, _, flow_filtered, scale = get_query_params(
            destination, start_date, end_date, [], flow_type, unit
        )
        
        agg_mode = (agg_mode or 'MONTHLY').upper()
        
        time_sql = "DATE_TRUNC('month', tr.date)"
        fmt_sql = "TO_CHAR(DATE_TRUNC('month', tr.date), 'FMMonth YYYY')"
        if agg_mode == 'YEARLY':
            time_sql = "DATE_TRUNC('year', tr.date)"
            fmt_sql = "TO_CHAR(DATE_TRUNC('year', tr.date), 'YYYY')"
        elif agg_mode == 'QUARTERLY':
            time_sql = "DATE_TRUNC('quarter', tr.date)"
            fmt_sql = "TO_CHAR(DATE_TRUNC('quarter', tr.date), 'YYYY \"Q\"Q')"
        elif agg_mode == 'DATE':
            time_sql = "tr.date"
            fmt_sql = "TO_CHAR(tr.date, 'DD Mon YYYY')"
        
        c1_query = f"""
        WITH gas_data AS (
            SELECT
                {time_sql} AS month_date,
                {fmt_sql} AS "Month of Date",
                CASE 
                    WHEN LOWER(tr.flow_type) = 'lng' THEN 'LNG'
                    WHEN LOWER(tr.flow_type) = 'natural gas' THEN 'Pipeline'
                END AS "Flow Type",
                ROUND(SUM(tr.value) / :scale, 4) AS "Value"
            FROM dev.glng_gas_trade tr
            LEFT JOIN dev.dim_country co ON co.dim_country_id = tr.target_country_id
            {where_clause} {region_clause} {dest_clause}
            AND LOWER(tr.flow_type) IN :flow_types
            GROUP BY {time_sql},
                CASE 
                    WHEN LOWER(tr.flow_type) = 'lng' THEN 'LNG'
                    WHEN LOWER(tr.flow_type) = 'natural gas' THEN 'Pipeline'
                END
        )
        SELECT "Month of Date", "Flow Type", '{unit}' AS Unit, "Value"
        FROM gas_data
        ORDER BY month_date;
        """
        df = load_data(c1_query, {**params, 'flow_types': tuple(flow_filtered), 'scale': scale})
        return dcc.send_data_frame(df.to_csv, "asian_gas_imports_lng_vs_pipeline.csv", index=False)

    @dash_app.callback(
        Output("gas-asia-download-chart2-csv", "data"),
        Input("gas-asia-export-chart2-btn", "n_clicks"),
        [State('gas-asia-destination-dropdown', 'value'),
         State('gas-asia-start-date-picker', 'value'),
         State('gas-asia-end-date-picker', 'value'),
         State('gas-asia-selected-origins-store', 'data'),
         State('gas-asia-flow-type-filter', 'value'),
         State('gas-asia-unit-filter', 'value'),
         State('gas-asia-chart2-agg-state', 'data')],
        prevent_initial_call=True
    )
    def export_chart2_csv(n_clicks, destination, start_date, end_date, origins, flow_type, unit, agg_mode):
        if n_clicks is None or n_clicks == 0:
            return no_update

        where_clause, region_clause, dest_clause, params, origins_filtered, flow_filtered, scale = get_query_params(
            destination, start_date, end_date, origins, flow_type, unit
        )
        
        agg_mode = (agg_mode or 'MONTHLY').upper()
        
        time_sql = "DATE_TRUNC('month', tr.date)"
        fmt_sql = "TO_CHAR(DATE_TRUNC('month', tr.date), 'FMMonth YYYY')"
        if agg_mode == 'YEARLY':
            time_sql = "DATE_TRUNC('year', tr.date)"
            fmt_sql = "TO_CHAR(DATE_TRUNC('year', tr.date), 'YYYY')"
        elif agg_mode == 'QUARTERLY':
            time_sql = "DATE_TRUNC('quarter', tr.date)"
            fmt_sql = "TO_CHAR(DATE_TRUNC('quarter', tr.date), 'YYYY \"Q\"Q')"
        elif agg_mode == 'DATE':
            time_sql = "tr.date"
            fmt_sql = "TO_CHAR(tr.date, 'DD Mon YYYY')"

        c2_query = f"""
        SELECT
            {fmt_sql} AS "Month of Date",
            tr.source_country AS "Origin",
            '{unit}' AS Unit,
            ROUND(SUM(tr.value) / :scale, 4) AS "Value"
        FROM dev.glng_gas_trade tr
        LEFT JOIN dev.dim_country co ON co.dim_country_id = tr.target_country_id
        {where_clause} {region_clause} {dest_clause}
        AND LOWER(tr.flow_type) IN :flow_types
        AND tr.source_country IN :origins
        GROUP BY {time_sql}, tr.source_country
        ORDER BY {time_sql};
        """
        df = load_data(c2_query, {**params, 'origins': tuple(origins_filtered), 'flow_types': tuple(flow_filtered), 'scale': scale})
        return dcc.send_data_frame(df.to_csv, "asian_gas_imports_by_origin.csv", index=False)

    @dash_app.callback(
        Output("gas-asia-download-chart3-csv", "data"),
        Input("gas-asia-export-chart3-btn", "n_clicks"),
        [State('gas-asia-destination-dropdown', 'value'),
         State('gas-asia-start-date-picker', 'value'),
         State('gas-asia-end-date-picker', 'value'),
         State('gas-asia-flow-type-filter', 'value'),
         State('gas-asia-unit-filter', 'value'),
         State('gas-asia-chart3-agg-state', 'data')],
        prevent_initial_call=True
    )
    def export_chart3_csv(n_clicks, destination, start_date, end_date, flow_type, unit, agg_mode):
        if n_clicks is None or n_clicks == 0:
            return no_update

        where_clause, region_clause, dest_clause, params, _, flow_filtered, scale = get_query_params(
            destination, start_date, end_date, [], flow_type, unit
        )

        agg_mode = (agg_mode or 'YEARLY').upper()
        
        time_sql = "DATE_TRUNC('year', tr.date)"
        fmt_sql = "TO_CHAR(DATE_TRUNC('year', tr.date), 'YYYY')"
        if agg_mode == 'YEARLY':
            time_sql = "DATE_TRUNC('year', tr.date)"
            fmt_sql = "TO_CHAR(DATE_TRUNC('year', tr.date), 'YYYY')"
        elif agg_mode == 'QUARTERLY':
            time_sql = "DATE_TRUNC('quarter', tr.date)"
            fmt_sql = "TO_CHAR(DATE_TRUNC('quarter', tr.date), 'YYYY \"Q\"Q')"
        elif agg_mode == 'MONTHLY':
            time_sql = "DATE_TRUNC('month', tr.date)"
            fmt_sql = "TO_CHAR(DATE_TRUNC('month', tr.date), 'FMMonth YYYY')"
        elif agg_mode == 'DATE':
            time_sql = "tr.date"
            fmt_sql = "TO_CHAR(tr.date, 'DD Mon YYYY')"

        c3_query = f"""
        SELECT
            {fmt_sql} AS "Month of Date",
            CASE 
                WHEN LOWER(tr.flow_type) = 'lng' THEN 'LNG'
                WHEN LOWER(tr.flow_type) = 'natural gas' THEN 'Pipeline'
            END AS "Flow Type",
            '{unit}' AS Unit,
            ROUND(SUM(tr.value) / :scale, 3) AS "Value"
        FROM dev.glng_gas_trade tr
        LEFT JOIN dev.dim_country co ON co.dim_country_id = tr.target_country_id
        {where_clause} {region_clause} {dest_clause}
        AND LOWER(tr.flow_type) IN :flow_types
        GROUP BY {time_sql},
            CASE 
                WHEN LOWER(tr.flow_type) = 'lng' THEN 'LNG'
                WHEN LOWER(tr.flow_type) = 'natural gas' THEN 'Pipeline'
            END
        ORDER BY {time_sql};
        """
        df = load_data(c3_query, {**params, 'flow_types': tuple(flow_filtered), 'scale': scale})
        return dcc.send_data_frame(df.to_csv, "asian_gas_imports_pipeline_vs_lng_yearly.csv", index=False)

    @dash_app.callback(
        Output("gas-asia-download-table-csv", "data"),
        Input("gas-asia-export-table-btn", "n_clicks"),
        [State('gas-asia-destination-dropdown', 'value'),
         State('gas-asia-start-date-picker', 'value'),
         State('gas-asia-end-date-picker', 'value'),
         State('gas-asia-selected-origins-store', 'data'),
         State('gas-asia-flow-type-filter', 'value'),
         State('gas-asia-table-agg-state', 'data')],
        prevent_initial_call=True
    )
    def export_table_csv(n_clicks, destination, start_date, end_date, origins, flow_type, agg_mode):
        if n_clicks is None or n_clicks == 0:
            return no_update

        where_clause, region_clause, dest_clause, params, origins_filtered, flow_filtered, _ = get_query_params(
            destination, start_date, end_date, origins, flow_type, 'Bcm'
        )
        
        agg_mode = (agg_mode or 'MONTHLY').upper()
        
        time_sql_select = "DATE_TRUNC('month', tr.date) AS month_date, TO_CHAR(DATE_TRUNC('month', tr.date), 'FMMonth') AS \"Month of Date\""
        time_sql_group = "DATE_TRUNC('month', tr.date)"
        
        if agg_mode == 'YEARLY':
            time_sql_select = "DATE_TRUNC('year', tr.date) AS month_date, TO_CHAR(DATE_TRUNC('year', tr.date), 'YYYY') AS \"Month of Date\""
            time_sql_group = "DATE_TRUNC('year', tr.date)"
        elif agg_mode == 'QUARTERLY':
            time_sql_select = "DATE_TRUNC('quarter', tr.date) AS month_date, TO_CHAR(DATE_TRUNC('quarter', tr.date), 'YYYY \"Q\"Q') AS \"Month of Date\""
            time_sql_group = "DATE_TRUNC('quarter', tr.date)"
        elif agg_mode == 'DATE':
            time_sql_select = "tr.date AS month_date, TO_CHAR(tr.date, 'DD Mon YYYY') AS \"Month of Date\""
            time_sql_group = "tr.date"
        
        t_query = f"""
        WITH gas_data AS (
            SELECT
                EXTRACT(YEAR FROM tr.date) AS "Year of Date",
                {time_sql_select},
                tr.target_country AS "Destination",
                CASE 
                    WHEN LOWER(tr.flow_type) = 'lng' THEN 'LNG'
                    WHEN LOWER(tr.flow_type) = 'natural gas' THEN 'Pipeline'
                END AS "Flow Type",
                ROUND(SUM(tr.value), 2) AS "Value (Mcm)"
            FROM dev.glng_gas_trade tr
            LEFT JOIN dev.dim_country co ON co.dim_country_id = tr.target_country_id
            {where_clause} {region_clause} {dest_clause}
            AND LOWER(tr.flow_type) IN :flow_types
            AND tr.source_country IN :origins
            GROUP BY
                EXTRACT(YEAR FROM tr.date),
                {time_sql_group},
                tr.target_country,
                CASE 
                    WHEN LOWER(tr.flow_type) = 'lng' THEN 'LNG'
                    WHEN LOWER(tr.flow_type) = 'natural gas' THEN 'Pipeline'
                END
        )
        SELECT "Year of Date", "Month of Date", "Destination", "Flow Type", "Value (Mcm)"
        FROM gas_data
        ORDER BY "Year of Date" DESC, month_date DESC;
        """
        
        df = load_data(t_query, {**params, 'origins': tuple(origins_filtered), 'flow_types': tuple(flow_filtered)})
        return dcc.send_data_frame(df.to_csv, "asian_gas_imports_table.csv", index=False)
