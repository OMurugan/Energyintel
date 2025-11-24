"""
Crude Profile Dashboard - Complete Implementation
"""
from dash import dcc, html, Dash
import plotly.graph_objects as go
import plotly.express as px

# Static content that matches the provided design EXACTLY
ASSAY_DATA = [
    {"Property": "Barrels", "Unit": "Per Metric Ton", "Value": "7.13"},
    {"Property": "", "Unit": "Total", "Value": ""},
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
    {"Property": "", "Unit": "cSt at 40 C", "Value": "14.82"},
    {"Property": "", "Unit": "cSt at 50 C", "Value": "11.23"}
]

REFINED_PRODUCTS = [
    ("Heavy Gasoil", "300-350", [
        ("Yield Volume", "%", "7.80"),
        ("Yield Weight", "%", "7.74"),
        ("Pour Point", "Temp. C", "-6.83"),
        ("Sulfur Content", "% Wt", "1.57"),
    ]),
    ("Heavy Naphtha", "100-150", [
        ("Yield Volume", "%", "8.44"),
        ("Yield Weight", "%", "7.18"),
        ("Aromatics", "% Wt", "9.07"),
        ("Naphthenes", "% Wt", "33.13"),
        ("Paraffins", "% Wt", "57.80"),
    ]),
    ("Heavy Residue", ">370", [
        ("Yield Volume", "%", "47.77"),
        ("Yield Weight", "%", "53.54"),
        ("Nickel", "ppm", "41.34"),
        ("Pour Point", "Temp. C", "26.64"),
        ("Sulfur Content", "% Wt", "3.57"),
        ("Vanadium", "ppm", "116.23"),
    ]),
    ("Int. Gasoil", "250-300", [
        ("Yield Volume", "%", "7.92"),
        ("Yield Weight", "%", "7.60"),
        ("Cetane Index", "", "51.28"),
        ("Cloud Point", "Temp. C", "-25.53"),
        ("Sulfur Content", "% Wt", "0.92"),
    ]),
    ("Int. Naphtha", "65-100", [
        ("Yield Volume", "%", "4.99"),
        ("Yield Weight", "%", "3.98"),
        ("Aromatics", "% Wt", "1.47"),
        ("Naphthenes", "% Wt", "26.11"),
        ("Paraffins", "% Wt", "72.42"),
    ]),
    ("Kerosene", "150-200", [
        ("Yield Volume", "%", "6.44"),
        ("Yield Weight", "%", "5.73"),
        ("Freeze Point", "Temp. C", "-63.90"),
        ("Smoke Point", "mm", "23.20"),
    ]),
    ("Light Gasoil", "200-250", [
        ("Yield Volume", "%", "7.98"),
        ("Yield Weight", "%", "6.83"),
        ("Cetane Index", "", "46.98"),
        ("Pour Point", "Temp. C", "-54.20"),
    ]),
    ("Light Naphtha", "C5-65", [
        ("Yield Volume", "%", "4.95"),
        ("Yield Weight", "%", "3.19"),
        ("Octane", "RON clear", "77.62"),
    ]),
    ("Light Residue", "350-370", [
        ("Yield Volume", "%", "2.89"),
        ("Yield Weight", "%", "2.93"),
        ("Viscosity", "cSt at 50 C", "8.95"),
    ])
]

QUALITY_SPECS = [
    ("Gravity (API at 60F)", "28.40"),
    ("Sulfur Content (% Wt)", "2.17"),
    ("TAN (mg KOH/g)", "0.48")
]

PRODUCERS_SELLERS = [
    ("BP, ConocoPhillips, Exxon Mobil, Shell", "BP America Inc., ConocoPhillips, Exxon Mobil, Shell")
]

PORT_DETAILS = [
    ("Berths", "4"),
    ("Max Draft (meters)", "23.5"),
    ("Max Length (meters)", "366"),
    ("Max Loading Rate (bbl/hour)", "80,000"),
    ("Max Tonnage (dwt)", "250,000"),
    ("Mooring Type", "Single Point"),
    ("Storage Capacity (million bbl)", "12.5")
]

# ------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------------------
def create_production_chart():
    """Create production and exports chart matching the image design."""
    fig = go.Figure()
    
    years = ['2006', '2007', '2008', '2009', '2010', '2011', '2012', '2013', '2014', 
             '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024']
    
    # Data from the image
    production = [235, 290, 220, 225, 200, 190, 150, 145, 170, 100, 200, 205, 225, 280, 270, 250, 235, 220, 215]
    exports = [5, 5, 5, 5, 5, 5, 5, 5, 75, 65, 50, 75, 115, 170, 110, 150, 160, 160, 115]
    
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
            range=[0, 300],
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
    fig = go.Figure()
    
    fig.add_trace(go.Scattergeo(
        lon=[-90.0715],
        lat=[29.1175],
        mode='markers',
        marker=dict(
            size=20,
            color='orange',
            symbol='circle'
        ),
        text=['Loop, Clovelly'],
        hoverinfo='text'
    ))
    
    fig.update_layout(
        geo=dict(
            scope='north america',
            showland=True,
            landcolor='rgb(243, 243, 243)',
            countrycolor='rgb(204, 204, 204)',
        ),
        height=250,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    
    return fig

def create_assay_table():
    """Create the assay data table matching the image exactly."""
    rows = []
    for row in ASSAY_DATA:
        rows.append(html.Tr([
            html.Td(row["Property"], style={
                "border": "1px solid #ddd",
                "padding": "6px 8px",
                "fontSize": "12px",
                "fontWeight": "bold" if row["Property"] else "normal"
            }),
            html.Td(row["Unit"], style={
                "border": "1px solid #ddd", 
                "padding": "6px 8px",
                "fontSize": "12px"
            }),
            html.Td(row["Value"], style={
                "border": "1px solid #ddd",
                "padding": "6px 8px", 
                "fontSize": "12px"
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
                "padding": "8px 10px",
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "textAlign": "left",
                "fontSize": "12px"
            }),
            html.Th("Unit", style={
                "border": "1px solid #ddd",
                "padding": "8px 10px", 
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "textAlign": "left",
                "fontSize": "12px"
            }),
            html.Th("Value", style={
                "border": "1px solid #ddd",
                "padding": "8px 10px",
                "backgroundColor": "#f5f5f5", 
                "fontWeight": "bold",
                "textAlign": "left",
                "fontSize": "12px"
            })
        ])),
        html.Tbody(rows)
    ])

def create_refined_products_table():
    """Create the refined products table matching the image exactly."""
    rows = []
    for product, cut_points, properties in REFINED_PRODUCTS:
        first_row = True
        for prop in properties:
            if first_row:
                rows.append(html.Tr([
                    html.Td(product, style={
                        "border": "1px solid #ddd",
                        "padding": "6px 8px",
                        "fontWeight": "bold",
                        "verticalAlign": "top",
                        "fontSize": "11px"
                    }, rowSpan=len(properties)),
                    html.Td(cut_points, style={
                        "border": "1px solid #ddd",
                        "padding": "6px 8px", 
                        "verticalAlign": "top",
                        "fontSize": "11px"
                    }, rowSpan=len(properties)),
                    html.Td(prop[0], style={
                        "border": "1px solid #ddd",
                        "padding": "6px 8px",
                        "fontSize": "11px"
                    }),
                    html.Td(prop[1], style={
                        "border": "1px solid #ddd",
                        "padding": "6px 8px",
                        "fontSize": "11px" 
                    }),
                    html.Td(prop[2], style={
                        "border": "1px solid #ddd",
                        "padding": "6px 8px",
                        "fontSize": "11px"
                    })
                ]))
                first_row = False
            else:
                rows.append(html.Tr([
                    html.Td(prop[0], style={
                        "border": "1px solid #ddd",
                        "padding": "6px 8px",
                        "fontSize": "11px"
                    }),
                    html.Td(prop[1], style={
                        "border": "1px solid #ddd",
                        "padding": "6px 8px",
                        "fontSize": "11px"
                    }),
                    html.Td(prop[2], style={
                        "border": "1px solid #ddd",
                        "padding": "6px 8px", 
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

def create_quality_specs_table():
    """Create the quality specs table matching the image exactly."""
    return html.Table(style={
        "width": "100%",
        "borderCollapse": "collapse",
        "border": "1px solid #ddd",
        "fontSize": "12px",
        "marginBottom": "10px"
    }, children=[
        html.Thead(html.Tr([
            html.Th("Gravity (API at 60F)", style={
                "textAlign": "center",
                "padding": "10px",
                "border": "1px solid #ddd",
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "fontSize": "12px"
            }),
            html.Th("Sulfur Content (% Wt)", style={
                "textAlign": "center",
                "padding": "10px",
                "border": "1px solid #ddd",
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "fontSize": "12px"
            }),
            html.Th("TAN (mg KOH/g)", style={
                "textAlign": "center",
                "padding": "10px",
                "border": "1px solid #ddd",
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "fontSize": "12px"
            })
        ])),
        html.Tbody(html.Tr([
            html.Td("28.40", style={
                "textAlign": "center",
                "padding": "10px",
                "border": "1px solid #ddd",
                "backgroundColor": "white",
                "fontWeight": "bold",
                "fontSize": "12px"
            }),
            html.Td("2.17", style={
                "textAlign": "center",
                "padding": "10px",
                "border": "1px solid #ddd",
                "backgroundColor": "white",
                "fontWeight": "bold",
                "fontSize": "12px"
            }),
            html.Td("0.48", style={
                "textAlign": "center",
                "padding": "10px",
                "border": "1px solid #ddd",
                "backgroundColor": "white",
                "fontWeight": "bold",
                "fontSize": "12px"
            })
        ]))
    ])

def create_producers_table():
    """Create producers and sellers table."""
    return html.Table(style={
        "width": "100%",
        "borderCollapse": "collapse",
        "marginBottom": "10px",
        "fontFamily": "Arial, sans-serif"
    }, children=[
        html.Thead(html.Tr([
            html.Th("Producers", style={
                "border": "1px solid #ddd",
                "padding": "8px 10px",
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "textAlign": "left",
                "fontSize": "12px"
            }),
            html.Th("Sellers", style={
                "border": "1px solid #ddd",
                "padding": "8px 10px",
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "textAlign": "left", 
                "fontSize": "12px"
            })
        ])),
        html.Tbody([
            html.Tr([
                html.Td("BP, ConocoPhillips, Exxon Mobil, Shell", style={
                    "border": "1px solid #ddd",
                    "padding": "8px 10px",
                    "fontSize": "12px"
                }),
                html.Td("BP America Inc., ConocoPhillips, Exxon Mobil, Shell", style={
                    "border": "1px solid #ddd",
                    "padding": "8px 10px",
                    "fontSize": "12px"
                })
            ])
        ])
    ])

def create_port_details_table():
    """Create port details table."""
    rows = []
    for measure, value in PORT_DETAILS:
        rows.append(html.Tr([
            html.Td(measure, style={
                "border": "1px solid #ddd",
                "padding": "8px 10px",
                "fontWeight": "bold",
                "fontSize": "12px"
            }),
            html.Td(value, style={
                "border": "1px solid #ddd",
                "padding": "8px 10px",
                "fontSize": "12px"
            })
        ]))
    
    return html.Table(style={
        "width": "100%",
        "borderCollapse": "collapse",
        "marginBottom": "15px",
        "fontFamily": "Arial, sans-serif"
    }, children=[
        html.Thead(html.Tr([
            html.Th("Measure", style={
                "border": "1px solid #ddd",
                "padding": "8px 10px",
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "textAlign": "left",
                "fontSize": "12px",
                "width": "50%"
            }),
            html.Th("Loop, Clovelly", style={
                "border": "1px solid #ddd",
                "padding": "8px 10px",
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "textAlign": "left",
                "fontSize": "12px",
                "width": "50%"
            })
        ])),
        html.Tbody(rows)
    ])

# ------------------------------------------------------------------------------
# LAYOUT
# ------------------------------------------------------------------------------
def create_layout():
    """Layout exactly matching the provided image design."""
    
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
        
        # Quality Specs Section
        html.Div(style={
            "marginBottom": "20px"
        }, children=[
            html.Div("Latest Quality Specs", style={
                "color": "#d65a00",
                "fontWeight": "bold",
                "fontSize": "16px",
                "marginBottom": "10px"
            }),
            create_quality_specs_table()
        ]),
        
        # Two Column Layout
        html.Div(style={
            "display": "grid",
            "gridTemplateColumns": "1fr 1fr",
            "gap": "20px",
            "marginBottom": "20px"
        }, children=[
            # Left Column
            html.Div(children=[
                html.Div("Mars Blend Assay", style={
                    "color": "#d65a00",
                    "fontWeight": "bold",
                    "fontSize": "16px",
                    "margin": "20px 0 10px 0",
                    "borderBottom": "2px solid #d65a00",
                    "paddingBottom": "5px"
                }),
                create_assay_table(),
                
                html.Div("Sellers and Producers", style={
                    "color": "#d65a00",
                    "fontWeight": "bold", 
                    "fontSize": "16px",
                    "margin": "25px 0 10px 0",
                    "borderBottom": "2px solid #d65a00",
                    "paddingBottom": "5px"
                }),
                create_producers_table(),
                html.Div(
                    "Countries: Select jurisdictions are included under countries for data presentation purposes.",
                    style={
                        "fontSize": "11px",
                        "color": "#666",
                        "marginTop": "10px",
                        "fontStyle": "italic"
                    }
                ),
                
                html.Div("Production and Exports", style={
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
                    dcc.Graph(figure=production_fig, config={"displayModeBar": False})
                ])
            ]),
            
            # Right Column
            html.Div(children=[
                html.Div("Refined Products Breakdown & Properties", style={
                    "color": "#d65a00",
                    "fontWeight": "bold",
                    "fontSize": "16px",
                    "margin": "20px 0 10px 0", 
                    "borderBottom": "2px solid #d65a00",
                    "paddingBottom": "5px"
                }),
                create_refined_products_table(),
                
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
                    "minHeight": "300px"
                }, children=[
                    dcc.Graph(figure=map_fig, config={"displayModeBar": False}),
                    html.Div("© 2025 Mapbox © OpenStreetMap", style={
                        "fontSize": "10px",
                        "color": "#999",
                        "marginTop": "10px",
                        "textAlign": "center"
                    }),
                    html.Div(
                        "Inland points represent terminals for pipeline-delivered crudes.",
                        style={
                            "fontSize": "11px",
                            "color": "#666", 
                            "marginTop": "8px",
                            "fontStyle": "italic",
                            "textAlign": "center"
                        }
                    )
                ]),
                
                html.Div("Port Details", style={
                    "color": "#d65a00",
                    "fontWeight": "bold",
                    "fontSize": "16px",
                    "margin": "25px 0 10px 0",
                    "borderBottom": "2px solid #d65a00",
                    "paddingBottom": "5px"
                }),
                create_port_details_table()
            ])
        ])
    ])

# ------------------------------------------------------------------------------
# DASH APP CREATION
# ------------------------------------------------------------------------------
def create_crude_profile_dashboard():
    """Create and configure the crude profile dashboard."""
    app = Dash(__name__)
    app.layout = create_layout()
    return app

# For standalone testing
if __name__ == "__main__":
    app = create_crude_profile_dashboard()
    app.run_server(debug=True, port=8050)