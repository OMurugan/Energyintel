"""
European Gas Demand - Monthly Demand by Sector
Monthly gas demand analytics by sector
"""
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import dcc, html, dash_table, Input, Output, State, callback, callback_context, no_update
from datetime import datetime, date
from core.data_helpers import execute_query
import os


# Button Styles
GRAN_BTN_CONTAINER_STYLE = {
    'display': 'flex',
    'align-items': 'center',
    'margin-right': '20px'
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


def load_data(unit='Million Cubic Meter', granularity='month'):
    """Load the sector demand data using SQL query"""
    try:
        # 1. Fetch all countries in Europe for the query filter
        country_query = "SELECT DISTINCT country_long_name FROM dev.dim_country WHERE LOWER(region) = 'europe'"
        try:
            country_results = execute_query(country_query)
            countries = [r['country_long_name'] for r in country_results]
        except Exception as e:
            print(f"Error loading countries: {e}")
            countries = []

        if not countries:
            print("No countries found in Europe region, query may fail returning empty.")
            return pd.DataFrame(), pd.DataFrame()

        # 2. Prepare main query params
        unit_map = {'Million Cubic Meter': 'Mcm', 'GWh': 'GWh'}
        db_unit = unit_map.get(unit, 'Mcm')
        
        # We fetch all sectors
        sectors = ['Household', 'Industrial', 'Power']
        
        # Query from yearly dashboard (Table Query) with granularity='month'
        query = """
        SELECT
            gd.country                                AS "Country",
            gd.sector                                 AS "Sector",
            period                                    AS "_period_sort",

            EXTRACT(YEAR FROM period)::int            AS "Year of Date",

            /* Quarter */
            CASE
                WHEN :granularity IN ('quarter','day')
                THEN 'Q' || EXTRACT(QUARTER FROM period)::int
                ELSE NULL
            END AS "Quarter of Date",

            /* Month */
            CASE
                WHEN :granularity IN ('month','day')
                THEN TO_CHAR(period, 'FMMonth')
                ELSE NULL
            END AS "Month of Date",

            /* Day */
            CASE
                WHEN :granularity = 'day'
                THEN TO_CHAR(period, 'FMMonth FMDD')
                ELSE NULL
            END AS "Day of Date",

            :display_unit                             AS "Unit",
            ROUND(SUM(gd.value), 9)                   AS "Value"

        FROM dev.glng_gas_demand gd
        JOIN dev.dim_country dc
            ON gd.country_id = dc.dim_country_id

        /* 🔹 dynamic time bucket */
        CROSS JOIN LATERAL (
            SELECT
                CASE
                    WHEN :granularity = 'year'    THEN DATE_TRUNC('year', gd.date)
                    WHEN :granularity = 'quarter' THEN DATE_TRUNC('quarter', gd.date)
                    WHEN :granularity = 'month'   THEN DATE_TRUNC('month', gd.date)
                    WHEN :granularity = 'day'     THEN DATE_TRUNC('day', gd.date)
                END AS period
        ) t

        WHERE LOWER(dc.region) = 'europe'
          AND gd.unit = :unit
          AND gd.to_be_deleted = false
          AND gd.sector = ANY(:selected_sectors)
          AND gd.country = ANY(:selected_countries)
          AND EXTRACT(YEAR FROM gd.date) >= 2019
          AND EXTRACT(YEAR FROM gd.date) < 2026

        GROUP BY
            gd.country,
            gd.sector,
            period

        ORDER BY
            "Year of Date" DESC,
            "Quarter of Date",
            "Month of Date",
            "Day of Date",
            "Country",
            "Sector";
        """
        
        params = {
            'granularity': granularity,
            'unit': db_unit,
            'display_unit': unit,
            'selected_sectors': sectors,
            'selected_countries': countries
        }
        
        results = execute_query(query, params)
        df = pd.DataFrame(results)
        
        if df.empty:
            print("Query returned empty results")
            return pd.DataFrame(), pd.DataFrame()
            
        # Process data
        df['Date'] = pd.to_datetime(df['_period_sort'])
        
        # Ensure 'Value' is numeric
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce').fillna(0)
        
        print(f"Loaded SQL data: {len(df)} rows")
        
        return df, pd.DataFrame() 

    except Exception as e:
        print(f"Error loading data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame(), pd.DataFrame()


def prepare_hierarchical_data(df, selection=None):
    """
    Helper to prepare data for the multi-level hierarchical table.
    Ensures Country name is only on the first row of a group.
    """
    if df.empty:
        return [], []
        
    df = df.copy()
    if 'Month' not in df.columns:
        df['Month'] = df['Date'].dt.strftime('%B')
    if 'Year' not in df.columns:
        df['Year'] = df['Date'].dt.year
        
    years = sorted(df['Year'].unique(), reverse=True)
    sector_list = ['Household', 'Industrial', 'Power']
    
    processed_data = []
    
    for country in sorted(df['Country'].unique()):
        country_data = df[df['Country'] == country]
        
        rows = []
        for i, sector in enumerate(sector_list):
            # Only show Country name on the first row of the group
            row = {"Country": country if i == 0 else "", "Sector": sector, "_Country": country}
            for year in years:
                year_sum = 0
                year_months = sorted(df[df['Year'] == year]['Month'].unique(), 
                                   key=lambda m: datetime.strptime(m, '%B').month, reverse=True)
                
                for month in year_months:
                    val = country_data[(country_data['Year'] == year) & 
                                      (country_data['Sector'] == sector) & 
                                      (country_data['Month'] == month)]['Value'].sum()
                    col_id = f"{year}_{month}"
                    row[col_id] = int(round(val)) if val > 0 else ""
                    year_sum += val
                
                row[f"{year}_Total"] = int(round(year_sum)) if year_sum > 0 else ""
            rows.append(row)
        
        # Add Total row for country
        total_row = {"Country": "", "Sector": "Total", "_Country": country}
        for year in years:
            year_sum = 0
            year_months = sorted(df[df['Year'] == year]['Month'].unique(), 
                               key=lambda m: datetime.strptime(m, '%B').month, reverse=True)
            for month in year_months:
                val = country_data[(country_data['Year'] == year) & 
                                  (country_data['Month'] == month)]['Value'].sum()
                col_id = f"{year}_{month}"
                total_row[col_id] = int(round(val)) if val > 0 else ""
                year_sum += val
            total_row[f"{year}_Total"] = int(round(year_sum)) if year_sum > 0 else ""
        rows.append(total_row)
        
        processed_data.extend(rows)
        
    return processed_data, years


def create_layout():
    """Create the European Monthly Demand by Sector layout"""
    df_table, df_chart = load_data()
    
    # Get unique countries for checkboxes
    countries = sorted(df_table['Country'].unique()) if not df_table.empty else []
    
    # Get date range
    if not df_table.empty:
        min_date = df_table['Date'].min()
        max_date = df_table['Date'].max()
    else:
        min_date = pd.Timestamp('2019-01-01')
        max_date = pd.Timestamp('2025-10-01')
    
    # Create initial chart and table data
    initial_fig = go.Figure()
    initial_columns = []
    initial_data = []
    
    # Use table data for chart as load_data returns unified df
    if not df_table.empty:
        if df_chart.empty:
            df_chart = df_table.copy()
            
    if not df_table.empty:
        # Create initial chart using chart data
        chart_data = df_chart.groupby(['Date', 'Sector'])['Value'].sum().reset_index()
        chart_data['Year-Month'] = chart_data['Date'].dt.strftime('%b %Y')
        chart_data['Full-Month'] = chart_data['Date'].dt.strftime('%B %Y')
        chart_data = chart_data.sort_values('Date')
        
        # Define colors for sectors (matching the image exactly)
        sector_colors = {
            'Household': '#006eb0',  # Blue
            'Industrial': '#c5d9a5', # Light Green
            'Power': '#b04e26'       # Brown/Red
        }
        
        # Add bars for each sector in the correct order (bottom to top: Power, Industrial, Household)
        for sector in ['Power', 'Industrial', 'Household']:
            sector_data = chart_data[chart_data['Sector'] == sector]
            if not sector_data.empty:
                initial_fig.add_trace(go.Bar(
                    name=sector,
                    x=sector_data['Year-Month'],
                    y=sector_data['Value'],
                    marker_color=sector_colors.get(sector, '#1f77b4'),
                    customdata=sector_data[['Full-Month', 'Year-Month']],
                    hovertemplate=(
                        f"Sector: <b>{sector}</b><br>"
                        "Month of Date: %{customdata[0]}<br>"
                        "Country: *<br>"
                        "Value: %{y:,.0f}<br>"
                        "Unit: Million Cubic Meter"
                        "<extra></extra>"
                    ),
                    hoverlabel=dict(
                        bgcolor="white",
                        font_size=12,
                        font_family="Arial",
                        font_color="#333"
                    )
                ))
        
        initial_fig.update_layout(
            barmode='stack',
            title='',
            xaxis_title='',
            yaxis_title='Million Cubic Meter',
            height=500,
            margin=dict(l=60, r=20, t=30, b=100),
            showlegend=False,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02,
                bgcolor="rgba(255,255,255,0)",
                bordercolor="rgba(255,255,255,0)",
                borderwidth=0
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
            clickmode='event'
        )
        
        initial_fig.update_xaxes(
            tickangle=-90,
            showgrid=True,
            gridwidth=1,
            gridcolor='#f0f0f0',
            tickfont=dict(size=10, color='#666'),
            showline=True,
            linecolor='#ddd'
        )
        
        initial_fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='#f0f0f0',
            tickformat='.0',
            ticksuffix='K',
            tickprefix='',
            showline=False,
            zeroline=True,
            zerolinecolor='#ddd'
        )
        
        # Adjust Y-axis values
        initial_fig.update_yaxes(tickvals=[0, 10000, 20000, 30000, 40000, 50000, 60000], 
                                ticktext=['0K', '10K', '20K', '30K', '40K', '50K', '60K'])
        
        # Create initial table data
        table_df = df_table.copy()
        if not table_df.empty:
            table_df['Month'] = table_df['Date'].dt.strftime('%B')
            table_df['Year'] = table_df['Date'].dt.year
            
            years = sorted(table_df['Year'].unique(), reverse=True)
            initial_columns = [
                {"name": ["", "Country"], "id": "Country"},
                {"name": ["", "Sector"], "id": "Sector"},
            ]
            
            processed_data, years = prepare_hierarchical_data(table_df)
            
            for year in years:
                year_months = sorted(table_df[table_df['Year'] == year]['Month'].unique(), 
                                   key=lambda m: datetime.strptime(m, '%B').month, reverse=True)
                for month in year_months:
                    initial_columns.append({"name": [str(year), month], "id": f"{year}_{month}"})
                initial_columns.append({"name": [str(year), "Total"], "id": f"{year}_Total"})
            
            initial_data = processed_data
    
    return html.Div([
        # Store components for data
        dcc.Store(id='min-date', data=min_date.isoformat() if not df_table.empty else '2019-01-01'),
        dcc.Store(id='max-date', data=max_date.isoformat() if not df_table.empty else '2025-10-01'),
        
        # Download Components
        dcc.Download(id='download-sector-chart-csv'),
        dcc.Download(id='download-sector-table-csv'),

        dcc.Store(id='sector-demand-selection-store', data={'sector': None, 'x_val': None, 'type': None, 'country': None, 'year': None}),
        dcc.Store(id='europe-table-highlight-state'),
        
        # New Stores for Granularity
        dcc.Store(id='sector-granularity-store', data='month'),
        dcc.Store(id='sector-table-granularity-store', data='month'),
        
        # Data Caching Stores (Initialized with df_table)
        dcc.Store(id='sector-chart-data-store', data=df_table.to_dict('records') if not df_table.empty else []),
        dcc.Store(id='sector-table-data-store', data=df_table.to_dict('records') if not df_table.empty else []),

        html.Div(id='europe-table-dummy-output', style={'display': 'none'}),
        dcc.Input(id='sector-demand-header-click-input', style={'display': 'none'}),
        
        # Main container
        html.Div([
            # Main content area (left side)
            html.Div([
                # Chart Area
                html.Div([
                    html.Div([
                        html.H3("Monthly Gas Demand by Sector", style={
                            'color': '#f45d2d', 
                            'margin': '0',
                            'fontSize': '24px',
                            'fontWeight': 'normal',
                            'fontFamily': 'Georgia, serif'
                        }),
                        html.Button(
                            'Export to CSV',
                            id='btn-export-chart',
                            n_clicks=0,
                            style={
                                'backgroundColor': 'white', 'color': '#2c3e50', 'border': '1px solid #dee2e6',
                                'padding': '5px 15px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '13px',
                                'marginLeft': '15px'
                            }
                        )
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px'}),
                    
                    # Chart Granularity Buttons
                    html.Div([
                        html.Div([
                            html.Span("Year of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                            html.Button('+', id='sector-toggle-year-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                        ], style=GRAN_BTN_CONTAINER_STYLE),
                        html.Div([
                            html.Span("Quarter of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                            html.Button('+', id='sector-toggle-quarter-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                        ], style=GRAN_BTN_CONTAINER_STYLE),
                        html.Div([
                            html.Span("Month of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                            html.Button('-', id='sector-toggle-month-btn', n_clicks=0, style=GRAN_BTN_ACTIVE)
                        ], style=GRAN_BTN_CONTAINER_STYLE),
                        html.Div([
                            html.Span("Day of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                            html.Button('+', id='sector-toggle-day-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                        ], style=GRAN_BTN_CONTAINER_STYLE),
                    ], style={'display': 'flex', 'padding': '10px 0', 'marginBottom': '10px', 'backgroundColor': '#fff'}),

                    dcc.Loading(
                        id="loading-chart",
                        type="graph",
                        color="#f45d2d",
                        children=dcc.Graph(
                            id='sector-demand-chart',
                            figure=initial_fig,
                            style={'height': '500px'},
                            config={'displayModeBar': True, 'displaylogo': False}
                        )
                    )
                ], style={'marginBottom': '30px'}),
                
                # Data Table Area
                html.Div([
                    # Table Header with Export
                    html.Div([
                        html.H4("Sector Demand Data", style={'margin': '0', 'color': '#333', 'display': 'none'}), # Hidden title for spacing/a11y if needed
                        html.Button(
                            'Export to CSV',
                            id='btn-export-table',
                            n_clicks=0,
                            style={
                                'backgroundColor': 'white', 'color': '#2c3e50', 'border': '1px solid #dee2e6',
                                'padding': '5px 15px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '13px',
                                'marginBottom': '10px',
                                'display': 'inline-block' 
                            }
                        )
                    ], style={'textAlign': 'right'}),

                    # Table Granularity Buttons
                    html.Div([
                        html.Div([
                            html.Span("Year of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                            html.Button('+', id='sector-table-toggle-year-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                        ], style=GRAN_BTN_CONTAINER_STYLE),
                        html.Div([
                            html.Span("Quarter of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                            html.Button('+', id='sector-table-toggle-quarter-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                        ], style=GRAN_BTN_CONTAINER_STYLE),
                        html.Div([
                            html.Span("Month of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                            html.Button('-', id='sector-table-toggle-month-btn', n_clicks=0, style=GRAN_BTN_ACTIVE)
                        ], style=GRAN_BTN_CONTAINER_STYLE),
                        html.Div([
                            html.Span("Day of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                            html.Button('+', id='sector-table-toggle-day-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                        ], style=GRAN_BTN_CONTAINER_STYLE),
                    ], style={'display': 'flex', 'padding': '10px 0', 'marginBottom': '10px', 'backgroundColor': '#fff'}),

                    dcc.Loading(
                        id="loading-table",
                        type="circle",
                        color="#f45d2d",
                        children=dash_table.DataTable(
                            id='sector-demand-table',
                            columns=initial_columns,
                            data=initial_data,
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
                                'padding': '0px 5px',
                                'fontSize': '11px',
                                'fontFamily': 'Arial, sans-serif',
                                'border': 'none', 
                                'minWidth': '70px',
                                'backgroundColor': '#fff',
                                'color': '#777',
                                'height': 'auto'
                            },
                            style_as_list_view=False,
                        )
                    )
                ], id='europe-gas-demand-table-container')
                
            ], style={
                'marginRight': '300px',
                'padding': '20px',
                'backgroundColor': '#ffffff',
                'fontFamily': 'Arial, sans-serif'
            }),
            
            # Right sidebar with controls
            html.Div([
                # Date Range
                html.Div([
                    html.Label("Date", style={'fontWeight': 'bold', 'marginBottom': '10px', 'display': 'block', 'color': '#333', 'fontSize': '14px'}),
                    html.Div([
                        html.Span("1/1/2019", style={'fontSize': '12px', 'color': '#666'}),
                        html.Span("10/1/2025", style={'fontSize': '12px', 'color': '#666', 'float': 'right'})
                    ], style={'marginBottom': '8px'}),
                    dcc.RangeSlider(
                        id='date-range-slider',
                        min=0,
                        max=100,
                        value=[0, 100],
                        marks={0: '', 100: ''},
                        tooltip={"placement": "bottom", "always_visible": False},
                        className='custom-range-slider'
                    )
                ], style={'marginBottom': '25px'}),
                
                # Unit Selection
                html.Div([
                    html.Label("Unit", style={'fontWeight': 'bold', 'marginBottom': '10px', 'display': 'block', 'color': '#333', 'fontSize': '14px'}),
                    dcc.RadioItems(
                        id='unit-selector',
                        options=[
                            {'label': ' Gigawatt-hour', 'value': 'GWh'},
                            {'label': ' Million Cubic Meter', 'value': 'Million Cubic Meter'}
                        ],
                        value='Million Cubic Meter',
                        style={'marginBottom': '15px', 'fontSize': '13px'},
                        inputStyle={"marginRight": "8px", "marginLeft": "0px"}
                    )
                ], style={'marginBottom': '25px'}),
                
                # Sector Legend
                html.Div([
                    html.Label("Sector", style={'fontWeight': 'bold', 'marginBottom': '10px', 'display': 'block', 'color': '#333', 'fontSize': '14px'}),
                    html.Div([
                        html.Div([
                            html.Div(style={'width': '20px', 'height': '15px', 'backgroundColor': '#006eb0', 'display': 'inline-block', 'marginRight': '8px', 'verticalAlign': 'middle'}),
                            html.Span("Household", style={'fontSize': '13px', 'color': '#666'})
                        ], style={'marginBottom': '6px'}),
                        html.Div([
                            html.Div(style={'width': '20px', 'height': '15px', 'backgroundColor': '#c5d9a5', 'display': 'inline-block', 'marginRight': '8px', 'verticalAlign': 'middle'}),
                            html.Span("Industrial", style={'fontSize': '13px', 'color': '#666'})
                        ], style={'marginBottom': '6px'}),
                        html.Div([
                            html.Div(style={'width': '20px', 'height': '15px', 'backgroundColor': '#b04e26', 'display': 'inline-block', 'marginRight': '8px', 'verticalAlign': 'middle'}),
                            html.Span("Power", style={'fontSize': '13px', 'color': '#666'})
                        ])
                    ])
                ], style={'marginBottom': '25px'}),
                
                # Country Selection
                html.Div([
                    html.Label("Country", style={'fontWeight': 'bold', 'marginBottom': '10px', 'display': 'block', 'color': '#333', 'fontSize': '14px'}),
                    html.Div([
                        dcc.Checklist(
                            id='country-checklist',
                            options=[{'label': ' (All)', 'value': 'All'}] + [{'label': f' {country}', 'value': country} for country in countries],
                            value=['All'] + countries,
                            style={'maxHeight': '280px', 'overflowY': 'auto', 'fontSize': '13px'},
                            inputStyle={"marginRight": "6px", "marginLeft": "0px"}
                        )
                    ])
                ], style={'marginBottom': '25px'}),
                
                # Highlight Country
                html.Div([
                    html.Label("Highlight Country", style={'fontWeight': 'bold', 'marginBottom': '10px', 'display': 'block', 'color': '#333', 'fontSize': '14px'}),
                    dcc.Dropdown(
                        id='highlight-country',
                        options=[{'label': country, 'value': country} for country in countries],
                        placeholder="Highlight Country",
                        style={'fontSize': '13px'}
                    )
                ])
                
            ], style={
                'width': '280px', 
                'padding': '15px', 
                'backgroundColor': '#f8f9fa',
                'height': '100vh',
                'overflowY': 'auto',
                'position': 'fixed',
                'right': '0',
                'top': '0',
                'borderLeft': '1px solid #dee2e6',
                'fontFamily': 'Arial, sans-serif'
            })
            
        ])
    ], className='tab-content', style={'backgroundColor': '#ffffff', 'minHeight': '100vh'})


def register_callbacks(dash_app, server):
    """Register callbacks for the European Monthly Demand by Sector dashboard"""
    
    # Chart Granularity Toggle
    @dash_app.callback(
        [Output('sector-granularity-store', 'data'),
         Output('sector-toggle-year-btn', 'children'),
         Output('sector-toggle-quarter-btn', 'children'),
         Output('sector-toggle-month-btn', 'children'),
         Output('sector-toggle-day-btn', 'children'),
         Output('sector-toggle-year-btn', 'style'),
         Output('sector-toggle-quarter-btn', 'style'),
         Output('sector-toggle-month-btn', 'style'),
         Output('sector-toggle-day-btn', 'style')],
        [Input('sector-toggle-year-btn', 'n_clicks'),
         Input('sector-toggle-quarter-btn', 'n_clicks'),
         Input('sector-toggle-month-btn', 'n_clicks'),
         Input('sector-toggle-day-btn', 'n_clicks')],
        [State('sector-granularity-store', 'data')]
    )
    def toggle_granularity(y_c, q_c, m_c, d_c, current_gran):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
        btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
        new_gran = current_gran
        
        if btn_id == 'sector-toggle-year-btn': new_gran = 'year'
        elif btn_id == 'sector-toggle-quarter-btn': new_gran = 'quarter'
        elif btn_id == 'sector-toggle-month-btn': new_gran = 'month'
        elif btn_id == 'sector-toggle-day-btn': new_gran = 'day'
        
        return (
            new_gran,
            '-' if new_gran == 'year' else '+',
            '-' if new_gran == 'quarter' else '+',
            '-' if new_gran == 'month' else '+',
            '-' if new_gran == 'day' else '+',
            GRAN_BTN_ACTIVE if new_gran == 'year' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'quarter' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'month' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'day' else GRAN_BTN_INACTIVE
        )

    # Table Granularity Toggle
    @dash_app.callback(
        [Output('sector-table-granularity-store', 'data'),
         Output('sector-table-toggle-year-btn', 'children'),
         Output('sector-table-toggle-quarter-btn', 'children'),
         Output('sector-table-toggle-month-btn', 'children'),
         Output('sector-table-toggle-day-btn', 'children'),
         Output('sector-table-toggle-year-btn', 'style'),
         Output('sector-table-toggle-quarter-btn', 'style'),
         Output('sector-table-toggle-month-btn', 'style'),
         Output('sector-table-toggle-day-btn', 'style')],
        [Input('sector-table-toggle-year-btn', 'n_clicks'),
         Input('sector-table-toggle-quarter-btn', 'n_clicks'),
         Input('sector-table-toggle-month-btn', 'n_clicks'),
         Input('sector-table-toggle-day-btn', 'n_clicks')],
        [State('sector-table-granularity-store', 'data')]
    )
    def toggle_table_granularity(y_c, q_c, m_c, d_c, current_gran):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
        btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
        new_gran = current_gran
        
        if btn_id == 'sector-table-toggle-year-btn': new_gran = 'year'
        elif btn_id == 'sector-table-toggle-quarter-btn': new_gran = 'quarter'
        elif btn_id == 'sector-table-toggle-month-btn': new_gran = 'month'
        elif btn_id == 'sector-table-toggle-day-btn': new_gran = 'day'
        
        return (
            new_gran,
            '-' if new_gran == 'year' else '+',
            '-' if new_gran == 'quarter' else '+',
            '-' if new_gran == 'month' else '+',
            '-' if new_gran == 'day' else '+',
            GRAN_BTN_ACTIVE if new_gran == 'year' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'quarter' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'month' else GRAN_BTN_INACTIVE,
            GRAN_BTN_ACTIVE if new_gran == 'day' else GRAN_BTN_INACTIVE
        )

    # FETCH CHART DATA (DB ACCESS)
    @dash_app.callback(
        Output('sector-chart-data-store', 'data'),
        [Input('unit-selector', 'value'),
         Input('sector-granularity-store', 'data')]
    )
    def fetch_chart_data(unit, granularity):
        if not granularity: granularity = 'month'
        df, _ = load_data(unit=unit, granularity=granularity)
        return df.to_dict('records')

    # FETCH TABLE DATA (DB ACCESS)
    @dash_app.callback(
        Output('sector-table-data-store', 'data'),
        [Input('unit-selector', 'value'),
         Input('sector-table-granularity-store', 'data')]
    )
    def fetch_table_data(unit, granularity):
        if not granularity: granularity = 'month'
        df, _ = load_data(unit=unit, granularity=granularity)
        return df.to_dict('records')

    # UPDATE CHART (CLIENT SIDE)
    @dash_app.callback(
        Output('sector-demand-chart', 'figure'),
        [Input('date-range-slider', 'value'),
         Input('unit-selector', 'value'),
         Input('country-checklist', 'value'),
         Input('highlight-country', 'value'),
         Input('min-date', 'data'),
         Input('max-date', 'data'),
         Input('sector-demand-selection-store', 'data'),
         Input('sector-granularity-store', 'data'),
         Input('sector-chart-data-store', 'data')]
    )
    def update_chart(date_range, unit, selected_countries, highlight_country, min_date_str, max_date_str, selection, granularity, chart_data):
        """Update chart based on filters and granularity"""
        if not granularity: granularity = 'month'
        
        if not chart_data:
            return go.Figure()

        df_to_use = pd.DataFrame(chart_data)
        # Reconstruct Date
        if 'Date' in df_to_use.columns:
            df_to_use['Date'] = pd.to_datetime(df_to_use['Date'])
        
        # Convert date strings back to datetime
        min_date = pd.to_datetime(min_date_str)
        max_date = pd.to_datetime(max_date_str)
        
        # Filter by date range (using Date column created in load_data)
        date_range_start = min_date + (max_date - min_date) * (date_range[0] / 100)
        date_range_end = min_date + (max_date - min_date) * (date_range[1] / 100)
        
        df_filtered = df_to_use[
            (df_to_use['Date'] >= date_range_start) & 
            (df_to_use['Date'] <= date_range_end)
        ].copy()
        
        # Handle country filtering
        if not selected_countries or 'All' in selected_countries:
            pass
        else:
            df_filtered = df_filtered[df_filtered['Country'].isin(selected_countries)]
        
        # Create a display label based on granularity
        if granularity == 'year':
            df_filtered['TimeLabel'] = df_filtered['Year of Date'].astype(str)
        elif granularity == 'quarter':
            df_filtered['TimeLabel'] = df_filtered['Year of Date'].astype(str) + ' ' + df_filtered['Quarter of Date']
        elif granularity == 'month':
             df_filtered['TimeLabel'] = df_filtered['Date'].dt.strftime('%b %Y')
        elif granularity == 'day':
             df_filtered['TimeLabel'] = df_filtered['Date'].dt.strftime('%d %b %Y')
        else:
             df_filtered['TimeLabel'] = df_filtered['Date'].dt.strftime('%b %Y')
             
        # Group by TimeLabel and Sector
        if 'TimeLabel' not in df_filtered.columns:
             df_filtered['TimeLabel'] = df_filtered['Year of Date'].astype(str) # Fallback

        chart_grp = df_filtered.groupby(['TimeLabel', 'Date', 'Sector'])['Value'].sum().reset_index()
        chart_grp = chart_grp.sort_values('Date')
        
        fig = go.Figure()
        
        sector_colors = {
            'Household': '#006eb0',
            'Industrial': '#c5d9a5', 
            'Power': '#b04e26'
        }
        
        sector_colors_dimmed = {
            'Household': 'rgba(0, 110, 176, 0.15)',
            'Industrial': 'rgba(197, 217, 165, 0.15)',
            'Power': 'rgba(176, 78, 38, 0.15)'
        }
        
        for sector in ['Power', 'Industrial', 'Household']:
            sector_data = chart_grp[chart_grp['Sector'] == sector]
            if not sector_data.empty:
                
                # --- PREPARE SELECTION STATE ---
                selected_sector = selection.get('sector') if selection else None
                selected_x = selection.get('x_val') if selection else None
                
                # Determine Selection Mode
                # Mode A: Point Highlight (Sector + Time)
                is_point_mode = (selected_sector is not None and selected_x is not None)
                
                # Mode B: Time Highlight (Time Only - from Table Column Click)
                is_time_mode = (selected_sector is None and selected_x is not None)
                
                # Mode C: Sector Highlight (Sector Only - from Legend/row click)
                is_sector_mode = (selected_sector is not None and selected_x is None)
                
                has_selection = (is_point_mode or is_time_mode or is_sector_mode)
                
                marker_colors = []
                marker_line_widths = []
                marker_line_colors = []
                custom_data_list = []
                
                for _, row in sector_data.iterrows():
                    time_label = str(row['TimeLabel'])
                    # Create robust customdata: [TimeLabel, Sector, Value]
                    # We put TimeLabel first for easy access
                    c_data = [time_label, sector, row['Value']]
                    custom_data_list.append(c_data)
                    
                    base_color = sector_colors.get(sector, '#1f77b4')
                    dimmed_color = sector_colors_dimmed.get(sector, 'rgba(0,0,0,0.1)')
                    
                    is_selected = False
                    
                    if not has_selection:
                        is_selected = True # All visible if no selection
                    else:
                        if is_point_mode:
                            # Must match BOTH sector and time
                            if str(selected_sector) == str(sector) and str(selected_x) == time_label:
                                is_selected = True
                        elif is_time_mode:
                            # Must match Time only
                            if str(selected_x) == time_label:
                                is_selected = True
                        elif is_sector_mode:
                            # Must match Sector only
                            if str(selected_sector) == str(sector):
                                is_selected = True
                    
                    if is_selected:
                        marker_colors.append(base_color)
                        # If we are in a specific selection mode, add border to the selected item(s)
                        # For Sector Mode, we might not want borders on everything, just full color.
                        # For Point Mode, definitely border.
                        if is_point_mode:
                             marker_line_widths.append(3)
                             marker_line_colors.append('black')
                        else:
                             marker_line_widths.append(0)
                             marker_line_colors.append('rgba(0,0,0,0)')
                    else:
                        marker_colors.append(dimmed_color)
                        marker_line_widths.append(0)
                        marker_line_colors.append('rgba(0,0,0,0)')

                country_label = highlight_country if highlight_country else "*"
                if not highlight_country and selected_countries and 'All' not in selected_countries:
                        if len(selected_countries) == 1:
                            country_label = selected_countries[0]

                fig.add_trace(go.Bar(
                    name=sector,
                    x=sector_data['TimeLabel'],
                    y=sector_data['Value'],
                    customdata=custom_data_list,
                    marker=dict(
                        color=marker_colors,
                        line=dict(width=marker_line_widths, color=marker_line_colors)
                    ),
                    hovertemplate=(
                        f"Sector: <b>{sector}</b><br>"
                        f"Period: %{{x}}<br>"
                        f"Country: {country_label}<br>"
                        f"Value: %{{y:,.0f}}<br>"
                        f"Unit: {unit}"
                        "<extra></extra>"
                    ),
                    hoverlabel=dict(bgcolor="white", font_size=12, font_family="Arial", font_color="#333")
                ))
        
        fig.update_layout(
            barmode='stack',
            title='',
            xaxis_title='',
            yaxis_title=unit,
            height=500,
            margin=dict(l=60, r=20, t=30, b=100),
            showlegend=False,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02,
                bgcolor="rgba(255,255,255,0)",
                bordercolor="rgba(255,255,255,0)",
                borderwidth=0
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
            clickmode='event'
        )
        
        fig.update_xaxes(
            tickangle=-90,
            showgrid=True,
            gridwidth=1,
            gridcolor='#f0f0f0',
            tickfont=dict(size=10, color='#666'),
            showline=True,
            linecolor='#ddd'
        )
        
        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='#f0f0f0',
            tickformat='.0',
            ticksuffix='K' if unit == 'Million Cubic Meter' else '',
            showline=False,
            zeroline=True,
            zerolinecolor='#ddd'
        )
        
        if unit == 'Million Cubic Meter':
            fig.update_yaxes(tickvals=[0, 10000, 20000, 30000, 40000, 50000, 60000], 
                            ticktext=['0K', '10K', '20K', '30K', '40K', '50K', '60K'])
                            
        return fig

    # UPDATE TABLE (CLIENT SIDE)
    @dash_app.callback(
        [Output('sector-demand-table', 'columns'),
         Output('sector-demand-table', 'data'),
         Output('sector-demand-table', 'style_data_conditional'),
         Output('sector-demand-table', 'style_header_conditional')],
        [Input('date-range-slider', 'value'),
         Input('unit-selector', 'value'),
         Input('country-checklist', 'value'),
         Input('highlight-country', 'value'),
         Input('min-date', 'data'),
         Input('max-date', 'data'),
         Input('sector-demand-selection-store', 'data'),
         Input('sector-table-granularity-store', 'data'),
         Input('sector-table-data-store', 'data')]
    )
    def update_table(date_range, unit, selected_countries, highlight_country, min_date_str, max_date_str, selection, granularity, table_data):
        """Update table based on filters and table granularity"""
        if not granularity: granularity = 'month'

        if not table_data:
            return [], [], [], []
            
        df_table = pd.DataFrame(table_data)
        if 'Date' in df_table.columns:
            df_table['Date'] = pd.to_datetime(df_table['Date'])

        # Convert date strings back to datetime
        min_date = pd.to_datetime(min_date_str)
        max_date = pd.to_datetime(max_date_str)
        
        date_range_start = min_date + (max_date - min_date) * (date_range[0] / 100)
        date_range_end = min_date + (max_date - min_date) * (date_range[1] / 100)
        
        df_filtered = df_table[
            (df_table['Date'] >= date_range_start) & 
            (df_table['Date'] <= date_range_end)
        ].copy()
        
        if not selected_countries or 'All' in selected_countries:
            pass
        else:
            df_filtered = df_filtered[df_filtered['Country'].isin(selected_countries)]
            
        if df_filtered.empty:
            return [], [], [], []

        if 'Year' not in df_filtered.columns:
            df_filtered['Year'] = df_filtered['Date'].dt.year
            
        if granularity == 'year':
             df_filtered['Month'] = 'Year'
        elif granularity == 'quarter':
             df_filtered['Month'] = df_filtered['Quarter of Date']
        elif granularity == 'month':
             df_filtered['Month'] = df_filtered['Date'].dt.strftime('%B')
        elif granularity == 'day':
             df_filtered['Month'] = df_filtered['Date'].dt.strftime('%d %b')
        else:
             df_filtered['Month'] = df_filtered['Date'].dt.strftime('%B')
        
        years = sorted(df_filtered['Year'].unique(), reverse=True)
        sector_list = ['Household', 'Industrial', 'Power']
        processed_data = []
        
        columns = [
            {"name": ["", "Country"], "id": "Country"},
            {"name": ["", "Sector"], "id": "Sector"},
        ]
        
        data_col_ids = []
        
        for year in years:
            year_df = df_filtered[df_filtered['Year'] == year]
            if year_df.empty: continue
            
            if granularity == 'month':
                sub_periods = sorted(year_df['Month'].unique(), key=lambda m: datetime.strptime(m, '%B').month, reverse=True)
            elif granularity == 'day':
                sub_periods = sorted(year_df['Month'].unique(), key=lambda d: datetime.strptime(d + f" {year}", '%d %b %Y'), reverse=True)
            else:
                 sub_periods = sorted(year_df['Month'].unique(), reverse=True)
            
            for sp in sub_periods:
                if granularity == 'year':
                     col_id = f"{year}_Total"
                else:
                     col_id = f"{year}_{sp}"
                     columns.append({"name": [str(year), sp], "id": col_id})
                     data_col_ids.append(col_id)
            
            columns.append({"name": [str(year), "Total"], "id": f"{year}_Total"})
            data_col_ids.append(f"{year}_Total")

        for country in sorted(df_filtered['Country'].unique()):
            country_data = df_filtered[df_filtered['Country'] == country]
            
            rows = []
            for i, sector in enumerate(sector_list):
                row = {"Country": country if i == 0 else "", "Sector": sector, "_Country": country}
                
                for year in years:
                    year_sum = country_data[(country_data['Year'] == year) & (country_data['Sector'] == sector)]['Value'].sum()
                    
                    year_df_c = country_data[country_data['Year'] == year]
                    sub_df = year_df_c[year_df_c['Sector'] == sector]
                    
                    for _, r in sub_df.iterrows():
                        sp = r['Month']
                        val = r['Value']
                        if granularity != 'year':
                            col_id = f"{year}_{sp}"
                            row[col_id] = int(round(val)) if val > 0 else ""

                    row[f"{year}_Total"] = int(round(year_sum)) if year_sum > 0 else ""
                
                rows.append(row)
            
            total_row = {"Country": "", "Sector": "Total", "_Country": country}
            for year in years:
                 year_sum = country_data[(country_data['Year'] == year)]['Value'].sum()
                 total_row[f"{year}_Total"] = int(round(year_sum)) if year_sum > 0 else ""
                 
                 year_df_c = country_data[country_data['Year'] == year]
                 if granularity != 'year':
                     start_agg = year_df_c.groupby('Month')['Value'].sum()
                     for sp, val in start_agg.items():
                         col_id = f"{year}_{sp}"
                         total_row[col_id] = int(round(val)) if val > 0 else ""

            rows.append(total_row)
            processed_data.extend(rows)

        style_data_conditional = [
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f2f2f2'},
            {'if': {'column_id': 'Country'}, 'textAlign': 'left', 'fontWeight': 'bold', 'minWidth': '120px', 'color': '#333'},
            {'if': {'column_id': 'Sector'}, 'textAlign': 'left', 'paddingLeft': '10px', 'minWidth': '100px', 'borderRight': '1px solid #ccc'},
            {'if': {'column_id': [f"{y}_Total" for y in years]}, 'borderRight': '1px solid #ccc'}
        ]

        has_highlight = False
        highlight_rows_query = []
        highlight_cols = []
        
        active_country = None
        if highlight_country:
            active_country = highlight_country
            has_highlight = True
            highlight_rows_query.append(f'{{_Country}} eq "{active_country}"')
        elif selection:
            sel_type = selection.get('type')
            if sel_type == 'table-country':
                active_country = selection.get('country')
                if active_country:
                    has_highlight = True
                    highlight_rows_query.append(f'{{_Country}} eq "{active_country}"')
            elif sel_type == 'table-sector':
                active_sector = selection.get('sector')
                active_country = selection.get('country')
                if active_sector:
                    has_highlight = True
                    if active_country:
                        highlight_rows_query.append(f'{{_Country}} eq "{active_country}" && {{Sector}} eq "{active_sector}"')
                    else:
                        highlight_rows_query.append(f'{{Sector}} eq "{active_sector}"')
            elif sel_type == 'chart':
                x_val = selection.get('x_val')
                sec = selection.get('sector')
                if sec:
                    highlight_rows_query.append(f'{{Sector}} eq "{sec}"')
                    has_highlight = True

        if has_highlight:
             style_data_conditional.append({'if': {'column_id': data_col_ids}, 'color': '#ccc'})
        
        for query in highlight_rows_query:
            style_data_conditional.append({'if': {'filter_query': query}, 'backgroundColor': '#cfe8ef', 'color': 'black'})
            
        return columns, processed_data, style_data_conditional, []

        return columns, processed_data, style_data_conditional, []

    # EXPORT CHART DATA
    @dash_app.callback(
        Output('download-sector-chart-csv', 'data'),
        Input('btn-export-chart', 'n_clicks'),
        [State('date-range-slider', 'value'),
         State('unit-selector', 'value'),
         State('country-checklist', 'value'),
         State('min-date', 'data'),
         State('max-date', 'data'),
         State('sector-granularity-store', 'data'),
         State('sector-chart-data-store', 'data')],
        prevent_initial_call=True
    )
    def export_chart_data(n_clicks, date_range, unit, selected_countries, min_date_str, max_date_str, granularity, chart_data):
        if not n_clicks:
            return no_update
            
        if not chart_data:
            return no_update

        df_to_use = pd.DataFrame(chart_data)
        if 'Date' in df_to_use.columns:
            df_to_use['Date'] = pd.to_datetime(df_to_use['Date'])
        
        min_date = pd.to_datetime(min_date_str)
        max_date = pd.to_datetime(max_date_str)
        
        date_range_start = min_date + (max_date - min_date) * (date_range[0] / 100)
        date_range_end = min_date + (max_date - min_date) * (date_range[1] / 100)
        
        df_filtered = df_to_use[
            (df_to_use['Date'] >= date_range_start) & 
            (df_to_use['Date'] <= date_range_end)
        ].copy()
        
        if selected_countries and 'All' not in selected_countries:
            df_filtered = df_filtered[df_filtered['Country'].isin(selected_countries)]
            
        # Format for export
        df_export = df_filtered.copy()
        df_export['Date'] = df_export['Date'].dt.strftime('%Y-%m-%d')
        
        filename = f"gas_demand_chart_data_{unit.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        return dcc.send_data_frame(df_export.to_csv, filename, index=False)

    # EXPORT TABLE DATA
    @dash_app.callback(
        Output('download-sector-table-csv', 'data'),
        Input('btn-export-table', 'n_clicks'),
        [State('date-range-slider', 'value'),
         State('unit-selector', 'value'),
         State('country-checklist', 'value'),
         State('min-date', 'data'),
         State('max-date', 'data'),
         State('sector-table-granularity-store', 'data'),
         State('sector-table-data-store', 'data')],
        prevent_initial_call=True
    )
    def export_table_data(n_clicks, date_range, unit, selected_countries, min_date_str, max_date_str, granularity, table_data):
        if not n_clicks:
            return no_update

        if not table_data:
            return no_update
            
        df_table = pd.DataFrame(table_data)
        if 'Date' in df_table.columns:
            df_table['Date'] = pd.to_datetime(df_table['Date'])

        min_date = pd.to_datetime(min_date_str)
        max_date = pd.to_datetime(max_date_str)
        
        date_range_start = min_date + (max_date - min_date) * (date_range[0] / 100)
        date_range_end = min_date + (max_date - min_date) * (date_range[1] / 100)
        
        df_filtered = df_table[
            (df_table['Date'] >= date_range_start) & 
            (df_table['Date'] <= date_range_end)
        ].copy()
        
        if selected_countries and 'All' not in selected_countries:
            df_filtered = df_filtered[df_filtered['Country'].isin(selected_countries)]

        # Determine granularity for column structure logic or just dump raw filtered data
        # For simplicity and utility, exporting the raw filtered data (long format) is usually better for analysis
        # If user wants the pivot view (as seen in table), that requires complex reconstruction.
        # User request usually implies "the data behind the view".
        
        df_export = df_filtered.copy()
        df_export['Date'] = df_export['Date'].dt.strftime('%Y-%m-%d')
        
        filename = f"gas_demand_table_data_{unit.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        return dcc.send_data_frame(df_export.to_csv, filename, index=False)

    # Unified selection callback handler
    @dash_app.callback(
        Output('sector-demand-selection-store', 'data'),
        [Input('sector-demand-chart', 'clickData'),
         Input('sector-demand-table', 'active_cell'),
         Input('sector-demand-header-click-input', 'value')],
        [State('sector-demand-table', 'data'),
         State('sector-demand-selection-store', 'data')],
        prevent_initial_call=True
    )
    def handle_selection(click_data, active_cell, header_val, table_data, current_selection):
        from dash import ctx
        if not ctx.triggered:
            return current_selection
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        new_selection = current_selection.copy() if current_selection else {'sector': None, 'x_val': None, 'type': None, 'country': None, 'year': None}
        
        if trigger_id == 'sector-demand-chart' and click_data:
            print(f"DEBUG APP: Chart click received")
            point = click_data['points'][0]
            
            # Use customdata if available [TimeLabel, Sector, Value]
            custom_data = point.get('customdata', [])
            
            sector = None
            x_val = None
            
            if custom_data and len(custom_data) >= 2:
                x_val = custom_data[0] # TimeLabel
                sector = custom_data[1] # Sector
            else:
                 # Fallback
                if point.get('legendgroup'):
                    sector = str(point.get('legendgroup')).strip()
                elif point.get('name'):
                    sector = str(point.get('name')).strip()
                x_val = point.get('x')
            
            if not sector or not x_val:
                return new_selection
                
            # Toggle check
            if str(current_selection.get('sector')) == str(sector) and str(current_selection.get('x_val')) == str(x_val):
                return {'sector': None, 'x_val': None, 'type': None, 'country': None, 'year': None}
                
            return {'sector': sector, 'x_val': x_val, 'type': 'chart', 'country': None, 'year': None}
            
        elif trigger_id == 'sector-demand-table' and active_cell:
            col_id = active_cell['column_id']
            row_idx = active_cell['row']
            
            if row_idx is not None and row_idx < len(table_data):
                row_data = table_data[row_idx]
                country = row_data.get('_Country') # Use hidden _Country
                sector = row_data.get('Sector')
                
                if col_id == 'Country':
                    if current_selection.get('country') == country and current_selection.get('type') == 'table-country':
                        return {'sector': None, 'x_val': None, 'type': None, 'country': None, 'year': None}
                    return {'sector': None, 'x_val': None, 'type': 'table-country', 'country': country, 'year': None}
                elif col_id == 'Sector':
                    if current_selection.get('country') == country and current_selection.get('sector') == sector and current_selection.get('type') == 'table-sector':
                        return {'sector': None, 'x_val': None, 'type': None, 'country': None, 'year': None}
                    return {'sector': sector, 'x_val': None, 'type': 'table-sector', 'country': country, 'year': None}
                else:
                    # Specific cell click -> Column highlight
                    if current_selection.get('x_val') == col_id and current_selection.get('type') == 'table-column':
                        return {'sector': None, 'x_val': None, 'type': None, 'country': None, 'year': None}
                    return {'sector': None, 'x_val': col_id, 'type': 'table-column', 'country': None, 'year': None}
                    
        elif trigger_id == 'sector-demand-header-click-input' and header_val:
            parts = header_val.split('|')
            if len(parts) >= 2:
                h_type = parts[0]
                h_val = parts[1]
                
                if h_type == 'year':
                    if current_selection.get('year') == h_val and current_selection.get('type') == 'table-year':
                        return {'sector': None, 'x_val': None, 'type': None, 'country': None, 'year': None}
                    return {'sector': None, 'x_val': None, 'type': 'table-year', 'country': None, 'year': h_val}
                elif h_type == 'month':
                    if current_selection.get('x_val') == h_val and current_selection.get('type') == 'table-column':
                        return {'sector': None, 'x_val': None, 'type': None, 'country': None, 'year': None}
                    return {'sector': None, 'x_val': h_val, 'type': 'table-column', 'country': None, 'year': None}
                    
        return new_selection

    # Clientside Callback for Header Clicks
    dash_app.clientside_callback(
        '''
        function(n_clicks, tableId) {
            try {
                if (!tableId) return window.dash_clientside.no_update;
                
                const table = document.getElementById(tableId);
                if (!table) return window.dash_clientside.no_update;
                
                const callbackInput = document.getElementById('sector-demand-header-click-input');
                
                // Helper to attach listeners safely
                function attachListeners() {
                    const ths = table.querySelectorAll('th');
                    ths.forEach(th => {
                        if (th.dataset.clickListenerAttached === 'true') return;
                        th.dataset.clickListenerAttached = 'true';
                        
                        th.style.cursor = 'pointer'; // Make it look clickable
                        
                        th.addEventListener('click', function(e) {
                            e.stopPropagation();
                            
                            const text = th.innerText.trim();
                            const colId = th.getAttribute('data-dash-column');
                            
                            // Detect Year (4 digits, possibly in merged header)
                            if (/^20\\d{2}$/.test(text)) {
                                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                                nativeInputValueSetter.call(callbackInput, 'year|' + text);
                                callbackInput.dispatchEvent(new Event('input', { bubbles: true }));
                                return;
                            }
                            
                            // Detect Month/Column (Must have ID and not be Country/Sector)
                            if (colId && colId !== 'Country' && colId !== 'Sector') {
                                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                                nativeInputValueSetter.call(callbackInput, 'month|' + colId);
                                callbackInput.dispatchEvent(new Event('input', { bubbles: true }));
                            }
                        });
                    });
                }
                
                // Attach now
                attachListeners();
                
                // Attach on mutation (if pagination or updates rebuild DOM)
                // We use a simple recurring check or observer
                if (!window.europeGasHeaderObserver) {
                    window.europeGasHeaderObserver = new MutationObserver((mutations) => {
                        attachListeners();
                    });
                    window.europeGasHeaderObserver.observe(table, { childList: true, subtree: true });
                }
                
            } catch (e) { console.error(e); }
            return window.dash_clientside.no_update;
        }
        ''',
        Output('sector-demand-header-click-input', 'style'), 
        [Input('sector-demand-table', 'id')]
    )
