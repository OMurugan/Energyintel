from dash import html, dcc, Input, Output, State, callback, clientside_callback
import pandas as pd
import plotly.graph_objects as go
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
    'Surgutneftegas': 'Surgut'
}

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

def create_layout():
    """Create the Product Output layout with Tabs"""
    return html.Div([
        # Selection Stores
        dcc.Store(id='company-treemap-selection', data=None),
        dcc.Store(id='company-bar-selection', data=None),

        # Main Tab Container
        dcc.Tabs(id='product-output-tabs', value='by-company', children=[
            dcc.Tab(label='By Company', value='by-company', className='custom-tab', selected_className='custom-tab--selected'),
            dcc.Tab(label='By Product', value='by-product', className='custom-tab', selected_className='custom-tab--selected'),
        ], className='custom-tabs-container'),

        # Tab Content
        html.Div(id='product-output-content', style={'padding': '20px'})
    ], style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh', 'fontFamily': 'Arial, sans-serif'})

# Clientside callbacks for fast interactivity
clientside_callback(
    """
    function(clickData, currentSelection) {
        if (!clickData || !clickData.points || clickData.points.length === 0) {
            return [currentSelection, window.dash_clientside.no_update];
        }
        const point = clickData.points[0];
        if (!point.customdata) return [null, null];
        const clickedCompany = String(point.customdata[0]).trim();
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
        if (!point.customdata) return [null, null];
        const company = String(point.customdata[0]).trim();
        const date = String(point.customdata[1]).trim();
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

def create_by_company_layout():
    """Layout for the 'By Company' tab"""
    return html.Div([
        html.Div([
            # Left side: Charts
            html.Div([
                # Treemap Header
                html.H3(id='treemap-company-header', 
                        style={'margin': '0 0 10px 0', 'fontWeight': 'bold', 'color': '#FF4500', 'fontSize': '22px'}),
                
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
                html.H3(id='bar-company-header', 
                        style={'margin': '20px 0 10px 0', 'fontWeight': 'bold', 'color': '#FF4500', 'fontSize': '22px'}),
                
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

            ], style={'width': '85%', 'display': 'inline-block', 'verticalAlign': 'top'}),

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
            ], style={'width': '13%', 'display': 'inline-block', 'marginLeft': '2%', 'verticalAlign': 'top'})
        ], style={'display': 'flex', 'justifyContent': 'space-between'})
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
            return html.Div([
                html.H3("By Product Analysis", style={'color': '#1b365d'}),
                html.P("This section is under development.", style={'fontStyle': 'italic'})
            ], style={'padding': '20px', 'textAlign': 'center'})
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
        FROM dev.russia_master_data 
        WHERE category = 'Refining And Products Output' 
        AND commodity = '{selected_product}'
        AND date >= '2022-01-01'
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
                # For 'All Years', use the latest available month snapshot
                latest_date = df['date'].max()
                df_tree_snapshot = df[df['date'] == latest_date]
                year_label = "ALL YEARS"
            else:
                # For a specific year, use January (Month 1) as requested by the user
                target_year = int(selected_year)
                df_tree_snapshot = df[
                    (df['date'].dt.year == target_year) & 
                    (df['date'].dt.month == 1)
                ]
                year_label = str(selected_year)
            
            if df_tree_snapshot.empty:
                tree_fig = go.Figure()
                tree_fig.add_annotation(text=f"No data for {year_label}", showarrow=False)
            else:
                treemap_data = df_tree_snapshot.groupby('company')['vol_kbpd'].sum().reset_index()
                
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
                        marker_colors.append(hex_to_rgba(base_color, 0.2))
                        line_widths.append(0)
                        line_colors.append('rgba(0,0,0,0)')
                    elif treemap_sel and company == treemap_sel:
                        marker_colors.append(base_color)
                        line_widths.append(2)
                        line_colors.append('black')
                    else:
                        marker_colors.append(base_color)
                        line_widths.append(0)
                        line_colors.append('rgba(0,0,0,0)')
                    # Determine precision based on product
                    precision = ".1f" if selected_product == 'VGO' else ".0f"
                    
                    labels.append(f"<b>{display_name}</b><br>{row['vol_kbpd']:{precision}} ('000 b/d)<br>{row['percentage']:.2f}%")
                    # CRITICAL: Keep original 'company' in customdata[0] for interactivity
                    custom_data.append([company, row['vol_kbpd'], row['percentage']])

                tree_fig = go.Figure(go.Treemap(
                    ids=ids,
                    labels=labels,
                    parents=[""] * len(labels),
                    values=treemap_data['vol_kbpd'],
                    textinfo="label",
                    marker=dict(colors=marker_colors, line=dict(width=line_widths, color=line_colors)),
                    customdata=custom_data,
                    hovertemplate=f"Company: %{{customdata[0]}}<br>Volume: %{{customdata[1]:{precision}}}<extra></extra>",
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
                    customdata=comp_df[['company', 'hover_date']].values.tolist(),
                    hovertemplate="Company: %{customdata[0]}<br>Date: %{customdata[1]}<br>Volume: %{y:,.0f} ('000 b/d)<extra></extra>",
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
