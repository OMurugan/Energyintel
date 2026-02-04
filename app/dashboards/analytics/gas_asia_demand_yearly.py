"""
Asian Gas Demand - Yearly Gas Demand
Recreated Tableau dashboard for Asian gas demand by sector and country.
Refined design to match Tableau aesthetics (Year top, Quarter bottom, Right-side legend, Radio filters).
"""
import pandas as pd
import numpy as np
from dash import dcc, html, dash_table, Input, Output, State, no_update
import plotly.graph_objects as go
import os

# --- Configuration ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "data", "Asian-gas-demand-yearly")
BCM_FILE = os.path.join(DATA_DIR, "Asia Gas Demand by Sector_data_bcm.csv")
GWH_FILE = os.path.join(DATA_DIR, "Asia Gas Demand by Sector_data_gwh.csv")

COLORS = {
    'Industrial': '#B7D28B', # Light Green
    'Power': '#CC5521',      # Orange
    'Household': '#006FAD',  # Blue
    'Other': '#1D8F91'       # Teal
}

SECTOR_ORDER = ['Industrial', 'Power', 'Household', 'Other']

# --- Data Loading & Processing ---

def load_data(unit):
    try:
        file_path = BCM_FILE if "Billion Cubic Meter" in unit else GWH_FILE
        if not os.path.exists(file_path):
            print(f"Error: File not found at {file_path}")
            return pd.DataFrame()
            
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        
        # Clean column names
        df.columns = [c.lstrip('\ufeff').strip() for c in df.columns]
        
        # Map months to quarters
        month_map = {
            'January': 'Q1', 'February': 'Q1', 'March': 'Q1',
            'April': 'Q2', 'May': 'Q2', 'June': 'Q2',
            'July': 'Q3', 'August': 'Q3', 'September': 'Q3',
            'October': 'Q4', 'November': 'Q4', 'December': 'Q4'
        }
        df['Quarter'] = df['Month of Date'].map(month_map)
        
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

def filter_data(df, sector, country):
    dff = df.copy()
    if sector != '(All)':
        dff = dff[dff['Sector'] == sector]
    
    if country and country != '(All)':
        dff = dff[dff['Country'] == country]
    
    return dff

# --- UI Components ---

def create_layout():
    """Create the Asian Yearly Demand layout"""
    # Load initial data to get filter options
    df = load_data("Billion Cubic Meter")
    if df.empty:
        return html.Div("Data failed to load.")
        
    all_countries = sorted(df['Country'].unique().tolist())
    all_sectors = ['(All)'] + sorted(df['Sector'].unique().tolist())

    return html.Div([
        # Header Row
        html.Div([
            html.H1("All Gas Demand", style={
                'color': '#FF6B00', 
                'fontSize': '24px', 
                'margin': '0', 
                'padding': '15px 25px',
                'fontWeight': 'bold',
                'fontFamily': 'Arial, sans-serif'
            }),
        ], style={'backgroundColor': '#ffffff', 'borderBottom': '1px solid #ddd'}),

        # Main Content Row
        html.Div([
            # Left Column: Charts and Tables
            html.Div([
                # Chart Container
                html.Div([
                    dcc.Graph(id='asia-gas-demand-chart', config={'displayModeBar': False})
                ], style={'backgroundColor': '#fff', 'padding': '10px'}),

                # Table Container
                html.Div(id='asia-gas-demand-table-container', style={'marginTop': '20px'}),
                dcc.Store(id='asia-table-highlight-state'),
                html.Div(id='asia-table-dummy-output', style={'display': 'none'})
            ], style={'flex': '1', 'padding': '20px', 'overflowX': 'hidden', 'backgroundColor': '#fff'}),

            # Right Column: Filters Panel
            html.Div([
                html.Div([
                    # Unit Filter
                    html.Div([
                        html.Label("Unit", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '12px', 'marginBottom': '8px', 'display': 'block'}),
                        dcc.RadioItems(
                            id='asia-unit-filter',
                            options=[
                                {'label': 'Billion Cubic Meter', 'value': 'Billion Cubic Meter'},
                                {'label': 'Gigawatt-hour', 'value': 'Gigawatt-hour'}
                            ],
                            value='Billion Cubic Meter',
                            labelStyle={'display': 'block', 'marginBottom': '4px', 'fontSize': '12px', 'color': '#333'}
                        )
                    ], style={'marginBottom': '20px', 'borderBottom': '1px solid #eee', 'paddingBottom': '10px'}),

                    # Sector Filter
                    html.Div([
                        html.Label("Sector", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '12px', 'marginBottom': '8px', 'display': 'block'}),
                        dcc.RadioItems(
                            id='asia-sector-filter',
                            options=[{'label': s, 'value': s} for s in all_sectors],
                            value='(All)',
                            labelStyle={'display': 'block', 'marginBottom': '4px', 'fontSize': '12px', 'color': '#333'}
                        )
                    ], style={'marginBottom': '20px', 'borderBottom': '1px solid #eee', 'paddingBottom': '10px'}),

                    # Country Filter
                    html.Div([
                        html.Label("Country", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '12px', 'marginBottom': '8px', 'display': 'block'}),
                        dcc.RadioItems(
                            id='asia-country-filter',
                            options=[{'label': '(All)', 'value': '(All)'}] + [{'label': c, 'value': c} for c in all_countries],
                            value='(All)',
                            labelStyle={'display': 'block', 'marginBottom': '3px', 'fontSize': '12px', 'color': '#333'}
                        )
                    ], style={'marginBottom': '30px'}),

                    # Sector Legend (Matching Image 1)
                    html.Div([
                        html.Label("Sector", style={'fontWeight': 'bold', 'color': '#555', 'fontSize': '12px', 'marginBottom': '10px', 'display': 'block'}),
                        html.Div([
                            html.Div([
                                html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': COLORS[s], 'marginRight': '8px', 'display': 'inline-block'}),
                                html.Span(s, style={'fontSize': '12px', 'color': '#555'})
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px'})
                            for s in reversed(SECTOR_ORDER)
                        ])
                    ], style={'borderTop': '2px solid #eee', 'paddingTop': '15px'})

                ], style={
                    'backgroundColor': '#ffffff',
                    'padding': '15px',
                    'fontSize': '14px'
                })
            ], style={'width': '220px', 'backgroundColor': '#fff', 'borderLeft': '1px solid #ddd', 'minHeight': '100vh'})
        ], style={'display': 'flex', 'minHeight': 'calc(100vh - 55px)'})
    ], id='gas-asia-yearly-container', style={'backgroundColor': '#ffffff', 'fontFamily': 'Arial, sans-serif'})

def build_chart(df, sector_filter, unit):
    available_sectors = df['Sector'].unique()
    sectors_to_plot = [s for s in SECTOR_ORDER if s in available_sectors]
    if sector_filter != '(All)':
        sectors_to_plot = [sector_filter]

    years = sorted(df['Year of Date'].unique())
    
    # Pre-aggregate to year-sector (Summing up quarters/months)
    agg_df = df.groupby(['Year of Date', 'Sector'])['adjusted_unit_value'].sum().reset_index()
    
    fig = go.Figure()
    
    if sector_filter == '(All)':
        for sector in SECTOR_ORDER:
            if sector not in available_sectors:
                continue
            
            y_vals = []
            for y in years:
                val = agg_df[(agg_df['Year of Date'] == y) & (agg_df['Sector'] == sector)]['adjusted_unit_value']
                y_vals.append(val.iloc[0] if not val.empty else 0)
            
            # Determine format string based on unit
            val_fmt = ",.1f" if unit == 'Billion Cubic Meter' else ",.0f"
            
            fig.add_trace(go.Bar(
                name=sector,
                x=years,
                y=y_vals,
                marker_color=COLORS.get(sector),
                # Using 1 decimal for BCM, 0 for GWh as per image style
                text=[f"<b>{v:,.1f}</b>" if unit == 'Billion Cubic Meter' else f"<b>{v:,.0f}</b>" if v > 0 else "" for v in y_vals],
                textposition='inside',
                insidetextanchor='middle',
                textfont=dict(size=11, color='white'),
                hovertemplate=(
                    "<span style='color: #777'>Sector:</span> <span style='color: black'>%{data.name}</span><br>" +
                    "<span style='color: #777'>Year of Date:</span> <span style='color: black'>%{x}</span><br>" +
                    "<span style='color: #777'>Value:</span> <span style='color: black'>%{y:" + val_fmt + "}</span><br>" +
                    f"<span style='color: #777'>Unit:</span> <span style='color: black'>{unit}</span>" +
                    "<extra></extra>"
                ),
                hoverlabel=dict(
                    bgcolor="white",
                    font_size=12,
                    font_family="Arial"
                )
            ))
        
        totals = []
        for y in years:
            val = agg_df[agg_df['Year of Date'] == y]['adjusted_unit_value'].sum()
            totals.append(val)
            
        fig.add_trace(go.Scatter(
            x=years,
            y=totals,
            mode='text',
            text=[f"<b>{v:,.1f}</b>" if unit == 'Billion Cubic Meter' else f"<b>{v:,.0f}</b>" if v > 0 else "" for v in totals],
            textposition='top center',
            showlegend=False,
            textfont=dict(size=12, color='black'),
            cliponaxis=False,
            hoverinfo='skip'
        ))
        fig.update_layout(barmode='stack')
    else:
        y_vals = []
        for y in years:
            val = agg_df[(agg_df['Year of Date'] == y) & (agg_df['Sector'] == sector_filter)]['adjusted_unit_value']
            y_vals.append(val.iloc[0] if not val.empty else 0)
            
        val_fmt = ",.1f" if unit == 'Billion Cubic Meter' else ",.0f"

        fig.add_trace(go.Bar(
            name=sector_filter,
            x=years,
            y=y_vals,
            marker_color=COLORS.get(sector_filter),
            text=[f"<b>{v:,.1f}</b>" if unit == 'Billion Cubic Meter' else f"<b>{v:,.0f}</b>" for v in y_vals],
            textposition='outside',
            textfont=dict(size=12, color='black'),
            cliponaxis=False,
            hovertemplate=(
                "<span style='color: #777'>Sector:</span> <span style='color: black'>%{data.name}</span><br>" +
                "<span style='color: #777'>Year of Date:</span> <span style='color: black'>%{x}</span><br>" +
                "<span style='color: #777'>Value:</span> <span style='color: black'>%{y:" + val_fmt + "}</span><br>" +
                f"<span style='color: #777'>Unit:</span> <span style='color: black'>{unit}</span>" +
                "<extra></extra>"
            ),
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial"
            )
        ))

    fig.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=years,
            ticktext=[str(y) for y in years],
            title='',
            showgrid=False,
            linecolor='#ccc',
            tickfont=dict(size=12, color='#999'),
            side='bottom'
        ),
        yaxis=dict(
            title='',
            showgrid=False,
            showline=False,
            showticklabels=False,
            zeroline=True,
            zerolinecolor='#ccc'
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(t=30, b=40, l=10, r=10),
        height=500,
        showlegend=False
    )

    return fig

def build_table(df, sector_filter, unit):
    if df.empty:
        return html.Div("No data found.", style={'padding': '20px', 'textAlign': 'center'})

    years = sorted(df['Year of Date'].unique(), reverse=True)
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    months_rev = months[::-1]
    
    countries = sorted(df['Country'].unique())
    # Order for table to match Image 1 (Household -> Total)
    table_sector_order = ['Household', 'Industrial', 'Other', 'Power']
    if sector_filter != '(All)':
        sectors_to_show = [sector_filter]
    else:
        sectors_to_show = table_sector_order
    
    table_data = []
    for country in countries:
        country_df = df[df['Country'] == country]
        
        is_first_sector = True
        for sector in sectors_to_show:
            sector_df = country_df[country_df['Sector'] == sector]
            if sector_df.empty and sector_filter == '(All)':
                continue
                
            row = {
                'Country': country if is_first_sector else "", 
                'Sector': sector,
                'Country_Full': country # for styling/filtering if needed
            }
            is_first_sector = False
            
            for y in years:
                year_df = sector_df[sector_df['Year of Date'] == y]
                year_total = 0
                for m in months:
                    val = year_df[year_df['Month of Date'] == m]['adjusted_unit_value'].sum()
                    row[f"{y}_{m}"] = val
                    year_total += val
                row[f"{y}_Total"] = year_total
            table_data.append(row)
            
        if sector_filter == '(All)':
            t_row = {
                'Country': "", 
                'Sector': 'Total',
                'Country_Full': country
            }
            for y in years:
                y_df = country_df[country_df['Year of Date'] == y]
                y_total = 0
                for m in months:
                    val = y_df[y_df['Month of Date'] == m]['adjusted_unit_value'].sum()
                    t_row[f"{y}_{m}"] = val
                    y_total += val
                t_row[f"{y}_Total"] = y_total
            table_data.append(t_row)

    fmt = ',.1f' if unit == 'Billion Cubic Meter' else ',.0f'
    
    # Columns with multi-level headers [Year, Month]
    columns = [
        {'name': ['\u00A0', 'Country'], 'id': 'Country'},
        {'name': ['\u00A0', 'Sector'], 'id': 'Sector'}
    ]
    
    # Track data column IDs for specific styling
    data_col_ids = []
    
    for y in years:
        for m in months_rev:
            col_id = f"{y}_{m}"
            columns.append({
                'name': [str(y), m], 
                'id': col_id, 
                'type': 'numeric', 
                'format': {'specifier': fmt}
            })
            data_col_ids.append(col_id)
            
        columns.append({
            'name': [str(y), 'Total'], 
            'id': f"{y}_Total", 
            'type': 'numeric', 
            'format': {'specifier': fmt}
        })
        data_col_ids.append(f"{y}_Total")

    return html.Div([
        dash_table.DataTable(
            id='asia-gas-demand-table',
            data=table_data,
            columns=columns,
            merge_duplicate_headers=True,
            fixed_rows={'headers': True},
            fixed_columns={'headers': True, 'data': 2},
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
                'textAlign': 'center',
                'fontSize': '11px',
                'border': 'none', 
                'color': '#333',
                'height': '25px',
                'padding': '2px'
            },
            style_cell={
                'padding': '0px 5px', # Minimal padding for reduced height
                'fontSize': '11px',
                'fontFamily': 'Arial, sans-serif',
                'border': 'none', 
                'minWidth': '70px',
                'backgroundColor': '#fff',
                'color': '#777', # Grey text for sectors and data
                'height': 'auto'
            },
            style_header_conditional=[
                # Apply borders ONLY to data columns (Years/Months)
                # 1. Separator between Year and Month (Bottom of Year / Top of Month)
                {'if': {'header_index': 0, 'column_id': data_col_ids}, 'borderBottom': '1px solid #d0d0d0'},
                {'if': {'header_index': 1, 'column_id': data_col_ids}, 'borderTop': '1px solid #d0d0d0'},
                
                # 2. Separator between Month and Data (Bottom of Month)
                {'if': {'header_index': 1, 'column_id': data_col_ids}, 'borderBottom': '1px solid #ccc'},

                # 3. Fixed Column Styling (Country/Sector) - Ensure they mask scrolling content
                # Make sure these are on top
                {'if': {'column_id': ['Country', 'Sector']}, 'zIndex': 999},

                # Empty cells ABOVE Country/Sector (Index 0)
                # Adds the continuous line (borderBottom) requested in red
                {'if': {'header_index': 0, 'column_id': ['Country', 'Sector']}, 
                 'backgroundColor': '#ffffff', 
                 'borderBottom': '1px solid #d0d0d0', 
                 'borderTop': 'none',
                 'borderRight': 'none'},

                # Label cells FOR Country/Sector (Index 1)
                {'if': {'header_index': 1, 'column_id': ['Country', 'Sector']}, 
                 'backgroundColor': '#ffffff', 
                 'borderTop': 'none', # Rely on the borderBottom of the cell above
                 'borderBottom': '1px solid #ccc'}, # Matches data separator
                
                # Vertical dividers
                {'if': {'column_id': 'Sector'}, 'borderRight': '1px solid #ccc'},
                {'if': {'column_id': [f"{y}_Total" for y in years]}, 'borderRight': '1px solid #ccc'},
            ],
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#f2f2f2' # Darker stripe
                },
                {
                    'if': {'filter_query': '{Sector} eq "Total"'},
                    # Removed custom background color to follow striping
                    'fontWeight': 'bold',
                    'color': '#000',
                    'borderBottom': '2px solid #aaa',
                    'borderTop': '1px solid #eee'
                },
                {
                    'if': {'column_id': 'Country'},
                    'textAlign': 'left',
                    'fontWeight': 'bold',
                    'minWidth': '120px',
                    'color': '#333' # Distinct black for Country
                },
                {
                    'if': {'column_id': 'Sector'},
                    'textAlign': 'left',
                    'paddingLeft': '8px',
                    'minWidth': '100px',
                    'borderRight': '1px solid #ccc' # Divider
                },
                {
                    'if': {'column_id': [f"{y}_Total" for y in years]},
                    'borderRight': '1px solid #ccc' # Divider
                }
            ],
            style_as_list_view=False,
        )
    ], style={'backgroundColor': '#fff', 'paddingBottom': '40px'})

# --- Callbacks ---

def register_callbacks(dash_app, server):
    @dash_app.callback(
        [Output('asia-gas-demand-chart', 'figure'),
         Output('asia-gas-demand-table-container', 'children')],
        [Input('asia-unit-filter', 'value'),
         Input('asia-sector-filter', 'value'),
         Input('asia-country-filter', 'value')]
    )
    def update_dashboard(unit, sector, country):
        # Load data
        df = load_data(unit)
        if df.empty:
            return go.Figure(), html.Div("Data error")
            
        # 2. Filter data
        dff = filter_data(df, sector, country)
        
        # Build Chart
        fig = build_chart(dff, sector, unit)
        
        # Build Table
        table = build_table(dff, sector, unit)
        
        return fig, table

    # Clientside Callback for Header Highlighting and Row Highlighting
    dash_app.clientside_callback(
        """
        function(n_data, columns, current_state) {
            try {
                const tableId = 'asia-gas-demand-table';
                
                // 1. Inject or Update CSS
                let style = document.getElementById('asia-gas-styles');
                if (!style) {
                    style = document.createElement('style');
                    style.id = 'asia-gas-styles';
                    document.head.appendChild(style);
                }
                
                style.innerHTML = `
                    .asia-col-selected { background-color: #cfe8ef !important; }
                    .asia-row-selected { background-color: #cfe8ef !important; }
                    .asia-dimmed { opacity: 0.3 !important; }
                    
                    /* Column Selection: Country/Sector remain visible (100% opacity) but NOT blue */
                    .asia-col-selection-active td[data-dash-column="Country"], 
                    .asia-col-selection-active td[data-dash-column="Sector"] { 
                        opacity: 1 !important; 
                        background-color: transparent !important; 
                    }
                    
                    /* Row Selection: The Highlighted Row(s) - FORCE BLUE ON ALL CELLS */
                    .asia-row-selection-active tr.asia-row-highlighted td {
                        opacity: 1 !important;
                        background-color: #cfe8ef !important;
                        color: black !important;
                    }

                    /* Row Selection: Non-selected rows dimmed */
                    .asia-row-selection-active tr:not(.asia-row-trip-wire) td {
                        opacity: 0.3 !important;
                    }

                    /* Headers */
                    th.asia-col-selected { background-color: #cfe8ef !important; }
                `;

                if (!window.asiaGasState) {
                    window.asiaGasState = { 
                        selectedColumnId: null,
                        selectedRowIndices: null // String "start_end" or null
                    };
                }

                // 2. Helper Logic
                function clearAll(spreadsheet) {
                    spreadsheet.classList.remove('asia-col-selection-active');
                    spreadsheet.classList.remove('asia-row-selection-active');
                    
                    const selected = spreadsheet.querySelectorAll('.asia-col-selected, .asia-dimmed, .asia-row-highlighted, .asia-row-trip-wire');
                    selected.forEach(el => {
                        el.classList.remove('asia-col-selected');
                        el.classList.remove('asia-dimmed');
                        el.classList.remove('asia-row-highlighted');
                        el.classList.remove('asia-row-trip-wire');
                    });
                }
                
                function applyState(spreadsheet, n_data) {
                    clearAll(spreadsheet);

                    // COLUMN HIGHLIGHTING
                    if (window.asiaGasState.selectedColumnId) {
                        const targetIds = window.asiaGasState.selectedColumnId.split(',');
                        if (targetIds.length === 0) return;

                        spreadsheet.classList.add('asia-col-selection-active');

                        // Headers
                        targetIds.forEach(id => {
                            const ths = spreadsheet.querySelectorAll(`th[data-dash-column="${id}"]`);
                            ths.forEach(th => th.classList.add('asia-col-selected'));
                        });

                        // Body Cells
                        const allCells = spreadsheet.querySelectorAll('td[data-dash-column]');
                        allCells.forEach(cell => {
                            const cId = cell.getAttribute('data-dash-column');
                            if (cId === 'Country' || cId === 'Sector') return;

                            if (targetIds.includes(cId)) {
                                cell.classList.add('asia-col-selected');
                            } else {
                                cell.classList.add('asia-dimmed');
                            }
                        });
                        return;
                    }

                    // ROW HIGHLIGHTING
                    if (window.asiaGasState.selectedRowIndices) {
                        const [start, end] = window.asiaGasState.selectedRowIndices.split('_').map(Number);
                        
                        spreadsheet.classList.add('asia-row-selection-active');
                        
                        // Handle Split Tables (Fixed Columns vs Data Columns)
                        // Dash often renders multiple TBodies or multiple Tables inside the container.
                        const tbodies = spreadsheet.querySelectorAll('tbody');
                        
                        tbodies.forEach(tbody => {
                            const rows = tbody.querySelectorAll('tr');
                            rows.forEach((row, idx) => {
                                if (idx >= start && idx <= end) {
                                    row.classList.add('asia-row-highlighted');
                                    row.classList.add('asia-row-trip-wire');
                                }
                            });
                        });
                    }
                }

                function setupTable() {
                    const tableEl = document.getElementById(tableId);
                    if (!tableEl) return;
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    
                    // Always try to re-apply state
                    if (spreadsheet && (window.asiaGasState.selectedColumnId || window.asiaGasState.selectedRowIndices)) {
                        applyState(spreadsheet, n_data);
                    }
                    
                    if (!spreadsheet || spreadsheet.dataset.enhanced === 'true') return;

                    spreadsheet.dataset.enhanced = 'true';
                    
                    // Click Handler
                    spreadsheet.addEventListener('click', function(e) {
                         // 1. Column Header Click
                        const header = e.target.closest('th[data-dash-column]');
                        if (header) {
                            e.stopPropagation();
                            const colId = header.getAttribute('data-dash-column');
                            if (colId === 'Country' || colId === 'Sector') return;

                            const headerContent = header.innerText.trim();
                            let isYearHeader = /^\d{4}$/.test(headerContent);
                            let targetIds = [];
                            if (isYearHeader && columns) {
                                columns.forEach(c => {
                                    if (c.id.startsWith(headerContent + '_')) targetIds.push(c.id);
                                });
                            } else {
                                targetIds.push(colId);
                            }

                            const selectionKey = targetIds.join(',');
                            
                            if (window.asiaGasState.selectedColumnId === selectionKey) {
                                window.asiaGasState.selectedColumnId = null;
                            } else {
                                window.asiaGasState.selectedColumnId = selectionKey;
                                window.asiaGasState.selectedRowIndices = null; // Clear rows
                            }
                            applyState(spreadsheet, n_data);
                            return;
                        }

                        // 2. Row Data Click (Country/Sector)
                        const cell = e.target.closest('td[data-dash-column]');
                        if (cell) {
                            const colId = cell.getAttribute('data-dash-column');
                            
                            if (colId === 'Country' || colId === 'Sector') {
                                e.stopPropagation();
                                const row = cell.closest('tr');
                                const tbody = row.closest('tbody');
                                // Calculate Index carefully relative to this specific tbody
                                const allRows = Array.from(tbody.querySelectorAll('tr'));
                                const rowIndex = allRows.indexOf(row);
                         
                                let startIndex = rowIndex;
                                let endIndex = rowIndex;

                                if (colId === 'Country') {
                                    // Use n_data (Data Driven) Grouping
                                    // Scan UP in data to find the "head" (non-empty Country)
                                    if (n_data) {
                                        let curr = rowIndex;
                                        // Scan up
                                        while (curr >= 0) {
                                            if (n_data[curr] && n_data[curr]['Country']) {
                                                startIndex = curr;
                                                break;
                                            }
                                            curr--;
                                        }
                                        if (curr < 0) startIndex = 0; // Fallback

                                        // Scan down
                                        curr = startIndex + 1;
                                        endIndex = n_data.length - 1;
                                        while (curr < n_data.length) {
                                            if (n_data[curr] && n_data[curr]['Country']) {
                                                // Found next country
                                                endIndex = curr - 1;
                                                break;
                                            }
                                            curr++;
                                        }
                                    }
                                } 
                                // Else if Sector: startIndex = endIndex = rowIndex (already set)
                                
                                const selectionKey = `${startIndex}_${endIndex}`;
                                
                                if (window.asiaGasState.selectedRowIndices === selectionKey) {
                                    window.asiaGasState.selectedRowIndices = null;
                                } else {
                                    window.asiaGasState.selectedRowIndices = selectionKey;
                                    window.asiaGasState.selectedColumnId = null; // Clear cols
                                }
                                applyState(spreadsheet, n_data);
                            } else {
                                // Clicked a data cell
                                if (window.asiaGasState.selectedColumnId || window.asiaGasState.selectedRowIndices) {
                                     window.asiaGasState.selectedColumnId = null;
                                     window.asiaGasState.selectedRowIndices = null;
                                     applyState(spreadsheet, n_data);
                                }
                            }
                        }
                    });
                    
                    // Outside Click
                    document.addEventListener('click', function(e) {
                        if (spreadsheet && !spreadsheet.contains(e.target)) {
                            window.asiaGasState.selectedColumnId = null;
                            window.asiaGasState.selectedRowIndices = null;
                            applyState(spreadsheet, n_data);
                        }
                    });
                }

                setupTable();
                
                if (!window.asiaGasObserver) {
                    window.asiaGasObserver = new MutationObserver(() => {
                        setupTable();
                    });
                    window.asiaGasObserver.observe(document.body, { childList: true, subtree: true });
                }

            } catch (e) { console.error(e); }
            return "";
        }
        """,
        Output('asia-table-dummy-output', 'children'),
        Input('asia-gas-demand-table', 'data'),
        [State('asia-gas-demand-table', 'columns'),
         State('asia-table-highlight-state', 'data')]
    )