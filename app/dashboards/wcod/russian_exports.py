"""
Russian Exports by Terminal and Exporting Company View
Detailed Russian exports data
"""
from dash import html, Input, Output, callback, dash_table, dcc, State
import pandas as pd
import os
from core.data_helpers import execute_query


def get_year_columns_from_db():
    """Extract year columns dynamically from the database"""
    try:
        query = """
        SELECT DISTINCT yr AS "Year"
        FROM t_wcod_icoh_exports
        WHERE exportercountry = 'Russia'
        ORDER BY yr DESC
        """
        
        results = execute_query(query)
        if results:
            years = [str(row['Year']) for row in results if row.get('Year')]
            return years
        
        return []
    except Exception as e:
        # Fallback to default years if database query fails
        return ['2022', '2021', '2020', '2019', '2018', '2017', '2016', '2015', '2014', '2013', '2012', '2011', '2010', '2009', '2008', '2007', '2006']


def create_layout():
    """Create the Russian Exports layout"""
    # Build conditional styles for year columns (right-align numeric data)
    # Get year columns dynamically from database
    year_columns = get_year_columns_from_db()
    conditional_styles = [
        {
            'if': {'filter_query': '{Company} contains Total'},
            'backgroundColor': '#e8f4f8',
            'fontWeight': 'bold'
        },
        {
            'if': {'filter_query': '{Terminal, Country} = "Grand Total"'},
            'backgroundColor': '#d4edda',
            'fontWeight': 'bold',
            'color': '#155724'
        },
        # Striped table rows - even rows (light gray) for all columns EXCEPT Terminal, Country
        {
            'if': {'row_index': 'even'},
            'backgroundColor': '#f8f9fa'
        },
        # Striped table rows - odd rows (white) for all columns EXCEPT Terminal, Country
        {
            'if': {'row_index': 'odd'},
            'backgroundColor': '#ffffff'
        },
        # Terminal, Country column - always white background for merged cells (override striped pattern)
        # Apply to cells with values (first row of group)
        {
            'if': {
                'filter_query': '{Terminal, Country} != "" && {Terminal, Country} != null',
                'column_id': 'Terminal, Country'
            },
            'backgroundColor': '#ffffff',
            'borderBottom': 'none',
            'verticalAlign': 'top',
            'maxWidth': '100px',
            'width': '100px',
            'fontSize': '12px'
        },
        # Terminal, Country column - always white background for empty cells in merged group
        # Override the striped pattern to match the cell above
        {
            'if': {
                'filter_query': '{Terminal, Country} = ""',
                'column_id': 'Terminal, Country'
            },
            'backgroundColor': '#ffffff',
            'borderTop': 'none',
            'maxWidth': '100px',
            'width': '100px',
            'fontSize': '12px'
        },
        # Terminal, Country column - bold font weight and increased font size
        {
            'if': {
                'column_id': 'Terminal, Country'
            },
            'fontSize': '12px',
            'fontWeight': 'bold'
        },
        # Company column - bold font weight and increased font size
        {
            'if': {
                'column_id': 'Company'
            },
            'fontSize': '12px',
            'fontWeight': 'bold'
        },
        # Remove top border for all OTHER columns when Terminal, Country cell is empty (to create merged appearance)
        {
            'if': {
                'filter_query': '{Terminal, Country} = ""'
            },
            'borderTop': 'none'
        },
        # Remove top padding from first data row to eliminate space below header
        {
            'if': {
                'row_index': 0
            },
            'paddingTop': '0px',
        }
    ]
    # Add right-align, fontSize, and normal font weight for year columns
    for col in year_columns:
        conditional_styles.append({
            'if': {'column_id': col},
            'textAlign': 'right',
            'fontSize': '12px',
            'fontWeight': 'normal'
        })
    
    # Create header conditional styles for year columns to minimize whitespace
    header_conditional_styles = []
    for col in year_columns:
        header_conditional_styles.append({
            'if': {'column_id': col},
            'padding': '2px 8px',
            'lineHeight': '14px',
            'fontSize': '14px',
        })
    # Add header styles for Terminal, Country and Company columns
    header_conditional_styles.append({
        'if': {'column_id': 'Terminal, Country'},
        'fontSize': '14px',
    })
    header_conditional_styles.append({
        'if': {'column_id': 'Company'},
        'fontSize': '14px',
    })
    
    return html.Div([
        html.Div([
            html.H3("Russian Exports by Terminal and Exporting Company", 
                    style={'marginBottom': '0px', 'fontWeight': 'bold', 'color': '#ff6600', 'textAlign': 'center', 'fontSize': '21px'}),
            html.P("('000 b/d)", 
                   style={'marginTop': '0px', 'marginBottom': '20px', 'color': '#ff6600', 'textAlign': 'center', 'fontSize': '21px', 'fontWeight': 'normal'}),
        ]),
        # CSV Export components
        dcc.Download(id="download-russian-exports-csv"),
        # Store for year column sort order (True = descending, False = ascending)
        dcc.Store(id='year-column-sort-order', data=True),  # Default: descending (2022 → 2006)
        # Hidden button to trigger sort toggle from clientside callback
        html.Button(id='sort-year-columns-btn-hidden', style={'display': 'none'}),
        # Dummy output for clientside callback
        html.Div(id='russian-exports-dummy-sort', style={'display': 'none'}),
        html.Div([
            # Export button positioned above the table
            html.Div([
                html.Button("Export CSV", id='export-russian-exports-btn', n_clicks=0, style={
                    'backgroundColor': 'white',
                    'color': '#2c3e50',
                    'border': '1px solid #dee2e6', 
                    'padding': '6px 10px', 
                    'borderRadius': '4px', 
                    'cursor': 'pointer', 
                    'fontSize': '12px',
                    'marginBottom': '10px'
                })
            ], style={'display': 'flex', 'justifyContent': 'flex-end'}),
            dcc.Loading(
                id='loading-russian-exports-table',
                type='default',
                color='#ff6600',
                children=[
                    dash_table.DataTable(
                        id='russian-exports-table',
                        style_table={
                            'overflowX': 'auto',
                            'width': 'auto',
                            'minWidth': '100%',
                            'border': '1px solid #ddd'
                        },
                        style_cell={
                            'textAlign': 'left',
                            'padding': '2px 8px',
                            'fontSize': '12px',
                            'fontFamily': 'Lato',
                            'whiteSpace': 'normal',
                            'height': 'auto',
                            'minWidth': '80px',
                            'width': 'auto'
                        },
                        style_data_conditional=conditional_styles,
                        style_header={
                            'backgroundColor': 'white',
                            'fontWeight': 'bold',
                            'textAlign': 'center',
                            'border': '1px solid #ddd',
                            'color': '#1b365d',
                            'fontSize': '14px',
                            'height': '45px',
                            'verticalAlign': 'middle',
                        },
                        style_header_conditional=header_conditional_styles,
                        style_data={
                            'border': '1px solid #ddd',
                            'fontFamily': 'Lato',
                            'fontSize': '12px',
                            'fontStyle': 'normal',
                            'fontWeight': 'normal',
                            'textDecoration': 'none',
                            'color': 'rgb(27, 54, 93)',
                            'textAlign': 'left',
                            'padding': '8px',
                            'maxHeight': '60px'
                        },
                        fixed_rows={'headers': True},
                        fixed_columns={'headers': True, 'data': 2},
                        sort_action='native',
                        css=[{
                            "selector": "th",
                            "rule": "padding-right: 25px !important;"
                        }]
                    )
                ],
                style={'minHeight': '400px'}
            )
        ], style={'marginTop': '20px', 'width': '100%', 'overflowX': 'auto'}),
        html.Div([
            html.P("Source: Energy Intelligence. Data through August 2022.", 
                   style={'fontSize': '11px', 'fontStyle': 'italic', 'marginTop': '10px', 'color': '#1b365d', 'fontWeight': 'bold'}),
            html.P("Countries: Select jurisdictions are included under countries for data presentation purposes.", 
                   style={'fontSize': '11px', 'fontStyle': 'italic', 'marginTop': '5px', 'color': '#1b365d',})
        ])
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Russian Exports"""
    
    @dash_app.callback(
        [Output('russian-exports-table', 'data'),
         Output('russian-exports-table', 'columns'),
         Output('year-column-sort-order', 'data')],
        [Input('current-submenu', 'data'),
         Input('sort-year-columns-btn-hidden', 'n_clicks')],
        [State('year-column-sort-order', 'data')]
    )
    def update_russian_exports(submenu, sort_clicks, current_sort_order):
        """Update Russian exports table from database"""
        if submenu != 'russian-exports':
            return [], [], current_sort_order
        
        # Determine sort order: toggle if button was clicked, otherwise use stored value
        sort_descending = current_sort_order if current_sort_order is not None else True
        if sort_clicks is not None and sort_clicks > 0:
            # Toggle sort order
            sort_descending = not sort_descending
        
        try:
            # Query data from database
            query = """
            SELECT 
                concat(value1, ' ', exportercountry) AS "Terminal, Country",
                value2 AS "Company",
                source,
                yr AS "Year",
                datavalue AS "DataValue",
                'Source: Energy Intelligence' AS "Sourced",
                'COPYRIGHT &copy; 2001-2021 ENERGY INTELLIGENCE GROUP, INC. / ENERGY INTELLIGENCE GROUP (UK) LIMITED.' AS "Copyright"
            FROM t_wcod_icoh_exports
            WHERE exportercountry = 'Russia'
            """
            
            # Execute query and convert to DataFrame
            results = execute_query(query)
            raw = pd.DataFrame(results)
            
            if raw.empty:
                raise ValueError("No data returned from database")
            
            # Ensure we have required columns
            if 'Year' not in raw.columns or 'DataValue' not in raw.columns or 'Company' not in raw.columns:
                raise ValueError("Missing required columns: Year, DataValue, or Company")
            
            # Convert Year to int and DataValue to numeric
            raw['Year'] = pd.to_numeric(raw['Year'], errors='coerce')
            raw['DataValue'] = pd.to_numeric(raw['DataValue'], errors='coerce')
            
            # Remove rows with invalid data
            raw = raw[raw['Year'].notna() & raw['DataValue'].notna()].copy()
            
            # Pivot from long format to wide format
            # Group by Terminal/Country and Company, pivot Year values to columns
            df_pivot = raw.pivot_table(
                index=['Terminal, Country', 'Company'],
                columns='Year',
                values='DataValue',
                aggfunc='sum',
                fill_value=None
            ).reset_index()
            
            # Get year columns (all numeric columns except Terminal, Country and Company)
            # After pivot, year columns might be integers or floats
            year_columns = []
            for col in df_pivot.columns:
                if col not in ['Terminal, Country', 'Company']:
                    try:
                        # Try to convert to int (year)
                        year_val = int(float(col))
                        if 1900 <= year_val <= 2100:  # Reasonable year range
                            year_columns.append(year_val)
                    except (ValueError, TypeError):
                        pass
            
            # Sort years based on sort order (descending = True means newest first)
            year_columns = sorted(year_columns, reverse=sort_descending)
            year_columns_str = [str(col) for col in year_columns]
            
            # Convert year column names in pivot table to strings for consistency
            column_mapping = {}
            for col in df_pivot.columns:
                if col not in ['Terminal, Country', 'Company']:
                    try:
                        year_val = int(float(col))
                        if 1900 <= year_val <= 2100:
                            column_mapping[col] = str(year_val)
                    except (ValueError, TypeError):
                        pass
            
            if column_mapping:
                df_pivot = df_pivot.rename(columns=column_mapping)
            
            # Reorder columns: Terminal, Country, Company, then years
            df = df_pivot[['Terminal, Country', 'Company'] + year_columns_str].copy()
            
            # Sort by Terminal, Country (ascending) and Company (custom order to match live source)
            # Company ordering: Regular companies in descending alphabetical order, then Grand Total last
            # This matches the live source at: https://dataanalytics.energyintel.com/t/EIProd/views/RussianExports/RussianExports
            # Create a custom sort key for Company column
            def company_sort_key(company):
                if pd.isna(company) or company == '':
                    return (1, '')  # Empty companies last within each group
                else:
                    return (0, company)  # Regular companies in descending alphabetical order
            
            df['_sort_key'] = df['Company'].apply(company_sort_key)
            df = df.sort_values(['Terminal, Country', '_sort_key'], ascending=[True, True]).reset_index(drop=True)
            df = df.drop('_sort_key', axis=1)
            
            # For regular companies, sort in descending order within each terminal
            df_final = []
            current_terminal = None
            current_group = []
            
            for idx, row in df.iterrows():
                terminal = row['Terminal, Country']
                
                if terminal != current_terminal and current_terminal is not None:
                    # Process the previous group - sort companies in descending order
                    if current_group:
                        current_group.sort(key=lambda x: str(x['Company']), reverse=True)
                        df_final.extend(current_group)
                    current_group = []
                
                current_terminal = terminal
                current_group.append(row.to_dict())
            
            # Process the last group
            if current_group:
                current_group.sort(key=lambda x: str(x['Company']), reverse=True)
                df_final.extend(current_group)
            
            # Convert back to DataFrame
            df = pd.DataFrame(df_final)
            
            # Add single Grand Total row at the bottom (sums ALL exports across ALL terminals/companies)
            grand_total_row = {'Terminal, Country': 'Grand Total', 'Company': ''}
            for year_col in year_columns_str:
                year_sum = pd.to_numeric(df[year_col], errors='coerce').sum()
                grand_total_row[year_col] = year_sum if not pd.isna(year_sum) else None
            
            # Append Grand Total row to the end of the dataframe
            df = pd.concat([df, pd.DataFrame([grand_total_row])], ignore_index=True)
            
            # Handle Terminal, Country merging (clear duplicate values)
            terminal_col = 'Terminal, Country'
            prev_terminal = None
            
            for idx in df.index:
                current_terminal = df.loc[idx, terminal_col]
                if pd.isna(current_terminal) or current_terminal is None:
                    current_terminal = ''
                else:
                    current_terminal = str(current_terminal).strip()
                
                # If current terminal matches previous, clear it (except for first occurrence)
                if current_terminal == prev_terminal and prev_terminal != '':
                    df.loc[idx, terminal_col] = ''
                else:
                    prev_terminal = current_terminal
            
            # Convert year columns to numeric
            for col in year_columns_str:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Store empty string values for Terminal, Country
            terminal_values = df[terminal_col].copy()
            # Convert other columns to None where null
            for col in df.columns:
                if col != terminal_col:
                    df[col] = df[col].where(pd.notnull(df[col]), None)
            # Restore Terminal, Country values (including empty strings)
            df[terminal_col] = terminal_values
            
            table_data = df.to_dict('records')
            
            # Create columns configuration
            columns = []
            for col in df.columns:
                col_str = str(col)
                col_config = {
                    'name': col_str,
                    'id': col_str
                }
                
                # Set specific widths for Terminal, Country and Company columns
                if col_str == 'Terminal, Country':
                    col_config['width'] = '100px'
                elif col_str == 'Company':
                    col_config['width'] = '500px'
                
                if col_str in year_columns_str:
                    col_config['type'] = 'numeric'
                    col_config['format'] = {'specifier': '.0f'}
                
                columns.append(col_config)
            
            return table_data, columns, sort_descending
            
        except Exception as e:
            error_data = [{'Error': f'Failed to load data: {str(e)}'}]
            error_columns = [{'name': 'Error', 'id': 'Error'}]
            return error_data, error_columns, current_sort_order
    
    # Add sort icons to Company column cells using clientside callback
    dash_app.clientside_callback(
        """
        function(data) {
            setTimeout(function() {
                // Find all Company column cells
                const companyCells = document.querySelectorAll('#russian-exports-table .dash-cell[data-dash-column="Company"]');
                
                companyCells.forEach(function(cell) {
                    // Skip if already has sort icon
                    if (cell.querySelector('.year-sort-icon')) {
                        return;
                    }
                    
                    // Skip empty cells
                    const cellText = (cell.textContent || '').trim();
                    if (!cellText || cellText === '') {
                        return;
                    }
                    
                    // Make cell position relative for absolute positioning of icon
                    cell.style.position = 'relative';
                    cell.style.paddingRight = '30px'; // Make room for icon
                    
                    // Create sort icon
                    const sortIcon = document.createElement('div');
                    sortIcon.className = 'year-sort-icon';
                    sortIcon.style.position = 'absolute';
                    sortIcon.style.right = '8px';
                    sortIcon.style.top = '50%';
                    sortIcon.style.transform = 'translateY(-50%)';
                    sortIcon.style.width = '18px';
                    sortIcon.style.height = '18px';
                    sortIcon.style.cursor = 'pointer';
                    sortIcon.style.opacity = '0';
                    sortIcon.style.transition = 'opacity 0.2s ease';
                    sortIcon.style.zIndex = '10';
                    sortIcon.title = 'Click to toggle year column order (Descending ↔ Ascending)';
                    
                    // Add SVG icon (double arrow for horizontal sort)
                    sortIcon.innerHTML = `
                        <svg fill="#666" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: 100%;">
                            <path d="M6.99 11L3 15l3.99 4v-3H14v-2H6.99v-3zM21 9l-3.99-4v3H10v2h7.01v3L21 9z"/>
                        </svg>
                    `;
                    
                    // Hover effects
                    sortIcon.onmouseover = function() {
                        sortIcon.style.opacity = '1';
                        sortIcon.style.backgroundColor = '#e6f3ff';
                        sortIcon.style.borderRadius = '3px';
                        sortIcon.querySelector('svg').style.fill = '#ff6600';
                    };
                    
                    sortIcon.onmouseout = function() {
                        sortIcon.style.opacity = '0';
                        sortIcon.style.backgroundColor = '';
                        sortIcon.querySelector('svg').style.fill = '#666';
                    };
                    
                    // Click handler - trigger the hidden button
                    sortIcon.onclick = function(e) {
                        e.stopPropagation();
                        e.preventDefault();
                        const btn = document.getElementById('sort-year-columns-btn-hidden');
                        if (btn) {
                            btn.click();
                        }
                    };
                    
                    cell.appendChild(sortIcon);
                    
                    // Show icon on cell hover
                    cell.onmouseover = function() {
                        sortIcon.style.opacity = '1';
                    };
                    
                    cell.onmouseout = function() {
                        sortIcon.style.opacity = '0';
                    };
                });
                
            }, 500);
            return '';
        }
        """,
        Output('russian-exports-dummy-sort', 'children'),
        Input('russian-exports-table', 'data'),
        prevent_initial_call=False
    )
    
    # CSV Export Callback
    @dash_app.callback(
        Output('download-russian-exports-csv', 'data'),
        Input('export-russian-exports-btn', 'n_clicks'),
        State('russian-exports-table', 'data'),
        State('russian-exports-table', 'columns'),
        prevent_initial_call=True
    )
    def export_russian_exports_csv(n_clicks, table_data, table_columns):
        """Export Russian Exports table data to CSV"""
        if n_clicks and table_data and table_columns:
            try:
                # Convert table data to DataFrame
                df = pd.DataFrame(table_data)
                
                if df.empty:
                    # Return empty CSV if no data
                    empty_df = pd.DataFrame(columns=['Terminal_Country', 'Company'])
                    filename = "Russian_Exports_by_Terminal_and_Company.csv"
                    return dcc.send_data_frame(empty_df.to_csv, filename=filename, index=False)
                
                # Clean up column names for CSV (replace spaces and special characters)
                column_mapping = {}
                for col in df.columns:
                    clean_name = str(col).replace(', ', '_').replace(' ', '_').replace('(', '').replace(')', '').replace("'", '')
                    column_mapping[col] = clean_name
                
                df_export = df.rename(columns=column_mapping)
                
                # Handle the merged Terminal, Country column - fill empty cells with the previous non-empty value
                terminal_col = 'Terminal_Country'
                if terminal_col in df_export.columns:
                    # Forward fill the Terminal, Country values to handle merged cells (except for Grand Total row)
                    current_terminal = None
                    for idx in df_export.index:
                        cell_value = df_export.loc[idx, terminal_col]
                        if pd.isna(cell_value) or cell_value == '' or cell_value is None:
                            # Don't fill Grand Total row
                            if current_terminal is not None and current_terminal != 'Grand Total':
                                df_export.loc[idx, terminal_col] = current_terminal
                        else:
                            current_terminal = str(cell_value).strip()
                
                # Sort by Terminal_Country (ascending) and Company (descending), with Grand Total at the end
                if 'Terminal_Country' in df_export.columns and 'Company' in df_export.columns:
                    # Separate Grand Total row from regular data
                    grand_total_rows = df_export[df_export['Terminal_Country'] == 'Grand Total'].copy()
                    regular_rows = df_export[df_export['Terminal_Country'] != 'Grand Total'].copy()
                    
                    if not regular_rows.empty:
                        # Sort regular rows by terminal and company (descending)
                        df_final_csv = []
                        current_terminal = None
                        current_group = []
                        
                        # Sort by terminal first
                        regular_rows = regular_rows.sort_values(['Terminal_Country'], ascending=[True]).reset_index(drop=True)
                        
                        for idx, row in regular_rows.iterrows():
                            terminal = row['Terminal_Country']
                            
                            if terminal != current_terminal and current_terminal is not None:
                                # Process the previous group - sort companies in descending order
                                if current_group:
                                    current_group.sort(key=lambda x: str(x['Company']), reverse=True)
                                    df_final_csv.extend(current_group)
                                current_group = []
                            
                            current_terminal = terminal
                            current_group.append(row.to_dict())
                        
                        # Process the last group
                        if current_group:
                            current_group.sort(key=lambda x: str(x['Company']), reverse=True)
                            df_final_csv.extend(current_group)
                        
                        # Combine regular rows with Grand Total at the end
                        df_export = pd.DataFrame(df_final_csv)
                        if not grand_total_rows.empty:
                            df_export = pd.concat([df_export, grand_total_rows], ignore_index=True)
                    else:
                        df_export = grand_total_rows
                
                filename = "Russian_Exports_by_Terminal_and_Company.csv"
                return dcc.send_data_frame(df_export.to_csv, filename=filename, index=False)
                
            except Exception as e:
                # Return empty CSV on error
                empty_df = pd.DataFrame(columns=['Error'], data=[{'Error': f'Export failed: {str(e)}'}])
                filename = "Russian_Exports_Export_Error.csv"
                return dcc.send_data_frame(empty_df.to_csv, filename=filename, index=False)
        
        raise dash.exceptions.PreventUpdate
    

