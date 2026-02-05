"""
European Gas Demand - Monthly Demand by Sector
Monthly gas demand analytics by sector
"""
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import dcc, html, dash_table, Input, Output, State, callback
from datetime import datetime, date
import os


def load_data():
    """Load the sector demand data"""
    try:
        # Load table data
        table_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'sector', 'Table_Demand by Sector_data.csv')
        df_table = pd.read_csv(table_path)
        
        # Load chart data  
        chart_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'sector', 'Column Chart_Demand by Sector_data.csv')
        df_chart = pd.read_csv(chart_path)
        
        # Process table data - create date from year and month
        df_table['Date'] = pd.to_datetime(df_table['Year of Date'].astype(str) + '-' + df_table['Month of Date'] + '-01')
        
        # Process chart data - parse the Month of Date column
        df_chart['Date'] = pd.to_datetime(df_chart['Month of Date'], format='%B %Y', errors='coerce')
        
        # Filter chart data to only include "In" Europe data and aggregate by sector
        df_chart_filtered = df_chart[df_chart['In / Out of Europe Country Set'] == 'In'].copy()
        
        print(f"Loaded table data: {len(df_table)} rows")
        print(f"Loaded chart data: {len(df_chart_filtered)} rows")
        print(f"Table columns: {df_table.columns.tolist()}")
        print(f"Chart columns: {df_chart_filtered.columns.tolist()}")
        
        return df_table, df_chart_filtered
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
    
    if not df_table.empty and not df_chart.empty:
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
        
        # Define dimmed colors for sectors
        sector_colors_dimmed = {
            'Household': 'rgba(0, 110, 176, 0.15)',
            'Industrial': 'rgba(197, 217, 165, 0.15)',
            'Power': 'rgba(176, 78, 38, 0.15)'
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
        
        # Adjust Y-axis values to reflect "K" (divide by 1000 if needed, assuming the image shows K)
        # Based on image, 60K, 50K...
        initial_fig.update_yaxes(tickvals=[0, 10000, 20000, 30000, 40000, 50000, 60000], 
                                ticktext=['0K', '10K', '20K', '30K', '40K', '50K', '60K'])
        
        # Create initial table data (show all available data, not just recent)
        table_df = df_table.copy()
        if not table_df.empty:
            table_df['Month'] = table_df['Date'].dt.strftime('%B')
            table_df['Year'] = table_df['Date'].dt.year
            
            # Match the table structure from image: Year Grouping (2025, 2024, etc.)
            # Month columns, and a "Total" for each year.
            
            years = sorted(table_df['Year'].unique(), reverse=True)
            initial_columns = [
                {"name": ["", "Country"], "id": "Country"},
                {"name": ["", "Sector"], "id": "Sector"},
            ]
            
            # Prepare hierarchical data using helper
            processed_data, years = prepare_hierarchical_data(table_df)
            
            # Build Columns with multi-level headers
            for year in years:
                # Add months for this year in reverse order
                year_months = sorted(table_df[table_df['Year'] == year]['Month'].unique(), 
                                   key=lambda m: datetime.strptime(m, '%B').month, reverse=True)
                for month in year_months:
                    initial_columns.append({"name": [str(year), month], "id": f"{year}_{month}"})
                # Add Total for this year
                initial_columns.append({"name": [str(year), "Total"], "id": f"{year}_Total"})
            
            initial_data = processed_data
    
    return html.Div([
        # Store components for data
        dcc.Store(id='min-date', data=min_date.isoformat() if not df_table.empty else '2019-01-01'),
        dcc.Store(id='max-date', data=max_date.isoformat() if not df_table.empty else '2025-10-01'),
        dcc.Store(id='sector-demand-selection-store', data={'sector': None, 'x_val': None, 'type': None, 'country': None, 'year': None}),
        dcc.Input(id='sector-demand-header-click-input', style={'display': 'none'}),
        html.Div(id='sector-demand-table-enhancer-anchor', style={'display': 'none'}),
        
        # Main container
        html.Div([
            # Main content area (left side)
            html.Div([
                # Chart
                html.Div([
                    html.H3("Monthly Gas Demand by Sector", style={
                        'color': '#f45d2d', 
                        'marginBottom': '20px',
                        'fontSize': '24px',
                        'fontWeight': 'normal',
                        'fontFamily': 'Georgia, serif'
                    }),
                    dcc.Graph(
                        id='sector-demand-chart',
                        figure=initial_fig,
                        style={'height': '500px'},
                        config={'displayModeBar': True, 'displaylogo': False}
                    )
                ], style={'marginBottom': '30px'}),
                
                # Data Table
                html.Div([
                    dash_table.DataTable(
                        id='sector-demand-table',
                        columns=initial_columns,
                        data=initial_data,
                        merge_duplicate_headers=True,
                        style_table={'overflowX': 'auto', 'maxHeight': '800px', 'overflowY': 'auto'},
                        style_cell={
                            'textAlign': 'right',
                            'fontSize': '12px',
                            'fontFamily': 'Arial, sans-serif',
                            'padding': '8px',
                            'border': '1px solid #ddd',
                            'minWidth': '80px',
                        },
                        style_cell_conditional=[
                            {
                                'if': {'column_id': 'Country'},
                                'textAlign': 'left',
                                'borderRight': '1.5px solid #bbb'
                            },
                            {
                                'if': {'column_id': 'Sector'},
                                'textAlign': 'left',
                                'borderRight': '1.5px solid #bbb'
                            }
                        ],
                        style_header={
                            'backgroundColor': '#f9f9f9',
                            'fontWeight': 'bold',
                            'border': '1px solid #ddd',
                            'borderRight': '1.5px solid #bbb',
                            'fontSize': '11px',
                            'textAlign': 'center',
                            'color': '#333'
                        },
                        style_data_conditional=[
                            {
                                'if': {'column_id': 'Country'},
                                'textAlign': 'left',
                                'fontWeight': 'bold',
                                'backgroundColor': '#f9f9f9',
                                'borderRight': '1.5px solid #bbb'
                            },
                            {
                                'if': {'column_id': 'Sector'},
                                'textAlign': 'left',
                                'paddingLeft': '10px',
                                'borderRight': '1.5px solid #bbb'
                            },
                            # Grey background for Total rows
                            {
                                'if': {
                                    'filter_query': '{Sector} eq "Total"'
                                },
                                'fontWeight': 'bold',
                                'backgroundColor': '#f2f2f2'
                            },
                            # Grey background for Total columns
                            {
                                'if': {
                                    'column_id': [c['id'] for c in initial_columns if 'Total' in str(c.get('name', ''))]
                                },
                                'fontWeight': 'bold',
                                'backgroundColor': '#f2f2f2'
                            }
                        ],
                        style_data={
                            'backgroundColor': 'white',
                            'color': '#444'
                        },
                        css=[
                            {
                                'selector': '.dash-spreadsheet-container td',
                                'rule': 'transition: opacity 0.15s ease-in-out, background-color 0.1s ease;'
                            },
                            {
                                'selector': '.dash-spreadsheet-container.selection-active td',
                                'rule': 'opacity: 0.3 !important;'
                            },
                            {
                                'selector': '.dash-spreadsheet-container.selection-active td.focused-cell, .dash-spreadsheet-container.selection-active td.active-label, .dash-spreadsheet-container.selection-active td.focused-header, .dash-spreadsheet-container.selection-active th.focused-header',
                                'rule': 'opacity: 1 !important;'
                            }
                        ]
                    )
                ])
                
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
    
    @dash_app.callback(
        [Output('sector-demand-chart', 'figure'),
         Output('sector-demand-table', 'columns'),
         Output('sector-demand-table', 'data'),
         Output('sector-demand-table', 'style_data_conditional'),
         Output('sector-demand-table', 'style_header_conditional')],
        [Input('date-range-slider', 'value'),
         Input('unit-selector', 'value'),
         Input('country-checklist', 'value'),
         Input('highlight-country', 'value'),
         Input('min-date', 'data'),
         Input('max-date', 'data'),
         Input('sector-demand-selection-store', 'data')]
    )
    def update_chart_and_table(date_range, unit, selected_countries, highlight_country, min_date_str, max_date_str, selection):
        """Update chart and table based on filters"""
        df_table, df_chart = load_data()
        
        if df_table.empty and df_chart.empty:
            print("Both dataframes are empty!")
            return {}, [], []
        
        # Use table data for both chart and table if available
        if not df_table.empty:
            df_to_use = df_table.copy()
        else:
            df_to_use = df_chart.copy()
        
        print(f"Using dataframe with {len(df_to_use)} rows")
        
        # Convert date strings back to datetime
        min_date = pd.to_datetime(min_date_str)
        max_date = pd.to_datetime(max_date_str)
        
        # Filter by date range
        date_range_start = min_date + (max_date - min_date) * (date_range[0] / 100)
        date_range_end = min_date + (max_date - min_date) * (date_range[1] / 100)
        
        df_filtered = df_to_use[
            (df_to_use['Date'] >= date_range_start) & 
            (df_to_use['Date'] <= date_range_end)
        ].copy()
        
        print(f"After date filtering: {len(df_filtered)} rows")
        
        # Handle country filtering - if 'All' is selected or no countries selected, show all
        if not selected_countries or 'All' in selected_countries:
            # Show all countries
            pass
        else:
            # Filter by selected countries only
            df_filtered = df_filtered[df_filtered['Country'].isin(selected_countries)]
        
        print(f"After country filtering: {len(df_filtered)} rows")
        
        # For chart: Group data by date and sector (sum across all countries)
        # Use df_filtered to ensure it respects country and date filters
        chart_data = df_filtered.groupby(['Date', 'Sector'])['Value'].sum().reset_index()
        
        chart_data['Year-Month'] = chart_data['Date'].dt.strftime('%b %Y')
        chart_data['Full-Month'] = chart_data['Date'].dt.strftime('%B %Y')
        chart_data = chart_data.sort_values('Date')
        
        print(f"Chart data: {len(chart_data)} rows")
        print(f"Unique sectors in chart: {chart_data['Sector'].unique()}")
        
        # Create stacked bar chart
        fig = go.Figure()
        
        # Define colors for sectors (matching the image)
        sector_colors = {
            'Household': '#006eb0',  # Blue
            'Industrial': '#c5d9a5', # Light Green
            'Power': '#b04e26'       # Brown/Red
        }
        
        # Define dimmed colors for sectors
        sector_colors_dimmed = {
            'Household': 'rgba(0, 110, 176, 0.15)',
            'Industrial': 'rgba(197, 217, 165, 0.15)',
            'Power': 'rgba(176, 78, 38, 0.15)'
        }
        
        # Add bars for each sector in the correct order (bottom to top)
        for sector in ['Power', 'Industrial', 'Household']:
            sector_data = chart_data[chart_data['Sector'] == sector]
            if not sector_data.empty:
                # Check if this sector is selected
                selected_sector = selection.get('sector') if selection else None
                selected_x = selection.get('x_val') if selection else None
                
                print(f"DEBUG APP: Sector={sector}, Selection={selection}")
                
                # Determine colors and border based on selection
                marker_colors = []
                marker_line_widths = []
                marker_line_colors = []
                
                for _, row in sector_data.iterrows():
                    is_selected = (str(selected_sector) == str(sector) and str(selected_x) == str(row['Year-Month']))
                    base_color = sector_colors.get(sector, '#1f77b4')
                    dimmed_color = sector_colors_dimmed.get(sector, 'rgba(0,0,0,0.1)')
                    
                    if selection and selection.get('sector') is not None:
                        # If something is selected, dim others
                        if is_selected:
                            marker_colors.append(base_color)
                            marker_line_widths.append(2)
                            marker_line_colors.append('black')
                        else:
                            # Dimming non-selected bars
                            marker_colors.append(dimmed_color)
                            marker_line_widths.append(0)
                            marker_line_colors.append('rgba(0,0,0,0)')
                    else:
                        marker_colors.append(base_color)
                        marker_line_widths.append(0)
                        marker_line_colors.append('rgba(0,0,0,0)')

                # Determine country label for tooltip
                country_label = highlight_country if highlight_country else "*"
                if not highlight_country and selected_countries and 'All' not in selected_countries:
                    if len(selected_countries) == 1:
                        country_label = selected_countries[0]
                    else:
                        country_label = "*"

                fig.add_trace(go.Bar(
                    name=sector,
                    x=sector_data['Year-Month'],
                    y=sector_data['Value'],
                    marker=dict(
                        color=marker_colors,
                        line=dict(
                            width=marker_line_widths,
                            color=marker_line_colors
                        )
                    ),
                    customdata=sector_data[['Full-Month', 'Year-Month']],
                    hovertemplate=(
                        f"Sector: <b>{sector}</b><br>"
                        "Month of Date: %{customdata[0]}<br>"
                        f"Country: {country_label}<br>"
                        f"Value: %{{y:,.0f}}<br>"
                        f"Unit: {unit}"
                        "<extra></extra>"
                    ),
                    hoverinfo="all" if not (selection and selection.get('sector') is not None) else ["all" if (str(selected_sector) == str(sector) and str(selected_x) == str(xm)) else "skip" for xm in sector_data['Year-Month']],
                    hoverlabel=dict(
                        bgcolor="white",
                        font_size=12,
                        font_family="Arial",
                        font_color="#333"
                    )
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
        
        # Update x-axis
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
        
        # Create table data exactly like in the image
        # Group by Country and Sector, then pivot by months
        table_df = df_filtered.copy()
        
        if table_df.empty:
            print("Table dataframe is empty after filtering!")
            return fig, [], []
        
        # Prepare hierarchical data using helper
        processed_data, years = prepare_hierarchical_data(table_df)
        
        columns = [
            {"name": ["", "Country"], "id": "Country"},
            {"name": ["", "Sector"], "id": "Sector"},
        ]
        
        # Build Columns with multi-level headers
        for year in years:
            # Add months for this year in reverse order
            year_months = sorted(table_df[table_df['Year'] == year]['Month'].unique(), 
                               key=lambda m: datetime.strptime(m, '%B').month, reverse=True)
            for month in year_months:
                columns.append({"name": [str(year), month], "id": f"{year}_{month}"})
            # Add Total for this year
            columns.append({"name": [str(year), "Total"], "id": f"{year}_Total"})
        
        data = processed_data
        
        # Prepare style_data_conditional for table highlighting
        style_data_conditional = [
            {
                'if': {'column_id': 'Country'},
                'textAlign': 'left',
                'fontWeight': 'bold',
                'backgroundColor': '#f9f9f9',
                'minWidth': '120px',
                'borderRight': '1.5px solid #bbb'
            },
            {
                'if': {'column_id': 'Sector'},
                'textAlign': 'left',
                'paddingLeft': '10px',
                'minWidth': '100px',
                'borderRight': '1.5px solid #bbb'
            },
            # Bold and highlight Total rows (Grey background)
            {
                'if': {
                    'filter_query': '{Sector} eq "Total"'
                },
                'fontWeight': 'bold',
                'backgroundColor': '#f2f2f2'
            },
            # Bold and highlight Total columns (Grey background)
            {
                'if': {
                    'column_id': [c['id'] for c in columns if 'Total' in str(c.get('name', ''))]
                },
                'fontWeight': 'bold',
                'backgroundColor': '#f2f2f2'
            }
        ]
        
        style_header_conditional = [
            {
                'if': {'header_index': 0},
                'backgroundColor': '#f8f9fa',
                'fontWeight': 'bold',
                'textAlign': 'center'
            },
            {
                'if': {'header_index': 1},
                'backgroundColor': '#ffffff',
                'textAlign': 'center'
            }
        ]

        # The clientside callback will now handle the "focus" and "dimming" visuals
        # using CSS classes for a higher performance "Global Price" experience.
        
        print(f"Table: {len(data)} rows, {len(columns)} columns")
        
        return fig, columns, data, style_data_conditional, style_header_conditional

        print(f"Table: {len(data)} rows, {len(columns)} columns")
        
        return fig, columns, data, style_data_conditional, style_header_conditional
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
            sector = None
            if point.get('legendgroup'):
                sector = str(point.get('legendgroup')).strip()
            elif point.get('name'):
                sector = str(point.get('name')).strip()
            
            custom_data = point.get('customdata')
            x_val = custom_data[1] if custom_data and len(custom_data) > 1 else point.get('x')
            
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

    # Clientside callback for table highlighting logic (Global Price Style)
    dash_app.clientside_callback(
        """
        function(selection, id) {
            const tableId = 'sector-demand-table';
            const inputId = 'sector-demand-header-click-input';
            
            const tableEl = document.getElementById(tableId);
            const inputEl = document.querySelector('#sector-demand-header-click-input');
            if (!tableEl) return null;
            
            const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
            if (!spreadsheet) return null;

            // Ensure Style is injected
            if (spreadsheet.dataset.globalPriceStyle !== 'true') {
                spreadsheet.dataset.globalPriceStyle = 'true';
                const styleId = 'sector-demand-table-focus-css';
                if (!document.getElementById(styleId)) {
                    const style = document.createElement('style');
                    style.id = styleId;
                    style.innerHTML = `
                        #sector-demand-table .dash-spreadsheet-container td {
                            transition: opacity 0.1s ease-in-out, background-color 0.1s ease;
                        }
                        /* Selection active state - fade out everything else */
                        #sector-demand-table .dash-spreadsheet-container.selection-active td {
                            opacity: 0.3 !important;
                        }
                        /* Except the focused cells */
                        #sector-demand-table .dash-spreadsheet-container.selection-active td.focused-cell,
                        #sector-demand-table .dash-spreadsheet-container.selection-active td.active-label,
                        #sector-demand-table .dash-spreadsheet-container.selection-active td.focused-header,
                        #sector-demand-table .dash-spreadsheet-container th.focused-header {
                            opacity: 1 !important;
                        }
                        /* Focused cell background */
                        #sector-demand-table .dash-spreadsheet-container td.focused-cell {
                            background-color: #e7f3ff !important;
                            color: #333 !important;
                        }
                        /* Active label cell */
                        #sector-demand-table .dash-spreadsheet-container td.active-label {
                            background-color: #006eb0 !important;
                            color: white !important;
                            font-weight: bold !important;
                        }
                        /* Header focus */
                        #sector-demand-table .dash-spreadsheet-container th.focused-header {
                            background-color: #006eb0 !important;
                            color: white !important;
                            font-weight: bold !important;
                            border-bottom: 2px solid #004a7a !important;
                        }
                    `;
                    document.head.appendChild(style);
                }

                // Add click listener for headers ONLY (server handles table body clicks via active_cell)
                spreadsheet.addEventListener('click', function(e) {
                    const cell = e.target.closest('th');
                    if (!cell) return;
                    
                    const colId = cell.getAttribute('data-dash-column');
                    const row = cell.closest('tr');
                    
                    const isYearRow = row && row.rowIndex === 0;
                    if (isYearRow) {
                        const yearText = cell.innerText.trim();
                        if (/^\\d{4}$/.test(yearText)) {
                            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                            setter.call(inputEl, 'year|' + yearText + '|' + Date.now());
                            inputEl.dispatchEvent(new Event('input', { bubbles: true }));
                            inputEl.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    } else if (colId && colId !== 'Country' && colId !== 'Sector') {
                        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                        setter.call(inputEl, 'month|' + colId + '|' + Date.now());
                        inputEl.dispatchEvent(new Event('input', { bubbles: true }));
                        inputEl.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }, true);
            }

            // Sync visual state with selection store
            const clearVisuals = () => {
                spreadsheet.classList.remove('selection-active');
                spreadsheet.querySelectorAll('.focused-cell, .active-label, .focused-header').forEach(el => {
                    el.classList.remove('focused-cell', 'active-label', 'focused-header');
                });
            };

            clearVisuals();

            if (selection && selection.type) {
                spreadsheet.classList.add('selection-active');
                const selType = selection.type;
                const selCountry = selection.country;
                const selSector = selection.sector;
                const selX = selection.x_val;
                const selYear = selection.year;

                // Use internal logic to find the Month/Year column ID from Chart label if needed
                let colId = selX;
                if (selType === 'chart' && selX) {
                    const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
                    const monthMap = {"Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April", "May": "May", "Jun": "June", "Jul": "July", "Aug": "August", "Sep": "September", "Oct": "October", "Nov": "November", "Dec": "December"};
                    const parts = selX.split(' ');
                    if (parts.length === 2) {
                        const m = monthMap[parts[0]] || parts[0];
                        colId = parts[1] + '_' + m;
                    }
                }

                if ((selType === 'table-country' || selType === 'table-sector') && selCountry) {
                    // Highlight the country name cell
                    spreadsheet.querySelectorAll('td[data-dash-column="Country"]').forEach(td => {
                        if (td.innerText.trim() === selCountry) {
                            td.classList.add('active-label');
                            // Highlight all rows in this country's group
                            let currentRow = td.closest('tr');
                            while (currentRow) {
                                // Add focused background to all data cells in this country group
                                currentRow.querySelectorAll('td:not([data-dash-column="Country"]):not([data-dash-column="Sector"])').forEach(c => {
                                    c.classList.add('focused-cell');
                                });
                                // Highlight the Sector labels in this group
                                currentRow.querySelectorAll('td[data-dash-column="Sector"]').forEach(c => {
                                    if (selType === 'table-sector' && c.innerText.trim() === selSector) {
                                        c.classList.add('active-label');
                                    } else {
                                        c.classList.add('focused-cell');
                                    }
                                });
                                
                                currentRow = currentRow.nextElementSibling;
                                if (!currentRow || (currentRow.querySelector('td[data-dash-column="Country"]') && currentRow.querySelector('td[data-dash-column="Country"]').innerText.trim() !== "")) {
                                    break;
                                }
                            }
                        }
                    });
                } else if (selType === 'table-column' && colId) {
                    spreadsheet.querySelectorAll(`td[data-dash-column="${colId}"]`).forEach(td => {
                        td.classList.add('focused-cell');
                    });
                    spreadsheet.querySelectorAll(`th[data-dash-column="${colId}"]`).forEach(th => {
                        th.classList.add('focused-header');
                    });
                } else if (selType === 'table-year' && selYear) {
                    const prefix = selYear + '_';
                    spreadsheet.querySelectorAll(`td[data-dash-column^="${prefix}"]`).forEach(td => {
                        td.classList.add('focused-cell');
                    });
                    spreadsheet.querySelectorAll(`th[data-dash-column^="${prefix}"]`).forEach(th => {
                        th.classList.add('focused-header');
                    });
                } else if (selType === 'chart' && selSector && colId) {
                    // Intersection highlight
                    spreadsheet.querySelectorAll(`td[data-dash-column="${colId}"]`).forEach(td => {
                        const rowSector = td.closest('tr').querySelector('td[data-dash-column="Sector"]');
                        if (rowSector && rowSector.innerText.trim() === selSector) {
                            td.classList.add('active-label'); // The core intersection
                        } else {
                            td.classList.add('focused-cell'); // The column rest
                        }
                    });
                    spreadsheet.querySelectorAll('td[data-dash-column="Sector"]').forEach(td => {
                        if (td.innerText.trim() === selSector) {
                            td.classList.add('active-label');
                        }
                    });
                    spreadsheet.querySelectorAll(`th[data-dash-column="${colId}"]`).forEach(th => {
                        th.classList.add('focused-header');
                    });
                }
            }

            return null;
        }
        """,
        Output('sector-demand-table-enhancer-anchor', 'children'),
        [Input('sector-demand-selection-store', 'data'),
         Input('sector-demand-table-enhancer-anchor', 'id')]
    )
