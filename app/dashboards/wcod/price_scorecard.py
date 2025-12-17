"""
Price Scorecard for Key World Oil Grades View
Price scorecard table for key crude grades with multi-level headers
"""
from dash import dcc, html, Input, Output, callback, dash_table
import dash
import pandas as pd
import os
from pathlib import Path
from functools import lru_cache
from core.data_helpers import execute_query


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
        
        # Store selected type filter
        dcc.Store(id='selected-type-filter', data='Cost to Refiners'),
        
        # Store selected column for highlighting
        dcc.Store(id='price-scorecard-selected-column', data=None),
        
        # Dummy output for client-side callback
        html.Div(id='price-scorecard-dummy-output', style={'display': 'none'}),
        
        # Table container with loading indicator
        dcc.Loading(
            id='price-scorecard-loading',
            type='dot',
            fullscreen=False,
            overlay_style={'backgroundColor': 'rgba(255, 255, 255, 0.8)'},
            children=html.Div(
                id='price-scorecard-table-container',
                style={'minHeight': '400px'}
            )
        )
    ], className='tab-content', style={'padding': '20px', 'backgroundColor': '#ffffff'})


def clear_price_scorecard_cache():
    """Clear the cache for price scorecard data - useful for testing or when data is updated"""
    _load_sql_data_cached.cache_clear()


@lru_cache(maxsize=3)
def _load_sql_data_cached(type_filter_value):
    """
    Cached function to load SQL data - filters at SQL level for performance
    type_filter_value: 'Cost to Refiners', 'Port of Loading', or 'Price Formula Adjustment'
    """
    try:
        # Map type filter to SQL value
        type_mapping = {
            'Cost to Refiners': 'Cost to Refiners',
            'Port of Loading': 'Port of Loading',
            'Price Formula': 'Price Formula Adjustment'
        }
        sql_type_value = type_mapping.get(type_filter_value, 'Cost to Refiners')
        
        # Optimized query with SQL-level filtering - much faster than filtering in Python
        query = """
        SELECT
            a.date,
            a.price_type AS type,
            a.crude_id,
            a.crude_name AS crude,
            a.crude_country AS country,
            b.region AS region,
            a.price AS price,
            a.delivery_to AS deliveryto,
            a.point_of_sale AS "Point Of Sale"
        FROM fact_wcod_prices a
        LEFT JOIN dim_country b
            ON a.crude_country_id = b.dim_country_id
        WHERE EXTRACT(YEAR FROM a.date) >= 2000
          AND a.price_type = :type_filter
        """
        
        # Execute query with parameterized filter - prevents SQL injection and allows query plan caching
        results = execute_query(query, params={'type_filter': sql_type_value})
        if not results:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        if df.empty:
            return None
        
        return df
    except Exception as e:
        print(f"Error loading SQL data: {e}")
        import traceback
        traceback.print_exc()
        return None


def load_sql_data(type_filter='Cost to Refiners'):
    """Load and transform SQL data with multi-level headers - optimized version"""
    try:
        # Load data using cached function (filters at SQL level)
        df = _load_sql_data_cached(type_filter)
        
        if df is None or df.empty:
            return None, None, None, None, None
        
        # Optimized date processing - convert once and extract in one pass
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date']).copy()  # Use copy to avoid SettingWithCopyWarning
        df['Year'] = df['date'].dt.year.astype(str)
        df['Month'] = df['date'].dt.strftime('%B')
        
        # Fill NaN values once for all columns to avoid repeated operations
        fill_cols = ['region', 'country', 'crude', 'Point Of Sale', 'deliveryto']
        for col in fill_cols:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str)
        
        # Create a unique identifier for each column combination
        # This will be used to create the multi-level headers
        # For Port of Loading: Level 1 = region, Level 2 = country, Level 3 = crude, Level 4 = Point Of Sale
        # For others: Level 1 = deliveryto, Level 2 = country, Level 3 = crude, Level 4 = Point Of Sale
        if type_filter == 'Port of Loading':
            # For Port of Loading: region -> country -> crude -> Point Of Sale
            df['column_key'] = (
                df['region'] + '|' +
                df['country'] + '|' +
                df['crude'] + '|' +
                df['Point Of Sale']
            )
            # Get unique column combinations with region and country - optimized with subset
            header_cols = ['region', 'country', 'crude', 'Point Of Sale', 'column_key']
            unique_combinations = df[header_cols].drop_duplicates().sort_values(
                ['region', 'country', 'crude', 'Point Of Sale']
            )
            # Extract header levels - Level 1 = region, Level 2 = country
            delivery_locations = unique_combinations['region'].tolist()
            countries = unique_combinations['country'].tolist()
        else:
            # Use country for Cost to Refiners and Price Formula
            df['column_key'] = (
                df['deliveryto'] + '|' +
                df['country'] + '|' +
                df['crude'] + '|' +
                df['Point Of Sale']
            )
            # Get unique column combinations with country - optimized
            header_cols = ['deliveryto', 'country', 'crude', 'Point Of Sale', 'column_key']
            unique_combinations = df[header_cols].drop_duplicates().sort_values(
                ['deliveryto', 'country', 'crude', 'Point Of Sale']
            )
            # Extract header levels - Level 1 = deliveryto, Level 2 = country
            # Add "Delivered to " prefix for Cost to Refiners and Price Formula
            delivery_locations = ['Delivered to ' + v if v else '' for v in unique_combinations['deliveryto'].tolist()]
            countries = unique_combinations['country'].tolist()
        
        crude_types = unique_combinations['crude'].tolist()
        pricing_terms = unique_combinations['Point Of Sale'].tolist()
        
        # Get the ordered list of column keys (this determines the column order)
        ordered_column_keys = unique_combinations['column_key'].tolist()
        
        # Optimized pivot: use groupby + unstack for better performance on large datasets
        # First, ensure we have unique (Year, Month, column_key) combinations
        df_pivot = df.groupby(['Year', 'Month', 'column_key'])['price'].first().reset_index()
        
        # Pivot using unstack for better performance
        pivot_df = df_pivot.set_index(['Year', 'Month', 'column_key'])['price'].unstack(fill_value=None).reset_index()
        
        # Ensure all column keys are present (add missing ones as None columns)
        missing_keys = set(ordered_column_keys) - set(pivot_df.columns)
        for key in missing_keys:
            pivot_df[key] = None
        
        # Reorder columns efficiently - build list once
        reordered_cols = ['Year', 'Month'] + [key for key in ordered_column_keys if key in pivot_df.columns]
        pivot_df = pivot_df[reordered_cols]
        
        # Rename columns to col_0, col_1, etc. for consistency with existing code
        value_cols_final = [col for col in pivot_df.columns if col not in ['Year', 'Month']]
        col_mapping = dict(zip(value_cols_final, [f'col_{i}' for i in range(len(value_cols_final))]))
        pivot_df = pivot_df.rename(columns=col_mapping)
        
        # Ensure Year and Month are strings, convert value columns to numeric in one pass
        pivot_df['Year'] = pivot_df['Year'].astype(str)
        pivot_df['Month'] = pivot_df['Month'].astype(str)
        
        # Convert value columns to numeric efficiently
        value_cols_to_convert = [c for c in pivot_df.columns if c.startswith('col_')]
        if value_cols_to_convert:
            pivot_df[value_cols_to_convert] = pivot_df[value_cols_to_convert].apply(pd.to_numeric, errors='coerce')
        
        # Convert header lists to match expected format (None for empty strings)
        delivery_locations = [None if not v or v == '' else v for v in delivery_locations]
        countries = [None if not v or v == '' else v for v in countries]
        crude_types = [None if not v or v == '' else v for v in crude_types]
        pricing_terms = [None if not v or v == '' else v for v in pricing_terms]
        
        return delivery_locations, countries, crude_types, pricing_terms, pivot_df
    
    except Exception as e:
        print(f"Error loading SQL data: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None, None, None


def build_column_structure(delivery_locations, countries, crude_types, pricing_terms):
    """Build column structure with proper hierarchy"""
    columns = []
    
    # First two columns: Year and Month
    columns.append({'name': ['', '', '', 'Year'], 'id': 'Year'})
    columns.append({'name': ['', '', '', 'Month'], 'id': 'Month'})
    
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
        
        # Sort months in descending order (December to January)
        year_data['Month'] = pd.Categorical(
            year_data['Month'], 
            categories=months_order, 
            ordered=True
        )
        year_data = year_data.sort_values('Month', ascending=True)  # ascending=True because categories are already in descending order
        
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
    
    # Callback to update selected type filter when buttons are clicked
    @callback(
        Output('selected-type-filter', 'data'),
        [Input('costs-to-refiners-btn', 'n_clicks'),
         Input('port-of-loading-btn', 'n_clicks'),
         Input('price-formula-btn', 'n_clicks')],
        prevent_initial_call=False
    )
    def update_selected_type(costs_clicks, port_clicks, formula_clicks):
        """Update selected type filter based on button clicks"""
        ctx = dash.callback_context
        if not ctx.triggered:
            # Initial load - default to Cost to Refiners
            return 'Cost to Refiners'
        
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if triggered_id == 'costs-to-refiners-btn':
            return 'Cost to Refiners'
        elif triggered_id == 'port-of-loading-btn':
            return 'Port of Loading'
        elif triggered_id == 'price-formula-btn':
            return 'Price Formula'
        
        return 'Cost to Refiners'  # Default
    
    # Callback to update button styles based on selection
    @callback(
        [Output('costs-to-refiners-btn', 'style'),
         Output('port-of-loading-btn', 'style'),
         Output('price-formula-btn', 'style')],
        Input('selected-type-filter', 'data')
    )
    def update_button_styles(selected_type):
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
        
        # Default to Cost to Refiners if selected_type is None
        if not selected_type:
            selected_type = 'Cost to Refiners'
        
        if selected_type == 'Cost to Refiners':
            return active_style, inactive_style, last_button_inactive
        elif selected_type == 'Port of Loading':
            return inactive_style, active_style, last_button_inactive
        elif selected_type == 'Price Formula':
            return inactive_style, inactive_style, last_button_active
        
        # Default to Cost to Refiners
        return active_style, inactive_style, last_button_inactive
    
    # Callback to update table based on selected type filter
    @callback(
        Output('price-scorecard-table-container', 'children'),
        [Input('selected-type-filter', 'data'),
         Input('current-submenu', 'data')]
    )
    def update_price_scorecard(selected_type, submenu):
        """Update price scorecard table"""
        if submenu != 'price-scorecard':
            return html.Div()
        
        # Use the selected type filter
        type_filter = selected_type if selected_type else 'Cost to Refiners'
        
        # Load the SQL data
        delivery_locations, countries, crude_types, pricing_terms, data_df = load_sql_data(type_filter)
        
        if data_df is None or data_df.empty:
            error_msg = f"Error loading data for type: {type_filter}"
            if delivery_locations is None:
                error_msg += " - Query returned no results or error occurred"
            return html.Div(error_msg, style={'padding': '20px', 'color': 'red'})
        
        if len(data_df) == 0:
            return html.Div("No data rows found for selected filter", style={'padding': '20px', 'color': 'red'})
        
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
                },
                {
                    'selector': '#price-scorecard-table .dash-spreadsheet-container th',
                    'rule': 'cursor: pointer; transition: background-color 0.2s ease;'
                },
                {
                    'selector': '#price-scorecard-table .dash-spreadsheet-container th.column-selected',
                    'rule': 'background-color: #b3d9ff !important; color: #1b365d !important; font-weight: bold !important;'
                },
                {
                    'selector': '#price-scorecard-table .dash-spreadsheet-container td.column-cell-selected',
                    'rule': 'background-color: #b3d9ff !important; border: none !important; font-weight: 600 !important; color: #1b365d !important; opacity: 1 !important;'
                },
                {
                    'selector': '#price-scorecard-table .dash-spreadsheet-container.column-selection-active td:not([data-dash-column="Year"]):not([data-dash-column="Month"]):not(.column-cell-selected)',
                    'rule': 'opacity: 0.3 !important;'
                }
            ]
        )
        
        return table
    
    # Client-side callback to handle header clicks and column highlighting
    dash_app.clientside_callback(
        """
        function(_id) {
            try {
                // Initialize global state if not exists
                if (!window.priceScorecardState) {
                    window.priceScorecardState = {
                        selectedColumnId: null,
                        selectedRowIndex: null,
                        lastTableSignature: null
                    };
                }
                
                function clearAllColumnSelections(spreadsheet) {
                    if (!spreadsheet) return;
                    // Clear all column headers
                    const allHeaders = spreadsheet.querySelectorAll('th.column-selected');
                    allHeaders.forEach(header => {
                        header.classList.remove('column-selected');
                        header.style.backgroundColor = '';
                        header.style.color = '';
                        header.style.fontWeight = '';
                    });
                    
                    // Clear all column cells
                    const allColumnCells = spreadsheet.querySelectorAll('td.column-cell-selected');
                    allColumnCells.forEach(cell => {
                        cell.classList.remove('column-cell-selected');
                        cell.style.backgroundColor = '';
                        cell.style.border = '';
                        cell.style.fontWeight = '';
                        cell.style.opacity = '';
                    });
                    
                    // Remove column selection active class and reset opacity for all cells
                    spreadsheet.classList.remove('column-selection-active');
                    const allDataCells = spreadsheet.querySelectorAll('td[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Month"])');
                    allDataCells.forEach(cell => {
                        cell.style.opacity = '';
                    });
                }
                
                function clearAllRowSelections(spreadsheet) {
                    if (!spreadsheet) return;
                    // Clear all row cells
                    const allRowCells = spreadsheet.querySelectorAll('td.row-cell-selected');
                    allRowCells.forEach(cell => {
                        cell.classList.remove('row-cell-selected');
                        cell.style.backgroundColor = '';
                        cell.style.border = '';
                    });
                    
                    // Remove row selection active class and reset opacity for all rows
                    spreadsheet.classList.remove('row-selection-active');
                    const allDataRows = spreadsheet.querySelectorAll('tbody tr');
                    allDataRows.forEach(r => {
                        const rowCells = r.querySelectorAll('td[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Month"])');
                        rowCells.forEach(c => {
                            c.style.opacity = '';
                        });
                    });
                }
                
                function getCellValue(cell) {
                    const text = cell.textContent || cell.innerText || '';
                    return text.trim();
                }
                
                function enhanceTable() {
                    const tableEl = document.getElementById('price-scorecard-table');
                    if (!tableEl) {
                        console.log('Price scorecard: Table element not found');
                        return;
                    }
                    
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    if (!spreadsheet) {
                        console.log('Price scorecard: Spreadsheet container not found');
                        return;
                    }
                    
                    // Check if headers exist
                    const headers = spreadsheet.querySelectorAll('th[data-dash-column]');
                    if (headers.length === 0) {
                        console.log('Price scorecard: No headers found yet');
                        return;
                    }
                    
                    // Create a hash of the table structure to detect changes
                    // Use the first few header texts and column count as a signature
                    let tableSignature = '';
                    const topRow = spreadsheet.querySelector('thead tr');
                    if (topRow) {
                        const topHeaders = Array.from(topRow.querySelectorAll('th')).slice(0, 5);
                        tableSignature = topHeaders.map(h => h.textContent.trim()).join('|') + '|' + headers.length;
                    } else {
                        tableSignature = headers.length.toString();
                    }
                    
                    // Check if table structure has changed (new table rendered)
                    const signatureChanged = window.priceScorecardState.lastTableSignature !== tableSignature;
                    if (signatureChanged) {
                        // Table was re-rendered, reset enhanced flag and clear handlers
                        console.log('Price scorecard: Table structure changed, resetting enhancement');
                        console.log('Price scorecard: Old signature:', window.priceScorecardState.lastTableSignature);
                        console.log('Price scorecard: New signature:', tableSignature);
                        spreadsheet.dataset.priceScorecardEnhanced = 'false';
                        
                        // Remove old click handler
                        if (spreadsheet._priceScorecardClickHandler) {
                            spreadsheet.removeEventListener('click', spreadsheet._priceScorecardClickHandler, true);
                            spreadsheet._priceScorecardClickHandler = null;
                        }
                        
                        // Clear selections
                        clearAllColumnSelections(spreadsheet);
                        clearAllRowSelections(spreadsheet);
                        
                        window.priceScorecardState.lastTableSignature = tableSignature;
                        window.priceScorecardState.selectedColumnId = null;
                        window.priceScorecardState.selectedRowIndex = null;
                    }
                    
                    // Skip if already enhanced (but only if signature hasn't changed)
                    if (spreadsheet.dataset.priceScorecardEnhanced === 'true' && !signatureChanged) {
                        console.log('Price scorecard: Table already enhanced, skipping');
                        return;
                    }
                    
                    // If signature changed or not enhanced, proceed with enhancement
                    console.log('Price scorecard: Proceeding with enhancement (enhanced:', spreadsheet.dataset.priceScorecardEnhanced, ', signatureChanged:', signatureChanged, ')');
                    
                    console.log('Price scorecard: Enhancing table');
                    spreadsheet.dataset.priceScorecardEnhanced = 'true';
                    
                    // Remove any existing click handler to avoid duplicates
                    if (spreadsheet._priceScorecardClickHandler) {
                        spreadsheet.removeEventListener('click', spreadsheet._priceScorecardClickHandler, true);
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
                            
                            // Get header text for debugging
                            const headerText = header.textContent.trim();
                            console.log('Price scorecard: Header clicked, columnId:', columnId, ', text:', headerText);
                            
                            // Skip Year and Month columns
                            if (columnId === 'Year' || columnId === 'Month') {
                                return;
                            }
                            
                            // Clear all previous selections before processing new selection
                            clearAllColumnSelections(clickedSpreadsheet);
                            clearAllRowSelections(clickedSpreadsheet);
                            if (window.priceScorecardState) {
                                window.priceScorecardState.selectedRowIndex = null;
                            }
                            
                            // Find which header row this header belongs to (header_index)
                            const headerRow = header.closest('tr');
                            const thead = header.closest('thead');
                            
                            let headerIndex = -1;
                            let totalHeaderRows = 0;
                            let headerRows = [];
                            
                            if (thead) {
                                headerRows = Array.from(thead.querySelectorAll('tr'));
                                console.log('Price scorecard: Found thead with', headerRows.length, 'rows');
                            }
                            
                            // If no rows found in thead, try in spreadsheet
                            if (headerRows.length === 0 && clickedSpreadsheet) {
                                headerRows = Array.from(clickedSpreadsheet.querySelectorAll('thead tr'));
                                console.log('Price scorecard: Found', headerRows.length, 'header rows in spreadsheet');
                            }
                            
                            // If still no rows, try finding any tr containing headers
                            if (headerRows.length === 0 && clickedSpreadsheet) {
                                const allTrs = clickedSpreadsheet.querySelectorAll('tr');
                                headerRows = Array.from(allTrs).filter(tr => {
                                    return tr.querySelector('th[data-dash-column]') !== null;
                                });
                                console.log('Price scorecard: Found', headerRows.length, 'rows with headers');
                            }
                            
                            // Filter out rows that only contain Year/Month headers - we only want data column header rows
                            // A data column header row should have at least one header with columnId starting with 'col_'
                            headerRows = headerRows.filter(tr => {
                                const dataHeaders = tr.querySelectorAll('th[data-dash-column^="col_"]');
                                return dataHeaders.length > 0;
                            });
                            
                            totalHeaderRows = headerRows.length;
                            
                            if (headerRow && headerRows.length > 0) {
                                headerIndex = headerRows.indexOf(headerRow);
                                console.log('Price scorecard: Header row found at index:', headerIndex);
                                
                                // Debug: log all header rows to verify structure
                                console.log('Price scorecard: All header rows (data columns only):', headerRows.map((r, i) => {
                                    const firstDataHeader = r.querySelector('th[data-dash-column^="col_"]');
                                    return `Row ${i}: ${firstDataHeader ? firstDataHeader.getAttribute('data-dash-column') : 'no data column'}`;
                                }));
                            } else if (headerRow) {
                                // If headerRow is not in the filtered list, it might be a Year/Month row
                                // Try to find it in the original thead rows
                                const theadRows = thead ? Array.from(thead.querySelectorAll('tr')) : [];
                                const allDataRows = theadRows.filter(tr => {
                                    const dataHeaders = tr.querySelectorAll('th[data-dash-column^="col_"]');
                                    return dataHeaders.length > 0;
                                });
                                if (allDataRows.length > 0) {
                                    headerIndex = allDataRows.indexOf(headerRow);
                                    headerRows = allDataRows;
                                    totalHeaderRows = headerRows.length;
                                    console.log('Price scorecard: Found header row in data rows at index:', headerIndex);
                                }
                            }
                            
                            console.log('Price scorecard: Final - Header index:', headerIndex, 'of', totalHeaderRows, 'total rows');
                            console.log('Price scorecard: Bottom header index should be:', totalHeaderRows - 1);
                            
                            // Create a unique key for this selection (columnId + headerIndex)
                            const selectionKey = columnId + '_' + headerIndex;
                            
                            // Check if this exact header level is already selected
                            if (window.priceScorecardState && window.priceScorecardState.selectedColumnId === selectionKey) {
                                // Deselect column
                                console.log('Price scorecard: Deselecting column');
                                clearAllColumnSelections(clickedSpreadsheet);
                                if (window.priceScorecardState) {
                                    window.priceScorecardState.selectedColumnId = null;
                                }
                            } else {
                                // Select new column
                                console.log('Price scorecard: Selecting column:', columnId, 'at header level:', headerIndex);
                                clearAllColumnSelections(clickedSpreadsheet);
                                clearAllRowSelections(clickedSpreadsheet);
                                
                                if (window.priceScorecardState) {
                                    window.priceScorecardState.selectedColumnId = selectionKey;
                                    window.priceScorecardState.selectedRowIndex = null;
                                }
                                
                                // Only highlight headers at the SAME header level (headerIndex) for this column
                                const allHeadersForColumn = clickedSpreadsheet.querySelectorAll(`th[data-dash-column="${columnId}"]`);
                                console.log('Price scorecard: Found', allHeadersForColumn.length, 'headers for column');
                                
                                // Check if this is the bottom-most header level
                                const isBottomHeader = (headerIndex >= 0 && totalHeaderRows > 0 && headerIndex === totalHeaderRows - 1);
                                // Check if this is the top-most header level (index 0)
                                const isTopHeader = (headerIndex === 0);
                                
                                console.log('Price scorecard: Is bottom header?', isBottomHeader, ', Is top header?', isTopHeader, '(headerIndex:', headerIndex, ', totalHeaderRows:', totalHeaderRows, ')');
                                
                                if (isBottomHeader || isTopHeader) {
                                    // Bottom or top header clicked - highlight ALL header levels and data cells
                                    if (isTopHeader) {
                                        console.log('Price scorecard: ✓ TOP HEADER CLICKED - Finding all columns under this spanning header');
                                        
                                        // For top header, find all columns that share the same top-level header text
                                        const topHeaderText = header.textContent.trim();
                                        console.log('Price scorecard: Top header text:', topHeaderText);
                                        
                                        // Check if header has colspan (spans multiple columns)
                                        const colspan = header.getAttribute('colspan') || header.colSpan;
                                        console.log('Price scorecard: Header colspan:', colspan);
                                        
                                        // Find all headers in the top row (index 0) with the same text
                                        const topRow = headerRows[0];
                                        if (topRow) {
                                            // Get all column IDs under this spanning header
                                            const columnIds = new Set();
                                            
                                            if (colspan && parseInt(colspan) > 1) {
                                                // Header spans multiple columns - find all columns under it
                                                const spanCount = parseInt(colspan);
                                                console.log('Price scorecard: Header spans', spanCount, 'columns');
                                                
                                                // Get all cells in the top row (including merged cells)
                                                const allTopRowCells = Array.from(topRow.querySelectorAll('th'));
                                                
                                                // Find the clicked header's position in the row (by cell index, not data-dash-column)
                                                let clickedCellIndex = -1;
                                                for (let i = 0; i < allTopRowCells.length; i++) {
                                                    if (allTopRowCells[i] === header || allTopRowCells[i].contains(header)) {
                                                        clickedCellIndex = i;
                                                        break;
                                                    }
                                                }
                                                
                                                console.log('Price scorecard: Clicked header cell index:', clickedCellIndex);
                                                
                                                // Get all bottom row headers (index 3) to find actual column IDs
                                                const bottomRow = headerRows[headerRows.length - 1];
                                                if (bottomRow) {
                                                    // Get ALL cells from bottom row (including any merged cells)
                                                    const allBottomRowCells = Array.from(bottomRow.querySelectorAll('th'));
                                                    console.log('Price scorecard: Found', allBottomRowCells.length, 'total bottom row cells');
                                                    
                                                    // Calculate the data column start position by counting colspan of all previous headers
                                                    // This accounts for headers like "Africa" (colspan=14) that come before "Asia"
                                                    let topRowDataStart = 0;
                                                    
                                                    for (let i = 0; i < clickedCellIndex; i++) {
                                                        const cell = allTopRowCells[i];
                                                        const cellColId = cell.getAttribute('data-dash-column');
                                                        
                                                        // Skip Year/Month - they don't count as data columns
                                                        if (cellColId === 'Year' || cellColId === 'Month') {
                                                            continue;
                                                        }
                                                        
                                                        // Count the colspan of this header (how many data columns it spans)
                                                        const cellColspan = parseInt(cell.getAttribute('colspan') || cell.colSpan || '1');
                                                        topRowDataStart += cellColspan;
                                                    }
                                                    
                                                    console.log('Price scorecard: Top row data start:', topRowDataStart, '(clickedCellIndex:', clickedCellIndex, ')');
                                                    
                                                    // Now map to bottom row: count Year/Month in bottom row, then get data columns
                                                    let bottomRowDataColIndex = 0;
                                                    
                                                    for (let i = 0; i < allBottomRowCells.length; i++) {
                                                        const bottomCell = allBottomRowCells[i];
                                                        const bottomCellColId = bottomCell.getAttribute('data-dash-column');
                                                        
                                                        // Skip Year and Month in bottom row
                                                        if (bottomCellColId === 'Year' || bottomCellColId === 'Month') {
                                                            continue;
                                                        }
                                                        
                                                        // Check if this data column is within the span
                                                        // The clicked header spans from topRowDataStart to topRowDataStart + spanCount
                                                        if (bottomRowDataColIndex >= topRowDataStart && 
                                                            bottomRowDataColIndex < topRowDataStart + spanCount) {
                                                            // This column is within the span
                                                            if (bottomCellColId && bottomCellColId.startsWith('col_')) {
                                                                columnIds.add(bottomCellColId);
                                                            } else {
                                                                // If no data-dash-column, check if it has colspan and get columns from data cells
                                                                const cellColspan = parseInt(bottomCell.getAttribute('colspan') || bottomCell.colSpan || '1');
                                                                // For merged cells, we need to get the actual column IDs from data cells
                                                                // This is a fallback - try to find columns by position
                                                                console.log('Price scorecard: Bottom cell at index', i, 'has no data-dash-column, colspan:', cellColspan);
                                                            }
                                                        }
                                                        
                                                        // Increment data column index (only for non-Year/Month cells)
                                                        bottomRowDataColIndex++;
                                                    }
                                                    
                                                    console.log('Price scorecard: Found', columnIds.size, 'columns within span (expected', spanCount, ')');
                                                    
                                                    // If we still don't have enough columns, use alternative method
                                                    // Get column IDs in the order they appear in the first data row
                                                    if (columnIds.size < spanCount) {
                                                        console.log('Price scorecard: Not enough columns found (', columnIds.size, 'of', spanCount, '), trying alternative method');
                                                        
                                                        // Get the first data row - try multiple selectors
                                                        console.log('Price scorecard: Trying to find first data row...');
                                                        let firstDataRow = clickedSpreadsheet.querySelector('tbody tr');
                                                        let allFirstRowCells = [];
                                                        console.log('Price scorecard: tbody tr found?', !!firstDataRow);
                                                        if (!firstDataRow) {
                                                            firstDataRow = clickedSpreadsheet.querySelector('tr[data-dash-row]');
                                                            console.log('Price scorecard: tr[data-dash-row] found?', !!firstDataRow);
                                                        }
                                                        if (!firstDataRow) {
                                                            // Try to find any row with data cells
                                                            const allRows = clickedSpreadsheet.querySelectorAll('tr');
                                                            console.log('Price scorecard: Found', allRows.length, 'total rows');
                                                            for (let row of allRows) {
                                                                // Skip header rows (rows with th elements)
                                                                if (row.querySelector('th')) {
                                                                    continue;
                                                                }
                                                                // Check if this row has data cells
                                                                const dataCells = row.querySelectorAll('td[data-dash-column^="col_"]');
                                                                if (dataCells.length > 0) {
                                                                    firstDataRow = row;
                                                                    console.log('Price scorecard: Found data row with', dataCells.length, 'data cells');
                                                                    break;
                                                                }
                                                            }
                                                        }
                                                        
                                                        if (firstDataRow) {
                                                            // Get all cells from the first row in order (including Year/Month)
                                                            allFirstRowCells = Array.from(firstDataRow.querySelectorAll('td'));
                                                            console.log('Price scorecard: Found', allFirstRowCells.length, 'cells in first data row');
                                                            
                                                            // If no cells found with td, try a different approach - get all cells including th
                                                            if (allFirstRowCells.length === 0) {
                                                                console.log('Price scorecard: No td cells found, trying alternative approach');
                                                                // Try getting cells from the table body directly
                                                                const tbody = clickedSpreadsheet.querySelector('tbody');
                                                                if (tbody) {
                                                                    const firstTbodyRow = tbody.querySelector('tr');
                                                                    if (firstTbodyRow) {
                                                                        const tbodyCells = Array.from(firstTbodyRow.querySelectorAll('td, th'));
                                                                        console.log('Price scorecard: Found', tbodyCells.length, 'cells in first tbody row');
                                                                        allFirstRowCells.push(...tbodyCells);
                                                                    }
                                                                }
                                                                
                                                                // If still no cells, try getting from all rows
                                                                if (allFirstRowCells.length === 0) {
                                                                    const allTableRows = clickedSpreadsheet.querySelectorAll('tr');
                                                                    for (let row of allTableRows) {
                                                                        // Skip if it has th (header row)
                                                                        if (row.querySelector('th')) continue;
                                                                        const rowCells = Array.from(row.querySelectorAll('td'));
                                                                        if (rowCells.length > 0) {
                                                                            allFirstRowCells.push(...rowCells);
                                                                            console.log('Price scorecard: Found', rowCells.length, 'cells in alternative row');
                                                                            break;
                                                                        }
                                                                    }
                                                                }
                                                            }
                                                            
                                                            // Get column IDs in order, skipping Year/Month
                                                            const orderedColIds = [];
                                                            allFirstRowCells.forEach(cell => {
                                                                const colId = cell.getAttribute('data-dash-column');
                                                                if (colId && colId.startsWith('col_')) {
                                                                    orderedColIds.push(colId);
                                                                }
                                                            });
                                                            
                                                            console.log('Price scorecard: Ordered column IDs from first row:', orderedColIds.length, '(first 10:', orderedColIds.slice(0, 10), ')');
                                                            
                                                            // Get columns starting from topRowDataStart, spanning spanCount columns
                                                            const startIndex = topRowDataStart;
                                                            const endIndex = Math.min(startIndex + spanCount, orderedColIds.length);
                                                            
                                                            console.log('Price scorecard: Getting columns from index', startIndex, 'to', endIndex, 'from', orderedColIds.length, 'total columns');
                                                            
                                                            // Clear and rebuild columnIds with the correct range
                                                            columnIds.clear();
                                                            for (let i = startIndex; i < endIndex && i < orderedColIds.length; i++) {
                                                                columnIds.add(orderedColIds[i]);
                                                            }
                                                            
                                                            console.log('Price scorecard: After alternative method, found', columnIds.size, 'columns:', Array.from(columnIds));
                                                            
                                                            // If still not enough columns, we'll fall through to all data cells method
                                                            if (columnIds.size >= spanCount) {
                                                                // Enough columns found, we're done
                                                                console.log('Price scorecard: Sufficient columns found from first row method');
                                                            } else {
                                                                console.log('Price scorecard: Still not enough columns (', columnIds.size, 'of', spanCount, '), will try all data cells method');
                                                            }
                                                        }
                                                        
                                                        // If we still don't have enough columns, use comprehensive method
                                                        // Key insight: "Africa" spans 14 columns starting from the first data column (index 0)
                                                        // We need to get all columns in visual order from the first row, then fill in any missing ones
                                                        if (columnIds.size < spanCount) {
                                                            console.log('Price scorecard: Using comprehensive method to get all columns in visual order');
                                                            
                                                            // Step 1: Get all unique column IDs from all data cells
                                                            const allDataCells = clickedSpreadsheet.querySelectorAll('td[data-dash-column^="col_"]');
                                                            const allUniqueColIds = new Set();
                                                            allDataCells.forEach(cell => {
                                                                const colId = cell.getAttribute('data-dash-column');
                                                                if (colId) allUniqueColIds.add(colId);
                                                            });
                                                            console.log('Price scorecard: Found', allUniqueColIds.size, 'unique column IDs in table');
                                                            
                                                            // Step 2: Build complete position map by scanning all data rows
                                                            // Then extract the range from topRowDataStart to topRowDataStart + spanCount
                                                            const columnPositionMap = new Map(); // Maps position to column ID
                                                            
                                                            // Calculate the maximum position we need
                                                            const maxPositionNeeded = topRowDataStart + spanCount;
                                                            console.log('Price scorecard: Need columns from position', topRowDataStart, 'to', maxPositionNeeded - 1, '(spanCount:', spanCount, ')');
                                                            
                                                            // Get all data rows
                                                            const allDataRows = clickedSpreadsheet.querySelectorAll('tbody tr, tr[data-dash-row]');
                                                            console.log('Price scorecard: Scanning', allDataRows.length, 'data rows to build complete column map');
                                                            
                                                            // Scan each row to build the position map for ALL positions up to maxPositionNeeded
                                                            allDataRows.forEach((row, rowIndex) => {
                                                                if (row.querySelector('th')) return; // Skip header rows
                                                                
                                                                const rowCells = Array.from(row.querySelectorAll('td'));
                                                                let dataColIndex = 0; // Position in data columns (after Year/Month)
                                                                
                                                                rowCells.forEach(cell => {
                                                                    const colId = cell.getAttribute('data-dash-column');
                                                                    
                                                                    // Skip Year/Month
                                                                    if (colId === 'Year' || colId === 'Month') {
                                                                        return;
                                                                    }
                                                                    
                                                                    // Map this position if we haven't mapped it yet and it's in the range we need
                                                                    if (dataColIndex < maxPositionNeeded && !columnPositionMap.has(dataColIndex)) {
                                                                        if (colId && colId.startsWith('col_')) {
                                                                            columnPositionMap.set(dataColIndex, colId);
                                                                            if (dataColIndex >= topRowDataStart && dataColIndex < maxPositionNeeded) {
                                                                                console.log('Price scorecard: Mapped position', dataColIndex, 'to column', colId, '(from row', rowIndex, ')');
                                                                            }
                                                                        }
                                                                    }
                                                                    
                                                                    // Always increment position counter for data columns
                                                                    if (colId && colId.startsWith('col_')) {
                                                                        dataColIndex++;
                                                                    } else {
                                                                        // Empty cell or non-data cell - still count as a position
                                                                        dataColIndex++;
                                                                    }
                                                                });
                                                            });
                                                            
                                                            // Extract the range we need from the position map
                                                            const orderedColIds = [];
                                                            for (let i = topRowDataStart; i < maxPositionNeeded; i++) {
                                                                if (columnPositionMap.has(i)) {
                                                                    orderedColIds.push(columnPositionMap.get(i));
                                                                } else {
                                                                    console.log('Price scorecard: WARNING - No column found for position', i);
                                                                }
                                                            }
                                                            
                                                            console.log('Price scorecard: Built column map for range', topRowDataStart, 'to', maxPositionNeeded - 1, ', got', orderedColIds.length, 'columns:', orderedColIds);
                                                            
                                                            // orderedColIds already contains the correct range (from topRowDataStart to topRowDataStart + spanCount)
                                                            // Just add all of them to columnIds
                                                            console.log('Price scorecard: Final column list for header:', orderedColIds);
                                                            
                                                            // Clear and rebuild columnIds with the correct columns
                                                            columnIds.clear();
                                                            orderedColIds.forEach(colId => {
                                                                columnIds.add(colId);
                                                            });
                                                            
                                                            console.log('Price scorecard: After comprehensive method, found', columnIds.size, 'columns:', Array.from(columnIds));
                                                        }
                                                    }
                                                }
                                            } else {
                                                // No colspan or colspan = 1 - find all headers with the same text
                                                const allTopHeaders = Array.from(topRow.querySelectorAll('th[data-dash-column^="col_"]'));
                                                const matchingTopHeaders = allTopHeaders.filter(h => {
                                                    const hText = h.textContent.trim();
                                                    return hText === topHeaderText || h === header || h.contains(header);
                                                });
                                                
                                                console.log('Price scorecard: Found', matchingTopHeaders.length, 'headers with same text');
                                                
                                                matchingTopHeaders.forEach(topH => {
                                                    const colId = topH.getAttribute('data-dash-column');
                                                    if (colId) columnIds.add(colId);
                                                });
                                                
                                                // If no matches found, use the clicked header's column
                                                if (columnIds.size === 0 && columnId) {
                                                    columnIds.add(columnId);
                                                }
                                            }
                                            
                                            console.log('Price scorecard: Column IDs under top header:', Array.from(columnIds), '(', columnIds.size, 'columns)');
                                            
                                            // Highlight only the clicked top header cell itself (not all headers with same column IDs)
                                            header.classList.add('column-selected');
                                            header.style.backgroundColor = '#b3d9ff';
                                            header.style.color = '#1b365d';
                                            header.style.fontWeight = 'bold';
                                            
                                            // Highlight data cells for all columns under this top header
                                            console.log('Price scorecard: Highlighting data cells for', columnIds.size, 'columns');
                                            let totalCellsHighlighted = 0;
                                            columnIds.forEach(colId => {
                                                // Highlight all data cells for these columns (no border)
                                                const colCells = clickedSpreadsheet.querySelectorAll(`td[data-dash-column="${colId}"]`);
                                                console.log('Price scorecard: Found', colCells.length, 'data cells for column', colId);
                                                colCells.forEach(cell => {
                                                    const cellValue = getCellValue(cell);
                                                    // Highlight all cells, not just numeric ones
                                                    cell.classList.add('column-cell-selected');
                                                    cell.style.backgroundColor = '#b3d9ff';
                                                    cell.style.border = ''; // No border
                                                    cell.style.fontWeight = '600';
                                                    cell.style.color = '#1b365d';
                                                    cell.style.opacity = '1';
                                                    totalCellsHighlighted++;
                                                });
                                            });
                                            console.log('Price scorecard: Total cells highlighted:', totalCellsHighlighted);
                                            
                                            clickedSpreadsheet.classList.add('column-selection-active');
                                            
                                            // Dim other columns
                                            const allDataCells = clickedSpreadsheet.querySelectorAll('td[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Month"])');
                                            allDataCells.forEach(cell => {
                                                const cellColId = cell.getAttribute('data-dash-column');
                                                if (!columnIds.has(cellColId)) {
                                                    cell.style.opacity = '0.3';
                                                }
                                            });
                                        }
                                    } else {
                                        // Bottom header clicked - highlight only the bottom header level and data cells
                                        console.log('Price scorecard: ✓ BOTTOM HEADER CLICKED - Highlighting bottom header level and data cells');
                                        
                                        // Only highlight headers at the bottom level (last row)
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
                                        
                                        // Highlight all data cells for this column (no border)
                                        const columnCells = clickedSpreadsheet.querySelectorAll(`td[data-dash-column="${columnId}"]`);
                                        console.log('Price scorecard: Found', columnCells.length, 'cells for column', columnId);
                                        
                                        if (columnCells.length === 0) {
                                            console.log('Price scorecard: WARNING - No data cells found for column', columnId);
                                        }
                                        
                                        columnCells.forEach(cell => {
                                            const cellValue = getCellValue(cell);
                                            if (cellValue && cellValue !== '' && cellValue !== 'NaN' && !isNaN(parseFloat(cellValue))) {
                                                cell.classList.add('column-cell-selected');
                                                cell.style.backgroundColor = '#b3d9ff';
                                                cell.style.border = ''; // No border
                                                cell.style.fontWeight = '600';
                                                cell.style.color = '#1b365d';
                                                cell.style.opacity = '1';
                                            }
                                        });
                                        
                                        clickedSpreadsheet.classList.add('column-selection-active');
                                        
                                        // Dim other columns
                                        const allDataCells = clickedSpreadsheet.querySelectorAll('td[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Month"])');
                                        console.log('Price scorecard: Dimming', allDataCells.length, 'other data cells');
                                        allDataCells.forEach(cell => {
                                            if (!cell.classList.contains('column-cell-selected')) {
                                                cell.style.opacity = '0.3';
                                            }
                                        });
                                    }
                                } else {
                                    // Middle header - highlight the clicked header level and check if it spans columns
                                    console.log('Price scorecard: ⚠ MIDDLE HEADER (index', headerIndex, 'of', totalHeaderRows, ')');
                                    
                                    // Check if this header spans multiple columns
                                    const headerColspan = header.getAttribute('colspan') || header.colSpan;
                                    const spanCount = headerColspan ? parseInt(headerColspan) : 1;
                                    const headerText = header.textContent.trim();
                                    
                                    console.log('Price scorecard: Middle header text:', headerText, ', colspan:', spanCount);
                                    
                                    // Get all columns under this middle header
                                    const columnIds = new Set();
                                    
                                    if (spanCount > 1) {
                                        // Header spans multiple columns - find all columns under it
                                        const currentRow = headerRows[headerIndex];
                                        if (currentRow) {
                                            const allRowCells = Array.from(currentRow.querySelectorAll('th'));
                                            let clickedCellIndex = -1;
                                            
                                            // Find clicked header's position
                                            for (let i = 0; i < allRowCells.length; i++) {
                                                if (allRowCells[i] === header || allRowCells[i].contains(header)) {
                                                    clickedCellIndex = i;
                                                    break;
                                                }
                                            }
                                            
                                            console.log('Price scorecard: Middle header cell index:', clickedCellIndex);
                                            
                                            // Count data columns before this header in the middle row
                                            // We need to count how many data column positions come before the clicked header
                                            let columnsBefore = 0;
                                            
                                            for (let i = 0; i < clickedCellIndex; i++) {
                                                const cell = allRowCells[i];
                                                const cellColId = cell.getAttribute('data-dash-column');
                                                
                                                // Skip Year/Month
                                                if (cellColId === 'Year' || cellColId === 'Month') {
                                                    continue;
                                                }
                                                
                                                // Count the colspan of this cell (how many data columns it spans)
                                                const cellColspan = parseInt(cell.getAttribute('colspan') || cell.colSpan || '1');
                                                columnsBefore += cellColspan;
                                            }
                                            
                                            console.log('Price scorecard: Middle header - columnsBefore:', columnsBefore, '(clickedCellIndex:', clickedCellIndex, ')');
                                            
                                            // Use comprehensive method to find columns - same as top header
                                            // Get first data row to build column position map
                                            let firstDataRow = clickedSpreadsheet.querySelector('tbody tr');
                                            if (!firstDataRow) {
                                                firstDataRow = clickedSpreadsheet.querySelector('tr[data-dash-row]');
                                            }
                                            if (!firstDataRow) {
                                                const allRows = clickedSpreadsheet.querySelectorAll('tr');
                                                for (let row of allRows) {
                                                    if (row.querySelector('th')) continue;
                                                    const dataCells = row.querySelectorAll('td[data-dash-column^="col_"]');
                                                    if (dataCells.length > 0) {
                                                        firstDataRow = row;
                                                        break;
                                                    }
                                                }
                                            }
                                            
                                            if (firstDataRow) {
                                                // Build column position map from all data rows
                                                const allDataRows = clickedSpreadsheet.querySelectorAll('tbody tr, tr[data-dash-row]');
                                                const columnPositionMap = new Map();
                                                
                                                console.log('Price scorecard: Building column position map for middle header, starting at position', columnsBefore);
                                                
                                                // Scan all rows to build position map
                                                allDataRows.forEach(row => {
                                                    if (row.querySelector('th')) return;
                                                    
                                                    const rowCells = Array.from(row.querySelectorAll('td'));
                                                    let dataColIndex = 0;
                                                    
                                                    rowCells.forEach(cell => {
                                                        const colId = cell.getAttribute('data-dash-column');
                                                        if (colId === 'Year' || colId === 'Month') return;
                                                        
                                                        // Map columns in the span range
                                                        if (dataColIndex >= columnsBefore && dataColIndex < columnsBefore + spanCount) {
                                                            if (!columnPositionMap.has(dataColIndex) && colId && colId.startsWith('col_')) {
                                                                columnPositionMap.set(dataColIndex, colId);
                                                            }
                                                        }
                                                        
                                                        if (colId && colId.startsWith('col_')) {
                                                            dataColIndex++;
                                                        } else {
                                                            dataColIndex++;
                                                        }
                                                    });
                                                });
                                                
                                                // Build ordered list from position map
                                                for (let i = columnsBefore; i < columnsBefore + spanCount; i++) {
                                                    if (columnPositionMap.has(i)) {
                                                        columnIds.add(columnPositionMap.get(i));
                                                    }
                                                }
                                                
                                                console.log('Price scorecard: Found', columnIds.size, 'columns under middle header (positions', columnsBefore, 'to', columnsBefore + spanCount - 1, ')');
                                            } else {
                                                // Fallback: use bottom row
                                                const bottomRow = headerRows[headerRows.length - 1];
                                                if (bottomRow) {
                                                    const allBottomHeaders = Array.from(bottomRow.querySelectorAll('th[data-dash-column^="col_"]'));
                                                    console.log('Price scorecard: Fallback - Found', allBottomHeaders.length, 'bottom headers');
                                                    
                                                    for (let i = 0; i < spanCount && (columnsBefore + i) < allBottomHeaders.length; i++) {
                                                        const bottomHeader = allBottomHeaders[columnsBefore + i];
                                                        const colId = bottomHeader.getAttribute('data-dash-column');
                                                        if (colId) {
                                                            columnIds.add(colId);
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    } else {
                                        // Single column - use the clicked column
                                        console.log('Price scorecard: Single column middle header, using columnId:', columnId);
                                        columnIds.add(columnId);
                                    }
                                    
                                    console.log('Price scorecard: Final columnIds for middle header:', Array.from(columnIds), '(', columnIds.size, 'columns)');
                                    
                                    // Highlight only the clicked header cell itself (not other headers with same text)
                                    if (headerIndex >= 0 && headerRows.length > 0) {
                                        const currentRow = headerRows[headerIndex];
                                        if (currentRow) {
                                            // Simply highlight the clicked header itself
                                            // If it has colspan, it will visually span multiple columns
                                            header.classList.add('column-selected');
                                            header.style.backgroundColor = '#b3d9ff';
                                            header.style.color = '#1b365d';
                                            header.style.fontWeight = 'bold';
                                            
                                            console.log('Price scorecard: Highlighted clicked header only');
                                        }
                                    }
                                    
                                    // Highlight data cells for all columns under this middle header
                                    if (columnIds.size > 0) {
                                        console.log('Price scorecard: Highlighting data cells for', columnIds.size, 'columns:', Array.from(columnIds));
                                        let totalCellsHighlighted = 0;
                                        columnIds.forEach(colId => {
                                            const colCells = clickedSpreadsheet.querySelectorAll(`td[data-dash-column="${colId}"]`);
                                            console.log('Price scorecard: Found', colCells.length, 'data cells for column', colId);
                                            colCells.forEach(cell => {
                                                // Highlight all cells, not just numeric ones
                                                cell.classList.add('column-cell-selected');
                                                cell.style.backgroundColor = '#b3d9ff';
                                                cell.style.border = ''; // No border
                                                cell.style.fontWeight = '600';
                                                cell.style.color = '#1b365d';
                                                cell.style.opacity = '1';
                                                totalCellsHighlighted++;
                                            });
                                        });
                                        console.log('Price scorecard: Total cells highlighted:', totalCellsHighlighted);
                                        
                                        if (totalCellsHighlighted === 0) {
                                            console.log('Price scorecard: WARNING - No cells were highlighted! Check if column IDs are correct.');
                                        }
                                        
                                        clickedSpreadsheet.classList.add('column-selection-active');
                                        
                                        // Dim other columns
                                        const allDataCells = clickedSpreadsheet.querySelectorAll('td[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Month"])');
                                        allDataCells.forEach(cell => {
                                            const cellColId = cell.getAttribute('data-dash-column');
                                            if (!columnIds.has(cellColId)) {
                                                cell.style.opacity = '0.3';
                                            }
                                        });
                                    } else {
                                        clickedSpreadsheet.classList.remove('column-selection-active');
                                    }
                                }
                            }
                            return false; // Prevent default
                        }
                        
                        // Handle row highlighting when clicking on Month cell
                        const monthCell = event.target.closest('td[data-dash-column="Month"]');
                        if (monthCell) {
                            event.stopPropagation();
                            console.log('Price scorecard: Month cell clicked');
                            
                            // Clear column selections first
                            clearAllColumnSelections(clickedSpreadsheet);
                            clearAllRowSelections(clickedSpreadsheet);
                            if (window.priceScorecardState) {
                                window.priceScorecardState.selectedColumnId = null;
                            }
                            
                            // Get the row containing this Month cell
                            const row = monthCell.closest('tr');
                            if (row) {
                                const rowIndex = row.getAttribute('data-dash-row');
                                console.log('Price scorecard: Row index:', rowIndex);
                                
                                // Check if this row is already selected
                                if (window.priceScorecardState && window.priceScorecardState.selectedRowIndex === rowIndex) {
                                    // Deselect row
                                    console.log('Price scorecard: Deselecting row', rowIndex);
                                    const allRowCells = clickedSpreadsheet.querySelectorAll(`td[data-dash-row="${rowIndex}"]`);
                                    console.log('Price scorecard: Found', allRowCells.length, 'cells in row');
                                    allRowCells.forEach(c => {
                                        c.classList.remove('row-cell-selected');
                                        c.style.backgroundColor = '';
                                        c.style.border = '';
                                    });
                                    clickedSpreadsheet.classList.remove('row-selection-active');
                                    
                                    // Reset opacity for all rows
                                    const allDataRows = clickedSpreadsheet.querySelectorAll('tbody tr');
                                    allDataRows.forEach(r => {
                                        const rowCells = r.querySelectorAll('td[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Month"])');
                                        rowCells.forEach(c => {
                                            c.style.opacity = '';
                                        });
                                    });
                                    
                                    if (window.priceScorecardState) {
                                        window.priceScorecardState.selectedRowIndex = null;
                                    }
                                } else {
                                    // Clear any previous row selection
                                    console.log('Price scorecard: Selecting row', rowIndex);
                                    const allSelectedRows = clickedSpreadsheet.querySelectorAll('td.row-cell-selected');
                                    allSelectedRows.forEach(c => {
                                        c.classList.remove('row-cell-selected');
                                        c.style.backgroundColor = '';
                                        c.style.border = '';
                                    });
                                    clickedSpreadsheet.classList.remove('row-selection-active');
                                    
                                    // Select new row
                                    const allRowCells = clickedSpreadsheet.querySelectorAll(`td[data-dash-row="${rowIndex}"]`);
                                    console.log('Price scorecard: Found', allRowCells.length, 'cells in row');
                                    let highlightedCount = 0;
                                    allRowCells.forEach(c => {
                                        const colId = c.getAttribute('data-dash-column');
                                        // Skip Year and Month columns
                                        if (colId !== 'Year' && colId !== 'Month') {
                                            const cellValue = getCellValue(c);
                                            if (cellValue && cellValue !== '' && cellValue !== 'NaN' && !isNaN(parseFloat(cellValue))) {
                                                c.classList.add('row-cell-selected');
                                                c.style.backgroundColor = '#b3d9ff';
                                                c.style.border = ''; // No border
                                                c.style.fontWeight = '600';
                                                c.style.color = '#1b365d';
                                                highlightedCount++;
                                            }
                                        }
                                    });
                                    console.log('Price scorecard: Highlighted', highlightedCount, 'cells in row');
                                    
                                    clickedSpreadsheet.classList.add('row-selection-active');
                                    
                                    // Dim other rows
                                    const allDataRows = clickedSpreadsheet.querySelectorAll('tbody tr');
                                    console.log('Price scorecard: Found', allDataRows.length, 'data rows');
                                    allDataRows.forEach(r => {
                                        const rIndex = r.getAttribute('data-dash-row');
                                        if (rIndex !== rowIndex) {
                                            const rowCells = r.querySelectorAll('td[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Month"])');
                                            rowCells.forEach(c => {
                                                c.style.opacity = '0.3';
                                            });
                                        } else {
                                            // Keep selected row at full opacity
                                            const rowCells = r.querySelectorAll('td[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Month"])');
                                            rowCells.forEach(c => {
                                                c.style.opacity = '1';
                                            });
                                        }
                                    });
                                    
                                    if (window.priceScorecardState) {
                                        window.priceScorecardState.selectedRowIndex = rowIndex;
                                    }
                                }
                            }
                            return false;
                        }
                        
                        // If clicking on a data cell, clear column and row selections
                        const cell = event.target.closest('td[data-dash-column]');
                        if (cell) {
                            const columnId = cell.getAttribute('data-dash-column');
                            if (columnId && columnId !== 'Year' && columnId !== 'Month') {
                                clearAllColumnSelections(clickedSpreadsheet);
                                
                                // Clear row selection
                                const allSelectedRows = clickedSpreadsheet.querySelectorAll('td.row-cell-selected');
                                allSelectedRows.forEach(c => {
                                    c.classList.remove('row-cell-selected');
                                    c.style.backgroundColor = '';
                                    c.style.border = '';
                                });
                                clickedSpreadsheet.classList.remove('row-selection-active');
                                
                                // Reset opacity for all rows
                                const allDataRows = clickedSpreadsheet.querySelectorAll('tbody tr');
                                allDataRows.forEach(r => {
                                    const rowCells = r.querySelectorAll('td[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Month"])');
                                    rowCells.forEach(c => {
                                        c.style.opacity = '';
                                    });
                                });
                                
                                if (window.priceScorecardState) {
                                    window.priceScorecardState.selectedColumnId = null;
                                    window.priceScorecardState.selectedRowIndex = null;
                                }
                            }
                        }
                    };
                    
                    spreadsheet._priceScorecardClickHandler = clickHandler;
                    
                    // Add click handler with capture phase
                    spreadsheet.addEventListener('click', spreadsheet._priceScorecardClickHandler, true);
                    console.log('Price scorecard: Click handler attached');
                }
                
                // Clear selection on outside click (use a single global handler)
                if (!window.priceScorecardOutsideClickHandler) {
                    window.priceScorecardOutsideClickHandler = function(event) {
                        const tableEl = document.getElementById('price-scorecard-table');
                        if (!tableEl) return;
                        const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                        if (!spreadsheet) return;
                        
                        if (!spreadsheet.contains(event.target)) {
                            clearAllColumnSelections(spreadsheet);
                            clearAllRowSelections(spreadsheet);
                            if (window.priceScorecardState) {
                                window.priceScorecardState.selectedColumnId = null;
                                window.priceScorecardState.selectedRowIndex = null;
                            }
                        }
                    };
                    document.addEventListener('click', window.priceScorecardOutsideClickHandler);
                }
                
                // Reset enhanced flag when container updates (table was re-rendered)
                // This ensures the table is re-enhanced when switching tabs
                console.log('Price scorecard: Container updated, checking for table...');
                const tableEl = document.getElementById('price-scorecard-table');
                if (tableEl) {
                    console.log('Price scorecard: Table element found');
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    if (spreadsheet) {
                        console.log('Price scorecard: Spreadsheet container found, resetting enhancement');
                        // Force reset to allow re-enhancement when switching tabs
                        spreadsheet.dataset.priceScorecardEnhanced = 'false';
                        
                        // Remove old click handler if exists
                        if (spreadsheet._priceScorecardClickHandler) {
                            spreadsheet.removeEventListener('click', spreadsheet._priceScorecardClickHandler, true);
                            spreadsheet._priceScorecardClickHandler = null;
                            console.log('Price scorecard: Removed old click handler');
                        }
                        
                        // Clear any existing selections
                        clearAllColumnSelections(spreadsheet);
                        clearAllRowSelections(spreadsheet);
                        
                        if (window.priceScorecardState) {
                            window.priceScorecardState.selectedColumnId = null;
                            window.priceScorecardState.selectedRowIndex = null;
                            window.priceScorecardState.lastTableSignature = null; // Reset signature to force re-enhancement
                        }
                        
                        // Force enhancement to run by calling tryEnhance after a short delay
                        // This ensures the table is enhanced even if the structure detection fails
                        setTimeout(function() {
                            console.log('Price scorecard: Forcing enhancement after container update');
                            tryEnhance();
                        }, 200);
                    } else {
                        console.log('Price scorecard: WARNING - Spreadsheet container not found in table');
                    }
                } else {
                    console.log('Price scorecard: WARNING - Table element not found');
                }
                
                // Apply enhancements with multiple attempts to ensure table is rendered
                function tryEnhance() {
                    console.log('Price scorecard: tryEnhance called');
                    const tableEl = document.getElementById('price-scorecard-table');
                    if (!tableEl) {
                        console.log('Price scorecard: tryEnhance - Table element not found');
                        return false;
                    }
                    
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    if (!spreadsheet) {
                        console.log('Price scorecard: tryEnhance - Spreadsheet container not found');
                        return false;
                    }
                    
                    // Check if headers exist
                    const headers = spreadsheet.querySelectorAll('th[data-dash-column]');
                    console.log('Price scorecard: tryEnhance - Found', headers.length, 'headers');
                    if (headers.length === 0) {
                        console.log('Price scorecard: tryEnhance - No headers found, returning false');
                        return false;
                    }
                    
                    // Check enhancement status
                    const isEnhanced = spreadsheet.dataset.priceScorecardEnhanced === 'true';
                    console.log('Price scorecard: tryEnhance - Already enhanced?', isEnhanced);
                    
                    // Only enhance if not already enhanced
                    if (!isEnhanced) {
                        console.log('Price scorecard: tryEnhance - Calling enhanceTable()');
                        enhanceTable();
                        return true;
                    }
                    
                    console.log('Price scorecard: tryEnhance - Already enhanced, skipping');
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
                if (!window.priceScorecardMutationObserver) {
                    window.priceScorecardMutationObserver = new MutationObserver(function(mutations) {
                        const tableEl = document.getElementById('price-scorecard-table');
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
                                    (spreadsheet.dataset.priceScorecardEnhanced !== 'true' || 
                                     window.priceScorecardState.lastTableSignature !== tableSignature)) {
                                    setTimeout(function() {
                                        enhanceTable();
                                    }, 100);
                                }
                            }
                        }
                    });
                    window.priceScorecardMutationObserver.observe(document.body, { 
                        childList: true, 
                        subtree: true 
                    });
                }
                
                // Also try to enhance on next tick
                setTimeout(function() {
                    tryEnhance();
                }, 50);
                
            } catch (error) {
                console.error('Price scorecard table enhancer error:', error);
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('price-scorecard-dummy-output', 'children'),
        Input('price-scorecard-table-container', 'children'),
        prevent_initial_call=False
    )
