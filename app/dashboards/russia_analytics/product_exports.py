from dash import html, dcc, Input, Output, State, callback
import pandas as pd
import plotly.graph_objects as go
from core.data_helpers import execute_query
import dash
import logging

# Set up logging to see output in terminal
logger = logging.getLogger(__name__)

# Exact color mapping and commodity set from user images
COMMODITY_COLORS = {
    'Diesel And Gasoil': '#A6644C',
    'Fuel Oil and VGO': '#2F3E4D',
    'Naphtha': '#1A3458',
    'Gasoline': '#5489B1',
    'Jet Fuel': '#C1392B',
    'Petcoke': '#8A4F3B',
    'Bitumen-Residues': '#00758B'
}

# Mapping for legend labels to match visual truncation
LEGEND_LABELS = {
    'Bitumen-Residues': 'Bitumen-Residu...'
}

# The order for stacking in the bar chart (Bottom to Top)
BAR_STACK_ORDER = [
    'Petcoke',
    'Naphtha',
    'Jet Fuel',
    'Gasoline',
    'Fuel Oil and VGO',
    'Diesel And Gasoil',
    'Bitumen-Residues'
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

def create_layout(years=None, default_year=None):
    """Create the Product Exports layout"""
    if years is None:
        years = [2025, 2024, 2023, 2022]
    if default_year is None:
        default_year = years[0] if years else 2025
    
    # Create year options
    year_options = [{'label': f' {year}', 'value': year} for year in years]
    
    return html.Div([
        # Selection Stores (Independent for each chart)
        dcc.Store(id='treemap-selection', data=None),
        dcc.Store(id='bar-selection', data=None),
        dcc.Store(id='exports-expansion-store', data={'Year': False, 'Quarter': False, 'Month': True, 'Day': False}),

        # Download components
        dcc.Download(id='download-treemap-csv'),
        dcc.Download(id='download-bar-csv'),

        # Main Header
        html.Div([
            html.H3(id='treemap-header', children="EXPORT OF OIL PRODUCTS ('000 b/d)", 
                    style={'margin': '0', 'fontWeight': 'bold', 'color': '#FF4500', 'fontSize': '24px'}),
            html.Button(
                'Export to CSV',
                id='btn-export-treemap',
                n_clicks=0,
                style={
                    'backgroundColor': 'white', 'color': '#2c3e50', 'border': '1px solid #dee2e6',
                    'padding': '5px 15px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '13px'
                }
            )
        ], style={'padding': '10px 20px', 'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}),

        html.Div([
            # Left side: Charts
            html.Div([
                # Treemap
                dcc.Loading(
                    id="loading-treemap",
                    type="default",
                    color='#FF4500',
                    children=dcc.Graph(
                        id='product-exports-treemap',
                        config={'displayModeBar': False},
                        style={'height': '330px', 'marginBottom': '30px'}
                    )
                ),

                # Subheader for Stacked Bar
                html.Div([
                    html.H3(id='bar-header', children="PRODUCT EXPORTS ('000 b/d)", 
                            style={'margin': '0', 'fontWeight': 'bold', 'color': '#FF4500', 'fontSize': '22px'}),
                    html.Button(
                        'Export to CSV',
                        id='btn-export-bar',
                        n_clicks=0,
                        style={
                            'backgroundColor': 'white', 'color': '#2c3e50', 'border': '1px solid #dee2e6',
                            'padding': '5px 15px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '13px'
                        }
                    )
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
                
                # Hierarchy Level Controls
                html.Div([
                    html.Div([
                        html.Span("Year of Date", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px', 'fontWeight': 'bold'}),
                        html.Button('+', id='btn-exports-expand-year', n_clicks=0, style={
                            'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                            'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                            'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                        })
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                    
                    html.Div([
                        html.Span("Quarter of Date", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px', 'fontWeight': 'bold'}),
                        html.Button('+', id='btn-exports-expand-quarter', n_clicks=0, style={
                            'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                            'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                            'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                        })
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                    
                    html.Div([
                        html.Span("Month of Date", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px', 'fontWeight': 'bold'}),
                        html.Button('-', id='btn-exports-expand-month', n_clicks=0, style={
                            'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                            'backgroundColor': 'white', 'color': '#add8e6', 'borderRadius': '3px', 'cursor': 'pointer',
                            'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                        })
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                    
                    html.Div([
                        html.Span("Day of Date", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px', 'fontWeight': 'bold'}),
                        html.Button('+', id='btn-exports-expand-day', n_clicks=0, style={
                            'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                            'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                            'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                        })
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], style={
                    'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#f8f9fa', 
                    'padding': '5px 10px', 'borderRadius': '4px', 'marginBottom': '10px'
                }),
                
                # Stacked Bar Chart
                dcc.Loading(
                    id="loading-bar",
                    type="default",
                    color='#FF4500',
                    children=dcc.Graph(
                        id='product-exports-bar',
                        config={'displayModeBar': False},
                        style={'height': '330px'}
                    )
                ),
                
                # Footer Source
                html.Div([
                    html.A("Energy Intelligence; data as of December 2025", 
                           id='footer-source-text',
                           className='source-link footer-source-link',
                           style={
                               'width': '100%', 'display': 'block', 'padding': '8px 10px', 
                               'fontStyle': 'italic', 'fontSize': '12px', 'marginTop': '10px',
                               'color': '#1b365d'
                           },
                           tabIndex=0)
                ], className='source-container'),

            ], style={'width': '88%', 'display': 'inline-block', 'verticalAlign': 'top'}),

            # Right side: Controls and Legend
            html.Div([
                # Year Selection
                html.Div([
                    html.Label("SELECT YEAR", style={'fontWeight': 'bold', 'fontSize': '14px', 'color': '#333'}),
                    dcc.RadioItems(
                        id='year-selector',
                        options=year_options,
                        value=default_year,
                        labelStyle={'display': 'block', 'marginBottom': '5px', 'fontSize': '14px'}
                    )
                ], style={'marginBottom': '30px', 'padding': '10px 0', 'border': 'none', 'borderRadius': '0'}),

                # Commodity Legend
                html.Div([
                    html.Label("Commodity", style={'fontWeight': 'bold', 'fontSize': '14px', 'color': '#333', 'marginBottom': '10px', 'display': 'block'}),
                    html.Div([
                        html.Div([
                            html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': COMMODITY_COLORS[commodity], 'display': 'inline-block', 'marginRight': '8px'}),
                            html.Span(LEGEND_LABELS.get(commodity, commodity), style={'fontSize': '12px', 'color': '#555'})
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '4px'})
                        for commodity in reversed(BAR_STACK_ORDER)
                    ])
                ], style={'padding': '10px 0', 'border': 'none', 'borderRadius': '0'})
            ], style={'width': '10%', 'display': 'inline-block', 'marginLeft': '2%', 'verticalAlign': 'top'})
        ], style={'padding': '0 20px'})
    ], style={'backgroundColor': 'white', 'fontFamily': 'Arial, sans-serif'})

# Consolidated Clientside Callbacks to handle selection toggling and reset clickData to null
# This resolves circular dependencies while enabling reset-on-click functionality

from dash import clientside_callback

# 1. Treemap Selection + Reset
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

        const clickedCommodity = String(point.customdata[0] || '').trim();
        if (!clickedCommodity) {
            return [null, null];
        }
        let nextSelection = clickedCommodity;
        
        // Toggle logic
        if (currentSelection && String(currentSelection).trim() === clickedCommodity) {
            nextSelection = null;
        }
        
        // Always return null for clickData to ensure Dash triggers on the next click
        return [nextSelection, null];
    }
    """,
    [Output('treemap-selection', 'data'),
     Output('product-exports-treemap', 'clickData')],
    Input('product-exports-treemap', 'clickData'),
    State('treemap-selection', 'data'),
    prevent_initial_call=True
)

# 2. Bar Selection + Reset
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

        const commodity = String(point.customdata[0] || '').trim();
        const date = String(point.customdata[1] || '').trim();
        if (!commodity || !date) {
            return [null, null];
        }
        const clickedId = commodity + "|" + date;
        
        let nextSelection = clickedId;
        
        // Toggle logic
        if (currentSelection && String(currentSelection).trim() === clickedId) {
            nextSelection = null;
        }
        
        // Always return null for clickData to ensure Dash triggers on the next click
        return [nextSelection, null];
    }
    """,
    [Output('bar-selection', 'data'),
     Output('product-exports-bar', 'clickData')],
    Input('product-exports-bar', 'clickData'),
    State('bar-selection', 'data'),
    prevent_initial_call=True
)
# Module-level callback functions removed - all callbacks now properly registered inside register_callbacks function

def register_callbacks(dash_app, server):
    """Register all callbacks for Product Exports Analytics"""

    @dash_app.callback(
        [Output('exports-expansion-store', 'data'),
         Output('btn-exports-expand-year', 'children'),
         Output('btn-exports-expand-quarter', 'children'),
         Output('btn-exports-expand-month', 'children'),
         Output('btn-exports-expand-day', 'children')],
        [Input('btn-exports-expand-year', 'n_clicks'),
         Input('btn-exports-expand-quarter', 'n_clicks'),
         Input('btn-exports-expand-month', 'n_clicks'),
         Input('btn-exports-expand-day', 'n_clicks')],
        [State('exports-expansion-store', 'data')],
        prevent_initial_call=True
    )
    def update_exports_expansion_state(y_c, q_c, m_c, d_c, current_visibility):
        from dash import callback_context
        ctx = callback_context
        if not ctx.triggered:
            return current_visibility, '+', '+', '-', '+'
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        new_visibility = current_visibility.copy() if current_visibility else {'Year': False, 'Quarter': False, 'Month': False, 'Day': False}
        
        if button_id == 'btn-exports-expand-year':
            new_visibility['Year'] = not new_visibility.get('Year', False)
            if not new_visibility['Year']:
                new_visibility['Quarter'] = False
                new_visibility['Month'] = False
                new_visibility['Day'] = False
        elif button_id == 'btn-exports-expand-quarter':
            new_visibility['Quarter'] = not new_visibility.get('Quarter', False)
            if new_visibility['Quarter']:
                new_visibility['Year'] = True
            else:
                new_visibility['Month'] = False
                new_visibility['Day'] = False
        elif button_id == 'btn-exports-expand-month':
            new_visibility['Month'] = not new_visibility.get('Month', False)
            if new_visibility['Month']:
                new_visibility['Year'] = True
                new_visibility['Quarter'] = True
            else:
                new_visibility['Day'] = False
        elif button_id == 'btn-exports-expand-day':
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

    @dash_app.callback(
        Output('download-treemap-csv', 'data'),
        Input('btn-export-treemap', 'n_clicks'),
        [State('year-selector', 'value'),
         State('treemap-selection', 'data')],
        prevent_initial_call=True
    )
    def export_treemap_data(n_clicks, selected_year, sel_commodity):
        if not n_clicks:
            return dash.no_update
        
        query = f"SELECT date, category, commodity, vol_kbpd FROM russia_master_data WHERE category = 'Exports' AND EXTRACT(YEAR FROM date) = {selected_year}"
        if sel_commodity:
            query += f" AND commodity = '{sel_commodity}'"
        
        try:
            results = execute_query(query)
            if not results:
                return dash.no_update
            df = pd.DataFrame(results)
            filename = f"treemap_data_{selected_year}_{sel_commodity or 'all'}.csv"
            return dcc.send_data_frame(df.to_csv, filename, index=False)
        except Exception as e:
            logger.error(f"Treemap Export Error: {str(e)}")
            return dash.no_update

    @dash_app.callback(
        Output('download-bar-csv', 'data'),
        Input('btn-export-bar', 'n_clicks'),
        [State('bar-selection', 'data')],
        prevent_initial_call=True
    )
    def export_bar_data(n_clicks, sel_commodity):
        if n_clicks > 0:
            query = f"SELECT date, category, commodity, vol_kbpd FROM russia_master_data WHERE category = 'Exports' AND date >= '2022-01-01';"
            results = execute_query(query) or []
            df = pd.DataFrame(results)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                if sel_commodity:
                    # Extract commodity name if it's a point-specific selection
                    sel_category = sel_commodity.split('|')[0] if '|' in sel_commodity else sel_commodity
                    df = df[df['commodity'].str.strip() == sel_category]
                
                filename = f"product_exports_{sel_commodity.replace('|','_') if sel_commodity else 'all'}.csv"
                return dcc.send_data_frame(df.to_csv, filename=filename, index=False)
        return None

    @dash_app.callback(
        [Output('product-exports-treemap', 'figure'),
         Output('treemap-header', 'children')],
        [Input('year-selector', 'value'),
         Input('treemap-selection', 'data')]
    )
    def update_treemap(selected_year, sel_treemap):
        logger.info(f"Treemap callback triggered: year={selected_year}, selection={sel_treemap}")
        query_treemap = f"SELECT date, category, commodity, vol_kbpd FROM russia_master_data WHERE category = 'Exports' AND EXTRACT(YEAR FROM date) = {selected_year};"
        
        try:
            results_t = execute_query(query_treemap) or []
            df_t = pd.DataFrame(results_t)
            logger.info(f"Treemap query returned {len(df_t)} rows")

        except Exception as e:
            logger.error(f"Treemap query failed: {str(e)}")
            df_t = pd.DataFrame()

        # Data Coercion
        if not df_t.empty:
            df_t['date'] = pd.to_datetime(df_t['date'])
            df_t['vol_kbpd'] = pd.to_numeric(df_t['vol_kbpd'], errors='coerce').fillna(0)
            df_t['commodity'] = df_t['commodity'].astype(str).str.strip()
            df_t['category'] = df_t['category'].astype(str).str.strip()

        # Filtering
        valid_commodities = list(COMMODITY_COLORS.keys())
        df_t = df_t[df_t['commodity'].isin(valid_commodities)] if not df_t.empty else df_t

        # Header
        treemap_header = f"EXPORT OF OIL PRODUCTS IN {selected_year} ('000 b/d) -- All"

        if df_t.empty:
            fig_treemap = go.Figure()
            fig_treemap.add_annotation(text=f"No data for {selected_year}", showarrow=False, font=dict(size=14, color="grey"))
            treemap_header += " -- No Data"
        else:
            df_t['month'] = df_t['date'].dt.to_period('M')
            monthly_t = df_t.groupby(['commodity', 'month'])['vol_kbpd'].sum().reset_index()
            treemap_df = monthly_t.groupby('commodity')['vol_kbpd'].mean().reset_index()
            total_val = treemap_df['vol_kbpd'].sum()
            treemap_df['percentage'] = (treemap_df['vol_kbpd'] / total_val * 100) if total_val > 0 else 0
            treemap_df = treemap_df.sort_values('vol_kbpd', ascending=False)

            labels, values, colors, custom_data, ids = [], [], [], [], []
            line_widths, line_colors = [], []
            for _, row in treemap_df.iterrows():
                commodity = row['commodity']
                ids.append(commodity)
                labels.append(f"<b>{commodity}</b><br>{row['vol_kbpd']:.1f} ('000 b/d)<br>{row['percentage']:.2f}%")
                values.append(row['vol_kbpd'])
                
                base_color = COMMODITY_COLORS.get(commodity, '#CCCCCC')
                if sel_treemap and commodity != sel_treemap:
                    colors.append(hex_to_rgba(base_color, 0.15))
                    line_widths.append(0)
                    line_colors.append('rgba(0,0,0,0)')
                elif sel_treemap and commodity == sel_treemap:
                    colors.append(base_color)
                    line_widths.append(4)
                    line_colors.append('black')
                else:
                    colors.append(base_color)
                    line_widths.append(0)
                    line_colors.append('rgba(0,0,0,0)')
                    
                # Add safety checks to ensure no None/NaN values
                commodity_str = str(commodity) if commodity is not None else 'Unknown'
                vol_float = float(row['vol_kbpd']) if pd.notna(row['vol_kbpd']) else 0.0
                pct_float = float(row['percentage']) if pd.notna(row['percentage']) else 0.0
                custom_data.append([commodity_str, vol_float, pct_float])

            # Ensure customdata is never empty - add a fallback
            if not custom_data:
                custom_data = [['No Data', 0.0, 0.0]]
                ids = ['no-data']
                labels = ['No Data Available']
                colors = ['#CCCCCC']
                values = [0]

            fig_treemap = go.Figure(go.Treemap(
                ids=ids,
                labels=labels,
                parents=[""] * len(labels),
                values=values,
                textinfo="label",
                marker=dict(colors=colors, line=dict(width=line_widths, color=line_colors)),
                customdata=custom_data,  # Keep for clientside callbacks
                tiling=dict(pad=2),
                maxdepth=1,
                hovertemplate="Product: <b>%{customdata[0]}</b><br>Volume ('000 b/d): <b>%{customdata[1]:,.1f}</b><br>% of Total: %{customdata[2]:.2f}%<extra></etra></extra>",
                hoverlabel=dict(bgcolor="white", font=dict(color="black", size=12, family="Arial"))
            ))
            fig_treemap.update_layout(
                margin=dict(t=0, b=0, l=0, r=0), 
                uirevision=f"{selected_year}-{sel_treemap}",
                clickmode='event'
            )

        fig_treemap.update_layout(
            paper_bgcolor='white', plot_bgcolor='white',
            font=dict(family="Arial, sans-serif"),
            hoverlabel=dict(bgcolor="white", font=dict(color="black", size=12, family="Arial"), bordercolor="#dddddd")
        )
        return fig_treemap, treemap_header

    @dash_app.callback(
        [Output('product-exports-bar', 'figure'),
         Output('bar-header', 'children')],
        [Input('bar-selection', 'data'),
         Input('exports-expansion-store', 'data')]
    )
    def update_bar_chart(sel_bar, expansion_state):
        logger.info(f"Bar chart callback triggered: selection={sel_bar}")
        query_bar = "SELECT date, category, commodity, vol_kbpd FROM russia_master_data WHERE category = 'Exports' AND date >= '2022-01-01';"
        
        try:
            results_b = execute_query(query_bar) or []
            df_b = pd.DataFrame(results_b)
            logger.info(f"Bar chart query returned {len(df_b)} rows")

        except Exception as e:
            logger.error(f"Bar chart query failed: {str(e)}")
            df_b = pd.DataFrame()

        # Data Coercion
        if not df_b.empty:
            df_b['date'] = pd.to_datetime(df_b['date'])
            df_b['vol_kbpd'] = pd.to_numeric(df_b['vol_kbpd'], errors='coerce').fillna(0)
            df_b['commodity'] = df_b['commodity'].astype(str).str.strip()
            df_b['category'] = df_b['category'].astype(str).str.strip()

        # Filtering
        valid_commodities = list(COMMODITY_COLORS.keys())
        df_b = df_b[df_b['commodity'].isin(valid_commodities)] if not df_b.empty else df_b

        # Header
        bar_header = f"PRODUCT EXPORTS ('000 b/d) -- All"

        if df_b.empty:
            fig_bar = go.Figure()
            fig_bar.add_annotation(text="No historical trend data", showarrow=False, font=dict(size=14, color="grey"))
            bar_header += " -- No Data"
        else:
            df_b = df_b.sort_values('date')
            
            # Determine granularity level
            if not expansion_state:
                expansion_state = {'Year': False, 'Quarter': False, 'Month': True, 'Day': False}
            
            gran_level = 'MONTH'  # Default
            if expansion_state.get('Day'):
                gran_level = 'DAY'
            elif expansion_state.get('Month'):
                gran_level = 'MONTH'
            elif expansion_state.get('Quarter'):
                gran_level = 'QUARTER'
            elif expansion_state.get('Year'):
                gran_level = 'YEAR'
            
            # Group by appropriate time period
            if gran_level == 'YEAR':
                df_b['time_sort'] = df_b['date'].dt.year
                # Format year as 2 digits with line break between digits (e.g., '2<br>5' for 2025)
                df_b['time_display'] = df_b['date'].dt.year.astype(str).str[-2:].apply(lambda x: f"{x[0]}<br>{x[1]}")
                df_b['hover_date'] = df_b['date'].dt.year.astype(str)
            elif gran_level == 'QUARTER':
                df_b['time_sort'] = df_b['date'].dt.to_period('Q')
                df_b['time_display'] = df_b['date'].dt.to_period('Q').astype(str).str.replace(r'(\d{4})', lambda m: m.group(1)[-2:], regex=True)  # Convert 2025Q1 to 25Q1
                df_b['hover_date'] = df_b['date'].dt.to_period('Q').astype(str)
            elif gran_level == 'DAY':
                df_b['time_sort'] = df_b['date']
                df_b['time_display'] = df_b['date'].dt.strftime('%d<br>%b<br>%y')  # 2-digit year
                df_b['hover_date'] = df_b['date'].dt.strftime('%d %b %Y')
            else:  # MONTH
                df_b['time_sort'] = df_b['date'].dt.to_period('M')
                df_b['time_display'] = df_b['date'].dt.strftime('%b<br>%y')  # 2-digit year
                df_b['hover_date'] = df_b['date'].dt.strftime('%b %Y')
            
            bar_df = df_b.groupby(['time_sort', 'time_display', 'hover_date', 'commodity'])['vol_kbpd'].sum().reset_index()
            bar_df = bar_df.sort_values('time_sort')

            fig_bar = go.Figure()
            time_displays = bar_df['time_display'].unique() if not bar_df.empty else []

            for commodity in BAR_STACK_ORDER:
                comm_data = bar_df[bar_df['commodity'] == commodity]
                if comm_data.empty:
                    continue
                    
                comm_data = comm_data.set_index('time_display').reindex(time_displays).fillna({'vol_kbpd': 0}).reset_index()
                hdate_map = bar_df[['time_display', 'hover_date']].drop_duplicates().set_index('time_display')
                reindexed_hdates = hdate_map.reindex(time_displays)['hover_date'].tolist()
                
                base_color = COMMODITY_COLORS.get(commodity, '#CCCCCC')
                marker_colors = []
                marker_line_widths = []
                marker_line_colors = []
                
                for _, bar_row in comm_data.iterrows():
                    point_id = f"{commodity}|{bar_row['hover_date']}"
                    if sel_bar and point_id == sel_bar:
                        marker_colors.append(base_color)
                        marker_line_widths.append(3)
                        marker_line_colors.append('black')
                    elif sel_bar:
                        marker_colors.append(hex_to_rgba(base_color, 0.15))
                        marker_line_widths.append(0)
                        marker_line_colors.append('rgba(0,0,0,0)')
                    else:
                        marker_colors.append(base_color)
                        marker_line_widths.append(0)
                        marker_line_colors.append('rgba(0,0,0,0)')

                fig_bar.add_trace(go.Bar(
                    name=commodity, x=comm_data['time_display'], y=comm_data['vol_kbpd'],
                    marker=dict(
                        color=marker_colors,
                        line=dict(width=marker_line_widths, color=marker_line_colors)
                    ),
                    customdata=[[str(commodity), str(d)] for d in reindexed_hdates],  # Simple customdata for callbacks
                    hovertemplate="Commodity: %{fullData.name}<br>Volume ('000 b/d): %{y:,.0f}<extra></extra>",
                    hoverlabel=dict(bgcolor="white", font=dict(color="black", size=12, family="Arial"))
                ))

            fig_bar.update_layout(
                barmode='stack',
                xaxis=dict(title="", type='category', tickangle=0, tickfont=dict(size=9, color='#1b365d')),
                yaxis=dict(
                    title="'000 b/d", 
                    gridcolor='#eee', 
                    tickfont=dict(size=12, color='#1b365d'), 
                    zerolinecolor='#eee', 
                    range=[0, 3100],
                    tickmode='array',
                    tickvals=[0, 1000, 2000, 3000],
                    tickformat=",d"
                ),
                margin=dict(t=10, b=50, l=50, r=10),
                paper_bgcolor='white', plot_bgcolor='white',
                showlegend=False, uirevision=f"static-{sel_bar}", 
                hoverlabel=dict(bgcolor="white", font=dict(color="black", size=12, family="Arial"), bordercolor="#dddddd")
            )

        return fig_bar, bar_header