"""
Global Exports View
Replicates Tableau Global Crude Exports dashboard with local CSV data
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Sequence, Tuple

import dash
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import (
    ALL,
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
YEAR_AXIS_FULL = [str(year) for year in range(2006, 2025)]

if not CHART_DF.empty:
    CHART_MIN_YEAR = int(CHART_DF["year"].min())
    CHART_MAX_YEAR = int(CHART_DF["year"].max())
else:
    CHART_MIN_YEAR = DEFAULT_YEAR or 0
    CHART_MAX_YEAR = DEFAULT_YEAR or 0

COUNTRY_OPTIONS = sorted(TABLE_DF["country"].unique().tolist()) if not TABLE_DF.empty else []
DEFAULT_COUNTRY = ["Russia"] if "Russia" in COUNTRY_OPTIONS else (COUNTRY_OPTIONS[:1] if COUNTRY_OPTIONS else [])

STREAM_DISPLAY = [
    ("Arco", "#0069aa"),
    ("Espo Blend", "#20295e"),
    ("Novy Port", "#a95b41"),
    ("Other Crudes - Russia", "#a95b41"),
    ("Sakhalin Blend", "#4e83bb"),
    ("Siberian Light", "#313849"),
    ("Sokol", "#cb4515"),
    ("Urals", "#826ecc"),
    ("Varandey", "#a6a6a6"),
    ("Vityaz", "#0069aa"),
    ("YK Blend", "#595959"),
]
STREAM_ORDER = [name for name, _ in STREAM_DISPLAY]
STREAM_COLOR_MAP = {name: color for name, color in STREAM_DISPLAY}
FALLBACK_COLORS = [
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

YEAR_COLUMNS = sorted(TABLE_DF["year"].unique().tolist(), reverse=True) if not TABLE_DF.empty else []
YEAR_COLUMN_IDS = [str(year) for year in YEAR_COLUMNS]
TABLE_STATIC_COLUMNS = [
    {"name": "", "id": "country"},
    {"name": "", "id": "crude"},
]
TABLE_YEAR_COLUMNS = [
    {"name": str(year), "id": str(year), "type": "numeric", "format": {"specifier": ",.0f"}}
    for year in YEAR_COLUMNS
]
TABLE_COLUMNS = TABLE_STATIC_COLUMNS + TABLE_YEAR_COLUMNS


def _stream_filter_options() -> List[Dict[str, html.Span]]:
    """Create checklist options with colored swatches."""
    options: List[Dict[str, html.Span]] = []
    for name, color in STREAM_DISPLAY:
        label = html.Span(
            [
                html.Span(
                    "",
                    style={
                        "display": "inline-block",
                        "width": "14px",
                        "height": "14px",
                        "backgroundColor": color,
                        "borderRadius": "2px",
                        "marginRight": "10px",
                        "border": "1px solid #cfd8e3",
                        "boxShadow": "0 0 2px rgba(0,0,0,0.1)",
                    },
                ),
                html.Button(
                    name,
                    id={"type": "stream-isolate-button", "stream": name},
                    n_clicks=0,
                    type="button",
                    style={
                        "border": "none",
                        "background": "transparent",
                        "padding": "0",
                        "margin": "0",
                        "textAlign": "left",
                        "color": "#1b365d",
                        "fontWeight": "600",
                        "fontSize": "13px",
                        "cursor": "pointer",
                        "userSelect": "none",
                    },
                ),
            ],
            style={"display": "flex", "alignItems": "center", "width": "100%"},
        )
        options.append({"label": label, "value": name})
    return options


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


def _filter_table_data(
    year: Optional[int],
    countries: Optional[Sequence[str]],
) -> pd.DataFrame:
    if TABLE_DF.empty:
        return pd.DataFrame(columns=["country", "crude", "year", "value"])
    df = TABLE_DF.copy()
    if countries:
        if isinstance(countries, str):
            countries = [countries]
        df = df[df["country"].isin(countries)]
    return df.sort_values(["country", "crude"])


def _prepare_table_records(df: pd.DataFrame) -> List[Dict[str, object]]:
    """Pivot yearly values into wide format for the data table."""
    if df.empty:
        return []
    years = YEAR_COLUMNS or sorted(df["year"].unique(), reverse=True)
    pivot = (
        df.pivot_table(index=["country", "crude"], columns="year", values="value", aggfunc="sum")
        .reindex(columns=years, fill_value=None)
        .reset_index()
    )
    pivot.columns = [str(col) for col in pivot.columns]
    pivot = pivot.sort_values(["country", "crude"]).reset_index(drop=True)
    records = pivot.to_dict("records")
    last_country = None
    for row in records:
        country_value = row.get("country")
        if country_value == last_country:
            row["country"] = ""
        else:
            last_country = country_value
    return records


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


def _build_chart_figure(selected_streams: Optional[Sequence[str]] = None) -> go.Figure:
    if CHART_DF.empty:
        return _empty_figure("No chart data available")
    streams = (
        [s for s in STREAM_ORDER if s in selected_streams]
        if selected_streams
        else STREAM_ORDER
    )
    if not streams:
        return _empty_figure("Select at least one stream")
    df = CHART_DF[
        (CHART_DF["year"].between(2006, 2024))
        & (CHART_DF["stream"].isin(streams))
    ].copy()
    if "country" in df.columns:
        df = df[df["country"].str.lower() == "russia"]
    if df.empty:
        return _empty_figure("No data in the selected range")
    country_label = (
        df["country"].dropna().iloc[0]
        if "country" in df.columns and not df["country"].dropna().empty
        else "Russia"
    )
    agg = df.groupby(["year", "stream"])["value"].sum().reset_index()
    agg["year"] = agg["year"].astype(int)
    agg = agg[(agg["year"] >= 2006) & (agg["year"] <= 2024)].copy()
    agg = agg.sort_values(["year", "stream"])
    available_streams = [s for s in STREAM_ORDER if s in agg["stream"].unique()]
    if not available_streams:
        return _empty_figure("No stream data available")
    complete_index = pd.MultiIndex.from_product(
        (YEAR_AXIS_FULL, available_streams), names=["year", "stream"]
    )
    agg = (
        agg.assign(year=agg["year"].astype(str))
        .set_index(["year", "stream"])
        .reindex(complete_index, fill_value=0)
        .reset_index()
    )
    fig = go.Figure()
    fallback_idx = 0
    years_sorted = YEAR_AXIS_FULL
    for stream in available_streams:
        stream_df = agg[agg["stream"] == stream]
        if stream_df.empty:
            continue
        color = STREAM_COLOR_MAP.get(stream)
        if not color:
            color = FALLBACK_COLORS[fallback_idx % len(FALLBACK_COLORS)]
            fallback_idx += 1
        fig.add_bar(
            x=stream_df["year"],
            y=stream_df["value"],
            name=stream,
            marker_color=color,
            hovertemplate=(
                "<span style='color:#1b365d; font-weight:300;'>Country:</span> "
                f"<span style='color:#1b365d; font-weight:700;'>{country_label}</span><br>"
                "<span style='color:#1b365d; font-weight:300;'>Year:</span> "
                "<span style='color:#1b365d; font-weight:700;'>%{x}</span><br>"
                "<span style='color:#1b365d; font-weight:300;'>Exports Volume:</span> "
                "<span style='color:#1b365d; font-weight:700;'>%{y:,.0f} ’000 b/d</span>"
                "<extra></extra>"
            ),
        )
    fig.update_layout(
        height=460,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=40, b=40),
        barmode="stack",
        showlegend=False,
        xaxis=dict(
            title="",
            tickformat="d",
            categoryorder="array",
            categoryarray=years_sorted,
        ),
        yaxis=dict(title="Export Volume ('000 b/d)", separatethousands=True),
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="#ffffff",
            font=dict(color="#1b365d", size=12, family="Lato, Arial, sans-serif"),
            bordercolor="#dfe3eb",
        ),
    )
    return fig


INITIAL_TABLE_RAW = _filter_table_data(DEFAULT_YEAR, None)
INITIAL_TABLE_DATA = _prepare_table_records(INITIAL_TABLE_RAW)


def create_layout():
    """Create the Global Exports layout."""
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
                    html.P(
                        "Click on a Country from the map to view annual exports volume below:",
                        style={
                            "textAlign": "left",
                            "color": "#6c757d",
                            "marginBottom": "10px",
                        },
                    ),
                    html.H3(
                        "Global Exports",
                        style={
                            "marginBottom": "20px",
                            "color": "#d35400",
                            "textAlign": "center",
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
                        ],
                        className="col-md-3",
                        style={"padding": "10px"},
                    ),
                ],
                className="row",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H4(
                                "Russia Annual Exports by Crude Stream",
                                style={"color": "#1b365d"},
                            ),
                            dcc.Graph(
                                id="global-exports-stream-chart",
                                figure=_build_chart_figure(STREAM_ORDER),
                            ),
                        ],
                        className="col-md-9",
                        style={"padding": "15px"},
                    ),
                    html.Div(
                        [
                            dcc.Checklist(
                                id="global-exports-stream-filter",
                                options=_stream_filter_options(),
                                value=STREAM_ORDER,
                                style={
                                    "display": "flex",
                                    "flexDirection": "column",
                                    "gap": "2px",
                                    "marginTop": "2px",
                                },
                                labelStyle={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "gap": "2px",
                                    "padding": "2px 2px",
                                    "borderRadius": "4px",
                                    "border": "0px solid #dfe3eb",
                                    "backgroundColor": "#ffffff",
                                    "width": "100%",
                                    "boxShadow": "0 1px 2px rgba(0,0,0,0.05)",
                                    "cursor": "pointer",
                                    "transition": "background-color 0.2s ease, border-color 0.2s ease",
                                    "userSelect": "none",
                                },
                                inputStyle={
                                    "marginRight": "12px",
                                    "width": "18px",
                                    "height": "18px",
                                    "cursor": "pointer",
                                },
                            ),
                        ],
                        className="col-md-3",
                        style={
                            "padding": "25px 20px",
                            "border": "0px solid #dfe3eb",
                            "borderRadius": "6px",
                            "backgroundColor": "#f8f9fb",
                            "height": "100%",
                            "maxHeight": "520px",
                            "overflowY": "auto",
                            "boxShadow": "0 2px 6px rgba(0,0,0,0.05)",
                            "marginLeft": "0",
                        },
                    ),
                ],
                className="row",
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
                        data=INITIAL_TABLE_DATA,
                        sort_action="native",
                        page_action="none",
                        style_table={
                            "overflowX": "auto",
                            "overflowY": "auto",
                            "backgroundColor": "white",
                            "maxHeight": "520px",
                            "border": "1px solid #e6e9ef",
                        },
                        style_cell={
                            "fontSize": "12px",
                            "padding": "5px 8px",
                            "fontFamily": "Lato, Arial, sans-serif",
                            "border": "1px solid #e6e9ef",
                        },
                        style_cell_conditional=[
                            {
                                "if": {"column_id": "country"},
                                "width": "160px",
                                "fontWeight": "600",
                                "color": "#1b365d",
                                "textAlign": "left",
                            },
                            {
                                "if": {"column_id": "crude"},
                                "width": "220px",
                                "color": "#1b365d",
                                "textAlign": "left",
                            },
                        ]
                        + [
                            {
                                "if": {"column_id": col_id},
                                "textAlign": "right",
                                "width": "70px",
                            }
                            for col_id in YEAR_COLUMN_IDS
                        ],
                        style_header={
                            "backgroundColor": "#f0f2f5",
                            "fontWeight": "600",
                            "color": "#1b365d",
                            "textAlign": "center",
                            "border": "1px solid #dfe3eb",
                        },
                        style_data_conditional=[
                            {
                                "if": {"row_index": "odd"},
                                "backgroundColor": "#f9fbfd",
                            }
                        ]
                        + [
                            {
                                "if": {"column_id": col_id},
                                "color": "#1b365d",
                            }
                            for col_id in YEAR_COLUMN_IDS
                        ],
                    ),
                ],
                className="col-md-9",
                style={"padding": "15px"},
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
        Input("global-exports-stream-filter", "value"),
    )
    def update_chart(submenu: str, streams: Optional[Sequence[str]]):
        """Update stacked area chart."""
        if submenu != "global-exports":
            return _empty_figure("")
        return _build_chart_figure(streams)

    @callback(
        Output("global-exports-stream-filter", "value"),
        Input({"type": "stream-isolate-button", "stream": ALL}, "n_clicks"),
        State("global-exports-stream-filter", "value"),
        prevent_initial_call=True,
    )
    def isolate_stream(_buttons, current_value):
        """Single-click a stream name to solo that series."""
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update
        triggered = ctx.triggered[0]["prop_id"].split(".")[0]
        try:
            stream_id = json.loads(triggered)
            stream_name = stream_id.get("stream")
        except (ValueError, TypeError, AttributeError):
            stream_name = None
        if not stream_name:
            return dash.no_update
        current_value = current_value or STREAM_ORDER
        if isinstance(current_value, list) and len(current_value) == 1 and current_value[0] == stream_name:
            return STREAM_ORDER
        return [stream_name]

    @callback(
        Output("global-exports-table", "data"),
        Input("current-submenu", "data"),
        Input("global-exports-year-display", "children"),
    )
    def update_table(
        submenu: str,
        year_str: Optional[str],
    ):
        """Update table data."""
        if submenu != "global-exports":
            return []
        year_value = _parse_year_value(year_str)
        filtered = _filter_table_data(year_value, None)
        return _prepare_table_records(filtered)

