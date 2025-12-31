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


def _read_csv(path: str) -> pd.DataFrame:
    """Read a CSV file and trim column names."""
    try:
        df = pd.read_csv(path)
        df.columns = df.columns.str.strip()
        return df
    except Exception:  # pragma: no cover - defensive logging
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
    FROM fact_wcod_country AS fwc
    LEFT JOIN dim_country AS dc
        ON dc.dim_country_id = fwc.country_id
    """
    
    try:
        results = execute_query(query)
        if not results:
            return pd.DataFrame()
        df = pd.DataFrame(results)
    except Exception:  # pragma: no cover - defensive logging
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
    """Load and normalize stacked area chart data from database."""
    query = """
    SELECT 
        -- Static columns
        'Source: Energy Intelligence' AS "Source",
        'COPYRIGHT &copy; 2001-2021 ENERGY INTELLIGENCE GROUP, INC. / ENERGY INTELLIGENCE GROUP (UK) LIMITED.'
            AS "Copyright",
        EXTRACT(YEAR FROM yr) AS "Year of Year",
        country_name AS "Country",	
        crude_name AS "Crude",  
        exports_kbpd AS "Avg. Value"
    FROM fact_wcod_crude
    """
    
    try:
        results = execute_query(query)
        if not results:
            return pd.DataFrame()
        df = pd.DataFrame(results)
    except Exception:  # pragma: no cover - defensive logging
        return pd.DataFrame()
    
    if df.empty:
        return df
    
    df.columns = df.columns.str.strip()
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
    """Load and normalize table data from database."""
    query = """
    SELECT 
        country_name AS "Country",	
        crude_name AS "Crude",  
        -- Static columns
        'Source: Energy Intelligence' AS "Source",
        'COPYRIGHT &copy; 2001-2021 ENERGY INTELLIGENCE GROUP, INC. / ENERGY INTELLIGENCE GROUP (UK) LIMITED.'
            AS "Copyright",
        EXTRACT(YEAR FROM yr) AS "Year of Year",    
        exports_kbpd AS "Value"
    FROM fact_wcod_crude
    """
    
    try:
        results = execute_query(query)
        if not results:
            return pd.DataFrame()
        df = pd.DataFrame(results)
    except Exception:  # pragma: no cover - defensive logging
        return pd.DataFrame()
    
    if df.empty:
        return df
    
    df.columns = df.columns.str.strip()
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
    ["Russia"] if "Russia" in COUNTRY_OPTIONS else (COUNTRY_OPTIONS[0] if COUNTRY_OPTIONS else [])
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
    """Create checklist options for countries with (All) option first."""
    options: List[Dict[str, str]] = [
        {"label": "(All)", "value": "(All)"}
    ] + [
        {"label": country, "value": country}
        for country in country_names
    ]
    return options


def _resolve_countries(selected: Optional[Sequence[str]], all_countries: Sequence[str]) -> List[str]:
    """Return concrete country list honoring '(All)' convenience value."""
    if not selected:
        return []
    if not all_countries:
        return []
    if "(All)" in selected:
        return list(all_countries)
    return [c for c in selected if c in all_countries]


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
                        "marginRight": "5px",
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
                        "fontWeight": "normal",
                        "fontSize": "12px",
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

    - If no countries are selected or "(All)" is included, use all countries.
    - Order:
        1. Streams in STREAM_ORDER that appear in the data.
        2. Any additional streams for those countries, sorted alphabetically.
    """
    if CHART_DF.empty:
        return STREAM_ORDER

    df = CHART_DF.copy()
    # Handle empty selection (when "(All)" is unselected)
    if selected_countries is not None and isinstance(selected_countries, list) and len(selected_countries) == 0:
        # Empty selection - return empty list (no streams available)
        return []
    
    if "country" in df.columns and selected_countries:
        # Resolve (All) to actual country list
        all_countries_in_data = df["country"].str.strip().unique()
        available_countries = sorted([c for c in all_countries_in_data if pd.notna(c)])
        resolved_countries = _resolve_countries(selected_countries, available_countries)
        
        if resolved_countries:
            selected_lower = [c.lower() for c in resolved_countries]
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
    """
    Filter table data by year and countries.
    
    Note: The year parameter is accepted for API consistency but the table shows
    all years in columns. Only country filtering is applied when countries is provided.
    When countries is None, all countries are returned.
    """
    if TABLE_DF.empty:
        return pd.DataFrame(columns=["country", "crude", "year", "value"])
    df = TABLE_DF.copy()
    # Only filter by countries if explicitly provided (not None)
    # When countries is None, return all countries
    if countries is not None:
        if isinstance(countries, str):
            countries = [countries]
        if countries:  # Only filter if list is not empty
            df = df[df["country"].isin(countries)]
    # Note: year parameter is not used - table shows all years in columns
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


def _build_map_figure(
    year: Optional[int], 
    highlight_country: Optional[str] = None,
    selected_countries: Optional[Sequence[str]] = None
) -> go.Figure:
    if MAP_DF.empty:
        return _empty_figure("No map data available")
    normalized_year = _normalize_year(year)
    df = MAP_DF[MAP_DF["year"] == normalized_year].copy()
    if df.empty:
        return _empty_figure("No data for the selected year")
    
    # Filter by selected countries if provided
    # Note: selected_countries is already resolved (no "(All)" in it)
    # None = show all countries, [] = show no countries, [list] = show specific countries
    if selected_countries is not None and "country" in df.columns:
        if isinstance(selected_countries, list) and len(selected_countries) == 0:
            # Empty list means no countries selected - return empty figure
            return _empty_figure("No countries selected")
        elif selected_countries:
            # Filter df by matching countries (case-insensitive)
            df_countries_normalized = df["country"].str.strip().str.lower()
            target_countries_normalized = {c.lower().strip(): c for c in selected_countries}
            mask = df_countries_normalized.isin(target_countries_normalized.keys())
            df = df[mask].copy()
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
        # Adjust projection to fill more of the available space
        projection=dict(
            scale=1.15,  # Scale up to reduce blank space around the map
        ),
    )
    fig.update_layout(
        height=520,
        paper_bgcolor="white",
        plot_bgcolor="white",
        # Reduce margins to minimize blank space - keep bottom margin for legend
        margin=dict(l=0, r=0, t=5, b=5),  # Minimal margins
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
    # Handle empty selection (when "(All)" is unselected)
    if selected_countries is not None and isinstance(selected_countries, list) and len(selected_countries) == 0:
        return _empty_figure("No countries selected")
    
    # First, determine which countries to include (before filtering by streams)
    # Note: selected_countries is already resolved (no "(All)" in it) from the callback
    # None means show all countries (optimization: skip country filtering), empty list means show no countries, list means show those countries
    filter_by_countries = False
    if selected_countries is not None and len(selected_countries) > 0:
        # Match resolved countries with data country names (case-insensitive)
        target_countries = []
        if "country" in CHART_DF.columns:
            all_countries_in_data = CHART_DF["country"].str.strip().unique()
            data_countries_lower = {c.lower(): c for c in all_countries_in_data if pd.notna(c)}
            
            # Match each resolved country with data country names (case-insensitive)
            for selected in selected_countries:
                selected_lower = str(selected).lower().strip()
                if selected_lower in data_countries_lower:
                    # Use the exact name from data
                    target_countries.append(data_countries_lower[selected_lower])
                else:
                    # If not found in data, still include the selected name
                    # (it might have data, or will show as 0)
                    target_countries.append(selected)
        else:
            # No country column in data, use resolved countries as-is
            target_countries = list(selected_countries)
        target_countries = sorted(set(target_countries))
        filter_by_countries = True
    else:
        # None means all countries - optimize by skipping country filtering
        # This avoids expensive filtering operations when showing all countries
        target_countries = []
        filter_by_countries = False
    
    # Now filter by streams and years (always needed)
    df = CHART_DF[
        (CHART_DF["year"].between(2006, 2024))
        & (CHART_DF["stream"].isin(streams))
    ].copy()
    
    # Filter by selected countries only if needed (optimization for "All" selection)
    if filter_by_countries and "country" in df.columns and target_countries:
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
    
    if df.empty:
        return _empty_figure("No data in the selected range")
    
    # Determine country label for display
    if filter_by_countries and target_countries:
        if len(target_countries) == 1:
            country_label = target_countries[0]
        elif len(target_countries) > 1:
            country_label = f"{len(target_countries)} Countries"
        else:
            country_label = "All Countries"
    else:
        country_label = "All Countries"
    # Group by year, stream, and country to keep each country-crude combination separate
    if not df.empty:
        if "country" in df.columns:
            agg = df.groupby(["year", "stream", "country"])["value"].sum().reset_index()
            # Ensure country names match target_countries exactly (case-insensitive match)
            # Only do this if we're filtering by countries (optimization for "All" selection)
            if filter_by_countries and target_countries:
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
    
    # Get unique countries - OPTIMIZATION: Only include countries that actually have data
    # This significantly reduces the number of combinations when "All" is selected
    if not agg.empty and "country" in agg.columns:
        # Only use countries that have data (filter out zero-only combinations early)
        countries_with_data = sorted(agg[agg["value"] > 0]["country"].unique().tolist())
        if target_countries:
            # If specific countries were selected, ensure they're included even if no data
            # But prioritize countries with actual data
            unique_countries = sorted(set(countries_with_data + target_countries))
        else:
            # When "All" is selected, only show countries that have data (major optimization)
            unique_countries = countries_with_data
    elif target_countries:
        unique_countries = sorted(target_countries)
    elif "country" in df.columns and not df.empty:
        unique_countries = sorted(df["country"].unique().tolist())
    else:
        unique_countries = [country_label]
    
    # Early exit if no countries with data
    if not unique_countries:
        return _empty_figure("No data for selected countries")
    
    # OPTIMIZATION: Pre-filter agg to only countries with data before creating complete index
    # This reduces the size of the complete_index significantly
    if not agg.empty and "country" in agg.columns:
        agg_filtered = agg[agg["country"].isin(unique_countries)].copy()
    else:
        agg_filtered = agg.copy()
    
    # Create a complete index only for countries that have data
    # This is much smaller than including all countries
    complete_index = pd.MultiIndex.from_product(
        (YEAR_AXIS_FULL, available_streams, unique_countries),
        names=["year", "stream", "country"]
    )
    
    # Prepare agg for reindexing - OPTIMIZED: work with filtered data
    if not agg_filtered.empty:
        # Convert year to string for reindexing
        agg_filtered["year"] = agg_filtered["year"].astype(str)
        agg_complete = (
            agg_filtered.set_index(["year", "stream", "country"])
            .reindex(complete_index, fill_value=0)
            .reset_index()
        )
    else:
        # If agg is empty, create agg_complete directly from complete_index
        agg_complete = pd.DataFrame(list(complete_index), columns=["year", "stream", "country"])
        agg_complete["value"] = 0
    
    # OPTIMIZATION: Pre-filter to only non-zero combinations before the loop
    # This avoids processing thousands of zero-value combinations
    non_zero_mask = agg_complete["value"] > 0
    if non_zero_mask.any():
        agg_non_zero = agg_complete[non_zero_mask].copy()
        # Get unique combinations that have data
        valid_combinations = agg_non_zero[["stream", "country"]].drop_duplicates()
    else:
        valid_combinations = pd.DataFrame(columns=["stream", "country"])
    
    # OPTIMIZATION: Pre-create year array as string to avoid repeated conversion
    years_sorted_str = [str(y) for y in years_sorted]
    
    # Create a separate bar series for each country-stream combination
    # OPTIMIZATION: Only iterate through combinations that have data
    for stream in available_streams:
        # Get color for this stream
        stream_color = STREAM_COLOR_MAP.get(stream)
        if not stream_color:
            stream_color = FALLBACK_COLORS[fallback_idx % len(FALLBACK_COLORS)]
            fallback_idx += 1
        
        # Get countries for this stream that have data
        stream_countries = valid_combinations[valid_combinations["stream"] == stream]["country"].unique()
        
        # Create a series for each country with this stream that has data
        for country in stream_countries:
            # Filter efficiently using vectorized operations
            mask = (agg_complete["stream"] == stream) & (agg_complete["country"] == country)
            country_stream_df = agg_complete[mask].copy()
            
            # Should not be empty due to our filtering, but safety check
            if country_stream_df.empty:
                continue
            
            # OPTIMIZATION: agg_complete already has all years from reindex, so no need to check/add missing years
            # Just ensure years are in the correct order (matching years_sorted_str)
            # Since reindex already filled missing years with 0, we just need to sort
            country_stream_df = country_stream_df.sort_values("year")
            
            # Create unique bar series name for each country-stream combination
            bar_name = f"{country} - {stream}"
            
            fig.add_bar(
                x=country_stream_df["year"].tolist(),
                y=country_stream_df["value"].tolist(),
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
    
    # Add a hidden trace with all years to ensure all year labels appear on X-axis
    # This ensures that even if some years have no data, they still appear on the axis
    # The trace is invisible (transparent) and won't affect the chart appearance
    # Add it first so Plotly knows all categories from the start
    fig.add_bar(
        x=years_sorted,
        y=[0] * len(years_sorted),
        name="_hidden_all_years",
        marker_color="rgba(0,0,0,0)",  # Transparent
        showlegend=False,
        hoverinfo="skip",
    )
    
    fig.update_layout(
        height=460,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=90, r=20, t=40, b=40),  # Increased left margin to accommodate Y-axis title and labels
        barmode="stack",
        showlegend=False,
        xaxis=dict(
            title="",
            type="category",  # Use category type to ensure all categories are shown
            categoryorder="array",
            categoryarray=years_sorted,
            tickvals=years_sorted,  # Explicitly set all tick positions
            ticktext=years_sorted,  # Explicitly set all tick labels
        ),
        yaxis=dict(
            title="Export Volume ('000 b/d)",
            separatethousands=True,
            titlefont=dict(size=12),
            tickfont=dict(size=10),
        ),
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
            # Download components
            dcc.Download(id="download-global-exports-map-csv"),
            dcc.Download(id="download-russia-exports-csv"),
            dcc.Download(id="download-annual-exports-csv"),
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
                    html.Div([
                        html.H3(
                            "Crude Exports",
                            style={
                                "marginBottom": "20px",
                                "color": "#fe5000",
                                "textAlign": "center",
                                "fontSize": "21px",
                                "fontWeight": "bold",
                                "flex": "1"
                            },
                        ),
                        html.Button(
                            "Export CSV",
                            id='export-global-exports-map-btn',
                            n_clicks=0,
                            style={
                                'backgroundColor': 'white',
                                'color': '#2c3e50',
                                'border': '1px solid #dee2e6',
                                'padding': '6px 12px',
                                'borderRadius': '4px',
                                'cursor': 'pointer',
                                'fontSize': '12px',
                                'fontWeight': 'normal'
                            }
                        )
                    ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'gap': '20px'}),
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
                            dcc.Loading(
                                id="loading-map",
                                type="default",
                                color="#fe5000",
                                children=[
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
                                            None,
                                        ),
                                        style={"height": "520px", "width": "100%"},
                                    ),
                                ],
                                style={"height": "520px"},
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
                        style={"padding": "10px 5px 10px 10px", "maxWidth": "100%", "boxSizing": "border-box"},
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
                                    value=DEFAULT_COUNTRY,
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
                        style={"padding": "10px", "maxWidth": "100%", "boxSizing": "border-box"},
                    ),
                ],
                className="row",
                style={"marginLeft": "0", "marginRight": "0", "width": "100%"},
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
                            html.Div([
                                html.H4(
                                    id="global-exports-chart-title",
                                    children="All Countries Annual Exports by Crude Stream",
                                    style={
                                        "color": "#fe5000",
                                        "textAlign": "center",
                                        "fontWeight": "bold",
                                        "fontSize": "19px",
                                        "flex": "1"
                                    },
                                ),
                                html.Button(
                                    "Export CSV",
                                    id='export-russia-exports-btn',
                                    n_clicks=0,
                                    style={
                                        'backgroundColor': 'white',
                                        'color': '#2c3e50',
                                        'border': '1px solid #dee2e6',
                                        'padding': '6px 12px',
                                        'borderRadius': '4px',
                                        'cursor': 'pointer',
                                        'fontSize': '12px',
                                        'fontWeight': 'normal'
                                    }
                                )
                            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'gap': '20px'}),
                            dcc.Loading(
                                id="loading-chart",
                                type="default",
                                color="#fe5000",
                                children=[
                                    dcc.Graph(
                                        id="global-exports-stream-chart",
                                    ),
                                ],
                            ),
                        ],
                        className="col-md-9",
                        style={"padding": "10px", "maxWidth": "100%", "boxSizing": "border-box"},
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
                                    "fontSize": "12px",
                                },
                                inputStyle={
                                    "marginRight": "5px",
                                    "width": "16px",
                                    "height": "16px",
                                    "cursor": "pointer",
                                },
                            ),
                        ],
                        className="col-md-3",
                        style={
                            "padding": "25px 10px",
                            "border": "0px solid #dfe3eb",
                            "borderRadius": "6px",
                            "backgroundColor": "#f8f9fb",
                            "height": "100%",
                            "maxHeight": "520px",
                            "overflowY": "auto",
                            "boxShadow": "0 2px 6px rgba(0,0,0,0.05)",
                            "marginLeft": "0",
                            "maxWidth": "100%",
                            "boxSizing": "border-box",
                        },
                    ),
                ],
                className="row",
                style={"marginTop": "30px", "marginLeft": "0", "marginRight": "0", "width": "100%"},
            ),
            html.Div(
                [
                    html.Div([
                        html.H4(
                            "Annual Exports Volume (‘000 b/d)",
                            style={
                                "color": "#fe5000",
                                "fontWeight": "bold",
                                "fontSize": "19px",
                                "margin": "0"
                            },
                        ),                    
                        html.Button(
                            "Export CSV",
                            id='export-annual-exports-btn',
                            n_clicks=0,
                            style={
                                'backgroundColor': 'white',
                                'color': '#2c3e50',
                                'border': '1px solid #dee2e6',
                                'padding': '6px 12px',
                                'borderRadius': '4px',
                                'cursor': 'pointer',
                                'fontSize': '12px',
                                'fontWeight': 'normal'
                            }
                        )
                    ], style={
                        'display': 'flex', 
                        'justifyContent': 'space-between', 
                        'alignItems': 'center', 
                        'width': '100%',
                        'marginTop': '30px',
                        'marginBottom': '10px'
                    }),
                    dcc.Loading(
                        id="loading-table",
                        type="default",
                        color="#fe5000",
                        children=[
                            dash_table.DataTable(
                                id="global-exports-table",
                                columns=TABLE_COLUMNS,
                                data=[],
                                sort_action="native",
                                page_action="none",
                                style_table={
                                    "overflowX": "auto",
                                    "overflowY": "auto",
                                    "backgroundColor": "white",
                                    "maxHeight": "520px",
                                    "border": "1px solid #e6e9ef",
                                    "width": "100%",
                                    "maxWidth": "100%",
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
                    ),
                ],
                className="col-md-9",
                style={"padding": "10px"},
            ),
            html.P(
                "Source: Energy Intelligence.",
                style={"fontSize": "13px", "color": "#6c757d", "marginTop": "15px", "fontStyle": "italic", "fontWeight": "normal"},
            ),
            html.P(
                "Countries: Select jurisdictions are included under countries for data presentation purposes.",
                style={"fontSize": "11px", "color": "#6c757d", "marginTop": "5px", "fontStyle": "italic"},
            ),
        ],
        className="tab-content",
        style={
            "padding": "20px 10px",
            "backgroundColor": "#f8f9fa",
            "overflowX": "hidden",  # Prevent horizontal scrolling
            "width": "100%",
            "maxWidth": "100%",
            "boxSizing": "border-box",
        },
    )


def register_callbacks(dash_app, server):  # pylint: disable=unused-argument
    """Register callbacks for the Global Exports view."""
    
    @dash_app.callback(
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

    @dash_app.callback(
        Output("global-exports-map", "figure"),
        Input("current-submenu", "data"),
        Input("global-exports-year-display", "children"),
        Input("global-exports-country-filter", "value"),
        prevent_initial_call=False,
    )
    def update_map(
        submenu: str,
        year_str: Optional[str],
        country_value: Optional[Sequence[str]],
    ):
        """Update the map when the submenu or year changes."""
        try:
            if submenu != "global-exports":
                return _empty_figure("")
            year_value = _parse_year_value(year_str)
            normalized_year = _normalize_year(year_value)
            
            # On initial load, ignore country filter - show all countries
            # Check if country filter input triggered this callback
            ctx = dash.callback_context
            country_filter_triggered = False
            if ctx.triggered:
                for trigger in ctx.triggered:
                    if "global-exports-country-filter" in trigger.get("prop_id", ""):
                        country_filter_triggered = True
                        break
            
            # Resolve countries for filtering
            selected_countries = None
            highlight = None
            # Only apply country filter if it was explicitly changed by user
            # On initial load, ignore country filter to show all countries
            if not country_filter_triggered:
                # Show all countries on initial load or when filter wasn't changed
                selected_countries = None
            elif country_value is not None:
                # Handle empty list (when "(All)" is unselected)
                if isinstance(country_value, list) and len(country_value) == 0:
                    # Empty selection - show no countries
                    selected_countries = []
                else:
                    # Resolve countries (handles "(All)" option)
                    resolved_countries = _resolve_countries(country_value, COUNTRY_OPTIONS)
                    if len(resolved_countries) == 0:
                        # No countries matched - show empty
                        selected_countries = []
                    else:
                        selected_countries = resolved_countries
                        # Highlight if exactly one country is selected
                        if len(resolved_countries) == 1:
                            highlight = resolved_countries[0]
            
            return _build_map_figure(normalized_year, highlight, selected_countries)
        except Exception:
            return _empty_figure("Error loading map")

    @dash_app.callback(
        Output("global-exports-country-filter", "value", allow_duplicate=True),
        Input("global-exports-country-filter", "value"),
        State("global-exports-country-filter", "options"),
        prevent_initial_call=True,
    )
    def sync_country_all(selected: Optional[Sequence[str]], options: Optional[List[Dict[str, str]]]):
        """Ensure '(All)' behaves as a real select-all for dropdown."""
        if not options:
            return selected
        
        all_countries = [o["value"] for o in options if o["value"] != "(All)"]
        if not all_countries:
            return selected
        
        selected = selected or []
        selected_set = set(selected)
        has_all = "(All)" in selected_set
        all_set = set(all_countries)
        subset_set = selected_set - {"(All)"}

        # Rules (matching requirements exactly):
        # 1) "(All)" clicked alone => select all countries.
        # 2) "(All)" + subset:
        #    - If subset is nearly/all countries (>= len(all_set) - 1), user is deselecting while All was active
        #      -> drop "(All)" and honor subset
        #    - Otherwise (subset is smaller), user clicked "(All)" while individual countries were selected
        #      -> snap to full select-all (requirement: "When the user re-selects 'All': All individual countries must be selected again")
        # 3) If everything is selected but "(All)" is not present, treat as user unchecked All -> clear all.
        # 4) If nothing selected, keep empty.
        # 5) Otherwise, keep the chosen subset.
        if has_all and not subset_set:
            # Case 1: "(All)" clicked alone -> select all countries
            # This can happen when:
            # - User clicks "(All)" when nothing is selected
            # - User clicks "(All)" when individual countries are selected (checklist sends only "(All)")
            normalized = ["(All)"] + all_countries
        elif has_all and subset_set:
            # Case 2: "(All)" + some countries selected
            if len(all_set) > 0 and len(subset_set) >= len(all_set) - 1:
                # User is deselecting countries while All was active (nearly all still selected)
                # Drop "(All)" and honor the subset
                normalized = sorted(subset_set)
            else:
                # User clicked "(All)" while individual countries were already selected
                # Requirement: "When the user re-selects 'All': All individual countries must be selected again"
                # Snap to full select-all
                normalized = ["(All)"] + all_countries
        elif not has_all and subset_set == all_set and all_countries:
            # Case 3: All countries selected but "(All)" not present -> user unchecked All, clear all
            normalized = []
        elif not subset_set:
            # Case 4: Nothing selected
            normalized = []
        else:
            # Case 5: Some countries selected (not all) -> keep the chosen subset
            # This handles when user selects individual countries (no "(All)" in selection)
            # Requirement: "If a user selects any individual country while 'All' is active:
            # The 'All' option must automatically become unselected."
            # This is already handled - when user clicks individual country while All is active,
            # the checklist sends the individual country without "(All)", so we're in Case 5
            # 
            # IMPORTANT: When user clicks "(All)" while individual countries are selected,
            # the checklist sends ["(All)", ...individual countries...], which triggers Case 2.
            # But if the checklist only sends ["(All)"] (without individual countries), we need to handle it.
            # However, this should not happen in normal operation.
            normalized = sorted(subset_set)

        # Avoid loops - only return if value actually changed
        new_sorted = normalized
        old_sorted = sorted(selected)
        if new_sorted == old_sorted:
            return dash.no_update
        
        return new_sorted

    @dash_app.callback(
        Output("global-exports-country-filter", "value", allow_duplicate=True),
        Input("global-exports-map", "clickData"),
        State("global-exports-country-filter", "value"),
        State("global-exports-country-filter", "options"),
        prevent_initial_call=True,
    )
    def update_country_from_map(click_data, current_value, options):
        """Sync checklist selection when clicking map."""
        if not click_data or not click_data.get("points"):
            return dash.no_update
        
        # Get country name from click data
        point = click_data["points"][0]
        country = point.get("location") or point.get("text")
        if not country or not options:
            return dash.no_update
        
        # Extract all country options (excluding "(All)")
        all_country_options = [opt["value"] for opt in options if opt["value"] != "(All)"]
        if country not in all_country_options:
            return dash.no_update
        
        # Get current selection
        current_list = current_value if isinstance(current_value, list) else (
            [current_value] if current_value else []
        )
        
        # Resolve current selection to actual countries (handle "(All)")
        all_countries = all_country_options
        resolved_current = _resolve_countries(current_list, all_countries)
        selected_set = set(resolved_current)
        
        # Toggle the clicked country
        if country in selected_set:
            selected_set.remove(country)
        else:
            selected_set.add(country)
        
        # Build new values
        if not selected_set:
            new_values = []
        elif selected_set == set(all_countries):
            new_values = ["(All)"] + all_countries
        else:
            new_values = sorted(selected_set)
        
        return new_values

    @dash_app.callback(
        Output("global-exports-stream-filter", "options"),
        Output("global-exports-stream-filter", "value", allow_duplicate=True),
        Input("current-submenu", "data"),
        Input("global-exports-country-filter", "value"),
        State("global-exports-stream-filter", "value"),
        prevent_initial_call="initial_duplicate",
    )
    def sync_stream_filter_options(
        submenu: str,
        countries: Optional[Sequence[str]],
        current_value: Optional[Sequence[str]],
    ):
        """
        Keep the crude stream filter in sync with the selected countries.
        Always ensures all available streams are checked by default.
        """
        try:
            if submenu != "global-exports":
                return no_update, no_update

            # Handle empty country selection (when "(All)" is unselected)
            if countries is not None and isinstance(countries, list) and len(countries) == 0:
                # No countries selected - return empty options and empty value
                return _stream_filter_options([]), []

            # Get available streams for selected countries
            available_streams = _streams_for_countries(countries)
            
            # If no streams available (shouldn't happen unless data is empty or countries have no streams)
            if not available_streams:
                # Only fallback to global list if countries is None (initial load)
                # If countries is explicitly set but no streams found, return empty
                if countries is None:
                    available_streams = STREAM_ORDER if STREAM_ORDER else []
                else:
                    # Countries selected but no streams available - return empty
                    return _stream_filter_options([]), []
            
            if not available_streams:
                return no_update, no_update
            
            # Determine new value:
            # 1. If current_value is None or empty, select all available streams (default)
            # 2. If current_value has some streams but not all are valid, select all available streams
            # 3. If current_value has all valid streams, keep current selection
            # 4. Always default to all streams if selection is invalid or incomplete
            if current_value and len(current_value) > 0:
                # Check if all current streams are valid for the new country selection
                valid_streams = [s for s in current_value if s in available_streams]
                # If we have valid streams and it's a subset, keep them
                # But if country filter changed significantly, default to all
                if len(valid_streams) == len(current_value) and len(valid_streams) == len(available_streams):
                    # All current streams are valid and we have all available streams - keep selection
                    new_value = current_value
                else:
                    # Some streams are invalid or we don't have all streams - default to all
                    new_value = available_streams
            else:
                # No current selection - default to all available streams
                new_value = available_streams

            return _stream_filter_options(available_streams), new_value
        except Exception:
            return no_update, no_update

    @dash_app.callback(
        Output("global-exports-stream-chart", "figure"),
        Output("global-exports-chart-title", "children"),
        Input("current-submenu", "data"),
        Input("global-exports-stream-filter", "value"),
        Input("global-exports-country-filter", "value"),
        prevent_initial_call=False,
    )
    def update_chart(
        submenu: Optional[str],
        streams: Optional[Sequence[str]],
        countries: Optional[Sequence[str]],
    ):
        """Update stacked area chart."""
        # Default values
        default_title = "All Countries Annual Exports by Crude Stream"
        default_fig = _empty_figure("Loading chart...")
        
        try:
            # Check if we're on the right submenu
            if submenu != "global-exports":
                return default_fig, default_title
            
            # Handle streams - default to all streams if empty
            if not streams:
                streams = STREAM_ORDER if STREAM_ORDER else []
            if isinstance(streams, list) and len(streams) == 0:
                streams = STREAM_ORDER if STREAM_ORDER else []
            
            # Resolve countries (handle "(All)" option and empty selection)
            # Get available countries from chart data for proper resolution
            resolved_countries = None
            try:
                # Get countries available in chart data
                if not CHART_DF.empty and "country" in CHART_DF.columns:
                    available_countries_in_chart = sorted(
                        [c for c in CHART_DF["country"].str.strip().unique() if pd.notna(c)]
                    )
                else:
                    available_countries_in_chart = COUNTRY_OPTIONS if COUNTRY_OPTIONS else []
                
                # Handle country selection
                if countries is None:
                    # None means default - show all countries (for initial load)
                    resolved_countries = None
                elif isinstance(countries, list) and len(countries) == 0:
                    # Empty list means "(All)" was unselected - show no countries
                    resolved_countries = []
                elif countries and len(countries) > 0:
                    # Check if "(All)" is in the selection first (before resolving)
                    # This is important because when "(All)" is selected, we want to show all countries
                    if "(All)" in countries:
                        # "(All)" was selected - show all countries (optimization)
                        # Pass None to _build_chart_figure to skip country filtering
                        resolved_countries = None
                    else:
                        # Countries selected (without "(All)") - resolve them
                        if available_countries_in_chart:
                            resolved = _resolve_countries(countries, available_countries_in_chart)
                            # _resolve_countries always returns a list (never None)
                            # If resolved is empty list, it means no countries matched
                            if len(resolved) == 0:
                                # No countries match the selection, show empty (no data)
                                resolved_countries = []
                            else:
                                # We have resolved countries - use them
                                resolved_countries = resolved
                        else:
                            # No available countries in chart data - show empty
                            resolved_countries = []
            except Exception:
                resolved_countries = None
            
            # Build the figure
            try:
                if not streams or (isinstance(streams, list) and len(streams) == 0):
                    fig = _empty_figure("No streams selected")
                else:
                    # Pass resolved countries (or None if no selection)
                    # None = show all countries, [] = show no countries, [list] = show specific countries
                    fig = _build_chart_figure(streams, resolved_countries)
                    # Validate figure
                    if not isinstance(fig, go.Figure):
                        fig = _empty_figure("Invalid chart data")
            except Exception:
                fig = _empty_figure("Error loading chart data")
            
            # Generate title
            title = default_title
            try:
                if countries and COUNTRY_OPTIONS and len(COUNTRY_OPTIONS) > 0:
                    # Use resolved_countries from above if available, otherwise resolve again for title
                    if resolved_countries is not None and len(resolved_countries) > 0:
                        title_countries = resolved_countries
                    elif resolved_countries is None:
                        # All countries selected - use all for title
                        title_countries = COUNTRY_OPTIONS
                    else:
                        # Resolve for title generation
                        title_countries = _resolve_countries(countries, COUNTRY_OPTIONS)
                    
                    if len(title_countries) == 1:
                        title = f"{title_countries[0]} Annual Exports by Crude Stream"
                    elif len(title_countries) > 1:
                        if len(title_countries) <= 3:
                            country_names = ", ".join(title_countries)
                        else:
                            country_names = ", ".join(title_countries[:3]) + f" and {len(title_countries) - 3} more"
                        title = f"{country_names} Annual Exports by Crude Stream"
            except Exception:
                title = default_title
            
            # Final validation - ensure we always return valid types
            if not isinstance(fig, go.Figure):
                fig = default_fig
            if not isinstance(title, str) or not title:
                title = default_title
            
            # Double-check return values
            if not isinstance(fig, go.Figure):
                fig = _empty_figure("Error: Invalid figure type")
            if not isinstance(title, str):
                title = "All Countries Annual Exports by Crude Stream"
            
            return fig, title
            
        except Exception:
            # Always return valid values - this is critical
            try:
                error_fig = _empty_figure("Error loading chart")
                if not isinstance(error_fig, go.Figure):
                    error_fig = go.Figure()
                return error_fig, "All Countries Annual Exports by Crude Stream"
            except Exception:
                # Last resort - return minimal valid figure
                minimal_fig = go.Figure()
                minimal_fig.add_annotation(text="Error loading chart", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
                return minimal_fig, "All Countries Annual Exports by Crude Stream"

    @dash_app.callback(
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

    @dash_app.callback(
        Output("global-exports-table", "data"),
        Input("current-submenu", "data"),
        Input("global-exports-year-display", "children"),
        Input("global-exports-stream-filter", "value"),
        Input("global-exports-country-filter", "value"),
        Input({"type": "stream-isolate-button", "stream": ALL}, "n_clicks"),
        prevent_initial_call=False,
    )
    def update_table(
        submenu: str,
        year_str: Optional[str],
        stream_filter_state: Optional[Sequence[str]],
        country_filter: Optional[Sequence[str]],
        legend_clicks,
    ):
        """
        Update table data.
        
        Behavior:
        - Initial load: Show ALL data (no filters applied)
        - Legend click: Apply both country and stream filters
        - Other changes: Show ALL data (ignore filters)
        """
        try:
            if submenu != "global-exports":
                return []
            
            year_value = _parse_year_value(year_str)
            
            # Check if legend button was clicked (user interaction)
            ctx = dash.callback_context
            
            # Check if this is truly an initial call (no triggers at all)
            is_initial_call = not ctx.triggered or len(ctx.triggered) == 0
            
            # Check for legend button clicks - must check actual n_clicks values
            legend_clicked = False
            if ctx.triggered and not is_initial_call and legend_clicks:
                # Check if any legend button has n_clicks > 0 (actual click)
                # legend_clicks is a list of n_clicks values for all legend buttons
                for clicks in legend_clicks:
                    if clicks is not None and clicks > 0:
                        legend_clicked = True
                        break
            
            # IMPORTANT: On initial load, show ALL data (no filters applied)
            if is_initial_call or not legend_clicked:
                if TABLE_DF.empty:
                    return []
                return _prepare_table_records(TABLE_DF.copy())
            
            # Legend was clicked - apply both country and stream filters
            
            if TABLE_DF.empty:
                return []
            
            # Check if stream filter contains all streams (reset state)
            # If all streams are selected, treat it as "no filter" and show all data
            if stream_filter_state and not TABLE_DF.empty:
                all_available_streams = set(TABLE_DF["crude"].unique())
                stream_filter_set = set(stream_filter_state)
                if stream_filter_set == all_available_streams:
                    # All streams selected - show all data
                    return _prepare_table_records(TABLE_DF.copy())
            
            # Start with all data
            filtered = TABLE_DF.copy()
            
            # Apply country filter
            if country_filter is not None:
                try:
                    resolved = _resolve_countries(country_filter, COUNTRY_OPTIONS)
                    if "(All)" in country_filter:
                        # Show all countries
                        pass
                    elif resolved and len(resolved) > 0:
                        filtered = filtered[filtered["country"].isin(resolved)]
                    else:
                        # Empty selection - show no countries
                        return []
                except Exception:
                    # Error resolving countries - show all data
                    pass
            
            # Apply stream filter (we know it's not all streams from the check above)
            if stream_filter_state:
                try:
                    filtered = filtered[filtered["crude"].isin(stream_filter_state)]
                except Exception:
                    # Error filtering by streams - continue with current filtered data
                    pass
            
            return _prepare_table_records(filtered)
        except Exception:
            # Return empty on any error
            return []

    @dash_app.callback(
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

    @dash_app.callback(
        Output("global-exports-year-interval", "disabled"),
        Input("global-exports-play-direction", "data"),
    )
    def toggle_year_interval(direction):
        """Enable or disable animation interval."""
        return direction == "stop"

    @dash_app.callback(
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

    # CSV Export Callbacks
    @dash_app.callback(
        Output('download-global-exports-map-csv', 'data'),
        Input('export-global-exports-map-btn', 'n_clicks'),
        State('global-exports-year-display', 'children'),
        State('global-exports-country-filter', 'value'),
        prevent_initial_call=True
    )
    def export_global_exports_map_csv(n_clicks, year_str, selected_countries):
        """Export Global Crude Exports map data to CSV"""
        if n_clicks and year_str:
            try:
                year_value = _parse_year_value(year_str)
                normalized_year = _normalize_year(year_value)
                
                # Get map data for the selected year
                if MAP_DF.empty:
                    # Return empty CSV if no data
                    empty_df = pd.DataFrame(columns=['Country', 'Year', 'Export_Volume'])
                    filename = f"Global_Crude_Exports_{normalized_year}.csv"
                    return dcc.send_data_frame(empty_df.to_csv, filename=filename, index=False)
                
                df = MAP_DF[MAP_DF["year"] == normalized_year].copy()
                
                # Filter by selected countries if specified
                if selected_countries is not None:
                    resolved_countries = _resolve_countries(selected_countries, COUNTRY_OPTIONS)
                    if len(resolved_countries) > 0 and "(All)" not in selected_countries:
                        # Filter df by matching countries (case-insensitive)
                        df_countries_normalized = df["country"].str.strip().str.lower()
                        target_countries_normalized = {c.lower().strip(): c for c in resolved_countries}
                        mask = df_countries_normalized.isin(target_countries_normalized.keys())
                        df = df[mask].copy()
                
                if df.empty:
                    # Return empty CSV if no data after filtering
                    empty_df = pd.DataFrame(columns=['Country', 'Year', 'Export_Volume'])
                    filename = f"Global_Crude_Exports_{normalized_year}.csv"
                    return dcc.send_data_frame(empty_df.to_csv, filename=filename, index=False)
                
                # Prepare export data
                df_export = df[['country', 'year', 'value']].copy()
                df_export = df_export.rename(columns={
                    'country': 'Country',
                    'year': 'Year',
                    'value': f"Export Volume {normalized_year} ('000 b/d)"
                })
                
                # Sort by export volume descending
                df_export = df_export.sort_values(f"Export Volume {normalized_year} ('000 b/d)", ascending=False)
                
                filename = f"Global_Crude_Exports_{normalized_year}.csv"
                return dcc.send_data_frame(df_export.to_csv, filename=filename, index=False)
            except Exception:
                # Return empty CSV on error
                empty_df = pd.DataFrame(columns=['Country', 'Year', 'Export_Volume'])
                filename = f"Global_Crude_Exports_{year_str or 'Unknown'}.csv"
                return dcc.send_data_frame(empty_df.to_csv, filename=filename, index=False)
        raise dash.exceptions.PreventUpdate

    @dash_app.callback(
        Output('download-russia-exports-csv', 'data'),
        Input('export-russia-exports-btn', 'n_clicks'),
        State('global-exports-stream-filter', 'value'),
        State('global-exports-country-filter', 'value'),
        prevent_initial_call=True
    )
    def export_russia_exports_csv(n_clicks, selected_streams, selected_countries):
        """Export Russia Annual Exports by Crude Stream data to CSV"""
        if n_clicks:
            try:
                # Get chart data
                if CHART_DF.empty:
                    # Return empty CSV if no data
                    empty_df = pd.DataFrame(columns=['Country', 'Year', 'Crude_Stream', 'Export_Volume'])
                    filename = "Russia_Annual_Exports_by_Crude_Stream.csv"
                    return dcc.send_data_frame(empty_df.to_csv, filename=filename, index=False)
                
                # Apply filters
                df = CHART_DF.copy()
                
                # Filter by streams
                if selected_streams:
                    df = df[df["stream"].isin(selected_streams)]
                
                # Filter by countries
                if selected_countries is not None:
                    resolved_countries = _resolve_countries(selected_countries, COUNTRY_OPTIONS)
                    if len(resolved_countries) > 0 and "(All)" not in selected_countries:
                        # Filter df by matching countries (case-insensitive)
                        if "country" in df.columns:
                            df_countries_normalized = df["country"].str.strip().str.lower()
                            target_countries_normalized = {c.lower().strip(): c for c in resolved_countries}
                            mask = df_countries_normalized.isin(target_countries_normalized.keys())
                            df = df[mask].copy()
                
                if df.empty:
                    # Return empty CSV if no data after filtering
                    empty_df = pd.DataFrame(columns=['Country', 'Year', 'Crude_Stream', 'Export_Volume'])
                    filename = "Russia_Annual_Exports_by_Crude_Stream.csv"
                    return dcc.send_data_frame(empty_df.to_csv, filename=filename, index=False)
                
                # Prepare export data
                df_export = df[['country', 'year', 'stream', 'value']].copy()
                df_export = df_export.rename(columns={
                    'country': 'Country',
                    'year': 'Year',
                    'stream': 'Crude_Stream',
                    'value': "Export Volume ('000 b/d)"
                })
                
                # Sort by country, year, and export volume
                df_export = df_export.sort_values(['Country', 'Year', "Export Volume ('000 b/d)"], ascending=[True, True, False])
                
                filename = "Russia_Annual_Exports_by_Crude_Stream.csv"
                return dcc.send_data_frame(df_export.to_csv, filename=filename, index=False)
            except Exception:
                # Return empty CSV on error
                empty_df = pd.DataFrame(columns=['Country', 'Year', 'Crude_Stream', 'Export_Volume'])
                filename = "Russia_Annual_Exports_by_Crude_Stream.csv"
                return dcc.send_data_frame(empty_df.to_csv, filename=filename, index=False)
        raise dash.exceptions.PreventUpdate

    @dash_app.callback(
        Output('download-annual-exports-csv', 'data'),
        Input('export-annual-exports-btn', 'n_clicks'),
        State('global-exports-country-filter', 'value'),
        State('global-exports-stream-filter', 'value'),
        prevent_initial_call=True
    )
    def export_annual_exports_csv(n_clicks, selected_countries, selected_streams):
        """Export Annual Exports Volume table data to CSV"""
        if n_clicks:
            try:
                # Get table data
                if TABLE_DF.empty:
                    # Return empty CSV if no data
                    empty_df = pd.DataFrame(columns=['Country', 'Crude'])
                    filename = "Annual_Exports_Volume.csv"
                    return dcc.send_data_frame(empty_df.to_csv, filename=filename, index=False)
                
                # Apply filters - NOTE: Country filter is NOT applied to export (export all countries)
                # Stream filter IS applied to export (export only selected streams)
                df = TABLE_DF.copy()
                
                # Filter by streams (crude types) only - country filter is ignored
                if selected_streams:
                    df = df[df["crude"].isin(selected_streams)]
                
                if df.empty:
                    # Return empty CSV if no data after filtering
                    empty_df = pd.DataFrame(columns=['Country', 'Crude'])
                    filename = "Annual_Exports_Volume.csv"
                    return dcc.send_data_frame(empty_df.to_csv, filename=filename, index=False)
                
                # Create pivot table: countries and crudes as rows, years as columns
                years = sorted(df["year"].unique(), reverse=True)
                
                # Pivot the data
                df_pivot = df.pivot_table(
                    index=["country", "crude"], 
                    columns="year", 
                    values="value", 
                    aggfunc="sum"
                ).fillna(0)
                
                # Reorder columns to match year order (newest first)
                df_pivot = df_pivot.reindex(columns=years, fill_value=0)
                
                # Reset index to make country and crude columns
                df_pivot = df_pivot.reset_index()
                df_pivot.columns.name = None
                
                # Rename columns
                df_pivot = df_pivot.rename(columns={'country': 'Country', 'crude': 'Crude'})
                
                # Rename year columns to include units
                rename_dict = {year: f"{year} ('000 b/d)" for year in years}
                df_pivot = df_pivot.rename(columns=rename_dict)
                
                # Sort by country and crude
                df_pivot = df_pivot.sort_values(['Country', 'Crude'])
                
                filename = "Annual_Exports_Volume.csv"
                return dcc.send_data_frame(df_pivot.to_csv, filename=filename, index=False)
            except Exception:
                # Return empty CSV on error
                empty_df = pd.DataFrame(columns=['Country', 'Crude'])
                filename = "Annual_Exports_Volume.csv"
                return dcc.send_data_frame(empty_df.to_csv, filename=filename, index=False)
        raise dash.exceptions.PreventUpdate

