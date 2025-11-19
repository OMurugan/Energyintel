from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc, Input, Output, callback_context
from dash import dash_table
from app import create_dash_app
import os
import numpy as np

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'CrossPlot.csv')

# ===================================
# LOAD CSV
# ===================================
def load_crossplot_data():

    df = pd.read_csv(
        CSV_PATH,
        encoding="utf-16",
        sep="\t",
        header=None,
        engine="python"
    )

    df = df.dropna(how="all")
    df = df[~df.astype(str).apply(lambda x: x.str.contains("COPYRIGHT", na=False)).any(axis=1)]

    df = df.iloc[3:].reset_index(drop=True)
    df.columns = ["Region", "Crude", "Property", "Value"]

    df = df.pivot_table(
        index=["Region", "Crude"],
        columns="Property",
        values="Value",
        aggfunc="first"
    ).reset_index()

    df = df.rename(columns={
        "Avg. X Property Value": "Gravity-API at 60°F",
        "Avg. Y Property Value": "Sulfur Content %",
        "Avg. Bubble Size": "BubbleSize"
    })

    df["Gravity-API at 60°F"] = pd.to_numeric(df["Gravity-API at 60°F"], errors="coerce")
    df["Sulfur Content %"] = pd.to_numeric(df["Sulfur Content %"], errors="coerce")
    df["BubbleSize"] = pd.to_numeric(df["BubbleSize"], errors="coerce").fillna(40)

    df = df.dropna(subset=["Gravity-API at 60°F", "Sulfur Content %"])

    return df


def load_crude_quality_table():
    """
    Load data for 'Crudes Compared by Quality' table.

    The file has:
        - Row 1–2  : source / copyright
        - Row 3    : parent headers  (Gravity, Sulfur Content, Pour Point, Viscosity, ...)
        - Row 4    : sub headers     (Country, CrudeOil, API at 60 F, % Wt, Temp. C, ...)
        - Row 5+   : data
    """
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'data',
        'crude_quality',
        'table_Crude Quality.csv'
    )

    raw = pd.read_csv(
        csv_path,
        encoding="utf-16",
        sep="\t",
        header=None,
        engine="python"
    )

    # Drop completely empty rows
    raw = raw.dropna(how="all")

    # Skip first two "Source / COPYRIGHT" rows
    raw = raw.iloc[2:].reset_index(drop=True)

    # Parent & sub headers
    parent_headers = raw.iloc[0].fillna("").astype(str).str.strip().tolist()
    sub_headers = raw.iloc[1].fillna("").astype(str).str.strip().tolist()

    # Data starts from row index 2
    df = raw.iloc[2:].reset_index(drop=True)
    df.columns = sub_headers

    # Keep only the columns that are visible in the Tableau view
    # Country | CrudeOil | Gravity (API at 60 F) |
    # Sulfur Content (% Wt) | Pour Point (Temp. C) | Viscosity (cSt at X C ...)
    columns_to_keep = [
        "Country",
        "CrudeOil",
        "API at 60 F",      # under Gravity
        "% Wt",             # under Sulfur Content
        "Temp. C",          # under Pour Point
        "cSt at 10 C",
        "cSt at 15.6 C",
        "cSt at 20 C",
        "cSt at 37.8 C",
        "cSt at 40 C",
        "cSt at 50 C",
    ]

    available_cols = [c for c in columns_to_keep if c in df.columns]
    df = df[available_cols]

    # Build column info for grouped headers (parent / sub)
    column_info = []
    for col in df.columns:
        parent = ""
        if col in sub_headers:
            idx = sub_headers.index(col)
            if idx < len(parent_headers):
                parent = parent_headers[idx].strip()

        # We only show grouped headers when there is a real parent
        # and we do NOT group Country / CrudeOil
        if parent and parent != col and col not in ["Country", "CrudeOil"]:
            column_info.append({"id": col, "parent": parent, "sub": col})
        else:
            column_info.append({"id": col, "parent": "", "sub": col})

    # Attach meta so create_grouped_columns can use it
    df._column_info = column_info
    df._parent_headers = parent_headers
    df._sub_headers = sub_headers

    return df


def create_grouped_columns(df):
    """Create columns with grouped headers for DataTable"""
    if df.empty or not hasattr(df, '_column_info'):
        return [{"name": col, "id": col} for col in df.columns]

    columns = []
    for info in df._column_info:
        col_id = info["id"]
        parent = info["parent"]
        sub = info["sub"]

        if parent and parent != sub and sub not in ["Country", "CrudeOil"]:
            # Two-level header: first row = parent, second row = sub
            display_name = [parent, sub]
        else:
            # Single header row
            display_name = sub

        columns.append({
            "name": display_name,
            "id": col_id
        })

    return columns


def load_yield_volume_table():
    """Load data for Crudes Compared by Product Yield table"""
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'crude_quality', 'table_yield Volume.csv')
    
    df = pd.read_csv(
        csv_path,
        encoding="utf-16",
        sep="\t",
        header=None,
        engine="python"
    )
    
    # Skip copyright rows (rows 0-2) and use row 4 (index 3) as header
    df = df.iloc[3:].reset_index(drop=True)
    
    # First row (index 0) is the header - strip whitespace
    df.columns = df.iloc[0].astype(str).str.strip()
    df = df.iloc[1:].reset_index(drop=True)
    
    # Select relevant columns for the table (only Tableau columns)
    columns_to_keep = [
        'Country',
        'CrudeOil',
        'Gravity (API at 60 F)',
        'Barrels ( Per Metric Ton)',
        'Gasoil',
        'Kerosene',
        'LPG',
        'Naphtha',
        'Residue'
    ]
    
    available_cols = [col for col in columns_to_keep if col in df.columns]
    if available_cols:
        df = df[available_cols]
    
    return df

def create_layout(dash_app=None):

    df = load_crossplot_data()
    
    # Load table data
    try:
        quality_df = load_crude_quality_table()
    except Exception as e:
        quality_df = pd.DataFrame()
    
    try:
        yield_df = load_yield_volume_table()
    except Exception as e:
        yield_df = pd.DataFrame()
        
    # Create options for dropdowns
    x_options = [{"label": 'Gravity-API at 60°F', "value": 'Gravity-API at 60°F'}]
    y_options = [{"label": 'Sulfur Content %', "value": 'Sulfur Content %'}]
    bubble_options = [{"label": 'BubbleSize', "value": 'BubbleSize'}]
    
    # Default values
    default_x = "Gravity-API at 60°F" if "Gravity-API at 60°F" else None
    default_y = "Sulfur Content %" if "Sulfur Content %" else None
    default_bubble = "BubbleSize" if "BubbleSize" else None

    return html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.Label("Select X Axis Property",
                    style={'fontFamily': 'Lato', 'fontSize': '16px', 'lineHeight': '18px', 'color': '#fe5000', 'fontWeight': 'bold', 'fontStyle': 'normal', 'textDecoration': 'none'}),
                dcc.Dropdown(
                    id="x-axis-dropdown",
                    options=x_options,
                    value=default_x,
                    clearable=False,
                    searchable=False,
                    style={'fontSize': '12px'}
                ),
                html.Br(),
                html.Label("X Axis Range",
                    style={'fontFamily': 'Arial', 'fontSize': '11px', 'lineHeight': '12px', 'color': '#1b365d', 'fontWeight': 'bold', 'fontStyle': 'normal', 'textDecoration': 'none', 'marginBottom': '5px'}),
                html.Div([
                    html.Div([
                        dcc.Input(
                            id="x-range-min-input",
                            type="text",
                            value=df[default_x].min() if default_x and default_x in df.columns else 0,
                            style={'display': 'inline-block'}
                        ),
                        dcc.Input(
                            id="x-range-max-input",
                            type="text",
                            value=df[default_x].max() if default_x and default_x in df.columns else 100,
                            style={'display': 'inline-block', 'float': 'right'}
                        ),
                    ], style={'width': '386px', 'marginBottom': '10px', 'position': 'relative'}),
                    html.Div([
                dcc.RangeSlider(
                    id="x-range-slider",
                            min=df[default_x].min() if default_x and default_x in df.columns else 0,
                            max=df[default_x].max() if default_x and default_x in df.columns else 100, step=0.1, value=[df[default_x].min() if default_x and default_x in df.columns else 0, df[default_x].max() if default_x and default_x in df.columns else 100],
                            marks=None,
                        ),
                    ], style={'width': '386px', 'margin': '0', 'padding': '0'}),
                ], style={'width': '100%', 'position': 'relative'}),
            ], style={'width': '32%', 'display': 'inline-block'}),

            html.Div([
                html.Label("Select Y Axis Property",
                    style={'fontFamily': 'Lato', 'fontSize': '16px', 'lineHeight': '18px', 'color': '#fe5000', 'fontWeight': 'bold', 'fontStyle': 'normal', 'textDecoration': 'none'}),
                
                dcc.Dropdown(
                    id="y-axis-dropdown",
                    options=y_options,
                    value=default_y,
                    clearable=False,
                    searchable=False,
                    style={'fontSize': '12px'}
                ),
                html.Br(),
                html.Label("Y Axis Range",
                    style={'fontFamily': 'Arial', 'fontSize': '11px', 'lineHeight': '12px', 'color': '#1b365d', 'fontWeight': 'bold', 'fontStyle': 'normal', 'textDecoration': 'none', 'marginBottom': '5px'}),
                html.Div([
                    html.Div([
                        dcc.Input(
                            id="y-range-min-input",
                            type="text",
                            value=df[default_y].min() if default_y and default_y in df.columns else 0,
                            style={'display': 'inline-block'}
                        ),
                        dcc.Input(
                            id="y-range-max-input",
                            type="text",
                            value=df[default_y].max() if default_y and default_y in df.columns else 100,
                            style={'display': 'inline-block', 'float': 'right'}
                        ),
                    ], style={'width': '386px', 'marginBottom': '10px', 'position': 'relative'}),
                    html.Div([
                dcc.RangeSlider(
                    id="y-range-slider",
                            min=df[default_y].min() if default_y and default_y in df.columns else 0,
                            max=df[default_y].max() if default_y and default_y in df.columns else 100, step=0.01, value=[df[default_y].min() if default_y and default_y in df.columns else 0, df[default_y].max() if default_y and default_y in df.columns else 100],
                            marks=None,
                        ),
                    ], style={'width': '386px', 'margin': '0', 'padding': '0'}),
                ], style={'width': '100%', 'position': 'relative'}),
            ], style={'width': '32%', 'display': 'inline-block', 'marginLeft': '2%'}),

            html.Div([
                html.Label("Select Bubble Size Property",
                    style={'fontFamily': 'Lato', 'fontSize': '16px', 'lineHeight': '18px', 'color': '#fe5000', 'fontWeight': 'bold', 'fontStyle': 'normal', 'textDecoration': 'none'}),
                html.Br(),
                dcc.Dropdown(
                    id="bubble-size-dropdown",
                    options=bubble_options,
                    value=default_bubble,
                    clearable=False,
                    searchable=False,
                    style={'fontSize': '12px'}
                ),
                 html.Br(),
                html.Label("Bubble Size Range",
                    style={'fontFamily': 'Arial', 'fontSize': '11px', 'lineHeight': '12px', 'color': '#1b365d', 'fontWeight': 'bold', 'fontStyle': 'normal', 'textDecoration': 'none', 'marginBottom': '5px'}),
                html.Div([
                    html.Div([
                        dcc.Input(
                            id="bubble-range-min-input",
                            type="text",
                            value=0,
                            style={'display': 'inline-block'}
                        ),
                        dcc.Input(
                            id="bubble-range-max-input",
                            type="text",
                            value=int(df[default_bubble].max()) if default_bubble and default_bubble in df.columns else 100,
                            style={'display': 'inline-block', 'float': 'right'}
                        ),
                    ], style={'width': '386px', 'marginBottom': '10px', 'position': 'relative'}),
                    html.Div([
                dcc.RangeSlider(
                    id="bubble-range-slider",
                            min=0,
                            max=int(df[default_bubble].max()) if default_bubble and default_bubble in df.columns else 100,
                    step=1,
                            value=[0, int(df[default_bubble].max()) if default_bubble and default_bubble in df.columns else 100],
                            marks=None,
                        ),
                    ], style={'width': '386px', 'margin': '0', 'padding': '0'}),
                ], style={'width': '100%', 'position': 'relative'}),
            ], style={'width': '32%', 'display': 'inline-block', 'marginLeft': '2%'}),

        ]),

        html.Br(),

        # --------------------------------------------------
        # MAIN CONTENT (CHART + RIGHT SIDEBAR)
        # --------------------------------------------------
        html.Div([

            # Chart
            html.Div([
                dcc.Graph(
                    id='crude-quality-chart',
                    config={
                        'displayModeBar': False,
                        'displaylogo': False,
                        'modeBarButtonsToRemove': [
                            'pan2d', 'zoom2d', 'select2d', 'lasso2d',
                            'autoScale2d', 'resetScale2d',
                            'hoverClosestCartesian', 'hoverCompareCartesian',
                            'zoomIn2d', 'zoomOut2d'
                        ]
                    }
                )
            ], style={'width': '80%', 'display': 'inline-block', 'verticalAlign': 'top'}),

            # Right Sidebar
            html.Div([

                # Key
                html.Div([
                    html.Div("Key",
                        style={'fontWeight': 'bold', 'marginBottom': '8px',
                               'fontSize': '14px', 'color': '#1a1a1a'}),
                    html.Div([
                        html.Div([
                            html.Span("", style={
                                'display': 'inline-block','width': '15px','height': '15px',
                                'backgroundColor': '#313B49','marginRight': '8px'
                            }),
                            "Null"
                        ], style={'fontSize': '8pt'}),

                        html.Div([
                            html.Span("", style={
                                'display': 'inline-block','width': '15px','height': '15px',
                                'backgroundColor': '#0075A8','marginRight': '8px'
                            }),
                            "FSU"
                        ], style={'fontSize': '8pt'}),

                        html.Div([
                            html.Span("", style={
                                'display': 'inline-block','width': '15px','height': '15px',
                                'backgroundColor': '#595959','marginRight': '8px'
                            }),
                            "OECD"
                        ], style={'fontSize': '8pt'}),

                        html.Div([
                            html.Span("", style={
                                'display': 'inline-block','width': '15px','height': '15px',
                                'backgroundColor': '#7986CB','marginRight': '8px'
                            }),
                            "OPEC"
                        ], style={'fontSize': '8pt'}),

                        html.Div([
                            html.Span("", style={
                                'display': 'inline-block','width': '15px','height': '15px',
                                'backgroundColor': '#FE5000','marginRight': '8px'
                            }),
                            "Others"
                        ], style={'fontSize': '9pt'}),

                    ])
                ], style={'marginBottom': '15px'}),

                # CrudeOil Filter
                html.Div([
                    html.Div("CrudeOil",
                        style={'fontWeight': 'bold', 'marginBottom': '7px',
                               'fontSize': '14px', 'color': '#1a1a1a'}),
                    dcc.Checklist(
                        id='crude-filter-checklist-all',
                        options=[{'label': '(All)', 'value': 'all'}],
                        value=['all'],
                        style={'fontSize': '12px'}
                    ),
                    html.Div([
                        dcc.Checklist(
                            id='crude-filter-checklist-items',
                            options=[],
                            value=[],
                            style={'fontSize': '12px'}
                        )
                    ], style={'maxHeight': '300px', 'overflowY': 'auto', 'marginTop': '10px'})
                ])

            ], style={
                'width': '18%',
                'display': 'inline-block',
                'verticalAlign': 'top',
                'paddingTop': '10px',
                'marginLeft': '2%'
            })

        ]),

        # Tables Section
        html.Div([
            # First Table: Crudes Compared by Quality
            html.Div([
                html.H3("Crudes Compared by Quality", 
                       style={'color': '#FF6600', 'fontWeight': 'bold', 'marginBottom': '10px', 'fontSize': '18px'}),
                dash_table.DataTable(
                    id='crude-quality-table',
                    columns=create_grouped_columns(quality_df) if not quality_df.empty else [],
                    data=quality_df.to_dict('records') if not quality_df.empty else [],
                    style_table={
                        'overflowX': 'auto',
                        'overflowY': 'auto',
                        'height': '550px',
                        'marginBottom': '0px',
                    },
                    style_header={
                        'fontWeight': 'bold',
                        'backgroundColor': 'white',
                        'border': '1px solid #d3d3d3',
                        'textAlign': 'center',
                    },
                    style_cell={
                        'padding': '4px',
                        'fontSize': '12px',
                        'textAlign': 'right',
                        'minWidth': '80px',
                    },

                    filter_action="none",      # <-- IMPORTANT
                    page_action="none",        # ensure no pagination
                    sort_action="native",
                )
            ], style={'marginTop': '30px', 'marginBottom': '30px', }),

            # Second Table: Crudes Compared by Product Yield
            html.Div([
                html.H3("Crudes Compared by Product Yield", 
                       style={'color': '#FF6600', 'fontWeight': 'bold', 'marginBottom': '10px', 'fontSize': '18px'}),
                dash_table.DataTable(
                    id='yield-volume-table',
                    columns=[{"name": col, "id": col} for col in yield_df.columns] if not yield_df.empty else [],
                    data=yield_df.to_dict('records') if not yield_df.empty else [],
                    style_table={
                        'overflowX': 'auto',
                        'overflowY': 'hidden',
                        'height': 'auto',
                        'marginBottom': '0px',
                    },
                    style_header={
                        'fontWeight': 'bold',
                        'backgroundColor': 'white',
                        'border': '1px solid #d3d3d3',
                        'textAlign': 'center',
                    },
                    style_cell={
                        'padding': '4px',
                        'fontSize': '12px',
                        'textAlign': 'right',
                        'minWidth': '80px',
                    },

                    filter_action="none",
                    page_action="none",        # <-- removes pagination
                    sort_action="native",
                )
            ], style={'marginTop': '30px', 'marginBottom': '30px'})
        ])

        ], style={'marginLeft': '10px', 'marginRight': '80px', 'padding': '20px'})
    ])


# ===================================
# DASH APP CREATION
# ===================================
def create_crude_quality_dashboard(server, url_base_pathname="/dash/crude-quality/"):

    current_dir = Path(__file__).parent
    assets_dir = current_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    dash_app = create_dash_app(server, url_base_pathname)

    dash_app.assets_folder = str(assets_dir)

    # --------------------------------------------------------
    # INLINE CSS INJECTION — SLIDER + TOOLTIP + HANDLE
    # --------------------------------------------------------
    css_injected = """
        <style>
        /* Allow vertical scrolling to see tables */
        html, body {
            overflow-x: hidden !important;
            overflow-y: auto !important;
            height: auto !important;
            min-height: 100% !important;
        }
        
        /* === Left Handle: flat left, round right === */
        .rc-slider-handle-1 {
            width: 10px !important;
            height: 14px !important;
            background: #FFFFFF !important;
            border: 2px solid #6E6E6E !important;
            border-radius: 0 7px 7px 0 !important;  /* D faces right */
            margin-top: -6px !important;
            box-shadow: none !important;
        }

        /* === Right Handle: flat right, round left === */
        .rc-slider-handle-2 {
            width: 10px !important;
            height: 14px !important;
            background: #FFFFFF !important;
            border: 2px solid #6E6E6E !important;
            border-radius: 7px 0 0 7px !important;  /* D faces left */
            margin-top: -6px !important;
            box-shadow: none !important;
        }

        .rc-slider-handle {
            width: 10px !important;
            height: 14px !important;

            background-color: #FFFFFF !important;
            border: 2px solid #6E6E6E !important;

            margin-top: -6px !important;
            box-shadow: none !important;
            cursor: pointer !important;
        }

        .rc-slider-handle-1 {
            border-radius: 7px 0 0 7px !important;
        }
        .rc-slider-handle-2 {
            border-radius: 0 7px 7px 0 !important;
        }

        /* Hover */
        .rc-slider-handle:hover {
            border-color: #4D4D4D !important;
        }

        /* Active press */
        .rc-slider-handle:active {
            border-color: #3A3A3A !important;
        }

        .rc-slider-track,
        .rc-slider-track-1,
        .rc-slider-track-2,
        div[class*="rc-slider-track"] {
            background: #6E6E6E !important;
            height: 4px !important;
        }

        .rc-slider-rail {
            background: #D3D3D3 !important;
            height: 4px !important;
        }

        /* Tooltip */
        .rc-slider-tooltip-inner {
            background: #ffffff !important;
            color: black !important;
            border: 1px solid #999 !important;
        }

        /* Dropdown Styling */
        .Select-control {
            font-size: 12px !important;
            height: 22px !important;
            min-height: 22px !important;
            border-radius: 0 !important;
        }
        
        .Select-value-label {
            font-size: 12px !important;
            line-height: 20px !important;
            color: rgb(27, 54, 93) !important;
        }
        
        .Select-input {
            font-size: 12px !important;
            height: 20px !important;
            line-height: 20px !important;
            color: rgb(27, 54, 93) !important;
        }
        
        .Select-input > input {
            font-size: 12px !important;
            line-height: 20px !important;
            color: rgb(27, 54, 93) !important;
        }
        
        .Select-menu-outer {
            font-size: 12px !important;
            border-radius: 0 !important;
        }
        
        .Select-option {
            font-size: 12px !important;
            padding: 4px 10px !important;
        }
        
        .Select-placeholder {
            font-size: 12px !important;
            line-height: 20px !important;
            color: rgb(27, 54, 93) !important;
        }
        
        .Select--single > .Select-control .Select-value {
            font-size: 12px !important;
            line-height: 20px !important;
            color: rgb(27, 54, 93) !important;
        }
        
        .Select--single > .Select-control .Select-value .Select-value-label {
            font-size: 12px !important;
            line-height: 20px !important;
            color: rgb(27, 54, 93) !important;
        }
        
        #x-axis-dropdown .Select-control,
        #y-axis-dropdown .Select-control,
        #bubble-size-dropdown .Select-control {
            font-size: 12px !important;
            height: 22px !important;
            min-height: 22px !important;
            border-radius: 0 !important;
        }
        
        #x-axis-dropdown .Select-value-label,
        #y-axis-dropdown .Select-value-label,
        #bubble-size-dropdown .Select-value-label {
            font-size: 12px !important;
            line-height: 20px !important;
            color: rgb(27, 54, 93) !important;
        }
        
        #x-axis-dropdown .Select-input,
        #y-axis-dropdown .Select-input,
        #bubble-size-dropdown .Select-input {
            height: 20px !important;
            line-height: 20px !important;
            color: rgb(27, 54, 93) !important;
        }
        
        #x-axis-dropdown .Select-input > input,
        #y-axis-dropdown .Select-input > input,
        #bubble-size-dropdown .Select-input > input {
            color: rgb(27, 54, 93) !important;
        }
        
        /* Force all dropdown menu items to use Arial font and proper formatting */
        .Select-menu-outer *,
        .Select-menu *,
        .Select-option *,
        div[id*="dropdown"] .Select-menu-outer *,
        div[id*="dropdown"] .Select-menu * {
            font-family: Arial, Helvetica, sans-serif !important;
            font-size: 12px !important;
        }
        
        /* Ensure dropdown menu items are properly styled */
        .Select-menu-outer .Select-option,
        .Select-menu .Select-option,
        div[id*="dropdown"] .Select-menu-outer .Select-option {
            font-family: Arial, Helvetica, sans-serif !important;
            font-size: 12px !important;
            padding: 6px 10px !important;
            color: #000000 !important;
            background-color: #fff !important;
            line-height: 1.5 !important;
            white-space: nowrap !important;
        }
        
        .Select-menu-outer .Select-option:hover,
        .Select-menu .Select-option:hover {
            background-color: #f0f0f0 !important;
            color: #000000 !important;
        }
        
        .Select-menu-outer .Select-option.is-selected,
        .Select-menu .Select-option.is-selected {
            background-color: #e6f3ff !important;
            color: #000000 !important;
        }
        
        /* Range input fields - show as text by default, input box on hover */
        #x-range-min-input,
        #x-range-max-input,
        #y-range-min-input,
        #y-range-max-input,
        #bubble-range-min-input,
        #bubble-range-max-input {
            border: none !important;
            background: transparent !important;
            padding: 0 !important;
            font-size: 12px !important;
            color: #1b365d !important;
            width: auto !important;
            min-width: 150px !important;
            max-width: 80px !important;
            height: 18px !important;
            line-height: 18px !important;
            outline: none !important;
            box-shadow: none !important;
            top: 0 !important;
            vertical-align: top !important;
            margin: 0 !important;
        }
        
        #x-range-min-input,
        #y-range-min-input,
        #bubble-range-min-input {
            left: 0 !important;
            text-align: left !important;
        }
        
        #x-range-max-input,
        #y-range-max-input,
        #bubble-range-max-input {
            text-align: right !important;
            float: right !important;
            margin-right: 0 !important;
            padding-right: 0 !important;
        }
        
        /* Ensure text and number inputs have same styling */
        #x-range-min-input[type="text"],
        #x-range-min-input[type="number"],
        #x-range-max-input[type="text"],
        #x-range-max-input[type="number"],
        #y-range-min-input[type="text"],
        #y-range-min-input[type="number"],
        #y-range-max-input[type="text"],
        #y-range-max-input[type="number"],
        #bubble-range-min-input[type="text"],
        #bubble-range-min-input[type="number"],
        #bubble-range-max-input[type="text"],
        #bubble-range-max-input[type="number"] {
            vertical-align: top !important;
            margin: 0 !important;
            display: inline-block !important;
        }
        
        #x-range-min-input:hover,
        #x-range-max-input:hover,
        #y-range-min-input:hover,
        #y-range-max-input:hover,
        #bubble-range-min-input:hover,
        #bubble-range-max-input:hover {
            border: 1px solid #ccc !important;
            background: #ffffff !important;
            padding: 1px 3px !important;
        }
        
        #x-range-min-input:focus,
        #x-range-max-input:focus,
        #y-range-min-input:focus,
        #y-range-max-input:focus,
        #bubble-range-min-input:focus,
        #bubble-range-max-input:focus {
            border: 1px solid #999 !important;
            background: #ffffff !important;
            padding: 1px 3px !important;
        }
        
        /* Ensure slider containers align with inputs on both sides */
        div[id*="range-slider"] {
            margin-left: 0 !important;
            padding-left: 0 !important;
            margin-right: 0 !important;
            padding-right: 0 !important;
        }
        
        /* Ensure RangeSlider component has no margin/padding */
        .rc-slider {
            margin-left: 0 !important;
            padding-left: 0 !important;
            margin-right: 0 !important;
            padding-right: 0 !important;
        }
        
        /* Ensure slider track aligns properly */
        .rc-slider-rail {
            margin-left: 0 !important;
            margin-right: 0 !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }
        
        /* Ensure slider wrapper has proper box-sizing */
        .rc-slider {
            width: 100% !important;
            box-sizing: border-box !important;
        }
        
        /* Ensure input container has no right padding/margin for alignment */
        div:has(#x-range-min-input),
        div:has(#y-range-min-input),
        div:has(#bubble-range-min-input) {
            margin-right: 0 !important;
            padding-right: 0 !important;
        }

        </style>
        """

    # Inject CSS into index_string
    dash_app.index_string = f"""
    <!DOCTYPE html>
    <html>
        <head>
            {{%metas%}}
            <title>Crude Quality Dashboard</title>
            {{%favicon%}}
            {{%css%}}
            {css_injected}
        </head>
        <body>
            {{%app_entry%}}
            <footer>
                {{%config%}}
                {{%scripts%}}
                {{%renderer%}}
            </footer>
        </body>
    </html>
    """

    # Layout + callbacks
    dash_app.layout = create_layout(dash_app)
    register_callbacks(dash_app)

    return dash_app


# ===================================
# CALLBACKS
# ===================================
def register_callbacks(dash_app, server=None):

    @dash_app.callback(
        [
            Output('crude-filter-checklist-items', 'options'),
            Output('crude-filter-checklist-items', 'value'),
            Output('crude-filter-checklist-all', 'value')
        ],
        [
            Input('crude-filter-checklist-all', 'value'),
            Input('crude-filter-checklist-items', 'value')
        ],
        prevent_initial_call=False
    )
    def update_crude_filter_list(all_selected, current_selected):

        df = load_crossplot_data()
        crude_list = sorted(df["Crude"].unique().tolist())

        options = [{'label': crude, 'value': crude} for crude in crude_list]

        ctx = callback_context
        trigger = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

        if trigger == 'crude-filter-checklist-all':
            if all_selected and 'all' in all_selected:
                return options, crude_list, ['all']
            return options, [], []

        if trigger == 'crude-filter-checklist-items':
            if not current_selected:
                return options, [], []
            if len(current_selected) == len(crude_list):
                return options, current_selected, ['all']
            return options, current_selected, []

        return options, crude_list, ['all']

    @dash_app.callback(
        [
            Output('x-range-slider', 'min'),
            Output('x-range-slider', 'max'),
            Output('x-range-slider', 'value'),
            Output('x-range-slider', 'step'),
            Output('x-range-min-input', 'value'),
            Output('x-range-max-input', 'value')
        ],
        [Input('x-axis-dropdown', 'value')]
    )
    def update_x_slider(x_prop):
        if not x_prop:
            return 0, 100, [0, 100], 0.1, 0, 100
        
        df = load_crossplot_data()
        if x_prop not in df.columns:
            return 0, 100, [0, 100], 0.1, 0, 100
        
        df[x_prop] = pd.to_numeric(df[x_prop], errors="coerce")
        df = df.dropna(subset=[x_prop])
        
        if len(df) == 0:
            return 0, 100, [0, 100], 0.1, 0, 100
        
        min_val = float(df[x_prop].min())
        max_val = float(df[x_prop].max())
        step = 0.1 if (max_val - min_val) > 10 else 0.01
        
        return min_val, max_val, [min_val, max_val], step, min_val, max_val

    @dash_app.callback(
        [
            Output('y-range-slider', 'min'),
            Output('y-range-slider', 'max'),
            Output('y-range-slider', 'value'),
            Output('y-range-slider', 'step'),
            Output('y-range-min-input', 'value'),
            Output('y-range-max-input', 'value')
        ],
        [Input('y-axis-dropdown', 'value')]
    )
    def update_y_slider(y_prop):
        if not y_prop:
            return 0, 100, [0, 100], 0.01, 0, 100
        
        df = load_crossplot_data()
        if y_prop not in df.columns:
            return 0, 100, [0, 100], 0.01, 0, 100
        
        df[y_prop] = pd.to_numeric(df[y_prop], errors="coerce")
        df = df.dropna(subset=[y_prop])
        
        if len(df) == 0:
            return 0, 100, [0, 100], 0.01, 0, 100
        
        min_val = float(df[y_prop].min())
        max_val = float(df[y_prop].max())
        step = 0.1 if (max_val - min_val) > 10 else 0.01
        
        return min_val, max_val, [min_val, max_val], step, min_val, max_val

    @dash_app.callback(
        [
            Output('bubble-range-slider', 'min'),
            Output('bubble-range-slider', 'max'),
            Output('bubble-range-slider', 'value'),
            Output('bubble-range-min-input', 'value'),
            Output('bubble-range-max-input', 'value')
        ],
        [Input('bubble-size-dropdown', 'value')]
    )
    def update_bubble_slider(bubble_prop):
        if not bubble_prop:
            return 0, 100, [0, 100], 0, 100
        
        df = load_crossplot_data()
        if bubble_prop not in df.columns:
            return 0, 100, [0, 100], 0, 100
        
        df[bubble_prop] = pd.to_numeric(df[bubble_prop], errors="coerce").fillna(40)
        df = df.dropna(subset=[bubble_prop])
        
        if len(df) == 0:
            return 0, 100, [0, 100], 0, 100
        
        min_val = 0
        max_val = int(df[bubble_prop].max())
        
        return min_val, max_val, [min_val, max_val], min_val, max_val

    # Bidirectional sync: X-axis input fields <-> slider
    @dash_app.callback(
        [
            Output('x-range-slider', 'value', allow_duplicate=True),
            Output('x-range-min-input', 'value', allow_duplicate=True),
            Output('x-range-max-input', 'value', allow_duplicate=True)
        ],
        [
            Input('x-range-min-input', 'value'),
            Input('x-range-max-input', 'value'),
            Input('x-range-slider', 'value')
        ],
        prevent_initial_call=True
    )
    def sync_x_range(min_input, max_input, slider_value):
        ctx = callback_context
        if not ctx.triggered:
            return [0, 100], 0, 100
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'x-range-min-input' or trigger_id == 'x-range-max-input':
            # Input changed, update slider
            if min_input is not None and max_input is not None:
                return [min_input, max_input], min_input, max_input
        elif trigger_id == 'x-range-slider':
            # Slider changed, update inputs
            if slider_value:
                return slider_value, slider_value[0], slider_value[1]
        
        return [0, 100], 0, 100

    # Bidirectional sync: Y-axis input fields <-> slider
    @dash_app.callback(
        [
            Output('y-range-slider', 'value', allow_duplicate=True),
            Output('y-range-min-input', 'value', allow_duplicate=True),
            Output('y-range-max-input', 'value', allow_duplicate=True)
        ],
        [
            Input('y-range-min-input', 'value'),
            Input('y-range-max-input', 'value'),
            Input('y-range-slider', 'value')
        ],
        prevent_initial_call=True
    )
    def sync_y_range(min_input, max_input, slider_value):
        ctx = callback_context
        if not ctx.triggered:
            return [0, 100], 0, 100
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'y-range-min-input' or trigger_id == 'y-range-max-input':
            # Input changed, update slider
            if min_input is not None and max_input is not None:
                return [min_input, max_input], min_input, max_input
        elif trigger_id == 'y-range-slider':
            # Slider changed, update inputs
            if slider_value:
                return slider_value, slider_value[0], slider_value[1]
        
        return [0, 100], 0, 100

    # Bidirectional sync: Bubble size input fields <-> slider
    @dash_app.callback(
        [
            Output('bubble-range-slider', 'value', allow_duplicate=True),
            Output('bubble-range-min-input', 'value', allow_duplicate=True),
            Output('bubble-range-max-input', 'value', allow_duplicate=True)
        ],
        [
            Input('bubble-range-min-input', 'value'),
            Input('bubble-range-max-input', 'value'),
            Input('bubble-range-slider', 'value')
        ],
        prevent_initial_call=True
    )
    def sync_bubble_range(min_input, max_input, slider_value):
        ctx = callback_context
        if not ctx.triggered:
            return [0, 100], 0, 100
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'bubble-range-min-input' or trigger_id == 'bubble-range-max-input':
            # Input changed, update slider
            if min_input is not None and max_input is not None:
                return [int(min_input), int(max_input)], min_input, max_input
        elif trigger_id == 'bubble-range-slider':
            # Slider changed, update inputs
            if slider_value:
                return slider_value, slider_value[0], slider_value[1]
        
        return [0, 100], 0, 100

    @dash_app.callback(
        Output('crude-quality-chart', 'figure'),
        [
            Input("x-axis-dropdown", "value"),
            Input("y-axis-dropdown", "value"),
            Input("bubble-size-dropdown", "value"),
            Input("x-range-slider", "value"),
            Input("y-range-slider", "value"),
            Input("bubble-range-slider", "value"),
            Input('crude-filter-checklist-items', 'value'),
        ]
    )
    def update_crude_quality(x_col, y_col, size_col, x_range, y_range, size_range, selected_crudes):

        if not x_col or not y_col or not size_col:
            fig = go.Figure()
            fig.update_layout(
                title=dict(text="Crude Oils Compared by Quality", x=0.5, font=dict(color="#FF6600", size=20)),
                height=500, plot_bgcolor="white"
            )
            return fig

        df = load_crossplot_data()

        # Convert to numeric
        df[x_col] = pd.to_numeric(df[x_col], errors="coerce")
        df[y_col] = pd.to_numeric(df[y_col], errors="coerce")
        df[size_col] = pd.to_numeric(df[size_col], errors="coerce").fillna(40)
        
        # Drop rows where x or y are NaN
        df = df.dropna(subset=[x_col, y_col])

        # Apply filters
        df = df[
            (df[x_col] >= x_range[0]) & (df[x_col] <= x_range[1]) &
            (df[y_col] >= y_range[0]) & (df[y_col] <= y_range[1]) &
            (df[size_col] >= size_range[0]) & (df[size_col] <= size_range[1])
        ]

        if not selected_crudes or len(df) == 0:
            fig = go.Figure()
            x_min = float(df[x_col].min()) if len(df) > 0 else x_range[0]
            x_max = float(df[x_col].max()) if len(df) > 0 else x_range[1]
            y_min = float(df[y_col].min()) if len(df) > 0 else y_range[0]
            y_max = float(df[y_col].max()) if len(df) > 0 else y_range[1]
            
            fig.update_layout(
                title=dict(text="Crude Oils Compared by Quality", x=0.5, font=dict(color="#FF6600", size=20)),
                xaxis=dict(title=x_col, range=[x_min, x_max], showgrid=False),
                yaxis=dict(title=y_col, range=[y_min, y_max], showgrid=False),
                height=500, plot_bgcolor="white"
            )
            return fig

        df = df[df["Crude"].isin(selected_crudes)]

        color_map = {
            'Null': '#313B49',
            'FSU': '#0075A8',
            'OECD': '#595959',
            'OPEC': '#7986CB',
            'Others': '#FE5000'
        }

        fig = go.Figure()

        for region in df["Region"].unique():
            grp = df[df["Region"] == region]
            if len(grp) == 0:
                continue
            custom = grp[size_col].apply(lambda x: f"{x:,.0f}")
            fig.add_trace(go.Scatter(
                x=grp[x_col], y=grp[y_col],
                mode="markers",
                text=grp["Crude"],
                customdata=custom,
                marker=dict(
                    size=np.sqrt(grp[size_col]) * 0.8,
                    color=color_map.get(region, "#444"),
                    opacity=0.8,
                    line=dict(width=1, color="white")
                ),
                hovertemplate=(
                    f"<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#787878;font-weight:normal;font-style:normal;text-decoration:none;\">Crude:</span> "
                    f"<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#000000;font-weight:bold;font-style:normal;text-decoration:none;\">%{{text}}</span><br>"
                    f"<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#787878;font-weight:normal;font-style:normal;text-decoration:none;\">{x_col}:</span> "
                    f"<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#000000;font-weight:bold;font-style:normal;textDecoration:none;\">%{{x:.1f}}</span><br>"
                    f"<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#787878;font-weight:normal;font-style:normal;text-decoration:none;\">{y_col}:</span> "
                    f"<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#000000;font-weight:bold;font-style:normal;text-decoration:none;\">%{{y:.2f}}</span><br>"
                    f"<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#787878;font-weight:normal;font-style:normal;text-decoration:none;\">{size_col}:</span> "
                    f"<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#000000;font-weight:bold;font-style:normal;text-decoration:none;\">%{{customdata}}</span><extra></extra>"
                )
            ))

        # Set fixed axis ranges
        if "API" in x_col:
            x_axis_range = [10.0, 65.0]  # Reversed for API
            x_axis_autorange = False
        else:
            x_axis_range = [10.0, 65.0]
            x_axis_autorange = False
        
        y_axis_range = [0.00, 4.50]

        fig.update_layout(
            title=dict(text="Crude Oils Compared by Quality", x=0.5, font=dict(color="#FF6600", size=20)),
            xaxis=dict(
                title=x_col,
                range=x_axis_range,
                autorange=x_axis_autorange,
                dtick=5,
                tickmode="linear",
                showgrid=False,
                showline=True,
                linecolor="black",
                mirror=True
            ),
            yaxis=dict(
                title=y_col,
                range=y_axis_range,
                dtick=0.5,
                tickmode="linear",
                showgrid=False,
                showline=True,
                linecolor="black",
                mirror=True
            ),
            height=500,
            width=1000,
            autosize=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            showlegend=False,
            margin=dict(l=60, r=10, t=50, b=50),
            hoverlabel=dict(
                bgcolor="white",
                bordercolor="#999999",
                font_size=12,
                font_family='"Benton Sans Low-DPI", Arial, Helvetica, sans-serif',
                font_color="black",
                align="left"
            )
        )

        return fig
