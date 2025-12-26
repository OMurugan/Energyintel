"""
Imports - Country Detail View
Detailed imports data by country
"""
from dash import dcc, html, Input, Output, callback, State, dash_table
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from core.data_helpers import execute_query


def load_legend_data():
    """Load region colors - static mapping based on standard regions"""
    # Define colors for each region (matching the figure exactly)
    # Based on the legend: Africa=Medium Blue, Asia-Pacific=Bright Orange, Europe=Vibrant Green,
    # FSU=Strong Red, Latin America=Medium Purple, Middle East=Dark Brown, 
    # North America=Light Pink/Magenta, Others=Medium Grey
    color_map = {
        'Africa': '#1f77b4',  # Medium Blue
        'Asia-Pacific': '#ff7f0e',  # Bright Orange
        'Europe': '#2ea12e',  # Vibrant Green
        'FSU': '#d62a2b',  # Strong Red (Crimson)
        'Latin America': '#9569be',  # Medium Purple
        'Middle East': '#8d584d',  # Dark Brown
        'North America': '#e379c3',  # Light Pink/Magenta (Hot Pink)
        'Others': '#808080'  # Medium Grey
    }
    # Regions list will be dynamically determined from the data
    regions = list(color_map.keys())
    return regions, color_map


def load_imports_by_region_data(selected_country='Japan'):
    """Load and aggregate imports data by region and year from database."""
    try:
        query = """
        SELECT
            DATE_PART('year', yr)::INT AS "Year",
            import_region AS "Exporting Region",
            import_country AS "Importer",
            SUM(vol_kbpd) AS "DataValue"
        FROM fact_wcod_imports
        WHERE
            import_country = :import_country
            AND (
                import_country NOT IN ('Australia', 'Japan', 'South Korea', 'United States')
                OR source <> 'OECD Imports'
            )
        GROUP BY
            DATE_PART('year', yr),
            import_region,
            import_country
        ORDER BY
            "Year",
            "Exporting Region";
        """
        
        rows = execute_query(query, {'import_country': selected_country})
        
        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(rows)
        # Rename columns to match expected format
        df = df.rename(columns={'Exporting Region': 'Region', 'DataValue': 'Volume'})
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce').astype('Int64')
        df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')
        df = df.dropna(subset=['Region', 'Year', 'Volume'])
        
        return df
    except Exception as e:
        print(f"Error loading imports by region: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def load_imports_by_country_crude_data(selected_country='Japan', selected_year=2023):
    """Load imports data by country and crude from database"""
    try:
        # Use exact query structure as provided
        query = """
        SELECT
            yr AS "Year",
            import_country AS "Importer",
            export_country AS "Exporter",
            COALESCE(crude_name, 'Other') AS "Crude",
            company_name AS "Company",
            vol_kbpd AS "DataValue"
        FROM fact_wcod_imports a
        WHERE
            import_country = :import_country
            AND (
                import_country NOT IN ('Australia', 'Japan', 'South Korea', 'United States')
                OR source <> 'OECD Imports'
            )
            AND yr >= (
                SELECT DATE_TRUNC('year', MAX(yr))
                FROM fact_wcod_imports
            )
            AND yr < (
                SELECT DATE_TRUNC('year', MAX(yr)) + INTERVAL '1 year'
                FROM fact_wcod_imports
            );
        """
        
        params = {'import_country': selected_country}
        
        rows = execute_query(query, params)
        
        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(rows)
        
        # Extract year from date for consistency with chart code
        if 'Year' in df.columns:
            df['Year'] = pd.to_datetime(df['Year'], errors='coerce').dt.year
            df['Year'] = pd.to_numeric(df['Year'], errors='coerce').astype('Int64')
        
        df['DataValue'] = pd.to_numeric(df['DataValue'], errors='coerce')
        
        # Clean up the data
        df = df[df['DataValue'].notna() & (df['DataValue'] > 0)]
        
        return df
    except Exception as e:
        print(f"Error loading imports by country/crude: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def load_table_data(selected_country='Japan'):
    """Load table data from database (year/quarter/month/day structure)"""
    try:
        # Use exact query structure as provided
        query = """
        SELECT
            import_region AS "Exporting Region",
            export_country AS "Exporter",
            company_name AS "Company",
            COALESCE(crude_name, 'Other') AS "Crude",
            EXTRACT(YEAR FROM yr)::INT AS "Year of Year",
            EXTRACT(QUARTER FROM yr)::INT AS "Quarter of Year",
            EXTRACT(MONTH FROM yr)::INT AS "Month of Year",
            EXTRACT(DAY FROM yr)::INT AS "Day of Year",
            vol_kbpd AS "DataValue"
        FROM fact_wcod_imports a
        WHERE
            import_country = :import_country
            AND (
                import_country NOT IN ('Australia', 'Japan', 'South Korea', 'United States')
                OR source <> 'OECD Imports'
            );
        """
        
        rows = execute_query(query, {'import_country': selected_country})
        
        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(rows)
        
        # Convert quarter integer (1-4) to string format (Q1, Q2, Q3, Q4)
        if 'Quarter of Year' in df.columns:
            quarter_map = {1: 'Q1', 2: 'Q2', 3: 'Q3', 4: 'Q4'}
            df['Quarter of Year'] = df['Quarter of Year'].map(quarter_map).fillna('').astype(str)
        
        # Convert month integer (1-12) to month name
        if 'Month of Year' in df.columns:
            month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
            def convert_month(x):
                try:
                    if pd.notna(x) and 1 <= int(x) <= 12:
                        return month_names[int(x)]
                except (ValueError, TypeError):
                    pass
                return ''
            df['Month of Year'] = df['Month of Year'].apply(convert_month).astype(str)
        
        # Clean text columns
        text_cols = ['Exporting Region', 'Exporter', 'Company', 'Crude']
        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str).str.strip()
        
        # Numeric data
        df['DataValue'] = pd.to_numeric(df['DataValue'], errors='coerce')
        df = df[df['DataValue'].notna()]
        
        # Ensure year is int
        if 'Year of Year' in df.columns:
            df['Year of Year'] = pd.to_numeric(df['Year of Year'], errors='coerce').astype('Int64')
        # Day of year to numeric if possible
        if 'Day of Year' in df.columns:
            df['Day of Year'] = pd.to_numeric(df['Day of Year'], errors='coerce')
        
        return df
    except Exception as e:
        print(f"Error loading table data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def load_available_countries():
    """Load available countries from the same imports table (import_country)"""
    try:
        query = """
        SELECT DISTINCT import_country AS "Importer"
        FROM fact_wcod_imports
        WHERE import_country IS NOT NULL
        ORDER BY import_country;
        """
        rows = execute_query(query)
        if rows:
            return [row['Importer'] for row in rows]
        return ['Japan']  # Default fallback
    except Exception as e:
        print(f"Error loading available countries: {e}")
        import traceback
        traceback.print_exc()
        return ['Japan']  # Default fallback


def create_layout():
    """Create the Imports - Country Detail layout"""
    regions, _ = load_legend_data()
    
    # Get available countries from the database
    available_countries = load_available_countries()
    
    # Set default country - use Japan if available, otherwise first in list
    default_country = 'Japan' if 'Japan' in available_countries else (available_countries[0] if available_countries else 'Japan')
    
    return html.Div([
        dcc.Store(id='selected-year-store', data=2023),  # Store selected year from chart click
        dcc.Store(id='selected-country-store', data=default_country),  # Store selected country
        dcc.Store(id='imports-expand-store', data={'years': [], 'quarters': []}),  # Track header expansion state
        dcc.Store(id='imports-time-visibility', data={'Year': True, 'Quarter': False, 'Month': False, 'Day': False}),
        
        # Country Selector
        html.Div([
            html.Label(
                "Select Importing Country",
                style={
                    'fontWeight': 'bold',
                    'fontSize': '16px',
                    'lineHeight': '18px',
                    'color': '#1b365d',
                    'marginBottom': '5px',
                    'display': 'block',
                    'fontFamily': '"Lato", "Benton Sans", "Arial", "Helvetica", sans-serif',
                    'textAlign': 'left'
                }
            ),
            dcc.Dropdown(
                id='importing-country-select',
                options=[{'label': country, 'value': country} for country in available_countries],
                value=default_country,
                clearable=False,
                searchable=True,
                style={
                    'width': '1200px',
                    'fontSize': '13px',
                    'fontFamily': '"Lato", "Benton Sans", "Arial", "Helvetica", sans-serif',
                    'color': '#1b365d',
                    'align': 'center',
                },
                className='importing-country-dropdown'
            )
        ], style={'marginBottom': '20px'}),
        
        # First Chart: Imports by Region over Time
        html.Div([
            dcc.Graph(id='imports-by-region-chart')
        ], style={'marginBottom': '30px'}),
        
        # Instruction text
        html.Div([
            html.P(
                "Click on any bar to highlight it. Use the country selector above to change the data view.",
                style={'fontSize': '13px', 'fontStyle': 'italic', 'marginBottom': '20px', 'color': '#666'}
            )
        ]),
        
        # Second Chart: Imports by Country for Selected Year
        html.Div([
            dcc.Graph(id='imports-by-country-chart')
        ], style={'marginBottom': '30px'}),
        
        # Table: Detailed Imports Data
        html.Div([
            # Time dimension toggle row (Year / Quarter / Month / Day)
            html.Div([
            # Year toggle hidden (Year always on)
            html.Div([
                html.Span("Year of Year"),
                html.Button('−', id='imports-toggle-year-btn', n_clicks=0)
            ], style={'display': 'none'}),
                html.Div([
                    html.Span("Quarter of Year", style={'fontSize': '12px', 'color': '#2c3e50', 'flex': '1'}),
                    html.Button('+', id='imports-toggle-quarter-btn', n_clicks=0, style={
                        'width': '20px', 'height': '20px', 'padding': '0',
                        'border': '1px solid #dee2e6', 'backgroundColor': '#f8f9fa',
                        'color': '#2c3e50', 'borderRadius': '3px', 'cursor': 'pointer',
                        'fontSize': '14px', 'fontWeight': 'bold', 'lineHeight': '1',
                        'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
                        'marginLeft': '8px', 'flexShrink': '0'
                    })
                ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px', 'width': '150px'}),
                html.Div([
                    html.Span("Month of Year", style={'fontSize': '12px', 'color': '#2c3e50', 'flex': '1'}),
                    html.Button('+', id='imports-toggle-month-btn', n_clicks=0, style={
                        'width': '20px', 'height': '20px', 'padding': '0',
                        'border': '1px solid #dee2e6', 'backgroundColor': '#f8f9fa',
                        'color': '#2c3e50', 'borderRadius': '3px', 'cursor': 'pointer',
                        'fontSize': '14px', 'fontWeight': 'bold', 'lineHeight': '1',
                        'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
                        'marginLeft': '8px', 'flexShrink': '0'
                    })
                ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px', 'width': '140px'}),
                html.Div([
                    html.Span("Day of Year", style={'fontSize': '12px', 'color': '#2c3e50', 'flex': '1'}),
                    html.Button('+', id='imports-toggle-day-btn', n_clicks=0, style={
                        'width': '20px', 'height': '20px', 'padding': '0',
                        'border': '1px solid #dee2e6', 'backgroundColor': '#f8f9fa',
                        'color': '#2c3e50', 'borderRadius': '3px', 'cursor': 'pointer',
                        'fontSize': '14px', 'fontWeight': 'bold', 'lineHeight': '1',
                        'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
                        'marginLeft': '8px', 'flexShrink': '0'
                    })
                ], style={'display': 'flex', 'alignItems': 'center', 'width': '130px'})
            ], style={
                'padding': '10px 0',
                'marginBottom': '10px',
                'display': 'flex',
                'justifyContent': 'flex-start',
                'alignItems': 'center',
                'gap': '10px'
            }),
            html.H4(id='imports-table-title', children="Japan Crude Oil Imports by Region and Country", className='imports-table-title'),
            dash_table.DataTable(
                id='imports-detail-table',
                data=[],
                columns=[
                    {'name': 'Exporting Region', 'id': 'Exporting Region'},
                    {'name': 'Exporter', 'id': 'Exporter'},
                    {'name': 'Company', 'id': 'Company'},
                    {'name': 'Crude', 'id': 'Crude'}
                ],
                style_table={
                    'overflowX': 'auto',
                    'overflowY': 'auto',
                    'maxHeight': '500px',
                    'fontFamily': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                    'border': '1px solid #d3d3d3',
                    'borderRadius': '4px'
                },
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px 12px',
                    'fontSize': '12px',
                    'fontFamily': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                    'border': '1px solid #e0e0e0',
                    'backgroundColor': 'white',
                    'color': '#333333',
                    'minWidth': '80px',
                    'width': 'auto',
                    'maxWidth': '200px',
                    'whiteSpace': 'normal',
                    'height': 'auto'
                },
                style_header={
                    'backgroundColor': '#f8f8f8',
                    'fontWeight': '600',
                    'border': '1px solid #d3d3d3',
                    'textAlign': 'center',
                    'fontSize': '12px',
                    'fontFamily': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                    'color': '#333333',
                    'textTransform': 'none',
                    'padding': '10px 12px'
                },
                style_data={
                    'border': '1px solid #e0e0e0',
                    'backgroundColor': 'white',
                    'color': '#333333'
                },
                css=[
                    {
                        'selector': '.dash-loading-overlay',
                        'rule': 'display: none !important;'
                    }
                ],
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#fafafa'
                    },
                    {
                        'if': {'filter_query': '{Exporting Region} = Total'},
                        'fontWeight': '600',
                        'backgroundColor': '#f0f0f0'
                    },
                    {
                        'if': {'column_id': 'Exporting Region'},
                        'minWidth': '150px',
                        'width': '150px',
                        'maxWidth': '150px'
                    },
                    {
                        'if': {'column_id': 'Exporter'},
                        'minWidth': '150px',
                        'width': '150px',
                        'maxWidth': '150px'
                    },
                    {
                        'if': {'column_id': 'Company'},
                        'minWidth': '120px',
                        'width': '120px',
                        'maxWidth': '120px'
                    },
                    {
                        'if': {'column_id': 'Crude'},
                        'minWidth': '150px',
                        'width': '150px',
                        'maxWidth': '150px'
                    }
                ],
                page_action='none',
                filter_action='none',
                sort_action='none',
                fixed_rows={'headers': True},
                merge_duplicate_headers=True,
                hidden_columns=[]
            )
        ], style={'marginBottom': '30px', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '4px', 'boxShadow': '0 1px 3px rgba(0,0,0,0.1)'}),
        
        # Source and Footer (Static content)
        html.Div([
            html.Div([
                html.P("Source: Energy Intelligence", style={'fontSize': '11px', 'marginBottom': '5px'})
            ]),
            html.Div([
                html.P("EIA Data is through June 2025", style={'fontSize': '11px', 'marginBottom': '2px'}),
                html.P("Energy Intelligence Data is through July 2025", style={'fontSize': '11px', 'marginBottom': '2px'}),
                html.P("OECD Data is through July 2025", style={'fontSize': '11px', 'marginBottom': '2px'}),
                html.P("Russian Imports Data is through August 2022", style={'fontSize': '11px', 'marginBottom': '2px'}),
                html.P("South Korea trade data source: KNOC", style={'fontSize': '11px', 'marginBottom': '2px'}),
                html.P("Countries: Select jurisdictions are included under countries for data presentation purposes.", style={'fontSize': '11px', 'marginBottom': '2px'})
            ])
        ], style={'marginTop': '20px', 'fontSize': '11px', 'color': '#666'})
    ], className='tab-content', style={'padding': '20px'})


def create_imports_by_region_chart(selected_country='Japan'):
    """Create stacked bar chart showing imports by region over time"""
    df = load_imports_by_region_data(selected_country)
    _, color_map = load_legend_data()
    
    if df.empty:
        return go.Figure()
    
    # Filter by country if needed (for now, data is already filtered to Japan)
    # Group by Region and Year, sum volumes
    df_grouped = df.groupby(['Region', 'Year'])['Volume'].sum().reset_index()
    
    # Get all years from 2006 to 2025 (matching Figure 1)
    years = sorted([y for y in df_grouped['Year'].unique() if 2006 <= y <= 2025])
    
    # Get available regions from data
    available_regions = df_grouped['Region'].unique().tolist()
    
    # Separate 'Others' and sort the rest alphabetically
    regions = sorted(available_regions)
    
    print(f"Regions order for chart: {regions}")
    
    # Reverse the regions list to change stacking order (bottom to top: Others -> ... -> Africa)
    regions.reverse()
    
    fig = go.Figure()
    
    # Add a trace for each region in the specified stacking order
    # In stacked bars, first trace is at bottom, last trace is at top
    for region in regions:
        region_data = df_grouped[df_grouped['Region'] == region]
        volumes = []
        for year in years:
            year_data = region_data[region_data['Year'] == year]
            if len(year_data) > 0:
                volumes.append(year_data['Volume'].iloc[0])
            else:
                volumes.append(0)
        
        fig.add_trace(go.Bar(
            x=years,
            y=volumes,
            name=region,
            marker_color=color_map.get(region, '#CCCCCC'),
            hovertemplate=f'Region: {region}<br>Year: %{{x}}<br>Import Volume: %{{y:,.0f}} (\'000 b/d)<extra></extra>',
            selected=dict(marker=dict(opacity=1.0)),  # Selected bars remain fully opaque
            unselected=dict(marker=dict(opacity=0.3))
            
        ))
    
    # Calculate total volumes for each year to display on top of bars
    year_totals = df_grouped.groupby('Year')['Volume'].sum()
    total_volumes = [year_totals.get(year, 0) for year in years]
    
    # Calculate max value for dynamic y-axis (4 or 5 ticks)
    max_value = max(total_volumes) if total_volumes else 4500
    import math
    # Calculate approximate interval for 4-5 ticks (divide max by 4 for 5 ticks, or by 3 for 4 ticks)
    # Prefer 5 ticks if possible, otherwise 4 ticks
    approx_interval_5 = max_value / 4  # For 5 ticks: 0, interval, 2*interval, 3*interval, 4*interval
    approx_interval_4 = max_value / 3  # For 4 ticks: 0, interval, 2*interval, 3*interval
    
    # Choose between 4 or 5 ticks based on which gives nicer numbers
    # Round intervals to nice numbers
    def round_to_nice(num):
        if num <= 250:
            return max(50, round(num / 50) * 50)
        elif num <= 500:
            return round(num / 100) * 100
        elif num <= 1000:
            return round(num / 200) * 200
        elif num <= 2000:
            return round(num / 500) * 500
        else:
            return round(num / 1000) * 1000
    
    tick_interval_5 = round_to_nice(approx_interval_5)
    tick_interval_4 = round_to_nice(approx_interval_4)
    
    # Prefer 5 ticks if the interval is reasonable, otherwise use 4
    if tick_interval_5 >= 50 and (tick_interval_5 * 4) >= max_value:
        tick_interval = tick_interval_5
        num_ticks = 5
    else:
        tick_interval = tick_interval_4
        num_ticks = 4
    
    # Calculate y-axis max: round max up to next multiple of tick_interval to cover all data
    yaxis_max = math.ceil(max_value / tick_interval) * tick_interval
    
    # Add total values on top of bars
    fig.add_trace(go.Scatter(
        x=years,
        y=total_volumes,
        mode='text',
        text=[f'{val:,.0f}' if val > 0 else '' for val in total_volumes],
        textposition='top center',
        showlegend=False,
        hoverinfo='skip',
        textfont=dict(size=11, color='#000000')
    ))
    
    # Update layout to match Figure 1 exactly
    fig.update_layout(
        title={
            'text': f"{selected_country}'s Crude Imports by Exporting Region",
            'x': 0.5,
            'xanchor': 'center',
            'font': {
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 16,
                'color': '#ff7f0e'  # Orange color matching Figure 1
            }
        },
        xaxis=dict(
            title="Year",
            tickmode='linear',
            tick0=2006,
            dtick=1,  # Show every year
            range=[2005.5, 2025.5],  # Slight padding for better visibility
            tickfont={
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 11,
                'color': '#333333'
            },
            titlefont={
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 13,
                'color': '#333333'
            },
            showgrid=True,
            gridcolor='#e0e0e0',
            gridwidth=1,
            linecolor='#d3d3d3',
            linewidth=1
        ),
        yaxis=dict(
            title="Import Volume ('000 b/d)",
            range=[0, yaxis_max],  # Dynamic range based on max value
            tickmode='linear',
            tick0=0,
            dtick=tick_interval,  # Dynamic tick interval
            tickvals=[tick_interval * i for i in range(num_ticks)],  # Explicitly set tick values: 0, interval, 2*interval, etc.
            tickfont={
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 11,
                'color': '#333333'
            },
            titlefont={
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 13,
                'color': '#333333'
            },
            showgrid=True,
            gridcolor='#e0e0e0',
            gridwidth=1,
            linecolor='#d3d3d3',
            linewidth=1
        ),
        barmode='stack',
        height=400,
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=60, r=200, t=60, b=50),
        clickmode='select',  # Only selection, no event callbacks
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02,
            font={
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 11,
                'color': '#333333'
            },
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#d3d3d3',
            borderwidth=1,
            traceorder='normal' # Ensure legend order matches trace order
        ),
        hovermode='closest',
        hoverlabel=dict(
            bgcolor='white',
            bordercolor='#999999',
            font=dict(
                size=12,
                family='"Benton Sans", "Arial", "Helvetica", sans-serif',
                color='#000000'
            ),
            align='left'
        ),
        legend_traceorder='reversed' # Ensure legend order is reversed from trace order for ascending display
    )
    
    return fig


def create_imports_by_country_chart(selected_year=2023, selected_country='Japan'):
    """Create stacked bar chart showing imports by country for selected year, broken down by crude"""
    df = load_imports_by_country_crude_data(selected_country, selected_year)
    
    if df.empty:
        return go.Figure()
    
    # Extract the actual year from the data (since query now uses latest year dynamically)
    actual_year = int(df['Year'].iloc[0]) if 'Year' in df.columns and not df['Year'].isna().all() else selected_year
    
    # Group by Exporter and Crude, sum volumes (query returns individual records)
    df_grouped = df.groupby(['Exporter', 'Crude'])['DataValue'].sum().reset_index()
    
    # Get all exporters and order by total volume
    exporter_totals = df_grouped.groupby('Exporter')['DataValue'].sum().sort_values(ascending=False)
    exporters = exporter_totals.index.tolist()
    
    # Calculate max value for dynamic y-axis - use maximum total sum per exporter (total bar height)
    # Example: Saudi Arabia = 965, UAE = 843, Kuwait = 190.5 -> max = 965
    max_value = exporter_totals.max() if not exporter_totals.empty else 100
    # For 4 tick marks (0, interval, 2*interval, 3*interval), calculate interval from max
    # Example: max 965 -> divide by 3 = 321.67, round to nice number 250 or 300
    # Result: ticks at 0, 250, 500, 750 or 0, 300, 600, 900
    import math
    # Calculate approximate interval for 4 ticks (divide max by 3)
    approx_interval = max_value / 3
    # Round to nice number (nearest 50, 100, 200, 250, 500, etc.)
    if approx_interval <= 50:
        tick_interval = max(10, round(approx_interval / 10) * 10)
    elif approx_interval <= 100:
        tick_interval = round(approx_interval / 25) * 25
    elif approx_interval <= 250:
        tick_interval = round(approx_interval / 50) * 50
    elif approx_interval <= 500:
        tick_interval = round(approx_interval / 100) * 100
    else:
        tick_interval = round(approx_interval / 250) * 250
    
    # Calculate y-axis max: round max up to next multiple of tick_interval to cover all data
    # This ensures range covers the data while ticks are at nice intervals
    yaxis_max = math.ceil(max_value / tick_interval) * tick_interval
    
    # Define exact color mapping for each crude type
    crude_color_map = {
        'Al-Shaheen': '#2ca02c',
        'Arab Extra Light': '#ff9896',
        'Arab Heavy': '#9467bd',
        'Arab Light': '#c5b0d5',
        'Arab Medium': '#c49c94',
        'Arab Super Light': '#f7b6d2',
        'Bach Ho': '#d62728',
        'Banoco Arab Medium': '#c7c7c7',
        'Champion': '#7f7f7f',
        'Clifhead': '#c7c7c7',
        'Cossack': '#8c564b',
        'Das Blend': '#2ca02c',
        'Deodorized Field Condensate': '#98df8a',
        'Dubai': '#ff9896',
        'Ichthys Condensate': '#7f7f7f',
        'Isthmus': '#c7c7c7',
        'Ketapang': '#c7c7c7',
        'Khafji': '#d62728',
        'Kikeh': '#dbdb8d',
        'Kuwait': '#8c564b',
        'Kuwait Super Light': '#f7b6d2',
        'Lalang': '#1f77b4',
        'Mares Blend': '#aec7e8',
        'Mars Blend': '#ff7f0e',
        'Mubarras Blend': '#1f77b4',
        'Murban': '#aec7e8',
        'Napo': '#98df8a',
        'Nile Blend Sudan': '#d62728',
        'Oman': '#8c564b',
        'Oriente': '#ff9896',
        'Pyrenees': '#c49c94',
        'Qatar Land': '#c7c7c7',
        'Qatar Low Sulphur Condensate': '#bcbd22',
        'Qatar Marine': '#dbdb8d',
        'Ruby': '#f7b6d2',
        'Sakhalin Blend': '#ff9896',
        'Sepat': '#bcbd22',
        'Seria Light': '#17becf',
        'Stag': '#9edae5',
        'Thang Long': '#ffbb78',
        'Umm Lulu': '#bcbd22',
        'Upper Zakum': '#9edae5',
        'Wandoo': '#2ca02c',
        'West Texas Intermediate': '#aec7e8',
        'West Texas Light': '#ff7f0e'
    }
    
    # Get unique crudes from data
    available_crudes = df_grouped['Crude'].unique().tolist()

    # Separate 'Other' and sort the rest alphabetically
    crudes = sorted(available_crudes)
    
    print(f"Crudes order for chart: {crudes}")
    
    # Reverse the crudes list to change stacking order (bottom to top: Other -> ... -> Al-Shaheen)
    crudes.reverse()
    
    fig = go.Figure()
    
    # Store volumes for each crude to calculate cumulative positions for text labels
    crude_volumes_dict = {}
    
    # Add a trace for each crude
    for crude in crudes:
        crude_data = df_grouped[df_grouped['Crude'] == crude]
        volumes = []
        for exporter in exporters:
            exporter_data = crude_data[crude_data['Exporter'] == exporter]
            if len(exporter_data) > 0:
                volumes.append(exporter_data['DataValue'].iloc[0])
            else:
                volumes.append(0)
        
        # Only add trace if there's at least one non-zero value
        if sum(volumes) > 0:
            # Format year as "01-01-YYYY" for hover tooltip
            year_str = f"01-01-{actual_year}"
            # Use rgba format for crudes not in color map (Other crudes)
            # Convert #1f77b400 to rgba(31, 119, 180, 0.25) - semi-transparent blue
            # Note: 00 in hex alpha = 0 (fully transparent), using 0.25 for visibility
            crude_color = crude_color_map.get(crude, 'rgba(31, 119, 180, 1)')
            fig.add_trace(go.Bar(
                x=exporters,
                y=volumes,
                name=crude,
                marker_color=crude_color,
                hovertemplate=f'Crude: {crude}<br>Year: {year_str}<br>Traded Volume: %{{y:,.1f}}(\'000 b/d)<extra></extra>',
                text=[f'{v:,.1f}' if v >= 10 else '' for v in volumes],  # Show value if >= 10
                textposition='inside',
                textangle=-90,  # Rotate text vertically
                textfont=dict(size=10, color='#000000'),
                selected=dict(marker=dict(opacity=1.0)),  # Selected bars remain fully opaque
                unselected=dict(marker=dict(opacity=0.3))  # Unselected bars are dimmed
            ))
            crude_volumes_dict[crude] = volumes
    
    # Update layout
    fig.update_layout(
        title={
            'text': f"{selected_country} Crude Imports by Country - {actual_year}",
            'x': 0.5,
            'xanchor': 'center',
            'font': {
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 16,
                'color': '#333333'
            },
            'pad': {'t': 10, 'b': 20}
        },
        xaxis=dict(
            title={
                'text': "Country",
                'font': {
                    'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                    'size': 13,
                    'color': '#333333'
                }
            },
            tickfont={
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 10,
                'color': '#666666'
            },
            tickangle=90,  # Vertical labels (straight up)
            showgrid=False,  # Remove vertical grid lines to avoid square boxes
            showline=True,  # Show the axis line
            linecolor='#d3d3d3',
            linewidth=1,
            mirror=True  # Show axis line on all sides
        ),
        yaxis=dict(
            title={
                'text': "Volume ('000 b/d)",
                'font': {
                    'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                    'size': 13,
                    'color': '#333333'
                }
            },
            tickfont={
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 11,
                'color': '#666666'
            },
            range=[0, max(yaxis_max, max_value)],  # Dynamic range covering all data
            tickmode='linear',
            tick0=0,
            dtick=tick_interval,  # Dynamic tick interval - will show ticks at 0, interval, 2*interval, etc.
            tickvals=[0, tick_interval, tick_interval * 2, tick_interval * 3],  # Explicitly set 4 tick values
            gridcolor='#e0e0e0',
            gridwidth=1,
            showgrid=False,  # Remove horizontal grid lines
            showline=True,  # Show the axis line
            linecolor='#d3d3d3',
            linewidth=1,
            mirror=True  # Show axis line on all sides
        ),
        barmode='stack',
        height=520,
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=60, r=200, t=60, b=100),
        clickmode='select',  # Only selection, no event callbacks
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02,
            font={
                'family': '"Benton Sans", "Arial", "Helvetica", sans-serif',
                'size': 10,
                'color': '#333333'
            },
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#d3d3d3',
            borderwidth=1,
            traceorder='normal' # Ensure legend order matches trace order
        ),
        hovermode='closest',  # Show only the hovered segment
        hoverlabel=dict(
            bgcolor='white',
            bordercolor='#999999',
            font=dict(
                size=12,
                family='"Benton Sans", "Arial", "Helvetica", sans-serif',
                color='#000000'
            ),
            align='left'
        )
    )
    
    return fig


def create_imports_table(selected_country='Japan', expansion_state=None, time_visibility=None):
    """Create data table with stacked header text per column (Year/Quarter/Month/Day) but still one column per year."""
    df = load_table_data(selected_country)
    
    if df.empty:
        return [], [], []
    
    time_visibility = time_visibility or {'Year': True, 'Quarter': False, 'Month': False, 'Day': False}
    show_year = time_visibility.get('Year', True)
    show_quarter = time_visibility.get('Quarter', False)
    show_month = time_visibility.get('Month', False)
    show_day = time_visibility.get('Day', False)
    
    # Orderings
    years = sorted(df['Year of Year'].unique(), reverse=True)
    quarter_order = ['Q1', 'Q2', 'Q3', 'Q4']
    month_order = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]
    
    # Build IDs
    def year_id(y): return f"Y|{y}"
    def quarter_id(y): return f"Q|{y}"
    def month_id(y): return f"M|{y}"
    def day_id(y): return f"D|{y}"
    
    columns = [
        {'name': 'Exporting Region', 'id': 'Exporting Region'},
        {'name': 'Exporter', 'id': 'Exporter'},
        {'name': 'Company', 'id': 'Company'},
        {'name': 'Crude', 'id': 'Crude'}
    ]
    
    # Determine default quarter/month per year (first available in order)
    year_defaults = {}
    for year in years:
        df_year = df[df['Year of Year'] == year]
        q_default = ''
        m_default = ''
        d_default = ''
        for q in quarter_order:
            if q in df_year['Quarter of Year'].unique():
                q_default = q
                df_q = df_year[df_year['Quarter of Year'] == q]
                for m in month_order:
                    if m in df_q['Month of Year'].unique():
                        m_default = m
                        df_m = df_q[df_q['Month of Year'] == m]
                        # pick first available day
                        if 'Day of Year' in df_m.columns and not df_m['Day of Year'].dropna().empty:
                            d_default = str(int(df_m['Day of Year'].dropna().iloc[0]))
                        break
                if m_default:
                    break
        year_defaults[year] = (q_default, m_default, d_default)

    dynamic_columns = []
    for year in years:
        q_def, m_def, d_def = year_defaults.get(year, ('', '', ''))
        if show_day:
            header_label = " ".join(part for part in [str(year), q_def, m_def, d_def] if part)
            col_id = day_id(year)
        elif show_month:
            header_label = " ".join(part for part in [str(year), q_def, m_def] if part)
            col_id = month_id(year)
        elif show_quarter:
            header_label = " ".join(part for part in [str(year), q_def] if part)
            col_id = quarter_id(year)
        else:
            header_label = str(year)
            col_id = year_id(year)
        dynamic_columns.append({
            'name': header_label,
            'id': col_id,
            'type': 'numeric',
            'format': {'specifier': ',.1f'},
            'presentation': 'input'
        })
    columns.extend(dynamic_columns)
    
    # Pivot data into wide format keyed by region/exporter/company/crude
    records = {}
    for _, row in df.iterrows():
        key = (
            row.get('Exporting Region', ''),
            row.get('Exporter', ''),
            row.get('Company', ''),
            row.get('Crude', '')
        )
        y = row['Year of Year']
        q = row['Quarter of Year']
        m = row['Month of Year']
        # Normalize day to string
        day_val_raw = row.get('Day of Year', '')
        day_key = ''
        if pd.notna(day_val_raw) and day_val_raw != '':
            try:
                day_key = str(int(float(day_val_raw)))
            except Exception:
                day_key = str(day_val_raw)
        
        rec = records.setdefault(key, {
            'Exporting Region': str(key[0]) if key[0] is not None else '',
            'Exporter': str(key[1]) if key[1] is not None else '',
            'Company': str(key[2]) if key[2] is not None else '',
            'Crude': str(key[3]) if key[3] is not None else '',
            '_year': {},
            '_quarter': {},
            '_month': {},
            '_day': {}
        })
        try:
            val = float(row['DataValue'])
        except Exception:
            val = 0
        
        rec['_year'][y] = rec['_year'].get(y, 0) + val
        rec['_quarter'][(y, q)] = rec['_quarter'].get((y, q), 0) + val
        rec['_month'][(y, q, m)] = rec['_month'].get((y, q, m), 0) + val
        rec['_day'][(y, q, m, day_key)] = rec['_day'].get((y, q, m, day_key), 0) + val
    
    # Convert to list and sort for grouping, selecting values per year (with defaults)
    table_data = []
    for rec in records.values():
        out = {
            'Exporting Region': rec['Exporting Region'],
            'Exporter': rec['Exporter'],
            'Company': rec['Company'],
            'Crude': rec['Crude']
        }
        for year in years:
            q_def, m_def, d_def = year_defaults.get(year, ('', '', ''))
            y_val = rec['_year'].get(year, '')
            q_val = rec['_quarter'].get((year, q_def), '') if q_def else ''
            m_val = rec['_month'].get((year, q_def, m_def), '') if (q_def and m_def) else ''
            d_val = rec['_day'].get((year, q_def, m_def, d_def), '') if (q_def and m_def and d_def) else ''
            if show_day:
                out[day_id(year)] = d_val
            elif show_month:
                out[month_id(year)] = m_val
            elif show_quarter:
                out[quarter_id(year)] = q_val
            else:
                out[year_id(year)] = y_val
        table_data.append(out)
    
    table_data = sorted(table_data, key=lambda r: (
        r.get('Exporting Region', ''), r.get('Exporter', ''),
        r.get('Company', ''), r.get('Crude', '')
    ))
    
    # Hierarchical grouping: blank repeated text fields
    prev_region = prev_exporter = prev_company = None
    for record in table_data:
        current_region = record.get('Exporting Region', '').strip()
        current_exporter = record.get('Exporter', '').strip()
        current_company = record.get('Company', '').strip()
        
        if current_region == prev_region:
            record['Exporting Region'] = ''
        else:
            prev_region = current_region
            prev_exporter = None
            prev_company = None
        
        if current_exporter == prev_exporter and current_region == prev_region:
            record['Exporter'] = ''
        else:
            if current_exporter:
                prev_exporter = current_exporter
            prev_company = None
        
        if current_company == prev_company and current_exporter == prev_exporter:
            record['Company'] = ''
        else:
            if current_company:
                prev_company = current_company
    
    # Hidden columns: only keep the active level
    hidden = []
    if show_day:
        active_prefix = 'D|'
    elif show_month:
        active_prefix = 'M|'
    elif show_quarter:
        active_prefix = 'Q|'
    else:
        active_prefix = 'Y|'
    for col in dynamic_columns:
        if not col['id'].startswith(active_prefix):
            hidden.append(col['id'])
    return table_data, columns, hidden


def register_callbacks(dash_app, server):
    """Register all callbacks for Imports - Country Detail"""
    
    @callback(
        Output('imports-by-region-chart', 'figure'),
        [Input('importing-country-select', 'value'),
         Input('current-submenu', 'data')],
        prevent_initial_call=False
    )
    def update_imports_by_region(selected_country, submenu):
        """Update imports by region chart"""
        if submenu != 'imports-detail':
            return go.Figure()
        fig = create_imports_by_region_chart(selected_country)
        # Ensure the figure is valid and has data
        if fig and len(fig.data) > 0:
            return fig
        return go.Figure()
    
    @callback(
        Output('imports-by-country-chart', 'figure'),
        [Input('importing-country-select', 'value'),
         Input('current-submenu', 'data'),
         State('selected-year-store', 'data')]
    )
    def update_imports_by_country(selected_country, submenu, current_year):
        """Update imports by country chart based on country selection"""
        if submenu != 'imports-detail':
            return go.Figure()
        
        # Use current year (default 2023) - chart 1 clicks no longer affect chart 2
        selected_year = current_year if current_year else 2023
        
        fig = create_imports_by_country_chart(selected_year, selected_country)
        return fig
    
    @callback(
        [Output('imports-detail-table', 'data'),
         Output('imports-detail-table', 'columns'),
         Output('imports-detail-table', 'hidden_columns'),
         Output('imports-table-title', 'children')],
        [Input('importing-country-select', 'value'),
         Input('current-submenu', 'data'),
         Input('imports-expand-store', 'data'),
         Input('imports-time-visibility', 'data')]
    )
    def update_imports_table(selected_country, submenu, expand_state, time_visibility):
        """Update imports detail table"""
        if submenu != 'imports-detail':
            # Return empty but valid structures
            empty_columns = [
                {'name': 'Exporting Region', 'id': 'Exporting Region'},
                {'name': 'Exporter', 'id': 'Exporter'},
                {'name': 'Company', 'id': 'Company'},
                {'name': 'Crude', 'id': 'Crude'}
            ]
            return [], empty_columns, [], ""
        try:
            data, columns, hidden = create_imports_table(selected_country, expand_state, time_visibility)
            # Ensure data and columns are lists
            if not isinstance(data, list):
                data = []
            if not isinstance(columns, list):
                # Return default columns structure if columns is invalid
                columns = [
                    {'name': 'Exporting Region', 'id': 'Exporting Region'},
                    {'name': 'Exporter', 'id': 'Exporter'},
                    {'name': 'Company', 'id': 'Company'},
                    {'name': 'Crude', 'id': 'Crude'}
                ]
            if not isinstance(hidden, list):
                hidden = []
            
            # Deep clean: Ensure all data items are dictionaries with only native Python types
            cleaned_data = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                cleaned_item = {}
                for key, value in item.items():
                    # Ensure key is a string
                    key_str = str(key) if key is not None else ''
                    # Ensure value is a native Python type
                    if value is None:
                        cleaned_item[key_str] = ''
                    elif isinstance(value, (int, float, str, bool)):
                        # Check for NaN or inf in floats
                        if isinstance(value, float) and (value != value or abs(value) == float('inf')):
                            cleaned_item[key_str] = ''
                        else:
                            cleaned_item[key_str] = value
                    elif hasattr(value, 'item'):  # numpy scalar
                        try:
                            cleaned_item[key_str] = value.item()
                        except:
                            cleaned_item[key_str] = str(value)
                    else:
                        # Convert everything else to string
                        try:
                            cleaned_item[key_str] = str(value) if value is not None else ''
                        except:
                            cleaned_item[key_str] = ''
                cleaned_data.append(cleaned_item)
            
            # Ensure all column items are dictionaries with required keys
            cleaned_columns = []
            for col in columns:
                if not isinstance(col, dict):
                    continue
                if 'name' in col and 'id' in col:
                    name_val = col['name']
                    if isinstance(name_val, (list, tuple)):
                        cleaned_name = list(name_val)
                    else:
                        cleaned_name = name_val if name_val is not None else ''
                    cleaned_col = {
                        'name': cleaned_name,
                        'id': col['id'] if col['id'] is not None else ''
                    }
                    # Copy other properties if they exist
                    for key, value in col.items():
                        if key not in ['name', 'id']:
                            cleaned_col[key] = value
                    cleaned_columns.append(cleaned_col)
            
            if not cleaned_columns:
                # Fallback to default columns
                cleaned_columns = [
                    {'name': 'Exporting Region', 'id': 'Exporting Region'},
                    {'name': 'Exporter', 'id': 'Exporter'},
                    {'name': 'Company', 'id': 'Company'},
                    {'name': 'Crude', 'id': 'Crude'}
                ]
            
            title = f"{selected_country} Crude Oil Imports by Region and Country"
            return cleaned_data, cleaned_columns, hidden, title
        except Exception as e:
            print(f"Error updating imports table: {e}")
            import traceback
            traceback.print_exc()
            # Return empty but valid structures on error
            empty_columns = [
                {'name': 'Exporting Region', 'id': 'Exporting Region'},
                {'name': 'Exporter', 'id': 'Exporter'},
                {'name': 'Company', 'id': 'Company'},
                {'name': 'Crude', 'id': 'Crude'}
            ]
            return [], empty_columns, [], ""

    @callback(
        Output('imports-expand-store', 'data'),
        Input('imports-detail-table', 'active_cell'),
        State('imports-expand-store', 'data'),
        prevent_initial_call=True
    )
    def toggle_header_expansion(active_cell, state):
        """Toggle expansion for year/quarter headers via header clicks."""
        state = state or {'years': [], 'quarters': []}
        years = set(state.get('years', []))
        quarters = set(tuple(q) for q in state.get('quarters', []))
        
        if not active_cell or active_cell.get('row') != -1:
            return state
        
        col_id = active_cell.get('column_id') or ''
        parts = col_id.split('|')
        if not parts:
            return state
        
        if parts[0] == 'Y' and len(parts) >= 2:
            year = parts[1]
            if year in years:
                years.remove(year)
                quarters = {q for q in quarters if q[0] != year}
            else:
                years.add(year)
        elif parts[0] == 'Q' and len(parts) >= 3:
            key = (parts[1], parts[2])
            if key in quarters:
                quarters.remove(key)
            else:
                quarters.add(key)
        
        return {
            'years': sorted(years, reverse=True),
            'quarters': sorted(list(quarters), reverse=True)
        }
    
    # Button icons and styles reflecting time visibility state
    @callback(
        [Output('imports-toggle-year-btn', 'children'),
         Output('imports-toggle-year-btn', 'style'),
         Output('imports-toggle-quarter-btn', 'children'),
         Output('imports-toggle-quarter-btn', 'style'),
         Output('imports-toggle-month-btn', 'children'),
         Output('imports-toggle-month-btn', 'style'),
         Output('imports-toggle-day-btn', 'children'),
         Output('imports-toggle-day-btn', 'style')],
        Input('imports-time-visibility', 'data'),
        prevent_initial_call=False
    )
    def update_imports_toggle_icons(vis):
        vis = vis or {'Year': True, 'Quarter': False, 'Month': False, 'Day': False}
        def base_style(active):
            return {
                'width': '20px',
                'height': '20px',
                'padding': '0',
                'border': '1px solid #007bff' if active else '1px solid #dee2e6',
                'backgroundColor': '#e7f3ff' if active else '#f8f9fa',
                'color': '#007bff' if active else '#2c3e50',
                'borderRadius': '3px',
                'cursor': 'pointer',
                'fontSize': '14px',
                'fontWeight': 'bold',
                'lineHeight': '1',
                'display': 'flex',
                'alignItems': 'center',
                'justifyContent': 'center',
                'marginLeft': '8px',
                'flexShrink': '0'
            }
        year_active = vis.get('Year', True)
        quarter_active = vis.get('Quarter', False)
        month_active = vis.get('Month', False)
        day_active = vis.get('Day', False)
        return (
            '−' if year_active else '+', base_style(year_active),
            '−' if quarter_active else '+', base_style(quarter_active),
            '−' if month_active else '+', base_style(month_active),
            '−' if day_active else '+', base_style(day_active)
        )
    
    # Toggle button callbacks to update visibility and expansion state
    @callback(
        [Output('imports-time-visibility', 'data', allow_duplicate=True),
         Output('imports-expand-store', 'data', allow_duplicate=True)],
        Input('imports-toggle-year-btn', 'n_clicks'),
        State('imports-time-visibility', 'data'),
        State('imports-expand-store', 'data'),
        prevent_initial_call=True
    )
    def toggle_year_vis(n_clicks, vis, expand_state):
        vis = (vis or {'Year': True, 'Quarter': False, 'Month': False, 'Day': False}).copy()
        expand_state = expand_state or {'years': [], 'quarters': []}
        vis['Year'] = not vis.get('Year', True)
        if not vis['Year']:
            expand_state = {'years': [], 'quarters': []}
        return vis, expand_state
    
    @callback(
        [Output('imports-time-visibility', 'data', allow_duplicate=True),
         Output('imports-expand-store', 'data', allow_duplicate=True)],
        Input('imports-toggle-quarter-btn', 'n_clicks'),
        State('imports-time-visibility', 'data'),
        State('imports-expand-store', 'data'),
        prevent_initial_call=True
    )
    def toggle_quarter_vis(n_clicks, vis, expand_state):
        vis = (vis or {'Year': True, 'Quarter': False, 'Month': False, 'Day': False}).copy()
        expand_state = expand_state or {'years': [], 'quarters': []}
        vis['Quarter'] = not vis.get('Quarter', False)
        return vis, expand_state
    
    @callback(
        [Output('imports-time-visibility', 'data', allow_duplicate=True),
         Output('imports-expand-store', 'data', allow_duplicate=True)],
        Input('imports-toggle-month-btn', 'n_clicks'),
        State('imports-time-visibility', 'data'),
        State('imports-expand-store', 'data'),
        prevent_initial_call=True
    )
    def toggle_month_vis(n_clicks, vis, expand_state):
        vis = (vis or {'Year': True, 'Quarter': False, 'Month': False, 'Day': False}).copy()
        expand_state = expand_state or {'years': [], 'quarters': []}
        vis['Month'] = not vis.get('Month', False)
        return vis, expand_state
    
    @callback(
        Output('imports-time-visibility', 'data', allow_duplicate=True),
        Input('imports-toggle-day-btn', 'n_clicks'),
        State('imports-time-visibility', 'data'),
        prevent_initial_call=True
    )
    def toggle_day_vis(n_clicks, vis):
        vis = (vis or {'Year': True, 'Quarter': False, 'Month': False, 'Day': False}).copy()
        vis['Day'] = not vis.get('Day', False)
        return vis
