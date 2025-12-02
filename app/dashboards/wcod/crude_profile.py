"""
Crude Profile Dashboard - Complete Implementation with Latest Quality Specs Hover Popup
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
# DATA LOADING FUNCTIONS - UPDATED FOR MERGED CELLS
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
# SORTING FUNCTIONS
# ------------------------------------------------------------------------------
def sort_assay_data_alphabetically(data, column, direction='asc'):
    """Sort assay data alphabetically by specified column"""
    if not data:
        return data
    
    df = pd.DataFrame(data)
    df_sorted = df.sort_values(column, ascending=(direction == 'asc'), na_position='last')
    return df_sorted.to_dict('records')

def sort_refined_products_data(data, column, sort_type, direction):
    """Sort refined products data based on column and sort type."""
    if not data:
        return data
    
    data_copy = data.copy()
    
    if sort_type == 'source':
        return data_copy
    elif sort_type == 'alphabetic':
        reverse = (direction == 'desc')
        data_copy.sort(key=lambda x: str(x.get(column, '')).lower(), reverse=reverse)
        return data_copy
    elif sort_type in ['field', 'nested']:
        # Sort by maximum value (for Property column only)
        reverse = (direction == 'desc')
        data_copy.sort(key=lambda x: float(str(x.get('Value', '0')).replace(',', '')) if str(x.get('Value', '0')).replace('.', '').replace('-', '').isdigit() else 0, reverse=reverse)
        return data_copy
    return data_copy

# ------------------------------------------------------------------------------
# CREATING TABLES WITH MERGED CELLS
# ------------------------------------------------------------------------------
def create_refined_products_table():
    """Create the Refined Products Breakdown & Properties table with merged cells."""
    grouped_data = load_refined_products()
    
    # Convert grouped data to flat rows for DataTable with merged cells
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
            {
                'selector': '.dash-header[data-dash-column="Product"]',
                'rule': 'position: relative;'
            },
            {
                'selector': '.dash-header[data-dash-column="Cut Points (°C)"]',
                'rule': 'position: relative;'
            },
            {
                'selector': '.dash-header[data-dash-column="Property"]',
                'rule': 'position: relative;'
            },
            {
                'selector': '.dash-header[data-dash-column="Unit"]',
                'rule': 'position: relative;'
            },
            # Sort indicator (SVG icon) for ALL headers - HIDDEN BY DEFAULT
            {
                'selector': '.dash-header .sort-indicator',
                'rule': '''
                    position: absolute;
                    right: 8px;
                    top: 50%;
                    transform: translateY(-50%);
                    width: 15px;
                    height: 15px;
                    cursor: pointer;
                    opacity: 0;
                    transition: opacity 0.2s ease;
                '''
            },
            {
                'selector': '.dash-header:hover .sort-indicator',
                'rule': '''
                    opacity: 1;
                '''
            },
            {
                'selector': '.dash-header .sort-indicator:hover',
                'rule': '''
                    background-color: #e6f3ff;
                    border-radius: 2px;
                '''
            },
        ],
        markdown_options={"html": True},
        editable=False,
        sort_action="none",
        filter_action="none",
        page_action="none",
    )

def create_assay_table():
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
            # Sort indicator (SVG icon) for ALL headers - HIDDEN BY DEFAULT
            {
                'selector': '.dash-header .sort-indicator',
                'rule': '''
                    position: absolute;
                    right: 8px;
                    top: 50%;
                    transform: translateY(-50%);
                    width: 15px;
                    height: 15px;
                    cursor: pointer;
                    opacity: 0;
                    transition: opacity 0.2s ease;
                '''
            },
            {
                'selector': '.dash-header:hover .sort-indicator',
                'rule': '''
                    opacity: 1;
                '''
            },
            {
                'selector': '.dash-header .sort-indicator:hover',
                'rule': '''
                    background-color: #e6f3ff;
                    border-radius: 2px;
                '''
            },
            # A/Z sort order container - HIDDEN BY DEFAULT (Both tables)
            {
                'selector': '#assay-table .dash-header .sort-order-container',
                'rule': '''
                    opacity: 0 !important;
                    visibility: hidden !important;
                    pointer-events: none;
                '''
            },
            {
                'selector': '#assay-table .dash-header:hover .sort-order-container',
                'rule': '''
                    opacity: 1 !important;
                    visibility: visible !important;
                    pointer-events: auto;
                '''
            },
            {
                'selector': '#refined-products-table .dash-header .sort-order-container',
                'rule': '''
                    opacity: 0 !important;
                    visibility: hidden !important;
                    pointer-events: none;
                '''
            },
            {
                'selector': '#refined-products-table .dash-header:hover .sort-order-container',
                'rule': '''
                    opacity: 1 !important;
                    visibility: visible !important;
                    pointer-events: auto;
                '''
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
        width=None,
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
        paper_bgcolor='white',
        autosize=False
    )
    
    # Config to completely disable all interactive and responsive features
    config = {
        "displayModeBar": False,
        "staticPlot": True,  # CRITICAL: This disables all resize handlers
        "displaylogo": False
    }
    
    return dcc.Graph(
        id='production-chart',
        figure=fig,
        config=config,
        style={
            "width": "100%", 
            "height": "400px", 
            "minHeight": "400px", 
            "maxHeight": "400px",
            "overflow": "hidden",
            "position": "relative"
        }
    )

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
            ),
            # CRITICAL FIX: Completely disable resize and autosize features
            autosize=False,
        )
        
        # Config to disable all responsive features
        # Config to completely disable all interactive and responsive features
        config = {
            "displayModeBar": False,
            "staticPlot": True,  # CRITICAL: This disables all resize handlers
            "displaylogo": False
        }
        
        return dcc.Graph(
            id='map-chart',
            figure=fig,
            config=config,
            style={
                "width": "100%", 
                "height": "500px", 
                "minHeight": "500px", 
                "maxHeight": "500px",
                "overflow": "hidden",
                "position": "relative"
            }
        )
    
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
        width=None,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        geo_bgcolor="white",
        paper_bgcolor="white",
        hovermode='closest',
        autosize=False
    )
    
    # Config to completely disable all interactive and responsive features
    config = {
        "displayModeBar": False,
        "staticPlot": True,  # CRITICAL: This disables all resize handlers
        "displaylogo": False
    }
    
    return dcc.Graph(
        id='map-chart',
        figure=fig,
        config=config,
        style={
            "width": "100%", 
            "height": "500px", 
            "minHeight": "500px", 
            "maxHeight": "500px",
            "overflow": "hidden",
            "position": "relative"
        }
    )

# ------------------------------------------------------------------------------
# INITIAL LOAD
# ------------------------------------------------------------------------------
assay_data = load_mars_assay()

# Load refined products data for initial store
refined_grouped_data = load_refined_products()
refined_products_data = []
for product_group in refined_grouped_data:
    product = product_group["Product"]
    cut_points = product_group["Cut Points (°C)"]
    properties = product_group["properties"]
    
    for i, prop in enumerate(properties):
        refined_products_data.append({
            "Product": product if i == 0 else "",
            "Cut Points (°C)": cut_points if i == 0 else "",
            "Property": prop["Property"],
            "Unit": prop["Unit"],
            "Value": prop["Value"]
        })

# ------------------------------------------------------------------------------
# LAYOUT
# ------------------------------------------------------------------------------
def create_layout(server=None):
    """Layout with Latest Quality Specs hover popup functionality."""
    
    # Load dynamic data
    assay_details = load_assay_details()
    quality_specs = load_quality_specs()
    port_details_data = load_port_details()
    port_details_rows = port_details_data.get("rows", [])
    port_details_label = port_details_data.get("label", "Port Details")
    
    # Convert port details to DataTable format
    port_details_table_data = [{"Measure": row[0], port_details_label: row[1]} for row in port_details_rows]
    producers_sellers = load_producers_sellers()
    
    # CREATE GRAPHS WITH FIXED SIZES (no autosize)
    production_graph = create_production_chart()
    map_graph = create_map_chart()
    
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
                
                /* Refined Products table wrapper height control */
                #refined-products-table-wrapper {
                    max-height: 1360px !important;
                    overflow-y: auto !important;
                    overflow-x: auto !important;
                }
                
                #refined-products-table-wrapper .dash-table-container {
                    max-height: 100% !important;
                    overflow: hidden !important; /* Let the wrapper handle the scroll */
                }
                
                #refined-products-table-wrapper .dash-spreadsheet-container {
                    max-height: 100% !important;
                    overflow: hidden !important; /* Let the wrapper handle the scroll */
                }
                
                /* Sort indicator icon styles for ALL headers */
                /* Positioned inline with A/Z - arrow on right, A/Z on left */
                .sort-indicator {
                    position: absolute;
                    right: 8px;
                    top: 50%;
                    transform: translateY(-50%);
                    width: 15px;
                    height: 15px;
                    cursor: pointer;
                    opacity: 0;
                    transition: opacity 0.2s ease;
                    z-index: 11;
                }
                .dash-header:hover .sort-indicator {
                    opacity: 1;
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
                /* A/Z sort order container styles - HIDDEN BY DEFAULT, SHOW ON HOVER */
                /* Positioned inline with down arrow - A/Z on left, arrow on right */
                .sort-order-container {
                    position: absolute;
                    right: 28px;
                    top: 50%;
                    transform: translateY(-50%);
                    font-size: 10px;
                    color: #666;
                    cursor: pointer;
                    padding: 2px 4px;
                    border: 1px solid transparent;
                    border-radius: 2px;
                    line-height: 1;
                    text-align: center;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 30px;
                    width: 16px;
                    opacity: 0 !important;
                    visibility: hidden !important;
                    transition: opacity 0.2s ease, visibility 0.2s ease;
                    z-index: 10;
                    pointer-events: none;
                }
                /* Specific rules for both tables - A/Z HIDDEN BY DEFAULT, SHOW ON HOVER */
                #assay-table .dash-header .sort-order-container,
                #refined-products-table .dash-header .sort-order-container {
                    opacity: 0 !important;
                    visibility: hidden !important;
                    pointer-events: none;
                }
                #assay-table .dash-header:hover .sort-order-container,
                #refined-products-table .dash-header:hover .sort-order-container {
                    opacity: 1 !important;
                    visibility: visible !important;
                    pointer-events: auto;
                }
                .sort-order-container:hover {
                    background-color: #e6f3ff;
                    border-color: #1f3263;
                }
                .sort-asc, .sort-desc {
                    display: block;
                    line-height: 1.2;
                    cursor: pointer;
                    padding: 2px 4px;
                    border-radius: 2px;
                    font-size: 11px;
                    font-weight: bold;
                    text-align: center;
                    width: 100%;
                    min-width: 16px;
                }
                .sort-asc {
                    margin-bottom: 2px;
                }
                .sort-desc {
                    margin-top: 2px;
                }
                .sort-asc:hover, .sort-desc:hover {
                    background-color: #d4e7ff;
                    font-weight: bold;
                }
                
                /* Popup menu styles */
                .assay-popup-menu {
                    position: absolute;
                    background-color: white;
                    padding: 4px 0;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    z-index: 1000;
                    min-width: 160px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
                
                .refined-popup-menu {
                    position: absolute;
                    background-color: white;
                    padding: 4px 0;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    z-index: 1000;
                    min-width: 160px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
                
                .port-popup-menu {
                    position: absolute;
                    background-color: white;
                    padding: 4px 0;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    z-index: 1000;
                    min-width: 160px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
                
                .quality-specs-popup {
                    position: absolute;
                    background: white;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    padding: 12px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    z-index: 1000;
                    min-width: 200px;
                    font-family: Arial, sans-serif;
                }
                .quality-specs-popup h4 {
                    margin: 0 0 8px 0;
                    color: #d65a00;
                    font-size: 13px;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 4px;
                }
                .quality-specs-popup .spec-item {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 4px;
                    font-size: 12px;
                }
                .quality-specs-popup .spec-label {
                    color: #666;
                    font-weight: normal;
                }
                .quality-specs-popup .spec-value {
                    color: #333;
                    font-weight: bold;
                }
                .quality-specs-hover-area {
                    cursor: pointer;
                    position: relative;
                    border-radius: 3px;
                    transition: background-color 0.2s ease;
                }
                .quality-specs-hover-area:hover {
                    background-color: #f5f5f5;
                }
                
                .popup-menu-item {
                    padding: 6px 10px;
                    font-size: 12px;
                    cursor: pointer;
                    font-family: Arial;
                    color: #333;
                    border: none;
                    background: none;
                    width: 100%;
                    text-align: left;
                }
                
                .popup-menu-item:hover {
                    background-color: #f5f5f5;
                }
                </style>
            """, dangerously_allow_html=True)
        ]),
        
        # Hidden components for interactivity - MARS BLEND ASSAY TABLE
        html.Button("Assay Property Sort Asc", id="assay-property-sort-asc-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Assay Property Sort Desc", id="assay-property-sort-desc-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Assay Unit Sort Asc", id="assay-unit-sort-asc-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Assay Unit Sort Desc", id="assay-unit-sort-desc-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Assay Property Popup Menu Click", id="assay-property-popup-menu-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Assay Unit Popup Menu Click", id="assay-unit-popup-menu-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Assay Property Popup Source Click", id="assay-property-popup-source-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Assay Property Popup Alphabetic Click", id="assay-property-popup-alphabetic-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Assay Property Popup Field Click", id="assay-property-popup-field-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Assay Property Popup Nested Click", id="assay-property-popup-nested-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Assay Property Field Arrow Click", id="assay-property-field-arrow-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Assay Property Nested Arrow Click", id="assay-property-nested-arrow-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Assay Unit Popup Source Click", id="assay-unit-popup-source-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Assay Unit Popup Alphabetic Click", id="assay-unit-popup-alphabetic-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Assay Unit Popup Field Click", id="assay-unit-popup-field-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Assay Unit Popup Nested Click", id="assay-unit-popup-nested-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Assay Unit Field Arrow Click", id="assay-unit-field-arrow-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Assay Unit Nested Arrow Click", id="assay-unit-nested-arrow-btn", n_clicks=0, style={"display": "none"}),
        
        # Hidden components for interactivity - REFINED PRODUCTS TABLE
        html.Button("Refined Product Sort Asc", id="refined-product-sort-asc-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Product Sort Desc", id="refined-product-sort-desc-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Cut Points Sort Asc", id="refined-cutpoints-sort-asc-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Cut Points Sort Desc", id="refined-cutpoints-sort-desc-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Property Sort Asc", id="refined-property-sort-asc-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Property Sort Desc", id="refined-property-sort-desc-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Unit Sort Asc", id="refined-unit-sort-asc-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Unit Sort Desc", id="refined-unit-sort-desc-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Product Popup Menu Click", id="refined-product-popup-menu-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Cut Points Popup Menu Click", id="refined-cutpoints-popup-menu-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Property Popup Menu Click", id="refined-property-popup-menu-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Unit Popup Menu Click", id="refined-unit-popup-menu-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Product Popup Source Click", id="refined-product-popup-source-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Product Popup Alphabetic Click", id="refined-product-popup-alphabetic-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Product Popup Field Click", id="refined-product-popup-field-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Product Popup Nested Click", id="refined-product-popup-nested-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Product Field Arrow Click", id="refined-product-field-arrow-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Product Nested Arrow Click", id="refined-product-nested-arrow-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Cut Points Popup Source Click", id="refined-cutpoints-popup-source-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Cut Points Popup Alphabetic Click", id="refined-cutpoints-popup-alphabetic-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Cut Points Popup Field Click", id="refined-cutpoints-popup-field-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Cut Points Popup Nested Click", id="refined-cutpoints-popup-nested-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Cut Points Field Arrow Click", id="refined-cutpoints-field-arrow-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Cut Points Nested Arrow Click", id="refined-cutpoints-nested-arrow-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Property Popup Source Click", id="refined-property-popup-source-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Property Popup Alphabetic Click", id="refined-property-popup-alphabetic-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Property Popup Field Click", id="refined-property-popup-field-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Property Popup Nested Click", id="refined-property-popup-nested-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Property Field Arrow Click", id="refined-property-field-arrow-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Property Nested Arrow Click", id="refined-property-nested-arrow-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Unit Popup Source Click", id="refined-unit-popup-source-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Unit Popup Alphabetic Click", id="refined-unit-popup-alphabetic-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Unit Popup Field Click", id="refined-unit-popup-field-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Unit Popup Nested Click", id="refined-unit-popup-nested-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Unit Field Arrow Click", id="refined-unit-field-arrow-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Refined Unit Nested Arrow Click", id="refined-unit-nested-arrow-btn", n_clicks=0, style={"display": "none"}),
        
        # Hidden components for Port Details table
        html.Button("Port Measure Sort Asc", id="port-measure-sort-asc-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Port Measure Sort Desc", id="port-measure-sort-desc-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Port Measure Popup Menu Click", id="port-measure-popup-menu-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Port Measure Popup Source Click", id="port-measure-popup-source-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Port Measure Popup Alphabetic Click", id="port-measure-popup-alphabetic-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Port Measure Popup Field Click", id="port-measure-popup-field-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Port Measure Popup Nested Click", id="port-measure-popup-nested-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Port Measure Field Arrow Click", id="port-measure-field-arrow-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Port Measure Nested Arrow Click", id="port-measure-nested-arrow-btn", n_clicks=0, style={"display": "none"}),
        
        # Hidden components for Quality Specs Popup
        html.Button("Show Quality Specs Popup", id="show-quality-specs-popup-btn", n_clicks=0, style={"display": "none"}),
        html.Button("Hide Quality Specs Popup", id="hide-quality-specs-popup-btn", n_clicks=0, style={"display": "none"}),
        
        # Popup menus for Mars Blend Assay table - SEPARATE CLASS NAMES
        html.Div([
            html.Div("Data source order", className="popup-menu-item assay-property-popup-source-item", 
                    style={
                        "padding": "6px 10px", 
                        "fontSize": "12px",
                        "cursor": "pointer",
                        "fontFamily": "Arial",
                        "color": "#333",
                    }),
            html.Div("Alphabetic", className="popup-menu-item assay-property-popup-alphabetic-item",
                    style={
                        "padding": "6px 10px", 
                        "fontSize": "12px",
                        "cursor": "pointer",
                        "fontFamily": "Arial",
                        "color": "#333",
                    }),
            html.Div([
                html.Span("Field", style={"flex": "1"}),
                html.Span("▶", className="assay-property-field-arrow-item", style={
                    "cursor": "pointer",
                    "fontSize": "10px",
                    "color": "#666",
                    "marginLeft": "8px",
                }),
            ], className="popup-menu-item assay-property-popup-field-item",
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
               }),
            html.Div([
                html.Span("Nested", style={"flex": "1"}),
                html.Span("▶", className="assay-property-nested-arrow-item", style={
                    "cursor": "pointer",
                    "fontSize": "10px",
                    "color": "#666",
                    "marginLeft": "8px",
                }),
            ], className="popup-menu-item assay-property-popup-nested-item",
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
               }),
        ], id="assay-property-sorting-controls", className="assay-popup-menu", style={
            "display": "none",
        }),
        
        html.Div([
            html.Div("Data source order", className="popup-menu-item assay-unit-popup-source-item", 
                    style={
                        "padding": "6px 10px", 
                        "fontSize": "12px",
                        "cursor": "pointer",
                        "fontFamily": "Arial",
                        "color": "#333",
                    }),
            html.Div("Alphabetic", className="popup-menu-item assay-unit-popup-alphabetic-item",
                    style={
                        "padding": "6px 10px", 
                        "fontSize": "12px",
                        "cursor": "pointer",
                        "fontFamily": "Arial",
                        "color": "#333",
                    }),
            html.Div([
                html.Span("Field", style={"flex": "1"}),
                html.Span("▶", className="assay-unit-field-arrow-item", style={
                    "cursor": "pointer",
                    "fontSize": "10px",
                    "color": "#666",
                    "marginLeft": "8px",
                }),
            ], className="popup-menu-item assay-unit-popup-field-item",
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
               }),
            html.Div([
                html.Span("Nested", style={"flex": "1"}),
                html.Span("▶", className="assay-unit-nested-arrow-item", style={
                    "cursor": "pointer",
                    "fontSize": "10px",
                    "color": "#666",
                    "marginLeft": "8px",
                }),
            ], className="popup-menu-item assay-unit-popup-nested-item",
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
               }),
        ], id="assay-unit-sorting-controls", className="assay-popup-menu", style={
            "display": "none",
        }),
        
        # Popup menus for Refined Products table - SEPARATE CLASS NAMES
        html.Div([
            html.Div("Data source order", className="popup-menu-item refined-product-popup-source-item", 
                    style={
                        "padding": "6px 10px", 
                        "fontSize": "12px",
                        "cursor": "pointer",
                        "fontFamily": "Arial",
                        "color": "#333",
                    }),
            html.Div("Alphabetic", className="popup-menu-item refined-product-popup-alphabetic-item",
                    style={
                        "padding": "6px 10px", 
                        "fontSize": "12px",
                        "cursor": "pointer",
                        "fontFamily": "Arial",
                        "color": "#333",
                    }),
            html.Div([
                html.Span("Field", style={"flex": "1"}),
                html.Span("▶", className="refined-product-field-arrow-item", style={
                    "cursor": "pointer",
                    "fontSize": "10px",
                    "color": "#666",
                    "marginLeft": "8px",
                }),
            ], className="popup-menu-item refined-product-popup-field-item",
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
               }),
            html.Div([
                html.Span("Nested", style={"flex": "1"}),
                html.Span("▶", className="refined-product-nested-arrow-item", style={
                    "cursor": "pointer",
                    "fontSize": "10px",
                    "color": "#666",
                    "marginLeft": "8px",
                }),
            ], className="popup-menu-item refined-product-popup-nested-item",
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
               }),
        ], id="refined-product-sorting-controls", className="refined-popup-menu", style={
            "display": "none",
            "top": "1075px",
            "left": "714px",
        }),
        
        html.Div([
            html.Div("Data source order", className="popup-menu-item refined-cutpoints-popup-source-item", 
                    style={
                        "padding": "6px 10px", 
                        "fontSize": "12px",
                        "cursor": "pointer",
                        "fontFamily": "Arial",
                        "color": "#333",
                    }),
            html.Div("Alphabetic", className="popup-menu-item refined-cutpoints-popup-alphabetic-item",
                    style={
                        "padding": "6px 10px", 
                        "fontSize": "12px",
                        "cursor": "pointer",
                        "fontFamily": "Arial",
                        "color": "#333",
                    }),
            html.Div([
                html.Span("Field", style={"flex": "1"}),
                html.Span("▶", className="refined-cutpoints-field-arrow-item", style={
                    "cursor": "pointer",
                    "fontSize": "10px",
                    "color": "#666",
                    "marginLeft": "8px",
                }),
            ], className="popup-menu-item refined-cutpoints-popup-field-item",
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
               }),
            html.Div([
                html.Span("Nested", style={"flex": "1"}),
                html.Span("▶", className="refined-cutpoints-nested-arrow-item", style={
                    "cursor": "pointer",
                    "fontSize": "10px",
                    "color": "#666",
                    "marginLeft": "8px",
                }),
            ], className="popup-menu-item refined-cutpoints-popup-nested-item",
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
               }),
        ], id="refined-cutpoints-sorting-controls", className="refined-popup-menu", style={
            "display": "none",
            "top": "1075px",
            "left": "818px",
        }),
        
        html.Div([
            html.Div("Data source order", className="popup-menu-item refined-property-popup-source-item", 
                    style={
                        "padding": "6px 10px", 
                        "fontSize": "12px",
                        "cursor": "pointer",
                        "fontFamily": "Arial",
                        "color": "#333",
                    }),
            html.Div("Alphabetic", className="popup-menu-item refined-property-popup-alphabetic-item",
                    style={
                        "padding": "6px 10px", 
                        "fontSize": "12px",
                        "cursor": "pointer",
                        "fontFamily": "Arial",
                        "color": "#333",
                    }),
            html.Div([
                html.Span("Field", style={"flex": "1"}),
                html.Span("▶", className="refined-property-field-arrow-item", style={
                    "cursor": "pointer",
                    "fontSize": "10px",
                    "color": "#666",
                    "marginLeft": "8px",
                }),
            ], className="popup-menu-item refined-property-popup-field-item",
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
               }),
            html.Div([
                html.Span("Nested", style={"flex": "1"}),
                html.Span("▶", className="refined-property-nested-arrow-item", style={
                    "cursor": "pointer",
                    "fontSize": "10px",
                    "color": "#666",
                    "marginLeft": "8px",
                }),
            ], className="popup-menu-item refined-property-popup-nested-item",
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
               }),
        ], id="refined-property-sorting-controls", className="refined-popup-menu", style={
            "display": "none",
            "left": "869px",
        }),
        
        html.Div([
            html.Div("Data source order", className="popup-menu-item refined-unit-popup-source-item", 
                    style={
                        "padding": "6px 10px", 
                        "fontSize": "12px",
                        "cursor": "pointer",
                        "fontFamily": "Arial",
                        "color": "#333",
                    }),
            html.Div("Alphabetic", className="popup-menu-item refined-unit-popup-alphabetic-item",
                    style={
                        "padding": "6px 10px", 
                        "fontSize": "12px",
                        "cursor": "pointer",
                        "fontFamily": "Arial",
                        "color": "#333",
                    }),
            html.Div([
                html.Span("Field", style={"flex": "1"}),
                html.Span("▶", className="refined-unit-field-arrow-item", style={
                    "cursor": "pointer",
                    "fontSize": "10px",
                    "color": "#666",
                    "marginLeft": "8px",
                }),
            ], className="popup-menu-item refined-unit-popup-field-item",
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
               }),
            html.Div([
                html.Span("Nested", style={"flex": "1"}),
                html.Span("▶", className="refined-unit-nested-arrow-item", style={
                    "cursor": "pointer",
                    "fontSize": "10px",
                    "color": "#666",
                    "marginLeft": "8px",
                }),
            ], className="popup-menu-item refined-unit-popup-nested-item",
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
               }),
        ], id="refined-unit-sorting-controls", className="refined-popup-menu", style={
            "display": "none",
            "left": "943px",
        }),
        
        # Popup menus for Port Details table
        html.Div([
            html.Div("Data source order", className="popup-menu-item port-measure-popup-source-item", 
                    style={
                        "padding": "6px 10px", 
                        "fontSize": "12px",
                        "cursor": "pointer",
                        "fontFamily": "Arial",
                        "color": "#333",
                    }),
            html.Div("Alphabetic", className="popup-menu-item port-measure-popup-alphabetic-item",
                    style={
                        "padding": "6px 10px", 
                        "fontSize": "12px",
                        "cursor": "pointer",
                        "fontFamily": "Arial",
                        "color": "#333",
                    }),
            html.Div([
                html.Span("Field", style={"flex": "1"}),
                html.Span("▶", className="port-measure-field-arrow-item", style={
                    "cursor": "pointer",
                    "fontSize": "10px",
                    "color": "#666",
                    "marginLeft": "8px",
                }),
            ], className="popup-menu-item port-measure-popup-field-item",
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
               }),
            html.Div([
                html.Span("Nested", style={"flex": "1"}),
                html.Span("▶", className="port-measure-nested-arrow-item", style={
                    "cursor": "pointer",
                    "fontSize": "10px",
                    "color": "#666",
                    "marginLeft": "8px",
                }),
            ], className="popup-menu-item port-measure-popup-nested-item",
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
               }),
        ], id="port-measure-sorting-controls", className="port-popup-menu", style={
            "display": "none",
        }),
        
        # Quality Specs Popup
        html.Div(
            id="quality-specs-popup",
            className="quality-specs-popup",
            style={
                "display": "none",
                "position": "absolute",
                "top": "200px",
                "left": "900px"
            },
            children=[
                html.H4("Latest Quality Specs"),
                html.Div([
                    html.Div([
                        html.Span("Carbon Intensity:", className="spec-label"),
                        html.Span("Low", className="spec-value")
                    ], className="spec-item"),
                    html.Div([
                        html.Span("Gravity (API at 60F):", className="spec-label"),
                        html.Span(quality_specs[0][1] if len(quality_specs) > 0 else "28.40", className="spec-value")
                    ], className="spec-item"),
                    html.Div([
                        html.Span("Sulfur Content (% Wt):", className="spec-label"),
                        html.Span(quality_specs[1][1] if len(quality_specs) > 1 else "2.17", className="spec-value")
                    ], className="spec-item"),
                    html.Div([
                        html.Span("TAN (mg KOH/g):", className="spec-label"),
                        html.Span(quality_specs[2][1] if len(quality_specs) > 2 else "0.48", className="spec-value")
                    ], className="spec-item")
                ])
            ]
        ),
        
        # Store components for both tables - COMPLETELY SEPARATE
        dcc.Store(id='assay-current-sort-order', data={'column': None, 'type': 'source', 'direction': 'asc'}),
        dcc.Store(id='assay-show-sorting-controls', data={'header': None}),
        dcc.Store(id='assay-original-data', data=assay_data),
        
        dcc.Store(id='refined-current-sort-order', data={'column': None, 'type': 'source', 'direction': 'asc'}),
        dcc.Store(id='refined-show-sorting-controls', data={'header': None}),
        dcc.Store(id='refined-original-data', data=refined_products_data),
        
        dcc.Store(id='port-current-sort-order', data={'column': None, 'type': 'source', 'direction': 'asc'}),
        dcc.Store(id='port-show-sorting-controls', data={'header': None}),
        dcc.Store(id='port-original-data', data=port_details_table_data),
        
        dcc.Store(id='quality-specs-data', data=quality_specs),
        
        html.Div(id='assay-dummy-output', style={'display': 'none'}),
        html.Div(id='assay-dummy-output-2', style={'display': 'none'}),
        html.Div(id='refined-dummy-output', style={'display': 'none'}),
        html.Div(id='refined-dummy-output-2', style={'display': 'none'}),
        html.Div(id='port-dummy-output', style={'display': 'none'}),
        html.Div(id='port-dummy-output-2', style={'display': 'none'}),
        html.Div(id='port-dummy-output-3', style={'display': 'none'}),
        html.Div(id='quality-specs-dummy-output', style={'display': 'none'}),
        
        # AVG(Value) Text Box for Mars Blend Assay (initially hidden, shows on hover over Field/Nested)
        html.Div(
            "AVG(Value)",
            id="assay-avg-text-box",
            n_clicks=0,
            style={
                "position": "absolute",
                "backgroundColor": "white",
                "border": "1px solid #ccc",
                "padding": "8px 12px",
                "borderRadius": "4px",
                "fontSize": "12px",
                "fontFamily": "Arial",
                "boxShadow": "0 2px 5px rgba(0,0,0,0.1)",
                "zIndex": "1002",
                "display": "none",
                "color": "#333",
                "cursor": "pointer",
                "left": "256px",
            }
        ),
        
        # AVG(Value) Text Box for Refined Products (initially hidden, shows on hover over Field/Nested)
        html.Div(
            "AVG(Value)",
            id="refined-avg-text-box",
            n_clicks=0,
            style={
                "position": "absolute",
                "backgroundColor": "white",
                "border": "1px solid #ccc",
                "padding": "8px 12px",
                "borderRadius": "4px",
                "fontSize": "12px",
                "fontFamily": "Arial",
                "boxShadow": "0 2px 5px rgba(0,0,0,0.1)",
                "zIndex": "1002",
                "display": "none",
                "color": "#333",
                "cursor": "pointer",
                "left": "900px",
            }
        ),
        
        # AVG(Value) Text Box for Port Details (initially hidden, shows on hover over Field/Nested)
        html.Div(
            "AVG(Value)",
            id="port-avg-text-box",
            n_clicks=0,
            style={
                "position": "absolute",
                "backgroundColor": "white",
                "border": "1px solid #ccc",
                "padding": "8px 12px",
                "borderRadius": "4px",
                "fontSize": "12px",
                "fontFamily": "Arial",
                "boxShadow": "0 2px 5px rgba(0,0,0,0.1)",
                "zIndex": "1002",
                "display": "none",
                "color": "#333",
                "cursor": "pointer",
            }
        ),
        
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
            
            # Right: Latest Quality Specs with Hover Popup
            html.Div(style={
                "flex": "1",
                "minWidth": "350px",
                "position": "relative"
            }, children=[
                html.Div(
                    "Latest Quality Specs", 
                    style={
                        "color": "#d65a00",
                        "fontWeight": "bold",
                        "fontSize": "15px",
                        "marginBottom": "12px",
                        "borderBottom": "2px solid #d65a00",
                        "paddingBottom": "5px"
                    }
                ),
                
                # Headers row with hover area
                html.Div(
                    className="quality-specs-hover-area",
                    id="quality-specs-hover-trigger",
                    style={
                        "display": "flex",
                        "gap": "15px",
                        "marginBottom": "8px",
                        "padding": "5px",
                        "borderRadius": "3px"
                    },
                    children=[
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
                    ]
                ),
                
                # Values row with hover area
                html.Div(
                    className="quality-specs-hover-area",
                    style={
                        "display": "flex",
                        "gap": "15px",
                        "padding": "5px",
                        "borderRadius": "3px"
                    },
                    children=[
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
                    ]
                )
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
                create_assay_table()
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
                html.Div(
                    id="refined-products-table-wrapper",
                    style={
                        "maxHeight": "1360px",
                        "overflowY": "auto",
                        "overflowX": "auto",
                        "border": "1px solid #d9d9d9",
                        "backgroundColor": "white",
                        "position": "relative",
                    },
                    children=[
                        create_refined_products_table()
                    ]
                )
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
                    "backgroundColor": "white",
                    # ADD FIXED CONTAINER SIZE
                    "width": "100%",
                    "height": "400px",
                    "overflow": "hidden"
                }, children=[
                    production_graph
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
                    "backgroundColor": "white",
                    # ADD FIXED CONTAINER SIZE
                    "width": "100%",
                    "height": "500px",
                    "overflow": "hidden"
                }, children=[
                    map_graph
                ]),
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
                }),
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
                    css=[{
                        "selector": ".dash-header[data-dash-column='Measure']",
                        "rule": "position: relative;"
                    },
                    {
                        "selector": ".dash-header[data-dash-column='Measure'] .sort-order-container",
                        "rule": "display: flex; flex-direction: column; position: absolute; right: 30px; top: 50%; transform: translateY(-50%); opacity: 0 !important; visibility: hidden !important; pointer-events: none; transition: opacity 0.2s ease, visibility 0.2s ease;"
                    },
                    {
                        "selector": ".dash-header[data-dash-column='Measure'] .sort-indicator",
                        "rule": "position: absolute; right: 5px; top: 50%; transform: translateY(-50%); opacity: 0; transition: opacity 0.2s; cursor: pointer; width: 16px; height: 16px;"
                    },
                    {
                        "selector": ".dash-header[data-dash-column='Measure']:hover .sort-order-container",
                        "rule": "opacity: 1 !important; visibility: visible !important; pointer-events: auto;"
                    },
                    {
                        "selector": ".dash-header[data-dash-column='Measure']:hover .sort-indicator",
                        "rule": "opacity: 1 !important;"
                    },
                    {
                        "selector": ".dash-header[data-dash-column='Measure'] .sort-asc, .dash-header[data-dash-column='Measure'] .sort-desc",
                        "rule": "display: block; cursor: pointer; padding: 2px 4px; font-size: 11px; font-weight: bold; color: #333; line-height: 1.2; text-align: center; width: 100%; min-width: 16px;"
                    },
                    {
                        "selector": ".dash-header[data-dash-column='Measure'] .sort-asc",
                        "rule": "margin-bottom: 2px;"
                    },
                    {
                        "selector": ".dash-header[data-dash-column='Measure'] .sort-desc",
                        "rule": "margin-top: 2px;"
                    },
                    {
                        "selector": ".dash-header[data-dash-column='Measure'] .sort-asc:hover, .dash-header[data-dash-column='Measure'] .sort-desc:hover",
                        "rule": "background-color: #d4e7ff; font-weight: bold;"
                    }]
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
# CALLBACKS - COMPLETELY SEPARATE FOR BOTH TABLES
# ------------------------------------------------------------------------------
def register_callbacks(app):
    """Register callbacks for the dashboard with Latest Quality Specs hover popup"""
    
    # ==========================================================================
    # QUALITY SPECS POPUP CALLBACKS
    # ==========================================================================
    
    @app.callback(
        [Output("quality-specs-popup", "style"),
         Output("quality-specs-popup", "children")],
        [Input("show-quality-specs-popup-btn", "n_clicks"),
         Input("hide-quality-specs-popup-btn", "n_clicks")],
        [State("quality-specs-popup", "style"),
         State('quality-specs-data', 'data')],
        prevent_initial_call=True
    )
    def handle_quality_specs_popup(show_clicks, hide_clicks, current_style, quality_specs_data):
        trigger = ctx.triggered_id
        
        if trigger == "show-quality-specs-popup-btn":
            # Update popup content with current data
            popup_content = [
                html.H4("Latest Quality Specs"),
                html.Div([
                    html.Div([
                        html.Span("Carbon Intensity:", className="spec-label"),
                        html.Span("Low", className="spec-value")
                    ], className="spec-item"),
                    html.Div([
                        html.Span("Gravity (API at 60F):", className="spec-label"),
                        html.Span(quality_specs_data[0][1] if quality_specs_data and len(quality_specs_data) > 0 else "28.40", className="spec-value")
                    ], className="spec-item"),
                    html.Div([
                        html.Span("Sulfur Content (% Wt):", className="spec-label"),
                        html.Span(quality_specs_data[1][1] if quality_specs_data and len(quality_specs_data) > 1 else "2.17", className="spec-value")
                    ], className="spec-item"),
                    html.Div([
                        html.Span("TAN (mg KOH/g):", className="spec-label"),
                        html.Span(quality_specs_data[2][1] if quality_specs_data and len(quality_specs_data) > 2 else "0.48", className="spec-value")
                    ], className="spec-item")
                ])
            ]
            
            new_style = current_style.copy() if current_style else {}
            new_style.update({
                "display": "block",
                "position": "absolute",
                "top": "200px",
                "left": "900px",
                "background": "white",
                "border": "1px solid #ddd",
                "borderRadius": "4px",
                "padding": "12px",
                "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                "zIndex": "1000",
                "minWidth": "200px"
            })
            return new_style, popup_content
        
        elif trigger == "hide-quality-specs-popup-btn":
            new_style = current_style.copy() if current_style else {}
            new_style["display"] = "none"
            return new_style, no_update
        
        return no_update, no_update

    # ==========================================================================
    # MARS BLEND ASSAY TABLE CALLBACKS - ONLY HANDLES ASSAY TABLE
    # ==========================================================================
    
    @app.callback(
        [Output("assay-property-sorting-controls", "style"),
         Output("assay-unit-sorting-controls", "style"),
         Output('assay-current-sort-order', 'data', allow_duplicate=True),
         Output('assay-show-sorting-controls', 'data', allow_duplicate=True)],
        [Input('assay-property-popup-menu-btn', 'n_clicks'),
         Input('assay-unit-popup-menu-btn', 'n_clicks'),
         Input('assay-property-popup-source-btn', 'n_clicks'),
         Input('assay-property-popup-alphabetic-btn', 'n_clicks'),
         Input('assay-unit-popup-source-btn', 'n_clicks'),
         Input('assay-unit-popup-alphabetic-btn', 'n_clicks'),
         Input('assay-property-sort-asc-btn', 'n_clicks'),
         Input('assay-property-sort-desc-btn', 'n_clicks'),
         Input('assay-unit-sort-asc-btn', 'n_clicks'),
         Input('assay-unit-sort-desc-btn', 'n_clicks')],
        [State('assay-show-sorting-controls', 'data'),
         State('assay-current-sort-order', 'data')],
        prevent_initial_call=True
    )
    def handle_assay_sorting_interactions(prop_popup_clicks, unit_popup_clicks,
                                        prop_source_clicks, prop_alpha_clicks,
                                        unit_source_clicks, unit_alpha_clicks,
                                        prop_asc_clicks, prop_desc_clicks,
                                        unit_asc_clicks, unit_desc_clicks,
                                        show_controls, current_sort):
        trigger = ctx.triggered_id
        
        # Default popup styles
        property_popup_style = {"display": "none"}
        unit_popup_style = {"display": "none"}
        
        # Handle popup menu visibility - ONLY FOR ASSAY TABLE
        if trigger == 'assay-property-popup-menu-btn':
            current_header = show_controls.get('header') if show_controls else None
            if current_header == 'Property':
                return property_popup_style, unit_popup_style, no_update, {'header': None}
            else:
                property_style = {
                    "position": "absolute",
                    "backgroundColor": "white",
                    "padding": "4px 0",
                    "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                    "zIndex": "1000",
                    "display": "block",
                    "minWidth": "160px"
                }
                return property_style, unit_popup_style, no_update, {'header': 'Property'}
        
        elif trigger == 'assay-unit-popup-menu-btn':
            current_header = show_controls.get('header') if show_controls else None
            if current_header == 'Unit':
                return property_popup_style, unit_popup_style, no_update, {'header': None}
            else:
                unit_style = {
                    "position": "absolute",
                    "backgroundColor": "white",
                    "padding": "4px 0",
                    "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                    "zIndex": "1000",
                    "display": "block",
                    "minWidth": "160px"
                }
                return property_popup_style, unit_style, no_update, {'header': 'Unit'}
        
        # Handle sort order changes (close popup) - ONLY FOR ASSAY TABLE
        elif trigger in ['assay-property-popup-source-btn', 'assay-property-popup-alphabetic-btn',
                        'assay-unit-popup-source-btn', 'assay-unit-popup-alphabetic-btn',
                        'assay-property-sort-asc-btn', 'assay-property-sort-desc-btn',
                        'assay-unit-sort-asc-btn', 'assay-unit-sort-desc-btn']:
            
            # Close all assay popups
            popup_style = {"display": "none"}
            
            # Update sort order based on trigger - ONLY FOR ASSAY TABLE
            if trigger == 'assay-property-popup-source-btn':
                return popup_style, popup_style, {'column': 'Property', 'type': 'source', 'direction': 'asc'}, {'header': None}
            elif trigger == 'assay-property-popup-alphabetic-btn':
                return popup_style, popup_style, {'column': 'Property', 'type': 'alphabetic', 'direction': 'asc'}, {'header': None}
            elif trigger == 'assay-property-sort-asc-btn':
                return popup_style, popup_style, {'column': 'Property', 'type': 'alphabetic', 'direction': 'asc'}, {'header': None}
            elif trigger == 'assay-property-sort-desc-btn':
                return popup_style, popup_style, {'column': 'Property', 'type': 'alphabetic', 'direction': 'desc'}, {'header': None}
            elif trigger == 'assay-unit-popup-source-btn':
                return popup_style, popup_style, {'column': 'Unit', 'type': 'source', 'direction': 'asc'}, {'header': None}
            elif trigger == 'assay-unit-popup-alphabetic-btn':
                return popup_style, popup_style, {'column': 'Unit', 'type': 'alphabetic', 'direction': 'asc'}, {'header': None}
            elif trigger == 'assay-unit-sort-asc-btn':
                return popup_style, popup_style, {'column': 'Unit', 'type': 'alphabetic', 'direction': 'asc'}, {'header': None}
            elif trigger == 'assay-unit-sort-desc-btn':
                return popup_style, popup_style, {'column': 'Unit', 'type': 'alphabetic', 'direction': 'desc'}, {'header': None}
        
        return no_update, no_update, no_update, no_update

    # Apply sorting to assay table data
    @app.callback(
        Output('assay-table', 'data', allow_duplicate=True),
        Input('assay-current-sort-order', 'data'),
        State('assay-original-data', 'data'),
        prevent_initial_call=True
    )
    def apply_assay_sort_order(current_sort, original_data):
        if not original_data or not current_sort:
            return no_update
            
        sort_type = current_sort.get('type', 'source')
        direction = current_sort.get('direction', 'asc')
        column = current_sort.get('column')
        
        if sort_type == 'source':
            # Return original data order
            return original_data
        elif sort_type == 'alphabetic':
            if column in ['Property', 'Unit']:
                return sort_assay_data_alphabetically(original_data, column, direction)
            else:
                return original_data
        else:
            return original_data

    # ==========================================================================
    # REFINED PRODUCTS TABLE CALLBACKS - ONLY HANDLES REFINED TABLE
    # ==========================================================================
    
    @app.callback(
        [Output('refined-product-sorting-controls', 'style'),
         Output('refined-cutpoints-sorting-controls', 'style'),
         Output('refined-property-sorting-controls', 'style'),
         Output('refined-unit-sorting-controls', 'style'),
         Output('refined-current-sort-order', 'data', allow_duplicate=True),
         Output('refined-show-sorting-controls', 'data', allow_duplicate=True)],
        [Input('refined-product-popup-menu-btn', 'n_clicks'),
         Input('refined-cutpoints-popup-menu-btn', 'n_clicks'),
         Input('refined-property-popup-menu-btn', 'n_clicks'),
         Input('refined-unit-popup-menu-btn', 'n_clicks'),
         Input('refined-product-popup-source-btn', 'n_clicks'),
         Input('refined-product-popup-alphabetic-btn', 'n_clicks'),
         Input('refined-cutpoints-popup-source-btn', 'n_clicks'),
         Input('refined-cutpoints-popup-alphabetic-btn', 'n_clicks'),
         Input('refined-property-popup-source-btn', 'n_clicks'),
         Input('refined-property-popup-alphabetic-btn', 'n_clicks'),
         Input('refined-unit-popup-source-btn', 'n_clicks'),
         Input('refined-unit-popup-alphabetic-btn', 'n_clicks'),
         Input('refined-product-sort-asc-btn', 'n_clicks'),
         Input('refined-product-sort-desc-btn', 'n_clicks'),
         Input('refined-cutpoints-sort-asc-btn', 'n_clicks'),
         Input('refined-cutpoints-sort-desc-btn', 'n_clicks'),
         Input('refined-property-sort-asc-btn', 'n_clicks'),
         Input('refined-property-sort-desc-btn', 'n_clicks'),
         Input('refined-unit-sort-asc-btn', 'n_clicks'),
         Input('refined-unit-sort-desc-btn', 'n_clicks')],
        [State('refined-show-sorting-controls', 'data'),
         State('refined-current-sort-order', 'data')],
        prevent_initial_call=True
    )
    def handle_refined_sorting_interactions(product_popup, cutpoints_popup, property_popup, unit_popup,
                                          product_source, product_alpha, cutpoints_source, cutpoints_alpha,
                                          property_source, property_alpha, unit_source, unit_alpha,
                                          product_asc, product_desc, cutpoints_asc, cutpoints_desc,
                                          property_asc, property_desc, unit_asc, unit_desc,
                                          show_controls, current_sort):
        trigger = ctx.triggered_id
        
        # Default popup styles
        product_popup_style = {"display": "none"}
        cutpoints_popup_style = {"display": "none"}
        property_popup_style = {"display": "none"}
        unit_popup_style = {"display": "none"}
        
        # Handle popup menu visibility - ONLY FOR REFINED TABLE
        if trigger == 'refined-product-popup-menu-btn':
            current_header = show_controls.get('header') if show_controls else None
            if current_header == 'Product':
                return product_popup_style, cutpoints_popup_style, property_popup_style, unit_popup_style, no_update, {'header': None}
            else:
                product_style = {
                    "position": "absolute",
                    "backgroundColor": "white",
                    "padding": "4px 0",
                    "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                    "zIndex": "1000",
                    "display": "block",
                    "minWidth": "160px"
                }
                return product_style, cutpoints_popup_style, property_popup_style, unit_popup_style, no_update, {'header': 'Product'}
        
        elif trigger == 'refined-cutpoints-popup-menu-btn':
            current_header = show_controls.get('header') if show_controls else None
            if current_header == 'Cut Points':
                return product_popup_style, cutpoints_popup_style, property_popup_style, unit_popup_style, no_update, {'header': None}
            else:
                cutpoints_style = {
                    "position": "absolute",
                    "backgroundColor": "white",
                    "padding": "4px 0",
                    "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                    "zIndex": "1000",
                    "display": "block",
                    "minWidth": "160px"
                }
                return product_popup_style, cutpoints_style, property_popup_style, unit_popup_style, no_update, {'header': 'Cut Points'}
        
        elif trigger == 'refined-property-popup-menu-btn':
            current_header = show_controls.get('header') if show_controls else None
            if current_header == 'Property':
                return product_popup_style, cutpoints_popup_style, property_popup_style, unit_popup_style, no_update, {'header': None}
            else:
                property_style = {
                    "position": "absolute",
                    "backgroundColor": "white",
                    "padding": "4px 0",
                    "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                    "zIndex": "1000",
                    "display": "block",
                    "minWidth": "160px"
                }
                return product_popup_style, cutpoints_popup_style, property_style, unit_popup_style, no_update, {'header': 'Property'}
        
        elif trigger == 'refined-unit-popup-menu-btn':
            current_header = show_controls.get('header') if show_controls else None
            if current_header == 'Unit':
                return product_popup_style, cutpoints_popup_style, property_popup_style, unit_popup_style, no_update, {'header': None}
            else:
                unit_style = {
                    "position": "absolute",
                    "backgroundColor": "white",
                    "padding": "4px 0",
                    "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                    "zIndex": "1000",
                    "display": "block",
                    "minWidth": "160px"
                }
                return product_popup_style, cutpoints_popup_style, property_popup_style, unit_style, no_update, {'header': 'Unit'}
        
        # Handle sort order changes (close popup) - ONLY FOR REFINED TABLE
        elif trigger in ['refined-product-popup-source-btn', 'refined-product-popup-alphabetic-btn',
                        'refined-cutpoints-popup-source-btn', 'refined-cutpoints-popup-alphabetic-btn',
                        'refined-property-popup-source-btn', 'refined-property-popup-alphabetic-btn',
                        'refined-unit-popup-source-btn', 'refined-unit-popup-alphabetic-btn',
                        'refined-product-sort-asc-btn', 'refined-product-sort-desc-btn',
                        'refined-cutpoints-sort-asc-btn', 'refined-cutpoints-sort-desc-btn',
                        'refined-property-sort-asc-btn', 'refined-property-sort-desc-btn',
                        'refined-unit-sort-asc-btn', 'refined-unit-sort-desc-btn']:
            
            # Close all refined popups
            popup_style = {"display": "none"}
            
            # Update sort order based on trigger - ONLY FOR REFINED TABLE
            if trigger == 'refined-product-popup-source-btn':
                return popup_style, popup_style, popup_style, popup_style, {'column': 'Product', 'type': 'source', 'direction': 'asc'}, {'header': None}
            elif trigger == 'refined-product-popup-alphabetic-btn':
                return popup_style, popup_style, popup_style, popup_style, {'column': 'Product', 'type': 'alphabetic', 'direction': 'asc'}, {'header': None}
            elif trigger == 'refined-product-sort-asc-btn':
                return popup_style, popup_style, popup_style, popup_style, {'column': 'Product', 'type': 'alphabetic', 'direction': 'asc'}, {'header': None}
            elif trigger == 'refined-product-sort-desc-btn':
                return popup_style, popup_style, popup_style, popup_style, {'column': 'Product', 'type': 'alphabetic', 'direction': 'desc'}, {'header': None}
            elif trigger == 'refined-cutpoints-popup-source-btn':
                return popup_style, popup_style, popup_style, popup_style, {'column': 'Cut Points (°C)', 'type': 'source', 'direction': 'asc'}, {'header': None}
            elif trigger == 'refined-cutpoints-popup-alphabetic-btn':
                return popup_style, popup_style, popup_style, popup_style, {'column': 'Cut Points (°C)', 'type': 'alphabetic', 'direction': 'asc'}, {'header': None}
            elif trigger == 'refined-cutpoints-sort-asc-btn':
                return popup_style, popup_style, popup_style, popup_style, {'column': 'Cut Points (°C)', 'type': 'alphabetic', 'direction': 'asc'}, {'header': None}
            elif trigger == 'refined-cutpoints-sort-desc-btn':
                return popup_style, popup_style, popup_style, popup_style, {'column': 'Cut Points (°C)', 'type': 'alphabetic', 'direction': 'desc'}, {'header': None}
            elif trigger == 'refined-property-popup-source-btn':
                return popup_style, popup_style, popup_style, popup_style, {'column': 'Property', 'type': 'source', 'direction': 'asc'}, {'header': None}
            elif trigger == 'refined-property-popup-alphabetic-btn':
                return popup_style, popup_style, popup_style, popup_style, {'column': 'Property', 'type': 'alphabetic', 'direction': 'asc'}, {'header': None}
            elif trigger == 'refined-property-sort-asc-btn':
                return popup_style, popup_style, popup_style, popup_style, {'column': 'Property', 'type': 'alphabetic', 'direction': 'asc'}, {'header': None}
            elif trigger == 'refined-property-sort-desc-btn':
                return popup_style, popup_style, popup_style, popup_style, {'column': 'Property', 'type': 'alphabetic', 'direction': 'desc'}, {'header': None}
            elif trigger == 'refined-unit-popup-source-btn':
                return popup_style, popup_style, popup_style, popup_style, {'column': 'Unit', 'type': 'source', 'direction': 'asc'}, {'header': None}
            elif trigger == 'refined-unit-popup-alphabetic-btn':
                return popup_style, popup_style, popup_style, popup_style, {'column': 'Unit', 'type': 'alphabetic', 'direction': 'asc'}, {'header': None}
            elif trigger == 'refined-unit-sort-asc-btn':
                return popup_style, popup_style, popup_style, popup_style, {'column': 'Unit', 'type': 'alphabetic', 'direction': 'asc'}, {'header': None}
            elif trigger == 'refined-unit-sort-desc-btn':
                return popup_style, popup_style, popup_style, popup_style, {'column': 'Unit', 'type': 'alphabetic', 'direction': 'desc'}, {'header': None}
        
        return no_update, no_update, no_update, no_update, no_update, no_update

    # Apply sorting to refined products table data
    @app.callback(
        Output('refined-products-table', 'data', allow_duplicate=True),
        Input('refined-current-sort-order', 'data'),
        State('refined-original-data', 'data'),
        prevent_initial_call=True
    )
    def apply_refined_sort_order(current_sort, original_data):
        if not original_data or not current_sort:
            return no_update
            
        sort_type = current_sort.get('type', 'source')
        direction = current_sort.get('direction', 'asc')
        column = current_sort.get('column')
        
        if not column:
            return no_update
        
        return sort_refined_products_data(original_data, column, sort_type, direction)

    # Clientside callback to position popup menus below down arrow for Assay table
    app.clientside_callback(
        """
        function(showControls) {
            if (showControls && showControls.header) {
                setTimeout(function() {
                    const headerName = showControls.header;
                    let popup = null;
                    let sortIndicator = null;
                    
                    if (headerName === 'Property') {
                        popup = document.getElementById('assay-property-sorting-controls');
                        const header = document.querySelector('#assay-table .dash-header[data-dash-column="Property"]');
                        if (header) {
                            sortIndicator = header.querySelector('.sort-indicator');
                        }
                    } else if (headerName === 'Unit') {
                        popup = document.getElementById('assay-unit-sorting-controls');
                        const header = document.querySelector('#assay-table .dash-header[data-dash-column="Unit"]');
                        if (header) {
                            sortIndicator = header.querySelector('.sort-indicator');
                        }
                    }
                    
                    if (popup && sortIndicator) {
                        const indicatorRect = sortIndicator.getBoundingClientRect();
                        popup.style.position = 'absolute';
                        popup.style.top = (indicatorRect.bottom + window.scrollY + 5) + 'px';
                        popup.style.left = (indicatorRect.left + window.scrollX - 80) + 'px';
                        popup.style.zIndex = '1000';
                    }
                }, 50);
            }
            return '';
        }
        """,
        Output('assay-dummy-output-2', 'children'),
        Input('assay-show-sorting-controls', 'data'),
        prevent_initial_call=True
    )
    
    # Clientside callback to position popup menus below down arrow for Refined Products table
    app.clientside_callback(
        """
        function(showControls) {
            if (showControls && showControls.header) {
                setTimeout(function() {
                    const headerName = showControls.header;
                    let popup = null;
                    let sortIndicator = null;
                    
                    if (headerName === 'Product') {
                        popup = document.getElementById('refined-product-sorting-controls');
                        const header = document.querySelector('#refined-products-table .dash-header[data-dash-column="Product"]');
                        if (header) {
                            sortIndicator = header.querySelector('.sort-indicator');
                        }
                    } else if (headerName === 'Cut Points') {
                        popup = document.getElementById('refined-cutpoints-sorting-controls');
                        const header = document.querySelector('#refined-products-table .dash-header[data-dash-column="Cut Points (°C)"]');
                        if (header) {
                            sortIndicator = header.querySelector('.sort-indicator');
                        }
                    } else if (headerName === 'Property') {
                        popup = document.getElementById('refined-property-sorting-controls');
                        const header = document.querySelector('#refined-products-table .dash-header[data-dash-column="Property"]');
                        if (header) {
                            sortIndicator = header.querySelector('.sort-indicator');
                        }
                    } else if (headerName === 'Unit') {
                        popup = document.getElementById('refined-unit-sorting-controls');
                        const header = document.querySelector('#refined-products-table .dash-header[data-dash-column="Unit"]');
                        if (header) {
                            sortIndicator = header.querySelector('.sort-indicator');
                        }
                    }
                    
                    if (popup && sortIndicator) {
                        const indicatorRect = sortIndicator.getBoundingClientRect();
                        popup.style.position = 'absolute';
                        popup.style.top = (indicatorRect.bottom + window.scrollY + 5) + 'px';
                        popup.style.left = (indicatorRect.left + window.scrollX - 80) + 'px';
                        popup.style.zIndex = '1000';
                    }
                }, 50);
            }
            return '';
        }
        """,
        Output('refined-dummy-output-2', 'children'),
        Input('refined-show-sorting-controls', 'data'),
        prevent_initial_call=True
    )
    
    # Clientside callback to position popup menu below down arrow for Port Details table
    app.clientside_callback(
        """
        function(showControls) {
            if (showControls && showControls.header) {
                setTimeout(function() {
                    const headerName = showControls.header;
                    let popup = null;
                    let sortIndicator = null;
                    
                    if (headerName === 'Measure') {
                        popup = document.getElementById('port-measure-sorting-controls');
                        const header = document.querySelector('#port-details-table .dash-header[data-dash-column="Measure"]');
                        if (header) {
                            sortIndicator = header.querySelector('.sort-indicator');
                        }
                    }
                    
                    if (popup && sortIndicator) {
                        const indicatorRect = sortIndicator.getBoundingClientRect();
                        popup.style.position = 'absolute';
                        popup.style.top = (indicatorRect.bottom + window.scrollY + 5) + 'px';
                        popup.style.left = (indicatorRect.left + window.scrollX - 80) + 'px';
                        popup.style.zIndex = '1000';
                    }
                }, 50);
            }
            return '';
        }
        """,
        Output('port-dummy-output-2', 'children'),
        Input('port-show-sorting-controls', 'data'),
        prevent_initial_call=True
    )

    # Clientside callback for Port Details table popup menu handlers
    app.clientside_callback(
        """
        function(n) {
            setTimeout(function() {
                // Set up popup menu click handlers for Port Details table
                const portMeasurePopup = document.getElementById('port-measure-sorting-controls');
                if (portMeasurePopup) {
                    const measureSourceItem = portMeasurePopup.querySelector('.port-measure-popup-source-item');
                    const measureAlphaItem = portMeasurePopup.querySelector('.port-measure-popup-alphabetic-item');
                    const measureFieldItem = portMeasurePopup.querySelector('.port-measure-popup-field-item');
                    const measureNestedItem = portMeasurePopup.querySelector('.port-measure-popup-nested-item');
                    
                    if (measureSourceItem) {
                        measureSourceItem.onclick = function() {
                            const btn = document.getElementById('port-measure-popup-source-btn');
                            if (btn) btn.click();
                        };
                    }
                    if (measureAlphaItem) {
                        measureAlphaItem.onclick = function() {
                            const btn = document.getElementById('port-measure-popup-alphabetic-btn');
                            if (btn) btn.click();
                        };
                    }
                    if (measureFieldItem) {
                        measureFieldItem.onclick = function() {
                            const btn = document.getElementById('port-measure-popup-field-btn');
                            if (btn) btn.click();
                        };
                        // Add click handler for Field arrow to show AVG(Value) text box
                        const fieldArrow = portMeasurePopup.querySelector('.port-measure-field-arrow-item');
                        if (fieldArrow) {
                            fieldArrow.onclick = function(e) {
                                e.stopPropagation();
                                const avgTextBox = document.getElementById('port-avg-text-box');
                                if (avgTextBox) {
                                    const arrowRect = fieldArrow.getBoundingClientRect();
                                    avgTextBox.style.display = 'block';
                                    avgTextBox.style.top = (arrowRect.top + window.scrollY) + 'px';
                                    avgTextBox.style.left = (arrowRect.right + window.scrollX + 5) + 'px';
                                    // Close text box when clicking outside or on the text box itself
                                    setTimeout(function() {
                                        avgTextBox.onclick = function(e) {
                                            e.stopPropagation();
                                            avgTextBox.style.display = 'none';
                                        };
                                        document.addEventListener('click', function closeAvgBox(event) {
                                            if (!avgTextBox.contains(event.target) && !fieldArrow.contains(event.target)) {
                                                avgTextBox.style.display = 'none';
                                                document.removeEventListener('click', closeAvgBox);
                                            }
                                        });
                                    }, 10);
                                }
                            };
                        }
                    }
                    if (measureNestedItem) {
                        measureNestedItem.onclick = function() {
                            const btn = document.getElementById('port-measure-popup-nested-btn');
                            if (btn) btn.click();
                        };
                        // Add click handler for Nested arrow to show AVG(Value) text box
                        const nestedArrow = portMeasurePopup.querySelector('.port-measure-nested-arrow-item');
                        if (nestedArrow) {
                            nestedArrow.onclick = function(e) {
                                e.stopPropagation();
                                const avgTextBox = document.getElementById('port-avg-text-box');
                                if (avgTextBox) {
                                    const arrowRect = nestedArrow.getBoundingClientRect();
                                    avgTextBox.style.display = 'block';
                                    avgTextBox.style.top = (arrowRect.top + window.scrollY) + 'px';
                                    avgTextBox.style.left = (arrowRect.right + window.scrollX + 5) + 'px';
                                    // Close text box when clicking outside or on the text box itself
                                    setTimeout(function() {
                                        avgTextBox.onclick = function(e) {
                                            e.stopPropagation();
                                            avgTextBox.style.display = 'none';
                                        };
                                        document.addEventListener('click', function closeAvgBox(event) {
                                            if (!avgTextBox.contains(event.target) && !nestedArrow.contains(event.target)) {
                                                avgTextBox.style.display = 'none';
                                                document.removeEventListener('click', closeAvgBox);
                                            }
                                        });
                                    }, 10);
                                }
                            };
                        }
                    }
                }
                
                // Add click handler to close AVG text box when clicked
                const portAvgBox = document.getElementById('port-avg-text-box');
                if (portAvgBox) {
                    portAvgBox.onclick = function(e) {
                        e.stopPropagation();
                        portAvgBox.style.display = 'none';
                    };
                }
            }, 100);
            return '';
        }
        """,
        Output('port-dummy-output', 'children'),
        Input('port-details-table', 'columns'),
        prevent_initial_call=False
    )

    # Client-side callback for Port Details table headers
    app.clientside_callback(
        """
        function(n) {
            setTimeout(function() {
                // Helper function to add sorting controls to a header
                function addSortingControls(header, columnName, ascBtnId, descBtnId, popupBtnId) {
                    if (!header) return;
                    if (header && !header.querySelector('.sort-order-container')) {
                        const sortContainer = document.createElement('div');
                        sortContainer.className = 'sort-order-container';
                        // Ensure vertical display with inline styles and inline positioning
                        sortContainer.style.position = 'absolute';
                        sortContainer.style.right = '28px';
                        sortContainer.style.top = '50%';
                        sortContainer.style.transform = 'translateY(-50%)';
                        sortContainer.style.display = 'flex';
                        sortContainer.style.flexDirection = 'column';
                        sortContainer.style.alignItems = 'center';
                        sortContainer.style.justifyContent = 'center';
                        sortContainer.style.width = '16px';
                        sortContainer.style.height = '30px';
                        sortContainer.style.zIndex = '10';
                        // HIDE BY DEFAULT - only show on hover
                        sortContainer.style.opacity = '0';
                        sortContainer.style.visibility = 'hidden';
                        sortContainer.style.pointerEvents = 'none';
                        
                        const aElement = document.createElement('div');
                        aElement.className = 'sort-asc';
                        aElement.textContent = 'A';
                        aElement.title = 'Click for ascending alphabetical order';
                        aElement.style.display = 'block';
                        aElement.style.lineHeight = '1.2';
                        aElement.style.fontSize = '11px';
                        aElement.style.fontWeight = 'bold';
                        aElement.style.textAlign = 'center';
                        aElement.style.marginBottom = '2px';
                        aElement.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById(ascBtnId);
                            if (btn) btn.click();
                        };
                        
                        const zElement = document.createElement('div');
                        zElement.className = 'sort-desc';
                        zElement.textContent = 'Z';
                        zElement.title = 'Click for descending alphabetical order';
                        zElement.style.display = 'block';
                        zElement.style.lineHeight = '1.2';
                        zElement.style.fontSize = '11px';
                        zElement.style.fontWeight = 'bold';
                        zElement.style.textAlign = 'center';
                        zElement.style.marginTop = '2px';
                        zElement.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById(descBtnId);
                            if (btn) btn.click();
                        };
                        
                        sortContainer.appendChild(aElement);
                        sortContainer.appendChild(zElement);
                        
                        // Add hover event listeners to show/hide A/Z text
                        header.addEventListener('mouseenter', function() {
                            sortContainer.style.opacity = '1';
                            sortContainer.style.visibility = 'visible';
                            sortContainer.style.pointerEvents = 'auto';
                        });
                        header.addEventListener('mouseleave', function() {
                            sortContainer.style.opacity = '0';
                            sortContainer.style.visibility = 'hidden';
                            sortContainer.style.pointerEvents = 'none';
                        });
                        
                        // Add SVG sort icon - positioned inline with A/Z
                        const sortIndicator = document.createElement('div');
                        sortIndicator.className = 'sort-indicator';
                        sortIndicator.title = 'Click to show sort options';
                        sortIndicator.style.position = 'absolute';
                        sortIndicator.style.right = '8px';
                        sortIndicator.style.top = '50%';
                        sortIndicator.style.transform = 'translateY(-50%)';
                        sortIndicator.style.width = '15px';
                        sortIndicator.style.height = '15px';
                        sortIndicator.style.zIndex = '11';
                        
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
                            const btn = document.getElementById(popupBtnId);
                            if (btn) {
                                // Position popup below the down arrow before showing
                                setTimeout(function() {
                                    const popupId = popupBtnId.replace('-popup-menu-btn', '-sorting-controls');
                                    const popup = document.getElementById(popupId);
                                    if (popup && sortIndicator) {
                                        const indicatorRect = sortIndicator.getBoundingClientRect();
                                        popup.style.position = 'absolute';
                                        popup.style.top = (indicatorRect.bottom + window.scrollY + 5) + 'px';
                                        popup.style.left = (indicatorRect.left + window.scrollX - 80) + 'px';
                                        popup.style.zIndex = '1000';
                                    }
                                }, 10);
                                btn.click();
                            }
                        };
                        
                        header.appendChild(sortContainer);
                        header.appendChild(sortIndicator);
                    }
                }
                
                // Add A/Z and SVG sort icon to Measure header
                const measureHeader = document.querySelector('#port-details-table .dash-header[data-dash-column="Measure"]');
                if (measureHeader) {
                    addSortingControls(measureHeader, 'Measure', 
                        'port-measure-sort-asc-btn', 
                        'port-measure-sort-desc-btn',
                        'port-measure-popup-menu-btn');
                }
                
                // Use MutationObserver to re-initialize if table structure changes
                // Only observe if not already initialized to prevent infinite loops
                if (!window.portDetailsObserverInitialized) {
                    window.portDetailsObserverInitialized = true;
                    const observer = new MutationObserver(function(mutations) {
                        // Check if we're already processing to prevent infinite loops
                        if (window.portDetailsObserverProcessing) {
                            return;
                        }
                        let shouldReinit = false;
                        mutations.forEach(function(mutation) {
                            // Only reinit if the mutation is not from our own additions
                            if (mutation.type === 'childList') {
                                // Check if the added nodes are our sorting controls
                                let isOurAddition = false;
                                if (mutation.addedNodes && mutation.addedNodes.length > 0) {
                                    mutation.addedNodes.forEach(function(node) {
                                        if (node.nodeType === 1 && (
                                            node.classList && (
                                                node.classList.contains('sort-order-container') ||
                                                node.classList.contains('sort-indicator')
                                            )
                                        )) {
                                            isOurAddition = true;
                                        }
                                    });
                                }
                                if (!isOurAddition) {
                                    shouldReinit = true;
                                }
                            } else if (mutation.type === 'attributes') {
                                // Only reinit for attribute changes that aren't from our code
                                const target = mutation.target;
                                if (target && !target.querySelector('.sort-order-container')) {
                                    shouldReinit = true;
                                }
                            }
                        });
                        if (shouldReinit) {
                            window.portDetailsObserverProcessing = true;
                            setTimeout(function() {
                                const measureHeader = document.querySelector('#port-details-table .dash-header[data-dash-column="Measure"]');
                                if (measureHeader && !measureHeader.querySelector('.sort-order-container')) {
                                    addSortingControls(measureHeader, 'Measure', 
                                        'port-measure-sort-asc-btn', 
                                        'port-measure-sort-desc-btn',
                                        'port-measure-popup-menu-btn');
                                }
                                window.portDetailsObserverProcessing = false;
                            }, 100);
                        }
                    });
                    
                    const portTable = document.getElementById('port-details-table');
                    if (portTable) {
                        observer.observe(portTable, {
                            childList: true,
                            subtree: true,
                            attributes: true,
                            attributeFilter: ['class', 'data-dash-column']
                        });
                    }
                }
            }, 100);
            return '';
        }
        """,
        Output('port-dummy-output-3', 'children'),
        Input('port-details-table', 'columns'),
        prevent_initial_call=False
    )

    # ==========================================================================
    # CLIENT-SIDE CALLBACKS FOR ALL TABLES
    # ==========================================================================
    
    # Client-side callback for Quality Specs hover functionality
    app.clientside_callback(
        """
        function(n) {
            setTimeout(function() {
                // Add hover functionality to quality specs section
                const hoverArea = document.getElementById('quality-specs-hover-trigger');
                const popup = document.getElementById('quality-specs-popup');
                const showBtn = document.getElementById('show-quality-specs-popup-btn');
                const hideBtn = document.getElementById('hide-quality-specs-popup-btn');
                
                if (hoverArea && popup && showBtn && hideBtn) {
                    // Show popup on mouse enter
                    hoverArea.addEventListener('mouseenter', function(e) {
                        // Position popup near the hover area
                        const rect = hoverArea.getBoundingClientRect();
                        popup.style.top = (rect.bottom + window.scrollY + 5) + 'px';
                        popup.style.left = (rect.left + window.scrollX) + 'px';
                        
                        showBtn.click();
                    });
                    
                    // Hide popup on mouse leave
                    hoverArea.addEventListener('mouseleave', function(e) {
                        // Small delay to allow moving to popup
                        setTimeout(function() {
                            if (!popup.matches(':hover')) {
                                hideBtn.click();
                            }
                        }, 100);
                    });
                    
                    // Keep popup visible when hovering over it
                    popup.addEventListener('mouseenter', function(e) {
                        // Keep popup visible
                    });
                    
                    // Hide popup when leaving popup
                    popup.addEventListener('mouseleave', function(e) {
                        setTimeout(function() {
                            if (!hoverArea.matches(':hover')) {
                                hideBtn.click();
                            }
                        }, 100);
                    });
                }
                
                // Also add hover to the values row
                const valueRows = document.querySelectorAll('.quality-specs-hover-area');
                valueRows.forEach(function(row) {
                    if (row.id !== 'quality-specs-hover-trigger') {
                        row.addEventListener('mouseenter', function(e) {
                            const rect = row.getBoundingClientRect();
                            popup.style.top = (rect.bottom + window.scrollY + 5) + 'px';
                            popup.style.left = (rect.left + window.scrollX) + 'px';
                            showBtn.click();
                        });
                        
                        row.addEventListener('mouseleave', function(e) {
                            setTimeout(function() {
                                if (!popup.matches(':hover')) {
                                    hideBtn.click();
                                }
                            }, 100);
                        });
                    }
                });
                
            }, 100);
            return '';
        }
        """,
        Output('quality-specs-dummy-output', 'children'),
        Input('quality-specs-popup', 'id'),
        prevent_initial_call=False
    )
    
    # Client-side callback for Mars Blend Assay table headers
    app.clientside_callback(
        """
        function(n) {
            setTimeout(function() {
                // Helper function to add sorting controls to a header
                function addSortingControls(header, columnName, ascBtnId, descBtnId, popupBtnId) {
                    if (!header) return;
                    if (header && !header.querySelector('.sort-order-container')) {
                        const sortContainer = document.createElement('div');
                        sortContainer.className = 'sort-order-container';
                        // Ensure vertical display with inline styles and inline positioning
                        sortContainer.style.position = 'absolute';
                        sortContainer.style.right = '28px';
                        sortContainer.style.top = '50%';
                        sortContainer.style.transform = 'translateY(-50%)';
                        sortContainer.style.display = 'flex';
                        sortContainer.style.flexDirection = 'column';
                        sortContainer.style.alignItems = 'center';
                        sortContainer.style.justifyContent = 'center';
                        sortContainer.style.width = '16px';
                        sortContainer.style.height = '30px';
                        sortContainer.style.zIndex = '10';
                        // HIDE BY DEFAULT - only show on hover
                        sortContainer.style.opacity = '0';
                        sortContainer.style.visibility = 'hidden';
                        sortContainer.style.pointerEvents = 'none';
                        
                        const aElement = document.createElement('div');
                        aElement.className = 'sort-asc';
                        aElement.textContent = 'A';
                        aElement.title = 'Click for ascending alphabetical order';
                        aElement.style.display = 'block';
                        aElement.style.lineHeight = '1.2';
                        aElement.style.fontSize = '11px';
                        aElement.style.fontWeight = 'bold';
                        aElement.style.textAlign = 'center';
                        aElement.style.marginBottom = '2px';
                        aElement.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById(ascBtnId);
                            if (btn) btn.click();
                        };
                        
                        const zElement = document.createElement('div');
                        zElement.className = 'sort-desc';
                        zElement.textContent = 'Z';
                        zElement.title = 'Click for descending alphabetical order';
                        zElement.style.display = 'block';
                        zElement.style.lineHeight = '1.2';
                        zElement.style.fontSize = '11px';
                        zElement.style.fontWeight = 'bold';
                        zElement.style.textAlign = 'center';
                        zElement.style.marginTop = '2px';
                        zElement.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById(descBtnId);
                            if (btn) btn.click();
                        };
                        
                        sortContainer.appendChild(aElement);
                        sortContainer.appendChild(zElement);
                        
                        // Add hover event listeners to show/hide A/Z text
                        header.addEventListener('mouseenter', function() {
                            sortContainer.style.opacity = '1';
                            sortContainer.style.visibility = 'visible';
                            sortContainer.style.pointerEvents = 'auto';
                        });
                        header.addEventListener('mouseleave', function() {
                            sortContainer.style.opacity = '0';
                            sortContainer.style.visibility = 'hidden';
                            sortContainer.style.pointerEvents = 'none';
                        });
                        
                        // Add SVG sort icon - positioned inline with A/Z
                        const sortIndicator = document.createElement('div');
                        sortIndicator.className = 'sort-indicator';
                        sortIndicator.title = 'Click to show sort options';
                        sortIndicator.style.position = 'absolute';
                        sortIndicator.style.right = '8px';
                        sortIndicator.style.top = '50%';
                        sortIndicator.style.transform = 'translateY(-50%)';
                        sortIndicator.style.width = '15px';
                        sortIndicator.style.height = '15px';
                        sortIndicator.style.zIndex = '11';
                        
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
                            const btn = document.getElementById(popupBtnId);
                            if (btn) {
                                // Position popup below the down arrow before showing
                                setTimeout(function() {
                                    const popupId = popupBtnId.replace('-popup-menu-btn', '-sorting-controls');
                                    const popup = document.getElementById(popupId);
                                    if (popup && sortIndicator) {
                                        const indicatorRect = sortIndicator.getBoundingClientRect();
                                        popup.style.position = 'absolute';
                                        popup.style.top = (indicatorRect.bottom + window.scrollY + 5) + 'px';
                                        popup.style.left = (indicatorRect.left + window.scrollX - 80) + 'px';
                                        popup.style.zIndex = '1000';
                                    }
                                }, 10);
                                btn.click();
                            }
                        };
                        
                        header.appendChild(sortContainer);
                        header.appendChild(sortIndicator);
                    }
                }
                
                // Add A/Z and SVG sort icon to Property header
                const propertyHeader = document.querySelector('.dash-header[data-dash-column="Property"]');
                if (propertyHeader) {
                    addSortingControls(propertyHeader, 'Property', 
                        'assay-property-sort-asc-btn', 
                        'assay-property-sort-desc-btn',
                        'assay-property-popup-menu-btn');
                }
                    
                // Add A/Z and SVG sort icon to Unit header
                const unitHeader = document.querySelector('.dash-header[data-dash-column="Unit"]');
                if (unitHeader) {
                    addSortingControls(unitHeader, 'Unit', 
                        'assay-unit-sort-asc-btn', 
                        'assay-unit-sort-desc-btn',
                        'assay-unit-popup-menu-btn');
                }
                
                // Add click handlers for Property popup menu items - ASSAY TABLE ONLY
                const propertyPopup = document.getElementById('assay-property-sorting-controls');
                if (propertyPopup) {
                    const propSourceItem = propertyPopup.querySelector('.assay-property-popup-source-item');
                    const propAlphaItem = propertyPopup.querySelector('.assay-property-popup-alphabetic-item');
                    const propFieldItem = propertyPopup.querySelector('.assay-property-popup-field-item');
                    const propNestedItem = propertyPopup.querySelector('.assay-property-popup-nested-item');
                    
                    if (propSourceItem) {
                        propSourceItem.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById('assay-property-popup-source-btn');
                            if (btn) btn.click();
                        };
                    }
                    if (propAlphaItem) {
                        propAlphaItem.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById('assay-property-popup-alphabetic-btn');
                            if (btn) btn.click();
                        };
                    }
                    if (propFieldItem) {
                        propFieldItem.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById('assay-property-popup-field-btn');
                            if (btn) btn.click();
                        };
                        // Add click handler for Field arrow to show AVG(Value) text box
                        const fieldArrow = propertyPopup.querySelector('.assay-property-field-arrow-item');
                        if (fieldArrow) {
                            fieldArrow.onclick = function(e) {
                                e.stopPropagation();
                                const avgTextBox = document.getElementById('assay-avg-text-box');
                                if (avgTextBox) {
                                    const arrowRect = fieldArrow.getBoundingClientRect();
                                    avgTextBox.style.display = 'block';
                                    avgTextBox.style.top = (arrowRect.top + window.scrollY) + 'px';
                                    avgTextBox.style.left = (arrowRect.right + window.scrollX + 5) + 'px';
                                    // Close text box when clicking outside or on the text box itself
                                    setTimeout(function() {
                                        avgTextBox.onclick = function(e) {
                                            e.stopPropagation();
                                            avgTextBox.style.display = 'none';
                                        };
                                        document.addEventListener('click', function closeAvgBox(event) {
                                            if (!avgTextBox.contains(event.target) && !fieldArrow.contains(event.target)) {
                                                avgTextBox.style.display = 'none';
                                                document.removeEventListener('click', closeAvgBox);
                                            }
                                        });
                                    }, 10);
                                }
                            };
                        }
                    }
                    if (propNestedItem) {
                        propNestedItem.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById('assay-property-popup-nested-btn');
                            if (btn) btn.click();
                        };
                        // Add click handler for Nested arrow to show AVG(Value) text box
                        const nestedArrow = propertyPopup.querySelector('.assay-property-nested-arrow-item');
                        if (nestedArrow) {
                            nestedArrow.onclick = function(e) {
                                e.stopPropagation();
                                const avgTextBox = document.getElementById('assay-avg-text-box');
                                if (avgTextBox) {
                                    const arrowRect = nestedArrow.getBoundingClientRect();
                                    avgTextBox.style.display = 'block';
                                    avgTextBox.style.top = (arrowRect.top + window.scrollY) + 'px';
                                    avgTextBox.style.left = (arrowRect.right + window.scrollX + 5) + 'px';
                                    // Close text box when clicking outside or on the text box itself
                                    setTimeout(function() {
                                        avgTextBox.onclick = function(e) {
                                            e.stopPropagation();
                                            avgTextBox.style.display = 'none';
                                        };
                                        document.addEventListener('click', function closeAvgBox(event) {
                                            if (!avgTextBox.contains(event.target) && !nestedArrow.contains(event.target)) {
                                                avgTextBox.style.display = 'none';
                                                document.removeEventListener('click', closeAvgBox);
                                            }
                                        });
                                    }, 10);
                                }
                            };
                        }
                    }
                }
                
                // Add click handlers for Unit popup menu items - ASSAY TABLE ONLY
                const unitPopup = document.getElementById('assay-unit-sorting-controls');
                if (unitPopup) {
                    const unitSourceItem = unitPopup.querySelector('.assay-unit-popup-source-item');
                    const unitAlphaItem = unitPopup.querySelector('.assay-unit-popup-alphabetic-item');
                    const unitFieldItem = unitPopup.querySelector('.assay-unit-popup-field-item');
                    const unitNestedItem = unitPopup.querySelector('.assay-unit-popup-nested-item');
                    
                    if (unitSourceItem) {
                        unitSourceItem.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById('assay-unit-popup-source-btn');
                            if (btn) btn.click();
                        };
                    }
                    if (unitAlphaItem) {
                        unitAlphaItem.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById('assay-unit-popup-alphabetic-btn');
                            if (btn) btn.click();
                        };
                    }
                    if (unitFieldItem) {
                        unitFieldItem.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById('assay-unit-popup-field-btn');
                            if (btn) btn.click();
                        };
                        // Add click handler for Field arrow to show AVG(Value) text box
                        const fieldArrow = unitPopup.querySelector('.assay-unit-field-arrow-item');
                        if (fieldArrow) {
                            fieldArrow.onclick = function(e) {
                                e.stopPropagation();
                                const avgTextBox = document.getElementById('assay-avg-text-box');
                                if (avgTextBox) {
                                    const arrowRect = fieldArrow.getBoundingClientRect();
                                    avgTextBox.style.display = 'block';
                                    avgTextBox.style.top = (arrowRect.top + window.scrollY) + 'px';
                                    avgTextBox.style.left = (arrowRect.right + window.scrollX + 5) + 'px';
                                    // Close text box when clicking outside or on the text box itself
                                    setTimeout(function() {
                                        avgTextBox.onclick = function(e) {
                                            e.stopPropagation();
                                            avgTextBox.style.display = 'none';
                                        };
                                        document.addEventListener('click', function closeAvgBox(event) {
                                            if (!avgTextBox.contains(event.target) && !fieldArrow.contains(event.target)) {
                                                avgTextBox.style.display = 'none';
                                                document.removeEventListener('click', closeAvgBox);
                                            }
                                        });
                                    }, 10);
                                }
                            };
                        }
                    }
                    if (unitNestedItem) {
                        unitNestedItem.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById('assay-unit-popup-nested-btn');
                            if (btn) btn.click();
                        };
                        // Add click handler for Nested arrow to show AVG(Value) text box
                        const nestedArrow = unitPopup.querySelector('.assay-unit-nested-arrow-item');
                        if (nestedArrow) {
                            nestedArrow.onclick = function(e) {
                                e.stopPropagation();
                                const avgTextBox = document.getElementById('assay-avg-text-box');
                                if (avgTextBox) {
                                    const arrowRect = nestedArrow.getBoundingClientRect();
                                    avgTextBox.style.display = 'block';
                                    avgTextBox.style.top = (arrowRect.top + window.scrollY) + 'px';
                                    avgTextBox.style.left = (arrowRect.right + window.scrollX + 5) + 'px';
                                    // Close text box when clicking outside or on the text box itself
                                    setTimeout(function() {
                                        avgTextBox.onclick = function(e) {
                                            e.stopPropagation();
                                            avgTextBox.style.display = 'none';
                                        };
                                        document.addEventListener('click', function closeAvgBox(event) {
                                            if (!avgTextBox.contains(event.target) && !nestedArrow.contains(event.target)) {
                                                avgTextBox.style.display = 'none';
                                                document.removeEventListener('click', closeAvgBox);
                                            }
                                        });
                                    }, 10);
                                }
                            };
                        }
                    }
                }
                
                // Add click handler to close AVG text box when clicked
                const assayAvgBox = document.getElementById('assay-avg-text-box');
                if (assayAvgBox) {
                    assayAvgBox.onclick = function(e) {
                        e.stopPropagation();
                        assayAvgBox.style.display = 'none';
                    };
                }
            }, 100);
            return '';
        }
        """,
        Output('assay-dummy-output', 'children'),
        Input('assay-table', 'columns'),
        prevent_initial_call=False
    )
    
    # Client-side callback for Refined Products table headers
    app.clientside_callback(
        """
        function(n) {
            setTimeout(function() {
                // Helper function to add sorting controls to a header
                function addSortingControls(header, columnName, ascBtnId, descBtnId, popupBtnId) {
                    if (!header) return;
                    if (header && !header.querySelector('.sort-order-container')) {
                        const sortContainer = document.createElement('div');
                        sortContainer.className = 'sort-order-container';
                        // Ensure vertical display with inline styles and inline positioning
                        sortContainer.style.position = 'absolute';
                        sortContainer.style.right = '28px';
                        sortContainer.style.top = '50%';
                        sortContainer.style.transform = 'translateY(-50%)';
                        sortContainer.style.display = 'flex';
                        sortContainer.style.flexDirection = 'column';
                        sortContainer.style.alignItems = 'center';
                        sortContainer.style.justifyContent = 'center';
                        sortContainer.style.width = '16px';
                        sortContainer.style.height = '30px';
                        sortContainer.style.zIndex = '10';
                        // HIDE BY DEFAULT - only show on hover
                        sortContainer.style.opacity = '0';
                        sortContainer.style.visibility = 'hidden';
                        sortContainer.style.pointerEvents = 'none';
                        
                        const aElement = document.createElement('div');
                        aElement.className = 'sort-asc';
                        aElement.textContent = 'A';
                        aElement.title = 'Click for ascending alphabetical order';
                        aElement.style.display = 'block';
                        aElement.style.lineHeight = '1.2';
                        aElement.style.fontSize = '11px';
                        aElement.style.fontWeight = 'bold';
                        aElement.style.textAlign = 'center';
                        aElement.style.marginBottom = '2px';
                        aElement.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById(ascBtnId);
                            if (btn) btn.click();
                        };
                        
                        const zElement = document.createElement('div');
                        zElement.className = 'sort-desc';
                        zElement.textContent = 'Z';
                        zElement.title = 'Click for descending alphabetical order';
                        zElement.style.display = 'block';
                        zElement.style.lineHeight = '1.2';
                        zElement.style.fontSize = '11px';
                        zElement.style.fontWeight = 'bold';
                        zElement.style.textAlign = 'center';
                        zElement.style.marginTop = '2px';
                        zElement.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById(descBtnId);
                            if (btn) btn.click();
                        };
                        
                        sortContainer.appendChild(aElement);
                        sortContainer.appendChild(zElement);
                        
                        // Add hover event listeners to show/hide A/Z text
                        header.addEventListener('mouseenter', function() {
                            sortContainer.style.opacity = '1';
                            sortContainer.style.visibility = 'visible';
                            sortContainer.style.pointerEvents = 'auto';
                        });
                        header.addEventListener('mouseleave', function() {
                            sortContainer.style.opacity = '0';
                            sortContainer.style.visibility = 'hidden';
                            sortContainer.style.pointerEvents = 'none';
                        });
                        
                        // Add SVG sort icon - positioned inline with A/Z
                        const sortIndicator = document.createElement('div');
                        sortIndicator.className = 'sort-indicator';
                        sortIndicator.title = 'Click to show sort options';
                        sortIndicator.style.position = 'absolute';
                        sortIndicator.style.right = '8px';
                        sortIndicator.style.top = '50%';
                        sortIndicator.style.transform = 'translateY(-50%)';
                        sortIndicator.style.width = '15px';
                        sortIndicator.style.height = '15px';
                        sortIndicator.style.zIndex = '11';
                        
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
                            const btn = document.getElementById(popupBtnId);
                            if (btn) {
                                // Position popup below the down arrow before showing
                                setTimeout(function() {
                                    const popupId = popupBtnId.replace('-popup-menu-btn', '-sorting-controls');
                                    const popup = document.getElementById(popupId);
                                    if (popup && sortIndicator) {
                                        const indicatorRect = sortIndicator.getBoundingClientRect();
                                        popup.style.position = 'absolute';
                                        popup.style.top = (indicatorRect.bottom + window.scrollY + 5) + 'px';
                                        popup.style.left = (indicatorRect.left + window.scrollX - 80) + 'px';
                                        popup.style.zIndex = '1000';
                                    }
                                }, 10);
                                btn.click();
                            }
                        };
                        
                        header.appendChild(sortContainer);
                        header.appendChild(sortIndicator);
                    }
                }
                
                // Find headers using multiple strategies with retries - REFINED TABLE ONLY
                function findRefinedHeader(columnName) {
                    // Strategy 1: Search within refined products table first
                    const table = document.getElementById('refined-products-table');
                    if (table) {
                        let header = table.querySelector('.dash-header[data-dash-column="' + columnName + '"]');
                        if (header) return header;
                    }
                    
                    // Strategy 2: Direct data-dash-column match
                    let header = document.querySelector('.dash-header[data-dash-column="' + columnName + '"]');
                    if (header) return header;
                    
                    return null;
                }
                
                // Function to initialize all headers - REFINED TABLE ONLY
                function initializeRefinedHeaders() {
                    // Add controls to Product header
                    let productHeader = findRefinedHeader('Product');
                    if (productHeader) {
                        addSortingControls(productHeader, 'Product', 
                            'refined-product-sort-asc-btn', 
                            'refined-product-sort-desc-btn',
                            'refined-product-popup-menu-btn');
                    }
                    
                    // Add controls to Cut Points header
                    let cutPointsHeader = findRefinedHeader('Cut Points (°C)');
                    if (cutPointsHeader) {
                        addSortingControls(cutPointsHeader, 'Cut Points (°C)', 
                            'refined-cutpoints-sort-asc-btn', 
                            'refined-cutpoints-sort-desc-btn',
                            'refined-cutpoints-popup-menu-btn');
                    }
                    
                    // Add controls to Property header
                    let propertyHeader = findRefinedHeader('Property');
                    if (propertyHeader) {
                        addSortingControls(propertyHeader, 'Property', 
                            'refined-property-sort-asc-btn', 
                            'refined-property-sort-desc-btn',
                            'refined-property-popup-menu-btn');
                    }
                    
                    // Add controls to Unit header
                    let unitHeader = findRefinedHeader('Unit');
                    if (unitHeader) {
                        addSortingControls(unitHeader, 'Unit', 
                            'refined-unit-sort-asc-btn', 
                            'refined-unit-sort-desc-btn',
                            'refined-unit-popup-menu-btn');
                    }
                }
                
                // Try to initialize headers
                initializeRefinedHeaders();
                
                // Use MutationObserver to re-initialize if table is re-rendered
                const table = document.getElementById('refined-products-table');
                if (table) {
                    // Only create observer once to prevent infinite loops
                    if (!window.refinedObserverInitialized) {
                        window.refinedObserverInitialized = true;
                        const observer = new MutationObserver(function(mutations) {
                            // Check if we're already processing to prevent infinite loops
                            if (window.refinedObserverProcessing) {
                                return;
                            }
                            let shouldReinit = false;
                            mutations.forEach(function(mutation) {
                                // Only reinit if the mutation is not from our own additions
                                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                                    // Check if the added nodes are our sorting controls
                                    let isOurAddition = false;
                                    mutation.addedNodes.forEach(function(node) {
                                        if (node.nodeType === 1 && (
                                            node.classList && (
                                                node.classList.contains('sort-order-container') ||
                                                node.classList.contains('sort-indicator')
                                            )
                                        )) {
                                            isOurAddition = true;
                                        }
                                    });
                                    if (!isOurAddition) {
                                        shouldReinit = true;
                                    }
                                }
                            });
                            if (shouldReinit) {
                                window.refinedObserverProcessing = true;
                                setTimeout(function() {
                                    initializeRefinedHeaders();
                                    window.refinedObserverProcessing = false;
                                }, 100);
                            }
                        });
                        
                        observer.observe(table, {
                            childList: true,
                            subtree: true
                        });
                    }
                }
                
                // Also retry after a delay in case headers aren't ready yet
                setTimeout(function() {
                    initializeRefinedHeaders();
                }, 300);
                
                setTimeout(function() {
                    initializeRefinedHeaders();
                }, 600);
                
                // Set up popup menu click handlers for all refined products headers - REFINED TABLE ONLY
                const productPopup = document.getElementById('refined-product-sorting-controls');
                if (productPopup) {
                    const productSourceItem = productPopup.querySelector('.refined-product-popup-source-item');
                    const productAlphaItem = productPopup.querySelector('.refined-product-popup-alphabetic-item');
                    const productFieldItem = productPopup.querySelector('.refined-product-popup-field-item');
                    const productNestedItem = productPopup.querySelector('.refined-product-popup-nested-item');
                    
                    if (productSourceItem) {
                        productSourceItem.onclick = function() {
                            const btn = document.getElementById('refined-product-popup-source-btn');
                            if (btn) btn.click();
                        };
                    }
                    if (productAlphaItem) {
                        productAlphaItem.onclick = function() {
                            const btn = document.getElementById('refined-product-popup-alphabetic-btn');
                            if (btn) btn.click();
                        };
                    }
                    if (productFieldItem) {
                        productFieldItem.onclick = function() {
                            const btn = document.getElementById('refined-product-popup-field-btn');
                            if (btn) btn.click();
                        };
                        // Add click handler for Field arrow to show AVG(Value) text box
                        const fieldArrow = productPopup.querySelector('.refined-product-field-arrow-item');
                        if (fieldArrow) {
                            fieldArrow.onclick = function(e) {
                                e.stopPropagation();
                                const avgTextBox = document.getElementById('refined-avg-text-box');
                                if (avgTextBox) {
                                    const arrowRect = fieldArrow.getBoundingClientRect();
                                    avgTextBox.style.display = 'block';
                                    avgTextBox.style.top = (arrowRect.top + window.scrollY) + 'px';
                                    avgTextBox.style.left = (arrowRect.right + window.scrollX + 5) + 'px';
                                    // Close text box when clicking outside or on the text box itself
                                    setTimeout(function() {
                                        avgTextBox.onclick = function(e) {
                                            e.stopPropagation();
                                            avgTextBox.style.display = 'none';
                                        };
                                        document.addEventListener('click', function closeAvgBox(event) {
                                            if (!avgTextBox.contains(event.target) && !fieldArrow.contains(event.target)) {
                                                avgTextBox.style.display = 'none';
                                                document.removeEventListener('click', closeAvgBox);
                                            }
                                        });
                                    }, 10);
                                }
                            };
                        }
                    }
                    if (productNestedItem) {
                        productNestedItem.onclick = function() {
                            const btn = document.getElementById('refined-product-popup-nested-btn');
                            if (btn) btn.click();
                        };
                        // Add click handler for Nested arrow to show AVG(Value) text box
                        const nestedArrow = productPopup.querySelector('.refined-product-nested-arrow-item');
                        if (nestedArrow) {
                            nestedArrow.onclick = function(e) {
                                e.stopPropagation();
                                const avgTextBox = document.getElementById('refined-avg-text-box');
                                if (avgTextBox) {
                                    const arrowRect = nestedArrow.getBoundingClientRect();
                                    avgTextBox.style.display = 'block';
                                    avgTextBox.style.top = (arrowRect.top + window.scrollY) + 'px';
                                    avgTextBox.style.left = (arrowRect.right + window.scrollX + 5) + 'px';
                                    // Close text box when clicking outside or on the text box itself
                                    setTimeout(function() {
                                        avgTextBox.onclick = function(e) {
                                            e.stopPropagation();
                                            avgTextBox.style.display = 'none';
                                        };
                                        document.addEventListener('click', function closeAvgBox(event) {
                                            if (!avgTextBox.contains(event.target) && !nestedArrow.contains(event.target)) {
                                                avgTextBox.style.display = 'none';
                                                document.removeEventListener('click', closeAvgBox);
                                            }
                                        });
                                    }, 10);
                                }
                            };
                        }
                    }
                }
                
                const cutPointsPopup = document.getElementById('refined-cutpoints-sorting-controls');
                if (cutPointsPopup) {
                    const cutPointsSourceItem = cutPointsPopup.querySelector('.refined-cutpoints-popup-source-item');
                    const cutPointsAlphaItem = cutPointsPopup.querySelector('.refined-cutpoints-popup-alphabetic-item');
                    const cutPointsFieldItem = cutPointsPopup.querySelector('.refined-cutpoints-popup-field-item');
                    const cutPointsNestedItem = cutPointsPopup.querySelector('.refined-cutpoints-popup-nested-item');
                    
                    if (cutPointsSourceItem) {
                        cutPointsSourceItem.onclick = function() {
                            const btn = document.getElementById('refined-cutpoints-popup-source-btn');
                            if (btn) btn.click();
                        };
                    }
                    if (cutPointsAlphaItem) {
                        cutPointsAlphaItem.onclick = function() {
                            const btn = document.getElementById('refined-cutpoints-popup-alphabetic-btn');
                            if (btn) btn.click();
                        };
                    }
                    if (cutPointsFieldItem) {
                        cutPointsFieldItem.onclick = function() {
                            const btn = document.getElementById('refined-cutpoints-popup-field-btn');
                            if (btn) btn.click();
                        };
                        // Add click handler for Field arrow to show AVG(Value) text box
                        const fieldArrow = cutPointsPopup.querySelector('.refined-cutpoints-field-arrow-item');
                        if (fieldArrow) {
                            fieldArrow.onclick = function(e) {
                                e.stopPropagation();
                                const avgTextBox = document.getElementById('refined-avg-text-box');
                                if (avgTextBox) {
                                    const arrowRect = fieldArrow.getBoundingClientRect();
                                    avgTextBox.style.display = 'block';
                                    avgTextBox.style.top = (arrowRect.top + window.scrollY) + 'px';
                                    avgTextBox.style.left = (arrowRect.right + window.scrollX + 5) + 'px';
                                    // Close text box when clicking outside or on the text box itself
                                    setTimeout(function() {
                                        avgTextBox.onclick = function(e) {
                                            e.stopPropagation();
                                            avgTextBox.style.display = 'none';
                                        };
                                        document.addEventListener('click', function closeAvgBox(event) {
                                            if (!avgTextBox.contains(event.target) && !fieldArrow.contains(event.target)) {
                                                avgTextBox.style.display = 'none';
                                                document.removeEventListener('click', closeAvgBox);
                                            }
                                        });
                                    }, 10);
                                }
                            };
                        }
                    }
                    if (cutPointsNestedItem) {
                        cutPointsNestedItem.onclick = function() {
                            const btn = document.getElementById('refined-cutpoints-popup-nested-btn');
                            if (btn) btn.click();
                        };
                        // Add click handler for Nested arrow to show AVG(Value) text box
                        const nestedArrow = cutPointsPopup.querySelector('.refined-cutpoints-nested-arrow-item');
                        if (nestedArrow) {
                            nestedArrow.onclick = function(e) {
                                e.stopPropagation();
                                const avgTextBox = document.getElementById('refined-avg-text-box');
                                if (avgTextBox) {
                                    const arrowRect = nestedArrow.getBoundingClientRect();
                                    avgTextBox.style.display = 'block';
                                    avgTextBox.style.top = (arrowRect.top + window.scrollY) + 'px';
                                    avgTextBox.style.left = (arrowRect.right + window.scrollX + 5) + 'px';
                                    // Close text box when clicking outside or on the text box itself
                                    setTimeout(function() {
                                        avgTextBox.onclick = function(e) {
                                            e.stopPropagation();
                                            avgTextBox.style.display = 'none';
                                        };
                                        document.addEventListener('click', function closeAvgBox(event) {
                                            if (!avgTextBox.contains(event.target) && !nestedArrow.contains(event.target)) {
                                                avgTextBox.style.display = 'none';
                                                document.removeEventListener('click', closeAvgBox);
                                            }
                                        });
                                    }, 10);
                                }
                            };
                        }
                    }
                }
                
                const propertyPopup = document.getElementById('refined-property-sorting-controls');
                if (propertyPopup) {
                    const propertySourceItem = propertyPopup.querySelector('.refined-property-popup-source-item');
                    const propertyAlphaItem = propertyPopup.querySelector('.refined-property-popup-alphabetic-item');
                    const propertyFieldItem = propertyPopup.querySelector('.refined-property-popup-field-item');
                    const propertyNestedItem = propertyPopup.querySelector('.refined-property-popup-nested-item');
                    
                    if (propertySourceItem) {
                        propertySourceItem.onclick = function() {
                            const btn = document.getElementById('refined-property-popup-source-btn');
                            if (btn) btn.click();
                        };
                    }
                    if (propertyAlphaItem) {
                        propertyAlphaItem.onclick = function() {
                            const btn = document.getElementById('refined-property-popup-alphabetic-btn');
                            if (btn) btn.click();
                        };
                    }
                    if (propertyFieldItem) {
                        propertyFieldItem.onclick = function() {
                            const btn = document.getElementById('refined-property-popup-field-btn');
                            if (btn) btn.click();
                        };
                        // Add click handler for Field arrow to show AVG(Value) text box
                        const fieldArrow = propertyPopup.querySelector('.refined-property-field-arrow-item');
                        if (fieldArrow) {
                            fieldArrow.onclick = function(e) {
                                e.stopPropagation();
                                const avgTextBox = document.getElementById('refined-avg-text-box');
                                if (avgTextBox) {
                                    const arrowRect = fieldArrow.getBoundingClientRect();
                                    avgTextBox.style.display = 'block';
                                    avgTextBox.style.top = (arrowRect.top + window.scrollY) + 'px';
                                    avgTextBox.style.left = (arrowRect.right + window.scrollX + 5) + 'px';
                                    // Close text box when clicking outside or on the text box itself
                                    setTimeout(function() {
                                        avgTextBox.onclick = function(e) {
                                            e.stopPropagation();
                                            avgTextBox.style.display = 'none';
                                        };
                                        document.addEventListener('click', function closeAvgBox(event) {
                                            if (!avgTextBox.contains(event.target) && !fieldArrow.contains(event.target)) {
                                                avgTextBox.style.display = 'none';
                                                document.removeEventListener('click', closeAvgBox);
                                            }
                                        });
                                    }, 10);
                                }
                            };
                        }
                    }
                    if (propertyNestedItem) {
                        propertyNestedItem.onclick = function() {
                            const btn = document.getElementById('refined-property-popup-nested-btn');
                            if (btn) btn.click();
                        };
                        // Add click handler for Nested arrow to show AVG(Value) text box
                        const nestedArrow = propertyPopup.querySelector('.refined-property-nested-arrow-item');
                        if (nestedArrow) {
                            nestedArrow.onclick = function(e) {
                                e.stopPropagation();
                                const avgTextBox = document.getElementById('refined-avg-text-box');
                                if (avgTextBox) {
                                    const arrowRect = nestedArrow.getBoundingClientRect();
                                    avgTextBox.style.display = 'block';
                                    avgTextBox.style.top = (arrowRect.top + window.scrollY) + 'px';
                                    avgTextBox.style.left = (arrowRect.right + window.scrollX + 5) + 'px';
                                    // Close text box when clicking outside or on the text box itself
                                    setTimeout(function() {
                                        avgTextBox.onclick = function(e) {
                                            e.stopPropagation();
                                            avgTextBox.style.display = 'none';
                                        };
                                        document.addEventListener('click', function closeAvgBox(event) {
                                            if (!avgTextBox.contains(event.target) && !nestedArrow.contains(event.target)) {
                                                avgTextBox.style.display = 'none';
                                                document.removeEventListener('click', closeAvgBox);
                                            }
                                        });
                                    }, 10);
                                }
                            };
                        }
                    }
                }
                
                const unitPopup = document.getElementById('refined-unit-sorting-controls');
                if (unitPopup) {
                    const unitSourceItem = unitPopup.querySelector('.refined-unit-popup-source-item');
                    const unitAlphaItem = unitPopup.querySelector('.refined-unit-popup-alphabetic-item');
                    const unitFieldItem = unitPopup.querySelector('.refined-unit-popup-field-item');
                    const unitNestedItem = unitPopup.querySelector('.refined-unit-popup-nested-item');
                    
                    if (unitSourceItem) {
                        unitSourceItem.onclick = function() {
                            const btn = document.getElementById('refined-unit-popup-source-btn');
                            if (btn) btn.click();
                        };
                    }
                    if (unitAlphaItem) {
                        unitAlphaItem.onclick = function() {
                            const btn = document.getElementById('refined-unit-popup-alphabetic-btn');
                            if (btn) btn.click();
                        };
                    }
                    if (unitFieldItem) {
                        unitFieldItem.onclick = function() {
                            const btn = document.getElementById('refined-unit-popup-field-btn');
                            if (btn) btn.click();
                        };
                        // Add click handler for Field arrow to show AVG(Value) text box
                        const fieldArrow = unitPopup.querySelector('.refined-unit-field-arrow-item');
                        if (fieldArrow) {
                            fieldArrow.onclick = function(e) {
                                e.stopPropagation();
                                const avgTextBox = document.getElementById('refined-avg-text-box');
                                if (avgTextBox) {
                                    const arrowRect = fieldArrow.getBoundingClientRect();
                                    avgTextBox.style.display = 'block';
                                    avgTextBox.style.top = (arrowRect.top + window.scrollY) + 'px';
                                    avgTextBox.style.left = (arrowRect.right + window.scrollX + 5) + 'px';
                                    // Close text box when clicking outside or on the text box itself
                                    setTimeout(function() {
                                        avgTextBox.onclick = function(e) {
                                            e.stopPropagation();
                                            avgTextBox.style.display = 'none';
                                        };
                                        document.addEventListener('click', function closeAvgBox(event) {
                                            if (!avgTextBox.contains(event.target) && !fieldArrow.contains(event.target)) {
                                                avgTextBox.style.display = 'none';
                                                document.removeEventListener('click', closeAvgBox);
                                            }
                                        });
                                    }, 10);
                                }
                            };
                        }
                    }
                    if (unitNestedItem) {
                        unitNestedItem.onclick = function() {
                            const btn = document.getElementById('refined-unit-popup-nested-btn');
                            if (btn) btn.click();
                        };
                        // Add click handler for Nested arrow to show AVG(Value) text box
                        const nestedArrow = unitPopup.querySelector('.refined-unit-nested-arrow-item');
                        if (nestedArrow) {
                            nestedArrow.onclick = function(e) {
                                e.stopPropagation();
                                const avgTextBox = document.getElementById('refined-avg-text-box');
                                if (avgTextBox) {
                                    const arrowRect = nestedArrow.getBoundingClientRect();
                                    avgTextBox.style.display = 'block';
                                    avgTextBox.style.top = (arrowRect.top + window.scrollY) + 'px';
                                    avgTextBox.style.left = (arrowRect.right + window.scrollX + 5) + 'px';
                                    // Close text box when clicking outside or on the text box itself
                                    setTimeout(function() {
                                        avgTextBox.onclick = function(e) {
                                            e.stopPropagation();
                                            avgTextBox.style.display = 'none';
                                        };
                                        document.addEventListener('click', function closeAvgBox(event) {
                                            if (!avgTextBox.contains(event.target) && !nestedArrow.contains(event.target)) {
                                                avgTextBox.style.display = 'none';
                                                document.removeEventListener('click', closeAvgBox);
                                            }
                                        });
                                    }, 10);
                                }
                            };
                        }
                    }
                }
                
                // Add click handler to close AVG text box when clicked
                const refinedAvgBox = document.getElementById('refined-avg-text-box');
                if (refinedAvgBox) {
                    refinedAvgBox.onclick = function(e) {
                        e.stopPropagation();
                        refinedAvgBox.style.display = 'none';
                    };
                }
            }, 100);
            return '';
        }
        """,
        Output('refined-dummy-output', 'children'),
        Input('refined-products-table', 'columns'),
        prevent_initial_call=False
    )
    

# ------------------------------------------------------------------------------
# DASH APP CREATION - MAIN FUNCTION
# ------------------------------------------------------------------------------
def create_crude_profile_dashboard(server, url_base_pathname="/dash/crude-profile/"):
    """Create and configure the crude profile dashboard"""
    try:
        # Try to import from your existing app structure
        from app import create_dash_app
        dash_app = create_dash_app(server, url_base_pathname)
    except ImportError:
        # Fallback to standalone creation
        print("Using standalone Dash app creation")
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