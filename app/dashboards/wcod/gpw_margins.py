"""
Gross Product Worth and Margins View
GPW and margins analysis for crude types with filters and charts
"""
import os
from datetime import datetime
from dash import dcc, html, Input, Output, State, callback, dash_table, callback_context, dash
import dash.dependencies as dd
import plotly.graph_objects as go
import pandas as pd
import plotly.io as pio
import base64
from weasyprint import HTML, CSS
import fitz # PyMuPDF
import io
from PIL import Image
from core.data_helpers import execute_query

# Data locations
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "Gross_Product_Worth_and_Margins"
)
# GPW_CSV = os.path.join(DATA_DIR, "Gross Product Worth_data.csv")
# INCREMENTAL_MARGINS_CSV = os.path.join(DATA_DIR, "Incremental Margins_data.csv")


def _read_csv(path: str) -> pd.DataFrame:
    """Read a CSV file and trim column names."""
    try:
        df = pd.read_csv(path)
        df.columns = df.columns.str.strip()
        return df
    except Exception as exc:
        print(f"[gpw_margins] Failed to read {path}: {exc}")
        return pd.DataFrame()


def _load_gpw_data(region: str = None) -> pd.DataFrame:
    """Load and normalize Gross Product Worth data from database."""
    try:
        query = """
        SELECT
            CASE tech_type
                WHEN 'HYCRK' THEN 'Hydrocracking'
                WHEN 'HSK'   THEN 'Hydroskimming'
                WHEN 'Coker' THEN 'Coking'
                WHEN 'FCC' THEN
                    CASE delivery_to
                        WHEN 'NWE' THEN 'Catalytic Cracking'
                        WHEN 'Singapore' THEN 'Catalytic Cracking'
                        ELSE 'Fluid Catalytic Cracking'
                    END
                ELSE tech_type
            END AS "TechTypeFull",
            TO_CHAR("date", 'Mon YY') AS "Month of Date",
            crude_name AS "Crude",
            delivery_to AS "Region",
            tech_type AS "TechType",
            price AS "DataValue"
        FROM fact_wcod_prices
        WHERE price_type = 'GPW'
        """
        
        params = {}
        if region:
            query += " AND delivery_to = :region"
            params['region'] = region
        
        rows = execute_query(query, params)
        
        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(rows)
        
        # Rename columns to match expected format
        df = df.rename(columns={
            'Month of Date': 'MonthDate',
            'DataValue': 'Value',
            'TechTypeFull': 'TechType',
            'Region': 'Region',
            'Crude': 'Crude',
            'TechType': 'TechTypeShort'
        })
        
        # Parse date - format is like "Feb 19", "Mar 19", "Sept 19"
        # Handle "Sept" which should be "Sep"
        if 'MonthDate' in df.columns:
            df['MonthDate'] = df['MonthDate'].str.replace('Sept', 'Sep', regex=False)
            # Parse date with format "%b %y" (e.g., "Feb 19" -> February 2019)
            df['Date'] = pd.to_datetime(df['MonthDate'], format='%b %y', errors='coerce')
        
        # Clean and ensure proper types
        if 'Value' in df.columns:
            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
        
        df = df.dropna(subset=['Value', 'Date'])
        return df
    except Exception as e:
        print(f"[gpw_margins] Error loading GPW data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def _load_incremental_margins_data(region: str = None) -> pd.DataFrame:
    """Load and normalize Incremental Margins data from database."""
    try:
        query = """
        SELECT
            CASE tech_type
                WHEN 'HYCRK' THEN 'Hydrocracking'
                WHEN 'HSK'   THEN 'Hydroskimming'
                WHEN 'Coker' THEN 'Coking'
                WHEN 'FCC' THEN
                    CASE delivery_to
                        WHEN 'NWE' THEN 'Catalytic Cracking'
                        ELSE 'Fluid Catalytic Cracking'
                    END
                ELSE tech_type
            END AS "TechTypeFull",
            TO_CHAR("date", 'Mon YY') AS "Month of Date",
            crude_name AS "Crude",
            delivery_to AS "Region",
            tech_type AS "TechType",
            price AS "DataValue"
        FROM fact_wcod_prices
        WHERE price_type = 'Refining Margin'
        """
        
        params = {}
        if region:
            query += " AND delivery_to = :region"
            params['region'] = region
        
        rows = execute_query(query, params)
        
        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(rows)
        
        # Rename columns to match expected format
        df = df.rename(columns={
            'Month of Date': 'MonthDate',
            'DataValue': 'Value',
            'TechTypeFull': 'TechType',
            'Region': 'Region',
            'Crude': 'Crude',
            'TechType': 'TechTypeShort'
        })
        
        # Parse date - format is like "Feb 19", "Mar 19", "Sept 19"
        if 'MonthDate' in df.columns:
            df['MonthDate'] = df['MonthDate'].str.replace('Sept', 'Sep', regex=False)
            df['Date'] = pd.to_datetime(df['MonthDate'], format='%b %y', errors='coerce')
        
        if 'Value' in df.columns:
            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
        
        df = df.dropna(subset=['Value', 'Date'])
        return df
    except Exception as e:
        print(f"[gpw_margins] Error loading Incremental Margins data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()




def _load_data_table_data_from_db(region: str = None, start_date: str = None, end_date: str = None, crudes: list = None, tech_types: list = None) -> pd.DataFrame:
    """Load and normalize Data Table data from database using the provided query."""
    try:
        query = """
        SELECT
            TO_CHAR(date, 'Mon YY') AS "Month of Date",
            price_type AS "DataType",
            CASE tech_type
                WHEN 'HYCRK' THEN 'Hydrocracking'
                WHEN 'HSK' THEN 'Hydroskimming'
                WHEN 'Coker' THEN 'Coking'
                WHEN 'FCC' THEN
                    CASE delivery_to
                        WHEN 'NWE' THEN 'Catalytic Cracking'
                        ELSE 'Fluid Catalytic Cracking'
                    END
                ELSE tech_type
            END AS "TechTypeFull",
            crude_name AS "Crude",
            price AS "DataValue",
            date AS "Date"
        FROM fact_wcod_prices
        WHERE price_type IN ('GPW', 'Refining Margin')
        """
        
        params = {}
        if region:
            query += " AND delivery_to = :region"
            params['region'] = region
        if start_date:
            query += " AND date >= :start_date"
            params['start_date'] = start_date
        if end_date:
            query += " AND date <= :end_date"
            params['end_date'] = end_date
        if crudes:
            query += " AND crude_name = ANY(:crudes)"
            params['crudes'] = crudes
        if tech_types:
            query += " AND tech_type = ANY(:tech_types)"
            params['tech_types'] = tech_types
        
        query += """
        ORDER BY
            date DESC, 
            price_type,
            "TechTypeFull",
            crude_name
        """
        
        rows = execute_query(query, params)
        
        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(rows)
        
        # Rename columns to match expected format
        df = df.rename(columns={
            'Month of Date': 'MonthDate',
            'DataValue': 'Value',
            'TechTypeFull': 'TechType',
            'Crude': 'Crude',
            'DataType': 'DataType'
        })
        
        # Preserve original date format for display (e.g., "Aug 07")
        if 'MonthDate' in df.columns:
            df['MonthDateDisplay'] = df['MonthDate'].copy()  # Keep original format
            # Parse date for filtering/sorting (handle "Sept" -> "Sep")
            df['MonthDateParsed'] = df['MonthDate'].str.replace('Sept', 'Sep', regex=False)
            # Use the Date column from database if available, otherwise parse from MonthDate
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            else:
                df['Date'] = pd.to_datetime(df['MonthDateParsed'], format='%b %y', errors='coerce')
        
        if 'Value' in df.columns:
            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
        
        df = df.dropna(subset=['Value', 'Date'])
        return df
    except Exception as e:
        print(f"[gpw_margins] Error loading Data Table data from database: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


# Load filter options from database (without region filter to get all available options)
def _load_incremental_margins_data_from_db(region: str = None, start_date: str = None, end_date: str = None, crudes: list = None, tech_types: list = None) -> pd.DataFrame:
    """Load Incremental Margins data from database."""
    try:
        query = """
        SELECT
            TO_CHAR(date, 'Mon YY') AS "Month of Date",
            price_type AS "DataType",
            CASE tech_type
                WHEN 'HYCRK' THEN 'Hydrocracking'
                WHEN 'HSK' THEN 'Hydroskimming'
                WHEN 'Coker' THEN 'Coking'
                WHEN 'FCC' THEN
                    CASE delivery_to
                        WHEN 'NWE' THEN 'Catalytic Cracking'
                        ELSE 'Fluid Catalytic Cracking'
                    END
                ELSE tech_type
            END AS "TechTypeFull",
            crude_name AS "Crude",
            price AS "DataValue",
            date AS "Date"
        FROM fact_wcod_prices
        WHERE price_type = 'Refining Margin'
        """
        
        params = {}
        if region:
            query += " AND delivery_to = :region"
            params['region'] = region
        if start_date:
            query += " AND date >= :start_date"
            params['start_date'] = start_date
        if end_date:
            query += " AND date <= :end_date"
            params['end_date'] = end_date
        if crudes:
            query += " AND crude_name = ANY(:crudes)"
            params['crudes'] = crudes
        if tech_types:
            query += " AND tech_type = ANY(:tech_types)"
            params['tech_types'] = tech_types
        
        query += """
        ORDER BY
            date DESC, 
            price_type,
            "TechTypeFull",
            crude_name
        """
        
        rows = execute_query(query, params)
        print(f"[gpw_margins] Incremental Margins query rows: {len(rows) if rows else 0}")
        
        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(rows)
        
        # Rename columns to match expected format
        df = df.rename(columns={
            'Month of Date': 'MonthDate',
            'DataValue': 'Value',
            'TechTypeFull': 'TechType',
            'Crude': 'Crude',
            'DataType': 'DataType'
        })
        
        # Preserve original date format for display (e.g., "Aug 07")
        if 'MonthDate' in df.columns:
            df['MonthDateDisplay'] = df['MonthDate'].copy()  # Keep original format
            # Parse date for filtering/sorting (handle "Sept" -> "Sep")
            df['MonthDateParsed'] = df['MonthDate'].str.replace('Sept', 'Sep', regex=False)
            # Use the Date column from database if available, otherwise parse from MonthDate
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            else:
                df['Date'] = pd.to_datetime(df['MonthDateParsed'], format='%b %y', errors='coerce')
        
        if 'Value' in df.columns:
            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
        
        df = df.dropna(subset=['Value', 'Date'])
        return df
    except Exception as e:
        print(f"[gpw_margins] Error loading Incremental Margins data from database: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def _get_available_regions():
    """Get available regions from database."""
    try:
        query = """
        SELECT DISTINCT delivery_to AS "Region"
        FROM fact_wcod_prices
        WHERE price_type IN ('GPW', 'Refining Margin')
            AND delivery_to IS NOT NULL
        ORDER BY delivery_to
        """
        rows = execute_query(query)
        if rows:
            return [row['Region'] for row in rows]
        return []
    except Exception as e:
        print(f"[gpw_margins] Error getting regions: {e}")
        return []

def _get_available_crudes(region: str = None):
    """Get available crudes from database, optionally filtered by region."""
    try:
        query = """
        SELECT DISTINCT crude_name AS "Crude"
        FROM fact_wcod_prices
        WHERE price_type IN ('GPW', 'Refining Margin')
            AND crude_name IS NOT NULL
        """
        params = {}
        if region:
            query += " AND delivery_to = :region"
            params['region'] = region
        query += """
        ORDER BY crude_name
        """
        rows = execute_query(query, params)
        if rows:
            return [row['Crude'] for row in rows]
        return []
    except Exception as e:
        print(f"[gpw_margins] Error getting crudes: {e}")
        return []

def _get_available_tech_types(region: str = None):
    """Get available tech types from database, optionally filtered by region."""
    try:
        query = """
        SELECT DISTINCT
            CASE tech_type
                WHEN 'HYCRK' THEN 'Hydrocracking'
                WHEN 'HSK'   THEN 'Hydroskimming'
                WHEN 'Coker' THEN 'Coking'
                WHEN 'FCC' THEN
                    CASE delivery_to
                        WHEN 'NWE' THEN 'Catalytic Cracking'
                        ELSE 'Fluid Catalytic Cracking'
                    END
                ELSE tech_type
            END AS "TechTypeFull"
        FROM fact_wcod_prices
        WHERE price_type IN ('GPW', 'Refining Margin')
        """
        params = {}
        if region:
            query += " AND delivery_to = :region"
            params['region'] = region
        query += """
        ORDER BY "TechTypeFull"
        """
        rows = execute_query(query, params)
        if rows:
            return [row['TechTypeFull'] for row in rows]
        return []
    except Exception as e:
        print(f"[gpw_margins] Error getting tech types: {e}")
        return []

# Get filter options from database
REGIONS = _get_available_regions()
CRUDES = _get_available_crudes(None) # Load all crudes initially
TECH_TYPES = _get_available_tech_types(None) # Load all tech types initially

# Load initial data with default region for date range calculation (if available)
# This is only used for initial date range setup
if REGIONS:
    DEFAULT_REGION = REGIONS[0]
    initial_gpw_df = _load_gpw_data(DEFAULT_REGION)
else:
    DEFAULT_REGION = None
    initial_gpw_df = pd.DataFrame()

# Color mapping for crudes (for legend)
CRUDE_COLORS = {
    'Arab Light': '#1f77b4',
    'Bonny Light': '#ff7f0e',
    'Brent Blend': '#2ca02c',
    'Minas': '#9467bd',
    'Oman': '#8c564b',
    'Tapis': '#e377c2',
    'Urals': '#d62728',
    'Forties Blend': '#7f7f7f',
    'Mars Blend': '#bcbd22',
    'Maya': '#17becf',
}

# Highlight color for selected crude in table
HIGHLIGHT_COLOR = '#fff8dc'

# Fallback colors
FALLBACK_COLORS = ['#9467bd', '#8c564b', '#e377c2', '#7f7f7f']


def _crude_filter_options(crude_names):
    """Create checklist options for crudes (no color boxes, just checkbox and text)."""
    options = []
    for name in crude_names:
        options.append({"label": name, "value": name})
    return options

def _crude_legend_options(crude_names):
    """Create checklist options with colored swatches for crudes (for legend)."""
    options = []
    for idx, name in enumerate(crude_names):
        color = CRUDE_COLORS.get(name)
        if not color:
            color = FALLBACK_COLORS[idx % len(FALLBACK_COLORS)]
        
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
                name,
            ],
            style={"display": "flex", "alignItems": "center", "width": "100%", "color": "#1b365d", "fontWeight": "600", "fontSize": "13px"},
        )
        options.append({"label": label, "value": name})
    return options

# Date range - create sorted list of unique dates from initial data
if not initial_gpw_df.empty:
    unique_dates = sorted(initial_gpw_df['Date'].unique())
    DATE_MIN = unique_dates[0] if unique_dates else datetime(2019, 1, 1)
    DATE_MAX = unique_dates[-1] if unique_dates else datetime(2024, 12, 31)
    # Create date index mapping (for slider)
    DATE_LIST = unique_dates
    DEFAULT_START_INDEX = 0
    DEFAULT_END_INDEX = len(unique_dates) - 1 if unique_dates else 0
else:
    DATE_LIST = []
    DATE_MIN = datetime(2019, 1, 1)
    DATE_MAX = datetime(2024, 12, 31)
    DEFAULT_START_INDEX = 0
    DEFAULT_END_INDEX = 0

# Set default start date to Jan 19 (find in date list)
# Set default start date to Apr 19 (find in date list)
DEFAULT_START_DATE = DATE_MIN
if DATE_LIST:
    # Try to find Jan 19 in the date list
    jan_19_dates = [d for d in DATE_LIST if d.month == 1 and d.year == 2019]
    if jan_19_dates:
        DEFAULT_START_DATE = jan_19_dates[0]
        DEFAULT_START_INDEX = DATE_LIST.index(DEFAULT_START_DATE)
    else:
        # If Jan 19 not found, use the first date that's Jan 2019 or later
        jan_2019_or_later = [d for d in DATE_LIST if d >= datetime(2019, 1, 1)]
        if jan_2019_or_later:
            DEFAULT_START_DATE = jan_2019_or_later[0]
            DEFAULT_START_INDEX = DATE_LIST.index(DEFAULT_START_DATE)

DEFAULT_END_DATE = DATE_MAX


def _map_tech_type_to_display(tech_type: str) -> str:
    """Map tech type technical names to display names."""
    mapping = {
        'Catalytic Cracking': 'FCC',
        'Fluid Catalytic Cracking': 'FCC',
        'Hydroskimming': 'HSK',
        'Hydrocracking': 'HYCRK',
        'Coking': 'Coker'
    }
    return mapping.get(tech_type, tech_type)


def _format_date_for_display(date):
    """Format date as 'Month Year' (e.g., 'Aug 07')"""
    if pd.isna(date) or date is None:
        return ""
    if isinstance(date, str):
        date = pd.to_datetime(date, errors='coerce')
    if pd.isna(date):
        return ""
    return date.strftime('%b %y')


def _index_to_date(index):
    """Convert slider index to date"""
    if not DATE_LIST or index < 0 or index >= len(DATE_LIST):
        return DATE_MIN
    return DATE_LIST[int(index)]


def _date_to_index(date):
    """Convert date to slider index"""
    if not DATE_LIST:
        return 0
    if isinstance(date, str):
        date = pd.to_datetime(date, errors='coerce')
    if pd.isna(date):
        return 0
    # Find closest date index
    try:
        idx = DATE_LIST.index(date)
        return idx
    except ValueError:
        # Find closest date
        for i, d in enumerate(DATE_LIST):
            if d >= date:
                return i
        return len(DATE_LIST) - 1


def _empty_figure(message: str, height: int = 400) -> go.Figure:
    """Create an empty figure with a message."""
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
        showlegend=False,
        paper_bgcolor="white",
        plot_bgcolor="white",
        height=height,
        margin=dict(l=0, r=0, t=5, b=0),
    )
    return fig


def _build_gpw_chart(df: pd.DataFrame, tech_type_internal: str, tech_type_display: str, selected_crudes: list = None, region: str = None, highlight_crude: str = None) -> go.Figure:
    """Build a Gross Product Worth chart for a specific technology type."""
    if df.empty:
        return _empty_figure(f"No data available for {tech_type_display}")
    
    fig = go.Figure()
    
    # Filter by tech type
    tech_df = df[df['TechType'] == tech_type_internal].copy()
    
    if tech_df.empty:
        return _empty_figure(f"No data available for {tech_type_display}")
    
    # Get unique crudes for this tech type
    available_crudes = sorted(tech_df['Crude'].unique())
    
    # Filter by selected crudes if provided
    if selected_crudes and 'ALL' not in selected_crudes:
        available_crudes = [c for c in available_crudes if c in selected_crudes]
    
    if not available_crudes:
        return _empty_figure(f"No crudes selected for {tech_type_display}")
    
    # Get region (use first available if not specified)
    if region is None and 'Region' in tech_df.columns and not tech_df.empty:
        region = tech_df['Region'].iloc[0] if not tech_df['Region'].isna().all() else "NWE"
    region_display = region if region else "NWE"
    
    # Color palette for different crudes
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    for idx, crude in enumerate(available_crudes):
        crude_df = tech_df[tech_df['Crude'] == crude].copy()
        crude_df = crude_df.sort_values('Date')
        
        if not crude_df.empty:
            # Use predefined color if available
            color = CRUDE_COLORS.get(crude, colors[idx % len(colors)])
            
            # Create custom hover text with all required fields
            hover_texts = []
            for _, row in crude_df.iterrows():
                date_str = _format_date_for_display(row['Date'])
                hover_text = (
                    f"Region: {region_display}<br>"
                    f"Crude: {crude}<br>"
                    f"Refining Complexity: {tech_type_display}<br>"
                    f"Date: {date_str}<br>"
                    f"Gross Product Worth: {row['Value']:.1f} ($/bbl)"
                )
                hover_texts.append(hover_text)
            
            line_width = 2
            line_color = color
            marker_size = 4
            opacity = 1.0

            if highlight_crude:
                if crude == highlight_crude:
                    line_width = 2   # Thinner highlighted line as requested
                    marker_size = 4  # Normal marker size
                else:
                    # Low opacity original colors for others
                    line_width = 1
                    marker_size = 2
                    opacity = 0.15  # Slightly increased for better visibility of "disabled" lines

            fig.add_trace(go.Scatter(
                x=crude_df['Date'],
                y=crude_df['Value'],
                mode='lines+markers',
                name=crude,
                line=dict(color=line_color, width=line_width),
                marker=dict(size=marker_size, color=line_color),
                opacity=opacity,
                customdata=hover_texts,
                hovertemplate="%{customdata}<extra></extra>"
            ))
    
    fig.update_layout(
        showlegend=False,
        xaxis=dict(
            # title="Date",
            showgrid=True,
            gridcolor="#e0e0e0",
            linecolor="#cccccc", # Added x-axis line color
            tickangle=90,
            dtick="M7",  # Show ticks every 7 months
            tickformat="%b %y" # Format as "Jan 19"
        ),
        yaxis=dict(
            title="Gross Product Worth ($/bbl)",
            showgrid=True,
            gridcolor="#e0e0e0"
        ),
        hovermode='closest',
        height=350,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=60, r=20, t=40, b=70),
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#999999",
            font=dict(
                size=12,
                family="Arial, sans-serif",
                color="#000000"
            ),
            align="left"
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=3.01,
            xanchor="right",
            x=0.98,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#dee2e6",
            borderwidth=1
        )
    )
    return fig


def _build_incremental_margins_chart(df: pd.DataFrame, tech_type_internal: str, tech_type_display: str, selected_crudes: list = None, region: str = None, highlight_crude: str = None) -> go.Figure:
    """Build an Incremental Margins chart for a specific technology type."""
    if df.empty:
        return _empty_figure(f"No data available for {tech_type_display}")
    
    fig = go.Figure()
    
    # Filter by tech type
    tech_df = df[df['TechType'] == tech_type_internal].copy()
    
    if tech_df.empty:
        return _empty_figure(f"No data available for {tech_type_display}")
    
    # Get unique crudes for this tech type
    available_crudes = sorted(tech_df['Crude'].unique())
    
    # Filter by selected crudes if provided
    if selected_crudes and 'ALL' not in selected_crudes:
        available_crudes = [c for c in available_crudes if c in selected_crudes]
    
    if not available_crudes:
        return _empty_figure(f"No crudes selected for {tech_type_display}")
    
    # Get region (use first available if not specified)
    if region is None and 'Region' in tech_df.columns and not tech_df.empty:
        region = tech_df['Region'].iloc[0] if not tech_df['Region'].isna().all() else "NWE"
    region_display = region if region else "NWE"
    
    # Color palette for different crudes
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    for idx, crude in enumerate(available_crudes):
        crude_df = tech_df[tech_df['Crude'] == crude].copy()
        crude_df = crude_df.sort_values('Date')
        
        if not crude_df.empty:
            # Use predefined color if available
            color = CRUDE_COLORS.get(crude, colors[idx % len(colors)])
            
            # Create custom hover text with all required fields
            hover_texts = []
            for _, row in crude_df.iterrows():
                date_str = _format_date_for_display(row['Date'])
                hover_text = (
                    f"Region: {region_display}<br>"
                    f"Crude: {crude}<br>"
                    f"Refining Complexity: {tech_type_display}<br>"
                    f"Date: {date_str}<br>"
                    f"Incremental Margins: {row['Value']:.1f} ($/bbl)"
                )
                hover_texts.append(hover_text)
            
            line_width = 2
            line_color = color
            marker_size = 4
            opacity = 1.0

            if highlight_crude:
                if crude == highlight_crude:
                    line_width = 2   # Thinner highlighted line as requested
                    marker_size = 4  # Normal marker size
                else:
                    # Low opacity original colors for others
                    line_width = 1
                    marker_size = 2
                    opacity = 0.15  # Slightly increased for better visibility of "disabled" lines

            fig.add_trace(go.Scatter(
                x=crude_df['Date'],
                y=crude_df['Value'],
                mode='lines+markers',
                name=crude,
                line=dict(color=line_color, width=line_width),
                marker=dict(size=marker_size, color=line_color),
                opacity=opacity,
                customdata=hover_texts,
                hovertemplate="%{customdata}<extra></extra>"
            ))
    
    fig.update_layout(
        showlegend=False,
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor="#e0e0e0",
            linecolor="#cccccc", # Added x-axis line color
            tickangle=90,
            dtick="M7",  # Show ticks every 7 months
            tickformat="%b %y" # Format as "Jan 19"
        ),
        yaxis=dict(
            title="Incremental Margins ($/bbl)",
            showgrid=True,
            gridcolor="#e0e0e0",
            zeroline=False # Hide the zero line
        ),
        hovermode='closest',
        height=350,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=60, r=20, t=40, b=70),
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#999999",
            font=dict(
                size=12,
                family="Arial, sans-serif",
                color="#000000"
            ),
            align="left"
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=3.01,
            xanchor="right",
            x=0.98,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#dee2e6",
            borderwidth=1
        )
    )
    return fig


def _prepare_data_table(df: pd.DataFrame, start_date, end_date, region, selected_crudes=None, selected_tech_types=None, highlight_crude: str = None) -> tuple:
    """Prepare data for the complex data table with multi-level headers.
    
    Args:
        df: DataFrame with the data
        start_date: Start date for filtering
        end_date: End date for filtering
        region: Region filter
        selected_crudes: List of selected crudes (None means all)
        selected_tech_types: List of selected tech types (None means all)
    
    Returns:
        tuple: (columns, data, tooltip_data) where columns is list of hierarchical column definitions,
               data is list of records, and tooltip_data is list of tooltip records for hover
    """
    if df.empty:
        return [], [], [], []
    
    # Filter by date range
    filtered_df = df[
        (df['Date'] >= start_date) &
        (df['Date'] <= end_date)
    ].copy()
    
    # Filter by region if Region column exists
    if region and 'Region' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Region'] == region]
    
    if filtered_df.empty:
        return [], [], [], []
    
    CRUDE_ORDER = selected_crudes
    DATA_TYPES = ['GPW', 'Refining Margin']
    TECH_TYPES = selected_tech_types
    
    # Use MonthDateDisplay if available, otherwise format from Date
    if 'MonthDateDisplay' in filtered_df.columns:
        filtered_df['DateStr'] = filtered_df['MonthDateDisplay']
    else:
        filtered_df['DateStr'] = filtered_df['Date'].dt.strftime('%b %y')
    
    # Sort by date descending (most recent first)
    filtered_df = filtered_df.sort_values(['Date'], ascending=[False])
    
    # Get unique dates in sorted order (most recent first)
    unique_dates = filtered_df.sort_values('Date', ascending=False)['DateStr'].unique().tolist()
    
    # Create hierarchical columns structure
    columns = [
        {
            'name': ['', '', 'Date'],
            'id': 'DateStr',
            'type': 'text',
            'style_cell': {'fontWeight': 'bold'}
        }
    ]
    
    # Create columns for each combination
    for data_type in DATA_TYPES:
        for tech_type in TECH_TYPES:
            for crude in CRUDE_ORDER:
                col_id = f"{data_type}_{tech_type}_{crude}".replace(' ', '_').replace('/', '_')
                columns.append({
                    'name': [data_type, tech_type, crude],
                    'id': col_id,
                    'type': 'numeric',
                    'format': {'specifier': '.2f'}
                })
    
    # Create data records and tooltip data
    data = []
    tooltip_data = []
    
    for date_str in unique_dates:
        record = {'DateStr': date_str}
        tooltip_row = {'DateStr': None}  # No tooltip for date column
        
        # Get all values for this date
        date_data = filtered_df[filtered_df['DateStr'] == date_str]
        
        # Get the actual date value for tooltip formatting
        actual_date = None
        if not date_data.empty:
            actual_date = date_data.iloc[0].get('Date')
            if pd.notna(actual_date):
                actual_date = _format_date_for_display(actual_date)
        
        # Create a lookup dictionary: (DataType, TechType, Crude) -> (Value, Row)
        value_lookup = {}
        for _, row in date_data.iterrows():
            key = (
                str(row.get('DataType', '')).strip(),
                str(row.get('TechType', '')).strip(),
                str(row.get('Crude', '')).strip()
            )
            val = row.get('Value')
            if pd.notna(val):
                value_lookup[key] = (float(val), row)
            else:
                value_lookup[key] = (None, row)
        
        # Populate record only with columns that exist (filtered by selection)
        for data_type in DATA_TYPES:
            for tech_type in TECH_TYPES:
                for crude in CRUDE_ORDER:
                    col_id = f"{data_type}_{tech_type}_{crude}".replace(' ', '_').replace('/', '_')
                    key = (data_type, tech_type, crude)
                    
                    # Map tech type to display name
                    tech_display = "FCC" if tech_type == "Catalytic Cracking" else "HSK" if tech_type == "Hydroskimming" else tech_type
                    
                    if key in value_lookup:
                        record[col_id] = value_lookup[key][0]
                        # Create tooltip text (each field on its own line, one by one vertically)
                        # Format must be a dict with 'value' and 'type' keys
                        # Use markdown type to properly render line breaks
                        if value_lookup[key][0] is not None and actual_date:
                            # Format each field on a separate line for vertical display
                            # Use double space + newline for markdown line breaks
                            tooltip_text = (
                                f"Crude: {crude}  \n" +
                                f"Data Type: {data_type}  \n" +
                                f"Refining Complexity: {tech_display}  \n" +
                                f"Date: {actual_date}"
                            )
                            tooltip_row[col_id] = {
                                'value': tooltip_text,
                                'type': 'markdown'
                            }
                        else:
                            tooltip_row[col_id] = None
                    else:
                        record[col_id] = None
                        tooltip_row[col_id] = None
        
        data.append(record)
        tooltip_data.append(tooltip_row)
    
    # Identify columns that are entirely empty (all None)
    # Exclude 'DateStr' from this check as it always has data
    all_column_ids = [col['id'] for col in columns if col['id'] != 'DateStr']
    
    # Create a mapping from col_id to a list of its values across all rows
    column_values = {col_id: [] for col_id in all_column_ids}
    for row_data in data:
        for col_id in all_column_ids:
            column_values[col_id].append(row_data.get(col_id))
            
    # Determine which columns are empty
    empty_column_ids = [col_id for col_id, values in column_values.items() if all(v is None for v in values)]
    
    # Filter out empty columns from the columns definition
    filtered_columns = [col for col in columns if col['id'] not in empty_column_ids]
    
    # Filter out empty columns from the data
    filtered_data = []
    for row_data in data:
        filtered_row = {k: v for k, v in row_data.items() if k not in empty_column_ids}
        filtered_data.append(filtered_row)
        
    # Filter out empty columns from the tooltip data
    filtered_tooltip_data = []
    for row_tooltip in tooltip_data:
        filtered_tooltip_row = {k: v for k, v in row_tooltip.items() if k not in empty_column_ids}
        filtered_tooltip_data.append(filtered_tooltip_row)
    
    styles_data_conditional = [
        # Always make the DateStr column bold as requested
        {
            'if': {'column_id': 'DateStr'},
            'fontWeight': 'bold',
            'color': '#000000',
            'textAlign': 'center'
        }
    ]
    
    if highlight_crude:
        # All columns except DateStr should be dimmed by default when highlighting is active
        non_highlighted_cols = [col['id'] for col in filtered_columns if col['id'] != 'DateStr']
        styles_data_conditional.append({
            'if': {'column_id': non_highlighted_cols},
            'color': '#aaaaaa',  # Slightly darker gray for better visibility
            'opacity': 0.5       # Increased opacity for "disabled" look
        })

        for data_type in DATA_TYPES:
            for tech_type in TECH_TYPES:
                # Construct the column ID for the highlighted crude
                col_id = f"{data_type}_{tech_type}_{highlight_crude}".replace(' ', '_').replace('/', '_')
                styles_data_conditional.append({
                    'if': {'column_id': col_id},
                    'backgroundColor': '#fffde7',  # Subtler yellow highlight (Lemon Chiffon variant)
                    'color': '#000000',           # Ensure text remains black/visible
                    'fontWeight': 'bold',         # Make the highlighted column text bold
                    'border': '1px solid #3498db'  # Consistent blue border
                })
    
    return filtered_columns, filtered_data, filtered_tooltip_data, styles_data_conditional


def create_layout():
    """Create the GPW Margins layout with filters and charts."""
    return html.Div([
        # Store to track initial load state
        dcc.Store(id='gpw-initial-load', data=True),
        dcc.Store(id='gpw-crude-filter-previous', data=None),
        dcc.Store(id='gpw-refining-complexity-filter-previous', data=None),
        dcc.Store(id='gpw-available-tech-types', data=[]),
        dcc.Store(id='gpw-available-crudes-for-region', data=[]),
        dcc.Store(id='gpw-highlight-crude-store', data=None),
        dcc.Store(id='gpw-selected-tech-type-store', data=None),

        # CSS styling for rc-slider using dcc.Markdown
        html.Div(
            dcc.Markdown(
                """
                <style>
                /* === RC-Slider Styling for Date Range === */
                .rc-slider-handle-1 {
                    width: 10px !important;
                    height: 14px !important;
                    background: #FFFFFF !important;
                    border: 2px solid #6E6E6E !important;
                    border-radius: 0 7px 7px 0 !important;
                    margin-top: -6px !important;
                    box-shadow: none !important;
                }
                .rc-slider-handle-2 {
                    width: 10px !important;
                    height: 14px !important;
                    background: #FFFFFF !important;
                    border: 2px solid #6E6E6E !important;
                    border-radius: 7px 0 0 7px !important;
                    margin-top: -6px !important;
                    box-shadow: none !important;
                }
                .rc-slider-handle {
                    width: 10px !important;
                    height: 14px !important;
                    background-color: #FFFFFF !important;
                    border: 2px solid #6E6E6E !important;
                    margin-top: -6px !important;
                    box-shadow: none !important;
                    cursor: pointer !important;
                }
                .rc-slider-handle:hover {
                    border-color: #4D4D4D !important;
                }
                .rc-slider-handle:active {
                    border-color: #3A3A3A !important;
                }
                .rc-slider-track,
                .rc-slider-track,
                .rc-slider-track-1,
                .rc-slider-track-2,
                div[class*="rc-slider-track"] {
                    background: #6E6E6E !important; /* Dark gray for the active range (Start to End) */
                    height: 4px !important;
                }
                .rc-slider-rail {
                    background: #D3D3D3 !important; /* Light gray for the inactive range (Min to Start) */
                    height: 4px !important;
                }
                /* Date range input fields */
                #gpw-date-range-min-input,
                #gpw-date-range-max-input {
                    border: none !important;
                    background: transparent !important;
                    padding: 0 !important;
                    font-size: 12px !important;
                    color: #1b365d !important;
                    width: auto !important;
                    min-width: 80px !important;
                    max-width: 150px !important;
                    height: 18px !important;
                    line-height: 18px !important;
                    outline: none !important;
                    box-shadow: none !important;
                    top: 0 !important;
                    vertical-align: top !important;
                    margin: 0 !important;
                }
                #gpw-date-range-min-input {
                    left: 0 !important;
                    text-align: left !important;
                }
                #gpw-date-range-max-input {
                    text-align: right !important;
                    float: right !important;
                    margin-right: 0 !important;
                    padding-right: 0 !important;
                    cursor: default !important;
                    pointer-events: none !important;
                }
                #gpw-date-range-min-input:hover {
                    border: 1px solid #ccc !important;
                    background: #ffffff !important;
                    padding: 1px 3px !important;
                }
                #gpw-date-range-min-input:focus {
                    border: 1px solid #999 !important;
                    background: #ffffff !important;
                    padding: 1px 3px !important;
                }
                #gpw-date-range-max-input:hover,
                #gpw-date-range-max-input:focus {
                    border: 0px solid #dee2e6 !important;
                    background: unset !important;
                    padding: 0 !important;
                }
                div[id*="date-range-slider"] {
                    margin-left: 0 !important;
                    padding-left: 0 !important;
                    margin-right: 0 !important;
                    padding-right: 0 !important;
                }
                .rc-slider {
                    margin-left: 0 !important;
                    padding-left: 0 !important;
                    margin-right: 0 !important;
                    padding-right: 0 !important;
                    width: 100% !important;
                    box-sizing: border-box !important;
                }
                .rc-slider-rail {
                    margin-left: 0 !important;
                    margin-right: 0 !important;
                    width: 100% !important;
                    box-sizing: border-box !important;
                }
                /* Single slider handle styling */
                div[id*="date-range-slider"] .rc-slider-handle {
                    cursor: grab !important;
                }
                div[id*="date-range-slider"] .rc-slider-handle:active {
                    cursor: grabbing !important;
                }
                
                /* DataTable Tooltip Font Size */
                #gpw-data-table .dash-table-tooltip,
                .dash-table-tooltip {
                    font-size: 12px !important;
                }
                
                /* DataTable Column and Row Selection Styling */
                #gpw-data-table .dash-spreadsheet-container {
                    cursor: pointer;
                    transition: background-color 0.2s ease;
                }
                #gpw-data-table .dash-spreadsheet-container th.column-selected {
                    background-color: #b3d9ff !important;
                    color: #1b365d !important;
                    font-weight: bold !important;
                }
                #gpw-data-table .dash-spreadsheet-container td.column-cell-selected {
                    background-color: #b3d9ff !important;
                    border: none !important;
                    font-weight: 600 !important;
                    color: #1b365d !important;
                    opacity: 1 !important;
                }
                #gpw-data-table .dash-spreadsheet-container td.row-cell-selected {
                    background-color: #b3d9ff !important;
                    border: none !important;
                    font-weight: 600 !important;
                    color: #1b365d !important;
                    opacity: 1 !important;
                }
                #gpw-data-table .dash-spreadsheet-container.column-selection-active td:not([data-dash-column="DateStr"]):not(.column-cell-selected) {
                    opacity: 0.3 !important;
                }
                #gpw-data-table .dash-spreadsheet-container.row-selection-active tbody tr:not(.row-selected) td:not([data-dash-column="DateStr"]) {
                    opacity: 0.3 !important;
                }
                #gpw-data-table .dash-spreadsheet-container.row-selection-active tbody tr.row-selected td.row-cell-selected {
                    opacity: 1 !important;
                    background-color: #b3d9ff !important;
                    color: #1b365d !important;
                    font-weight: 600 !important;
                    border: none !important;
                }
                </style>
                """,
                dangerously_allow_html=True
            ),
            style={"display": "none"}
        ),
        html.Div([
            html.H2(
                "Gross Product Worth and Margins",
                style={
                    'color': '#fe5000',
                    'textAlign': 'center',
                    'marginBottom': '5px',
                    'fontSize': '24px',
                    'fontWeight': 'bold'
                }
            ),
            
            # Filters Section
            html.Div([
                html.Div([
                    html.Label(
                        "Date Range",
                        style={
                            'fontFamily': 'Arial',
                            'fontSize': '14px',
                            'lineHeight': '12px',
                            'color': '#2c3e50',
                            'fontWeight': 'bold',
                            'fontStyle': 'normal',
                            'textDecoration': 'none',
                            'marginBottom': '2px'
                        }
                    ),
                    html.Div([
                        html.Div([
                            html.Label(
                                id="gpw-date-range-min-label",
                                children=_format_date_for_display(DEFAULT_START_DATE),
                                style={'display': 'inline-block', 'color': '#1b365d', 'fontSize': '11px', 'fontFamily': 'Arial', 'lineHeight': '12px', 'fontWeight': 'bold'}
                            ),
                            html.Label(
                                id="gpw-date-range-max-label",
                                children=_format_date_for_display(DEFAULT_END_DATE),
                                style={'float': 'right', 'color': '#1b365d', 'fontSize': '11px', 'fontFamily': 'Arial', 'lineHeight': '12px', 'fontWeight': 'bold'}
                            ),
                        ], style={'width': '100%', 'marginBottom': '2px', 'position': 'relative'}),
                        html.Div([
                            dcc.RangeSlider(
                                id="gpw-date-range-slider",
                                min=0,
                                max=max(len(DATE_LIST) - 1, 0) if DATE_LIST else 0,
                                step=1,
                                value=[DEFAULT_START_INDEX, DEFAULT_END_INDEX],
                                marks=None,
                            ),
                        ], style={'width': '100%', 'margin': '0', 'padding': '0'}),
                    ], style={'width': '100%', 'position': 'relative'}),
                ], className='col-md-4', style={'padding': '10px'}),
                
                html.Div([
                    html.Label(
                        "Refining Center",
                        style={
                            'fontWeight': 'bold',
                            'color': '#2c3e50',
                            'fontSize': '14px',
                            'marginBottom': '2px'
                        }
                    ),
                    dcc.Dropdown(
                        id='gpw-region-filter',
                        options=[{'label': r, 'value': r} for r in REGIONS],
                        value=DEFAULT_REGION,
                        clearable=False,
                        style={'width': '100%'}
                    )
                ], className='col-md-8', style={'padding': '10px'})
            ], className='row', style={
                'backgroundColor': '#f8f9fa',
                'padding': '2px 20px',
                'marginBottom': '0px',
                'borderRadius': '5px'
            })
        ], style={'padding': '0px 20px 0px 20px'}),
        
        # Gross Product Worth Section
        html.Div([
            html.Div([
                html.Div([
                    html.Div([
                        html.H3(
                            id='gpw-gpw-title',
                            children="NWE - Gross Product Worth ($/bbl)",
                            style={
                                'color': '#fe5000',
                                'textAlign': 'center',
                                'marginBottom': '5px',
                                'fontSize': '16px',
                                'fontWeight': 'bold',
                                'flexGrow': 1 # Allow title to take available space
                            }
                        ),
                        html.Div(
                            dcc.Dropdown(
                                id='gpw-dashboard-export-dropdown',
                                options=[
                                    {'label': 'Export to PDF', 'value': 'pdf'},
                                    {'label': 'Export to PNG', 'value': 'png'},
                                    {'label': 'Export to CSV', 'value': 'raw_data_csv'}
                                ],
                                placeholder='Export Data',
                                style={
                                    'width': '250px',
                                    'marginRight': '10px',
                                    'fontSize': '13px',
                                    'color': '#2c3e50',
                                    'display': 'inline-block'
                                },
                                clearable=False
                            ),
                            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'flex-end', 'paddingRight': '15px'}
                        ),
                    ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'width': '100%', 'padding': '0 15px'}),
                    dcc.Download(id="gpw-download-dashboard-content"),
                    dcc.Download(id="gpw-download-chart-png"),
                    dcc.Download(id="gpw-download-raw-data-csv"),
                    
                    html.Div([
                        html.Div([
                            html.Div([
                                html.H4(
                                    id='gpw-catalytic-cracking-chart-title',
                                    children="Catalytic Cracking",
                                    style={
                                        'color': '#1b365d',
                                        'textAlign': 'center',
                                        'marginBottom': '8px',
                                        'fontSize': '16px',
                                        'fontWeight': 'bold',
                                        'flexGrow': 1
                                    }
                                ),
                                dcc.Download(id={'type': 'download-chart-content', 'index': 'gpw-catalytic-cracking-pdf'}),
                                dcc.Download(id={'type': 'download-chart-content', 'index': 'gpw-catalytic-cracking-png'}),
                                dcc.Download(id={'type': 'download-chart-content', 'index': 'gpw-catalytic-cracking-csv'}),
                            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'width': '100%', 'padding': '0 15px'}),
                            dcc.Loading(
                                id="loading-cat-cracking",
                                type="default",
                                color="#fe5000",
                                children=dcc.Graph(id='gpw-catalytic-cracking-chart',
                                style={'height': '550px'},
                                config={'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian', 'toggleHover', 'toggleSpikelines', 'sendDataToCloud', 'hoverClosestGl2d', 'hoverClosestPie', 'resetViewBag'], 'displaylogo': False})
                            ),
                        ], className='col-md-6', style={'padding': '5px 15px'}),
                        
                        html.Div([
                            html.Div([
                                html.H4(
                                    id='gpw-hydroskimming-chart-title',
                                    children="Hydroskimming",
                                    style={
                                        'color': '#1b365d',
                                        'textAlign': 'center',
                                        'marginBottom': '8px',
                                        'fontSize': '16px',
                                        'fontWeight': 'bold',
                                        'flexGrow': 1
                                    }
                                ),
                            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'width': '100%', 'padding': '0 15px'}),
                            dcc.Loading(
                                id="loading-hydroskimming",
                                type="default",
                                color="#fe5000",
                                children=dcc.Graph(id='gpw-hydroskimming-chart',
                                style={'height': '550px'},
                                config={'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian', 'toggleHover', 'toggleSpikelines', 'sendDataToCloud', 'hoverClosestGl2d', 'hoverClosestPie', 'resetViewBag'], 'displaylogo': False})
                            ),
                        ], className='col-md-6', style={'padding': '0px 15px'})
                    ], className='row')
                ], className='col-md-10', style={'padding': '0px 15px'}),
                
                # Right Side Filters
                html.Div([
                    html.Label(
                        "Crude",
                        style={
                            'fontWeight': 'bold',
                            'color': '#2c3e50',
                            'fontSize': '14px',
                            'marginBottom': '8px'
                        }
                    ),
                    dcc.Checklist(
                        id='gpw-crude-filter',
                        options=[{'label': 'ALL', 'value': 'ALL'}] + _crude_filter_options(CRUDES),
                        value=['ALL'] + CRUDES.copy() if CRUDES else ['ALL'],
                        style={
                            'display': 'flex',
                            'flexDirection': 'column',
                            'gap': '2px',
                            'marginTop': '2px',
                            'marginBottom': '20px',
                        },
                        labelStyle={
                            'display': 'flex',
                            'alignItems': 'center',
                            'gap': '2px',
                            'padding': '2px 2px',
                            'borderRadius': '4px',
                            'border': '0px solid #dfe3eb',
                            'backgroundColor': '#ffffff',
                            'width': '100%',
                            'boxShadow': '0 1px 2px rgba(0,0,0,0.05)',
                            'cursor': 'pointer',
                            'transition': 'background-color 0.2s ease',
                            'userSelect': 'none',
                            'fontSize': '12px',
                        },
                        inputStyle={
                            'marginRight': '12px',
                            'width': '18px',
                            'height': '18px',
                            'cursor': 'pointer',
                        },
                    ),
                    
                    html.Label(
                        "Refining Complexity",
                        style={
                            'fontWeight': 'bold',
                            'color': '#2c3e50',
                            'fontSize': '14px',
                            'marginBottom': '8px',
                            'marginTop': '10px'
                        }
                    ),
                    dcc.Checklist(
                        id='gpw-refining-complexity-filter',
                        options=[],
                        value=[],
                        style={
                            'display': 'flex',
                            'flexDirection': 'column',
                            'gap': '2px',
                            'marginTop': '2px',
                            'marginBottom': '20px',
                        },
                        labelStyle={
                            'display': 'flex',
                            'alignItems': 'center',
                            'gap': '2px',
                            'padding': '2px 2px',
                            'borderRadius': '4px',
                            'border': '0px solid #dfe3eb',
                            'backgroundColor': '#ffffff',
                            'width': '100%',
                            'boxShadow': '0 1px 2px rgba(0,0,0,0.05)',
                            'cursor': 'pointer',
                            'transition': 'background-color 0.2s ease',
                            'userSelect': 'none',
                            'fontSize': '12px',
                        },
                        inputStyle={
                            'marginRight': '12px',
                            'width': '18px',
                            'height': '18px',
                            'cursor': 'pointer',
                        },
                    ),
                    
                    html.Label(
                        "Crude",
                        id='gpw-crude-legend-title',
                        style={
                            'fontWeight': 'bold',
                            'color': '#2c3e50',
                            'fontSize': '12px',
                            'marginBottom': '8px',
                            'marginTop': '10px'
                        }
                    ),
                    # Crude Legend with row click selection (no checkboxes)
                    html.Div([], id='gpw-crude-legend-container'),
                    # Hidden checklist to store selected values
                    dcc.Checklist(
                        id='gpw-crude-legend',
                        options=[{'label': c, 'value': c} for c in CRUDES],
                        value=CRUDES.copy() if CRUDES else [],
                        style={'display': 'none'}
                    ),
                ], className='col-md-2', style={
                    'padding': '15px 20px',
                    'border': '0px solid #dfe3eb',
                    'borderRadius': '6px',
                    'backgroundColor': '#f8f9fb',
                    'height': '100%',
                    'boxShadow': '0 2px 6px rgba(0,0,0,0.05)',
                    'marginLeft': '0',
                }),
            ], className='row')
        ], style={'padding': '0px 20px', 'marginBottom': '5px'}),
        
        # Incremental Margins Section
        html.Div([
            html.Div([
                html.Div([
                    html.Div([
                        html.H3(
                            id='gpw-margins-title',
                            children="NWE - Incremental Margins ($/bbl)",
                            style={
                                'color': '#fe5000',
                                'textAlign': 'left',
                                'marginBottom': '10px',
                                'fontSize': '16px',
                                'fontWeight': 'bold',
                                'flexGrow': 1
                            }
                        ),
                        html.Div(
                            html.Button(
                                'Export to CSV',
                                id='gpw-incremental-margins-export-button',
                                n_clicks=0,
                                style={
                                    'backgroundColor': 'white',
                                    'color': '#2c3e50',
                                    'border': '1px solid #dee2e6',
                                    'padding': '8px 15px',
                                    'borderRadius': '5px',
                                    'cursor': 'pointer',
                                    'fontSize': '13px',
                                    'marginRight': '10px',
                                    'display': 'inline-block'
                                }
                            ),
                            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'flex-end', 'paddingRight': '15px'}
                        ),
                        dcc.Download(id="gpw-download-incremental-margins-csv"),
                    ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'width': '100%', 'padding': '0 15px'}),
                    
                    html.Div([
                        html.Div([
                            html.H4(
                                id='gpw-incremental-catalytic-cracking-chart-title',
                                children="Catalytic Cracking",
                                style={
                                    'color': '#1b365d',
                                    'textAlign': 'center',
                                    'marginBottom': '5px',
                                    'fontSize': '16px',
                                    'fontWeight': 'bold'
                                }
                            ),
                            html.Div([
                            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'width': '100%', 'padding': '0 15px'}),
                            dcc.Loading(
                                id="loading-inc-cat",
                                type="default",
                                color="#fe5000",
                                children=dcc.Graph(id='gpw-incremental-catalytic-chart',
                                    style={'height': '550px'},
                                    config={'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian', 'toggleHover', 'toggleSpikelines', 'sendDataToCloud', 'hoverClosestGl2d', 'hoverClosestPie', 'resetViewBag'], 'displaylogo': False})
                            ),
                        ], className='col-md-6', style={'padding': '5px 15px'}),
                        
                        html.Div([
                            html.Div([
                                html.H4(
                                    id='gpw-incremental-hydroskimming-chart-title',
                                    children="Incremental Hydroskimming",
                                    style={
                                        'color': '#1b365d',
                                        'textAlign': 'center',
                                        'marginBottom': '5px',
                                        'fontSize': '16px',
                                        'fontWeight': 'bold',
                                        'flexGrow': 1
                                    }
                                ),
                            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'width': '100%', 'padding': '0 15px'}),
                            dcc.Loading(
                                id="loading-inc-hydro",
                                type="default",
                                color="#fe5000",
                                children=dcc.Graph(id='gpw-incremental-hydroskimming-chart',
                                    style={'height': '550px'},
                                    config={'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian', 'toggleHover', 'toggleSpikelines', 'sendDataToCloud', 'hoverClosestGl2d', 'hoverClosestPie', 'resetViewBag'], 'displaylogo': False})
                            ),
                        ], className='col-md-6', style={'padding': '5px 15px'})
                    ], className='row')
                ], className='col-md-10', style={'padding': '5px 15px'}),
                
                # Empty column to maintain layout (filters already shown above)
                html.Div([
                ], className='col-md-2', style={'padding': '0px 15px'}),
            ], className='row')
        ], style={'padding': '0px 20px', 'marginBottom': '0px'}),
        
        # Data Table Section
        html.Div([
            html.Div([
                html.Div([
                    html.Div(
                        id='gpw-data-table-container',
                        children=[
                            html.H4(
                                id='gpw-data-table-title',
                                children="Data Table",
                                style={
                                    'color': '#1b365d',
                                    'textAlign': 'center',
                                    'marginBottom': '5px',
                                    'fontSize': '16px',
                                    'fontWeight': 'bold',
                                    'flexGrow': 1 # Allow title to take available space
                                }
                            ),
                            html.Div([ # Existing div for button
                                html.Button(
                                    'Export to CSV',
                                    id='btn-export-gpw-data-table-csv',
                                    n_clicks=0,
                                    style={
                                        'backgroundColor': 'white',
                                        'color': '#2c3e50',
                                        'border': '1px solid #dee2e6',
                                        'padding': '8px 15px',
                                        'borderRadius': '4px',
                                        'cursor': 'pointer',
                                        'fontSize': '13px',
                                        'marginRight': '10px',
                                        'display': 'inline-block'
                                    }
                                ),
                                dcc.Download(id="download-gpw-data-table-csv"),
                            ], style={'display': 'flex', 'justifyContent': 'flex-end', 'padding': '0 15px 15px 0'}),
                            dcc.Loading(
                                id="loading-data-table",
                                type="default",
                                color="#fe5000",
                                children=dash_table.DataTable(
                                id='gpw-data-table',
                            columns=[],  # Will be populated by callback
                            data=[],     # Will be populated by callback
                            style_table={
                                'overflowX': 'auto',
                                'overflowY': 'auto',
                                'maxHeight': '600px',
                                'backgroundColor': 'white',
                                'border': '1px solid #dee2e6'
                            },
                            style_cell={
                                'textAlign': 'right',
                                'padding': '8px',
                                'fontSize': '11px',
                                'fontFamily': 'Arial, sans-serif',
                                'border': '1px solid #dee2e6',
                                'minWidth': '70px',
                                'whiteSpace': 'nowrap'
                            },
                            style_header={
                                'backgroundColor': '#f8f9fa',
                                'fontWeight': 'bold',
                                'color': '#1b365d',
                                'textAlign': 'center',
                                'border': '1px solid #dee2e6',
                                'padding': '8px',
                                'fontSize': '12px',
                            },
                            style_cell_conditional=[
                                {
                                    'if': {'column_id': 'DateStr'},
                                    'textAlign': 'left',
                                    'fontWeight': 'bold',
                                    'minWidth': '80px',
                                    'backgroundColor': '#f8f9fa',
                                    'fontSize': '13px' # Adjusted font size for DateStr column
                                }
                            ],
                            style_data_conditional=[
                                {
                                    'if': {'row_index': 'odd'},
                                    'backgroundColor': '#f9fbfd'
                                },
                                {
                                    'if': {'filter_query': '{DateStr} != ""'},
                                    'backgroundColor': 'white'
                                }
                            ],
                            merge_duplicate_headers=True,
                            page_action='none',
                            sort_action='native',
                            tooltip_data=[],  # Will be populated by callback
                            tooltip_duration=None,
                            css=[
                                {
                                    'selector': '#gpw-data-table .dash-table-tooltip',
                                    'rule': 'font-size: 12px !important;'
                                },
                                {
                                    'selector': '.dash-table-tooltip',
                                    'rule': 'font-size: 12px !important;'
                                    },
                                    {
                                        'selector': '#gpw-data-table .dash-spreadsheet-container',
                                        'rule': 'cursor: pointer; transition: background-color 0.2s ease;'
                                    },
                                    {
                                        'selector': '#gpw-data-table .dash-spreadsheet-container th.column-selected',
                                        'rule': 'background-color: #b3d9ff !important; color: #1b365d !important; font-weight: bold !important;'
                                    },
                                    {
                                        'selector': '#gpw-data-table .dash-spreadsheet-container td.column-cell-selected',
                                        'rule': 'background-color: #b3d9ff !important; border: none !important; font-weight: 600 !important; color: #1b365d !important; opacity: 1 !important;'
                                    },
                                    {
                                        'selector': '#gpw-data-table .dash-spreadsheet-container td.row-cell-selected',
                                        'rule': 'background-color: #b3d9ff !important; border: none !important; font-weight: 600 !important; color: #1b365d !important; opacity: 1 !important;'
                                    },
                                    {
                                        'selector': '#gpw-data-table .dash-spreadsheet-container.column-selection-active td:not([data-dash-column="DateStr"]):not(.column-cell-selected)',
                                        'rule': 'opacity: 0.3 !important;'
                                    },
                                    {
                                        'selector': '#gpw-data-table .dash-spreadsheet-container.row-selection-active tbody tr:not(.row-selected) td',
                                        'rule': 'opacity: 0.3 !important;'
                                    },
                                    {
                                        'selector': '#gpw-data-table .dash-spreadsheet-container.row-selection-active tbody tr.row-selected td.row-cell-selected',
                                        'rule': 'opacity: 1 !important; background-color: #b3d9ff !important; color: #1b365d !important; font-weight: 600 !important; border: none !important;'
                                    }
                                ]
                            )
                            )
                        ]
                    )
                ], className='col-md-10', style={'padding': '15px'}),
                
                # Empty column to maintain layout (filters already shown above)
                html.Div([
                ], className='col-md-2', style={'padding': '15px'}),
            ], className='row')
        ], style={'padding': '20px', 'marginBottom': '30px'}),
        
        # Store selected column for highlighting
        dcc.Store(id='gpw-selected-column', data=None),
        
        # Dummy output for client-side callback
        html.Div(id='gpw-table-dummy-output', style={'display': 'none'}),
        
        # Hidden anchor for clientside callback to enhance data table
        html.Div(id='gpw-table-enhancer-anchor', style={'display': 'none'})
    ], className='tab-content', style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh'})


def register_callbacks(dash_app, server):
    """Register all callbacks for GPW Margins."""
    
    # Mark initial load as complete after first render and initialize previous values
    @dash_app.callback(
        Output('gpw-initial-load', 'data', allow_duplicate=True),
        Output('gpw-crude-filter-previous', 'data', allow_duplicate=True),
        Output('gpw-refining-complexity-filter-previous', 'data', allow_duplicate=True),
        Input('current-submenu', 'data'),
        prevent_initial_call='initial_duplicate'
    )
    def mark_initial_load_complete(submenu):
        """Mark that initial load is complete after first render and initialize previous values."""
        if submenu == 'gpw-margins':
            # Set initial previous values to match initial filter values
            initial_crude = ['ALL'] + CRUDES.copy() if CRUDES else ['ALL']
            initial_tech = ['ALL'] + TECH_TYPES.copy() if TECH_TYPES else ['ALL']
            return False, initial_crude, initial_tech  # Initial load complete
        return dash.no_update, dash.no_update, dash.no_update
    
    # Clientside callback for tech type header click handling
    dash_app.clientside_callback(
        """
        function(_trigger) {
            try {
                setTimeout(function() {
                    const table = document.querySelector('#gpw-data-table');
                    if (!table) return;
                    
                    const container = table.querySelector('.dash-spreadsheet-container');
                    if (!container) return;
                    
                    let selectedTechType = null;
                    
                    const headers = container.querySelectorAll('th[data-dash-column]');
                    headers.forEach(function(header) {
                        const columnId = header.getAttribute('data-dash-column');
                        if (!columnId || columnId === 'DateStr') return;
                        
                        const headerIndex = header.getAttribute('data-dash-header-index');
                        if (headerIndex !== '1') return;
                        
                        header.style.cursor = 'pointer';
                        
                        header.addEventListener('click', function(e) {
                            e.stopPropagation();
                            
                            const parts = columnId.split('_');
                            if (parts.length < 3) return;
                            
                            const dataType = parts[0];
                            let techType = parts[1];
                            if (parts.length > 3 && (parts[1] === 'Catalytic' || parts[1] === 'Fluid')) {
                                techType = parts[1] + '_' + parts[2];
                            }
                            
                            const clickedKey = dataType + '_' + techType;
                            
                            if (selectedTechType === clickedKey) {
                                selectedTechType = null;
                                container.classList.remove('column-selection-active');
                                
                                headers.forEach(function(h) {
                                    h.classList.remove('column-selected');
                                });
                                container.querySelectorAll('td').forEach(function(cell) {
                                    cell.classList.remove('column-cell-selected');
                                });
                            } else {
                                selectedTechType = clickedKey;
                                container.classList.add('column-selection-active');
                                
                                headers.forEach(function(h) {
                                    h.classList.remove('column-selected');
                                });
                                container.querySelectorAll('td').forEach(function(cell) {
                                    cell.classList.remove('column-cell-selected');
                                });
                                
                                headers.forEach(function(h) {
                                    const colId = h.getAttribute('data-dash-column');
                                    if (colId && colId.startsWith(clickedKey)) {
                                        h.classList.add('column-selected');
                                    }
                                });
                                
                                container.querySelectorAll('td[data-dash-column]').forEach(function(cell) {
                                    const colId = cell.getAttribute('data-dash-column');
                                    if (colId && colId.startsWith(clickedKey)) {
                                        cell.classList.add('column-cell-selected');
                                    }
                                });
                            }
                        });
                    });
                }, 100);
            } catch (error) {
                console.error('Tech type header click error:', error);
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('gpw-selected-tech-type-store', 'data'),
        Input('gpw-data-table', 'data'),
        prevent_initial_call=False
    )
    
    # Update date labels based on slider selection
    @dash_app.callback(
        [
            Output('gpw-date-range-min-label', 'children'),
            Output('gpw-date-range-max-label', 'children')
        ],
        [Input('gpw-date-range-slider', 'value')]
    )
    def update_date_labels(slider_range):
        """Update date labels based on range slider value."""
        if not slider_range or not isinstance(slider_range, list) or len(slider_range) < 2:
            return _format_date_for_display(DEFAULT_START_DATE), _format_date_for_display(DEFAULT_END_DATE)
        
        start_idx, end_idx = slider_range
        start_date = _index_to_date(start_idx)
        end_date = _index_to_date(end_idx)
        
        return _format_date_for_display(start_date), _format_date_for_display(end_date)

    @dash_app.callback(
        [Output('gpw-download-dashboard-content', 'data'),
         Output('gpw-download-chart-png', 'data'),
         Output('gpw-download-raw-data-csv', 'data')],
        [Input('gpw-dashboard-export-dropdown', 'value')],
        [State('gpw-catalytic-cracking-chart', 'figure'),
         State('gpw-hydroskimming-chart', 'figure'),
         State('gpw-incremental-catalytic-chart', 'figure'),
         State('gpw-incremental-hydroskimming-chart', 'figure'),
         State('gpw-data-table', 'data'),
         State('gpw-data-table', 'columns'),
         State('gpw-region-filter', 'value')],
        prevent_initial_call=True
    )
    def export_gpw_dashboard_content_and_data(selected_value, cat_cracking_figure, hydroskimming_figure, inc_cat_figure, inc_hydro_figure, table_data, table_columns, region):
        if not selected_value:
            return dash.no_update, dash.no_update, dash.no_update

        download_pdf = dash.no_update
        download_png = dash.no_update
        download_raw_data_csv = dash.no_update

        df_table = pd.DataFrame(table_data)
        
        if selected_value == 'pdf':
            chart_figures = {
                "Catalytic Cracking": go.Figure(cat_cracking_figure),
                "Hydroskimming": go.Figure(hydroskimming_figure),
                "Incremental Catalytic Cracking": go.Figure(inc_cat_figure),
                "Incremental Hydroskimming": go.Figure(inc_hydro_figure)
            }
            
            chart_html_parts = []
            for title, fig in chart_figures.items():
                if fig.data: # Only include if chart has data
                    img_bytes = pio.to_image(fig, format="png", height=720, width=1280, scale=2)
                    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                    chart_html_parts.append(f"<h4>{title}</h4><img src=\"data:image/png;base64,{img_base64}\" />")
            
            html_table_content = ""
            if not df_table.empty:
                html_table_headers = "<thead><tr class=\"header-row-1\">"
                
                # Track unique top-level (DataType) and mid-level (TechType) headers
                data_type_headers = {}
                tech_type_headers = {}

                # First pass: Determine colspans for Data Type and Tech Type
                for col in table_columns:
                    if col['id'] == 'DateStr':
                        continue
                    
                    data_type = col['name'][0]
                    tech_type = col['name'][1]
                    
                    if data_type not in data_type_headers:
                        data_type_headers[data_type] = {'colspan': 0, 'tech_types': {}}
                    if tech_type not in data_type_headers[data_type]['tech_types']:
                        data_type_headers[data_type]['tech_types'][tech_type] = {'colspan': 0}
                    
                    data_type_headers[data_type]['colspan'] += 1
                    data_type_headers[data_type]['tech_types'][tech_type]['colspan'] += 1

                # Row 1: Date and Data Type headers
                html_table_headers += f"<th rowspan=\"3\" style=\"vertical-align:top;\">Date</th>"
                for data_type, data_type_info in data_type_headers.items():
                    html_table_headers += f"<th colspan=\"{data_type_info['colspan']}\">{data_type}</th>"
                html_table_headers += "</tr><tr class=\"header-row-2\">"
                
                # Row 2: Tech Type headers
                for data_type, data_type_info in data_type_headers.items():
                    for tech_type, tech_type_info in data_type_info['tech_types'].items():
                        html_table_headers += f"<th colspan=\"{tech_type_info['colspan']}\">{tech_type}</th>"
                html_table_headers += "</tr><tr class=\"header-row-3\">"

                # Row 3: Crude headers
                for col in table_columns:
                    if col['id'] == 'DateStr':
                        continue
                    html_table_headers += f"<th>{col['name'][2]}</th>"
                html_table_headers += "</tr></thead>"

                html_table_body = "<tbody>"
                for index, row in df_table.iterrows():
                    html_table_body += "<tr>"
                    for col_id in [c['id'] for c in table_columns]:
                        value = row.get(col_id, '')
                        html_table_body += f"<td>{value}</td>"
                    html_table_body += "</tr>"
                html_table_body += "</tbody>"

                html_table_content = f"<h4>Data Table</h4><table border=\"1\" style=\"width:100%; border-collapse: collapse; text-align: center;\">{html_table_headers}{html_table_body}</table>"
            
            chart_html_content_str = "\n".join(chart_html_parts)
            html_content = f"""
                <html>
                <head>
                    <title>GPW Margins Report</title>
                    <style>
                        @page {{
                            size: 1200px 5000px;
                            margin: 20px;
                        }}
                        body {{ font-family: Arial, sans-serif; margin: 0; }}
                        h1, h4 {{ color: #fe5000; text-align: center; }}
                        img {{ max-width: 100%; height: auto; display: block; margin: 0 auto; }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                        th, td {{ border: 1px solid #dee2e6; padding: 8px; text-align: center; font-size: 10px; }}
                        th {{ background-color: #f8f9fa; font-weight: bold; }}
                    </style>
                </head>
                <body>
                    <h1>GPW Margins Report</h1>
                    {chart_html_content_str}
                    {html_table_content}
                </body>
                </html>
            """
            
            pdf_bytes = HTML(string=html_content).write_pdf()
            download_pdf = dcc.send_bytes(pdf_bytes, "gpw_margins_report.pdf")

        elif selected_value == 'png':
            chart_figures = {
                "Catalytic Cracking": go.Figure(cat_cracking_figure),
                "Hydroskimming": go.Figure(hydroskimming_figure),
                "Incremental Catalytic Cracking": go.Figure(inc_cat_figure),
                "Incremental Hydroskimming": go.Figure(inc_hydro_figure)
            }
            
            chart_html_parts = []
            for title, fig in chart_figures.items():
                if fig.data: 
                    img_bytes = pio.to_image(fig, format="png", height=720, width=1280, scale=2)
                    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                    chart_html_parts.append(f"<h4>{title}</h4><img src=\"data:image/png;base64,{img_base64}\" />")
            
            html_table_content = ""
            if not df_table.empty:
                html_table_headers = "<thead><tr class=\"header-row-1\">"
                
                # Track unique top-level (DataType) and mid-level (TechType) headers
                data_type_headers = {}
                tech_type_headers = {}

                # First pass: Determine colspans for Data Type and Tech Type
                for col in table_columns:
                    if col['id'] == 'DateStr':
                        continue
                    
                    data_type = col['name'][0]
                    tech_type = col['name'][1]
                    
                    if data_type not in data_type_headers:
                        data_type_headers[data_type] = {'colspan': 0, 'tech_types': {}}
                    if tech_type not in data_type_headers[data_type]['tech_types']:
                        data_type_headers[data_type]['tech_types'][tech_type] = {'colspan': 0}
                    
                    data_type_headers[data_type]['colspan'] += 1
                    data_type_headers[data_type]['tech_types'][tech_type]['colspan'] += 1

                # Row 1: Date and Data Type headers
                html_table_headers += f"<th rowspan=\"3\" style=\"vertical-align:top;\">Date</th>"
                for data_type, data_type_info in data_type_headers.items():
                    html_table_headers += f"<th colspan=\"{data_type_info['colspan']}\">{data_type}</th>"
                html_table_headers += "</tr><tr class=\"header-row-2\">"
                
                # Row 2: Tech Type headers
                for data_type, data_type_info in data_type_headers.items():
                    for tech_type, tech_type_info in data_type_info['tech_types'].items():
                        html_table_headers += f"<th colspan=\"{tech_type_info['colspan']}\">{tech_type}</th>"
                html_table_headers += "</tr><tr class=\"header-row-3\">"

                # Row 3: Crude headers
                for col in table_columns:
                    if col['id'] == 'DateStr':
                        continue
                    html_table_headers += f"<th>{col['name'][2]}</th>"
                html_table_headers += "</tr></thead>"

                html_table_body = "<tbody>"
                for index, row in df_table.iterrows():
                    html_table_body += "<tr>"
                    for col_id in [c['id'] for c in table_columns]:
                        value = row.get(col_id, '')
                        html_table_body += f"<td>{value}</td>"
                    html_table_body += "</tr>"
                html_table_body += "</tbody>"

                html_table_content = f"<h4>Data Table</h4><table border=\"1\" style=\"width:100%; border-collapse: collapse; text-align: center;\">{html_table_headers}{html_table_body}</table>"
            
            chart_html_content_str = "\n".join(chart_html_parts)
            combined_html_content = f"""
                <html>
                <head>
                    <title>GPW Margins Report</title>
                    <style>
                        @page {{
                            size: 1200px 5000px;
                            margin: 20px;
                        }}
                        body {{ font-family: Arial, sans-serif; margin: 0; }}
                        h1, h4 {{ color: #fe5000; text-align: center; }}
                        img {{ max-width: 100%; height: auto; display: block; margin: 0 auto; }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                        th, td {{ border: 1px solid #dee2e6; padding: 8px; text-align: center; font-size: 10px; }}
                        th {{ background-color: #f8f9fa; font-weight: bold; }}
                    </style>
                </head>
                <body>
                    <h1>GPW Margins Report</h1>
                    {chart_html_content_str}
                    {html_table_content}
                </body>
                </html>
            """
            
            pdf_for_png_bytes = HTML(string=combined_html_content).write_pdf()
            
            doc = fitz.open("pdf", pdf_for_png_bytes)
            pix = doc[0].get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format="PNG")
            png_combined_bytes = img_byte_arr.getvalue()
            doc.close()

            download_png = dcc.send_bytes(png_combined_bytes, "gpw_margins_report.png")

                
                
        elif selected_value == 'raw_data_csv':
            gpw_df = _load_gpw_data(region=region)
            incremental_margins_df = _load_incremental_margins_data(region=region)
            
            combined_df = pd.concat([gpw_df, incremental_margins_df], ignore_index=True)
            download_raw_data_csv = dcc.send_data_frame(combined_df.to_csv, "gpw_all_raw_data.csv")

        return download_pdf, download_png, download_raw_data_csv

    @dash_app.callback(
        Output('gpw-download-incremental-margins-csv', 'data'),
        Input('gpw-incremental-margins-export-button', 'n_clicks'),
        State('gpw-region-filter', 'value'),
        State('gpw-date-range-slider', 'value'),
        State('gpw-crude-filter', 'value'),
        State('gpw-refining-complexity-filter', 'value'),
        prevent_initial_call=True
    )
    def export_incremental_margins_to_csv(n_clicks, region, date_range, crudes, tech_types):
        if n_clicks > 0:
            print(f"[DEBUG] n_clicks: {n_clicks}, region: {region}, date_slider_value: {date_range}, crudes: {crudes}, tech_types: {tech_types}")
            
            # The date_range here is actually the range slider value (list [start, end])
            if date_range and isinstance(date_range, list) and len(date_range) >= 2:
                start_date = _index_to_date(date_range[0]).strftime('%Y-%m-%d')
                end_date = _index_to_date(date_range[1]).strftime('%Y-%m-%d')
            else:
                start_date = _index_to_date(date_range).strftime('%Y-%m-%d') if date_range is not None else DEFAULT_START_DATE.strftime('%Y-%m-%d')
                end_date = DEFAULT_END_DATE.strftime('%Y-%m-%d')

            filtered_crudes = [c for c in crudes if c != 'ALL'] if crudes else None
            filtered_tech_types = [t for t in tech_types if t != 'ALL'] if tech_types else None

            incremental_margins_data = _load_incremental_margins_data_from_db(region=region, start_date=start_date, end_date=end_date, crudes=filtered_crudes, tech_types=filtered_tech_types)
            return dcc.send_data_frame(incremental_margins_data.to_csv, "incremental_margins_data.csv")
        return dash.no_update
        return dash.no_update

    @dash_app.callback(
        Output('download-gpw-data-table-csv', 'data'),
        Input('btn-export-gpw-data-table-csv', 'n_clicks'),
        State('gpw-region-filter', 'value'),
        State('gpw-date-range-slider', 'value'),
        State('gpw-crude-filter', 'value'),
        State('gpw-refining-complexity-filter', 'value'),
        prevent_initial_call=True
    )
    def export_gpw_table_data_to_csv(n_clicks, region, date_range, crudes, tech_types):
        if n_clicks > 0:
            if date_range and isinstance(date_range, list) and len(date_range) >= 2:
                start_date = _index_to_date(date_range[0]).strftime('%Y-%m-%d')
                end_date = _index_to_date(date_range[1]).strftime('%Y-%m-%d')
            else:
                start_date = _index_to_date(date_range).strftime('%Y-%m-%d') if date_range is not None else DEFAULT_START_DATE.strftime('%Y-%m-%d')
                end_date = DEFAULT_END_DATE.strftime('%Y-%m-%d')
            
            # Exclude 'ALL' from crudes and tech_types before passing to DB
            filtered_crudes = [c for c in crudes if c != 'ALL'] if crudes else None
            filtered_tech_types = [t for t in tech_types if t != 'ALL'] if tech_types else None

            raw_table_data = _load_data_table_data_from_db(region=region, start_date=start_date, end_date=end_date, crudes=filtered_crudes, tech_types=filtered_tech_types)
            return dcc.send_data_frame(raw_table_data.to_csv, "gpw_data_table_raw_data.csv")
        return dash.no_update

    @dash_app.callback(
        [Output({'type': 'download-chart-content', 'index': dd.MATCH}, 'data')],
        [Input({'type': 'chart-export-dropdown', 'index': dd.MATCH}, 'value')],
        [State({'type': 'chart-export-dropdown', 'index': dd.MATCH}, 'id'),
         State('gpw-catalytic-cracking-chart', 'figure'),
         State('gpw-hydroskimming-chart', 'figure'),
         State('gpw-incremental-catalytic-chart', 'figure'),
         State('gpw-incremental-hydroskimming-chart', 'figure'),
         State('gpw-region-filter', 'value')],
        prevent_initial_call=True
    )
    def export_individual_chart(selected_value, chart_id, cat_cracking_figure, hydroskimming_figure, inc_cat_figure, inc_hydro_figure, region):
        if not selected_value:
            return [dash.no_update]

        download_data = dash.no_update
        chart_index = chart_id['index']
        figure_to_export = go.Figure()
        filename_prefix = chart_index.replace('gpw-', '').replace('-', '_')

        if chart_index == 'gpw-catalytic-cracking':
            figure_to_export = go.Figure(cat_cracking_figure)
        elif chart_index == 'gpw-hydroskimming':
            figure_to_export = go.Figure(hydroskimming_figure)
        elif chart_index == 'gpw-incremental-catalytic':
            figure_to_export = go.Figure(inc_cat_figure)
        elif chart_index == 'gpw-incremental-hydroskimming':
            figure_to_export = go.Figure(inc_hydro_figure)

        if figure_to_export.data:
            if selected_value == 'pdf':
                img_bytes = pio.to_image(figure_to_export, format="png", height=720, width=1280, scale=2)
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                html_content = f"""
                    <html>
                    <head><title>{chart_index.replace('-', ' ').title()} Chart</title></head>
                    <body>
                        <h1>{chart_index.replace('-', ' ').title()} Chart</h1>
                        <img src="data:image/png;base64,{img_base64}" />
                    </body>
                    </html>
                """
                pdf_bytes = HTML(string=html_content).write_pdf()
                download_data = dcc.send_bytes(pdf_bytes, f"{filename_prefix}_chart.pdf")
            
            elif selected_value == 'png':
                chart_png_bytes = pio.to_image(figure_to_export, format="png", height=720, width=1280, scale=2)
                download_data = dcc.send_bytes(chart_png_bytes, f"{filename_prefix}_chart.png")
            
            elif selected_value == 'csv':
                if 'gpw' in chart_index:
                    raw_chart_data = _load_gpw_data(region=region)
                else:
                    raw_chart_data = _load_incremental_margins_data(region=region)
                
                download_data = dcc.send_data_frame(raw_chart_data.to_csv, f"{filename_prefix}_chart_data.csv")
        
        return [download_data]


    
    
    @dash_app.callback(
        Output('gpw-catalytic-cracking-chart', 'figure'),
        Output('gpw-hydroskimming-chart', 'figure'),
        Output('gpw-incremental-catalytic-chart', 'figure'),
        Output('gpw-incremental-hydroskimming-chart', 'figure'),
        Output('gpw-catalytic-cracking-chart-title', 'children'),
        Output('gpw-hydroskimming-chart-title', 'children'),
        Output('gpw-incremental-catalytic-cracking-chart-title', 'children'),
        Output('gpw-incremental-hydroskimming-chart-title', 'children'),
        Output('gpw-data-table-title', 'children'),
        Output('gpw-gpw-title', 'children'),
        Output('gpw-margins-title', 'children'),
        Output('gpw-refining-complexity-filter', 'options'),
        Output('gpw-refining-complexity-filter', 'value'),
        Output('gpw-available-tech-types', 'data'),
        Output('gpw-available-crudes-for-region', 'data'),
        Output('gpw-data-table', 'columns'),
        Output('gpw-data-table', 'data'),
        Output('gpw-data-table', 'tooltip_data'),
        Output('gpw-data-table', 'style_data_conditional'),
        Input('current-submenu', 'data'),
        Input('gpw-date-range-slider', 'value'),
        Input('gpw-region-filter', 'value'),
        Input('gpw-crude-filter', 'value'),
        Input('gpw-refining-complexity-filter', 'value'),
        Input('gpw-crude-legend', 'value')
    )
    def update_all_charts(submenu, date_slider_value, region, crude_filter, tech_type_filter, crude_legend):
        """Update all charts and table based on filters."""
        # Only highlight if EXACTLY ONE crude is selected from the legend
        highlight_crude = crude_legend[0] if crude_legend and len(crude_legend) == 1 else None
        if submenu != 'gpw-margins':
            return (
                _empty_figure(""),
                _empty_figure(""),
                _empty_figure(""),
                _empty_figure(""),
                "", # gpw-catalytic-cracking-chart-title
                "", # gpw-hydroskimming-chart-title
                "", # gpw-incremental-catalytic-cracking-chart-title
                "", # gpw-incremental-hydroskimming-chart-title
                "", # gpw-data-table-title
                "", # gpw-gpw-title
                "", # gpw-margins-title
                [], # options for gpw-refining-complexity-filter
                [], # value for gpw-refining-complexity-filter
                [], # gpw-available-tech-types
                [],
                [],
                []
            )
        
        table_title = f"{region} - Data Table ($/bbl)"
        gpw_title = f"{region} - Gross Product Worth ($/bbl)"
        margins_title = f"{region} - Incremental Margins ($/bbl)"

        gpw_catalytic_title = "Not selected"
        gpw_hydro_title = "Not selected"
        margins_catalytic_title = "Not selected"
        margins_hydro_title = "Not selected"

        # Initialize table tooltips
        table_tooltips = []
        
        # Parse dates from slider (range value [start, end])
        if date_slider_value and isinstance(date_slider_value, list) and len(date_slider_value) >= 2:
            start_date = _index_to_date(date_slider_value[0])
            end_date = _index_to_date(date_slider_value[1])
        else:
            # Fallback for old slider value or empty
            start_date = _index_to_date(date_slider_value) if date_slider_value is not None else DEFAULT_START_DATE
            end_date = DEFAULT_END_DATE
        
        # Load available crudes and tech types for the current region
        available_crudes_for_region = _get_available_crudes(region)
        available_tech_types_for_region = _get_available_tech_types(region)

        # Prepare dynamic options for Refining Complexity filter
        tech_type_options = [{'label': 'ALL', 'value': 'ALL'}] + [{'label': _map_tech_type_to_display(t), 'value': t} for t in available_tech_types_for_region]
        
        # Determine default selected tech types: all available for the region
        # If the user has already selected some tech types, try to preserve them
        if tech_type_filter and 'ALL' not in tech_type_filter:
            # Filter current selection to only include what's available for the new region
            tech_type_value = [t for t in tech_type_filter if t in available_tech_types_for_region]
            if not tech_type_value and available_tech_types_for_region:
                # If existing selection is now empty, default to all available for region
                tech_type_value = ['ALL'] + available_tech_types_for_region
            elif 'ALL' in tech_type_filter and available_tech_types_for_region:
                tech_type_value = ['ALL'] + available_tech_types_for_region
            elif not tech_type_filter and available_tech_types_for_region:
                tech_type_value = ['ALL'] + available_tech_types_for_region
        elif available_tech_types_for_region:
            tech_type_value = ['ALL'] + available_tech_types_for_region
        else:
            tech_type_value = [] # No tech types available


        # Determine selected crudes for plotting
        # Data inclusion is STRICTLY determined by the crude_filter (checkboxes)
        if crude_filter is not None:
            selected_crudes = crude_filter if isinstance(crude_filter, list) else [crude_filter]
        else:
            # Default to all available crudes if no filter set
            selected_crudes = available_crudes_for_region.copy()

        # Handle ALL option for crudes in data selection
        if selected_crudes and 'ALL' in selected_crudes:
            selected_crudes = available_crudes_for_region.copy()
        else:
            selected_crudes = [c for c in selected_crudes if c != 'ALL'] if selected_crudes else []
        
        # Note: crude_legend is used ONLY to determine highlight_crude at the start of the function.
        # This matches the live site where clicking the legend focuses one line but keeps others faint.
        
        # Determine selected tech types from checkbox
        if tech_type_filter:
            selected_tech_types = tech_type_filter if isinstance(tech_type_filter, list) else [tech_type_filter]
        else:
            # If filter is empty/None, default to all tech types for the *current region*
            selected_tech_types = available_tech_types_for_region.copy()
        
        # Handle ALL option for tech types
        if 'ALL' in selected_tech_types:
            selected_tech_types = available_tech_types_for_region.copy()
        else:
            selected_tech_types = [t for t in selected_tech_types if t != 'ALL']
            # Allow empty selection - if empty, no tech types selected (charts will be empty)
        
        # Load GPW data dynamically from database based on region filter
        gpw_df = _load_gpw_data(region)
        
        # Filter GPW data by date range and selected crudes
        if not gpw_df.empty:
            gpw_filtered = gpw_df[
                (gpw_df['Date'] >= start_date) &
                (gpw_df['Date'] <= end_date) &
                (gpw_df['Crude'].isin(selected_crudes))
            ].copy()
            
            if selected_tech_types:
                gpw_filtered = gpw_filtered[gpw_filtered['TechType'].isin(selected_tech_types)]
        else:
            gpw_filtered = pd.DataFrame()
        
        # Load Incremental Margins data dynamically from database based on region filter
        margins_df = _load_incremental_margins_data(region)
        
        # Filter Incremental Margins data by date range and selected crudes
        if not margins_df.empty:
            margins_filtered = margins_df[
                (margins_df['Date'] >= start_date) &
                (margins_df['Date'] <= end_date) &
                (margins_df['Crude'].isin(selected_crudes))
            ].copy()
            
            if selected_tech_types:
                margins_filtered = margins_filtered[margins_filtered['TechType'].isin(selected_tech_types)]
        else:
            margins_filtered = pd.DataFrame()
        
        # Build charts only if tech type is selected
        gpw_catalytic = _empty_figure("FCC not selected")
        gpw_hydro = _empty_figure("HSK not selected")
        margins_catalytic = _empty_figure("FCC not selected")
        margins_hydro = _empty_figure("HSK not selected")

        # Build charts only if tech type is selected
        gpw_catalytic = _empty_figure("Not selected")
        gpw_hydro = _empty_figure("Not selected")
        margins_catalytic = _empty_figure("Not selected")
        margins_hydro = _empty_figure("Not selected")

        gpw_catalytic_title = "Not selected"
        gpw_hydro_title = "Not selected"
        margins_catalytic_title = "Not selected"
        margins_hydro_title = "Not selected"

        # Prepare a list of selected tech types with their internal and display names
        charts_to_display = []
        
        # Define region-specific display name mappings
        region_tech_map = {
            'NWE': {
                'Catalytic Cracking': 'Catalytic Cracking',
                'Fluid Catalytic Cracking': 'Fluid Catalytic Cracking',
                'Hydroskimming': 'Hydroskimming',
                'Hydrocracking': 'Hydrocracking',
                'Coking': 'Coking'
            },
            'USGC': {
                'Catalytic Cracking': 'Catalytic Cracking',
                'Fluid Catalytic Cracking': 'Fluid Catalytic Cracking',
                'Hydroskimming': 'Hydroskimming',
                'Hydrocracking': 'Hydrocracking',
                'Coking': 'Coking'
            },
            'Singapore': {
                'Catalytic Cracking': 'Catalytic Cracking',
                'Fluid Catalytic Cracking': 'Fluid Catalytic Cracking',
                'Hydroskimming': 'Hydroskimming',
                'Hydrocracking': 'Hydrocracking',
                'Coking': 'Coking'
            }
        }

        # Get the mapping for the current region, default to generic if not found
        current_region_map = region_tech_map.get(region, {})

        for tech_type_internal in selected_tech_types:
            # Include all valid tech types for chart display
            if tech_type_internal in ['Catalytic Cracking', 'Fluid Catalytic Cracking', 'Hydroskimming', 'Hydrocracking', 'Coking']:
                # Use region-specific mapping, otherwise use generic display mapping
                tech_type_display = current_region_map.get(tech_type_internal, _map_tech_type_to_display(tech_type_internal))
                charts_to_display.append((tech_type_internal, tech_type_display))
        
        # Only display up to two charts at a time for the main two slots
        if len(charts_to_display) > 0:
            # First chart slot
            tech_internal_1, tech_display_1 = charts_to_display[0]
            gpw_catalytic = _build_gpw_chart(
                gpw_filtered,
                tech_internal_1,
                tech_display_1,
                selected_crudes,
                region,
                highlight_crude
            )
            gpw_catalytic_title = tech_display_1
            margins_catalytic = _build_incremental_margins_chart(
                margins_filtered,
                tech_internal_1,
                tech_display_1,
                selected_crudes,
                region,
                highlight_crude
            )
            margins_catalytic_title = tech_display_1

            if len(charts_to_display) > 1:
                # Second chart slot
                tech_internal_2, tech_display_2 = charts_to_display[1]
                gpw_hydro = _build_gpw_chart(
                    gpw_filtered,
                    tech_internal_2,
                    tech_display_2,
                    selected_crudes,
                    region,
                    highlight_crude
                )
                gpw_hydro_title = tech_display_2
                margins_hydro = _build_incremental_margins_chart(
                    margins_filtered,
                    tech_internal_2,
                    tech_display_2,
                    selected_crudes,
                    region,
                    highlight_crude
                )
                margins_hydro_title = tech_display_2
        
        # Prepare data table with multi-level headers
        # Load data table data directly from database using the provided query
        table_df = _load_data_table_data_from_db(region)
        
        if not table_df.empty:
            # Filter by date range, selected crudes, and selected tech types
            table_filtered = table_df[
                (table_df['Date'] >= start_date) &
                (table_df['Date'] <= end_date)
            ].copy()
            
            # Filter by selected crudes (empty list means show nothing)
            table_filtered = table_filtered[table_filtered['Crude'].isin(selected_crudes)]
            
            # Filter by selected tech types (empty list means show nothing)
            table_filtered = table_filtered[table_filtered['TechType'].isin(selected_tech_types)]
            
            if not table_filtered.empty:
                table_columns, table_data, table_tooltips, styles_data_conditional = _prepare_data_table(
                    table_filtered,
                    start_date,
                    end_date,
                    region,
                    selected_crudes,
                    selected_tech_types,
                    highlight_crude
                )
            else:
                table_columns, table_data, table_tooltips, styles_data_conditional = [], [], [], []
        else:
            table_columns, table_data, table_tooltips = [], [], []
        
        return (
            gpw_catalytic,
            gpw_hydro,
            margins_catalytic,
            margins_hydro,
            gpw_catalytic_title,
            gpw_hydro_title,
            margins_catalytic_title,
            margins_hydro_title,
            html.H3(table_title, style={'color': '#fe5000', 'fontSize': 20}),
            gpw_title,
            margins_title,
            tech_type_options,
            tech_type_value,
            available_tech_types_for_region,
            available_crudes_for_region,
            table_columns,
            table_data,
            table_tooltips,
            styles_data_conditional
        )
    
    # Handle ALL option normalization for crude filter
    @dash_app.callback(
        Output('gpw-crude-filter', 'value', allow_duplicate=True),
        Output('gpw-initial-load', 'data', allow_duplicate=True),
        Output('gpw-crude-filter-previous', 'data', allow_duplicate=True),
        Input('gpw-crude-filter', 'value'),
        State('gpw-initial-load', 'data'),
        State('gpw-crude-filter-previous', 'data'),
        prevent_initial_call=True
    )
    def normalize_crude_filter(value, is_initial_load, previous_value):
        """Handle ALL option behavior (like Refining Complexity Filter):
        - When ALL is checked: select all individual items
        - When ALL is unchecked: uncheck all individual items
        """
        all_crudes_option = [c['value'] for c in _crude_filter_options(CRUDES)]
        all_crudes_value = ['ALL'] + all_crudes_option

        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update
        
        # Process all triggers - normalization should handle all value changes
        # The sync callback will handle legend->filter sync separately
        
        
        
        
        value_list = list(value) if value else []
        previous_list = list(previous_value) if previous_value and isinstance(previous_value, (list, tuple)) else []
        
        has_all = 'ALL' in value_list
        had_all = 'ALL' in previous_list
        non_all_items = [v for v in value_list if v != 'ALL']
        all_items_set = set(CRUDES)
        non_all_set = set(non_all_items)
        previous_non_all_set = set([v for v in previous_list if v != 'ALL'])
        
        # If neither previous nor current has ALL, and it's just individual item changes
        # This allows independent item selection without interference
        if not had_all and not has_all:
            # Clean items to ensure only valid crudes
            cleaned_items = [v for v in non_all_items if v in CRUDES]
            
            # Only normalize if all items are now selected (auto-check ALL)
            if set(cleaned_items) == all_items_set:
                result = ['ALL'] + CRUDES.copy()
                return result, False, result
            
            # For individual item selection without ALL, pass through exactly as user selected
            # Only filter out invalid items if any exist
            if len(cleaned_items) != len(non_all_items):
                # Some invalid items - return cleaned version
                return cleaned_items, False, cleaned_items
            else:
                # All items are valid - pass through exactly as user selected
                # Always return the value to allow Dash to update the UI
                return cleaned_items, False, cleaned_items
        
        # Case 1: ALL is being checked (transition: didn't have ALL, now has ALL)
        if not had_all and has_all:
            # User just checked ALL checkbox - select all items automatically
            result = ['ALL'] + CRUDES.copy()
            return result, False, result
        
        # Case 2: ALL is currently checked
        if has_all:
            # If ALL is checked, ensure all items are also checked
            if non_all_set == all_items_set:
                # ALL + all items - keep as is (correct state)
                result = ['ALL'] + CRUDES.copy()
                return result, False, result
            elif len(non_all_items) > 0 and len(non_all_set) < len(all_items_set):
                # ALL is checked but some items are missing
                # This means user unclicked an item while ALL was checked
                # Remove ALL and keep only the selected items
                cleaned_items = [v for v in non_all_items if v in CRUDES]
                return cleaned_items, False, cleaned_items
            elif len(non_all_items) == 0:
                # ALL is checked but no items are present - this shouldn't happen, but ensure all items
                result = ['ALL'] + CRUDES.copy()
                return result, False, result
            else:
                # Default: ensure ALL + all items
                result = ['ALL'] + CRUDES.copy()
                return result, False, result
        
        # Case 3: ALL was unchecked (had ALL before, don't have ALL now)
        if had_all and not has_all:
            # Check if items decreased (user unclicked an item) or stayed same (ALL unclicked)
            if previous_non_all_set == all_items_set and len(non_all_set) < len(all_items_set):
                # User unclicked an item from ALL+all - keep remaining items
                cleaned_items = [v for v in non_all_items if v in CRUDES]
                return cleaned_items, False, cleaned_items
            else:
                # User unchecked ALL checkbox - uncheck all items
                return [], False, []
        
        # Allow empty selection
        return [], False, []
    
    # Handle crude legend item clicks (row click selection, no checkboxes)
    @dash_app.callback(
        Output('gpw-crude-legend', 'value', allow_duplicate=True),
        Input({'type': 'gpw-crude-legend-item', 'crude': dd.ALL}, 'n_clicks'),
        State({'type': 'gpw-crude-legend-item', 'crude': dd.ALL}, 'id'),
        State('gpw-crude-legend', 'value'),
        prevent_initial_call=True
    )
    def handle_crude_legend_clicks(n_clicks_list, id_list, current_values):
        """Toggle crude selection when legend item is clicked."""
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update
        
        # Get the clicked item's crude name from triggered ID
        triggered_id = ctx.triggered[0]['prop_id']
        if not triggered_id or 'gpw-crude-legend-item' not in triggered_id:
            return dash.no_update
        
        # Extract crude name from the triggered ID
        import json
        try:
            # Parse the ID structure: {"type":"gpw-crude-legend-item","crude":"Arab Light"}.n_clicks
            id_part = triggered_id.split('.')[0]
            id_dict = json.loads(id_part.replace("'", '"'))
            clicked_crude = id_dict.get('crude')
        except:
            return dash.no_update
        
        if not clicked_crude or clicked_crude not in CRUDES:
            return dash.no_update

        # Check if the clicked crude is currently the ONLY selected crude.
        # If so, clicking it again should revert to showing all crudes.
        if current_values == [clicked_crude]:
            return CRUDES.copy()  # Revert to all crudes selected
        else:
            return [clicked_crude] # Select only the clicked crude
        
        # Toggle the clicked crude in the selection
        current_values = current_values or []
        if clicked_crude in current_values:
            # Remove if already selected
            new_values = [v for v in current_values if v != clicked_crude]
        else:
            # Add if not selected
            new_values = current_values + [clicked_crude] if current_values else [clicked_crude]
        
        return new_values if new_values else []
    
    # Update legend content and visual state based on selection and active region
    @dash_app.callback(
        Output('gpw-crude-legend-container', 'children'),
        Output('gpw-crude-legend-title', 'children'),
        Input('gpw-crude-legend', 'value'),
        Input('gpw-region-filter', 'value'),
        Input('gpw-available-crudes-for-region', 'data'),
        prevent_initial_call=False
    )
    def update_crude_legend_content(selected_crudes, region, available_crudes_from_store):
        """Update visible legend items, their order, and their style based on selection."""
        selected_crudes = selected_crudes or []
        selected_set = set(selected_crudes)
        
        # Determine available crudes for the region
        available_crudes_for_region = available_crudes_from_store if available_crudes_from_store is not None else []
        available_crudes_set = set(available_crudes_for_region)

        # Determine "highlight mode"
        is_highlight_mode = 0 < len(selected_set) < len(available_crudes_set)

        # Sort crudes: selected ones first, then others (maintaining original CRUDES order within groups)
        ordered_crudes = []
        # First add selected crudes that are available for the region
        for crude in CRUDES:
            if crude in available_crudes_set and crude in selected_set:
                ordered_crudes.append(crude)
        
        # Then add remaining available crudes
        for crude in CRUDES:
            if crude in available_crudes_set and crude not in selected_set:
                ordered_crudes.append(crude)

        legend_items = []
        for crude in ordered_crudes:
            # Determine style based on highlight mode
            if is_highlight_mode:
                if crude in selected_set:
                    # Highlighted state
                    container_style = {
                        'display': 'flex',
                        'alignItems': 'center',
                        'padding': '6px 8px',
                        'marginBottom': '4px',
                        'borderRadius': '4px',
                        'cursor': 'pointer',
                        'transition': 'all 0.2s ease',
                        'userSelect': 'none',
                        'backgroundColor': '#ffffff',
                        'border': '2px solid #3498db',
                        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
                    }
                    opacity = 1.0
                else:
                    # Dimmed state
                    container_style = {
                        'display': 'flex',
                        'alignItems': 'center',
                        'padding': '6px 8px',
                        'marginBottom': '4px',
                        'borderRadius': '4px',
                        'cursor': 'pointer',
                        'transition': 'all 0.2s ease',
                        'userSelect': 'none',
                        'backgroundColor': 'transparent',
                        'border': '1px solid transparent',
                        'opacity': 0.4  # Increased visibility from 0.15
                    }
                    opacity = 1.0
            else:
                # Normal state
                container_style = {
                    'display': 'flex',
                    'alignItems': 'center',
                    'padding': '6px 8px',
                    'marginBottom': '4px',
                    'borderRadius': '4px',
                    'cursor': 'pointer',
                    'transition': 'all 0.2s ease',
                    'userSelect': 'none',
                    'backgroundColor': 'transparent',
                    'border': '1px solid transparent'
                }
                opacity = 1.0

            # Get color for swatch
            color = CRUDE_COLORS.get(crude, FALLBACK_COLORS[CRUDES.index(crude) % len(FALLBACK_COLORS)])

            # If in highlight mode and NOT selected, dim the swatch as well
            swatch_opacity = 0.4 if is_highlight_mode and crude not in selected_set else 1.0
            text_color = '#1b365d' if not (is_highlight_mode and crude not in selected_set) else '#999999'

            item = html.Div(
                id={'type': 'gpw-crude-legend-item', 'crude': crude},
                n_clicks=0,
                children=[
                    html.Div(
                        style={
                            'width': '14px',
                            'height': '14px',
                            'backgroundColor': color,
                            'borderRadius': '2px',
                            'marginRight': '10px',
                            'border': '1px solid #cfd8e3',
                            'boxShadow': '0 0 2px rgba(0,0,0,0.1)',
                            'display': 'inline-block',
                            'verticalAlign': 'middle',
                            'opacity': swatch_opacity,
                            'transition': 'opacity 0.2s ease'
                        }
                    ),
                    html.Span(
                        crude,
                        style={
                            'color': text_color,
                            'fontWeight': '600',
                            'fontSize': '13px',
                            'verticalAlign': 'middle',
                            'transition': 'color 0.2s ease'
                        }
                    )
                ],
                style=container_style
            )
            legend_items.append(item)
        
        # Calculate crude count for header
        crude_count = len(available_crudes_for_region)
        title_text = f"Crude ({crude_count})"
        
        return legend_items, title_text
    
    # Sync crude filter checkbox with crude legend checklist (one-way: legend -> filter)
    # This sync happens when legend changes
    @dash_app.callback(
        Output('gpw-crude-legend', 'value', allow_duplicate=True),
        Input('gpw-crude-filter', 'value'),
        State('gpw-crude-legend', 'value'),
        prevent_initial_call=True
    )
    def sync_crude_legend_from_filter(crude_filter_values, current_legend_values):
        """Sync crude legend when filter changes.
        Update legend to match filter selection.
        If filter has ALL + all items, show all items in legend.
        If filter has individual items, show those items in legend.
        If filter is empty, clear legend."""
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update
        
        # Only sync if triggered by the filter (not by legend changes or normalization)
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        if trigger_id != 'gpw-crude-filter':
            return dash.no_update
        
        # When filter is empty, clear legend
        if not crude_filter_values or (isinstance(crude_filter_values, list) and len(crude_filter_values) == 0):
            return []
        
        filter_list = crude_filter_values if isinstance(crude_filter_values, list) else [crude_filter_values]
        filter_set = set(filter_list)
        all_items_set = set(CRUDES)
        all_set_with_all = set(['ALL'] + CRUDES)
        
        # Check if filter has ALL + all items
        if filter_set == all_set_with_all:
            # ALL + all items selected - sync legend to show all items
            # Check if legend already matches
            if current_legend_values and isinstance(current_legend_values, list):
                legend_set = set(current_legend_values)
                if legend_set == all_items_set:
                    return dash.no_update
            return CRUDES.copy()
        
        # Check if filter has ALL (but not all items - normalization will handle this case)
        if 'ALL' in filter_list:
            # ALL is present but not all items - wait for normalization to complete
            # But if all items are present, sync them
            non_all_items = [v for v in filter_list if v != 'ALL']
            if set(non_all_items) == all_items_set:
                # Check if legend already matches
                if current_legend_values and isinstance(current_legend_values, list):
                    legend_set = set(current_legend_values)
                    if legend_set == all_items_set:
                        return dash.no_update
                return CRUDES.copy()
            # Otherwise, don't sync yet (normalization will handle)
            return dash.no_update
        
        # For individual selections (no ALL), sync to legend directly
        # Filter out any invalid values and sync only valid crudes
        valid_crudes = [c for c in filter_list if c in CRUDES]
        # Check if legend already matches
        if current_legend_values and isinstance(current_legend_values, list):
            legend_set = set(current_legend_values)
            valid_set = set(valid_crudes)
            if legend_set == valid_set:
                return dash.no_update
        return valid_crudes
    
    # Handle ALL option normalization for refining complexity filter
    @dash_app.callback(
        Output('gpw-refining-complexity-filter', 'value', allow_duplicate=True),
        Output('gpw-refining-complexity-filter-previous', 'data', allow_duplicate=True),
        Input('gpw-refining-complexity-filter', 'value'),
        State('gpw-initial-load', 'data'),
        State('gpw-refining-complexity-filter-previous', 'data'),
        State('gpw-available-tech-types', 'data'),
        prevent_initial_call=True
    )
    def normalize_tech_type_filter(value, is_initial_load, previous_value, available_tech_types):
        """Handle ALL option behavior (like Crude Legend):
        - When ALL is checked: select all individual items
        - When ALL is unchecked: uncheck all individual items
        - Individual items work independently
        - Allow empty selection
        """
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update
        
        # Skip normalization on initial load
        if is_initial_load:
            return dash.no_update, value
        
        if value is None:
            return [], []
        
        if not isinstance(value, (list, tuple)):
            return dash.no_update, previous_value
        
        value_list = list(value) if value else []
        previous_list = list(previous_value) if previous_value and isinstance(previous_value, (list, tuple)) else []
        
        has_all = 'ALL' in value_list
        had_all = 'ALL' in previous_list
        non_all_items = [v for v in value_list if v != 'ALL']
        all_items_set = set(available_tech_types)
        non_all_set = set(non_all_items)
        previous_non_all_set = set([v for v in previous_list if v != 'ALL'])
        
        # If neither previous nor current has ALL, and it's just individual item changes
        # This allows independent item selection without interference
        if not had_all and not has_all:
            # Clean items to ensure only valid tech types
            cleaned_items = [v for v in non_all_items if v in available_tech_types]
            
            # Only normalize if all items are now selected (auto-check ALL)
            if set(cleaned_items) == all_items_set:
                result = ['ALL'] + available_tech_types.copy()
                return result, result
            
            # For individual item selection without ALL, pass through exactly as user selected
            # Only filter out invalid items if any exist
            if len(cleaned_items) != len(non_all_items):
                # Some invalid items - return cleaned version
                return cleaned_items, cleaned_items
            else:
                # All items are valid - pass through exactly as user selected
                # Maintain order as user selected it
                return cleaned_items, cleaned_items
        
        # Case 1: ALL is being checked (transition: didn't have ALL, now has ALL)
        if not had_all and has_all:
            # User just checked ALL checkbox - select all items automatically
            result = ['ALL'] + available_tech_types.copy()
            return result, result
        
        # Case 2: ALL is checked - detect if item was unclicked or if ALL was just checked
        if has_all:
            if non_all_set == all_items_set:
                # ALL + all items - keep as is
                result = ['ALL'] + available_tech_types.copy()
                return result, result
            else:
                # ALL is checked but not all items are present
                # This means user unclicked an item while ALL was checked
                # Remove ALL and keep only the selected items
                cleaned_items = [v for v in non_all_items if v in available_tech_types]
                return cleaned_items, cleaned_items
        
        # Case 3: ALL was unchecked (had ALL before, don't have ALL now)
        if had_all and not has_all:
            # Check if items decreased (user unclicked an item) or stayed same (ALL unclicked)
            if previous_non_all_set == all_items_set and len(non_all_set) < len(all_items_set):
                # User unclicked an item from ALL+all - keep remaining items
                cleaned_items = [v for v in non_all_items if v in available_tech_types]
                return cleaned_items, cleaned_items
            else:
                # User unchecked ALL checkbox - uncheck all items
                return [], []
        
        # Allow empty selection
        return [], []
    
    # Client-side callback to handle header clicks and column/row highlighting
    dash_app.clientside_callback(
        """
        function(container, data) {
            try {
                // Initialize global state if not exists
                if (!window.gpwTableState) {
                    window.gpwTableState = {
                        selectedColumnId: null,
                        selectedRowIndex: null,
                        selectedDate: null,
                        lastTableSignature: null
                    };
                }
                
                function clearAllColumnSelections(spreadsheet) {
                    if (!spreadsheet) return;
                    // Clear all column headers
                    const allHeaders = spreadsheet.querySelectorAll('th.column-selected');
                    allHeaders.forEach(header => {
                        header.classList.remove('column-selected');
                        header.style.backgroundColor = '';
                        header.style.color = '';
                        header.style.fontWeight = '';
                    });
                    
                    // Clear all column cells
                    const allColumnCells = spreadsheet.querySelectorAll('td.column-cell-selected');
                    allColumnCells.forEach(cell => {
                        cell.classList.remove('column-cell-selected');
                        cell.style.backgroundColor = '';
                        cell.style.border = '';
                        cell.style.fontWeight = '';
                        cell.style.opacity = '';
                    });
                    
                    // Remove column selection active class and reset opacity for all cells
                    spreadsheet.classList.remove('column-selection-active');
                    const allDataCells = spreadsheet.querySelectorAll('td[data-dash-column]:not([data-dash-column="DateStr"])');
                    allDataCells.forEach(cell => {
                        cell.style.opacity = '';
                    });
                }
                
                function clearAllRowSelections(spreadsheet) {
                    if (!spreadsheet) return;
                    
                    // Clear all row cells - remove classes and all inline styles
                    const allRowCells = spreadsheet.querySelectorAll('td.row-cell-selected');
                    allRowCells.forEach(cell => {
                        cell.classList.remove('row-cell-selected');
                        cell.style.removeProperty('background-color');
                        cell.style.removeProperty('border');
                        cell.style.removeProperty('font-weight');
                        cell.style.removeProperty('color');
                        cell.style.removeProperty('opacity');
                    });
                    
                    // Reset all rows to normal state
                    const allDataRows = spreadsheet.querySelectorAll('tbody tr');
                    allDataRows.forEach(r => {
                        const rowCells = r.querySelectorAll('td');
                        rowCells.forEach(c => {
                            c.classList.remove('row-cell-selected');
                            c.style.removeProperty('background-color');
                            c.style.removeProperty('border');
                            c.style.removeProperty('font-weight');
                            c.style.removeProperty('color');
                            c.style.removeProperty('opacity');
                        });
                    });
                    
                    // Clear row-selected class from row elements
                    const allSelectedRows = spreadsheet.querySelectorAll('tr.row-selected');
                    allSelectedRows.forEach(r => {
                        r.classList.remove('row-selected');
                    });
                    
                    // Remove row selection active class
                    spreadsheet.classList.remove('row-selection-active');
                }
                
                function getCellValue(cell) {
                    const text = cell.textContent || cell.innerText || '';
                    return text.trim();
                }
                
                function enhanceTable() {
                    const tableEl = document.getElementById('gpw-data-table');
                    if (!tableEl) {
                        return;
                    }
                    
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    if (!spreadsheet) {
                        return;
                }

                    // Check if headers exist
                    const headers = spreadsheet.querySelectorAll('th[data-dash-column]');
                    if (headers.length === 0) {
                        return;
                    }
                    
                    // Create a hash of the table structure to detect changes
                    let tableSignature = '';
                    const topRow = spreadsheet.querySelector('thead tr');
                    if (topRow) {
                        const topHeaders = Array.from(topRow.querySelectorAll('th')).slice(0, 5);
                        tableSignature = topHeaders.map(h => h.textContent.trim()).join('|') + '|' + headers.length;
                    } else {
                        tableSignature = headers.length.toString();
                    }
                    
                    // Check if table structure has changed (new table rendered)
                    const signatureChanged = window.gpwTableState.lastTableSignature !== tableSignature;
                    if (signatureChanged) {
                        // Table was re-rendered, reset enhanced flag and clear handlers
                        spreadsheet.dataset.gpwEnhanced = 'false';
                        
                        // Remove old click handler
                        if (spreadsheet._gpwClickHandler) {
                            spreadsheet.removeEventListener('click', spreadsheet._gpwClickHandler, true);
                            spreadsheet._gpwClickHandler = null;
                        }
                        
                        // Clear selections
                        clearAllColumnSelections(spreadsheet);
                        clearAllRowSelections(spreadsheet);
                        
                        window.gpwTableState.lastTableSignature = tableSignature;
                        window.gpwTableState.selectedColumnId = null;
                        window.gpwTableState.selectedRowIndex = null;
                        window.gpwTableState.selectedDate = null;
                    }
                    
                    // Skip if already enhanced (but only if signature hasn't changed)
                    if (spreadsheet.dataset.gpwEnhanced === 'true' && !signatureChanged) {
                        return;
                    }

                    spreadsheet.dataset.gpwEnhanced = 'true';
                    
                    // Remove any existing click handler to avoid duplicates
                    if (spreadsheet._gpwClickHandler) {
                        spreadsheet.removeEventListener('click', spreadsheet._gpwClickHandler, true);
                    }
                    
                    // Create click handler
                    const clickHandler = function(event) {
                        const clickedSpreadsheet = event.target.closest('.dash-spreadsheet-container') || spreadsheet;
                        if (!clickedSpreadsheet) return;
                        
                        // Try to find header
                        let header = event.target.closest('th[data-dash-column]');
                        
                        if (!header) {
                            const thead = event.target.closest('thead');
                            if (thead) {
                                const allHeaders = thead.querySelectorAll('th[data-dash-column]');
                                for (let h of allHeaders) {
                                    if (h.contains(event.target) || h === event.target) {
                                        header = h;
                                        break;
                                    }
                                }
                            }
                        }
                        
                        if (header) {
                            event.stopPropagation();
                            
                            const columnId = header.getAttribute('data-dash-column');
                            if (!columnId) return;
                            
                            // Skip DateStr column
                    if (columnId === 'DateStr') {
                        return;
                    }

                            // Clear all previous selections
                            clearAllColumnSelections(clickedSpreadsheet);
                            clearAllRowSelections(clickedSpreadsheet);
                            if (window.gpwTableState) {
                                window.gpwTableState.selectedRowIndex = null;
                                window.gpwTableState.selectedDate = null;
                            }
                            
                            // Find which header row this header belongs to
                            const headerRow = header.closest('tr');
                            const thead = header.closest('thead');
                            
                            let headerIndex = -1;
                            let totalHeaderRows = 0;
                            let headerRows = [];
                            
                            if (thead) {
                                headerRows = Array.from(thead.querySelectorAll('tr'));
                            }
                            
                            if (headerRows.length === 0 && clickedSpreadsheet) {
                                headerRows = Array.from(clickedSpreadsheet.querySelectorAll('thead tr'));
                            }
                            
                            // Filter out rows that only contain DateStr headers
                            headerRows = headerRows.filter(tr => {
                                const dataHeaders = tr.querySelectorAll('th[data-dash-column]:not([data-dash-column="DateStr"])');
                                return dataHeaders.length > 0;
                            });
                            
                            totalHeaderRows = headerRows.length;
                            
                            if (headerRow && headerRows.length > 0) {
                                headerIndex = headerRows.indexOf(headerRow);
                            }
                            
                            // Create a unique key for this selection
                            const selectionKey = columnId + '_' + headerIndex;
                            
                            // Check if this exact header level is already selected
                            if (window.gpwTableState && window.gpwTableState.selectedColumnId === selectionKey) {
                                // Deselect column
                                clearAllColumnSelections(clickedSpreadsheet);
                                if (window.gpwTableState) {
                                    window.gpwTableState.selectedColumnId = null;
                                }
                            } else {
                                // Select new column
                                clearAllColumnSelections(clickedSpreadsheet);
                                clearAllRowSelections(clickedSpreadsheet);
                                
                                if (window.gpwTableState) {
                                    window.gpwTableState.selectedColumnId = selectionKey;
                                    window.gpwTableState.selectedRowIndex = null;
                                    window.gpwTableState.selectedDate = null;
                                }
                                
                                // Check if this is the bottom-most header level
                                const isBottomHeader = (headerIndex >= 0 && totalHeaderRows > 0 && headerIndex === totalHeaderRows - 1);
                                const isTopHeader = (headerIndex === 0);
                                
                                if (isBottomHeader || isTopHeader) {
                                    if (isTopHeader) {
                                        // Top header clicked - find all columns under this spanning header
                                        const topHeaderText = header.textContent.trim();
                                        const colspan = header.getAttribute('colspan') || header.colSpan;
                                        
                                        const topRow = headerRows[0];
                                        if (topRow) {
                                            const columnIds = new Set();
                                            
                                            if (colspan && parseInt(colspan) > 1) {
                                                // Header spans multiple columns
                                                const spanCount = parseInt(colspan);
                                                const allTopRowCells = Array.from(topRow.querySelectorAll('th'));
                                                
                                                let clickedCellIndex = -1;
                                                for (let i = 0; i < allTopRowCells.length; i++) {
                                                    if (allTopRowCells[i] === header || allTopRowCells[i].contains(header)) {
                                                        clickedCellIndex = i;
                                                        break;
                                                    }
                                                }
                                                
                                                // Get bottom row headers to find actual column IDs
                                                const bottomRow = headerRows[headerRows.length - 1];
                                                if (bottomRow) {
                                                    const allBottomRowCells = Array.from(bottomRow.querySelectorAll('th'));
                                                    
                                                    let topRowDataStart = 0;
                                                    for (let i = 0; i < clickedCellIndex; i++) {
                                                        const cell = allTopRowCells[i];
                                                        const cellColId = cell.getAttribute('data-dash-column');
                                                        if (cellColId === 'DateStr') continue;
                                                        const cellColspan = parseInt(cell.getAttribute('colspan') || cell.colSpan || '1');
                                                        topRowDataStart += cellColspan;
                                                    }
                                                    
                                                    // Build column position map from data rows
                                                    const allDataRows = clickedSpreadsheet.querySelectorAll('tbody tr, tr[data-dash-row]');
                                                    const columnPositionMap = new Map();
                                                    
                                                    allDataRows.forEach((row, rowIndex) => {
                                                        if (row.querySelector('th')) return;
                                                        
                                                        const rowCells = Array.from(row.querySelectorAll('td'));
                                                        let dataColIndex = 0;
                                                        
                                                        rowCells.forEach(cell => {
                                                            const colId = cell.getAttribute('data-dash-column');
                                                            if (colId === 'DateStr') return;
                                                            
                                                            if (dataColIndex >= topRowDataStart && dataColIndex < topRowDataStart + spanCount) {
                                                                if (!columnPositionMap.has(dataColIndex) && colId && colId !== 'DateStr') {
                                                                    columnPositionMap.set(dataColIndex, colId);
                                                                }
                                                            }
                                                            
                                                            if (colId && colId !== 'DateStr') {
                                                                dataColIndex++;
                                                            }
                                                        });
                                                    });
                                                    
                                                    for (let i = topRowDataStart; i < topRowDataStart + spanCount; i++) {
                                                        if (columnPositionMap.has(i)) {
                                                            columnIds.add(columnPositionMap.get(i));
                                                        }
                                                    }
                                                }
                                            } else {
                                                // Single column or find by text
                                                const allTopHeaders = Array.from(topRow.querySelectorAll('th[data-dash-column]:not([data-dash-column="DateStr"])'));
                                                const matchingTopHeaders = allTopHeaders.filter(h => {
                                                    const hText = h.textContent.trim();
                                                    return hText === topHeaderText || h === header || h.contains(header);
                                                });
                                                
                                                matchingTopHeaders.forEach(topH => {
                                                    const colId = topH.getAttribute('data-dash-column');
                                                    if (colId) columnIds.add(colId);
                                                });
                                                
                                                if (columnIds.size === 0 && columnId) {
                                                    columnIds.add(columnId);
                                                }
                                            }
                                            
                                            // Highlight the clicked top header
                                            header.classList.add('column-selected');
                                            header.style.backgroundColor = '#b3d9ff';
                                            header.style.color = '#1b365d';
                                            header.style.fontWeight = 'bold';
                                            
                                            // Highlight data cells for all columns under this top header
                                            columnIds.forEach(colId => {
                                                const colCells = clickedSpreadsheet.querySelectorAll(`td[data-dash-column="${colId}"]`);
                                                colCells.forEach(cell => {
                                                    cell.classList.add('column-cell-selected');
                                                    cell.style.backgroundColor = '#b3d9ff';
                                                    cell.style.border = '';
                                                    cell.style.fontWeight = '600';
                                                    cell.style.color = '#1b365d';
                                                    cell.style.opacity = '1';
                                                });
                                            });
                                            
                                            clickedSpreadsheet.classList.add('column-selection-active');
                                            
                                            // Dim other columns
                                            const allDataCells = clickedSpreadsheet.querySelectorAll('td[data-dash-column]:not([data-dash-column="DateStr"])');
                                            allDataCells.forEach(cell => {
                                                const cellColId = cell.getAttribute('data-dash-column');
                                                if (!columnIds.has(cellColId)) {
                                                    cell.style.opacity = '0.3';
                                                }
                                            });
                                        }
                                    } else {
                                        // Bottom header clicked
                                        const bottomRow = headerRows[headerRows.length - 1];
                                        if (bottomRow) {
                                            const bottomRowHeaders = bottomRow.querySelectorAll(`th[data-dash-column="${columnId}"]`);
                                            bottomRowHeaders.forEach(h => {
                                                h.classList.add('column-selected');
                                                h.style.backgroundColor = '#b3d9ff';
                                                h.style.color = '#1b365d';
                                                h.style.fontWeight = 'bold';
                                            });
                                        }
                                        
                                        // Highlight all data cells for this column
                                        const columnCells = clickedSpreadsheet.querySelectorAll(`td[data-dash-column="${columnId}"]`);
                                        columnCells.forEach(cell => {
                                            cell.classList.add('column-cell-selected');
                                            cell.style.backgroundColor = '#b3d9ff';
                                            cell.style.border = '';
                                            cell.style.fontWeight = '600';
                                            cell.style.color = '#1b365d';
                                            cell.style.opacity = '1';
                                        });
                                        
                                        clickedSpreadsheet.classList.add('column-selection-active');
                                        
                                        // Dim other columns
                                        const allDataCells = clickedSpreadsheet.querySelectorAll('td[data-dash-column]:not([data-dash-column="DateStr"])');
                                        allDataCells.forEach(cell => {
                                            if (!cell.classList.contains('column-cell-selected')) {
                                                cell.style.opacity = '0.3';
                                            }
                                        });
                                    }
                                } else {
                                    // Middle header - highlight the clicked header and find columns under it
                                    const headerColspan = header.getAttribute('colspan') || header.colSpan;
                                    const spanCount = headerColspan ? parseInt(headerColspan) : 1;
                                    
                                    const columnIds = new Set();
                                    
                                    if (spanCount > 1) {
                                        // Header spans multiple columns
                                        const currentRow = headerRows[headerIndex];
                                        if (currentRow) {
                                            const allRowCells = Array.from(currentRow.querySelectorAll('th'));
                                            let clickedCellIndex = -1;
                                            
                                            for (let i = 0; i < allRowCells.length; i++) {
                                                if (allRowCells[i] === header || allRowCells[i].contains(header)) {
                                                    clickedCellIndex = i;
                                                    break;
                                                }
                                            }
                                            
                                            let columnsBefore = 0;
                                            for (let i = 0; i < clickedCellIndex; i++) {
                                                const cell = allRowCells[i];
                                                const cellColId = cell.getAttribute('data-dash-column');
                                                if (cellColId === 'DateStr') continue;
                                                const cellColspan = parseInt(cell.getAttribute('colspan') || cell.colSpan || '1');
                                                columnsBefore += cellColspan;
                                            }
                                            
                                            // Build column position map
                                            const allDataRows = clickedSpreadsheet.querySelectorAll('tbody tr, tr[data-dash-row]');
                                            const columnPositionMap = new Map();
                                            
                                            allDataRows.forEach(row => {
                                                if (row.querySelector('th')) return;
                                                
                                                const rowCells = Array.from(row.querySelectorAll('td'));
                                                let dataColIndex = 0;
                                                
                                                rowCells.forEach(cell => {
                                                    const colId = cell.getAttribute('data-dash-column');
                                                    if (colId === 'DateStr') return;
                                                    
                                                    if (dataColIndex >= columnsBefore && dataColIndex < columnsBefore + spanCount) {
                                                        if (!columnPositionMap.has(dataColIndex) && colId) {
                                                            columnPositionMap.set(dataColIndex, colId);
                                                        }
                                                    }
                                                    
                                                    if (colId) {
                                                        dataColIndex++;
                                                    }
                                                });
                                            });
                                            
                                            for (let i = columnsBefore; i < columnsBefore + spanCount; i++) {
                                                if (columnPositionMap.has(i)) {
                                                    columnIds.add(columnPositionMap.get(i));
                                                }
                                            }
                                        }
                                    } else {
                                        // Single column
                                        columnIds.add(columnId);
                                    }
                                    
                                    // Highlight the clicked header
                                    if (headerIndex >= 0 && headerRows.length > 0) {
                                        header.classList.add('column-selected');
                                        header.style.backgroundColor = '#b3d9ff';
                                        header.style.color = '#1b365d';
                                        header.style.fontWeight = 'bold';
                                    }
                                    
                                    // Highlight data cells for all columns under this middle header
                                    columnIds.forEach(colId => {
                                        const colCells = clickedSpreadsheet.querySelectorAll(`td[data-dash-column="${colId}"]`);
                                        colCells.forEach(cell => {
                                            cell.classList.add('column-cell-selected');
                                            cell.style.backgroundColor = '#b3d9ff';
                                            cell.style.border = '';
                                            cell.style.fontWeight = '600';
                                            cell.style.color = '#1b365d';
                                            cell.style.opacity = '1';
                                        });
                                    });
                                    
                                    clickedSpreadsheet.classList.add('column-selection-active');
                                    
                                    // Dim other columns
                                    const allDataCells = clickedSpreadsheet.querySelectorAll('td[data-dash-column]:not([data-dash-column="DateStr"])');
                                    allDataCells.forEach(cell => {
                                        const cellColId = cell.getAttribute('data-dash-column');
                                        if (!columnIds.has(cellColId)) {
                                            cell.style.opacity = '0.3';
                                        }
                                    });
                                }
                            }
                            return false;
                        }
                        
                        // Handle row highlighting when clicking on DateStr cell
                        const dateCell = event.target.closest('td[data-dash-column="DateStr"]');
                        if (dateCell) {
                            event.stopPropagation();
                            
                            // Clear column selections first
                            clearAllColumnSelections(clickedSpreadsheet);
                            clearAllRowSelections(clickedSpreadsheet);
                            if (window.gpwTableState) {
                                window.gpwTableState.selectedColumnId = null;
                            }
                            
                            // Get the date value
                            const dateValue = getCellValue(dateCell);
                            
                            if (dateValue) {
                                // Check if this date is already selected
                                if (window.gpwTableState && window.gpwTableState.selectedDate === dateValue) {
                                    // Deselect date - clear all row selections
                                    clearAllRowSelections(clickedSpreadsheet);
                                    if (window.gpwTableState) {
                                        window.gpwTableState.selectedDate = null;
                                        window.gpwTableState.selectedRowIndex = null;
                                    }
                                } else {
                                    // Clear any previous selection
                                    clearAllRowSelections(clickedSpreadsheet);
                                    
                                    // Find all rows with this date and highlight them
                                    const allDataRows = Array.from(clickedSpreadsheet.querySelectorAll('tbody tr'));
                                    let currentDate = null;
                                    
                                    allDataRows.forEach((row) => {
                                        const rowDateCell = row.querySelector('td[data-dash-column="DateStr"]');
                                        let rowDateValue = null;
                                        
                                        if (rowDateCell) {
                                            const cellValue = getCellValue(rowDateCell);
                                            if (cellValue && cellValue.trim() !== '') {
                                                rowDateValue = cellValue;
                                                currentDate = cellValue;
                                            } else {
                                                rowDateValue = currentDate;
                                            }
                                        } else {
                                            rowDateValue = currentDate;
                                        }
                                        
                                        // Check if this row matches the selected date
                                        if (rowDateValue === dateValue) {
                                            // Highlight all cells in this row except DateStr
                                            const allRowCells = Array.from(row.querySelectorAll('td'));
                                            allRowCells.forEach(c => {
                                                const colId = c.getAttribute('data-dash-column');
                                                if (colId !== 'DateStr') {
                                                    c.classList.add('row-cell-selected');
                                                    c.style.backgroundColor = '#b3d9ff';
                                                    c.style.border = 'none';
                                                    c.style.fontWeight = '600';
                                                    c.style.color = '#1b365d';
                                                    c.style.opacity = '1';
                                                } else {
                                                    // DateStr cells: keep at normal state
                                                    c.classList.remove('row-cell-selected');
                                                    c.style.backgroundColor = '';
                                                    c.style.border = '';
                                                    c.style.fontWeight = '';
                                                    c.style.color = '';
                                                    c.style.opacity = '1';
                                                }
                                            });
                                            row.classList.add('row-selected');
                                        }
                                    });
                                    
                                    if (window.gpwTableState) {
                                        window.gpwTableState.selectedDate = dateValue;
                                        window.gpwTableState.selectedRowIndex = null;
                                    }
                                    
                                    // Add row-selection-active class to dim other rows
                                    clickedSpreadsheet.classList.add('row-selection-active');
                                    clickedSpreadsheet.classList.remove('column-selection-active');
                                    
                                    // Explicitly dim non-selected rows (both via CSS class and inline style as fallback)
                                    // Exclude DateStr column from dimming
                                    allDataRows.forEach((row) => {
                                        if (!row.classList.contains('row-selected')) {
                                            const rowCells = row.querySelectorAll('td');
                                            rowCells.forEach(c => {
                                                const colId = c.getAttribute('data-dash-column');
                                                // Don't dim DateStr column
                                                if (colId !== 'DateStr') {
                                                    // Remove any inline opacity first, then let CSS handle it
                                                    // But also set it explicitly as fallback
                                                    c.style.opacity = '0.3';
                                                } else {
                                                    // Keep DateStr at full opacity
                                                    c.style.opacity = '1';
                                                }
                                            });
                                        }
                                    });
                                }
                            }
                            return false;
                        }
                        
                        // If clicking on a data cell (not DateStr), highlight the row and dim others
                        const cell = event.target.closest('td[data-dash-column]');
                        if (cell) {
                            const columnId = cell.getAttribute('data-dash-column');
                            if (columnId && columnId !== 'DateStr') {
                                // Clear column selections first
                                clearAllColumnSelections(clickedSpreadsheet);
                                
                                // Get the row containing this cell
                                const row = cell.closest('tbody tr');
                                if (row) {
                                    // Check if this row is already selected
                                    const isRowSelected = row.classList.contains('row-selected');
                                    
                                    if (isRowSelected) {
                                        // Deselect row - clear all row selections
                                        clearAllRowSelections(clickedSpreadsheet);
                                        clickedSpreadsheet.classList.remove('row-selection-active');
                                        if (window.gpwTableState) {
                                            window.gpwTableState.selectedRowIndex = null;
                                            window.gpwTableState.selectedDate = null;
                                        }
                                    } else {
                                        // Clear any previous row selection
                                        clearAllRowSelections(clickedSpreadsheet);
                                        
                                        // Get the date value from this row
                                        const rowDateCell = row.querySelector('td[data-dash-column="DateStr"]');
                                        let dateValue = null;
                                        
                                        if (rowDateCell) {
                                            dateValue = getCellValue(rowDateCell);
                                        }
                                        
                                        // Find all rows with the same date and highlight them
                                        const allDataRows = Array.from(clickedSpreadsheet.querySelectorAll('tbody tr'));
                                        let currentDate = null;
                                        
                                        allDataRows.forEach((dataRow) => {
                                            const dataRowDateCell = dataRow.querySelector('td[data-dash-column="DateStr"]');
                                            let rowDateValue = null;
                                            
                                            if (dataRowDateCell) {
                                                const cellValue = getCellValue(dataRowDateCell);
                                                if (cellValue && cellValue.trim() !== '') {
                                                    rowDateValue = cellValue;
                                                    currentDate = cellValue;
                                                } else {
                                                    rowDateValue = currentDate;
                                                }
                                            } else {
                                                rowDateValue = currentDate;
                                            }
                                            
                                            // Check if this row matches the selected date
                                            if (dateValue && rowDateValue === dateValue) {
                                                // Highlight all cells in this row except DateStr
                                                const allRowCells = Array.from(dataRow.querySelectorAll('td'));
                                                allRowCells.forEach(c => {
                                                    const colId = c.getAttribute('data-dash-column');
                                                    if (colId !== 'DateStr') {
                                                        c.classList.add('row-cell-selected');
                                                        c.style.backgroundColor = '#b3d9ff';
                                                        c.style.border = 'none';
                                                        c.style.fontWeight = '600';
                                                        c.style.color = '#1b365d';
                                                        c.style.opacity = '1';
                                                    } else {
                                                        // DateStr cells: keep at normal state
                                                        c.classList.remove('row-cell-selected');
                                                        c.style.backgroundColor = '';
                                                        c.style.border = '';
                                                        c.style.fontWeight = '';
                                                        c.style.color = '';
                                                        c.style.opacity = '1';
                                                    }
                                                });
                                                dataRow.classList.add('row-selected');
                                            }
                                        });
                                        
                                        // Add row-selection-active class to dim other rows
                                        clickedSpreadsheet.classList.add('row-selection-active');
                                        clickedSpreadsheet.classList.remove('column-selection-active');
                                        
                                        // Explicitly dim non-selected rows (both via CSS class and inline style as fallback)
                                        // Exclude DateStr column from dimming
                                        allDataRows.forEach((row) => {
                                            if (!row.classList.contains('row-selected')) {
                                                const rowCells = row.querySelectorAll('td');
                                                rowCells.forEach(c => {
                                                    const colId = c.getAttribute('data-dash-column');
                                                    // Don't dim DateStr column
                                                    if (colId !== 'DateStr') {
                                                        // Remove any inline opacity first, then let CSS handle it
                                                        // But also set it explicitly as fallback
                                                        c.style.opacity = '0.3';
                                                    } else {
                                                        // Keep DateStr at full opacity
                                                        c.style.opacity = '1';
                                                    }
                                                });
                                            }
                                        });
                                        
                                        if (window.gpwTableState) {
                                            window.gpwTableState.selectedDate = dateValue;
                                            window.gpwTableState.selectedRowIndex = null;
                                            window.gpwTableState.selectedColumnId = null;
                                        }
                                    }
                                } else {
                                    // No row found, clear selections
                                    clearAllRowSelections(clickedSpreadsheet);
                                    clickedSpreadsheet.classList.remove('row-selection-active');
                                    
                                    if (window.gpwTableState) {
                                        window.gpwTableState.selectedColumnId = null;
                                        window.gpwTableState.selectedRowIndex = null;
                                        window.gpwTableState.selectedDate = null;
                                    }
                                }
                            }
                        }
                    };
                    
                    spreadsheet._gpwClickHandler = clickHandler;
                    
                    // Add click handler with capture phase
                    spreadsheet.addEventListener('click', spreadsheet._gpwClickHandler, true);
                }
                
                // Clear selection on outside click
                if (!window.gpwTableOutsideClickHandler) {
                    window.gpwTableOutsideClickHandler = function(event) {
                        const tableEl = document.getElementById('gpw-data-table');
                        if (!tableEl) return;
                        const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                        if (!spreadsheet) return;
                        
                        if (!spreadsheet.contains(event.target)) {
                            clearAllColumnSelections(spreadsheet);
                            clearAllRowSelections(spreadsheet);
                            if (window.gpwTableState) {
                                window.gpwTableState.selectedColumnId = null;
                                window.gpwTableState.selectedRowIndex = null;
                                window.gpwTableState.selectedDate = null;
                            }
                        }
                    };
                    document.addEventListener('click', window.gpwTableOutsideClickHandler);
                }

                // Reset enhanced flag when container updates
                const tableEl = document.getElementById('gpw-data-table');
                if (tableEl) {
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    if (spreadsheet) {
                        spreadsheet.dataset.gpwEnhanced = 'false';
                        
                        if (spreadsheet._gpwClickHandler) {
                            spreadsheet.removeEventListener('click', spreadsheet._gpwClickHandler, true);
                            spreadsheet._gpwClickHandler = null;
                        }
                        
                        clearAllColumnSelections(spreadsheet);
                        clearAllRowSelections(spreadsheet);
                        
                        if (window.gpwTableState) {
                            window.gpwTableState.selectedColumnId = null;
                            window.gpwTableState.selectedRowIndex = null;
                            window.gpwTableState.selectedDate = null;
                            window.gpwTableState.lastTableSignature = null;
                        }
                        
                setTimeout(function() {
                            enhanceTable();
                        }, 200);
                    }
                }
                
                // Apply enhancements with multiple attempts
                function tryEnhance() {
                    const tableEl = document.getElementById('gpw-data-table');
                    if (!tableEl) {
                        return false;
                    }
                    
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    if (!spreadsheet) {
                        return false;
                    }
                    
                    const headers = spreadsheet.querySelectorAll('th[data-dash-column]');
                    if (headers.length === 0) {
                        return false;
                    }
                    
                    const isEnhanced = spreadsheet.dataset.gpwEnhanced === 'true';
                    
                    if (!isEnhanced) {
                        enhanceTable();
                        return true;
                    }
                    
                    return true;
                }
                
                // Try immediately
                if (!tryEnhance()) {
                    setTimeout(function() {
                        if (!tryEnhance()) {
                            setTimeout(function() {
                                if (!tryEnhance()) {
                                    setTimeout(function() {
                                        tryEnhance();
                                    }, 1000);
                                }
                            }, 300);
                        }
                }, 100);
                }
                
                // Use MutationObserver to re-enhance when table structure changes
                if (!window.gpwTableMutationObserver) {
                    window.gpwTableMutationObserver = new MutationObserver(function(mutations) {
                        const tableEl = document.getElementById('gpw-data-table');
                        if (tableEl) {
                            const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                            if (spreadsheet) {
                                const headers = spreadsheet.querySelectorAll('th[data-dash-column]');
                                
                                let tableSignature = '';
                                const topRow = spreadsheet.querySelector('thead tr');
                                if (topRow && headers.length > 0) {
                                    const topHeaders = Array.from(topRow.querySelectorAll('th')).slice(0, 5);
                                    tableSignature = topHeaders.map(h => h.textContent.trim()).join('|') + '|' + headers.length;
                                } else if (headers.length > 0) {
                                    tableSignature = headers.length.toString();
                                }
                                
                                if (headers.length > 0 && 
                                    (spreadsheet.dataset.gpwEnhanced !== 'true' || 
                                     window.gpwTableState.lastTableSignature !== tableSignature)) {
                                    setTimeout(function() {
                                        enhanceTable();
                                    }, 100);
                                }
                            }
                        }
                    });
                    window.gpwTableMutationObserver.observe(document.body, { 
                        childList: true, 
                        subtree: true 
                    });
                }
                
                setTimeout(function() {
                    tryEnhance();
                }, 50);
                
            } catch (error) {
                // Error handled silently
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('gpw-table-dummy-output', 'children'),
        [Input('gpw-data-table-container', 'children'),
         Input('gpw-data-table', 'data')],
        prevent_initial_call=False
    )
