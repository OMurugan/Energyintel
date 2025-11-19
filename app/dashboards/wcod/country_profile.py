"""
Country Profile View
World map-based country profile with detailed statistics
Replicates Energy Intelligence WCoD Country Profile functionality
"""
from dash import dcc, html, Input, Output, dash_table, dash
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import os
from app import create_dash_app

# CSV paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'Country_Profile')
MAP_CSV = os.path.join(DATA_DIR, 'Map_data.csv')
MONTHLY_PRODUCTION_CSV = os.path.join(DATA_DIR, 'Monthly_Production.csv')
PORT_DETAIL_CSV = os.path.join(DATA_DIR, 'Port-Detail_data.csv')
KEY_FIGURES_CSV = os.path.join(DATA_DIR, 'Key Figures_data.csv')

# Load CSV data
try:
    map_df = pd.read_csv(MAP_CSV)
    map_df.columns = map_df.columns.str.strip()
    
    # Handle duplicate column names - pandas adds .1, .2 etc. for duplicates
    # Find the country_long_name column that has actual data (not empty)
    country_cols = [col for col in map_df.columns if 'country_long_name' in col]
    if len(country_cols) > 1:
        # Use the column that has the MOST non-null/non-empty values
        data_col = None
        max_non_empty = 0
        for col in sorted(country_cols):  # Check in order
            if col in map_df.columns:
                # Check if column has non-empty values (not just 'nan' strings)
                col_values = map_df[col].astype(str).str.strip()
                non_empty = col_values[~col_values.isin(['', 'nan', 'None', 'NaN'])]
                non_empty_count = len(non_empty)
                # Use the column with the most non-empty values
                if non_empty_count > max_non_empty:
                    max_non_empty = non_empty_count
                    data_col = col
        
        # If we found a column with data, use it
        if data_col:
            map_df['country_long_name'] = map_df[data_col].astype(str).str.strip()
            # Drop duplicate columns
            for dup_col in country_cols:
                if dup_col != 'country_long_name' and dup_col in map_df.columns:
                    map_df = map_df.drop(columns=[dup_col])
        else:
            # If no data found, use the first one
            map_df['country_long_name'] = map_df[country_cols[0]].astype(str).str.strip()
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
    # The CSV has nested headers: Row 1 = "Date" repeated, Row 2 = Years, Row 3 = "Crude", "Monthly production dynamic title", then months
    # Try different encodings and separators
    header_df = None
    data_df = None
    
    # Try different combinations of encoding and separator
    # UTF-16 with BOM is common for Excel exports
    encodings = ['utf-16', 'utf-16-le', 'utf-16-be', 'utf-8-sig', 'utf-8', 'latin-1']
    separators = ['\t', ',', ';']
    
    for encoding in encodings:
        for sep in separators:
            try:
                # Read first 3 rows to understand structure
                try:
                    header_df = pd.read_csv(MONTHLY_PRODUCTION_CSV, encoding=encoding, sep=sep, nrows=3, header=None, on_bad_lines='skip')
                except TypeError:
                    # Older pandas versions don't have on_bad_lines
                    header_df = pd.read_csv(MONTHLY_PRODUCTION_CSV, encoding=encoding, sep=sep, nrows=3, header=None, error_bad_lines=False)
                
                # Read the full data starting from row 4 (index 3)
                # Skip first 2 rows (row 0 and row 1), use row 2 as header, then read data from row 3 onwards
                try:
                    data_df = pd.read_csv(MONTHLY_PRODUCTION_CSV, encoding=encoding, sep=sep, skiprows=2, header=0, on_bad_lines='skip')
                except TypeError:
                    # Older pandas versions don't have on_bad_lines
                    data_df = pd.read_csv(MONTHLY_PRODUCTION_CSV, encoding=encoding, sep=sep, skiprows=2, header=0, error_bad_lines=False)
                
                print(f"Successfully loaded CSV with encoding={encoding}, sep='{sep}'")
                break
            except Exception as e:
                continue
        if header_df is not None and data_df is not None:
            break
    
    if header_df is None or data_df is None:
        raise Exception("Could not read CSV file with any encoding/separator combination")
    
    # Get header rows
    row1 = header_df.iloc[0].tolist() if len(header_df) > 0 else []
    row2 = header_df.iloc[1].tolist() if len(header_df) > 1 else []
    row3 = header_df.iloc[2].tolist() if len(header_df) > 2 else []
    
    # Clean column names (remove special characters and whitespace)
    data_df.columns = data_df.columns.astype(str).str.strip()
    
    # Find the "Crude" column (first column) and "Monthly production dynamic title" (second column)
    crude_col = data_df.columns[0] if len(data_df.columns) > 0 else None
    title_col = data_df.columns[1] if len(data_df.columns) > 1 else None
    
    # Also try to find the title column by name in case column order is different
    if title_col and 'production' not in title_col.lower() and 'monthly' not in title_col.lower():
        # Try to find it by searching column names
        for col in data_df.columns:
            if 'monthly' in col.lower() and 'production' in col.lower() and 'dynamic' in col.lower():
                title_col = col
                break
    
    print(f"DEBUG: CSV loading - crude_col='{crude_col}', title_col='{title_col}', total columns={len(data_df.columns)}")
    
    # Transform from wide to long format
    monthly_prod_list = []
    
    # Get data columns (skip first 2: Crude and Monthly production dynamic title)
    data_cols = data_df.columns[2:].tolist() if len(data_df.columns) > 2 else []
    
    for idx, row in data_df.iterrows():
        crude = str(row[crude_col]).strip() if crude_col and pd.notna(row[crude_col]) else ''
        title = str(row[title_col]).strip() if title_col and pd.notna(row[title_col]) else ''
        
        # Skip empty rows
        if not crude or crude.lower() in ['', 'nan', 'none']:
            continue
        
        # Process each data column
        for col_idx, col_name in enumerate(data_cols):
            # Get year from row2 (offset by 2 for first two columns)
            # data_cols[0] corresponds to data_df.columns[2], which should align with row2[2] and row3[2]
            year = ''
            month = ''
            
            # The data column index in the original CSV (accounting for first 2 columns: Crude and Title)
            csv_col_idx = col_idx + 2
            
            if csv_col_idx < len(row2):
                year_val = row2[csv_col_idx]
                if pd.notna(year_val):
                    year = str(year_val).strip()
            
            if csv_col_idx < len(row3):
                month_val = row3[csv_col_idx]
                if pd.notna(month_val):
                    month = str(month_val).strip()
            
            # Skip if year or month is invalid
            if not year or not year.isdigit() or not month or month.lower() in ['', 'nan', 'none', 'date', 'monthly production dynamic title']:
                continue
            
            # Get value
            value = row[col_name] if col_name in row.index else None
            
            # Convert value to numeric
            try:
                if pd.isna(value):
                    # Allow empty values for some cells (they'll show as empty in table)
                    # But still create the record so the table structure is correct
                    value_num = None
                else:
                    # Remove commas and convert
                    value_str = str(value).replace(',', '').strip()
                    if value_str and value_str.lower() not in ['', 'nan', 'none', 'null']:
                        value_num = float(value_str)
                    else:
                        value_num = None
                
                # Add record - use NaN for empty values (pandas handles this better)
                monthly_prod_list.append({
                    'Crude': crude,
                    'Monthly production dynamic title': title,
                    'Year of Date': int(year),
                    'Month of Date': month,
                    'Avg. Value': value_num if value_num is not None else pd.NA
                })
            except (ValueError, TypeError) as e:
                # Skip invalid values
                continue
    
    monthly_prod_df = pd.DataFrame(monthly_prod_list)
    
    if monthly_prod_df.empty:
        print(f"Warning: No production data loaded from {MONTHLY_PRODUCTION_CSV}")
    else:
        print(f"Loaded {len(monthly_prod_df)} production records from {MONTHLY_PRODUCTION_CSV}")
        if 'Monthly production dynamic title' in monthly_prod_df.columns:
            unique_countries = monthly_prod_df['Monthly production dynamic title'].unique()
            print(f"Available countries in data: {list(unique_countries)}")
        if 'Crude' in monthly_prod_df.columns:
            unique_crudes = monthly_prod_df['Crude'].unique()
            print(f"Available crudes: {len(unique_crudes)} types (e.g., {list(unique_crudes[:3])})")
        
except Exception as e:
    print(f"Error loading monthly production data: {e}")
    import traceback
    traceback.print_exc()
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

try:
    key_figures_df = pd.read_csv(KEY_FIGURES_CSV)
    key_figures_df.columns = key_figures_df.columns.str.strip()
except Exception as e:
    print(f"Error loading key figures data: {e}")
    import traceback
    traceback.print_exc()
    key_figures_df = pd.DataFrame()

# Create the layout for the Country Profile page
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


def get_port_details_for_hover(port_name):
    """Get port details for hover tooltip from port_df"""
    if port_df.empty or 'Port Name' not in port_df.columns:
        return {}
    
    # Clean port name for matching (case-insensitive)
    port_name_clean = str(port_name).strip().strip('"').lower()
    
    # Find matching port in port_df (case-insensitive matching)
    port_df_clean = port_df.copy()
    port_df_clean['Port Name Clean'] = port_df_clean['Port Name'].astype(str).str.strip().str.strip('"').str.lower()
    
    matching_ports = port_df_clean[port_df_clean['Port Name Clean'] == port_name_clean]
    
    if matching_ports.empty:
        return {}
    
    # Get port details - pivot structure with measure_name and value
    if 'measure_name' in port_df.columns and 'value' in port_df.columns:
        port_details = {}
        for _, row in matching_ports.iterrows():
            measure = str(row.get('measure_name', '')).strip()
            value = row.get('value', '')
            if measure and pd.notna(value):
                value_str = str(value).strip()
                if value_str and value_str.lower() not in ['nan', 'none', 'null', '']:
                    port_details[measure] = value_str
        
        return port_details
    
    return {}


def create_world_map(selected_country=None):
    """Create world map choropleth using Map_data.csv, filtered by selected country"""
    if map_df.empty:
        return create_empty_map()
    
    # Filter by selected country if provided
    # Note: country_long_name columns are already consolidated during data loading
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
        # Include country_long_name and Port if available (already consolidated during data loading)
        port_cols = ['Port Name', 'latitude', 'longitude']
        if 'country_long_name' in filtered_map.columns:
            port_cols.append('country_long_name')
        if 'Port' in filtered_map.columns:
            port_cols.append('Port')
        port_data = filtered_map[port_cols].copy()
        # Filter out rows with empty Port Name (but keep rows with valid coordinates)
        port_data = port_data[port_data['Port Name'].astype(str).str.strip() != '']
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
                hoverinfo='skip',
                marker_line_width=0,  # No border lines
                marker_line_color='rgba(0,0,0,0)'  # Transparent border
            ))
        
        # Add scatter points for each port with orange-red markers and varied symbols
        for _, row in port_data.iterrows():
            port_name = row['Port Name'] if pd.notna(row['Port Name']) else 'Unknown'
            lat = float(row['latitude']) if pd.notna(row['latitude']) else 0
            lon = float(row['longitude']) if pd.notna(row['longitude']) else 0
            
            # Skip invalid coordinates
            if lat == 0 and lon == 0:
                continue
            
            # Build hover text - only show port name (matching original format from image)
            # Format: "Port name: [Port Name]" with port name in bold
            hover_text = f"Port name: <b>{port_name}</b>"
            
            # Determine symbol based on Port value
            # Port 513 = plus/cross symbol, Port 342 = square, others (171) = circle
            port_value = None
            if 'Port' in row and pd.notna(row['Port']):
                try:
                    port_value = int(float(row['Port']))
                except (ValueError, TypeError):
                    port_value = None
            
            if port_value == 513:
                symbol = 'cross'  # Plus/cross symbol (matches image)
            elif port_value == 342:
                symbol = 'square'  # Square symbol (matches image)
            else:
                symbol = 'circle'  # Default circle for 171 and others (matches image)
            fig.add_trace(go.Scattergeo(
                lon=[lon],
                lat=[lat],
                text=port_name,
                mode='markers',
                marker=dict(
                    size=18,
                    color='#fe5000',  # Orange-red for ports
                    opacity=0.9,
                    line=dict(width=0),  # No white border on port markers
                    symbol=symbol
                ),
                name=port_name,
                hovertemplate=hover_text + '<extra></extra>',
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
            projection=dict(
                type='equirectangular',
                scale=1.0  # Default scale
            ),
            bgcolor='rgba(0,0,0,0)',
            coastlinecolor='#d0d0d0',  # Lighter gray for coastlines
            landcolor='#e8e8e8',  # Light gray for land (matching image)
            showocean=True,
            oceancolor='white',  # White ocean color
            showcountries=True,
            countrycolor='#bdbdbd',  # Medium gray for country borders (matching image)
            showlakes=False,
            showrivers=False,
            lonaxis=dict(
                range=[-180, 180],
                showgrid=False
            ),
            lataxis=dict(
                range=[-70, 85],  # Zoom out limit - prevent full world view
                showgrid=False
            ),
            uirevision='fixed-zoom-range'  # Lock the view to prevent zoom beyond range
        ),
        height=None,  # Auto height to fill container
        autosize=True,  # Auto-size to fill container width and height
        margin=dict(l=0, r=0, t=0, b=30),  # Bottom margin for copyright only
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False,
        hovermode='closest',  # Enable hover mode for hover effects
        hoverlabel=dict(
            bgcolor='white',  # White background for hover tooltip
            bordercolor='#999999',  # Light gray border
            font_size=12,
            font_family='Arial, sans-serif',
            font_color='#000000'  # Black text
        ),
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
            oceancolor='white',  # White ocean color
            showcountries=True,
            countrycolor='#bdbdbd',  # Medium gray for country borders (matching image)
            lonaxis_range=[-180, 180],
            lataxis_range=[-70, 85]  # Allow more zoom out but prevent full world view
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
        print(f"DEBUG: monthly_prod_df is empty for country: {country_name}")
        return pd.DataFrame()
    
    # Filter by country name (from Monthly production dynamic title column)
    # The column contains format like "United States Production"
    # So we check if country name is in the title
    if 'Monthly production dynamic title' not in monthly_prod_df.columns:
        print(f"DEBUG: 'Monthly production dynamic title' column not found. Available columns: {list(monthly_prod_df.columns)}")
        return pd.DataFrame()
    
    # Create a pattern to match: "CountryName Production"
    # Handle variations like "United States" matching "United States Production"
    pattern = f"{country_name} Production"
    
    # Try exact match first, then contains
    country_data = monthly_prod_df[
        monthly_prod_df['Monthly production dynamic title'].str.contains(pattern, case=False, na=False)
    ].copy()
    
    if country_data.empty:
        print(f"DEBUG: No data found for country '{country_name}' with pattern '{pattern}'. Available titles: {monthly_prod_df['Monthly production dynamic title'].unique()[:5]}")
        return pd.DataFrame()
    
    print(f"DEBUG: Found {len(country_data)} records for country '{country_name}'")
    
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
    """Return port details for a country; fallback to full dataset when mapping is incomplete."""
    if port_df.empty:
        return pd.DataFrame()
    
    port_df_clean = port_df.copy()
    port_df_clean['Port Name Clean'] = port_df_clean['Port Name'].astype(str).str.strip().str.strip('"')
    port_df_clean['Port Name'] = port_df_clean['Port Name'].astype(str).str.strip().str.strip('"')
    port_df_clean['Coordinates'] = port_df_clean['Coordinates'].astype(str).str.strip()
    
    if not map_df.empty and 'country_long_name' in map_df.columns and 'Port Name' in map_df.columns:
        country_ports = map_df[
            map_df['country_long_name'].astype(str).str.strip() == str(country_name).strip()
        ]['Port Name'].dropna().unique()
        
        if len(country_ports) > 0:
            country_ports_clean = [str(p).strip().strip('"') for p in country_ports]
            port_data = port_df_clean[port_df_clean['Port Name Clean'].isin(country_ports_clean)].copy()
            
            # If mapping captured only a subset (or none), show the full dataset for completeness
            if port_data.empty or port_data['Port Name Clean'].nunique() < port_df_clean['Port Name Clean'].nunique():
                port_data = port_df_clean.copy()
            
            if 'Port Name Clean' in port_data.columns:
                port_data = port_data.drop(columns=['Port Name Clean'])
            return port_data
    
    return port_df_clean.drop(columns=['Port Name Clean'])


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
        # Months order for sorting (chronological)
        months_order = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        
        # Get unique crudes (sort alphabetically, but Total should be after Thunder Horse)
        crudes = sorted([c for c in prod_data['Crude'].unique() if c != 'Total'])
        if 'Total' in prod_data['Crude'].unique():
            # Insert Total right after Thunder Horse
            if 'Thunder Horse' in crudes:
                thunder_horse_idx = crudes.index('Thunder Horse')
                crudes.insert(thunder_horse_idx + 1, 'Total')
            else:
                # If Thunder Horse not found, append at end
                crudes.append('Total')
        
        # Build columns with nested structure (three-level headers: Date -> Year -> Month)
        columns = [{'name': ['', '', 'Crude'], 'id': 'Crude', 'type': 'text', 'sortable': True}]
        
        # Add "Date" parent header
        date_cols = []
        for year in years:
            year_data = prod_data[prod_data['Year'] == year]
            # Sort months chronologically, then reverse to get most recent first (reverse chronological)
            year_months = sorted(year_data['Month'].unique(), 
                               key=lambda x: months_order.index(x) if x in months_order else 999)
            year_months = list(reversed(year_months))  # Reverse to show most recent first
            
            for month in year_months:
                col_id = f"{year}_{month}"
                date_cols.append({
                    'name': ['Date', str(year), month],
                    'id': col_id,
                    'type': 'numeric',
                    'format': {'specifier': ',.0f'},
                    'sortable': False
                })
        
        columns.extend(date_cols)
        
        # Build table data by creating a pivot structure manually
        table_data = []
        for crude in crudes:
            row = {'Crude': crude}
            
            for year in years:
                year_data = prod_data[prod_data['Year'] == year]
                # Sort months chronologically, then reverse to get most recent first (reverse chronological)
                year_months = sorted(year_data['Month'].unique(),
                                   key=lambda x: months_order.index(x) if x in months_order else 999)
                year_months = list(reversed(year_months))  # Reverse to show most recent first
                
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
        # Yearly view - pivot style table with years as columns (descending order)
        prod_data['Year'] = prod_data['Year of Date'].astype(int)
        
        years = sorted(prod_data['Year'].unique(), reverse=True)
        crudes = sorted([c for c in prod_data['Crude'].unique() if c != 'Total'])
        if 'Total' in prod_data['Crude'].unique():
            # Insert Total right after Thunder Horse
            if 'Thunder Horse' in crudes:
                thunder_horse_idx = crudes.index('Thunder Horse')
                crudes.insert(thunder_horse_idx + 1, 'Total')
            else:
                # If Thunder Horse not found, append at end
                crudes.append('Total')
        
        columns = [{'name': ['', 'Crude'], 'id': 'Crude', 'type': 'text', 'sortable': True}]
        for year in years:
            year_id = str(year)
            columns.append({
                'name': ['Date', year_id],
                'id': year_id,
                'type': 'numeric',
                'format': {'specifier': ',.0f'},
                'sortable': False
            })
        
        table_data = []
        for crude in crudes:
            row = {'Crude': crude}
            for year in years:
                value_row = prod_data[
                    (prod_data['Crude'] == crude) &
                    (prod_data['Year'] == year)
                ]
                if not value_row.empty:
                    value = value_row['Avg. Value'].iloc[0]
                    row[str(year)] = int(round(value)) if pd.notna(value) else ''
                else:
                    row[str(year)] = ''
            table_data.append(row)
    
    return dash_table.DataTable(
        data=table_data, 
        columns=columns,
        sort_action='native',
        sort_mode='single',
        sort_by=[{'column_id': 'Crude', 'direction': 'asc'}],
        style_cell={
            'textAlign': 'center',
            'fontFamily': 'Arial, sans-serif',
            'fontSize': '13px',
            'padding': '8px',
            'border': '1px solid #dee2e6',
            'color': '#2c3e50',
            'whiteSpace': 'normal'
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': '600',
            'color': '#2c3e50',
            'border': '1px solid #dee2e6',
            'textAlign': 'center',
            'fontSize': '13px',
            'fontFamily': 'Arial, sans-serif',
            'padding': '8px',
            'pointerEvents': 'none',
            'cursor': 'default'
        },
        style_data={
            'border': '1px solid #dee2e6',
            'backgroundColor': 'white',
            'color': '#2c3e50'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa'
            },
            {
                'if': {'filter_query': '{Crude} = Total'},
                'fontWeight': 'bold',
                'backgroundColor': 'white'
            },
            {
                'if': {'filter_query': '{Crude} = Total', 'row_index': 'odd'},
                'fontWeight': 'bold',
                'backgroundColor': '#f8f9fa'
            }
        ],
        style_cell_conditional=[
            {
                'if': {'column_id': 'Crude'},
                'textAlign': 'left',
                'fontWeight': '500',
                'minWidth': '200px'
            }
        ],
        style_header_conditional=[
            {
                'if': {'column_id': 'Crude'},
                'pointerEvents': 'auto',
                'cursor': 'pointer'
            }
        ],
        page_action='none',
        filter_action='none',
        merge_duplicate_headers=True,
        style_table={
            'overflowX': 'auto',
            'border': '1px solid #dee2e6',
            'borderRadius': '4px',
            'backgroundColor': 'white',
            'width': '100%'
        },
        tooltip_data=[
            {
                col: {
                    'value': (
                        f"Month of Date: {col.split('_')[1]}\n"
                        f"Stream Name: {row.get('Crude', '')}\n"
                        f"Year of Date: {col.split('_')[0]}\n"
                        f"Avg. Value: {row.get(col, '')}"
                    ) if '_' in col else (
                        f"Year: {col}\n"
                        f"Stream Name: {row.get('Crude', '')}\n"
                        f"Avg. Value: {row.get(col, '')}"
                    ),
                    'type': 'text'
                }
                for col in row.keys()
                if col != 'Crude' and row.get(col) not in ['', None]
            }
            for row in table_data
        ],
        tooltip_duration=None,
        css=[
            {
                'selector': '.dash-table-sort',
                'rule': 'display: none !important;'
            },
            {
                'selector': '.column-header--sort',
                'rule': 'display: none !important;'
            },
            {
                'selector': 'th.dash-header[data-dash-column="Crude"] .dash-table-sort',
                'rule': 'display: inline-flex !important;'
            },
            {
                'selector': 'th.dash-header[data-dash-column="Crude"] .column-header--sort',
                'rule': 'display: inline-flex !important;'
            },
            {
                'selector': '.dash-spreadsheet-container td',
                'rule': 'transition: opacity 0.2s ease-in-out, background-color 0.2s ease-in-out;'
            },
            {
                'selector': '.dash-spreadsheet-container:focus-within td:not([data-dash-column="Crude"])',
                'rule': 'opacity: 0.3;'
            },
            {
                'selector': '.dash-spreadsheet-container:focus-within td.dash-cell.focused',
                'rule': 'opacity: 1 !important; background-color: #f7fbff !important; box-shadow: inset 0 0 0 2px #0075A8 !important; font-weight: 600; color: #1f2d3d;'
            },
            {
                'selector': '.dash-spreadsheet-container:focus-within td[data-dash-column="Crude"]',
                'rule': 'opacity: 1 !important;'
            }
        ]
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
        index=['Port Name', 'Coordinates'],
        columns='measure_name',
        values='value',
        aggfunc='first',
        dropna=False
    ).reset_index()
    
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
        coordinates = format_cell_value(row.get('Coordinates', ''))
        if not port_name or not coordinates:
            continue
            
        table_data.append({
            'Port Name': port_name,
            'Coordinates': coordinates,
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
        {'name': 'Berths', 'id': 'Berths', 'type': 'text'},
        {'name': 'Max Draft', 'id': 'Max Draft', 'type': 'text'},
        {'name': 'Max length', 'id': 'Max length', 'type': 'text'},
        {'name': 'Max Loading Rate (bbl/hour)', 'id': 'Max Loading Rate (bbl/hour)', 'type': 'text'},
        {'name': 'Max. Tonnage (dwt)', 'id': 'Max. Tonnage (dwt)', 'type': 'text'},
        {'name': 'Mooring Type', 'id': 'Mooring Type', 'type': 'text'},
        {'name': 'Storage Capacity (million bbl)', 'id': 'Storage Capacity (million bbl)', 'type': 'text'}
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
            },
            {
                'if': {'state': 'active'},
                'backgroundColor': '#fdeedc',
                'border': '1px solid #fe5000'
            },
            {
                'if': {'state': 'selected'},
                'backgroundColor': '#e1f0ff',
                'border': '1px solid #3390ff'
            }
        ],
        page_action='none',
        filter_action='none',
        sort_action='native',
        sort_mode='single',
        style_table={
            'overflowX': 'auto',
            'maxHeight': '220px',
            'overflowY': 'auto'
        },
        fixed_rows={'headers': True}
    )


def quarter_sort_key(quarter_str):
    """Return sortable tuple (year, quarter) from labels like '2024 Q1'"""
    if not isinstance(quarter_str, str):
        return (0, 0)
    parts = quarter_str.strip().split()
    year = 0
    quarter = 0
    if parts:
        try:
            year = int(parts[0])
        except ValueError:
            year = 0
    if len(parts) > 1:
        try:
            quarter = int(parts[1].replace('Q', ''))
        except ValueError:
            quarter = 0
    return (year, quarter)


def format_key_figure_value(measure, value):
    """Format key figures based on measure type"""
    if value in ['', None] or pd.isna(value):
        return ''
    value = float(value)
    if "Production" in measure or "Exports" in measure:
        return f"{value:,.0f}"
    if "Reserves" in measure:
        return f"{value:,.1f}".rstrip('0').rstrip('.')
    if "R/P" in measure:
        # Show up to two decimals but trim trailing zeros
        formatted = f"{value:.2f}"
        return formatted.rstrip('0').rstrip('.')
    return f"{value:,.2f}"


def create_key_figures_table(country_name):
    """Create Key Figures table from Key Figures CSV"""
    if key_figures_df.empty:
        return dash_table.DataTable(
            data=[],
            columns=[],
            style_cell={'textAlign': 'center', 'fontFamily': 'Arial, sans-serif', 'fontSize': '13px'}
        )
    
    df = key_figures_df.copy()
    if 'Measure Names' not in df.columns or 'Quarter of Year' not in df.columns or 'Measure Values' not in df.columns:
        return dash_table.DataTable(data=[], columns=[])
    
    df['Measure Names'] = df['Measure Names'].astype(str).str.strip()
    df['Quarter of Year'] = df['Quarter of Year'].astype(str).str.strip()
    
    pivot_df = df.pivot_table(
        index='Measure Names',
        columns='Quarter of Year',
        values='Measure Values',
        aggfunc='first'
    )
    
    quarters = sorted(pivot_df.columns.tolist(), key=quarter_sort_key, reverse=True)
    pivot_df = pivot_df[quarters]
    measure_order = [
        'Reserves (Billion bbl)',
        "Production ('000 b/d)",
        "Exports ('000 b/d)",
        'R/P Ratio (Year)'
    ]
    measures = [m for m in measure_order if m in pivot_df.index] + [m for m in pivot_df.index if m not in measure_order]
    
    table_data = []
    for measure in measures:
        row = {'Measure': measure}
        for quarter in quarters:
            value = pivot_df.loc[measure, quarter] if quarter in pivot_df.columns else ''
            row[quarter] = format_key_figure_value(measure, value)
        table_data.append(row)
    
    columns = [{'name': ['', 'Measure'], 'id': 'Measure', 'type': 'text'}]
    for quarter in quarters:
        columns.append({
            'name': ['Date', quarter],
            'id': quarter,
            'type': 'text'
        })
    
    return dash_table.DataTable(
        data=table_data,
        columns=columns,
        style_cell={
            'textAlign': 'center',
            'fontFamily': 'Arial, sans-serif',
            'fontSize': '13px',
            'padding': '12px 10px',
            'border': '1px solid #e9ecef',
            'color': '#2c3e50',
            'whiteSpace': 'normal',
            'backgroundColor': 'white'
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': '600',
            'color': '#2c3e50',
            'border': '1px solid #e9ecef',
            'textAlign': 'center',
            'fontSize': '13px',
            'fontFamily': 'Arial, sans-serif',
            'padding': '12px 10px',
            'borderBottom': '2px solid #dee2e6'
        },
        style_data={
            'border': '1px solid #e9ecef',
            'backgroundColor': 'white',
            'color': '#2c3e50'
        },
        style_cell_conditional=[
            {
                'if': {'column_id': 'Measure'},
                'textAlign': 'left',
                'fontWeight': '600',
                'minWidth': '220px',
                'paddingLeft': '15px'
            }
        ],
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa'
            }
        ],
        style_table={
            'overflowX': 'auto',
            'border': 'none',
            'backgroundColor': 'white',
            'width': '100%'
        },
        merge_duplicate_headers=True,
        tooltip_data=[
            {
                col: {
                    'value': f"Quarter: {col}\nMeasure: {row.get('Measure', '')}\nValue: {row.get(col, '')}",
                    'type': 'text'
                }
                for col in row.keys() if col != 'Measure' and row.get(col) not in ['', None]
            }
            for row in table_data
        ],
        tooltip_duration=None
    )


def register_callbacks(dash_app, server):
    """Register all callbacks for Country Profile"""
    
    @dash_app.callback(
        [Output('country-profile-content', 'children'),
         Output('selected-country-profile-store', 'data')],
        [Input('country-select-profile', 'value'),
         Input('world-map-chart', 'clickData'),
         Input('time-period-select', 'value')],
        prevent_initial_call=False
    )
    def update_country_profile(selected_country, click_data, time_period):
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
        
        sections = []
        
        if time_period == 'Yearly':
            sections.append(
                html.Div([
                    html.Div([
                        html.H5(
                            f"{country_name} - Key Figures",
                            style={
                                'color': '#fe5000',
                                'fontWeight': '600',
                                'fontSize': '18px',
                                'marginBottom': '20px'
                            }
                        ),
                        html.Div([
                            create_key_figures_table(country_name)
                        ], style={'background': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
                    ], className='col-md-12', style={'padding': '15px'})
                ], className='row', style={'margin': '30px 0', 'padding': '0 15px'})
            )
        else:
            sections.append(
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
                ], className='row', style={'margin': '30px 0', 'padding': '0 15px'})
            )
        
        sections.append(
            html.Div([
                html.Div([
                    html.H5(
                        f"{country_name} - Loading Port Details",
                        style={
                            'color': '#fe5000',
                            'fontWeight': '600',
                            'fontSize': '18px',
                            'marginBottom': '20px',
                            'textAlign': 'center'
                        }
                    ),
                    html.Div([
                        create_port_details_table(country_name)
                    ], style={'background': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
                ], className='col-md-12', style={'padding': '15px'})
            ], className='row', style={'margin': '30px 0', 'padding': '0 15px'})
        )
        
        return html.Div([
            html.Div([], style={'padding': '20px 30px', 'background': 'white', 'borderBottom': '1px solid #e0e0e0'}),
            *sections
        ]), country_name
    
    @dash_app.callback(
        Output('world-map-chart', 'figure'),
        Input('country-select-profile', 'value'),
        prevent_initial_call=False
    )
    def update_world_map(selected_country):
        """Update world map when country selection changes or page loads"""
        # Use selected country or default
        country = selected_country or default_country
        
        try:
            return create_world_map(country)
        except Exception as e:
            print(f"Error updating world map: {e}")
            import traceback
            traceback.print_exc()
            return create_empty_map()
    
    @dash_app.callback(
        Output('time-period-store', 'data'),
        Input('time-period-select', 'value'),
        prevent_initial_call=False
    )
    def update_time_period_store(time_period):
        """Update time period store"""
        return time_period or 'Monthly'
    
    @dash_app.callback(
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
    
    # Clientside callback to inject CSS for hover effects and limit zoom
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
            /* Add black outline on hover for ALL countries (including selected) */
            /* Target all choropleth paths on hover - show black border */
            #world-map-chart .plotly .choroplethlayer path:hover,
            #world-map-chart .plotly .choroplethlayer path.hover,
            #world-map-chart .plotly .choropleth path:hover,
            #world-map-chart .plotly .choropleth path.hover {
                stroke: black !important;
                stroke-width: 2px !important;
            }
            /* Default: no stroke for choropleth paths (when not hovering) */
            #world-map-chart .plotly .choroplethlayer path {
                stroke: none !important;
                stroke-width: 0 !important;
            }
            #world-map-chart .plotly .choropleth path {
                stroke: none !important;
                stroke-width: 0 !important;
            }
            `;
            document.head.appendChild(style);
            
            // Zoom limit constants
            const ZOOM_OUT_MIN_LAT = -70;   // Maximum zoom out limit (latitude)
            const ZOOM_OUT_MAX_LAT = 85;
            const ZOOM_OUT_MIN_LON = -180;
            const ZOOM_OUT_MAX_LON = 180;
            const MIN_LAT_RANGE = 30;       // Minimum latitude range (degrees) - zoom in limit
            const MIN_LON_RANGE = 60;       // Minimum longitude range (degrees) - zoom in limit
            const MAX_LAT_RANGE = ZOOM_OUT_MAX_LAT - ZOOM_OUT_MIN_LAT;  // Maximum allowed latitude range (155 degrees)
            const MAX_LON_RANGE = ZOOM_OUT_MAX_LON - ZOOM_OUT_MIN_LON;  // Maximum allowed longitude range (360 degrees)
            
            // Limit zoom in and zoom out on map
            function enforceZoomLimits() {
                const mapElement = document.getElementById('world-map-chart');
                if (!mapElement) return;
                
                const plotlyDiv = mapElement.querySelector('.plotly');
                if (!plotlyDiv || !plotlyDiv._fullLayout) return;
                
                const geoLayout = plotlyDiv._fullLayout.geo;
                if (!geoLayout) return;
                
                // Get current ranges
                let currentLatRange = geoLayout.lataxis && geoLayout.lataxis.range ? geoLayout.lataxis.range : null;
                let currentLonRange = geoLayout.lonaxis && geoLayout.lonaxis.range ? geoLayout.lonaxis.range : null;
                
                if (!currentLatRange || !currentLonRange) {
                    // Initialize ranges if not set
                    if (!geoLayout.lataxis) geoLayout.lataxis = {};
                    if (!geoLayout.lonaxis) geoLayout.lonaxis = {};
                    geoLayout.lataxis.range = [ZOOM_OUT_MIN_LAT, ZOOM_OUT_MAX_LAT];
                    geoLayout.lonaxis.range = [ZOOM_OUT_MIN_LON, ZOOM_OUT_MAX_LON];
                    // Apply immediately
                    if (window.Plotly) {
                        try {
                            window.Plotly.relayout(plotlyDiv, {
                                'geo.lataxis.range': [ZOOM_OUT_MIN_LAT, ZOOM_OUT_MAX_LAT],
                                'geo.lonaxis.range': [ZOOM_OUT_MIN_LON, ZOOM_OUT_MAX_LON]
                            });
                        } catch(e) {
                            console.log('Plotly relayout error:', e);
                        }
                    }
                    return;
                }
                
                let needsUpdate = false;
                let newLatRange = [currentLatRange[0], currentLatRange[1]];
                let newLonRange = [currentLonRange[0], currentLonRange[1]];
                
                // Calculate current range sizes
                const currentLatRangeSize = newLatRange[1] - newLatRange[0];
                const currentLonRangeSize = newLonRange[1] - newLonRange[0];
                
                // Enforce zoom OUT limit - check if range exceeds maximum allowed
                if (currentLatRangeSize > MAX_LAT_RANGE) {
                    // Range is too large, reset to maximum zoom out
                    newLatRange = [ZOOM_OUT_MIN_LAT, ZOOM_OUT_MAX_LAT];
                    needsUpdate = true;
                } else {
                    // Enforce boundaries
                    if (newLatRange[0] < ZOOM_OUT_MIN_LAT) {
                        newLatRange[0] = ZOOM_OUT_MIN_LAT;
                        needsUpdate = true;
                    }
                    if (newLatRange[1] > ZOOM_OUT_MAX_LAT) {
                        newLatRange[1] = ZOOM_OUT_MAX_LAT;
                        needsUpdate = true;
                    }
                }
                
                if (currentLonRangeSize > MAX_LON_RANGE) {
                    // Range is too large, reset to maximum zoom out
                    newLonRange = [ZOOM_OUT_MIN_LON, ZOOM_OUT_MAX_LON];
                    needsUpdate = true;
                } else {
                    // Enforce boundaries
                    if (newLonRange[0] < ZOOM_OUT_MIN_LON) {
                        newLonRange[0] = ZOOM_OUT_MIN_LON;
                        needsUpdate = true;
                    }
                    if (newLonRange[1] > ZOOM_OUT_MAX_LON) {
                        newLonRange[1] = ZOOM_OUT_MAX_LON;
                        needsUpdate = true;
                    }
                }
                
                // Recalculate range sizes after boundary enforcement
                const updatedLatRangeSize = newLatRange[1] - newLatRange[0];
                const updatedLonRangeSize = newLonRange[1] - newLonRange[0];
                
                // Enforce zoom IN limit (prevent zooming in too much)
                if (updatedLatRangeSize < MIN_LAT_RANGE) {
                    // Calculate center and expand range
                    const center = (newLatRange[0] + newLatRange[1]) / 2;
                    newLatRange[0] = center - MIN_LAT_RANGE / 2;
                    newLatRange[1] = center + MIN_LAT_RANGE / 2;
                    // Ensure it doesn't exceed zoom out limits
                    if (newLatRange[0] < ZOOM_OUT_MIN_LAT) {
                        newLatRange[0] = ZOOM_OUT_MIN_LAT;
                        newLatRange[1] = ZOOM_OUT_MIN_LAT + MIN_LAT_RANGE;
                    }
                    if (newLatRange[1] > ZOOM_OUT_MAX_LAT) {
                        newLatRange[1] = ZOOM_OUT_MAX_LAT;
                        newLatRange[0] = ZOOM_OUT_MAX_LAT - MIN_LAT_RANGE;
                    }
                    needsUpdate = true;
                }
                
                if (updatedLonRangeSize < MIN_LON_RANGE) {
                    // Calculate center and expand range
                    const center = (newLonRange[0] + newLonRange[1]) / 2;
                    newLonRange[0] = center - MIN_LON_RANGE / 2;
                    newLonRange[1] = center + MIN_LON_RANGE / 2;
                    // Ensure it doesn't exceed zoom out limits
                    if (newLonRange[0] < ZOOM_OUT_MIN_LON) {
                        newLonRange[0] = ZOOM_OUT_MIN_LON;
                        newLonRange[1] = ZOOM_OUT_MIN_LON + MIN_LON_RANGE;
                    }
                    if (newLonRange[1] > ZOOM_OUT_MAX_LON) {
                        newLonRange[1] = ZOOM_OUT_MAX_LON;
                        newLonRange[0] = ZOOM_OUT_MAX_LON - MIN_LON_RANGE;
                    }
                    needsUpdate = true;
                }
                
                // Apply the enforced ranges
                if (needsUpdate) {
                    if (!geoLayout.lataxis) geoLayout.lataxis = {};
                    if (!geoLayout.lonaxis) geoLayout.lonaxis = {};
                    
                    geoLayout.lataxis.range = newLatRange;
                    geoLayout.lonaxis.range = newLonRange;
                    
                    // Redraw the map with enforced limits
                    if (window.Plotly) {
                        try {
                            window.Plotly.relayout(plotlyDiv, {
                                'geo.lataxis.range': newLatRange,
                                'geo.lonaxis.range': newLonRange
                            });
                        } catch(e) {
                            console.log('Plotly relayout error:', e);
                        }
                    }
                }
            }
            
            // Setup zoom limit enforcement
            function setupZoomLimits() {
                const mapElement = document.getElementById('world-map-chart');
                if (!mapElement) {
                    setTimeout(setupZoomLimits, 500);
                    return;
                }
                
                const plotlyDiv = mapElement.querySelector('.plotly');
                if (!plotlyDiv) {
                    setTimeout(setupZoomLimits, 500);
                    return;
                }
                
                // Enforce limits after map loads
                setTimeout(enforceZoomLimits, 1000);
                
                // Listen for ALL relayout events (zoom, pan, etc.) and enforce both zoom limits
                mapElement.on('plotly_relayout', function(eventData) {
                    // Enforce limits on any relayout event (more aggressive)
                    setTimeout(enforceZoomLimits, 10);
                });
                
                // Also intercept wheel events for more immediate control
                const geoDiv = plotlyDiv.querySelector('.geo');
                if (geoDiv) {
                    // Use a more aggressive approach - check before and after
                    let wheelTimeout1, wheelTimeout2;
                    geoDiv.addEventListener('wheel', function(e) {
                        // Clear any pending enforcement
                        clearTimeout(wheelTimeout1);
                        clearTimeout(wheelTimeout2);
                        // Enforce limits immediately and repeatedly during wheel events
                        enforceZoomLimits();
                        wheelTimeout1 = setTimeout(enforceZoomLimits, 50);
                        wheelTimeout2 = setTimeout(enforceZoomLimits, 150);
                    }, { passive: true });
                }
                
                // Also check periodically to ensure limits are maintained
                setInterval(enforceZoomLimits, 500);
            }
            
            // Start setup
            setupZoomLimits();
            
            return window.dash_clientside.no_update;
        }
        """,
        Output('css-injection-placeholder', 'children'),
        Input('css-injection-placeholder', 'id'),
        prevent_initial_call=False
    )


# ------------------------------------------------------------------------------
# DASH APP CREATION
# ------------------------------------------------------------------------------
def create_country_profile_dashboard(server, url_base_pathname="/dash/country-profile/"):
    """Create the Country Profile dashboard"""
    dash_app = create_dash_app(server, url_base_pathname)
    dash_app.layout = create_layout(server)
    register_callbacks(dash_app, server)
    return dash_app

