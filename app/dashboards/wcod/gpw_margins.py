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
from core.data_helpers import execute_query

# Data locations
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "Gross_Product_Worth_and_Margins"
)
GPW_CSV = os.path.join(DATA_DIR, "Gross Product Worth_data.csv")
INCREMENTAL_MARGINS_CSV = os.path.join(DATA_DIR, "Incremental Margins_data.csv")
DATA_TABLE_CSV = os.path.join(DATA_DIR, "Data Table_data.csv")


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


def _load_data_table_data() -> pd.DataFrame:
    """Load and normalize Data Table data."""
    df = _read_csv(DATA_TABLE_CSV)
    if df.empty:
        return df
    
    # Normalize column names
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
        df['Date'] = pd.to_datetime(df['MonthDateParsed'], format='%b %y', errors='coerce')
    
    if 'Value' in df.columns:
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
    
    df = df.dropna(subset=['Value', 'Date'])
    return df


def _load_data_table_data_from_db(region: str = None) -> pd.DataFrame:
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

def _get_available_crudes():
    """Get available crudes from database."""
    try:
        query = """
        SELECT DISTINCT crude_name AS "Crude"
        FROM fact_wcod_prices
        WHERE price_type IN ('GPW', 'Refining Margin')
            AND crude_name IS NOT NULL
        ORDER BY crude_name
        """
        rows = execute_query(query)
        if rows:
            return [row['Crude'] for row in rows]
        return []
    except Exception as e:
        print(f"[gpw_margins] Error getting crudes: {e}")
        return []

def _get_available_tech_types():
    """Get available tech types from database."""
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
        ORDER BY "TechTypeFull"
        """
        rows = execute_query(query)
        if rows:
            return [row['TechTypeFull'] for row in rows]
        return []
    except Exception as e:
        print(f"[gpw_margins] Error getting tech types: {e}")
        return []

# Get filter options from database
REGIONS = _get_available_regions()
CRUDES = _get_available_crudes()
TECH_TYPES = _get_available_tech_types()

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
    'Urals': '#d62728'
}

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
DEFAULT_START_DATE = datetime(2019, 1, 1)
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
        paper_bgcolor="white",
        plot_bgcolor="white",
        height=height,
        margin=dict(l=0, r=0, t=10, b=0),
    )
    return fig


def _build_gpw_chart(df: pd.DataFrame, tech_type: str, title: str, selected_crudes: list = None, region: str = None) -> go.Figure:
    """Build a Gross Product Worth chart for a specific technology type."""
    if df.empty:
        return _empty_figure(f"No data available for {tech_type}")
    
    fig = go.Figure()
    
    # Filter by tech type
    tech_df = df[df['TechType'] == tech_type].copy()
    
    if tech_df.empty:
        return _empty_figure(f"No data available for {tech_type}")
    
    # Get unique crudes for this tech type
    available_crudes = sorted(tech_df['Crude'].unique())
    
    # Filter by selected crudes if provided
    if selected_crudes and 'ALL' not in selected_crudes:
        available_crudes = [c for c in available_crudes if c in selected_crudes]
    
    if not available_crudes:
        return _empty_figure(f"No crudes selected for {tech_type}")
    
    # Map tech type to display name
    tech_display = "FCC" if tech_type == "Catalytic Cracking" else "HSK" if tech_type == "Hydroskimming" else tech_type
    
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
                    f"Refining Complexity: {tech_display}<br>"
                    f"Date: {date_str}<br>"
                    f"Gross Product Worth: {row['Value']:.1f} ($/bbl)"
                )
                hover_texts.append(hover_text)
            
            fig.add_trace(go.Scatter(
                x=crude_df['Date'],
                y=crude_df['Value'],
                mode='lines+markers',
                name=crude,
                line=dict(color=color, width=2),
                marker=dict(size=4),
                customdata=hover_texts,
                hovertemplate="%{customdata}<extra></extra>"
            ))
    
    fig.update_layout(
        xaxis=dict(
            title="Date",
            showgrid=True,
            gridcolor="#e0e0e0",
            linecolor="#cccccc", # Added x-axis line color
            tickangle=-45,
            dtick="M6",  # Show ticks every 6 months
            tickformat="%b %y" # Format as "Jan 19"
        ),
        yaxis=dict(
            title="Gross Product Worth ($/bbl)",
            showgrid=True,
            gridcolor="#e0e0e0"
        ),
        hovermode='closest',
        height=400,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=60, r=20, t=80, b=50),
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


def _build_incremental_margins_chart(df: pd.DataFrame, tech_type: str, title: str, selected_crudes: list = None, region: str = None) -> go.Figure:
    """Build an Incremental Margins chart for a specific technology type."""
    if df.empty:
        return _empty_figure(f"No data available for {tech_type}")
    
    fig = go.Figure()
    
    # Filter by tech type
    tech_df = df[df['TechType'] == tech_type].copy()
    
    if tech_df.empty:
        return _empty_figure(f"No data available for {tech_type}")
    
    # Get unique crudes for this tech type
    available_crudes = sorted(tech_df['Crude'].unique())
    
    # Filter by selected crudes if provided
    if selected_crudes and 'ALL' not in selected_crudes:
        available_crudes = [c for c in available_crudes if c in selected_crudes]
    
    if not available_crudes:
        return _empty_figure(f"No crudes selected for {tech_type}")
    
    # Map tech type to display name
    tech_display = "FCC" if tech_type == "Catalytic Cracking" else "HSK" if tech_type == "Hydroskimming" else tech_type
    
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
                    f"Refining Complexity: {tech_display}<br>"
                    f"Date: {date_str}<br>"
                    f"Incremental Margins: {row['Value']:.1f} ($/bbl)"
                )
                hover_texts.append(hover_text)
            
            fig.add_trace(go.Scatter(
                x=crude_df['Date'],
                y=crude_df['Value'],
                mode='lines+markers',
                name=crude,
                line=dict(color=color, width=2),
                marker=dict(size=4),
                customdata=hover_texts,
                hovertemplate="%{customdata}<extra></extra>"
            ))
    
    fig.update_layout(
        xaxis=dict(
            title="Date",
            showgrid=True,
            gridcolor="#e0e0e0",
            linecolor="#cccccc", # Added x-axis line color
            tickangle=-45,
            dtick="M6",  # Show ticks every 6 months
            tickformat="%b %y" # Format as "Jan 19"
        ),
        yaxis=dict(
            title="Incremental Margins ($/bbl)",
            showgrid=True,
            gridcolor="#e0e0e0",
            zeroline=False # Hide the zero line
        ),
        hovermode='closest',
        height=400,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=60, r=20, t=80, b=50),
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


def _prepare_data_table(df: pd.DataFrame, start_date, end_date, region, selected_crudes=None, selected_tech_types=None) -> tuple:
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
        return [], [], []
    
    # Filter by date range
    filtered_df = df[
        (df['Date'] >= start_date) &
        (df['Date'] <= end_date)
    ].copy()
    
    # Filter by region if Region column exists
    if region and 'Region' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Region'] == region]
    
    if filtered_df.empty:
        return [], []
    
    # Define the order of crudes
    CRUDE_ORDER = ['Arab Light', 'Bonny Light', 'Brent Blend', 'Urals']
    DATA_TYPES = ['GPW', 'Refining Margin']
    TECH_TYPES = ['Catalytic Cracking', 'Hydroskimming']
    
    # Filter by selected crudes and tech types
    if selected_crudes:
        CRUDE_ORDER = [c for c in CRUDE_ORDER if c in selected_crudes]
    if selected_tech_types:
        TECH_TYPES = [t for t in TECH_TYPES if t in selected_tech_types]
    
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
            'type': 'text'
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
    
    return columns, data, tooltip_data


def create_layout():
    """Create the GPW Margins layout with filters and charts."""
    return html.Div([
        # Store to track initial load state
        dcc.Store(id='gpw-initial-load', data=True),
        dcc.Store(id='gpw-crude-filter-previous', data=None),
        dcc.Store(id='gpw-refining-complexity-filter-previous', data=None),
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
                .rc-slider-track-1,
                .rc-slider-track-2,
                div[class*="rc-slider-track"] {
                    background: #6E6E6E !important;
                    height: 4px !important;
                }
                .rc-slider-rail {
                    background: #D3D3D3 !important;
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
                    'marginBottom': '30px',
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
                            'marginBottom': '5px'
                        }
                    ),
                    html.Div([
                        html.Div([
                            dcc.Input(
                                id="gpw-date-range-min-input",
                                type="text",
                                value=_format_date_for_display(DEFAULT_START_DATE),
                                style={'display': 'inline-block', 'border': '0px solid #dee2e6', 'color': '#1b365d', 'fontSize': '11px', 'fontFamily': 'Arial', 'lineHeight': '12px', 'fontWeight': 'bold', 'backgroundColor': 'unset'}
                            ),
                            dcc.Input(
                                id="gpw-date-range-max-input",
                                type="text",
                                value=_format_date_for_display(DEFAULT_END_DATE),
                                disabled=True,
                                readOnly=True,
                                style={'width': '15%', 'display': 'inline-block', 'float': 'right', 'border': '0px solid #dee2e6', 'color': '#1b365d', 'fontSize': '11px', 'fontFamily': 'Arial', 'lineHeight': '12px', 'fontWeight': 'bold', 'backgroundColor': 'unset', 'cursor': 'default', 'pointer-events': 'none'}
                            ),
                        ], style={'width': '100%', 'marginBottom': '10px', 'position': 'relative'}),
                        html.Div([
                            dcc.Slider(
                                id="gpw-date-range-slider",
                                min=0,
                                max=max(len(DATE_LIST) - 1, 0) if DATE_LIST else 0,
                                step=1,
                                value=DEFAULT_START_INDEX,
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
                            'marginBottom': '5px'
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
                'padding': '20px',
                'marginBottom': '0px',
                'borderRadius': '5px'
            })
        ], style={'padding': '20px'}),
        
        # Gross Product Worth Section
        html.Div([
            html.Div([
                html.Div([
                    html.H3(
                        "NWE - Gross Product Worth ($/bbl)",
                        style={
                            'color': '#fe5000',
                            'textAlign': 'center',
                            'marginBottom': '30px',
                            'marginTop': '20px',
                            'fontSize': '20px',
                            'fontWeight': 'bold',
                            'paddingBottom': '10px',
                            'borderBottom': '0px solid #fe5000'
                        }
                    ),
                    
                    html.Div([
                        html.Div([
                            html.H4(
                                "Catalytic Cracking",
                                style={
                                    'color': '#1b365d',
                                    'textAlign': 'center',
                                    'marginBottom': '15px',
                                    'fontSize': '16px',
                                    'fontWeight': 'bold'
                                }
                            ),
                            dcc.Graph(id='gpw-catalytic-cracking-chart')
                        ], className='col-md-6', style={'padding': '15px'}),
                        
                        html.Div([
                            html.H4(
                                "Hydroskimming",
                                style={
                                    'color': '#1b365d',
                                    'textAlign': 'center',
                                    'marginBottom': '15px',
                                    'fontSize': '16px',
                                    'fontWeight': 'bold'
                                }
                            ),
                            dcc.Graph(id='gpw-hydroskimming-chart')
                        ], className='col-md-6', style={'padding': '15px'})
                    ], className='row')
                ], className='col-md-10', style={'padding': '15px'}),
                
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
                        options=[
                            {'label': 'ALL', 'value': 'ALL'},
                            {'label': 'FCC', 'value': 'Catalytic Cracking'},
                            {'label': 'HSK', 'value': 'Hydroskimming'}
                        ],
                        value=['ALL'] + TECH_TYPES.copy() if TECH_TYPES else ['ALL'],
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
                        style={
                            'fontWeight': 'bold',
                            'color': '#2c3e50',
                            'fontSize': '12px',
                            'marginBottom': '8px',
                            'marginTop': '10px'
                        }
                    ),
                    # Crude Legend with row click selection (no checkboxes)
                    html.Div([
                        html.Div(
                            id={'type': 'gpw-crude-legend-item', 'crude': crude},
                            n_clicks=0,
                            children=[
                                html.Div(
                                    style={
                                        'width': '14px',
                                        'height': '14px',
                                        'backgroundColor': CRUDE_COLORS.get(crude, FALLBACK_COLORS[idx % len(FALLBACK_COLORS)]),
                                        'borderRadius': '2px',
                                        'marginRight': '10px',
                                        'border': '1px solid #cfd8e3',
                                        'boxShadow': '0 0 2px rgba(0,0,0,0.1)',
                                        'display': 'inline-block',
                                        'verticalAlign': 'middle'
                                    }
                                ),
                                html.Span(
                                    crude,
                                    style={
                                        'color': '#1b365d',
                                        'fontWeight': '600',
                                        'fontSize': '13px',
                                        'verticalAlign': 'middle'
                                    }
                                )
                            ],
                            style={
                                'display': 'flex',
                                'alignItems': 'center',
                                'padding': '6px 8px',
                                'marginBottom': '2px',
                                'borderRadius': '4px',
                                'cursor': 'pointer',
                                'transition': 'background-color 0.2s ease',
                                'userSelect': 'none',
                                'backgroundColor': '#ffffff',
                                'border': '1px solid transparent'
                            }
                        ) for idx, crude in enumerate(CRUDES)
                    ]),
                    # Hidden checklist to store selected values
                    dcc.Checklist(
                        id='gpw-crude-legend',
                        options=[{'label': c, 'value': c} for c in CRUDES],
                        value=CRUDES.copy() if CRUDES else [],
                        style={'display': 'none'}
                    ),
                ], className='col-md-2', style={
                    'padding': '25px 20px',
                    'border': '0px solid #dfe3eb',
                    'borderRadius': '6px',
                    'backgroundColor': '#f8f9fb',
                    'height': '100%',
                    'maxHeight': '600px',
                    'overflowY': 'auto',
                    'boxShadow': '0 2px 6px rgba(0,0,0,0.05)',
                    'marginLeft': '0',
                }),
            ], className='row')
        ], style={'padding': '20px', 'marginBottom': '30px'}),
        
        # Incremental Margins Section
        html.Div([
            html.Div([
                html.Div([
                    html.H3(
                        "NWE - Incremental Margins ($/bbl)",
                        style={
                            'color': '#fe5000',
                            'textAlign': 'center',
                            'marginBottom': '30px',
                            'marginTop': '20px',
                            'fontSize': '20px',
                            'fontWeight': 'bold',
                            'paddingBottom': '10px',
                            'borderBottom': '0px solid #fe5000'
                        }
                    ),
                    
                    html.Div([
                        html.Div([
                            html.H4(
                                "Catalytic Cracking",
                                style={
                                    'color': '#1b365d',
                                    'textAlign': 'center',
                                    'marginBottom': '15px',
                                    'fontSize': '16px',
                                    'fontWeight': 'bold'
                                }
                            ),
                            dcc.Graph(id='gpw-incremental-catalytic-chart')
                        ], className='col-md-6', style={'padding': '15px'}),
                        
                        html.Div([
                            html.H4(
                                "Hydroskimming",
                                style={
                                    'color': '#1b365d',
                                    'textAlign': 'center',
                                    'marginBottom': '15px',
                                    'fontSize': '16px',
                                    'fontWeight': 'bold'
                                }
                            ),
                            dcc.Graph(id='gpw-incremental-hydroskimming-chart')
                        ], className='col-md-6', style={'padding': '15px'})
                    ], className='row')
                ], className='col-md-10', style={'padding': '15px'}),
                
                # Empty column to maintain layout (filters already shown above)
                html.Div([
                ], className='col-md-2', style={'padding': '15px'}),
            ], className='row')
        ], style={'padding': '20px', 'marginBottom': '30px'}),
        
        # Data Table Section
        html.Div([
            html.Div([
                html.Div([
                    html.H3(
                        "NWE - Data Table ($/bbl)",
                        style={
                            'color': '#fe5000',
                            'textAlign': 'center',
                            'marginBottom': '20px',
                            'fontSize': '20px',
                            'fontWeight': 'bold'
                        }
                    ),
                    
                    html.Div(
                        id='gpw-data-table-container',
                        children=[
                        dash_table.DataTable(
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
                                'textAlign': 'center',
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
                                    'backgroundColor': '#f8f9fa'
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
    
    # Bidirectional sync: Date range input fields <-> slider
    @dash_app.callback(
        [
            Output('gpw-date-range-slider', 'value', allow_duplicate=True),
            Output('gpw-date-range-min-input', 'value', allow_duplicate=True),
            Output('gpw-date-range-max-input', 'value', allow_duplicate=True)
        ],
        [
            Input('gpw-date-range-min-input', 'value'),
            Input('gpw-date-range-max-input', 'value'),
            Input('gpw-date-range-slider', 'value')
        ],
        prevent_initial_call=True
    )
    def sync_date_range(min_input, max_input, slider_value):
        """Sync date range inputs with slider. Single slider for start date only."""
        ctx = callback_context
        
        if not ctx.triggered:
            return DEFAULT_START_INDEX, _format_date_for_display(DEFAULT_START_DATE), _format_date_for_display(DEFAULT_END_DATE)
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'gpw-date-range-min-input':
            # Start date input changed, update slider (end date stays fixed)
            if min_input:
                # Parse date string like "Jan 19" back to date
                try:
                    min_date = pd.to_datetime(min_input, format='%b %y', errors='coerce')
                    if pd.notna(min_date):
                        min_idx = _date_to_index(min_date)
                        # Ensure min doesn't exceed max
                        if min_idx > DEFAULT_END_INDEX:
                            min_idx = DEFAULT_END_INDEX
                        return min_idx, min_input, _format_date_for_display(DEFAULT_END_DATE)
                except Exception:
                    pass
        elif trigger_id == 'gpw-date-range-slider':
            # Slider changed, update start date input (end date stays fixed)
            if slider_value is not None:
                # Ensure slider value doesn't exceed max
                if slider_value > DEFAULT_END_INDEX:
                    slider_value = DEFAULT_END_INDEX
                min_date = _index_to_date(slider_value)
                return slider_value, _format_date_for_display(min_date), _format_date_for_display(DEFAULT_END_DATE)
        
        return DEFAULT_START_INDEX, _format_date_for_display(DEFAULT_START_DATE), _format_date_for_display(DEFAULT_END_DATE)
    
    @dash_app.callback(
        Output('gpw-catalytic-cracking-chart', 'figure'),
        Output('gpw-hydroskimming-chart', 'figure'),
        Output('gpw-incremental-catalytic-chart', 'figure'),
        Output('gpw-incremental-hydroskimming-chart', 'figure'),
        Output('gpw-data-table', 'columns'),
        Output('gpw-data-table', 'data'),
        Output('gpw-data-table', 'tooltip_data'),
        Input('current-submenu', 'data'),
        Input('gpw-date-range-slider', 'value'),
        Input('gpw-region-filter', 'value'),
        Input('gpw-crude-filter', 'value'),
        Input('gpw-refining-complexity-filter', 'value'),
        Input('gpw-crude-legend', 'value')
    )
    def update_all_charts(submenu, date_slider_value, region, crude_filter, tech_type_filter, crude_legend):
        """Update all charts and table based on filters."""
        if submenu != 'gpw-margins':
            return (
                _empty_figure(""),
                _empty_figure(""),
                _empty_figure(""),
                _empty_figure(""),
                [],
                [],
                []
            )
        
        # Initialize table tooltips
        table_tooltips = []
        
        # Parse dates from slider (single value for start date, end date is fixed)
        if date_slider_value is not None:
            start_date = _index_to_date(date_slider_value)
        else:
            start_date = DEFAULT_START_DATE
        # End date is always fixed
        end_date = DEFAULT_END_DATE
        
        # Determine selected crudes (use filter if available, otherwise use legend)
        # Filter takes priority since it's the user's direct input
        # Check if filter is explicitly set (not None and not empty list if it was intentionally cleared)
        if crude_filter is not None:
            # Filter has a value (could be empty list if all unchecked)
            selected_crudes = crude_filter if isinstance(crude_filter, list) else [crude_filter]
        elif crude_legend:
            # Fall back to legend if filter is None
            selected_crudes = crude_legend if isinstance(crude_legend, list) else [crude_legend]
        else:
            # If both are empty/None, default to all crudes for initial load
            selected_crudes = CRUDES.copy()
        
        # Handle ALL option for crudes
        if selected_crudes and 'ALL' in selected_crudes:
            selected_crudes = CRUDES.copy()
        else:
            # Remove ALL from list if present
            selected_crudes = [c for c in selected_crudes if c != 'ALL'] if selected_crudes else []
            # Don't default to all crudes if empty - respect user's empty selection
            # Empty selection means no crudes selected (show empty charts)
        
        # Determine selected tech types from checkbox
        if tech_type_filter:
            selected_tech_types = tech_type_filter if isinstance(tech_type_filter, list) else [tech_type_filter]
        else:
            selected_tech_types = []
        
        # Handle ALL option for tech types
        if 'ALL' in selected_tech_types:
            selected_tech_types = TECH_TYPES.copy()
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
        if selected_tech_types and 'Catalytic Cracking' in selected_tech_types:
            gpw_catalytic = _build_gpw_chart(
                gpw_filtered,
                'Catalytic Cracking',
                'Catalytic Cracking',
                selected_crudes,
                region
            )
        else:
            gpw_catalytic = _empty_figure("FCC not selected")
        
        if selected_tech_types and 'Hydroskimming' in selected_tech_types:
            gpw_hydro = _build_gpw_chart(
                gpw_filtered,
                'Hydroskimming',
                'Hydroskimming',
                selected_crudes,
                region
            )
        else:
            gpw_hydro = _empty_figure("HSK not selected")
        
        if selected_tech_types and 'Catalytic Cracking' in selected_tech_types:
            margins_catalytic = _build_incremental_margins_chart(
                margins_filtered,
                'Catalytic Cracking',
                'Catalytic Cracking',
                selected_crudes,
                region
            )
        else:
            margins_catalytic = _empty_figure("FCC not selected")
        
        if selected_tech_types and 'Hydroskimming' in selected_tech_types:
            margins_hydro = _build_incremental_margins_chart(
                margins_filtered,
                'Hydroskimming',
                'Hydroskimming',
                selected_crudes,
                region
            )
        else:
            margins_hydro = _empty_figure("HSK not selected")
        
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
                table_columns, table_data, table_tooltips = _prepare_data_table(
                    table_filtered,
                    start_date,
                    end_date,
                    region,
                    selected_crudes,
                    selected_tech_types
                )
            else:
                table_columns, table_data, table_tooltips = [], [], []
        else:
            table_columns, table_data, table_tooltips = [], [], []
        
        return (
            gpw_catalytic,
            gpw_hydro,
            margins_catalytic,
            margins_hydro,
            table_columns,
            table_data,
            table_tooltips
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
        - Individual items work independently
        """
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update
        
        # Process all triggers - normalization should handle all value changes
        # The sync callback will handle legend->filter sync separately
        
        # Skip normalization on initial load
        if is_initial_load:
            return dash.no_update, False, value
        
        # Handle empty value - check if this is from unchecking ALL or initial state
        if not value:
            # If we had ALL before and now value is empty, user unchecked ALL - clear everything
            if had_all:
                return [], False, []
            # Otherwise, empty value is valid (user unchecked all items)
            return [], False, []
        
        if not isinstance(value, (list, tuple)):
            return dash.no_update, False, previous_value
        
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
        
        # Toggle the clicked crude in the selection
        current_values = current_values or []
        if clicked_crude in current_values:
            # Remove if already selected
            new_values = [v for v in current_values if v != clicked_crude]
        else:
            # Add if not selected
            new_values = current_values + [clicked_crude] if current_values else [clicked_crude]
        
        return new_values if new_values else []
    
    # Update legend item visual state based on selection
    @dash_app.callback(
        Output({'type': 'gpw-crude-legend-item', 'crude': dd.ALL}, 'style'),
        Input('gpw-crude-legend', 'value'),
        prevent_initial_call=False
    )
    def update_crude_legend_visual_state(selected_crudes):
        """Update visual state of legend items based on selection."""
        selected_crudes = selected_crudes or []
        selected_set = set(selected_crudes) if isinstance(selected_crudes, list) else set([selected_crudes])
        
        styles = []
        for crude in CRUDES:
            if crude in selected_set:
                # Selected state
                style = {
                    'display': 'flex',
                    'alignItems': 'center',
                    'padding': '6px 8px',
                    'marginBottom': '2px',
                    'borderRadius': '4px',
                    'cursor': 'pointer',
                    'transition': 'background-color 0.2s ease',
                    'userSelect': 'none',
                    'backgroundColor': '#e6f1ff',
                    'border': '1px solid #0075A8'
                }
            else:
                # Unselected state
                style = {
                    'display': 'flex',
                    'alignItems': 'center',
                    'padding': '6px 8px',
                    'marginBottom': '2px',
                    'borderRadius': '4px',
                    'cursor': 'pointer',
                    'transition': 'background-color 0.2s ease',
                    'userSelect': 'none',
                    'backgroundColor': '#ffffff',
                    'border': '1px solid transparent'
                }
            styles.append(style)
        
        return styles
    
    # Sync crude filter checkbox with crude legend checklist (one-way: legend -> filter)
    # This sync happens when legend changes
    @dash_app.callback(
        Output('gpw-crude-filter', 'value', allow_duplicate=True),
        Input('gpw-crude-legend', 'value'),
        State('gpw-crude-filter', 'value'),
        prevent_initial_call=True
    )
    def sync_crude_filter_from_legend(crude_legend_values, current_filter_value):
        """Sync crude filter checkbox when legend checklist changes.
        When legend changes, update filter to reflect the same selection.
        If all items are selected in legend, set filter to ALL + all items.
        Otherwise, pass through individual legend values."""
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update
        
        if not crude_legend_values:
            # Legend is empty - clear filter (if not already empty)
            if not current_filter_value or (isinstance(current_filter_value, list) and len(current_filter_value) == 0):
                return dash.no_update
            return []
        
        legend_list = crude_legend_values if isinstance(crude_legend_values, list) else [crude_legend_values]
        legend_set = set(legend_list)
        all_items_set = set(CRUDES)
        
        # If all items are selected in legend, set filter to ALL + all items
        if legend_set == all_items_set:
            expected_filter = ['ALL'] + CRUDES.copy()
            # Check if filter already matches
            if current_filter_value and isinstance(current_filter_value, list):
                current_set = set(current_filter_value)
                expected_set = set(expected_filter)
                if current_set == expected_set:
                    return dash.no_update
            return expected_filter
        
        # Otherwise, pass through the legend values directly to filter (no ALL)
        # Check if filter already matches
        if current_filter_value and isinstance(current_filter_value, list):
            current_set = set([c for c in current_filter_value if c != 'ALL'])
            if current_set == legend_set:
                return dash.no_update
        return legend_list
    
    # Sync crude legend from crude filter (two-way sync)
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
        prevent_initial_call=True
    )
    def normalize_tech_type_filter(value, is_initial_load, previous_value):
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
        all_items_set = set(TECH_TYPES)
        non_all_set = set(non_all_items)
        previous_non_all_set = set([v for v in previous_list if v != 'ALL'])
        
        # If neither previous nor current has ALL, and it's just individual item changes
        # This allows independent item selection without interference
        if not had_all and not has_all:
            # Clean items to ensure only valid tech types
            cleaned_items = [v for v in non_all_items if v in TECH_TYPES]
            
            # Only normalize if all items are now selected (auto-check ALL)
            if set(cleaned_items) == all_items_set:
                result = ['ALL'] + TECH_TYPES.copy()
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
            result = ['ALL'] + TECH_TYPES.copy()
            return result, result
        
        # Case 2: ALL is checked - detect if item was unclicked or if ALL was just checked
        if has_all:
            if non_all_set == all_items_set:
                # ALL + all items - keep as is
                result = ['ALL'] + TECH_TYPES.copy()
                return result, result
            else:
                # ALL is checked but not all items are present
                # This means user unclicked an item while ALL was checked
                # Remove ALL and keep only the selected items
                cleaned_items = [v for v in non_all_items if v in TECH_TYPES]
                return cleaned_items, cleaned_items
        
        # Case 3: ALL was unchecked (had ALL before, don't have ALL now)
        if had_all and not has_all:
            # Check if items decreased (user unclicked an item) or stayed same (ALL unclicked)
            if previous_non_all_set == all_items_set and len(non_all_set) < len(all_items_set):
                # User unclicked an item from ALL+all - keep remaining items
                cleaned_items = [v for v in non_all_items if v in TECH_TYPES]
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
