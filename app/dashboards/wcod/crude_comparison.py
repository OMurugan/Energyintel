from dash import dcc, html, Input, Output, dash_table, callback_context, State, ctx
import pandas as pd
import os
import chardet
import dash
import re

# ------------------------------------------------------------------------------
# PATH CONSTANTS
# ------------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PRODUCTION_FILE = os.path.join(DATA_DIR, "production-crude-comparison.csv")
EXPORTS_FILE = os.path.join(DATA_DIR, "exports-crude-comparison.csv")

# ------------------------------------------------------------------------------
# DETECT ENCODING
# ------------------------------------------------------------------------------
def detect_encoding(file_path):
    with open(file_path, "rb") as f:
        raw = f.read()
        enc = chardet.detect(raw)
        return enc["encoding"]

# ------------------------------------------------------------------------------
# REMOVE FOOTER ROWS
# ------------------------------------------------------------------------------
def remove_footer_rows(df):
    not_fully_empty = ~df.apply(lambda row: all(str(x).strip() == "" for x in row), axis=1)

    footer_keywords = [
        "copyright",
        "energy intelligence",
        "source",
    ]

    def is_footer(row):
        return any(
            any(keyword in str(cell).lower() for keyword in footer_keywords)
            for cell in row
        )

    not_footer = ~df.apply(is_footer, axis=1)
    return df[not_fully_empty & not_footer]

# ------------------------------------------------------------------------------
# SAMPLE DATA IF CSV IS MISSING
# ------------------------------------------------------------------------------
def get_sample():
    sample = [{"CrudeOil": "Sample Oil", "2024": 10, "2023": 8, "2022": 6}]
    cols = [{"name": c, "id": c, "presentation": "markdown"} if c=="CrudeOil" else {"name": c, "id": c} for c in sample[0].keys()]
    return sample, cols

# ------------------------------------------------------------------------------
# LOAD CSV (SAFE, AUTO-DELIMITER, SKIP BAD LINES)
# ------------------------------------------------------------------------------
def load_crude_data(mode):
    csv_path = PRODUCTION_FILE if mode == "production" else EXPORTS_FILE

    if not os.path.exists(csv_path):
        print(f"❌ File missing: {csv_path}. Using sample.")
        return get_sample()

    encoding = detect_encoding(csv_path)

    try:
        df = pd.read_csv(
            csv_path,
            encoding=encoding,
            sep=None,
            engine="python",
            on_bad_lines="skip",
            header=None
        )
        print(f"Loaded {mode} CSV using encoding: {encoding}")
    except Exception as e:
        print("Retrying CSV read with latin-1:", e)
        df = pd.read_csv(
            csv_path,
            encoding="latin-1", 
            sep=None,
            engine="python",
            on_bad_lines="skip",
            header=None
        )

    # 1️⃣ Remove blank rows
    df = df.dropna(how="all")

    # 2️⃣ Detect header row
    header_row_index = df[df.apply(lambda row: "crude" in " ".join(row.astype(str)).lower(), axis=1)].index
    header_row = header_row_index[0] if len(header_row_index) else 0
    df.columns = df.iloc[header_row].astype(str).str.strip()
    df = df[df.index > header_row]

    # 3️⃣ Remove footer
    df = remove_footer_rows(df)

    # 4️⃣ Remove unwanted columns
    df = df.loc[:, ~df.columns.str.contains("Unnamed")]
    df = df.loc[:, ~df.columns.str.contains("Source", case=False)]
    df = df.loc[:, df.columns.notnull()]

    # Remove profile_url column if exists
    if "profile_url" in df.columns:
        df = df.drop(columns=["profile_url"])

    # Remove columns that are completely empty
    df = df.dropna(axis=1, how='all')

    # 5️⃣ Clean up
    df = df.dropna(how="all").fillna("")
    df.columns = [c.strip() for c in df.columns]

    # -----------------------------
    # Convert CrudeOil to clickable URLs (EXTERNAL)
    # -----------------------------
    if "CrudeOil" in df.columns:
        df["CrudeOil"] = df["CrudeOil"].apply(
            lambda x: f"[{x}](https://www.energyintel.com/wcod/crude-profile/{x.replace(' ', '-')})"
        )

    return df.to_dict("records"), [
        {"name": c, "id": c, "presentation": "markdown"} if c=="CrudeOil" else {"name": c, "id": c} 
        for c in df.columns
    ]

# ------------------------------------------------------------------------------
# CALCULATE COMBINED SUM DATA (Production + Exports)
# ------------------------------------------------------------------------------
def calculate_combined_sums():
    """Calculate combined sums of Production and Exports for each crude oil and year"""
    
    # Load both datasets
    production_data, production_cols = load_crude_data("production")
    exports_data, exports_cols = load_crude_data("exports")
    
    # Convert to DataFrames
    prod_df = pd.DataFrame(production_data)
    exp_df = pd.DataFrame(exports_data)
    
    # Get numeric columns (years)
    numeric_cols = [col for col in prod_df.columns if col != 'CrudeOil']
    
    # Create combined data
    combined_data = []
    
    # Get all unique crude oils from both datasets
    all_crudes = set(prod_df['CrudeOil'].tolist() + exp_df['CrudeOil'].tolist())
    
    for crude in all_crudes:
        combined_row = {'CrudeOil': crude}
        
        # Find this crude in production data
        prod_row = prod_df[prod_df['CrudeOil'] == crude]
        # Find this crude in exports data  
        exp_row = exp_df[exp_df['CrudeOil'] == crude]
        
        for col in numeric_cols:
            prod_val = 0
            exp_val = 0
            
            # Get production value
            if not prod_row.empty and col in prod_row.columns:
                prod_cell = prod_row[col].iloc[0]
                if prod_cell and str(prod_cell).strip() and str(prod_cell).strip() != '':
                    try:
                        clean_val = str(prod_cell).replace(',', '')
                        prod_val = float(clean_val)
                    except (ValueError, TypeError):
                        prod_val = 0
            
            # Get exports value
            if not exp_row.empty and col in exp_row.columns:
                exp_cell = exp_row[col].iloc[0]
                if exp_cell and str(exp_cell).strip() and str(exp_cell).strip() != '':
                    try:
                        clean_val = str(exp_cell).replace(',', '')
                        exp_val = float(clean_val)
                    except (ValueError, TypeError):
                        exp_val = 0
            
            # Calculate combined sum
            combined_val = prod_val + exp_val
            combined_row[col] = f"{combined_val:,.0f}" if combined_val > 0 else ""
        
        combined_data.append(combined_row)
    
    return combined_data

# ------------------------------------------------------------------------------
# CALCULATE SUM ROW FOR COMBINED DATA
# ------------------------------------------------------------------------------
def calculate_combined_sum_row(combined_data):
    """Calculate sum row for combined data"""
    if not combined_data:
        return None
    
    df = pd.DataFrame(combined_data)
    numeric_cols = [col for col in df.columns if col != 'CrudeOil']
    
    sum_row = {'CrudeOil': 'SUM'}
    
    for col in numeric_cols:
        col_sum = 0
        for val in df[col]:
            if val and str(val).strip() and str(val).strip() != '':
                try:
                    clean_val = str(val).replace(',', '')
                    col_sum += float(clean_val)
                except (ValueError, TypeError):
                    continue
        sum_row[col] = f"{col_sum:,.0f}"
    
    return sum_row

# ------------------------------------------------------------------------------
# CALCULATE SUM ROW FOR REGULAR DATA
# ------------------------------------------------------------------------------
def calculate_sum_row(data):
    """Calculate sum row for regular production/exports data"""
    if not data:
        return None
    
    df = pd.DataFrame(data)
    numeric_cols = [col for col in df.columns if col != 'CrudeOil']
    
    sum_row = {'CrudeOil': 'SUM'}
    
    for col in numeric_cols:
        col_sum = 0
        for val in df[col]:
            if val and str(val).strip() and str(val).strip() != '':
                try:
                    clean_val = str(val).replace(',', '')
                    col_sum += float(clean_val)
                except (ValueError, TypeError):
                    continue
        sum_row[col] = f"{col_sum:,.0f}"
    
    return sum_row

# ------------------------------------------------------------------------------
# INITIAL LOAD
# ------------------------------------------------------------------------------
production_data, production_columns = load_crude_data("production")
production_sum_row = calculate_sum_row(production_data)
table_data_with_sum = production_data + [production_sum_row] if production_sum_row else production_data

# ------------------------------------------------------------------------------
# LAYOUT
# ------------------------------------------------------------------------------
def create_layout(server):
    return html.Div(
        children=[
            html.Div([
                html.Label(
                    "Select Export/Production",
                    style={
                        "fontSize": "20px",
                        "color": "#d65a00",
                        "fontWeight": "bold",
                        "marginBottom": "10px",
                        "display": "block",
                        "fontFamily": "Arial",
                    }
                ),
                dcc.Dropdown(
                    id="export-production-dropdown",
                    options=[
                        {"label": "Production", "value": "production"},
                        {"label": "Exports", "value": "exports"},
                    ],
                    value="production",
                    clearable=False,
                    style={
                        "width": "100%",
                        "fontSize": "14px",
                        "fontFamily": "Arial",
                    }
                ),
            ], style={"marginBottom": "25px", "width": "100%"}),

            html.Div(id="crude-heading", style={"textAlign": "center"}),

            html.Hr(style={"margin": "10px 0", "border": "1px solid #ccc"}),

            # CSS for popup menu hover effects and tooltips
            dcc.Markdown("""
                <style>
                .popup-menu-item:hover {
                    background-color: #f5f5f5 !important;
                }
                #popup-field-btn:hover, #popup-nested-btn:hover {
                    background-color: #f5f5f5 !important;
                }
                .arrow-tooltip {
                    position: absolute;
                    background-color: #333;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                    font-family: Arial;
                    white-space: nowrap;
                    z-index: 1003;
                    pointer-events: none;
                }
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
                /* Specific styles for CrudeOil header additional elements */
                .dash-header[data-dash-column="CrudeOil"] .sort-order-container {
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
                .dash-header[data-dash-column="CrudeOil"]:hover .sort-order-container {
                    opacity: 1;
                }
                .dash-header[data-dash-column="CrudeOil"] .sort-order-container:hover {
                    background-color: #e6f3ff;
                    border-color: #1f3263;
                }
                .dash-header[data-dash-column="CrudeOil"] .sort-asc,
                .dash-header[data-dash-column="CrudeOil"] .sort-desc {
                    display: block;
                    line-height: 1;
                    cursor: pointer;
                    padding: 1px 2px;
                    border-radius: 1px;
                }
                .dash-header[data-dash-column="CrudeOil"] .sort-asc:hover,
                .dash-header[data-dash-column="CrudeOil"] .sort-desc:hover {
                    background-color: #d4e7ff;
                    font-weight: bold;
                }
                .dash-cell:not([data-dash-column="CrudeOil"]):not(.dash-header) {
                    cursor: pointer;
                }
                </style>
            """, dangerously_allow_html=True),

            # Sorting controls popup (initially hidden)
            html.Div([
                html.Div([
                    html.Div("Data source order", id="popup-source-btn", 
                            style={
                                "padding": "6px 10px", 
                                "fontSize": "12px",
                                "cursor": "pointer",
                                "fontFamily": "Arial",
                                "color": "#333",
                            }, className="popup-menu-item"),
                    html.Div("Alphabetic", id="popup-alphabetic-btn",
                            style={
                                "padding": "6px 10px", 
                                "fontSize": "12px",
                                "cursor": "pointer",
                                "fontFamily": "Arial",
                                "color": "#333",
                            }, className="popup-menu-item"),
                    html.Div([
                        html.Span("Field", style={"flex": "1"}),
                        html.Span("▶", id="field-arrow-btn", style={
                            "cursor": "pointer",
                            "fontSize": "10px",
                            "color": "#666",
                            "marginLeft": "8px",
                        }),
                    ], id="popup-field-btn",
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
                        html.Span("▶", id="nested-arrow-btn", style={
                            "cursor": "pointer",
                            "fontSize": "10px",
                            "color": "#666",
                            "marginLeft": "8px",
                        }),
                    ], id="popup-nested-btn",
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
                ]),
            ], id="sorting-controls", style={
                "position": "absolute", 
                "backgroundColor": "white", 
                "padding": "4px 0",
                "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                "zIndex": "1000",
                "display": "none",
                "minWidth": "160px"
            }),

            dash_table.DataTable(
                id="crude-comparison-table",
                data=table_data_with_sum,
                columns=production_columns,
                style_table={
                    "overflowX": "auto",
                    "overflowY": "auto",
                    "maxHeight": "500px",
                    "border": "1px solid #d9d9d9",
                    "backgroundColor": "white",
                    "position": "relative",
                },
                style_cell={
                    "textAlign": "center",
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
                    "textAlign": "center",
                    "padding": "10px 12px",
                    "position": "relative",
                },
                style_cell_conditional=[
                    {
                        "if": {"column_id": "CrudeOil"},
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
                        "if": {"column_id": "CrudeOil", "header": True},
                        "textAlign": "left",
                        "color": "#1f3263",
                        "position": "relative",
                    },
                    # Year column headers - dark blue, center-aligned
                    {
                        "if": {"header": True, "column_id": [str(year) for year in range(2007, 2025)]},
                        "color": "#1f3263",
                        "textAlign": "center",
                    },
                ],
                style_data_conditional=[
                    # All data rows white background
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "#FFFFFF",
                    },
                    {
                        "if": {"row_index": "even"},
                        "backgroundColor": "#FFFFFF",
                    },
                    # CrudeOil column data - dark blue
                    {
                        "if": {"column_id": "CrudeOil"},
                        "color": "#1f3263",
                        "backgroundColor": "#FFFFFF",
                    },
                    # Year columns data - dark gray/black, center-aligned
                    {
                        "if": {"column_id": [str(year) for year in range(2007, 2025)]},
                        "color": "#333333",
                        "textAlign": "center",
                    },
                    # Style for SUM row - DARK BLUE BACKGROUND
                    {
                        "if": {"filter_query": '{CrudeOil} = "SUM"'},
                        "backgroundColor": "#1f3263",
                        "color": "white",
                        "fontWeight": "bold",
                        "borderTop": "2px solid #d65a00",
                    },
                    {
                        "if": {"filter_query": '{CrudeOil} = "SUM"', "column_id": "CrudeOil"},
                        "textAlign": "left",
                        "backgroundColor": "#1f3263",
                        "color": "white",
                        "fontWeight": "bold",
                    }
                ],
                css=[
                    {
                        'selector': '.dash-cell[data-dash-column="CrudeOil"] a',
                        'rule': '''
                            color: #1f3263 !important; 
                            text-decoration: underline !important;
                            font-weight: 600 !important;
                            font-family: Arial, sans-serif !important;
                            cursor: pointer !important;
                        '''
                    },
                    {
                        'selector': '.dash-cell[data-dash-column="CrudeOil"] a:hover',
                        'rule': '''
                            color: #1f3263 !important; 
                            text-decoration: underline !important;
                        '''
                    },
                    {
                        'selector': '.dash-header[data-dash-column="CrudeOil"]',
                        'rule': '''
                            color: #1f3263 !important;
                            position: relative !important;
                            text-align: left !important;
                        '''
                    },
                    # Year column headers styling
                    {
                        'selector': '.dash-header[data-dash-column*="20"]',
                        'rule': '''
                            color: #1f3263 !important;
                            text-align: center !important;
                            font-weight: bold !important;
                        '''
                    },
                    # Table borders - horizontal lines for rows
                    {
                        'selector': '.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner table',
                        'rule': '''
                            border-collapse: collapse !important;
                        '''
                    },
                    {
                        'selector': '.dash-cell',
                        'rule': '''
                            border-top: 1px solid #e0e0e0 !important;
                            border-bottom: 1px solid #e0e0e0 !important;
                        '''
                    },
                    {
                        'selector': '.dash-header',
                        'rule': '''
                            border-left: 1px solid #d0d0d0 !important;
                            border-right: 1px solid #d0d0d0 !important;
                        '''
                    },
                    # A-Z vertical text for sort order - HIDDEN BY DEFAULT
                    {
                        'selector': '.dash-header[data-dash-column="CrudeOil"] .sort-order-container',
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
                        'selector': '.dash-header[data-dash-column="CrudeOil"]:hover .sort-order-container',
                        'rule': '''
                            opacity: 1;
                        '''
                    },
                    {
                        'selector': '.dash-header[data-dash-column="CrudeOil"] .sort-order-container:hover',
                        'rule': '''
                            background-color: #e6f3ff;
                            border-color: #1f3263;
                        '''
                    },
                    {
                        'selector': '.dash-header[data-dash-column="CrudeOil"] .sort-asc',
                        'rule': '''
                            display: block;
                            line-height: 1;
                            cursor: pointer;
                            padding: 1px 2px;
                            border-radius: 1px;
                        '''
                    },
                    {
                        'selector': '.dash-header[data-dash-column="CrudeOil"] .sort-asc:hover',
                        'rule': '''
                            background-color: #d4e7ff;
                            font-weight: bold;
                        '''
                    },
                    {
                        'selector': '.dash-header[data-dash-column="CrudeOil"] .sort-desc',
                        'rule': '''
                            display: block;
                            line-height: 1;
                            cursor: pointer;
                            padding: 1px 2px;
                            border-radius: 1px;
                        '''
                    },
                    {
                        'selector': '.dash-header[data-dash-column="CrudeOil"] .sort-desc:hover',
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
                    {
                        'selector': '.dash-cell:not([data-dash-column="CrudeOil"]):not(.dash-header)',
                        'rule': 'cursor: pointer;'
                    },
                ],
                fixed_rows={"headers": True},
                page_action="none",
                sort_action="none",
                filter_action="none",
                markdown_options={"html": True},
            ),

            # Store components
            dcc.Store(id='external-url-store'),
            dcc.Store(id='selected-cell-store', data=None),
            dcc.Store(id='original-data-store', data=production_data),
            dcc.Store(id='current-sort-order', data={'type': 'source', 'direction': 'asc'}),
            dcc.Store(id='show-sorting-controls', data=False),
            dcc.Store(id='sum-row-store', data=production_sum_row),
            dcc.Store(id='is-combined-mode', data=False),  # Track if we're in combined mode
            html.Div(id='dummy-output', style={'display': 'none'}),
            html.Div(id='dummy-output-2', style={'display': 'none'}),

            # Hidden buttons for header interactions
            html.Button("Sort Ascending Click", id="sort-asc-btn-hidden", n_clicks=0, style={"display": "none"}),
            html.Button("Sort Descending Click", id="sort-desc-btn-hidden", n_clicks=0, style={"display": "none"}),
            html.Button("Popup Menu Click", id="popup-menu-btn", n_clicks=0, style={"display": "none"}),
            # Hidden buttons for year column sorting and combined mode
            html.Button("Year Column Click", id="year-column-btn", n_clicks=0, style={"display": "none"}),
            html.Button("Field Sort Click", id="field-sort-btn", n_clicks=0, style={"display": "none"}),
            html.Button("Nested Sort Click", id="nested-sort-btn", n_clicks=0, style={"display": "none"}),

            html.Div([
                html.P(
                    "Data source: Energy Intelligence",
                    style={
                        "fontSize": "11px",
                        "fontStyle": "italic",
                        "color": "#777",
                        "textAlign": "right",
                        "marginTop": "8px",
                        "fontFamily": "Arial",
                    },
                )
            ]),
        ],
        style={
            "padding": "25px",
            "backgroundColor": "white",
            "maxWidth": "1500px",
            "margin": "0 auto",
            "position": "relative",
        },
        id="main-container"
    )

# ------------------------------------------------------------------------------
# CALLBACKS
# ------------------------------------------------------------------------------
def register_callbacks(app):

    @app.callback(
        Output("crude-heading", "children"),
        [Input("export-production-dropdown", "value"),
         Input("is-combined-mode", "data")]
    )
    def update_header(selected, is_combined):
        if is_combined:
            title = "Production + Exports Combined ('000 b/d)"
        elif selected == "exports":
            title = "Exports ('000 b/d)"
        else:  # production
            title = "Production ('000 b/d)"
        
        return html.H2(
            title,
            style={
                "color": "#d65a00",
                "fontSize": "22px",
                "fontWeight": "bold",
                "fontFamily": "Arial",
                "marginBottom": "10px",
                "textAlign": "center",
            },
        )

    @app.callback(
        [Output("crude-comparison-table", "data"),
         Output("original-data-store", "data"),
         Output("sum-row-store", "data"),
         Output("is-combined-mode", "data")],
        [Input("export-production-dropdown", "value"),
         Input("field-sort-btn", "n_clicks"),
         Input("nested-sort-btn", "n_clicks"),
         Input("year-column-btn", "n_clicks")],
        [State("is-combined-mode", "data")]
    )
    def reload_data(mode, field_clicks, nested_clicks, year_clicks, is_combined):
        trigger = ctx.triggered_id
        
        # If Field, Nested, or Year icon is clicked, switch to combined mode
        if trigger in ['field-sort-btn', 'nested-sort-btn', 'year-column-btn']:
            # Use combined data
            combined_data = calculate_combined_sums()
            sum_row = calculate_combined_sum_row(combined_data)
            table_data_with_sum = combined_data + [sum_row] if sum_row else combined_data
            return table_data_with_sum, combined_data, sum_row, True
        else:
            # Use individual dataset (Production or Exports)
            crude_data, columns = load_crude_data(mode)
            sum_row = calculate_sum_row(crude_data)
            table_data_with_sum = crude_data + [sum_row] if sum_row else crude_data
            return table_data_with_sum, crude_data, sum_row, False

    @app.callback(
        Output("crude-comparison-table", "columns"),
        Input("export-production-dropdown", "value"),
    )
    def reload_columns(mode):
        _, columns = load_crude_data(mode)
        return columns

    # Handle header clicks (both sort order and popup menu)
    @app.callback(
        [Output('sorting-controls', 'style'),
         Output('show-sorting-controls', 'data'),
         Output('current-sort-order', 'data', allow_duplicate=True)],
        [Input('sort-asc-btn-hidden', 'n_clicks'),
         Input('sort-desc-btn-hidden', 'n_clicks'),
         Input('popup-menu-btn', 'n_clicks'),
         Input('popup-source-btn', 'n_clicks'),
         Input('popup-alphabetic-btn', 'n_clicks'),
         Input('popup-field-btn', 'n_clicks'),
         Input('popup-nested-btn', 'n_clicks'),
         Input('field-sort-btn', 'n_clicks'),
         Input('nested-sort-btn', 'n_clicks')],
        [State('show-sorting-controls', 'data'),
         State('current-sort-order', 'data')],
        prevent_initial_call=True
    )
    def handle_header_interactions(asc_clicks, desc_clicks, popup_clicks, 
                                  popup_source_clicks, popup_alpha_clicks,
                                  popup_field_clicks, popup_nested_clicks,
                                  field_sort_clicks, nested_sort_clicks,
                                  show_controls, current_sort):
        trigger = ctx.triggered_id
        
        if trigger == 'sort-asc-btn-hidden':
            return dash.no_update, dash.no_update, {'type': 'alphabetic', 'direction': 'asc'}
        
        elif trigger == 'sort-desc-btn-hidden':
            return dash.no_update, dash.no_update, {'type': 'alphabetic', 'direction': 'desc'}
        
        elif trigger == 'popup-menu-btn':
            return {
                "position": "absolute", 
                "backgroundColor": "white", 
                "padding": "4px 0",
                "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                "zIndex": "1000",
                "display": "block",
                "minWidth": "160px",
                "top": "200px",
                "left": "50px"
            }, True, dash.no_update
        
        elif trigger == 'popup-source-btn':
            return {
                "position": "absolute", 
                "backgroundColor": "white", 
                "padding": "4px 0",
                "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                "zIndex": "1000",
                "display": "none",
                "minWidth": "160px"
            }, False, {'type': 'source', 'direction': current_sort.get('direction', 'asc') if current_sort else 'asc'}
        
        elif trigger == 'popup-alphabetic-btn':
            return {
                "position": "absolute", 
                "backgroundColor": "white", 
                "padding": "4px 0",
                "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                "zIndex": "1000",
                "display": "none",
                "minWidth": "160px"
            }, False, {'type': 'alphabetic', 'direction': current_sort.get('direction', 'asc') if current_sort else 'asc'}
        
        elif trigger == 'popup-field-btn' or trigger == 'field-sort-btn':
            return dash.no_update, dash.no_update, {'type': 'field', 'direction': current_sort.get('direction', 'asc') if current_sort else 'asc'}
        
        elif trigger == 'popup-nested-btn' or trigger == 'nested-sort-btn':
            return dash.no_update, dash.no_update, {'type': 'nested', 'direction': current_sort.get('direction', 'asc') if current_sort else 'asc'}
        
        return {
            "position": "absolute", 
            "backgroundColor": "white", 
            "padding": "4px 0",
            "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
            "zIndex": "1000",
            "display": "none",
            "minWidth": "160px"
        }, False, dash.no_update

    # Apply sorting when sort order changes
    @app.callback(
        [Output('crude-comparison-table', 'data', allow_duplicate=True),
         Output('current-sort-order', 'data', allow_duplicate=True)],
        [Input('current-sort-order', 'data')],
        [State('original-data-store', 'data'),
         State('export-production-dropdown', 'value'),
         State('sum-row-store', 'data')],
        prevent_initial_call=True
    )
    def apply_sort_order(current_sort, original_data, mode, sum_row):
        if not original_data or not current_sort:
            return dash.no_update, dash.no_update
            
        sort_type = current_sort.get('type', 'alphabetic')
        direction = current_sort.get('direction', 'asc')
        
        # Convert back to DataFrame for sorting
        df = pd.DataFrame(original_data)
        
        if sort_type == 'alphabetic':
            df_sorted = df.sort_values('CrudeOil', ascending=(direction == 'asc'), na_position='last')
        elif sort_type in ['field', 'nested']:
            numeric_cols = [col for col in df.columns if col != 'CrudeOil']
            
            def calculate_sum(row):
                total = 0
                for col in numeric_cols:
                    val = row[col]
                    if val and str(val).strip() and str(val).strip() != '':
                        try:
                            clean_val = str(val).replace(',', '')
                            total += float(clean_val)
                        except (ValueError, TypeError):
                            continue
                return total
            
            df['_sum'] = df.apply(calculate_sum, axis=1)
            df_sorted = df.sort_values('_sum', ascending=(direction == 'asc'))
            df_sorted = df_sorted.drop('_sum', axis=1)
        else:
            df_sorted = df
        
        # Convert back to dict and add SUM row
        sorted_data = df_sorted.to_dict('records')
        if sum_row:
            sorted_data.append(sum_row)
        
        return sorted_data, dash.no_update

    # Handle sorting from popup menu text options
    @app.callback(
        [Output('crude-comparison-table', 'data', allow_duplicate=True),
         Output('current-sort-order', 'data', allow_duplicate=True)],
        [Input('popup-source-btn', 'n_clicks'),
         Input('popup-alphabetic-btn', 'n_clicks'),
         Input('popup-field-btn', 'n_clicks'),
         Input('popup-nested-btn', 'n_clicks')],
        [State('original-data-store', 'data'),
         State('current-sort-order', 'data'),
         State('export-production-dropdown', 'value'),
         State('sum-row-store', 'data')],
        prevent_initial_call=True
    )
    def handle_popup_sorting(popup_source_clicks, popup_alpha_clicks,
                           popup_field_clicks, popup_nested_clicks,
                           original_data, current_sort, mode, sum_row):
        if not original_data:
            return dash.no_update, dash.no_update
            
        trigger = ctx.triggered_id
        
        if trigger == 'popup-source-btn':
            sort_type = 'source'
        elif trigger == 'popup-alphabetic-btn':
            sort_type = 'alphabetic'
        elif trigger == 'popup-field-btn':
            sort_type = 'field'
        elif trigger == 'popup-nested-btn':
            sort_type = 'nested'
        else:
            return dash.no_update, dash.no_update
        
        direction = current_sort.get('direction', 'asc')
        
        df = pd.DataFrame(original_data)
        
        if sort_type == 'alphabetic':
            df_sorted = df.sort_values('CrudeOil', ascending=(direction == 'asc'), na_position='last')
        elif sort_type in ['field', 'nested']:
            numeric_cols = [col for col in df.columns if col != 'CrudeOil']
            
            def calculate_sum(row):
                total = 0
                for col in numeric_cols:
                    val = row[col]
                    if val and str(val).strip() and str(val).strip() != '':
                        try:
                            clean_val = str(val).replace(',', '')
                            total += float(clean_val)
                        except (ValueError, TypeError):
                            continue
                return total
            
            df['_sum'] = df.apply(calculate_sum, axis=1)
            df_sorted = df.sort_values('_sum', ascending=(direction == 'asc'))
            df_sorted = df_sorted.drop('_sum', axis=1)
        else:
            df_sorted = df
        
        sorted_data = df_sorted.to_dict('records')
        if sum_row:
            sorted_data.append(sum_row)
        
        return sorted_data, {'type': sort_type, 'direction': direction}

    @app.callback(
        [Output('external-url-store', 'data'),
         Output('selected-cell-store', 'data')],
        Input('crude-comparison-table', 'active_cell'),
        [State('crude-comparison-table', 'data'),
         State('selected-cell-store', 'data')],
        prevent_initial_call=True
    )
    def handle_cell_click(active_cell, data, previous_selected):
        if active_cell:
            row = active_cell['row']
            column = active_cell['column_id']
            
            if (column != "CrudeOil" and data and row is not None and 
                row < len(data) and data[row].get('CrudeOil') != 'SUM'):
                cell_value = data[row].get(column)
                crude_markdown = data[row].get('CrudeOil', '')
                
                if cell_value and str(cell_value).strip():
                    url_match = re.search(r'\[.*?\]\((.*?)\)', crude_markdown)
                    if url_match:
                        external_url = url_match.group(1)
                        selected_cell = {
                            'row': row,
                            'column': column,
                            'value': cell_value
                        }
                        return external_url, selected_cell
        
        raise dash.exceptions.PreventUpdate

    @app.callback(
        Output('crude-comparison-table', 'style_data_conditional'),
        [Input('selected-cell-store', 'data')],
        [State('crude-comparison-table', 'data')]
    )
    def update_table_styles(selected_cell, current_data):
        default_styles = [
            {"if": {"row_index": "odd"}, "backgroundColor": "#f9f9f9"},
            {"if": {"column_id": "CrudeOil"}, "color": "#1f3263"},
            {"if": {"column_id": [str(year) for year in range(2007, 2025)]}, "cursor": "pointer"},
            {"if": {"filter_query": '{CrudeOil} = "SUM"'}, "backgroundColor": "#1f3263", "color": "white", "fontWeight": "bold", "borderTop": "2px solid #d65a00"},
            {"if": {"filter_query": '{CrudeOil} = "SUM"', "column_id": "CrudeOil"}, "textAlign": "left", "backgroundColor": "#1f3263", "color": "white", "fontWeight": "bold"}
        ]
        
        if selected_cell:
            numeric_columns = [col for col in (current_data[0].keys() if current_data else []) if col != "CrudeOil"]
            
            style_conditions = [
                {"if": {"row_index": "odd"}, "backgroundColor": "#f9f9f9"},
                {"if": {"column_id": "CrudeOil"}, "color": "#1f3263", "backgroundColor": "white", "cursor": "pointer"},
                {"if": {"column_id": numeric_columns}, "color": "#f0f0f0", "backgroundColor": "white", "cursor": "pointer"},
                {"if": {"row_index": selected_cell['row'], "column_id": selected_cell['column']}, "color": "#1f3263", "backgroundColor": "#e6f3ff", "fontWeight": "bold", "border": "2px solid #1f3263", "cursor": "pointer"},
                {"if": {"filter_query": '{CrudeOil} = "SUM"'}, "backgroundColor": "#1f3263", "color": "white", "fontWeight": "bold", "borderTop": "2px solid #d65a00"},
                {"if": {"filter_query": '{CrudeOil} = "SUM"', "column_id": "CrudeOil"}, "textAlign": "left", "backgroundColor": "#1f3263", "color": "white", "fontWeight": "bold"}
            ]
            return style_conditions
        
        return default_styles

    # Client-side callback to open the external URL
    app.clientside_callback(
        """
        function(url) {
            if (url && url !== '') {
                window.open(url, '_blank');
            }
            return '';
        }
        """,
        Output('dummy-output', 'children'),
        Input('external-url-store', 'data')
    )

    # Add custom CSS for the header elements and tooltips
    app.clientside_callback(
        """
        function(n) {
            setTimeout(function() {
                // Add A/Z and SVG sort icon to CrudeOil header
                const crudeHeader = document.querySelector('.dash-header[data-dash-column="CrudeOil"]');
                if (crudeHeader && !crudeHeader.querySelector('.sort-order-container')) {
                    const sortContainer = document.createElement('div');
                    sortContainer.className = 'sort-order-container';
                    
                    const aElement = document.createElement('div');
                    aElement.className = 'sort-asc';
                    aElement.textContent = 'A';
                    aElement.title = 'Click for ascending alphabetical order';
                    aElement.onclick = function(e) {
                        e.stopPropagation();
                        const btn = document.getElementById('sort-asc-btn-hidden');
                        if (btn) btn.click();
                    };
                    
                    const zElement = document.createElement('div');
                    zElement.className = 'sort-desc';
                    zElement.textContent = 'Z';
                    zElement.title = 'Click for descending alphabetical order';
                    zElement.onclick = function(e) {
                        e.stopPropagation();
                        const btn = document.getElementById('sort-desc-btn-hidden');
                        if (btn) btn.click();
                    };
                    
                    sortContainer.appendChild(aElement);
                    sortContainer.appendChild(zElement);
                    
                    // Add SVG sort icon (same as year columns)
                    const sortIndicator = document.createElement('div');
                    sortIndicator.className = 'sort-indicator';
                    sortIndicator.title = 'Click to show sort options';
                    
                    // Add the exact SVG from your file
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
                        const btn = document.getElementById('popup-menu-btn');
                        if (btn) btn.click();
                    };
                    
                    crudeHeader.appendChild(sortContainer);
                    crudeHeader.appendChild(sortIndicator);
                }
                
                // Add SVG sort icons to ALL year columns (2024, 2023, etc.)
                const yearHeaders = document.querySelectorAll('.dash-header:not([data-dash-column="CrudeOil"])');
                yearHeaders.forEach(header => {
                    if (!header.querySelector('.sort-indicator')) {
                        const sortIndicator = document.createElement('div');
                        sortIndicator.className = 'sort-indicator';
                        sortIndicator.title = 'Click to show combined Production + Exports data';
                        
                        // Add the exact SVG from your file
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
                            const btn = document.getElementById('year-column-btn');
                            if (btn) btn.click();
                        };
                        
                        header.appendChild(sortIndicator);
                    }
                });
                
                // Add mouseover tooltips for Field and Nested arrows
                const fieldArrow = document.getElementById('field-arrow-btn');
                const nestedArrow = document.getElementById('nested-arrow-btn');
                
                if (fieldArrow) {
                    fieldArrow.title = 'Click to show combined Production + Exports data';
                    
                    fieldArrow.addEventListener('mouseover', function(e) {
                        const tooltip = document.createElement('div');
                        tooltip.className = 'arrow-tooltip';
                        tooltip.textContent = 'Click to show combined Production + Exports data';
                        tooltip.style.left = (e.pageX + 10) + 'px';
                        tooltip.style.top = (e.pageY - 25) + 'px';
                        document.body.appendChild(tooltip);
                        
                        fieldArrow._tooltip = tooltip;
                    });
                    
                    fieldArrow.addEventListener('mouseout', function(e) {
                        if (fieldArrow._tooltip) {
                            fieldArrow._tooltip.remove();
                            fieldArrow._tooltip = null;
                        }
                    });
                    
                    fieldArrow.addEventListener('mousemove', function(e) {
                        if (fieldArrow._tooltip) {
                            fieldArrow._tooltip.style.left = (e.pageX + 10) + 'px';
                            fieldArrow._tooltip.style.top = (e.pageY - 25) + 'px';
                        }
                    });
                    
                    // Make Field arrow clickable
                    fieldArrow.onclick = function(e) {
                        e.stopPropagation();
                        const btn = document.getElementById('field-sort-btn');
                        if (btn) btn.click();
                    };
                }
                
                if (nestedArrow) {
                    nestedArrow.title = 'Click to show combined Production + Exports data';
                    
                    nestedArrow.addEventListener('mouseover', function(e) {
                        const tooltip = document.createElement('div');
                        tooltip.className = 'arrow-tooltip';
                        tooltip.textContent = 'Click to show combined Production + Exports data';
                        tooltip.style.left = (e.pageX + 10) + 'px';
                        tooltip.style.top = (e.pageY - 25) + 'px';
                        document.body.appendChild(tooltip);
                        
                        nestedArrow._tooltip = tooltip;
                    });
                    
                    nestedArrow.addEventListener('mouseout', function(e) {
                        if (nestedArrow._tooltip) {
                            nestedArrow._tooltip.remove();
                            nestedArrow._tooltip = null;
                        }
                    });
                    
                    nestedArrow.addEventListener('mousemove', function(e) {
                        if (nestedArrow._tooltip) {
                            nestedArrow._tooltip.style.left = (e.pageX + 10) + 'px';
                            nestedArrow._tooltip.style.top = (e.pageY - 25) + 'px';
                        }
                    });
                    
                    // Make Nested arrow clickable
                    nestedArrow.onclick = function(e) {
                        e.stopPropagation();
                        const btn = document.getElementById('nested-sort-btn');
                        if (btn) btn.click();
                    };
                }
                
            }, 100);
            return '';
        }
        """,
        Output('dummy-output-2', 'children'),
        Input('crude-comparison-table', 'columns'),
        prevent_initial_call=False
    )