"""
Russian Exports by Terminal and Exporting Company View
Detailed Russian exports data
"""
from dash import html, Input, Output, callback, dash_table
import pandas as pd
import os


def get_year_columns_from_csv():
    """Extract year columns dynamically from the CSV file"""
    # Get the CSV file path
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'data',
        'Trade',
        'Russian Exports by Terminal.csv'
    )
    
    try:
        raw = pd.read_csv(
            csv_path,
            encoding="utf-16",
            sep="\t",
            header=None,
            engine="python"
        )
        
        # Drop completely empty rows
        raw = raw.dropna(how="all")
        
        # Skip first two "Source / COPYRIGHT" rows
        raw = raw.iloc[2:].reset_index(drop=True)
        
        # Header is in first row (index 0)
        headers = raw.iloc[0].fillna("").astype(str).str.strip().tolist()
        
        # Extract year columns (4-digit years starting with '20' or all digits)
        year_columns = []
        for col in headers:
            col_str = str(col).strip()
            if col_str.isdigit() or (col_str.startswith('20') and len(col_str) == 4):
                year_columns.append(col_str)
        
        return year_columns
    except Exception as e:
        # Fallback to default years if CSV can't be read
        return ['2022', '2021', '2020', '2019', '2018', '2017', '2016', '2015', '2014', '2013', '2012', '2011', '2010', '2009', '2008', '2007', '2006']


def create_layout():
    """Create the Russian Exports layout"""
    # Build conditional styles for year columns (right-align numeric data)
    # Get year columns dynamically from CSV
    year_columns = get_year_columns_from_csv()
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
        """Update Russian exports table from CSV"""
        if submenu != 'russian-exports':
            return [], []
        
        # Get the CSV file path
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data',
            'Trade',
            'Russian Exports by Terminal.csv'
        )
        
        try:
            raw = pd.read_csv(
                csv_path,
                encoding="utf-16",
                sep="\t",
                header=None,
                engine="python"
            )
            
            # Drop completely empty rows
            raw = raw.dropna(how="all")
            
            # Skip first two "Source / COPYRIGHT" rows
            raw = raw.iloc[2:].reset_index(drop=True)
            
            # Header is in first row (index 0)
            headers = raw.iloc[0].fillna("").astype(str).str.strip().tolist()
            
            # Data starts from row index 1
            df = raw.iloc[1:].reset_index(drop=True)
            df.columns = headers
            
            # Remove any completely empty columns
            df = df.dropna(axis=1, how='all')
            
            # Replace empty strings with None
            df = df.replace(r'^\s*$', None, regex=True)
            df = df.replace('', None)
            
            year_columns = []
            for col in df.columns:
                col_str = str(col)
                if col_str.isdigit() or (col_str.startswith('20') and len(col_str) == 4):
                    year_columns.append(col)
            
            for col in year_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            terminal_col = 'Terminal, Country'
            df = df.reset_index(drop=True)
            
            if terminal_col in df.columns:
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
            
            if terminal_col in df.columns:
                # Store empty string values
                terminal_values = df[terminal_col].copy()
                # Convert other columns (not Terminal, Country) to None where null
                for col in df.columns:
                    if col != terminal_col:
                        df[col] = df[col].where(pd.notnull(df[col]), None)
                # Restore Terminal, Country values (including empty strings)
                df[terminal_col] = terminal_values
            else:
                df = df.where(pd.notnull(df), None)
            
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
                
                if col in year_columns:
                    col_config['type'] = 'numeric'
                    col_config['format'] = {'specifier': '.0f'}
                
                columns.append(col_config)
            
            return table_data, columns
            
        except Exception as e:
            error_data = [{'Error': f'Failed to load data: {str(e)}'}]
            error_columns = [{'name': 'Error', 'id': 'Error'}]
            return error_data, error_columns

