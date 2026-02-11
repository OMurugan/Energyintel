"""
Activity by Date Announced
Low-carbon investment activity analytics by announcement date
"""
from dash import dcc, html, Input, Output, State, no_update, callback_context, clientside_callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
from core.data_helpers import get_db_engine

# -----------------------------------------------------------------------------
# SQL QUERIES
# -----------------------------------------------------------------------------

QUERY_PROJECT_CATEGORY = """
WITH params AS (
    SELECT
        '{period}'::text AS period   -- YEARLY | QUARTERLY | MONTHLY | DAILY
)
SELECT
    EXTRACT(YEAR FROM a.date_announced)::int AS "Year of Date",
    CASE
        WHEN p.period IN ('QUARTERLY', 'MONTHLY', 'DAILY')
            THEN 'Q' || EXTRACT(QUARTER FROM a.date_announced)::int
        ELSE NULL
    END AS "Quarter of Date",
    CASE
        WHEN p.period IN ('QUARTERLY', 'MONTHLY', 'DAILY')
            THEN EXTRACT(MONTH FROM a.date_announced)::int
        ELSE NULL
    END AS "Month of Date",
    CASE
        WHEN p.period IN ('QUARTERLY', 'MONTHLY', 'DAILY')
            THEN EXTRACT(DAY FROM a.date_announced)::int
        ELSE NULL
    END AS "Day of Date",
    a.date_announced AS "Date Announced",
    a.project_category_1 AS "Breakdown",
    a.investment_type AS "Investment Type",
    a.new_status AS "Status",
    COUNT(*) AS investment_count,
    ROUND(SUM(a.investment_usd) / 1000.0, 2) AS investment_value
FROM dev.fact_et_assets a
LEFT JOIN dev.dim_company b
    ON a.company_id = b.company_id
LEFT JOIN dev.dim_country c
    ON a.country_id = c.dim_country_id
CROSS JOIN params p
WHERE a.new_status <> 'Uncertain'
  AND a.date_announced >= DATE '2018-01-01'
GROUP BY
    EXTRACT(YEAR FROM a.date_announced),
    "Quarter of Date",
    "Month of Date",
    "Day of Date",
    a.date_announced,
    a.project_category_1,
    a.investment_type,
    a.new_status,
    p.period
ORDER BY
    "Year of Date",
    "Quarter of Date" DESC NULLS LAST,
    "Month of Date" DESC NULLS LAST,
    "Day of Date" DESC NULLS LAST,
    "Breakdown",
    "Investment Type",
    "Status";
"""

QUERY_PEER_GROUP = """
WITH params AS (
    SELECT
        '{period}'::text AS period   -- YEARLY | QUARTERLY | MONTHLY | DAILY
)
SELECT
    EXTRACT(YEAR FROM a.date_announced)::int AS "Year of Date",
    CASE
        WHEN p.period IN ('QUARTERLY', 'MONTHLY', 'DAILY')
            THEN 'Q' || EXTRACT(QUARTER FROM a.date_announced)::int
        ELSE NULL
    END AS "Quarter of Date",
    CASE
        WHEN p.period IN ('QUARTERLY', 'MONTHLY', 'DAILY')
            THEN EXTRACT(MONTH FROM a.date_announced)::int
        ELSE NULL
    END AS "Month of Date",
    CASE
        WHEN p.period IN ('QUARTERLY', 'MONTHLY', 'DAILY')
            THEN EXTRACT(DAY FROM a.date_announced)::int
        ELSE NULL
    END AS "Day of Date",
    a.date_announced AS "Date Announced",
    b.peer_group_simple AS "Breakdown",
    a.investment_type AS "Investment Type",
    a.new_status AS "Status",
    COUNT(*) AS investment_count,
    ROUND(SUM(a.investment_usd) / 1000.0, 2) AS investment_value
FROM dev.fact_et_assets a
LEFT JOIN dev.dim_company b
    ON a.company_id = b.company_id
LEFT JOIN dev.dim_country c
    ON a.country_id = c.dim_country_id
CROSS JOIN params p
WHERE a.new_status <> 'Uncertain'
  AND a.date_announced >= DATE '2018-01-01'
GROUP BY
    EXTRACT(YEAR FROM a.date_announced),
    "Quarter of Date",
    "Month of Date",
    "Day of Date",
    a.date_announced,
    b.peer_group_simple,
    a.investment_type,
    a.new_status,
    p.period
ORDER BY
    "Year of Date",
    "Quarter of Date" DESC NULLS LAST,
    "Month of Date" DESC NULLS LAST,
    "Day of Date" DESC NULLS LAST,
    "Breakdown",
    "Investment Type",
    "Status";
"""

# -----------------------------------------------------------------------------
# CONSTANTS & STYLES
# -----------------------------------------------------------------------------

COLOR_PALETTE = {
    # Project Category Colors
    "CCS & Carbon Removal": "#006BA4",  # Blue
    "Electricity Solutions": "#595959", # Dark Grey
    "EVs & Mobility": "#4E5D6C",        # Grey Blue
    "Hydrogen & L-C Fuels/Gases": "#B6CB92", # Light Green
    "L-C Power Generation": "#FF5A09",  # Orange
    "Other": "#A52A2A",                 # Brown

    # Peer Group Colors (Matching Image 1)
    "European Major": "#006BA4",
    "Independent E&P": "#555555",
    "Independent Refiner": "#4E5D6C",
    "Midstream Firm": "#A9A9A9",
    "NOC": "#C8522D",
    "US Major": "#8B4513"
}

SIDEBAR_STYLE = {
    "width": "12rem",
    "padding": "2rem 1rem",
    "backgroundColor": "transparent",
    "flexShrink": 0
}

CONTENT_STYLE = {
    "flex": 1,
    "padding": "2rem 1rem",
    "minWidth": 0
}

# -----------------------------------------------------------------------------
# LAYOUT
# -----------------------------------------------------------------------------

def create_layout():
    """Create the Activity by Date layout"""
    return html.Div([
        # Download components
        dcc.Download(id="download-lcad-chart-csv"),
        dcc.Download(id="download-lcad-table-csv"),
        
        # Initialize stores
        dcc.Store(id='lcad-data-store'),
        dcc.Store(id='lcad-selection-store'), # Tracks highlighted series name
        dcc.Store(id='lcad-status-prev-store'), # Tracks previous status values
        dcc.Store(id='lcad-inv-type-prev-store'), # Tracks previous inv type values
        dcc.Store(id='lcad-chart-time-level', data='YEARLY'), # Chart hierarchy state
        dcc.Store(id='lcad-table-time-level', data='YEARLY'), # Table hierarchy state

        # Main Layout (Natural Scrolling)
        html.Div([
            # 1. Main Content (Left)
            html.Div([
                html.H2(id='lcad-chart-title', style={'color': '#FF5A09', 'fontWeight': 'bold', 'marginBottom': '10px', 'fontFamily': 'Georgia, serif'}),
                
                # New Header row for Hierarchy Icons and Export Button
                html.Div([
                    # Chart Hierarchy Controls (left)
                    html.Div([
                        html.Div([
                            html.Span("Year of Date", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('-', id='lcad-chart-toggle-year-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#add8e6', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Quarter of Date", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('+', id='lcad-chart-toggle-quarter-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Month of Date", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('+', id='lcad-chart-toggle-month-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                        
                        html.Div([
                            html.Span("Day of Year", style={'fontSize': '11px', 'color': '#1b365d', 'marginRight': '8px'}),
                            html.Button('+', id='lcad-chart-toggle-day-btn', n_clicks=0, style={
                                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                            })
                        ], style={'display': 'flex', 'alignItems': 'center'})
                    ], style={
                        'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#f8f9fa', 
                        'padding': '5px 10px', 'borderRadius': '4px'
                    }),

                    # Chart Export Button (right)
                    html.Div(dcc.Loading(
                        html.Button("Export to CSV", id="export-lcad-chart-btn", n_clicks=0, style={
                            "backgroundColor": "white",
                            "color": "#2c3e50",
                            "border": "1px solid #dee2e6",
                            "padding": "6px 12px",
                            "borderRadius": "4px",
                            "cursor": "pointer",
                            "fontSize": "12px",
                            "fontWeight": "normal",
                        })
                    ))
                ], style={
                    'display': 'flex', 
                    'justifyContent': 'space-between', 
                    'alignItems': 'center', 
                    'padding': '0 10px',
                    'marginBottom': '10px'
                }),
                
                # Chart Container
                html.Div([
                    dcc.Loading(
                        id="loading-chart",
                        type="circle",
                        children=[
                            dcc.Graph(
                                id='lcad-chart',
                                config={'displayModeBar': False},
                                style={'height': '105vh'}
                            )
                        ]
                    )
                ], style={'backgroundColor': '#fff', 'padding': '10px'}),
                
                html.Div([
                    html.P("Source: Energy Intelligence, Low-Carbon Investment Tracker. Data as of Q4 2025.", 
                           style={'fontSize': '10px', 'color': '#666', 'margin': '0'}),
                    html.P([
                        "Covers activity by leading oil and gas firms, tracked by date initially announced or approved. Reported or estimated value is net for companies tracked. For more information see methodology. ",
                        html.A("Go To Low-Carbon Investment Tracker", 
                               href="https://www.energyintel.com/low-carbon-energy-data#low-carbon-investment-data", 
                               target="_blank",
                               style={'fontSize': '10px', 'color': '#006BA4', 'textDecoration': 'underline'})
                    ], style={'fontSize': '10px', 'color': '#666', 'marginTop': '1px', 'lineHeight': '1.2'}),
                ], style={'marginTop': '10px'}),
                
                # Hidden components for X-Axis Click Listening
                dcc.Input(id='lcad-axis-click-trigger', type='text', style={'display': 'none'}),
                html.Div(id='lcad-axis-listener-output', style={'display': 'none'})
                
            ], style=CONTENT_STYLE),

            # 2. Sidebar (Right)
            html.Div([
                
                html.Label("Aggregation Interval", className="fw-bold mb-0", style={'fontSize': '11px'}),
                dcc.Dropdown(
                    id='lcad-interval-dropdown',
                    options=[
                        {'label': 'Yearly', 'value': 'YEARLY'},
                        {'label': 'Quarterly', 'value': 'QUARTERLY'}
                    ],
                    value='YEARLY',
                    clearable=False,
                    searchable=False,
                    style={'marginBottom': '8px', 'fontSize': '11px', 'minHeight': '24px', 'height': '20px', 'width': '180px'},
                ),

                html.Label("Breakdown", className="fw-bold mb-0", style={'fontSize': '11px'}),
                dcc.Dropdown(
                    id='lcad-breakdown-dropdown',
                    options=[
                        {'label': 'Project Category', 'value': 'Project Category'},
                        {'label': 'Peer Group', 'value': 'Peer Group'}
                    ],
                    value='Project Category',
                    clearable=False,
                    searchable=False,
                    style={'marginBottom': '8px', 'fontSize': '11px', 'minHeight': '24px', 'height': '24px', 'width': '180px'}
                ),

                html.Label("Measure", className="fw-bold mb-0", style={'fontSize': '11px'}),
                dcc.Dropdown(
                    id='lcad-measure-dropdown',
                    options=[
                        {'label': 'Investment Value', 'value': 'investment_value'},
                        {'label': 'Investment Count', 'value': 'investment_count'}
                    ],
                    value='investment_value',
                    clearable=False,
                    searchable=False,
                    style={'marginBottom': '8px', 'fontSize': '11px', 'minHeight': '24px', 'height': '24px', 'width': '180px'}
                ),

                html.Label("Status", className="fw-bold mb-0", style={'fontSize': '11px'}),
                dcc.Checklist(
                    id='lcad-status-checklist',
                    options=[],
                    value=[],
                    style={'marginBottom': '10px', 'maxHeight': '150px', 'overflowY': 'auto', 'fontSize': '12px'},
                    inputStyle={"marginRight": "4px", "accentColor": "#555"},
                    labelStyle={"display": "block", "marginBottom": "2px"}
                ),

                html.Label("Investment Type", className="fw-bold mb-0", style={'fontSize': '11px'}),
                dcc.Checklist(
                    id='lcad-investment-type-checklist',
                    options=[],
                    value=[],
                    style={'marginBottom': '10px', 'maxHeight': '200px', 'overflowY': 'auto', 'fontSize': '12px'},
                    inputStyle={"marginRight": "4px", "accentColor": "#555"},
                    labelStyle={"display": "block", "marginBottom": "2px"}
                ),

            ], style=SIDEBAR_STYLE),
        ], style={'display': 'flex', 'flexDirection': 'row', 'width': '100%'})
    ], style={'backgroundColor': 'white', 'minHeight': '100vh'})


# -----------------------------------------------------------------------------
# CALLBACKS
# -----------------------------------------------------------------------------

def register_callbacks(app, server):
    
    # Chart Hierarchy Callbacks
    @app.callback(
        [Output('lcad-chart-time-level', 'data'),
         Output('lcad-chart-toggle-year-btn', 'children'),
         Output('lcad-chart-toggle-quarter-btn', 'children'),
         Output('lcad-chart-toggle-month-btn', 'children'),
         Output('lcad-chart-toggle-day-btn', 'children')],
        [Input('lcad-chart-toggle-year-btn', 'n_clicks'),
         Input('lcad-chart-toggle-quarter-btn', 'n_clicks'),
         Input('lcad-chart-toggle-month-btn', 'n_clicks'),
         Input('lcad-chart-toggle-day-btn', 'n_clicks'),
         Input('lcad-interval-dropdown', 'value')],
        [State('lcad-chart-time-level', 'data')]
    )
    def chart_hierarchy_handler(y_c, q_c, m_c, d_c, dropdown_val, current_level):
        ctx = callback_context
        if not ctx.triggered:
            cl = current_level or 'YEARLY'
            return (cl, 
                    '-' if cl == 'YEARLY' else '+',
                    '-' if cl == 'QUARTERLY' else '+',
                    '-' if cl == 'MONTHLY' else '+',
                    '-' if cl == 'DAILY' else '+')

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'lcad-interval-dropdown':
            # Dropdown overrides icons: set chart level to match dropdown
            new_level = dropdown_val
        else:
            # Button clicked: only change icon state, don't touch dropdown
            new_level = current_level or 'YEARLY'
            if '-year-btn' in trigger_id:
                new_level = 'YEARLY'
            elif '-quarter-btn' in trigger_id:
                new_level = 'QUARTERLY'
            elif '-month-btn' in trigger_id:
                new_level = 'MONTHLY'
            elif '-day-btn' in trigger_id:
                new_level = 'DAILY'
            
        return (new_level,
                '-' if new_level == 'YEARLY' else '+',
                '-' if new_level == 'QUARTERLY' else '+',
                '-' if new_level == 'MONTHLY' else '+',
                '-' if new_level == 'DAILY' else '+')
    
    # 1. Fetch Data
    @app.callback(
        Output('lcad-data-store', 'data'),
        Output('lcad-status-checklist', 'options'),
        Output('lcad-status-checklist', 'value'),
        Output('lcad-status-prev-store', 'data'),
        Output('lcad-investment-type-checklist', 'options'),
        Output('lcad-investment-type-checklist', 'value'),
        Output('lcad-inv-type-prev-store', 'data'),
        Input('lcad-interval-dropdown', 'value'),
        Input('lcad-chart-time-level', 'data'),
        Input('lcad-breakdown-dropdown', 'value')
    )
    def fetch_data(dropdown_interval, chart_time_level, breakdown):
        # Determine the SQL period based on both inputs
        if dropdown_interval == 'QUARTERLY' or chart_time_level in ['QUARTERLY', 'MONTHLY', 'DAILY']:
            interval = 'QUARTERLY'
        else:
            interval = 'YEARLY'

        if not interval or not breakdown:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update

        engine = get_db_engine()
        
        # Select query
        if breakdown == 'Project Category':
            query_template = QUERY_PROJECT_CATEGORY
        else:
            query_template = QUERY_PEER_GROUP
            
        # Format query
        query = query_template.format(period=interval)
        
        try:
            df = pd.read_sql(query, engine)
            
            # CRITICAL FIX: Ensure numeric columns are floats
            # This prevents potential Decimal vs String issues during JSON serialization/deserialization
            for col in ['investment_count', 'investment_value']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                    
        except Exception as e:
            print(f"Error executing query: {e}")
            return [], [], [], [], [], [], []

        # Prepare filter options (unique values)
        status_vals = sorted(df['Status'].dropna().unique())
        status_options = [{'label': '(All)', 'value': '(All)'}] + [{'label': s, 'value': s} for s in status_vals]
        status_defaults = ['(All)'] + status_vals
        
        inv_type_vals = sorted(df['Investment Type'].dropna().unique())
        inv_type_options = [{'label': '(All)', 'value': '(All)'}] + [{'label': s, 'value': s} for s in inv_type_vals]
        inv_type_defaults = ['(All)'] + inv_type_vals
        
        return df.to_dict('records'), status_options, status_defaults, status_defaults, inv_type_options, inv_type_defaults, inv_type_defaults

    # Helper for "Select All" logic
    def handle_select_all(current_values, previous_values, options):
        if current_values is None: current_values = []
        if previous_values is None: previous_values = []
        
        all_vals = [opt['value'] for opt in options]
        data_vals = [v for v in all_vals if v != '(All)']
        
        # Determine what changed
        added = [v for v in current_values if v not in previous_values]
        removed = [v for v in previous_values if v not in current_values]
        
        new_values = current_values
        
        if '(All)' in added:
            # User explicitly checked "(All)" -> Force-check everything
            new_values = all_vals
        elif '(All)' in removed:
            # User explicitly unchecked "(All)" -> Force-uncheck everything
            new_values = []
        elif removed:
            # User unchecked an individual item while (All) was probably on
            if '(All)' in current_values:
                new_values = [v for v in current_values if v != '(All)']
        elif added:
            # User checked an individual item. If all data items are now checked, add (All)
            if '(All)' not in current_values and all(v in current_values for v in data_vals) and len(data_vals) > 0:
                new_values = all_vals
                
        return new_values, new_values

    @app.callback(
        Output('lcad-status-checklist', 'value', allow_duplicate=True),
        Output('lcad-status-prev-store', 'data', allow_duplicate=True),
        Input('lcad-status-checklist', 'value'),
        State('lcad-status-prev-store', 'data'),
        State('lcad-status-checklist', 'options'),
        prevent_initial_call=True
    )
    def update_status_all(values, prev_values, options):
        return handle_select_all(values, prev_values, options)

    @app.callback(
        Output('lcad-investment-type-checklist', 'value', allow_duplicate=True),
        Output('lcad-inv-type-prev-store', 'data', allow_duplicate=True),
        Input('lcad-investment-type-checklist', 'value'),
        State('lcad-inv-type-prev-store', 'data'),
        State('lcad-investment-type-checklist', 'options'),
        prevent_initial_call=True
    )
    def update_inv_type_all(values, prev_values, options):
        return handle_select_all(values, prev_values, options)

    # 4. Clientside Callback to attach X-Axis Click Listeners
    # Attaches listener to Plotly Axis Labels and updates 'axis-yearly-click-trigger'
    app.clientside_callback(
        """
        function(fig_data) {
            // Wait for plot to render
            setTimeout(function() {
                try {
                    const graph = document.getElementById('lcad-chart');
                    if (!graph) return;
                    
                    // Target the groups 'g.xtick' to catch clicks on the general area
                    const ticks = graph.querySelectorAll('g.xtick');
                    
                    if (ticks.length === 0) return;
                    
                    ticks.forEach(t => {
                        t.style.cursor = 'pointer'; 
                        t.style.pointerEvents = 'all'; 
                        
                        // Prevent attaching multiple times if re-running
                        if (t.getAttribute('data-click-attached')) return;
                        t.setAttribute('data-click-attached', 'true');
                        
                        t.addEventListener('click', function(e) {
                            // Find the text content. It might be in a child 'text' element or 'tspan'
                            const textEl = t.querySelector('text');
                            if (textEl) {
                                let dateStr = textEl.textContent; 
                                // Remove any zero-width spaces or artifacts if present
                                dateStr = dateStr.replace(/[\\u200B\\u00A0]/g, ''); 
                                
                                const input = document.getElementById('lcad-axis-click-trigger');
                                if (input) {
                                    // Timestamp payload to ensure uniqueness
                                    const payload = dateStr + "|" + Date.now();
                                    
                                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                                    nativeInputValueSetter.call(input, payload);
                                    input.dispatchEvent(new Event('input', { bubbles: true }));
                                }
                            }
                        });
                    });
                } catch(e) { console.error("Axis listener error:", e); }
            }, 1000); 
            return window.dash_clientside.no_update;
        }
        """,
        Output('lcad-axis-listener-output', 'children'), # Dedicated output
        Input('lcad-chart', 'figure')
    )

    # 2. Handle Selection (Highlighting)
    @app.callback(
        Output('lcad-selection-store', 'data'),
        Input('lcad-chart', 'clickData'),
        Input('lcad-axis-click-trigger', 'value'),
        State('lcad-selection-store', 'data'),
    )
    def update_selection(clickData, axis_trigger, current_selection):
        ctx = callback_context
        if not ctx.triggered:
            return no_update
            
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        new_selection = None
        
        if trigger_id == 'lcad-axis-click-trigger':
            if not axis_trigger:
                return no_update
            # Format: "Year|Timestamp"
            try:
                clicked_year = axis_trigger.split('|')[0]
                new_selection = {'type': 'period', 'value': clicked_year}
            except:
                return no_update
                
        elif trigger_id == 'lcad-chart':
            if not clickData:
                return no_update
                
            point = clickData['points'][0]
            x_val = str(point['x']) # Ensure string
            
            # Determine click type based on customdata
            try:
                cdata = point['customdata']
                # Check for Totals trace
                if cdata and cdata[0] == 'TOTALS_TRACE':
                    new_selection = {'type': 'period', 'value': x_val}
                else:
                    # Assume Bar trace -> Point selection
                    cat = cdata[0]
                    new_selection = {'type': 'point', 'period': x_val, 'breakdown': cat}
            except (KeyError, IndexError, TypeError):
                return no_update

        # Toggle logic
        # If clicking same thing again -> clear
        if current_selection and isinstance(current_selection, dict):
            # We need to compare carefully.
            # If current is {'type': 'period', 'value': '2019'} and new is same, clear it.
            if new_selection and current_selection.get('type') == new_selection.get('type'):
                if current_selection.get('value') == new_selection.get('value') and \
                   current_selection.get('period') == new_selection.get('period') and \
                   current_selection.get('breakdown') == new_selection.get('breakdown'):
                    return None 
                
        return new_selection

    # 3. Update Chart
    @app.callback(
        Output('lcad-chart', 'figure'),
        Output('lcad-chart-title', 'children'),
        Input('lcad-data-store', 'data'),
        Input('lcad-measure-dropdown', 'value'),
        Input('lcad-status-checklist', 'value'),
        Input('lcad-investment-type-checklist', 'value'),
        Input('lcad-selection-store', 'data'),
        Input('lcad-chart-time-level', 'data'),
        State('lcad-interval-dropdown', 'value'),
        State('lcad-breakdown-dropdown', 'value')
    )
    def update_chart(data, measure, status_filter, inv_type_filter, selection, chart_time_level, interval, breakdown_type):
        try:
            if not data:
                return go.Figure(), "Low-Carbon Investments"
                
            df = pd.DataFrame(data)
            if df.empty:
                 return go.Figure(), "Low-Carbon Investments (No Data)"
            
            # Ensure numeric columns are floats (just in case)
            if measure in df.columns:
                df[measure] = pd.to_numeric(df[measure], errors='coerce').fillna(0.0)

            # Filter by Status
            if status_filter is not None:
                status_to_filter = [s for s in status_filter if s != '(All)']
                df = df[df['Status'].isin(status_to_filter)]
            
            # Filter by Investment Type
            if inv_type_filter is not None:
                inv_type_to_filter = [s for s in inv_type_filter if s != '(All)']
                df = df[df['Investment Type'].isin(inv_type_to_filter)]

            if df.empty:
                 return go.Figure(), f"Low-Carbon Investments (No matches for selected filters)"

            # Construct X-axis column based on chart_time_level and interval
            # dropdown_interval is what's explicitly selected in the sidebar
            # data_interval is what we actually have in the dataframe
            dropdown_interval = interval
            data_interval = 'YEARLY'
            # Enhanced check: columns must exist AND have non-null values
            if 'Quarter of Date' in df.columns and df['Quarter of Date'].notna().any():
                data_interval = 'QUARTERLY'
            
            time_level = chart_time_level or dropdown_interval or 'YEARLY'
            month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            
            # Use data_interval to decide how much detail we can show
            if data_interval == 'YEARLY':
                # Override time_level to YEARLY since we don't have quarterly/monthly data
                time_level = 'YEARLY'
                df['Period'] = df['Year of Date'].astype(str)
            elif data_interval == 'QUARTERLY':
                # We have quarterly data, can display as QUARTERLY, MONTHLY, or DAILY
                if time_level == 'DAILY':
                    # Format: "Jan 1, 2018" (monthly aggregation with day 1)
                    df['Period'] = df.apply(lambda row: f"{month_names[int(row['Month of Date'])]} 1, {int(row['Year of Date'])}" if pd.notna(row.get('Month of Date')) else str(int(row['Year of Date'])), axis=1)
                elif time_level == 'MONTHLY':
                    # Format: "2018 Jan"
                    df['Period'] = df.apply(lambda row: f"{int(row['Year of Date'])} {month_names[int(row['Month of Date'])]}" if pd.notna(row.get('Month of Date')) else str(int(row['Year of Date'])), axis=1)
                else:  # QUARTERLY or YEARLY
                    # Format: "2018 Q1"
                    df['Period'] = df['Year of Date'].astype(str) + ' ' + df['Quarter of Date'].fillna('')
                
            # Group by Period and Breakdown
            # We need to aggregate sum of value and count
            # Also collect Type and Status for tooltip (unique list)
            
            # Helper for unique join
            def unique_join(x):
                return '<br>'.join(sorted(x.astype(str).unique()))
                
            # Pre-group for tooltips
            # Group by [Period, Breakdown], sum metric, join others
            
            agg_dict = {
                 'investment_count': 'sum',
                 'investment_value': 'sum',
                 'Investment Type': unique_join,
                 'Status': unique_join, 
                 'Year of Date': 'first'
            }
            if 'Quarter of Date' in df.columns:
                agg_dict['Quarter of Date'] = 'first'
            if 'Month of Date' in df.columns:
                agg_dict['Month of Date'] = 'first'
            if 'Day of Date' in df.columns:
                agg_dict['Day of Date'] = 'first'
                
            grouped = df.groupby(['Period', 'Breakdown']).agg(agg_dict).reset_index()
            
            # Sorting Periods
            sort_cols = ['Year of Date']
            if time_level == 'DAILY' and 'Month of Date' in grouped.columns and 'Day of Date' in grouped.columns:
                sort_cols.extend(['Month of Date', 'Day of Date'])
            elif time_level == 'MONTHLY' and 'Month of Date' in grouped.columns:
                sort_cols.append('Month of Date')
            elif time_level == 'QUARTERLY' and 'Quarter of Date' in grouped.columns:
                sort_cols.append('Quarter of Date')
            
            grouped.sort_values(by=sort_cols, inplace=True)
                
            periods = grouped['Period'].unique() # Ordered
            
            # Pivot for plotting to ensure stacking alignment
            pivot_val = grouped.pivot(index='Period', columns='Breakdown', values=measure).fillna(0)
            # Reindex to ensure sorted order
            pivot_val = pivot_val.reindex(periods)
            
            # Define custom sort order for visual stacking (Trace order: First Added = Bottom, Last Added = Top)
            if breakdown_type == 'Project Category':
                # Order: [Bottom -> Top]
                custom_order = [
                    'Other', 
                    'L-C Power Generation', 
                    'Hydrogen & L-C Fuels/Gases', 
                    'EVs & Mobility', 
                    'Electricity Solutions', 
                    'CCS & Carbon Removal'
                ]
                unique_cats = grouped['Breakdown'].unique()
                categories = [c for c in custom_order if c in unique_cats]
                categories.extend(sorted([c for c in unique_cats if c not in categories]))
            elif breakdown_type == 'Peer Group':
                # User requested: European Major TOP, US Major BELOW/BOTTOM
                # Order: [Bottom -> Top]
                custom_order = [
                    'US Major',
                    'NOC',
                    'Midstream Firm',
                    'Industrial Gas and Chemicals Manufacturer',
                    'Independent Refiner',
                    'Independent E&P',
                    'European Major'
                ]
                unique_cats = grouped['Breakdown'].unique()
                categories = [c for c in custom_order if c in unique_cats]
                # Filter alphabetical remains for any unexpected peers
                remaining = sorted([c for c in unique_cats if c not in categories])
                # We add remaining to the bottom (before US Major) unless they should be elsewhere
                categories = remaining + categories
            else:
                categories = sorted(grouped['Breakdown'].unique())
            
            # Build Figure
            fig = go.Figure()
            
            # Prepare X-Axis Tikcs with Highlighting
            tick_texts = []
            for p in periods:
                is_selected = False
                if selection and isinstance(selection, dict):
                    # Check if this period is selected (either as a whole column or a point in it)
                    if selection.get('type') == 'period' and selection.get('value') == p:
                         is_selected = True
                    # Optional: Also highlight axis if a point in that year is selected? 
                    # Reference image 2 doesn't show axis highlight for point selection, only Image 1 for Year selection.
                    # Image 1: Year 2019 selected -> Axis 2019 has blue box.
                    # Image 2: Segment selected -> Axis 2022 has NO blue box (it has a black box around bar).
                    # So only highlight axis if type == 'period'.
                
                if is_selected:
                     # Highlight style matching Image 1 (Blue background)
                     # Note: Plotly supports some HTML in tick labels
                     tick_texts.append(f"<span style='font-weight:bold; color:#000000; background-color:#cfe8ef;'>{p}</span>")
                else:
                     tick_texts.append(p)
            
            # Prepare tooltip labels
            suffix_tooltip = " ($ Billion)" if measure == 'investment_value' else ""
            measure_label = measure.replace('_', ' ').title()
            period_label = "Year" if data_interval == "YEARLY" else "Date Announced"
            
            suffix = "($ Billion)" if measure == 'investment_value' else "(#)"
            title = f"Low-Carbon Investments by {breakdown_type} {suffix}"

            # Add bar traces
            for cat in categories:
                # Extract data for this category, aligned to period index
                # Filter grouped
                cat_group = grouped[grouped['Breakdown'] == cat]
                
                # Align to full period list
                cat_group = cat_group.set_index('Period').reindex(periods).reset_index()
                
                # Fill NaNs for values
                y_vals = cat_group[measure].fillna(0)
                
                # Prepare hover text
                hover_visuals = []
                custom_data = [] # [cat, ...]
                
                for idx, row in cat_group.iterrows():
                    val_num = row[measure]
                    if pd.isna(val_num) or val_num == 0:
                        hover_visuals.append("")
                        custom_data.append([cat])
                        continue
                        
                    val_str = f"{val_num:,.1f}" if measure == 'investment_value' else f"{int(val_num)}"
                    
                    # Tooltip content
                    # Format: 
                    # Project Category: Value
                    # Investment Value: Value ($ Billion)
                    # Year: Value
                    
                    # Use spans for coloring: Label (grey), Value (black)
                    tt = (
                        f"<span style='color:gray'>{breakdown_type}: </span><span style='color:black'>{cat}</span><br>" +
                        f"<span style='color:gray'>{measure_label}: </span><span style='color:black'>{val_str}{suffix_tooltip}</span><br>" +
                        f"<span style='color:gray'>{period_label}: </span><span style='color:black'>{row['Period']}</span>"
                    )
                    hover_visuals.append(tt)
                    custom_data.append([cat])

                # Selection / Highlighting Logic
                opacity_list = []
                line_width_list = []
                line_color_list = []
                
                default_opacity = 1.0
                dimmed_opacity = 0.3 # For unselected items
                
                for p in periods:
                    is_highlighted = False
                    is_dimmed = False
                    show_border = False
                    
                    if selection and isinstance(selection, dict):
                        sel_type = selection.get('type')
                        
                        if sel_type == 'period':
                            # Highlight entire column for this period, dim others
                            if p == selection.get('value'):
                                is_highlighted = True
                            else:
                                is_dimmed = True
                                
                        elif sel_type == 'point':
                            # Highlight only the specific segment, dim EVERYTHING else
                            if p == selection.get('period') and cat == selection.get('breakdown'):
                                is_highlighted = True
                                show_border = True
                            else:
                                is_dimmed = True
                    
                    # Apply logic
                    if selection:
                        if is_dimmed:
                            opacity_list.append(dimmed_opacity)
                        else:
                            opacity_list.append(default_opacity)
                    else:
                        opacity_list.append(default_opacity)
                        
                    if show_border:
                        line_width_list.append(2)
                        line_color_list.append('black')
                    else:
                        line_width_list.append(0)
                        line_color_list.append('rgba(0,0,0,0)')
                
                # Color
                color = COLOR_PALETTE.get(cat, None)

                fig.add_trace(go.Bar(
                    name=cat,
                    x=periods,
                    y=y_vals,
                    text=hover_visuals,
                    hovertemplate="%{text}<extra></extra>",
                    textposition="none",
                    marker_color=color,
                    marker_opacity=opacity_list,
                    marker_line=dict(width=line_width_list, color=line_color_list),
                    customdata=custom_data
                ))
                
            # Add Total Labels (Scatter trace)
            # Calculate totals per period
            period_totals = pivot_val.sum(axis=1)
            
            # 1. Add Trend Line (FIRST, behind labels)
            if data_interval in ['QUARTERLY', 'MONTHLY', 'DAILY']:
                fig.add_trace(go.Scatter(
                    name='Total Trend',
                    x=period_totals.index,
                    y=period_totals.values,
                    mode='lines',
                    line=dict(color='#FF5A09', width=2),
                    hovertemplate=(
                        f"<span style='color:gray'>Date Announced: </span><span style='color:black'>%{{x}}</span>" +
                        "<extra></extra>"
                    ),
                    showlegend=False, 
                    yaxis='y', 
                    hoverlabel=dict(bgcolor='white', font=dict(color='black'))
                ))

            # 2. Add Total Labels (Scatter trace, on TOP)
            fig.add_trace(go.Scatter(
                x=period_totals.index,
                y=period_totals.values,
                text=[f"<b>{v:,.1f}</b>" if measure == 'investment_value' else f"<b>{int(v)}</b>" for v in period_totals.values],
                mode='text',
                textposition='top center',
                textfont=dict(size=11, color='black'),
                showlegend=False,
                hoverinfo='skip',
                cliponaxis=False,
                customdata=[['TOTALS_TRACE']] * len(period_totals)
            ))

            # Y-Axis Settings based on Measure and Interval
            # Increase range slightly to account for trend line and total labels
            if measure == 'investment_value':
                if data_interval == 'QUARTERLY':
                    y_dtick = 5
                    max_total = period_totals.max() if not period_totals.empty else 40
                    y_range = [0, max(40, max_total * 1.2)]
                else:
                    y_dtick = 20
                    max_total = period_totals.max() if not period_totals.empty else 150
                    y_range = [0, max(150, max_total * 1.2)]
            else: # investment_count
                if data_interval == 'QUARTERLY':
                    y_dtick = 20
                    max_total = period_totals.max() if not period_totals.empty else 160
                    y_range = [0, max(160, max_total * 1.2)]
                else:
                    y_dtick = 50
                    max_total = period_totals.max() if not period_totals.empty else 600
                    y_range = [0, max(600, max_total * 1.2)]

            # Layout styling
            fig.update_layout(
                barmode='stack',
                plot_bgcolor='white',
                paper_bgcolor='white',
                hoverlabel=dict(
                    bgcolor="white",
                    font_family="Lato, sans-serif"
                ),
                legend=dict(
                    orientation='v',
                    yanchor="top",
                    y=1.0,
                    xanchor="left",
                    x=0.02, # Inside chart top left
                    bgcolor="rgba(255,255,255,0.8)",
                    bordercolor="lightgrey",
                    borderwidth=0,
                    traceorder='reversed'
                ),
                xaxis=dict(
                    tickfont=dict(size=12, family='Arial'),
                    linecolor='lightgrey',
                    type='category', # Ensure periods are treated as categorical chunks
                    tickmode='array',
                    tickvals=periods,
                    ticktext=tick_texts
                ),
                yaxis=dict(
                    title=measure.replace('_', ' ').title(),
                    showgrid=False,
                    gridcolor='#eeeeee',
                    zeroline=True,
                    zerolinecolor='#eee',
                    side='left',
                    tickmode='linear',
                    tick0=0,
                    dtick=y_dtick,
                    range=y_range
                ),
                yaxis2=dict(
                    title='Count',
                    overlaying='y',
                    side='right',
                    showgrid=False,
                    showticklabels=False, 
                    rangemode='tozero'
                ),
                margin=dict(l=60, r=20, t=10, b=80),
                font=dict(family="Lato, sans-serif")
            )

            return fig, title
            
        except Exception as e:
            # Fallback in case of error
            import traceback
            traceback.print_exc()
            return go.Figure(), f"Error updating chart: {str(e)}"
    # CSV Export Callbacks
    @app.callback(
        Output("download-lcad-chart-csv", "data"),
        Input("export-lcad-chart-btn", 'n_clicks'),
        [State('lcad-data-store', 'data'),
         State('lcad-measure-dropdown', 'value'),
         State('lcad-status-checklist', 'value'),
         State('lcad-investment-type-checklist', 'value'),
         State('lcad-interval-dropdown', 'value'),
         State('lcad-breakdown-dropdown', 'value')],
        prevent_initial_call=True
    )
    def export_chart_data(n_clicks, data, measure, status_filter, inv_type_filter, interval, breakdown):
        if not n_clicks or not data:
            return no_update

        try:
            df = pd.DataFrame(data)
            
            if df.empty:
                return no_update

            # Apply filters
            if status_filter:
                status_to_filter = [s for s in status_filter if s != '(All)']
                df = df[df['Status'].isin(status_to_filter)]
            
            if inv_type_filter:
                inv_type_to_filter = [s for s in inv_type_filter if s != '(All)']
                df = df[df['Investment Type'].isin(inv_type_to_filter)]

            if df.empty:
                return no_update
            
            # Remove internal tracking columns for cleaner CSV
            cols_to_drop = ['Year of Date', 'Quarter of Date', 'Month of Date', 'Day of Date']
            df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
            
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"low_carbon_investments_chart_{timestamp}.csv"
            
            return dcc.send_data_frame(df.to_csv, filename, index=False)

        except Exception as e:
            print(f"Error exporting chart data: {e}")
            return no_update
