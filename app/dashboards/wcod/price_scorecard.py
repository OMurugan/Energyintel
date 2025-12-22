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
        df['Quarter'] = 'Q' + df['date'].dt.quarter.astype(str)
        df['Month'] = df['date'].dt.strftime('%B')
        df['Day'] = '1'  # Day column should always show '1' for each month
        
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
        # First, ensure we have unique (Year, Quarter, Month, Day, column_key) combinations
        df_pivot = df.groupby(['Year', 'Quarter', 'Month', 'Day', 'column_key'])['price'].first().reset_index()
        
        # Pivot using unstack for better performance
        pivot_df = df_pivot.set_index(['Year', 'Quarter', 'Month', 'Day', 'column_key'])['price'].unstack(fill_value=None).reset_index()
        
        # Ensure all column keys are present (add missing ones as None columns)
        missing_keys = set(ordered_column_keys) - set(pivot_df.columns)
        for key in missing_keys:
            pivot_df[key] = None
        
        # Reorder columns efficiently - build list once
        reordered_cols = ['Year', 'Quarter', 'Month', 'Day'] + [key for key in ordered_column_keys if key in pivot_df.columns]
        pivot_df = pivot_df[reordered_cols]
        
        # Rename columns to col_0, col_1, etc. for consistency with existing code
        value_cols_final = [col for col in pivot_df.columns if col not in ['Year', 'Quarter', 'Month', 'Day']]
        col_mapping = dict(zip(value_cols_final, [f'col_{i}' for i in range(len(value_cols_final))]))
        pivot_df = pivot_df.rename(columns=col_mapping)
        
        # Ensure Year, Quarter, Month, and Day are strings, convert value columns to numeric in one pass
        pivot_df['Year'] = pivot_df['Year'].astype(str)
        pivot_df['Quarter'] = pivot_df['Quarter'].astype(str)
        pivot_df['Month'] = pivot_df['Month'].astype(str)
        pivot_df['Day'] = pivot_df['Day'].astype(str)
        
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
    
    # First four columns: Year, Quarter, Month, and Day
    columns.append({'name': ['', '', '', 'Year'], 'id': 'Year'})
    columns.append({'name': ['', '', '', 'Quarter'], 'id': 'Quarter'})
    columns.append({'name': ['', '', '', 'Month'], 'id': 'Month'})
    columns.append({'name': ['', '', '', 'Day'], 'id': 'Day'})
    
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
    
    # Quarter order for descending sort
    quarter_order = {'Q4': 4, 'Q3': 3, 'Q2': 2, 'Q1': 1}
    
    # Track row indices for year boundaries
    year_boundary_rows = []
    current_row_index = 0
    
    # Group by year, quarter, month, and day, then sort
    for year in sorted(data_df['Year'].unique(), reverse=True):
        year_data = data_df[data_df['Year'] == year].copy()
        
        # Add quarter order for sorting
        year_data['QuarterOrder'] = year_data['Quarter'].map(quarter_order).fillna(0)
        
        # Sort months in descending order (December to January)
        year_data['Month'] = pd.Categorical(
            year_data['Month'], 
            categories=months_order, 
            ordered=True
        )
        
        # Convert Day to numeric for sorting
        year_data['DayInt'] = pd.to_numeric(year_data['Day'], errors='coerce').fillna(0)
        
        # Sort by Quarter (descending), Month (descending), Day (descending)
        year_data = year_data.sort_values(['QuarterOrder', 'Month', 'DayInt'], ascending=[False, True, False])
        
        # Track current quarter, month, and day for showing values only in first row
        current_quarter = None
        current_month = None
        current_day = None
        
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
            
            # Show quarter only in the first row of each quarter group
            quarter_value = ''
            # Convert to string for comparison to handle any type mismatches
            row_quarter = str(row['Quarter']).strip() if pd.notna(row['Quarter']) else ''
            if row_quarter != current_quarter and row_quarter != '':
                quarter_value = row_quarter
                current_quarter = row_quarter
                current_month = None  # Reset month when quarter changes
                current_day = None   # Reset day when quarter changes
            
            # Show month only in the first row of each month group
            month_value = ''
            if row['Month'] != current_month:
                month_value = str(row['Month'])
                current_month = row['Month']
                current_day = None  # Reset day when month changes
            
            # Day should always show '1' for each month row (not just first row of day group)
            day_value = str(row['Day']) if pd.notna(row['Day']) and str(row['Day']).strip() != '' else '1'
            
            record = {
                'Year': year_value,  # Show year only in first row of group, formatted without decimal
                'Quarter': quarter_value,  # Show quarter only in first row of quarter group
                'Month': month_value,  # Show month only in first row of month group
                'Day': day_value  # Show day only in first row of day group
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
        try:
            if submenu != 'price-scorecard':
                return html.Div()
            
            # Use the selected type filter
            type_filter = selected_type if selected_type else 'Cost to Refiners'
            
            # Load the SQL data
            result = load_sql_data(type_filter)
            if result is None:
                return html.Div(f"Error: Failed to load data for {type_filter}", style={'padding': '20px', 'color': 'red'})
            delivery_locations, countries, crude_types, pricing_terms, data_df = result
            
            if data_df is None or data_df.empty:
                error_msg = f"Error loading data for type: {type_filter}"
                if delivery_locations is None:
                    error_msg += " - Query returned no results or error occurred"
                return html.Div(error_msg, style={'padding': '20px', 'color': 'red'})
            
            if len(data_df) == 0:
                return html.Div("No data rows found for selected filter", style={'padding': '20px', 'color': 'red'})
            
            # Build columns with multi-level structure
            columns = build_column_structure(delivery_locations, countries, crude_types, pricing_terms)
            
            # Count value columns (excluding Year, Quarter, Month, and Day)
            num_value_cols = len([c for c in columns if c['id'].startswith('col_')])
            
            # Get actual data columns from the dataframe
            data_cols = [col for col in data_df.columns if col.startswith('col_')]
            actual_num_cols = len(data_cols)
            
            # Use the minimum to ensure we don't go out of bounds
            num_cols_to_use = min(num_value_cols, actual_num_cols)
            
            # If we have more columns defined than data columns, trim the columns
            if num_value_cols > actual_num_cols:
                # Keep Year, Quarter, Month, Day, and only the columns we have data for
                value_columns = [c for c in columns if c['id'].startswith('col_')]
                columns_to_keep = value_columns[:actual_num_cols]
                columns = [c for c in columns if c['id'] in ['Year', 'Quarter', 'Month', 'Day']] + columns_to_keep
            
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
                'overflowY': 'auto',
                'fontSize': '11px',
                'border': 'none',  # Remove outer border
                'maxHeight': '600px',
                'width': '100%',
                'borderCollapse': 'collapse',
                'position': 'relative'
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
                    'color': '#1b365d',  # Apply color to Year column
                    'minWidth': '80px',
                    'width': '80px'
                },
                {
                    'if': {'column_id': 'Month'},
                    'textAlign': 'left',
                    'fontWeight': 'normal',
                    'color': '#1b365d',  # Apply color to Month column
                    'minWidth': '80px',
                    'width': '80px'
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
            page_action='none',
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
                        'selector': '#price-scorecard-table .dash-spreadsheet-container td.row-cell-selected',
                        'rule': 'background-color: #b3d9ff !important; border: none !important; font-weight: 600 !important; color: #1b365d !important; opacity: 1 !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container.column-selection-active td:not([data-dash-column="Year"]):not([data-dash-column="Quarter"]):not([data-dash-column="Month"]):not([data-dash-column="Day"]):not(.column-cell-selected)',
                        'rule': 'opacity: 0.3 !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container.row-selection-active tbody tr:not(.row-selected) td',
                        'rule': 'opacity: 0.3 !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container.row-selection-active tbody tr.row-selected td.row-cell-selected',
                        'rule': 'opacity: 1 !important; background-color: #b3d9ff !important; color: #1b365d !important; font-weight: 600 !important; border: none !important;'
                    },
                    {
                        'selector': '#price-scorecard-table-container',
                        'rule': 'overflow-x: auto !important; overflow-y: visible !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container',
                        'rule': 'overflow-x: auto !important; overflow-y: auto !important; position: relative !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-table-container',
                        'rule': 'overflow-x: auto !important;'
                    },
                    {
                        'selector': '#price-scorecard-table table',
                        'rule': 'border-collapse: separate !important; border-spacing: 0 !important;'
                    },
                    {
                        'selector': '#price-scorecard-table th[data-dash-column="Year"], #price-scorecard-table th[data-dash-column="Quarter"], #price-scorecard-table th[data-dash-column="Month"], #price-scorecard-table th[data-dash-column="Day"]',
                        'rule': 'min-width: 80px !important; width: 80px !important; position: sticky !important; background-color: white !important; z-index: 25 !important;'
                    },
                    {
                        'selector': '#price-scorecard-table th[data-dash-column="Year"]',
                        'rule': 'left: 0 !important;'
                    },
                    {
                        'selector': '#price-scorecard-table th[data-dash-column="Quarter"]',
                        'rule': 'left: 80px !important;'
                    },
                    {
                        'selector': '#price-scorecard-table th[data-dash-column="Month"]',
                        'rule': 'left: 160px !important;'
                    },
                    {
                        'selector': '#price-scorecard-table th[data-dash-column="Day"]',
                        'rule': 'left: 240px !important;'
                    },
                    {
                        'selector': '#price-scorecard-table td[data-dash-column="Year"], #price-scorecard-table td[data-dash-column="Quarter"], #price-scorecard-table td[data-dash-column="Month"], #price-scorecard-table td[data-dash-column="Day"]',
                        'rule': 'min-width: 80px !important; width: 80px !important; position: sticky !important; z-index: 15 !important;'
                    },
                    {
                        'selector': '#price-scorecard-table td[data-dash-column="Year"]',
                        'rule': 'left: 0 !important;'
                    },
                    {
                        'selector': '#price-scorecard-table td[data-dash-column="Quarter"]',
                        'rule': 'left: 80px !important;'
                    },
                    {
                        'selector': '#price-scorecard-table td[data-dash-column="Month"]',
                        'rule': 'left: 160px !important;'
                    },
                    {
                        'selector': '#price-scorecard-table td[data-dash-column="Day"]',
                        'rule': 'left: 240px !important;'
                    },
                    {
                        'selector': '#price-scorecard-table tbody tr:nth-child(odd) td[data-dash-column="Year"], #price-scorecard-table tbody tr:nth-child(odd) td[data-dash-column="Quarter"], #price-scorecard-table tbody tr:nth-child(odd) td[data-dash-column="Month"], #price-scorecard-table tbody tr:nth-child(odd) td[data-dash-column="Day"]',
                        'rule': 'background-color: #f9f9f9 !important;'
                    },
                    {
                        'selector': '#price-scorecard-table tbody tr:nth-child(even) td[data-dash-column="Year"], #price-scorecard-table tbody tr:nth-child(even) td[data-dash-column="Quarter"], #price-scorecard-table tbody tr:nth-child(even) td[data-dash-column="Month"], #price-scorecard-table tbody tr:nth-child(even) td[data-dash-column="Day"]',
                        'rule': 'background-color: white !important;'
                    },
                    {
                        'selector': '#price-scorecard-table thead tr th[data-dash-column="Year"], #price-scorecard-table thead tr th[data-dash-column="Quarter"], #price-scorecard-table thead tr th[data-dash-column="Month"], #price-scorecard-table thead tr th[data-dash-column="Day"]',
                        'rule': 'background-color: white !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container table thead tr th:first-child',
                        'rule': 'position: sticky !important; left: 0 !important; z-index: 25 !important; background-color: white !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container table thead tr th:nth-child(2)',
                        'rule': 'position: sticky !important; left: 80px !important; z-index: 25 !important; background-color: white !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container table thead tr th:nth-child(3)',
                        'rule': 'position: sticky !important; left: 160px !important; z-index: 25 !important; background-color: white !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container table thead tr th:nth-child(4)',
                        'rule': 'position: sticky !important; left: 240px !important; z-index: 25 !important; background-color: white !important;'
                    },
                    {
                        'selector': '#price-scorecard-table thead tr:first-child th:first-child, #price-scorecard-table thead tr:first-child th:nth-child(2), #price-scorecard-table thead tr:first-child th:nth-child(3), #price-scorecard-table thead tr:first-child th:nth-child(4)',
                        'rule': 'position: sticky !important; z-index: 30 !important; background-color: white !important;'
                    },
                    {
                        'selector': '#price-scorecard-table thead tr:first-child th:first-child',
                        'rule': 'left: 0 !important;'
                    },
                    {
                        'selector': '#price-scorecard-table thead tr:first-child th:nth-child(2)',
                        'rule': 'left: 80px !important;'
                    },
                    {
                        'selector': '#price-scorecard-table thead tr th:first-child, #price-scorecard-table thead tr th:nth-child(2)',
                        'rule': 'position: sticky !important; background-color: white !important; z-index: 25 !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container table tbody tr td:first-child',
                        'rule': 'position: sticky !important; left: 0 !important; z-index: 15 !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container table tbody tr td:nth-child(2)',
                        'rule': 'position: sticky !important; left: 80px !important; z-index: 15 !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container table tbody tr:nth-child(odd) td:first-child, #price-scorecard-table .dash-spreadsheet-container table tbody tr:nth-child(odd) td:nth-child(2)',
                        'rule': 'background-color: #f9f9f9 !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container table tbody tr:nth-child(even) td:first-child, #price-scorecard-table .dash-spreadsheet-container table tbody tr:nth-child(even) td:nth-child(2)',
                        'rule': 'background-color: white !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Year"] .year-header-toggle, #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Quarter"] .quarter-header-toggle, #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Month"] .month-header-toggle, #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Day"] .day-header-toggle',
                        'rule': 'display: none !important; margin-left: 6px !important; width: 16px !important; height: 16px !important; line-height: 14px !important; text-align: center !important; font-size: 12px !important; font-weight: normal !important; color: #505050 !important; border: 1px solid #d0d0d0 !important; border-radius: 2px !important; background-color: #ffffff !important; user-select: none !important; cursor: pointer !important; vertical-align: middle !important; flex-shrink: 0 !important; box-sizing: border-box !important; transition: all 0.15s ease !important; font-family: Arial, sans-serif !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Year"]:hover .year-header-toggle, #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Year"] .year-header-toggle:hover',
                        'rule': 'display: inline-block !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Quarter"]:hover .quarter-header-toggle, #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Quarter"] .quarter-header-toggle:hover',
                        'rule': 'display: inline-block !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Month"]:hover .month-header-toggle, #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Month"] .month-header-toggle:hover',
                        'rule': 'display: inline-block !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Day"]:hover .day-header-toggle, #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Day"] .day-header-toggle:hover',
                        'rule': 'display: inline-block !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Year"] .year-header-toggle:hover, #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Quarter"] .quarter-header-toggle:hover, #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Month"] .month-header-toggle:hover, #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Day"] .day-header-toggle:hover',
                        'rule': 'color: #333333 !important; border-color: #a0a0a0 !important; background-color: #f0f0f0 !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Quarter"], #price-scorecard-table .dash-spreadsheet-container td[data-dash-column="Quarter"]',
                        'rule': 'display: table-cell !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Day"], #price-scorecard-table .dash-spreadsheet-container td[data-dash-column="Day"]',
                        'rule': 'display: table-cell !important;'
                    }
            ]
        )
        
            return table
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in update_price_scorecard: {e}")
            print(error_details)
            return html.Div(
                [
                    html.Div(f"Error loading table: {str(e)}", style={'padding': '20px', 'color': 'red', 'fontWeight': 'bold'}),
                    html.Div("Please try refreshing the page or selecting a different filter.", style={'padding': '10px 20px', 'color': '#666'})
                ],
                style={'padding': '20px'}
            )
    
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
                    const allDataCells = spreadsheet.querySelectorAll('td[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Quarter"]):not([data-dash-column="Month"]):not([data-dash-column="Day"])');
                    allDataCells.forEach(cell => {
                        cell.style.opacity = '';
                    });
                }
                
                function clearAllRowSelections(spreadsheet) {
                    if (!spreadsheet) return;
                    
                    // Clear all row cells - remove classes and all inline styles
                    const allRowCells = spreadsheet.querySelectorAll('td.row-cell-selected');
                    allRowCells.forEach(cell => {
                        cell.classList.remove('row-cell-selected');
                        // Remove all inline styles including those set with !important
                        cell.style.removeProperty('background-color');
                        cell.style.removeProperty('border');
                        cell.style.removeProperty('font-weight');
                        cell.style.removeProperty('color');
                        cell.style.removeProperty('opacity');
                        cell.style.removeProperty('filter');
                    });
                    
                    // Also clear any cells that might have been highlighted but don't have the class
                    // Reset all rows to normal state
                    const allDataRows = spreadsheet.querySelectorAll('tbody tr');
                    allDataRows.forEach(r => {
                        const rowCells = r.querySelectorAll('td');
                        rowCells.forEach(c => {
                            // Remove all highlighting styles and reset to normal
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
                
                function getCellValue(cell) {
                    const text = cell.textContent || cell.innerText || '';
                    return text.trim();
                }
                
                function applyStickyColumns(spreadsheet) {
                    if (!spreadsheet) return;
                    
                    // Find all Year, Quarter, Month, and Day columns
                    const yearHeaders = spreadsheet.querySelectorAll('th[data-dash-column="Year"]');
                    const quarterHeaders = spreadsheet.querySelectorAll('th[data-dash-column="Quarter"]');
                    const monthHeaders = spreadsheet.querySelectorAll('th[data-dash-column="Month"]');
                    const dayHeaders = spreadsheet.querySelectorAll('th[data-dash-column="Day"]');
                    const yearCells = spreadsheet.querySelectorAll('td[data-dash-column="Year"]');
                    const quarterCells = spreadsheet.querySelectorAll('td[data-dash-column="Quarter"]');
                    const monthCells = spreadsheet.querySelectorAll('td[data-dash-column="Month"]');
                    const dayCells = spreadsheet.querySelectorAll('td[data-dash-column="Day"]');
                    
                    // Also target by position (first, second, third, and fourth columns) as fallback
                    const allHeaders = spreadsheet.querySelectorAll('thead tr th');
                    const allCells = spreadsheet.querySelectorAll('tbody tr td');
                    
                    // Apply sticky to Year headers (first column in each header row)
                    yearHeaders.forEach((th, idx) => {
                        th.style.position = 'sticky';
                        th.style.left = '0px';
                        th.style.zIndex = '25';
                        th.style.backgroundColor = 'white';
                        th.style.minWidth = '80px';
                        th.style.width = '80px';
                    });
                    
                    // Apply sticky to Quarter headers (second column in each header row)
                    quarterHeaders.forEach((th, idx) => {
                        th.style.position = 'sticky';
                        th.style.left = '80px';
                        th.style.zIndex = '25';
                        th.style.backgroundColor = 'white';
                        th.style.minWidth = '80px';
                        th.style.width = '80px';
                    });
                    
                    // Apply sticky to Month headers (third column in each header row)
                    monthHeaders.forEach((th, idx) => {
                        th.style.position = 'sticky';
                        th.style.left = '160px';
                        th.style.zIndex = '25';
                        th.style.backgroundColor = 'white';
                        th.style.minWidth = '80px';
                        th.style.width = '80px';
                    });
                    
                    // Apply sticky to Day headers (fourth column in each header row)
                    dayHeaders.forEach((th, idx) => {
                        th.style.position = 'sticky';
                        th.style.left = '240px';
                        th.style.zIndex = '25';
                        th.style.backgroundColor = 'white';
                        th.style.minWidth = '80px';
                        th.style.width = '80px';
                    });
                    
                    // Apply sticky to Year cells
                    yearCells.forEach((td, idx) => {
                        td.style.position = 'sticky';
                        td.style.left = '0px';
                        td.style.zIndex = '15';
                        td.style.minWidth = '80px';
                        td.style.width = '80px';
                    });
                    
                    // Apply sticky to Quarter cells
                    quarterCells.forEach((td, idx) => {
                        td.style.position = 'sticky';
                        td.style.left = '80px';
                        td.style.zIndex = '15';
                        td.style.minWidth = '80px';
                        td.style.width = '80px';
                    });
                    
                    // Apply sticky to Month cells
                    monthCells.forEach((td, idx) => {
                        td.style.position = 'sticky';
                        td.style.left = '160px';
                        td.style.zIndex = '15';
                        td.style.minWidth = '80px';
                        td.style.width = '80px';
                    });
                    
                    // Apply sticky to Day cells
                    dayCells.forEach((td, idx) => {
                        td.style.position = 'sticky';
                        td.style.left = '240px';
                        td.style.zIndex = '15';
                        td.style.minWidth = '80px';
                        td.style.width = '80px';
                    });
                    
                    // Fallback: Apply to first, second, third, and fourth columns by position
                    const headerRows = spreadsheet.querySelectorAll('thead tr');
                    headerRows.forEach((row, rowIdx) => {
                        const firstTh = row.querySelector('th:first-child');
                        const secondTh = row.querySelector('th:nth-child(2)');
                        const thirdTh = row.querySelector('th:nth-child(3)');
                        const fourthTh = row.querySelector('th:nth-child(4)');
                        if (firstTh && (!firstTh.hasAttribute('data-dash-column') || firstTh.getAttribute('data-dash-column') === 'Year')) {
                            firstTh.style.position = 'sticky';
                            firstTh.style.left = '0px';
                            firstTh.style.zIndex = (30 - rowIdx).toString();
                            firstTh.style.backgroundColor = 'white';
                        }
                        if (secondTh && (!secondTh.hasAttribute('data-dash-column') || secondTh.getAttribute('data-dash-column') === 'Quarter')) {
                            secondTh.style.position = 'sticky';
                            secondTh.style.left = '80px';
                            secondTh.style.zIndex = (30 - rowIdx).toString();
                            secondTh.style.backgroundColor = 'white';
                        }
                        if (thirdTh && (!thirdTh.hasAttribute('data-dash-column') || thirdTh.getAttribute('data-dash-column') === 'Month')) {
                            thirdTh.style.position = 'sticky';
                            thirdTh.style.left = '160px';
                            thirdTh.style.zIndex = (30 - rowIdx).toString();
                            thirdTh.style.backgroundColor = 'white';
                        }
                        if (fourthTh && (!fourthTh.hasAttribute('data-dash-column') || fourthTh.getAttribute('data-dash-column') === 'Day')) {
                            fourthTh.style.position = 'sticky';
                            fourthTh.style.left = '240px';
                            fourthTh.style.zIndex = (30 - rowIdx).toString();
                            fourthTh.style.backgroundColor = 'white';
                        }
                    });
                    
                    // Apply to data rows
                    const dataRows = spreadsheet.querySelectorAll('tbody tr');
                    dataRows.forEach((row, rowIdx) => {
                        const firstTd = row.querySelector('td:first-child');
                        const secondTd = row.querySelector('td:nth-child(2)');
                        const thirdTd = row.querySelector('td:nth-child(3)');
                        const fourthTd = row.querySelector('td:nth-child(4)');
                        if (firstTd && (!firstTd.hasAttribute('data-dash-column') || firstTd.getAttribute('data-dash-column') === 'Year')) {
                            firstTd.style.position = 'sticky';
                            firstTd.style.left = '0px';
                            firstTd.style.zIndex = '15';
                            // Preserve background color
                            if (rowIdx % 2 === 0) {
                                firstTd.style.backgroundColor = '#f9f9f9';
                            } else {
                                firstTd.style.backgroundColor = 'white';
                            }
                        }
                        if (secondTd && (!secondTd.hasAttribute('data-dash-column') || secondTd.getAttribute('data-dash-column') === 'Quarter')) {
                            secondTd.style.position = 'sticky';
                            secondTd.style.left = '80px';
                            secondTd.style.zIndex = '15';
                            // Preserve background color
                            if (rowIdx % 2 === 0) {
                                secondTd.style.backgroundColor = '#f9f9f9';
                            } else {
                                secondTd.style.backgroundColor = 'white';
                            }
                        }
                        if (thirdTd && (!thirdTd.hasAttribute('data-dash-column') || thirdTd.getAttribute('data-dash-column') === 'Month')) {
                            thirdTd.style.position = 'sticky';
                            thirdTd.style.left = '160px';
                            thirdTd.style.zIndex = '15';
                            // Preserve background color
                            if (rowIdx % 2 === 0) {
                                thirdTd.style.backgroundColor = '#f9f9f9';
                            } else {
                                thirdTd.style.backgroundColor = 'white';
                            }
                        }
                        if (fourthTd && (!fourthTd.hasAttribute('data-dash-column') || fourthTd.getAttribute('data-dash-column') === 'Day')) {
                            fourthTd.style.position = 'sticky';
                            fourthTd.style.left = '240px';
                            fourthTd.style.zIndex = '15';
                            // Preserve background color
                            if (rowIdx % 2 === 0) {
                                fourthTd.style.backgroundColor = '#f9f9f9';
                            } else {
                                fourthTd.style.backgroundColor = 'white';
                            }
                        }
                    });
                    
                    // Ensure the spreadsheet container has overflow
                    spreadsheet.style.overflowX = 'auto';
                    spreadsheet.style.overflowY = 'auto';
                }
                
                function enhanceTable() {
                    const tableEl = document.getElementById('price-scorecard-table');
                    if (!tableEl) {
                        return;
                    }
                    
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    if (!spreadsheet) {
                        return;
                    }
                    
                    // Check if headers exist
                    const headers = spreadsheet.querySelectorAll('th[data-dash-column]');
                    if (headers.length === 0) {
                        return;
                    }
                    
                    // Apply sticky columns
                    applyStickyColumns(spreadsheet);
                    
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
                        return;
                    }
                    
                    // If signature changed or not enhanced, proceed with enhancement
                    
                    spreadsheet.dataset.priceScorecardEnhanced = 'true';

                    // Add style tag to ensure toggle icons are hidden by default and show on hover
                    const styleId = 'price-scorecard-toggle-icons-style';
                    if (!document.getElementById(styleId)) {
                        const style = document.createElement('style');
                        style.id = styleId;
                        style.textContent = `
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Year"] .year-header-toggle,
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Quarter"] .quarter-header-toggle,
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Month"] .month-header-toggle,
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Day"] .day-header-toggle {
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
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Year"]:hover .year-header-toggle,
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Month"]:hover .month-header-toggle,
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Quarter"]:hover .quarter-header-toggle,
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Day"]:hover .day-header-toggle {
                                display: inline-block !important;
                            }
                            /* Ensure toggle parent headers have relative positioning */
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Year"],
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Month"],
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Quarter"],
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Day"] {
                                position: relative;
                                white-space: nowrap;
                            }
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Year"] .year-header-toggle:hover,
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Month"] .month-header-toggle:hover,
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Quarter"] .quarter-header-toggle:hover,
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Day"] .day-header-toggle:hover {
                                color: #333333;
                                border-color: #a0a0a0;
                                background-color: #f0f0f0;
                            }
                            /* Sticky column positions and z-index for fixed date columns */
                            /* Year: always fixed at left 0 */
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Year"],
                            #price-scorecard-table .dash-spreadsheet-container td[data-dash-column="Year"] {
                                position: sticky !important;
                                left: 0 !important;
                                z-index: 10 !important;
                                box-shadow: 2px 0 4px rgba(0,0,0,0.1);
                            }
                            /* Quarter: positioned after Year (80px) when visible */
                            #price-scorecard-table .dash-spreadsheet-container.year-expanded th[data-dash-column="Quarter"],
                            #price-scorecard-table .dash-spreadsheet-container.year-expanded td[data-dash-column="Quarter"] {
                                position: sticky !important;
                                left: 80px !important;
                                z-index: 10 !important;
                                box-shadow: 2px 0 4px rgba(0,0,0,0.1);
                            }
                            /* Month: positioned at 80px when Quarter is hidden, 140px when Quarter is visible */
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Month"],
                            #price-scorecard-table .dash-spreadsheet-container td[data-dash-column="Month"] {
                                position: sticky !important;
                                left: 80px !important;
                                z-index: 10 !important;
                                box-shadow: 2px 0 4px rgba(0,0,0,0.1);
                            }
                            #price-scorecard-table .dash-spreadsheet-container.year-expanded th[data-dash-column="Month"],
                            #price-scorecard-table .dash-spreadsheet-container.year-expanded td[data-dash-column="Month"] {
                                left: 140px !important;
                            }
                            /* Day: positioned after Month (180px when Quarter hidden, 240px when Quarter visible) */
                            #price-scorecard-table .dash-spreadsheet-container.month-expanded:not(.year-expanded) th[data-dash-column="Day"],
                            #price-scorecard-table .dash-spreadsheet-container.month-expanded:not(.year-expanded) td[data-dash-column="Day"] {
                                position: sticky !important;
                                left: 180px !important;
                                z-index: 10 !important;
                                box-shadow: 2px 0 4px rgba(0,0,0,0.1);
                            }
                            #price-scorecard-table .dash-spreadsheet-container.month-expanded.year-expanded:not(.quarter-collapsed) th[data-dash-column="Day"],
                            #price-scorecard-table .dash-spreadsheet-container.month-expanded.year-expanded:not(.quarter-collapsed) td[data-dash-column="Day"] {
                                position: sticky !important;
                                left: 240px !important;
                                z-index: 10 !important;
                                box-shadow: 2px 0 4px rgba(0,0,0,0.1);
                            }
                            /* Ensure header cells have higher z-index and background color */
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Year"],
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Quarter"],
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Month"],
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Day"] {
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
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Quarter"],
                            #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Day"],
                            #price-scorecard-table .dash-spreadsheet-container td[data-dash-column="Quarter"],
                            #price-scorecard-table .dash-spreadsheet-container td[data-dash-column="Day"] {
                                display: none !important;
                            }
                            /* Show Quarter when year is expanded */
                            #price-scorecard-table .dash-spreadsheet-container.year-expanded th[data-dash-column="Quarter"],
                            #price-scorecard-table .dash-spreadsheet-container.year-expanded td[data-dash-column="Quarter"] {
                                display: table-cell !important;
                            }
                            /* Hide Month and Day when quarter is collapsed (only when Quarter is visible) */
                            #price-scorecard-table .dash-spreadsheet-container.year-expanded.quarter-collapsed th[data-dash-column="Month"],
                            #price-scorecard-table .dash-spreadsheet-container.year-expanded.quarter-collapsed th[data-dash-column="Day"],
                            #price-scorecard-table .dash-spreadsheet-container.year-expanded.quarter-collapsed td[data-dash-column="Month"],
                            #price-scorecard-table .dash-spreadsheet-container.year-expanded.quarter-collapsed td[data-dash-column="Day"] {
                                display: none !important;
                            }
                            /* Show Day when month is expanded (hide if quarter is collapsed) */
                            #price-scorecard-table .dash-spreadsheet-container.month-expanded:not(.quarter-collapsed) th[data-dash-column="Day"],
                            #price-scorecard-table .dash-spreadsheet-container.month-expanded:not(.quarter-collapsed) td[data-dash-column="Day"] {
                                display: table-cell !important;
                            }
                        `;
                        document.head.appendChild(style);
                    }
                    
                    // Initialize expand/collapse state
                    let isYearExpanded = false; // Default: hide Quarter
                    let isMonthExpanded = false; // Default: hide Day
                    let isQuarterCollapsed = false; // Default: Quarter is not collapsed (Month and Day visible initially)

                    // Ensure initial state of year-expanded class based on isYearExpanded
                    if (!isYearExpanded) {
                        spreadsheet.classList.remove('year-expanded');
                    } else {
                        spreadsheet.classList.add('year-expanded');
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
                        // Don't set display inline - let CSS handle visibility (hidden by default, shown on hover)
                        icon.style.setProperty('margin-left', '6px', 'important');
                        icon.style.setProperty('width', '16px', 'important');
                        icon.style.setProperty('height', '16px', 'important');
                        icon.style.setProperty('line-height', '14px', 'important');
                        icon.style.setProperty('text-align', 'center', 'important');
                        icon.style.setProperty('font-size', '12px', 'important');
                        icon.style.setProperty('font-weight', 'normal', 'important');
                        icon.style.setProperty('color', '#505050', 'important');
                        icon.style.setProperty('border', '1px solid #d0d0d0', 'important');
                        icon.style.setProperty('border-radius', '2px', 'important');
                        icon.style.setProperty('background-color', '#ffffff', 'important');
                        icon.style.setProperty('user-select', 'none', 'important');
                        icon.style.setProperty('cursor', 'pointer', 'important');
                        icon.style.setProperty('vertical-align', 'middle', 'important');
                        icon.style.setProperty('box-sizing', 'border-box', 'important');
                        
                        // Always append icon to the cell
                        cell.appendChild(icon);
                        
                        icon.addEventListener('click', function(e) {
                            e.stopPropagation();
                            onClickHandler();
                        });
                        
                        return icon;
                    }
                    
                    // Initialize toggle buttons in header columns only
                    function initializeYearHeaderToggle() {
                        // Find the header cell that contains "Year" text (the visible one in hierarchical headers)
                        const allYearHeaders = Array.from(spreadsheet.querySelectorAll('th[data-dash-column="Year"]'));
                        if (!allYearHeaders.length) return;
                        
                        // Find the header in the last header row (the visible one in multi-level headers)
                        // Get all header rows
                        const headerRows = Array.from(spreadsheet.querySelectorAll('thead tr'));
                        let yearHeader = null;
                        
                        // Start from the last row and work backwards to find the visible header
                        for (let i = headerRows.length - 1; i >= 0; i--) {
                            const headerInRow = headerRows[i].querySelector('th[data-dash-column="Year"]');
                            if (headerInRow) {
                                const text = headerInRow.textContent.trim();
                                // Check if this header contains "Year" text (not just empty or merged cell)
                                if (text.includes('Year') || (text === '' && i === headerRows.length - 1)) {
                                    yearHeader = headerInRow;
                                    break;
                                }
                            }
                        }
                        
                        // Fallback to the last one if not found
                        if (!yearHeader) {
                            yearHeader = allYearHeaders[allYearHeaders.length - 1];
                        }
                        
                        // Remove toggle buttons from any other Year headers so the icon only appears once
                        allYearHeaders.forEach(header => {
                            if (header !== yearHeader) {
                                const extraToggle = header.querySelector('.year-header-toggle');
                                if (extraToggle) extraToggle.remove();
                            }
                        });
                        
                        const existingToggle = yearHeader.querySelector('.year-header-toggle');
                        if (existingToggle) {
                            existingToggle.remove();
                        }
                        
                        addToggleIcon(yearHeader, 'year-header-toggle', isYearExpanded, function() {
                            toggleYearExpand();
                        });
                    }
                    
                    function initializeQuarterHeaderToggle() {
                        // Find the header cell that contains "Quarter" text (the visible one in hierarchical headers)
                        const allQuarterHeaders = Array.from(spreadsheet.querySelectorAll('th[data-dash-column="Quarter"]'));
                        if (!allQuarterHeaders.length) {
                            // Try again after a short delay if headers aren't found yet
                            setTimeout(function() {
                                initializeQuarterHeaderToggle();
                            }, 100);
                            return;
                        }
                        
                        // Find the header in the last header row (the visible one in multi-level headers)
                        const headerRows = Array.from(spreadsheet.querySelectorAll('thead tr'));
                        let quarterHeader = null;
                        
                        // Start from the last row and work backwards to find the visible header
                        for (let i = headerRows.length - 1; i >= 0; i--) {
                            const headerInRow = headerRows[i].querySelector('th[data-dash-column="Quarter"]');
                            if (headerInRow) {
                                const text = headerInRow.textContent.trim();
                                // Check if this header contains "Quarter" text (not just empty or merged cell)
                                if (text.includes('Quarter') || (text === '' && i === headerRows.length - 1)) {
                                    quarterHeader = headerInRow;
                                    break;
                                }
                            }
                        }
                        
                        // Fallback to the last one if not found
                        if (!quarterHeader) {
                            quarterHeader = allQuarterHeaders[allQuarterHeaders.length - 1];
                        }
                        
                        // Remove toggle buttons from any other Quarter headers
                        allQuarterHeaders.forEach(header => {
                            if (header !== quarterHeader) {
                                const extraToggle = header.querySelector('.quarter-header-toggle');
                                if (extraToggle) extraToggle.remove();
                            }
                        });
                        
                        const existingToggle = quarterHeader.querySelector('.quarter-header-toggle');
                        if (existingToggle) {
                            existingToggle.remove();
                        }
                        
                        addToggleIcon(quarterHeader, 'quarter-header-toggle', !isQuarterCollapsed, function() {
                            toggleQuarterCollapse();
                        });
                    }
                    
                    function initializeMonthHeaderToggle() {
                        // Find the header cell that contains "Month" text (the visible one in hierarchical headers)
                        const allMonthHeaders = Array.from(spreadsheet.querySelectorAll('th[data-dash-column="Month"]'));
                        if (!allMonthHeaders.length) {
                            // Try again after a short delay if headers aren't found yet
                            setTimeout(function() {
                                initializeMonthHeaderToggle();
                            }, 100);
                            return;
                        }
                        
                        // Find the header in the last header row (the visible one in multi-level headers)
                        const headerRows = Array.from(spreadsheet.querySelectorAll('thead tr'));
                        let monthHeader = null;
                        
                        // Start from the last row and work backwards to find the visible header
                        for (let i = headerRows.length - 1; i >= 0; i--) {
                            const headerInRow = headerRows[i].querySelector('th[data-dash-column="Month"]');
                            if (headerInRow) {
                                const text = headerInRow.textContent.trim();
                                // Check if this header contains "Month" text (not just empty or merged cell)
                                if (text.includes('Month') || (text === '' && i === headerRows.length - 1)) {
                                    monthHeader = headerInRow;
                                    break;
                                }
                            }
                        }
                        
                        // Fallback to the last one if not found
                        if (!monthHeader) {
                            monthHeader = allMonthHeaders[allMonthHeaders.length - 1];
                        }
                        
                        // Remove toggle buttons from any other Month headers
                        allMonthHeaders.forEach(header => {
                            if (header !== monthHeader) {
                                const extraToggle = header.querySelector('.month-header-toggle');
                                if (extraToggle) extraToggle.remove();
                            }
                        });
                        
                        const existingToggle = monthHeader.querySelector('.month-header-toggle');
                        if (existingToggle) {
                            existingToggle.remove();
                        }
                        
                        addToggleIcon(monthHeader, 'month-header-toggle', isMonthExpanded, function() {
                            toggleMonthExpand();
                        });
                    }
                    
                    function initializeDayHeaderToggle() {
                        // Find the header cell that contains "Day" text (the visible one in hierarchical headers)
                        // Use querySelectorAll which works even on hidden elements (display:none)
                        const allDayHeaders = Array.from(spreadsheet.querySelectorAll('th[data-dash-column="Day"]'));
                        if (!allDayHeaders.length) {
                            // Try again after a short delay if headers aren't found yet
                            setTimeout(function() {
                                initializeDayHeaderToggle();
                            }, 100);
                            return;
                        }
                        
                        // Find the header in the last header row (the visible one in multi-level headers)
                        const headerRows = Array.from(spreadsheet.querySelectorAll('thead tr'));
                        let dayHeader = null;
                        
                        // Start from the last row and work backwards to find the visible header
                        for (let i = headerRows.length - 1; i >= 0; i--) {
                            const headerInRow = headerRows[i].querySelector('th[data-dash-column="Day"]');
                            if (headerInRow) {
                                const text = headerInRow.textContent.trim();
                                // Check if this header contains "Day" text (not just empty or merged cell)
                                if (text.includes('Day') || (text === '' && i === headerRows.length - 1)) {
                                    dayHeader = headerInRow;
                                    break;
                                }
                            }
                        }
                        
                        // Fallback to the last one if not found
                        if (!dayHeader) {
                            dayHeader = allDayHeaders[allDayHeaders.length - 1];
                        }
                        
                        // Remove toggle buttons from any other Day headers
                        allDayHeaders.forEach(header => {
                            if (header !== dayHeader) {
                                const extraToggle = header.querySelector('.day-header-toggle');
                                if (extraToggle) extraToggle.remove();
                            }
                        });
                        
                        const existingToggle = dayHeader.querySelector('.day-header-toggle');
                        if (existingToggle) {
                            existingToggle.remove();
                        }
                        
                        addToggleIcon(dayHeader, 'day-header-toggle', isMonthExpanded, function() {
                            toggleMonthExpand();
                        });
                    }
                    
                    // Toggle Year expand (shows/hides Quarter)
                    function toggleYearExpand() {
                        isYearExpanded = !isYearExpanded;
                        
                        const yearHeaderToggle = spreadsheet.querySelector('th[data-dash-column="Year"] .year-header-toggle');
                        if (yearHeaderToggle) {
                            yearHeaderToggle.textContent = isYearExpanded ? '−' : '+';
                            yearHeaderToggle.setAttribute('aria-label', isYearExpanded ? 'Collapse Quarter' : 'Expand Quarter');
                        }
                        
                        // Toggle Quarter column visibility
                        if (isYearExpanded) {
                            spreadsheet.classList.add('year-expanded');
                            // When Year is expanded, Quarter is shown, and Month/Day should be visible by default (not collapsed)
                            isQuarterCollapsed = false;
                            spreadsheet.classList.remove('quarter-collapsed');
                            
                            // Re-initialize Month and Day toggles to ensure their states are correct
                            console.log('toggleYearExpand: Calling initializeMonthHeaderToggle()...');
                            initializeMonthHeaderToggle();
                            console.log('toggleYearExpand: Calling initializeDayHeaderToggle()...');
                            initializeDayHeaderToggle();

                            // Initialize Quarter header toggle when Quarter becomes visible
                            initializeQuarterHeaderToggle();
                        } else {
                            spreadsheet.classList.remove('year-expanded');
                            // Reset quarter collapse state when Quarter is hidden
                            isQuarterCollapsed = true; // Quarter is hidden, so Month and Day should be effectively collapsed
                            spreadsheet.classList.add('quarter-collapsed'); // Add class to hide Month/Day if Quarter isn't shown
                            
                            // Also remove month-expanded class and reset isMonthExpanded
                            spreadsheet.classList.remove('month-expanded');
                            isMonthExpanded = false;
                            // Remove Month toggle if it exists
                            const monthHeader = spreadsheet.querySelector('th[data-dash-column="Month"]');
                            if (monthHeader) {
                                const toggle = monthHeader.querySelector('.month-header-toggle');
                                if (toggle) toggle.remove();
                            }
                            // Remove Day toggle if it exists
                            const dayHeader = spreadsheet.querySelector('th[data-dash-column="Day"]');
                            if (dayHeader) {
                                const toggle = dayHeader.querySelector('.day-header-toggle');
                                if (toggle) toggle.remove();
                            }
                            
                            // Remove Quarter toggle if it exists
                            const quarterHeader = spreadsheet.querySelector('th[data-dash-column="Quarter"]');
                            if (quarterHeader) {
                                const toggle = quarterHeader.querySelector('.quarter-header-toggle');
                                if (toggle) toggle.remove();
                            }
                        }
                        
                        // Clear selections
                        clearAllColumnSelections(spreadsheet);
                        clearAllRowSelections(spreadsheet);
                    }
                    
                    // Toggle Quarter collapse (shows/hides Month and Day)
                    function toggleQuarterCollapse() {
                        isQuarterCollapsed = !isQuarterCollapsed;
                        
                        const quarterHeaderToggle = spreadsheet.querySelector('th[data-dash-column="Quarter"] .quarter-header-toggle');
                        if (quarterHeaderToggle) {
                            quarterHeaderToggle.textContent = isQuarterCollapsed ? '+' : '−';
                            quarterHeaderToggle.setAttribute('aria-label', isQuarterCollapsed ? 'Show Month & Day' : 'Hide Month & Day');
                        }
                        
                        // Toggle Month and Day column visibility
                        if (isQuarterCollapsed) {
                            spreadsheet.classList.add('quarter-collapsed');
                            // When Quarter is collapsed, Month and Day should be collapsed too
                            spreadsheet.classList.remove('month-expanded');
                            isMonthExpanded = false;
                            // Remove Month toggle if it exists
                            const monthHeader = spreadsheet.querySelector('th[data-dash-column="Month"]');
                            if (monthHeader) {
                                const toggle = monthHeader.querySelector('.month-header-toggle');
                                if (toggle) toggle.remove();
                            }
                            // Remove Day toggle if it exists
                            const dayHeader = spreadsheet.querySelector('th[data-dash-column="Day"]');
                            if (dayHeader) {
                                const toggle = dayHeader.querySelector('.day-header-toggle');
                                if (toggle) toggle.remove();
                            }
                        } else {
                            spreadsheet.classList.remove('quarter-collapsed');
                            // When Quarter is expanded, Month and Day should be in their default (collapsed) state
                            spreadsheet.classList.remove('month-expanded');
                            isMonthExpanded = false;
                            // Re-initialize Month and Day toggles to ensure their states are correct
                            console.log('toggleQuarterCollapse: Calling initializeMonthHeaderToggle()...');
                            initializeMonthHeaderToggle();
                            console.log('toggleQuarterCollapse: Calling initializeDayHeaderToggle()...');
                            initializeDayHeaderToggle();
                        }
                        
                        // Clear selections
                        clearAllColumnSelections(spreadsheet);
                        clearAllRowSelections(spreadsheet);
                    }
                    
                    // Toggle Month expand (shows/hides Day)
                    function toggleMonthExpand() {
                        isMonthExpanded = !isMonthExpanded;
                        
                        const monthHeaderToggle = spreadsheet.querySelector('th[data-dash-column="Month"] .month-header-toggle');
                        if (monthHeaderToggle) {
                            monthHeaderToggle.textContent = isMonthExpanded ? '−' : '+';
                            monthHeaderToggle.setAttribute('aria-label', isMonthExpanded ? 'Collapse Day' : 'Expand Day');
                        }
                        
                        // Toggle Day column visibility
                        if (isMonthExpanded) {
                            spreadsheet.classList.add('month-expanded');
                            // Initialize Day header toggle when Day becomes visible
                            initializeDayHeaderToggle();
                        } else {
                            spreadsheet.classList.remove('month-expanded');
                            // Remove Day toggle if it exists
                            const dayHeader = spreadsheet.querySelector('th[data-dash-column="Day"]');
                            if (dayHeader) {
                                const toggle = dayHeader.querySelector('.day-header-toggle');
                                if (toggle) toggle.remove();
                            }
                        }
                        
                        // Clear selections
                        clearAllColumnSelections(spreadsheet);
                        clearAllRowSelections(spreadsheet);
                    }
                    
                    // Initialize toggle buttons in headers on load - use multiple attempts to ensure table is rendered
                    function initToggles() {
                        // Always initialize Year and Month toggles
                        initializeYearHeaderToggle();
                        initializeMonthHeaderToggle();
                        
                        // Always initialize Quarter and Day toggles immediately - headers exist in DOM even if hidden
                        // querySelector works on hidden elements (display:none)
                        initializeQuarterHeaderToggle();
                        initializeDayHeaderToggle();
                    }
                    
                    // Try multiple times to catch table rendering
                    setTimeout(initToggles, 300);
                    setTimeout(initToggles, 600);
                    setTimeout(initToggles, 1000);
                    setTimeout(initToggles, 1500);
                    
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
                            
                                                        // Handle Year header toggle
                            if (columnId === 'Year') {
                                const toggleBtn = event.target.closest('.year-header-toggle');
                                if (toggleBtn || event.target === header || header.contains(event.target)) {
                                    toggleYearExpand();
                                    return;
                                }
                            }
                            
                            // Handle Quarter header toggle
                            if (columnId === 'Quarter') {
                                const toggleBtn = event.target.closest('.quarter-header-toggle');
                                if (toggleBtn || event.target === header || header.contains(event.target)) {
                                    toggleQuarterCollapse();
                                    return;
                                }
                            }
                            
                            // Handle Month header toggle
                            if (columnId === 'Month') {
                                const toggleBtn = event.target.closest('.month-header-toggle');
                                if (toggleBtn || event.target === header || header.contains(event.target)) {
                                    toggleMonthExpand();
                                    return;
                                }
                            }
                            
                            // Clear selection if clicking Day header (no toggle functionality)
                            if (columnId === 'Day') {
                                clearAllColumnSelections(clickedSpreadsheet);
                                clearAllRowSelections(clickedSpreadsheet);
                                if (window.priceScorecardState) {
                                    window.priceScorecardState.selectedColumnId = null;
                                    window.priceScorecardState.selectedRowIndex = null;
                                }
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
                            // A data column header row should have at least one header with columnId starting with 'col_'
                            headerRows = headerRows.filter(tr => {
                                const dataHeaders = tr.querySelectorAll('th[data-dash-column^="col_"]');
                                return dataHeaders.length > 0;
                            });
                            
                            totalHeaderRows = headerRows.length;
                            
                            if (headerRow && headerRows.length > 0) {
                                headerIndex = headerRows.indexOf(headerRow);
                            } else if (headerRow) {
                                // If headerRow is not in the filtered list, it might be a Year/Quarter/Month/Day row
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
                                }
                            }
                            
                            
                            // Create a unique key for this selection (columnId + headerIndex)
                            const selectionKey = columnId + '_' + headerIndex;
                            
                            // Check if this exact header level is already selected
                            if (window.priceScorecardState && window.priceScorecardState.selectedColumnId === selectionKey) {
                                // Deselect column
                                clearAllColumnSelections(clickedSpreadsheet);
                                if (window.priceScorecardState) {
                                    window.priceScorecardState.selectedColumnId = null;
                                }
                            } else {
                                // Select new column
                                clearAllColumnSelections(clickedSpreadsheet);
                                clearAllRowSelections(clickedSpreadsheet);
                                
                                if (window.priceScorecardState) {
                                    window.priceScorecardState.selectedColumnId = selectionKey;
                                    window.priceScorecardState.selectedRowIndex = null;
                                }
                                
                                // Only highlight headers at the SAME header level (headerIndex) for this column
                                const allHeadersForColumn = clickedSpreadsheet.querySelectorAll(`th[data-dash-column="${columnId}"]`);
                                
                                // Check if this is the bottom-most header level
                                const isBottomHeader = (headerIndex >= 0 && totalHeaderRows > 0 && headerIndex === totalHeaderRows - 1);
                                // Check if this is the top-most header level (index 0)
                                const isTopHeader = (headerIndex === 0);
                                
                                
                                if (isBottomHeader || isTopHeader) {
                                    // Bottom or top header clicked - highlight ALL header levels and data cells
                                    if (isTopHeader) {
                                        
                                        // For top header, find all columns that share the same top-level header text
                                        const topHeaderText = header.textContent.trim();
                                        
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
                                                
                                                // Find the clicked header's position in the row (by cell index, not data-dash-column)
                                                let clickedCellIndex = -1;
                                                for (let i = 0; i < allTopRowCells.length; i++) {
                                                    if (allTopRowCells[i] === header || allTopRowCells[i].contains(header)) {
                                                        clickedCellIndex = i;
                                                        break;
                                                    }
                                                }
                                                
                                                
                                                // Get all bottom row headers (index 3) to find actual column IDs
                                                const bottomRow = headerRows[headerRows.length - 1];
                                                if (bottomRow) {
                                                    // Get ALL cells from bottom row (including any merged cells)
                                                    const allBottomRowCells = Array.from(bottomRow.querySelectorAll('th'));
                                                    
                                                    // Calculate the data column start position by counting colspan of all previous headers
                                                    // This accounts for headers like "Africa" (colspan=14) that come before "Asia"
                                                    let topRowDataStart = 0;
                                                    
                                                    for (let i = 0; i < clickedCellIndex; i++) {
                                                        const cell = allTopRowCells[i];
                                                        const cellColId = cell.getAttribute('data-dash-column');
                                                        
                                                        // Skip Year/Quarter/Month/Day - they don't count as data columns
                                                        if (cellColId === 'Year' || cellColId === 'Quarter' || cellColId === 'Month' || cellColId === 'Day') {
                                                            continue;
                                                        }
                                                        
                                                        // Count the colspan of this header (how many data columns it spans)
                                                        const cellColspan = parseInt(cell.getAttribute('colspan') || cell.colSpan || '1');
                                                        topRowDataStart += cellColspan;
                                                    }
                                                    
                                                    
                                                    // Now map to bottom row: count Year/Quarter/Month/Day in bottom row, then get data columns
                                                    let bottomRowDataColIndex = 0;
                                                    
                                                    for (let i = 0; i < allBottomRowCells.length; i++) {
                                                        const bottomCell = allBottomRowCells[i];
                                                        const bottomCellColId = bottomCell.getAttribute('data-dash-column');
                                                        
                                                        // Skip Year, Quarter, Month, and Day in bottom row
                                                        if (bottomCellColId === 'Year' || bottomCellColId === 'Quarter' || bottomCellColId === 'Month' || bottomCellColId === 'Day') {
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
                                                            }
                                                        }
                                                        
                                                        // Increment data column index (only for non-Year/Quarter/Month/Day cells)
                                                        bottomRowDataColIndex++;
                                                    }
                                                    
                                                    
                                                    // If we still don't have enough columns, use alternative method
                                                    // Get column IDs in the order they appear in the first data row
                                                    if (columnIds.size < spanCount) {
                                                        
                                                        // Get the first data row - try multiple selectors
                                                        let firstDataRow = clickedSpreadsheet.querySelector('tbody tr');
                                                        let allFirstRowCells = [];
                                                        if (!firstDataRow) {
                                                            firstDataRow = clickedSpreadsheet.querySelector('tr[data-dash-row]');
                                                        }
                                                        if (!firstDataRow) {
                                                            // Try to find any row with data cells
                                                            const allRows = clickedSpreadsheet.querySelectorAll('tr');
                                                            for (let row of allRows) {
                                                                // Skip header rows (rows with th elements)
                                                                if (row.querySelector('th')) {
                                                                    continue;
                                                                }
                                                                // Check if this row has data cells
                                                                const dataCells = row.querySelectorAll('td[data-dash-column^="col_"]');
                                                                if (dataCells.length > 0) {
                                                                    firstDataRow = row;
                                                                    break;
                                                                }
                                                            }
                                                        }
                                                        
                                                        if (firstDataRow) {
                                                            // Get all cells from the first row in order (including Year/Quarter/Month/Day)
                                                            allFirstRowCells = Array.from(firstDataRow.querySelectorAll('td'));
                                                            
                                                            // If no cells found with td, try a different approach - get all cells including th
                                                            if (allFirstRowCells.length === 0) {
                                                                // Try getting cells from the table body directly
                                                                const tbody = clickedSpreadsheet.querySelector('tbody');
                                                                if (tbody) {
                                                                    const firstTbodyRow = tbody.querySelector('tr');
                                                                    if (firstTbodyRow) {
                                                                        const tbodyCells = Array.from(firstTbodyRow.querySelectorAll('td, th'));
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
                                                                            break;
                                                                        }
                                                                    }
                                                                }
                                                            }
                                                            
                                                            // Get column IDs in order, skipping Year/Quarter/Month/Day
                                                            const orderedColIds = [];
                                                            allFirstRowCells.forEach(cell => {
                                                                const colId = cell.getAttribute('data-dash-column');
                                                                if (colId && colId.startsWith('col_')) {
                                                                    orderedColIds.push(colId);
                                                                }
                                                            });
                                                            
                                                            
                                                            // Get columns starting from topRowDataStart, spanning spanCount columns
                                                            const startIndex = topRowDataStart;
                                                            const endIndex = Math.min(startIndex + spanCount, orderedColIds.length);
                                                            
                                                            
                                                            // Clear and rebuild columnIds with the correct range
                                                            columnIds.clear();
                                                            for (let i = startIndex; i < endIndex && i < orderedColIds.length; i++) {
                                                                columnIds.add(orderedColIds[i]);
                                                            }
                                                            
                                                            
                                                            // If still not enough columns, we'll fall through to all data cells method
                                                            if (columnIds.size >= spanCount) {
                                                                // Enough columns found, we're done
                                                            } else {
                                                            }
                                                        }
                                                        
                                                        // If we still don't have enough columns, use comprehensive method
                                                        // Key insight: "Africa" spans 14 columns starting from the first data column (index 0)
                                                        // We need to get all columns in visual order from the first row, then fill in any missing ones
                                                        if (columnIds.size < spanCount) {
                                                            
                                                            // Step 1: Get all unique column IDs from all data cells
                                                            const allDataCells = clickedSpreadsheet.querySelectorAll('td[data-dash-column^="col_"]');
                                                            const allUniqueColIds = new Set();
                                                            allDataCells.forEach(cell => {
                                                                const colId = cell.getAttribute('data-dash-column');
                                                                if (colId) allUniqueColIds.add(colId);
                                                            });
                                                            
                                                            // Step 2: Build complete position map by scanning all data rows
                                                            // Then extract the range from topRowDataStart to topRowDataStart + spanCount
                                                            const columnPositionMap = new Map(); // Maps position to column ID
                                                            
                                                            // Calculate the maximum position we need
                                                            const maxPositionNeeded = topRowDataStart + spanCount;
                                                            
                                                            // Get all data rows
                                                            const allDataRows = clickedSpreadsheet.querySelectorAll('tbody tr, tr[data-dash-row]');
                                                            
                                                            // Scan each row to build the position map for ALL positions up to maxPositionNeeded
                                                            allDataRows.forEach((row, rowIndex) => {
                                                                if (row.querySelector('th')) return; // Skip header rows
                                                                
                                                                const rowCells = Array.from(row.querySelectorAll('td'));
                                                                let dataColIndex = 0; // Position in data columns (after Year/Quarter/Month/Day)
                                                                
                                                                rowCells.forEach(cell => {
                                                                    const colId = cell.getAttribute('data-dash-column');
                                                                    
                                                                    // Skip Year/Quarter/Month/Day
                                                                    if (colId === 'Year' || colId === 'Quarter' || colId === 'Month' || colId === 'Day') {
                                                                        return;
                                                                    }
                                                                    
                                                                    // Map this position if we haven't mapped it yet and it's in the range we need
                                                                    if (dataColIndex < maxPositionNeeded && !columnPositionMap.has(dataColIndex)) {
                                                                        if (colId && colId.startsWith('col_')) {
                                                                            columnPositionMap.set(dataColIndex, colId);
                                                                            if (dataColIndex >= topRowDataStart && dataColIndex < maxPositionNeeded) {
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
                                                                }
                                                            }
                                                            
                                                            
                                                            // orderedColIds already contains the correct range (from topRowDataStart to topRowDataStart + spanCount)
                                                            // Just add all of them to columnIds
                                                            
                                                            // Clear and rebuild columnIds with the correct columns
                                                            columnIds.clear();
                                                            orderedColIds.forEach(colId => {
                                                                columnIds.add(colId);
                                                            });
                                                            
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
                                                
                                                
                                                matchingTopHeaders.forEach(topH => {
                                                    const colId = topH.getAttribute('data-dash-column');
                                                    if (colId) columnIds.add(colId);
                                                });
                                                
                                                // If no matches found, use the clicked header's column
                                                if (columnIds.size === 0 && columnId) {
                                                    columnIds.add(columnId);
                                                }
                                            }
                                            
                                            
                                            // Highlight only the clicked top header cell itself (not all headers with same column IDs)
                                            header.classList.add('column-selected');
                                            header.style.backgroundColor = '#b3d9ff';
                                            header.style.color = '#1b365d';
                                            header.style.fontWeight = 'bold';
                                            
                                            // Highlight data cells for all columns under this top header
                                            let totalCellsHighlighted = 0;
                                            columnIds.forEach(colId => {
                                                // Highlight all data cells for these columns (no border)
                                                const colCells = clickedSpreadsheet.querySelectorAll(`td[data-dash-column="${colId}"]`);
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
                                        
                                        if (columnCells.length === 0) {
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
                                        allDataCells.forEach(cell => {
                                            if (!cell.classList.contains('column-cell-selected')) {
                                                cell.style.opacity = '0.3';
                                            }
                                        });
                                    }
                                } else {
                                    // Middle header - highlight the clicked header level and check if it spans columns
                                    
                                    // Check if this header spans multiple columns
                                    const headerColspan = header.getAttribute('colspan') || header.colSpan;
                                    const spanCount = headerColspan ? parseInt(headerColspan) : 1;
                                    const headerText = header.textContent.trim();
                                    
                                    
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
                                            
                                            
                                            // Count data columns before this header in the middle row
                                            // We need to count how many data column positions come before the clicked header
                                            let columnsBefore = 0;
                                            
                                            for (let i = 0; i < clickedCellIndex; i++) {
                                                const cell = allRowCells[i];
                                                const cellColId = cell.getAttribute('data-dash-column');
                                                
                                                // Skip Year/Quarter/Month/Day
                                                if (cellColId === 'Year' || cellColId === 'Quarter' || cellColId === 'Month' || cellColId === 'Day') {
                                                    continue;
                                                }
                                                
                                                // Count the colspan of this cell (how many data columns it spans)
                                                const cellColspan = parseInt(cell.getAttribute('colspan') || cell.colSpan || '1');
                                                columnsBefore += cellColspan;
                                            }
                                            
                                            
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
                                                
                                            } else {
                                                // Fallback: use bottom row
                                                const bottomRow = headerRows[headerRows.length - 1];
                                                if (bottomRow) {
                                                    const allBottomHeaders = Array.from(bottomRow.querySelectorAll('th[data-dash-column^="col_"]'));
                                                    
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
                                        columnIds.add(columnId);
                                    }
                                    
                                    
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
                                            
                                        }
                                    }
                                    
                                    // Highlight data cells for all columns under this middle header
                                    if (columnIds.size > 0) {
                                        let totalCellsHighlighted = 0;
                                        columnIds.forEach(colId => {
                                            const colCells = clickedSpreadsheet.querySelectorAll(`td[data-dash-column="${colId}"]`);
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
                                        
                                        if (totalCellsHighlighted === 0) {
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
                        
                        // Check if clicking on a toggle button in header columns
                        const yearToggle = event.target.closest('.year-header-toggle');
                        if (yearToggle) {
                            toggleYearExpand();
                            return false;
                        }
                        const quarterToggle = event.target.closest('.quarter-header-toggle');
                        if (quarterToggle) {
                            toggleQuarterCollapse();
                            return false;
                        }
                        const monthToggle = event.target.closest('.month-header-toggle');
                        if (monthToggle) {
                            toggleMonthExpand();
                            return false;
                        }
                        
                        // Handle row highlighting when clicking on Year cell
                        const yearCell = event.target.closest('td[data-dash-column="Year"]');
                        if (yearCell) {
                            event.stopPropagation();
                            toggleYearExpand();
                            return false;
                        }
                        
                        // Handle Quarter cell click
                        const quarterCell = event.target.closest('td[data-dash-column="Quarter"]');
                        if (quarterCell) {
                            event.stopPropagation();
                            toggleQuarterCollapse();
                            return false;
                        }
                        
                        // Handle row highlighting when clicking on Month cell
                        const monthCell = event.target.closest('td[data-dash-column="Month"]');
                        if (monthCell) {
                            event.stopPropagation();
                            
                            // Clear column selections first
                            clearAllColumnSelections(clickedSpreadsheet);
                            
                            // Increment selection counter to invalidate old callbacks
                            if (!window.priceScorecardState) {
                                window.priceScorecardState = {};
                            }
                            window.priceScorecardState.selectionCounter = (window.priceScorecardState.selectionCounter || 0) + 1;
                            const currentSelectionCounter = window.priceScorecardState.selectionCounter;
                            
                            // Clear ALL cells with row-cell-selected class (most comprehensive)
                            const allHighlightedCells = clickedSpreadsheet.querySelectorAll('td.row-cell-selected');
                            allHighlightedCells.forEach(c => {
                                c.classList.remove('row-cell-selected');
                                c.style.removeProperty('background-color');
                                c.style.removeProperty('border');
                                c.style.removeProperty('font-weight');
                                c.style.removeProperty('color');
                                c.style.removeProperty('opacity');
                                c.style.removeProperty('filter');
                                c.style.backgroundColor = '';
                                c.style.border = '';
                                c.style.fontWeight = '';
                                c.style.color = '';
                                c.style.opacity = '';
                            });
                            
                            // Clear ALL previously selected rows (find by class, not just state)
                            const allSelectedRows = clickedSpreadsheet.querySelectorAll('tbody tr.row-selected');
                            allSelectedRows.forEach(prevRow => {
                                const prevRowCells = prevRow.querySelectorAll('td');
                                prevRowCells.forEach(c => {
                                    c.classList.remove('row-cell-selected');
                                    // Force remove all styles with !important
                                    c.style.removeProperty('background-color');
                                    c.style.removeProperty('border');
                                    c.style.removeProperty('font-weight');
                                    c.style.removeProperty('color');
                                    c.style.removeProperty('opacity');
                                    c.style.removeProperty('filter');
                                    // Set to empty to override any !important styles
                                    c.style.backgroundColor = '';
                                    c.style.border = '';
                                    c.style.fontWeight = '';
                                    c.style.color = '';
                                    c.style.opacity = '';
                                });
                                prevRow.classList.remove('row-selected');
                            });
                            
                            // Also clear by state if available (fallback)
                            if (window.priceScorecardState && window.priceScorecardState.selectedRowIndex !== null) {
                                const prevRowIndex = window.priceScorecardState.selectedRowIndex;
                                // Try multiple ways to find the row
                                let prevRow = clickedSpreadsheet.querySelector(`tbody tr[data-dash-row="${prevRowIndex}"]`);
                                if (!prevRow) {
                                    // Try by position
                                    const tbody = clickedSpreadsheet.querySelector('tbody');
                                    if (tbody) {
                                        const allRows = Array.from(tbody.querySelectorAll('tr'));
                                        const rowPos = parseInt(prevRowIndex);
                                        if (!isNaN(rowPos) && rowPos >= 0 && rowPos < allRows.length) {
                                            prevRow = allRows[rowPos];
                                        }
                                    }
                                }
                                if (prevRow) {
                                    const prevRowCells = prevRow.querySelectorAll('td');
                                    prevRowCells.forEach(c => {
                                        c.classList.remove('row-cell-selected');
                                        c.style.removeProperty('background-color');
                                        c.style.removeProperty('border');
                                        c.style.removeProperty('font-weight');
                                        c.style.removeProperty('color');
                                        c.style.removeProperty('opacity');
                                        c.style.removeProperty('filter');
                                        c.style.backgroundColor = '';
                                        c.style.border = '';
                                        c.style.fontWeight = '';
                                        c.style.color = '';
                                        c.style.opacity = '';
                                    });
                                    prevRow.classList.remove('row-selected');
                                }
                            }
                            
                            // Clear all row selections (comprehensive cleanup)
                            clearAllRowSelections(clickedSpreadsheet);
                            
                            // Force reset ALL rows to normal state (no dimming, no highlighting)
                            const allDataRows = clickedSpreadsheet.querySelectorAll('tbody tr');
                            allDataRows.forEach(r => {
                                const rowCells = r.querySelectorAll('td');
                                rowCells.forEach(c => {
                                    // Remove all classes and styles
                                    c.classList.remove('row-cell-selected');
                                    // Remove all inline styles
                                    c.style.removeProperty('background-color');
                                    c.style.removeProperty('border');
                                    c.style.removeProperty('font-weight');
                                    c.style.removeProperty('color');
                                    c.style.removeProperty('opacity');
                                    c.style.removeProperty('filter');
                                    // Set to empty to clear any remaining styles
                                    c.style.backgroundColor = '';
                                    c.style.border = '';
                                    c.style.fontWeight = '';
                                    c.style.color = '';
                                    c.style.opacity = '';
                                });
                                r.classList.remove('row-selected');
                            });
                            
                            // Remove row-selection-active class
                            clickedSpreadsheet.classList.remove('row-selection-active');
                            
                            // Clear state BEFORE applying new selection
                            if (window.priceScorecardState) {
                                window.priceScorecardState.selectedColumnId = null;
                                window.priceScorecardState.selectedRowIndex = null; // Clear previous selection
                            }
                            
                            // Get the row containing this Month cell BEFORE requestAnimationFrame
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
                            if (window.priceScorecardState && window.priceScorecardState.selectedRowIndex === rowIndex) {
                                // Deselect row
                                clearAllRowSelections(clickedSpreadsheet);
                                if (window.priceScorecardState) {
                                    window.priceScorecardState.selectedRowIndex = null;
                                }
                            } else {
                                // Clear any previous row selection
                                clearAllRowSelections(clickedSpreadsheet);
                                    
                                // Get all cells directly from the row element
                                // This ensures we get ALL cells in the row
                                const allRowCells = Array.from(row.querySelectorAll('td'));
                                
                                // Highlight Month and data columns, but NOT Year
                                let highlightedCount = 0;
                                allRowCells.forEach((c, index) => {
                                    const colId = c.getAttribute('data-dash-column');
                                    if (colId === 'Year') {
                                        // Year column: keep at normal state, don't highlight
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
                                        // Apply inline styles with !important to ensure visibility
                                        c.style.setProperty('background-color', '#b3d9ff', 'important');
                                        c.style.setProperty('border', 'none', 'important');
                                        c.style.setProperty('font-weight', '600', 'important');
                                        c.style.setProperty('color', '#1b365d', 'important');
                                        c.style.setProperty('opacity', '1', 'important');
                                        // Remove any conflicting styles that might dim the cell
                                        c.style.removeProperty('filter');
                                        highlightedCount++;
                                    }
                                });
                                
                                
                                // Add row-selected class to row element
                                row.classList.add('row-selected');
                                
                                // Dim other rows first
                                const allDataRows = clickedSpreadsheet.querySelectorAll('tbody tr');
                                allDataRows.forEach((r, rPos) => {
                                    const rIndex = r.getAttribute('data-dash-row') || rPos.toString();
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
                                
                                // Force selected row to be bright (apply again to ensure it overrides any CSS)
                                const selectedRowCells = row.querySelectorAll('td');
                                selectedRowCells.forEach(c => {
                                    const colId = c.getAttribute('data-dash-column');
                                    if (colId !== 'Year') {
                                        // Force Month and data cells to be bright with !important
                                        c.style.setProperty('opacity', '1', 'important');
                                        c.style.setProperty('background-color', '#b3d9ff', 'important');
                                        c.style.setProperty('color', '#1b365d', 'important');
                                        c.style.setProperty('font-weight', '600', 'important');
                                        c.style.setProperty('border', 'none', 'important');
                                        c.style.removeProperty('filter');
                                    } else {
                                        // Year column: normal state
                                        c.style.setProperty('opacity', '1', 'important');
                                        c.style.setProperty('background-color', '', 'important');
                                        c.style.setProperty('color', '', 'important');
                                        c.style.setProperty('font-weight', '', 'important');
                                    }
                                });
                                
                                // Use requestAnimationFrame to ensure styles are applied after any Dash updates
                                const selectionCounterForCallback = currentSelectionCounter;
                                requestAnimationFrame(() => {
                                    // Check selection counter to ensure this is still the current selection
                                    const currentCounter = window.priceScorecardState && window.priceScorecardState.selectionCounter;
                                    const currentSelectedRowIndex = window.priceScorecardState && window.priceScorecardState.selectedRowIndex;
                                    
                                    // Only apply if this is still the current selection (counter matches and row index matches)
                                    if (currentCounter === selectionCounterForCallback && 
                                        currentSelectedRowIndex === rowIndex && 
                                        row.classList.contains('row-selected')) {
                                        const selectedRowCells = row.querySelectorAll('td');
                                        selectedRowCells.forEach(c => {
                                            const colId = c.getAttribute('data-dash-column');
                                            if (colId !== 'Year' && c.classList.contains('row-cell-selected')) {
                                                // Force bright styles one more time
                                                c.style.setProperty('opacity', '1', 'important');
                                                c.style.setProperty('background-color', '#b3d9ff', 'important');
                                                c.style.setProperty('color', '#1b365d', 'important');
                                                c.style.setProperty('font-weight', '600', 'important');
                                                c.style.setProperty('border', 'none', 'important');
                                            }
                                        });
                                    }
                                });
                                
                                if (window.priceScorecardState) {
                                    window.priceScorecardState.selectedRowIndex = rowIndex;
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
                    
                    // Reapply sticky columns after handlers are attached
                    setTimeout(function() {
                        applyStickyColumns(spreadsheet);
                        // Also initialize toggles after table is fully set up
                        if (typeof initializeYearHeaderToggle === 'function') {
                            initializeYearHeaderToggle();
                        }
                        if (typeof initializeMonthHeaderToggle === 'function') {
                            initializeMonthHeaderToggle();
                        }
                    }, 200);
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
                const tableEl = document.getElementById('price-scorecard-table');
                if (tableEl) {
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    if (spreadsheet) {
                        // Force reset to allow re-enhancement when switching tabs
                        spreadsheet.dataset.priceScorecardEnhanced = 'false';
                        
                        // Remove old click handler if exists
                        if (spreadsheet._priceScorecardClickHandler) {
                            spreadsheet.removeEventListener('click', spreadsheet._priceScorecardClickHandler, true);
                            spreadsheet._priceScorecardClickHandler = null;
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
                            tryEnhance();
                        }, 200);
                    } else {
                    }
                } else {
                }
                
                // Apply enhancements with multiple attempts to ensure table is rendered
                function tryEnhance() {
                    const tableEl = document.getElementById('price-scorecard-table');
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
                    const isEnhanced = spreadsheet.dataset.priceScorecardEnhanced === 'true';
                    
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
                                        // Re-initialize toggles after enhancement
                                        setTimeout(function() {
                                            const tableEl = document.getElementById('price-scorecard-table');
                                            if (tableEl) {
                                                const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                                                if (spreadsheet && spreadsheet.dataset.priceScorecardEnhanced === 'true') {
                                                    // Access the functions from the enhanceTable closure
                                                    // We'll need to call them through a different mechanism
                                                    // For now, just re-run enhanceTable which will re-initialize
                                                }
                                            }
                                        }, 300);
                                    }, 100);
                                } else if (spreadsheet && spreadsheet.dataset.priceScorecardEnhanced === 'true') {
                                    // Table is enhanced but might need toggle re-initialization
                                    // Re-initialize toggles when data changes
                                    setTimeout(function() {
                                        const yearHeader = spreadsheet.querySelector('th[data-dash-column="Year"]');
                                        const monthHeader = spreadsheet.querySelector('th[data-dash-column="Month"]');
                                        // If headers exist but no toggles, re-initialize
                                        if (yearHeader || monthHeader) {
                                            const hasToggles = spreadsheet.querySelectorAll('.year-header-toggle, .month-header-toggle').length > 0;
                                            if (!hasToggles) {
                                                // Toggles missing, trigger re-enhancement
                                                spreadsheet.dataset.priceScorecardEnhanced = 'false';
                                                enhanceTable();
                                            }
                                        }
                                    }, 200);
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
                    // After enhancement, ensure toggles are initialized
                    setTimeout(function() {
                        const tableEl = document.getElementById('price-scorecard-table');
                        if (tableEl) {
                            const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                            if (spreadsheet && spreadsheet.dataset.priceScorecardEnhanced === 'true') {
                                // Check if toggles exist, if not, re-initialize
                                const yearHeader = spreadsheet.querySelector('th[data-dash-column="Year"]');
                                const hasToggles = spreadsheet.querySelectorAll('.year-header-toggle').length > 0;
                                if (yearHeader && !hasToggles) {
                                    // Toggles missing, force re-enhancement
                                    spreadsheet.dataset.priceScorecardEnhanced = 'false';
                                    tryEnhance();
                                }
                            }
                        }
                    }, 500);
                }, 50);
                
                // Set up periodic reapplication of sticky columns
                if (!window.priceScorecardStickyInterval) {
                    window.priceScorecardStickyInterval = setInterval(function() {
                        const tableEl = document.getElementById('price-scorecard-table');
                        if (tableEl) {
                            const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                            if (spreadsheet) {
                                applyStickyColumns(spreadsheet);
                            }
                        }
                    }, 500);
                }
                
            } catch (error) {
                // Error handled silently
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('price-scorecard-dummy-output', 'children'),
        Input('price-scorecard-table-container', 'children'),
        prevent_initial_call=False
    )
