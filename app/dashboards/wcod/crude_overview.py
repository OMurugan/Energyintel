def format_with_link(value, link):
    if value is None:
        return ""
    text = str(value)
    if not link or not isinstance(link, str) or not link.strip():
        return text
    if not text.strip():
        return text
    # Use markdown format for Dash DataTable
    safe_text = text.strip()
    safe_link = link.strip()
    # Escape special markdown characters in text
    safe_text = safe_text.replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)')
    return f'[{safe_text}]({safe_link})'
"""
Crude Overview View
Replicates Energy Intelligence WCoD Crude Overview functionality
Monthly World Crude Production Dashboard - Based on Tableau source
"""
from dash import dcc, html, Input, Output, State, dash_table, dash, no_update
import dash.dependencies as dd
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os
import re
import itertools
import math
import html as html_lib
from app import create_dash_app

# Define data paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'crude_overview')
BAR_YEARLY_CSV = os.path.join(DATA_DIR, 'Yearly Bar - Production_data.csv')
BAR_MONTHLY_CSV = os.path.join(DATA_DIR, 'Monthly Bar - Production_data.csv')
MAP_YEARLY_CSV = os.path.join(DATA_DIR, 'Yearly World Map_data.csv')
MAP_MONTHLY_CSV = os.path.join(DATA_DIR, 'Monthly World Map_data.csv')
TABLE_YEARLY_CSV = os.path.join(DATA_DIR, 'Table - Country Production_data.csv')
TABLE_MONTHLY_CSV = os.path.join(DATA_DIR, 'Table - monthly crude production_data.csv')
YEARLY_GRADES_CSV = os.path.join(DATA_DIR, 'Yearly List of grades for selected country_data.csv')
MONTHLY_GRADES_CSV = os.path.join(DATA_DIR, 'Monthly List of grades for selected country_data.csv')

# Data loading functions
def load_yearly_bar():
    """Load yearly bar data from Yearly Bar - Production_data.csv"""
    try:
        df = pd.read_csv(BAR_YEARLY_CSV, encoding="utf-8", sep=",")
        df.columns = df.columns.str.strip()
        print(f"DEBUG: Yearly bar data columns: {df.columns.tolist()}")
        print(f"DEBUG: Yearly bar data sample:\n{df.head(3)}")
        
        # Extract year-level ProductionDataValue BEFORE filtering by Country/CrudeOil
        # ProductionDataValue is a single value per year, not per stream
        # Note: ProductionDataValue rows may have blank Country/CrudeOil/Crude Color/Avg. ProductionDataValue
        year_production_data_value = {}
        if "ProductionDataValue" in df.columns and "Year of YearReported" in df.columns:
            print(f"DEBUG: Extracting ProductionDataValue from {len(df)} rows")
            # Get ALL rows with ProductionDataValue (don't filter by Country/CrudeOil yet)
            year_value_df = df[["Year of YearReported", "ProductionDataValue"]].copy()
            print(f"DEBUG: ProductionDataValue column sample:\n{year_value_df.head(10)}")
            print(f"DEBUG: ProductionDataValue non-null count: {year_value_df['ProductionDataValue'].notna().sum()}")
            
            # Remove rows where ProductionDataValue is blank/empty/null
            year_value_df = year_value_df[
                year_value_df["ProductionDataValue"].notna() & 
                (year_value_df["ProductionDataValue"].astype(str).str.strip() != "") &
                (year_value_df["ProductionDataValue"].astype(str).str.strip().str.lower() != "nan")
            ].copy()
            print(f"DEBUG: After filtering blanks, {len(year_value_df)} rows with ProductionDataValue")
            
            if len(year_value_df) > 0:
                # Convert to numeric
                year_value_df["ProductionDataValue"] = pd.to_numeric(
                    year_value_df["ProductionDataValue"].astype(str).str.replace(',', '').str.replace('$', ''),
                    errors="coerce"
                )
                # Remove any rows that couldn't be converted to numeric
                year_value_df = year_value_df[year_value_df["ProductionDataValue"].notna()].copy()
                print(f"DEBUG: After numeric conversion, {len(year_value_df)} valid ProductionDataValue rows")
                
                # Group by year and take the first non-null value (should be unique per year)
                for year, group in year_value_df.groupby("Year of YearReported"):
                    year_str = str(year).strip()
                    valid_values = group[group["ProductionDataValue"].notna() & (group["ProductionDataValue"] > 0)]["ProductionDataValue"]
                    if len(valid_values) > 0:
                        year_production_data_value[year_str] = float(valid_values.iloc[0])
                        print(f"DEBUG: Found ProductionDataValue for year {year_str}: {year_production_data_value[year_str]}")
            else:
                print(f"DEBUG: WARNING - No valid ProductionDataValue found in CSV!")
        else:
            print(f"DEBUG: WARNING - ProductionDataValue or Year of YearReported column not found!")
            if "ProductionDataValue" not in df.columns:
                print(f"DEBUG: Available columns: {df.columns.tolist()}")
        
        print(f"DEBUG: Final year-level ProductionDataValue dictionary: {year_production_data_value}")
        
        # Filter out rows where Country or CrudeOil is missing
        df = df[(df["Country"].notna()) & (df["CrudeOil"].notna())].copy()
        df_long = pd.DataFrame()
        
        value_columns = []
        # For bar chart values, use Avg. ProductionDataValue (NOT ProductionDataValue which is year-level only)
        if "Avg. ProductionDataValue" in df.columns:
            value_columns.append("Avg. ProductionDataValue")
        
        required_cols = {"CrudeOil", "Country", "Year of YearReported"}
        if required_cols.issubset(df.columns) and value_columns:
            columns_to_keep = ["CrudeOil", "Country", "Year of YearReported"] + value_columns
            df_long = df[columns_to_keep].copy()
            df_long = df_long.rename(columns={
                "CrudeOil": "Stream",
                "Year of YearReported": "year"
            })
            
            # Use Avg. ProductionDataValue for bar chart (stream-level values)
            if "Avg. ProductionDataValue" in df_long.columns:
                value_source = df_long["Avg. ProductionDataValue"]
            else:
                value_source = pd.Series([0] * len(df_long), index=df_long.index)
            
            df_long["value"] = pd.to_numeric(
                value_source.astype(str).str.replace(',', ''),
                errors="coerce"
            ).fillna(0)
            
            df_long["year"] = df_long["year"].astype(str)
            df_long["month_idx"] = 0
            df_long = df_long[df_long["value"] > 0].copy()
            print(f"DEBUG: Loaded {len(df_long)} yearly bar records from {BAR_YEARLY_CSV}")
            if len(df_long) > 0:
                print(f"DEBUG: Value range: {df_long['value'].min():.0f} to {df_long['value'].max():.0f}")
                print(f"DEBUG: Years: {sorted(df_long['year'].unique())}")
                print(f"DEBUG: Streams: {df_long['Stream'].unique().tolist()}")
    except Exception as e:
        print(f"Error loading yearly bar data: {e}")
        import traceback
        traceback.print_exc()
        df = pd.DataFrame()
        df_long = pd.DataFrame()
        year_production_data_value = {}
    return df, df_long, year_production_data_value

def load_monthly_bar():
    """Load monthly bar data from Monthly Bar - Production_data.csv"""
    try:
        df = pd.read_csv(BAR_MONTHLY_CSV, encoding="utf-8", sep=",")
        df.columns = df.columns.str.strip()
        
        df_long = pd.DataFrame()
        if "Stream Name" in df.columns and "Country" in df.columns and "Year of Date" in df.columns and "Month of Date" in df.columns and "Avg. Value" in df.columns:
            df_long = df[["Stream Name", "Country", "Year of Date", "Month of Date", "Avg. Value"]].copy()
            df_long = df_long.rename(columns={
                "Stream Name": "Stream",
                "Year of Date": "year",
                "Month of Date": "month",
                "Avg. Value": "value"
            })
            
            # Convert year to string
            df_long["year"] = df_long["year"].astype(str)
            
            # Map month names to numbers
            month_map = {
                "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
                "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
            }
            df_long["month_idx"] = df_long["month"].map(month_map)
            
            # Convert value to numeric
            df_long["value"] = pd.to_numeric(df_long["value"].astype(str).str.replace(',', ''), errors="coerce").fillna(0)
            
            # Filter out invalid data
            df_long = df_long[(df_long["value"] > 0) & 
                              (df_long["Country"].notna()) & 
                              (df_long["Stream"].notna())].copy()
            print(f"DEBUG: Loaded {len(df_long)} monthly bar records from {BAR_MONTHLY_CSV}")
    except Exception as e:
        print(f"Error loading monthly bar data: {e}")
        import traceback
        traceback.print_exc()
        df = pd.DataFrame()
        df_long = pd.DataFrame()
    return df, df_long

def load_map_data():
    """Load map data - both yearly and monthly"""
    map_yearly_long = pd.DataFrame()
    map_monthly_long = pd.DataFrame()
    
    try:
        # Load yearly map data - CSV is already in long format
        # Columns: Country, Year of YearReported, Latitude, Longitude, Exports/Production Value
        map_yearly_df = pd.read_csv(MAP_YEARLY_CSV, encoding="utf-8", sep=",")
        
        # Clean column names
        map_yearly_df.columns = map_yearly_df.columns.str.strip()
        
        # Map column names (handle variations)
        if "Year of YearReported" in map_yearly_df.columns:
            map_yearly_df = map_yearly_df.rename(columns={"Year of YearReported": "year"})
        elif "Year" in map_yearly_df.columns:
            map_yearly_df = map_yearly_df.rename(columns={"Year": "year"})
        
        if "Exports/Production Value" in map_yearly_df.columns:
            map_yearly_df = map_yearly_df.rename(columns={"Exports/Production Value": "value"})
        elif "Value" in map_yearly_df.columns:
            map_yearly_df = map_yearly_df.rename(columns={"Value": "value"})
        
        if "Country" in map_yearly_df.columns and "year" in map_yearly_df.columns and "value" in map_yearly_df.columns:
            map_yearly_long = map_yearly_df[["Country", "year", "value"]].copy()
            map_yearly_long["year"] = map_yearly_long["year"].astype(str)
            map_yearly_long["value"] = pd.to_numeric(
                map_yearly_long["value"].astype(str).str.replace(',', ''), errors="coerce"
            ).fillna(0)
            map_yearly_long = map_yearly_long[map_yearly_long["value"] > 0].copy()
    except Exception as e:
        print(f"Error loading yearly map data: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        # Load monthly map data - CSV is already in long format
        # Columns: Country, Measure Names, month_year, Latitude, Longitude, Value
        map_monthly_df = pd.read_csv(MAP_MONTHLY_CSV, encoding="utf-8", sep=",")
        
        # Clean column names
        map_monthly_df.columns = map_monthly_df.columns.str.strip()
        
        # Map column names
        if "Value" in map_monthly_df.columns:
            map_monthly_df = map_monthly_df.rename(columns={"Value": "value"})
        
        if "month_year" in map_monthly_df.columns:
            # Split month_year into year and month
            map_monthly_df[["year", "month"]] = map_monthly_df["month_year"].str.split("-", expand=True)
            map_monthly_df["year"] = map_monthly_df["year"].astype(str)
            map_monthly_df["month"] = pd.to_numeric(map_monthly_df["month"], errors="coerce")
        
        if "Country" in map_monthly_df.columns and "year" in map_monthly_df.columns and "month" in map_monthly_df.columns and "value" in map_monthly_df.columns:
            map_monthly_long = map_monthly_df[["Country", "year", "month", "value"]].copy()
            map_monthly_long["value"] = pd.to_numeric(
                map_monthly_long["value"].astype(str).str.replace(',', ''), errors="coerce"
            ).fillna(0)
            map_monthly_long = map_monthly_long[map_monthly_long["value"] > 0].copy()
    except Exception as e:
        print(f"Error loading monthly map data: {e}")
        import traceback
        traceback.print_exc()
    
    return map_yearly_long, map_monthly_long

def load_grades_data():
    """Load grades/streams data for selected country - both yearly and monthly"""
    yearly_grades = pd.DataFrame()
    monthly_grades = pd.DataFrame()
    
    try:
        # Load yearly grades data
        yearly_grades = pd.read_csv(YEARLY_GRADES_CSV, encoding="utf-8", sep=",")
        yearly_grades.columns = yearly_grades.columns.str.strip()
        # Map column names
        if "CrudeOil" in yearly_grades.columns:
            yearly_grades = yearly_grades.rename(columns={"CrudeOil": "Stream"})
        elif "Stream" in yearly_grades.columns:
            pass  # Already has Stream column
        elif "Stream Name" in yearly_grades.columns:
            yearly_grades = yearly_grades.rename(columns={"Stream Name": "Stream"})
    except Exception as e:
        print(f"Error loading yearly grades data: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        # Load monthly grades data
        monthly_grades = pd.read_csv(MONTHLY_GRADES_CSV, encoding="utf-8", sep=",")
        monthly_grades.columns = monthly_grades.columns.str.strip()
        # Map column names
        if "Stream Name" in monthly_grades.columns:
            monthly_grades = monthly_grades.rename(columns={"Stream Name": "Stream"})
        elif "Stream" in monthly_grades.columns:
            pass  # Already has Stream column
        elif "CrudeOil" in monthly_grades.columns:
            monthly_grades = monthly_grades.rename(columns={"CrudeOil": "Stream"})
    except Exception as e:
        print(f"Error loading monthly grades data: {e}")
        import traceback
        traceback.print_exc()
    
    return yearly_grades, monthly_grades

def load_stream_color_order():
    """Load stream color and order from grades CSV files"""
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
    
    try:
        # Load yearly stream color/order
        if os.path.exists(YEARLY_GRADES_CSV):
            yearly_df = pd.read_csv(YEARLY_GRADES_CSV, encoding="utf-8", sep=",")
            yearly_df.columns = yearly_df.columns.str.strip()
            
            # Map Stream column
            stream_col = None
            if "Stream" in yearly_df.columns:
                stream_col = "Stream"
            elif "Stream Name" in yearly_df.columns:
                stream_col = "Stream Name"
            elif "CrudeOil" in yearly_df.columns:
                stream_col = "CrudeOil"
            
            # Map Color column
            color_col = None
            for col in ["Color", "colour", "COLOUR", "Stream Color", "Stream Colour"]:
                if col in yearly_df.columns:
                    color_col = col
                    break
            
            if stream_col and color_col:
                # Build list of (stream, color) tuples, preserving order
                for _, row in yearly_df.iterrows():
                    stream = str(row[stream_col]).strip() if pd.notna(row[stream_col]) else None
                    color = str(row[color_col]).strip() if pd.notna(row[color_col]) else None
                    if stream and color:
                        yearly_order.append((stream, color))
            elif stream_col:
                # If no color column, use default colors for streams found in CSV
                streams_in_csv = yearly_df[stream_col].dropna().unique().tolist()
                default_color_map = dict(default_yearly)
                for stream in streams_in_csv:
                    stream_str = str(stream).strip()
                    color = default_color_map.get(stream_str, "#808080")  # Default gray if not found
                    yearly_order.append((stream_str, color))
    except Exception as e:
        print(f"Error loading yearly stream color/order: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        # Load monthly stream color/order
        if os.path.exists(MONTHLY_GRADES_CSV):
            monthly_df = pd.read_csv(MONTHLY_GRADES_CSV, encoding="utf-8", sep=",")
            monthly_df.columns = monthly_df.columns.str.strip()
            
            # Map Stream column
            stream_col = None
            if "Stream" in monthly_df.columns:
                stream_col = "Stream"
            elif "Stream Name" in monthly_df.columns:
                stream_col = "Stream Name"
            elif "CrudeOil" in monthly_df.columns:
                stream_col = "CrudeOil"
            
            # Map Color column
            color_col = None
            for col in ["Color", "colour", "COLOUR", "Stream Color", "Stream Colour"]:
                if col in monthly_df.columns:
                    color_col = col
                    break
            
            if stream_col and color_col:
                # Build list of (stream, color) tuples, preserving order
                for _, row in monthly_df.iterrows():
                    stream = str(row[stream_col]).strip() if pd.notna(row[stream_col]) else None
                    color = str(row[color_col]).strip() if pd.notna(row[color_col]) else None
                    if stream and color:
                        monthly_order.append((stream, color))
            elif stream_col:
                # If no color column, use default colors for streams found in CSV
                streams_in_csv = monthly_df[stream_col].dropna().unique().tolist()
                default_color_map = dict(default_monthly)
                for stream in streams_in_csv:
                    stream_str = str(stream).strip()
                    color = default_color_map.get(stream_str, "#808080")  # Default gray if not found
                    monthly_order.append((stream_str, color))
    except Exception as e:
        print(f"Error loading monthly stream color/order: {e}")
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

def load_table():
    """Load table data from Table - Country Production_data.csv (yearly) and Table - monthly crude production_data.csv (monthly)"""
    yearly_df = pd.DataFrame()
    monthly_df = pd.DataFrame()
    year_to_month_cols = {}
    
    try:
        # Load yearly table data
        yearly_raw = pd.read_csv(TABLE_YEARLY_CSV, encoding="utf-8", sep=",")
        yearly_raw.columns = yearly_raw.columns.str.strip()
        profile_col = next((col for col in yearly_raw.columns if col.strip().lower() == "profile_url"), None)
        if profile_col and profile_col != "profile_url":
            yearly_raw = yearly_raw.rename(columns={profile_col: "profile_url"})
        
        # Pivot yearly data: CrudeOil -> rows, Year of YearReported -> columns
        if not yearly_raw.empty and "CrudeOil" in yearly_raw.columns and "Year of YearReported" in yearly_raw.columns:
            # Get unique crudes and years
            crudes = yearly_raw["CrudeOil"].dropna().unique()
            years = sorted(yearly_raw["Year of YearReported"].dropna().unique(), reverse=True)
            
            # Create base dataframe with CrudeOil
            yearly_df = pd.DataFrame({"CrudeOil": crudes})
            
            # Add year columns with values
            for year in years:
                year_str = str(int(year))
                year_data = yearly_raw[yearly_raw["Year of YearReported"] == year]
            # Merge values by CrudeOil
                year_values = year_data[["CrudeOil", "Avg. ProductionDataValue"]].set_index("CrudeOil")["Avg. ProductionDataValue"]
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
            
            # Add metadata columns if available (from bar data or grades data)
            # We'll add these in the callback when we have country context
            
        # Load monthly table data
        monthly_raw = pd.read_csv(TABLE_MONTHLY_CSV, encoding="utf-8", sep=",")
        monthly_raw.columns = monthly_raw.columns.str.strip()
        monthly_profile_col = next((col for col in monthly_raw.columns if col.strip().lower() == "profile_url"), None)
        if monthly_profile_col and monthly_profile_col != "profile_url":
            monthly_raw = monthly_raw.rename(columns={monthly_profile_col: "profile_url"})
        
        if not monthly_raw.empty and {"Crude", "Year of Date", "Month of Date", "Measure Values"}.issubset(monthly_raw.columns):
            metadata_cols = ["Crude", "CI Rank", "API", "Sulfur", "BSP link", "profile_url"]
            available_metadata = [col for col in metadata_cols if col in monthly_raw.columns]
            
            if available_metadata:
                monthly_df = monthly_raw[available_metadata].drop_duplicates(subset=["Crude"]).copy()
            else:
                monthly_df = pd.DataFrame({"Crude": monthly_raw["Crude"].dropna().unique()})
            
            monthly_df = monthly_df.sort_values("Crude")
            monthly_df.set_index("Crude", inplace=True)
            
            months_order = ['January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December']
            
            monthly_raw["Year of Date"] = monthly_raw["Year of Date"].astype(int)
            years = sorted(monthly_raw["Year of Date"].dropna().unique(), reverse=True)
            
            for year in years:
                year_str = str(year)
                year_to_month_cols[year_str] = []
                for month in months_order:
                    mask = (
                        (monthly_raw["Year of Date"] == year) &
                        (monthly_raw["Month of Date"] == month)
                    )
                    if not mask.any():
                        continue
                    
                    month_values = (
                        monthly_raw.loc[mask, ["Crude", "Measure Values"]]
                        .drop_duplicates(subset=["Crude"])
                        .set_index("Crude")["Measure Values"]
                    )
                    if month_values.empty:
                        continue
                    
                    col_name = f"{year_str}_{month}"
                    monthly_df[col_name] = monthly_df.index.map(month_values)
                    year_to_month_cols[year_str].append({"month": month, "column": col_name})
            
            monthly_df.reset_index(inplace=True)
            
    except Exception as e:
        print(f"Error loading table data: {e}")
        import traceback
        traceback.print_exc()
    
    return yearly_df, monthly_df, year_to_month_cols

# Load data once at module import
BAR_DF_YEARLY, BAR_LONG_YEARLY, YEAR_PRODUCTION_DATA_VALUE = load_yearly_bar()
BAR_DF_MONTHLY, BAR_LONG_MONTHLY = load_monthly_bar()
MAP_YEARLY_LONG, MAP_MONTHLY_LONG = load_map_data()
TABLE_DF_YEARLY, TABLE_DF_MONTHLY, YEAR_TO_MONTH_COLS = load_table()
YEARLY_GRADES_DF, MONTHLY_GRADES_DF = load_grades_data()

def _collect_filter_values(column_name):
    values = set()
    for df in [TABLE_DF_YEARLY, TABLE_DF_MONTHLY]:
        if column_name in df.columns:
            series = (
                df[column_name]
                .dropna()
                .astype(str)
                .str.strip()
            )
            values.update(v for v in series if v and v.lower() != "nan")
    return sorted(values)

CI_OPTIONS = _collect_filter_values("CI Rank")
API_OPTIONS = _collect_filter_values("API")
SULFUR_OPTIONS = _collect_filter_values("Sulfur")
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
    if api_value < 22.3:
        return "Heavy"
    if api_value <= 31.1:
        return "Medium"
    return "Light"

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
    return "Sour" if sulfur_value >= 0.5 else "Sweet"

# Get options for dropdowns
COUNTRIES = sorted(BAR_DF_MONTHLY["Country"].dropna().unique().tolist()) if not BAR_DF_MONTHLY.empty and "Country" in BAR_DF_MONTHLY.columns else []
STREAMS = sorted(BAR_DF_MONTHLY["Stream"].dropna().unique().tolist()) if not BAR_DF_MONTHLY.empty and "Stream" in BAR_DF_MONTHLY.columns else []
YEARS_YEARLY = sorted(BAR_LONG_YEARLY["year"].dropna().unique().tolist()) if not BAR_LONG_YEARLY.empty and "year" in BAR_LONG_YEARLY.columns else []
YEARS_MONTHLY = sorted(BAR_LONG_MONTHLY["year"].dropna().unique().tolist()) if not BAR_LONG_MONTHLY.empty and "year" in BAR_LONG_MONTHLY.columns else []
YEARS = sorted(list(set(YEARS_YEARLY + YEARS_MONTHLY))) if YEARS_YEARLY or YEARS_MONTHLY else []

# Generate year-month options
YEAR_MONTHS = []
for year in range(2000, 2026):
    for month in range(1, 13):
        month_str = f"{month:02d}"
        YEAR_MONTHS.append({"label": f"{year}-{month_str}", "value": f"{year}-{month_str}"})
YEAR_MONTHS.reverse()

PRODUCTION_YEARS = sorted([int(y) for y in YEAR_TO_MONTH_COLS.keys() if y.isdigit()], reverse=True)
PRODUCTION_YEAR_DEFAULT = [y for y in PRODUCTION_YEARS if y in (2025, 2024)]
if not PRODUCTION_YEAR_DEFAULT:
    PRODUCTION_YEAR_DEFAULT = PRODUCTION_YEARS[:2] if PRODUCTION_YEARS else []

# Stream color/ordering requirements - loaded from CSV files
YEARLY_STREAM_COLOR_ORDER, MONTHLY_STREAM_COLOR_ORDER = load_stream_color_order()

STREAM_COLOR_ORDERS = {
    "yearly": YEARLY_STREAM_COLOR_ORDER,
    "monthly": MONTHLY_STREAM_COLOR_ORDER
}
STREAM_COLOR_MAPS = {mode: {name: color for name, color in order} for mode, order in STREAM_COLOR_ORDERS.items()}
STREAM_ORDERS = {mode: [name for name, _ in order] for mode, order in STREAM_COLOR_ORDERS.items()}
FALLBACK_COLORS = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
    '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5'
]


def get_stream_order(tab="yearly"):
    return STREAM_ORDERS.get(tab, STREAM_ORDERS["yearly"])


def get_stream_color_map(tab="yearly"):
    return STREAM_COLOR_MAPS.get(tab, STREAM_COLOR_MAPS["yearly"])


def get_color_sequence(tab="yearly"):
    base = [color for _, color in STREAM_COLOR_ORDERS.get(tab, STREAM_COLOR_ORDERS["yearly"])]
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
    return html.Div([
        # Custom CSS to style markdown links in DataTable to look like normal text
        html.Div(
            dcc.Markdown(
                """
                <style>
                    #crude-table a {
                        color: #2c3e50 !important;
                        text-decoration: none !important;
                    }
                    #crude-table a:hover {
                        color: #2c3e50 !important;
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
            value="yearly", 
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
        html.H4(
            "World Crude Production*", 
            style={"color":"#d35400","textAlign":"center", "marginTop":"10px"}
        ),
        html.Hr(),
        html.H4(
            id="production-breakdown-title",
            children="",
            style={"display": "none"}
        ),
        html.Div([
            html.Div([
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
                dcc.Dropdown(
                    id="crude-country-dropdown", 
                    options=[{"label":c,"value":c} for c in COUNTRIES], 
                    value=[COUNTRIES[0]] if COUNTRIES else None,
                    multi=True,
                    placeholder="Select countries",
                    style={"fontSize":"12px"}
                )
            ], className='col-md-2', style={'padding': '10px', 'paddingTop': '20px'})
        ], className='row'),
        html.Br(),
        html.Div([
            html.Div(
                dcc.Graph(
                    id="production-breakdown-chart", 
                    style={"height":"520px"},
                    figure=go.Figure()  # Initialize with empty figure
                ), 
                className='col-md-9',
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
                        dcc.Dropdown(
                            id="production-year-dropdown",
                            options=([{"label": str(y), "value": y} for y in PRODUCTION_YEARS]
                                     if PRODUCTION_YEARS else [{"label": str(y), "value": y} for y in range(2000, 2026)]),
                            value=PRODUCTION_YEAR_DEFAULT if PRODUCTION_YEAR_DEFAULT else [],
                            multi=True,
                            placeholder="Select years",
                            style={"marginBottom": "15px", "fontSize": "12px"}
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
            ], className='col-md-3', style={'padding': '15px'})
        ], className='row'),
        html.Br(),
        html.H4(
            id="table-title",
            children="Global Crude Production Breakdown",
            style={"color":"#d35400","textAlign":"center"}
        ),
        html.Div([
            html.Div([
            dash_table.DataTable(
                id="crude-table",
                columns=[{"name":str(c),"id":str(c)} for c in TABLE_DF_YEARLY.columns.tolist()] if not TABLE_DF_YEARLY.empty else [],
                data=TABLE_DF_YEARLY.to_dict("records") if not TABLE_DF_YEARLY.empty else [],
                page_action='none',
                style_table={
                    "overflowX": "auto", 
                    "overflowY": "auto", 
                    "minHeight": "400px",
                    "maxHeight": "600px",
                    "height": "auto"
                },
                style_cell={"textAlign":"left","minWidth":"80px","whiteSpace":"normal"},
                style_header={
                    "textAlign": "center",
                    "fontWeight": "bold"
                },
                merge_duplicate_headers=True
            )
            ], className='col-md-9', style={'padding': '15px', 'minHeight': '400px'}),
            html.Div([
                html.Label("Stream Name"),
                dcc.Input(id="filter-stream", type="text", placeholder="Stream Name"),
                html.Br(), html.Br(),
                html.Label("CI Rank"),
                dcc.Dropdown(
                    id="filter-ci", 
                    options=([{"label":"(All)", "value":"(All)"}] + [{"label":v, "value":v} for v in CI_OPTIONS]) if CI_OPTIONS else [{"label":"(All)", "value":"(All)"}],
                    multi=True
                ),
                html.Br(),
                html.Label("API"),
                dcc.Dropdown(
                    id="filter-api", 
                    options=[{"label":"(All)", "value":"(All)"}] + [{"label":v, "value":v} for v in API_FILTER_CHOICES],
                    multi=True
                ),
                html.Br(),
                html.Label("Sulfur"),
                dcc.Dropdown(
                    id="filter-sulfur", 
                    options=[{"label":"(All)", "value":"(All)"}] + [{"label":v, "value":v} for v in SULFUR_FILTER_CHOICES],
                    multi=True
                ),
            ], className='col-md-3', style={'padding': '15px'})
        ], className='row')
    ], style={'padding': '20px', 'background': '#f8f9fa'})


def register_callbacks(dash_app, server):
    """Register all callbacks for Crude Overview"""
    
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
        [Output("profiled-streams", "options"),
         Output("profiled-streams", "value")],
        [Input("crude-country-dropdown", "value"),
         Input("crude-main-tabs", "value"),
         Input("crude-year-dropdown", "value"),
         Input("crude-year-month-dropdown", "value")],
        prevent_initial_call=False
    )
    def update_profiled_streams_options(country, tab, year, year_month):
        """Update profiled streams options based on selected country and tab using grades CSV files"""
        
        try:
            # Handle country - ensure it's a list
            if not country:
                country = [COUNTRIES[0]] if COUNTRIES else ["Russia"]
            elif isinstance(country, str):
                country = [country]
            elif not isinstance(country, list):
                country = [country] if country else [COUNTRIES[0]] if COUNTRIES else ["Russia"]
            
            selected_country = country[0] if country else ("Russia" if not COUNTRIES else COUNTRIES[0])
            
            print(f"DEBUG update_profiled_streams_options: country={country}, selected_country={selected_country}, tab={tab}")
            
            # Get streams from grades CSV based on tab
            available_streams = []
            stream_to_url = {}  # Map stream name to profile_url
            
            if tab == "yearly" or tab is None:
                # Use yearly grades CSV
                if not YEARLY_GRADES_DF.empty and "Stream" in YEARLY_GRADES_DF.columns:
                    # Filter by country if Country column exists
                    if "Country" in YEARLY_GRADES_DF.columns:
                        country_df = YEARLY_GRADES_DF[YEARLY_GRADES_DF["Country"] == selected_country].copy()
                    else:
                        # If no Country column, use all streams
                        country_df = YEARLY_GRADES_DF.copy()
                    
                    # Extract link if available (profile_url or BSP link)
                    link_col = None
                    for col in ["profile_url", "Profile URL", "Profile_URL", "profile-url", "Profile-URL", "BSP link", "BSP Link"]:
                        if col in country_df.columns:
                            link_col = col
                            break
                    
                    if link_col:
                        for _, row in country_df.iterrows():
                            stream = str(row["Stream"]).strip() if pd.notna(row["Stream"]) else None
                            url = str(row[link_col]).strip() if pd.notna(row[link_col]) else None
                            if stream and url:
                                stream_to_url[stream] = url
                    
                    country_streams = country_df["Stream"].dropna().unique().tolist()
                    available_streams = order_streams_list(country_streams, tab="yearly")
                    print(f"DEBUG: Yearly streams for {selected_country}: {len(available_streams)} streams")
            else:
                # Use monthly grades CSV - use exact order from MONTHLY_STREAM_COLOR_ORDER
                if not MONTHLY_GRADES_DF.empty and "Stream" in MONTHLY_GRADES_DF.columns:
                    # Filter by country if Country column exists
                    if "Country" in MONTHLY_GRADES_DF.columns:
                        country_df = MONTHLY_GRADES_DF[MONTHLY_GRADES_DF["Country"] == selected_country].copy()
                    else:
                        # If no Country column, use all streams
                        country_df = MONTHLY_GRADES_DF.copy()
                    
                    # Extract link if available (profile_url or BSP link)
                    link_col = None
                    for col in ["profile_url", "Profile URL", "Profile_URL", "profile-url", "Profile-URL", "BSP link", "BSP Link"]:
                        if col in country_df.columns:
                            link_col = col
                            break
                    
                    if link_col:
                        for _, row in country_df.iterrows():
                            stream = str(row["Stream"]).strip() if pd.notna(row["Stream"]) else None
                            url = str(row[link_col]).strip() if pd.notna(row[link_col]) else None
                            if stream and url:
                                stream_to_url[stream] = url
                    
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
            
            # Select all streams by default so charts display complete totals
            default_value = available_streams[:]
            
            print(f"DEBUG: Returning {len(options)} options and {len(default_value)} default values")
            return options, default_value
            
        except Exception as e:
            print(f"Error updating profiled streams options: {e}")
            import traceback
            traceback.print_exc()
            return [], []
    
    def get_stream_color(stream, all_streams_list, tab="yearly"):
        """Get consistent color for a stream based on its position in the full streams list"""
        color_map = get_stream_color_map(tab)
        if stream in color_map:
            return color_map[stream]
        if stream in all_streams_list:
            idx = all_streams_list.index(stream)
            return FALLBACK_COLORS[idx % len(FALLBACK_COLORS)]
        return FALLBACK_COLORS[0]
    
    @dash_app.callback(
        Output("profiled-streams-container", "children"),
        [Input("profiled-streams", "value"),
         Input("profiled-streams", "options"),
         Input("production-breakdown-chart", "figure"),
         Input("crude-main-tabs", "value")],
        prevent_initial_call=False
    )
    def update_profiled_streams_with_colors(selected_streams, stream_options, chart_figure, active_tab):
        """Create combined checklist with checkbox and color badge for each stream - single list with both"""
        if not stream_options:
            return html.Div("No streams available")
        
        selected_streams = selected_streams if selected_streams else []
        
        # Get all available streams from options
        all_available_streams = [opt["value"] for opt in stream_options] if stream_options else []
        
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
        
        # Create combined checklist items with checkbox and color badge
        checklist_items = []
        selected_set = set(selected_streams) if selected_streams else set()
        
        for opt in stream_options:
            stream = opt["value"]
            is_checked = stream in selected_set
            profile_url = opt.get("profile_url")  # Get profile_url from options
            
            # Get color for this stream
            if stream in color_map:
                color = color_map[stream]
            else:
                tab_value = active_tab if active_tab in STREAM_COLOR_ORDERS else "yearly"
                color = get_stream_color(stream, all_available_streams, tab=tab_value)
            
            # Convert color to hex if needed
            color_hex = color
            if isinstance(color, str) and color.startswith('rgb'):
                color_hex = color
            elif isinstance(color, tuple):
                color_hex = f"rgb({color[0]}, {color[1]}, {color[2]})"
            
            # Check if color is dark for text contrast
            is_dark = False
            if isinstance(color_hex, str) and color_hex.startswith('#'):
                try:
                    r = int(color_hex[1:3], 16)
                    g = int(color_hex[3:5], 16)
                    b = int(color_hex[5:7], 16)
                    brightness = (r * 299 + g * 587 + b * 114) / 1000
                    is_dark = brightness < 128
                except:
                    pass
            
            # Create stream name element - with link if profile_url is available
            stream_name_style = {
                "fontSize": "10px",
                "verticalAlign": "middle",
                "backgroundColor": color_hex,
                "padding": "1px 4px",
                "borderRadius": "3px",
                "display": "inline-block",
                "minWidth": "100px",
                "textAlign": "center",
                "color": "#ffffff" if is_dark else "#2c3e50",
                "fontWeight": "500"
            }
            
            if profile_url:
                # Create clickable link
                stream_name_element = html.A(
                    stream,
                    href=profile_url,
                    target="_blank",
                    style={
                        **stream_name_style,
                        "textDecoration": "none",
                        "cursor": "pointer"
                    }
                )
            else:
                # Create non-clickable span
                stream_name_element = html.Span(stream, style=stream_name_style)
            
            # Create combined checkbox and color badge in one item using dcc.Checklist
            checklist_items.append(
                html.Div([
                    dcc.Checklist(
                        id={"type": "stream-checkbox", "stream": stream},
                        options=[{"label": "", "value": stream}],
                        value=[stream] if is_checked else [],
                        style={"display": "inline-block", "marginRight": "8px", "verticalAlign": "middle"},
                        inputStyle={"marginRight": "5px", "cursor": "pointer", "width": "16px", "height": "16px"},
                        labelStyle={"margin": "0", "display": "flex", "alignItems": "center"}
                    ),
                    stream_name_element
                ], style={
                    "display": "flex",
                    "alignItems": "center",
                    "marginBottom": "2px",  # Reduced from 6px
                    "padding": "0"  # Reduced from 2px 0
                })
            )
        
        return checklist_items
    
    @dash_app.callback(
        Output("profiled-streams", "value", allow_duplicate=True),
        [Input({"type": "stream-checkbox", "stream": dd.ALL}, "value")],
        [State({"type": "stream-checkbox", "stream": dd.ALL}, "id")],
        prevent_initial_call=True
    )
    def update_profiled_streams_from_checkboxes(checkbox_values, checkbox_ids):
        """Update main profiled-streams checklist when individual checkboxes change"""
        if not checkbox_values or not checkbox_ids:
            return no_update
        
        # Collect all checked streams
        checked_streams = []
        for idx, value in enumerate(checkbox_values):
            if value and len(value) > 0:
                stream_id = checkbox_ids[idx]
                if isinstance(stream_id, dict) and "stream" in stream_id:
                    checked_streams.append(stream_id["stream"])
        
        return checked_streams
    
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
        Output("crude-map", "figure"),
        [Input("crude-year-dropdown", "value"),
         Input("crude-year-month-dropdown", "value"),
         Input("crude-country-dropdown", "value"),
         Input("crude-main-tabs", "value")],
        prevent_initial_call=False
    )
    def update_map(selected_year, selected_year_month, selected_countries, tab):
        """Update world map based on filters"""
        
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
                        agg = agg.groupby("Country")["value"].sum().reset_index()
                    else:
                        agg = pd.DataFrame(columns=["Country", "value"])
                else:
                    agg = pd.DataFrame(columns=["Country", "value"])
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
                                    agg = pd.DataFrame(columns=["Country", "value"])
                            else:
                                agg = pd.DataFrame(columns=["Country", "value"])
                        
                        if len(agg) > 0:
                            agg = agg.groupby("Country")["value"].sum().reset_index()
                            print(f"DEBUG MAP MONTHLY: After groupby, agg length={len(agg)}")
                            print(f"DEBUG MAP MONTHLY: Sample countries: {agg['Country'].head().tolist() if len(agg) > 0 else []}")
                        else:
                            agg = pd.DataFrame(columns=["Country", "value"])
                    else:
                        print(f"DEBUG MAP MONTHLY: Missing required columns. Available: {MAP_MONTHLY_LONG.columns.tolist()}")
                        agg = pd.DataFrame(columns=["Country", "value"])
                else:
                    print(f"DEBUG MAP MONTHLY: MAP_MONTHLY_LONG is empty")
                    agg = pd.DataFrame(columns=["Country", "value"])
        except Exception as e:
            print(f"Error in update_map: {e}")
            import traceback
            traceback.print_exc()
            agg = pd.DataFrame(columns=["Country", "value"])
        
        if agg.empty:
            fig = go.Figure()
            fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return fig
        
        fig = px.choropleth(
            agg, 
            locations="Country", 
            locationmode="country names", 
            color="value",
            projection="natural earth", 
            color_continuous_scale="Blues",
            labels={"value":"Production ('000 b/d)"},
            hover_data={"Country": True, "value": ":,.0f"},
            range_color=[0, 13500]
        )
        fig.update_layout(
            margin=dict(l=10,r=10,t=10,b=80),
            height=500,  # Increased height for better map visibility
            geo=dict(
                bgcolor="white",
                showframe=False,
                showcoastlines=True,
                projection_type="natural earth",
                projection=dict(
                    type="natural earth",
                    scale=1.0,  # Base scale - prevents zooming out too far
                    rotation=dict(lon=0, lat=0)
                ),
                lonaxis=dict(range=[-180, 180], showgrid=False),
                lataxis=dict(range=[-90, 90], showgrid=False),
                center=dict(lon=0, lat=0),
                visible=True,
                domain=dict(x=[0, 1], y=[0, 1]),
                # Improve map styling for better visibility
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
                dtick=2000,
                showticklabels=True,
                ticks="outside"
            ),
            template="plotly_white",
            autosize=True
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
         Input("crude-map", "clickData")],
        prevent_initial_call=False
    )
    def update_breakdown(country, year, year_month, production_years, profiled, tab, map_click):
        """Update production breakdown chart"""
        
        try:
            month_names = ["January", "February", "March", "April", "May", "June",
                          "July", "August", "September", "October", "November", "December"]
            
            # Handle map click - update country selection
            if map_click and map_click.get("points"):
                clicked_country = map_click["points"][0].get("location")
                if clicked_country:
                    if not country:
                        country = [clicked_country]
                    elif clicked_country not in country:
                        country = [clicked_country]
                    print(f"DEBUG: Map clicked, country={clicked_country}, updated country={country}")
            
            if year is None:
                year = int(YEARS[-1]) if YEARS else 2024
            if tab is None:
                tab = "yearly"
            
            # Handle country - ensure it's a list
            if not country:
                country = [COUNTRIES[0]] if COUNTRIES else ["Russia"]
            elif isinstance(country, str):
                country = [country]
            elif not isinstance(country, list):
                country = [country] if country else [COUNTRIES[0]] if COUNTRIES else ["Russia"]
            
            # Handle profiled streams - if empty, show all available streams (don't filter)
            # profiled will be used later to filter if it has values
            
            title_text = f"Production Breakdown - {' & '.join(country)}"
            
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
                    
                    # Get available streams from yearly grades CSV for the selected country
                    if not YEARLY_GRADES_DF.empty and "Stream" in YEARLY_GRADES_DF.columns:
                        # Filter by country if Country column exists
                        if "Country" in YEARLY_GRADES_DF.columns:
                            selected_country = country[0] if country else "Russia"
                            grades_for_country = YEARLY_GRADES_DF[YEARLY_GRADES_DF["Country"] == selected_country]
                            available_streams = grades_for_country["Stream"].dropna().unique().tolist()
                        else:
                            # If no Country column, use all streams (grades CSV is country-specific)
                            available_streams = YEARLY_GRADES_DF["Stream"].dropna().unique().tolist()
                        print(f"DEBUG BREAKDOWN YEARLY: Available streams from grades CSV: {available_streams} ({len(available_streams)} streams)")
                        
                        # Filter data to only show streams from grades CSV
                        if available_streams:
                            streams_in_data = df["Stream"].unique().tolist()
                            matching_streams = [s for s in available_streams if s in streams_in_data]
                            print(f"DEBUG BREAKDOWN YEARLY: Matching streams between grades CSV and data: {matching_streams}")
                            if matching_streams:
                                df = df[df["Stream"].isin(matching_streams)].copy()
                                print(f"DEBUG BREAKDOWN YEARLY: After grades CSV filter, df length={len(df)}")
                            else:
                                print(f"DEBUG BREAKDOWN YEARLY: WARNING - No matching streams found! Grades CSV streams: {available_streams}, Data streams: {streams_in_data}")
                                # Don't filter - show all streams from data
                        else:
                            print(f"DEBUG BREAKDOWN YEARLY: No streams in grades CSV, showing all streams from data")
                    else:
                        print(f"DEBUG BREAKDOWN YEARLY: YEARLY_GRADES_DF is empty or missing Stream column")
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
                        title=dict(text=title_text, font=dict(color="#d35400", size=18, family="Arial, sans-serif"), x=0.5, xanchor="center", y=0.98),
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
                
                # Apply profiled streams filter ONLY if streams are selected
                # If no streams selected (profiled is None or empty), show ALL available streams
                if profiled and len(profiled) > 0:
                    profiled_in_data = [s for s in profiled if s in df["Stream"].values]
                    if profiled_in_data:
                        df = df[df["Stream"].isin(profiled_in_data)].copy()
                        print(f"DEBUG BREAKDOWN YEARLY: After profiled filter ({len(profiled_in_data)} streams), df length={len(df)}")
                    else:
                        print(f"DEBUG BREAKDOWN YEARLY: No profiled streams found in data, showing all available streams")
                else:
                    print(f"DEBUG BREAKDOWN YEARLY: No profiled streams selected, showing all available streams")
                
                # Group by year and stream, sum values
                agg = df.groupby(["year", "Stream"])["value"].sum().reset_index()
                
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
                        title=dict(text=title_text, font=dict(color="#d35400", size=18, family="Arial, sans-serif"), x=0.5, xanchor="center", y=0.98),
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
                
                # Ensure we have data for all years (even if empty) for proper X-axis display
                # Create a complete year-stream combination dataframe
                all_years_list = [str(y) for y in range(2006, 2025)]
                all_streams_list = order_streams_list(agg["Stream"].unique().tolist(), tab="yearly")
                
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
                    agg_for_chart = pd.concat([agg_nonzero, placeholder_data], ignore_index=True)
                    print(f"DEBUG BREAKDOWN YEARLY: Added placeholder entries for {len(missing_years)} years")
                else:
                    agg_for_chart = agg_nonzero
                
                print(f"DEBUG BREAKDOWN YEARLY: Final chart data shape: {agg_for_chart.shape}")
                print(f"DEBUG BREAKDOWN YEARLY: Years in chart data: {sorted(agg_for_chart['year'].unique())}")
                print(f"DEBUG BREAKDOWN YEARLY: All years should be: {all_years_list}")
                if len(agg_for_chart) > 0:
                    print(f"DEBUG BREAKDOWN YEARLY: Sample of chart data:\n{agg_for_chart.head(20)}")
                
                if len(agg_for_chart) == 0:
                    print("DEBUG BREAKDOWN YEARLY: No data, creating empty chart with all years on X-axis")
                    # Create empty chart but with all years on X-axis - use first stream with tiny values
                    first_stream = all_streams_list[0] if all_streams_list else "None"
                    empty_df = pd.DataFrame({
                        "year": all_years_list,
                        "value": [0.0001] * len(all_years_list),
                        "Stream": [first_stream] * len(all_years_list)
                    })
                    fig = px.bar(empty_df, x="year", y="value", color="Stream", 
                                labels={"value":"Production Volume ('000 b/d)", "year":"Year"})
                    fig.update_layout(
                        title=dict(text=title_text, font=dict(color="#d35400", size=18, family="Arial, sans-serif"), x=0.5, xanchor="center", y=0.98),
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
                        title=dict(text=title_text, font=dict(color="#d35400", size=18, family="Arial, sans-serif"), x=0.5, xanchor="center", y=0.98),
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
                
                # Format traces first
                fig.update_traces(
                    marker=dict(line=dict(width=1, color='white')),
                    hovertemplate='<b>%{fullData.name}</b><br>Year: %{x}<br>Production: %{y:,.0f} (\'000 b/d)<extra></extra>'
                )
                
                # Calculate max bar height first (needed for annotation positioning)
                max_bar_height = max(year_totals_dict.values()) if year_totals_dict else 0
                
                # Add ProductionDataValue above each bar - show only the value (no year, since year is on X-axis)
                # Use year-level ProductionDataValue if available, otherwise use sum of bars
                annotations_list = []
                max_annotation_y = 0
                
                # Create year to index mapping for categorical X-axis positioning
                year_to_index = {year: idx for idx, year in enumerate(years_sorted)}
                
                for year in years_sorted:
                    # Prefer ProductionDataValue, fallback to sum of bars
                    production_value = year_production_values.get(year)
                    print(f"DEBUG BREAKDOWN YEARLY: Year {year} - ProductionDataValue: {production_value}, Sum of bars: {year_totals_dict.get(year, 0)}")
                    
                    if production_value is None or production_value == 0:
                        production_value = year_totals_dict.get(year, 0)
                    
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
                y_axis_max = base_max * 1.25  # Add 25% padding above highest point
                
                if y_axis_max == 0:
                    y_axis_max = 12000
                
                print(f"DEBUG BREAKDOWN YEARLY: max_bar_height={max_bar_height}, max_annotation_y={max_annotation_y}, expected_max_annotation_y={expected_max_annotation_y}, base_max={base_max}, y_axis_max={y_axis_max}")
                
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
                    title=dict(text=title_text, font=dict(color="#d35400", size=18, family="Arial, sans-serif"), x=0.5, xanchor="center", y=0.98),
                    xaxis=dict(
                        showgrid=True, 
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
                        range=[-0.5, len(years_sorted) - 0.5]
                    ),
                    yaxis=dict(
                        showgrid=True, 
                        gridcolor="#e0e0e0", 
                        title="Production Volume ('000 b/d)", 
                        range=[0, y_axis_max],
                        tickfont=dict(size=11, color="#2c3e50"),
                        titlefont=dict(size=12, color="#2c3e50"),
                        tickmode='linear',
                        tick0=0,
                        dtick=2000,
                        tickformat=',.0f'
                    ),
                    showlegend=False,
                    plot_bgcolor="white",
                    paper_bgcolor="white",
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
                # Monthly view implementation - Show months on X-axis, filter by multiple years from Year of Date filter
                print(f"DEBUG BREAKDOWN MONTHLY: production_years={production_years}, country={country}")
                
                # Handle production_years (Year of Date filter) - use this for the chart
                selected_years = []
                if production_years:
                    if isinstance(production_years, list):
                        selected_years = [str(y) for y in production_years]
                    elif isinstance(production_years, (int, str)):
                        selected_years = [str(production_years)]
                else:
                    # Default to 2024 and 2025
                    selected_years = ["2024", "2025"]
                
                print(f"DEBUG BREAKDOWN MONTHLY: Country={country}, Selected Years={selected_years}, Tab={tab}")
                print(f"DEBUG BREAKDOWN MONTHLY: BAR_LONG_MONTHLY empty={BAR_LONG_MONTHLY.empty}")
                
                available_streams = []
                
                if selected_years and not BAR_LONG_MONTHLY.empty and "year" in BAR_LONG_MONTHLY.columns:
                    print(f"DEBUG BREAKDOWN MONTHLY: Filtering by years={selected_years}, country={country}")
                    print(f"DEBUG BREAKDOWN MONTHLY: BAR_LONG_MONTHLY columns={BAR_LONG_MONTHLY.columns.tolist()}")
                    print(f"DEBUG BREAKDOWN MONTHLY: BAR_LONG_MONTHLY length={len(BAR_LONG_MONTHLY)}")
                    
                    # Filter by country and multiple years (show all months for selected years)
                    country_mask = BAR_LONG_MONTHLY["Country"].isin(country)
                    year_series = BAR_LONG_MONTHLY["year"].astype(str)
                    year_mask = year_series.isin(selected_years)
                    df = BAR_LONG_MONTHLY[country_mask & year_mask].copy()
                    df["year"] = df["year"].astype(str)
                    print(f"DEBUG BREAKDOWN MONTHLY: After country/years filter, df length={len(df)}")
                    
                    # Get available streams from monthly grades CSV for color mapping only
                    # DO NOT filter the data - show ALL streams from the data
                    available_streams = []
                    if not MONTHLY_GRADES_DF.empty and "Stream" in MONTHLY_GRADES_DF.columns:
                        available_streams = order_streams_list(MONTHLY_GRADES_DF["Stream"].dropna().unique().tolist(), tab="monthly")
                        print(f"DEBUG BREAKDOWN MONTHLY: Available streams from grades (for color mapping only): {len(available_streams)}")
                    # DO NOT filter df by available_streams - show all streams in the data
                    all_streams_in_df = sorted(df["Stream"].unique().tolist())
                    print(f"DEBUG BREAKDOWN MONTHLY: All streams in data (NOT filtered by grades CSV): {all_streams_in_df} ({len(all_streams_in_df)} streams)")
                else:
                    print(f"DEBUG BREAKDOWN MONTHLY: BAR_LONG_MONTHLY is empty or missing columns")
                    df = pd.DataFrame(columns=["Stream", "Country", "year", "value", "month_idx"])
                
                if len(df) == 0:
                    print("DEBUG BREAKDOWN MONTHLY: No data after filtering, returning empty chart")
                    # Create empty chart with all months on X-axis
                    month_names = ["January", "February", "March", "April", "May", "June",
                                  "July", "August", "September", "October", "November", "December"]
                    empty_df = pd.DataFrame({"month": month_names, "value": [0]*12})
                    fig = px.bar(empty_df, x="month", y="value", labels={"value":"Avg. Value", "month":"Month"})
                    fig.update_layout(
                        title=dict(text=title_text, font=dict(color="#d35400", size=18, family="Arial, sans-serif"), x=0.5, xanchor="center", y=0.98),
                        xaxis_title="Month",
                        yaxis_title="Avg. Value",
                        barmode="stack",
                        plot_bgcolor="white",
                        paper_bgcolor="white",
                        xaxis=dict(
                            type="category",
                            categoryorder="array",
                            categoryarray=month_names
                        )
                    )
                    return fig, title_text
                
                # Month names / mappings for ordering
                month_names = ["January", "February", "March", "April", "May", "June",
                              "July", "August", "September", "October", "November", "December"]
                month_to_idx = {name: idx+1 for idx, name in enumerate(month_names)}
                idx_to_month = {idx+1: name for idx, name in enumerate(month_names)}
                
                if len(df) > 0:
                    if "month_idx" not in df.columns:
                        df["month_idx"] = df["month"].map(month_to_idx)
                    df["month_idx"] = pd.to_numeric(df["month_idx"], errors="coerce")
                    df["month"] = df["month_idx"].map(idx_to_month)
                    
                    # Apply profiled streams filter if provided
                    all_streams_before_profiled = sorted(df["Stream"].unique().tolist())
                    print(f"DEBUG BREAKDOWN MONTHLY: All streams before profiled filter: {all_streams_before_profiled} ({len(all_streams_before_profiled)} streams)")
                    print(f"DEBUG BREAKDOWN MONTHLY: Profiled filter value: {profiled}")
                    
                    if profiled and len(profiled) > 0:
                        profiled_list = [str(s).strip() for s in profiled] if isinstance(profiled, (list, tuple)) else [str(profiled).strip()]
                        df_streams_list = [str(s).strip() for s in df["Stream"].values]
                        profiled_in_data = [s for s in profiled_list if s in df_streams_list]
                        missing_profiled = [s for s in profiled_list if s not in df_streams_list]
                        print(f"DEBUG BREAKDOWN MONTHLY: Profiled streams in data: {profiled_in_data} ({len(profiled_in_data)} streams)")
                        if missing_profiled:
                            print(f"DEBUG BREAKDOWN MONTHLY: WARNING - Profiled streams NOT in data: {missing_profiled}")
                        if profiled_in_data:
                            df = df[df["Stream"].isin(profiled_in_data)].copy()
                            print(f"DEBUG BREAKDOWN MONTHLY: After profiled filter ({len(profiled_in_data)} streams), df length={len(df)}")
                            print(f"DEBUG BREAKDOWN MONTHLY: Streams after profiled filter: {sorted(df['Stream'].unique().tolist())}")
                        else:
                            print(f"DEBUG BREAKDOWN MONTHLY: No profiled streams found in data, showing all streams")
                    else:
                        print(f"DEBUG BREAKDOWN MONTHLY: No profiled filter or empty, showing all {len(all_streams_before_profiled)} streams")
                    
                    agg = df.groupby(["year", "month_idx", "Stream"])["value"].sum().reset_index()
                    agg["month"] = agg["month_idx"].map(idx_to_month)
                    print(f"DEBUG BREAKDOWN MONTHLY: After grouping by year/month/stream, agg length={len(agg)}")
                else:
                    agg = pd.DataFrame(columns=["year", "month_idx", "Stream", "value", "month"])
                    print(f"DEBUG BREAKDOWN MONTHLY: No data after filtering")
                
                if len(agg) == 0:
                    print("DEBUG BREAKDOWN MONTHLY: No data after profiled filter, returning empty chart")
                    empty_df = pd.DataFrame({
                        "year": selected_years,
                        "month": month_names * max(1, len(selected_years)),
                        "value": [0] * (len(selected_years) * len(month_names))
                    })
                    fig = px.bar(empty_df, x="month", y="value", facet_col="year")
                    fig.update_layout(
                        title=dict(text=title_text, font=dict(color="#d35400", size=18, family="Arial, sans-serif"), x=0.5, xanchor="center", y=0.98),
                        plot_bgcolor="white",
                        paper_bgcolor="white"
                    )
                    return fig, title_text
                
                selected_years_sorted = sorted(set(selected_years), key=lambda y: int(y))
                if not selected_years_sorted:
                    selected_years_sorted = sorted(agg["year"].unique(), key=lambda y: int(y))
                
                # Determine which months actually have data for each selected year
                months_by_year = {}
                year_has_data = {}
                for year in selected_years_sorted:
                    year_data = agg[agg["year"] == year]
                    if len(year_data) == 0:
                        months_by_year[str(year)] = []
                        year_has_data[str(year)] = False
                        continue
                    
                    monthly_totals = year_data.groupby("month_idx")["value"].sum().reset_index()
                    months_with_data = monthly_totals[monthly_totals["value"] > 0]["month_idx"].tolist()
                    months_with_data_names = [idx_to_month[idx] for idx in sorted(months_with_data)]
                    months_by_year[str(year)] = months_with_data_names
                    year_has_data[str(year)] = len(months_with_data_names) > 0
                
                print(f"DEBUG BREAKDOWN MONTHLY: Months by year: {months_by_year}")
                
                # Filter out years with no data
                selected_years_sorted = [y for y in selected_years_sorted if year_has_data.get(str(y), False)]
                if not selected_years_sorted:
                    print("DEBUG BREAKDOWN MONTHLY: No years with data after filtering")
                    fig = go.Figure()
                    fig.add_annotation(
                        text="No monthly data available for selected filters and time period",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=14, color='#7f8c8d')
                    )
                    fig.update_layout(
                        height=400,
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        xaxis=dict(showgrid=False, showticklabels=False),
                        yaxis=dict(showgrid=False, showticklabels=False)
                    )
                    return fig, title_text
                
                # Filter agg to only include years and months that have data
                # This removes blank months from the data before chart creation
                filtered_agg = []
                for year in selected_years_sorted:
                    year_months = months_by_year.get(str(year), [])
                    month_indices = [month_to_idx[m] for m in year_months]
                    year_data = agg[(agg["year"] == year) & (agg["month_idx"].isin(month_indices))]
                    filtered_agg.append(year_data)
                    print(f"DEBUG BREAKDOWN MONTHLY: Year {year}: filtered to {len(year_data)} rows (only months with data: {year_months})")
                
                if filtered_agg:
                    agg = pd.concat(filtered_agg, ignore_index=True)
                else:
                    agg = pd.DataFrame(columns=["year", "month_idx", "Stream", "value", "month"])
                
                print(f"DEBUG BREAKDOWN MONTHLY: Final data shape after removing blank months: {agg.shape}")
                # Verify no blank months in final data
                for year in selected_years_sorted:
                    year_data = agg[agg["year"] == year]
                    months_in_data = sorted(year_data["month"].unique().tolist())
                    expected_months = months_by_year.get(str(year), [])
                    print(f"DEBUG BREAKDOWN MONTHLY: Year {year} - months in final data: {months_in_data}, expected: {expected_months}")
                    if set(months_in_data) != set(expected_months):
                        print(f"DEBUG BREAKDOWN MONTHLY: WARNING - Year {year} has unexpected months in data!")
                print(f"DEBUG BREAKDOWN MONTHLY: Unique streams in final agg: {sorted(agg['Stream'].unique().tolist())}")
                
                # Get all available streams for consistent coloring
                # Prioritize streams that are actually in the data
                streams_in_data = order_streams_list(agg["Stream"].dropna().unique().tolist(), tab="monthly")
                print(f"DEBUG BREAKDOWN MONTHLY: Streams in data (ordered): {streams_in_data}")
                
                # Use streams from data as primary source, merge with grades CSV streams for color mapping
                all_available_streams = streams_in_data if streams_in_data else get_stream_order("monthly")
                # Add any streams from grades CSV that aren't in data (for color mapping consistency)
                if available_streams:
                    for stream in available_streams:
                        if stream not in all_available_streams:
                            all_available_streams.append(stream)
                
                print(f"DEBUG BREAKDOWN MONTHLY: All available streams (for color mapping): {all_available_streams}")
                
                # Use streams_in_data for categories (only streams that actually have data)
                stream_categories = streams_in_data if streams_in_data else get_stream_order("monthly")
                print(f"DEBUG BREAKDOWN MONTHLY: Stream categories (for chart): {stream_categories}")
                
                color_map = {stream: get_stream_color(stream, all_available_streams, tab="monthly") for stream in all_available_streams}
                
                agg = agg[agg["year"].isin(selected_years_sorted)].copy()
                agg["Stream"] = pd.Categorical(agg["Stream"], categories=stream_categories, ordered=True)
                agg["month_order"] = agg["month_idx"]
                agg = agg.sort_values(["year", "month_order", "Stream"])
                
                agg["year"] = pd.Categorical(agg["year"], categories=selected_years_sorted, ordered=True)
                # Use month names directly (not numeric positions) - this works better with Plotly's grouping
                # IMPORTANT: Only use months that have data - don't create categorical with all 12 months
                agg["month"] = agg["month_idx"].map(idx_to_month)
                agg_for_chart = agg.sort_values(["year", "month_order", "Stream"]).copy()
                
                # Convert to string (NOT categorical) to avoid Plotly showing all possible months
                # This ensures only months with actual data are in the chart
                agg_for_chart["Stream"] = agg_for_chart["Stream"].astype(str)
                agg_for_chart["month"] = agg_for_chart["month"].astype(str)
                country_display = ", ".join(country)
                agg_for_chart["country_display"] = country_display
                agg_for_chart["year_label"] = agg_for_chart["year"].astype(str)
                
                # Verify only months with data are present
                for year in selected_years_sorted:
                    year_data = agg_for_chart[agg_for_chart["year"] == year]
                    months_in_chart = sorted(year_data["month"].unique().tolist())
                    expected_months = months_by_year.get(str(year), [])
                    print(f"DEBUG BREAKDOWN MONTHLY: Year {year} - months in chart data: {months_in_chart}, expected: {expected_months}")
                    if set(months_in_chart) != set(expected_months):
                        print(f"DEBUG BREAKDOWN MONTHLY: ERROR - Year {year} has unexpected months! Filtering out blank months...")
                        # Remove any months not in expected_months
                        agg_for_chart = agg_for_chart[
                            ~((agg_for_chart["year"] == year) & (~agg_for_chart["month"].isin(expected_months)))
                        ].copy()
                
                print(f"DEBUG BREAKDOWN MONTHLY: Chart data shape: {agg_for_chart.shape}")
                print(f"DEBUG BREAKDOWN MONTHLY: Unique streams in agg_for_chart: {sorted(agg_for_chart['Stream'].unique().tolist())}")
                print(f"DEBUG BREAKDOWN MONTHLY: Stream categories: {stream_categories}")
                
                years_in_chart = agg_for_chart["year"].astype(str).unique().tolist()
                selected_years_sorted = [y for y in selected_years_sorted if y in years_in_chart]
                print(f"DEBUG BREAKDOWN MONTHLY: Years in chart: {selected_years_sorted}")
                
                print(f"DEBUG BREAKDOWN MONTHLY: Streams in final data: {sorted(agg_for_chart['Stream'].unique().tolist())}")
                print(f"DEBUG BREAKDOWN MONTHLY: Number of unique streams: {len(agg_for_chart['Stream'].unique())}")
                
                # Final verification: ensure no blank months in data
                all_months_in_data = set()
                for year in selected_years_sorted:
                    year_data = agg_for_chart[agg_for_chart["year"] == year]
                    year_months = set(year_data["month"].unique())
                    all_months_in_data.update(year_months)
                    expected = set(months_by_year.get(str(year), []))
                    if year_months != expected:
                        print(f"DEBUG BREAKDOWN MONTHLY: CRITICAL - Year {year} data contains months not in expected list!")
                        print(f"  Data has: {sorted(year_months)}, Expected: {sorted(expected)}")
                        print(f"  Removing unexpected months...")
                        # Keep only expected months for this year
                        mask = (agg_for_chart["year"] != year) | (agg_for_chart["month"].isin(expected))
                        agg_for_chart = agg_for_chart[mask].copy()
                
                print(f"DEBUG BREAKDOWN MONTHLY: Final verification - all months in data: {sorted(all_months_in_data)}")
                
                # Use 0 spacing when we have multiple years (we'll set custom domains)
                # Otherwise use default spacing for single year
                spacing = 0.0 if len(selected_years_sorted) > 1 else 0.04
                
                fig = px.bar(
                    agg_for_chart, 
                    x="month",  # use month labels directly
                    y="value",
                    color="Stream",
                    color_discrete_map=color_map,
                    color_discrete_sequence=get_color_sequence("monthly"),
                    category_orders={
                        "Stream": stream_categories,
                        "year": selected_years_sorted
                        # DO NOT set month in category_orders - let each facet control its own months
                    },
                    facet_col="year",
                    facet_col_spacing=spacing,
                    labels={"value":"Avg. Value", "month":"Month", "Stream":"Stream", "year":"Year"},
                    barmode="stack",
                    custom_data=["month", "country_display", "year_label"]
                )
                # Increase individual bar width after chart creation
                fig.update_traces(width=0.95, selector=dict(type='bar'))
                
                # Debug: Check how many traces were created and which streams they represent
                print(f"DEBUG BREAKDOWN MONTHLY: Number of traces created by Plotly: {len(fig.data)}")
                trace_names = [trace.name for trace in fig.data if trace.name]
                print(f"DEBUG BREAKDOWN MONTHLY: Trace names: {trace_names}")
                print(f"DEBUG BREAKDOWN MONTHLY: Expected streams: {stream_categories}")
                
                # Check if all streams have traces
                missing_traces = [s for s in stream_categories if s not in trace_names]
                if missing_traces:
                    print(f"DEBUG BREAKDOWN MONTHLY: WARNING - Streams without traces: {missing_traces}")
                
                # Check data points per trace
                for trace in fig.data:
                    if trace.name:
                        x_len = len(trace.x) if hasattr(trace, 'x') and trace.x is not None else 0
                        y_max = max(trace.y) if hasattr(trace, 'y') and trace.y is not None and len(trace.y) > 0 else 'N/A'
                        print(f"DEBUG BREAKDOWN MONTHLY: Trace '{trace.name}': {x_len} data points, max y: {y_max}")
                
                # Verify colors are applied correctly and fix if needed
                print(f"DEBUG BREAKDOWN MONTHLY: Verifying trace colors:")
                for trace in fig.data:
                    if trace.name and trace.name in color_map:
                        expected_color = color_map[trace.name]
                        # Get current color from trace
                        current_color = None
                        if hasattr(trace, 'marker') and hasattr(trace.marker, 'color'):
                            current_color = trace.marker.color
                        
                        # Explicitly set the color to ensure it's correct
                        if hasattr(trace, 'marker'):
                            trace.marker.color = expected_color
                            print(f"  Trace '{trace.name}': Set color to {expected_color}")
                
                stack_order = list(reversed(stream_categories))
                order_lookup = {name: idx for idx, name in enumerate(stack_order)}
                fig.data = tuple(
                    sorted(fig.data, key=lambda trace: order_lookup.get(trace.name, len(order_lookup)))
                )
                
                # Ensure month labels only show months with data for each year
                fig.update_traces(
                    marker=dict(line=dict(width=1, color='white')),
                    hovertemplate=(
                        "Month of Date: %{customdata[0]}<br>"
                        "Country: %{customdata[1]}<br>"
                        "Stream Name: %{fullData.name}<br>"
                        "Year of Date: %{customdata[2]}<br>"
                        "Production Volume: %{y:,.0f} (\\'000 b/d)"
                        "<extra></extra>"
                    )
                )
                
                fig.update_yaxes(matches='y')
                # Update general x-axis styling first
                fig.for_each_xaxis(
                    lambda axis: axis.update(
                        showgrid=True,
                        gridcolor="#e0e0e0",
                        tickfont=dict(size=9, color="#2c3e50"),
                        tickangle=-45,
                        showline=True,
                        linewidth=1,
                        linecolor="#c0c0c0",
                        title=""
                    )
                )
                
                # Apply per-year month ordering to x-axes - only show months with data
                # Chart months should be in forward order (January to December), NOT reversed
                # Reverse order is only for the table, not the chart
                print(f"DEBUG BREAKDOWN MONTHLY: Applying x-axis configuration to remove blank months")
                for idx, year in enumerate(selected_years_sorted, start=1):
                    axis_key = f"xaxis{idx}" if idx > 1 else "xaxis"
                    year_data = agg_for_chart[agg_for_chart["year"] == year]
                    months_for_axis = []
                    if len(year_data) > 0:
                        # Sort in forward order (January to December) - ascending=True
                        months_for_axis = (
                            year_data[["month", "month_order"]]
                            .drop_duplicates()
                            .sort_values("month_order", ascending=True)["month"]
                            .tolist()
                        )
                    
                    print(f"DEBUG BREAKDOWN MONTHLY: Year {year} ({axis_key}): months with data = {months_for_axis}")
                    
                    if axis_key in fig.layout and months_for_axis:
                        fig.layout[axis_key].update(
                            type="category",
                            categoryorder="array",
                            categoryarray=months_for_axis,
                            tickmode="array",
                            tickvals=months_for_axis,
                            ticktext=months_for_axis,
                            title=""
                        )
                        print(f"DEBUG BREAKDOWN MONTHLY: Set {axis_key} to show only {len(months_for_axis)} months: {months_for_axis}")
                    elif axis_key in fig.layout:
                        # No data for this year - hide axis
                        print(f"DEBUG BREAKDOWN MONTHLY: No months with data for year {year}, hiding {axis_key}")
                        fig.layout[axis_key].update(
                            showticklabels=False,
                            showgrid=False,
                            title=""
                        )
                fig.for_each_yaxis(
                    lambda axis: axis.update(
                        showgrid=True,
                        gridcolor="#e0e0e0",
                        title="Avg. Value" if axis.anchor == 'x1' else "",
                        tickformat='s',
                        showline=True,
                        linewidth=1,
                        linecolor="#c0c0c0"
                    )
                )
                if "yaxis" in fig.layout:
                    fig.layout["yaxis"].update(title="Avg. Value", tickformat='s')
                if "yaxis" in fig.layout:
                    fig.layout["yaxis"].update(title="Avg. Value")
                fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1], font=dict(size=11, color="#2c3e50")))
                
                cols = min(4, len(selected_years_sorted)) if selected_years_sorted else 1
                rows = math.ceil(len(selected_years_sorted) / cols) if selected_years_sorted else 1
                base_height = 520  # Increased to give monthly facets more vertical space
                
                fig.update_layout(
                    title=dict(text=title_text, font=dict(color="#d35400", size=18, family="Arial, sans-serif"), x=0.5, xanchor="center", y=0.98),
                    showlegend=False,
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    margin=dict(l=70, r=30, t=80, b=120),
                    hovermode='closest',
                    height=base_height * rows,
                    shapes=[dict(
                        type="rect",
                        xref="paper",
                        yref="paper",
                        x0=0,
                        y0=0,
                        x1=1,
                        y1=1,
                        line=dict(color="#bfbfbf", width=1),
                        fillcolor="rgba(0,0,0,0)"
                    )]
                )

                # Adjust spacing/width for monthly bars (visual only, data unchanged)
                fig.update_layout(bargap=0.02, bargroupgap=0.0)
                fig.update_traces(width=0.96, selector=dict(type='bar'))

                # Dynamically allocate facet widths based on months count per year
                if len(selected_years_sorted) > 1:
                    year_month_counts = {}
                    # Ensure we're comparing strings consistently
                    agg_for_chart["year"] = agg_for_chart["year"].astype(str)
                    
                    for year in selected_years_sorted:
                        year_str = str(year)
                        year_data = agg_for_chart[agg_for_chart["year"] == year_str]
                        months_for_year = year_data["month"].nunique() if len(year_data) > 0 else 0
                        year_month_counts[year_str] = max(1, months_for_year)
                        print(f"DEBUG BREAKDOWN MONTHLY: Year {year_str} has {year_month_counts[year_str]} months")

                    total_weight = sum(year_month_counts.values())
                    if total_weight == 0:
                        total_weight = len(selected_years_sorted)
                    gap = 0.02
                    n_years = len(selected_years_sorted)
                    usable_width = 1.0 - gap * (n_years - 1)
                    usable_width = max(0.3, usable_width)
                    unit = usable_width / total_weight if total_weight > 0 else usable_width / n_years
                    current_start = 0.0
                    axis_centers = {}

                    print(f"DEBUG BREAKDOWN MONTHLY: Total weight: {total_weight}, Unit width: {unit}, Usable width: {usable_width}")

                    for idx, year in enumerate(selected_years_sorted, start=1):
                        year_str = str(year)
                        width = unit * year_month_counts.get(year_str, 1)
                        domain_start = current_start
                        domain_end = domain_start + width
                        # Don't force last year to 1.0 - calculate proportionally
                        # Only ensure we don't exceed 1.0
                        domain_end = min(1.0, domain_end)
                        axis_key = f"xaxis{idx}" if idx > 1 else "xaxis"
                        yaxis_key = f"yaxis{idx}" if idx > 1 else "yaxis"

                        print(f"DEBUG BREAKDOWN MONTHLY: Year {year_str} ({axis_key}): domain=[{domain_start:.4f}, {domain_end:.4f}], width={width:.4f}, months={year_month_counts.get(year_str, 1)}")

                        # Update xaxis domain - must be done directly on layout for faceted charts
                        if axis_key in fig.layout:
                            # Force update the domain
                            fig.layout[axis_key].domain = [domain_start, domain_end]
                            axis_centers[year_str] = (domain_start + domain_end) / 2
                            print(f"DEBUG BREAKDOWN MONTHLY: Updated {axis_key}.domain to [{domain_start:.4f}, {domain_end:.4f}]")
                        if yaxis_key in fig.layout:
                            fig.layout[yaxis_key].domain = [0.0, 1.0]

                        current_start = domain_end + (gap if idx < n_years else 0)

                    # Reposition annotations (year labels) to align with new facet widths
                    if hasattr(fig.layout, "annotations"):
                        for ann in fig.layout.annotations:
                            if ann.text:
                                ann_year = ann.text.strip()
                                if ann_year in axis_centers:
                                    ann.update(x=axis_centers[ann_year])
                                    print(f"DEBUG BREAKDOWN MONTHLY: Repositioned annotation for {ann_year} to x={axis_centers[ann_year]:.4f}")
                
                print(f"DEBUG BREAKDOWN MONTHLY: Faceted chart layout updated, returning figure")
                return fig, title_text
        except Exception as e:
            print(f"Error in update_breakdown: {e}")
            import traceback
            traceback.print_exc()
            # Return empty figure on error
            fig = go.Figure()
            fig.add_annotation(
                text="Error loading chart data. Please check filters.",
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
         Input("crude-main-tabs", "value")],
        prevent_initial_call=False
    )
    def filter_table(stream, ci, api, sulfur, year, year_month, country, tab):
        """Filter and update data table"""
        
        # Set defaults if None
        if tab is None:
            tab = "yearly"
        
        if tab == "yearly":
            df = TABLE_DF_YEARLY.copy()
        else:
            df = TABLE_DF_MONTHLY.copy()
        df = df.reset_index(drop=True)
        
        if df.empty:
            return [], []
        
        # Filter by country (only applied to yearly list; monthly table shows all crudes like the Tableau source)
        if country and len(country) > 0 and tab == "yearly":
            if not BAR_LONG_YEARLY.empty and "Country" in BAR_LONG_YEARLY.columns and "Stream" in BAR_LONG_YEARLY.columns:
                country_crudes = BAR_LONG_YEARLY[BAR_LONG_YEARLY["Country"].isin(country)]["Stream"].dropna().unique().tolist()
                if "CrudeOil" in df.columns:
                    df = df[df["CrudeOil"].isin(country_crudes)]
        
        def sanitize(values):
            if not values:
                return []
            return [v for v in values if v and v != "(All)"]
        
        ci = sanitize(ci)
        api = sanitize(api)
        sulfur = sanitize(sulfur)
        
        # Filter by stream name
        if stream:
            col_name = "CrudeOil" if tab == "yearly" else "Crude"
            if col_name in df.columns:
                df = df[df[col_name].astype(str).str.contains(stream, case=False, na=False)]
        
        # Filter by CI Rank, API, Sulfur (only for monthly)
        if tab == "monthly":
            if ci and "CI Rank" in df.columns:
                df = df[df["CI Rank"].isin(ci)]
            if api and "API" in df.columns:
                df = df[df["API"].apply(lambda v: classify_api_value(v) in api)]
            if sulfur and "Sulfur" in df.columns:
                df = df[df["Sulfur"].apply(lambda v: classify_sulfur_value(v) in sulfur)]
        
        if tab == "yearly":
            display_metadata_cols = ["CrudeOil"]
            year_cols = [c for c in df.columns if c not in ["CrudeOil", "CI Rank", "API", "Sulfur"] and str(c).isdigit()]
            year_cols = sorted([int(c) for c in year_cols], reverse=True)
            year_cols = [str(c) for c in year_cols]
            
            # Filter to only show selected years if specified
            if year:
                year_strs = [str(y) for y in year if str(y) in year_cols]
                if year_strs:
                    year_cols = year_strs
            
            display_cols = [c for c in display_metadata_cols if c in df.columns] + year_cols
            columns = []
            for c in display_cols:
                col_def = {"name": str(c), "id": str(c)}
                if c == "CrudeOil":
                    col_def.update({"type": "text", "presentation": "markdown"})
                columns.append(col_def)
            
            df_display = df[display_cols].copy()
            records = df_display.to_dict("records")
            link_col = "profile_url" if "profile_url" in df.columns else None
            for idx, record in enumerate(records):
                link = None
                if link_col and idx < len(df):
                    link_value = df.at[idx, link_col]
                    if pd.notna(link_value):
                        link = link_value
                record["CrudeOil"] = format_with_link(record.get("CrudeOil", ""), link)
            
            return records, columns
        else:
            # Monthly view: Create nested headers with Year -> Month structure
            if "CrudeOil" in df.columns:
                df = df.rename(columns={"CrudeOil": "Crude"})
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
            
            # Month order references
            months_order = ['January', 'February', 'March', 'April', 'May', 'June',
                            'July', 'August', 'September', 'October', 'November', 'December']
            
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
                                            formatted = f"{num_value:,.2f}"
                                        else:
                                            formatted = str(value) if value else ''
                                    except:
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
            
            return table_data, columns


# ------------------------------------------------------------------------------
# DASH APP CREATION
# ------------------------------------------------------------------------------
def create_crude_overview_dashboard(server, url_base_pathname="/dash/crude-overview/"):
    """Create the Crude Overview dashboard"""
    dash_app = create_dash_app(server, url_base_pathname)
    dash_app.layout = create_layout(server)
    register_callbacks(dash_app, server)
    return dash_app
