"""
Imports - Country Comparison View
Global Crude Imports Dashboard - Based on Tableau design
"""
import json
import os
from urllib.request import urlopen
import dash
from dash import dcc, html, Input, Output, State, callback, dash_table, no_update
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from core.data_helpers import execute_query
from core.country_mappings import COUNTRY_TO_ISO, get_iso_code
from config import Config
from .shared_map_utils import (
    create_choropleth_map, 
    get_mapbox_config, 
    load_world_geojson,
    handle_map_click_reset,
    create_empty_map,
    MAP_BACKGROUND_COLOR as SHARED_MAP_BACKGROUND_COLOR,
    MAP_LAND_COLOR as SHARED_MAP_LAND_COLOR
)

# Set Mapbox access token
if Config.MAPBOX_ACCESS_TOKEN:
    px.set_mapbox_access_token(Config.MAPBOX_ACCESS_TOKEN)

def _iso_for_country(country):
    """Return ISO Alpha-3 code for a country, using centralized mapping."""
    return get_iso_code(country)

# Styling constants to match Energy Intelligence design
# Adjusted color scale with darker colors at lower values for better visibility
MAP_COLOR_SCALE = [
    (0.0, '#9fb3d1'),  # Darker light blue - was #d9dee7
    (0.2, '#7a95b8'),  # Darker - was #c5cedd
    (0.4, '#5d7ba5'),  # Darker - was #a0b9cf
    (0.6, '#4f6b96'),  # Darker - was #799dc0
    (0.8, '#3d5580'),  # Darker - was #4f76a4
    (1.0, '#1f3f70')   # Keep darkest the same
]
MAP_BACKGROUND_COLOR = SHARED_MAP_BACKGROUND_COLOR  # Use shared white background
MAP_LAND_COLOR = SHARED_MAP_LAND_COLOR

# Load data
def load_imports_data(selected_year=2023):
    """Load imports comparison data from database"""
    try:
        print(f"Loading imports data for year {selected_year}...")
        query = """
        SELECT
            EXTRACT(YEAR FROM yr)::INT AS "Year",
            import_country AS "Importer",
            SUM(vol_kbpd) AS "DataValue"
        FROM fact_wcod_imports
        WHERE
            (import_country NOT IN ('Australia', 'Japan', 'South Korea', 'United States')
            OR source <> 'OECD Imports')
            AND EXTRACT(YEAR FROM yr) = :selected_year
        GROUP BY
            EXTRACT(YEAR FROM yr),
            import_country
        ORDER BY
            "Year",
            "Importer";
        """
        
        rows = execute_query(query, {'selected_year': selected_year})
        
        if not rows:
            print("No imports data found for the selected year")
            return pd.DataFrame()
        
        print(f"Loaded {len(rows)} import records")
        df = pd.DataFrame(rows)
        # Rename DataValue to Import_Volume for consistency
        df = df.rename(columns={'DataValue': 'Import_Volume'})
        
        # Clean the data
        df = df[df['Importer'].notna()].copy()
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce').astype('Int64')
        df = df[df['Year'].notna()].copy()
        
        # Convert import volume to numeric
        df['Import_Volume'] = pd.to_numeric(df['Import_Volume'], errors='coerce')
        df = df[df['Import_Volume'].notna()].copy()
        
        # Filter out zero values for better visualization
        df = df[df['Import_Volume'] > 0].copy()
        
        print(f"Processed imports data: {len(df)} valid records")
        return df
    except Exception as e:
        print(f"Error loading imports data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

# Country name mapping for Plotly compatibility
COUNTRY_NAME_MAP = {
    'United States': 'United States of America',
    'South Korea': 'South Korea',
    'Czech Republic': 'Czechia',
    # Add more mappings as needed
}

# Reverse mapping for display
REVERSE_COUNTRY_MAP = {v: k for k, v in COUNTRY_NAME_MAP.items()}

def normalize_country_name(country):
    """Normalize country name for Plotly compatibility"""
    return COUNTRY_NAME_MAP.get(country, country)

def denormalize_country_name(country):
    """Convert normalized country name back to original"""
    return REVERSE_COUNTRY_MAP.get(country, country)

# Load annual imports data
def load_annual_imports_data(selected_countries=None):
    """Load annual imports data from database with dynamic country filtering"""
    try:
        # Base query
        base_query = """
        SELECT
            EXTRACT(YEAR FROM yr)::INT    AS "Year",
            EXTRACT(QUARTER FROM yr)::INT AS "Quarter of Year",
            EXTRACT(MONTH FROM yr)::INT   AS "Month of Year",
            EXTRACT(DAY FROM yr)::INT     AS "Day of Year",
            import_country AS "Importer",
            SUM(vol_kbpd) AS "DataValue"
        FROM fact_wcod_imports
        WHERE
            (import_country NOT IN ('Australia', 'Japan', 'South Korea', 'United States')
            OR source <> 'OECD Imports')
        """
        
        params = {}
        
        # Add country filter if countries are specified (filter out 'All' if present)
        if selected_countries:
            # Remove 'All' from the list if present
            countries_to_filter = [c for c in selected_countries if c != 'All']
            
            # If no countries are selected after removing 'All', return empty DataFrame
            if not countries_to_filter:
                return pd.DataFrame()
            
            if len(countries_to_filter) == 1:
                # Single country - use = operator
                base_query += " AND import_country = :import_country"
                params['import_country'] = countries_to_filter[0]
            else:
                # Multiple countries - use IN clause
                placeholders = ", ".join([f":country_{i}" for i in range(len(countries_to_filter))])
                base_query += f" AND import_country IN ({placeholders})"
                params = {f"country_{i}": country for i, country in enumerate(countries_to_filter)}
        else:
            # If selected_countries is None or empty, return empty DataFrame
            return pd.DataFrame()
        
        base_query += """
        GROUP BY
            EXTRACT(YEAR FROM yr)::INT,
            EXTRACT(QUARTER FROM yr)::INT,
            EXTRACT(MONTH FROM yr)::INT,
            EXTRACT(DAY FROM yr)::INT,
    import_country
        ORDER BY
            "Year",
            "Quarter of Year",
            "Month of Year",
            "Day of Year",
            "Importer";
        """
        
        rows = execute_query(base_query, params)
        
        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(rows)
        # Rename DataValue to Import_Volume for consistency
        df = df.rename(columns={'DataValue': 'Import_Volume'})
        
        # Clean the data
        df = df[df['Importer'].notna()].copy()
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce').astype('Int64')
        df = df[df['Year'].notna()].copy()
        
        # Convert import volume to numeric
        df['Import_Volume'] = pd.to_numeric(df['Import_Volume'], errors='coerce')
        df = df[df['Import_Volume'].notna()].copy()
        
        # Filter out zero values
        df = df[df['Import_Volume'] > 0].copy()
        
        return df
    except Exception as e:
        print(f"Error loading annual imports data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def load_import_export_matrix_data(selected_year=2023, selected_countries=None):
    """Load Import – Export Matrix data from database (single-year snapshot) with optional country filtering"""
    try:
        base_query = """
        SELECT
            EXTRACT(YEAR FROM yr)::INT AS "Year",
            import_country AS "Importer",
            export_country AS "Exporter",
            SUM(vol_kbpd) AS "DataValue"
        FROM fact_wcod_imports
        WHERE
            EXTRACT(YEAR FROM yr) = :selected_year
            AND (
                import_country NOT IN ('Australia', 'Japan', 'South Korea', 'United States')
                OR source <> 'OECD Imports'
            )
        """
        
        params = {'selected_year': selected_year}
        
        # Add country filter if countries are specified (filter out 'All' if present)
        if selected_countries:
            # Remove 'All' from the list if present
            countries_to_filter = [c for c in selected_countries if c != 'All']
            
            # If no countries are selected after removing 'All', return empty DataFrame
            if not countries_to_filter:
                return pd.DataFrame()
            
            if len(countries_to_filter) == 1:
                # Single country - use = operator
                base_query += " AND import_country = :import_country"
                params['import_country'] = countries_to_filter[0]
            else:
                # Multiple countries - use IN clause
                placeholders = ", ".join([f":country_{i}" for i in range(len(countries_to_filter))])
                base_query += f" AND import_country IN ({placeholders})"
                for i, country in enumerate(countries_to_filter):
                    params[f"country_{i}"] = country
        
        base_query += """
        GROUP BY
            EXTRACT(YEAR FROM yr),
            import_country,
            export_country
        ORDER BY
            "Year",
            "Importer",
            "Exporter";
        """
        
        rows = execute_query(base_query, params)
        
        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(rows)
        
        # Clean the data
        df = df[df['Importer'].notna() & df['Exporter'].notna()].copy()
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce').astype('Int64')
        df['DataValue'] = pd.to_numeric(df['DataValue'], errors='coerce')
        df = df[df['DataValue'].notna()].copy()
        
        # Filter out zero values
        df = df[df['DataValue'] > 0].copy()
        
        # Pivot the data: Exporter as rows, Importer as columns
        if df.empty:
            return pd.DataFrame()
        
        df_pivot = df.pivot_table(
            index='Exporter',
            columns='Importer',
            values='DataValue',
            aggfunc='sum',
            fill_value=0
        ).reset_index()
        
        # Sort exporters alphabetically
        df_pivot = df_pivot.sort_values('Exporter').reset_index(drop=True)
        
        return df_pivot
    except Exception as e:
        print(f"Error loading import-export matrix data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

# Load data on module import (all data is now loaded dynamically)
# Matrix data is loaded dynamically based on selected year

def get_available_years():
    """Get continuous list of available years from database"""
    try:
        query = """
        SELECT DISTINCT EXTRACT(YEAR FROM yr)::INT AS "Year"
        FROM fact_wcod_imports
        WHERE (import_country NOT IN ('Australia', 'Japan', 'South Korea', 'United States')
            OR source <> 'OECD Imports')
        ORDER BY "Year";
        """
        rows = execute_query(query)
        if rows:
            years = [int(row['Year']) for row in rows if row['Year'] is not None]
            if years:
                year_min, year_max = min(years), max(years)
                return list(range(year_min, year_max + 1))
        # Fallback to default range
        return list(range(2000, 2026))
    except Exception as e:
        print(f"Error getting available years: {e}")
        return list(range(2000, 2026))

def get_available_countries():
    """Get list of available countries from database"""
    try:
        query = """
        SELECT DISTINCT import_country AS "Importer"
        FROM fact_wcod_imports
        WHERE (import_country NOT IN ('Australia', 'Japan', 'South Korea', 'United States')
            OR source <> 'OECD Imports')
        ORDER BY import_country;
        """
        rows = execute_query(query)
        if rows:
            countries = [row['Importer'] for row in rows if row['Importer'] is not None]
            return sorted(countries)
        return []
    except Exception as e:
        print(f"Error getting available countries: {e}")
        return []

# Cache for world GeoJSON
_world_geojson = None

def _load_world_geojson():
    """Load world GeoJSON for Mapbox maps"""
    global _world_geojson
    if _world_geojson is not None:
        return _world_geojson
    url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
    try:
        with urlopen(url, timeout=5) as resp:
            _world_geojson = json.load(resp)
    except Exception as e:
        print(f"Error loading world GeoJSON: {e}")
        _world_geojson = None
    return _world_geojson

def get_all_countries_with_coordinates():
    """Get all countries from dim_country with their coordinates and ISO codes for labels and map"""
    try:
        query = """
        SELECT DISTINCT
            country_long_name AS "Country",
            country_code AS "ISO_Code",
            latitude AS "Latitude",
            longitude AS "Longitude"
        FROM dim_country
        WHERE country_long_name IS NOT NULL
            AND latitude IS NOT NULL
            AND longitude IS NOT NULL
        ORDER BY country_long_name;
        """
        rows = execute_query(query)
        if rows:
            return pd.DataFrame(rows)
        return pd.DataFrame(columns=['Country', 'ISO_Code', 'Latitude', 'Longitude'])
    except Exception as e:
        print(f"Error getting all countries with coordinates: {e}")
        return pd.DataFrame(columns=['Country', 'ISO_Code', 'Latitude', 'Longitude'])

AVAILABLE_YEARS = get_available_years()
YEAR_MIN = AVAILABLE_YEARS[0] if AVAILABLE_YEARS else 2000
YEAR_MAX = AVAILABLE_YEARS[-1] if AVAILABLE_YEARS else 2025
DEFAULT_YEAR = 2023 if 2023 in AVAILABLE_YEARS else YEAR_MAX
AVAILABLE_COUNTRIES = get_available_countries()


def build_year_marks(years, max_marks=8):
    """Create evenly spaced slider marks"""
    if not years:
        return {}
    years_sorted = sorted(years)
    if len(years_sorted) <= max_marks:
        return {year: str(year) for year in years_sorted}
    step = max(1, len(years_sorted) // (max_marks - 1))
    marks = {}
    for idx, year in enumerate(years_sorted):
        if idx % step == 0 or year in (years_sorted[0], years_sorted[-1]):
            marks[year] = str(year)
    marks[years_sorted[-1]] = str(years_sorted[-1])
    return marks


def create_imports_map_figure(df_map, single_selected_country, max_volume, selected_year):
    """Create the imports map figure using shared map utilities for consistency"""
    if df_map.empty:
        return create_empty_map("No countries with valid data for map display", height=550)
    
    # Store original country names BEFORE normalization for ISO code lookup
    df_map['Country_DB_Original'] = df_map['Country'].copy()
    
    # Store normalized country names for display
    df_map['Country_Original'] = df_map['Country'].apply(normalize_country_name)
    
    # Ensure country names are normalized for map compatibility
    df_map['Country'] = df_map['Country'].apply(normalize_country_name)
    
    # Create mapping from country names to ISO-3 codes using _iso_for_country function
    df_map['ISO_Code'] = df_map['Country_DB_Original'].apply(_iso_for_country)
    
    # Filter out any countries without valid ISO-3 codes
    df_map = df_map.dropna(subset=['ISO_Code']).copy()
    
    # Ensure ISO codes are strings and exactly 3 characters
    if not df_map.empty:
        df_map['ISO_Code'] = df_map['ISO_Code'].astype(str)
        df_map = df_map[df_map['ISO_Code'].str.len() == 3].copy()
    
    # Prepare data for the shared map utility
    locations = df_map['ISO_Code'].astype(str).tolist()
    z_values = df_map['Import_Volume'].tolist()
    
    # Create hover text with structured format matching the requested design
    # Using monospaced font for labels to ensure perfect alignment and adding extra br/nbsp for padding
    hover_text = df_map.apply(
        lambda row: (
            f"&nbsp;<br>"   # Top padding
            f"&nbsp;&nbsp;<span style='color: #666666; font-family: monospace;'>Importer:      </span><b>{row['Country_DB_Original']}</b>&nbsp;&nbsp;<br>"
            f"&nbsp;&nbsp;<span style='color: #666666; font-family: monospace;'>Year:          </span><b>{selected_year}</b>&nbsp;&nbsp;<br>"
            f"&nbsp;&nbsp;<span style='color: #666666; font-family: monospace;'>Traded Volume: </span><b>{row['Import_Volume']:,.0f}('000 b/d)</b>&nbsp;&nbsp;"
            f"<br>&nbsp;"  # Bottom padding
        ),
        axis=1,
    ).tolist()
    
    # Get country coordinates for labels
    all_countries_df = get_all_countries_with_coordinates()
    countries_in_map = df_map['Country_DB_Original'].tolist()
    countries_df = None
    if not all_countries_df.empty:
        countries_df = all_countries_df[all_countries_df['Country'].isin(countries_in_map)].copy()
    
    # Determine selection parameters - CRITICAL FIX HERE
    selected_iso = None
    other_isos = None
    
    if single_selected_country:
        # First, try to find the selected country in our dataframe
        # We need to handle potential normalization differences
        normalized_selected = normalize_country_name(single_selected_country)
        
        # Look for the country in various name fields
        country_match = None
        if single_selected_country in df_map['Country_DB_Original'].values:
            country_match = single_selected_country
        elif normalized_selected in df_map['Country'].values:
            # Find the original name for this normalized name
            matching_row = df_map[df_map['Country'] == normalized_selected]
            if not matching_row.empty:
                country_match = matching_row['Country_DB_Original'].iloc[0]
        
        if country_match and country_match in df_map['Country_DB_Original'].values:
            selected_iso = df_map.loc[df_map['Country_DB_Original'] == country_match, 'ISO_Code'].iloc[0]
            other_isos = [iso for iso in locations if iso != selected_iso]
            print(f"Map selection: {country_match} (ISO: {selected_iso}), dimming {len(other_isos)} other countries")
    
    # Create the map using shared utilities
    fig = create_choropleth_map(
        locations=locations,
        z_values=z_values,
        colorscale=MAP_COLOR_SCALE,
        hover_text=hover_text,
        selected_country=single_selected_country,
        selected_iso=selected_iso,
        other_isos=other_isos,
        countries_df=countries_df,
        height=550,
        zmin=0,
        zmax=max_volume
    )
    
    # Add custom margin and UI revision for imports
    fig.update_layout(
        margin=dict(l=20, r=20, t=20, b=80),
        uirevision='imports-map',
        mapbox_zoom=0.8,
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#cccccc",
            font=dict(
                family="Arial, sans-serif",
                size=12,
                color="black"
            ),
            align="left",
            namelength=0  # Hide trace name
        )
    )
    
    # Ensure only the main data trace shows the custom tooltip
    for trace in fig.data:
        if trace.name != "countries":
            trace.hoverinfo = 'skip'
    
    # Add copyright annotation
    use_mapbox, _, _ = get_mapbox_config()
    copyright_text = "© 2025 Mapbox © OpenStreetMap" if use_mapbox else "© 2025 Natural Earth"
    fig.add_annotation(
        text=copyright_text,
        xref="paper", yref="paper",
        x=0.01, y=0.01,
        showarrow=False,
        font=dict(size=10, color='#666'),
        bgcolor='rgba(255,255,255,0.8)',
        bordercolor='rgba(255,255,255,0.8)'
    )
    
    return fig

def create_layout():
    """Create the Imports - Country Comparison layout matching Tableau design"""
    return html.Div([
        dcc.Store(id='imports-year-store', data=DEFAULT_YEAR),
        dcc.Store(id='imports-year-play-store', data=False),
        dcc.Store(id='imports-country-store', data={'all_selected': True}),
        dcc.Store(id='imports-map-clicked-country', data=None),  # Store clicked country from map
        dcc.Store(id='imports-loading-state', data=False),  # Global loading state
        dcc.Store(id='imports-time-visibility', data={'Year': True, 'Quarter': False, 'Month': False, 'Day': False}),
        dcc.Store(id='imports-expand-store', data={'years': [], 'quarters': []}),
        dcc.Interval(id='imports-year-interval', interval=2000, disabled=True),
        # Download components
        dcc.Download(id="download-global-imports-csv"),
        dcc.Download(id="download-annual-imports-csv"),
        dcc.Download(id="download-matrix-imports-csv"),
        # Instruction text with loading indicator
        dcc.Loading(
            id="loading-instructions",
            type="dot",
            color="#d35400",
            children=[
                html.P(
                    "Select Countries from Map or List (right) to filter the tables below:",
                    style={
                        'textAlign': 'left',
                        'fontSize': '14px',
                        'color': '#1b365d',
                        'fontWeight': 'bold',
                        'marginBottom': '10px',
                        'marginTop': '10px'
                    }
                )
            ]
        ),
        # Main title with export button
        html.Div([
            html.H2(
                "Global Crude Imports",
                style={
                    'color': '#d35400',  # Orange color
                    'textAlign': 'center',
                    'marginBottom': '25px',
                    'fontSize': '20px',
                    'fontWeight': 'bold',
                    'letterSpacing': '0.5px',
                    'textTransform': 'uppercase',
                    'flex': '1'
                }
            ),
            dcc.Loading(
                id="loading-export-global-imports",
                type="default",
                color="#d35400",
                children=[
                    html.Button(
                        "Export to CSV",
                        id='export-global-imports-btn',
                        n_clicks=0,
                        style={
                            'backgroundColor': 'white',
                            'color': '#2c3e50',
                            'border': '1px solid #dee2e6',
                            'padding': '6px 12px',
                            'borderRadius': '4px',
                            'cursor': 'pointer',
                            'fontSize': '12px',
                            'fontWeight': 'normal'
                        }
                    )
                ]
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'gap': '20px', 'marginBottom': '25px'}),
        # Main content area
        html.Div([
            # Map area (left, larger)
            html.Div([
                dcc.Loading(
                    id="loading-imports-map",
                    type="dot",
                    color="#d35400",
                    children=[
                        dcc.Graph(
                            id='imports-world-map',
                            config={
                                'displayModeBar': True,
                                'displaylogo': False,
                                'modeBarButtons': [
                                    ['toImage', 'resetScale2d']
                                ],
                                'scrollZoom': True,
                                'doubleClick': 'reset'
                            },
                            style={
                                'height': '100%',
                                'width': '100%',
                                'maxWidth': '100%',
                                'margin': '0 auto'
                            }
                        )
                    ],
                    style={'height': '550px'}  # Match the map height
                )
            ], style={
                'flex': '1 1 calc(100% - 260px)',
                'maxWidth': 'calc(100% - 260px)',
                'display': 'inline-block',
                'verticalAlign': 'top',
                'paddingRight': '10px',
                'transition': 'width 0.2s ease'
            }),
            # Filters sidebar (right)
            html.Div([
                # Year filter
                html.Label(
                    "Year",
                    style={
                        'fontWeight': 'bold',
                        'color': '#2c3e50',
                        'fontSize': '13px',
                        'marginBottom': '5px',
                        'display': 'block'
                    }
                ),
                html.Div([
                    html.Button(
                        '◀',
                        id='imports-year-prev',
                        title='Previous year',
                        n_clicks=0,
                        style={
                            'border': '1px solid #cdd6e0',
                            'backgroundColor': 'white',
                            'padding': '4px 8px',
                            'cursor': 'pointer',
                            'borderRadius': '4px',
                            'fontSize': '12px'
                        }
                    ),
                    dcc.Dropdown(
                        id='imports-year-dropdown',
                        options=[{'label': str(y), 'value': y} for y in sorted(AVAILABLE_YEARS, reverse=True)],
                        value=DEFAULT_YEAR,
                        clearable=False,
                        style={
                            'flex': 1,
                            'fontSize': '12px'
                        }
                    ),
                    html.Button(
                        '▶',
                        id='imports-year-next',
                        title='Next year',
                        n_clicks=0,
                        style={
                            'border': '1px solid #cdd6e0',
                            'backgroundColor': 'white',
                            'padding': '4px 8px',
                            'cursor': 'pointer',
                            'borderRadius': '4px',
                            'fontSize': '12px'
                        }
                    )
                ], style={
                    'display': 'flex',
                    'alignItems': 'center',
                    'gap': '6px',
                    'marginBottom': '10px'
                }),
                dcc.Slider(
                    id='imports-year-slider',
                    min=YEAR_MIN,
                    max=YEAR_MAX,
                    step=1,
                    value=DEFAULT_YEAR,
                    marks=None,  # Remove marks to prevent overlapping labels
                    tooltip={'always_visible': False, 'placement': 'bottom'},
                    included=False,
                    updatemode='mouseup',
                    className='imports-year-slider'
                ),
                html.Div([
                    html.Button(
                        '◄',
                        id='imports-year-timeline-prev',
                        n_clicks=0,
                        title='Step backward',
                        style={
                            'border': '1px solid #cdd6e0',
                            'backgroundColor': 'white',
                            'padding': '4px 10px',
                            'cursor': 'pointer',
                            'borderRadius': '4px',
                            'fontSize': '12px',
                            'minWidth': '34px'
                        }
                    ),
                    html.Button(
                        '▶',
                        id='imports-year-play-toggle',
                        n_clicks=0,
                        title='Play/Pause animation',
                        style={
                            'border': '1px solid #cdd6e0',
                            'backgroundColor': 'white',
                            'padding': '4px 10px',
                            'cursor': 'pointer',
                            'borderRadius': '4px',
                            'fontSize': '12px',
                            'minWidth': '34px'
                        }
                    ),
                    html.Button(
                        '►',
                        id='imports-year-timeline-next',
                        n_clicks=0,
                        title='Step forward',
                        style={
                            'border': '1px solid #cdd6e0',
                            'backgroundColor': 'white',
                            'padding': '4px 10px',
                            'cursor': 'pointer',
                            'borderRadius': '4px',
                            'fontSize': '12px',
                            'minWidth': '34px'
                        }
                    )
                ], style={
                    'display': 'flex',
                    'justifyContent': 'center',
                    'gap': '6px',
                    'margin': '8px 0 18px'
                }),
                # Country filter
                html.Label(
                    "Importing Country",
                    style={
                        'fontWeight': 'bold',
                        'color': '#2c3e50',
                        'fontSize': '13px',
                        'marginBottom': '5px',
                        'display': 'block'
                    }
                ),
                html.Div([
                    dcc.Checklist(
                        id='imports-country-checklist',
                        options=[{'label': '(All)', 'value': 'All'}] + 
                                [{'label': c, 'value': c} for c in AVAILABLE_COUNTRIES],
                        value=['All'] + AVAILABLE_COUNTRIES,
                        style={'fontSize': '12px'},
                    inputStyle={
                        'marginRight': '6px',
                        'width': '16px',
                        'height': '16px',
                            'accentColor': '#2c3e50',
                            'verticalAlign': 'middle'
                    },
                    labelStyle={
                            'display': 'flex',
                            'alignItems': 'center',
                            'gap': '4px',
                            'marginBottom': '4px',
                            'paddingLeft': '2px',
                            'fontSize': '12px',
                            'lineHeight': '16px',
                            'color': '#2c3e50',
                            'fontWeight': 'normal'
                    }
                    )
                ], style={
                    'marginBottom': '20px',
                    'maxHeight': '300px',
                    'overflowY': 'auto',
                    'border': '1px solid #ddd',
                    'borderRadius': '4px',
                    'padding': '10px',
                    'backgroundColor': '#f9f9f9'
                }),
                # Import Volume Legend (visual representation)
                html.Div([
                    html.Label(
                        "Import Volume ('000 b/d)",
                        style={
                            'fontWeight': 'bold',
                            'color': '#2c3e50',
                            'fontSize': '13px',
                            'marginBottom': '10px',
                            'display': 'block'
                        }
                    ),
                    dcc.Loading(
                        id="loading-imports-legend",
                        type="dot",
                        color="#d35400",
                        children=[
                            html.Div([
                                html.Div([
                                    html.Div(style={'flex': 1, 'backgroundColor': '#e9ecf2'}),
                                    html.Div(style={'flex': 1, 'backgroundColor': '#d9dee8'}),
                                    html.Div(style={'flex': 1, 'backgroundColor': '#c6cedf'}),
                                    html.Div(style={'flex': 1, 'backgroundColor': '#b3bed6'}),
                                    html.Div(style={'flex': 1, 'backgroundColor': '#a1adcc'}),
                                    html.Div(style={'flex': 1, 'backgroundColor': '#8e9cc3'}),
                                    html.Div(style={'flex': 1, 'backgroundColor': '#7c8cb9'}),
                                    html.Div(style={'flex': 1, 'backgroundColor': '#6a7bb0'}),
                                    html.Div(style={'flex': 1, 'backgroundColor': '#586ba6'}),
                                    html.Div(style={'flex': 1, 'backgroundColor': '#475a9d'}),
                                    html.Div(style={'flex': 1, 'backgroundColor': '#364a94'}),
                                    html.Div(style={'flex': 1, 'backgroundColor': '#25398a'}),
                                    html.Div(style={'flex': 1, 'backgroundColor': '#132880'})
                                ], style={
                                    'display': 'flex',
                                    'height': '16px',
                                    'borderRadius': '4px',
                                    'overflow': 'hidden',
                                    'border': '1px solid #8e98ad'
                                }),
                                html.Div([
                                    html.Span('0', style={'fontSize': '10px', 'color': '#333', 'flex': '1', 'textAlign': 'left', 'paddingTop': '3px'}),
                                    html.Span(id='imports-mid-value', children='', style={'display': 'none'}),
                                    html.Span(id='imports-max-value', children='0', style={'fontSize': '10px', 'color': '#333', 'flex': '1', 'textAlign': 'right', 'paddingTop': '3px'})
                                ], style={'display': 'flex', 'width': '100%'})
                            ], id='imports-legend', style={'maxWidth': '190px'})
                        ]
                    )
                ], style={'marginTop': '20px'})
            ], style={
                'width': '240px',
                'maxWidth': '240px',
                'display': 'inline-block',
                'verticalAlign': 'top',
                'paddingLeft': '10px',
                'boxSizing': 'border-box'
            })
        ], style={'width': '100%', 'display': 'flex'}),
        # Annual Imports Volume section
        html.Div([
            html.Div([
                html.H3(
                    "Annual Imports Volume ('000 b/d)",
                    style={
                        'color': '#d35400',
                        'textAlign': 'center',
                        'marginTop': '30px',
                        'marginBottom': '15px',
                        'fontSize': '20px',
                        'fontWeight': 'bold',
                        'flex': '1'
                    }
                ),
                dcc.Loading(
                    id="loading-export-annual-imports",
                    type="default",
                    color="#d35400",
                    children=[
                        html.Button(
                            "Export to CSV",
                            id='export-annual-imports-btn',
                            n_clicks=0,
                            style={
                                'backgroundColor': 'white',
                                'color': '#2c3e50',
                                'border': '1px solid #dee2e6',
                                'padding': '6px 12px',
                                'borderRadius': '4px',
                                'cursor': 'pointer',
                                'fontSize': '12px',
                                'marginTop': '30px'
                            }
                        )
                    ]
                )
            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'gap': '20px'}),
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
                        'marginLeft': '3px', 'flexShrink': '0'
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
                        'marginLeft': '3px', 'flexShrink': '0'
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
                        'marginLeft': '3px', 'flexShrink': '0'
                    })
                ], style={'display': 'flex', 'alignItems': 'left', 'width': '130px'})
            ], style={
                'padding': '10px 0',
                'marginBottom': '10px',
                'display': 'flex',
                'justifyContent': 'flex-start',
                'alignItems': 'center',
                'gap': '10px'
            }),
            dcc.Loading(
                id="loading-imports-annual-table",
                type="default",
                color="#d35400",
                children=[
                    html.Div(
                        id='imports-annual-table-container',
                        children=[],
                        style={'minHeight': '430px'}
                    )
                ],
                style={'minHeight': '430px'}
            ),
            html.Div([
                html.P(
                    id='imports-matrix-caption',
                    children="Import – Export Matrix ('000 b/d)",
                    style={
                        'textAlign': 'center',
                        'fontWeight': 'bold',
                        'color': '#d35400',
                        'marginTop': '15px',
                        'marginBottom': '0',
                        'flex': '1'
                    }
                ),
                dcc.Loading(
                    id="loading-export-matrix-imports",
                    type="default",
                    color="#d35400",
                    children=[
                        html.Button(
                            "Export to CSV",
                            id='export-matrix-imports-btn',
                            n_clicks=0,
                            style={
                                'backgroundColor': 'white',
                                'color': '#2c3e50',
                                'border': '1px solid #dee2e6',
                                'padding': '6px 12px',
                                'borderRadius': '4px',
                                'cursor': 'pointer',
                                'fontSize': '12px',
                                'marginTop': '15px'
                            }
                        )
                    ]
                )
            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'gap': '20px'}),
            dcc.Loading(
                id="loading-imports-matrix-table",
                type="default",
                color="#d35400",
                children=[
                    html.Div(
                        id='imports-matrix-table-container',
                        children=[],
                        style={'marginTop': '10px', 'minHeight': '520px'}
                    )
                ],
                style={'minHeight': '520px'}
            ),
            html.Div(
                id='imports-footnotes',
                children=[
                    html.Div("EIA Data is through June 2025", className='footnote-item', **{'data-note-key': 'eia'}),
                    html.Div("Energy Intelligence Data is through July 2025", className='footnote-item', **{'data-note-key': 'ei'}),
                    html.Div("OECD Data is through July 2025", className='footnote-item', **{'data-note-key': 'oecd'}),
                    html.Div("Russian Imports Data is through August 2022", className='footnote-item', **{'data-note-key': 'russia'}),
                    html.Div("South Korea trade data source: KNOC", className='footnote-static'),
                    html.Div("Countries: Select jurisdictions are included under countries for data presentation purposes.", className='footnote-static')
                ],
                style={
                    'fontSize': '11px',
                    'color': '#6c7a89',
                    'lineHeight': '1.4',
                    'marginTop': '12px',
                    'textAlign': 'left',
                    'display': 'flex',
                    'flexDirection': 'column',
                    'gap': '4px'
                }
            )
        ], style={'width': '100%', 'marginTop': '30px'}),
        html.Div(id='imports-table-enhancer-anchor', style={'display': 'none'})
    ], className='tab-content', style={'padding': '20px'})


def register_callbacks(dash_app, server):
    """Register all callbacks for Imports - Country Comparison"""
    
    @dash_app.callback(
        [Output('imports-map-clicked-country', 'data'),
         Output('imports-country-checklist', 'value', allow_duplicate=True)],
        Input('imports-world-map', 'clickData'),
        [State('imports-map-clicked-country', 'data'),
         State('imports-country-checklist', 'value')],
        prevent_initial_call=True
    )
    def handle_map_click(clickData, current_clicked_country, current_selection):
        """Handle map click to update country selection like in projects_by_country.py"""
        if not clickData or 'points' not in clickData or len(clickData['points']) == 0:
            return no_update, no_update
        
        point = clickData['points'][0]
        clicked_country = None
        
        # Extract country name using multiple fallback methods (same as projects_by_country.py)
        if "text" in point and point["text"]:
            clicked_country = point["text"]
        elif "hovertext" in point and point["hovertext"]:
            hovertext = point["hovertext"]
            if "<b>" in hovertext and "</b>" in hovertext:
                clicked_country = hovertext.split("<b>")[1].split("</b>")[0]
        elif "customdata" in point and point["customdata"]:
            if isinstance(point["customdata"], list) and len(point["customdata"]) > 0:
                clicked_country = point["customdata"][0]
            else:
                clicked_country = point["customdata"]
        elif "location" in point:
            iso_value = point["location"]
            # Use reverse mapping from COUNTRY_TO_ISO
            reverse_map = {v: k for k, v in COUNTRY_TO_ISO.items()}
            clicked_country = reverse_map.get(iso_value, None)
        
        if not clicked_country:
            return no_update, no_update
        
        # Denormalize country name if needed (convert from map display name to original name)
        original_country_name = denormalize_country_name(clicked_country)
        if original_country_name not in AVAILABLE_COUNTRIES:
            # Try to find by case-insensitive matching
            for country in AVAILABLE_COUNTRIES:
                if (country.lower() == clicked_country.lower() or 
                    normalize_country_name(country).lower() == clicked_country.lower()):
                    original_country_name = country
                    break
            else:
                # Country not found in available countries
                return no_update, no_update
        
        # Apply the same logic as projects_by_country.py
        current_selection = current_selection or []
        
        # Resolve current selection (handle "All" case)
        if 'All' in current_selection:
            resolved_countries = AVAILABLE_COUNTRIES
        else:
            resolved_countries = [c for c in current_selection if c in AVAILABLE_COUNTRIES]
        
        # If country is not currently in the resolved selection, select only this country
        if original_country_name not in resolved_countries:
            return original_country_name, [original_country_name]
        
        # If this country is already the only one selected, expand to show all
        if len(resolved_countries) == 1 and original_country_name in resolved_countries:
            return None, ['All'] + AVAILABLE_COUNTRIES
            
        # If multiple countries are selected and this one is clicked, select only this country
        return original_country_name, [original_country_name]
    
    @dash_app.callback(
        [Output('imports-world-map', 'figure'),
         Output('imports-annual-table-container', 'children'),
         Output('imports-matrix-table-container', 'children'),
         Output('imports-max-value', 'children'),
         Output('imports-mid-value', 'children'),
         Output('imports-matrix-caption', 'children')],
        [Input('imports-year-store', 'data'),
         Input('imports-country-checklist', 'value'),
         Input('imports-map-clicked-country', 'data'),
         Input('imports-time-visibility', 'data'),
         Input('imports-expand-store', 'data')],
        prevent_initial_call=False
    )
    def update_imports_dashboard(selected_year, selected_countries, clicked_country, time_visibility, expansion_state):
        """Update map and annual chart based on filters"""
        matrix_caption = f"Import – Export Matrix for {selected_year} ('000 b/d)"
        
        # Load imports data dynamically for the selected year
        IMPORTS_DF = load_imports_data(selected_year)
        
        # Normalize country names for map compatibility
        if not IMPORTS_DF.empty:
            IMPORTS_DF['Importer'] = IMPORTS_DF['Importer'].apply(normalize_country_name)
        
        if IMPORTS_DF.empty:
            empty_fig = go.Figure()
            empty_fig.add_annotation(
                text="No data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False
            )
            empty_fig.update_layout(height=600, plot_bgcolor='white', paper_bgcolor='white')
            return (
                empty_fig,
                html.Div("No data available", style={'padding': '20px', 'textAlign': 'center', 'color': '#666'}),
                html.Div("No data available", style={'padding': '20px', 'textAlign': 'center', 'color': '#666'}),
                '0',
                '0',
                matrix_caption
            )
        
        # Data is already filtered by year in the query
        df_filtered = IMPORTS_DF.copy()
        
        # Filter by countries if not "All"
        # The checklist uses original country names, but map data uses normalized names
        selected_countries_for_map = []
        if 'All' in selected_countries:
            # Show all countries
            selected_countries_for_map = [normalize_country_name(country) for country in AVAILABLE_COUNTRIES]
        elif selected_countries:
            # Show only selected countries
            selected_countries_for_map = [normalize_country_name(country) for country in selected_countries]
        else:
            # No countries selected, show empty
            selected_countries_for_map = []
        
        # Filter the data to show only selected countries
        if selected_countries_for_map:
            df_filtered = df_filtered[df_filtered['Importer'].isin(selected_countries_for_map)].copy()
        else:
            # No countries selected, return empty dataframe
            df_filtered = pd.DataFrame()
        
        print(f"After country filtering: {len(df_filtered)} rows, countries: {df_filtered['Importer'].unique().tolist() if not df_filtered.empty else []}")
        
        # Determine if a single country is selected for special handling
        single_selected_country = None
        if clicked_country and clicked_country in selected_countries:
            single_selected_country = clicked_country
        elif len(selected_countries) == 1 and 'All' not in selected_countries:
            single_selected_country = selected_countries[0]
        
        # Create map
        if IMPORTS_DF.empty:
            map_fig = go.Figure()
            map_fig.add_annotation(
                text="No data available for the selected year",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False
            )
            map_fig.update_layout(height=600, plot_bgcolor='white', paper_bgcolor='white')
        else:
            # Aggregate by country using unfiltered data for the map
            df_map = IMPORTS_DF.groupby('Importer')['Import_Volume'].sum().reset_index()
            df_map.columns = ['Country', 'Import_Volume']
            
            print(f"Map data after aggregation: {len(df_map)} countries")
            if not df_map.empty:
                print(f"Countries in map data: {df_map['Country'].tolist()}")
            
            # Store original country names BEFORE normalization for ISO code lookup
            df_map['Country_DB_Original'] = df_map['Country'].copy()
            
            # Store normalized country names for display
            df_map['Country_Original'] = df_map['Country'].apply(normalize_country_name)
            
            # Ensure country names are normalized for map compatibility
            df_map['Country'] = df_map['Country'].apply(normalize_country_name)
            
            # Create choropleth map
            max_volume = df_map['Import_Volume'].max() if len(df_map) > 0 else 1
            # Add year column for hover
            df_map['Year'] = selected_year
            
            # Store original country names BEFORE normalization for ISO code lookup
            df_map['Country_DB_Original'] = df_map['Country'].copy()
            
            # Store normalized country names for display
            df_map['Country_Original'] = df_map['Country'].apply(normalize_country_name)
            
            # Create mapping from country names to ISO-3 codes using _iso_for_country function
            df_map['ISO_Code'] = df_map['Country_DB_Original'].apply(_iso_for_country)
            
            # Filter out any countries without valid ISO-3 codes
            df_map = df_map.dropna(subset=['ISO_Code']).copy()
            
            # Ensure ISO codes are strings and exactly 3 characters
            if not df_map.empty:
                df_map['ISO_Code'] = df_map['ISO_Code'].astype(str)
                df_map = df_map[df_map['ISO_Code'].str.len() == 3].copy()
            
            # Create map figure using the same approach as projects_by_country.py
            map_fig = create_imports_map_figure(df_map, single_selected_country, max_volume, selected_year)
        
        # Create annual table using database query with dynamic country filtering
        # Load annual imports data based on selected countries
        df_annual = load_annual_imports_data(selected_countries)
        
        if df_annual.empty:
            annual_table = html.Div("No data available", style={'padding': '20px', 'textAlign': 'center', 'color': '#666'})
        else:
            # Time visibility settings
            time_visibility = time_visibility or {'Year': True, 'Quarter': False, 'Month': False, 'Day': False}
            show_quarter = time_visibility.get('Quarter', False)
            show_month = time_visibility.get('Month', False)
            show_day = time_visibility.get('Day', False)
            
            # Constants for names
            quarter_order = ['Q1', 'Q2', 'Q3', 'Q4']
            month_order = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]
            
            # Map numeric values to names
            if 'Quarter of Year' in df_annual.columns:
                quarter_map = {1: 'Q1', 2: 'Q2', 3: 'Q3', 4: 'Q4'}
                df_annual['Quarter of Year'] = df_annual['Quarter of Year'].map(quarter_map).fillna('').astype(str)
            
            if 'Month of Year' in df_annual.columns:
                month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                              'July', 'August', 'September', 'October', 'November', 'December']
                df_annual['Month of Year'] = df_annual['Month of Year'].apply(lambda x: month_names[int(x)] if pd.notna(x) and 1 <= int(x) <= 12 else '').astype(str)

            # Get available years (sorted descending: 2025, 2024, 2023, etc.)
            available_years = sorted(df_annual['Year'].unique().tolist(), reverse=True)
            
            # Limit to recent years (2019-2025) as shown in the reference
            target_years = [y for y in range(2025, 2018, -1) if y in available_years]
            if not target_years:
                target_years = available_years
            
            # Determine default quarter/month per year (first available in order)
            year_defaults = {}
            for year in target_years:
                df_year = df_annual[df_annual['Year'] == year]
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
                                if 'Day of Year' in df_m.columns and not df_m['Day of Year'].dropna().empty:
                                    d_default = str(int(df_m['Day of Year'].dropna().iloc[0]))
                                break
                        if m_default:
                            break
                year_defaults[year] = (q_default, m_default, d_default)

            # Prepare columns and data for pivot
            # We want to pivot to: Importer as index, Year as columns (with multi-line header)
            # The value should be the specific slice (Year sum, or specific Q/M/D slice)
            
            table_records = []
            importers = sorted(df_annual['Importer'].unique())
            
            for importer in importers:
                record = {'Importer': importer}
                df_imp = df_annual[df_annual['Importer'] == importer]
                
                for year in target_years:
                    q_def, m_def, d_def = year_defaults.get(year, ('', '', ''))
                    
                    if show_day:
                        # Day slice
                        val = df_imp[(df_imp['Year'] == year) & 
                                    (df_imp['Quarter of Year'] == q_def) & 
                                    (df_imp['Month of Year'] == m_def) & 
                                    (df_imp['Day of Year'] == float(d_def) if d_def else False)]['Import_Volume'].sum()
                        col_id = str(year)
                    elif show_month:
                        # Month slice
                        val = df_imp[(df_imp['Year'] == year) & 
                                    (df_imp['Quarter of Year'] == q_def) & 
                                    (df_imp['Month of Year'] == m_def)]['Import_Volume'].sum()
                        col_id = str(year)
                    elif show_quarter:
                        # Quarter slice
                        val = df_imp[(df_imp['Year'] == year) & 
                                    (df_imp['Quarter of Year'] == q_def)]['Import_Volume'].sum()
                        col_id = str(year)
                    else:
                        # Year slice (sum of all months in that year)
                        val = df_imp[df_imp['Year'] == year]['Import_Volume'].sum()
                        col_id = str(year)
                    
                    record[col_id] = val if val > 0 else 0
                table_records.append(record)
            
            # Add Grand Total row
            totals_row = {'Importer': 'Grand Total'}
            for year in target_years:
                col_id = str(year)
                q_def, m_def, d_def = year_defaults.get(year, ('', '', ''))
                
                if show_day:
                    val = df_annual[(df_annual['Year'] == year) & 
                                   (df_annual['Quarter of Year'] == q_def) & 
                                   (df_annual['Month of Year'] == m_def) & 
                                   (df_annual['Day of Year'] == float(d_def) if d_def else False)]['Import_Volume'].sum()
                elif show_month:
                    val = df_annual[(df_annual['Year'] == year) & 
                                   (df_annual['Quarter of Year'] == q_def) & 
                                   (df_annual['Month of Year'] == m_def)]['Import_Volume'].sum()
                elif show_quarter:
                    val = df_annual[(df_annual['Year'] == year) & 
                                   (df_annual['Quarter of Year'] == q_def)]['Import_Volume'].sum()
                else:
                    val = df_annual[df_annual['Year'] == year]['Import_Volume'].sum()
                
                totals_row[col_id] = val if val > 0 else 0
            table_records.append(totals_row)

            # Build multi-line headers
            columns = [{'name': 'Importer', 'id': 'Importer'}]
            for year in target_years:
                q_def, m_def, d_def = year_defaults.get(year, ('', '', ''))
                header_lines = [str(year)]
                if show_quarter and q_def:
                    header_lines.append(q_def)
                if show_month and m_def:
                    header_lines.append(m_def)
                if show_day and d_def:
                    header_lines.append(d_def)
                
                header_name = '\n'.join(header_lines)
                columns.append({
                    'name': header_name,
                    'id': str(year),
                    'type': 'numeric',
                    'format': {'specifier': ',.0f'}
                })

            data = []
            for record in table_records:
                formatted = {'Importer': record['Importer']}
                for year in target_years:
                    val = record.get(str(year), 0)
                    formatted[str(year)] = f"{val:,.0f}" if val > 0 else ""
                data.append(formatted)

            # Create DataTable
            annual_table = dash_table.DataTable(
                    id='imports-annual-table',
                    columns=columns,
                    data=data,
                    style_table={
                        'overflowX': 'auto',
                        'overflowY': 'auto',
                        'border': '1px solid #e0e0e0',
                        'borderRadius': '4px',
                        'backgroundColor': 'white',
                        'width': '100%',
                        'minWidth': '100%',
                        'maxHeight': '430px',
                        'height': '430px'
                    },
                    style_cell={
                        'textAlign': 'left',
                        'padding': '8px 12px',
                        'fontSize': '12px',
                        'fontFamily': 'Arial, sans-serif',
                        'border': '1px solid #e0e0e0',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                        'minHeight': '35px',
                        'color': '#333333',
                        'backgroundColor': 'white'
                    },
                    style_header={
                        'backgroundColor': '#f8f9fa',
                        'fontWeight': 'bold',
                        'fontSize': '12px',
                        'fontFamily': 'Arial, sans-serif',
                        'border': '1px solid #e0e0e0',
                        'color': '#2c3e50',
                        'textAlign': 'center',
                        'padding': '10px 12px'
                    },
                    style_data={
                        'border': '1px solid #e0e0e0',
                        'backgroundColor': 'white'
                    },
                    style_cell_conditional=[
                        {
                            'if': {'column_id': 'Importer'},
                            'textAlign': 'left',
                            'fontWeight': 'bold',
                            'minWidth': '150px',
                            'color': '#1b365d'
                    }
                ] + [
                        {
                            'if': {'column_id': str(year)},
                            'textAlign': 'right',
                            'minWidth': '100px'
                        }
                        for year in target_years
                    ],
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#f8f9fa'
                        },
                        {
                            'if': {'filter_query': '{Importer} = "Grand Total"'},
                            'fontWeight': 'bold',
                            'backgroundColor': '#f0f0f0'
                        }
                    ],
                    css=[
                        {
                            'selector': '.dash-header',
                            'rule': 'white-space: pre-line !important; line-height: 1.2 !important;'
                        }
                    ],
                    fixed_rows={'headers': True},
                    page_action='none',
                    sort_action='none',
                    filter_action='none',
                    merge_duplicate_headers=True
                )

        # Load matrix data dynamically for the selected year and countries
        # Pass selected_countries to filter the matrix by clicked/selected countries
        IMPORT_EXPORT_MATRIX_DF = load_import_export_matrix_data(selected_year, selected_countries)
        
        if IMPORT_EXPORT_MATRIX_DF.empty:
            matrix_table = html.Div(
                "Import – Export matrix data unavailable",
                style={'padding': '20px', 'textAlign': 'center', 'color': '#666'}
            )
        else:
            # Get column order (all columns except 'Exporter')
            MATRIX_COLUMN_ORDER = [
                col for col in IMPORT_EXPORT_MATRIX_DF.columns if col != 'Exporter'
            ]
            
            # Sort importers (columns) alphabetically
            MATRIX_COLUMN_ORDER = sorted(MATRIX_COLUMN_ORDER)
            
            # Add row totals (sum of all importers for each exporter)
            IMPORT_EXPORT_MATRIX_DF = IMPORT_EXPORT_MATRIX_DF.copy()
            IMPORT_EXPORT_MATRIX_DF['Grand Total'] = IMPORT_EXPORT_MATRIX_DF[MATRIX_COLUMN_ORDER].sum(axis=1)
            
            # Add column totals (sum of all exporters for each importer)
            totals_row = {'Exporter': 'Grand Total'}
            for col in MATRIX_COLUMN_ORDER:
                totals_row[col] = IMPORT_EXPORT_MATRIX_DF[col].sum()
            totals_row['Grand Total'] = IMPORT_EXPORT_MATRIX_DF[MATRIX_COLUMN_ORDER].sum().sum()
            
            # Append totals row to dataframe
            IMPORT_EXPORT_MATRIX_DF = pd.concat([
                IMPORT_EXPORT_MATRIX_DF,
                pd.DataFrame([totals_row])
            ], ignore_index=True)
            
            # Update column order to include Grand Total column
            MATRIX_COLUMN_ORDER_WITH_TOTAL = MATRIX_COLUMN_ORDER + ['Grand Total']
            
            matrix_data_records = []
            for record in IMPORT_EXPORT_MATRIX_DF.to_dict('records'):
                formatted = {'Exporter': record.get('Exporter', '')}
                for column in MATRIX_COLUMN_ORDER_WITH_TOTAL:
                    value = record.get(column)
                    if value is None or pd.isna(value) or value == 0:
                        formatted[column] = ''
                    else:
                        formatted[column] = f"{value:,.0f}"
                matrix_data_records.append(formatted)

            matrix_columns = [{'name': 'Exporter', 'id': 'Exporter'}] + [
                {'name': col, 'id': col} for col in MATRIX_COLUMN_ORDER_WITH_TOTAL
            ]

            matrix_table = dash_table.DataTable(
                id='imports-matrix-table',
                columns=matrix_columns,
                data=matrix_data_records,
                style_table={
                    'overflowX': 'auto',
                    'overflowY': 'auto',
                    'border': '1px solid #e0e0e0',
                    'borderRadius': '4px',
                    'backgroundColor': 'white',
                    'maxHeight': '520px',
                    'height': '520px',
                    'width': '100%'
                },
                style_cell={
                    'textAlign': 'right',
                    'padding': '6px 10px',
                    'fontSize': '11px',
                    'fontFamily': 'Arial, sans-serif',
                    'border': '1px solid #e0e0e0',
                    'whiteSpace': 'normal',
                    'minWidth': '90px',
                    'backgroundColor': 'white',
                    'color': '#333333'
                },
                style_header={
                    'backgroundColor': '#f8f9fa',
                    'fontWeight': 'bold',
                    'fontSize': '11px',
                    'fontFamily': 'Arial, sans-serif',
                    'border': '1px solid #e0e0e0',
                    'color': '#1b365d',
                    'textAlign': 'center',
                    'padding': '8px 10px'
                },
                style_cell_conditional=[
                    {
                        'if': {'column_id': 'Exporter'},
                        'textAlign': 'left',
                        'fontWeight': 'bold',
                        'minWidth': '180px',
                        'color': '#1b365d'
                    }
                ],
                style_data={
                    'border': '1px solid #e0e0e0',
                    'backgroundColor': 'white'
                },
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
                    {
                        'if': {'filter_query': '{Exporter} = "Grand Total"'},
                        'fontWeight': 'bold',
                        'backgroundColor': '#f0f0f0'
                    },
                    {
                        'if': {'column_id': 'Grand Total'},
                        'fontWeight': 'bold',
                        'backgroundColor': '#f0f0f0'
                    }
                ],
                fixed_rows={'headers': True},
                page_action='none',
                sort_action='none',
                filter_action='none'
            )
        
        # Get max value for legend from unfiltered map data
        if IMPORTS_DF.empty:
            max_value = 0
        else:
            max_value = IMPORTS_DF.groupby('Importer')['Import_Volume'].sum().max()
        
        max_value_str = f"{max_value:,.0f}" if max_value > 0 else "0"
        mid_value_str = f"{(max_value / 2):,.0f}" if max_value > 0 else "0"
        
        return map_fig, annual_table, matrix_table, max_value_str, mid_value_str, matrix_caption
    
    # Button icons and styles reflecting time visibility state
    @dash_app.callback(
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

    @dash_app.callback(
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

    @dash_app.callback(
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
        if not vis['Quarter']:
            vis['Month'] = False
            vis['Day'] = False
        return vis, expand_state

    @dash_app.callback(
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
        if vis['Month']:
            vis['Quarter'] = True
        else:
            vis['Day'] = False
        return vis, expand_state

    @dash_app.callback(
        Output('imports-time-visibility', 'data', allow_duplicate=True),
        Input('imports-toggle-day-btn', 'n_clicks'),
        State('imports-time-visibility', 'data'),
        prevent_initial_call=True
    )
    def toggle_day_vis(n_clicks, vis):
        vis = (vis or {'Year': True, 'Quarter': False, 'Month': False, 'Day': False}).copy()
        vis['Day'] = not vis.get('Day', False)
        if vis['Day']:
            vis['Month'] = True
            vis['Quarter'] = True
        return vis

    @dash_app.callback(
        Output('imports-expand-store', 'data'),
        Input('imports-annual-table', 'active_cell'),
        State('imports-expand-store', 'data'),
        prevent_initial_call=True
    )
    def toggle_header_expansion(active_cell, state):
        """Toggle expansion for year/quarter headers via header clicks."""
        state = state or {'years': [], 'quarters': []}
        years = set(state.get('years', []))
        quarters = set(tuple(q) for q in state.get('quarters', []))
        
        if not active_cell or active_cell.get('row') != -1:
            return dash.no_update
        
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

    @dash_app.callback(
        Output('imports-country-checklist', 'value'),
        Output('imports-country-store', 'data'),
        Input('imports-country-checklist', 'value'),
        State('imports-country-store', 'data'),
        prevent_initial_call=True
    )
    def handle_country_checklist(selection, country_state):
        """Toggle '(All)' checkbox to select/deselect every country"""
        selection = selection or []
        state = country_state or {'all_selected': False}
        all_selected = bool(state.get('all_selected'))
        selected_set = set(selection)
        has_all = 'All' in selected_set
        countries_set = set(AVAILABLE_COUNTRIES)
        
        # User unchecked "(All)" while everything else stayed checked => clear all
        if all_selected and not has_all and selected_set == countries_set:
            return [], {'all_selected': False}
        
        # User clicked "(All)" to select everything
        if has_all and not all_selected:
            return ['All'] + AVAILABLE_COUNTRIES, {'all_selected': True}
        
        # User manually reached full selection without "(All)" checked
        if not has_all and selected_set == countries_set:
            return ['All'] + AVAILABLE_COUNTRIES, {'all_selected': True}
        
        # Regular multi-select - drop "(All)" if present
        cleaned = [v for v in selection if v != 'All']
        return cleaned, {'all_selected': False}

    @dash_app.callback(
        Output('imports-year-store', 'data'),
        Output('imports-year-dropdown', 'value'),
        Output('imports-year-slider', 'value'),
        Input('imports-year-dropdown', 'value'),
        Input('imports-year-slider', 'value'),
        Input('imports-year-prev', 'n_clicks'),
        Input('imports-year-next', 'n_clicks'),
        Input('imports-year-timeline-prev', 'n_clicks'),
        Input('imports-year-timeline-next', 'n_clicks'),
        Input('imports-year-interval', 'n_intervals'),
        State('imports-year-store', 'data'),
        State('imports-year-play-store', 'data'),
        prevent_initial_call=True
    )
    def sync_year_controls(drop_value, slider_value, prev_clicks, next_clicks,
                           timeline_prev, timeline_next, interval_tick,
                           current_year, is_playing):
        """Keep dropdown, slider, slider controls, and animation in sync"""
        triggered = dash.callback_context.triggered_id
        years_sorted = sorted(AVAILABLE_YEARS)
        year = current_year or DEFAULT_YEAR
        playing = bool(is_playing)
        
        def clamp(y):
            return max(YEAR_MIN, min(YEAR_MAX, y))
        
        def step(delta):
            if year in years_sorted:
                idx = years_sorted.index(year)
                new_idx = max(0, min(len(years_sorted) - 1, idx + delta))
                return years_sorted[new_idx]
            return clamp(year + delta)
        
        if triggered in ('imports-year-prev', 'imports-year-timeline-prev'):
            year = step(-1)
        elif triggered in ('imports-year-next', 'imports-year-timeline-next'):
            year = step(1)
        elif triggered == 'imports-year-dropdown':
            year = clamp(drop_value or year)
        elif triggered == 'imports-year-slider':
            year = clamp(slider_value or year)
        elif triggered == 'imports-year-interval' and playing:
            if year in years_sorted:
                idx = years_sorted.index(year)
                year = years_sorted[(idx + 1) % len(years_sorted)]
            else:
                year = clamp(year + 1)
        
        return year, year, year

    @dash_app.callback(
        Output('imports-year-play-store', 'data'),
        Output('imports-year-play-toggle', 'children'),
        Output('imports-year-interval', 'disabled'),
        Input('imports-year-play-toggle', 'n_clicks'),
        State('imports-year-play-store', 'data'),
        prevent_initial_call=True
    )
    def toggle_year_animation(_n_clicks, is_playing):
        """Toggle auto-play animation of the year slider"""
        playing = not bool(is_playing)
        label = '■' if playing else '▶'
        interval_disabled = not playing
        return playing, label, interval_disabled

    dash_app.clientside_callback(
        """
        function(_id) {
            try {
                const styleId = 'imports-table-selection-css';
                if (!document.getElementById(styleId)) {
                    const style = document.createElement('style');
                    style.id = styleId;
                    style.type = 'text/css';
                    style.innerHTML = `
#imports-annual-table .dash-spreadsheet-container,
#imports-matrix-table .dash-spreadsheet-container {
    cursor: pointer;
}
#imports-annual-table .dash-spreadsheet-container.imports-selection-active td:not([data-dash-column="Importer"]),
#imports-matrix-table .dash-spreadsheet-container.imports-selection-active td:not([data-dash-column="Exporter"]) {
    opacity: 0.18;
    transition: opacity 0.1s ease-in-out;
}
#imports-annual-table .dash-spreadsheet-container.imports-selection-active td.imports-cell-selected,
#imports-matrix-table .dash-spreadsheet-container.imports-selection-active td.imports-cell-selected,
#imports-annual-table .dash-spreadsheet-container.imports-selection-active td.imports-row-selected,
#imports-matrix-table .dash-spreadsheet-container.imports-selection-active td.imports-row-selected,
#imports-annual-table .dash-spreadsheet-container.imports-selection-active td.imports-column-selected,
#imports-matrix-table .dash-spreadsheet-container.imports-selection-active td.imports-column-selected {
    opacity: 1 !important;
}
#imports-annual-table .dash-spreadsheet-container td.imports-column-selected,
#imports-matrix-table .dash-spreadsheet-container td.imports-column-selected {
    background-color: #e6f1ff !important;
    color: #102a43 !important;
}
#imports-annual-table .dash-spreadsheet-container th.imports-column-label-selected,
#imports-matrix-table .dash-spreadsheet-container th.imports-column-label-selected {
    background-color: #ffd9d7 !important;
    color: white !important;
    font-weight: 600 !important;
}
#imports-annual-table .dash-spreadsheet-container td.imports-cell-selected,
#imports-matrix-table .dash-spreadsheet-container td.imports-cell-selected {
    background-color: #f7fbff !important;
    box-shadow: inset 0 0 0 2px #0075A8 !important;
    font-weight: 600;
    color: #1f2d3d !important;
}
#imports-annual-table .dash-spreadsheet-container td.imports-row-selected,
#imports-matrix-table .dash-spreadsheet-container td.imports-row-selected {
    background-color: #e6f1ff !important;
    color: #102a43 !important;
}
#imports-annual-table .dash-spreadsheet-container td.imports-row-label-selected,
#imports-matrix-table .dash-spreadsheet-container td.imports-row-label-selected {
    font-weight: 600;
    color: #102a43 !important;
}
#imports-annual-table .dash-spreadsheet-container td.imports-row-label-selected::before,
#imports-matrix-table .dash-spreadsheet-container td.imports-row-label-selected::before {
    content: '';
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #ffd9d7;
    margin-right: 8px;
    position: relative;
    top: -1px;
    box-shadow: 0 0 0 2px #ffffff;
}
#imports-footnotes {
    position: relative;
}
#imports-footnotes .footnote-item {
    cursor: pointer;
    transition: color 0.1s ease, opacity 0.1s ease;
    padding: 2px 0;
}
#imports-footnotes .footnote-item:hover {
    color: #1b365d;
}
#imports-footnotes.footnote-selection-active .footnote-item {
    opacity: 0.2;
}
#imports-footnotes .footnote-item.footnote-item-selected {
    color: #d35400;
    font-weight: 600;
    opacity: 1 !important;
}
#imports-footnotes .footnote-static {
    opacity: 0.9;
    padding: 2px 0;
}
                    `;
                    document.head.appendChild(style);
                }

                const TABLE_CONFIGS = [
                    { id: 'imports-annual-table', labelColumn: 'Importer' },
                    { id: 'imports-matrix-table', labelColumn: 'Exporter' }
                ];

                function resetSelectionClasses(spreadsheet) {
                    if (!spreadsheet) return;
                    spreadsheet.querySelectorAll('.imports-cell-selected, .imports-row-selected, .imports-row-label-selected, .imports-column-selected, .imports-column-label-selected').forEach(function(el) {
                        el.classList.remove('imports-cell-selected', 'imports-row-selected', 'imports-row-label-selected', 'imports-column-selected', 'imports-column-label-selected');
                    });
                }

                function clearSelection(spreadsheet) {
                    if (!spreadsheet) return;
                    resetSelectionClasses(spreadsheet);
                    spreadsheet.classList.remove('imports-selection-active');
                    spreadsheet.dataset.selectedKey = '';
                }

                function highlightEntireRow(spreadsheet, rowIndex, labelColumn) {
                    const rowCells = spreadsheet.querySelectorAll('td[data-dash-row=\"' + rowIndex + '\"]');
                    rowCells.forEach(function(rowCell) {
                        rowCell.classList.add('imports-row-selected');
                        if (rowCell.getAttribute('data-dash-column') === labelColumn) {
                            rowCell.classList.add('imports-row-label-selected');
                        }
                    });
                }

                function highlightEntireColumn(spreadsheet, columnId) {
                    const colCells = spreadsheet.querySelectorAll('td[data-dash-column=\"' + columnId + '\"]');
                    colCells.forEach(function(colCell) {
                        colCell.classList.add('imports-column-selected');
                    });
                    const headers = spreadsheet.querySelectorAll('th[data-dash-column=\"' + columnId + '\"]');
                    headers.forEach(function(header) {
                        header.classList.add('imports-column-label-selected');
                    });
                }

                function enhanceTable(tableId, labelColumn) {
                    const tableEl = document.getElementById(tableId);
                    if (!tableEl) return;
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    if (!spreadsheet || spreadsheet.dataset.importsSelectionBound === 'true') return;
                    spreadsheet.dataset.importsSelectionBound = 'true';
                    spreadsheet.dataset.selectedKey = '';

                    spreadsheet.addEventListener('click', function(event) {
                        const cell = event.target.closest('td[data-dash-row]');
                        const header = event.target.closest('th[data-dash-column]');

                        if (header) {
                            const columnId = header.getAttribute('data-dash-column');
                            if (!columnId || columnId === labelColumn) return;
                            const colKey = 'col-' + columnId;
                            if (spreadsheet.dataset.selectedKey === colKey) {
                                clearSelection(spreadsheet);
                            } else {
                                spreadsheet.dataset.selectedKey = colKey;
                                spreadsheet.classList.add('imports-selection-active');
                                resetSelectionClasses(spreadsheet);
                                highlightEntireColumn(spreadsheet, columnId);
                            }
                            return;
                        }

                        if (cell) {
                            const columnId = cell.getAttribute('data-dash-column');
                            const rowIndex = cell.getAttribute('data-dash-row');
                            if (!columnId || rowIndex === null) return;
                            const rowKey = 'row-' + rowIndex;
                            const cellKey = rowIndex + '-' + columnId;

                            if (columnId === labelColumn) {
                                if (spreadsheet.dataset.selectedKey === rowKey) {
                                    clearSelection(spreadsheet);
                                } else {
                                    spreadsheet.dataset.selectedKey = rowKey;
                                    spreadsheet.classList.add('imports-selection-active');
                                    resetSelectionClasses(spreadsheet);
                                    highlightEntireRow(spreadsheet, rowIndex, labelColumn);
                                }
                            } else {
                                if (spreadsheet.dataset.selectedKey === cellKey) {
                                    clearSelection(spreadsheet);
                                } else {
                                    spreadsheet.dataset.selectedKey = cellKey;
                                    spreadsheet.classList.add('imports-selection-active');
                                    resetSelectionClasses(spreadsheet);
                                    cell.classList.add('imports-cell-selected');
                                }
                            }
                        }
                    });
                }

                function clearFootnoteSelection(container) {
                    if (!container) {
                        return;
                    }
                    container.classList.remove('footnote-selection-active');
                    container.dataset.selectedKey = '';
                    container.querySelectorAll('.footnote-item').forEach(function(item) {
                        item.classList.remove('footnote-item-selected');
                    });
                }

                function initFootnoteSelection() {
                    const container = document.getElementById('imports-footnotes');
                    if (!container || container.dataset.footnoteEnhanced === 'true') {
                        return;
                    }
                    container.dataset.footnoteEnhanced = 'true';
                    container.dataset.selectedKey = '';

                    container.addEventListener('click', function(event) {
                        const item = event.target.closest('.footnote-item');
                        if (!item) {
                            return;
                        }
                        const key = item.getAttribute('data-note-key') || '';
                        if (!key) {
                            return;
                        }
                        if (container.dataset.selectedKey === key) {
                            clearFootnoteSelection(container);
                            return;
                        }
                        container.dataset.selectedKey = key;
                        container.classList.add('footnote-selection-active');
                        container.querySelectorAll('.footnote-item').forEach(function(node) {
                            node.classList.remove('footnote-item-selected');
                        });
                        item.classList.add('footnote-item-selected');
                    });

                    document.addEventListener('click', function(event) {
                        if (!container.contains(event.target)) {
                            clearFootnoteSelection(container);
                        }
                    });
                }

                function applyEnhancements() {
                    TABLE_CONFIGS.forEach(function(cfg) {
                        enhanceTable(cfg.id, cfg.labelColumn);
                    });
                    initFootnoteSelection();
                }

                if (!window.importsTablesMutationObserver) {
                    window.importsTablesMutationObserver = new MutationObserver(function() {
                        applyEnhancements();
                    });
                    window.importsTablesMutationObserver.observe(document.body, { childList: true, subtree: true });
                }

                if (!window.importsTablesOutsideClickHandler) {
                    window.importsTablesOutsideClickHandler = function(event) {
                        TABLE_CONFIGS.forEach(function(cfg) {
                            const tableEl = document.getElementById(cfg.id);
                            if (!tableEl || tableEl.contains(event.target)) {
                                return;
                            }
                            const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                            if (spreadsheet && spreadsheet.classList.contains('imports-selection-active')) {
                                clearSelection(spreadsheet);
                            }
                        });
                    };
                    document.addEventListener('click', window.importsTablesOutsideClickHandler);
                }

                applyEnhancements();
            } catch (error) {
                console.error('Imports table enhancer error:', error);
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('imports-table-enhancer-anchor', 'children'),
        Input('imports-table-enhancer-anchor', 'id'),
        prevent_initial_call=False
    )

    # CSV Export Callbacks
    @dash_app.callback(
        Output('download-global-imports-csv', 'data'),
        Input('export-global-imports-btn', 'n_clicks'),
        State('imports-year-store', 'data'),
        State('imports-country-checklist', 'value'),
        prevent_initial_call=True
    )
    def export_global_imports_csv(n_clicks, selected_year, selected_countries):
        """Export Global Crude Imports data to CSV"""
        if n_clicks and selected_year:
            # Load the same data used for the map
            df = load_imports_data(selected_year)
            
            if df.empty:
                # Return empty CSV if no data
                empty_df = pd.DataFrame(columns=['Year', 'Importer', 'Import_Volume'])
                filename = f"Global_Crude_Imports_{selected_year}.csv"
                return dcc.send_data_frame(empty_df.to_csv, filename=filename, index=False)
            
            # Filter by countries if not "All"
            if 'All' not in selected_countries and selected_countries:
                # Convert original country names to normalized names for filtering
                normalized_countries = [normalize_country_name(country) for country in selected_countries]
                df = df[df['Importer'].isin(normalized_countries)].copy()
            
            # Denormalize country names back to original for export
            df['Importer'] = df['Importer'].apply(denormalize_country_name)
            
            # Sort by import volume descending
            df = df.sort_values('Import_Volume', ascending=False)
            
            # Rename columns for export
            df_export = df.rename(columns={
                'Import_Volume': f"Import Volume {selected_year} ('000 b/d)"
            })
            
            filename = f"Global_Crude_Imports_{selected_year}.csv"
            return dcc.send_data_frame(df_export.to_csv, filename=filename, index=False)
        raise dash.exceptions.PreventUpdate

    @dash_app.callback(
        Output('download-annual-imports-csv', 'data'),
        Input('export-annual-imports-btn', 'n_clicks'),
        State('imports-country-checklist', 'value'),
        prevent_initial_call=True
    )
    def export_annual_imports_csv(n_clicks, selected_countries):
        """Export Annual Imports Volume data to CSV"""
        if n_clicks:
            # Load the same data used for the annual table
            df = load_annual_imports_data(selected_countries)
            
            if df.empty:
                # Return empty CSV if no data
                empty_df = pd.DataFrame(columns=['Importer', 'Year', 'Import_Volume'])
                filename = "Annual_Imports_Volume.csv"
                return dcc.send_data_frame(empty_df.to_csv, filename=filename, index=False)
            
            # Get available years (sorted descending)
            available_years = sorted(df['Year'].unique().tolist(), reverse=True)
            target_years = [y for y in range(2025, 2018, -1) if y in available_years]
            if not target_years:
                target_years = available_years
            
            # Create pivot table: countries as rows, years as columns
            df_pivot = df[df['Year'].isin(target_years)].pivot(
                index='Importer', 
                columns='Year', 
                values='Import_Volume'
            ).fillna(0)
            
            # Reorder columns to match year order (newest first)
            df_pivot = df_pivot.reindex(columns=target_years, fill_value=0)
            
            # Sort countries alphabetically
            df_pivot = df_pivot.sort_index()
            
            # Reset index to make Importer a column
            df_pivot = df_pivot.reset_index()
            df_pivot.columns.name = None
            
            # Add grand total row
            totals_row = {'Importer': 'Grand Total'}
            for year in target_years:
                totals_row[year] = df[df['Year'] == year]['Import_Volume'].sum()
            df_pivot = pd.concat([df_pivot, pd.DataFrame([totals_row])], ignore_index=True)
            
            # Rename year columns to include units
            rename_dict = {year: f"{year} ('000 b/d)" for year in target_years}
            df_pivot = df_pivot.rename(columns=rename_dict)
            
            filename = "Annual_Imports_Volume.csv"
            return dcc.send_data_frame(df_pivot.to_csv, filename=filename, index=False)
        raise dash.exceptions.PreventUpdate

    @dash_app.callback(
        Output('download-matrix-imports-csv', 'data'),
        Input('export-matrix-imports-btn', 'n_clicks'),
        State('imports-year-store', 'data'),
        State('imports-country-checklist', 'value'),
        prevent_initial_call=True
    )
    def export_matrix_imports_csv(n_clicks, selected_year, selected_countries):
        """Export Import-Export Matrix data to CSV"""
        if n_clicks and selected_year:
            # Load the same data used for the matrix table (with country filtering)
            df = load_import_export_matrix_data(selected_year, selected_countries)
            
            if df.empty:
                # Return empty CSV if no data
                empty_df = pd.DataFrame(columns=['Exporter'])
                filename = f"Import_Export_Matrix_{selected_year}.csv"
                return dcc.send_data_frame(empty_df.to_csv, filename=filename, index=False)
            
            # Get column order (all columns except 'Exporter')
            column_order = [col for col in df.columns if col != 'Exporter']
            column_order = sorted(column_order)
            
            # Add row totals (sum of all importers for each exporter)
            df = df.copy()
            df['Grand Total'] = df[column_order].sum(axis=1)
            
            # Add column totals (sum of all exporters for each importer)
            totals_row = {'Exporter': 'Grand Total'}
            for col in column_order:
                totals_row[col] = df[col].sum()
            totals_row['Grand Total'] = df[column_order].sum().sum()
            
            # Append totals row to dataframe
            df = pd.concat([df, pd.DataFrame([totals_row])], ignore_index=True)
            
            # Update column order to include Grand Total
            column_order_with_total = column_order + ['Grand Total']
            
            # Reorder columns: Exporter first, then importers, then Grand Total
            df = df[['Exporter'] + column_order_with_total]
            
            # Rename columns to include units and year
            rename_dict = {col: f"{col} {selected_year} ('000 b/d)" for col in column_order_with_total if col != 'Grand Total'}
            rename_dict['Grand Total'] = f"Grand Total {selected_year} ('000 b/d)"
            df = df.rename(columns=rename_dict)
            
            filename = f"Import_Export_Matrix_{selected_year}.csv"
            return dcc.send_data_frame(df.to_csv, filename=filename, index=False)
        raise dash.exceptions.PreventUpdate
