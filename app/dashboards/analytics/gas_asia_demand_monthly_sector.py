"""
Asian Gas Demand - Monthly Demand by Sector
Recreated Tableau dashboard for Asian gas demand by sector and country.
Strict separation of CSV usage between chart and table.
"""
import pandas as pd
import numpy as np
from dash import dcc, html, dash_table, Input, Output, State, no_update
import plotly.graph_objects as go
import os
from datetime import datetime

# --- Configuration ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Data dirs
YEARLY_DATA_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "data", "Asian-gas-demand-yearly")
SECTOR_DATA_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "data", "Asian-gas-demand-sector")

# Table CSVs (EXISTING - DO NOT CHANGE)
TABLE_BCM_FILE = os.path.join(YEARLY_DATA_DIR, "Asia Gas Demand by Sector_data_bcm.csv")
TABLE_GWH_FILE = os.path.join(YEARLY_DATA_DIR, "Asia Gas Demand by Sector_data_gwh.csv")

# Chart CSVs (NEW - ONLY FOR CHART)
CHART_BCM_FILE = os.path.join(SECTOR_DATA_DIR, "Asia Column Chart_Demand by Sector_data_bcm.csv")
CHART_GWH_FILE = os.path.join(SECTOR_DATA_DIR, "Asia Column Chart_Demand by Sector_data_gwh.csv")

COLORS = {
    'Industrial': '#B7D28B', # Light Green
    'Power': '#CC5521',      # Orange
    'Household': '#006FAD',  # Blue
    'Other': '#1D8F91'       # Teal
}

# Stack Order: Bottom -> Top
SECTOR_ORDER = ['Industrial', 'Power', 'Household', 'Other']

# --- Data Loading ---

def load_table_data(unit):
    """
    Load data for the TABLE using existing logic and files.
    """
    try:
        file_path = TABLE_BCM_FILE if "Billion Cubic Meter" in unit else TABLE_GWH_FILE
        if not os.path.exists(file_path):
            print(f"Error: Table file not found at {file_path}")
            return pd.DataFrame()
            
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        df.columns = [c.lstrip('\ufeff').strip() for c in df.columns]
        
        # Existing Logic provided in yearly.py
        month_map = {
            'January': 'Q1', 'February': 'Q1', 'March': 'Q1',
            'April': 'Q2', 'May': 'Q2', 'June': 'Q2',
            'July': 'Q3', 'August': 'Q3', 'September': 'Q3',
            'October': 'Q4', 'November': 'Q4', 'December': 'Q4'
        }
        df['Quarter'] = df['Month of Date'].map(month_map)
        
        # Add Date object for filtering
        # Assume 'Year of Date' is int and 'Month of Date' is string
        # format: Month YYYY construction for easy filtering
        # Note: input df has 'Year of Date' (int) and 'Month of Date' (str name)
        df['Date_Obj'] = pd.to_datetime(df['Month of Date'] + ' ' + df['Year of Date'].astype(str), format='%B %Y')
        
        return df
    except Exception as e:
        print(f"Error loading table data: {e}")
        return pd.DataFrame()

def load_chart_data(unit):
    """
    Load data for the CHART using NEW files.
    """
    try:
        file_path = CHART_BCM_FILE if "Billion Cubic Meter" in unit else CHART_GWH_FILE
        if not os.path.exists(file_path):
            print(f"Error: Chart file not found at {file_path}")
            return pd.DataFrame()
            
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        df.columns = [c.lstrip('\ufeff').strip() for c in df.columns]
        
        # format: September 2025
        # Parse 'Month of Date' column
        df['Date_Obj'] = pd.to_datetime(df['Month of Date'], format='%B %Y')
        df['Year'] = df['Date_Obj'].dt.year
        df['Month'] = df['Date_Obj'].dt.strftime('%B')
        
        return df
    except Exception as e:
        print(f"Error loading chart data: {e}")
        return pd.DataFrame()

def filter_dataframe(df, sector, country, start_date, end_date):
    """
    Apply filters to a dataframe (works for both table and chart DFs if they have standard cols).
    """
    dff = df.copy()
    
    # Date Range Filter
    if start_date and end_date:
        dff = dff[(dff['Date_Obj'] >= start_date) & (dff['Date_Obj'] <= end_date)]
        
    if sector != '(All)':
        dff = dff[dff['Sector'] == sector]
    
    if country and country != '(All)':
        dff = dff[dff['Country'] == country]
        
    return dff

# --- UI Components ---

def create_layout():
    # Load initial data to get filter options and date range
    df_chart = load_chart_data("Billion Cubic Meter") # Use chart data for master date range
    df_table = load_table_data("Billion Cubic Meter")
    
    if df_chart.empty or df_table.empty:
        return html.Div("Data failed to load.")
        
    all_countries = sorted(df_chart['Country'].unique().tolist())
    all_sectors = ['(All)'] + sorted(df_chart['Sector'].unique().tolist())
    
    # Date Range Slider Logic
    unique_dates = sorted(df_chart['Date_Obj'].unique())
    if not unique_dates:
        return html.Div("No date data found.")
        
    min_date = unique_dates[0]
    max_date = unique_dates[-1]
    
    # Map dates to numerical marks
    # We will use unix timestamp chunks or just index if continuous?
    # Index is safer if data is sparse, but monthly data is usually continuous.
    # Let's use Index mapping for the Slider
    date_marks = {}
    # Show one label per year
    # Redesign: Only show Start and End Date labels matching Image 2 style
    # Format: M/D/YYYY e.g. 1/1/2019 and 9/30/2025
    # Use invisible marks to suppress auto-generated numeric ticks
    date_marks = {
        0: {'label': '', 'style': {'display': 'none'}}, 
        len(unique_dates) - 1: {'label': '', 'style': {'display': 'none'}}
    } 

    # Initial Start/End indices
    start_idx = 0
    end_idx = len(unique_dates) - 1
    max_idx = len(unique_dates) - 1

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
                # Stores for Table State (Clientside)
                dcc.Store(id='asia-table-highlight-state'),
                html.Div(id='asia-table-dummy-output', style={'display': 'none'})
                
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
                            html.Div(id='asia-date-label-start', children=pd.Timestamp(unique_dates[0]).strftime('%-m/%-d/%Y'), style={
                                'position': 'absolute', 'top': '-30px', 'left': '0', 
                                'fontSize': '11px', 'color': '#777', 
                                'whiteSpace': 'nowrap',
                                'pointerEvents': 'none',
                                'zIndex': '10'
                            }),
                            html.Div(id='asia-date-label-end', children=pd.Timestamp(unique_dates[-1]).strftime('%-m/%-d/%Y'), style={
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
                    dcc.Store(id='asia-date-map', data=[d.strftime('%-m/%-d/%Y') for d in unique_dates]),
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


def build_chart(df, sector_filter, unit):
    # Sort by Date
    df = df.sort_values('Date_Obj')
    
    unique_dates = df['Date_Obj'].unique()
    # Format for X axis ticks
    x_axis_labels = [pd.Timestamp(d).strftime('%B %Y') for d in unique_dates]
    
    fig = go.Figure()
    
    # Determine format
    val_fmt = ",.1f" if unit == 'Billion Cubic Meter' else ",.0f"
    
    # Stacked Bar Chart
    # Order: Industrial (Bottom), Power, Household, Other (Top)
    # The loop should go in this order so Plotly stacks them correctly (first trace at bottom? Standard bar stack adds on top)
    # Actually Plotly stacks in order of traces added.
    
    sectors_to_plot = SECTOR_ORDER if sector_filter == '(All)' else [sector_filter]
    
    for sector in sectors_to_plot:
        # Filter for sector
        sdf = df[df['Sector'] == sector]
        
        # We need to align with unique_dates to ensure stacking aligns correctly
        # Create a Series indexed by date
        # Sum duplicates if any (shouldn't be for Chart data but safety first)
        sdf_grouped = sdf.groupby('Date_Obj')['adjusted_unit_value'].sum()
        
        y_vals = []
        hover_names = []
        for d in unique_dates:
            val = sdf_grouped.get(d, 0)
            y_vals.append(val)
            hover_names.append(sector)

        fig.add_trace(go.Bar(
            name=sector,
            x=x_axis_labels,
            y=y_vals,
            marker_color=COLORS.get(sector, '#ccc'),
            # No text on bars for dense monthly chart usually, unless requested. Image 1 shows no text on bars.
            # Wait, Image 1 shows... No text labels on the bars themselves in the small view? 
            # Actually the screenshot might be zoomed out. 
            # Instructions say: "Bars must be continuous and dense". Suggests no text labels on bars to avoid clutter.
            # I will omit 'text' argument or leave it empty.
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
            tickangle=-90, # Vertical labels for months often needed
            tickfont=dict(size=10, color='#999'),
        ),
        yaxis=dict(
            title='',
            showgrid=False,
            showline=False,
            zeroline=True,
            zerolinecolor='#ccc',
            tickfont=dict(size=10, color='#999') # Show Y axis labels
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(t=30, b=80, l=40, r=10),
        height=500,
        showlegend=False # Custom legend in sidebar
    )
    
    return fig


def build_table(df, sector_filter, unit):
    """
    Existing Table Logic from yearly.py
    """
    if df.empty:
        return html.Div("No data found.", style={'padding': '20px', 'textAlign': 'center'})

    years = sorted(df['Year of Date'].unique(), reverse=True)
    months_ref = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    
    # helper to sort months
    def month_sort_key(m):
        return months_ref.index(m)

    # Pre-calculate active months per year to hide empty columns outside range
    active_months_map = {}
    for y in years:
        # Get unique months for this year present in data
        m_in_data = df[df['Year of Date'] == y]['Month of Date'].unique().tolist()
        # Sort them descending (Dec -> Jan) for display
        m_in_data.sort(key=month_sort_key, reverse=True)
        active_months_map[y] = m_in_data

    countries = sorted(df['Country'].unique())
    # Order for table to match Image 1 (Household -> Total)
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
                'Country_Full': country # for styling/filtering if needed
            }
            is_first_sector = False
            
            for y in years:
                # Use ONLY active months for this year
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
    
    # Columns with multi-level headers [Year, Month]
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
                'padding': '0px 5px', # Minimal padding for reduced height
                'fontSize': '11px',
                'fontFamily': 'Arial, sans-serif',
                'border': 'none', 
                'minWidth': '70px',
                'backgroundColor': '#fff',
                'color': '#777', # Grey text for sectors and data
                'height': 'auto',
                'textAlign': 'right'
            },
            style_header_conditional=[
                # Apply borders ONLY to data columns (Years/Months)
                {'if': {'header_index': 0, 'column_id': data_col_ids}, 'borderBottom': '1px solid #d0d0d0'},
                {'if': {'header_index': 0, 'column_id': data_col_ids}, 'textAlign': 'center'}, # Center Year Headers
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
         Output('asia-gas-monthly-table-container', 'children')],
        [Input('asia-unit-filter', 'value'),
         Input('asia-sector-filter', 'value'),
         Input('asia-country-filter', 'value'),
         Input('asia-date-slider', 'value')],
        [State('asia-date-map', 'data')]
    )
    def update_dashboard(unit, sector, country, date_range_idx, date_map):
        # 1. Resolve Data Range
        if date_map and date_range_idx:
            try:
                start_date_str = date_map[date_range_idx[0]]
                end_date_str = date_map[date_range_idx[1]]
                start_date = pd.to_datetime(start_date_str)
                end_date = pd.to_datetime(end_date_str)
            except:
                start_date = None
                end_date = None
        else:
            start_date = None
            end_date = None
        
        # 2. LOAD & FILTER: Table (Existing Data)
        df_table = load_table_data(unit)
        if df_table.empty:
            table_comp = html.Div("Data error")
        else:
            dff_table = filter_dataframe(df_table, sector, country, start_date, end_date)
            # Table Logic expects dataframe
            table_comp = build_table(dff_table, sector, unit)
            
        # 3. LOAD & FILTER: Chart (New Data)
        df_chart = load_chart_data(unit)
        if df_chart.empty:
            fig = go.Figure()
        else:
            dff_chart = filter_dataframe(df_chart, sector, country, start_date, end_date)
            fig = build_chart(dff_chart, sector, unit)
        
        return fig, table_comp

    # 2. Clientside Callback for tooltips text transformation on Slider
    dash_app.clientside_callback(
        """
        function(value, date_map) {
            if (!date_map || !value) return "";
            try {
                // Return start/end labels potentially?
                // Actually RangeSlider tooltip `transform` is not supported directly in dcc this way
                // But we can just use the built-in tooltip which shows value. 
                // Since value is index, we need a custom transform if supported.
                // dcc.RangeSlider `tooltip={transform: ...}` is not fully custom JS usually.
                // It expects a formatted string or simple map. 
                // We'll rely on the visual marks for now.
                return ""; 
            } catch(e) { return ""; }
        }
        """,
        Output('asia-table-dummy-output', 'style'), # Dummy output
        Input('asia-date-slider', 'value'),
        State('asia-date-map', 'data')
    )

    # 3. Clientside Callback for Table Highlighting (Reused from Yearly)
    dash_app.clientside_callback(
        """
        function(n_data, columns, current_state) {
            try {
                const tableId = 'asia-gas-demand-table';
                
                // 1. Inject or Update CSS
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
                    
                    /* Column Selection: Country/Sector remain visible (100% opacity) but NOT blue */
                    .asia-col-selection-active td[data-dash-column="Country"], 
                    .asia-col-selection-active td[data-dash-column="Sector"] { 
                        opacity: 1 !important; 
                        background-color: transparent !important; 
                    }
                    
                    /* Row Selection: The Highlighted Row(s) - FORCE BLUE ON ALL CELLS */
                    .asia-row-selection-active tr.asia-row-highlighted td {
                        opacity: 1 !important;
                        background-color: #cfe8ef !important;
                        color: black !important;
                    }

                    /* Row Selection: Non-selected rows dimmed */
                    .asia-row-selection-active tr:not(.asia-row-trip-wire) td {
                        opacity: 0.3 !important;
                    }

                    /* Headers */
                    th.asia-col-selected { background-color: #cfe8ef !important; }
                `;

                if (!window.asiaGasState) {
                    window.asiaGasState = { 
                        selectedColumnId: null,
                        selectedRowIndices: null // String "start_end" or null
                    };
                }

                // 2. Helper Logic
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

                    // COLUMN HIGHLIGHTING
                    if (window.asiaGasState.selectedColumnId) {
                        const targetIds = window.asiaGasState.selectedColumnId.split(',');
                        if (targetIds.length === 0) return;

                        spreadsheet.classList.add('asia-col-selection-active');

                        // Headers
                        targetIds.forEach(id => {
                            const ths = spreadsheet.querySelectorAll(`th[data-dash-column="${id}"]`);
                            ths.forEach(th => th.classList.add('asia-col-selected'));
                        });

                        // Body Cells
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

                    // ROW HIGHLIGHTING
                    if (window.asiaGasState.selectedRowIndices) {
                        const [start, end] = window.asiaGasState.selectedRowIndices.split('_').map(Number);
                        
                        spreadsheet.classList.add('asia-row-selection-active');
                        
                        // Handle Split Tables (Dash)
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
                    
                    // Always try to re-apply state
                    if (spreadsheet && (window.asiaGasState.selectedColumnId || window.asiaGasState.selectedRowIndices)) {
                        applyState(spreadsheet, n_data);
                    }
                    
                    if (!spreadsheet || spreadsheet.dataset.enhanced === 'true') return;

                    spreadsheet.dataset.enhanced = 'true';
                    
                    // Click Handler
                    spreadsheet.addEventListener('click', function(e) {
                         // 1. Column Header Click
                        const header = e.target.closest('th[data-dash-column]');
                        if (header) {
                            e.stopPropagation();
                            const colId = header.getAttribute('data-dash-column');
                            if (colId === 'Country' || colId === 'Sector') return;

                            const headerContent = header.innerText.trim();
                            let isYearHeader = /^\d{4}$/.test(headerContent);
                            let targetIds = [];
                            if (isYearHeader && columns) {
                                // Select all month columns for this year? 
                                // Assuming 'columns' var is available and up to date
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
                                window.asiaGasState.selectedRowIndices = null; // Clear rows
                            }
                            applyState(spreadsheet, n_data);
                            return;
                        }

                        // 2. Row Data Click (Country/Sector)
                        const cell = e.target.closest('td[data-dash-column]');
                        if (cell) {
                            const colId = cell.getAttribute('data-dash-column');
                            
                            if (colId === 'Country' || colId === 'Sector') {
                                e.stopPropagation();
                                const row = cell.closest('tr');
                                const tbody = row.closest('tbody');
                                // Calculate Index carefully relative to this specific tbody
                                const allRows = Array.from(tbody.querySelectorAll('tr'));
                                const rowIndex = allRows.indexOf(row);
                         
                                let startIndex = rowIndex;
                                let endIndex = rowIndex;

                                if (colId === 'Country') {
                                    // Use n_data (Data Driven) Grouping
                                    if (n_data) {
                                        let curr = rowIndex;
                                        // Scan up
                                        while (curr >= 0) {
                                            if (n_data[curr] && n_data[curr]['Country']) {
                                                startIndex = curr;
                                                break;
                                            }
                                            curr--;
                                        }
                                        if (curr < 0) startIndex = 0; // Fallback

                                        // Scan down
                                        curr = startIndex + 1;
                                        endIndex = n_data.length - 1;
                                        while (curr < n_data.length) {
                                            if (n_data[curr] && n_data[curr]['Country']) {
                                                endIndex = curr - 1;
                                                break;
                                            }
                                            curr++;
                                        }
                                    }
                                } 
                                
                                const selectionKey = `${startIndex}_${endIndex}`;
                                
                                if (window.asiaGasState.selectedRowIndices === selectionKey) {
                                    window.asiaGasState.selectedRowIndices = null;
                                } else {
                                    window.asiaGasState.selectedRowIndices = selectionKey;
                                    window.asiaGasState.selectedColumnId = null; // Clear cols
                                }
                                applyState(spreadsheet, n_data);
                            } else {
                                // Clicked a data cell
                                if (window.asiaGasState.selectedColumnId || window.asiaGasState.selectedRowIndices) {
                                     window.asiaGasState.selectedColumnId = null;
                                     window.asiaGasState.selectedRowIndices = null;
                                     applyState(spreadsheet, n_data);
                                }
                            }
                        }
                    });
                    
                    // Outside Click
                    document.addEventListener('click', function(e) {
                        if (spreadsheet && !spreadsheet.contains(e.target)) {
                            window.asiaGasState.selectedColumnId = null;
                            window.asiaGasState.selectedRowIndices = null;
                            applyState(spreadsheet, n_data);
                        }
                    });
                }

                setupTable();
                
                if (!window.asiaGasObserver) {
                    window.asiaGasObserver = new MutationObserver(() => {
                        setupTable();
                    });
                    window.asiaGasObserver.observe(document.body, { childList: true, subtree: true });
                }

            } catch (e) { console.error(e); }
            return "";
        }
        """,
        Output('asia-table-dummy-output', 'children', allow_duplicate=True),
        Input('asia-gas-demand-table', 'data'),
        [State('asia-gas-demand-table', 'columns'),
         State('asia-table-highlight-state', 'data')],
        prevent_initial_call=True
    )

    # 4. Clientside Callback for Moving Slider Labels
    # 4. Clientside Callback for Updating Slider Label TEXT Only (Static Position)
    dash_app.clientside_callback(
        """
        function(value, date_map, max_idx) {
            if (!value || !date_map || max_idx === undefined) return ["", ""];
            
            // Ensure integer indices for array lookup
            const startIdx = Math.round(value[0]);
            const endIdx = Math.round(value[1]);
            
            // Text lookup
            const startText = date_map[startIdx] || "";
            const endText = date_map[endIdx] || "";
            
            return [startText, endText];
        }
        """,
        [Output('asia-date-label-start', 'children'),
         Output('asia-date-label-end', 'children')],
        Input('asia-date-slider', 'value'),
        [State('asia-date-map', 'data'),
         State('asia-date-max', 'data')]
    )