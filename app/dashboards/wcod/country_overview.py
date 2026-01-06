"""
Country Overview View
Replicates Energy Intelligence WCoD Country Overview functionality
"""
from dash import dcc, html, Input, Output, State, callback, dash_table, dash, callback_context
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import numpy as np
import logging
import base64
from weasyprint import HTML, CSS
import fitz # PyMuPDF
import io
from PIL import Image

logger = logging.getLogger(__name__)


from core.data_helpers import execute_query

CHART_OVERVIEW_QUERY = """
WITH base AS (
    SELECT
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
        'Source: Energy Intelligence' AS "Source",
        EXTRACT(YEAR FROM A."yr")::INT              AS "Year of Year",
        'Q' || EXTRACT(QUARTER FROM A."yr")         AS "Quarter of Year",
        TRIM(TO_CHAR(A."yr", 'Month'))              AS "Month of Year",
        EXTRACT(DAY FROM A."yr")::INT               AS "Day of Year",
        A."output",
        A."exports"
    FROM fact_wcod_country A
    WHERE
        EXTRACT(YEAR FROM A."yr") = 2024
        AND A."to_be_deleted" IS NULL
),
top_exports AS (
    SELECT *
    FROM base
    ORDER BY exports DESC
    LIMIT 9
)
SELECT
    t."country_long_name",
    t.profile_url,
    t."Source",
    t."Year of Year",
    t."Quarter of Year",
    t."Month of Year",
    t."Day of Year",
    m.measure_name                 AS "Measure Names",
    'COPYRIGHT © 2001-2021 ENERGY INTELLIGENCE GROUP, INC. / ENERGY INTELLIGENCE GROUP (UK) LIMITED.'
                                    AS "Copyright",
    m.measure_value                AS "Measure Values"
FROM top_exports t
CROSS JOIN LATERAL (
    VALUES
        ('Exports (''000 b/d)',    t.exports),
        ('Production (''000 b/d)', t.output)
) m(measure_name, measure_value)
WHERE m.measure_value IS NOT NULL
ORDER BY
    t.exports DESC,
    m.measure_name;
"""

TABLE_OVERVIEW_QUERY = """
WITH base AS (
    SELECT
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
        'Source: Energy Intelligence' AS "Source",
        EXTRACT(YEAR FROM A."yr")::INT AS "Year of Year",
        'Q' || EXTRACT(QUARTER FROM A."yr")         AS "Quarter of Year",
        TRIM(TO_CHAR(A."yr", 'Month'))              AS "Month of Year",
        EXTRACT(DAY FROM A."yr")::INT               AS "Day of Year",
        A."output",
        A."exports",
        A."reserves"
    FROM fact_wcod_country A
    WHERE
        EXTRACT(YEAR FROM A."yr") IN (2023, 2024)
        AND A."country_long_name" IS NOT NULL
        AND A."to_be_deleted" IS NULL
)

SELECT
    b."country_long_name",
    b.profile_url,
    b."Source",
    b."Year of Year",
    b."Quarter of Year",
    b."Month of Year",
    b."Day of Year",

    m.measure_name       AS "Measure Names",

    'COPYRIGHT © 2001-2021 ENERGY INTELLIGENCE GROUP, INC. / ENERGY INTELLIGENCE GROUP (UK) LIMITED.'
        AS "Copyright",

    m.measure_value      AS "Measure Values"

FROM base b
CROSS JOIN LATERAL (
    VALUES
        ('Exports (''000 b/d)',        b.exports),
        ('Production (''000 b/d)',     b.output),
        ('R/P Ratio (Year)',
            CASE
                WHEN b.output IS NOT NULL AND b.output <> 0
                     AND b.reserves IS NOT NULL
                THEN (b.reserves * 1000000.0) / (365 * b.output)
                ELSE NULL
            END
        ),
        ('Reserves (Billion bbl)',     b.reserves)
) m(measure_name, measure_value)

WHERE m.measure_value IS NOT NULL

ORDER BY
    b."country_long_name",
    b."Year of Year",
    m.measure_name;
"""

METRIC_CONFIG = [
    ("Exports ('000 b/d)", 'Exports', ',.0f'),
    ("Production ('000 b/d)", 'Production', ',.0f'),
    ('R/P Ratio (Year)', 'R_P_Ratio', ',.0f'),
    ('Reserves (Billion bbl)', 'Reserves', ',.0f')
]

TIME_DIMENSION_COLUMNS_CONFIG = [
    {"name": ["", "Year of Year"], "id": "Year_of_Year", "type": "numeric", "format": {"specifier": ",.0f"}},
    {"name": ["", "Quarter of Year"], "id": "Quarter_of_Year", "type": "numeric", "format": {"specifier": ",.0f"}},
    {"name": ["", "Month of Year"], "id": "Month_of_Year", "type": "text"},
    {"name": ["", "Day of Year"], "id": "Day_of_Year", "type": "numeric", "format": {"specifier": ",.0f"}},
]


def build_data_columns(years, time_visibility, latest_quarter_value, latest_month_value, latest_day_value):
    columns = []
    for metric_name, prefix, spec in METRIC_CONFIG:
        for year in years:
            column_name_parts = [str(year)]
            
            if time_visibility.get('Quarter', False) and latest_quarter_value is not None:
               
                column_name_parts.append(f"{latest_quarter_value}")
            
            if time_visibility.get('Month', False) and latest_month_value is not None:
                column_name_parts.append(f"\n{latest_month_value}")
            
            if time_visibility.get('Day', False) and latest_day_value is not None:
                column_name_parts.append(f"{latest_day_value}")

            combined_year_name = " ".join(column_name_parts)
            
            columns.append({
                "name": [metric_name, combined_year_name],
                "id": f"{prefix}_{year}",
                "type": "numeric",
                "format": {"specifier": spec}
            })
    return columns


def get_metric_prefix(metric_name, metric_config):
    for name, prefix, _ in metric_config:
        if name == metric_name:
            return prefix
    return None

def load_country_overview_data():
    empty_df = pd.DataFrame(columns=['Country', 'Profile_URL'])
    empty_bar = pd.DataFrame(columns=['Country', 'Profile_URL'])
    empty_map = {}
    empty_years = []
    empty_columns = build_data_columns(empty_years, {}, None, None, None)

    chart_df = pd.DataFrame()
    table_df = pd.DataFrame()
    latest_quarter_value = None
    latest_month_value = None
    latest_day_value = None

    try:
        chart_query_results = execute_query(CHART_OVERVIEW_QUERY)
        chart_df = pd.DataFrame(chart_query_results)
        
        table_query_results = execute_query(TABLE_OVERVIEW_QUERY)
        table_df = pd.DataFrame(table_query_results)
        logger.info(f"table_df loaded, head:\n{table_df.head()}")

    except Exception as exc:
        print(f"Error loading country overview data: {exc}. Returning empty data.")
        return empty_df, empty_bar, empty_map, empty_years, empty_columns, None, None, None, None

    # Process chart data
    bar_chart_data = pd.DataFrame(columns=['Country', 'Exports_Value', 'Production_Value', 'Profile_URL'])
    country_url_map = {}
    if not chart_df.empty:
        chart_df.columns = chart_df.columns.str.strip()
        
        # Ensure required columns are present in chart_df
        required_chart_cols = ['country_long_name', 'profile_url', 'Year of Year', 'Measure Names', 'Measure Values']
        if not all(col in chart_df.columns for col in required_chart_cols):
            print(f"Missing expected columns in chart data: {set(required_chart_cols) - set(chart_df.columns)}")
        else:
            chart_df = chart_df.rename(columns={
                'country_long_name': 'Country',
                'profile_url': 'Profile_URL',
                'Year of Year': 'Year',
                'Measure Names': 'Metric',
                'Measure Values': 'Value'
            })
            
            # Pivot chart_df to get Exports_Value and Production_Value for the latest year
            latest_chart_year = chart_df['Year'].max()
            chart_pivot = chart_df[chart_df['Year'] == latest_chart_year].pivot_table(
                index=['Country', 'Profile_URL'], 
                columns='Metric', 
                values='Value'
            ).reset_index()

            if "Exports ('000 b/d)" in chart_pivot.columns:
                chart_pivot['Exports_Value'] = pd.to_numeric(chart_pivot["Exports ('000 b/d)"], errors='coerce').fillna(0)
            else:
                chart_pivot['Exports_Value'] = 0

            if "Production ('000 b/d)" in chart_pivot.columns:
                chart_pivot['Production_Value'] = pd.to_numeric(chart_pivot["Production ('000 b/d)"], errors='coerce').fillna(0)
            else:
                chart_pivot['Production_Value'] = 0
            
            bar_chart_data = chart_pivot[['Country', 'Exports_Value', 'Production_Value', 'Profile_URL']].sort_values('Exports_Value', ascending=False).head(9).reset_index(drop=True)
            country_url_map = {row['Country']: row.get('Profile_URL', '') for _, row in chart_pivot.iterrows() if row.get('Profile_URL')}

            # Extract latest quarter, month, and day from chart_df
            latest_chart_data = chart_df[chart_df['Year'] == latest_chart_year]
            latest_quarter_value = latest_chart_data['Quarter of Year'].iloc[0] if 'Quarter of Year' in latest_chart_data.columns and not latest_chart_data.empty else None
            latest_month_value = latest_chart_data['Month of Year'].iloc[0] if 'Month of Year' in latest_chart_data.columns and not latest_chart_data.empty else None
            latest_day_value = latest_chart_data['Day of Year'].iloc[0] if 'Day of Year' in latest_chart_data.columns and not latest_chart_data.empty else None
    # Process table data
    pivot_df = empty_df.copy()
    years = empty_years.copy()
    data_columns = empty_columns.copy()

    if not table_df.empty:
        table_df.columns = table_df.columns.str.strip()
        required_table_cols = ['country_long_name', 'profile_url', 'Year of Year', 'Measure Names', 'Measure Values']
        if not all(col in table_df.columns for col in required_table_cols):
            print(f"Missing expected columns in table data: {set(required_table_cols) - set(table_df.columns)}")
        else:
            table_df = table_df.rename(columns={
                'country_long_name': 'Country',
                'profile_url': 'Profile_URL',
                'Year of Year': 'Year',
                'Measure Names': 'Metric',
                'Measure Values': 'Value'
            })
            logger.info(f"table_df after rename, head:\n{table_df.head()}")

            # Get unique years from the table data
            years = sorted(table_df['Year'].dropna().unique(), reverse=True)
            if not years:
                print("No years found in table data.")
                return empty_df, empty_bar, empty_map, empty_years, empty_columns, None, None, None, None

            data_columns = build_data_columns(years, {}, None, None, None)

            # Create a combined metric-year column for pivoting
            table_df['Metric_Year'] = table_df.apply(lambda row: f'{get_metric_prefix(row["Metric"], METRIC_CONFIG)}_{row["Year"]}' if get_metric_prefix(row["Metric"], METRIC_CONFIG) else None, axis=1)
            logger.info(f"table_df after Metric_Year creation, head:\n{table_df.head()}")

            # Drop rows where Metric_Year is None (i.e., metric not found in METRIC_CONFIG)
            table_df.dropna(subset=['Metric_Year'], inplace=True)

            if table_df.empty:
                print("Table data is empty after dropping unmapped metrics.")
                return empty_df, empty_bar, empty_map, empty_years, empty_columns, None, None, None, None

            # Pivot table_df to get metrics for each year as columns
            pivot_df = table_df.pivot_table(
                index=['Country', 'Profile_URL'],
                columns='Metric_Year',
                values='Value'
            ).reset_index()

            # Fill missing columns (metric-year combinations) with 0
            for col_id in [col["id"] for col in data_columns]:
                if col_id not in pivot_df.columns:
                    pivot_df[col_id] = 0
            
            # Ensure Country and Profile_URL columns are clean
            pivot_df['Country'] = pivot_df['Country'].astype(str).str.strip()
            pivot_df['Profile_URL'] = pivot_df['Profile_URL'].replace({'nan': '', 'None': '', 'none': ''}).fillna('')
        logger.info(f"Final pivot_df before return, head:\n{pivot_df.head()}")

    print(f"load_country_overview_data returning: pivot_df.empty={pivot_df.empty}, bar_chart_data.empty={bar_chart_data.empty}, len(years)={len(years)}, len(data_columns)={len(data_columns)}, latest_year={years[0] if years else None}, latest_quarter={latest_quarter_value}, latest_month={latest_month_value}, latest_day={latest_day_value}")
    return pivot_df, bar_chart_data, country_url_map, years, data_columns, years[0] if years else None, latest_quarter_value, latest_month_value, latest_day_value


# Initialize empty - will be loaded lazily when page is accessed
pivot_df = pd.DataFrame(columns=['Country', 'Profile_URL'])
bar_chart_data = pd.DataFrame(columns=['Country', 'Profile_URL'])
country_url_map = {}
YEARS_TO_DISPLAY = []
DATA_COLUMNS = []
LATEST_YEAR = None
LATEST_QUARTER = None
LATEST_MONTH = None
LATEST_DAY = None

def get_country_overview_data():
    """Lazy load country overview data - only when page is accessed"""
    global pivot_df, bar_chart_data, country_url_map, YEARS_TO_DISPLAY, DATA_COLUMNS, LATEST_YEAR, LATEST_QUARTER, LATEST_MONTH, LATEST_DAY
    # Load data if not already loaded (check if pivot_df is empty or YEARS_TO_DISPLAY is empty)
    if pivot_df.empty or not YEARS_TO_DISPLAY:
        pivot_df, bar_chart_data, country_url_map, YEARS_TO_DISPLAY, DATA_COLUMNS, LATEST_YEAR, LATEST_QUARTER, LATEST_MONTH, LATEST_DAY = load_country_overview_data()
    return pivot_df, bar_chart_data, country_url_map, YEARS_TO_DISPLAY, DATA_COLUMNS, LATEST_YEAR, LATEST_QUARTER, LATEST_MONTH, LATEST_DAY


# Time dimension column definitions
TIME_DIMENSION_COLUMNS = TIME_DIMENSION_COLUMNS_CONFIG

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
        dcc.Store(id='time-dimension-table-visibility', data={'Year': True, 'Quarter': False, 'Month': False, 'Day': False}),
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
                     html.Div([ # New flex container for title and export controls
                html.H4(
                    "Ranking the world's crude oil exporters",
                    style={
                        'textAlign': 'center',
                        'marginTop': '0px',
                        'marginBottom': '0px',
                        'color': '#fe5000',
                        'fontWeight': 'bold',
                        'fontSize': '21px',
                        'fontFamily': 'Arial, sans-serif',
                        'lineHeight': '23px',
                        'flexGrow': 1 # Allow title to take available space
                    }
                ),
                html.Div([ # Container for dropdown and collapse button
                    html.Div(
                        dcc.Dropdown(
                            id='dashboard-export-dropdown',
                            options=[
                                {'label': 'Export to PDF', 'value': 'pdf'},
                                {'label': 'Export to PNG', 'value': 'png'},
                                {'label': 'Export to CSV', 'value': 'raw_chart_csv'}
                            ],
                    placeholder='Export Data',
                            style={
                                'width': '200px',
                                'marginRight': '10px',
                                'fontSize': '13px',
                                'color': '#2c3e50',
                                'display': 'inline-block'
                            },
                            clearable=False
                        ),
                        style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'flex-end', 'width': 'auto', 'padding': '0 0px'}
                    ),
                    dcc.Download(id="download-dashboard-content"),
                    dcc.Download(id="download-raw-chart-csv"),
                    dcc.Download(id="download-raw-table-csv"),
                    dcc.Download(id="download-png-report"),
                    # html.Button(
                    #     '−',
                    #     id='chart-collapse-button',
                    #     n_clicks=1,
                    #     style={
                    #         'fontSize': '20px',
                    #         'fontWeight': 'bold',
                    #         'color': '#2c3e50',
                    #         'textDecoration': 'none',
                    #         'padding': '0 10px',
                    #         'border': 'none',
                    #         'background': 'transparent',
                    #         'cursor': 'pointer',
                    #         'marginLeft': '10px' # Added margin for separation
                    #     }
                    # )
                ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'flex-end', 'padding': '0'})
            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'width': '100%', 'padding': '15px', 'background': '#f8f9fa', 'borderBottom': '1px solid #dee2e6'}),
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
                                        'padding': '0 10px',
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
                                        'padding': '0 10px',
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
                                        'padding': '0 10px',
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
                                        'padding': '0 10px',
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
                            style={'height': '600px'},
                            config={
                                "toImageButtonOptions": {
                                    "format": "png",
                                    "filename": "country_overview_chart",
                                    "height": 720,
                                    "width": 1280,
                                    "scale": 2
                                },
                                "displaylogo": False,
                                "displayModeBar": True,
                                'modeBarButtonsToRemove': [
                                    'zoom2d', 'pan2d', 'select2d', 'lasso2d', 
                                    'zoomIn2d', 'zoomOut2d', 'autoScale2d', 
                                    'hoverClosestCartesian', 'hoverCompareCartesian', 
                                    'toggleSpikelines', 'toggleSpikeLines', 'spikelines'
                                ]
                            }
                        )
                    ], id='chart-collapse-content', style={'padding': '0', 'background': 'white', 'border': '1px solid #dee2e6', 'borderRadius': '4px', 'overflow': 'hidden'}),
                ], style={'minHeight': '400px'})
            ),
            html.Br(), #
            html.Br(), 
        # ], style={'background': 'white', 'border': '1px solid #dee2e6', 'borderRadius': '4px', 'marginBottom': '30px', 'overflow': 'hidden'}),

        # Data Table Section
                html.Div([ # New parent div for title and button
                    html.H4(
                        "Leading Oil Exporting Countries",
                        style={
                            'textAlign': 'center',
                            'marginTop': '0px',
                            'marginBottom': '0px',
                            'color': '#fe5000',
                            'fontWeight': 'bold',
                            'fontSize': '21px',
                            'fontFamily': 'Arial, sans-serif',
                            'lineHeight': '23px',
                            'flexGrow': 1 # Allow title to take available space
                        }
                    ),
                    html.Div([ # Existing div for button
                        html.Button(
                            'Export to CSV',
                            id='btn-export-raw-table-csv',
                            n_clicks=0,
                            style={
                                'backgroundColor': 'white',
                                'color': '#2c3e50',
                                'border': '1px solid #dee2e6',
                                'padding': '8px 15px',
                                'borderRadius': '4px',
                                'cursor': 'pointer',
                                'fontSize': '13px',
                                'margin': '0',
                                'display': 'inline-block'
                            }
                        ),
                    ], style={'display': 'flex', 'alignItems': 'right', 'justifyContent': 'flex-end'}),
                    dcc.Download(id="download-raw-table-csv"),
                ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'padding': '0 0 15px 0px'}),
                html.Div([ # Time dimension controls inside table area - first row with icons at top right
                    html.Div([
                        html.Span("Quarter of Year", style={'fontSize': '12px', 'color': '#2c3e50', 'flex': '1'}),
                        html.Button(
                            '+',
                            id='toggle-table-quarter-btn',
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
                            id='toggle-table-month-btn',
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
                            id='toggle-table-day-btn',
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
                dcc.Loading(
                    id='table-loading',
                    type='dot',
                    fullscreen=False,
                    overlay_style={'backgroundColor': 'rgba(255, 255, 255, 0.8)'},
                    children=html.Div([
                        dash_table.DataTable(
                    id='oil-data-table',
                    data= [],
                    columns=DATA_TABLE_COLUMNS,
                    page_action='none',
                    style_cell={
                        'textAlign': 'right',
                        'padding': '0px 2px',
                        'fontSize': '12px',
                        'fontFamily': 'Arial, sans-serif',
                        'border': '1px solid #dee2e6',
                        'color': '#2c3e50'
                    },
                    style_header={
                        'backgroundColor': '#f8f9fa',
                        'fontWeight': 'bold',
                        'border': '1px solid #dee2e6',
                        'fontSize': '12px',
                        'fontFamily': 'Arial, sans-serif',
                        'color': '#2c3e50'
                    },
                    style_header_conditional=[
                        # Country header (first row, left-aligned)
                        {
                            'if': {'column_id': 'Country', 'header_index': 0},
                            'textAlign': 'left',
                            'justifyContent': 'flex-start'
                        },
                        # Top-level metric headers (first row, center-aligned)
                        {
                            'if': {'header_index': 0, 'column_id': '.*'}, # Target all columns in the first row
                            'textAlign': 'center'
                        },
                        # Removed explicit right-alignment for year headers, they will inherit center from style_header
                    ],
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


def create_ranking_chart(selected_country=None, time_visibility=None, year_value=None, quarter_value=None, month_value=None, day_value=None):
    """Create horizontal bar chart ranking crude oil exporters"""
    if bar_chart_data.empty or not LATEST_YEAR:
        return go.Figure()

    # exports_col = f'Exports_{LATEST_YEAR}'
    # production_col = f'Production_{LATEST_YEAR}'

    chart_columns = ['Country', 'Exports_Value', 'Production_Value']
    
    sorted_df = bar_chart_data[chart_columns].sort_values('Exports_Value', ascending=True).copy()
    if sorted_df.empty:
        return go.Figure()

    # Renaming columns are no longer needed as they are already in the correct format
    # sorted_df = sorted_df.rename(columns={exports_col: 'Exports_Value'})
    # if production_col in sorted_df.columns:
    #     sorted_df = sorted_df.rename(columns={production_col: 'Production_Value'})
    # else:
    #     sorted_df['Production_Value'] = 0

    fig = go.Figure()
    country_list_original = sorted_df['Country'].astype(str).str.strip().tolist()
    
    # Build y-axis labels with time dimensions if visible
    country_list = country_list_original.copy()
    if time_visibility:
        # year_value = LATEST_YEAR # Now passed as parameter
        # quarter_value = 4 # Now passed as parameter
        # month_value = "December" # Now passed as parameter
        # day_value = 31 # Now passed as parameter
        
        y_labels = []
        for country in country_list_original:
            label_parts = [country]
            if time_visibility.get('Year', True) and year_value:
                label_parts.append(str(year_value))
            if time_visibility.get('Quarter', False) and quarter_value:
                label_parts.append(f"{quarter_value}")
            if time_visibility.get('Month', False) and month_value:
                label_parts.append(month_value)
            if time_visibility.get('Day', False) and day_value:
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
        hovertemplate_production = (
            '<span style="color:#999999;">Country:</span> <span style="color:#0075A8;">%{customdata}</span><br>'
            '<span style="color:#999999;">Production (\'000 b/d):</span> <span style="color:#0075A8;">%{x:,.0f}</span><br>'
        )
        if time_visibility and time_visibility.get('Year', True) and year_value:
            hovertemplate_production += f'<span style="color:#999999;">Year:</span> <span style="color:#0075A8;">{year_value}</span><br>'
        if time_visibility and time_visibility.get('Quarter', False) and quarter_value:
            hovertemplate_production += f'<span style="color:#999999;">Quarter:</span> <span style="color:#0075A8;">{quarter_value}</span><br>'
        if time_visibility and time_visibility.get('Month', False) and month_value:
            hovertemplate_production += f'<span style="color:#999999;">Month:</span> <span style="color:#0075A8;">{month_value}</span><br>'
        if time_visibility and time_visibility.get('Day', False) and day_value:
            hovertemplate_production += f'<span style="color:#999999;">Day:</span> <span style="color:#0075A8;">{day_value}</span><br>'
        hovertemplate_production += '<extra></extra>'

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
            hovertemplate=hovertemplate_production,
            showlegend=True,
            legendgroup='production',
            offsetgroup='production',
            width=0.3
        ))

    hovertemplate_exports = (
        '<span style="color:#999999;">Country:</span> <span style="color:#0075A8;">%{customdata}</span><br>'
        '<span style="color:#999999;">Exports (\'000 b/d):</span> <span style="color:#0075A8;">%{x:,.0f}</span><br>'
    )
    if time_visibility and time_visibility.get('Year', True) and year_value:
        hovertemplate_exports += f'<span style="color:#999999;">Year:</span> <span style="color:#0075A8;">{year_value}</span><br>'
    if time_visibility and time_visibility.get('Quarter', False) and quarter_value:
        hovertemplate_exports += f'<span style="color:#999999;">Quarter:</span> <span style="color:#0075A8;">{quarter_value}</span><br>'
    if time_visibility and time_visibility.get('Month', False) and month_value:
        hovertemplate_exports += f'<span style="color:#999999;">Month:</span> <span style="color:#0075A8;">{month_value}</span><br>'
    if time_visibility and time_visibility.get('Day', False) and day_value:
        hovertemplate_exports += f'<span style="color:#999999;">Day:</span> <span style="color:#0075A8;">{day_value}</span><br>'
    hovertemplate_exports += '<extra></extra>'

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
        hovertemplate=hovertemplate_exports,
        showlegend=True,
        legendgroup='exports',
        offsetgroup='exports',
        width=0.3
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
        margin=dict(l=300, r=0, t=90, b=40),
        xaxis=dict(
            range=[0, max_val * 1.2] if max_val > 0 else [0, 1000],
            showgrid=True,
            gridcolor='#E0E0E0',
            gridwidth=1,
            tickformat=',',
            zeroline=False,
            showline=True,
            linecolor='#e0e0e0',  # Light gray color
            linewidth=1,
            title_font=dict(size=12, family='Arial, sans-serif', color='#2c3e50'),
            tickfont=dict(size=11, family='Arial, sans-serif', color='#2c3e50'),
            showspikes=False,
            spikethickness=0
        ),
        yaxis=dict(
            categoryorder='array',
            categoryarray=country_list,
            tickfont=dict(size=11, family='Arial, sans-serif', color='#1b365d'),
            showline=True,
            linecolor='#e0e0e0',  # Light gray color
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
        [Output('download-dashboard-content', 'data'),
         Output('download-raw-chart-csv', 'data'),
         Output('download-png-report', 'data')],
        [Input('dashboard-export-dropdown', 'value')],
        [State('exports-ranking-chart', 'figure'),
         State('oil-data-table', 'data'),
         State('oil-data-table', 'columns')],
        prevent_initial_call=True
    )
    def export_dashboard_content_and_data(selected_value, chart_figure, table_data, table_columns):
        if not selected_value:
            return dash.no_update, dash.no_update, dash.no_update

        # Initialize all download triggers to no_update
        download_pdf = dash.no_update
        download_png = dash.no_update
        download_raw_chart_csv = dash.no_update

        if selected_value == 'pdf':
            # Logic for PDF export
            fig = go.Figure(chart_figure)
            img_bytes = pio.to_image(fig, format="png", height=720, width=1280, scale=2)
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')

            df_table = pd.DataFrame(table_data)
            display_columns = [col['id'] for col in table_columns if col['id'] != 'Country_Original' and col['id'] != 'Profile_URL']
            if 'Country' in df_table.columns:
                df_table['Country'] = df_table['Country'].apply(lambda x: x.split('](')[0][1:] if x and x.startswith('[') else x)
            
            html_table_headers = "<thead><tr>"
            current_metric_header = ""
            for col in table_columns:
                if col['id'] == 'Country':
                    html_table_headers += f"<th rowspan=\"2\">{col['name'][1]}</th>"
                elif col['id'].startswith(('Exports_', 'Production_', 'R_P_Ratio_', 'Reserves_')):
                    metric_name = col['name'][0]
                    if metric_name != current_metric_header:
                        years_for_metric = len([c for c in table_columns if c['name'][0] == metric_name])
                        html_table_headers += f"<th colspan=\"{years_for_metric}\">{metric_name}</th>"
                        current_metric_header = metric_name
            html_table_headers += "</tr><tr>"
            for col in table_columns:
                if col['id'] != 'Country':
                    html_table_headers += f"<th>{col['name'][1]}</th>"
            html_table_headers += "</tr></thead>"

            html_table_body = "<tbody>"
            for index, row in df_table.iterrows():
                html_table_body += "<tr>"
                for col_id in display_columns:
                    value = row.get(col_id, '')
                    html_table_body += f"<td>{value}</td>"
                html_table_body += "</tr>"
            html_table_body += "</tbody>"

            html_table_content = f"<table border=\"1\" style=\"width:100%; border-collapse: collapse; text-align: center;\">{html_table_headers}{html_table_body}</table>"

            html_content = f"""
                <html>
                <head>
                    <title>Country Overview Report</title>
                    <style>
                        @page {{
                            size: 1200px 5000px; /* Custom size for a very tall single page */
                            margin: 20px; /* Apply margin to the page */
                        }}
                        body {{ font-family: Arial, sans-serif; margin: 0; }} /* Remove body margin as page margin is set */
                        h1, h4 {{ color: #fe5000; text-align: center; }}
                        img {{ max-width: 100%; height: auto; display: block; margin: 0 auto; }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                        th, td {{ border: 1px solid #dee2e6; padding: 8px; text-align: center; font-size: 10px; }}
                        th {{ background-color: #f8f9fa; font-weight: bold; }}
                    </style>
                </head>
                <body>
                    <h1>Country Overview Report</h1>
                    <h4>Ranking the world's crude oil exporters</h4>
                    <img src="data:image/png;base64,{img_base64}" />
                    <h4>Leading Oil Exporting Countries</h4>
                    {html_table_content}
                </body>
                </html>
            """

            pdf_bytes = HTML(string=html_content).write_pdf()
            download_pdf = dcc.send_bytes(pdf_bytes, "country_overview_report.pdf")

        elif selected_value == 'png':
            # Logic for PNG export (chart + table)
            fig = go.Figure(chart_figure)
            chart_png_bytes = pio.to_image(fig, format="png", height=720, width=1280, scale=2)
            chart_img_base64 = base64.b64encode(chart_png_bytes).decode('utf-8')

            df_table = pd.DataFrame(table_data)
            display_columns = [col['id'] for col in table_columns if col['id'] != 'Country_Original' and col['id'] != 'Profile_URL']
            if 'Country' in df_table.columns:
                df_table['Country'] = df_table['Country'].apply(lambda x: x.split('](')[0][1:] if x and x.startswith('[') else x)
            
            html_table_headers = "<thead><tr>"
            current_metric_header = ""
            for col in table_columns:
                if col['id'] == 'Country':
                    html_table_headers += f"<th rowspan=\"2\">{col['name'][1]}</th>"
                elif col['id'].startswith(('Exports_', 'Production_', 'R_P_Ratio_', 'Reserves_')):
                    metric_name = col['name'][0]
                    if metric_name != current_metric_header:
                        years_for_metric = len([c for c in table_columns if c['name'][0] == metric_name])
                        html_table_headers += f"<th colspan=\"{years_for_metric}\">{metric_name}</th>"
                        current_metric_header = metric_name
            html_table_headers += "</tr><tr>"
            for col in table_columns:
                if col['id'] != 'Country':
                    html_table_headers += f"<th>{col['name'][1]}</th>"
            html_table_headers += "</tr></thead>"

            html_table_body = "<tbody>"
            for index, row in df_table.iterrows():
                html_table_body += "<tr>"
                for col_id in display_columns:
                    value = row.get(col_id, '')
                    html_table_body += f"<td>{value}</td>"
                html_table_body += "</tr>"
            html_table_body += "</tbody>"

            html_table_content = f"<table border=\"1\" style=\"width:100%; border-collapse: collapse; text-align: center;\">{html_table_headers}{html_table_body}</table>"

            # Combine chart and table into a single HTML for WeasyPrint
            combined_html_content = f"""
                <html>
                <head>
                    <title>Country Overview Report</title>
                    <style>
                        @page {{
                            size: 1200px 5000px;
                            margin: 20px;
                        }}
                        body {{ font-family: Arial, sans-serif; margin: 0; }}
                        h1, h4 {{ color: #fe5000; text-align: center; }}
                        img {{ max-width: 100%; height: auto; display: block; margin: 0 auto; }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                        th, td {{ border: 1px solid #dee2e6; padding: 8px; text-align: center; font-size: 10px; }}
                        th {{ background-color: #f8f9fa; font-weight: bold; }}
                    </style>
                </head>
                <body>
                    <h1>Country Overview Report</h1>
                    <h4>Ranking the world's crude oil exporters</h4>
                    <img src="data:image/png;base64,{chart_img_base64}" />
                    <h4>Leading Oil Exporting Countries</h4>
                    {html_table_content}
                </body>
                </html>
            """
            
            # Use WeasyPrint to render the combined HTML to a single PNG image
            # WeasyPrint directly renders to PDF, so we need to render to PDF first, then convert to PNG
            pdf_for_png_bytes = HTML(string=combined_html_content).write_pdf()
            
            # Convert PDF to PNG using PyMuPDF
            doc = fitz.open("pdf", pdf_for_png_bytes)
            pix = doc[0].get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format="PNG")
            png_combined_bytes = img_byte_arr.getvalue()
            doc.close()

            download_png = dcc.send_bytes(png_combined_bytes, "country_overview_report.png")

        elif selected_value == 'raw_chart_csv':
            raw_chart_data = pd.DataFrame(execute_query(CHART_OVERVIEW_QUERY))
            download_raw_chart_csv = dcc.send_data_frame(raw_chart_data.to_csv, "raw_chart_query_data.csv")


        return download_pdf, download_raw_chart_csv, download_png

    @callback(
        Output('download-raw-table-csv', 'data'),
        Input('btn-export-raw-table-csv', 'n_clicks'),
        prevent_initial_call=True
    )
    def export_raw_table_data_to_csv(n_clicks):
        if n_clicks > 0:
            raw_table_data = pd.DataFrame(execute_query(TABLE_OVERVIEW_QUERY))
            return dcc.send_data_frame(raw_table_data.to_csv, "raw_table_query_data.csv")
        return dash.no_update



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
        _, _, _, _, _, _LATEST_YEAR, _LATEST_QUARTER, _LATEST_MONTH, _LATEST_DAY = get_country_overview_data()
        
        return create_ranking_chart(selected_country=selected_country, time_visibility=time_visibility, year_value=_LATEST_YEAR, quarter_value=_LATEST_QUARTER, month_value=_LATEST_MONTH, day_value=_LATEST_DAY)

    @callback(
        [Output('oil-data-table', 'data'),
         Output('oil-data-table', 'columns')],
        [Input('current-submenu', 'data'),
         Input('time-dimension-table-visibility', 'data')],
        prevent_initial_call=False
    )
    def update_oil_data_table(submenu, time_dimension_table_visibility):
        """Update oil data table with country statistics"""
        if submenu != 'country-overview':
            return [], []

        # Load data when page is active
        _pivot_df, _bar_chart_data, _country_url_map, _YEARS_TO_DISPLAY, _DATA_COLUMNS, _LATEST_YEAR, _LATEST_QUARTER, _LATEST_MONTH, _LATEST_DAY = get_country_overview_data()

        # Dynamically build data columns including time dimensions
        table_columns_config = build_data_columns(_YEARS_TO_DISPLAY, time_dimension_table_visibility, _LATEST_QUARTER, _LATEST_MONTH, _LATEST_DAY)

        # Base columns always present
        table_columns = [
            {"name": ["", "Country"], "id": "Country", "type": "text", "presentation": "markdown"},
        ] + table_columns_config

        if _pivot_df.empty:
            return [], table_columns

        table_data = []
        if 'Country' in _pivot_df.columns:
            iter_df = _pivot_df.sort_values('Country', key=lambda col: col.str.lower(), ascending=True)
        else:
            iter_df = _pivot_df

        for _, row in iter_df.iterrows():
            country_name = row.get('Country', '')
            profile_url = row.get('Profile_URL', '') or _country_url_map.get(country_name, '')
            row_data = {
                'Country': f"[{country_name}]({profile_url})" if profile_url else country_name,
                'Country_Original': country_name,
                'Profile_URL': profile_url
            }

            for metric_name, prefix, _ in METRIC_CONFIG:
                for year in _YEARS_TO_DISPLAY:
                    # Add main metric-year value
                    column_id = f'{prefix}_{year}'
                    row_data[column_id] = row.get(column_id, 0)

                    # Add time dimension values if visible
                    if time_dimension_table_visibility.get('Quarter', False) and _LATEST_QUARTER is not None:
                        row_data[f'{prefix}_{year}_Quarter'] = _LATEST_QUARTER
                    if time_dimension_table_visibility.get('Month', False) and _LATEST_MONTH is not None:
                        row_data[f'{prefix}_{year}_Month'] = _LATEST_MONTH
                    if time_dimension_table_visibility.get('Day', False) and _LATEST_DAY is not None:
                        row_data[f'{prefix}_{year}_Day'] = _LATEST_DAY

            table_data.append(row_data)

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
        # Load data to get the latest country_url_map
        _, _, _country_url_map, _, _, _, _, _, _ = get_country_overview_data()
        
        if clickData and 'points' in clickData and len(clickData['points']) > 0:
            point = clickData['points'][0]
            custom_country = point.get('customdata')
            if isinstance(custom_country, list) and custom_country:
                custom_country = custom_country[0]
            country_name = custom_country
            if not country_name and point.get('y') and isinstance(point.get('y'), str):
                country_name = point.get('y').split('   ')[0]
            profile_url = _country_url_map.get(country_name)
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
        # Load data to get the latest country_url_map
        _, _, _country_url_map, _, _, _, _, _, _ = get_country_overview_data()

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

        profile_url = row_data.get('Profile_URL') or _country_url_map.get(country)

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
        
        # Load data to get the latest bar_chart_data and LATEST_YEAR
        _, _, _, _, _, _LATEST_YEAR, _LATEST_QUARTER, _LATEST_MONTH, _LATEST_DAY = get_country_overview_data()

        return create_ranking_chart(selected_country=selected_country, year_value=_LATEST_YEAR, quarter_value=_LATEST_QUARTER, month_value=_LATEST_MONTH, day_value=_LATEST_DAY)

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
         Output('toggle-day-btn', 'style'),
         Output('toggle-table-quarter-btn', 'children'),
         Output('toggle-table-quarter-btn', 'style'),
         Output('toggle-table-month-btn', 'children'),
         Output('toggle-table-month-btn', 'style'),
         Output('toggle-table-day-btn', 'children'),
         Output('toggle-table-day-btn', 'style')],
        [Input('time-dimension-visibility', 'data'),
         Input('time-dimension-table-visibility', 'data')],
        prevent_initial_call=False
    )
    def update_button_icons(visibility, table_visibility):
        """Update button icons (+/-) and styles based on visibility state for both chart and table"""
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
        
        # Chart buttons
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

        # Table buttons
        table_quarter_expanded = table_visibility.get('Quarter', False)
        table_month_expanded = table_visibility.get('Month', False)
        table_day_expanded = table_visibility.get('Day', False)

        table_quarter_style = {**base_style,
            'backgroundColor': '#e7f3ff' if table_quarter_expanded else '#f8f9fa',
            'color': '#007bff' if table_quarter_expanded else '#2c3e50',
            'borderColor': '#007bff' if table_quarter_expanded else '#dee2e6'
        }
        table_month_style = {**base_style,
            'backgroundColor': '#e7f3ff' if table_month_expanded else '#f8f9fa',
            'color': '#007bff' if table_month_expanded else '#2c3e50',
            'borderColor': '#007bff' if table_month_expanded else '#dee2e6'
        }
        table_day_style = {**base_style,
            'backgroundColor': '#e7f3ff' if table_day_expanded else '#f8f9fa',
            'color': '#007bff' if table_day_expanded else '#2c3e50',
            'borderColor': '#007bff' if table_day_expanded else '#dee2e6'
        }
        
        return (
            '−' if year_expanded else '+', year_style,
            '−' if quarter_expanded else '+', quarter_style,
            '−' if month_expanded else '+', month_style,
            '−' if day_expanded else '+', day_style,
            dash.no_update, table_quarter_style,
            '−' if table_month_expanded else '+', table_month_style,
            '−' if table_day_expanded else '+', table_day_style
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

    @callback(
        [Output('time-dimension-table-visibility', 'data', allow_duplicate=True),
         Output('toggle-table-quarter-btn', 'children', allow_duplicate=True),
         Output('toggle-table-quarter-btn', 'style', allow_duplicate=True)],
        Input('toggle-table-quarter-btn', 'n_clicks'),
        State('time-dimension-table-visibility', 'data'),
        prevent_initial_call=True
    )
    def toggle_table_quarter(n_clicks, visibility):
        """Toggle Quarter column visibility for table"""
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
        [Output('time-dimension-table-visibility', 'data', allow_duplicate=True),
         Output('toggle-table-month-btn', 'children', allow_duplicate=True),
         Output('toggle-table-month-btn', 'style', allow_duplicate=True)],
        Input('toggle-table-month-btn', 'n_clicks'),
        State('time-dimension-table-visibility', 'data'),
        prevent_initial_call=True
    )
    def toggle_table_month(n_clicks, visibility):
        """Toggle Month column visibility for table"""
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
        [Output('time-dimension-table-visibility', 'data', allow_duplicate=True),
         Output('toggle-table-day-btn', 'children', allow_duplicate=True),
         Output('toggle-table-day-btn', 'style', allow_duplicate=True)],
        Input('toggle-table-day-btn', 'n_clicks'),
        State('time-dimension-table-visibility', 'data'),
        prevent_initial_call=True
    )
    def toggle_table_day(n_clicks, visibility):
        """Toggle Day column visibility for table"""
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

