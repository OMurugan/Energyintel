import os
import pandas as pd
from dash import dcc, html, dash_table, Input, Output, State, callback, callback_context, no_update
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Data paths
DATA_DIR = "/home/ranjini/Documents/projects/energy-intelligence/Energyintel/app/dashboards/data/europe_gas_data_yearly"
CHART_DATA_PATH = os.path.join(DATA_DIR, "YoY Europe_data.csv")
TABLE_DATA_PATH = os.path.join(DATA_DIR, "Yoy table Europe_data.csv")

# Color mapping to match the reference image
SECTOR_COLORS = {
    'Power': '#C0504D',      # Reddish
    'Industrial': '#9BBB59', # Greenish
    'Household': '#4F81BD'   # Blueish
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
    if df_chart_raw.empty or df_table_raw.empty:
        return html.Div("Error loading data. Please check CSV files.")

    # Get filter options
    units = df_chart_raw['Unit'].unique()
    sectors = sorted(df_chart_raw['Sector'].unique())
    countries = sorted(df_table_raw['Country'].unique())

    return html.Div([
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
                # Chart Area
                html.Div([
                    dcc.Graph(id='gas-demand-chart', config={'displayModeBar': False})
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
         Input('country-filter', 'value')]
    )
    def update_chart(unit, selected_sectors, selected_countries):
        if not selected_sectors or not selected_countries:
            return go.Figure()
            
        # Use table data for chart to support country filtering
        mask = (df_table_raw['Unit'] == unit) & \
               (df_table_raw['Sector'].isin(selected_sectors)) & \
               (df_table_raw['Country'].isin(selected_countries))
        
        filtered_df = df_table_raw[mask].copy()
        
        if filtered_df.empty:
            return go.Figure()

        # Aggregate by Year and Sector
        chart_df = filtered_df.groupby(['Year of Date', 'Sector'])['Value'].sum().reset_index()
        
        # Convert to BCM if unit is Million Cubic Meter (1000 Mcm = 1 Bcm)
        # Assuming the chart should always be in BCM or GWh (large scale)
        # Based on fig 1, Y axis is ~500 for total Europe in MCM? 
        # Wait, if 207.4 is Household demand in BCM, then total Europe is ~450 BCM.
        # If the unit is Million Cubic Meter, the label says "European Natural Gas Demand - Million Cubic Meter".
        # But 450 Million Cubic Meter is very small for Europe.
        # It must be 450 BILLION Cubic Meters (BCM).
        # Let's check the y-axis in fig 1. It goes up to 500.
        # So the values in `YoY Europe_data.csv` (207.4 etc) ARE the ones shown in the chart.
        # These are in BCM? Or is 207.4 MCM? 
        # No, 207.4 MCM is tiny. Household demand for all Europe is ~200 BCM.
        # So the values in `YoY Europe_data.csv` are in BCM.
        # AND the values in `Yoy table Europe_data.csv` for Austria (e.g. 542) are in MCM.
        # 542 MCM = 0.542 BCM.
        # So yes, divide by 1000 is correct for MCM -> BCM.
        
        scale_factor = 1000.0 if unit == 'Million Cubic Meter' else 1.0 # If GWh, maybe keep it or scale too?
        # Let's check the GWh values. 
        # For now, let's assume we want to match the "500" scale in the image.
        chart_df['DisplayValue'] = chart_df['Value'] / scale_factor
        
        # Sort sectors to match legend order
        chart_df['Sector'] = pd.Categorical(chart_df['Sector'], categories=['Household', 'Industrial', 'Power'], ordered=True)
        chart_df = chart_df.sort_values(['Year of Date', 'Sector'])
        
        fig = px.bar(
            chart_df,
            x='Year of Date',
            y='DisplayValue',
            color='Sector',
            color_discrete_map=SECTOR_COLORS,
            barmode='stack',
            text='DisplayValue'
        )
        
        fig.update_traces(
            texttemplate='%{text:.1f}',
            textposition='inside',
            insidetextanchor='middle',
            textfont=dict(color='white', size=10)
        )
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(
                title='',
                showgrid=False,
                linecolor='#ddd',
                tickmode='array',
                tickvals=chart_df['Year of Date'].unique()
            ),
            yaxis=dict(
                title='',
                showgrid=True,
                gridcolor='#eee',
                showline=True,
                linecolor='#ddd',
                range=[0, max(500, chart_df.groupby('Year of Date')['DisplayValue'].sum().max() * 1.1) if not chart_df.empty else 500]
            ),
            margin=dict(t=20, b=40, l=40, r=20),
            showlegend=False,
            height=500
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