# crude_profile.py
"""
Crude Profile Dashboard - Complete Implementation with Grouped Tables for Refined Products
"""
from dash import dcc, html, Dash, Input, Output, State, callback_context, ctx, dash_table, no_update
import dash
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os
import re
import numpy as np
from datetime import datetime, date, timedelta
from core.data_helpers import execute_query

# ------------------------------------------------------------------------------
# FILE PATHS
# ------------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "Crude_Profile")

CSV_PATHS = {
    "assay_details": os.path.join(DATA_DIR, "Assay_Details_data(1).csv"),
    "quality_specs": os.path.join(DATA_DIR, "Latest_Quality_Specs_data(1).csv"),
    # Mars assay and refined products are now loaded dynamically from the database.
    # These CSV paths are kept only as potential future fallbacks.
    "mars_assay": os.path.join(DATA_DIR, "Mars_Blend_Assay(1).csv"),
    "refined_products": os.path.join(DATA_DIR, "Refined_Products_Breakdown_and_Properties_data(1).csv"),
    "production_exports": os.path.join(DATA_DIR, "Production_and_Exports_Chart_Production_Exports.csv"),
    "loading_ports": os.path.join(DATA_DIR, "Country_Map_data(1).csv"),
    "port_details": os.path.join(DATA_DIR, "Loading_Port_Details_data(1).csv"),
    "producers_sellers": os.path.join(DATA_DIR, "Producers_Sellers_table_data(1).csv")
}

# ------------------------------------------------------------------------------
# DATA LOADING FUNCTIONS - UPDATED FOR GROUPED REFINED PRODUCTS
# ------------------------------------------------------------------------------
def load_csv_data(file_path, fallback_data=None, **read_kwargs):
    """Load CSV data with fallback to sample data if file not found."""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return fallback_data
    
    # Extract encoding if specified, but try multiple encodings
    specified_encoding = read_kwargs.pop("encoding", None)
    if specified_encoding:
        # If encoding is specified, try it first, then fall back to others
        encodings_to_try = [specified_encoding, "utf-8", "utf-8-sig", "latin-1"]
    else:
        encodings_to_try = ["utf-8", "utf-8-sig", "latin-1", "utf-16"]
    
    last_error = None
    base_kwargs = read_kwargs or {}
    
    for enc in encodings_to_try:
        try:
            kwargs = dict(base_kwargs)
            if enc:
                kwargs["encoding"] = enc
            df = pd.read_csv(file_path, **kwargs)
            print(f"✅ Loaded {os.path.basename(file_path)} (encoding={enc})")
            return df
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except Exception as e:
            # For non-encoding errors, try next encoding or return fallback
            if "header" in str(e).lower() or "lines" in str(e).lower():
                # Header/line count errors - try with different header values
                if "header" in base_kwargs:
                    header_val = base_kwargs["header"]
                    # Try with header=0, then header=1, then header=None
                    for alt_header in [0, 1, None]:
                        if alt_header != header_val:
                            try:
                                kwargs = dict(base_kwargs)
                                kwargs["header"] = alt_header
                                if enc:
                                    kwargs["encoding"] = enc
                                df = pd.read_csv(file_path, **kwargs)
                                print(f"✅ Loaded {os.path.basename(file_path)} (encoding={enc}, header={alt_header})")
                                return df
                            except Exception:
                                continue
            last_error = e
            continue
    
    print(f"❌ Error loading {file_path}: {last_error}")
    return fallback_data

def load_assay_details():
    """Load assay details data."""
    df = load_csv_data(CSV_PATHS["assay_details"])
    if df is None or df.empty:
        return {"alternate_names": "", "country": "United States", "assay_date": "2025"}
    
    # Assuming CSV has columns: Alternate_Names, Country, Assay_Date
    return {
        "alternate_names": df.iloc[0]["Alternate_Names"] if "Alternate_Names" in df.columns else "",
        "country": df.iloc[0]["Country"] if "Country" in df.columns else "United States",
        "assay_date": df.iloc[0]["Assay_Date"] if "Assay_Date" in df.columns else "2025"
    }

def load_quality_specs():
    """Load latest quality specs data."""
    df = load_csv_data(CSV_PATHS["quality_specs"])
    if df is None or df.empty:
        return [("Gravity (API at 60F)", "28.40"), ("Sulfur Content (% Wt)", "2.17"), ("TAN (mg KOH/g)", "0.48")]
    
    specs = []
    for _, row in df.iterrows():
        if "Property" in df.columns and "Value" in df.columns:
            specs.append((row["Property"], row["Value"]))
    return specs

def load_crude_options():
    """
    Load distinct crude list for the dropdown from the assays table.
    Uses Crudeoil (a.crude_name) both as label and value.
    """
    query = """
        SELECT DISTINCT 
            a.crude_name AS "Crudeoil"
        FROM fact_wcod_assays a
        WHERE a.to_be_deleted IS NULL
        ORDER BY a.crude_name
    """
    try:
        results = execute_query(query)
    except Exception as e:
        print(f"❌ Error loading crude options from DB: {e}")
        # Fallback to single Mars Blend option
        return [{"label": "Mars Blend", "value": "Mars Blend"}], "Mars Blend"

    if not results:
        return [{"label": "Mars Blend", "value": "Mars Blend"}], "Mars Blend"

    df = pd.DataFrame(results)
    if "Crudeoil" not in df.columns:
        return [{"label": "Mars Blend", "value": "Mars Blend"}], "Mars Blend"

    df["Crudeoil"] = df["Crudeoil"].fillna("").astype(str).str.strip()
    df = df[df["Crudeoil"] != ""]

    if df.empty:
        return [{"label": "Mars Blend", "value": "Mars Blend"}], "Mars Blend"

    options = [{"label": c, "value": c} for c in df["Crudeoil"].unique()]

    # Default to Mars Blend if present, otherwise first option
    default_value = "Mars Blend"
    if default_value not in df["Crudeoil"].values:
        default_value = df["Crudeoil"].iloc[0]

    return options, default_value


def _get_crude_name_from_value(crude_value: str | None) -> str:
    """
    Map dropdown value to database crude_name.
    For this dashboard we simply use the crude name itself as the value,
    with a safe default of 'Mars Blend' when nothing is selected.
    """
    if not crude_value:
        return "Mars Blend"
    return crude_value


def _load_crude_assay_df(crude_value: str | None = None) -> pd.DataFrame:
    """
    Load crude assay data from the database for a given crude selection.

    Returns a DataFrame with at least:
        crude_id, Crudeoil, profile_url, country_name, product, property,
        Value, unit, cut_point, cut_point_sort, assay_yr, crude_alias
    """
    crude_name = _get_crude_name_from_value(crude_value)

    query = """
        SELECT 
            a.crude_id AS crude_id,
            a.crude_name AS "Crudeoil",
            b.bsp_link AS profile_url,
            a.country_name,
            a.product,
            a.property,
            a.value AS "Value",
            a.unit,
            a.cut_point,
            a.cut_point_sort,
            a.assay_yr,
            c.crude_alias
        FROM fact_wcod_assays a
        LEFT JOIN fact_wcod_crude_bsp_links b 
               ON a.crude_id = b.crude_id
        LEFT JOIN fact_wcod_crude c 
               ON a.crude_id = c.crude_id
        WHERE a.to_be_deleted IS NULL
          AND a.crude_name = :crude_name AND a.product = 'Crude Oil'
    """

    try:
        print(f"🔍 Querying DB for crude_name: '{crude_name}'")
        results = execute_query(query, {"crude_name": crude_name})
        print(f"✅ Query returned {len(results) if results else 0} rows")
    except Exception as e:
        print(f"❌ Error loading crude assay data from DB: {e}")
        return pd.DataFrame()

    if not results:
        print(f"⚠️ No assay data returned from DB for crude_name '{crude_name}', falling back to CSV (if available).")
        return pd.DataFrame()

    return pd.DataFrame(results)


def _load_refined_products_df(crude_value: str | None = None) -> pd.DataFrame:
    """
    Load refined products data from the database for a given crude selection.
    This excludes 'Crude Oil' products (only refined products).

    Returns a DataFrame with at least:
        crude_id, Crudeoil, profile_url, country_name, product, property,
        Value, unit, cut_point, cut_point_sort, assay_yr, crude_alias
    """
    crude_name = _get_crude_name_from_value(crude_value)

    query = """
        SELECT 
            a.crude_id AS crude_id,
            a.crude_name AS "Crudeoil",
            b.bsp_link AS profile_url,
            a.country_name,
            a.product,
            a.property,
            a.value AS "Value",
            a.unit,
            a.cut_point,
            a.cut_point_sort,
            a.assay_yr,
            c.crude_alias
        FROM fact_wcod_assays a
        LEFT JOIN fact_wcod_crude_bsp_links b 
               ON a.crude_id = b.crude_id
        LEFT JOIN fact_wcod_crude c 
               ON a.crude_id = c.crude_id
        WHERE a.to_be_deleted IS NULL
          AND a.crude_name = :crude_name AND a.product != 'Crude Oil'
    """

    try:
        print(f"🔍 Querying DB for refined products (crude_name: '{crude_name}')")
        results = execute_query(query, {"crude_name": crude_name})
        print(f"✅ Refined products query returned {len(results) if results else 0} rows")
    except Exception as e:
        print(f"❌ Error loading refined products data from DB: {e}")
        return pd.DataFrame()

    if not results:
        print(f"⚠️ No refined products data returned from DB for crude_name '{crude_name}', falling back to CSV (if available).")
        return pd.DataFrame()

    return pd.DataFrame(results)


def load_mars_assay(crude_value: str | None = None):
    """Load Mars Blend Assay data from the database with merged Property column for Viscosity."""
    df = _load_crude_assay_df(crude_value)

    if df is None or df.empty:
        # Fallback to static sample if nothing from DB
        return [
            {"Property": "Barrels", "Unit": "Per Metric Ton", "Value": "7.13"},
        ]

    # Normalize and select relevant columns
    df_assay = df.copy()
    # Standardise column names used for the Mars Assay table
    df_assay.rename(
        columns={
            "property": "Property",
            "unit": "Unit",
        },
        inplace=True,
    )

    # If DB already uses title‑case columns, keep them
    for col in ["Property", "Unit", "Value"]:
        if col not in df_assay.columns and col.lower() in df_assay.columns:
            df_assay[col] = df_assay[col.lower()]

    # Drop rows without a property label
    df_assay["Property"] = df_assay["Property"].fillna("").astype(str).str.strip()
    df_assay["Unit"] = df_assay.get("Unit", "").fillna("").astype(str).str.strip()
    df_assay["Value"] = df_assay.get("Value", "").astype(str).str.strip()

    # Normalise property names so viscosity rows can be grouped under one heading
    def normalise_property(p: str) -> str:
        p_lower = p.lower().strip()
        if "viscos" in p_lower:
            return "Viscosity"
        return p.strip()

    df_assay["Property_norm"] = df_assay["Property"].apply(normalise_property)

    # Deduplicate: Remove exact duplicates (same Property+Unit+Value)
    # For Viscosity, we want to keep multiple entries with different units (temperatures)
    # For other properties, we also want to keep only unique Property+Unit combinations
    # First, remove exact duplicates on Property+Unit+Value
    df_assay_dedup = df_assay.drop_duplicates(
        subset=["Property_norm", "Unit", "Value"],
        keep="first"
    )
    
    # For non-Viscosity properties, if there are still duplicates with same Property+Unit but different values,
    # keep only the first one (or you could use assay_yr to get the latest)
    is_viscosity = df_assay_dedup["Property_norm"].str.lower().str.contains("viscos", na=False)
    
    # For non-viscosity properties, deduplicate on Property+Unit (keep first occurrence)
    df_non_viscosity = df_assay_dedup[~is_viscosity].drop_duplicates(
        subset=["Property_norm", "Unit"],
        keep="first"
    )
    
    # For viscosity, keep all unique Property+Unit combinations (already deduplicated above)
    df_viscosity = df_assay_dedup[is_viscosity]
    
    # Combine back
    df_assay_dedup = pd.concat([df_viscosity, df_non_viscosity], ignore_index=True)

    assay_data = []
    for _, row in df_assay_dedup.iterrows():
        prop = row.get("Property_norm", "")
        if not prop:
            continue
        
        # Format Value to 2 decimal places
        value_str = str(row.get("Value", "")).strip()
        try:
            # Try to convert to float and format to 2 decimal places
            value_float = float(value_str)
            value_formatted = f"{value_float:.2f}"
        except (ValueError, TypeError):
            # If conversion fails, keep original value
            value_formatted = value_str
        
        assay_data.append(
            {
                "Property": prop,
                "Unit": row.get("Unit", ""),
                "Value": value_formatted,
            }
        )

    # Process Viscosity entries to merge them under one Property (visual merge)
    if assay_data:
        viscosity_rows = []
        other_rows = []

        for row in assay_data:
            if row["Property"] == "Viscosity":
                viscosity_rows.append(row)
            else:
                other_rows.append(row)

        def get_temp_order(unit_val):
            unit_str = str(unit_val).lower()
            if "20" in unit_str:
                return 0
            elif "40" in unit_str:
                return 1
            elif "50" in unit_str:
                return 2
            return 999

        viscosity_rows.sort(key=lambda x: get_temp_order(x["Unit"]))

        processed_assay_data = other_rows.copy()

        if viscosity_rows:
            first_viscosity = viscosity_rows[0]
            first_viscosity["Property"] = "Viscosity"
            processed_assay_data.append(first_viscosity)

            for viscosity_row in viscosity_rows[1:]:
                viscosity_row["Property"] = ""  # Empty for merged appearance
                processed_assay_data.append(viscosity_row)

        assay_data = processed_assay_data

    return assay_data if assay_data else [
        {"Property": "Barrels", "Unit": "Per Metric Ton", "Value": "7.13"}
    ]

def load_refined_products(crude_value: str | None = None):
    """
    Load refined products breakdown data from the database with merged cells
    for Product and Cut Points.

    Mapping from query:
        a.product  → Product
        a.cut_point → Cut Points (°C)
        a.property → Property
        a.unit → Unit
        a.value → Value
    """
    df = _load_refined_products_df(crude_value)

    if df is None or df.empty:
        # Fallback data with merged format (same as previous CSV-based fallback)
        return [
            {
                "Product": "Heavy Gasoil",
                "Cut Points (°C)": "300-350",
                "properties": [
                    {"Property": "", "Unit": "Yield Volume (%)", "Value": "7.80"},
                    {"Property": "", "Unit": "Yield Weight (%)", "Value": "7.74"},
                    {"Property": "Pour Point", "Unit": "Temp. C", "Value": "-6.83"},
                    {"Property": "Sulfur Content", "Unit": "% Wt", "Value": "1.57"},
                ],
            }
        ]

    df_ref = df.copy()

    # Ensure we have the expected columns
    # DB columns might be lowercase; keep both variants
    # Check what columns we actually have
    print(f"🔍 Available columns in refined products df: {list(df_ref.columns)}")
    
    for src, dst in [
        ("product", "Product"),
        ("cut_point", "Cut Points (°C)"),
        ("property", "Property"),
        ("unit", "Unit"),
        ("Value", "Value"),
    ]:
        if dst not in df_ref.columns:
            if src in df_ref.columns:
                df_ref[dst] = df_ref[src]
                print(f"✅ Mapped '{src}' → '{dst}'")
            else:
                print(f"⚠️ Column '{src}' not found in dataframe")
    
    # Also check for case variations
    if "Cut Points (°C)" not in df_ref.columns:
        # Try to find cut_point column with any case
        for col in df_ref.columns:
            if "cut" in col.lower() and "point" in col.lower():
                df_ref["Cut Points (°C)"] = df_ref[col]
                print(f"✅ Found and mapped cut_point column: '{col}' → 'Cut Points (°C)'")
                break

    # Drop rows without product or property – those won't show in refined products table
    df_ref["Product"] = df_ref["Product"].fillna("").astype(str).str.strip()
    
    # Handle Cut Points column - ensure it exists
    if "Cut Points (°C)" not in df_ref.columns:
        df_ref["Cut Points (°C)"] = ""
    else:
        df_ref["Cut Points (°C)"] = (
            df_ref["Cut Points (°C)"].fillna("").astype(str).str.strip()
        )
    
    # Debug: Check cut_point values
    if "Cut Points (°C)" in df_ref.columns:
        unique_cut_points = df_ref["Cut Points (°C)"].unique()
        print(f"🔍 Unique Cut Points values: {unique_cut_points[:10]}")  # Show first 10
    
    # Handle Property column - allow null/empty values (for Yield Volume/Weight entries)
    df_ref["Property"] = df_ref["Property"].fillna("").astype(str).str.strip()
    df_ref["Unit"] = df_ref.get("Unit", "").fillna("").astype(str).str.strip()
    df_ref["Value"] = df_ref.get("Value", "").astype(str).str.strip()

    # Filter: Keep rows that have Product AND (Property OR Unit OR Value)
    # This includes rows where Property is null but Unit/Value exist (Yield Volume/Weight)
    df_ref = df_ref[
        (df_ref["Product"] != "") & 
        ((df_ref["Property"] != "") | (df_ref["Unit"] != "") | (df_ref["Value"] != ""))
    ]

    # Deduplicate: Remove exact duplicates (same Product + Cut Points + Property + Unit + Value)
    # Keep only the first occurrence of each unique combination
    df_ref = df_ref.drop_duplicates(
        subset=["Product", "Cut Points (°C)", "Property", "Unit", "Value"],
        keep="first"
    )

    if df_ref.empty:
        return [
            {
                "Product": "Heavy Gasoil",
                "Cut Points (°C)": "300-350",
                "properties": [
                    {"Property": "", "Unit": "Yield Volume (%)", "Value": "7.80"},
                    {"Property": "", "Unit": "Yield Weight (%)", "Value": "7.74"},
                    {"Property": "Pour Point", "Unit": "Temp. C", "Value": "-6.83"},
                    {"Property": "Sulfur Content", "Unit": "% Wt", "Value": "1.57"},
                ],
            }
        ]

    # If cut_point_sort is available use it to order within each product / cut point
    sort_cols = []
    if "cut_point_sort" in df_ref.columns:
        sort_cols.append("cut_point_sort")
    sort_cols.extend(["Product", "Cut Points (°C)", "Property"])
    df_ref = df_ref.sort_values(sort_cols)

    # Forward fill Cut Points within each Product group
    # This handles cases where cut_point might be empty for some rows but present for others in the same product
    # Use backward fill first to get cut_points from rows where property is null (Yield Volume/Weight rows)
    if "Cut Points (°C)" in df_ref.columns:
        df_ref["Cut Points (°C)"] = df_ref.groupby("Product")["Cut Points (°C)"].transform(
            lambda x: x.bfill().ffill().fillna("")
        )
    
    # Build grouped structure - GROUP BY PRODUCT ONLY (not Product + Cut Points)
    # This ensures all properties for the same product are grouped together
    grouped_products = []

    for product, group in df_ref.groupby("Product", sort=False):
        # Get the cut_points value for this product - use the first non-empty value
        cut_points_series = group["Cut Points (°C)"].dropna()
        cut_points_series = cut_points_series[cut_points_series.astype(str).str.strip() != ""]
        
        if len(cut_points_series) > 0:
            cut_points_value = str(cut_points_series.iloc[0]).strip()
        else:
            cut_points_value = ""
        
        print(f"🔍 Grouping: Product='{product}', Cut Points='{cut_points_value}', Total Rows={len(group)}")
        
        # Collect all properties for this product
        properties = []
        for _, row in group.iterrows():
            # Format Value to 2 decimal places
            value_str = str(row.get("Value", "")).strip()
            try:
                # Try to convert to float and format to 2 decimal places
                value_float = float(value_str)
                value_formatted = f"{value_float:.2f}"
            except (ValueError, TypeError):
                # If conversion fails, keep original value
                value_formatted = value_str
            
            properties.append(
                {
                    "Property": row.get("Property", ""),
                    "Unit": row.get("Unit", ""),
                    "Value": value_formatted,
                }
            )

        grouped_products.append(
            {
                "Product": product,
                "Cut Points (°C)": cut_points_value,
                "properties": properties,
            }
        )

    if not grouped_products:
        grouped_products = [
            {
                "Product": "Heavy Gasoil",
                "Cut Points (°C)": "300-350",
                "properties": [
                    {"Property": "", "Unit": "Yield Volume (%)", "Value": "7.80"},
                    {"Property": "", "Unit": "Yield Weight (%)", "Value": "7.74"},
                    {"Property": "Pour Point", "Unit": "Temp. C", "Value": "-6.83"},
                    {"Property": "Sulfur Content", "Unit": "% Wt", "Value": "1.57"},
                ],
            }
        ]

    return grouped_products

def load_production_exports():
    """Load production and exports data for chart."""
    fallback = {
        'years': ['2006', '2007', '2008', '2009', '2010', '2011', '2012', '2013', '2014',
                  '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024'],
        'production': [235, 290, 220, 225, 200, 190, 150, 145, 170, 100, 200, 205, 225, 280, 270, 250, 235, 220, 215],
        'exports': [5, 5, 5, 5, 5, 5, 5, 5, 75, 65, 50, 75, 115, 170, 110, 150, 160, 160, 115]
    }
    df = load_csv_data(CSV_PATHS["production_exports"])
    if df is None or df.empty:
        return fallback
    
    chart_data = {'years': [], 'production': [], 'exports': []}
    
    for _, row in df.iterrows():
        if 'Year' in df.columns:
            chart_data['years'].append(str(row['Year']))
        if 'Production' in df.columns:
            chart_data['production'].append(row['Production'])
        if 'Exports' in df.columns:
            chart_data['exports'].append(row['Exports'])
    
    # Ensure we have usable values; otherwise return fallback static data
    if not chart_data['years'] or not chart_data['production'] or not chart_data['exports']:
        return fallback
    
    return chart_data

def load_port_details():
    """Load port details data."""
    fallback_rows = [
        ("Berths", "4"),
        ("Max Draft (meters)", "23.5"),
        ("Max Length (meters)", "366"),
        ("Max Loading Rate (bbl/hour)", "80,000"),
        ("Max Tonnage (dwt)", "250,000"),
        ("Mooring Type", "Single Point"),
        ("Storage Capacity (million bbl)", "12.5")
    ]
    fallback_label = "Loop, Clovelly"
    
    # Use header=0 since the CSV has headers in the first row
    df = load_csv_data(CSV_PATHS["port_details"], header=0)
    if df is None or df.empty or "Measure" not in df.columns:
        return {"label": fallback_label, "rows": fallback_rows}
    
    # Try to find value column (could be "value", "Port Name", or any other column)
    value_col = None
    for col in df.columns:
        if col.lower() in ["value", "port name"] or (col != "Measure" and col not in ["Source", "Copyright"]):
            value_col = col
            break
    
    if not value_col:
        # Use first non-Measure column
        value_columns = [col for col in df.columns if col != "Measure" and col not in ["Source", "Copyright"]]
        if value_columns:
            value_col = value_columns[0]
        else:
            return {"label": fallback_label, "rows": fallback_rows}
    
    column_label = value_col if value_col != "value" else "Loop, Clovelly"
    
    df[value_col] = df[value_col].fillna("").astype(str).str.strip()
    
    # Load all rows
    port_details = []
    for _, row in df.iterrows():
        measure = str(row.get("Measure", "")).strip() if "Measure" in row and pd.notna(row.get("Measure")) else ""
        value = str(row.get(value_col, "")).strip() if value_col in row and pd.notna(row.get(value_col)) else ""
        if measure:
            port_details.append((measure, value if value else ""))
    
    # Return all rows even if values are empty
    rows = port_details if port_details else fallback_rows
    label = column_label if port_details else fallback_label
    
    return {
        "label": label,
        "rows": rows
    }

def load_loading_ports():
    """Load loading ports data for the map."""
    fallback = [{
        "port": "Loop, Clovelly",
        "country": "United States",
        "crude": "Mars Blend",
        "latitude": 29.1175,
        "longitude": -90.0715
    }]
    
    df = load_csv_data(
        CSV_PATHS["loading_ports"],
        sep="\t"
    )
    if df is None or df.empty:
        return fallback
    
    # Check and process Latitude column
    if "Latitude" in df.columns:
        df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    else:
        return fallback
    
    # Check and process Longitude column
    if "Longitude" in df.columns:
        df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    else:
        return fallback
    
    # Check and process Port Name column
    if "Port Name" in df.columns:
        df["Port Name"] = df["Port Name"].fillna("").astype(str).str.strip()
    else:
        return fallback
    
    # Check and process Country column
    if "Country" in df.columns:
        df["Country"] = df["Country"].fillna("").astype(str).str.strip()
    else:
        df["Country"] = ""
    
    # Check and process Crude column
    if "Crude" in df.columns:
        df["Crude"] = df["Crude"].fillna("").astype(str).str.strip()
    else:
        df["Crude"] = ""
    
    records = []
    for _, row in df.iterrows():
        lat = row.get("Latitude") if "Latitude" in row else None
        lon = row.get("Longitude") if "Longitude" in row else None
        name = row.get("Port Name", "") if "Port Name" in row else ""
        if pd.notna(lat) and pd.notna(lon) and name:
            records.append({
                "port": name,
                "country": row.get("Country", "") if "Country" in row else "",
                "crude": row.get("Crude", "") if "Crude" in row else "",
                "latitude": lat,
                "longitude": lon
            })
    
    return records or fallback

def load_producers_sellers():
    """Load producers and sellers data."""
    fallback = [("BP, ConocoPhillips, Exxon Mobil, Shell", "BP America Inc., ConocoPhillips, Exxon Mobil, Shell")]
    
    # Use header=0 since the CSV has headers in the first row
    df = load_csv_data(CSV_PATHS["producers_sellers"], header=0)
    if df is None or df.empty or "Producers" not in df.columns:
        return fallback
    
    # Load all rows
    records = []
    for _, row in df.iterrows():
        producers = str(row.get("Producers", "")).strip() if "Producers" in row and pd.notna(row.get("Producers")) else ""
        sellers = str(row.get("Sellers", "")).strip() if "Sellers" in row and pd.notna(row.get("Sellers")) else ""
        if producers or sellers:
            records.append((producers, sellers))
    
    return records if records else fallback

# ------------------------------------------------------------------------------
# CREATING GROUPED TABLES
# ------------------------------------------------------------------------------
def create_grouped_refined_products_table(crude_value: str | None = None):
    """Create a grouped Refined Products table with merged Product and Cut Points cells."""
    grouped_data = load_refined_products(crude_value)
    
    # Sort grouped_data by Product to ensure all rows for same product are together
    grouped_data = sorted(grouped_data, key=lambda x: (x["Product"], x.get("Cut Points (°C)", "")))
    
    # Convert grouped data to flat rows for DataTable
    # Track current product and cut_points to only show them once
    table_data = []
    current_product = None
    current_cut_points = None
    product_row_start_index = None
    
    for product_group in grouped_data:
        product = product_group["Product"]
        cut_points = product_group["Cut Points (°C)"]
        properties = product_group["properties"]
        
        # Check if this is a new product
        is_new_product = (product != current_product)
        if is_new_product:
            current_product = product
            product_row_start_index = len(table_data)
        
        # Check if this is a new cut_point for the same product
        is_new_cut_point = (cut_points != current_cut_points)
        if is_new_cut_point:
            current_cut_points = cut_points
        
        for i, prop in enumerate(properties):
            # Show Product only on the very first row of each product
            show_product = (is_new_product and i == 0)
            # Show Cut Points on first row of each cut_point group
            show_cut_points = (is_new_cut_point and i == 0)
            
            # Ensure empty strings are truly empty (not None or whitespace)
            product_value = product if show_product else ""
            cut_points_value = cut_points if show_cut_points else ""
            
            table_data.append({
                "Product": product_value,
                "Cut Points (°C)": cut_points_value,
                "Property": prop.get("Property", ""),
                "Unit": prop.get("Unit", ""),
                "Value": prop.get("Value", "")
            })
        
        # Reset flags after processing all properties in this group
        is_new_product = False
        is_new_cut_point = False
    
    # Debug: Print first few rows to verify structure
    if table_data:
        print(f"🔍 First 5 rows of table_data:")
        for idx, row in enumerate(table_data[:5]):
            print(f"  Row {idx}: Product='{row['Product']}', Cut Points='{row['Cut Points (°C)']}', Property='{row['Property']}'")
    
    # Create DataTable with custom CSS for merged cells
    return dash_table.DataTable(
        id='refined-products-table',
        columns=[
            {"name": "Product", "id": "Product", "presentation": "markdown"},
            {"name": "Cut Points (°C)", "id": "Cut Points (°C)", "presentation": "markdown"},
            {"name": "Property", "id": "Property", "presentation": "markdown"},
            {"name": "Unit", "id": "Unit", "presentation": "markdown"},
            {"name": "Value", "id": "Value", "presentation": "markdown"},
        ],
        data=table_data,
        style_table={
            "width": "100%",
            "marginBottom": "15px",
            "fontFamily": "Arial, sans-serif",
            "position": "relative",
            "height": "1360px",  # Reduced height
            "overflowY": "auto",  # Add vertical scroll
            "overflowX": "auto",  # Keep horizontal scroll if needed
            "border": "1px solid #ddd",  # Add border for better visibility
            
        },
        style_cell={
            "border": "1px solid #ddd",
            "padding": "8px 10px",
            "fontSize": "11px",
            "textAlign": "left",
            "backgroundColor": "white",
            "fontFamily": "Arial, sans-serif",
            "whiteSpace": "normal",
            "height": "auto",
            "minHeight": "35px",
            "verticalAlign": "middle",
             "maxWidth": "150px",
        },
        style_header={
            "backgroundColor": "#f5f5f5",
            "fontWeight": "bold",
            "fontSize": "12px",
            "border": "1px solid #ddd",
            "padding": "10px",
            "textAlign": "left",
            "position": "sticky",  # Make header sticky
            "top": "0",
            "zIndex": "10",
        },
        style_data={
            "whiteSpace": "normal",
            "height": "auto"
        },
        style_data_conditional=[
            # Alternate row colors for better readability
            {"if": {"row_index": "odd"}, "backgroundColor": "#f9f9f9"},
            {"if": {"row_index": "even"}, "backgroundColor": "#FFFFFF"},
            
            # Product column styling
            {
                "if": {"column_id": "Product", "filter_query": '{Product} != ""'},
                "fontWeight": "bold",
                "color": "#1f3263",
                "borderRight": "2px solid #ccc"
            },
            {
                "if": {"column_id": "Product", "filter_query": '{Product} = ""'},
                "borderTop": "none",
                "borderBottom": "none",
                "backgroundColor": "inherit",
            },
            
            # Cut Points column styling
            {
                "if": {"column_id": "Cut Points (°C)", "filter_query": '{Cut Points (°C)} != ""'},
                "fontWeight": "bold",
                "color": "#1f3263",
                "borderRight": "1px solid #ddd"
            },
            {
                "if": {"column_id": "Cut Points (°C)", "filter_query": '{Cut Points (°C)} = ""'},
                "borderTop": "none",
                "borderBottom": "none",
                "backgroundColor": "inherit",
            },
            
            # Property column styling
            {
                "if": {"column_id": "Property", "filter_query": '{Property} != ""'},
                "fontWeight": "600",
                "color": "#1f3263",
            },
        ],
        css=[
            # Hide empty Product cells to create merged appearance
            {
                'selector': '#refined-products-table .dash-cell[data-dash-column="Product"]:empty',
                'rule': '''
                    border-top: none !important;
                    border-bottom: none !important;
                    background-image: none !important;
                    height: 0 !important;
                    min-height: 0 !important;
                    padding-top: 0 !important;
                    padding-bottom: 0 !important;
                '''
            },
            # Hide Product cells that contain only whitespace (Dash might render empty strings as whitespace)
            {
                'selector': '#refined-products-table .dash-cell[data-dash-column="Product"]',
                'rule': '''
                    /* Additional rule for empty content */
                '''
            },
            # Ensure the cell above has proper bottom border
            {
                'selector': '#refined-products-table .dash-cell[data-dash-column="Product"]:not(:empty) + .dash-cell[data-dash-column="Product"]:empty',
                'rule': 'border-top: none !important;'
            },
            # Hide empty Cut Points cells to create merged appearance
            {
                'selector': '#refined-products-table .dash-cell[data-dash-column="Cut Points (°C)"]:empty',
                'rule': '''
                    border-top: none !important;
                    border-bottom: none !important;
                    background-image: none !important;
                    height: 0 !important;
                    min-height: 0 !important;
                    padding-top: 0 !important;
                    padding-bottom: 0 !important;
                '''
            },
            # Ensure the cell above has proper bottom border
            {
                'selector': '#refined-products-table .dash-cell[data-dash-column="Cut Points (°C)"]:not(:empty) + .dash-cell[data-dash-column="Cut Points (°C)"]:empty',
                'rule': 'border-top: none !important;'
            },
            # Stronger border for Product column
            {
                'selector': '.dash-cell[data-dash-column="Product"]',
                'rule': 'border-right: 2px solid #ccc !important;'
            },
            # Medium border for Cut Points column
            {
                'selector': '.dash-cell[data-dash-column="Cut Points (°C)"]',
                'rule': 'border-right: 1px solid #ddd !important;'
            },
        ],
        markdown_options={"html": True},
        editable=False,
        sort_action="native",
        filter_action="none",
        page_action="none",
    )

def create_grouped_assay_table(crude_value: str | None = None):
    """Create Mars Blend Assay table with merged Property cells for Viscosity."""
    assay_data = load_mars_assay(crude_value)
    
    return dash_table.DataTable(
        id="assay-table",
        data=assay_data,
        columns=[
            {"name": "Property", "id": "Property", "presentation": "markdown"},
            {"name": "Unit", "id": "Unit", "presentation": "markdown"}, 
            {"name": "Value", "id": "Value", "presentation": "markdown"}
        ],
        style_table={
            "overflowX": "auto",
            "overflowY": "auto",
            "maxHeight": "500px",
            "border": "1px solid #d9d9d9",
            "backgroundColor": "white",
            "position": "relative",
        },
        style_cell={
            "textAlign": "left",
            "padding": "8px 12px",
            "fontSize": "11px",
            "fontFamily": "Arial, sans-serif",
            "border": "1px solid #e0e0e0",
            "whiteSpace": "normal",
            "height": "auto",
            "minHeight": "35px",
            "color": "#333333",
            "verticalAlign": "middle",
        },
        style_header={
            "backgroundColor": "#f2f2f2",
            "fontWeight": "bold",
            "fontSize": "14px",
            "fontFamily": "Arial, sans-serif",
            "border": "1px solid #d0d0d0",
            "color": "#1f3263",
            "textAlign": "left",
            "padding": "10px 12px",
            "position": "relative",
        },
        style_cell_conditional=[
            {
                "if": {"column_id": "Property"},
                "textAlign": "left",
                "fontWeight": "600",
                "minWidth": "180px",
                "backgroundColor": "#FFFFFF",
                "borderRight": "2px solid #ccc",
                "paddingLeft": "12px",
                "paddingRight": "12px",
                "color": "#1f3263",
            },
            {
                "if": {"column_id": "Unit"},
                "textAlign": "left",
                "minWidth": "120px",
                "backgroundColor": "#FFFFFF",
                "borderRight": "1px solid #ddd",
            },
            {
                "if": {"column_id": "Value"},
                "textAlign": "left",
                "minWidth": "80px",
                "backgroundColor": "#FFFFFF",
            },
        ],
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f9f9f9"},
            {"if": {"row_index": "even"}, "backgroundColor": "#FFFFFF"},
            # Property column - bold for non-empty
            {
                "if": {"column_id": "Property", "filter_query": '{Property} != ""'},
                "color": "#1f3263",
                "fontWeight": "600",
            },
            # Property column - hide empty cells (for merged Viscosity rows)
            {
                "if": {"column_id": "Property", "filter_query": '{Property} = ""'},
                "borderTop": "none",
                "borderBottom": "none",
                "backgroundColor": "inherit",
            },
        ],
        css=[
            {
                'selector': '.dash-cell[data-dash-column="Property"]:empty',
                'rule': '''
                    border-top: none !important;
                    border-bottom: none !important;
                    background-image: none !important;
                    height: 0 !important;
                    min-height: 0 !important;
                    padding-top: 0 !important;
                    padding-bottom: 0 !important;
                '''
            },
            # Ensure the cell above has proper bottom border
            {
                'selector': '.dash-cell[data-dash-column="Property"]:not(:empty) + .dash-cell[data-dash-column="Property"]:empty',
                'rule': 'border-top: none !important;'
            },
        ],
        fixed_rows={"headers": True},
        page_action="none",
        sort_action="native",
        filter_action="none",
        markdown_options={"html": True},
    )

def create_production_chart():
    """Create production and exports chart using dynamic data."""
    chart_data = load_production_exports()
    fig = go.Figure()
    
    # Ensure data lists are aligned
    years = chart_data.get('years', [])
    production = chart_data.get('production', [])
    exports = chart_data.get('exports', [])
    
    # Determine y-axis max safely
    combined_values = [val for val in (production + exports) if pd.notna(val)]
    y_max = max(combined_values) * 1.1 if combined_values else 100
    
    # Crude Production as dark blue bars
    fig.add_trace(go.Bar(
        name="Crude Production",
        x=years,
        y=production,
        marker_color='#1f3263',
        marker_line_color='#1f3263',
        marker_line_width=0
    ))
    
    # Crude Exports as orange circular data points (scatter)
    fig.add_trace(go.Scatter(
        name="Crude Exports",
        x=years,
        y=exports,
        mode='markers',
        marker=dict(
            color='#d65a00',
            size=8,
            symbol='circle',
            line=dict(width=0)
        )
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(l=50, r=20, t=20, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(title="Year", showgrid=False),
        yaxis=dict(title="Thousand Barrels per Day", range=[0, y_max], showgrid=True),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return fig

def create_map_chart():
    """Create loading ports map chart matching Tableau design - North America focus with orange triangular markers."""
    ports_data = load_loading_ports()
    fig = go.Figure()
    
    if not ports_data:
        # Return empty figure focused on North America
        fig.update_layout(
            height=500,
            margin=dict(l=0, r=0, t=0, b=0),
            geo=dict(
                projection_type="natural earth",
                center=dict(lat=40, lon=-95),
                scope="north america",
                showland=True,
                landcolor="rgb(243, 243, 243)",
                showocean=True,
                oceancolor="white",
                showcountries=True,
                countrycolor="rgb(200, 200, 200)",
                lataxis=dict(range=[15, 75]),
                lonaxis=dict(range=[-180, -50])
            )
        )
        return fig
    
    # Extract coordinates and data for hover
    lats = [port.get('latitude') for port in ports_data if port.get('latitude')]
    lons = [port.get('longitude') for port in ports_data if port.get('longitude')]
    port_names = [port.get('port', '') for port in ports_data]
    countries = [port.get('country', '') for port in ports_data]
    crudes = [port.get('crude', '') for port in ports_data]
    
    if lats and lons:
        # Add choropleth to highlight US and Alaska in light green
        fig.add_trace(go.Choropleth(
            locations=['USA'],
            z=[1],
            locationmode='ISO-3',
            colorscale=[[0, 'rgb(200, 230, 200)'], [1, 'rgb(200, 230, 200)']],
            showscale=False,
            geo='geo',
            hoverinfo='skip',
            marker_line_width=0,
            marker_line_color='rgba(0,0,0,0)',
            hovertemplate='<extra></extra>',
            text='',
            name=''
        ))
        
        # Add scattergeo trace for ports with orange triangular markers
        fig.add_trace(go.Scattergeo(
            lon=lons,
            lat=lats,
            text=port_names,
            customdata=list(zip(countries, crudes, port_names)),
            mode='markers',
            marker=dict(
                size=15,
                color='#d65a00',
                symbol='triangle-up',
                line=dict(width=1, color='white'),
                opacity=0.9
            ),
            name='Loading Ports',
            hovertemplate='<b>Country:</b> %{customdata[0]}<br>' +
                          '<b>Crude:</b> %{customdata[1]}<br>' +
                          '<b>Loading Port:</b> %{customdata[2]}<extra></extra>'
        ))
        
        # Focus on North America region
        lat_min, lat_max = min(lats), max(lats)
        lon_min, lon_max = min(lons), max(lons)
        
        # Expand bounds to show North America context
        lat_min = min(lat_min - 10, 15)
        lat_max = max(lat_max + 10, 75)
        lon_min = min(lon_min - 15, -180)
        lon_max = max(lon_max + 15, -50)
        
        fig.update_geos(
            projection_type="natural earth",
            center=dict(lat=40, lon=-95),
            scope="north america",
            showland=True,
            landcolor="rgb(243, 243, 243)",
            showocean=True,
            oceancolor="white",
            showcountries=True,
            countrycolor="rgb(200, 200, 200)",
            showlakes=True,
            lakecolor="white",
            lataxis=dict(range=[lat_min, lat_max]),
            lonaxis=dict(range=[lon_min, lon_max]),
            subunitcolor="rgb(200, 200, 200)",
            bgcolor="white"
        )
    else:
        # Default North America view if no valid coordinates
        fig.update_geos(
            projection_type="natural earth",
            center=dict(lat=40, lon=-95),
            scope="north america",
            showland=True,
            landcolor="rgb(243, 243, 243)",
            showocean=True,
            oceancolor="white",
            showcountries=True,
            countrycolor="rgb(200, 200, 200)",
            lataxis=dict(range=[15, 75]),
            lonaxis=dict(range=[-180, -50])
        )
    
    fig.update_layout(
        height=500,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        geo_bgcolor="white",
        paper_bgcolor="white",
        hovermode='closest'
    )
    
    return fig

# ------------------------------------------------------------------------------
# LAYOUT
# ------------------------------------------------------------------------------
def create_layout(server=None):
    """Layout with grouped tables for both Mars Blend Assay and Refined Products."""
    
    # Load dynamic data
    crude_options, default_crude = load_crude_options()
    assay_details = load_assay_details()
    quality_specs = load_quality_specs()
    port_details_data = load_port_details()
    port_details_rows = port_details_data.get("rows", [])
    port_details_label = port_details_data.get("label", "Port Details")
    
    # Convert port details to DataTable format
    port_details_table_data = [{"Measure": row[0], port_details_label: row[1]} for row in port_details_rows]
    producers_sellers = load_producers_sellers()
    
    production_fig = create_production_chart()
    map_fig = create_map_chart()
    
    return html.Div(style={
        "fontFamily": "Arial, sans-serif",
        "maxWidth": "1500px",
        "margin": "0 auto",
        "padding": "20px",
        "backgroundColor": "white",
        "color": "#333"
    }, children=[
        # CSS Styles for merged cells
        html.Div(style={"display": "none"}, children=[
            dcc.Markdown("""
                <style>
                /* Merged cells for Mars Blend Assay table - Property column */
                #assay-table .dash-cell[data-dash-column="Property"]:empty {
                    border-top: none !important;
                    border-bottom: none !important;
                    background-image: none !important;
                    height: 0 !important;
                    min-height: 0 !important;
                    padding-top: 0 !important;
                    padding-bottom: 0 !important;
                }
                
                /* Ensure the cell above has proper bottom border */
                #assay-table .dash-cell[data-dash-column="Property"]:not(:empty) + .dash-cell[data-dash-column="Property"]:empty {
                    border-top: none !important;
                }
                
                /* Merged cells for Refined Products table */
                #refined-products-table .dash-cell[data-dash-column="Product"]:empty,
                #refined-products-table .dash-cell[data-dash-column="Cut Points (°C)"]:empty {
                    border-top: none !important;
                    border-bottom: none !important;
                    background-image: none !important;
                    height: 0 !important;
                    min-height: 0 !important;
                    padding-top: 0 !important;
                    padding-bottom: 0 !important;
                }
                
                /* Ensure the cell above has proper bottom border */
                #refined-products-table .dash-cell[data-dash-column="Product"]:not(:empty) + .dash-cell[data-dash-column="Product"]:empty,
                #refined-products-table .dash-cell[data-dash-column="Cut Points (°C)"]:not(:empty) + .dash-cell[data-dash-column="Cut Points (°C)"]:empty {
                    border-top: none !important;
                }
                
                /* Stronger border for Property and Product columns */
                #assay-table .dash-cell[data-dash-column="Property"],
                #refined-products-table .dash-cell[data-dash-column="Product"] {
                    border-right: 2px solid #ccc !important;
                }
                
                /* Medium border for Cut Points column */
                #refined-products-table .dash-cell[data-dash-column="Cut Points (°C)"] {
                    border-right: 1px solid #ddd !important;
                }
                </style>
            """, dangerously_allow_html=True)
        ]),
        
        # AVG Text Box (initially hidden)
        html.Div(
            "AVG(Value)",
            id="crude-profile-avg-text-box",
            n_clicks=0,
            style={
                "position": "fixed",
                "backgroundColor": "white",
                "border": "1px solid #ccc",
                "padding": "8px 12px",
                "borderRadius": "4px",
                "fontSize": "12px",
                "fontFamily": "Arial",
                "boxShadow": "0 2px 5px rgba(0,0,0,0.1)",
                "zIndex": "1002",
                "display": "none",
                "whiteSpace": "nowrap",
                "color": "#333",
                "cursor": "pointer",
            }
        ),
        
        # Popup Menu (initially hidden)
        html.Div([
            html.Div([
                html.Div("Data Source Order", id="crude-profile-popup-source-btn", 
                        style={
                            "padding": "6px 10px", 
                            "fontSize": "12px",
                            "cursor": "pointer",
                            "fontFamily": "Arial",
                            "color": "#333",
                        }, className="popup-menu-item"),
                html.Div("Alphabetic", id="crude-profile-popup-alphabetic-btn",
                        style={
                            "padding": "6px 10px", 
                            "fontSize": "12px",
                            "cursor": "pointer",
                            "fontFamily": "Arial",
                            "color": "#333",
                        }, className="popup-menu-item"),
                html.Div([
                    html.Span("Field", style={"flex": "1"}),
                    html.Span("▶", id="crude-profile-field-arrow-btn", style={
                        "cursor": "pointer",
                        "fontSize": "10px",
                        "color": "#666",
                        "marginLeft": "8px",
                    }),
                ], id="crude-profile-popup-field-btn",
                   style={
                       "padding": "6px 10px", 
                       "fontSize": "12px",
                       "cursor": "pointer",
                       "fontFamily": "Arial",
                       "color": "#333",
                       "display": "flex",
                       "alignItems": "center",
                       "justifyContent": "space-between",
                       "position": "relative",
                   }, className="popup-menu-item"),
                html.Div([
                    html.Span("Nested", style={"flex": "1"}),
                    html.Span("▶", id="crude-profile-nested-arrow-btn", style={
                        "cursor": "pointer",
                        "fontSize": "10px",
                        "color": "#666",
                        "marginLeft": "8px",
                    }),
                ], id="crude-profile-popup-nested-btn",
                   style={
                       "padding": "6px 10px", 
                       "fontSize": "12px",
                       "cursor": "pointer",
                       "fontFamily": "Arial",
                       "color": "#333",
                       "display": "flex",
                       "alignItems": "center",
                       "justifyContent": "space-between",
                       "position": "relative",
                   }, className="popup-menu-item"),
            ]),
        ], id="crude-profile-sorting-controls", style={
            "position": "fixed", 
            "backgroundColor": "white", 
            "padding": "15px",
            "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
            "zIndex": "1000",
            "display": "none",
            "minWidth": "160px",
        }),
        
        # Hidden buttons for interactions
        html.Button("Sort Ascending Click", id="crude-profile-sort-asc-btn-hidden", n_clicks=0, style={"display": "none"}),
        html.Button("Sort Descending Click", id="crude-profile-sort-desc-btn-hidden", n_clicks=0, style={"display": "none"}),
        html.Button("Popup Menu Click", id="crude-profile-popup-menu-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Field Sort Click", id="crude-profile-field-sort-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Nested Sort Click", id="crude-profile-nested-sort-btn", n_clicks=0, style={"display": "none"}),
        
        # Dummy output for clientside callback
        html.Div(id="crude-profile-dummy-output", style={"display": "none"}),
        
        # Header Section
        html.Div(style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "marginBottom": "20px",
            "borderBottom": "2px solid #f0f0f0",
            "paddingBottom": "15px"
        }, children=[
            html.Div(style={"display": "block"}, children=[
                html.Div("Select Crude:", style={
                    "color": "#d65a00",
                    "fontWeight": "bold",
                    "fontSize": "14px",
                    "display": "block",
                    "marginBottom": "5px"
                }),
                dcc.Dropdown(
                    id="crude-select",
                    options=crude_options,
                    value=default_crude,
                    clearable=False,
                    style={
                        "width": "650px",
                        "fontSize": "13px",
                        "display": "block"
                    }
                )
            ]),
            html.A(
                "Click here to see the Crude's Profile",
                href="https://www.energyintel.com/wcod/crude-profile/Mars-Blend",
                target="_blank",
                style={
                    "color": "#d65a00",
                    "textDecoration": "underline",
                    "fontStyle": "italic",
                    "fontSize": "13px",
                    "fontWeight": "normal"
                }
            )
        ]),
        
        # Summary Section
        html.Div(style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "flex-start",
            "gap": "20px",
            "marginBottom": "25px",
            "marginTop": "20px"
        }, children=[
            # Left: Headers row and Values row
            html.Div(style={
                "flex": "1",
                "minWidth": "250px"
            }, children=[
                # Headers row
                html.Div(style={
                    "display": "flex",
                    "gap": "15px",
                    "marginBottom": "8px"
                }, children=[
                    html.Div("Alternate Crude Names", style={
                        "color": "#1f3263",
                        "fontWeight": "bold",
                        "fontSize": "13px",
                        "flex": "1"
                    }),
                    html.Div("Country", style={
                        "color": "#1f3263",
                        "fontWeight": "bold",
                        "fontSize": "13px",
                        "flex": "1"
                    }),
                    html.Div("Assay Date", style={
                        "color": "#1f3263",
                        "fontWeight": "bold",
                        "fontSize": "13px",
                        "flex": "1"
                    })
                ]),
                # Values row
                html.Div(style={
                    "display": "flex",
                    "gap": "15px"
                }, children=[
                    html.Div(assay_details["alternate_names"], style={
                        "color": "#666",
                        "fontSize": "13px",
                        "flex": "1"
                    }),
                    html.Div(assay_details["country"], style={
                        "color": "#666",
                        "fontSize": "13px",
                        "flex": "1"
                    }),
                    html.Div(assay_details["assay_date"], style={
                        "color": "#666",
                        "fontSize": "13px",
                        "flex": "1"
                    })
                ])
            ]),
            
            # Center: Carbon Intensity Box
            html.Div(style={
                "background": "linear-gradient(135deg, #fff9e6, #ffedcc)",
                "border": "1px solid #e6b800",
                "padding": "20px 30px",
                "borderRadius": "5px",
                "textAlign": "center",
                "minWidth": "150px",
                "flexShrink": "0"
            }, children=[
                html.Div("Carbon Intensity", style={
                    "color": "#1f3263",
                    "fontWeight": "bold",
                    "fontSize": "14px",
                    "marginBottom": "8px"
                }),
                html.Div("Low", style={
                    "color": "#1f3263",
                    "fontWeight": "bold",
                    "fontSize": "16px"
                })
            ]),
            
            # Right: Latest Quality Specs
            html.Div(style={
                "flex": "1",
                "minWidth": "350px"
            }, children=[
                html.Div("Latest Quality Specs", style={
                    "color": "#d65a00",
                    "fontWeight": "bold",
                    "fontSize": "15px",
                    "marginBottom": "12px",
                    "borderBottom": "2px solid #d65a00",
                    "paddingBottom": "5px"
                }),
                # Headers row
                html.Div(style={
                    "display": "flex",
                    "gap": "15px",
                    "marginBottom": "8px"
                }, children=[
                    html.Div(quality_specs[0][0] if len(quality_specs) > 0 else "Gravity (API at 60F)", style={
                        "color": "#1f3263",
                        "fontWeight": "bold",
                        "fontSize": "12px",
                        "flex": "1"
                    }),
                    html.Div(quality_specs[1][0] if len(quality_specs) > 1 else "Sulfur Content (% Wt)", style={
                        "color": "#1f3263",
                        "fontWeight": "bold",
                        "fontSize": "12px",
                        "flex": "1"
                    }),
                    html.Div(quality_specs[2][0] if len(quality_specs) > 2 else "TAN (mg KOH/g)", style={
                        "color": "#1f3263",
                        "fontWeight": "bold",
                        "fontSize": "12px",
                        "flex": "1"
                    })
                ]),
                # Values row
                html.Div(style={
                    "display": "flex",
                    "gap": "15px"
                }, children=[
                    html.Div(quality_specs[0][1] if len(quality_specs) > 0 else "28.40", style={
                        "color": "#666",
                        "fontSize": "13px",
                        "flex": "1"
                    }),
                    html.Div(quality_specs[1][1] if len(quality_specs) > 1 else "2.17", style={
                        "color": "#666",
                        "fontSize": "13px",
                        "flex": "1"
                    }),
                    html.Div(quality_specs[2][1] if len(quality_specs) > 2 else "0.48", style={
                        "color": "#666",
                        "fontSize": "13px",
                        "flex": "1"
                    })
                ])
            ])
        ]),
        
        # Main Grid Layout
        html.Div(style={
            "display": "grid",
            "gridTemplateColumns": "1fr 5fr 6fr",
            "gap": "20px",
            "marginBottom": "20px",
            "alignItems": "start"
        }, children=[
            # Column 1: Mars Blend Assay
            html.Div(style={"gridColumn": "1 / 2"}, children=[
                html.Div("Mars Blend Assay", style={
                    "color": "#d65a00",
                    "fontWeight": "bold",
                    "fontSize": "16px",
                    "margin": "20px 0 10px 0",
                    "borderBottom": "2px solid #d65a00",
                    "paddingBottom": "5px"
                }),
                create_grouped_assay_table(default_crude)
            ]),
            
            # Column 2: Refined Products Breakdown & Properties
            html.Div(style={"gridColumn": "2 / 3"}, children=[
                html.Div("Refined Products Breakdown & Properties", style={
                    "color": "#d65a00",
                    "fontWeight": "bold",
                    "fontSize": "16px",
                    "margin": "20px 0 10px 0",
                    "borderBottom": "2px solid #d65a00",
                    "paddingBottom": "5px"
                }),
                create_grouped_refined_products_table(default_crude)
            ]),
            
            # Column 3: Right-side stack
            html.Div(style={"gridColumn": "3 / 4", "display": "flex", "flexDirection": "column"}, children=[
                html.Div("Production and Exports", style={
                    "color": "#d65a00",
                    "fontWeight": "bold",
                    "fontSize": "16px", 
                    "margin": "20px 0 10px 0",
                    "borderBottom": "2px solid #d65a00",
                    "paddingBottom": "5px"
                }),
                html.Div(style={
                    "border": "1px solid #ddd",
                    "padding": "15px",
                    "borderRadius": "4px",
                    "margin": "10px 0",
                    "backgroundColor": "white"
                }, children=[
                    dcc.Graph(figure=production_fig, config={"displayModeBar": False})
                ]),
                html.Div("Loading Ports", style={
                    "color": "#d65a00",
                    "fontWeight": "bold",
                    "fontSize": "16px",
                    "margin": "25px 0 10px 0",
                    "borderBottom": "2px solid #d65a00",
                    "paddingBottom": "5px"
                }),
                html.Div(style={
                    "border": "1px solid #ddd",
                    "padding": "15px",
                    "borderRadius": "4px",
                    "margin": "10px 0",
                    "backgroundColor": "white"
                }, children=[
                    dcc.Graph(figure=map_fig, config={"displayModeBar": False}),
                    html.Div([
                        html.A("© 2025 Mapbox", href="https://www.mapbox.com/about/maps", target="_blank", style={
                            "color": "#666",
                            "textDecoration": "none"
                        }),
                        " ",
                        html.A("© OpenStreetMap", href="https://www.openstreetmap.org/about", target="_blank", style={
                            "color": "#666",
                            "textDecoration": "none"
                        })
                    ], style={
                        "fontSize": "10px",
                        "color": "#666",
                        "marginTop": "5px",
                        "textAlign": "left"
                    })
                ]),
                html.Div("Inland points represent terminals for pipeline-delivered crudes.", style={
                    "fontSize": "11px",
                    "color": "#0066cc",
                    "marginTop": "5px",
                    "textAlign": "left"
                }),
                html.Div("Port Details", style={
                    "color": "#d65a00",
                    "fontWeight": "bold",
                    "fontSize": "16px",
                    "margin": "25px 0 10px 0",
                    "borderBottom": "2px solid #d65a00",
                    "paddingBottom": "5px"
                }),
                dash_table.DataTable(
                    id="port-details-table",
                    data=port_details_table_data,
                    columns=[
                        {"name": "Measure", "id": "Measure"},
                        {"name": port_details_label, "id": port_details_label}
                    ],
                    style_table={
                        "width": "100%",
                        "marginBottom": "15px",
                        "fontFamily": "Arial, sans-serif"
                    },
                    style_cell={
                        "border": "1px solid #ddd",
                        "padding": "10px",
                        "fontSize": "12px",
                        "textAlign": "left",
                        "backgroundColor": "white"
                    },
                    style_header={
                        "backgroundColor": "#f5f5f5",
                        "fontWeight": "bold",
                        "border": "1px solid #ddd",
                        "padding": "10px"
                    },
                    style_data={
                        "border": "1px solid #ddd"
                    },
                    editable=False,
                    sort_action="native",
                    filter_action="none",
                    page_action="none",
                )
            ]),
            
            # Bottom Row: Sellers and Producers
            html.Div(style={"gridColumn": "1 / 3"}, children=[
                html.Div("Sellers and Producers", style={
                    "color": "#d65a00",
                    "fontWeight": "bold", 
                    "fontSize": "16px",
                    "margin": "20px 0 10px 0",
                    "borderBottom": "2px solid #d65a00",
                    "paddingBottom": "5px"
                }),
                html.Table(style={
                    "width": "100%",
                    "borderCollapse": "collapse",
                    "marginBottom": "15px",
                    "fontFamily": "Arial, sans-serif"
                }, children=[
                    html.Thead(html.Tr([
                        html.Th("Producers", style={
                            "border": "1px solid #ddd",
                            "padding": "10px",
                            "backgroundColor": "#f5f5f5",
                            "fontWeight": "bold",
                            "textAlign": "left",
                            "fontSize": "12px"
                        }),
                        html.Th("Sellers", style={
                            "border": "1px solid #ddd",
                            "padding": "10px",
                            "backgroundColor": "#f5f5f5",
                            "fontWeight": "bold",
                            "textAlign": "left",
                            "fontSize": "12px"
                        })
                    ])),
                    html.Tbody(html.Tr([
                        html.Td(producers_sellers[0][0] if producers_sellers else "", style={
                            "border": "1px solid #ddd",
                            "padding": "10px",
                            "fontSize": "12px"
                        }),
                        html.Td(producers_sellers[0][1] if producers_sellers else "", style={
                            "border": "1px solid #ddd",
                            "padding": "10px",
                            "fontSize": "12px"
                        })
                    ]))
                ]),
                html.Div(
                    "Countries: Select jurisdictions are included under countries for data presentation purposes.",
                    style={
                        "fontSize": "11px",
                        "color": "#666",
                        "marginTop": "10px",
                        "fontStyle": "italic"
                    }
                )
            ])
        ])
    ])

# ------------------------------------------------------------------------------
# CALLBACKS - REQUIRED FOR THE DASH APP
# ------------------------------------------------------------------------------
def register_callbacks(app):
    """Register callbacks for the dashboard with grouped tables."""
    
    @app.callback(
        Output('assay-table', 'data'),
        Output('refined-products-table', 'data'),
        Input('crude-select', 'value')
    )
    def update_crude_profile(selected_crude):
        """Update tables when crude selection changes."""
        if selected_crude:
            # Reload data from the database for the selected crude name
            assay_data = load_mars_assay(selected_crude)
            grouped_data = load_refined_products(selected_crude)

            # Convert grouped data to flat rows for DataTable
            table_data = []
            for product_group in grouped_data:
                product = product_group["Product"]
                cut_points = product_group["Cut Points (°C)"]
                properties = product_group["properties"]

                for i, prop in enumerate(properties):
                    table_data.append({
                        "Product": product if i == 0 else "",
                        "Cut Points (°C)": cut_points if i == 0 else "",
                        "Property": prop["Property"],
                        "Unit": prop["Unit"],
                        "Value": prop["Value"]
                    })

            return assay_data, table_data
        
        # Return empty data for other crudes (if added later)
        return [], []
    
    # Handle popup menu interactions
    @app.callback(
        [Output('crude-profile-sorting-controls', 'style'),
         Output('crude-profile-avg-text-box', 'style')],
        [Input('crude-profile-popup-menu-btn', 'n_clicks'),
         Input('crude-profile-popup-source-btn', 'n_clicks'),
         Input('crude-profile-popup-alphabetic-btn', 'n_clicks'),
         Input('crude-profile-popup-field-btn', 'n_clicks'),
         Input('crude-profile-popup-nested-btn', 'n_clicks'),
         Input('crude-profile-field-arrow-btn', 'n_clicks'),
         Input('crude-profile-nested-arrow-btn', 'n_clicks'),
         Input('crude-profile-field-sort-btn', 'n_clicks'),
         Input('crude-profile-nested-sort-btn', 'n_clicks'),
         Input('crude-profile-avg-text-box', 'n_clicks')],
        [State('crude-profile-sorting-controls', 'style')],
        prevent_initial_call=True
    )
    def handle_popup_interactions(popup_clicks, source_clicks, alpha_clicks, field_clicks, nested_clicks,
                                  field_arrow_clicks, nested_arrow_clicks, field_sort_clicks, nested_sort_clicks, avg_clicks,
                                  popup_style):
        """Handle popup menu visibility and AVG text box display."""
        trigger = ctx.triggered_id
        
        if trigger == 'crude-profile-popup-menu-btn':
            # Toggle popup menu - preserve position if set
            base_style = {
                "position": "fixed", 
                "backgroundColor": "white", 
                "padding": "15px",
                "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                "zIndex": "1000",
                "minWidth": "160px",
            }
            if popup_style and popup_style.get('display') == 'block':
                base_style["display"] = "none"
            else:
                base_style["display"] = "block"
                if popup_style and 'top' in popup_style:
                    base_style["top"] = popup_style["top"]
                if popup_style and 'left' in popup_style:
                    base_style["left"] = popup_style["left"]
            return base_style, {"display": "none"}
        elif trigger in ['crude-profile-popup-source-btn', 'crude-profile-popup-alphabetic-btn']:
            # Close popup menu
            return {
                "position": "fixed", 
                "backgroundColor": "white", 
                "padding": "15px",
                "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                "zIndex": "1000",
                "display": "none",
                "minWidth": "160px",
            }, {"display": "none"}
        elif trigger in ['crude-profile-popup-field-btn', 'crude-profile-field-arrow-btn', 'crude-profile-field-sort-btn']:
            # Show AVG text box
            return dash.no_update, {
                "position": "fixed",
                "backgroundColor": "white",
                "border": "1px solid #ccc",
                "padding": "8px 12px",
                "borderRadius": "4px",
                "fontSize": "12px",
                "fontFamily": "Arial",
                "boxShadow": "0 2px 5px rgba(0,0,0,0.1)",
                "zIndex": "1002",
                "display": "block",
                "color": "#333",
                "cursor": "pointer",
            }
        elif trigger in ['crude-profile-popup-nested-btn', 'crude-profile-nested-arrow-btn', 'crude-profile-nested-sort-btn']:
            # Show AVG text box
            return dash.no_update, {
                "position": "fixed",
                "backgroundColor": "white",
                "border": "1px solid #ccc",
                "padding": "8px 12px",
                "borderRadius": "4px",
                "fontSize": "12px",
                "fontFamily": "Arial",
                "boxShadow": "0 2px 5px rgba(0,0,0,0.1)",
                "zIndex": "1002",
                "display": "block",
                "color": "#333",
                "cursor": "pointer",
            }
        elif trigger == 'crude-profile-avg-text-box':
            # Close AVG text box and popup
            return {
                "position": "fixed", 
                "backgroundColor": "white", 
                "padding": "15px",
                "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                "zIndex": "1000",
                "display": "none",
                "minWidth": "160px",
            }, {"display": "none"}
        
        return {
            "position": "fixed", 
            "backgroundColor": "white", 
            "padding": "15px",
            "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
            "zIndex": "1000",
            "display": "none",
            "minWidth": "160px",
        }, {"display": "none"}
    
    # Clientside callback to inject A/Z and down arrow indicators - SIMILAR TO CRUDE_COMPARISON.PY
    app.clientside_callback(
        """
        function(assay_cols, refined_cols, port_cols) {
            function addSortIndicatorsToHeaders() {
                // Target headers for each table
                const targetHeaders = {
                    'assay-table': ['Property', 'Unit'],
                    'refined-products-table': ['Product', 'Cut Points (°C)', 'Property', 'Unit'],
                    'port-details-table': ['Measure']
                };
                
                Object.keys(targetHeaders).forEach(tableId => {
                    const headers = targetHeaders[tableId];
                    headers.forEach(columnId => {
                        const header = document.querySelector(`#${tableId} .dash-header[data-dash-column="${columnId}"]`);
                        if (header && !header.querySelector('.sort-order-container')) {
                            // Create A/Z container
                            const sortContainer = document.createElement('div');
                            sortContainer.className = 'sort-order-container';
                            
                            const aElement = document.createElement('div');
                            aElement.className = 'sort-asc';
                            aElement.textContent = 'A';
                            aElement.title = 'Click for ascending alphabetical order';
                            aElement.onclick = function(e) {
                                e.stopPropagation();
                                e.preventDefault();
                                // Close popup if open
                                const popup = document.getElementById('crude-profile-sorting-controls');
                                if (popup && popup.style.display === 'block') {
                                    const btn = document.getElementById('crude-profile-popup-menu-btn');
                                    if (btn) btn.click();
                                }
                                // Trigger sorting for ascending
                                const headerCell = header.closest('.dash-header-cell') || header;
                                if (headerCell) {
                                    // Click header to trigger native sorting
                                    headerCell.click();
                                    // If it sorted descending, click again for ascending
                                    setTimeout(() => {
                                        if (headerCell.classList.contains('dash-header-cell--sort-desc')) {
                                            headerCell.click();
                                        }
                                    }, 100);
                                }
                            };
                            
                            const zElement = document.createElement('div');
                            zElement.className = 'sort-desc';
                            zElement.textContent = 'Z';
                            zElement.title = 'Click for descending alphabetical order';
                            zElement.onclick = function(e) {
                                e.stopPropagation();
                                e.preventDefault();
                                // Close popup if open
                                const popup = document.getElementById('crude-profile-sorting-controls');
                                if (popup && popup.style.display === 'block') {
                                    const btn = document.getElementById('crude-profile-popup-menu-btn');
                                    if (btn) btn.click();
                                }
                                // Trigger sorting for descending
                                const headerCell = header.closest('.dash-header-cell') || header;
                                if (headerCell) {
                                    // Click header to trigger native sorting
                                    headerCell.click();
                                    // If it sorted ascending, click again for descending
                                    setTimeout(() => {
                                        if (headerCell.classList.contains('dash-header-cell--sort-asc')) {
                                            headerCell.click();
                                        }
                                    }, 100);
                                }
                            };
                            
                            sortContainer.appendChild(aElement);
                            sortContainer.appendChild(zElement);
                            
                            // Create down arrow indicator (same SVG as crude_comparison.py)
                            const sortIndicator = document.createElement('div');
                            sortIndicator.className = 'sort-indicator';
                            sortIndicator.title = 'Click to show sort options';
                            sortIndicator.innerHTML = `
                                <svg fill="#000000" viewBox="0 0 301.219 301.219" xmlns="http://www.w3.org/2000/svg">
                                    <g>
                                        <path d="M159.365,23.736v-10c0-5.523-4.477-10-10-10H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h139.365
                                            C154.888,33.736,159.365,29.259,159.365,23.736z"/>
                                        <path d="M130.586,66.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h120.586c5.523,0,10-4.477,10-10v-10
                                            C140.586,71.213,136.109,66.736,130.586,66.736z"/>
                                        <path d="M111.805,129.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h101.805c5.523,0,10-4.477,10-10v-10
                                            C121.805,134.213,117.328,129.736,111.805,129.736z"/>
                                        <path d="M93.025,199.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h83.025c5.522,0,10-4.477,10-10v-10
                                            C103.025,204.213,98.548,199.736,93.025,199.736z"/>
                                        <path d="M74.244,262.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h64.244c5.522,0,10-4.477,10-10v-10
                                            C84.244,267.213,79.767,262.736,74.244,262.736z"/>
                                        <path d="M298.29,216.877l-7.071-7.071c-1.875-1.875-4.419-2.929-7.071-2.929c-2.652,0-5.196,1.054-7.072,2.929l-34.393,34.393
                                            V18.736c0-5.523-4.477-10-10-10h-10c-5.523,0-10,4.477-10,10v225.462l-34.393-34.393c-1.876-1.875-4.419-2.929-7.071-2.929
                                            c-2.652,0-5.196,1.054-7.071,2.929l-7.072,7.071c-3.904,3.905-3.904,10.237,0,14.142l63.536,63.536
                                            c1.953,1.953,4.512,2.929,7.071,2.929c2.559,0,5.119-0.976,7.071-2.929l63.536-63.536
                                            C302.195,227.113,302.195,220.781,298.29,216.877z"/>
                                    </g>
                                </svg>
                            `;
                            
                            sortIndicator.onclick = function(e) {
                                e.stopPropagation();
                                e.preventDefault();
                                const btn = document.getElementById('crude-profile-popup-menu-btn');
                                if (btn) {
                                    // Position popup menu near the clicked indicator
                                    const rect = sortIndicator.getBoundingClientRect();
                                    const popup = document.getElementById('crude-profile-sorting-controls');
                                    if (popup) {
                                        popup.style.position = 'fixed';
                                        popup.style.top = (rect.bottom + 5) + 'px';
                                        popup.style.left = (rect.left - 150) + 'px';
                                        popup.style.zIndex = '1000';
                                    }
                                    // Use setTimeout to ensure positioning is set before showing
                                    setTimeout(function() {
                                        btn.click();
                                    }, 10);
                                }
                            };
                            
                            header.appendChild(sortContainer);
                            header.appendChild(sortIndicator);
                            
                            // Add hover effect for the header
                            header.style.position = 'relative';
                            header.style.paddingRight = '60px';
                            
                            // Show indicators on header hover
                            header.addEventListener('mouseenter', function() {
                                sortContainer.style.opacity = '1';
                                sortContainer.style.visibility = 'visible';
                                sortIndicator.style.opacity = '1';
                                sortIndicator.style.visibility = 'visible';
                            });
                            
                            header.addEventListener('mouseleave', function() {
                                sortContainer.style.opacity = '0';
                                sortContainer.style.visibility = 'hidden';
                                sortIndicator.style.opacity = '0';
                                sortIndicator.style.visibility = 'hidden';
                            });
                        }
                    });
                });
            }
            
            // Setup Field and Nested arrow handlers
            function setupFieldNestedHandlers() {
                const fieldArrow = document.getElementById('crude-profile-field-arrow-btn');
                const nestedArrow = document.getElementById('crude-profile-nested-arrow-btn');
                
                if (fieldArrow && !fieldArrow.getAttribute('data-handler-attached')) {
                    fieldArrow.setAttribute('data-handler-attached', 'true');
                    fieldArrow.onclick = function(e) {
                        e.stopPropagation();
                        const btn = document.getElementById('crude-profile-field-sort-btn');
                        if (btn) {
                            const rect = fieldArrow.getBoundingClientRect();
                            const avgBox = document.getElementById('crude-profile-avg-text-box');
                            if (avgBox) {
                                avgBox.style.top = (rect.top) + 'px';
                                avgBox.style.left = (rect.right + 10) + 'px';
                            }
                            btn.click();
                        }
                    };
                }
                
                if (nestedArrow && !nestedArrow.getAttribute('data-handler-attached')) {
                    nestedArrow.setAttribute('data-handler-attached', 'true');
                    nestedArrow.onclick = function(e) {
                        e.stopPropagation();
                        const btn = document.getElementById('crude-profile-nested-sort-btn');
                        if (btn) {
                            const rect = nestedArrow.getBoundingClientRect();
                            const avgBox = document.getElementById('crude-profile-avg-text-box');
                            if (avgBox) {
                                avgBox.style.top = (rect.top) + 'px';
                                avgBox.style.left = (rect.right + 10) + 'px';
                            }
                            btn.click();
                        }
                    };
                }
            }
            
            // Initial setup - only if not already done
            if (!window._crudeProfileIndicatorsAdded) {
                addSortIndicatorsToHeaders();
                setupFieldNestedHandlers();
                window._crudeProfileIndicatorsAdded = true;
            } else {
                // Re-run if tables were updated
                addSortIndicatorsToHeaders();
                setupFieldNestedHandlers();
            }
            
            // Setup click outside to close popup - only once
            if (!window._crudeProfileClickHandlerAdded) {
                document.addEventListener('click', function(e) {
                    const popup = document.getElementById('crude-profile-sorting-controls');
                    const sortIndicator = e.target.closest('.sort-indicator');
                    const popupItem = e.target.closest('.popup-menu-item');
                    
                    if (popup && popup.style.display === 'block') {
                        if (!popup.contains(e.target) && !sortIndicator && !popupItem) {
                            // Click outside, close popup
                            const btn = document.getElementById('crude-profile-popup-menu-btn');
                            if (btn) {
                                btn.click();
                            }
                        }
                    }
                });
                window._crudeProfileClickHandlerAdded = true;
            }
            
            // Add CSS styles for the sort indicators - only once
            if (!document.getElementById('crude-profile-sort-styles')) {
                const style = document.createElement('style');
                style.id = 'crude-profile-sort-styles';
                style.textContent = `
                /* A/Z container - vertical stack - HIDDEN BY DEFAULT, SHOW ON HOVER */
                .sort-order-container {
                    position: absolute;
                    right: 30px;
                    top: 50%;
                    transform: translateY(-50%);
                    font-size: 10px;
                    color: #666;
                    cursor: pointer;
                    padding: 2px;
                    border: 1px solid transparent;
                    border-radius: 2px;
                    line-height: 1;
                    text-align: center;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 30px;
                    opacity: 0;
                    visibility: hidden;
                    transition: opacity 0.2s ease, visibility 0.2s ease;
                    z-index: 1001;
                }
                .dash-header:hover .sort-order-container {
                    opacity: 1;
                    visibility: visible;
                }
                .dash-header .sort-order-container:hover {
                    background-color: #e6f3ff;
                    border-color: #1f3263;
                }
                .sort-asc, .sort-desc {
                    display: block;
                    line-height: 1;
                    cursor: pointer;
                    padding: 1px 2px;
                    border-radius: 1px;
                }
                .sort-asc:hover, .sort-desc:hover {
                    background-color: #d4e7ff;
                    font-weight: bold;
                }
                
                /* Sort indicator icon styles - HIDDEN BY DEFAULT, SHOW ON HOVER */
                .sort-indicator {
                    position: absolute;
                    right: 8px;
                    top: 50%;
                    transform: translateY(-50%);
                    width: 15px;
                    height: 15px;
                    cursor: pointer;
                    opacity: 0;
                    visibility: hidden;
                    transition: opacity 0.2s ease, visibility 0.2s ease;
                    z-index: 1001;
                }
                .dash-header:hover .sort-indicator {
                    opacity: 1;
                    visibility: visible;
                }
                .sort-indicator:hover {
                    background-color: #e6f3ff;
                    border-radius: 2px;
                }
                .sort-indicator svg {
                    width: 100%;
                    height: 100%;
                    fill: #666;
                }
                .sort-indicator:hover svg {
                    fill: #1f3263;
                }
                
                /* Add padding to headers to make space for indicators */
                #assay-table .dash-header[data-dash-column="Property"],
                #assay-table .dash-header[data-dash-column="Unit"],
                #refined-products-table .dash-header[data-dash-column="Product"],
                #refined-products-table .dash-header[data-dash-column="Cut Points (°C)"],
                #refined-products-table .dash-header[data-dash-column="Property"],
                #refined-products-table .dash-header[data-dash-column="Unit"],
                #port-details-table .dash-header[data-dash-column="Measure"] {
                    padding-right: 60px !important;
                    position: relative;
                }
                
                /* Popup menu item hover */
                .popup-menu-item:hover {
                    background-color: #f5f5f5 !important;
                }
                
                /* Hide default Dash sort indicators */
                #assay-table .dash-header-cell--sort svg,
                #assay-table .dash-header-cell--sort-asc svg,
                #assay-table .dash-header-cell--sort-desc svg,
                #refined-products-table .dash-header-cell--sort svg,
                #refined-products-table .dash-header-cell--sort-asc svg,
                #refined-products-table .dash-header-cell--sort-desc svg,
                #port-details-table .dash-header-cell--sort svg,
                #port-details-table .dash-header-cell--sort-asc svg,
                #port-details-table .dash-header-cell--sort-desc svg {
                    display: none !important;
                }
                
                /* AVG text box styling */
                #crude-profile-avg-text-box {
                    cursor: pointer !important;
                }
                #crude-profile-avg-text-box:hover {
                    background-color: #f5f5f5 !important;
                    border-color: #999 !important;
                }
            `;
                document.head.appendChild(style);
            }
            
            return '';
        }
        """,
        Output('crude-profile-dummy-output', 'children'),
        [Input('assay-table', 'columns'),
         Input('refined-products-table', 'columns'),
         Input('port-details-table', 'columns')],
        prevent_initial_call=False
    )

# ------------------------------------------------------------------------------
# DASH APP CREATION - MAIN FUNCTION
# ------------------------------------------------------------------------------
def create_crude_profile_dashboard(dash_app, server, url_base_pathname="/dash/crude-profile/"):
    """Create and configure the crude profile dashboard with grouped tables."""
    # dash_app = dash.Dash(
    #     __name__,
    #     server=server,
    #     url_base_pathname=url_base_pathname,
    #     external_stylesheets=[
    #         'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
    #         'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
    #     ],
    #     suppress_callback_exceptions=True
    # )
    
    dash_app.layout = create_layout()
    register_callbacks(dash_app, server)