"""
Global Exports View
Replicates Tableau Global Crude Exports dashboard with local CSV data
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.request import urlopen

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
from core.country_mappings import COUNTRY_TO_ISO, get_iso_code
from config import Config
from .shared_map_utils import (
    create_choropleth_map,
    get_mapbox_config,
    load_world_geojson,
    handle_map_click_reset,
    create_empty_map,
    MAP_BACKGROUND_COLOR,
    WORLD_CENTER
)

# Set Mapbox access token
if Config.MAPBOX_ACCESS_TOKEN:
    px.set_mapbox_access_token(Config.MAPBOX_ACCESS_TOKEN)


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
DEFAULT_COUNTRY = ["Russia"]  # Default country selection for UI, but table shows all countries until map click

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

# Map styling constants to match Energy Intelligence design
MAP_BACKGROUND_COLOR = '#d6e1eb'
MAP_LAND_COLOR = '#f4f4f4'

# Global variable to cache world GeoJSON
_world_geojson = None

def _load_world_geojson():
    """Load world GeoJSON for Mapbox maps"""
    global _world_geojson
    if _world_geojson is not None:
        return _world_geojson
    
    try:
        # Use the same GeoJSON source as imports_comparison.py
        geojson_url = "https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson"
        with urlopen(geojson_url) as response:
            _world_geojson = json.load(response)
        print("World GeoJSON loaded successfully")
        return _world_geojson
    except Exception as e:
        print(f"Failed to load world GeoJSON: {e}")
        _world_geojson = None
        return None

def _iso_for_country(country):
    """Return ISO Alpha-3 code for a country, using centralized mapping."""
    return get_iso_code(country)

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
        return create_empty_map("No map data available")
    
    normalized_year = _normalize_year(year)
    df = MAP_DF[MAP_DF["year"] == normalized_year].copy()
    if df.empty:
        return create_empty_map("No data for the selected year")
    
    # Filter by selected countries if provided
    # Note: selected_countries is already resolved (no "(All)" in it)
    # None = show all countries, [] = show no countries, [list] = show specific countries
    if selected_countries is not None and "country" in df.columns:
        if isinstance(selected_countries, list) and len(selected_countries) == 0:
            # Empty list means no countries selected - return empty figure
            return create_empty_map("No countries selected")
        elif selected_countries:
            # Filter df by matching countries (case-insensitive)
            df_countries_normalized = df["country"].str.strip().str.lower()
            target_countries_normalized = {c.lower().strip(): c for c in selected_countries}
            mask = df_countries_normalized.isin(target_countries_normalized.keys())
            df = df[mask].copy()
    
    if df.empty:
        return create_empty_map("No data for selected countries")
    
    # Prepare data for choropleth map using shared utilities
    locations = []
    z_values = []
    hover_texts = []
    
    for _, row in df.iterrows():
        country = row["country"]
        value = row["value"]
        
        # Convert country name to ISO code for better mapping
        iso_code = _iso_for_country(country)
        if iso_code:
            locations.append(iso_code)
            z_values.append(value)
            hover_texts.append(f"<b>{country}</b><br>Exports: {value:,.0f} '000 b/d")
    
    if not locations:
        return create_empty_map("No valid country data found")
    
    # Prepare country labels data
    centroids = (
        df.groupby("country")[["lat", "lon"]]
        .mean()
        .reset_index()
        .dropna(subset=["lat", "lon"])
    )
    
    # Limit label density for readability
    label_cap = min(len(centroids), 40 if len(centroids) > 120 else 60 if len(centroids) > 80 else len(centroids))
    labels_df = centroids.sort_values("country").head(label_cap)
    
    # Rename columns to match expected format for shared utilities
    if not labels_df.empty:
        labels_df = labels_df.rename(columns={
            "country": "Country",
            "lat": "Latitude", 
            "lon": "Longitude"
        })
    
    # Determine selection highlighting
    selected_iso = None
    other_isos = None
    if highlight_country:
        selected_iso = _iso_for_country(highlight_country)
        if selected_iso:
            # Get all other countries for dimming
            other_isos = [iso for iso in locations if iso != selected_iso]
    
    # Create the map using shared utilities for proper Mapbox integration
    max_value = max(z_values) if z_values else None
    fig = create_choropleth_map(
        locations=locations,
        z_values=z_values,
        colorscale=MAP_COLOR_STEPS,
        hover_text=hover_texts,
        selected_country=highlight_country,
        selected_iso=selected_iso,
        other_isos=other_isos,
        countries_df=labels_df if not labels_df.empty else None,
        height=520,
        zmin=0,
        zmax=max_value
    )
    
    # Set custom zoom level for global exports
    if hasattr(fig.layout, 'mapbox') and fig.layout.mapbox:
        fig.update_layout(mapbox_zoom=0.8)
    
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
        mapbox_zoom=0.8,
    )
    return fig


# Ensure INITIAL_TABLE_DATA absolutely contains all countries
# This is what gets loaded in the layout initially
try:
    # Create INITIAL_TABLE_DATA from ALL data, no filters
    INITIAL_TABLE_RAW = TABLE_DF.copy() if not TABLE_DF.empty else pd.DataFrame()
    INITIAL_TABLE_DATA = _prepare_table_records(INITIAL_TABLE_RAW) if not INITIAL_TABLE_RAW.empty else []
    
    # Verify we have all countries
    if INITIAL_TABLE_DATA:
        initial_countries = set()
        for record in INITIAL_TABLE_DATA:
            country = record.get('country')
            if country and country != "":  # Skip empty strings (duplicate country markers)
                initial_countries.add(country)
        
        print(f"INITIAL_TABLE_DATA: {len(initial_countries)} unique countries, {len(INITIAL_TABLE_DATA)} records")
        
        # If we have fewer countries than expected, log warning
        if COUNTRY_OPTIONS and len(initial_countries) < len(COUNTRY_OPTIONS):
            print(f"WARNING: INITIAL_TABLE_DATA has {len(initial_countries)} countries, expected {len(COUNTRY_OPTIONS)}")
            
except Exception as e:
    print(f"ERROR creating INITIAL_TABLE_DATA: {e}")
    # Ultimate fallback
    INITIAL_TABLE_RAW = TABLE_DF.copy() if not TABLE_DF.empty else pd.DataFrame()
    INITIAL_TABLE_DATA = _prepare_table_records(INITIAL_TABLE_RAW) if not INITIAL_TABLE_RAW.empty else []


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
                                type="dot",
                                color="#d35400",
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
            dcc.Store(id="global-exports-selected-country", data=None),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div([
                                html.H4(
                                    id="global-exports-chart-title",
                                    children="All Annual Exports by Crude Stream",
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
                                color="#d35400",
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
                        color="#d35400",
                        children=[
                            dash_table.DataTable(
                                id="global-exports-table",
                                columns=TABLE_COLUMNS,
                                data=INITIAL_TABLE_DATA,  # Use initial data showing all countries
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
        Input("global-exports-selected-country", "data"),
        prevent_initial_call=False,
    )
    def update_map(
        submenu: str,
        year_str: Optional[str],
        country_value: Optional[Sequence[str]],
        selected_country: Optional[str],
    ):
        """Update the map when the submenu or year changes."""
        try:
            if submenu != "global-exports":
                return _empty_figure("")
            year_value = _parse_year_value(year_str)
            normalized_year = _normalize_year(year_value)
            
            # Check if this is initial load or if country filter was explicitly changed
            ctx = dash.callback_context
            country_filter_triggered = False
            is_initial_call = not ctx.triggered or len(ctx.triggered) == 0
            
            if ctx.triggered:
                for trigger in ctx.triggered:
                    if "global-exports-country-filter" in trigger.get("prop_id", ""):
                        country_filter_triggered = True
                        break
            
            # Resolve countries for filtering
            selected_countries = None
            highlight = selected_country  # Highlight the clicked country
            
            # On initial load, ALWAYS show all countries regardless of default country selection
            if is_initial_call:
                # Initial load - show ALL countries (ignore any default selection)
                selected_countries = None
            elif not country_filter_triggered:
                # Show all countries when filter wasn't explicitly changed
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
        Output("global-exports-selected-country", "data"),
        Input("global-exports-map", "clickData"),
        State("global-exports-country-filter", "value"),
        State("global-exports-country-filter", "options"),
        State("global-exports-selected-country", "data"),
        prevent_initial_call=True,
    )
    def handle_map_click(click_data, current_filter, options, current_selected_country):
        """Handle map click to update country selection using standardized behavior from shared_map_utils"""
        if not click_data or not options:
            return no_update, no_update
        
        # Extract all country options (excluding "(All)")
        all_country_options = [opt["value"] for opt in options if opt["value"] != "(All)"]
        
        # SPECIAL HANDLING FOR FIRST CLICK:
        # If no country is currently selected (selected_country is None), 
        # treat this as a first click from "all countries" state regardless of current_filter
        if current_selected_country is None:
            # This is the first map click - extract the clicked country and select it
            point = click_data["points"][0]
            clicked_country = None
            is_background_click = False
            
            # Extract country from click data
            if "customdata" in point and point["customdata"]:
                if isinstance(point["customdata"], list) and len(point["customdata"]) > 0:
                    if point["customdata"][0] == "__BACKGROUND_CLICK__":
                        is_background_click = True
                    else:
                        clicked_country = point["customdata"][0]
                elif point["customdata"] == "__BACKGROUND_CLICK__":
                    is_background_click = True
                else:
                    clicked_country = point["customdata"]
            
            # Extract from other click data if needed
            if not clicked_country and not is_background_click:
                if "text" in point and point["text"]:
                    clicked_country = point["text"]
                elif "hovertext" in point and point["hovertext"]:
                    hovertext = point["hovertext"]
                    if "<b>" in hovertext and "</b>" in hovertext:
                        clicked_country = hovertext.split("<b>")[1].split("</b>")[0]
            
            # Handle first click
            if is_background_click:
                # Background click on first interaction - keep showing all
                return ["(All)"] + all_country_options, None
            elif clicked_country and clicked_country in all_country_options:
                # Valid country clicked - select it
                return [clicked_country], clicked_country
            else:
                # Invalid click - keep showing all
                return ["(All)"] + all_country_options, None
        
        # SUBSEQUENT CLICKS: Use the standard map click handler
        updated_filter = handle_map_click_reset(click_data, current_filter, all_country_options)
        
        # Determine selected country for highlighting
        selected_country = None
        if updated_filter and len(updated_filter) == 1 and updated_filter[0] != "(All)":
            selected_country = updated_filter[0]
        
        return updated_filter, selected_country

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
        Input("global-exports-selected-country", "data"),
        prevent_initial_call=False,
    )
    def update_chart(
        submenu: Optional[str],
        streams: Optional[Sequence[str]],
        countries: Optional[Sequence[str]],
        selected_country: Optional[str],
    ):
        """Update stacked area chart."""
        # Default values
        default_title = "All Annual Exports by Crude Stream"
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
            
            # Check if this is initial load
            ctx = dash.callback_context
            is_initial_call = not ctx.triggered or len(ctx.triggered) == 0
            
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
                # On initial load, ALWAYS show all countries regardless of default selection
                if is_initial_call:
                    # Initial load - show all countries (ignore any default selection)
                    resolved_countries = None
                elif countries is None:
                    # None means default - show all countries
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
            
            # Generate title based on country selection
            title = default_title
            try:
                # Determine which countries are being displayed for title generation
                # Use selected_country if available (from map clicks), otherwise use resolved_countries
                if selected_country and selected_country not in [None, "(All)"]:
                    # Map click selected a specific country
                    title = f"{selected_country} Annual Exports by Crude Stream"
                elif resolved_countries is not None and len(resolved_countries) > 0:
                    # Specific countries selected via country filter
                    if len(resolved_countries) == 1:
                        title = f"{resolved_countries[0]} Annual Exports by Crude Stream"
                    elif len(resolved_countries) <= 3:
                        country_names = ", ".join(resolved_countries)
                        title = f"{country_names} Annual Exports by Crude Stream"
                    else:
                        country_names = ", ".join(resolved_countries[:3])
                        remaining_count = len(resolved_countries) - 3
                        title = f"{country_names} and {remaining_count} more Annual Exports by Crude Stream"
                else:
                    # All countries (default case)
                    title = "All Annual Exports by Crude Stream"
            except Exception:
                title = "All Annual Exports by Crude Stream"
            
            # Final validation - ensure we always return valid types
            if not isinstance(fig, go.Figure):
                fig = default_fig
            if not isinstance(title, str) or not title:
                title = "All Annual Exports by Crude Stream"
            
            # Double-check return values
            if not isinstance(fig, go.Figure):
                fig = _empty_figure("Error: Invalid figure type")
            if not isinstance(title, str):
                title = "All Annual Exports by Crude Stream"
            
            return fig, title
            
        except Exception:
            # Always return valid values - this is critical
            try:
                error_fig = _empty_figure("Error loading chart")
                if not isinstance(error_fig, go.Figure):
                    error_fig = go.Figure()
                return error_fig, "All Annual Exports by Crude Stream"
            except Exception:
                # Last resort - return minimal valid figure
                minimal_fig = go.Figure()
                minimal_fig.add_annotation(text="Error loading chart", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
                return minimal_fig, "All Annual Exports by Crude Stream"

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
        Input("global-exports-selected-country", "data"),
        Input({"type": "stream-isolate-button", "stream": ALL}, "n_clicks"),
        prevent_initial_call=False,
    )
    def update_table(
        submenu: str,
        year_str: Optional[str],
        stream_filter_state: Optional[Sequence[str]],
        selected_country: Optional[str],
        legend_clicks,
    ):
        """
        Update table data.
        
        FIXED: On initial load, show ALL countries without any filtering.
        Only apply filters after user interaction.
        """
        try:
            if submenu != "global-exports":
                return []
            
            if TABLE_DF.empty:
                return []
            
            # Get callback context to determine what triggered the update
            ctx = dash.callback_context
            is_initial_call = not ctx.triggered or len(ctx.triggered) == 0
            
            # Get the ID of what triggered the callback
            triggered_id = None
            if ctx.triggered:
                triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
            
            # INITIAL LOAD: Return all data without any filtering
            if is_initial_call:
                # Return initial table data which already has all countries
                # We need to create it fresh to ensure it's all countries
                all_data = TABLE_DF.copy()
                return _prepare_table_records(all_data)
            
            # SUBSEQUENT INTERACTIONS: Apply filters based on user actions
            
            # Start with all data
            filtered = TABLE_DF.copy()
            
            # Apply country filter ONLY if selected_country is explicitly set from map click
            # AND this callback was triggered by selected_country change
            country_filter_applied = False
            if selected_country and selected_country not in [None, "(All)"] and selected_country in COUNTRY_OPTIONS:
                # Only apply country filter if this was triggered by a country change
                # or if we're intentionally filtering by country
                if triggered_id == "global-exports-selected-country" or selected_country != "Russia":
                    filtered = filtered[filtered["country"] == selected_country]
                    country_filter_applied = True
            
            # Apply stream filter ONLY if this was triggered by stream filter change
            # AND we're not in the initial "show all" state
            stream_filter_applied = False
            if stream_filter_state and len(stream_filter_state) > 0:
                # Check if this was triggered by stream filter or stream isolate button
                if (triggered_id == "global-exports-stream-filter" or 
                    (triggered_id and "stream-isolate-button" in triggered_id)):
                    # Don't apply stream filter if it would result in only Russia on initial-like state
                    if not country_filter_applied:
                        stream_filtered = filtered[filtered["crude"].isin(stream_filter_state)]
                        stream_countries = set(stream_filtered["country"].unique()) if not stream_filtered.empty else set()
                        # If stream filtering would show only Russia and we haven't applied country filter,
                        # don't apply it (keep showing all countries)
                        if stream_countries != {"Russia"} or country_filter_applied:
                            filtered = stream_filtered
                            stream_filter_applied = True
                    else:
                        # Country filter is applied, so stream filter is safe to apply
                        filtered = filtered[filtered["crude"].isin(stream_filter_state)]
                        stream_filter_applied = True
            
            # If no filters were applied, return all data
            if not country_filter_applied and not stream_filter_applied:
                all_data = TABLE_DF.copy()
                return _prepare_table_records(all_data)
            
            return _prepare_table_records(filtered)
            
        except Exception as e:
            print(f"Error in update_table: {e}")
            # Ultimate fallback: always return all data
            if not TABLE_DF.empty:
                return _prepare_table_records(TABLE_DF.copy())
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

