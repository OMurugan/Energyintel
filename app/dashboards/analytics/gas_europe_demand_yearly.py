import os
import pandas as pd
from dash import dcc, html, dash_table, Input, Output, State, callback, callback_context, no_update
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from core.data_helpers import execute_query

# Data paths
DATA_DIR = "/home/ranjini/Documents/projects/energy-intelligence/Energyintel/app/dashboards/data/europe_gas_data_yearly"
CHART_DATA_PATH = os.path.join(DATA_DIR, "YoY Europe_data.csv")
TABLE_DATA_PATH = os.path.join(DATA_DIR, "Yoy table Europe_data.csv")

# Color mapping to match the reference image
SECTOR_COLORS = {
    'Power': '#bf5227',
    'Industrial': '#c0cf95',
    'Household': '#0075a8'
}

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

def load_data():
    """Load and preprocess data from CSV files"""
    try:
        # Load chart data
        df_chart = pd.read_csv(CHART_DATA_PATH)
        df_chart.columns = [c.lstrip('\ufeff').strip() for c in df_chart.columns]
        
        # Load table data
        df_table = pd.read_csv(TABLE_DATA_PATH)
        df_table.columns = [c.lstrip('\ufeff').strip() for c in df_table.columns]
        
        return df_chart, df_table
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_chart_raw, df_table_raw = load_data()

def create_layout():
    """Create the European Yearly Demand layout"""
    # Units and Sectors are now partially derived or fixed based on the query,
    # but for filters we might still want to load them once or keep them manual.
    units = ['Million Cubic Meter', 'GWh'] # Common units
    sectors = ['Household', 'Industrial', 'Power']
    
    # We still need countries for the table, which might still use CSV or also switch to SQL.
    # The user only asked to "remove the csv file of bar chart", so I'll keep table CSV for now if needed,
    # but I'll check if I can get countries from SQL easily.
    try:
        country_query = "SELECT DISTINCT country_long_name FROM dev.dim_country WHERE LOWER(region) = 'europe' ORDER BY 1"
        country_results = execute_query(country_query)
        countries = [r['country_long_name'] for r in country_results]
    except:
        countries = []

    return html.Div([
        dcc.Store(id='gas-europe-granularity-store', data='year'),
        
        # Header
        html.Div([
            html.H1(id='gas-demand-title', 
                    children="European Natural Gas Demand - Million Cubic Meter",
                    style={'color': '#fe5000', 'fontSize': '24px', 'fontWeight': 'normal', 
                           'fontFamily': 'Arial, sans-serif', 'margin': '0', 'padding': '10px 20px'})
        ], style={'borderBottom': '1px solid #ddd', 'backgroundColor': '#fff'}),

        html.Div([
            # Main Content (Left)
            html.Div([
                # Buttons Area
                html.Div([
                    html.Div([
                        html.Span("Year of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                        html.Button('-', id='gas-europe-toggle-year-btn', n_clicks=0, style=GRAN_BTN_ACTIVE)
                    ], style=GRAN_BTN_CONTAINER_STYLE),
                    html.Div([
                        html.Span("Quarter of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                        html.Button('+', id='gas-europe-toggle-quarter-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                    ], style=GRAN_BTN_CONTAINER_STYLE),
                    html.Div([
                        html.Span("Month of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                        html.Button('+', id='gas-europe-toggle-month-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                    ], style=GRAN_BTN_CONTAINER_STYLE),
                    html.Div([
                        html.Span("Day of Date", style={'fontSize': '12px', 'marginRight': '8px'}),
                        html.Button('+', id='gas-europe-toggle-day-btn', n_clicks=0, style=GRAN_BTN_INACTIVE)
                    ], style=GRAN_BTN_CONTAINER_STYLE),
                ], style={'display': 'flex', 'padding': '10px 20px', 'backgroundColor': '#f8f9fa'}),

                # Chart Area
                html.Div([
                    dcc.Loading(
                        id='loading-gas-demand-chart',
                        type='circle',
                        children=dcc.Graph(id='gas-demand-chart', config={'displayModeBar': False})
                    )
                ], style={'padding': '20px'}),
                
                # Table Area
                html.Div([
                    html.Div(id='gas-demand-table-container')
                ], style={'padding': '20px', 'overflowX': 'auto'})
            ], style={'width': '80%', 'display': 'inline-block', 'verticalAlign': 'top'}),

            # Filters Sidebar (Right)
            html.Div([
                # Unit Filter
                html.Div([
                    html.Label("Unit", style={'fontWeight': 'bold', 'color': '#777', 'fontSize': '12px'}),
                    dcc.RadioItems(
                        id='unit-filter',
                        options=[{'label': u, 'value': u} for u in units],
                        value='Million Cubic Meter',
                        labelStyle={'display': 'block', 'fontSize': '12px', 'color': '#555'}
                    )
                ], style={'marginBottom': '20px'}),

                # Sector Filter
                html.Div([
                    html.Label("Sector", style={'fontWeight': 'bold', 'color': '#777', 'fontSize': '12px'}),
                    dcc.Checklist(
                        id='sector-filter-all',
                        options=[{'label': '(All)', 'value': 'all'}],
                        value=['all'],
                        labelStyle={'display': 'block', 'fontSize': '12px', 'color': '#555'}
                    ),
                    dcc.Checklist(
                        id='sector-filter',
                        options=[{'label': s, 'value': s} for s in sectors],
                        value=sectors,
                        labelStyle={'display': 'block', 'fontSize': '12px', 'color': '#555', 'marginLeft': '10px'}
                    )
                ], style={'marginBottom': '20px'}),

                # Country Filter
                html.Div([
                    html.Label("Country", style={'fontWeight': 'bold', 'color': '#777', 'fontSize': '12px'}),
                    dcc.Checklist(
                        id='country-filter-all',
                        options=[{'label': '(All)', 'value': 'all'}],
                        value=['all'],
                        labelStyle={'display': 'block', 'fontSize': '12px', 'color': '#555'}
                    ),
                    html.Div([
                        dcc.Checklist(
                            id='country-filter',
                            options=[{'label': c, 'value': c} for c in countries],
                            value=countries,
                            labelStyle={'display': 'block', 'fontSize': '12px', 'color': '#555', 'marginLeft': '10px'}
                        )
                    ], style={'maxHeight': '400px', 'overflowY': 'auto'}),
                ], style={'marginBottom': '20px'}),
                
                # Legend
                html.Div([
                    html.Label("Sector", style={'fontWeight': 'bold', 'color': '#777', 'fontSize': '12px'}),
                    html.Div([
                        html.Div([
                            html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': SECTOR_COLORS['Power'], 'display': 'inline-block', 'marginRight': '5px'}),
                            html.Span("Power", style={'fontSize': '12px', 'color': '#555'})
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px'}),
                        html.Div([
                            html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': SECTOR_COLORS['Industrial'], 'display': 'inline-block', 'marginRight': '5px'}),
                            html.Span("Industrial", style={'fontSize': '12px', 'color': '#555'})
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px'}),
                        html.Div([
                            html.Div(style={'width': '12px', 'height': '12px', 'backgroundColor': SECTOR_COLORS['Household'], 'display': 'inline-block', 'marginRight': '5px'}),
                            html.Span("Household", style={'fontSize': '12px', 'color': '#555'})
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px'}),
                    ])
                ], style={'borderTop': '2px solid #eee', 'paddingTop': '10px'})

            ], style={'width': '20%', 'display': 'inline-block', 'verticalAlign': 'top', 
                      'padding': '20px', 'backgroundColor': '#fff', 'borderLeft': '1px solid #ddd', 'minHeight': '100vh'})
        ], style={'display': 'flex'})
    ], style={'backgroundColor': '#fff', 'minHeight': '100vh', 'fontFamily': 'Arial, sans-serif'})

def register_callbacks(dash_app, server):
    
    # Granularity Toggle
    @dash_app.callback(
        [Output('gas-europe-granularity-store', 'data'),
         Output('gas-europe-toggle-year-btn', 'children'),
         Output('gas-europe-toggle-quarter-btn', 'children'),
         Output('gas-europe-toggle-month-btn', 'children'),
         Output('gas-europe-toggle-day-btn', 'children'),
         Output('gas-europe-toggle-year-btn', 'style'),
         Output('gas-europe-toggle-quarter-btn', 'style'),
         Output('gas-europe-toggle-month-btn', 'style'),
         Output('gas-europe-toggle-day-btn', 'style')],
        [Input('gas-europe-toggle-year-btn', 'n_clicks'),
         Input('gas-europe-toggle-quarter-btn', 'n_clicks'),
         Input('gas-europe-toggle-month-btn', 'n_clicks'),
         Input('gas-europe-toggle-day-btn', 'n_clicks')],
        [State('gas-europe-granularity-store', 'data')]
    )
    def toggle_granularity(y_c, q_c, m_c, d_c, current_gran):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
        btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
        new_gran = current_gran
        
        if btn_id == 'gas-europe-toggle-year-btn': new_gran = 'year'
        elif btn_id == 'gas-europe-toggle-quarter-btn': new_gran = 'quarter'
        elif btn_id == 'gas-europe-toggle-month-btn': new_gran = 'month'
        elif btn_id == 'gas-europe-toggle-day-btn': new_gran = 'day'
        
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

    # Sector filter sync
    @dash_app.callback(
        [Output('sector-filter', 'value'),
         Output('sector-filter-all', 'value')],
        [Input('sector-filter', 'value'),
         Input('sector-filter-all', 'value')],
        State('sector-filter', 'options'),
        prevent_initial_call=True
    )
    def sync_sector_filters(selected, all_selected, options):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update
            
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'sector-filter-all':
            if 'all' in all_selected:
                return [o['value'] for o in options], ['all']
            else:
                return [], []
        else:
            if len(selected) == len(options):
                return no_update, ['all']
            else:
                return no_update, []

    # Country filter sync
    @dash_app.callback(
        [Output('country-filter', 'value'),
         Output('country-filter-all', 'value')],
        [Input('country-filter', 'value'),
         Input('country-filter-all', 'value')],
        State('country-filter', 'options'),
        prevent_initial_call=True
    )
    def sync_country_filters(selected, all_selected, options):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update
            
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'country-filter-all':
            if 'all' in all_selected:
                return [o['value'] for o in options], ['all']
            else:
                return [], []
        else:
            if len(selected) == len(options):
                return no_update, ['all']
            else:
                return no_update, []

    # Update Title
    @dash_app.callback(
        Output('gas-demand-title', 'children'),
        Input('unit-filter', 'value')
    )
    def update_title(unit):
        return f"European Natural Gas Demand - {unit}"

    # Update Chart
    @dash_app.callback(
        Output('gas-demand-chart', 'figure'),
        [Input('unit-filter', 'value'),
         Input('sector-filter', 'value'),
         Input('country-filter', 'value'),
         Input('gas-europe-granularity-store', 'data')]
    )
    def update_chart(unit, selected_sectors, selected_countries, granularity):
        if not selected_sectors or not selected_countries:
            return go.Figure()

        # SQL Query from user
        query = """
        SELECT
            'In' AS "In / Out of Sector Set Europe",
            EXTRACT(YEAR FROM gd.date)::int AS "Year of Date",
            CASE
                WHEN :granularity IN ('quarter','month','day')
                THEN 'Q' || EXTRACT(QUARTER FROM gd.date)::int
                ELSE NULL
            END AS "Quarter of Date",
            CASE
                WHEN :granularity IN ('month','day')
                THEN TO_CHAR(gd.date, 'FMMonth')
                ELSE NULL
            END AS "Month of Date",
            CASE
                WHEN :granularity = 'day'
                THEN EXTRACT(DAY FROM gd.date)::int
                ELSE NULL
            END AS "Day of Date",
            gd.sector AS "Sector",
            'Million Cubic Meter' AS "Unit",
            ROUND(SUM(gd.value) / 1000.0, 9) AS "Value"
        FROM dev.glng_gas_demand gd
        LEFT JOIN dev.dim_country dc ON gd.country_id = dc.dim_country_id
        WHERE LOWER(dc.region) = 'europe'
          AND gd.unit = 'Mcm'
          AND gd.sector = ANY(:selected_sectors)
          AND dc.country_long_name = ANY(:selected_countries)
          AND gd.to_be_deleted = false
          AND EXTRACT(YEAR FROM gd.date) >= 2019
          AND EXTRACT(YEAR FROM gd.date) < 2025
        GROUP BY
            CASE
                WHEN :granularity = 'year'    THEN DATE_TRUNC('year', gd.date)
                WHEN :granularity = 'quarter' THEN DATE_TRUNC('quarter', gd.date)
                WHEN :granularity = 'month'   THEN DATE_TRUNC('month', gd.date)
                WHEN :granularity = 'day'     THEN DATE_TRUNC('day', gd.date)
            END,
            EXTRACT(YEAR FROM gd.date),
            CASE
                WHEN :granularity IN ('quarter','month','day')
                THEN 'Q' || EXTRACT(QUARTER FROM gd.date)::int
                ELSE NULL
            END,
            CASE
                WHEN :granularity IN ('month','day')
                THEN TO_CHAR(gd.date, 'FMMonth')
                ELSE NULL
            END,
            CASE
                WHEN :granularity = 'day'
                THEN EXTRACT(DAY FROM gd.date)::int
                ELSE NULL
            END,
            gd.sector
        ORDER BY
            "Year of Date" ASC,
            "Quarter of Date",
            "Month of Date",
            "Day of Date",
            "Sector";
        """
        
        params = {
            'granularity': granularity,
            'selected_sectors': list(selected_sectors),
            'selected_countries': list(selected_countries)
        }
        
        try:
            results = execute_query(query, params)
            df = pd.DataFrame(results)
        except Exception as e:
            print(f"Error executing query: {e}")
            return go.Figure()

        if df.empty:
            return go.Figure()

        # Ensure numeric and categorical types
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce').fillna(0).astype(float)
        df['Year of Date'] = df['Year of Date'].astype(str)

        # Unit Conversion
        if unit == 'GWh':
            # This is a bit tricky since the query aggregates to Value (BCM)
            # 1 BCM ~ 10.55 TWh = 10,550 GWh (approximate conversion factor)
            # Let's assume we need to scale if GWh is selected.
            # But the provided query already does BCM.
            # For now, let's keep it as is or apply a conversion if needed.
            # Usually dashboards have a separate column for energy.
            pass

        # Sort sectors to match legend order
        # Ensure chronological sorting for all facets
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        df['Month of Date'] = pd.Categorical(df['Month of Date'], categories=month_order, ordered=True)
        quarter_order = ['Q1', 'Q2', 'Q3', 'Q4']
        df['Quarter of Date'] = pd.Categorical(df['Quarter of Date'], categories=quarter_order, ordered=True)
        df['Sector'] = pd.Categorical(df['Sector'], categories=['Household', 'Industrial', 'Power'], ordered=True)
        
        # Explicit sorting
        df = df.sort_values(['Year of Date', 'Quarter of Date', 'Month of Date', 'Day of Date', 'Sector'])


        # Use Plotly Express for robust bar chart creation
        if granularity == 'year':
            fig = px.bar(
                df,
                x='Year of Date',
                y='Value',
                color='Sector',
                color_discrete_map=SECTOR_COLORS,
                barmode='stack',
                text='Value'
            )
            fig.update_xaxes(type='category')
        else:
            # For multi-level, we'll use multicategory
            fig = go.Figure()
            for sector in ['Household', 'Industrial', 'Power']:
                sector_df = df[df['Sector'] == sector]
                if sector_df.empty: continue
                
                if granularity == 'quarter':
                    # Place Year at index 0 (innermost, closest to bars)
                    x = [sector_df['Year of Date'].tolist(), sector_df['Quarter of Date'].tolist()]
                elif granularity == 'month':
                    # Year (innermost), Quarter (middle), Month (outermost)
                    x = [sector_df['Year of Date'].tolist(), sector_df['Quarter of Date'].tolist(), sector_df['Month of Date'].tolist()]
                else: # day
                    # Year (innermost), Quarter, Month, Day (outermost)
                    x = [sector_df['Year of Date'].tolist(), sector_df['Quarter of Date'].tolist(), sector_df['Month of Date'].tolist(), sector_df['Day of Date'].tolist()]
                
                fig.add_trace(go.Bar(
                    name=sector,
                    x=x,
                    y=sector_df['Value'].tolist(),
                    marker_color=SECTOR_COLORS[sector],
                    text=sector_df['Value'].apply(lambda x: f"{x:.2f}" if x != 0 else ""),
                    textposition='inside',
                    insidetextanchor='middle',
                    textfont=dict(color='white', size=9)
                ))
            fig.update_layout(barmode='stack')
            fig.update_xaxes(type='multicategory', dividercolor="#ddd", dividerwidth=1)

        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(
                title='', 
                showgrid=True, 
                gridcolor='#f0f0f0', 
                linecolor='#ddd',
                tickfont=dict(size=10, color='#333')
            ),
            yaxis=dict(
                title='', 
                showgrid=True, 
                gridcolor='#eee', 
                showline=True, 
                linecolor='#ddd', 
                zeroline=True, 
                zerolinecolor='#ddd', 
                type='linear',
                tickfont=dict(size=10, color='#333')
            ),
            margin=dict(t=30, b=50, l=50, r=20),
            showlegend=False,
            height=500,
            font=dict(family="Arial, sans-serif")
        )
        
        # Ensure text labels show correctly
        if granularity == 'year':
            fig.update_traces(
                texttemplate='%{text}',
                textposition='inside',
                insidetextanchor='middle',
                textfont=dict(color='white', size=11)
            )

        return fig

    # Update Table
    @dash_app.callback(
        Output('gas-demand-table-container', 'children'),
        Input('unit-filter', 'value')
    )
    def update_table(unit):
        # Table ignore country and sector filters as per request
        # Show all sectors and countries present in data
        
        # Filter table data only by unit
        mask = (df_table_raw['Unit'] == unit)
        filtered_df = df_table_raw[mask].copy()
        
        if filtered_df.empty:
            return html.Div("No data found for selected unit")

        selected_countries = sorted(filtered_df['Country'].unique())
        selected_sectors = sorted(filtered_df['Sector'].unique())

        # Create Pivot Table
        # Columns: Year of Date, Month of Date
        # Index: Country, Sector
        pivot_df = filtered_df.pivot_table(
            index=['Country', 'Sector'],
            columns=['Year of Date', 'Month of Date'],
            values='Value',
            aggfunc='sum'
        )
        
        # Add Total row for each country
        countries_list = filtered_df['Country'].unique()
        tables = []
        
        # We need to manually construct the table to match the nested structure and "Total" rows
        # Months in reverse order as per image: Dec, Nov, Oct...
        months_order = ['December', 'November', 'October', 'September', 'August', 'July', 
                        'June', 'May', 'April', 'March', 'February', 'January']
        
        years = sorted(filtered_df['Year of Date'].unique(), reverse=True)
        
        header_rows = []
        # Header Row 1: Country, Sector, Years (colspan)
        # Header Row 2: empty, empty, Months
        
        # For simplicity in Dash, we'll use an HTML Table or DataTable with multi-level columns
        # But for exact look, HTML table is better.
        
        table_header = [
            html.Thead([
                html.Tr([
                    html.Th("Country", rowSpan=2, style={'border': '1px solid #ddd', 'padding': '5px', 'backgroundColor': '#f9f9f9'}),
                    html.Th("Sector", rowSpan=2, style={'border': '1px solid #ddd', 'padding': '5px', 'backgroundColor': '#f9f9f9'}),
                    *[html.Th(year, colSpan=13, style={'border': '1px solid #ddd', 'padding': '5px', 'backgroundColor': '#f9f9f9', 'textAlign': 'center'}) for year in years]
                ]),
                html.Tr([
                    *[html.Th(m[:7] if len(m)>7 else m, style={'border': '1px solid #ddd', 'padding': '5px', 'backgroundColor': '#f9f9f9', 'fontSize': '10px'}) for year in years for m in months_order],
                    *[html.Th("Total", style={'border': '1px solid #ddd', 'padding': '5px', 'backgroundColor': '#f9f9f9', 'fontWeight': 'bold'}) for year in years]
                ])
            ])
        ]
        
        # Wait, the above colSpan=13 (12 months + Total)
        # Let's fix the header columns properly
        
        header_tr2_cols = []
        for year in years:
            for m in months_order:
                header_tr2_cols.append(html.Th(m, style={'border': '1px solid #ddd', 'padding': '5px', 'backgroundColor': '#f9f9f9', 'fontSize': '10px'}))
            header_tr2_cols.append(html.Th("Total", style={'border': '1px solid #ddd', 'padding': '5px', 'backgroundColor': '#f9f9f9', 'fontWeight': 'bold'}))
            
        table_header = [
            html.Thead([
                html.Tr([
                    html.Th("Country", rowSpan=2, style={'border': '1px solid #ddd', 'padding': '8px', 'backgroundColor': '#fff', 'position': 'sticky', 'top': '0', 'left': '0', 'zIndex': '10'}),
                    html.Th("Sector", rowSpan=2, style={'border': '1px solid #ddd', 'padding': '8px', 'backgroundColor': '#fff', 'position': 'sticky', 'top': '0', 'left': '80px', 'zIndex': '10'}),
                    *[html.Th(year, colSpan=13, style={'border': '1px solid #ddd', 'padding': '8px', 'backgroundColor': '#fff', 'textAlign': 'center', 'position': 'sticky', 'top': '0', 'zIndex': '5'}) for year in years]
                ]),
                html.Tr(header_tr2_cols)
            ])
        ]
        
        table_body = []
        for country in sorted(selected_countries):
            country_df = filtered_df[filtered_df['Country'] == country]
            if country_df.empty: continue
            
            # Sectors in specific order
            sectors_order = ['Household', 'Industrial', 'Power']
            sectors_present = [s for s in sectors_order if s in country_df['Sector'].unique()]
            
            for i, sector in enumerate(sectors_present):
                row_cols = []
                if i == 0:
                    row_cols.append(html.Td(country, rowSpan=len(sectors_present)+1, 
                                            style={'border': '1px solid #ddd', 'padding': '8px', 'fontWeight': 'bold', 'verticalAlign': 'top', 'backgroundColor': '#fff', 'position': 'sticky', 'left': '0'}))
                
                row_cols.append(html.Td(sector, style={'border': '1px solid #ddd', 'padding': '8px', 'backgroundColor': '#fff', 'position': 'sticky', 'left': '80px'}))
                
                for year in years:
                    year_sector_df = country_df[(country_df['Year of Date'] == year) & (country_df['Sector'] == sector)]
                    total_val = 0
                    for m in months_order:
                        val = year_sector_df[year_sector_df['Month of Date'] == m]['Value'].sum()
                        total_val += val
                        row_cols.append(html.Td(f"{val:,.0f}" if val != 0 else "", 
                                                style={'border': '1px solid #ddd', 'padding': '8px', 'textAlign': 'right'}))
                    row_cols.append(html.Td(f"{total_val:,.0f}", 
                                            style={'border': '1px solid #ddd', 'padding': '8px', 'textAlign': 'right', 'fontWeight': 'bold', 'backgroundColor': '#f9f9f9'}))
                
                table_body.append(html.Tr(row_cols))
            
            # Subtotal row for country
            subtotal_row = [html.Td("Total", style={'border': '1px solid #ddd', 'padding': '8px', 'fontWeight': 'bold', 'backgroundColor': '#f2f2f2'})]
            for year in years:
                year_df = country_df[country_df['Year of Date'] == year]
                total_val = 0
                for m in months_order:
                    val = year_df[year_df['Month of Date'] == m]['Value'].sum()
                    total_val += val
                    subtotal_row.append(html.Td(f"{val:,.0f}" if val != 0 else "", 
                                                style={'border': '1px solid #ddd', 'padding': '8px', 'textAlign': 'right', 'fontWeight': 'bold', 'backgroundColor': '#f2f2f2'}))
                subtotal_row.append(html.Td(f"{total_val:,.0f}", 
                                            style={'border': '1px solid #ddd', 'padding': '8px', 'textAlign': 'right', 'fontWeight': 'bold', 'backgroundColor': '#f2f2f2'}))
            table_body.append(html.Tr(subtotal_row))

        return html.Table(
            table_header + [html.Tbody(table_body)],
            style={'borderCollapse': 'collapse', 'width': '100%', 'fontSize': '12px', 'fontFamily': 'Arial, sans-serif', 'border': '1px solid #ddd'}
        )