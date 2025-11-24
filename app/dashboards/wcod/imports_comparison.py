"""
Imports - Country Comparison View
Global Crude Imports Dashboard - Based on Tableau design
"""
import dash
from dash import dcc, html, Input, Output, State, callback
import dash_table
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os
from app import db
from app.models import Country, Imports
from sqlalchemy import func

# Define data path
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'Trade')
COMPARISON_MAP_CSV = os.path.join(DATA_DIR, 'comparison_map.csv')
ANNUAL_IMPORTS_CSV = os.path.join(DATA_DIR, 'comparison_Yearly Imports_data.csv')
IMPORT_EXPORT_MATRIX_CSV = os.path.join(DATA_DIR, 'Import-Export Matrix_data.csv')
IMPORT_EXPORT_MATRIX_YEAR = 2023

# Styling constants to match Energy Intelligence design
MAP_COLOR_SCALE = [
    (0.0, '#d9dee7'),
    (0.2, '#c5cedd'),
    (0.4, '#a0b9cf'),
    (0.6, '#799dc0'),
    (0.8, '#4f76a4'),
    (1.0, '#1f3f70')
]
MAP_BACKGROUND_COLOR = '#d6e1eb'
MAP_LAND_COLOR = '#f4f4f4'

# Load data
def load_imports_data():
    """Load imports comparison data from CSV"""
    try:
        df = pd.read_csv(COMPARISON_MAP_CSV, encoding='utf-16', sep='\t', skiprows=2)
        df.columns = ['Importer', 'Year', 'Import_Volume']
        
        # Clean the data
        df = df[df['Importer'].notna()].copy()
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
        df = df[df['Year'].notna()].copy()
        
        # Clean import volume - remove commas and convert to numeric
        df['Import_Volume'] = df['Import_Volume'].astype(str).str.replace(',', '').str.strip()
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
def load_annual_imports_data():
    """Load annual imports data from CSV"""
    try:
        df = pd.read_csv(ANNUAL_IMPORTS_CSV, encoding='utf-8')
        df.columns = df.columns.str.strip()
        
        # Rename columns
        if 'Year of Year' in df.columns:
            df = df.rename(columns={'Year of Year': 'Year', 'DataValue': 'Import_Volume'})
        
        # Clean the data
        df = df[df['Importer'].notna()].copy()
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
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


def load_import_export_matrix_data():
    """Load Import – Export Matrix data (single-year snapshot)"""
    try:
        df = pd.read_csv(
            IMPORT_EXPORT_MATRIX_CSV,
            encoding='utf-16',
            sep='\t',
            skiprows=3
        )
        df.columns = df.columns.str.strip()
        if 'Exporter' not in df.columns:
            return pd.DataFrame()

        df = df[df['Exporter'].notna()].copy()

        numeric_cols = [col for col in df.columns if col != 'Exporter']
        for col in numeric_cols:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(',', '', regex=False)
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df[numeric_cols] = df[numeric_cols].fillna(0)
        return df
    except Exception as e:
        print(f"Error loading import-export matrix data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

# Load data on module import
IMPORTS_DF = load_imports_data()
ANNUAL_IMPORTS_DF = load_annual_imports_data()
IMPORT_EXPORT_MATRIX_DF = load_import_export_matrix_data()
MATRIX_COLUMN_ORDER = [
    col for col in IMPORT_EXPORT_MATRIX_DF.columns if col != 'Exporter'
] if not IMPORT_EXPORT_MATRIX_DF.empty else []

# Normalize country names in the dataframes
if not IMPORTS_DF.empty:
    IMPORTS_DF['Importer'] = IMPORTS_DF['Importer'].apply(normalize_country_name)
if not ANNUAL_IMPORTS_DF.empty:
    # Keep original country names for annual table (don't normalize for display)
    pass

def get_available_years():
    """Get continuous list of available years across all datasets"""
    years = set()
    if not IMPORTS_DF.empty:
        years.update(IMPORTS_DF['Year'].dropna().astype(int).tolist())
    if not ANNUAL_IMPORTS_DF.empty:
        years.update(ANNUAL_IMPORTS_DF['Year'].dropna().astype(int).tolist())
    if years:
        year_min, year_max = min(years), max(years)
        return list(range(year_min, year_max + 1))
    return list(range(2000, 2026))

def get_available_countries():
    """Get list of available countries - use original names from annual imports CSV"""
    if not ANNUAL_IMPORTS_DF.empty:
        countries = sorted(ANNUAL_IMPORTS_DF['Importer'].unique().tolist())
        return countries
    elif not IMPORTS_DF.empty:
        # Fallback to map data countries
        countries = sorted(IMPORTS_DF['Importer'].unique().tolist())
        return countries
    return []

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
                        'displayModeBar': False,
                        'scrollZoom': True,
                        'doubleClick': 'reset'
                    },
                    style={
                        'height': '640px',
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
                    marks=YEAR_SLIDER_MARKS,
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
                children=f"Import – Export Matrix for {IMPORT_EXPORT_MATRIX_YEAR} ('000 b/d)",
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
        [Output('imports-world-map', 'figure'),
         Output('imports-annual-table-container', 'children'),
         Output('imports-matrix-table-container', 'children'),
         Output('imports-max-value', 'children'),
         Output('imports-mid-value', 'children'),
         Output('imports-matrix-caption', 'children')],
        [Input('imports-year-store', 'data'),
         Input('imports-country-checklist', 'value')]
    )
    def update_imports_dashboard(selected_year, selected_countries):
        """Update map and annual chart based on filters"""
        matrix_caption = f"Import – Export Matrix for {IMPORT_EXPORT_MATRIX_YEAR} ('000 b/d)"
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
                '0',
                '0',
                matrix_caption
            )
        
        # Filter by year
        df_filtered = IMPORTS_DF[IMPORTS_DF['Year'] == selected_year].copy()
        if df_filtered.empty and not ANNUAL_IMPORTS_DF.empty:
            fallback_df = ANNUAL_IMPORTS_DF[ANNUAL_IMPORTS_DF['Year'] == selected_year].copy()
            if not fallback_df.empty:
                fallback_df['Importer'] = fallback_df['Importer'].apply(normalize_country_name)
                df_filtered = fallback_df.rename(columns={'Importer': 'Importer', 'Import_Volume': 'Import_Volume'})
        
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
            # Ensure country names are normalized
            df_map['Country'] = df_map['Country'].apply(normalize_country_name)
            
            # Create choropleth map
            max_volume = df_map['Import_Volume'].max() if len(df_map) > 0 else 1
            # Add year column for hover
            df_map['Year'] = selected_year
            map_fig = px.choropleth(
                df_map,
                locations='Country',
                locationmode='country names',
                color='Import_Volume',
                projection='equirectangular',
                color_continuous_scale=MAP_COLOR_SCALE,
                labels={'Import_Volume': "Import Volume ('000 b/d)"},
                hover_data={'Year': True, 'Import_Volume': ':,.0f'},
                range_color=[0, max_volume]
            )
            # Customize hover template and styling to match Energy Intelligence design
            map_fig.update_traces(
                hovertemplate="<b>Importer:</b> %{location}<br>"
                              "<b>Year:</b> %{customdata[0]}<br>"
                              "<b>Traded Volume:</b> %{z}('000 b/d)<extra></extra>",
                hoverlabel=dict(
                    bgcolor='white',
                    font_color='#1b365d',
                    bordercolor='#99a6b8',
                    font_size=12,
                    font_family='Arial, sans-serif'
                )
            )
            map_fig.update_layout(
                margin=dict(l=20, r=20, t=20, b=80),
                height=640,
                plot_bgcolor=MAP_BACKGROUND_COLOR,
                paper_bgcolor=MAP_BACKGROUND_COLOR,
                dragmode='zoom',
                uirevision='imports-map',
                geo=dict(
                    bgcolor=MAP_BACKGROUND_COLOR,
                    showframe=False,
                    showcoastlines=True,
                    projection_type='equirectangular',
                    projection=dict(
                        type='equirectangular',
                        scale=1.02,
                        rotation=dict(lon=0, lat=0)
                    ),
                    lonaxis=dict(range=[-180, 180], showgrid=False, dtick=30),
                    lataxis=dict(range=[-65, 85], showgrid=False, dtick=30),
                    center=dict(lon=0, lat=15),
                    visible=True,
                    domain=dict(x=[0, 1], y=[0, 1]),
                    showland=True,
                    showocean=True,
                    showlakes=True,
                    showrivers=False,
                    coastlinewidth=0.5,
                    countrywidth=0.5,
                    showcountries=True,
                    countrycolor='#9aa7bb',
                    landcolor=MAP_LAND_COLOR,
                    oceancolor=MAP_BACKGROUND_COLOR
                ),
                coloraxis_showscale=False,
                newshape=dict(line_color='#2f4f6f')
            )
            map_fig.update_coloraxes(colorscale=MAP_COLOR_SCALE, cmin=0, cmax=max_volume if max_volume > 0 else 1)
            map_fig.update_traces(marker_line_color='#ffffff', marker_line_width=0.5)
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
        
        # Create annual table using the annual imports CSV data
        if ANNUAL_IMPORTS_DF.empty:
            annual_table = html.Div("No data available", style={'padding': '20px', 'textAlign': 'center', 'color': '#666'})
        else:
            # Filter by selected countries if not "All"
            # The checklist uses original country names (from annual CSV)
            if 'All' in selected_countries or not selected_countries:
                df_annual = ANNUAL_IMPORTS_DF.copy()
            else:
                df_annual = ANNUAL_IMPORTS_DF[ANNUAL_IMPORTS_DF['Importer'].isin(selected_countries)].copy()
            
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

        if IMPORT_EXPORT_MATRIX_DF.empty:
            matrix_table = html.Div(
                "Import – Export matrix data unavailable",
                style={'padding': '20px', 'textAlign': 'center', 'color': '#666'}
            )
        else:
            matrix_data_records = []
            for record in IMPORT_EXPORT_MATRIX_DF.to_dict('records'):
                formatted = {'Exporter': record.get('Exporter', '')}
                for column in MATRIX_COLUMN_ORDER:
                    value = record.get(column)
                    if value is None or pd.isna(value) or value == 0:
                        formatted[column] = ''
                    else:
                        formatted[column] = f"{value:,.0f}"
                matrix_data_records.append(formatted)

            matrix_columns = [{'name': 'Exporter', 'id': 'Exporter'}] + [
                {'name': col, 'id': col} for col in MATRIX_COLUMN_ORDER
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
                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}
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
