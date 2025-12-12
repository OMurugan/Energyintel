"""
Projects by Company View
Upstream projects grouped by company - matches Tableau dashboard design
"""
from dash import dcc, html, Input, Output, State, callback, ALL, callback_context, dash_table
import dash
import json
import plotly.graph_objects as go
import pandas as pd
import os
from core.data_helpers import execute_query

# Define data path for chart/map CSVs (chart & map remain CSV-based)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'projects_company')
CSV_FILE = os.path.join(DATA_DIR, 'Projects by Company_Chart_data.csv')
MAP_CSV_FILE = os.path.join(DATA_DIR, 'Map_by Company_data.csv')


def load_data():
    """Load chart data from CSV file (used for bar chart)."""
    try:
        df = pd.read_csv(CSV_FILE, encoding="utf-8", sep=",")
        df.columns = df.columns.str.strip()
        df['value_company'] = pd.to_numeric(df['value_company'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()


def load_map_data():
    """Load map data from CSV file."""
    try:
        df = pd.read_csv(MAP_CSV_FILE, encoding="utf-8", sep=",")
        df.columns = df.columns.str.strip()
        df['value_company'] = pd.to_numeric(df['value_company'], errors='coerce')
        return df
    except Exception as e:
        print(f"Error loading map data: {e}")
        return pd.DataFrame()

# Quarter columns returned by the SQL query (used for chart, map, and table)
QUARTER_COLUMNS = [
    "2024_Q1", "2024_Q2", "2024_Q3", "2024_Q4",
    "2025_Q1", "2025_Q2", "2025_Q3", "2025_Q4",
    "2026_Q1", "2026_Q2", "2026_Q3", "2026_Q4",
    "2027_Q1", "2027_Q2", "2027_Q3", "2027_Q4",
    "2028_Q1", "2028_Q2", "2028_Q3", "2028_Q4",
    "2029_Q1", "2029_Q2", "2029_Q3", "2029_Q4"
]

YEARS_FOR_CHART = list(range(2025, 2030))


def load_projects_data():
    """Load Projects by Company data directly from the database."""
    query = """
        SELECT
            a.project_name AS "Project Name",
            a.likely_goahead,
            c.country_long_name AS Country,
            c.region AS Region,
            CASE
                WHEN c.opec_grp = 'opec' OR c.opec_grp = 'opec_plus' THEN 'Opec-Plus'
                ELSE 'Non-Opec-Plus'
            END AS Opec_group,
            a.field_type,
            a.field,
            a.play_type,
            a.hydrocarbon AS Hydrocarbon,
            cr.crude_name AS "Associated Crude",
            a.depth AS Depth,
            op.company_name AS Operator,
            p1.company_name AS Partner1,
            p2.company_name AS Partner2,
            p3.company_name AS Partner3,
            p4.company_name AS Partner4,
            p5.company_name AS Partner5,
            yr.year AS "First Oil Year",
            a.sanctioned AS Sanctioned,
            a.external_comments AS Comments,
            a.project_status AS "Project Status",
            a.reserves_gas_mmboe AS "Gas Reserves (mmboe)",
            a.reserves_liquids_mmbbl AS "Liquids Reserves (mmbbl)",
            (
                COALESCE(
                    NULLIF(SPLIT_PART(a.reserves_gas_mmboe, '-', 1), '')::numeric,
                    0
                )
                +
                COALESCE(
                    NULLIF(SPLIT_PART(a.reserves_liquids_mmbbl, '-', 1), '')::numeric,
                    0
                )
            ) AS "Total Reserves (mmboe)",
            a.api_cat AS API,
            a.sulfur_cat AS Sulfur,
            a.operator_pc AS "Operator Share %",
            a.partner1_pc AS "Partner1 Share %",
            a.partner2_pc AS "Partner2 Share %",
            a.partner3_pc AS "Partner3 Share %",
            a.partner4_pc AS "Partner4 Share %",
            a.partner5_pc AS "Partner5 Share %",
            est."2024_Q1",
            est."2024_Q2",
            est."2024_Q3",
            est."2024_Q4",
            est."2025_Q1",
            est."2025_Q2",
            est."2025_Q3",
            est."2025_Q4",
            est."2026_Q1",
            est."2026_Q2",
            est."2026_Q3",
            est."2026_Q4",
            est."2027_Q1",
            est."2027_Q2",
            est."2027_Q3",
            est."2027_Q4",
            est."2028_Q1",
            est."2028_Q2",
            est."2028_Q3",
            est."2028_Q4",
            est."2029_Q1",
            est."2029_Q2",
            est."2029_Q3",
            est."2029_Q4"
        FROM fact_upstream_project_tracker a
        LEFT JOIN fact_upstream_tracker_prod_estimates est 
            ON a.project_id = est.project_id
        LEFT JOIN dim_country c 
            ON a.country_id = c.dim_country_id
        LEFT JOIN dim_company op 
            ON a.operator_id = op.company_id
        LEFT JOIN dim_company p1 
            ON a.partner1_id = p1.company_id
        LEFT JOIN dim_company p2 
            ON a.partner2_id = p2.company_id
        LEFT JOIN dim_company p3 
            ON a.partner3_id = p3.company_id
        LEFT JOIN dim_company p4 
            ON a.partner4_id = p4.company_id
        LEFT JOIN dim_company p5 
            ON a.partner5_id = p5.company_id
        LEFT JOIN (
            SELECT 
                project_id,
                MIN(EXTRACT(YEAR FROM period)) AS year
            FROM fact_upstream_tracker_prod_estimates_incremental
            WHERE value IS NOT NULL 
            GROUP BY project_id
        ) yr ON yr.project_id = a.project_id
        LEFT JOIN dim_crude cr 
            ON cr.dim_crude_id = a.crude_id
        WHERE a.include = TRUE
        ORDER BY a.project_name;
    """

    try:
        results = execute_query(query)
        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results)
        column_mapping = {
            'Project Name': 'Project Name',
            'project_name': 'Project Name',
            'likely_goahead': 'Likely Go-ahead',
            'Likely Go-ahead': 'Likely Go-ahead',
            'Country': 'Country',
            'country': 'Country',
            'country_long_name': 'Country',
            'Region': 'Region',
            'region': 'Region',
            'Opec_group': 'Group',
            'opec_group': 'Group',
            'field_type': 'Field Type',
            'Field Type': 'Field Type',
            'field': 'Field/Block',
            'Field': 'Field/Block',
            'play_type': 'Play Type',
            'Play Type': 'Play Type',
            'Hydrocarbon': 'Hydrocarbon',
            'hydrocarbon': 'Hydrocarbon',
            'Associated Crude': 'Associated Crude',
            'Depth': 'Depth',
            'depth': 'Depth',
            'Operator': 'Operator',
            'operator': 'Operator',
            'Partner1': 'Partner1',
            'partner1': 'Partner1',
            'Partner2': 'Partner2',
            'partner2': 'Partner2',
            'Partner3': 'Partner3',
            'partner3': 'Partner3',
            'Partner4': 'Partner4',
            'partner4': 'Partner4',
            'Partner5': 'Partner5',
            'partner5': 'Partner5',
            'First Oil Year': 'First Oil Year',
            'year': 'First Oil Year',
            'Sanctioned': 'Sanctioned',
            'sanctioned': 'Sanctioned',
            'Comments': 'Comments',
            'comments': 'Comments',
            'Project Status': 'Project Status',
            'project_status': 'Project Status',
            'Gas Reserves (mmboe)': 'Gas Reserves (mmboe)',
            'reserves_gas_mmboe': 'Gas Reserves (mmboe)',
            'Liquids Reserves (mmbbl)': 'Liquids Reserves (mmbbl)',
            'reserves_liquids_mmbbl': 'Liquids Reserves (mmbbl)',
            'Total Reserves (mmboe)': 'Total Reserves (mmboe)',
            'api_cat': 'API',
            'API': 'API',
            'sulfur_cat': 'Sulfur',
            'sulfur': 'Sulfur',
            'Sulfur': 'Sulfur',
            'operator_pc': 'Operator Share %',
            'partner1_pc': 'Partner1 Share %',
            'partner2_pc': 'Partner2 Share %',
            'partner3_pc': 'Partner3 Share %',
            'partner4_pc': 'Partner4 Share %',
            'partner5_pc': 'Partner5 Share %'
        }
        df = df.rename(columns=column_mapping)

        for col in QUARTER_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        non_quarter_cols = [c for c in df.columns if c not in QUARTER_COLUMNS]
        df[non_quarter_cols] = df[non_quarter_cols].fillna('')
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()


def build_quarterly_capacity(df):
    """Transform wide quarter columns into long format for the stacked bar chart."""
    if df.empty:
        return pd.DataFrame()

    records = []
    for _, row in df.iterrows():
        country = row.get('Country')
        if pd.isna(country) or not str(country).strip():
            continue
        for col in QUARTER_COLUMNS:
            if col not in df.columns:
                continue
            value = pd.to_numeric(row.get(col), errors='coerce')
            if pd.isna(value):
                value = 0
            year_part, quarter_part = col.split('_')
            try:
                year_int = int(year_part)
            except (TypeError, ValueError):
                continue
            if year_int not in YEARS_FOR_CHART:
                continue
            records.append({
                'Country': country,
                'Year of Period': year_int,
                'Quarter of Period': quarter_part.replace('Q', 'Q'),
                'value_company': value
            })

    return pd.DataFrame(records)


def build_map_data(quarter_df):
    """Aggregate quarterly data to yearly totals for the map."""
    if quarter_df.empty:
        return pd.DataFrame()
    try:
        return (
            quarter_df.groupby(['Country', 'Year of Period'])['value_company']
            .sum()
            .reset_index()
        )
    except Exception as e:
        print(f"Error building map data: {e}")
        return pd.DataFrame()


# Load data once at module level
PROJECTS_RAW_DF = load_projects_data()  # SQL – table only
DATA_DF = load_data()  # CSV – chart
MAP_DF = load_map_data()  # CSV – map

# Get unique values for filters
def get_unique_years():
    """Get unique years from data"""
    if DATA_DF.empty:
        return []
    return sorted(DATA_DF['Year of Period'].unique().tolist())

def get_unique_countries():
    """Get unique countries from data"""
    if DATA_DF.empty:
        return []
    countries = sorted([c for c in DATA_DF['Country'].unique().tolist() if pd.notna(c) and str(c).strip()])
    return countries

def get_unique_quarters():
    """Get unique quarters"""
    return ['Q1', 'Q2', 'Q3', 'Q4']

# Color palette for countries (matching Tableau dashboard exactly)
COUNTRY_COLORS = {
   'Algeria': '#a0cbe8',  # light blue
    'Angola': '#4e79a7',  # orange (matching Tableau dashboard)
    'Argentina': '#f28e2b',  # orange
    'Australia': '#ffbe7d',  # light orange/peach
    'Azerbaijan': '#8cd17d',  # light green
    'Brazil': '#d7b5a6', #light brown/tan
    'Brunei': '#f1ce63',  # yellow
    'Cameroon': '#e15759',  # red
    'Canada': '#86bcb6',  # teal/light blue-green
    'China': '#79706e',  # dark grey
    'Cote d\'Ivoire': '#d37295',  # pink
    'Denmark': '#d37295',  # dark pink
    'Egypt': '#b07aa1',  # muted purple (plum)
    'Gabon': '#d4a6c8',  # very light pink/peach
    'Ghana': '#9d7660',  # dark reddish-brown (saddle brown)
    'Guyana': '#76b7b2',  # distinct teal/turquoise (matching Tableau)
    'India': '#76b7b2',  # light sky blue
    'Indonesia': '#4e79a7',  # dark, rich blue
    'Iran': '#a0cbe8',  # very pale, almost white-blue (alice blue)
    'Iraq': '#9c755f',  # medium brown (peru)
    'Kazakhstan': '#59a14f',  # dark turquoise/teal (matching Tableau - shown as green in bars)
    'Kuwait': '#b6992d',  # mustard yellow/gold
    'Libya': '#76b7b2',  # light, slightly desaturated teal/green (medium turquoise)
    'Malaysia': '#86bcb6',  # dark forest green
    'Mexico': '#76b7b2' ,  # light, slightly desaturated teal/green (medium turquoise)
    'Namibia': '#79706e',  # light, slightly desaturated teal/green (medium turquoise)
    'Neutral Zone': '#79706e',  # light, slightly desaturated teal/green (medium turquoise)
    'Niger': '#bab0ac',  # light, slightly desaturated teal/green (medium turquoise)
    'Nigeria': '#59a14f',  # light, slightly desaturated teal/green (medium turquoise)
    'Norway': '#b07aa1',  # light, slightly desaturated teal/green (medium turquoise)
    'Oman': '#9c755f',  # light, slightly desaturated teal/green (medium turquoise)
    'Qatar': '#4e79a7',  # medium purple
    'Russia': '#4e79a7',  # light, slightly desaturated teal/green (medium turquoise)
    'Saudi Arabia': '#8cd17d',  # light, slightly desaturated teal/green (medium turquoise)
    'Senegal': '#f28e2b',  # light, slightly desaturated teal/green (medium turquoise)
    'Suriname': '#bab0ac',  # light, slightly desaturated teal/green (medium turquoise)
    'Thailand': '#f1ce63',  # light, slightly desaturated teal/green (medium turquoise)
    'Trinidad and Tobago': '#f1ce63',  # light, slightly desaturated teal/green (medium turquoise)
    'Turkey': '#8cd17d',  # light, slightly desaturated teal/green (medium turquoise)
    'Turkmenistan': '#8cd17d',  # light, slightly desaturated teal/green (medium turquoise)
    'Uganda': '#e15759',  # light, slightly desaturated teal/green (medium turquoise)
    'United Arab Emirates': '#edc948',  # light, slightly desaturated teal/green (medium turquoise)
    'United Kingdom': '#b07aa1',  # light, slightly desaturated teal/green (medium turquoise)
    'United States': '#ff9da7',  # dodger blue
    'Vietnam': '#499894',  # light sea green
}

def get_country_color(country):
    """Get color for a country, assign default if not in palette"""
    if country in COUNTRY_COLORS:
        return COUNTRY_COLORS[country]
    # Generate a color based on hash for countries not in palette
    import hashlib
    hash_obj = hashlib.md5(str(country).encode())
    hash_int = int(hash_obj.hexdigest(), 16)
    # Generate a color from hash
    r = (hash_int & 0xFF0000) >> 16
    g = (hash_int & 0xFF00) >> 8
    b = hash_int & 0xFF
    return f'rgb({r}, {g}, {b})'

def apply_opacity_to_color(color, opacity):
    """Return RGBA color string with the requested opacity; fall back to the original color on error."""
    try:
        if isinstance(color, str) and color.startswith('#') and len(color) == 7:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            return f'rgba({r},{g},{b},{opacity})'
        if isinstance(color, str) and color.startswith('rgb(') and color.endswith(')'):
            parts = color[4:-1].split(',')
            if len(parts) == 3:
                r, g, b = [int(p.strip()) for p in parts]
                return f'rgba({r},{g},{b},{opacity})'
    except Exception:
        pass
    return color

def create_stacked_bar_chart(df, selected_company="Exxon Mobil", selected_countries=None, highlight_year=None, highlight_quarter=None):
    """Create stacked bar chart showing quarterly capacity by country"""
    if selected_countries is None:
        selected_countries = []
    
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            height=500,
            plot_bgcolor='white',
            paper_bgcolor='white',
            title={
                'text': f"Oil Projects Capacity Start Up by {selected_company} ('000 b/d)*",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16, 'family': 'Arial, sans-serif', 'color': '#FF8C42'}
            }
        )
        return fig
    
    # Always use DATA_DF to ensure we have ALL countries from CSV (including those with zeros like Algeria)
    # This ensures all countries are available for the chart
    original_df = DATA_DF.copy() if not DATA_DF.empty else df.copy()
    
    # Create period labels on the full dataset first
    if 'Period' not in original_df.columns:
        original_df['Period'] = original_df['Year of Period'].astype(str) + ' ' + original_df['Quarter of Period']
    
    # Create a sort key for proper chronological ordering
    quarter_order = {'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4}
    if 'SortKey' not in original_df.columns:
        original_df['SortKey'] = original_df['Year of Period'] * 10 + original_df['Quarter of Period'].map(quarter_order)
        original_df = original_df.sort_values(['SortKey'])
    
    if selected_countries:
        # If countries are selected, show ONLY those selected countries (even if they have zero values)
        # This matches Tableau behavior - clicking a country filters to show only that country
        all_countries_in_data = [c for c in selected_countries if pd.notna(c) and str(c).strip()]
    else:
        # If no countries selected, show ALL countries from the CSV data (including those with zeros)
        # This ensures all countries from the CSV are displayed in the chart
        # Countries with zero values will still appear in tooltips and chart structure
        all_countries_in_data = [c for c in original_df['Country'].unique().tolist() if pd.notna(c) and str(c).strip()]
    
    # Filter by selected countries if any are selected (after getting country list)
    # Always use original_df (full DATA_DF) to ensure we have data for all countries even if they have zeros
    if selected_countries:
        # Filter to selected countries only
        df = original_df[original_df['Country'].isin(selected_countries)].copy()
    else:
        # When showing all countries, use the full original data
        df = original_df.copy()
    
    # Generate all possible periods from min year to max year (to ensure all quarters are shown)
    # Use the full data range (2025-2029) to show all quarters consistently
    all_periods = []
    for year in range(2025, 2030):
        for quarter in ['Q1', 'Q2', 'Q3', 'Q4']:
            all_periods.append(f"{year} {quarter}")
    periods = all_periods
    
    # Define stacking order to match Tableau visualization
    # In stacked bar charts, the order matters - countries are stacked from bottom to top
    # Based on the image, the typical order is: Kazakhstan (bottom), then others with data, then zeros on top
    # For proper stacking, we want countries with data first, then countries with zeros
    stacking_order = [
        'Kazakhstan', 'Guyana', 'Brazil', 'Azerbaijan', 'Indonesia', 'Angola', 
        'Qatar', 'Nigeria', 'Canada', 'China', 'Malaysia', 'Iran', 'Iraq',
        'Mexico', 'Libya', 'Niger', 'Kuwait', 'Algeria', 'Argentina', 'Australia',
        'Brunei', 'Cameroon', 'Cote d\'Ivoire', 'Denmark', 'Egypt', 'Gabon', 
        'Ghana', 'India', 'United States', 'United Kingdom', 'United Arab Emirates',
        'Uganda', 'Turkmenistan', 'Turkey', 'Trinidad and Tobago', 'Thailand',
        'Suriname', 'Senegal', 'Saudi Arabia', 'Russia', 'Oman', 'Norway',
        'Neutral Zone', 'Namibia', 'Vietnam', 'Ecuador'
    ]
    
    # Separate countries with data from countries with only zeros
    countries_with_data = []
    countries_with_zeros_only = []
    
    for country in all_countries_in_data:
        country_data = df[df['Country'] == country]
        if not country_data.empty and country_data['value_company'].sum() > 0:
            countries_with_data.append(country)
        else:
            countries_with_zeros_only.append(country)
    
    # Order countries with data according to stacking order
    ordered_with_data = [c for c in stacking_order if c in countries_with_data]
    remaining_with_data = [c for c in sorted(countries_with_data) if c not in stacking_order]
    
    # Order countries with zeros according to stacking order
    ordered_with_zeros = [c for c in stacking_order if c in countries_with_zeros_only]
    remaining_with_zeros = [c for c in sorted(countries_with_zeros_only) if c not in stacking_order]
    
    # Stack: countries with data first (bottom), then countries with zeros (top, but invisible)
    countries = ordered_with_data + remaining_with_data + ordered_with_zeros + remaining_with_zeros
    
    # Format periods for hover (Q1 2025 instead of 2025 Q1) - create once before loop
    hover_periods = [f"{p.split(' ')[1]} {p.split(' ')[0]}" for p in periods]
    
    # Create stacked bar chart
    fig = go.Figure()
    
    # Add a trace for each country
    for country in countries:
        # Always use the filtered df (which has Period column already created)
        # If country is selected, df is filtered to that country
        # If no countries selected, df has all countries
        country_data = df[df['Country'] == country]
        base_color = get_country_color(country)
        highlight_year_int = None
        highlight_quarter_label = None
        try:
            highlight_year_int = int(highlight_year) if highlight_year is not None else None
        except (ValueError, TypeError):
            highlight_year_int = None
        try:
            highlight_quarter_label = str(highlight_quarter) if highlight_quarter is not None else None
        except Exception:
            highlight_quarter_label = None
        
        values = []
        marker_colors = []
        for period in periods:
            period_data = country_data[country_data['Period'] == period]
            period_year = None
            try:
                period_year = int(str(period).split(' ')[0])
            except (ValueError, TypeError, AttributeError):
                period_year = None
            if not period_data.empty:
                values.append(period_data['value_company'].sum())
            else:
                # If no data for this period, set to 0
                values.append(0)
            
            # Dual highlight: keep full color if matches year and/or quarter selection; otherwise fade.
            if highlight_year_int is not None or highlight_quarter_label is not None:
                is_year_match = (highlight_year_int is not None and period_year == highlight_year_int)
                is_quarter_match = (
                    highlight_quarter_label is not None and str(period).endswith(f" {highlight_quarter_label}")
                )
                if (highlight_year_int is None and is_quarter_match) or \
                   (highlight_quarter_label is None and is_year_match) or \
                   (is_year_match and is_quarter_match):
                    marker_colors.append(base_color)
                else:
                    marker_colors.append(apply_opacity_to_color(base_color, 0.18))
            else:
                marker_colors.append(base_color)
        
        # Always create a trace for all countries, even if all values are 0
        # This ensures the chart structure is maintained and tooltips work for countries with zeros
        # In stacked bar charts, traces with zeros are still part of the stack and show in tooltips
        # Countries with zeros will be hoverable even though they don't show visually
        fig.add_trace(go.Bar(
            name=country,
            x=periods,
            y=values,
            marker_color=marker_colors if highlight_year_int is not None else base_color,
            customdata=hover_periods,
            meta=country,
            hovertemplate='Country: %{meta}<br>Period: %{customdata}<br>Production Additions (\'000 b/d): %{y:,.1f}<extra></extra>',
            showlegend=False,  # Hide legend - using sidebar legend instead
            marker_line_width=0,  # No border on bars
            # Make zero-value bars still hoverable
            opacity=1.0 if any(v > 0 for v in values) else 0.01
        ))
    
    # Y-axis should be exactly 0-70 to match images exactly; extend slightly to host invisible click-capture markers.
    y_max = 70
    
    # Update layout to match exact image design
    fig.update_layout(
        barmode='stack',
        bargap=0.12,  # slight gap to mirror reference spacing
        height=500,
        plot_bgcolor='white',
        paper_bgcolor='white',
        title={
            'text': f"Oil Projects Capacity Start Up by {selected_company} ('000 b/d)*",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'family': 'Arial, sans-serif', 'color': '#FF8C42'},
            'y': 0.98
        },
        xaxis=dict(
            title='',
            tickangle=0,
            showgrid=True,
            gridcolor='#e0e0e0',
            tickfont=dict(size=11, color='#2c3e50'),
            tickmode='array',
            tickvals=periods,
            ticktext=[p.split(' ')[1] for p in periods],  # Show only quarters (Q1, Q2, etc.)
            categoryorder='array',
            categoryarray=periods
        ),
        yaxis=dict(
            title="'000 b/d",
            showgrid=True,
            gridcolor='#e0e0e0',
            tickfont=dict(size=11, color='#2c3e50'),
            range=[-5, y_max + 5],
            dtick=10,
            titlefont=dict(size=12, color='#2c3e50')
        ),
        showlegend=False,  # Hide legend in chart - using sidebar legend instead
        margin=dict(l=60, r=60, t=60, b=100),  # Reduced right margin since legend is in sidebar
        hovermode='closest',
        hoverlabel=dict(
            bgcolor='white',
            bordercolor='#999999',
            font=dict(
                size=13,
                family='Arial, sans-serif',
                color='#000000'
            )
        )
    )
    
    # Add year annotations above quarter groups for full 2025–2029 span
    for year in range(2025, 2030):
        year_positions = [idx for idx, p in enumerate(periods) if p.startswith(f"{year} ")]
        if not year_positions:
            continue
        x_pos = sum(year_positions) / len(year_positions)  # center label across four quarters
        fig.add_annotation(
            x=x_pos,
            y=1.05,
            xref='x',
            yref='paper',
            text=str(year),
            showarrow=False,
            font=dict(size=12, color='#2c3e50'),
            xanchor='center'
        )
    
    # Add footnote to match reference design
    fig.add_annotation(
        text="*Only the company's stake in the project is included.",
        xref="paper",
        yref="paper",
        x=0.0,
        y=-0.08,
        showarrow=False,
        font=dict(size=11, color='#2c3e50'),
        xanchor='left',
        yanchor='top'
    )
    
    # Invisible traces to capture quarter and year clicks (so users can click labels/areas, not just bars).
    # Quarter capture: points aligned with every period; year capture: single point per year centered on its quarters.
    fig.add_trace(go.Scatter(
        x=periods,
        y=[-3] * len(periods),
        mode='markers',
        marker=dict(size=18, color='rgba(0,0,0,0)'),
        hoverinfo='skip',
        showlegend=False,
        customdata=[p.split(' ')[1] for p in periods],
        name='quarter-click-capture'
    ))
    year_click_x = []
    for year in range(2025, 2030):
        # Use the second quarter slot as the click anchor (roughly centered).
        year_click_x.append(f"{year} Q2")
    fig.add_trace(go.Scatter(
        x=year_click_x,
        y=[y_max + 2] * len(year_click_x),
        mode='markers',
        marker=dict(size=24, color='rgba(0,0,0,0)'),
        hoverinfo='skip',
        showlegend=False,
        customdata=[str(y) for y in range(2025, 2030)],
        name='year-click-capture'
    ))
    
    return fig

def create_world_map(df=None, selected_year=2025, selected_company="Exxon Mobil"):
    """Create world map showing geographical distribution for selected year - matching Tableau design exactly"""
    # Always use the dedicated map CSV when present to mirror the Tableau export.
    # Fall back to provided df only if the CSV is unavailable.
    map_df = MAP_DF.copy() if not MAP_DF.empty else (df.copy() if df is not None else pd.DataFrame())
    
    if map_df.empty:
        fig = go.Figure()
        fig.update_layout(
            geo=dict(
                showframe=False,
                showcoastlines=True,
                projection_type='equirectangular',
                bgcolor='rgba(0,0,0,0)',
                coastlinecolor='#d0d0d0',
                landcolor='#e8e8e8',
                showocean=True,
                oceancolor='white',
                showcountries=True,
                countrycolor='#bdbdbd'
            ),
            height=500,
            paper_bgcolor='white',
            plot_bgcolor='white',
            title={
                'text': f"Oil Projects Capacity Start Up by {selected_company} ('000 b/d)*- {selected_year}",
                'x': 0.02,
                'xanchor': 'left',
                'font': {'size': 16, 'family': 'Arial, sans-serif', 'color': '#2c3e50'}
            }
        )
        return fig
    
    # Filter by year
    year_df = map_df[map_df['Year of Period'] == selected_year].copy()
    
    # Create a blue/teal color scale that matches the reference map (soft teal to
    # deeper blue-green). Keeping the scale consistent avoids jumps when years
    # change and preserves the vertical legend look.
    colorscale = [
        [0.0, '#C7E8E4'],   # very light teal
        [0.16, '#A4DCD5'],  # light teal
        [0.32, '#7DC9C3'],  # medium-light teal
        [0.48, '#4FB2AF'],  # medium teal
        [0.64, '#2A94A1'],  # medium-dark teal
        [0.8, '#1F7A8A'],   # dark teal
        [1.0, '#1C6C7C']    # deepest teal
    ]
    
    # Fix the range to match the target legend (0.7 – 135.0) so the colorbar
    # always shows those endpoints and the shading matches the sample map.
    zmin, zmax = 0.7, 135.0
    
    # Aggregate by country (sum values if multiple entries per country)
    country_totals = year_df.groupby('Country')['value_company'].sum().reset_index()
    country_totals.columns = ['Country', 'Value']
    
    # Create choropleth map including all countries from the CSV
    fig = go.Figure(data=go.Choropleth(
        locations=country_totals['Country'],
        z=country_totals['Value'],
        locationmode='country names',
        colorscale=colorscale,
        zmin=zmin,
        zmax=zmax,
        marker_line_color='#ffffff',
        marker_line_width=0.5,
        hovertemplate='<b>%{location}</b><br>Production Addition: %{z:,.1f} \'000 b/d<extra></extra>',
        colorbar=dict(
            title="Production Additions ('000 b/d)",
            titleside='top',
            titlefont=dict(size=12, family='Arial, sans-serif', color='#1b365d'),
            tickfont=dict(size=10, family='Arial, sans-serif', color='#1b365d'),
            orientation='h',
            thickness=12,
            len=0.22,
            lenmode='fraction',
            x=1.0,
            xanchor='left',
            y=0.74,
            yanchor='top',
            outlinecolor='rgba(0,0,0,0)',
            outlinewidth=0,
            ticklen=0,
            tickvals=[0.7, 135.0],
            ticktext=['0.7', '135.0']
        ),
        showscale=False  # hide colorbar in the map; we render a custom legend beside controls
    ))
    
    # Update geo settings to match Tableau design
    fig.update_geos(
        showframe=False,
        showcoastlines=True,
        projection_type='equirectangular',
        bgcolor='rgba(0,0,0,0)',
        coastlinecolor='#c5c5c5',
        landcolor='#f2f2f2',  # light grey for countries with no data
        showocean=True,
        oceancolor='white',
        showcountries=True,
        countrycolor='#c5c5c5',
        showlakes=False,
        showrivers=False,
        resolution=50
    )
    
    fig.update_layout(
        height=520,
        paper_bgcolor='white',
        plot_bgcolor='white',
        margin=dict(l=0, r=190, t=30, b=10),
        title={
            'text': f"Oil Projects Capacity Start Up by {selected_company} ('000 b/d)*- {selected_year}",
            'x': 0.0,
            'xanchor': 'left',
            'y': 0.99,
            'yanchor': 'top',
            'font': {'size': 18, 'family': 'Georgia, serif', 'color': '#FF8C42'}
        },
        hovermode='closest',
        hoverlabel=dict(
            bgcolor='white',
            bordercolor='#999999',
            font_size=13,
            font_family='Arial, sans-serif',
            font_color='#000000'
        )
    )
    
    # Add copyright annotation at bottom left (matching Tableau)
    fig.add_annotation(
        text="© 2025 Mapbox © OpenStreetMap",
        xref="paper",
        yref="paper",
        x=0.01,
        y=0.01,
        showarrow=False,
        font=dict(size=10, color='#888888', family='Arial, sans-serif'),
        xanchor='left',
        yanchor='bottom'
    )
    
    return fig

def create_layout():
    """Create layout for Projects by Company with filters, year controls, legend, chart, map and table."""
    df_table = PROJECTS_RAW_DF.copy()
    if df_table.empty:
        data_full = []
        tooltip_data = []
    else:
        data_full = df_table.fillna("").to_dict('records')
        tooltip_data = []
        for row in data_full:
            tip_row = {}
            comments_val = str(row.get('Comments', '') or '').strip()
            if comments_val and comments_val.lower() != 'nan':
                tip_row['Comments'] = {'value': comments_val, 'type': 'text'}
            tooltip_data.append(tip_row)
    
    # Years for filters / slider
    years = get_unique_years()
    if years:
        min_year = min(years)
        max_year = max(years)
        default_year = years[0]
    else:
        # Sensible fallback based on Tableau dashboard (2025–2029)
        min_year, max_year, default_year = 2025, 2029, 2025
    
    # Countries for legend (match CSV as closely as possible)
    all_countries_from_data = get_unique_countries()
    legend_countries = (
        sorted(all_countries_from_data)
        if all_countries_from_data
        else sorted(list(COUNTRY_COLORS.keys()))
    )

    # Build clickable legend items – these are targeted by the pattern-matching callbacks
    legend_items = []
    for country in legend_countries:
        color = get_country_color(country)
        legend_items.append(
            html.Div(
                id={'type': 'country-item', 'index': country},
                children=[
                    html.Div(
                        style={
                            'width': '12px',
                            'height': '12px',
                            'backgroundColor': color,
                            'marginRight': '6px',
                            'borderRadius': '2px',
                            'flexShrink': '0'
                        }
                    ),
                    html.Span(
                        country,
                        style={
                            'fontSize': '12px',
                            'color': '#2c3e50',
                            'whiteSpace': 'nowrap'
                        }
                    )
                ],
                style={
                    'display': 'flex',
                    'alignItems': 'center',
                    'marginBottom': '4px',
                    'padding': '2px 4px',
                    'cursor': 'pointer',
                    'borderRadius': '3px'
                }
            )
        )

    layout = html.Div([
        # Stores and interval used by callbacks
        dcc.Store(id='selected-countries-store', data=[]),
        dcc.Store(id='year-period-play-store', data=False),
        dcc.Store(id='bar-highlight-year-store', data=None),
        dcc.Store(id='quarter-highlight-store', data=None),
        # Stores to keep full table data for filtering
        dcc.Store(id='projects-company-table-data-full', data=data_full if df_table is not None else []),
        dcc.Store(id='projects-company-table-tooltip-full', data=tooltip_data if df_table is not None else []),
        # Dummy target for clientside sort UI (adds A/Z hover like projects_latest)
        dcc.Store(id='projects-company-dummy-sort', data='', storage_type='memory'),
        dcc.Interval(
            id='year-period-interval',
            interval=2000,  # 2 seconds between steps when playing
            n_intervals=0,
            disabled=True
        ),
        
        # Top bar – only Company filter, matching Tableau
        html.Div([
            html.Label(
                "Company",
                style={
                    'fontSize': '12px',
                    'fontWeight': 'bold',
                    'color': '#1b365d',
                    'marginRight': '8px',
                    'whiteSpace': 'nowrap'
                }
            ),
            dcc.Dropdown(
                id='company-filter',
                options=[{'label': 'Exxon Mobil', 'value': 'Exxon Mobil'}],
                value='Exxon Mobil',
                clearable=False,
                style={
                    'width': '100%'
                }
            )
        ], style={
            'display': 'flex',
            'alignItems': 'center',
            'gap': '8px',
            'width': '100%',
            'marginBottom': '8px'
        }),
        
        # Main content – chart/map on the left, legend & filters on the right
        html.Div([
            # LEFT COLUMN: bar chart and map
            html.Div([
                dcc.Graph(
                    id='projects-company-bar-chart',
                    style={'height': '500px', 'marginBottom': '20px'}
                ),
                html.Div([
                    dcc.Graph(
                        id='projects-company-map',
                        style={
                            'height': '520px',
                            'width': '100%'
                        }
                    ),
                    html.Div([
                        html.Label(
                            "Year of Period",
                            style={
                                'fontSize': '12px',
                                'fontWeight': 'bold',
                                'color': '#1b365d',
                                'display': 'block',
                                'marginBottom': '4px'
                            }
                        ),
                        html.Div([
                            html.Button(
                                '◀',
                                id='year-period-prev',
                                n_clicks=0,
                                style={
                                    'border': '1px solid #ffffff',
                                    # 'backgroundColor': '#f5a623',
                                    'color': '#000000',
                                    'padding': '2px 6px',
                                    'fontSize': '12px',
                                    'cursor': 'pointer'
                                }
                            ),
                            dcc.Dropdown(
                                id='year-of-period-filter',
                                options=[{'label': str(y), 'value': y} for y in years] if years else [],
                                value=default_year,
                                clearable=False,
                                style={'width': '120px'}
                            ),
                            html.Button(
                                '▶',
                                id='year-period-next',
                                n_clicks=0,
                                style={
                                    'border': '1px solid #ffffff',
                                    # 'backgroundColor': '#f5a623',
                                    'color': '#000000',
                                    'padding': '2px 6px',
                                    'fontSize': '12px',
                                    'cursor': 'pointer'
                                }
                            )
                        ], style={'display': 'flex', 'alignItems': 'center', 'gap': '4px', 'marginBottom': '6px'}),
                        dcc.Slider(
                            id='year-period-slider',
                            min=min_year,
                            max=max_year,
                            step=1,
                            value=default_year,
                            marks={y: {'label': '|', 'style': {'color': '#666666', 'fontSize': '14px'}} for y in years} if years else {},
                            included=False
                        ),
                        html.Div([
                            html.Button(
                                '◀',
                                id='year-period-timeline-prev',
                                n_clicks=0,
                                style={
                                    'border': '1px solid #ffffff',
                                    # 'backgroundColor': '#f5a623',
                                    'color': '#000000',
                                    'padding': '2px 6px',
                                    'fontSize': '12px',
                                    'cursor': 'pointer'
                                }
                            ),
                            html.Button(
                                '■',
                                id='year-period-stop',
                                n_clicks=0,
                                style={
                                    'border': '1px solid #ffffff',
                                    'backgroundColor': '#000000',
                                    'color': '#ffffff',
                                    'padding': '2px 8px',
                                    'fontSize': '12px',
                                    'cursor': 'pointer'
                                }
                            ),
                            html.Button(
                                '▶',
                                id='year-period-play',
                                n_clicks=0,
                                style={
                                    'border': '1px solid #ffffff',
                                    # 'backgroundColor': '#f5a623',
                                    'color': '#000000',
                                    'padding': '2px 8px',
                                    'fontSize': '12px',
                                    'cursor': 'pointer'
                                }
                            )
                        ], style={'display': 'flex', 'alignItems': 'center', 'gap': '6px', 'margin': '8px 0 6px'}),
                        dcc.Checklist(
                            id='show-history-checkbox',
                            options=[{'label': 'Show history', 'value': 'history'}],
                            value=[],
                            labelStyle={'fontSize': '12px'}
                        ),
                        html.Div([
                            html.Div(
                                "Production Additions ('000 b/d)",
                                style={
                                    'fontSize': '11px',
                                    'color': '#1b365d',
                                    'marginBottom': '4px',
                                    'fontFamily': 'Arial, sans-serif'
                                }
                            ),
                            html.Div(style={
                                'height': '14px',
                                'width': '210px',
                                'background': 'linear-gradient(to right, #C7E8E4, #A4DCD5, #7DC9C3, #4FB2AF, #2A94A1, #1F7A8A, #1C6C7C)',
                                'border': '1px solid #c5c5c5',
                                'borderRadius': '2px'
                            }),
                            html.Div([
                                html.Span('0.7', style={'fontSize': '10px', 'color': '#1b365d'}),
                                html.Span('135.0', style={'fontSize': '10px', 'color': '#1b365d', 'marginLeft': 'auto'})
                            ], style={
                                'display': 'flex',
                                'justifyContent': 'space-between',
                                'width': '210px',
                                'marginTop': '2px'
                            })
                        ], style={'marginTop': '10px'}),
                        html.Div(
                            id='year-period-display',
                            style={'display': 'none'}
                        )
                    ], style={
                        'position': 'absolute',
                        'top': '10px',
                        'right': '-243px',
                        'backgroundColor': '#ffffff',
                        'padding': '8px 10px',
                        'border': '1px solid #dcdcdc',
                        'borderRadius': '4px',
                        'boxShadow': '0 1px 4px rgba(0, 0, 0, 0.12)',
                        'minWidth': '220px',
                        'zIndex': 5
                    })
                ], style={
                    'position': 'relative',
                    'height': '520px',
                    'marginBottom': '20px'
                })
            ], style={'flex': '4', 'minWidth': '0'}),
            
            # RIGHT COLUMN: legend, Likely To Go, year controls, history toggle
            html.Div([
                html.Div(
                    "Country",
                    style={
                        'fontWeight': 'bold',
                        'fontSize': '13px',
                        'color': '#1b365d',
                        'marginBottom': '4px'
                    }
                ),
                html.Div(
                    legend_items,
                    style={
                        'display': 'flex',
                        'flexDirection': 'column',
                        'flexWrap': 'nowrap',
                        'maxHeight': '260px',
                        'overflowY': 'auto',
                        'padding': '6px 8px',
                        'border': '1px solid #e0e0e0',
                        'borderRadius': '4px',
                        'backgroundColor': '#fafafa',
                        'marginBottom': '10px'
                    }
                ),
                
                html.Div([
                    html.Label(
                        "Likely To Go Ahead",
                        style={
                            'fontSize': '12px',
                            'fontWeight': 'bold',
                            'color': '#1b365d',
                            'display': 'block',
                            'marginBottom': '4px'
                        }
                    ),
                    dcc.Checklist(
                        id='likely-to-go-filter',
                        options=[
                            {'label': '(All)', 'value': 'ALL'},
                            {'label': '', 'value': 'EMPTY'},
                            {'label': 'N', 'value': 'N'},
                            {'label': 'Uncertain', 'value': 'UNCERTAIN'},
                            {'label': 'Y', 'value': 'Y'},
                        ],
                        value=['Y'],
                        labelStyle={
                            'display': 'block',
                            'fontSize': '12px',
                            'marginBottom': '2px'
                        }
                    )
                ], style={'marginBottom': '14px'}),
            ], style={
                'flex': '1',
                'minWidth': '260px',
                'maxWidth': '340px',
                'marginLeft': '20px'
            })
        ], style={
            'display': 'flex',
            'alignItems': 'flex-start'
        }),
        
        # Projects table – match design from projects_by_time
        html.Div([
            html.H4(
                "Project Details",
                style={
                    'marginBottom': '15px',
                    'fontSize': '16px',
                    'fontWeight': 'bold',
                    'fontFamily': 'Lato, sans-serif',
                    'color': '#fe5000',
                    'textAlign': 'left'
                }
            ),
            dcc.Loading(
                id="loading-projects-company-table",
                type="default",
                children=dash_table.DataTable(
                    id='projects-company-table',
                    columns=[],
                    data=[],
                    tooltip_data=[],
                    tooltip_duration=None,
                    page_action='none',
                    sort_action='native',
                    filter_action='native',
                    style_table={
                        'overflowX': 'auto',
                        'overflowY': 'auto',
                        'maxHeight': '600px',
                        'width': '100%',
                        'border': '1px solid #ddd'
                    },
                    style_cell={
                        'textAlign': 'left',
                        'padding': '8px',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                        'overflow': 'hidden',
                        'textOverflow': 'ellipsis',
                        'maxWidth': '180px',
                        'fontSize': '12px',
                        'border': '1px solid #ddd',
                        'backgroundColor': '#fff',
                        'fontFamily': 'Lato, sans-serif',
                        'color': 'rgb(27, 54, 93)'
                    },
                    style_header={
                        'backgroundColor': '#f8f9fa',
                        'fontWeight': 'bold',
                        'fontFamily': 'Lato, sans-serif',
                        'color': 'rgb(27, 54, 93)',
                        'border': '1px solid #ddd',
                        'textAlign': 'center',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                        'position': 'relative'
                    },
                    style_data={
                        'border': '1px solid #ddd',
                        'whiteSpace': 'normal',
                        'fontFamily': 'Lato, sans-serif',
                        'color': 'rgb(27, 54, 93)'
                    },
                    style_data_conditional=[
                        {'if': {'row_index': 'odd'}, 'backgroundColor': '#f9f9f9'},
                        {
                            'if': {'column_id': 'Comments'},
                            'whiteSpace': 'nowrap',
                            'overflow': 'hidden',
                            'textOverflow': 'ellipsis',
                            'height': 'auto',
                            'textAlign': 'left'
                        }
                    ],
                    css=[{
                        'selector': '.dash-table-tooltip',
                        'rule': 'font-size: 10px !important; font-family: Lato, sans-serif !important; color: rgb(27, 54, 93) !important; max-width: 400px !important; white-space: normal !important; word-wrap: break-word !important; line-height: 1.4 !important; padding: 6px 8px !important;'
                    }, {
                        'selector': '.dash-table-container .row:last-child',
                        'rule': 'display: none !important;'
                    }, {
                        'selector': '.previous-page, .next-page, .first-page, .last-page, .page-number, .page-number--current',
                        'rule': 'display: none !important;'
                    }]
                )
            )
        ], style={'marginTop': '20px'})
    ], style={'padding': '10px 18px'})
    return layout

def register_callbacks(dash_app, server):
    """Register all callbacks for Projects by Company"""
    
    # Get all countries from CSV data for creating dynamic outputs
    # This ensures all countries in the data are available for filtering
    all_countries_from_data = get_unique_countries()
    legend_countries = sorted(all_countries_from_data) if all_countries_from_data else sorted(list(COUNTRY_COLORS.keys()))
    
    # Create outputs for all country items
    country_outputs = [
        Output({'type': 'country-item', 'index': country}, 'style')
        for country in legend_countries
    ]
    
    @callback(
        Output('selected-countries-store', 'data', allow_duplicate=True),
        Input({'type': 'country-item', 'index': ALL}, 'n_clicks'),
        State('selected-countries-store', 'data'),
        prevent_initial_call=True
    )
    def toggle_country(_clicks, selected_countries):
        """Toggle country selection on click"""
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update
        
        # Get the triggered country
        triggered = ctx.triggered[0]["prop_id"]
        try:
            country_id = json.loads(triggered.split('.')[0])
            clicked_country = country_id.get("index")
        except (ValueError, TypeError, AttributeError, KeyError):
            return dash.no_update
        
        if not clicked_country or clicked_country not in legend_countries:
            return dash.no_update
        
        # Initialize selected_countries if None
        if selected_countries is None:
            selected_countries = []
        
        # Toggle the clicked country
        if clicked_country in selected_countries:
            # Deselect
            new_selected = [c for c in selected_countries if c != clicked_country]
        else:
            # Select
            new_selected = selected_countries + [clicked_country] if selected_countries else [clicked_country]
        
        return new_selected
    
    @callback(
        country_outputs,
        Input('selected-countries-store', 'data'),
        prevent_initial_call=False
    )
    def update_country_styles(selected_countries):
        """Update country item styles based on store"""
        selected_countries = selected_countries or []
        styles = []
        for country in legend_countries:
            is_selected = country in selected_countries
            country_color = get_country_color(country)
            # Match Tableau design: selected countries get a colored border matching their color
            # and a subtle background highlight
            styles.append({
                'display': 'flex',
                'alignItems': 'center',
                'marginBottom': '4px',
                'padding': '2px 4px',
                'cursor': 'pointer',
                'borderRadius': '3px',
                'border': f'2px solid {country_color}' if is_selected else '1px solid transparent',
                'backgroundColor': 'rgba(240, 240, 240, 0.5)' if is_selected else 'transparent',
                'transition': 'all 0.2s ease'
            })
        return styles
    
    # Initial callback to set year display
    @callback(
        Output('year-period-display', 'children', allow_duplicate=True),
        Input('year-of-period-filter', 'value'),
        prevent_initial_call='initial_duplicate'
    )
    def initialize_year_display(year_value):
        """Initialize year display on page load"""
        if year_value:
            return str(year_value)
        years = get_unique_years()
        return str(years[0]) if years else '2025'
    
    # Normalize Likely To Go checklist: (All) selects all; otherwise keep only the latest choice.
    @callback(
        Output('likely-to-go-filter', 'value'),
        Input('likely-to-go-filter', 'value'),
        prevent_initial_call=True
    )
    def normalize_likely_to_go(selected):
        """Checklist behavior: (All) checks everything; otherwise allow multi-select and dedupe."""
        options_all = ['ALL', 'EMPTY', 'N', 'UNCERTAIN', 'Y']
        if not selected:
            return ['Y']
        # If All is present, force all options on
        if 'ALL' in selected:
            return options_all
        # Otherwise keep the order and remove duplicates
        seen = []
        for v in selected:
            if v not in seen:
                seen.append(v)
        return seen
    
    @callback(
        [Output('projects-company-table', 'data'),
         Output('projects-company-table', 'tooltip_data'),
         Output('projects-company-table', 'columns')],
        [Input('likely-to-go-filter', 'value'),
         Input('selected-countries-store', 'data')],
        [State('projects-company-table-data-full', 'data'),
         State('projects-company-table-tooltip-full', 'data')],
        prevent_initial_call=False
    )
    def filter_projects_company_table(likely_filter, selected_countries, data_full, tooltip_full):
        """Filter and format the Projects by Company table to mirror projects_by_time layout."""
        data_full = data_full or []
        tooltip_full = tooltip_full or []
        
        if not data_full:
            return [], [], []
        
        df = pd.DataFrame(data_full)
        
        # Filter by selected countries (when any are chosen)
        if selected_countries:
            df = df[df['Country'].isin(selected_countries)]
        
        if df.empty:
            return [], [], []
        
        # Find likely-go-ahead column
        likely_col = None
        for col in df.columns:
            col_lower = str(col).lower()
            if 'likely' in col_lower and ('go' in col_lower or 'ahead' in col_lower):
                likely_col = col
                break
        
        # Normalize Likely To Go filter (match projects_by_time behavior)
        if not likely_filter:
            likely_filter = []
        if not isinstance(likely_filter, list):
            likely_filter = [likely_filter]
        
        selected_statuses = []
        if 'ALL' in [str(v).upper() for v in likely_filter]:
            selected_statuses = ['Y', 'N', 'UNCERTAIN', '']
        else:
            for v in likely_filter:
                v_up = str(v).upper()
                if v_up == 'Y':
                    selected_statuses.append('Y')
                elif v_up == 'N':
                    selected_statuses.append('N')
                elif v_up.startswith('U'):
                    selected_statuses.append('UNCERTAIN')
                elif v_up == 'EMPTY':
                    selected_statuses.append('')
                elif v == '':
                    selected_statuses.append('')
        
        if likely_col and selected_statuses:
            df[likely_col] = df[likely_col].astype(str).str.strip()
            col_upper = df[likely_col].str.upper()
            mask = pd.Series(False, index=df.index)
            for status in selected_statuses:
                if status == 'Y':
                    mask |= col_upper.str.startswith('Y')
                elif status == 'N':
                    mask |= col_upper.str.startswith('N')
                elif status == 'UNCERTAIN' or status == 'U':
                    mask |= col_upper.str.startswith('U')
                elif status == '':
                    mask |= (col_upper == '')
            df = df[mask].copy()
        elif likely_col and not selected_statuses:
            df = pd.DataFrame()
        
        if df.empty:
            return [], [], []
        
        # Preserve all available columns; order them similar to projects_by_time
        base_priority = [
            'Project Name',
            'Likely Go-ahead',
            'Country',
            'Region',
            'Group',
            'Hydrocarbon',
            'Depth',
            'Field/Block',
            'Play Type',
            'Operator',
            'Partner1',
            'Partner2',
            'Partner3',
            'Partner4',
            'Partner5',
            'First Oil Year',
            'Sanctioned',
            'Comments',
            'Project Status',
            'Gas Reserves (mmboe)',
            'Liquids Reserves (mmbbl)',
            'Total Reserves (mmboe)',
            'API',
            'Sulfur',
            'Operator Share %',
            'Partner1 Share %',
            'Partner2 Share %',
            'Partner3 Share %',
            'Partner4 Share %',
            'Partner5 Share %',
        ]
        
        all_cols = list(df.columns)
        quarter_cols = [
            c for c in all_cols
            if isinstance(c, str) and len(c) == 7 and c[4] == '_' and c[:4].isdigit()
        ]
        
        def quarter_key(name):
            try:
                year = int(name[:4])
                q = int(name[-1])
                return (year, q)
            except Exception:
                return (9999, 9)
        
        quarter_cols = sorted(quarter_cols, key=quarter_key)
        
        ordered_cols = (
            [c for c in base_priority if c in all_cols] +
            [c for c in all_cols if c not in base_priority and c not in quarter_cols] +
            quarter_cols
        )
        
        df = df[[c for c in ordered_cols if c in df.columns]].copy()
        df = df.reset_index(drop=True)
        
        # Format numeric reserve columns
        numeric_cols = ['Gas Reserves (mmboe)', 'Liquids Reserves (mmbbl)', 'Total Reserves (mmboe)']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].apply(lambda x: f'{x:,.3f}' if pd.notna(x) and x != 0 else '')
        
        # Normalize boolean / categorical displays
        bool_display_map = {
            'Y': 'Yes',
            'N': 'No',
            'U': 'Uncertain',
            'TRUE': 'Yes',
            'FALSE': 'No'
        }
        
        for col in ['Likely Go-ahead', 'Sanctioned']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].apply(lambda v: bool_display_map.get(str(v).upper(), v))
        
        # Preserve full comments for tooltips; truncate in display
        if 'Comments' in df.columns:
            original_comments = df['Comments'].copy()
            df['Comments'] = df['Comments'].astype(str).apply(lambda x: (x[:10] + '...') if len(x) > 10 else x)
        else:
            original_comments = pd.Series([''] * len(df))
        
        # Build columns with consistent display names and widths
        column_widths = {
            'Project Name': '180px',
            'Likely Go-ahead': '130px',
            'Country': '120px',
            'Region': '120px',
            'Group': '140px',
            'Hydrocarbon': '120px',
            'Depth': '80px',
            'Field/Block': '140px',
            'Play Type': '120px',
            'Operator': '120px',
            'Partner1': '100px',
            'Partner2': '100px',
            'Partner3': '100px',
            'Partner4': '100px',
            'Partner5': '100px',
            'First Oil Year': '100px',
            'Sanctioned': '80px',
            'Comments': '140px',
            'Project Status': '120px',
            'Gas Reserves (mmboe)': '140px',
            'Liquids Reserves (mmbbl)': '150px',
            'Total Reserves (mmboe)': '150px',
            'API': '80px',
            'Sulfur': '80px'
        }
        
        display_name_map = {
            'Likely Go-ahead': 'Likely To Go Ahead',
            'Field/Block': 'Field/Block',
            'Play Type': 'Play Type',
            'Group': 'Group'
        }
        
        available_cols = list(df.columns)
        quarter_cols = [
            c for c in available_cols
            if isinstance(c, str) and len(c) == 7 and c[4] == '_' and c[:4].isdigit()
        ]
        
        columns = []
        for col in available_cols:
            display_name = display_name_map.get(col, col)
            col_def = {'name': display_name, 'id': col}
            if col in column_widths:
                col_def['minWidth'] = column_widths[col]
                col_def['maxWidth'] = column_widths[col]
            elif col in quarter_cols:
                col_def['minWidth'] = '85px'
            columns.append(col_def)
        
        df = df.fillna('')
        data = df.to_dict('records')
        
        tooltip_data = []
        for idx, row in enumerate(data):
            tip_row = {}
            comment_val = original_comments.iloc[idx] if idx < len(original_comments) else ''
            if pd.notna(comment_val):
                comment_str = str(comment_val).strip()
                if comment_str and comment_str.lower() != 'nan':
                    tip_row['Comments'] = {'value': comment_str, 'type': 'text'}
            tooltip_data.append(tip_row)
        
        return data, tooltip_data, columns
    
    # Add A/Z hover sort UI on selected headers (matches projects_latest behavior)
    dash_app.clientside_callback(
        """
        function(columns) {
            setTimeout(function() {
                function addSortUI(header) {
                    if (header.querySelector('.sort-order-container')) {
                        return;
                    }
                    const sortContainer = document.createElement('div');
                    sortContainer.style.position = 'absolute';
                    sortContainer.style.right = '30px';
                    sortContainer.style.top = '50%';
                    sortContainer.style.transform = 'translateY(-50%)';
                    sortContainer.style.fontSize = '10px';
                    sortContainer.style.color = '#666';
                    sortContainer.style.cursor = 'pointer';
                    sortContainer.style.padding = '2px';
                    sortContainer.style.border = '1px solid transparent';
                    sortContainer.style.borderRadius = '2px';
                    sortContainer.style.lineHeight = '1';
                    sortContainer.style.textAlign = 'center';
                    sortContainer.style.display = 'flex';
                    sortContainer.style.flexDirection = 'column';
                    sortContainer.style.alignItems = 'center';
                    sortContainer.style.justifyContent = 'center';
                    sortContainer.style.height = '30px';
                    sortContainer.style.opacity = '0';
                    sortContainer.style.transition = 'opacity 0.2s ease';
                    sortContainer.style.zIndex = '2';
                    sortContainer.className = 'sort-order-container';
                    
                    const aElement = document.createElement('div');
                    aElement.textContent = 'A';
                    aElement.title = 'Click for ascending order';
                    aElement.style.display = 'block';
                    aElement.style.lineHeight = '1';
                    aElement.style.cursor = 'pointer';
                    aElement.style.padding = '1px 2px';
                    aElement.style.borderRadius = '1px';
                    aElement.style.fontFamily = 'Lato, sans-serif';
                    aElement.style.fontSize = '10px';
                    aElement.onmouseover = function() {
                        aElement.style.backgroundColor = '#d4e7ff';
                        aElement.style.fontWeight = 'bold';
                    };
                    aElement.onmouseout = function() {
                        aElement.style.backgroundColor = '';
                        aElement.style.fontWeight = '';
                    };
                    aElement.onclick = function(e) {
                        e.stopPropagation();
                        for (let i = 0; i < 3; i++) {
                            header.click();
                        }
                    };
                    
                    const zElement = document.createElement('div');
                    zElement.textContent = 'Z';
                    zElement.title = 'Click for descending order';
                    zElement.style.display = 'block';
                    zElement.style.lineHeight = '1';
                    zElement.style.cursor = 'pointer';
                    zElement.style.padding = '1px 2px';
                    zElement.style.borderRadius = '1px';
                    zElement.style.fontFamily = 'Lato, sans-serif';
                    zElement.style.fontSize = '10px';
                    zElement.onmouseover = function() {
                        zElement.style.backgroundColor = '#d4e7ff';
                        zElement.style.fontWeight = 'bold';
                    };
                    zElement.onmouseout = function() {
                        zElement.style.backgroundColor = '';
                        zElement.style.fontWeight = '';
                    };
                    zElement.onclick = function(e) {
                        e.stopPropagation();
                        for (let i = 0; i < 2; i++) {
                            header.click();
                        }
                    };
                    
                    sortContainer.appendChild(aElement);
                    sortContainer.appendChild(zElement);
                    header.appendChild(sortContainer);
                    
                    const sortIndicator = document.createElement('div');
                    sortIndicator.style.position = 'absolute';
                    sortIndicator.style.right = '8px';
                    sortIndicator.style.top = '50%';
                    sortIndicator.style.transform = 'translateY(-50%)';
                    sortIndicator.style.width = '15px';
                    sortIndicator.style.height = '15px';
                    sortIndicator.style.cursor = 'pointer';
                    sortIndicator.style.opacity = '0';
                    sortIndicator.style.transition = 'opacity 0.2s ease';
                    sortIndicator.style.zIndex = '1';
                    sortIndicator.title = 'Click to sort';
                    sortIndicator.className = 'sort-indicator';
                    
                    sortIndicator.innerHTML = `
                        <svg fill="#666" viewBox="0 0 301.219 301.219" xmlns="http://www.w3.org/2000/svg">
                            <g>
                                <path d="M159.365,23.736v-10c0-5.523-4.477-10-10-10H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h139.365
                                    C154.888,33.736,159.365,29.259,159.365,23.736z"/>
                                <path d="M130.586,66.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h120.586c5.523,0,10-4.477,10-10v-10
                                    C140.586,71.213,136.109,66.736,130.586,66.736z"/>
                                <path d="M111.805,129.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h101.805c5.523,0,10-4.477,10-10v-10
                                    C121.805,134.213,117.328,129.736,111.805,129.736z"/>
                                <path d="M93.025,199.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h83.025c5.522,0,10-4.477,10-10v-10
                                    C103.025,204.213,98.548,199.736,93.025,199.736z"/>
                                <path d="M74.244,262.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h64.244c5.522,0,10-4.477,10-10v-10
                                    C84.244,267.213,79.767,262.736,74.244,262.736z"/>
                                <path d="M298.29,216.877l-7.071-7.071c-1.875-1.875-4.419-2.929-7.071-2.929c-2.652,0-5.196,1.054-7.072,2.929l-34.393,34.393
                                    V18.736c0-5.523-4.477-10-10-10h-10c-5.523,0-10,4.477-10,10v225.462l-34.393-34.393c-1.876-1.875-4.419-2.929-7.071-2.929
                                    c-2.652,0-5.196,1.054-7.071,2.929l-7.072,7.071c-3.904,3.905-3.904,10.237,0,14.142l63.536,63.536
                                    c1.953,1.953,4.512,2.929,7.071,2.929c2.559,0,5.119-0.976,7.071-2.929l63.536-63.536
                                    C302.195,227.113,302.195,220.781,298.29,216.877z"/>
                            </g>
                        </svg>
                    `;
                    
                    sortIndicator.onmouseover = function() {
                        sortIndicator.style.opacity = '1';
                        sortIndicator.style.backgroundColor = '#e6f3ff';
                        sortIndicator.style.borderRadius = '2px';
                        sortIndicator.querySelector('svg').style.fill = '#1f3263';
                    };
                    
                    sortIndicator.onmouseout = function() {
                        sortIndicator.style.opacity = '0';
                        sortIndicator.style.backgroundColor = '';
                        sortIndicator.querySelector('svg').style.fill = '#666';
                    };
                    
                    sortIndicator.onclick = function(e) {
                        e.stopPropagation();
                        // Toggle sort by clicking the header twice
                        for (let i = 0; i < 2; i++) {
                            header.click();
                        }
                    };
                    
                    header.appendChild(sortIndicator);
                    
                    header.onmouseover = function() {
                        sortContainer.style.opacity = '1';
                        sortIndicator.style.opacity = '1';
                    };
                    
                    header.onmouseout = function() {
                        sortContainer.style.opacity = '0';
                        sortIndicator.style.opacity = '0';
                    };
                }
                
                const headers = document.querySelectorAll('#projects-company-table .dash-header');
                headers.forEach(header => {
                    addSortUI(header);
                });
            }, 500);
            return '';
        }
        """,
        Output('projects-company-dummy-sort', 'data'),
        Input('projects-company-table', 'columns'),
        prevent_initial_call=False
    )
    
    # Callback to sync year controls (display, dropdown, slider, prev/next buttons)
    @callback(
        [Output('year-period-display', 'children'),
         Output('year-of-period-filter', 'value', allow_duplicate=True),
         Output('year-period-slider', 'value', allow_duplicate=True),
         Output('bar-highlight-year-store', 'data', allow_duplicate=True)],
        [Input('year-of-period-filter', 'value'),
         Input('year-period-slider', 'value'),
         Input('year-period-prev', 'n_clicks'),
         Input('year-period-next', 'n_clicks'),
         Input('year-period-timeline-prev', 'n_clicks'),
         Input('year-period-interval', 'n_intervals')],
        [State('year-period-slider', 'min'),
         State('year-period-slider', 'max'),
         State('year-period-play-store', 'data'),
         State('bar-highlight-year-store', 'data')],
        prevent_initial_call=True
    )
    def sync_year_controls(dropdown_value, slider_value, prev_clicks, next_clicks, 
                           timeline_prev_clicks, interval_tick, min_year, max_year, is_playing, bar_highlight_year):
        """Sync year display, dropdown, slider, navigation buttons; keep chart highlight unchanged."""
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        current_year = dropdown_value or slider_value or min_year
        
        try:
            current_year = int(current_year)
        except (ValueError, TypeError):
            current_year = min_year
        
        # Handle different triggers
        if trigger_id == 'year-period-prev':
            new_year = max(current_year - 1, min_year)
        elif trigger_id == 'year-period-next':
            new_year = min(current_year + 1, max_year)
        elif trigger_id == 'year-period-timeline-prev':
            new_year = max(current_year - 1, min_year)
        elif trigger_id == 'year-period-interval':
            if is_playing:
                # Auto-advance to next year, loop back to min if at max
                if current_year >= max_year:
                    new_year = min_year
                else:
                    new_year = current_year + 1
            else:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        elif trigger_id == 'year-of-period-filter':
            new_year = dropdown_value
        elif trigger_id == 'year-period-slider':
            new_year = slider_value
        else:
            new_year = current_year
        
        # Do not change bar highlight when year controls change; keep prior highlight (if any)
        return str(new_year), new_year, new_year, dash.no_update

    # Clicking a bar (or invisible quarter/year markers) selects that year's controls and optional quarter highlight
    @callback(
        [Output('year-of-period-filter', 'value', allow_duplicate=True),
         Output('year-period-slider', 'value', allow_duplicate=True),
         Output('bar-highlight-year-store', 'data', allow_duplicate=True),
         Output('quarter-highlight-store', 'data', allow_duplicate=True)],
        Input('projects-company-bar-chart', 'clickData'),
        prevent_initial_call=True
    )
    def set_year_from_bar_click(click_data):
        """When a bar is clicked, sync the year selection controls to that year and set highlight."""
        if not click_data or 'points' not in click_data or not click_data['points']:
            # Clear highlights when clicking outside/blank
            return dash.no_update, dash.no_update, None, None
        
        try:
            x_val = click_data['points'][0].get('x')
            year_part = str(x_val).split(' ')[0]
            selected_year = int(year_part)
        except (ValueError, TypeError, AttributeError, IndexError):
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Quarter highlight comes from customdata (set on invisible quarter capture trace) or from x label.
        quarter_val = None
        try:
            quarter_val = click_data['points'][0].get('customdata')
        except Exception:
            quarter_val = None
        if not quarter_val and isinstance(x_val, str) and ' ' in x_val:
            # Fallback: parse from x category text
            parts = str(x_val).split(' ')
            if len(parts) > 1:
                quarter_val = parts[1]
        
        return selected_year, selected_year, selected_year, quarter_val
    
    # Callback to handle play/pause/stop buttons
    @callback(
        [Output('year-period-play-store', 'data'),
         Output('year-period-interval', 'disabled'),
         Output('year-period-play', 'children')],
        [Input('year-period-play', 'n_clicks'),
         Input('year-period-stop', 'n_clicks')],
        [State('year-period-play-store', 'data')],
        prevent_initial_call=True
    )
    def toggle_year_animation(play_clicks, stop_clicks, is_playing):
        """Toggle auto-play animation of the year slider"""
        ctx = callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'year-period-stop':
            return False, True, '▶'  # Stop playing
        elif trigger_id == 'year-period-play':
            # Toggle play state
            new_state = not bool(is_playing)
            return new_state, not new_state, '⏸' if new_state else '▶'
        
        return dash.no_update, dash.no_update, dash.no_update
    
    @callback(
        [Output('projects-company-bar-chart', 'figure'),
         Output('projects-company-map', 'figure')],
        [Input('current-submenu', 'data'),
         Input('company-filter', 'value'),
         Input('likely-to-go-filter', 'value'),
         Input('year-of-period-filter', 'value'),
         Input('year-period-slider', 'value'),
         Input('show-history-checkbox', 'value'),
         Input('selected-countries-store', 'data'),
         Input('bar-highlight-year-store', 'data')],
        prevent_initial_call=False
    )
    def update_projects_by_company(submenu, company, likely_to_go, selected_year, slider_year, show_history, selected_countries, bar_highlight_year):
        """Update projects by company chart and map"""
        # Handle checklist value (after normalization) - keep list for filtering
        ltg_list = likely_to_go if isinstance(likely_to_go, list) else ([likely_to_go] if likely_to_go else [])
        
        # Check if this is the correct submenu (allow None on initial load)
        if submenu is not None and submenu != 'projects-company':
            empty_fig = go.Figure()
            empty_fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return empty_fig, empty_fig
        
        # Use the year from dropdown or slider (whichever is more recent)
        year_to_use = selected_year if selected_year else slider_year
        if not year_to_use:
            year_to_use = get_unique_years()[0] if get_unique_years() else 2025
        
        # Filter data
        df = DATA_DF.copy()
        
        if df.empty:
            empty_fig = go.Figure()
            empty_fig.add_annotation(
                text="No data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            empty_fig.update_layout(height=500, plot_bgcolor='white', paper_bgcolor='white')
            return empty_fig, empty_fig
        
        # Note: Likely To Go filter would require additional data column
        # Apply Likely To Go filter (matches table + projects_by_time behavior)
        likely_col = None
        for col in df.columns:
            col_lower = str(col).lower()
            if 'likely' in col_lower and ('go' in col_lower or 'ahead' in col_lower):
                likely_col = col
                break
        if likely_col:
            df[likely_col] = df[likely_col].astype(str).str.strip()
            col_upper = df[likely_col].str.upper()
            # Build selected statuses
            selected_statuses = []
            if isinstance(likely_to_go, list):
                ltg_list = likely_to_go
            else:
                ltg_list = [likely_to_go] if likely_to_go else []
            if 'ALL' in ltg_list:
                selected_statuses = ['Y', 'N', 'UNCERTAIN', '']
            else:
                for v in ltg_list:
                    v_up = str(v).upper()
                    if v_up == 'Y':
                        selected_statuses.append('Y')
                    elif v_up == 'N':
                        selected_statuses.append('N')
                    elif v_up.startswith('U'):
                        selected_statuses.append('UNCERTAIN')
                    elif v_up == 'EMPTY':
                        selected_statuses.append('')
                    elif v == '':
                        selected_statuses.append('')
            if selected_statuses:
                mask = pd.Series(False, index=col_upper.index)
                for status in selected_statuses:
                    if status == 'Y':
                        mask |= col_upper.str.startswith('Y')
                    elif status == 'N':
                        mask |= col_upper.str.startswith('N')
                    elif status == 'UNCERTAIN' or status == 'U':
                        mask |= col_upper.str.startswith('U')
                    elif status == '':
                        mask |= (col_upper == '')
                df = df[mask].copy()
            else:
                df = pd.DataFrame()
        
        # Use selected countries for filtering
        # If empty list, show all countries. If countries are selected, show only those.
        countries_to_show = selected_countries if selected_countries else None
        
        # Create bar chart - show all years by default (matches Tableau behavior)
        # The bar chart displays all available years/quarters
        bar_df = df.copy()
        bar_fig = create_stacked_bar_chart(
            bar_df,
            company or "Company",
            countries_to_show,
            highlight_year=bar_highlight_year
        )
        
        # Create map - always filtered by selected year (Year of Period filter controls the map)
        map_fig = create_world_map(df, year_to_use, company or "Company")
        
        return bar_fig, map_fig
