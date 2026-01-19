import json
import os
import unicodedata
import logging
from urllib.request import urlopen
import dash
from dash import (
    ALL,
    Input,
    Output,
    State,
    callback_context,
    dcc,
    html,
    dash_table,
    no_update,
)
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from config import Config
from core.data_helpers import execute_query
from core.country_mappings import COUNTRY_TO_ISO, get_iso_code
from .shared_map_utils import (
    create_choropleth_map,
    get_mapbox_config,
    load_world_geojson,
    handle_map_click_reset,
    create_empty_map,
    MAP_BACKGROUND_COLOR,
    WORLD_CENTER,
    WORLD_ZOOM
)

# Set up logging first
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Data locations and shared constants
# ---------------------------------------------------------------------

GROUP_COLORS = {
    "OPEC-Plus": "#f5a555",
    "Non-OPEC-Plus": "#7194b9", 
}
DEFAULT_GROUPS = list(GROUP_COLORS.keys())
DEFAULT_LIKELY = ["Y"]

# Lazily populated globals (avoid repeated disk I/O)
map_df = pd.DataFrame()
chart_df = pd.DataFrame()
table_df = pd.DataFrame()
country_colors = {}

# Mapbox token (optional) with enhanced error handling
try:
    if Config.MAPBOX_ACCESS_TOKEN:
        token = Config.MAPBOX_ACCESS_TOKEN.strip()
        if token.startswith('pk.'):
            px.set_mapbox_access_token(token)
            logger.info(f"Mapbox token configured: {token[:20]}...")
        else:
            logger.warning(f"Invalid Mapbox token format: {token[:10]}...")
    else:
        logger.warning("No Mapbox token configured - maps will use geo fallback")
except Exception as e:
    logger.error(f"Error configuring Mapbox token: {e}")


# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------
def _normalize_group(raw_value: str | None) -> str | None:
    """Normalize group names to OPEC / Non-OPEC buckets.
    Handles SQL query values: 'opec_plus' and 'Non opec_plus'
    Converts them to UI format: 'OPEC-Plus' and 'Non-OPEC-Plus'
    """
    if raw_value is None:
        return None
    value = str(raw_value).strip()
    if not value:
        return None
    lower = value.lower()
    
    # Handle SQL query normalized values
    if lower == "opec_plus":
        return "OPEC-Plus"
    if lower == "non opec_plus" or lower == "non_opec_plus":
        return "Non-OPEC-Plus"
    
    # Handle legacy/other formats
    if "non" in lower:
        return "Non-OPEC-Plus"
    return "OPEC-Plus"


def _iso_for_country(country: str | None) -> str | None:
    """Return ISO Alpha-3 code for a country, using centralized mapping."""
    return get_iso_code(country)


def _build_country_colors(countries: list[str]) -> dict[str, str]:
    """Generate a stable color map for countries (Tableau-like palette)."""
    if countries:
        palette = [
            "#4E79A7",
            "#F28E2B",
            "#E15759",
            "#76B7B2",
            "#59A14F",
            "#EDC948",
            "#B07AA1",
            "#FF9DA7",
            "#9C755F",
            "#BAB0AC",
            "#1F77B4",
            "#FF7F0E",
            "#2CA02C",
            "#D62728",
            "#9467BD",
            "#8C564B",
            "#E377C2",
            "#7F7F7F",
            "#BCBD22",
            "#17BECF",
        ]
        color_map = {}
        for idx, country in enumerate(sorted(countries)):
            color_map[country] = palette[idx % len(palette)]
        return color_map
    return {}


def _ordered_countries() -> list[str]:
    """Return countries in the same stable ordering used to render legend blocks."""
    df = load_map_data()
    if df.empty:
        return []
    return sorted(df["Country"].unique().tolist())


def _normalize_country_name(name: str | None) -> str:
    """Return ASCII/English-friendly country name."""
    if name is None:
        return ""
    text = str(name).strip()
    if not text:
        return ""
    # Remove accents/diacritics
    text = (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return text


def _standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names to be proper-case for internal consistency."""
    rename_map = {}
    for col in df.columns:
        low = col.lower()
        if low == "country": rename_map[col] = "Country"
        elif low == "group": rename_map[col] = "Group"
        elif "latitude" in low: rename_map[col] = "Latitude"
        elif "longitude" in low: rename_map[col] = "Longitude"
        elif low == "quarter": rename_map[col] = "Quarter"
        elif low == "productionadditions": rename_map[col] = "ProductionAdditions"
        elif low == "likely_goahead": rename_map[col] = "likely_goahead"
        elif low == "opec_group": rename_map[col] = "Opec_group"
    return df.rename(columns=rename_map)


def _normalize_likely(val: str) -> str:
    """Standardize Likely To Go Ahead status values."""
    if pd.isna(val) or val is None:
        return ""
    text = str(val or "").strip().lower()
    if not text or text in ("nan", "none", "null", "undefined"):
        return ""
    if text.startswith("y"):
        return "Y"
    if text.startswith("n"):
        return "N"
    if "uncertain" in text:
        return "Uncertain"
    return text.capitalize()


def _resolve_countries(selected: list[str] | None, all_countries: list[str]) -> list[str]:
    """Return concrete country list honoring '(All)' convenience value."""
    if not selected:
        return []
    if "(All)" in selected:
        return all_countries
    return [c for c in selected if c in all_countries]


def _quarter_components(quarter_str: str) -> tuple[int, int]:
    """Return (year, quarter_number) parsed from 'YYYY Q#' strings."""
    if not quarter_str:
        return 0, 0
    parts = str(quarter_str).replace("_", " ").split()
    year = 0
    q_num = 0
    for part in parts:
        if part.lower().startswith("q"):
            try:
                q_num = int(part.lower().replace("q", ""))
            except Exception:
                q_num = 0
        else:
            try:
                year = int(part)
            except Exception:
                year = 0
    return year, q_num


def _build_match_expression(df_subset: pd.DataFrame, color_map: dict[str, str]):
    """
    Build a Mapbox match expression keyed on iso_3166_1_alpha_3 to ensure
    country-level coloring matches the legend selection, even when using the
    vector country boundaries source.
    """
    expr = ["match", ["get", "iso_3166_1_alpha_3"]]
    for _, row in df_subset.iterrows():
        iso = row.get("iso_alpha")
        country = row.get("Country")
        if pd.isna(iso):
            continue
        expr.extend([iso, color_map.get(country, "#888")])
    expr.append("#cccccc")  # fallback color
    return expr


# ---------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------
def load_map_data() -> pd.DataFrame:
    """Load and cache map data from SQL query."""
    global map_df, country_colors
    
    def _normalize_map_df(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["Country"] = (
            df["Country"].astype(str).str.strip().apply(_normalize_country_name)
        )
        df["Group"] = df["Group"].apply(_normalize_group)
        df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
        df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
        df = df.dropna(subset=["Country", "Group", "Latitude", "Longitude"])
        # Removed drop_duplicates by Country here to preserve project statuses for filtering
        df["iso_alpha"] = df["Country"].apply(_iso_for_country)
        df = df.dropna(subset=["iso_alpha"])
        return df

    if map_df.empty:
        try:
            query = """
            SELECT DISTINCT
                c.country_long_name AS "Country",
                CASE
                    WHEN LOWER(c.opec_grp) IN ('opec', 'opec_plus') THEN 'OPEC-Plus'
                    ELSE 'Non-OPEC-Plus'
                END AS "Group",
                c.latitude AS "Latitude (generated)",
                c.longitude AS "Longitude (generated)",
                COALESCE(est.likely_goahead, a.likely_goahead) AS likely_goahead
            FROM fact_upstream_project_tracker a
            LEFT JOIN dim_country c
                ON a.country_id = c.dim_country_id
            LEFT JOIN fact_upstream_tracker_prod_estimates est
                ON a.project_id = est.project_id
            WHERE a.include = true
            ORDER BY c.country_long_name DESC;
            """
            
            results = execute_query(query)
            if not results:
                logger.warning("SQL query returned no results for map data")
                return pd.DataFrame()
            
            df = pd.DataFrame(results)
            
            if df.empty:
                logger.warning("Dataframe is empty after SQL query")
                return pd.DataFrame()

            # Standardize columns first
            df = _standardize_column_names(df)
            
            # Filter data
            df = _normalize_map_df(df)
            df["likely_goahead_normalized"] = df["likely_goahead"].apply(_normalize_likely)
            
            map_df = df
            country_colors = _build_country_colors(map_df["Country"].unique().tolist())
            return map_df
        except Exception as e:
            logger.error(f"Error loading map data from SQL: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    else:
        # If map_df is not empty, we still want to ensure country_colors is populated
        if not country_colors:
            country_colors = _build_country_colors(map_df["Country"].unique().tolist())

    return map_df


def load_chart_data(likely_filter: list[str] | None = None) -> pd.DataFrame:
    """Load chart data from SQL query, optionally filtering by likely status."""
    global chart_df
    # We disable global caching when a filter is applied to ensure dynamic results
    if likely_filter is None and not chart_df.empty:
        return chart_df

    where_clause = "WHERE a.include = TRUE"
    if likely_filter and "(All)" not in likely_filter:
        conditions = []
        for val in likely_filter:
            # Use COALESCE directly for status expression to maximize NULL-matching reliability
            status_expr = "COALESCE(est.likely_goahead, a.likely_goahead)"
            raw_expr = "LOWER(TRIM(COALESCE(est.likely_goahead, a.likely_goahead)))"
            
            if val == "":  # (Empty)
                conditions.append(f"({status_expr} IS NULL OR {raw_expr} = '' OR {raw_expr} IN ('nan', 'none', 'null', 'undefined'))")
            else:
                # Use LIKE to handle 'Y' -> 'yes', 'N' -> 'no', etc.
                conditions.append(f"{raw_expr} LIKE '{val.lower()}%'")
        if conditions:
            where_clause += f" AND ({' OR '.join(conditions)})"

    try:
        query = f"""
        WITH unpivoted AS (
            SELECT
                c.country_long_name AS Country,
                CASE
                    WHEN c.opec_grp = 'opec' OR c.opec_grp = 'opec_plus' THEN 'OPEC-Plus'
                    ELSE 'Non-OPEC-Plus'
                END AS Opec_group,
                q.quarter AS Quarter,
                q.value
            FROM fact_upstream_project_tracker a
            LEFT JOIN fact_upstream_tracker_prod_estimates est
                ON a.project_id = est.project_id
            LEFT JOIN dim_country c
                ON a.country_id = c.dim_country_id
            CROSS JOIN LATERAL (
                VALUES
                    ('2024 Q1', est."2024_Q1"), ('2024 Q2', est."2024_Q2"),
                    ('2024 Q3', est."2024_Q3"), ('2024 Q4', est."2024_Q4"),
                    ('2025 Q1', est."2025_Q1"), ('2025 Q2', est."2025_Q2"),
                    ('2025 Q3', est."2025_Q3"), ('2025 Q4', est."2025_Q4"),
                    ('2026 Q1', est."2026_Q1"), ('2026 Q2', est."2026_Q2"),
                    ('2026 Q3', est."2026_Q3"), ('2026 Q4', est."2026_Q4"),
                    ('2027 Q1', est."2027_Q1"), ('2027 Q2', est."2027_Q2"),
                    ('2027 Q3', est."2027_Q3"), ('2027 Q4', est."2027_Q4"),
                    ('2028 Q1', est."2028_Q1"), ('2028 Q2', est."2028_Q2"),
                    ('2028 Q3', est."2028_Q3"), ('2028 Q4', est."2028_Q4"),
                    ('2029 Q1', est."2029_Q1"), ('2029 Q2', est."2029_Q2"),
                    ('2029 Q3', est."2029_Q3"), ('2029 Q4', est."2029_Q4")
            ) AS q(quarter, value)
            {where_clause}
        ),
        aggregated AS (
            SELECT
                Quarter,
                Country,
                Opec_group,
                SUM(value) AS ProductionAdditions
            FROM unpivoted
            GROUP BY Quarter, Country, Opec_group
        )
        SELECT * FROM aggregated
        ORDER BY
            SPLIT_PART(Quarter, ' ', 1)::INT,
            SPLIT_PART(Quarter, ' ', 2);
        """
        
        results = execute_query(query)
        if not results:
            logger.warning("SQL query returned no results for chart data")
            return pd.DataFrame()
            
        df = pd.DataFrame(results)
        df = _standardize_column_names(df)
        
        # If no filter applied, we can cache the result
        if likely_filter is None:
            chart_df = df
        
        if df.empty:
            logger.warning("SQL query returned empty DataFrame for chart data")
            return pd.DataFrame()

        df["Country"] = (
            df["Country"]
            .fillna("")
            .astype(str)
            .str.strip()
            .apply(_normalize_country_name)
        )
        df = df[df["Country"] != ""]
        df["Group"] = df["Country"].map(
            load_map_data().set_index("Country")["Group"].to_dict()
        )
        df["Quarter"] = df["Quarter"].astype(str).str.strip()
        df[["Year", "QuarterNum"]] = df["Quarter"].apply(
            lambda q: pd.Series(_quarter_components(q))
        )
        df["ProductionAdditions"] = pd.to_numeric(
            df["ProductionAdditions"], errors="coerce"
        ).fillna(0)
        df = df.sort_values(["Year", "QuarterNum"])
        return df
    except Exception as e:
        logger.error(f"Error loading chart data from SQL: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def load_table_data() -> pd.DataFrame:
    """Load and cache the project detail table data."""
    global table_df
    if not table_df.empty:
        return table_df

    try:
        query = """
        SELECT
            a.project_name AS "Project Name",
            COALESCE(est.likely_goahead, a.likely_goahead) AS likely_goahead,
            c.country_long_name AS Country,
            c.region AS Region,
            CASE
                WHEN c.opec_grp = 'opec' OR c.opec_grp = 'opec_plus' THEN 'Opec-Plus'
                ELSE 'Non-Opec-Plus'
            END AS Opec_group,
            a.field_type,
            a.field,
            a.play_type,
            a.hydrocarbon AS Hydrocarbon,
            cr.crude_name AS "Associated Crude",
            a.depth AS Depth,
            op.company_name AS Operator,
            p1.company_name AS Partner1,
            p2.company_name AS Partner2,
            p3.company_name AS Partner3,
            p4.company_name AS Partner4,
            p5.company_name AS Partner5,
            yr.year AS "First Oil Year",
            a.sanctioned AS Sanctioned,
            a.external_comments AS Comments,
            a.project_status AS "Project Status",
            a.reserves_gas_mmboe AS "Gas Reserves (mmboe)",
            a.reserves_liquids_mmbbl AS "Liquids Reserves (mmbbl)",
            (
                COALESCE(
                    NULLIF(SPLIT_PART(a.reserves_gas_mmboe, '-', 1), '')::numeric,
                    0
                )
                +
                COALESCE(
                    NULLIF(SPLIT_PART(a.reserves_liquids_mmbbl, '-', 1), '')::numeric,
                    0
                )
            ) AS "Total Reserves (mmboe)",
            a.api_cat AS API,
            a.sulfur_cat AS Sulfur,
            a.operator_pc AS "Operator Share %",
            a.partner1_pc AS "Partner1 Share %",
            a.partner2_pc AS "Partner2 Share %",
            a.partner3_pc AS "Partner3 Share %",
            a.partner4_pc AS "Partner4 Share %",
            a.partner5_pc AS "Partner5 Share %",
            est."2024_Q1",
            est."2024_Q2",
            est."2024_Q3",
            est."2024_Q4",
            est."2025_Q1",
            est."2025_Q2",
            est."2025_Q3",
            est."2025_Q4",
            est."2026_Q1",
            est."2026_Q2",
            est."2026_Q3",
            est."2026_Q4",
            est."2027_Q1",
            est."2027_Q2",
            est."2027_Q3",
            est."2027_Q4",
            est."2028_Q1",
            est."2028_Q2",
            est."2028_Q3",
            est."2028_Q4",
            est."2029_Q1",
            est."2029_Q2",
            est."2029_Q3",
            est."2029_Q4"
        FROM fact_upstream_project_tracker a
        LEFT JOIN fact_upstream_tracker_prod_estimates est 
            ON a.project_id = est.project_id
        LEFT JOIN dim_country c 
            ON a.country_id = c.dim_country_id
        LEFT JOIN dim_company op 
            ON a.operator_id = op.company_id
        LEFT JOIN dim_company p1 
            ON a.partner1_id = p1.company_id
        LEFT JOIN dim_company p2 
            ON a.partner2_id = p2.company_id
        LEFT JOIN dim_company p3 
            ON a.partner3_id = p3.company_id
        LEFT JOIN dim_company p4 
            ON a.partner4_id = p4.company_id
        LEFT JOIN dim_company p5 
            ON a.partner5_id = p5.company_id
        LEFT JOIN (
            SELECT 
                project_id,
                MIN(EXTRACT(YEAR FROM period)) AS year
            FROM fact_upstream_tracker_prod_estimates_incremental
            WHERE value IS NOT NULL 
            GROUP BY project_id
        ) yr ON yr.project_id = a.project_id
        LEFT JOIN dim_crude cr 
            ON cr.dim_crude_id = a.crude_id
        WHERE a.include = TRUE
        ORDER BY a.project_name;
        """
        
        results = execute_query(query)
        if not results:
            return pd.DataFrame()
            
        df = pd.DataFrame(results)
        df = _standardize_column_names(df)
        if "Country" in df.columns:
            df["Country"] = df["Country"].astype(str).str.strip().apply(_normalize_country_name)
        if "Opec_group" in df.columns:
            df["Opec_group"] = df["Opec_group"].apply(_normalize_group)
        table_df = df
        return table_df
    except Exception as e:
        logger.error(f"Error loading table data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


# ---------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------
def create_layout():
    """Create the Projects by Country layout."""
    map_data = load_map_data()
    if map_data.empty:
        available_countries = []
    else:
        available_countries = sorted(map_data["Country"].unique().tolist())

    country_options = [{"label": country, "value": country} for country in available_countries]
    default_country_values = ["(All)"] + available_countries

    return html.Div(
        [
            dcc.Store(id="projects-selected-country", data=None),
            dcc.Store(id="projects-country-filter-previous", data=[]),
            dcc.Store(id="projects-likely-filter-previous", data=["Y"]),
            
            # Download components
            dcc.Download(id="download-projects-map-csv"),
            dcc.Download(id="download-projects-chart-csv"),
            dcc.Download(id="download-projects-table-csv"),
            
            # Loading states for exports
            dcc.Store(id="export-map-loading", data=False),
            dcc.Store(id="export-chart-loading", data=False),
            dcc.Store(id="export-table-loading", data=False),
            
            # Global loading state
            dcc.Store(id="global-loading-state", data=False),
            # Top row: Map + Chart on left, Filters on right
            html.Div(
                [
                    # Left column: map + chart
                    html.Div(
                        [
                            # Map
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.H3(
                                                        "Producing Countries",
                                                        style={
                                                            "marginBottom": "8px",
                                                            "color": "#fe5000",
                                                            "fontSize": "20px",
                                                            "fontWeight": "bold",
                                                        },
                                                    ),
                                                    html.Div(
                                                        id="projects-selected-country-label",
                                                        style={
                                                            "fontSize": "13px",
                                                            "color": "#4e79a7",
                                                            "fontWeight": "600",
                                                        },
                                                    ),
                                                ],
                                            ),
                                            dcc.Loading(
                                                id="loading-export-map",
                                                type="default",
                                                color="#fe5000",
                                                children=[
                                                    html.Button(
                                                        "Export to CSV",
                                                        id="export-projects-map-btn",
                                                        n_clicks=0,
                                                        style={
                                                            "backgroundColor": "white",
                                                            "color": "#2c3e50",
                                                            "border": "1px solid #dee2e6",
                                                            "padding": "6px 12px",
                                                            "borderRadius": "4px",
                                                            "cursor": "pointer",
                                                            "fontSize": "12px",
                                                            "fontWeight": "normal",
                                                        },
                                                    )
                                                ],
                                            ),
                                        ],
                                        style={
                                            "display": "flex",
                                            "justifyContent": "space-between",
                                            "alignItems": "center",
                                        },
                                    ),
                                    dcc.Loading(
                                        id="loading-projects-map",
                                        type="dot",
                                        color="#fe5000",
                                        children=[
                                            dcc.Graph(
                                                id="projects-country-map",
                                                style={"height": "520px"},
                                                config={
                                                    "displayModeBar": True,
                                                    "modeBarButtonsToAdd": [
                                                        "zoomIn2d",
                                                        "zoomOut2d",
                                                        "autoScale2d",
                                                        "resetViewMapbox",
                                                    ],
                                                    "modeBarButtonsToRemove": [
                                                        "lasso2d",
                                                        "select2d",
                                                    ],
                                                    "scrollZoom": True,
                                                    "doubleClick": "reset",
                                                    "showTips": True,
                                                },
                                            )
                                        ],
                                    ),
                                ],
                                style={
                                    "background": "white",
                                    "padding": "16px",
                                    "borderRadius": "8px",
                                    "border": "1px solid #e0e0e0",
                                    "marginBottom": "16px",
                                },
                            ),
                            # Chart
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H3(
                                                "Projected Oil Capacity Additions by Quarter ('000 b/d) - All",
                                                style={
                                                    "marginBottom": "8px",
                                                    "color": "#fe5000",
                                                    "fontSize": "20px",
                                                    "fontWeight": "bold",
                                                },
                                            ),
                                            dcc.Loading(
                                                id="loading-export-chart",
                                                type="default",
                                                color="#fe5000",
                                                children=[
                                                    html.Button(
                                                        "Export to CSV",
                                                        id="export-projects-chart-btn",
                                                        n_clicks=0,
                                                        style={
                                                            "backgroundColor": "white",
                                                            "color": "#2c3e50",
                                                            "border": "1px solid #dee2e6",
                                                            "padding": "6px 12px",
                                                            "borderRadius": "4px",
                                                            "cursor": "pointer",
                                                            "fontSize": "12px",
                                                            "fontWeight": "normal",
                                                        },
                                                    )
                                                ],
                                            ),
                                        ],
                                        style={
                                            "display": "flex",
                                            "justifyContent": "space-between",
                                            "alignItems": "center",
                                            "marginBottom": "8px",
                                        },
                                    ),
                                    dcc.Loading(
                                        id="loading-projects-chart",
                                        type="dot",
                                        color="#fe5000",
                                        children=[
                                            dcc.Graph(
                                                id="projects-country-chart",
                                                style={"height": "420px", "width": "100%"},
                                                config={"displayModeBar": False},
                                            )
                                        ],
                                    ),
                                ],
                                style={
                                    "background": "white",
                                    "padding": "16px",
                                    "borderRadius": "8px",
                                    "border": "1px solid #e0e0e0",
                                    "width": "100%",
                                },
                            ),
                        ],
                        style={
                            "width": "80%",
                            "float": "left",
                            "paddingRight": "10px",
                            "minWidth": "0",
                        },
                    ),
                    # Right column: filters
                    html.Div(
                        [
                            dcc.Loading(
                                id="loading-filters",
                                type="default",
                                color="#fe5000",
                                style={"position": "absolute", "top": "10px", "right": "10px", "zIndex": "1000"},
                                children=[html.Div(id="filter-loading-trigger", style={"display": "none"})],
                            ),
                            html.H4(
                                "Filters",
                                style={
                                    "marginBottom": "10px",
                                    "marginTop": "0px",
                                    "color": "#1b2838",
                                    "fontSize": "16px",
                                },
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Group",
                                        style={
                                            "fontWeight": "600",
                                            "marginBottom": "6px",
                                            "display": "block",
                                            "fontSize": "13px",
                                        },
                                    ),
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.Div(
                                                        style={
                                                            "width": "14px",
                                                            "height": "14px",
                                                            "backgroundColor": GROUP_COLORS[
                                                                "Non-OPEC-Plus"
                                                            ],
                                                            "borderRadius": "2px",
                                                            "marginRight": "8px",
                                                        }
                                                    ),
                                                    html.Span("Non-OPEC-Plus"),
                                                ],
                                                id="projects-group-non-opec",
                                                n_clicks=0,
                                                style={
                                                    "display": "flex",
                                                    "alignItems": "center",
                                                    "cursor": "pointer",
                                                    "padding": "4px 6px",
                                                "borderRadius": "4px",
                                                "marginBottom": "4px",
                                                "fontSize": "11px",
                                                },
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        style={
                                                            "width": "14px",
                                                            "height": "14px",
                                                            "backgroundColor": GROUP_COLORS[
                                                                "OPEC-Plus"
                                                            ],
                                                            "borderRadius": "2px",
                                                            "marginRight": "8px",
                                                        }
                                                    ),
                                                    html.Span("OPEC-Plus"),
                                                ],
                                                id="projects-group-opec",
                                                n_clicks=0,
                                                style={
                                                    "display": "flex",
                                                    "alignItems": "center",
                                                    "cursor": "pointer",
                                                    "padding": "4px 6px",
                                                "borderRadius": "4px",
                                                "marginBottom": "4px",
                                                "fontSize": "11px",
                                                },
                                            ),
                                        ],
                                    style={"display": "block"},
                                    ),
                                    dcc.Checklist(
                                        id="projects-group-filter",
                                        options=[
                                            {"label": "Non-OPEC-Plus", "value": "Non-OPEC-Plus"},
                                            {"label": "OPEC-Plus", "value": "OPEC-Plus"},
                                        ],
                                        value=DEFAULT_GROUPS,
                                        style={"display": "none"},
                                    ),
                                ],
                                style={
                                    "padding": "8px",
                                    "border": "1px solid #e0e0e0",
                                    "borderRadius": "8px",
                                    "marginBottom": "8px",
                                    "background": "#fafbfc",
                                },
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Country",
                                        style={
                                            "fontWeight": "600",
                                            "marginBottom": "6px",
                                            "display": "block",
                                            "fontSize": "13px",
                                        },
                                    ),
                                    dcc.Checklist(
                                        id="projects-country-filter",
                                        options=[{"label": "(All)", "value": "(All)"}] + country_options,
                                        value=default_country_values,
                                        inputStyle={"marginRight": "8px"},
                                        labelStyle={"display": "block", "marginBottom": "4px", "fontSize": "11px"},
                                        style={
                                            "maxHeight": "180px",
                                            "overflowY": "auto",
                                            "padding": "6px",
                                            "border": "1px solid #e0e0e0",
                                            "borderRadius": "6px",
                                            "background": "white",
                                        },
                                    ),
                                ],
                                style={
                                    "padding": "8px",
                                    "border": "1px solid #e0e0e0",
                                    "borderRadius": "8px",
                                    "marginBottom": "8px",
                                    "background": "#fafbfc",
                                },
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Country (Legend Style)",
                                        style={
                                            "fontWeight": "600",
                                            "marginBottom": "6px",
                                            "display": "block",
                                            "fontSize": "12px",
                                        },
                                    ),
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.Div(
                                                        style={
                                                            "width": "12px",
                                                            "height": "12px",
                                                            "backgroundColor": country_colors.get(
                                                                country, "#888"
                                                            ),
                                                            "borderRadius": "2px",
                                                            "marginRight": "6px",
                                                            "flexShrink": "0",
                                                        }
                                                    ),
                                                    html.Span(
                                                        country,
                                                        style={
                                                            "fontSize": "10px",
                                                            "lineHeight": "1.2",
                                                        }
                                                    ),
                                                ],
                                                id={"type": "country-legend", "value": country},
                                                n_clicks=0,
                                                style={
                                                    "display": "flex",
                                                    "alignItems": "center",
                                                    "cursor": "pointer",
                                                    "padding": "3px 4px",
                                                    "borderRadius": "3px",
                                                    "marginBottom": "2px",
                                                    "backgroundColor": "#ffffff",
                                                    "border": "1px solid #e0e0e0",
                                                    "minHeight": "20px",
                                                },
                                            )
                                            for country in available_countries
                                        ],
                                        style={
                                            "maxHeight": "200px",
                                            "overflowY": "auto",
                                            "padding": "4px",
                                            "border": "1px solid #e0e0e0",
                                            "borderRadius": "6px",
                                            "background": "white",
                                        },
                                    ),
                                ],
                                style={
                                    "padding": "8px",
                                    "border": "1px solid #e0e0e0",
                                    "borderRadius": "8px",
                                    "marginBottom": "8px",
                                    "background": "#fafbfc",
                                },
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Likely To Go Ahead",
                                        style={
                                            "fontWeight": "600",
                                            "marginBottom": "6px",
                                            "display": "block",
                                            "fontSize": "13px",
                                        },
                                    ),
                                    dcc.Checklist(
                                        id="projects-likely-filter",
                                        options=[
                                            {"label": "(All)", "value": "(All)"},
                                            {"label": "(Empty)", "value": ""},
                                            {"label": "N", "value": "N"},
                                            {"label": "Uncertain", "value": "Uncertain"},
                                            {"label": "Y", "value": "Y"},
                                        ],
                                        value=["Y"],
                                        inputStyle={"marginRight": "6px"},
                                        labelStyle={"display": "block", "marginBottom": "3px", "fontSize": "11px"},
                                    ),
                                ],
                                style={
                                    "padding": "8px",
                                    "border": "1px solid #e0e0e0",
                                    "borderRadius": "8px",
                                    "marginBottom": "8px",
                                    "background": "#fafbfc",
                                },
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Group Chart Filter",
                                        style={
                                            "fontWeight": "600",
                                            "marginBottom": "6px",
                                            "display": "block",
                                            "fontSize": "13px",
                                        },
                                    ),
                                    dcc.Checklist(
                                        id="projects-chart-group-filter",
                                        options=[
                                            {"label": "Non-OPEC-Plus", "value": "Non-OPEC-Plus"},
                                            {"label": "OPEC-Plus", "value": "OPEC-Plus"},
                                        ],
                                        value=DEFAULT_GROUPS,
                                        inputStyle={"marginRight": "6px"},
                                        labelStyle={"display": "block", "fontSize": "11px"},
                                    ),
                                ],
                                style={
                                    "padding": "8px",
                                    "border": "1px solid #e0e0e0",
                                    "borderRadius": "8px",
                                    "background": "#fafbfc",
                                },
                            ),
                        ],
                        style={
                            "width": "20%",
                            "float": "right",
                            "paddingLeft": "10px",
                            "minWidth": "200px",
                            "background": "white",
                            "padding": "12px",
                            "borderRadius": "8px",
                            "border": "1px solid #e0e0e0",
                            "height": "fit-content",
                            "maxHeight": "1000px",
                            "overflowY": "auto",
                        },
                    ),
                ],
                style={"overflow": "hidden", "marginBottom": "16px"},
            ),
            # Full width table below
            html.Div(
                [
                    html.Div(
                        [
                            html.H3(
                                "Project Details",
                                id="projects-country-table-heading",
                                style={
                                    "marginBottom": "8px",
                                    "color": "#fe5000",
                                    "fontSize": "20px",
                                    "fontWeight": "bold",
                                },
                            ),
                            dcc.Loading(
                                id="loading-export-table",
                                type="default",
                                color="#fe5000",
                                children=[
                                    html.Button(
                                        "Export to CSV",
                                        id="export-projects-table-btn",
                                        n_clicks=0,
                                        style={
                                            "backgroundColor": "white",
                                            "color": "#2c3e50",
                                            "border": "1px solid #dee2e6",
                                            "padding": "6px 12px",
                                            "borderRadius": "4px",
                                            "cursor": "pointer",
                                            "fontSize": "12px",
                                            "fontWeight": "normal",
                                        },
                                    )
                                ],
                            ),
                        ],
                        style={
                            "display": "flex",
                            "justifyContent": "space-between",
                            "alignItems": "center",
                            "marginBottom": "8px",
                        },
                    ),
                    dcc.Loading(
                        id="loading-projects-table",
                        type="dot",
                        color="#fe5000",
                        children=[
                            dash_table.DataTable(
                                id="projects-country-table",
                                columns=[],  # Columns will be dynamically generated in callback
                                data=[],
                                fixed_rows={'headers': True},
                                page_action="none",
                                sort_action="native",
                                filter_action="native",
                                tooltip_duration=None,
                                style_table={
                                    "overflowX": "auto",
                                    "maxHeight": "600px",
                                },
                                style_cell={
                                    'textAlign': 'left',
                                    'padding': '1px 4px',
                                    'fontSize': '11px',
                                    'fontFamily': 'Lato, sans-serif',
                                    'color': 'rgb(27, 54, 93)',
                                    'whiteSpace': 'nowrap',
                                    'height': '22px',
                                    'minHeight': '22px',
                                    'lineHeight': '1.1',
                                    'overflow': 'hidden',
                                    'textOverflow': 'ellipsis',
                                    'maxWidth': '180px'
                                },
                                style_cell_conditional=[
                                    {
                                        "if": {"column_id": "Comments"},
                                        "whiteSpace": "nowrap",
                                        "overflow": "hidden",
                                        "textOverflow": "ellipsis",
                                        "height": "22px",
                                        "textAlign": "left",
                                    }
                                ],
                                style_header={
                                    'backgroundColor': '#f8f9fa',
                                    'fontWeight': 'bold',
                                    'fontFamily': 'Lato, sans-serif',
                                    'color': 'rgb(27, 54, 93)',
                                    'border': '1px solid #ddd',
                                    'textAlign': 'center',
                                    'height': '25px',
                                    'minHeight': '25px',
                                    'padding': '1px 4px'
                                },
                                style_data={
                                    'border': '1px solid #ddd',
                                    'whiteSpace': 'nowrap',
                                    'fontFamily': 'Lato, sans-serif',
                                    'color': 'rgb(27, 54, 93)',
                                    'overflow': 'hidden',
                                    'textOverflow': 'ellipsis'
                                },
                                style_data_conditional=[
                                    {
                                        'if': {'row_index': 'odd'},
                                        'backgroundColor': '#f9f9f9'
                                    }
                                ],
                                css=[
                                    {
                                        "selector": ".dash-table-tooltip",
                                        "rule": "font-size: 10px !important; font-family: Lato, sans-serif !important; color: rgb(27, 54, 93) !important; max-width: 400px !important; white-space: normal !important; word-wrap: break-word !important; line-height: 1.4 !important; padding: 6px 8px !important;",
                                    },
                                    {
                                        "selector": ".dash-table-container .row:last-child",
                                        "rule": "display: none !important;",
                                    },
                                    {
                                        "selector": ".previous-page, .next-page, .first-page, .last-page, .page-number, .page-number--current",
                                        "rule": "display: none !important;",
                                    },
                                    {
                                        "selector": ".dash-spreadsheet-container .dash-spreadsheet-inner tr",
                                        "rule": "min-height: 22px !important; height: 22px !important;"
                                    },
                                    {
                                        "selector": ".dash-spreadsheet-container .dash-spreadsheet-inner td",
                                        "rule": "min-height: 22px !important; height: 22px !important; padding: 1px 4px !important; line-height: 22px !important;"
                                    },
                                    {
                                        "selector": ".dash-filter input",
                                        "rule": "height: 18px !important; padding: 0 4px !important; font-size: 10px !important;"
                                    }
                                ],
                            )
                        ],
                    ),
                ],
                style={
                    "background": "white",
                    "padding": "16px",
                    "borderRadius": "8px",
                    "border": "1px solid #e0e0e0",
                    "width": "100%",
                },
            ),
        ],
        className="tab-content",
        style={"padding": "5px", "background": "#f5f6fa", "position": "relative"},
    )


# ---------------------------------------------------------------------
# Figure builders
# ---------------------------------------------------------------------
def _create_fallback_map(df: pd.DataFrame, selected_country: str | None) -> go.Figure:
    """Create a fallback scatter plot map if Mapbox fails."""
    fig = go.Figure()
    
    # Add country markers using regular scatter plot
    for _, row in df.iterrows():
        country = row["Country"]
        group = row["Group"]
        lat = float(row["Latitude"]) if pd.notna(row["Latitude"]) else 0.0
        lon = float(row["Longitude"]) if pd.notna(row["Longitude"]) else 0.0
        
        # Skip if coordinates are invalid
        if lat == 0.0 and lon == 0.0:
            continue
            
        # Determine color based on group
        color = GROUP_COLORS.get(group, "#888")
        
        # Determine size and styling based on selection
        if selected_country and country == selected_country:
            # Selected country: larger, highlighted
            marker_size = 15
            marker_color = color
            marker_line_color = "#4A4A4A"
            marker_line_width = 2
            hover_text = f"<b>{country}</b><br>Group: {group}<br>Click to reset view"
        else:
            # Regular country
            marker_size = 12
            marker_color = color
            marker_line_color = "white"
            marker_line_width = 2
            hover_text = f"<b>{country}</b><br>Group: {group}<br>Click to select"
        
        fig.add_trace(
            go.Scatter(
                x=[lon],
                y=[lat],
                mode="markers+text",
                marker=dict(
                    size=marker_size,
                    color=marker_color,
                    line=dict(color=marker_line_color, width=marker_line_width)
                ),
                text=[country],
                textfont=dict(size=8, color="black"),
                textposition="middle center",
                hoverinfo="text",
                hovertext=hover_text,
                customdata=[country],
                showlegend=False,
                name=f"country_{country}"
            )
        )
    
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=520,
        hovermode="closest",
        plot_bgcolor="white",  # White background to match ocean
        paper_bgcolor="white",
        showlegend=False,
        xaxis=dict(
            range=[-180, 180],
            showgrid=True,
            gridcolor="lightgray",
            title="Longitude"
        ),
        yaxis=dict(
            range=[-90, 90],
            showgrid=True,
            gridcolor="lightgray",
            title="Latitude"
        )
    )
    
    return fig


def _map_figure(filtered_df: pd.DataFrame, selected_country: str | None, selected_countries: list | None = None) -> go.Figure:
    """Create a map figure using shared map utilities."""
    if filtered_df.empty:
        return create_empty_map("No countries match the selected filters.", height=520)

    df = filtered_df.copy()
    # Guard against bad coords to avoid client-side Mapbox layer errors
    df = df.dropna(subset=["Latitude", "Longitude"])
    if df.empty:
        return create_empty_map("No valid country data for mapping.", height=520)

    if "iso_alpha" not in df.columns:
        df["iso_alpha"] = df["Country"].apply(_iso_for_country)
    df = df.dropna(subset=["iso_alpha"])
    if df.empty:
        return create_empty_map("No valid country data for mapping.", height=520)

    # Prepare data for choropleth map
    locations = df["iso_alpha"].tolist()
    country_names = df["Country"].tolist()  # Collect country names for customdata
    
    # Create z-values based on group (for coloring)
    group_code = df["Group"].map({"Non-OPEC-Plus": 0, "OPEC-Plus": 1}).fillna(0)
    z_values = group_code.tolist()
    
    # Create colorscale matching the group colors
    colorscale = [
        [0, GROUP_COLORS.get("Non-OPEC-Plus", "#7194b9")],
        [1, GROUP_COLORS.get("OPEC-Plus", "#f5a555")],
    ]
    
    # Generate hover text
    def generate_hover_text(row):
        country = row['Country']
        group = row['Group']
        if selected_country and country == selected_country:
            return f"<b>{country}</b> (Focused)<br>Group: {group}<br>Click to reset focus"
        elif country in (selected_countries or []):
            return f"<b>{country}</b> (Active)<br>Group: {group}<br>Click to focus"
        else:
            return f"<b>{country}</b><br>Group: {group}<br>Click to select"
    
    hover_text = df.apply(generate_hover_text, axis=1).tolist()
    
    # Prepare selection highlighting data
    selected_isos = []
    other_isos = []
    
    # If a single country is focused, highlight only that one.
    # Otherwise, highlight all selected countries from the dropdown.
    highlight_countries = [selected_country] if selected_country else selected_countries
    
    if highlight_countries:
        selected_isos = [
            df.loc[df["Country"] == c, "iso_alpha"].iloc[0] 
            for c in highlight_countries if c in df["Country"].values
        ]
        other_isos = df[~df["Country"].isin(highlight_countries)]["iso_alpha"].tolist()
    else:
        # If nothing is selected (shouldn't happen with (All)), everything is "other" and thus dimmed
        # But usually (All) means everything is bright.
        other_isos = []
    
    # Prepare country coordinates for labels
    countries_df = df[["Country", "Latitude", "Longitude"]].copy()
    
    # Create the map using shared utilities
    fig = create_choropleth_map(
        locations=locations,
        z_values=z_values,
        colorscale=colorscale,
        hover_text=hover_text,
        selected_country=highlight_countries if len(highlight_countries) > 1 else (highlight_countries[0] if highlight_countries else None),
        selected_iso=selected_isos,
        other_isos=other_isos,
        countries_df=countries_df,
        height=520,
        zmin=0,
        zmax=1,
        country_names=country_names  # Pass country names for proper click handling
    )
    
    return fig
        

def _chart_figure(
    selected_country: str | None,
    selected_countries: list[str] | None,
    allowed_groups: set[str],
    likely_filter: list[str] | None = None,
) -> go.Figure:
    df = load_chart_data(likely_filter)
    
    # Filter by group directly since load_chart_data now joins dim_country
    if allowed_groups and not df.empty and "Opec_group" in df.columns:
        df = df[df["Opec_group"].isin(allowed_groups)]
        
    map_data = load_map_data()

    # Resolve the working country set; explicit empty list means "none selected"
    if selected_countries is None:
        base_countries = map_data["Country"].tolist()
    else:
        base_countries = selected_countries

    if selected_country:
        country_df = df[df["Country"] == selected_country].copy()
        title = f"Capacity Additions — {selected_country}"
    else:
        country_df = df[df["Country"].isin(base_countries)].copy()
        title = "Capacity Additions — Selected Countries"

    if country_df.empty:
        return create_empty_map("No chart data for the selected filters.")

    # Aggregate once per Country/Quarter to avoid duplicate bars per quarter
    country_df = (
        country_df.groupby(["Country", "Year", "QuarterNum", "Quarter"], as_index=False)[
            "ProductionAdditions"
        ]
        .sum()
        .sort_values(["Year", "QuarterNum", "Country"])
    )
    country_order = sorted(country_df["Country"].unique().tolist())

    # Build a complete ordered quarter list (even if some quarters have zero additions)
    quarter_dim = (
        country_df[["Year", "QuarterNum", "Quarter"]]
        .drop_duplicates()
        .sort_values(["Year", "QuarterNum"])
    )
    quarter_order = quarter_dim["Quarter"].tolist()

    totals_raw = (
        country_df.groupby(["Year", "QuarterNum", "Quarter"])["ProductionAdditions"]
        .sum()
        .reset_index()
    )
    # Ensure every quarter exists, even if zero, and preserve order
    totals = (
        quarter_dim.merge(
            totals_raw,
            on=["Year", "QuarterNum", "Quarter"],
            how="left",
        )
        .fillna({"ProductionAdditions": 0})
        .sort_values(["Year", "QuarterNum"])
        .reset_index(drop=True)
    )
    totals["RunningSumComputed"] = totals["ProductionAdditions"].cumsum()
    x_values = totals["Quarter"]
    line_values = totals["RunningSumComputed"]

    # Build stacked bars on primary y-axis, running sum on secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    color_map = {c: country_colors.get(c, "#4e79a7") for c in country_order}
    for country in country_order:
        sub = country_df[country_df["Country"] == country]
        if sub.empty:
            continue
        fig.add_bar(
            x=sub["Quarter"],
            y=sub["ProductionAdditions"],
            name=country,
            marker_color=color_map.get(country, "#4e79a7"),
            hovertemplate=(
                "Period: %{x}<br>"
                f"Country: {country}<br>"
                "Oil Capacity Additions: %{y:,.1f}<extra></extra>"
            ),
            secondary_y=False,
        )

    fig.add_scatter(
        x=x_values,
        y=line_values,
        name="Running sum",
        mode="lines+markers",
        marker=dict(size=6, color="#2f4b7c"),
        line=dict(color="#2f4b7c", width=2),
        hovertemplate="Period: %{x}<br>Cumulative Additions ('000 b/d): %{y:,.1f}<extra></extra>",
        secondary_y=True,
    )

    # Axis styling per requirements
    fig.update_yaxes(
        title_text="'000 b/d",
        showgrid=True,
        gridcolor="#f0f0f0",
        tickformat=',d',
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="Cumulative Additions ('000 b/d)",
        showgrid=False,
        tickformat=',.1f',
        secondary_y=True,
    )

    fig.update_layout(
        title=title,
        height=420,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis_title="",
        showlegend=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        barmode="stack",
    )
    fig.update_xaxes(showgrid=False, tickangle=-30, categoryorder="array", categoryarray=quarter_order)
    return fig


# ---------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------
def register_callbacks(dash_app, server):  # pylint: disable=unused-argument
    """Register all callbacks for Projects by Country."""

    @dash_app.callback(
        Output("projects-group-filter", "value", allow_duplicate=True),
        [
            Input("projects-group-opec", "n_clicks"),
            Input("projects-group-non-opec", "n_clicks"),
        ],
        State("projects-group-filter", "value"),
        prevent_initial_call=True,
    )
    def toggle_group_filter(opec_clicks, non_opec_clicks, current_values):
        """Toggle group selections using legend-style buttons."""
        current = current_values or DEFAULT_GROUPS
        ctx = callback_context
        if not ctx.triggered:
            return current
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]
        if trigger == "projects-group-opec":
            group_value = "OPEC-Plus"
        else:
            group_value = "Non-OPEC-Plus"

        if group_value in current and len(current) > 1:
            return [v for v in current if v != group_value]
        if group_value not in current:
            return current + [group_value]
        return current

    @dash_app.callback(
        [
            Output("projects-group-opec", "style"),
            Output("projects-group-non-opec", "style"),
        ],
        Input("projects-group-filter", "value"),
    )
    def update_group_styles(selected_groups):
        selected = set(selected_groups or DEFAULT_GROUPS)
        base_style = {
            "display": "flex",
            "alignItems": "center",
            "cursor": "pointer",
            "padding": "6px 8px",
            "borderRadius": "4px",
        }
        return (
            {
                **base_style,
                "backgroundColor": "#eef2ff" if "OPEC-Plus" in selected else "transparent",
                "opacity": 1.0 if "OPEC-Plus" in selected else 0.35,
            },
            {
                **base_style,
                "backgroundColor": "#eef2ff"
                if "Non-OPEC-Plus" in selected
                else "transparent",
                "opacity": 1.0 if "Non-OPEC-Plus" in selected else 0.35,
            },
        )

    @dash_app.callback(
        [Output("projects-likely-filter", "value", allow_duplicate=True),
         Output("projects-likely-filter-previous", "data")],
        Input("projects-likely-filter", "value"),
        [State("projects-likely-filter", "options"),
         State("projects-likely-filter-previous", "data")],
        prevent_initial_call=True,
    )
    def sync_likely_all(selected, options, previous_selected):
        """Handle (All) checkbox behavior with proper sequential logic for Likely filter."""
        if not options:
            return selected, selected
        
        # Get all individual likely options (excluding "(All)")
        all_likely = [o["value"] for o in options if o["value"] != "(All)"]
        selected = selected or []
        previous_selected = previous_selected or []
        
        # Convert to sets for easier comparison
        current_set = set(selected)
        previous_set = set(previous_selected)
        
        # Check what changed
        added = current_set - previous_set
        removed = previous_set - current_set
        
        # Priority 1: Handle explicit "(All)" checkbox clicks
        if "(All)" in removed and "(All)" in previous_set and not added:
            # User explicitly unchecked "(All)" only - clear everything
            return [], []
            
        if "(All)" in added and "(All)" not in previous_set and len(added) == 1:
            # User explicitly checked "(All)" only - select everything
            result = ["(All)"] + all_likely
            return result, result
        
        # Priority 2: Handle individual likely changes when "(All)" is currently selected
        if "(All)" in previous_selected and added and not removed:
            # User clicked an individual likely while "(All)" was selected
            # This should unselect "(All)" and select only the clicked likely
            clicked_likely = list(added)
            return clicked_likely, clicked_likely
        
        # Priority 3: Handle individual likely changes when "(All)" is not selected
        if added or removed:
            # Get current individual likely (excluding "(All)")
            individual_likely = [c for c in selected if c != "(All)"]
            individual_set = set(individual_likely)
            all_likely_set = set(all_likely)
            
            # If all individual likely are now selected, auto-add "(All)"
            if individual_set == all_likely_set and len(all_likely) > 0 and "(All)" not in selected:
                result = ["(All)"] + all_likely
                return result, result
            
            # If "(All)" is currently selected but not all likely are individually selected
            if "(All)" in selected and individual_set != all_likely_set:
                result = individual_likely
                return result, result
            
            # Otherwise keep current individual selections
            result = individual_likely
            return result, result
        
        # No changes detected - return current state
        return selected, selected

    @dash_app.callback(
        [Output("projects-country-filter", "value", allow_duplicate=True),
         Output("projects-country-filter-previous", "data")],
        Input("projects-country-filter", "value"),
        [State("projects-country-filter", "options"),
         State("projects-country-filter-previous", "data")],
        prevent_initial_call=True,
    )
    def sync_country_all(selected, options, previous_selected):
        """Handle (All) checkbox behavior with proper sequential logic."""
        if not options:
            return selected, selected
        
        # Get all individual country options (excluding "(All)")
        all_countries = [o["value"] for o in options if o["value"] != "(All)"]
        selected = selected or []
        previous_selected = previous_selected or []
        
        # Convert to sets for easier comparison
        current_set = set(selected)
        previous_set = set(previous_selected)
        
        # Check what changed
        added = current_set - previous_set
        removed = previous_set - current_set
        
        # Priority 1: Handle explicit "(All)" checkbox clicks
        if "(All)" in removed and "(All)" in previous_set and not added:
            # Check if this is a direct "(All)" uncheck vs a selection change
            # If only "(All)" was removed and nothing else changed, it's a direct uncheck
            individual_removed = removed - {"(All)"}
            if not individual_removed:
                # User explicitly unchecked "(All)" only - clear everything
                return [], []
            # Otherwise, this is a selection change (like from map click), continue processing
            
        if "(All)" in added and "(All)" not in previous_set and len(added) == 1:
            # User explicitly checked "(All)" only - select everything
            result = ["(All)"] + all_countries
            return result, result
        
        # Priority 2: Handle individual country changes when "(All)" is currently selected
        if "(All)" in previous_selected and added and not removed:
            # User clicked an individual country while "(All)" was selected
            # This should unselect "(All)" and select only the clicked country
            clicked_countries = list(added)
            return clicked_countries, clicked_countries
        
        # Priority 3: Handle individual country changes when "(All)" is not selected
        if added or removed:
            # Get current individual countries (excluding "(All)")
            individual_countries = [c for c in selected if c != "(All)"]
            individual_set = set(individual_countries)
            all_countries_set = set(all_countries)
            
            # If all individual countries are now selected, auto-add "(All)"
            if individual_set == all_countries_set and len(all_countries) > 0 and "(All)" not in selected:
                result = ["(All)"] + all_countries
                return result, result
            
            # If "(All)" is currently selected but not all countries are individually selected
            if "(All)" in selected and individual_set != all_countries_set:
                result = individual_countries
                return result, result
            
            # Otherwise keep current selections (including "(All)" if it was already there)
            result = selected
            return result, result
        
        # No changes detected - return current state
        return selected, selected



    @dash_app.callback(
        Output("projects-country-filter", "value", allow_duplicate=True),
        Input({"type": "country-legend", "value": ALL}, "n_clicks"),
        [
            State("projects-country-filter", "value"),
            State("projects-group-filter", "value"),
            State("projects-chart-group-filter", "value"),
        ],
        prevent_initial_call=True,
    )
    def toggle_country_from_legend(n_clicks_list, current_values, group_filter, chart_group_filter):
        """Toggle countries via legend blocks with group filtering."""
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update
        
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]
        try:
            trigger_id = json.loads(trigger)
        except Exception:
            return dash.no_update

        country = trigger_id.get("value")
        if not country:
            return dash.no_update

        all_countries = _ordered_countries()
        current_values = current_values or []
        
        # Apply group filtering to determine which countries are actually available
        group_set = set(group_filter or DEFAULT_GROUPS)
        chart_group_set = set(chart_group_filter or DEFAULT_GROUPS)
        allowed_groups = group_set.intersection(chart_group_set)
        
        map_data = load_map_data()
        filtered_countries_set = set(
            map_data[map_data["Group"].isin(allowed_groups)]["Country"].tolist()
        )
        
        # If clicked country is not in filtered set, do nothing
        if country not in filtered_countries_set:
            return dash.no_update
        
        # Resolve current selection (handle "(All)" case)
        resolved_countries = _resolve_countries(current_values, all_countries)
        
        # Check if only this country is currently selected
        if len(resolved_countries) == 1 and country in resolved_countries:
            # If clicking the same active country, reset to show all filtered countries
            new_values = ["(All)"] + sorted(filtered_countries_set)
        else:
            # Otherwise, select only this country
            new_values = [country]
        
        return new_values

    # In the update_country_legend_styles callback, add the group filters as inputs:
    @dash_app.callback(
        Output({"type": "country-legend", "value": ALL}, "style"),
        [
            Input("projects-country-filter", "value"),
            Input("projects-group-filter", "value"),
            Input("projects-chart-group-filter", "value"),
            Input("projects-likely-filter", "value"),
        ],
    )
    def update_country_legend_styles(selected_countries, group_filter, chart_group_filter, likely_filter):
        """Dim legend items that are not selected and hide those filtered out by group."""
        all_countries = _ordered_countries()
        selected_set = set(_resolve_countries(selected_countries, all_countries))
        
        # Apply same group filtering logic as the map
        group_set = set(group_filter or DEFAULT_GROUPS)
        chart_group_set = set(chart_group_filter or DEFAULT_GROUPS)
        allowed_groups = group_set.intersection(chart_group_set)
        
        # Get map data and filter by allowed groups and likely status
        map_data = load_map_data()
        
        # Filter map data by group
        mask = map_data["Group"].isin(allowed_groups)
        
        # Filter map data by likely status
        likely_values = likely_filter if likely_filter is not None else DEFAULT_LIKELY
        if "(All)" not in likely_values:
            mask &= map_data["likely_goahead_normalized"].isin(likely_values)
            
        filtered_countries_set = set(map_data[mask]["Country"].tolist())
        
        base_style = {
            "display": "flex",
            "alignItems": "center",
            "cursor": "pointer",
            "padding": "3px 4px",
            "borderRadius": "3px",
            "marginBottom": "2px",
            "border": "1px solid #e0e0e0",
            "transition": "background-color 0.15s ease, opacity 0.15s ease",
            "minHeight": "20px",
            "fontSize": "10px",
        }
        styles = []
        for country in all_countries:
            is_selected = country in selected_set
            is_filtered_by_group = country in filtered_countries_set
            
            if not is_filtered_by_group or not is_selected:
                # Hide countries filtered out by group selection or those not selected
                styles.append({**base_style, "display": "none"})
            else:
                styles.append(
                    {
                        **base_style,
                        "backgroundColor": "#eef2ff",
                        "borderColor": "#4e79a7",
                        "fontWeight": "600",
                        "opacity": 1.0,
                    }
                )
        return styles

    @dash_app.callback(
        Output("projects-selected-country", "data"),
        [
            Input("projects-country-map", "clickData"),
            Input("projects-country-filter", "value"),
        ],
        [
            State("projects-selected-country", "data"),
            State("current-submenu", "data"),
        ],
        prevent_initial_call=True,
    )
    def update_selected_country(click_data, country_filter, current_selected, submenu):
        if submenu != "projects-country":
            return current_selected
        ctx = callback_context
        if not ctx.triggered:
            return current_selected
        all_countries = load_map_data()["Country"].tolist()
        resolved = _resolve_countries(country_filter, all_countries)
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]
        if trigger == "projects-country-map" and click_data:
            # Use shared map click handler to detect background clicks
            point = click_data["points"][0]
            is_background_click = False
            country = None
            
            # Check for background click using shared logic pattern
            if "customdata" in point and point["customdata"]:
                if isinstance(point["customdata"], list) and len(point["customdata"]) > 0:
                    if point["customdata"][0] == "__BACKGROUND_CLICK__":
                        is_background_click = True
                    else:
                        country = point["customdata"][0]
                elif point["customdata"] == "__BACKGROUND_CLICK__":
                    is_background_click = True
                else:
                    country = point["customdata"]
            
            # Handle background clicks - reset selection
            if is_background_click:
                return None
            
            if country and country in resolved:
                # If clicking the already focused country, reset focus
                if country == current_selected:
                    return None
                return country
            return current_selected

        if trigger == "projects-country-filter":
            # Always clear manual focus when the dropdown selection changes to ensure
            # the dashboard immediately reflects the full new selection.
            return None
        return current_selected

    @dash_app.callback(
        Output("projects-country-filter", "value", allow_duplicate=True),
        Input("projects-country-map", "clickData"),
        [
            State("projects-country-filter", "value"),
            State("current-submenu", "data"),
        ],
        prevent_initial_call=True,
    )
    def update_country_filter_from_map_click(click_data, current_filter, submenu):
        """Update country filter when a country is clicked on the map using shared ocean click functionality."""
        if submenu != "projects-country":
            return no_update
        
        if not click_data:
            return no_update
        
        # Get available countries
        all_countries = load_map_data()["Country"].tolist()
        
        # Use shared map click handler for consistent ocean click behavior
        updated_filter = handle_map_click_reset(click_data, current_filter, all_countries)
        
        # Return the updated filter if it changed
        if updated_filter != current_filter:
            return updated_filter
            
        return no_update

    @dash_app.callback(
        Output("projects-selected-country-label", "children"),
        Input("projects-country-filter", "value"),
    )
    def render_selected_country_label(countries):
        return "" # Removed "X countries selected" label as requested

    @dash_app.callback(
        Output("projects-country-map", "figure"),
        [
            Input("projects-group-filter", "value"),
            Input("projects-country-filter", "value"),
            Input("projects-likely-filter", "value"),
            Input("projects-chart-group-filter", "value"),
            Input("projects-selected-country", "data"),
        ],
        prevent_initial_call=False,
    )
    def refresh_map(group_filter, country_filter, likely_filter, chart_group_filter, focus_country):
        try:
            # Check if likely filter is empty (no options selected)
            likely_values = likely_filter if likely_filter is not None else DEFAULT_LIKELY
            
            group_set = set(group_filter or DEFAULT_GROUPS)
            chart_group_set = (
                set(chart_group_filter) if chart_group_filter is not None else set(DEFAULT_GROUPS)
            )
            if not chart_group_set:
                return create_empty_map("Select at least one group to see the map.", height=520)

            allowed_groups = group_set.intersection(chart_group_set)
            if not allowed_groups:
                return create_empty_map("Selected groups are filtered out.")
            
            base_df = load_map_data()
            
            # Filter by likely status
            if "(All)" not in likely_values:
                base_df = base_df[base_df["likely_goahead_normalized"].isin(likely_values)]
            
            # Deduplicate by country AFTER likely filter to ensure we have a valid set for the map
            # but preserve countries that have at least one project matching the filter
            base_df = base_df.drop_duplicates(subset=["Country"])
            
            all_countries = base_df["Country"].tolist()
            selected_countries = _resolve_countries(country_filter, all_countries)
            
            if not selected_countries:
                return create_empty_map("No countries selected.", height=520)
            
            filtered_df = base_df[base_df["Group"].isin(allowed_groups)]
            
            return _map_figure(filtered_df, selected_country=focus_country, selected_countries=selected_countries)
        except Exception as e:
            print(f"Error updating projects-country-map: {e}")
            import traceback
            traceback.print_exc()
            return create_empty_map("Map error. Please check data sources.", height=520)

    @dash_app.callback(
        Output("projects-country-chart", "figure"),
        [
            Input("projects-country-filter", "value"),
            Input("projects-group-filter", "value"),
            Input("projects-chart-group-filter", "value"),
            Input("projects-likely-filter", "value"),
            Input("projects-selected-country", "data"),
        ],
        prevent_initial_call=False,
    )
    def refresh_chart(
        country_filter, group_filter, chart_group_filter, likely_filter, focus_country
    ):
        # Check if likely filter is empty
        likely_values = likely_filter if likely_filter is not None else DEFAULT_LIKELY
        
        group_set = set(group_filter or DEFAULT_GROUPS)
        chart_group_set = (
            set(chart_group_filter) if chart_group_filter is not None else set(DEFAULT_GROUPS)
        )
        if not chart_group_set:
            return create_empty_map("Select at least one group to see the chart.")

        allowed_groups = group_set.intersection(chart_group_set)
        if not allowed_groups:
            return create_empty_map("Selected groups are filtered out.")

        all_countries = load_map_data()["Country"].tolist()
        
        # If a single country is focused, show ONLY that country in chart/table
        if focus_country:
            selected_countries = [focus_country]
        else:
            selected_countries = _resolve_countries(country_filter, all_countries)
        
        return _chart_figure(focus_country, selected_countries, allowed_groups, likely_filter=likely_values)

    @dash_app.callback(
        [
            Output("projects-country-table", "data"),
            Output("projects-country-table", "columns"),
            Output("projects-country-table", "tooltip_data"),
            Output("projects-country-table", "style_cell_conditional"),
            Output("projects-country-table-heading", "children"),
        ],
        [
            Input("projects-country-filter", "value"),
            Input("projects-group-filter", "value"),
            Input("projects-likely-filter", "value"),
            Input("projects-chart-group-filter", "value"),
            Input("projects-selected-country", "data"),
        ],
        prevent_initial_call=False,
    )
    def refresh_table(
        country_filter, group_filter, likely_filter, chart_group_filter, focus_country
    ):
        df = load_table_data()
        
        # Default heading
        table_heading = "Project Details"
        
        if df.empty:
            logger.warning("Table data is empty after loading")
            return [], [], [], [], table_heading
        
        groups = group_filter or DEFAULT_GROUPS
        likely_values = likely_filter if likely_filter is not None else DEFAULT_LIKELY
        
        # Apply same group filtering logic as chart (intersection of both group filters)
        group_set = set(groups)
        chart_group_set = (
            set(chart_group_filter) if chart_group_filter is not None else set(DEFAULT_GROUPS)
        )
        if not chart_group_set:
            return [], [], [], [], table_heading

        allowed_groups = group_set.intersection(chart_group_set)
        if not allowed_groups:
            return [], [], [], [], table_heading
        
        # Get available countries from the dataframe
        if "Country" in df.columns:
            available_countries = df["Country"].unique().tolist()
            
            # If a single country is focused, filter table to ONLY that country
            if focus_country:
                selected_countries = [focus_country]
            else:
                selected_countries = _resolve_countries(country_filter, available_countries)
        else:
            selected_countries = []
            logger.warning("Country column not found in table data")

        # Filter by group - use Opec_group column name
        if "Opec_group" in df.columns:
            df = df[df["Opec_group"].isin(allowed_groups)]
        elif "Group" in df.columns:
            df = df[df["Group"].isin(allowed_groups)]
        else:
            logger.warning("Group column not found in table data")
        
        # Filter by likely go-ahead - use likely_goahead column name
        if "likely_goahead" in df.columns:
            df["likely_goahead_normalized"] = df["likely_goahead"].apply(_normalize_likely)
            if "(All)" not in likely_values:
                if not likely_values:  # If no options selected, return empty dataframe
                    df = df.iloc[0:0]  # Return empty dataframe with same structure
                else:
                    df = df[df["likely_goahead_normalized"].isin(likely_values)]
            df = df.drop(columns=["likely_goahead_normalized"], errors="ignore")
        
        # Filter by country - use the resolved countries from country filter
        if "Country" in df.columns:
            if not selected_countries:
                # No countries selected - return empty dataframe
                df = df.iloc[0:0]  # Return empty dataframe with same structure
            else:
                # Filter by selected countries
                df = df[df["Country"].isin(selected_countries)]
        
        if df.empty:
            logger.warning("Table data is empty after filtering")
            return [], [], [], [], table_heading

        # Create dynamic heading based on selected countries/focus
        if focus_country:
            table_heading = f"Project Details - {focus_country}"
        elif selected_countries:
            # Sort countries to maintain consistent order in heading
            sorted_selected = sorted(selected_countries)
            num_selected = len(sorted_selected)
            
            # Check if (All) is selected or inferred
            options = load_map_data()["Country"].unique().tolist()
            is_all = set(selected_countries) == set(options) or "(All)" in (country_filter or [])
            
            if is_all:
                table_heading = "Project Details - All Countries"
            elif num_selected == 1:
                table_heading = f"Project Details - {sorted_selected[0]}"
            elif num_selected == 2:
                table_heading = f"Project Details - {sorted_selected[0]} & {sorted_selected[1]}"
            elif num_selected == 3:
                table_heading = f"Project Details - {sorted_selected[0]}, {sorted_selected[1]} & {sorted_selected[2]}"
            else:
                table_heading = f"Project Details - {sorted_selected[0]}, {sorted_selected[1]}, {sorted_selected[2]} and {num_selected - 3} more"

        quarter_columns = [
            "2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4",
            "2025_Q1", "2025_Q2", "2025_Q3", "2025_Q4",
            "2026_Q1", "2026_Q2", "2026_Q3", "2026_Q4",
            "2027_Q1", "2027_Q2", "2027_Q3", "2027_Q4",
            "2028_Q1", "2028_Q2", "2028_Q3", "2028_Q4",
            "2029_Q1", "2029_Q2", "2029_Q3", "2029_Q4",
        ]

        share_columns = [
            "Operator Share %",
            "Partner1 Share %",
            "Partner2 Share %",
            "Partner3 Share %",
            "Partner4 Share %",
            "Partner5 Share %",
        ]

        # Use original column names like projects_by_time.py
        base_columns = [
            "Project Name",
            "likely_goahead",
            "Country",
            "Region",
            "Opec_group",
            "field_type",
            "field",
            "play_type",
            "Hydrocarbon",
            "Associated Crude",
            "Depth",
            "Operator",
            "Partner1",
            "Partner2",
            "Partner3",
            "Partner4",
            "Partner5",
            "First Oil Year",
            "Sanctioned",
            "Comments",
            "Project Status",
            "Gas Reserves (mmboe)",
            "Liquids Reserves (mmbbl)",
            "Total Reserves (mmboe)",
            "API",
            "Sulfur",
        ]
        
        # Data already has quarter columns from SQL query, no pivot needed
        # Ensure all required columns exist
        for qc in quarter_columns:
            if qc not in df.columns:
                df[qc] = ""
            else:
                # Convert quarter columns to numeric, then to string for display
                df[qc] = pd.to_numeric(df[qc], errors="coerce").fillna(0)
                df[qc] = df[qc].apply(lambda x: "" if x == 0 or pd.isna(x) else str(x))
        
        for sc in share_columns:
            if sc not in df.columns:
                df[sc] = ""
            else:
                # Convert share columns to numeric, then to string for display
                df[sc] = pd.to_numeric(df[sc], errors="coerce").fillna("")
                df[sc] = df[sc].apply(lambda x: "" if pd.isna(x) else str(x) if x != "" else "")
        
        # Keep only base + shares + ordered quarters
        all_columns = base_columns + share_columns + quarter_columns
        available_columns = [col for col in all_columns if col in df.columns]
        
        if not available_columns:
            logger.warning("No available columns found for table display")
            return [], [], [], [], table_heading
        
        display_df = df[available_columns].copy()
        
        # Format numeric columns like projects_by_time.py
        numeric_cols = ['Gas Reserves (mmboe)', 'Liquids Reserves (mmbbl)', 'Total Reserves (mmboe)']
        for col in numeric_cols:
            if col in display_df.columns:
                display_df[col] = pd.to_numeric(display_df[col], errors='coerce')
                display_df[col] = display_df[col].apply(lambda x: f'{x:,.3f}' if pd.notna(x) and x != 0 else '')
        
        # Format boolean columns
        bool_display_map = {
            'Y': 'Yes',
            'N': 'No',
            'true': 'Yes',
            'false': 'No',
            'True': 'Yes',
            'False': 'No'
        }
        
        if 'likely_goahead' in display_df.columns:
            display_df['likely_goahead'] = display_df['likely_goahead'].astype(str).str.strip().map(bool_display_map).fillna(display_df['likely_goahead'])
        
        if 'Sanctioned' in display_df.columns:
            display_df['Sanctioned'] = display_df['Sanctioned'].astype(str).str.strip().map(bool_display_map).fillna(display_df['Sanctioned'])
        
        # Handle Comments column - truncate for display, save original for tooltip
        if 'Comments' in display_df.columns:
            original_comments = display_df['Comments'].copy()
            display_df['Comments'] = display_df['Comments'].astype(str).apply(
                lambda x: (x[:10] + '...') if len(x) > 10 else x
            )
        else:
            original_comments = pd.Series([''] * len(display_df))
        
        # Fill any remaining NaN values
        display_df = display_df.fillna("")
        
        # Generate columns with display names like projects_by_time.py
        display_name_map = {
            'Opec_group': 'Group',
            'field_type': 'Field Type',
            'field': 'Field/Block',
            'play_type': 'Play Type',
            'likely_goahead': 'Likely To Go Ahead',
        }
        
        column_widths = {
            'Project Name': '180px',
            'likely_goahead': '100px',
            'Country': '120px',
            'Region': '120px',
            'Opec_group': '140px',
            'field_type': '100px',
            'field': '150px',
            'play_type': '120px',
            'Hydrocarbon': '120px',
            'Associated Crude': '140px',
            'Depth': '80px',
            'Operator': '120px',
            'Partner1': '100px',
            'Partner2': '100px',
            'Partner3': '100px',
            'Partner4': '100px',
            'Partner5': '100px',
            'First Oil Year': '100px',
            'Sanctioned': '80px',
            'Comments': '120px',
            'Project Status': '120px',
            'Gas Reserves (mmboe)': '140px',
            'Liquids Reserves (mmbbl)': '150px',
            'Total Reserves (mmboe)': '150px',
            'API': '80px',
            'Sulfur': '80px'
        }
        
        # Base styles for Comments column
        style_cell_conditional = [
            {
                "if": {"column_id": "Comments"},
                "whiteSpace": "nowrap",
                "overflow": "hidden",
                "textOverflow": "ellipsis",
                "height": "22px",
                "textAlign": "left",
            }
        ]

        columns = []
        for col in available_columns:
            display_name = display_name_map.get(col, col)
            col_def = {'name': display_name, 'id': col}
            
            # Move width definitions to style_cell_conditional
            if col in column_widths:
                width = column_widths[col]
                style_cell_conditional.append({
                    'if': {'column_id': col},
                    'minWidth': width,
                    'width': width,
                    'maxWidth': width,
                })
            
            # Right align numeric columns
            numeric_cols_static = [
                'Gas Reserves (mmboe)', 'Liquids Reserves (mmbbl)', 'Total Reserves (mmboe)',
                'API', 'Sulfur', 'First Oil Year',
                'Operator Share %', 'Partner1 Share %', 'Partner2 Share %', 
                'Partner3 Share %', 'Partner4 Share %', 'Partner5 Share %'
            ]
            is_quarter = len(col) == 7 and col[4] == '_' and col[:4].isdigit() and col[5:] in ['Q1', 'Q2', 'Q3', 'Q4']
            
            if col in numeric_cols_static or is_quarter:
                    style_cell_conditional.append({
                    'if': {'column_id': col},
                    'textAlign': 'right'
                })

            columns.append(col_def)
        
        # Create tooltip_data for Comments column
        data = display_df.to_dict("records")
        tooltip_data = []
        for i, row in enumerate(data):
            tooltip_row = {}
            if 'Comments' in row:
                original_comment = str(original_comments.iloc[i]) if i < len(original_comments) else ''
                if original_comment and original_comment != 'nan' and original_comment.strip():
                    tooltip_row['Comments'] = {
                        'value': original_comment,
                        'type': 'text'
                    }
            
            # Add tooltips for truncated columns (len > 14)
            for col, val in row.items():
                if col != 'Comments':
                    val_str = str(val).strip()
                    if val_str and val_str.lower() != 'nan' and len(val_str) > 14:
                        tooltip_row[col] = {'value': val_str, 'type': 'text'}
                        
            tooltip_data.append(tooltip_row)
        
        logger.info(f"Returning {len(display_df)} rows to table")
        return data, columns, tooltip_data, style_cell_conditional, table_heading

    # CSV Export Callbacks
    @dash_app.callback(
        Output("download-projects-map-csv", "data"),
        Input("export-projects-map-btn", "n_clicks"),
        [
            State("projects-country-filter", "value"),
            State("projects-group-filter", "value"),
            State("projects-chart-group-filter", "value"),
            State("projects-likely-filter", "value"),
            State("projects-selected-country", "data"),
        ],
        prevent_initial_call=True,
    )
    def export_map_data(n_clicks, country_filter, group_filter, chart_group_filter, likely_filter, focus_country):
        """Export map data to CSV."""
        if n_clicks == 0:
            return no_update
            
        try:
            likely_values = likely_filter if likely_filter is not None else DEFAULT_LIKELY
            group_set = set(group_filter or DEFAULT_GROUPS)
            chart_group_set = (
                set(chart_group_filter) if chart_group_filter is not None else set(DEFAULT_GROUPS)
            )
            allowed_groups = group_set.intersection(chart_group_set)
            
            base_df = load_map_data()
            if base_df.empty:
                return no_update

            # Filter by likely status
            if "(All)" not in likely_values:
                base_df = base_df[base_df["likely_goahead_normalized"].isin(likely_values)]
            
            # Filter by group
            base_df = base_df[base_df["Group"].isin(allowed_groups)]
            
            # Resolve countries
            if focus_country:
                selected_countries = [focus_country]
            else:
                all_countries = base_df["Country"].tolist()
                selected_countries = _resolve_countries(country_filter, all_countries)
            
            filtered_df = base_df[base_df["Country"].isin(selected_countries)]
            
            if filtered_df.empty:
                return no_update
                
            # Prepare export data (deduplicate for map view)
            export_df = filtered_df.drop_duplicates(subset=["Country"])[["Country", "Group", "Latitude", "Longitude"]].copy()
            
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"projects_producing_countries_{timestamp}.csv"
            return dcc.send_data_frame(export_df.to_csv, filename, index=False)
            
        except Exception as e:
            logger.error(f"Error exporting map data: {e}")
            return no_update

    @dash_app.callback(
        Output("download-projects-chart-csv", "data"),
        Input("export-projects-chart-btn", "n_clicks"),
        [
            State("projects-country-filter", "value"),
            State("projects-group-filter", "value"),
            State("projects-chart-group-filter", "value"),
            State("projects-likely-filter", "value"),
            State("projects-selected-country", "data"),
        ],
        prevent_initial_call=True,
    )
    def export_chart_data(n_clicks, country_filter, group_filter, chart_group_filter, likely_filter, focus_country):
        """Export chart data to CSV."""
        if n_clicks == 0:
            return no_update
            
        try:
            likely_values = likely_filter if likely_filter is not None else DEFAULT_LIKELY
            group_set = set(group_filter or DEFAULT_GROUPS)
            chart_group_set = (
                set(chart_group_filter) if chart_group_filter is not None else set(DEFAULT_GROUPS)
            )
            allowed_groups = group_set.intersection(chart_group_set)
            
            # Load optimized chart data via SQL
            df = load_chart_data(likely_values)
            if df.empty:
                return no_update
                
            # Filter by group directly
            if allowed_groups and "Opec_group" in df.columns:
                df = df[df["Opec_group"].isin(allowed_groups)]
                
            map_data = load_map_data()
            all_countries = map_data["Country"].tolist()
            
            if focus_country:
                base_countries = [focus_country]
            else:
                base_countries = _resolve_countries(country_filter, all_countries)
                
            country_df = df[df["Country"].isin(base_countries)].copy()
            
            if country_df.empty:
                return no_update
                
            export_df = (
                country_df.groupby(["Country", "Year", "QuarterNum", "Quarter"], as_index=False)[
                    "ProductionAdditions"
                ]
                .sum()
                .sort_values(["Year", "QuarterNum", "Country"])
            )
            
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"projects_capacity_additions_{timestamp}.csv"
            return dcc.send_data_frame(export_df.to_csv, filename, index=False)
            
        except Exception as e:
            logger.error(f"Error exporting chart data: {e}")
            return no_update

    @dash_app.callback(
        Output("download-projects-table-csv", "data"),
        Input("export-projects-table-btn", "n_clicks"),
        [
            State("projects-country-filter", "value"),
            State("projects-group-filter", "value"),
            State("projects-chart-group-filter", "value"),
            State("projects-likely-filter", "value"),
            State("projects-selected-country", "data"),
        ],
        prevent_initial_call=True,
    )
    def export_table_data(n_clicks, country_filter, group_filter, chart_group_filter, likely_filter, focus_country):
        """Export table data to CSV."""
        if n_clicks == 0:
            return no_update
            
        try:
            df = load_table_data()
            if df.empty:
                return no_update
                
            groups = group_filter or DEFAULT_GROUPS
            likely_values = likely_filter if likely_filter is not None else DEFAULT_LIKELY
            group_set = set(groups)
            chart_group_set = (
                set(chart_group_filter) if chart_group_filter is not None else set(DEFAULT_GROUPS)
            )
            allowed_groups = group_set.intersection(chart_group_set)
            
            # Filter by group
            group_col = "Opec_group" if "Opec_group" in df.columns else "Group"
            if group_col in df.columns:
                df = df[df[group_col].isin(allowed_groups)]
                
            # Filter by likely status
            if "likely_goahead" in df.columns and "(All)" not in likely_values:
                df["likely_goahead_normalized"] = df["likely_goahead"].apply(_normalize_likely)
                df = df[df["likely_goahead_normalized"].isin(likely_values)]
                df = df.drop(columns=["likely_goahead_normalized"], errors="ignore")
                
            # Filter by country
            if focus_country:
                df = df[df["Country"] == focus_country]
            else:
                available_countries = df["Country"].unique().tolist()
                selected_countries = _resolve_countries(country_filter, available_countries)
                if selected_countries:
                    df = df[df["Country"].isin(selected_countries)]
                    
            if df.empty:
                return no_update
                
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"projects_details_{timestamp}.csv"
            return dcc.send_data_frame(df.to_csv, filename, index=False)
            
        except Exception as e:
            logger.error(f"Error exporting table data: {e}")
            return no_update

    # Filter loading indicator callback
    @dash_app.callback(
        Output("filter-loading-trigger", "children"),
        [
            Input("projects-country-filter", "value"),
            Input("projects-group-filter", "value"),
            Input("projects-chart-group-filter", "value"),
            Input("projects-likely-filter", "value"),
        ],
        prevent_initial_call=True,
    )
    def trigger_filter_loading(country_filter, group_filter, chart_group_filter, likely_filter):
        """Trigger loading indicator when filters change."""
        return ""

    # Performance optimization: Add loading states for better UX
    @dash_app.callback(
        Output("global-loading-state", "data"),
        [
            Input("projects-country-filter", "value"),
            Input("projects-group-filter", "value"),
            Input("projects-chart-group-filter", "value"),
            Input("projects-likely-filter", "value"),
        ],
        prevent_initial_call=True,
    )
    def update_global_loading_state(country_filter, group_filter, chart_group_filter, likely_filter):
        """Update global loading state when filters change."""
        return True  # Indicates loading is in progress