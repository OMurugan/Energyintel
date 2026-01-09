"""
Price Scorecard for Key World Oil Grades View
Price scorecard table for key crude grades with multi-level headers
"""
from dash import dcc, html, Input, Output, callback, dash_table, State, ctx
import dash
import re
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
        
        # Clickable boxes container
        html.Div([
            # Costs to Refiners box
            html.Button(
                "Costs to Refiners",
                id='costs-to-refiners-btn',
                n_clicks=0,
                style={
                    'display': 'inline-block',
                    'marginRight': '20px',
                    'padding': '12px 20px',
                    'border': '2px solid #ff6600',  # Orange border
                    'color': '#0066cc',  # Blue text
                    'fontSize': '15px',
                    'fontWeight': 'normal',
                    'fontFamily': 'Arial, sans-serif',
                    'width': '30%',
                    'minWidth': '280px',
                    'maxWidth': '350px',
                    'textAlign': 'center',
                    'cursor': 'pointer',
                    'borderRadius': '4px',
                    'height': '45px',
                    'lineHeight': '21px',
                    'boxSizing': 'border-box',
                    'whiteSpace': 'nowrap'
                }
            ),
            
            # Port of Loading box
            html.Button(
                "Port of Loading",
                id='port-of-loading-btn',
                n_clicks=0,
                style={
                    'display': 'inline-block',
                    'marginRight': '20px',
                    'padding': '12px 20px',
                    'border': '2px solid #ff6600',  # Orange border
                    'color': '#0066cc',  # Blue text
                    'fontSize': '15px',
                    'fontWeight': 'normal',
                    'fontFamily': 'Arial, sans-serif',
                    'width': '30%',
                    'minWidth': '280px',
                    'maxWidth': '350px',
                    'textAlign': 'center',
                    'cursor': 'pointer',
                    'borderRadius': '4px',
                    'height': '45px',
                    'lineHeight': '21px',
                    'boxSizing': 'border-box',
                    'whiteSpace': 'nowrap'
                }
            ),
            
            # Price Formula box
            html.Button(
                "Price Formula",
                id='price-formula-btn',
                n_clicks=0,
                style={
                    'display': 'inline-block',
                    'padding': '12px 20px',
                    'border': '2px solid #ff6600',  # Orange border
                    'color': '#0066cc',  # Blue text
                    'fontSize': '15px',
                    'fontWeight': 'bold',
                    'fontFamily': 'Arial, sans-serif',
                    'width': '30%',
                    'minWidth': '280px',
                    'maxWidth': '350px',
                    'textAlign': 'center',
                    'cursor': 'pointer',
                    'borderRadius': '4px',
                    'height': '45px',
                    'lineHeight': '21px',
                    'boxSizing': 'border-box',
                    'whiteSpace': 'nowrap'
                }
            )
        ], style={
            'marginBottom': '30px',
            'textAlign': 'center',
            'display': 'flex',
            'justifyContent': 'center',
            'alignItems': 'center',
            'flexWrap': 'nowrap',
            'gap': '0px',
            'width': '100%',
            'minWidth': '900px',
            'overflowX': 'auto'
        }),
        # Title - left-aligned, orange-brown, serif font
        html.H3("PIW SCORECARD -- COSTS TO REFINERS OF KEY FORMULA PRICED CRUDE OILS IN PRIMARY WORLD MARKETS ($/bbl)", 
        id='price-scorecard-header',
        style={
            'marginBottom': '20px', 
            'fontSize': '16px', 
            'fontWeight': 'bold',
            'textAlign': 'start',
            'color': '#cc6600',  # Orange-brown color
            'fontFamily': 'Times New Roman, serif',
            'padding': '0',
            'margin': '0px 55px 20px'
        }),
        # Export button
        html.Div([
            html.Div([
                html.Button(
                    "Export to CSV",
                    id="price-scorecard-export-btn",
                    n_clicks=0,
                    style={
                        'backgroundColor': 'white',
                        'color': '#2c3e50',
                        'border': '1px solid #dee2e6',
                        'padding': '6px 12px',
                        'borderRadius': '4px',
                        'cursor': 'pointer',
                        'fontSize': '13px',
                        'display': 'inline-block'
                    }
                ),
                dcc.Download(id="download-price-scorecard-csv"),
            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'flex-end', 'marginBottom': '10px'}),
        ], style={'width': '100%'}),
        
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
        ),
        
        # Footnote
        html.Div(id='price-scorecard-footnote', style={
            'marginTop': '20px',
            'fontSize': '13px',
            'color': 'grey',
            'fontFamily': '"Benton Sans Low-DPI", Arial, Helvetica, sans-serif',
            'textAlign': 'left'
        }),
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
            a.point_of_sale AS "Point Of Sale",
            EXTRACT(DAY FROM a.date)::int AS day_num,
            CONCAT('Q', EXTRACT(QUARTER FROM a.date)::int) AS quarter
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
        df['Day'] = df['day_num'].astype(str)
        df['Quarter'] = df['quarter'].astype(str)
        
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
        
        # Ensure Year, Quarter, Month, Day are strings, convert value columns to numeric in one pass
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
    
    # First four columns: Year, Quarter, Month, Day
    # Use zero-width characters to ensure proper alignment in multi-level headers
    columns.append({'name': ['\u200B', '\u200B', '\u200B', 'Year'], 'id': 'Year'})
    columns.append({'name': ['\u200C', '\u200C', '\u200C', 'Quarter'], 'id': 'Quarter'})
    columns.append({'name': ['\u200D', '\u200D', '\u200D', 'Month'], 'id': 'Month'})
    columns.append({'name': ['\u200E', '\u200E', '\u200E', 'Day'], 'id': 'Day'})
    
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
    # Track row indices for year and quarter boundaries
    year_boundary_rows = []
    current_row_index = 0
    records = []
    
    # Sort data by Year (desc), Month (desc), Day (desc)
    # Define month order for sorting
    month_mapping = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    
    data_df = data_df.copy()
    data_df['MonthNum'] = data_df['Month'].map(month_mapping)
    data_df['YearInt'] = pd.to_numeric(data_df['Year'], errors='coerce')
    data_df['DayInt'] = pd.to_numeric(data_df['Day'], errors='coerce')
    
    sorted_df = data_df.sort_values(['YearInt', 'MonthNum', 'DayInt'], ascending=[False, False, False])
    
    current_year = None
    current_quarter = None
    current_month = None
    
    for _, row in sorted_df.iterrows():
        year = row['Year']
        quarter = row['Quarter']
        month = row['Month']
        day = row['Day']
        
        # Format year to remove decimal
        try:
            year_val = str(int(float(year)))
        except:
            year_val = str(year)
            
        record = {
            'Year': year_val if year_val != current_year else None,
            'Quarter': quarter if (year_val != current_year or quarter != current_quarter) else None,
            'Month': month if (year_val != current_year or quarter != current_quarter or month != current_month) else None,
            'Day': day,
            'Year_Quarter_Month_Day': f"{year_val}_{quarter}_{month}_{day}"
        }
        
        current_year = year_val
        current_quarter = quarter
        current_month = month
            
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
        
        # Track the last row of each year group for border styling - using a simple check
        # Let's just use a simple approach: if Year is not None, it's a boundary.
        if record['Year'] is not None and current_row_index > 0:
            year_boundary_rows.append(current_row_index - 1)
        
        records.append(record)
        current_row_index += 1
            
    return records, year_boundary_rows


def register_callbacks(dash_app, server):
    """Register all callbacks for Price Scorecard"""
    
    # Callback to update selected type filter when buttons are clicked
    @dash_app.callback(
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
    @dash_app.callback(
        [Output('costs-to-refiners-btn', 'style'),
         Output('port-of-loading-btn', 'style'),
         Output('price-formula-btn', 'style')],
        Input('selected-type-filter', 'data')
    )
    def update_button_styles(selected_type):
        """Update button styles to show which one is active"""
        base_style = {
            'display': 'inline-block',
            'marginRight': '20px',
            'padding': '12px 20px',
            'border': '2px solid #ff6600',
            'color': '#0066cc',
            'fontSize': '15px',
            'fontWeight': 'normal',
            'fontFamily': 'Arial, sans-serif',
            'width': '30%',
            'minWidth': '280px',
            'maxWidth': '350px',
            'textAlign': 'center',
            'cursor': 'pointer',
            'borderRadius': '4px',
            'height': '45px',
            'lineHeight': '21px',
            'boxSizing': 'border-box',
            'whiteSpace': 'nowrap'
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

    # Callback to update the heading text and footnote based on selected type
    @dash_app.callback(
        [Output('price-scorecard-header', 'children'),
         Output('price-scorecard-footnote', 'children')],
        Input('selected-type-filter', 'data')
    )
    def update_header_and_footnote(selected_type):
        """Update header text and footnote based on selected type"""
        if selected_type == 'Port of Loading':
            header = "PIW SCORECARD -- CRUDE VALUES AT PORT OF LOADING ($/bbl)"
            footnote = ""
        elif selected_type == 'Price Formula':
            header = "PIW SCORECARD - PRICE FORMULA ADJUSTMENT FACTORS ($/bbl)"
            footnote = "f.o.b. is freight on board,"
        else:
            header = "PIW SCORECARD -- COSTS TO REFINERS OF KEY FORMULA PRICED CRUDE OILS IN PRIMARY WORLD MARKETS ($/bbl)"
            footnote = "f.o.b. is freight on board, c.i.f. is cargo, insurance and freight"
            
        return header, footnote
    
    # Callback to update table based on selected type filter
    @dash_app.callback(
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
            
            # Count value columns (excluding Year and Month)
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
                    'height': '1000px',
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
                    'border': '1px solid #E6E6E6',
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
                    'border': '1px solid #E6E6E6',
                    'padding': '6px 8px',
                    'fontSize': '11px',
                    'fontFamily': '"Benton Sans Low-DPI", Arial, Helvetica, sans-serif',
                    'color': '#1b365d'  # Apply color to all data cell fonts
                },
                style_data_conditional=([
                    {
                        'if': {'column_id': 'Year'},
                        'textAlign': 'left',
                        'fontWeight': 'bold',
                        'color': '#1b365d'
                    },
                    {
                        'if': {'column_id': 'Quarter'},
                        'textAlign': 'left',
                        'fontWeight': 'bold',
                        'color': '#1b365d'
                    },
                    {
                        'if': {'column_id': 'Month'},
                        'textAlign': 'left',
                        'fontWeight': 'bold',
                        'color': '#1b365d'
                    },
                    {
                        'if': {'column_id': 'Day'},
                        'textAlign': 'left',
                        'fontWeight': 'bold',
                        'color': '#1b365d'
                    }
                ] + [
                    {
                        'if': {'column_id': f'col_{i}'},
                        'textAlign': 'right',
                        'fontWeight': 'normal',
                        'color': '#1b365d'
                    } for i in range(num_cols_to_use)
                ] + year_boundary_styles),
                style_header_conditional=[
                    {
                        'if': {'header_index': 0},
                        'backgroundColor': 'white',
                        'fontWeight': '900',
                        'textAlign': 'center',
                        'color': '#ff6600'
                    },
                    {
                        'if': {'header_index': 1},
                        'backgroundColor': 'white',
                        'fontWeight': '900',
                        'textAlign': 'center',
                        'color': '#1b365d'
                    },
                    {
                        'if': {'header_index': 2},
                        'backgroundColor': 'white',
                        'fontWeight': '900',
                        'textAlign': 'center',
                        'color': '#1b365d'
                    },
                    {
                        'if': {'header_index': 3},
                        'backgroundColor': 'white',
                        'fontWeight': '900',
                        'textAlign': 'center',
                        'color': '#1b365d'
                    }
                ],
                fixed_rows={'headers': True},
                page_action='none',
                sort_action='native',
                filter_action='none',
                css=[
                    {
                        'selector': 'tbody tr:nth-child(odd) td:not(.column-cell-selected):not(.row-cell-selected)',
                        'rule': 'background-color: #f0f0f0 !important; color: #1b365d !important;'
                    },
                    {
                        'selector': 'tbody tr:nth-child(even) td:not(.column-cell-selected):not(.row-cell-selected)',
                        'rule': 'background-color: white !important; color: #1b365d !important;'
                    },
                    {
                        'selector': 'tbody td',
                        'rule': 'color: #1b365d !important;'
                    },
                    {
                        'selector': 'tbody td[data-dash-column="Year"], tbody td[data-dash-column="Quarter"], tbody td[data-dash-column="Month"], tbody td[data-dash-column="Day"]',
                        'rule': 'font-weight: bold !important; color: #1b365d !important;'
                    },
                    {
                        'selector': '.dash-table-tooltip',
                        'rule': 'display: none'
                    },
                    {
                        'selector': '#price-scorecard-table thead tr:nth-child(1) th',
                        'rule': 'font-weight: 900 !important; text-shadow: 0.5px 0 0 currentColor, -0.5px 0 0 currentColor !important; color: #ff6600 !important;'
                    },
                    {
                        'selector': '#price-scorecard-table thead tr:nth-child(2) th',
                        'rule': 'font-weight: 900 !important; text-shadow: 0.5px 0 0 currentColor, -0.5px 0 0 currentColor !important; color: #1b365d !important;'
                    },
                    {
                        'selector': '#price-scorecard-table thead tr:nth-child(3) th',
                        'rule': 'font-weight: 900 !important; text-shadow: 0.5px 0 0 currentColor, -0.5px 0 0 currentColor !important; color: #1b365d !important;'
                    },
                    {
                        'selector': '#price-scorecard-table thead tr:nth-child(4) th',
                        'rule': 'font-weight: 900 !important; text-shadow: 0.5px 0 0 currentColor, -0.5px 0 0 currentColor !important; color: #1b365d !important;'
                    },
                    {
                        'selector': '#price-scorecard-table th[data-dash-column="Year"], #price-scorecard-table th[data-dash-column="Quarter"], #price-scorecard-table th[data-dash-column="Month"], #price-scorecard-table th[data-dash-column="Day"]',
                        'rule': 'font-weight: 900 !important; text-shadow: 0.5px 0 0 currentColor, -0.5px 0 0 currentColor !important; color: #1b365d !important; text-align: center !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Year"], #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Quarter"], #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Month"], #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Day"]',
                        'rule': 'font-weight: 900 !important; text-shadow: 0.5px 0 0 currentColor, -0.5px 0 0 currentColor !important; color: #1b365d !important; text-align: center !important;'
                    },
                    {
                        'selector': '#price-scorecard-table thead th[data-dash-column="Year"], #price-scorecard-table thead th[data-dash-column="Quarter"], #price-scorecard-table thead th[data-dash-column="Month"], #price-scorecard-table thead th[data-dash-column="Day"]',
                        'rule': 'font-weight: 900 !important; text-shadow: 0.5px 0 0 currentColor, -0.5px 0 0 currentColor !important; color: #1b365d !important; text-align: center !important;'
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
                        'rule': 'background-color: #b3d9ff !important; border: none !important; font-weight: bold !important; color: #1b365d !important; opacity: 1 !important;'
                    },
                    {
                        'selector': '#price-scorecard-table .dash-spreadsheet-container td.row-cell-selected',
                        'rule': 'background-color: #b3d9ff !important; border: none !important; font-weight: bold !important; color: #1b365d !important; opacity: 1 !important;'
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
                        'rule': 'opacity: 1 !important; background-color: #b3d9ff !important; color: #1b365d !important; font-weight: bold !important; border: none !important;'
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
                    html.Pre(error_details, style={'whiteSpace': 'pre-wrap', 'fontSize': '10px'})
                ]
            )

    @dash_app.callback(
        Output("download-price-scorecard-csv", "data"),
        Input("price-scorecard-export-btn", "n_clicks"),
        [State("price-scorecard-table", "data"),
         State("price-scorecard-table", "columns")],
        prevent_initial_call=True
    )
    def export_price_scorecard_csv(n_clicks, data, columns):
        if not n_clicks or not data:
            raise dash.exceptions.PreventUpdate

        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Get column names for sorting
        col_names = [c['id'] for c in columns]
        # Only keep columns that are in the dataframe
        col_names = [c for c in col_names if c in df.columns]
        df = df[col_names]
        
        # Rename columns to their display names (joined multi-level headers)
        rename_dict = {}
        for c in columns:
            if isinstance(c['name'], list):
                # Filter out empty strings and invisible characters, then join
                # Removing invisible characters like \u200B, \u200C, \u200D, \uFEFF
                clean_names = []
                for n in c['name']:
                    if n and n.strip():
                        clean_n = n.replace('\u200B', '').replace('\u200C', '').replace('\u200D', '').replace('\uFEFF', '').strip()
                        if clean_n:
                            clean_names.append(clean_n)
                
                joined_name = " / ".join(clean_names)
                rename_dict[c['id']] = joined_name
            else:
                rename_dict[c['id']] = c['name']
        
        df = df.rename(columns=rename_dict)

        return dcc.send_data_frame(df.to_csv, "price_scorecard_export.csv", index=False)
    
    # Client-side callback to handle header clicks and column highlighting
    dash_app.clientside_callback(
        """
        function(_id) {
            try {
                // Custom CSS for Quarter and Day column toggling
                const styleId = 'price-scorecard-table-toggle-styles';
                if (!document.getElementById(styleId)) {
                    const style = document.createElement('style');
                    style.id = styleId;
                    style.textContent = `
                        /* Toggle columns: Quarter and Day hidden by default */
                        #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Quarter"],
                        #price-scorecard-table .dash-spreadsheet-container td[data-dash-column="Quarter"],
                        #price-scorecard-table .dash-spreadsheet-container th[data-dash-column="Day"],
                        #price-scorecard-table .dash-spreadsheet-container td[data-dash-column="Day"] {
                            display: none !important; width: 0 !important; min-width: 0 !important; max-width: 0 !important;
                            padding: 0 !important; margin: 0 !important; border: none !important;
                            overflow: hidden !important; visibility: hidden !important;
                        }
                        #price-scorecard-table .dash-spreadsheet-container.year-expanded th[data-dash-column="Quarter"],
                        #price-scorecard-table .dash-spreadsheet-container.year-expanded td[data-dash-column="Quarter"] {
                            display: table-cell !important; width: auto !important; min-width: 60px !important;
                            max-width: none !important; padding: 6px 10px !important; margin: 0 !important;
                            border: 1px solid #e6e6e6 !important; overflow: visible !important; visibility: visible !important;
                        }
                        #price-scorecard-table .dash-spreadsheet-container.month-expanded th[data-dash-column="Day"],
                        #price-scorecard-table .dash-spreadsheet-container.month-expanded td[data-dash-column="Day"] {
                            display: table-cell !important; width: auto !important; min-width: 50px !important;
                            max-width: none !important; padding: 6px 10px !important; margin: 0 !important;
                            border: 1px solid #e6e6e6 !important; overflow: visible !important; visibility: visible !important;
                        }
                        /* Quarter collapsed: hide Month and Day even if expanded */
                        #price-scorecard-table .dash-spreadsheet-container.year-expanded.quarter-collapsed th[data-dash-column="Month"],
                        #price-scorecard-table .dash-spreadsheet-container.year-expanded.quarter-collapsed td[data-dash-column="Month"],
                        #price-scorecard-table .dash-spreadsheet-container.year-expanded.quarter-collapsed th[data-dash-column="Day"],
                        #price-scorecard-table .dash-spreadsheet-container.year-expanded.quarter-collapsed td[data-dash-column="Day"] {
                            display: none !important; width: 0 !important; padding: 0 !important; border: none !important;
                        }

                        /* Toggle buttons: match global_prices.py style */
                        .year-header-toggle, .month-header-toggle, .quarter-header-toggle {
                            display: none; margin-left: 6px; width: 16px; height: 16px; line-height: 14px;
                            text-align: center; font-size: 12px; font-weight: normal; color: #505050;
                            border: 1px solid #d0d0d0; border-radius: 2px; background-color: #ffffff;
                            user-select: none; cursor: pointer; vertical-align: middle; flex-shrink: 0;
                            box-sizing: border-box; transition: all 0.15s ease; font-family: Arial, sans-serif;
                        }
                        th[data-dash-column="Year"]:hover .year-header-toggle,
                        th[data-dash-column="Month"]:hover .month-header-toggle,
                        th[data-dash-column="Quarter"]:hover .quarter-header-toggle {
                            display: inline-block;
                        }
                        .year-header-toggle:hover, .month-header-toggle:hover, .quarter-header-toggle:hover {
                            color: #333333; border-color: #a0a0a0; background-color: #f0f0f0;
                        }
                    `;
                    document.head.appendChild(style);
                }

                if (!window.priceScorecardState) {
                    window.priceScorecardState = {
                        selectedColumnId: null, selectedRowIndex: null, lastTableSignature: null,
                        isYearExpanded: false, isMonthExpanded: false, isQuarterCollapsed: false
                    };
                } else {
                    if (window.priceScorecardState.isYearExpanded === undefined) window.priceScorecardState.isYearExpanded = false;
                    if (window.priceScorecardState.isMonthExpanded === undefined) window.priceScorecardState.isMonthExpanded = false;
                    if (window.priceScorecardState.isQuarterCollapsed === undefined) window.priceScorecardState.isQuarterCollapsed = false;
                }
                
                function clearAllColumnSelections(spreadsheet) {
                    if (!spreadsheet) return;
                    const selectedHeaders = spreadsheet.querySelectorAll('th.column-selected');
                    selectedHeaders.forEach(header => {
                        header.classList.remove('column-selected');
                        header.style.removeProperty('background-color');
                        header.style.removeProperty('color');
                        header.style.removeProperty('font-weight');
                    });
                    
                    const selectedCells = spreadsheet.querySelectorAll('td.column-cell-selected');
                    selectedCells.forEach(cell => {
                        cell.classList.remove('column-cell-selected');
                        cell.style.removeProperty('background-color');
                        cell.style.removeProperty('border');
                        cell.style.removeProperty('font-weight');
                        cell.style.removeProperty('color');
                        cell.style.removeProperty('opacity');
                    });
                    
                    if (spreadsheet.classList.contains('column-selection-active')) {
                        const allDataCells = spreadsheet.querySelectorAll('td[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Quarter"]):not([data-dash-column="Month"]):not([data-dash-column="Day"])');
                        allDataCells.forEach(cell => {
                            cell.style.removeProperty('opacity');
                        });
                    }
                    spreadsheet.classList.remove('column-selection-active');
                }
                
                function clearAllRowSelections(spreadsheet) {
                    if (!spreadsheet) return;
                    const selectedRows = spreadsheet.querySelectorAll('tr.row-selected');
                    selectedRows.forEach(row => { row.classList.remove('row-selected'); });
                    
                    const cellsWithProperties = spreadsheet.querySelectorAll('td.row-cell-selected, th.row-cell-selected');
                    cellsWithProperties.forEach(cell => {
                        cell.classList.remove('row-cell-selected');
                        cell.style.removeProperty('background-color');
                        cell.style.removeProperty('border');
                        cell.style.removeProperty('font-weight');
                        cell.style.removeProperty('color');
                    });

                    // Reset opacity for ALL cells to return to normal state
                    const allTableCells = spreadsheet.querySelectorAll('td, th');
                    allTableCells.forEach(cell => {
                        cell.style.removeProperty('opacity');
                    });

                    spreadsheet.classList.remove('row-selection-active');
                    if (window.priceScorecardState) {
                        window.priceScorecardState.selectedYear = null;
                        window.priceScorecardState.selectedRowIndex = null;
                    }
                }
                
                function getCellValue(cell) {
                    const text = cell.textContent || cell.innerText || '';
                    return text.trim();
                }

                function addToggleIcon(cell, iconClass, isExpanded, onClickHandler) {
                    const existingIcon = cell.querySelector('.' + iconClass);
                    if (existingIcon) {
                        existingIcon.textContent = isExpanded ? '−' : '+';
                        return existingIcon;
                    }
                    const icon = document.createElement('span');
                    icon.className = iconClass;
                    icon.textContent = isExpanded ? '−' : '+';
                    cell.appendChild(icon);
                    icon.addEventListener('click', (e) => { e.stopPropagation(); onClickHandler(); });
                    return icon;
                }

                function toggleYearExpand() {
                    const spreadsheet = document.querySelector('#price-scorecard-table .dash-spreadsheet-container');
                    if (!spreadsheet) return;
                    window.priceScorecardState.isYearExpanded = !window.priceScorecardState.isYearExpanded;
                    if (window.priceScorecardState.isYearExpanded) {
                        spreadsheet.classList.add('year-expanded');
                    } else {
                        spreadsheet.classList.remove('year-expanded');
                        window.priceScorecardState.isQuarterCollapsed = false;
                        spreadsheet.classList.remove('quarter-collapsed');
                    }
                    enhanceTable();
                }

                function toggleQuarterCollapse() {
                    const spreadsheet = document.querySelector('#price-scorecard-table .dash-spreadsheet-container');
                    if (!spreadsheet) return;
                    window.priceScorecardState.isQuarterCollapsed = !window.priceScorecardState.isQuarterCollapsed;
                    if (window.priceScorecardState.isQuarterCollapsed) spreadsheet.classList.add('quarter-collapsed');
                    else spreadsheet.classList.remove('quarter-collapsed');
                    enhanceTable();
                }

                function toggleMonthExpand() {
                    const spreadsheet = document.querySelector('#price-scorecard-table .dash-spreadsheet-container');
                    if (!spreadsheet) return;
                    window.priceScorecardState.isMonthExpanded = !window.priceScorecardState.isMonthExpanded;
                    if (window.priceScorecardState.isMonthExpanded) spreadsheet.classList.add('month-expanded');
                    else spreadsheet.classList.remove('month-expanded');
                    enhanceTable();
                }

                function enhanceTable() {
                    const tableEl = document.getElementById('price-scorecard-table');
                    if (!tableEl) return;
                    const spreadsheet = tableEl.querySelector('.dash-spreadsheet-container');
                    if (!spreadsheet) return;
                    
                    const headers = spreadsheet.querySelectorAll('th[data-dash-column]');
                    if (headers.length === 0) return;
                    
                    let tableSignature = '';
                    const topRow = spreadsheet.querySelector('thead tr');
                    if (topRow) {
                        const topHeaders = Array.from(topRow.querySelectorAll('th')).slice(0, 5);
                        tableSignature = topHeaders.map(h => h.textContent.trim()).join('|') + '|' + headers.length;
                    } else tableSignature = headers.length.toString();
                    
                    const signatureChanged = window.priceScorecardState.lastTableSignature !== tableSignature;
                    if (signatureChanged) {
                        spreadsheet.dataset.priceScorecardEnhanced = 'false';
                        if (spreadsheet._priceScorecardClickHandler) {
                            spreadsheet.removeEventListener('click', spreadsheet._priceScorecardClickHandler, true);
                            spreadsheet._priceScorecardClickHandler = null;
                        }
                        clearAllColumnSelections(spreadsheet);
                        clearAllRowSelections(spreadsheet);
                        window.priceScorecardState.lastTableSignature = tableSignature;
                    }
                    
                    if (spreadsheet.dataset.priceScorecardEnhanced === 'true' && !signatureChanged) {
                        // Just update icon text if already enhanced
                        const yearToggle = spreadsheet.querySelector('.year-header-toggle');
                        if (yearToggle) yearToggle.textContent = window.priceScorecardState.isYearExpanded ? '−' : '+';
                        const monthToggle = spreadsheet.querySelector('.month-header-toggle');
                        if (monthToggle) monthToggle.textContent = window.priceScorecardState.isMonthExpanded ? '−' : '+';
                        return;
                    }
                    
                    spreadsheet.dataset.priceScorecardEnhanced = 'true';

                    // Initialize Year Toggle
                    const yearHeaders = Array.from(spreadsheet.querySelectorAll('th[data-dash-column="Year"]'));
                    const yearHeader = yearHeaders.find(h => h.textContent.trim().includes('Year')) || yearHeaders[yearHeaders.length - 1];
                    if (yearHeader) addToggleIcon(yearHeader, 'year-header-toggle', window.priceScorecardState.isYearExpanded, toggleYearExpand);

                    // Initialize Quarter Toggle (only if Year is expanded)
                    if (window.priceScorecardState.isYearExpanded) {
                        const quarterHeaders = Array.from(spreadsheet.querySelectorAll('th[data-dash-column="Quarter"]'));
                        const quarterHeader = quarterHeaders.find(h => h.textContent.trim().includes('Quarter')) || quarterHeaders[quarterHeaders.length - 1];
                        if (quarterHeader) addToggleIcon(quarterHeader, 'quarter-header-toggle', window.priceScorecardState.isQuarterCollapsed, toggleQuarterCollapse);
                    }

                    // Initialize Month Toggle
                    const monthHeaders = Array.from(spreadsheet.querySelectorAll('th[data-dash-column="Month"]'));
                    const monthHeader = monthHeaders.find(h => h.textContent.trim().includes('Month')) || monthHeaders[monthHeaders.length - 1];
                    if (monthHeader) addToggleIcon(monthHeader, 'month-header-toggle', window.priceScorecardState.isMonthExpanded, toggleMonthExpand);
                    
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
                                if (toggleBtn) {
                                    toggleYearExpand();
                                    return;
                                }
                            }
                            
                            // Handle Quarter header toggle
                            if (columnId === 'Quarter') {
                                const toggleBtn = event.target.closest('.quarter-header-toggle');
                                if (toggleBtn) {
                                    toggleQuarterCollapse();
                                    return;
                                }
                            }

                            // Handle Month header toggle
                            if (columnId === 'Month') {
                                const toggleBtn = event.target.closest('.month-header-toggle');
                                if (toggleBtn) {
                                    toggleMonthExpand();
                                    return;
                                }
                            }
                            
                            // Skip hierarchy columns for selection logic
                            if (['Year', 'Quarter', 'Month', 'Day'].includes(columnId)) return;
                            
                            // Check if this exact header level is already selected BEFORE clearing
                            const headerRow = header.closest('tr');
                            const thead = header.closest('thead');
                            let headerIndex = -1;
                            let headerRows = thead ? Array.from(thead.querySelectorAll('tr')) : [];
                            
                            // Filter to rows with column IDs
                            headerRows = headerRows.filter(tr => tr.querySelector('th[data-dash-column]') !== null);
                            if (headerRow) headerIndex = headerRows.indexOf(headerRow);
                            
                            const selectionKey = columnId + '_' + headerIndex;
                            const alreadySelected = (window.priceScorecardState && window.priceScorecardState.selectedColumnId === selectionKey);
                            
                            // Clear all previous selections
                            clearAllColumnSelections(clickedSpreadsheet);
                            clearAllRowSelections(clickedSpreadsheet);
                            if (window.priceScorecardState) {
                                window.priceScorecardState.selectedRowIndex = null;
                                window.priceScorecardState.selectedYear = null;
                            }
                            
                            if (alreadySelected) {
                                // Deselect - already cleared state and UI above
                                if (window.priceScorecardState) {
                                    window.priceScorecardState.selectedColumnId = null;
                                }
                                return false;
                            }
                            
                            // If not already selected, continue with selection logic (rest of function will be reached)
                            
                            // Note: the rest of the original code follows here, starting with determining headerIndex etc.
                            // I will keep the original logic for determining headerIndex as it was more robust.
                            
                            let totalHeaderRows = 0;
                            headerRows = thead ? Array.from(thead.querySelectorAll('tr')) : [];
                            
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
                            
                            // Filter out rows that don't contain any column headers
                            headerRows = headerRows.filter(tr => {
                                return tr.querySelector('th[data-dash-column]') !== null;
                            });
                            
                            totalHeaderRows = headerRows.length;
                            
                            if (headerRow && headerRows.length > 0) {
                                headerIndex = headerRows.indexOf(headerRow);
                            } else if (headerRow) {
                                // If headerRow is not in the filtered list, it might be a Year/Month row
                                // Try to find it in the original thead rows
                                const theadRows = thead ? Array.from(thead.querySelectorAll('tr')) : [];
                                const allDataRows = theadRows.filter(tr => {
                                    return tr.querySelector('th[data-dash-column]') !== null;
                                });
                                if (allDataRows.length > 0) {
                                    headerIndex = allDataRows.indexOf(headerRow);
                                    headerRows = allDataRows;
                                    totalHeaderRows = headerRows.length;
                                }
                            }
                            // Create new selection - all previous selections are already cleared above
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
                                                        
                                                        // Skip Year/Month - they don't count as data columns
                                                        if (cellColId === 'Year' || cellColId === 'Month') {
                                                            continue;
                                                        }
                                                        
                                                        // Count the colspan of this header (how many data columns it spans)
                                                        const cellColspan = parseInt(cell.getAttribute('colspan') || cell.colSpan || '1');
                                                        topRowDataStart += cellColspan;
                                                    }
                                                    
                                                    
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
                                                            }
                                                        }
                                                        
                                                        // Increment data column index (only for non-Year/Month cells)
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
                                                            // Get all cells from the first row in order (including Year/Month)
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
                                                            
                                                            // Get column IDs in order, skipping Year/Month
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
                                                            
                                                            // Scan first 10 rows to build position map (efficiency)
                                                            const scannerRows = Array.from(allDataRows).slice(0, 10);
                                                            scannerRows.forEach(row => {
                                                                if (row.querySelector('th')) return;
                                                                
                                                                const rowCells = Array.from(row.querySelectorAll('td'));
                                                                let dataColIndex = 0;
                                                                
                                                                rowCells.forEach(cell => {
                                                                    const colId = cell.getAttribute('data-dash-column');
                                                                    if (colId === 'Year' || colId === 'Month') return;
                                                                    
                                                                    if (dataColIndex < maxPositionNeeded && !columnPositionMap.has(dataColIndex)) {
                                                                        if (colId && (colId.startsWith('col_') || colId.length > 0)) {
                                                                            columnPositionMap.set(dataColIndex, colId);
                                                                        }
                                                                    }
                                                                    dataColIndex++;
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
                                            
                                            
                                            // Highlight only the clicked top header cell itself
                                            header.classList.add('column-selected');
                                            header.style.backgroundColor = '#b3d9ff';
                                            header.style.color = '#1b365d';
                                            header.style.fontWeight = 'bold';
                                            
                                            // Highlight data cells for all columns under this top header
                                            if (columnIds.size > 0) {
                                                const selector = Array.from(columnIds).map(colId => `td[data-dash-column="${colId}"]`).join(',');
                                                const colCells = clickedSpreadsheet.querySelectorAll(selector);
                                                colCells.forEach(cell => {
                                                    cell.classList.add('column-cell-selected');
                                                    cell.style.backgroundColor = '#b3d9ff';
                                                    cell.style.fontWeight = '600';
                                                    cell.style.color = '#1b365d';
                                                    cell.style.opacity = '1';
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
                                        }
                                    } else {
                                        // Bottom header clicked
                                        header.classList.add('column-selected');
                                        header.style.backgroundColor = '#b3d9ff';
                                        header.style.color = '#1b365d';
                                        header.style.fontWeight = 'bold';
                                        
                                        // Highlight all data cells for this column
                                        const columnCells = clickedSpreadsheet.querySelectorAll(`td[data-dash-column="${columnId}"]`);
                                        columnCells.forEach(cell => {
                                            cell.classList.add('column-cell-selected');
                                            cell.style.backgroundColor = '#b3d9ff';
                                            cell.style.fontWeight = '600';
                                            cell.style.color = '#1b365d';
                                            cell.style.opacity = '1';
                                        });
                                        
                                        clickedSpreadsheet.classList.add('column-selection-active');
                                        
                                        // Dim others
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
                                        const currentRow = (headerRows && headerIndex >= 0) ? headerRows[headerIndex] : null;
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
                                                
                                                // Skip Year/Month
                                                if (cellColId === 'Year' || cellColId === 'Month') {
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
                                                
                                                
                                                // Scan first 10 rows to build position map
                                                const scannerRows = Array.from(allDataRows).slice(0, 10);
                                                scannerRows.forEach(row => {
                                                    if (row.querySelector('th')) return;
                                                    const rowCells = Array.from(row.querySelectorAll('td'));
                                                    let dataColIndex = 0;
                                                    rowCells.forEach(cell => {
                                                        const colId = cell.getAttribute('data-dash-column');
                                                        if (colId === 'Year' || colId === 'Month') return;
                                                        if (dataColIndex >= columnsBefore && dataColIndex < columnsBefore + spanCount) {
                                                            if (!columnPositionMap.has(dataColIndex) && colId) {
                                                                columnPositionMap.set(dataColIndex, colId);
                                                            }
                                                        }
                                                        dataColIndex++;
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
                                    
                                    
                                    // Highlight only the clicked header cell itself
                                    header.classList.add('column-selected');
                                    header.style.backgroundColor = '#b3d9ff';
                                    header.style.color = '#1b365d';
                                    header.style.fontWeight = 'bold';
                                    
                                    // Highlight data cells for all columns under this middle header
                                    if (columnIds.size > 0) {
                                        const selector = Array.from(columnIds).map(colId => `td[data-dash-column="${colId}"]`).join(',');
                                        const colCells = clickedSpreadsheet.querySelectorAll(selector);
                                        colCells.forEach(cell => {
                                            cell.classList.add('column-cell-selected');
                                            cell.style.backgroundColor = '#b3d9ff';
                                            cell.style.fontWeight = '600';
                                            cell.style.color = '#1b365d';
                                            cell.style.opacity = '1';
                                        });
                                        
                                        clickedSpreadsheet.classList.add('column-selection-active');
                                        
                                        // Dim other columns
                                        const allDataCells = clickedSpreadsheet.querySelectorAll('td[data-dash-column]:not([data-dash-column="Year"]):not([data-dash-column="Quarter"]):not([data-dash-column="Month"]):not([data-dash-column="Day"])');
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
                            return false; // Prevent default
                        }
                        
                        // Handle row highlighting when clicking on hierarchy cells
                        const hierarchyCell = event.target.closest('td[data-dash-column="Year"], td[data-dash-column="Quarter"], td[data-dash-column="Month"], td[data-dash-column="Day"]');
                        if (hierarchyCell) {
                            event.stopPropagation();
                            const columnId = hierarchyCell.getAttribute('data-dash-column');
                            const cellValue = getCellValue(hierarchyCell);
                            const row = hierarchyCell.closest('tr');
                            if (!row) return;
                            
                            const rowIndex = row.getAttribute('data-dash-row') || Array.from(row.parentNode.children).indexOf(row).toString();

                            clearAllColumnSelections(clickedSpreadsheet);
                            
                            if (window.priceScorecardState && window.priceScorecardState.selectedRowIndex === (columnId + '_' + rowIndex + '_' + cellValue)) {
                                clearAllRowSelections(clickedSpreadsheet);
                                window.priceScorecardState.selectedRowIndex = null;
                                return;
                            }

                            clearAllRowSelections(clickedSpreadsheet);
                            
                            const allRows = Array.from(clickedSpreadsheet.querySelectorAll('tbody tr'));
                            const currentRowIndex = allRows.indexOf(row);
                            
                            let startIndex = currentRowIndex;
                            let firstLabelCell = hierarchyCell;

                            // Find start index (look up to find the non-empty label cell)
                            if (cellValue === "") {
                                for (let i = currentRowIndex; i >= 0; i--) {
                                    const cell = allRows[i].querySelector(`td[data-dash-column="${columnId}"]`);
                                    if (getCellValue(cell) !== "") {
                                        startIndex = i;
                                        firstLabelCell = cell;
                                        break;
                                    }
                                }
                            }
                            
                            // Find end index (look down to find the row before the next label)
                            let endIndex = allRows.length - 1;
                            for (let i = startIndex + 1; i < allRows.length; i++) {
                                const val = getCellValue(allRows[i].querySelector(`td[data-dash-column="${columnId}"]`));
                                if (val !== "") {
                                    endIndex = i - 1;
                                    break;
                                }
                            }

                            targetRows = allRows.slice(startIndex, endIndex + 1);

                            targetRows.forEach(r => {
                                r.classList.add('row-selected');
                                r.querySelectorAll('td').forEach(c => {
                                    const cColId = c.getAttribute('data-dash-column');
                                    // Highlight data cells
                                    if (!['Year', 'Quarter', 'Month', 'Day'].includes(cColId)) {
                                        c.classList.add('row-cell-selected');
                                        c.style.setProperty('background-color', '#b3d9ff', 'important');
                                        c.style.setProperty('font-weight', '600', 'important');
                                        c.style.setProperty('opacity', '1', 'important');
                                    }
                                    // Highlight the specific label cell that spans this group
                                    if (c === firstLabelCell) {
                                        c.classList.add('row-cell-selected');
                                        c.style.setProperty('background-color', '#b3d9ff', 'important');
                                        c.style.setProperty('font-weight', 'bold', 'important');
                                        c.style.setProperty('opacity', '1', 'important');
                                    }
                                });
                            });

                            // Dim other rows
                            allRows.forEach(r => {
                                if (!r.classList.contains('row-selected')) {
                                    r.querySelectorAll('td').forEach(c => c.style.setProperty('opacity', '0.3', 'important'));
                                }
                            });
                            clickedSpreadsheet.classList.add('row-selection-active');
                            window.priceScorecardState.selectedRowIndex = columnId + '_' + rowIndex + '_' + cellValue;
                            return;
                        }
                        
                        // If clicking on a data cell, clear column and row selections
                        const cell = event.target.closest('td[data-dash-column]');
                        if (cell) {
                            const columnId = cell.getAttribute('data-dash-column');
                            if (columnId && !['Year', 'Quarter', 'Month', 'Day'].includes(columnId)) {
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
                // Error handled silently
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('price-scorecard-dummy-output', 'children'),
        Input('price-scorecard-table-container', 'children'),
        prevent_initial_call=False
    )
