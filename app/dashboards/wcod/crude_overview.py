def format_with_link(value, link):
    if value is None:
        return ""
    text = str(value)
    if not link or not isinstance(link, str) or not link.strip():
        return text
    if not text.strip():
        return text
    safe_text = text.strip()
    safe_link = link.strip()
    return f'[{safe_text}]({safe_link})'
"""
Crude Overview View
Replicates Energy Intelligence WCoD Crude Overview functionality
Monthly World Crude Production Dashboard - Based on Tableau source
"""
from dash import Dash, dcc, html, Input, Output, State, callback, clientside_callback, dash_table, ALL, no_update
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import os
import re
import itertools
import math
import html as html_lib
import json
import urllib.request
from core.data_helpers import execute_query
from .shared_map_utils import (
    create_choropleth_map,
    get_mapbox_config,
    load_world_geojson,
    handle_map_click_reset,
    create_empty_map,
    MAP_BACKGROUND_COLOR,
    WORLD_CENTER,
    WORLD_ZOOM
)

# Define data paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'crude_overview')
YEARLY_GRADES_CSV = os.path.join(DATA_DIR, 'Yearly List of grades for selected country_data.csv')
MONTHLY_GRADES_CSV = os.path.join(DATA_DIR, 'Monthly List of grades for selected country_data.csv')

COUNTRIES_GEOJSON = None

# Helpers
COUNTRY_NAME_MAPPING = {
    "United States": "United States of America",
    "Abu Dhabi": "United Arab Emirates",
    "Dubai": "United Arab Emirates",
    "Congo (Brazzaville)": "Republic of the Congo",
}
def _resolve_countries_selection(selected):
    """Normalize country selection; expand '(All)' to full list."""
    if selected is None:
        return []
    if isinstance(selected, str):
        selected_list = [selected]
    else:
        selected_list = list(selected)
    if "(All)" in selected_list:
        return COUNTRIES[:] if COUNTRIES else []
    return [c for c in selected_list if c]

def _format_production_breakdown_title(country_selection):
    """Format the production breakdown title based on country selection.
    
    Args:
        country_selection: Original country selection (before resolution)
    
    Returns:
        Formatted title string
    """
    if country_selection is None:
        return "Production Breakdown"
    
    # Normalize to list
    if isinstance(country_selection, str):
        selected_list = [country_selection]
    else:
        selected_list = list(country_selection) if country_selection else []
    
    # Check if "(All)" is selected
    if "(All)" in selected_list:
        return "Production Breakdown – All"
    
    # Filter out "(All)" and get actual countries
    countries = [c for c in selected_list if c != "(All)"]
    
    if not countries:
        return "Production Breakdown"
    
    # If 3 or fewer countries, show all names
    if len(countries) <= 3:
        return f"Production Breakdown – {', '.join(countries)}"
    
    # If more than 3, show first 3 + count of remaining
    first_three = countries[:3]
    remaining_count = len(countries) - 3
    return f"Production Breakdown – {', '.join(first_three)} and {remaining_count} more"

def _calculate_yaxis_ticks(max_value):
    """
    Calculate Y-axis ticks dividing the range into 5 parts based on max value.
    Returns (y_axis_max, y_axis_ticks)
    """
    import math
    
    if max_value <= 0:
        return 100, [0, 20, 40, 60, 80, 100]
        
    # Calculate step size to get exactly 5 intervals (6 ticks including 0)
    # Target: 0, 1*step, 2*step, ... 5*step
    # where 5*step >= max_value
    
    raw_step = max_value / 5
    
    # Calculate magnitude of the step
    magnitude = 10 ** math.floor(math.log10(raw_step)) if raw_step > 0 else 1
    normalized_step = raw_step / magnitude
    
    # Round up to a nice number: 1, 2, 2.5, 5, 10
    if normalized_step <= 1:
        step = 1 * magnitude
    elif normalized_step <= 2:
        step = 2 * magnitude
    elif normalized_step <= 2.5:
        step = 2.5 * magnitude
    elif normalized_step <= 5:
        step = 5 * magnitude
    else:
        step = 10 * magnitude
        
    # Ensure step is an integer for cleaner look if magnitude >= 1
    if step >= 1:
        step = int(step)
        
    # Calculate max axis value (5 * step)
    y_axis_max = step * 5
    
    # Generate ticks
    y_axis_ticks = [step * i for i in range(6)]
    
    return y_axis_max, y_axis_ticks

def _resolve_years_selection(selected):
    """Normalize year selection; expand '(All)' to full list."""
    if selected is None:
        return []
    if isinstance(selected, str):
        selected_list = [selected]
    else:
        selected_list = list(selected)
    if "(All)" in selected_list:
        # Ensure data is loaded to get PRODUCTION_YEARS
        _ensure_data_loaded()
        return PRODUCTION_YEARS[:] if PRODUCTION_YEARS else []
    # Filter out "(All)" and convert to integers (years are stored as ints in PRODUCTION_YEARS)
    years = []
    for y in selected_list:
        if y != "(All)":
            try:
                # Handle both string and int inputs
                year_val = int(y) if isinstance(y, str) else y
                if isinstance(year_val, int):
                    years.append(year_val)
            except (ValueError, TypeError):
                # If it can't convert, skip
                pass
    return years

# Data loading functions
def load_yearly_bar():
    """Load yearly bar data from DB (fact_wcod_crude)."""
    query = """
        SELECT
            a.country_name AS "Country",
            a.crude_name AS "CrudeOil",
            EXTRACT(YEAR FROM a.yr) AS "YearReported",
            a.production_kbpd AS "ProductionDataValue",
            a.exports_kbpd AS "ExportDataValue",
            a.ci_rank
        FROM fact_wcod_crude a
        LEFT JOIN dim_country grp
            ON a.country_id = grp.dim_country_id
    """
    try:
        rows = execute_query(query)
        if not rows:
            print("DEBUG: No yearly bar rows returned from DB")
            return pd.DataFrame(), pd.DataFrame(), {}
        df = pd.DataFrame(rows)
        if df.empty:
            print("DEBUG: Yearly bar DataFrame empty after conversion")
            return pd.DataFrame(), pd.DataFrame(), {}
        df.columns = df.columns.str.strip()
        # Basic cleaning
        df = df[(df["Country"].notna()) & (df["CrudeOil"].notna())].copy()
        df["YearReported"] = pd.to_numeric(df["YearReported"], errors="coerce")
        df["ProductionDataValue"] = pd.to_numeric(df["ProductionDataValue"], errors="coerce")
        df = df.dropna(subset=["YearReported", "ProductionDataValue"])
        # Long format for chart
        df_long = pd.DataFrame()
        required_cols = {"CrudeOil", "Country", "YearReported", "ProductionDataValue"}
        if required_cols.issubset(df.columns):
            df_long = df[["CrudeOil", "Country", "YearReported", "ProductionDataValue"]].copy()
            df_long = df_long.rename(columns={"CrudeOil": "Stream", "YearReported": "year", "ProductionDataValue": "value"})
            df_long["year"] = df_long["year"].astype(int).astype(str)
            df_long["value"] = pd.to_numeric(df_long["value"], errors="coerce").fillna(0)
            df_long["month_idx"] = 0
            df_long = df_long[df_long["value"] > 0].copy()
            print(f"DEBUG: Loaded {len(df_long)} yearly bar records from DB")
        # Year-level totals for annotations (sum of production by year)
        year_production_data_value = {}
        if not df_long.empty:
            totals = df_long.groupby("year")["value"].sum()
            year_production_data_value = {str(k): float(v) for k, v in totals.items() if pd.notna(v)}
        return df, df_long, year_production_data_value
    except Exception as e:
        print(f"Error loading yearly bar data from DB: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame(), pd.DataFrame(), {}

def load_monthly_bar():
    """Load monthly bar data from DB (t_wcod_monthly_stream_production)."""
    query = """
        SELECT  
            EXTRACT(YEAR FROM date) AS "Year of Date",
            TO_CHAR(date, 'FMMonth') AS "Month of Date",
            country AS "Country",
            stream_name AS "Stream Name",
            value AS "Value"
        FROM t_wcod_monthly_stream_production where stream_name not in ('Total')
        ORDER BY date DESC, stream_name;
    """
    try:
        rows = execute_query(query)
        if not rows:
            print("DEBUG: No monthly bar rows returned from DB")
            return pd.DataFrame(), pd.DataFrame()
        df = pd.DataFrame(rows)
        if df.empty:
            print("DEBUG: Monthly bar DataFrame empty after conversion")
            return pd.DataFrame(), pd.DataFrame()
        df.columns = df.columns.str.strip()
        df_long = pd.DataFrame()
        required = {"Stream Name", "Country", "Year of Date", "Month of Date", "Value"}
        if required.issubset(df.columns):
            df_long = df[["Stream Name", "Country", "Year of Date", "Month of Date", "Value"]].copy()
            df_long = df_long.rename(columns={
                "Stream Name": "Stream",
                "Year of Date": "year",
                "Month of Date": "month",
                "Value": "value"
            })
            df_long["year"] = pd.to_numeric(df_long["year"], errors="coerce").astype("Int64")
            df_long["year"] = df_long["year"].astype(str)
            month_map = {
                "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
                "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
            }
            df_long["month_idx"] = df_long["month"].map(month_map)
            df_long["value"] = pd.to_numeric(df_long["value"], errors="coerce").fillna(0)
            df_long = df_long[
                (df_long["value"] > 0) &
                              (df_long["Country"].notna()) & 
                (df_long["Stream"].notna()) &
                (df_long["month_idx"].notna())
            ].copy()
            df_long["month_idx"] = df_long["month_idx"].astype(int)
            print(f"DEBUG: Loaded {len(df_long)} monthly bar records from DB")
        return df, df_long
    except Exception as e:
        print(f"Error loading monthly bar data from DB: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame(), pd.DataFrame()


def _load_countries_geojson():
    """Load and cache world countries GeoJSON for Mapbox choropleths."""
    global COUNTRIES_GEOJSON
    if COUNTRIES_GEOJSON is not None:
        return COUNTRIES_GEOJSON
    url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            COUNTRIES_GEOJSON = json.load(response)
            print("DEBUG: Loaded countries GeoJSON for mapbox")
    except Exception as e:
        print(f"WARNING: Failed to load countries GeoJSON: {e}")
        COUNTRIES_GEOJSON = None
    return COUNTRIES_GEOJSON


def load_monthly_map_from_db(raw_export=False):
    """
    Load monthly map data from the database instead of CSV.
    Expected columns from query:
        country, month_year (YYYY-MM), value, country_id
    """
    query = """
        SELECT DISTINCT ON (p.country, TO_CHAR(p.date, 'YYYY-MM'))
            p.country,
            TO_CHAR(p.date, 'YYYY-MM') AS month_year,
            q.latitude,
            q.longitude,
            p.value,
            p.country_id
        FROM t_wcod_monthly_stream_production p
        LEFT JOIN dim_country q
            ON q.dim_country_id = p.country_id
        WHERE q.latitude is NOT NULL
        ORDER BY
            p.country,
            TO_CHAR(p.date, 'YYYY-MM'),
            p.value DESC;
    """
    try:
        rows = execute_query(query)
        if not rows:
            print("DEBUG: No monthly map rows returned from DB")
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        if df.empty:
            print("DEBUG: Monthly map DataFrame is empty after conversion")
            return pd.DataFrame()
        df.columns = df.columns.str.strip()
        
        if raw_export:
            print(f"DEBUG: Returning raw monthly map data with {len(df)} rows")
            return df
            
        required_cols = {"country", "month_year", "value"}
        if not required_cols.issubset(set(df.columns)):
            print(f"DEBUG: Monthly map DB result missing required columns. Columns: {df.columns.tolist()}")
            return pd.DataFrame()
        df["year"] = df["month_year"].astype(str).str.split("-").str[0]
        df["month"] = pd.to_numeric(df["month_year"].astype(str).str.split("-").str[1], errors="coerce")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.rename(columns={"country": "Country"})
        
        # Add GeoCountry for map matching while keeping Country for labels
        df["GeoCountry"] = df["Country"].apply(lambda x: COUNTRY_NAME_MAPPING.get(x, x))
        
        df_long = df[["Country", "GeoCountry", "year", "month", "value"]].copy()
        df_long["year"] = df_long["year"].astype(str)
        df_long = df_long.dropna(subset=["Country", "year", "month", "value"])
        df_long["month"] = df_long["month"].astype(int)
        df_long = df_long[df_long["value"] > 0].copy()
        print(f"DEBUG: Loaded {len(df_long)} monthly map records from DB")
        return df_long
    except Exception as e:
        print(f"Error loading monthly map data from DB: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def load_yearly_map_from_db(raw_export=False):
    """
    Load yearly map data from the database, averaging monthly values per year.
    """
    query = """
        WITH monthly_distinct AS (
            SELECT DISTINCT ON (p.country, TO_CHAR(p.date, 'YYYY-MM'))
                p.country,
                TO_CHAR(p.date, 'YYYY-MM') AS month_year,
                TO_CHAR(p.date, 'YYYY') AS year,
                p.value,
                p.country_id,
                q.latitude,
                q.longitude
            FROM t_wcod_monthly_stream_production p
            LEFT JOIN dim_country q
                ON q.dim_country_id = p.country_id
            WHERE q.latitude is NOT NULL
            ORDER BY p.country, TO_CHAR(p.date, 'YYYY-MM'), p.value DESC
        )
        SELECT
            country,
            year,
            AVG(value) AS value,
            country_id,
            latitude,
            longitude
        FROM monthly_distinct
        GROUP BY
            country,
            year,
            country_id,
            latitude,
            longitude
        ORDER BY year;
    """
    try:
        rows = execute_query(query)
        if not rows:
            print("DEBUG: No yearly map rows returned from DB")
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        if df.empty:
            print("DEBUG: Yearly map DataFrame is empty after conversion")
            return pd.DataFrame()
        df.columns = df.columns.str.strip()
        
        if raw_export:
            print(f"DEBUG: Returning raw yearly map data with {len(df)} rows")
            return df
            
        required_cols = {"country", "year", "value"}
        if not required_cols.issubset(set(df.columns)):
            print(f"DEBUG: Yearly map DB result missing required columns. Columns: {df.columns.tolist()}")
            return pd.DataFrame()
        df = df.rename(columns={"country": "Country"})
        # Add GeoCountry for map matching while keeping Country for labels
        df["GeoCountry"] = df["Country"].apply(lambda x: COUNTRY_NAME_MAPPING.get(x, x))
        
        df["year"] = df["year"].astype(str)
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df_long = df[["Country", "GeoCountry", "year", "value"]].copy()
        df_long = df_long.dropna(subset=["Country", "year", "value"])
        df_long = df_long[df_long["value"] > 0].copy()
        print(f"DEBUG: Loaded {len(df_long)} yearly map records from DB")
        return df_long
    except Exception as e:
        print(f"Error loading yearly map data from DB: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()
    

def load_map_data():
    """Load map data - both yearly and monthly"""
    map_yearly_long = load_yearly_map_from_db()
    map_monthly_long = load_monthly_map_from_db()
    return map_yearly_long, map_monthly_long

def load_grades_data():
    """Load grades/streams data.
    Yearly grades are now fetched dynamically from the database per-country.
    Monthly grades remain DB-backed and are fetched on-demand elsewhere.
    """
    yearly_grades = pd.DataFrame()   # fetched per country via load_yearly_grades_for_country
    monthly_grades = pd.DataFrame()  # fetched per country via load_monthly_grades_for_country
    return yearly_grades, monthly_grades


def load_yearly_grades_for_country(countries):
    """Fetch yearly grades/streams for given countries from DB.
    
    Args:
        countries: Can be a single country name (str), list of countries, or empty list/None for all countries
    """
    # Normalize input to list
    if not countries:
        country_list = []
    elif isinstance(countries, str):
        country_list = [countries]
    else:
        country_list = list(countries)
    
    # Build query with appropriate WHERE clause
    base_query = """
        SELECT
            a.crude_name AS "CrudeOil",
            c.BSP_link AS "profile_url",
            a.country_name || ' ' || a.crude_name AS "crude_color",
            1 AS avg_calculation1
        FROM fact_wcod_crude a
        LEFT JOIN dim_country grp
            ON a.country_id = grp.dim_country_id
        LEFT JOIN fact_wcod_crude_bsp_links c 
            ON a.crude_id = c.crude_id
    """
    
    # If empty list (all countries), don't add WHERE clause
    # If single country, use = 
    # If multiple countries, use IN with tuple
    if not country_list:
        # All countries - no WHERE clause
        query = base_query + ";"
        params = {}
    elif len(country_list) == 1:
        # Single country
        query = base_query + " WHERE a.country_name = :country;"
        params = {"country": country_list[0]}
    else:
        # Multiple countries - use IN clause with tuple
        # Build placeholders for SQLAlchemy text() with bindparam expanding
        placeholders = ", ".join([f":country_{i}" for i in range(len(country_list))])
        query = base_query + f" WHERE a.country_name IN ({placeholders});"
        params = {f"country_{i}": country for i, country in enumerate(country_list)}
    
    try:
        rows = execute_query(query, params)
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        df.columns = df.columns.str.strip()
        # Normalize stream column
        if "CrudeOil" in df.columns:
            df = df.rename(columns={"CrudeOil": "Stream"})
        elif "Stream Name" in df.columns:
            df = df.rename(columns={"Stream Name": "Stream"})
        elif "stream_name" in df.columns:
            df = df.rename(columns={"stream_name": "Stream"})
        # Normalize color column naming
        if "CRUDE COLOR" in df.columns:
            df = df.rename(columns={"CRUDE COLOR": "crude_color"})
        # Ensure helper columns exist
        for col in ["crude_color", "avg_calculation1"]:
            if col not in df.columns:
                if col == "crude_color":
                    df[col] = df.get("Stream", "")
                else:
                    df[col] = 1
        df = df.drop_duplicates(subset=["Stream"]).reset_index(drop=True)
        return df
    except Exception as e:
        print(f"Error loading yearly grades data from DB for countries '{countries}': {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def get_yearly_grades_for_country(countries):
    """Cached accessor for yearly grades per country/countries."""
    global YEARLY_GRADES_CACHE
    # Create cache key from sorted country list
    if not countries:
        key = "__ALL__"
    elif isinstance(countries, str):
        key = countries
    else:
        key = "__".join(sorted(countries))
    
    if key in YEARLY_GRADES_CACHE:
        return YEARLY_GRADES_CACHE[key]
    df = load_yearly_grades_for_country(countries)
    YEARLY_GRADES_CACHE[key] = df
    return df


def load_monthly_grades_for_country(countries):
    """Fetch monthly grades/streams for given countries from DB.
    
    Args:
        countries: Can be a single country name (str), list of countries, or empty list/None for all countries
    """
    # Normalize input to list
    if not countries:
        country_list = []
    elif isinstance(countries, str):
        country_list = [countries]
    else:
        country_list = list(countries)
    
    # Build query with appropriate WHERE clause
    base_query = """
        SELECT DISTINCT ON (A.stream_name)
            A.stream_name,
            b.BSP_link,
            A.country || ' ' || A.stream_name AS crude_color,
            1 AS avg_calculation1
        FROM t_wcod_monthly_stream_production A
        LEFT JOIN fact_wcod_crude_bsp_links b 
            ON A.crude_id = b.crude_id
    """
    
    # If empty list (all countries), don't add WHERE clause for country
    # If single country, use = 
    # If multiple countries, use IN
    if not country_list:
        # All countries - only filter out 'Total' stream
        query = base_query + " WHERE A.stream_name != 'Total' ORDER BY A.stream_name;"
        params = {}
    elif len(country_list) == 1:
        # Single country
        query = base_query + " WHERE A.country = :country AND A.stream_name != 'Total' ORDER BY A.stream_name;"
        params = {"country": country_list[0]}
    else:
        # Multiple countries - use IN clause
        placeholders = ", ".join([f":country_{i}" for i in range(len(country_list))])
        query = base_query + f" WHERE A.country IN ({placeholders}) AND A.stream_name != 'Total' ORDER BY A.stream_name;"
        params = {f"country_{i}": country for i, country in enumerate(country_list)}
    
    try:
        rows = execute_query(query, params)
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        df.columns = df.columns.str.strip()
        # Normalize stream column
        if "stream_name" in df.columns:
            df = df.rename(columns={"stream_name": "Stream"})
        elif "Stream Name" in df.columns:
            df = df.rename(columns={"Stream Name": "Stream"})
        elif "CrudeOil" in df.columns:
            df = df.rename(columns={"CrudeOil": "Stream"})
        # Ensure expected helper columns exist
        for col in ["crude_color", "avg_calculation1"]:
            if col not in df.columns:
                if col == "crude_color":
                    df[col] = df.get("Stream", "")
                else:
                    df[col] = 1
        return df
    except Exception as e:
        print(f"Error loading monthly grades data from DB for countries '{countries}': {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def get_monthly_grades_for_country(countries):
    """Cached accessor for monthly grades per country/countries."""
    global MONTHLY_GRADES_CACHE
    # Create cache key from sorted country list
    if not countries:
        key = "__ALL__"
    elif isinstance(countries, str):
        key = countries
    else:
        key = "__".join(sorted(countries))
    
    if key in MONTHLY_GRADES_CACHE:
        return MONTHLY_GRADES_CACHE[key]
    df = load_monthly_grades_for_country(countries)
    MONTHLY_GRADES_CACHE[key] = df
    return df


def build_monthly_table_from_bar(bar_long_monthly):
    """Fallback monthly table builder using BAR_LONG_MONTHLY when DB table data is empty."""
    if bar_long_monthly is None or bar_long_monthly.empty:
        return pd.DataFrame(), {}
    
    required_cols = {"Stream", "year", "month_idx", "value"}
    if not required_cols.issubset(set(bar_long_monthly.columns)):
        return pd.DataFrame(), {}
    
    df = bar_long_monthly.copy()
    # Normalize month name
    month_map = {
        1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
        7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
    }
    if "month" not in df.columns:
        df["month"] = df["month_idx"].map(month_map)
    df["value"] = pd.to_numeric(df["value"], errors="coerce").fillna(0)
    df = df[df["value"] > 0]
    if df.empty:
        return pd.DataFrame(), {}
    
    group = df.groupby(["Stream", "year", "month"])["value"].sum().reset_index()
    streams = sorted(group["Stream"].dropna().unique().tolist())
    years = sorted(group["year"].dropna().unique().tolist(), reverse=True)
    months_order = ["January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December"]
    
    table_df = pd.DataFrame({"Crude": streams})
    table_df.set_index("Crude", inplace=True)
    year_to_month_cols = {}
    new_columns = {}
    
    for year in years:
        year_str = str(year)
        year_to_month_cols[year_str] = []
        for month in months_order:
            mask = (group["year"] == year) & (group["month"] == month)
            if not mask.any():
                continue
            month_values = (
                group.loc[mask, ["Stream", "value"]]
                .drop_duplicates(subset=["Stream"])
                .set_index("Stream")["value"]
            )
            if month_values.empty:
                continue
            col_name = f"{year_str}_{month}"
            new_columns[col_name] = table_df.index.map(month_values)
            year_to_month_cols[year_str].append({"month": month, "column": col_name})
    
    if new_columns:
        table_df = pd.concat([table_df, pd.DataFrame(new_columns, index=table_df.index)], axis=1)
    
    table_df.reset_index(inplace=True)
    return table_df, year_to_month_cols


# Comprehensive color mapping for monthly crudes (fallback for missing colors)
MONTHLY_CRUDE_COLORS = {
    "Agbami": "#0077A3",
    "Akpo Blend": "#5A8FB8",
    "Alaska North Slope": "#0077A3",
    "Algerian Condensate": "#4F8BB6",
    "Al-Shaheen": "#2CA02C",
    "Al-shaheen": "#2CA02C",  # Alternative spelling
    "Al Shaheen": "#2CA02C",  # Alternative spelling
    "Alvheim": "#5C8FB8",
    "Amenam Blend": "#A9A9A9",
    "Anyala-madu": "#9B5C42",
    "Arab Extra Light": "#5F5F5F",
    "Arab Heavy": "#5C8FB8",
    "Arab Light": "#A9A9A9",
    "Arab Medium": "#2E3D4F",
    "Arab Super Light": "#0077A3",
    "Arco": "#0077A3",
    "Asgard Blend": "#9B5C42",
    "Atapu": "#7E8BC7",
    "Azeri (Btc)": "#FF6A00",
    "Azeri Light": "#0077A3",
    "Bach Ho": "#D62728",
    "Bakken": "#C9D9A3",
    "Balder": "#5F5F5F",
    "Banoco Arab Medium": "#C7C7C7",
    "Basrah Heavy": "#A9A9A9",
    "Basrah Light": "#2E3D4F",
    "Basrah Medium": "#5A8FB8",
    "Belayim Blend": "#1F3B5D",
    "Bonga": "#5A8FB8",
    "Bonny Light": "#2E3D4F",
    "Brass River": "#0077A3",
    "Brent Blend": "#2E3D4F",
    "Buzios": "#5A8FB8",
    "Cabinda": "#FF6A00",
    "Castilla": "#1F3B5D",
    "Cepu": "#9B5C42",
    "Champion": "#7F7F7F",
    "Clair": "#C35A2E",
    "Clifhead": "#C7C7C7",
    "Clov": "#1F3B5D",
    "Condensate": "#2E3D4F",
    "Cossack": "#8C564B",
    "CPC Blend - Russia": "#C35A2E",
    "Cpc Blend - Russia": "#C35A2E",  # Alternative spelling
    "Dalia": "#FF6A00",
    "Danish Crude Blend": "#A9A9A9",
    "Dar Blend South Sudan": "#7E8BC7",
    "Das Blend": "#9B5C42",
    "Deodorized Field Condensate": "#98DF8A",
    "Djeno": "#7E8BC7",
    "Doba": "#C9D9A3",
    "Dubai": "#0077A3",
    "Duri": "#C9D9A3",
    "Dussafu": "#7E8BC7",
    "Eagle Ford": "#FF6A00",
    "Egina": "#0077A3",
    "Ekofisk Blend": "#2E3D4F",
    "Eocene": "#5F5F5F",
    "Erha": "#9B5C42",
    "Escalante": "#C9D9A3",
    "Escravos": "#2E3D4F",
    "Espo Blend": "#C9D9A3",
    "Flotta Gold": "#A9A9A9",
    "Forcados": "#A9A9A9",
    "Forties Blend": "#5A8FB8",
    "Frade": "#FF6A00",
    "Gindungo": "#0077A3",
    "Girassol": "#7E8BC7",
    "Goliat": "#2E3D4F",
    "Grane": "#5F5F5F",
    "Gudrun Blend": "#A9A9A9",
    "Gullfaks Blend": "#FF6A00",
    "Heavy Louisiana Sweet": "#A9A9A9",
    "Heidrun": "#C35A2E",
    "Hoops Blend": "#0077A3",
    "Hungo": "#9B5C42",
    "Ichthys Condensate": "#7F7F7F",
    "Iran Heavy": "#FF6A00",
    "Iran Light": "#C35A2E",
    "Isthmus": "#5A8FB8",
    "Johan Sverdrup": "#5A8FB8",
    "Jubarte": "#C9D9A3",
    "Jubilee": "#5F5F5F",
    "Kashagan": "#5A8FB8",
    "Kebco": "#C9D9A3",
    "Ketapang": "#C7C7C7",
    "Khafji": "#5F5F5F",
    "Kikeh": "#DBDB8D",
    "Kimanis": "#1F3B5D",
    "Kirkuk": "#0077A3",
    "Kissanje Blend": "#5A8FB8",
    "Kumkol": "#C35A2E",
    "Kurdish Crude": "#C9D9A3",
    "Kutubu": "#5A8FB8",
    "Kuwait": "#5F5F5F",
    "Kuwait Export Heavy": "#7E8BC7",
    "Kuwait Super Light": "#FF6A00",
    "Lalang": "#1F77B4",
    "Lapa": "#C9D9A3",
    "Light Louisiana Sweet": "#1F3B5D",
    "Liza": "#0077A3",
    "Mandji": "#FF6A00",
    "Mares Blend": "#AEC7E8",
    "Marlim": "#A9A9A9",
    "Mars Blend": "#C9D9A3",
    "Maya": "#1F3B5D",
    "Medanito": "#9B5C42",
    "Mero": "#FF6A00",
    "Minas": "#1F3B5D",
    "Miri": "#5F5F5F",
    "Mostarda": "#7E8BC7",
    "Mubarras Blend": "#1F77B4",
    "Murban": "#FF6A00",
    "Napo": "#98DF8A",
    "Nemba": "#C35A2E",
    "Nile Blend South Sudan": "#C35A2E",
    "Nile Blend Sudan": "#1F3B5D",
    "Nkossa": "#A9A9A9",
    "Novy Port": "#1F3B5D",
    "Oguendjo Blend": "#5A8FB8",
    "Okwuibome": "#7E8BC7",
    "Olmeca": "#C9D9A3",
    "Olombendo": "#5F5F5F",
    "Oman": "#7E8BC7",
    "Oriente": "#FF9896",
    "Oseberg": "#7E8BC7",
    "Other Crudes - Algeria": "#1F3B5D",
    "Other Crudes - Angola": "#2E3D4F",
    "Other Crudes - Argentina": "#A9A9A9",
    "Other Crudes - Azerbaijan": "#C9D9A3",
    "Other Crudes - Brazil": "#2E3D4F",
    "Other Crudes - Chad": "#A9A9A9",
    "Other Crudes - Colombia (Brazzaville)": "#0077A3",
    "Other Crudes - Denmark": "#C35A2E",
    "Other Crudes - Egypt": "#1F3B5D",
    "Other Crudes - Ghana": "#C9D9A3",
    "Other Crudes - Indonesia": "#C35A2E",
    "Other Crudes - Iran": "#5F5F5F",
    "Kazakhstan": "#5F5F5F",
    "Other Crudes - Kuwait": "#C35A2E",
    "Other Crudes - Malaysia": "#A9A9A9",
    "Other Crudes - Nigeria": "#0077A3",
    "Other Crudes - Norway": "#1F3B5D",
    "Other Crudes - Russia": "#1F3B5D",
    "Other Crudes - Sudan": "#FF6A00",
    "Kingdom": "#9B5C42",
    "States": "#5F5F5F",
    "Payara Gold": "#C35A2E",
    "Pazflor": "#C9D9A3",
    "Peregrino": "#5A8FB8",
    "Plutonio": "#5A8FB8",
    "Poseidon": "#1F3B5D",
    "Pyrenees": "#C49C94",
    "Qua Iboe": "#9B5C42",
    "Qatar Land": "#C7C7C7",
    "Qatar Low Sulphur Condensate": "#BCBD22",
    "Qatar Marine": "#DBDB8D",
    "Rabi Blend": "#C9D9A3",
    "Rabi Light": "#FF6A00",
    "Roncador": "#1F3B5D",
    "Ruby": "#F7B6D2",
    "Saharan Blend": "#C9D9A3",
    "Sakhalin Blend": "#5F5F5F",
    "Sangos": "#A9A9A9",
    "Sankofa": "#1F3B5D",
    "Sapinhoa": "#9B5C42",
    "Saturno": "#C35A2E",
    "Schiehallion Blend": "#5F5F5F",
    "Sepia": "#5A8FB8",
    "Sepat": "#BCBD22",
    "Seria Light": "#17BECF",
    "Siberian Light": "#5A8FB8",
    "Skarv": "#0077A3",
    "Sokol": "#A9A9A9",
    "Southern Green Canyon": "#FF6A00",
    "Stag": "#9EDAE5",
    "Suez Blend": "#FF6A00",
    "Sururu": "#0077A3",
    "Tapis": "#2E3D4F",
    "Ten": "#9B5C42",
    "Tengiz": "#A9A9A9",
    "Thang Long": "#FFBB78",
    "Thunder Horse": "#FF6A00",
    "Troll": "#C9D9A3",
    "Tupi": "#9B5C42",
    "Umm Lulu": "#5F5F5F",
    "Unity Gold": "#5A8FB8",
    "Upper Zakum": "#9B5C42",
    "Urals": "#9B5C42",
    "Varandey": "#7E8BC7",
    "Vasconia": "#7E8BC7",
    "Vityaz": "#0069AA",
    "Wafra": "#5F5F5F",
    "Wandoo": "#2CA02C",
    "West Texas Intermediate": "#AEC7E8",
    "West Texas Intermediate (Midland)": "#0077A3",
    "(Midland)": "#474F5C",
    "West Texas Light": "#B4B4B4",
    "West Texas Sour": "#1F3B5D",
    "Western Desert Blend": "#FF6A00",
    "YK Blend": "#595959"
}


def load_stream_color_order():
    """Load stream color and order from grades CSV files"""
    def _is_valid_color(val):
        if not isinstance(val, str):
            return False
        v = val.strip()
        if v.startswith("#") and len(v) in (4, 7):
            return True
        if v.lower().startswith("rgb"):
            return True
        return False
    # Default fallback values (current hardcoded lists)
    default_yearly = [
        ("Arco", "#0069aa"),
        ("Siberian Light", "#313849"),
        ("Vityaz", "#0069aa"),
        ("YK Blend", "#595959"),
        ("Sakhalin Blend", "#4e83bb"),
        ("Varandey", "#a6a6a6"),
        ("Novy Port", "#a95b41"),
        ("Sokol", "#cb4515"),
        ("Other Crudes - Russia", "#a95b41"),
        ("Espo Blend", "#20295e"),
        ("Urals", "#826ecc")
    ]
    
    default_monthly = [
        ("Arco", "#0069aa"),
        ("Cpc Blend - Russia", "#cb4515"),
        ("Espo Blend", "#badf97"),
        ("Novy Port", "#20295e"),
        ("Other Crudes - Russia", "#313849"),
        ("Sakhalin Blend", "#595959"),
        ("Siberian Light", "#4e83bb"),
        ("Sokol", "#a6a6a6"),
        ("Urals", "#a95b41"),
        ("Varandey", "#826ecc")
    ]
    
    yearly_order = []
    monthly_order = []
    
    # Keep existing yearly colors/order static (per current design)
    yearly_order = default_yearly[:]
    
    try:
        # Load monthly stream color/order via DB for default country (Russia fallback)
        default_country = "Russia"
        monthly_df = load_monthly_grades_for_country(default_country)
        if not monthly_df.empty:
            # Use crude_color if present for ordering, else stream
            stream_col = "Stream" if "Stream" in monthly_df.columns else None
            color_col = "crude_color" if "crude_color" in monthly_df.columns else None
            default_color_map = dict(default_monthly)
            # Merge comprehensive color mapping with default_monthly (comprehensive takes precedence)
            comprehensive_color_map = {**default_color_map, **MONTHLY_CRUDE_COLORS}
            
            if stream_col and color_col:
                for _, row in monthly_df.iterrows():
                    stream = str(row[stream_col]).strip() if pd.notna(row[stream_col]) else None
                    color = str(row[color_col]).strip() if pd.notna(row[color_col]) else None
                    # If color is not a valid css/hex color, fall back to comprehensive color mapping
                    if stream:
                        if not _is_valid_color(color):
                            # Try comprehensive mapping first, then default_monthly, then gray fallback
                            color = comprehensive_color_map.get(stream, default_color_map.get(stream, "#808080"))
                        monthly_order.append((stream, color))
            elif stream_col:
                streams_in_result = monthly_df[stream_col].dropna().unique().tolist()
                for stream in streams_in_result:
                    stream_str = str(stream).strip()
                    # Use comprehensive color mapping first, then default_monthly, then gray fallback
                    color = comprehensive_color_map.get(stream_str, default_color_map.get(stream_str, "#808080"))
                    monthly_order.append((stream_str, color))
    except Exception as e:
        print(f"Error loading monthly stream color/order from DB: {e}")
        import traceback
        traceback.print_exc()
    
    # Use loaded data if available, otherwise fall back to defaults
    def sort_by_reference(order_list, reference_pairs):
        """Sort (stream, color) pairs to match reference order of stream names."""
        if not order_list:
            return []
        reference_names = [name for name, _ in reference_pairs]
        reference_index = {name: idx for idx, name in enumerate(reference_names)}
        in_reference = [pair for pair in order_list if pair[0] in reference_index]
        in_reference.sort(key=lambda pair: reference_index[pair[0]])
        not_in_reference = [pair for pair in order_list if pair[0] not in reference_index]
        return in_reference + not_in_reference
    
    yearly_result = sort_by_reference(yearly_order, default_yearly) if yearly_order else default_yearly
    monthly_result = sort_by_reference(monthly_order, default_monthly) if monthly_order else default_monthly
    
    return yearly_result, monthly_result


def _ensure_color_maps():
    """Initialize color maps/orders if missing without reloading all data."""
    global YEARLY_STREAM_COLOR_ORDER, MONTHLY_STREAM_COLOR_ORDER
    global STREAM_COLOR_ORDERS, STREAM_COLOR_MAPS, STREAM_ORDERS
    # If already built, ensure maps exist
    if STREAM_COLOR_MAPS and STREAM_COLOR_ORDERS and STREAM_ORDERS:
        # Still merge comprehensive colors to ensure all streams have colors
        if "monthly" in STREAM_COLOR_MAPS:
            STREAM_COLOR_MAPS["monthly"] = {**STREAM_COLOR_MAPS["monthly"], **MONTHLY_CRUDE_COLORS}
        return
    # Build orders if missing
    if not YEARLY_STREAM_COLOR_ORDER or not MONTHLY_STREAM_COLOR_ORDER:
        YEARLY_STREAM_COLOR_ORDER, MONTHLY_STREAM_COLOR_ORDER = load_stream_color_order()
    STREAM_COLOR_ORDERS = {
        "yearly": YEARLY_STREAM_COLOR_ORDER,
        "monthly": MONTHLY_STREAM_COLOR_ORDER
    }
    STREAM_COLOR_MAPS = {mode: {name: color for name, color in order} for mode, order in STREAM_COLOR_ORDERS.items()}
    # Merge comprehensive monthly colors into the color map (comprehensive takes precedence)
    if "monthly" in STREAM_COLOR_MAPS:
        STREAM_COLOR_MAPS["monthly"] = {**STREAM_COLOR_MAPS["monthly"], **MONTHLY_CRUDE_COLORS}
    STREAM_ORDERS = {mode: [name for name, _ in order] for mode, order in STREAM_COLOR_ORDERS.items()}

def load_table():
    """Load table data: yearly from DB query; monthly from DB monthly production."""
    yearly_df = pd.DataFrame()
    monthly_df = pd.DataFrame()
    year_to_month_cols = {}
    
    # Raw dataframes for export
    yearly_raw_export = pd.DataFrame()
    monthly_raw_export = pd.DataFrame()
    
    try:
        # Load yearly table data from DB
        yearly_query = """
            SELECT
                a.country_name AS "Country",
                a.crude_name AS "CrudeOil",
                b.BSP_link AS profile_url,
                EXTRACT(YEAR FROM a.yr) AS "YearReported",
                a.production_kbpd AS "ProductionDataValue",
                a.exports_kbpd AS "ExportDataValue"
            FROM fact_wcod_crude a
            LEFT JOIN dim_country grp
                ON a.country_id = grp.dim_country_id
            LEFT JOIN fact_wcod_crude_bsp_links b
                ON a.crude_id = b.crude_id
            ORDER BY a.crude_name ASC;
        """
        yearly_rows = execute_query(yearly_query)
        if yearly_rows:
            yearly_raw = pd.DataFrame(yearly_rows)
            yearly_raw.columns = yearly_raw.columns.str.strip()
            
            # Capture raw export data immediately (before renaming profile_url if strict, 
            # but user query has profile_url alias so it's fine). 
            # However, code below renames "BSP link" to "profile_url".
            # The query ALREADY constructs "profile_url" alias. 
            # Let's check if the previous code was handling potential missing alias or just safeguard.
            # Query has: b.BSP_link AS profile_url. So column IS "profile_url".
            # The existing code had: if "BSP link" in yearly_raw.columns...
            # This implies maybe sometimes execute_query returns original column names? 
            # Or maybe the alias isn't respected by some driver? 
            # In any case, we want exactly what "query returns".
            
            yearly_raw_export = yearly_raw.copy()
            
            # Normalize optional column names for INTERNAL use
            if "BSP link" in yearly_raw.columns and "profile_url" not in yearly_raw.columns:
                yearly_raw = yearly_raw.rename(columns={"BSP link": "profile_url"})
            yearly_raw["YearReported"] = pd.to_numeric(yearly_raw.get("YearReported"), errors="coerce")
            yearly_raw["ProductionDataValue"] = pd.to_numeric(yearly_raw.get("ProductionDataValue"), errors="coerce")
            yearly_raw = yearly_raw.dropna(subset=["CrudeOil", "YearReported", "ProductionDataValue"])
            
            # Aggregate by crude and year (sum production) to get one value per year column
            yearly_agg = (
                yearly_raw
                .groupby(["CrudeOil", "YearReported"], as_index=False)["ProductionDataValue"]
                .sum()
            )
            
            crudes = sorted(yearly_agg["CrudeOil"].dropna().unique())
            years = sorted(yearly_agg["YearReported"].dropna().unique(), reverse=True)
            
            yearly_df = pd.DataFrame({"CrudeOil": crudes})
            for year in years:
                year_str = str(int(year))
                year_values = (
                    yearly_agg[yearly_agg["YearReported"] == year]
                    .set_index("CrudeOil")["ProductionDataValue"]
                )
                yearly_df[year_str] = yearly_df["CrudeOil"].map(year_values)
            
            # Add profile_url metadata if available
            if "profile_url" in yearly_raw.columns:
                profile_map = (
                    yearly_raw[["CrudeOil", "profile_url"]]
                    .dropna(subset=["CrudeOil"])
                    .drop_duplicates(subset=["CrudeOil"])
                    .set_index("CrudeOil")["profile_url"]
                )
                yearly_df["profile_url"] = yearly_df["CrudeOil"].map(profile_map)
            
            # Add CI Rank metadata if available
            if "ci_rank" in yearly_raw.columns:
                ci_map = (
                    yearly_raw[["CrudeOil", "ci_rank"]]
                    .dropna(subset=["CrudeOil"])
                    .drop_duplicates(subset=["CrudeOil"])
                    .set_index("CrudeOil")["ci_rank"]
                )
                yearly_df["CI Rank"] = yearly_df["CrudeOil"].map(ci_map)
            
            # Add Country metadata if available
            if "Country" in yearly_raw.columns:
                country_map = (
                    yearly_raw[["CrudeOil", "Country"]]
                    .dropna(subset=["CrudeOil"])
                    .drop_duplicates(subset=["CrudeOil"])
                    .set_index("CrudeOil")["Country"]
                )
                yearly_df["Country"] = yearly_df["CrudeOil"].map(country_map)
            
        # Load monthly table data
        monthly_query = """
            SELECT     
                c.crude_name AS "Crude",
                c.ci_rank,
                c.api,
                c.sulfur_pct,
                l.bsp_link AS profile_url,
                EXTRACT(YEAR FROM a.date) AS "Year of Date",
                TO_CHAR(a.date, 'FMMonth') AS "Month of Date",
                a.value AS "Value",
                a.country AS "_internal_country"
            FROM t_wcod_monthly_stream_production a

            -- Latest crude master data
            LEFT JOIN (
                SELECT DISTINCT ON (crude_id) 
                    crude_id,
                    crude_name,
                    ci_rank,
                    api,
                    sulfur_pct
                FROM fact_wcod_crude
                ORDER BY crude_id, yr DESC
            ) c 
                ON a.crude_id = c.crude_id

            -- Profile URL
            LEFT JOIN fact_wcod_crude_bsp_links l
                ON a.crude_id = l.crude_id
        """
        monthly_rows = execute_query(monthly_query)
        if monthly_rows:
            monthly_raw = pd.DataFrame(monthly_rows)
            monthly_raw.columns = monthly_raw.columns.str.strip()
            
            monthly_raw_export = monthly_raw.copy()
            
            # Normalize columns
            monthly_raw = monthly_raw.rename(columns={
                "ci_rank": "CI Rank",
                "api": "API",
                "sulfur_pct": "Sulfur"
            })
            
            # Clean numeric fields
            monthly_raw["Year of Date"] = pd.to_numeric(monthly_raw.get("Year of Date"), errors="coerce")
            monthly_raw["Value"] = pd.to_numeric(monthly_raw.get("Value"), errors="coerce")
            
            # Drop invalid rows
            monthly_raw = monthly_raw.dropna(subset=["Crude", "Year of Date", "Month of Date", "Value"])
        
            if not monthly_raw.empty:
                # Aggregate by Crude/Year/Month (sum values) to ensure one value per cell
                monthly_agg = (
                    monthly_raw
                    .groupby(["Crude", "Year of Date", "Month of Date"], as_index=False)["Value"]
                    .sum()
                )
                
                metadata_cols = ["Crude", "CI Rank", "API", "Sulfur", "profile_url"]
                available_metadata = [col for col in metadata_cols if col in monthly_raw.columns]
                
                if available_metadata:
                    monthly_df = monthly_raw[available_metadata].drop_duplicates(subset=["Crude"]).copy()
                else:
                    monthly_df = pd.DataFrame({"Crude": monthly_raw["Crude"].dropna().unique()})
                
                monthly_df = monthly_df.sort_values("Crude")
                monthly_df.set_index("Crude", inplace=True)
                
                months_order = ['January', 'February', 'March', 'April', 'May', 'June',
                               'July', 'August', 'September', 'October', 'November', 'December']
                
                years = sorted(monthly_agg["Year of Date"].dropna().unique(), reverse=True)
                
                year_to_month_cols = {}
                new_columns = {}
                
                for year in years:
                    year_str = str(int(year))
                    year_to_month_cols[year_str] = []
                    for month in months_order:
                        mask = (
                                (monthly_agg["Year of Date"] == year) &
                                (monthly_agg["Month of Date"] == month)
                        )
                        if not mask.any():
                            continue
                        
                        month_values = (
                                monthly_agg.loc[mask, ["Crude", "Value"]]
                            .drop_duplicates(subset=["Crude"])
                                .set_index("Crude")["Value"]
                        )
                        if month_values.empty:
                            continue
                        
                        col_name = f"{year_str}_{month}"
                        new_columns[col_name] = monthly_df.index.map(month_values)
                        year_to_month_cols[year_str].append({"month": month, "column": col_name})
                
                if new_columns:
                    new_cols_df = pd.DataFrame(new_columns, index=monthly_df.index)
                    monthly_df = pd.concat([monthly_df, new_cols_df], axis=1)
                
                monthly_df.reset_index(inplace=True)
            else:
                monthly_df = pd.DataFrame()
                year_to_month_cols = {}
        else:
            monthly_df = pd.DataFrame()
            year_to_month_cols = {}

        # Fallback: if monthly table is empty, rebuild from BAR_LONG_MONTHLY to avoid blank table
        if (monthly_df.empty or not year_to_month_cols) and not BAR_LONG_MONTHLY.empty:
            fallback_df, fallback_year_to_month_cols = build_monthly_table_from_bar(BAR_LONG_MONTHLY)
            if not fallback_df.empty:
                monthly_df = fallback_df
                year_to_month_cols = fallback_year_to_month_cols
                print(f"DEBUG: Using fallback monthly table from BAR_LONG_MONTHLY ({len(monthly_df)} rows, {len(year_to_month_cols)} years)")
    except Exception as e:
        print(f"Error loading table data: {e}")
        import traceback
        traceback.print_exc()
        # Fallback on error: try to build monthly table from already loaded bar data
        if (monthly_df is None or monthly_df.empty) and not BAR_LONG_MONTHLY.empty:
            fallback_df, fallback_year_to_month_cols = build_monthly_table_from_bar(BAR_LONG_MONTHLY)
            if not fallback_df.empty:
                monthly_df = fallback_df
                year_to_month_cols = fallback_year_to_month_cols
                print(f"DEBUG: Table fallback from BAR_LONG_MONTHLY after error ({len(monthly_df)} rows, {len(year_to_month_cols)} years)")
    
    # Final cleanup to remove 'nan' strings and NaNs
    if not yearly_df.empty:
        yearly_df = yearly_df.fillna("")
        # Replace string "nan" if it leaked through string conversions
        yearly_df = yearly_df.replace(to_replace=r'(?i)^nan$', value="", regex=True)
        
    if not monthly_df.empty:
        monthly_df = monthly_df.fillna("")
        monthly_df = monthly_df.replace(to_replace=r'(?i)^nan$', value="", regex=True)

    return yearly_df, monthly_df, year_to_month_cols, yearly_raw_export, monthly_raw_export

# Global variables for lazy loading - initialized to empty DataFrames
BAR_DF_YEARLY = pd.DataFrame()
BAR_LONG_YEARLY = pd.DataFrame()
YEAR_PRODUCTION_DATA_VALUE = {}
BAR_DF_MONTHLY = pd.DataFrame()
BAR_LONG_MONTHLY = pd.DataFrame()
MAP_YEARLY_LONG = pd.DataFrame()
MAP_MONTHLY_LONG = pd.DataFrame()
TABLE_DF_YEARLY = pd.DataFrame()
TABLE_DF_MONTHLY = pd.DataFrame()
TABLE_RAW_YEARLY = pd.DataFrame()
TABLE_RAW_MONTHLY = pd.DataFrame()
YEAR_TO_MONTH_COLS = {}
YEARLY_GRADES_DF = pd.DataFrame()
MONTHLY_GRADES_DF = pd.DataFrame()
YEARLY_GRADES_CACHE = {}
MONTHLY_GRADES_CACHE = {}

def _ensure_data_loaded():
    """Lazy load all data - only called when page is active"""
    global BAR_DF_YEARLY, BAR_LONG_YEARLY, YEAR_PRODUCTION_DATA_VALUE
    global BAR_DF_MONTHLY, BAR_LONG_MONTHLY
    global MAP_YEARLY_LONG, MAP_MONTHLY_LONG
    global TABLE_DF_YEARLY, TABLE_DF_MONTHLY, YEAR_TO_MONTH_COLS
    global TABLE_RAW_YEARLY, TABLE_RAW_MONTHLY
    global YEARLY_GRADES_DF, MONTHLY_GRADES_DF
    global COUNTRIES, STREAMS, YEARS_YEARLY, YEARS_MONTHLY, YEARS
    global CI_OPTIONS, API_OPTIONS, SULFUR_OPTIONS
    global PRODUCTION_YEARS, PRODUCTION_YEAR_DEFAULT
    global YEARLY_STREAM_COLOR_ORDER, MONTHLY_STREAM_COLOR_ORDER
    global STREAM_COLOR_ORDERS, STREAM_COLOR_MAPS, STREAM_ORDERS
    
    # Check if data is already loaded (not empty)
    if BAR_DF_YEARLY.empty or TABLE_DF_YEARLY.empty:
        BAR_DF_YEARLY, BAR_LONG_YEARLY, YEAR_PRODUCTION_DATA_VALUE = load_yearly_bar()
        BAR_DF_MONTHLY, BAR_LONG_MONTHLY = load_monthly_bar()
        MAP_YEARLY_LONG, MAP_MONTHLY_LONG = load_map_data()
        TABLE_DF_YEARLY, TABLE_DF_MONTHLY, YEAR_TO_MONTH_COLS, TABLE_RAW_YEARLY, TABLE_RAW_MONTHLY = load_table()
        YEARLY_GRADES_DF, MONTHLY_GRADES_DF = load_grades_data()
        
        # Initialize derived variables
        if not BAR_DF_YEARLY.empty and "Country" in BAR_DF_YEARLY.columns:
            COUNTRIES = sorted(BAR_DF_YEARLY["Country"].dropna().unique().tolist())
        elif not BAR_DF_MONTHLY.empty and "Country" in BAR_DF_MONTHLY.columns:
            COUNTRIES = sorted(BAR_DF_MONTHLY["Country"].dropna().unique().tolist())
        else:
            COUNTRIES = []
        STREAMS = sorted(BAR_DF_MONTHLY["Stream"].dropna().unique().tolist()) if not BAR_DF_MONTHLY.empty and "Stream" in BAR_DF_MONTHLY.columns else []
        YEARS_YEARLY = sorted(BAR_LONG_YEARLY["year"].dropna().unique().tolist()) if not BAR_LONG_YEARLY.empty and "year" in BAR_LONG_YEARLY.columns else []
        YEARS_MONTHLY = sorted(BAR_LONG_MONTHLY["year"].dropna().unique().tolist()) if not BAR_LONG_MONTHLY.empty and "year" in BAR_LONG_MONTHLY.columns else []
        YEARS = sorted(list(set(YEARS_YEARLY + YEARS_MONTHLY))) if YEARS_YEARLY or YEARS_MONTHLY else []
        
        CI_OPTIONS = _collect_filter_values("CI Rank")
        API_OPTIONS = _collect_filter_values("API")
        SULFUR_OPTIONS = _collect_filter_values("Sulfur")
        
        PRODUCTION_YEARS = sorted([int(y) for y in YEAR_TO_MONTH_COLS.keys() if y.isdigit()], reverse=True) if YEAR_TO_MONTH_COLS else []
        # Default to the two most recent years available (e.g., 2024, 2025)
        PRODUCTION_YEAR_DEFAULT = PRODUCTION_YEARS[:2] if len(PRODUCTION_YEARS) >= 2 else PRODUCTION_YEARS[:] if PRODUCTION_YEARS else []
        
        YEARLY_STREAM_COLOR_ORDER, MONTHLY_STREAM_COLOR_ORDER = load_stream_color_order()
        STREAM_COLOR_ORDERS = {
            "yearly": YEARLY_STREAM_COLOR_ORDER,
            "monthly": MONTHLY_STREAM_COLOR_ORDER
        }
        STREAM_COLOR_MAPS = {mode: {name: color for name, color in order} for mode, order in STREAM_COLOR_ORDERS.items()}
        STREAM_ORDERS = {mode: [name for name, _ in order] for mode, order in STREAM_COLOR_ORDERS.items()}
    else:
        # Colors may not be initialized if data loaded before code change
        _ensure_color_maps()

def _collect_filter_values(column_name):
    values = set()
    for df in [TABLE_DF_YEARLY, TABLE_DF_MONTHLY]:
        if not df.empty and column_name in df.columns:
            series = (
                df[column_name]
                .dropna()
                .astype(str)
                .str.strip()
            )
            values.update(v for v in series if v and v.lower() != "nan")
    return sorted(values)

# Initialize to empty - will be populated when data loads
CI_OPTIONS = []
API_OPTIONS = []
SULFUR_OPTIONS = []

CI_FILTER_CHOICES = ["-", "High", "Low", "Medium", "Very High", "Very Low"]
API_FILTER_CHOICES = ["-", "Heavy", "Light", "Medium"]
SULFUR_FILTER_CHOICES = ["-", "Sour", "Sweet"]

def classify_api_value(value):
    if value is None:
        return "-"
    value_str = str(value).strip()
    if value_str in ("", "-", "nan", "None"):
        return "-"
    try:
        api_value = float(value_str)
    except ValueError:
        return "-"
    
    if api_value == 0:
        return "-"
    if api_value > 31.1:
        return "Light"
    if api_value > 22.3:
        return "Medium"
    # Grouping <10 (Extra Heavy) into Heavy as per latest user request
    return "Heavy"

def classify_sulfur_value(value):
    if value is None:
        return "-"
    value_str = str(value).strip()
    if value_str in ("", "-", "nan", "None"):
        return "-"
    try:
        sulfur_value = float(value_str)
    except ValueError:
        return "-"
    
    # User rule: < 0.5% = Sweet, > 0.5% = Sour. Using >= for Sour boundary.
    return "Sour" if sulfur_value >= 0.5 else "Sweet"

# Initialize to empty - will be populated when data loads
COUNTRIES = []
STREAMS = []
YEARS_YEARLY = []
YEARS_MONTHLY = []
YEARS = []

# Generate year-month options (static, doesn't depend on data)
YEAR_MONTHS = []
for year in range(2000, 2026):
    for month in range(1, 13):
        month_str = f"{month:02d}"
        YEAR_MONTHS.append({"label": f"{year}-{month_str}", "value": f"{year}-{month_str}"})
YEAR_MONTHS.reverse()

PRODUCTION_YEARS = []
PRODUCTION_YEAR_DEFAULT = []

# Stream color/ordering - initialized to empty, loaded when data loads
YEARLY_STREAM_COLOR_ORDER = []
MONTHLY_STREAM_COLOR_ORDER = []
STREAM_COLOR_ORDERS = {}
STREAM_COLOR_MAPS = {}
STREAM_ORDERS = {}
FALLBACK_COLORS = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
    '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5'
]
TABLE_LINK_COLUMNS = ["Crude", "CrudeOil"]
TABLE_LINK_STYLE = [
    {"if": {"column_id": col}, "color": "#000000", "textDecoration": "none"}
    for col in TABLE_LINK_COLUMNS
]

# ================================
# TABLE TEXT COLOR & ALIGN FIXES
# ================================

# ================================
# TABLE STYLE – EXACT FIG MATCH
# ================================

# ================================
# TABLE LINK UNDERLINE REMOVAL
# ================================
TABLE_LINK_CSS = [
    {
        "selector": "#crude-table .dash-cell-value, #crude-table .dash-cell-value a",
        "rule": "color: #1f3b6f !important; text-decoration: none !important;"
    },
    {
        "selector": "#crude-table .dash-cell-value a:hover",
        "rule": "color: #1f3b6f !important; text-decoration: none !important;"
    },
    {
        "selector": "#crude-table th",
        "rule": "color: #1f3b6f !important; font-weight: bold;"
    },
    {
        "selector": "#crude-table .dash-cell, #crude-table .dash-row",
        "rule": "cursor: pointer;"
    }
]





def get_stream_order(tab="yearly"):
    # Ensure colors/orders are initialized
    _ensure_color_maps()
    if not STREAM_ORDERS:
        return []
    return STREAM_ORDERS.get(tab) or STREAM_ORDERS.get("yearly", [])


def get_stream_color_map(tab="yearly"):
    # Ensure colors/orders are initialized
    _ensure_color_maps()
    if not STREAM_COLOR_MAPS:
        # Return comprehensive monthly colors if available
        if tab == "monthly":
            return MONTHLY_CRUDE_COLORS.copy()
        return {}
    color_map = STREAM_COLOR_MAPS.get(tab) or STREAM_COLOR_MAPS.get("yearly", {})
    # For monthly, ensure comprehensive colors are included
    if tab == "monthly":
        color_map = {**color_map, **MONTHLY_CRUDE_COLORS}
    return color_map


def get_color_sequence(tab="yearly"):
    # Ensure colors/orders are initialized
    _ensure_color_maps()
    base_pairs = STREAM_COLOR_ORDERS.get(tab) or STREAM_COLOR_ORDERS.get("yearly") or []
    base = [color for _, color in base_pairs]
    return base + [c for c in FALLBACK_COLORS if c not in base]


def order_streams_list(streams, tab="yearly"):
    """Order streams to match required Tableau order, then append any unknowns"""
    if not streams:
        return []
    seen = set()
    ordered = []
    for name in get_stream_order(tab):
        if name in streams and name not in seen:
            ordered.append(name)
            seen.add(name)
    for stream in streams:
        if stream not in seen:
            ordered.append(stream)
            seen.add(stream)
    return ordered


def create_layout(server=None):
    """Create the Crude Overview layout matching Tableau dashboard"""
    default_country_value = ["Russia"] if "Russia" in COUNTRIES else ([COUNTRIES[0]] if COUNTRIES else None)
    return html.Div([
        # Store to hold profile URLs for streams
        dcc.Store(id="stream-profile-urls-store", data={}),
        # Store to track last clicked stream (to prevent duplicate navigation)
        dcc.Store(id="last-clicked-stream-store", data=None),
        # Store to track map country selection
        dcc.Store(id="selected-country-map-store", data=None),
        # Dummy store for navigation callback output
        dcc.Store(id="stream-navigation-dummy", data=None),
        # Custom CSS to style markdown links in DataTable to look like normal text
        html.Div(
            dcc.Markdown(
                """
                <style>
                    #crude-table .dash-cell-value a,
                    #crude-table .dash-cell-value a:link,
                    #crude-table .dash-cell-value a:visited,
                    #crude-table .dash-cell-value a:hover,
                    #crude-table .dash-cell-value a:active {
                        color: #000000 !important;
                        text-decoration: none !important;
                    }
                </style>
                """,
                dangerously_allow_html=True
            ),
            style={"display": "none"}
        ),
        # Text above tabs
        html.P(
            "Click on a country for a breakdown of production by crude stream. *Profiled countries only.", 
            style={"textAlign":"left", "fontSize":"14px", "color":"#666", "marginBottom":"10px"}
        ),
        # Top tabs: Yearly / Monthly
        dcc.Tabs(
            id="crude-main-tabs", 
            value="monthly", 
            children=[
                dcc.Tab(
                    label="Yearly", 
                    value="yearly", 
                    style={
                        "backgroundColor": "#f8f9fa", 
                        "border": "2px solid #d35400", 
                        "padding": "10px 20px", 
                        "fontWeight": "bold", 
                        "color": "#d35400"
                    },
                    selected_style={
                        "backgroundColor": "#d35400", 
                        "color": "white", 
                        "border": "2px solid #d35400",
                        "padding": "10px 20px", 
                        "fontWeight": "bold"
                    }
                ),
                dcc.Tab(
                    label="Monthly", 
                    value="monthly",
                    style={
                        "backgroundColor": "#f8f9fa", 
                        "border": "2px solid #d35400", 
                        "padding": "10px 20px",
                        "fontWeight": "bold", 
                        "color": "#d35400"
                    },
                    selected_style={
                        "backgroundColor": "#d35400", 
                        "color": "white", 
                        "border": "2px solid #d35400",
                        "padding": "10px 20px", 
                        "fontWeight": "bold"
                    }
                ),
            ], 
            persistence=True, 
            persistence_type="session", 
            style={"marginBottom": "20px", "display": "flex", "justifyContent": "center"}
        ),
        html.Br(),
        html.Div([
            html.H4(
                "World Crude Production*", 
                style={"color":"#d35400", "textAlign":"center", "marginTop":"10px", "marginBottom": "0px", "flexGrow": 1}
            ),
            html.Div([
                html.Button(
                    'Export Data to CSV',
                    id='btn-export-map-csv',
                    n_clicks=0,
                    style={
                        'backgroundColor': 'white',
                        'color': '#2c3e50',
                        'border': '1px solid #dee2e6',
                        'padding': '4px 10px',
                        'borderRadius': '4px',
                        'cursor': 'pointer',
                        'fontSize': '12px',
                        'margin': '0',
                        'display': 'inline-block'
                    }
                ),
            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'flex-end', 'position': 'absolute', 'right': '15px', 'top': '10px'})
        ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'position': 'relative', 'width': '100%'}),
        dcc.Download(id="download-map-csv"),
        html.Hr(),

        html.Div([
            html.Div([
                dcc.Loading(
                    id="loading-map",
                    type="dot",
                    color="#d35400",
                    children=[
                        dcc.Graph(
                            id="crude-map", 
                            config={
                                "displayModeBar": False,
                                "scrollZoom": True,  # Allow scroll zoom
                                "doubleClick": "reset",  # Double-click to reset zoom
                                "modeBarButtonsToRemove": ["pan2d", "lasso2d"]  # Remove some controls
                            }, 
                            style={"height":"500px", "width":"100%"},
                            figure=go.Figure()  # Initialize with empty figure
                        )
                    ],
                    style={"height":"500px", "width":"100%"}
                )
            ], className='col-md-10', style={'padding': '10px'}),
            html.Div([
                # Year dropdown (shown when yearly tab is selected)
                html.Div(
                    id="year-controls", 
                    children=[
                        html.Label("Year", style={"fontWeight":"bold", "color":"#2c3e50", "fontSize":"13px", "marginBottom":"5px"}),
                        dcc.Dropdown(
                            id="crude-year-dropdown", 
                            options=[{"label":str(y),"value":y} for y in range(2000, 2026)],
                            value=2024,  # Default to 2024 for yearly filter
                            style={"marginBottom":"10px", "fontSize":"12px"}
                        )
                    ]
                ),
                # Year Month dropdown (shown when monthly tab is selected) - for map filter
                html.Div(
                    id="year-month-controls", 
                    style={"display":"none"}, 
                    children=[
                        html.Label("Year Month", style={"fontWeight":"bold", "color":"#2c3e50", "fontSize":"13px", "marginBottom":"5px"}),
                        dcc.Dropdown(
                            id="crude-year-month-dropdown",
                            options=YEAR_MONTHS,
                            value="2025-07",  # Default to 2025-07 for monthly filter
                            style={"marginBottom":"10px", "fontSize":"12px"}
                        )
                    ]
                ),
                html.Label("Country", style={"fontWeight":"bold", "color":"#2c3e50", "fontSize":"13px", "marginBottom":"5px"}),
                dcc.Checklist(
                    id="crude-country-dropdown",
                    options=([{"label": "(All)", "value": "(All)"}] + [{"label": c, "value": c} for c in COUNTRIES]),
                    value=["Russia"],
                    inputStyle={"marginRight": "8px"},
                    labelStyle={"display": "block", "marginBottom": "6px"},
                    style={
                        "maxHeight": "280px",
                        "overflowY": "auto",
                        "padding": "8px",
                        "border": "1px solid #e0e0e0",
                        "borderRadius": "6px",
                        "background": "white",
                        "fontSize": "12px"
                    },
                    persistence=True,
                    persistence_type="session",
                )
            ], className='col-md-2', style={'padding': '10px', 'paddingTop': '20px'})
        ], className='row'),
        html.Br(),
        html.Div([
            html.Div([
                html.H4(
                    id="production-breakdown-title",
                    children="",
                    style={"color": "#d35400", "textAlign": "center", "marginTop": "10px", "marginBottom": "0px", "flexGrow": 1}
                ),
                html.Div([
                    html.Button(
                        'Export Data to CSV',
                        id='btn-export-chart-csv',
                        n_clicks=0,
                        style={
                            'backgroundColor': 'white',
                            'color': '#2c3e50',
                            'border': '1px solid #dee2e6',
                            'padding': '4px 10px',
                            'borderRadius': '4px',
                            'cursor': 'pointer',
                            'fontSize': '12px',
                            'margin': '0',
                            'display': 'inline-block'
                        }
                    ),
                ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'flex-end', 'position': 'absolute', 'right': '15px', 'top': '10px'})
            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'position': 'relative', 'width': '100%', 'marginBottom': '10px'}),
            dcc.Download(id="download-chart-csv"),

            html.Div(
                dcc.Loading(
                    id="loading-chart",
                    type="dot",
                    color="#d35400",
                    children=[
                        dcc.Graph(
                            id="production-breakdown-chart", 
                            style={"height":"520px"},
                            figure=go.Figure(),  # Initialize with empty figure
                            config={
                                'displayModeBar': True,
                                'displaylogo': False,
                                'modeBarButtons': [['toImage', 'resetViews']] 
                            }
                        )
                    ],
                    style={"height":"520px"}
                ), 
                className='col-md-10',
                style={'padding': '15px'}
            ),
            html.Div([
                # Year of Date filter (only for monthly view, for 
                # chart)
                html.Div(
                    id="production-year-filter",
                    style={"display": "none"},
                    children=[
                        html.Label("Year of Date", style={"fontWeight": "bold", "color": "#2c3e50", "fontSize": "13px", "marginBottom": "5px"}),
                        dcc.Checklist(
                            id="production-year-dropdown",
                            options=([{"label": "(All)", "value": "(All)"}] + [{"label": str(y), "value": y} for y in sorted(PRODUCTION_YEARS) if PRODUCTION_YEARS]
                                     if PRODUCTION_YEARS else [{"label": "(All)", "value": "(All)"}] + [{"label": str(y), "value": y} for y in range(2000, 2026)]),
                            value=PRODUCTION_YEAR_DEFAULT if PRODUCTION_YEAR_DEFAULT else [],
                            inputStyle={"marginRight": "8px"},
                            labelStyle={"display": "block", "marginBottom": "6px"},
                            style={
                                "maxHeight": "280px",
                                "overflowY": "auto",
                                "padding": "8px",
                                "border": "1px solid #e0e0e0",
                                "borderRadius": "6px",
                                "background": "white",
                                "fontSize": "12px",
                                "marginBottom": "15px"
                            },
                            persistence=True,
                            persistence_type="session",
                        )
                    ]
                ),
                html.Div([
                    html.H6("Profiled Crude Oils", style={"marginBottom": "8px", "fontWeight": "bold", "color": "#2c3e50"}),
                    # Hidden checklist to store values
                    dcc.Checklist(
                        id="profiled-streams", 
                        options=[], 
                        value=[],
                        style={"display": "none"}
                    ),
                    html.Div(id="profiled-streams-container", children=[])
                ], style={
                    "padding": "15px",
                    "border": "1px solid #ddd",
                    "borderRadius": "4px",
                    "backgroundColor": "#f9f9f9",
                    "maxHeight": "400px",
                    "overflowY": "auto"
                })
            ], className='col-md-2', style={'padding': '15px'})
        ], className='row'),
        html.Br(),
        html.Div([
            html.H4(
                id="table-title",
                children="Global Crude Production Breakdown",
                style={"color":"#d35400","textAlign":"center", "marginTop":"10px", "marginBottom": "0px", "flexGrow": 1}
            ),
            html.Div([
                html.Button(
                    'Export Data to CSV',
                    id='btn-export-table-csv',
                    n_clicks=0,
                    style={
                        'backgroundColor': 'white',
                        'color': '#2c3e50',
                        'border': '1px solid #dee2e6',
                        'padding': '4px 10px',
                        'borderRadius': '4px',
                        'cursor': 'pointer',
                        'fontSize': '12px',
                        'margin': '0',
                        'display': 'inline-block'
                    }
                ),
            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'flex-end', 'position': 'absolute', 'right': '15px', 'top': '10px'})
        ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'position': 'relative', 'width': '100%'}),
        dcc.Download(id="download-table-csv"),
        html.Div([
            html.Div([
                dcc.Loading(
                    id="loading-table",
                    type="dot",
                    color="#d35400",
                    children=[
                        dash_table.DataTable(
                            id="crude-table",
                            columns=[
                                {"name": str(c), "id": str(c), "type": "numeric"}
                                if c != "CrudeOil" else
                                {"name": "CrudeOil", "id": "CrudeOil", "type": "text"}
                                for c in TABLE_DF_YEARLY.columns.tolist()
                            ] if not TABLE_DF_YEARLY.empty else [],
                            data=TABLE_DF_YEARLY.to_dict("records") if not TABLE_DF_YEARLY.empty else [],
                            page_action='none',
                            fixed_rows={'headers': True},  # Freeze headers
                            markdown_options={"link_target": "_blank"},
                            style_table={
                                "overflowX": "auto", 
                                "overflowY": "auto", 
                                "minHeight": "400px",
                                "maxHeight": "600px",
                                "height": "auto"
                            },
                            
    
                            
                            style_cell={
                                "fontSize": "13px",
                                "fontFamily": "Arial",
                                "whiteSpace": "normal",
                                "color": "#1f3b6f",
                                "minWidth": "90px",
                                "textAlign": "right",
                                "padding": "5px"  # Reduced padding for thinner rows
                            },

                            # Removed style_cell_conditional to keep all columns right-aligned
                            


                            style_header={
                                "textAlign": "center",
                                "fontWeight": "bold",
                                "backgroundColor": "white",
                                "color": "#1f3b6f"
                            },


                            style_header_conditional=[
                                # Keep year headers (top level) centered
                                {
                                    "if": {"header_index": 0},
                                    "textAlign": "center"
                                },
                                # Left align month headers (second level) for monthly view
                                {
                                    "if": {"header_index": 1},
                                    "textAlign": "right"
                                }
                            ],
                            style_data_conditional=[
                                # Alternating row colors (white and grey)
                                {
                                    "if": {"row_index": "odd"},
                                      "backgroundColor": "#f5f5f5" ,
                                      "textAlign": "right" # Light grey for odd rows
                                  },
                                {
                                    "if": {"row_index": "even"},
                                      "backgroundColor": "white",  # White for even rows
                                      "textAlign": "right"
                                  },
                                # Left-align first column (Crude name)
                                {
                                    "if": {"column_id": "CrudeOil"},
                                    "textAlign": "left"
                                },

                                # Remove conflicting text alignment rules

                                # Keep link styling
                                *TABLE_LINK_STYLE
                            ],
                            css=[
                                {"selector": "p", "rule": "text-align: right; margin: 0; padding: 0;"},
                                {"selector": ".dash-cell.column-0 p, .dash-cell.column-0", "rule": "text-align: left !important;"}
                            ] + TABLE_LINK_CSS,
                            merge_duplicate_headers=True
                        )
                    ],
                    style={"minHeight": "400px"}
                )
            ], className='col-md-10', style={'padding': '15px', 'minHeight': '400px'}),
            html.Div([
                html.Label("Stream Name"),
                dcc.Input(id="filter-stream", type="text", placeholder="Stream Name"),
                html.Br(), html.Br(),
                html.Div([
                    html.Label("CI Rank", style={"fontWeight":"bold", "color":"#2c3e50", "fontSize":"13px", "marginBottom":"5px"}),
                    dcc.Checklist(
                        id="filter-ci", 
                        options=[{"label": "ALL", "value": "ALL"}] + [{"label": v, "value": v} for v in CI_FILTER_CHOICES],
                        value=["ALL"] + CI_FILTER_CHOICES,
                        inputStyle={"marginRight": "8px"},
                        labelStyle={"display": "block", "marginBottom": "6px"},
                        style={
                            "maxHeight": "150px", "overflowY": "auto", "padding": "8px",
                            "border": "1px solid #e0e0e0", "borderRadius": "6px",
                            "background": "white", "fontSize": "12px"
                        }
                    ),
                    html.Br(),
                    html.Label("API", style={"fontWeight":"bold", "color":"#2c3e50", "fontSize":"13px", "marginBottom":"5px"}),
                    dcc.Checklist(
                        id="filter-api", 
                        options=[{"label": "ALL", "value": "ALL"}] + [{"label": v, "value": v} for v in API_FILTER_CHOICES],
                        value=["ALL"] + API_FILTER_CHOICES,
                        inputStyle={"marginRight": "8px"},
                        labelStyle={"display": "block", "marginBottom": "6px"},
                        style={
                            "maxHeight": "150px", "overflowY": "auto", "padding": "8px",
                            "border": "1px solid #e0e0e0", "borderRadius": "6px",
                            "background": "white", "fontSize": "12px"
                        }
                    ),
                    html.Br(),
                    html.Label("Sulfur", style={"fontWeight":"bold", "color":"#2c3e50", "fontSize":"13px", "marginBottom":"5px"}),
                    dcc.Checklist(
                        id="filter-sulfur", 
                        options=[{"label": "ALL", "value": "ALL"}] + [{"label": v, "value": v} for v in SULFUR_FILTER_CHOICES],
                        value=["ALL"] + SULFUR_FILTER_CHOICES,
                        inputStyle={"marginRight": "8px"},
                        labelStyle={"display": "block", "marginBottom": "6px"},
                        style={
                            "maxHeight": "150px", "overflowY": "auto", "padding": "8px",
                            "border": "1px solid #e0e0e0", "borderRadius": "6px",
                            "background": "white", "fontSize": "12px"
                        }
                    ),
                ], id="monthly-only-filters-container", style={"display": "none"})
            ], className='col-md-2', style={'padding': '15px'})

        ], className='row')
    ], style={'padding': '20px', 'background': '#f8f9fa'})


def register_callbacks(dash_app, server):
    """Register all callbacks for Crude Overview"""
    
    @dash_app.callback(
        Output("monthly-only-filters-container", "style"),
        [Input("crude-main-tabs", "value")]
    )
    def toggle_monthly_filters(tab):
        """Show/hide filters only for monthly tab"""
        if tab == "monthly":
            return {"display": "block"}
        return {"display": "none"}

    @dash_app.callback(
        Output("filter-stream", "value"),
        [Input("crude-main-tabs", "value")],
        prevent_initial_call=True
    )
    def reset_crude_table_search(tab):
        """Reset search filter when changing tabs to isolate search results"""
        return ""

    @dash_app.callback(
        [Output("crude-country-dropdown", "options"),

         Output("crude-country-dropdown", "value", allow_duplicate=True)],
        Input("current-submenu", "data"),
        # Using initial_duplicate to allow initial population alongside other callbacks on the same output
        prevent_initial_call="initial_duplicate"
    )
    def populate_countries(current_submenu):
        """Populate country dropdown options once data is loaded."""
        if current_submenu != 'crude-overview':
            return no_update, no_update
        
        _ensure_data_loaded()
        countries = []
        if not BAR_DF_YEARLY.empty and "Country" in BAR_DF_YEARLY.columns:
            countries = sorted(BAR_DF_YEARLY["Country"].dropna().unique().tolist())
        elif not BAR_DF_MONTHLY.empty and "Country" in BAR_DF_MONTHLY.columns:
            countries = sorted(BAR_DF_MONTHLY["Country"].dropna().unique().tolist())
        
        options = [{"label": "(All)", "value": "(All)"}] + [{"label": c, "value": c} for c in countries]
        default_value = ["Russia"] if "Russia" in countries else (["(All)"] if countries else [])
        return options, default_value

    @dash_app.callback(
        Output("crude-country-dropdown", "value", allow_duplicate=True),
        Input("crude-country-dropdown", "value"),
        State("crude-country-dropdown", "options"),
        prevent_initial_call=True,
    )
    def sync_country_all(selected, options):
        """Ensure '(All)' behaves as select-all for country checklist."""
        if not options:
            return no_update
        all_countries = [o["value"] for o in options if o["value"] != "(All)"]
        selected = selected or []
        selected_set = set(selected)
        has_all = "(All)" in selected_set
        all_set = set(all_countries)
        subset_set = selected_set - {"(All)"}

        if has_all and not subset_set:
            normalized = ["(All)"] + all_countries
        elif has_all and subset_set:
            if len(all_set) > 0 and len(subset_set) >= len(all_set) - 1:
                normalized = sorted(subset_set)  # user is deselecting while All was active
            else:
                normalized = ["(All)"] + all_countries  # user added All from a partial subset
        elif not has_all and subset_set == all_set and all_countries:
            normalized = []  # allow explicit unselect-all after All was selected
        elif not subset_set:
            normalized = []
        else:
            normalized = sorted(subset_set)

        new_sorted = normalized
        old_sorted = sorted(selected)
        return new_sorted if new_sorted != old_sorted else no_update
    
    @dash_app.callback(
        Output("crude-country-dropdown", "value", allow_duplicate=True),
        Input("crude-map", "clickData"),
        prevent_initial_call=True
    )
    def update_country_from_map(clickData):
        """Update country dropdown when map is clicked"""
        if clickData and clickData.get("points"):
            clicked_country = clickData["points"][0].get("location")
            if clicked_country:
                return [clicked_country]
        return no_update
    
    @dash_app.callback(
        [Output("production-year-dropdown", "options"),
         Output("production-year-dropdown", "value", allow_duplicate=True)],
        Input("current-submenu", "data"),
        prevent_initial_call="initial_duplicate"
    )
    def populate_production_years(current_submenu):
        """Populate production year dropdown options once data is loaded."""
        if current_submenu != 'crude-overview':
            return no_update, no_update
        
        _ensure_data_loaded()
        years = PRODUCTION_YEARS if PRODUCTION_YEARS else []
        
        # Sort years in ascending order for display (PRODUCTION_YEARS is in descending order)
        years_ascending = sorted(years) if years else []
        
        options = [{"label": "(All)", "value": "(All)"}] + [{"label": str(y), "value": y} for y in years_ascending]
        # Default to the two most recent years (e.g., 2024, 2025)
        # Use integer values to match the option values
        default_value = PRODUCTION_YEAR_DEFAULT if PRODUCTION_YEAR_DEFAULT else []
        return options, default_value
    
    @dash_app.callback(
        Output("production-year-dropdown", "value", allow_duplicate=True),
        Input("production-year-dropdown", "value"),
        State("production-year-dropdown", "options"),
        prevent_initial_call=True,
    )
    def sync_years_all(selected, options):
        """Ensure '(All)' behaves as select-all for year checklist."""
        if not options:
            return no_update
        all_years = [o["value"] for o in options if o["value"] != "(All)"]
        selected = selected or []
        selected_set = set(selected)
        has_all = "(All)" in selected_set
        all_set = set(all_years)
        subset_set = selected_set - {"(All)"}

        if has_all and not subset_set:
            normalized = ["(All)"] + all_years
        elif has_all and subset_set:
            if len(all_set) > 0 and len(subset_set) >= len(all_set) - 1:
                # Sort years (integers) in descending order
                normalized = sorted(subset_set, key=lambda x: x if isinstance(x, int) else int(x) if str(x).isdigit() else 0, reverse=True)
            else:
                normalized = ["(All)"] + all_years  # user added All from a partial subset
        elif not has_all and subset_set == all_set and all_years:
            normalized = []  # allow explicit unselect-all after All was selected
        elif not subset_set:
            normalized = []
        else:
            # Sort years (integers) in descending order
            normalized = sorted(subset_set, key=lambda x: x if isinstance(x, int) else int(x) if str(x).isdigit() else 0, reverse=True)

        new_sorted = normalized
        old_sorted = sorted(selected, key=lambda x: x if isinstance(x, int) else int(x) if str(x).isdigit() else 0, reverse=True)
        return new_sorted if new_sorted != old_sorted else no_update

    def _sync_categorical_checklist(selected, options, all_values):
        """Helper to sync 'ALL' toggle for categorical checklists."""
        if not options:
            return no_update
        
        selected = selected or []
        selected_set = set(selected)
        has_all = "ALL" in selected_set
        others_set = selected_set - {"ALL"}
        all_categories_set = set(all_values)
        
        if has_all and not others_set:
            # Only ALL selected -> select everything
            normalized = ["ALL"] + all_values
        elif has_all and others_set:
            # ALL and some others -> if user unchecked one from a full set, uncheck ALL
            if len(others_set) < len(all_categories_set):
                normalized = sorted(list(others_set))
            else:
                normalized = ["ALL"] + all_values
        elif not has_all and others_set == all_categories_set:
            # Everything except ALL is checked -> check ALL too
            normalized = ["ALL"] + all_values
        elif not has_all and not others_set:
            # Nothing selected
            normalized = []
        else:
            # Just some categories
            normalized = sorted(list(others_set))
            
        return normalized if normalized != selected else no_update

    @dash_app.callback(
        Output("filter-ci", "value"),
        Input("filter-ci", "value"),
        State("filter-ci", "options"),
        prevent_initial_call=True
    )
    def sync_ci_all(selected, options):
        return _sync_categorical_checklist(selected, options, CI_FILTER_CHOICES)

    @dash_app.callback(
        Output("filter-api", "value"),
        Input("filter-api", "value"),
        State("filter-api", "options"),
        prevent_initial_call=True
    )
    def sync_api_all(selected, options):
        return _sync_categorical_checklist(selected, options, API_FILTER_CHOICES)

    @dash_app.callback(
        Output("filter-sulfur", "value"),
        Input("filter-sulfur", "value"),
        State("filter-sulfur", "options"),
        prevent_initial_call=True
    )
    def sync_sulfur_all(selected, options):
        return _sync_categorical_checklist(selected, options, SULFUR_FILTER_CHOICES)
    
    @dash_app.callback(
        [Output("profiled-streams", "options"),
         Output("profiled-streams", "value")],
        [Input("crude-country-dropdown", "value"),
         Input("crude-main-tabs", "value"),
         Input("crude-year-dropdown", "value"),
         Input("crude-year-month-dropdown", "value"),
         Input("current-submenu", "data")],
        prevent_initial_call=False
    )
    def update_profiled_streams_options(country, tab, year, year_month, current_submenu):
        """Update profiled streams options based on selected country and tab using grades CSV files"""
        # Only load data if page is active
        if current_submenu != 'crude-overview':
            return [], None
        
        # Ensure data is loaded
        _ensure_data_loaded()
        
        try:
            # Handle country - ensure it's a list
            resolved_countries = _resolve_countries_selection(country)
            # If no countries selected, return empty options
            if not resolved_countries:
                print(f"DEBUG update_profiled_streams_options: No countries selected, returning empty options")
                return [], []
            
            selected_country = resolved_countries[0] if resolved_countries else None
            
            print(f"DEBUG update_profiled_streams_options: country={country}, resolved_countries={resolved_countries}, tab={tab}")
            
            # Get streams from grades CSV based on tab
            available_streams = []
            stream_to_url = {}  # Map stream name to profile_url
            
            if tab == "yearly" or tab is None:
                # Fetch yearly grades dynamically from DB - pass all resolved countries
                country_df = get_yearly_grades_for_country(resolved_countries)
                if not country_df.empty and "Stream" in country_df.columns:
                    # Extract link if available (profile_url or BSP link)
                    # Check all possible column name variations
                    link_col = None
                    possible_cols = ["profile_url", "Profile URL", "Profile_URL", "profile-url", "Profile-URL", 
                                     "BSP link", "BSP Link", "BSP_link", "BSP_link", "bsp_link", "Bsp_link"]
                    for col in possible_cols:
                        if col in country_df.columns:
                            link_col = col
                            print(f"DEBUG: Found link column '{col}' in yearly data")
                            break
                    
                    # Also check case-insensitive
                    if not link_col:
                        for col in country_df.columns:
                            if col.lower().replace(" ", "_").replace("-", "_") in ["profile_url", "bsp_link"]:
                                link_col = col
                                print(f"DEBUG: Found link column '{col}' (case-insensitive match) in yearly data")
                                break
                    
                    if link_col:
                        print(f"DEBUG: Using link column '{link_col}' for yearly streams")
                        for _, row in country_df.iterrows():
                            stream = str(row["Stream"]).strip() if pd.notna(row["Stream"]) else None
                            url_val = row[link_col]
                            url = str(url_val).strip() if pd.notna(url_val) and str(url_val).strip() else None
                            if stream and url and url != "nan" and url != "None":
                                stream_to_url[stream] = url
                                print(f"DEBUG: Stored URL for stream '{stream}': {url}")
                    else:
                        print(f"DEBUG: No link column found in yearly data. Available columns: {list(country_df.columns)}")
                    
                    country_streams = country_df["Stream"].dropna().unique().tolist()
                    available_streams = order_streams_list(country_streams, tab="yearly")
                    print(f"DEBUG: Yearly streams for {resolved_countries}: {len(available_streams)} streams (from DB)")
            else:
                # Load monthly grades dynamically for all selected countries - pass all resolved countries
                country_df = get_monthly_grades_for_country(resolved_countries)
                if not country_df.empty and "Stream" in country_df.columns:
                    # Extract link if available (profile_url or BSP link)
                    # Check all possible column name variations
                    link_col = None
                    possible_cols = ["profile_url", "Profile URL", "Profile_URL", "profile-url", "Profile-URL", 
                                     "BSP link", "BSP Link", "BSP_link", "BSP_link", "bsp_link", "Bsp_link"]
                    for col in possible_cols:
                        if col in country_df.columns:
                            link_col = col
                            print(f"DEBUG: Found link column '{col}' in monthly data")
                            break
                    
                    # Also check case-insensitive
                    if not link_col:
                        for col in country_df.columns:
                            if col.lower().replace(" ", "_").replace("-", "_") in ["profile_url", "bsp_link"]:
                                link_col = col
                                print(f"DEBUG: Found link column '{col}' (case-insensitive match) in monthly data")
                                break
                    
                    if link_col:
                        print(f"DEBUG: Using link column '{link_col}' for monthly streams")
                        for _, row in country_df.iterrows():
                            stream = str(row["Stream"]).strip() if pd.notna(row["Stream"]) else None
                            url_val = row[link_col]
                            url = str(url_val).strip() if pd.notna(url_val) and str(url_val).strip() else None
                            if stream and url and url != "nan" and url != "None":
                                stream_to_url[stream] = url
                                print(f"DEBUG: Stored URL for stream '{stream}': {url}")
                    else:
                        print(f"DEBUG: No link column found in monthly data. Available columns: {list(country_df.columns)}")
                    
                    country_streams = country_df["Stream"].dropna().unique().tolist()
                    
                    # For monthly, use exact order from MONTHLY_STREAM_COLOR_ORDER
                    monthly_order = [name for name, _ in MONTHLY_STREAM_COLOR_ORDER]
                    seen = set()
                    ordered = []
                    # First, add streams in the exact order from MONTHLY_STREAM_COLOR_ORDER
                    for name in monthly_order:
                        if name in country_streams and name not in seen:
                            ordered.append(name)
                            seen.add(name)
                    # Then add any remaining streams not in the order list
                    for stream in country_streams:
                        if stream not in seen:
                            ordered.append(stream)
                            seen.add(stream)
                    available_streams = ordered
                    print(f"DEBUG: Monthly streams for {selected_country}: {len(available_streams)} streams (ordered by MONTHLY_STREAM_COLOR_ORDER)")
            
            # Fallback: enrich profile URLs from Production Breakdown tables if missing
            if tab == "yearly" or tab is None:
                link_col = next((col for col in ["profile_url", "BSP link"] if col in TABLE_DF_YEARLY.columns), None)
                if link_col and not TABLE_DF_YEARLY.empty:
                    table_url_map = (
                        TABLE_DF_YEARLY[["CrudeOil", link_col]]
                        .dropna(subset=["CrudeOil", link_col])
                        .drop_duplicates(subset=["CrudeOil"])
                        .set_index("CrudeOil")[link_col]
                        .to_dict()
                    )
                    for stream in available_streams:
                        if stream not in stream_to_url and stream in table_url_map:
                            stream_to_url[stream] = table_url_map[stream]
            else:
                link_col = next((col for col in ["profile_url", "BSP link"] if col in TABLE_DF_MONTHLY.columns), None)
                if link_col and not TABLE_DF_MONTHLY.empty:
                    table_url_map = (
                        TABLE_DF_MONTHLY[["Crude", link_col]]
                        .dropna(subset=["Crude", link_col])
                        .drop_duplicates(subset=["Crude"])
                        .set_index("Crude")[link_col]
                        .to_dict()
                    )
                    for stream in available_streams:
                        if stream not in stream_to_url and stream in table_url_map:
                            stream_to_url[stream] = table_url_map[stream]
    
            # If no streams from grades CSV, fall back to all streams from bar data
            if not available_streams:
                if tab == "yearly" or tab is None:
                    if not BAR_LONG_YEARLY.empty and "Stream" in BAR_LONG_YEARLY.columns:
                        country_data = BAR_LONG_YEARLY[BAR_LONG_YEARLY["Country"].isin(country)]
                        available_streams = order_streams_list(country_data["Stream"].dropna().unique().tolist(), tab="yearly")
                else:
                    if not BAR_LONG_MONTHLY.empty and "Stream" in BAR_LONG_MONTHLY.columns:
                        country_data = BAR_LONG_MONTHLY[BAR_LONG_MONTHLY["Country"].isin(country)]
                        # For monthly, use exact order from MONTHLY_STREAM_COLOR_ORDER
                        monthly_order = [name for name, _ in MONTHLY_STREAM_COLOR_ORDER]
                        country_streams_list = country_data["Stream"].dropna().unique().tolist()
                        seen = set()
                        ordered = []
                        for name in monthly_order:
                            if name in country_streams_list and name not in seen:
                                ordered.append(name)
                                seen.add(name)
                        for stream in country_streams_list:
                            if stream not in seen:
                                ordered.append(stream)
                                seen.add(stream)
                        available_streams = ordered
            
            # Create options with profile_url stored in the option dict
            options = []
            for s in available_streams:
                opt = {"label": s, "value": s}
                if s in stream_to_url:
                    opt["profile_url"] = stream_to_url[s]
                options.append(opt)
            
            # Default: select all streams (default mode - no filtering)
            default_value = available_streams[:]
            
            print(f"DEBUG: Returning {len(options)} options and {len(default_value)} default values (all selected by default)")
            return options, default_value
            
        except Exception as e:
            print(f"Error updating profiled streams options: {e}")
            import traceback
            traceback.print_exc()
            return [], []
    
    def get_stream_color(stream, all_streams_list, tab="yearly"):
        """Get consistent color for a stream based on its position in the full streams list"""
        all_streams_list = all_streams_list or []
        _ensure_color_maps()
        color_map = get_stream_color_map(tab)
        if stream in color_map:
            return color_map[stream]
        # For monthly streams, check comprehensive color mapping as fallback (case-insensitive)
        if tab == "monthly":
            if stream in MONTHLY_CRUDE_COLORS:
                return MONTHLY_CRUDE_COLORS[stream]
            # Try case-insensitive lookup
            stream_normalized = stream.strip()
            stream_lower = stream_normalized.lower()
            for key, value in MONTHLY_CRUDE_COLORS.items():
                if key.lower().strip() == stream_lower:
                    return value
        if stream in all_streams_list:
            idx = all_streams_list.index(stream)
            return FALLBACK_COLORS[idx % len(FALLBACK_COLORS)]
        return FALLBACK_COLORS[0]
    
    @dash_app.callback(
        [Output("profiled-streams-container", "children"),
         Output("stream-profile-urls-store", "data")],
        [Input("profiled-streams", "value"),
         Input("profiled-streams", "options"),
         Input("production-breakdown-chart", "figure"),
         Input("crude-main-tabs", "value")],
        prevent_initial_call=False
    )
    def update_profiled_streams_with_colors(selected_streams, stream_options, chart_figure, active_tab):
        """Create clickable stream buttons with highlight/dimmed selection - no checkboxes"""
        _ensure_color_maps()
        if not stream_options:
            return html.Div("No streams available")
        
        selected_streams = selected_streams if selected_streams else []
        
        # Get all available streams from options
        all_available_streams = [opt["value"] for opt in stream_options] if stream_options else []
        print(f"DEBUG COLOR: update_profiled_streams_with_colors called with tab='{active_tab}', {len(all_available_streams)} streams")
        if active_tab == "monthly" and len(all_available_streams) > 0:
            print(f"DEBUG COLOR: First 10 monthly streams: {all_available_streams[:10]}")
        
        # Get colors from chart if available
        color_map = {}
        streams_in_chart = []
        
        if chart_figure and 'data' in chart_figure:
            for trace in chart_figure.get('data', []):
                stream_name = trace.get('name') or trace.get('legendgroup', '')
                if stream_name:
                    streams_in_chart.append(stream_name)
                    marker = trace.get('marker', {})
                    if isinstance(marker, dict):
                        color = marker.get('color')
                        if color:
                            if isinstance(color, list) and len(color) > 0:
                                color_map[stream_name] = color[0] if isinstance(color[0], str) else str(color[0])
                            elif isinstance(color, str):
                                color_map[stream_name] = color
                            elif hasattr(color, '__iter__') and not isinstance(color, str):
                                color_map[stream_name] = str(color)
        
        # Also populate color_map from STREAM_COLOR_MAPS and comprehensive mapping
        tab_value = active_tab if active_tab in STREAM_COLOR_ORDERS else "yearly"
        stream_color_map = get_stream_color_map(tab_value)
        for stream_name, stream_color in stream_color_map.items():
            if stream_name not in color_map:  # Don't override chart colors
                color_map[stream_name] = stream_color
        
        # For monthly streams, also add comprehensive color mapping
        # Create a normalized lookup map for case-insensitive matching
        normalized_color_map = {}
        if tab_value == "monthly":
            print(f"DEBUG COLOR: Populating monthly color map, MONTHLY_CRUDE_COLORS has {len(MONTHLY_CRUDE_COLORS)} entries")
            for stream_name, stream_color in MONTHLY_CRUDE_COLORS.items():
                normalized_key = stream_name.lower().strip()
                if normalized_key not in normalized_color_map:
                    normalized_color_map[normalized_key] = (stream_name, stream_color)
                # Also add exact match if not already in color_map
                if stream_name not in color_map:
                    color_map[stream_name] = stream_color
            print(f"DEBUG COLOR: After populating, color_map has {len(color_map)} entries, normalized_color_map has {len(normalized_color_map)} entries")
        
        # Create clickable stream buttons with highlight/dimmed states
        stream_items = []
        selected_set = set(selected_streams) if selected_streams else set()
        profile_urls_dict = {}  # Store profile URLs for navigation
        
        # Helper function to dim a color (reduce opacity/brightness)
        def dim_color(color_hex, opacity=0.3):
            """Convert color to a dimmed version with reduced opacity"""
            if isinstance(color_hex, str) and color_hex.startswith('#'):
                try:
                    r = int(color_hex[1:3], 16)
                    g = int(color_hex[3:5], 16)
                    b = int(color_hex[5:7], 16)
                    # Create rgba with reduced opacity
                    return f"rgba({r}, {g}, {b}, {opacity})"
                except:
                    return color_hex
            return color_hex
        
        for opt in stream_options:
            stream = opt["value"]
            # Normalize stream name (strip whitespace, handle None)
            if stream:
                stream = str(stream).strip()
            else:
                stream = ""
            is_selected = stream in selected_set
            profile_url = opt.get("profile_url")  # Get profile_url from options
            
            # Store profile URL for navigation
            if profile_url:
                profile_urls_dict[stream] = profile_url
            
            # Get color for this stream - check multiple sources
            color = None
            stream_normalized = stream.lower().strip() if stream else ""
            
            # First check exact match in color_map
            if stream in color_map:
                color = color_map[stream]
                if tab_value == "monthly":
                    print(f"DEBUG COLOR: Stream '{stream}' found in color_map with color '{color}'")
            # Then check normalized lookup for monthly streams
            elif tab_value == "monthly" and stream_normalized in normalized_color_map:
                _, color = normalized_color_map[stream_normalized]
                print(f"DEBUG COLOR: Stream '{stream}' (normalized: '{stream_normalized}') found in normalized_color_map with color '{color}'")
            # Then check comprehensive mapping directly (case-insensitive)
            elif tab_value == "monthly":
                found_match = False
                for key, value in MONTHLY_CRUDE_COLORS.items():
                    if key.lower().strip() == stream_normalized:
                        color = value
                        found_match = True
                        print(f"DEBUG COLOR: Stream '{stream}' matched '{key}' in MONTHLY_CRUDE_COLORS with color '{color}'")
                        break
                # If still not found, use get_stream_color which also checks comprehensive mapping
                if not found_match:
                    print(f"DEBUG COLOR: Stream '{stream}' not found in MONTHLY_CRUDE_COLORS, trying get_stream_color")
                    color = get_stream_color(stream, all_available_streams, tab=tab_value)
                    print(f"DEBUG COLOR: get_stream_color returned '{color}' for '{stream}'")
            else:
                # Final fallback
                color = get_stream_color(stream, all_available_streams, tab=tab_value)
            
            # Ensure we have a color (fallback to gray if still None)
            if not color:
                print(f"DEBUG COLOR: WARNING - No color found for stream '{stream}', using gray fallback")
                color = "#808080"
            elif tab_value == "monthly" and color == "#808080":
                print(f"DEBUG COLOR: Stream '{stream}' got gray fallback color")
            
            # Convert color to hex if needed
            color_hex = color
            if isinstance(color, str) and color.startswith('rgb'):
                color_hex = color
            elif isinstance(color, tuple):
                color_hex = f"rgb({color[0]}, {color[1]}, {color[2]})"
            
            # Apply highlight/dimmed styling based on selection
            if is_selected:
                # Highlighted: use full color, solid background with white text
                bg_color = color_hex
                text_color = "#ffffff"  # Always white text for highlighted items
                border_color = "#000000"  # Black border for highlighted
                border_width = "1px"
            else:
                # Dimmed: use lighter/muted background
                # Convert to lighter version by mixing with white
                if isinstance(color_hex, str) and color_hex.startswith('#'):
                    try:
                        r = int(color_hex[1:3], 16)
                        g = int(color_hex[3:5], 16)
                        b = int(color_hex[5:7], 16)
                        # Mix with white (80% white, 20% original color) for dimmed effect
                        r_dimmed = int(r * 0.2 + 255 * 0.8)
                        g_dimmed = int(g * 0.2 + 255 * 0.8)
                        b_dimmed = int(b * 0.2 + 255 * 0.8)
                        bg_color = f"rgb({r_dimmed}, {g_dimmed}, {b_dimmed})"
                    except:
                        bg_color = "#e0e0e0"  # Fallback light gray
                else:
                    bg_color = "#e0e0e0"  # Fallback light gray
                text_color = "#ffffff"  # White text for dimmed items too
                border_color = "#ccc"  # Light border for dimmed
                border_width = "1px"
            
            # Create stream button style - highlighted or dimmed
            stream_button_style = {
                "fontSize": "12px",
                "verticalAlign": "middle",
                "backgroundColor": bg_color,
                "padding": "6px 10px",  # Reduced padding to make bars thinner
                "borderRadius": "0px",  # No border radius to match fig2
                "display": "block",
                "width": "100%",  # Reduced width from 100% to make bars thinner
                "textAlign": "left",
                "color": text_color,
                "fontWeight": "500",
                "cursor": "pointer",
                "border": f"{border_width} solid {border_color}",
                "marginBottom": "0px",
                "transition": "all 0.2s ease",
                "outline": "none"  # Remove focus outline
            }
            
            # Create clickable button (don't use profile_url for selection - handle clicks separately)
            stream_button = html.Button(
                stream,
                id={"type": "stream-button", "stream": stream},
                n_clicks=0,
                style=stream_button_style
            )
            
            stream_items.append(stream_button)
        
        print(f"DEBUG NAVIGATION: Storing {len(profile_urls_dict)} profile URLs: {list(profile_urls_dict.keys())[:5]}...")
        return stream_items, profile_urls_dict
    
    @dash_app.callback(
        Output("profiled-streams", "value", allow_duplicate=True),
        [Input({"type": "stream-button", "stream": ALL}, "n_clicks")],
        [State({"type": "stream-button", "stream": ALL}, "id"),
         State("profiled-streams", "value")],
        prevent_initial_call=True
    )
    def update_profiled_streams_from_buttons(button_clicks, button_ids, current_selected):
        """Update profiled-streams selection when stream buttons are clicked - toggle behavior"""
        from dash import ctx
        if not ctx.triggered:
            return no_update
            
        # CRITICAL: Ensure this only runs if a button was actually clicked.
        # Pattern-matching callbacks can trigger when buttons are added to the layout (Input ALL).
        # We check if any of the buttons have n_clicks > 0.
        if not any(click and click > 0 for click in (button_clicks or []) if click is not None):
            return no_update
        
        # Find which button was clicked using ctx.triggered
        clicked_stream = None
        triggered_id = ctx.triggered[0]["prop_id"]
        
        # Parse the triggered_id to get the stream name
        # Format: '{"type":"stream-button","stream":"Arco"}.n_clicks'
        if 'stream-button' in triggered_id:
            try:
                import json
                # Extract the JSON part
                start_idx = triggered_id.find('{')
                end_idx = triggered_id.find('}', start_idx) + 1
                if start_idx >= 0 and end_idx > start_idx:
                    id_dict = json.loads(triggered_id[start_idx:end_idx])
                    if isinstance(id_dict, dict) and "stream" in id_dict:
                        clicked_stream = id_dict["stream"]
            except Exception as e:
                print(f"Error parsing triggered_id: {e}")
        
        if not clicked_stream:
            return no_update
        
        # Get all available streams from button_ids
        all_streams = []
        if button_ids:
            for button_id in button_ids:
                if isinstance(button_id, dict) and "stream" in button_id:
                    all_streams.append(button_id["stream"])
        
        # Get current selection
        current_selected = current_selected if current_selected else []
        current_set = set(current_selected)
        all_set = set(all_streams)
        
        # Determine if we're in default mode (all streams selected)
        is_default_mode = (current_set == all_set and len(all_set) > 0) or len(current_set) == 0
        
        # Toggle behavior:
        # - If in default mode (all selected): clicking a stream selects only that stream
        # - If one stream is selected: clicking the same stream returns to default (all selected)
        if is_default_mode:
            # Default mode: clicking any stream selects only that stream
            return [clicked_stream]
        elif len(current_set) == 1 and clicked_stream in current_set:
            # One stream selected and clicking the same stream: return to default (all selected)
            return sorted(all_streams) if all_streams else []
        else:
            # Clicking a different stream when one is already selected: select the clicked stream
            return [clicked_stream]
    
    # Clientside callback to navigate to stream profile URL and track last clicked stream
    clientside_callback(
        """
        function(button_clicks, button_ids, profile_urls, last_clicked_stream) {
            if (!window.dash_clientside) {
                return null;
            }
            
            if (!profile_urls || Object.keys(profile_urls).length === 0) {
                console.log('No profile URLs available');
                return null;
            }
            
            // Find which button was clicked
            const triggered = window.dash_clientside.callback_context.triggered[0];
            if (!triggered) {
                return null;
            }
            
            // Parse the triggered_id to get the stream name
            // Format: '{"type":"stream-button","stream":"Arco"}.n_clicks'
            try {
                const jsonPart = triggered.prop_id.split('.')[0];
                const buttonId = JSON.parse(jsonPart);
                const clickedStream = buttonId.stream;
                
                console.log('Button clicked for stream:', clickedStream);
                console.log('Last clicked stream:', last_clicked_stream);
                
                // Check if this is the same stream as last clicked - if so, don't navigate
                // We compare against the last_clicked_stream from the store
                if (clickedStream === last_clicked_stream) {
                    console.log('Same stream clicked again, skipping navigation');
                    return null;
                }
                
                console.log('Available profile URLs:', Object.keys(profile_urls));
                
                if (clickedStream && profile_urls[clickedStream]) {
                    const profileUrl = profile_urls[clickedStream];
                    if (profileUrl && profileUrl !== 'nan' && profileUrl !== 'None' && profileUrl.trim() !== '') {
                        console.log('Navigating to', profileUrl, 'for stream', clickedStream);
                        // Open in new tab
                        window.open(profileUrl, '_blank');
                        // Return the clicked stream so it becomes the new last_clicked_stream
                        return clickedStream;
                    } else {
                        console.log('Invalid URL for stream', clickedStream, ':', profileUrl);
                    }
                } else {
                    console.log('No URL found for stream:', clickedStream);
                }
            } catch (e) {
                console.error('Error parsing button click:', e);
            }
            
            return null;
        }
        """,
        Output("last-clicked-stream-store", "data"),
        [Input({"type": "stream-button", "stream": ALL}, "n_clicks")],
        [State({"type": "stream-button", "stream": ALL}, "id"),
         State("stream-profile-urls-store", "data"),
         State("last-clicked-stream-store", "data")]
    )
    
    @dash_app.callback(
        [Output("year-controls", "style"),
         Output("year-month-controls", "style"),
         Output("production-year-filter", "style")],
        Input("crude-main-tabs", "value"),
        prevent_initial_call=False
    )
    def toggle_controls(tab):
        """Show/hide year and year-month controls based on tab"""
        if tab == "yearly":
            return {"display": "block"}, {"display": "none"}, {"display": "none"}
        else:
            return {"display": "none"}, {"display": "block"}, {"display": "block"}
    
    @dash_app.callback(
        Output("selected-country-map-store", "data"),
        [Input("crude-map", "clickData")],
        [State("selected-country-map-store", "data"),
         State("current-submenu", "data")],
        prevent_initial_call=True
    )
    def update_selected_country_map(click_data, current_selected, submenu):
        """Update country selection from map click, toggle if clicked again"""
        if submenu != 'crude-overview':
            return no_update
            
        if click_data and click_data.get("points"):
            clicked_country = click_data["points"][0].get("location")
            if clicked_country:
                # Toggle logic: if already selected, reset to None
                if clicked_country == current_selected:
                    return None
                return clicked_country
        return current_selected
    
    @dash_app.callback(
        Output("crude-map", "figure"),
        [Input("crude-year-dropdown", "value"),
         Input("crude-year-month-dropdown", "value"),
         Input("crude-country-dropdown", "value"),
         Input("crude-main-tabs", "value"),
         Input("selected-country-map-store", "data"),
         Input("current-submenu", "data")],
        prevent_initial_call=False
    )
    def update_map(selected_year, selected_year_month, selected_countries, tab, selected_country_map, current_submenu):
        """Update world map based on filters - only loads data when page is active"""
        # Only load data if page is active
        if current_submenu != 'crude-overview':
            fig = go.Figure()
            fig.update_layout(height=600, plot_bgcolor='white', paper_bgcolor='white')
            return fig
        
        # Ensure data is loaded
        _ensure_data_loaded()
        selected_countries = _resolve_countries_selection(selected_countries)
        
        # Set defaults if None
        if selected_year is None:
            selected_year = 2024  # Default to 2024 for yearly filter
        if tab is None:
            tab = "yearly"
        
        try:
            if tab == "yearly":
                if not MAP_YEARLY_LONG.empty and "year" in MAP_YEARLY_LONG.columns:
                    agg = MAP_YEARLY_LONG[MAP_YEARLY_LONG["year"] == str(selected_year)].copy()
                    if len(agg) > 0:
                        agg = agg.groupby("GeoCountry").agg({
                            "value": "sum",
                            "Country": lambda x: x.iloc[0] if len(x.unique()) == 1 else COUNTRY_NAME_MAPPING.get(x.iloc[0], x.iloc[0])
                        }).reset_index()
                    else:
                        agg = pd.DataFrame(columns=["Country", "GeoCountry", "value"])
                else:
                    agg = pd.DataFrame(columns=["Country", "GeoCountry", "value"])
            else:
                # Monthly view - Map uses Year Month dropdown
                print(f"DEBUG MAP MONTHLY: selected_year_month={selected_year_month}, tab={tab}, MAP_MONTHLY_LONG empty={MAP_MONTHLY_LONG.empty}")
                
                # Set default year_month if not provided - default to 2025-07
                if not selected_year_month:
                    selected_year_month = "2025-07"  # Default to 2025-07 for monthly filter
                    print(f"DEBUG MAP MONTHLY: Using default selected_year_month={selected_year_month}")
                
                if not MAP_MONTHLY_LONG.empty:
                    print(f"DEBUG MAP MONTHLY: columns={MAP_MONTHLY_LONG.columns.tolist()}")
                    print(f"DEBUG MAP MONTHLY: MAP_MONTHLY_LONG length={len(MAP_MONTHLY_LONG)}")
                    if "year" in MAP_MONTHLY_LONG.columns and "month" in MAP_MONTHLY_LONG.columns:
                        if selected_year_month:
                            year, month = selected_year_month.split("-")
                            year = str(year)
                            month = int(month)
                            print(f"DEBUG MAP MONTHLY: Filtering by year={year}, month={month}")
                            agg = MAP_MONTHLY_LONG[(MAP_MONTHLY_LONG["year"] == year) & 
                                                  (MAP_MONTHLY_LONG["month"] == month)].copy()
                            print(f"DEBUG MAP MONTHLY: After filter, agg length={len(agg)}")
                        else:
                            # Use default: latest year and month
                            if len(MAP_MONTHLY_LONG) > 0:
                                max_year = MAP_MONTHLY_LONG["year"].max()
                                df_monthly = MAP_MONTHLY_LONG[MAP_MONTHLY_LONG["year"] == max_year].copy()
                                if len(df_monthly) > 0:
                                    max_month = df_monthly["month"].max()
                                    df_monthly = df_monthly[df_monthly["month"] == max_month]
                                    agg = df_monthly.copy()
                                    print(f"DEBUG MAP MONTHLY: Using default max_year={max_year}, max_month={max_month}, agg length={len(agg)}")
                                else:
                                    agg = pd.DataFrame(columns=["Country", "GeoCountry", "value"])
                            else:
                                agg = pd.DataFrame(columns=["Country", "GeoCountry", "value"])
                        
                        if len(agg) > 0:
                            # Group by GeoCountry to merge Abu Dhabi/Dubai and handle renames (USA)
                            # Use 'first' for Country to preserve original label where possible
                            # but if it was a merge (UAE), the GeoCountry name might be better.
                            # For simplicity, we'll keep the first one or just use GeoCountry for the tooltip.
                            agg = agg.groupby("GeoCountry").agg({
                                "value": "sum",
                                "Country": lambda x: x.iloc[0] if len(x.unique()) == 1 else COUNTRY_NAME_MAPPING.get(x.iloc[0], x.iloc[0])
                            }).reset_index()
                            print(f"DEBUG MAP MONTHLY: After groupby, agg length={len(agg)}")
                            print(f"DEBUG MAP MONTHLY: Sample mapping: {agg[['Country', 'GeoCountry']].head().values.tolist()}")
                        else:
                            agg = pd.DataFrame(columns=["Country", "GeoCountry", "value"])
                    else:
                        print(f"DEBUG MAP MONTHLY: Missing required columns. Available: {MAP_MONTHLY_LONG.columns.tolist()}")
                        agg = pd.DataFrame(columns=["Country", "GeoCountry", "value"])
                else:
                    print(f"DEBUG MAP MONTHLY: MAP_MONTHLY_LONG is empty")
                    agg = pd.DataFrame(columns=["Country", "GeoCountry", "value"])
        except Exception as e:
            print(f"Error in update_map: {e}")
            import traceback
            traceback.print_exc()
            agg = pd.DataFrame(columns=["Country", "value"])
        
        # Add year/period for tooltip
        if not agg.empty:
            if tab == "yearly":
                agg["Year"] = str(selected_year)
            else:
                agg["Year"] = str(selected_year_month)
        
        if agg.empty:
            fig = go.Figure()
            fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return fig
        
        # Dynamically scale the color range to the data so the map colors
        # match the production bar scale for the selected period.
        max_val = agg["value"].max() if "value" in agg.columns and len(agg) > 0 else 0
        if pd.isna(max_val) or max_val <= 0:
            max_val = 1000  # sensible fallback to keep the scale visible
        color_max = float(max_val) * 1.05  # small headroom
        # Pick a reasonable tick step based on the max value
        tick_step = max(500, round((color_max / 6) / 500) * 500)
        if tick_step == 0:
            tick_step = 500
        
        # Try Mapbox choropleth; fall back to geo-based choropleth if GeoJSON missing.
        geojson = _load_countries_geojson()
        main_opacity = 0.3 if selected_country_map else 1.0
        
        if geojson:
            fig = px.choropleth_mapbox(
                agg,
                geojson=geojson,
                locations="GeoCountry",
                featureidkey="properties.name",
                color="value",
                color_continuous_scale="Blues",
                labels={"value": "Production ('000 b/d)"},
                custom_data=["Country", "Year"],
                range_color=[0, color_max],
                mapbox_style="open-street-map",
                center={"lat": 20, "lon": 0},
                zoom=1,
                opacity=main_opacity
            )
            fig.update_traces(
                hovertemplate=(
                    "<span style='color: #7f7f7f;'>Country:</span> <span style='font-weight: bold; color: #000;'>%{customdata[0]}</span><br>"
                    "<span style='color: #7f7f7f;'>Production Volume:</span> <span style='font-weight: bold; color: #000;'>%{z:,.0f} ('000 b/d)</span><br>"
                    "<span style='color: #7f7f7f;'>Year:</span> <span style='font-weight: bold; color: #000;'>%{customdata[1]}</span>"
                    "<extra></extra>"
                ) if tab == "yearly" else (
                    "<span style='color: #7f7f7f;'>Date:</span> <span style='font-weight: bold; color: #000;'>%{customdata[1]}</span><br>"
                    "<span style='color: #7f7f7f;'>Country:</span> <span style='font-weight: bold; color: #000;'>%{customdata[0]}</span><br>"
                    "<span style='color: #7f7f7f;'>Production Volume:</span> <span style='font-weight: bold; color: #000;'>%{z:,.0f} ('000 b/d)</span>"
                    "<extra></extra>"
                )
            )
            
            if selected_country_map:
                sel_df = agg[agg["GeoCountry"] == selected_country_map]
                if not sel_df.empty:
                    fig.add_trace(
                        go.Choroplethmapbox(
                            geojson=geojson,
                            locations=sel_df["GeoCountry"],
                            featureidkey="properties.name",
                            z=sel_df["value"],
                            colorscale="Blues",
                            zmin=0, zmax=color_max,
                            showscale=False,
                            marker=dict(opacity=1.0, line=dict(color="#FF6B35", width=3)),
                            hovertemplate=fig.data[0].hovertemplate,
                            customdata=sel_df[["Country", "Year"]].values
                        )
                    )

            fig.update_layout(
                margin=dict(l=10, r=10, t=10, b=80),
                height=500,
                coloraxis_colorbar=dict(
                    title=dict(text="Production<br>('000 b/d)", font=dict(size=12)),
                    tickfont=dict(size=10),
                    orientation="h",
                    x=0.5,
                    xanchor="center",
                    y=-0.12,
                    yanchor="top",
                    len=0.7,
                    thickness=20,
                    outlinewidth=0,
                    bordercolor="white",
                    bgcolor="rgba(255,255,255,0)",
                    tickmode="linear",
                    tickformat=",",
                    tick0=0,
                    dtick=tick_step,
                    showticklabels=True,
                    ticks="outside"
                ),
                template="plotly_white",
                autosize=True,
                hoverlabel=dict(
                    bgcolor="white",
                    bordercolor="#ccc",
                    font=dict(family="Arial", size=13, color="black"),
                    align="left"
                )
            )
        else:
            fig = px.choropleth(
                agg, 
                locations="GeoCountry", 
                locationmode="country names", 
                color="value",
                projection="natural earth", 
                color_continuous_scale="Blues",
                labels={"value":"Production ('000 b/d)"},
                custom_data=["Country", "Year"],
                range_color=[0, color_max],
                opacity=main_opacity
            )
            fig.update_traces(
                hovertemplate=(
                    "<span style='color: #7f7f7f;'>Country:</span> <span style='font-weight: bold; color: #000;'>%{customdata[0]}</span><br>"
                    "<span style='color: #7f7f7f;'>Production Volume:</span> <span style='font-weight: bold; color: #000;'>%{z:,.0f} ('000 b/d)</span><br>"
                    "<span style='color: #7f7f7f;'>Year:</span> <span style='font-weight: bold; color: #000;'>%{customdata[1]}</span>"
                    "<extra></extra>"
                ) if tab == "yearly" else (
                    "<span style='color: #7f7f7f;'>Date:</span> <span style='font-weight: bold; color: #000;'>%{customdata[1]}</span><br>"
                    "<span style='color: #7f7f7f;'>Country:</span> <span style='font-weight: bold; color: #000;'>%{customdata[0]}</span><br>"
                    "<span style='color: #7f7f7f;'>Production Volume:</span> <span style='font-weight: bold; color: #000;'>%{z:,.0f} ('000 b/d)</span>"
                    "<extra></extra>"
                )
            )
            
            if selected_country_map:
                sel_df = agg[agg["GeoCountry"] == selected_country_map]
                if not sel_df.empty:
                    fig.add_trace(
                        go.Choropleth(
                            locations=sel_df["GeoCountry"],
                            locationmode="country names",
                            z=sel_df["value"],
                            colorscale="Blues",
                            zmin=0, zmax=color_max,
                            showscale=False,
                            marker=dict(opacity=1.0, line=dict(color="#FF6B35", width=3)),
                            hovertemplate=fig.data[0].hovertemplate,
                            customdata=sel_df[["Country", "Year"]].values
                        )
                    )

            fig.update_layout(
                margin=dict(l=10,r=10,t=10,b=80),
                height=500,
                geo=dict(
                    bgcolor="white",
                    showframe=False,
                    showcoastlines=True,
                    projection_type="natural earth",
                    projection=dict(
                        type="natural earth",
                        scale=1.0,
                        rotation=dict(lon=0, lat=0)
                    ),
                    lonaxis=dict(range=[-180, 180], showgrid=False),
                    lataxis=dict(range=[-90, 90], showgrid=False),
                    center=dict(lon=0, lat=0),
                    visible=True,
                    domain=dict(x=[0, 1], y=[0, 1]),
                    showland=True,
                    showocean=True,
                    showlakes=True,
                    showrivers=False,
                    coastlinewidth=0.5,
                    countrywidth=0.5
                ),
                coloraxis_colorbar=dict(
                    title=dict(text="Production<br>('000 b/d)", font=dict(size=12)),
                    tickfont=dict(size=10),
                    orientation="h",
                    x=0.5,
                    xanchor="center",
                    y=-0.12,
                    yanchor="top",
                    len=0.7,
                    thickness=20,
                    outlinewidth=0,
                    bordercolor="white",
                    bgcolor="rgba(255,255,255,0)",
                    tickmode="linear",
                    tickformat=",",
                    tick0=0,
                    dtick=tick_step,
                    showticklabels=True,
                    ticks="outside"
                ),
                template="plotly_white",
                autosize=True,
                hoverlabel=dict(
                    bgcolor="white",
                    bordercolor="#ccc",
                    font=dict(family="Arial", size=13, color="black"),
                    align="left"
                )
            )
        fig.update_geos(
            resolution=50,
            showcountries=True,
            countrycolor="lightgray",
            coastlinecolor="lightgray",
            landcolor="white",
            lakecolor="white",
            oceancolor="white"
        )
        return fig
    
    @dash_app.callback(
        [Output("production-breakdown-chart", "figure"),
         Output("production-breakdown-title", "children")],
        [Input("crude-country-dropdown", "value"),
         Input("crude-year-dropdown", "value"),
         Input("crude-year-month-dropdown", "value"),
         Input("production-year-dropdown", "value"),  # Year of Date filter for monthly chart
         Input("profiled-streams", "value"),
         Input("crude-main-tabs", "value"),
         Input("selected-country-map-store", "data"),
         Input("current-submenu", "data")],
        prevent_initial_call=False
    )
    def update_breakdown(country, year, year_month, production_years, profiled, tab, selected_country_map, current_submenu):
        """Update production breakdown chart - only loads data when page is active"""
        # Only load data if page is active
        if current_submenu != 'crude-overview':
            fig = go.Figure()
            fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return fig, ""
        
        # Ensure data is loaded
        _ensure_data_loaded()
        _ensure_color_maps()
        
        # Store original country selection for title formatting (before resolution)
        original_country_selection = country
        
        # Resolve country selection for data filtering
        country = _resolve_countries_selection(country)
        
        try:
            month_names = ["January", "February", "March", "April", "May", "June",
                          "July", "August", "September", "October", "November", "December"]
            
            # Handle map selection - update country selection
            if selected_country_map:
                country = [selected_country_map]
                original_country_selection = [selected_country_map]
                print(f"DEBUG: Map selection active, country={selected_country_map}")
            
            if year is None:
                year = int(YEARS[-1]) if YEARS else 2024
            if tab is None:
                tab = "yearly"
            
            # Handle country - ensure it's a list and resolve "(All)" if present
            resolved_countries = _resolve_countries_selection(original_country_selection)
            # If no countries selected, return empty chart
            if not resolved_countries:
                print(f"DEBUG BREAKDOWN: No countries selected, returning empty chart")
                fig = go.Figure()
                fig.add_annotation(
                    text="No countries selected. Please select at least one country.",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=14, color='#7f8c8d')
                )
                fig.update_layout(
                    height=360,
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    xaxis=dict(showgrid=False, showticklabels=False),
                    yaxis=dict(showgrid=False, showticklabels=False)
                )
                return fig, "Production Breakdown"
            
            country = resolved_countries  # Use resolved list for filtering
            
            # Handle profiled streams - if empty, show all available streams (don't filter)
            # profiled will be used later to filter if it has values
            
            # Format title based on original country selection
            title_text = _format_production_breakdown_title(original_country_selection)
            
            if tab == "yearly":
                # For yearly view: Show all years on X-axis, stack streams for each year
                print(f"DEBUG BREAKDOWN YEARLY START: Country={country}, Tab={tab}, Profiled={profiled}")
                print(f"DEBUG BREAKDOWN YEARLY: BAR_LONG_YEARLY empty={BAR_LONG_YEARLY.empty}")
                print(f"DEBUG BREAKDOWN YEARLY: BAR_LONG_YEARLY columns={BAR_LONG_YEARLY.columns.tolist() if not BAR_LONG_YEARLY.empty else 'N/A'}")
                print(f"DEBUG BREAKDOWN YEARLY: BAR_LONG_YEARLY shape={BAR_LONG_YEARLY.shape if not BAR_LONG_YEARLY.empty else 'N/A'}")
                
                # Initialize available_streams early
                available_streams = []
                
                if not BAR_LONG_YEARLY.empty and "Country" in BAR_LONG_YEARLY.columns and "year" in BAR_LONG_YEARLY.columns:
                    # Filter by country only (show all years)
                    df = BAR_LONG_YEARLY[BAR_LONG_YEARLY["Country"].isin(country)].copy()
                    print(f"DEBUG BREAKDOWN YEARLY: After country filter, df length={len(df)}")
                    print(f"DEBUG BREAKDOWN YEARLY: Unique streams in data: {df['Stream'].unique().tolist() if len(df) > 0 else 'N/A'}")
                    
                    # Get available streams from yearly grades (DB) for all selected countries
                    grades_for_country = get_yearly_grades_for_country(country)
                    if not grades_for_country.empty and "Stream" in grades_for_country.columns:
                        available_streams = order_streams_list(grades_for_country["Stream"].dropna().unique().tolist(), tab="yearly")
                        print(f"DEBUG BREAKDOWN YEARLY: Available streams from yearly DB: {available_streams} ({len(available_streams)} streams)")
                        
                        # Filter data to only show streams from DB result
                        if available_streams:
                            streams_in_data = df["Stream"].unique().tolist()
                            matching_streams = [s for s in available_streams if s in streams_in_data]
                            print(f"DEBUG BREAKDOWN YEARLY: Matching streams between yearly DB and data: {matching_streams}")
                            if matching_streams:
                                df = df[df["Stream"].isin(matching_streams)].copy()
                                print(f"DEBUG BREAKDOWN YEARLY: After yearly DB filter, df length={len(df)}")
                            else:
                                print(f"DEBUG BREAKDOWN YEARLY: WARNING - No matching streams found! Yearly DB streams: {available_streams}, Data streams: {streams_in_data}")
                                # Don't filter - show all streams from data
                        else:
                            print(f"DEBUG BREAKDOWN YEARLY: No streams from yearly DB, showing all streams from data")
                    else:
                        print(f"DEBUG BREAKDOWN YEARLY: Yearly DB result is empty or missing Stream column")
                        # Use all streams from data
                        available_streams = order_streams_list(df["Stream"].dropna().unique().tolist(), tab="yearly") if len(df) > 0 else []
                else:
                    df = pd.DataFrame(columns=["Stream", "Country", "year", "value", "month_idx"])
                    print("DEBUG BREAKDOWN YEARLY: BAR_LONG_YEARLY is empty or missing columns")
                
                if len(df) == 0:
                    print("DEBUG BREAKDOWN YEARLY: No data after initial filtering, returning empty chart")
                    # Create empty chart with proper structure
                    empty_df = pd.DataFrame({"year": [str(y) for y in range(2006, 2025)], "value": [0]*19})
                    fig = px.bar(empty_df, x="year", y="value", labels={"value":"Production Volume ('000 b/d)", "year":"Year"})
                    fig.update_layout(
                        # title removed
                        xaxis_title="Year",
                        yaxis_title="Production Volume ('000 b/d)",
                        barmode="stack",
                        plot_bgcolor="white",
                        paper_bgcolor="white",
                        xaxis=dict(
                            type="category",
                            categoryorder="array",
                            categoryarray=[str(y) for y in range(2006, 2025)]  # 2006 to 2024 ascending
                        )
                    )
                    return fig, title_text
                
                # Apply profiled streams filter - check if all streams are selected (default mode)
                # If all streams selected, don't filter (show all streams)
                # If a specific stream is selected, filter to show only that stream
                is_single_stream_selected = False
                selected_stream = None
                if profiled and len(profiled) > 0:
                    # Check if all available streams are selected (default mode)
                    profiled_set = set(profiled)
                    available_set = set(available_streams) if available_streams else set()
                    
                    # If all streams are selected, don't filter (show all)
                    if profiled_set == available_set and len(available_set) > 0:
                        print(f"DEBUG BREAKDOWN YEARLY: All streams selected (default mode), showing all streams")
                        # Don't filter - show all streams
                        is_single_stream_selected = False
                    elif len(profiled) == 1:
                        # Single stream selected: filter to show only that stream
                        selected_stream = profiled[0]
                        is_single_stream_selected = True
                        if selected_stream in df["Stream"].values:
                            df = df[df["Stream"] == selected_stream].copy()
                            print(f"DEBUG BREAKDOWN YEARLY: After profiled filter (selected: {selected_stream}), df length={len(df)}")
                        else:
                            print(f"DEBUG BREAKDOWN YEARLY: Selected stream '{selected_stream}' not found in data")
                            is_single_stream_selected = False
                    else:
                        # Multiple streams selected (shouldn't happen in single selection mode, but handle it)
                        df = df[df["Stream"].isin(profiled)].copy()
                        print(f"DEBUG BREAKDOWN YEARLY: After profiled filter ({len(profiled)} streams), df length={len(df)}")
                        is_single_stream_selected = False
                else:
                    # If no stream selected, show all streams (default mode)
                    print(f"DEBUG BREAKDOWN YEARLY: No stream selected, showing all streams (default mode)")
                    is_single_stream_selected = False
                
                # Group by year and stream, sum values
                # Include Country in aggregation if available for hover template
                if "Country" in df.columns:
                    # Aggregate with Country - get unique countries per year/Stream combination
                    country_info = df.groupby(["year", "Stream"])["Country"].apply(
                        lambda x: ", ".join(sorted(x.unique()))
                    ).reset_index(name="Country")
                    agg = df.groupby(["year", "Stream"])["value"].sum().reset_index()
                    agg = agg.merge(country_info, on=["year", "Stream"], how="left")
                else:
                    # Fallback: use country filter variable
                    agg = df.groupby(["year", "Stream"])["value"].sum().reset_index()
                    if country and len(country) > 0:
                        agg["Country"] = ", ".join(sorted(country)) if len(country) > 1 else country[0]
                    else:
                        agg["Country"] = ""
                
                # Filter years to 2006-2024 range
                agg["year"] = agg["year"].astype(str)
                agg["year_int"] = pd.to_numeric(agg["year"], errors="coerce")
                agg = agg[(agg["year_int"] >= 2006) & (agg["year_int"] <= 2024)].copy()
                agg = agg.drop(columns=["year_int"])
                
                # Ensure all years from 2006-2024 are in the sorted list for proper X-axis display
                all_years = [str(y) for y in range(2006, 2025)]  # 2006 to 2024
                years_sorted = sorted(all_years)  # 2006 to 2024 (ascending order)
                
                print(f"DEBUG BREAKDOWN YEARLY: Years in data: {sorted(agg['year'].unique()) if len(agg) > 0 else 'N/A'}")
                print(f"DEBUG BREAKDOWN YEARLY: All years to display: {years_sorted} ({len(years_sorted)} years)")
                print(f"DEBUG BREAKDOWN YEARLY: Streams in data: {agg['Stream'].unique().tolist() if len(agg) > 0 else 'N/A'} ({len(agg['Stream'].unique()) if len(agg) > 0 else 0} streams)")
                print(f"DEBUG BREAKDOWN YEARLY: Total records: {len(agg)}")
                if len(agg) > 0:
                    print(f"DEBUG BREAKDOWN YEARLY: Sample data:\n{agg.head(20)}")
                
                if len(agg) == 0:
                    print("DEBUG BREAKDOWN YEARLY: No data after grouping, returning empty chart with year structure")
                    # Create empty chart but with all years on X-axis
                    empty_df = pd.DataFrame({"year": years_sorted, "value": [0]*len(years_sorted)})
                    fig = px.bar(empty_df, x="year", y="value", labels={"value":"Production Volume ('000 b/d)", "year":"Year"})
                    fig.update_layout(
                        # title=dict(text=title_text, font=dict(color="#d35400", size=18, family="Arial, sans-serif"), x=0.5, xanchor="center", y=0.98),
                        xaxis_title="Year",
                        yaxis_title="Production Volume ('000 b/d)",
                        barmode="stack",
                        plot_bgcolor="white",
                        paper_bgcolor="white",
                        xaxis=dict(
                            type="category",
                            categoryorder="array",
                            categoryarray=years_sorted
                        )
                    )
                    return fig, title_text
                
                # Get all available streams for consistent coloring
                all_available_streams = available_streams if available_streams else order_streams_list(agg["Stream"].unique().tolist(), tab="yearly")
                
                # Create color map - use specific colors for known streams, fallback to palette
                unique_streams = order_streams_list(agg["Stream"].unique().tolist(), tab="yearly")
                color_map = {}
                for stream in unique_streams:
                    color_map[stream] = get_stream_color(stream, all_available_streams, tab="yearly")
                
                print(f"DEBUG BREAKDOWN YEARLY: Color map: {color_map}")
                
                # Handle years based on selection mode
                all_years_list = [str(y) for y in range(2006, 2025)]
                all_streams_list = order_streams_list(agg["Stream"].unique().tolist(), tab="yearly")
                
                if is_single_stream_selected:
                    # Single stream selected: Only show years that have data for this stream
                    # Filter out years with zero or no data
                    agg_with_data = agg[agg["value"] > 0].copy()
                    years_with_data = sorted(agg_with_data["year"].unique().tolist())
                    
                    print(f"DEBUG BREAKDOWN YEARLY: Single stream selected ({selected_stream})")
                    print(f"DEBUG BREAKDOWN YEARLY: Years with data: {years_with_data}")
                    
                    # Only include years that have actual data
                    agg_for_chart = agg_with_data.copy()
                    
                    # Update years_sorted to only include years with data
                    years_sorted = years_with_data
                    
                    print(f"DEBUG BREAKDOWN YEARLY: Filtered to years with data: {years_sorted} ({len(years_sorted)} years)")
                else:
                    # Default mode (all streams): Show all years from 2006-2024
                    print(f"DEBUG BREAKDOWN YEARLY: Creating complete combo - years: {len(all_years_list)}, streams: {len(all_streams_list)}")
                    
                    # Create complete combination
                    complete_combos = pd.DataFrame(list(itertools.product(all_years_list, all_streams_list)), 
                                                   columns=["year", "Stream"])
                    
                    # Merge with actual data
                    agg_complete = complete_combos.merge(agg, on=["year", "Stream"], how="left")
                    agg_complete["value"] = agg_complete["value"].fillna(0)
                    
                    print(f"DEBUG BREAKDOWN YEARLY: Complete data shape: {agg_complete.shape}")
                    print(f"DEBUG BREAKDOWN YEARLY: Years in complete data: {sorted(agg_complete['year'].unique())}")
                    print(f"DEBUG BREAKDOWN YEARLY: Streams in complete data: {agg_complete['Stream'].unique().tolist()}")
                    print(f"DEBUG BREAKDOWN YEARLY: Non-zero records: {len(agg_complete[agg_complete['value'] > 0])}")
                    
                    # IMPORTANT: For X-axis to show all years, we need to ensure each year appears in the data
                    # Plotly will only show categories that exist in the data, so we need to include all years
                    # We'll filter out zero values for individual stream-year combos, but ensure each year
                    # has at least one entry (even if it's a tiny value) so it appears on the X-axis
                    
                    agg_nonzero = agg_complete.copy()
                    
                    years_in_data = set(agg_nonzero["year"].unique())
                    missing_years = [y for y in all_years_list if y not in years_in_data]
                    
                    print(f"DEBUG BREAKDOWN YEARLY: Years with non-zero data: {sorted(years_in_data)}")
                    print(f"DEBUG BREAKDOWN YEARLY: Missing years (will add placeholder): {missing_years}")
                    
                    # For years that have no data at all, add a placeholder entry so they appear on X-axis
                    # Use a very small value (0.0001) that won't be visible but ensures the year appears
                    if missing_years and len(all_streams_list) > 0:
                        placeholder_data = pd.DataFrame({
                            "year": missing_years,
                            "Stream": [all_streams_list[0]] * len(missing_years),
                            "value": [0.0001] * len(missing_years)  # Tiny invisible value
                        })
                        # Add Country column to placeholder if Country exists in agg_complete
                        if "Country" in agg_complete.columns:
                            # Get Country from the first non-null value in agg_complete, or use empty string
                            default_country = agg_complete["Country"].dropna().iloc[0] if not agg_complete["Country"].dropna().empty else ""
                            placeholder_data["Country"] = default_country
                        agg_for_chart = pd.concat([agg_nonzero, placeholder_data], ignore_index=True)
                        print(f"DEBUG BREAKDOWN YEARLY: Added placeholder entries for {len(missing_years)} years")
                    else:
                        agg_for_chart = agg_nonzero
                    
                    years_sorted = sorted(all_years_list)  # 2006 to 2024 (ascending order)
                
                print(f"DEBUG BREAKDOWN YEARLY: Final chart data shape: {agg_for_chart.shape}")
                print(f"DEBUG BREAKDOWN YEARLY: Years in chart data: {sorted(agg_for_chart['year'].unique())}")
                print(f"DEBUG BREAKDOWN YEARLY: Years for X-axis: {years_sorted}")
                if len(agg_for_chart) > 0:
                    print(f"DEBUG BREAKDOWN YEARLY: Sample of chart data:\n{agg_for_chart.head(20)}")
                
                if len(agg_for_chart) == 0:
                    print("DEBUG BREAKDOWN YEARLY: No data, creating empty chart")
                    # Create empty chart - use years_sorted which is already set based on selection mode
                    if is_single_stream_selected:
                        # For single stream with no data, show empty chart with no years
                        fig = go.Figure()
                        fig.add_annotation(text=f"No data available for {selected_stream}", 
                                         xref="paper", yref="paper",
                                         x=0.5, y=0.5, showarrow=False,
                                         font=dict(size=14, color='#7f8c8d'))
                        fig.update_layout(
                            # title removed
                            xaxis_title="Year",
                            yaxis_title="Production Volume ('000 b/d)",
                            plot_bgcolor="white",
                            paper_bgcolor="white",
                            height=360
                        )
                    else:
                        # Default mode: show all years on X-axis
                        first_stream = all_streams_list[0] if all_streams_list else "None"
                        empty_df = pd.DataFrame({
                            "year": all_years_list,
                            "value": [0.0001] * len(all_years_list),
                            "Stream": [first_stream] * len(all_years_list)
                        })
                        fig = px.bar(empty_df, x="year", y="value", color="Stream", 
                                    labels={"value":"Production Volume ('000 b/d)", "year":"Year"})
                        fig.update_layout(
                            # title removed
                            xaxis_title="Year",
                            yaxis_title="Production Volume ('000 b/d)",
                            barmode="stack",
                            plot_bgcolor="white",
                            paper_bgcolor="white",
                            xaxis=dict(
                                type="category",
                                categoryorder="array",
                                categoryarray=years_sorted,
                                tickmode='array',
                                tickvals=years_sorted,
                                ticktext=years_sorted
                            ),
                            yaxis=dict(range=[0, 100])  # Small range for invisible bars
                        )
                    return fig, title_text
                
                stream_categories = all_streams_list if all_streams_list else get_stream_order("yearly")
                agg_for_chart["Stream"] = pd.Categorical(agg_for_chart["Stream"], categories=stream_categories, ordered=True)
                agg_for_chart = agg_for_chart.sort_values(["year", "Stream"])

                # Create the stacked bar chart using plotly express - px.bar creates vertical bars by default
                print(f"DEBUG BREAKDOWN YEARLY: Creating chart with {len(agg_for_chart)} records")
                try:
                    fig = px.bar(
                        agg_for_chart, 
                        x="year", 
                        y="value",
                        color="Stream",
                        color_discrete_map=color_map,
                        color_discrete_sequence=get_color_sequence("yearly"),
                        category_orders={"Stream": stream_categories},
                        labels={"value":"Production Volume ('000 b/d)", "year":"Year", "Stream":"Stream"},
                        barmode="stack"  # Stack streams for each year
                    )
                    stack_order = list(reversed(stream_categories))
                    order_lookup = {name: idx for idx, name in enumerate(stack_order)}
                    fig.data = tuple(
                        sorted(fig.data, key=lambda trace: order_lookup.get(trace.name, len(order_lookup)))
                    )
                    print(f"DEBUG BREAKDOWN YEARLY: Chart created successfully with {len(fig.data)} traces")
                    print(f"DEBUG BREAKDOWN YEARLY: Years in figure data: {sorted(set([trace.x[i] for trace in fig.data for i in range(len(trace.x)) if trace.x[i] in all_years_list]))}")
                except Exception as e:
                    print(f"ERROR BREAKDOWN YEARLY: Failed to create chart: {e}")
                    import traceback
                    traceback.print_exc()
                    # Return empty chart on error
                    empty_df = pd.DataFrame({"year": years_sorted, "value": [0]*len(years_sorted)})
                    fig = px.bar(empty_df, x="year", y="value", labels={"value":"Production Volume ('000 b/d)", "year":"Year"})
                    fig.update_layout(
                        # title removed
                        xaxis_title="Year",
                        yaxis_title="Production Volume ('000 b/d)",
                        barmode="stack",
                        plot_bgcolor="white",
                        paper_bgcolor="white"
                    )
                    return fig, title_text
                
                # Get year-level ProductionDataValue for annotations (single value per year)
                # This is different from the bar chart values which are stream-level
                year_production_values = YEAR_PRODUCTION_DATA_VALUE if YEAR_PRODUCTION_DATA_VALUE else {}
                
                print(f"DEBUG BREAKDOWN YEARLY: YEAR_PRODUCTION_DATA_VALUE type: {type(YEAR_PRODUCTION_DATA_VALUE)}")
                print(f"DEBUG BREAKDOWN YEARLY: YEAR_PRODUCTION_DATA_VALUE content: {YEAR_PRODUCTION_DATA_VALUE}")
                print(f"DEBUG BREAKDOWN YEARLY: year_production_values: {year_production_values}")
                print(f"DEBUG BREAKDOWN YEARLY: years_sorted: {years_sorted}")
                
                # Calculate max value for Y-axis scaling (use either ProductionDataValue or sum of bars)
                chart_totals_df = agg_for_chart[agg_for_chart["value"] > 0.001].copy()  # Filter out tiny placeholder values
                if len(chart_totals_df) > 0:
                    year_totals = chart_totals_df.groupby("year")["value"].sum().reset_index()
                else:
                    # Fallback to original agg if chart data is empty
                    year_totals = agg.groupby("year")["value"].sum().reset_index()
                year_totals_dict = dict(zip(year_totals["year"], year_totals["value"]))
                
                # Format traces first - ensure equal bar widths
                # Update hover template to show: Country, Crude (Stream), Year
                # Need to set customdata for each trace with Country information
                # Use agg_for_chart which is the actual data used to create the chart
                for trace_idx, trace in enumerate(fig.data):
                    stream_name = trace.name
                    # Build customdata array: [Country] for each data point
                    customdata_list = []
                    if len(trace.x) > 0:
                        for year_val in trace.x:
                            # Match by Stream and year to get Country from agg_for_chart
                            matching_rows = agg_for_chart[
                                (agg_for_chart["Stream"] == stream_name) & 
                                (agg_for_chart["year"] == str(year_val))
                            ]
                            if not matching_rows.empty and "Country" in matching_rows.columns:
                                country_val = matching_rows.iloc[0]["Country"]
                                # Handle NaN/None values
                                if pd.isna(country_val) or country_val == "":
                                    # Fallback to agg if Country is missing in agg_for_chart
                                    agg_matching = agg[
                                        (agg["Stream"] == stream_name) & 
                                        (agg["year"] == str(year_val))
                                    ]
                                    if not agg_matching.empty and "Country" in agg_matching.columns:
                                        country_val = agg_matching.iloc[0]["Country"]
                                    else:
                                        country_val = ""
                            else:
                                # Fallback to agg if not found in agg_for_chart
                                agg_matching = agg[
                                    (agg["Stream"] == stream_name) & 
                                    (agg["year"] == str(year_val))
                                ]
                                if not agg_matching.empty and "Country" in agg_matching.columns:
                                    country_val = agg_matching.iloc[0]["Country"]
                                else:
                                    country_val = ""
                            customdata_list.append([country_val if country_val else ""])
                    
                    # Set customdata
                    if customdata_list:
                        trace.customdata = customdata_list
                    
                    # Update hover template
                    trace.hovertemplate = (
                        "<b>Country:</b> %{customdata[0]}<br>"
                        "<b>Crude:</b> %{fullData.name}<br>"
                        "<b>Year:</b> %{x}<extra></extra>"
                    )
                    trace.marker = dict(line=dict(width=1, color='white'))
                    trace.width = None  # Let Plotly calculate equal widths automatically
                
                # Calculate max bar height first (needed for annotation positioning)
                max_bar_height = max(year_totals_dict.values()) if year_totals_dict else 0
                
                # Add ProductionDataValue above each bar - show only the value (no year, since year is on X-axis)
                # Use year-level ProductionDataValue if available, otherwise use sum of bars
                annotations_list = []
                max_annotation_y = 0
                
                # Create year to index mapping for categorical X-axis positioning
                year_to_index = {year: idx for idx, year in enumerate(years_sorted)}
                
                for year in years_sorted:
                    param_production_value = year_production_values.get(year)
                    # Prefer sum of bars (displayed data) to ensure visual consistency
                    # Fallback to ProductionDataValue only if sum is 0
                    bar_sum = year_totals_dict.get(year, 0)
                    if bar_sum > 0:
                        production_value = bar_sum
                    else:
                        production_value = param_production_value
                    
                    print(f"DEBUG BREAKDOWN YEARLY: Year {year} - Bar Sum: {bar_sum}, ProductionDataValue (ignored if bar>0): {param_production_value}, Final Value: {production_value}")
                    
                    # Always show annotation if we have a value (either ProductionDataValue or sum)
                    if production_value > 0:
                        # Show only the value (no year, since year is on X-axis)
                        annotation_text = f"{int(production_value):,}"
                        # Position annotation above the bar - use bar height + fixed offset
                        bar_height = year_totals_dict.get(year, 0)
                        # Position annotation slightly above the bar (5% of max bar height for consistent spacing)
                        annotation_y = bar_height + (max_bar_height * 0.05) if max_bar_height > 0 else bar_height + 500
                        max_annotation_y = max(max_annotation_y, annotation_y)
                        
                        # Use numeric index for X position (works better with categorical axes)
                        x_index = year_to_index.get(year, 0)
                        
                        print(f"DEBUG BREAKDOWN YEARLY: Adding annotation for year {year} (index {x_index}): text='{annotation_text}', y={annotation_y}, bar_height={bar_height}")
                        
                        annotations_list.append({
                            "text": annotation_text,
                            "x": x_index,  # Use numeric index for categorical X-axis
                            "y": annotation_y,
                            "xref": "x",
                            "yref": "y",
                            "xanchor": "center",
                            "yanchor": "bottom",
                            "showarrow": False,
                            "font": dict(size=11, color="#2c3e50", family="Arial, sans-serif"),
                            "align": "center",
                            "textangle": -90  # Rotate text 90 degrees counterclockwise (bottom to top)
                        })
                    else:
                        print(f"DEBUG BREAKDOWN YEARLY: Skipping annotation for year {year} - no value")
                
                print(f"DEBUG BREAKDOWN YEARLY: Created {len(annotations_list)} annotations, max Y: {max_annotation_y}")
                
                # Calculate Y-axis max to accommodate annotations
                # Calculate expected max annotation Y position
                expected_max_annotation_y = max_bar_height + (max_bar_height * 0.05) if max_bar_height > 0 else 0
                # Use the larger of actual max annotation Y or expected, then add padding
                # Ensure we have enough space - use at least 25% padding above the highest point
                base_max = max(max_annotation_y, expected_max_annotation_y, max_bar_height)
                # Recalculate Y-axis ticks based on the max value needed for annotations
                y_axis_max, y_axis_ticks = _calculate_yaxis_ticks(base_max)
                
                print(f"DEBUG BREAKDOWN YEARLY: max_bar_height={max_bar_height}, max_annotation_y={max_annotation_y}, expected_max_annotation_y={expected_max_annotation_y}, base_max={base_max}, y_axis_max={y_axis_max}, y_axis_ticks={y_axis_ticks}")
                
                # Verify all annotations are within Y-axis range
                for i, ann in enumerate(annotations_list):
                    if ann.get('y', 0) > y_axis_max:
                        print(f"DEBUG BREAKDOWN YEARLY: WARNING - Annotation {i} (year {ann.get('x')}) Y position {ann.get('y')} exceeds Y-axis max {y_axis_max}")
                
                print(f"DEBUG BREAKDOWN YEARLY: Year-level ProductionDataValue: {year_production_values}")
                print(f"DEBUG BREAKDOWN YEARLY: Year totals (sum of bars): {year_totals_dict}")
                print(f"DEBUG BREAKDOWN YEARLY: Max bar height: {max_bar_height}, Max annotation Y: {max_annotation_y}, Y-axis max: {y_axis_max}")
                
                # Update layout with annotations included directly
                fig.update_layout(
                    xaxis_title="",
                    yaxis_title="Production Volume ('000 b/d)",
                    title=None, # title removed
                    xaxis=dict(
                        showgrid=False,  # Remove X-axis grid lines (match original)
                        gridcolor="#e0e0e0", 
                        type="category",  # Treat as categorical to show all years
                        categoryorder="array",
                        categoryarray=years_sorted,  # Order years ascending (2006 to 2024)
                        tickfont=dict(size=10, color="#2c3e50"),
                        titlefont=dict(size=12, color="#2c3e50"),
                        tickangle=0,
                        tickmode='array',
                        tickvals=years_sorted,
                        ticktext=years_sorted,
                        range=[-0.5, len(years_sorted) - 0.5],
                        zeroline=False  # Remove zero line
                    ),
                    yaxis=dict(
                        showgrid=True, 
                        gridcolor="#e0e0e0", 
                        title="Production Volume ('000 b/d)", 
                        range=[0, y_axis_max],
                        tickfont=dict(size=11, color="#2c3e50"),
                        titlefont=dict(size=12, color="#2c3e50"),
                        tickmode='array',
                        tickvals=y_axis_ticks,
                        ticktext=[f"{int(t):,}" for t in y_axis_ticks],
                        tickformat=',.0f'
                    ),
                    showlegend=False,
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    bargap=0.2,  # Add proper spacing between bars (10% gap)
                    bargroupgap=0.0,
                    barmode="stack",
                    margin=dict(l=70, r=30, t=70, b=80),
                    hovermode='closest',
                    annotations=annotations_list  # Add annotations directly to layout
                )
                
                print(f"DEBUG BREAKDOWN YEARLY: Added {len(annotations_list)} ProductionDataValue annotations to layout")
                print(f"DEBUG BREAKDOWN YEARLY: Final figure has {len(fig.layout.annotations) if fig.layout.annotations else 0} total annotations")
                if fig.layout.annotations:
                    print(f"DEBUG BREAKDOWN YEARLY: First annotation sample: {fig.layout.annotations[0] if len(fig.layout.annotations) > 0 else 'N/A'}")
                
                print(f"DEBUG BREAKDOWN YEARLY: Chart layout updated, returning figure")
                return fig, title_text
            else:
                # Monthly view: simplified and robust stacked bars
                print(f"DEBUG BREAKDOWN MONTHLY: production_years={production_years}, country={country}")
                
                # Default country/year handling
                if not country:
                    country = ["Russia"] if "Russia" in COUNTRIES else COUNTRIES[:1]
                if isinstance(country, str):
                    country = [country]
                
                # Resolve year selection - expand "(All)" to all available years
                resolved_years = _resolve_years_selection(production_years)
                if resolved_years:
                    selected_years = [str(y) for y in resolved_years]
                else:
                    # default to latest two years if available, else 2024/2025
                    if not BAR_LONG_MONTHLY.empty and "year" in BAR_LONG_MONTHLY.columns:
                        latest_years = sorted(BAR_LONG_MONTHLY["year"].astype(int).unique(), reverse=True)[:2]
                        selected_years = [str(y) for y in latest_years] if latest_years else ["2024", "2025"]
                    else:
                        selected_years = ["2024", "2025"]
                
                print(f"DEBUG BREAKDOWN MONTHLY: Selected years={selected_years}, countries={country}")
                
                if BAR_LONG_MONTHLY.empty or "year" not in BAR_LONG_MONTHLY.columns:
                    fig = go.Figure()
                    fig.add_annotation(text="No monthly data available.", xref="paper", yref="paper",
                                       x=0.5, y=0.5, showarrow=False,
                                       font=dict(size=14, color='#7f8c8d'))
                    fig.update_layout(height=360, plot_bgcolor='white', paper_bgcolor='white')
                    return fig, title_text
                
                df = BAR_LONG_MONTHLY.copy()
                df["year"] = df["year"].astype(str)
                df = df[df["year"].isin(selected_years)]
                df = df[df["Country"].isin(country)]
                print(f"DEBUG BREAKDOWN MONTHLY: After country/year filter len={len(df)}")
                
                if df.empty:
                    # fallback to all countries for selected years
                    df = BAR_LONG_MONTHLY.copy()
                    df["year"] = df["year"].astype(str)
                    df = df[df["year"].isin(selected_years)]
                    print(f"DEBUG BREAKDOWN MONTHLY: Fallback all countries len={len(df)}")
                
                if df.empty:
                    fig = go.Figure()
                    fig.add_annotation(text="No monthly data available for selected filters.",
                                       xref="paper", yref="paper",
                                       x=0.5, y=0.5, showarrow=False,
                                       font=dict(size=14, color='#7f8c8d'))
                    fig.update_layout(height=360, plot_bgcolor='white', paper_bgcolor='white')
                    return fig, title_text
                
                month_names = ["January", "February", "March", "April", "May", "June",
                               "July", "August", "September", "October", "November", "December"]
                month_map = {i+1: name for i, name in enumerate(month_names)}
                if "month" not in df.columns:
                    df["month"] = df["month_idx"].map(month_map)
                else:
                    # normalize month text to standard names if numeric
                    df["month"] = pd.to_numeric(df["month"], errors="ignore")
                    df["month"] = df["month"].map(month_map).fillna(df["month"])
                
                # Aggregate by year, month, Stream (summing across countries)
                agg = (
                    df.groupby(["year", "month", "Stream"], as_index=False)["value"]
                    .sum()
                )
                
                # Add Country information for hover template
                # Get unique countries from the filtered data or use the country filter variable
                if "Country" in df.columns:
                    # Get unique countries per year/month/Stream combination
                    country_info = df.groupby(["year", "month", "Stream"])["Country"].apply(
                        lambda x: ", ".join(sorted(x.unique()))
                    ).reset_index(name="Country")
                    agg = agg.merge(country_info, on=["year", "month", "Stream"], how="left")
                else:
                    # Fallback: use country filter variable
                    if country and len(country) > 0:
                        agg["Country"] = ", ".join(sorted(country)) if len(country) > 1 else country[0]
                    else:
                        agg["Country"] = ""
                
                print(f"DEBUG BREAKDOWN MONTHLY: Aggregated rows={len(agg)}, years={agg['year'].unique().tolist() if not agg.empty else []}")
                
                # Filter out months with no data (value = 0 or missing)
                # Only keep months where at least one stream has data (value > 0)
                if not agg.empty:
                    # Group by year and month to find months with data
                    months_with_data = agg[agg["value"] > 0].groupby(["year", "month"]).size().reset_index(name="count")
                    # Keep only year-month combinations that have data
                    agg = agg.merge(months_with_data[["year", "month"]], on=["year", "month"], how="inner")
                    print(f"DEBUG BREAKDOWN MONTHLY: After filtering months with no data, rows={len(agg)}")
                
                # Get available streams from the data
                available_monthly_streams = sorted(agg["Stream"].dropna().unique().tolist()) if not agg.empty else []
                
                # For monthly view: Always show all streams in the chart
                # Use visual styling (opacity) to highlight selected stream and dim others
                # Don't filter the data - keep all streams visible
                selected_stream_for_highlight = None
                if profiled and len(profiled) > 0:
                    # Check if all available streams are selected (default mode)
                    profiled_set = set(profiled)
                    available_set = set(available_monthly_streams)
                    
                    # If all streams are selected, no highlighting needed (all at full opacity)
                    if profiled_set == available_set and len(available_set) > 0:
                        print(f"DEBUG BREAKDOWN MONTHLY: All streams selected (default mode), showing all streams at full opacity")
                        selected_stream_for_highlight = None
                    elif len(profiled) == 1:
                        # Single stream selected: highlight this stream, dim others
                        selected_stream_for_highlight = str(profiled[0]).strip()
                        print(f"DEBUG BREAKDOWN MONTHLY: Single stream selected ({selected_stream_for_highlight}), will highlight this stream and dim others")
                    else:
                        # Multiple streams selected (shouldn't happen, but handle it)
                        print(f"DEBUG BREAKDOWN MONTHLY: Multiple streams selected ({len(profiled)}), showing all at full opacity")
                        selected_stream_for_highlight = None
                else:
                    # If no stream selected, show all streams at full opacity (default mode)
                    print(f"DEBUG BREAKDOWN MONTHLY: No stream selected, showing all streams at full opacity (default mode)")
                    selected_stream_for_highlight = None
                
                # If no rows or all values are zero, show a friendly message
                if agg.empty or (agg["value"].fillna(0).sum() <= 0):
                    print(f"DEBUG BREAKDOWN MONTHLY: No usable data (rows={len(agg)}, total={agg['value'].fillna(0).sum() if not agg.empty else 0})")
                    fig = go.Figure()
                    fig.add_annotation(text="No monthly data available for selected filters.",
                                       xref="paper", yref="paper",
                                       x=0.5, y=0.5, showarrow=False,
                                       font=dict(size=14, color='#7f8c8d'))
                    fig.update_layout(height=360, plot_bgcolor='white', paper_bgcolor='white')
                    return fig, title_text
                
                # Stream color map
                color_map = get_stream_color_map("monthly")
                
                # Ensure data is sorted by year and month (in correct month order)
                # This ensures months appear in the right order and only months with data are shown
                if not agg.empty:
                    # Convert month names to numeric for proper sorting
                    month_to_num = {name: idx+1 for idx, name in enumerate(month_names)}
                    agg["month_num"] = agg["month"].map(month_to_num)
                    agg = agg.sort_values(["year", "month_num"]).drop(columns=["month_num"])
                    
                    # Convert month to categorical with only the months that have data
                    # This ensures Plotly only shows months with data for each facet
                    # Get unique months from data, sorted in month order
                    available_months = agg["month"].unique().tolist()
                    months_ordered = [m for m in month_names if m in available_months]
                    agg["month"] = pd.Categorical(agg["month"], categories=months_ordered, ordered=True)
                    print(f"DEBUG BREAKDOWN MONTHLY: Data sorted by year and month, month column converted to categorical with {len(months_ordered)} months")
                
                # Get unique years - each will be a separate subplot
                unique_years = sorted(agg["year"].unique().tolist()) if not agg.empty else []
                
                if not unique_years:
                    # No years, return empty chart
                    fig = go.Figure()
                    fig.add_annotation(text="No monthly data available.", xref="paper", yref="paper",
                                       x=0.5, y=0.5, showarrow=False,
                                       font=dict(size=14, color='#7f8c8d'))
                    fig.update_layout(height=360, plot_bgcolor='white', paper_bgcolor='white')
                    return fig, title_text
                
                # Create subplots - one column per year
                fig = make_subplots(
                    rows=1,
                    cols=len(unique_years),
                    subplot_titles=unique_years,
                    shared_yaxes=True,
                    horizontal_spacing=0.05
                )
                
                # Add traces for each year separately
                for year_idx, year_val in enumerate(unique_years):
                    year_data = agg[agg["year"] == year_val].copy()
                    
                    if year_data.empty:
                        continue
                    
                    # Get months with data for this year, in correct order
                    year_months = year_data["month"].unique().tolist()
                    year_months_ordered = [m for m in month_names if m in year_months]
                    
                    # Get unique streams for this year
                    year_streams = sorted(year_data["Stream"].unique().tolist())
                    
                    # Add a trace for each stream
                    for stream in year_streams:
                        stream_data = year_data[year_data["Stream"] == stream].copy()
                        
                        # Ensure months are in correct order
                        stream_data["month_cat"] = pd.Categorical(
                            stream_data["month"], 
                            categories=year_months_ordered, 
                            ordered=True
                        )
                        stream_data = stream_data.sort_values("month_cat")
                        
                        # Get color for this stream
                        stream_color = color_map.get(stream) if color_map else None
                        if not stream_color:
                            stream_color = get_stream_color(stream, year_streams, tab="monthly")
                        
                        # Add bar trace for this stream
                        fig.add_trace(
                            go.Bar(
                                x=stream_data["month"],
                                y=stream_data["value"],
                                name=stream,
                                marker_color=stream_color,
                                legendgroup=stream,
                                showlegend=False,  # Hide legend since we have custom legend
                                hovertemplate=(
                                    "<b>Month:</b> %{x}<br>"
                                    "<b>Stream:</b> " + stream + "<br>"
                                    "<b>Production Volume:</b> %{y:,.0f} ('000 b/d)<extra></extra>"
                                )
                            ),
                            row=1,
                            col=year_idx + 1
                        )
                
                # Calculate max value across all data for Y-axis scaling
                max_value = agg["value"].max() if not agg.empty and "value" in agg.columns else 0
                
                # Calculate Y-axis ticks (5 evenly spaced values from 0 to max)
                y_axis_max, y_axis_ticks = _calculate_yaxis_ticks(max_value)
                
                # Calculate bar width to ensure all bars are equal size across all years
                # Find the maximum number of months across all years
                max_months = 0
                for year_val in unique_years:
                    year_data = agg[agg["year"] == year_val]
                    if not year_data.empty:
                        num_months_for_year = len(year_data["month"].unique())
                        max_months = max(max_months, num_months_for_year)
                
                # If no data, default to 12
                if max_months == 0:
                    max_months = 12
                
                # Calculate bar width as a fraction that will make all bars appear equal
                # Use a consistent fraction (e.g., 0.75) but base it on max_months
                # This ensures bars in years with fewer months don't appear wider
                # The bargap will create consistent spacing
                monthly_bar_width = 0.75  # 75% of category width - consistent across all years
                monthly_bargap = 0.2  # Keep same gap as yearly for consistency
                
                print(f"DEBUG BREAKDOWN MONTHLY: Max months across all years: {max_months}, bar width: {monthly_bar_width}")
                
                # Update layout
                fig.update_layout(
                    # title removed
                    showlegend=False,
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    bargap=monthly_bargap,  # Same gap as yearly chart
                    bargroupgap=0.0,
                    barmode="stack",
                    hovermode="closest",
                    margin=dict(l=60, r=10, t=80, b=120),
                    height=520
                )
                
                # Update subplot title annotations to match styling
                if fig.layout.annotations:
                    for annotation in fig.layout.annotations:
                        if hasattr(annotation, 'text') and annotation.text in [str(y) for y in unique_years]:
                            annotation.font = dict(size=14, color="#2c3e50", family="Arial, sans-serif")
                
                # Calculate domains for each subplot so that each month gets equal visual space
                # This ensures bars appear the same size across all years
                total_months = 0
                year_month_counts = {}
                for year_val in unique_years:
                    year_data = agg[agg["year"] == year_val]
                    if not year_data.empty:
                        num_months = len(year_data["month"].unique())
                        year_month_counts[year_val] = num_months
                        total_months += num_months
                    else:
                        year_month_counts[year_val] = 0
                
                # Calculate domain start positions for each subplot
                # Each subplot gets domain width proportional to its number of months
                domain_start = 0
                domain_width_per_month = 1.0 / total_months if total_months > 0 else 1.0 / len(unique_years)
                
                # Update x-axis for each subplot to show only months with data and make labels vertical
                for year_idx, year_val in enumerate(unique_years):
                    year_data = agg[agg["year"] == year_val]
                    year_months_ordered = []
                    if not year_data.empty:
                        year_months = year_data["month"].unique().tolist()
                        # Sort months according to month_names order
                        year_months_ordered = [m for m in month_names if m in year_months]
                        print(f"DEBUG BREAKDOWN MONTHLY: Year {year_val} has months: {year_months_ordered}")
                    
                    # Calculate domain for this subplot
                    num_months_for_year = year_month_counts.get(year_val, 0)
                    if num_months_for_year > 0:
                        subplot_domain_width = num_months_for_year * domain_width_per_month
                        domain_end = domain_start + subplot_domain_width
                    else:
                        # Fallback: equal width for all subplots
                        subplot_domain_width = 1.0 / len(unique_years)
                        domain_end = domain_start + subplot_domain_width
                    
                    # Update x-axis for this specific subplot
                    if year_months_ordered:
                        fig.update_xaxes(
                            tickangle=-90,  # Vertical labels
                            type="category",
                            categoryorder="array",
                            categoryarray=year_months_ordered,  # Only months with data for this year
                            tickfont=dict(size=10, color="#2c3e50"),
                            titlefont=dict(size=12, color="#2c3e50"),
                            domain=[domain_start, domain_end],  # Set domain proportional to number of months
                            row=1,
                            col=year_idx + 1
                        )
                    else:
                        fig.update_xaxes(
                            tickangle=-90,
                            type="category",
                            tickfont=dict(size=10, color="#2c3e50"),
                            titlefont=dict(size=12, color="#2c3e50"),
                            domain=[domain_start, domain_end],
                            row=1,
                            col=year_idx + 1
                        )
                    
                    # Update domain start for next subplot
                    domain_start = domain_end
                
                # Update y-axis
                fig.update_yaxes(
                    title_text="Production Volume ('000 b/d)",
                    tickfont=dict(size=10, color="#2c3e50"),
                    titlefont=dict(size=12, color="#2c3e50"),
                    row=1,
                    col=1
                )
                
                # Set explicit bar width and update hover template with Country info
                # With make_subplots, traces are added in order: all streams for year1, then all streams for year2, etc.
                trace_idx = 0
                for year_idx, year_val in enumerate(unique_years):
                    year_data = agg[agg["year"] == year_val]
                    if year_data.empty:
                        continue
                    
                    year_streams = sorted(year_data["Stream"].unique().tolist())
                    
                    # Process traces for this year
                    for stream in year_streams:
                        if trace_idx >= len(fig.data):
                            break
                        
                        trace = fig.data[trace_idx]
                        trace.width = monthly_bar_width
                        
                        # Get the Stream name for this trace
                        stream_name = trace.name
                        
                        # Build customdata array matching this trace's data points
                        customdata_list = []
                        if len(trace.x) > 0:
                            for month_val in trace.x:
                                # Match by Stream, month, and year
                                matching_rows = year_data[
                                    (year_data["Stream"] == stream_name) & 
                                    (year_data["month"] == month_val)
                                ]
                                
                                if not matching_rows.empty and "Country" in matching_rows.columns:
                                    country_val = matching_rows.iloc[0]["Country"]
                                else:
                                    country_val = ""
                                
                                # Add to customdata: [Country, Year]
                                customdata_list.append([country_val, str(year_val)])
                        
                        # Set customdata
                        trace.customdata = customdata_list if customdata_list else None
                        
                        # Create custom hover template
                        trace.hovertemplate = (
                            "<b>Month of Date:</b> %{x}<br>"
                            "<b>Country:</b> %{customdata[0]}<br>"
                            "<b>Stream Name:</b> " + stream_name + "<br>"
                            "<b>Year of Date:</b> " + str(year_val) + "<br>"
                            "<b>Production Volume:</b> %{y:,.0f} ('000 b/d)<extra></extra>"
                        )
                        
                        # Apply highlight/dimmed styling for monthly view
                        try:
                            if selected_stream_for_highlight:
                                if stream_name == selected_stream_for_highlight:
                                    # Selected stream: full opacity (highlighted)
                                    target_opacity = 1.0
                                else:
                                    # Other streams: reduced opacity (dimmed)
                                    target_opacity = 0.3
                            else:
                                # Default mode: all streams at full opacity
                                target_opacity = 1.0
                            
                            # Apply opacity to trace
                            trace.opacity = target_opacity
                            
                            # Also apply to marker if it exists
                            if not hasattr(trace, 'marker') or trace.marker is None:
                                trace.marker = {}
                            if isinstance(trace.marker, dict):
                                trace.marker['opacity'] = target_opacity
                            else:
                                # Plotly marker object
                                try:
                                    trace.marker.opacity = target_opacity
                                except:
                                    # Fallback: create new marker dict
                                    trace.marker = {'opacity': target_opacity}
                        except Exception as e:
                            print(f"Error applying opacity to trace {stream_name}: {e}")
                            # Continue without opacity modification
                            pass
                        
                        trace_idx += 1
                
                # Update Y-axis for all subplots (yaxis, yaxis2, yaxis3, etc.) with 5 evenly spaced ticks
                for i in range(len(unique_years)):
                    yaxis_key = f"yaxis{i+1}" if i > 0 else "yaxis"
                    if yaxis_key in fig.layout:
                        fig.layout[yaxis_key].update(
                            range=[0, y_axis_max],
                            tickmode='array',
                            tickvals=y_axis_ticks,
                            ticktext=[f"{int(t):,}" for t in y_axis_ticks],
                            tickformat=',.0f',
                            showgrid=True,  # Keep Y-axis grid lines
                            gridcolor="#e0e0e0"
                        )
                
                # Remove "Month" label text and X-axis grid lines from each subplot (match original)
                # Update xaxis for each facet (xaxis, xaxis2, xaxis3, etc.)
                for i in range(len(unique_years)):
                    xaxis_key = f"xaxis{i+1}" if i > 0 else "xaxis"
                    if xaxis_key in fig.layout:
                        fig.layout[xaxis_key].update(
                            title_text="",  # Remove "Month" label text, but keep month tick labels visible
                            showgrid=False,  # Remove X-axis grid lines (match original)
                            gridwidth=0,
                            zeroline=False  # Remove zero line
                        )
                
                if not fig.data:
                    fig = go.Figure()
                    fig.add_annotation(text="No monthly data available for selected filters.",
                                       xref="paper", yref="paper",
                                       x=0.5, y=0.5, showarrow=False,
                                       font=dict(size=14, color='#7f8c8d'))
                    fig.update_layout(height=360, plot_bgcolor='white', paper_bgcolor='white')
                
                return fig, title_text
        except Exception as e:
            print(f"Error in update_breakdown: {e}")
            import traceback
            traceback.print_exc()
            # Return empty figure on error
            fig = go.Figure()
            err_text = f"Error loading chart data: {e}"
            fig.add_annotation(
                text=err_text,
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color='#7f8c8d')
            )
            fig.update_layout(
                height=360,
                plot_bgcolor='white',
                paper_bgcolor='white',
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=False)
            )
            return fig, "Production Breakdown"
    
    @dash_app.callback(
        Output("table-title", "children"),
        Input("crude-main-tabs", "value"),
        prevent_initial_call=False
    )
    def update_table_title(tab):
        """Update table title based on selected tab"""
        if tab == "yearly":
            return "Global Crude Production Breakdown"
        else:
            return "Crude Production Breakdown"
    
    @dash_app.callback(
        [Output("crude-table", "data"),
         Output("crude-table", "columns")],
        [Input("filter-stream", "value"),
         Input("filter-ci", "value"),
         Input("filter-api", "value"),
         Input("filter-sulfur", "value"),
         Input("crude-year-dropdown", "value"),
         Input("crude-year-month-dropdown", "value"),
         Input("crude-country-dropdown", "value"),
         Input("crude-main-tabs", "value"),
         Input("profiled-streams", "value"),
         Input("selected-country-map-store", "data"),
         Input("current-submenu", "data")],
        [State("profiled-streams", "options")],
        prevent_initial_call=False
    )
    def filter_table(stream, ci, api, sulfur, year, year_month, country, tab, profiled_streams, selected_country_map, current_submenu, profiled_streams_options):
        """Filter and update data table - only loads data when page is active"""
        # Only load data if page is active
        if current_submenu != 'crude-overview':
            return [], []
        
        # Ensure data is loaded
        _ensure_data_loaded()
        
        # Map selection overrides dropdown if present
        if selected_country_map:
            country = [selected_country_map]
        else:
            country = _resolve_countries_selection(country)
        
        # Set defaults if None
        if tab is None:
            tab = "yearly"
        
        if tab == "yearly":
            df = TABLE_DF_YEARLY.copy()
        else:
            df = TABLE_DF_MONTHLY.copy()
        
        if df.empty:
            return [], []
            
        # Unify crude name column to 'Crude' for internal logic
        if "CrudeOil" in df.columns and "Crude" not in df.columns:
            df = df.rename(columns={"CrudeOil": "Crude"})
        elif "Crude" not in df.columns and df.index.name in ["Crude", "CrudeOil"]:
            df = df.reset_index().rename(columns={df.index.name: "Crude"})
            
        # 1. Profiled Stream Filter (Checklist on the right)
        # For Yearly tab, we allow filtering by a single selected stream from the checklist
        # unless a text search is active (text search takes priority)
        applied_checklist_filter = False
        if tab == "yearly" and not (stream and str(stream).strip()):
            if profiled_streams and len(profiled_streams) == 1:
                selected_stream = profiled_streams[0]
                # Check if options are initialized to avoid filtering on initial load default state
                available_streams = [opt.get("value") for opt in (profiled_streams_options or []) if opt.get("value")]
                if available_streams and len(available_streams) > 1 and len(profiled_streams) < len(available_streams):
                    if "Crude" in df.columns:
                        df = df[df["Crude"] == selected_stream]
                        applied_checklist_filter = True

        # 2. Text Search Filter (Stream Name box)
        if stream and str(stream).strip():
            stream_val = str(stream).strip()
            if "Crude" in df.columns:
                try:
                    df = df[df["Crude"].astype(str).str.contains(re.escape(stream_val), case=False, na=False)]
                except Exception as e:
                    print(f"Error in stream search: {e}")

        # 3. Metadata Filters (CI, API, Sulfur - mostly for monthly)
        def sanitize(values):
            if not values: return []
            return [v for v in values if v and v not in ("(All)", "ALL")]
        
        # Only apply these specifically if available in df
        ci_vals = sanitize(ci)
        if ci_vals and "CI Rank" in df.columns:
            df = df[df["CI Rank"].isin(ci_vals)]
            
        api_vals = sanitize(api)
        if api_vals and "API" in df.columns:
            df = df[df["API"].apply(lambda v: classify_api_value(v) in api_vals)]
            
        sulfur_vals = sanitize(sulfur)
        if sulfur_vals and "Sulfur" in df.columns:
            df = df[df["Sulfur"].apply(lambda v: classify_sulfur_value(v) in sulfur_vals)]


        # 4. Country Filter
        # Map selection applies to both tabs
        # Dropdown country filter only applies to monthly tab (Yearly is "Global" by default from dropdown)
        if selected_country_map:
            # Map selection overrides everything - apply to both tabs
            if "Country" in df.columns:
                df = df[df["Country"] == selected_country_map]
        elif tab == "monthly" and country and country != ['ALL']:
            # Dropdown country filter only for monthly when no map selection
            resolved_countries = _resolve_countries_selection(country)
            if "Country" in df.columns:
                df = df[df["Country"].isin(resolved_countries)]
        
        # Filter by CI Rank, API, Sulfur (only for monthly)
        if tab == "monthly":
            if ci and "CI Rank" in df.columns:
                df = df[df["CI Rank"].isin(ci)]
            if api and "API" in df.columns:
                df = df[df["API"].apply(lambda v: classify_api_value(v) in api)]
            if sulfur and "Sulfur" in df.columns:
                df = df[df["Sulfur"].apply(lambda v: classify_sulfur_value(v) in sulfur)]
        
        if tab == "yearly":
            display_metadata_cols = ["Crude"]
            year_cols = [c for c in df.columns if c not in ["Crude", "CI Rank", "API", "Sulfur"] and str(c).isdigit()]
            year_cols = sorted([int(c) for c in year_cols], reverse=True)
            year_cols = [str(c) for c in year_cols]
            
            # Filter to only show selected years if specified
            if year and isinstance(year, (list, tuple, set)):
                year_strs = [str(y) for y in year if str(y) in year_cols]
                if year_strs:
                    year_cols = year_strs
            
            # Map back to 'CrudeOil' for display if that's what's expected
            # Actually, let's just use 'CrudeOil' as the ID for the column to be consistent with layout
            df = df.rename(columns={"Crude": "CrudeOil"})
            display_cols = ["CrudeOil"] + year_cols
            columns = []
            for c in display_cols:
                # Use nested header format [top, bottom] even for yearly to avoid DataTable rendering glitches
                # when switching from monthly (which has 2 levels)
                col_name = "CrudeOil" if c == "CrudeOil" else str(c)
                columns.append({
                    "name": ["", col_name],
                    "id": str(c),
                    "type": "text",
                    "presentation": "markdown"
                })
            
            df_display = df[display_cols].copy()
            df_display = df_display.sort_values("CrudeOil", key=lambda s: s.astype(str).str.lower())
            
            if 'Year of YearReported' in df.columns:
                all_years_in_data = df['Year of YearReported'].dropna().unique().tolist()
            else:
                all_years_in_data = year_cols[:]
                
            for y in all_years_in_data:
                y_str = str(int(y))
                if y_str not in df_display.columns:
                    df_display[y_str] = ""
                    
            df_display = df_display.reset_index(drop=True)
            records = df_display.to_dict("records")
            
            # ADD GRAND TOTAL ROW FOR YEARLY VIEW
            if records:
                total_record = {"CrudeOil": "**Grand Total**"}
                for col in year_cols:
                    if col in df_display.columns:
                        total_val = pd.to_numeric(df_display[col], errors='coerce').sum()
                        total_record[col] = total_val
                records.append(total_record)
                
            link_col = "profile_url" if "profile_url" in df.columns else None
            link_series = None
            if link_col and link_col in df.columns:
                link_series = df[link_col].reset_index(drop=True)
            
            year_columns_set = set(year_cols + [str(int(y)) for y in all_years_in_data])
            
            for idx, record in enumerate(records):
                for year_col in year_columns_set:
                    value = record.get(year_col, "")
                    if value is None or str(value).strip() == "":
                        record[year_col] = ""
                        continue
                    try:
                        numeric_value = float(str(value).replace(",", ""))
                        record[year_col] = f"{numeric_value:,.0f}"
                    except (ValueError, TypeError):
                        record[year_col] = str(value)
                link = None
                if link_series is not None and idx < len(link_series):
                    link_value = link_series.iloc[idx]
                    if pd.notna(link_value):
                        link = str(link_value).strip()
                if link:
                    record["profile_url"] = link  # Store for row navigation
                    for col in display_cols:
                        record[col] = format_with_link(record.get(col, ""), link)
                else:
                    record["CrudeOil"] = format_with_link(record.get("CrudeOil", ""), link)
            
            return records, columns
        else:
            # Monthly view: Create nested headers with Year -> Month structure
            display_metadata_cols = ["Crude", "CI Rank", "API", "Sulfur"]
            
            # Always show all years/months available in the monthly dataset
            all_years = sorted([int(y) for y in YEAR_TO_MONTH_COLS.keys() if y.isdigit()], reverse=True)
            months_to_show = None
            
            # Build columns with nested structure (Year -> Month)
            # Similar to country_profile.py - first column is Crude with empty top level
            columns = [{'name': ['', 'Crude'], 'id': 'Crude', 'type': 'text', 'presentation': 'markdown'}]
            
            # Add other metadata columns with empty top level
            for col in display_metadata_cols:
                if col != 'Crude' and col in df.columns:
                    columns.append({'name': ['', col], 'id': col, 'type': 'text', 'presentation': 'markdown'})
            
            # Build table data structure
            table_data = []
            crudes = sorted(df['Crude'].dropna().unique().tolist()) if 'Crude' in df.columns else []
            
            # Build columns with nested structure: Year -> Month (same pattern as country_profile.py)
            for year in all_years:
                year_str = str(year)
                if year_str in YEAR_TO_MONTH_COLS:
                    month_entries = YEAR_TO_MONTH_COLS[year_str]
                    for entry in reversed(month_entries):
                        col_name = entry.get("column")
                        month_name = entry.get("month")
                        if not col_name or col_name not in df.columns:
                            continue
                        if months_to_show and month_name not in months_to_show:
                            continue
                        clean_month = str(month_name or "").strip()
                        if '.' in clean_month:
                            clean_month = clean_month.split('.')[0]
                        clean_month = clean_month.split()[0] if clean_month else clean_month
                        columns.append({
                            'name': [year_str, clean_month],
                            'id': col_name,
                            'type': 'text',
                            'presentation': 'markdown'
                        })

            # Build table data rows
            for crude in crudes:
                row = {}
                # Add metadata columns
                crude_row = df[df['Crude'] == crude].iloc[0] if len(df[df['Crude'] == crude]) > 0 else None
                if crude_row is not None:
                    link = None
                    if "profile_url" in df.columns and pd.notna(crude_row.get("profile_url")):
                        link = crude_row.get("profile_url")
                    elif "BSP link" in df.columns and pd.notna(crude_row.get("BSP link")):
                        link = crude_row.get("BSP link")
                    
                    if link:
                        row["profile_url"] = link  # Store for row navigation
                        
                    for col in display_metadata_cols:
                        if col in df.columns:
                            label = crude_row[col] if pd.notna(crude_row[col]) else ''
                            row[col] = format_with_link(label, link)
                    
                    # Add year-month values
                    for year in all_years:
                        year_str = str(year)
                        if year_str in YEAR_TO_MONTH_COLS:
                            month_entries = YEAR_TO_MONTH_COLS[year_str]
                            for entry in reversed(month_entries):
                                col_name = entry.get("column")
                                month_name = entry.get("month")
                                if not col_name or col_name not in df.columns:
                                    continue
                                if months_to_show and month_name not in months_to_show:
                                    continue
                                
                                value = crude_row[col_name]
                                if pd.notna(value) and value != '':
                                    try:
                                        num_value = pd.to_numeric(str(value).replace(',', ''), errors='coerce')
                                        if pd.notna(num_value):
                                            formatted = f"{num_value:,.0f}"
                                        else:
                                            formatted = str(value) if value else ''
                                    except Exception:
                                        formatted = str(value) if value else ''
                                else:
                                    formatted = ''
                                row[col_name] = format_with_link(formatted, link)
                else:
                    # If no data for this crude, create empty row
                    for col in display_metadata_cols:
                        row[col] = '' if col != "Crude" else ''
                    for year in all_years:
                        year_str = str(year)
                        if year_str in YEAR_TO_MONTH_COLS:
                            month_entries = YEAR_TO_MONTH_COLS[year_str]
                            for entry in reversed(month_entries):
                                col_name = entry.get("column")
                                month_name = entry.get("month")
                                if months_to_show and month_name not in months_to_show:
                                    continue
                                if col_name:
                                    row[col_name] = ''
                
                table_data.append(row)
            
            # ADD GRAND TOTAL ROW FOR MONTHLY VIEW
            if table_data:
                total_row = {"Crude": "**Grand Total**"}
                # Metadata columns empty for total row
                for col in display_metadata_cols:
                    if col != "Crude":
                        total_row[col] = ""
                
                # Sum the data columns
                for year in all_years:
                    year_str = str(year)
                    if year_str in YEAR_TO_MONTH_COLS:
                        for entry in reversed(YEAR_TO_MONTH_COLS[year_str]):
                            col_name = entry.get("column")
                            if col_name and col_name in df.columns:
                                total_val = df[col_name].sum()
                                if pd.notna(total_val):
                                    total_row[col_name] = f"**{total_val:,.0f}**"
                                else:
                                    total_row[col_name] = "0"
                table_data.append(total_row)
            
            return table_data, columns



    @callback(
        Output("download-map-csv", "data"),
        Input("btn-export-map-csv", "n_clicks"),
        State("crude-main-tabs", "value"),
        prevent_initial_call=True
    )
    def export_map_data_to_csv(n_clicks, tab):
        if n_clicks is None or n_clicks <= 0:
            return no_update
            
        try:
            # Default to yearly map if tab is None
            if tab is None:
                tab = "yearly"
                
            if tab == "yearly":
                print("DEBUG: Exporting YEARLY map data (raw_export=True)")
                df = load_yearly_map_from_db(raw_export=True)
                filename = "world_crude_production_yearly.csv"
            else:
                # monthly
                print("DEBUG: Exporting MONTHLY map data (raw_export=True)")
                df = load_monthly_map_from_db(raw_export=True)
                filename = "world_crude_production_monthly.csv"
            
            if df.empty:
                print("DEBUG: No data to export for map")
                return no_update
                
            return dcc.send_data_frame(df.to_csv, filename, index=False)
            
        except Exception as e:
            print(f"Error exporting map data: {e}")
            import traceback
            traceback.print_exc()
            return no_update

    # ----------------------------------------------------------------------
    # Export Callbacks for Chart and Table
    # ----------------------------------------------------------------------
    @dash_app.callback(
        Output("download-chart-csv", "data"),
        Input("btn-export-chart-csv", "n_clicks"),
        [State("crude-country-dropdown", "value"),
         State("production-year-dropdown", "value"),
         State("profiled-streams", "value"),
         State("crude-main-tabs", "value")],
        prevent_initial_call=True
    )
    def export_chart_data(n_clicks, country, production_years, profiled, tab):
        print(f"DEBUG EXPORT CHART: Triggered. n_clicks={n_clicks}, tab={tab}")
        if n_clicks is None or n_clicks <= 0:
            return no_update
            
        try:
            _ensure_data_loaded()
            print("DEBUG EXPORT CHART: Data loaded.")
            
            country = _resolve_countries_selection(country)
            print(f"DEBUG EXPORT CHART: Resolved country={country}")
            
            if tab is None:
                tab = "yearly"
                
            df_export = pd.DataFrame()
            filename = "crude_production_breakdown.csv"
            
            if tab == "yearly":
                df = BAR_DF_YEARLY.copy()
                print(f"DEBUG EXPORT CHART: Yearly mode. BAR_DF_YEARLY empty? {df.empty}")
                if not df.empty:
                    # Filter by country
                    if country:
                        if "Country" in df.columns:
                            df = df[df["Country"].isin(country)]
                    
                    # Filter by Profiled Streams 
                    if profiled and len(profiled) > 0:
                        if "CrudeOil" in df.columns:
                            df = df[df["CrudeOil"].isin(profiled)]
                    
                    df_export = df
                    filename = "crude_production_breakdown_yearly.csv"
            else:
                # Monthly
                df = BAR_DF_MONTHLY.copy()
                print(f"DEBUG EXPORT CHART: Monthly mode. BAR_DF_MONTHLY empty? {df.empty}, production_years={production_years}")
                if not df.empty:
                    # Filter by country
                    if country:
                        if "Country" in df.columns:
                            df = df[df["Country"].isin(country)]
                    
                    # Filter by Year
                    selected_years = _resolve_years_selection(production_years)
                    print(f"DEBUG EXPORT CHART: Selected years={selected_years}")
                    if not selected_years:
                        if PRODUCTION_YEARS:
                             selected_years = [int(PRODUCTION_YEARS[-1])]
                        else:
                             selected_years = [2024]
                    
                    if "Year of Date" in df.columns:
                        df = df[pd.to_numeric(df["Year of Date"], errors='coerce').astype("Int64").isin(selected_years)]
                    
                    df_export = df
                    filename = "crude_production_breakdown_monthly.csv"
                    
                    # Ensure specific headers order if possible for consistency
                    desired_order = ["Year of Date", "Month of Date", "Stream Name", "Country", "Value"]
                    existing_cols = [c for c in desired_order if c in df_export.columns]
                    if len(existing_cols) == len(desired_order):
                        df_export = df_export[desired_order]
            
            print(f"DEBUG EXPORT CHART: Exporting {len(df_export)} rows to {filename}")
            if df_export.empty:
                print("DEBUG EXPORT CHART: No data to export")
                return no_update
                
            return dcc.send_data_frame(df_export.to_csv, filename, index=False)

        except Exception as e:
            print(f"Error exporting chart data: {e}")
            import traceback
            traceback.print_exc()
            return no_update

    @dash_app.callback(
        Output("download-table-csv", "data"),
        Input("btn-export-table-csv", "n_clicks"),
        [State("crude-country-dropdown", "value"),
         State("production-year-dropdown", "value"),
         State("crude-main-tabs", "value"),
         State("filter-stream", "value"),
         State("filter-ci", "value"),
         State("filter-api", "value"),
         State("filter-sulfur", "value")],
        prevent_initial_call=True
    )
    def export_table_data(n_clicks, country, production_years, tab, stream_filter, ci_filter, api_filter, sulfur_filter):
        print(f"DEBUG EXPORT TABLE: Triggered. n_clicks={n_clicks}")
        if n_clicks is None or n_clicks <= 0:
            return no_update
        
        try:
            _ensure_data_loaded()
            
            country = _resolve_countries_selection(country)
            if tab is None:
                tab = "yearly"
            
            df_export = pd.DataFrame()
            filename = "global_crude_production_breakdown.csv"
            
            # Export raw data (flat) matching query headers, filtered by current view
            
            if tab == "yearly":
                # Use strict raw dataframe
                df = TABLE_RAW_YEARLY.copy()
                if not df.empty:
                    if country:
                        if "Country" in df.columns:
                            df = df[df["Country"].isin(country)]
                            
                    if stream_filter and str(stream_filter).strip():
                        val = str(stream_filter).strip()
                        # Yearly query alias is "CrudeOil"
                        if "CrudeOil" in df.columns:
                            df = df[df["CrudeOil"].astype(str).str.contains(re.escape(val), case=False, na=False)]
                            
                    df_export = df
                    filename = "global_crude_production_yearly.csv"
            else:
                # Monthly
                df = TABLE_RAW_MONTHLY.copy()
                if not df.empty:
                    # Filter Country using the hidden column we added
                    if country:
                        if "_internal_country" in df.columns:
                            df = df[df["_internal_country"].isin(country)]
                            
                    selected_years = _resolve_years_selection(production_years)
                    if not selected_years:
                         if PRODUCTION_YEARS: selected_years = [int(PRODUCTION_YEARS[-1])]
                         else: selected_years = [2024]
                    
                    if "Year of Date" in df.columns:
                        df = df[pd.to_numeric(df["Year of Date"], errors='coerce').astype("Int64").isin(selected_years)]
                        
                    # Filter Stream Name (Text Match) - alias "Crude"
                    if stream_filter and str(stream_filter).strip():
                        val = str(stream_filter).strip()
                        if "Crude" in df.columns:
                            df = df[df["Crude"].astype(str).str.contains(re.escape(val), case=False, na=False)]
                    
                    # Apply Metadata Filters (CI/API/Sulfur)
                    # "ci_rank", "API", "Sulfur" (checking load_table renames/aliases)
                    # User's query: c.ci_rank, c.api, c.sulfur_pct
                    # load_table rename: "ci_rank" -> "CI Rank", "api" -> "API", "sulfur_pct" -> "Sulfur" is ONLY for the visual table processing
                    # BUT we captured `monthly_raw_export` BEFORE renames!
                    # So `TABLE_RAW_MONTHLY` columns are: "Crude", "ci_rank", "api", "sulfur_pct", "profile_url", "Year of Date", "Month of Date", "Value", "_internal_country"
                    
                    # So filters should use snake_case
                    def sanitize(values):
                        if not values: return []
                        return [v for v in values if v and v not in ("(All)", "ALL")]

                    ci_vals = sanitize(ci_filter)
                    if ci_vals and "ci_rank" in df.columns:
                        df = df[df["ci_rank"].isin(ci_vals)]
                        
                    api_vals = sanitize(api_filter)
                    if api_vals and "api" in df.columns:
                         try:
                             df = df[df["api"].apply(lambda v: classify_api_value(v) in api_vals)]
                         except:
                             pass
                             
                    sulfur_vals = sanitize(sulfur_filter)
                    if sulfur_vals and "sulfur_pct" in df.columns:
                        try:
                            df = df[df["sulfur_pct"].apply(lambda v: classify_sulfur_value(v) in sulfur_vals)]
                        except:
                            pass
                            
                    df_export = df
                    filename = "global_crude_production_monthly.csv"
                    
                    # Drop internal country column
                    if "_internal_country" in df_export.columns:
                        df_export = df_export.drop(columns=["_internal_country"])
                    
                    desired_order = ["Crude", "ci_rank", "api", "sulfur_pct", "profile_url", "Year of Date", "Month of Date", "Value"]
                    existing_cols = [c for c in desired_order if c in df_export.columns]
                    if len(existing_cols) == len(desired_order):
                        df_export = df_export[desired_order]

            if df_export.empty:
                print("DEBUG EXPORT TABLE: No data to export")
                return no_update

            print(f"DEBUG EXPORT TABLE: Exporting {len(df_export)} rows")
            return dcc.send_data_frame(df_export.to_csv, filename, index=False)
        except Exception as e:
            print(f"Error exporting table data: {e}")
            import traceback
            traceback.print_exc()
            return no_update

    dash_app.clientside_callback(
        """
        function(active_cell, data) {
            if (active_cell && data) {
                const row = data[active_cell.row];
                if (row && row.profile_url) {
                    window.open(row.profile_url, '_blank');
                }
            }
            return null;
        }
        """,
        Output("stream-navigation-dummy", "data"),
        Input("crude-table", "active_cell"),
        State("crude-table", "data")
    )

# DASH APP CREATION
# ------------------------------------------------------------------------------
def create_crude_overview_dashboard(dash_app, server, url_base_pathname="/dash/crude-overview/"):
    """Create the Crude Overview dashboard"""
    dash_app.layout = create_layout()
    register_callbacks(dash_app, server)
