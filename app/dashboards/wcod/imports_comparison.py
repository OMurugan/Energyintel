"""
Imports - Country Comparison View
Global Crude Imports Dashboard - Based on Tableau design
"""
import json
from urllib.request import urlopen
import dash
from dash import dcc, html, Input, Output, State, callback, dash_table, no_update
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from core.data_helpers import execute_query
from config import Config

# Set Mapbox access token
if Config.MAPBOX_ACCESS_TOKEN:
    px.set_mapbox_access_token(Config.MAPBOX_ACCESS_TOKEN)

# Country to ISO-3 mapping for Mapbox
COUNTRY_TO_ISO = {
    "United States": "USA",
    "United Kingdom": "GBR",
    "Saudi Arabia": "SAU",
    "Russia": "RUS",
    "China": "CHN",
    "India": "IND",
    "Brazil": "BRA",
    "Canada": "CAN",
    "Mexico": "MEX",
    "Venezuela": "VEN",
    "Nigeria": "NGA",
    "Angola": "AGO",
    "Algeria": "DZA",
    "Libya": "LBY",
    "Iraq": "IRQ",
    "Iran": "IRN",
    "Kuwait": "KWT",
    "United Arab Emirates": "ARE",
    "Qatar": "QAT",
    "Norway": "NOR",
    "Kazakhstan": "KAZ",
    "Azerbaijan": "AZE",
    "Indonesia": "IDN",
    "Malaysia": "MYS",
    "Thailand": "THA",
    "Vietnam": "VNM",
    "Australia": "AUS",
    "Colombia": "COL",
    "Ecuador": "ECU",
    "Argentina": "ARG",
    "Chile": "CHL",
    "Peru": "PER",
    "Egypt": "EGY",
    "Sudan": "SDN",
    "South Sudan": "SSD",
    "Gabon": "GAB",
    "Congo": "COG",
    "Republic of the Congo": "COG",
    "Equatorial Guinea": "GNQ",
    "Cameroon": "CMR",
    "Ghana": "GHA",
    "Côte d'Ivoire": "CIV",
    "Cote d'Ivoire": "CIV",
    "Ivory Coast": "CIV",
    "Tunisia": "TUN",
    "Oman": "OMN",
    "Yemen": "YEM",
    "Turkmenistan": "TKM",
    "Uzbekistan": "UZB",
    "Georgia": "GEO",
    "Turkey": "TUR",
    "Greece": "GRC",
    "Italy": "ITA",
    "Spain": "ESP",
    "France": "FRA",
    "Germany": "DEU",
    "Netherlands": "NLD",
    "Belgium": "BEL",
    "Denmark": "DNK",
    "Sweden": "SWE",
    "Finland": "FIN",
    "Poland": "POL",
    "Romania": "ROU",
    "Bulgaria": "BGR",
    "Ukraine": "UKR",
    "Japan": "JPN",
    "South Korea": "KOR",
    "Philippines": "PHL",
    "Singapore": "SGP",
    "Brunei": "BRN"
}

try:
    import pycountry
except Exception:
    pycountry = None

def _iso_for_country(country):
    """Return ISO Alpha-3 code for a country, using custom map then pycountry."""
    if not country:
        return None
    country_clean = str(country).strip()
    if not country_clean:
        return None
    if country_clean in COUNTRY_TO_ISO:
        return COUNTRY_TO_ISO[country_clean]
    if pycountry:
        try:
            match = pycountry.countries.search_fuzzy(country_clean)
            if match:
                return match[0].alpha_3
        except Exception:
            pass
    return None

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
MAP_BACKGROUND_COLOR = '#d6e1eb'
MAP_LAND_COLOR = '#f4f4f4'

# Load data
def load_imports_data(selected_year=2023):
    """Load imports comparison data from database"""
    try:
        query = """
        SELECT
            EXTRACT(YEAR FROM yr)::INT AS "Year",
            import_country AS "Importer",
            SUM(vol_kbpd) AS "DataValue"
        FROM dev.fact_wcod_imports
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
        
        # Filter out zero values for better visualization
        df = df[df['Import_Volume'] > 0].copy()
        
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
            EXTRACT(YEAR FROM yr)::INT AS "Year",
            import_country AS "Importer",
            SUM(vol_kbpd) AS "DataValue"
        FROM dev.fact_wcod_imports
        WHERE
            (import_country NOT IN ('Australia', 'Japan', 'South Korea', 'United States')
            OR source <> 'OECD Imports')
        """
        
        params = {}
        
        # Add country filter if countries are specified (filter out 'All' if present)
        if selected_countries:
            # Remove 'All' from the list if present
            countries_to_filter = [c for c in selected_countries if c != 'All']
            
            if countries_to_filter:
                if len(countries_to_filter) == 1:
                    # Single country - use = operator
                    base_query += " AND import_country = :import_country"
                    params['import_country'] = countries_to_filter[0]
                else:
                    # Multiple countries - use IN clause
                    placeholders = ", ".join([f":country_{i}" for i in range(len(countries_to_filter))])
                    base_query += f" AND import_country IN ({placeholders})"
                    params = {f"country_{i}": country for i, country in enumerate(countries_to_filter)}
        
        base_query += """
        GROUP BY
            EXTRACT(YEAR FROM yr),
            import_country
        ORDER BY
            "Year",
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


def load_import_export_matrix_data(selected_year=2023):
    """Load Import – Export Matrix data from database (single-year snapshot)"""
    try:
        query = """
        SELECT
            EXTRACT(YEAR FROM yr)::INT AS "Year",
            import_country AS "Importer",
            export_country AS "Exporter",
            SUM(vol_kbpd) AS "DataValue"
        FROM dev.fact_wcod_imports
        WHERE
            EXTRACT(YEAR FROM yr) = :selected_year
            AND (
                import_country NOT IN ('Australia', 'Japan', 'South Korea', 'United States')
                OR source <> 'OECD Imports'
            )
        GROUP BY
            EXTRACT(YEAR FROM yr),
            import_country,
            export_country
        ORDER BY
            "Year",
            "Importer",
            "Exporter";
        """
        
        rows = execute_query(query, {'selected_year': selected_year})
        
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
        FROM dev.fact_wcod_imports
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
        FROM dev.fact_wcod_imports
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
        FROM dev.dim_country
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


YEAR_SLIDER_MARKS = build_year_marks(AVAILABLE_YEARS)

def create_layout():
    """Create the Imports - Country Comparison layout matching Tableau design"""
    return html.Div([
        dcc.Store(id='imports-year-store', data=DEFAULT_YEAR),
        dcc.Store(id='imports-year-play-store', data=False),
        dcc.Store(id='imports-country-store', data={'all_selected': True}),
        dcc.Store(id='imports-map-clicked-country', data=None),  # Store clicked country from map
        dcc.Interval(id='imports-year-interval', interval=2000, disabled=True),
        # Instruction text
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
        ),
        # Main title
        html.H2(
            "Global Crude Imports",
            style={
                'color': '#d35400',  # Orange color
                'textAlign': 'center',
                'marginBottom': '25px',
                'fontSize': '20px',
                'fontWeight': 'bold',
                'letterSpacing': '0.5px',
                'textTransform': 'uppercase'
            }
        ),
        # Main content area
        html.Div([
            # Map area (left, larger)
            html.Div([
                dcc.Graph(
                    id='imports-world-map',
                    config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        # Geo-specific controls (home/reset + zoom)
                        'modeBarButtonsToAdd': [
                            'zoomInGeo',
                            'zoomOutGeo',
                            'resetGeo',
                            'resetScale2d'  # home-style reset icon
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
                            'accentColor': '#1a4a83',
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
                            'color': '#1a4a83',
                            'fontWeight': 'bold'
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
            html.H3(
                "Annual Imports Volume ('000 b/d)",
                style={
                    'color': '#d35400',
                    'textAlign': 'center',
                    'marginTop': '30px',
                    'marginBottom': '15px',
                    'fontSize': '20px',
                    'fontWeight': 'bold'
                }
            ),
            html.Div(
                id='imports-annual-table-container',
                children=[]
            ),
            html.P(
                id='imports-matrix-caption',
                children="Import – Export Matrix ('000 b/d)",
                style={
                    'textAlign': 'center',
                    'fontWeight': 'bold',
                    'color': '#d35400',
                    'marginTop': '15px',
                    'marginBottom': '0'
                }
            ),
            html.Div(
                id='imports-matrix-table-container',
                children=[],
                style={'marginTop': '10px'}
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
        State('imports-map-clicked-country', 'data'),
        prevent_initial_call=True
    )
    def handle_map_click(clickData, current_clicked_country):
        """Handle map click to store clicked country and update checklist.
        If clicking the same country again, deselect it and return to original state.
        For Mapbox, clickData contains ISO codes in 'location' or country names in 'customdata'."""
        if clickData and 'points' in clickData and len(clickData['points']) > 0:
            point = clickData['points'][0]
            clicked_country = None
            
            # Try to get country from customdata first (contains original country name)
            if 'customdata' in point and point['customdata']:
                customdata = point['customdata']
                if isinstance(customdata, list) and len(customdata) > 0:
                    clicked_country = customdata[0]  # First element is country name
                elif isinstance(customdata, str):
                    clicked_country = customdata
            # Fallback: try to get from location (ISO code) - need to map back to country
            elif 'location' in point and point['location']:
                iso_code = point['location']
                # Use reverse mapping from COUNTRY_TO_ISO
                iso_to_country_reverse = {v: k for k, v in COUNTRY_TO_ISO.items()}
                clicked_country = iso_to_country_reverse.get(iso_code)
                # If not found in mapping, try to get from all_countries_df
                if not clicked_country:
                    all_countries_df = get_all_countries_with_coordinates()
                    if not all_countries_df.empty and 'ISO_Code' in all_countries_df.columns:
                        iso_to_country = dict(zip(all_countries_df['ISO_Code'], all_countries_df['Country']))
                        clicked_country = iso_to_country.get(iso_code)
            
            if clicked_country:
                # Check if the country exists in available countries
                if clicked_country in AVAILABLE_COUNTRIES:
                    # If clicking the same country that's already selected, deselect it (return to original)
                    if current_clicked_country == clicked_country:
                        # Return to original state: clear clicked country and select all countries
                        return None, ['All'] + AVAILABLE_COUNTRIES
                    else:
                        # Select only the clicked country in the checklist (deselect all others)
                        return clicked_country, [clicked_country]
                return clicked_country, no_update
        return None, no_update
    
    @dash_app.callback(
        [Output('imports-world-map', 'figure'),
         Output('imports-annual-table-container', 'children'),
         Output('imports-matrix-table-container', 'children'),
         Output('imports-max-value', 'children'),
         Output('imports-mid-value', 'children'),
         Output('imports-matrix-caption', 'children')],
        [Input('imports-year-store', 'data'),
         Input('imports-country-checklist', 'value'),
         Input('imports-map-clicked-country', 'data')]
    )
    def update_imports_dashboard(selected_year, selected_countries, clicked_country):
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
        if 'All' not in selected_countries and selected_countries:
            # Convert original country names to normalized names for map filtering
            # Map data already has normalized names, so we need to normalize the selected countries
            normalized_countries = [normalize_country_name(country) for country in selected_countries]
            df_filtered = df_filtered[df_filtered['Importer'].isin(normalized_countries)].copy()
        
        # Create map
        if df_filtered.empty:
            map_fig = go.Figure()
            map_fig.add_annotation(
                text="No data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False
            )
            map_fig.update_layout(height=600, plot_bgcolor='white', paper_bgcolor='white')
        else:
            # Aggregate by country (sum if multiple entries)
            df_map = df_filtered.groupby('Importer')['Import_Volume'].sum().reset_index()
            df_map.columns = ['Country', 'Import_Volume']
            # Store original country names before normalization for matching
            df_map['Country_Original'] = df_map['Country'].copy()
            # Ensure country names are normalized
            df_map['Country'] = df_map['Country'].apply(normalize_country_name)
            
            # Create choropleth map
            max_volume = df_map['Import_Volume'].max() if len(df_map) > 0 else 1
            # Add year column for hover
            df_map['Year'] = selected_year
            
            # Load GeoJSON and all countries data for Mapbox
            geojson = _load_world_geojson()
            all_countries_df = get_all_countries_with_coordinates()
            
            # Create mapping from country names to ISO-3 codes using _iso_for_country function
            # This ensures we get proper ISO-3 codes that match the GeoJSON
            df_map['ISO_Code'] = df_map['Country_Original'].apply(_iso_for_country)
            # Filter out any countries without valid ISO-3 codes
            df_map = df_map.dropna(subset=['ISO_Code']).copy()
            # Ensure ISO codes are strings and exactly 3 characters
            if not df_map.empty:
                df_map['ISO_Code'] = df_map['ISO_Code'].astype(str)
                df_map = df_map[df_map['ISO_Code'].str.len() == 3].copy()
            
            # Handle clicked country highlighting
            # clicked_country is the original country name from AVAILABLE_COUNTRIES
            clicked_country_original = None
            if clicked_country and not df_map.empty:
                # Get ISO code for the clicked country
                clicked_iso = _iso_for_country(clicked_country)
                # Check if we have a valid ISO code
                if clicked_iso and len(str(clicked_iso)) == 3:
                    clicked_iso_str = str(clicked_iso)
                    # Check if this ISO code exists in our filtered map data (compare as strings)
                    matching_iso_rows = df_map[df_map['ISO_Code'].astype(str) == clicked_iso_str]
                    if not matching_iso_rows.empty:
                        # Found a match by ISO code - use the country name from the data
                        clicked_country_original = matching_iso_rows.iloc[0]['Country_Original']
                    else:
                        # Try matching by country name (case-insensitive)
                        matching_name_rows = df_map[df_map['Country_Original'].str.strip().str.lower() == str(clicked_country).strip().lower()]
                        if not matching_name_rows.empty:
                            clicked_country_original = matching_name_rows.iloc[0]['Country_Original']
            
            if geojson is None:
                # Fallback to empty map if no GeoJSON
                map_fig = go.Figure()
                map_fig.add_annotation(
                    text="No GeoJSON data available for map display",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5,
                    showarrow=False
                )
                map_fig.update_layout(height=550, plot_bgcolor='white', paper_bgcolor='white')
            elif df_map.empty:
                # No valid countries with ISO-3 codes
                map_fig = go.Figure()
                map_fig.add_annotation(
                    text="No countries with valid ISO codes for map display",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5,
                    showarrow=False
                )
                map_fig.update_layout(height=550, plot_bgcolor='white', paper_bgcolor='white')
            else:
                # Create Mapbox choropleth map
                map_fig = go.Figure()
                
                if clicked_country_original:
                    # Dimmed base map for all countries - filter to only valid ISO-3 codes
                    df_map_valid = df_map.copy()  # Already filtered to valid ISO codes
                    if not df_map_valid.empty:
                        map_fig.add_trace(go.Choroplethmapbox(
                            geojson=geojson,
                            locations=df_map_valid['ISO_Code'].tolist(),
                            z=df_map_valid['Import_Volume'].tolist(),
                            featureidkey="id",
                            colorscale=MAP_COLOR_SCALE,
                            zmin=0,
                            zmax=max_volume,
                            marker=dict(line=dict(color='#ffffff', width=0.5), opacity=0.3),
                            showscale=False,
                            hovertemplate="<b>Importer:</b> %{customdata[0]}<br>" \
                                          "<b>Year:</b> %{customdata[1]}<br>" \
                                          "<b>Traded Volume:</b> %{z:,.0f}('000 b/d)<extra></extra>",
                            customdata=[[c, selected_year] for c in df_map_valid['Country_Original']],
                            hoverlabel=dict(bgcolor='white', font_color='#1b365d', bordercolor='#99a6b8',
                                           font_size=12, font_family='Arial, sans-serif')
                        ))
                    
                    # Highlighted country - add on top with full opacity and black border
                    df_highlighted = df_map[df_map['Country_Original'] == clicked_country_original].copy()
                    if not df_highlighted.empty:
                        map_fig.add_trace(go.Choroplethmapbox(
                            geojson=geojson,
                            locations=df_highlighted['ISO_Code'].tolist(),
                            z=df_highlighted['Import_Volume'].tolist(),
                            featureidkey="id",
                            colorscale=MAP_COLOR_SCALE,
                            zmin=0,
                            zmax=max_volume,
                            marker=dict(line=dict(color='#000000', width=3), opacity=1.0),
                            showscale=False,
                            hovertemplate="<b>Importer:</b> %{customdata[0]}<br>" \
                                          "<b>Year:</b> %{customdata[1]}<br>" \
                                          "<b>Traded Volume:</b> %{z:,.0f}('000 b/d)<br>" \
                                          "<b>(Selected)</b><extra></extra>",
                            customdata=[[c, selected_year] for c in df_highlighted['Country_Original']],
                            hoverlabel=dict(bgcolor='white', font_color='#1b365d', bordercolor='#000000',
                                           font_size=12, font_family='Arial, sans-serif')
                        ))
                else:
                    # Normal map - already filtered to valid ISO-3 codes
                    df_map_valid = df_map.copy()
                    if not df_map_valid.empty:
                        map_fig.add_trace(go.Choroplethmapbox(
                            geojson=geojson,
                            locations=df_map_valid['ISO_Code'].tolist(),
                            z=df_map_valid['Import_Volume'].tolist(),
                            featureidkey="id",
                            colorscale=MAP_COLOR_SCALE,
                            zmin=0,
                            zmax=max_volume,
                            marker=dict(line=dict(color='#ffffff', width=0.5)),
                            showscale=False,
                            hovertemplate="<b>Importer:</b> %{customdata[0]}<br>" \
                                          "<b>Year:</b> %{customdata[1]}<br>" \
                                          "<b>Traded Volume:</b> %{z:,.0f}('000 b/d)<extra></extra>",
                            customdata=[[c, selected_year] for c in df_map_valid['Country_Original']],
                            hoverlabel=dict(bgcolor='white', font_color='#1b365d', bordercolor='#99a6b8',
                                           font_size=12, font_family='Arial, sans-serif')
                        ))
                
                # Add ALL country labels (not just import countries)
                if not all_countries_df.empty:
                    map_fig.add_trace(go.Scattermapbox(
                        lat=all_countries_df['Latitude'].tolist(),
                        lon=all_countries_df['Longitude'].tolist(),
                        mode='text',
                        text=all_countries_df['Country'].tolist(),
                        textfont=dict(size=9, color='#2c3e50', family='Arial'),
                        textposition='top center',
                        hoverinfo='skip',
                        showlegend=False
                    ))
                
                # Update layout with Mapbox
                mapbox_layout = dict(
                    style="carto-positron",
                    center=dict(lat=24.0, lon=45.0),
                    zoom=1.5
                )
                if Config.MAPBOX_ACCESS_TOKEN:
                    mapbox_layout["accesstoken"] = Config.MAPBOX_ACCESS_TOKEN
                
                map_fig.update_layout(
                    margin=dict(l=20, r=20, t=20, b=80),
                    height=550,
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    mapbox=mapbox_layout,
                    uirevision='imports-map'
                )
                
                # Add copyright annotation
                map_fig.add_annotation(
                    text="© 2025 Mapbox © OpenStreetMap",
                    xref="paper", yref="paper",
                    x=0.01, y=0.01,
                    showarrow=False,
                    font=dict(size=10, color='#666'),
                    bgcolor='rgba(255,255,255,0.8)',
                    bordercolor='rgba(255,255,255,0.8)'
                )
        
        # Create annual table using database query with dynamic country filtering
        # Load annual imports data based on selected countries
        df_annual = load_annual_imports_data(selected_countries)
        
        if df_annual.empty:
            annual_table = html.Div("No data available", style={'padding': '20px', 'textAlign': 'center', 'color': '#666'})
        else:
            
            if df_annual.empty:
                annual_table = html.Div("No data available for selected countries", style={'padding': '20px', 'textAlign': 'center', 'color': '#666'})
            else:
                # Get available years (sorted descending: 2025, 2024, 2023, etc.)
                available_years = sorted(df_annual['Year'].unique().tolist(), reverse=True)
                
                # Limit to recent years (2019-2025) as shown in the reference
                target_years = [y for y in range(2025, 2018, -1) if y in available_years]
                if not target_years:
                    target_years = available_years
                
                # Create pivot table: countries as rows, years as columns
                df_annual_pivot = df_annual[df_annual['Year'].isin(target_years)].pivot(
                    index='Importer', 
                    columns='Year', 
                    values='Import_Volume'
                ).fillna(0)
                
                # Reorder columns to match year order (newest first: 2025, 2024, 2023, etc.)
                df_annual_pivot = df_annual_pivot.reindex(columns=target_years, fill_value=0)
                
                # Sort countries alphabetically
                df_annual_pivot = df_annual_pivot.sort_index()
                
                # Reset index to make Importer a column
                df_annual_pivot = df_annual_pivot.reset_index()
                df_annual_pivot.columns.name = None
                
                # Append grand total row
                totals_row = {'Importer': 'Grand Total'}
                for year in target_years:
                    totals_row[year] = df_annual[df_annual['Year'] == year]['Import_Volume'].sum()
                df_annual_pivot = pd.concat([df_annual_pivot, pd.DataFrame([totals_row])], ignore_index=True)
                
                # Prepare columns for DataTable
                columns = [{'name': 'Importer', 'id': 'Importer'}] + [
                    {'name': str(year), 'id': str(year), 'type': 'numeric', 'format': {'specifier': ',.0f'}}
                    for year in target_years
                ]
                
                # Prepare data
                data = df_annual_pivot.to_dict('records')
                
                # Format numeric values in data
                for record in data:
                    for year in target_years:
                        val = record.pop(year, None)
                        if val is None or pd.isna(val) or val == 0:
                            record[str(year)] = ''
                        else:
                            record[str(year)] = f"{val:,.0f}"
                
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
                        }
                    ],
                    fixed_rows={'headers': True},
                    page_action='none',
                    sort_action='none',
                    filter_action='none',
                    merge_duplicate_headers=True
                )

        # Load matrix data dynamically for the selected year
        IMPORT_EXPORT_MATRIX_DF = load_import_export_matrix_data(selected_year)
        
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
        
        # Get max value for legend
        if df_filtered.empty:
            max_value = 0
        else:
            max_value = df_filtered.groupby('Importer')['Import_Volume'].sum().max()
        
        max_value_str = f"{max_value:,.0f}" if max_value > 0 else "0"
        mid_value_str = f"{(max_value / 2):,.0f}" if max_value > 0 else "0"
        
        return map_fig, annual_table, matrix_table, max_value_str, mid_value_str, matrix_caption
    
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
    transition: opacity 0.2s ease-in-out;
}
#imports-annual-table .dash-spreadsheet-container.imports-selection-active td.imports-cell-selected,
#imports-matrix-table .dash-spreadsheet-container.imports-selection-active td.imports-cell-selected,
#imports-annual-table .dash-spreadsheet-container.imports-selection-active td.imports-row-selected,
#imports-matrix-table .dash-spreadsheet-container.imports-selection-active td.imports-row-selected {
    opacity: 1 !important;
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
    background-color: #fe5000;
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
    transition: color 0.2s ease, opacity 0.2s ease, background-color 0.2s ease;
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
                    if (!spreadsheet) {
                        return;
                    }
                    spreadsheet.querySelectorAll('.imports-cell-selected').forEach(function(cell) {
                        cell.classList.remove('imports-cell-selected');
                    });
                    spreadsheet.querySelectorAll('.imports-row-selected').forEach(function(cell) {
                        cell.classList.remove('imports-row-selected');
                    });
                    spreadsheet.querySelectorAll('.imports-row-label-selected').forEach(function(cell) {
                        cell.classList.remove('imports-row-label-selected');
                    });
                }

                function clearSelection(spreadsheet) {
                    if (!spreadsheet) {
                        return;
                    }
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

                function enhanceTable(tableId, labelColumn) {
                    const tableEl = document.getElementById(tableId);
                    if (!tableEl) {
                        return;
                    }
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    if (!spreadsheet || spreadsheet.dataset.importsSelectionBound === 'true') {
                        return;
                    }
                    spreadsheet.dataset.importsSelectionBound = 'true';
                    spreadsheet.dataset.selectedKey = '';

                    spreadsheet.addEventListener('click', function(event) {
                        const cell = event.target.closest('td[data-dash-row]');
                        if (!cell) {
                            return;
                        }
                        const columnId = cell.getAttribute('data-dash-column');
                        const rowIndex = cell.getAttribute('data-dash-row');
                        if (!columnId || rowIndex === null) {
                            return;
                        }

                        const rowKey = 'row-' + rowIndex;
                        const cellKey = rowIndex + '-' + columnId;

                        if (columnId === labelColumn) {
                            if (spreadsheet.dataset.selectedKey === rowKey) {
                                clearSelection(spreadsheet);
                                return;
                            }
                            spreadsheet.dataset.selectedKey = rowKey;
                            spreadsheet.classList.add('imports-selection-active');
                            resetSelectionClasses(spreadsheet);
                            highlightEntireRow(spreadsheet, rowIndex, labelColumn);
                            return;
                        }

                        if (spreadsheet.dataset.selectedKey === cellKey) {
                            clearSelection(spreadsheet);
                            return;
                        }

                        spreadsheet.dataset.selectedKey = cellKey;
                        spreadsheet.classList.add('imports-selection-active');
                        resetSelectionClasses(spreadsheet);
                        cell.classList.add('imports-cell-selected');
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
