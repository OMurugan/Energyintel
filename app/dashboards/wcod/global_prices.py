"""
Global Crude Prices View
Monthly Crude Spot Prices ($/bbl) - Matching Energy Intelligence design
"""
import logging
from dash import dcc, html, Input, Output, callback, dash_table, State, clientside_callback, ClientsideFunction
import pandas as pd
from sqlalchemy import text

from core.data_helpers import get_db_engine, execute_query

logger = logging.getLogger(__name__)


# Month → quarter mapping
MONTH_TO_QUARTER = {
    'January': 'Q1', 'February': 'Q1', 'March': 'Q1',
    'April': 'Q2', 'May': 'Q2', 'June': 'Q2',
    'July': 'Q3', 'August': 'Q3', 'September': 'Q3',
    'October': 'Q4', 'November': 'Q4', 'December': 'Q4'
}

# Query for Spot Prices - generates all combinations of dates × crudes
# Ensures all date/crude combinations exist (with NULL prices where missing)
CRUDE_PRICE_QUERY = """
    SET LOCAL statement_timeout = 300000;  -- 300s to avoid cancel on large pull
    WITH crude_names AS (
        SELECT DISTINCT 
            fwp.crude_country_id, 
            fwp.crude_country, 
            fwp.crude_id, 
            fwp.crude_name, 
            dc.region,
            dc.country_long_name AS country_name
        FROM dev.fact_wcod_prices fwp 
        JOIN dev.dim_country dc ON fwp.crude_country_id = dc.dim_country_id 
        WHERE fwp.price_type = 'Spot'
          AND COALESCE(fwp.to_be_deleted, FALSE) = FALSE
    ),
    date_range AS (
        SELECT generate_series(
            (SELECT MIN(date) FROM dev.fact_wcod_prices WHERE price_type = 'Spot' AND COALESCE(to_be_deleted, FALSE) = FALSE),
            (SELECT MAX(date) FROM dev.fact_wcod_prices WHERE price_type = 'Spot' AND COALESCE(to_be_deleted, FALSE) = FALSE),
            '1 day'::interval
        )::date AS price_date
    ),
    all_combinations AS (
        SELECT 
            cn.crude_country_id, 
            cn.crude_country, 
            cn.crude_id, 
            cn.crude_name, 
            cn.region, 
            cn.country_name,
            dr.price_date,
            EXTRACT(YEAR FROM dr.price_date)::int AS year_int,
            TO_CHAR(dr.price_date, 'FMMonth') AS month_name,
            EXTRACT(MONTH FROM dr.price_date)::int AS month_num,
            EXTRACT(DAY FROM dr.price_date)::int AS day_num,
            CONCAT('Q', EXTRACT(QUARTER FROM dr.price_date)::int) AS quarter
        FROM crude_names cn
        CROSS JOIN date_range dr
    ),
    spot_prices AS (
        SELECT 
            fwp.date AS price_date,
            fwp.crude_country_id,
            fwp.crude_id,
            ROUND(fwp.price, 2) AS spot_price
        FROM dev.fact_wcod_prices fwp 
        WHERE fwp.price_type = 'Spot'
          AND COALESCE(fwp.to_be_deleted, FALSE) = FALSE
    )
    SELECT 
        ac.price_date,
        ac.region,
        ac.crude_country_id,
        ac.crude_country,
        ac.crude_id,
        ac.crude_name,
        ac.country_name,
        sp.spot_price AS avg_price,
        ac.year_int,
        ac.month_name,
        ac.month_num,
        ac.day_num,
        ac.quarter
    FROM all_combinations ac
    LEFT JOIN spot_prices sp ON sp.crude_country_id = ac.crude_country_id
                            AND sp.crude_id = ac.crude_id
                            AND sp.price_date = ac.price_date
    ORDER BY ac.year_int DESC, ac.month_num DESC, ac.region, ac.crude_country, ac.crude_name
"""


def load_crude_prices_data():
    """Load and parse crude prices data from Postgres (long format)."""
    results = execute_query(CRUDE_PRICE_QUERY)
    df = pd.DataFrame(results)

    if df.empty:
        raise Exception("No crude price data returned from database.")

    # Log a small summary to confirm query is working
    try:
        logger.info(
            "[global_prices] rows=%s dates=%s..%s crudes=%s regions=%s",
            len(df),
            df['price_date'].min(),
            df['price_date'].max(),
            df['crude_name'].nunique(),
            df['region'].nunique()
        )
    except Exception:
        # Never fail the page due to logging issues
        pass

    # Build standard columns from SQL-provided parts
    df['Year'] = df['year_int'].astype(int).astype(str)
    df['Month'] = df['month_name'].astype(str).str.strip()
    df['Day'] = df['day_num'].astype(int).astype(str)
    df['Region'] = df['region'].fillna(df['crude_country']).astype(str).str.strip()
    df['Country'] = df['country_name'].fillna(df['crude_country']).astype(str).str.strip()
    df['Blend'] = df['crude_name'].astype(str).str.strip()
    df['Price'] = pd.to_numeric(df['avg_price'], errors='coerce')
    # Use quarter from SQL (already computed)
    df['Quarter'] = df['quarter'].astype(str)

    # Filter out invalid rows
    df = df[
        (df['Year'].notna()) &
        (df['Year'] != '') &
        (df['Year'] != 'nan') &
        (df['Month'].notna()) &
        (df['Month'] != '') &
        (df['Month'] != 'nan') &
        (df['Day'].notna()) &
        (df['Day'] != '') &
        (df['Day'] != 'nan') &
        (df['Region'].notna()) &
        (df['Region'] != '') &
        (df['Country'].notna()) &
        (df['Country'] != '') &
        (df['Blend'].notna()) &
        (df['Blend'] != '')
    ].copy()

    # Create column ID for each Region-Country-Blend combination
    df['ColumnID'] = df['Region'] + '_' + df['Country'] + '_' + df['Blend']

    # Pivot the data from long to wide format
    pivot_df = df.pivot_table(
        index=['Year', 'Quarter', 'Month', 'Day'],
        columns='ColumnID',
        values='Price',
        aggfunc='first'  # Use first value if duplicates exist
    ).reset_index()

    # Get unique combinations for column metadata
    unique_combos = df[['Region', 'Country', 'Blend', 'ColumnID']].drop_duplicates()

    # Create metadata for columns
    column_metadata = []
    for _, row in unique_combos.iterrows():
        column_metadata.append({
            'region': str(row['Region']).strip(),
            'country': str(row['Country']).strip(),
            'blend': str(row['Blend']).strip(),
            'column_id': str(row['ColumnID']).strip(),
            'index': len(column_metadata)
        })

    # Log column count for debugging
    try:
        logger.info(
            "[global_prices] Generated %s columns from %s unique region/country/blend combinations",
            len(column_metadata),
            len(unique_combos)
        )
    except Exception:
        pass

    return pivot_df, column_metadata


def create_table_data(df, column_metadata):
    """Create table data structure for Dash DataTable with hierarchical columns."""
    # Define month order for sorting
    month_order = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    
    # Define quarter order for sorting
    quarter_order = {'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4}
    
    # Add sorting columns
    df['MonthOrder'] = df['Month'].map(month_order)
    df['QuarterOrder'] = df['Quarter'].map(quarter_order)
    df['YearInt'] = pd.to_numeric(df['Year'], errors='coerce')
    df['DayInt'] = pd.to_numeric(df['Day'], errors='coerce')
    
    # Sort by Year (descending), Quarter (descending), Month (descending), Day (ascending)
    # Sort descending by year/quarter/month to match reference view (latest first)
    df_sorted = df.sort_values(['YearInt', 'QuarterOrder', 'MonthOrder', 'DayInt'], 
                               ascending=[False, False, False, True])
    
    # Create row data - FIXED: Remove empty strings, use None instead
    table_data = []
    current_year = None
    current_quarter = None
    current_month = None
    
    for _, row in df_sorted.iterrows():
        year = row['Year']
        quarter = row['Quarter']
        month = row['Month']
        day = row['Day']
        
        # Use None for repeated values instead of empty strings
        row_dict = {
            'Year': year if year != current_year else None,
            'Quarter': quarter if (year != current_year or quarter != current_quarter) else None,
            'Month': month if (year != current_year or quarter != current_quarter or month != current_month) else None,
            'Day': day,
            'Year_Quarter_Month_Day': f"{year}_{quarter}_{month}_{day}"
        }
        
        current_year = year
        current_quarter = quarter
        current_month = month
        
        # Add price values
        for meta in column_metadata:
            col_id = meta['column_id']
            value = row.get(col_id, None)
            if pd.notna(value) and value != '':
                row_dict[col_id] = float(value)
            else:
                row_dict[col_id] = None
        
        table_data.append(row_dict)
    
    return table_data


def create_table_columns(column_metadata):
    """Create column definitions with hierarchical structure."""
    # Use 3-level structure to align with data columns (region / country / blend)
    # Left columns (Year/Quarter/Month/Day) with Quarter/Day toggle-only
    columns = [
        {'name': ['', '', 'Year'], 'id': 'Year', 'type': 'text'},
        {'name': ['', '', 'Quarter'], 'id': 'Quarter', 'type': 'text'},
        {'name': ['', '', 'Month'], 'id': 'Month', 'type': 'text'},
        {'name': ['', '', 'Day'], 'id': 'Day', 'type': 'text'},
    ]
    
    # Region priority order matching first image exactly:
    # Latin America → Middle East → North America → Oceania → Other
    # (Africa and Asia come first if present, but may be off-screen)
    region_priority = {
        'Africa': 1,
        'Asia': 2,
        'Europe': 3,
        'FSU': 4,
        'Latin America': 5,
        'Middle East': 6,
        'North America': 7,
        'Oceania': 8,
        'Other': 9,
    }
    
    # Dynamic order: use region priority, then alphabetical within each region
    sorted_meta = sorted(
        column_metadata,
        key=lambda m: (
            region_priority.get(str(m['region']).strip(), 99),  # Use priority, strip whitespace
            str(m['country']).lower().strip(),  # Then by country (alphabetical)
            str(m['blend']).lower().strip(),    # Then by blend (alphabetical)
        ),
    )

    for meta in sorted_meta:
        columns.append({
            'name': [meta['region'], meta['country'], meta['blend']],
            'id': meta['column_id'],
            'type': 'numeric',
            'format': {'specifier': '.2f'}
        })
    
    # Log final column count and region order for debugging
    try:
        regions_in_order = [m['region'] for m in sorted_meta]
        unique_regions = list(dict.fromkeys(regions_in_order))  # Preserve order, remove duplicates
        logger.info(
            "[global_prices] Created %s table columns (4 date columns + %s data columns). Regions in order: %s",
            len(columns),
            len(sorted_meta),
            unique_regions
        )
    except Exception:
        pass
    
    return columns


def create_layout():
    """Create the layout for Global Crude Prices dashboard."""
    # Load data
    try:
        df, column_metadata = load_crude_prices_data()
        table_data = create_table_data(df, column_metadata)
        table_columns = create_table_columns(column_metadata)
    except Exception as e:
        return html.Div([
            html.H3("Error loading data"),
            html.P(str(e))
        ])
    
    return html.Div([
        # Store for selected cells
        dcc.Store(id='global-prices-selection-store', data={'selected_cells': []}),
        
        # Store for year column collapse state (default: expanded - all columns visible)
        dcc.Store(id='global-prices-year-collapse-store', data={'is_collapsed': False}),
        
        # Title
        html.H2(
            "Monthly Crude Spot Prices ($/bbl)",
            style={
                'textAlign': 'center',
                'marginBottom': '10px',
                'marginTop': '0px',
                'fontSize': '20px',
                'fontWeight': 'bold',
                'color': '#fe5000',
                'fontFamily': 'Arial, sans-serif'
            }
        ),
        
        # Table
        html.Div([
            dash_table.DataTable(
                id='global-prices-table',
                data=table_data,
                columns=table_columns,
                merge_duplicate_headers=True,
                fixed_rows={'headers': True},
                # Note: Using CSS sticky positioning instead of fixed_columns to avoid empty space issues
                style_table={
                    'tableLayout': 'auto',  # Changed to 'auto' for dynamic column widths
                    'overflowX': 'auto',
                    'overflowY': 'auto',
                    'border': '1px solid #dee2e6',
                    'fontFamily': 'Arial, sans-serif',
                    'fontSize': '12px',
                    'height': '800px',
                    'maxHeight': '800px',
                    'width': '100%',
                    'maxWidth': '100%',  # Prevent table from exceeding container
                    'marginTop': '0px'
                },
                style_cell={
                    'textAlign': 'center',
                    'padding': '6px 10px',
                    'border': '1px solid #e6e6e6',
                    'backgroundColor': 'white',
                    'color': '#1b365d',
                    'fontFamily': 'Arial, sans-serif',
                    'fontSize': '12px',
                    'minWidth': '80px',
                    'whiteSpace': 'normal',
                    'height': 'auto'
                },
                style_header={
                    'backgroundColor': '#f8f9fa',
                    'fontWeight': 'bold',
                    'textAlign': 'center',
                    'border': '1px solid #dee2e6',
                    'padding': '8px 10px',
                    'fontFamily': 'Arial, sans-serif',
                    'fontSize': '12px',
                    'color': '#1b365d',
                    'position': 'sticky',
                    'top': 0,
                    'zIndex': 2
                },
                style_data={
                    'border': '1px solid #e6e6e6'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#f8f9fa'
                    },
                    {
                        # Remove the font weight conditions for empty cells since we use None now
                        'if': {'column_id': 'Year', 'filter_query': '{Year} != ""'},
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {'column_id': 'Quarter', 'filter_query': '{Quarter} != ""'},
                        'fontWeight': 'bold'
                    }
                ],
                style_cell_conditional=[
                    {
                        'if': {'column_id': 'Year'},
                        'fontWeight': 'bold',
                        'backgroundColor': '#f8f9fa',
                        'minWidth': '80px',
                        'textAlign': 'center'
                    },
                    {
                        'if': {'column_id': 'Quarter'},
                        'fontWeight': 'bold',
                        'backgroundColor': '#f8f9fa',
                        'minWidth': '60px',
                        'textAlign': 'center'
                    },
                    {
                        'if': {'column_id': 'Month'},
                        'fontWeight': 'normal',
                        'minWidth': '100px',
                        'textAlign': 'center'
                    },
                    {
                        'if': {'column_id': 'Day'},
                        'fontWeight': 'normal',
                        'minWidth': '50px',
                        'textAlign': 'center'
                    }
                ],
                page_action='none',
                filter_action='none',
                sort_action='none',
                editable=False,
                row_selectable=False,
                cell_selectable=True,
                selected_cells=[]
            )
        ], style={
            'margin': '0 auto', 
            'width': '100%', 
            'maxWidth': '100%',
            'overflowX': 'auto', 
            'overflowY': 'auto',
            'boxSizing': 'border-box',
            'position': 'relative'
        }),
        
        # Hidden div for clientside callback anchor
        html.Div(id='global-prices-enhancer-anchor', style={'display': 'none'}),
        
        # Clientside script for table enhancements
        html.Script(
            id='global-prices-clientside-script',
            children=''
        )
    ], style={
        'padding': '10px 20px 0 20px', 
        'backgroundColor': '#ffffff', 
        'overflowX': 'hidden', 
        'overflowY': 'auto',
        'width': '100%',
        'maxWidth': '100%',
        'boxSizing': 'border-box'
    })


def register_callbacks(dash_app, server):
    """Register all callbacks for Global Crude Prices dashboard."""
    
    # Clientside callback for table click handling and tooltip
    dash_app.clientside_callback(
        """
        function(_id) {
            try {
                const styleId = 'global-prices-table-css';
                if (!document.getElementById(styleId)) {
                    const style = document.createElement('style');
                    style.id = styleId;
                    style.type = 'text/css';
                    style.innerHTML = `
#global-prices-table {
    max-width: 100%;
    overflow-x: auto;
    overflow-y: auto;
}
#global-prices-table .dash-spreadsheet-container {
    cursor: pointer;
    table-layout: auto;
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
    overflow-x: auto;
    overflow-y: auto;
}
#global-prices-table .dash-table-container {
    max-width: 100%;
    overflow-x: auto;
    overflow-y: auto;
    width: 100%;
}
#global-prices-table .dash-spreadsheet-container table {
    border-collapse: separate;
    border-spacing: 0;
    width: auto;
    min-width: 100%;
}
#global-prices-table .dash-spreadsheet-container .row {
    width: auto;
}
#global-prices-table .dash-spreadsheet-container .row-1 {
    width: auto;
}
/* Ensure data columns are visible and properly sized */
#global-prices-table .dash-spreadsheet-container td:not([data-dash-column="Year"]):not([data-dash-column="Quarter"]):not([data-dash-column="Month"]):not([data-dash-column="Day"]),
#global-prices-table .dash-spreadsheet-container th:not([data-dash-column="Year"]):not([data-dash-column="Quarter"]):not([data-dash-column="Month"]):not([data-dash-column="Day"]) {
    display: table-cell !important;
    min-width: 80px;
}
#global-prices-table .dash-spreadsheet-container td {
    transition: opacity 0.2s ease, background-color 0.2s ease;
    cursor: pointer;
}
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Year"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Day"] {
    cursor: pointer;
}
/* Hide empty header cells for Year/Quarter/Month/Day (they use 3-level structure with empty upper levels) */
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Year"]:empty,
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Quarter"]:empty,
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Month"]:empty,
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Day"]:empty {
    display: none !important;
}
/* Fixed columns: Year, Quarter, Month, Day - position sticky */
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Year"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Year"],
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Day"] {
    position: sticky !important;
    z-index: 10 !important;
}
/* Fixed column headers - higher z-index */
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Year"],
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Day"] {
    z-index: 11 !important;
    background-color: #f8f9fa !important;
}
/* Fixed column data cells - inherit background from row */
#global-prices-table .dash-spreadsheet-container tr:nth-child(odd) td[data-dash-column="Year"],
#global-prices-table .dash-spreadsheet-container tr:nth-child(odd) td[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container tr:nth-child(odd) td[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container tr:nth-child(odd) td[data-dash-column="Day"] {
    background-color: #f8f9fa !important;
}
#global-prices-table .dash-spreadsheet-container tr:nth-child(even) td[data-dash-column="Year"],
#global-prices-table .dash-spreadsheet-container tr:nth-child(even) td[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container tr:nth-child(even) td[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container tr:nth-child(even) td[data-dash-column="Day"] {
    background-color: white !important;
}
/* Year column - left: 0 (always first) */
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Year"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Year"] {
    left: 0 !important;
}
/* Quarter column - left: 80px (after Year, only when visible) */
#global-prices-table .dash-spreadsheet-container.year-expanded th[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container.year-expanded td[data-dash-column="Quarter"] {
    left: 80px !important;
}
/* Month column - left position depends on Quarter visibility */
/* Default: Month is second column (after Year) */
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Month"] {
    left: 80px !important;
}
/* When Quarter is visible, Month is third column */
#global-prices-table .dash-spreadsheet-container.year-expanded th[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container.year-expanded td[data-dash-column="Month"] {
    left: 140px !important;
}
/* Day column - left position depends on Quarter and Month visibility */
/* Default: Day is hidden, but if shown without Quarter, it's third column */
#global-prices-table .dash-spreadsheet-container.month-expanded:not(.year-expanded) th[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container.month-expanded:not(.year-expanded) td[data-dash-column="Day"] {
    left: 180px !important;
}
/* When Quarter is visible, Day is fourth column */
#global-prices-table .dash-spreadsheet-container.year-expanded.month-expanded:not(.quarter-collapsed) th[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container.year-expanded.month-expanded:not(.quarter-collapsed) td[data-dash-column="Day"] {
    left: 240px !important;
}
/* Default: Quarter and Day columns hidden - ensure Year and Month are always visible */
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Year"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Year"],
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Month"] {
    display: table-cell !important;
}
/* Default: Quarter and Day columns hidden - ensure they don't take up space */
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container table th[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container table th[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container table td[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container table td[data-dash-column="Day"] {
    display: none !important;
    width: 0 !important;
    min-width: 0 !important;
    max-width: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
}
/* Show Quarter when year is expanded */
#global-prices-table .dash-spreadsheet-container.year-expanded th[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container.year-expanded td[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container.year-expanded table th[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container.year-expanded table td[data-dash-column="Quarter"] {
    display: table-cell !important;
}
/* Hide Month and Day when quarter is collapsed (only when Quarter is visible) */
#global-prices-table .dash-spreadsheet-container.year-expanded.quarter-collapsed th[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container.year-expanded.quarter-collapsed th[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container.year-expanded.quarter-collapsed td[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container.year-expanded.quarter-collapsed td[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container.year-expanded.quarter-collapsed table th[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container.year-expanded.quarter-collapsed table th[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container.year-expanded.quarter-collapsed table td[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container.year-expanded.quarter-collapsed table td[data-dash-column="Day"] {
    display: none !important;
}
/* Show Day when month is expanded (hide if quarter is collapsed) */
#global-prices-table .dash-spreadsheet-container.month-expanded:not(.quarter-collapsed) th[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container.month-expanded:not(.quarter-collapsed) td[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container.month-expanded:not(.quarter-collapsed) table th[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container.month-expanded:not(.quarter-collapsed) table td[data-dash-column="Day"] {
    display: table-cell !important;
}
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Year"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Month"] {
    position: relative;
    cursor: pointer;
    white-space: nowrap;
}
/* Header toggle buttons - Show on hover only */
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Year"] .year-header-toggle,
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Month"] .month-header-toggle,
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Quarter"] .quarter-header-toggle {
    display: none;
    margin-left: 6px;
    width: 16px;
    height: 16px;
    line-height: 14px;
    text-align: center;
    font-size: 12px;
    font-weight: normal;
    color: #505050;
    border: 1px solid #d0d0d0;
    border-radius: 2px;
    background-color: #ffffff;
    user-select: none;
    cursor: pointer;
    vertical-align: middle;
    flex-shrink: 0;
    box-sizing: border-box;
    transition: all 0.15s ease;
    font-family: Arial, sans-serif;
}
/* Show toggle buttons on header hover */
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Year"]:hover .year-header-toggle,
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Month"]:hover .month-header-toggle,
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Quarter"]:hover .quarter-header-toggle {
    display: inline-block;
}
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Year"] .year-header-toggle:hover,
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Month"] .month-header-toggle:hover,
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Quarter"] .quarter-header-toggle:hover {
    color: #333333;
    border-color: #a0a0a0;
    background-color: #f0f0f0;
}
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Year"],
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Quarter"] {
    position: relative;
    white-space: nowrap;
}
#global-prices-table .dash-spreadsheet-container.selection-active td:not(.cell-selected):not([data-dash-column="Year"]):not([data-dash-column="Quarter"]):not([data-dash-column="Month"]):not([data-dash-column="Day"]) {
    opacity: 0.3 !important;
}
#global-prices-table .dash-spreadsheet-container td.cell-selected {
    background-color: #b3d9ff !important;
    border: 2px solid #0075A8 !important;
    font-weight: 600;
    color: #1f2d3d !important;
    opacity: 1 !important;
}
#global-prices-table .dash-spreadsheet-container th {
    cursor: pointer;
    transition: background-color 0.2s ease;
}
#global-prices-table .dash-spreadsheet-container th.column-selected {
    background-color: #0075A8 !important;
    color: white !important;
    font-weight: bold;
}
#global-prices-table .dash-spreadsheet-container.column-selection-active td:not([data-dash-column="Year"]):not([data-dash-column="Quarter"]):not([data-dash-column="Month"]):not([data-dash-column="Day"]):not(.column-cell-selected) {
    opacity: 0.3 !important;
}
#global-prices-table .dash-spreadsheet-container td.column-cell-selected {
    background-color: #b3d9ff !important;
    border: 2px solid #0075A8 !important;
    font-weight: 600;
    color: #1f2d3d !important;
    opacity: 1 !important;
}
                    `;
                    document.head.appendChild(style);
                }

                function getCellValue(cell) {
                    const text = cell.textContent || cell.innerText || '';
                    return text.trim();
                }

                function getColumnInfo(cell) {
                    const columnId = cell.getAttribute('data-dash-column');
                    const header = document.querySelector(`th[data-dash-column="${columnId}"]`);
                    if (!header) return null;
                    
                    const headerText = header.textContent || '';
                    const parts = headerText.split('\\n').filter(p => p.trim());
                    
                    return {
                        columnId: columnId,
                        region: parts[0] || '',
                        country: parts[1] || '',
                        blend: parts[2] || parts[1] || parts[0] || ''
                    };
                }

                function getRowInfo(cell) {
                    const rowIndex = cell.getAttribute('data-dash-row');
                    const row = document.querySelector(`tr[data-dash-row="${rowIndex}"]`);
                    if (!row) return null;
                    
                    const yearCell = row.querySelector('td[data-dash-column="Year"]');
                    const quarterCell = row.querySelector('td[data-dash-column="Quarter"]');
                    const monthCell = row.querySelector('td[data-dash-column="Month"]');
                    const dayCell = row.querySelector('td[data-dash-column="Day"]');
                    
                    return {
                        year: yearCell ? (yearCell.textContent || '').trim() : '',
                        quarter: quarterCell ? (quarterCell.textContent || '').trim() : '',
                        month: monthCell ? (monthCell.textContent || '').trim() : '',
                        day: dayCell ? (dayCell.textContent || '').trim() : ''
                    };
                }

                function updateSelectionState(spreadsheet, selectedCells) {
                    if (selectedCells.length > 0) {
                        spreadsheet.classList.add('selection-active');
                    } else {
                        spreadsheet.classList.remove('selection-active');
                    }
                }
                
                function clearAllColumnSelections(spreadsheet) {
                    // Clear all column headers
                    const allHeaders = spreadsheet.querySelectorAll('th.column-selected');
                    allHeaders.forEach(header => header.classList.remove('column-selected'));
                    
                    // Clear all column cells
                    const allColumnCells = spreadsheet.querySelectorAll('td.column-cell-selected');
                    allColumnCells.forEach(cell => cell.classList.remove('column-cell-selected'));
                    
                    // Remove column selection active class
                    spreadsheet.classList.remove('column-selection-active');
                }

                function enhanceTable() {
                    const tableEl = document.getElementById('global-prices-table');
                    if (!tableEl) return;
                    
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    if (!spreadsheet || spreadsheet.dataset.enhanced === 'true') return;
                    
                    spreadsheet.dataset.enhanced = 'true';
                    let selectedCells = [];
                    let selectedColumnId = null;
                    let isYearExpanded = false; // Default: hide Quarter
                    let isMonthExpanded = false; // Default: hide Day
                    let isQuarterCollapsed = false; // Default: Month and Day visible when Quarter is shown
                    
                    // Ensure default state: Year and Month visible, Quarter and Day hidden
                    spreadsheet.classList.remove('year-expanded', 'month-expanded', 'quarter-collapsed');
                    
                    // Function to update sticky column positions
                    function updateStickyPositions() {
                        const yearCells = spreadsheet.querySelectorAll('th[data-dash-column="Year"], td[data-dash-column="Year"]');
                        const quarterCells = spreadsheet.querySelectorAll('th[data-dash-column="Quarter"], td[data-dash-column="Quarter"]');
                        const monthCells = spreadsheet.querySelectorAll('th[data-dash-column="Month"], td[data-dash-column="Month"]');
                        const dayCells = spreadsheet.querySelectorAll('th[data-dash-column="Day"], td[data-dash-column="Day"]');
                        
                        // Get actual column widths
                        let yearWidth = 80;
                        let quarterWidth = 60;
                        let monthWidth = 100;
                        let dayWidth = 50;
                        
                        if (yearCells.length > 0) {
                            const firstYearCell = yearCells[0];
                            yearWidth = firstYearCell.offsetWidth || 80;
                        }
                        if (quarterCells.length > 0 && isYearExpanded) {
                            const firstQuarterCell = quarterCells[0];
                            quarterWidth = firstQuarterCell.offsetWidth || 60;
                        }
                        if (monthCells.length > 0) {
                            const firstMonthCell = monthCells[0];
                            monthWidth = firstMonthCell.offsetWidth || 100;
                        }
                        if (dayCells.length > 0 && isMonthExpanded && !isQuarterCollapsed) {
                            const firstDayCell = dayCells[0];
                            dayWidth = firstDayCell.offsetWidth || 50;
                        }
                        
                        // Year is always at left: 0
                        yearCells.forEach(cell => {
                            cell.style.left = '0px';
                            cell.style.position = 'sticky';
                            cell.style.zIndex = cell.tagName === 'TH' ? '11' : '10';
                        });
                        
                        // Quarter position (only when visible)
                        if (isYearExpanded) {
                            quarterCells.forEach(cell => {
                                cell.style.left = yearWidth + 'px';
                                cell.style.position = 'sticky';
                                cell.style.zIndex = cell.tagName === 'TH' ? '11' : '10';
                            });
                        }
                        
                        // Month position depends on Quarter visibility
                        if (isYearExpanded) {
                            // Month is after Quarter
                            monthCells.forEach(cell => {
                                cell.style.left = (yearWidth + quarterWidth) + 'px';
                                cell.style.position = 'sticky';
                                cell.style.zIndex = cell.tagName === 'TH' ? '11' : '10';
                            });
                        } else {
                            // Month is after Year
                            monthCells.forEach(cell => {
                                cell.style.left = yearWidth + 'px';
                                cell.style.position = 'sticky';
                                cell.style.zIndex = cell.tagName === 'TH' ? '11' : '10';
                            });
                        }
                        
                        // Day position depends on Quarter and Month visibility
                        if (isMonthExpanded && !isQuarterCollapsed) {
                            if (isYearExpanded) {
                                // Day is after Year + Quarter + Month
                                dayCells.forEach(cell => {
                                    cell.style.left = (yearWidth + quarterWidth + monthWidth) + 'px';
                                    cell.style.position = 'sticky';
                                    cell.style.zIndex = cell.tagName === 'TH' ? '11' : '10';
                                });
                            } else {
                                // Day is after Year + Month
                                dayCells.forEach(cell => {
                                    cell.style.left = (yearWidth + monthWidth) + 'px';
                                    cell.style.position = 'sticky';
                                    cell.style.zIndex = cell.tagName === 'TH' ? '11' : '10';
                                });
                            }
                        }
                    }
                    
                    // Helper function to get cell text without icons
                    function getCellTextWithoutIcons(cell, iconClass) {
                        let text = '';
                        const childNodes = Array.from(cell.childNodes);
                        childNodes.forEach(node => {
                            if (node.classList && node.classList.contains(iconClass)) return;
                            if (node.nodeType === Node.TEXT_NODE) {
                                text += node.textContent;
                            } else if (node.nodeType === Node.ELEMENT_NODE && (!node.classList || !node.classList.contains(iconClass))) {
                                text += node.textContent;
                            }
                        });
                        return text.trim();
                    }
                    
                    // Helper function to add toggle icon to cell
                    function addToggleIcon(cell, iconClass, isExpanded, onClickHandler) {
                        const existingIcon = cell.querySelector('.' + iconClass);
                        if (existingIcon) {
                            existingIcon.textContent = isExpanded ? '−' : '+';
                            existingIcon.setAttribute('aria-label', isExpanded ? 'Collapse' : 'Expand');
                            return existingIcon;
                        }
                        
                        const icon = document.createElement('span');
                        icon.className = iconClass;
                        icon.textContent = isExpanded ? '−' : '+';
                        icon.setAttribute('aria-label', isExpanded ? 'Collapse' : 'Expand');
                        
                        // Insert icon after text content
                        const childNodes = Array.from(cell.childNodes);
                        let inserted = false;
                        for (let i = 0; i < childNodes.length; i++) {
                            const node = childNodes[i];
                            if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
                                if (node.nextSibling) {
                                    cell.insertBefore(icon, node.nextSibling);
                                } else {
                                    cell.appendChild(icon);
                                }
                                inserted = true;
                                break;
                            }
                        }
                        if (!inserted) {
                            cell.appendChild(icon);
                        }
                        
                        icon.addEventListener('click', function(e) {
                            e.stopPropagation();
                            onClickHandler();
                        });
                        
                        return icon;
                    }
                    
                    // Initialize Year header toggle button
                    function initializeYearHeaderToggle() {
                        // Find the header cell that contains "Year" text (the visible one in hierarchical headers)
                        const allYearHeaders = Array.from(spreadsheet.querySelectorAll('th[data-dash-column="Year"]'));
                        if (!allYearHeaders.length) return;
                        
                        // Prefer the lowest header row that actually shows the "Year" label
                        let yearHeader = allYearHeaders.slice().reverse().find(header => header.textContent.trim().includes('Year'));
                        if (!yearHeader) {
                            yearHeader = allYearHeaders[allYearHeaders.length - 1]; // Fallback to the last one (usually the visible row)
                        }
                        
                        // Remove toggle buttons from any other Year headers so the icon only appears once
                        allYearHeaders.forEach(header => {
                            if (header !== yearHeader) {
                                const extraToggle = header.querySelector('.year-header-toggle');
                                if (extraToggle) extraToggle.remove();
                            }
                        });
                        
                        // Remove any existing toggle button on the chosen header
                        const existingToggle = yearHeader.querySelector('.year-header-toggle');
                        if (existingToggle) {
                            existingToggle.remove();
                        }
                        
                        // Create toggle button
                        const toggleBtn = document.createElement('span');
                        toggleBtn.className = 'year-header-toggle';
                        toggleBtn.textContent = isYearExpanded ? '−' : '+';
                        toggleBtn.setAttribute('aria-label', isYearExpanded ? 'Collapse Quarter' : 'Expand Quarter');
                        
                        // Preserve existing content and append button
                        // Check if header has text nodes or other content
                        const hasTextContent = yearHeader.textContent.trim() && 
                                             !yearHeader.querySelector('.year-header-toggle');
                        if (hasTextContent) {
                            // Append button after existing content
                            yearHeader.appendChild(toggleBtn);
                        } else {
                            // If no content, add "Year" text first
                            yearHeader.textContent = 'Year';
                            yearHeader.appendChild(toggleBtn);
                        }
                        
                        // Add click handler
                        toggleBtn.addEventListener('click', function(e) {
                            e.stopPropagation();
                            toggleYearExpand();
                        });
                    }
                    
                    // Initialize Month header toggle button
                    function initializeMonthHeaderToggle() {
                        // Find the header cell that contains "Month" text (the visible one in hierarchical headers)
                        const allMonthHeaders = spreadsheet.querySelectorAll('th[data-dash-column="Month"]');
                        let monthHeader = null;
                        for (let header of allMonthHeaders) {
                            if (header.textContent.trim().includes('Month') || header.textContent.trim() === '') {
                                monthHeader = header;
                                break;
                            }
                        }
                        // Fallback to last one if none found with text
                        if (!monthHeader && allMonthHeaders.length > 0) {
                            monthHeader = allMonthHeaders[allMonthHeaders.length - 1]; // Get the last one (usually the visible row)
                        }
                        if (!monthHeader) return;
                        
                        // Remove any existing toggle button
                        const existingToggle = monthHeader.querySelector('.month-header-toggle');
                        if (existingToggle) {
                            existingToggle.remove();
                        }
                        
                        // Create toggle button
                        const toggleBtn = document.createElement('span');
                        toggleBtn.className = 'month-header-toggle';
                        toggleBtn.textContent = isMonthExpanded ? '−' : '+';
                        toggleBtn.setAttribute('aria-label', isMonthExpanded ? 'Collapse Day' : 'Expand Day');
                        
                        // Preserve existing content and append button
                        // Check if header has text nodes or other content
                        const hasTextContent = monthHeader.textContent.trim() && 
                                             !monthHeader.querySelector('.month-header-toggle');
                        if (hasTextContent) {
                            // Append button after existing content
                            monthHeader.appendChild(toggleBtn);
                        } else {
                            // If no content, add "Month" text first
                            monthHeader.textContent = 'Month';
                            monthHeader.appendChild(toggleBtn);
                        }
                        
                        // Add click handler
                        toggleBtn.addEventListener('click', function(e) {
                            e.stopPropagation();
                            toggleMonthExpand();
                        });
                    }
                    
                    // Initialize Quarter header toggle button (only when Quarter is visible)
                    function initializeQuarterHeaderToggle() {
                        // Find the header cell that contains "Quarter" text (the visible one in hierarchical headers)
                        const allQuarterHeaders = spreadsheet.querySelectorAll('th[data-dash-column="Quarter"]');
                        let quarterHeader = null;
                        for (let header of allQuarterHeaders) {
                            if (header.textContent.trim().includes('Quarter') || header.textContent.trim() === '') {
                                quarterHeader = header;
                                break;
                            }
                        }
                        // Fallback to last one if none found with text
                        if (!quarterHeader && allQuarterHeaders.length > 0) {
                            quarterHeader = allQuarterHeaders[allQuarterHeaders.length - 1]; // Get the last one (usually the visible row)
                        }
                        if (!quarterHeader) return;
                        
                        // Remove any existing toggle button
                        const existingToggle = quarterHeader.querySelector('.quarter-header-toggle');
                        if (existingToggle) {
                            existingToggle.remove();
                        }
                        
                        // Create toggle button
                        const toggleBtn = document.createElement('span');
                        toggleBtn.className = 'quarter-header-toggle';
                        toggleBtn.textContent = isQuarterCollapsed ? '+' : '−';
                        toggleBtn.setAttribute('aria-label', isQuarterCollapsed ? 'Show Month & Day' : 'Hide Month & Day');
                        
                        // Preserve existing content and append button
                        const hasTextContent = quarterHeader.textContent.trim() && 
                                             !quarterHeader.querySelector('.quarter-header-toggle');
                        if (hasTextContent) {
                            quarterHeader.appendChild(toggleBtn);
                        } else {
                            quarterHeader.textContent = 'Quarter';
                            quarterHeader.appendChild(toggleBtn);
                        }
                        
                        // Add click handler
                        toggleBtn.addEventListener('click', function(e) {
                            e.stopPropagation();
                            toggleQuarterCollapse();
                        });
                    }
                    
                    // Toggle Year expand (shows/hides Quarter)
                    function toggleYearExpand() {
                        isYearExpanded = !isYearExpanded;
                        
                        // Update header toggle button
                        const yearHeaderToggle = spreadsheet.querySelector('th[data-dash-column="Year"] .year-header-toggle');
                        if (yearHeaderToggle) {
                            yearHeaderToggle.textContent = isYearExpanded ? '−' : '+';
                            yearHeaderToggle.setAttribute('aria-label', isYearExpanded ? 'Collapse Quarter' : 'Expand Quarter');
                        }
                        
                        // Toggle Quarter column visibility
                        const quarterCells = spreadsheet.querySelectorAll('th[data-dash-column="Quarter"], td[data-dash-column="Quarter"]');
                        if (isYearExpanded) {
                            spreadsheet.classList.add('year-expanded');
                            // Show Quarter columns
                            quarterCells.forEach(cell => {
                                cell.style.display = 'table-cell';
                            });
                            // Initialize Quarter header toggle when Quarter becomes visible
                            setTimeout(function() {
                                initializeQuarterHeaderToggle();
                            }, 100);
                        } else {
                            spreadsheet.classList.remove('year-expanded');
                            // Hide Quarter columns
                            quarterCells.forEach(cell => {
                                cell.style.display = 'none';
                            });
                            // Reset quarter collapse state when Quarter is hidden
                            isQuarterCollapsed = false;
                            spreadsheet.classList.remove('quarter-collapsed');
                        }
                        
                        // Update sticky positions after toggling
                        setTimeout(function() {
                            updateStickyPositions();
                        }, 50);
                        
                        // Clear selections
                        clearAllColumnSelections(spreadsheet);
                        selectedColumnId = null;
                        selectedCells.forEach(c => c.classList.remove('cell-selected'));
                        selectedCells = [];
                        updateSelectionState(spreadsheet, selectedCells);
                    }
                    
                    // Toggle Quarter collapse (shows/hides Month and Day)
                    function toggleQuarterCollapse() {
                        isQuarterCollapsed = !isQuarterCollapsed;
                        
                        // Update header toggle button
                        const quarterHeaderToggle = spreadsheet.querySelector('th[data-dash-column="Quarter"] .quarter-header-toggle');
                        if (quarterHeaderToggle) {
                            quarterHeaderToggle.textContent = isQuarterCollapsed ? '+' : '−';
                            quarterHeaderToggle.setAttribute('aria-label', isQuarterCollapsed ? 'Show Month & Day' : 'Hide Month & Day');
                        }
                        
                        // Toggle Month and Day column visibility
                        const monthCells = spreadsheet.querySelectorAll('th[data-dash-column="Month"], td[data-dash-column="Month"]');
                        const dayCells = spreadsheet.querySelectorAll('th[data-dash-column="Day"], td[data-dash-column="Day"]');
                        if (isQuarterCollapsed) {
                            spreadsheet.classList.add('quarter-collapsed');
                            // Hide Month and Day columns
                            monthCells.forEach(cell => {
                                cell.style.display = 'none';
                            });
                            dayCells.forEach(cell => {
                                cell.style.display = 'none';
                            });
                            // Reset month expanded state since Day is hidden
                            isMonthExpanded = false;
                            spreadsheet.classList.remove('month-expanded');
                            const monthHeaderToggle = spreadsheet.querySelector('th[data-dash-column="Month"] .month-header-toggle');
                            if (monthHeaderToggle) {
                                monthHeaderToggle.textContent = '+';
                                monthHeaderToggle.setAttribute('aria-label', 'Expand Day');
                            }
                        } else {
                            spreadsheet.classList.remove('quarter-collapsed');
                            // Show Month columns
                            monthCells.forEach(cell => {
                                cell.style.display = 'table-cell';
                            });
                            // Show Day columns only if month is expanded
                            if (isMonthExpanded) {
                                dayCells.forEach(cell => {
                                    cell.style.display = 'table-cell';
                                });
                            } else {
                                dayCells.forEach(cell => {
                                    cell.style.display = 'none';
                                });
                            }
                        }
                        
                        // Update sticky positions after toggling
                        setTimeout(function() {
                            updateStickyPositions();
                        }, 50);
                        
                        // Clear selections
                        clearAllColumnSelections(spreadsheet);
                        selectedColumnId = null;
                        selectedCells.forEach(c => c.classList.remove('cell-selected'));
                        selectedCells = [];
                        updateSelectionState(spreadsheet, selectedCells);
                    }
                    
                    // Toggle Month expand (shows/hides Day)
                    function toggleMonthExpand() {
                        isMonthExpanded = !isMonthExpanded;
                        
                        // Update header toggle button
                        const monthHeaderToggle = spreadsheet.querySelector('th[data-dash-column="Month"] .month-header-toggle');
                        if (monthHeaderToggle) {
                            monthHeaderToggle.textContent = isMonthExpanded ? '−' : '+';
                            monthHeaderToggle.setAttribute('aria-label', isMonthExpanded ? 'Collapse Day' : 'Expand Day');
                        }
                        
                        // Toggle Day column visibility (only if Quarter is not collapsed)
                        const dayCells = spreadsheet.querySelectorAll('th[data-dash-column="Day"], td[data-dash-column="Day"]');
                        if (isMonthExpanded && !isQuarterCollapsed) {
                            spreadsheet.classList.add('month-expanded');
                            // Show Day columns
                            dayCells.forEach(cell => {
                                cell.style.display = 'table-cell';
                            });
                        } else {
                            spreadsheet.classList.remove('month-expanded');
                            // Hide Day columns
                            dayCells.forEach(cell => {
                                cell.style.display = 'none';
                            });
                        }
                        
                        // Update sticky positions after toggling
                        setTimeout(function() {
                            updateStickyPositions();
                        }, 50);
                        
                        // Clear selections
                        clearAllColumnSelections(spreadsheet);
                        selectedColumnId = null;
                        selectedCells.forEach(c => c.classList.remove('cell-selected'));
                        selectedCells = [];
                        updateSelectionState(spreadsheet, selectedCells);
                    }
                    
                    // Initialize on load - ensure default state
                    // Force hide Quarter and Day columns initially
                    const quarterCells = spreadsheet.querySelectorAll('th[data-dash-column="Quarter"], td[data-dash-column="Quarter"]');
                    quarterCells.forEach(cell => {
                        cell.style.display = 'none';
                    });
                    const dayCells = spreadsheet.querySelectorAll('th[data-dash-column="Day"], td[data-dash-column="Day"]');
                    dayCells.forEach(cell => {
                        cell.style.display = 'none';
                    });
                    
                    // Ensure Year and Month are visible
                    const yearCells = spreadsheet.querySelectorAll('th[data-dash-column="Year"], td[data-dash-column="Year"]');
                    yearCells.forEach(cell => {
                        cell.style.display = 'table-cell';
                    });
                    const monthCells = spreadsheet.querySelectorAll('th[data-dash-column="Month"], td[data-dash-column="Month"]');
                    monthCells.forEach(cell => {
                        cell.style.display = 'table-cell';
                    });
                    
                    initializeYearHeaderToggle();
                    initializeMonthHeaderToggle();
                    if (isYearExpanded) {
                        initializeQuarterHeaderToggle();
                    }
                    
                    // Function to ensure table renders correctly with all columns visible
                    function ensureTableLayout() {
                        const table = spreadsheet.querySelector('table');
                        if (table) {
                            // Ensure table has auto width to show all columns
                            table.style.width = 'auto';
                            table.style.minWidth = '100%';
                            
                            // Ensure all data columns are visible
                            const allCells = spreadsheet.querySelectorAll('td, th');
                            allCells.forEach(cell => {
                                const colId = cell.getAttribute('data-dash-column');
                                if (colId && colId !== 'Year' && colId !== 'Quarter' && colId !== 'Month' && colId !== 'Day') {
                                    // This is a data column - ensure it's visible
                                    if (cell.style.display === 'none') {
                                        cell.style.display = '';
                                    }
                                }
                            });
                            
                            // Force a reflow to ensure layout updates
                            void table.offsetWidth;
                        }
                    }
                    
                    // Initialize sticky positions after a short delay to ensure DOM is ready
                    setTimeout(function() {
                        ensureTableLayout();
                        updateStickyPositions();
                    }, 100);
                    
                    // Also ensure layout after any column visibility changes
                    setTimeout(function() {
                        ensureTableLayout();
                    }, 300);
                    
                    // Clear selection on outside click
                    document.addEventListener('click', function(event) {
                        if (!spreadsheet.contains(event.target)) {
                            selectedCells.forEach(cell => {
                                cell.classList.remove('cell-selected');
                            });
                            selectedCells = [];
                            updateSelectionState(spreadsheet, selectedCells);
                            
                            // Clear column selection
                            clearAllColumnSelections(spreadsheet);
                            selectedColumnId = null;
                        }
                    });
                    
                    // Handle column header clicks
                    spreadsheet.addEventListener('click', function(event) {
                        const header = event.target.closest('th[data-dash-column]');
                        if (header) {
                            event.stopPropagation();
                            const columnId = header.getAttribute('data-dash-column');
                            
                            // Handle Year header toggle
                            if (columnId === 'Year') {
                                // Check if clicking on toggle button or header
                                const toggleBtn = event.target.closest('.year-header-toggle');
                                if (toggleBtn || event.target === header || header.contains(event.target)) {
                                    toggleYearExpand();
                                    return;
                                }
                            }
                            
                            // Handle Month header toggle
                            if (columnId === 'Month') {
                                // Check if clicking on toggle button or header
                                const toggleBtn = event.target.closest('.month-header-toggle');
                                if (toggleBtn || event.target === header || header.contains(event.target)) {
                                    toggleMonthExpand();
                                    return;
                                }
                            }
                            
                            // Handle Quarter header toggle
                            if (columnId === 'Quarter') {
                                // Check if clicking on toggle button or header
                                const toggleBtn = event.target.closest('.quarter-header-toggle');
                                if (toggleBtn || event.target === header || header.contains(event.target)) {
                                    toggleQuarterCollapse();
                                    return;
                                }
                            }
                            
                            // Clear selection if clicking Day header
                            if (columnId === 'Day') {
                                clearAllColumnSelections(spreadsheet);
                                selectedColumnId = null;
                                selectedCells.forEach(c => c.classList.remove('cell-selected'));
                                selectedCells = [];
                                updateSelectionState(spreadsheet, selectedCells);
                                return;
                            }
                            
                            // Check if this column is already selected
                            if (selectedColumnId === columnId) {
                                // Deselect column
                                clearAllColumnSelections(spreadsheet);
                                selectedColumnId = null;
                                
                                // Clear cell selection too
                                selectedCells.forEach(c => c.classList.remove('cell-selected'));
                                selectedCells = [];
                                updateSelectionState(spreadsheet, selectedCells);
                            } else {
                                // Select new column - clear ALL previous selections first
                                clearAllColumnSelections(spreadsheet);
                                
                                // Clear cell selection
                                selectedCells.forEach(c => c.classList.remove('cell-selected'));
                                selectedCells = [];
                                updateSelectionState(spreadsheet, selectedCells);
                                
                                // Now select new column
                                selectedColumnId = columnId;
                                header.classList.add('column-selected');
                                const columnCells = spreadsheet.querySelectorAll(`td[data-dash-column="${columnId}"]`);
                                columnCells.forEach(cell => {
                                    const cellValue = getCellValue(cell);
                                    if (cellValue && cellValue !== '' && cellValue !== 'NaN' && !isNaN(parseFloat(cellValue))) {
                                        cell.classList.add('column-cell-selected');
                                    }
                                });
                                spreadsheet.classList.add('column-selection-active');
                            }
                            return;
                        }
                    });
                    
                    // Handle cell clicks
                    spreadsheet.addEventListener('click', function(event) {
                        event.stopPropagation();
                        const cell = event.target.closest('td[data-dash-row][data-dash-column]');
                        if (!cell) return;
                        
                        // Clear column selection if clicking on a cell
                        clearAllColumnSelections(spreadsheet);
                        selectedColumnId = null;
                        
                        const columnId = cell.getAttribute('data-dash-column');
                        const rowIndex = cell.getAttribute('data-dash-row');
                        
                        // If clicking Quarter or Day cells, clear selection and enable all
                        if (columnId === 'Quarter' || columnId === 'Day') {
                            selectedCells.forEach(c => c.classList.remove('cell-selected'));
                            selectedCells = [];
                            updateSelectionState(spreadsheet, selectedCells);
                            return;
                        }
                        
                        // If clicking Month (and not the toggle icon), toggle entire row selection
                        if (columnId === 'Month') {
                            // Get all cells in this row (excluding Year, Quarter, Month, and Day columns)
                            const rowCells = spreadsheet.querySelectorAll(`td[data-dash-row="${rowIndex}"]`);
                            const rowPriceCells = [];
                            rowCells.forEach(rowCell => {
                                const cellColId = rowCell.getAttribute('data-dash-column');
                                if (cellColId !== 'Year' && cellColId !== 'Quarter' && cellColId !== 'Month' && cellColId !== 'Day') {
                                    const cellVal = getCellValue(rowCell);
                                    if (cellVal && cellVal !== '' && cellVal !== 'NaN' && !isNaN(parseFloat(cellVal))) {
                                        rowPriceCells.push(rowCell);
                                    }
                                }
                            });
                            
                            // Check if this row is already selected (all price cells in row are selected)
                            const isRowSelected = rowPriceCells.length > 0 && rowPriceCells.every(cell => cell.classList.contains('cell-selected'));
                            
                            if (isRowSelected) {
                                // Row is already selected - deselect it
                                rowPriceCells.forEach(cell => {
                                    cell.classList.remove('cell-selected');
                                });
                                selectedCells = selectedCells.filter(cell => !rowPriceCells.includes(cell));
                            } else {
                                // Row is not selected - select entire row
                                selectedCells.forEach(c => c.classList.remove('cell-selected'));
                                selectedCells = [];
                                rowPriceCells.forEach(cell => {
                                    cell.classList.add('cell-selected');
                                    selectedCells.push(cell);
                                });
                            }
                            
                            // Update selection state (dim other cells)
                            updateSelectionState(spreadsheet, selectedCells);
                            return;
                        }
                        
                        const cellValue = getCellValue(cell);
                        if (!cellValue || cellValue === '' || cellValue === 'NaN' || isNaN(parseFloat(cellValue))) return;
                        
                        // Check if this cell is already selected
                        const index = selectedCells.indexOf(cell);
                        if (index > -1) {
                            // Clicking same cell again - deselect and enable all
                            cell.classList.remove('cell-selected');
                            selectedCells.splice(index, 1);
                        } else {
                            // Select new cell - clear previous selection
                            selectedCells.forEach(c => c.classList.remove('cell-selected'));
                            selectedCells = [];
                            cell.classList.add('cell-selected');
                            selectedCells.push(cell);
                        }
                        
                        // Update selection state (dim other cells)
                        updateSelectionState(spreadsheet, selectedCells);
                    });
                }

                // Apply enhancements
                if (!window.globalPricesMutationObserver) {
                    window.globalPricesMutationObserver = new MutationObserver(function(mutations) {
                        // Only re-enhance if table structure changed
                        const tableEl = document.getElementById('global-prices-table');
                        if (tableEl) {
                            const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                            if (spreadsheet && spreadsheet.dataset.enhanced !== 'true') {
                                enhanceTable();
                            }
                        }
                    });
                    window.globalPricesMutationObserver.observe(document.body, { 
                        childList: true, 
                        subtree: true 
                    });
                }
                
                enhanceTable();
            } catch (error) {
                console.error('Global prices table enhancer error:', error);
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('global-prices-enhancer-anchor', 'children'),
        Input('global-prices-table', 'id'),
        prevent_initial_call=False
    )