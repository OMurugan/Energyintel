"""
Crude Profile View - Exact Match to Image
Individual crude type profile with detailed specifications
"""
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
from app import create_dash_app

# Static content that matches the provided design EXACTLY
ASSAY_DATA = [
    {"Property": "Barrels", "Unit": "Per Metric Ton", "Value": "7.13"},
    {"Property": "", "Unit": "Total", "Value": ""},
    {"Property": "Gravity", "Unit": "API at 60 F", "Value": "28.51"},
    {"Property": "Mercaptan Sulfur", "Unit": "ppm", "Value": "26.00"},
    {"Property": "Micro Carbon Residue", "Unit": "% Wt", "Value": "6.52"},
    {"Property": "Nickel", "Unit": "ppm", "Value": "22.13"},
    {"Property": "Pour Point", "Unit": "Temp. C", "Value": "-33.00"},
    {"Property": "Reid Vapor Pressure", "Unit": "psi at 37.8 C", "Value": "6.06"},
    {"Property": "Sulfur Content", "Unit": "% Wt", "Value": "2.21"},
    {"Property": "Total Acid Number", "Unit": "Mg KOH/g", "Value": "0.46"},
    {"Property": "Vanadium", "Unit": "ppm", "Value": "62.24"},
    {"Property": "Viscosity", "Unit": "cSt at 20 C", "Value": "28.88"},
    {"Property": "", "Unit": "cSt at 40 C", "Value": "14.82"},
    {"Property": "", "Unit": "cSt at 50 C", "Value": "11.28"}
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
        ("Naphthenes", "% Wt", "53.13"),
        ("Paraffins", "% Wt", "37.80"),
    ]),
    ("Heavy Residue", ">370", [
        ("Yield Volume", "%", "47.77"),
        ("Yield Weight", "%", "53.54"),
        ("Nickel", "ppm", "41.34"),
        ("Pour Point", "Temp. C", "26.64"),
        ("Sulfur Content", "% Wt", "3.57"),
        ("Vanadium", "ppm", "116.29"),
    ]),
    ("Int. Gasoil", "250-300", [
        ("Yield Volume", "%", "7.92"),
        ("Yield Weight", "%", "7.70"),
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
        ("Freeze Point", "Temp. C", "-53.90"),
        ("Smoke Point", "mm", "23.20"),
    ]),
    ("Light Gasoil", "200-250", [
        ("Yield Volume", "%", "7.38"),
        ("Yield Weight", "%", "6.63"),
        ("Cetane Index", "", "46.98"),
        ("Pour Point", "Temp. C", "-54.20"),
    ]),
    ("Light Naphtha", "C5-65", [
        ("Yield Volume", "%", "4.36"),
        ("Yield Weight", "%", "3.19"),
        ("Octane", "RON clear", "77.62"),
    ]),
    ("Residue", "350-370", [
        ("Yield Volume", "%", "2.93"),
        ("Yield Weight", "%", "2.93"),
        ("Viscosity", "cSt at 50 C", "6.95"),
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
    """Create production and exports bar chart matching the image design."""
    fig = go.Figure()
    
    years = ['2006', '2007', '2008', '2009', '2010', '2011', '2012', '2013', '2014', 
             '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024']
    
    production = [250, 300, 280, 260, 240, 220, 200, 210, 230, 200, 220, 240, 260, 280, 270, 250, 240, 230, 220]
    exports = [50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180, 170, 160, 150, 140, 130]
    
    fig.add_trace(go.Bar(
        name="Crude Production",
        x=years,
        y=production,
        marker_color='#1f77b4'
    ))
    
    fig.add_trace(go.Bar(
        name="Crude Exports", 
        x=years,
        y=exports,
        marker_color='#ff7f0e'
    ))
    
    fig.update_layout(
        barmode='group',
        height=300,
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(
            tickangle=-45,
            showgrid=True,
            gridcolor='lightgray'
        ),
        yaxis=dict(
            title="Value (000 b/d)",
            showgrid=True,
            gridcolor='lightgray'
        ),
        plot_bgcolor='white'
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
    """Create the quality specs table."""
    return html.Table(style={
        "width": "100%",
        "borderCollapse": "collapse",
        "marginBottom": "15px",
        "fontFamily": "Arial, sans-serif"
    }, children=[
        html.Thead(html.Tr([
            html.Th("Gravity (API at 60F)", style={
                "border": "1px solid #ddd",
                "padding": "10px",
                "backgroundColor": "#f5f5f5", 
                "fontWeight": "bold",
                "textAlign": "center",
                "fontSize": "12px"
            }),
            html.Th("Sulfur Content (% Wt)", style={
                "border": "1px solid #ddd",
                "padding": "10px",
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "textAlign": "center",
                "fontSize": "12px"
            }),
            html.Th("TAN (mg KOH/g)", style={
                "border": "1px solid #ddd",
                "padding": "10px",
                "backgroundColor": "#f5f5f5",
                "fontWeight": "bold",
                "textAlign": "center", 
                "fontSize": "12px"
            })
        ])),
        html.Tbody(html.Tr([
            html.Td("28.40", style={
                "border": "1px solid #ddd",
                "padding": "10px",
                "textAlign": "center",
                "fontWeight": "bold",
                "fontSize": "12px"
            }),
            html.Td("2.17", style={
                "border": "1px solid #ddd", 
                "padding": "10px",
                "textAlign": "center",
                "fontWeight": "bold",
                "fontSize": "12px"
            }),
            html.Td("0.48", style={
                "border": "1px solid #ddd",
                "padding": "10px",
                "textAlign": "center",
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
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "10px"}, children=[
                html.Span("Select Crude:", style={
                    "color": "#ff6600",
                    "fontWeight": "bold",
                    "fontSize": "14px"
                }),
                dcc.Dropdown(
                    id="crude-select",
                    options=[{"label": "Mars Blend", "value": "mars"}],
                    value="mars",
                    clearable=False,
                    style={
                        "width": "200px",
                        "fontSize": "13px"
                    }
                )
            ]),
            html.A(
                "Click here to see the Crude's Profile",
                href="#",
                style={
                    "color": "#ff6600",
                    "textDecoration": "none",
                    "fontWeight": "bold",
                    "fontSize": "13px"
                }
            )
        ]),
        
        # Summary Section
        html.Div(style={
            "display": "flex",
            "justifyContent": "space-between",
            "marginBottom": "25px",
            "backgroundColor": "#f8f8f8",
            "padding": "15px",
            "borderRadius": "5px"
        }, children=[
            html.Table(style={
                "width": "70%",
                "borderCollapse": "collapse"
            }, children=[
                html.Thead(html.Tr([
                    html.Th("Alternate Crude Names", style={
                        "backgroundColor": "#e8e8e8",
                        "padding": "10px",
                        "textAlign": "left",
                        "border": "1px solid #ddd",
                        "fontWeight": "bold",
                        "fontSize": "12px"
                    }),
                    html.Th("Country", style={
                        "backgroundColor": "#e8e8e8",
                        "padding": "10px",
                        "textAlign": "left", 
                        "border": "1px solid #ddd",
                        "fontWeight": "bold",
                        "fontSize": "12px"
                    }),
                    html.Th("Assay Date", style={
                        "backgroundColor": "#e8e8e8",
                        "padding": "10px",
                        "textAlign": "left",
                        "border": "1px solid #ddd",
                        "fontWeight": "bold",
                        "fontSize": "12px"
                    })
                ])),
                html.Tbody(html.Tr([
                    html.Td("Mars Blend", style={
                        "padding": "10px",
                        "border": "1px solid #ddd",
                        "backgroundColor": "white",
                        "fontSize": "12px"
                    }),
                    html.Td("United States", style={
                        "padding": "10px",
                        "border": "1px solid #ddd", 
                        "backgroundColor": "white",
                        "fontSize": "12px"
                    }),
                    html.Td("2025", style={
                        "padding": "10px",
                        "border": "1px solid #ddd",
                        "backgroundColor": "white",
                        "fontSize": "12px"
                    })
                ]))
            ]),
            html.Div(style={
                "background": "linear-gradient(135deg, #fff9e6, #ffedcc)",
                "border": "1px solid #e6b800",
                "padding": "15px 25px",
                "borderRadius": "5px",
                "textAlign": "center",
                "minWidth": "150px"
            }, children=[
                html.Div("Carbon Intensity", style={
                    "color": "#b38600",
                    "fontWeight": "bold",
                    "fontSize": "14px",
                    "marginBottom": "5px"
                }),
                html.Div("Low", style={
                    "color": "#805500", 
                    "fontWeight": "bold",
                    "fontSize": "16px"
                })
            ])
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
                    "color": "#ff6600",
                    "fontWeight": "bold",
                    "fontSize": "16px",
                    "margin": "25px 0 10px 0",
                    "borderBottom": "1px solid #ff6600",
                    "paddingBottom": "5px"
                }),
                create_assay_table(),
                
                html.Div("Sellers and Producers", style={
                    "color": "#ff6600",
                    "fontWeight": "bold", 
                    "fontSize": "16px",
                    "margin": "25px 0 10px 0",
                    "borderBottom": "1px solid #ff6600",
                    "paddingBottom": "5px"
                }),
                create_producers_table(),
                html.Div(
                    "Countries: Select jurisdictions are included under countries for data presentation purposes.",
                    style={
                        "fontSize": "11px",
                        "color": "#666",
                        "marginTop": "6px",
                        "fontStyle": "italic"
                    }
                ),
                
                html.Div("Production and Exports", style={
                    "color": "#ff6600",
                    "fontWeight": "bold",
                    "fontSize": "16px", 
                    "margin": "25px 0 10px 0",
                    "borderBottom": "1px solid #ff6600",
                    "paddingBottom": "5px"
                }),
                html.Div(style={
                    "border": "1px solid #ddd",
                    "padding": "15px",
                    "borderRadius": "5px",
                    "margin": "10px 0"
                }, children=[
                    dcc.Graph(figure=production_fig, config={"displayModeBar": False})
                ])
            ]),
            
            # Right Column
            html.Div(children=[
                html.Div("Refined Products Breakdown & Properties", style={
                    "color": "#ff6600",
                    "fontWeight": "bold",
                    "fontSize": "16px",
                    "margin": "25px 0 10px 0", 
                    "borderBottom": "1px solid #ff6600",
                    "paddingBottom": "5px"
                }),
                create_refined_products_table(),
                
                html.Div("Latest Quality Specs", style={
                    "color": "#ff6600",
                    "fontWeight": "bold",
                    "fontSize": "16px",
                    "margin": "25px 0 10px 0",
                    "borderBottom": "1px solid #ff6600",
                    "paddingBottom": "5px"
                }),
                html.Div(style={
                    "border": "1px solid #ddd",
                    "padding": "15px",
                    "borderRadius": "5px",
                    "marginBottom": "15px"
                }, children=[
                    create_quality_specs_table()
                ]),
                
                html.Div("Loading Ports", style={
                    "color": "#ff6600",
                    "fontWeight": "bold",
                    "fontSize": "16px",
                    "margin": "25px 0 10px 0",
                    "borderBottom": "1px solid #ff6600", 
                    "paddingBottom": "5px"
                }),
                html.Div(style={
                    "border": "1px solid #ddd",
                    "padding": "15px",
                    "borderRadius": "5px",
                    "margin": "10px 0",
                    "height": "300px"
                }, children=[
                    dcc.Graph(figure=map_fig, config={"displayModeBar": False}),
                    html.Div("© 2025 Mapbox © OpenStreetMap", style={
                        "fontSize": "10px",
                        "color": "#999",
                        "margin": "5px 0"
                    }),
                    html.Div(
                        "Inland points represent terminals for pipeline-delivered crudes.",
                        style={
                            "fontSize": "11px",
                            "color": "#666", 
                            "marginTop": "6px",
                            "fontStyle": "italic"
                        }
                    )
                ]),
                
                html.Div("Port Details", style={
                    "color": "#ff6600",
                    "fontWeight": "bold",
                    "fontSize": "16px",
                    "margin": "25px 0 10px 0",
                    "borderBottom": "1px solid #ff6600",
                    "paddingBottom": "5px"
                }),
                create_port_details_table()
            ])
        ])
    ])

# ------------------------------------------------------------------------------
# CALLBACKS
# ------------------------------------------------------------------------------
def register_callbacks(dash_app):
    """Register callbacks for the dashboard."""
    
    @dash_app.callback(
        Output("crude-select", "value"),
        Input("crude-select", "value")
    )
    def keep_value(value):
        """Keep the current value."""
        return value

# ------------------------------------------------------------------------------
# DASH APP CREATION
# ------------------------------------------------------------------------------
def create_crude_profile_dashboard(server, url_base_pathname="/dash/crude-profile/"):
    """Create and configure the crude profile dashboard."""
    from app import create_dash_app
    dash_app = create_dash_app(server, url_base_pathname)
    dash_app.layout = create_layout()
    register_callbacks(dash_app)
    return dash_app

# For standalone testing
if __name__ == "__main__":
    # This allows testing the layout directly
    app = create_dash_app(__name__, "/")
    app.layout = create_layout()
    register_callbacks(app)
    
    if __name__ == "__main__":
        app.run_server(debug=True)