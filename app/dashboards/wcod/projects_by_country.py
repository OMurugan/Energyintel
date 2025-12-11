"""
Projects by Country dashboard

Implements a Tableau-inspired view that links a Mapbox country map with
quarterly capacity additions and a project-level table. All data is
loaded from CSV files in ``app/dashboards/data/projects_by_country``.
"""

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
)
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import Config

# ---------------------------------------------------------------------
# Data locations and shared constants
# ---------------------------------------------------------------------
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "projects_by_country"
)
MAP_CSV = os.path.join(DATA_DIR, "Map_data.csv")
CHART_CSV = os.path.join(DATA_DIR, "Projects by Country_Chart_data.csv")
TABLE_CSV = os.path.join(DATA_DIR, "Projects by Country_Table_data.csv")

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
world_geojson = None

# Mapbox token (optional)
if Config.MAPBOX_ACCESS_TOKEN:
    px.set_mapbox_access_token(Config.MAPBOX_ACCESS_TOKEN)

# Common ISO mapping used to draw filled country shapes on the map
COUNTRY_TO_ISO = {
    "United States": "USA",
    "United Kingdom": "GBR",
    "Saudi Arabia": "SAU",
    "Russia": "RUS",
    "China": "CHN",
    "India": "IND",
    "Brazil": "BRA",
    "Canada": "CAN",
    "Mexico": "MEX",
    "Venezuela": "VEN",
    "Nigeria": "NGA",
    "Angola": "AGO",
    "Algeria": "DZA",
    "Libya": "LBY",
    "Iraq": "IRQ",
    "Iran": "IRN",
    "Kuwait": "KWT",
    "United Arab Emirates": "ARE",
    "Qatar": "QAT",
    "Norway": "NOR",
    "Kazakhstan": "KAZ",
    "Azerbaijan": "AZE",
    "Indonesia": "IDN",
    "Malaysia": "MYS",
    "Thailand": "THA",
    "Vietnam": "VNM",
    "Australia": "AUS",
    "Colombia": "COL",
    "Ecuador": "ECU",
    "Argentina": "ARG",
    "Chile": "CHL",
    "Peru": "PER",
    "Egypt": "EGY",
    "Sudan": "SDN",
    "South Sudan": "SSD",
    "Gabon": "GAB",
    "Congo": "COG",
    "Republic of the Congo": "COG",
    "Equatorial Guinea": "GNQ",
    "Cameroon": "CMR",
    "Ghana": "GHA",
    "Côte d'Ivoire": "CIV",
    "Cote d'Ivoire": "CIV",
    "Ivory Coast": "CIV",
    "Tunisia": "TUN",
    "Oman": "OMN",
    "Yemen": "YEM",
    "Turkmenistan": "TKM",
    "Uzbekistan": "UZB",
    "Georgia": "GEO",
    "Turkey": "TUR",
    "Greece": "GRC",
    "Italy": "ITA",
    "Spain": "ESP",
    "France": "FRA",
    "Germany": "DEU",
    "Netherlands": "NLD",
    "Belgium": "BEL",
    "Denmark": "DNK",
    "Sweden": "SWE",
    "Finland": "FIN",
    "Poland": "POL",
    "Romania": "ROU",
    "Bulgaria": "BGR",
    "Ukraine": "UKR",
    "Belarus": "BLR",
    "Lithuania": "LTU",
    "Latvia": "LVA",
    "Estonia": "EST",
    "Portugal": "PRT",
    "Ireland": "IRL",
    "Austria": "AUT",
    "Switzerland": "CHE",
    "Czech Republic": "CZE",
    "Slovakia": "SVK",
    "Hungary": "HUN",
    "Slovenia": "SVN",
    "Croatia": "HRV",
    "Serbia": "SRB",
    "Bosnia and Herzegovina": "BIH",
    "Montenegro": "MNE",
    "North Macedonia": "MKD",
    "Albania": "ALB",
    "Morocco": "MAR",
    "Kenya": "KEN",
    "Ethiopia": "ETH",
    "Tanzania": "TZA",
    "Uganda": "UGA",
    "Chad": "TCD",
    "Niger": "NER",
    "Suriname": "SUR",
    "Senegal": "SEN",
    "Trinidad and Tobago": "TTO",
    "Papua New Guinea": "PNG",
    "Guyana": "GUY",
    "Brunei": "BRN",
    "Bahrain": "BHR",
    "Japan": "JPN",
    "South Korea": "KOR",
    "Philippines": "PHL",
    "Singapore": "SGP",
    "Myanmar": "MMR",
    "Bangladesh": "BGD",
    "Pakistan": "PAK",
    "Sri Lanka": "LKA"
}

logger = logging.getLogger(__name__)

try:  # Optional fallback resolver for ISO codes
    import pycountry  # type: ignore
except Exception:  # pragma: no cover - pycountry might not be installed
    pycountry = None


# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------
def _normalize_group(raw_value: str | None) -> str | None:
    """Normalize group names to OPEC / Non-OPEC buckets."""
    if raw_value is None:
        return None
    value = str(raw_value).strip()
    if not value:
        return None
    lower = value.lower()
    if "non" in lower:
        return "Non-OPEC-Plus"
    return "OPEC-Plus"


def _iso_for_country(country: str | None) -> str | None:
    """Return ISO Alpha-3 code for a country, using custom map then pycountry."""
    if not country:
        return None
    country_clean = str(country).strip()
    if not country_clean:
        return None
    if country_clean in COUNTRY_TO_ISO:
        return COUNTRY_TO_ISO[country_clean]
    if pycountry:
        try:
            match = pycountry.countries.search_fuzzy(country_clean)
            if match:
                return match[0].alpha_3
        except Exception:
            pass
    return None


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
    return sorted(load_map_data()["Country"].tolist())


def _load_world_geojson() -> dict | None:
    """Load a lightweight world GeoJSON once, with a short timeout fallback."""
    global world_geojson
    if world_geojson is not None:
        return world_geojson
    url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
    try:
        with urlopen(url, timeout=5) as resp:
            world_geojson = json.load(resp)
    except Exception:
        world_geojson = None
    return world_geojson


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


def _empty_figure(message: str, height: int = 420) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=14, color="#444"),
    )
    fig.update_layout(
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=0, r=0, t=0, b=0),
    )
    return fig


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
    """Load and cache map data."""
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
        df = df.drop_duplicates(subset=["Country"])
        df["iso_alpha"] = df["Country"].apply(_iso_for_country)
        df = df.dropna(subset=["iso_alpha"])
        return df

    if map_df.empty:
        df = pd.read_csv(MAP_CSV)
        df = df.rename(
            columns={
                "Country": "Country",
                "Group": "Group",
                "Latitude (generated)": "Latitude",
                "Longitude (generated)": "Longitude",
            }
        )
        map_df = _normalize_map_df(df)
    else:
        map_df = _normalize_map_df(map_df)

    country_colors = _build_country_colors(map_df["Country"].unique().tolist())
    return map_df


def load_chart_data() -> pd.DataFrame:
    """Load and cache chart data."""
    global chart_df
    if not chart_df.empty:
        return chart_df

    df = pd.read_csv(CHART_CSV)
    df = df.rename(
        columns={
            "Quarter of Period": "Quarter",
            "Country": "Country",
            "Production Additions": "ProductionAdditions",
        }
    )

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
    chart_df = df
    return chart_df


def load_table_data() -> pd.DataFrame:
    """Load and cache the project detail table data."""
    global table_df
    if not table_df.empty:
        return table_df

    df = pd.read_csv(TABLE_CSV)
    df = df.rename(
        columns={
            "Project Name": "Project Name",
            "Likely Go-ahead": "Likely Go-ahead",
            "Country": "Country",
            "Region": "Region",
            "Group": "Group",
            "Field/Block": "Field/Block",
            "Field Type": "Field Type",
            "Play Type": "Play Type",
            "Hydrocarbon": "Hydrocarbon",
            "Operator": "Operator",
            "First Oil Year": "First Oil Year",
            "Project Status": "Project Status",
            "Measure Names": "Measure Names",
            "Measure Values": "Measure Values",
        }
    )
    df["Country"] = df["Country"].astype(str).str.strip().apply(_normalize_country_name)
    df["Group"] = df["Group"].apply(_normalize_group)
    def _normalize_likely(val: str) -> str:
        text = str(val or "").strip().lower()
        if not text:
            return ""
        if text.startswith("y"):
            return "Y"
        if text.startswith("n"):
            return "N"
        if "uncertain" in text:
            return "Uncertain"
        return text.capitalize()

    df["Likely Go-ahead"] = df["Likely Go-ahead"].apply(_normalize_likely)
    df["Measure Values"] = pd.to_numeric(df["Measure Values"], errors="coerce")
    table_df = df
    return table_df


# ---------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------
def create_layout():
    """Create the Projects by Country layout."""
    map_data = load_map_data()
    available_countries = sorted(map_data["Country"].unique().tolist())

    country_options = [{"label": country, "value": country} for country in available_countries]
    default_country_values = ["(All)"] + available_countries

    return html.Div(
        [
            dcc.Store(id="projects-selected-country", data=None),
            html.Div(
                [
                    # Left column: map + chart + table
                    html.Div(
                        [
                            # Map
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H3(
                                                "Producing Countries — Map View",
                                                style={
                                                    "marginBottom": "8px",
                                                    "color": "#1b2838",
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
                                        style={
                                            "display": "flex",
                                            "justifyContent": "space-between",
                                            "alignItems": "baseline",
                                        },
                                    ),
                                    dcc.Loading(
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
                                                "scrollZoom": True,
                                            },
                                        ),
                                        type="dot",
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
                            # Chart full width
                            html.Div(
                                [
                                    html.H3(
                                        "Projected Oil Capacity Additions by Quarter ('000 b/d)",
                                        style={
                                            "marginBottom": "8px",
                                            "color": "#1b2838",
                                        },
                                    ),
                                    dcc.Loading(
                                        dcc.Graph(
                                            id="projects-country-chart",
                                            style={"height": "420px", "width": "100%"},
                                            config={"displayModeBar": False},
                                        ),
                                        type="dot",
                                    ),
                                ],
                                style={
                                    "background": "white",
                                    "padding": "16px",
                                    "borderRadius": "8px",
                                    "border": "1px solid #e0e0e0",
                                    "marginBottom": "16px",
                                    "width": "100%",
                                },
                            ),
                            # Table full width
                            html.Div(
                                [
                                    html.H3(
                                        "Project Details",
                                        style={
                                            "marginBottom": "8px",
                                            "color": "#1b2838",
                                        },
                                    ),
                                    dcc.Loading(
                                        dash_table.DataTable(
                                            id="projects-country-table",
                                            columns=[
                                                {"name": "Project", "id": "Project Name"},
                                                {"name": "Likely Go-ahead", "id": "Likely Go-ahead"},
                                                {"name": "Country", "id": "Country"},
                                                {"name": "Region", "id": "Region"},
                                                {"name": "Group", "id": "Group"},
                                                {"name": "Field/Block", "id": "Field/Block"},
                                                {"name": "Field Type", "id": "Field Type"},
                                                {"name": "Play Type", "id": "Play Type"},
                                                {"name": "Hydrocarbon", "id": "Hydrocarbon"},
                                                {"name": "Associated Crude", "id": "Associated Crude"},
                                                {"name": "Depth", "id": "Depth"},
                                                {"name": "Operator", "id": "Operator"},
                                                {"name": "Partner1", "id": "Partner1"},
                                                {"name": "Partner2", "id": "Partner2"},
                                                {"name": "Partner3", "id": "Partner3"},
                                                {"name": "Partner4", "id": "Partner4"},
                                                {"name": "Partner5", "id": "Partner5"},
                                                {"name": "First Oil Year", "id": "First Oil Year"},
                                                {"name": "Sanctioned", "id": "Sanctioned"},
                                                {"name": "Comments", "id": "Comments"},
                                                {"name": "Comments Link", "id": "Comments_link"},
                                                {"name": "Project Status", "id": "Project Status"},
                                                {"name": "Gas Reserves (mmboe)", "id": "Gas Reserves (mmboe)"},
                                                {"name": "Liquids Reserves (mmbbl)", "id": "Liquids Reserves (mmbbl)"},
                                                {"name": "Total Reserves (mmboe)", "id": "Total Reserves (mmboe)"},
                                                {"name": "API", "id": "API"},
                                                {"name": "Sulfur", "id": "Sulfur"},
                                                {"name": "Operator Share %", "id": "Operator Share %"},
                                                {"name": "Partner1 Share %", "id": "Partner1 Share %"},
                                                {"name": "Partner2 Share %", "id": "Partner2 Share %"},
                                                {"name": "Partner3 Share %", "id": "Partner3 Share %"},
                                                {"name": "Partner4 Share %", "id": "Partner4 Share %"},
                                                {"name": "Partner5 Share %", "id": "Partner5 Share %"},
                                                {"name": "2024 Q1", "id": "2024_Q1"},
                                                {"name": "2024 Q2", "id": "2024_Q2"},
                                                {"name": "2024 Q3", "id": "2024_Q3"},
                                                {"name": "2024 Q4", "id": "2024_Q4"},
                                                {"name": "2025 Q1", "id": "2025_Q1"},
                                                {"name": "2025 Q2", "id": "2025_Q2"},
                                                {"name": "2025 Q3", "id": "2025_Q3"},
                                                {"name": "2025 Q4", "id": "2025_Q4"},
                                                {"name": "2026 Q1", "id": "2026_Q1"},
                                                {"name": "2026 Q2", "id": "2026_Q2"},
                                                {"name": "2026 Q3", "id": "2026_Q3"},
                                                {"name": "2026 Q4", "id": "2026_Q4"},
                                                {"name": "2027 Q1", "id": "2027_Q1"},
                                                {"name": "2027 Q2", "id": "2027_Q2"},
                                                {"name": "2027 Q3", "id": "2027_Q3"},
                                                {"name": "2027 Q4", "id": "2027_Q4"},
                                                {"name": "2028 Q1", "id": "2028_Q1"},
                                                {"name": "2028 Q2", "id": "2028_Q2"},
                                                {"name": "2028 Q3", "id": "2028_Q3"},
                                                {"name": "2028 Q4", "id": "2028_Q4"},
                                                {"name": "2029 Q1", "id": "2029_Q1"},
                                                {"name": "2029 Q2", "id": "2029_Q2"},
                                                {"name": "2029 Q3", "id": "2029_Q3"},
                                                {"name": "2029 Q4", "id": "2029_Q4"},
                                            ],
                                            data=[],
                                            page_action="none",
                                            sort_action="native",
                                            filter_action="native",
                                            style_table={
                                                "overflowX": "auto",
                                                "maxHeight": "500px",
                                            },
                                            style_cell={
                                                "fontFamily": "Arial, sans-serif",
                                                "fontSize": "12px",
                                                "padding": "6px",
                                                "whiteSpace": "normal",
                                                "height": "auto",
                                            },
                                            style_header={
                                                "backgroundColor": "#f5f6fa",
                                                "fontWeight": "600",
                                            },
                                        ),
                                        type="dot",
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
                            "width": "75%",
                            "float": "left",
                            "paddingRight": "20px",
                            "minWidth": "0",
                        },
                    ),
                    # Right column: filters
                    html.Div(
                        [
                            html.H4(
                                "Filters",
                                style={
                                    "marginBottom": "12px",
                                    "color": "#1b2838",
                                },
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Group",
                                        style={
                                            "fontWeight": "600",
                                            "marginBottom": "8px",
                                            "display": "block",
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
                                                    "padding": "6px 8px",
                                                "borderRadius": "4px",
                                                "marginBottom": "6px",
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
                                                    "padding": "6px 8px",
                                                "borderRadius": "4px",
                                                "marginBottom": "6px",
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
                                    "padding": "12px",
                                    "border": "1px solid #e0e0e0",
                                    "borderRadius": "8px",
                                    "marginBottom": "12px",
                                    "background": "#fafbfc",
                                },
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Country",
                                        style={
                                            "fontWeight": "600",
                                            "marginBottom": "8px",
                                            "display": "block",
                                        },
                                    ),
                                    dcc.Checklist(
                                        id="projects-country-filter",
                                        options=[{"label": "(All)", "value": "(All)"}] + country_options,
                                        value=default_country_values,
                                        inputStyle={"marginRight": "8px"},
                                        labelStyle={"display": "block", "marginBottom": "6px"},
                                        style={
                                            "maxHeight": "260px",
                                            "overflowY": "auto",
                                            "padding": "8px",
                                            "border": "1px solid #e0e0e0",
                                            "borderRadius": "6px",
                                            "background": "white",
                                        },
                                    ),
                                ],
                                style={
                                    "padding": "12px",
                                    "border": "1px solid #e0e0e0",
                                    "borderRadius": "8px",
                                    "marginBottom": "12px",
                                    "background": "#fafbfc",
                                },
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Country (Legend Style)",
                                        style={
                                            "fontWeight": "600",
                                            "marginBottom": "8px",
                                            "display": "block",
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
                                                            "backgroundColor": country_colors.get(
                                                                country, "#888"
                                                            ),
                                                            "borderRadius": "2px",
                                                            "marginRight": "8px",
                                                        }
                                                    ),
                                                    html.Span(country),
                                                ],
                                                id={"type": "country-legend", "value": country},
                                                n_clicks=0,
                                                style={
                                                    "display": "flex",
                                                    "alignItems": "center",
                                                    "cursor": "pointer",
                                                    "padding": "6px 8px",
                                                    "borderRadius": "4px",
                                                    "marginBottom": "6px",
                                                    "backgroundColor": "#ffffff",
                                                    "border": "1px solid #e0e0e0",
                                                },
                                            )
                                            for country in available_countries
                                        ],
                                        style={
                                            "maxHeight": "260px",
                                            "overflowY": "auto",
                                            "padding": "8px",
                                            "border": "1px solid #e0e0e0",
                                            "borderRadius": "6px",
                                            "background": "white",
                                        },
                                    ),
                                ],
                                style={
                                    "padding": "12px",
                                    "border": "1px solid #e0e0e0",
                                    "borderRadius": "8px",
                                    "marginBottom": "12px",
                                    "background": "#fafbfc",
                                },
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Likely To Go Ahead",
                                        style={
                                            "fontWeight": "600",
                                            "marginBottom": "8px",
                                            "display": "block",
                                        },
                                    ),
                                    dcc.Checklist(
                                        id="projects-likely-filter",
                                        options=[
                                            {"label": "(All)", "value": "(All)"},
                                            {"label": "", "value": ""},
                                            {"label": "N", "value": "N"},
                                            {"label": "Uncertain", "value": "Uncertain"},
                                            {"label": "Y", "value": "Y"},
                                        ],
                                        value=["Y"],
                                        inputStyle={"marginRight": "8px"},
                                        labelStyle={"display": "block", "marginBottom": "4px"},
                                    ),
                                ],
                                style={
                                    "padding": "12px",
                                    "border": "1px solid #e0e0e0",
                                    "borderRadius": "8px",
                                    "marginBottom": "12px",
                                    "background": "#fafbfc",
                                },
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Group Chart Filter",
                                        style={
                                            "fontWeight": "600",
                                            "marginBottom": "8px",
                                            "display": "block",
                                        },
                                    ),
                                    dcc.Checklist(
                                        id="projects-chart-group-filter",
                                        options=[
                                            {"label": "Non-OPEC-Plus", "value": "Non-OPEC-Plus"},
                                            {"label": "OPEC-Plus", "value": "OPEC-Plus"},
                                        ],
                                        value=DEFAULT_GROUPS,
                                        inputStyle={"marginRight": "8px"},
                                        labelStyle={"display": "block"},
                                    ),
                                ],
                                style={
                                    "padding": "12px",
                                    "border": "1px solid #e0e0e0",
                                    "borderRadius": "8px",
                                    "background": "#fafbfc",
                                },
                            ),
                        ],
                        style={
                            "width": "25%",
                            "float": "right",
                            "paddingLeft": "20px",
                            "minWidth": "280px",
                            "background": "white",
                            "padding": "16px",
                            "borderRadius": "8px",
                            "border": "1px solid #e0e0e0",
                            "height": "fit-content",
                        },
                    ),
                ],
                style={"overflow": "hidden"},
            ),
        ],
        className="tab-content",
        style={"padding": "16px", "background": "#f5f6fa"},
    )


# ---------------------------------------------------------------------
# Figure builders
# ---------------------------------------------------------------------
def _map_figure(filtered_df: pd.DataFrame, selected_country: str | None) -> go.Figure:
    """Create a map figure with choropleth fills; no point symbols."""
    if filtered_df.empty:
        return _empty_figure("No countries match the selected filters.", height=520)

    df = filtered_df.copy()
    # Guard against bad coords to avoid client-side Mapbox layer errors
    df = df.dropna(subset=["Latitude", "Longitude"])
    if df.empty:
        return _empty_figure("No valid country data for mapping.", height=520)

    if "iso_alpha" not in df.columns:
        df["iso_alpha"] = df["Country"].apply(_iso_for_country)
    df = df.dropna(subset=["iso_alpha"])
    if df.empty:
        return _empty_figure("No valid country data for mapping.", height=520)

    # Only attempt Mapbox rendering when a token looks valid; otherwise fall back
    # to the non-Mapbox choropleth to avoid client-side "Mapbox error".
    _mapbox_token = (getattr(Config, "MAPBOX_ACCESS_TOKEN", None) or "").strip()
    has_mapbox_token = _mapbox_token.startswith("pk.")
    use_mapbox = (
        has_mapbox_token
        and (_load_world_geojson() is not None)
        and os.getenv("USE_MAPBOX_WCOD", "false").lower() in ("1", "true", "yes")
    )

    # Color per group; selection outlined separately
    color_map = {}
    for _, row in df.iterrows():
        country = row["Country"]
        group = row["Group"]
        color_map[country] = GROUP_COLORS.get(group, "#888")

    # Preferred Mapbox path (with world geojson) for OSM base map + controls
    geojson = _load_world_geojson()
    world_center = {"lat": 24.0, "lon": 45.0}
    avg_lat = df["Latitude"].mean()
    avg_lon = df["Longitude"].mean()
    map_center = (
        dict(lat=avg_lat, lon=avg_lon)
        if selected_country and not (pd.isna(avg_lat) or pd.isna(avg_lon))
        else world_center
    )
    map_zoom = 2.8 if not selected_country else 2

    if geojson and use_mapbox:
        try:
            group_code = df["Group"].map({"Non-OPEC-Plus": 0, "OPEC-Plus": 1}).fillna(0)
            fig = go.Figure(
                go.Choroplethmapbox(
                    geojson=geojson,
                    locations=df["iso_alpha"],
                    z=group_code,
                    featureidkey="id",  # world.geo.json uses ISO-3 in `id`
                    colorscale=[
                        [0, GROUP_COLORS.get("Non-OPEC-Plus", "#7194b9")],
                        [1, GROUP_COLORS.get("OPEC-Plus", "#f5a555")],
                    ],
                    showscale=False,
                    hoverinfo="text",
                    hovertext=df.apply(
                        lambda row: f"<b>{row['Country']}</b><br>Group: {row['Group']}<br>Click to select",
                        axis=1,
                    ),
                    marker_line_color="white",
                    marker_line_width=0.6,
                )
            )
            centroids = (
                df.groupby("Country")[["Latitude", "Longitude"]]
                .mean()
                .reset_index()
                .dropna(subset=["Latitude", "Longitude"])
            )
            if centroids.empty:
                raise ValueError("No centroid coordinates for Mapbox text labels.")
            # Limit label density at low zoom so names stay readable
            max_labels = len(centroids)
            if map_zoom <= 2.8:
                max_labels = 40
            elif map_zoom <= 3.4:
                max_labels = 80
            centroids_display = (
                centroids.sort_values("Country").head(max_labels)
                if max_labels < len(centroids)
                else centroids
            )
            fig.add_trace(
                go.Scattermapbox(
                    lon=centroids_display["Longitude"],
                    lat=centroids_display["Latitude"],
                    mode="text",
                    text=centroids_display["Country"],
                    textfont=dict(size=10, color="#2c3e50"),
                    textposition="top center",
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

            if selected_country and selected_country in df["Country"].values:
                sel_iso = df.loc[df["Country"] == selected_country, "iso_alpha"].iloc[0]
                fig.add_trace(
                    go.Choroplethmapbox(
                        geojson=geojson,
                        locations=[sel_iso],
                        z=[0],
                        featureidkey="id",
                        colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                        showscale=False,
                        marker_line_color="#FF6B35",
                        marker_line_width=2.5,
                        hoverinfo="skip",
                    )
                )
                if len(fig.data) > 1:
                    fig.data = tuple(list(fig.data)[1:] + [fig.data[0]])

            mapbox_layout = dict(
                style="carto-positron",
                center=map_center,
                zoom=map_zoom,
                bearing=0,
                pitch=0,
            )
            if has_mapbox_token:
                mapbox_layout["accesstoken"] = _mapbox_token

            fig.update_layout(
                margin=dict(l=0, r=0, t=0, b=0),
                height=520,
                mapbox=mapbox_layout,
                hovermode="closest",
                plot_bgcolor="white",
                paper_bgcolor="white",
                showlegend=False,
            )
            return fig
        except Exception as exc:
            logger.warning("Mapbox rendering failed; falling back to geo map. Error: %s", exc)

    # Fallback: geo-based choropleth (no Mapbox) if GeoJSON unavailable
    group_code = df["Group"].map({"Non-OPEC-Plus": 0, "OPEC-Plus": 1}).fillna(0)
    fig = go.Figure(
        go.Choropleth(
            locations=df["iso_alpha"],
            z=group_code,
            locationmode="ISO-3",
            colorscale=[
                [0, GROUP_COLORS.get("Non-OPEC-Plus", "#7194b9")],
                [1, GROUP_COLORS.get("OPEC-Plus", "#f5a555")],
            ],
            showscale=False,
            hoverinfo="text",
            hovertext=df.apply(
                lambda row: f"<b>{row['Country']}</b><br>Group: {row['Group']}<br>Click to select",
                axis=1,
            ),
            marker_line_color="white",
            marker_line_width=0.7,
        )
    )
    centroids = (
        df.groupby("Country")[["Latitude", "Longitude"]]
        .mean()
        .reset_index()
    )
    # Limit label density at low zoom so names stay readable
    fallback_labels = centroids
    if len(centroids) > 60:
        fallback_labels = centroids.sort_values("Country").head(60)
    fig.add_trace(
        go.Scattergeo(
            lon=fallback_labels["Longitude"],
            lat=fallback_labels["Latitude"],
            mode="text",
            text=fallback_labels["Country"],
            textfont=dict(size=10, color="#2c3e50"),
            textposition="top center",
            hoverinfo="skip",
            showlegend=False,
        )
    )
    center_lat = df["Latitude"].mean()
    center_lon = df["Longitude"].mean()

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=520,
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection=dict(type="natural earth"),
            center=dict(lat=center_lat, lon=center_lon),
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    if selected_country and selected_country in df["Country"].values:
        sel_iso = df.loc[df["Country"] == selected_country, "iso_alpha"].iloc[0]
        fig.add_trace(
            go.Choropleth(
                locations=[sel_iso],
                z=[0],
                locationmode="ISO-3",
                colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                showscale=False,
                marker_line_color="#FF6B35",
                marker_line_width=2.5,
                hoverinfo="skip",
            )
        )
        if len(fig.data) > 1:
            fig.data = tuple(list(fig.data)[1:] + [fig.data[0]])

    return fig
        

def _chart_figure(
    selected_country: str | None,
    selected_countries: list[str] | None,
    allowed_groups: set[str],
) -> go.Figure:
    df = load_chart_data()
    map_data = load_map_data()
    country_to_group = map_data.set_index("Country")["Group"].to_dict()

    def _allowed(country: str) -> bool:
        if not allowed_groups:
            return True
        return country_to_group.get(country) in allowed_groups

    # Resolve the working country set; explicit empty list means "none selected"
    if selected_countries is None:
        base_countries = [c for c in map_data["Country"].tolist() if _allowed(c)]
    else:
        base_countries = [c for c in selected_countries if _allowed(c)]

    if selected_country:
        if not _allowed(selected_country):
            return _empty_figure("Selected country is filtered out by group selection.")
        country_df = df[df["Country"] == selected_country].copy()
        title = f"Capacity Additions — {selected_country}"
    else:
        country_df = df[df["Country"].isin(base_countries)].copy()
        title = "Capacity Additions — Selected Countries"

    if country_df.empty:
        return _empty_figure("No chart data for the selected filters.")

    # Aggregate once per Country/Quarter to avoid duplicate bars per quarter
    country_df = (
        country_df.groupby(["Country", "Year", "QuarterNum", "Quarter"], as_index=False)[
            "ProductionAdditions"
        ]
        .sum()
        .sort_values(["Year", "QuarterNum", "Country"])
    )
    country_order = sorted(country_df["Country"].unique().tolist())

    totals = (
        country_df.groupby(["Year", "QuarterNum", "Quarter"], as_index=False)["ProductionAdditions"]
        .sum()
        .sort_values(["Year", "QuarterNum"])
    )
    totals["RunningSumComputed"] = totals["ProductionAdditions"].cumsum()
    x_values = totals["Quarter"]
    line_values = totals["RunningSumComputed"]
    quarter_order = totals["Quarter"].tolist()

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
        range=[0, 1000],
        tick0=0,
        dtick=200,
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="'000 b/d",
        showgrid=False,
        range=[0, 12000],
        tick0=0,
        dtick=2000,
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
        Output("projects-likely-filter", "value", allow_duplicate=True),
        Input("projects-likely-filter", "value"),
        State("projects-likely-filter", "options"),
        prevent_initial_call=True,
    )
    def sync_likely_all(selected, options):
        """Ensure '(All)' behaves as select-all for Likely filter."""
        if not options:
            return selected
        all_values = [o["value"] for o in options if o["value"] != "(All)"]
        selected = selected or []
        selected_set = set(selected)
        has_all = "(All)" in selected_set

        normalized = selected
        if has_all and len(selected_set) == 1:
            normalized = ["(All)"] + all_values
        elif not has_all and set(all_values).issubset(selected_set):
            normalized = ["(All)"] + all_values
        elif has_all and not set(all_values).issubset(selected_set):
            normalized = [v for v in selected if v != "(All)"]

        new_sorted = sorted(normalized)
        old_sorted = sorted(selected)
        return new_sorted if new_sorted != old_sorted else dash.no_update

    @dash_app.callback(
        Output("projects-country-filter", "value", allow_duplicate=True),
        Input("projects-country-filter", "value"),
        State("projects-country-filter", "options"),
        prevent_initial_call=True,
    )
    def sync_country_all(selected, options):
        """Ensure '(All)' behaves as a real select-all for dropdown."""
        if not options:
            return selected
        all_countries = [o["value"] for o in options if o["value"] != "(All)"]
        selected = selected or []
        selected_set = set(selected)
        has_all = "(All)" in selected_set
        all_set = set(all_countries)
        subset_set = selected_set - {"(All)"}

        # Rules:
        # 1) "(All)" clicked alone => select all countries.
        # 2) "(All)" + subset:
        #    - If subset is nearly/all countries (user deselected while All was on), drop "(All)" and honor subset.
        #    - Otherwise (user added All while a partial subset was selected), snap to full select-all.
        # 3) If everything is selected but "(All)" is not present, treat as user unchecked All -> clear all.
        # 4) If nothing selected, keep empty.
        # 5) Otherwise, keep the chosen subset.
        if has_all and not subset_set:
            normalized = ["(All)"] + all_countries
        elif has_all and subset_set:
            if len(all_set) > 0 and len(subset_set) >= len(all_set) - 1:
                normalized = sorted(subset_set)  # user is deselecting while All was active
            else:
                normalized = ["(All)"] + all_countries  # user added All from a partial subset
        elif not has_all and subset_set == all_set and all_countries:
            normalized = []  # allow explicit unselect-all after All was selected
        elif not subset_set:
            normalized = []
        else:
            normalized = sorted(subset_set)

        # Avoid loops
        new_sorted = normalized
        old_sorted = sorted(selected)
        return new_sorted if new_sorted != old_sorted else dash.no_update

    @dash_app.callback(
        Output("projects-country-filter", "value", allow_duplicate=True),
        Input({"type": "country-legend", "value": ALL}, "n_clicks"),
        State("projects-country-filter", "value"),
        prevent_initial_call=True,
    )
    def toggle_country_from_legend(n_clicks_list, current_values):
        """Toggle countries via legend blocks."""
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
        selected_set = set(_resolve_countries(current_values or [], all_countries))

        if country in selected_set:
            selected_set.remove(country)
        else:
            selected_set.add(country)

        if not selected_set:
            new_values = []
        elif selected_set == set(all_countries):
            new_values = ["(All)"] + all_countries
        else:
            new_values = sorted(selected_set)
        return new_values

    @dash_app.callback(
        Output({"type": "country-legend", "value": ALL}, "style"),
        Input("projects-country-filter", "value"),
    )
    def update_country_legend_styles(selected_countries):
        """Dim legend items that are not selected."""
        all_countries = _ordered_countries()
        selected_set = set(_resolve_countries(selected_countries, all_countries))
        base_style = {
            "display": "flex",
            "alignItems": "center",
            "cursor": "pointer",
            "padding": "6px 8px",
            "borderRadius": "4px",
            "marginBottom": "6px",
            "border": "1px solid #e0e0e0",
            "transition": "background-color 0.15s ease, opacity 0.15s ease",
        }
        styles = []
        for country in all_countries:
            is_selected = country in selected_set
            styles.append(
                {
                    **base_style,
                    "backgroundColor": "#eef2ff" if is_selected else "#ffffff",
                    "borderColor": "#4e79a7" if is_selected else "#e0e0e0",
                    "fontWeight": "600" if is_selected else "400",
                    "opacity": 1.0 if is_selected else 0.35,
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
            point = click_data["points"][0]
            country = None
            if "text" in point and point["text"]:
                country = point["text"]
            elif "hovertext" in point and point["hovertext"]:
                hovertext = point["hovertext"]
                if "<b>" in hovertext and "</b>" in hovertext:
                    country = hovertext.split("<b>")[1].split("</b>")[0]
            elif "customdata" in point and point["customdata"]:
                if isinstance(point["customdata"], list):
                    country = point["customdata"][0]
                else:
                    country = point["customdata"]
            elif "location" in point:
                iso_value = point["location"]
                reverse_map = {v: k for k, v in COUNTRY_TO_ISO.items()}
                country = reverse_map.get(iso_value, None)
            if country and country in resolved:
                return country
            return current_selected

        if trigger == "projects-country-filter":
            if current_selected and current_selected not in resolved:
                return None
        return current_selected

    @dash_app.callback(
        Output("projects-selected-country-label", "children"),
        [
            Input("projects-selected-country", "data"),
            Input("projects-country-filter", "value"),
        ],
    )
    def render_selected_country_label(selected_country, countries):
        all_countries = load_map_data()["Country"].tolist()
        resolved = _resolve_countries(countries, all_countries)
        if selected_country:
            return f"Selected country: {selected_country}"
        return f"{len(resolved)} countries selected"

    @dash_app.callback(
        Output("projects-country-map", "figure"),
        [
            Input("projects-group-filter", "value"),
            Input("projects-country-filter", "value"),
            Input("projects-selected-country", "data"),
        ],
        prevent_initial_call=False,
    )
    def refresh_map(group_filter, country_filter, selected_country):
        try:
            base_df = load_map_data()
            all_countries = base_df["Country"].tolist()
            groups = group_filter or DEFAULT_GROUPS
            selected_countries = _resolve_countries(country_filter, all_countries)
            filtered_df = base_df[
                base_df["Group"].isin(groups) & base_df["Country"].isin(selected_countries)
            ]
            return _map_figure(filtered_df, selected_country)
        except Exception as e:
            print(f"Error updating projects-country-map: {e}")
            import traceback
            traceback.print_exc()
            return _empty_figure("Map error. Please check data sources.", height=520)

    @dash_app.callback(
        Output("projects-country-chart", "figure"),
        [
            Input("projects-selected-country", "data"),
            Input("projects-country-filter", "value"),
            Input("projects-group-filter", "value"),
            Input("projects-chart-group-filter", "value"),
        ],
        prevent_initial_call=False,
    )
    def refresh_chart(
        selected_country, country_filter, group_filter, chart_group_filter
    ):
        group_set = set(group_filter or DEFAULT_GROUPS)
        chart_group_set = (
            set(chart_group_filter) if chart_group_filter is not None else set(DEFAULT_GROUPS)
        )
        if not chart_group_set:
            return _empty_figure("Select at least one group to see the chart.")

        allowed_groups = group_set.intersection(chart_group_set)
        if not allowed_groups:
            return _empty_figure("Selected groups are filtered out.")

        all_countries = load_map_data()["Country"].tolist()
        selected_countries = _resolve_countries(country_filter, all_countries)
        return _chart_figure(selected_country, selected_countries, allowed_groups)

    @dash_app.callback(
        Output("projects-country-table", "data"),
        [
            Input("projects-selected-country", "data"),
            Input("projects-country-filter", "value"),
            Input("projects-group-filter", "value"),
            Input("projects-likely-filter", "value"),
        ],
        prevent_initial_call=False,
    )
    def refresh_table(
        selected_country, country_filter, group_filter, likely_filter
    ):
        df = load_table_data()
        groups = group_filter or DEFAULT_GROUPS
        likely_values = likely_filter or DEFAULT_LIKELY
        countries = _resolve_countries(country_filter, df["Country"].unique().tolist())

        df = df[df["Group"].isin(groups)]
        if "(All)" not in likely_values:
            df = df[df["Likely Go-ahead"].isin(likely_values)]
        if selected_country:
            df = df[df["Country"] == selected_country]
        else:
            df = df[df["Country"].isin(countries)]

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

        base_columns = [
            "Project Name",
            "Likely Go-ahead",
            "Country",
            "Region",
            "Group",
            "Field/Block",
            "Field Type",
            "Play Type",
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
            "Comments_link",
            "Project Status",
            "Gas Reserves (mmboe)",
            "Liquids Reserves (mmbbl)",
            "Total Reserves (mmboe)",
            "API",
            "Sulfur",
        ]
        # Pivot Measure Names/Values into quarter columns
        pivot_source = df[base_columns + ["Measure Names", "Measure Values"]].copy()
        pivot = (
            pivot_source.groupby(base_columns + ["Measure Names"])["Measure Values"]
            .sum()
            .reset_index()
            .pivot(index=base_columns, columns="Measure Names", values="Measure Values")
            .reset_index()
        )
        # Ensure all quarter columns exist
        for qc in quarter_columns:
            if qc not in pivot.columns:
                pivot[qc] = ""
        # Ensure share columns exist and order after Sulfur
        for sc in share_columns:
            if sc not in pivot.columns:
                pivot[sc] = ""
        # Keep only base + shares + ordered quarters
        display_df = pivot[base_columns + share_columns + quarter_columns].fillna("")
        return display_df.to_dict("records")
