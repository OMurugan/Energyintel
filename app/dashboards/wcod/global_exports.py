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

from core.data_helpers import execute_query

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
    """Load and normalize map data from database."""
    query = """
    SELECT 
        -- Static columns
        'Source: Energy Intelligence' AS "Source",
        'COPYRIGHT &copy; 2001-2021 ENERGY INTELLIGENCE GROUP, INC. / ENERGY INTELLIGENCE GROUP (UK) LIMITED.'
            AS "Copyright",
        fwc.country_long_name AS "Country",
        EXTRACT(YEAR FROM fwc.yr) AS "Year of Year",
        dc.latitude AS "Latitude",
        dc.longitude AS "Longitude",
        fwc.exports AS "Value"
    FROM dev.fact_wcod_country AS fwc
    LEFT JOIN dev.dim_country AS dc
        ON dc.dim_country_id = fwc.country_id
    """
    
    try:
        results = execute_query(query)
        if not results:
            return pd.DataFrame()
        df = pd.DataFrame(results)
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"[global_exports] Failed to execute map data query: {exc}")
        return pd.DataFrame()
    
    if df.empty:
        return df
    
    df.columns = df.columns.str.strip()
    df = df.rename(
        columns={
            "Country": "country",
            "Year of Year": "year",
            "Latitude": "lat",
            "Longitude": "lon",
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
MAP_VALUE_MAX_LABEL = (
    f"{(MAP_DF['value'].max() / 1000):,.3f}"
    if not MAP_DF.empty and MAP_DF["value"].max() > 0
    else "0"
)

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
DEFAULT_COUNTRY = (
    ["Russia"] if "Russia" in COUNTRY_OPTIONS else (COUNTRY_OPTIONS[:1] if COUNTRY_OPTIONS else [])
)

# Base stream configuration – explicit ordering and colors requested by design
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

# Fallback colors used for any additional streams that appear in the CSV data
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

# Extend stream list dynamically based on the chart CSV
# This ensures that when Chart_Crude_data.csv contains multiple countries and
# many crude streams (as in the Tableau "All Annual Exports by Crude Stream"
# view), the chart and right-side filter include ALL available streams,
# not just the original Russia-only list.
if not CHART_DF.empty:
    existing_streams = set(STREAM_COLOR_MAP.keys())
    csv_streams = sorted(
        {str(s).strip() for s in CHART_DF["stream"].dropna().unique().tolist()}
    )
    extra_streams = [s for s in csv_streams if s not in existing_streams]

    if extra_streams:
        for idx, stream_name in enumerate(extra_streams):
            # Assign a fallback color; reuse the palette in a cycle
            color = FALLBACK_COLORS[idx % len(FALLBACK_COLORS)]
            STREAM_COLOR_MAP[stream_name] = color

        # Preserve the explicit design order first, then append additional streams
        STREAM_ORDER = STREAM_ORDER + extra_streams

MAP_COLOR_SCALE = [
    "#f2f4f6",
    "#e9edf2",
    "#e1e6ee",
    "#d9dee8",
    "#d0d6e2",
    "#c7cedc",
    "#bec6d6",
    "#b3bfd0",
    "#a8b7ca",
    "#9dafc4",
    "#91a7be",
    "#859fb9",
    "#7a96b3",
    "#6f8dae",
    "#6384a8",
    "#577ba2",
    "#4d739b",
    "#466b93",
    "#41638b",
    "#3c5a83",
]
MAP_COLOR_STEPS = [
    (idx / (len(MAP_COLOR_SCALE) - 1), color)
    for idx, color in enumerate(MAP_COLOR_SCALE)
]
COLOR_LEGEND_WIDTH = len(MAP_COLOR_SCALE) * 18

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


def _country_filter_options(country_names: Sequence[str]) -> List[Dict[str, str]]:
    """Create checklist options for countries with ALL option first."""
    options: List[Dict[str, str]] = [
        {"label": "ALL", "value": "ALL"}
    ] + [
        {"label": country, "value": country}
        for country in country_names
    ]
    return options


def _stream_filter_options(stream_names: Sequence[str]) -> List[Dict[str, html.Span]]:
    """Create checklist options with colored swatches for the given streams."""
    options: List[Dict[str, html.Span]] = []
    for name in stream_names:
        # Use explicit color mapping when available, otherwise fall back
        color = STREAM_COLOR_MAP.get(name)
        if not color:
            # Deterministic fallback based on name hash so it is stable across reloads
            idx = abs(hash(name)) % len(FALLBACK_COLORS)
            color = FALLBACK_COLORS[idx]

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


def _streams_for_countries(
    selected_countries: Optional[Sequence[str]],
) -> List[str]:
    """
    Return ordered list of crude streams available for the given countries.

    - If no countries are selected or "ALL" is included, use all countries.
    - Order:
        1. Streams in STREAM_ORDER that appear in the data.
        2. Any additional streams for those countries, sorted alphabetically.
    """
    if CHART_DF.empty:
        return STREAM_ORDER

    df = CHART_DF.copy()
    if "country" in df.columns and selected_countries and "ALL" not in selected_countries:
        selected_lower = [c.lower() for c in selected_countries]
        df = df[df["country"].str.strip().str.lower().isin(selected_lower)]
        # If filtering by country removes everything, fall back to all data
        if df.empty:
            df = CHART_DF.copy()

    if "stream" not in df.columns:
        return STREAM_ORDER

    streams_in_data = {
        str(s).strip() for s in df["stream"].dropna().unique().tolist()
    }

    # Preserve explicit design order first
    ordered = [s for s in STREAM_ORDER if s in streams_in_data]
    # Then include any additional streams
    extra = sorted([s for s in streams_in_data if s not in STREAM_ORDER])
    return ordered + extra


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


def _build_map_figure(year: Optional[int], highlight_country: Optional[str] = None) -> go.Figure:
    if MAP_DF.empty:
        return _empty_figure("No map data available")
    normalized_year = _normalize_year(year)
    df = MAP_DF[MAP_DF["year"] == normalized_year]
    if df.empty:
        return _empty_figure("No data for the selected year")
    max_value = df["value"].max() if not df.empty else None
    fig = go.Figure(
        data=[
            go.Choropleth(
                locations=df["country"],
                z=df["value"],
                locationmode="country names",
                colorscale=MAP_COLOR_STEPS,
                zmin=0,
                zmax=max_value if max_value else None,
                marker_line_color="#ffffff",
                marker_line_width=0.5,
                hovertemplate="<b>%{location}</b><br>Exports: %{z:,.0f} ’000 b/d<extra></extra>",
                showscale=False,
            )
        ]
    )
    # Add country labels with density control to reduce overlap at wide zooms
    centroids = (
        df.groupby("country")[["lat", "lon"]]
        .mean()
        .reset_index()
        .dropna(subset=["lat", "lon"])
    )
    label_cap = len(centroids)
    if len(centroids) > 120:
        label_cap = 40
    elif len(centroids) > 80:
        label_cap = 60
    labels_df = (
        centroids.sort_values("country")
        .head(label_cap)
    )
    fig.add_trace(
        go.Scattergeo(
            lon=labels_df["lon"],
            lat=labels_df["lat"],
            mode="text",
            text=labels_df["country"],
            textfont=dict(size=8, color="#2c3e50"),
            textposition="top center",
            hoverinfo="skip",
            showlegend=False,
        )
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
        margin=dict(l=0, r=0, t=20, b=110),
        template="plotly_white",
    )
    if highlight_country:
        highlight_list = (
            highlight_country
            if isinstance(highlight_country, list)
            else [highlight_country]
        )
        highlight_list = [c for c in highlight_list if c]
        if highlight_list:
            fig.add_trace(
                go.Choropleth(
                    locations=highlight_list,
                    locationmode="country names",
                    z=[max_value or 1] * len(highlight_list),
                    colorscale=[[0, "#2f3f5c"], [1, "#2f3f5c"]],
                    showscale=False,
                    marker_line_color="#182238",
                    marker_line_width=1.6,
                    hoverinfo="skip",
                )
            )
    return fig


def _build_chart_figure(
    selected_streams: Optional[Sequence[str]] = None,
    selected_countries: Optional[Sequence[str]] = None,
) -> go.Figure:
    if CHART_DF.empty:
        return _empty_figure("No chart data available")
    streams = (
        [s for s in STREAM_ORDER if s in selected_streams]
        if selected_streams
        else STREAM_ORDER
    )
    if not streams:
        return _empty_figure("Select at least one stream")
    # First, determine which countries to include (before filtering by streams)
    # Use selected countries directly, but match with data country names for consistency
    if selected_countries:
        if "ALL" in selected_countries:
            # Get all countries from the full dataset
            if "country" in CHART_DF.columns:
                all_countries_in_data = CHART_DF["country"].str.strip().unique()
                target_countries = sorted([c for c in all_countries_in_data if pd.notna(c)])
            else:
                target_countries = []
        else:
            # Start with selected countries, then match with data country names
            target_countries = []
            if "country" in CHART_DF.columns:
                all_countries_in_data = CHART_DF["country"].str.strip().unique()
                data_countries_lower = {c.lower(): c for c in all_countries_in_data if pd.notna(c)}
                
                # Match each selected country with data country names (case-insensitive)
                for selected in selected_countries:
                    selected_lower = selected.lower().strip()
                    if selected_lower in data_countries_lower:
                        # Use the exact name from data
                        target_countries.append(data_countries_lower[selected_lower])
                    else:
                        # If not found in data, still include the selected name
                        # (it might have data, or will show as 0)
                        target_countries.append(selected)
            else:
                # No country column in data, use selected countries as-is
                target_countries = selected_countries.copy()
            target_countries = sorted(set(target_countries))
    else:
        # Default to Russia if no selection
        if "country" in CHART_DF.columns:
            all_countries_in_data = CHART_DF["country"].str.strip().unique()
            russia_match = [c for c in all_countries_in_data if pd.notna(c) and c.lower().strip() == "russia"]
            target_countries = russia_match if russia_match else ["Russia"]
        else:
            target_countries = ["Russia"]
    
    # Now filter by streams and years
    df = CHART_DF[
        (CHART_DF["year"].between(2006, 2024))
        & (CHART_DF["stream"].isin(streams))
    ].copy()
    
    # Filter by selected countries (case-insensitive, using exact names from target_countries)
    if "country" in df.columns and target_countries:
        # Normalize both data countries and target countries for matching
        df_countries_normalized = df["country"].str.strip().str.lower()
        target_countries_normalized = {c.lower().strip(): c for c in target_countries}
        
        # Filter df by matching countries (case-insensitive)
        mask = df_countries_normalized.isin(target_countries_normalized.keys())
        df = df[mask].copy()
        
        # Map country names to use exact names from target_countries
        # This ensures consistency throughout the rest of the code
        if not df.empty:
            # Create reverse mapping: normalized data country -> target country name
            country_name_map = {}
            for data_country in df["country"].unique():
                data_country_normalized = str(data_country).strip().lower()
                if data_country_normalized in target_countries_normalized:
                    country_name_map[data_country] = target_countries_normalized[data_country_normalized]
                else:
                    # Keep original if no match (shouldn't happen after mask, but safety)
                    country_name_map[data_country] = data_country
            
            df["country"] = df["country"].map(country_name_map).fillna(df["country"])
    
    if df.empty and not target_countries:
        return _empty_figure("No data in the selected range")
    # Determine country label for display
    if selected_countries and "ALL" not in selected_countries and len(selected_countries) == 1:
        country_label = selected_countries[0]
    elif selected_countries and "ALL" in selected_countries:
        country_label = "All Countries"
    elif selected_countries and len(selected_countries) > 1:
        country_label = f"{len(selected_countries)} Countries"
    else:
        country_label = (
            df["country"].dropna().iloc[0]
            if "country" in df.columns and not df["country"].dropna().empty
            else "Russia"
        )
    # Group by year, stream, and country to keep each country-crude combination separate
    if not df.empty:
        if "country" in df.columns:
            agg = df.groupby(["year", "stream", "country"])["value"].sum().reset_index()
            # Ensure country names match target_countries exactly (case-insensitive match)
            if target_countries:
                # Create mapping from current country names to target_countries names
                country_mapping = {}
                for country in agg["country"].unique():
                    country_lower = str(country).lower().strip()
                    for target in target_countries:
                        if country_lower == target.lower().strip():
                            country_mapping[country] = target
                            break
                    # If no match found, keep original
                    if country not in country_mapping:
                        country_mapping[country] = country
                agg["country"] = agg["country"].map(country_mapping).fillna(agg["country"])
        else:
            agg = df.groupby(["year", "stream"])["value"].sum().reset_index()
            agg["country"] = country_label
        agg["year"] = agg["year"].astype(int)
        agg = agg[(agg["year"] >= 2006) & (agg["year"] <= 2024)].copy()
        agg = agg.sort_values(["year", "stream", "country"])
        available_streams = [s for s in STREAM_ORDER if s in agg["stream"].unique()]
    else:
        # If df is empty, create empty agg but still use selected streams
        agg = pd.DataFrame(columns=["year", "stream", "country", "value"])
        available_streams = streams if streams else STREAM_ORDER
    
    if not available_streams:
        return _empty_figure("No stream data available")
    
    fig = go.Figure()
    fallback_idx = 0
    years_sorted = YEAR_AXIS_FULL
    
    # Get unique countries - use target_countries to ensure all selected countries are included
    # target_countries already contains matched country names from data, so use it directly
    if target_countries:
        unique_countries = target_countries.copy()
        # Also add any countries from the filtered data that might not be in target_countries
        # (this handles edge cases where country names in data don't match exactly)
        if "country" in df.columns and not df.empty:
            for country in df["country"].unique():
                country_str = str(country).strip()
                # Check if this country is already in unique_countries (case-insensitive)
                if not any(c.lower().strip() == country_str.lower() for c in unique_countries):
                    unique_countries.append(country_str)
        elif "country" in agg.columns and not agg.empty:
            for country in agg["country"].unique():
                country_str = str(country).strip()
                if not any(c.lower().strip() == country_str.lower() for c in unique_countries):
                    unique_countries.append(country_str)
        unique_countries = sorted(set(unique_countries))
    elif "country" in df.columns and not df.empty:
        unique_countries = sorted(df["country"].unique().tolist())
    elif "country" in agg.columns and not agg.empty:
        unique_countries = sorted(agg["country"].unique().tolist())
    else:
        unique_countries = [country_label]
    
    # Create a complete index for all year-stream-country combinations
    # Use unique_countries to ensure all selected countries are included
    complete_index = pd.MultiIndex.from_product(
        (YEAR_AXIS_FULL, available_streams, unique_countries),
        names=["year", "stream", "country"]
    )
    
    # Prepare agg for reindexing - ensure country column exists and has correct names
    if not agg.empty:
        if "country" in agg.columns:
            # Ensure country names in agg match unique_countries (case-insensitive)
            country_name_map = {}
            for country in agg["country"].unique():
                country_lower = str(country).lower().strip()
                for unique_country in unique_countries:
                    if country_lower == unique_country.lower().strip():
                        country_name_map[country] = unique_country
                        break
                # If no match, keep original
                if country not in country_name_map:
                    country_name_map[country] = country
            agg["country"] = agg["country"].map(country_name_map).fillna(agg["country"])
        
        # Convert year to string for reindexing
        agg["year"] = agg["year"].astype(str)
        agg_complete = (
            agg.set_index(["year", "stream", "country"])
            .reindex(complete_index, fill_value=0)
            .reset_index()
        )
    else:
        # If agg is empty, create agg_complete directly from complete_index
        agg_complete = pd.DataFrame(list(complete_index), columns=["year", "stream", "country"])
        agg_complete["value"] = 0
    
    # Create a separate bar series for each country-stream combination
    # This ensures each combination stacks separately in the chart
    for stream in available_streams:
        # Get color for this stream
        stream_color = STREAM_COLOR_MAP.get(stream)
        if not stream_color:
            stream_color = FALLBACK_COLORS[fallback_idx % len(FALLBACK_COLORS)]
            fallback_idx += 1
        
        # Create a series for each country with this stream
        for country in unique_countries:
            country_stream_df = agg_complete[
                (agg_complete["stream"] == stream) & 
                (agg_complete["country"] == country)
            ]
            
            # Only skip if truly empty (shouldn't happen after reindex, but safety check)
            if country_stream_df.empty:
                continue
            
            # Check if this country-stream combination has any non-zero data
            # If all values are 0, skip this combination
            if country_stream_df["value"].sum() == 0:
                continue
            
            # Create unique bar series name for each country-stream combination
            # This ensures each combination is a separate series that stacks
            # Use format that includes both country and stream for uniqueness
            bar_name = f"{country} - {stream}"
            
            fig.add_bar(
                x=country_stream_df["year"],
                y=country_stream_df["value"],
                name=bar_name,
                marker_color=stream_color,
                hovertemplate=(
                    "<span style='color:#1b365d; font-weight:300;'>Country:</span> "
                    f"<span style='color:#1b365d; font-weight:700;'>{country}</span><br>"
                    "<span style='color:#1b365d; font-weight:300;'>Year:</span> "
                    "<span style='color:#1b365d; font-weight:700;'>%{x}</span><br>"
                    "<span style='color:#1b365d; font-weight:300;'>Exports Volume:</span> "
                    "<span style='color:#1b365d; font-weight:700;'>%{y:,.0f} '000 b/d</span>"
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
                        "Crude Exports",
                        style={
                            "marginBottom": "20px",
                            "color": "#fe5000",
                            "textAlign": "center",
                            "fontSize": "21px",
                            "fontWeight": "bold",
                        },
                    ),
                ]
            ),
            html.Div(
                [
                    html.Div(
                        [
                            # html.Div(
                            #     id="global-exports-map-title",
                            #     children=f"Crude Exports — {DEFAULT_YEAR or 'N/A'}",
                            #     style={
                            #         "fontWeight": "bold",
                            #         "color": "#1b365d",
                            #         "marginBottom": "10px",
                            #     },
                            # ),
                            dcc.Graph(
                                id="global-exports-map",
                                config={
                                    "displayModeBar": True,
                                    "displaylogo": False,
                                    "modeBarButtonsToAdd": [
                                        "zoomInGeo",
                                        "zoomOutGeo",
                                        "resetGeo",
                                        "resetScale2d",
                                    ],
                                    "scrollZoom": True,
                                    "doubleClick": "reset",
                                },
                                figure=_build_map_figure(
                                    DEFAULT_YEAR,
                                    "Russia" if "Russia" in COUNTRY_OPTIONS else None,
                                ),
                                style={"height": "520px", "width": "100%"},
                            ),
                    html.Div(
                        [
                            html.Div(
                                "Export Volume (‘000 b/d)",
                                style={
                                    "fontWeight": "bold",
                                    "fontSize": "12px",
                                    "color": "#1b365d",
                                    "marginTop": "12px",
                                },
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        style={
                                            "backgroundColor": color,
                                            "width": "18px",
                                            "height": "14px",
                                        }
                                    )
                                    for color in MAP_COLOR_SCALE
                                ],
                                style={
                                    "display": "flex",
                                    "gap": "1px",
                                    "marginTop": "4px",
                                    "border": "1px solid #cdd3dd",
                                    "padding": "2px",
                                    "backgroundColor": "#f2f4f8",
                                    "width": f"{COLOR_LEGEND_WIDTH}px",
                                },
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        "0",
                                        style={
                                            "fontSize": "11px",
                                            "color": "#1b365d",
                                            "fontWeight": "bold",
                                        },
                                    ),
                                    html.Span(
                                        MAP_VALUE_MAX_LABEL,
                                        style={
                                            "fontSize": "11px",
                                            "color": "#1b365d",
                                            "fontWeight": "bold",
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "justifyContent": "space-between",
                                    "marginTop": "2px",
                                    "width": f"{COLOR_LEGEND_WIDTH}px",
                                },
                            ),
                        ],
                        style={"marginTop": "10px"},
                    ),
                        ],
                        className="col-md-9",
                        style={"padding": "10px 5px 10px 10px"},
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
                                        "◄◄",
                                        id="global-exports-year-first",
                                        n_clicks=0,
                                        style={
                                            "width": "32px",
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
                                    html.Button(
                                        "▶▶",
                                        id="global-exports-year-last",
                                        n_clicks=0,
                                        style={
                                            "width": "32px",
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
                                    "gap": "4px",
                                },
                            ),
                            html.Div(
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
                                className="global-exports-slider-wrapper",
                                style={"paddingLeft": "0px"},
                            ),
                            html.Div(
                                [
                                    html.Button(
                                        "◀",
                                        id="global-exports-year-reverse",
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
                                    html.Button(
                                        "⏹",
                                        id="global-exports-year-stop",
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
                                    html.Button(
                                        "▶",
                                        id="global-exports-year-play",
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
                                    "gap": "6px",
                                    "marginBottom": "10px",
                                },
                            ),
                            html.Div(
                                id="global-exports-year-display",
                                children=year_display_value,
                                style={"display": "none"},
                            ),
                            html.Br(),
                            html.Label(
                                "Country",
                                style={
                                    "fontWeight": "bold",
                                    "color": "#2c3e50",
                                    "fontSize": "13px",
                                    "marginBottom": "5px",
                                },
                            ),
                            html.Div(
                                dcc.Checklist(
                                    id="global-exports-country-filter",
                                    options=_country_filter_options(COUNTRY_OPTIONS),
                                    value=["Russia"] if "Russia" in COUNTRY_OPTIONS else [],
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
                                        "fontSize": "12px",
                                    },
                                    inputStyle={
                                        "marginRight": "8px",
                                        "width": "16px",
                                        "height": "16px",
                                        "cursor": "pointer",
                                    },
                                ),
                                style={
                                    "marginBottom": "20px",
                                    "maxHeight": "300px",
                                    "overflowY": "auto",
                                    "border": "1px solid rgb(221, 221, 221)",
                                    "borderRadius": "4px",
                                    "padding": "10px",
                                    "backgroundColor": "rgb(249, 249, 249)",
                                },
                            ),
                        ],
                        className="col-md-3",
                        style={"padding": "10px"},
                    ),
                ],
                className="row",
            ),
            dcc.Interval(
                id="global-exports-year-interval",
                interval=1500,
                n_intervals=0,
                disabled=True,
            ),
            dcc.Store(id="global-exports-play-direction", data="stop"),
            html.Div(
                [
                    html.Div(
                        [
                            html.H4(
                                id="global-exports-chart-title",
                                children="Russia Annual Exports by Crude Stream",
                                style={
                                    "color": "#fe5000",
                                    "textAlign": "center",
                                    "fontWeight": "bold",
                                    "fontSize": "19px",
                                },
                            ),
                            dcc.Graph(
                                id="global-exports-stream-chart",
                                figure=_build_chart_figure(STREAM_ORDER, ["Russia"]),
                            ),
                        ],
                        className="col-md-9",
                        style={"padding": "15px"},
                    ),
                    html.Div(
                        [
                            dcc.Checklist(
                                id="global-exports-stream-filter",
                                options=_stream_filter_options(STREAM_ORDER),
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
                            "color": "#fe5000",
                            "textAlign": "center",
                            "fontWeight": "bold",
                            "fontSize": "19px",
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
        Input("global-exports-year-first", "n_clicks"),
        Input("global-exports-year-last", "n_clicks"),
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
        first_clicks,
        last_clicks,
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
        elif trigger_id == "global-exports-year-first":
            new_year = min_year
        elif trigger_id == "global-exports-year-last":
            new_year = max_year
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
        Input("global-exports-country-filter", "value"),
    )
    def update_map(
        submenu: str,
        year_str: Optional[str],
        country_value: Optional[Sequence[str]],
    ):
        """Update the map when the submenu or year changes."""
        if submenu != "global-exports":
            return _empty_figure(""), no_update
        year_value = _parse_year_value(year_str)
        normalized_year = _normalize_year(year_value)
        if country_value:
            if "ALL" in country_value:
                highlight = None
            else:
                highlight = country_value[0] if len(country_value) == 1 else None
        else:
            highlight = "Russia" if "Russia" in COUNTRY_OPTIONS else None
        title = f"Crude Exports — {normalized_year or 'N/A'}"
        return _build_map_figure(normalized_year, highlight), title

    @callback(
        Output("global-exports-country-filter", "value", allow_duplicate=True),
        Input("global-exports-map", "clickData"),
        State("global-exports-country-filter", "value"),
        prevent_initial_call=True,
    )
    def update_country_from_map(click_data, current_value):
        """Sync checklist selection when clicking map."""
        if not click_data or not click_data.get("points"):
            return dash.no_update
        country = click_data["points"][0].get("location") or click_data["points"][0].get("text")
        if not country:
            return dash.no_update
        if country not in COUNTRY_OPTIONS:
            return dash.no_update
        current_list = current_value if isinstance(current_value, list) else (
            [current_value] if current_value else []
        )
        if country in current_list:
            return dash.no_update
        # If "ALL" is currently selected, replace it with the clicked country
        if "ALL" in current_list:
            return [country]
        return current_list + [country]

    @callback(
        Output("global-exports-country-filter", "value", allow_duplicate=True),
        Input("global-exports-country-filter", "value"),
        prevent_initial_call=True,
    )
    def normalize_country_filter(value: Optional[Sequence[str]]):
        """
        Ensure 'ALL' behaves as a true 'select all':
        - If 'ALL' is selected, clear any other countries so the value becomes ['ALL'].
        """
        if not value:
            return dash.no_update
        # If ALL is present with others, reduce to just ALL
        if isinstance(value, (list, tuple)) and "ALL" in value:
            if len(value) == 1 and value[0] == "ALL":
                return dash.no_update
            return ["ALL"]
        return dash.no_update

    @callback(
        Output("global-exports-stream-filter", "options"),
        Output("global-exports-stream-filter", "value", allow_duplicate=True),
        Input("current-submenu", "data"),
        Input("global-exports-country-filter", "value"),
        State("global-exports-stream-filter", "value"),
        # Run on initial load, but still allow duplicate output updates safely.
        prevent_initial_call="initial_duplicate",
    )
    def sync_stream_filter_options(
        submenu: str,
        countries: Optional[Sequence[str]],
        current_value: Optional[Sequence[str]],
    ):
        """
        Keep the crude stream filter in sync with the selected countries.

        - When countries change, recompute the list of available streams for those countries.
        - All available streams are selected by default (so the chart and table show full data).
        - If the current selection is still valid, preserve it.
        """
        if submenu != "global-exports":
            return no_update, no_update

        available_streams = _streams_for_countries(countries)
        if not available_streams:
            # Fallback to global list
            available_streams = STREAM_ORDER

        # For each country selection change, always show all available crudes as checked.
        # This matches the Tableau behaviour: the filter list updates and everything is
        # selected by default for the chosen countries.
        new_value = available_streams

        return _stream_filter_options(available_streams), new_value

    @callback(
        Output("global-exports-stream-chart", "figure"),
        Output("global-exports-chart-title", "children"),
        Input("current-submenu", "data"),
        Input("global-exports-stream-filter", "value"),
        Input("global-exports-country-filter", "value"),
    )
    def update_chart(
        submenu: str,
        streams: Optional[Sequence[str]],
        countries: Optional[Sequence[str]],
    ):
        """Update stacked area chart."""
        if submenu != "global-exports":
            return _empty_figure(""), no_update
        fig = _build_chart_figure(streams, countries)
        # Update title based on selected countries
        if countries:
            if "ALL" in countries:
                title = "All Countries Annual Exports by Crude Stream"
            elif len(countries) == 1:
                title = f"{countries[0]} Annual Exports by Crude Stream"
            else:
                # Join country names with commas
                country_names = ", ".join(countries)
                title = f"{country_names} Annual Exports by Crude Stream"
        else:
            title = "Russia Annual Exports by Crude Stream"
        return fig, title

    @callback(
        Output("global-exports-stream-filter", "value", allow_duplicate=True),
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
        Input("global-exports-stream-filter", "value"),
    )
    def update_table(
        submenu: str,
        year_str: Optional[str],
        stream_filter_state: Optional[Sequence[str]],
    ):
        """Update table data."""
        if submenu != "global-exports":
            return []
        year_value = _parse_year_value(year_str)
        # By default, show all countries (no country filter)
        filtered = _filter_table_data(year_value, None)
        # When streams are filtered (not all streams selected), filter by selected streams
        # This automatically shows only countries that have data for those streams
        if stream_filter_state:
            # Check if all streams are selected (default state)
            all_streams_selected = (
                set(stream_filter_state) == set(STREAM_ORDER)
                if isinstance(stream_filter_state, (list, tuple))
                else False
            )
            # Only filter if not all streams are selected (user has filtered)
            if not all_streams_selected:
                filtered = filtered[filtered["crude"].isin(stream_filter_state)]
        return _prepare_table_records(filtered)

    @callback(
        Output("global-exports-play-direction", "data"),
        Input("global-exports-year-play", "n_clicks"),
        Input("global-exports-year-stop", "n_clicks"),
        Input("global-exports-year-reverse", "n_clicks"),
        prevent_initial_call=True,
    )
    def update_play_direction(play_clicks, stop_clicks, reverse_clicks):
        """Set play direction for year animation."""
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]
        if trigger == "global-exports-year-play":
            return "forward"
        if trigger == "global-exports-year-reverse":
            return "reverse"
        return "stop"

    @callback(
        Output("global-exports-year-interval", "disabled"),
        Input("global-exports-play-direction", "data"),
    )
    def toggle_year_interval(direction):
        """Enable or disable animation interval."""
        return direction == "stop"

    @callback(
        Output("global-exports-year-slider", "value", allow_duplicate=True),
        Output("global-exports-year-input", "value", allow_duplicate=True),
        Output("global-exports-year-display", "children", allow_duplicate=True),
        Input("global-exports-year-interval", "n_intervals"),
        State("global-exports-play-direction", "data"),
        State("global-exports-year-display", "children"),
        State("global-exports-year-slider", "min"),
        State("global-exports-year-slider", "max"),
        prevent_initial_call=True,
    )
    def animate_year(
        interval_count,
        direction,
        current_year,
        min_year,
        max_year,
    ):
        """Advance or reverse year based on play direction."""
        del interval_count
        if direction not in {"forward", "reverse"}:
            return dash.no_update, dash.no_update, dash.no_update
        min_year = min_year or YEAR_MIN
        max_year = max_year or YEAR_MAX
        try:
            current_year_int = int(current_year) if current_year else max_year
        except (TypeError, ValueError):
            current_year_int = max_year
        if direction == "forward":
            new_year = current_year_int + 1
            if new_year > max_year:
                new_year = min_year
        else:
            new_year = current_year_int - 1
            if new_year < min_year:
                new_year = max_year
        return new_year, new_year, str(new_year)

