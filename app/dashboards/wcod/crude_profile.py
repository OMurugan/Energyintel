# crude_profile.py
"""
Crude Profile Dashboard - Complete Implementation with Grouped Tables for Refined Products
"""
from dash import dcc, html, Dash, Input, Output, State, callback_context, ctx, dash_table, no_update
import dash
import plotly.graph_objects as go
import pandas as pd
import re
import numpy as np
from datetime import datetime, date, timedelta
from core.data_helpers import execute_query
import dash.exceptions
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

def load_assay_details(crude_value: str | None = None):
    """Load assay details data from DB for the selected crude (first row)."""
    df = _load_crude_assay_df(crude_value)
    if df is None or df.empty:
        return {
            "alternate_names": "",
            "country": "United States",
            "assay_date": "2025",
            "profile_url": "https://www.energyintel.com/wcod/crude-profile/Mars-Blend",
        }

    # Take first row
    row = df.iloc[0]
    return {
        "alternate_names": row.get("crude_alias", ""),
        "country": row.get("country_name", "United States"),
        "assay_date": row.get("assay_yr", "2025"),
        "profile_url": row.get("profile_url", "https://www.energyintel.com/wcod/crude-profile/Mars-Blend"),
    }

def load_quality_specs(crude_value: str | None = None):
    """
    Load latest quality specs from the same assays query.
    Pulls Gravity, Sulfur Content, and TAN for the selected crude.
    """
    df = _load_crude_assay_df(crude_value)
    if df is None or df.empty:
        return [("Gravity (API at 60F)", "11.40"), ("Sulfur Content (% Wt)", "2.17"), ("TAN (mg KOH/g)", "0.48")]

    df_local = df.copy()
    # Normalize property names
    df_local["Property_norm"] = df_local["property"].fillna("").astype(str).str.strip().str.lower()

    def match_prop(pnorm: str):
        if any(k in pnorm for k in ["gravity", "api"]):
            return "Gravity (API at 60F)"
        if any(k in pnorm for k in ["sulfur", "sulphur"]):
            return "Sulfur Content (% Wt)"
        if any(k in pnorm for k in ["tan", "acid"]):
            return "TAN (mg KOH/g)"
        return None

    value_map = {
        "Gravity (API at 60F)": None,
        "Sulfur Content (% Wt)": None,
        "TAN (mg KOH/g)": None,
    }

    for _, row in df_local.iterrows():
        key = match_prop(row["Property_norm"])
        if key:
            val = row.get("Value", "")
            try:
                valf = float(val)
                val = f"{valf:.2f}"
            except Exception:
                val = str(val)
            if val:
                value_map[key] = val

    specs = []
    for k, fallback in [
        ("Gravity (API at 60F)", "28.40"),
        ("Sulfur Content (% Wt)", "2.17"),
        ("TAN (mg KOH/g)", "0.48"),
    ]:
        specs.append((k, value_map[k] if value_map[k] is not None else fallback))
    return specs


def load_carbon_intensity(crude_value: str | None = None):
    """Load carbon intensity rank (ci_rank) for the selected crude."""
    df = _load_crude_assay_df(crude_value)
    if df is None or df.empty:
        return "Low"
    ci_series = df.get("ci_rank")
    if ci_series is None:
        return "Low"
    ci_series = ci_series.dropna().astype(str).str.strip()
    ci_series = ci_series[ci_series != ""]
    if ci_series.empty:
        return "Low"
    return ci_series.iloc[0]

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
          AND a.crude_name = :crude_name
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
            c.crude_alias,
            c.ci_rank
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
    df_ref["Unit"] = df_ref.get("Unit", "").fillna("").astype(str).str.strip().apply(lambda x: x + " (%)" if x in ["Yield Volume", "Yield Weight"] else x)
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

def load_production_exports(crude_value: str | None = None):
    """Load production and exports data for chart from DB."""
    fallback = {
        'years': ['2006', '2007', '2008', '2009', '2010', '2011', '2012', '2013', '2014',
                  '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024'],
        'production': [235, 290, 220, 225, 200, 190, 150, 145, 170, 100, 200, 205, 225, 280, 270, 250, 235, 220, 215],
        'exports': [5, 5, 5, 5, 5, 5, 5, 5, 75, 65, 50, 75, 115, 170, 110, 150, 160, 160, 115]
    }
    crude_name = _get_crude_name_from_value(crude_value)
    query = """
        SELECT
            a.country_name AS "Country",
            a.crude_name AS "CrudeOil",
            EXTRACT(YEAR FROM a.yr) AS "YearReported",
            a.production_kbpd AS "CrudeProduction",
            a.exports_kbpd AS "CrudeExport",
            a.ci_rank,
            a.sellers,
	        a.producers
        FROM fact_wcod_crude a
        LEFT JOIN dim_country grp 
               ON a.country_id = grp.dim_country_id
        WHERE a.ci_rank IS NOT NULL 
          AND a.crude_name = :crude_name
        ORDER BY "YearReported"
    """
    try:
        results = execute_query(query, {"crude_name": crude_name})
    except Exception as e:
        print(f"❌ Error loading production/exports from DB: {e}")
        return fallback

    if not results:
        return fallback

    df = pd.DataFrame(results)
    chart_data = {'years': [], 'production': [], 'exports': []}
    for _, row in df.iterrows():
        year = row.get("YearReported")
        prod = row.get("CrudeProduction")
        exp = row.get("CrudeExport")
        
        # Convert to float for numeric comparison, coerce errors to NaN
        prod_numeric = float(prod) if pd.notna(prod) else None
        exp_numeric = float(exp) if pd.notna(exp) else None

        # Only append if year is valid and at least one of production or export data
        # is present and its absolute value is >= 1.0 (to exclude negligible values)
        if pd.notna(year) and (\
           (prod_numeric is not None and abs(prod_numeric) >= 1.0) or \
           (exp_numeric is not None and abs(exp_numeric) >= 1.0)
        ):
            chart_data['years'].append(str(int(year)))
            chart_data['production'].append(prod_numeric)
            chart_data['exports'].append(exp_numeric)

    if not chart_data['years']:
        # If no valid years after filtering, return empty chart data
        return {'years': [], 'production': [], 'exports': []}

    return chart_data

def load_port_details(crude_value: str | None = None):
    """Load port details data from DB for the selected crude, supporting multiple ports."""
    fallback_rows = [
        ("Berths", "4"),
        ("Max Draft (meters)", "23.5"),
        ("Max Length (meters)", "366"),
        ("Max Loading Rate (bbl/hour)", "80,000"),
        ("Max Tonnage (dwt)", "250,000"),
        ("Mooring Type", "Single Point"),
        ("Storage Capacity (million bbl)", "12.5")
    ]
    fallback_label = "Port Details"
    crude_name = _get_crude_name_from_value(crude_value)
    query = """
        SELECT 
            a.port_name AS "PortName",
            a.measure_name,
            a.value
        FROM fact_wcod_port a
        LEFT JOIN dim_crude b 
               ON a.crude_id = b.dim_crude_id
        WHERE b.crude_name = :crude_name
    """
    try:
        results = execute_query(query, {"crude_name": crude_name})
    except Exception as e:
        print(f"❌ Error loading port details from DB: {e}")
        return {"label": fallback_label, "rows": fallback_rows, "ports": [fallback_label]}

    if not results:
        return {"label": fallback_label, "rows": fallback_rows, "ports": [fallback_label]}

    df = pd.DataFrame(results)
    df["measure_name"] = df.get("measure_name", "").fillna("").astype(str).str.strip()
    # Format measure_name from snake_case to Title Case
    df["measure_name"] = df["measure_name"].apply(lambda x: ' '.join([word.capitalize() for word in x.split('_')]))

    # Append units to specific measure names
    unit_mapping = {
        "Max Draft": " (meters)",
        "Max Length": " (meters)",
        "Max Loading Rate": " (bbl/hour)",
        "Max Tonnage": " (dwt)",
        "Storage Capacity": " (million bbl)",
    }
    df["measure_name"] = df.apply(lambda row: row["measure_name"] + unit_mapping.get(row["measure_name"], ""), axis=1)

    df["value"] = df.get("value", "").fillna("").astype(str).str.strip()
    df["PortName"] = df.get("PortName", "").fillna("").astype(str).str.strip()

    # Get unique ports
    unique_ports = df["PortName"][df["PortName"] != ""].unique().tolist()
    
    if not unique_ports:
        return {"label": fallback_label, "rows": fallback_rows, "ports": [fallback_label]}

    # If only one port, use the original format for backward compatibility
    if len(unique_ports) == 1:
        port_label = unique_ports[0]
        rows = []
        port_df = df[df["PortName"] == port_label]
        for _, row in port_df.iterrows():
            measure = row.get("measure_name", "")
            val = row.get("value", "")
            if measure:
                rows.append((measure, val))
        
        if not rows:
            rows = fallback_rows
            port_label = fallback_label
        
        return {"label": port_label, "rows": rows, "ports": [port_label]}
    
    # Multiple ports - create structured data for multi-column table
    # Get all unique measures
    all_measures = df["measure_name"][df["measure_name"] != ""].unique().tolist()
    
    # Create a structured format for multiple ports
    port_data = {}
    for port in unique_ports:
        port_df = df[df["PortName"] == port]
        port_data[port] = {}
        for _, row in port_df.iterrows():
            measure = row.get("measure_name", "")
            val = row.get("value", "")
            if measure:
                port_data[port][measure] = val
    
    # Create rows with data for all ports
    structured_rows = []
    for measure in all_measures:
        row_data = {"Measure": measure}
        for port in unique_ports:
            row_data[port] = port_data[port].get(measure, "")
        structured_rows.append(row_data)
    
    # If no structured data, fall back to single port format
    if not structured_rows:
        return {"label": fallback_label, "rows": fallback_rows, "ports": [fallback_label]}
    
    return {
        "label": "Port Details", 
        "rows": structured_rows, 
        "ports": unique_ports,
        "is_multi_port": True
    }

def load_loading_ports(crude_value: str | None = None):
    """Load loading ports data for the map from DB."""
    fallback = [{
        "port": "test, Clovelly",
        "country": "United States",
        "crude": "Mars Blend",
        "latitude": 29.1175,
        "longitude": -90.0715
    }]
    crude_name = _get_crude_name_from_value(crude_value)
    query = """
        SELECT 
            a.port_name AS "PortName",
            c.country_long_name AS "Country",
            b.crude_name AS "Crude",
            a.latitude,
            a.longitude
        FROM fact_wcod_port a
        LEFT JOIN dim_crude b 
               ON a.crude_id = b.dim_crude_id
        LEFT JOIN dim_country c 
               ON a.country_id = c.dim_country_id
        WHERE b.crude_name LIKE '%' || :crude_name || '%'
    """
    try:
        results = execute_query(query, {"crude_name": crude_name})
    except Exception as e:
        print(f"❌ Error loading loading ports from DB: {e}")
        return fallback

    if not results:
        return fallback

    df = pd.DataFrame(results)
    records = []
    for _, row in df.iterrows():
        lat = pd.to_numeric(row.get("latitude"), errors="coerce")
        lon = pd.to_numeric(row.get("longitude"), errors="coerce")
        name = str(row.get("PortName", "")).strip()
        if pd.notna(lat) and pd.notna(lon) and name:
            records.append({
                "port": name,
                "country": str(row.get("Country", "")).strip(),
                "crude": str(row.get("Crude", "")).strip(),
                "latitude": lat,
                "longitude": lon
            })
    return records or fallback

def load_producers_sellers(crude_value: str | None = None):
    """Load producers and sellers data for the selected crude."""
    fallback = [("BP, ConocoPhillips, Exxon Mobil, Shell", "BP America Inc., ConocoPhillips, Exxon Mobil, Shell")]
    crude_name = _get_crude_name_from_value(crude_value)
    query = """
        SELECT
            a.sellers,
            a.producers,
            a.crude_name
        FROM fact_wcod_crude a
        WHERE a.ci_rank IS NOT NULL 
          AND a.crude_name = :crude_name
        ORDER BY a.yr
    """
    try:
        results = execute_query(query, {"crude_name": crude_name})
    except Exception as e:
        print(f"❌ Error loading producers/sellers from DB: {e}")
        return fallback

    if not results:
        return fallback

    df = pd.DataFrame(results)
    df["sellers"] = df.get("sellers", "").fillna("").astype(str).str.strip()
    df["producers"] = df.get("producers", "").fillna("").astype(str).str.strip()

    # Take first non-empty row
    for _, row in df.iterrows():
        prod = row.get("producers", "")
        sell = row.get("sellers", "")
        crude = row.get("crude_name", "")
        if prod or sell or crude:
            return [(prod, sell, crude)]

    return fallback

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
            {"name": "Cut Points (°C)", "id": "Cut Points (°C)"},
            {"name": "Property", "id": "Property"},
            {"name": "Unit", "id": "Unit"},
            {"name": "Value", "id": "Value"},
        ],
        data=table_data,
        style_table={
            "width": "100%",
            "marginBottom": "15px",
            "fontFamily": "Arial, sans-serif",
            "position": "relative",
            "maxHeight": "1360px",  # Reduced height
            "overflowY": "auto",  # Add vertical scroll
            "overflowX": "auto",  # Keep horizontal scroll if needed
            "border": "1px solid #ddd",  # Add border for better visibility
            
        },
        style_cell={
            "border": "1px solid #ddd",
            "padding": "2px 8px",
            "fontSize": "11px",
            "textAlign": "left",
            "backgroundColor": "white",
            "fontFamily": "Arial, sans-serif",
            "whiteSpace": "normal",
            "height": "auto",
            "minHeight": "20px",
            "verticalAlign": "middle",            
        },
        style_header={
            "backgroundColor": "#f5f5f5",
            "fontWeight": "bold",
            "fontSize": "12px",
            "border": "1px solid #ddd",
            "padding": "4px 8px",
            "textAlign": "left",
            "position": "static", # Make header sticky
            "top": "0",
            "zIndex": "10",
        },
        style_header_conditional=[
            {
                "if": {"column_id": "Value"},
                "textAlign": "right",
                "paddingRight": "0px",
            }
        ],
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
                "fontWeight": "normal",
                "color": "#1f3263",
                "borderRight": "2px solid #ccc",
                "maxWidth": "84px",
            },
            {
                "if": {"column_id": "Product", "filter_query": '{Product} = ""'},
                "borderTop": "none",
                "borderBottom": "none",
                "backgroundColor": "inherit",
                "maxWidth": "80px",
            },
            
            # Cut Points column styling
            {
                "if": {"column_id": "Cut Points (°C)", "filter_query": '{Cut Points (°C)} != ""'},
                "fontWeight": "normal",
                "color": "#1f3263",
                "borderRight": "1px solid #ddd",
                "maxWidth": "60px",
            },
            {
                "if": {"column_id": "Cut Points (°C)", "filter_query": '{Cut Points (°C)} = ""'},
                "borderTop": "none",
                "borderBottom": "none",
                "backgroundColor": "inherit",
                "maxWidth": "92px",
            },
            
            # Property column styling
            {
                "if": {"column_id": "Property", "filter_query": '{Property} != ""'},
                "fontWeight": "normal",
                "color": "#1f3263",
                "maxWidth": "56px",
            },
            # Value column right alignment
            {
                "if": {"column_id": "Value"},
                "textAlign": "right",
                "paddingRight": "0px",
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
            {"name": "Property", "id": "Property", "presentation": "markdown", "minWidth": "80px", "maxWidth": "120px"},
            {"name": "Unit", "id": "Unit", "minWidth": "50px", "maxWidth": "80px"}, 
            {"name": "Value", "id": "Value", "minWidth": "50px", "maxWidth": "70px"}
        ],
        style_table={
            "overflowX": "auto",
            "overflowY": "auto",
            "maxHeight": "750px",
            "border": "1px solid #d9d9d9",
            "backgroundColor": "white",
            "position": "relative",
        },
        style_cell={
            "textAlign": "left",
            "padding": "2px 8px",
            "fontSize": "11px",
            "fontFamily": "Arial, sans-serif",
            "border": "1px solid #e0e0e0",
            "whiteSpace": "normal",
            "height": "auto",
            "minHeight": "20px",
            "color": "#333333",
            "verticalAlign": "middle",
        },
        style_header={
            "backgroundColor": "#f2f2f2",
            "fontWeight": "bold",
            "fontSize": "12px",
            "fontFamily": "Arial, sans-serif",
            "border": "1px solid #d0d0d0",
            "color": "#1b365d",
            "textAlign": "left",
            "padding": "4px 8px",
            "position": "relative",
        },
        style_header_conditional=[
            {
                "if": {"column_id": "Value"},
                "textAlign": "right",
                "paddingRight": "0px",
            }
        ],
        style_cell_conditional=[
            {
                "if": {"column_id": "Property"},
                "textAlign": "left",
                "fontWeight": "normal",
                "minWidth": "80px",
                "maxWidth": "120px",
                "backgroundColor": "#FFFFFF",
                "borderRight": "2px solid #ccc",
                "padding": "2px 8px",
                "color": "#1b365d",
            },
            {
                "if": {"column_id": "Unit"},
                "textAlign": "left",
                "minWidth": "50px",
                "maxWidth": "80px",
                "backgroundColor": "#FFFFFF",
                "borderRight": "1px solid #ddd",
                "padding": "2px 8px",
            },
            {
                "if": {"column_id": "Value"},
                "textAlign": "right",
                "minWidth": "50px",
                "maxWidth": "70px",
                "backgroundColor": "#FFFFFF",
                "padding": "2px 0px",
            },
        ],
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f9f9f9"},
            {"if": {"row_index": "even"}, "backgroundColor": "#FFFFFF"},
            # Property column - bold for non-empty
            {
                "if": {"column_id": "Property", "filter_query": '{Property} != ""'},
                "color": "#1f3263",
                "fontWeight": "normal",
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
            # Set width to auto for flexible columns
            {
                'selector': '#assay-table .dash-cell',
                'rule': 'width: auto !important;'
            },
            # Force right alignment for markdown content in Value column (Removed)
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

def create_production_chart(crude_value: str | None = None):
    """Create production and exports chart using dynamic data."""
    chart_data = load_production_exports(crude_value)
    fig = go.Figure()
    
    # Ensure data lists are aligned
    years = chart_data.get('years', [])
    # Cast to floats to avoid Decimal issues
    production = [float(x) if x is not None else None for x in chart_data.get('production', [])]
    exports = [float(x) if x is not None else None for x in chart_data.get('exports', [])]
    
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
        marker_line_width=0,
        width=0.5,
        hovertemplate='Year: <span style="color:#1b365d;"><b>%{x}</b></span><br>Production: <span style="color:#1b365d;"><b>%{y:.2f} (000 b/d)</b></span><extra></extra>'
    ))
    
    # Crude Exports as orange circular data points (scatter)
    fig.add_trace(go.Scatter(
        name="Crude Exports",
        x=years,
        y=exports,
        mode='markers',
        marker=dict(
            color='#fe5000',
            size=8,
            symbol='circle',
            line=dict(width=0)
        ),
        hovertemplate='Year: <span style="color:#1b365d;"><b>%{x}</b></span><br>Exports: <span style="color:#1b365d;"><b>%{y:.2f} (000 b/d)</b></span><extra></extra>'
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(l=40, r=0, t=20, b=50),
        bargap=0.1,
        hoverlabel=dict(bgcolor='#ffffff'), # Set hover background color
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(title="Year", showgrid=False, tickangle=-90, dtick=1, tickvals=years),
        yaxis=dict(title="Volume ('000 b/d)", range=[0, y_max], showgrid=True),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return fig

def create_map_chart(crude_value: str | None = None):
    """Create loading ports map chart with country-level interactions and proper port markers."""
    ports_data = load_loading_ports(crude_value)
    
    if not ports_data:
        return create_empty_map("No loading ports data available", height=500)
    
    # Extract coordinates and data for hover
    lats = [port.get('latitude') for port in ports_data if port.get('latitude')]
    lons = [port.get('longitude') for port in ports_data if port.get('longitude')]
    port_names = [port.get('port', '') for port in ports_data]
    countries = [port.get('country', '') for port in ports_data]
    crudes = [port.get('crude', '') for port in ports_data]
    unique_countries = [c for c in dict.fromkeys(countries) if c]
    
    if not (lats and lons):
        return create_empty_map("No valid port coordinates available", height=500)
    
    # Use shared map configuration
    use_mapbox, token, mapbox_layout = get_mapbox_config()
    geojson = load_world_geojson()
    
    fig = go.Figure()
    
    # Add country choropleth layer for country-level interactions
    if unique_countries:
        # Create country data for choropleth
        country_values = [1] * len(unique_countries)  # All countries have same value for uniform coloring
        country_hover_text = [f"<b>{country}</b><br>Click to zoom to country" for country in unique_countries]
        
        if use_mapbox and geojson:
            # Get ISO codes for countries
            from core.country_mappings import get_iso_code
            country_isos = []
            valid_countries = []
            for country in unique_countries:
                iso = get_iso_code(country)
                if iso:
                    country_isos.append(iso)
                    valid_countries.append(country)
            
            if country_isos:
                fig.add_trace(
                    go.Choroplethmapbox(
                        geojson=geojson,
                        locations=country_isos,
                        z=country_values[:len(country_isos)],
                        featureidkey="id",
                        colorscale=[[0, 'rgba(200, 230, 200, 0.6)'], [1, 'rgba(200, 230, 200, 0.6)']],
                        showscale=False,
                        hoverinfo="text",
                        hovertext=[f"<b>{country}</b><br>Click to zoom to country" for country in valid_countries],
                        marker_line_color="white",
                        marker_line_width=1,
                        marker_opacity=0.6,
                        name="countries"
                    )
                )
        else:
            # Fallback to regular choropleth
            from core.country_mappings import get_iso_code
            country_isos = []
            valid_countries = []
            for country in unique_countries:
                iso = get_iso_code(country)
                if iso:
                    country_isos.append(iso)
                    valid_countries.append(country)
            
            if country_isos:
                fig.add_trace(
                    go.Choropleth(
                        locations=country_isos,
                        z=country_values[:len(country_isos)],
                        locationmode='ISO-3',
                        colorscale=[[0, 'rgba(200, 230, 200, 0.6)'], [1, 'rgba(200, 230, 200, 0.6)']],
                        showscale=False,
                        hoverinfo="text",
                        hovertext=[f"<b>{country}</b><br>Click to zoom to country" for country in valid_countries],
                        marker_line_width=1,
                        marker_line_color='white',
                        name="countries"
                    )
                )
    
    # Add port markers with proper red circles (changed from triangles)
    if use_mapbox:
        fig.add_trace(go.Scattermapbox(
            lon=lons,
            lat=lats,
            text=port_names,
            customdata=list(zip(countries, crudes, port_names)),
            mode='markers',
            marker=dict(
                size=15,
                color='red',  # Red color as requested
                symbol='circle',  # Changed from triangle-up to circle
                opacity=0.9
            ),
            name='Loading Ports',
            hovertemplate='<b>Country:</b> %{customdata[0]}<br>' +
                          '<b>Crude:</b> %{customdata[1]}<br>' +
                          '<b>Loading Port:</b> %{customdata[2]}<extra></extra>'
        ))
    else:
        fig.add_trace(go.Scattergeo(
            lon=lons,
            lat=lats,
            text=port_names,
            customdata=list(zip(countries, crudes, port_names)),
            mode='markers',
            marker=dict(
                size=15,
                color='red',  # Red color as requested
                symbol='circle',  # Changed from triangle-up to circle
                line=dict(width=1, color='white'),
                opacity=0.9
            ),
            name='Loading Ports',
            hovertemplate='<b>Country:</b> %{customdata[0]}<br>' +
                          '<b>Crude:</b> %{customdata[1]}<br>' +
                          '<b>Loading Port:</b> %{customdata[2]}<extra></extra>'
        ))
    
    # Add background click layer for reset functionality
    from .shared_map_utils import add_background_click_layer
    add_background_click_layer(fig, None, use_mapbox)
    
    # Calculate bounds for better view
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)
    
    # Calculate center
    center_lat = (lat_min + lat_max) / 2
    center_lon = (lon_min + lon_max) / 2
    
    # Calculate dynamic zoom and center based on country (similar to country_profile.py)
    lat_span = lat_max - lat_min
    lon_span = lon_max - lon_min
    max_span = max(lat_span, lon_span)
    
    # Dynamic zoom based on country size
    if max_span > 30:
        map_zoom = 1.2
    elif max_span > 15:
        map_zoom = 1.4
    elif max_span > 8:
        map_zoom = 1.8
    elif max_span > 4:
        map_zoom = 2.4
    elif max_span > 2:
        map_zoom = 2.8
    else:
        map_zoom = 3.4
    
    # Country-specific zoom overrides (based on the first country in the ports data)
    if unique_countries:
        selected_country = unique_countries[0]  # Use first country for zoom calculation
        country_zoom_overrides = {
            'Russia': 1.0, 'Canada': 0.9, 'United States': 1.0, 'Brazil': 1.2,
            'Australia': 1.1, 'China': 1.1, 'Saudi Arabia': 1.7, 'Iran': 1.8,
            'Norway': 2.1, 'United Kingdom': 2.5, 'Nigeria': 1.9, 'Venezuela': 1.8,
            'Mexico': 1.5, 'Indonesia': 1.6, 'Libya': 2.1, 'Algeria': 1.8,
            'Iraq': 2.2, 'Kuwait': 3.0, 'Qatar': 3.5, 'UAE': 2.7, 'Oman': 2.3
        }
        
        if selected_country in country_zoom_overrides:
            map_zoom = country_zoom_overrides[selected_country]
        
        # Adjust center for better visibility (similar to country_profile.py)
        if selected_country in ['United States', 'Russia']:
            adjusted_lat = center_lat + (lat_span * 0.30)
        elif selected_country == 'Canada':
            adjusted_lat = center_lat + (lat_span * 0.08)
        elif lat_span > 25:
            adjusted_lat = center_lat + (lat_span * 0.05)
        elif lat_span > 15:
            adjusted_lat = center_lat + (lat_span * 0.08)
        elif lat_span > 8:
            adjusted_lat = center_lat + (lat_span * 0.05)
        elif lat_span > 4:
            adjusted_lat = center_lat + (lat_span * 0.03)
        else:
            adjusted_lat = center_lat
        
        center_lat = adjusted_lat
    
    # Update mapbox layout with calculated center and zoom
    if use_mapbox:
        mapbox_layout.update({
            "center": {"lat": center_lat, "lon": center_lon},
            "zoom": map_zoom
        })
        
        fig.update_layout(
            height=500,
            margin=dict(l=0, r=0, t=0, b=0),
            mapbox=mapbox_layout,
            showlegend=False,
            plot_bgcolor=MAP_BACKGROUND_COLOR,
            paper_bgcolor="white",
            hovermode='closest'
        )
    else:
        fig.update_layout(
            height=500,
            margin=dict(l=0, r=0, t=0, b=0),
            geo=dict(
                projection_type="natural earth",
                center=dict(lat=center_lat, lon=center_lon),
                scope="world",
                showland=True,
                landcolor="rgb(243, 243, 243)",
                showocean=True,
                oceancolor=MAP_BACKGROUND_COLOR,  # Use shared white background
                showcountries=True,
                countrycolor="rgb(200, 200, 200)",
                showlakes=True,
                lakecolor=MAP_BACKGROUND_COLOR,  # Use shared white background
                # Use calculated bounds with zoom consideration
                lataxis=dict(range=[center_lat - (lat_span * (4 - map_zoom) / 2), center_lat + (lat_span * (4 - map_zoom) / 2)]),
                lonaxis=dict(range=[center_lon - (lon_span * (4 - map_zoom) / 2), center_lon + (lon_span * (4 - map_zoom) / 2)]),
                subunitcolor="rgb(200, 200, 200)",
                bgcolor=MAP_BACKGROUND_COLOR
            ),
            showlegend=False,
            plot_bgcolor=MAP_BACKGROUND_COLOR,
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
    assay_details = load_assay_details(default_crude)
    quality_specs = load_quality_specs(default_crude)
    port_details_data = load_port_details(default_crude)
    port_details_rows = port_details_data.get("rows", [])
    port_details_label = port_details_data.get("label", "Port Details")
    
    # Convert port details to DataTable format
    port_details_table_data = [{"Measure": row[0], port_details_label: row[1]} for row in port_details_rows]
    producers_sellers = load_producers_sellers(default_crude)
    
    production_fig = create_production_chart()
    map_fig = create_map_chart(default_crude)
    
    return html.Div(style={
        "fontFamily": "Arial, sans-serif",
        "maxWidth": "1500px",
        "margin": "0 auto",
        "padding": "20px",
        "backgroundColor": "white",
        "color": "#333",
        "overflowX": "hidden"
    }, children=[
        # Download components for CSV exports
        dcc.Download(id="download-mars-assay-csv"),
        dcc.Download(id="download-refined-products-csv"),
        dcc.Download(id="download-production-exports-csv"),
        dcc.Download(id="download-loading-ports-csv"),
        dcc.Download(id="download-port-details-csv"),
        dcc.Download(id="download-sellers-producers-csv"),
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
                    "color": "#fe5000",
                    "fontWeight": "bold",
                    "fontSize": "14px",
                    "display": "block",
                    "marginBottom": "5px"
                }),
                dcc.Loading(
                    id="crude-select-loading-spinner",
                    type="default",
                    color="#fe5000",
                    children=[
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
                    ]
                )
            ]),
            html.A(
                "Click here to see the Crude's Profile",
                href=assay_details.get("profile_url", "https://www.energyintel.com/wcod/crude-profile/Mars-Blend"),
                target="_blank",
                id="crude-profile-link",
                style={
                    "color": "#fe5000",
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
            # Left: Assay Details table
            dcc.Loading(
            id="assay-details-loading-spinner",
            type="default",
            color="#fe5000",
            children=[
                html.Div(style={
                    "flex": "1",
                    "minWidth": "250px",
                    "background": "#f8fafc",
                    "padding": "12px",
                    "borderRadius": "5px",
                    "border": "1px solid #e6e6e6"
                }, children=[
                    
                    html.Table(style={
                        "width": "100%",
                        "borderCollapse": "collapse",
                        "fontSize": "9pt",
                        "color": "#333"
                    }, children=[
                        html.Thead(html.Tr([
                            html.Th("Alternate Crude Names", style={
                                "border": "1px solid #e6e6e6",
                                "padding": "8px",
                                "backgroundColor": "#eef3f8",
                                "color": "#1f3263",
                                "fontWeight": "bold",
                                "textAlign": "left"
                            }),
                            html.Th("Country", style={
                                "border": "1px solid #e6e6e6",
                                "padding": "8px",
                                "backgroundColor": "#eef3f8",
                                "color": "#1f3263",
                                "fontWeight": "bold",
                                "textAlign": "left"
                            }),
                            html.Th("Assay Date", style={
                                "border": "1px solid #e6e6e6",
                                "padding": "8px",
                                "backgroundColor": "#eef3f8",
                                "color": "#1f3263",
                                "fontWeight": "bold",
                                "textAlign": "right"
                            })
                        ])),
                        html.Tbody(html.Tr([
                            html.Td(assay_details["alternate_names"], id="assay-alt-names", style={
                                "border": "1px solid #e6e6e6",
                                "padding": "8px"
                            }),
                            html.Td(assay_details["country"], id="assay-country", style={
                                "border": "1px solid #e6e6e6",
                                "padding": "8px"
                            }),
                            html.Td(assay_details["assay_date"], id="assay-date", style={
                                "border": "1px solid #e6e6e6",
                                "padding": "8px",
                                "textAlign": "right"
                            })
                        ]))
                    ])
                ])
            ]),
            
            # Center: Carbon Intensity Box
            dcc.Loading(
                id="carbon-intensity-loading-spinner",
                type="default",
                color="#fe5000",
                children=[
                    html.Div(style={
                        "background": "linear-gradient(135deg, #fff9e6, #ffedcc)",
                        "border": "1px solid #e6b800",
                        "padding": "20px 10px",
                        "borderRadius": "5px",
                        "textAlign": "center",
                        "minWidth": "150px",
                        "flexShrink": "0"
                    }, children=[
                        html.Div("Carbon Intensity", style={
                            "color": "#1b365d",
                            "fontWeight": "bold",
                            "fontSize": "9pt",
                            "marginBottom": "8px"
                        }),
                        html.Div("Low", id="carbon-intensity-value", style={
                            "color": "#1b365d",
                            "fontWeight": "normal",
                            "fontSize": "9pt"
                        })
                    ])
                ]
            ),
            
            # Right: Latest Quality Specs table
            dcc.Loading(
                id="quality-specs-loading-spinner",
                type="default",
                color="#fe5000",
                children=[
                    html.Div(style={
                        "flex": "1",
                        "minWidth": "350px",
                        "background": "#f8fafc",
                        "padding": "9pt",
                        "borderRadius": "5px",
                        "border": "1px solid #e6e6e6"
                    }, children=[
                        html.Div("Latest Quality Specs", style={
                            "color": "#fe5000",
                            "fontWeight": "bold",
                            "fontSize": "16px",
                            "marginBottom": "12px",                    
                            "paddingBottom": "6px",
                            "textAlign": "center"
                        }),
                        html.Table(style={
                            "width": "100%",
                            "borderCollapse": "collapse",
                            "fontSize": "13px",
                            "color": "#333"
                        }, children=[
                            html.Thead(html.Tr([
                                html.Th("Gravity (API at 60F)", style={
                                    "border": "1px solid #e6e6e6",
                                    "padding": "10px",
                                    "backgroundColor": "#eef3f8",
                                    "color": "#1f3263",
                                    "fontWeight": "bold",
                                    "textAlign": "center"
                                }),
                                html.Th("Sulfur Content (% Wt)", style={
                                    "border": "1px solid #e6e6e6",
                                    "padding": "10px",
                                    "backgroundColor": "#eef3f8",
                                    "color": "#1f3263",
                                    "fontWeight": "bold",
                                    "textAlign": "center"
                                }),
                                html.Th("TAN (mg KOH/g)", style={
                                    "border": "1px solid #e6e6e6",
                                    "padding": "10px",
                                    "backgroundColor": "#eef3f8",
                                    "color": "#1f3263",
                                    "fontWeight": "bold",
                                    "textAlign": "center"
                                })
                            ])),
                            html.Tbody([
                                html.Tr([
                                    html.Td(quality_specs[0][1] if len(quality_specs) > 0 else "28.40", id="quality-spec-gravity", style={
                                        "border": "1px solid #e6e6e6",
                                        "padding": "10px",
                                        "textAlign": "center"
                                    }),
                                    html.Td(quality_specs[1][1] if len(quality_specs) > 1 else "2.17", id="quality-spec-sulfur", style={
                                        "border": "1px solid #e6e6e6",
                                        "padding": "10px",
                                        "textAlign": "center"
                                    }),
                                    html.Td(quality_specs[2][1] if len(quality_specs) > 2 else "0.48", id="quality-spec-tan", style={
                                        "border": "1px solid #e6e6e6",
                                        "padding": "10px",
                                        "textAlign": "center"
                                    })
                                ])
                            ])
                        ])
                    ])
            ]), # Closing for html.Div (Latest Quality Specs)
        ]), # Closing for dcc.Loading (quality-specs-loading-spinner)
        
        # Main Grid Layout
        html.Div(style={
            "display": "grid",
            "gridTemplateColumns": "minmax(0, 2fr) minmax(0, 4fr) minmax(0, 4fr)",
            "gap": "15px",
            "marginBottom": "20px",
            "alignItems": "start"
        }, children=[
            # Column 1: Mars Blend Assay
            dcc.Loading(
                id="mars-assay-loading-spinner",
                type="default",
                color="#fe5000",
                children=[
                    html.Div(style={"gridColumn": "1 / 2"}, children=[
                        html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}, children=[
                            html.Div("Mars Blend Assay", style={
                                "color": "#fe5000",
                                "fontWeight": "bold",
                                "fontSize": "16px",
                                "margin": "20px 0 10px 0",                   
                                "paddingBottom": "5px",
                                "textAlign": "center"
                            }),
                            html.Button("Export to CSV", id='export-mars-assay-btn', n_clicks=0, style={'marginLeft': '12px', 'backgroundColor': 'white',
                                'color': '#2c3e50',
                                'border': '1px solid #dee2e6', 'padding': '6px 10px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '12px'})
                        ]),
                        create_grouped_assay_table(default_crude)
                    ]),
            ]), # Closing for dcc.Loading (mars-assay-loading-spinner)
            
            # Column 2: Refined Products Breakdown & Properties
            dcc.Loading(
                id="refined-products-loading-spinner",
                type="default",
                color="#fe5000",
                children=[
                    html.Div(style={"gridColumn": "2 / 2"}, children=[
                        html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}, children=[
                            html.Div("Refined Products Breakdown & Properties", style={
                                "color": "#fe5000",
                                "fontWeight": "bold",
                                "fontSize": "16px",
                                "margin": "20px 0 10px 0",                   
                                "paddingBottom": "5px",
                                "textAlign": "center"
                            }),
                            html.Button("Export to CSV", id='export-refined-products-btn', n_clicks=0, style={'marginLeft': '12px', 'backgroundColor': 'white',
                                'color': '#2c3e50',
                                'border': '1px solid #dee2e6', 'padding': '6px 10px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '12px'})
                        ]),
                        create_grouped_refined_products_table(default_crude)
                    ]),
            ]), # Closing for dcc.Loading (refined-products-loading-spinner)
            
            # Column 3: Right-side stack
            html.Div(style={"gridColumn": "3 / 4", "display": "flex", "flexDirection": "column"}, 
            children=[
                dcc.Loading(
                id="production-exports-loading-spinner",
                type="default",
                color="#fe5000",
                children=[
                    html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}, children=[
                        html.Div("Production and Exports", style={
                            "color": "#fe5000",
                            "fontWeight": "bold",
                            "fontSize": "16px", 
                            "margin": "20px 0 10px 0",                    
                            "paddingBottom": "5px",
                            "textAlign": "center"
                        }),
                        html.Button("Export to CSV", id='export-production-exports-btn', n_clicks=0, style={'marginLeft': '12px', 'backgroundColor': 'white',
                            'color': '#2c3e50',
                            'border': '1px solid #dee2e6', 'padding': '6px 10px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '12px'})
                    ]),
                    html.Div(style={
                        "border": "1px solid #ddd",
                        "padding": "15px",
                        "borderRadius": "4px",
                        "margin": "10px 0",
                        "backgroundColor": "white"
                    }, children=[
                        dcc.Graph(id="production-exports-graph", figure=production_fig, config={"displayModeBar": False})
                    ])
                ]), # Closing for dcc.Loading (production-exports-loading-spinner),
                
                html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}, 
                children=[
                    html.Div("Loading Ports", style={
                        "color": "#fe5000",
                        "fontWeight": "bold",
                        "fontSize": "16px",
                        "margin": "25px 0 10px 0",                   
                        "paddingBottom": "5px",
                        "textAlign": "center"
                    }),
                    html.Button("Export to CSV", id='export-loading-ports-btn', n_clicks=0, style={'marginLeft': '12px', 'backgroundColor': 'white',
                        'color': '#2c3e50',
                        'border': '1px solid #dee2e6', 'padding': '6px 10px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '12px'})
                ]),
                dcc.Loading(
                id="loading-ports-map-loading-spinner",
                type="default",
                color="#fe5000",
                    children=[
                html.Div(id="loading-ports-map-container", style={
                    "border": "1px solid #ddd",
                    "padding": "15px",
                    "borderRadius": "4px",
                    "margin": "10px 0",
                    "backgroundColor": "white"
                }, children=[
                    dcc.Graph(id="loading-ports-map", figure=map_fig, config={"displayModeBar": False}),
                        # html.Div([
                        #     html.A("© 2025 Mapbox", href="https://www.mapbox.com/about/maps", target="_blank", style={
                        #         "color": "#666",
                        #         "textDecoration": "none"
                        #     }),
                        #     " ",
                        #     html.A("© OpenStreetMap", href="https://www.openstreetmap.org/about", target="_blank", style={
                        #         "color": "#666",
                        #         "textDecoration": "none"
                        #     })
                        # ], style={
                        #     "fontSize": "10px",
                        #     "color": "#666",
                        #     "marginTop": "5px",
                        #     "textAlign": "left"
                        # })
                    ]),
                ]),
                
                html.Div("Inland points represent terminals for pipeline-delivered crudes.", style={
                    "fontSize": "11px",
                    "color": "#0066cc",
                    "marginTop": "5px",
                    "textAlign": "left"
                }),
            
                html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}, 
                children=[
                    html.Div("Port Details", style={
                        "color": "#fe5000",
                        "fontWeight": "bold",
                        "fontSize": "16px",
                        "margin": "25px 0 10px 0",                  
                        "paddingBottom": "5px",
                        "textAlign": "center"
                    }),
                    html.Button("Export to CSV", id='export-port-details-btn', n_clicks=0, style={'marginLeft': '12px', 'backgroundColor': 'white',
                        'color': '#2c3e50',
                        'border': '1px solid #dee2e6', 'padding': '6px 10px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '12px'})
                ]),
                dcc.Loading(
                id="port-details-table-loading-spinner",
                type="default",
                color="#fe5000",
                children=[
                html.Div(id="port-details-table-container", children=[
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
                            "fontFamily": "Arial, sans-serif",
                            "position": "relative",
                            "maxHeight": "500px",  # Consistent with assay table
                            "overflowY": "auto",
                            "overflowX": "auto",
                            "border": "1px solid #ddd",
                        },
                        style_cell={
                            "border": "1px solid #ddd",
                            "padding": "2px 8px",
                            "fontSize": "12px",
                            "textAlign": "left",
                            "backgroundColor": "white",
                            "fontFamily": "Arial, sans-serif",
                            "whiteSpace": "normal",
                            "height": "auto",
                            "minHeight": "20px",
                            "verticalAlign": "middle",
                        },
                        style_header={
                            "backgroundColor": "#f5f5f5",
                            "fontWeight": "bold",
                            "fontSize": "12px",
                            "border": "1px solid #ddd",
                            "padding": "4px 8px",
                            "textAlign": "left", # Default to left, then override conditionally
                            "position": "static", # Make header sticky
                            "top": "0",
                            "zIndex": "10",
                        },
                        style_data={
                            "border": "1px solid #ddd",
                            "whiteSpace": "normal",
                            "height": "auto"
                        },
                        style_header_conditional=[
                            {
                                "if": {"column_id": "Measure"},
                                "textAlign": "left",
                            },
                            {
                                "if": {"column_id": port_details_label},
                                "textAlign": "right",
                                "paddingRight": "0px",
                            },
                        ],
                        style_data_conditional=[
                            # Alternate row colors for better readability
                            {"if": {"row_index": "odd"}, "backgroundColor": "#f9f9f9"},
                            {"if": {"row_index": "even"}, "backgroundColor": "#FFFFFF"},
                            # Measure column styling
                            {
                                "if": {"column_id": "Measure"},
                                "fontWeight": "normal",
                                "color": "#1f3263",
                                "borderRight": "2px solid #ccc",
                                "maxWidth": "150px", # Example max-width, adjust as needed
                                "textAlign": "left",
                                "padding": "2px 8px",
                            },
                            {
                                "if": {"column_id": port_details_label},
                                "textAlign": "right",
                                "padding": "2px 0px",
                            },
                        ],
                        css=[
                            # Stronger border for Measure column
                            {
                                'selector': '.dash-cell[data-dash-column="Measure"]',
                                'rule': 'border-right: 2px solid #ccc !important;'
                            },
                        ],
                        editable=False,
                        sort_action="native",
                        filter_action="none",
                        page_action="none",
                    )
                ]), # Closing for html.Div (port-details-table-container)
                ]), # Closing for dcc.Loading (port-details-table-loading-spinner)
            ]), # Closing for dcc.Loading (loading-ports-map-loading-spinner),   
            html.Div(style={"gridColumn": "1 / 3", "marginBottom": "20px"}, 
            children=[ # Wrapper for the entire section
                dcc.Loading(
                id="sellers-producers-loading-spinner",
                type="default",
                color="#fe5000",
                children=[
                    html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}, children=[
                        html.Div("Sellers and Producers", style={
                            "color": "#fe5000",
                            "fontWeight": "bold",
                            "fontSize": "16px",
                            "margin": "20px 0 10px 0",
                            "paddingBottom": "5px",
                            "textAlign": "center"
                        }),
                        html.Button("Export to CSV", id='export-sellers-producers-btn', n_clicks=0, style={'marginLeft': '12px', 'backgroundColor': 'white',
                            'color': '#2c3e50',
                            'border': '1px solid #dee2e6', 'padding': '6px 10px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '12px'})
                    ]),
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
                            }),
                            html.Th("Crude Name", style={
                                "border": "1px solid #ddd",
                                "padding": "10px",
                                "backgroundColor": "#f5f5f5",
                                "fontWeight": "bold",
                                "textAlign": "left",
                                "fontSize": "12px"
                            })
                        ])),
                        html.Tbody(html.Tr([
                            html.Td(producers_sellers[0][0] if producers_sellers else "", id="producers-cell", style={
                                "border": "1px solid #ddd",
                                "padding": "10px",
                                "fontSize": "12px"
                            }),
                            html.Td(producers_sellers[0][1] if producers_sellers else "", id="sellers-cell", style={
                                "border": "1px solid #ddd",
                                "padding": "10px",
                                "fontSize": "12px"
                            }),
                            html.Td(producers_sellers[0][2] if producers_sellers else "", id="crude-name-cell", style={
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
                ]) # Closing for dcc.Loading (sellers-producers-loading-spinner)
            
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
        Output('quality-spec-gravity', 'children'),
        Output('quality-spec-sulfur', 'children'),
        Output('quality-spec-tan', 'children'),
        Output('carbon-intensity-value', 'children'),
        Output('loading-ports-map', 'figure'),
        Output('loading-ports-map-container', 'style'), # Added for conditional visibility
        Output('port-details-table', 'data'),
        Output('port-details-table', 'columns'),
        Output('port-details-table-container', 'style'), # Added for conditional visibility
        Output('production-exports-graph', 'figure'),
        Output('producers-cell', 'children'),
        Output('sellers-cell', 'children'),
        Output('crude-name-cell', 'children'), # Added output for Crude Name
        Output('assay-alt-names', 'children'),
        Output('assay-country', 'children'),
        Output('assay-date', 'children'),
        Output('crude-profile-link', 'href'),
        Input('crude-select', 'value')
    )
    def update_crude_profile(selected_crude):
        """Update tables and quality specs when crude selection changes."""
        if selected_crude:
            # Reload data from the database for the selected crude name
            assay_data = load_mars_assay(selected_crude)
            grouped_data = load_refined_products(selected_crude)
            quality_specs = load_quality_specs(selected_crude)
            carbon_intensity = load_carbon_intensity(selected_crude)
            ports_data = load_loading_ports(selected_crude) # Load ports data here
            port_details_data = load_port_details(selected_crude)
            map_fig = create_map_chart(selected_crude)
            production_fig = create_production_chart(selected_crude)
            producers_sellers = load_producers_sellers(selected_crude)
            assay_details = load_assay_details(selected_crude)

            # Determine map visibility
            map_display_style = {'display': 'block'} if ports_data else {'display': 'none'}

            # Handle port details - support both single and multi-port formats
            port_details_rows_data = port_details_data.get("rows", [])
            port_details_display_style = {'display': 'block'} if port_details_rows_data else {'display': 'none'}
            
            # Check if this is multi-port data
            is_multi_port = port_details_data.get("is_multi_port", False)
            
            if is_multi_port:
                # Multi-port format: rows are already dictionaries with port columns
                port_rows = port_details_rows_data
                port_ports = port_details_data.get("ports", [])
                
                # Create columns: Measure + one column per port
                port_columns = [
                    {"name": "Measure", "id": "Measure", "header_style": {"textAlign": "left"}, "style": {"textAlign": "left"}}
                ]
                for port in port_ports:
                    port_columns.append({
                        "name": port, 
                        "id": port, 
                        "header_style": {"textAlign": "center"}, 
                        "style": {"textAlign": "center"}
                    })
            else:
                # Single port format: convert tuples to dictionaries (backward compatibility)
                port_label = port_details_data.get("label", "Port Details")
                port_rows = [{"Measure": r[0], port_label: r[1]} for r in port_details_rows_data]
                port_columns = [
                    {"name": "Measure", "id": "Measure", "header_style": {"textAlign": "left"}, "style": {"textAlign": "left"}},
                    {"name": port_label, "id": port_label, "header_style": {"textAlign": "center"}, "style": {"textAlign": "center"}}
                ]

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

            gravity_val = quality_specs[0][1] if len(quality_specs) > 0 else "28.40"
            sulfur_val = quality_specs[1][1] if len(quality_specs) > 1 else "2.17"
            tan_val = quality_specs[2][1] if len(quality_specs) > 2 else "0.48"

            prod_text = producers_sellers[0][0] if producers_sellers else ""
            sell_text = producers_sellers[0][1] if producers_sellers else ""
            crude_text = producers_sellers[0][2] if producers_sellers else ""

            return (
                assay_data,
                table_data,
                gravity_val,
                sulfur_val,
                tan_val,
                carbon_intensity,
                map_fig,
                map_display_style, # Added map_display_style
                port_rows,
                port_columns,
                port_details_display_style, # Added port_details_display_style
                production_fig,
                prod_text,
                sell_text,
                crude_text, # Added crude_text to the return tuple
                assay_details.get("alternate_names", ""),
                assay_details.get("country", ""),
                assay_details.get("assay_date", ""),
                assay_details.get("profile_url", "https://www.energyintel.com/wcod/crude-profile/Mars-Blend"),
            )
        
        # Return empty data for other crudes (if added later)
        empty_port_rows = []
        empty_port_cols = [
            {"name": "Measure", "id": "Measure"},
            {"name": "Port Details", "id": "Port Details"}
        ]
        empty_map_style = {'display': 'none'}
        empty_port_style = {'display': 'none'}
        
        return (
            [],
            [],
            "28.40",
            "2.17",
            "0.48",
            "Low",
            create_empty_map("No data available", height=500),
            empty_map_style,
            empty_port_rows,
            empty_port_cols,
            empty_port_style,
            create_production_chart(),
            "",
            "",
            "",
            "",
            "United States",
            "2025",
            "https://www.energyintel.com/wcod/crude-profile/Mars-Blend",
        )

    # Callbacks for CSV exports
    @app.callback(
        Output('download-mars-assay-csv', 'data'),
        Input('export-mars-assay-btn', 'n_clicks'),
        State('crude-select', 'value'),
        prevent_initial_call=True
    )
    def export_mars_assay_csv(n_clicks, selected_crude):
        if n_clicks and selected_crude:
            df = pd.DataFrame(load_mars_assay(selected_crude))
            return dcc.send_data_frame(df.to_csv, filename=f"{selected_crude}_Mars_Blend_Assay.csv")
        raise dash.exceptions.PreventUpdate

    @app.callback(
        Output('download-refined-products-csv', 'data'),
        Input('export-refined-products-btn', 'n_clicks'),
        State('crude-select', 'value'),
        prevent_initial_call=True
    )
    def export_refined_products_csv(n_clicks, selected_crude):
        if n_clicks and selected_crude:
            grouped_data = load_refined_products(selected_crude)
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
            df = pd.DataFrame(table_data)
            return dcc.send_data_frame(df.to_csv, filename=f"{selected_crude}_Refined_Products_Breakdown_Properties.csv")
        raise dash.exceptions.PreventUpdate

    @app.callback(
        Output('download-production-exports-csv', 'data'),
        Input('export-production-exports-btn', 'n_clicks'),
        State('crude-select', 'value'),
        prevent_initial_call=True
    )
    def export_production_exports_csv(n_clicks, selected_crude):
        if n_clicks and selected_crude:
            df = pd.DataFrame(load_production_exports(selected_crude))
            return dcc.send_data_frame(df.to_csv, filename=f"{selected_crude}_Production_Exports.csv")
        raise dash.exceptions.PreventUpdate

    @app.callback(
        Output('download-loading-ports-csv', 'data'),
        Input('export-loading-ports-btn', 'n_clicks'),
        State('crude-select', 'value'),
        prevent_initial_call=True
    )
    def export_loading_ports_csv(n_clicks, selected_crude):
        if n_clicks and selected_crude:
            ports_data = load_loading_ports(selected_crude)
            df = pd.DataFrame([
                {
                    "Latitude": port.get('latitude'),
                    "Longitude": port.get('longitude'),
                    "Country": port.get('country'),
                    "Crude": port.get('crude'),
                        "Port Name": port.get('port'),
                    }
                    for port in ports_data
            ])
            df.drop_duplicates(subset=["Latitude", "Longitude", "Country", "Crude", "Port Name"], inplace=True)
            return dcc.send_data_frame(df.to_csv, filename=f"{selected_crude}_Loading_Ports_Map_Data.csv")
        raise dash.exceptions.PreventUpdate

    @app.callback(
        Output('download-port-details-csv', 'data'),
        Input('export-port-details-btn', 'n_clicks'),
        State('crude-select', 'value'),
        prevent_initial_call=True
    )
    def export_port_details_csv(n_clicks, selected_crude):
        if n_clicks and selected_crude:
            port_details_data = load_port_details(selected_crude)
            rows = port_details_data.get("rows", [])
            is_multi_port = port_details_data.get("is_multi_port", False)
            
            if is_multi_port:
                # Multi-port format: rows are already dictionaries
                df = pd.DataFrame(rows)
            else:
                # Single port format: convert tuples to dictionaries
                formatted_rows = []
                for r in rows:
                    measure_name = " ".join([word.capitalize() for word in r[0].split('_')])
                    formatted_rows.append({"Measure": measure_name, port_details_data.get("label", "Value"): r[1]})
                df = pd.DataFrame(formatted_rows)
            
            return dcc.send_data_frame(df.to_csv, filename=f"{selected_crude}_Port_Details.csv")
        raise dash.exceptions.PreventUpdate

    @app.callback(
        Output('download-sellers-producers-csv', 'data'),
        Input('export-sellers-producers-btn', 'n_clicks'),
        State('crude-select', 'value'),
        prevent_initial_call=True
    )
    def export_sellers_producers_csv(n_clicks, selected_crude):
        if n_clicks and selected_crude:
            producers_sellers = load_producers_sellers(selected_crude)
            df = pd.DataFrame(producers_sellers, columns=["Producers", "Sellers", "Crude Name"])
            return dcc.send_data_frame(df.to_csv, filename=f"{selected_crude}_Sellers_Producers.csv")
        raise dash.exceptions.PreventUpdate
    
    # Separate map click callback for country-level zoom functionality
    @app.callback(
        Output('loading-ports-map', 'figure', allow_duplicate=True),
        Input('loading-ports-map', 'clickData'),
        State('crude-select', 'value'),
        prevent_initial_call=True
    )
    def handle_map_click(click_data, selected_crude):
        """Handle map clicks for country-level zoom and reset functionality."""
        if not click_data:
            return no_update
        
        # Get the current map figure
        current_fig = create_map_chart(selected_crude)
        
        # Extract click information
        point = click_data["points"][0]
        
        # Check if it's a background click (reset to world view)
        is_background_click = False
        clicked_country = None
        
        if "customdata" in point and point["customdata"]:
            if isinstance(point["customdata"], list) and len(point["customdata"]) > 0:
                if point["customdata"][0] == "__BACKGROUND_CLICK__":
                    is_background_click = True
                else:
                    # This might be a port click, extract country from port data
                    clicked_country = point["customdata"][0]  # Country is first element
            elif point["customdata"] == "__BACKGROUND_CLICK__":
                is_background_click = True
        
        # Check if it's a country choropleth click
        if "hovertext" in point and point["hovertext"] and "Click to zoom to country" in point["hovertext"]:
            # Extract country name from hover text
            hovertext = point["hovertext"]
            if "<b>" in hovertext and "</b>" in hovertext:
                clicked_country = hovertext.split("<b>")[1].split("</b>")[0]
        
        # If background click or ocean click, reset to world view
        if is_background_click or (not clicked_country and "lon" in point and "lat" in point):
            # Return the default world view
            return create_map_chart(selected_crude)
        
        # If a country was clicked, zoom to that country
        if clicked_country:
            # Get ports data for the selected crude
            ports_data = load_loading_ports(selected_crude)
            
            # Filter ports for the clicked country
            country_ports = [port for port in ports_data if port.get('country') == clicked_country]
            
            if country_ports:
                # Calculate bounds for the country
                country_lats = [port.get('latitude') for port in country_ports if port.get('latitude')]
                country_lons = [port.get('longitude') for port in country_ports if port.get('longitude')]
                
                if country_lats and country_lons:
                    lat_min, lat_max = min(country_lats), max(country_lats)
                    lon_min, lon_max = min(country_lons), max(country_lons)
                    
                    # Add padding
                    lat_pad = max(2, (lat_max - lat_min) * 0.3)
                    lon_pad = max(2, (lon_max - lon_min) * 0.3)
                    lat_min -= lat_pad
                    lat_max += lat_pad
                    lon_min -= lon_pad
                    lon_max += lon_pad
                    
                    center_lat = (lat_min + lat_max) / 2
                    center_lon = (lon_min + lon_max) / 2
                    
                    # Calculate appropriate zoom level
                    lat_range = lat_max - lat_min
                    lon_range = lon_max - lon_min
                    max_range = max(lat_range, lon_range)
                    
                    if max_range < 5:
                        zoom = 6
                    elif max_range < 10:
                        zoom = 5
                    elif max_range < 20:
                        zoom = 4
                    else:
                        zoom = 3
                    
                    # Update the figure with new center and zoom
                    use_mapbox, token, mapbox_layout = get_mapbox_config()
                    
                    if use_mapbox:
                        current_fig.update_layout(
                            mapbox=dict(
                                **mapbox_layout,
                                center=dict(lat=center_lat, lon=center_lon),
                                zoom=zoom
                            )
                        )
                    else:
                        current_fig.update_layout(
                            geo=dict(
                                projection_type="natural earth",
                                center=dict(lat=center_lat, lon=center_lon),
                                scope="world",
                                showland=True,
                                landcolor="rgb(243, 243, 243)",
                                showocean=True,
                                oceancolor=MAP_BACKGROUND_COLOR,
                                showcountries=True,
                                countrycolor="rgb(200, 200, 200)",
                                showlakes=True,
                                lakecolor=MAP_BACKGROUND_COLOR,
                                lataxis=dict(range=[lat_min - 10, lat_max + 10]),
                                lonaxis=dict(range=[lon_min - 20, lon_max + 20]),
                                subunitcolor="rgb(200, 200, 200)",
                                bgcolor=MAP_BACKGROUND_COLOR
                            )
                        )
                    
                    return current_fig
        
        # Default: return current figure unchanged
        return no_update
    
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
                
                #assay-table .dash-spreadsheet-inner {
                    max-height: 750px !important;
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
                p {
                    margin-top: 0;
                    margin-bottom: 0;
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
    dash_app.layout = create_layout()
    register_callbacks(dash_app)