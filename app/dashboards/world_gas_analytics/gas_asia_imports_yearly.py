import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash
from dash import dcc, html, Input, Output, dash_table, State, callback, ctx, no_update
from core.data_helpers import execute_query
from core.country_mappings import get_iso_code
from .shared_map_utils import (
    create_choropleth_map, handle_map_click_reset, load_world_geojson, get_mapbox_config
)

# Color Palette
EI_ORANGE = "#ff6600"
EI_DARK_BLUE = "#1b365d"
EI_LIGHT_BLUE = "#e8f4f8"

# Origin colors based on Fig 1 (approximate colors from legend images)
ORIGIN_COLORS = {
    'Algeria': '#0070c0',
    'Angola': '#363d4e',
    'Australia': '#945d41',
    'Belgium': '#5b9bd5',
    'Bolivia': '#a5a5a5',
    'Brunei': '#4f81bd',
    'Cameroon': '#b7b7b7',
    'Canada': '#c0504d',
    'China': '#953735',
    'Egypt': '#ff6600',
    'Equatorial Guinea': '#1f497d',
    'France': '#0070c0',
    'Germany': '#515151',
    'Guinea': '#3d4552',
    'India': '#c0504d',
    'Indonesia': '#ed7d31',
    'Iran': '#945d41',
    'Japan': '#ff3300',
    'Kazakhstan': '#555555',
    'Malaysia': '#70adad',
    'Mauritania': '#ed7d31',
    'Mozambique': '#555555',
    'Myanmar': '#5b9bd5',
    'Netherlands': '#1f497d',
    'Nigeria': '#7281bc',
    'Norway': '#7281bc',
    'Oman': '#c5d487',
    'Others': '#c5d487',
    'Papua New Guinea': '#0070c0',
    'Peru': '#303742',
    'Philippines': '#16365d',
    'Qatar': '#16365d',
    'Republic of the Congo': '#7281bc',
    'Russia': '#4682B4',
    'Saudi Arabia': '#0070c0',
    'Senegal': '#303742',
    'Singapore': '#c5d487',
    'South Africa': '#a5a5a5',
    'South Korea': '#0070c0',
    'Spain': '#5b9bd5',
    'Thailand': '#a5a5a5',
    'Timor-Leste': '#a5a5a5',
    'Trinidad and Tobago': '#555555',
    'Turkey': '#945d41',
    'Turkmenistan': '#c5e0b4',
    'United Arab Emirates': '#5b9bd5',
    'United Kingdom': '#a5a5a5',
    'United States': '#c6531d',
    'Uzbekistan': '#16365d'
}

# Button Styles from European Dashboard
GRAN_BTN_CONTAINER_STYLE = {
    'display': 'flex',
    'alignItems': 'center',
    'marginRight': '20px'
}

GRAN_BTN_ACTIVE = {
    'width': '18px',
    'height': '18px',
    'padding': '0',
    'border': '1px solid #007bff',
    'backgroundColor': 'white',
    'color': '#add8e6',
    'borderRadius': '3px',
    'cursor': 'pointer',
    'fontSize': '12px',
    'fontWeight': 'bold',
    'display': 'flex',
    'alignItems': 'center',
    'justifyContent': 'center'
}

GRAN_BTN_INACTIVE = {
    'width': '18px',
    'height': '18px',
    'padding': '0',
    'border': '1px solid #007bff',
    'backgroundColor': 'white',
    'color': '#007bff',
    'borderRadius': '3px',
    'cursor': 'pointer',
    'fontSize': '12px',
    'fontWeight': 'bold',
    'display': 'flex',
    'alignItems': 'center',
    'justifyContent': 'center'
}

EXPORT_BTN_STYLE = {
    'backgroundColor': 'white',
    'color': '#1b365d',
    'border': '1px solid #ddd',
    'padding': '4px 8px',
    'borderRadius': '4px',
    'fontSize': '11px',
    'cursor': 'pointer',
    'zIndex': '1000'
}

def create_asia_period_selector():
    """Helper to create granularity selectors for Asian Imports chart"""
    return html.Div([
        html.Div([
            html.Span("Year of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
            html.Button('-', id='asia-toggle-year-btn', n_clicks=0, style=GRAN_BTN_ACTIVE)
        ], style=GRAN_BTN_CONTAINER_STYLE),
        
        html.Div([
            html.Span("Quarter of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
            html.Button('+', id='asia-toggle-quarter-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
        ], style=GRAN_BTN_CONTAINER_STYLE),
        
        html.Div([
            html.Span("Month of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
            html.Button('+', id='asia-toggle-month-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
        ], style=GRAN_BTN_CONTAINER_STYLE),

        html.Div([
            html.Span("Day of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
            html.Button('+', id='asia-toggle-day-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
        ], style=GRAN_BTN_CONTAINER_STYLE)
    ], style={
        'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#f8f9fa', 
        'padding': '10px 20px', 'width': 'fit-content'
    })

def create_asia_table_period_selector():
    """Helper to create granularity selectors for Asian Imports table"""
    return html.Div([
        html.Div([
            html.Span("Year of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
            html.Button('-', id='asia-imports-table-toggle-year-btn', n_clicks=0, style=GRAN_BTN_ACTIVE)
        ], style=GRAN_BTN_CONTAINER_STYLE),
        
        html.Div([
            html.Span("Quarter of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
            html.Button('+', id='asia-imports-table-toggle-quarter-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
        ], style=GRAN_BTN_CONTAINER_STYLE),
        
        html.Div([
            html.Span("Month of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
            html.Button('+', id='asia-imports-table-toggle-month-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
        ], style=GRAN_BTN_CONTAINER_STYLE),

        html.Div([
            html.Span("Day of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
            html.Button('+', id='asia-imports-table-toggle-day-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
        ], style=GRAN_BTN_CONTAINER_STYLE)
    ], style={
        'display': 'flex', 'alignItems': 'center', 'backgroundColor': '#fff', 
        'padding': '10px 0', 'width': 'fit-content'
    })

def create_layout():
    """Create the Asian Yearly Imports layout"""
    return html.Div([
        # Selection stores
        dcc.Store(id='gas-asia-period-store', data='YEARLY'),
        dcc.Store(id='asia-map-selection-store', data=None),  # Independent map selection
        dcc.Store(id='asia-chart-granularity-store', data='year'),
        dcc.Store(id='asia-table-granularity-store', data='YEARLY'),
        dcc.Store(id='asia-chart-selection-store', data=None),
        dcc.Store(id='asia-imports-table-selection-store', data={}),
        dcc.Store(id='asia-imports-table-highlight-state', data={}),
        
        # Download components
        dcc.Download(id="download-asia-imports-chart-csv"),
        dcc.Download(id="download-asia-imports-map-csv"),
        dcc.Download(id="download-asia-imports-table-csv"),
        
        # Main container with Flexbox for Content and Sidebar
        html.Div([
            
            # Content Area (Left side)
            html.Div([
                # Top Row: Chart and Map
                html.Div([
                    # Chart Section
                    html.Div([
                        html.H3(id='asia-imports-origin-chart-title', children="All Imports by Origin (Bcm)", style={
                            'color': EI_ORANGE, 'fontSize': '18px', 'fontWeight': 'normal', 
                            'margin': '10px 0', 'fontFamily': 'Lato, sans-serif'
                        }),
                        html.Div([
                            # Granularity Selector for Chart
                            create_asia_period_selector(),
                            html.Button("Export to CSV", id="export-asia-imports-chart-csv-btn", style=EXPORT_BTN_STYLE)
                        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
                        
                        # Scrollable container for chart
                        html.Div([
                            dcc.Loading(
                                id='loading-asia-imports-chart',
                                type='circle',
                                color=EI_ORANGE,
                                children=dcc.Graph(
                                    id='asia-imports-bar-chart',
                                    style={'height': '500px'},
                                    config={
                                        'displayModeBar': True,
                                        'modeBarButtonsToAdd': ['zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d'],
                                        'modeBarButtonsToRemove': ['lasso2d', 'select2d', 'zoom2d', 'pan2d'],
                                        'displaylogo': False,
                                        'scrollZoom': False  # Disable scroll zoom to avoid confusion
                                    }
                                )
                            )
                        ], id='asia-chart-scroll-container', style={'overflowX': 'auto', 'overflowY': 'hidden'})
                    ], id='asia-chart-container', style={'width': '50%', 'padding': '10px', 'backgroundColor': 'white'}),
                    
                    # Map Section
                    html.Div([
                        html.H3(id='asia-imports-yearly-map-title', children="All Imports by Origin (Bcm) - 2025", style={
                            'color': EI_ORANGE, 'fontSize': '18px', 'fontWeight': 'normal', 
                            'margin': '10px 0', 'fontFamily': 'Lato, sans-serif'
                        }),
                        html.Div([
                           html.Button("Export to CSV", id="export-asia-imports-map-csv-btn", style=EXPORT_BTN_STYLE)
                        ], style={'textAlign': 'right', 'marginBottom': '10px'}),
                        dcc.Loading(
                            id='loading-asia-imports-yearly-map',
                            type='circle',
                            color=EI_ORANGE,
                            children=dcc.Graph(
                                id='asia-imports-yearly-map',
                                style={'height': '500px'},
                                config={'displayModeBar': False}
                            )
                        )
                    ], id='asia-map-container', style={'width': '50%', 'padding': '10px', 'backgroundColor': 'white'}),
                ], style={'display': 'flex', 'flexDirection': 'row', 'marginBottom': '20px'}),
                
                # Bottom Row: Table
                html.Div([
                    html.H3(id='asia-table-title', children="Total Annual Imports by Destination Bcm - All", style={
                        'color': EI_ORANGE, 'fontSize': '18px', 'fontWeight': 'normal', 
                        'margin': '10px 0', 'fontFamily': 'Lato, sans-serif'
                    }),
                    html.Div([
                        create_asia_table_period_selector(),
                        html.Button("Export to CSV", id="export-asia-imports-table-csv-btn", style=EXPORT_BTN_STYLE)
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
                    dcc.Loading(
                        id='loading-asia-imports-table',
                        type='circle',
                        color=EI_ORANGE,
                        children=html.Div(id='asia-imports-table-container')
                    ),
                    html.Div(
                        "Source: Energy Intelligence.",
                        style={
                            'fontStyle': 'italic',
                            'fontSize': '12px',
                            'color': '#6c757d',
                            'marginTop': '10px',
                            'fontFamily': 'Lato, sans-serif'
                        }
                    )
                ], style={'padding': '10px', 'backgroundColor': 'white'})
                
            ], style={'flex': '1', 'minWidth': '0'}),
            
            # Sidebar Filter (Right side)
            html.Div([
                html.Div([
                    # Unit Filter
                    html.Label("Unit", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': '#777', 'marginTop': '10px'}),
                    dcc.RadioItems(
                        id='asia-unit-filter',
                        options=[{'label': ' Bcm', 'value': 'Bcm'}, {'label': ' GWh', 'value': 'GWh'}],
                        value='Bcm',
                        labelStyle={'display': 'block', 'fontSize': '12px', 'color': '#555', 'marginBottom': '5px'}
                    ),
                    
                    # Flow Type Filter
                    html.Label("Flow Type", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': '#777', 'marginTop': '20px'}),
                    dcc.RadioItems(
                        id='asia-flow-type-filter',
                        options=[
                            {'label': ' (All)', 'value': ' '},
                            {'label': ' LNG', 'value': 'lng'},
                            {'label': ' Pipeline', 'value': 'natural gas'}
                        ],
                        value=' ',
                        labelStyle={'display': 'block', 'fontSize': '12px', 'color': '#555', 'marginBottom': '5px'}
                    ),
                    
                    # Destination Dropdown
                    html.Label("Destination", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': '#777', 'marginTop': '20px'}),
                    dcc.Dropdown(
                        id='asia-destination-dropdown',
                        options=[{'label': '(All)', 'value': '(All)'}],
                        value='(All)',
                        clearable=False,
                        style={'fontSize': '12px', 'marginBottom': '10px'}
                    ),
                    
                    # Origin Dropdown
                    html.Label("Origin", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': '#777', 'marginTop': '20px'}),
                    dcc.Dropdown(
                        id='asia-origin-dropdown',
                        options=[{'label': '(All)', 'value': '(All)'}],
                        value='(All)',
                        clearable=False,
                        style={'fontSize': '12px', 'marginBottom': '10px'}
                    ),
                    
                    # Legend Area
                    html.Div([
                        html.Label("Origin", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': '#777', 'marginTop': '20px', 'display': 'block'}),
                        html.Div(id='asia-origin-legend-items', style={'maxHeight': '400px', 'overflowY': 'auto', 'padding': '5px'})
                    ])
                    
                ], style={'padding': '15px', 'backgroundColor': '#fcfcfc', 'borderLeft': '1px solid #eee', 'height': '100%'})
            ], style={'width': '220px', 'minWidth': '220px'})
            
        ], style={'display': 'flex', 'padding': '10px'})
    ], className='tab-content', style={'backgroundColor': '#ffffff', 'minHeight': '100vh'})

def register_callbacks(dash_app, server):
    """Register all callbacks for Asian Yearly Imports"""
    
    # Clientside Callback for Chart Highlighting (Instant Response)
    dash_app.clientside_callback(
        """
        function(clickData, currentSelection) {
            try {
                console.log("=== Asia Chart Click Debug ===");
                console.log("clickData:", clickData);
                console.log("currentSelection:", currentSelection);
                
                // Find the graph element - it might be wrapped by Dash
                let graphDiv = null;
                const allGraphs = document.querySelectorAll('.js-plotly-plot');
                console.log("Found plotly graphs:", allGraphs.length);
                
                // Find the chart graph (first one in the list, map is second)
                for (let g of allGraphs) {
                    let parent = g.parentElement;
                    while (parent) {
                        if (parent.id === 'loading-asia-imports-chart' || parent.id === 'asia-imports-bar-chart') {
                            graphDiv = g;
                            break;
                        }
                        parent = parent.parentElement;
                    }
                    if (graphDiv && graphDiv.data) break;
                }
                
                if (!graphDiv || !graphDiv.data) {
                    console.error("Graph div not found");
                    return window.dash_clientside.no_update;
                }
                
                console.log("Graph found! Data traces:", graphDiv.data.length);
                
                // No click data - do nothing
                if (!clickData || !clickData.points || clickData.points.length === 0) {
                    console.log("No click data - ignoring");
                    return window.dash_clientside.no_update;
                }
                
                const point = clickData.points[0];
                console.log("Clicked point:", point);
                console.log("Point customdata:", point.customdata);
                console.log("Point curveNumber:", point.curveNumber);
                console.log("Point x:", point.x);
                
                if (!point.customdata || point.customdata.length < 4) {
                    console.log("Invalid customdata - length:", point.customdata ? point.customdata.length : 0);
                    return window.dash_clientside.no_update;
                }
                
                const clickedDest = point.customdata[0];
                const clickedFacet = point.customdata[1];
                const clickedOrigin = point.customdata[2];
                const clickedDestPos = point.customdata[3];
                
                console.log("Clicked segment:", {
                    dest: clickedDest,
                    facet: clickedFacet,
                    origin: clickedOrigin,
                    destPos: clickedDestPos
                });
                
                const newSelection = {
                    destination: clickedDest,
                    facet: clickedFacet,
                    origin: clickedOrigin,
                    dest_pos: clickedDestPos
                };
                
                // Check if clicking same segment - toggle off
                if (currentSelection && 
                    currentSelection.destination === clickedDest &&
                    currentSelection.facet === clickedFacet &&
                    currentSelection.origin === clickedOrigin &&
                    currentSelection.dest_pos === clickedDestPos) {
                    
                    console.log("Same segment clicked - toggling off");
                    // Reset all traces to full opacity
                    const update = {
                        'marker.opacity': graphDiv.data.map(trace => 
                            Array(trace.x ? trace.x.length : 0).fill(1.0)
                        )
                    };
                    Plotly.restyle(graphDiv, update);
                    return null;
                }
                
                // Apply highlighting
                console.log("Applying highlighting...");
                const opacityUpdates = [];
                
                for (let i = 0; i < graphDiv.data.length; i++) {
                    const trace = graphDiv.data[i];
                    const traceName = trace.name || '';
                    
                    if (i < 5) {
                        console.log(`Trace ${i}: ${traceName}, customdata length:`, trace.customdata ? trace.customdata.length : 0);
                    }
                    
                    if (!trace.customdata || trace.customdata.length === 0) {
                        opacityUpdates.push(Array(trace.x ? trace.x.length : 0).fill(1.0));
                        continue;
                    }
                    
                    const opacities = [];
                    
                    if (traceName === clickedOrigin) {
                        console.log(`Trace ${i} matches clicked origin: ${clickedOrigin}`);
                        // This is the selected origin - highlight matching segments
                        for (let j = 0; j < trace.customdata.length; j++) {
                            const cd = trace.customdata[j];
                            if (cd && cd.length >= 4) {
                                const segDest = cd[0];
                                const segFacet = cd[1];
                                const segOrigin = cd[2];
                                const segDestPos = cd[3];
                                
                                const isMatch = (segDest === clickedDest && 
                                    segFacet === clickedFacet && 
                                    segOrigin === clickedOrigin && 
                                    segDestPos === clickedDestPos);
                                
                                if (j < 3) {
                                    console.log(`  Segment ${j}:`, {segDest, segFacet, segOrigin, segDestPos, isMatch});
                                }
                                
                                opacities.push(isMatch ? 1.0 : 0.2);
                            } else {
                                opacities.push(0.2);
                            }
                        }
                        console.log(`  Total opacities for trace ${i}:`, opacities.length, "highlighted:", opacities.filter(o => o === 1.0).length);
                    } else {
                        // Different origin - dim all
                        opacities.push(...Array(trace.customdata.length).fill(0.2));
                    }
                    
                    opacityUpdates.push(opacities);
                }
                
                console.log("Opacity updates prepared:", opacityUpdates.length, "traces");
                
                // Apply the opacity updates immediately
                Plotly.restyle(graphDiv, {'marker.opacity': opacityUpdates});
                console.log("Highlighting applied successfully");
                
                return newSelection;
                
            } catch(e) {
                console.error("Asia Chart Highlight Error:", e);
                console.error("Stack:", e.stack);
                return window.dash_clientside.no_update;
            }
        }
        """,
        Output('asia-chart-selection-store', 'data'),
        Input('asia-imports-bar-chart', 'clickData'),
        State('asia-chart-selection-store', 'data'),
        prevent_initial_call=True
    )
    
    # Clientside callback to re-apply highlighting after chart updates
    dash_app.clientside_callback(
        """
        function(figure, currentSelection) {
            if (!currentSelection) {
                return window.dash_clientside.no_update;
            }
            
            try {
                console.log("=== Re-applying highlighting after chart update ===");
                
                // Small delay to ensure DOM is ready
                setTimeout(function() {
                    let graphDiv = null;
                    const allGraphs = document.querySelectorAll('.js-plotly-plot');
                    
                    for (let g of allGraphs) {
                        let parent = g.parentElement;
                        while (parent) {
                            if (parent.id === 'loading-asia-imports-chart' || parent.id === 'asia-imports-bar-chart') {
                                graphDiv = g;
                                break;
                            }
                            parent = parent.parentElement;
                        }
                        if (graphDiv && graphDiv.data) break;
                    }
                    
                    if (!graphDiv || !graphDiv.data) {
                        console.log("Graph not found for re-highlighting");
                        return;
                    }
                    
                    const clickedDest = currentSelection.destination;
                    const clickedFacet = currentSelection.facet;
                    const clickedOrigin = currentSelection.origin;
                    const clickedDestPos = currentSelection.dest_pos;
                    
                    console.log("Re-applying for:", {clickedDest, clickedFacet, clickedOrigin, clickedDestPos});
                    
                    const opacityUpdates = [];
                    
                    for (let i = 0; i < graphDiv.data.length; i++) {
                        const trace = graphDiv.data[i];
                        const traceName = trace.name || '';
                        
                        if (!trace.customdata || trace.customdata.length === 0) {
                            opacityUpdates.push(Array(trace.x ? trace.x.length : 0).fill(1.0));
                            continue;
                        }
                        
                        const opacities = [];
                        
                        if (traceName === clickedOrigin) {
                            for (let j = 0; j < trace.customdata.length; j++) {
                                const cd = trace.customdata[j];
                                if (cd && cd.length >= 4) {
                                    const segDest = cd[0];
                                    const segFacet = cd[1];
                                    const segOrigin = cd[2];
                                    const segDestPos = cd[3];
                                    
                                    const isMatch = (segDest === clickedDest && 
                                        segFacet === clickedFacet && 
                                        segOrigin === clickedOrigin && 
                                        segDestPos === clickedDestPos);
                                    
                                    opacities.push(isMatch ? 1.0 : 0.2);
                                } else {
                                    opacities.push(0.2);
                                }
                            }
                        } else {
                            opacities.push(...Array(trace.customdata.length).fill(0.2));
                        }
                        
                        opacityUpdates.push(opacities);
                    }
                    
                    Plotly.restyle(graphDiv, {'marker.opacity': opacityUpdates});
                    console.log("Re-highlighting complete");
                }, 100);
                
            } catch(e) {
                console.error("Re-highlight error:", e);
            }
            
            return window.dash_clientside.no_update;
        }
        """,
        Output('asia-chart-selection-store', 'data', allow_duplicate=True),
        Input('asia-imports-bar-chart', 'figure'),
        State('asia-chart-selection-store', 'data'),
        prevent_initial_call=True
    )
    
    # Clientside Callback for Table Highlighting
    dash_app.clientside_callback(
        """
        function(n_data, columns, current_state) {
            try {
                const tableId = 'asia-imports-table';
                
                // 1. Define Styles if not present
                let style = document.getElementById('asia-gas-table-styles');
                if (!style) {
                    style = document.createElement('style');
                    style.id = 'asia-gas-table-styles';
                    document.head.appendChild(style);
                }
                
                // Color: #bbe4f2 (Light Blue)
                style.innerHTML = `
                    .asia-col-selected { background-color: #bbe4f2 !important; }
                    .asia-row-selected { background-color: #bbe4f2 !important; }
                    
                    .asia-dimmed { color: #ccc !important; }
                    
                    .asia-col-selection-active td[data-dash-column="Destination"] { 
                        opacity: 1 !important; 
                        background-color: #fff !important; 
                        color: #ccc !important; 
                    }
                    
                    .asia-row-selection-active tr.asia-row-highlighted td {
                        background-color: #bbe4f2 !important;
                        color: black !important;
                        font-weight: bold;
                    }

                    .asia-row-selection-active tr:not(.asia-row-highlighted) td {
                        color: #ccc !important;
                    }
                    
                    /* Headers */
                    th.asia-col-selected { background-color: #bbe4f2 !important; }
                `;

                if (!window.asiaGasTableState) {
                    window.asiaGasTableState = { 
                        selectedColumnId: null,
                        selectedRowIndices: null
                    };
                }
                // ALWAYS update columns
                window.asiaGasTableState.columns = columns;

                // Helper to clear classes
                function clearAll(spreadsheet) {
                    spreadsheet.classList.remove('asia-col-selection-active');
                    spreadsheet.classList.remove('asia-row-selection-active');
                    
                    const selected = spreadsheet.querySelectorAll('.asia-col-selected, .asia-dimmed, .asia-row-highlighted');
                    selected.forEach(el => {
                        el.classList.remove('asia-col-selected');
                        el.classList.remove('asia-dimmed');
                        el.classList.remove('asia-row-highlighted');
                    });
                }
                
                // Helper to Apply State
                function applyState(spreadsheet) {
                    clearAll(spreadsheet);
                    
                    const state = window.asiaGasTableState;

                    // 1. COLUMN SELECTION
                    if (state.selectedColumnId) {
                        const targetIds = state.selectedColumnId.split(',');
                        if (targetIds.length > 0) {
                            spreadsheet.classList.add('asia-col-selection-active');

                            // Headers
                            targetIds.forEach(id => {
                                const ths = spreadsheet.querySelectorAll(`th[data-dash-column="${id}"]`);
                                ths.forEach(th => th.classList.add('asia-col-selected'));
                            });

                            // Cells
                            const tbodies = spreadsheet.querySelectorAll('tbody');
                            tbodies.forEach(tbody => {
                                const rows = Array.from(tbody.querySelectorAll('tr'));
                                rows.forEach(r => {
                                    const cells = Array.from(r.children);
                                    cells.forEach(cell => {
                                        const cId = cell.getAttribute('data-dash-column');
                                        if (!cId || cId === 'Destination') return;
                                        
                                        if (targetIds.includes(cId)) {
                                            cell.classList.add('asia-col-selected');
                                            cell.classList.remove('asia-dimmed'); 
                                        } else {
                                            cell.classList.add('asia-dimmed');
                                        }
                                    });
                                });
                            });
                        }
                    }

                    // 2. ROW SELECTION
                    if (state.selectedRowIndices) {
                        spreadsheet.classList.add('asia-row-selection-active');
                        
                        let targetIndices = state.selectedRowIndices.split(',').map(Number);

                        const tbodies = spreadsheet.querySelectorAll('tbody');
                        tbodies.forEach(tbody => {
                            const rows = Array.from(tbody.querySelectorAll('tr'));
                            rows.forEach((row, idx) => {
                                if (targetIndices.includes(idx)) {
                                    row.classList.add('asia-row-highlighted');
                                }
                            });
                        });
                    }
                }

                function setupTable() {
                    const tableEl = document.getElementById(tableId);
                    if (!tableEl) { setTimeout(setupTable, 200); return; }
                    
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    if (!spreadsheet) { setTimeout(setupTable, 200); return; }
                    
                    applyState(spreadsheet);
                    
                    if (spreadsheet.dataset.enhanced === 'true') return;
                    spreadsheet.dataset.enhanced = 'true';
                    
                    spreadsheet.addEventListener('click', function(e) {
                        // A. HEADER CLICK
                        const header = e.target.closest('th[data-dash-column]');
                        if (header) {
                            e.stopPropagation();
                            const colId = header.getAttribute('data-dash-column');
                            if (colId === 'Destination') return;
                            
                            const headerContent = header.innerText.trim();
                            
                            // Detect Year/Quarter/Month group
                            let isYear = /^20\d{2}$/.test(headerContent);
                            let isQuarter = /^Q[1-4]$/.test(headerContent);
                            let isMonth = /^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)$/.test(headerContent);
                            
                            let targetIds = [];
                            const currentColumns = window.asiaGasTableState.columns;
                            
                            if (isYear && currentColumns) {
                                currentColumns.forEach(c => {
                                    // Robust match: ID starts with col_YEAR or contains _YEAR_
                                    if (c.id && (c.id === `col_${headerContent}` || c.id.indexOf(`_${headerContent}_`) !== -1 || c.id.endsWith(`_${headerContent}`))) {
                                        targetIds.push(c.id);
                                    }
                                });
                            } else if (isQuarter && currentColumns) {
                                // Extract Year from the clicked column ID
                                const parts = colId.split('_');
                                let year = null;
                                parts.forEach(p => { if (/^20\d{2}$/.test(p)) year = p; });
                                
                                if (year) {
                                    const qStr = `_${year}_${headerContent}`;
                                    currentColumns.forEach(c => {
                                        // Match col_2024_Q1 or col_2024_Q1_January
                                        if (c.id && (c.id === `col_${year}_${headerContent}` || c.id.indexOf(qStr) !== -1)) {
                                            targetIds.push(c.id);
                                        }
                                    });
                                } else {
                                    targetIds.push(colId);
                                }
                            } else {
                                targetIds.push(colId);
                            }

                            const newKey = targetIds.join(',');
                            
                            if (window.asiaGasTableState.selectedColumnId === newKey) {
                                window.asiaGasTableState.selectedColumnId = null;
                            } else {
                                window.asiaGasTableState.selectedColumnId = newKey;
                                window.asiaGasTableState.selectedRowIndices = null;
                            }
                            applyState(spreadsheet);
                            return;
                        }
                        
                        // B. CELL CLICK
                        const cell = e.target.closest('td[data-dash-column]');
                        if (cell) {
                             const colId = cell.getAttribute('data-dash-column');
                             const row = cell.closest('tr');
                             const tbody = row.closest('tbody');
                             const rows = Array.from(tbody.querySelectorAll('tr'));
                             const clickIdx = rows.indexOf(row);
                             
                             if (colId === 'Destination') {
                                 const newKey = String(clickIdx);
                                 
                                 if (window.asiaGasTableState.selectedRowIndices === newKey) {
                                      window.asiaGasTableState.selectedRowIndices = null;
                                 } else {
                                      window.asiaGasTableState.selectedRowIndices = newKey;
                                      window.asiaGasTableState.selectedColumnId = null;
                                 }
                                 applyState(spreadsheet);
                             } else {
                                 // Data Cell -> Reset
                                 window.asiaGasTableState.selectedColumnId = null;
                                 window.asiaGasTableState.selectedRowIndices = null;
                                 applyState(spreadsheet);
                             }
                        }
                    });
                }
                
                setTimeout(setupTable, 500);
                return window.asiaGasTableState;

            } catch(e) { 
                console.error("Asia Table Highlight JS Error:", e);
                return {}; 
            }
        }
        """,
        Output('asia-imports-table-highlight-state', 'data'),
        Input('asia-imports-table-container', 'children'), # Re-run when table children update
        State('asia-imports-table', 'columns'), # Correctly pass the table columns
        State('asia-imports-table-highlight-state', 'data')
    )

    @dash_app.callback(
        [Output('asia-destination-dropdown', 'options'),
         Output('asia-origin-dropdown', 'options')],
        [Input('asia-unit-filter', 'value')]
    )
    def update_filter_options(unit):
        print(f"Asia: update_filter_options started: {unit}")
        data_unit = 'Mcm' if unit == 'Bcm' else 'GWh'
        
        # Query destinations from trade data (Asia/Oceania only)
        dest_query = f"""
        SELECT DISTINCT tr.target_country
        FROM glng_gas_trade tr
        LEFT JOIN dim_country co ON co.dim_country_id = tr.target_country_id
        WHERE tr.unit = '{data_unit}'
          AND (LOWER(co.region) IN ('asia', 'oceania') OR co.country_long_name IS  NULL)
          AND EXTRACT(YEAR FROM tr.date) >= 2019 
        ORDER BY 1;
        """
        # Query origins from trade data (Global origins that import to Asia/Oceania)
        origin_query = f"""
        SELECT DISTINCT tr.source_country
        FROM glng_gas_trade tr
        LEFT JOIN dim_country co ON co.dim_country_id = tr.target_country_id
        WHERE tr.unit = '{data_unit}' AND tr.value is not NULL 
          AND (LOWER(co.region) IN ('asia', 'oceania'))
          AND EXTRACT(YEAR FROM tr.date) >= 2019 
        ORDER BY 1;
        """
        
        try:
            dest_results = execute_query(dest_query)
            origin_results = execute_query(origin_query)
            
            dest_options = [{'label': '(All)', 'value': '(All)'}] + \
                           [{'label': r['target_country'], 'value': r['target_country']} for r in dest_results if r['target_country']]
            origin_options = [{'label': '(All)', 'value': '(All)'}] + \
                            [{'label': r['source_country'], 'value': r['source_country']} for r in origin_results if r['source_country']]
            
            print(f"Asia: options loaded from trade data. Dests: {len(dest_options)}, Origins: {len(origin_options)}")
            return dest_options, origin_options
        except Exception as e:
            print(f"Error loading filter options: {e}")
            return no_update, no_update

    @dash_app.callback(
        [Output('asia-chart-granularity-store', 'data'),
         Output('asia-toggle-year-btn', 'children'),
         Output('asia-toggle-quarter-btn', 'children'),
         Output('asia-toggle-month-btn', 'children'),
         Output('asia-toggle-day-btn', 'children'),
         Output('asia-toggle-year-btn', 'style'),
         Output('asia-toggle-quarter-btn', 'style'),
         Output('asia-toggle-month-btn', 'style'),
         Output('asia-toggle-day-btn', 'style'),
         Output('asia-chart-selection-store', 'data', allow_duplicate=True)],
        [Input('asia-toggle-year-btn', 'n_clicks'),
         Input('asia-toggle-quarter-btn', 'n_clicks'),
         Input('asia-toggle-month-btn', 'n_clicks'),
         Input('asia-toggle-day-btn', 'n_clicks')],
        [State('asia-chart-granularity-store', 'data')],
        prevent_initial_call=True
    )
    def toggle_asia_chart_granularity(y_c, q_c, m_c, d_c, current_gran):
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
        btn_id = ctx.triggered_id
        new_gran = current_gran
        
        if btn_id == 'asia-toggle-year-btn': new_gran = 'year'
        elif btn_id == 'asia-toggle-quarter-btn': new_gran = 'quarter'
        elif btn_id == 'asia-toggle-month-btn': new_gran = 'month'
        elif btn_id == 'asia-toggle-day-btn': new_gran = 'day'
        
        return (
            new_gran,
            '-' if new_gran == 'year' else '+',
            '-' if new_gran == 'quarter' else '+',
            '-' if new_gran == 'month' else '+',
            '-' if new_gran == 'day' else '+',
            GRAN_BTN_ACTIVE if new_gran == 'year' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'quarter' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'month' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'day' else GRAN_BTN_INACTIVE,
            None  # Reset selection when granularity changes
        )

    @dash_app.callback(
        [Output('asia-table-granularity-store', 'data'),
         Output('asia-imports-table-toggle-year-btn', 'children'),
         Output('asia-imports-table-toggle-quarter-btn', 'children'),
         Output('asia-imports-table-toggle-month-btn', 'children'),
         Output('asia-imports-table-toggle-day-btn', 'children'),
         Output('asia-imports-table-toggle-year-btn', 'style'),
         Output('asia-imports-table-toggle-quarter-btn', 'style'),
         Output('asia-imports-table-toggle-month-btn', 'style'),
         Output('asia-imports-table-toggle-day-btn', 'style')],
        [Input('asia-imports-table-toggle-year-btn', 'n_clicks'),
         Input('asia-imports-table-toggle-quarter-btn', 'n_clicks'),
         Input('asia-imports-table-toggle-month-btn', 'n_clicks'),
         Input('asia-imports-table-toggle-day-btn', 'n_clicks')],
        [State('asia-table-granularity-store', 'data')]
    )
    def toggle_asia_table_granularity(y, q, m, d, current_gran):
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
        
        btn_id = ctx.triggered_id
        new_gran = current_gran
        
        if btn_id == 'asia-imports-table-toggle-year-btn': new_gran = 'YEARLY'
        elif btn_id == 'asia-imports-table-toggle-quarter-btn': new_gran = 'QUARTERLY'
        elif btn_id == 'asia-imports-table-toggle-month-btn': new_gran = 'MONTHLY'
        elif btn_id == 'asia-imports-table-toggle-day-btn': new_gran = 'DAILY'
        
        return (
            new_gran,
            '-' if new_gran == 'YEARLY' else '+',
            '-' if new_gran == 'QUARTERLY' else '+',
            '-' if new_gran == 'MONTHLY' else '+',
            '-' if new_gran == 'DAILY' else '+',
            GRAN_BTN_ACTIVE if new_gran == 'YEARLY' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'QUARTERLY' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'MONTHLY' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'DAILY' else GRAN_BTN_INACTIVE
        )

    @dash_app.callback(
        [Output('asia-imports-bar-chart', 'figure'),
         Output('asia-imports-origin-chart-title', 'children'),
         Output('asia-chart-container', 'style'),
         Output('asia-map-container', 'style'),
         Output('asia-imports-bar-chart', 'style')],
        [Input('asia-unit-filter', 'value'),
         Input('asia-flow-type-filter', 'value'),
         Input('asia-origin-dropdown', 'value'),
         Input('asia-destination-dropdown', 'value'),
         Input('asia-chart-granularity-store', 'data')]
    )
    def update_asia_bar_chart(unit, flow_type, origin, destination, granularity):
        chart_title = f"All Imports by Origin ({unit})"
        # Default styles (50/50 split)
        chart_style = {'width': '50%', 'padding': '10px', 'backgroundColor': 'white'}
        map_style = {'width': '50%', 'padding': '10px', 'backgroundColor': 'white'}
        
        # Dynamic chart width based on granularity
        if granularity == 'month':
            chart_width = '3000px'  # Wide enough for monthly bars
        elif granularity == 'day':
            chart_width = '5000px'  # Very wide for daily bars
        else:
            chart_width = '100%'  # Normal width for year/quarter
        
        graph_style = {'height': '500px', 'width': chart_width}
        
        # Unit and Scale
        chart_data_unit = 'Mcm' if unit == 'Bcm' else 'GWh'
        chart_scale = 1000.0 if unit == 'Bcm' else 1.0
        
        # Broaden chart for Month/Day views
        if granularity in ('month', 'day'):
            chart_style['width'] = '75%'
            map_style['width'] = '25%'

        try:
            # Re-generate clauses using f-strings for maximum compatibility (like table callback)
            f_flow_clause = f"AND tr.flow_type = '{flow_type}'" if flow_type != ' ' else ""
            f_origin_clause = f"AND tr.source_country = '{origin}'" if origin != '(All)' else ""
            f_dest_clause = f"AND tr.target_country = '{destination}'" if destination != '(All)' else ""

            query = f"""
            SELECT
                EXTRACT(YEAR FROM tr.date)::int AS "Year of Date",
                CASE
                    WHEN '{granularity}' IN ('quarter', 'month', 'day') 
                    THEN 'Q' || EXTRACT(QUARTER FROM tr.date)::int 
                    ELSE NULL 
                END AS "Quarter of Date",
                CASE
                    WHEN '{granularity}' IN ('month', 'day') 
                    THEN TO_CHAR(tr.date, 'Mon') 
                    ELSE NULL 
                END AS "Month of Date",
                CASE
                    WHEN '{granularity}' = 'day' 
                    THEN EXTRACT(DAY FROM tr.date)::int 
                    ELSE NULL 
                END AS "Day of Date",
                tr.target_country  AS "Destination",
                tr.source_country  AS "Origin",
                '{unit}'           AS "Unit",
                ROUND(SUM(tr.value / {chart_scale}), 9) AS "Value"
            FROM glng_gas_trade tr
            LEFT JOIN dim_country co ON co.dim_country_id = tr.target_country_id
            WHERE tr.unit = '{chart_data_unit}'
              AND (LOWER(co.region) IN ('asia', 'oceania') OR co.country_long_name IS NULL)
              AND EXTRACT(YEAR FROM tr.date) >= 2019
              {f_flow_clause}
              {f_origin_clause}
              {f_dest_clause}
            GROUP BY
                EXTRACT(YEAR FROM tr.date),
                CASE
                    WHEN '{granularity}' IN ('quarter', 'month', 'day') 
                    THEN 'Q' || EXTRACT(QUARTER FROM tr.date)::int 
                    ELSE NULL 
                END,
                CASE
                    WHEN '{granularity}' IN ('month', 'day') 
                    THEN TO_CHAR(tr.date, 'Mon') 
                    ELSE NULL 
                END,
                CASE
                    WHEN '{granularity}' = 'day' 
                    THEN EXTRACT(DAY FROM tr.date)::int 
                    ELSE NULL 
                END,
                tr.target_country,
                tr.source_country
            ORDER BY
                "Year of Date" ASC, 
                "Quarter of Date" ASC, 
                "Month of Date" ASC, 
                "Day of Date" ASC, 
                "Value" DESC;
            """
            
            results = execute_query(query)
            df = pd.DataFrame(results)
            if df.empty: return go.Figure(), chart_title, chart_style, map_style, graph_style

            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
            df = df.dropna(subset=['Value', 'Destination', 'Origin']).copy()
            if df.empty: return go.Figure(), chart_title, chart_style, map_style, graph_style

            # 1. Sort Destinations Alphabetically
            top_dest = sorted(df['Destination'].unique().tolist())
            df = df[df['Destination'].isin(top_dest)].copy()
            if df.empty: return go.Figure(), chart_title, chart_style, map_style, graph_style

            # 2. Origin grouping
            origin_vols = df.groupby('Origin')['Value'].sum().sort_values(ascending=False)
            top_origins = origin_vols.head(15).index.tolist()
            df['Origin_Plot'] = df['Origin'].apply(lambda x: x if x in top_origins else 'Others')

            # 3. Faceting Key (Hierarchical)
            def create_facet_label(row):
                yr = row['Year of Date']
                q = row['Quarter of Date']
                m = row['Month of Date']
                d = row['Day of Date']
                return f"{yr}|{q or ''}|{m or ''}|{d or ''}"

            df['Facet_Key'] = df.apply(create_facet_label, axis=1)

            # Sorting
            time_cols = ['Year of Date', 'Quarter of Date', 'Month of Date', 'Day of Date']
            time_order = df[time_cols + ['Facet_Key']].drop_duplicates()
            month_map = {m: i for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])}
            time_order['Month_Num'] = time_order['Month of Date'].map(month_map).fillna(0)
            time_order = time_order.sort_values(['Year of Date', 'Quarter of Date', 'Month_Num', 'Day of Date'])
            facet_categories = time_order['Facet_Key'].tolist()

            chart_df = df.groupby(['Facet_Key'] + time_cols + ['Destination', 'Origin_Plot', 'Unit'], dropna=False)['Value'].sum().reset_index()

            # Create destination position mapping
            dest_pos_df = pd.DataFrame({'Destination': top_dest, 'dest_pos': range(len(top_dest))})
            chart_df = chart_df.merge(dest_pos_df, on='Destination', how='left')

            # Spacing
            f_spacing = 0.003 if granularity in ('month', 'day') else 0.012

            # Create Chart with customdata: [Destination, Facet_Key, Origin_Plot, dest_pos]
            fig = px.bar(
                chart_df,
                x='Destination',
                y='Value',
                color='Origin_Plot',
                facet_col='Facet_Key',
                facet_col_spacing=f_spacing,
                color_discrete_map=ORIGIN_COLORS,
                category_orders={'Destination': top_dest, 'Facet_Key': facet_categories},
                hover_data=['Year of Date', 'Quarter of Date', 'Month of Date', 'Day of Date', 'Unit', 'Facet_Key', 'dest_pos'],
                custom_data=['Destination', 'Facet_Key', 'Origin_Plot', 'dest_pos'],
                template='plotly_white'
            )

            # Fallback for missing colors (like Fig 1/2)
            fig.update_traces(marker_line_width=0)

            # Tooltip Fig 3 / 4 style
            def get_hovertemplate(gran):
                lbl_color = "#888"
                val_color = "#333"
                
                base = f"<span style='color: {lbl_color}'>Origin:</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style='color: {val_color}'>%{{fullData.name}}</span><br>"
                base += f"<span style='color: {lbl_color}'>Destination:</span> &nbsp;&nbsp;&nbsp;&nbsp;<span style='color: {val_color}'>%{{x}}</span><br>"
                base += f"<span style='color: {lbl_color}'>Year of Date:</span> &nbsp;&nbsp;<span style='color: {val_color}'>%{{customdata[0]}}</span><br>"
                
                if gran in ('quarter', 'month', 'day'):
                    base += f"<span style='color: {lbl_color}'>Quarter:</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style='color: {val_color}'>%{{customdata[1]}}</span><br>"
                if gran in ('month', 'day'):
                    base += f"<span style='color: {lbl_color}'>Month:</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style='color: {val_color}'>%{{customdata[2]}}</span><br>"
                if gran == 'day':
                    base += f"<span style='color: {lbl_color}'>Day:</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style='color: {val_color}'>%{{customdata[3]}}</span><br>"
                
                base += f"<span style='color: {lbl_color}'>Unit:</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style='color: {val_color}'>%{{customdata[4]}}</span><br>"
                base += f"<span style='color: {lbl_color}'>Value:</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style='color: {val_color}'>%{{y:,.3f}}</span><extra></extra>"
                return base

            fig.update_traces(hovertemplate=get_hovertemplate(granularity))

            # Remove the server-side highlighting logic - now handled by clientside callback
            # All traces start with full opacity
            for trace in fig.data:
                trace.hovertemplate = get_hovertemplate(granularity)
                trace.marker.opacity = 1.0

            # Spacing for triple headers
            t_margin = 135 if granularity in ('month', 'day') else (120 if granularity == 'quarter' else 110)
            
            fig.update_layout(
                margin=dict(l=60, r=20, t=t_margin, b=120),
                showlegend=False,
                height=550,
                font=dict(family="Lato, sans-serif"),
                barmode='stack',
                xaxis_title=None,
                yaxis_title=None,
                yaxis=dict(autorange=True, fixedrange=True),  # Lock Y-axis to prevent vertical zoom
                hoverlabel=dict(
                    bgcolor="white",
                    bordercolor="#ddd",
                    font_size=11,
                    font_family="Lato, sans-serif",
                    align="left"
                ),
                dragmode='zoom',  # Enable zoom mode (horizontal only due to fixedrange on y)
                uirevision='asia-chart-constant'  # Maintain UI state across updates
            )

            # Selective Tick Labels (Sparse Labels)
            all_dests = []
            # Plotly internally repeats categories across facets. 
            # We need to find the unique sequence of X positions.
            if not chart_df.empty:
                all_dests = top_dest
            
            tick_text = []
            for i, d in enumerate(all_dests):
                show_label = False
                if granularity == 'year':
                    # Pattern: Unnamed, Named, Unnamed, Unnamed, Named... (Starting index 1)
                    if (i - 1) % 3 == 0:
                        show_label = True
                elif granularity == 'quarter':
                    # Middle value (assuming ~11-12 dests, index 5/6)
                    if i == len(all_dests) // 2:
                        show_label = True
                elif granularity in ('month', 'day'):
                    # First bar named, then skip 2, then 4th bar named, skip 2, repeat
                    # Pattern: Named (0), Unnamed (1,2), Named (3), Unnamed (4,5), Named (6)...
                    if i % 3 == 0:
                        show_label = True
                
                tick_text.append(d if show_label else " ")

            fig.update_xaxes(
                type='category', 
                tickangle=-90, 
                tickfont=dict(size=9), 
                title=None, 
                gridcolor='#f0f0f0',
                tickvals=all_dests,
                ticktext=tick_text
            )
            fig.update_yaxes(tickformat="~s", gridcolor='#f0f0f0', nticks=10)
            # Replace lowercase 'k' with 'K' in ticks if possible? 
            # Actually ~s is automatic. Let's try .3s or similar.

            # Triple Headers Logic (Fig 2 sketch)
            seen_years = {}
            seen_quarters = {}
            
            def format_annotation(a):
                if not a.text: return
                try:
                    full_val = a.text.split("=")[-1]
                    parts = full_val.split("|")
                    if len(parts) < 3: return
                    yr, q, m = parts[0], parts[1], parts[2]
                    
                    label = ""
                    
                    if granularity == 'month':
                        # For monthly view: Year centered, Quarter labels, Month at bottom
                        # Row 1: Year (only show once, centered between Q2 and Q3)
                        if yr not in seen_years:
                            # Only show year label for Q2 or Q3 to center it
                            if q in ('Q2', 'Q3'):
                                label += f"<b>{yr}</b><br>"
                                seen_years[yr] = True
                            else:
                                label += "<br>"
                        else:
                            label += "<br>"
                        
                        # Row 2: Quarter (show for each quarter)
                        q_key = f"{yr}-{q}"
                        if q and q_key not in seen_quarters:
                            label += f"<b>{q}</b><br>"
                            seen_quarters[q_key] = True
                        elif q:
                            label += "<br>"
                        else:
                            label += "<br>"
                        
                        # Row 3: Month (always show)
                        if m:
                            label += f"{m}"
                        
                    elif granularity == 'day':
                        # For daily view: Year centered, Quarter labels, Month + Day at bottom
                        if len(parts) < 4: return
                        day = parts[3]
                        
                        # Row 1: Year (only show once, centered between Q2 and Q3)
                        if yr not in seen_years:
                            if q in ('Q2', 'Q3'):
                                label += f"<b>{yr}</b><br>"
                                seen_years[yr] = True
                            else:
                                label += "<br>"
                        else:
                            label += "<br>"
                        
                        # Row 2: Quarter (show for each quarter)
                        q_key = f"{yr}-{q}"
                        if q and q_key not in seen_quarters:
                            label += f"<b>{q}</b><br>"
                            seen_quarters[q_key] = True
                        elif q:
                            label += "<br>"
                        else:
                            label += "<br>"
                        
                        # Row 3: Month + Day (e.g., "Jan 1", "Feb 1")
                        if m and day:
                            label += f"{m} {day}"
                        
                    elif granularity == 'quarter':
                        # Row 1: Year
                        if yr not in seen_years:
                            label += f"<b>{yr}</b><br>"
                            seen_years[yr] = True
                        else:
                            label += "<br>" 

                        # Row 2: Quarter
                        q_key = f"{yr}-{q}"
                        if q and q_key not in seen_quarters:
                            label += f"<b>{q}</b><br>"
                            seen_quarters[q_key] = True
                        elif q:
                            label += "<br>"
                    
                    elif granularity == 'year':
                        label = f"<b>{yr}</b>"

                    a.update(text=label, font=dict(size=9, color=EI_DARK_BLUE), y=1.02, yanchor='bottom')
                except:
                    pass

            fig.for_each_annotation(format_annotation)
            return fig, chart_title, chart_style, map_style, graph_style
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return go.Figure(), chart_title, chart_style, map_style, {'height': '500px', 'width': '100%'}

    @dash_app.callback(
        [Output('asia-imports-yearly-map', 'figure'),
         Output('asia-imports-yearly-map-title', 'children')],
        [Input('asia-unit-filter', 'value'),
         Input('asia-flow-type-filter', 'value'),
         Input('asia-destination-dropdown', 'value'),
         Input('asia-origin-dropdown', 'value')],
        prevent_initial_call=False
    )
    def update_asia_map_callback(unit, flow_type, dest, origins):
        """Update map based on filter changes - origin filter drives the zoom"""
        return update_asia_map(unit, flow_type, dest, origins)

    @dash_app.callback(
        [Output('asia-imports-table-container', 'children'),
         Output('asia-table-title', 'children')],
        [Input('asia-unit-filter', 'value'),
         Input('asia-flow-type-filter', 'value'),
         Input('asia-origin-dropdown', 'value'),
         Input('asia-destination-dropdown', 'value'),
         Input('asia-table-granularity-store', 'data')]
    )
    def update_asia_table(unit, flow_type, origin, destination, granularity):
        print(f"Asia: update_asia_table started: {unit}, {flow_type}, {origin}, {destination}, {granularity}")
        
        # 1. Build Query
        dest_clause = ""
        if destination != '(All)':
            dest_clause = f"AND tr.target_country = '{destination}'"

        origin_clause = ""
        if origin != '(All)':
            origin_clause = f"AND tr.source_country = '{origin}'"

        flow_clause = ""
        if flow_type != ' ':
            flow_clause = f"AND tr.flow_type = '{flow_type}'"

        data_unit = 'Mcm' if unit == 'Bcm' else 'GWh'
        scale = 1000.0 if unit == 'Bcm' else 1.0

        query = f"""
        WITH params AS (
            SELECT '{granularity}'::text AS period   -- DAILY | MONTHLY | QUARTERLY | YEARLY
        ),
        base AS (
            SELECT
                tr.target_country                                      AS "Destination",

                EXTRACT(YEAR FROM tr.date)::int                        AS "Year of Date",

                CASE
                    WHEN p.period IN ('QUARTERLY', 'MONTHLY', 'DAILY')
                    THEN 'Q' || EXTRACT(QUARTER FROM tr.date)::int
                END                                                    AS "Quarter of Date",

                CASE
                    WHEN p.period IN ('MONTHLY', 'DAILY')
                    THEN TO_CHAR(tr.date, 'FMMonth')
                END                                                    AS "Month of Date",

                CASE
                    WHEN p.period = 'DAILY'
                    THEN EXTRACT(DAY FROM tr.date)::int
                END                                                    AS "Day of Date",

                '{unit}'                                               AS "Unit",

                tr.value / {scale}                                     AS bcm_value

            FROM glng_gas_trade tr
            LEFT JOIN dim_country co
                ON co.dim_country_id = tr.target_country_id
            CROSS JOIN params p

            WHERE tr.unit = '{data_unit}'
              AND LOWER(co.region) IN ('asia', 'oceania')
              AND EXTRACT(YEAR FROM tr.date) >= 2019
              {dest_clause}
              {origin_clause}
              {flow_clause}
        )

        SELECT
            "Destination",
            "Year of Date",
            "Quarter of Date",
            "Month of Date",
            "Day of Date",
            "Unit",
            ROUND(SUM(bcm_value), 9) AS "Value"

        FROM base
        GROUP BY
            "Destination",
            "Year of Date",
            "Quarter of Date",
            "Month of Date",
            "Day of Date",
            "Unit"

        ORDER BY
            "Destination" ASC,
            "Year of Date" DESC;
        """
        
        try:
            results = execute_query(query)
            print(f"Asia: table query returned {len(results)} rows")
            df = pd.DataFrame(results)
            if df.empty:
                return html.Div("No data available", style={'color': '#666', 'padding': '20px'}), f"Total Annual Imports by Destination {unit}"

            # Ensure Value is numeric
            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
            
            # Month sorting helper
            month_map = {m: i for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'])}
            df['Month_Num'] = df['Month of Date'].map(month_map).fillna(0)

            # Determine pivot columns based on granularity
            pivot_index = 'Destination'
            if granularity == 'YEARLY':
                pivot_cols = ['Year of Date']
                sort_cols = ['Year of Date']
            elif granularity == 'QUARTERLY':
                pivot_cols = ['Year of Date', 'Quarter of Date']
                sort_cols = ['Year of Date', 'Quarter of Date']
            elif granularity == 'MONTHLY':
                pivot_cols = ['Year of Date', 'Quarter of Date', 'Month of Date']
                sort_cols = ['Year of Date', 'Quarter of Date', 'Month_Num']
            elif granularity == 'DAILY':
                # Consolidate to monthly totals with '1' as day label to match reference Fig 1, but keep Quarter
                df['Day of Date'] = 1
                df = df.groupby(['Destination', 'Year of Date', 'Quarter of Date', 'Month of Date', 'Month_Num', 'Day of Date', 'Unit'], as_index=False)['Value'].sum()
                pivot_cols = ['Year of Date', 'Quarter of Date', 'Month of Date', 'Day of Date']
                sort_cols = ['Year of Date', 'Quarter of Date', 'Month_Num', 'Day of Date']
            
            # Sort before pivoting to ensure column order
            df = df.sort_values(sort_cols, ascending=[False] + [True] * (len(sort_cols)-1))
            
            # Pivot
            pivot_df = df.pivot_table(index=pivot_index, columns=pivot_cols, values='Value', aggfunc='sum')
            
            # Flatten columns for DataTable
            # If multi-level, columns will be a MultiIndex
            if len(pivot_cols) > 1:
                # We need to construct columns carefully
                # Expected structure is something that DataTable can consume or we pre-format headers
                # Dash DataTable supports multi-header via 'name' as a list
                
                # Sort columns descending by Year, then Ascending by Q/M/D? Reference Fig 2/3 shows:
                # 2025 (Q1, Q2..), 2024..
                # Actually typically time goes Left to Right or Right to Left.
                # User request: "2025, 2024, 2023..." (Descending Year)
                # Within Year: "Q1, Q2, Q3, Q4" (Ascending Quarter?)
                # Looking at Fig3 provided in prompt:
                # 2025 (Q1, Q2, Q3, Q4) | 2024 (Q1, Q2...)
                # It seems years are descending, but sub-periods are ascending.
                
                # Let's sort the columns explicitly
                # We can't easily sort a MultiIndex with mixed directions (Desc Year, Asc Quarter)
                # So we sort the flattened tuples
                
                col_tuples = pivot_df.columns.to_list()
                
                def sort_key(tup):
                    # Year is index 0 (desc), others are asc
                    yr = tup[0]
                    rest = tup[1:]
                    # We want to reverse year for sorting? 
                    # Easier: negate year for sort if it's int
                    return (-int(yr),) + rest 
                
                # Note: Month is string, so we need month num for sorting if using MONTHLY/DAILY
                # But here we only have the strings in the column usage
                # We might need to re-sort carefully
                 
                # Re-sorting logic:
                # Extract unique combinations from df sorted by `sort_cols` earlier
                unique_cols_df = df[list(set(pivot_cols + sort_cols))].drop_duplicates().sort_values(by=sort_cols, ascending=[False] + [True] * (len(sort_cols)-1))
                sorted_cols = [tuple(row[col] for col in pivot_cols) for _, row in unique_cols_df.iterrows()]
                
                # Filter to only those present in pivot (though they should match)
                sorted_cols = [c for c in sorted_cols if c in pivot_df.columns]
                
                pivot_df = pivot_df[sorted_cols]
                
                # Destination Header with padding
                dest_header = [""] * (len(pivot_cols) - 1) + ["Destination"]
                dt_columns = [{'name': dest_header, 'id': 'Destination'}]
                
                for i, col_tuple in enumerate(sorted_cols):
                    # col_tuple is (Year, Quarter, Month...)
                    # We build the name list. All elements must be strings.
                    name_list = [str(x) for x in col_tuple]
                    
                    # If granularity is DAILY, the last level is Day (often 1)
                    # We use zero-width spaces to prevent merging of common values like '1'
                    if granularity == 'DAILY' and len(name_list) >= 3:
                        name_list[-1] = str(name_list[-1]) + ('\u200b' * (i + 1))
                        
                    # col_id must be a clean string to avoid tooltip issues
                    col_id = "col_" + "_".join([str(x).replace(" ", "") for x in col_tuple])
                    dt_columns.append({'name': name_list, 'id': col_id})
            
            else:
                # Single level (YEARLY)
                # Sort columns descending
                cols = sorted(pivot_df.columns.tolist(), reverse=True)
                pivot_df = pivot_df[cols]
                dt_columns = [{'name': 'Destination', 'id': 'Destination'}] + \
                             [{'name': str(col), 'id': "col_" + str(col)} for col in cols]

            # Re-map pivot_df columns to match dt_columns IDs
            if len(pivot_cols) > 1:
                pivot_df.columns = ["col_" + "_".join([str(x).replace(" ", "") for x in c]) for c in pivot_df.columns]
            else:
                pivot_df.columns = ["col_" + str(c) for c in pivot_df.columns]
                
            pivot_df = pivot_df.reset_index()
            data = pivot_df.to_dict('records')
            
            # Format values
            for row in data:
                for k, v in row.items():
                    if k != 'Destination' and pd.notnull(v):
                        try:
                            # Use comma separator for thousands
                            val_float = float(v)
                            # If it's a whole number, don't show decimals (GWh usually large)
                            if val_float == int(val_float):
                                row[k] = f"{int(val_float):,}"
                            else:
                                row[k] = f"{val_float:,.2f}"
                        except:
                            pass
                    if pd.isnull(v):
                         row[k] = ""

            # 4. Generate Tooltips
            tooltip_data = []
            for row in data:
                row_tooltips = {}
                dest = row.get('Destination', '')
                for col in dt_columns:
                    col_id = col['id']
                    if col_id == 'Destination':
                        continue
                        
                    val = row.get(col_id, '')
                    if val == "":
                        continue
                    
                    # Tooltip construction
                    tooltip_text = f"Destination: {dest}  \n"
                    
                    if isinstance(col['name'], list):
                        for i, name_val in enumerate(col['name']):
                            if name_val == "": continue
                            label = pivot_cols[i]
                            
                            # Only include Year of Date in the tooltip to match Fig 1 / Yearly view
                            if label != 'Year of Date':
                                continue
                                
                            # Strip zero-width spaces used for header separation
                            clean_name = str(name_val).replace('\u200b', '')
                            tooltip_text += f"{label}: {clean_name}  \n"
                    else:
                        tooltip_text += f"Year of Date: {col['name']}  \n"
                    
                    tooltip_text += f"Unit: {unit}  \n"
                    tooltip_text += f"Value: {val}"
                    
                    row_tooltips[col_id] = {'value': tooltip_text, 'type': 'markdown'}
                tooltip_data.append(row_tooltips)
            
            # Construct DataTable
            table = dash_table.DataTable(
                id='asia-imports-table',
                data=data,
                columns=dt_columns,
                tooltip_data=tooltip_data,
                tooltip_delay=0,
                tooltip_duration=None,
                merge_duplicate_headers=True,
                fixed_rows={'headers': True},
                fixed_columns={'headers': True, 'data': 1},
                style_table={
                    'minWidth': '100%', 
                    'height': '600px', 
                    'overflowY': 'auto', 
                    'overflowX': 'auto', 
                    'border': '1px solid #ddd'
                },
                style_header={
                    'backgroundColor': '#ffffff',
                    'fontWeight': 'bold',
                    'textAlign': 'right',
                    'fontSize': '11px',
                    'border': 'none', 
                    'color': '#333',
                    'height': '25px',
                    'padding': '2px'
                },
                style_cell={
                    'padding': '0px 5px',
                    'fontSize': '11px',
                    'fontFamily': 'Arial, sans-serif',
                    'border': 'none', 
                    'minWidth': '70px',
                    'backgroundColor': '#fff',
                    'color': '#777',
                    'height': 'auto',
                    'textAlign': 'right',
                    'cursor': 'pointer'
                },
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#f9f9f9'}
                ],
                css=[{
                    'selector': '.dash-table-tooltip',
                    'rule': 'background-color: white !important; color: #333 !important; border: 1px solid #ccc !important; font-family: Arial, sans-serif !important; border-radius: 2px !important; padding: 10px !important; box-shadow: 2px 2px 8px rgba(0,0,0,0.1) !important; z-index: 1000 !important; visibility: visible !important; opacity: 1 !important; text-align: left !important; min-width: 150px !important;'
                }]
            )
            
            print(f"Asia Table: data rows={len(data)}, tooltip_data rows={len(tooltip_data)}")
            if tooltip_data:
                print(f"Asia Table: Sample tooltip keys: {list(tooltip_data[0].keys())}")
                print(f"Asia Table: Sample data keys: {list(data[0].keys())}")
            
            return table, f"Total Annual Imports by Destination {unit} - {granularity.title()}"

        except Exception as e:
            print(f"Error in update_asia_table: {e}")
            import traceback
            traceback.print_exc()
            return html.Div(f"Error loading table: {e}"), "Error"


    @dash_app.callback(
        Output('asia-origin-legend-items', 'children'),
        Input('asia-imports-bar-chart', 'figure')
    )
    def update_asia_legend(fig):
        if not fig or 'data' not in fig:
            return []
            
        # Extract unique origin names from the visible traces
        active_origins = set()
        for trace in fig['data']:
            if trace.get('name'):
                active_origins.add(trace['name'])
        
        sorted_origins = sorted(list(active_origins))
        
        items = []
        for origin in sorted_origins:
            color = ORIGIN_COLORS.get(origin, '#ccc')
            items.append(html.Div([
                html.Div(style={
                    'width': '10px', 'height': '10px', 'backgroundColor': color, 'marginRight': '6px', 'flexShrink': '0'
                }),
                html.Span(origin, style={'fontSize': '10px', 'color': '#333', 'whiteSpace': 'nowrap', 'overflow': 'hidden', 'textOverflow': 'ellipsis'})
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '2px'}))
            
        return items

    # --- Export Callbacks ---

    @dash_app.callback(
        Output("download-asia-imports-chart-csv", "data"),
        Input("export-asia-imports-chart-csv-btn", "n_clicks"),
        [State('asia-unit-filter', 'value'),
         State('asia-flow-type-filter', 'value'),
         State('asia-origin-dropdown', 'value'),
         State('asia-destination-dropdown', 'value'),
         State('asia-chart-granularity-store', 'data')],
        prevent_initial_call=True
    )
    def export_asia_chart_csv(n_clicks, unit, flow_type, origin, destination, granularity):
        if not n_clicks: return no_update
        
        chart_data_unit = 'Mcm' if unit == 'Bcm' else 'GWh'
        chart_scale = 1000.0 if unit == 'Bcm' else 1.0
        
        f_flow_clause = f"AND tr.flow_type = '{flow_type}'" if flow_type != ' ' else ""
        f_origin_clause = f"AND tr.source_country = '{origin}'" if origin != '(All)' else ""
        f_dest_clause = f"AND tr.target_country = '{destination}'" if destination != '(All)' else ""

        query = f"""
        SELECT
            EXTRACT(YEAR FROM tr.date)::int AS "Year of Date",
            CASE WHEN '{granularity}' IN ('quarter', 'month', 'day') THEN 'Q' || EXTRACT(QUARTER FROM tr.date)::int END AS "Quarter of Date",
            CASE WHEN '{granularity}' IN ('month', 'day') THEN TO_CHAR(tr.date, 'Mon') END AS "Month of Date",
            CASE WHEN '{granularity}' = 'day' THEN EXTRACT(DAY FROM tr.date)::int END AS "Day of Date",
            tr.target_country  AS "Destination",
            tr.source_country  AS "Origin",
            '{unit}'           AS "Unit",
            ROUND(SUM(tr.value / {chart_scale}), 9) AS "Value"
        FROM glng_gas_trade tr
        LEFT JOIN dim_country co ON co.dim_country_id = tr.target_country_id
        WHERE tr.unit = '{chart_data_unit}'
          AND (LOWER(co.region) IN ('asia', 'oceania') OR co.country_long_name IS NULL)
          AND EXTRACT(YEAR FROM tr.date) >= 2019
          {f_flow_clause}
          {f_origin_clause}
          {f_dest_clause}
        GROUP BY 1, 2, 3, 4, 5, 6, 7
        ORDER BY 1, 2, 3, 4, 8 DESC;
        """
        try:
            results = execute_query(query)
            df = pd.DataFrame(results)
            if df.empty: return dcc.send_string("No data found", "no_data.txt")
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            return dcc.send_data_frame(df.to_csv, f"asia_gas_imports_chart_{timestamp}.csv", index=False)
        except Exception as e:
            return dcc.send_string(f"Error: {e}", "error.txt")

    @dash_app.callback(
        Output("download-asia-imports-map-csv", "data"),
        Input("export-asia-imports-map-csv-btn", "n_clicks"),
        [State('asia-unit-filter', 'value'),
         State('asia-flow-type-filter', 'value'),
         State('asia-destination-dropdown', 'value'),
         State('asia-origin-dropdown', 'value')],
        prevent_initial_call=True
    )
    def export_asia_map_csv(n_clicks, unit, flow_type, dest, origins):
        if not n_clicks: return no_update
        data_unit = 'Mcm' if unit == 'Bcm' else 'GWh'
        scale = 1000.0 if unit == 'Bcm' else 1.0
        
        flow_clause = f"AND tr.flow_type = '{flow_type}'" if flow_type != ' ' else ""
        origin_clause = ""
        if origins and "(All)" not in origins:
            if isinstance(origins, list): origin_clause = "AND tr.source_country = ANY(:origins)"
            else: origin_clause = f"AND tr.source_country = '{origins}'"
        dest_clause = f"AND tr.target_country = :dest" if dest and "(All)" not in dest else ""

        query = f"""
        SELECT 
            tr.source_country as "Origin",
            '2025' as "Year",
            '{unit}' as "Unit",
            SUM(tr.value / {scale}) as "Total Value"
        FROM glng_gas_trade tr
        LEFT JOIN dim_country co ON co.dim_country_id = tr.target_country_id
        WHERE EXTRACT(YEAR FROM tr.date) = 2025
          AND tr.unit = '{data_unit}'
          AND (LOWER(co.region) IN ('asia', 'oceania') OR co.country_long_name IS NULL)
          {flow_clause}
        GROUP BY 1, 2, 3
        """
        try:
            results = execute_query(query)
            df = pd.DataFrame(results)
            if df.empty: return dcc.send_string("No data found", "no_data.txt")
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            return dcc.send_data_frame(df.to_csv, f"asia_gas_imports_map_{timestamp}.csv", index=False)
        except Exception as e:
            return dcc.send_string(f"Error: {e}", "error.txt")

    @dash_app.callback(
        Output("download-asia-imports-table-csv", "data"),
        Input("export-asia-imports-table-csv-btn", "n_clicks"),
        [State('asia-unit-filter', 'value'),
         State('asia-flow-type-filter', 'value'),
         State('asia-origin-dropdown', 'value'),
         State('asia-destination-dropdown', 'value'),
         State('asia-table-granularity-store', 'data')],
        prevent_initial_call=True
    )
    def export_asia_table_csv(n_clicks, unit, flow_type, origin, destination, granularity):
        if not n_clicks: return no_update
        
        dest_clause = f"AND tr.target_country = '{destination}'" if destination != '(All)' else ""
        origin_clause = f"AND tr.source_country = '{origin}'" if origin != '(All)' else ""
        flow_clause = f"AND tr.flow_type = '{flow_type}'" if flow_type != ' ' else ""
        data_unit = 'Mcm' if unit == 'Bcm' else 'GWh'
        scale = 1000.0 if unit == 'Bcm' else 1.0

        query = f"""
        SELECT
            tr.target_country                                      AS "Destination",
            EXTRACT(YEAR FROM tr.date)::int                        AS "Year of Date",
            CASE WHEN '{granularity}' IN ('QUARTERLY', 'MONTHLY', 'DAILY') THEN 'Q' || EXTRACT(QUARTER FROM tr.date)::int END AS "Quarter of Date",
            CASE WHEN '{granularity}' IN ('MONTHLY', 'DAILY') THEN TO_CHAR(tr.date, 'FMMonth') END AS "Month of Date",
            CASE WHEN '{granularity}' = 'DAILY' THEN EXTRACT(DAY FROM tr.date)::int END AS "Day of Date",
            '{unit}'                                               AS "Unit",
            ROUND(SUM(tr.value / {scale}), 9)                      AS "Value"
        FROM glng_gas_trade tr
        LEFT JOIN dim_country co ON co.dim_country_id = tr.target_country_id
        WHERE tr.unit = '{data_unit}'
          AND LOWER(co.region) IN ('asia', 'oceania')
          AND EXTRACT(YEAR FROM tr.date) >= 2019
          {dest_clause}
          {origin_clause}
          {flow_clause}
        GROUP BY 1, 2, 3, 4, 5, 6
        ORDER BY 1 ASC, 2 DESC;
        """
        try:
            results = execute_query(query)
            df = pd.DataFrame(results)
            if df.empty: return dcc.send_string("No data found", "no_data.txt")
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            return dcc.send_data_frame(df.to_csv, f"asia_gas_imports_table_{timestamp}.csv", index=False)
        except Exception as e:
            return dcc.send_string(f"Error: {e}", "error.txt")

    # Map click interaction to update origin filter
    @dash_app.callback(
        Output('asia-origin-dropdown', 'value'),
        Input('asia-imports-yearly-map', 'clickData'),
        [State('asia-origin-dropdown', 'value'),
         State('asia-origin-dropdown', 'options')],
        prevent_initial_call=True
    )
    def handle_map_click_filter(clickData, current_origin, options):
        """Handle map clicks to update origin filter using shared utility"""
        if not clickData:
            return no_update
            
        try:
            # Extract all origin options (excluding "(All)")
            all_origins = []
            if options:
                all_origins = [opt['value'] for opt in options if opt['value'] != '(All)']
            
            if not all_origins:
                print("DEBUG: Options empty or missing origins")
                return no_update
            
            # Extract clicked country from map
            point = clickData.get('points', [{}])[0]
            clicked_country = None
            is_background_click = False
            
            # Check for background click markers in customdata
            if "customdata" in point and point["customdata"]:
                if isinstance(point["customdata"], list) and len(point["customdata"]) > 0:
                    if point["customdata"][0] == "__BACKGROUND_CLICK__":
                        is_background_click = True
                    else:
                        clicked_country = point["customdata"][0]
                elif point["customdata"] == "__BACKGROUND_CLICK__":
                    is_background_click = True
                else:
                    clicked_country = point["customdata"]
            
            # Check trace name for background layers
            if "curveNumber" in point and not is_background_click and not clicked_country:
                trace_name = point.get("data", {}).get("name", "")
                if trace_name in ["ocean_grid", "world_background", "atlantic_fill", 
                                 "pacific_west_fill", "pacific_east_fill", "ocean_background", 
                                 "background_fill", "europe_background_fill", "asia_background_fill"]:
                    is_background_click = True

            # Background click detection
            if is_background_click:
                # Reset to (All)
                return '(All)'
            
            # Fallback to text
            if not clicked_country and 'text' in point:
                # Extract country name from hover text
                text = point['text']
                if 'Origin:' in text:
                    # Parse the HTML to extract country name
                    import re
                    match = re.search(r'Origin:.*?<span[^>]*>([^<]+)</span>', text)
                    if match:
                        clicked_country = match.group(1).strip()
            
            if not clicked_country:
                return no_update
            
            # Check if clicked country is in available origins
            if clicked_country not in all_origins:
                print(f"DEBUG: Clicked country '{clicked_country}' not in available origins")
                return no_update
            
            # Toggle logic: clicking same country resets to (All)
            if current_origin == clicked_country:
                return '(All)'
            else:
                return clicked_country
                
        except Exception as e:
            print(f"Map click error: {e}")
            import traceback
            traceback.print_exc()
            return no_update

def _iso_for_country(country):
    """Return ISO Alpha-3 code for a country, using centralized mapping with Asian country additions."""
    # Add missing Asian countries to the mapping
    asian_additions = {
        'Taiwan': 'TWN',
        'New Zealand': 'NZL',
    }
    
    # Check Asian additions first
    if country in asian_additions:
        return asian_additions[country]
    
    # Use centralized mapping
    return get_iso_code(country)

def update_asia_map(unit, flow_type, dest, origins):
    """Update the Asia imports map with zoom to selected origin country"""
    title = f"All Imports by Origin ({unit}) - 2025"
    
    # Build Query for 2025
    data_unit = 'Mcm' if unit == 'Bcm' else 'GWh'
    scale = 1000.0 if unit == 'Bcm' else 1.0

    flow_clause = ""
    if flow_type == 'lng': flow_clause = "AND tr.flow_type = 'lng'"
    elif flow_type == 'natural gas': flow_clause = "AND tr.flow_type = 'natural gas'"
    
    origin_clause = ""
    if origins and "(All)" not in origins:
        if isinstance(origins, list):
            origin_clause = "AND tr.source_country = ANY(:origins)"
        else:
            origin_clause = f"AND tr.source_country = '{origins}'"
        
    dest_clause = ""
    if dest and "(All)" not in dest:
        dest_clause = "AND tr.target_country = :dest"

    query = f"""
    SELECT 
        tr.source_country as origin,
        co.latitude,
        co.longitude,
        SUM(tr.value / {scale}) as total_value
    FROM glng_gas_trade tr
    LEFT JOIN dim_country co ON co.dim_country_id = tr.source_country_id
    WHERE EXTRACT(YEAR FROM tr.date) = 2025
      AND tr.unit = '{data_unit}'
      AND (LOWER(co.region) IN ('asia', 'oceania') OR co.country_long_name IS NULL)
      {flow_clause}
      {origin_clause}
      {dest_clause}
    GROUP BY origin, co.latitude, co.longitude
    """
    
    try:
        results = execute_query(query, {'origins': [origins] if isinstance(origins, str) else origins, 'dest': dest})
        df = pd.DataFrame(results)
        
        if df.empty:
            from .shared_map_utils import create_empty_map
            return create_empty_map("No data available for 2025", height=500), title

        # Ensure numeric and rename for convenience
        df['Value'] = df['total_value'].astype(float)
        
        # Get ISO codes using helper
        df['iso'] = df['origin'].apply(_iso_for_country)
        df = df.dropna(subset=['iso'])
        
        if df.empty:
            from .shared_map_utils import create_empty_map
            return create_empty_map("No geographic data for these origins", height=500), title

        # Colorscale - subdued blues matching Figure 1
        colorscale = [
            (0.0, '#e6f2f8'),  # Very light grayish-blue (for low values)
            (0.3, '#b3d9e8'),  # Light blue-gray
            (0.5, '#80c1d8'),  # Medium blue
            (0.7, '#5a9fba'),  # Medium-dark blue
            (0.9, '#4682b4'),  # Steel blue (for high values like Russia)
            (1.0, '#36648B')   # Dark steel blue (for highest values)
        ]
        
        # Selection handling - check if a specific origin is selected
        selected_name = None
        selected_iso = None
        other_isos = []
        
        # Get all Asian/Oceanian ISOs for better regional dimming
        regional_iso_query = "SELECT country_code FROM dim_country WHERE LOWER(region) IN ('asia', 'oceania') AND country_code IS NOT NULL"
        regional_isos = [r['country_code'] for r in execute_query(regional_iso_query)]
        
        # Check if a specific origin is selected (not "All")
        if origins and origins != '(All)':
            selected_name = origins
            selected_iso = _iso_for_country(selected_name)
            if selected_iso:
                # Dim all other regional countries
                other_isos = [iso for iso in regional_isos if iso != selected_iso]
            else:
                # Fallback to data-driven dimming if selection not in regional list
                other_isos = [iso for iso in df['iso'].tolist() if iso != selected_iso]

        # Create Hover Text and Custom Data (for click handling)
        hover_text = []
        custom_data = []
        for _, row in df.iterrows():
            text = (
                f"<span style='color: #666666; font-family: Arial, sans-serif;'>Origin: </span>"
                f"<span style='color: #000000; font-weight: bold;'>{row['origin']}</span><br>"
                f"<span style='color: #666666; font-family: Arial, sans-serif;'>Year of Date: </span>"
                f"<span style='color: #000000; font-weight: bold;'>2025</span><br>"
                f"<span style='color: #666666; font-family: Arial, sans-serif;'>Value: </span>"
                f"<span style='color: #000000; font-weight: bold;'>{row['Value']:,.2f}</span><br>"
                f"<span style='color: #666666; font-family: Arial, sans-serif;'>Unit: </span>"
                f"<span style='color: #000000; font-weight: bold;'>{unit}</span>"
            )
            hover_text.append(text)
            # Store country name for click handling
            custom_data.append(row['origin'])

        # Create Map using Shared Utility
        from .shared_map_utils import create_choropleth_map
        
        # Prepare countries_df for labels (only for selected country or all if none selected)
        countries_df = df[['origin', 'latitude', 'longitude', 'Value']].copy().rename(columns={'origin': 'Country', 'latitude': 'Latitude', 'longitude': 'Longitude'})
        if selected_name:
            # When selected, show only the selected country label
            countries_df = countries_df[countries_df['Country'] == selected_name]
        else:
            # When not selected, limit labels or show main ones to avoid clutter
            countries_df = countries_df.nlargest(15, 'Value')

        fig = create_choropleth_map(
            locations=df['iso'],
            z_values=df['Value'],
            colorscale=colorscale,
            hover_text=hover_text,
            selected_country=selected_name,
            selected_iso=selected_iso,
            other_isos=other_isos,
            countries_df=countries_df,
            country_names=custom_data,  # Pass country names for click handling
            height=500,
            zmin=0,
            zmax=df['Value'].max()
        )

        # Layout with uirevision and auto-zoom
        use_mapbox, _, mapbox_layout = get_mapbox_config()
        
        # Calculate optimal center and zoom based on selection
        if selected_name and not df[df['origin'] == selected_name].empty:
            sel_row = df[df['origin'] == selected_name].iloc[0]
            if pd.notna(sel_row['latitude']) and pd.notna(sel_row['longitude']):
                center_lat = sel_row['latitude']
                center_lon = sel_row['longitude']
                
                # Determine zoom level based on country size (similar to demand page)
                # Determine zoom level based on country size (similar to demand page)
                # For large countries like Australia, Russia, use lower zoom
                large_countries = ['Australia', 'Russia', 'China', 'United States', 'Canada', 'India', 'Indonesia', 'Brazil']
                medium_countries = ['Malaysia', 'Norway', 'Saudi Arabia', 'Algeria', 'Japan', 'Papua New Guinea']
                
                if selected_name in large_countries:
                    zoom = 2.5  # Lower zoom for large countries
                elif selected_name in medium_countries:
                    zoom = 3.5  # Medium zoom
                else:
                    zoom = 4.5  # Higher zoom for smaller countries
            else:
                center_lat, center_lon, zoom = 25, 105, 1.8  # Default Asia
        else:
            # Default Asia-Pacific view when no specific origin selected
            # Lower zoom to show full region including Australia
            center_lat, center_lon, zoom = 15, 110, 1.3

        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            uirevision='asia-imports-yearly-map',  # Maintain zoom state
            hoverlabel=dict(
                bgcolor="white",
                bordercolor="#cccccc",
                font=dict(family="Arial, sans-serif", size=12, color="black"),
                align="left"
            )
        )
        
        if use_mapbox:
            # Create a copy of mapbox_layout and override center and zoom
            asia_mapbox_layout = mapbox_layout.copy()
            asia_mapbox_layout.update({
                'center': dict(lat=center_lat, lon=center_lon),
                'zoom': zoom
            })
            fig.update_layout(mapbox=asia_mapbox_layout)
        
        return fig, title
        
    except Exception as e:
        print(f"Asia ERROR: update_asia_map failed: {e}")
        import traceback
        traceback.print_exc()
        from .shared_map_utils import create_error_figure
        return create_error_figure(str(e), height=500), title

