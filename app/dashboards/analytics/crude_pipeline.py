import dash
from dash import dcc, html, Input, Output, State, callback, callback_context, ALL, no_update
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from core.data_helpers import execute_query
from datetime import datetime
import json

# --- Constants & Config ---

COLOR_MAP = {
    'Transneft Seaborne': '#006d9c',  # Blue
    'Bypassing Transneft': '#003049',  # Dark Blue
    'Czech Republic': '#0072bc',     # Blue
    'Germany': '#9e9e9e',            # Grey
    'Hungary': '#424242',             # Dark Grey
    'Poland': '#6baed6',              # Light Blue
    'Slovakia': '#212121',            # Black/Dark
    'China': '#5b9bd5'                # Solid Blue for China
}

DRUZHBA_DESTINATIONS = ['Czech Republic', 'Germany', 'Hungary', 'Poland', 'Slovakia']

MONTH_ORDER = [
    'January', 'February', 'March', 'April', 'May', 'June', 
    'July', 'August', 'September', 'October', 'November', 'December'
]

# --- Data Loading Functions ---

def get_available_years():
    """Fetch distinct years from the database for the filter."""
    query = """
    SELECT DISTINCT EXTRACT(YEAR FROM date)::INT AS year
    FROM dev.russia_master_data
    ORDER BY year DESC;
    """
    try:
        results = execute_query(query)
        if results and isinstance(results, list):
            return [int(r['year']) for r in results if r['year'] is not None]
        return []
    except Exception as e:
        print(f"Error loading years: {e}")
        return [2022, 2023, 2024, 2025]

def load_seaborne_data(years):
    """Load Seaborne Crude Oil Exports data."""
    if not years:
        return pd.DataFrame()
    
    years_str = ",".join(str(y) for y in years)
    query = f"""
    SELECT
        ru.country,
        ru.date,
        ru.type,
        ru.destination,
        ru.commodity,
        ru.category,
        ru.vol_kbpd
    FROM dev.russia_master_data ru
    WHERE ru.type IN ('Transneft Seaborne', 'Bypassing Transneft')
      AND EXTRACT(YEAR FROM ru.date) IN ({years_str})
    ORDER BY ru.date
    """
    try:
        results = execute_query(query)
        if not results:
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        df['date'] = pd.to_datetime(df['date'])
        df['vol_kbpd'] = pd.to_numeric(df['vol_kbpd'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        print(f"Error loading seaborne data: {e}")
        return pd.DataFrame()

def load_pipeline_data(years):
    """Load Pipeline Crude Exports data."""
    if not years:
        return pd.DataFrame()
    
    years_str = ",".join(str(y) for y in years)
    query = f"""
    SELECT
        ru.country,
        ru.date,
        ru.type,
        ru.destination,
        ru.commodity,
        ru.category,
        ru.vol_kbpd
    FROM dev.russia_master_data ru
    WHERE ru.type = 'Pipeline'
      AND EXTRACT(YEAR FROM ru.date) IN ({years_str})
    ORDER BY ru.date
    """
    try:
        results = execute_query(query)
        if not results:
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        df['date'] = pd.to_datetime(df['date'])
        df['vol_kbpd'] = pd.to_numeric(df['vol_kbpd'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        print(f"Error loading pipeline data: {e}")
        return pd.DataFrame()

# --- Layout ---

def create_layout():
    available_years = get_available_years()
    # Default to latest 4 years
    default_years = available_years[:4] if len(available_years) >= 4 else available_years

    return html.Div([
        # Stores for interactive selection state
        dcc.Store(id='selected-seaborne', data=None),
        dcc.Store(id='selected-pipeline', data=None),
        dcc.Store(id='seaborne-agg-state', data='monthly'),
        dcc.Store(id='pipeline-agg-state', data='monthly'),
        
        # Download components
        dcc.Download(id="download-seaborne-csv"),
        dcc.Download(id="download-pipeline-csv"),
        
        # Style for the hand cursor
        html.Div(id='cursor-style-container'),
        
        html.Div([
            # Left Column: Charts (Flexible width)
            html.Div([
                # Title 1 + Export
                html.Div([
                    html.H1("SEABORNE CRUDE OIL EXPORTS ('000 b/d)", 
                            style={'color': '#d35400', 'fontSize': '18px', 'fontWeight': 'bold', 'margin': '0', 'fontFamily': 'sans-serif'}),
                    dcc.Loading(
                        id="loading-export-seaborne",
                        type="default",
                        color="#fe5000",
                        children=[
                            html.Button(
                                "Export to CSV",
                                id="export-seaborne-btn",
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
                                },
                            )
                        ]
                    )
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
                
                # Chart 1
                html.Div(dcc.Loading(
                    dcc.Graph(id='seaborne-chart', className='custom-chart', config={'displayModeBar': False}, style={'height': '300px'})
                ), style={'cursor': 'pointer'}),
                
                html.Hr(style={'margin': '5px 0', 'border': '0', 'borderTop': '1px solid #eee', 'clear': 'both'}),
                
                # Title 2 + Export
                html.Div([
                    html.H1(id='pipeline-title', 
                            children="PIPELINE CRUDE EXPORTS TO EUROPE VIA DRUZHBA ('000 b/d)",
                            style={'color': '#d35400', 'fontSize': '18px', 'fontWeight': 'bold', 'margin': '0', 'fontFamily': 'sans-serif'}),
                    dcc.Loading(
                        id="loading-export-pipeline",
                        type="default",
                        color="#fe5000",
                        children=[
                            html.Button(
                                "Export to CSV",
                                id="export-pipeline-btn",
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
                                },
                            )
                        ]
                    )
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
                
                # Chart 2
                html.Div(dcc.Loading(
                    dcc.Graph(id='pipeline-chart', className='custom-chart', config={'displayModeBar': False}, style={'height': '350px'})
                ), style={'cursor': 'pointer'})
                
            ], style={'flex': '1', 'marginRight': '30px', 'minWidth': '0'}),
            
            # Right Column: Controls & Legends (Fixed width)
            html.Div([
                # 1. Year Filter
                html.Div([
                    html.Label("Select Year(s)", style={'fontWeight': 'bold', 'fontSize': '13px', 'marginBottom': '5px', 'display': 'block'}),
                    dcc.Checklist(
                        id='year-check-filter',
                        options=[{'label': f" {y}", 'value': y} for y in sorted(available_years, reverse=True)],
                        value=default_years,
                        style={'fontSize': '12px', 'lineHeight': '1.6'},
                        inputStyle={'cursor': 'pointer'}
                    )
                ], style={'marginBottom': '30px'}),

                # 2. Seaborne Legend
                html.Div([
                    html.Div([
                        html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': COLOR_MAP['Transneft Seaborne'], 'marginRight': '8px'}),
                        html.Span("Transneft Seaborne", style={'fontSize': '12px', 'color': '#333'})
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px', 'cursor': 'pointer'}, 
                        id={'type': 'legend-item', 'chart': 'seaborne', 'value': 'Transneft Seaborne'}),
                    html.Div([
                        html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': COLOR_MAP['Bypassing Transneft'], 'marginRight': '8px'}),
                        html.Span("Bypassing Transneft", style={'fontSize': '12px', 'color': '#333'})
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px', 'cursor': 'pointer'},
                        id={'type': 'legend-item', 'chart': 'seaborne', 'value': 'Bypassing Transneft'}),
                ], style={'marginBottom': '80px', 'marginTop': '20px'}),

                # 3. Direction Filter
                html.Div([
                    html.Label("DIRECTION", style={'fontWeight': 'bold', 'fontSize': '13px', 'marginBottom': '5px', 'display': 'block'}),
                    dcc.Dropdown(
                        id='direction-dropdown',
                        options=[
                            {'label': 'Druzhba', 'value': 'Druzhba'},
                            {'label': 'China', 'value': 'China'}
                        ],
                        value='Druzhba',
                        clearable=False,
                        style={'fontSize': '12px', 'width': '140px'}
                    )
                ], style={'marginBottom': '30px'}),

                # 4. Pipeline Legend (Dynamic)
                html.Div(id='pipeline-legend-container')

            ], style={'width': '160px', 'flexShrink': '0', 'position': 'sticky', 'top': '10px', 'paddingTop': '10px'})
            
        ], style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'flex-start'})
        
    ], style={'padding': '15px 25px', 'backgroundColor': '#fff', 'fontFamily': 'sans-serif'})

# --- Helper Functions ---

def hex_to_rgba(h, a):
    """Convert hex color to rgba string."""
    h = h.lstrip('#')
    rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({rgb[0]},{rgb[1]},{rgb[2]},{a})'

def generate_timeline_data(years, mode='monthly'):
    """
    Generate timeline mapping, labels, and separators for a set of years based on aggregation mode.
    Modes: 'monthly', 'quarterly', 'yearly'
    """
    timeline = []
    year_annotations = []
    month_separators = []
    year_separators = []
    
    year_centers = [] # Used for Header placement (and Icon placement)
    
    current_global_x = 0
    num_years = len(years)
    
    # Configuration based on mode
    if mode == 'monthly':
        slots_per_year = 12
        slot_width = 1.0
        # X-axis labels
        sub_labels = MONTH_ORDER
    elif mode == 'quarterly':
        slots_per_year = 4
        slot_width = 1.0
        sub_labels = ['Q1', 'Q2', 'Q3', 'Q4']
    elif mode == 'yearly':
        slots_per_year = 1
        slot_width = 1.0 # One bar per year
        sub_labels = [''] # No sub-labels for yearly
        
    for y_idx, y in enumerate(years):
        # Calculate visual center for the year header
        # Center is at start + (total_width / 2)
        # total_width = slots_per_year * slot_width
        year_width = slots_per_year * slot_width
        year_center = current_global_x + (year_width / 2)
        
        # Icon position: To the left of the center (roughly same relative pos as Tableau)
        # Or just use the center and offset text? Tableau puts icon left of text.
        # We'll store year_center for the text.
        year_centers.append({'year': y, 'x': year_center, 'width': year_width})
        
        # Add Year Annotation (Header)
        # Offset x for icon can be handled in the chart trace
        year_annotations.append(dict(
             x=year_center, y=0.5, xref="x", yref="y2",
             text=f"<b>{y}</b>", showarrow=False, font=dict(size=14, color="black"),
             xanchor="center", yanchor="middle"
        ))
        
        for s_idx, label in enumerate(sub_labels):
            # Shortening logic only applies to Monthly mode really
            final_label = label
            if mode == 'monthly':
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
            
            # For timeline mapping
            item = {
                'year': y,
                'x_pos': current_global_x + (slot_width / 2),
                'short_label': final_label,
                'full_label': label # This might be month name or Qx
            }
            if mode == 'monthly':
                item['month_name'] = label
                item['month_idx'] = s_idx
            elif mode == 'quarterly':
                item['quarter'] = label
            
            timeline.append(item)
            
            # Separators (between months/quarters)
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
            month_separators.append(y_sep) # Add to general list too
            
            # Add a small gap between years? No, continuous line.
            # current_global_x += 0.5 # REMOVED gap to match Tableau compact style for non-monthly
            # For 'monthly' we had a gap. Let's keep consistency.
            if mode == 'monthly':
                 current_global_x += 0.5 
            elif mode == 'quarterly':
                 current_global_x += 0.25 # Smaller gap
            else:
                 current_global_x += 0.25
            
    df = pd.DataFrame(timeline)
    return df, year_annotations, month_separators, year_separators, num_years, year_centers

# --- Callbacks ---

@callback(
    [Output('selected-seaborne', 'data'),
     Output('selected-pipeline', 'data'),
     Output('seaborne-chart', 'clickData'),
     Output('pipeline-chart', 'clickData')],
    [Input('seaborne-chart', 'clickData'),
     Input('pipeline-chart', 'clickData'),
     Input('seaborne-chart', 'restyleData'),
     Input('pipeline-chart', 'restyleData'),
     Input('year-check-filter', 'value'),
     Input('direction-dropdown', 'value')],
    [State('selected-seaborne', 'data'),
     State('selected-pipeline', 'data'),
     State('seaborne-chart', 'figure'),
     State('pipeline-chart', 'figure')]
)
def update_chart_selections(sea_click, pipe_click, sea_restyle, pipe_restyle, year_filter, dir_filter, 
                            sea_sel, pipe_sel, sea_fig, pipe_fig):
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update, no_update
    
    trigger_id = ctx.triggered[0]['prop_id']
    
    # Reset selections if year filter or direction filter changes
    if 'year-check-filter' in trigger_id or 'direction-dropdown' in trigger_id:
        sea_reset = None if sea_sel else no_update
        pipe_reset = None if pipe_sel else no_update
        return sea_reset, pipe_reset, None, None
    
    # --- Seaborne Logic ---
    if 'seaborne-chart.clickData' in trigger_id or 'seaborne-chart.restyleData' in trigger_id:
        new_sea_sel = no_update
        
        if 'seaborne-chart.clickData' in trigger_id and sea_click:
            point = sea_click['points'][0]
            cdata = point.get('customdata', [])
            
            # Year Header Click
            if cdata and isinstance(cdata, list) and len(cdata) > 0 and cdata[-1] == 'YEAR_HEADER':
                clicked_year = cdata[0]
                # Toggle logic: Check string equality to handle potential type mismatches
                if (sea_sel and isinstance(sea_sel, dict) and 
                    sea_sel.get('mode') == 'year_only' and 
                    str(sea_sel.get('year')) == str(clicked_year)):
                    new_sea_sel = None
                else:
                    new_sea_sel = {'year': clicked_year, 'mode': 'year_only'}

            # Month Header Click
            elif cdata and isinstance(cdata, list) and len(cdata) > 0 and cdata[-1] == 'MONTH_HEADER':
                clicked_year = cdata[0]
                clicked_month = cdata[1]
                # Toggle
                if (sea_sel and isinstance(sea_sel, dict) and 
                    sea_sel.get('mode') == 'month_only' and 
                    str(sea_sel.get('year')) == str(clicked_year) and
                    sea_sel.get('month') == clicked_month):
                    new_sea_sel = None
                else:
                    new_sea_sel = {'year': clicked_year, 'month': clicked_month, 'mode': 'month_only'}
            
            # Normal Bar Click
            elif cdata:
                candidate = {
                    'year': cdata[0],
                    'month': cdata[1],
                    'type': cdata[2],
                    'is_categorical': False
                }
                if (sea_sel and isinstance(sea_sel, dict) and not sea_sel.get('is_categorical') and
                    not sea_sel.get('mode') and
                    str(sea_sel.get('year')) == str(candidate['year']) and 
                    sea_sel.get('month') == candidate['month'] and 
                    sea_sel.get('type') == candidate['type']):
                    new_sea_sel = None
                else:
                    new_sea_sel = candidate
        
        elif 'seaborne-chart.restyleData' in trigger_id and sea_restyle:
            if 'visible' in sea_restyle[0]:
                curve_idx = sea_restyle[1][0]
                if sea_fig and 'data' in sea_fig:
                    type_name = sea_fig['data'][curve_idx]['name']
                    candidate = {'type': type_name, 'is_categorical': True}
                    if (sea_sel and isinstance(sea_sel, dict) and sea_sel.get('is_categorical') and 
                        sea_sel.get('type') == type_name):
                        new_sea_sel = None
                    else:
                        new_sea_sel = candidate
        
        if new_sea_sel != no_update:
            pipe_reset = None if pipe_sel else no_update
            return new_sea_sel, pipe_reset, None, None
            
    # --- Pipeline Logic ---
    if 'pipeline-chart.clickData' in trigger_id or 'pipeline-chart.restyleData' in trigger_id:
        new_pipe_sel = no_update
        
        if 'pipeline-chart.clickData' in trigger_id and pipe_click:
            point = pipe_click['points'][0]
            cdata = point.get('customdata', [])
            
            # Check for Icon Click (Year Toggle)
            if cdata and isinstance(cdata, list) and len(cdata) > 0 and cdata[-1] == 'YEAR_ICON':
                # This is handled in a separate callback or we need to output to the store here
                # But current callback outputs to 'selected-seaborne'/'selected-pipeline'.
                # We need a NEW callback for aggregation state.
                pass 

            # Year Header Click
            elif cdata and isinstance(cdata, list) and len(cdata) > 0 and cdata[-1] == 'YEAR_HEADER':
                clicked_year = cdata[0]
                if (pipe_sel and isinstance(pipe_sel, dict) and 
                    pipe_sel.get('mode') == 'year_only' and 
                    str(pipe_sel.get('year')) == str(clicked_year)):
                    new_pipe_sel = None
                else:
                    new_pipe_sel = {'year': clicked_year, 'mode': 'year_only'}

            # Month Header Click
            elif cdata and isinstance(cdata, list) and len(cdata) > 0 and cdata[-1] == 'MONTH_HEADER':
                clicked_year = cdata[0]
                clicked_month = cdata[1]
                # Toggle
                if (pipe_sel and isinstance(pipe_sel, dict) and 
                    pipe_sel.get('mode') == 'month_only' and 
                    str(pipe_sel.get('year')) == str(clicked_year) and
                    pipe_sel.get('month') == clicked_month):
                    new_pipe_sel = None
                else:
                    new_pipe_sel = {'year': clicked_year, 'month': clicked_month, 'mode': 'month_only'}
            
            # Normal Bar Click
            elif cdata:
                candidate = {
                    'year': cdata[0],
                    'month': cdata[1],
                    'destination': cdata[2],
                    'is_categorical': False
                }
                if (pipe_sel and isinstance(pipe_sel, dict) and not pipe_sel.get('is_categorical') and
                    not pipe_sel.get('mode') and
                    str(pipe_sel.get('year')) == str(candidate['year']) and 
                    pipe_sel.get('month') == candidate['month'] and 
                    pipe_sel.get('destination') == candidate['destination']):
                    new_pipe_sel = None
                else:
                    new_pipe_sel = candidate
                    
        elif 'pipeline-chart.restyleData' in trigger_id and pipe_restyle:
            if 'visible' in pipe_restyle[0]:
                curve_idx = pipe_restyle[1][0]
                if pipe_fig and 'data' in pipe_fig:
                    destination = pipe_fig['data'][curve_idx]['name']
                    candidate = {'destination': destination, 'is_categorical': True}
                    if (pipe_sel and isinstance(pipe_sel, dict) and pipe_sel.get('is_categorical') and 
                        pipe_sel.get('destination') == destination):
                        new_pipe_sel = None
                    else:
                        new_pipe_sel = candidate

        # If Pipeline updated, force Seaborne reset ONLY if it has data
        if new_pipe_sel != no_update:
            sea_reset = None if sea_sel else no_update
            return sea_reset, new_pipe_sel, None, None
            
    return no_update, no_update, no_update, no_update

@callback(
    [Output('seaborne-agg-state', 'data'),
     Output('pipeline-agg-state', 'data')],
    [Input('seaborne-chart', 'clickData'),
     Input('pipeline-chart', 'clickData')],
    [State('seaborne-agg-state', 'data'),
     State('pipeline-agg-state', 'data')]
)
def update_aggregation_state(sea_click, pipe_click, current_sea_agg, current_pipe_agg):
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update
    
    trigger_id = ctx.triggered[0]['prop_id']
    
    # Seaborne Icon Click
    if 'seaborne-chart.clickData' in trigger_id and sea_click:
        point = sea_click['points'][0]
        cdata = point.get('customdata', [])
        if cdata and isinstance(cdata, list) and len(cdata) > 0 and cdata[-1] == 'YEAR_ICON':
            if current_sea_agg == 'monthly':
                new_agg = 'yearly'
            elif current_sea_agg == 'yearly':
                new_agg = 'quarterly'
            else: # quarterly
                new_agg = 'yearly'
            return new_agg, no_update

    # Pipeline Icon Click
    if 'pipeline-chart.clickData' in trigger_id and pipe_click:
        point = pipe_click['points'][0]
        cdata = point.get('customdata', [])
        if cdata and isinstance(cdata, list) and len(cdata) > 0 and cdata[-1] == 'YEAR_ICON':
            if current_pipe_agg == 'monthly':
                new_agg = 'yearly'
            elif current_pipe_agg == 'yearly':
                new_agg = 'quarterly'
            else: # quarterly
                new_agg = 'yearly'
            return no_update, new_agg
            
    return no_update, no_update

@callback(
    Output('selected-seaborne', 'data', allow_duplicate=True),
    [Input({'type': 'legend-item', 'chart': 'seaborne', 'value': ALL}, 'n_clicks')],
    [State('selected-seaborne', 'data')],
    prevent_initial_call=True
)
def update_seaborne_selection_from_legend(n_clicks, sel_sea):
    ctx = callback_context
    if not ctx.triggered or all(c is None for c in n_clicks):
        return no_update
    
    trigger_info = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
    val = trigger_info['value']
    
    new_sel = {'type': val, 'is_categorical': True}
    if sel_sea and isinstance(sel_sea, dict) and sel_sea.get('is_categorical') and sel_sea['type'] == val:
        return None
    return new_sel

@callback(
    Output('selected-pipeline', 'data', allow_duplicate=True),
    [Input({'type': 'legend-item', 'chart': 'pipeline', 'value': ALL}, 'n_clicks')],
    [State('selected-pipeline', 'data')],
    prevent_initial_call=True
)
def update_pipeline_selection_from_legend(n_clicks, sel_pipe):
    ctx = callback_context
    if not ctx.triggered or all(c is None for c in n_clicks):
        return no_update
    
    trigger_info = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
    val = trigger_info['value']
    
    new_sel = {'destination': val, 'is_categorical': True}
    if (sel_pipe and isinstance(sel_pipe, dict) and sel_pipe.get('is_categorical') and 
        sel_pipe.get('destination') == val):
        return None
    return new_sel

@callback(
    Output('seaborne-chart', 'figure'),
    [Input('year-check-filter', 'value'),
     Input('selected-seaborne', 'data'),
     Input('seaborne-agg-state', 'data')]
)
def update_seaborne_chart(selected_years, sel_sea, agg_mode):
    if not selected_years:
        return go.Figure().update_layout(template="simple_white", title="No years selected"), []
    
    try:
        agg_mode = agg_mode if agg_mode else 'monthly'
        
        years = sorted([int(y) for y in selected_years])
        timeline_df, year_annotations, month_separators, year_separators, num_years, year_centers = generate_timeline_data(years, mode=agg_mode)
        
        df_sea = load_seaborne_data(years)
        fig_sea = go.Figure()
        
        # Add visual logic: specific highlighting for year mode
        selected_year_mode = (sel_sea and isinstance(sel_sea, dict) and sel_sea.get('mode') == 'year_only')
        target_year = sel_sea.get('year') if selected_year_mode else None
                
        selected_month_mode = (sel_sea and isinstance(sel_sea, dict) and sel_sea.get('mode') == 'month_only')
        target_month = sel_sea.get('month') if selected_month_mode else None
        target_month_year = sel_sea.get('year') if selected_month_mode else None

        if not df_sea.empty:
            df_sea['year'] = df_sea['date'].dt.year
            # Aggregation grouping keys
            if agg_mode == 'monthly':
                 df_sea['group_key'] = df_sea['date'].dt.strftime('%B')
            elif agg_mode == 'quarterly':
                 df_sea['group_key'] = df_sea['date'].dt.to_period('Q').astype(str).str[-2:] # Q1, Q2 etc
            elif agg_mode == 'yearly':
                 df_sea['group_key'] = '' # Single group per year

            sea_grouped = df_sea.groupby(['year', 'group_key', 'type'])['vol_kbpd'].sum().reset_index()
            # If monthly, calc mean? No, user said "Y-axis rescales automatically... Monthly -> High... Yearly -> Highest".
            # Usually export data is sum per period. If viewing yearly, it should be sum of year?
            # User says "Y-axis rescales to higher values". So SUM is correct.
            
            # Merge keys need to match generate_timeline_data columns
            merge_col = 'month_name' if agg_mode == 'monthly' else ('quarter' if agg_mode == 'quarterly' else 'dummy')
            
            # Prepare dataframes for merge
            if agg_mode == 'monthly':
                sea_grouped = sea_grouped.rename(columns={'group_key': 'month_name'})
                join_on = ['year', 'month_name']
            elif agg_mode == 'quarterly':
                sea_grouped = sea_grouped.rename(columns={'group_key': 'quarter'})
                join_on = ['year', 'quarter']
            else: # Yearly
                sea_grouped['dummy'] = ''
                timeline_df['dummy'] = ''
                join_on = ['year', 'dummy']
            
            t1_name, t2_name = "Transneft Seaborne", "Bypassing Transneft"
            t1_data = timeline_df.merge(sea_grouped[sea_grouped['type'] == t1_name], on=join_on, how='left').fillna({'vol_kbpd': 0})
            t2_data = timeline_df.merge(sea_grouped[sea_grouped['type'] == t2_name], on=join_on, how='left').fillna({'vol_kbpd': 0})
            
            def get_marker(df, t_name):
                base_color = COLOR_MAP.get(t_name, '#333')
                colors, line_colors, line_widths = [], [], []
                for _, row in df.iterrows():
                    # Simplified highlighting for aggregated modes - usually disable detailed highlighting or keep year highlight
                    is_cat = (sel_sea and isinstance(sel_sea, dict) and sel_sea.get('is_categorical') and sel_sea['type'] == t_name)
                    
                    is_pin = False
                    if agg_mode == 'monthly':
                        is_pin = (sel_sea and isinstance(sel_sea, dict) and not sel_sea.get('is_categorical') and not sel_sea.get('mode') and
                                  sel_sea.get('type') == t_name and str(sel_sea.get('year')) == str(row['year']) and sel_sea.get('month') == row['month_name'])

                    if not sel_sea:
                        colors.append(base_color); line_colors.append('rgba(0,0,0,0)'); line_widths.append(0)
                    elif selected_year_mode:
                        # Year Highlight Mode
                        if str(row['year']) == str(target_year):
                            colors.append(base_color); line_colors.append('rgba(0,0,0,0)'); line_widths.append(0)
                        else:
                            colors.append(hex_to_rgba(base_color, 0.15)); line_colors.append('rgba(0,0,0,0)'); line_widths.append(0)
                    elif selected_month_mode and agg_mode == 'monthly':
                        # Month Highlight Mode only in monthly
                        if str(row['year']) == str(target_month_year) and row['month_name'] == target_month:
                            colors.append(base_color); line_colors.append('rgba(0,0,0,0)'); line_widths.append(0)
                        else:
                            colors.append(hex_to_rgba(base_color, 0.15)); line_colors.append('rgba(0,0,0,0)'); line_widths.append(0)
                    elif is_pin or is_cat:
                        colors.append(base_color); line_colors.append('black'); line_widths.append(2)
                    else:
                        colors.append(hex_to_rgba(base_color, 0.15)); line_colors.append('rgba(0,0,0,0)'); line_widths.append(0)
                return dict(color=colors, line=dict(color=line_colors, width=line_widths))

            fig_sea.add_trace(go.Bar(name=t1_name, x=t1_data['x_pos'], y=t1_data['vol_kbpd'], marker=get_marker(t1_data, t1_name),
                                   customdata=t1_data.apply(lambda r: [r['year'], r.get('month_name', ''), t1_name], axis=1),
                                   hovertemplate="<span style='color: grey'>Date:</span> %{customdata[1]} %{customdata[0]}<br><span style='color: grey'>Exports ('000 b/d):</span> %{y:,.0f}<extra></extra>"))
            fig_sea.add_trace(go.Bar(name=t2_name, x=t2_data['x_pos'], y=t2_data['vol_kbpd'], marker=get_marker(t2_data, t2_name),
                                   customdata=t2_data.apply(lambda r: [r['year'], r.get('month_name', ''), t2_name], axis=1),
                                   hovertemplate="<span style='color: grey'>Date:</span> %{customdata[1]} %{customdata[0]}<br><span style='color: grey'>Exports ('000 b/d):</span> %{y:,.0f}<extra></extra>"))
    
            # Add Clickable Year Header Bars (Background + Click Target)
            header_x = [yc['x'] for yc in year_centers]
            header_y = [1] * len(header_x) 
            header_widths = [yc['width'] for yc in year_centers] 
            
            # Determine colors based on selection
            header_colors = []
            for yc in year_centers:
                y = yc['year']
                if selected_year_mode and str(target_year) == str(y):
                    header_colors.append("rgba(0, 109, 156, 0.4)") # Selected Blue
                else:
                    header_colors.append("rgba(0, 0, 0, 0)") # Transparent for unselected
            
            fig_sea.add_trace(go.Bar(
                x=header_x, y=header_y,
                width=header_widths,
                yaxis='y2',
                marker=dict(color=header_colors, line=dict(width=0)), # No border
                hoverinfo='text',
                hovertext=[f"Click to filter {yc['year']}" for yc in year_centers],
                showlegend=False,
                customdata=[[yc['year'], 'YEAR_HEADER'] for yc in year_centers]
            ))
            
            # Year Icons (Interactive Traces)
            # White square with gray border and text, placed in the left margin area
            icon_symbol_text = "+" if agg_mode == 'yearly' else "-"
            
            # Dynamic margins to prevent "gap" in yearly mode
            if agg_mode == 'monthly':
                icon_x = -0.6
                margin_min = -1.2
            elif agg_mode == 'quarterly':
                icon_x = -0.2
                margin_min = -0.4
            else: # yearly
                icon_x = -0.08
                margin_min = -0.15
            
            fig_sea.add_trace(go.Scatter(
                x=[icon_x], 
                y=[0.5], # Middle of yaxis2
                yaxis='y2',
                mode='markers+text',
                marker=dict(symbol='square', size=12, color='white', line=dict(color='#d0d0d0', width=1)),
                text=[icon_symbol_text],
                textfont=dict(color='#505050', size=10, family='Arial'),
                textposition='middle center',
                hoverinfo='none',
                showlegend=False,
                customdata=[[year_centers[0]['year'], 'YEAR_ICON']] if year_centers else []
            ))

            # Month Header Trace (Only if Monthly or Quarterly)
            if agg_mode in ['monthly', 'quarterly']:
                label_size = 13 if num_years == 1 else (11 if num_years == 2 else (10 if num_years <= 6 else 9))
                fig_sea.add_trace(go.Bar(
                    x=timeline_df['x_pos'], y=[1] * len(timeline_df),
                    width=1, yaxis='y3',
                    marker=dict(color='rgba(0,0,0,0)'),
                    text=timeline_df['short_label'], textposition='inside',
                    textangle=0,
                    textfont=dict(color="grey", size=label_size),
                    hoverinfo='none', showlegend=False,
                    customdata=timeline_df.apply(lambda r: [r['year'], r.get('month_name', r.get('quarter','')), 'MONTH_HEADER'], axis=1)
                ))
            
            # Adjust separators logic
            shapes = []
            for s in month_separators:
                new_s = s.copy()
                if new_s.get('line', {}).get('color') == '#999999': # Month separator
                     new_s['y1'] = 0.88 
                     new_s['y0'] = 0 
                else:
                     # Year separator
                     new_s['y1'] = 1
                     new_s['y0'] = 0
                shapes.append(new_s)

            # Add horizontal line extension for visual continuity (Chart 1)
            shapes.append(dict(
                type="line",
                xref="paper", yref="paper",
                x0=-0.06, x1=1, # Extends into the left margin to cover axis ticks
                y0=0.78, y1=0.78, # At the top of the data area
                line=dict(color="#000", width=1),
                layer="below"
            ))

            max_x = timeline_df['x_pos'].max() + (0.6 if agg_mode == 'monthly' else 0.5)

            # Determine Visibility of Month Headers
            show_month_headers = (agg_mode != 'yearly')
            yaxis3_visible = show_month_headers

            fig_sea.update_layout(
                template="simple_white", barmode='group', height=300, margin=dict(l=40, r=40, t=30, b=10), showlegend=False,
                xaxis=dict(title=None, range=[margin_min, max_x], side='top', tickmode='array', tickvals=timeline_df['x_pos'], ticktext=timeline_df['short_label'] if show_month_headers else [], tickangle=0, showgrid=False, showline=True, linecolor='#000', ticks="", showticklabels=False),
                yaxis=dict(title=None, showgrid=True, gridcolor='#eee', dtick=(1000 if agg_mode=='monthly' else None), tickfont=dict(color="grey"), domain=[0, 0.78]),
                # yaxis2 for Year headers - enable line for left border
                yaxis2=dict(title=None, range=[0, 1], showgrid=False, showline=True, linecolor='black', showticklabels=False, visible=True, fixedrange=True, domain=[0.88, 1], ticks=""),
                # yaxis3 for Month headers - enable line for left border
                yaxis3=dict(title=None, range=[0, 1], showgrid=False, showline=True, linecolor='black', showticklabels=False, visible=yaxis3_visible, fixedrange=True, domain=[0.78, 0.88], ticks=""),
                dragmode=False, hovermode="closest", bargap=0.1, bargroupgap=0.05, shapes=shapes, annotations=year_annotations,
                hoverlabel=dict(bgcolor="white", font_size=13, font_color="black", bordercolor="#cccccc")
            )
        return fig_sea
    except Exception as e:
        print(f"Error in seaborne chart: {e}")
        return go.Figure().update_layout(title=f"Error: {e}")

@callback(
    [Output('pipeline-chart', 'figure'),
     Output('pipeline-title', 'children'),
     Output('pipeline-legend-container', 'children')],
    [Input('year-check-filter', 'value'),
     Input('direction-dropdown', 'value'),
     Input('selected-pipeline', 'data'),
     Input('pipeline-agg-state', 'data')]
)
def update_pipeline_chart(selected_years, direction_val, sel_pipe, agg_mode):
    if not selected_years:
        return go.Figure().update_layout(template="simple_white", title="No years selected"), "PIPELINE CRUDE EXPORTS ('000 b/d)", []
    
    try:
        years = sorted([int(y) for y in selected_years])
        timeline_df, year_annotations, month_separators, year_separators, num_years, year_centers = generate_timeline_data(years, mode=agg_mode)
        
        # Title and Legends
        if direction_val == 'China':
            pipe_title = "PIPELINE CRUDE EXPORTS TO CHINA ('000 b/d)"
            pipe_legend_items = [html.Div([html.Div(style={'width':'12px','height':'12px','backgroundColor':COLOR_MAP['China'],'marginRight':'8px'}),
                                           html.Span("China", style={'fontSize':'12px','color':'#333'})],
                                           style={'display':'flex','alignItems':'center','marginBottom':'5px','cursor':'pointer'},
                                           id={'type':'legend-item','chart':'pipeline','value':'China'})]
        else:
            pipe_title = "PIPELINE CRUDE EXPORTS TO EUROPE VIA DRUZHBA ('000 b/d)"
            pipe_legend_items = [html.Div([html.Div(style={'width':'12px','height':'12px','backgroundColor':COLOR_MAP[d],'marginRight':'8px'}),
                                           html.Span(d, style={'fontSize':'12px','color':'#333'})],
                                           style={'display':'flex','alignItems':'center','marginBottom':'5px','cursor':'pointer'},
                                           id={'type':'legend-item','chart':'pipeline','value':d})
                                 for d in DRUZHBA_DESTINATIONS if d in COLOR_MAP]

        df_pipe = load_pipeline_data(years)
        fig_pipe = go.Figure()

        # Add visual logic: specific highlighting for year mode
        selected_year_mode = (sel_pipe and isinstance(sel_pipe, dict) and sel_pipe.get('mode') == 'year_only')
        target_year = sel_pipe.get('year') if selected_year_mode else None

        selected_month_mode = (sel_pipe and isinstance(sel_pipe, dict) and sel_pipe.get('mode') == 'month_only')
        target_month = sel_pipe.get('month') if selected_month_mode else None
        target_month_year = sel_pipe.get('year') if selected_month_mode else None

        if not df_pipe.empty:
            df_pipe['year'] = df_pipe['date'].dt.year
            # Aggregation keys
            if agg_mode == 'monthly':
                 df_pipe['group_key'] = df_pipe['date'].dt.strftime('%B')
            elif agg_mode == 'quarterly':
                 df_pipe['group_key'] = df_pipe['date'].dt.to_period('Q').astype(str).str[-2:]
            elif agg_mode == 'yearly':
                 df_pipe['group_key'] = ''

            if direction_val == 'China':
                df_pipe = df_pipe[df_pipe['destination'] == 'China']
                destinations = ['China']
            else:
                df_pipe = df_pipe[df_pipe['destination'].isin(DRUZHBA_DESTINATIONS)]
                destinations = sorted(df_pipe['destination'].unique(), reverse=True)
            
            pipe_grouped = df_pipe.groupby(['year', 'group_key', 'destination'])['vol_kbpd'].sum().reset_index()
            
            # Merge keys
            merge_col = 'month_name' if agg_mode == 'monthly' else ('quarter' if agg_mode == 'quarterly' else 'dummy')
            
            if agg_mode == 'monthly':
                pipe_grouped = pipe_grouped.rename(columns={'group_key': 'month_name'})
                join_on = ['year', 'month_name']
            elif agg_mode == 'quarterly':
                pipe_grouped = pipe_grouped.rename(columns={'group_key': 'quarter'})
                join_on = ['year', 'quarter']
            else:
                pipe_grouped['dummy'] = ''
                timeline_df['dummy'] = ''
                join_on = ['year', 'dummy']
            
            for dest in destinations:
                dest_series = timeline_df.merge(pipe_grouped[pipe_grouped['destination'] == dest], on=join_on, how='left').fillna({'vol_kbpd': 0})
                base_color = COLOR_MAP.get(dest, '#333')
                colors, line_colors, line_widths = [], [], []
                
                for _, row in dest_series.iterrows():
                    is_cat = (sel_pipe and isinstance(sel_pipe, dict) and sel_pipe.get('is_categorical') and 
                             sel_pipe.get('destination') == dest)
                    
                    is_pin = False
                    if agg_mode == 'monthly':
                        is_pin = (sel_pipe and isinstance(sel_pipe, dict) and not sel_pipe.get('is_categorical') and not sel_pipe.get('mode') and
                                  sel_pipe.get('destination') == dest and 
                                  str(sel_pipe.get('year')) == str(row['year']) and 
                                  sel_pipe.get('month') == row.get('month_name', ''))

                    if not sel_pipe:
                        colors.append(base_color); line_colors.append('rgba(0,0,0,0)'); line_widths.append(0)
                    elif selected_year_mode:
                        # Year Highlight Mode
                        if str(row['year']) == str(target_year):
                            colors.append(base_color); line_colors.append('rgba(0,0,0,0)'); line_widths.append(0)
                        else:
                            colors.append(hex_to_rgba(base_color, 0.15)); line_colors.append('rgba(0,0,0,0)'); line_widths.append(0)
                    elif selected_month_mode and agg_mode == 'monthly':
                        # Month Highlight Mode
                        if str(row['year']) == str(target_month_year) and row['month_name'] == target_month:
                            colors.append(base_color); line_colors.append('rgba(0,0,0,0)'); line_widths.append(0)
                        else:
                            colors.append(hex_to_rgba(base_color, 0.15)); line_colors.append('rgba(0,0,0,0)'); line_widths.append(0)
                    elif is_pin or is_cat:
                        colors.append(base_color); line_colors.append('black'); line_widths.append(2)
                    else:
                        colors.append(hex_to_rgba(base_color, 0.15)); line_colors.append('rgba(0,0,0,0)'); line_widths.append(0)

                fig_pipe.add_trace(go.Bar(name=dest, x=dest_series['x_pos'], y=dest_series['vol_kbpd'],
                                        marker=dict(color=colors, line=dict(color=line_colors, width=line_widths)),
                                        customdata=dest_series.apply(lambda r: [r['year'], r.get('month_name', r.get('quarter','')), dest], axis=1),
                                        hovertemplate="<span style='color: grey'>Date:</span> %{customdata[1]} %{customdata[0]}<br><span style='color: grey'>Destination:</span> %{customdata[2]}<br><span style='color: grey'>Exports(000b/d):</span> %{y:,.0f}<extra></extra>"))
            
            # Add Clickable Year Header Bars (Background + Click Target)
            header_x = [yc['x'] for yc in year_centers]
            header_y = [1] * len(header_x)
            header_widths = [yc['width'] for yc in year_centers] 
            
            header_colors = []
            for yc in year_centers:
                y = yc['year']
                if selected_year_mode and str(target_year) == str(y):
                    header_colors.append("rgba(0, 109, 156, 0.4)")
                else:
                    header_colors.append("rgba(0, 0, 0, 0)")
            
            fig_pipe.add_trace(go.Bar(
                x=header_x, y=header_y,
                width=header_widths,
                yaxis='y2',
                marker=dict(color=header_colors, line=dict(width=0)),
                hoverinfo='text',
                hovertext=[f"Click to filter {yc['year']}" for yc in year_centers],
                showlegend=False,
                customdata=[[yc['year'], 'YEAR_HEADER'] for yc in year_centers]
            ))

            # Icon Trace (Year Toggle)
            icon_symbol_text = "+" if agg_mode == 'yearly' else "-"
            
            if agg_mode == 'monthly':
                icon_x = -0.6
                margin_min = -1.2
            elif agg_mode == 'quarterly':
                icon_x = -0.2
                margin_min = -0.4
            else: # yearly
                icon_x = -0.08
                margin_min = -0.15
            
            fig_pipe.add_trace(go.Scatter(
                x=[icon_x], 
                y=[0.5], # Middle of yaxis2
                yaxis='y2',
                mode='markers+text',
                marker=dict(symbol='square', size=12, color='white', line=dict(color='#d0d0d0', width=1)),
                text=[icon_symbol_text],
                textfont=dict(color='#505050', size=10, family='Arial'),
                textposition='middle center',
                hoverinfo='none',
                showlegend=False,
                customdata=[[year_centers[0]['year'], 'YEAR_ICON']] if year_centers else []
            ))

            # Month Header Trace (Clickable Labels)
            if agg_mode in ['monthly', 'quarterly']:
                label_size = 13 if num_years == 1 else (11 if num_years == 2 else (10 if num_years <= 6 else 9))
                fig_pipe.add_trace(go.Bar(
                    x=timeline_df['x_pos'], y=[1] * len(timeline_df),
                    width=1, yaxis='y3',
                    marker=dict(color='rgba(0,0,0,0)'),
                    text=timeline_df['full_label'], textposition='inside',
                    textangle=-90,
                    textfont=dict(color="grey", size=label_size),
                    hoverinfo='none', showlegend=False,
                    customdata=timeline_df.apply(lambda r: [r['year'], r.get('month_name', r.get('quarter','')), 'MONTH_HEADER'], axis=1)
                ))
            
            shapes = []
            for s in month_separators:
                new_s = s.copy()
                new_s['layer'] = 'below'
                if new_s.get('line', {}).get('color') == '#999999': # Month separator
                     new_s['y1'] = 0.85 # Touches the bottom of Year Header
                     new_s['y0'] = 0 
                else:
                     # Year separator
                     new_s['y1'] = 1
                     new_s['y0'] = 0
                shapes.append(new_s)
            
            max_x = timeline_df['x_pos'].max() + (0.6 if agg_mode == 'monthly' else 0.5)

            # Determine Visibility of Month Headers
            show_month_headers = (agg_mode != 'yearly')
            yaxis3_visible = show_month_headers

            fig_pipe.update_layout(
                template="simple_white", barmode='stack' if direction_val == 'Druzhba' else 'group', height=300, margin=dict(l=40, r=40, t=30, b=10), showlegend=False,
                xaxis=dict(title=None, range=[margin_min, max_x], tickmode='array', tickvals=timeline_df['x_pos'], ticktext=timeline_df['full_label'] if show_month_headers else [], tickangle=-90, showgrid=False, showline=True, linecolor='#000', ticks="", showticklabels=False),
                yaxis=dict(title=None, showgrid=True, gridcolor='#eee', dtick=(500 if agg_mode == 'quarterly' else None), tickfont=dict(color="grey"), domain=[0.15, 0.80]),
                # yaxis2 for headers - enable line for left border
                yaxis2=dict(title=None, range=[0, 1], showgrid=False, showline=True, linecolor='black', showticklabels=False, visible=True, fixedrange=True, domain=[0.85, 1], ticks=""),
                # yaxis3 for Month headers - enable line for left border
                yaxis3=dict(title=None, range=[0, 1], showgrid=False, showline=True, linecolor='black', showticklabels=False, visible=yaxis3_visible, fixedrange=True, domain=[0, 0.12], ticks=""),
                dragmode=False, hovermode="closest", bargap=0.25, shapes=shapes, annotations=year_annotations,
                hoverlabel=dict(bgcolor="white", font_size=13, font_color="black", bordercolor="#cccccc")
            )
        return fig_pipe, pipe_title, pipe_legend_items
    except Exception as e:
        print(f"Error in pipeline chart: {e}")
        return go.Figure().update_layout(title=f"Error: {e}"), "Error", [] # Return 3 outputs to match signature

@callback(
    Output("download-seaborne-csv", "data"),
    Input("export-seaborne-btn", "n_clicks"),
    State("year-check-filter", "value"),
    prevent_initial_call=True
)
def export_seaborne_data(n_clicks, selected_years):
    if not n_clicks or not selected_years:
        return no_update
        
    try:
        years = sorted([int(y) for y in selected_years])
        df_sea = load_seaborne_data(years)
        
        if df_sea.empty:
            return no_update
            
        df_sea['year'] = df_sea['date'].dt.year
        df_sea['month_num'] = df_sea['date'].dt.month
        df_sea['month_name'] = df_sea['date'].dt.strftime('%B')
        
        # Aggregate to match chart data, including month_num for sorting
        sea_grouped = df_sea.groupby(['year', 'month_num', 'month_name', 'type'])['vol_kbpd'].sum().reset_index()
        
        # Sort by year and month number
        sea_grouped = sea_grouped.sort_values(['year', 'month_num'])
        
        # Drop month_num before export
        sea_grouped = sea_grouped.drop(columns=['month_num'])
        
        # Add timestamp to filename
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        filename = f"seaborne_exports_{timestamp}.csv"
        
        return dcc.send_data_frame(sea_grouped.to_csv, filename, index=False)
    except Exception as e:
        print(f"Error exporting seaborne data: {e}")
        return no_update

@callback(
    Output("download-pipeline-csv", "data"),
    Input("export-pipeline-btn", "n_clicks"),
    [State("year-check-filter", "value"),
     State("direction-dropdown", "value")],
    prevent_initial_call=True
)
def export_pipeline_data(n_clicks, selected_years, direction_val):
    if not n_clicks or not selected_years:
        return no_update
        
    try:
        years = sorted([int(y) for y in selected_years])
        df_pipe = load_pipeline_data(years)
        
        if df_pipe.empty:
            return no_update
            
        df_pipe['year'] = df_pipe['date'].dt.year
        df_pipe['month_num'] = df_pipe['date'].dt.month
        df_pipe['month_name'] = df_pipe['date'].dt.strftime('%B')
        
        if direction_val == 'China':
            df_pipe = df_pipe[df_pipe['destination'] == 'China']
        else:
            df_pipe = df_pipe[df_pipe['destination'].isin(DRUZHBA_DESTINATIONS)]
        
        # Aggregate to match chart data, including month_num for sorting
        pipe_grouped = df_pipe.groupby(['year', 'month_num', 'month_name', 'destination'])['vol_kbpd'].sum().reset_index()
        
        # Sort by year and month number
        pipe_grouped = pipe_grouped.sort_values(['year', 'month_num'])
        
        # Drop month_num before export
        pipe_grouped = pipe_grouped.drop(columns=['month_num'])
        
        # Add timestamp to filename
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        filename_prefix = "pipeline_exports_china" if direction_val == 'China' else "pipeline_exports_druzhba"
        filename = f"{filename_prefix}_{timestamp}.csv"
        
        return dcc.send_data_frame(pipe_grouped.to_csv, filename, index=False)
    except Exception as e:
        print(f"Error exporting pipeline data: {e}")
        return no_update

def register_callbacks(app, server):
    pass
