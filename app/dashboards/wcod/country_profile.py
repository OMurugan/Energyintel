"""
Country Profile View
World map-based country profile with detailed statistics
Replicates Energy Intelligence WCoD Country Profile functionality
"""
from dash import dcc, html, Input, Output, callback, dash_table, dash
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import os

# CSV paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'Country_Profile')
MAP_CSV = os.path.join(DATA_DIR, 'Map_data.csv')
MONTHLY_PRODUCTION_CSV = os.path.join(DATA_DIR, 'Monthly_Production_data.csv')
PORT_DETAIL_CSV = os.path.join(DATA_DIR, 'Port-Detail_data.csv')

# Load CSV data
try:
    map_df = pd.read_csv(MAP_CSV)
    map_df.columns = map_df.columns.str.strip()
    
    # Handle duplicate column names - pandas adds .1, .2 etc. for duplicates
    # Find the country_long_name column that has actual data (not empty)
    country_cols = [col for col in map_df.columns if 'country_long_name' in col]
    if len(country_cols) > 1:
        # Use the column that has non-null/non-empty values
        for col in sorted(country_cols):  # Check in order
            if col in map_df.columns:
                # Check if column has non-empty values
                non_empty = map_df[col].dropna()
                if len(non_empty) > 0 and (non_empty.astype(str).str.strip() != '').any():
                    map_df['country_long_name'] = map_df[col].astype(str).str.strip()
                    # Drop duplicate columns
                    for dup_col in country_cols:
                        if dup_col != 'country_long_name' and dup_col in map_df.columns:
                            map_df = map_df.drop(columns=[dup_col])
                    break
    elif 'country_long_name' in map_df.columns:
        map_df['country_long_name'] = map_df['country_long_name'].astype(str).str.strip()
    
    # Get unique countries from map data for dropdown
    if not map_df.empty and 'country_long_name' in map_df.columns:
        country_list = sorted(map_df['country_long_name'].dropna().unique().tolist())
        country_list = [str(c).strip() for c in country_list if c and str(c).strip() and str(c).strip() != 'nan']  # Remove empty strings and NaN
        # Set default to United States
        default_country = 'United States' if 'United States' in country_list else (country_list[0] if country_list else None)
    else:
        country_list = []
        default_country = None
except Exception as e:
    print(f"Error loading map data: {e}")
    import traceback
    traceback.print_exc()
    map_df = pd.DataFrame()
    country_list = []
    default_country = None

try:
    monthly_prod_df = pd.read_csv(MONTHLY_PRODUCTION_CSV)
    monthly_prod_df.columns = monthly_prod_df.columns.str.strip()
except Exception:
    monthly_prod_df = pd.DataFrame()

try:
    port_df = pd.read_csv(PORT_DETAIL_CSV, quotechar='"', skipinitialspace=True)
    port_df.columns = port_df.columns.str.strip()
    # Clean up port names (remove quotes if present)
    if 'Port Name' in port_df.columns:
        port_df['Port Name'] = port_df['Port Name'].astype(str).str.strip().str.strip('"')
except Exception as e:
    print(f"Error loading port data: {e}")
    import traceback
    traceback.print_exc()
    port_df = pd.DataFrame()


def create_layout(server):
    """Create the Country Profile layout with filters and world map"""
    # Create country options from map data
    country_options = [{'label': country, 'value': country} for country in country_list]
    
    # Initialize map with default country data
    try:
        initial_map = create_world_map(default_country)
    except Exception:
        initial_map = create_empty_map()

    # Initial profile URL
    initial_profile_url = f"https://www.energyintel.com/wcod/country-profile/{default_country.lower().replace(' ', '-')}" if default_country else "#"
    

    # Dropdown style (smaller width and padding)
    dropdown_style = {
        'fontSize': '14px',
        'width': '200px'  # Smaller width
    }

    label_style = {
        'fontWeight': '600',
        'fontSize': '14px',
        'color': '#2c3e50',
        'marginBottom': '8px',
        'display': 'block'
    }

    # Profile link style (border only, no background, orange text, orange border on hover)
    profile_link_style = {
        'display': 'inline-block',
        'padding': '8px 16px',
        'backgroundColor': 'transparent',
        'color': '#fe5000',  # Orange text color
        'textDecoration': 'none',
        'fontSize': '14px',
        'fontWeight': '500',
        'borderRadius': '4px',
        'border': '1px solid #cccccc',
        'cursor': 'pointer',
        'textAlign': 'center',
        'transition': 'border-color 0.3s ease'
    }
    return html.Div([
        # Store for selected country
        dcc.Store(id='selected-country-profile-store', data=default_country),
        # Store for time period (Yearly/Monthly)
        dcc.Store(id='time-period-store', data='Monthly'),
        
        # Filters Section
        html.Div([
            html.Div([
                # Flex container for alignment
                html.Div([
                    # Country selector (smaller width)
                    html.Div([
                        html.Label("Select Country:", style=label_style),
                        dcc.Dropdown(
                            id='country-select-profile',
                            options=country_options,
                            value=default_country,
                            clearable=False,
                            placeholder="Select a country...",
                            style=dropdown_style
                        )
                    ], style={'width': '220px', 'marginRight': '20px'}),
                    


                    # Time period selector (smaller width)
                    html.Div([
                        html.Label("Yearly or Monthly:", style=label_style),
                        dcc.Dropdown(
                            id='time-period-select',
                            options=[
                                {'label': 'Yearly', 'value': 'Yearly'},
                                {'label': 'Monthly', 'value': 'Monthly'}
                            ],
                            value='Monthly',
                            clearable=False,
                            style=dropdown_style
                        )
                    ], style={'width': '220px', 'marginRight': '20px'}),
                    
                    # Profile link container (border only, hover orange)
                    html.Div([
                        html.A(
                            id='profile-link',
                            href=initial_profile_url,
                            target='_blank',
                            children="Click here to see the Country's Profile",
                            style=profile_link_style,
                            className='profile-link-hover'
                        )
                    ], style={'flex': '1', 'textAlign': 'right', 'display': 'flex', 'alignItems': 'flex-end', 'justifyContent': 'flex-end'})
                ], style={
                    'display': 'flex',
                    'alignItems': 'flex-end',
                    'gap': '20px',
                    'width': '100%'
                })
            ], style={'padding': '20px 30px', 'background': 'white', 'borderBottom': '1px solid #e0e0e0'})
        ]),
        
        # World Map Section with hover controls (full screen)
        html.Div([
            html.Div([
                # Map container with relative positioning for controls overlay
                html.Div([
                    dcc.Graph(
                        id='world-map-chart',
                        figure=initial_map,
                        style={
                            'height': 'calc(100vh - 150px)',  # Full screen height minus filters only
                            'width': '100vw',  # Full viewport width - no space
                            'maxWidth': '100%',
                            'background': 'white',
                            'borderRadius': '0',
                            'boxShadow': 'none',
                            'margin': '0',  # No margin - full width
                            'padding': '0',
                            'position': 'relative',
                            'display': 'block'
                        }
                    ),
                    # Map controls (left side, always visible)
                    html.Div([
                        html.Div([
                            html.Button('🔍', style={'width': '32px', 'height': '32px', 'border': '1px solid #d0d0d0', 'background': 'white', 'cursor': 'pointer', 'borderRadius': '2px', 'marginBottom': '4px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'fontSize': '14px'}),
                            html.Button('📋', style={'width': '32px', 'height': '32px', 'border': '1px solid #d0d0d0', 'background': 'white', 'cursor': 'pointer', 'borderRadius': '2px', 'marginBottom': '4px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'fontSize': '14px'}),
                            html.Button('+', style={'width': '32px', 'height': '32px', 'border': '1px solid #d0d0d0', 'background': 'white', 'cursor': 'pointer', 'borderRadius': '2px', 'marginBottom': '4px', 'fontSize': '18px', 'fontWeight': 'bold', 'lineHeight': '1'}),
                            html.Button('−', style={'width': '32px', 'height': '32px', 'border': '1px solid #d0d0d0', 'background': 'white', 'cursor': 'pointer', 'borderRadius': '2px', 'marginBottom': '4px', 'fontSize': '18px', 'fontWeight': 'bold', 'lineHeight': '1'}),
                            html.Button('⌂', style={'width': '32px', 'height': '32px', 'border': '1px solid #d0d0d0', 'background': 'white', 'cursor': 'pointer', 'borderRadius': '2px', 'marginBottom': '4px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'fontSize': '14px'}),
                            html.Button('▶', style={'width': '32px', 'height': '32px', 'border': '1px solid #d0d0d0', 'background': 'white', 'cursor': 'pointer', 'borderRadius': '2px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'fontSize': '12px'})
                        ], style={'display': 'flex', 'flexDirection': 'column', 'padding': '4px', 'background': 'white', 'border': '1px solid #d0d0d0', 'borderRadius': '4px', 'boxShadow': '0 1px 3px rgba(0,0,0,0.1)'})
                    ], className='map-controls', style={
                        'position': 'absolute',
                        'left': '10px',
                        'top': '10px',
                        'opacity': '1',
                        'zIndex': '1000'
                    })
                ], style={'position': 'relative', 'width': '100vw', 'maxWidth': '100%', 'height': 'calc(100vh - 150px)', 'margin': '0', 'padding': '0', 'overflow': 'hidden'}, className='map-container')
            ], style={'padding': '0', 'background': '#f8f9fa', 'width': '100vw', 'maxWidth': '100%', 'height': 'calc(100vh - 150px)', 'margin': '0', 'overflow': 'hidden', 'position': 'relative'})
        ], style={'width': '100vw', 'maxWidth': '100%', 'height': 'calc(100vh - 150px)', 'margin': '0', 'padding': '0', 'overflow': 'hidden', 'position': 'relative', 'display': 'block'}),
        
        # CSS injection div (will be handled by clientside callback)
        html.Div(id='css-injection-placeholder', style={'display': 'none'}),
        
        # Country Details Section (shown when country is selected)
        html.Div(id='country-profile-content', style={'padding': '24px', 'background': '#f8f9fa'})
    ])


def create_world_map(selected_country=None):
    """Create world map choropleth using Map_data.csv, filtered by selected country"""
    if map_df.empty:
        return create_empty_map()
    
    # Filter by selected country if provided
    if selected_country and 'country_long_name' in map_df.columns:
        # Filter by country name (handle case sensitivity and string conversion)
        filtered_map = map_df[map_df['country_long_name'].astype(str).str.strip() == str(selected_country).strip()].copy()
    else:
        filtered_map = map_df.copy()
    
    if filtered_map.empty:
        return create_empty_map()
    
    # Ensure required columns exist
    required_cols = ['Port Name', 'latitude', 'longitude']
    if not all(col in filtered_map.columns for col in required_cols):
        return create_empty_map()
    
    # Group by country to get port counts and locations
    if selected_country:
        # For selected country, show individual ports and highlight the country
        port_data = filtered_map[['Port Name', 'latitude', 'longitude']].copy()
        port_data = port_data.dropna(subset=['latitude', 'longitude'])
        
        if port_data.empty:
            return create_empty_map()
        
        fig = go.Figure()
        
        # Add choropleth to highlight the selected country
        # Map country names to ISO codes (common mappings)
        country_to_iso = {
            'United States': 'USA',
            'United Kingdom': 'GBR',
            'Saudi Arabia': 'SAU',
            'Russia': 'RUS',
            'China': 'CHN',
            'India': 'IND',
            'Brazil': 'BRA',
            'Canada': 'CAN',
            'Mexico': 'MEX',
            'Venezuela': 'VEN',
            'Nigeria': 'NGA',
            'Angola': 'AGO',
            'Algeria': 'DZA',
            'Libya': 'LBY',
            'Iraq': 'IRQ',
            'Iran': 'IRN',
            'Kuwait': 'KWT',
            'United Arab Emirates': 'ARE',
            'Qatar': 'QAT',
            'Norway': 'NOR',
            'Kazakhstan': 'KAZ',
            'Azerbaijan': 'AZE',
            'Indonesia': 'IDN',
            'Malaysia': 'MYS',
            'Thailand': 'THA',
            'Vietnam': 'VNM',
            'Australia': 'AUS',
            'Colombia': 'COL',
            'Ecuador': 'ECU',
            'Argentina': 'ARG',
            'Chile': 'CHL',
            'Peru': 'PER',
            'Egypt': 'EGY',
            'Sudan': 'SDN',
            'South Sudan': 'SSD',
            'Gabon': 'GAB',
            'Congo': 'COG',
            'Equatorial Guinea': 'GNQ',
            'Cameroon': 'CMR',
            'Ghana': 'GHA',
            'Côte d\'Ivoire': 'CIV',
            'Tunisia': 'TUN',
            'Oman': 'OMN',
            'Yemen': 'YEM',
            'Turkmenistan': 'TKM',
            'Uzbekistan': 'UZB',
            'Azerbaijan': 'AZE',
            'Georgia': 'GEO',
            'Turkey': 'TUR',
            'Greece': 'GRC',
            'Italy': 'ITA',
            'Spain': 'ESP',
            'France': 'FRA',
            'Germany': 'DEU',
            'Netherlands': 'NLD',
            'Belgium': 'BEL',
            'Denmark': 'DNK',
            'Sweden': 'SWE',
            'Finland': 'FIN',
            'Poland': 'POL',
            'Romania': 'ROU',
            'Bulgaria': 'BGR',
            'Ukraine': 'UKR',
            'Japan': 'JPN',
            'South Korea': 'KOR',
            'Philippines': 'PHL',
            'Singapore': 'SGP',
            'Brunei': 'BRN',
            'Myanmar': 'MMR',
            'Bangladesh': 'BGD',
            'Pakistan': 'PAK',
            'Sri Lanka': 'LKA'
        }
        
        # Get ISO code for selected country
        country_iso = country_to_iso.get(selected_country, None)
        
        if country_iso:
            # Create a choropleth to highlight the selected country
            all_countries = list(country_to_iso.values())
            country_values = [1 if code == country_iso else 0 for code in all_countries]
            
            fig.add_trace(go.Choropleth(
                locations=all_countries,
                z=country_values,
                colorscale=[[0, 'rgba(232,232,232,0.5)'], [1, 'rgba(142, 153, 208, 1)']],  # Light gray for others, light blue for selected (matching image)
                showscale=False,
                geo='geo',
                hoverinfo='skip'
            ))
        
        # Add scatter points for each port with orange-red markers and varied symbols
        for _, row in port_data.iterrows():
            port_name = row['Port Name'] if pd.notna(row['Port Name']) else 'Unknown'
            lat = float(row['latitude']) if pd.notna(row['latitude']) else 0
            lon = float(row['longitude']) if pd.notna(row['longitude']) else 0
            
            # Skip invalid coordinates
            if lat == 0 and lon == 0:
                continue
            
            # Use circle or cross symbol based on port name (example logic, adjust as needed)
            symbol = 'circle' if 'City' in str(port_name) else 'circle'
            fig.add_trace(go.Scattergeo(
                lon=[lon],
                lat=[lat],
                text=port_name,
                mode='markers',
                marker=dict(
                    size=18,
                    color='#fe5000',  # Orange-red for ports
                    opacity=0.9,
                    line=dict(width=2, color='white'),
                    symbol=symbol
                ),
                name=port_name,
                hovertemplate='<b>Port name: %{text}</b><extra></extra>',
                showlegend=False
            ))
        
        title_text = f"{selected_country} Production"
    else:
        # For all countries, show aggregated data
        if 'country_long_name' in filtered_map.columns:
            country_data = filtered_map.groupby('country_long_name').agg({
                'Port': 'count',
                'latitude': 'mean',
                'longitude': 'mean'
            }).reset_index()
            
            country_data.columns = ['country', 'port_count', 'lat', 'lon']
            country_data = country_data.dropna(subset=['lat', 'lon'])
            
            if country_data.empty:
                return create_empty_map()
            
            fig = go.Figure()
            
            # Add scatter points for each country
            for _, row in country_data.iterrows():
                fig.add_trace(go.Scattergeo(
                    lon=[float(row['lon'])],
                    lat=[float(row['lat'])],
                    text=[f"{row['country']}<br>Ports: {int(row['port_count'])}"],
                    mode='markers',
                    marker=dict(
                        size=max(10, int(row['port_count']) * 5),
                        color='#0075A8',
                        opacity=0.7,
                        line=dict(width=1, color='white')
                    ),
                    name=row['country'],
                    hovertemplate='<b>%{text}</b><extra></extra>'
                ))
            
            title_text = 'World Crude Oil Ports by Country'
        else:
            return create_empty_map()
    
    fig.update_layout(
        title=None,  # No title on map - shown below map in red text
        geo=dict(
            scope='world',
            showframe=False,
            showcoastlines=True,
            projection_type='equirectangular',  # Square projection that maintains aspect ratio
            bgcolor='rgba(0,0,0,0)',
            coastlinecolor='#d0d0d0',  # Lighter gray for coastlines
            landcolor='#e8e8e8',  # Light gray for land (matching image)
            showocean=True,
            oceancolor='#e3f2fd',  # Light blue for ocean (matching image)
            showcountries=True,
            countrycolor='#bdbdbd',  # Medium gray for country borders (matching image)
            showlakes=False,
            showrivers=False,
            lonaxis_range=[-180, 180],
            lataxis_range=[-60, 75]  # Limit vertical range to reduce upper/lower empty space (no full zoom out)
        ),
        height=None,  # Auto height to fill container
        autosize=True,  # Auto-size to fill container width and height
        margin=dict(l=0, r=0, t=0, b=30),  # Bottom margin for copyright only
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False,
        annotations=[
            dict(
                text="© 2025 Mapbox © OpenStreetMap",
                xref="paper", yref="paper",
                x=0.01, y=0.01,
                xanchor="left", yanchor="bottom",
                showarrow=False,
                font=dict(size=10, color='#666666'),
                bgcolor='rgba(255,255,255,0.7)',
                bordercolor='rgba(255,255,255,0.7)',
                borderwidth=1
            )
        ]
    )
    
    return fig

def create_empty_map():
    """Create an empty world map when no data is available"""
    fig = go.Figure()
    
    fig.update_layout(
        title={
            'text': 'World Crude Oil Ports by Country',
            'x': 0.5,
            'xanchor': 'center',
            'font': {
                'size': 18,
                'family': 'Arial, sans-serif',
                'color': '#2c3e50'
            }
        },
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type='equirectangular',  # Square projection that maintains aspect ratio
            bgcolor='rgba(0,0,0,0)',
            coastlinecolor='#d0d0d0',  # Lighter gray for coastlines
            landcolor='#e8e8e8',  # Light gray for land (matching image)
            showocean=True,
            oceancolor='#e3f2fd',  # Light blue for ocean (matching image)
            showcountries=True,
            countrycolor='#bdbdbd',  # Medium gray for country borders (matching image)
            lonaxis_range=[-180, 180],
            lataxis_range=[-60, 75]  # Limit vertical range to reduce upper/lower empty space
        ),
        height=700,
        width=700,  # Square aspect ratio
        margin=dict(l=0, r=0, t=60, b=30),  # Bottom margin for copyright
        autosize=False,  # Disable autosize to maintain square
        plot_bgcolor='white',
        paper_bgcolor='white',
        annotations=[
            dict(
                text="No data available.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color='#7f8c8d')
            ),
            dict(
                text="© 2025 Mapbox © OpenStreetMap",
                xref="paper", yref="paper",
                x=0.01, y=0.01,
                xanchor="left", yanchor="bottom",
                showarrow=False,
                font=dict(size=10, color='#666666'),
                bgcolor='rgba(255,255,255,0.7)',
                bordercolor='rgba(255,255,255,0.7)',
                borderwidth=1
            )
        ]
    )
    
    return fig


def get_production_data(country_name, time_period='Yearly'):
    """Get production data for a country from Monthly_Production_data.csv"""
    if monthly_prod_df.empty:
        return pd.DataFrame()
    
    # Filter by country name (from Monthly production dynamic title column)
    # The column contains format like "United States Production"
    # So we check if country name is in the title
    if 'Monthly production dynamic title' in monthly_prod_df.columns:
        # Create a pattern to match: "CountryName Production"
        pattern = f"{country_name} Production"
        country_data = monthly_prod_df[
            monthly_prod_df['Monthly production dynamic title'].str.contains(pattern, case=False, na=False)
        ].copy()
    else:
        return pd.DataFrame()
    
    if country_data.empty:
        return pd.DataFrame()
    
    if time_period == 'Yearly':
        # Aggregate by year and crude type - sum the monthly values for yearly total
        yearly_data = country_data.groupby(['Year of Date', 'Crude']).agg({
            'Avg. Value': 'sum'  # Sum monthly values to get yearly total
        }).reset_index()
        yearly_data = yearly_data.sort_values('Year of Date', ascending=False)
        return yearly_data
    else:
        # Return monthly data - keep all columns needed
        monthly_data = country_data[['Year of Date', 'Month of Date', 'Crude', 'Avg. Value']].copy()
        # Sort by year (descending) and month
        monthly_data = monthly_data.sort_values(['Year of Date', 'Month of Date'], ascending=[False, True])
        return monthly_data


def get_port_details(country_name):
    """Get port details for a country from Port-Detail_data.csv"""
    if port_df.empty:
        return pd.DataFrame()
    
    # Filter by country - we need to match ports to countries
    # Since Port-Detail_data.csv doesn't have country column directly,
    # we'll use Map_data.csv to get ports for the country
    if not map_df.empty and 'country_long_name' in map_df.columns and 'Port Name' in map_df.columns:
        # Get all ports for the selected country
        country_ports = map_df[map_df['country_long_name'].astype(str).str.strip() == str(country_name).strip()]['Port Name'].dropna().unique()
        
        if len(country_ports) > 0:
            # Clean port names for matching (remove quotes, strip whitespace)
            country_ports_clean = [str(p).strip().strip('"') for p in country_ports]
            port_df_clean = port_df.copy()
            port_df_clean['Port Name Clean'] = port_df_clean['Port Name'].astype(str).str.strip().str.strip('"')
            
            # Filter port details by matching port names
            port_data = port_df_clean[port_df_clean['Port Name Clean'].isin(country_ports_clean)].copy()
            # Drop the temporary clean column
            if 'Port Name Clean' in port_data.columns:
                port_data = port_data.drop(columns=['Port Name Clean'])
            return port_data
    
    return pd.DataFrame()


def create_production_table(country_name, time_period='Yearly'):
    """Create production data table with pivot format for monthly view"""
    prod_data = get_production_data(country_name, time_period)
    
    if prod_data.empty:
        return dash_table.DataTable(
            data=[],
            columns=[],
            style_cell={'textAlign': 'left', 'fontFamily': 'Arial, sans-serif', 'fontSize': '13px'},
            style_header={
                'backgroundColor': '#f8f9fa',
                'fontWeight': '600',
                'color': '#2c3e50',
                'border': '1px solid #dee2e6'
            }
        )
    
    if time_period == 'Monthly':
        # Create pivot table: Crude as rows, Year-Month combinations as columns
        # First, ensure Year and Month are properly formatted
        prod_data['Year'] = prod_data['Year of Date'].astype(int)
        prod_data['Month'] = prod_data['Month of Date'].astype(str)
        
        # Get unique years and months in order (most recent first)
        years = sorted(prod_data['Year'].unique(), reverse=True)
        # Months in reverse chronological order (most recent first)
        months_order = ['July', 'June', 'May', 'April', 'March', 'February', 
                       'January', 'December', 'November', 'October', 'September', 'August']
        
        # Get unique crudes
        crudes = sorted(prod_data['Crude'].unique())
        
        # Build columns with nested structure (three-level headers: Date -> Year -> Month)
        columns = [{'name': ['', '', 'Crude'], 'id': 'Crude', 'type': 'text'}]
        
        # Add "Date" parent header
        date_cols = []
        for year in years:
            year_data = prod_data[prod_data['Year'] == year]
            year_months = sorted(year_data['Month'].unique(), 
                               key=lambda x: months_order.index(x) if x in months_order else 999)
            
            for month in year_months:
                col_id = f"{year}_{month}"
                date_cols.append({
                    'name': ['Date', str(year), month],
                    'id': col_id,
                    'type': 'numeric',
                    'format': {'specifier': ',.0f'}
                })
        
        columns.extend(date_cols)
        
        # Build table data by creating a pivot structure manually
        table_data = []
        for crude in crudes:
            row = {'Crude': crude}
            
            for year in years:
                year_data = prod_data[prod_data['Year'] == year]
                year_months = sorted(year_data['Month'].unique(),
                                   key=lambda x: months_order.index(x) if x in months_order else 999)
                
                for month in year_months:
                    col_id = f"{year}_{month}"
                    # Get value for this crude, year, month combination
                    value_row = prod_data[
                        (prod_data['Crude'] == crude) & 
                        (prod_data['Year'] == year) & 
                        (prod_data['Month'] == month)
                    ]
                    
                    if not value_row.empty:
                        value = value_row['Avg. Value'].iloc[0]
                        # Format as integer (no decimals) like in the image
                        row[col_id] = int(round(value)) if pd.notna(value) else ''
                    else:
                        row[col_id] = ''
            
            table_data.append(row)
        
    else:
        # Yearly view - simple table
        # Sort by year (descending) and crude name
        prod_data_sorted = prod_data.sort_values(['Year of Date', 'Crude'], ascending=[False, True])
        
        table_data = []
        for _, row in prod_data_sorted.iterrows():
            table_data.append({
                'Year': int(row['Year of Date']) if pd.notna(row['Year of Date']) else '',
                'Crude': row['Crude'] if pd.notna(row['Crude']) else '',
                'Avg. Value': f"{row['Avg. Value']:,.2f}" if pd.notna(row['Avg. Value']) else '0.00'
            })
        columns = [
            {'name': 'Year', 'id': 'Year', 'type': 'numeric'},
            {'name': 'Crude', 'id': 'Crude', 'type': 'text'},
            {'name': 'Avg. Value', 'id': 'Avg. Value', 'type': 'text'}
        ]
    
    return dash_table.DataTable(
        data=table_data,
        columns=columns,
        style_cell={
            'textAlign': 'left',
            'fontFamily': 'Arial, sans-serif',
            'fontSize': '13px',
            'padding': '12px',
            'border': '1px solid #dee2e6'
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': '600',
            'color': '#2c3e50',
            'border': '1px solid #dee2e6',
            'textAlign': 'center'
        },
        style_data={
            'border': '1px solid #dee2e6',
            'backgroundColor': 'white'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa'
            }
        ],
        page_action='none',
        filter_action='none',
        sort_action='none',
        merge_duplicate_headers=True
    )


def create_port_details_table(country_name):
    """Create port details table from Port-Detail_data.csv"""
    port_data = get_port_details(country_name)
    
    if port_data.empty:
        return dash_table.DataTable(
            data=[],
            columns=[],
            style_cell={'textAlign': 'left', 'fontFamily': 'Arial, sans-serif', 'fontSize': '13px'},
            style_header={
                'backgroundColor': '#f8f9fa',
                'fontWeight': '600',
                'color': '#2c3e50',
                'border': '1px solid #dee2e6'
            }
        )
    
    # Clean port names
    port_data['Port Name'] = port_data['Port Name'].astype(str).str.strip().str.strip('"')
    
    # Pivot the data to show ports as rows and measures as columns
    # Handle empty values properly
    port_data['value'] = port_data['value'].astype(str).str.strip()
    port_data['value'] = port_data['value'].replace(['', 'nan', 'NaN', 'None'], pd.NA)
    
    pivot_port = port_data.pivot_table(
        index='Port Name',
        columns='measure_name',
        values='value',
        aggfunc='first'
    ).reset_index()
    
    # Get coordinates
    coordinates = port_data.groupby('Port Name')['Coordinates'].first().reset_index()
    pivot_port = pivot_port.merge(coordinates, on='Port Name', how='left')
    
    # Helper function to format cell values (handle NaN, None, empty strings)
    def format_cell_value(val):
        if pd.isna(val) or val is None:
            return ''
        val_str = str(val).strip()
        if val_str == '' or val_str.lower() in ['nan', 'none', 'null']:
            return ''
        return val_str
    
    # Prepare table data - ensure all ports are included
    table_data = []
    for _, row in pivot_port.iterrows():
        port_name = format_cell_value(row.get('Port Name', ''))
        if not port_name:  # Skip if port name is empty
            continue
            
        table_data.append({
            'Port Name': port_name,
            'Coordinates': format_cell_value(row.get('Coordinates', '')),
            'Storage Capacity (million bbl)': format_cell_value(row.get('Storage Capacity (million bbl)', '')),
            'Mooring Type': format_cell_value(row.get('Mooring Type', '')),
            'Max. Tonnage (dwt)': format_cell_value(row.get('Max. Tonnage (dwt)', '')),
            'Max Loading Rate (bbl/hour)': format_cell_value(row.get('Max Loading Rate (bbl/hour)', '')),
            'Max length': format_cell_value(row.get('Max length', '')),
            'Max Draft': format_cell_value(row.get('Max Draft', '')),
            'Berths': format_cell_value(row.get('Berths', ''))
        })
    
    columns = [
        {'name': 'Port Name', 'id': 'Port Name', 'type': 'text'},
        {'name': 'Coordinates', 'id': 'Coordinates', 'type': 'text'},
        {'name': 'Storage Capacity (million bbl)', 'id': 'Storage Capacity (million bbl)', 'type': 'text'},
        {'name': 'Mooring Type', 'id': 'Mooring Type', 'type': 'text'},
        {'name': 'Max. Tonnage (dwt)', 'id': 'Max. Tonnage (dwt)', 'type': 'text'},
        {'name': 'Max Loading Rate (bbl/hour)', 'id': 'Max Loading Rate (bbl/hour)', 'type': 'text'},
        {'name': 'Max length', 'id': 'Max length', 'type': 'text'},
        {'name': 'Max Draft', 'id': 'Max Draft', 'type': 'text'},
        {'name': 'Berths', 'id': 'Berths', 'type': 'text'}
    ]
    
    return dash_table.DataTable(
        data=table_data,
        columns=columns,
        style_cell={
            'textAlign': 'left',
            'fontFamily': 'Arial, sans-serif',
            'fontSize': '13px',
            'padding': '12px',
            'border': '1px solid #dee2e6',
            'whiteSpace': 'normal',
            'height': 'auto'
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': '600',
            'color': '#2c3e50',
            'border': '1px solid #dee2e6',
            'textAlign': 'center'
        },
        style_data={
            'border': '1px solid #dee2e6',
            'backgroundColor': 'white'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa'
            }
        ],
        page_action='none',
        filter_action='none',
        sort_action='none',
        style_table={'overflowX': 'auto'}
    )


def register_callbacks(dash_app, server):
    """Register all callbacks for Country Profile"""
    
    @callback(
        [Output('country-profile-content', 'children'),
         Output('selected-country-profile-store', 'data')],
        [Input('country-select-profile', 'value'),
         Input('world-map-chart', 'clickData'),
         Input('time-period-select', 'value'),
         Input('url', 'pathname')],
        prevent_initial_call=False
    )
    def update_country_profile(selected_country, click_data, time_period, pathname):
        """Update country profile content based on selection"""
        # Determine which country is selected
        country_name = selected_country or default_country
        
        # Use default time period if not provided
        if not time_period:
            time_period = 'Monthly'
        
        # If map was clicked, we could update selection (for now, use dropdown value)
        if not country_name:
            return html.Div("Please select a country", style={'padding': '20px', 'textAlign': 'center'}), None
        
        # Create profile URL
        profile_url = f"https://www.energyintel.com/wcod/country-profile/{country_name.lower().replace(' ', '-')}"
        
        return html.Div([
            # Page Title with Profile Link
            html.Div([
                # html.Div([
                #     html.H4(
                #         country_name,
                #         style={
                #             'color': '#2c3e50',
                #             'fontWeight': '600',
                #             'fontSize': '24px',
                #             'marginBottom': '10px'
                #         }
                #     ),
                #     html.A(
                #         "Click here to see the Country's Profile",
                #         href=profile_url,
                #         target='_blank',
                #         style={
                #             'color': '#0075A8',
                #             'textDecoration': 'underline',
                #             'fontSize': '14px',
                #             'fontWeight': '500',
                #             'display': 'block',
                #             'marginBottom': '15px'
                #         }
                #     )
                # ])
            ], style={'padding': '20px 30px', 'background': 'white', 'borderBottom': '1px solid #e0e0e0'}),
            
            # Production Data Section
                html.Div([
                html.Div([
                    html.H5(
                        f"{country_name} Production",
                        style={
                            'color': '#fe5000',
                            'fontWeight': '600',
                            'fontSize': '18px',
                            'marginBottom': '20px'
                        }
                    ),
                    html.Div([
                        create_production_table(country_name, time_period)
                    ], style={'background': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
                ], className='col-md-12', style={'padding': '15px'})
            ], className='row', style={'margin': '30px 0', 'padding': '0 15px'}),
            
            # Port Details Section
            html.Div([
                html.Div([
                    html.H5(
                        f"{country_name} - Loading Port Details",
                        style={
                            'color': '#2c3e50',
                            'fontWeight': '600',
                            'fontSize': '18px',
                            'marginBottom': '20px'
                        }
                    ),
            html.Div([
                        create_port_details_table(country_name)
                    ], style={'background': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
                ], className='col-md-12', style={'padding': '15px'})
            ], className='row', style={'margin': '30px 0', 'padding': '0 15px'})
        ]), country_name
    
    @callback(
        Output('world-map-chart', 'figure'),
        [Input('country-select-profile', 'value'),
         Input('current-submenu', 'data'),
         Input('url', 'pathname')],
        prevent_initial_call=False
    )
    def update_world_map(selected_country, submenu, pathname):
        """Update world map when country selection changes or page loads"""
        # This callback is only registered for country profile, so always show the map
        # Use selected country or default
        country = selected_country or default_country
        
        try:
            return create_world_map(country)
        except Exception as e:
            print(f"Error updating world map: {e}")
            import traceback
            traceback.print_exc()
            return create_empty_map()
    
    @callback(
        Output('time-period-store', 'data'),
        Input('time-period-select', 'value'),
        prevent_initial_call=False
    )
    def update_time_period_store(time_period):
        """Update time period store"""
        return time_period or 'Monthly'
    
    @callback(
        Output('profile-link', 'href'),
        Input('country-select-profile', 'value'),
        prevent_initial_call=False
    )
    def update_profile_link(selected_country):
        """Update profile link when country changes"""
        country = selected_country or default_country
        if country:
            return f"https://www.energyintel.com/wcod/country-profile/{country.lower().replace(' ', '-')}"
        return "#"
    
    # Clientside callback to inject CSS for hover effects
    dash_app.clientside_callback(
        """
        function(n) {
            // Check if style already exists
            if (document.getElementById('country-profile-custom-css')) {
                return window.dash_clientside.no_update;
            }
            
            // Create and inject style tag
            const style = document.createElement('style');
            style.id = 'country-profile-custom-css';
            style.type = 'text/css';
            style.innerHTML = `
            .map-controls {
                opacity: 1 !important;
            }
                .profile-link-hover:hover {
                    border-color: #fe5000 !important;
                }
            `;
            document.head.appendChild(style);
            
            return window.dash_clientside.no_update;
        }
        """,
        Output('css-injection-placeholder', 'children'),
        Input('css-injection-placeholder', 'id'),
        prevent_initial_call=False
    )
