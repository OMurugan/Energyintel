"""
Shared map utilities for consistent Mapbox-based map implementation across WCOD dashboards.

This module provides standardized map creation functions with:
- Consistent white ocean/background color
- Unified click-to-reset behavior
- Mapbox integration with geo fallback
- Standardized styling and interactions
"""

import json
import os
import logging
from urllib.request import urlopen
import plotly.graph_objects as go
from config import Config

logger = logging.getLogger(__name__)

# Shared map configuration constants
MAP_BACKGROUND_COLOR = "white"  # Consistent white background
MAP_LAND_COLOR = "#f4f4f4"  # Light gray for land areas
MAP_COASTLINE_COLOR = "#cccccc"  # Light gray for coastlines
MAP_COUNTRY_BORDER_COLOR = "white"  # White country borders
MAP_SELECTION_COLOR = "#4A4A4A"  # Dark gray for selection highlights
MAP_SELECTION_WIDTH = 1  # Selection border width
MAP_SELECTED_WIDTH = 1 #Selected border width

# Shared tooltip styling
HOVER_LABEL_STYLE = dict(
    bgcolor="white",
    bordercolor="#cccccc",
    font=dict(
        family="Lato, sans-serif",
        size=13,
        color="#2c3e50"
    ),
    align="left"
)

# World map settings - optimized for carto-positron style
WORLD_CENTER = {"lat": 15.0, "lon": 0.0}  # Slightly lower center for better world view
WORLD_ZOOM = 1.2  # Lower zoom for better world overview with carto-positron

# Lazily loaded global geojson
_world_geojson = None


def load_world_geojson() -> dict | None:
    """Load a lightweight world GeoJSON once, with a short timeout fallback."""
    global _world_geojson
    if _world_geojson is not None:
        return _world_geojson
    
    url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
    try:
        logger.info("Loading world GeoJSON data from GitHub...")
        with urlopen(url, timeout=10) as resp:  # Increased timeout for server environments
            _world_geojson = json.load(resp)
        logger.info(f"Successfully loaded GeoJSON with {len(_world_geojson.get('features', []))} countries")
    except Exception as e:
        logger.error(f"Failed to load world GeoJSON: {e}")
        logger.info("Maps will fall back to built-in geo projection")
        _world_geojson = None
    return _world_geojson


def get_mapbox_config() -> tuple[bool, str | None, dict]:
    """
    Get Mapbox configuration and determine if Mapbox should be used.
    
    Returns:
        tuple: (use_mapbox, token, mapbox_layout_dict)
    """
    _mapbox_token = (getattr(Config, "MAPBOX_ACCESS_TOKEN", None) or "").strip()
    has_mapbox_token = _mapbox_token.startswith("pk.")
    geojson = load_world_geojson()
    
    # Log configuration status for debugging
    logger.info(f"Mapbox token configured: {has_mapbox_token}")
    logger.info(f"GeoJSON data loaded: {geojson is not None}")
    
    # Use Mapbox rendering if we have GeoJSON data (even without token for carto-positron)
    use_mapbox = geojson is not None
    
    if not geojson:
        logger.warning("No GeoJSON data - using geo fallback")
    elif not has_mapbox_token:
        logger.info("Using Mapbox with carto-positron (no token required)")
    else:
        logger.info("Using Mapbox with light style (token available)")
    
    logger.info(f"Map rendering mode: {'Mapbox' if use_mapbox else 'Geo fallback'}")
    
    # Optimized settings for carto-positron style (no token required)
    mapbox_layout = {
        "style": "carto-positron",  # Free style that works without token
        "center": WORLD_CENTER,
        "zoom": WORLD_ZOOM,
        "bearing": 0,
        "pitch": 0,
        "uirevision": "mapbox_config",  # Preserve UI state
    }
    
    # Only use token-based features if we have a valid token
    if has_mapbox_token:
        mapbox_layout["accesstoken"] = _mapbox_token
        # Use light style with token, but keep carto-positron as fallback
        mapbox_layout["style"] = "light"
        # Adjust zoom slightly for light style
        mapbox_layout["zoom"] = WORLD_ZOOM + 0.3
    
    return use_mapbox, _mapbox_token, mapbox_layout


def add_background_click_layer(fig: go.Figure, selected_country: str | None = None, use_mapbox: bool = True):
    """
    Add optimized invisible scatter points across ocean areas for click-to-reset functionality.
    
    Reduced from 100+ points to ~20 strategic locations for better performance while
    maintaining good click coverage across major ocean areas.
    
    Args:
        fig: Plotly figure to add the layer to
        selected_country: Currently selected country (affects whether layers are added)
        use_mapbox: Whether to use Mapbox or geo coordinates
    """
    # Optimized strategic ocean points - reduced for better performance
    # These cover major ocean areas where users are likely to click
    ocean_points = [
        # Atlantic Ocean - key points
        [-40, 0], [-30, 20], [-50, -20], [-60, 40], [-20, -30],
        [-45, 10], [-35, -10], [-25, 35],
        
        # Pacific Ocean - key points  
        [-140, 0], [-160, 20], [-120, -10], [160, -20], [140, 10], [-150, 30],
        [170, 0], [-130, 40], [150, 30],
        
        # Indian Ocean - key points
        [80, -20], [90, 0], [100, -30], [70, 10], [85, -10],
        
        # Arctic Ocean - key points
        [-100, 80], [0, 85], [100, 80],
        
        # Southern Ocean - key points
        [-120, -65], [0, -75], [120, -70]
    ]
    
    # Extract lons and lats
    lons = [point[0] for point in ocean_points]
    lats = [point[1] for point in ocean_points]
    
    # Only add background click layers if a country is selected
    if selected_country:
        if use_mapbox:
            # Add invisible scatter points in ocean areas
            fig.add_trace(
                go.Scattermapbox(
                    lon=lons,
                    lat=lats,
                    mode="markers",
                    marker=dict(
                        size=120,  # Larger invisible markers to increase click area
                        color="rgba(255,255,255,0.01)",  # Nearly transparent
                        opacity=0.01
                    ),
                    hoverinfo="none",  # Hide hover text but keep click functionality
                    customdata=[["__BACKGROUND_CLICK__"]] * len(ocean_points),
                    showlegend=False,
                    name="ocean_background"
                )
            )
            
            # Also add a very transparent fill layer as backup
            fig.add_trace(
                go.Scattermapbox(
                    lon=[-180, 180, 180, -180, -180],
                    lat=[-85, -85, 85, 85, -85],
                    mode="lines",
                    line=dict(color="rgba(0,0,0,0)", width=0),
                    fill="toself",
                    fillcolor="rgba(255,255,255,0.001)",  # Extremely transparent
                    hoverinfo="none",  # Hide hover text but keep click functionality
                    customdata=[["__BACKGROUND_CLICK__"]],
                    showlegend=False,
                    name="background_fill",
                    opacity=0.001
                )
            )
        else:
            # Geo fallback - use scatter points
            fig.add_trace(
                go.Scattergeo(
                    lon=lons,
                    lat=lats,
                    mode="markers",
                    marker=dict(
                        size=120,
                        color="rgba(255,255,255,0.01)",
                        opacity=0.01
                    ),
                    hoverinfo="none",  # Hide hover text but keep click functionality
                    customdata=[["__BACKGROUND_CLICK__"]] * len(ocean_points),
                    showlegend=False,
                    name="ocean_background"
                )
            )
            
            # Backup fill layer
            fig.add_trace(
                go.Scattergeo(
                    lon=[-180, 180, 180, -180, -180],
                    lat=[-85, -85, 85, 85, -85],
                    mode="lines",
                    line=dict(color="rgba(0,0,0,0)", width=0),
                    fill="toself",
                    fillcolor="rgba(255,255,255,0.001)",
                    hoverinfo="none",  # Hide hover text but keep click functionality
                    customdata=[["__BACKGROUND_CLICK__"]],
                    showlegend=False,
                    name="background_fill",
                    opacity=0.001
                )
            )


def add_country_labels(fig: go.Figure, countries_df, use_mapbox: bool = True, max_labels: int = 40):
    """
    Add country labels to the map with single text layer for better readability.
    
    Args:
        fig: Plotly figure to add labels to
        countries_df: DataFrame with Country, Latitude, Longitude columns
        use_mapbox: Whether to use Mapbox or geo coordinates
        max_labels: Maximum number of labels to show
    """
    if countries_df.empty:
        return
    
    # Limit label density for readability
    display_df = countries_df.head(max_labels) if len(countries_df) > max_labels else countries_df
    
    if use_mapbox:
        # Single text layer with good contrast
        fig.add_trace(
            go.Scattermapbox(
                lon=display_df["Longitude"],
                lat=display_df["Latitude"],
                mode="text",
                text=display_df["Country"],
                textfont=dict(
                    size=11,
                    color="#2c3e50",  # Dark blue-gray for good contrast
                    family="Open Sans Regular"
                ),
                textposition="middle center",
                hoverinfo="skip",
                showlegend=False,
                name="labels"
            )
        )
    else:
        # Single text layer for geo map
        fig.add_trace(
            go.Scattergeo(
                lon=display_df["Longitude"],
                lat=display_df["Latitude"],
                mode="text",
                text=display_df["Country"],
                textfont=dict(
                    size=12, 
                    color="#2c3e50",  # Dark blue-gray for good contrast
                    family="Open Sans Regular"
                ),
                textposition="middle center",
                hoverinfo="skip",
                showlegend=False,
                opacity=1.0,
                name="labels"
            )
        )


def add_selection_highlight(fig: go.Figure, geojson: dict, selected_iso: str | list, selected_country: str | list, 
                          other_isos: list = None, use_mapbox: bool = True):
    """
    Add selection highlighting for selected countries and dim others.
    
    Args:
        fig: Plotly figure to add highlighting to
        geojson: GeoJSON data for country boundaries
        selected_iso: ISO code(s) of selected country/countries
        selected_country: Name(s) of selected country/countries
        other_isos: List of ISO codes for other countries to dim
        use_mapbox: Whether to use Mapbox or geo coordinates
    """
    # Normalize inputs to lists
    selected_isos = [selected_iso] if isinstance(selected_iso, str) else (selected_iso or [])
    selected_names = [selected_country] if isinstance(selected_country, str) else (selected_country or [])
    
    if use_mapbox and geojson:
        # Add dimming overlay for other countries
        if other_isos:
            fig.add_trace(
                go.Choroplethmapbox(
                    geojson=geojson,
                    locations=other_isos,
                    z=[0] * len(other_isos),
                    featureidkey="id",
                    colorscale=[[0, "rgba(255,255,255,0.8)"], [1, "rgba(255,255,255,0.8)"]],
                    showscale=False,
                    hoverinfo="none",  # Hide hover text but keep click functionality
                    customdata=["__BACKGROUND_CLICK__" for _ in other_isos],
                    marker_line_color="rgba(200,200,200,0.3)",
                    marker_line_width=0.5,
                    name="inactive_countries"
                )
            )
        
        # Add selection border for selected countries
        if selected_isos:
            fig.add_trace(
                go.Choroplethmapbox(
                    geojson=geojson,
                    locations=selected_isos,
                    z=[0] * len(selected_isos),
                    featureidkey="id",
                    colorscale=[[0, "rgba(255,255,255,0.01)"], [1, "rgba(255,255,255,0.01)"]],
                    showscale=False,
                    marker_line_color=MAP_SELECTION_COLOR,
                    marker_line_width=MAP_SELECTED_WIDTH,
                    hoverinfo="none",  # Hide hover text but keep click functionality
                    customdata=selected_names if len(selected_names) == len(selected_isos) else ["__SELECTED__"] * len(selected_isos),
                    name="selected_countries_border"
                )
            )
    else:
        # Geo fallback
        if other_isos:
            fig.add_trace(
                go.Choropleth(
                    locations=other_isos,
                    z=[0] * len(other_isos),
                    locationmode="ISO-3",
                    colorscale=[[0, "rgba(255,255,255,0.8)"], [1, "rgba(255,255,255,0.8)"]],
                    showscale=False,
                    hoverinfo="none",  # Hide hover text but keep click functionality
                    customdata=["__BACKGROUND_CLICK__" for _ in other_isos],
                    marker_line_color="rgba(200,200,200,0.3)",
                    marker_line_width=0.5,
                    name="inactive_countries"
                )
            )
        
        if selected_isos:
            fig.add_trace(
                go.Choropleth(
                    locations=selected_isos,
                    z=[0] * len(selected_isos),
                    locationmode="ISO-3",
                    colorscale=[[0, "rgba(255,255,255,0.01)"], [1, "rgba(255,255,255,0.01)"]],
                    showscale=False,
                    marker_line_color=MAP_SELECTION_COLOR,
                    marker_line_width=MAP_SELECTION_WIDTH,
                    hoverinfo="none",  # Hide hover text but keep click functionality
                    customdata=selected_names if len(selected_names) == len(selected_isos) else ["__SELECTED__"] * len(selected_isos),
                    name="selected_countries_border"
                )
            )


def apply_standard_layout(fig: go.Figure, use_mapbox: bool = True, mapbox_layout: dict = None, 
                         height: int = 520, margin: dict = None):
    """
    Apply standard layout settings with consistent white background.
    
    Args:
        fig: Plotly figure to apply layout to
        use_mapbox: Whether to use Mapbox or geo layout
        mapbox_layout: Mapbox layout configuration
        height: Figure height in pixels
        margin: Custom margin dict, defaults to minimal margins
    """
    if margin is None:
        margin = dict(l=0, r=0, t=0, b=0)
    
    layout_config = {
        "margin": margin,
        "height": height,
        "hovermode": "closest",
        "plot_bgcolor": MAP_BACKGROUND_COLOR,
        "paper_bgcolor": "white",
        "showlegend": False,
        "dragmode": "pan",
    }
    
    if use_mapbox and mapbox_layout:
        layout_config["mapbox"] = mapbox_layout
    else:
        layout_config["geo"] = {
            "showframe": False,
            "showcoastlines": True,
            "projection": dict(type="natural earth"),
            "center": dict(lat=WORLD_CENTER["lat"], lon=WORLD_CENTER["lon"]),
            "showland": True,
            "landcolor": MAP_LAND_COLOR,
            "coastlinecolor": MAP_COASTLINE_COLOR,
            "showocean": True,
            "oceancolor": MAP_BACKGROUND_COLOR,
            "showlakes": True,
            "lakecolor": MAP_BACKGROUND_COLOR,
            "showrivers": False,
        }
    
    fig.update_layout(**layout_config)


def create_choropleth_map(locations: list, z_values: list, colorscale: list, 
                         hover_text: list = None, selected_country: str = None,
                         selected_iso: str = None, other_isos: list = None,
                         countries_df = None, height: int = 520, 
                         zmin: float = None, zmax: float = None,
                         country_names: list = None) -> go.Figure:
    """
    Create a standardized choropleth map with consistent styling and behavior.
    
    Args:
        locations: List of ISO codes for countries
        z_values: List of values for color mapping
        colorscale: Plotly colorscale for the choropleth
        hover_text: Optional list of hover text for each location
        selected_country: Name of selected country for highlighting
        selected_iso: ISO code of selected country
        other_isos: List of other ISO codes to dim when country is selected
        countries_df: DataFrame with country coordinates for labels
        height: Figure height in pixels
        zmin: Minimum value for color scale
        zmax: Maximum value for color scale
        country_names: List of country names corresponding to locations (for customdata)
    
    Returns:
        go.Figure: Configured Plotly figure
    """
    use_mapbox, token, mapbox_layout = get_mapbox_config()
    geojson = load_world_geojson()
    
    fig = go.Figure()
    
    # Prepare customdata for click handling
    # If country_names is provided, use it; otherwise try to extract from hover_text
    if country_names:
        customdata = [[name] for name in country_names]
    elif hover_text:
        # Try to extract country names from hover_text
        customdata = []
        for text in hover_text:
            if isinstance(text, str) and "<b>" in text and "</b>" in text:
                # Extract country name from HTML formatted text
                try:
                    country_name = text.split("<b>")[1].split("</b>")[0]
                    customdata.append([country_name])
                except (IndexError, AttributeError):
                    customdata.append([text])
            else:
                customdata.append([text if text else ""])
    else:
        # Fallback: use locations as country identifiers
        customdata = [[loc] for loc in locations]
    
    # Create main choropleth layer FIRST
    if use_mapbox and geojson:
        logger.info("Creating Mapbox choropleth map")
        fig.add_trace(
            go.Choroplethmapbox(
                geojson=geojson,
                locations=locations,
                z=z_values,
                zmin=zmin,
                zmax=zmax,
                featureidkey="id",
                colorscale=colorscale,
                showscale=False,
                hoverinfo="text" if hover_text else "location+z",
                hovertext=hover_text,
                customdata=customdata,  # Use proper country names for click handling
                marker_line_color=MAP_COUNTRY_BORDER_COLOR,
                marker_line_width=0.8,
                marker_opacity=0.8,
                hoverlabel=HOVER_LABEL_STYLE,
                name="countries"
            )
        )
    else:
        logger.info("Creating geo choropleth map (fallback)")
        fig.add_trace(
            go.Choropleth(
                locations=locations,
                z=z_values,
                zmin=zmin,
                zmax=zmax,
                locationmode="ISO-3",
                colorscale=colorscale,
                showscale=False,
                hoverinfo="text" if hover_text else "location+z",
                hovertext=hover_text,
                customdata=customdata,  # Use proper country names for click handling
                marker_line_color=MAP_COUNTRY_BORDER_COLOR,
                marker_line_width=0.7,
                marker_opacity=0.8,
                hoverlabel=HOVER_LABEL_STYLE,
                name="countries"
            )
        )
    
    # Add selection highlighting if a country is selected
    if selected_country and selected_iso:
        add_selection_highlight(fig, geojson, selected_iso, selected_country, other_isos, use_mapbox)
    
    # Add background click layer AFTER countries and selection highlights
    # This ensures it's on top and can capture clicks
    add_background_click_layer(fig, selected_country, use_mapbox)
    
    # Add country labels if provided (on top of everything)
    if countries_df is not None and not countries_df.empty:
        add_country_labels(fig, countries_df, use_mapbox)
    
    # Apply standard layout
    apply_standard_layout(fig, use_mapbox, mapbox_layout, height)
    
    # Add configuration metadata for debugging
    fig.update_layout(
        uirevision="map_config",  # Preserve UI state across updates
        meta={
            "mapbox_enabled": use_mapbox,
            "token_present": bool(token),
            "geojson_loaded": geojson is not None
        }
    )
    
    logger.info(f"Map created with {len(fig.data)} traces, mapbox_enabled: {use_mapbox}")
    
    return fig


def create_empty_map(message: str = "No data available", height: int = 520) -> go.Figure:
    """Create an empty map with a message."""
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
        plot_bgcolor=MAP_BACKGROUND_COLOR,
        margin=dict(l=0, r=0, t=0, b=0),
    )
    return fig


def create_error_figure(error_message: str = "An error occurred while loading data", height: int = 520) -> go.Figure:
    """Create an error figure with a user-friendly message."""
    fig = go.Figure()
    fig.add_annotation(
        text=f"⚠️ {error_message}<br><br>Please try refreshing the page or contact support if the issue persists.",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=14, color="#e74c3c"),
        align="center"
    )
    fig.update_layout(
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False)
    )
    return fig


def create_loading_figure(message: str = "Loading data...", height: int = 520) -> go.Figure:
    """Create a loading figure with a message."""
    fig = go.Figure()
    fig.add_annotation(
        text=f"🔄 {message}",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=14, color="#3498db"),
        align="center"
    )
    fig.update_layout(
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False)
    )
    return fig


def handle_map_click_reset(click_data, current_filter, all_countries: list) -> list:
    """
    Handle map click events with consistent reset behavior.
    
    When a country is selected, clicking anywhere else on the map (including 
    ocean areas or other countries) resets the view to show all countries.
    
    Args:
        click_data: Dash clickData from map
        current_filter: Current country filter selection
        all_countries: List of all available countries
    
    Returns:
        list: Updated country filter selection
    """
    if not click_data:
        return current_filter
    
    point = click_data["points"][0]
    country = None
    is_background_click = False
    
    # Check for background click
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
    
    # Extract country from other click data
    if not country and not is_background_click:
        if "text" in point and point["text"]:
            country = point["text"]
        elif "hovertext" in point and point["hovertext"]:
            hovertext = point["hovertext"]
            if "Click to reset view" in hovertext:
                if "<b>" in hovertext and "</b>" in hovertext:
                    country = hovertext.split("<b>")[1].split("</b>")[0]
                else:
                    is_background_click = True
            elif "<b>" in hovertext and "</b>" in hovertext:
                country = hovertext.split("<b>")[1].split("</b>")[0]
    
    # Handle background clicks - always reset to all countries
    if is_background_click:
        return ["(All)"] + all_countries
    
    # If we can't determine the country, treat as background click
    if not country or country not in all_countries:
        return ["(All)"] + all_countries
    
    # Resolve current selection
    current_filter = current_filter or []
    if "(All)" in current_filter:
        resolved_countries = all_countries
    else:
        resolved_countries = [c for c in current_filter if c in all_countries]
    
    # Enhanced behavior: if one country is selected, any click resets to all
    if len(resolved_countries) == 1:
        return ["(All)"] + all_countries
    
    # If all countries shown, clicking selects only that country
    return [country]