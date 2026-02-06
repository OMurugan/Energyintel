from dash import html, dcc, Input, Output, State, callback, clientside_callback
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from core.data_helpers import execute_query
import dash
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Color mapping for Companies based on user design
COMPANY_COLORS = {
    'Rosneft': '#1B365D',
    'Lukoil': '#5B92B9',
    'Gazprom Neft': '#3A414A',
    'Gazprom': '#3A414A',
    'Others': '#A66144',
    'Tatneft': '#595959',
    'Surgutneftegas': '#C3D09A',
    'Slavneft': '#FF4500',
    'TAIF': '#007BA7',
    'ForteInvest': '#7A88CC',
    'NNK': '#A9A9A9',
    'Novatek': '#9E5235',
    'Orsk': '#A6A6A6',
    'New Stream': '#D9D9D9'
}

DEFAULT_COLOR = '#CCCCCC'

# Ordering for Stacked Bar and Treemap
COMPANY_ORDER = [
    'Rosneft', 'Lukoil', 'Gazprom Neft', 'Others', 'Tatneft', 'Surgutneftegas', 'ForteInvest', 'Slavneft', 'TAIF', 'NNK', 'Novatek', 'Gazprom'
]

# Display name overrides for cleaner labels
DISPLAY_NAMES = {
    'Surgutneftegas': 'Surgut',
    'ForteInvest': 'FortelInvest'
}

# Standard legend order for Gasoline/Oil products
LIVE_LEGEND_ORDER = [
    'ForteInvest', 'NNK', 'TAIF', 'Others', 'Surgutneftegas', 
    'Slavneft', 'Tatneft', 'Gazprom', 'Gazprom Neft', 'Lukoil', 'Rosneft'
]

def hex_to_rgba(hex_color, alpha=1.0):
    """Convert hex color to rgba string"""
    try:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"
    except:
        return f"rgba(200, 200, 200, {alpha})"

# Mapping from Treemap selection (Refinery Output) to Breakdown Chart (Refining And Products Output)
REFINERY_TO_BREAKDOWN_MAP = {
    'Diesel': 'Diesel And Gasoil',
    'Gasoline': 'Gasoline',
    'Heavy Fuel Oils': 'VGO',
    'Mazut': 'Fuel Oil',
    'Naphtha': 'Naphtha',
    'Jet Fuel': 'Jet Fuel And Kerosene',
    'Petroleum Coke': 'Petroleum Coke',
    'Bitumen-Residues': 'Bitumen And Residue'
}

PRODUCT_DISPLAY_OVERRIDES = {
    'Bitumen-Residues': 'Other'
}

def create_layout():
    """Create the Product Output layout with Tabs"""
    return html.Div([
        # Selection Stores
        dcc.Store(id='company-treemap-selection', data=None),
        dcc.Store(id='company-bar-selection', data=None),
        dcc.Store(id='product-treemap-selection', data=None),
        dcc.Store(id='product-company-selection', data=None),
        dcc.Store(id='product-expansion-store', data={'Year': False, 'Quarter': False, 'Month': True, 'Day': False}), 

        # Main Tab Container
        dcc.Tabs(id='product-output-tabs', value='by-company', children=[
            dcc.Tab(label='By Company', value='by-company', className='custom-tab', selected_className='custom-tab--selected'),
            dcc.Tab(label='By Product', value='by-product', className='custom-tab', selected_className='custom-tab--selected'),
        ], className='custom-tabs-container'),

        # Tab Content
        html.Div(id='product-output-content', style={'padding': '20px'}),

        # Downloads
        dcc.Download(id="download-company-treemap"),
        dcc.Download(id="download-company-bar"),
        dcc.Download(id="download-product-treemap"),
        dcc.Download(id="download-product-bar"),
    ], style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh', 'fontFamily': 'Arial, sans-serif'})

# Clientside callbacks for fast interactivity
clientside_callback(
    """
    function(clickData, currentSelection) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return [currentSelection, window.dash_clientside.no_update];
        }
        const point = clickData.points[0];
        if (!point.customdata || !Array.isArray(point.customdata) || point.customdata.length < 1) {
            return [null, null];
        }
        const clickedCompany = String(point.customdata[0] || '').trim();
        if (!clickedCompany) {
            return [null, null];
        }
        let nextSelection = clickedCompany;
        if (currentSelection && currentSelection === clickedCompany) {
            nextSelection = null;
        }
        return [nextSelection, null];
    }
    """,
    [Output('company-treemap-selection', 'data'),
     Output('company-treemap', 'clickData')],
    Input('company-treemap', 'clickData'),
    State('company-treemap-selection', 'data'),
    prevent_initial_call=True
)

clientside_callback(
    """
    function(clickData, currentSelection) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return [currentSelection, window.dash_clientside.no_update];
        }
        const point = clickData.points[0];
        if (!point.customdata || !Array.isArray(point.customdata) || point.customdata.length < 1) {
            return [null, null];
        }
        const clickedProduct = String(point.customdata[0] || '').trim();
        if (!clickedProduct) {
            return [null, null];
        }
        let nextSelection = clickedProduct;
        if (currentSelection && currentSelection === clickedProduct) {
            nextSelection = null;
        }
        return [nextSelection, null];
    }
    """,
    [Output('product-treemap-selection', 'data'),
     Output('product-treemap', 'clickData')],
    Input('product-treemap', 'clickData'),
    State('product-treemap-selection', 'data'),
    prevent_initial_call=True
)

clientside_callback(
    """
    function(clickData, currentSelection) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return [currentSelection, window.dash_clientside.no_update];
        }
        const point = clickData.points[0];
        if (!point.customdata || !Array.isArray(point.customdata) || point.customdata.length < 2) {
            return [null, null];
        }
        const company = String(point.customdata[0] || '').trim();
        const date = String(point.customdata[1] || '').trim();
        if (!company || !date) {
            return [null, null];
        }
        const clickedId = company + "|" + date;
        let nextSelection = clickedId;
        if (currentSelection && currentSelection === clickedId) {
            nextSelection = null;
        }
        return [nextSelection, null];
    }
    """,
    [Output('company-bar-selection', 'data'),
     Output('company-bar-chart', 'clickData')],
    Input('company-bar-chart', 'clickData'),
    State('company-bar-selection', 'data'),
    prevent_initial_call=True
)

clientside_callback(
    """
    function(clickData, currentSelection) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return [currentSelection, window.dash_clientside.no_update];
        }
        const point = clickData.points[0];
        if (!point.customdata || !Array.isArray(point.customdata) || point.customdata.length < 3) {
            return [null, null];
        }
        const clickedCompany = String(point.customdata[0] || '').trim();
        const slotId = String(point.customdata[2] || '').trim(); // NEW: slotId
        if (!clickedCompany || !slotId) {
            return [null, null];
        }
        const clickedId = clickedCompany + "|" + slotId;
        let nextSelection = clickedId;
        if (currentSelection && currentSelection === clickedId) {
            nextSelection = null;
        }
        return [nextSelection, null];
    }
    """,
    [Output('product-company-selection', 'data'),
     Output('product-bar-chart', 'clickData')],
    Input('product-bar-chart', 'clickData'),
    State('product-company-selection', 'data'),
    prevent_initial_call=True
)

@callback(
    [Output('product-expansion-store', 'data'),
     Output('btn-expand-year', 'children'),
     Output('btn-expand-quarter', 'children'),
     Output('btn-expand-month', 'children'),
     Output('btn-expand-day', 'children')],
    [Input('btn-expand-year', 'n_clicks'),
     Input('btn-expand-quarter', 'n_clicks'),
     Input('btn-expand-month', 'n_clicks'),
     Input('btn-expand-day', 'n_clicks')],
    [State('product-expansion-store', 'data')],
    prevent_initial_call=True
)
def update_expansion_state(y_c, q_c, m_c, d_c, current_visibility):
    from dash import callback_context
    ctx = callback_context
    if not ctx.triggered:
        return current_visibility, '+', '+', '-', '+'
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    new_visibility = current_visibility.copy() if current_visibility else {'Year': False, 'Quarter': False, 'Month': False, 'Day': False}
    
    if button_id == 'btn-expand-year':
        new_visibility['Year'] = not new_visibility.get('Year', False)
        if not new_visibility['Year']:
            new_visibility['Quarter'] = False
            new_visibility['Month'] = False
            new_visibility['Day'] = False
    elif button_id == 'btn-expand-quarter':
        new_visibility['Quarter'] = not new_visibility.get('Quarter', False)
        if new_visibility['Quarter']:
            new_visibility['Year'] = True
        else:
            new_visibility['Month'] = False
            new_visibility['Day'] = False
    elif button_id == 'btn-expand-month':
        new_visibility['Month'] = not new_visibility.get('Month', False)
        if new_visibility['Month']:
            new_visibility['Year'] = True
            new_visibility['Quarter'] = True
        else:
            new_visibility['Day'] = False
    elif button_id == 'btn-expand-day':
        new_visibility['Day'] = not new_visibility.get('Day', False)
        if new_visibility['Day']:
            new_visibility['Year'] = True
            new_visibility['Quarter'] = True
            new_visibility['Month'] = True
    
    return (
        new_visibility, 
        '-' if new_visibility.get('Year') else '+',
        '-' if new_visibility.get('Quarter') else '+',
        '-' if new_visibility.get('Month') else '+',
        '-' if new_visibility.get('Day') else '+'
    )

def create_by_company_layout():
    """Layout for the 'By Company' tab"""
    return html.Div([
        html.Div([
            # Left side: Charts
            html.Div([
                # Treemap Header
                html.Div([
                    html.H3(id='treemap-company-header', 
                            style={'margin': '0', 'fontWeight': 'bold', 'color': '#FF4500', 'fontSize': '22px'}),
                    html.Button("Export to CSV", id="btn-export-company-treemap", style={
                        'backgroundColor': 'white', 'color': '#2c3e50', 'border': '1px solid #dee2e6',
                        'padding': '5px 15px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '13px'
                    })
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
                
                # Treemap Chart
                dcc.Loading(
                    id="loading-company-treemap",
                    type="default",
                    color='#FF4500',
                    children=dcc.Graph(
                        id='company-treemap',
                        config={'displayModeBar': False},
                        style={'height': '350px', 'marginBottom': '40px'}
                    )
                ),

                # Stacked Bar Header
                html.Div([
                    html.H3(id='bar-company-header', 
                            style={'margin': '0', 'fontWeight': 'bold', 'color': '#FF4500', 'fontSize': '22px'}),
                    html.Button("Export to CSV", id="btn-export-company-bar", style={
                        'backgroundColor': 'white', 'color': '#2c3e50', 'border': '1px solid #dee2e6',
                        'padding': '5px 15px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '13px'
                    })
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'margin': '20px 0 10px 0'}),
                
                # Stacked Bar Chart
                dcc.Loading(
                    id="loading-company-bar",
                    type="default",
                    color='#FF4500',
                    children=dcc.Graph(
                        id='company-bar-chart',
                        config={'displayModeBar': False},
                        style={'height': '350px'}
                    )
                ),
                
                # Footer Source
                html.Div([
                    html.P("Energy Intelligence; data as of December 2025", 
                           style={'fontStyle': 'italic', 'fontSize': '12px', 'marginTop': '20px', 'color': '#1b365d'})
                ])

            ], style={'width': '88%', 'display': 'inline-block', 'verticalAlign': 'top'}),

            # Right side: Controls
            html.Div([
                # Year Selection
                html.Div([
                    html.Label("SELECT YEAR", style={'fontWeight': 'bold', 'fontSize': '13px', 'color': '#333', 'marginBottom': '10px', 'display': 'block'}),
                    dcc.RadioItems(
                        id='company-year-selector',
                        options=[
                            {'label': ' (All)', 'value': 'All'},
                            {'label': ' 2022', 'value': 2022},
                            {'label': ' 2023', 'value': 2023},
                            {'label': ' 2024', 'value': 2024},
                            {'label': ' 2025', 'value': 2025}
                        ],
                        value=2025,
                        labelStyle={'display': 'block', 'marginBottom': '2px', 'fontSize': '13px'}
                    )
                ], style={'marginBottom': '30px'}),

                # Product Selection
                html.Div([
                    html.Label("SELECT PRODUCT", style={'fontWeight': 'bold', 'fontSize': '13px', 'color': '#333', 'marginBottom': '10px', 'display': 'block'}),
                    dcc.RadioItems(
                        id='company-product-selector',
                        options=[
                            {'label': ' Bitumen And Resi...', 'value': 'Bitumen And Residues'},
                            {'label': ' Diesel And Gasoil', 'value': 'Diesel And Gasoil'},
                            {'label': ' Fuel Oil', 'value': 'Fuel Oil'},
                            {'label': ' Gasoline', 'value': 'Gasoline'},
                            {'label': ' Jet Fuel And Kero...', 'value': 'Jet Fuel And Kerosene'},
                            {'label': ' Naphtha', 'value': 'Naphtha'},
                            {'label': ' Petroleum Coke', 'value': 'Petroleum Coke'},
                            {'label': ' VGO', 'value': 'VGO'}
                        ],
                        value='Diesel And Gasoil',
                        labelStyle={'display': 'block', 'marginBottom': '2px', 'fontSize': '13px'}
                    )
                ])
            ], style={'width': '10%', 'display': 'inline-block', 'marginLeft': '2%', 'verticalAlign': 'top'})
        ], style={'display': 'flex', 'justifyContent': 'space-between'})
    ])

def create_by_product_layout():
    """Layout for the 'By Product' tab"""
    return html.Div([
        html.Div([
            # Left side: Charts
            html.Div([
                # Treemap Header
                html.Div([
                    html.H3(id='treemap-product-header', 
                            style={'margin': '0', 'fontWeight': 'bold', 'color': '#FF4500', 'fontSize': '22px'}),
                    html.Button("Export to CSV", id="btn-export-product-treemap", style={
                        'backgroundColor': 'white', 'color': '#2c3e50', 'border': '1px solid #dee2e6',
                        'padding': '5px 15px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '13px'
                    })
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
                
                # Treemap Chart
                dcc.Loading(
                    id="loading-product-treemap",
                    type="default",
                    color='#FF4500',
                    children=dcc.Graph(
                        id='product-treemap',
                        config={'displayModeBar': False},
                        style={'height': '350px', 'marginBottom': '40px'}
                    )
                ),

                # Stacked Bar Header
                html.Div([
                    html.H3(id='bar-product-header', 
                            style={'margin': '0', 'fontWeight': 'bold', 'color': '#FF4500', 'fontSize': '22px'}),
                    html.Button("Export to CSV", id="btn-export-product-bar", style={
                        'backgroundColor': 'white', 'color': '#2c3e50', 'border': '1px solid #dee2e6',
                        'padding': '5px 15px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '13px'
                    })
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'margin': '25px 0 10px 0'}),
                
                # Stacked Bar Chart with Overlay Controls
                html.Div([
                    # Hierarchy Level Controls (+/- buttons in corner)
                    html.Div([
                        html.Div([
                            html.Span("Year", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px', 'fontWeight': 'bold'}),
                            html.Button('+', id='btn-expand-year', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Quarter", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px', 'fontWeight': 'bold'}),
                            html.Button('+', id='btn-expand-quarter', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Month", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px', 'fontWeight': 'bold'}),
                            html.Button('-', id='btn-expand-month', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Day", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px', 'fontWeight': 'bold'}),
                            html.Button('+', id='btn-expand-day', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center'})
                    ], style={
                        'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#f8f9fa', 
                        'padding': '5px 10px', 'borderRadius': '4px', 'marginBottom': '0px',
                        'position': 'absolute', 'top': '0px', 'left': '0px', 'zIndex': '20'
                    }),

                    dcc.Loading(
                        id="loading-product-bar",
                        type="default",
                        color='#FF4500',
                        children=dcc.Graph(
                            id='product-bar-chart',
                            config={'displayModeBar': False},
                            style={'height': '420px', 'width': '100%'} 
                        )
                    )
                ], style={'position': 'relative', 'flex': '1', 'marginTop': '10px'}),
                
                # Footer Source
                html.Div([
                    html.P("Energy Intelligence; data as of December 2025", 
                           style={'fontStyle': 'italic', 'fontSize': '12px', 'marginTop': '20px', 'color': '#1b365d'})
                ])
            ], style={'flex': '1', 'minWidth': '0'}),

            # Right side: Controls & Legend
            html.Div([
                # Year Selection
                html.Div([
                    html.Label("SELECT YEAR", style={'fontWeight': 'bold', 'fontSize': '13px', 'color': '#333', 'marginBottom': '10px', 'display': 'block'}),
                    dcc.RadioItems(
                        id='product-year-selector',
                        options=[
                            {'label': ' 2022', 'value': 2022},
                            {'label': ' 2023', 'value': 2023},
                            {'label': ' 2024', 'value': 2024},
                            {'label': ' 2025', 'value': 2025}
                        ],
                        value=2025,
                        labelStyle={'display': 'block', 'marginBottom': '2px', 'fontSize': '13px'}
                    )
                ], style={'marginBottom': '30px'}),

                # Company Legend
                html.Div([
                    html.Label("Company", style={'fontWeight': 'bold', 'fontSize': '14px', 'color': '#333', 'marginBottom': '10px', 'display': 'block'}),
                    html.Div([
                        html.Div([
                            html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': COMPANY_COLORS.get(comp, DEFAULT_COLOR), 'display': 'inline-block', 'marginRight': '8px'}),
                            html.Span(DISPLAY_NAMES.get(comp, comp), style={'fontSize': '13px', 'color': '#555', 'fontWeight': '500'})
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '6px'})
                        for comp in LIVE_LEGEND_ORDER
                    ])
                ], style={'padding': '10px 0'})

            ], style={'width': '160px', 'flexShrink': '0', 'marginLeft': '25px', 'paddingTop': '40px'})
        ], style={'display': 'flex', 'flexDirection': 'row', 'justifyContent': 'flex-start', 'alignItems': 'flex-start'})
    ])

def register_callbacks(dash_app, server):
    """Register all callbacks for Product Output Analytics"""

    @callback(
        Output('product-output-content', 'children'),
        Input('product-output-tabs', 'value')
    )
    def render_tab_content(tab):
        if tab == 'by-company':
            return create_by_company_layout()
        elif tab == 'by-product':
            return create_by_product_layout()
        return html.Div("Select a tab")

    @callback(
        [Output('company-treemap', 'figure'),
         Output('treemap-company-header', 'children'),
         Output('company-bar-chart', 'figure'),
         Output('bar-company-header', 'children')],
        [Input('company-year-selector', 'value'),
         Input('company-product-selector', 'value'),
         Input('company-treemap-selection', 'data'),
         Input('company-bar-selection', 'data')]
    )
    def update_company_charts(selected_year, selected_product, treemap_sel, bar_sel):
        # Base query for Russia Product Output (Filtered to start from 2022 to match live dash)
        query = f"""
        SELECT company, date, vol_kbpd 
        FROM russia_master_data 
        WHERE category = 'Refining And Products Output' 
        AND commodity = '{selected_product}'
        """
        
        try:
            results = execute_query(query)
            df = pd.DataFrame(results)
            
            if df.empty:
                empty_fig = go.Figure()
                empty_fig.add_annotation(text="No data found", showarrow=False)
                return empty_fig, f"PRODUCERS OF {selected_product.upper()} ('000 b/d)", empty_fig, f"{selected_product.upper()} PRODUCTION ('000 b/d)"
            
            df['date'] = pd.to_datetime(df['date'])
            df['year'] = df['date'].dt.year
            df['vol_kbpd'] = pd.to_numeric(df['vol_kbpd'], errors='coerce').fillna(0)
            
            # Aggregate by company and date to handle duplicates as per user observation
            df = df.groupby(['company', 'date', 'year'])['vol_kbpd'].sum().reset_index()
            
            # --- TREEMAP DATA ---
            if selected_year == 'All':
                # For 'All Years', user expects sum of annual averages (e.g. 2022 avg + 2023 avg + ...)
                # derived from comparing ~500 (mean) vs ~2200 (live dashboard) for ~4 years.
                
                # 1. Calculate Average volume per Company per Year
                annual_avgs = df.groupby(['company', 'year'])['vol_kbpd'].mean().reset_index()
                
                # 2. Sum these annual averages for each company
                treemap_data = annual_avgs.groupby('company')['vol_kbpd'].sum().reset_index()
                
                # Generate dynamic title: "IN 2022, 2023, 2024 and X more"
                all_years = sorted(df['year'].unique())
                
                # Per user request, prioritize displaying years starting from 2022
                # But include all data in the "more" count
                display_candidates = [y for y in all_years if y >= 2022]
                if not display_candidates:
                    display_candidates = all_years
                
                shown_years = display_candidates[:3]
                remainder_count = len(all_years) - len(shown_years)
                
                if remainder_count > 0:
                     year_label_str = f"{', '.join(map(str, shown_years))} and {remainder_count} more"
                else:
                     year_label_str = ', '.join(map(str, shown_years))
                year_label = year_label_str 
                
            else:
                # For a specific year, use January (Month 1) as requested by the user
                target_year = int(selected_year)
                df_tree_snapshot = df[
                    (df['date'].dt.year == target_year) & 
                    (df['date'].dt.month == 1)
                ]
                year_label = str(selected_year)
                
                if df_tree_snapshot.empty:
                    treemap_data = pd.DataFrame(columns=['company', 'vol_kbpd'])
                else:
                    treemap_data = df_tree_snapshot.groupby('company')['vol_kbpd'].sum().reset_index()

            # Shared logic for both branches if data exists
            if treemap_data.empty:
                tree_fig = go.Figure()
                tree_fig.add_annotation(text=f"No data for {year_label}", showarrow=False)
            else:
                # Sort by volume descending to match "live" design as requested
                treemap_data = treemap_data.sort_values('vol_kbpd', ascending=False)
                
                total_vol = treemap_data['vol_kbpd'].sum()
                treemap_data['percentage'] = (treemap_data['vol_kbpd'] / total_vol * 100) if total_vol > 0 else 0
                
                # Map colors and highlighting
                ids = []
                marker_colors = []
                labels = []
                line_widths = []
                line_colors = []
                custom_data = []

                for _, row in treemap_data.iterrows():
                    company = row['company']
                    ids.append(company)
                    display_name = DISPLAY_NAMES.get(company, company)
                    base_color = COMPANY_COLORS.get(company, DEFAULT_COLOR)
                    
                    if treemap_sel and company != treemap_sel:
                        # Dim non-selected companies
                        marker_colors.append(hex_to_rgba(base_color, 0.3))
                        line_widths.append(0)
                        line_colors.append('rgba(0,0,0,0)')
                    elif treemap_sel and company == treemap_sel:
                        # Highlight selected company with black border
                        marker_colors.append(base_color)
                        line_widths.append(3)
                        line_colors.append('black')
                    else:
                        # Default state - no selection
                        marker_colors.append(base_color)
                        line_widths.append(0)
                        line_colors.append('rgba(0,0,0,0)')
                    # Determine precision based on product
                    precision = ".1f" if selected_product == 'VGO' else ".0f"
                    
                    labels.append(f"<b>{display_name}</b><br>{row['vol_kbpd']:{precision}} ('000 b/d)<br>{row['percentage']:.2f}%")
                    # CRITICAL: Keep original 'company' in customdata[0] for interactivity - ensure all elements exist
                    # Add safety checks to ensure no None/NaN values
                    company_str = str(company) if company is not None else 'Unknown'
                    vol_float = float(row['vol_kbpd']) if pd.notna(row['vol_kbpd']) else 0.0
                    pct_float = float(row['percentage']) if pd.notna(row['percentage']) else 0.0
                    custom_data.append([company_str, vol_float, pct_float])

                # Ensure customdata is never empty - add a fallback
                if not custom_data:
                    custom_data = [['No Data', 0.0, 0.0]]
                    ids = ['no-data']
                    labels = ['No Data Available']
                    marker_colors = ['#CCCCCC']
                    treemap_data = pd.DataFrame({'vol_kbpd': [0]})

                tree_fig = go.Figure(go.Treemap(
                    ids=ids,
                    labels=labels,
                    parents=[""] * len(labels),
                    values=treemap_data['vol_kbpd'],
                    textinfo="label",
                    marker=dict(colors=marker_colors, line=dict(width=line_widths, color=line_colors)),
                    customdata=custom_data,  # CRITICAL: Add customdata for click interactivity
                    tiling=dict(pad=2),
                    maxdepth=1,
                    hoverlabel=dict(bgcolor="white", font=dict(color="black", size=12, family="Arial"))
                ))
                tree_fig.update_layout(
                    margin=dict(t=0, b=0, l=0, r=0), 
                    uirevision=f"tree-{selected_year}-{selected_product}-{treemap_sel}",
                    clickmode='event'
                )

            # --- BAR CHART DATA ---
            # Group by month and company
            df['month_sort'] = df['date'].dt.to_period('M')
            # Use %y for 2-digit year to avoid truncation/splitting like Ma y..
            df['month_display'] = df['date'].dt.strftime('%b<br>%y') 
            df['hover_date'] = df['date'].dt.strftime('%b %Y')
            
            bar_data = df.groupby(['month_sort', 'month_display', 'hover_date', 'company'])['vol_kbpd'].sum().reset_index()
            bar_data = bar_data.sort_values('month_sort')
            
            bar_fig = go.Figure()
            unique_months = bar_data['month_display'].unique()
            
            companies_in_data = bar_data['company'].unique()
            # Calculate total volume per company to sort High to Low (bottom to top) as clarified by user
            company_totals = bar_data.groupby('company')['vol_kbpd'].sum().sort_values(ascending=False)
            sorted_companies = company_totals.index.tolist()

            for company in sorted_companies:
                # ONLY treemap selection filters the traces in the bar chart
                if treemap_sel and company != treemap_sel:
                    continue

                comp_df = bar_data[bar_data['company'] == company]
                # Reindex to ensure all months are presents
                comp_df = comp_df.set_index('month_display').reindex(unique_months).fillna({'vol_kbpd': 0, 'company': company})
                # Recover hover_date and month_display
                temp_map = bar_data[['month_display', 'hover_date']].drop_duplicates().set_index('month_display')
                comp_df['hover_date'] = temp_map.reindex(comp_df.index)['hover_date'].fillna('').values
                comp_df = comp_df.reset_index()

                base_color = COMPANY_COLORS.get(company, DEFAULT_COLOR)
                marker_colors = []
                line_widths = []
                line_colors = []
                
                for _, row in comp_df.iterrows():
                    point_id = f"{company}|{row['hover_date']}"
                    
                    if bar_sel:
                        # If a specific bar is clicked, highlight it and dim everything else
                        if point_id == bar_sel:
                            marker_colors.append(base_color)
                            line_widths.append(2)
                            line_colors.append('black')
                        else:
                            marker_colors.append(hex_to_rgba(base_color, 0.2))
                            line_widths.append(0)
                            line_colors.append('rgba(0,0,0,0)')
                    elif treemap_sel:
                        # If filtering by treemap, highlight the company's bars (though selection is primarily in treemap)
                        if company == treemap_sel:
                            marker_colors.append(base_color)
                            line_widths.append(1.5)
                            line_colors.append('black')
                        else:
                            # This branch is effectively unused due to the trace filtering loop above
                            marker_colors.append(hex_to_rgba(base_color, 0.2))
                            line_widths.append(0)
                            line_colors.append('rgba(0,0,0,0)')
                    else:
                        # Default state: no dimming, no highlight
                        marker_colors.append(base_color)
                        line_widths.append(0)
                        line_colors.append('rgba(0,0,0,0)')

                bar_fig.add_trace(go.Bar(
                    name=company,
                    x=comp_df['month_display'],
                    y=comp_df['vol_kbpd'],
                    marker=dict(color=marker_colors, line=dict(width=line_widths, color=line_colors)),
                    customdata=[[str(company), str(date)] for date in comp_df['hover_date']],  # Simple customdata for callbacks
                    hovertemplate="Company: " + company + "<br>Volume: %{y:,.0f} ('000 b/d)<extra></extra>",
                    hoverlabel=dict(bgcolor="white", font=dict(color="black", size=12, family="Arial"))
                ))

                # --- Y-Axis Configuration ---
                # Fixed range for high-volume products (Diesel) ONLY when NO treemap filter is active
                if selected_product == 'Diesel And Gasoil' and not treemap_sel:
                    yaxis_config = dict(
                        range=[0, 2500],
                        tickvals=[0, 1000, 2000],
                        dtick=1000
                    )
                else:
                    # Let plotter decide or set a simple range
                    yaxis_config = dict(range=[0, None])

                bar_fig.update_layout(
                    barmode='stack',
                    xaxis=dict(
                        title="", 
                        tickfont=dict(size=9, color='#1b365d'), 
                        type='category',
                        tickangle=0,
                        automargin=True
                    ),
                    yaxis=dict(
                        title="'000 b/d", 
                        gridcolor='#f0f0f0',
                        tickfont=dict(size=12, color='#1b365d'),
                        zerolinecolor='#f0f0f0',
                        **yaxis_config
                    ),
                showlegend=False,
                margin=dict(t=10, b=50, l=50, r=10),
                paper_bgcolor='white',
                plot_bgcolor='white',
                font=dict(family="Arial, sans-serif"),
                uirevision=f"bar-{selected_product}"
            )

            treemap_title = f"PRODUCERS OF {selected_product.upper()} IN {year_label} ('000 b/d)"
            bar_title = f"{selected_product.upper()} PRODUCTION ('000 b/d)"
            
            return tree_fig, treemap_title, bar_fig, bar_title

        except Exception as e:
            logger.error(f"Error updating company charts: {str(e)}")
            empty_fig = go.Figure()
            empty_fig.add_annotation(text="Error loading data", showarrow=False)
            return empty_fig, "Error Loading", empty_fig, "Error Loading"



    @callback(
        [Output('product-treemap', 'figure'),
         Output('treemap-product-header', 'children'),
         Output('product-bar-chart', 'figure'),
         Output('bar-product-header', 'children')],
        [Input('product-year-selector', 'value'),
         Input('product-treemap-selection', 'data'),
         Input('product-expansion-store', 'data'),
         Input('product-company-selection', 'data')]
    )
    def update_product_charts(selected_year, product_sel, expansion_state, company_sel):
        # Default expansion state if None
        if not expansion_state:
            expansion_state = {'year': True, 'q1': True, 'q2': True, 'q3': True, 'q4': True, 'm': {}}
            

        try:
            # 1. TOP TREEMAP: Production of Oil Products by Commodity (Category: Refinery Output)
            query_tree = f"""
            SELECT commodity, date, vol_kbpd 
            FROM russia_master_data 
            WHERE category = 'Refinery Output' 
            AND EXTRACT(YEAR FROM date) = {selected_year}
            """
            
            # 2. BOTTOM BAR CHART: Production by Company (Category: Refining And Products Output)
            target_product = product_sel if product_sel else 'Gasoline' 
            # Translate the selected commodity for the breakdown query
            breakdown_product = REFINERY_TO_BREAKDOWN_MAP.get(target_product, target_product)
            
            query_bar = f"""
            SELECT company, date, vol_kbpd 
            FROM russia_master_data 
            WHERE category = 'Refining And Products Output' 
            AND commodity = '{breakdown_product}'
            AND EXTRACT(YEAR FROM date) = {selected_year}
            """
            
            # --- Treemap Data Processing ---
            results_tree = execute_query(query_tree)
            df_tree = pd.DataFrame(results_tree)
            
            if df_tree.empty:
                tree_fig = go.Figure()
                tree_fig.add_annotation(text="No data found", showarrow=False)
                treemap_title = f"PRODUCTION OF OIL PRODUCTS IN {selected_year} ('000 b/d)"
            else:
                df_tree['vol_kbpd'] = pd.to_numeric(df_tree['vol_kbpd'], errors='coerce').fillna(0)
                df_tree['date'] = pd.to_datetime(df_tree['date'])
                
                # Annual Average of Monthly Sums:
                monthly_sums = df_tree.groupby(['commodity', 'date'])['vol_kbpd'].sum().reset_index()
                treemap_data = monthly_sums.groupby('commodity')['vol_kbpd'].mean().reset_index()
                treemap_data = treemap_data.sort_values('vol_kbpd', ascending=False)
                
                total_vol    = treemap_data['vol_kbpd'].sum()
                treemap_data['percentage'] = (treemap_data['vol_kbpd'] / total_vol * 100) if total_vol > 0 else 0
                
                # Color and Display mapping based on live design images
                PRODUCT_COLOR_MAP = {
                    'Diesel': '#595959',
                    'Gasoline': '#5B92B9',
                    'Heavy Fuel Oils': '#A9A9A9',
                    'Mazut': '#8E5431',
                    'Naphtha': '#1B365D',
                    'Others': '#FF4500',
                    'Jet Fuel': '#B85B35',
                    'Other Heavy Fuels': '#3A414A',
                    'Bitumen-Residues': '#7A88CC',
                    'Fuel Oil and VGO': '#2F3E4D',
                    'Petroleum Coke': '#FF4500'
                }
                

                ids = []
                marker_colors = []
                labels = []
                custom_data = []
                
                for i, row in treemap_data.iterrows():
                    prod = row['commodity']
                    ids.append(prod)
                    display_name = PRODUCT_DISPLAY_OVERRIDES.get(prod, prod)
                    base_color = PRODUCT_COLOR_MAP.get(prod, '#CCCCCC')
                    
                    if product_sel and prod != product_sel:
                        clr = hex_to_rgba(base_color, 0.4)
                    else:
                        clr = base_color
                    
                    marker_colors.append(clr)
                    labels.append(f"<b>{display_name}</b><br>{row['vol_kbpd']:,.0f} ('000 b/d)<br>{row['percentage']:.2f}%")
                    # Add safety checks to ensure no None/NaN values
                    display_name_str = str(display_name) if display_name is not None else 'Unknown'
                    vol_float = float(row['vol_kbpd']) if pd.notna(row['vol_kbpd']) else 0.0
                    pct_float = float(row['percentage']) if pd.notna(row['percentage']) else 0.0
                    custom_data.append([display_name_str, vol_float, pct_float])

                # Ensure customdata is never empty - add a fallback
                if not custom_data:
                    custom_data = [['No Data', 0.0, 0.0]]
                    ids = ['no-data']
                    labels = ['No Data Available']
                    marker_colors = ['#CCCCCC']
                    treemap_data = pd.DataFrame({'vol_kbpd': [0]})

                tree_fig = go.Figure(go.Treemap(
                    ids=ids,
                    labels=labels,
                    parents=[""] * len(labels),
                    values=treemap_data['vol_kbpd'],
                    textinfo="label",
                    marker=dict(colors=marker_colors),
                    customdata=custom_data,  # Keep for clientside callbacks
                    hoverlabel=dict(
                        bgcolor="white",
                        font_size=12,
                        font_family="Arial",
                        font_color="black"
                    ),
                    tiling=dict(pad=2)
                ))
                tree_fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                treemap_title = f"PRODUCTION OF OIL PRODUCTS IN {selected_year} ('000 b/d)"

            # --- Pie Chart Row Data Processing (12 months) ---
            results_bar = execute_query(query_bar)
            df_bar = pd.DataFrame(results_bar)
            
            # Display name for the title
            display_product = PRODUCT_DISPLAY_OVERRIDES.get(target_product, target_product)

            if df_bar.empty:
                bar_fig = go.Figure()
                bar_fig.add_annotation(text=f"No data for {display_product}", showarrow=False)
                bar_title = f"{display_product.upper()} PRODUCTION BY COMPANY ('000 b/d)"
            else:
                bar_fig = go.Figure()
                df_bar['date'] = pd.to_datetime(df_bar['date'])
                df_bar['vol_kbpd'] = pd.to_numeric(df_bar['vol_kbpd'], errors='coerce').fillna(0)
                
                year_expanded = expansion_state.get('year', False)
                # --- Hierarchical Slots Calculation ---
                month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                               'July', 'August', 'September', 'October', 'November', 'December']
                
                # Get available months for the selected year to avoid showing ghost December (per user feedback)
                available_months = sorted(df_bar['date'].dt.month.unique()) if not df_bar.empty else range(1, 13)
                
                slots = []
                # Determine granularity level
                gran_level = 'YEAR'
                if expansion_state.get('Day'): gran_level = 'DAY'
                elif expansion_state.get('Month'): gran_level = 'MONTH'
                elif expansion_state.get('Quarter'): gran_level = 'QUARTER'
                
                if gran_level == 'YEAR':
                    slots.append({'type': 'year', 'id': selected_year, 'label': str(selected_year)})
                elif gran_level == 'QUARTER':
                    for q in [1, 2, 3, 4]:
                        q_month_range = {1: [1, 2, 3], 2: [4, 5, 6], 3: [7, 8, 9], 4: [10, 11, 12]}[q]
                        if any(m in available_months for m in q_month_range):
                            slots.append({'type': 'quarter', 'id': q, 'label': f'Q{q}'})
                elif gran_level == 'MONTH':
                    for m in available_months:
                        slots.append({'type': 'month', 'id': m, 'label': month_names[m-1]})
                elif gran_level == 'DAY':
                    for m in available_months:
                        slots.append({'type': 'day', 'id': m, 'label': month_names[m-1], 'sub_label': '1'})

                num_slots = len(slots)
                total_chart_width = 1.0
                col_width = total_chart_width / num_slots

                # Add Centered Year Title only if expanded beyond the root root Year pie
                if expansion_state.get('year', False):
                    bar_fig.add_annotation(
                        text=f"<b>{selected_year}</b>",
                        x=0.5, y=0.97,
                        xref="paper", yref="paper",
                        showarrow=False,
                        font=dict(size=14, color="black"),
                        xanchor="center"
                    )

                # Add Gray Bar for Labels
                bar_fig.add_shape(
                    type="rect",
                    x0=0, y0=0.87, x1=1, y1=0.93,
                    xref="paper", yref="paper",
                    fillcolor="#f8f9fa", line=dict(width=0)
                )

                # --- Slots Rendering ---

                for i, slot in enumerate(slots):
                    center_x = i * col_width + (col_width / 2)
                    left_x = i * col_width
                    
                    # Data Filtering based on slot type
                    if slot['type'] == 'year':
                        df_period = df_bar
                    elif slot['type'] == 'quarter':
                        df_period = df_bar[df_bar['date'].dt.quarter == slot['id']]
                    elif slot['type'] == 'month':
                        df_period = df_bar[df_bar['date'].dt.month == slot['id']]
                    elif slot['type'] == 'day':
                        df_period = df_bar[(df_bar['date'].dt.month == slot['id']) & (df_bar['date'].dt.day == 1)]
                    
                    if df_period.empty:
                        bar_fig.add_annotation(
                            text=slot['label'],
                            x=center_x, y=0.90,
                            xref="paper", yref="paper",
                            showarrow=False,
                            font=dict(size=10, color="#8d8d8d")
                        )
                    else:
                        period_data = df_period.groupby('company')['vol_kbpd'].sum().reset_index()
                        period_data = period_data.sort_values('vol_kbpd', ascending=False)
                        total_vol = period_data['vol_kbpd'].sum()
                        # Parse selection
                        sel_comp = company_sel.split('|')[0] if company_sel else None
                        sel_slot = company_sel.split('|')[1] if company_sel else None
                        curr_slot_id = str(i) # Slot index as ID

                        p_colors = []
                        p_line_widths = []
                        p_line_colors = []
                        for comp in period_data['company']:
                            base_color = COMPANY_COLORS.get(comp, DEFAULT_COLOR)
                            if sel_comp:
                                if curr_slot_id == sel_slot:
                                    # Inside the clicked month: highlight the company
                                    if comp == sel_comp:
                                        p_colors.append(base_color)
                                        p_line_widths.append(2)
                                        p_line_colors.append('black')
                                    else:
                                        p_colors.append(hex_to_rgba(base_color, 0.2))
                                        p_line_widths.append(0)
                                        p_line_colors.append('rgba(0,0,0,0)')
                                else:
                                    # Other months: dim everything
                                    p_colors.append(hex_to_rgba(base_color, 0.15))
                                    p_line_widths.append(0)
                                    p_line_colors.append('rgba(0,0,0,0)')
                            else:
                                # Default state
                                p_colors.append(base_color)
                                p_line_widths.append(0.5)
                                p_line_colors.append('white')

                        bar_fig.add_trace(go.Pie(
                            labels=period_data['company'],
                            values=period_data['vol_kbpd'],
                            marker=dict(colors=p_colors, line=dict(color=p_line_colors, width=p_line_widths)),
                            textinfo='none',
                            hole=0,
                            showlegend=False,
                            customdata=[[str(c), float(v), str(curr_slot_id)] for c, v in period_data[['company', 'vol_kbpd']].values],  # Simple customdata for callbacks
                            domain={'x': [i*col_width, (i+1)*col_width], 'y': [0.645, 0.765]}
                        ))
                        
                        # Month label style
                        month_label_color = "black" if (sel_slot and curr_slot_id == sel_slot) else "#8d8d8d"
                        
                        # Main Label (Month/Quarter name)
                        bar_fig.add_annotation(
                            text=f"<b>{slot['label']}</b>" if (sel_slot and curr_slot_id == sel_slot) else slot['label'],
                            x=center_x, y=0.91,
                            xref="paper", yref="paper",
                            showarrow=False,
                            font=dict(size=12, color=month_label_color)
                        )

                        if slot['type'] == 'day':
                            bar_fig.add_annotation(
                                text=slot.get('sub_label', '1'),
                                x=center_x, y=0.88,
                                xref="paper", yref="paper",
                                showarrow=False,
                                font=dict(size=11, color="#8d8d8d")
                            )
                        
                        # Helper for labeling style
                        def get_label_color(comp_name, slot_id):
                            if sel_comp:
                                # ONLY black for the clicked company in the clicked month
                                if slot_id == sel_slot and comp_name == sel_comp:
                                    return "black"
                                return "#c0c0c0" # Dimmed gray for everything else
                            return "black"

                        # Top 1 labels (Above Pie)
                        top1_name = period_data.iloc[0]['company']
                        top1_vol = period_data.iloc[0]['vol_kbpd']
                        top1_pct = (top1_vol / total_vol * 100) if total_vol > 0 else 0
                        label_font_size = 9 if num_slots > 10 else 11
                        top1_color = get_label_color(top1_name, curr_slot_id)
                        
                        bar_fig.add_annotation(
                            text=f"<b>{DISPLAY_NAMES.get(top1_name, top1_name)}</b><br>{top1_vol:,.1f} ('000 b/d)<br>{top1_pct:.2f}%",
                            x=center_x, y=0.86,
                            xref="paper", yref="paper",
                            showarrow=False,
                            font=dict(size=label_font_size, color=top1_color),
                            align="center"
                        )
                        
                        # Top 2 labels (Below Pie)
                        if len(period_data) > 1:
                            top2_name = period_data.iloc[1]['company']
                            top2_vol = period_data.iloc[1]['vol_kbpd']
                            top2_pct = (top2_vol / total_vol * 100) if total_vol > 0 else 0
                            top2_color = get_label_color(top2_name, curr_slot_id)
                            bar_fig.add_annotation(
                                text=f"<b>{DISPLAY_NAMES.get(top2_name, top2_name)}</b><br>{top2_vol:,.1f} ('000 b/d)<br>{top2_pct:.2f}%",
                                x=center_x, y=0.54,
                                xref="paper", yref="paper",
                                showarrow=False,
                                font=dict(size=label_font_size, color=top2_color),
                                align="center"
                            )

                    # --- Loop logic for per-slot content complete ---

                # Top-level Year label (Title)
                bar_fig.add_annotation(
                    text=f"<b>{selected_year}</b>",
                    x=0.5, y=0.965,
                    xref="paper", yref="paper",
                    showarrow=False,
                    font=dict(size=14, color="#333")
                )
                

                bar_fig.update_layout(
                    height=420,
                    margin=dict(t=5, b=5, l=5, r=5),
                    paper_bgcolor='white',
                    plot_bgcolor='white',
                    xaxis=dict(visible=False, range=[0, 1], fixedrange=True),
                    yaxis=dict(visible=False, range=[0, 1], fixedrange=True),
                    showlegend=False,
                    hoverlabel=dict(bgcolor="white", font=dict(color="black", size=12, family="Arial")),
                    clickmode='event+select'
                )
                
                bar_title = f"{display_product.upper()} PRODUCTION BY COMPANY ('000 b/d)"

            return tree_fig, treemap_title, bar_fig, bar_title

        except Exception as e:
            logger.error(f"Error updating product charts: {str(e)}")
            empty_fig = go.Figure()
            empty_fig.add_annotation(text="Error loading data", showarrow=False)
            return empty_fig, "Error", empty_fig, "Error"

    @callback(
        Output("download-company-treemap", "data"),
        Input("btn-export-company-treemap", "n_clicks"),
        [State('company-year-selector', 'value'),
         State('company-product-selector', 'value')],
        prevent_initial_call=True
    )
    def export_company_treemap(n_clicks, selected_year, selected_product):
        if not n_clicks: return dash.no_update
        try:
            query = f"""
            SELECT company, date, vol_kbpd 
            FROM russia_master_data 
            WHERE category = 'Refining And Products Output' 
            AND commodity = '{selected_product}'
            """
            results = execute_query(query)
            df = pd.DataFrame(results)
            if df.empty: return dash.no_update
            
            df['date'] = pd.to_datetime(df['date'])
            df['vol_kbpd'] = pd.to_numeric(df['vol_kbpd'], errors='coerce').fillna(0)
            
            if selected_year == 'All':
                latest_date = df['date'].max()
                export_df = df[df['date'] == latest_date]
                filename = f"company_market_share_{selected_product.replace(' ', '_')}_latest.csv"
            else:
                target_year = int(selected_year)
                export_df = df[(df['date'].dt.year == target_year) & (df['date'].dt.month == 1)]
                filename = f"company_market_share_{selected_product.replace(' ', '_')}_{selected_year}.csv"
                
            export_df = export_df.groupby('company')['vol_kbpd'].sum().reset_index()
            export_df = export_df.sort_values('vol_kbpd', ascending=False)
            return dcc.send_data_frame(export_df.to_csv, filename, index=False)
        except Exception as e:
            logger.error(f"Error exporting company treemap: {str(e)}")
            return dash.no_update

    @callback(
        Output("download-company-bar", "data"),
        Input("btn-export-company-bar", "n_clicks"),
        [State('company-year-selector', 'value'),
         State('company-product-selector', 'value'),
         State('company-treemap-selection', 'data')],
        prevent_initial_call=True
    )
    def export_company_bar(n_clicks, selected_year, selected_product, treemap_sel):
        if not n_clicks: return dash.no_update
        try:
            query = f"""
            SELECT company, date, vol_kbpd 
            FROM russia_master_data 
            WHERE category = 'Refining And Products Output' 
            AND commodity = '{selected_product}'
            """
            results = execute_query(query)
            df = pd.DataFrame(results)
            if df.empty: return dash.no_update
            
            df['date'] = pd.to_datetime(df['date'])
            df['vol_kbpd'] = pd.to_numeric(df['vol_kbpd'], errors='coerce').fillna(0)
            
            if treemap_sel:
                df = df[df['company'] == treemap_sel]
                
            export_df = df.groupby(['date', 'company'])['vol_kbpd'].sum().reset_index()
            export_df = export_df.sort_values(['date', 'company'])
            
            filename = f"production_timeseries_{selected_product.replace(' ', '_')}.csv"
            return dcc.send_data_frame(export_df.to_csv, filename, index=False)
        except Exception as e:
            logger.error(f"Error exporting company bar: {str(e)}")
            return dash.no_update

    @callback(
        Output("download-product-treemap", "data"),
        Input("btn-export-product-treemap", "n_clicks"),
        State('product-year-selector', 'value'),
        prevent_initial_call=True
    )
    def export_product_treemap(n_clicks, selected_year):
        if not n_clicks: return dash.no_update
        try:
            query = f"""
            SELECT commodity, date, vol_kbpd 
            FROM russia_master_data 
            WHERE category = 'Refinery Output' 
            AND EXTRACT(YEAR FROM date) = {selected_year}
            """
            results = execute_query(query)
            df = pd.DataFrame(results)
            if df.empty: return dash.no_update
            
            df['vol_kbpd'] = pd.to_numeric(df['vol_kbpd'], errors='coerce').fillna(0)
            df['date'] = pd.to_datetime(df['date'])
            
            # Annual Average of Monthly Sums:
            monthly_sums = df.groupby(['commodity', 'date'])['vol_kbpd'].sum().reset_index()
            export_df = monthly_sums.groupby('commodity')['vol_kbpd'].mean().reset_index()
            export_df = export_df.sort_values('vol_kbpd', ascending=False)
            
            filename = f"oil_products_production_mix_{selected_year}.csv"
            return dcc.send_data_frame(export_df.to_csv, filename, index=False)
        except Exception as e:
            logger.error(f"Error exporting product treemap: {str(e)}")
            return dash.no_update

    @callback(
        Output("download-product-bar", "data"),
        Input("btn-export-product-bar", "n_clicks"),
        [State('product-year-selector', 'value'),
         State('product-treemap-selection', 'data')],
        prevent_initial_call=True
    )
    def export_product_bar(n_clicks, selected_year, product_sel):
        if not n_clicks: return dash.no_update
        try:
            target_product = product_sel if product_sel else 'Gasoline' 
            breakdown_product = REFINERY_TO_BREAKDOWN_MAP.get(target_product, target_product)
            
            query = f"""
            SELECT company, date, vol_kbpd 
            FROM russia_master_data 
            WHERE category = 'Refining And Products Output' 
            AND commodity = '{breakdown_product}'
            AND EXTRACT(YEAR FROM date) = {selected_year}
            """
            results = execute_query(query)
            df = pd.DataFrame(results)
            if df.empty: return dash.no_update
            
            df['date'] = pd.to_datetime(df['date'])
            df['vol_kbpd'] = pd.to_numeric(df['vol_kbpd'], errors='coerce').fillna(0)
            
            export_df = df.groupby(['date', 'company'])['vol_kbpd'].sum().reset_index()
            export_df = export_df.sort_values(['date', 'company'])
            
            filename = f"{breakdown_product.replace(' ', '_')}_by_company_{selected_year}.csv"
            return dcc.send_data_frame(export_df.to_csv, filename, index=False)
        except Exception as e:
            logger.error(f"Error exporting product bar: {str(e)}")
            return dash.no_update
