"""
European Gas Trade - Pipeline Flows to Europe
Pipeline flow analytics for European gas trade
"""
from dash import dcc, html, Input, Output, callback, State, dash_table, clientside_callback, ClientsideFunction, no_update
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from core.data_helpers import execute_query


# Color Palette
EI_ORANGE = "#ff6600"
EI_DARK_BLUE = "#1b365d"
EI_LIGHT_BLUE = "#e8f4f8"

# Color mapping for Gas Origin (from Fig 2)
GAS_ORIGIN_COLORS = {
    'Russia': '#c38b7d',
    'Norway': '#6f839d',
    'Algeria': '#acafcf',
    'Azerbaijan': '#cbdcb6',
    'Libya': '#dadbb1'
}

def create_layout():
    """Create the European Pipeline Flows layout"""
    return html.Div([
        # Selection stores
        dcc.Store(id='gas-flows-period-store', data='DAILY'),
        dcc.Store(id='gas-flows-table-selection-store', data={'selected_column_id': None}),

        # Main container with Flexbox for Sidebar and Content
        html.Div([
            
            # Sidebar Filter (Right side as per Fig 1)
            html.Div([
                html.Div([
                    html.Label("Start Date", style={'fontSize': '11px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE}),
                    dcc.Input(
                        id='gas-flows-start-date',
                        type='date',
                        value='2021-01-01',
                        style={
                            'width': '100%', 
                            'marginBottom': '15px',
                            'height': '28px',
                            'fontSize': '11px',
                            'fontFamily': 'Inter, sans-serif',
                            'border': '1px solid #ccc',
                            'borderRadius': '4px',
                            'padding': '0 5px',
                            'color': '#333'
                        }
                    ),
                    
                    html.Label("End Date", style={'fontSize': '11px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE}),
                    dcc.Input(
                        id='gas-flows-end-date',
                        type='date',
                        value='2026-01-09',
                        style={
                            'width': '100%', 
                            'marginBottom': '20px',
                            'height': '28px',
                            'fontSize': '11px',
                            'fontFamily': 'Inter, sans-serif',
                            'border': '1px solid #ccc',
                            'borderRadius': '4px',
                            'padding': '0 5px',
                            'color': '#333'
                        }
                    ),
                    
                    html.Div([
                        html.Span("Gas Origin", style={'fontSize': '11px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE}),
                        html.I(className="fas fa-search", style={'fontSize': '10px', 'color': '#999', 'marginLeft': '5px'})
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px'}),
                    
                    dcc.Checklist(
                        id='gas-origin-checklist',
                        options=[
                            {'label': ' Algeria', 'value': 'Algeria'},
                            {'label': ' Azerbaijan', 'value': 'Azerbaijan'},
                            {'label': ' Libya', 'value': 'Libya'},
                            {'label': ' Norway', 'value': 'Norway'},
                            {'label': ' Russia', 'value': 'Russia'}
                        ],
                        value=['Algeria', 'Azerbaijan', 'Libya', 'Norway', 'Russia'],
                        style={'fontSize': '11px', 'color': '#333', 'padding': '5px', 'border': '1px solid #ddd', 'backgroundColor': 'white', 'maxHeight': '150px', 'overflowY': 'auto'},
                        labelStyle={'display': 'block', 'marginBottom': '5px', 'paddingLeft': '5px'}
                    ),
                    
                    # Legend as per Fig 2
                    html.Div([
                        html.Label("Gas Origin", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE, 'marginTop': '20px', 'display': 'block'}),
                        html.Div([
                            html.Div([
                                html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': GAS_ORIGIN_COLORS['Russia'], 'marginRight': '8px'}),
                                html.Span("Russia", style={'fontSize': '11px', 'color': '#666'})
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '4px'}),
                            html.Div([
                                html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': GAS_ORIGIN_COLORS['Norway'], 'marginRight': '8px'}),
                                html.Span("Norway", style={'fontSize': '11px', 'color': '#666'})
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '4px'}),
                            html.Div([
                                html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': GAS_ORIGIN_COLORS['Algeria'], 'marginRight': '8px'}),
                                html.Span("Algeria", style={'fontSize': '11px', 'color': '#666'})
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '4px'}),
                            html.Div([
                                html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': GAS_ORIGIN_COLORS['Azerbaijan'], 'marginRight': '8px'}),
                                html.Span("Azerbaijan", style={'fontSize': '11px', 'color': '#666'})
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '4px'}),
                            html.Div([
                                html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': GAS_ORIGIN_COLORS['Libya'], 'marginRight': '8px'}),
                                html.Span("Libya", style={'fontSize': '11px', 'color': '#666'})
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '4px'}),
                        ])
                    ])
                ], style={'padding': '15px', 'backgroundColor': '#fcfcfc', 'border': '1px solid #eee', 'height': '100%'})
            ], style={'width': '200px', 'order': '2', 'marginLeft': '15px'}),
            
            # Content Area (Left side)
            html.Div([
                # Chart Section with title and export button
                html.Div([
                    html.H3("Gas Pipeline Flows to Europe-Billion Cubic Meters", style={
                        'color': EI_ORANGE,
                        'fontSize': '20px',
                        'fontWeight': 'bold',
                        'margin': '0 0 10px 0',
                        'fontFamily': 'Inter, sans-serif'
                    }),
                    html.Button(
                        "Export to CSV",
                        id="export-gas-flows-chart-btn",
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
                
                # Period Selector (as per Fig 1)
                html.Div([
                    html.Div([
                        html.Span("Year of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                        html.Button('+', id='gas-flows-toggle-year-btn', n_clicks=0, style={
                            'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                            'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                            'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                        })
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                    
                    html.Div([
                        html.Span("Quarter of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                        html.Button('+', id='gas-flows-toggle-quarter-btn', n_clicks=0, style={
                            'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                            'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                            'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                        })
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                    
                    html.Div([
                        html.Span("Month of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                        html.Button('+', id='gas-flows-toggle-month-btn', n_clicks=0, style={
                            'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                            'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                            'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                        })
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),

                    html.Div([
                        html.Span("Week of Year", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                        html.Button('+', id='gas-flows-toggle-week-btn', n_clicks=0, style={
                            'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                            'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                            'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                        })
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
                    
                    html.Div([
                        html.Span("Day of Year", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
                        html.Button('-', id='gas-flows-toggle-day-btn', n_clicks=0, style={
                            'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                            'backgroundColor': 'white', 'color': '#add8e6', 'borderRadius': '3px', 'cursor': 'pointer',
                            'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
                        })
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], style={
                    'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#f8f9fa', 
                    'padding': '5px 10px', 'borderRadius': '4px', 'marginBottom': '10px',
                    'width': 'fit-content'
                }),
                
                dcc.Loading(
                    id='loading-gas-flows-chart',
                    type='circle',
                    color=EI_ORANGE,
                    children=dcc.Graph(
                        id='gas-flows-wave-chart',
                        style={'height': '500px'},
                        config={'displayModeBar': False}
                    )
                ),
                
                # Table Area with header and export button
                html.Div([
                    # Table header with export button
                    html.Div([
                        html.H4("Pipeline Flow Details", style={
                            'color': EI_DARK_BLUE,
                            'fontSize': '16px',
                            'fontWeight': 'bold',
                            'margin': '0',
                            'fontFamily': 'Inter, sans-serif'
                        }),
                        html.Button(
                            "Export to CSV",
                            id="export-gas-flows-table-btn",
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
                        id='loading-gas-flows-table',
                        type='circle',
                        color=EI_ORANGE,
                        children=html.Div(id='gas-flows-table-container')
                    )
                ], style={'marginTop': '20px'}),
                
                # Hidden div for clientside callback anchor
                html.Div(id='gas-flows-table-enhancer-anchor', style={'display': 'none'}),
                
                # Download components
                dcc.Download(id="download-gas-flows-chart-csv"),
                dcc.Download(id="download-gas-flows-table-csv")
            ], style={'flex': '1', 'order': '1', 'minWidth': '0', 'overflow': 'hidden'})
            
        ], style={'display': 'flex', 'padding': '15px'})
    ], className='tab-content', style={'backgroundColor': 'white', 'maxWidth': '1400px', 'margin': '0 auto'})


def register_callbacks(dash_app, server):
    """Register all callbacks for European Pipeline Flows"""
    
    # Clientside callback for table highlighting
    dash_app.clientside_callback(
        """
        function(id) {
            const tableId = 'gas-flows-data-table';
            const baseStyleId = 'gas-flows-table-base-css';
            const dynamicStyleId = 'gas-flows-table-dynamic-highlight-css';
            
            // 1. Inject Base CSS if not present
            if (!document.getElementById(baseStyleId)) {
                const style = document.createElement('style');
                style.id = baseStyleId;
                style.innerHTML = `
                    #${tableId} .dash-spreadsheet-container {
                        cursor: pointer;
                    }
                    #${tableId} .dash-spreadsheet-container td {
                        transition: all 0.2s ease;
                    }
                    /* Base selection state: dim normal data cells */
                    #${tableId} .dash-spreadsheet-container.selection-active td {
                        color: #ccc !important;
                        background-color: transparent !important;
                    }
                    /* Keep Day of Date column clear and undimmed */
                    #${tableId} .dash-spreadsheet-container.selection-active td[data-dash-column="Day of Date"] {
                        color: #666 !important;
                        opacity: 1 !important;
                    }
                    /* Highlight for selected column header */
                    #${tableId} .dash-spreadsheet-container th.column-header-selected {
                        background-color: #0075A8 !important;
                        color: white !important;
                    }
                `;
                document.head.appendChild(style);
            }
            
            // 2. Set up click listener on the table
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
                    
                    if (columnId === 'Day of Date' && !rowIndex) return;
                    
                    const isHeader = !!header;
                    const headerRow = isHeader ? header.closest('tr') : null;
                    const thead = isHeader ? header.closest('thead') : null;
                    const headerRows = thead ? Array.from(thead.querySelectorAll('tr')) : [];
                    const headerIndex = headerRow ? headerRows.indexOf(headerRow) : -1;
                    
                    // Toggle logic
                    const selectionKey = isHeader ? (columnId + '_' + headerIndex) : (columnId + '_' + rowIndex);
                    if (container.dataset.lastSelection === selectionKey) {
                        container.dataset.lastSelection = '';
                        container.classList.remove('selection-active');
                        container.querySelectorAll('.column-header-selected').forEach(el => el.classList.remove('column-header-selected'));
                        const dynStyle = document.getElementById(dynamicStyleId);
                        if (dynStyle) dynStyle.remove();
                        return;
                    }
                    container.dataset.lastSelection = selectionKey;
                    
                    // Clear existing header highlights
                    container.querySelectorAll('.column-header-selected').forEach(el => el.classList.remove('column-header-selected'));
                    
                    // Apply highlighting
                    container.classList.add('selection-active');
                    
                    let targetColumnIds = [columnId];
                    let highlightRow = rowIndex;
                    
                    // Discovery logic for child columns if a parent header is clicked
                    if (isHeader) {
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
                    }
                    
                    // Generate Dynamic CSS for high contrast highlights
                    let dynamicStyles = '';
                    
                    // 1. Column(s) Highlighting
                    targetColumnIds.forEach(id => {
                        dynamicStyles += `
                            #${tableId} .dash-spreadsheet-container td[data-dash-column="${id}"] {
                                background-color: #e1f0ff !important;
                                color: #1b365d !important;
                                font-weight: 600 !important;
                            }
                        `;
                    });
                    
                    // 2. Row Highlighting
                    if (highlightRow !== null) {
                        dynamicStyles += `
                            #${tableId} .dash-spreadsheet-container tr:has(td[data-dash-row="${highlightRow}"]) td {
                                background-color: #e1f0ff !important;
                                color: #1b365d !important;
                                font-weight: 600 !important;
                            }
                        `;
                        // 3. Active Cell with intense border and background
                        dynamicStyles += `
                            #${tableId} .dash-spreadsheet-container td[data-dash-column="${columnId}"][data-dash-row="${highlightRow}"] {
                                border: 2px solid #fe5000 !important;
                                border-radius: 2px;
                                z-index: 10 !important;
                                position: relative;
                            }
                            /* Special highlight for the Day of Date cell in the selected row */
                            #${tableId} .dash-spreadsheet-container td[data-dash-column="Day of Date"][data-dash-row="${highlightRow}"] {
                                background-color: #b3d9ff !important;
                                color: #1b365d !important;
                                font-weight: bold !important;
                            }
                        `;
                    }
                    
                    let dynStyle = document.getElementById(dynamicStyleId);
                    if (!dynStyle) {
                        dynStyle = document.createElement('style');
                        dynStyle.id = dynamicStyleId;
                        document.head.appendChild(dynStyle);
                    }
                    dynStyle.innerHTML = dynamicStyles;
                });
            };
            
            setupListener();
            if (!window._gasFlowsTableInterval) {
                window._gasFlowsTableInterval = setInterval(setupListener, 1000);
            }
            
            return null;
        }
        """,
        Output('gas-flows-table-enhancer-anchor', 'children'),
        Input('gas-flows-table-enhancer-anchor', 'id')
    )

    @dash_app.callback(
        [Output('gas-flows-period-store', 'data'),
         Output('gas-flows-toggle-year-btn', 'children'),
         Output('gas-flows-toggle-quarter-btn', 'children'),
         Output('gas-flows-toggle-month-btn', 'children'),
         Output('gas-flows-toggle-week-btn', 'children'),
         Output('gas-flows-toggle-day-btn', 'children')],
        [Input('gas-flows-toggle-year-btn', 'n_clicks'),
         Input('gas-flows-toggle-quarter-btn', 'n_clicks'),
         Input('gas-flows-toggle-month-btn', 'n_clicks'),
         Input('gas-flows-toggle-week-btn', 'n_clicks'),
         Input('gas-flows-toggle-day-btn', 'n_clicks')],
        [State('gas-flows-period-store', 'data')]
    )
    def toggle_gas_flows_period(y_clicks, q_clicks, m_clicks, w_clicks, d_clicks, current_period):
        from dash import callback_context
        ctx = callback_context
        if not ctx.triggered:
            return current_period, '+', '+', '+', '+', '-'
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        new_period = current_period
        if button_id == 'gas-flows-toggle-year-btn':
            new_period = 'YEARLY'
        elif button_id == 'gas-flows-toggle-quarter-btn':
            new_period = 'QUARTERLY'
        elif button_id == 'gas-flows-toggle-month-btn':
            new_period = 'MONTHLY'
        elif button_id == 'gas-flows-toggle-week-btn':
            new_period = 'WEEKLY'
        elif button_id == 'gas-flows-toggle-day-btn':
            new_period = 'DAILY'
            
        return (
            new_period,
            '-' if new_period == 'YEARLY' else '+',
            '-' if new_period == 'QUARTERLY' else '+',
            '-' if new_period == 'MONTHLY' else '+',
            '-' if new_period == 'WEEKLY' else '+',
            '-' if new_period == 'DAILY' else '+'
        )
    
    @dash_app.callback(
        Output('gas-flows-wave-chart', 'figure'),
        [Input('gas-flows-start-date', 'value'),
         Input('gas-flows-end-date', 'value'),
         Input('gas-origin-checklist', 'value'),
         Input('gas-flows-period-store', 'data')]
    )
    def update_gas_flows_chart(start_date, end_date, selected_origins, period):
        if not selected_origins:
            return go.Figure()
            
        # We need to include 'Turkey' if 'Azerbaijan' is selected
        query_origins = selected_origins.copy()
        if 'Azerbaijan' in selected_origins and 'Turkey' not in query_origins:
            query_origins.append('Turkey')

        # Map UI period to SQL period
        sql_period = {
            'DAILY': 'DAILY',
            'WEEKLY': 'WEEKLY',
            'MONTHLY': 'MONTHLY',
            'QUARTERLY': 'QUARTERLY',
            'YEARLY': 'YEARLY'
        }.get(period, 'DAILY')

        query = f"""
        WITH base AS (
            SELECT
                tr.date,
                tr.source_country AS gas_origin,
                tr.point_label,
                tr.value / 1000.0 AS flows_bcm
            FROM glng_gas_trade tr
            LEFT JOIN dim_country co
                ON co.dim_country_id = tr.target_country_id
            WHERE tr.flow_type = 'natural gas'
              AND tr.unit = 'Mcm'
              AND co.region = 'Europe'
              AND tr.source_country = ANY(:origins)
              AND tr.date >= :start_date
              AND tr.date <= :end_date
        )
        -- DAILY
        SELECT
            'DAILY' AS period,
            TO_CHAR(date, 'Month DD, YYYY') AS period_of_date,
            gas_origin,
            point_label,
            date AS date,
            flows_bcm
        FROM base
        WHERE :period = 'DAILY'

        UNION ALL

        -- WEEKLY
        SELECT
            'WEEKLY' AS period,
            TO_CHAR((date_trunc('week', date + interval '1 day') - interval '1 day')::date, 'Month DD, YYYY') AS period_of_date,
            gas_origin,
            point_label,
            (date_trunc('week', date + interval '1 day') - interval '1 day')::date AS date,
            SUM(flows_bcm) AS flows_bcm
        FROM base
        WHERE :period = 'WEEKLY'
        GROUP BY gas_origin, point_label, 5

        UNION ALL

        -- MONTHLY
        SELECT
            'MONTHLY' AS period,
            TO_CHAR(date_trunc('month', date), 'Month YYYY') AS period_of_date,
            gas_origin,
            point_label,
            date_trunc('month', date)::date AS date,
            SUM(flows_bcm) AS flows_bcm
        FROM base
        WHERE :period = 'MONTHLY'
        GROUP BY gas_origin, point_label, date_trunc('month', date)

        UNION ALL

        -- QUARTERLY
        SELECT
            'QUARTERLY' AS period,
            EXTRACT(YEAR FROM date)::text || ' Q' || EXTRACT(QUARTER FROM date)::text AS period_of_date,
            gas_origin,
            point_label,
            date_trunc('quarter', date)::date AS date,
            SUM(flows_bcm) AS flows_bcm
        FROM base
        WHERE :period = 'QUARTERLY'
        GROUP BY gas_origin, point_label, EXTRACT(YEAR FROM date), EXTRACT(QUARTER FROM date), date_trunc('quarter', date)

        UNION ALL

        -- YEARLY
        SELECT
            'YEARLY' AS period,
            EXTRACT(YEAR FROM date)::text AS period_of_date,
            gas_origin,
            point_label,
            date_trunc('year', date)::date AS date,
            SUM(flows_bcm) AS flows_bcm
        FROM base
        WHERE :period = 'YEARLY'
        GROUP BY gas_origin, point_label, EXTRACT(YEAR FROM date), date_trunc('year', date)

        ORDER BY date;
        """
        
        try:
            results = execute_query(query, {
                'start_date': start_date,
                'end_date': end_date,
                'origins': query_origins,
                'period': sql_period
            })
            
            df = pd.DataFrame(results)
            if df.empty:
                return go.Figure()

            # Convert types
            df['flows_bcm'] = pd.to_numeric(df['flows_bcm'], errors='coerce').fillna(0).astype(float)
            df['date'] = pd.to_datetime(df['date'])
            
            # Mapping for Azerbaijan
            aze_points = ['Kipi', 'Nea Mesimvria', 'Strandzha 2', 'Malkoclar']
            mask_aze = (df['gas_origin'] == 'Turkey') & (df['point_label'].str.contains('|'.join(aze_points), na=False, case=False))
            df.loc[mask_aze, 'gas_origin'] = 'Azerbaijan'
            
            if 'Turkey' not in selected_origins:
                df = df[df['gas_origin'] != 'Turkey']
            
            # Aggregation
            df = df.groupby(['date', 'gas_origin', 'period_of_date'])['flows_bcm'].sum().reset_index()
            
            # RESAMPLING: For DAILY ONLY, handle Russia monthly granularity in 2025+
            if period == 'DAILY':
                final_dfs = []
                for origin in df['gas_origin'].unique():
                    origin_df = df[df['gas_origin'] == origin].sort_values('date')
                    future_data = origin_df[origin_df['date'] >= '2025-01-01']
                    if not future_data.empty and all(future_data['date'].dt.day == 1):
                        new_rows = []
                        for _, row in future_data.iterrows():
                            days_in_month = row['date'].days_in_month
                            daily_vol = row['flows_bcm'] / days_in_month
                            for d in range(days_in_month):
                                new_date = row['date'] + pd.Timedelta(days=d)
                                if new_date <= pd.to_datetime(end_date):
                                    new_rows.append({
                                        'date': new_date, 
                                        'gas_origin': origin, 
                                        'flows_bcm': daily_vol,
                                        'period_of_date': new_date.strftime('%B %d, %Y')
                                    })
                        pre_2025 = origin_df[origin_df['date'] < '2025-01-01']
                        origin_df = pd.concat([pre_2025, pd.DataFrame(new_rows)])
                    final_dfs.append(origin_df)
                if final_dfs:
                    df = pd.concat(final_dfs).sort_values(['date', 'gas_origin'])
            
            # Consistency in ordering
            origin_order = ['Libya', 'Azerbaijan', 'Algeria', 'Norway', 'Russia']
            all_origins_present = [o for o in origin_order if o in selected_origins]
            
            fig = go.Figure()
            
            for origin in all_origins_present:
                origin_df = df[df['gas_origin'] == origin].sort_values('date')
                if not origin_df.empty:
                    fig.add_trace(go.Scatter(
                        x=origin_df['date'],
                        y=origin_df['flows_bcm'],
                        name=origin,
                        stackgroup='one', 
                        mode='lines',
                        line=dict(width=0.8, color='rgba(255,255,255,0.2)'),
                        fillcolor=GAS_ORIGIN_COLORS.get(origin, '#ddd'),
                        hoveron='points+fills',
                        customdata=origin_df['period_of_date'],
                        hovertemplate=(
                            "Gas Origin: <b>%{fullData.name}</b><br>" +
                            "Period: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>%{customdata}</b><br>" +
                            "flows_bcm: <b>%{y:.4f}</b><extra></extra>"
                        )
                    ))

            # Annotations
            if 'Russia' in selected_origins:
                fig.add_annotation(x='2022-02-01', y=0.68, text="Russia", showarrow=False, font=dict(family="Inter, sans-serif", size=10, color="#333"))
            if 'Norway' in selected_origins:
                fig.add_annotation(x='2024-03-01', y=0.48, text="Norway", showarrow=False, font=dict(family="Inter, sans-serif", size=10, color="#f0f0f0"))
            if 'Algeria' in selected_origins:
                fig.add_annotation(x='2025-06-01', y=0.08, text="Algeria", showarrow=False, font=dict(family="Inter, sans-serif", size=10, color="#333"))

            # Responsive axis config
            xaxis_config = dict(
                showgrid=True,
                gridcolor='#f5f5f5',
                tickfont=dict(size=10, color='#999'),
                fixedrange=True,
                range=[start_date, end_date]
            )
            
            if period == 'DAILY':
                xaxis_config.update(dtick="M4", tickformat="%d-%b-%y")
            elif period == 'WEEKLY':
                # Exact 26 weeks to match Sundays in Fig 1
                xaxis_config.update(dtick=26 * 7 * 86400000, tickformat="%b %d, %y")
            elif period == 'MONTHLY':
                xaxis_config.update(dtick="M6", tickformat="%b-%y")
            elif period == 'QUARTERLY':
                xaxis_config.update(dtick="M12", tickformat="%Y")
            elif period == 'YEARLY':
                xaxis_config.update(dtick="M24", tickformat="%Y")

            fig.update_layout(
                margin=dict(l=40, r=20, t=10, b=40),
                paper_bgcolor='white',
                plot_bgcolor='white',
                hovermode='closest', 
                showlegend=False,    
                xaxis=xaxis_config,
                yaxis=dict(
                    showgrid=True,
                    gridcolor='#f5f5f5',
                    tickfont=dict(size=10, color='#999'),
                    dtick=1.0 if period == 'WEEKLY' else (0.05 if len(selected_origins) == 1 else 0.1),
                    fixedrange=True,
                    zeroline=True,
                    zerolinecolor='#f5f5f5',
                    range=[0, max(df['flows_bcm'].max() * 1.2 if not df.empty else 1.0, 1.0)]
                ),
                font=dict(family="Inter, sans-serif")
            )
            
            return fig
            
        except Exception as e:
            print(f"Error updating gas flows chart: {e}")
            import traceback
            traceback.print_exc()
            return go.Figure()

    @dash_app.callback(
        Output('gas-flows-table-container', 'children'),
        [Input('gas-flows-start-date', 'value'),
         Input('gas-flows-end-date', 'value'),
         Input('gas-origin-checklist', 'value')]
    )
    def update_gas_flows_table(start_date, end_date, selected_origins):
        if not selected_origins:
            return html.Div("Please select at least one gas origin.", style={'color': '#666', 'fontSize': '12px', 'padding': '20px'})

        query_origins = selected_origins.copy()
        if 'Azerbaijan' in selected_origins and 'Turkey' not in query_origins:
            query_origins.append('Turkey')

        query = f"""
        SELECT
            tr.date AS "Day of Date",
            'Exporter' AS "Header_Exporter",
            tr.source_country AS gas_origin,
            'Importer' AS "Header_Importer",
            tr.target_country AS target_country,
            tr.pointlabel AS "Interconnection Point",
            tr."flow_mcm/d" / 1000.0 AS flows_bcm
        FROM european_gas_trade tr
        WHERE tr.source_country IN ('Algeria','Azerbaijan','Libya','Norway','Russia')
        AND tr.date >= :start_date
        AND tr.date <= :end_date
        ORDER BY tr.date DESC;
        """

        try:
            results = execute_query(query, {
                'start_date': start_date,
                'end_date': end_date,
                # 'origins': query_origins
            })
            df = pd.DataFrame(results)
            if df.empty:
                return html.Div("No data available for the selected filters.", style={'color': '#666', 'fontSize': '12px', 'padding': '20px'})

            # Convert types
            df['flows_bcm'] = pd.to_numeric(df['flows_bcm'], errors='coerce').fillna(0)
            df['Day of Date'] = pd.to_datetime(df['Day of Date'])

            # Mapping for Azerbaijan
            aze_points = ['Kipi', 'Nea Mesimvria', 'Strandzha 2', 'Malkoclar']
            mask_aze = (df['gas_origin'] == 'Turkey') & (df['Interconnection Point'].str.contains('|'.join(aze_points), na=False, case=False))
            df.loc[mask_aze, 'gas_origin'] = 'Azerbaijan'
            
            if 'Turkey' not in selected_origins:
                df = df[df['gas_origin'] != 'Turkey']

            # Aggregate
            df = df.groupby(['Day of Date', 'gas_origin', 'target_country', 'Interconnection Point'])['flows_bcm'].sum().reset_index()

            # Pivot
            pivot_df = df.pivot_table(
                index='Day of Date',
                columns=['gas_origin', 'target_country', 'Interconnection Point'],
                values='flows_bcm'
            ).reset_index()
            
            # Sort by date descending
            pivot_df = pivot_df.sort_values(pivot_df.columns[0], ascending=False)

            # Sort origins
            origin_order = ['Algeria', 'Azerbaijan', 'Libya', 'Norway', 'Russia']
            
            def sort_columns_key(col):
                if col[0] == 'Day of Date':
                    return (-1, "")
                origin = col[0]
                order = origin_order.index(origin) if origin in origin_order else 99
                return (order, str(col[2]))

            # Determine the actual column name for the date (could be a string or a tuple)
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
            # Convert date to string after sorting but before iteration to avoid index issues
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

            return dash_table.DataTable(
                id='gas-flows-data-table',
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
                style_data_conditional=[
                    {
                        'if': {'column_id': 'Day of Date'},
                        'textAlign': 'left',
                        'fontWeight': 'normal',
                        'color': '#666',
                        'minWidth': '180px',
                        'borderRight': '1px solid #dee2e6'
                    },
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#f8f9fa'
                    },
                    {
                        'if': {'state': 'active'},
                        'backgroundColor': '#fdeedc',
                        'border': '1px solid #fe5000'
                    },
                    {
                        'if': {'state': 'selected'},
                        'backgroundColor': '#e1f0ff',
                        'border': '1px solid #3390ff'
                    }
                ],
                style_header_conditional=[
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
                ],
                fixed_rows={'headers': True},
                virtualization=True
            )

        except Exception as e:
            print(f"Error updating gas flows table: {e}")
            import traceback
            traceback.print_exc()
            return html.Div(f"Error loading table: {str(e)}", style={'color': 'red'})

    # CSV Export Callbacks
    @dash_app.callback(
        Output("download-gas-flows-chart-csv", "data"),
        Input("export-gas-flows-chart-btn", "n_clicks"),
        [State('gas-flows-start-date', 'value'),
         State('gas-flows-end-date', 'value'),
         State('gas-origin-checklist', 'value')],
        prevent_initial_call=True,
    )
    def export_chart_data(n_clicks, start_date, end_date, selected_origins):
        """Export chart data to CSV."""
        if n_clicks == 0:
            return no_update
            
        try:
            if not selected_origins:
                return no_update
                
            # Use same query logic as the chart
            query_origins = selected_origins.copy()
            if 'Azerbaijan' in selected_origins and 'Turkey' not in query_origins:
                query_origins.append('Turkey')

            query = f"""
            SELECT
                tr.source_country AS gas_origin,
                tr.point_label,
                tr.date AS date,
                tr.value / 1000.0 AS flows_bcm
            FROM glng_gas_trade tr
            LEFT JOIN dim_country co
                ON co.dim_country_id = tr.target_country_id
            WHERE tr.flow_type = 'natural gas'
              AND tr.date >= :start_date
              AND tr.date <= :end_date
              AND tr.unit = 'Mcm'
              AND co.region = 'Europe'
              AND tr.source_country = ANY(:origins)
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
            
            # Azerbaijan mapping
            aze_points = ['Kipi', 'Nea Mesimvria', 'Strandzha 2', 'Malkoclar']
            mask_aze = (df['gas_origin'] == 'Turkey') & (df['point_label'].str.contains('|'.join(aze_points), na=False, case=False))
            df.loc[mask_aze, 'gas_origin'] = 'Azerbaijan'
            
            if 'Turkey' not in selected_origins:
                df = df[df['gas_origin'] != 'Turkey']
            
            # Aggregate by date and origin
            df = df.groupby(['date', 'gas_origin'])['flows_bcm'].sum().reset_index()
            
            # Prepare export data
            export_df = df.sort_values(['date', 'gas_origin']).copy()
            export_df['date'] = export_df['date'].dt.strftime('%Y-%m-%d')
            export_df = export_df.rename(columns={
                'date': 'Date',
                'gas_origin': 'Gas Origin',
                'flows_bcm': 'Flows (BCM)'
            })
            
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gas_pipeline_flows_chart_{timestamp}.csv"
            return dcc.send_data_frame(export_df.to_csv, filename, index=False)
            
        except Exception as e:
            print(f"Error exporting chart data: {e}")
            return no_update

    @dash_app.callback(
        Output("download-gas-flows-table-csv", "data"),
        Input("export-gas-flows-table-btn", "n_clicks"),
        [State('gas-flows-start-date', 'value'),
         State('gas-flows-end-date', 'value'),
         State('gas-origin-checklist', 'value')],
        prevent_initial_call=True,
    )
    def export_table_data(n_clicks, start_date, end_date, selected_origins):
        """Export table data to CSV."""
        if n_clicks == 0:
            return no_update
            
        try:
            if not selected_origins:
                return no_update

            query_origins = selected_origins.copy()
            if 'Azerbaijan' in selected_origins and 'Turkey' not in query_origins:
                query_origins.append('Turkey')

            query = f"""
            SELECT
                tr.date AS "Day of Date",
                'Exporter' AS "Header_Exporter",
                tr.source_country AS gas_origin,
                'Importer' AS "Header_Importer",
                tr.target_country AS target_country,
                tr.pointlabel AS "Interconnection Point",
                tr."flow_mcm/d" / 1000.0 AS flows_bcm
            FROM european_gas_trade tr
            WHERE tr.source_country IN ('Algeria','Azerbaijan','Libya','Norway','Russia')
            AND tr.date >= :start_date
            AND tr.date <= :end_date
            ORDER BY tr.date DESC;
            """

            results = execute_query(query, {
                'start_date': start_date,
                'end_date': end_date,
            })
            df = pd.DataFrame(results)
            
            if df.empty:
                return no_update

            # Apply same transformations as table
            df['flows_bcm'] = pd.to_numeric(df['flows_bcm'], errors='coerce').fillna(0)
            df['Day of Date'] = pd.to_datetime(df['Day of Date'])

            # Azerbaijan mapping
            aze_points = ['Kipi', 'Nea Mesimvria', 'Strandzha 2', 'Malkoclar']
            mask_aze = (df['gas_origin'] == 'Turkey') & (df['Interconnection Point'].str.contains('|'.join(aze_points), na=False, case=False))
            df.loc[mask_aze, 'gas_origin'] = 'Azerbaijan'
            
            if 'Turkey' not in selected_origins:
                df = df[df['gas_origin'] != 'Turkey']

            # Aggregate
            df = df.groupby(['Day of Date', 'gas_origin', 'target_country', 'Interconnection Point'])['flows_bcm'].sum().reset_index()

            # Prepare export data - flatten the hierarchical structure for CSV
            export_df = df.sort_values('Day of Date', ascending=False).copy()
            export_df['Day of Date'] = export_df['Day of Date'].dt.strftime('%Y-%m-%d')
            export_df = export_df.rename(columns={
                'Day of Date': 'Date',
                'gas_origin': 'Gas Origin',
                'target_country': 'Target Country',
                'Interconnection Point': 'Interconnection Point',
                'flows_bcm': 'Flows (BCM)'
            })
            
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gas_pipeline_flows_table_{timestamp}.csv"
            return dcc.send_data_frame(export_df.to_csv, filename, index=False)
            
        except Exception as e:
            print(f"Error exporting table data: {e}")
            return no_update