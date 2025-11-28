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


def _load_gpw_data() -> pd.DataFrame:
    """Load and normalize Gross Product Worth data."""
    df = _read_csv(GPW_CSV)
    if df.empty:
        return df
    
    # Rename columns first
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


def _load_incremental_margins_data() -> pd.DataFrame:
    """Load and normalize Incremental Margins data."""
    df = _read_csv(INCREMENTAL_MARGINS_CSV)
    if df.empty:
        return df
    
    # Rename columns
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


# Load data on module import
GPW_DF = _load_gpw_data()
INCREMENTAL_MARGINS_DF = _load_incremental_margins_data()
DATA_TABLE_DF = _load_data_table_data()

# Extract unique values for filters
REGIONS = sorted(GPW_DF['Region'].unique().tolist()) if not GPW_DF.empty else []
CRUDES = sorted(GPW_DF['Crude'].unique().tolist()) if not GPW_DF.empty else []
TECH_TYPES = sorted(GPW_DF['TechType'].unique().tolist()) if not GPW_DF.empty else []

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

# Date range - create sorted list of unique dates
if not GPW_DF.empty:
    unique_dates = sorted(GPW_DF['Date'].unique())
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

DEFAULT_REGION = REGIONS[0] if REGIONS else None
DEFAULT_START_DATE = DATE_MIN
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


def _build_gpw_chart(df: pd.DataFrame, tech_type: str, title: str, selected_crudes: list = None) -> go.Figure:
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
    
    # Color palette for different crudes
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    for idx, crude in enumerate(available_crudes):
        crude_df = tech_df[tech_df['Crude'] == crude].copy()
        crude_df = crude_df.sort_values('Date')
        
        if not crude_df.empty:
            # Use predefined color if available
            color = CRUDE_COLORS.get(crude, colors[idx % len(colors)])
            
            fig.add_trace(go.Scatter(
                x=crude_df['Date'],
                y=crude_df['Value'],
                mode='lines+markers',
                name=crude,
                line=dict(color=color, width=2),
                marker=dict(size=4),
                hovertemplate=f"<b>{crude}</b><br>" +
                              "Date: %{x|%b %Y}<br>" +
                              "Value: $%{y:.2f}/bbl<extra></extra>"
            ))
    
    fig.update_layout(
        xaxis=dict(
            title="Date",
            showgrid=True,
            gridcolor="#e0e0e0"
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
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#dee2e6",
            borderwidth=1
        )
    )
    return fig


def _build_incremental_margins_chart(df: pd.DataFrame, tech_type: str, title: str, selected_crudes: list = None) -> go.Figure:
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
    
    # Color palette for different crudes
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    for idx, crude in enumerate(available_crudes):
        crude_df = tech_df[tech_df['Crude'] == crude].copy()
        crude_df = crude_df.sort_values('Date')
        
        if not crude_df.empty:
            # Use predefined color if available
            color = CRUDE_COLORS.get(crude, colors[idx % len(colors)])
            
            fig.add_trace(go.Scatter(
                x=crude_df['Date'],
                y=crude_df['Value'],
                mode='lines+markers',
                name=crude,
                line=dict(color=color, width=2),
                marker=dict(size=4),
                hovertemplate=f"<b>{crude}</b><br>" +
                              "Date: %{x|%b %Y}<br>" +
                              "Value: $%{y:.2f}/bbl<extra></extra>"
            ))
    
    fig.update_layout(
        xaxis=dict(
            title="Date",
            showgrid=True,
            gridcolor="#e0e0e0"
        ),
        yaxis=dict(
            title="Incremental Margins ($/bbl)",
            showgrid=True,
            gridcolor="#e0e0e0"
        ),
        hovermode='closest',
        height=400,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=60, r=20, t=80, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
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
        tuple: (columns, data) where columns is list of hierarchical column definitions
               and data is list of records
    """
    if df.empty:
        return [], []
    
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
    
    # Create data records
    data = []
    for date_str in unique_dates:
        record = {'DateStr': date_str}
        
        # Get all values for this date
        date_data = filtered_df[filtered_df['DateStr'] == date_str]
        
        # Create a lookup dictionary: (DataType, TechType, Crude) -> Value
        value_lookup = {}
        for _, row in date_data.iterrows():
            key = (
                str(row.get('DataType', '')).strip(),
                str(row.get('TechType', '')).strip(),
                str(row.get('Crude', '')).strip()
            )
            val = row.get('Value')
            if pd.notna(val):
                value_lookup[key] = float(val)
            else:
                value_lookup[key] = None
        
        # Populate record only with columns that exist (filtered by selection)
        for data_type in DATA_TYPES:
            for tech_type in TECH_TYPES:
                for crude in CRUDE_ORDER:
                    col_id = f"{data_type}_{tech_type}_{crude}".replace(' ', '_').replace('/', '_')
                    key = (data_type, tech_type, crude)
                    
                    if key in value_lookup:
                        record[col_id] = value_lookup[key]
                    else:
                        record[col_id] = None
        
        data.append(record)
    
    return columns, data


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
                }
                #gpw-date-range-min-input:hover,
                #gpw-date-range-max-input:hover {
                    border: 1px solid #ccc !important;
                    background: #ffffff !important;
                    padding: 1px 3px !important;
                }
                #gpw-date-range-min-input:focus,
                #gpw-date-range-max-input:focus {
                    border: 1px solid #999 !important;
                    background: #ffffff !important;
                    padding: 1px 3px !important;
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
                                style={'width': '15%', 'display': 'inline-block', 'float': 'right', 'border': '0px solid #dee2e6', 'color': '#1b365d', 'fontSize': '11px', 'fontFamily': 'Arial', 'lineHeight': '12px', 'fontWeight': 'bold', 'backgroundColor': 'unset'}
                            ),
                        ], style={'width': '100%', 'marginBottom': '10px', 'position': 'relative'}),
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
                            'borderBottom': '2px solid #fe5000'
                        }
                    ),
                    
                    html.Div([
                        html.Div([
                            html.H4(
                                "FCC",
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
                                "HSK",
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
                ], className='col-md-9', style={'padding': '15px'}),
                
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
                            'fontSize': '14px',
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
                ], className='col-md-3', style={
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
                            'borderBottom': '2px solid #fe5000'
                        }
                    ),
                    
                    html.Div([
                        html.Div([
                            html.H4(
                                "FCC",
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
                                "HSK",
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
                ], className='col-md-9', style={'padding': '15px'}),
                
                # Empty column to maintain layout (filters already shown above)
                html.Div([
                ], className='col-md-3', style={'padding': '15px'}),
            ], className='row')
        ], style={'padding': '20px', 'marginBottom': '30px'}),
        
        # Data Table Section
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
            
            html.Div([
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
                        'padding': '8px'
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
                    sort_action='native'
                )
            ])
        ], style={'padding': '20px'})
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
        """Sync date range inputs with slider."""
        ctx = callback_context
        
        if not ctx.triggered:
            return [DEFAULT_START_INDEX, DEFAULT_END_INDEX], _format_date_for_display(DEFAULT_START_DATE), _format_date_for_display(DEFAULT_END_DATE)
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id in ['gpw-date-range-min-input', 'gpw-date-range-max-input']:
            # Input changed, update slider
            if min_input and max_input:
                # Parse date strings like "Aug 07" back to dates
                try:
                    min_date = pd.to_datetime(min_input, format='%b %y', errors='coerce')
                    max_date = pd.to_datetime(max_input, format='%b %y', errors='coerce')
                    if pd.notna(min_date) and pd.notna(max_date):
                        min_idx = _date_to_index(min_date)
                        max_idx = _date_to_index(max_date)
                        # Ensure min <= max
                        if min_idx > max_idx:
                            min_idx, max_idx = max_idx, min_idx
                        return [min_idx, max_idx], min_input, max_input
                except Exception:
                    pass
        elif trigger_id == 'gpw-date-range-slider':
            # Slider changed, update inputs
            if slider_value and len(slider_value) == 2:
                min_date = _index_to_date(slider_value[0])
                max_date = _index_to_date(slider_value[1])
                return slider_value, _format_date_for_display(min_date), _format_date_for_display(max_date)
        
        return [DEFAULT_START_INDEX, DEFAULT_END_INDEX], _format_date_for_display(DEFAULT_START_DATE), _format_date_for_display(DEFAULT_END_DATE)
    
    @dash_app.callback(
        Output('gpw-catalytic-cracking-chart', 'figure'),
        Output('gpw-hydroskimming-chart', 'figure'),
        Output('gpw-incremental-catalytic-chart', 'figure'),
        Output('gpw-incremental-hydroskimming-chart', 'figure'),
        Output('gpw-data-table', 'columns'),
        Output('gpw-data-table', 'data'),
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
                []
            )
        
        # Parse dates from slider
        if date_slider_value and len(date_slider_value) == 2:
            start_date = _index_to_date(date_slider_value[0])
            end_date = _index_to_date(date_slider_value[1])
        else:
            start_date = DEFAULT_START_DATE
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
        
        # Filter GPW data
        gpw_filtered = GPW_DF[
            (GPW_DF['Date'] >= start_date) &
            (GPW_DF['Date'] <= end_date) &
            (GPW_DF['Crude'].isin(selected_crudes))
        ].copy()
        
        if selected_tech_types:
            gpw_filtered = gpw_filtered[gpw_filtered['TechType'].isin(selected_tech_types)]
        
        if region:
            gpw_filtered = gpw_filtered[gpw_filtered['Region'] == region]
        
        # Filter Incremental Margins data
        margins_filtered = INCREMENTAL_MARGINS_DF[
            (INCREMENTAL_MARGINS_DF['Date'] >= start_date) &
            (INCREMENTAL_MARGINS_DF['Date'] <= end_date) &
            (INCREMENTAL_MARGINS_DF['Crude'].isin(selected_crudes))
        ].copy()
        
        if selected_tech_types:
            margins_filtered = margins_filtered[margins_filtered['TechType'].isin(selected_tech_types)]
        
        if region:
            margins_filtered = margins_filtered[margins_filtered['Region'] == region]
        
        # Build charts only if tech type is selected
        if selected_tech_types and 'Catalytic Cracking' in selected_tech_types:
            gpw_catalytic = _build_gpw_chart(
                gpw_filtered,
                'Catalytic Cracking',
                'Catalytic Cracking',
                selected_crudes
            )
        else:
            gpw_catalytic = _empty_figure("FCC not selected")
        
        if selected_tech_types and 'Hydroskimming' in selected_tech_types:
            gpw_hydro = _build_gpw_chart(
                gpw_filtered,
                'Hydroskimming',
                'Hydroskimming',
                selected_crudes
            )
        else:
            gpw_hydro = _empty_figure("HSK not selected")
        
        if selected_tech_types and 'Catalytic Cracking' in selected_tech_types:
            margins_catalytic = _build_incremental_margins_chart(
                margins_filtered,
                'Catalytic Cracking',
                'Catalytic Cracking',
                selected_crudes
            )
        else:
            margins_catalytic = _empty_figure("FCC not selected")
        
        if selected_tech_types and 'Hydroskimming' in selected_tech_types:
            margins_hydro = _build_incremental_margins_chart(
                margins_filtered,
                'Hydroskimming',
                'Hydroskimming',
                selected_crudes
            )
        else:
            margins_hydro = _empty_figure("HSK not selected")
        
        # Prepare data table with multi-level headers
        # Use Data Table CSV
        if not DATA_TABLE_DF.empty:
            # Filter Data Table by date range
            table_filtered = DATA_TABLE_DF[
                (DATA_TABLE_DF['Date'] >= start_date) &
                (DATA_TABLE_DF['Date'] <= end_date)
            ].copy()
            
            # Filter by region if Region column exists
            if region and 'Region' in table_filtered.columns:
                table_filtered = table_filtered[table_filtered['Region'] == region]
            
            # Filter by crude
            if 'Crude' in table_filtered.columns:
                table_filtered = table_filtered[table_filtered['Crude'].isin(selected_crudes)]
            
            # Filter by tech type
            if 'TechType' in table_filtered.columns:
                table_filtered = table_filtered[table_filtered['TechType'].isin(selected_tech_types)]
            
            table_columns, table_data = _prepare_data_table(
                table_filtered,
                start_date,
                end_date,
                region,
                selected_crudes,
                selected_tech_types
            )
        else:
            # Fallback: combine GPW and Margins data
            combined_df = pd.DataFrame()
            if not gpw_filtered.empty:
                gpw_copy = gpw_filtered.copy()
                gpw_copy['DataType'] = 'GPW'
                combined_df = pd.concat([combined_df, gpw_copy], ignore_index=True)
            
            if not margins_filtered.empty:
                margins_copy = margins_filtered.copy()
                margins_copy['DataType'] = 'Refining Margin'
                combined_df = pd.concat([combined_df, margins_copy], ignore_index=True)
            
            if not combined_df.empty:
                table_columns, table_data = _prepare_data_table(
                    combined_df,
                    start_date,
                    end_date,
                    region,
                    selected_crudes,
                    selected_tech_types
                )
            else:
                table_columns, table_data = [], []
        
        return (
            gpw_catalytic,
            gpw_hydro,
            margins_catalytic,
            margins_hydro,
            table_columns,
            table_data
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
        
        # Only process if triggered by the filter itself (not by sync from legend)
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        if trigger_id != 'gpw-crude-filter':
            return dash.no_update, dash.no_update, dash.no_update
        
        # Skip normalization on initial load
        if is_initial_load:
            return dash.no_update, False, value
        
        if not value:
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
        
        # Case 2: ALL is checked - detect if item was unclicked or if ALL was just checked
        if has_all:
            if non_all_set == all_items_set:
                # ALL + all items - keep as is
                result = ['ALL'] + CRUDES.copy()
                return result, False, result
            else:
                # ALL is checked but not all items are present
                # This means user unclicked an item while ALL was checked
                # Remove ALL and keep only the selected items
                cleaned_items = [v for v in non_all_items if v in CRUDES]
                return cleaned_items, False, cleaned_items
        
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
    # This sync only happens when legend changes, not when filter changes
    @dash_app.callback(
        Output('gpw-crude-filter', 'value', allow_duplicate=True),
        Input('gpw-crude-legend', 'value'),
        prevent_initial_call=True
    )
    def sync_crude_filter_from_legend(crude_legend_values):
        """Sync crude filter checkbox when legend checklist changes.
        Pass legend values directly to filter - no ALL conversion.
        Only runs when legend changes, allowing filter to work independently."""
        if not crude_legend_values:
            return []
        # Pass through the legend values directly to filter (no conversion to ALL)
        return crude_legend_values if isinstance(crude_legend_values, list) else [crude_legend_values]
    
    # Sync crude legend from crude filter (only when ALL is set via normalization)
    @dash_app.callback(
        Output('gpw-crude-legend', 'value', allow_duplicate=True),
        Input('gpw-crude-filter', 'value'),
        prevent_initial_call=True
    )
    def sync_crude_legend_from_filter(crude_filter_values):
        """Sync crude legend when filter changes, but only for ALL option.
        Don't interfere with individual legend item selection or direct filter clicks."""
        if not crude_filter_values:
            return dash.no_update
        
        # Only sync if ALL is in the filter and all items are selected
        # This indicates normalization happened
        if isinstance(crude_filter_values, list) and 'ALL' in crude_filter_values:
            filter_set = set(crude_filter_values)
            all_set_with_all = set(['ALL'] + CRUDES)
            if filter_set == all_set_with_all:
                # Normalization set ALL + all items - sync legend
                return CRUDES.copy()
        
        # Don't sync for individual selections
        return dash.no_update
    
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
