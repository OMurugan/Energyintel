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

# ------------------------------------------------------------------------------
# FILE PATHS
# ------------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "Crude_Profile")

CSV_PATHS = {
    "assay_details": os.path.join(DATA_DIR, "Assay_Details_data(1).csv"),
    "quality_specs": os.path.join(DATA_DIR, "Latest_Quality_Specs_data(1).csv"),
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

def load_mars_assay():
    """Load Mars Blend Assay data with merged Property column for Viscosity."""
    df = load_csv_data(CSV_PATHS["mars_assay"])
    if df is None or df.empty:
        return [
            {"Property": "Barrels", "Unit": "Per Metric Ton", "Value": "7.13"},
        ]
    
    # Find value column (could be "Value", "Avg. Value", "Column Header", etc.)
    value_col = None
    for col in df.columns:
        if col.lower() in ["value", "avg. value", "avg value"]:
            value_col = col
            break
    
    if not value_col:
        # Try "Column Header" as fallback
        if "Column Header" in df.columns:
            value_col = "Column Header"
        else:
            # Use first column that's not Property, Unit, Source, Copyright
            for col in df.columns:
                if col not in ["Property", "Unit", "Source", "Copyright"]:
                    value_col = col
                    break
    
    # Load all rows - keep all rows separate, we'll merge Property column visually
    assay_data = []
    for _, row in df.iterrows():
        property_val = str(row.get("Property", "")).strip() if "Property" in row and pd.notna(row.get("Property")) else ""
        unit_val = str(row.get("Unit", "")).strip() if "Unit" in row and pd.notna(row.get("Unit")) else ""
        value_val = str(row.get(value_col, "")).strip() if value_col and value_col in row and pd.notna(row.get(value_col)) else ""
        
        if property_val:  # Only add if we have a property
            assay_data.append({
                "Property": property_val,
                "Unit": unit_val,
                "Value": value_val
            })
    
    # Process Viscosity entries to merge them under one Property
    if assay_data:
        # Separate viscosity rows from other rows
        viscosity_rows = []
        other_rows = []
        
        for row in assay_data:
            if row["Property"] == "Viscosity":
                viscosity_rows.append(row)
            else:
                other_rows.append(row)
        
        # Sort viscosity rows by temperature (20 C, 40 C, 50 C)
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
        
        # Reconstruct assay_data with merged Viscosity
        # First viscosity row keeps "Viscosity" in Property column
        # Subsequent rows have empty Property column for merged appearance
        processed_assay_data = other_rows.copy()
        
        if viscosity_rows:
            # Add first viscosity row with Property name
            first_viscosity = viscosity_rows[0]
            first_viscosity["Property"] = "Viscosity"
            processed_assay_data.append(first_viscosity)
            
            # Add remaining viscosity rows with empty Property column
            for viscosity_row in viscosity_rows[1:]:
                viscosity_row["Property"] = ""  # Empty for merged appearance
                processed_assay_data.append(viscosity_row)
        
        assay_data = processed_assay_data
    
    return assay_data if assay_data else [
        {"Property": "Barrels", "Unit": "Per Metric Ton", "Value": "7.13"}
    ]

def load_refined_products():
    """Load refined products breakdown data with merged cells for Product and Cut Points."""
    # Use header=0 since the CSV has headers in the first row
    df = load_csv_data(CSV_PATHS["refined_products"], header=0)
    
    if df is None or df.empty:
        # Return fallback data with merged format
        return [
            {
                "Product": "Heavy Gasoil",
                "Cut Points (°C)": "300-350",
                "properties": [
                    {"Property": "", "Unit": "Yield Volume (%)", "Value": "7.80"},
                    {"Property": "", "Unit": "Yield Weight (%)", "Value": "7.74"},
                    {"Property": "Pour Point", "Unit": "Temp. C", "Value": "-6.83"},
                    {"Property": "Sulfur Content", "Unit": "% Wt", "Value": "1.57"},
                ]
            }
        ]
    
    df = df.dropna(how="all")
    
    # Forward fill Product and Cut Points columns to handle empty cells
    df["Product"] = df["Product"].ffill()
    
    # Handle Cut Points column variations
    cut_col = None
    for col in df.columns:
        if "cut points" in col.lower() or "cut points" in col.lower():
            cut_col = col
            break
    
    if cut_col:
        df[cut_col] = df[cut_col].ffill()
    else:
        df["Cut Points (°C)"] = ""
        cut_col = "Cut Points (°C)"
    
    # Find value column
    value_col = None
    for col in df.columns:
        if "value" in col.lower():
            value_col = col
            break
    
    if not value_col:
        value_col = df.columns[-1]  # Use last column as fallback
    
    # Process data into grouped structure
    grouped_products = []
    current_product = None
    current_cut_points = None
    current_properties = []
    
    for _, row in df.iterrows():
        product = str(row["Product"]).strip() if pd.notna(row["Product"]) else ""
        cut_points = str(row[cut_col]).strip() if cut_col in row and pd.notna(row[cut_col]) else ""
        
        # Get Property and Unit values
        property_val = ""
        unit_val = ""
        
        if "Property" in df.columns and pd.notna(row["Property"]):
            property_val = str(row["Property"]).strip()
        
        if "Unit" in df.columns and pd.notna(row["Unit"]):
            unit_val = str(row["Unit"]).strip()
        elif property_val and "Unit" not in df.columns:
            # If there's no Unit column, check if property contains unit info
            if "(" in property_val and ")" in property_val:
                # Extract property name and unit
                match = re.match(r"^(.*?)\s*\((.*?)\)$", property_val)
                if match:
                    property_val = match.group(1).strip()
                    unit_val = match.group(2).strip()
        
        # Get value
        value = str(row[value_col]).strip() if value_col in row and pd.notna(row[value_col]) else ""
        
        # When product changes, save the previous product's data
        if product and product != current_product:
            if current_product and current_properties:
                grouped_products.append({
                    "Product": current_product,
                    "Cut Points (°C)": current_cut_points or "",
                    "properties": current_properties.copy()
                })
            current_product = product
            current_cut_points = cut_points
            current_properties = []
        
        # Only add properties with values
        if property_val or unit_val or value:
            current_properties.append({
                "Property": property_val,
                "Unit": unit_val,
                "Value": value
            })
    
    # Don't forget the last product
    if current_product and current_properties:
        grouped_products.append({
            "Product": current_product,
            "Cut Points (°C)": current_cut_points or "",
            "properties": current_properties.copy()
        })
    
    # If no grouped data was created, return fallback
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
                ]
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
def create_grouped_refined_products_table():
    """Create a grouped Refined Products table with merged Product and Cut Points cells."""
    grouped_data = load_refined_products()
    
    # Convert grouped data to flat rows for DataTable
    table_data = []
    for product_group in grouped_data:
        product = product_group["Product"]
        cut_points = product_group["Cut Points (°C)"]
        properties = product_group["properties"]
        
        for i, prop in enumerate(properties):
            table_data.append({
                "Product": product if i == 0 else "",  # Only show product on first row
                "Cut Points (°C)": cut_points if i == 0 else "",  # Only show cut points on first row
                "Property": prop["Property"],
                "Unit": prop["Unit"],
                "Value": prop["Value"]
            })
    
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
            "fontFamily": "Arial, sans-serif"
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
        },
        style_header={
            "backgroundColor": "#f5f5f5",
            "fontWeight": "bold",
            "fontSize": "12px",
            "border": "1px solid #ddd",
            "padding": "10px",
            "textAlign": "left"
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
                'selector': '.dash-cell[data-dash-column="Product"]:empty',
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
                'selector': '.dash-cell[data-dash-column="Product"]:not(:empty) + .dash-cell[data-dash-column="Product"]:empty',
                'rule': 'border-top: none !important;'
            },
            # Hide empty Cut Points cells to create merged appearance
            {
                'selector': '.dash-cell[data-dash-column="Cut Points (°C)"]:empty',
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
                'selector': '.dash-cell[data-dash-column="Cut Points (°C)"]:not(:empty) + .dash-cell[data-dash-column="Cut Points (°C)"]:empty',
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
        sort_action="none",
        filter_action="none",
        page_action="none",
    )

def create_grouped_assay_table():
    """Create Mars Blend Assay table with merged Property cells for Viscosity."""
    assay_data = load_mars_assay()
    
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
        sort_action="none",
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
                    options=[{"label": "Mars Blend", "value": "mars"}],
                    value="mars",
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
                create_grouped_assay_table()
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
                create_grouped_refined_products_table()
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
                    sort_action="none",
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
    # Since we're using static grouped tables with no interactive sorting,
    # we don't need complex callbacks. But we'll add a simple one for the dropdown.
    
    @app.callback(
        Output('assay-table', 'data'),
        Output('refined-products-table', 'data'),
        Input('crude-select', 'value')
    )
    def update_crude_profile(selected_crude):
        """Update tables when crude selection changes."""
        # Currently only Mars Blend is supported
        if selected_crude == 'mars':
            # Reload data
            assay_data = load_mars_assay()
            grouped_data = load_refined_products()
            
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

# ------------------------------------------------------------------------------
# DASH APP CREATION - MAIN FUNCTION
# ------------------------------------------------------------------------------
def create_crude_profile_dashboard(server, url_base_pathname="/dash/crude-profile/"):
    """Create and configure the crude profile dashboard with grouped tables."""
    try:
        from app import create_dash_app
        dash_app = create_dash_app(server, url_base_pathname)
    except ImportError:
        dash_app = Dash(__name__, server=server, url_base_pathname=url_base_pathname)
    
    dash_app.layout = create_layout()
    register_callbacks(dash_app)
    return dash_app

# For standalone testing
if __name__ == "__main__":
    app = Dash(__name__)
    app.layout = create_layout()
    register_callbacks(app)
    app.run_server(debug=True, port=8050)