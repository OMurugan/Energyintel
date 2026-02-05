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
                # Chart Container
                html.Div([
                    dcc.Graph(id='asia-gas-monthly-chart', config={'displayModeBar': False})
                ], style={'backgroundColor': '#fff', 'padding': '10px'}),

                # Table Container
                html.Div(id='asia-gas-monthly-table-container', style={'marginTop': '20px'}),
                
                # Stores for State
                dcc.Store(id='asia-table-highlight-state'), # From Clientside
                dcc.Store(id='chart-highlight-state', data=None), # Server side Highlight State
                
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
                        
                        # Relative Container for Slider + Moving Labels
                        html.Div([
                            # Moving Labels (Static Placement, Dynamic Text)
                            html.Div(id='asia-date-label-start', children=start_date_label, style={
                                'position': 'absolute', 'top': '-30px', 'left': '0', 
                                'fontSize': '11px', 'color': '#777', 
                                'whiteSpace': 'nowrap',
                                'pointerEvents': 'none',
                                'zIndex': '10'
                            }),
                            html.Div(id='asia-date-label-end', children=end_date_label, style={
                                'position': 'absolute', 'top': '-30px', 'right': '0', 
                                'fontSize': '11px', 'color': '#777', 
                                'whiteSpace': 'nowrap',
                                'pointerEvents': 'none',
                                'zIndex': '10'
                            }),

                            dcc.RangeSlider(
                                id='asia-date-slider',
                                min=0,
                                max=max_idx,
                                value=[start_idx, end_idx],
                                marks=date_marks,
                                step=1,
                                updatemode='drag'
                            ),
                        ], style={'position': 'relative', 'padding': '0 10px', 'marginTop': '30px', 'height': '20px'}) 
                        
                    ], style={'marginBottom': '20px', 'borderBottom': '1px solid #eee', 'paddingBottom': '20px'}),
                    
                    # Store unique dates as JSON and MAX Index for callback math
                    dcc.Store(id='asia-date-map', data=date_map_data),
                    dcc.Store(id='asia-date-max', data=max_idx),

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
        html.Script("""
        """)
    ], id='gas-asia-monthly-container', style={'backgroundColor': '#ffffff', 'fontFamily': 'Arial, sans-serif'})


def build_chart(df, sector_filter, unit, highlight_state=None):
    # Sort by Date
    df = df.sort_values('Date_Obj')
    
    unique_dates = df['Date_Obj'].unique()
    # Format for X axis ticks
    x_axis_labels = [pd.Timestamp(d).strftime('%B %Y') for d in unique_dates]
    
    # Generate tick text with conditional formatting
    tick_texts = []
    for d in unique_dates:
        d_str = pd.Timestamp(d).strftime('%B %Y')
        is_selected = False
        if highlight_state and highlight_state.get('type') == 'month':
            if highlight_state.get('date') == d_str:
                is_selected = True
        
        if is_selected:
            # Highlight style matching Image 1 (Blue background)
            # Note: Plotly accepts subset of HTML
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
        sdf = df[df['Sector'] == sector]
        
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
            date_str = pd.Timestamp(d).strftime('%B %Y') # Match format
            
            op = 1.0 # Default full opacity
            lw = 0
            lc = 'rgba(0,0,0,0)' # Transparent
            
            if highlight_state:
                op = 0.3 # Default dim if highlighting active
                
                if highlight_state.get('type') == 'month':
                    # Highlight entire stack for date
                    if highlight_state.get('date') == date_str:
                        op = 1.0
                        
                elif highlight_state.get('type') == 'bar':
                    # Highlight specific segment
                    if highlight_state.get('date') == date_str and highlight_state.get('sector') == sector:
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
        clickmode='event+select'
    )
    
    return fig


def build_table(df, sector_filter, unit):
    if df.empty:
        return html.Div("No data found.", style={'padding': '20px', 'textAlign': 'center'})

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

    return html.Div([
        dash_table.DataTable(
            id='asia-gas-demand-table',
            data=table_data,
            columns=columns,
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

def register_callbacks(dash_app, server):
    # 1. Main Update Callback
    
    @dash_app.callback(
        [Output('asia-gas-monthly-chart', 'figure'),
         Output('asia-gas-monthly-table-container', 'children'),
         Output('chart-highlight-state', 'data')],
        [Input('asia-unit-filter', 'value'),
         Input('asia-sector-filter', 'value'),
         Input('asia-country-filter', 'value'),
         Input('asia-date-slider', 'value'),
         Input('asia-gas-monthly-chart', 'clickData'),
         Input('asia-table-highlight-state', 'data'),
         Input('axis-click-trigger', 'value')],
        [State('asia-date-map', 'data'),
         State('chart-highlight-state', 'data')]
    )
    def update_dashboard(unit, sector, country, date_range_idx, clickData, table_highlight_state, axis_click_raw, date_map, current_highlight):
        try:
            # 0. Determine Trigger
            triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
            
            # 1. Resolve Highlight State Change
            highlight_state = current_highlight # Default keep current
            
            # If Filters changed, clear highlight
            if triggered_id in ['asia-unit-filter', 'asia-sector-filter', 'asia-country-filter', 'asia-date-slider']:
                highlight_state = None
                
            # If Chart Bar Clicked -> Toggle Bar Selection (Image 2 Style)
            elif triggered_id == 'asia-gas-monthly-chart':
                if clickData and 'points' in clickData:
                    point = clickData['points'][0]
                    clicked_date = point.get('x') # "Month YYYY"
                    clicked_sector = point.get('data', {}).get('name')
                    
                    if clicked_date and clicked_sector:
                        # Check if same click -> Deselect
                        if (highlight_state and 
                            highlight_state.get('type') == 'bar' and 
                            highlight_state.get('date') == clicked_date and 
                            highlight_state.get('sector') == clicked_sector):
                            highlight_state = None
                        else:
                            highlight_state = {
                                'type': 'bar',
                                'date': clicked_date,
                                'sector': clicked_sector
                            }
            
            # If Table Highlighted (Header Click) -> Month Selection (Image 1 Style)
            elif triggered_id == 'asia-table-highlight-state':
                if not table_highlight_state:
                     if highlight_state and highlight_state.get('type') == 'month':
                         highlight_state = None
                elif isinstance(table_highlight_state, str) and re.match(r'^\d{4}_[A-Za-z]+$', table_highlight_state):
                    parts = table_highlight_state.split('_')
                    year = parts[0]
                    month = parts[1]
                    chart_date_str = f"{month} {year}"
                    
                    if (highlight_state and 
                        highlight_state.get('type') == 'month' and 
                        highlight_state.get('date') == chart_date_str):
                        highlight_state = None
                    else:
                        highlight_state = {
                            'type': 'month',
                            'date': chart_date_str,
                            'sector': None
                        }
            
            # If Axis Clicked (Simulated) -> Month Selection (Image 1 Style)
            elif triggered_id == 'axis-click-trigger':
                if axis_click_raw:
                    # Parse "Month YYYY|TIMESTAMP" -> "Month YYYY"
                    axis_click_date = axis_click_raw.split('|')[0]
                    
                    if (highlight_state and 
                        highlight_state.get('type') == 'month' and 
                        highlight_state.get('date') == axis_click_date):
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
            
            # 3. LOAD using SQL logic
            # These functions handle db connection errors internally and return empty DF
            df_table = load_table_data(country)
            df_chart = load_chart_data(country)

            # 4. FILTER
            if not df_table.empty:
                df_table = df_table[df_table['Unit'] == unit]
            if not df_chart.empty:
                df_chart = df_chart[df_chart['Unit'] == unit]

            if sector != '(All)':
                if not df_table.empty:
                    df_table = df_table[df_table['Sector'] == sector]
                if not df_chart.empty:
                    df_chart = df_chart[df_chart['Sector'] == sector]

            if start_date and end_date:
                if not df_table.empty:
                    df_table = df_table[(df_table['Date_Obj'] >= start_date) & (df_table['Date_Obj'] <= end_date)]
                if not df_chart.empty:
                    df_chart = df_chart[(df_chart['Date_Obj'] >= start_date) & (df_chart['Date_Obj'] <= end_date)]
                    
            # 5. Build Components
            if df_table.empty:
                table_comp = html.Div("Data error or empty for selection")
            else:
                table_comp = build_table(df_table, sector, unit)
                
            if df_chart.empty:
                fig = go.Figure()
            else:
                # IMPORTANT: build_chart handles Plotly construction. 
                # If highlight_state is corrupt or causes error, we catch it?
                # We sanitized input logic above.
                fig = build_chart(df_chart, sector, unit, highlight_state)
            
            return fig, table_comp, highlight_state

        except Exception as e:
            # Fallback to prevent 500 error on frontend
            print(f"Error in update_dashboard: {e}")
            fig = go.Figure()
            fig.update_layout(title=f"Error: {str(e)}")
            return fig, no_update, no_update

    # 2. Clientside Callback for tooltips text transformation on Slider (No Op, just for output)
    # 2. Clientside Callback for updating Slider Date Labels
    dash_app.clientside_callback(
        """
        function(value, date_map) {
            if (!date_map || !value) return ["", ""];
            return [date_map[value[0]], date_map[value[1]]];
        }
        """,
        [Output('asia-date-label-start', 'children'),
         Output('asia-date-label-end', 'children')],
        Input('asia-date-slider', 'value'),
        State('asia-date-map', 'data')
    )

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
                    if (!tableEl) return;
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    
                    if (spreadsheet && (window.asiaGasState.selectedColumnId || window.asiaGasState.selectedRowIndices)) {
                        applyState(spreadsheet, n_data);
                    }
                    
                    if (!spreadsheet || spreadsheet.dataset.enhanced === 'true') return;

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
                                    if (c.id.startsWith(headerContent + '_')) targetIds.push(c.id);
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
                             const row = cell.closest('tr');
                             const tbody = row.closest('tbody');
                             const rows = Array.from(tbody.querySelectorAll('tr'));
                             const idx = rows.indexOf(row);
                             
                             const start = idx; 
                             const end = idx; 
                             
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
                
                setTimeout(setupTable, 500); 
                return window.asiaGasState.selectedColumnId || ""; 

            } catch(e) { console.error(e); return ""; }
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
                    
                    // x-axis ticks text. Note this selector might need tuning depending on Plotly version
                    // Usually .xaxislayer-above .xtick text OR .xtick text
                    // Use a slightly more generic selector for safety
                    const ticks = graph.querySelectorAll('.xtick text');
                    
                    if (ticks.length === 0) return;
                    
                    ticks.forEach(t => {
                        t.style.cursor = 'pointer'; 
                        
                        // Prevent attaching multiple times if re-running
                        if (t.getAttribute('data-click-attached')) return;
                        t.setAttribute('data-click-attached', 'true');
                        
                        t.addEventListener('click', function(e) {
                            const dateStr = t.textContent; // "May 2020"
                            const input = document.getElementById('axis-click-trigger');
                            if (input) {
                                // Append timestamp to ensure value CHANGE
                                const payload = dateStr + "|" + Date.now();
                                
                                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                                nativeInputValueSetter.call(input, payload);
                                input.dispatchEvent(new Event('input', { bubbles: true }));
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