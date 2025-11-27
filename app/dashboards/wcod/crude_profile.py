# crude_profile.py
"""
Crude Profile Dashboard - Complete Implementation with Separate Sorting for Both Tables
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
    "assay_details": os.path.join(DATA_DIR, "Assay_Details.csv"),
    "quality_specs": os.path.join(DATA_DIR, "Latest_Quality_Specs.csv"),
    "mars_assay": os.path.join(DATA_DIR, "Mars_Blend_Assay.csv"),
    "refined_products": os.path.join(DATA_DIR, "Refined_Product_Breakdown_and_Properties.csv"),
    "production_exports": os.path.join(DATA_DIR, "Production_and_Exports_Chart_Production_Exports.csv"),
    "loading_ports": os.path.join(DATA_DIR, "Loading_Ports_Country_Map.csv"),
    "port_details": os.path.join(DATA_DIR, "Port_Details.csv"),
    "producers_sellers": os.path.join(DATA_DIR, "Producers_Sellers_table.csv")
}

# ------------------------------------------------------------------------------
# DATA LOADING FUNCTIONS
# ------------------------------------------------------------------------------
def load_csv_data(file_path, fallback_data=None, **read_kwargs):
    """Load CSV data with fallback to sample data if file not found."""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return fallback_data
    
    if "encoding" in read_kwargs:
        encodings_to_try = [read_kwargs.pop("encoding")]
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
            print(f"❌ Error loading {file_path} with encoding {enc}: {e}")
            return fallback_data
    
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
    """Load Mars Blend Assay data."""
    df = load_csv_data(CSV_PATHS["mars_assay"])
    if df is None or df.empty:
        return [
            {"Property": "Barrels", "Unit": "Per Metric Ton", "Value": "7.13"},
            {"Property": "Gravity", "Unit": "API at 60 F", "Value": "28.51"},
            {"Property": "Mercaptan Sulfur", "Unit": "ppm", "Value": "28.00"},
            {"Property": "Micro Carbon Residue", "Unit": "% Wt", "Value": "6.52"},
            {"Property": "Nickel", "Unit": "ppm", "Value": "22.13"},
            {"Property": "Pour Point", "Unit": "Temp. C", "Value": "-33.00"},
            {"Property": "Reid Vapor Pressure", "Unit": "psi at 37.8 C", "Value": "6.66"},
            {"Property": "Sulfur Content", "Unit": "% Wt", "Value": "2.21"},
            {"Property": "Total Acid Number", "Unit": "Mg KOH/g", "Value": "0.46"},
            {"Property": "Vanadium", "Unit": "ppm", "Value": "62.24"},
            {"Property": "Viscosity", "Unit": "cSt at 20 C", "Value": "28.88"},
        ]
    
    assay_data = []
    for _, row in df.iterrows():
        assay_data.append({
            "Property": row.get("Property", ""),
            "Unit": row.get("Unit", ""),
            "Value": row.get("Value", "")
        })
    return assay_data

def load_refined_products():
    """Load refined products breakdown data."""
    fallback = [
        ("Heavy Gasoil", "300-350", [
            ("Yield Volume", "%", "7.80"),
            ("Yield Weight", "%", "7.74"),
            ("Pour Point", "Temp. C", "-6.83"),
            ("Sulfur Content", "% Wt", "1.57"),
        ])
    ]
    
    df = load_csv_data(CSV_PATHS["refined_products"], header=2)
    if df is None or df.empty or "Product" not in df.columns:
        return fallback
    
    df = df.dropna(how="all")
    df["Product"] = df["Product"].ffill()
    if "Cut Points (ºC)" in df.columns:
        df["Cut Points (ºC)"] = df["Cut Points (ºC)"].ffill()
        cut_col = "Cut Points (ºC)"
    else:
        df["Cut Points (°C)"] = df.get("Cut Points (°C)", "").ffill()
        cut_col = "Cut Points (°C)"
    
    df["Value"] = df["Value"].astype(str).str.strip()
    
    def parse_property_unit(prop_raw, unit_raw):
        prop = str(prop_raw).strip() if prop_raw is not None else ""
        unit = str(unit_raw).strip() if unit_raw is not None else ""
        if prop:
            return prop, unit
        if unit:
            match = re.match(r"^(?P<name>.+?)\s*\((?P<unit>.+)\)$", unit)
            if match:
                return match.group("name").strip(), match.group("unit").strip()
            return unit, ""
        return "", ""
    
    products_data = []
    current_product = None
    current_cut_points = None
    current_properties = []
    
    for _, row in df.iterrows():
        product = str(row.get("Product", "")).strip()
        cut_points = str(row.get(cut_col, "")).strip()
        property_name, unit = parse_property_unit(row.get("Property"), row.get("Unit"))
        value = row.get("Value", "")
        
        if product and product != current_product:
            if current_product and current_properties:
                products_data.append((current_product, current_cut_points, current_properties))
            current_product = product
            current_cut_points = cut_points
            current_properties = []
        
        if property_name:
            current_properties.append((property_name, unit, value))
    
    if current_product and current_properties:
        products_data.append((current_product, current_cut_points, current_properties))
    
    return products_data or fallback

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
    
    df = load_csv_data(CSV_PATHS["port_details"], header=2)
    if df is None or df.empty or "Measure" not in df.columns:
        return {"label": fallback_label, "rows": fallback_rows}
    
    value_columns = [col for col in df.columns if col != "Measure"]
    if not value_columns:
        return {"label": fallback_label, "rows": fallback_rows}
    value_col = value_columns[0]
    column_label = value_col
    
    df[value_col] = df[value_col].fillna("").astype(str).str.strip()
    
    port_details = []
    for _, row in df.iterrows():
        measure = str(row.get("Measure", "")).strip()
        value = str(row.get(value_col, "")).strip()
        if measure:
            port_details.append((measure, value if value else ""))
    
    has_real_value = any(val for _, val in port_details)
    rows = port_details if has_real_value else fallback_rows
    label = column_label if has_real_value else fallback_label
    
    return {
        "label": label,
        "rows": rows
    }

def load_loading_ports():
    """Load loading ports data for the map."""
    fallback = [{
        "port": "Loop, Clovelly",
        "country": "United States",
        "latitude": 29.1175,
        "longitude": -90.0715
    }]
    
    df = load_csv_data(
        CSV_PATHS["loading_ports"],
        encoding="utf-16",
        sep="\t"
    )
    if df is None or df.empty:
        return fallback
    
    df["Latitude"] = pd.to_numeric(df.get("Latitude"), errors="coerce")
    df["Longitude"] = pd.to_numeric(df.get("Longitude"), errors="coerce")
    df["Port Name"] = df.get("Port Name", "").fillna("").astype(str).str.strip()
    df["Country"] = df.get("Country", "").fillna("").astype(str).str.strip()
    
    records = []
    for _, row in df.iterrows():
        lat = row.get("Latitude")
        lon = row.get("Longitude")
        name = row.get("Port Name", "")
        if pd.notna(lat) and pd.notna(lon) and name:
            records.append({
                "port": name,
                "country": row.get("Country", ""),
                "latitude": lat,
                "longitude": lon
            })
    
    return records or fallback

def load_producers_sellers():
    """Load producers and sellers data."""
    fallback = [("BP, ConocoPhillips, Exxon Mobil, Shell", "BP America Inc., ConocoPhillips, Exxon Mobil, Shell")]
    
    df = load_csv_data(CSV_PATHS["producers_sellers"], header=2)
    if df is None or df.empty or "Producers" not in df.columns:
        return fallback
    
    records = []
    for _, row in df.iterrows():
        producers = str(row.get("Producers", "")).strip()
        sellers = str(row.get("Sellers", "")).strip()
        if producers or sellers:
            records.append((producers, sellers))
    
    return records or fallback

# ------------------------------------------------------------------------------
# SORTING FUNCTIONS
# ------------------------------------------------------------------------------
def sort_assay_data_by_maximum_value(data, direction='desc'):
    """Sort assay data by maximum value across all properties"""
    if not data:
        return data
    
    df = pd.DataFrame(data)
    
    # Calculate maximum value for each row
    def get_max_value(row):
        try:
            val = str(row['Value']).replace(',', '')
            return float(val)
        except (ValueError, TypeError):
            return 0
    
    df['_max_value'] = df.apply(get_max_value, axis=1)
    
    # Sort by maximum value
    ascending = (direction == 'asc')
    df_sorted = df.sort_values('_max_value', ascending=ascending)
    df_sorted = df_sorted.drop('_max_value', axis=1)
    
    return df_sorted.to_dict('records')

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
    """Create loading ports map chart using dynamic data."""
    ports_data = load_loading_ports()
    fig = go.Figure()
    
    if not ports_data:
        # Return empty figure if no data
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=0, b=0),
            geo=dict(
                projection_type="natural earth",
                showland=True,
                landcolor="rgb(243, 243, 243)",
                showocean=True,
                oceancolor="rgb(230, 245, 255)"
            )
        )
        return fig
    
    # Extract coordinates
    lats = [port.get('latitude') for port in ports_data if port.get('latitude')]
    lons = [port.get('longitude') for port in ports_data if port.get('longitude')]
    port_names = [port.get('port', '') for port in ports_data]
    
    if lats and lons:
        # Add scattergeo trace for ports
        fig.add_trace(go.Scattergeo(
            lon=lons,
            lat=lats,
            text=port_names,
            mode='markers',
            marker=dict(
                size=10,
                color='#d65a00',
                symbol='circle',
                line=dict(width=1, color='white')
            ),
            name='Loading Ports'
        ))
        
        # Calculate map bounds
        lat_min, lat_max = min(lats), max(lats)
        lon_min, lon_max = min(lons), max(lons)
        lat_padding = (lat_max - lat_min) * 0.2 if (lat_max - lat_min) > 0 else 5
        lon_padding = (lon_max - lon_min) * 0.2 if (lon_max - lon_min) > 0 else 5
        
        fig.update_geos(
            projection_type="natural earth",
            showland=True,
            landcolor="rgb(243, 243, 243)",
            showocean=True,
            oceancolor="rgb(230, 245, 255)",
            lataxis=dict(range=[lat_min - lat_padding, lat_max + lat_padding]),
            lonaxis=dict(range=[lon_min - lon_padding, lon_max + lon_padding]),
            showcountries=True,
            countrycolor="rgb(200, 200, 200)"
        )
    else:
        # Default world view if no valid coordinates
        fig.update_geos(
            projection_type="natural earth",
            showland=True,
            landcolor="rgb(243, 243, 243)",
            showocean=True,
            oceancolor="rgb(230, 245, 255)"
        )
    
    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False
    )
    
    return fig

def create_refined_products_table():
    """Create the Refined Products Breakdown & Properties table as DataTable."""
    refined_products = load_refined_products()
    
    # Convert nested structure to flat rows
    table_data = []
    for product, cut_points, properties in refined_products:
        for prop in properties:
            table_data.append({
                "Product": product,
                "Cut Points (°C)": cut_points,
                "Property": prop[0],
                "Unit": prop[1],
                "Value": prop[2]
            })
    
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
            "fontFamily": "Arial, sans-serif"
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
        css=[
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
            # A-Z vertical text for sort order - HIDDEN BY DEFAULT (Product)
            {
                'selector': '.dash-header[data-dash-column="Product"] .sort-order-container',
                'rule': '''
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
                    transition: opacity 0.2s ease;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Product"]:hover .sort-order-container',
                'rule': '''
                    opacity: 1;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Product"] .sort-order-container:hover',
                'rule': '''
                    background-color: #e6f3ff;
                    border-color: #1f3263;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Product"] .sort-asc',
                'rule': '''
                    display: block;
                    line-height: 1;
                    cursor: pointer;
                    padding: 1px 2px;
                    border-radius: 1px;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Product"] .sort-asc:hover',
                'rule': '''
                    background-color: #d4e7ff;
                    font-weight: bold;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Product"] .sort-desc',
                'rule': '''
                    display: block;
                    line-height: 1;
                    cursor: pointer;
                    padding: 1px 2px;
                    border-radius: 1px;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Product"] .sort-desc:hover',
                'rule': '''
                    background-color: #d4e7ff;
                    font-weight: bold;
                '''
            },
            # A-Z vertical text for sort order - HIDDEN BY DEFAULT (Cut Points)
            {
                'selector': '.dash-header[data-dash-column="Cut Points (°C)"] .sort-order-container',
                'rule': '''
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
                    transition: opacity 0.2s ease;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Cut Points (°C)"]:hover .sort-order-container',
                'rule': '''
                    opacity: 1;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Cut Points (°C)"] .sort-order-container:hover',
                'rule': '''
                    background-color: #e6f3ff;
                    border-color: #1f3263;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Cut Points (°C)"] .sort-asc',
                'rule': '''
                    display: block;
                    line-height: 1;
                    cursor: pointer;
                    padding: 1px 2px;
                    border-radius: 1px;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Cut Points (°C)"] .sort-asc:hover',
                'rule': '''
                    background-color: #d4e7ff;
                    font-weight: bold;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Cut Points (°C)"] .sort-desc',
                'rule': '''
                    display: block;
                    line-height: 1;
                    cursor: pointer;
                    padding: 1px 2px;
                    border-radius: 1px;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Cut Points (°C)"] .sort-desc:hover',
                'rule': '''
                    background-color: #d4e7ff;
                    font-weight: bold;
                '''
            },
            # A-Z vertical text for sort order - HIDDEN BY DEFAULT (Property)
            {
                'selector': '.dash-header[data-dash-column="Property"] .sort-order-container',
                'rule': '''
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
                    transition: opacity 0.2s ease;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Property"]:hover .sort-order-container',
                'rule': '''
                    opacity: 1;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Property"] .sort-order-container:hover',
                'rule': '''
                    background-color: #e6f3ff;
                    border-color: #1f3263;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Property"] .sort-asc',
                'rule': '''
                    display: block;
                    line-height: 1;
                    cursor: pointer;
                    padding: 1px 2px;
                    border-radius: 1px;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Property"] .sort-asc:hover',
                'rule': '''
                    background-color: #d4e7ff;
                    font-weight: bold;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Property"] .sort-desc',
                'rule': '''
                    display: block;
                    line-height: 1;
                    cursor: pointer;
                    padding: 1px 2px;
                    border-radius: 1px;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Property"] .sort-desc:hover',
                'rule': '''
                    background-color: #d4e7ff;
                    font-weight: bold;
                '''
            },
            # A-Z vertical text for sort order - HIDDEN BY DEFAULT (Unit)
            {
                'selector': '.dash-header[data-dash-column="Unit"] .sort-order-container',
                'rule': '''
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
                    transition: opacity 0.2s ease;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Unit"]:hover .sort-order-container',
                'rule': '''
                    opacity: 1;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Unit"] .sort-order-container:hover',
                'rule': '''
                    background-color: #e6f3ff;
                    border-color: #1f3263;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Unit"] .sort-asc',
                'rule': '''
                    display: block;
                    line-height: 1;
                    cursor: pointer;
                    padding: 1px 2px;
                    border-radius: 1px;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Unit"] .sort-asc:hover',
                'rule': '''
                    background-color: #d4e7ff;
                    font-weight: bold;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Unit"] .sort-desc',
                'rule': '''
                    display: block;
                    line-height: 1;
                    cursor: pointer;
                    padding: 1px 2px;
                    border-radius: 1px;
                '''
            },
            {
                'selector': '.dash-header[data-dash-column="Unit"] .sort-desc:hover',
                'rule': '''
                    background-color: #d4e7ff;
                    font-weight: bold;
                '''
            },
        ],
        markdown_options={"html": True},
        editable=False,
        sort_action="none",
        filter_action="none",
        page_action="none",
        style_data_conditional=[
            {
                "if": {"column_id": "Product"},
                "fontWeight": "bold"
            }
        ]
    )

# ------------------------------------------------------------------------------
# INITIAL LOAD
# ------------------------------------------------------------------------------
assay_data = load_mars_assay()

# Load refined products data for initial store
refined_products_data = []
for product, cut_points, properties in load_refined_products():
    for prop in properties:
        refined_products_data.append({
            "Product": product,
            "Cut Points (°C)": cut_points,
            "Property": prop[0],
            "Unit": prop[1],
            "Value": prop[2]
        })

# ------------------------------------------------------------------------------
# LAYOUT
# ------------------------------------------------------------------------------
def create_layout(server=None):
    """Layout with completely separate sorting functionality for both tables."""
    
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
        # CSS Styles
        html.Div(style={"display": "none"}, children=[
            dcc.Markdown("""
                <style>
                /* Sort indicator icon styles for ALL headers */
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
                /* Specific styles for Property and Unit headers */
                .dash-header[data-dash-column="Property"] .sort-order-container,
                .dash-header[data-dash-column="Unit"] .sort-order-container,
                .dash-header[data-dash-column="Product"] .sort-order-container,
                .dash-header[data-dash-column="Cut Points (°C)"] .sort-order-container {
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
                    transition: opacity 0.2s ease;
                }
                .dash-header[data-dash-column="Property"]:hover .sort-order-container,
                .dash-header[data-dash-column="Unit"]:hover .sort-order-container,
                .dash-header[data-dash-column="Product"]:hover .sort-order-container,
                .dash-header[data-dash-column="Cut Points (°C)"]:hover .sort-order-container {
                    opacity: 1;
                }
                .dash-header[data-dash-column="Property"] .sort-order-container:hover,
                .dash-header[data-dash-column="Unit"] .sort-order-container:hover,
                .dash-header[data-dash-column="Product"] .sort-order-container:hover,
                .dash-header[data-dash-column="Cut Points (°C)"] .sort-order-container:hover {
                    background-color: #e6f3ff;
                    border-color: #1f3263;
                }
                .dash-header[data-dash-column="Property"] .sort-asc,
                .dash-header[data-dash-column="Property"] .sort-desc,
                .dash-header[data-dash-column="Unit"] .sort-asc,
                .dash-header[data-dash-column="Unit"] .sort-desc,
                .dash-header[data-dash-column="Product"] .sort-asc,
                .dash-header[data-dash-column="Product"] .sort-desc,
                .dash-header[data-dash-column="Cut Points (°C)"] .sort-asc,
                .dash-header[data-dash-column="Cut Points (°C)"] .sort-desc {
                    display: block;
                    line-height: 1;
                    cursor: pointer;
                    padding: 1px 2px;
                    border-radius: 1px;
                }
                .dash-header[data-dash-column="Property"] .sort-asc:hover,
                .dash-header[data-dash-column="Property"] .sort-desc:hover,
                .dash-header[data-dash-column="Unit"] .sort-asc:hover,
                .dash-header[data-dash-column="Unit"] .sort-desc:hover,
                .dash-header[data-dash-column="Product"] .sort-asc:hover,
                .dash-header[data-dash-column="Product"] .sort-desc:hover,
                .dash-header[data-dash-column="Cut Points (°C)"] .sort-asc:hover,
                .dash-header[data-dash-column="Cut Points (°C)"] .sort-desc:hover {
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
        
        html.Div(id='assay-dummy-output', style={'display': 'none'}),
        html.Div(id='assay-dummy-output-2', style={'display': 'none'}),
        html.Div(id='refined-dummy-output', style={'display': 'none'}),
        html.Div(id='refined-dummy-output-2', style={'display': 'none'}),
        html.Div(id='port-dummy-output', style={'display': 'none'}),
        html.Div(id='port-dummy-output-2', style={'display': 'none'}),
        
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
                # "left": "2684px",
                # "right": "50px",
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
                dash_table.DataTable(
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
                            "borderRight": "1px solid #d0d0d0",
                            "paddingLeft": "12px",
                            "paddingRight": "12px",
                            "color": "#1f3263",
                        },
                        {
                            "if": {"column_id": "Property", "header": True},
                            "textAlign": "left",
                            "color": "#1f3263",
                            "position": "relative",
                        },
                        {
                            "if": {"column_id": "Unit"},
                            "textAlign": "left",
                            "minWidth": "120px",
                            "backgroundColor": "#FFFFFF",
                        },
                        {
                            "if": {"column_id": "Unit", "header": True},
                            "textAlign": "left",
                            "color": "#1f3263",
                            "position": "relative",
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
                        # Property column data - dark blue
                        {
                            "if": {"column_id": "Property"},
                            "color": "#1f3263",
                            "backgroundColor": "#FFFFFF",
                        },
                        # Unit column data - dark gray/black
                        {
                            "if": {"column_id": "Unit"},
                            "color": "#333333",
                            "textAlign": "left",
                        },
                        # Value column data - dark gray/black
                        {
                            "if": {"column_id": "Value"},
                            "color": "#333333",
                            "textAlign": "left",
                        },
                    ],
                    css=[
                        {
                            'selector': '.dash-header[data-dash-column="Property"]',
                            'rule': '''
                                color: #1f3263 !important;
                                position: relative !important;
                                text-align: left !important;
                            '''
                        },
                        {
                            'selector': '.dash-header[data-dash-column="Unit"]',
                            'rule': '''
                                color: #1f3263 !important;
                                position: relative !important;
                                text-align: left !important;
                            '''
                        },
                        # A-Z vertical text for sort order - HIDDEN BY DEFAULT (Property)
                        {
                            'selector': '.dash-header[data-dash-column="Property"] .sort-order-container',
                            'rule': '''
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
                                transition: opacity 0.2s ease;
                            '''
                        },
                        {
                            'selector': '.dash-header[data-dash-column="Property"]:hover .sort-order-container',
                            'rule': '''
                                opacity: 1;
                            '''
                        },
                        {
                            'selector': '.dash-header[data-dash-column="Property"] .sort-order-container:hover',
                            'rule': '''
                                background-color: #e6f3ff;
                                border-color: #1f3263;
                            '''
                        },
                        {
                            'selector': '.dash-header[data-dash-column="Property"] .sort-asc',
                            'rule': '''
                                display: block;
                                line-height: 1;
                                cursor: pointer;
                                padding: 1px 2px;
                                border-radius: 1px;
                            '''
                        },
                        {
                            'selector': '.dash-header[data-dash-column="Property"] .sort-asc:hover',
                            'rule': '''
                                background-color: #d4e7ff;
                                font-weight: bold;
                            '''
                        },
                        {
                            'selector': '.dash-header[data-dash-column="Property"] .sort-desc',
                            'rule': '''
                                display: block;
                                line-height: 1;
                                cursor: pointer;
                                padding: 1px 2px;
                                border-radius: 1px;
                            '''
                        },
                        {
                            'selector': '.dash-header[data-dash-column="Property"] .sort-desc:hover',
                            'rule': '''
                                background-color: #d4e7ff;
                                font-weight: bold;
                            '''
                        },
                        # A-Z vertical text for sort order - HIDDEN BY DEFAULT (Unit)
                        {
                            'selector': '.dash-header[data-dash-column="Unit"] .sort-order-container',
                            'rule': '''
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
                                transition: opacity 0.2s ease;
                            '''
                        },
                        {
                            'selector': '.dash-header[data-dash-column="Unit"]:hover .sort-order-container',
                            'rule': '''
                                opacity: 1;
                            '''
                        },
                        {
                            'selector': '.dash-header[data-dash-column="Unit"] .sort-order-container:hover',
                            'rule': '''
                                background-color: #e6f3ff;
                                border-color: #1f3263;
                            '''
                        },
                        {
                            'selector': '.dash-header[data-dash-column="Unit"] .sort-asc',
                            'rule': '''
                                display: block;
                                line-height: 1;
                                cursor: pointer;
                                padding: 1px 2px;
                                border-radius: 1px;
                            '''
                        },
                        {
                            'selector': '.dash-header[data-dash-column="Unit"] .sort-asc:hover',
                            'rule': '''
                                background-color: #d4e7ff;
                                font-weight: bold;
                            '''
                        },
                        {
                            'selector': '.dash-header[data-dash-column="Unit"] .sort-desc',
                            'rule': '''
                                display: block;
                                line-height: 1;
                                cursor: pointer;
                                padding: 1px 2px;
                                border-radius: 1px;
                            '''
                        },
                        {
                            'selector': '.dash-header[data-dash-column="Unit"] .sort-desc:hover',
                            'rule': '''
                                background-color: #d4e7ff;
                                font-weight: bold;
                            '''
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
                    fixed_rows={"headers": True},
                    page_action="none",
                    sort_action="none",
                    filter_action="none",
                    markdown_options={"html": True},
                )
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
                create_refined_products_table()
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
                    dcc.Graph(figure=map_fig, config={"displayModeBar": False})
                ]),
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
                        "rule": "display: flex; flex-direction: column; position: absolute; right: 30px; top: 50%; transform: translateY(-50%); opacity: 0; transition: opacity 0.2s;"
                    },
                    {
                        "selector": ".dash-header[data-dash-column='Measure'] .sort-indicator",
                        "rule": "position: absolute; right: 5px; top: 50%; transform: translateY(-50%); opacity: 0; transition: opacity 0.2s; cursor: pointer; width: 16px; height: 16px;"
                    },
                    {
                        "selector": ".dash-header[data-dash-column='Measure']:hover .sort-order-container",
                        "rule": "opacity: 1 !important;"
                    },
                    {
                        "selector": ".dash-header[data-dash-column='Measure']:hover .sort-indicator",
                        "rule": "opacity: 1 !important;"
                    },
                    {
                        "selector": ".dash-header[data-dash-column='Measure'] .sort-asc, .dash-header[data-dash-column='Measure'] .sort-desc",
                        "rule": "cursor: pointer; padding: 2px 4px; font-size: 11px; font-weight: bold; color: #333;"
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
    """Register callbacks for the dashboard with completely separate sorting for both tables"""
    
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

    # ==========================================================================
    # PORT DETAILS TABLE CALLBACKS
    # ==========================================================================
    
    @app.callback(
        [Output("port-measure-sorting-controls", "style"),
         Output('port-current-sort-order', 'data', allow_duplicate=True),
         Output('port-show-sorting-controls', 'data', allow_duplicate=True)],
        [Input('port-measure-sort-asc-btn', 'n_clicks'),
         Input('port-measure-sort-desc-btn', 'n_clicks'),
         Input('port-measure-popup-menu-btn', 'n_clicks'),
         Input('port-measure-popup-source-btn', 'n_clicks'),
         Input('port-measure-popup-alphabetic-btn', 'n_clicks'),
         Input('port-measure-popup-field-btn', 'n_clicks'),
         Input('port-measure-popup-nested-btn', 'n_clicks')],
        [State('port-current-sort-order', 'data'),
         State('port-show-sorting-controls', 'data')],
        prevent_initial_call=True
    )
    def handle_port_sorting_interactions(asc_clicks, desc_clicks, popup_clicks, source_clicks, 
                                         alpha_clicks, field_clicks, nested_clicks,
                                         current_sort, show_controls):
        trigger = ctx.triggered_id
        if not trigger:
            return no_update, no_update, no_update
        
        popup_style_hidden = {"display": "none", "position": "absolute", "backgroundColor": "white", 
                              "padding": "4px 0", "boxShadow": "0 2px 10px rgba(0,0,0,0.1)", 
                              "zIndex": "1000", "minWidth": "160px", "border": "1px solid #ddd", 
                              "borderRadius": "4px"}
        popup_style_visible = {"display": "block", "position": "absolute", "backgroundColor": "white", 
                              "padding": "4px 0", "boxShadow": "0 2px 10px rgba(0,0,0,0.1)", 
                              "zIndex": "1000", "minWidth": "160px", "border": "1px solid #ddd", 
                              "borderRadius": "4px"}
        
        if trigger == 'port-measure-popup-menu-btn':
            if show_controls and show_controls.get('header') == 'Measure':
                return popup_style_hidden, no_update, {'header': None}
            else:
                return popup_style_visible, no_update, {'header': 'Measure'}
        elif trigger in ['port-measure-popup-source-btn', 'port-measure-popup-alphabetic-btn',
                        'port-measure-popup-field-btn', 'port-measure-popup-nested-btn']:
            sort_type = 'source' if trigger == 'port-measure-popup-source-btn' else \
                       'alphabetic' if trigger == 'port-measure-popup-alphabetic-btn' else \
                       'field' if trigger == 'port-measure-popup-field-btn' else 'nested'
            return popup_style_hidden, {'column': 'Measure', 'type': sort_type, 'direction': 'asc'}, {'header': None}
        elif trigger in ['port-measure-sort-asc-btn', 'port-measure-sort-desc-btn']:
            direction = 'asc' if trigger == 'port-measure-sort-asc-btn' else 'desc'
            current_type = current_sort.get('type', 'source') if current_sort else 'source'
            return popup_style_hidden, {'column': 'Measure', 'type': current_type, 'direction': direction}, {'header': None}
        
        return no_update, no_update, no_update
    
    @app.callback(
        Output('port-details-table', 'data', allow_duplicate=True),
        Input('port-current-sort-order', 'data'),
        State('port-original-data', 'data'),
        prevent_initial_call=True
    )
    def apply_port_sort_order(sort_order, original_data):
        if not sort_order or not original_data:
            return no_update
        
        column = sort_order.get('column')
        sort_type = sort_order.get('type', 'source')
        direction = sort_order.get('direction', 'asc')
        
        if not column or column != 'Measure':
            return no_update
        
        sorted_data = original_data.copy()
        
        if sort_type == 'source':
            # Return original order
            pass
        elif sort_type == 'alphabetic':
            sorted_data.sort(key=lambda x: str(x.get('Measure', '')).lower(), reverse=(direction == 'desc'))
        elif sort_type == 'field':
            # Sort by numeric value if available
            def get_numeric_value(row):
                val = str(row.get('Measure', '')).strip()
                try:
                    return float(re.sub(r'[^\d.]', '', val))
                except:
                    return float('inf')
            sorted_data.sort(key=get_numeric_value, reverse=(direction == 'desc'))
        elif sort_type == 'nested':
            # Similar to field but with different logic if needed
            sorted_data.sort(key=lambda x: str(x.get('Measure', '')).lower(), reverse=(direction == 'desc'))
        
        return sorted_data

    # ==========================================================================
    # CLIENT-SIDE CALLBACKS FOR ALL TABLES
    # ==========================================================================
    
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
                        
                        const aElement = document.createElement('div');
                        aElement.className = 'sort-asc';
                        aElement.textContent = 'A';
                        aElement.title = 'Click for ascending alphabetical order';
                        aElement.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById(ascBtnId);
                            if (btn) btn.click();
                        };
                        
                        const zElement = document.createElement('div');
                        zElement.className = 'sort-desc';
                        zElement.textContent = 'Z';
                        zElement.title = 'Click for descending alphabetical order';
                        zElement.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById(descBtnId);
                            if (btn) btn.click();
                        };
                        
                        sortContainer.appendChild(aElement);
                        sortContainer.appendChild(zElement);
                        
                        // Add SVG sort icon
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
                            const btn = document.getElementById(popupBtnId);
                            if (btn) btn.click();
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
                        
                        // Add hover handlers to show AVG(Value) text box
                        propFieldItem.addEventListener('mouseenter', function(e) {
                            const textBox = document.getElementById('assay-avg-text-box');
                            if (textBox) {
                                const rect = propFieldItem.getBoundingClientRect();
                                textBox.style.display = 'block';
                                textBox.style.top = (rect.top + window.scrollY) + 'px';
                                textBox.style.left = (rect.right + window.scrollX + 5) + 'px';
                            }
                        });
                        propFieldItem.addEventListener('mouseleave', function(e) {
                            setTimeout(function() {
                                const textBox = document.getElementById('assay-avg-text-box');
                                if (textBox && !textBox.matches(':hover')) {
                                    textBox.style.display = 'none';
                                }
                            }, 100);
                        });
                    }
                    if (propNestedItem) {
                        propNestedItem.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById('assay-property-popup-nested-btn');
                            if (btn) btn.click();
                        };
                        
                        // Add hover handlers to show AVG(Value) text box
                        propNestedItem.addEventListener('mouseenter', function(e) {
                            const textBox = document.getElementById('assay-avg-text-box');
                            if (textBox) {
                                const rect = propNestedItem.getBoundingClientRect();
                                textBox.style.display = 'block';
                                textBox.style.top = (rect.top + window.scrollY) + 'px';
                                textBox.style.left = (rect.right + window.scrollX + 5) + 'px';
                            }
                        });
                        propNestedItem.addEventListener('mouseleave', function(e) {
                            setTimeout(function() {
                                const textBox = document.getElementById('assay-avg-text-box');
                                if (textBox && !textBox.matches(':hover')) {
                                    textBox.style.display = 'none';
                                }
                            }, 100);
                        });
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
                        
                        // Add hover handlers to show AVG(Value) text box
                        unitFieldItem.addEventListener('mouseenter', function(e) {
                            const textBox = document.getElementById('assay-avg-text-box');
                            if (textBox) {
                                const rect = unitFieldItem.getBoundingClientRect();
                                textBox.style.display = 'block';
                                textBox.style.top = (rect.top + window.scrollY) + 'px';
                                textBox.style.left = (rect.right + window.scrollX + 5) + 'px';
                            }
                        });
                        unitFieldItem.addEventListener('mouseleave', function(e) {
                            setTimeout(function() {
                                const textBox = document.getElementById('assay-avg-text-box');
                                if (textBox && !textBox.matches(':hover')) {
                                    textBox.style.display = 'none';
                                }
                            }, 100);
                        });
                    }
                    if (unitNestedItem) {
                        unitNestedItem.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById('assay-unit-popup-nested-btn');
                            if (btn) btn.click();
                        };
                        
                        // Add hover handlers to show AVG(Value) text box
                        unitNestedItem.addEventListener('mouseenter', function(e) {
                            const textBox = document.getElementById('assay-avg-text-box');
                            if (textBox) {
                                const rect = unitNestedItem.getBoundingClientRect();
                                textBox.style.display = 'block';
                                textBox.style.top = (rect.top + window.scrollY) + 'px';
                                textBox.style.left = (rect.right + window.scrollX + 5) + 'px';
                            }
                        });
                        unitNestedItem.addEventListener('mouseleave', function(e) {
                            setTimeout(function() {
                                const textBox = document.getElementById('assay-avg-text-box');
                                if (textBox && !textBox.matches(':hover')) {
                                    textBox.style.display = 'none';
                                }
                            }, 100);
                        });
                    }
                }
                
                // Keep text box visible when hovering over it and close popup on click
                const assayTextBox = document.getElementById('assay-avg-text-box');
                if (assayTextBox) {
                    assayTextBox.addEventListener('mouseenter', function(e) {
                        this.style.display = 'block';
                    });
                    
                    assayTextBox.addEventListener('mouseleave', function(e) {
                        this.style.display = 'none';
                    });
                    
                    // Close popup menu when clicking the text box
                    assayTextBox.addEventListener('click', function(e) {
                        e.stopPropagation();
                        // Close Property popup if open
                        const propertyPopup = document.getElementById('assay-property-sorting-controls');
                        if (propertyPopup && (propertyPopup.style.display === 'block' || window.getComputedStyle(propertyPopup).display === 'block')) {
                            const btn = document.getElementById('assay-property-popup-menu-btn');
                            if (btn) btn.click();
                        }
                        // Close Unit popup if open
                        const unitPopup = document.getElementById('assay-unit-sorting-controls');
                        if (unitPopup && (unitPopup.style.display === 'block' || window.getComputedStyle(unitPopup).display === 'block')) {
                            const btn = document.getElementById('assay-unit-popup-menu-btn');
                            if (btn) btn.click();
                        }
                    });
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
                        
                        const aElement = document.createElement('div');
                        aElement.className = 'sort-asc';
                        aElement.textContent = 'A';
                        aElement.title = 'Click for ascending alphabetical order';
                        aElement.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById(ascBtnId);
                            if (btn) btn.click();
                        };
                        
                        const zElement = document.createElement('div');
                        zElement.className = 'sort-desc';
                        zElement.textContent = 'Z';
                        zElement.title = 'Click for descending alphabetical order';
                        zElement.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById(descBtnId);
                            if (btn) btn.click();
                        };
                        
                        sortContainer.appendChild(aElement);
                        sortContainer.appendChild(zElement);
                        
                        // Add SVG sort icon
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
                            const btn = document.getElementById(popupBtnId);
                            if (btn) btn.click();
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
                    const observer = new MutationObserver(function(mutations) {
                        let shouldReinit = false;
                        mutations.forEach(function(mutation) {
                            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                                shouldReinit = true;
                            }
                        });
                        if (shouldReinit) {
                            setTimeout(initializeRefinedHeaders, 100);
                        }
                    });
                    
                    observer.observe(table, {
                        childList: true,
                        subtree: true
                    });
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
                        
                        // Find the arrow element within Field item
                        const productFieldArrow = productFieldItem.querySelector('.refined-product-field-arrow-item');
                        if (productFieldArrow) {
                            // Add hover handlers to arrow to show AVG(Value) text box
                            productFieldArrow.addEventListener('mouseenter', function(e) {
                                const textBox = document.getElementById('refined-avg-text-box');
                                if (textBox) {
                                    const rect = productFieldArrow.getBoundingClientRect();
                                    textBox.style.display = 'block';
                                    textBox.style.top = (rect.top + window.scrollY) + 'px';
                                    textBox.style.left = (rect.right + window.scrollX + 5) + 'px';
                                }
                            });
                            productFieldArrow.addEventListener('mouseleave', function(e) {
                                setTimeout(function() {
                                    const textBox = document.getElementById('refined-avg-text-box');
                                    if (textBox && !textBox.matches(':hover')) {
                                        textBox.style.display = 'none';
                                    }
                                }, 100);
                            });
                        }
                    }
                    if (productNestedItem) {
                        productNestedItem.onclick = function() {
                            const btn = document.getElementById('refined-product-popup-nested-btn');
                            if (btn) btn.click();
                        };
                        
                        // Find the arrow element within Nested item
                        const productNestedArrow = productNestedItem.querySelector('.refined-product-nested-arrow-item');
                        if (productNestedArrow) {
                            // Add hover handlers to arrow to show AVG(Value) text box
                            productNestedArrow.addEventListener('mouseenter', function(e) {
                                const textBox = document.getElementById('refined-avg-text-box');
                                if (textBox) {
                                    const rect = productNestedArrow.getBoundingClientRect();
                                    textBox.style.display = 'block';
                                    textBox.style.top = (rect.top + window.scrollY) + 'px';
                                    textBox.style.left = (rect.right + window.scrollX + 5) + 'px';
                                }
                            });
                            productNestedArrow.addEventListener('mouseleave', function(e) {
                                setTimeout(function() {
                                    const textBox = document.getElementById('refined-avg-text-box');
                                    if (textBox && !textBox.matches(':hover')) {
                                        textBox.style.display = 'none';
                                    }
                                }, 100);
                            });
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
                        
                        // Find the arrow element within Field item
                        const cutPointsFieldArrow = cutPointsFieldItem.querySelector('.refined-cutpoints-field-arrow-item');
                        if (cutPointsFieldArrow) {
                            // Add hover handlers to arrow to show AVG(Value) text box
                            cutPointsFieldArrow.addEventListener('mouseenter', function(e) {
                                const textBox = document.getElementById('refined-avg-text-box');
                                if (textBox) {
                                    const rect = cutPointsFieldArrow.getBoundingClientRect();
                                    textBox.style.display = 'block';
                                    textBox.style.top = (rect.top + window.scrollY) + 'px';
                                    textBox.style.left = (rect.right + window.scrollX + 5) + 'px';
                                }
                            });
                            cutPointsFieldArrow.addEventListener('mouseleave', function(e) {
                                setTimeout(function() {
                                    const textBox = document.getElementById('refined-avg-text-box');
                                    if (textBox && !textBox.matches(':hover')) {
                                        textBox.style.display = 'none';
                                    }
                                }, 100);
                            });
                        }
                    }
                    if (cutPointsNestedItem) {
                        cutPointsNestedItem.onclick = function() {
                            const btn = document.getElementById('refined-cutpoints-popup-nested-btn');
                            if (btn) btn.click();
                        };
                        
                        // Find the arrow element within Nested item
                        const cutPointsNestedArrow = cutPointsNestedItem.querySelector('.refined-cutpoints-nested-arrow-item');
                        if (cutPointsNestedArrow) {
                            // Add hover handlers to arrow to show AVG(Value) text box
                            cutPointsNestedArrow.addEventListener('mouseenter', function(e) {
                                const textBox = document.getElementById('refined-avg-text-box');
                                if (textBox) {
                                    const rect = cutPointsNestedArrow.getBoundingClientRect();
                                    textBox.style.display = 'block';
                                    textBox.style.top = (rect.top + window.scrollY) + 'px';
                                    textBox.style.left = (rect.right + window.scrollX + 5) + 'px';
                                }
                            });
                            cutPointsNestedArrow.addEventListener('mouseleave', function(e) {
                                setTimeout(function() {
                                    const textBox = document.getElementById('refined-avg-text-box');
                                    if (textBox && !textBox.matches(':hover')) {
                                        textBox.style.display = 'none';
                                    }
                                }, 100);
                            });
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
                        
                        // Find the arrow element within Field item
                        const propertyFieldArrow = propertyFieldItem.querySelector('.refined-property-field-arrow-item');
                        if (propertyFieldArrow) {
                            // Add hover handlers to arrow to show AVG(Value) text box
                            propertyFieldArrow.addEventListener('mouseenter', function(e) {
                                const textBox = document.getElementById('refined-avg-text-box');
                                if (textBox) {
                                    const rect = propertyFieldArrow.getBoundingClientRect();
                                    textBox.style.display = 'block';
                                    textBox.style.top = (rect.top + window.scrollY) + 'px';
                                    textBox.style.left = (rect.right + window.scrollX + 5) + 'px';
                                }
                            });
                            propertyFieldArrow.addEventListener('mouseleave', function(e) {
                                setTimeout(function() {
                                    const textBox = document.getElementById('refined-avg-text-box');
                                    if (textBox && !textBox.matches(':hover')) {
                                        textBox.style.display = 'none';
                                    }
                                }, 100);
                            });
                        }
                    }
                    if (propertyNestedItem) {
                        propertyNestedItem.onclick = function() {
                            const btn = document.getElementById('refined-property-popup-nested-btn');
                            if (btn) btn.click();
                        };
                        
                        // Find the arrow element within Nested item
                        const propertyNestedArrow = propertyNestedItem.querySelector('.refined-property-nested-arrow-item');
                        if (propertyNestedArrow) {
                            // Add hover handlers to arrow to show AVG(Value) text box
                            propertyNestedArrow.addEventListener('mouseenter', function(e) {
                                const textBox = document.getElementById('refined-avg-text-box');
                                if (textBox) {
                                    const rect = propertyNestedArrow.getBoundingClientRect();
                                    textBox.style.display = 'block';
                                    textBox.style.top = (rect.top + window.scrollY) + 'px';
                                    textBox.style.left = (rect.right + window.scrollX + 5) + 'px';
                                }
                            });
                            propertyNestedArrow.addEventListener('mouseleave', function(e) {
                                setTimeout(function() {
                                    const textBox = document.getElementById('refined-avg-text-box');
                                    if (textBox && !textBox.matches(':hover')) {
                                        textBox.style.display = 'none';
                                    }
                                }, 100);
                            });
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
                        
                        // Find the arrow element within Field item
                        const unitFieldArrow = unitFieldItem.querySelector('.refined-unit-field-arrow-item');
                        if (unitFieldArrow) {
                            // Add hover handlers to arrow to show AVG(Value) text box
                            unitFieldArrow.addEventListener('mouseenter', function(e) {
                                const textBox = document.getElementById('refined-avg-text-box');
                                if (textBox) {
                                    const rect = unitFieldArrow.getBoundingClientRect();
                                    textBox.style.display = 'block';
                                    textBox.style.top = (rect.top + window.scrollY) + 'px';
                                    textBox.style.left = (rect.right + window.scrollX + 5) + 'px';
                                }
                            });
                            unitFieldArrow.addEventListener('mouseleave', function(e) {
                                setTimeout(function() {
                                    const textBox = document.getElementById('refined-avg-text-box');
                                    if (textBox && !textBox.matches(':hover')) {
                                        textBox.style.display = 'none';
                                    }
                                }, 100);
                            });
                        }
                    }
                    if (unitNestedItem) {
                        unitNestedItem.onclick = function() {
                            const btn = document.getElementById('refined-unit-popup-nested-btn');
                            if (btn) btn.click();
                        };
                        
                        // Find the arrow element within Nested item
                        const unitNestedArrow = unitNestedItem.querySelector('.refined-unit-nested-arrow-item');
                        if (unitNestedArrow) {
                            // Add hover handlers to arrow to show AVG(Value) text box
                            unitNestedArrow.addEventListener('mouseenter', function(e) {
                                const textBox = document.getElementById('refined-avg-text-box');
                                if (textBox) {
                                    const rect = unitNestedArrow.getBoundingClientRect();
                                    textBox.style.display = 'block';
                                    textBox.style.top = (rect.top + window.scrollY) + 'px';
                                    textBox.style.left = (rect.right + window.scrollX + 5) + 'px';
                                }
                            });
                            unitNestedArrow.addEventListener('mouseleave', function(e) {
                                setTimeout(function() {
                                    const textBox = document.getElementById('refined-avg-text-box');
                                    if (textBox && !textBox.matches(':hover')) {
                                        textBox.style.display = 'none';
                                    }
                                }, 100);
                            });
                        }
                    }
                }
                
                // Keep text box visible when hovering over it and close popup on click
                const textBox = document.getElementById('refined-avg-text-box');
                if (textBox) {
                    textBox.addEventListener('mouseenter', function(e) {
                        this.style.display = 'block';
                    });
                    
                    textBox.addEventListener('mouseleave', function(e) {
                        this.style.display = 'none';
                    });
                    
                    // Close popup menu when clicking the text box
                    textBox.addEventListener('click', function(e) {
                        e.stopPropagation();
                        // Close Product popup if open
                        const productPopup = document.getElementById('refined-product-sorting-controls');
                        if (productPopup && (productPopup.style.display === 'block' || window.getComputedStyle(productPopup).display === 'block')) {
                            const btn = document.getElementById('refined-product-popup-menu-btn');
                            if (btn) btn.click();
                        }
                        // Close Cut Points popup if open
                        const cutPointsPopup = document.getElementById('refined-cutpoints-sorting-controls');
                        if (cutPointsPopup && (cutPointsPopup.style.display === 'block' || window.getComputedStyle(cutPointsPopup).display === 'block')) {
                            const btn = document.getElementById('refined-cutpoints-popup-menu-btn');
                            if (btn) btn.click();
                        }
                        // Close Property popup if open
                        const propertyPopup = document.getElementById('refined-property-sorting-controls');
                        if (propertyPopup && (propertyPopup.style.display === 'block' || window.getComputedStyle(propertyPopup).display === 'block')) {
                            const btn = document.getElementById('refined-property-popup-menu-btn');
                            if (btn) btn.click();
                        }
                        // Close Unit popup if open
                        const unitPopup = document.getElementById('refined-unit-sorting-controls');
                        if (unitPopup && (unitPopup.style.display === 'block' || window.getComputedStyle(unitPopup).display === 'block')) {
                            const btn = document.getElementById('refined-unit-popup-menu-btn');
                            if (btn) btn.click();
                        }
                    });
                }
            }, 100);
            return '';
        }
        """,
        Output('refined-dummy-output', 'children'),
        Input('refined-products-table', 'columns'),
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
                        
                        const aElement = document.createElement('div');
                        aElement.className = 'sort-asc';
                        aElement.textContent = 'A';
                        aElement.title = 'Click for ascending alphabetical order';
                        aElement.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById(ascBtnId);
                            if (btn) btn.click();
                        };
                        
                        const zElement = document.createElement('div');
                        zElement.className = 'sort-desc';
                        zElement.textContent = 'Z';
                        zElement.title = 'Click for descending alphabetical order';
                        zElement.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById(descBtnId);
                            if (btn) btn.click();
                        };
                        
                        sortContainer.appendChild(aElement);
                        sortContainer.appendChild(zElement);
                        
                        // Add SVG sort icon
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
                            const btn = document.getElementById(popupBtnId);
                            if (btn) btn.click();
                        };
                        
                        header.appendChild(sortContainer);
                        header.appendChild(sortIndicator);
                    }
                }
                
                // Find Measure header using multiple strategies with retries
                function findPortHeader(columnName) {
                    // Strategy 1: Search within port details table first
                    const table = document.getElementById('port-details-table');
                    if (table) {
                        let header = table.querySelector('.dash-header[data-dash-column="' + columnName + '"]');
                        if (header) return header;
                        
                        // Strategy 2: Search by text content within table
                        const headers = table.querySelectorAll('.dash-header');
                        for (let h of headers) {
                            if (h.textContent && h.textContent.trim().includes(columnName)) {
                                return h;
                            }
                        }
                    }
                    
                    // Strategy 3: Global search
                    let header = document.querySelector('.dash-header[data-dash-column="' + columnName + '"]');
                    if (header) return header;
                    
                    // Strategy 4: Search by text content globally
                    const allHeaders = document.querySelectorAll('.dash-header');
                    for (let h of allHeaders) {
                        if (h.textContent && h.textContent.trim().includes(columnName)) {
                            return h;
                        }
                    }
                    
                    return null;
                }
                
                // Function to initialize Measure header
                function initializePortHeader() {
                    let measureHeader = findPortHeader('Measure');
                    if (measureHeader && !measureHeader.querySelector('.sort-order-container')) {
                        addSortingControls(measureHeader, 'Measure', 
                            'port-measure-sort-asc-btn', 
                            'port-measure-sort-desc-btn',
                            'port-measure-popup-menu-btn');
                    }
                }
                
                // Try to initialize header with multiple retries
                initializePortHeader();
                
                // Retry after delays
                setTimeout(initializePortHeader, 200);
                setTimeout(initializePortHeader, 500);
                setTimeout(initializePortHeader, 1000);
                
                // Use MutationObserver to re-initialize if table is re-rendered
                const table = document.getElementById('port-details-table');
                if (table) {
                    const observer = new MutationObserver(function(mutations) {
                        let shouldReinit = false;
                        for (let mutation of mutations) {
                            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                                shouldReinit = true;
                                break;
                            }
                        }
                        if (shouldReinit) {
                            setTimeout(initializePortHeader, 100);
                            setTimeout(initializePortHeader, 300);
                        }
                    });
                    observer.observe(table, { childList: true, subtree: true });
                }
                
                // Also observe document for table addition
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', function() {
                        setTimeout(initializePortHeader, 100);
                        setTimeout(initializePortHeader, 500);
                    });
                }
                
                // Add click handlers for Measure popup menu items
                const measurePopup = document.getElementById('port-measure-sorting-controls');
                if (measurePopup) {
                    const measureSourceItem = measurePopup.querySelector('.port-measure-popup-source-item');
                    const measureAlphaItem = measurePopup.querySelector('.port-measure-popup-alphabetic-item');
                    const measureFieldItem = measurePopup.querySelector('.port-measure-popup-field-item');
                    const measureNestedItem = measurePopup.querySelector('.port-measure-popup-nested-item');
                    
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
                        
                        // Find the arrow element within Field item
                        const fieldArrow = measureFieldItem.querySelector('.port-measure-field-arrow-item');
                        if (fieldArrow) {
                            // Add hover handlers to arrow to show AVG(Value) text box
                            fieldArrow.addEventListener('mouseenter', function(e) {
                                const textBox = document.getElementById('port-avg-text-box');
                                if (textBox) {
                                    const rect = fieldArrow.getBoundingClientRect();
                                    textBox.style.display = 'block';
                                    textBox.style.top = (rect.top + window.scrollY) + 'px';
                                    textBox.style.left = (rect.right + window.scrollX + 5) + 'px';
                                }
                            });
                            fieldArrow.addEventListener('mouseleave', function(e) {
                                setTimeout(function() {
                                    const textBox = document.getElementById('port-avg-text-box');
                                    if (textBox && !textBox.matches(':hover')) {
                                        textBox.style.display = 'none';
                                    }
                                }, 100);
                            });
                        }
                    }
                    if (measureNestedItem) {
                        measureNestedItem.onclick = function() {
                            const btn = document.getElementById('port-measure-popup-nested-btn');
                            if (btn) btn.click();
                        };
                        
                        // Find the arrow element within Nested item
                        const nestedArrow = measureNestedItem.querySelector('.port-measure-nested-arrow-item');
                        if (nestedArrow) {
                            // Add hover handlers to arrow to show AVG(Value) text box
                            nestedArrow.addEventListener('mouseenter', function(e) {
                                const textBox = document.getElementById('port-avg-text-box');
                                if (textBox) {
                                    const rect = nestedArrow.getBoundingClientRect();
                                    textBox.style.display = 'block';
                                    textBox.style.top = (rect.top + window.scrollY) + 'px';
                                    textBox.style.left = (rect.right + window.scrollX + 5) + 'px';
                                }
                            });
                            nestedArrow.addEventListener('mouseleave', function(e) {
                                setTimeout(function() {
                                    const textBox = document.getElementById('port-avg-text-box');
                                    if (textBox && !textBox.matches(':hover')) {
                                        textBox.style.display = 'none';
                                    }
                                }, 100);
                            });
                        }
                    }
                }
                
                // Keep text box visible when hovering over it and close popup on click
                const portTextBox = document.getElementById('port-avg-text-box');
                if (portTextBox) {
                    portTextBox.addEventListener('mouseenter', function(e) {
                        this.style.display = 'block';
                    });
                    
                    portTextBox.addEventListener('mouseleave', function(e) {
                        this.style.display = 'none';
                    });
                    
                    // Close popup menu when clicking the text box
                    portTextBox.addEventListener('click', function(e) {
                        e.stopPropagation();
                        // Close Measure popup if open
                        const measurePopup = document.getElementById('port-measure-sorting-controls');
                        if (measurePopup && (measurePopup.style.display === 'block' || window.getComputedStyle(measurePopup).display === 'block')) {
                            const btn = document.getElementById('port-measure-popup-menu-btn');
                            if (btn) btn.click();
                        }
                    });
                }
            }, 100);
            return '';
        }
        """,
        Output('port-dummy-output', 'children'),
        [Input('port-details-table', 'columns'),
         Input('port-details-table', 'data')],
        prevent_initial_call=False
    )
    
    # Popup positioning callback for Mars Blend Assay table
    app.clientside_callback(
        """
        function(showControls) {
            if (showControls && showControls.header) {
                setTimeout(function() {
                    const headerName = showControls.header;
                    let popup = null;
                    
                    if (headerName === 'Property') {
                        popup = document.getElementById('assay-property-sorting-controls');
                        if (popup) {
                            // Fixed position for Property popup
                            popup.style.top = '1082px';
                            popup.style.left = '256px';
                        }
                    } else if (headerName === 'Unit') {
                        popup = document.getElementById('assay-unit-sorting-controls');
                        const targetHeader = document.querySelector('.dash-header[data-dash-column="Unit"]');
                        if (popup && targetHeader) {
                            const rect = targetHeader.getBoundingClientRect();
                            const sortIndicator = targetHeader.querySelector('.sort-indicator');
                            
                            if (sortIndicator) {
                                const indicatorRect = sortIndicator.getBoundingClientRect();
                                popup.style.top = (indicatorRect.bottom + window.scrollY + 5) + 'px';
                                popup.style.left = (indicatorRect.left + window.scrollX) + 'px';
                            } else {
                                popup.style.top = (rect.bottom + window.scrollY + 5) + 'px';
                                popup.style.left = (rect.left + window.scrollX) + 'px';
                            }
                        }
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
    
    # Popup positioning callback for Refined Products table
    app.clientside_callback(
        """
        function(showControls) {
            if (showControls && showControls.header) {
                setTimeout(function() {
                    const headerName = showControls.header;
                    let popup = null;
                    let targetHeader = null;
                    
                    if (headerName === 'Product') {
                        popup = document.getElementById('refined-product-sorting-controls');
                        if (popup) {
                            // Fixed position for Product popup
                            popup.style.top = '1075px';
                            popup.style.left = '714px';
                        }
                    } else if (headerName === 'Cut Points') {
                        popup = document.getElementById('refined-cutpoints-sorting-controls');
                        if (popup) {
                            // Fixed position for Cut Points popup
                            popup.style.top = '1075px';
                            popup.style.left = '818px';
                        }
                    } else if (headerName === 'Property') {
                        popup = document.getElementById('refined-property-sorting-controls');
                        targetHeader = document.querySelector('.dash-header[data-dash-column="Property"]');
                        if (popup && targetHeader) {
                            const rect = targetHeader.getBoundingClientRect();
                            const sortIndicator = targetHeader.querySelector('.sort-indicator');
                            
                            // Fixed left position for Property popup
                            popup.style.left = '869px';
                            
                            if (sortIndicator) {
                                const indicatorRect = sortIndicator.getBoundingClientRect();
                                popup.style.top = (indicatorRect.bottom + window.scrollY + 5) + 'px';
                            } else {
                                popup.style.top = (rect.bottom + window.scrollY + 5) + 'px';
                            }
                        }
                    } else if (headerName === 'Unit') {
                        popup = document.getElementById('refined-unit-sorting-controls');
                        targetHeader = document.querySelector('.dash-header[data-dash-column="Unit"]');
                        if (popup && targetHeader) {
                            const rect = targetHeader.getBoundingClientRect();
                            const sortIndicator = targetHeader.querySelector('.sort-indicator');
                            
                            // Fixed left position for Unit popup
                            popup.style.left = '943px';
                            
                            if (sortIndicator) {
                                const indicatorRect = sortIndicator.getBoundingClientRect();
                                popup.style.top = (indicatorRect.bottom + window.scrollY + 5) + 'px';
                            } else {
                                popup.style.top = (rect.bottom + window.scrollY + 5) + 'px';
                            }
                        }
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
    
    # Popup positioning callback for Port Details table
    app.clientside_callback(
        """
        function(showControls) {
            if (showControls && showControls.header) {
                setTimeout(function() {
                    const headerName = showControls.header;
                    let popup = null;
                    let targetHeader = null;
                    
                    if (headerName === 'Measure') {
                        popup = document.getElementById('port-measure-sorting-controls');
                        targetHeader = document.querySelector('.dash-header[data-dash-column="Measure"]');
                        if (popup && targetHeader) {
                            const rect = targetHeader.getBoundingClientRect();
                            const sortIndicator = targetHeader.querySelector('.sort-indicator');
                            
                            if (sortIndicator) {
                                const indicatorRect = sortIndicator.getBoundingClientRect();
                                popup.style.top = (indicatorRect.bottom + window.scrollY + 5) + 'px';
                                popup.style.left = (indicatorRect.left + window.scrollX) + 'px';
                            } else {
                                popup.style.top = (rect.bottom + window.scrollY + 5) + 'px';
                                popup.style.left = (rect.left + window.scrollX) + 'px';
                            }
                        }
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