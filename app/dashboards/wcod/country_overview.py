"""
Country Overview View
Replicates Energy Intelligence WCoD Country Overview functionality
"""
from dash import dcc, html, Input, Output, State, callback, dash_table, dash
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from core.data_helpers import execute_query

COUNTRY_OVERVIEW_QUERY = """
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
    FULL JOIN fact_wcod_port P
        ON P."country_id" = A."country_id"
    WHERE A."country_long_name" IS NOT NULL
      AND A."to_be_deleted" IS NULL
"""

METRIC_CONFIG = [
    ('Exports (\'000 b/d)', 'Exports', ',.0f'),
    ('Production (\'000 b/d)', 'Production', ',.0f'),
    ('R/P Ratio (Year)', 'R_P_Ratio', ',.0f'),
    ('Reserves (Billion bbl)', 'Reserves', ',.0f')
]


def build_data_columns(years):
    columns = []
    for metric_name, prefix, spec in METRIC_CONFIG:
        for year in years:
            columns.append({
                "name": [metric_name, str(year)],
                "id": f"{prefix}_{year}",
                "type": "numeric",
                "format": {"specifier": spec}
            })
    return columns


def load_country_overview_data():
    empty_df = pd.DataFrame(columns=['Country', 'Profile_URL'])
    empty_bar = pd.DataFrame(columns=['Country', 'Profile_URL'])
    empty_map = {}
    empty_years = []
    empty_columns = build_data_columns(empty_years)

    try:
        query_results = execute_query(COUNTRY_OVERVIEW_QUERY)
    except Exception as exc:
        print(f"Error loading country overview data: {exc}")
        return empty_df, empty_bar, empty_map, empty_years, empty_columns

    df = pd.DataFrame(query_results)
    if df.empty:
        return empty_df, empty_bar, empty_map, empty_years, empty_columns

    df.columns = df.columns.str.strip()
    required_cols = ['country_long_name', 'profile_url', 'yr', 'output', 'exports', 'reserves']
    available_cols = [col for col in required_cols if col in df.columns]

    if len(available_cols) < len(required_cols):
        missing = set(required_cols) - set(available_cols)
        print(f"Missing expected columns in country overview data: {missing}")
        return empty_df, empty_bar, empty_map, empty_years, empty_columns

    df = df[required_cols].copy()
    df['country_long_name'] = df['country_long_name'].astype(str).str.strip()
    df['Profile_URL'] = df['profile_url'].astype(str).str.strip()
    df['yr_value'] = pd.to_datetime(df['yr'], errors='coerce')
    df['Year'] = df['yr_value'].dt.year
    df['Production'] = pd.to_numeric(df['output'], errors='coerce')
    df['Exports'] = pd.to_numeric(df['exports'], errors='coerce')
    df['Reserves'] = pd.to_numeric(df['reserves'], errors='coerce')

    production_series = df['Production'].replace(0, np.nan)
    df['R_P_Ratio'] = (df['Reserves'] * 1_000_000) / (365 * production_series)

    df = df.dropna(subset=['country_long_name', 'Year'])
    df = df.sort_values(['country_long_name', 'Year', 'yr_value'], ascending=[True, False, False])
    df = df.drop_duplicates(subset=['country_long_name', 'Profile_URL', 'Year'])

    years = sorted(df['Year'].dropna().unique(), reverse=True)[:2]
    if not years:
        return empty_df, empty_bar, empty_map, empty_years, empty_columns

    country_records = []
    for (country, profile_url), group in df.groupby(['country_long_name', 'Profile_URL']):
        row = {
            'Country': country,
            'Profile_URL': profile_url
        }
        for year in years:
            year_subset = group[group['Year'] == year]
            if year_subset.empty:
                continue
            latest = year_subset.iloc[0]
            row[f'Exports_{year}'] = latest['Exports']
            row[f'Production_{year}'] = latest['Production']
            row[f'Reserves_{year}'] = latest['Reserves']
            row[f'R_P_Ratio_{year}'] = latest['R_P_Ratio']
        country_records.append(row)

    pivot_df = pd.DataFrame(country_records)
    if pivot_df.empty:
        return empty_df, empty_bar, empty_map, empty_years, empty_columns

    numeric_columns = []
    for _, prefix, _ in METRIC_CONFIG:
        for year in years:
            numeric_columns.append(f'{prefix}_{year}')

    for col in numeric_columns:
        if col in pivot_df.columns:
            pivot_df[col] = pd.to_numeric(pivot_df[col], errors='coerce').fillna(0)
        else:
            pivot_df[col] = 0

    pivot_df['Country'] = pivot_df['Country'].astype(str).str.strip()
    pivot_df['Profile_URL'] = pivot_df['Profile_URL'].replace({'nan': '', 'None': '', 'none': ''}).fillna('')

    latest_year = years[0]
    exports_col = f'Exports_{latest_year}'
    production_col = f'Production_{latest_year}'
    for col in (exports_col, production_col):
        if col not in pivot_df.columns:
            pivot_df[col] = 0

    bar_chart_data = (
        pivot_df[['Country', exports_col, production_col, 'Profile_URL']]
        .sort_values(exports_col, ascending=False)
        .head(9)
        .reset_index(drop=True)
    )

    country_url_map = {
        row['Country']: row.get('Profile_URL', '')
        for _, row in pivot_df.iterrows() if row.get('Profile_URL')
    }

    data_columns = build_data_columns(years)
    return pivot_df, bar_chart_data, country_url_map, years, data_columns


# Initialize empty - will be loaded lazily when page is accessed
pivot_df = pd.DataFrame(columns=['Country', 'Profile_URL'])
bar_chart_data = pd.DataFrame(columns=['Country', 'Profile_URL'])
country_url_map = {}
YEARS_TO_DISPLAY = []
DATA_COLUMNS = []
LATEST_YEAR = None

def get_country_overview_data():
    """Lazy load country overview data - only when page is accessed"""
    global pivot_df, bar_chart_data, country_url_map, YEARS_TO_DISPLAY, DATA_COLUMNS, LATEST_YEAR
    # Load data if not already loaded (check if pivot_df is empty or YEARS_TO_DISPLAY is empty)
    if pivot_df.empty or not YEARS_TO_DISPLAY:
        pivot_df, bar_chart_data, country_url_map, YEARS_TO_DISPLAY, DATA_COLUMNS = load_country_overview_data()
        LATEST_YEAR = YEARS_TO_DISPLAY[0] if YEARS_TO_DISPLAY else None
    return pivot_df, bar_chart_data, country_url_map, YEARS_TO_DISPLAY, DATA_COLUMNS, LATEST_YEAR


# Time dimension column definitions
TIME_DIMENSION_COLUMNS = [
    {"name": ["", "Year of Year"], "id": "Year_of_Year", "type": "numeric", "format": {"specifier": ",.0f"}},
    {"name": ["", "Quarter of Year"], "id": "Quarter_of_Year", "type": "numeric", "format": {"specifier": ",.0f"}},
    {"name": ["", "Month of Year"], "id": "Month_of_Year", "type": "text"},
    {"name": ["", "Day of Year"], "id": "Day_of_Year", "type": "numeric", "format": {"specifier": ",.0f"}},
]

# Data table columns (without time dimensions) - will be updated when data loads
DATA_TABLE_COLUMNS = [
    {"name": ["", "Country"], "id": "Country", "type": "text", "presentation": "markdown"},
]


def create_layout():
    """Create the Country Overview layout"""
    return html.Div([
        # Store for selected country
        dcc.Store(id='selected-country-store', data=None),
        # Store for profile URL to open
        dcc.Store(id='profile-url-store', data=None),
        # Store for click counter (ensures callback fires on every click)
        dcc.Store(id='click-counter-store', data=0),
        # Store for time dimension visibility (Year, Quarter, Month, Day)
        dcc.Store(id='time-dimension-visibility', data={'Year': True, 'Quarter': False, 'Month': False, 'Day': False}),
        # Hidden div to trigger URL opening via clientside callback
        html.Div(id='open-url-trigger', children=0, style={'display': 'none'}),

        html.Div([
            html.Span(
                "Click on the Country's name to view the Profile",
                style={'textAlign': 'left', 'marginBottom': '20px', 'fontSize': '13px', 'color': '#2c3e50', 'fontWeight': 'bold', 'fontStyle': 'italic'}
            )
        ]),

        # Ranking Chart Card
        # html.Div([
            html.Div([
                # html.Div([                   
                    html.H4(
                        "Ranking the world's crude oil exporters",
                        style={
                            'textAlign': 'center',
                            'marginTop': '30px',
                            'marginBottom': '20px',
                            'color': '#fe5000',
                            'fontWeight': 'bold',
                            'fontSize': '21px',
                            'fontFamily': 'Arial, sans-serif',
                            'lineHeight': '23px'
                        }
                    ),
                    html.Button(
                        '−',
                        id='chart-collapse-button',
                        n_clicks=0,
                        style={
                            'float': 'right',
                            'fontSize': '20px',
                            'fontWeight': 'bold',
                            'color': '#2c3e50',
                            'textDecoration': 'none',
                            'padding': '0 10px',
                            'border': 'none',
                            'background': 'transparent',
                            'cursor': 'pointer'
                        }
                    )
                # ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'width': '100%', 'padding': '15px', 'background': '#f8f9fa', 'borderBottom': '1px solid #dee2e6'})
            ]),
            dcc.Loading(
                id='chart-loading',
                type='dot',
                fullscreen=False,
                overlay_style={'backgroundColor': 'rgba(255, 255, 255, 0.8)'},
                children=html.Div([
                    # Chart with embedded time dimension expand/collapse controls
                    html.Div([
                        # Time dimension controls inside chart area - first row with icons at top right
                        html.Div([
                            html.Div([
                                html.Span("Year of Year", style={'fontSize': '12px', 'color': '#2c3e50', 'flex': '1'}),
                                html.Button(
                                    '−',
                                    id='toggle-year-btn',
                                    n_clicks=0,
                                    style={
                                        'width': '20px',
                                        'height': '20px',
                                        'padding': '0',
                                        'border': '1px solid #dee2e6',
                                        'backgroundColor': '#f8f9fa',
                                        'color': '#2c3e50',
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
                                )
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px', 'width': '120px'}),
                            html.Div([
                                html.Span("Quarter of Year", style={'fontSize': '12px', 'color': '#2c3e50', 'flex': '1'}),
                                html.Button(
                                    '+',
                                    id='toggle-quarter-btn',
                                    n_clicks=0,
                                    style={
                                        'width': '20px',
                                        'height': '20px',
                                        'padding': '0',
                                        'border': '1px solid #dee2e6',
                                        'backgroundColor': '#f8f9fa',
                                        'color': '#2c3e50',
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
                                )
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px', 'width': '130px'}),
                            html.Div([
                                html.Span("Month of Year", style={'fontSize': '12px', 'color': '#2c3e50', 'flex': '1'}),
                                html.Button(
                                    '+',
                                    id='toggle-month-btn',
                                    n_clicks=0,
                                    style={
                                        'width': '20px',
                                        'height': '20px',
                                        'padding': '0',
                                        'border': '1px solid #dee2e6',
                                        'backgroundColor': '#f8f9fa',
                                        'color': '#2c3e50',
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
                                )
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px', 'width': '130px'}),
                            html.Div([
                                html.Span("Day of Year", style={'fontSize': '12px', 'color': '#2c3e50', 'flex': '1'}),
                                html.Button(
                                    '+',
                                    id='toggle-day-btn',
                                    n_clicks=0,
                                    style={
                                        'width': '20px',
                                        'height': '20px',
                                        'padding': '0',
                                        'border': '1px solid #dee2e6',
                                        'backgroundColor': '#f8f9fa',
                                        'color': '#2c3e50',
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
                                )
                            ], style={'display': 'flex', 'alignItems': 'center', 'width': '120px'})
                        ], style={'padding': '10px 20px', 'borderBottom': '1px solid #dee2e6', 'background': '#f8f9fa', 'display': 'flex', 'justifyContent': 'flex-start', 'alignItems': 'center'}),
                        dcc.Graph(
                            id='exports-ranking-chart',
                            figure=go.Figure(),  # Empty figure initially, will be updated by callback when data loads
                            clickData=None,
                            style={'height': '600px'}
                        )
                    ], id='chart-collapse-content', style={'padding': '0', 'background': 'white', 'border': '1px solid #dee2e6', 'borderRadius': '4px', 'overflow': 'hidden'}),
                ], style={'minHeight': '400px'})
            ),
        # ], style={'background': 'white', 'border': '1px solid #dee2e6', 'borderRadius': '4px', 'marginBottom': '30px', 'overflow': 'hidden'}),

        # Data Table Section
        dcc.Loading(
            id='table-loading',
            type='dot',
            fullscreen=False,
            overlay_style={'backgroundColor': 'rgba(255, 255, 255, 0.8)'},
            children=html.Div([
                html.H4(
                    "Leading Oil Exporting Countries",
                    style={
                        'textAlign': 'center',
                        'marginTop': '30px',
                        'marginBottom': '20px',
                        'color': '#fe5000',
                        'fontWeight': 'bold',
                        'fontSize': '21px',
                        'fontFamily': 'Arial, sans-serif',
                        'lineHeight': '23px'
                    }
                ),
                dash_table.DataTable(
                    id='oil-data-table',
                    data=[],
                    columns=DATA_TABLE_COLUMNS,
                    page_action='none',
                    style_cell={
                        'textAlign': 'center',
                        'padding': '8px',
                        'fontSize': '12px',
                        'fontFamily': 'Arial, sans-serif',
                        'border': '1px solid #dee2e6',
                        'color': '#2c3e50'
                    },
                    style_header={
                        'backgroundColor': '#f8f9fa',
                        'fontWeight': 'bold',
                        'border': '1px solid #dee2e6',
                        'textAlign': 'center',
                        'fontSize': '12px',
                        'fontFamily': 'Arial, sans-serif',
                        'color': '#2c3e50'
                    },
                    style_data={
                        'border': '1px solid #dee2e6',
                        'backgroundColor': 'white',
                        'color': '#2c3e50'
                    },
                    style_cell_conditional=[
                        {
                            'if': {'column_id': 'Country'},
                            'textAlign': 'left',
                            'fontWeight': 'bold',
                            'minWidth': '150px',
                            'color': '#1b365d'
                        }
                    ],
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        },
                        {
                            'if': {'filter_query': '{Country} contains ""'},
                            'backgroundColor': 'white'
                        }
                    ],
                    merge_duplicate_headers=True,
                    sort_action='native',
                    filter_action='none',
                    style_table={
                        'overflowX': 'auto',
                        'border': '1px solid #dee2e6',
                        'borderRadius': '4px',
                        'backgroundColor': 'white'
                    },
                    cell_selectable=True
                )
            ], style={'minHeight': '400px'})
        ),

        # Footer notes
        html.Div([
            html.P(
                "Countries: Select jurisdictions are included under countries for data presentation purposes.",
                style={'fontSize': '10px', 'fontStyle': 'italic', 'marginTop': '20px', 'color': '#6c757d'}
            ),
            # html.P(
            #     "Source: Energy Intelligence | COPYRIGHT © 2001-2025 ENERGY INTELLIGENCE GROUP, INC.",
            #     style={'fontSize': '10px', 'fontStyle': 'italic', 'marginTop': '10px', 'color': '#6c757d'}
            # )
        ])
    ], className='tab-content')


def create_ranking_chart(selected_country=None, time_visibility=None):
    """Create horizontal bar chart ranking crude oil exporters"""
    if bar_chart_data.empty or not LATEST_YEAR:
        return go.Figure()

    exports_col = f'Exports_{LATEST_YEAR}'
    production_col = f'Production_{LATEST_YEAR}'

    chart_columns = ['Country', exports_col]
    if production_col in bar_chart_data.columns:
        chart_columns.append(production_col)

    sorted_df = bar_chart_data[chart_columns].sort_values(exports_col, ascending=True).copy()
    if sorted_df.empty:
        return go.Figure()

    sorted_df = sorted_df.rename(columns={exports_col: 'Exports_Value'})
    if production_col in sorted_df.columns:
        sorted_df = sorted_df.rename(columns={production_col: 'Production_Value'})
    else:
        sorted_df['Production_Value'] = 0

    fig = go.Figure()
    country_list_original = sorted_df['Country'].astype(str).str.strip().tolist()
    
    # Build y-axis labels with time dimensions if visible
    country_list = country_list_original.copy()
    if time_visibility:
        year_value = LATEST_YEAR
        quarter_value = 4
        month_value = "December"
        day_value = 31
        
        y_labels = []
        for country in country_list_original:
            label_parts = [country]
            if time_visibility.get('Year', True) and year_value:
                label_parts.append(str(year_value))
            if time_visibility.get('Quarter', False):
                label_parts.append(f"Q{quarter_value}")
            if time_visibility.get('Month', False):
                label_parts.append(month_value)
            if time_visibility.get('Day', False):
                label_parts.append(f"{day_value}")
            y_labels.append("   ".join(label_parts))
        
        # Use enhanced labels if any time dimension is visible
        if any([time_visibility.get('Year', True), time_visibility.get('Quarter', False), 
                time_visibility.get('Month', False), time_visibility.get('Day', False)]):
            country_list = y_labels

    # For color matching, use original country names
    export_colors = ['#0075A8' if country == selected_country else 'rgb(0, 117, 168)' for country in country_list_original]
    production_colors = ['#595959' if country == selected_country else 'rgb(89, 89, 89)' for country in country_list_original]

    if sorted_df['Production_Value'].any():
        fig.add_trace(go.Bar(
            y=country_list,
            x=sorted_df['Production_Value'].tolist(),
            customdata=country_list_original,
            orientation='h',
            marker=dict(
                color=production_colors,
                line=dict(color=production_colors, width=1.5 if selected_country else 0.5)
            ),
            text=sorted_df['Production_Value'].apply(lambda x: f'{x:,.0f}' if pd.notna(x) and x else '').tolist(),
            textposition='outside',
            name="Production ('000 b/d)",
            hovertemplate='<span style="color:#999999;">Country:</span> <span style="color:#0075A8;">%{customdata}</span><br><span style="color:#999999;">Production (\'000 b/d):</span> <span style="color:#0075A8;">%{x:,.0f}</span><br><span style="color:#999999;">Year:</span> <span style="color:#0075A8;">' + str(LATEST_YEAR) + '</span><extra></extra>',
            showlegend=True,
            legendgroup='production',
            offsetgroup='production',
            width=0.4
        ))

    fig.add_trace(go.Bar(
        y=country_list,
        x=sorted_df['Exports_Value'].tolist(),
        customdata=country_list_original,
        orientation='h',
        marker=dict(
            color=export_colors,
            line=dict(color=export_colors, width=1.5 if selected_country else 0.5)
        ),
        text=sorted_df['Exports_Value'].apply(lambda x: f'{x:,.0f}' if pd.notna(x) else '').tolist(),
        textposition='outside',
        name="Exports ('000 b/d)",
        hovertemplate='<span style="color:#999999;">Country:</span> <span style="color:#0075A8;">%{customdata}</span><br><span style="color:#999999;">Exports (\'000 b/d):</span> <span style="color:#0075A8;">%{x:,.0f}</span><br><span style="color:#999999;">Year:</span> <span style="color:#0075A8;">' + str(LATEST_YEAR) + '</span><extra></extra>',
        showlegend=True,
        legendgroup='exports',
        offsetgroup='exports',
        width=0.4
    ))

    max_export = sorted_df['Exports_Value'].max() if len(sorted_df) else 0
    max_production = sorted_df['Production_Value'].max() if len(sorted_df) else 0
    max_val = max(max_export, max_production) if max(max_export, max_production) > 0 else 1000

    fig.update_layout(
        # title={
        #     'text': "Ranking the world's crude oil exporters",
        #     'x': 0.5,
        #     'xanchor': 'center',
        #     'font': {
        #         'size': 21,
        #         'family': 'Arial, sans-serif',
        #         'color': '#fe5000'
        #     }
        # },
        xaxis_title="('000 b/d)",
        yaxis_title="",
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            font=dict(size=12, family='Arial, sans-serif', color='#2c3e50'),
            bgcolor='rgba(255,255,255,0.8)',
            traceorder='normal',
            itemsizing='constant',
            bordercolor='#dee2e6',
            borderwidth=1
        ),
        height=600,
        margin=dict(l=150, r=120, t=90, b=40),
        xaxis=dict(
            range=[0, max_val * 1.2] if max_val > 0 else [0, 1000],
            showgrid=True,
            gridcolor='#E0E0E0',
            gridwidth=1,
            tickformat=',',
            zeroline=False,
            showline=True,
            linecolor='#000000',
            linewidth=1,
            title_font=dict(size=12, family='Arial, sans-serif', color='#2c3e50'),
            tickfont=dict(size=11, family='Arial, sans-serif', color='#2c3e50')
        ),
        yaxis=dict(
            categoryorder='array',
            categoryarray=country_list,
            tickfont=dict(size=11, family='Arial Black, Arial, sans-serif', color='#1b365d'),
            showline=True,
            linecolor='#000000',
            linewidth=1,
            side='left',
            type='category',
            tickmode='array',
            tickvals=country_list,
            ticktext=country_list
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='closest',
        barmode='group',
        bargap=0.1,
        bargroupgap=0.8,
        hoverlabel=dict(
            bgcolor='white',
            bordercolor='#0075A8',
            font=dict(
                size=14,
                family='Arial, sans-serif',
                color='#333333'
            )
        )
    )

    # Add horizontal lines after each country
    shapes = []
    num_countries = len(country_list)
    for i in range(num_countries - 1):
        # Calculate y position between countries (category positions are 0-indexed)
        y_pos = i + 0.5
        shapes.append({
            'type': 'line',
            'xref': 'x',
            'yref': 'y',
            'x0': 0,
            'y0': y_pos,
            'x1': max_val * 1.2 if max_val > 0 else 1000,
            'y1': y_pos,
            'line': {
                'color': '#E0E0E0',
                'width': 1,
                'dash': 'solid'
            },
            'layer': 'below'
        })
    
    if shapes:
        fig.update_layout(shapes=shapes)

    fig.update_traces(selector=dict(name="Exports ('000 b/d)"), legendrank=1)
    fig.update_traces(selector=dict(name="Production ('000 b/d)"), legendrank=2)

    return fig


def register_callbacks(dash_app, server):
    """Register all callbacks for Country Overview"""

    @callback(
        Output('exports-ranking-chart', 'figure', allow_duplicate=True),
        [Input('current-submenu', 'data'),
         Input('selected-country-store', 'data'),
         Input('time-dimension-visibility', 'data')],
        prevent_initial_call='initial_duplicate'
    )
    def update_ranking_chart(submenu, selected_country, time_visibility):
        """Update ranking chart with highlighting"""
        if submenu != 'country-overview':
            return go.Figure()
        
        # Load data when page is active
        get_country_overview_data()
        
        return create_ranking_chart(selected_country=selected_country, time_visibility=time_visibility)

    @callback(
        [Output('oil-data-table', 'data'),
         Output('oil-data-table', 'columns')],
        Input('current-submenu', 'data'),
        prevent_initial_call=False
    )
    def update_oil_data_table(submenu):
        """Update oil data table with country statistics"""
        if submenu != 'country-overview':
            return [], []

        # Load data when page is active
        get_country_overview_data()
        
        # Update DATA_TABLE_COLUMNS with loaded data columns
        table_columns = [
            {"name": ["", "Country"], "id": "Country", "type": "text", "presentation": "markdown"},
        ] + DATA_COLUMNS

        if pivot_df.empty:
            return [], table_columns

        table_data = []
        if 'Country' in pivot_df.columns:
            iter_df = pivot_df.sort_values('Country', key=lambda col: col.str.lower(), ascending=True)
        else:
            iter_df = pivot_df

        for _, row in iter_df.iterrows():
            country_name = row.get('Country', '')
            profile_url = row.get('Profile_URL', '') or country_url_map.get(country_name, '')
            row_data = {
                'Country': f"[{country_name}]({profile_url})" if profile_url else country_name,
                'Country_Original': country_name,
                'Profile_URL': profile_url
            }

            for year in YEARS_TO_DISPLAY:
                for _, prefix, _ in METRIC_CONFIG:
                    column_id = f'{prefix}_{year}'
                    row_data[column_id] = row.get(column_id, 0)

            table_data.append(row_data)

        # Update DATA_TABLE_COLUMNS with loaded data columns
        table_columns = [
            {"name": ["", "Country"], "id": "Country", "type": "text", "presentation": "markdown"},
        ] + DATA_COLUMNS
        
        return table_data, table_columns

    @callback(
        [Output('selected-country-store', 'data'),
         Output('profile-url-store', 'data'),
         Output('click-counter-store', 'data')],
        Input('exports-ranking-chart', 'clickData'),
        State('click-counter-store', 'data'),
        prevent_initial_call=True
    )
    def update_selected_country_from_chart(clickData, click_counter):
        if clickData and 'points' in clickData and len(clickData['points']) > 0:
            point = clickData['points'][0]
            custom_country = point.get('customdata')
            if isinstance(custom_country, list) and custom_country:
                custom_country = custom_country[0]
            country_name = custom_country or point.get('y')
            if country_name and isinstance(country_name, str):
                country_name = country_name.split('   ')[0]
            profile_url = country_url_map.get(country_name)
            new_counter = (click_counter or 0) + 1
            return country_name, profile_url, new_counter
        return dash.no_update, dash.no_update, click_counter

    @callback(
        [Output('selected-country-store', 'data', allow_duplicate=True),
         Output('profile-url-store', 'data', allow_duplicate=True),
         Output('click-counter-store', 'data', allow_duplicate=True)],
        [Input('oil-data-table', 'active_cell'),
         Input('oil-data-table', 'selected_rows')],
        [State('oil-data-table', 'data'),
         State('click-counter-store', 'data')],
        prevent_initial_call=True
    )
    def update_selected_country_from_table(active_cell, selected_rows, table_data, click_counter):
        if not table_data:
            return dash.no_update, dash.no_update, click_counter

        row_idx = None
        if active_cell and isinstance(active_cell, dict) and active_cell.get('row') is not None:
            row_idx = active_cell['row']
        elif selected_rows and isinstance(selected_rows, list) and len(selected_rows) > 0:
            row_idx = selected_rows[0]

        if row_idx is None or row_idx >= len(table_data):
            return dash.no_update, dash.no_update, click_counter

        row_data = table_data[row_idx]
        country = row_data.get('Country_Original', row_data.get('Country', ''))

        if isinstance(country, str) and country.startswith('[') and '](' in country:
            country = country.split('](')[0][1:]

        profile_url = row_data.get('Profile_URL') or country_url_map.get(country)

        if country:
            new_counter = (click_counter or 0) + 1
            return country, profile_url, new_counter

        return dash.no_update, dash.no_update, click_counter

    @callback(
        Output('exports-ranking-chart', 'figure', allow_duplicate=True),
        Input('selected-country-store', 'data'),
        State('current-submenu', 'data'),
        prevent_initial_call='initial_duplicate'
    )
    def update_chart_highlight(selected_country, submenu):
        """Update chart highlighting based on selected country"""
        if submenu != 'country-overview':
            return dash.no_update
        return create_ranking_chart(selected_country=selected_country)

    @callback(
        Output('oil-data-table', 'style_data_conditional', allow_duplicate=True),
        Input('selected-country-store', 'data'),
        State('oil-data-table', 'data'),
        prevent_initial_call=True
    )
    def update_table_highlight(selected_country, table_data):
        """Update table row highlighting based on selected country"""
        style_conditions = [
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }
        ]

        if selected_country and table_data:
            for idx, row in enumerate(table_data):
                country_original = row.get('Country_Original', '')
                if country_original == selected_country:
                    style_conditions.append({
                        'if': {'row_index': idx},
                        'backgroundColor': '#FFF8DC',  # Light yellow highlight
                        'fontWeight': 'bold'
                    })
                    break

        return style_conditions

    @callback(
        [Output('chart-collapse-content', 'style'),
         Output('chart-collapse-button', 'children')],
        Input('chart-collapse-button', 'n_clicks'),
        State('chart-collapse-content', 'style'),
        prevent_initial_call=True
    )
    def toggle_chart_collapse(n_clicks, current_style):
        """Toggle chart collapse/expand"""
        if n_clicks:
            is_hidden = current_style.get('display') == 'none'
            new_style = {**current_style, 'display': 'none' if not is_hidden else 'block'}
            button_text = '+' if is_hidden else '−'
            return new_style, button_text
        return current_style, '−'

    # Initialize button icons and styles based on visibility state
    @callback(
        [Output('toggle-year-btn', 'children'),
         Output('toggle-year-btn', 'style'),
         Output('toggle-quarter-btn', 'children'),
         Output('toggle-quarter-btn', 'style'),
         Output('toggle-month-btn', 'children'),
         Output('toggle-month-btn', 'style'),
         Output('toggle-day-btn', 'children'),
         Output('toggle-day-btn', 'style')],
        Input('time-dimension-visibility', 'data'),
        prevent_initial_call=False
    )
    def update_button_icons(visibility):
        """Update button icons (+/-) and styles based on visibility state"""
        base_style = {
            'width': '20px',
            'height': '20px',
            'padding': '0',
            'border': '1px solid #dee2e6',
            'borderRadius': '3px',
            'cursor': 'pointer',
            'fontSize': '14px',
            'fontWeight': 'bold',
            'lineHeight': '1',
            'display': 'inline-flex',
            'alignItems': 'center',
            'justifyContent': 'center'
        }
        
        year_expanded = visibility.get('Year', True)
        quarter_expanded = visibility.get('Quarter', False)
        month_expanded = visibility.get('Month', False)
        day_expanded = visibility.get('Day', False)
        
        year_style = {**base_style,
            'backgroundColor': '#e7f3ff' if year_expanded else '#f8f9fa',
            'color': '#007bff' if year_expanded else '#2c3e50',
            'borderColor': '#007bff' if year_expanded else '#dee2e6'
        }
        quarter_style = {**base_style,
            'backgroundColor': '#e7f3ff' if quarter_expanded else '#f8f9fa',
            'color': '#007bff' if quarter_expanded else '#2c3e50',
            'borderColor': '#007bff' if quarter_expanded else '#dee2e6'
        }
        month_style = {**base_style,
            'backgroundColor': '#e7f3ff' if month_expanded else '#f8f9fa',
            'color': '#007bff' if month_expanded else '#2c3e50',
            'borderColor': '#007bff' if month_expanded else '#dee2e6'
        }
        day_style = {**base_style,
            'backgroundColor': '#e7f3ff' if day_expanded else '#f8f9fa',
            'color': '#007bff' if day_expanded else '#2c3e50',
            'borderColor': '#007bff' if day_expanded else '#dee2e6'
        }
        
        return (
            '−' if year_expanded else '+', year_style,
            '−' if quarter_expanded else '+', quarter_style,
            '−' if month_expanded else '+', month_style,
            '−' if day_expanded else '+', day_style
        )

    # Callbacks for time dimension toggles
    @callback(
        [Output('time-dimension-visibility', 'data', allow_duplicate=True),
         Output('toggle-year-btn', 'children', allow_duplicate=True),
         Output('toggle-year-btn', 'style', allow_duplicate=True)],
        Input('toggle-year-btn', 'n_clicks'),
        State('time-dimension-visibility', 'data'),
        prevent_initial_call=True
    )
    def toggle_year(n_clicks, visibility):
        """Toggle Year column visibility"""
        if n_clicks:
            new_visibility = visibility.copy()
            new_visibility['Year'] = not new_visibility.get('Year', True)
            is_expanded = new_visibility['Year']
            button_style = {
                'width': '20px',
                'height': '20px',
                'padding': '0',
                'border': '1px solid #007bff' if is_expanded else '#dee2e6',
                'backgroundColor': '#e7f3ff' if is_expanded else '#f8f9fa',
                'color': '#007bff' if is_expanded else '#2c3e50',
                'borderRadius': '3px',
                'cursor': 'pointer',
                'fontSize': '14px',
                'fontWeight': 'bold',
                'lineHeight': '1',
                'display': 'inline-flex',
                'alignItems': 'center',
                'justifyContent': 'center'
            }
            return new_visibility, '−' if is_expanded else '+', button_style
        return visibility, dash.no_update, dash.no_update

    @callback(
        [Output('time-dimension-visibility', 'data', allow_duplicate=True),
         Output('toggle-quarter-btn', 'children', allow_duplicate=True),
         Output('toggle-quarter-btn', 'style', allow_duplicate=True)],
        Input('toggle-quarter-btn', 'n_clicks'),
        State('time-dimension-visibility', 'data'),
        prevent_initial_call=True
    )
    def toggle_quarter(n_clicks, visibility):
        """Toggle Quarter column visibility"""
        if n_clicks:
            new_visibility = visibility.copy()
            new_visibility['Quarter'] = not new_visibility.get('Quarter', False)
            is_expanded = new_visibility['Quarter']
            button_style = {
                'width': '20px',
                'height': '20px',
                'padding': '0',
                'border': '1px solid #007bff' if is_expanded else '#dee2e6',
                'backgroundColor': '#e7f3ff' if is_expanded else '#f8f9fa',
                'color': '#007bff' if is_expanded else '#2c3e50',
                'borderRadius': '3px',
                'cursor': 'pointer',
                'fontSize': '14px',
                'fontWeight': 'bold',
                'lineHeight': '1',
                'display': 'inline-flex',
                'alignItems': 'center',
                'justifyContent': 'center'
            }
            return new_visibility, '−' if is_expanded else '+', button_style
        return visibility, dash.no_update, dash.no_update

    @callback(
        [Output('time-dimension-visibility', 'data', allow_duplicate=True),
         Output('toggle-month-btn', 'children', allow_duplicate=True),
         Output('toggle-month-btn', 'style', allow_duplicate=True)],
        Input('toggle-month-btn', 'n_clicks'),
        State('time-dimension-visibility', 'data'),
        prevent_initial_call=True
    )
    def toggle_month(n_clicks, visibility):
        """Toggle Month column visibility"""
        if n_clicks:
            new_visibility = visibility.copy()
            new_visibility['Month'] = not new_visibility.get('Month', False)
            is_expanded = new_visibility['Month']
            button_style = {
                'width': '20px',
                'height': '20px',
                'padding': '0',
                'border': '1px solid #007bff' if is_expanded else '#dee2e6',
                'backgroundColor': '#e7f3ff' if is_expanded else '#f8f9fa',
                'color': '#007bff' if is_expanded else '#2c3e50',
                'borderRadius': '3px',
                'cursor': 'pointer',
                'fontSize': '14px',
                'fontWeight': 'bold',
                'lineHeight': '1',
                'display': 'inline-flex',
                'alignItems': 'center',
                'justifyContent': 'center'
            }
            return new_visibility, '−' if is_expanded else '+', button_style
        return visibility, dash.no_update, dash.no_update

    @callback(
        [Output('time-dimension-visibility', 'data', allow_duplicate=True),
         Output('toggle-day-btn', 'children', allow_duplicate=True),
         Output('toggle-day-btn', 'style', allow_duplicate=True)],
        Input('toggle-day-btn', 'n_clicks'),
        State('time-dimension-visibility', 'data'),
        prevent_initial_call=True
    )
    def toggle_day(n_clicks, visibility):
        """Toggle Day column visibility"""
        if n_clicks:
            new_visibility = visibility.copy()
            new_visibility['Day'] = not new_visibility.get('Day', False)
            is_expanded = new_visibility['Day']
            button_style = {
                'width': '20px',
                'height': '20px',
                'padding': '0',
                'border': '1px solid #007bff' if is_expanded else '#dee2e6',
                'backgroundColor': '#e7f3ff' if is_expanded else '#f8f9fa',
                'color': '#007bff' if is_expanded else '#2c3e50',
                'borderRadius': '3px',
                'cursor': 'pointer',
                'fontSize': '14px',
                'fontWeight': 'bold',
                'lineHeight': '1',
                'display': 'inline-flex',
                'alignItems': 'center',
                'justifyContent': 'center'
            }
            return new_visibility, '−' if is_expanded else '+', button_style
        return visibility, dash.no_update, dash.no_update

    # Client-side callback to open profile URL in new tab
    dash_app.clientside_callback(
        """
        function(url, click_counter) {
            if (url && url !== '' && url !== null && url !== undefined && url !== 'None' && url !== 'null' && click_counter > 0) {
                // Always open in new tab (target=_blank)
                setTimeout(function() {
                    window.open(url, '_blank', 'noopener,noreferrer');
                }, 100);
                return click_counter; // Return counter to track changes
            }
            return click_counter || 0;
        }
        """,
        Output('open-url-trigger', 'children'),
        [Input('profile-url-store', 'data'),
         Input('click-counter-store', 'data')]
    )

