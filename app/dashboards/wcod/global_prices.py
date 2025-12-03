"""
Global Crude Prices View
Monthly Crude Spot Prices ($/bbl) - Matching Energy Intelligence design
"""
from dash import dcc, html, Input, Output, callback, dash_table
import pandas as pd
import os

# Define data path
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'Prices')
CRUDE_PRICES_CSV = os.path.join(DATA_DIR, 'Crude Prices.csv')

def _read_prices_csv(skiprows, nrows=None):
    """Read the Crude Prices CSV trying encodings until one succeeds."""
    encodings = ['utf-16', 'utf-16le', 'utf-8']
    last_error = None
    for enc in encodings:
        try:
            return pd.read_csv(
                CRUDE_PRICES_CSV,
                sep='\t',
                skiprows=skiprows,
                nrows=nrows,
                encoding=enc,
                header=None,
                engine='python'
            )
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
    raise last_error  # Re-raise the last decoding error if all encodings fail

def load_crude_prices_data():
    """Load crude prices data from CSV file"""
    try:
        # Read header rows (rows 3, 4, 5: Region, Country, Crude Blend)
        # Skip first 2 rows (copyright headers), read next 3 rows for headers
        header_df = _read_prices_csv(skiprows=2, nrows=3)
        
        # Get data rows (starting from row 6, which is index 5 after skipping 2)
        data_df = _read_prices_csv(skiprows=5)
        
        # Extract header information
        region_row = header_df.iloc[0].values.tolist()  # Row 3: Regions
        country_row = header_df.iloc[1].values.tolist()  # Row 4: Countries
        crude_row = header_df.iloc[2].values.tolist()  # Row 5: Crude Blends
        
        # First two columns are empty (for Year and Month), so skip them
        region_row = region_row[2:] if len(region_row) > 2 else []
        country_row = country_row[2:] if len(country_row) > 2 else []
        crude_row = crude_row[2:] if len(crude_row) > 2 else []
        
        # Set column names for data
        num_price_cols = len(crude_row)
        data_df.columns = ['Year', 'Month'] + [f'Price_{i}' for i in range(num_price_cols)]
        
        # Clean data - remove rows where Year is missing
        data_df = data_df[data_df['Year'].notna()].copy()
        data_df = data_df[data_df['Year'] != ''].copy()
        
        # Convert Year to int
        data_df['Year'] = pd.to_numeric(data_df['Year'], errors='coerce')
        data_df = data_df[data_df['Year'].notna()].copy()
        data_df['Year'] = data_df['Year'].astype(int)
        
        # Convert price columns to numeric
        for i in range(num_price_cols):
            col = f'Price_{i}'
            if col in data_df.columns:
                data_df[col] = pd.to_numeric(data_df[col], errors='coerce')
        
        # Sort by Year (descending) and Month (descending - most recent first)
        # Use the exact month order from the image: September at top, then August, July, etc.
        month_order = ['September', 'August', 'July', 'June', 'May', 'April', 
                      'March', 'February', 'January', 'December', 'November', 'October']
        data_df['Month_Order'] = data_df['Month'].map({m: i for i, m in enumerate(month_order)})
        data_df = data_df.sort_values(['Year', 'Month_Order'], ascending=[False, True])
        data_df = data_df.drop('Month_Order', axis=1)
        
        return {
            'data': data_df,
            'regions': region_row,
            'countries': country_row,
            'crudes': crude_row
        }
    except Exception as e:
        print(f"Error loading crude prices data: {e}")
        import traceback
        traceback.print_exc()
        return {
            'data': pd.DataFrame(),
            'regions': [],
            'countries': [],
            'crudes': []
        }

# Load data on module import
CRUDE_PRICES_DATA = load_crude_prices_data()

def create_hierarchical_columns(regions, countries, crudes):
    """Create hierarchical column structure for DataTable with three levels: Region > Country > Crude"""
    columns = [
        {
            'name': ['', '', 'Year'],
            'id': 'Year',
            'type': 'text'
        },
        {
            'name': ['', '', 'Month'],
            'id': 'Month',
            'type': 'text'
        }
    ]
    
    for i in range(len(crudes)):
        region = str(regions[i]).strip() if i < len(regions) and pd.notna(regions[i]) else ''
        country = str(countries[i]).strip() if i < len(countries) and pd.notna(countries[i]) else ''
        crude = str(crudes[i]).strip() if i < len(crudes) and pd.notna(crudes[i]) else ''
        
        columns.append({
            'name': [region, country, crude],
            'id': f'Price_{i}',
            'type': 'numeric',
            'format': {'specifier': '.2f'}
        })
    
    return columns

def create_layout():
    """Create the Global Crude Prices layout matching Energy Intelligence design"""
    return html.Div([
        html.Div(id='global-prices-table-enhancer-anchor', style={'display': 'none'}),
        html.Div([
            html.H2(
                "Monthly Crude Spot Prices ($/bbl)",
                style={
                    'color': '#fe5000',
                    'textAlign': 'center',
                    'marginBottom': '15px',
                    'marginTop': '5px',
                    'fontSize': '20px',
                    'fontWeight': 'bold',
                    'fontFamily': 'Arial, sans-serif'
                }
            )
        ]),
        html.Div(
            id='global-prices-table-container',
            children=[],
            style={
                'border': '1px solid #dee2e6',
                'borderRadius': '0',
                'overflow': 'hidden',
                'boxShadow': '0 1px 3px rgba(0,0,0,0.1)',
                'backgroundColor': 'white'
            }
        )
    ], className='tab-content', style={'padding': '15px', 'backgroundColor': 'white'})

def register_callbacks(dash_app, server):
    """Register all callbacks for Global Crude Prices"""
    
    @callback(
        Output('global-prices-table-container', 'children'),
        Input('current-submenu', 'data')
    )
    def update_global_prices(submenu):
        """Update global prices table"""
        if submenu != 'global-prices':
            return html.Div()
        
        if CRUDE_PRICES_DATA['data'].empty:
            return html.Div(
                "No data available",
                style={'padding': '20px', 'textAlign': 'center', 'color': '#666'}
            )
        
        df = CRUDE_PRICES_DATA['data'].copy()
        regions = CRUDE_PRICES_DATA['regions']
        countries = CRUDE_PRICES_DATA['countries']
        crudes = CRUDE_PRICES_DATA['crudes']
        
        # Create hierarchical columns
        columns = create_hierarchical_columns(regions, countries, crudes)
        
        # Prepare table data - exactly like the image
        table_data = []
        prev_year = None
        
        for _, row in df.iterrows():
            record = {
                'Year': '',
                'Month': row['Month'] if pd.notna(row['Month']) else ''
            }
            
            # Show year only once per year group (like in the image)
            current_year = int(row['Year']) if pd.notna(row['Year']) else None
            if current_year != prev_year:
                record['Year'] = str(current_year) if current_year else ''
                prev_year = current_year
            else:
                record['Year'] = ''
            
            # Add price columns
            for i in range(len(crudes)):
                col_id = f'Price_{i}'
                value = row[col_id] if col_id in row else None
                if pd.isna(value) or value is None or value == '':
                    record[col_id] = ''
                else:
                    record[col_id] = float(value)
            
            table_data.append(record)
        
        # Create DataTable with exact styling from image
        table = dash_table.DataTable(
            id='global-prices-table',
            columns=columns,
            data=table_data,
            style_table={
                'overflowX': 'auto',
                'overflowY': 'auto',
                'border': 'none',
                'borderRadius': '0',
                'backgroundColor': 'white',
                'width': '100%',
                'minWidth': '100%',
                'fontFamily': 'Arial, sans-serif',
                'margin': '0 auto'
            },
            style_cell={
                'textAlign': 'center',
                'padding': '4px 8px',
                'fontSize': '12px',
                'fontFamily': 'Arial, sans-serif',
                'border': '1px solid #dee2e6',
                'whiteSpace': 'nowrap',
                'height': '30px',
                'minWidth': '70px',
                'maxWidth': '90px',
                'color': '#333333',
                'backgroundColor': 'white'
            },
            style_header={
                'backgroundColor': '#f8f9fa',
                'fontWeight': 'bold',
                'fontSize': '11px',
                'fontFamily': 'Arial, sans-serif',
                'border': '1px solid #dee2e6',
                'color': '#333333',
                'textAlign': 'center',
                'padding': '6px 8px'
            },
            style_cell_conditional=[
                {
                    'if': {'column_id': 'Year'},
                    'textAlign': 'left',
                    'fontWeight': 'bold',
                    'backgroundColor': '#f8f9fa',
                    'minWidth': '60px',
                    'maxWidth': '60px'
                },
                {
                    'if': {'column_id': 'Month'},
                    'textAlign': 'left',
                    'fontWeight': 'bold',
                    'minWidth': '100px',
                    'maxWidth': '100px'
                }
            ],
            style_data={
                'border': '1px solid #dee2e6',
                'backgroundColor': 'white'
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#f8f9fa'
                },
                {
                    'if': {'filter_query': '{Year} != ""'},
                    'backgroundColor': '#e9ecef'
                },
                {
                    'if': {'filter_query': '{Year} != ""'},
                    'column_id': 'Year',
                    'backgroundColor': '#e9ecef'
                },
                {
                    'if': {'filter_query': '{Year} != ""'},
                    'column_id': 'Month',
                    'backgroundColor': '#e9ecef'
                }
            ],
            fixed_rows={'headers': True},
            page_action='none',
            sort_action='none',
            filter_action='none',
            merge_duplicate_headers=True,
            css=[
                {
                    'selector': '.dash-spreadsheet-container',
                    'rule': 'font-family: Arial, sans-serif;'
                },
                {
                    'selector': '.dash-header',
                    'rule': 'background-color: #f8f9fa; border: 1px solid #dee2e6;'
                },
                {
                    'selector': '.dash-cell',
                    'rule': 'border: 1px solid #dee2e6;'
                }
            ]
        )
        
        return table

    # Clientside callback for interactive features
    dash_app.clientside_callback(
        """
        function(_id) {
            try {
                const TABLE_ID = 'global-prices-table';
                const STYLE_ID = 'global-prices-table-selection-css';
                const LABEL_COLUMNS = ['Year', 'Month'];

                function ensureStyle() {
                    if (document.getElementById(STYLE_ID)) {
                        return;
                    }
                    const style = document.createElement('style');
                    style.id = STYLE_ID;
                    style.type = 'text/css';
                    style.innerHTML = `
#global-prices-table .dash-spreadsheet-container {
    cursor: pointer;
    user-select: none;
}
#global-prices-table .dash-spreadsheet-container th {
    cursor: pointer;
    transition: background-color 0.15s ease;
}
#global-prices-table .dash-spreadsheet-container th:hover {
    background-color: #f0f0f0 !important;
}
#global-prices-table .dash-spreadsheet-container td {
    cursor: pointer;
    transition: opacity 0.2s ease-in-out, background-color 0.15s ease;
}
#global-prices-table .dash-spreadsheet-container.global-prices-selection-active td:not([data-dash-column="Year"]):not([data-dash-column="Month"]):not(.global-prices-row-selected):not(.global-prices-column-selected):not(.global-prices-cell-selected) {
    opacity: 0.15;
    background-color: #ffffff !important;
}
#global-prices-table .dash-spreadsheet-container.global-prices-selection-active th:not(.global-prices-column-header-selected) {
    opacity: 0.2;
    background-color: #ffffff !important;
}
#global-prices-table .dash-spreadsheet-container.global-prices-selection-active th.global-prices-column-header-selected {
    opacity: 1 !important;
}
#global-prices-table .dash-spreadsheet-container.global-prices-selection-active td.global-prices-cell-selected,
#global-prices-table .dash-spreadsheet-container.global-prices-selection-active td.global-prices-row-selected,
#global-prices-table .dash-spreadsheet-container.global-prices-selection-active td.global-prices-column-selected {
    opacity: 1 !important;
}
#global-prices-table .dash-spreadsheet-container td.global-prices-cell-selected {
    background-color: #e3f2fd !important;
    box-shadow: inset 0 0 0 2px #1976d2 !important;
    font-weight: 600;
    color: #0d47a1 !important;
    z-index: 1;
    position: relative;
}
#global-prices-table .dash-spreadsheet-container td.global-prices-row-selected {
    background-color: #e8f5e9 !important;
}
#global-prices-table .dash-spreadsheet-container td.global-prices-column-selected {
    background-color: #e8f5e9 !important;
}
#global-prices-table .dash-spreadsheet-container th.global-prices-column-header-selected {
    background-color: #c8e6c9 !important;
    font-weight: 600;
    color: #1b5e20 !important;
}
#global-prices-table .dash-spreadsheet-container td.global-prices-row-label-selected {
    font-weight: 600;
    color: #1b5e20 !important;
    background-color: #c8e6c9 !important;
}
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Year"]:hover,
#global-prices-table .dash-spreadsheet-container td[data-dash-column="Month"]:hover {
    background-color: #f5f5f5 !important;
}
                    `;
                    document.head.appendChild(style);
                }

                function resetSelection(spreadsheet) {
                    if (!spreadsheet) {
                        return;
                    }
                    spreadsheet.querySelectorAll('.global-prices-cell-selected').forEach(function(cell) {
                        cell.classList.remove('global-prices-cell-selected');
                    });
                    spreadsheet.querySelectorAll('.global-prices-row-selected').forEach(function(cell) {
                        cell.classList.remove('global-prices-row-selected');
                    });
                    spreadsheet.querySelectorAll('.global-prices-column-selected').forEach(function(cell) {
                        cell.classList.remove('global-prices-column-selected');
                    });
                    spreadsheet.querySelectorAll('.global-prices-column-header-selected').forEach(function(header) {
                        header.classList.remove('global-prices-column-header-selected');
                    });
                    spreadsheet.querySelectorAll('.global-prices-row-label-selected').forEach(function(cell) {
                        cell.classList.remove('global-prices-row-label-selected');
                    });
                }

                function clearSelection(spreadsheet) {
                    if (!spreadsheet) {
                        return;
                    }
                    resetSelection(spreadsheet);
                    spreadsheet.classList.remove('global-prices-selection-active');
                    spreadsheet.dataset.selectedKey = '';
                }

                function highlightRow(spreadsheet, rowIndex) {
                    const cells = spreadsheet.querySelectorAll('td[data-dash-row=\"' + rowIndex + '\"]');
                    cells.forEach(function(cell) {
                        const colId = cell.getAttribute('data-dash-column');
                        if (LABEL_COLUMNS.indexOf(colId) === -1) {
                            cell.classList.add('global-prices-row-selected');
                        } else {
                            cell.classList.add('global-prices-row-label-selected');
                        }
                    });
                }

                function highlightColumn(spreadsheet, columnId) {
                    if (LABEL_COLUMNS.indexOf(columnId) !== -1) {
                        return; // Don't highlight Year/Month columns
                    }
                    
                    // Find the bottom header cell with this column ID
                    const bottomHeader = spreadsheet.querySelector('th[data-dash-column=\"' + columnId + '\"]');
                    if (bottomHeader) {
                        // Get column index from bottom header
                        const headerRows = spreadsheet.querySelectorAll('thead tr');
                        if (headerRows.length > 0) {
                            const lastRow = headerRows[headerRows.length - 1];
                            const bottomCells = Array.from(lastRow.querySelectorAll('th'));
                            const colIndex = bottomCells.indexOf(bottomHeader);
                            
                            // Highlight all header cells in this column (for hierarchical headers: Region, Country, Crude)
                            if (colIndex >= 0) {
                                headerRows.forEach(function(row) {
                                    const cells = Array.from(row.querySelectorAll('th'));
                                    if (colIndex < cells.length) {
                                        cells[colIndex].classList.add('global-prices-column-header-selected');
                                    }
                                });
                            }
                        } else {
                            // Fallback: just highlight the bottom header
                            bottomHeader.classList.add('global-prices-column-header-selected');
                        }
                    }
                    
                    // Highlight all data cells in this column
                    const cells = spreadsheet.querySelectorAll('td[data-dash-column=\"' + columnId + '\"]');
                    cells.forEach(function(cell) {
                        cell.classList.add('global-prices-column-selected');
                    });
                }

                function highlightMultipleColumns(spreadsheet, columnIds) {
                    // Highlight multiple columns (for Region/Country selection)
                    columnIds.forEach(function(columnId) {
                        highlightColumn(spreadsheet, columnId);
                    });
                    
                    // Also highlight parent Region header if this is a Country selection
                    highlightParentRegionHeader(spreadsheet, columnIds);
                }

                function highlightParentRegionHeader(spreadsheet, columnIds) {
                    // When highlighting multiple columns (Country selection), also highlight parent Region header
                    if (columnIds.length === 0) {
                        return;
                    }
                    
                    const headerRows = spreadsheet.querySelectorAll('thead tr');
                    if (headerRows.length < 3) {
                        return; // Need at least 3 rows (Region, Country, Crude)
                    }
                    
                    // Get the Region row (first row, index 0)
                    const regionRow = headerRows[0];
                    const regionCells = Array.from(regionRow.querySelectorAll('th'));
                    
                    // Get column indices for all selected columns (from bottom row)
                    const lastRow = headerRows[headerRows.length - 1];
                    const bottomCells = Array.from(lastRow.querySelectorAll('th'));
                    const selectedIndices = [];
                    
                    columnIds.forEach(function(columnId) {
                        const bottomHeader = spreadsheet.querySelector('th[data-dash-column=\"' + columnId + '\"]');
                        if (bottomHeader) {
                            const colIndex = bottomCells.indexOf(bottomHeader);
                            if (colIndex >= 0) {
                                selectedIndices.push(colIndex);
                            }
                        }
                    });
                    
                    if (selectedIndices.length === 0) {
                        return;
                    }
                    
                    // Find the Region header that spans these columns
                    // Account for Year and Month columns (first 2 columns in region row)
                    let currentCol = 0;
                    for (let i = 0; i < regionCells.length; i++) {
                        const cell = regionCells[i];
                        const colspan = parseInt(cell.getAttribute('colspan') || '1', 10);
                        const cellStart = currentCol;
                        const cellEnd = currentCol + colspan - 1;
                        
                        // Skip Year and Month columns (first 2 columns)
                        if (cellEnd < 2) {
                            currentCol += colspan;
                            continue;
                        }
                        
                        // Adjust for Year/Month columns - Region cells start from index 2
                        const regionCellStart = Math.max(2, cellStart);
                        const regionCellEnd = cellEnd;
                        
                        // Check if any selected column falls within this region cell
                        const hasSelectedColumn = selectedIndices.some(function(idx) {
                            return idx >= regionCellStart && idx <= regionCellEnd;
                        });
                        
                        if (hasSelectedColumn) {
                            // Check if ALL selected columns are within this region cell
                            const allInRegion = selectedIndices.every(function(idx) {
                                return idx >= regionCellStart && idx <= regionCellEnd;
                            });
                            
                            if (allInRegion) {
                                // All selected columns are under this Region, highlight it
                                cell.classList.add('global-prices-column-header-selected');
                                break;
                            }
                        }
                        
                        currentCol += colspan;
                    }
                }

                function getHeaderRowIndex(headerCell) {
                    const headerRow = headerCell.closest('tr');
                    if (!headerRow) {
                        return -1;
                    }
                    const headerRows = Array.from(headerRow.parentElement.querySelectorAll('tr'));
                    return headerRows.indexOf(headerRow);
                }

                function getColumnRangeForHeader(headerCell, spreadsheet) {
                    const headerRow = headerCell.closest('tr');
                    if (!headerRow) {
                        return [];
                    }
                    
                    const allCells = Array.from(headerRow.querySelectorAll('th'));
                    const clickedIndex = allCells.indexOf(headerCell);
                    
                    if (clickedIndex < 0) {
                        return [];  
                    }
                    
                    // Skip Year and Month columns (first 2 columns)
                    if (clickedIndex < 2) {
                        return [];
                    }
                    
                    // Get all header rows
                    const headerRows = spreadsheet.querySelectorAll('thead tr');
                    if (headerRows.length === 0) {
                        return [];
                    }
                    
                    const lastRow = headerRows[headerRows.length - 1];
                    const bottomCells = Array.from(lastRow.querySelectorAll('th'));
                    const columnIds = [];
                    
                    // Calculate the starting position of the clicked cell in the bottom row
                    let currentBottomCol = 0;
                    for (let i = 0; i < clickedIndex; i++) {
                        const cell = allCells[i];
                        const cellColspan = parseInt(cell.getAttribute('colspan') || '1', 10);
                        currentBottomCol += cellColspan;
                    }
                    
                    // Get the colspan of the clicked cell
                    let clickedColspan = parseInt(headerCell.getAttribute('colspan') || '1', 10);
                    
                    // If colspan is 1, we need to find where this header ends by looking at the next header
                    if (clickedColspan === 1) {
                        // Look ahead to find the next non-empty header cell
                        for (let k = clickedIndex + 1; k < allCells.length; k++) {
                            const nextCell = allCells[k];
                            const nextCellText = (nextCell.textContent || '').trim();
                            
                            // If we find a cell with text (next header), calculate where it starts
                            if (nextCellText !== '') {
                                let nextStartCol = 0;
                                for (let m = 0; m < k; m++) {
                                    const prevCell = allCells[m];
                                    const prevColspan = parseInt(prevCell.getAttribute('colspan') || '1', 10);
                                    nextStartCol += prevColspan;
                                }
                                clickedColspan = nextStartCol - currentBottomCol;
                                break;
                            }
                        }
                        
                        // If we still don't have a valid colspan, use all remaining columns
                        if (clickedColspan === 1) {
                            clickedColspan = bottomCells.length - currentBottomCol;
                        }
                    }
                    
                    // Get all column IDs that fall under this header cell
                    for (let j = 0; j < clickedColspan; j++) {
                        const bottomColIndex = currentBottomCol + j;
                        
                        // Make sure we don't go beyond bottom row length
                        if (bottomColIndex >= bottomCells.length) {
                            break;
                        }
                        
                        // Skip Year and Month columns (first 2 columns)
                        if (bottomColIndex >= 2) {
                            const columnId = bottomCells[bottomColIndex].getAttribute('data-dash-column');
                            if (columnId && LABEL_COLUMNS.indexOf(columnId) === -1) {
                                // Avoid duplicates
                                if (columnIds.indexOf(columnId) === -1) {
                                    columnIds.push(columnId);
                                }
                            }
                        }
                    }
                    
                    return columnIds;
                }

                function getColumnIdFromHeaderCell(headerCell, spreadsheet) {
                    // First try to get direct column ID
                    let columnId = headerCell.getAttribute('data-dash-column');
                    if (columnId) {
                        return columnId;
                    }
                    
                    // For hierarchical headers, find column index and get ID from bottom row
                    const headerRow = headerCell.closest('tr');
                    if (!headerRow) {
                        return null;
                    }
                    
                    const allCells = Array.from(headerRow.querySelectorAll('th'));
                    const colIndex = allCells.indexOf(headerCell);
                    
                    if (colIndex < 0) {
                        return null;
                    }
                    
                    // Get the bottom header row (has actual column IDs)
                    const headerRows = spreadsheet.querySelectorAll('thead tr');
                    if (headerRows.length > 0) {
                        const lastRow = headerRows[headerRows.length - 1];
                        const bottomCells = Array.from(lastRow.querySelectorAll('th'));
                        if (colIndex >= 0 && colIndex < bottomCells.length) {
                            columnId = bottomCells[colIndex].getAttribute('data-dash-column');
                            return columnId;
                        }
                    }
                    
                    return null;
                }

                function enhanceTable() {
                    const table = document.getElementById(TABLE_ID);
                    if (!table) {
                        return;
                    }
                    let spreadsheet = table.querySelector('.dash-spreadsheet-container');
                    if (!spreadsheet) {
                        return;
                    }
                    
                    // If already enhanced, skip (will be reset by MutationObserver if table re-renders)
                    if (spreadsheet.dataset.globalPricesEnhanced === 'true') {
                        return;
                    }
                    
                    spreadsheet.dataset.globalPricesEnhanced = 'true';
                    spreadsheet.dataset.selectedKey = '';

                    spreadsheet.addEventListener('click', function(event) {
                        event.preventDefault();
                        event.stopPropagation();
                        
                        // Check if clicking on column header (handle hierarchical headers: Region, Country, Crude)
                        const headerCell = event.target.closest('th');
                        
                        if (headerCell) {
                            const headerRowIndex = getHeaderRowIndex(headerCell);
                            const headerRows = spreadsheet.querySelectorAll('thead tr');
                            const totalHeaderRows = headerRows.length;
                            
                            // Get column index (accounting for Year/Month in first 2 columns)
                            const headerRow = headerCell.closest('tr');
                            const allCells = Array.from(headerRow.querySelectorAll('th'));
                            const clickedIndex = allCells.indexOf(headerCell);
                            
                            // Skip Year and Month columns
                            if (clickedIndex < 2) {
                                return;
                            }
                            
                            // Determine if this is a Region, Country, or Crude header
                            // Row 0 = Region, Row 1 = Country, Row 2 (last) = Crude
                            let selectionKey = '';
                            let columnIds = [];
                            
                            // Check which header row this is
                            // In Dash DataTable with hierarchical headers:
                            // - First row (index 0) is usually Region
                            // - Second row (index 1) is usually Country  
                            // - Last row (index totalHeaderRows-1) is Crude
                            const isLastRow = (headerRowIndex === totalHeaderRows - 1);
                            
                            if (!isLastRow && totalHeaderRows >= 3) {
                                // Clicked on Region or Country header (not the bottom row)
                                columnIds = getColumnRangeForHeader(headerCell, spreadsheet);
                                if (columnIds.length > 0) {
                                    const headerText = (headerCell.textContent || '').trim();
                                    if (headerRowIndex === 0) {
                                        selectionKey = 'region-' + headerText + '-' + clickedIndex;
                                    } else {
                                        selectionKey = 'country-' + headerText + '-' + clickedIndex;
                                    }
                                }
                            } else {
                                // Clicked on Crude header (bottom row) or single column
                                const columnId = getColumnIdFromHeaderCell(headerCell, spreadsheet);
                                if (columnId && LABEL_COLUMNS.indexOf(columnId) === -1) {
                                    columnIds = [columnId];
                                    selectionKey = 'column-' + columnId;
                                }
                            }
                            
                            if (columnIds.length > 0) {
                                if (spreadsheet.dataset.selectedKey === selectionKey) {
                                    clearSelection(spreadsheet);
                                    return;
                                }
                                spreadsheet.dataset.selectedKey = selectionKey;
                                spreadsheet.classList.add('global-prices-selection-active');
                                resetSelection(spreadsheet);
                                
                                if (columnIds.length === 1) {
                                    highlightColumn(spreadsheet, columnIds[0]);
                                } else {
                                    highlightMultipleColumns(spreadsheet, columnIds);
                                }
                                return;
                            }
                        }

                        // Handle data cell clicks
                        const cell = event.target.closest('td[data-dash-row]');
                        if (!cell) {
                            return;
                        }
                        
                        const columnId = cell.getAttribute('data-dash-column');
                        const rowIndex = cell.getAttribute('data-dash-row');
                        if (!columnId || rowIndex === null) {
                            return;
                        }

                        const rowKey = 'row-' + rowIndex;
                        const cellKey = rowIndex + '-' + columnId;

                        // If clicking on Year or Month column, select entire row
                        if (LABEL_COLUMNS.indexOf(columnId) !== -1) {
                            if (spreadsheet.dataset.selectedKey === rowKey) {
                                clearSelection(spreadsheet);
                                return;
                            }
                            spreadsheet.dataset.selectedKey = rowKey;
                            spreadsheet.classList.add('global-prices-selection-active');
                            resetSelection(spreadsheet);
                            highlightRow(spreadsheet, rowIndex);
                            return;
                        }

                        // If clicking on a data cell, select just that cell
                        if (spreadsheet.dataset.selectedKey === cellKey) {
                            clearSelection(spreadsheet);
                            return;
                        }

                        spreadsheet.dataset.selectedKey = cellKey;
                        spreadsheet.classList.add('global-prices-selection-active');
                        resetSelection(spreadsheet);
                        cell.classList.add('global-prices-cell-selected');
                    });
                }

                function applyEnhancements() {
                    ensureStyle();
                    enhanceTable();
                }

                // Use MutationObserver to re-apply enhancements when table is re-rendered
                if (!window.globalPricesTableObserver) {
                    window.globalPricesTableObserver = new MutationObserver(function(mutations) {
                        let shouldReapply = false;
                        mutations.forEach(function(mutation) {
                            if (mutation.addedNodes.length > 0) {
                                const table = document.getElementById(TABLE_ID);
                                if (table) {
                                    const spreadsheet = table.querySelector('.dash-spreadsheet-container');
                                    if (spreadsheet) {
                                        // Check if table was re-rendered (enhanced flag is missing or false)
                                        if (!spreadsheet.dataset.globalPricesEnhanced || 
                                            spreadsheet.dataset.globalPricesEnhanced === 'false') {
                                            shouldReapply = true;
                                        }
                                    }
                                }
                            }
                        });
                        if (shouldReapply) {
                            // Reset enhanced flag to allow re-application
                            const table = document.getElementById(TABLE_ID);
                            if (table) {
                                const spreadsheet = table.querySelector('.dash-spreadsheet-container');
                                if (spreadsheet) {
                                    spreadsheet.dataset.globalPricesEnhanced = 'false';
                                }
                            }
                            applyEnhancements();
                        }
                    });
                    window.globalPricesTableObserver.observe(document.body, { 
                        childList: true, 
                        subtree: true,
                        attributes: false
                    });
                }

                // Clear selection when clicking outside the table
                if (!window.globalPricesOutsideClickHandler) {
                    window.globalPricesOutsideClickHandler = function(event) {
                        const table = document.getElementById(TABLE_ID);
                        if (!table || table.contains(event.target)) {
                            return;
                        }
                        const spreadsheet = table.querySelector('.dash-spreadsheet-container');
                        if (spreadsheet && spreadsheet.classList.contains('global-prices-selection-active')) {
                            clearSelection(spreadsheet);
                        }
                    };
                    document.addEventListener('click', window.globalPricesOutsideClickHandler, true);
                }

                // Apply enhancements immediately
                applyEnhancements();
                
                // Also apply after a short delay to catch any delayed rendering
                setTimeout(applyEnhancements, 100);
                setTimeout(applyEnhancements, 500);
            } catch (error) {
                console.error('Global prices table enhancer error:', error);
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('global-prices-table-enhancer-anchor', 'children'),
        Input('global-prices-table-enhancer-anchor', 'id'),
        prevent_initial_call=False
    )