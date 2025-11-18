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
# INITIAL LOAD
# ------------------------------------------------------------------------------
crude_data, columns = load_crude_data("production")

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

            # Sorting dropdown (initially hidden)
            html.Div([
                html.Div("Sort order", style={
                    "fontWeight": "bold", 
                    "marginBottom": "8px",
                    "fontSize": "12px"
                }),
                
                html.Div([
                    html.Button("▲ Ascending", id="sort-asc-btn", n_clicks=0, 
                               style={
                                   "marginRight": "5px", 
                                   "padding": "4px 8px", 
                                   "fontSize": "11px",
                                   "border": "1px solid #ccc",
                                   "backgroundColor": "#f8f9fa",
                                   "cursor": "pointer"
                               }),
                    html.Button("▼ Descending", id="sort-desc-btn", n_clicks=0,
                               style={
                                   "padding": "4px 8px", 
                                   "fontSize": "11px",
                                   "border": "1px solid #ccc",
                                   "backgroundColor": "#f8f9fa",
                                   "cursor": "pointer"
                               }),
                ], style={"marginBottom": "10px"}),
                
                html.Div("Sort by:", style={
                    "fontSize": "11px", 
                    "marginBottom": "5px",
                    "color": "#666"
                }),
                
                dcc.Dropdown(
                    id="sort-options-dropdown",
                    options=[
                        {"label": "Data source order", "value": "source"},
                        {"label": "Alphabetic", "value": "alphabetic"},
                        {"label": "Field", "value": "field"},
                        {"label": "Nested", "value": "nested"},
                    ],
                    value="source",
                    clearable=False,
                    style={
                        "width": "180px",
                        "fontSize": "11px",
                        "fontFamily": "Arial",
                    }
                ),
                
                html.Div(id="sort-sum-display", style={
                    "marginTop": "8px",
                    "fontSize": "10px",
                    "color": "#666",
                    "fontStyle": "italic"
                }),
            ], id="sorting-controls", style={
                "position": "absolute", 
                "backgroundColor": "white", 
                "border": "1px solid #ccc",
                "padding": "12px",
                "borderRadius": "4px",
                "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                "zIndex": "1000",
                "display": "none",
                "minWidth": "200px"
            }),

            dash_table.DataTable(
                id="crude-comparison-table",
                data=crude_data,
                columns=columns,
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
                    "padding": "2px 4px",
                    "fontSize": "12px",
                    "fontFamily": "Arial",
                    "border": "1px solid #e2e2e2",
                    "whiteSpace": "normal",
                    "height": "35px",
                    "cursor": "pointer",
                },
                style_header={
                    "backgroundColor": "#f2f2f2",
                    "fontWeight": "bold",
                    "fontSize": "12px",
                    "border": "1px solid #d0d0d0",
                    "cursor": "pointer",
                    "position": "relative",
                },
                style_cell_conditional=[
                    {
                        "if": {"column_id": "CrudeOil"},
                        "textAlign": "left",
                        "fontWeight": "600",
                        "minWidth": "160px",
                        "backgroundColor": "#FFFFFF",
                        "borderRight": "2px solid #d0d0d0",
                        "paddingLeft": "10px",
                        "paddingTop": "5px",
                        "paddingBottom": "5px",
                        "color": "#1f3263",
                        "cursor": "pointer",
                    },
                    {
                        "if": {"column_id": "CrudeOil", "header": True},
                        "color": "#1f3263",
                        "cursor": "pointer",
                        "position": "relative",
                    },
                ],
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "#f9f9f9"},
                    {
                        "if": {"column_id": "CrudeOil"},
                        "color": "#1f3263",
                    },
                    # Default style for all numeric cells
                    {
                        "if": {"column_id": [str(year) for year in range(2007, 2025)]},
                        "cursor": "pointer",
                    }
                ],
                css=[
                    {
                        'selector': '.dash-cell[data-dash-column="CrudeOil"] a',
                        'rule': '''
                            color: #1f3263 !important; 
                            text-decoration: underline !important;
                            font-weight: 600 !important;
                            cursor: pointer !important;
                        '''
                    },
                    {
                        'selector': '.dash-cell[data-dash-column="CrudeOil"] a:hover',
                        'rule': '''
                            color: #1f3263 !important; 
                            text-decoration: underline !important;
                            background-color: #f0f5ff !important;
                        '''
                    },
                    {
                        'selector': '.dash-header[data-dash-column="CrudeOil"]',
                        'rule': '''
                            color: #1f3263 !important;
                            position: relative !important;
                        '''
                    },
                    {
                        'selector': '.dash-header[data-dash-column="CrudeOil"]:hover::after',
                        'rule': '''
                            content: "▼";
                            position: absolute;
                            right: 8px;
                            top: 50%;
                            transform: translateY(-50%);
                            font-size: 10px;
                            color: #666;
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
            dcc.Store(id='original-data-store', data=crude_data),
            dcc.Store(id='current-sort-order', data={'type': 'source', 'direction': 'asc'}),
            dcc.Store(id='show-sorting-controls', data=False),
            html.Div(id='dummy-output', style={'display': 'none'}),
            html.Div(id='header-click-trigger', style={'display': 'none'}),

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
        Input("export-production-dropdown", "value"),
    )
    def update_header(selected):
        title = "Exports ('000 b/d)" if selected == "exports" else "Production ('000 b/d)"
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
         Output("original-data-store", "data")],
        Input("export-production-dropdown", "value"),
    )
    def reload_data(mode):
        crude_data, _ = load_crude_data(mode)
        return crude_data, crude_data

    @app.callback(
        Output("crude-comparison-table", "columns"),
        Input("export-production-dropdown", "value"),
    )
    def reload_columns(mode):
        _, columns = load_crude_data(mode)
        return columns

    # Toggle sorting controls visibility
    @app.callback(
        [Output('sorting-controls', 'style'),
         Output('show-sorting-controls', 'data')],
        [Input('crude-comparison-table', 'active_cell'),
         Input('sort-asc-btn', 'n_clicks'),
         Input('sort-desc-btn', 'n_clicks'),
         Input('sort-options-dropdown', 'value')],
        [State('show-sorting-controls', 'data'),
         State('crude-comparison-table', 'data')]
    )
    def toggle_sorting_controls(active_cell, asc_clicks, desc_clicks, sort_value, show_controls, table_data):
        trigger = ctx.triggered_id
        
        if trigger == 'crude-comparison-table' and active_cell:
            # Check if CrudeOil header was clicked
            if active_cell['column_id'] == 'CrudeOil' and active_cell['row'] is None:
                # Show the sorting controls
                return {
                    "position": "absolute", 
                    "backgroundColor": "white", 
                    "border": "1px solid #ccc",
                    "padding": "12px",
                    "borderRadius": "4px",
                    "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                    "zIndex": "1000",
                    "display": "block",
                    "minWidth": "200px",
                    "top": "200px",
                    "left": "50px"
                }, True
        elif trigger in ['sort-asc-btn', 'sort-desc-btn', 'sort-options-dropdown']:
            # Hide after selection
            return {
                "position": "absolute", 
                "backgroundColor": "white", 
                "border": "1px solid #ccc",
                "padding": "12px",
                "borderRadius": "4px",
                "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                "zIndex": "1000",
                "display": "none",
                "minWidth": "200px"
            }, False
        
        # Default: hide controls
        return {
            "position": "absolute", 
            "backgroundColor": "white", 
            "border": "1px solid #ccc",
            "padding": "12px",
            "borderRadius": "4px",
            "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
            "zIndex": "1000",
            "display": "none",
            "minWidth": "200px"
        }, False

    # Show SUM values for Field and Nested options
    @app.callback(
        Output('sort-sum-display', 'children'),
        [Input('sort-options-dropdown', 'value'),
         Input('export-production-dropdown', 'value')],
        [State('crude-comparison-table', 'data')]
    )
    def show_sum_display(sort_type, mode, table_data):
        if not table_data:
            return ""
            
        if sort_type in ['field', 'nested']:
            # Calculate total sum for all data
            df = pd.DataFrame(table_data)
            numeric_cols = [col for col in df.columns if col != 'CrudeOil']
            
            total_sum = 0
            for col in numeric_cols:
                for val in df[col]:
                    if val and str(val).strip() and str(val).strip() != '':
                        try:
                            # Remove commas from numbers like "1,000"
                            clean_val = str(val).replace(',', '')
                            total_sum += float(clean_val)
                        except (ValueError, TypeError):
                            continue
            
            mode_text = "Production" if mode == "production" else "Exports"
            return f"SUM({mode_text} Value): {total_sum:,.0f}"
        
        return ""

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
            
            # Only process clicks on numeric columns (not CrudeOil column)
            if column != "CrudeOil" and data and row is not None and row < len(data):
                cell_value = data[row].get(column)
                crude_markdown = data[row].get('CrudeOil', '')
                
                # Only navigate if there's a valid number (including 0)
                if cell_value and str(cell_value).strip():
                    # Extract the EXTERNAL URL from the CrudeOil markdown link
                    url_match = re.search(r'\[.*?\]\((.*?)\)', crude_markdown)
                    if url_match:
                        external_url = url_match.group(1)
                        
                        # Store the selected cell information
                        selected_cell = {
                            'row': row,
                            'column': column,
                            'value': cell_value
                        }
                        
                        return external_url, selected_cell
        
        # Return no update if conditions aren't met
        raise dash.exceptions.PreventUpdate

    @app.callback(
        Output('crude-comparison-table', 'style_data_conditional'),
        [Input('selected-cell-store', 'data')],
        [State('crude-comparison-table', 'data')]
    )
    def update_table_styles(selected_cell, current_data):
        # Default styles - show all values normally
        default_styles = [
            {"if": {"row_index": "odd"}, "backgroundColor": "#f9f9f9"},
            {"if": {"column_id": "CrudeOil"}, "color": "#1f3263"},
            {"if": {"column_id": [str(year) for year in range(2007, 2025)]}, "cursor": "pointer"}
        ]
        
        # If a cell is selected, make other numbers very light (almost hidden)
        if selected_cell:
            # Get all column IDs except CrudeOil
            numeric_columns = [col for col in (current_data[0].keys() if current_data else []) 
                             if col != "CrudeOil"]
            
            style_conditions = [
                # Keep row striping
                {"if": {"row_index": "odd"}, "backgroundColor": "#f9f9f9"},
                
                # Keep CrudeOil column always visible
                {
                    "if": {"column_id": "CrudeOil"},
                    "color": "#1f3263",
                    "backgroundColor": "white",
                    "cursor": "pointer"
                },
                
                # Make ALL numeric cells very light gray (almost hidden but still visible)
                {
                    "if": {
                        "column_id": numeric_columns
                    },
                    "color": "#f0f0f0",  # Very light gray - almost invisible
                    "backgroundColor": "white",
                    "cursor": "pointer"
                },
                
                # Show ONLY the selected cell normally with highlight
                {
                    "if": {
                        "row_index": selected_cell['row'],
                        "column_id": selected_cell['column']
                    },
                    "color": "#1f3263",
                    "backgroundColor": "#e6f3ff",
                    "fontWeight": "bold",
                    "border": "2px solid #1f3263",
                    "cursor": "pointer"
                }
            ]
            return style_conditions
        
        # Return default styles when no cell is selected
        return default_styles

    # Handle sorting
    @app.callback(
        [Output('crude-comparison-table', 'data', allow_duplicate=True),
         Output('current-sort-order', 'data')],
        [Input('sort-asc-btn', 'n_clicks'),
         Input('sort-desc-btn', 'n_clicks'),
         Input('sort-options-dropdown', 'value')],
        [State('crude-comparison-table', 'data'),
         State('current-sort-order', 'data'),
         State('export-production-dropdown', 'value')],
        prevent_initial_call=True
    )
    def handle_sorting(asc_clicks, desc_clicks, sort_type, current_data, current_sort, mode):
        if not current_data:
            return dash.no_update, dash.no_update
            
        trigger = ctx.triggered_id
        
        if trigger == 'sort-asc-btn':
            direction = 'asc'
        elif trigger == 'sort-desc-btn':
            direction = 'desc'
        else:
            direction = current_sort.get('direction', 'asc')
        
        # Convert back to DataFrame for sorting
        df = pd.DataFrame(current_data)
        
        if sort_type == 'alphabetic':
            # Sort by CrudeOil name alphabetically
            df_sorted = df.sort_values('CrudeOil', ascending=(direction == 'asc'), na_position='last')
        elif sort_type in ['field', 'nested']:
            # Calculate sum for Field/Nested sorting
            numeric_cols = [col for col in df.columns if col != 'CrudeOil']
            
            def calculate_sum(row):
                total = 0
                for col in numeric_cols:
                    val = row[col]
                    if val and str(val).strip() and str(val).strip() != '':
                        try:
                            # Remove commas from numbers like "1,000"
                            clean_val = str(val).replace(',', '')
                            total += float(clean_val)
                        except (ValueError, TypeError):
                            continue
                return total
            
            df['_sum'] = df.apply(calculate_sum, axis=1)
            df_sorted = df.sort_values('_sum', ascending=(direction == 'asc'))
            df_sorted = df_sorted.drop('_sum', axis=1)
        else:  # source order - return to original order
            # Reload original data to get source order
            original_data, _ = load_crude_data(mode)
            df_sorted = pd.DataFrame(original_data)
        
        return df_sorted.to_dict('records'), {'type': sort_type, 'direction': direction}

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