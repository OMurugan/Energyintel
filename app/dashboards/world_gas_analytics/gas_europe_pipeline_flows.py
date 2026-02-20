"""
European Gas Trade - Pipeline Flows to Europe
Pipeline flow analytics for European gas trade
"""
from dash import dcc, html, Input, Output, callback, State, dash_table, clientside_callback, ClientsideFunction, no_update, ALL, callback_context
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

GAS_ORIGIN_ORDER = ['Algeria', 'Azerbaijan', 'Libya', 'Norway', 'Russia']

def create_period_selector(prefix):
    """Helper to create independent period selectors for chart or table"""
    return html.Div([
        html.Div([
            html.Span("Year of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
            html.Button('+', id=f'gas-flows-toggle-year-btn-{prefix}', n_clicks=0, style={
                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
            })
        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
        
        html.Div([
            html.Span("Quarter of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
            html.Button('+', id=f'gas-flows-toggle-quarter-btn-{prefix}', n_clicks=0, style={
                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
            })
        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
        
        html.Div([
            html.Span("Month of Date", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
            html.Button('+', id=f'gas-flows-toggle-month-btn-{prefix}', n_clicks=0, style={
                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
            })
        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),

        html.Div([
            html.Span("Week of Year", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
            html.Button('+', id=f'gas-flows-toggle-week-btn-{prefix}', n_clicks=0, style={
                'width': '18px', 'height': '18px', 'padding': '0', 'border': '1px solid #007bff', 
                'backgroundColor': 'white', 'color': '#007bff', 'borderRadius': '3px', 'cursor': 'pointer',
                'fontSize': '12px', 'fontWeight': 'bold', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'
            })
        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '15px'}),
        
        html.Div([
            html.Span("Day of Year", style={'fontSize': '11px', 'color': EI_DARK_BLUE, 'marginRight': '8px'}),
            html.Button('-', id=f'gas-flows-toggle-day-btn-{prefix}', n_clicks=0, style={
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

def create_layout():
    """Create the European Pipeline Flows layout"""
    return html.Div([
        # Selection stores
        dcc.Store(id='gas-flows-chart-period-store', data='DAILY'),
        dcc.Store(id='gas-flows-table-period-store', data='DAILY'),
        dcc.Store(id='gas-flows-table-selection-store', data={'selected_column_id': None}),
        dcc.Store(id='gas-flows-wave-selection', data=None),

        # Main container with Flexbox for Sidebar and Content
        html.Div([
            
            # Sidebar Filter (Right side as per Fig 1)
            html.Div([
                html.Div([
                    html.Label("Start Date", style={'fontSize': '11px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE}),
                    html.Div([
                        dcc.Input(
                            id='gas-flows-start-date',
                            type='text',
                            value='2021-01-01',
                            placeholder='YYYY-MM-DD',
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
                        )
                    ]),
                    
                    html.Label("End Date", style={'fontSize': '11px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE}),
                    html.Div([
                        dcc.Input(
                            id='gas-flows-end-date',
                            type='text',
                            value='2026-01-09',
                            placeholder='YYYY-MM-DD',
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
                        )
                    ]),
                    
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
                        html.Div(id='gas-origin-legend-items')
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
                
                # Period Selector for Chart
                create_period_selector('chart'),
                
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
                    
                    # Period Selector for Table
                    create_period_selector('table'),
                    
                    dcc.Loading(
                        id='loading-gas-flows-table',
                        type='circle',
                        color=EI_ORANGE,
                        children=html.Div(id='gas-flows-table-container')
                    ),
                    
                    # Footer text
                    html.Div([
                        html.P("Source: Energy Intelligence, Transmission System Operators, Federal Agencies", 
                               style={
                                   'fontSize': '10px',
                                   'color': '#666',
                                   'fontStyle': 'italic',
                                   'marginTop': '10px',
                                   'marginBottom': '0',
                                   'fontFamily': 'Inter, sans-serif'
                               })
                    ])
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
    
    # Clientside callback to convert text inputs to date inputs (bypasses Dash validation)
    dash_app.clientside_callback(
        """
        function() {
            setTimeout(function() {
                const startInput = document.getElementById('gas-flows-start-date');
                const endInput = document.getElementById('gas-flows-end-date');
                
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
        Output('gas-flows-table-enhancer-anchor', 'children', allow_duplicate=True),
        Input('gas-flows-start-date', 'id'),
        prevent_initial_call='initial_duplicate'
    )
    
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
                    #${tableId} {
                        cursor: pointer;
                    }
                    #${tableId} td {
                        transition: background-color 0.15s ease, color 0.15s ease;
                    }
                    /* Base selection state: dim normal data cells */
                    #${tableId}.selection-active td {
                        color: #ccc !important;
                    }
                    /* Keep Period of Date column undimmed */
                    #${tableId}.selection-active td[data-dash-column="Period of Date"] {
                        color: #666 !important;
                    }
                    /* Highlight for selected column header */
                    #${tableId} th.column-header-selected {
                        background-color: #0075A8 !important;
                        color: white !important;
                    }
                `;
                document.head.appendChild(style);
            }
            
            // 2. Set up click listener on the table element directly
            const setupListener = () => {
                const tableEl = document.getElementById(tableId);
                if (!tableEl) return;
                if (tableEl.dataset.highlightEnhanced === 'true') return;
                tableEl.dataset.highlightEnhanced = 'true';
                
                tableEl.addEventListener('click', function(e) {
                    const header = e.target.closest('th[data-dash-column]');
                    const cell   = e.target.closest('td[data-dash-column]');
                    if (!header && !cell) return;
                    
                    const columnId = (header || cell).getAttribute('data-dash-column');
                    const rowIndex = cell ? cell.getAttribute('data-dash-row') : null;
                    if (columnId === 'Period of Date' && !rowIndex) return;
                    
                    const isHeader    = !!header;
                    const thead       = isHeader ? header.closest('thead') : null;
                    const headerRows  = thead ? Array.from(thead.querySelectorAll('tr')) : [];
                    const headerRow   = isHeader ? header.closest('tr') : null;
                    const headerIndex = headerRow ? headerRows.indexOf(headerRow) : -1;
                    
                    // Toggle: clicking same cell/header twice clears selection
                    const selectionKey = isHeader ? (columnId + '_' + headerIndex) : (columnId + '_' + rowIndex);
                    if (tableEl.dataset.lastSelection === selectionKey) {
                        tableEl.dataset.lastSelection = '';
                        tableEl.classList.remove('selection-active');
                        tableEl.querySelectorAll('.column-header-selected').forEach(el => el.classList.remove('column-header-selected'));
                        const dynStyle = document.getElementById(dynamicStyleId);
                        if (dynStyle) dynStyle.remove();
                        return;
                    }
                    tableEl.dataset.lastSelection = selectionKey;
                    tableEl.querySelectorAll('.column-header-selected').forEach(el => el.classList.remove('column-header-selected'));
                    tableEl.classList.add('selection-active');
                    
                    let targetColumnIds = [columnId];
                    
                    if (isHeader) {
                        const colspan = parseInt(header.getAttribute('colspan') || header.colSpan || '1');
                        if (colspan > 1) {
                            // Gather leaf column IDs from the last header row (row 4 = entry points)
                            const lastHeaderRow = headerRows[headerRows.length - 1];
                            const leafThs = lastHeaderRow
                                ? Array.from(lastHeaderRow.querySelectorAll('th[data-dash-column]'))
                                : [];
                            const leafIds = leafThs.map(th => th.getAttribute('data-dash-column'));
                            
                            // Count how many columns come before the clicked <th> in its row
                            const allCellsInRow = Array.from(header.closest('tr').querySelectorAll('th'));
                            let colStart = 0;
                            for (let th of allCellsInRow) {
                                if (th === header) break;
                                // The date column has rowSpan and no colspan; treat as 1 col
                                colStart += parseInt(th.getAttribute('colspan') || th.colSpan || '1');
                            }
                            // Subtract 1 for the rowSpan date placeholder in rows 0–3
                            // (it contributes colStart=1 but is not in leafIds)
                            if (headerIndex < headerRows.length - 1) {
                                colStart = Math.max(0, colStart - 1);
                            }
                            targetColumnIds = leafIds.slice(colStart, colStart + colspan);
                        } else {
                            header.classList.add('column-header-selected');
                        }
                    }
                    
                    let dynamicStyles = '';
                    
                    // Column highlight
                    targetColumnIds.forEach(cid => {
                        dynamicStyles += `
                            #${tableId}.selection-active td[data-dash-column="${cid}"] {
                                background-color: #e1f0ff !important;
                                color: #1b365d !important;
                                font-weight: 600 !important;
                            }
                        `;
                    });
                    
                    // Row + active-cell highlight
                    if (rowIndex !== null) {
                        dynamicStyles += `
                            #${tableId}.selection-active tr:has(td[data-dash-row="${rowIndex}"]) td {
                                background-color: #e1f0ff !important;
                                color: #1b365d !important;
                                font-weight: 600 !important;
                            }
                            #${tableId}.selection-active td[data-dash-column="${columnId}"][data-dash-row="${rowIndex}"] {
                                outline: 2px solid #fe5000 !important;
                                outline-offset: -2px;
                                position: relative;
                                z-index: 10 !important;
                            }
                            #${tableId}.selection-active td[data-dash-column="Period of Date"][data-dash-row="${rowIndex}"] {
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
        Output('gas-origin-legend-items', 'children'),
        [Input('gas-origin-checklist', 'value'),
         Input('gas-flows-wave-selection', 'data')]
    )
    def update_gas_origin_legend(selected_origins, selection):
        if not selected_origins:
            return []
            
        # Maintain order from Fig 2: Russia, Norway, Algeria, Azerbaijan, Libya
        origin_order = GAS_ORIGIN_ORDER
        items = []
        for origin in origin_order:
            if origin in selected_origins:
                # Dimming Logic
                is_selected = (selection == origin)
                is_dimmed = (selection is not None) and (not is_selected)
                
                opacity = 0.3 if is_dimmed else 1.0
                font_weight = 'bold' if is_selected else 'normal'
                bg_color = '#f0f0f0' if is_selected else 'transparent'
                
                items.append(html.Div([
                    html.Div(style={
                        'width': '12px', 
                        'height': '12px', 
                        'backgroundColor': GAS_ORIGIN_COLORS.get(origin, '#ccc'), 
                        'marginRight': '8px'
                    }),
                    html.Span(origin, style={'fontSize': '11px', 'color': '#666', 'fontWeight': font_weight})
                ], 
                id={'type': 'gas-origin-legend-item', 'index': origin},
                n_clicks=0,
                style={
                    'display': 'flex', 
                    'alignItems': 'center', 
                    'marginBottom': '4px',
                    'opacity': opacity,
                    'cursor': 'pointer',
                    'padding': '2px 4px',
                    'borderRadius': '4px',
                    'backgroundColor': bg_color,
                    'transition': 'all 0.2s ease'
                }))
        return items

    # Combined helper for both toggle callbacks to minimize duplication
    def get_period_toggle_updates(button_id, current_period, prefix):
        from dash import no_update
        if not button_id:
            return current_period, '+', '+', '+', '+', '-'
            
        new_period = current_period
        if f'gas-flows-toggle-year-btn-{prefix}' in button_id:
            new_period = 'YEARLY'
        elif f'gas-flows-toggle-quarter-btn-{prefix}' in button_id:
            new_period = 'QUARTERLY'
        elif f'gas-flows-toggle-month-btn-{prefix}' in button_id:
            new_period = 'MONTHLY'
        elif f'gas-flows-toggle-week-btn-{prefix}' in button_id:
            new_period = 'WEEKLY'
        elif f'gas-flows-toggle-day-btn-{prefix}' in button_id:
            new_period = 'DAILY'
            
        return (
            new_period,
            '-' if new_period == 'YEARLY' else '+',
            '-' if new_period == 'QUARTERLY' else '+',
            '-' if new_period == 'MONTHLY' else '+',
            '-' if new_period == 'WEEKLY' else '+',
            '-' if new_period == 'DAILY' else '+'
        )

    # Independent store/button callback for Chart
    @dash_app.callback(
        [Output('gas-flows-chart-period-store', 'data'),
         Output('gas-flows-toggle-year-btn-chart', 'children'),
         Output('gas-flows-toggle-quarter-btn-chart', 'children'),
         Output('gas-flows-toggle-month-btn-chart', 'children'),
         Output('gas-flows-toggle-week-btn-chart', 'children'),
         Output('gas-flows-toggle-day-btn-chart', 'children')],
        [Input('gas-flows-toggle-year-btn-chart', 'n_clicks'),
         Input('gas-flows-toggle-quarter-btn-chart', 'n_clicks'),
         Input('gas-flows-toggle-month-btn-chart', 'n_clicks'),
         Input('gas-flows-toggle-week-btn-chart', 'n_clicks'),
         Input('gas-flows-toggle-day-btn-chart', 'n_clicks')],
        [State('gas-flows-chart-period-store', 'data')]
    )
    def toggle_gas_flows_chart_period(*args):
        from dash import callback_context
        ctx = callback_context
        button_id = ctx.triggered[0]['prop_id'] if ctx.triggered else None
        current_period = args[-1]
        return get_period_toggle_updates(button_id, current_period, 'chart')

    # Independent store/button callback for Table
    @dash_app.callback(
        [Output('gas-flows-table-period-store', 'data'),
         Output('gas-flows-toggle-year-btn-table', 'children'),
         Output('gas-flows-toggle-quarter-btn-table', 'children'),
         Output('gas-flows-toggle-month-btn-table', 'children'),
         Output('gas-flows-toggle-week-btn-table', 'children'),
         Output('gas-flows-toggle-day-btn-table', 'children')],
        [Input('gas-flows-toggle-year-btn-table', 'n_clicks'),
         Input('gas-flows-toggle-quarter-btn-table', 'n_clicks'),
         Input('gas-flows-toggle-month-btn-table', 'n_clicks'),
         Input('gas-flows-toggle-week-btn-table', 'n_clicks'),
         Input('gas-flows-toggle-day-btn-table', 'n_clicks')],
        [State('gas-flows-table-period-store', 'data')]
    )
    def toggle_gas_flows_table_period(*args):
        from dash import callback_context
        ctx = callback_context
        button_id = ctx.triggered[0]['prop_id'] if ctx.triggered else None
        current_period = args[-1]
        return get_period_toggle_updates(button_id, current_period, 'table')
    
    @dash_app.callback(
        Output('gas-flows-wave-selection', 'data'),
        [Input('gas-flows-wave-chart', 'clickData'),
         Input({'type': 'gas-origin-legend-item', 'index': ALL}, 'n_clicks')],
        [State('gas-flows-wave-selection', 'data')],
        prevent_initial_call=True
    )
    def toggle_gas_flows_wave_selection(clickData, legend_clicks, current_selection):
        ctx = callback_context
        if not ctx.triggered:
            return no_update
            
        triggered_input = ctx.triggered[0]
        trigger_id = triggered_input['prop_id']
        trigger_value = triggered_input['value']
        
        clicked_origin = None
        
        # 1. Chart Click
        if 'gas-flows-wave-chart.clickData' in trigger_id:
            if not clickData:
                return no_update
            # Use customdata for robust selection: [period_of_date, gas_origin]
            point = clickData['points'][0]
            if 'customdata' not in point:
                return no_update
            clicked_origin = point['customdata'][1]

        # 2. Legend Click
        elif 'gas-origin-legend-item' in trigger_id:
            # Ignore initial load where n_clicks might be 0
            if not trigger_value:
                return no_update
                
            # ctx.triggered_id is a dictionary for pattern matching callbacks
            if not ctx.triggered_id:
                 return no_update
            clicked_origin = ctx.triggered_id['index']
        
        # Ensure it's a clean string
        if clicked_origin:
            clicked_origin = str(clicked_origin).strip()
        else:
            return no_update
        
        # Toggle: if already selected, clear it; otherwise set it
        if current_selection == clicked_origin:
            return None
        
        return clicked_origin

    @dash_app.callback(
        Output('gas-flows-wave-chart', 'figure'),
        [Input('gas-flows-start-date', 'value'),
        Input('gas-flows-end-date', 'value'),
        Input('gas-origin-checklist', 'value'),
        Input('gas-flows-chart-period-store', 'data'),
        Input('gas-flows-wave-selection', 'data')]
    )
    def update_gas_flows_chart(start_date, end_date, selected_origins, period, selection):
        if not selected_origins:
            return go.Figure()

        # Helper for rgba
        def hex_to_rgba(hex_color, opacity):
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 3:
                hex_color = ''.join([c*2 for c in hex_color])
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return f'rgba({rgb[0]},{rgb[1]},{rgb[2]},{opacity})'
            
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
            TO_CHAR(date, 'MM/DD/YYYY') AS period_of_date,
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
            '*' AS period_of_date,
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
            '*' AS period_of_date,
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
            '*' AS period_of_date,
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
            '*' AS period_of_date,
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
            # Clean string data to prevent matching issues
            df['gas_origin'] = df['gas_origin'].astype(str).str.strip()
            
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
                                        'period_of_date': new_date.strftime('%m/%d/%Y')
                                    })
                        pre_2025 = origin_df[origin_df['date'] < '2025-01-01']
                        origin_df = pd.concat([pre_2025, pd.DataFrame(new_rows)])
                    final_dfs.append(origin_df)
                if final_dfs:
                    df = pd.concat(final_dfs).sort_values(['date', 'gas_origin'])
            
            # Consistency in ordering
            origin_order = ['Libya', 'Azerbaijan', 'Algeria', 'Norway', 'Russia']
            all_origins_present = [o for o in origin_order if o in selected_origins]
            
            # Ensure period_of_date exists for all rows
            if 'period_of_date' not in df.columns or df['period_of_date'].isna().any():
                if period == 'DAILY':
                    df['period_of_date'] = df['date'].dt.strftime('%m/%d/%Y')
                else:
                    df['period_of_date'] = '*'
            
            fig = go.Figure()
            
            # Store data for hover traces and calculate cumulative positions
            hover_data = []
            cumulative_y = {}  # Store cumulative y values for stacking
            
            # First pass: Add all area traces and calculate cumulative positions
            for origin in all_origins_present:
                origin_df = df[df['gas_origin'] == origin].sort_values('date').copy()
                
                # For DAILY period, filter out rows where flows_bcm is 0
                if period == 'DAILY':
                    origin_df = origin_df[origin_df['flows_bcm'] > 0]
                
                if not origin_df.empty:
                    base_color = GAS_ORIGIN_COLORS.get(origin, '#ddd')
                    
                    # Calculate cumulative y position for this trace
                    origin_df_with_cumulative = origin_df.copy()
                    for idx, row in origin_df.iterrows():
                        date_key = row['date']
                        if date_key not in cumulative_y:
                            cumulative_y[date_key] = {}
                        
                        # Sum all previous origins' values at this date
                        prev_sum = sum(cumulative_y[date_key].get(prev_origin, 0) for prev_origin in all_origins_present if all_origins_present.index(prev_origin) < all_origins_present.index(origin))
                        cumulative_y[date_key][origin] = prev_sum + row['flows_bcm']
                    
                    # Highlighting Logic
                    if selection:
                        if origin == selection:
                            # Highlighted: bold color (opacity 1.0)
                             fill_color = base_color
                             line_color = 'rgba(255,255,255,0.4)' # Slightly more visible line
                             line_width = 1.0
                        else:
                            # Dimmed: transparent/faded
                            fill_color = hex_to_rgba(base_color, 0.2)
                            line_color = 'rgba(255,255,255,0.1)'
                            line_width = 0.5
                    else:
                        # Normal state (no selection)
                        fill_color = base_color
                        line_color = 'rgba(255,255,255,0.2)'
                        line_width = 0.8
                    
                    # Main trace for the area
                    fig.add_trace(go.Scatter(
                        x=origin_df['date'].values,
                        y=origin_df['flows_bcm'].values,
                        name=origin,
                        stackgroup='one',
                        mode='lines',
                        line=dict(width=line_width, color=line_color),
                        fillcolor=fill_color,
                        showlegend=False,
                        hoverinfo='skip'
                    ))
                    
                    # Store for hover traces with cumulative y positions
                    cumulative_y_values = [cumulative_y[row['date']][origin] for _, row in origin_df.iterrows()]
                    hover_data.append((origin, origin_df, cumulative_y_values))
            
            # Second pass: Add all invisible hover traces on top
            # We need markers throughout the filled area, not just at the top edge
            for origin, origin_df, cumulative_y_values in hover_data:
                # Get the previous cumulative values (bottom of this trace's area)
                origin_index = all_origins_present.index(origin)
                if origin_index == 0:
                    # First trace - bottom is at 0
                    bottom_y_values = [0] * len(origin_df)
                else:
                    # Calculate bottom position (sum of all previous traces)
                    bottom_y_values = []
                    for _, row in origin_df.iterrows():
                        date_key = row['date']
                        prev_sum = sum(cumulative_y[date_key].get(prev_origin, 0) for prev_origin in all_origins_present[:origin_index])
                        bottom_y_values.append(prev_sum)
                
                # Add hover markers at multiple heights within the filled area
                # Top edge, middle, and bottom edge
                for height_fraction in [0.2, 0.5, 0.8]:
                    interpolated_y = [
                        bottom + (top - bottom) * height_fraction 
                        for bottom, top in zip(bottom_y_values, cumulative_y_values)
                    ]
                    
                    fig.add_trace(go.Scatter(
                        x=origin_df['date'].values,
                        y=interpolated_y,
                        name=origin,
                        mode='markers',
                        marker=dict(size=20, opacity=0),
                        showlegend=False,
                        customdata=list(zip(origin_df['period_of_date'].values, [origin] * len(origin_df), origin_df['flows_bcm'].values)),
                        hovertemplate=(
                            "Gas Origin: %{customdata[1]}<br>" +
                            "Date: %{customdata[0]}<br>" +
                            "flows_bcm: %{customdata[2]:.4f}<extra></extra>"
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
                xaxis_config.update(dtick="M12", tickformat="%Y")
            elif period == 'QUARTERLY':
                xaxis_config.update(dtick="M12", tickformat="%Y")
            elif period == 'YEARLY':
                xaxis_config.update(dtick="M12", tickformat="%Y")

            fig.update_layout(
                margin=dict(l=40, r=20, t=10, b=40),
                paper_bgcolor='white',
                plot_bgcolor='white',
                hovermode='closest',
                showlegend=False,
                hoverlabel=dict(
                    bgcolor='white',
                    font_size=12,
                    font_family='Inter, sans-serif',
                    font_color='#333',
                    bordercolor='#ddd',
                    align='left'
                ),
                xaxis=xaxis_config,
                yaxis=dict(
                    showgrid=True,
                    gridcolor='#f5f5f5',
                    tickfont=dict(size=10, color='#999'),
                    dtick=(
                        50.0 if period == 'YEARLY' else
                        10.0 if period == 'QUARTERLY' else
                        5.0 if period == 'MONTHLY' else
                        1.0 if period == 'WEEKLY' else
                        (0.05 if len(selected_origins) == 1 else 0.1)
                    ),
                    fixedrange=True,
                    zeroline=True,
                    zerolinecolor='#f5f5f5',
                    range=[0, (
                        300 if period == 'YEARLY' else
                        80 if period == 'QUARTERLY' else
                        30 if period == 'MONTHLY' else
                        7 if period == 'WEEKLY' else
                        1.0 if period == 'DAILY' else
                        max(df['flows_bcm'].max() * 1.2 if not df.empty else 1.0, 1.0)
                    )]
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
         Input('gas-origin-checklist', 'value'),
         Input('gas-flows-table-period-store', 'data')]
    )
    def update_gas_flows_table(start_date, end_date, selected_origins, period):
        if not selected_origins:
            return html.Div("Please select at least one gas origin.", style={'color': '#666', 'fontSize': '12px', 'padding': '20px'})

        query_origins = selected_origins.copy()
        if 'Azerbaijan' in selected_origins and 'Turkey' not in query_origins:
            query_origins.append('Turkey')

        # Map UI period to SQL granularity
        time_gran = {
            'DAILY': 'DAY',
            'WEEKLY': 'WEEK',
            'MONTHLY': 'MONTH',
            'QUARTERLY': 'QUARTER',
            'YEARLY': 'YEAR'
        }.get(period, 'DAY')

        query = f"""
        SELECT
            CASE
                WHEN :time_granularity = 'DAY' THEN tr.date
                WHEN :time_granularity = 'WEEK' THEN (date_trunc('week', tr.date + interval '1 day') - interval '1 day')::date
                WHEN :time_granularity = 'MONTH' THEN date_trunc('month', tr.date)::date
                WHEN :time_granularity = 'QUARTER' THEN date_trunc('quarter', tr.date)::date
                WHEN :time_granularity = 'YEAR' THEN date_trunc('year', tr.date)::date
            END AS "Period of Date",
            'Exporter' AS "Header_Exporter",
            tr.source_country AS gas_origin,
            'Importer' AS "Header_Importer",
            tr.target_country AS target_country,
            tr.pointlabel AS "Interconnection Point",
            ROUND(SUM(tr."flow_mcm/d") / 1000.0, 6) AS flows_bcm
        FROM european_gas_trade tr
        WHERE tr.source_country = ANY(:origins)
          AND tr.date BETWEEN :start_date AND :end_date
        GROUP BY
            "Period of Date",
            tr.source_country,
            tr.target_country,
            tr.pointlabel
        ORDER BY "Period of Date" DESC;
        """

        try:
            results = execute_query(query, {
                'start_date': start_date,
                'end_date': end_date,
                'time_granularity': time_gran,
                'origins': query_origins
            })
            df = pd.DataFrame(results)
            if df.empty:
                return html.Div("No data available for the selected filters.", style={'color': '#666', 'fontSize': '12px', 'padding': '20px'})

            # Convert types
            df['flows_bcm'] = pd.to_numeric(df['flows_bcm'], errors='coerce').fillna(0)
            df['Period of Date'] = pd.to_datetime(df['Period of Date'])

            # Mapping for Azerbaijan
            aze_points = ['Kipi', 'Nea Mesimvria', 'Strandzha 2', 'Malkoclar']
            mask_aze = (df['gas_origin'] == 'Turkey') & (df['Interconnection Point'].str.contains('|'.join(aze_points), na=False, case=False))
            df.loc[mask_aze, 'gas_origin'] = 'Azerbaijan'
            
            if 'Turkey' not in selected_origins:
                df = df[df['gas_origin'] != 'Turkey']

            # Pivot with 5 levels as requested
            pivot_df = df.pivot_table(
                index='Period of Date',
                columns=['Header_Exporter', 'gas_origin', 'Header_Importer', 'target_country', 'Interconnection Point'],
                values='flows_bcm'
            ).reset_index()
            
            # Sort by date descending
            pivot_df = pivot_df.sort_values(pivot_df.columns[0], ascending=False)

            # Sort origins
            origin_order = GAS_ORIGIN_ORDER
            
            def sort_columns_key(col):
                if col[0] == 'Period of Date':
                    return (-1, "", "", "")
                # col is (Header_Exporter, gas_origin, Header_Importer, target_country, Interconnection Point)
                origin = col[1]
                target = col[3]
                point = col[4]
                order = origin_order.index(origin) if origin in origin_order else 99
                return (order, target, point) # Sort by origin order, then importer name (ascending), then point label

            # Determine the actual column name for the date
            date_col_name = pivot_df.columns[0]
            hier_cols = [c for c in pivot_df.columns if c != date_col_name]
            hier_cols.sort(key=sort_columns_key)
            
            # Date column header alignment (empty labels for the top 4 rows)
            date_header_name = ["", "", "", "", "Period of Date"]
            table_columns = [{"name": date_header_name, "id": "Period of Date"}]
            
            # Prepare unique header labels to prevent excessive merging and show "Exporter"/"Importer" above each group
            exporter_space_map = {}
            importer_space_map = {}
            
            for col in hier_cols:
                header_exp, origin, header_imp, target, point = col
                
                # Assign unique "Exporter" string per gas_origin to repeat title above each origin group
                if origin not in exporter_space_map:
                    exporter_space_map[origin] = " " * len(exporter_space_map)
                unique_exporter = "Exporter" + exporter_space_map[origin]
                
                # Assign unique "Importer" string per (origin, target) to repeat title above each target country
                if (origin, target) not in importer_space_map:
                    importer_space_map[(origin, target)] = " " * len(importer_space_map)
                unique_importer = "Importer" + importer_space_map[(origin, target)]
                
                table_columns.append({
                    "name": [unique_exporter, origin, unique_importer, target, point],
                    "id": "_".join(map(str, col))
                })

            # Identify columns that are the last and first in an Exporter group for boundary borders
            border_col_ids_last = []
            border_col_ids_first = []
            
            if hier_cols:
                border_col_ids_first.append("_".join(map(str, hier_cols[0]))) # First group starts (after date column)
                
            for i in range(len(hier_cols) - 1):
                if hier_cols[i][1] != hier_cols[i+1][1]:
                    border_col_ids_last.append("_".join(map(str, hier_cols[i])))
                    border_col_ids_first.append("_".join(map(str, hier_cols[i+1])))
                    
            # Also the last column of the table
            if hier_cols:
                border_col_ids_last.append("_".join(map(str, hier_cols[-1])))

            # Formatting based on period
            def format_period_date(dt, p):
                if pd.isnull(dt): return ""
                if p == 'YEARLY': return dt.strftime('%Y')
                if p == 'MONTHLY': return dt.strftime('%B %Y')
                if p == 'QUARTERLY': 
                    q = (dt.month - 1) // 3 + 1
                    return f"{dt.year} Q{q}"
                return dt.strftime('%B %d, %Y')

            table_data = []
            for _, row in pivot_df.iterrows():
                d_row = {"Period of Date": format_period_date(row[date_col_name], period)}
                for col in hier_cols:
                    val = row[col]
                    if pd.notnull(val):
                        try:
                            d_row["_".join(map(str, col))] = f"{float(val):.4f}"
                        except (ValueError, TypeError):
                            d_row["_".join(map(str, col))] = str(val)
                    else:
                        d_row["_".join(map(str, col))] = ""
                table_data.append(d_row)

            # ----------------------------------------------------------------
            # Build a custom HTML table for correct borders & scroll alignment.
            # Dash DataTable with fixed_rows + fixed_columns + virtualization
            # creates 4 separate DOM tables, which breaks continuous borders
            # and causes column drift. A single HTML table with CSS sticky
            # avoids all of those issues.
            # ----------------------------------------------------------------

            # --- Compute colspan spans for header rows 0-2 ---
            # Row 0: "Exporter" spanning each gas_origin group
            # Row 1: gas_origin name spanning each (origin) group
            # Row 2: "Importer" spanning each target_country
            # Row 3: target_country spanning each point
            # Row 4: one <th> per leaf column

            def make_spans(hier_cols):
                """Return list of (label, colspan) groups for each header level."""
                spans = [[], [], [], [], []]
                for col in hier_cols:
                    header_exp, origin, header_imp, target, point = col
                    # Row 0 – Exporter group
                    if spans[0] and spans[0][-1][0] == origin:
                        spans[0][-1][1] += 1
                    else:
                        spans[0].append([origin, 1])   # keyed on origin for grouping
                    # Row 1 – gas origin label
                    if spans[1] and spans[1][-1][0] == origin:
                        spans[1][-1][1] += 1
                    else:
                        spans[1].append([origin, 1])
                    # Row 2 – Importer group
                    if spans[2] and spans[2][-1][0] == (origin, target):
                        spans[2][-1][1] += 1
                    else:
                        spans[2].append([(origin, target), 1])
                    # Row 3 – target country label
                    if spans[3] and spans[3][-1][0] == (origin, target):
                        spans[3][-1][1] += 1
                    else:
                        spans[3].append([(origin, target), 1])
                    # Row 4 – leaf point
                    spans[4].append([(origin, target, point), 1])
                return spans

            spans = make_spans(hier_cols)

            # Pre-compute the set of first-column IDs for group-boundary detection
            border_first_set = set(border_col_ids_first)
            border_last_set  = set(border_col_ids_last)

            # Row heights for sticky offsets (px). These match the CSS padding/font.
            ROW_H = [28, 32, 28, 28, 28]  # header rows 0-4

            def sticky_top(row_idx):
                return sum(ROW_H[:row_idx])

            # Common th/td styles
            BASE_TH = {
                'fontFamily': 'Inter, sans-serif',
                'border': '1px solid #dee2e6',
                'padding': '6px 8px',
                'whiteSpace': 'nowrap',
                'textAlign': 'center',
                'boxSizing': 'border-box',
            }
            DATE_COL_W = '150px'
            DATA_COL_W = '100px'

            # ── HEADER ROW STYLES ──────────────────────────────────────────
            ROW_STYLES = [
                # Row 0 – Exporter
                {'backgroundColor': '#e9ecef', 'color': EI_DARK_BLUE,
                 'fontWeight': 'bold', 'fontSize': '11px'},
                # Row 1 – gas origin
                {'backgroundColor': '#f8f9fa', 'color': '#212529',
                 'fontSize': '13px', 'fontWeight': 'bold'},
                # Row 2 – Importer
                {'backgroundColor': '#e9ecef', 'color': EI_DARK_BLUE,
                 'fontWeight': 'bold', 'fontSize': '11px'},
                # Row 3 – target country
                {'backgroundColor': 'white', 'color': EI_DARK_BLUE,
                 'fontWeight': 'bold', 'fontSize': '12px'},
                # Row 4 – entry point
                {'backgroundColor': 'white', 'color': '#666',
                 'fontSize': '11px'},
            ]

            # ── BUILD THEAD ───────────────────────────────────────────────
            thead_rows = []

            # ---- ROWS 0-3: spanned header rows ----
            for row_idx in range(4):
                # "Period of Date" placeholder cell spans all 4 top rows only in row 0
                cells = []
                if row_idx == 0:
                    cells.append(html.Th(
                        '',
                        rowSpan=4,
                        style={
                            **BASE_TH,
                            **ROW_STYLES[row_idx],
                            'position': 'sticky',
                            'top':  f'{sticky_top(row_idx)}px',
                            'left': '0',
                            'zIndex': 5,
                            'minWidth': DATE_COL_W,
                            'width':    DATE_COL_W,
                            'backgroundColor': '#e9ecef',
                            'borderRight': '2px solid #666',
                        }
                    ))

                # Labels for rows 0-3 (Exporter / origin / Importer / target)
                span_row = spans[row_idx]

                # Track running column index to know if a cell lands on a border
                col_cursor = 0
                for label_key, cs in span_row:
                    # Is the first leaf column of this span a group-border?
                    first_leaf_id = "_".join(map(str, hier_cols[col_cursor]))
                    is_first = first_leaf_id in border_first_set

                    display_label = label_key if isinstance(label_key, str) else label_key[1]  # target_country
                    if row_idx == 0:
                        display_label = 'Exporter'
                    if row_idx == 2:
                        display_label = 'Importer'

                    extra_border = {'borderLeft': '2px solid #666'} if is_first else {}

                    cells.append(html.Th(
                        display_label,
                        colSpan=cs,
                        style={
                            **BASE_TH,
                            **ROW_STYLES[row_idx],
                            'position': 'sticky',
                            'top': f'{sticky_top(row_idx)}px',
                            'zIndex': 3,
                            **extra_border,
                        }
                    ))
                    col_cursor += cs

                thead_rows.append(html.Tr(cells))

            # ---- ROW 4: leaf / entry-point row ----
            leaf_cells = [
                html.Th(
                    'Period of Date',
                    style={
                        **BASE_TH,
                        **ROW_STYLES[4],
                        'position': 'sticky',
                        'top':  f'{sticky_top(4)}px',
                        'left': '0',
                        'zIndex': 5,
                        'minWidth': DATE_COL_W,
                        'width':    DATE_COL_W,
                        'backgroundColor': 'white',
                        'borderRight': '2px solid #666',
                        'fontWeight': 'bold',
                        'color': EI_DARK_BLUE,
                    }
                )
            ]
            for col in hier_cols:
                col_id = "_".join(map(str, col))
                is_first = col_id in border_first_set
                extra_border = {'borderLeft': '2px solid #666'} if is_first else {}
                leaf_cells.append(html.Th(
                    col[4],  # Interconnection Point label
                    **{'data-dash-column': col_id},
                    style={
                        **BASE_TH,
                        **ROW_STYLES[4],
                        'position': 'sticky',
                        'top': f'{sticky_top(4)}px',
                        'zIndex': 3,
                        'minWidth': DATA_COL_W,
                        'width':    DATA_COL_W,
                        **extra_border,
                    }
                ))
            thead_rows.append(html.Tr(leaf_cells))

            # ── BUILD TBODY ───────────────────────────────────────────────
            tbody_rows = []
            for row_idx_d, row in enumerate(table_data):
                is_odd = (row_idx_d % 2 == 1)
                row_bg = '#f8f9fa' if is_odd else 'white'

                td_date = html.Td(
                    row.get('Period of Date', ''),
                    **{'data-dash-column': 'Period of Date',
                       'data-dash-row': str(row_idx_d)},
                    style={
                        'fontFamily': 'Inter, sans-serif',
                        'fontSize': '11px',
                        'padding': '6px 8px',
                        'border': '1px solid #dee2e6',
                        'borderRight': '2px solid #999',
                        'whiteSpace': 'nowrap',
                        'textAlign': 'left',
                        'color': '#666',
                        'position': 'sticky',
                        'left': '0',
                        'zIndex': 2,
                        'backgroundColor': row_bg,
                        'minWidth': DATE_COL_W,
                        'width':    DATE_COL_W,
                        'boxSizing': 'border-box',
                    }
                )

                data_cells = [td_date]
                for col in hier_cols:
                    col_id = "_".join(map(str, col))
                    val = row.get(col_id, '')
                    is_first = col_id in border_first_set
                    extra_border = {'borderLeft': '2px solid #666'} if is_first else {}
                    data_cells.append(html.Td(
                        val,
                        **{'data-dash-column': col_id,
                           'data-dash-row': str(row_idx_d)},
                        style={
                            'fontFamily': 'Inter, sans-serif',
                            'fontSize': '11px',
                            'padding': '6px 8px',
                            'border': '1px solid #dee2e6',
                            'textAlign': 'center',
                            'color': '#333',
                            'backgroundColor': row_bg,
                            'minWidth': DATA_COL_W,
                            'width':    DATA_COL_W,
                            'boxSizing': 'border-box',
                            **extra_border,
                        }
                    ))

                tbody_rows.append(html.Tr(data_cells))

            # ── ASSEMBLE TABLE ────────────────────────────────────────────
            table = html.Table(
                [html.Thead(thead_rows), html.Tbody(tbody_rows)],
                id='gas-flows-data-table',
                style={
                    'borderCollapse': 'collapse',
                    'width': 'max-content',
                    'minWidth': '100%',
                    'tableLayout': 'fixed',
                }
            )

            return html.Div(
                table,
                style={
                    'overflowX': 'auto',
                    'overflowY': 'auto',
                    'height': '600px',
                    'width': '100%',
                    'position': 'relative',
                    'marginTop': '10px',
                    'border': '1px solid #dee2e6',
                }
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
         State('gas-origin-checklist', 'value'),
         State('gas-flows-chart-period-store', 'data')],
        prevent_initial_call=True,
    )
    def export_chart_data(n_clicks, start_date, end_date, selected_origins, period):
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
            
            results = execute_query(query, {
                'start_date': start_date,
                'end_date': end_date,
                'origins': query_origins,
                'period': sql_period
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
                                        'period': 'DAILY',
                                        'gas_origin': origin, 
                                        'flows_bcm': daily_vol,
                                        'period_of_date': new_date.strftime('%B %d, %Y')
                                    })
                        pre_2025 = origin_df[origin_df['date'] < '2025-01-01']
                        origin_df = pd.concat([pre_2025, pd.DataFrame(new_rows)])
                    final_dfs.append(origin_df)
                if final_dfs:
                    df = pd.concat(final_dfs).sort_values(['date', 'gas_origin'])

            # Aggregate by date, period, and origin
            df = df.groupby(['date', 'period_of_date', 'gas_origin'])['flows_bcm'].sum().reset_index()
            
            # Prepare export data
            export_df = df.sort_values(['date', 'gas_origin']).copy()
            export_df['date'] = export_df['date'].dt.strftime('%Y-%m-%d')
            export_df = export_df.rename(columns={
                'date': 'Date',
                'period_of_date': 'Period',
                'gas_origin': 'Gas Origin',
                'flows_bcm': 'Flows (BCM)'
            })
            
            # Final column selection and order
            export_df = export_df[['Date', 'Period', 'Gas Origin', 'Flows (BCM)']]
            
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gas_pipeline_flows_{period}_{timestamp}.csv"
            return dcc.send_data_frame(export_df.to_csv, filename, index=False)
            
        except Exception as e:
            print(f"Error exporting chart data: {e}")
            return no_update

    @dash_app.callback(
        Output("download-gas-flows-table-csv", "data"),
        Input("export-gas-flows-table-btn", "n_clicks"),
        [State('gas-flows-start-date', 'value'),
         State('gas-flows-end-date', 'value'),
         State('gas-origin-checklist', 'value'),
         State('gas-flows-table-period-store', 'data')],
        prevent_initial_call=True,
    )
    def export_table_data(n_clicks, start_date, end_date, selected_origins, period):
        """Export table data to CSV."""
        if n_clicks == 0:
            return no_update
            
        try:
            if not selected_origins:
                return no_update

            query_origins = selected_origins.copy()
            if 'Azerbaijan' in selected_origins and 'Turkey' not in query_origins:
                query_origins.append('Turkey')

            # Map UI period to SQL granularity
            time_gran = {
                'DAILY': 'DAY',
                'WEEKLY': 'WEEK',
                'MONTHLY': 'MONTH',
                'QUARTERLY': 'QUARTER',
                'YEARLY': 'YEAR'
            }.get(period, 'DAY')

            query = f"""
            SELECT
                CASE
                    WHEN :time_granularity = 'DAY' THEN tr.date
                    WHEN :time_granularity = 'WEEK' THEN (date_trunc('week', tr.date + interval '1 day') - interval '1 day')::date
                    WHEN :time_granularity = 'MONTH' THEN date_trunc('month', tr.date)::date
                    WHEN :time_granularity = 'QUARTER' THEN date_trunc('quarter', tr.date)::date
                    WHEN :time_granularity = 'YEAR' THEN date_trunc('year', tr.date)::date
                END AS "Period of Date",
                tr.source_country AS gas_origin,
                tr.target_country AS target_country,
                tr.pointlabel AS "Interconnection Point",
                ROUND(SUM(tr."flow_mcm/d") / 1000.0, 6) AS flows_bcm
            FROM european_gas_trade tr
            WHERE tr.source_country = ANY(:origins)
              AND tr.date BETWEEN :start_date AND :end_date
            GROUP BY
                "Period of Date",
                tr.source_country,
                tr.target_country,
                tr.pointlabel
            ORDER BY "Period of Date" DESC;
            """

            results = execute_query(query, {
                'start_date': start_date,
                'end_date': end_date,
                'time_granularity': time_gran,
                'origins': query_origins
            })
            df = pd.DataFrame(results)
            
            if df.empty:
                return no_update

            # Apply same transformations as table
            df['flows_bcm'] = pd.to_numeric(df['flows_bcm'], errors='coerce').fillna(0)
            df['Period of Date'] = pd.to_datetime(df['Period of Date'])

            # Azerbaijan mapping
            aze_points = ['Kipi', 'Nea Mesimvria', 'Strandzha 2', 'Malkoclar']
            mask_aze = (df['gas_origin'] == 'Turkey') & (df['Interconnection Point'].str.contains('|'.join(aze_points), na=False, case=False))
            df.loc[mask_aze, 'gas_origin'] = 'Azerbaijan'
            
            if 'Turkey' not in selected_origins:
                df = df[df['gas_origin'] != 'Turkey']

            # Aggregate
            df = df.groupby(['Period of Date', 'gas_origin', 'target_country', 'Interconnection Point'])['flows_bcm'].sum().reset_index()

            # Prepare export data with consistent sorting: Date (desc), Origin, Target, Point
            export_df = df.sort_values(['Period of Date', 'gas_origin', 'target_country', 'Interconnection Point'], 
                                     ascending=[False, True, True, True]).copy()
            
            def format_period_date(dt, p):
                if pd.isnull(dt): return ""
                if p == 'YEARLY': return dt.strftime('%Y')
                if p == 'MONTHLY': return dt.strftime('%B %Y')
                if p == 'QUARTERLY': 
                    q = (dt.month - 1) // 3 + 1
                    return f"{dt.year} Q{q}"
                return dt.strftime('%Y-%m-%d')

            export_df['Period of Date'] = export_df['Period of Date'].apply(lambda x: format_period_date(x, period))
            export_df = export_df.rename(columns={
                'Period of Date': 'Date/Period',
                'gas_origin': 'Gas Origin',
                'target_country': 'Target Country',
                'Interconnection Point': 'Interconnection Point',
                'flows_bcm': 'Flows (BCM)'
            })
            
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gas_pipeline_flows_table_{period}_{timestamp}.csv"
            return dcc.send_data_frame(export_df.to_csv, filename, index=False)
            
        except Exception as e:
            print(f"Error exporting table data: {e}")
            return no_update