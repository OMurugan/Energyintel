"""
Russian Exports by Terminal and Exporting Company View
Detailed Russian exports data
"""
from dash import html, Input, Output, callback, dash_table
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
        # Company column - increased font size
        {
            'if': {
                'column_id': 'Company'
            },
            'fontSize': '12px'
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
    # Add right-align and fontSize for year columns
    for col in year_columns:
        conditional_styles.append({
            'if': {'column_id': col},
            'textAlign': 'right',
            'fontSize': '12px',
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
                    style={'marginBottom': '0px', 'fontWeight': 'bold', 'color': '#ff6600', 'textAlign': 'center', 'fontSize': '24px'}),
            html.P("('000 b/d)", 
                   style={'marginTop': '0px', 'marginBottom': '20px', 'color': '#ff6600', 'textAlign': 'center', 'fontSize': '16px', 'fontWeight': 'normal'}),
        ]),
        html.Div([
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
                    'fontWeight': 'bold',
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
    
    @callback(
        [Output('russian-exports-table', 'data'),
         Output('russian-exports-table', 'columns')],
        Input('current-submenu', 'data')
    )
    def update_russian_exports(submenu):
        """Update Russian exports table from database"""
        if submenu != 'russian-exports':
            return [], []
        
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
            
            # Sort years descending and convert to strings
            year_columns = sorted(year_columns, reverse=True)
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
            
            # Sort by Terminal, Country and Company
            df = df.sort_values(['Terminal, Country', 'Company']).reset_index(drop=True)
            
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
            
            return table_data, columns
            
        except Exception as e:
            error_data = [{'Error': f'Failed to load data: {str(e)}'}]
            error_columns = [{'name': 'Error', 'id': 'Error'}]
            return error_data, error_columns

