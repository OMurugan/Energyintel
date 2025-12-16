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
                }
            ]
        )
        
        return table
