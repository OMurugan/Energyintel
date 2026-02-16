"""
European Gas Trade - Pipeline Flows by Country
Country-specific pipeline flow analytics
"""
import os
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, callback, State, dash_table, clientside_callback, no_update
from core.data_helpers import execute_query

# Color Palette
EI_ORANGE = "#ff6600"
EI_DARK_BLUE = "#1b365d"
EI_LIGHT_BLUE = "#e8f4f8"

# Qualitative colors for countries - matching the reference image
COUNTRY_COLORS = {
    'Belgium': '#4c78a8',           # Dark blue
    'Bulgaria': '#72b7b2',          # Light blue/teal
    'Denmark': '#ff9d4a',           # Orange
    'Finland': '#ffcc99',           # Light orange/peach
    'France': '#e15759',            # Red
    'Germany': '#76b7b2',           # Teal/green
    'Greece': '#b07aa1',            # Purple/pink
    'Hungary': '#9ccc65',           # Light green
    'Italy': '#1f77b4',             # Dark blue
    'Joint Baltic Zone EE/LV': '#bcbd22',  # Olive/yellow-green
    'Lithuania': '#d62728',         # Dark red/brown
    'Moldova': '#ffcc00',           # Yellow
    'Netherlands': '#2ca02c',       # Green
    'Poland': '#17becf',            # Cyan/teal
    'Romania': '#7fcdcd',           # Light teal
    'Slovakia': '#8c564b',          # Brown
    'Spain': '#636363',             # Dark gray
    'United Kingdom': '#ffff00'     # Bright yellow
}

def create_period_selector(prefix):
    """Helper to create independent period selectors for chart or table"""
    return html.Div([
        html.Div([
            html.Span("Year of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
            html.Button('+', id=f'gas-country-toggle-year-btn-{prefix}', n_clicks=0, style={
                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
            })
        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
        
        html.Div([
            html.Span("Quarter of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
            html.Button('+', id=f'gas-country-toggle-quarter-btn-{prefix}', n_clicks=0, style={
                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
            })
        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
        
        html.Div([
            html.Span("Month of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
            html.Button('+', id=f'gas-country-toggle-month-btn-{prefix}', n_clicks=0, style={
                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
            })
        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),

        html.Div([
            html.Span("Week of Year", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
            html.Button('+', id=f'gas-country-toggle-week-btn-{prefix}', n_clicks=0, style={
                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
            })
        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
        
        html.Div([
            html.Span("Day of Year", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
            html.Button('-', id=f'gas-country-toggle-day-btn-{prefix}', n_clicks=0, style={
                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                'backgroundColor': 'white', 'color': '#add8e6', 'borderRadius': '3px', 'cursor': 'pointer',
                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
            })
        ], style={'display': 'flex', 'alignItems': 'center'})
    ], style={
        'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#f8f9fa', 
        'padding': '5px 10px', 'borderRadius': '4px', 'marginBottom': '10px',
        'width': 'fit-content'
    })

def load_data():
    """Load and preprocess data from database - using european_gas_trade table"""
    try:
        # Use the european_gas_trade table which is known to work
        query = """
        SELECT
            tr.source_country AS gas_origin,
            tr.target_country,
            tr.date AS date,
            tr."flow_mcm/d" / 1000.0 AS flows_bcm
        FROM european_gas_trade tr
        WHERE tr.source_country IN ('Algeria','Azerbaijan','Libya','Norway','Russia')
        ORDER BY tr.date;
        """
        
        results = execute_query(query, {})
        df = pd.DataFrame(results)
        
        if df.empty:
            return pd.DataFrame()
            
        # Convert types
        df['flows_bcm'] = pd.to_numeric(df['flows_bcm'], errors='coerce').fillna(0).astype(float)
        df['date'] = pd.to_datetime(df['date'])

        # AGGREGATION: Sum up flows by date, origin, and target country
        df = df.groupby(['date', 'gas_origin', 'target_country'])['flows_bcm'].sum().reset_index()
        
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def create_layout():
    """Create the European Pipeline Flows by Country layout"""
    # Initialize with default values for immediate render
    # Data loading is deferred to callbacks to prevent white screen on load
    
    # Defaults matching the query filters
    origins = ['Algeria', 'Azerbaijan', 'Libya', 'Norway', 'Russia']
    
    # Default destinations (same as fallback in callback)
    destinations = ['Belgium', 'Bulgaria', 'Denmark', 'Finland', 'France', 'Germany', 'Greece', 'Hungary', 'Italy', 'Lithuania', 'Moldova', 'Netherlands', 'Poland', 'Romania', 'Slovakia', 'Spain']
    
    # Default selection
    default_origin = 'Russia'

    return html.Div([
        # Selection stores
        dcc.Store(id='gas-country-chart-period-store', data='DAILY'),
        dcc.Store(id='gas-country-table-period-store', data='DAILY'),
        
        # Main container with Flexbox for Sidebar and Content
        html.Div([
            
            # Sidebar Filter (Right side)
            html.Div([
                html.Div([
                    html.Label("Gas Origin", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE, 'display': 'block', 'marginBottom': '8px'}),
                    dcc.RadioItems(
                        id='gas-country-origin-radio',
                        options=[{'label': ' (All)', 'value': '(All)'}] + [{'label': f' {o}', 'value': o} for o in origins],
                        value=default_origin,
                        style={'fontSize': '12px', 'color': '#333'},
                        labelStyle={'display': 'block', 'marginBottom': '4px', 'paddingLeft': '5px'}
                    ),
                    
                    html.Label("Start Date", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE, 'marginTop': '20px', 'display': 'block', 'marginBottom': '5px'}),
                    dcc.Input(
                        id='gas-country-start-date',
                        type='text',
                        value='2021-01-01',
                        placeholder='YYYY-MM-DD',
                        className='custom-date-input',
                        style={
                            'width': '100%', 'marginBottom': '10px', 'height': '28px',
                            'fontSize': '12px', 'fontFamily': 'Inter, sans-serif',
                            'border': '1px solid #999', 'borderRadius': '0px', 'padding': '0 5px', 'color': '#333'
                        }
                    ),
                    
                    html.Label("End Date", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE, 'marginBottom': '5px', 'display': 'block'}),
                    dcc.Input(
                        id='gas-country-end-date',
                        type='text',
                        value='2026-01-09',
                        placeholder='YYYY-MM-DD',
                        className='custom-date-input',
                        style={
                            'width': '100%', 'marginBottom': '20px', 'height': '28px',
                            'fontSize': '12px', 'fontFamily': 'Inter, sans-serif',
                            'border': '1px solid #999', 'borderRadius': '0px', 'padding': '0 5px', 'color': '#333'
                        }
                    ),
                    
                    # Unified Destination Filter & Legend
                    html.Label("Destination", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE, 'marginBottom': '10px', 'display': 'block'}),
                    
                    # Destination items will be populated by callback
                    html.Div(id='gas-country-dest-list'),
                    
                    # Hidden checklist for maintaining filter functionality
                    dcc.Checklist(
                        id='gas-country-dest-checklist',
                        options=[{'label': o, 'value': o} for o in destinations],
                        value=destinations[:12], # Default select first 12
                        style={'display': 'none'}
                    ),
                ], style={'padding': '0px', 'backgroundColor': 'transparent', 'height': '100%'})
            ], style={'width': '220px', 'order': '2', 'marginLeft': '25px', 'borderLeft': '1px solid #f0f0f0', 'paddingLeft': '20px'}),
            
            # Content Area (Left side)
            html.Div([
                # Chart Section with title and export button
                html.Div([
                    html.H3(id='gas-country-dynamic-title', style={
                        'color': EI_ORANGE, 'fontSize': '20px', 'fontWeight': 'bold',
                        'margin': '0 0 10px 0', 'fontFamily': 'Inter, sans-serif'
                    }),
                    html.Button(
                        "Export to CSV",
                        id="export-gas-country-chart-btn",
                        n_clicks=0,
                        style={
                            'backgroundColor': '#f8f9fa',
                            'color': '#666',
                            'border': '1px solid #ddd',
                            'padding': '6px 12px',
                            'borderRadius': '4px',
                            'fontSize': '11px',
                            'fontFamily': 'Inter, sans-serif',
                            'cursor': 'pointer',
                            'position': 'absolute',
                            'top': '10px',
                            'right': '15px'
                        }
                    )
                ], style={'position': 'relative', 'marginBottom': '10px'}),
                
                dcc.Loading(
                    id='loading-gas-country-chart',
                    type='circle',
                    color=EI_ORANGE,
                    children=dcc.Graph(
                        id='gas-country-line-chart',
                        style={'height': '500px'},
                        config={'displayModeBar': False}
                    )
                ),
                
                # Table Area with header and export button
                html.Div([
                    # Table header with export button
                    html.Div([
                        html.H3("Gas Pipeline Flows to Europe-Billion Cubic Meters", style={
                            'color': EI_ORANGE, 'fontSize': '20px', 'fontWeight': 'bold',
                            'margin': '0', 'fontFamily': 'Inter, sans-serif'
                        }),
                        html.Button(
                            "Export to CSV",
                            id="export-gas-country-table-btn",
                            n_clicks=0,
                            style={
                                'backgroundColor': '#f8f9fa',
                                'color': '#666',
                                'border': '1px solid #ddd',
                                'padding': '6px 12px',
                                'borderRadius': '4px',
                                'fontSize': '11px',
                                'fontFamily': 'Inter, sans-serif',
                                'cursor': 'pointer'
                            }
                        )
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px', 'paddingTop': '10px'}),
                    
                    dcc.Loading(
                        id='loading-gas-country-table',
                        type='circle',
                        color=EI_ORANGE,
                        children=html.Div(id='gas-country-table-container', style={'marginTop': '10px'})
                    )
                ], style={'marginTop': '20px'}),
                
                # Hidden div for clientside callback anchor
                html.Div(id='gas-country-table-enhancer-anchor', style={'display': 'none'}),
                
                # Hidden div to store selected destination for chart highlighting
                html.Div(id='gas-country-selected-destination', style={'display': 'none'}),
                
                # Interval component for monitoring destination clicks
                dcc.Interval(
                    id='gas-country-legend-interval',
                    interval=500,  # Check every 500ms
                    n_intervals=0,
                    disabled=False
                ),
                
                # Download components
                dcc.Download(id="download-gas-country-chart-csv"),
                dcc.Download(id="download-gas-country-table-csv")

            ], style={'flex': '1', 'order': '1', 'minWidth': '0', 'overflow': 'hidden'})
            
        ], style={'display': 'flex', 'padding': '15px'})
    ], className='tab-content', style={'backgroundColor': 'white', 'maxWidth': '1600px', 'margin': '0 auto'})


def register_callbacks(dash_app, server):
    """Register all callbacks for European Pipeline Flows by Country"""

    # Clientside callback to convert text inputs to date inputs (bypasses Dash validation)
    dash_app.clientside_callback(
        """
        function() {
            setTimeout(function() {
                const startInput = document.getElementById('gas-country-start-date');
                const endInput = document.getElementById('gas-country-end-date');
                
                if (startInput && startInput.type === 'text') {
                    startInput.type = 'date';
                    startInput.max = new Date().toISOString().split('T')[0];
                }
                
                if (endInput && endInput.type === 'text') {
                    endInput.type = 'date';
                    endInput.max = new Date().toISOString().split('T')[0];
                }
            }, 100);
            return null;
        }
        """,
        Output('gas-country-table-enhancer-anchor', 'children', allow_duplicate=True),
        Input('gas-country-start-date', 'id'),
        prevent_initial_call='initial_duplicate'
    )

    @dash_app.callback(
        Output('gas-country-dynamic-title', 'children'),
        Input('gas-country-origin-radio', 'value')
    )
    def update_title(selected_origin):
        if selected_origin == '(All)':
            return "All's Pipeline gas Flows to Europe -Billion Cubic Meters"
        return f"{selected_origin}'s Pipeline gas Flows to Europe -Billion Cubic Meters"

    # NEW CALLBACK: Update destination options based on selected gas origin
    @dash_app.callback(
        [Output('gas-country-dest-list', 'children'),
         Output('gas-country-dest-checklist', 'options'),
         Output('gas-country-dest-checklist', 'value')],
        Input('gas-country-origin-radio', 'value')
    )
    def update_destination_options(selected_origin):
        try:
            # Get available destinations for the selected origin using european_gas_trade table
            if selected_origin == '(All)':
                # If All is selected, show all destinations
                query = """
                SELECT DISTINCT tr.target_country
                FROM european_gas_trade tr
                WHERE tr.source_country IN ('Algeria','Azerbaijan','Libya','Norway','Russia')
                ORDER BY tr.target_country;
                """
                results = execute_query(query, {})
            else:
                # If specific origin is selected, show only destinations for that origin
                query = """
                SELECT DISTINCT tr.target_country
                FROM european_gas_trade tr
                WHERE tr.source_country = :selected_origin
                ORDER BY tr.target_country;
                """
                results = execute_query(query, {'selected_origin': selected_origin})
            
            if results:
                destinations = [row['target_country'] for row in results if row['target_country']]
                
                # Create clickable destination items
                dest_items = []
                for dest in destinations:
                    dest_items.append(
                        html.Div([
                            html.Div(style={
                                'width': '14px', 
                                'height': '14px', 
                                'backgroundColor': COUNTRY_COLORS.get(dest, '#ccc'), 
                                'marginRight': '10px', 
                                'borderRadius': '1px',
                                'display': 'inline-block'
                            }),
                            html.Span(dest, style={'display': 'inline-block'})
                        ], 
                        id=f'dest-item-{dest}',
                        style={
                            'display': 'flex', 
                            'alignItems': 'center', 
                            'padding': '6px 8px',
                            'cursor': 'pointer',
                            'borderRadius': '4px',
                            'marginBottom': '2px',
                            'transition': 'all 0.2s ease',
                            'fontSize': '12px',
                            'color': '#666'
                        },
                        className='destination-item',
                        **{'data-country': dest}
                        )
                    )
                
                # Create options for hidden checklist
                options = [{'label': dest, 'value': dest} for dest in destinations]
                
                # Select all available destinations by default
                return dest_items, options, destinations
            else:
                return [], [], []
                
        except Exception as e:
            print(f"Error updating destination options: {e}")
            # Fallback to default destinations
            default_destinations = ['Belgium', 'Bulgaria', 'Denmark', 'Finland', 'France', 'Germany', 'Greece', 'Hungary', 'Italy', 'Lithuania', 'Moldova', 'Netherlands', 'Poland', 'Romania', 'Slovakia', 'Spain']
            
            dest_items = []
            for dest in default_destinations:
                dest_items.append(
                    html.Div([
                        html.Div(style={
                            'width': '14px', 
                            'height': '14px', 
                            'backgroundColor': COUNTRY_COLORS.get(dest, '#ccc'), 
                            'marginRight': '10px', 
                            'borderRadius': '1px',
                            'display': 'inline-block'
                        }),
                        html.Span(dest, style={'display': 'inline-block'})
                    ], 
                    id=f'dest-item-{dest}',
                    style={
                        'display': 'flex', 
                        'alignItems': 'center', 
                        'padding': '6px 8px',
                        'cursor': 'pointer',
                        'borderRadius': '4px',
                        'marginBottom': '2px',
                        'transition': 'all 0.2s ease',
                        'fontSize': '12px',
                        'color': '#666'
                    },
                    className='destination-item',
                    **{'data-country': dest}
                    )
                )
            
            options = [{'label': dest, 'value': dest} for dest in default_destinations]
            return dest_items, options, default_destinations[:12]


    # Clientside callback for destination item clicks
    dash_app.clientside_callback(
        """
        function(children) {
            if (!children) return window.dash_clientside.no_update;
            
            setTimeout(function() {
                const destItems = document.querySelectorAll('.destination-item');
                
                destItems.forEach(function(item) {
                    // Remove existing listeners
                    item.removeEventListener('click', item._clickHandler);
                    
                    // Add click handler
                    item._clickHandler = function() {
                        const country = this.getAttribute('data-country');
                        const hiddenDiv = document.getElementById('gas-country-selected-destination');
                        
                        if (hiddenDiv) {
                            const currentSelection = hiddenDiv.textContent;
                            
                            // Toggle selection
                            if (currentSelection === country) {
                                hiddenDiv.textContent = '';  // Deselect
                                // Reset all items to normal style
                                destItems.forEach(function(di) {
                                    di.style.backgroundColor = 'transparent';
                                    di.style.fontWeight = 'normal';
                                    di.style.color = '#666';
                                });
                            } else {
                                hiddenDiv.textContent = country;  // Select
                                // Reset all items first
                                destItems.forEach(function(di) {
                                    di.style.backgroundColor = 'transparent';
                                    di.style.fontWeight = 'normal';
                                    di.style.color = '#666';
                                });
                                // Highlight selected item
                                this.style.backgroundColor = '#e3f2fd';
                                this.style.fontWeight = 'bold';
                                this.style.color = '#1976d2';
                            }
                        }
                    };
                    
                    item.addEventListener('click', item._clickHandler);
                });
            }, 100);
            
            return window.dash_clientside.no_update;
        }
        """,
        Output('gas-country-selected-destination', 'title'),
        Input('gas-country-dest-list', 'children')
    )

    # Monitor destination selection changes
    dash_app.clientside_callback(
        """
        function(n_intervals) {
            const hiddenDiv = document.getElementById('gas-country-selected-destination');
            if (!hiddenDiv) return window.dash_clientside.no_update;
            
            const currentSelection = hiddenDiv.textContent;
            
            // Store previous selection to detect changes
            if (!window._gasCountryPrevDestSelection) {
                window._gasCountryPrevDestSelection = '';
            }
            
            // If selection changed, trigger chart update
            if (window._gasCountryPrevDestSelection !== currentSelection) {
                window._gasCountryPrevDestSelection = currentSelection;
                return currentSelection;
            }
            
            return window.dash_clientside.no_update;
        }
        """,
        Output('gas-country-selected-destination', 'children'),
        Input('gas-country-legend-interval', 'n_intervals')
    )


    @dash_app.callback(
        Output('gas-country-line-chart', 'figure'),
        [Input('gas-country-start-date', 'value'),
         Input('gas-country-end-date', 'value'),
         Input('gas-country-origin-radio', 'value'),
         Input('gas-country-dest-checklist', 'value'),
         Input('gas-country-selected-destination', 'children')]
    )
    def update_chart(start_date, end_date, selected_origin, selected_dests, selected_destination):
        if not selected_origin or not selected_dests:
            return go.Figure()

        try:
            # Use the european_gas_trade table which is known to work
            query_origins = [selected_origin] if selected_origin != '(All)' else ['Algeria','Azerbaijan','Libya','Norway','Russia']

            query = f"""
            SELECT
                tr.source_country AS gas_origin,
                tr.target_country,
                tr.date AS date,
                tr."flow_mcm/d" / 1000.0 AS flows_bcm
            FROM european_gas_trade tr
            WHERE tr.source_country = ANY(:origins)
              AND tr.date >= :start_date
              AND tr.date <= :end_date
            ORDER BY tr.date;
            """
            
            results = execute_query(query, {
                'start_date': start_date,
                'end_date': end_date,
                'origins': query_origins
            })
            df = pd.DataFrame(results)
            if df.empty:
                return go.Figure()

            # Convert types
            df['flows_bcm'] = pd.to_numeric(df['flows_bcm'], errors='coerce').fillna(0).astype(float)
            df['date'] = pd.to_datetime(df['date'])
            
            # Apply destination filter
            df = df[df['target_country'].isin(selected_dests)]
            
            if df.empty:
                return go.Figure()

            # AGGREGATION: Sum up flows by date, origin, and target country
            df = df.groupby(['date', 'gas_origin', 'target_country'])['flows_bcm'].sum().reset_index()

            # Monthly aggregation for chart display
            df['month_date'] = df['date'].dt.to_period('M').dt.to_timestamp()
            monthly_df = df.groupby(['month_date', 'gas_origin', 'target_country'])['flows_bcm'].sum().reset_index()

            fig = go.Figure()
            
            for dest in selected_dests:
                dest_df = monthly_df[monthly_df['target_country'] == dest].sort_values('month_date')
                if not dest_df.empty:
                    # Create custom hover text
                    hover_text = []
                    for _, row in dest_df.iterrows():
                        month_str = row['month_date'].strftime('%B %Y')
                        hover_text.append(
                            f"Target Country: {dest}<br>" +
                            f"Month of Date: {month_str}<br>" +
                            f"flows_bcm: {row['flows_bcm']:.3f}"
                        )
                    
                    # Determine line styling based on selection
                    is_selected = selected_destination == dest if selected_destination else True
                    line_opacity = 1.0 if is_selected else 0.3
                    line_width = 3 if is_selected else 1
                    line_color = COUNTRY_COLORS.get(dest, '#999')
                    
                    # If a country is selected, make it more prominent
                    if selected_destination and is_selected:
                        line_width = 4
                        line_opacity = 1.0
                    elif selected_destination and not is_selected:
                        line_opacity = 0.2
                        line_width = 1
                    
                    fig.add_trace(go.Scatter(
                        x=dest_df['month_date'],
                        y=dest_df['flows_bcm'],
                        name=dest,
                        mode='lines',
                        line=dict(width=line_width, color=line_color),
                        opacity=line_opacity,
                        text=hover_text,
                        hovertemplate="%{text}<extra></extra>",
                        hoverlabel=dict(
                            bgcolor="white",
                            bordercolor="gray",
                            font=dict(color="black", size=12)
                        )
                    ))

            fig.update_layout(
                margin=dict(l=40, r=20, t=10, b=40),
                paper_bgcolor='white',
                plot_bgcolor='white',
                hovermode='closest',
                showlegend=False,
                xaxis=dict(
                    showgrid=True, gridcolor='#f5f5f5',
                    tickfont=dict(size=10, color='#999'),
                    tickformat="%b %y", dtick="M6",
                    fixedrange=True,
                    range=[start_date, end_date]
                ),
                yaxis=dict(
                    showgrid=True, gridcolor='#f5f5f5',
                    tickfont=dict(size=10, color='#999'),
                    zeroline=True, zerolinecolor='#f5f5f5',
                    fixedrange=True,
                    range=[0, max(monthly_df['flows_bcm'].max() * 1.2 if not monthly_df.empty else 1.0, 1.0)]
                ),
                font=dict(family="Lato, sans-serif")
            )
            return fig
            
        except Exception as e:
            print(f"Error updating gas flows chart: {e}")
            import traceback
            traceback.print_exc()
            return go.Figure()

    @dash_app.callback(
        Output('gas-country-table-container', 'children'),
        [Input('gas-country-start-date', 'value'),
         Input('gas-country-end-date', 'value'),
         Input('gas-country-origin-radio', 'value'),
         Input('gas-country-dest-checklist', 'value'),
         Input('gas-country-selected-destination', 'children')]
    )
    def update_table(start_date, end_date, selected_origin, selected_dests, selected_destination):
        if not selected_origin or not selected_dests:
            return html.Div("Please select filters.", style={'color': '#666', 'fontSize': '12px', 'padding': '20px'})

        # Use the european_gas_trade table which is known to work
        try:
            query_origins = [selected_origin] if selected_origin != '(All)' else ['Algeria','Azerbaijan','Libya','Norway','Russia']

            query = f"""
            SELECT
                tr.date AS date,
                tr.source_country AS gas_origin,
                tr.target_country AS target_country,
                tr.pointlabel AS point_label,
                tr."flow_mcm/d" / 1000.0 AS flows_bcm
            FROM european_gas_trade tr
            WHERE tr.source_country = ANY(:origins)
              AND tr.date >= :start_date
              AND tr.date <= :end_date
            ORDER BY tr.date DESC;
            """

            results = execute_query(query, {
                'start_date': start_date,
                'end_date': end_date,
                'origins': query_origins
            })
            df = pd.DataFrame(results)
            
            if df.empty:
                return html.Div("No data available for the selected filters.", style={'color': '#666', 'fontSize': '12px', 'padding': '20px'})

            # Convert types
            df['flows_bcm'] = pd.to_numeric(df['flows_bcm'], errors='coerce').fillna(0)
            df['date'] = pd.to_datetime(df['date'])

            # Apply destination filter
            df = df[df['target_country'].isin(selected_dests)]

            if df.empty:
                return html.Div("No data matches filters.", style={'padding': '20px'})

            # Aggregate by date, origin, target country, and point
            df = df.groupby(['date', 'gas_origin', 'target_country', 'point_label'])['flows_bcm'].sum().reset_index()

            # Pivot for multi-level headers (same structure as main file)
            pivot_df = df.pivot_table(
                index='date',
                columns=['gas_origin', 'target_country', 'point_label'],
                values='flows_bcm'
            ).reset_index()
            
            # Sort by date descending
            pivot_df = pivot_df.sort_values(pivot_df.columns[0], ascending=False)

            # Sort origins (same order as main file)
            origin_order = ['Algeria', 'Azerbaijan', 'Libya', 'Norway', 'Russia']
            
            def sort_columns_key(col):
                if col[0] == 'date':
                    return (-1, "")
                origin = col[0]
                order = origin_order.index(origin) if origin in origin_order else 99
                return (order, str(col[2]))

            # Determine the actual column name for the date
            date_col_name = pivot_df.columns[0]
            
            # Get hierarchical columns (excluding the date column)
            hier_cols = [c for c in pivot_df.columns if c != date_col_name]
            hier_cols.sort(key=sort_columns_key)
            
            table_columns = [{"name": ["", "", "Day of Date"], "id": "Day of Date"}]
            for col in hier_cols:
                table_columns.append({
                    "name": list(col),
                    "id": "_".join(map(str, col))
                })

            # Prepare data
            # Convert date to string after sorting but before iteration
            pivot_df[date_col_name] = pd.to_datetime(pivot_df[date_col_name], errors='coerce').dt.strftime('%B %d, %Y')
            
            table_data = []
            for _, row in pivot_df.iterrows():
                d_row = {"Day of Date": row[date_col_name]}
                for col in hier_cols:
                    val = row[col]
                    # Format as float only if it's numeric
                    if pd.notnull(val):
                        try:
                            d_row["_".join(map(str, col))] = f"{float(val):.4f}"
                        except (ValueError, TypeError):
                            d_row["_".join(map(str, col))] = str(val)
                    else:
                        d_row["_".join(map(str, col))] = ""
                table_data.append(d_row)

            # Create conditional styling for selected destination
            style_data_conditional = [
                {
                    'if': {'column_id': 'Day of Date'},
                    'textAlign': 'left',
                    'fontWeight': 'normal',
                    'color': '#666',
                    'minWidth': '180px',
                    'borderRight': '2px solid #dee2e6'
                },
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#f8f9fa'
                }
            ]
            
            # Add highlighting for selected destination columns
            if selected_destination:
                # Find columns that match the selected destination
                for col in hier_cols:
                    if col[1] == selected_destination:  # col[1] is the target_country
                        column_id = "_".join(map(str, col))
                        style_data_conditional.append({
                            'if': {'column_id': column_id},
                            'backgroundColor': '#e3f2fd',
                            'color': '#1976d2',
                            'fontWeight': 'bold',
                            'border': '2px solid #1976d2'
                        })
            
            # Create conditional header styling
            style_header_conditional = [
                {
                    'if': {'header_index': 0}, # This targets the top-most header row (Origin)
                    'backgroundColor': '#e9ecef',
                    'color': '#212529',
                    'fontSize': '12px',
                    'fontWeight': 'bold'
                },
                {
                    'if': {'header_index': 1}, # This targets the second header row (Interconnection Point)
                    'backgroundColor': 'white',
                    'fontSize': '11px',
                    'color': '#666'
                }
            ]
            
            # Add header highlighting for selected destination
            if selected_destination:
                # Highlight headers for the selected destination
                for i, col in enumerate(table_columns):
                    if col["name"][1] == selected_destination:  # Check if this column belongs to selected destination
                        style_header_conditional.append({
                            'if': {'column_id': col["id"]},
                            'backgroundColor': '#1976d2',
                            'color': 'white',
                            'fontWeight': 'bold'
                        })

            return dash_table.DataTable(
                id='gas-country-data-table',
                columns=table_columns,
                data=table_data,
                merge_duplicate_headers=True,
                page_action='none',
                style_table={
                    'overflowX': 'auto',
                    'overflowY': 'auto',
                    'height': '600px',
                    'width': '100%',
                    'border': 'none',
                    'marginTop': '10px'
                },
                style_header={
                    'backgroundColor': 'white',
                    'color': EI_DARK_BLUE,
                    'fontWeight': 'bold',
                    'textAlign': 'center',
                    'fontSize': '12px',
                    'fontFamily': 'Inter, sans-serif',
                    'border': '1px solid #dee2e6',
                    'padding': '10px'
                },
                style_cell={
                    'padding': '8px',
                    'textAlign': 'center',
                    'fontSize': '11px',
                    'fontFamily': 'Inter, sans-serif',
                    'border': '1px solid #dee2e6',
                    'color': '#333',
                    'minWidth': '100px'
                },
                style_data_conditional=style_data_conditional,
                style_header_conditional=style_header_conditional,
                fixed_rows={'headers': True},
                virtualization=True
            )

        except Exception as e:
            print(f"Error updating gas flows table: {e}")
            import traceback
            traceback.print_exc()
            return html.Div(f"Error loading table: {str(e)}", style={'color': 'red'})

    # Complete table highlighting functionality - Column, Cell, and Row highlighting
    dash_app.clientside_callback(
        """
        function(id) {
            const tableId = 'gas-country-data-table';
            const baseStyleId = 'gas-country-table-base-css';
            const dynamicStyleId = 'gas-country-table-dynamic-highlight-css';
            
            // 1. Inject Base CSS if not present
            if (!document.getElementById(baseStyleId)) {
                const style = document.createElement('style');
                style.id = baseStyleId;
                style.innerHTML = `
                    #${tableId} .dash-spreadsheet-container {
                        cursor: pointer;
                    }
                    #${tableId} .dash-spreadsheet-container td,
                    #${tableId} .dash-spreadsheet-container th {
                        transition: all 0.15s ease;
                    }
                    
                    /* Hover effects for better UX */
                    #${tableId} .dash-spreadsheet-container td:hover {
                        background-color: #f0f8ff !important;
                    }
                    #${tableId} .dash-spreadsheet-container th:hover {
                        background-color: #e6f3ff !important;
                    }
                    
                    /* Selected column header styling */
                    #${tableId} .dash-spreadsheet-container th.column-header-selected {
                        background-color: #4a90e2 !important;
                        color: white !important;
                        font-weight: bold !important;
                    }
                    
                    /* Sidebar UI Refinements */
                    .custom-legend-filter input[type="checkbox"] {
                        display: none;
                    }
                    .custom-legend-filter label {
                        cursor: pointer;
                        transition: all 0.2s ease;
                    }
                    .custom-legend-filter label:hover {
                        background-color: #f5f5f5;
                    }
                    
                    .custom-date-input {
                        font-family: 'Inter', sans-serif;
                    }
                `;
                document.head.appendChild(style);
            }
            
            const setupListener = () => {
                const tableEl = document.getElementById(tableId);
                if (!tableEl) return;
                const container = tableEl.querySelector('.dash-spreadsheet-container');
                if (!container || container.dataset.highlightEnhanced === 'true') return;
                container.dataset.highlightEnhanced = 'true';
                
                container.addEventListener('click', function(e) {
                    const header = e.target.closest('th[data-dash-column]');
                    const cell = e.target.closest('td[data-dash-column]');
                    if (!header && !cell) return;
                    
                    const columnId = (header || cell).getAttribute('data-dash-column');
                    const rowIndex = cell ? cell.getAttribute('data-dash-row') : null;
                    
                    const isHeader = !!header;
                    const isDateColumn = columnId === 'Day of Date';
                    
                    // Determine what type of highlighting to apply
                    let highlightType = '';
                    let selectionKey = '';
                    
                    if (isHeader && !isDateColumn) {
                        // Column header click - highlight entire column
                        highlightType = 'column';
                        const headerRow = header.closest('tr');
                        const thead = header.closest('thead');
                        const headerRows = thead ? Array.from(thead.querySelectorAll('tr')) : [];
                        const headerIndex = headerRow ? headerRows.indexOf(headerRow) : -1;
                        selectionKey = columnId + '_header_' + headerIndex;
                    } else if (isDateColumn && cell) {
                        // Date cell click - highlight entire row
                        highlightType = 'row';
                        selectionKey = 'row_' + rowIndex;
                    } else if (cell && !isDateColumn) {
                        // Data cell click - highlight individual cell
                        highlightType = 'cell';
                        selectionKey = columnId + '_cell_' + rowIndex;
                    } else {
                        return; // Invalid click target
                    }
                    
                    // Toggle selection if clicking same element
                    if (container.dataset.lastSelection === selectionKey) {
                        container.dataset.lastSelection = '';
                        container.querySelectorAll('.column-header-selected').forEach(el => el.classList.remove('column-header-selected'));
                        const dynStyle = document.getElementById(dynamicStyleId);
                        if (dynStyle) dynStyle.remove();
                        return;
                    }
                    
                    // Clear previous selection
                    container.dataset.lastSelection = selectionKey;
                    container.querySelectorAll('.column-header-selected').forEach(el => el.classList.remove('column-header-selected'));
                    
                    // Generate dynamic styles based on highlight type
                    let dynamicStyles = '';
                    
                    if (highlightType === 'column') {
                        // COLUMN HIGHLIGHTING
                        let targetColumnIds = [columnId];
                        
                        // Handle multi-column headers
                        const headerRow = header.closest('tr');
                        const thead = header.closest('thead');
                        const headerRows = thead ? Array.from(thead.querySelectorAll('tr')) : [];
                        const colspan = parseInt(header.getAttribute('colspan') || header.colSpan || '1');
                        
                        if (colspan > 1) {
                            const bottomRow = headerRows[headerRows.length - 1];
                            const allBottomHeaders = Array.from(bottomRow.querySelectorAll('th[data-dash-column]'));
                            let currentIdx = 0;
                            const bottomHeaderMap = allBottomHeaders.map(h => {
                                const cs = parseInt(h.getAttribute('colspan') || h.colSpan || '1');
                                const start = currentIdx;
                                currentIdx += cs;
                                return { header: h, start: start, end: currentIdx, colId: h.getAttribute('data-dash-column') };
                            });
                            
                            let clickedStartIdx = 0;
                            const rowHeaders = Array.from(headerRow.querySelectorAll('th'));
                            for (let h of rowHeaders) {
                                if (h === header) break;
                                clickedStartIdx += parseInt(h.getAttribute('colspan') || h.colSpan || '1');
                            }
                            const clickedEndIdx = clickedStartIdx + colspan;
                            
                            targetColumnIds = bottomHeaderMap
                                .filter(m => m.start >= clickedStartIdx && m.end <= clickedEndIdx && m.colId !== 'Day of Date')
                                .map(m => m.colId);
                        }
                        
                        header.classList.add('column-header-selected');
                        
                        // Highlight all cells in the selected columns
                        targetColumnIds.forEach(id => {
                            dynamicStyles += `
                                #${tableId} .dash-spreadsheet-container td[data-dash-column="${id}"] {
                                    background-color: #b3d9ff !important;
                                    color: #1b365d !important;
                                    font-weight: 500 !important;
                                }
                            `;
                        });
                        
                    } else if (highlightType === 'row') {
                        // ROW HIGHLIGHTING
                        dynamicStyles += `
                            #${tableId} .dash-spreadsheet-container tr:has(td[data-dash-row="${rowIndex}"]) td {
                                background-color: #b3d9ff !important;
                                color: #1b365d !important;
                                font-weight: 500 !important;
                            }
                            #${tableId} .dash-spreadsheet-container td[data-dash-column="Day of Date"][data-dash-row="${rowIndex}"] {
                                background-color: #b3d9ff !important;
                                color: #1b365d !important;
                                font-weight: bold !important;
                            }
                        `;
                        
                    } else if (highlightType === 'cell') {
                        // CELL HIGHLIGHTING
                        dynamicStyles += `
                            #${tableId} .dash-spreadsheet-container td[data-dash-column="${columnId}"][data-dash-row="${rowIndex}"] {
                                background-color: #e1f0ff !important;
                                color: #1b365d !important;
                                font-weight: 600 !important;
                                border: 2px solid #fe5000 !important;
                                border-radius: 2px;
                                z-index: 10 !important;
                                position: relative;
                            }
                        `;
                    }
                    
                    // Apply the dynamic styles
                    let dynStyle = document.getElementById(dynamicStyleId);
                    if (!dynStyle) {
                        dynStyle = document.createElement('style');
                        dynStyle.id = dynamicStyleId;
                        document.head.appendChild(dynStyle);
                    }
                    dynStyle.innerHTML = dynamicStyles;
                });
            };
            
            // Setup the listener and keep checking for table updates
            setupListener();
            if (!window._gasCountryTableInterval) {
                window._gasCountryTableInterval = setInterval(setupListener, 1000);
            }
            return null;
        }
        """,
        Output('gas-country-table-enhancer-anchor', 'children'),
        Input('gas-country-table-enhancer-anchor', 'id')
    )

    # CSV Export Callbacks
    @dash_app.callback(
        Output("download-gas-country-chart-csv", "data"),
        Input("export-gas-country-chart-btn", "n_clicks"),
        [State('gas-country-start-date', 'value'),
         State('gas-country-end-date', 'value'),
         State('gas-country-origin-radio', 'value'),
         State('gas-country-dest-checklist', 'value')],
        prevent_initial_call=True,
    )
    def export_chart_data(n_clicks, start_date, end_date, selected_origin, selected_dests):
        """Export chart data to CSV."""
        if n_clicks == 0:
            return no_update
            
        try:
            if not selected_origin or not selected_dests:
                return no_update
                
            # Use european_gas_trade table
            query_origins = [selected_origin] if selected_origin != '(All)' else ['Algeria','Azerbaijan','Libya','Norway','Russia']

            query = f"""
            SELECT
                tr.source_country AS gas_origin,
                tr.target_country,
                tr.date AS date,
                tr."flow_mcm/d" / 1000.0 AS flows_bcm
            FROM european_gas_trade tr
            WHERE tr.source_country = ANY(:origins)
              AND tr.date >= :start_date
              AND tr.date <= :end_date
            ORDER BY tr.date;
            """
            
            results = execute_query(query, {
                'start_date': start_date,
                'end_date': end_date,
                'origins': query_origins
            })
            df = pd.DataFrame(results)
            
            if df.empty:
                return no_update

            # Apply same transformations as chart
            df['flows_bcm'] = pd.to_numeric(df['flows_bcm'], errors='coerce').fillna(0).astype(float)
            df['date'] = pd.to_datetime(df['date'])
            
            # Apply filters
            df = df[df['target_country'].isin(selected_dests)]
            
            # Aggregate by date, origin, and target country for monthly data
            df = df.groupby(['date', 'gas_origin', 'target_country'])['flows_bcm'].sum().reset_index()
            
            # Monthly aggregation
            df['month_date'] = df['date'].dt.to_period('M').dt.to_timestamp()
            monthly_df = df.groupby(['month_date', 'gas_origin', 'target_country'])['flows_bcm'].sum().reset_index()
            
            # Prepare export data to match CSV format
            export_df = monthly_df.sort_values(['month_date', 'target_country']).copy()
            export_df['Month of Date'] = export_df['month_date'].dt.strftime('%B %Y')  # Format like "January 2021"
            export_df = export_df[['Month of Date', 'target_country', 'flows_bcm']].rename(columns={
                'target_country': 'Target Country',
                'flows_bcm': 'flows_bcm'
            })
            
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gas_pipeline_flows_country_chart_{timestamp}.csv"
            return dcc.send_data_frame(export_df.to_csv, filename, index=False)
            
        except Exception as e:
            print(f"Error exporting chart data: {e}")
            return no_update

    @dash_app.callback(
        Output("download-gas-country-table-csv", "data"),
        Input("export-gas-country-table-btn", "n_clicks"),
        [State('gas-country-start-date', 'value'),
         State('gas-country-end-date', 'value'),
         State('gas-country-origin-radio', 'value'),
         State('gas-country-dest-checklist', 'value')],
        prevent_initial_call=True,
    )
    def export_table_data(n_clicks, start_date, end_date, selected_origin, selected_dests):
        """Export table data to CSV."""
        if n_clicks == 0:
            return no_update
            
        try:
            if not selected_origin or not selected_dests:
                return no_update

            query_origins = [selected_origin] if selected_origin != '(All)' else ['Algeria','Azerbaijan','Libya','Norway','Russia']

            query = f"""
            SELECT
                tr.date AS date,
                tr.source_country AS gas_origin,
                tr.target_country AS target_country,
                tr.pointlabel AS point_label,
                tr."flow_mcm/d" / 1000.0 AS flows_bcm
            FROM european_gas_trade tr
            WHERE tr.source_country = ANY(:origins)
              AND tr.date >= :start_date
              AND tr.date <= :end_date
            ORDER BY tr.date DESC;
            """

            results = execute_query(query, {
                'start_date': start_date,
                'end_date': end_date,
                'origins': query_origins
            })
            df = pd.DataFrame(results)
            
            if df.empty:
                return no_update

            # Apply same transformations as table
            df['flows_bcm'] = pd.to_numeric(df['flows_bcm'], errors='coerce').fillna(0)
            df['date'] = pd.to_datetime(df['date'])

            # Apply filters
            df = df[df['target_country'].isin(selected_dests)]

            # Aggregate
            df = df.groupby(['date', 'gas_origin', 'target_country', 'point_label'])['flows_bcm'].sum().reset_index()

            # Prepare export data - flatten the hierarchical structure for CSV
            export_df = df.sort_values('date', ascending=False).copy()
            export_df['date'] = export_df['date'].dt.strftime('%Y-%m-%d')
            export_df = export_df.rename(columns={
                'date': 'Date',
                'gas_origin': 'Gas Origin',
                'target_country': 'Target Country',
                'point_label': 'Interconnection Point',
                'flows_bcm': 'Flows (BCM)'
            })
            
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gas_pipeline_flows_country_table_{timestamp}.csv"
            return dcc.send_data_frame(export_df.to_csv, filename, index=False)
            
        except Exception as e:
            print(f"Error exporting table data: {e}")
            return no_update