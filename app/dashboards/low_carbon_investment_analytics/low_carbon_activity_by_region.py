"""
Activity by Region
Low-carbon investment activity analytics by region
"""
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, State, callback_context, no_update
from core.data_helpers import execute_query

# Color scheme matching the reference image
EI_ORANGE = "#fe5000"
EI_DARK_BLUE = "#1b365d"

def hex_to_rgba(hex_color, opacity):
    hex_color = hex_color.lstrip('#')
    lv = len(hex_color)
    rgb = tuple(int(hex_color[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
    return f'rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {opacity})'

# Status colors from the reference image
STATUS_COLORS = {
    'Divested': '#8b4513',           # Dark brown
    'Completed': '#d2691e',          # Orange/brown
    'Under Development': '#4682b4',  # Blue
    'Proposed': '#c0cf95',           # Light green
    'Cancelled': '#e8f4d8'           # Pale green
}

# Project category colors (matching fig3)
CATEGORY_COLORS = {
    'CCS & Carbon Removal': '#8b4513',
    'Electricity Solutions': '#d2691e',
    'EVs & Mobility': '#4682b4',
    'Hydrogen & L-C Fuels/Gases': '#f4a460', # Sandy Brown / Yellowish
    'L-C Power Generation': '#c0cf95',
    'Other': '#e8f4d8'
}

# Peer group colors (matching fig3)
PEER_GROUP_COLORS = {
    'European Major': '#1b365d',
    'Independent E&P': '#c0cf95',
    'Independent Refiner': '#999999',
    'Industrial Gas and Chemicals Manufacturer': '#f0e442',
    'Midstream Firm': '#d55e00',
    'NOC': '#8b4513',
    'US Major': '#fe5000',
    'Other': '#e8f4d8'
}

# Investment type colors (matching fig3)
INVESTMENT_TYPE_COLORS = {
    'Acquisition': '#007ba7',
    'Capex Investment': '#444444',
    'Joint Venture': '#c0cf95',
    'MOU': '#a9a9a9',
    'Other': '#fe5000',
    'R&D': '#4169e1',
    'VC Investment': '#8b4513'
}


def _format_date_for_display(date):
    """Format date as 'YYYY-MM-DD' (e.g., '2019-01-01')"""
    if pd.isna(date) or date is None:
        return ""
    if isinstance(date, str):
        date = pd.to_datetime(date, errors='coerce')
    if pd.isna(date):
        return ""
    return date.strftime('%Y-%m-%d')  # Standard format for date inputs

def _index_to_date(index, date_list):
    """Convert slider index to date"""
    if not date_list or index < 0 or index >= len(date_list):
        return pd.Timestamp.now()
    return date_list[index]

def _date_to_index(date_str, date_list):
    """Convert date string to slider index"""
    if not date_list or not date_str:
        return 0
    
    try:
        date = pd.to_datetime(date_str)
        # Find closest date
        # This assumes date_list is sorted
        for i, d in enumerate(date_list):
            if d >= date:
                return i
        return len(date_list) - 1
    except:
        return 0

def create_layout():
    """Create the Activity by Region layout"""
    # Fetch min and max dates from database for dynamic range
    min_max_query = """
    SELECT MIN(date_announced) as min_date, MAX(date_announced) as max_date
    FROM fact_et_assets
    WHERE new_status <> 'Uncertain'
    """
    
    try:
        date_result = execute_query(min_max_query, {})
        if date_result and date_result[0]['min_date'] and date_result[0]['max_date']:
            min_date_val = pd.to_datetime(date_result[0]['min_date'])
            max_date_val = pd.to_datetime(date_result[0]['max_date'])
        else:
            # Fallback if query fails or returns no data
            min_date_val = pd.Timestamp('2015-01-01')
            max_date_val = pd.Timestamp('2025-12-31')
    except Exception as e:
        print(f"Error fetching date range: {e}")
        min_date_val = pd.Timestamp('2015-01-01')
        max_date_val = pd.Timestamp('2025-12-31')

    # Create a daily date list from min to max
    date_list = pd.date_range(start=min_date_val, end=max_date_val, freq='D')
    
    # Set default range to most recent 10 years
    default_end_date = max_date_val
    default_start_date = max_date_val - pd.DateOffset(years=10)
    
    # Ensure start date is not before available data
    if default_start_date < min_date_val:
        default_start_date = min_date_val
        
    # Find indices for default range
    default_start_index = 0
    default_end_index = len(date_list) - 1
    
    # Find closest indices
    for i, date in enumerate(date_list):
        if date >= default_start_date:
            default_start_index = i
            break
            
    # Format dates for display
    min_date_str = _format_date_for_display(min_date_val)
    max_date_str = _format_date_for_display(max_date_val)
    default_start_date_str = _format_date_for_display(default_start_date)
    default_end_date_str = _format_date_for_display(default_end_date)
    
    return html.Div([
        # Data stores
        dcc.Store(id='low-carbon-measure-store', data='investment_value'),
        dcc.Store(id='low-carbon-breakdown-store', data='status'),
        dcc.Store(id='low-carbon-chart-selection', data=None),
        dcc.Store(id='low-carbon-is-expanded', data=False),
        dcc.Store(id='low-carbon-latest-date', data=None),
        dcc.Store(id='low-carbon-date-list-store', data=[d.isoformat() for d in date_list]),
        dcc.Download(id='low-carbon-download-csv'),
        
        # Clientside callback anchor
        html.Div(id='low-carbon-date-picker-enhancer-anchor', style={'display': 'none'}),
        
        # Header
        html.Div([
            html.H1(
                id='low-carbon-title',
                children="Low-Carbon Investment Activity by Region - Investment Value",
                style={
                    'color': EI_ORANGE,
                    'fontSize': '24px',
                    'fontWeight': 'normal',
                    'fontFamily': 'Arial, sans-serif',
                    'margin': '0',
                    'padding': '10px 20px'
                }
            )
        ], style={'borderBottom': '1px solid #ddd', 'backgroundColor': '#fff'}),
        
        # Main container
        html.Div([
            # Main content area (Left - 80%)
            html.Div([
                # Chart area
                html.Div([
                    html.Div([
                        html.Button(
                            "Export to CSV",
                            id="low-carbon-export-csv-btn",
                            style={
                                'backgroundColor': 'white',
                                'color': EI_DARK_BLUE,
                                'border': '1px solid #ddd',
                                'padding': '4px 8px',
                                'borderRadius': '4px',
                                'fontSize': '11px',
                                'cursor': 'pointer',
                                'position': 'absolute',
                                'top': '10px',
                                'right': '20px',
                                'zIndex': '1000'
                            }
                        )
                    ]),
                    
                    dcc.Loading(
                        id='loading-low-carbon-chart',
                        type='circle',
                        children=[
                            dcc.Graph(
                                id='low-carbon-chart',
                                config={'displayModeBar': False},
                                style={'height': '600px'}
                            )
                        ]
                    ),
                    # Drill-down Buttons (Outside Loading to avoid overlay issues)
                    html.Div(
                        "+",
                        id="low-carbon-plus-btn",
                        title="Expand to Country View",
                        n_clicks=0,
                        style={
                            'position': 'absolute',
                            'bottom': '75px',
                            'left': '45px',
                            'width': '18px',
                            'height': '18px',
                            'border': '2px solid #666',
                            'borderRadius': '2px',
                            'backgroundColor': 'white',
                            'color': '#333',
                            'fontSize': '16px',
                            'fontWeight': 'bold',
                            'lineHeight': '14px',
                            'textAlign': 'center',
                            'cursor': 'pointer',
                            'zIndex': '100',
                            'display': 'block',
                            'userSelect': 'none'
                        }
                    ),
                    html.Div(
                        "–",
                        id="low-carbon-minus-btn",
                        title="Collapse to Region View",
                        n_clicks=0,
                        style={
                            'position': 'absolute',
                            'top': '40px',
                            'left': '45px',
                            'width': '18px',
                            'height': '18px',
                            'border': '2px solid #666',
                            'borderRadius': '2px',
                            'backgroundColor': 'white',
                            'color': '#333',
                            'fontSize': '16px',
                            'fontWeight': 'bold',
                            'lineHeight': '14px',
                            'textAlign': 'center',
                            'cursor': 'pointer',
                            'zIndex': '100',
                            'display': 'none',
                            'userSelect': 'none'
                        }
                    )
                ], id='low-carbon-chart-container', n_clicks=0, style={
                    'padding': '20px',
                    'position': 'relative',
                    'cursor': 'pointer'
                })
            ], style={
                'width': '80%',
                'display': 'inline-block',
                'verticalAlign': 'top'
            }),
            
            # Filters sidebar (Right - 20%)
            html.Div([
                # Announcement Date Filter
                html.Div([
                    html.Label(
                        "Announcement Date",
                        style={
                            'fontWeight': 'bold',
                            'color': EI_DARK_BLUE,
                            'fontSize': '16px',
                            'marginBottom': '10px',
                            'display': 'block',
                            'fontFamily': 'Arial, sans-serif'
                        }
                    ),
                    html.Div([
                        html.Div([
                            html.Div([
                                dcc.Input(
                                    id='low-carbon-start-date',
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
                                        'borderRadius': '4px',
                                        'padding': '0 2px',
                                        'color': '#333',
                                        'cursor': 'pointer'
                                    }
                                ),
                            ], style={'marginRight': '65px'}),
                            html.Div([
                                dcc.Input(
                                    id='low-carbon-end-date',
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
                                        'borderRadius': '4px',
                                        'padding': '0 2px',
                                        'color': '#333',
                                        'cursor': 'pointer'
                                    }
                                ),
                            ]),
                        ], style={'width': 'auto', 'display': 'flex', 'gap': '0px', 'marginBottom': '10px', 'alignItems': 'center'}),
                    ], style={'marginBottom': '5px', 'fontFamily': 'Arial, sans-serif', 'overflow': 'hidden'}),
                    dcc.RangeSlider(
                        id='low-carbon-date-filter',
                        min=0,
                        max=len(date_list) - 1,
                        value=[default_start_index, default_end_index],
                        step=1,
                        marks=None,
                        tooltip={"placement": "bottom", "always_visible": False}
                    ),
                ], style={'marginBottom': '30px'}),
                
                # Measure Filter
                html.Div([
                    html.Label(
                        "Measure",
                        style={
                            'fontWeight': 'bold',
                            'color': '#333',
                            'fontSize': '14px',
                            'marginBottom': '10px',
                            'display': 'block'
                        }
                    ),
                    dcc.Dropdown(
                        id='low-carbon-measure-filter',
                        options=[
                            {'label': 'Investment Value', 'value': 'investment_value'},
                            {'label': 'Investment Count', 'value': 'investment_count'}
                        ],
                        value='investment_value',
                        clearable=False,
                        style={'fontSize': '14px'}
                    )
                ], style={'marginBottom': '30px'}),
                
                # Breakdown Filter
                html.Div([
                    html.Label(
                        "Breakdown",
                        style={
                            'fontWeight': 'bold',
                            'color': '#333',
                            'fontSize': '14px',
                            'marginBottom': '10px',
                            'display': 'block'
                        }
                    ),
                    dcc.Dropdown(
                        id='low-carbon-breakdown-filter',
                        options=[
                            {'label': 'Status', 'value': 'status'},
                            {'label': 'Project Category', 'value': 'project_category'},
                            {'label': 'Peer Group', 'value': 'peer_group'},
                            {'label': 'Investment Type', 'value': 'investment_type'}
                        ],
                        value='status',
                        clearable=False,
                        style={'fontSize': '14px'}
                    )
                ], style={'marginBottom': '30px'}),
                
                # Legend
                html.Div([
                    html.Label(
                        "Legend",
                        style={
                            'fontWeight': 'bold',
                            'color': '#777',
                            'fontSize': '12px',
                            'marginBottom': '10px',
                            'display': 'block'
                        }
                    ),
                    html.Div(id='low-carbon-legend-items')
                ], style={'borderTop': '2px solid #eee', 'paddingTop': '15px'})
                
            ], style={
                'width': '20%',
                'display': 'inline-block',
                'verticalAlign': 'top',
                'padding': '20px',
                'backgroundColor': '#fff',
                'borderLeft': '1px solid #ddd',
                'minHeight': '100vh'
            })
        ], style={'display': 'flex'}),
        
        # Footer
        html.Div([
            html.Div([
                html.Span(
                    "Source: Energy Intelligence, Low-Carbon Investment Tracker. Data as of ",
                    style={'fontSize': '11px', 'color': '#666', 'fontFamily': 'Arial, sans-serif'}
                ),
                html.Span(
                    id='low-carbon-footer-date',
                    children="",
                    style={'fontSize': '11px', 'color': '#666', 'fontFamily': 'Arial, sans-serif'}
                ),
                html.Span(
                    ". Covers activity by leading oil and gas firms, tracked by date initially announced or approved. Reported or estimated value is net for companies tracked. For more information see methodology. ",
                    style={'fontSize': '11px', 'color': '#666', 'fontFamily': 'Arial, sans-serif'}
                ),
                html.A(
                    "Go To Low-Carbon Investment Tracker",
                    href="https://www.energyintel.com/low-carbon-energy-data#low-carbon-investment-data",
                    target="_blank",
                    style={
                        'fontSize': '11px',
                        'color': '#fe5000',
                        'fontFamily': 'Arial, sans-serif',
                        'textDecoration': 'underline',
                        'cursor': 'pointer'
                    }
                )
            ], style={
                'padding': '15px 20px',
                'backgroundColor': '#fff',
                'borderTop': '1px solid #ddd'
            })
        ])
    ], className='tab-content', style={
        'backgroundColor': '#ffffff',
        'minHeight': '100vh',
        'fontFamily': 'Arial, sans-serif'
    })


def register_callbacks(dash_app, server):
    """Register all callbacks for the dashboard"""
    
    # Clientside callback to enhance date pickers (hide icon, show on click)
    dash_app.clientside_callback(
        """
        function(n_clicks, start_id, end_id) {
            // Create a style element to hide the calendar icon but keep it clickable
            var styleId = 'date-input-style-overrides';
            if (!document.getElementById(styleId)) {
                var style = document.createElement('style');
                style.id = styleId;
                style.innerHTML = `
                    input[type="date"]::-webkit-calendar-picker-indicator {
                        opacity: 0 !important;
                        pointer-events: none !important;
                        width: 0px;
                        display: none;
                    }
                    input[type="date"]::-webkit-inner-spin-button,
                    input[type="date"]::-webkit-outer-spin-button {
                        -webkit-appearance: none;
                        margin: 0;
                    }
                `;
                document.head.appendChild(style);
            }
            
            // Helper to setup date input
            function setupDateInput(id) {
                var input = document.getElementById(id);
                if (input) {
                    input.addEventListener('click', function(e) {
                        try {
                            if (typeof this.showPicker === 'function') {
                                this.showPicker();
                            } else {
                                console.log('showPicker API not supported');
                            }
                        } catch (error) {
                            console.log('Error opening picker:', error);
                        }
                    });
                }
            }
            
            // Setup both inputs with a slight delay to ensure they exist
            setTimeout(function() {
                setupDateInput(start_id);
                setupDateInput(end_id);
            }, 500);
            
            return window.dash_clientside.no_update;
        }
        """,
        Output('low-carbon-date-picker-enhancer-anchor', 'children'),
        Input('low-carbon-date-picker-enhancer-anchor', 'id'), # Dummy trigger
        [State('low-carbon-start-date', 'id'),
         State('low-carbon-end-date', 'id')]
    )

    @dash_app.callback(
        [Output('low-carbon-start-date', 'value'),
         Output('low-carbon-end-date', 'value'),
         Output('low-carbon-date-filter', 'value')],
        [Input('low-carbon-start-date', 'value'),
         Input('low-carbon-end-date', 'value'),
         Input('low-carbon-date-filter', 'value')],
        [State('low-carbon-date-list-store', 'data')],
        prevent_initial_call=True
    )
    def sync_date_controls(start_str, end_str, slider_val, date_list):
        ctx = callback_context
        if not ctx.triggered or not date_list:
            return no_update, no_update, no_update
            
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Parse date list back to Timestamp
        try:
            dates = [pd.Timestamp(d) for d in date_list]
        except:
            return no_update, no_update, no_update
            
        if trigger_id == 'low-carbon-date-filter':
            # Slider moved -> Update inputs
            if not slider_val or len(slider_val) < 2:
                return no_update, no_update, no_update
                
            start_idx, end_idx = slider_val
            
            # Ensure valid indices
            start_idx = max(0, min(start_idx, len(dates)-1))
            end_idx = max(0, min(end_idx, len(dates)-1))
            
            new_start = _format_date_for_display(dates[int(start_idx)])
            new_end = _format_date_for_display(dates[int(end_idx)])
            
            # Check equality - start_str and end_str are current values from Input
            if new_start == start_str and new_end == end_str:
                return no_update, no_update, no_update
                
            return new_start, new_end, no_update
            
        elif trigger_id == 'low-carbon-start-date' or trigger_id == 'low-carbon-end-date':
            # Inputs changed -> Update slider
            
            # Use current value of the OTHER input which comes from `end_str` or `start_str` arguments
            # Note: start_str and end_str are the values of the inputs at trigger time.
            
            target_start = start_str
            target_end = end_str
            
            if not target_start or not target_end:
                 return no_update, no_update, no_update
                
            try:
                start_idx = _date_to_index(target_start, dates)
                end_idx = _date_to_index(target_end, dates)
                
                # Ensure start <= end
                # Because changing one input might invalidate the range, we adjust.
                if start_idx > end_idx:
                    if trigger_id == 'low-carbon-start-date':
                        # If start moved past end, push end
                        end_idx = start_idx
                        target_end = target_start
                    else:
                        # If end moved before start, push start
                        start_idx = end_idx
                        target_start = target_end
                
                slider_val = [start_idx, end_idx]
                
                # If we implicitly updated an input (like start pushing end), we must return it
                if target_start != start_str or target_end != end_str:
                     return target_start, target_end, slider_val
                
                return no_update, no_update, slider_val
                
            except Exception as e:
                print(f"Error syncing dates: {e}")
                return no_update, no_update, no_update
                
        return no_update, no_update, no_update

    # Update title based on measure
    @dash_app.callback(
        Output('low-carbon-title', 'children'),
        Input('low-carbon-measure-filter', 'value')
    )
    def update_title(measure):
        measure_label = "Investment Value" if measure == 'investment_value' else "Investment Count"
        return f"Low-Carbon Investment Activity by Region - {measure_label}"
    
    # Update legend based on breakdown
    @dash_app.callback(
        Output('low-carbon-legend-items', 'children'),
        Input('low-carbon-breakdown-filter', 'value')
    )
    def update_legend(breakdown):
        # Select color map based on breakdown
        if breakdown == 'status':
            color_map = STATUS_COLORS
        elif breakdown == 'project_category':
            color_map = CATEGORY_COLORS
        elif breakdown == 'peer_group':
            color_map = PEER_GROUP_COLORS
        else:  # investment_type
            color_map = INVESTMENT_TYPE_COLORS
        
        # Define strict order for legend
        if breakdown == 'status':
            order = ['Divested', 'Completed', 'Under Development', 'Proposed', 'Cancelled']
        elif breakdown == 'project_category':
            order = ['CCS & Carbon Removal', 'Electricity Solutions', 'EVs & Mobility', 'Hydrogen & L-C Fuels/Gases', 'L-C Power Generation', 'Other']
        elif breakdown == 'peer_group':
            order = ['European Major', 'Independent E&P', 'Independent Refiner', 'Industrial Gas and Chemicals Manufacturer', 'Midstream Firm', 'NOC', 'US Major', 'Other']
        else: # investment_type
            order = ['Acquisition', 'Capex Investment', 'Joint Venture', 'MOU', 'Other', 'R&D', 'VC Investment']
            
        legend_items = []
        for label in order:
            if label not in color_map:
                continue
            color = color_map[label]
            legend_items.append(
                html.Div([
                    html.Div(
                        style={
                            'width': '12px',
                            'height': '12px',
                            'backgroundColor': color,
                            'display': 'inline-block',
                            'marginRight': '8px',
                            'border': '1px solid #ddd'
                        }
                    ),
                    html.Span(label, style={'fontSize': '11px', 'color': '#555'})
                ], style={
                    'display': 'flex',
                    'alignItems': 'center',
                    'marginBottom': '8px'
                })
            )
        
        return legend_items
    
    # Handle chart selection
    @dash_app.callback(
        [Output('low-carbon-chart-selection', 'data'),
         Output('low-carbon-chart', 'clickData')],
        [Input('low-carbon-chart', 'clickData'),
         Input('low-carbon-measure-filter', 'value'),
         Input('low-carbon-breakdown-filter', 'value'),
         Input('low-carbon-chart-container', 'n_clicks'),
         Input('low-carbon-is-expanded', 'data')],
        State('low-carbon-chart-selection', 'data'),
        prevent_initial_call=True
    )
    def toggle_chart_selection(click_data, measure, breakdown, n_clicks_bg, is_expanded, current_sel):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update
        
        triggers = [t['prop_id'] for t in ctx.triggered]
        chart_triggered = any('low-carbon-chart.clickData' in t for t in triggers)
        container_triggered = any('low-carbon-chart-container.n_clicks' in t for t in triggers)
        
        # Reset on filter or expansion changes
        if any(x in triggers[0] for x in ['measure-filter', 'breakdown-filter', 'is-expanded']):
            return None, None
        
        # 1. Chart Click (Bar Interaction)
        if chart_triggered and click_data:
            point = click_data['points'][0]
            
            # Use customdata for robust selection
            if 'customdata' not in point:
                return no_update, no_update
                
            c_data = point['customdata']
            # Based on: [x_label, Region, Breakdown, x_pos]
            try:
                breakdown_val = c_data[2]
                x_pos = int(c_data[3])
            except (IndexError, TypeError, ValueError):
                return no_update, no_update
                
            new_sel = {'x_pos': x_pos, 'breakdown': breakdown_val}
            
            # Toggle logic
            if current_sel and current_sel == new_sel:
                return None, None
            
            return new_sel, None
        
        # 2. Background Click (Container Clicked but not Chart Click)
        elif container_triggered and not chart_triggered:
            if current_sel:
                return None, None
            return no_update, no_update
        
        return no_update, no_update
    
    @dash_app.callback(
        [Output('low-carbon-is-expanded', 'data'),
         Output('low-carbon-plus-btn', 'style'),
         Output('low-carbon-minus-btn', 'style')],
        [Input('low-carbon-plus-btn', 'n_clicks'),
         Input('low-carbon-minus-btn', 'n_clicks')],
        [State('low-carbon-is-expanded', 'data'),
         State('low-carbon-plus-btn', 'style'),
         State('low-carbon-minus-btn', 'style')],
        prevent_initial_call=True
    )
    def toggle_drilldown(plus_clicks, minus_clicks, is_expanded, plus_style, minus_style):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update
        
        trigger_id = ctx.triggered[0]['prop_id']
        
        if 'low-carbon-plus-btn.n_clicks' == trigger_id:
            plus_style['display'] = 'none'
            minus_style['display'] = 'block'
            return True, plus_style, minus_style
        
        elif 'low-carbon-minus-btn.n_clicks' == trigger_id:
            plus_style['display'] = 'block'
            minus_style['display'] = 'none'
            return False, plus_style, minus_style
            
        return no_update, no_update, no_update

    # Update chart
    @dash_app.callback(
        [Output('low-carbon-chart', 'figure'),
         Output('low-carbon-latest-date', 'data')],
        [Input('low-carbon-measure-filter', 'value'),
         Input('low-carbon-breakdown-filter', 'value'),
         Input('low-carbon-chart-selection', 'data'),
         Input('low-carbon-is-expanded', 'data'),
         Input('low-carbon-date-filter', 'value')],
        [State('low-carbon-date-list-store', 'data')]
    )
    def update_chart(measure, breakdown, selection, is_expanded, date_range, date_list):
        if not date_list or not date_range:
            start_date = '2015-01-01'
            end_date = '2025-12-31'
        else:
            try:
                # Resolve indices to dates from the store
                start_idx = int(date_range[0])
                end_idx = int(date_range[1])
                
                # Ensure indices are within bounds
                start_idx = max(0, min(start_idx, len(date_list)-1))
                end_idx = max(0, min(end_idx, len(date_list)-1))
                
                start_date = date_list[start_idx][:10] # Take YYYY-MM-DD
                end_date = date_list[end_idx][:10]
            except Exception as e:
                print(f"Error resolving dates: {e}")
                start_date = '2015-01-01'
                end_date = '2025-12-31'
        
        # Get latest date from database
        latest_date_query = """
        SELECT MAX(a.date_announced) AS latest_date
        FROM fact_et_assets a
        WHERE a.new_status <> 'Uncertain'
        """
        
        try:
            latest_date_result = execute_query(latest_date_query, {})
            latest_date = latest_date_result[0]['latest_date'] if latest_date_result else None
            if latest_date:
                latest_date_str = latest_date.strftime('%-m/%-d/%Y')
            else:
                latest_date_str = "N/A"
        except Exception as e:
            print(f"Error fetching latest date: {e}")
            latest_date_str = "N/A"
        
        # SQL Query with country granularity
        query = f"""
        SELECT
            c.et_region                                   AS "Region",
            c.country_long_name                           AS "Country",
            a.new_status                                  AS "Status",
            EXTRACT(YEAR FROM a.date_announced)::int      AS "Year Announced",
            a.investment_type                             AS "Investment Type",

            /* Measure logic */
            CASE
                WHEN :measure = 'investment_value'
                    THEN ROUND(SUM(a.investment_usd), 2)
                WHEN :measure = 'investment_count'
                    THEN COUNT(a.investment_usd)
            END                                           AS "Measure Value",

            /* Breakdown logic */
            CASE
                WHEN :breakdown = 'status'
                    THEN a.new_status
                WHEN :breakdown = 'project_category'
                    THEN a.project_category_1
                WHEN :breakdown = 'peer_group'
                    THEN b.peer_group_simple
                WHEN :breakdown = 'investment_type'
                    THEN a.investment_type
            END                                           AS "Breakdown"

        FROM fact_et_assets a
        LEFT JOIN dim_company b
            ON a.company_id = b.company_id
        LEFT JOIN dim_country c
            ON a.country_id = c.dim_country_id

        WHERE a.new_status <> 'Uncertain'
          AND a.date_announced >= :start_date
          AND a.date_announced <= :end_date

        GROUP BY
            c.et_region,
            c.country_long_name,
            a.new_status,
            EXTRACT(YEAR FROM a.date_announced),
            a.investment_type,
            CASE
                WHEN :breakdown = 'status'
                    THEN a.new_status
                WHEN :breakdown = 'project_category'
                    THEN a.project_category_1
                WHEN :breakdown = 'peer_group'
                    THEN b.peer_group_simple
                WHEN :breakdown = 'investment_type'
                    THEN a.investment_type
            END

        ORDER BY
            "Year Announced" DESC,
            "Breakdown";
        """
        
        params = {
            'measure': measure,
            'breakdown': breakdown,
            'start_date': start_date,
            'end_date': end_date
        }
        
        try:
            results = execute_query(query, params)
            df = pd.DataFrame(results)
        except Exception as e:
            print(f"Error executing query: {e}")
            return go.Figure(), latest_date_str
        
        if df.empty:
            return go.Figure(), latest_date_str
        
        # Process data
        df['Measure Value'] = pd.to_numeric(df['Measure Value'], errors='coerce').fillna(0)
        
        # Scale Investment Value to Billions if applicable
        if measure == 'investment_value':
            df['Measure Value'] = df['Measure Value'] / 1000  # Assuming original is in millions to get Billion
        
        # Aggregate based on expansion level
        if is_expanded:
            agg_df = df.groupby(['Region', 'Country', 'Breakdown'], as_index=False)['Measure Value'].sum()
            x_label = 'Country'
        else:
            agg_df = df.groupby(['Region', 'Breakdown'], as_index=False)['Measure Value'].sum()
            x_label = 'Region'
            
        agg_df = agg_df[agg_df['Measure Value'] > 0]
        agg_df = agg_df.dropna(subset=['Region', 'Breakdown'])
        
        if agg_df.empty:
            return go.Figure(), latest_date_str
        
        # Sort regions by total value
        region_totals = agg_df.groupby('Region')['Measure Value'].sum().sort_values(ascending=False)
        region_order = region_totals.index.tolist()
        
        # Define x-axis order and map to x_pos
        if is_expanded:
            country_totals = agg_df.groupby(['Region', 'Country'])['Measure Value'].sum().reset_index()
            country_totals['RegionCat'] = pd.Categorical(country_totals['Region'], categories=region_order, ordered=True)
            country_totals = country_totals.sort_values(['RegionCat', 'Measure Value'], ascending=[True, False])
            x_axis_labels = country_totals['Country'].tolist()
        else:
            x_axis_labels = region_order

        # Create x_axis mapping
        x_axis_df = pd.DataFrame({x_label: x_axis_labels, 'x_pos': range(len(x_axis_labels))})
        agg_df = agg_df.merge(x_axis_df, on=x_label, how='left')

        # Define strict Order for Breakdown (bottom to top for stacking)
        if breakdown == 'status':
            breakdown_order = ['Cancelled', 'Proposed', 'Under Development', 'Completed', 'Divested']
            color_map = STATUS_COLORS
        elif breakdown == 'project_category':
            breakdown_order = ['Other', 'L-C Power Generation', 'Hydrogen & L-C Fuels/Gases', 'EVs & Mobility', 'Electricity Solutions', 'CCS & Carbon Removal']
            color_map = CATEGORY_COLORS
        elif breakdown == 'peer_group':
            breakdown_order = ['Other', 'US Major', 'NOC', 'Midstream Firm', 'Industrial Gas and Chemicals Manufacturer', 'Independent Refiner', 'Independent E&P', 'European Major']
            color_map = PEER_GROUP_COLORS
        else: # investment_type
            breakdown_order = ['VC Investment', 'R&D', 'Other', 'MOU', 'Joint Venture', 'Capex Investment', 'Acquisition']
            color_map = INVESTMENT_TYPE_COLORS
        
        # Create grouped traces
        fig = go.Figure()
        
        # Get unique countries for trace creation
        if is_expanded:
            unique_countries = agg_df['Country'].unique()
            # Ensure 'Country' column exists in agg_df for expanded view
            if 'Country' not in agg_df.columns:
                agg_df = df.groupby(['Region', 'Country', 'Breakdown'], as_index=False)['Measure Value'].sum()
                agg_df = agg_df[agg_df['Measure Value'] > 0]
                agg_df = agg_df.dropna(subset=['Region', 'Breakdown'])
                agg_df = agg_df.merge(x_axis_df, on=x_label, how='left')
        else:
            # For region view, we need country-level data to split bars
            # Re-aggregate with country granularity
            country_df = df.groupby(['Region', 'Country', 'Breakdown'], as_index=False)['Measure Value'].sum()
            country_df = country_df[country_df['Measure Value'] > 0]
            country_df = country_df.dropna(subset=['Region', 'Breakdown'])
            
            # Map regions to x_pos
            region_x_map = {region: idx for idx, region in enumerate(x_axis_labels)}
            country_df['x_pos'] = country_df['Region'].map(region_x_map)
            
            unique_countries = country_df['Country'].unique()
        
        # Create one trace per (breakdown, country) combination
        for b_val in breakdown_order:
            for country in unique_countries:
                if is_expanded:
                    trace_data = agg_df[
                        (agg_df['Breakdown'] == b_val) & 
                        (agg_df['Country'] == country)
                    ].copy()
                else:
                    trace_data = country_df[
                        (country_df['Breakdown'] == b_val) & 
                        (country_df['Country'] == country)
                    ].copy()
                
                if trace_data.empty:
                    continue
                
                # Ensure strict sorting by x_pos
                trace_data = trace_data.sort_values('x_pos')
                    
                base_color = color_map.get(b_val, '#999999')
                
                marker_colors = []
                marker_lines = []
                
                for _, row in trace_data.iterrows():
                    row_x_pos = row['x_pos']
                    
                    is_selected = (
                        selection and 
                        selection.get('breakdown') == b_val and 
                        int(selection.get('x_pos')) == int(row_x_pos)
                    )

                    if not selection:
                        marker_colors.append(base_color)
                        marker_lines.append(dict(color='white', width=0.5))
                    elif is_selected:
                        marker_colors.append(base_color)
                        marker_lines.append(dict(color='black', width=2.0))
                    else:
                        # Others - dimmed
                        marker_colors.append(hex_to_rgba(base_color, 0.2))
                        marker_lines.append(dict(color='white', width=0.5))

                value_label = f"{measure.replace('_', ' ').title()}"
                unit = " ($ Billion)" if measure == 'investment_value' else ""
                
                if breakdown == 'project_category':
                    breakdown_label = "Project Category"
                elif breakdown == 'peer_group':
                    breakdown_label = "Peer Group"
                elif breakdown == 'investment_type':
                    breakdown_label = "Investment Type"
                else:
                    breakdown_label = breakdown.replace('_', ' ').title()

                # Customdata: [x_label_val, Region, Breakdown, x_pos, Country]
                # x_label_val is Country if expanded, Region if not expanded
                trace_customdata = []
                for _, row in trace_data.iterrows():
                    x_label_val_for_row = row[x_label]
                    region_for_row = row['Region'] if 'Region' in row else None # Should always be present
                    trace_customdata.append([x_label_val_for_row, region_for_row, b_val, row['x_pos'], country])
                
                fig.add_trace(go.Bar(
                    name=f"{b_val}_{country}",
                    x=trace_data['x_pos'],
                    y=trace_data['Measure Value'],
                    legendgroup=b_val,
                    showlegend=False,
                    marker=dict(
                        color=marker_colors,
                        line=dict(
                            color=[l['color'] for l in marker_lines],
                            width=[l['width'] for l in marker_lines]
                        )
                    ),
                    customdata=trace_customdata,
                    hovertemplate=(
                        f"<span style='color: #666; font-weight: normal;'>{breakdown_label}:</span> "
                        f"<span style='color: #000; font-weight: normal;'>{b_val}</span><br>"
                        f"<span style='color: #666; font-weight: normal;'>Region:</span> "
                        f"<span style='color: #000; font-weight: normal;'>%{{customdata[1]}}</span><br>"
                        f"<span style='color: #666; font-weight: normal;'>{value_label}:</span> "
                        f"<span style='color: #000; font-weight: normal;'>%{{y:,.2f}}{unit}</span><br>"
                        f"<span style='color: #666; font-weight: normal;'>Host Country:</span> "
                        f"<span style='color: #000; font-weight: normal;'>%{{customdata[4]}}</span>"
                        "<extra></extra>"
                    )
                ))


        
        # Expanded View Decorations
        if is_expanded:
            # Region grouping lines and labels
            current_idx = 0
            for region in region_order:
                region_countries = country_totals[country_totals['Region'] == region]['Country'].tolist()
                num_countries = len(region_countries)
                if num_countries == 0: continue
                
                # Midpoint for label (relative to the count of countries so far)
                label_x = current_idx + (num_countries - 1) / 2
                
                fig.add_annotation(
                    x=label_x,
                    y=1.05,
                    xref="x",
                    yref="paper",
                    text=f"<b>{region}</b>",
                    showarrow=False,
                    font=dict(size=12, color='#333'),
                    yshift=10
                )
                
                # Separation line (to the right of the region block)
                if current_idx + num_countries < len(x_axis_labels):
                    fig.add_shape(
                        type="line",
                        x0=current_idx + num_countries - 0.5,
                        x1=current_idx + num_countries - 0.5,
                        y0=0,
                        y1=1.05,
                        xref="x",
                        yref="paper",
                        line=dict(color="#bbb", width=1.5, dash="dot")
                    )
                
                current_idx += num_countries

        # Update layout
        measure_label = "Investment Value ($ Billion)" if measure == 'investment_value' else "Investment Count"
        
        fig.update_layout(
            barmode='stack',
            xaxis=dict(
                title=None,
                tickvals=list(range(len(x_axis_labels))),
                ticktext=x_axis_labels,
                tickangle=0 if not is_expanded else -90,
                tickfont=dict(size=11 if not is_expanded else 9, color='#666')
            ),
            yaxis=dict(
                title=measure_label,
                titlefont=dict(size=12, color='#666'),
                tickfont=dict(size=10, color='#666'),
                gridcolor='#f0f0f0',
                zeroline=True,
                zerolinecolor='#ccc',
                range=[0, None]
            ),
            showlegend=False,
            margin=dict(l=80, r=150, t=100 if is_expanded else 40, b=120 if is_expanded else 80),
            height=600,
            font=dict(family="Arial, sans-serif"),
            plot_bgcolor='white',
            paper_bgcolor='white',
            hoverlabel=dict(
                bgcolor="white",
                bordercolor="#ccc",
                font_size=11,
                font_family="Arial, sans-serif",
                font_color="#000",
                align="left"
            )
        )
        
        return fig, latest_date_str
        # Sync date labels with slider
    @dash_app.callback(
        [Output('low-carbon-start-date-label', 'children'),
         Output('low-carbon-end-date-label', 'children')],
        [Input('low-carbon-date-filter', 'value')]
    )
    def update_date_labels(date_range):
        if not date_range or len(date_range) < 2:
            return no_update, no_update
        start_dt = datetime(2015, 1, 1) + timedelta(days=date_range[0])
        end_dt = datetime(2015, 1, 1) + timedelta(days=date_range[1])
        return start_dt.strftime('%-m/%-d/%Y'), end_dt.strftime('%-m/%-d/%Y')
    
    # Update footer date
    @dash_app.callback(
        Output('low-carbon-footer-date', 'children'),
        Input('low-carbon-latest-date', 'data')
    )
    def update_footer_date(latest_date):
        return latest_date if latest_date else ""

    # Export to CSV
    @dash_app.callback(
        Output('low-carbon-download-csv', 'data'),
        Input('low-carbon-export-csv-btn', 'n_clicks'),
        [State('low-carbon-measure-filter', 'value'),
         State('low-carbon-breakdown-filter', 'value'),
         State('low-carbon-date-filter', 'value')],
        prevent_initial_call=True
    )
    def export_csv(n_clicks, measure, breakdown, date_range):
        start_date = (datetime(2015, 1, 1) + timedelta(days=date_range[0])).strftime('%Y-%m-%d')
        end_date = (datetime(2015, 1, 1) + timedelta(days=date_range[1])).strftime('%Y-%m-%d')
        if not n_clicks:
            return no_update
        
        # Query to get aggregated data matching the chart
        query = """
        SELECT
            c.et_region                                   AS "Region",
            c.country_long_name                           AS "Country",
            CASE
                WHEN :breakdown = 'status'
                    THEN a.new_status
                WHEN :breakdown = 'project_category'
                    THEN a.project_category_1
                WHEN :breakdown = 'peer_group'
                    THEN b.peer_group_simple
                WHEN :breakdown = 'investment_type'
                    THEN a.investment_type
            END                                           AS "Breakdown",
            CASE
                WHEN :measure = 'investment_value'
                    THEN ROUND(SUM(a.investment_usd) / 1000, 2)
                WHEN :measure = 'investment_count'
                    THEN COUNT(a.investment_usd)
            END                                           AS "Measure Value"

        FROM fact_et_assets a
        LEFT JOIN dim_company b
            ON a.company_id = b.company_id
        LEFT JOIN dim_country c
            ON a.country_id = c.dim_country_id

        WHERE a.new_status <> 'Uncertain'
          AND a.date_announced >= :start_date
          AND a.date_announced <= :end_date

        GROUP BY
            c.et_region,
            c.country_long_name,
            CASE
                WHEN :breakdown = 'status'
                    THEN a.new_status
                WHEN :breakdown = 'project_category'
                    THEN a.project_category_1
                WHEN :breakdown = 'peer_group'
                    THEN b.peer_group_simple
                WHEN :breakdown = 'investment_type'
                    THEN a.investment_type
            END

        ORDER BY
            c.et_region,
            c.country_long_name,
            "Breakdown";
        """
        
        params = {
            'measure': measure, 
            'breakdown': breakdown,
            'start_date': start_date,
            'end_date': end_date
        }
        
        try:
            results = execute_query(query, params)
            df = pd.DataFrame(results)
            
            # Rename columns based on selected filters
            measure_label = "Investment Value ($ Billion)" if measure == 'investment_value' else "Investment Count"
            
            if breakdown == 'status':
                breakdown_label = "Status"
            elif breakdown == 'project_category':
                breakdown_label = "Project Category"
            elif breakdown == 'peer_group':
                breakdown_label = "Peer Group"
            else:  # investment_type
                breakdown_label = "Investment Type"
            
            # Rename columns for clarity
            df = df.rename(columns={
                'Breakdown': breakdown_label,
                'Measure Value': measure_label
            })
            
            # Reorder columns
            df = df[['Region', 'Country', breakdown_label, measure_label]]
            
            return dcc.send_data_frame(df.to_csv, f"low_carbon_activity_{measure}_{breakdown}.csv", index=False)
        except Exception as e:
            print(f"Error exporting CSV: {e}")
            return no_update