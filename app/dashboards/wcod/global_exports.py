"""
Global Exports View
Replicates Tableau Global Crude Exports dashboard with local CSV data
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Sequence, Tuple

import dash
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import (
    Input,
    Output,
    State,
    callback,
    dash_table,
    dcc,
    html,
    no_update,
)

# Data locations
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "global-exports",
)
MAP_CSV = os.path.join(DATA_DIR, "Map_data.csv")
CHART_CSV = os.path.join(DATA_DIR, "Chart_Crude_data.csv")
TABLE_CSV = os.path.join(DATA_DIR, "Exports Table_data.csv")


def _read_csv(path: str) -> pd.DataFrame:
    """Read a CSV file and trim column names."""
    try:
        df = pd.read_csv(path)
        df.columns = df.columns.str.strip()
        return df
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"[global_exports] Failed to read {path}: {exc}")
        return pd.DataFrame()


def _to_numeric(series: pd.Series) -> pd.Series:
    """Convert a series to numeric, stripping commas."""
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.strip(),
        errors="coerce",
    )


def _prepare_map_df() -> pd.DataFrame:
    """Normalize map CSV."""
    df = _read_csv(MAP_CSV)
    if df.empty:
        return df
    df = df.rename(
        columns={
            "Country": "country",
            "Year of Year": "year",
            "Latitude (generated)": "lat",
            "Longitude (generated)": "lon",
            "Value": "value",
        }
    )
    keep_cols = ["country", "year", "lat", "lon", "value"]
    df = df[keep_cols].copy()
    df["country"] = df["country"].astype(str).str.strip()
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["lat"] = _to_numeric(df["lat"])
    df["lon"] = _to_numeric(df["lon"])
    df["value"] = _to_numeric(df["value"])
    df = df.dropna(subset=["country", "year", "lat", "lon", "value"])
    df["year"] = df["year"].astype(int)
    return df


def _prepare_chart_df() -> pd.DataFrame:
    """Normalize stacked area chart CSV."""
    df = _read_csv(CHART_CSV)
    if df.empty:
        return df
    df = df.rename(
        columns={
            "Year of Year": "year",
            "Crude": "stream",
            "Avg. Value": "value",
            "Country": "country",
        }
    )
    df = df[["year", "stream", "value", "country"]].copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["value"] = _to_numeric(df["value"])
    df["stream"] = df["stream"].astype(str).str.strip()
    df["country"] = df["country"].astype(str).str.strip()
    df = df.dropna(subset=["year", "stream", "value"])
    df["year"] = df["year"].astype(int)
    return df


def _prepare_table_df() -> pd.DataFrame:
    """Normalize table CSV."""
    df = _read_csv(TABLE_CSV)
    if df.empty:
        return df
    df = df.rename(
        columns={
            "Country": "country",
            "Crude": "crude",
            "Year of Year": "year",
            "Value": "value",
        }
    )
    df = df[["country", "crude", "year", "value"]].copy()
    df["country"] = df["country"].astype(str).str.strip()
    df["crude"] = df["crude"].astype(str).str.strip()
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["value"] = _to_numeric(df["value"])
    df = df.dropna(subset=["country", "crude", "year", "value"])
    df["year"] = df["year"].astype(int)
    return df


MAP_DF = _prepare_map_df()
CHART_DF = _prepare_chart_df()
TABLE_DF = _prepare_table_df()

_year_pool: List[int] = []
if not MAP_DF.empty:
    _year_pool.extend(MAP_DF["year"].unique().tolist())
if not TABLE_DF.empty:
    _year_pool.extend(TABLE_DF["year"].unique().tolist())
UNIQUE_YEARS = sorted(set(_year_pool))
YEAR_MIN = min(UNIQUE_YEARS) if UNIQUE_YEARS else 2006
YEAR_MAX = max(UNIQUE_YEARS) if UNIQUE_YEARS else 2024
if 2023 in UNIQUE_YEARS:
    DEFAULT_YEAR = 2023
else:
    DEFAULT_YEAR = UNIQUE_YEARS[-1] if UNIQUE_YEARS else None
DEFAULT_YEAR_STR = str(DEFAULT_YEAR) if DEFAULT_YEAR is not None else ""

if not CHART_DF.empty:
    CHART_MIN_YEAR = int(CHART_DF["year"].min())
    CHART_MAX_YEAR = int(CHART_DF["year"].max())
else:
    CHART_MIN_YEAR = DEFAULT_YEAR or 0
    CHART_MAX_YEAR = DEFAULT_YEAR or 0

DEFAULT_CHART_RANGE = (
    max(CHART_MIN_YEAR, CHART_MAX_YEAR - 9),
    CHART_MAX_YEAR,
) if CHART_MAX_YEAR else (CHART_MIN_YEAR, CHART_MAX_YEAR)

COUNTRY_OPTIONS = sorted(TABLE_DF["country"].unique().tolist()) if not TABLE_DF.empty else []
DEFAULT_COUNTRY = ["Russia"] if "Russia" in COUNTRY_OPTIONS else (COUNTRY_OPTIONS[:1] if COUNTRY_OPTIONS else [])
STREAM_ORDER = CHART_DF["stream"].dropna().unique().tolist() if not CHART_DF.empty else []
COLOR_PALETTE = [
    "#f15a24",
    "#1b365d",
    "#5b9bd5",
    "#ed8b00",
    "#6c757d",
    "#a05d56",
    "#17a398",
    "#c4b9a5",
    "#cb6ce6",
    "#ffa600",
]
STREAM_COLOR_MAP = {
    stream: COLOR_PALETTE[idx % len(COLOR_PALETTE)]
    for idx, stream in enumerate(STREAM_ORDER)
}

TABLE_COLUMNS = [
    {"name": "Country", "id": "country"},
    {"name": "Crude Stream", "id": "crude"},
    {"name": "Year", "id": "year"},
    {"name": "Volume (‘000 b/d)", "id": "value", "type": "numeric", "format": {"specifier": ",.0f"}},
]


def _build_slider_marks(years: Sequence[int]) -> Dict[int, str]:
    marks: Dict[int, str] = {}
    if not years:
        return marks
    for idx, year in enumerate(sorted(years)):
        if idx == 0 or idx == len(years) - 1 or idx % 3 == 0:
            marks[int(year)] = str(int(year))
    return marks


SLIDER_MARKS = _build_slider_marks(
    CHART_DF["year"].unique().tolist() if not CHART_DF.empty else []
)


def _normalize_year(year: Optional[int]) -> Optional[int]:
    if year is None:
        return DEFAULT_YEAR
    try:
        return int(year)
    except (TypeError, ValueError):
        return DEFAULT_YEAR


def _parse_year_value(value: Optional[str]) -> Optional[int]:
    if value is None:
        return DEFAULT_YEAR
    try:
        return int(value)
    except (TypeError, ValueError):
        return DEFAULT_YEAR


def _normalize_year_range(
    value: Optional[Sequence[int]],
) -> Tuple[int, int]:
    if not value:
        return DEFAULT_CHART_RANGE
    start, end = value
    if start is None or end is None:
        return DEFAULT_CHART_RANGE
    return int(start), int(end)


def _filter_table_data(
    year: Optional[int],
    countries: Optional[Sequence[str]],
) -> pd.DataFrame:
    if TABLE_DF.empty:
        return pd.DataFrame(columns=["country", "crude", "year", "value"])
    df = TABLE_DF.copy()
    normalized_year = _normalize_year(year)
    if normalized_year is not None:
        df = df[df["year"] == normalized_year]
    if countries:
        if isinstance(countries, str):
            countries = [countries]
        df = df[df["country"].isin(countries)]
    return df.sort_values(["country", "crude"])


def _empty_figure(message: str, height: int = 420) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        showarrow=False,
        font=dict(color="#6c757d", size=14),
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(
        paper_bgcolor="#f8f9fa",
        plot_bgcolor="#f8f9fa",
        height=height,
        margin=dict(l=0, r=0, t=10, b=0),
    )
    return fig


def _build_map_figure(year: Optional[int]) -> go.Figure:
    if MAP_DF.empty:
        return _empty_figure("No map data available")
    normalized_year = _normalize_year(year)
    df = MAP_DF[MAP_DF["year"] == normalized_year]
    if df.empty:
        return _empty_figure("No data for the selected year")
    max_value = df["value"].max() if not df.empty else None
    color_scale = [
        "#d6e3f3",
        "#a1c4e8",
        "#6b9ed6",
        "#336bb3",
        "#1b365d",
    ]
    fig = go.Figure(
        data=[
            go.Choropleth(
                locations=df["country"],
                z=df["value"],
                locationmode="country names",
                colorscale=color_scale,
                zmin=0,
                zmax=max_value if max_value else None,
                marker_line_color="#ffffff",
                marker_line_width=0.5,
                hovertemplate="<b>%{location}</b><br>Exports: %{z:,.0f} ’000 b/d<extra></extra>",
                colorbar=dict(
                    title="Exports (‘000 b/d)",
                    orientation="h",
                    x=0.5,
                    xanchor="center",
                    y=-0.2,
                    yanchor="top",
                    len=0.6,
                    thickness=16,
                    outlinewidth=0,
                    tickformat=",",
                    tickfont=dict(size=11, color="#1b365d"),
                    titlefont=dict(size=12, color="#1b365d"),
                    bgcolor="rgba(255,255,255,0)",
                ),
            )
        ]
    )
    fig.update_geos(
        showframe=False,
        showcoastlines=True,
        showcountries=True,
        projection_type="natural earth",
        bgcolor="rgba(0,0,0,0)",
        landcolor="#ffffff",
        countrycolor="#d0d0d0",
        coastlinecolor="#d0d0d0",
    )
    fig.update_layout(
        height=520,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=20, b=110),
        template="plotly_white",
    )
    fig.update_traces(colorbar=dict(tickmode="auto"))
    return fig


def _build_chart_figure(year_range: Tuple[int, int]) -> go.Figure:
    if CHART_DF.empty:
        return _empty_figure("No chart data available")
    start, end = year_range
    df = CHART_DF[
        (CHART_DF["year"] >= start) & (CHART_DF["year"] <= end)
    ]
    if df.empty:
        return _empty_figure("No data in the selected range")
    fig = px.area(
        df,
        x="year",
        y="value",
        color="stream",
        category_orders={"stream": STREAM_ORDER},
        color_discrete_map=STREAM_COLOR_MAP,
    )
    fig.update_layout(
        height=460,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=0, r=0, t=10, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            x=0,
            font=dict(size=11),
        ),
        hovermode="x unified",
        xaxis=dict(title="", tickformat="d"),
        yaxis=dict(title="‘000 b/d", separatethousands=True),
    )
    return fig


INITIAL_TABLE_DF = _filter_table_data(DEFAULT_YEAR, DEFAULT_COUNTRY)


def create_layout():
    """Create the Global Exports layout."""
    chart_range = DEFAULT_CHART_RANGE
    current_year_value = DEFAULT_YEAR or YEAR_MAX
    slider_disabled = not UNIQUE_YEARS
    slider_marks = {year: "" for year in UNIQUE_YEARS} if UNIQUE_YEARS else {}
    year_display_value = (
        DEFAULT_YEAR_STR if DEFAULT_YEAR_STR else str(current_year_value or YEAR_MAX)
    )
    return html.Div(
        [
            html.Div(
                [
                    html.H3(
                        "Global Exports",
                        style={
                            "marginBottom": "4px",
                            "color": "#d35400",
                            "textAlign": "center",
                        },
                    ),
                    html.P(
                        "Click on a Country from the map to view annual exports volume below:",
                        style={
                            "textAlign": "left",
                            "color": "#6c757d",
                            "marginBottom": "30px",
                        },
                    ),
                ]
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                id="global-exports-map-title",
                                children=f"Crude Exports — {DEFAULT_YEAR or 'N/A'}",
                                style={
                                    "fontWeight": "bold",
                                    "color": "#1b365d",
                                    "marginBottom": "10px",
                                },
                            ),
                            dcc.Graph(
                                id="global-exports-map",
                                config={"displayModeBar": False},
                                figure=_build_map_figure(DEFAULT_YEAR),
                                style={"height": "520px"},
                            ),
                        ],
                        className="col-md-9",
                        style={"padding": "10px"},
                    ),
                    html.Div(
                        [
                            html.Label(
                                "Year",
                                style={
                                    "fontWeight": "bold",
                                    "color": "#2c3e50",
                                    "fontSize": "13px",
                                },
                            ),
                            html.Div(
                                [
                                    html.Button(
                                        "◄",
                                        id="global-exports-year-decrement",
                                        n_clicks=0,
                                        style={
                                            "width": "28px",
                                            "height": "28px",
                                            "border": "1px solid #b3b3b3",
                                            "backgroundColor": "#ffffff",
                                            "cursor": "pointer",
                                            "fontSize": "12px",
                                            "padding": "0",
                                            "marginRight": "4px",
                                            "borderRadius": "3px",
                                            "color": "#333333",
                                        },
                                    ),
                                    dcc.Input(
                                        id="global-exports-year-input",
                                        type="number",
                                        value=current_year_value,
                                        min=YEAR_MIN,
                                        max=YEAR_MAX,
                                        step=1,
                                        style={
                                            "width": "70px",
                                            "height": "26px",
                                            "textAlign": "center",
                                            "border": "1px solid #b3b3b3",
                                            "fontSize": "13px",
                                            "padding": "2px 5px",
                                            "fontWeight": "500",
                                            "color": "#333333",
                                        },
                                    ),
                                    html.Button(
                                        "►",
                                        id="global-exports-year-increment",
                                        n_clicks=0,
                                        style={
                                            "width": "28px",
                                            "height": "28px",
                                            "border": "1px solid #b3b3b3",
                                            "backgroundColor": "#ffffff",
                                            "cursor": "pointer",
                                            "fontSize": "12px",
                                            "padding": "0",
                                            "marginLeft": "4px",
                                            "borderRadius": "3px",
                                            "color": "#333333",
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "marginBottom": "8px",
                                },
                            ),
                            dcc.Slider(
                                id="global-exports-year-slider",
                                min=YEAR_MIN,
                                max=YEAR_MAX,
                                value=current_year_value,
                                step=1,
                                marks=slider_marks,
                                tooltip={"placement": "bottom", "always_visible": False},
                                disabled=slider_disabled,
                            ),
                            html.Div(
                                id="global-exports-year-display",
                                children=year_display_value,
                                style={"display": "none"},
                            ),
                            html.Br(),
                            html.Label("Country filter"),
                            dcc.Dropdown(
                                id="global-exports-country-filter",
                                options=[
                                    {"label": country, "value": country}
                                    for country in COUNTRY_OPTIONS
                                ],
                                value=DEFAULT_COUNTRY if DEFAULT_COUNTRY else None,
                                multi=True,
                                placeholder="All countries",
                            ),
                        ],
                        className="col-md-3",
                        style={"padding": "10px"},
                    ),
                ],
                className="row",
            ),
            html.Div(
                [
                    html.H4(
                        "Russia Annual Exports by Crude Stream",
                        style={"color": "#1b365d", "marginTop": "30px"},
                    ),
                    html.Div(
                        [
                            html.Label("Year range", style={"fontWeight": "bold"}),
                            dcc.RangeSlider(
                                id="global-exports-year-range",
                                min=CHART_MIN_YEAR,
                                max=CHART_MAX_YEAR,
                                value=list(chart_range),
                                marks=SLIDER_MARKS,
                                allowCross=False,
                                tooltip={"placement": "bottom", "always_visible": False},
                                updatemode="mouseup",
                            ),
                        ],
                        style={"margin": "10px 0 20px"},
                    ),
                    dcc.Graph(
                        id="global-exports-stream-chart",
                        figure=_build_chart_figure(chart_range),
                    ),
                ],
                style={"marginTop": "30px"},
            ),
            html.Div(
                [
                    html.H4(
                        "Annual Exports Volume (‘000 b/d)",
                        style={
                            "marginTop": "30px",
                            "marginBottom": "10px",
                            "color": "#1b365d",
                        },
                    ),
                    dash_table.DataTable(
                        id="global-exports-table",
                        columns=TABLE_COLUMNS,
                        data=INITIAL_TABLE_DF.to_dict("records"),
                        page_action="native",
                        page_size=25,
                        sort_action="native",
                        style_table={
                            "overflowX": "auto",
                            "backgroundColor": "white",
                        },
                        style_cell={
                            "textAlign": "left",
                            "fontSize": "12px",
                            "padding": "6px",
                            "fontFamily": "Lato, Arial, sans-serif",
                        },
                        style_header={
                            "backgroundColor": "#f0f2f5",
                            "fontWeight": "bold",
                            "color": "#1b365d",
                        },
                        style_data_conditional=[
                            {
                                "if": {"row_index": "odd"},
                                "backgroundColor": "#f9fbfd",
                            }
                        ],
                    ),
                ]
            ),
            html.P(
                "Source: Energy Intelligence (Global Crude Exports dashboard).",
                style={"fontSize": "11px", "color": "#6c757d", "marginTop": "15px"},
            ),
        ],
        className="tab-content",
        style={"padding": "20px", "backgroundColor": "#f8f9fa"},
    )


def register_callbacks(dash_app, server):  # pylint: disable=unused-argument
    """Register callbacks for the Global Exports view."""

    @callback(
        Output("global-exports-year-input", "value"),
        Output("global-exports-year-slider", "value"),
        Output("global-exports-year-display", "children"),
        Input("global-exports-year-input", "value"),
        Input("global-exports-year-slider", "value"),
        Input("global-exports-year-increment", "n_clicks"),
        Input("global-exports-year-decrement", "n_clicks"),
        State("global-exports-year-display", "children"),
        State("global-exports-year-slider", "min"),
        State("global-exports-year-slider", "max"),
        prevent_initial_call=True,
    )
    def sync_year_controls(
        input_value,
        slider_value,
        inc_clicks,
        dec_clicks,
        current_year,
        min_year,
        max_year,
    ):
        """Keep year input, slider, and hidden store aligned."""
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        fallback_year = DEFAULT_YEAR or YEAR_MAX
        try:
            current_year_int = int(current_year) if current_year else fallback_year
        except (TypeError, ValueError):
            current_year_int = fallback_year
        min_year = min_year or YEAR_MIN
        max_year = max_year or YEAR_MAX
        if trigger_id == "global-exports-year-increment":
            new_year = min(current_year_int + 1, max_year)
        elif trigger_id == "global-exports-year-decrement":
            new_year = max(current_year_int - 1, min_year)
        elif trigger_id == "global-exports-year-input":
            if input_value is None:
                new_year = current_year_int
            else:
                try:
                    new_year = max(min(int(input_value), max_year), min_year)
                except (TypeError, ValueError):
                    new_year = current_year_int
        elif trigger_id == "global-exports-year-slider":
            new_year = slider_value if slider_value is not None else current_year_int
        else:
            new_year = current_year_int
        return new_year, new_year, str(new_year)

    @callback(
        Output("global-exports-map", "figure"),
        Output("global-exports-map-title", "children"),
        Input("current-submenu", "data"),
        Input("global-exports-year-display", "children"),
    )
    def update_map(submenu: str, year_str: Optional[str]):
        """Update the map when the submenu or year changes."""
        if submenu != "global-exports":
            return _empty_figure(""), no_update
        year_value = _parse_year_value(year_str)
        normalized_year = _normalize_year(year_value)
        title = f"Crude Exports — {normalized_year or 'N/A'}"
        return _build_map_figure(normalized_year), title

    @callback(
        Output("global-exports-stream-chart", "figure"),
        Input("current-submenu", "data"),
        Input("global-exports-year-range", "value"),
    )
    def update_chart(submenu: str, year_range: Sequence[int]):
        """Update stacked area chart."""
        if submenu != "global-exports":
            return _empty_figure("")
        normalized_range = _normalize_year_range(year_range)
        return _build_chart_figure(normalized_range)

    @callback(
        Output("global-exports-table", "data"),
        Input("current-submenu", "data"),
        Input("global-exports-year-display", "children"),
        Input("global-exports-country-filter", "value"),
    )
    def update_table(
        submenu: str,
        year_str: Optional[str],
        countries: Optional[Sequence[str]],
    ):
        """Update table data."""
        if submenu != "global-exports":
            return []
        year_value = _parse_year_value(year_str)
        filtered = _filter_table_data(year_value, countries)
        return filtered.to_dict("records")

    @callback(
        Output("global-exports-country-filter", "value"),
        Input("global-exports-map", "clickData"),
        State("global-exports-country-filter", "options"),
        prevent_initial_call=True,
    )
    def sync_country_from_map(click_data, options):
        """When a country is clicked on the map, update the dropdown selection."""
        if not click_data or not click_data.get("points"):
            return dash.no_update
        country = click_data["points"][0].get("location") or click_data["points"][0].get("text")
        if not country:
            return dash.no_update
        valid_values = {opt["value"] for opt in (options or [])}
        if country not in valid_values:
            return dash.no_update
        return [country]

