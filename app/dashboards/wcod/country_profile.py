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
from datetime import datetime
from core.data_helpers import execute_query
from config import Config

# # CSV paths
# DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'Country_Profile')
# MAP_CSV = os.path.join(DATA_DIR, 'Map_data.csv')
# MONTHLY_PRODUCTION_CSV = os.path.join(DATA_DIR, 'Monthly_Production.csv')
# PORT_DETAIL_CSV = os.path.join(DATA_DIR, 'Port-Detail_data.csv')
# KEY_FIGURES_CSV = os.path.join(DATA_DIR, 'Key Figures_data.csv')

# Initialize empty dataframes - will be loaded lazily when needed
map_df = pd.DataFrame()
monthly_prod_df = pd.DataFrame()
port_df = pd.DataFrame() # Initialize port_df
key_figures_df = pd.DataFrame() # Initialize key_figures_df
country_list = []
default_country = None

# Mapbox access token (falls back to config default token if env not set)
MAPBOX_ACCESS_TOKEN = Config.MAPBOX_ACCESS_TOKEN
# Set Plotly-wide token for px maps
if MAPBOX_ACCESS_TOKEN:
    px.set_mapbox_access_token(MAPBOX_ACCESS_TOKEN)

def load_map_data():
    """Load map data from database - called only when needed"""
    global map_df
    if not map_df.empty:
        return map_df
    
    try:
        # Query map data from database
        map_query = """
        WITH original_query AS (
            SELECT
                A."country_id",
                A."country_long_name",
                CASE
                    WHEN A."country_long_name" = 'Abu Dhabi' THEN 'https://www.energyintel.com/wcod/country-profile/abu-dhabi'
                    WHEN A."country_long_name" = 'Algeria' THEN 'https://www.energyintel.com/wcod/country-profile/algeria'
                    WHEN A."country_long_name" = 'Angola' THEN 'https://www.energyintel.com/wcod/country-profile/angola'
                    WHEN A."country_long_name" = 'Argentina' THEN 'https://www.energyintel.com/wcod/country-profile/argentina'
                    WHEN A."country_long_name" = 'Australia' THEN 'https://www.energyintel.com/wcod/country-profile/australia'
                    WHEN A."country_long_name" = 'Azerbaijan' THEN 'https://www.energyintel.com/wcod/country-profile/azerbaijan'
                    WHEN A."country_long_name" = 'Brazil' THEN 'https://www.energyintel.com/wcod/country-profile/brazil'
                    WHEN A."country_long_name" = 'Brunei' THEN 'https://www.energyintel.com/wcod/country-profile/brunei'
                    WHEN A."country_long_name" = 'Canada' THEN 'https://www.energyintel.com/wcod/country-profile/canada'
                    WHEN A."country_long_name" = 'Chad' THEN 'https://www.energyintel.com/wcod/country-profile/chad'
                    WHEN A."country_long_name" = 'China' THEN 'https://www.energyintel.com/wcod/country-profile/china'
                    WHEN A."country_long_name" = 'Colombia' THEN 'https://www.energyintel.com/wcod/country-profile/colombia'
                    WHEN A."country_long_name" = 'Congo (Brazzaville)' THEN 'https://www.energyintel.com/wcod/country-profile/republic-of-the-congo'
                    WHEN A."country_long_name" = 'Denmark' THEN 'https://www.energyintel.com/wcod/country-profile/denmark'
                    WHEN A."country_long_name" = 'Dubai' THEN 'https://www.energyintel.com/wcod/country-profile/dubai'
                    WHEN A."country_long_name" = 'Ecuador' THEN 'https://www.energyintel.com/wcod/country-profile/ecuador'
                    WHEN A."country_long_name" = 'Egypt' THEN 'https://www.energyintel.com/wcod/country-profile/egypt'
                    WHEN A."country_long_name" = 'Equatorial Guinea' THEN 'https://www.energyintel.com/wcod/country-profile/equatorial-guinea'
                    WHEN A."country_long_name" = 'Gabon' THEN 'https://www.energyintel.com/wcod/country-profile/gabon'
                    WHEN A."country_long_name" = 'Ghana' THEN 'https://www.energyintel.com/wcod/country-profile/ghana'
                    WHEN A."country_long_name" = 'Guyana' THEN 'https://www.energyintel.com/wcod/country-profile/guyana'
                    WHEN A."country_long_name" = 'Indonesia' THEN 'https://www.energyintel.com/wcod/country-profile/indonesia'
                    WHEN A."country_long_name" = 'Iran' THEN 'https://www.energyintel.com/wcod/country-profile/iran'
                    WHEN A."country_long_name" = 'Iraq' THEN 'https://www.energyintel.com/wcod/country-profile/iraq'
                    WHEN A."country_long_name" = 'Kazakhstan' THEN 'https://www.energyintel.com/wcod/country-profile/kazakhstan'
                    WHEN A."country_long_name" = 'Kuwait' THEN 'https://www.energyintel.com/wcod/country-profile/kuwait'
                    WHEN A."country_long_name" = 'Libya' THEN 'https://www.energyintel.com/wcod/country-profile/libya'
                    WHEN A."country_long_name" = 'Malaysia' THEN 'https://www.energyintel.com/wcod/country-profile/malaysia'
                    WHEN A."country_long_name" = 'Mexico' THEN 'https://www.energyintel.com/wcod/country-profile/mexico'
                    WHEN A."country_long_name" = 'Neutral Zone' THEN 'https://www.energyintel.com/wcod/country-profile/neutral-zone'
                    WHEN A."country_long_name" = 'Nigeria' THEN 'https://www.energyintel.com/wcod/country-profile/nigeria'
                    WHEN A."country_long_name" = 'Norway' THEN 'https://www.energyintel.com/wcod/country-profile/norway'
                    WHEN A."country_long_name" = 'Oman' THEN 'https://www.energyintel.com/wcod/country-profile/oman'
                    WHEN A."country_long_name" = 'Papua New Guinea' THEN 'https://www.energyintel.com/wcod/country-profile/papua-new-guinea'
                    WHEN A."country_long_name" = 'Qatar' THEN 'https://www.energyintel.com/wcod/country-profile/qatar'
                    WHEN A."country_long_name" = 'Russia' THEN 'https://www.energyintel.com/wcod/country-profile/russia'
                    WHEN A."country_long_name" = 'Saudi Arabia' THEN 'https://www.energyintel.com/wcod/country-profile/saudi-arabia'
                    WHEN A."country_long_name" = 'South Sudan' THEN 'https://www.energyintel.com/wcod/country-profile/south-sudan'
                    WHEN A."country_long_name" = 'Sudan' THEN 'https://www.energyintel.com/wcod/country-profile/sudan'
                    WHEN A."country_long_name" = 'Syria' THEN 'https://www.energyintel.com/wcod/country-profile/syria'
                    WHEN A."country_long_name" = 'Turkmenistan' THEN 'https://www.energyintel.com/wcod/country-profile/turkmenistan'
                    WHEN A."country_long_name" = 'United Kingdom' THEN 'https://www.energyintel.com/wcod/country-profile/united-kingdom'
                    WHEN A."country_long_name" = 'United States' THEN 'https://www.energyintel.com/wcod/country-profile/united-states'
                    WHEN A."country_long_name" = 'Venezuela' THEN 'https://www.energyintel.com/wcod/country-profile/venezuela'
                    WHEN A."country_long_name" = 'Vietnam' THEN 'https://www.energyintel.com/wcod/country-profile/vietnam'
                    WHEN A."country_long_name" = 'Yemen' THEN 'https://www.energyintel.com/wcod/country-profile/yemen'
                    ELSE NULL
                END AS profile_url,
                P."port_name",
                P."latitude",
                P."longitude",
                P."coordinates",
                P."measure_name",
                P."value",
                A."yr",
                A."output",
                A."exports",
                A."reserves"
            FROM fact_wcod_country A
            LEFT JOIN fact_wcod_port P
                ON P."country_id" = A."country_id"
            WHERE A."country_long_name" IS NOT NULL
            AND A."to_be_deleted" IS NULL
        ),
        port_counts AS (
            SELECT
                country_id,
                country_long_name,
                port_name,
                COUNT(*) AS port_value
            FROM original_query
            GROUP BY
                country_id,
                country_long_name,
                port_name
        )
        SELECT
            o.country_id,
            o.country_long_name,
            o.profile_url,
            o.port_name,
            o.latitude,
            o.longitude,
            o.coordinates,
            o.measure_name,
            o.value,
            o.yr,
            o.output,
            o.exports,
            o.reserves,
            pc.port_value
        FROM original_query o
        LEFT JOIN port_counts pc
            ON  o.country_id = pc.country_id
            AND o.port_name  = pc.port_name
        WHERE o.latitude IS NOT NULL
          AND o.longitude IS NOT NULL;
        """
        
        # Execute query and convert to DataFrame
        map_results = execute_query(map_query)
        # print(f"DEBUG: load_map_data: map_results length: {len(map_results)}") # Temporarily commented out to prevent TypeError

        map_df = pd.DataFrame(map_results)
        # print(f"DEBUG: load_map_data: map_df after creation - shape: {map_df.shape}, columns: {map_df.columns.tolist()}")
        # print(f"DEBUG: load_map_data: map_df head:\n{map_df.head()}")
        
        if not map_df.empty:
            # Clean and standardize column names
            map_df.columns = map_df.columns.str.strip()
            
            # Rename port_name to Port Name for compatibility with existing code
            if 'port_name' in map_df.columns:
                map_df['Port Name'] = map_df['port_name'].astype(str).str.strip()
            
            # Ensure country_long_name is properly formatted
            if 'country_long_name' in map_df.columns:
                map_df['country_long_name'] = map_df['country_long_name'].astype(str).str.strip()
            
            print(f"Loaded map data with {len(map_df)} records from database")
        else:
            map_df = pd.DataFrame()
            print("Warning: No map data loaded from database")
            
    except Exception as e:
        # print(f"ERROR: load_map_data failed: {e}") # Keep this for critical errors
        # import traceback # Keep this for critical errors
        # traceback.print_exc() # Keep this for critical errors
        # Silently handle missing database tables - app can work with CSV data
        map_df = pd.DataFrame()
    
    return map_df

def load_production_data():
    """Load production data from database - called only when needed"""
    global monthly_prod_df, country_list, default_country
    
    if not monthly_prod_df.empty:
        return monthly_prod_df, country_list, default_country
    
    try:
        # Query production data from database
        query = """
        SELECT 
            "t_wcod_monthly_stream_production"."added_by" AS added_by,
            "t_wcod_monthly_stream_production"."commodity" AS commodity,
            "t_wcod_monthly_stream_production"."commodity_id" AS commodity_id,
            "t_wcod_monthly_stream_production"."country" AS country,
            (CASE 
                WHEN "country" = 'Abu Dhabi' THEN 'https://www.energyintel.com/wcod/country-profile/abu-dhabi'
                WHEN "country" = 'Algeria' THEN 'https://www.energyintel.com/wcod/country-profile/algeria'
                WHEN "country" = 'Angola' THEN 'https://www.energyintel.com/wcod/country-profile/angola'
                WHEN "country" = 'Argentina' THEN 'https://www.energyintel.com/wcod/country-profile/argentina'
                WHEN "country" = 'Australia' THEN 'https://www.energyintel.com/wcod/country-profile/australia'
                WHEN "country" = 'Azerbaijan' THEN 'https://www.energyintel.com/wcod/country-profile/azerbaijan'
                WHEN "country" = 'Brazil' THEN 'https://www.energyintel.com/wcod/country-profile/brazil'
                WHEN "country" = 'Brunei' THEN 'https://www.energyintel.com/wcod/country-profile/brunei'
                WHEN "country" = 'Canada' THEN 'https://www.energyintel.com/wcod/country-profile/canada'
                WHEN "country" = 'Chad' THEN 'https://www.energyintel.com/wcod/country-profile/chad'
                WHEN "country" = 'China' THEN 'https://www.energyintel.com/wcod/country-profile/china'
                WHEN "country" = 'Colombia' THEN 'https://www.energyintel.com/wcod/country-profile/colombia'
                WHEN "country" = 'Congo (Brazzaville)' THEN 'https://www.energyintel.com/wcod/country-profile/republic-of-the-congo'
                WHEN "country" = 'Denmark' THEN 'https://www.energyintel.com/wcod/country-profile/denmark'
                WHEN "country" = 'Dubai' THEN 'https://www.energyintel.com/wcod/country-profile/dubai'
                WHEN "country" = 'Ecuador' THEN 'https://www.energyintel.com/wcod/country-profile/ecuador'
                WHEN "country" = 'Egypt' THEN 'https://www.energyintel.com/wcod/country-profile/egypt'
                WHEN "country" = 'Equatorial Guinea' THEN 'https://www.energyintel.com/wcod/country-profile/equatorial-guinea'
                WHEN "country" = 'Gabon' THEN 'https://www.energyintel.com/wcod/country-profile/gabon'
                WHEN "country" = 'Ghana' THEN 'https://www.energyintel.com/wcod/country-profile/ghana'
                WHEN "country" = 'Guyana' THEN 'https://www.energyintel.com/wcod/country-profile/guyana'
                WHEN "country" = 'Indonesia' THEN 'https://www.energyintel.com/wcod/country-profile/indonesia'
                WHEN "country" = 'Iran' THEN 'https://www.energyintel.com/wcod/country-profile/iran'
                WHEN "country" = 'Iraq' THEN 'https://www.energyintel.com/wcod/country-profile/iraq'
                WHEN "country" = 'Kazakhstan' THEN 'https://www.energyintel.com/wcod/country-profile/kazakhstan'
                WHEN "country" = 'Kuwait' THEN 'https://www.energyintel.com/wcod/country-profile/kuwait'
                WHEN "country" = 'Libya' THEN 'https://www.energyintel.com/wcod/country-profile/libya'
                WHEN "country" = 'Malaysia' THEN 'https://www.energyintel.com/wcod/country-profile/malaysia'
                WHEN "country" = 'Mexico' THEN 'https://www.energyintel.com/wcod/country-profile/mexico'
                WHEN "country" = 'Neutral Zone' THEN 'https://www.energyintel.com/wcod/country-profile/neutral-zone'
                WHEN "country" = 'Nigeria' THEN 'https://www.energyintel.com/wcod/country-profile/nigeria'
                WHEN "country" = 'Norway' THEN 'https://www.energyintel.com/wcod/country-profile/norway'
                WHEN "country" = 'Oman' THEN 'https://www.energyintel.com/wcod/country-profile/oman'
                WHEN "country" = 'Papua New Guinea' THEN 'https://www.energyintel.com/wcod/country-profile/papua-new-guinea'
                WHEN "country" = 'Qatar' THEN 'https://www.energyintel.com/wcod/country-profile/qatar'
                WHEN "country" = 'Russia' THEN 'https://www.energyintel.com/wcod/country-profile/russia'
                WHEN "country" = 'Saudi Arabia' THEN 'https://www.energyintel.com/wcod/country-profile/saudi-arabia'
                WHEN "country" = 'South Sudan' THEN 'https://www.energyintel.com/wcod/country-profile/south-sudan'
                WHEN "country" = 'Sudan' THEN 'https://www.energyintel.com/wcod/country-profile/sudan'
                WHEN "country" = 'Syria' THEN 'https://www.energyintel.com/wcod/country-profile/syria'
                WHEN "country" = 'Turkmenistan' THEN 'https://www.energyintel.com/wcod/country-profile/turkmenistan'
                WHEN "country" = 'United Kingdom' THEN 'https://www.energyintel.com/wcod/country-profile/united-kingdom'
                WHEN "country" = 'United States' THEN 'https://www.energyintel.com/wcod/country-profile/united-states'
                WHEN "country" = 'Venezuela' THEN 'https://www.energyintel.com/wcod/country-profile/venezuela'
                WHEN "country" = 'Vietnam' THEN 'https://www.energyintel.com/wcod/country-profile/vietnam'
                WHEN "country" = 'Yemen' THEN 'https://www.energyintel.com/wcod/country-profile/yemen'
                ELSE NULL
            END) AS profile_url,
            "t_wcod_monthly_stream_production"."country_id" AS country_id,
            "t_wcod_monthly_stream_production"."date" AS date,
            "t_wcod_monthly_stream_production"."date_added" AS date_added,
            "t_wcod_monthly_stream_production"."date_modified" AS date_modified,
            "t_wcod_monthly_stream_production"."is_forecast" AS is_forecast,
            "t_wcod_monthly_stream_production"."modified_by" AS modified_by,
            "t_wcod_monthly_stream_production"."record_id" AS record_id,
            "t_wcod_monthly_stream_production"."stream_name" AS stream_name,
            "t_wcod_monthly_stream_production"."unit" AS unit,
            "t_wcod_monthly_stream_production"."value" AS value
        FROM "dev"."t_wcod_monthly_stream_production"
        """
        
        # Execute query and convert to DataFrame
        results = execute_query(query)
        monthly_prod_df = pd.DataFrame(results)
        
        if not monthly_prod_df.empty:
            # Extract year and month from date field
            monthly_prod_df['date'] = pd.to_datetime(monthly_prod_df['date'], errors='coerce')
            monthly_prod_df['Year of Date'] = monthly_prod_df['date'].dt.year
            monthly_prod_df['Month of Date'] = monthly_prod_df['date'].dt.strftime('%B')  # Full month name
            
            # Map columns to match expected format
            monthly_prod_df['Crude'] = monthly_prod_df['stream_name']
            monthly_prod_df['Monthly production dynamic title'] = monthly_prod_df['country'] + ' Production'
            monthly_prod_df['Avg. Value'] = pd.to_numeric(monthly_prod_df['value'], errors='coerce')
            
            # Get unique countries for dropdown from database
            country_list = sorted(monthly_prod_df['country'].dropna().unique().tolist())
            country_list = [str(c).strip() for c in country_list if c and str(c).strip() and str(c).strip() != 'nan']
            default_country = 'United States' if 'United States' in country_list else (country_list[0] if country_list else None)
            
            print(f"Loaded {len(monthly_prod_df)} production records from database")
            print(f"Available countries: {len(country_list)} countries")
            print(f"Available crudes: {monthly_prod_df['stream_name'].nunique()} types")
        else:
            monthly_prod_df = pd.DataFrame()
            print("Warning: No production data loaded from database")
            
    except Exception as e:
        # Silently handle missing database tables - app can work with CSV data
        monthly_prod_df = pd.DataFrame()
        country_list = []
        default_country = None
    
    return monthly_prod_df, country_list, default_country

def load_port_data():
    """Load port data from database - called only when needed"""
    global port_df
    if not port_df.empty:
        return port_df
    
    try:
        # Query port data from database
        port_query = """
        SELECT
            P."port_id",
            P."port_name",
            P."country_id",
            P."latitude",
            P."longitude",
            P."coordinates",
            P."measure_name",
            P."value"
        FROM fact_wcod_port P
        """
        
        # Execute query and convert to DataFrame
        port_results = execute_query(port_query)
        port_df = pd.DataFrame(port_results)
        
        if not port_df.empty:
            # Clean and standardize column names
            port_df.columns = port_df.columns.str.strip()
            
            # Ensure port_name is properly formatted
            if 'port_name' in port_df.columns:
                port_df['Port Name'] = port_df['port_name'].astype(str).str.strip()
            
            print(f"Loaded port data with {len(port_df)} records from database")
        else:
            port_df = pd.DataFrame()
            print("Warning: No port data loaded from database")
            
    except Exception as e:
        # Silently handle missing database tables
        port_df = pd.DataFrame()
    
    return port_df

def load_key_figures_data():
    """Load key figures data from database - called only when needed"""
    global key_figures_df
    if not key_figures_df.empty:
        return key_figures_df
    
    try:
        # Query key figures data from database
        key_figures_query = """
        SELECT
            K."measure_names",
            K."quarter_of_year",
            K."measure_values",
            K."country_id",
            C."country_long_name"
        FROM fact_wcod_key_figures K
        LEFT JOIN dim_wcod_country C ON K."country_id" = C."country_id"
        """
        
        # Execute query and convert to DataFrame
        key_figures_results = execute_query(key_figures_query)
        key_figures_df = pd.DataFrame(key_figures_results)
        
        if not key_figures_df.empty:
            # Clean and standardize column names
            key_figures_df.columns = key_figures_df.columns.str.strip()
            
            # Ensure measure_names and quarter_of_year are properly formatted
            if 'measure_names' in key_figures_df.columns:
                key_figures_df['Measure Names'] = key_figures_df['measure_names'].astype(str).str.strip()
            if 'quarter_of_year' in key_figures_df.columns:
                key_figures_df['Quarter of Year'] = key_figures_df['quarter_of_year'].astype(str).str.strip()
            
            print(f"Loaded key figures data with {len(key_figures_df)} records from database")
        else:
            key_figures_df = pd.DataFrame()
            print("Warning: No key figures data loaded from database")
            
    except Exception as e:
        # Silently handle missing database tables
        key_figures_df = pd.DataFrame()
    
    return key_figures_df

def _ensure_production_data_loaded():
    """Ensure production data is loaded - wrapper for load_production_data()"""
    return load_production_data()

# --- CSV data loading (uncommented) ---
# try:
#     # Assuming PORT_DETAIL_CSV is defined globally or passed
#     # For now, let's assume it's defined elsewhere or we need to add a placeholder
#     # For this fix, let's use the DB query instead of CSV if possible
#     # If not using DB, PORT_DETAIL_CSV needs to be defined from context
#     port_df = pd.DataFrame() # Placeholder for now if no DB loading for port_df yet
#     # TODO: Implement database loading for port_df instead of CSV
# except Exception as e:
#     print(f"Error loading port data (from CSV initially): {e}")
#     import traceback
#     traceback.print_exc()
#     port_df = pd.DataFrame()

# try:
#     # Assuming KEY_FIGURES_CSV is defined globally or passed
#     # For now, let's assume it's defined elsewhere or we need to add a placeholder
#     # For this fix, let's use the DB query instead of CSV if possible
#     # If not using DB, KEY_FIGURES_CSV needs to be defined from context
#     key_figures_df = pd.DataFrame() # Placeholder for now if no DB loading for key_figures_df yet
#     # TODO: Implement database loading for key_figures_df instead of CSV
# except Exception as e:
#     print(f"Error loading key figures data (from CSV initially): {e}")
#     import traceback
#     traceback.print_exc()
#     key_figures_df = pd.DataFrame()

# Create the layout for the Country Profile page
def create_layout():
    """Create the Country Profile layout with filters and world map"""
    # Note: Data will be loaded lazily when page is accessed via callbacks
    # Create country options from map data (may be empty initially)
    country_options = [{'label': country, 'value': country} for country in country_list] if country_list else []
    
    # Initialize map with empty map (data will load when page is accessed)
    initial_map = create_empty_map()

    # Initial profile URL
    initial_profile_url = "#"
    

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
                    # html.Div([
                    #     html.Div([
                    #         html.Button('🔍', style={'width': '32px', 'height': '32px', 'border': '1px solid #d0d0d0', 'background': 'white', 'cursor': 'pointer', 'borderRadius': '2px', 'marginBottom': '4px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'fontSize': '14px'}),
                    #         html.Button('📋', style={'width': '32px', 'height': '32px', 'border': '1px solid #d0d0d0', 'background': 'white', 'cursor': 'pointer', 'borderRadius': '2px', 'marginBottom': '4px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'fontSize': '14px'}),
                    #         html.Button('+', style={'width': '32px', 'height': '32px', 'border': '1px solid #d0d0d0', 'background': 'white', 'cursor': 'pointer', 'borderRadius': '2px', 'marginBottom': '4px', 'fontSize': '18px', 'fontWeight': 'bold', 'lineHeight': '1'}),
                    #         html.Button('−', style={'width': '32px', 'height': '32px', 'border': '1px solid #d0d0d0', 'background': 'white', 'cursor': 'pointer', 'borderRadius': '2px', 'marginBottom': '4px', 'fontSize': '18px', 'fontWeight': 'bold', 'lineHeight': '1'}),
                    #         html.Button('⌂', style={'width': '32px', 'height': '32px', 'border': '1px solid #d0d0d0', 'background': 'white', 'cursor': 'pointer', 'borderRadius': '2px', 'marginBottom': '4px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'fontSize': '14px'}),
                    #         html.Button('▶', style={'width': '32px', 'height': '32px', 'border': '1px solid #d0d0d0', 'background': 'white', 'cursor': 'pointer', 'borderRadius': '2px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'fontSize': '12px'})
                    #     ], style={'display': 'flex', 'flexDirection': 'column', 'padding': '4px', 'background': 'white', 'border': '1px solid #d0d0d0', 'borderRadius': '4px', 'boxShadow': '0 1px 3px rgba(0,0,0,0.1)'})
                    # ], className='map-controls', style={
                    #     'position': 'absolute',
                    #     'left': '10px',
                    #     'top': '10px',
                    #     'opacity': '1',
                    #     'zIndex': '1000'
                    # })
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
    load_port_data() # Ensure port data is loaded
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
    """Create world map choropleth using database map data, filtered by selected country"""

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

    if map_df.empty:
        return create_empty_map()
    
    # Filter by selected country if provided
    # Note: country_long_name columns are already consolidated during data loading
    if selected_country and 'country_long_name' in map_df.columns:
        print(f"DEBUG: Selected country for map: {selected_country}")
        # Filter by country name (handle case sensitivity and string conversion)
        filtered_map = map_df[map_df['country_long_name'].astype(str).str.strip() == str(selected_country).strip()].copy()
    else:
        print("DEBUG: No country selected for map, showing all countries.")
        filtered_map = map_df.copy()
    
    if filtered_map.empty:
        print(f"DEBUG: filtered_map is empty for {selected_country}. Returning empty map.")
        return create_empty_map()
    
    # Ensure required columns exist
    required_cols = ['Port Name', 'latitude', 'longitude']
    if not all(col in filtered_map.columns for col in required_cols):
        print(f"DEBUG: Missing required columns in filtered_map: {required_cols}. Returning empty map.")
        return create_empty_map()
    
    # Group by country to get port counts and locations
    if selected_country:
        # For selected country, show individual ports and highlight the country
        # Include country_long_name and Port if available (already consolidated during data loading)
        port_cols = ['Port Name', 'latitude', 'longitude', 'port_value'] # Added 'port_value' here
        if 'country_long_name' in filtered_map.columns:
            port_cols.append('country_long_name')
        # Port column may not exist in database, so check before adding
        if 'Port' in filtered_map.columns:
            port_cols.append('Port')
        # Add profile_url to port_cols to enable customdata for hovertemplate
        if 'profile_url' in filtered_map.columns:
            port_cols.append('profile_url')
        port_data = filtered_map[port_cols].copy()

        # Force latitude and longitude to numeric and drop NaNs
        port_data['latitude'] = pd.to_numeric(port_data['latitude'], errors='coerce')
        port_data['longitude'] = pd.to_numeric(port_data['longitude'], errors='coerce')
        port_data = port_data.dropna(subset=['latitude', 'longitude'])
        
        # Normalize port_value as per ChatGPT's suggestion (applied once to the DataFrame)
        # port_data['port_value'] = port_data['port_value'].fillna(1)
        # port_data.loc[port_data['port_value'] <= 0, 'port_value'] = 1
        # port_data['port_value'] = port_data['port_value'] * 4   # Force visible size

        # Filter out rows with empty Port Name
        port_data = port_data[
            (port_data['Port Name'].astype(str).str.strip() != '') &
            (port_data['Port Name'].astype(str).str.strip().str.lower() != 'nan')
        ].copy()
            
        if port_data.empty:
            return create_empty_map()
        
        fig = go.Figure()
        
        # Get ISO code for selected country
        country_iso = country_to_iso.get(selected_country, None)
        
        if country_iso:
            # Add Choroplethmapbox (country fill) first
            fig.add_trace(go.Choroplethmapbox(
                locations=[country_iso],
                z=[1],
                colorscale=[[0, 'rgba(142, 153, 208, 1)'], [1, 'rgba(142, 153, 208, 1)']],
                showscale=False,
                featureidkey="properties.iso_a3",
                hoverinfo='text',
                text=[selected_country], 
                marker_line_width=0,
                marker_line_color='rgba(0,0,0,0)'
            ))
        
            # Bucket ports by symbol to ensure reliable rendering per symbol type
            ports_by_symbol = {}
            for _, port_row in port_data.iterrows():
                port_value = port_row['port_value']
                # Map symbol and a modest size so markers don't overwhelm the map
                # Use built-in Plotly symbols (no sprite) for reliability
                if port_value == 171:
                    symbol, marker_size = 'circle', 14
                elif port_value == 513:
                    symbol, marker_size = '+', 14   # plus symbol
                elif port_value == 342:
                    symbol, marker_size = 'square', 14
                else:
                    symbol, marker_size = 'circle', 14

                bucket = ports_by_symbol.setdefault(symbol, {"lat": [], "lon": [], "name": [], "size": [], "custom": []})
                bucket["lat"].append(port_row['latitude'])
                bucket["lon"].append(port_row['longitude'])
                bucket["name"].append(port_row['Port Name'])
                bucket["size"].append(marker_size)
                profile_url = f"/wcod/country-profile?country={port_row['country_long_name']}"
                bucket["custom"].append([profile_url])

            if ports_by_symbol:
                # Add one trace per symbol to avoid per-point symbol issues
                for symbol_key, data_bucket in ports_by_symbol.items():
                    fig.add_trace(go.Scattermapbox(
                        lat=data_bucket["lat"],
                        lon=data_bucket["lon"],
                        mode='markers',
                        marker=dict(
                            size=data_bucket["size"],
                            color='#fe5000',
                            opacity=0.9,
                            symbol='circle'
                        ),
                        text=data_bucket["name"],
                        customdata=data_bucket["custom"],
                        hovertemplate="""
                            <b>Port Name:</b> %{text}
                            <extra></extra>
                        """,
                        showlegend=False
                    ))
            # If no ports, do nothing
        
        # Add country name label for the selected country (if selected_country is not None)
        # Ensure this trace is only added when selected_country is present
        if selected_country:
            map_center_lat = filtered_map['latitude'].mean() if not filtered_map.empty else 24.0
            map_center_lon = filtered_map['longitude'].mean() if not filtered_map.empty else 45.0
            fig.add_trace(go.Scattermapbox(
                lat=[map_center_lat],
                lon=[map_center_lon],
                mode='text',
                text=[selected_country],
                textfont=dict(size=12, color="black"), # Removed 'weight="bold"'
                textposition="middle center",
                hoverinfo='skip',
                showlegend=False
            ))

        title_text = f"{selected_country} Production"
        map_zoom = 4 # Zoom in for a specific country
        map_center = dict(lat=filtered_map['latitude'].mean(), lon=filtered_map['longitude'].mean()) if not filtered_map.empty else dict(lat=24.0, lon=45.0)
    else:
        # For all countries, show a choropleth map of all countries
        # Use px.choropleth_mapbox for simpler all-country view
        all_countries_df = map_df[['country_long_name']].drop_duplicates().dropna().copy()
        all_countries_df['iso_alpha'] = all_countries_df['country_long_name'].map(country_to_iso)
        all_countries_df = all_countries_df.dropna(subset=['iso_alpha'])
        
        fig = px.choropleth_mapbox(all_countries_df,
                            locations="iso_alpha",
                            color="country_long_name", # Use country name for color to differentiate countries
                            color_continuous_scale="Viridis",
                            featureidkey="properties.iso_a3",
                            mapbox_style="carto-positron", # Default style for all countries
                            zoom=1, center={"lat": 24.0, "lon": 45.0},
                            opacity=0.5,
                            hover_name="country_long_name" # Display country name on hover
                        )
        
        title_text = 'World Crude Oil Ports by Country'
        map_zoom = 2.8 # World view zoom adjusted as per suggestion
        map_center = dict(lat=24.0, lon=45.0)

        # Add country name labels to the world map
        country_centroids = map_df.groupby('country_long_name').agg({
            'latitude': 'mean',
            'longitude': 'mean'
        }).reset_index()

        fig.add_trace(go.Scattermapbox(
            lat=country_centroids['latitude'],
            lon=country_centroids['longitude'],
            mode='text',
            text=country_centroids['country_long_name'],
            textfont=dict(size=10, color="black"),
            textposition="middle center",
            hoverinfo='skip',
            showlegend=False
        ))
        
    mapbox_layout = dict(
        style="carto-positron",  # Prefer custom sprite style, fallback inside helper
        center=map_center, # Dynamic center
        zoom=map_zoom, # Dynamic zoom for world view
        # Enable interactive controls
        bearing=0,
        pitch=0
    )
    if MAPBOX_ACCESS_TOKEN:
        mapbox_layout["accesstoken"] = MAPBOX_ACCESS_TOKEN

    fig.update_layout(
        title=None,
        mapbox=mapbox_layout,
        height=None,  # Auto height to fill container
        width=None,   # Auto width to fill container
        autosize=True,  # Auto-size to fill container width and height
        margin=dict(l=0, r=0, t=0, b=30),
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False,
        hovermode='closest',
        hoverlabel=dict(
            bgcolor='white',
            font_size=12,
            font_family="Arial"
        )
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
        mapbox=dict(
            style="carto-positron",
            center=dict(lat=24.0, lon=45.0),
            zoom=1 # Consistent zoom with world view
        ),
        height=700,
        width=700,  # Square aspect ratio
        margin=dict(l=0, r=0, t=60, b=30),
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
    """Get production data for a country from database"""
    monthly_prod_df, _, _ = _ensure_production_data_loaded()
    if monthly_prod_df.empty:
        print(f"DEBUG: monthly_prod_df is empty for country: {country_name}")
        return pd.DataFrame()
    
    # Filter by country name directly from database
    if 'country' not in monthly_prod_df.columns:
        print(f"DEBUG: 'country' column not found. Available columns: {list(monthly_prod_df.columns)}")
        return pd.DataFrame()
    
    # Filter by exact country match
    country_data = monthly_prod_df[
        monthly_prod_df['country'].astype(str).str.strip() == str(country_name).strip()
    ].copy()
    
    if country_data.empty:
        print(f"DEBUG: No data found for country '{country_name}'. Available countries: {monthly_prod_df['country'].unique()[:5]}")
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
    """Get port-specific details from global map_df, filtered by country"""
    if map_df.empty:
        return pd.DataFrame()

    # Filter by country name
    country_data = map_df[map_df['country_long_name'].astype(str).str.strip() == str(country_name).strip()].copy()

    if country_data.empty:
        return pd.DataFrame()

    # Ensure required columns exist, including 'port_value'
    required_cols = ['port_name', 'coordinates', 'measure_name', 'value', 'port_value']
    if not all(col in country_data.columns for col in required_cols):
        print(f"DEBUG: Missing required columns in country_data for port details: {required_cols}. Available: {country_data.columns.tolist()}")
        return pd.DataFrame()
    
    # Clean and prepare the data
    port_data = country_data[required_cols].copy()
    port_data['Port Name'] = port_data['port_name'].astype(str).str.strip()
    port_data['Coordinates'] = port_data['coordinates'].astype(str).str.strip()
    
    # Filter out rows with empty port names or coordinates
    port_data = port_data[
        (port_data['Port Name'].str.strip() != '') & 
        (port_data['Port Name'].str.strip().str.lower() != 'nan') &
        (port_data['Coordinates'].str.strip() != '') &
        (port_data['Coordinates'].str.strip().str.lower() != 'nan')
    ].copy()
    
    return port_data


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
        columns = [{
            'name': ['', 'Crude'],
            'id': 'Crude',
            'type': 'text',
            'sortable': True
        }]
        
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
                    'name': [str(year), month],
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
        
        columns = [{
            'name': ['', 'Crude'],
            'id': 'Crude',
            'type': 'text',
            'sortable': True
        }]
        for year in years:
            year_id = str(year)
            columns.append({
                'name': ['Year', year_id],
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
    
    production_table = dash_table.DataTable(
        id='production-table',
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
            }
        ]
    )
    
    return html.Div([
        production_table,
        html.Div(
            id='production-table-dropdown-container',
            className='production-table-dropdown-container'
        )
    ])


def create_port_details_table(country_name):
    """Create port details table from database map data"""
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
    
    # Map measure_name from database to display column names
    measure_name_mapping = {
        'berths': 'Berths',
        'max_draft': 'Max Draft',
        'max_length': 'Max length',
        'max_loading_rate': 'Max Loading Rate (bbl/hour)',
        'max_tonnage': 'Max. Tonnage (dwt)',
        'mooring_type': 'Mooring Type',
        'storage_cap': 'Storage Capacity (million bbl)'
    }
    
    # Clean and prepare values
    port_data['value'] = port_data['value'].astype(str).str.strip()
    port_data['value'] = port_data['value'].replace(['', 'nan', 'NaN', 'None', 'null', 'NULL'], pd.NA)
    
    # Remove duplicates before pivoting (same port and measure_name)
    # Group by Port Name only, not by Coordinates
    port_data = port_data.drop_duplicates(subset=['Port Name', 'measure_name'], keep='first')
    
    # Get the first coordinates for each port (in case a port has multiple coordinates)
    port_coords = port_data.groupby('Port Name')['Coordinates'].first().reset_index()
    port_coords.columns = ['Port Name', 'Coordinates']
    
    # Pivot the data to show ports as rows and measures as columns
    # Group by Port Name only - each port appears once with all measures as columns
    pivot_port = port_data.pivot_table(
        index='Port Name',
        columns='measure_name',
        values='value',
        aggfunc='first',
        dropna=False
    )
    
    # Flatten column names if MultiIndex (pivot_table sometimes creates MultiIndex)
    if isinstance(pivot_port.columns, pd.MultiIndex):
        pivot_port.columns = pivot_port.columns.droplevel(0)
    
    # Reset index to make Port Name a regular column
    pivot_port = pivot_port.reset_index()
    
    # Merge with coordinates to get the first coordinates for each port
    pivot_port = pivot_port.merge(port_coords, on='Port Name', how='left')
    
    # Remove any duplicate rows (shouldn't happen after pivot, but just in case)
    pivot_port = pivot_port.drop_duplicates(subset=['Port Name'], keep='first')
    
    # Helper function to format cell values (handle NaN, None, empty strings)
    def format_cell_value(val):
        if pd.isna(val) or val is None:
            return ''
        val_str = str(val).strip()
        if val_str == '' or val_str.lower() in ['nan', 'none', 'null', 'null']:
            return ''
        return val_str
    
    # Prepare table data - map measure_name to display names
    table_data = []
    seen_ports = set()  # Track unique ports
    
    for _, row in pivot_port.iterrows():
        port_name = format_cell_value(row.get('Port Name', ''))
        coordinates = format_cell_value(row.get('Coordinates', ''))
        
        if not port_name:
            continue
        
        # Skip if we've already processed this port
        if port_name in seen_ports:
            continue
        
        seen_ports.add(port_name)
        
        # Map each measure_name to its display column name in the correct order
        # Access columns directly by their measure_name values
        row_data = {
            'Port Name': port_name,
            'Coordinates': format_cell_value(coordinates),
            'Port Value': format_cell_value(row.get('port_value', '')),
            'Berths': format_cell_value(row.get('berths', '')),
            'Max Draft': format_cell_value(row.get('max_draft', '')),
            'Max length': format_cell_value(row.get('max_length', '')),
            'Max Loading Rate (bbl/hour)': format_cell_value(row.get('max_loading_rate', '')),
            'Max. Tonnage (dwt)': format_cell_value(row.get('max_tonnage', '')),
            'Mooring Type': format_cell_value(row.get('mooring_type', '')),
            'Storage Capacity (million bbl)': format_cell_value(row.get('storage_cap', ''))
        }
        
        table_data.append(row_data)
    
    columns = [
        {'name': 'Port Name', 'id': 'Port Name', 'type': 'text'},
        {'name': 'Coordinates', 'id': 'Coordinates', 'type': 'text'},
        {'name': 'Port Value', 'id': 'Port Value', 'type': 'numeric'},
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


def create_key_figures_table(country_name, time_period='Monthly'):
    """Create Key Figures table from database (Yearly) or CSV (Monthly)"""
    
    if time_period == 'Yearly':
        # Use database data from map_df query
        load_map_data()
        if map_df.empty:
            return dash_table.DataTable(
                data=[],
                columns=[],
                style_cell={'textAlign': 'center', 'fontFamily': 'Arial, sans-serif', 'fontSize': '13px'}
            )
        
        # Filter map data by country
        if 'country_long_name' not in map_df.columns:
            print(f"DEBUG: 'country_long_name' column not found in map_df. Available columns: {list(map_df.columns)}")
            return dash_table.DataTable(data=[], columns=[])
        
        # Check required columns
        required_cols = ['yr', 'output', 'exports', 'reserves']
        if not all(col in map_df.columns for col in required_cols):
            print(f"DEBUG: Missing required columns. Available: {list(map_df.columns)}")
            return dash_table.DataTable(data=[], columns=[])
        
        # Filter by country name (case-insensitive, handle whitespace)
        country_data = map_df[
            map_df['country_long_name'].astype(str).str.strip().str.lower() == str(country_name).strip().lower()
        ].copy()
        
        if country_data.empty:
            # Try to see what countries are available
            available_countries = map_df['country_long_name'].dropna().unique()[:10]
            print(f"DEBUG: No data found for country '{country_name}' in map_df. Available countries (sample): {list(available_countries)}")
            return dash_table.DataTable(data=[], columns=[])
        
        print(f"DEBUG: Found {len(country_data)} rows for country '{country_name}'")
        
        # Filter out rows where yr is NULL (we need at least yr to create the table)
        # Also ensure we have at least one of output, exports, or reserves (country data exists)
        country_data = country_data[
            (country_data['yr'].notna()) & 
            ((country_data['output'].notna()) | (country_data['exports'].notna()) | (country_data['reserves'].notna()))
        ].copy()
        
        if country_data.empty:
            print(f"DEBUG: No data with valid 'yr' and country metrics for country '{country_name}'")
            return dash_table.DataTable(data=[], columns=[])
        
        # Extract year from date field (yr is a date like '2024-01-01')
        # Convert to datetime if it's not already
        country_data['yr'] = pd.to_datetime(country_data['yr'], errors='coerce')
        country_data = country_data.dropna(subset=['yr'])
        
        # Extract year as integer
        country_data['year'] = country_data['yr'].dt.year
        
        # Remove duplicates and prepare data - keep first occurrence for each year
        # This handles cases where FULL JOIN creates multiple rows per year (one per port)
        # Group by year and take first non-null values for output, exports, reserves
        country_data = country_data.sort_values('year', ascending=False)
        
        # For each year, take the first row with non-null values
        yearly_data = []
        for year_val in country_data['year'].unique():
            year_rows = country_data[country_data['year'] == year_val]
            # Get first row with at least one non-null value
            first_row = year_rows.iloc[0]
            yearly_data.append({
                'year': int(year_val),
                'output': first_row['output'] if pd.notna(first_row['output']) else None,
                'exports': first_row['exports'] if pd.notna(first_row['exports']) else None,
                'reserves': first_row['reserves'] if pd.notna(first_row['reserves']) else None
            })
        
        if not yearly_data:
            print(f"DEBUG: No yearly data extracted for country '{country_name}'")
            return dash_table.DataTable(data=[], columns=[])
        
        # Convert to DataFrame for easier handling - use a new variable name to avoid confusion
        yearly_df = pd.DataFrame(yearly_data)
        yearly_df = yearly_df.sort_values('year', ascending=False)
        
        # Get unique years
        years = yearly_df['year'].unique().tolist()
        years = sorted([int(y) for y in years if pd.notna(y)], reverse=True)
        
        print(f"DEBUG: Found {len(years)} unique years for country '{country_name}': {years[:10]}")
        
        if not years:
            print(f"DEBUG: No years found after processing for country '{country_name}'")
            return dash_table.DataTable(data=[], columns=[])
        
        # Prepare table data
        table_data = []
        
        # Helper function to format values
        def format_value(val, measure_type):
            if pd.isna(val) or val is None:
                return ''
            try:
                val_float = float(val)
                if measure_type == 'reserves':
                    return f"{val_float:,.0f}"
                elif measure_type in ['production', 'exports']:
                    return f"{val_float:,.0f}"
                elif measure_type == 'rp_ratio':
                    # Round to nearest integer (no decimal places)
                    rounded = round(val_float)
                    return f"{rounded:,.0f}"
                return f"{val_float:,.2f}"
            except (ValueError, TypeError):
                return ''
        
        # Create rows for each measure
        measures = [
            ('Reserves (Billion bbl)', 'reserves'),
            ("Production ('000 b/d)", 'production'),
            ("Exports ('000 b/d)", 'exports'),
            ('R/P Ratio (Year)', 'rp_ratio')
        ]
        
        for measure_name, measure_type in measures:
            row = {'Measure': measure_name}
            
            for year in years:
                # Get data for this year
                year_row = yearly_df[yearly_df['year'] == year]
                if year_row.empty:
                    row[str(year)] = ''
                    continue
                
                year_row_data = year_row.iloc[0]
                
                if measure_type == 'reserves':
                    value = year_row_data['reserves'] if pd.notna(year_row_data['reserves']) else None
                elif measure_type == 'production':
                    value = year_row_data['output'] if pd.notna(year_row_data['output']) else None
                elif measure_type == 'exports':
                    value = year_row_data['exports'] if pd.notna(year_row_data['exports']) else None
                elif measure_type == 'rp_ratio':
                    # Calculate R/P ratio: (reserves * 1000000) / (365 * output)
                    reserves = year_row_data['reserves'] if pd.notna(year_row_data['reserves']) else None
                    output = year_row_data['output'] if pd.notna(year_row_data['output']) else None
                    
                    if reserves is not None and output is not None and output != 0:
                        try:
                            value = (float(reserves) * 1000000) / (365 * float(output))
                        except (ValueError, TypeError, ZeroDivisionError):
                            value = None
                    else:
                        value = None
                else:
                    value = None
                
                row[str(year)] = format_value(value, measure_type)
            
            table_data.append(row)
        
        print(f"DEBUG: Created {len(table_data)} rows for Key Figures table")
        
        if not table_data:
            return dash_table.DataTable(
                data=[],
                columns=[],
                style_cell={'textAlign': 'center', 'fontFamily': 'Arial, sans-serif', 'fontSize': '13px'}
            )
        
        # Create columns
        columns = [{'name': ['', 'Measure'], 'id': 'Measure', 'type': 'text'}]
        for year in years:
            columns.append({
                'name': ['Date', str(year)],
                'id': str(year),
                'type': 'text'
            })
        
        # Return DataTable for yearly view (shared return statement is below)
        # Continue to shared return statement
    
    else:
        # Use database data for Monthly view
        load_key_figures_data()
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


def get_profile_url_for_country(country):
    """Return the profile URL for a given country using DB data when possible."""
    if not country:
        return "#"

    # Prefer URL from map query (fact_wcod_country) because it is authoritative
    if not map_df.empty and 'country_long_name' in map_df.columns and 'profile_url' in map_df.columns:
        subset = map_df[
            map_df['country_long_name'].astype(str).str.strip().str.lower() == str(country).strip().lower()
        ]
        if not subset.empty:
            url = subset['profile_url'].dropna().astype(str).str.strip()
            if not url.empty and url.iloc[0]:
                return url.iloc[0]

    # Fallback to monthly production query (if available)
    monthly_prod_df, _, _ = _ensure_production_data_loaded()
    if not monthly_prod_df.empty and 'profile_url' in monthly_prod_df.columns:
        subset = monthly_prod_df[
            monthly_prod_df['country'].astype(str).str.strip().str.lower() == str(country).strip().lower()
        ]
        if not subset.empty:
            url = subset['profile_url'].dropna().astype(str).str.strip()
            if not url.empty and url.iloc[0]:
                return url.iloc[0]

    # Last resort: construct URL slug manually
    return f"https://www.energyintel.com/wcod/country-profile/{str(country).strip().lower().replace(' ', '-')}"


def register_callbacks(dash_app, server):
    """Register all callbacks for Country Profile"""
    
    @dash_app.callback(
        [Output('country-profile-content', 'children'),
         Output('selected-country-profile-store', 'data')],
        [Input('country-select-profile', 'value'),
         Input('world-map-chart', 'clickData'),
         Input('time-period-select', 'value'),
         Input('current-submenu', 'data')],
        prevent_initial_call=False
    )
    def update_country_profile(selected_country, click_data, time_period, current_submenu):
        """Update country profile content based on selection"""
        # Only load data when this page is active
        if current_submenu != 'country-profile':
            return html.Div("Please select a country", style={'padding': '20px', 'textAlign': 'center'}), None
        
        # Ensure data is loaded
        load_map_data()
        _ensure_production_data_loaded()
        
        # Determine which country is selected
        country_name = selected_country or default_country
        
        # Use default time period if not provided
        if not time_period:
            time_period = 'Monthly'
        
        # If map was clicked, we could update selection (for now, use dropdown value)
        if not country_name:
            return html.Div("Please select a country", style={'padding': '20px', 'textAlign': 'center'}), None
        
        # Create profile URL
        profile_url = get_profile_url_for_country(country_name)
        
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
                            create_key_figures_table(country_name, time_period)
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
        [Input('country-select-profile', 'value'),
         Input('current-submenu', 'data')],
        prevent_initial_call=False
    )
    def update_world_map(selected_country, current_submenu):
        """Update world map when country selection changes or page loads"""
        if current_submenu != 'country-profile':
            # print(f"DEBUG: update_world_map: current_submenu is {current_submenu}, returning empty map.")
            return create_empty_map()
        
        # Ensure map data is loaded
        load_map_data()
        # print(f"DEBUG: update_world_map: map_df loaded with {len(map_df)} records.")
        # print(f"DEBUG: update_world_map: map_df columns: {map_df.columns.tolist()}")

        # Ensure port data is loaded (if not already in map_df)
        # Note: port_df is now loaded within map_df query for direct use
        # If port_df is a separate global, ensure it's loaded here if needed
        global port_df
        if port_df.empty:
            load_port_data() # Assuming load_port_data() populates global port_df
        # print(f"DEBUG: update_world_map: port_df loaded with {len(port_df)} records.")
        # print(f"DEBUG: update_world_map: port_df columns: {port_df.columns.tolist()}")
        
        # Use selected country or default
        country = selected_country or default_country
        # print(f"DEBUG: update_world_map: Selected country for map is '{country}'.")
        
        try:
            return create_world_map(country)
        except Exception as e:
            print(f"Error updating world map: {e}")
            import traceback
            traceback.print_exc()
            return create_empty_map()
    
    @dash_app.callback(
        Output('time-period-store', 'data'),
        [Input('time-period-select', 'value'),
         Input('current-submenu', 'data')],
        prevent_initial_call=False
    )
    def update_time_period_store(time_period, current_submenu):
        """Update time period store"""
        if current_submenu != 'country-profile':
            return 'Monthly'
        return time_period or 'Monthly'
    
    @dash_app.callback(
        Output('profile-link', 'href'),
        [Input('selected-country-profile-store', 'data'),
         Input('country-select-profile', 'value'),
         Input('current-submenu', 'data')],
        prevent_initial_call=False
    )
    def update_profile_link(selected_country_from_store, selected_country_dropdown, current_submenu):
        """Update profile link when country changes"""
        if current_submenu != 'country-profile':
            return "#"
        
        # Ensure map data is loaded to get profile URLs
        load_map_data()
        
        country = selected_country_from_store or selected_country_dropdown or default_country
        return get_profile_url_for_country(country)
    
    @dash_app.callback(
        [Output('country-select-profile', 'options'),
         Output('country-select-profile', 'value')],
        Input('current-submenu', 'data'),
        prevent_initial_call=False
    )
    def update_country_dropdown(current_submenu):
        """Update country dropdown options when page is accessed and data is loaded"""
        if current_submenu != 'country-profile':
            return [], None
        
        # Ensure data is loaded
        load_map_data()
        _ensure_production_data_loaded()
        
        # Create country options from loaded data
        country_options = [{'label': country, 'value': country} for country in country_list] if country_list else []
        
        # Set default value if not already set
        default_val = default_country if default_country else (country_list[0] if country_list else None)
        
        return country_options, default_val
    
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
            #production-table .dash-spreadsheet-container {
                cursor: pointer;
            }
            #production-table .dash-spreadsheet-container.production-selection-active td {
                opacity: 0.18;
                transition: opacity 0.2s ease-in-out;
            }
            #production-table .dash-spreadsheet-container.production-selection-active td.production-cell-selected,
            #production-table .dash-spreadsheet-container.production-selection-active td[data-dash-column="Crude"] {
                opacity: 1 !important;
            }
            #production-table .dash-spreadsheet-container td.production-cell-selected {
                background-color: #f7fbff !important;
                box-shadow: inset 0 0 0 2px #0075A8 !important;
                font-weight: 600;
                color: #1f2d3d !important;
            }
            #production-table .dash-spreadsheet-container td.production-row-selected {
                opacity: 1 !important;
                background-color: #e6f1ff !important;
                color: #102a43 !important;
            }
            #production-table .dash-spreadsheet-container td.production-row-label-selected {
                font-weight: 600;
                color: #102a43 !important;
            }
            #production-table .dash-spreadsheet-container td.production-row-label-selected::before {
                content: '';
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background-color: #fe5000;
                margin-right: 8px;
                position: relative;
                top: -1px;
                box-shadow: 0 0 0 2px #ffffff;
            }
            #production-table th.dash-header {
                overflow: visible !important;
            }
            #production-table th.dash-header[data-dash-column="Crude"] {
                position: relative;
                padding-right: 28px;
            }
            #production-table .crude-header-toggle {
                position: absolute;
                top: 50%;
                right: 6px;
                transform: translateY(-50%);
                width: 22px;
                height: 22px;
                border: none;
                background: transparent;
                color: #5f6368;
                border-radius: 3px;
                cursor: pointer;
                font-size: 13px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.2s ease, color 0.2s ease;
                z-index: 12;
            }
            #production-table .crude-header-toggle:hover,
            #production-table .crude-header-toggle.active {
                background: rgba(95, 99, 104, 0.18);
                color: #1f2d3d;
            }
            #production-table .crude-sort-menu {
                position: absolute;
                top: calc(100% + 6px);
                left: -1px;
                min-width: 170px;
                background: #ffffff;
                border: 1px solid #d9dde3;
                border-radius: 3px;
                box-shadow: 0 10px 28px rgba(31, 45, 61, 0.25);
                padding: 4px 0;
                display: none;
                z-index: 1000;
            }
            #production-table .crude-sort-menu.open {
                display: block;
            }
            #production-table .crude-sort-item {
                width: 100%;
                padding: 6px 14px;
                text-align: left;
                background: transparent;
                border: none;
                color: #1f2d3d;
                font-size: 13px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 10px;
            }
            #production-table .crude-sort-item:hover {
                background: rgba(95, 99, 104, 0.12);
            }
            #production-table .crude-sort-item.has-submenu {
                position: relative;
            }
            #production-table .crude-sort-item .submenu-arrow {
                font-size: 11px;
                color: #5f6368;
            }
            #production-table .crude-sort-submenu {
                position: absolute;
                top: -4px;
                left: 100%;
                margin-left: 2px;
                min-width: 160px;
                background: #ffffff;
                border: 1px solid #d9dde3;
                border-radius: 3px;
                box-shadow: 0 8px 18px rgba(31, 45, 61, 0.2);
                padding: 4px 0;
                display: none;
            }
            #production-table .crude-sort-item.has-submenu:hover .crude-sort-submenu {
                display: block;
            }
            #production-table .crude-sort-submenu .crude-sort-item {
                padding: 6px 12px;
            }
            #production-table .crude-sort-submenu .crude-sort-item.aggregator-info {
                cursor: default;
                font-style: italic;
                color: #5f6368;
                justify-content: flex-start;
                gap: 6px;
                pointer-events: none;
            }
            #production-table .crude-row-hidden {
                display: none !important;
            }
            #production-table .dash-table-tooltip {
                background-color: #ffffff !important;
                color: #1f2933 !important;
                border: 1px solid #d5d9dd !important;
                box-shadow: 0 4px 12px rgba(31, 45, 61, 0.15) !important;
                padding: 10px 12px !important;
                border-radius: 6px !important;
                font-family: 'Arial', 'Helvetica', sans-serif !important;
                font-size: 12px !important;
                line-height: 1.5 !important;
                white-space: pre-wrap !important;
                max-width: 220px !important;
            }
            #production-table .dash-table-tooltip span {
                display: block;
            }
            #world-map-chart .plotly .choroplethlayer {
                z-index: 10 !important;
                pointer-events: auto !important;
            }
            #world-map-chart .plotly .scatterlayer,
            #world-map-chart .plotly .scattergeo {
                z-index: 20 !important;
            }
            #world-map-chart .plotly .choroplethlayer path {
                pointer-events: auto !important;
                stroke: none !important;
                stroke-width: 0 !important;
                transition: stroke 0.15s ease-in-out, stroke-width 0.15s ease-in-out;
            }
            #world-map-chart .plotly .choroplethlayer path:hover {
                stroke: black !important;
                stroke-width: 1px !important;
            }
            /* Hide country border when port is being hovered */
            #world-map-chart.port-hovering .plotly .choroplethlayer path:hover {
                stroke: none !important;
                stroke-width: 0 !important;
                pointer-events: none !important;
            }
            #world-map-chart .plotly .scattergeo .points path {
                pointer-events: auto !important;
                cursor: pointer;
            }
            #world-map-chart .plotly .scattergeo .points path:hover {
                stroke: none !important;
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
            
            function setupPortHoverEffects() {
                const mapElement = document.getElementById('world-map-chart');
                if (!mapElement) {
                    setTimeout(setupPortHoverEffects, 500);
                    return;
                }
                const plotlyDiv = mapElement.querySelector('.plotly');
                if (!plotlyDiv) {
                    setTimeout(setupPortHoverEffects, 500);
                    return;
                }
                
                function bindPortListeners() {
                    const portMarkers = plotlyDiv.querySelectorAll('.scattergeo .points path');
                    if (!portMarkers || !portMarkers.length) {
                        return;
                    }
                    
                    portMarkers.forEach(function(marker) {
                        if (marker.dataset.portHoverBound === 'true') {
                            return;
                        }
                        marker.dataset.portHoverBound = 'true';
                        
                        const addHoverClass = function() {
                            mapElement.classList.add('port-hovering');
                        };
                        const removeHoverClass = function() {
                            mapElement.classList.remove('port-hovering');
                        };
                        
                        marker.addEventListener('mouseenter', addHoverClass);
                        marker.addEventListener('mouseleave', removeHoverClass);
                        marker.addEventListener('focus', addHoverClass);
                        marker.addEventListener('blur', removeHoverClass);
                        marker.addEventListener('touchstart', addHoverClass, { passive: true });
                        marker.addEventListener('touchend', removeHoverClass);
                        marker.addEventListener('touchcancel', removeHoverClass);
                    });
                }
                
                bindPortListeners();
                
                if (mapElement._portHoverObserver) {
                    mapElement._portHoverObserver.disconnect();
                }
                
                const observer = new MutationObserver(function() {
                    bindPortListeners();
                });
                observer.observe(plotlyDiv, { childList: true, subtree: true });
                mapElement._portHoverObserver = observer;
                
                mapElement.addEventListener('mouseleave', function() {
                    mapElement.classList.remove('port-hovering');
                });
            }
            
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
                // Use a polling mechanism since Plotly event system may not be available in Dash
                let lastLayout = null;
                const checkLayoutChange = function() {
                    if (plotlyDiv && plotlyDiv._fullLayout) {
                        const currentLayout = JSON.stringify(plotlyDiv._fullLayout.geo);
                        if (currentLayout !== lastLayout) {
                            lastLayout = currentLayout;
                            enforceZoomLimits();
                        }
                    }
                };
                
                // Poll for layout changes
                const layoutInterval = setInterval(checkLayoutChange, 100);
                
                // Also check on mouse events
                if (plotlyDiv) {
                    plotlyDiv.addEventListener('mousedown', function() {
                        setTimeout(enforceZoomLimits, 10);
                    });
                    plotlyDiv.addEventListener('wheel', function() {
                        setTimeout(enforceZoomLimits, 10);
                    }, { passive: true });
                }
                
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
            
            function initProductionTableEnhancements() {
                if (window.productionTableEnhancerInitialized) {
                    return;
                }
                window.productionTableEnhancerInitialized = true;
                
                function clearSelection(spreadsheet) {
                    if (!spreadsheet) return;
                    spreadsheet.classList.remove('production-selection-active');
                    spreadsheet.dataset.selectedKey = '';
                    spreadsheet.querySelectorAll('.production-cell-selected').forEach(function(cell) {
                        cell.classList.remove('production-cell-selected');
                    });
                    spreadsheet.querySelectorAll('.production-row-selected').forEach(function(cell) {
                        cell.classList.remove('production-row-selected');
                    });
                    spreadsheet.querySelectorAll('.production-row-label-selected').forEach(function(cell) {
                        cell.classList.remove('production-row-label-selected');
                    });
                }
                
                function closeAllCrudeMenus(eventTarget, forceAll) {
                    document.querySelectorAll('#production-table .crude-sort-menu.open').forEach(function(menu) {
                        const toggle = menu._toggleButton;
                        if (forceAll || (!menu.contains(eventTarget) && (!toggle || !toggle.contains(eventTarget)))) {
                            menu.classList.remove('open');
                            if (toggle) {
                                toggle.classList.remove('active');
                            }
                        }
                    });
                }
                
                function captureOriginalOrder(spreadsheet) {
                    if (spreadsheet.dataset.originalCrudeOrder) {
                        return;
                    }
                    const order = Array.from(spreadsheet.querySelectorAll('td[data-dash-column="Crude"]')).map(function(cell) {
                        return {
                            rowKey: cell.getAttribute('data-dash-row'),
                            label: cell.textContent.trim()
                        };
                    });
                    spreadsheet.dataset.originalCrudeOrder = JSON.stringify(order);
                }
                
                function sortRows(spreadsheet, comparator) {
                    const tbody = spreadsheet.querySelector('tbody');
                    if (!tbody) {
                        return;
                    }
                    const rows = Array.from(tbody.querySelectorAll('tr[data-dash-row]'));
                    if (!rows.length) {
                        return;
                    }
                    rows.sort(comparator);
                    const fragment = document.createDocumentFragment();
                    rows.forEach(function(row) {
                        fragment.appendChild(row);
                    });
                    tbody.appendChild(fragment);
                }
                
                function getRowLabel(row) {
                    const labelCell = row.querySelector('td[data-dash-column="Crude"]');
                    return labelCell ? labelCell.textContent.trim() : '';
                }
                
                function getRowLatestValue(row) {
                    const cells = Array.from(row.querySelectorAll('td'));
                    for (let i = 0; i < cells.length; i += 1) {
                        const colId = cells[i].getAttribute('data-dash-column');
                        if (colId && colId !== 'Crude') {
                            const numeric = parseFloat((cells[i].textContent || '').replace(/,/g, ''));
                            if (!isNaN(numeric)) {
                                return numeric;
                            }
                        }
                    }
                    return -Infinity;
                }
                
                function applyCrudeSort(spreadsheet, mode) {
                    const originalData = spreadsheet.dataset.originalCrudeOrder ? JSON.parse(spreadsheet.dataset.originalCrudeOrder) : [];
                    if (mode === 'data-source' && originalData.length) {
                        const indexMap = {};
                        originalData.forEach(function(item, idx) {
                            indexMap[item.rowKey] = idx;
                        });
                        sortRows(spreadsheet, function(a, b) {
                            const aKey = a.getAttribute('data-dash-row');
                            const bKey = b.getAttribute('data-dash-row');
                            return (indexMap[aKey] || 0) - (indexMap[bKey] || 0);
                        });
                        return;
                    }
                    
                    if (mode === 'alphabetic' || mode === 'field-crude') {
                        sortRows(spreadsheet, function(a, b) {
                            return getRowLabel(a).localeCompare(getRowLabel(b));
                        });
                        return;
                    }
                    
                    if (mode === 'field-date' || mode === 'nested') {
                        sortRows(spreadsheet, function(a, b) {
                            return getRowLatestValue(b) - getRowLatestValue(a);
                        });
                        return;
                    }
                }
                
                function setupCrudeSortMenu(tableElement, spreadsheet) {
                    if (!tableElement || !spreadsheet) {
                        return;
                    }
                    const headerCells = tableElement.querySelectorAll('th.dash-header[data-dash-column="Crude"]');
                    const headerCell = headerCells.length ? headerCells[headerCells.length - 1] : null;
                    if (!headerCell || headerCell.dataset.crudeMenuAttached === 'true') {
                        return;
                    }
                    headerCell.dataset.crudeMenuAttached = 'true';
                    captureOriginalOrder(spreadsheet);
                    
                    const toggle = document.createElement('button');
                    toggle.type = 'button';
                    toggle.className = 'crude-header-toggle';
                    toggle.setAttribute('aria-label', 'Sort options');
                    toggle.innerHTML = '&#9662;';
                    
                    const menu = document.createElement('div');
                    menu.className = 'crude-sort-menu';
                    menu._toggleButton = toggle;
                    
                    function createMenuButton(label, sortKey) {
                        const btn = document.createElement('button');
                        btn.type = 'button';
                        btn.className = 'crude-sort-item';
                        btn.textContent = label;
                        if (sortKey) {
                            btn.setAttribute('data-sort', sortKey);
                        }
                        return btn;
                    }
                    
                    function createSubmenuInfo(label) {
                        const info = document.createElement('div');
                        info.className = 'crude-sort-item aggregator-info';
                        info.textContent = label;
                        return info;
                    }
                    
                    const dataSourceBtn = createMenuButton('Data source order', 'data-source');
                    const alphabeticBtn = createMenuButton('Alphabetic', 'alphabetic');
                    
                    const nestedBtn = createMenuButton('Nested', 'nested');
                    nestedBtn.classList.add('has-submenu');
                    const nestedArrow = document.createElement('span');
                    nestedArrow.className = 'submenu-arrow';
                    nestedArrow.innerHTML = '&#9656;';
                    nestedBtn.appendChild(nestedArrow);
                    const nestedSubmenu = document.createElement('div');
                    nestedSubmenu.className = 'crude-sort-submenu';
                    nestedSubmenu.appendChild(createSubmenuInfo('AVG(Value)'));
                    nestedBtn.appendChild(nestedSubmenu);
                    
                    const fieldWrapper = document.createElement('div');
                    fieldWrapper.className = 'crude-sort-item has-submenu';
                    const fieldText = document.createElement('span');
                    fieldText.textContent = 'Field';
                    const submenuArrow = document.createElement('span');
                    submenuArrow.className = 'submenu-arrow';
                    submenuArrow.innerHTML = '&#9656;';
                    fieldWrapper.appendChild(fieldText);
                    fieldWrapper.appendChild(submenuArrow);
                    
                    const fieldSubmenu = document.createElement('div');
                    fieldSubmenu.className = 'crude-sort-submenu';
                    fieldSubmenu.appendChild(createSubmenuInfo('AVG(Value)'));
                    fieldWrapper.appendChild(fieldSubmenu);
                    
                    menu.appendChild(dataSourceBtn);
                    menu.appendChild(alphabeticBtn);
                    menu.appendChild(fieldWrapper);
                    menu.appendChild(nestedBtn);
                    
                    menu.addEventListener('click', function(event) {
                        event.stopPropagation();
                    });
                    
                    headerCell.appendChild(toggle);
                    headerCell.appendChild(menu);
                    
                    toggle.addEventListener('click', function(event) {
                        event.stopPropagation();
                        const isOpen = menu.classList.contains('open');
                        closeAllCrudeMenus(toggle, true);
                        if (!isOpen) {
                            menu.classList.add('open');
                            toggle.classList.add('active');
                        }
                    });
                    
                    menu.querySelectorAll('button[data-sort]').forEach(function(button) {
                        button.addEventListener('click', function(event) {
                            event.stopPropagation();
                            const sortKey = this.getAttribute('data-sort');
                            applyCrudeSort(spreadsheet, sortKey);
                            menu.classList.remove('open');
                            toggle.classList.remove('active');
                        });
                    });
                }
                
                function enhanceTable(tableElement) {
                    if (!tableElement || tableElement.dataset.productionEnhanced === 'true') {
                        return;
                    }
                    const spreadsheet = tableElement.querySelector('.dash-spreadsheet-container');
                    if (!spreadsheet) {
                        return;
                    }
                    tableElement.dataset.productionEnhanced = 'true';
                    spreadsheet.dataset.selectedKey = '';
                    
                    spreadsheet.addEventListener('click', function(event) {
                        const cell = event.target.closest('td[data-dash-row]');
                        if (!cell) {
                            return;
                        }
                        
                        const columnId = cell.getAttribute('data-dash-column');
                        const rowIndex = cell.getAttribute('data-dash-row');
                        
                        // Create a unique key for row selection (use row index as key)
                        const rowKey = 'row-' + rowIndex;
                        
                        // If clicking on Crude column, use row-based selection
                        if (columnId === 'Crude') {
                            if (spreadsheet.dataset.selectedKey === rowKey) {
                                clearSelection(spreadsheet);
                                return;
                            }
                            
                            spreadsheet.dataset.selectedKey = rowKey;
                            spreadsheet.classList.add('production-selection-active');
                            spreadsheet.querySelectorAll('.production-cell-selected').forEach(function(selectedCell) {
                                selectedCell.classList.remove('production-cell-selected');
                            });
                            spreadsheet.querySelectorAll('.production-row-selected').forEach(function(rowCell) {
                                rowCell.classList.remove('production-row-selected');
                            });
                            spreadsheet.querySelectorAll('.production-row-label-selected').forEach(function(labelCell) {
                                labelCell.classList.remove('production-row-label-selected');
                            });
                            
                            // Highlight entire row
                            const selectedRowCells = spreadsheet.querySelectorAll('td[data-dash-row="' + rowIndex + '"]');
                            selectedRowCells.forEach(function(rowCell) {
                                rowCell.classList.add('production-row-selected');
                                if (rowCell.getAttribute('data-dash-column') === 'Crude') {
                                    rowCell.classList.add('production-row-label-selected');
                                }
                            });
                            return;
                        }
                        
                        // For data cells, use cell-based selection (highlight only the clicked cell)
                        const cellKey = cell.getAttribute('data-dash-row') + '-' + columnId;
                        
                        if (spreadsheet.dataset.selectedKey === cellKey) {
                            clearSelection(spreadsheet);
                            return;
                        }
                        
                        spreadsheet.dataset.selectedKey = cellKey;
                        spreadsheet.classList.add('production-selection-active');
                        spreadsheet.querySelectorAll('.production-cell-selected').forEach(function(selectedCell) {
                            selectedCell.classList.remove('production-cell-selected');
                        });
                        spreadsheet.querySelectorAll('.production-row-selected').forEach(function(rowCell) {
                            rowCell.classList.remove('production-row-selected');
                        });
                        spreadsheet.querySelectorAll('.production-row-label-selected').forEach(function(labelCell) {
                            labelCell.classList.remove('production-row-label-selected');
                        });
                        cell.classList.add('production-cell-selected');
                    });
                    
                    setupCrudeSortMenu(tableElement, spreadsheet);
                }
                
                document.addEventListener('click', function(event) {
                    closeAllCrudeMenus(event.target, false);
                    document.querySelectorAll('#production-table .dash-spreadsheet-container.production-selection-active').forEach(function(spreadsheet) {
                        const wrapper = spreadsheet.closest('#production-table');
                        if (wrapper && !wrapper.contains(event.target)) {
                            clearSelection(spreadsheet);
                        }
                    });
                });
                
                const observer = new MutationObserver(function() {
                    const tableElement = document.getElementById('production-table');
                    if (tableElement) {
                        enhanceTable(tableElement);
                    }
                });
                
                observer.observe(document.body, { childList: true, subtree: true });
                
                const initialTable = document.getElementById('production-table');
                if (initialTable) {
                    enhanceTable(initialTable);
                }
            }
            
            // Start setup
            setupZoomLimits();
            initProductionTableEnhancements();
            setupPortHoverEffects();
            
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
def create_country_profile_dashboard(dash_app, server, url_base_pathname="/dash/country-profile/"):
    """Create the Country Profile dashboard"""
    # dash_app = create_dash_app(server, url_base_pathname) # Removed this line
    dash_app.layout = create_layout()
    register_callbacks(dash_app, server)
    return dash_app