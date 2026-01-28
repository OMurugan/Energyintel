"""
European Gas Trade - Pipeline Flows by Country
Country-specific pipeline flow analytics
"""
import os
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, callback, State, dash_table

# File Paths
DATA_DIR = "./app/dashboards/data/gas-europe_pipeline_flow_by_country/"
TABLE_CSV = os.path.join(DATA_DIR, "TABLE_Gas Pipeline Flows to Europe_data (2).csv")

# Color Palette
EI_ORANGE = "#ff6600"
EI_DARK_BLUE = "#1b365d"
EI_LIGHT_BLUE = "#e8f4f8"

# Qualitative colors for countries
COUNTRY_COLORS = {
    'United Kingdom': '#ffcc00',
    'Netherlands': '#4c78a8',
    'Italy': '#e15759',
    'Germany': '#76b7b2',
    'France': '#59a14f',
    'Spain': '#edc948',
    'Belgium': '#b07aa1',
    'Poland': '#ff9da7',
    'Finland': '#9c755f',
    'Greece': '#bab0ac',
    'Bulgaria': '#72b7b2',
    'Hungary': '#f58518',
    'Romania': '#4e79a7',
    'Slovakia': '#e15759',
    'Denmark': '#76b7b2'
}

def load_data():
    """Load and preprocess the CSV data"""
    try:
        if not os.path.exists(TABLE_CSV):
            return pd.DataFrame()
        
        df = pd.read_csv(TABLE_CSV)
        # Handle BOM if present
        if df.columns[0].startswith('\ufeff'):
            df.columns = [df.columns[0].replace('\ufeff', '')] + list(df.columns[1:])
            
        df['Day of Date'] = pd.to_datetime(df['Day of Date'])
        df['flows_bcm'] = pd.to_numeric(df['flows_bcm'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

def create_layout():
    """Create the European Pipeline Flows by Country layout"""
    df = load_data()
    if df.empty:
        return html.Div("Data file not found or empty.", style={'padding': '50px', 'textAlign': 'center'})

    origins = sorted(df['Gas Origin'].unique().tolist())
    destinations = sorted(df['Target Country'].unique().tolist())
    max_date = df['Day of Date'].max()

    return html.Div([
        # Main container with Flexbox for Sidebar and Content
        html.Div([
            
            # Sidebar Filter (Right side)
            html.Div([
                html.Div([
                    html.Label("Start Date", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE}),
                    dcc.DatePickerSingle(
                        id='gas-country-start-date',
                        date='2021-01-01',
                        display_format='M/D/YYYY',
                        style={'width': '100%', 'marginBottom': '15px'}
                    ),
                    
                    html.Label("End Date", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE}),
                    dcc.DatePickerSingle(
                        id='gas-country-end-date',
                        date=max_date.strftime('%Y-%m-%d') if pd.notnull(max_date) else '2026-01-09',
                        display_format='M/D/YYYY',
                        style={'width': '100%', 'marginBottom': '20px'}
                    ),
                    
                    # Gas Origin Filter
                    html.Div([
                        html.Span("Gas Origin", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE}),
                        html.I(className="fas fa-search", style={'fontSize': '10px', 'color': '#999', 'marginLeft': '5px'})
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px'}),
                    
                    dcc.Checklist(
                        id='gas-country-origin-checklist',
                        options=[{'label': f' {o}', 'value': o} for o in origins],
                        value=origins,
                        style={'fontSize': '12px', 'color': '#666', 'padding': '5px', 'border': '1px solid #ddd', 'backgroundColor': 'white', 'maxHeight': '120px', 'overflowY': 'auto'},
                        labelStyle={'display': 'block', 'marginBottom': '2px', 'paddingLeft': '5px'}
                    ),
                    
                    # Destination Filter
                    html.Div([
                        html.Span("Destination", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE, 'marginTop': '15px', 'display': 'block'}),
                    ], style={'marginBottom': '5px'}),
                    
                    dcc.Checklist(
                        id='gas-country-dest-checklist',
                        options=[{'label': f' {o}', 'value': o} for o in destinations],
                        value=destinations if len(destinations) < 10 else destinations[:10], # Default to some if too many
                        style={'fontSize': '12px', 'color': '#666', 'padding': '5px', 'border': '1px solid #ddd', 'backgroundColor': 'white', 'maxHeight': '250px', 'overflowY': 'auto'},
                        labelStyle={'display': 'block', 'marginBottom': '2px', 'paddingLeft': '5px'}
                    ),
                    
                    # Legend (Simplified for countries)
                    html.Div([
                        html.Label("Destination Legend", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': EI_DARK_BLUE, 'marginTop': '20px', 'display': 'block'}),
                        html.Div([
                            html.Div([
                                html.Div(style={'width': '10px', 'height': '10px', 'backgroundColor': COUNTRY_COLORS.get(dest, '#ccc'), 'marginRight': '5px'}),
                                html.Span(dest, style={'fontSize': '10px', 'color': '#666'})
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '2px'})
                            for dest in sorted(COUNTRY_COLORS.keys())[:10]
                        ])
                    ])
                ], style={'padding': '15px', 'backgroundColor': '#fcfcfc', 'border': '1px solid #eee', 'height': '100%'})
            ], style={'width': '180px', 'order': '2', 'marginLeft': '15px'}),
            
            # Content Area (Left side)
            html.Div([
                html.H3("All's Pipeline gas Flows to Europe -Billion Cubic Meters", style={
                    'color': EI_ORANGE, 'fontSize': '20px', 'fontWeight': 'bold',
                    'margin': '0 0 10px 0', 'fontFamily': 'Lato, sans-serif'
                }),
                
                dcc.Loading(
                    id='loading-gas-country-chart',
                    type='circle',
                    children=dcc.Graph(
                        id='gas-country-line-chart',
                        style={'height': '500px'},
                        config={'displayModeBar': False}
                    )
                ),
                
                html.H3("Gas Pipeline Flows to Europe-Billion Cubic Meters", style={
                    'color': EI_ORANGE, 'fontSize': '20px', 'fontWeight': 'bold',
                    'margin': '30px 0 10px 0', 'fontFamily': 'Lato, sans-serif'
                }),
                
                html.Div(id='gas-country-table-container', style={'marginTop': '10px'})
            ], style={'flex': '1', 'order': '1', 'minWidth': '0', 'overflow': 'hidden'})
            
        ], style={'display': 'flex', 'padding': '15px'})
    ], className='tab-content', style={'backgroundColor': 'white', 'maxWidth': '1450px', 'margin': '0 auto'})


def register_callbacks(dash_app, server):
    """Register all callbacks for European Pipeline Flows by Country"""
    
    @dash_app.callback(
        Output('gas-country-line-chart', 'figure'),
        [Input('gas-country-start-date', 'date'),
         Input('gas-country-end-date', 'date'),
         Input('gas-country-origin-checklist', 'value'),
         Input('gas-country-dest-checklist', 'value')]
    )
    def update_chart(start_date, end_date, selected_origins, selected_dests):
        if not selected_origins or not selected_dests:
            return go.Figure()

        df = load_data()
        if df.empty:
            return go.Figure()

        # Filter
        mask = (df['Day of Date'] >= pd.to_datetime(start_date)) & \
               (df['Day of Date'] <= pd.to_datetime(end_date)) & \
               (df['Gas Origin'].isin(selected_origins)) & \
               (df['Target Country'].isin(selected_dests))
        
        filtered_df = df[mask].copy()
        
        if filtered_df.empty:
            return go.Figure()

        # Aggregation for Chart: Monthly by Target Country
        filtered_df['Month'] = filtered_df['Day of Date'].dt.to_period('M').dt.to_timestamp()
        chart_df = filtered_df.groupby(['Month', 'Target Country'])['flows_bcm'].sum().reset_index()
        
        fig = go.Figure()
        
        for dest in selected_dests:
            dest_df = chart_df[chart_df['Target Country'] == dest].sort_values('Month')
            if not dest_df.empty:
                fig.add_trace(go.Scatter(
                    x=dest_df['Month'],
                    y=dest_df['flows_bcm'],
                    name=dest,
                    mode='lines',
                    line=dict(width=2, color=COUNTRY_COLORS.get(dest, None)),
                    hovertemplate="<b>" + dest + "</b><br>Date: %{x|%b %Y}<br>Volume: %{y:.4f} Bcm<extra></extra>"
                ))

        fig.update_layout(
            margin=dict(l=40, r=20, t=10, b=40),
            paper_bgcolor='white',
            plot_bgcolor='white',
            hovermode='x unified',
            showlegend=False,
            xaxis=dict(
                showgrid=True, gridcolor='#f5f5f5',
                tickfont=dict(size=10, color='#999'),
                tickformat="%b %y", dtick="M6"
            ),
            yaxis=dict(
                showgrid=True, gridcolor='#f5f5f5',
                tickfont=dict(size=10, color='#999'),
                zeroline=True, zerolinecolor='#f5f5f5'
            ),
            font=dict(family="Lato, sans-serif")
        )
        return fig

    @dash_app.callback(
        Output('gas-country-table-container', 'children'),
        [Input('gas-country-start-date', 'date'),
         Input('gas-country-end-date', 'date'),
         Input('gas-country-origin-checklist', 'value'),
         Input('gas-country-dest-checklist', 'value')]
    )
    def update_table(start_date, end_date, selected_origins, selected_dests):
        if not selected_origins or not selected_dests:
            return html.Div("Please select filters.", style={'color': '#666', 'fontSize': '12px', 'padding': '20px'})

        df = load_data()
        if df.empty:
            return html.Div("No data available.")

        mask = (df['Day of Date'] >= pd.to_datetime(start_date)) & \
               (df['Day of Date'] <= pd.to_datetime(end_date)) & \
               (df['Gas Origin'].isin(selected_origins)) & \
               (df['Target Country'].isin(selected_dests))
        
        filtered_df = df[mask].copy()
        if filtered_df.empty:
            return html.Div("No data matches filters.", style={'padding': '20px'})

        # Pivot for multi-level headers
        pivot_df = filtered_df.pivot_table(
            index='Day of Date',
            columns=['Header_Exporter', 'Gas Origin', 'Header_Importer', 'Target Country', 'Interconnection Point'],
            values='flows_bcm',
            aggfunc='sum'
        ).reset_index()
        
        # Sort by date descending
        pivot_df = pivot_df.sort_values('Day of Date', ascending=False)
        
        date_col = pivot_df.columns[0]
        hier_cols = [c for c in pivot_df.columns if c != date_col]
        hier_cols.sort(key=lambda x: (x[1], x[3], x[4]))

        table_columns = [{"name": ["", "", "", "", "Day of Date"], "id": "Day of Date"}]
        for col in hier_cols:
            table_columns.append({
                "name": list(col),
                "id": "_".join(map(str, col))
            })

        # Prepare data rows
        pivot_df_display = pivot_df.copy()
        pivot_df_display['Day of Date'] = pivot_df_display['Day of Date'].dt.strftime('%B %d, %Y')
        
        table_data = []
        for _, row in pivot_df_display.iterrows():
            d_row = {"Day of Date": row['Day of Date']}
            for col in hier_cols:
                val = row[col]
                col_id = "_".join(map(str, col))
                d_row[col_id] = f"{val:.4f}" if pd.notnull(val) else ""
            table_data.append(d_row)

        return dash_table.DataTable(
            columns=table_columns,
            data=table_data,
            merge_duplicate_headers=True,
            style_table={'overflowX': 'auto', 'width': '100%'},
            style_header={
                'backgroundColor': 'white', 'color': EI_DARK_BLUE, 'fontWeight': 'bold',
                'textAlign': 'center', 'fontSize': '10px', 'fontFamily': 'Lato, sans-serif',
                'border': '1px solid #dee2e6', 'padding': '5px', 'height': 'auto'
            },
            style_cell={
                'padding': '5px', 'textAlign': 'center', 'fontSize': '10px',
                'fontFamily': 'Lato, sans-serif', 'border': '1px solid #dee2e6',
                'color': '#333', 'minWidth': '80px'
            },
            style_data_conditional=[
                {'if': {'column_id': 'Day of Date'}, 'textAlign': 'left', 'minWidth': '150px'},
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}
            ],
            style_header_conditional=[
                {'if': {'header_index': 0}, 'border': 'none', 'textAlign': 'right', 'paddingRight': '20px'},
                {'if': {'header_index': 1}, 'backgroundColor': '#e9ecef'},
                {'if': {'header_index': 2}, 'backgroundColor': 'white'}
            ],
            fixed_rows={'headers': True}
        )