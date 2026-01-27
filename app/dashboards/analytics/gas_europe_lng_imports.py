import pandas as pd
import plotly.express as px
from dash import dcc, html, Input, Output, dash_table
import os
from datetime import datetime

# Define file paths
CHART_DATA_PATH = '/var/www/Projects/ENERGY_DASH/Energyintel/European_gas_trade/CHART_LNG Imports_data.csv'
TABLE_DATA_PATH = '/var/www/Projects/ENERGY_DASH/Energyintel/European_gas_trade/TABLE_LNG Imports_data.csv'

# Custom Color Palette - Exact names from CSV
TERMINAL_COLORS = {
    'Alexandroupolis': '#1b365d',
    'Baltic Energy Gate': '#7a8ec9',
    'Barcelona': '#007ba7',
    'Bilbao': '#595959',
    'Brunsbuettel Hafen FSRU': '#ff5000',
    'Cartagena': '#2c3e50',
    'Croatia LNG': '#a0522d',
    'Dunkerque LNG / PEG North': '#1b365d',
    'Eems Energy Terminal': '#7a8ec9',
    'Fos (Tonkin/Cavaou)': '#ff5000',
    'Gate Terminal (I)': '#c5d9a1',
    'Hamina LNG': '#007ba7',
    'Huelva': '#5489b4',
    'Inkoo LNG (FI)': '#2c3e50',
    'Isle of Grain': '#5489b4',
    'Klaipeda (LNG)': '#a6a6a6',
    'Le Havre FSRU': '#bf5700',
    'LNG Cavarzere': '#595959',
    'LNG Livorno': '#1b365d',
    'LNG Panigaglia': '#7a8ec9',
    'LNG Piombino': '#ff5000',
    'Milford Haven': '#c5d9a1',
    'Montoir de Bretagne': '#007ba7',
    'Reganosa': '#a6a6a6',
    'Revithoussa': '#5489b4',
    'Sagunto': '#bf5700',
    'Sines': '#a6a6a6',
    'Swinoujscie': '#bf5700',
    'Wilhelmshaven LNG': '#a0522d',
    'Zeebrugge LNG': '#595959',
}

def load_data():
    """Load and preprocess data from CSVs"""
    try:
        if not os.path.exists(CHART_DATA_PATH) or not os.path.exists(TABLE_DATA_PATH):
            print(f"ERROR: Data files not found at {CHART_DATA_PATH} or {TABLE_DATA_PATH}")
            return pd.DataFrame(), pd.DataFrame()
        
        chart_df = pd.read_csv(CHART_DATA_PATH)
        table_df = pd.read_csv(TABLE_DATA_PATH)
        
        # Preprocess dates - handle "Month Year" format
        chart_df['Date'] = pd.to_datetime(chart_df['Month of Date'], errors='coerce')
        table_df['Date'] = pd.to_datetime(table_df['Month of Date'], errors='coerce')
        
        # Clean up any failed parses
        chart_df = chart_df.dropna(subset=['Date'])
        table_df = table_df.dropna(subset=['Date'])
        
        print(f"SUCCESS: Loaded {len(chart_df)} chart rows and {len(table_df)} table rows")
        return chart_df, table_df
    except Exception as e:
        print(f"CRITICAL: Data loading failed: {e}")
        return pd.DataFrame(), pd.DataFrame()

def create_layout():
    """Create the European LNG Imports layout"""
    chart_df, table_df = load_data()
    
    if chart_df.empty or table_df.empty:
        return html.Div("Data could not be loaded or is empty. Check server logs.", 
                        style={'padding': '50px', 'color': 'red'})

    countries = sorted(table_df['Target Country'].unique())
    terminals = sorted(chart_df['Point'].unique())
    
    min_date_val = chart_df['Date'].min()
    max_date_val = chart_df['Date'].max()

    return html.Div([
        # Header
        html.Div([
            html.H1("LNG Imports By Terminal - All - Billion Cubic Meters (v2)", style={
                'color': '#fe5000', 'fontSize': '20px', 'fontWeight': 'bold',
                'fontFamily': 'Arial, sans-serif', 'margin': '25px 0 15px 40px'
            }),
        ]),

        html.Div([
            # Side Filter Panel (on the right)
            html.Div([
                html.Div([
                    html.Label("Country", style={'fontWeight': 'normal', 'color': '#555', 'fontSize': '13px'}),
                    dcc.Dropdown(
                        id='country-dropdown',
                        options=[{'label': '(All)', 'value': 'All'}] + [{'label': c, 'value': c} for c in countries],
                        value=['All'],
                        multi=True,
                        clearable=False,
                        style={'marginBottom': '15px', 'fontSize': '12px'}
                    ),
                    
                    html.Label("Regasification Terminal", style={'fontWeight': 'normal', 'color': '#555', 'fontSize': '13px'}),
                    dcc.Dropdown(
                        id='terminal-dropdown',
                        options=[{'label': '(All)', 'value': 'All'}] + [{'label': t, 'value': t} for t in terminals],
                        value=['All'],
                        multi=True,
                        clearable=False,
                        style={'marginBottom': '15px', 'fontSize': '12px'}
                    ),
                    
                    html.Label("Start Date", style={'fontWeight': 'normal', 'color': '#555', 'fontSize': '13px'}),
                    dcc.Input(
                        id='start-date-input',
                        type='text',
                        value=min_date_val.strftime('%-m/%-d/%Y') if pd.notnull(min_date_val) else "1/1/2021",
                        style={'width': '90%', 'marginBottom': '15px', 'padding': '5px', 'border': '1px solid #ccc', 'fontSize': '12px'}
                    ),
                    
                    html.Label("End Date", style={'fontWeight': 'normal', 'color': '#555', 'fontSize': '13px'}),
                    dcc.Input(
                        id='end-date-input',
                        type='text',
                        value=max_date_val.strftime('%-m/%-d/%Y') if pd.notnull(max_date_val) else "1/1/2026",
                        style={'width': '90%', 'marginBottom': '15px', 'padding': '5px', 'border': '1px solid #ccc', 'fontSize': '12px'}
                    ),
                ], style={'padding': '20px', 'backgroundColor': '#fcfcfc', 'borderLeft': '1px solid #eee', 'minHeight': '500px'})
            ], style={'width': '230px', 'float': 'right'}),

            # Main content area
            html.Div([
                dcc.Loading(
                    id="loading-chart",
                    type="circle",
                    children=dcc.Graph(id='lng-imports-chart', config={'displayModeBar': False})
                ),
                
                html.Div([
                    html.H2("LNG Imports By Terminal- Billion Cubic Meters", style={
                        'color': '#fe5000', 'fontSize': '18px', 'fontWeight': 'bold',
                        'marginTop': '30px', 'marginBottom': '20px'
                    }),
                    dcc.Loading(
                        id="loading-table",
                        type="circle",
                        children=html.Div(id='lng-imports-table-container')
                    )
                ], style={'padding': '0 20px'})
            ], style={'marginRight': '240px'})
        ], style={'overflow': 'hidden'})
    ], className='tab-content', style={'backgroundColor': '#ffffff', 'minHeight': '100vh', 'fontFamily': 'Arial, sans-serif'})

def register_callbacks(dash_app, server):
    @dash_app.callback(
        Output('terminal-dropdown', 'options'),
        Input('country-dropdown', 'value')
    )
    def update_terminal_options(selected_countries):
        _, table_df = load_data()
        if table_df.empty: return [{'label': '(All)', 'value': 'All'}]
        
        if not selected_countries: selected_countries = []
        if isinstance(selected_countries, str): selected_countries = [selected_countries]
            
        if not selected_countries or 'All' in selected_countries:
            terminals = sorted(table_df['Point'].unique())
        else:
            terminals = sorted(table_df[table_df['Target Country'].isin(selected_countries)]['Point'].unique())
        
        return [{'label': '(All)', 'value': 'All'}] + [{'label': t, 'value': t} for t in terminals]

    @dash_app.callback(
        [Output('lng-imports-chart', 'figure'),
         Output('lng-imports-table-container', 'children')],
        [Input('country-dropdown', 'value'),
         Input('terminal-dropdown', 'value'),
         Input('start-date-input', 'value'),
         Input('end-date-input', 'value')]
    )
    def update_dashboard(selected_countries, selected_terminals, start_date, end_date):
        try:
            chart_df_orig, table_df_orig = load_data()
            if chart_df_orig.empty:
                return px.bar(title="Error: Data not loaded"), html.Div("Data error")

            chart_df = chart_df_orig.copy()
            table_df = table_df_orig.copy()
            
            # --- Robust Date Filtering ---
            try:
                start_dt = pd.to_datetime(start_date, errors='coerce')
                end_dt = pd.to_datetime(end_date, errors='coerce')
                
                if pd.notnull(start_dt):
                    chart_df = chart_df[chart_df['Date'] >= start_dt]
                    table_df = table_df[table_df['Date'] >= start_dt]
                if pd.notnull(end_dt):
                    # Ensure we include the entire month of the end date
                    adjusted_end_dt = end_dt + pd.offsets.MonthEnd(0)
                    chart_df = chart_df[chart_df['Date'] <= adjusted_end_dt]
                    table_df = table_df[table_df['Date'] <= adjusted_end_dt]
            except Exception as e:
                print(f"Date conversion error: {e}")

            # --- Multi-select Filtering ---
            if not selected_countries: selected_countries = []
            if isinstance(selected_countries, str): selected_countries = [selected_countries]
            
            if selected_countries and 'All' not in selected_countries:
                chart_df = chart_df[chart_df['Point'].isin(table_df_orig[table_df_orig['Target Country'].isin(selected_countries)]['Point'].unique())]
                table_df = table_df[table_df['Target Country'].isin(selected_countries)]
                
            if not selected_terminals: selected_terminals = []
            if isinstance(selected_terminals, str): selected_terminals = [selected_terminals]

            if selected_terminals and 'All' not in selected_terminals:
                chart_df = chart_df[chart_df['Point'].isin(selected_terminals)]
                table_df = table_df[table_df['Point'].isin(selected_terminals)]

            # --- Chart Rendering ---
            if chart_df.empty:
                fig = px.bar(title="No data matches selected filters")
                fig.update_layout(xaxis={'visible': False}, yaxis={'visible': False})
            else:
                chart_df = chart_df.sort_values('Date')
                chart_df['Month_Label'] = chart_df['Date'].dt.strftime('%b %y')
                
                unique_labels = chart_df.sort_values('Date')['Month_Label'].unique()
                
                fig = px.bar(
                    chart_df, 
                    x='Month_Label', 
                    y='flows_bcm', 
                    color='Point',
                    color_discrete_map=TERMINAL_COLORS,
                    category_orders={'Month_Label': unique_labels},
                )
                
                fig.update_layout(
                    barmode='stack',
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    legend_title_text='Point',
                    xaxis={
                        'tickangle': -90, 
                        'showgrid': True, 
                        'gridcolor': '#f5f5f5', 
                        'type': 'category',
                        'title': ''
                    },
                    yaxis={
                        'showgrid': True, 
                        'gridcolor': '#f5f5f5', 
                        'title': 'Billion Cubic Meters',
                        'rangemode': 'tozero'
                    },
                    margin={'t': 10, 'b': 10, 'l': 50, 'r': 20},
                    height=450,
                    showlegend=True
                )

            # --- Table Rendering ---
            if table_df.empty:
                table_output = html.Div("No table data found for filters", style={'padding': '20px'})
            else:
                # Pivot and group
                pivot_table = table_df.pivot_table(
                    index=['Month of Date', 'Date'], 
                    columns=['Target Country', 'Point'], 
                    values='flows_bcm', 
                    aggfunc='sum'
                ).reset_index()
                
                pivot_table = pivot_table.sort_values('Date', ascending=False)
                
                # Construct columns for dash_table
                columns = [{"name": ["", "Month of Date"], "id": "Month of Date"}]
                
                for country in sorted(table_df['Target Country'].unique()):
                    terminals_in_country = sorted(table_df[table_df['Target Country'] == country]['Point'].unique())
                    for term in terminals_in_country:
                        col_id = f"{country}_{term}"
                        columns.append({"name": [country, term], "id": col_id})
                
                data_rows = []
                for _, row in pivot_table.iterrows():
                    d = {"Month of Date": row["Month of Date"]}
                    for col in columns[1:]:
                        c_name, t_name = col["name"]
                        try:
                            val = row.get((c_name, t_name))
                            d[col["id"]] = f"{val:.3f}" if (pd.notnull(val) and val != 0) else "0"
                        except:
                            d[col["id"]] = "0"
                    data_rows.append(d)

                table_output = dash_table.DataTable(
                    columns=columns,
                    data=data_rows,
                    merge_duplicate_headers=True,
                    style_table={'overflowX': 'auto', 'border': '1px solid #ddd'},
                    style_header={
                        'backgroundColor': '#fdfdfd',
                        'fontWeight': 'bold',
                        'border': '1px solid #eee',
                        'textAlign': 'center',
                        'fontSize': '12px',
                        'padding': '5px'
                    },
                    style_cell={
                        'border': '1px solid #f0f0f0',
                        'padding': '5px 10px',
                        'textAlign': 'right',
                        'fontFamily': 'Arial, sans-serif',
                        'fontSize': '11px',
                        'minWidth': '80px'
                    },
                    style_cell_conditional=[
                        {'if': {'column_id': 'Month of Date'}, 'textAlign': 'left', 'minWidth': '130px'}
                    ],
                    style_data_conditional=[
                        {'if': {'row_index': 'odd'}, 'backgroundColor': '#f9f9f9'}
                    ],
                    fixed_rows={'headers': True}
                )

            return fig, table_output
            
        except Exception as outer_e:
            print(f"DASHBOARD CALLBACK ERROR: {outer_e}")
            return px.bar(title="Dashboard error - check logs"), html.Div(f"Error: {outer_e}")