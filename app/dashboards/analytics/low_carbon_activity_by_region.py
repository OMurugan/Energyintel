"""
Activity by Region
Low-carbon investment activity analytics by region
"""
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, State, callback_context, no_update
from core.data_helpers import execute_query

# Color scheme matching the reference image
EI_ORANGE = "#fe5000"
EI_DARK_BLUE = "#1b365d"

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


def create_layout():
    """Create the Activity by Region layout"""
    return html.Div([
        # Data stores
        dcc.Store(id='low-carbon-measure-store', data='investment_value'),
        dcc.Store(id='low-carbon-breakdown-store', data='status'),
        dcc.Store(id='low-carbon-chart-selection', data=None),
        dcc.Store(id='low-carbon-is-expanded', data=False),
        dcc.Download(id='low-carbon-download-csv'),
        
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
                # Measure Filter
                html.Div([
                    html.Label(
                        "Measure",
                        style={
                            'fontWeight': 'bold',
                            'color': '#777',
                            'fontSize': '12px',
                            'marginBottom': '10px',
                            'display': 'block'
                        }
                    ),
                    dcc.RadioItems(
                        id='low-carbon-measure-filter',
                        options=[
                            {'label': ' Investment Value', 'value': 'investment_value'},
                            {'label': ' Investment Count', 'value': 'investment_count'}
                        ],
                        value='investment_value',
                        labelStyle={
                            'display': 'block',
                            'fontSize': '12px',
                            'color': '#555',
                            'marginBottom': '5px'
                        }
                    )
                ], style={'marginBottom': '30px'}),
                
                # Breakdown Filter
                html.Div([
                    html.Label(
                        "Breakdown",
                        style={
                            'fontWeight': 'bold',
                            'color': '#777',
                            'fontSize': '12px',
                            'marginBottom': '10px',
                            'display': 'block'
                        }
                    ),
                    dcc.RadioItems(
                        id='low-carbon-breakdown-filter',
                        options=[
                            {'label': ' Status', 'value': 'status'},
                            {'label': ' Project Category', 'value': 'project_category'},
                            {'label': ' Peer Group', 'value': 'peer_group'},
                            {'label': ' Investment Type', 'value': 'investment_type'}
                        ],
                        value='status',
                        labelStyle={
                            'display': 'block',
                            'fontSize': '12px',
                            'color': '#555',
                            'marginBottom': '5px'
                        }
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
        ], style={'display': 'flex'})
    ], className='tab-content', style={
        'backgroundColor': '#ffffff',
        'minHeight': '100vh',
        'fontFamily': 'Arial, sans-serif'
    })


def register_callbacks(dash_app, server):
    """Register all callbacks for the dashboard"""
    
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
         Input('low-carbon-chart-container', 'n_clicks')],
        State('low-carbon-chart-selection', 'data'),
        prevent_initial_call=True
    )
    def toggle_chart_selection(click_data, measure, breakdown, n_clicks_bg, current_sel):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update
        
        trigger_id = ctx.triggered[0]['prop_id']
        
        # Filter changes -> Reset
        if 'measure-filter' in trigger_id or 'breakdown-filter' in trigger_id:
            return None, None
        
        # Chart click
        if 'low-carbon-chart.clickData' in trigger_id and click_data:
            point = click_data['points'][0]
            region = point.get('x', '')
            breakdown_val = point.get('legendgroup', '')
            
            new_sel = {'region': region, 'breakdown': breakdown_val}
            
            # Toggle logic
            if current_sel and current_sel == new_sel:
                return None, None
            
            return new_sel, None
        
        # Background click
        elif 'chart-container.n_clicks' in trigger_id:
            if current_sel:
                return None, None
        
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
        Output('low-carbon-chart', 'figure'),
        [Input('low-carbon-measure-filter', 'value'),
         Input('low-carbon-breakdown-filter', 'value'),
         Input('low-carbon-chart-selection', 'data'),
         Input('low-carbon-is-expanded', 'data')]
    )
    def update_chart(measure, breakdown, selection, is_expanded):
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

        FROM dev.fact_et_assets a
        LEFT JOIN dev.dim_company b
            ON a.company_id = b.company_id
        LEFT JOIN dev.dim_country c
            ON a.country_id = c.dim_country_id

        WHERE a.new_status <> 'Uncertain'

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
            'breakdown': breakdown
        }
        
        try:
            results = execute_query(query, params)
            df = pd.DataFrame(results)
        except Exception as e:
            print(f"Error executing query: {e}")
            return go.Figure()
        
        if df.empty:
            return go.Figure()
        
        # Process data
        df['Measure Value'] = pd.to_numeric(df['Measure Value'], errors='coerce').fillna(0)
        
        # Scale Investment Value to Billions if applicable
        if measure == 'investment_value':
            df['Measure Value'] = df['Measure Value'] / 1000  # Assuming original is in millions to get Billion
        
        # Aggregate by Region, Breakdown, and Country
        agg_df = df.groupby(['Region', 'Breakdown', 'Country'], as_index=False)['Measure Value'].sum()
        agg_df = agg_df[agg_df['Measure Value'] > 0]
        agg_df = agg_df.dropna(subset=['Region', 'Breakdown'])
        
        if agg_df.empty:
            return go.Figure()
        
        # Sort regions by total value
        region_totals = agg_df.groupby('Region')['Measure Value'].sum().sort_values(ascending=False)
        region_order = region_totals.index.tolist()
        
        # Define x-axis logic
        if is_expanded:
            # Sort agg_df by region order and then by country value within region
            country_totals = agg_df.groupby(['Region', 'Country'])['Measure Value'].sum().reset_index()
            country_totals['RegionCat'] = pd.Categorical(country_totals['Region'], categories=region_order, ordered=True)
            country_totals = country_totals.sort_values(['RegionCat', 'Measure Value'], ascending=[True, False])
            x_axis_order = country_totals['Country'].tolist()
            x_label = 'Country'
        else:
            x_axis_order = region_order
            x_label = 'Region'

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
        
        # Add real traces (hidden from legend)
        for b_val in breakdown_order:
            if b_val not in agg_df['Breakdown'].values:
                continue
                
            b_subset = agg_df[agg_df['Breakdown'] == b_val]
            
            base_color = color_map.get(b_val, '#999999')
            
            # For each segment item (Country in both modes, but mode changes x placement)
            for country in b_subset['Country'].unique():
                c_subset = b_subset[b_subset['Country'] == country]
                region_val = c_subset['Region'].iloc[0]
                
                # Selection logic
                if selection and selection.get('breakdown') == b_val:
                    opacity = 1.0
                    marker_line = dict(color='black', width=1.5)
                elif selection:
                    opacity = 0.2
                    marker_line = dict(color='white', width=0.5)
                else:
                    opacity = 1.0
                    marker_line = dict(color='white', width=0.5)

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

                fig.add_trace(go.Bar(
                    name=b_val,
                    x=c_subset[x_label],
                    y=c_subset['Measure Value'],
                    legendgroup=b_val,
                    showlegend=False,
                    marker=dict(
                        color=base_color,
                        line=marker_line,
                        opacity=opacity
                    ),
                    hovertemplate=(
                        f"<span style='color: #666'>{breakdown_label}:</span> {b_val}<br>"
                        f"<span style='color: #666'>Region:</span> {region_val}<br>"
                        f"<span style='color: #666'>{value_label}:</span> %{{y:,.2f}}{unit}<br>"
                        f"<span style='color: #666'>Asset Country:</span> {country}<extra></extra>"
                    )
                ))

        # Add dummy traces for controlled legend order (Divested at top)
        for b_val in reversed(breakdown_order):
            if b_val in agg_df['Breakdown'].values:
                fig.add_trace(go.Bar(
                    name=b_val,
                    x=[None],
                    y=[None],
                    legendgroup=b_val,
                    marker=dict(color=color_map.get(b_val, '#999999')),
                    showlegend=True
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
                if current_idx + num_countries < len(x_axis_order):
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
                categoryorder='array',
                categoryarray=x_axis_order,
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
            legend=dict(
                traceorder='normal',
                font=dict(size=11, color='#555'),
                itemclick='toggle',
                itemdoubleclick='toggleothers',
                yanchor="top",
                y=0.7,
                xanchor="left",
                x=1.02
            ),
            margin=dict(l=80, r=150, t=100 if is_expanded else 40, b=120 if is_expanded else 80),
            height=600,
            font=dict(family="Arial, sans-serif"),
            plot_bgcolor='white',
            paper_bgcolor='white',
            hoverlabel=dict(
                bgcolor="white",
                bordercolor="#ddd",
                font_size=12,
                font_family="Arial, sans-serif",
                align="left"
            )
        )
        
        return fig
    
    # Export to CSV
    @dash_app.callback(
        Output('low-carbon-download-csv', 'data'),
        Input('low-carbon-export-csv-btn', 'n_clicks'),
        [State('low-carbon-measure-filter', 'value'),
         State('low-carbon-breakdown-filter', 'value')],
        prevent_initial_call=True
    )
    def export_csv(n_clicks, measure, breakdown):
        if not n_clicks:
            return no_update
        
        # Same query as chart
        query = """
        SELECT
            c.et_region                                   AS "Region",
            c.country_long_name                           AS "Country",
            a.new_status                                  AS "Status",
            EXTRACT(YEAR FROM a.date_announced)::int      AS "Year Announced",
            a.investment_type                             AS "Investment Type",

            CASE
                WHEN :measure = 'investment_value'
                    THEN ROUND(SUM(a.investment_usd), 2)
                WHEN :measure = 'investment_count'
                    THEN COUNT(a.investment_usd)
            END                                           AS "Measure Value",

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

        FROM dev.fact_et_assets a
        LEFT JOIN dev.dim_company b
            ON a.company_id = b.company_id
        LEFT JOIN dev.dim_country c
            ON a.country_id = c.dim_country_id

        WHERE a.new_status <> 'Uncertain'

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
        
        params = {'measure': measure, 'breakdown': breakdown}
        
        try:
            results = execute_query(query, params)
            df = pd.DataFrame(results)
            return dcc.send_data_frame(df.to_csv, f"low_carbon_activity_{measure}_{breakdown}.csv", index=False)
        except Exception as e:
            print(f"Error exporting CSV: {e}")
            return no_update