"""
Crude Profile Dashboard - Complete Implementation
"""
from dash import dcc, html, Dash, Input, Output
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os
import re

# ------------------------------------------------------------------------------
# FILE PATHS
# ------------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data","Crude_Profile")

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
            # {"Property": "", "Unit": "Total", "Value": ""},
            # {"Property": "Gravity", "Unit": "API at 60 F", "Value": "28.51"},
            # {"Property": "Mercaptan Sulfur", "Unit": "ppm", "Value": "28.00"},
            # {"Property": "Micro Carbon Residue", "Unit": "% Wt", "Value": "6.52"},
            # {"Property": "Nickel", "Unit": "ppm", "Value": "22.13"},
            # {"Property": "Pour Point", "Unit": "Temp. C", "Value": "-33.00"},
            # {"Property": "Reid Vapor Pressure", "Unit": "psi at 37.8 C", "Value": "6.66"},
            # {"Property": "Sulfur Content", "Unit": "% Wt", "Value": "2.21"},
            # {"Property": "Total Acid Number", "Unit": "Mg KOH/g", "Value": "0.46"},
            # {"Property": "Vanadium", "Unit": "ppm", "Value": "62.24"},
            # {"Property": "Viscosity", "Unit": "cSt at 20 C", "Value": "28.88"},
            # {"Property": "", "Unit": "cSt at 40 C", "Value": "14.82"},
            # {"Property": "", "Unit": "cSt at 50 C", "Value": "11.23"}
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
        # ("Heavy Naphtha", "100-150", [
        #     ("Yield Volume", "%", "8.44"),
        #     ("Yield Weight", "%", "7.18"),
        #     ("Aromatics", "% Wt", "9.07"),
        #     ("Naphthenes", "% Wt", "33.13"),
        #     ("Paraffins", "% Wt", "57.80"),
        # ]),
        # ("Heavy Residue", ">370", [
        #     ("Yield Volume", "%", "47.77"),
        #     ("Yield Weight", "%", "53.54"),
        #     ("Nickel", "ppm", "41.34"),
        #     ("Pour Point", "Temp. C", "26.64"),
        #     ("Sulfur Content", "% Wt", "3.57"),
        #     ("Vanadium", "ppm", "116.23"),
        # ]),
        # ("Int. Gasoil", "250-300", [
        #     ("Yield Volume", "%", "7.92"),
        #     ("Yield Weight", "%", "7.60"),
        #     ("Cetane Index", "", "51.28"),
        #     ("Cloud Point", "Temp. C", "-25.53"),
        #     ("Sulfur Content", "% Wt", "0.92"),
        # ]),
        # ("Int. Naphtha", "65-100", [
        #     ("Yield Volume", "%", "4.99"),
        #     ("Yield Weight", "%", "3.98"),
        #     ("Aromatics", "% Wt", "1.47"),
        #     ("Naphthenes", "% Wt", "26.11"),
        #     ("Paraffins", "% Wt", "72.42"),
        # ]),
        # ("Kerosene", "150-200", [
        #     ("Yield Volume", "%", "6.44"),
        #     ("Yield Weight", "%", "5.73"),
        #     ("Freeze Point", "Temp. C", "-63.90"),
        #     ("Smoke Point", "mm", "23.20"),
        # ]),
        # ("Light Gasoil", "200-250", [
        #     ("Yield Volume", "%", "7.98"),
        #     ("Yield Weight", "%", "6.83"),
        #     ("Cetane Index", "", "46.98"),
        #     ("Pour Point", "Temp. C", "-54.20"),
        # ]),
        # ("Light Naphtha", "C5-65", [
        #     ("Yield Volume", "%", "4.95"),
        #     ("Yield Weight", "%", "3.19"),
        #     ("Octane", "RON clear", "77.62"),
        # ]),
        # ("Light Residue", "350-370", [
        #     ("Yield Volume", "%", "2.89"),
        #     ("Yield Weight", "%", "2.93"),
        #     ("Viscosity", "cSt at 50 C", "8.95"),
        # ])
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
        # ("Max Draft (meters)", "23.5"),
        # ("Max Length (meters)", "366"),
        # ("Max Loading Rate (bbl/hour)", "80,000"),
        # ("Max Tonnage (dwt)", "250,000"),
        # ("Mooring Type", "Single Point"),
        # ("Storage Capacity (million bbl)", "12.5")
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
        # "country": "United States",
        # "latitude": 29.1175,
        # "longitude": -90.0715
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
# HELPER FUNCTIONS (UPDATED TO USE DYNAMIC DATA)
# ------------------------------------------------------------------------------
def create_assay_table():
    """Create the Mars Blend Assay table with 3 columns using dynamic data."""
    assay_data = load_mars_assay()
    rows = []
    for item in assay_data:
        rows.append(html.Tr([
            html.Td(item["Property"], style={
                "border": "1px solid #ddd",
                "padding": "8px 10px",
                "fontSize": "12px",
                "textAlign": "left"
            }),
            html.Td(item["Unit"], style={
                "border": "1px solid #ddd",
                "padding": "8px 10px",
                "fontSize": "12px",
                "textAlign": "left"
            }),
            html.Td(item["Value"], style={
                "border": "1px solid #ddd",
                "padding": "8px 10px",
                "fontSize": "12px",
                "textAlign": "left"
            })
        ]))
    
    return html.Table(style={
        "width": "100%",
        "borderCollapse": "collapse",
        "marginBottom": "15px",
        "fontFamily": "Arial, sans-serif"
    }, children=[
        html.Thead(html.Tr([
            html.Th("Property", style={
                "border": "1px solid #ddd",
                "padding": "10px",
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "textAlign": "left",
                "fontSize": "12px"
            }),
            html.Th("Unit", style={
                "border": "1px solid #ddd",
                "padding": "10px",
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "textAlign": "left",
                "fontSize": "12px"
            }),
            html.Th("Value", style={
                "border": "1px solid #ddd",
                "padding": "10px",
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "textAlign": "left",
                "fontSize": "12px"
            })
        ])),
        html.Tbody(rows)
    ])

def create_refined_products_table():
    """Create the Refined Products Breakdown & Properties table with 4 columns using dynamic data."""
    refined_products = load_refined_products()
    rows = []
    for product, cut_points, properties in refined_products:
        first_row = True
        for prop in properties:
            if first_row:
                rows.append(html.Tr([
                    html.Td(product, style={
                        "border": "1px solid #ddd",
                        "padding": "8px 10px",
                        "fontWeight": "bold",
                        "verticalAlign": "top",
                        "fontSize": "11px"
                    }, rowSpan=len(properties)),
                    html.Td(cut_points, style={
                        "border": "1px solid #ddd",
                        "padding": "8px 10px", 
                        "verticalAlign": "top",
                        "fontSize": "11px"
                    }, rowSpan=len(properties)),
                    html.Td(prop[0], style={
                        "border": "1px solid #ddd",
                        "padding": "8px 10px",
                        "fontSize": "11px"
                    }),
                    html.Td(prop[1], style={
                        "border": "1px solid #ddd",
                        "padding": "8px 10px",
                        "fontSize": "11px"
                    }),
                    html.Td(prop[2], style={
                        "border": "1px solid #ddd",
                        "padding": "8px 10px",
                        "fontSize": "11px"
                    })
                ]))
                first_row = False
            else:
                rows.append(html.Tr([
                    html.Td(prop[0], style={
                        "border": "1px solid #ddd",
                        "padding": "8px 10px",
                        "fontSize": "11px"
                    }),
                    html.Td(prop[1], style={
                        "border": "1px solid #ddd",
                        "padding": "8px 10px",
                        "fontSize": "11px"
                    }),
                    html.Td(prop[2], style={
                        "border": "1px solid #ddd",
                        "padding": "8px 10px", 
                        "fontSize": "11px"
                    })
                ]))
    
    return html.Table(style={
        "width": "100%",
        "borderCollapse": "collapse",
        "marginBottom": "15px",
        "fontFamily": "Arial, sans-serif"
    }, children=[
        html.Thead(html.Tr([
            html.Th("Product", style={
                "border": "1px solid #ddd",
                "padding": "8px 10px",
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "textAlign": "left",
                "fontSize": "11px"
            }),
            html.Th("Cut Points (°C)", style={
                "border": "1px solid #ddd",
                "padding": "8px 10px",
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "textAlign": "left",
                "fontSize": "11px"
            }),
            html.Th("Property", style={
                "border": "1px solid #ddd",
                "padding": "8px 10px",
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "textAlign": "left",
                "fontSize": "11px"
            }),
            html.Th("Unit", style={
                "border": "1px solid #ddd",
                "padding": "8px 10px",
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "textAlign": "left",
                "fontSize": "11px"
            }),
            html.Th("Value", style={
                "border": "1px solid #ddd",
                "padding": "8px 10px",
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "textAlign": "left",
                "fontSize": "11px"
            })
        ])),
        html.Tbody(rows)
    ])

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
            x=1,
            font=dict(size=11)
        ),
        xaxis=dict(
            tickangle=-45,
            showgrid=True,
            gridcolor='#e0e0e0',
            gridwidth=1,
            tickfont=dict(size=10)
        ),
        yaxis=dict(
            title="Volume ('000 b/d)",
            showgrid=True,
            gridcolor='#e0e0e0',
            gridwidth=1,
            range=[0, y_max],
            dtick=50,
            tickfont=dict(size=10),
            titlefont=dict(size=11)
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Arial', size=11)
    )
    
    return fig

def create_map_chart():
    """Create loading ports map matching the image."""
    ports = load_loading_ports()
    lons = [p["longitude"] for p in ports]
    lats = [p["latitude"] for p in ports]
    labels = [f"{p['port']} ({p['country']})" if p.get("country") else p["port"] for p in ports]
    
    fig = go.Figure()
    fig.add_trace(go.Scattergeo(
        lon=lons,
        lat=lats,
        mode='markers',
        text=labels,
        hoverinfo='text',
        marker=dict(
            size=10,
            color='#d65a00',
            symbol='circle',
            line=dict(width=1, color='#ffffff')
        ),
        name='Loading Ports'
    ))
    
    lon_min = min(lons) if lons else -90
    lon_max = max(lons) if lons else -90
    lat_min = min(lats) if lats else 29
    lat_max = max(lats) if lats else 29
    lon_padding = max(1, (lon_max - lon_min) * 0.1 or 1)
    lat_padding = max(1, (lat_max - lat_min) * 0.1 or 1)
    
    fig.update_geos(
        visible=True,
        resolution=50,
        showcountries=True,
        countrycolor='#cccccc',
        showcoastlines=True,
        coastlinecolor='#cccccc',
        showland=True,
        landcolor='#e6f3e6',
        showocean=True,
        oceancolor='#cce5ff',
        projection_type='natural earth',
        lonaxis_range=[lon_min - lon_padding, lon_max + lon_padding],
        lataxis_range=[lat_min - lat_padding, lat_max + lat_padding]
    )
    
    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=0, b=0),
        geo=dict(
            bgcolor='white'
        )
    )
    
    return fig

# ------------------------------------------------------------------------------
# LAYOUT (UPDATED TO USE DYNAMIC DATA)
# ------------------------------------------------------------------------------
def create_layout(server=None):
    """Layout exactly matching the provided image design with dynamic data."""
    
    # Load dynamic data
    assay_details = load_assay_details()
    quality_specs = load_quality_specs()
    port_details_data = load_port_details()
    port_details_rows = port_details_data.get("rows", [])
    port_details_label = port_details_data.get("label", "Port Details")
    producers_sellers = load_producers_sellers()
    
    production_fig = create_production_chart()
    map_fig = create_map_chart()
    
    return html.Div(style={
        "fontFamily": "Arial, sans-serif",
        "maxWidth": "1200px",
        "margin": "0 auto",
        "padding": "20px",
        "backgroundColor": "white",
        "color": "#333"
    }, children=[
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
        
        # Summary Section - Three parts: Left (Headers + Values), Center (Carbon Intensity), Right (Latest Quality Specs)
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
        
        # Main Grid Layout matching reference design
        html.Div(style={
            "display": "grid",
            "gridTemplateColumns": "3fr 4fr 5fr",
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
                create_refined_products_table()
            ]),
            # Column 3: Right-side stack (Production chart + Loading Ports + Port Details)
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
                html.Table(style={
                    "width": "100%",
                    "borderCollapse": "collapse",
                    "marginBottom": "15px",
                    "fontFamily": "Arial, sans-serif"
                }, children=[
                    html.Thead(html.Tr([
                        html.Th("Measure", style={
                            "border": "1px solid #ddd",
                            "padding": "10px",
                            "backgroundColor": "#f5f5f5",
                            "fontWeight": "bold",
                            "textAlign": "left",
                            "fontSize": "12px"
                        }),
                        html.Th(port_details_label, style={
                            "border": "1px solid #ddd",
                            "padding": "10px",
                            "backgroundColor": "#f5f5f5",
                            "fontWeight": "bold",
                            "textAlign": "left",
                            "fontSize": "12px"
                        })
                    ])),
                    html.Tbody([html.Tr([
                        html.Td(port[0], style={
                            "border": "1px solid #ddd",
                            "padding": "10px",
                            "fontSize": "12px"
                        }),
                        html.Td(port[1], style={
                            "border": "1px solid #ddd",
                            "padding": "10px",
                            "fontSize": "12px"
                        })
                    ]) for port in port_details_rows])
                ])
            ]),
            # Bottom Row spanning first two columns: Sellers and Producers
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
# DASH APP CREATION
# ------------------------------------------------------------------------------
def register_callbacks(dash_app):
    """Register callbacks for the dashboard"""
    @dash_app.callback(
        Output("crude-select", "value"),
        Input("crude-select", "value")
    )
    def update_crude(selected_crude):
        return selected_crude

def create_crude_profile_dashboard(server, url_base_pathname="/dash/crude-profile/"):
    """Create and configure the crude profile dashboard"""
    from app import create_dash_app
    dash_app = create_dash_app(server, url_base_pathname)
    dash_app.layout = create_layout()
    register_callbacks(dash_app)
    return dash_app

# For standalone testing
if __name__ == "__main__":
    app = Dash(__name__)
    app.layout = create_layout()
    app.run_server(debug=True, port=8050)