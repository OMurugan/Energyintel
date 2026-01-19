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
from core.country_mappings import get_iso_code
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

# ISO code to country name mapping for map clicks
ISO_TO_COUNTRY_MAPPING = {
    "USA": "United States",
    "BRA": "Brazil", 
    "RUS": "Russia",
    "SAU": "Saudi Arabia",
    "IRQ": "Iraq",
    "IRN": "Iran",
    "ARE": "United Arab Emirates",
    "KWT": "Kuwait",
    "VEN": "Venezuela",
    "NGA": "Nigeria",
    "AGO": "Angola",
    "NOR": "Norway",
    "KAZ": "Kazakhstan",
    "CAN": "Canada",
    "CHN": "China",
    "MEX": "Mexico",
    "GBR": "United Kingdom",
    "DZA": "Algeria",
    "LBY": "Libya",
    "OMN": "Oman",
    "QAT": "Qatar",
    "AZE": "Azerbaijan",
    "EGY": "Egypt",
    "MYS": "Malaysia",
    "IDN": "Indonesia",
    "IND": "India",
    "THA": "Thailand",
    "VNM": "Vietnam",
    "ARG": "Argentina",
    "COL": "Colombia",
    "ECU": "Ecuador",
    "TTO": "Trinidad and Tobago",
    "GHA": "Ghana",
    "GAB": "Gabon",
    "GNQ": "Equatorial Guinea",
    "COG": "Congo (Brazzaville)",
    "TCD": "Chad",
    "SDN": "Sudan",
    "SSD": "South Sudan",
    "YEM": "Yemen",
    "SYR": "Syria",
    "TUN": "Tunisia",
    "DNK": "Denmark",
    "AUS": "Australia",
    "PNG": "Papua New Guinea",
    "BRN": "Brunei",
}

def _map_iso_to_country_name(iso_or_name):
    """Map ISO code to full country name, or return the name if it's already a full name."""
    if not iso_or_name:
        return iso_or_name
    
    # If it's already a full country name, return as-is
    if len(str(iso_or_name)) > 3:
        return str(iso_or_name)
    
    # Try to map ISO code to country name
    iso_code = str(iso_or_name).upper()
    return ISO_TO_COUNTRY_MAPPING.get(iso_code, iso_or_name)
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
    """Calculate nice round Y-axis ticks from 0 to max_value.
    
    Args:
        max_value: Maximum value for the Y-axis
    
    Returns:
        Tuple of (y_axis_max, tick_values)
    """
    import math
    if max_value <= 0:
        return 10000, [0, 2500, 5000, 7500, 10000]
    
    # We want roughly 5-7 parts (6-8 ticks)
    # The user specifically requested 6 parts for 12,000 (steps of 2,000)
    target_parts = 6
    raw_step = max_value / target_parts
    
    if raw_step == 0:
        return 100, [0, 25, 50, 75, 100]
    
    magnitude = 10**math.floor(math.log10(raw_step))
    normalized_step = raw_step / magnitude
    
    # Choose a nice step based on standard sets {1, 2, 2.5, 5, 10}
    if normalized_step < 1.5: nice_step = 1
    elif normalized_step < 2.25: nice_step = 2
    elif normalized_step < 3: nice_step = 2.5
    elif normalized_step < 7.5: nice_step = 5
    else: nice_step = 10
    
    actual_step = nice_step * magnitude
    
    # Calculate number of steps to cover max_value
    num_steps = math.ceil(max_value / actual_step)
    
    # Ensure we have at least target_parts if possible (padding)
    if num_steps < target_parts:
        num_steps = target_parts
        
    y_axis_max = actual_step * num_steps
    tick_values = [actual_step * i for i in range(num_steps + 1)]
    
    return y_axis_max, tick_values

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
    # Add Country metadata if available in original bar data (before groupby)
    if "Country" in df.columns:
        country_map = df.drop_duplicates(subset=["Stream"]).set_index("Stream")["Country"]
        table_df["Country"] = table_df["Crude"].map(country_map)
        print(f"DEBUG FALLBACK: Added Country column to monthly table from BAR_LONG_MONTHLY, {len(table_df)} rows")
    else:
        print(f"DEBUG FALLBACK: No Country column found in BAR_LONG_MONTHLY, available columns: {df.columns.tolist()}")
        
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
            # Normalize optional column names
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
                print(f"DEBUG LOAD: yearly_df columns: {yearly_df.columns.tolist()} (rows: {len(yearly_df)})")
            
        # Load monthly table data
        # Load monthly table data from DB
        monthly_query = """
            SELECT     
                a.country AS "Country",
                c.crude_name AS "Crude",
                c.ci_rank,
                c.api,
                c.sulfur_pct,
                l.bsp_link AS profile_url,
                EXTRACT(YEAR FROM a.date) AS "Year of Date",
                TO_CHAR(a.date, 'FMMonth') AS "Month of Date",
                a.value AS "Value"
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
                
                metadata_cols = ["Crude", "Country", "CI Rank", "API", "Sulfur", "profile_url"]
                available_metadata = [col for col in metadata_cols if col in monthly_raw.columns]
                
                if available_metadata:
                    monthly_df = monthly_raw[available_metadata].drop_duplicates(subset=["Crude"]).copy()
                    print(f"DEBUG LOAD: monthly_df columns after metadata: {monthly_df.columns.tolist()} (rows: {len(monthly_df)})")
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
    
    return yearly_df, monthly_df, year_to_month_cols

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
        TABLE_DF_YEARLY, TABLE_DF_MONTHLY, YEAR_TO_MONTH_COLS = load_table()
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
        # Store to track if map selection should filter the table
        dcc.Store(id="table-map-filter-active-store", data=False),
        # Store to track ocean clicks for reset behavior
        dcc.Store(id="ocean-click-trigger", data=None),
        # Store to track selected bar for monthly chart isolation
        dcc.Store(id="selected-bar-store", data=None),
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
                    .tab-content {
                        padding: 0px !important;
                    }
                    .jsx-4017309047.tab-content {
                        display: none !important;
                        padding: 0px !important;
                    }
                    div[class*="jsx-"][class*="tab-content"] {
                        display: none !important;
                        padding: 0px !important;
                    }
                    .dash-spreadsheet.dash-freeze-top, .dash-spreadsheet.dash-virtualized {
                        max-height: 600px !important;
                    }
                    /* Map cursor styles for reset functionality */
                    #crude-map .js-plotly-plot .plotly .modebar {
                        pointer-events: auto;
                    }
                    #crude-map .js-plotly-plot .plotly .main-svg {
                        cursor: default;
                    }
                    /* Show pointer cursor when country is selected (when reset layers are present) */
                    #crude-map[data-country-selected="true"] .js-plotly-plot .plotly .main-svg {
                        cursor: pointer;
                    }
                    /* Ensure country hover shows pointer */
                    #crude-map .js-plotly-plot .plotly .main-svg .geo,
                    #crude-map .js-plotly-plot .plotly .main-svg .mapboxgl-map {
                        cursor: pointer;
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
            content_style={"display": "none"},
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
            style={"marginBottom": "0px", "paddingBottom": "0px", "display": "flex", "justifyContent": "center"}
        ),
        html.Br(),
        html.Div([
            html.H4(
                "World Crude Production*", 
                style={"color":"#d35400", "textAlign":"center", "marginTop":"0px", "marginBottom": "0px", "flexGrow": 1}
            ),
            html.Div([
                html.Button(
                    'Export to CSV',
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
        ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'position': 'relative', 'width': '100%', 'marginTop': '0px', 'paddingTop': '0px'}),
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
                                'displaylogo': False,
                                'displayModeBar': True,
                                'scrollZoom': True,  # Allow scroll zoom
                                'doubleClick': 'reset',  # Double-click to reset zoom
                                'modeBarButtonsToRemove': [
                                    'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 
                                    'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 
                                    'hoverCompareCartesian', 'toggleSpikelines', 
                                    'zoom2d', 'resetViews', 'toggleHover',
                                    'zoomInMapbox', 'zoomOutMapbox', 'panMapbox', 
                                    'selectMapbox', 'lassoMapbox'
                                ]
                            }, 
                            style={"height":"500px", "width":"100%"},
                            figure=go.Figure()  # Initialize with empty figure
                        )
                    ],
                    style={"height":"500px", "width":"100%"}
                )
            ], style={'padding': '10px', 'width': '83.33%', 'display': 'inline-block', 'verticalAlign': 'top'}),
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
                            clearable=False,
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
            ], style={'padding': '10px', 'paddingTop': '20px', 'width': '16.67%', 'display': 'inline-block', 'verticalAlign': 'top'})
        ], style={'display': 'block', 'width': '100%'}),
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
                        'Export to CSV',
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
                            figure=go.Figure(),
                            config={
                                'displayModeBar': True,
                                'displaylogo': False,
                                'modeBarButtonsToRemove': [
                                    'zoom2d', 'pan2d', 'select2d', 'lasso2d', 
                                    'zoomIn2d', 'zoomOut2d', 'autoScale2d', 
                                    'hoverClosestCartesian', 'hoverCompareCartesian'
                                ]
                            }
                        )
                    ],
                    style={"height":"520px"}
                ), 
                style={'padding': '15px', 'width': '83.33%', 'display': 'inline-block', 'verticalAlign': 'top'}
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
                    html.H6("Profiled Crude Oils", style={"marginBottom": "6px", "fontWeight": "bold", "color": "#2c3e50", "fontSize": "12px",}),
                    # Hidden checklist to store values
                    dcc.Checklist(
                        id="profiled-streams", 
                        options=[], 
                        value=[],
                        style={"display": "none"}
                    ),
                    html.Div(id="profiled-streams-container", children=[])
                ], style={
            
                    "padding": "12px",
                    "border": "1px solid #ddd",
                    "borderRadius": "4px",
                    "backgroundColor": "#f9f9f9",
                    "maxHeight": "350px",
                    "overflowY": "auto",
                    "fontSize": "10px",
                })
            ], style={'padding': '12px', 'width': '16.67%', 'display': 'inline-block', 'verticalAlign': 'top'})
        ], style={'display': 'block', 'width': '100%'}),
        html.Br(),
        html.Div([
            html.H4(
                id="table-title",
                children="Global Crude Production Breakdown",
                style={"color":"#d35400","textAlign":"center", "marginTop":"10px", "marginBottom": "0px", "flexGrow": 1}
            ),
            html.Div([
                html.Button(
                    'Export to CSV',
                    id='btn-export-table-csv',
                    n_clicks=0,
                    style={
                        'backgroundColor': 'white',
                        'color': '#2c3e50',
                        'border': '1px solid #dee2e6',
                        'padding': '4px 10px',
                        'borderRadius': '4px',
                        'cursor': 'pointer',
                        'fontSize': '13px',
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
                            fixed_rows={'headers': True},
                            markdown_options={"link_target": "_blank"},
                            style_table={
                                "overflowX": "auto", 
                                "overflowY": "auto", 
                                "minHeight": "600px",
                                "maxHeight": "600px",
                                "height": "auto"
                            },
                            
    
                            
                            style_cell={
                                "fontSize": "12px",
                                "fontFamily": "Arial",
                                "whiteSpace": "normal",
                                "color": "#1f3b6f",
                                "minWidth": "90px",
                                "textAlign": "right",
                                "padding": "1px",
                                "height": "auto"
                            },

                            # Removed style_cell_conditional to keep all columns right-aligned
                            


                            style_header={
                                "textAlign": "center",
                                "fontWeight": "bold",
                                "backgroundColor": "white",
                                "color": "#1f3b6f",
                                "padding": "4px"
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
                    style={"minHeight": "600px", 'maxHeight': '600px'}
                )
            ], style={'padding': '15px', 'minHeight': '600px', 'maxHeight': '600px', 'width': '83.33%', 'display': 'inline-block', 'verticalAlign': 'top'}),
            html.Div([
                html.Label("Stream Name"),
                dcc.Input(id="filter-stream", type="text", placeholder="Stream Name", value="", style={"width": "100%"}),
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
            ], style={'padding': '15px', 'width': '16.67%', 'display': 'inline-block', 'verticalAlign': 'top'})

        ], style={'display': 'block', 'width': '100%'}),
        
        # Footer Content
        html.Div([
            # Yearly Footer
            html.Div(id="yearly-footer", children=[
                html.P([
                    html.B("Countries: "),
                    "Select jurisdictions are included under countries for data presentation purposes."
                ], style={"fontSize": "12px", "color": "#2c3e50", "marginTop": "10px", "marginBottom": "5px", "fontStyle": "italic"})
            ], style={"display": "block", "paddingLeft": "15px", "width": "83.33%"}),
            
            # Monthly Footer
            html.Div(id="monthly-footer", children=[
                html.P([
                    html.B("Countries: "),
                    "Select jurisdictions are included under countries for data presentation purposes."
                ], style={"fontSize": "12px", "color": "#2c3e50", "marginTop": "10px", "marginBottom": "2px", "fontStyle": "italic"}),
                html.P("Countries are being added as they are updated.", 
                       style={"fontSize": "12px", "color": "#2c3e50", "marginBottom": "2px", "fontStyle": "italic"}),
                html.Ul([
                    html.Li("Starting 2024, Olmeca is being blended with condensates."),
                    html.Li("CPC Kazakhstan is a blend of Tengiz, Kashagan and Karachaganak streams."),
                    html.Li("In April and May 2022, Russia's \"Other Crudes\" are negative due to significant inventory withdrawals.")
                ], style={"fontSize": "12px", "color": "#2c3e50", "marginTop": "5px", "paddingLeft": "20px", "fontStyle": "italic"})
            ], style={"display": "none", "paddingLeft": "15px", "width": "83.33%"})
        ])
    ], style={'padding': '20px', 'background': '#f8f9fa'})


def register_callbacks(dash_app, server):
    """Register all callbacks for Crude Overview"""
    
    @dash_app.callback(
        [Output("monthly-only-filters-container", "style"),
         Output("yearly-footer", "style"),
         Output("monthly-footer", "style")],
        [Input("crude-main-tabs", "value")]
    )
    def toggle_monthly_elements(tab):
        """Show/hide filters and footers based on active tab"""
        if tab == "monthly":
            return {"display": "block"}, {"display": "none"}, {"display": "block", "paddingLeft": "15px", "width": "83.33%"}
        elif tab == "yearly":
            return {"display": "none"}, {"display": "block", "paddingLeft": "15px", "width": "83.33%"}, {"display": "none"}
        else:
            return {"display": "none"}, {"display": "block", "paddingLeft": "15px", "width": "83.33%"}, {"display": "none"}

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
        State("selected-country-map-store", "data"),
        State("table-map-filter-active-store", "data"),
        prevent_initial_call=True
    )
    def update_country_from_map(clickData, current_selected_country, table_map_filter_active):
        """Update country dropdown when map is clicked - but only for new country selections"""
        if clickData and clickData.get("points"):
            point = clickData["points"][0]
            
            # Check for background click (ocean/empty area)
            if "customdata" in point and point["customdata"]:
                cdata = point["customdata"]
                if (isinstance(cdata, list) and len(cdata) > 0 and cdata[0] == "__BACKGROUND_CLICK__") or \
                   (isinstance(cdata, str) and cdata == "__BACKGROUND_CLICK__"):
                    return no_update
            
            # Try to get country name from customdata first (standardized map)
            clicked_country = None
            if "customdata" in point and point["customdata"]:
                clicked_country = point["customdata"][0]
            
            # Fallback to location (might be ISO or name)
            if not clicked_country:
                clicked_country = point.get("location")
                
            if clicked_country:
                # Map ISO code to full country name if needed
                clicked_country = _map_iso_to_country_name(clicked_country)
                
                # Only update dropdown for NEW country selections
                # If clicking the same country again, don't change the dropdown
                if clicked_country != current_selected_country:
                    print(f"DEBUG: Map clicked, updating dropdown to: {clicked_country}")
                    return [clicked_country]
                else:
                    print(f"DEBUG: Same country clicked ({clicked_country}), keeping dropdown unchanged")
                    return no_update
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
        all_years = PRODUCTION_YEARS if PRODUCTION_YEARS else []
        
        # Limit to recent 5 years (2021-2025) as per live source requirements
        current_year = 2025  # Based on live source data availability
        recent_years_range = list(range(current_year - 4, current_year + 1))  # 2021, 2022, 2023, 2024, 2025
        
        # Filter to only include years that exist in data AND are in the recent 5 years range
        available_recent_years = [y for y in all_years if y in recent_years_range]
        
        # If no years available in recent range, fall back to recent 5 years from available data
        if not available_recent_years and all_years:
            # Take the 5 most recent years from available data
            sorted_years = sorted(all_years, reverse=True)
            available_recent_years = sorted_years[:5]
        
        # Sort years in ascending order for display
        years_ascending = sorted(available_recent_years) if available_recent_years else []
        
        print(f"DEBUG PRODUCTION YEARS: All available years: {sorted(all_years) if all_years else []}")
        print(f"DEBUG PRODUCTION YEARS: Filtered to recent 5 years: {years_ascending}")
        
        options = [{"label": "(All)", "value": "(All)"}] + [{"label": str(y), "value": y} for y in years_ascending]
        
        # Default to the two most recent years from the filtered list
        if len(years_ascending) >= 2:
            default_value = sorted(years_ascending, reverse=True)[:2]  # Most recent 2 years
        elif len(years_ascending) == 1:
            default_value = [years_ascending[0]]
        else:
            default_value = []
        
        print(f"DEBUG PRODUCTION YEARS: Default selection: {default_value}")
        
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
         Input("current-submenu", "data"),
         Input("selected-country-map-store", "data"),
         Input("table-map-filter-active-store", "data")],
        prevent_initial_call=False
    )
    def update_profiled_streams_options(country, tab, year, year_month, current_submenu, selected_country_map, table_map_filter_active):
        """Update profiled streams options based on selected country and tab using grades CSV files"""
        # Only load data if page is active
        if current_submenu != 'crude-overview':
            return [], None
        
        # Ensure data is loaded
        _ensure_data_loaded()
        
        try:
            # Handle country - ensure it's a list
            # Map selection overrides dropdown if present AND active
            if selected_country_map and table_map_filter_active:
                resolved_countries = [selected_country_map]
            else:
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
            
            if tab == "monthly" or tab is None:
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
            else:
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

            
            # Fallback: enrich profile URLs from Production Breakdown tables if missing
            if tab == "monthly" or tab is None:
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
            else:
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
    
            # If no streams from grades CSV, fall back to all streams from bar data
            if not available_streams:
                if tab == "monthly" or tab is None:
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
                else:
                    if not BAR_LONG_YEARLY.empty and "Stream" in BAR_LONG_YEARLY.columns:
                        country_data = BAR_LONG_YEARLY[BAR_LONG_YEARLY["Country"].isin(country)]
                        available_streams = order_streams_list(country_data["Stream"].dropna().unique().tolist(), tab="yearly")
            
            # Create options - only include label and value (profile_url is handled separately)
            options = []
            for s in available_streams:
                opt = {"label": s, "value": s}
                # Note: profile_url is stored in stream_to_url dict and handled by the stream-profile-urls-store
                options.append(opt)
            
            # Default: select all streams (default mode - no filtering)
            default_value = available_streams[:]
            
            print(f"DEBUG: Returning {len(options)} options and {len(default_value)} default values (all selected by default)")
            print(f"DEBUG: Profile URLs will be handled by update_profiled_streams_with_colors callback")
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
         Input("crude-main-tabs", "value"),
         Input("crude-country-dropdown", "value"),
         Input("selected-country-map-store", "data"),
         Input("table-map-filter-active-store", "data")],
        prevent_initial_call=False
    )
    def update_profiled_streams_with_colors(selected_streams, stream_options, chart_figure, active_tab, country, selected_country_map, table_map_filter_active):
        """Create clickable stream buttons with highlight/dimmed selection - no checkboxes"""
        _ensure_color_maps()
        if not stream_options:
            return html.Div("No streams available"), {}
        
        selected_streams = selected_streams if selected_streams else []
        
        # Get profile URLs for the streams
        profile_urls_dict = {}
        
        # Handle country - ensure it's a list
        # Map selection overrides dropdown if present AND active
        if selected_country_map and table_map_filter_active:
            resolved_countries = [selected_country_map]
        else:
            resolved_countries = _resolve_countries_selection(country)
        
        if resolved_countries:
            # Get profile URLs from the same data source as the options callback
            if active_tab == "monthly" or active_tab is None:
                # Load monthly grades dynamically for all selected countries
                country_df = get_monthly_grades_for_country(resolved_countries)
                if not country_df.empty and "Stream" in country_df.columns:
                    # Extract link if available (profile_url or BSP link)
                    link_col = None
                    possible_cols = ["profile_url", "Profile URL", "Profile_URL", "profile-url", "Profile-URL", 
                                     "BSP link", "BSP Link", "BSP_link", "BSP_link", "bsp_link", "Bsp_link"]
                    for col in possible_cols:
                        if col in country_df.columns:
                            link_col = col
                            break
                    
                    # Also check case-insensitive
                    if not link_col:
                        for col in country_df.columns:
                            if col.lower().replace(" ", "_").replace("-", "_") in ["profile_url", "bsp_link"]:
                                link_col = col
                                break
                    
                    if link_col:
                        for _, row in country_df.iterrows():
                            stream = str(row["Stream"]).strip() if pd.notna(row["Stream"]) else None
                            url_val = row[link_col]
                            url = str(url_val).strip() if pd.notna(url_val) and str(url_val).strip() else None
                            if stream and url and url != "nan" and url != "None":
                                profile_urls_dict[stream] = url
            else:
                # Fetch yearly grades dynamically from DB
                country_df = get_yearly_grades_for_country(resolved_countries)
                if not country_df.empty and "Stream" in country_df.columns:
                    # Extract link if available (profile_url or BSP link)
                    link_col = None
                    possible_cols = ["profile_url", "Profile URL", "Profile_URL", "profile-url", "Profile-URL", 
                                     "BSP link", "BSP Link", "BSP_link", "BSP_link", "bsp_link", "Bsp_link"]
                    for col in possible_cols:
                        if col in country_df.columns:
                            link_col = col
                            break
                    
                    # Also check case-insensitive
                    if not link_col:
                        for col in country_df.columns:
                            if col.lower().replace(" ", "_").replace("-", "_") in ["profile_url", "bsp_link"]:
                                link_col = col
                                break
                    
                    if link_col:
                        for _, row in country_df.iterrows():
                            stream = str(row["Stream"]).strip() if pd.notna(row["Stream"]) else None
                            url_val = row[link_col]
                            url = str(url_val).strip() if pd.notna(url_val) and str(url_val).strip() else None
                            if stream and url and url != "nan" and url != "None":
                                profile_urls_dict[stream] = url
        
        # Get all available streams from options
        all_available_streams = [opt["value"] for opt in stream_options] if stream_options else []
        print(f"DEBUG COLOR: update_profiled_streams_with_colors called with tab='{active_tab}', {len(all_available_streams)} streams")
        if active_tab == "monthly" and len(all_available_streams) > 0:
            print(f"DEBUG COLOR: First 10 monthly streams: {all_available_streams[:10]}")
        
        # Get colors from STREAM_COLOR_MAPS and comprehensive mapping (NOT from chart figure to avoid circular dependency)
        color_map = {}
        streams_in_chart = []
        
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
            profile_url = profile_urls_dict.get(stream)  # Get from our fetched profile URLs
            
            # Store profile URL for navigation (it's already in the dict, but ensure it's there)
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
                "padding": "2px 5px",  # Reduced padding to make bars thinner
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
                    all_streams.append(str(button_id["stream"]))
        
        # Normalize clicked_stream to string
        clicked_stream = str(clicked_stream) if clicked_stream else None
        
        print(f"DEBUG PROFILE BTN: Clicked='{clicked_stream}'")
        print(f"DEBUG PROFILE BTN: Current selected count={len(current_selected) if current_selected else 0}")
        print(f"DEBUG PROFILE BTN: All streams count={len(all_streams)}")

        # Get current selection - normalize to strings
        current_selected = [str(s) for s in current_selected] if current_selected else []
        current_set = set(current_selected)
        all_set = set(all_streams)
        
        # Determine if we're in default mode (all streams selected)
        # Note: If current_selected is empty, it usually implies default mode in UI logic, 
        # but here we want to return EXPLICIT list of all streams for "all selected" state.
        is_default_mode = (current_set == all_set and len(all_set) > 0) or len(current_set) == 0
        
        print(f"DEBUG PROFILE BTN: is_default_mode={is_default_mode}")
        
        # Toggle behavior:
        # - If in default mode (all selected): clicking a stream selects only that stream
        # - If one stream is selected: clicking the same stream returns to default (all selected)
        if is_default_mode:
            # Default mode: clicking any stream selects only that stream
            print(f"DEBUG PROFILE BTN: Default mode -> Selecting only '{clicked_stream}'")
            return [clicked_stream]
        elif len(current_set) == 1 and clicked_stream in current_set:
            # One stream selected and clicking the same stream: return to default (all selected)
            print(f"DEBUG PROFILE BTN: Single select match -> Resetting to ALL ({len(all_streams)} items)")
            # Return sorted all_streams to explicitly select all
            res = sorted(all_streams) if all_streams else []
            return res
        else:
            # Clicking a different stream when one is already selected: select the clicked stream
            print(f"DEBUG PROFILE BTN: Switching selection to '{clicked_stream}'")
            return [clicked_stream]
    
    # Clientside callback to navigate to stream profile URL and track last clicked stream
    clientside_callback(
        """
        function(button_clicks, button_ids, profile_urls, last_clicked_stream, current_selected) {
            if (!window.dash_clientside) {
                return null;
            }
            
            if (!profile_urls || Object.keys(profile_urls).length === 0) {
                console.log('No profile URLs available');
                return null;
            }
            
            // Find which button was clicked
            const triggered = window.dash_clientside.callback_context.triggered[0];
            if (!triggered || !triggered.prop_id) {
                console.log('No trigger detected');
                return null;
            }
            
            // CRITICAL: Ensure this only runs if a button was actually clicked.
            // Pattern-matching callbacks can trigger when buttons are added to the layout (Input ALL).
            // We check if any of the buttons have n_clicks > 0.
            if (!button_clicks || !button_clicks.some(click => click && click > 0)) {
                console.log('🚫 SKIPPING - No genuine button clicks detected (all n_clicks <= 0)');
                return null;
            }
            
            // Parse the triggered_id to get the stream name and validate the click
            try {
                const jsonPart = triggered.prop_id.split('.')[0];
                const buttonId = JSON.parse(jsonPart);
                const clickedStream = buttonId.stream;
                
                // Find the corresponding button click count for the triggered stream
                let clickCount = 0;
                if (button_ids && button_clicks) {
                    for (let i = 0; i < button_ids.length; i++) {
                        if (button_ids[i].stream === clickedStream) {
                            clickCount = button_clicks[i] || 0;
                            break;
                        }
                    }
                }
                
                console.log('Button clicked for stream:', clickedStream, 'click count:', clickCount);
                
                // Only proceed if this specific button has been clicked (click count > 0)
                if (clickCount <= 0) {
                    console.log('🚫 SKIPPING - Clicked stream has no genuine clicks (click count <= 0)');
                    return null;
                }
                
                console.log('Current selected streams:', current_selected);
                console.log('Last clicked stream:', last_clicked_stream);
                
                // Mirror the exact server-side logic to determine if stream will be selected
                const allStreams = button_ids.map(id => id.stream);
                const currentSelectedSet = new Set(current_selected || []);
                const allStreamsSet = new Set(allStreams);
                
                // Determine if we're in default mode (matches server-side logic exactly)
                const isDefaultMode = (currentSelectedSet.size === allStreamsSet.size && 
                                     [...currentSelectedSet].every(s => allStreamsSet.has(s))) || 
                                     currentSelectedSet.size === 0;
                
                let willBeSelected = false;
                
                if (isDefaultMode) {
                    // Default mode: clicking any stream selects only that stream -> SELECTION
                    willBeSelected = true;
                    console.log('Default mode detected - clicking will SELECT stream');
                } else if (currentSelectedSet.size === 1 && currentSelectedSet.has(clickedStream)) {
                    // One stream selected and clicking the same stream: return to default -> DESELECTION
                    willBeSelected = false;
                    console.log('Single stream selected, clicking same stream - will DESELECT (return to all)');
                } else {
                    // Clicking a different stream when one is already selected -> SELECTION
                    willBeSelected = true;
                    console.log('Switching to different stream - will SELECT new stream');
                }
                
                console.log('Will stream be selected?', willBeSelected);
                console.log('Is different from last navigation?', clickedStream !== last_clicked_stream);
                
                // Only navigate if:
                // 1. The stream will be SELECTED (not deselected)
                // 2. It's different from the last navigation (prevent duplicate navigation)
                if (willBeSelected && clickedStream !== last_clicked_stream) {
                    console.log('Available profile URLs:', Object.keys(profile_urls));
                    
                    if (clickedStream && profile_urls[clickedStream]) {
                        const profileUrl = profile_urls[clickedStream];
                        if (profileUrl && profileUrl !== 'nan' && profileUrl !== 'None' && profileUrl.trim() !== '') {
                            console.log('✅ NAVIGATING to', profileUrl, 'for stream', clickedStream);
                            // Open in new tab
                            window.open(profileUrl, '_blank');
                            // Return the clicked stream so it becomes the new last_clicked_stream
                            return clickedStream;
                        } else {
                            console.log('❌ Invalid URL for stream', clickedStream, ':', profileUrl);
                        }
                    } else {
                        console.log('❌ No URL found for stream:', clickedStream);
                    }
                } else {
                    if (!willBeSelected) {
                        console.log('🚫 SKIPPING navigation - stream will be DESELECTED');
                    } else {
                        console.log('🚫 SKIPPING navigation - same as last navigation');
                    }
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
         State("last-clicked-stream-store", "data"),
         State("profiled-streams", "value")]
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
    
    # Clientside callback to set cursor style based on country selection
    dash_app.clientside_callback(
        """
        function(selectedCountry, isActive) {
            const mapElement = document.getElementById('crude-map');
            if (mapElement) {
                if (selectedCountry && isActive) {
                    mapElement.setAttribute('data-country-selected', 'true');
                } else {
                    mapElement.removeAttribute('data-country-selected');
                }
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("crude-map", "style"),
        Input("selected-country-map-store", "data"),
        Input("table-map-filter-active-store", "data"),
        prevent_initial_call=False
    )

    # Enhanced clientside callback for comprehensive ocean click detection
    # This uses JavaScript to detect clicks directly on the map container
    dash_app.clientside_callback(
        """
        function(clickData, selectedCountry, isActive, mapFigure) {
            // Enhanced ocean click detection using multiple strategies
            
            if (!selectedCountry || !isActive) {
                // No country selected, nothing to reset
                return window.dash_clientside.no_update;
            }
            
            // Strategy 1: Check if clickData indicates a background click
            if (clickData && clickData.points && clickData.points.length > 0) {
                const point = clickData.points[0];
                
                // Check for our background click markers
                if (point.customdata) {
                    let cdata = point.customdata;
                    
                    // Handle different customdata formats
                    if (Array.isArray(cdata)) {
                        if (cdata.length > 0) {
                            let firstItem = cdata[0];
                            if (Array.isArray(firstItem) && firstItem.length > 0 && firstItem[0] === "__BACKGROUND_CLICK__") {
                                return {"trigger": "ocean_click", "timestamp": Date.now()};
                            } else if (typeof firstItem === "string" && firstItem === "__BACKGROUND_CLICK__") {
                                return {"trigger": "ocean_click", "timestamp": Date.now()};
                            }
                        }
                    } else if (typeof cdata === "string" && cdata === "__BACKGROUND_CLICK__") {
                        return {"trigger": "ocean_click", "timestamp": Date.now()};
                    }
                }
                
                // Check trace name for background elements
                if (point.trace && point.trace.name) {
                    const traceName = point.trace.name;
                    if (traceName === "ocean_background" || traceName === "background_fill" || traceName === "background") {
                        return {"trigger": "ocean_click", "timestamp": Date.now()};
                    }
                }
            }
            
            return window.dash_clientside.no_update;
        }
        """,
        Output("ocean-click-trigger", "data"),
        Input("crude-map", "clickData"),
        State("selected-country-map-store", "data"),
        State("table-map-filter-active-store", "data"),
        State("crude-map", "figure"),
        prevent_initial_call=True
    )

    # Enhanced map click callback with better ocean detection
    @dash_app.callback(
        [Output("selected-country-map-store", "data"),
         Output("table-map-filter-active-store", "data"),
         Output("crude-country-dropdown", "value")],
        [Input("crude-map", "clickData"),
         Input("crude-main-tabs", "value"),
         Input("ocean-click-trigger", "data")],
        [State("selected-country-map-store", "data"),
         State("table-map-filter-active-store", "data"),
         State("current-submenu", "data"),
         State("crude-country-dropdown", "value")],
        prevent_initial_call=False
    )
    def update_selected_country_map(click_data, tab_value, ocean_trigger, current_selected, current_active, submenu, current_dropdown):
        """Update country selection from map click with enhanced ocean click detection"""
        from dash import ctx
        if submenu != 'crude-overview':
            return no_update, no_update, no_update
            
        triggered_id = ctx.triggered_id
        
        # Handle ocean click trigger
        if triggered_id == "ocean-click-trigger" and ocean_trigger:
            print("DEBUG MAP CLICK: Ocean click trigger activated - resetting to show all countries")
            _ensure_data_loaded()
            all_countries = COUNTRIES if COUNTRIES else []
            reset_dropdown = ["(All)"] + all_countries
            return None, False, reset_dropdown
        
        # Don't reset selection when switching tabs - allow persistence
        if triggered_id == "crude-main-tabs":
            return no_update, no_update, no_update
            
        if click_data and click_data.get("points"):
            point = click_data["points"][0]
            
            # Enhanced background click detection
            is_background_click = False
            if "customdata" in point and point["customdata"]:
                cdata = point["customdata"]
                # Handle both old format (string/list with string) and new format (list of lists)
                if isinstance(cdata, list):
                    if len(cdata) > 0:
                        # New format: [["__BACKGROUND_CLICK__"]] or old format: ["__BACKGROUND_CLICK__"]
                        first_item = cdata[0]
                        if isinstance(first_item, list) and len(first_item) > 0 and first_item[0] == "__BACKGROUND_CLICK__":
                            is_background_click = True
                        elif isinstance(first_item, str) and first_item == "__BACKGROUND_CLICK__":
                            is_background_click = True
                elif isinstance(cdata, str) and cdata == "__BACKGROUND_CLICK__":
                    is_background_click = True
            
            # Additional check: if the trace name suggests it's a background element
            if hasattr(point, 'trace') and point.trace and hasattr(point.trace, 'name'):
                trace_name = point.trace.name
                if trace_name in ['ocean_background', 'background_fill', 'background']:
                    is_background_click = True
            
            # Handle background clicks - reset to show all countries
            if is_background_click:
                print("DEBUG MAP CLICK: Background/ocean click detected - resetting to show all countries")
                # Ensure data is loaded to get all countries
                _ensure_data_loaded()
                all_countries = COUNTRIES if COUNTRIES else []
                reset_dropdown = ["(All)"] + all_countries
                return None, False, reset_dropdown
            
            # Try to get country name from customdata first (standardized map)
            clicked_country = None
            if "customdata" in point and point["customdata"]:
                if isinstance(point["customdata"], list) and len(point["customdata"]) > 0:
                    # Handle nested list format [[country, iso]] or simple list [country]
                    first_item = point["customdata"][0]
                    if isinstance(first_item, list) and len(first_item) > 0:
                        clicked_country = first_item[0]  # [[country, iso]] format
                    elif isinstance(first_item, str):
                        clicked_country = first_item  # [country] format
                else:
                    clicked_country = point["customdata"]
            
            # Fallback to location (might be ISO or name)
            if not clicked_country:
                clicked_country = point.get("location")
                
            if clicked_country:
                # Map ISO code to full country name if needed
                clicked_country = _map_iso_to_country_name(clicked_country)
                
                # Enhanced behavior: if one country is selected, any other click resets to all
                if current_selected and current_active:
                    if clicked_country == current_selected:
                        # Same country clicked - reset to show all countries
                        print(f"DEBUG MAP CLICK: Same country clicked ({clicked_country}) - resetting to show all countries")
                        _ensure_data_loaded()
                        all_countries = COUNTRIES if COUNTRIES else []
                        reset_dropdown = ["(All)"] + all_countries
                        return None, False, reset_dropdown
                    else:
                        # Different country clicked - also reset to show all countries (matches Tableau behavior)
                        print(f"DEBUG MAP CLICK: Different country clicked ({clicked_country}) when {current_selected} was selected - resetting to show all countries")
                        _ensure_data_loaded()
                        all_countries = COUNTRIES if COUNTRIES else []
                        reset_dropdown = ["(All)"] + all_countries
                        return None, False, reset_dropdown
                
                # No country currently selected or not active - select the clicked country
                print(f"DEBUG MAP CLICK: New country selected ({clicked_country}), setting table_map_filter_active to True")
                return clicked_country, True, [clicked_country]
                
        return current_selected, current_active, no_update
    
    @dash_app.callback(
        Output("selected-bar-store", "data"),
        Input("production-breakdown-chart", "clickData"),
        [State("selected-bar-store", "data"),
         State("crude-main-tabs", "value"),
         State("production-year-dropdown", "value")],
        prevent_initial_call=True
    )
    def handle_chart_bar_click(clickData, current_selection, tab, production_years):
        """
        Handle chart bar clicks for single-bar global selection behavior.
        
        Core Logic:
        - Only ONE bar can be active across the entire chart at any time
        - Selection is based on unique bar identity: {year, month, stream}
        - Click same bar → deselect (activeBar = null)
        - Click different bar → replace selection (activeBar = new bar)
        """
        print(f"DEBUG CHART CLICK: Handler called! clickData={clickData is not None}, tab={tab}")
        
        if not clickData:
            print(f"DEBUG CHART CLICK: No clickData provided")
            return no_update
        
        try:
            # Extract point information with robust error handling
            point = clickData["points"][0]
            
            # DEBUG: Print all available fields in the point
            print(f"DEBUG CHART CLICK: Point data: {point}")
            print(f"DEBUG CHART CLICK: Available keys: {list(point.keys())}")
            
            # Extract stream information with multiple fallbacks
            clicked_stream = None
            if point.get("legendgroup"):
                clicked_stream = str(point.get("legendgroup")).strip()
                print(f"DEBUG CHART CLICK: Extracted stream from legendgroup: '{clicked_stream}'")
            elif point.get("name"):
                clicked_stream = str(point.get("name")).strip()
                print(f"DEBUG CHART CLICK: Extracted stream from name: '{clicked_stream}'")
            elif point.get("customdata") and isinstance(point.get("customdata"), list):
                # Try customdata if available
                customdata = point.get("customdata")
                print(f"DEBUG CHART CLICK: Customdata available: {customdata}")
                if len(customdata) >= 3:
                    # Monthly format: [Country, Year, Stream]
                    clicked_stream = str(customdata[2]).strip()
                    print(f"DEBUG CHART CLICK: Extracted stream from customdata[2] (monthly): '{clicked_stream}'")
                elif len(customdata) >= 1:
                    # Yearly format: [Stream] - stream is at index 0
                    clicked_stream = str(customdata[0]).strip()
                    print(f"DEBUG CHART CLICK: Extracted stream from customdata[0] (yearly): '{clicked_stream}'")
            
            if not clicked_stream:
                print(f"DEBUG CHART CLICK: Could not extract stream from point: {point}")
                return no_update
            
            # Extract month with robust handling
            clicked_month = str(point.get("x", "")).strip()
            if not clicked_month:
                print(f"DEBUG CHART CLICK: Could not extract month from point: {point}")
                return no_update
            
            # Get the year from the subplot structure with robust error handling
            subplot_col = point.get("xaxis", "x")  # e.g., "x", "x2", "x3"
            print(f"DEBUG CHART CLICK: Subplot column: {subplot_col}")
            
            # Extract column number from xaxis (x=1, x2=2, x3=3, etc.)
            try:
                if subplot_col == "x":
                    col_idx = 0
                elif subplot_col.startswith("x") and subplot_col[1:].isdigit():
                    col_idx = int(subplot_col[1:]) - 1  # x2 -> 1, x3 -> 2, etc.
                else:
                    print(f"DEBUG CHART CLICK: Invalid subplot format: {subplot_col}")
                    return no_update
            except (ValueError, IndexError) as e:
                print(f"DEBUG CHART CLICK: Error parsing subplot column {subplot_col}: {e}")
                return no_update
            
            # Extract year information - for monthly charts, use customdata; for yearly charts, use column mapping
            clicked_year = None
            if tab == "monthly" and point.get("customdata") and isinstance(point.get("customdata"), list):
                customdata = point.get("customdata")
                if len(customdata) >= 2:
                    # Monthly format: [Country, Year, Stream] - extract year from customdata[1]
                    clicked_year = str(customdata[1]).strip()
                    print(f"DEBUG CHART CLICK: Extracted year from customdata[1] (monthly): '{clicked_year}'")
                else:
                    print(f"DEBUG CHART CLICK: Monthly customdata too short for year extraction: {customdata}")
                    return no_update
            else:
                # For yearly charts or fallback, use column index mapping
                resolved_years = _resolve_years_selection(production_years)
                if resolved_years:
                    selected_years = sorted([str(y) for y in resolved_years])
                    print(f"DEBUG CHART CLICK: Available years: {selected_years}, Column index: {col_idx}")
                    
                    if 0 <= col_idx < len(selected_years):
                        clicked_year = selected_years[col_idx]
                    else:
                        print(f"DEBUG CHART CLICK: Column index {col_idx} out of range for years {selected_years}")
                        # Try to fallback to first year if index is out of range
                        clicked_year = selected_years[0] if selected_years else None
                        print(f"DEBUG CHART CLICK: Fallback to year: {clicked_year}")
                else:
                    print(f"DEBUG CHART CLICK: No production years available")
                    return no_update
            
            if not clicked_year:
                print(f"DEBUG CHART CLICK: Could not determine year")
                return no_update
            
            print(f"DEBUG CHART CLICK: Bar clicked - Stream: '{clicked_stream}', Month: '{clicked_month}', Year: '{clicked_year}'")
            print(f"DEBUG CHART CLICK: Data types - Stream: {type(clicked_stream)}, Month: {type(clicked_month)}, Year: {type(clicked_year)}")
            
            # Core Logic: Single-bar global selection across entire chart
            # Create the clicked bar identity - ensure all values are strings for consistent comparison
            clicked_bar = {
                "year": str(clicked_year),
                "month": str(clicked_month),
                "stream": str(clicked_stream)
            }
            
            # Check if same bar is clicked (toggle off)
            if (current_selection and 
                str(current_selection.get("year")) == str(clicked_bar["year"]) and
                str(current_selection.get("month")) == str(clicked_bar["month"]) and
                str(current_selection.get("stream")) == str(clicked_bar["stream"])):
                print(f"DEBUG CHART CLICK: Same bar clicked ({clicked_stream}-{clicked_month}-{clicked_year}), clearing selection (activeBar = null)")
                return None  # activeBar = null
            
            # New bar selected → replace previous selection globally
            active_bar = {
                "year": str(clicked_bar["year"]),
                "month": str(clicked_bar["month"]),
                "stream": str(clicked_bar["stream"]),
                "tab": str(tab),  # Store current tab for clearing logic
                "timestamp": pd.Timestamp.now().isoformat()  # To force updates
            }
            
            if current_selection:
                prev_stream = current_selection.get("stream")
                prev_month = current_selection.get("month")
                prev_year = current_selection.get("year")
                print(f"DEBUG CHART CLICK: Replacing global selection from {prev_stream}-{prev_month}-{prev_year} to {clicked_stream}-{clicked_month}-{clicked_year}")
            else:
                print(f"DEBUG CHART CLICK: New global bar selected: {clicked_stream}-{clicked_month}-{clicked_year} (tab: {tab})")
            
            print(f"DEBUG CHART CLICK: activeBar = {active_bar}")
            return active_bar
            
        except Exception as e:
            print(f"ERROR CHART CLICK: {e}")
            import traceback
            traceback.print_exc()
            return no_update
    
    @dash_app.callback(
        Output("crude-map", "figure"),
        [Input("crude-year-dropdown", "value"),
         Input("crude-year-month-dropdown", "value"),
         Input("crude-country-dropdown", "value"),
         Input("crude-main-tabs", "value"),
         Input("selected-country-map-store", "data"),
         Input("table-map-filter-active-store", "data"),
         Input("current-submenu", "data")],
        prevent_initial_call=False
    )
    def update_map(selected_year, selected_year_month, selected_countries, tab, selected_country_map, table_map_filter_active, current_submenu):
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
            tab = "monthly"
        
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
        
        # Add year/period for tooltip and ISO codes for map
        if not agg.empty:
            if tab == "yearly":
                agg["Year"] = str(selected_year)
            else:
                agg["Year"] = str(selected_year_month)
            
            # Add iso_alpha for standardized map
            agg["iso_alpha"] = agg["GeoCountry"].apply(get_iso_code)
            
            # Create hover text matching design (gray labels, bold values)
            if tab == "yearly":
                agg["hover_text"] = agg.apply(lambda row: (
                    f"<span style='color: #7f7f7f;'>Country:</span> <span style='font-weight: bold; color: #000;'>{row['Country']}</span><br>"
                    f"<span style='color: #7f7f7f;'>Production Volume:</span> <span style='font-weight: bold; color: #000;'>{row['value']:,.0f} ('000 b/d)</span><br>"
                    f"<span style='color: #7f7f7f;'>Year:</span> <span style='font-weight: bold; color: #000;'>{row['Year']}</span>"
                ), axis=1)
            else:
                agg["hover_text"] = agg.apply(lambda row: (
                    f"<span style='color: #7f7f7f;'>Date:</span> <span style='font-weight: bold; color: #000;'>{row['Year']}</span><br>"
                    f"<span style='color: #7f7f7f;'>Country:</span> <span style='font-weight: bold; color: #000;'>{row['Country']}</span><br>"
                    f"<span style='color: #7f7f7f;'>Production Volume:</span> <span style='font-weight: bold; color: #000;'>{row['value']:,.0f} ('000 b/d)</span>"
                ), axis=1)
        
        if agg.empty:
            fig = go.Figure()
            fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return fig
        
        # Identify selected ISOs for highlighting - only when table_map_filter_active is True
        selected_iso = None
        other_isos = None
        map_selected_country = None
        if selected_country_map and table_map_filter_active:
            # Only highlight when the map filter is active for the table
            selected_iso = get_iso_code(selected_country_map)
            other_isos = [iso for iso in agg["iso_alpha"].tolist() if iso and iso != selected_iso]
            map_selected_country = selected_country_map
            print(f"DEBUG MAP: Highlighting country {selected_country_map} (table_map_filter_active=True)")
        else:
            print(f"DEBUG MAP: No highlighting (selected_country_map={selected_country_map}, table_map_filter_active={table_map_filter_active})")

        # Calculate max_val for scaling
        max_val = agg["value"].max() if "value" in agg.columns and len(agg) > 0 else 0
        if pd.isna(max_val) or max_val <= 0:
            max_val = 1000

        # Use max_val directly for the scale limit as requested
        color_max = float(max_val)
        if color_max > 1000:
             # Round to nearest 100 to match the 13,200 style in the live sample
             color_max = round(color_max / 100) * 100
        
        # Custom discrete colorscale using exact 19 hex codes from live dashboard
        CUSTOM_MAP_COLORSCALE = [
            [0.00, "#e8eaeb"], [0.05, "#e8eaeb"],
            [0.05, "#dfe2e5"], [0.10, "#dfe2e5"],
            [0.10, "#d6d9df"], [0.15, "#d6d9df"],
            [0.15, "#ccd0d9"], [0.20, "#ccd0d9"],
            [0.20, "#c3c7d3"], [0.25, "#c3c7d3"],
            [0.25, "#b9bdcd"], [0.30, "#b9bdcd"],
            [0.30, "#b0b4c7"], [0.35, "#b0b4c7"],
            [0.35, "#a6abc1"], [0.40, "#a6abc1"],
            [0.40, "#9da2bb"], [0.45, "#9da2bb"],
            [0.45, "#9399b5"], [0.50, "#9399b5"],
            [0.50, "#8a8faf"], [0.55, "#8a8faf"],
            [0.55, "#8086a9"], [0.60, "#8086a9"],
            [0.60, "#777da3"], [0.65, "#777da3"],
            [0.65, "#6d739d"], [0.70, "#6d739d"],
            [0.70, "#646a97"], [0.75, "#646a97"],
            [0.75, "#5a6191"], [0.80, "#5a6191"],
            [0.80, "#51578b"], [0.85, "#51578b"],
            [0.85, "#474e85"], [0.90, "#474e85"],
            [0.90, "#3e447f"], [0.95, "#3e447f"],
            [0.95, "#343b79"], [1.00, "#343b79"]
        ]

        # Use the custom discrete colorscale for both yearly and monthly
        dynamic_colorscale = CUSTOM_MAP_COLORSCALE
        
        # Create custom tick values to show actual scale (like live: 0 and max)
        scale_ticks = [0, round(color_max)]
        
        print(f"DEBUG MAP: Using CUSTOM discrete colorscale - max_val: {max_val}, color_max: {color_max}")
        print(f"DEBUG MAP: Custom scale ticks: {scale_ticks}")
        
        # Use standardized map creation with dynamic colorscale
        fig = create_choropleth_map(
            locations=agg["iso_alpha"].tolist(),
            z_values=agg["value"].tolist(),
            colorscale=dynamic_colorscale,
            hover_text=agg["hover_text"].tolist(),
            selected_country=map_selected_country,
            selected_iso=selected_iso,
            other_isos=other_isos,
            height=500,
            zmin=0,
            zmax=color_max
        )

        # Restore the production bar (coloraxis_colorbar) and add customdata for click handling
        # Store Country name at idx 0 and ISO at idx 1
        # Use coloraxis='coloraxis' to link with layout settings
        fig.update_traces(
            showscale=True, 
            coloraxis='coloraxis',
            customdata=agg[["Country", "iso_alpha"]].values,
            selector=dict(name="countries")
        )
        
        # Ensure all traces have proper customdata for consistent click handling
        # This is important for selection highlight traces
        if map_selected_country:
            # Find the selected country's data for customdata
            selected_country_data = agg[agg["Country"] == map_selected_country]
            if not selected_country_data.empty:
                selected_customdata = [[map_selected_country, selected_iso]]
                
                # Update selection highlight traces with proper customdata
                for trace in fig.data:
                    if trace.name in ["selected_country_border", "inactive_countries"]:
                        # Set customdata for selection traces to ensure consistent click handling
                        if trace.name == "selected_country_border":
                            trace.customdata = selected_customdata
                        elif trace.name == "inactive_countries" and hasattr(trace, 'locations'):
                            # For inactive countries, set customdata for each location
                            inactive_customdata = []
                            for iso in trace.locations:
                                # Find the country name for this ISO
                                country_match = agg[agg["iso_alpha"] == iso]
                                if not country_match.empty:
                                    country_name = country_match.iloc[0]["Country"]
                                    inactive_customdata.append([country_name, iso])
                                else:
                                    inactive_customdata.append([iso, iso])  # Fallback
                            trace.customdata = inactive_customdata
        
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=100),
            coloraxis=dict(
                colorscale=dynamic_colorscale if isinstance(dynamic_colorscale, list) else "Blues",
                showscale=True,
                colorbar=dict(
                    title=dict(
                        text="", # Labelled via annotations
                        font=dict(size=12, color="#1f3b6f")
                    ),
                    tickfont=dict(size=10, color="#1f3b6f"),
                    orientation="h",
                    x=0.20,  # Safe starting position
                    xanchor="left",
                    y=-0.12,
                    yanchor="bottom",
                    len=0.70, # Controlled length for precise annotation mapping
                    thickness=12,
                    outlinewidth=1,
                    outlinecolor="#A0A0A0",
                    bordercolor="white",
                    bgcolor="rgba(255,255,255,0)",
                    showticklabels=False, # Use annotations instead for absolute control
                    ticks=""
                )
            ),
            annotations=[
                # Colorbar Title
                dict(
                    text="<b>Production</b><br><b>('000 b/d)</b>",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.19,  # Just left of the bar's start
                    y=-0.13,
                    xanchor="right",
                    font=dict(size=12, color="#1f3b6f")
                ),
                # Start Label (0)
                dict(
                    text="0",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.20,  # Start of the bar
                    y=-0.16, # Under the bar
                    font=dict(size=10, color="#1f3b6f")
                ),
                # End Label (Max Value)
                dict(
                    text=f"{int(color_max):,}",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.90,  # x(0.2) + len(0.7)
                    y=-0.16, # Under the bar
                    font=dict(size=10, color="#1f3b6f")
                )
            ],
            hoverlabel=dict(
                bgcolor="white",
                bordercolor="#ccc",
                font=dict(family="Arial", size=13, color="black"),
                align="left"
            )
        )
        # Apply requested zoom level
        if "mapbox" in fig.layout:
            fig.layout.mapbox.zoom = 0.8
        elif "geo" in fig.layout:
            # For geo-style maps, we can adjust the projection scale
            fig.layout.geo.projection.scale = 0.8
            
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
         Input("table-map-filter-active-store", "data"),
         Input("selected-bar-store", "data"),
         Input("current-submenu", "data")],
        prevent_initial_call=False
    )
    def update_breakdown(country, year, year_month, production_years, profiled, tab, selected_country_map, table_map_filter_active, selected_bar, current_submenu):
        """Update production breakdown chart - only loads data when page is active"""
        # Only load data if page is active
        if current_submenu != 'crude-overview':
            fig = go.Figure()
            fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return fig, ""
        
        # Clear selected_bar when switching tabs to start fresh
        if selected_bar:
            # Check if the selected_bar belongs to a different tab
            selected_bar_tab = selected_bar.get("tab")
            if selected_bar_tab and selected_bar_tab != tab:
                print(f"DEBUG BREAKDOWN: Clearing selected_bar from previous tab '{selected_bar_tab}' when switching to '{tab}'")
                selected_bar = None
            elif not selected_bar_tab:
                # If no tab info in selected_bar, clear it when switching to be safe
                print(f"DEBUG BREAKDOWN: Clearing selected_bar with no tab info when switching to '{tab}'")
                selected_bar = None
            else:
                print(f"DEBUG BREAKDOWN: Keeping selected_bar from same tab '{selected_bar_tab}'")
        
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
            # Only use map selection if table_map_filter_active is True
            # This allows the chart to keep using dropdown selection when user clicks same country again
            if selected_country_map and table_map_filter_active:
                country = [selected_country_map]
                original_country_selection = [selected_country_map]
                print(f"DEBUG: Map selection active for chart, country={selected_country_map}")
            elif selected_country_map and not table_map_filter_active:
                # Map selection exists but is not active for table - chart should use dropdown selection
                print(f"DEBUG: Map selection inactive for chart, using dropdown selection: {country}")
            
            if year is None:
                year = int(YEARS[-1]) if YEARS else 2024
            if tab is None:
                tab = "monthly"
            
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
                    height=520,
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
                
                # NEW LOGIC: Handle stream selection for yearly chart
                # For yearly view: If a single stream is selected, we should highlight it across ALL years
                # but NOT filter the data - keep all streams and all years, just adjust opacity
                is_single_stream_selected = False
                selected_stream = None
                if profiled and len(profiled) > 0:
                    # Check if all available streams are selected (default mode)
                    profiled_set = set(profiled)
                    available_set = set(available_streams) if available_streams else set()
                    
                    # If all streams are selected, don't filter (show all)
                    if profiled_set == available_set and len(available_set) > 0:
                        print(f"DEBUG BREAKDOWN YEARLY: All streams selected (default mode), showing all streams")
                        # Don't filter - show all streams at full opacity
                        is_single_stream_selected = False
                    elif len(profiled) == 1:
                        # Single stream selected: highlight this stream across all years
                        selected_stream = profiled[0]
                        is_single_stream_selected = True
                        print(f"DEBUG BREAKDOWN YEARLY: Single stream selected ({selected_stream}), will highlight across all years")
                        # IMPORTANT: Don't filter the data here - we'll handle highlighting via opacity later
                    else:
                        # Multiple streams selected (shouldn't happen in single selection mode, but handle it)
                        print(f"DEBUG BREAKDOWN YEARLY: Multiple streams selected ({len(profiled)} streams), showing all at full opacity")
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
                
                # FIXED LOGIC: Always show all years from 2006-2024 regardless of stream selection
                # This ensures the yearly chart always displays the full timeline
                all_years_list = [str(y) for y in range(2006, 2025)]
                all_streams_list = order_streams_list(agg["Stream"].unique().tolist(), tab="yearly")
                
                # Always create complete combination for yearly view (show all years)
                print(f"DEBUG BREAKDOWN YEARLY: Creating complete combo - years: {len(all_years_list)}, streams: {len(all_streams_list)}")
                
                # Create complete combination
                complete_combos = pd.DataFrame(list(itertools.product(all_years_list, all_streams_list)), 
                                               columns=["year", "Stream"])
                
                # Merge with actual data
                agg_complete = complete_combos.merge(agg, on=["year", "Stream"], how="left")
                agg_complete["value"] = agg_complete["value"].fillna(0)
                
                # Add Country column if it exists in agg
                if "Country" in agg.columns:
                    # For missing combinations, use the country filter variable
                    if country and len(country) > 0:
                        default_country = ", ".join(sorted(country)) if len(country) > 1 else country[0]
                    else:
                        default_country = ""
                    agg_complete["Country"] = agg_complete["Country"].fillna(default_country)
                
                print(f"DEBUG BREAKDOWN YEARLY: Complete data shape: {agg_complete.shape}")
                print(f"DEBUG BREAKDOWN YEARLY: Years in complete data: {sorted(agg_complete['year'].unique())}")
                print(f"DEBUG BREAKDOWN YEARLY: Streams in complete data: {agg_complete['Stream'].unique().tolist()}")
                print(f"DEBUG BREAKDOWN YEARLY: Non-zero records: {len(agg_complete[agg_complete['value'] > 0])}")
                
                # For X-axis to show all years, we need to ensure each year appears in the data
                # Plotly will only show categories that exist in the data, so we need to include all years
                # We'll filter out zero values for individual stream-year combos, but ensure each year
                # has at least one entry (even if it's a tiny value) so it appears on the X-axis
                
                agg_nonzero = agg_complete.copy()
                
                years_in_data = set(agg_nonzero["year"].unique())
                missing_years = [y for y in all_years_list if y not in years_in_data]
                
                print(f"DEBUG BREAKDOWN YEARLY: Years with data: {sorted(years_in_data)}")
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
                    # Create empty chart with all years on X-axis
                    first_stream = all_streams_list[0] if all_streams_list else "None"
                    empty_df = pd.DataFrame({
                        "year": all_years_list,
                        "value": [0.0001] * len(all_years_list),
                        "Stream": [first_stream] * len(all_years_list)
                    })
                    fig = px.bar(empty_df, x="year", y="value", color="Stream", 
                                labels={"value":"Production Volume ('000 b/d)", "year":"Year"})
                    fig.update_layout(
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
                        barmode="stack",  # Stack streams for each year
                        custom_data=["Stream"]
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
                        xaxis_title="Year",
                        yaxis_title="Production Volume ('000 b/d)",
                        barmode="stack",
                        plot_bgcolor="white",
                        paper_bgcolor="white"
                    )
                    return fig, title_text
                
                # NEW LOGIC: Apply point-level highlighting for yearly chart (single bar selection)
                # Check for both legend filter selection (profiled) and chart bar click (selected_bar)
                chart_selected_stream = None
                chart_selected_year = None
                if selected_bar and selected_bar.get("stream"):
                    # Chart bar click detected - extract stream and year from selected_bar
                    chart_selected_stream = selected_bar.get("stream")
                    chart_selected_year = selected_bar.get("month")  # For yearly, month contains the year
                    print(f"DEBUG BREAKDOWN YEARLY: Chart bar click detected for stream: {chart_selected_stream}, year: {chart_selected_year}")
                
                # Use chart selection if available, otherwise use legend filter selection
                active_stream = chart_selected_stream or selected_stream
                should_highlight = (is_single_stream_selected and selected_stream) or (chart_selected_stream is not None)
                
                if should_highlight and active_stream:
                    if chart_selected_stream and chart_selected_year:
                        # Chart bar click: point-level styling for single bar
                        print(f"DEBUG BREAKDOWN YEARLY: Applying point-level highlighting for {active_stream}-{chart_selected_year}")
                        
                        for trace in fig.data:
                            if trace.name == active_stream:
                                # Create point-level styling arrays
                                point_marker_colors = []
                                point_marker_line_widths = []
                                point_marker_line_colors = []
                                point_hover_infos = []
                                
                                # Get the stream color
                                stream_color = color_map.get(trace.name, '#808080')
                                
                                for i, year_val in enumerate(trace.x):
                                    if str(year_val) == str(chart_selected_year):
                                        # Highlight the clicked bar
                                        point_marker_colors.append(stream_color)
                                        point_marker_line_widths.append(2)
                                        point_marker_line_colors.append("black")
                                        point_hover_infos.append("all")
                                        print(f"DEBUG BREAKDOWN YEARLY: Highlighted {trace.name}-{year_val}")
                                    else:
                                        # Dim other bars in same stream
                                        point_marker_colors.append("rgba(200,200,200,0.3)")
                                        point_marker_line_widths.append(1)
                                        point_marker_line_colors.append("rgba(220,220,220,0.2)")
                                        point_hover_infos.append("skip")
                                
                                # Apply point-level styling
                                trace.marker.color = point_marker_colors
                                trace.marker.line.width = point_marker_line_widths
                                trace.marker.line.color = point_marker_line_colors
                                trace.hoverinfo = point_hover_infos
                            else:
                                # Dim entire trace for other streams
                                point_marker_colors = ["rgba(200,200,200,0.3)"] * len(trace.x)
                                point_marker_line_widths = [1] * len(trace.x)
                                point_marker_line_colors = ["rgba(220,220,220,0.2)"] * len(trace.x)
                                point_hover_infos = ["skip"] * len(trace.x)
                                
                                trace.marker.color = point_marker_colors
                                trace.marker.line.width = point_marker_line_widths
                                trace.marker.line.color = point_marker_line_colors
                                trace.hoverinfo = point_hover_infos
                                print(f"DEBUG BREAKDOWN YEARLY: Dimmed entire trace: {trace.name}")
                    else:
                        # Legend filter selection: trace-level styling (all years of selected stream)
                        print(f"DEBUG BREAKDOWN YEARLY: Applying trace-level highlighting for stream: {active_stream}")
                        for trace in fig.data:
                            if trace.name == active_stream:
                                # Highlight the selected stream
                                trace.marker.opacity = 1.0
                                print(f"DEBUG BREAKDOWN YEARLY: Set opacity=1.0 for trace: {trace.name}")
                            else:
                                # Dim all other streams
                                trace.marker.opacity = 0.3
                                print(f"DEBUG BREAKDOWN YEARLY: Set opacity=0.3 for trace: {trace.name}")
                else:
                    # Default mode: all streams at full opacity
                    print(f"DEBUG BREAKDOWN YEARLY: Default mode - all streams at full opacity")
                    for trace in fig.data:
                        trace.marker.opacity = 1.0
                
                # Add total labels on top of bars
                if not agg_for_chart.empty:
                    # Calculate totals per year for the labels
                    # Filter out the tiny placeholder values used for empty years
                    labels_df = agg_for_chart[agg_for_chart["value"] > 0.001].copy()
                    if labels_df.empty:
                        # Fallback for empty/placeholder state
                        labels_df = agg_for_chart.copy()
                        
                    totals = labels_df.groupby("year")["value"].sum().reset_index()
                    totals["year"] = totals["year"].astype(str)
                    
                    # Sort totals by year order to match X-axis
                    totals["year_cat"] = pd.Categorical(totals["year"], categories=years_sorted, ordered=True)
                    totals = totals.sort_values("year_cat")
                    
                    # Add total labels as a separate scatter trace
                    fig.add_trace(go.Scatter(
                        x=totals["year"],
                        y=totals["value"],
                        mode='text',
                        text=[f"{v:,.0f}" if v > 0.1 else "" for v in totals["value"]],
                        textposition='top center',
                        textfont=dict(size=11, color="#2c3e50"),
                        showlegend=False,
                        hoverinfo='skip',
                        name='Totals'
                    ))
                    print(f"DEBUG BREAKDOWN YEARLY: Added totals trace for labels")
                
                # Calculate max value for Y-axis scaling (use either ProductionDataValue or sum of bars)
                chart_totals_df = agg_for_chart[agg_for_chart["value"] > 0.001].copy()  # Filter out tiny placeholder values
                if len(chart_totals_df) > 0:
                    year_totals = chart_totals_df.groupby("year")["value"].sum().reset_index()
                    max_value = year_totals["value"].max() if len(year_totals) > 0 else 0
                else:
                    max_value = 0
                
                # Calculate Y-axis ticks (5 evenly spaced values from 0 to max)
                y_axis_max, y_axis_ticks = _calculate_yaxis_ticks(max_value)
                
                # Update layout to match monthly chart styling
                fig.update_layout(
                    xaxis_title="Year",
                    yaxis_title="Production Volume ('000 b/d)",
                    barmode="stack",
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    showlegend=False,  # Hide legend to match monthly chart
                    bargap=0.2,  # Same gap as monthly chart
                    bargroupgap=0.0,
                    hovermode="closest",
                    margin=dict(l=60, r=10, t=80, b=120),
                    height=520,
                    xaxis=dict(
                        type="category",
                        categoryorder="array",
                        categoryarray=years_sorted,
                        tickmode='array',
                        tickvals=years_sorted,
                        ticktext=years_sorted,
                        tickfont=dict(size=10, color="#2c3e50"),
                        titlefont=dict(size=12, color="#2c3e50"),
                        showgrid=False,  # Remove X-axis grid lines
                        gridwidth=0,
                        zeroline=False,  # Remove zero line
                        showline=False,
                        linewidth=0,
                        linecolor='#ced4da',
                        mirror=True
                    ),
                    yaxis=dict(
                        range=[0, y_axis_max * 1.05], # Add 5% buffer for labels
                        tickmode='array',
                        tickvals=y_axis_ticks,
                        ticktext=[f"{int(t):,}" for t in y_axis_ticks],
                        tickformat=',.0f',
                        showgrid=True,  # Keep Y-axis grid lines
                        gridcolor="#e0e0e0",
                        tickfont=dict(size=10, color="#2c3e50"),
                        titlefont=dict(size=12, color="#2c3e50"),
                        showline=False,
                        linewidth=0,
                        linecolor='#ced4da',
                        mirror=True
                    )
                )
                
                # Update hover templates to match monthly chart format
                for trace in fig.data:
                    stream_name = trace.name
                    # Build customdata for hover template
                    customdata_list = []
                    if len(trace.x) > 0:
                        for year_val in trace.x:
                            # Match by Stream and year
                            matching_rows = agg_for_chart[
                                (agg_for_chart["Stream"] == stream_name) & 
                                (agg_for_chart["year"] == str(year_val))
                            ]
                            
                            if not matching_rows.empty and "Country" in matching_rows.columns:
                                country_val = matching_rows.iloc[0]["Country"]
                            else:
                                country_val = ""
                            
                            # Add to customdata: [Stream] (matching reference file format)
                            customdata_list.append([stream_name])
                    
                    # Set customdata
                    trace.customdata = customdata_list if customdata_list else None
                    
                    # Create custom hover template
                    trace.hovertemplate = (
                        "<b>Year:</b> %{x}<br>"
                        "<b>Stream Name:</b> %{customdata[0]}<br>"
                        "<b>Country:</b> " + country_val + "<br>"
                        "<b>Production Volume:</b> %{y:,.0f} ('000 b/d)<extra></extra>"
                    )
                
                fig.update_layout(clickmode='event')
                return fig, title_text
            else:
                # Monthly view: Handle stream selection behavior as per requirements
                print(f"DEBUG BREAKDOWN MONTHLY: production_years={production_years}, country={country}")
                print(f"DEBUG BREAKDOWN MONTHLY: original_country_selection={original_country_selection}")
                
                # Default country/year handling
                if not country:
                    country = ["Russia"] if "Russia" in COUNTRIES else COUNTRIES[:1]
                if isinstance(country, str):
                    country = [country]
                
                # Resolve year selection - expand "(All)" to all available years
                resolved_years = _resolve_years_selection(production_years)
                if resolved_years:
                    selected_years = [str(y) for y in resolved_years]
                    print(f"DEBUG BREAKDOWN MONTHLY: Selected years={selected_years}, countries={country}")
                else:
                    # No years selected - show empty chart instead of defaulting
                    print(f"DEBUG BREAKDOWN MONTHLY: No years selected, showing empty chart")
                    fig = go.Figure()
                    fig.add_annotation(
                        text="No years selected. Please select at least one year from 'Year of Date' filter.",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=14, color='#7f8c8d')
                    )
                    fig.update_layout(
                        height=520,
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        xaxis=dict(showgrid=False, showticklabels=False),
                        yaxis=dict(showgrid=False, showticklabels=False)
                    )
                    return fig, title_text
                
                if BAR_LONG_MONTHLY.empty or "year" not in BAR_LONG_MONTHLY.columns:
                    fig = go.Figure()
                    fig.add_annotation(text="No monthly data available.", xref="paper", yref="paper",
                                    x=0.5, y=0.5, showarrow=False,
                                    font=dict(size=14, color='#7f8c8d'))
                    fig.update_layout(height=520, plot_bgcolor='white', paper_bgcolor='white')
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
                    fig.update_layout(height=520, plot_bgcolor='white', paper_bgcolor='white')
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
                
                # NEW LOGIC: Handle stream selection based on profiled streams
                # For monthly view: If a single stream is selected, we need to isolate it properly
                highlight_stream = None
                highlight_month = None
                highlight_year = None
                is_single_stream_selected = False
                
                if profiled and len(profiled) > 0:
                    profiled_set = set(str(p) for p in profiled)
                    available_set = set(str(s) for s in available_monthly_streams)
                    
                    # Check if we have a specific stream selected
                    if len(profiled) == 1:
                        # Single stream selected: we need to determine if this is for a specific month
                        selected_stream = str(profiled[0]).strip()
                        
                        # Check if the selected stream exists in our data
                        if selected_stream in available_set:
                            # For monthly chart, when a single stream is selected,
                            # we should show ALL months for ALL years for that stream
                            # but highlight/dim based on the profiled selection
                            highlight_stream = selected_stream
                            is_single_stream_selected = True
                            print(f"DEBUG BREAKDOWN MONTHLY: Single stream selected ({highlight_stream}), will highlight this stream across all months/years")
                    else:
                        # Multiple streams selected (shouldn't happen, but handle it)
                        print(f"DEBUG BREAKDOWN MONTHLY: Multiple streams selected ({len(profiled)}), showing all at full opacity")
                        highlight_stream = None
                else:
                    # If no stream selected, show all streams at full opacity (default mode)
                    print(f"DEBUG BREAKDOWN MONTHLY: No stream selected, showing all streams at full opacity (default mode)")
                    highlight_stream = None
                
                # If no rows or all values are zero, show a friendly message
                if agg.empty or (agg["value"].fillna(0).sum() <= 0):
                    print(f"DEBUG BREAKDOWN MONTHLY: No usable data (rows={len(agg)}, total={agg['value'].fillna(0).sum() if not agg.empty else 0})")
                    fig = go.Figure()
                    fig.add_annotation(text="No monthly data available for selected filters.",
                                    xref="paper", yref="paper",
                                    x=0.5, y=0.5, showarrow=False,
                                    font=dict(size=14, color='#7f8c8d'))
                    fig.update_layout(height=520, plot_bgcolor='white', paper_bgcolor='white')
                    return fig, title_text
                
                # Stream color map
                color_map = get_stream_color_map("monthly")
                
                # Ensure data is sorted by year and month (in correct month order)
                # This ensures months appear in the right order and only months with data are shown
                if not agg.empty:
                    # Normalize names for robust mapping and sorting
                    agg["month"] = agg["month"].astype(str).str.strip()
                    agg["Stream"] = agg["Stream"].astype(str).str.strip()
                    month_to_num = {name: idx+1 for idx, name in enumerate(month_names)}
                    agg["month_num"] = agg["month"].map(month_to_num)
                    agg = agg.sort_values(["year", "month_num"]).drop(columns=["month_num"])
                    
                    # Convert month to categorical with only the months that have data
                    available_months = agg["month"].unique().tolist()
                    months_ordered = [m for m in month_names if m in available_months]
                    agg["month"] = pd.Categorical(agg["month"], categories=months_ordered, ordered=True)
                    print(f"DEBUG BREAKDOWN MONTHLY: Data normalized and sorted. Month categorical with {len(months_ordered)} months")
                
                # Get unique years - each will be a separate subplot
                unique_years = sorted(agg["year"].unique().tolist()) if not agg.empty else []
                
                if not unique_years:
                    # No years, return empty chart
                    fig = go.Figure()
                    fig.add_annotation(text="No monthly data available.", xref="paper", yref="paper",
                                    x=0.5, y=0.5, showarrow=False,
                                    font=dict(size=14, color='#7f8c8d'))
                    fig.update_layout(height=520, plot_bgcolor='white', paper_bgcolor='white')
                    return fig, title_text
                
                # 1. Calculate Global Stream Ordering and Max Stacked Total
                # We need a consistent order across all subplots, and a Y-axis that fits the tallest stack
                if not agg.empty:
                    # Global Stream Order: Highest total volume at the bottom
                    global_stream_totals = agg.groupby("Stream")["value"].sum().reset_index()
                    global_ordered_streams = global_stream_totals.sort_values("value", ascending=False)["Stream"].tolist()
                    print(f"DEBUG BREAKDOWN MONTHLY: Global ordered streams: {global_ordered_streams}")
                    
                    # Max Stacked Total: For Y-axis range
                    # Group by year and month to get the total stacked height for each column
                    monthly_totals_test = agg.groupby(["year", "month"])["value"].sum().reset_index()
                    max_stacked_value = monthly_totals_test["value"].max() if not monthly_totals_test.empty else 0
                    print(f"DEBUG BREAKDOWN MONTHLY: Max stacked bar height: {max_stacked_value}")
                else:
                    global_ordered_streams = []
                    max_stacked_value = 0

                # Calculate Y-axis ticks (5-6 evenly spaced values from 0 to max)
                y_axis_max, y_axis_ticks = _calculate_yaxis_ticks(max_stacked_value)
                
                # Calculate bar width to ensure all bars are equal size across all years
                max_months = 0
                for year_val in unique_years:
                    year_data = agg[agg["year"] == year_val]
                    if not year_data.empty:
                        num_months_for_year = len(year_data["month"].unique())
                        max_months = max(max_months, num_months_for_year)
                
                if max_months == 0:
                    max_months = 12
                    
                monthly_bargap = 0.15  # Increased gap for better visual spacing
                
                # 2. Add Traces for each Subplot and Stream
                # Create subplots - one column per year
                fig = make_subplots(
                    rows=1,
                    cols=len(unique_years),
                    subplot_titles=unique_years,
                    shared_yaxes=True,
                    horizontal_spacing=0.02  # Added margin between subplots
                )
                
                # We add streams in the order of global_ordered_streams (Highest volume first -> Bottom of stack)
                for year_idx, year_val in enumerate(unique_years):
                    year_data = agg[agg["year"] == year_val].copy()
                    if year_data.empty:
                        continue
                    
                    # Months ordering for this year
                    year_months = year_data["month"].unique().tolist()
                    year_months_ordered = [m for m in month_names if m in year_months]
                    
                    for stream in global_ordered_streams:
                        stream_data = year_data[year_data["Stream"] == stream].copy()
                        if stream_data.empty:
                            continue # Skip if this stream has no data in this specific year
                        
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
                            stream_color = get_stream_color(stream, global_ordered_streams, tab="monthly")
                        
                        # Point-level styling (Highlighting, Opacity)
                        point_marker_colors = []
                        point_marker_line_widths = []
                        point_marker_line_colors = []
                        point_hover_infos = []
                        customdata_list = []
                        any_point_highlighted = False
                        
                        # Trace/Selection Identifiers
                        t_stream = str(stream).strip().lower()
                        t_year = str(year_val).strip()
                        
                        # Selection context
                        h_stream = str(selected_bar.get("stream")).strip().lower() if selected_bar and selected_bar.get("stream") else None
                        h_month = str(selected_bar.get("month")).strip().lower() if selected_bar and selected_bar.get("month") else None
                        h_year = str(selected_bar.get("year")).strip() if selected_bar and selected_bar.get("year") else None
                        
                        # Determine selection type
                        if h_stream:
                            selection_type = "chart_click"
                        elif profiled and len(profiled) == 1:
                            h_stream = str(profiled[0]).strip().lower()
                            selection_type = "legend_filter"
                        else:
                            selection_type = "none"

                        for _, row in stream_data.iterrows():
                            curr_month = str(row["month"]).strip().lower()
                            is_this_point_highlighted = True
                            is_at_intersection = False
                            
                            if selection_type == "chart_click":
                                matches_stream = (t_stream == h_stream)
                                if h_month and h_year:
                                    matches_column = (t_year == h_year and curr_month == h_month)
                                    is_this_point_highlighted = matches_stream and matches_column
                                    is_at_intersection = matches_stream and matches_column
                                elif h_year and not h_month:
                                    matches_column = (t_year == h_year)
                                    is_this_point_highlighted = matches_stream and matches_column
                                    is_at_intersection = matches_stream and matches_column
                                else:
                                    is_this_point_highlighted = matches_stream
                            elif selection_type == "legend_filter":
                                is_this_point_highlighted = (t_stream == h_stream)
                            
                            if is_this_point_highlighted:
                                any_point_highlighted = True
                                point_marker_colors.append(stream_color)
                                if is_at_intersection:
                                    point_marker_line_widths.append(2)
                                    point_marker_line_colors.append("black")
                                else:
                                    point_marker_line_widths.append(1)
                                    point_marker_line_colors.append("white")
                                point_hover_infos.append("all")
                            else:
                                point_marker_colors.append("rgba(200,200,200,0.3)")
                                point_marker_line_widths.append(1)
                                point_marker_line_colors.append("rgba(220,220,220,0.2)")
                                point_hover_infos.append("skip")
                                
                            # Customdata for hover: [Country, Year, Stream]
                            country_val = row["Country"] if "Country" in row else ""
                            customdata_list.append([country_val, str(year_val), stream])

                        # Add the trace to the subplot
                        fig.add_trace(
                            go.Bar(
                                x=stream_data["month"],
                                y=stream_data["value"],
                                name=stream,
                                marker=dict(
                                    color=point_marker_colors,
                                    line=dict(width=point_marker_line_widths, color=point_marker_line_colors),
                                ),
                                legendgroup=stream,
                                showlegend=False,
                                hoverinfo=point_hover_infos,
                                customdata=customdata_list if customdata_list else None,
                                hovertemplate=(
                                    "<b>Month:</b> %{x}<br>"
                                    "<b>Country:</b> %{customdata[0]}<br>"
                                    "<b>Stream Name:</b> %{customdata[2]}<br>"
                                    "<b>Year:</b> %{customdata[1]}<br>"
                                    "<b>Production Volume:</b> %{y:,.0f} ('000 b/d)<extra></extra>"
                                )
                            ),
                            row=1,
                            col=year_idx + 1
                        )

                # 3. Finalize Layout and Domain Spacing
                # Update subplot domains so each month gets equal visual space (Crucial for multi-year view)
                total_months = 0
                year_month_counts = {}
                for year_val in unique_years:
                    year_data = agg[agg["year"] == year_val]
                    num_months = len(year_data["month"].unique()) if not year_data.empty else 0
                    year_month_counts[year_val] = num_months
                    total_months += num_months
                
                domain_start = 0.0
                available_width = 1.0 - (max(0, len(unique_years) - 1) * 0.02)
                domain_width_per_month = available_width / total_months if total_months > 0 else available_width / len(unique_years)
                
                subplot_boundaries = []
                
                for year_idx, year_val in enumerate(unique_years):
                    num_months_for_year = year_month_counts.get(year_val, 0)
                    subplot_domain_width = num_months_for_year * domain_width_per_month if total_months > 0 else 1.0 / len(unique_years)
                    domain_end = domain_start + subplot_domain_width
                    
                    # Store for separator lines
                    subplot_boundaries.append((domain_start, domain_end))
                    
                    # Update X-axis for this subplot
                    year_data = agg[agg["year"] == year_val]
                    year_months_ordered = [m for m in month_names if m in year_data["month"].unique().tolist()] if not year_data.empty else []
                    
                    fig.update_xaxes(
                        tickangle=-90,
                        type="category",
                        categoryorder="array",
                        categoryarray=year_months_ordered,
                        tickfont=dict(size=10, color="#2c3e50"),
                        domain=[domain_start, domain_end],
                        title_text="",  # No "Month" label
                        showgrid=False,
                        zeroline=False,
                        row=1, col=year_idx + 1
                    )
                    
                    # Update Y-axis for each subplot
                    yaxis_key = f"yaxis{year_idx+1}" if year_idx > 0 else "yaxis"
                    if yaxis_key in fig.layout:
                        fig.layout[yaxis_key].update(
                            range=[0, y_axis_max * 1.05], # 5% buffer for highlight borders
                            tickmode='array',
                            tickvals=y_axis_ticks,
                            ticktext=[f"{int(t):,}" for t in y_axis_ticks],
                            tickformat=',.0f',
                            showgrid=True,
                            gridcolor="#e0e0e0",
                            title_text="Production Volume ('000 b/d)" if year_idx == 0 else "",
                            tickfont=dict(size=10, color="#2c3e50"),
                            titlefont=dict(size=12, color="#2c3e50")
                        )
                    
                    domain_start = domain_end + 0.02 # horizontal_spacing = 0.02
                
                # Add vertical separation lines
                if len(subplot_boundaries) > 1:
                    shapes = []
                    for i in range(len(subplot_boundaries) - 1):
                        line_x = (subplot_boundaries[i][1] + subplot_boundaries[i+1][0]) / 2
                        shapes.append(dict(
                            type="line", xref="paper", yref="paper",
                            x0=line_x, x1=line_x, y0=0.05, y1=0.95,
                            line=dict(color="#ced4da", width=1)
                        ))
                    fig.update_layout(shapes=shapes)
                
                # Update subplot title fonts
                if fig.layout.annotations:
                    for annotation in fig.layout.annotations:
                        if hasattr(annotation, 'text') and annotation.text in [str(y) for y in unique_years]:
                            annotation.font = dict(size=14, color="#2c3e50", family="Arial, sans-serif")
                
                if not fig.data:
                    fig = go.Figure()
                    fig.add_annotation(text="No monthly data available for selected filters.",
                                    xref="paper", yref="paper",
                                    x=0.5, y=0.5, showarrow=False,
                                    font=dict(size=14, color='#7f8c8d'))
                    fig.update_layout(height=520, plot_bgcolor='white', paper_bgcolor='white')
                
                fig.update_layout(
                    barmode="stack",
                    bargap=monthly_bargap,
                    bargroupgap=0.0,
                    clickmode='event'
                )
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
                height=520,
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
         Input("table-map-filter-active-store", "data"),
         Input("current-submenu", "data")],
        [State("profiled-streams", "options")],
        prevent_initial_call=False
    )
    def filter_table(stream, ci, api, sulfur, year, year_month, country, tab, profiled_streams, selected_country_map, table_map_filter_active, current_submenu, profiled_streams_options):
        """Filter and update data table - only loads data when page is active"""
        # Only load data if page is active
        if current_submenu != 'crude-overview':
            return [], []
        
        # Ensure data is loaded
        _ensure_data_loaded()
        
        # Map selection overrides dropdown if present AND active for table
        if selected_country_map and table_map_filter_active:
            country = [selected_country_map]
        else:
            country = _resolve_countries_selection(country)
        
        # Set defaults if None
        if tab is None:
            tab = "monthly"
        
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
        # Map selection applies to both tabs when active
        # For Monthly tab, dropdown country filter applies when map selection is not active
        print(f"DEBUG FILTER_TABLE: selected_country_map={selected_country_map}, table_map_filter_active={table_map_filter_active}, tab={tab}, country={country}")
        if selected_country_map and table_map_filter_active:
            # Map selection overrides everything - apply to both tabs
            # Ensure we use the full country name, not ISO code
            country_name = _map_iso_to_country_name(selected_country_map)
            if "Country" in df.columns:
                df = df[df["Country"] == country_name]
                print(f"DEBUG FILTER_TABLE: Applied map selection filter for {tab} tab: {country_name} (from {selected_country_map}), rows after filter: {len(df)}")
        elif selected_country_map and not table_map_filter_active:
            # Map country is selected but table filter is inactive (user clicked same country twice)
            # Show all data in table while keeping chart/legend filtered
            print(f"DEBUG FILTER_TABLE: Map country selected ({selected_country_map}) but table filter inactive, showing all data: {len(df)} rows")
        else:
            # No map selection active or table filter inactive
            # For initial load: always show all data regardless of dropdown selection
            # For monthly tab: only apply dropdown filter if user has interacted with map before
            # This prevents filtering on initial load with default dropdown values
            print(f"DEBUG FILTER_TABLE: No country filter applied for {tab} tab, showing all data: {len(df)} rows")
        
        # Additional metadata filters (only for monthly)
        if tab == "monthly":
            # These were duplicated above, removing the duplicate
            pass
        
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
            df_display = df_display.fillna("")
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
                        val_str = str(value).strip().lower()
                        if val_str == "nan" or val_str == "none" or val_str == "":
                            record[year_col] = ""
                            continue
                            
                        numeric_value = float(str(value).replace(",", ""))
                        if math.isnan(numeric_value):
                             record[year_col] = ""
                        else:
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
        [State("crude-main-tabs", "value"),
         State("crude-country-dropdown", "value"),
         State("selected-country-map-store", "data"),
         State("table-map-filter-active-store", "data")],
        prevent_initial_call=True
    )
    def export_map_data_to_csv(n_clicks, tab, country_dropdown, selected_country_map, table_map_filter_active):
        if n_clicks is None or n_clicks <= 0:
            return no_update
            
        try:
            # Default to yearly map if tab is None
            if tab is None:
                tab = "monthly"
                
            if tab == "yearly":
                print("DEBUG: Exporting YEARLY map data (raw_export=True)")
                df = load_yearly_map_from_db(raw_export=True)
                filename = "world_crude_production_yearly.csv"
            else:
                # monthly
                print("DEBUG: Exporting MONTHLY map data (raw_export=True)")
                df = load_monthly_map_from_db(raw_export=True)
                filename = "world_crude_production_monthly.csv"
            
            # Apply Country Filtering to Map Data Export
            if df is not None and not df.empty:
                df.columns = df.columns.str.strip()
                
                # CHECK FOR INITIAL LOAD: If only default "Russia" is selected and no map click, download all
                is_initial_load = (selected_country_map is None and country_dropdown == ["Russia"])
                
                if is_initial_load:
                    print("DEBUG MAP EXPORT: Initial load detected (default Russia only), exporting all countries.")
                else:
                    # Determine target country from map selection or dropdown
                    if selected_country_map and table_map_filter_active:
                        target_country = _map_iso_to_country_name(selected_country_map)
                        if "country" in df.columns:
                            df = df[df["country"] == target_country]
                        elif "Country" in df.columns:
                            df = df[df["Country"] == target_country]
                        print(f"DEBUG MAP EXPORT: Filtered for map selection: {target_country}")
                    elif country_dropdown:
                        dropdown_countries = _resolve_countries_selection(country_dropdown)
                        if dropdown_countries and len(dropdown_countries) > 0:
                            if "country" in df.columns:
                                df = df[df["country"].isin(dropdown_countries)]
                            elif "Country" in df.columns:
                                df = df[df["Country"].isin(dropdown_countries)]
                            print(f"DEBUG MAP EXPORT: Filtered for dropdown: {dropdown_countries}")
            
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
         State("crude-main-tabs", "value"),
         State("selected-country-map-store", "data")],
        prevent_initial_call=True
    )
    def export_chart_data(n_clicks, country, production_years, profiled, tab, selected_country_map):
        """
        Export chart data to CSV based on the active tab (Yearly/Monthly) and applied filters.
        Re-executes the query to fetch raw data (Long Format) as requested.
        """
        print(f"DEBUG EXPORT CHART: Triggered. n_clicks={n_clicks}, tab={tab}")
        if n_clicks is None or n_clicks <= 0:
            return no_update
            
        try:
            # Map selection overrides dropdown if present
            if selected_country_map:
                country = [selected_country_map]
            else:
                country = _resolve_countries_selection(country)
                
            print(f"DEBUG EXPORT CHART: Resolved country={country}")
            
            if tab is None:
                tab = "monthly"
            
            # ==========================================
            # YEARLY CHART EXPORT
            # ==========================================
            if tab == "yearly":
                yearly_query = """
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
                rows = execute_query(yearly_query)
                if not rows:
                     print("DEBUG EXPORT CHART: No yearly data returned from query.")
                     return no_update
                
                df = pd.DataFrame(rows)
                df.columns = df.columns.str.strip()
                
                if not df.empty:
                    # Filter by Country
                    if country:
                         if "Country" in df.columns:
                            df = df[df["Country"].isin(country)]
                    
                    # Filter by Profiled Streams
                    if profiled and len(profiled) > 0:
                        if "CrudeOil" in df.columns:
                            df = df[df["CrudeOil"].isin(profiled)]
                    
                    filename = "crude_production_breakdown_yearly.csv"
                    print(f"DEBUG EXPORT CHART: Exporting {len(df)} rows to {filename}")
                    return dcc.send_data_frame(df.to_csv, filename, index=False)
            
            # ==========================================
            # MONTHLY CHART EXPORT
            # ==========================================
            else:
                monthly_query = """
            SELECT  
                EXTRACT(YEAR FROM date) AS "Year of Date",
                TO_CHAR(date, 'FMMonth') AS "Month of Date",
                country AS "Country",
                stream_name AS "Stream Name",
                value AS "Value"
            FROM t_wcod_monthly_stream_production where stream_name not in ('Total')
            ORDER BY date DESC, stream_name;
        """
                rows = execute_query(monthly_query)
                if not rows:
                     print("DEBUG EXPORT CHART: No monthly data returned from query.")
                     return no_update
                
                df = pd.DataFrame(rows)
                df.columns = df.columns.str.strip()
                
                if not df.empty:
                    # Filter by Country
                    if country:
                        if "Country" in df.columns:
                            df = df[df["Country"].isin(country)]
                    
                    # Filter by Year (production-year-dropdown)
                    selected_years = _resolve_years_selection(production_years)
                    print(f"DEBUG EXPORT CHART: Selected years={selected_years}")
                    
                    # Default if no years selected
                    if not selected_years:
                        if PRODUCTION_YEARS:
                             selected_years = [int(PRODUCTION_YEARS[-1])]
                        else:
                             selected_years = [2024]
                    
                    if "Year of Date" in df.columns:
                        # Convert to int for comparison
                        df["year_int"] = pd.to_numeric(df["Year of Date"], errors="coerce").fillna(0).astype(int)
                        df = df[df["year_int"].isin(selected_years)]
                        df = df.drop(columns=["year_int"])
                    
                    filename = "crude_production_breakdown_monthly.csv"
                    print(f"DEBUG EXPORT CHART: Exporting {len(df)} rows to {filename}")
                    return dcc.send_data_frame(df.to_csv, filename, index=False)
            
            return no_update

        except Exception as e:
            print(f"Error exporting chart data: {e}")
            import traceback
            traceback.print_exc()
            return no_update

    @dash_app.callback(
        Output("download-table-csv", "data"),
        Input("btn-export-table-csv", "n_clicks"),
        [State("filter-stream", "value"),
         State("filter-ci", "value"),
         State("filter-api", "value"),
         State("filter-sulfur", "value"),
         State("crude-country-dropdown", "value"),
         State("crude-main-tabs", "value"),
         State("profiled-streams", "value"),
         State("selected-country-map-store", "data"),
         State("table-map-filter-active-store", "data"),
         State("profiled-streams", "options")],
        prevent_initial_call=True
    )
    def export_table_data(n_clicks, stream, ci, api, sulfur, country, tab, profiled_streams, selected_country_map, table_map_filter_active, profiled_streams_options):
        """
        Export table data to CSV based on the active tab (Yearly/Monthly) and applied filters.
        Re-executes the query to fetch raw data (Long Format) as requested.
        """
        print(f"DEBUG EXPORT TABLE: Triggered. n_clicks={n_clicks}, tab={tab}")
        if n_clicks is None or n_clicks <= 0:
            return no_update
        
        try:
            # Default to yearly if tab is None
            if tab is None:
                tab = "monthly"

            # ==========================================
            # YEARLY EXPORT
            # ==========================================
            if tab == "yearly":
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
            ORDER BY a.country_name ASC, a.crude_name ASC;
        """
                rows = execute_query(yearly_query)
                if not rows:
                    print("DEBUG EXPORT TABLE: No yearly data returned from query.")
                    return no_update
                
                df = pd.DataFrame(rows)
                df.columns = df.columns.str.strip()
                
                # Apply Filters to Yearly Data
                
                # 1. Country Filter (Map selection or Dropdown)
                # CHECK FOR INITIAL LOAD: If only default "Russia" is selected and no map click, download all
                is_initial_load = (selected_country_map is None and country == ["Russia"])
                
                if is_initial_load:
                    print("DEBUG EXPORT TABLE: Initial load detected (default Russia only), exporting all yearly data.")
                elif selected_country_map and table_map_filter_active:
                    country_name = _map_iso_to_country_name(selected_country_map)
                    if "Country" in df.columns:
                        df = df[df["Country"] == country_name]
                elif country:
                    dropdown_countries = _resolve_countries_selection(country)
                    if dropdown_countries and len(dropdown_countries) > 0:
                        if "Country" in df.columns:
                            df = df[df["Country"].isin(dropdown_countries)]
                
                # 2. Text Search Filter (Stream Name)
                if stream and str(stream).strip():
                    stream_val = str(stream).strip()
                    if "CrudeOil" in df.columns: # Query returns CrudeOil
                        df = df[df["CrudeOil"].astype(str).str.contains(re.escape(stream_val), case=False, na=False)]
                
                # 3. Profiled Stream Filter (Checklist) - Only if text search is NOT active
                if not (stream and str(stream).strip()):
                    if profiled_streams and len(profiled_streams) == 1:
                        selected_stream = profiled_streams[0]
                        # Check availability logic similar to UI
                        available_streams = [opt.get("value") for opt in (profiled_streams_options or []) if opt.get("value")]
                        if available_streams and len(available_streams) > 1 and len(profiled_streams) < len(available_streams):
                            if "CrudeOil" in df.columns:
                                df = df[df["CrudeOil"] == selected_stream]
                
                filename = "global_crude_production_breakdown_yearly.csv"
                
                print(f"DEBUG EXPORT TABLE: Exporting {len(df)} rows to {filename}")
                return dcc.send_data_frame(df.to_csv, filename, index=False)

            # ==========================================
            # MONTHLY EXPORT
            # ==========================================
            else:
                monthly_query = """
            SELECT     
                m.country_long_name AS "Country",
                c.crude_name AS "Crude",
                c.ci_rank,
                c.api,
                c.sulfur_pct,
                l.bsp_link AS profile_url,
                EXTRACT(YEAR FROM a.date) AS "Year of Date",
                TO_CHAR(a.date, 'FMMonth') AS "Month of Date",
                a.value AS "Value"
            FROM t_wcod_monthly_stream_production a

            -- Latest crude master data
            LEFT JOIN (
                SELECT DISTINCT ON (crude_id) 
                    crude_id,
                    country_id,
                    crude_name,
                    ci_rank,
                    api,
                    sulfur_pct
                FROM fact_wcod_crude
                ORDER BY crude_id, yr DESC
            ) c 
                ON a.crude_id = c.crude_id

            -- Country Name
            LEFT JOIN dim_country m
                ON c.country_id = m.dim_country_id

            -- Profile URL
            LEFT JOIN fact_wcod_crude_bsp_links l
                ON a.crude_id = l.crude_id
            ORDER BY m.country_long_name ASC, c.crude_name ASC;
        """
                rows = execute_query(monthly_query)
                if not rows:
                    print("DEBUG EXPORT TABLE: No monthly data returned from query.")
                    return no_update

                df = pd.DataFrame(rows)
                df.columns = df.columns.str.strip()
                
                # Rename columns from query to match UI expectations if needed, but user asked for "same as query return values"
                # The query returns: Crude, ci_rank, api, sulfur_pct, profile_url, Year of Date, Month of Date, Value
                # Filter logic uses: CI Rank, API, Sulfur. Need to ensure mapping or adjust filter logic.
                # Let's map for filtering purposes, but keep original for export if possible?
                # Actually, the user wants "same header values" from query.
                # So I should filter based on the query columns: ci_rank, api, sulfur_pct.
                
                # 1. Text Search Filter
                if stream and str(stream).strip():
                    stream_val = str(stream).strip()
                    if "Crude" in df.columns:
                        df = df[df["Crude"].astype(str).str.contains(re.escape(stream_val), case=False, na=False)]
                
                # 2. Metadata Filters (CI, API, Sulfur)
                def sanitize(values):
                    if not values: return []
                    return [v for v in values if v and v not in ("(All)", "ALL")]

                # CI Rank
                ci_vals = sanitize(ci)
                if ci_vals and "ci_rank" in df.columns:
                    df = df[df["ci_rank"].isin(ci_vals)]
                
                # API
                api_vals = sanitize(api)
                if api_vals and "api" in df.columns:
                     # Use helper classify_api_value
                    df = df[df["api"].apply(lambda v: classify_api_value(v) in api_vals)]
                
                # Sulfur
                sulfur_vals = sanitize(sulfur)
                if sulfur_vals and "sulfur_pct" in df.columns:
                    # Use helper classify_sulfur_value
                    df = df[df["sulfur_pct"].apply(lambda v: classify_sulfur_value(v) in sulfur_vals)]
                    
                # 3. Country Filter
                # CHECK FOR INITIAL LOAD: If only default "Russia" is selected and no map click, download all
                is_initial_load = (selected_country_map is None and country == ["Russia"])
                
                if is_initial_load:
                    print("DEBUG EXPORT TABLE: Initial load detected (default Russia only), exporting all monthly data.")
                elif selected_country_map and table_map_filter_active:
                    country_name = _map_iso_to_country_name(selected_country_map)
                    if "Country" in df.columns:
                        df = df[df["Country"] == country_name]
                        print(f"DEBUG EXPORT TABLE: Filtered by map country: {country_name}")
                elif country:
                    dropdown_countries = _resolve_countries_selection(country)
                    if dropdown_countries and len(dropdown_countries) > 0:
                        if "Country" in df.columns:
                            df = df[df["Country"].isin(dropdown_countries)]
                            print(f"DEBUG EXPORT TABLE: Filtered by dropdown countries: {dropdown_countries}")
                
                
                filename = "global_crude_production_breakdown_monthly.csv"
                print(f"DEBUG EXPORT TABLE: Exporting {len(df)} rows to {filename}")
                return dcc.send_data_frame(df.to_csv, filename, index=False)

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
