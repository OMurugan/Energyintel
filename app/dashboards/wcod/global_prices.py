"""
Global Crude Prices View
Monthly Crude Spot Prices ($/bbl) - Matching Energy Intelligence design
"""
from dash import dcc, html, Input, Output, callback, dash_table, State, clientside_callback, ClientsideFunction
import pandas as pd
import os

# Define data path
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'Global crude price')
CRUDE_PRICES_CSV = os.path.join(DATA_DIR, 'Crude Prices_data.csv')

                                    
def load_crude_prices_data():
    """Load and parse crude prices data from CSV (long format)."""
    # Read the CSV file
    encodings = ['utf-8', 'utf-16', 'utf-16le', 'latin-1']
    df = None
    last_error = None
    
    for enc in encodings:
        try:
            df = pd.read_csv(CRUDE_PRICES_CSV, encoding=enc)
            break
        except (UnicodeDecodeError, pd.errors.EmptyDataError) as exc:
            last_error = exc
            continue
    
    if df is None:
        raise last_error if last_error else Exception("Failed to read CSV file")
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    # Rename columns to standard names
    column_mapping = {
        'Year of date': 'Year',
        'Month of date': 'Month',
        'Day of date': 'Day',
        'Region1': 'Region',
        'crude_country': 'Country',
        'crude_name': 'Blend',
        'Avg. price': 'Price'
    }
    
    for old_col, new_col in column_mapping.items():
        if old_col in df.columns:
            df = df.rename(columns={old_col: new_col})
    
    # Clean and convert data
    df['Year'] = df['Year'].astype(str).str.strip()
    df['Month'] = df['Month'].astype(str).str.strip()
    df['Day'] = df['Day'].astype(str).str.strip()
    df['Region'] = df['Region'].astype(str).str.strip()
    df['Country'] = df['Country'].astype(str).str.strip()
    df['Blend'] = df['Blend'].astype(str).str.strip()
    df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
    
    # Calculate Quarter from Month
    month_to_quarter = {
        'January': 'Q1', 'February': 'Q1', 'March': 'Q1',
        'April': 'Q2', 'May': 'Q2', 'June': 'Q2',
        'July': 'Q3', 'August': 'Q3', 'September': 'Q3',
        'October': 'Q4', 'November': 'Q4', 'December': 'Q4'
    }
    df['Quarter'] = df['Month'].map(month_to_quarter)
    
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
    # Group by Year, Quarter, Month, and Day, then pivot
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
    
    # Sort by Year (descending), Quarter (descending), Month (descending), Day (ascending)
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
    columns = [
        {
            'name': ['Year', 'Year', 'Year', 'Year'],
            'id': 'Year',
            'type': 'text'
        },
        {
            'name': ['Quarter', 'Quarter', 'Quarter', 'Quarter'],
            'id': 'Quarter',
            'type': 'text'
        },
        {
            'name': ['Month', 'Month', 'Month', 'Month'],
            'id': 'Month',
            'type': 'text'
        },
        {
            'name': ['Day', 'Day', 'Day', 'Day'],
            'id': 'Day',
            'type': 'text'
        }
    ]
    
    # Group columns by region
    regions = {}
    for meta in column_metadata:
        region = meta['region']
        if region not in regions:
            regions[region] = []
        regions[region].append(meta)
    
    # Sort regions to match Tableau order (Africa, Asia first)
    region_order = ['Africa', 'Asia', 'Europe', 'FSU', 'Latin America', 'Middle East', 'North America', 'Oceania', 'Other']
    sorted_regions = sorted(regions.keys(), key=lambda x: (region_order.index(x) if x in region_order else 999, x))
    
    # Create hierarchical columns
    for region in sorted_regions:
        metas = regions[region]
        
        # Group by country within region
        countries = {}
        for meta in metas:
            country = meta['country']
            if country not in countries:
                countries[country] = []
            countries[country].append(meta)
        
        # Create columns for each country-blend combination
        for country in sorted(countries.keys()):
            country_metas = countries[country]
            # Sort blends within country
            country_metas_sorted = sorted(country_metas, key=lambda x: x['blend'])
            for meta in country_metas_sorted:
                columns.append({
                    'name': [region, country, meta['blend'], ''],
                    'id': meta['column_id'],
                    'type': 'numeric',
                    'format': {'specifier': '.2f'}
                })
    
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
                'marginBottom': '20px',
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
                style_table={
                    'overflowX': 'auto',
                    'overflowY': 'auto',
                    'border': '1px solid #dee2e6',
                    'fontFamily': 'Arial, sans-serif',
                    'fontSize': '12px',
                    'height': '800px',
                    'maxHeight': '800px'
                },
                style_cell={
                    'textAlign': 'left',
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
                    'color': '#1b365d'
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
                        'textAlign': 'left'
                    },
                    {
                        'if': {'column_id': 'Quarter'},
                        'fontWeight': 'bold',
                        'backgroundColor': '#f8f9fa',
                        'minWidth': '60px',
                        'textAlign': 'left'
                    },
                    {
                        'if': {'column_id': 'Month'},
                        'fontWeight': 'normal',
                        'minWidth': '100px',
                        'textAlign': 'left'
                    },
                    {
                        'if': {'column_id': 'Day'},
                        'fontWeight': 'normal',
                        'minWidth': '50px',
                        'textAlign': 'left'
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
        ], style={'margin': '0 auto', 'maxWidth': '100%'}),
        
        # Hidden div for clientside callback anchor
        html.Div(id='global-prices-enhancer-anchor', style={'display': 'none'}),
        
        # Clientside script for table enhancements
        html.Script(
            id='global-prices-clientside-script',
            children=''
        )
    ], style={'padding': '20px', 'backgroundColor': '#ffffff'})


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
#global-prices-table .dash-spreadsheet-container {
    cursor: pointer;
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
/* Default: Quarter and Day columns hidden */
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Day"] {
    display: none !important;
}
/* Show Quarter when year is expanded */
#global-prices-table .dash-spreadsheet-container.year-expanded th[data-dash-column="Quarter"],
#global-prices-table .dash-spreadsheet-container.year-expanded td[data-dash-column="Quarter"] {
    display: table-cell !important;
}
/* Hide Month and Day when quarter is collapsed (only when Quarter is visible) */
#global-prices-table .dash-spreadsheet-container.year-expanded.quarter-collapsed th[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container.year-expanded.quarter-collapsed th[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container.year-expanded.quarter-collapsed td[data-dash-column="Month"],
#global-prices-table .dash-spreadsheet-container.year-expanded.quarter-collapsed td[data-dash-column="Day"] {
    display: none !important;
}
/* Show Day when month is expanded (only if quarter is not collapsed and Quarter is visible) */
#global-prices-table .dash-spreadsheet-container.year-expanded.month-expanded:not(.quarter-collapsed) th[data-dash-column="Day"],
#global-prices-table .dash-spreadsheet-container.year-expanded.month-expanded:not(.quarter-collapsed) td[data-dash-column="Day"] {
    display: table-cell !important;
}
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Year"],
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Month"] {
    position: relative;
    cursor: pointer;
    white-space: nowrap;
}
/* Header toggle buttons - Common plus/minus in column headers */
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Year"] .year-header-toggle,
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Month"] .month-header-toggle,
#global-prices-table .dash-spreadsheet-container th[data-dash-column="Quarter"] .quarter-header-toggle {
    display: inline-block;
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
                    let isYearExpanded = false; // Default: Quarter hidden
                    let isMonthExpanded = false; // Default: Day hidden
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
                        const yearHeader = spreadsheet.querySelector('th[data-dash-column="Year"]');
                        if (!yearHeader) return;
                        
                        // Remove any existing toggle button
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
                        const monthHeader = spreadsheet.querySelector('th[data-dash-column="Month"]');
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
                        const quarterHeader = spreadsheet.querySelector('th[data-dash-column="Quarter"]');
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