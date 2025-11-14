from dash import dcc, html, Input, Output, dash_table
import pandas as pd
import os
import chardet

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
    """
    mode = 'production' or 'exports'
    Load correct CSV and clean fully.
    """

    if mode == "production":
        csv_path = "/home/lifo/Documents/Energy/Energyintel/app/dashboards/data/production-crude-comparison.csv"
    else:
        csv_path = "/home/lifo/Documents/Energy/Energyintel/app/dashboards/data/exports-crude-comparison.csv"

    if not os.path.exists(csv_path):
        print(f"❌ File missing: {csv_path}. Using sample.")
        return get_sample()

    encoding = detect_encoding(csv_path)

    # SAFE CSV reading
    try:
        df = pd.read_csv(
            csv_path,
            encoding=encoding,
            sep=None,            # auto-detect delimiter
            engine="python",     # safe parser
            on_bad_lines="skip", # skip corrupted rows
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

    # 2️⃣ Detect header row (first row containing the word "crude")
    header_row_index = df[
        df.apply(lambda row: "crude" in " ".join(row.astype(str)).lower(), axis=1)
    ].index

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

    # 5️⃣ Clean up - Drop rows where ALL columns are empty/NaN
    df = df.dropna(how="all")
    
    # Also drop rows where all values are empty strings
    df = df[~df.apply(lambda row: all(str(x).strip() == "" for x in row), axis=1)]
    
    df = df.fillna("")
    df.columns = [c.strip() for c in df.columns]

    # -----------------------------
    # Convert CrudeOil to clickable URLs
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
# INITIAL LOAD (Default → Production)
# ------------------------------------------------------------------------------
crude_data, columns = load_crude_data("production")

# ------------------------------------------------------------------------------
# LAYOUT
# ------------------------------------------------------------------------------
def create_layout(server):
    return html.Div(
        children=[
            # ----------------- Dropdown -----------------
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

            # ----------------- Heading -----------------
            html.Div(id="crude-heading", style={"textAlign": "center"}),

            html.Hr(style={"margin": "10px 0", "border": "1px solid #ccc"}),

            # ----------------- Table -----------------
            dash_table.DataTable(
                id="crude-comparison-table",
                data=crude_data,
                columns=columns,
                style_table={
                    "overflowX": "auto",
                    "overflowY": "auto",
                    "maxHeight": "630px",
                    "border": "1px solid #d9d9d9",
                    "backgroundColor": "white",
                },
                style_cell={
                    "textAlign": "center",
                    "padding": "6px",
                    "fontSize": "12px",
                    "fontFamily": "Arial",
                    "border": "1px solid #e2e2e2",
                },
                style_header={
                    "backgroundColor": "#f2f2f2",
                    "fontWeight": "bold",
                    "fontSize": "12px",
                    "color": "#444",
                    "border": "1px solid #d0d0d0",
                },
                style_cell_conditional=[
                    {
                        "if": {"column_id": "CrudeOil"},
                        "textAlign": "left",
                        "fontWeight": "600",
                        "minWidth": "160px",
                        "backgroundColor": "#fafafa",
                        "borderRight": "2px solid #d0d0d0",
                        "paddingLeft": "10px",
                    }
                ],
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "#f9f9f9"}
                ],
                fixed_rows={"headers": True},
                page_action="none",
                sort_action="none",
                filter_action="none",
            ),

            # ----------------- Data Source -----------------
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
        }
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
        Output("crude-comparison-table", "data"),
        Input("export-production-dropdown", "value"),
    )
    def reload_data(mode):
        crude_data, _ = load_crude_data(mode)
        return crude_data

    @app.callback(
        Output("crude-comparison-table", "columns"),
        Input("export-production-dropdown", "value"),
    )
    def reload_columns(mode):
        _, columns = load_crude_data(mode)
        return columns