"""
Price Scorecard for Key World Oil Grades View
Price scorecard table for key crude grades with multi-level headers
"""
from dash import dcc, html, Input, Output, callback, dash_table
import dash
import pandas as pd
import os
from pathlib import Path


def create_layout():
    """Create the Price Scorecard layout"""
    return html.Div([
        # Top grey line
        html.Hr(style={
            'border': 'none',
            'borderTop': '1px solid #cccccc',
            'margin': '0',
            'marginBottom': '20px'
        }),
        
        # Title - left-aligned, orange-brown, serif font
        html.H3("PIW SCORECARD -- COSTS TO REFINERS OF KEY FORMULA PRICED CRUDE OILS IN PRIMARY WORLD MARKETS ($/bbl)", 
                style={
                    'marginBottom': '20px', 
                    'fontSize': '16px', 
                    'fontWeight': 'normal',
                    'textAlign': 'left',
                    'color': '#cc6600',  # Orange-brown color
                    'fontFamily': 'Times New Roman, serif',
                    'padding': '0',
                    'margin': '0 0 20px 0'
                }),
        
        # Clickable boxes container
        html.Div([
            # Costs to Refiners box
            html.Button(
                "Costs to Refiners",
                id='costs-to-refiners-btn',
                n_clicks=0,
                style={
                    'display': 'inline-block',
                    'marginRight': '30px',
                    'padding': '12px 25px',
                    'border': '2px solid #ff6600',  # Orange border
                    'color': '#0066cc',  # Blue text
                    'fontSize': '15px',
                    'fontWeight': 'normal',
                    'fontFamily': 'Arial, sans-serif',
                    'width': '380px',
                    'textAlign': 'center',
                    'cursor': 'pointer',
                    'borderRadius': '4px',
                    'height': '45px',
                    'lineHeight': '21px'
                }
            ),
            
            # Port of Loading box
            html.Button(
                "Port of Loading",
                id='port-of-loading-btn',
                n_clicks=0,
                style={
                    'display': 'inline-block',
                    'marginRight': '30px',
                    'padding': '12px 25px',
                    'border': '2px solid #ff6600',  # Orange border
                    'color': '#0066cc',  # Blue text
                    'fontSize': '15px',
                    'fontWeight': 'normal',
                    'fontFamily': 'Arial, sans-serif',
                    'width': '380px',
                    'textAlign': 'center',
                    'cursor': 'pointer',
                    'borderRadius': '4px',
                    'height': '45px',
                    'lineHeight': '21px'
                }
            ),
            
            # Price Formula box
            html.Button(
                "Price Formula",
                id='price-formula-btn',
                n_clicks=0,
                style={
                    'display': 'inline-block',
                    'padding': '12px 25px',
                    'border': '2px solid #ff6600',  # Orange border
                    'color': '#0066cc',  # Blue text
                    'fontSize': '15px',
                    'fontWeight': 'normal',
                    'fontFamily': 'Arial, sans-serif',
                    'width': '380px',
                    'textAlign': 'center',
                    'cursor': 'pointer',
                    'borderRadius': '4px',
                    'height': '45px',
                    'lineHeight': '21px'
                }
            )
        ], style={
            'marginBottom': '30px',
            'textAlign': 'left'
        }),
        
        # Store selected CSV type
        dcc.Store(id='selected-csv-type', data='Cost_to_Refiners'),
        
        # Table container
        html.Div(id='price-scorecard-table-container')
    ], className='tab-content', style={'padding': '20px', 'backgroundColor': '#ffffff'})


def load_csv_data(csv_type='Cost_to_Refiners'):
    """Load and parse CSV data with multi-level headers"""
    # Get the base directory
    base_dir = Path(__file__).parent.parent / 'data' / 'price'
    csv_file = base_dir / f'{csv_type}.csv'
    
    if not csv_file.exists():
        print(f"CSV file not found: {csv_file}")
        return None, None, None, None, None
    
    try:
        # Read CSV with tab separator, skip first 2 rows (copyright info)
        # Try UTF-16 first (common for Excel exports), fallback to UTF-8
        try:
            df = pd.read_csv(csv_file, sep='\t', header=None, skiprows=2, encoding='utf-16')
        except UnicodeDecodeError:
            df = pd.read_csv(csv_file, sep='\t', header=None, skiprows=2, encoding='utf-8')
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None, None, None
    
    # Extract header rows
    # Row 0 (index 0): Delivery locations
    # Row 1 (index 1): Countries
    # Row 2 (index 2): Crude types
    # Row 3 (index 3): Pricing terms
    
    # Extract header rows and convert NaN to None for easier handling
    delivery_locations = [None if pd.isna(v) else v for v in df.iloc[0].values[2:]]  # Skip first 2 empty columns
    countries = [None if pd.isna(v) else v for v in df.iloc[1].values[2:]]
    crude_types = [None if pd.isna(v) else v for v in df.iloc[2].values[2:]]
    pricing_terms = [None if pd.isna(v) else v for v in df.iloc[3].values[2:]]
    
    # Extract data rows (starting from row 4, index 4)
    data_df = df.iloc[4:].copy()
    
    # Set first two columns as Year and Month
    if len(data_df.columns) >= 2:
        data_df.columns = ['Year', 'Month'] + [f'col_{i}' for i in range(len(data_df.columns) - 2)]
    
    # Clean data - remove rows with all NaN
    data_df = data_df.dropna(how='all')
    
    # Convert year and month columns
    data_df['Year'] = data_df['Year'].astype(str).str.strip()
    data_df['Month'] = data_df['Month'].astype(str).str.strip()
    
    # Convert value columns to numeric
    value_cols = [col for col in data_df.columns if col.startswith('col_')]
    for col in value_cols:
        data_df[col] = pd.to_numeric(data_df[col], errors='coerce')
    
    return delivery_locations, countries, crude_types, pricing_terms, data_df


def build_column_structure(delivery_locations, countries, crude_types, pricing_terms):
    """Build column structure with proper hierarchy"""
    columns = []
    
    # First two columns: Year and Month
    columns.append({'name': ['', '', '', 'Year'], 'id': 'Year'})
    columns.append({'name': ['', '', '', 'Month'], 'id': 'Month'})
    
    # Forward-fill all header levels to handle empty cells in CSV
    # This ensures headers span across all their related columns
    max_len = max(len(delivery_locations), len(countries), len(crude_types), len(pricing_terms))
    
    filled_delivery = []
    filled_countries = []
    filled_crude = []
    
    last_delivery = None
    last_country = None
    last_crude = None
    
    # Helper function to check if value is non-empty
    def is_non_empty(val):
        if val is None:
            return False
        try:
            if pd.isna(val):
                return False
        except (TypeError, ValueError):
            pass
        # Handle float NaN
        try:
            if isinstance(val, float) and (val != val):  # NaN check: NaN != NaN
                return False
        except:
            pass
        val_str = str(val).strip()
        return val_str != '' and val_str.lower() not in ['nan', 'none', 'null']
    
    # First pass: forward-fill empty cells
    for i in range(max_len):
        # Get raw values, handling all edge cases
        delivery_raw = delivery_locations[i] if i < len(delivery_locations) else None
        country_raw = countries[i] if i < len(countries) else None
        crude_raw = crude_types[i] if i < len(crude_types) else None
        
        # Forward-fill delivery location
        if is_non_empty(delivery_raw):
            delivery_str = str(delivery_raw).strip()
            # If delivery changed, reset country and crude
            if delivery_str != last_delivery:
                last_country = None
                last_crude = None
            last_delivery = delivery_str
        # Keep last_delivery for forward-fill (even if None, we'll handle it later)
        filled_delivery.append(last_delivery)
        
        # Forward-fill country
        if is_non_empty(country_raw):
            country_str = str(country_raw).strip()
            # If country changed, reset crude
            if country_str != last_country:
                last_crude = None
            last_country = country_str
        # Keep last_country for forward-fill
        filled_countries.append(last_country)
        
        # Forward-fill crude type
        if is_non_empty(crude_raw):
            last_crude = str(crude_raw).strip()
        # Keep last_crude for forward-fill
        filled_crude.append(last_crude)
    
    # Track current values for grouping
    current_delivery = None
    current_country = None
    current_crude = None
    col_idx = 0
    
    # Second pass: build column structure with forward-filled values
    for i in range(max_len):
        # Use forward-filled values directly - same value = automatic merging by Dash
        delivery = filled_delivery[i] if filled_delivery[i] is not None else ''
        country = filled_countries[i] if filled_countries[i] is not None else ''
        crude = filled_crude[i] if filled_crude[i] is not None else ''
        pricing = str(pricing_terms[i]).strip() if i < len(pricing_terms) and pricing_terms[i] is not None and is_non_empty(pricing_terms[i]) else ''
        
        # Build column name array for multi-level header
        # Use the forward-filled values directly - Dash will merge cells with the same value
        col_name = ['', '', '', '']
        
        # Level 1: Delivery location - use forward-filled value (same value = merged)
        col_name[0] = delivery if delivery else ''
        
        # Level 2: Country - use forward-filled value (same value = merged)
        col_name[1] = country if country else ''
        
        # Level 3: Crude type - use forward-filled value (same value = merged)
        col_name[2] = crude if crude else ''
        
        # Level 4: Pricing terms - always show value for every column (no merging)
        # Add invisible character to prevent Dash from merging identical consecutive values
        if pricing:
            # Use zero-width non-joiner (U+200C) with column index to make each value unique
            # This prevents merging while keeping the display visually identical
            # Different invisible chars for different columns: U+200B (zero-width space), 
            # U+200C (zero-width non-joiner), U+200D (zero-width joiner), U+FEFF (zero-width no-break space)
            invisible_chars = ['\u200B', '\u200C', '\u200D', '\uFEFF']
            invisible_char = invisible_chars[i % len(invisible_chars)]
            col_name[3] = pricing + invisible_char
        else:
            col_name[3] = ''
        
        # Create column ID
        col_id = f'col_{col_idx}'
        col_idx += 1
        
        columns.append({
            'name': col_name,
            'id': col_id
        })
    
    return columns


def format_data_for_table(data_df, num_value_cols):
    """Format data for dash_table with proper sorting"""
    # Create records
    records = []
    
    # Month order for descending sort
    months_order = ['December', 'November', 'October', 'September', 'August', 'July', 'June', 'May', 'April', 'March', 'February', 'January']
    
    # Track row indices for year boundaries
    year_boundary_rows = []
    current_row_index = 0
    
    # Group by year and sort
    for year in sorted(data_df['Year'].unique(), reverse=True):
        year_data = data_df[data_df['Year'] == year].copy()
        
        # Sort months in descending order
        year_data['Month'] = pd.Categorical(
            year_data['Month'], 
            categories=months_order, 
            ordered=True
        )
        year_data = year_data.sort_values('Month', ascending=False)
        
        # Show year only in the first row of each year group, empty for others
        for idx, (_, row) in enumerate(year_data.iterrows()):
            # Format year to remove decimal (e.g., 2025.0 -> 2025)
            year_value = ''
            if idx == 0:
                try:
                    # Convert to float first to handle string "2025.0", then to int to remove decimal
                    year_value = str(int(float(row['Year'])))
                except (ValueError, TypeError):
                    # If conversion fails, use original value as string and remove .0 if present
                    year_str = str(row['Year'])
                    year_value = year_str.replace('.0', '') if year_str.endswith('.0') else year_str
            
            record = {
                'Year': year_value,  # Show year only in first row of group, formatted without decimal
                'Month': row['Month']
            }
            
            # Add value columns
            for i in range(num_value_cols):
                col_id = f'col_{i}'
                if col_id in row:
                    value = row[col_id]
                    if pd.notna(value) and value != '':
                        try:
                            record[col_id] = f'{float(value):.2f}'
                        except (ValueError, TypeError):
                            record[col_id] = ''
                    else:
                        record[col_id] = ''
                else:
                    record[col_id] = ''
            
            records.append(record)
            
            # Track the last row of each year group for border styling
            if idx == len(year_data) - 1:
                year_boundary_rows.append(current_row_index)
            
            current_row_index += 1
    
    return records, year_boundary_rows


def register_callbacks(dash_app, server):
    """Register all callbacks for Price Scorecard"""
    
    # Callback to update selected CSV type when buttons are clicked
    @callback(
        Output('selected-csv-type', 'data'),
        [Input('costs-to-refiners-btn', 'n_clicks'),
         Input('port-of-loading-btn', 'n_clicks'),
         Input('price-formula-btn', 'n_clicks')],
        prevent_initial_call=False
    )
    def update_selected_csv(costs_clicks, port_clicks, formula_clicks):
        """Update selected CSV type based on button clicks"""
        ctx = dash.callback_context
        if not ctx.triggered:
            # Initial load - default to Cost_to_Refiners
            return 'Cost_to_Refiners'
        
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if triggered_id == 'costs-to-refiners-btn':
            return 'Cost_to_Refiners'
        elif triggered_id == 'port-of-loading-btn':
            return 'Port_of_Loading'
        elif triggered_id == 'price-formula-btn':
            return 'Price_Formula'
        
        return 'Cost_to_Refiners'  # Default
    
    # Callback to update button styles based on selection
    @callback(
        [Output('costs-to-refiners-btn', 'style'),
         Output('port-of-loading-btn', 'style'),
         Output('price-formula-btn', 'style')],
        Input('selected-csv-type', 'data')
    )
    def update_button_styles(selected_csv):
        """Update button styles to show which one is active"""
        base_style = {
            'display': 'inline-block',
            'marginRight': '30px',
            'padding': '12px 25px',
            'border': '2px solid #ff6600',
            'color': '#0066cc',
            'fontSize': '15px',
            'fontWeight': 'normal',
            'fontFamily': 'Arial, sans-serif',
            'width': '380px',
            'textAlign': 'center',
            'cursor': 'pointer',
            'borderRadius': '4px',
            'height': '45px',
            'lineHeight': '21px'
        }
        
        # Active button has background color
        active_style = base_style.copy()
        active_style['backgroundColor'] = '#e0e0e0'  # Light grey when active
        
        # Inactive buttons have no background (transparent)
        inactive_style = base_style.copy()
        inactive_style['backgroundColor'] = 'transparent'
        
        # Last button (Price Formula) should not have right margin
        last_button_base = base_style.copy()
        last_button_base['marginRight'] = '0px'
        
        last_button_active = last_button_base.copy()
        last_button_active['backgroundColor'] = '#e0e0e0'
        
        last_button_inactive = last_button_base.copy()
        last_button_inactive['backgroundColor'] = 'transparent'
        
        # Default to Cost_to_Refiners if selected_csv is None
        if not selected_csv:
            selected_csv = 'Cost_to_Refiners'
        
        if selected_csv == 'Cost_to_Refiners':
            return active_style, inactive_style, last_button_inactive
        elif selected_csv == 'Port_of_Loading':
            return inactive_style, active_style, last_button_inactive
        elif selected_csv == 'Price_Formula':
            return inactive_style, inactive_style, last_button_active
        
        # Default to Cost_to_Refiners
        return active_style, inactive_style, last_button_inactive
    
    # Callback to update table based on selected CSV
    @callback(
        Output('price-scorecard-table-container', 'children'),
        [Input('selected-csv-type', 'data'),
         Input('current-submenu', 'data')]
    )
    def update_price_scorecard(selected_csv, submenu):
        """Update price scorecard table"""
        if submenu != 'price-scorecard':
            return html.Div()
        
        # Use the selected CSV type
        csv_type = selected_csv if selected_csv else 'Cost_to_Refiners'
        
        # Load the CSV data
        delivery_locations, countries, crude_types, pricing_terms, data_df = load_csv_data(csv_type)
        
        if data_df is None or data_df.empty:
            error_msg = f"Error loading data from {csv_type}.csv"
            if delivery_locations is None:
                error_msg += " - File not found or could not be read"
            return html.Div(error_msg, style={'padding': '20px', 'color': 'red'})
        
        if len(data_df) == 0:
            return html.Div("No data rows found in CSV", style={'padding': '20px', 'color': 'red'})
        
        # Build columns with multi-level structure
        columns = build_column_structure(delivery_locations, countries, crude_types, pricing_terms)
        
        # Count value columns (excluding Year and Month)
        num_value_cols = len([c for c in columns if c['id'].startswith('col_')])
        
        # Get actual data columns from the dataframe
        data_cols = [col for col in data_df.columns if col.startswith('col_')]
        actual_num_cols = len(data_cols)
        
        # Use the minimum to ensure we don't go out of bounds
        num_cols_to_use = min(num_value_cols, actual_num_cols)
        
        # If we have more columns defined than data columns, trim the columns
        if num_value_cols > actual_num_cols:
            # Keep Year, Month, and only the columns we have data for
            value_columns = [c for c in columns if c['id'].startswith('col_')]
            columns_to_keep = value_columns[:actual_num_cols]
            columns = [c for c in columns if c['id'] in ['Year', 'Month']] + columns_to_keep
        
        # Format data
        data, year_boundary_rows = format_data_for_table(data_df, num_cols_to_use)
        
        if not data:
            return html.Div("No data rows to display", style={'padding': '20px', 'color': 'red'})
        
        if not columns:
            return html.Div("No columns defined", style={'padding': '20px', 'color': 'red'})
        
        # Build conditional styles for borders at year boundaries
        year_boundary_styles = []
        for row_idx in year_boundary_rows:
            year_boundary_styles.append({
                'if': {'row_index': row_idx},
                'borderBottom': '1px solid #ddd'
            })
        
        # Create table with multi-level headers
        table = dash_table.DataTable(
            id='price-scorecard-table',
            columns=columns,
            data=data,
            merge_duplicate_headers=True,
            style_table={
                'overflowX': 'auto',
                'fontSize': '11px',
                'border': 'none',  # Remove outer border
                'maxHeight': '600px',
                'width': '100%',
                'borderCollapse': 'collapse'
            },
            style_cell={
                'textAlign': 'left',
                'padding': '6px 8px',
                'minWidth': '80px',
                'whiteSpace': 'normal',
                'height': 'auto',
                'fontSize': '11px',
                'border': 'none',  # Remove borders by default (will be overridden for headers)
                'backgroundColor': 'white',
                'fontFamily': '"Benton Sans Low-DPI", Arial, Helvetica, sans-serif',
                'color': '#1b365d'  # Apply color to all table fonts
            },
            style_header={
                'backgroundColor': 'white',
                'fontWeight': 'normal',  # Default normal, will be overridden by conditional styles
                'textAlign': 'center',
                'border': '1px solid #ddd',  # Keep header borders
                'verticalAlign': 'middle',
                'padding': '8px',
                'fontSize': '11px',
                'fontFamily': '"Benton Sans Low-DPI", Arial, Helvetica, sans-serif',
                'whiteSpace': 'normal',
                'height': 'auto',
                'color': '#1b365d'  # Apply color to all header fonts
            },
            style_data={
                'border': 'none',  # Remove data cell borders only
                'padding': '6px 8px',
                'fontSize': '11px',
                'fontFamily': '"Benton Sans Low-DPI", Arial, Helvetica, sans-serif',
                'color': '#1b365d'  # Apply color to all data cell fonts
            },
            style_data_conditional=([
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#f9f9f9'
                },
                {
                    'if': {'row_index': 'even'},
                    'backgroundColor': 'white'
                },
                {
                    'if': {'column_id': 'Year'},
                    'textAlign': 'left',
                    'fontWeight': 'normal',
                    'color': '#1b365d'  # Apply color to Year column
                },
                {
                    'if': {'column_id': 'Month'},
                    'textAlign': 'left',
                    'fontWeight': 'normal',
                    'color': '#1b365d'  # Apply color to Month column
                }
            ] + [
                {
                    'if': {'column_id': f'col_{i}'},
                    'textAlign': 'center',
                    'fontWeight': 'normal',
                    'color': '#1b365d'  # Apply color to data columns
                } for i in range(num_cols_to_use)
            ] + year_boundary_styles),  # Add borders only at year boundaries
            style_header_conditional=[
                {
                    'if': {'header_index': 0},
                    'backgroundColor': 'white',
                    'fontWeight': 'bold',
                    'textAlign': 'center',
                    'color': '#ff6600'  # Orange color for Level 1 header
                },
                {
                    'if': {'header_index': 1},
                    'backgroundColor': 'white',
                    'fontWeight': 'bold',
                    'textAlign': 'center',
                    'color': '#1b365d'  # Apply color to Level 2 header
                },
                {
                    'if': {'header_index': 2},
                    'backgroundColor': 'white',
                    'fontWeight': 'bold',
                    'textAlign': 'center',
                    'color': '#1b365d'  # Apply color to Level 3 header
                },
                {
                    'if': {'header_index': 3},
                    'backgroundColor': 'white',
                    'fontWeight': 'normal',  # Regular weight for Level 4 header
                    'textAlign': 'center',
                    'color': '#1b365d'  # Apply color to Level 4 header
                }
            ],
            fixed_rows={'headers': True},
            page_size=50,
            sort_action='native',
            filter_action='none',
            css=[
                {
                    'selector': '.dash-table-tooltip',
                    'rule': 'display: none'
                }
            ]
        )
        
        return table
