"""
Projects by Company View
Upstream projects grouped by company - matches Tableau dashboard design
"""
from dash import dcc, html, Input, Output, State, callback, ALL, callback_context, dash_table
import dash
import json
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os
from sqlalchemy import func

# Define data path
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'projects_company')
CSV_FILE = os.path.join(DATA_DIR, 'Projects by Company_Chart_data.csv')
MAP_CSV_FILE = os.path.join(DATA_DIR, 'Map_by Company_data.csv')

# Load CSV data
def load_data():
    """Load data from CSV file"""
    try:
        df = pd.read_csv(CSV_FILE, encoding="utf-8", sep=",")
        df.columns = df.columns.str.strip()
        # Convert value_company to numeric
        df['value_company'] = pd.to_numeric(df['value_company'], errors='coerce').fillna(0)
        # Keep all rows (including zeros) so all countries are available for the chart
        # Countries with zero values will just show as 0 in the chart
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

# Load map CSV data
def load_map_data():
    """Load map data from CSV file"""
    try:
        df = pd.read_csv(MAP_CSV_FILE, encoding="utf-8", sep=",")
        df.columns = df.columns.str.strip()
        # Convert value_company to numeric, keeping NaN for countries with no data
        df['value_company'] = pd.to_numeric(df['value_company'], errors='coerce')
        return df
    except Exception as e:
        print(f"Error loading map data: {e}")
        return pd.DataFrame()

# Load data once at module level
DATA_DF = load_data()
MAP_DF = load_map_data()

# Get unique values for filters
def get_unique_years():
    """Get unique years from data"""
    if DATA_DF.empty:
        return []
    return sorted(DATA_DF['Year of Period'].unique().tolist())

def get_unique_countries():
    """Get unique countries from data"""
    if DATA_DF.empty:
        return []
    countries = sorted([c for c in DATA_DF['Country'].unique().tolist() if pd.notna(c) and str(c).strip()])
    return countries

def get_unique_quarters():
    """Get unique quarters"""
    return ['Q1', 'Q2', 'Q3', 'Q4']

# Color palette for countries (matching Tableau dashboard exactly)
COUNTRY_COLORS = {
    'Algeria': '#87CEEB',  # light blue
    'Angola': '#FF8C42',  # orange (matching Tableau dashboard)
    'Argentina': '#FF8C42',  # orange
    'Australia': '#FFB366',  # light orange/peach
    'Azerbaijan': '#90EE90',  # light green
    'Brazil': '#D2B48C',  # light brown/tan
    'Brunei': '#FFD700',  # yellow
    'Cameroon': '#DC143C',  # red
    'Canada': '#20B2AA',  # teal/light blue-green
    'China': '#696969',  # dark grey
    'Cote d\'Ivoire': '#FFC0CB',  # pink
    'Denmark': '#C71585',  # dark pink
    'Egypt': '#DDA0DD',  # muted purple (plum)
    'Gabon': '#FFE4E1',  # very light pink/peach
    'Ghana': '#8B4513',  # dark reddish-brown (saddle brown)
    'Guyana': '#20B2AA',  # distinct teal/turquoise (matching Tableau)
    'India': '#87CEEB',  # light sky blue
    'Indonesia': '#1E3A8A',  # dark, rich blue
    'Iran': '#F0F8FF',  # very pale, almost white-blue (alice blue)
    'Iraq': '#CD853F',  # medium brown (peru)
    'Kazakhstan': '#00CED1',  # dark turquoise/teal (matching Tableau - shown as green in bars)
    'Kuwait': '#DAA520',  # mustard yellow/gold
    'Libya': '#48D1CC',  # light, slightly desaturated teal/green (medium turquoise)
    'Malaysia': '#228B22',  # dark forest green
    'Nigeria': '#4169E1',  # royal blue
    'Qatar': '#9370DB',  # medium purple
    'United States': '#1E90FF',  # dodger blue
    'Vietnam': '#20B2AA',  # light sea green
}

def get_country_color(country):
    """Get color for a country, assign default if not in palette"""
    if country in COUNTRY_COLORS:
        return COUNTRY_COLORS[country]
    # Generate a color based on hash for countries not in palette
    import hashlib
    hash_obj = hashlib.md5(str(country).encode())
    hash_int = int(hash_obj.hexdigest(), 16)
    # Generate a color from hash
    r = (hash_int & 0xFF0000) >> 16
    g = (hash_int & 0xFF00) >> 8
    b = hash_int & 0xFF
    return f'rgb({r}, {g}, {b})'

def create_stacked_bar_chart(df, selected_company="Exxon Mobil", selected_countries=None):
    """Create stacked bar chart showing quarterly capacity by country"""
    if selected_countries is None:
        selected_countries = []
    
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            height=500,
            plot_bgcolor='white',
            paper_bgcolor='white',
            title={
                'text': f"Oil Projects Capacity Start Up by {selected_company} ('000 b/d)*",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16, 'family': 'Arial, sans-serif', 'color': '#FF8C42'}
            }
        )
        return fig
    
    # Always use DATA_DF to ensure we have ALL countries from CSV (including those with zeros like Algeria)
    # This ensures all countries are available for the chart
    original_df = DATA_DF.copy() if not DATA_DF.empty else df.copy()
    
    # Create period labels on the full dataset first
    if 'Period' not in original_df.columns:
        original_df['Period'] = original_df['Year of Period'].astype(str) + ' ' + original_df['Quarter of Period']
    
    # Create a sort key for proper chronological ordering
    quarter_order = {'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4}
    if 'SortKey' not in original_df.columns:
        original_df['SortKey'] = original_df['Year of Period'] * 10 + original_df['Quarter of Period'].map(quarter_order)
        original_df = original_df.sort_values(['SortKey'])
    
    if selected_countries:
        # If countries are selected, show ONLY those selected countries (even if they have zero values)
        # This matches Tableau behavior - clicking a country filters to show only that country
        all_countries_in_data = [c for c in selected_countries if pd.notna(c) and str(c).strip()]
    else:
        # If no countries selected, show ALL countries from the CSV data (including those with zeros)
        # This ensures all countries from the CSV are displayed in the chart
        # Countries with zero values will still appear in tooltips and chart structure
        all_countries_in_data = [c for c in original_df['Country'].unique().tolist() if pd.notna(c) and str(c).strip()]
    
    # Filter by selected countries if any are selected (after getting country list)
    # Always use original_df (full DATA_DF) to ensure we have data for all countries even if they have zeros
    if selected_countries:
        # Filter to selected countries only
        df = original_df[original_df['Country'].isin(selected_countries)].copy()
    else:
        # When showing all countries, use the full original data
        df = original_df.copy()
    
    # Generate all possible periods from min year to max year (to ensure all quarters are shown)
    # Use the full data range (2025-2029) to show all quarters consistently
    all_periods = []
    for year in range(2025, 2030):
        for quarter in ['Q1', 'Q2', 'Q3', 'Q4']:
            all_periods.append(f"{year} {quarter}")
    periods = all_periods
    
    # Define stacking order to match Tableau visualization
    # In stacked bar charts, the order matters - countries are stacked from bottom to top
    # Based on the image, the typical order is: Kazakhstan (bottom), then others with data, then zeros on top
    # For proper stacking, we want countries with data first, then countries with zeros
    stacking_order = [
        'Kazakhstan', 'Guyana', 'Brazil', 'Azerbaijan', 'Indonesia', 'Angola', 
        'Qatar', 'Nigeria', 'Canada', 'China', 'Malaysia', 'Iran', 'Iraq',
        'Mexico', 'Libya', 'Niger', 'Kuwait', 'Algeria', 'Argentina', 'Australia',
        'Brunei', 'Cameroon', 'Cote d\'Ivoire', 'Denmark', 'Egypt', 'Gabon', 
        'Ghana', 'India', 'United States', 'United Kingdom', 'United Arab Emirates',
        'Uganda', 'Turkmenistan', 'Turkey', 'Trinidad and Tobago', 'Thailand',
        'Suriname', 'Senegal', 'Saudi Arabia', 'Russia', 'Oman', 'Norway',
        'Neutral Zone', 'Namibia', 'Vietnam', 'Ecuador'
    ]
    
    # Separate countries with data from countries with only zeros
    countries_with_data = []
    countries_with_zeros_only = []
    
    for country in all_countries_in_data:
        country_data = df[df['Country'] == country]
        if not country_data.empty and country_data['value_company'].sum() > 0:
            countries_with_data.append(country)
        else:
            countries_with_zeros_only.append(country)
    
    # Order countries with data according to stacking order
    ordered_with_data = [c for c in stacking_order if c in countries_with_data]
    remaining_with_data = [c for c in sorted(countries_with_data) if c not in stacking_order]
    
    # Order countries with zeros according to stacking order
    ordered_with_zeros = [c for c in stacking_order if c in countries_with_zeros_only]
    remaining_with_zeros = [c for c in sorted(countries_with_zeros_only) if c not in stacking_order]
    
    # Stack: countries with data first (bottom), then countries with zeros (top, but invisible)
    countries = ordered_with_data + remaining_with_data + ordered_with_zeros + remaining_with_zeros
    
    # Format periods for hover (Q1 2025 instead of 2025 Q1) - create once before loop
    hover_periods = [f"{p.split(' ')[1]} {p.split(' ')[0]}" for p in periods]
    
    # Create stacked bar chart
    fig = go.Figure()
    
    # Add a trace for each country
    for country in countries:
        # Always use the filtered df (which has Period column already created)
        # If country is selected, df is filtered to that country
        # If no countries selected, df has all countries
        country_data = df[df['Country'] == country]
        
        values = []
        for period in periods:
            period_data = country_data[country_data['Period'] == period]
            if not period_data.empty:
                values.append(period_data['value_company'].sum())
            else:
                # If no data for this period, set to 0
                values.append(0)
        
        # Always create a trace for all countries, even if all values are 0
        # This ensures the chart structure is maintained and tooltips work for countries with zeros
        # In stacked bar charts, traces with zeros are still part of the stack and show in tooltips
        # Countries with zeros will be hoverable even though they don't show visually
        fig.add_trace(go.Bar(
            name=country,
            x=periods,
            y=values,
            marker_color=get_country_color(country),
            customdata=hover_periods,
            hovertemplate='<b>Country: ' + country + '</b><br>Period: %{customdata}<br>Production Additions (\'000 b/d): %{y:,.1f}<extra></extra>',
            showlegend=False,  # Hide legend - using sidebar legend instead
            marker_line_width=0,  # No border on bars
            # Make zero-value bars still hoverable
            opacity=1.0 if any(v > 0 for v in values) else 0.01
        ))
    
    # Y-axis should be exactly 0-70 to match images exactly
    y_max = 70
    
    # Update layout to match exact image design
    fig.update_layout(
        barmode='stack',
        height=500,
        plot_bgcolor='white',
        paper_bgcolor='white',
        title={
            'text': f"Oil Projects Capacity Start Up by {selected_company} ('000 b/d)*",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'family': 'Arial, sans-serif', 'color': '#FF8C42'},
            'y': 0.98
        },
        xaxis=dict(
            title='',
            tickangle=0,
            showgrid=True,
            gridcolor='#e0e0e0',
            tickfont=dict(size=11, color='#2c3e50'),
            tickmode='array',
            tickvals=periods,
            ticktext=[p.split(' ')[1] for p in periods],  # Show only quarters (Q1, Q2, etc.)
            categoryorder='array',
            categoryarray=periods
        ),
        yaxis=dict(
            title="'000 b/d",
            showgrid=True,
            gridcolor='#e0e0e0',
            tickfont=dict(size=11, color='#2c3e50'),
            range=[0, y_max],
            dtick=10,
            titlefont=dict(size=12, color='#2c3e50')
        ),
        showlegend=False,  # Hide legend in chart - using sidebar legend instead
        margin=dict(l=60, r=60, t=60, b=100),  # Reduced right margin since legend is in sidebar
        hovermode='closest'
    )
    
    # Add year annotations above quarter groups
    if not df.empty:
        min_year = int(df['Year of Period'].min())
        max_year = int(df['Year of Period'].max())
        for year in range(min_year, max_year + 1):
            # Find the middle position of the 4 quarters for this year
            try:
                q1_idx = periods.index(f"{year} Q1")
                q2_idx = periods.index(f"{year} Q2")
                # Calculate x position (center between Q1 and Q2, using category index)
                x_pos = (q1_idx + q2_idx) / 2
                fig.add_annotation(
                    x=x_pos,
                    y=1.05,
                    xref='x',
                    yref='paper',
                    text=str(year),
                    showarrow=False,
                    font=dict(size=12, color='#2c3e50'),
                    xanchor='center'
                )
            except (ValueError, IndexError):
                pass
    
    return fig

def create_world_map(df, selected_year=2025, selected_company="Exxon Mobil"):
    """Create world map showing geographical distribution for selected year - matching Tableau design exactly"""
    # Use map-specific data if available, otherwise fall back to main data
    map_df = MAP_DF.copy() if not MAP_DF.empty else df.copy()
    
    if map_df.empty:
        fig = go.Figure()
        fig.update_layout(
            geo=dict(
                showframe=False,
                showcoastlines=True,
                projection_type='equirectangular',
                bgcolor='rgba(0,0,0,0)',
                coastlinecolor='#d0d0d0',
                landcolor='#e8e8e8',
                showocean=True,
                oceancolor='white',
                showcountries=True,
                countrycolor='#bdbdbd'
            ),
            height=500,
            paper_bgcolor='white',
            plot_bgcolor='white',
            title={
                'text': f"Oil Projects Capacity Start Up by {selected_company} ('000 b/d)*- {selected_year}",
                'x': 0.02,
                'xanchor': 'left',
                'font': {'size': 16, 'family': 'Arial, sans-serif', 'color': '#2c3e50'}
            }
        )
        return fig
    
    # Filter by year
    year_df = map_df[map_df['Year of Period'] == selected_year].copy()
    
    # Create a blue/teal color scale matching Tableau design exactly
    # Colors from light blue/teal to dark blue/teal (matching the image description)
    colorscale = [
        [0.0, '#B3E5FC'],  # Very light blue/teal (for low values ~0.7)
        [0.15, '#81D4FA'],  # Light blue/teal
        [0.3, '#4FC3F7'],  # Medium light blue/teal
        [0.5, '#29B6F6'],  # Medium blue/teal
        [0.7, '#03A9F4'],  # Medium dark blue/teal
        [0.85, '#0288D1'],  # Dark blue/teal
        [1.0, '#01579B']   # Very dark blue (for high values ~135.0)
    ]
    
    # Get min and max values for color scale (excluding NaN)
    # Match Tableau design: range from 0.7 to 135.0
    valid_values = year_df['value_company'].dropna()
    if valid_values.empty:
        zmin, zmax = 0.7, 135.0
    else:
        # Use actual min/max but ensure minimum is at least 0.7 and max is at least 135
        zmin = max(0.7, valid_values.min()) if valid_values.min() > 0 else 0.7
        zmax = max(135.0, valid_values.max()) if valid_values.max() > 0 else 135.0
    
    # Aggregate by country (sum values if multiple entries per country)
    country_totals = year_df.groupby('Country')['value_company'].sum().reset_index()
    country_totals.columns = ['Country', 'Value']
    
    # Treat missing values as 0.7 (minimum of the legend range) so ALL countries
    # (including United States) get the lightest color instead of being invisible.
    country_totals['Value'] = country_totals['Value'].fillna(0.7)
    
    # Create choropleth map including all countries from the CSV
    fig = go.Figure(data=go.Choropleth(
        locations=country_totals['Country'],
        z=country_totals['Value'],
        locationmode='country names',
        colorscale=colorscale,
        zmin=zmin,
        zmax=zmax,
        marker_line_color='#ffffff',
        marker_line_width=0.5,
        hovertemplate='<b>%{location}</b><br>Production Addition: %{z:,.1f} \'000 b/d<extra></extra>',
        showscale=True,
        colorbar=dict(
            title="Production Additions\n('000 b/d)",
            titleside='top',
            titlefont=dict(size=11, family='Arial, sans-serif', color='#2c3e50'),
            tickfont=dict(size=10, family='Arial, sans-serif', color='#2c3e50'),
            thickness=12,
            len=0.45,
            x=1.02,
            xanchor='left',
            y=0.5,
            outlinecolor='#bdbdbd',
            outlinewidth=0.5
        )
    ))
    
    # Update geo settings to match Tableau design
    fig.update_geos(
        showframe=False,
        showcoastlines=True,
        projection_type='equirectangular',
        bgcolor='rgba(0,0,0,0)',
        coastlinecolor='#d0d0d0',
        landcolor='#e8e8e8',  # Grey for countries with no data
        showocean=True,
        oceancolor='white',
        showcountries=True,
        countrycolor='#bdbdbd',
        showlakes=False,
        showrivers=False,
        resolution=50
    )
    
    fig.update_layout(
        height=500,
        paper_bgcolor='white',
        plot_bgcolor='white',
        margin=dict(l=0, r=0, t=60, b=30),
        title={
            'text': f"Oil Projects Capacity Start Up by {selected_company} ('000 b/d)*- {selected_year}",
            'x': 0.02,
            'xanchor': 'left',
            'y': 0.98,
            'yanchor': 'top',
            'font': {'size': 16, 'family': 'Arial, sans-serif', 'color': '#2c3e50'}
        },
        hovermode='closest',
        hoverlabel=dict(
            bgcolor='white',
            bordercolor='#999999',
            font_size=12,
            font_family='Arial, sans-serif',
            font_color='#000000'
        )
    )
    
    # Add copyright annotation at bottom left (matching Tableau)
    fig.add_annotation(
        text="© 2025 Mapbox © OpenStreetMap",
        xref="paper",
        yref="paper",
        x=0.01,
        y=0.01,
        showarrow=False,
        font=dict(size=9, color='#666666'),
        xanchor='left',
        yanchor='bottom'
    )
    
    return fig

def create_layout():
    """Create layout for Projects by Company with filters, year controls, legend, chart, map and table."""
    # Load table data
    table_csv = os.path.join(DATA_DIR, 'Projects by Company_Table_data.csv')
    try:
        df_table = pd.read_csv(table_csv, encoding='utf-8', sep=',')
        # Strip whitespace from column names
        df_table.columns = [c.strip() for c in df_table.columns]
    except Exception as e:
        print(f"Error loading table CSV: {e}")
        df_table = pd.DataFrame()
    
    # Prepare DataTable columns and data (pivot long Measure Names/Values to wide format like Tableau)
    if df_table.empty:
        columns = [{"name": "No data", "id": "no_data"}]
        data = [{"no_data": "No data available"}]
    else:
        # Identify base columns (all except Measure Names / Measure Values)
        measure_name_col = 'Measure Names'
        measure_value_col = 'Measure Values'
        base_cols = [c for c in df_table.columns if c not in [measure_name_col, measure_value_col]]
        
        # Pivot so that each Measure Name becomes a separate column (e.g., 2024_Q1, Partner Share %, etc.)
        try:
            pivot_df = df_table.pivot_table(
                index=base_cols,
                columns=measure_name_col,
                values=measure_value_col,
                aggfunc='first'
            ).reset_index()
            
            # Flatten columns after pivot (base columns stay the same, others are the Measure Names)
            pivot_df.columns = [
                col if isinstance(col, str) else str(col)
                for col in pivot_df.columns
            ]
            
            # Convert numeric measure columns where possible
            measure_cols = [c for c in pivot_df.columns if c not in base_cols]
            for c in measure_cols:
                pivot_df[c] = pd.to_numeric(pivot_df[c], errors='coerce')
            
            table_df = pivot_df
        except Exception as e:
            # Fallback to raw table if pivot fails
            print(f"Error pivoting Projects by Company table data: {e}")
            table_df = df_table.copy()
        
        columns = [{"name": col, "id": col} for col in table_df.columns]
        data = table_df.fillna("").to_dict('records')
    
    # Years for filters / slider
    years = get_unique_years()
    if years:
        min_year = min(years)
        max_year = max(years)
        default_year = years[0]
    else:
        # Sensible fallback based on Tableau dashboard (2025–2029)
        min_year, max_year, default_year = 2025, 2029, 2025
    
    # Countries for legend (match CSV as closely as possible)
    all_countries_from_data = get_unique_countries()
    legend_countries = (
        sorted(all_countries_from_data)
        if all_countries_from_data
        else sorted(list(COUNTRY_COLORS.keys()))
    )
    
    # Build clickable legend items – these are targeted by the pattern-matching callbacks
    legend_items = []
    for country in legend_countries:
        color = get_country_color(country)
        legend_items.append(
            html.Div(
                id={'type': 'country-item', 'index': country},
                children=[
                    html.Div(
                        style={
                            'width': '12px',
                            'height': '12px',
                            'backgroundColor': color,
                            'marginRight': '6px',
                            'borderRadius': '2px',
                            'flexShrink': '0'
                        }
                    ),
                    html.Span(
                        country,
                        style={
                            'fontSize': '12px',
                            'color': '#2c3e50',
                            'whiteSpace': 'nowrap'
                        }
                    )
                ],
                style={
                    'display': 'flex',
                    'alignItems': 'center',
                    'marginBottom': '4px',
                    'padding': '2px 4px',
                    'cursor': 'pointer',
                    'borderRadius': '3px'
                }
            )
        )
    
    layout = html.Div([
        # Stores and interval used by callbacks
        dcc.Store(id='selected-countries-store', data=[]),
        dcc.Store(id='year-period-play-store', data=False),
        dcc.Interval(
            id='year-period-interval',
            interval=2000,  # 2 seconds between steps when playing
            n_intervals=0,
            disabled=True
        ),
        
        # Top bar – only Company filter, matching Tableau
        html.Div([
            html.Label(
                "Company",
                style={
                    'fontSize': '12px',
                    'fontWeight': 'bold',
                    'color': '#1b365d',
                    'marginRight': '8px'
                }
            ),
            dcc.Dropdown(
                id='company-filter',
                options=[{'label': 'Exxon Mobil', 'value': 'Exxon Mobil'}],
                value='Exxon Mobil',
                clearable=False,
                style={'minWidth': '220px'}
            )
        ], style={
            'display': 'flex',
            'alignItems': 'center',
            'marginBottom': '8px'
        }),
        
        # Main content – chart/map on the left, legend & filters on the right
        html.Div([
            # LEFT COLUMN: bar chart, map, table
            html.Div([
                dcc.Graph(
                    id='projects-company-bar-chart',
                    style={'height': '500px', 'marginBottom': '20px'}
                ),
                dcc.Graph(
                    id='projects-company-map',
                    style={'height': '500px', 'marginBottom': '20px'}
                ),
                # Projects table
                html.H3(
                    "Projected Oil Capacity Details by Company",
                    style={
                        'color': '#FF8C42',
                        'font-family': 'Georgia, serif',
                        'margin-top': '10px',
                        'margin-bottom': '8px',
                        'fontWeight': 'bold',
                        'fontSize': '22px',
                        'textAlign': 'left'
                    }
                ),
                dash_table.DataTable(
                    id='projects-company-table',
                    columns=columns,
                    data=data,
                    page_action='none',
                    style_table={
                        'overflowX': 'auto',
                        'overflowY': 'auto',
                        'maxHeight': '520px',
                        'width': '100%',
                        'border': 'none',
                        'backgroundColor': '#fff'
                    },
                    style_header={
                        'backgroundColor': '#fff',
                        'fontWeight': 'bold',
                        'color': '#2c3e50',
                        'fontSize': '15px',
                        'border': '1px solid #e0e0e0',
                        'textAlign': 'left',
                        'font-family': 'Arial, sans-serif'
                    },
                    style_cell={
                        'textAlign': 'left',
                        'padding': '6px 8px',
                        'whiteSpace': 'nowrap',
                        'overflow': 'hidden',
                        'textOverflow': 'ellipsis',
                        'fontSize': '13px',
                        'border': '1px solid #e0e0e0',
                        'backgroundColor': '#fff',
                        'font-family': 'Arial, sans-serif'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#fafbfc'
                        }
                    ],
                    fixed_rows={'headers': True},
                    sort_action='none',
                    filter_action='none',
                    row_selectable=False,
                    selected_rows=[],
                    css=[{
                        'selector': '.dash-table-container .dash-spreadsheet-inner tr th',
                        'rule': 'text-transform: none;'
                    }]
                )
            ], style={'flex': '3', 'minWidth': '0'}),
            
            # RIGHT COLUMN: legend, Likely To Go, year controls, history toggle
            html.Div([
                html.Div(
                    "Country",
                    style={
                        'fontWeight': 'bold',
                        'fontSize': '13px',
                        'color': '#1b365d',
                        'marginBottom': '4px'
                    }
                ),
                html.Div(
                    legend_items,
                    style={
                        'display': 'flex',
                        'flexDirection': 'column',
                        'flexWrap': 'nowrap',
                        'maxHeight': '260px',
                        'overflowY': 'auto',
                        'padding': '6px 8px',
                        'border': '1px solid #e0e0e0',
                        'borderRadius': '4px',
                        'backgroundColor': '#fafafa',
                        'marginBottom': '10px'
                    }
                ),
                
                html.Div([
                    html.Label(
                        "Likely To Go",
                        style={
                            'fontSize': '12px',
                            'fontWeight': 'bold',
                            'color': '#1b365d',
                            'display': 'block',
                            'marginBottom': '4px'
                        }
                    ),
                    dcc.RadioItems(
                        id='likely-to-go-filter',
                        options=[
                            {'label': '(All)', 'value': 'ALL'},
                            {'label': 'N', 'value': 'N'},
                            {'label': 'Uncertain', 'value': 'U'},
                            {'label': 'Y', 'value': 'Y'},
                        ],
                        value='Y',
                        labelStyle={
                            'display': 'block',
                            'fontSize': '12px',
                            'marginBottom': '2px'
                        }
                    )
                ], style={'marginBottom': '14px'}),
                
                html.Div([
                    html.Label(
                        "Year of Period",
                        style={
                            'fontSize': '12px',
                            'fontWeight': 'bold',
                            'color': '#1b365d',
                            'display': 'block',
                            'marginBottom': '4px'
                        }
                    ),
                    html.Div([
                        dcc.Dropdown(
                            id='year-of-period-filter',
                            options=[{'label': str(y), 'value': y} for y in years] if years else [],
                            value=default_year,
                            clearable=False,
                            style={'width': '110px', 'marginRight': '6px'}
                        ),
                        html.Button(
                            '◀',
                            id='year-period-prev',
                            n_clicks=0,
                            style={
                                'border': '1px solid #d0d0d0',
                                'backgroundColor': '#ffffff',
                                'padding': '2px 6px',
                                'fontSize': '12px',
                                'cursor': 'pointer',
                                'marginRight': '2px'
                            }
                        ),
                        html.Button(
                            '▶',
                            id='year-period-next',
                            n_clicks=0,
                            style={
                                'border': '1px solid #d0d0d0',
                                'backgroundColor': '#ffffff',
                                'padding': '2px 6px',
                                'fontSize': '12px',
                                'cursor': 'pointer'
                            }
                        )
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], style={'marginBottom': '10px'}),
                
                html.Div([
                    dcc.Slider(
                        id='year-period-slider',
                        min=min_year,
                        max=max_year,
                        step=1,
                        value=default_year,
                        marks={y: str(y) for y in years} if years else {},
                        included=False
                    )
                ], style={'marginBottom': '8px'}),
                
                html.Div([
                    html.Button(
                        '◀',
                        id='year-period-timeline-prev',
                        n_clicks=0,
                        style={
                            'border': '1px solid #d0d0d0',
                            'backgroundColor': '#ffffff',
                            'padding': '2px 6px',
                            'fontSize': '12px',
                            'cursor': 'pointer',
                            'marginRight': '6px'
                        }
                    ),
                    html.Button(
                        '▶',
                        id='year-period-play',
                        n_clicks=0,
                        style={
                            'border': '1px solid #d0d0d0',
                            'backgroundColor': '#ffffff',
                            'padding': '2px 8px',
                            'fontSize': '12px',
                            'cursor': 'pointer',
                            'marginRight': '6px'
                        }
                    ),
                    html.Button(
                        '■',
                        id='year-period-stop',
                        n_clicks=0,
                        style={
                            'border': '1px solid #d0d0d0',
                            'backgroundColor': '#ffffff',
                            'padding': '2px 8px',
                            'fontSize': '12px',
                            'cursor': 'pointer'
                        }
                    )
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '6px'}),
                
                dcc.Checklist(
                    id='show-history-checkbox',
                    options=[{'label': 'Show history', 'value': 'history'}],
                    value=['history'],
                    labelStyle={'fontSize': '12px'}
                ),
                
                html.Div(
                    id='year-period-display',
                    style={
                        'marginTop': '8px',
                        'fontSize': '12px',
                        'fontWeight': 'bold',
                        'color': '#1b365d'
                    }
                )
            ], style={
                'flex': '1',
                'minWidth': '260px',
                'maxWidth': '320px',
                'marginLeft': '20px'
            })
        ], style={
            'display': 'flex',
            'alignItems': 'flex-start'
        })
    ], style={'padding': '10px 18px'})
    return layout

def register_callbacks(dash_app, server):
    """Register callbacks for the Projects by Company view. (No interactive callbacks required for the static table display.)"""
    # No callbacks required for static table display. Placeholder kept for future use.
    return

def register_callbacks(dash_app, server):
    """Register all callbacks for Projects by Company"""
    
    # Get all countries from CSV data for creating dynamic outputs
    # This ensures all countries in the data are available for filtering
    all_countries_from_data = get_unique_countries()
    legend_countries = sorted(all_countries_from_data) if all_countries_from_data else sorted(list(COUNTRY_COLORS.keys()))
    
    # Create outputs for all country items
    country_outputs = [
        Output({'type': 'country-item', 'index': country}, 'style')
        for country in legend_countries
    ]
    
    @callback(
        Output('selected-countries-store', 'data', allow_duplicate=True),
        Input({'type': 'country-item', 'index': ALL}, 'n_clicks'),
        State('selected-countries-store', 'data'),
        prevent_initial_call=True
    )
    def toggle_country(_clicks, selected_countries):
        """Toggle country selection on click"""
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update
        
        # Get the triggered country
        triggered = ctx.triggered[0]["prop_id"]
        try:
            country_id = json.loads(triggered.split('.')[0])
            clicked_country = country_id.get("index")
        except (ValueError, TypeError, AttributeError, KeyError):
            return dash.no_update
        
        if not clicked_country or clicked_country not in legend_countries:
            return dash.no_update
        
        # Initialize selected_countries if None
        if selected_countries is None:
            selected_countries = []
        
        # Toggle the clicked country
        if clicked_country in selected_countries:
            # Deselect
            new_selected = [c for c in selected_countries if c != clicked_country]
        else:
            # Select
            new_selected = selected_countries + [clicked_country] if selected_countries else [clicked_country]
        
        return new_selected
    
    @callback(
        country_outputs,
        Input('selected-countries-store', 'data'),
        prevent_initial_call=False
    )
    def update_country_styles(selected_countries):
        """Update country item styles based on store"""
        selected_countries = selected_countries or []
        styles = []
        for country in legend_countries:
            is_selected = country in selected_countries
            country_color = get_country_color(country)
            # Match Tableau design: selected countries get a colored border matching their color
            # and a subtle background highlight
            styles.append({
                'display': 'flex',
                'alignItems': 'center',
                'marginBottom': '4px',
                'padding': '2px 4px',
                'cursor': 'pointer',
                'borderRadius': '3px',
                'border': f'2px solid {country_color}' if is_selected else '1px solid transparent',
                'backgroundColor': 'rgba(240, 240, 240, 0.5)' if is_selected else 'transparent',
                'transition': 'all 0.2s ease'
            })
        return styles
    
    # Initial callback to set year display
    @callback(
        Output('year-period-display', 'children', allow_duplicate=True),
        Input('year-of-period-filter', 'value'),
        prevent_initial_call='initial_duplicate'
    )
    def initialize_year_display(year_value):
        """Initialize year display on page load"""
        if year_value:
            return str(year_value)
        years = get_unique_years()
        return str(years[0]) if years else '2025'
    
    # Callback to sync year controls (display, dropdown, slider, prev/next buttons)
    @callback(
        [Output('year-period-display', 'children'),
         Output('year-of-period-filter', 'value', allow_duplicate=True),
         Output('year-period-slider', 'value', allow_duplicate=True)],
        [Input('year-of-period-filter', 'value'),
         Input('year-period-slider', 'value'),
         Input('year-period-prev', 'n_clicks'),
         Input('year-period-next', 'n_clicks'),
         Input('year-period-timeline-prev', 'n_clicks'),
         Input('year-period-interval', 'n_intervals')],
        [State('year-period-slider', 'min'),
         State('year-period-slider', 'max'),
         State('year-period-play-store', 'data')],
        prevent_initial_call=True
    )
    def sync_year_controls(dropdown_value, slider_value, prev_clicks, next_clicks, 
                           timeline_prev_clicks, interval_tick, min_year, max_year, is_playing):
        """Sync year display, dropdown, slider, and navigation buttons"""
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        current_year = dropdown_value or slider_value or min_year
        
        try:
            current_year = int(current_year)
        except (ValueError, TypeError):
            current_year = min_year
        
        # Handle different triggers
        if trigger_id == 'year-period-prev':
            new_year = max(current_year - 1, min_year)
        elif trigger_id == 'year-period-next':
            new_year = min(current_year + 1, max_year)
        elif trigger_id == 'year-period-timeline-prev':
            new_year = max(current_year - 1, min_year)
        elif trigger_id == 'year-period-interval':
            if is_playing:
                # Auto-advance to next year, loop back to min if at max
                if current_year >= max_year:
                    new_year = min_year
                else:
                    new_year = current_year + 1
            else:
                return dash.no_update, dash.no_update, dash.no_update
        elif trigger_id == 'year-of-period-filter':
            new_year = dropdown_value
        elif trigger_id == 'year-period-slider':
            new_year = slider_value
        else:
            new_year = current_year
        
        return str(new_year), new_year, new_year
    
    # Callback to handle play/pause/stop buttons
    @callback(
        [Output('year-period-play-store', 'data'),
         Output('year-period-interval', 'disabled'),
         Output('year-period-play', 'children')],
        [Input('year-period-play', 'n_clicks'),
         Input('year-period-stop', 'n_clicks')],
        [State('year-period-play-store', 'data')],
        prevent_initial_call=True
    )
    def toggle_year_animation(play_clicks, stop_clicks, is_playing):
        """Toggle auto-play animation of the year slider"""
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'year-period-stop':
            return False, True, '▶'  # Stop playing
        elif trigger_id == 'year-period-play':
            # Toggle play state
            new_state = not bool(is_playing)
            return new_state, not new_state, '⏸' if new_state else '▶'
        
        return dash.no_update, dash.no_update, dash.no_update
    
    @callback(
        [Output('projects-company-bar-chart', 'figure'),
         Output('projects-company-map', 'figure')],
        [Input('current-submenu', 'data'),
         Input('company-filter', 'value'),
         Input('likely-to-go-filter', 'value'),
         Input('year-of-period-filter', 'value'),
         Input('year-period-slider', 'value'),
         Input('show-history-checkbox', 'value'),
         Input('selected-countries-store', 'data')],
        prevent_initial_call=False
    )
    def update_projects_by_company(submenu, company, likely_to_go, selected_year, slider_year, show_history, selected_countries):
        """Update projects by company chart and map"""
        # Handle RadioItems value (single value instead of list)
        if isinstance(likely_to_go, list):
            likely_to_go = likely_to_go[0] if likely_to_go else 'Y'
        
        # Check if this is the correct submenu (allow None on initial load)
        if submenu is not None and submenu != 'projects-company':
            empty_fig = go.Figure()
            empty_fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return empty_fig, empty_fig
        
        # Use the year from dropdown or slider (whichever is more recent)
        year_to_use = selected_year if selected_year else slider_year
        if not year_to_use:
            year_to_use = get_unique_years()[0] if get_unique_years() else 2025
        
        # Filter data
        df = DATA_DF.copy()
        
        if df.empty:
            empty_fig = go.Figure()
            empty_fig.add_annotation(
                text="No data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            empty_fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return empty_fig, empty_fig
        
        # Note: Likely To Go filter would require additional data column
        # For now, we'll skip this filter as it's not in the CSV
        
        # Use selected countries for filtering
        # If empty list, show all countries. If countries are selected, show only those.
        countries_to_show = selected_countries if selected_countries else None
        
        # Create bar chart - show all years by default (matches Tableau behavior)
        # The bar chart displays all available years/quarters
        bar_df = df.copy()
        bar_fig = create_stacked_bar_chart(bar_df, company or "Company", countries_to_show)
        
        # Create map - always filtered by selected year (Year of Period filter controls the map)
        map_fig = create_world_map(df, year_to_use, company or "Company")
        
        return bar_fig, map_fig
