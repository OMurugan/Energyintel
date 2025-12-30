"""
Global Crude Spot Prices View
Daily Crude Spot Prices ($/bbl)
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

# Updated query for daily spot prices based on email requirements
SPOT_PRICE_QUERY = """
    WITH crude_names AS (
        SELECT DISTINCT 
            fwp.crude_country_id, 
            fwp.crude_country, 
            fwp.crude_id, 
            fwp.crude_name, 
            dc.region,
            dc.country_long_name as country_name
        FROM fact_wcod_prices fwp 
        JOIN dim_country dc ON fwp.crude_country_id = dc.dim_country_id 
        WHERE fwp.price_type = 'Spot'
    ),
    date_range AS (
        SELECT generate_series(
            (SELECT MIN(date) FROM fact_wcod_prices WHERE price_type = 'Spot'),
            (SELECT MAX(date) FROM fact_wcod_prices WHERE price_type = 'Spot'),
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
        FROM fact_wcod_prices fwp 
        WHERE fwp.price_type = 'Spot'
    )
    SELECT 
        ac.price_date,
        ac.region,
        ac.crude_country_id,
        ac.crude_country,
        ac.crude_id,
        ac.crude_name,
        ac.country_name,
        sp.spot_price AS price,
        ac.year_int,
        ac.month_name,
        ac.month_num,
        ac.day_num,
        ac.quarter
    FROM all_combinations ac
    LEFT JOIN spot_prices sp ON sp.crude_country_id = ac.crude_country_id
                             AND sp.crude_id = ac.crude_id
                             AND sp.price_date = ac.price_date
    WHERE sp.spot_price IS NOT NULL
    ORDER BY ac.year_int DESC, ac.month_num DESC, ac.region, ac.crude_country, ac.crude_name
"""


def load_crude_prices_data():
    """Load and parse crude spot prices data from Postgres (long format)."""
    results = execute_query(SPOT_PRICE_QUERY)
    df = pd.DataFrame(results)

    if df.empty:
        raise Exception("No crude spot price data returned from database.")

    # Log a small summary to confirm query is working
    try:
        logger.info(
            "[global_spot_prices] rows=%s dates=%s..%s unique_crudes=%s",
            len(df),
            df['price_date'].min(),
            df['price_date'].max(),
            df['crude_name'].nunique()
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
    df['Price'] = pd.to_numeric(df['price'], errors='coerce')
    
    # Use quarter from SQL
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
    
    # Sort by Year (descending), Quarter (descending), Month (descending), Day (descending)
    # For daily data, we want latest dates first
    df_sorted = df.sort_values(['YearInt', 'QuarterOrder', 'MonthOrder', 'DayInt'], 
                               ascending=[False, False, False, False])
    
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
    # Get region name from metadata to ensure proper header alignment
    region_name = ''
    if column_metadata:
        # Get the region from the first metadata entry (all should have the same region)
        region_name = str(column_metadata[0].get('region', '')).strip()
    
    # Use region name in top level, zero-width character in middle level that will merge across left columns,
    # and column name in bottom level. The zero-width character creates proper cell structure for alignment
    # but is visually invisible. This ensures country headers align correctly with their blend columns.
    # The same placeholder value across all left columns causes Dash to merge them into a single colspan cell
    # in the middle header row, which properly aligns with the country header row (Algeria, Angola, etc.)
    # Use unique invisible placeholders for Level 1 and Level 2 of date columns.
    # This prevents them from merging with each other or the region labels, 
    # ensuring that th[data-dash-column="..."] correctly hides all hierarchical levels
    # for Quarter and Day without affecting Year or Month.
    columns = [
        {'name': ['\u200B', '\u200B', 'Year'], 'id': 'Year', 'type': 'text'},
        {'name': ['\u200C', '\u200C', 'Quarter'], 'id': 'Quarter', 'type': 'text'},
        {'name': ['\u200D', '\u200D', 'Month'], 'id': 'Month', 'type': 'text'},
        {'name': ['\u200E', '\u200E', 'Day'], 'id': 'Day', 'type': 'text'},
    ]
    
    # Dynamic order: region → country → blend (alphabetical) so all DB data shows
    sorted_meta = sorted(
        column_metadata,
        key=lambda m: (
            str(m['region']).lower(),
            str(m['country']).lower(),
            str(m['blend']).lower(),
        ),
    )

    for meta in sorted_meta:
        columns.append({
            'name': [meta['region'], meta['country'], meta['blend']],
            'id': meta['column_id'],
            'type': 'numeric',
            'format': {'specifier': '.2f'}
        })
    
    return columns


def create_layout():
    """Create the layout for Global Crude Spot Prices dashboard."""
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
        html.Div([
            html.Div(style={'flexGrow': 1}), # Left spacer
            # Title
            html.H2(
                "Daily Crude Spot Prices ($/bbl)",
                style={
                    'textAlign': 'center', # Center the title
                    'marginTop': '0px',
                    'fontSize': '20px',
                    'fontWeight': 'bold',
                    'color': '#fe5000',
                    'fontFamily': 'Arial, sans-serif'
                }
            ),
            # Export button and download component
            html.Div([
                html.Button(
                    "Export Data Table to CSV",
                    id='btn-export-global-prices-data-table-csv',
                    n_clicks=0,
                    style={
                        'margin': '10px 0',
                        'padding': '10px 20px',
                        'fontSize': '14px',
                        'fontWeight': 'bold',
                        'color': '#1b365d',
                        'backgroundColor': '#f8f9fa',
                        'border': '1px solid #dee2e6',
                        'borderRadius': '5px',
                        'cursor': 'pointer'
                    }
                ),
                dcc.Download(id="download-global-prices-data-table-csv"),
            ], style={'textAlign': 'right', 'flexGrow': 1}) # Align the button to the right within its container
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'paddingBottom': '20px'}),
        
        # Table
        html.Div([
            dcc.Loading(
                id="loading-global-prices-table",
                type="default", # You can choose 'graph', 'cube', 'circle', 'dot', or 'default'
                children=html.Div([
                    dash_table.DataTable(
                id='global-prices-table',
                data=table_data,
                columns=table_columns,
                merge_duplicate_headers=True,
                fixed_rows={'headers': True},
                style_table={
                    'tableLayout': 'fixed',
                    'overflowX': 'auto',
                    'overflowY': 'auto',
                    'border': '1px solid #dee2e6',
                    'fontFamily': 'Arial, sans-serif',
                    'fontSize': '12px',
                    'height': '800px',
                    'maxHeight': '800px',
                    'minWidth': '1400px',
                    'marginTop': '0px'
                },
                style_cell={
                    'textAlign': 'right',
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
                    },
                    # Ensure fixed columns maintain background color for odd rows
                    {
                        'if': {'row_index': 'odd', 'column_id': 'Year'},
                        'backgroundColor': '#f8f9fa'
                    },
                    {
                        'if': {'row_index': 'odd', 'column_id': 'Quarter'},
                        'backgroundColor': '#f8f9fa'
                    },
                    {
                        'if': {'row_index': 'odd', 'column_id': 'Month'},
                        'backgroundColor': '#f8f9fa'
                    },
                    {
                        'if': {'row_index': 'odd', 'column_id': 'Day'},
                        'backgroundColor': '#f8f9fa'
                    },
                    # Ensure fixed columns maintain white background for even rows
                    {
                        'if': {'row_index': 'even', 'column_id': 'Year'},
                        'backgroundColor': 'white'
                    },
                    {
                        'if': {'row_index': 'even', 'column_id': 'Quarter'},
                        'backgroundColor': 'white'
                    },
                    {
                        'if': {'row_index': 'even', 'column_id': 'Month'},
                        'backgroundColor': 'white'
                    },
                    {
                        'if': {'row_index': 'even', 'column_id': 'Day'},
                        'backgroundColor': 'white'
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
                 selected_cells=[],
                 style_header_conditional=[
                     {
                         'if': {'header_index': 0}, # For Region headers
                         'backgroundColor': '#f8f9fa',
                         'fontWeight': 'bold',
                         'textAlign': 'center',
                         'color': '#1b365d'  # Default color for Level 1 header
                     },
                     {
                         'if': {'header_index': 1}, # For Country headers
                         'backgroundColor': '#f8f9fa',
                         'fontWeight': 'bold',
                         'textAlign': 'center',
                         'color': '#1b365d'
                     },
                     {
                         'if': {'header_index': 2}, # For Blend headers
                         'backgroundColor': '#f8f9fa',
                         'fontWeight': 'normal',
                         'textAlign': 'center',
                         'color': '#1b365d'
                     }
                 ],
                 css=[
                     {
                         'selector': '.dash-table-tooltip',
                         'rule': 'display: none'
                     },
                     {
                         'selector': '#global-prices-table .dash-spreadsheet-container th',
                         'rule': 'cursor: pointer; transition: background-color 0.2s ease;'
                     },
                     {
                         'selector': '#global-prices-table .dash-spreadsheet-container th.column-selected',
                         'rule': 'background-color: #b3d9ff !important; color: #1b365d !important; font-weight: bold !important;'
                     },
                     {
                         'selector': '#global-prices-table .dash-spreadsheet-container td.column-cell-selected',
                         'rule': 'background-color: #b3d9ff !important; border: none !important; font-weight: 600 !important; color: #1b365d !important; opacity: 1 !important;'
                     },
                     {
                         'selector': '#global-prices-table .dash-spreadsheet-container td.row-cell-selected',
                         'rule': 'background-color: #b3d9ff !important; border: none !important; font-weight: 600 !important; color: #1b365d !important; opacity: 1 !important;'
                     },
                     {
                         'selector': '#global-prices-table .dash-spreadsheet-container.column-selection-active td:not([data-dash-column="Year"]):not([data-dash-column="Quarter"]):not([data-dash-column="Month"]):not([data-dash-column="Day"]):not(.column-cell-selected)',
                         'rule': 'opacity: 0.3 !important;'
                     },
                     {
                         'selector': '#global-prices-table .dash-spreadsheet-container.row-selection-active tbody tr:not(.row-selected) td',
                         'rule': 'opacity: 0.3 !important;'
                     },
                     {
                         'selector': '#global-prices-table .dash-spreadsheet-container.row-selection-active tbody tr.row-selected td.row-cell-selected',
                         'rule': 'opacity: 1 !important; background-color: #b3d9ff !important; color: #1b365d !important; font-weight: 600 !important; border: none !important;'
                     }
                 ]
             )], style={'width': '100%', 'overflowX': 'hidden'})
         )], style={'margin': '0 auto', 'maxWidth': '100%', 'position': 'relative', 'padding': '20px'}),
        
        # Hidden div for clientside callback anchor
        html.Div(id='global-prices-enhancer-anchor', style={'display': 'none'}),
        
        # Clientside script for table enhancements
        html.Script(
            id='global-prices-clientside-script',
            children=''
        ),
        # Footnote
        html.Div(
            "Countries: Select jurisdictions are included under countries for data presentation purposes.",
            style={
                'fontSize': '10px', # Smaller font size for footnotes
                'color': '#6c757d', # Grayish color for footnotes
                'textAlign': 'left',
                'marginTop': '20px',
                'marginBottom': '10px',
                'paddingLeft': '20px',
                'fontFamily': 'Arial, sans-serif'
            }
        )
    ], style={'backgroundColor': '#ffffff'})


def register_callbacks(dash_app, server):
    """Register all callbacks for Global Crude Spot Prices dashboard."""
    
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
#global-prices-table .dash-spreadsheet-container {
    cursor: pointer;
    table-layout: fixed;
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
/* Fix first 4 columns (Year, Quarter, Month, Day) on the left - they don't scroll */
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Year"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Year"] {
    position: sticky !important;
    left: 0 !important;
    z-index: 10 !important;
    box-shadow: 2px 0 4px rgba(0,0,0,0.1);
}
/* Quarter: positioned after Year (80px) when visible */
#global-prices-table .dash-spreadsheet-container.year-expanded th[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container.year-expanded td[data-dash-column="Quarter"] {
    position: sticky !important;
    left: 80px !important;
    z-index: 10 !important;
    box-shadow: 2px 0 4px rgba(0,0,0,0.1);
}
/* Month: positioned at 80px when Quarter is hidden, 140px when Quarter is visible */
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Month"] {
    position: sticky !important;
    left: 80px !important;
    z-index: 10 !important;
    box-shadow: 2px 0 4px rgba(0,0,0,0.1);
}
#global-prices-table .dash-spreadsheet-container.year-expanded th[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container.year-expanded td[data-dash-column="Month"] {
    left: 140px !important;
}
/* Day: positioned after Month (180px when Quarter hidden, 240px when Quarter visible) */
#global-prices-table .dash-spreadsheet-container.month-expanded:not(.year-expanded) th[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container.month-expanded:not(.year-expanded) td[data-dash-column="Day"] {
    position: sticky !important;
    left: 180px !important;
    z-index: 10 !important;
    box-shadow: 2px 0 4px rgba(0,0,0,0.1);
}
#global-prices-table .dash-spreadsheet-container.month-expanded.year-expanded:not(.quarter-collapsed) th[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container.month-expanded.year-expanded:not(.quarter-collapsed) td[data-dash-column="Day"] {
    position: sticky !important;
    left: 240px !important;
    z-index: 10 !important;
    box-shadow: 2px 0 4px rgba(0,0,0,0.1);
}
/* Ensure header cells have higher z-index and background color */
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Year"],
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Day"] {
    z-index: 11 !important;
    background-color: #f8f9fa !important;
}
/* Ensure middle-level header cells for Year/Quarter/Month/Day are properly aligned */
/* The zero-width character in middle level creates proper cell structure without visual content */
/* Dash DataTable's merge_duplicate_headers=True automatically creates colspan:
   - Default (Year + Month): colspan 2
   - With Quarter: colspan 3 (Year, Quarter, Month)
   - With Day: colspan 4 (Year, Quarter, Month, Day)
   This ensures the middle-level header spans all visible date columns and aligns with country headers */
/* Default: Quarter and Day columns hidden (Year and Month visible by default) */
/* Use very specific selectors to ensure these columns are hidden on initial load */
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Day"] {
    display: none !important;
    width: 0 !important;
    min-width: 0 !important;
    max-width: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
    overflow: hidden !important;
    visibility: hidden !important;
}
/* Show Quarter when year is expanded */
#global-prices-table .dash-spreadsheet-container.year-expanded th[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container.year-expanded td[data-dash-column="Quarter"] {
    display: table-cell !important;
    width: auto !important;
    min-width: 60px !important;
    max-width: none !important;
    padding: 6px 10px !important;
    margin: 0 !important;
    border: 1px solid #e6e6e6 !important;
    overflow: visible !important;
    visibility: visible !important;
}
/* Hide Month and Day when quarter is collapsed (only when Quarter is visible) */
#global-prices-table .dash-spreadsheet-container.year-expanded.quarter-collapsed th[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container.year-expanded.quarter-collapsed th[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container.year-expanded.quarter-collapsed td[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container.year-expanded.quarter-collapsed td[data-dash-column="Day"] {
    display: none !important;
    width: 0 !important;
    padding: 0 !important;
    border: none !important;
    overflow: hidden !important;
}
/* Show Day when month is expanded (hide if quarter is collapsed) */
#global-prices-table .dash-spreadsheet-container.month-expanded:not(.quarter-collapsed) th[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container.month-expanded:not(.quarter-collapsed) td[data-dash-column="Day"] {
    display: table-cell !important;
    width: auto !important;
    min-width: 50px !important;
    max-width: none !important;
    padding: 6px 10px !important;
    margin: 0 !important;
    border: 1px solid #e6e6e6 !important;
    overflow: visible !important;
    visibility: visible !important;
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
    border: none !important;
    font-weight: 600;
    color: #1b365d !important;
    opacity: 1 !important;
}
#global-prices-table .dash-spreadsheet-container td.row-cell-selected {
    background-color: #b3d9ff !important;
    border: none !important;
    font-weight: 600 !important;
    color: #1b365d !important;
    opacity: 1 !important;
}
#global-prices-table .dash-spreadsheet-container.row-selection-active tbody tr:not(.row-selected) td {
    opacity: 0.3 !important;
}
#global-prices-table .dash-spreadsheet-container.row-selection-active tbody tr.row-selected td.row-cell-selected {
    opacity: 1 !important;
    background-color: #b3d9ff !important;
    color: #1b365d !important;
    font-weight: 600 !important;
    border: none !important;
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
                    if (!spreadsheet) return;
                    // Clear all column headers
                    const allHeaders = spreadsheet.querySelectorAll('th.column-selected');
                    allHeaders.forEach(header => {
                        header.classList.remove('column-selected');
                        header.style.removeProperty('background-color');
                        header.style.removeProperty('color');
                        header.style.removeProperty('font-weight');
                    });
                    
                    // Clear all column cells
                    const allColumnCells = spreadsheet.querySelectorAll('td.column-cell-selected');
                    allColumnCells.forEach(cell => {
                        cell.classList.remove('column-cell-selected');
                        cell.style.removeProperty('background-color');
                        cell.style.removeProperty('border');
                        cell.style.removeProperty('font-weight');
                        cell.style.removeProperty('color');
                        cell.style.removeProperty('opacity');
                    });
                    
                    // Remove column selection active class and reset opacity for all cells
                    spreadsheet.classList.remove('column-selection-active');
                    const allDataCells = spreadsheet.querySelectorAll('td[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Quarter"]):not([data-dash-column="Month"]):not([data-dash-column="Day"])');
                    allDataCells.forEach(cell => {
                        cell.style.removeProperty('opacity');
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
                        cell.style.removeProperty('filter');
                    });
                    
                    // Also clear any cells that might have been highlighted but don't have the class
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
                            c.style.removeProperty('filter');
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

                function enhanceTable() {
                    const tableEl = document.getElementById('global-prices-table');
                    if (!tableEl) return;
                    
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    if (!spreadsheet) return;
                    
                    // Initialize global state if not exists
                    if (!window.globalPricesState) {
                        window.globalPricesState = {
                            selectedColumnId: null,
                            selectedRowIndex: null,
                            selectedYear: null,
                            lastTableSignature: null
                        };
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
                    const signatureChanged = window.globalPricesState.lastTableSignature !== tableSignature;
                    if (signatureChanged) {
                        // Table was re-rendered, reset enhanced flag and clear handlers
                        spreadsheet.dataset.enhanced = 'false';
                        
                        // Remove old click handler
                        if (spreadsheet._globalPricesClickHandler) {
                            spreadsheet.removeEventListener('click', spreadsheet._globalPricesClickHandler, true);
                            spreadsheet._globalPricesClickHandler = null;
                        }
                        
                        // Clear selections
                        clearAllColumnSelections(spreadsheet);
                        clearAllRowSelections(spreadsheet);
                        
                        window.globalPricesState.lastTableSignature = tableSignature;
                        window.globalPricesState.selectedColumnId = null;
                        window.globalPricesState.selectedRowIndex = null;
                        window.globalPricesState.selectedYear = null;
                    }
                    
                    // Skip if already enhanced (but only if signature hasn't changed)
                    if (spreadsheet.dataset.enhanced === 'true' && !signatureChanged) {
                        return;
                    }
                    
                    spreadsheet.dataset.enhanced = 'true';
                    let selectedCells = [];
                    let selectedColumnId = null;
                    let isYearExpanded = false; // Default: hide Quarter
                    let isMonthExpanded = false; // Default: hide Day
                    let isQuarterCollapsed = false; // Default: Month and Day visible when Quarter is shown
                    
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
                        if (isYearExpanded) {
                            spreadsheet.classList.add('year-expanded');
                            // Initialize Quarter header toggle when Quarter becomes visible
                            setTimeout(function() {
                                initializeQuarterHeaderToggle();
                            }, 100);
                        } else {
                            spreadsheet.classList.remove('year-expanded');
                            // Reset quarter collapse state when Quarter is hidden
                            isQuarterCollapsed = false;
                            spreadsheet.classList.remove('quarter-collapsed');
                        }
                        
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
                        if (isQuarterCollapsed) {
                            spreadsheet.classList.add('quarter-collapsed');
                        } else {
                            spreadsheet.classList.remove('quarter-collapsed');
                        }
                        
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
                        
                        // Toggle Day column visibility
                        if (isMonthExpanded) {
                            spreadsheet.classList.add('month-expanded');
                        } else {
                            spreadsheet.classList.remove('month-expanded');
                        }
                        
                        // Clear selections
                        clearAllColumnSelections(spreadsheet);
                        selectedColumnId = null;
                        selectedCells.forEach(c => c.classList.remove('cell-selected'));
                        selectedCells = [];
                        updateSelectionState(spreadsheet, selectedCells);
                    }
                    
                    // Initialize on load
                    initializeYearHeaderToggle();
                    initializeMonthHeaderToggle();
                    if (isYearExpanded) {
                        initializeQuarterHeaderToggle();
                    }
                    
                    // Clear selection on outside click (use a single global handler)
                    if (!window.globalPricesOutsideClickHandler) {
                        window.globalPricesOutsideClickHandler = function(event) {
                            const tableEl = document.getElementById('global-prices-table');
                            if (!tableEl) return;
                            const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                            if (!spreadsheet) return;
                            
                            if (!spreadsheet.contains(event.target)) {
                                clearAllColumnSelections(spreadsheet);
                                clearAllRowSelections(spreadsheet);
                                if (window.globalPricesState) {
                                    window.globalPricesState.selectedColumnId = null;
                                    window.globalPricesState.selectedRowIndex = null;
                                    window.globalPricesState.selectedYear = null;
                                }
                            }
                        };
                        document.addEventListener('click', window.globalPricesOutsideClickHandler);
                    }
                    
                    // Remove any existing click handler to avoid duplicates
                    if (spreadsheet._globalPricesClickHandler) {
                        spreadsheet.removeEventListener('click', spreadsheet._globalPricesClickHandler, true);
                    }
                    
                    // Create click handler - capture spreadsheet and functions in closure
                    const clickHandler = function(event) {
                        // Get spreadsheet from event target to ensure we have the right element
                        const clickedSpreadsheet = event.target.closest('.dash-spreadsheet-container') || spreadsheet;
                        if (!clickedSpreadsheet) return;
                        
                        // Try to find header - check multiple ways
                        let header = event.target.closest('th[data-dash-column]');
                        
                        // If not found, try finding by checking if we're in a thead
                        if (!header) {
                            const thead = event.target.closest('thead');
                            if (thead) {
                                // Find the th that contains the clicked element
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
                            
                            // Handle Year header toggle
                            if (columnId === 'Year') {
                                // Check if clicking on toggle button
                                const toggleBtn = event.target.closest('.year-header-toggle');
                                if (toggleBtn) {
                                    toggleYearExpand();
                                    return;
                                }
                                // If clicking header itself (not toggle), allow it to fall through for row highlighting
                            }
                            
                            // Handle Month header toggle
                            if (columnId === 'Month') {
                                // Check if clicking on toggle button
                                const toggleBtn = event.target.closest('.month-header-toggle');
                                if (toggleBtn) {
                                    toggleMonthExpand();
                                    return;
                                }
                            }
                            
                            // Handle Quarter header toggle
                            if (columnId === 'Quarter') {
                                // Check if clicking on toggle button
                                const toggleBtn = event.target.closest('.quarter-header-toggle');
                                if (toggleBtn) {
                                    toggleQuarterCollapse();
                                    return;
                                }
                            }
                            
                            // Skip Year, Quarter, Month, Day columns for column selection
                            if (columnId === 'Year' || columnId === 'Quarter' || columnId === 'Month' || columnId === 'Day') {
                                return;
                            }
                            
                            // Clear all previous selections before processing new selection
                            clearAllColumnSelections(clickedSpreadsheet);
                            clearAllRowSelections(clickedSpreadsheet);
                            if (window.globalPricesState) {
                                window.globalPricesState.selectedRowIndex = null;
                                window.globalPricesState.selectedYear = null;
                            }
                            
                            // Find which header row this header belongs to (header_index)
                            const headerRow = header.closest('tr');
                            const thead = header.closest('thead');
                            
                            let headerIndex = -1;
                            let totalHeaderRows = 0;
                            let headerRows = [];
                            
                            if (thead) {
                                headerRows = Array.from(thead.querySelectorAll('tr'));
                            }
                            
                            // If no rows found in thead, try in spreadsheet
                            if (headerRows.length === 0 && clickedSpreadsheet) {
                                headerRows = Array.from(clickedSpreadsheet.querySelectorAll('thead tr'));
                            }
                            
                            // If still no rows, try finding any tr containing headers
                            if (headerRows.length === 0 && clickedSpreadsheet) {
                                const allTrs = clickedSpreadsheet.querySelectorAll('tr');
                                headerRows = Array.from(allTrs).filter(tr => {
                                    return tr.querySelector('th[data-dash-column]') !== null;
                                });
                            }
                            
                            // Filter out rows that only contain Year/Quarter/Month/Day headers - we only want data column header rows
                            // A data column header row should have at least one header with columnId not in the fixed list
                            headerRows = headerRows.filter(tr => {
                                const dataHeaders = tr.querySelectorAll('th[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Quarter"]):not([data-dash-column="Month"]):not([data-dash-column="Day"])');
                                return dataHeaders.length > 0;
                            });
                            
                            totalHeaderRows = headerRows.length;
                            
                            if (headerRow && headerRows.length > 0) {
                                headerIndex = headerRows.indexOf(headerRow);
                            } else if (headerRow) {
                                // If headerRow is not in the filtered list, it might be a Year/Quarter/Month/Day row
                                // Try to find it in the original thead rows
                                const theadRows = thead ? Array.from(thead.querySelectorAll('tr')) : [];
                                const allDataHeadersRows = theadRows.filter(tr => {
                                    const dataHeaders = tr.querySelectorAll('th[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Quarter"]):not([data-dash-column="Month"]):not([data-dash-column="Day"])');
                                    return dataHeaders.length > 0;
                                });
                                if (allDataHeadersRows.length > 0) {
                                    headerIndex = allDataHeadersRows.indexOf(headerRow);
                                    headerRows = allDataHeadersRows;
                                    totalHeaderRows = headerRows.length;
                                }
                            }
                            
                            
                            // Create a unique key for this selection (columnId + headerIndex)
                            const selectionKey = columnId + '_' + headerIndex;
                            
                            // Check if this exact header level is already selected
                            if (window.globalPricesState && window.globalPricesState.selectedColumnId === selectionKey) {
                                // Deselect column
                                clearAllColumnSelections(clickedSpreadsheet);
                                if (window.globalPricesState) {
                                    window.globalPricesState.selectedColumnId = null;
                                }
                            } else {
                                // Select new column
                                clearAllColumnSelections(clickedSpreadsheet);
                                clearAllRowSelections(clickedSpreadsheet);
                                
                                if (window.globalPricesState) {
                                    window.globalPricesState.selectedColumnId = selectionKey;
                                    window.globalPricesState.selectedRowIndex = null;
                                    window.globalPricesState.selectedYear = null;
                                }
                                
                                // Check if this is the bottom-most header level
                                const isBottomHeader = (headerIndex >= 0 && totalHeaderRows > 0 && headerIndex === totalHeaderRows - 1);
                                // Check if this is the top-most header level (index 0)
                                const isTopHeader = (headerIndex === 0);
                                
                                if (isBottomHeader || isTopHeader) {
                                    // Bottom or top header clicked - highlight ALL header levels and data cells
                                    if (isTopHeader) {
                                        // For top header, find all columns that share the same top-level header text
                                        const topHeaderText = getCellTextWithoutIcons(header, 'year-header-toggle');
                                        
                                        // Check if header has colspan (spans multiple columns)
                                        const colspan = header.getAttribute('colspan') || header.colSpan;
                                        
                                        // Find all headers in the top row (index 0) with the same text
                                        const topRow = headerRows[0];
                                        if (topRow) {
                                            // Get all column IDs under this spanning header
                                            const columnIds = new Set();
                                            
                                            if (colspan && parseInt(colspan) > 1) {
                                                // Header spans multiple columns - find all columns under it
                                                const spanCount = parseInt(colspan);
                                                
                                                // Get all cells in the top row (including merged cells)
                                                const allTopRowCells = Array.from(topRow.querySelectorAll('th'));
                                                
                                                // Find the clicked header's position in the row
                                                let clickedCellIndex = -1;
                                                for (let i = 0; i < allTopRowCells.length; i++) {
                                                    if (allTopRowCells[i] === header || allTopRowCells[i].contains(header)) {
                                                        clickedCellIndex = i;
                                                        break;
                                                    }
                                                }
                                                
                                                // Get all bottom row headers (last row) to find actual column IDs
                                                const bottomRow = headerRows[headerRows.length - 1];
                                                if (bottomRow) {
                                                    const allBottomRowCells = Array.from(bottomRow.querySelectorAll('th'));
                                                    
                                                    // Calculate the data column start position
                                                    let topRowDataStart = 0;
                                                    
                                                    for (let i = 0; i < clickedCellIndex; i++) {
                                                        const cell = allTopRowCells[i];
                                                        const cellColId = cell.getAttribute('data-dash-column');
                                                        
                                                        // Skip Year/Quarter/Month/Day - they don't count as data columns
                                                        if (cellColId === 'Year' || cellColId === 'Quarter' || cellColId === 'Month' || cellColId === 'Day') {
                                                            continue;
                                                        }
                                                        
                                                        const cellColspan = parseInt(cell.getAttribute('colspan') || cell.colSpan || '1');
                                                        topRowDataStart += cellColspan;
                                                    }
                                                    
                                                    // Map to bottom row: count Year/Quarter/Month/Day in bottom row, then get data columns
                                                    let bottomRowDataColIndex = 0;
                                                    
                                                    for (let i = 0; i < allBottomRowCells.length; i++) {
                                                        const bottomCell = allBottomRowCells[i];
                                                        const bottomCellColId = bottomCell.getAttribute('data-dash-column');
                                                        
                                                        // Skip Year, Quarter, Month, Day in bottom row
                                                        if (bottomCellColId === 'Year' || bottomCellColId === 'Quarter' || bottomCellColId === 'Month' || bottomCellColId === 'Day') {
                                                            continue;
                                                        }
                                                        
                                                        // Check if this data column is within the span
                                                        if (bottomRowDataColIndex >= topRowDataStart && 
                                                            bottomRowDataColIndex < topRowDataStart + spanCount) {
                                                            if (bottomCellColId) {
                                                                columnIds.add(bottomCellColId);
                                                            }
                                                        }
                                                        
                                                        bottomRowDataColIndex++;
                                                    }
                                                    
                                                    // Use comprehensive data row method to ensure we get ALL columns
                                                    // This is more reliable than just using bottom row
                                                    let firstDataRow = clickedSpreadsheet.querySelector('tbody tr');
                                                    if (!firstDataRow) {
                                                        firstDataRow = clickedSpreadsheet.querySelector('tr[data-dash-row]');
                                                    }
                                                    if (!firstDataRow) {
                                                        const allRows = clickedSpreadsheet.querySelectorAll('tr');
                                                        for (let row of allRows) {
                                                            if (row.querySelector('th')) continue;
                                                            const dataCells = row.querySelectorAll('td[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Quarter"]):not([data-dash-column="Month"]):not([data-dash-column="Day"])');
                                                            if (dataCells.length > 0) {
                                                                firstDataRow = row;
                                                                break;
                                                            }
                                                        }
                                                    }
                                                    
                                                    if (firstDataRow) {
                                                        // Build comprehensive position map from all data rows
                                                        const allDataRows = clickedSpreadsheet.querySelectorAll('tbody tr, tr[data-dash-row]');
                                                        const columnPositionMap = new Map();
                                                        
                                                        // Scan all rows to build position map
                                                        allDataRows.forEach(row => {
                                                            if (row.querySelector('th')) return;
                                                            
                                                            const rowCells = Array.from(row.querySelectorAll('td'));
                                                            let dataColIndex = 0;
                                                            
                                                            rowCells.forEach(cell => {
                                                                const colId = cell.getAttribute('data-dash-column');
                                                                // Skip fixed columns
                                                                if (colId === 'Year' || colId === 'Quarter' || colId === 'Month' || colId === 'Day') {
                                                                    return;
                                                                }
                                                                
                                                                // Only map actual data columns
                                                                if (colId && colId.trim() !== '') {
                                                                    // Map columns in the span range
                                                                    if (dataColIndex >= topRowDataStart && dataColIndex < topRowDataStart + spanCount) {
                                                                        if (!columnPositionMap.has(dataColIndex)) {
                                                                            columnPositionMap.set(dataColIndex, colId);
                                                                        }
                                                                    }
                                                                    dataColIndex++;
                                                                }
                                                            });
                                                        });
                                                        
                                                        // Clear and rebuild columnIds with all mapped columns
                                                        columnIds.clear();
                                                        for (let i = topRowDataStart; i < topRowDataStart + spanCount; i++) {
                                                            if (columnPositionMap.has(i)) {
                                                                columnIds.add(columnPositionMap.get(i));
                                                            }
                                                        }
                                                    }
                                                }
                                            } else {
                                                // No colspan or colspan = 1 - find all headers with the same text
                                                const allTopHeaders = Array.from(topRow.querySelectorAll('th[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Quarter"]):not([data-dash-column="Month"]):not([data-dash-column="Day"])'));
                                                const matchingTopHeaders = allTopHeaders.filter(h => {
                                                    const hText = h.textContent.trim();
                                                    return hText === topHeaderText || h === header || h.contains(header);
                                                });
                                                
                                                matchingTopHeaders.forEach(topH => {
                                                    const colId = topH.getAttribute('data-dash-column');
                                                    if (colId) columnIds.add(colId);
                                                });
                                                
                                                // If no matches found, use the clicked header's column
                                                if (columnIds.size === 0 && columnId) {
                                                    columnIds.add(columnId);
                                                }
                                            }
                                            
                                            // Highlight all top-level headers with the same text (for merged headers)
                                            const allTopHeadersInRow = Array.from(topRow.querySelectorAll('th'));
                                            allTopHeadersInRow.forEach(h => {
                                                const hText = h.textContent.trim();
                                                const hColId = h.getAttribute('data-dash-column');
                                                // Skip fixed columns
                                                if (hColId === 'Year' || hColId === 'Quarter' || hColId === 'Month' || hColId === 'Day') {
                                                    return;
                                                }
                                                // If this header matches the clicked header's text or is the clicked header
                                                if (hText === topHeaderText || h === header || h.contains(header)) {
                                                    h.classList.add('column-selected');
                                                    h.style.setProperty('background-color', '#b3d9ff', 'important');
                                                    h.style.setProperty('color', '#1b365d', 'important');
                                                    h.style.setProperty('font-weight', 'bold', 'important');
                                                }
                                            });
                                            
                                            // Highlight data cells for all columns under this top header
                                            columnIds.forEach(colId => {
                                                const colCells = clickedSpreadsheet.querySelectorAll(`td[data-dash-column="${colId}"]`);
                                                colCells.forEach(cell => {
                                                    cell.classList.add('column-cell-selected');
                                                    cell.style.setProperty('background-color', '#b3d9ff', 'important');
                                                    cell.style.setProperty('border', 'none', 'important');
                                                    cell.style.setProperty('font-weight', '600', 'important');
                                                    cell.style.setProperty('color', '#1b365d', 'important');
                                                    cell.style.setProperty('opacity', '1', 'important');
                                                });
                                            });
                                            
                                            clickedSpreadsheet.classList.add('column-selection-active');
                                            
                                            // Dim other columns
                                            const allDataCells = clickedSpreadsheet.querySelectorAll('td[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Quarter"]):not([data-dash-column="Month"]):not([data-dash-column="Day"])');
                                            allDataCells.forEach(cell => {
                                                const cellColId = cell.getAttribute('data-dash-column');
                                                if (!columnIds.has(cellColId)) {
                                                    cell.style.setProperty('opacity', '0.3', 'important');
                                                }
                                            });
                                        }
                                    } else {
                                        // Bottom header clicked - highlight only the bottom header level and data cells
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
                                            const cellValue = getCellValue(cell);
                                            if (cellValue && cellValue !== '' && cellValue !== 'NaN' && !isNaN(parseFloat(cellValue))) {
                                                cell.classList.add('column-cell-selected');
                                                    cell.style.setProperty('background-color', '#b3d9ff', 'important');
                                                    cell.style.setProperty('border', 'none', 'important');
                                                    cell.style.setProperty('font-weight', '600', 'important');
                                                    cell.style.setProperty('color', '#1b365d', 'important');
                                                    cell.style.setProperty('opacity', '1', 'important');
                                            }
                                        });
                                        
                                        clickedSpreadsheet.classList.add('column-selection-active');
                                        
                                        // Dim other columns
                                        const allDataCells = clickedSpreadsheet.querySelectorAll('td[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Quarter"]):not([data-dash-column="Month"]):not([data-dash-column="Day"])');
                                        allDataCells.forEach(cell => {
                                            if (!cell.classList.contains('column-cell-selected')) {
                                                cell.style.opacity = '0.3';
                                            }
                                        });
                                    }
                                } else {
                                    // Middle header (Level 1 or Level 2) - highlight the clicked header and all sub-columns
                                    const headerColspan = header.getAttribute('colspan') || header.colSpan;
                                    const spanCount = headerColspan ? parseInt(headerColspan) : 1;
                                    const headerText = getCellTextWithoutIcons(header, 'year-header-toggle');
                                    
                                    // Get all columns under this header (all bottom-level columns)
                                    const columnIds = new Set();
                                    
                                    // Find all headers in the current row that match this header's text or are within its span
                                    const currentRow = headerRows[headerIndex];
                                    if (currentRow) {
                                        const allRowCells = Array.from(currentRow.querySelectorAll('th'));
                                        let clickedCellIndex = -1;
                                        
                                        // Find the clicked header's position
                                        for (let i = 0; i < allRowCells.length; i++) {
                                            if (allRowCells[i] === header || allRowCells[i].contains(header)) {
                                                clickedCellIndex = i;
                                                break;
                                            }
                                        }
                                        
                                        // Count data columns before this header (skip Year/Quarter/Month/Day)
                                        let columnsBefore = 0;
                                        for (let i = 0; i < clickedCellIndex; i++) {
                                            const cell = allRowCells[i];
                                            const cellColId = cell.getAttribute('data-dash-column');
                                            if (cellColId === 'Year' || cellColId === 'Quarter' || cellColId === 'Month' || cellColId === 'Day') {
                                                continue;
                                            }
                                            const cellColspan = parseInt(cell.getAttribute('colspan') || cell.colSpan || '1');
                                            columnsBefore += cellColspan;
                                        }
                                        
                                        // Use comprehensive data row method (same as price_scorecard.py) to find ALL columns
                                        // This is the most reliable method for finding all sub-columns
                                        let firstDataRow = clickedSpreadsheet.querySelector('tbody tr');
                                        if (!firstDataRow) {
                                            firstDataRow = clickedSpreadsheet.querySelector('tr[data-dash-row]');
                                        }
                                        if (!firstDataRow) {
                                            const allRows = clickedSpreadsheet.querySelectorAll('tr');
                                            for (let row of allRows) {
                                                if (row.querySelector('th')) continue;
                                                const dataCells = row.querySelectorAll('td[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Quarter"]):not([data-dash-column="Month"]):not([data-dash-column="Day"])');
                                                if (dataCells.length > 0) {
                                                    firstDataRow = row;
                                                    break;
                                                }
                                            }
                                        }
                                        
                                        if (firstDataRow) {
                                            // Build column position map from all data rows (comprehensive method)
                                            const allDataRows = clickedSpreadsheet.querySelectorAll('tbody tr, tr[data-dash-row]');
                                            const columnPositionMap = new Map();
                                            
                                            // Scan all rows to build position map for ALL positions
                                            allDataRows.forEach(row => {
                                                if (row.querySelector('th')) return;
                                                
                                                const rowCells = Array.from(row.querySelectorAll('td'));
                                                let dataColIndex = 0;
                                                
                                                rowCells.forEach(cell => {
                                                    const colId = cell.getAttribute('data-dash-column');
                                                    // Skip fixed columns
                                                    if (colId === 'Year' || colId === 'Quarter' || colId === 'Month' || colId === 'Day') {
                                                        return;
                                                    }
                                                    
                                                    // Only map actual data columns (those with valid column IDs)
                                                    if (colId && colId.trim() !== '') {
                                                        // Map columns in the span range
                                                        if (dataColIndex >= columnsBefore && dataColIndex < columnsBefore + spanCount) {
                                                            if (!columnPositionMap.has(dataColIndex)) {
                                                                columnPositionMap.set(dataColIndex, colId);
                                                            }
                                                        }
                                                        dataColIndex++;
                                                    }
                                                });
                                            });
                                            
                                            // Add all mapped columns to the set
                                            for (let i = columnsBefore; i < columnsBefore + spanCount; i++) {
                                                if (columnPositionMap.has(i)) {
                                                    columnIds.add(columnPositionMap.get(i));
                                                }
                                            }
                                        }
                                        
                                        // Fallback: if data row method didn't work, try bottom row method
                                        if (columnIds.size === 0) {
                                            const bottomRow = headerRows[headerRows.length - 1];
                                            if (bottomRow) {
                                                const allBottomRowCells = Array.from(bottomRow.querySelectorAll('th'));
                                                let bottomRowDataColIndex = 0;
                                                
                                                for (let i = 0; i < allBottomRowCells.length; i++) {
                                                    const bottomCell = allBottomRowCells[i];
                                                    const bottomCellColId = bottomCell.getAttribute('data-dash-column');
                                                    
                                                    // Skip Year/Quarter/Month/Day
                                                    if (bottomCellColId === 'Year' || bottomCellColId === 'Quarter' || bottomCellColId === 'Month' || bottomCellColId === 'Day') {
                                                        continue;
                                                    }
                                                    
                                                    // Only process actual data columns
                                                    if (bottomCellColId && bottomCellColId.trim() !== '') {
                                                        // Check if this column is within the span range
                                                        if (bottomRowDataColIndex >= columnsBefore && bottomRowDataColIndex < columnsBefore + spanCount) {
                                                            columnIds.add(bottomCellColId);
                                                        }
                                                        bottomRowDataColIndex++;
                                                    }
                                                }
                                            }
                                        }
                                    } else {
                                        // Fallback: if no current row, try to find by header text matching
                                        // Find all headers with same text in same row
                                        const allHeadersInRow = Array.from(headerRow.querySelectorAll('th'));
                                        const matchingHeaders = allHeadersInRow.filter(h => {
                                            const hText = h.textContent.trim();
                                            return hText === headerText || h === header || h.contains(header);
                                        });
                                        
                                        // For each matching header, find its bottom-level columns
                                        matchingHeaders.forEach(matchingHeader => {
                                            const matchingColId = matchingHeader.getAttribute('data-dash-column');
                                            if (matchingColId && matchingColId !== 'Year' && matchingColId !== 'Quarter' && matchingColId !== 'Month' && matchingColId !== 'Day') {
                                                // Try to find columns by traversing down
                                                const bottomRow = headerRows[headerRows.length - 1];
                                                if (bottomRow) {
                                                    // Find headers in bottom row that might be under this header
                                                    // This is a fallback - the main logic above should handle it
                                                }
                                            }
                                        });
                                        
                                        // If still no columns found, use the clicked column ID
                                        if (columnIds.size === 0 && columnId) {
                                            columnIds.add(columnId);
                                        }
                                    }
                                    
                                    // Highlight the clicked header cell itself and all headers at the same level with same text
                                    if (headerIndex >= 0 && headerRows.length > 0) {
                                        const currentRow = headerRows[headerIndex];
                                        if (currentRow) {
                                            // Highlight all headers in this row with the same text (for merged headers)
                                            const allHeadersInCurrentRow = Array.from(currentRow.querySelectorAll('th'));
                                            allHeadersInCurrentRow.forEach(h => {
                                                const hText = h.textContent.trim();
                                                const hColId = h.getAttribute('data-dash-column');
                                                // Skip fixed columns
                                                if (hColId === 'Year' || hColId === 'Quarter' || hColId === 'Month' || hColId === 'Day') {
                                                    return;
                                                }
                                                // If this header matches the clicked header's text or is the clicked header
                                                if (hText === headerText || h === header || h.contains(header)) {
                                                    h.classList.add('column-selected');
                                                    h.style.setProperty('background-color', '#b3d9ff', 'important');
                                                    h.style.setProperty('color', '#1b365d', 'important');
                                                    h.style.setProperty('font-weight', 'bold', 'important');
                                                }
                                            });
                                        }
                                    }
                                    
                                    // Highlight data cells for all columns under this header
                                    if (columnIds.size > 0) {
                                        columnIds.forEach(colId => {
                                            const colCells = clickedSpreadsheet.querySelectorAll(`td[data-dash-column="${colId}"]`);
                                                colCells.forEach(cell => {
                                                    cell.classList.add('column-cell-selected');
                                                    cell.style.setProperty('background-color', '#b3d9ff', 'important');
                                                    cell.style.setProperty('border', 'none', 'important');
                                                    cell.style.setProperty('font-weight', '600', 'important');
                                                    cell.style.setProperty('color', '#1b365d', 'important');
                                                    cell.style.setProperty('opacity', '1', 'important');
                                                });
                                        });
                                        
                                        clickedSpreadsheet.classList.add('column-selection-active');
                                        
                                        // Dim other columns
                                        const allDataCells = clickedSpreadsheet.querySelectorAll('td[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Quarter"]):not([data-dash-column="Month"]):not([data-dash-column="Day"])');
                                        allDataCells.forEach(cell => {
                                            const cellColId = cell.getAttribute('data-dash-column');
                                                if (!columnIds.has(cellColId)) {
                                                    cell.style.setProperty('opacity', '0.3', 'important');
                                                }
                                        });
                                    } else {
                                        clickedSpreadsheet.classList.remove('column-selection-active');
                                    }
                                }
                            }
                            return false; // Prevent default
                        }
                    
                        // Handle row highlighting when clicking on Year cell
                        const yearCell = event.target.closest('td[data-dash-column="Year"]');
                        if (yearCell) {
                            event.stopPropagation();
                            
                            // Clear column selections first
                            clearAllColumnSelections(clickedSpreadsheet);
                            clearAllRowSelections(clickedSpreadsheet);
                            if (window.globalPricesState) {
                                window.globalPricesState.selectedColumnId = null;
                            }
                            
                            // Get the year value
                            const yearValue = getCellValue(yearCell);
                            
                            if (yearValue) {
                                // Check if this year is already selected
                                if (window.globalPricesState && window.globalPricesState.selectedYear === yearValue) {
                                    // Deselect year - clear all row selections
                                    clearAllRowSelections(clickedSpreadsheet);
                                    if (window.globalPricesState) {
                                        window.globalPricesState.selectedYear = null;
                                        window.globalPricesState.selectedRowIndex = null;
                                    }
                                } else {
                                    // Clear any previous selection
                                    clearAllRowSelections(clickedSpreadsheet);
                                    
                                    // Find all rows with this year and highlight them
                                    const allDataRows = Array.from(clickedSpreadsheet.querySelectorAll('tbody tr'));
                                    let currentYear = null; // Track current year as we iterate
                                    
                                    allDataRows.forEach((row) => {
                                        // Find Year cell in this row
                                        const rowYearCell = row.querySelector('td[data-dash-column="Year"]');
                                        let rowYearValue = null;
                                        
                                        if (rowYearCell) {
                                            const cellValue = getCellValue(rowYearCell);
                                            if (cellValue && cellValue.trim() !== '') {
                                                rowYearValue = cellValue;
                                                currentYear = cellValue;
                                            } else {
                                                rowYearValue = currentYear;
                                            }
                                        } else {
                                            rowYearValue = currentYear;
                                        }
                                        
                                        // Check if this row matches the selected year
                                        if (rowYearValue === yearValue) {
                                            // This row matches the selected year - highlight Year and data cells, but NOT Quarter, Month, Day
                                            const allRowCells = Array.from(row.querySelectorAll('td'));
                                            allRowCells.forEach(c => {
                                                const colId = c.getAttribute('data-dash-column');
                                                if (colId === 'Quarter' || colId === 'Month' || colId === 'Day') {
                                                    // Quarter, Month, Day cells: keep at normal state
                                                    c.classList.remove('row-cell-selected');
                                                    c.style.backgroundColor = '';
                                                    c.style.border = '';
                                                    c.style.fontWeight = '';
                                                    c.style.color = '';
                                                    c.style.opacity = '1';
                                                    c.style.removeProperty('filter');
                                                } else {
                                                    // Year and data columns: highlight
                                                    c.classList.add('row-cell-selected');
                                                    c.style.backgroundColor = '#b3d9ff';
                                                    c.style.border = 'none';
                                                    c.style.fontWeight = '600';
                                                    c.style.color = '#1b365d';
                                                    c.style.opacity = '1';
                                                    c.style.removeProperty('filter');
                                                }
                                            });
                                            row.classList.add('row-selected');
                                        }
                                    });
                                    
                                    // Ensure all cells in non-selected rows are at normal opacity
                                    allDataRows.forEach((row) => {
                                        if (!row.classList.contains('row-selected')) {
                                            const rowCells = row.querySelectorAll('td');
                                            rowCells.forEach(c => {
                                                c.style.opacity = '1';
                                            });
                                        }
                                    });
                                    
                                    if (window.globalPricesState) {
                                        window.globalPricesState.selectedYear = yearValue;
                                        window.globalPricesState.selectedRowIndex = null;
                                    }
                                }
                            }
                            return false; // Prevent default
                        }
                        
                        // Handle row highlighting when clicking on Month cell
                        const monthCell = event.target.closest('td[data-dash-column="Month"]');
                        if (monthCell) {
                            event.stopPropagation();
                            
                            // Clear column selections first
                            clearAllColumnSelections(clickedSpreadsheet);
                            
                            // Clear ALL cells with row-cell-selected class
                            const allHighlightedCells = clickedSpreadsheet.querySelectorAll('td.row-cell-selected');
                            allHighlightedCells.forEach(c => {
                                c.classList.remove('row-cell-selected');
                                c.style.removeProperty('background-color');
                                c.style.removeProperty('border');
                                c.style.removeProperty('font-weight');
                                c.style.removeProperty('color');
                                c.style.removeProperty('opacity');
                                c.style.removeProperty('filter');
                            });
                            
                            // Clear ALL previously selected rows
                            const allSelectedRows = clickedSpreadsheet.querySelectorAll('tbody tr.row-selected');
                            allSelectedRows.forEach(prevRow => {
                                const prevRowCells = prevRow.querySelectorAll('td');
                                prevRowCells.forEach(c => {
                                    c.classList.remove('row-cell-selected');
                                    c.style.removeProperty('background-color');
                                    c.style.removeProperty('border');
                                    c.style.removeProperty('font-weight');
                                    c.style.removeProperty('color');
                                    c.style.removeProperty('opacity');
                                    c.style.removeProperty('filter');
                                });
                                prevRow.classList.remove('row-selected');
                            });
                            
                            // Clear all row selections
                            clearAllRowSelections(clickedSpreadsheet);
                            
                            // Clear state BEFORE applying new selection
                            if (window.globalPricesState) {
                                window.globalPricesState.selectedColumnId = null;
                                window.globalPricesState.selectedRowIndex = null;
                            }
                            
                            // Get the row containing this Month cell
                            const row = monthCell.closest('tr');
                            if (!row) {
                                return false;
                            }
                            
                            let rowIndex = row.getAttribute('data-dash-row');
                            
                            // Fallback: if no data-dash-row, use row position
                            if (!rowIndex) {
                                const tbody = row.closest('tbody');
                                if (tbody) {
                                    const allRows = Array.from(tbody.querySelectorAll('tr'));
                                    const rowPosition = allRows.indexOf(row);
                                    rowIndex = rowPosition.toString();
                                }
                            }
                            
                            // Check if this row is already selected
                            if (window.globalPricesState && window.globalPricesState.selectedRowIndex === rowIndex) {
                                // Deselect row
                                clearAllRowSelections(clickedSpreadsheet);
                                if (window.globalPricesState) {
                                    window.globalPricesState.selectedRowIndex = null;
                                }
                            } else {
                                // Clear any previous row selection
                                clearAllRowSelections(clickedSpreadsheet);
                                
                                // Get all cells directly from the row element
                                const allRowCells = Array.from(row.querySelectorAll('td'));
                                
                                // Highlight Month and data columns, but NOT Year, Quarter, Day
                                allRowCells.forEach((c) => {
                                    const colId = c.getAttribute('data-dash-column');
                                    if (colId === 'Year' || colId === 'Quarter' || colId === 'Day') {
                                        // Year, Quarter, Day columns: keep at normal state
                                        c.classList.remove('row-cell-selected');
                                        c.style.backgroundColor = '';
                                        c.style.border = '';
                                        c.style.fontWeight = '';
                                        c.style.color = '';
                                        c.style.opacity = '1';
                                        c.style.removeProperty('filter');
                                    } else {
                                        // Month and data columns: highlight with bright blue
                                        c.classList.add('row-cell-selected');
                                        c.style.setProperty('background-color', '#b3d9ff', 'important');
                                        c.style.setProperty('border', 'none', 'important');
                                        c.style.setProperty('font-weight', '600', 'important');
                                        c.style.setProperty('color', '#1b365d', 'important');
                                        c.style.setProperty('opacity', '1', 'important');
                                        c.style.removeProperty('filter');
                                    }
                                });
                                
                                // Add row-selected class to row element
                                row.classList.add('row-selected');
                                
                                // Dim other rows first
                                const allDataRows = clickedSpreadsheet.querySelectorAll('tbody tr');
                                allDataRows.forEach((r) => {
                                    const rIndex = r.getAttribute('data-dash-row') || Array.from(allDataRows).indexOf(r).toString();
                                    if (rIndex !== rowIndex) {
                                        // Dim all cells in other rows
                                        const rowCells = r.querySelectorAll('td');
                                        rowCells.forEach(c => {
                                            c.style.setProperty('opacity', '0.3', 'important');
                                        });
                                    }
                                });
                                
                                // Now add row-selection-active class
                                clickedSpreadsheet.classList.add('row-selection-active');
                                
                                // Force selected row to be bright
                                const selectedRowCells = row.querySelectorAll('td');
                                selectedRowCells.forEach(c => {
                                    const colId = c.getAttribute('data-dash-column');
                                    if (colId !== 'Year' && colId !== 'Quarter' && colId !== 'Day') {
                                        c.style.setProperty('opacity', '1', 'important');
                                        c.style.setProperty('background-color', '#b3d9ff', 'important');
                                        c.style.setProperty('color', '#1b365d', 'important');
                                        c.style.setProperty('font-weight', '600', 'important');
                                        c.style.setProperty('border', 'none', 'important');
                                        c.style.removeProperty('filter');
                                    } else {
                                        // Year, Quarter, Day columns: normal state
                                        c.style.setProperty('opacity', '1', 'important');
                                        c.style.setProperty('background-color', '', 'important');
                                        c.style.setProperty('color', '', 'important');
                                        c.style.setProperty('font-weight', '', 'important');
                                    }
                                });
                                
                                if (window.globalPricesState) {
                                    window.globalPricesState.selectedRowIndex = rowIndex;
                                }
                            }
                            return false;
                        }
                        
                        // If clicking on a data cell, clear column and row selections
                        const cell = event.target.closest('td[data-dash-column]');
                        if (cell) {
                            const columnId = cell.getAttribute('data-dash-column');
                            if (columnId && columnId !== 'Year' && columnId !== 'Quarter' && columnId !== 'Month' && columnId !== 'Day') {
                                clearAllColumnSelections(clickedSpreadsheet);
                                clearAllRowSelections(clickedSpreadsheet);
                                
                                if (window.globalPricesState) {
                                    window.globalPricesState.selectedColumnId = null;
                                    window.globalPricesState.selectedRowIndex = null;
                                }
                            }
                        }
                    };
                    
                    spreadsheet._globalPricesClickHandler = clickHandler;
                    
                    // Add click handler with capture phase
                    spreadsheet.addEventListener('click', spreadsheet._globalPricesClickHandler, true);
                }

                // Apply enhancements with multiple attempts to ensure table is rendered
                function tryEnhance() {
                    const tableEl = document.getElementById('global-prices-table');
                    if (!tableEl) {
                        return false;
                    }
                    
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    if (!spreadsheet) {
                        return false;
                    }
                    
                    // Check if headers exist
                    const headers = spreadsheet.querySelectorAll('th[data-dash-column]');
                    if (headers.length === 0) {
                        return false;
                    }
                    
                    // Check enhancement status
                    const isEnhanced = spreadsheet.dataset.enhanced === 'true';
                    
                    // Only enhance if not already enhanced
                    if (!isEnhanced) {
                        enhanceTable();
                        return true;
                    }
                    
                    return true;
                }
                
                // Try immediately
                if (!tryEnhance()) {
                    // Try after short delay
                    setTimeout(function() {
                        if (!tryEnhance()) {
                            // Try after medium delay
                            setTimeout(function() {
                                if (!tryEnhance()) {
                                    // Try after longer delay
                                    setTimeout(function() {
                                        tryEnhance();
                                    }, 1000);
                                }
                            }, 300);
                        }
                    }, 100);
                }
                
                // Use MutationObserver to re-enhance when table structure changes
                if (!window.globalPricesMutationObserver) {
                    window.globalPricesMutationObserver = new MutationObserver(function(mutations) {
                        const tableEl = document.getElementById('global-prices-table');
                        if (tableEl) {
                            const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                            if (spreadsheet) {
                                const headers = spreadsheet.querySelectorAll('th[data-dash-column]');
                                
                                // Check if table structure changed
                                let tableSignature = '';
                                const topRow = spreadsheet.querySelector('thead tr');
                                if (topRow && headers.length > 0) {
                                    const topHeaders = Array.from(topRow.querySelectorAll('th')).slice(0, 5);
                                    tableSignature = topHeaders.map(h => h.textContent.trim()).join('|') + '|' + headers.length;
                                } else if (headers.length > 0) {
                                    tableSignature = headers.length.toString();
                                }
                                
                                // If signature changed or table not enhanced, re-enhance
                                if (headers.length > 0 && 
                                    (spreadsheet.dataset.enhanced !== 'true' || 
                                     window.globalPricesState.lastTableSignature !== tableSignature)) {
                                    setTimeout(function() {
                                        enhanceTable();
                                    }, 100);
                                }
                            }
                        }
                    });
                    window.globalPricesMutationObserver.observe(document.body, { 
                        childList: true, 
                        subtree: true 
                    });
                }
                
                // Also try to enhance on next tick
                setTimeout(function() {
                    tryEnhance();
                }, 50);
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
    
    @dash_app.callback(
        Output('download-global-prices-data-table-csv', 'data'),
        Input('btn-export-global-prices-data-table-csv', 'n_clicks'),
        prevent_initial_call=True
    )
    def export_global_prices_table_data_to_csv(n_clicks):
        if n_clicks:
            # Load the original wide-format DataFrame and column metadata directly from the database
            df, _ = load_crude_prices_data()
            
            # Since the data is already in a wide format suitable for export,
            # we can directly send it as a CSV.
            # No need to filter columns or reconstruct from table_data/table_columns.
            
            # Fill None values with empty string for better CSV representation
            export_df = df.fillna('')
            
            return dcc.send_data_frame(export_df.to_csv, "global_crude_prices.csv", index=False)
        return None
