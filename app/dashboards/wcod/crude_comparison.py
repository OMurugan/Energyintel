from dash import dcc, html, Input, Output, dash_table, callback_context, State, ctx
import pandas as pd
import os
import dash
import re
import copy
from functools import lru_cache

from core.data_helpers import execute_query


# ------------------------------------------------------------------------------
# LOAD DATA FROM DATABASE
# ------------------------------------------------------------------------------
@lru_cache(maxsize=4)
def _load_crude_data_cached(mode):
    """
    Load crude oil data from database
    mode: 'production' or 'exports'
    Returns: (data_dict_list, columns_list)
    """
    
    # Build the query - using exact query provided by user
    query = f"""
    SELECT 
        A.country_name AS "Country",
        GRP.opec_grp AS "group",
        A.crude_name AS "CrudeOil",
        B.bsp_link AS "profile_url",
        A.yr AS "YearReported",
        A.production_kbpd AS "ProductionDataValue",
        A.exports_kbpd AS "ExportDataValue",
        A.api,
        A.sulfur_pct,
        A."tan_mg_koh/g",
        A.ports_terminals,
        A.classification,
        A.crude_alias,
        A.producers,
        A.sellers,
        A.ci_rank,
        A.external_comments,
        A.insert_by,
        A.insert_date,
        A.last_update_date,
        A.last_update_by,
        A.to_be_deleted
    FROM fact_wcod_crude A
    LEFT JOIN dim_country GRP 
        ON A.country_id = GRP.dim_country_id
    LEFT JOIN fact_wcod_crude_bsp_links B 
        ON A.crude_id = B.crude_id
    WHERE A.to_be_deleted IS NULL
    AND A.crude_name IS NOT NULL
    AND A.crude_name NOT LIKE 'Other Crudes%'
    """
    
    try:
        # Execute query
        results = execute_query(query)
        
        if not results:
            print(f"⚠️ No data found for {mode}. Returning empty data.")
            return [], []
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        # Filter based on mode and get the appropriate value column
        if mode == "production":
            value_col = "ProductionDataValue"
        else:  # exports
            value_col = "ExportDataValue"
        
        # Filter out rows where the value is null or zero for the selected mode
        df = df[df[value_col].notna() & (df[value_col] != 0)]
        
        if df.empty:
            print(f"⚠️ No {mode} data found. Returning empty data.")
            return [], []
        
        # Extract year from YearReported (handle both date and year formats)
        if 'YearReported' in df.columns:
            # Convert YearReported to year integer
            if pd.api.types.is_datetime64_any_dtype(df['YearReported']):
                df['Year'] = df['YearReported'].dt.year.astype(int)
            elif pd.api.types.is_object_dtype(df['YearReported']):
                # Try to extract year from date string or use as-is if already a year
                def extract_year(val):
                    if pd.isna(val):
                        return None
                    val_str = str(val)
                    # If it's a date string like "2010-01-01", extract year
                    if '-' in val_str and len(val_str) > 4:
                        try:
                            return int(val_str.split('-')[0])
                        except:
                            return None
                    # If it's already a year, convert to int
                    try:
                        return int(float(val_str))
                    except:
                        return None
                df['Year'] = df['YearReported'].apply(extract_year)
            else:
                # Already numeric, convert to int (handle float years like 2010.0)
                df['Year'] = df['YearReported'].fillna(0).astype(float).astype(int)
                # Replace 0 with NaN for invalid years
                df.loc[df['Year'] == 0, 'Year'] = None
        else:
            print(f"⚠️ YearReported column not found in results. Returning empty data.")
            return [], []
        
        # Remove rows where Year extraction failed
        df = df[df['Year'].notna() & (df['Year'] > 1900) & (df['Year'] < 2100)]
        
        if df.empty:
            print(f"⚠️ No valid year data found. Returning empty data.")
            return [], []
        
        # Get the full year range from the data
        min_year = int(df['Year'].min())
        max_year = int(df['Year'].max())
        all_years = list(range(min_year, max_year + 1))
        
        # Pivot the data: CrudeOil as rows, Year as columns
        # Use fill_value=None to keep NaN for missing values (we'll convert to empty strings later)
        pivot_df = df.pivot_table(
            index='CrudeOil',
            columns='Year',
            values=value_col,
            aggfunc='sum',  # In case there are duplicates
            fill_value=None  # Keep NaN for missing years
        )
        
        # Reset index to make CrudeOil a column
        pivot_df = pivot_df.reset_index()
        
        # Ensure all years in the range are present as columns
        # Add missing year columns with NaN values
        existing_year_cols = []
        for col in pivot_df.columns:
            if col != 'CrudeOil':
                # Handle MultiIndex columns (if any)
                if isinstance(col, tuple):
                    col_name = col[-1]  # Get the last element
                else:
                    col_name = col
                
                # Try to convert to int to verify it's a year
                try:
                    year_val = int(float(str(col_name)))
                    if 1900 <= year_val <= 2100:  # Valid year range
                        existing_year_cols.append(year_val)
                except (ValueError, TypeError):
                    # Not a year column, skip it
                    continue
        
        # Add missing year columns (years that exist in range but not in data)
        for year in all_years:
            if year not in existing_year_cols:
                pivot_df[year] = None  # Add as NaN/None
        
        # Get all year columns (now including all years in range)
        year_cols = []
        for col in pivot_df.columns:
            if col != 'CrudeOil':
                # Handle MultiIndex columns (if any)
                if isinstance(col, tuple):
                    col_name = col[-1]  # Get the last element
                else:
                    col_name = col
                
                # Try to convert to int to verify it's a year
                try:
                    year_val = int(float(str(col_name)))
                    if 1900 <= year_val <= 2100:  # Valid year range
                        year_cols.append((col, year_val))
                except (ValueError, TypeError):
                    # Not a year column, skip it
                    continue
        
        if not year_cols:
            print(f"⚠️ No valid year columns found after pivot. Columns: {list(pivot_df.columns)}. Returning empty data.")
            return [], []
        
        # Sort years in descending order (newest first)
        year_cols.sort(key=lambda x: x[1], reverse=True)
        
        # Extract column names (original column names from pivot)
        year_col_names = [col[0] for col in year_cols]
        
        # Reorder columns: CrudeOil first, then years in descending order
        pivot_df = pivot_df[['CrudeOil'] + year_col_names]
        
        # Rename year columns to strings for consistency
        rename_dict = {col[0]: str(col[1]) for col in year_cols}
        pivot_df = pivot_df.rename(columns=rename_dict)
        
        # Get the final sorted year column names as strings
        year_cols_sorted = [str(col[1]) for col in year_cols]
        
        # Format numeric values (remove decimals, add commas)
        # Show empty string for NaN, None, zero, or negative values
        for col in year_cols_sorted:
            if col in pivot_df.columns:
                pivot_df[col] = pivot_df[col].apply(
                    lambda x: (f"{float(x):,.0f}" if float(x) != 0 else "0") if pd.notna(x) else ""
                )
        
        # Convert CrudeOil to clickable URLs
        # Use profile_url (bsp_link) if available, otherwise construct from crude name
        def create_crude_link(crude_name, profile_url):
            if profile_url and pd.notna(profile_url) and str(profile_url).strip():
                # Use the actual profile_url from database
                return f"[{crude_name}]({profile_url})"
            else:
                # Construct URL from crude name
                crude_slug = str(crude_name).replace(' ', '-')
                return f"[{crude_name}](https://www.energyintel.com/wcod/crude-profile/{crude_slug})"
        
        # Get profile URLs mapping (use first available profile_url for each crude)
        profile_map = df.groupby('CrudeOil')['profile_url'].first().to_dict()
        
        pivot_df['CrudeOil'] = pivot_df['CrudeOil'].apply(
            lambda x: create_crude_link(x, profile_map.get(x, None))
        )
        
        # Convert to dict records
        data_records = pivot_df.to_dict('records')
        
        # Create columns definition
        columns = [
            {"name": c, "id": c, "presentation": "markdown"} if c == "CrudeOil" 
            else {"name": str(c), "id": str(c)} 
            for c in pivot_df.columns
        ]
        
        print(f"✅ Loaded {len(data_records)} records for {mode} from database")
        print(f"   Columns: {[c['name'] for c in columns]}")
        if data_records:
            print(f"   Sample record keys: {list(data_records[0].keys())[:5]}...")
        return data_records, tuple(columns)
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error loading {mode} data from database:")
        print(f"   {error_msg}")
        import traceback
        traceback.print_exc()
        print(f"\n⚠️ Returning empty data for {mode}. Please check database connection and configuration.")
        return tuple([]), tuple([])


def load_crude_data(mode):
    """
    Cached wrapper that defends against multiple initial calls triggering
    duplicate database hits. Returns deep copies so downstream callbacks
    can safely mutate data (sorting, etc.) without altering the cached
    baseline.
    """
    data_records, columns = _load_crude_data_cached(mode)
    return copy.deepcopy(list(data_records)), copy.deepcopy(list(columns))


def _columns_from_records(records):
    if not records:
        return []

    # Extract keys
    keys = list(records[0].keys())

    # Separate CrudeOil and year columns
    year_cols = []
    for k in keys:
        if k != "CrudeOil":
            try:
                year_cols.append(int(k))
            except ValueError:
                pass

    # Sort years descending
    year_cols = sorted(year_cols, reverse=True)
    year_cols = [str(y) for y in year_cols]

    # Final column order
    ordered_cols = ["CrudeOil"] + year_cols

    # Build Dash columns
    columns = []
    for col in ordered_cols:
        if col == "CrudeOil":
            columns.append({
                "name": col,
                "id": col,
                "presentation": "markdown"
            })
        else:
            columns.append({
                "name": col,
                "id": col
            })

    return columns


# ------------------------------------------------------------------------------
# SAMPLE DATA IF DATABASE QUERY FAILS
# ------------------------------------------------------------------------------
# def get_sample():
#     sample = [{"CrudeOil": "Sample Oil", "2024": 10, "2023": 8, "2022": 6}]
#     cols = [{"name": c, "id": c, "presentation": "markdown"} if c=="CrudeOil" else {"name": c, "id": c} for c in sample[0].keys()]
#     return sample, cols

# ------------------------------------------------------------------------------
# CALCULATE COMBINED SUM DATA (Production + Exports) - SORTED BY MAXIMUM VALUE DESC
# ------------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _calculate_combined_sums_cached():
    """Calculate combined sums of Production and Exports for each crude oil and year, sorted by maximum value descending"""
        
    # Query to get both production and exports data - using exact query format
    query = f"""
    SELECT 
        A.country_name AS "Country",
        GRP.opec_grp AS "group",
        A.crude_name AS "CrudeOil",
        B.bsp_link AS "profile_url",
        A.yr AS "YearReported",
        A.production_kbpd AS "ProductionDataValue",
        A.exports_kbpd AS "ExportDataValue",
        A.api,
        A.sulfur_pct,
        A."tan_mg_koh/g",
        A.ports_terminals,
        A.classification,
        A.crude_alias,
        A.producers,
        A.sellers,
        A.ci_rank,
        A.external_comments,
        A.insert_by,
        A.insert_date,
        A.last_update_date,
        A.last_update_by,
        A.to_be_deleted
    FROM fact_wcod_crude A
    LEFT JOIN dim_country GRP 
        ON A.country_id = GRP.dim_country_id
    LEFT JOIN fact_wcod_crude_bsp_links B 
        ON A.crude_id = B.crude_id
    WHERE A.to_be_deleted IS NULL
    AND A.crude_name IS NOT NULL
    AND (A.production_kbpd IS NOT NULL OR A.exports_kbpd IS NOT NULL)
    AND A.crude_name NOT LIKE 'Other Crudes%';
    """
    
    try:
        # Execute query
        results = execute_query(query)
        
        if not results:
            return []
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        # Extract year from YearReported (handle both date and year formats)
        if 'YearReported' in df.columns:
            # Convert YearReported to year integer
            if pd.api.types.is_datetime64_any_dtype(df['YearReported']):
                df['Year'] = df['YearReported'].dt.year.astype(int)
            elif pd.api.types.is_object_dtype(df['YearReported']):
                # Try to extract year from date string or use as-is if already a year
                def extract_year(val):
                    if pd.isna(val):
                        return None
                    val_str = str(val)
                    # If it's a date string like "2010-01-01", extract year
                    if '-' in val_str and len(val_str) > 4:
                        try:
                            return int(val_str.split('-')[0])
                        except:
                            return None
                    # If it's already a year, convert to int
                    try:
                        return int(float(val_str))
                    except:
                        return None
                df['Year'] = df['YearReported'].apply(extract_year)
            else:
                # Already numeric, convert to int (handle float years like 2010.0)
                df['Year'] = df['YearReported'].fillna(0).astype(float).astype(int)
                # Replace 0 with NaN for invalid years
                df.loc[df['Year'] == 0, 'Year'] = None
        else:
            print(f"⚠️ YearReported column not found in results")
            return []
        
        # Remove rows where Year extraction failed
        df = df[df['Year'].notna() & (df['Year'] > 1900) & (df['Year'] < 2100)]
        
        # Calculate combined value (Production + Exports) for each row
        df['CombinedValue'] = df['ProductionDataValue'].fillna(0) + df['ExportDataValue'].fillna(0)
        
        # Filter out rows where combined value is zero
        df = df[df['CombinedValue'] > 0]
        
        if df.empty:
            return []
        
        # Get the full year range from the data
        min_year = int(df['Year'].min())
        max_year = int(df['Year'].max())
        all_years = list(range(min_year, max_year + 1))
        
        # Pivot the data: CrudeOil as rows, Year as columns, CombinedValue as values
        # Use fill_value=None to keep NaN for missing values (we'll convert to empty strings later)
        pivot_df = df.pivot_table(
            index='CrudeOil',
            columns='Year',
            values='CombinedValue',
            aggfunc='sum',  # Sum if there are duplicates
            fill_value=None  # Keep NaN for missing years
        )
        
        # Reset index to make CrudeOil a column
        pivot_df = pivot_df.reset_index()
        
        # Ensure all years in the range are present as columns
        # Add missing year columns with NaN values
        existing_year_cols = []
        for col in pivot_df.columns:
            if col != 'CrudeOil':
                # Handle MultiIndex columns (if any)
                if isinstance(col, tuple):
                    col_name = col[-1]  # Get the last element
                else:
                    col_name = col
                
                # Try to convert to int to verify it's a year
                try:
                    year_val = int(float(str(col_name)))
                    if 1900 <= year_val <= 2100:  # Valid year range
                        existing_year_cols.append(year_val)
                except (ValueError, TypeError):
                    # Not a year column, skip it
                    continue
        
        # Add missing year columns (years that exist in range but not in data)
        for year in all_years:
            if year not in existing_year_cols:
                pivot_df[year] = None  # Add as NaN/None
        
        # Get all year columns (now including all years in range)
        year_cols = []
        for col in pivot_df.columns:
            if col != 'CrudeOil':
                # Handle MultiIndex columns (if any)
                if isinstance(col, tuple):
                    col_name = col[-1]  # Get the last element
                else:
                    col_name = col
                
                # Try to convert to int to verify it's a year
                try:
                    year_val = int(float(str(col_name)))
                    if 1900 <= year_val <= 2100:  # Valid year range
                        year_cols.append((col, year_val))
                except (ValueError, TypeError):
                    # Not a year column, skip it
                    continue
        
        if not year_cols:
            print(f"⚠️ No valid year columns found after pivot. Columns: {list(pivot_df.columns)}")
            return []
        
        # Sort years in descending order (newest first)
        year_cols.sort(key=lambda x: x[1], reverse=True)
        
        # Extract column names (original column names from pivot)
        year_col_names = [col[0] for col in year_cols]
        
        # Reorder columns: CrudeOil first, then years in descending order
        pivot_df = pivot_df[['CrudeOil'] + year_col_names]
        
        # Rename year columns to strings for consistency
        rename_dict = {col[0]: str(col[1]) for col in year_cols}
        pivot_df = pivot_df.rename(columns=rename_dict)
        
        # Get the final sorted year column names as strings
        year_cols_sorted = [str(col[1]) for col in year_cols]
        
        # Calculate maximum value for each row (for sorting)
        max_values = []
        for idx, row in pivot_df.iterrows():
            max_val = 0
            for col in year_cols_sorted:
                if col in pivot_df.columns:
                    val = row[col]
                    if pd.notna(val) and val > 0:
                        try:
                            val_float = float(val)
                            if val_float > max_val:
                                max_val = val_float
                        except (ValueError, TypeError):
                            pass
            max_values.append(max_val)
        
        pivot_df['_max_value'] = max_values
        
        # Sort by maximum value in descending order
        pivot_df = pivot_df.sort_values('_max_value', ascending=False)
        
        # Remove the temporary _max_value column
        pivot_df = pivot_df.drop('_max_value', axis=1)
        
        # Format numeric values (remove decimals, add commas)
        # Show empty string for NaN, None, zero, or negative values
        for col in year_cols_sorted:
            if col in pivot_df.columns:
                pivot_df[col] = pivot_df[col].apply(
                    lambda x: (f"{float(x):,.0f}" if float(x) != 0 else "0") if pd.notna(x) else ""
                )
        
        # Convert CrudeOil to clickable URLs
        profile_map = df.groupby('CrudeOil')['profile_url'].first().to_dict()
        
        def create_crude_link(crude_name, profile_url):
            if profile_url and pd.notna(profile_url) and str(profile_url).strip():
                # Use the actual profile_url from database
                return f"[{crude_name}]({profile_url})"
            else:
                # Construct URL from crude name
                crude_slug = str(crude_name).replace(' ', '-')
                return f"[{crude_name}](https://www.energyintel.com/wcod/crude-profile/{crude_slug})"
        
        pivot_df['CrudeOil'] = pivot_df['CrudeOil'].apply(
            lambda x: create_crude_link(x, profile_map.get(x, None))
        )
        
        # Convert to dict records
        combined_data = pivot_df.to_dict('records')
        
        print(f"✅ Calculated combined sums for {len(combined_data)} crude oils")
        return tuple(combined_data)
        
    except Exception as e:
        print(f"❌ Error calculating combined sums: {e}")
        import traceback
        traceback.print_exc()
        return tuple()


def calculate_combined_sums():
    """Return a cached deep copy to avoid repeated DB queries on initial load."""
    return copy.deepcopy(list(_calculate_combined_sums_cached()))

# ------------------------------------------------------------------------------
# CALCULATE SUM ROW FOR REGULAR DATA
# ------------------------------------------------------------------------------
def calculate_sum_row(data):
    """Calculate sum row for regular production/exports data"""
    if not data:
        return None
    
    df = pd.DataFrame(data)
    numeric_cols = [col for col in df.columns if col != 'CrudeOil']
    
    sum_row = {'CrudeOil': 'SUM'}
    
    for col in numeric_cols:
        col_sum = 0
        for val in df[col]:
            if val and str(val).strip() and str(val).strip() != '':
                try:
                    clean_val = str(val).replace(',', '')
                    col_sum += float(clean_val)
                except (ValueError, TypeError):
                    continue
        sum_row[col] = f"{col_sum:,.0f}"
    
    return sum_row

# ------------------------------------------------------------------------------
# SORT DATA BY MAXIMUM VALUE (For Field/Nested sorting)
# ------------------------------------------------------------------------------
def sort_by_maximum_value(data, direction='desc'):
    """Sort data by maximum value across all years"""
    if not data:
        return data
    
    df = pd.DataFrame(data)
    numeric_cols = [col for col in df.columns if col != 'CrudeOil']
    
    # Calculate maximum value for each row
    def get_max_value(row):
        max_val = 0
        for col in numeric_cols:
            val = row[col]
            if val and str(val).strip() and str(val).strip() != '':
                try:
                    clean_val = str(val).replace(',', '')
                    float_val = float(clean_val)
                    if float_val > max_val:
                        max_val = float_val
                except (ValueError, TypeError):
                    continue
        return max_val
    
    df['_max_value'] = df.apply(get_max_value, axis=1)
    
    # Sort by maximum value
    ascending = (direction == 'asc')
    df_sorted = df.sort_values('_max_value', ascending=ascending)
    df_sorted = df_sorted.drop('_max_value', axis=1)
    
    return df_sorted.to_dict('records')

# ------------------------------------------------------------------------------
# INITIAL LOAD - Lazy loading, only when page is accessed
# ------------------------------------------------------------------------------
production_data = []
production_columns = []

# ------------------------------------------------------------------------------
# LAYOUT
# ------------------------------------------------------------------------------
def create_layout(server):
    return html.Div(
        children=[
            html.Div([
                html.Label(
                    "Select Export/Production",
                    style={
                        "fontSize": "20px",
                        "color": "#d65a00",
                        "fontWeight": "bold",
                        "marginBottom": "10px",
                        "display": "block",
                        "fontFamily": "Arial",
                    }
                ),
                dcc.Dropdown(
                    id="export-production-dropdown",
                    options=[
                        {"label": "Production", "value": "production"},
                        {"label": "Exports", "value": "exports"},
                    ],
                    value="production",
                    clearable=False,
                    style={
                        "width": "100%",
                        "fontSize": "14px",
                        "fontFamily": "Arial",
                    }
                ),
            ], style={"marginBottom": "25px", "width": "100%"}),

            html.Div(id="crude-heading", style={"textAlign": "center"}),

            html.Hr(style={"margin": "10px 0", "border": "1px solid #ccc"}),

            # CSS for popup menu hover effects and tooltips
            dcc.Markdown("""
                <style>
                .popup-menu-item:hover {
                    background-color: #f5f5f5 !important;
                }
                #popup-field-btn:hover, #popup-nested-btn:hover {
                    background-color: #f5f5f5 !important;
                }
                .arrow-tooltip {
                    position: absolute;
                    background-color: #333;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                    font-family: Arial;
                    white-space: nowrap;
                    z-index: 1003;
                    pointer-events: none;
                }
                .sum-text-box {
                    position: absolute;
                    background-color: white;
                    border: 1px solid #ccc;
                    padding: 8px 12px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-family: Arial;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    z-index: 1002;
                    white-space: nowrap;
                    color: #333;
                }
                /* Sort indicator icon styles for ALL headers */
                .sort-indicator {
                    position: absolute;
                    right: 8px;
                    top: 50%;
                    transform: translateY(-50%);
                    width: 15px;
                    height: 15px;
                    cursor: pointer;
                    opacity: 0;
                    transition: opacity 0.2s ease;
                }
                .dash-header:hover .sort-indicator {
                    opacity: 1;
                }
                .sort-indicator:hover {
                    background-color: #e6f3ff;
                    border-radius: 2px;
                }
                .sort-indicator svg {
                    width: 100%;
                    height: 100%;
                    fill: #666;
                }
                .sort-indicator:hover svg {
                    fill: #1f3263;
                }
                /* Specific styles for CrudeOil header additional elements */
                .dash-header[data-dash-column="CrudeOil"] .sort-order-container {
                    position: absolute;
                    right: 30px;
                    top: 50%;
                    transform: translateY(-50%);
                    font-size: 10px;
                    color: #666;
                    cursor: pointer;
                    padding: 2px;
                    border: 1px solid transparent;
                    border-radius: 2px;
                    line-height: 1;
                    text-align: center;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 30px;
                    opacity: 0;
                    transition: opacity 0.2s ease;
                }
                .dash-header[data-dash-column="CrudeOil"]:hover .sort-order-container {
                    opacity: 1;
                }
                .dash-header[data-dash-column="CrudeOil"] .sort-order-container:hover {
                    background-color: #e6f3ff;
                    border-color: #1f3263;
                }
                .dash-header[data-dash-column="CrudeOil"] .sort-asc,
                .dash-header[data-dash-column="CrudeOil"] .sort-desc {
                    display: block;
                    line-height: 1;
                    cursor: pointer;
                    padding: 1px 2px;
                    border-radius: 1px;
                }
                .dash-header[data-dash-column="CrudeOil"] .sort-asc:hover,
                .dash-header[data-dash-column="CrudeOil"] .sort-desc:hover {
                    background-color: #d4e7ff;
                    font-weight: bold;
                }
                .dash-cell:not([data-dash-column="CrudeOil"]):not(.dash-header) {
                    cursor: pointer;
                }
                #sum-text-box {
                    cursor: pointer !important;
                }
                #sum-text-box:hover {
                    background-color: #f5f5f5 !important;
                    border-color: #999 !important;
                }
                </style>
            """, dangerously_allow_html=True),

            # SUM Text Box (initially hidden)
            html.Div(
                "SUM(Exports/Production Value)",
                id="sum-text-box",
                n_clicks=0,
                style={
                    "position": "absolute",
                    "backgroundColor": "white",
                    "border": "1px solid #ccc",
                    "padding": "8px 12px",
                    "borderRadius": "4px",
                    "fontSize": "12px",
                    "fontFamily": "Arial",
                    "boxShadow": "0 2px 5px rgba(0,0,0,0.1)",
                    "zIndex": "1002",
                    "display": "none",
                    "color": "#333",
                    "cursor": "pointer",
                }
            ),

            # Sorting controls popup (initially hidden)
            html.Div([
                html.Div([
                    html.Div("Data source order", id="popup-source-btn", 
                            style={
                                "padding": "6px 10px", 
                                "fontSize": "12px",
                                "cursor": "pointer",
                                "fontFamily": "Arial",
                                "color": "#333",
                            }, className="popup-menu-item"),
                    html.Div("Alphabetic", id="popup-alphabetic-btn",
                            style={
                                "padding": "6px 10px", 
                                "fontSize": "12px",
                                "cursor": "pointer",
                                "fontFamily": "Arial",
                                "color": "#333",
                            }, className="popup-menu-item"),
                    html.Div([
                        html.Span("Field", style={"flex": "1"}),
                        html.Span("▶", id="field-arrow-btn", style={
                            "cursor": "pointer",
                            "fontSize": "10px",
                            "color": "#666",
                            "marginLeft": "8px",
                        }),
                    ], id="popup-field-btn",
                       style={
                           "padding": "6px 10px", 
                           "fontSize": "12px",
                           "cursor": "pointer",
                           "fontFamily": "Arial",
                           "color": "#333",
                           "display": "flex",
                           "alignItems": "center",
                           "justifyContent": "space-between",
                           "position": "relative",
                       }),
                    html.Div([
                        html.Span("Nested", style={"flex": "1"}),
                        html.Span("▶", id="nested-arrow-btn", style={
                            "cursor": "pointer",
                            "fontSize": "10px",
                            "color": "#666",
                            "marginLeft": "8px",
                        }),
                    ], id="popup-nested-btn",
                       style={
                           "padding": "6px 10px", 
                           "fontSize": "12px",
                           "cursor": "pointer",
                           "fontFamily": "Arial",
                           "color": "333",
                           "display": "flex",
                           "alignItems": "center",
                           "justifyContent": "space-between",
                           "position": "relative",
                       }),
                ]),
            ], id="sorting-controls", style={
                "position": "absolute", 
                "backgroundColor": "white", 
                "padding": "15px",
                "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                "zIndex": "1000",
                "display": "none",
                "minWidth": "160px",
                "top": "213px",
                "left": "209px"
            }),
            
            html.Div([
                html.Div([
                    dcc.Dropdown(
                        id='crude-comparison-export-dropdown',
                        options=[
                            {'label': 'Export Data CSV', 'value': 'csv'}
                        ],
                        placeholder='Export Data',
                        style={
                            'width': '200px',
                            'fontSize': '13px',
                            'color': '#2c3e50',
                            'display': 'inline-block'
                        },
                        clearable=False
                    ),
                    dcc.Download(id="download-crude-comparison-csv"),
                ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'flex-end', 'marginBottom': '10px'}),
            ], style={'width': '100%'}),

            dcc.Loading(
                id="crude-comparison-table-loading",
                type="circle",
                children=[
                    dash_table.DataTable(
                        id="crude-comparison-table",
                        data=production_data,
                        columns=production_columns,
                        style_table={
                            "overflowX": "auto",
                            "overflowY": "auto",
                            "height": "1000px",
                            "maxHeight": "1000px",
                            "border": "1px solid #d9d9d9",
                            "backgroundColor": "white",
                            "position": "relative",
                        },
                        style_cell={
                            "textAlign": "center",
                            "padding": "8px 12px",
                            "fontSize": "11px",
                            "fontFamily": "Arial, sans-serif",
                            "border": "1px solid #e0e0e0",
                            "whiteSpace": "normal",
                            "height": "auto",
                            "minHeight": "35px",
                            "color": "#333333",
                        },
                        style_header={
                            "backgroundColor": "#f2f2f2",
                            "fontWeight": "bold",
                            "fontSize": "14px",
                            "fontFamily": "Arial, sans-serif",
                            "border": "1px solid #d0d0d0",
                            "color": "#1f3263",
                            "textAlign": "center",
                            "padding": "10px 12px",
                            "position": "relative",
                        },
                        style_cell_conditional=[
                            {
                                "if": {"column_id": "CrudeOil"},
                                "textAlign": "left",
                                "fontWeight": "600",
                                "minWidth": "180px",
                                "backgroundColor": "#FFFFFF",
                                "borderRight": "1px solid #d0d0d0",
                                "paddingLeft": "12px",
                                "paddingRight": "12px",
                                "color": "#1f3263",
                                "cursor": "pointer",
                            },
                            {
                                "if": {"column_id": "CrudeOil", "header": True},
                                "textAlign": "left",
                                "color": "#1f3263",
                                "position": "relative",
                            },
                            # Year column headers - dark blue, center-aligned
                            {
                                "if": {"header": True, "column_id": [str(year) for year in range(2007, 2025)]},
                                "color": "#1f3263",
                                "textAlign": "center",
                            },
                        ],
                        style_data_conditional=[
                            # All data rows white background
                            {
                                "if": {"row_index": "odd"},
                                "backgroundColor": "#FFFFFF",
                            },
                            {
                                "if": {"row_index": "even"},
                                "backgroundColor": "#FFFFFF",
                            },
                            # CrudeOil column data - dark blue
                            {
                                "if": {"column_id": "CrudeOil"},
                                "color": "#1f3263",
                                "backgroundColor": "#FFFFFF",
                            },
                            # Year columns data - dark gray/black, center-aligned
                            {
                                "if": {"column_id": [str(year) for year in range(2007, 2025)]},
                                "color": "#333333",
                                "textAlign": "center",
                            },
                        ],
                        css=[
                            {
                                'selector': '.dash-cell[data-dash-column="CrudeOil"]',
                                'rule': '''
                                    cursor: pointer !important;
                                '''
                            },
                            {
                                'selector': '.dash-cell[data-dash-column="CrudeOil"] a',
                                'rule': '''
                                    color: #1f3263 !important; 
                                    text-decoration: underline !important;
                                    font-weight: 600 !important;
                                    font-family: Arial, sans-serif !important;
                                    cursor: pointer !important;
                                '''
                            },
                            {
                                'selector': '.dash-cell[data-dash-column="CrudeOil"] a:hover',
                                'rule': '''
                                    color: #1f3263 !important; 
                                    text-decoration: underline !important;
                                '''
                            },
                            {
                                'selector': '.dash-header[data-dash-column="CrudeOil"]',
                                'rule': '''
                                    color: #1f3263 !important;
                                    position: relative !important;
                                    text-align: left !important;
                                '''
                            },
                            # Year column headers styling
                            {
                                'selector': '.dash-header[data-dash-column*="20"]',
                                'rule': '''
                                    color: #1f3263 !important;
                                    text-align: center !important;
                                    font-weight: bold !important;
                                '''
                            },
                            # Table borders - horizontal lines for rows
                            {
                                'selector': '.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner table',
                                'rule': '''
                                    border-collapse: collapse !important;
                                '''
                            },
                            {
                                'selector': '.dash-cell',
                                'rule': '''
                                    border-top: 1px solid #e0e0e0 !important;
                                    border-bottom: 1px solid #e0e0e0 !important;
                                '''
                            },
                            {
                                'selector': '.dash-header',
                                'rule': '''
                                    border-left: 1px solid #d0d0d0 !important;
                                    border-right: 1px solid #d0d0d0 !important;
                                '''
                            },
                            # A-Z vertical text for sort order - HIDDEN BY DEFAULT
                            {
                                'selector': '.dash-header[data-dash-column="CrudeOil"] .sort-order-container',
                                'rule': '''
                                    position: absolute;
                                    right: 30px;
                                    top: 50%;
                                    transform: translateY(-50%);
                                    font-size: 10px;
                                    color: #666;
                                    cursor: pointer;
                                    padding: 2px;
                                    border: 1px solid transparent;
                                    border-radius: 2px;
                                    line-height: 1;
                                    text-align: center;
                                    display: flex;
                                    flex-direction: column;
                                    align-items: center;
                                    justify-content: center;
                                    height: 30px;
                                    opacity: 0;
                                    transition: opacity 0.2s ease;
                                '''
                            },
                            {
                                'selector': '.dash-header[data-dash-column="CrudeOil"]:hover .sort-order-container',
                                'rule': '''
                                    opacity: 1;
                                '''
                            },
                            {
                                'selector': '.dash-header[data-dash-column="CrudeOil"] .sort-order-container:hover',
                                'rule': '''
                                    background-color: #e6f3ff;
                                    border-color: #1f3263;
                                '''
                            },
                            {
                                'selector': '.dash-header[data-dash-column="CrudeOil"] .sort-asc',
                                'rule': '''
                                    display: block;
                                    line-height: 1;
                                    cursor: pointer;
                                    padding: 1px 2px;
                                    border-radius: 1px;
                                '''
                            },
                            {
                                'selector': '.dash-header[data-dash-column="CrudeOil"] .sort-asc:hover',
                                'rule': '''
                                    background-color: #d4e7ff;
                                    font-weight: bold;
                                '''
                            },
                            {
                                'selector': '.dash-header[data-dash-column="CrudeOil"] .sort-desc',
                                'rule': '''
                                    display: block;
                                    line-height: 1;
                                    cursor: pointer;
                                    padding: 1px 2px;
                                    border-radius: 1px;
                                '''
                            },
                            {
                                'selector': '.dash-header[data-dash-column="CrudeOil"] .sort-desc:hover',
                                'rule': '''
                                    background-color: #d4e7ff;
                                    font-weight: bold;
                                '''
                            },
                            # Sort indicator (SVG icon) for ALL headers - HIDDEN BY DEFAULT
                            {
                                'selector': '.dash-header .sort-indicator',
                                'rule': '''
                                    position: absolute;
                                    right: 8px;
                                    top: 50%;
                                    transform: translateY(-50%);
                                    width: 15px;
                                    height: 15px;
                                    cursor: pointer;
                                    opacity: 0;
                                    transition: opacity 0.2s ease;
                                '''
                            },
                            {
                                'selector': '.dash-header:hover .sort-indicator',
                                'rule': '''
                                    opacity: 1;
                                '''
                            },
                            {
                                'selector': '.dash-header .sort-indicator:hover',
                                'rule': '''
                                    background-color: #e6f3ff;
                                    border-radius: 2px;
                                '''
                            },
                            {
                                'selector': '.dash-cell:not([data-dash-column="CrudeOil"]):not(.dash-header)',
                                'rule': 'cursor: pointer;'
                            },
                            # SUM text box styling
                            {
                                'selector': '#sum-text-box',
                                'rule': 'cursor: pointer !important;'
                            },
                            {
                                'selector': '#sum-text-box:hover',
                                'rule': 'background-color: #f5f5f5 !important; border-color: #999 !important;'
                            },
                        ],
                        fixed_rows={"headers": True},
                        page_action="none",
                        sort_action="none",
                        filter_action="none",
                        markdown_options={"html": True, "link_target": "_blank"},
                    ),
                ]
            ),

            # Store components
            dcc.Store(id='external-url-store'),
            dcc.Store(id='selected-cell-store', data=None),
            dcc.Store(id='original-data-store', data=production_data),
            dcc.Store(id='current-sort-order', data={'type': 'source', 'direction': 'asc'}),
            dcc.Store(id='show-sorting-controls', data=False),
            dcc.Store(id='is-combined-mode', data=False),  # Track if we're in combined mode
            html.Div(id='dummy-output', style={'display': 'none'}),
            html.Div(id='dummy-output-2', style={'display': 'none'}),

            # Hidden buttons for header interactions
            html.Button("Sort Ascending Click", id="sort-asc-btn-hidden", n_clicks=0, style={"display": "none"}),
            html.Button("Sort Descending Click", id="sort-desc-btn-hidden", n_clicks=0, style={"display": "none"}),
            html.Button("Popup Menu Click", id="popup-menu-btn", n_clicks=0, style={"display": "none"}),
            # Hidden buttons for year column sorting and combined mode
            html.Button("Year Column Click", id="year-column-btn", n_clicks=0, style={"display": "none"}),
            html.Button("Field Sort Click", id="field-sort-btn", n_clicks=0, style={"display": "none"}),
            html.Button("Nested Sort Click", id="nested-sort-btn", n_clicks=0, style={"display": "none"}),

            html.Div([
                html.P(
                    "Data source: Energy Intelligence",
                    style={
                        "fontSize": "11px",
                        "fontStyle": "italic",
                        "color": "#777",
                        "textAlign": "right",
                        "marginTop": "8px",
                        "fontFamily": "Arial",
                    },
                )
            ]),
        ],
        style={
            "height": "auto",
            "overflowY": "auto",
            "padding": "25px",
            "backgroundColor": "white",
            "maxWidth": "1500px",
            "margin": "0 auto",
            "position": "relative",
        },
        id="main-container"
    )

# ------------------------------------------------------------------------------
# CALLBACKS
# ------------------------------------------------------------------------------
def register_callbacks(app, server):

    @app.callback(
        Output("crude-heading", "children"),
        [Input("export-production-dropdown", "value"),
         Input("is-combined-mode", "data")]
    )
    def update_header(selected, is_combined):
        if is_combined:
            title = "Production('000 b/d)"
        elif selected == "exports":
            title = "Exports ('000 b/d)"
        else:  # production
            title = "Production ('000 b/d)"
        
        return html.H2(
            title,
            style={
                "color": "#d65a00",
                "fontSize": "22px",
                "fontWeight": "bold",
                "fontFamily": "Arial",
                "marginBottom": "10px",
                "textAlign": "center",
            },
        )

    @app.callback(
        [Output("crude-comparison-table", "data"),
         Output("original-data-store", "data"),
         Output("is-combined-mode", "data")],
        [Input("export-production-dropdown", "value"),
         Input("sum-text-box", "n_clicks"),
         Input("year-column-btn", "n_clicks")],
        [State("is-combined-mode", "data")]
    )
    def reload_data(mode, sum_text_clicks, year_clicks, is_combined):
        trigger = ctx.triggered_id
        
        # SUM text box OR Year icon click switches to combined mode
        if trigger in ['sum-text-box', 'year-column-btn']:
            # Use combined data
            combined_data = calculate_combined_sums()
            return combined_data, combined_data, True
        else:
            # Use individual dataset (Production or Exports) - NO sum row
            crude_data, columns = load_crude_data(mode)
            return crude_data, crude_data, False

    @app.callback(
        Output("crude-comparison-table", "columns"),
        [
            Input("original-data-store", "data"),
            Input("export-production-dropdown", "value"),
        ],
    )
    def reload_columns(original_data, mode):
        if original_data:
            return _columns_from_records(original_data)
        _, columns = load_crude_data(mode)
        return columns

    # Handle SUM text box display
    @app.callback(
        Output('sum-text-box', 'style'),
        [Input('popup-field-btn', 'n_clicks'),
         Input('popup-nested-btn', 'n_clicks'),
         Input('field-arrow-btn', 'n_clicks'),
         Input('nested-arrow-btn', 'n_clicks')],
        [State('show-sorting-controls', 'data')]
    )
    def handle_sum_text_box(field_clicks, nested_clicks, field_arrow_clicks, nested_arrow_clicks, show_controls):
        trigger = ctx.triggered_id
        
        # Show SUM text box when hovering over Field/Nested arrows
        if trigger in ['popup-field-btn', 'popup-nested-btn', 'field-arrow-btn', 'nested-arrow-btn']:
            if show_controls:
                return {
                    "position": "absolute",
                    "backgroundColor": "white",
                    "border": "1px solid #ccc",
                    "padding": "8px 12px",
                    "borderRadius": "4px",
                    "fontSize": "12px",
                    "fontFamily": "Arial",
                    "boxShadow": "0 2px 5px rgba(0,0,0,0.1)",
                    "zIndex": "1002",
                    "display": "block",
                    "color": "#333",
                    "top": "286px",
                    "left": "353px"
                }
        
        return {
            "position": "absolute",
            "backgroundColor": "white",
            "border": "1px solid #ccc",
            "padding": "8px 12px",
            "borderRadius": "4px",
            "fontSize": "12px",
            "fontFamily": "Arial",
            "boxShadow": "0 2px 5px rgba(0,0,0,0.1)",
            "zIndex": "1002",
            "display": "none",
            "color": "#333",
        }

    # Handle header clicks (both sort order and popup menu)
    @app.callback(
        [Output('sorting-controls', 'style'),
         Output('show-sorting-controls', 'data'),
         Output('current-sort-order', 'data', allow_duplicate=True),
         Output('sum-text-box', 'style', allow_duplicate=True)],
        [Input('sort-asc-btn-hidden', 'n_clicks'),
         Input('sort-desc-btn-hidden', 'n_clicks'),
         Input('popup-menu-btn', 'n_clicks'),
         Input('popup-source-btn', 'n_clicks'),
         Input('popup-alphabetic-btn', 'n_clicks'),
         Input('popup-field-btn', 'n_clicks'),
         Input('popup-nested-btn', 'n_clicks'),
         Input('field-sort-btn', 'n_clicks'),
         Input('nested-sort-btn', 'n_clicks'),
         Input('sum-text-box', 'n_clicks'),
         Input('year-column-btn', 'n_clicks')],
        [State('show-sorting-controls', 'data'),
         State('current-sort-order', 'data')],
        prevent_initial_call=True
    )
    def handle_header_interactions(asc_clicks, desc_clicks, popup_clicks, 
                                  popup_source_clicks, popup_alpha_clicks,
                                  popup_field_clicks, popup_nested_clicks,
                                  field_sort_clicks, nested_sort_clicks,
                                  sum_text_clicks, year_clicks,
                                  show_controls, current_sort):
        trigger = ctx.triggered_id
        
        if trigger == 'sort-asc-btn-hidden':
            return dash.no_update, dash.no_update, {'type': 'alphabetic', 'direction': 'asc'}, dash.no_update
        
        elif trigger == 'sort-desc-btn-hidden':
            return dash.no_update, dash.no_update, {'type': 'alphabetic', 'direction': 'desc'}, dash.no_update
        
        elif trigger == 'popup-menu-btn':
            return {
                "position": "absolute", 
                "backgroundColor": "white", 
                "padding": "15px",
                "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                "zIndex": "1000",
                "display": "block",
                "minWidth": "160px",
                "top": "213px",
                "left": "209px"
            }, True, dash.no_update, dash.no_update
        
        elif trigger == 'popup-source-btn':
            return {
                "position": "absolute", 
                "backgroundColor": "white", 
                "padding": "4px 0",
                "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                "zIndex": "1000",
                "display": "none",
                "minWidth": "160px"
            }, False, {'type': 'source', 'direction': current_sort.get('direction', 'asc') if current_sort else 'asc'}, {
                "position": "absolute",
                "backgroundColor": "white",
                "border": "1px solid #ccc",
                "padding": "8px 12px",
                "borderRadius": "4px",
                "fontSize": "12px",
                "fontFamily": "Arial",
                "boxShadow": "0 2px 5px rgba(0,0,0,0.1)",
                "zIndex": "1002",
                "display": "none",
                "color": "#333",
            }
        
        elif trigger == 'popup-alphabetic-btn':
            return {
                "position": "absolute", 
                "backgroundColor": "white", 
                "padding": "4px 0",
                "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                "zIndex": "1000",
                "display": "none",
                "minWidth": "160px"
            }, False, {'type': 'alphabetic', 'direction': current_sort.get('direction', 'asc') if current_sort else 'asc'}, {
                "position": "absolute",
                "backgroundColor": "white",
                "border": "1px solid #ccc",
                "padding": "8px 12px",
                "borderRadius": "4px",
                "fontSize": "12px",
                "fontFamily": "Arial",
                "boxShadow": "0 2px 5px rgba(0,0,0,0.1)",
                "zIndex": "1002",
                "display": "none",
                "color": "#333",
            }
        
        elif trigger == 'popup-field-btn' or trigger == 'field-sort-btn':
            # Show SUM text box but keep popup open for Field menu item
            return dash.no_update, dash.no_update, {'type': 'field', 'direction': current_sort.get('direction', 'asc') if current_sort else 'asc'}, {
                "position": "absolute",
                "backgroundColor": "white",
                "border": "1px solid #ccc",
                "padding": "8px 12px",
                "borderRadius": "4px",
                "fontSize": "12px",
                "fontFamily": "Arial",
                "boxShadow": "0 2px 5px rgba(0,0,0,0.1)",
                "zIndex": "1002",
                "display": "block",
                "color": "#333",
                "top": "286px",
                "left": "353px"
            }
        
        elif trigger == 'popup-nested-btn' or trigger == 'nested-sort-btn':
            # Show SUM text box but keep popup open for Nested menu item
            return dash.no_update, dash.no_update, {'type': 'nested', 'direction': current_sort.get('direction', 'asc') if current_sort else 'asc'}, {
                "position": "absolute",
                "backgroundColor": "white",
                "border": "1px solid #ccc",
                "padding": "8px 12px",
                "borderRadius": "4px",
                "fontSize": "12px",
                "fontFamily": "Arial",
                "boxShadow": "0 2px 5px rgba(0,0,0,0.1)",
                "zIndex": "1002",
                "display": "block",
                "color": "#333",
                "top": "316px",
                "left": "351px"
            }
        
        elif trigger == 'sum-text-box' or trigger == 'year-column-btn':
            # When SUM text box OR Year icon is clicked, close popup and show combined data with maximum value sorting
            return {
                "position": "absolute", 
                "backgroundColor": "white", 
                "padding": "4px 0",
                "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
                "zIndex": "1000",
                "display": "none",
                "minWidth": "160px"
            }, False, {'type': 'field', 'direction': 'desc'}, {
                "position": "absolute",
                "backgroundColor": "white",
                "border": "1px solid #ccc",
                "padding": "8px 12px",
                "borderRadius": "4px",
                "fontSize": "12px",
                "fontFamily": "Arial",
                "boxShadow": "0 2px 5px rgba(0,0,0,0.1)",
                "zIndex": "1002",
                "display": "none",
                "color": "#333",
            }
        
        return {
            "position": "absolute", 
            "backgroundColor": "white", 
            "padding": "4px 0",
            "boxShadow": "0 2px 10px rgba(0,0,0,0.1)",
            "zIndex": "1000",
            "display": "none",
            "minWidth": "160px"
        }, False, dash.no_update, {
            "position": "absolute",
            "backgroundColor": "white",
            "border": "1px solid #ccc",
            "padding": "8px 12px",
            "borderRadius": "4px",
            "fontSize": "12px",
            "fontFamily": "Arial",
            "boxShadow": "0 2px 5px rgba(0,0,0,0.1)",
            "zIndex": "1002",
            "display": "none",
            "color": "#333",
        }

    # Apply sorting when sort order changes - UPDATED FOR MAXIMUM VALUE SORTING
    @app.callback(
        [Output('crude-comparison-table', 'data', allow_duplicate=True),
         Output('current-sort-order', 'data', allow_duplicate=True)],
        [Input('current-sort-order', 'data')],
        [State('original-data-store', 'data'),
         State('export-production-dropdown', 'value'),
         State('is-combined-mode', 'data')],
        prevent_initial_call=True
    )
    def apply_sort_order(current_sort, original_data, mode, is_combined):
        if not original_data or not current_sort:
            return dash.no_update, dash.no_update
            
        sort_type = current_sort.get('type', 'alphabetic')
        direction = current_sort.get('direction', 'asc')
        
        # If we're in combined mode, use the combined data directly
        if is_combined:
            combined_data = calculate_combined_sums()
            return combined_data, dash.no_update
            
        # Convert back to DataFrame for sorting
        df = pd.DataFrame(original_data)
        
        if sort_type == 'alphabetic':
            df_sorted = df.sort_values('CrudeOil', ascending=(direction == 'asc'), na_position='last')
        elif sort_type in ['field', 'nested']:
            # Use maximum value sorting for Field and Nested
            df_sorted_data = sort_by_maximum_value(original_data, direction)
            df_sorted = pd.DataFrame(df_sorted_data)
        else:
            df_sorted = df
        
        # Convert back to dict (no SUM row)
        sorted_data = df_sorted.to_dict('records')
        
        return sorted_data, dash.no_update

    # Handle sorting from popup menu text options - UPDATED FOR MAXIMUM VALUE SORTING
    @app.callback(
        [Output('crude-comparison-table', 'data', allow_duplicate=True),
         Output('current-sort-order', 'data', allow_duplicate=True)],
        [Input('popup-source-btn', 'n_clicks'),
         Input('popup-alphabetic-btn', 'n_clicks'),
         Input('popup-field-btn', 'n_clicks'),
         Input('popup-nested-btn', 'n_clicks')],
        [State('original-data-store', 'data'),
         State('current-sort-order', 'data'),
         State('export-production-dropdown', 'value'),
         State('is-combined-mode', 'data')],
        prevent_initial_call=True
    )
    def handle_popup_sorting(popup_source_clicks, popup_alpha_clicks,
                           popup_field_clicks, popup_nested_clicks,
                           original_data, current_sort, mode, is_combined):
        if not original_data:
            return dash.no_update, dash.no_update
            
        trigger = ctx.triggered_id
        
        if trigger == 'popup-source-btn':
            sort_type = 'source'
        elif trigger == 'popup-alphabetic-btn':
            sort_type = 'alphabetic'
        elif trigger == 'popup-field-btn':
            sort_type = 'field'
        elif trigger == 'popup-nested-btn':
            sort_type = 'nested'
        else:
            return dash.no_update, dash.no_update
        
        direction = current_sort.get('direction', 'asc')
        
        # If we're in combined mode, use the combined data directly
        if is_combined:
            combined_data = calculate_combined_sums()
            return combined_data, {'type': sort_type, 'direction': direction}
            
        df = pd.DataFrame(original_data)
        
        if sort_type == 'alphabetic':
            df_sorted = df.sort_values('CrudeOil', ascending=(direction == 'asc'), na_position='last')
        elif sort_type in ['field', 'nested']:
            # Use maximum value sorting for Field and Nested
            sorted_data = sort_by_maximum_value(original_data, direction)
            df_sorted = pd.DataFrame(sorted_data)
        else:
            df_sorted = df
        
        sorted_data = df_sorted.to_dict('records')
        
        return sorted_data, {'type': sort_type, 'direction': direction}

    @app.callback(
        [Output('external-url-store', 'data'),
         Output('selected-cell-store', 'data')],
        Input('crude-comparison-table', 'active_cell'),
        [State('crude-comparison-table', 'data'),
         State('selected-cell-store', 'data')],
        prevent_initial_call=True
    )
    def handle_cell_click(active_cell, data, previous_selected):
        if active_cell and data:
            row = active_cell['row']
            column = active_cell['column_id']
            
            if row is not None and row < len(data):
                crude_markdown = data[row].get('CrudeOil', '')
                url_match = re.search(r'\[.*?\]\((.*?)\)', crude_markdown)
                
                if url_match:
                    external_url = url_match.group(1)
                    
                    if column == "CrudeOil":
                        # Click on CrudeOil column - highlight entire row
                        selected_cell = {
                            'row': row,
                            'column': 'row',  # Special marker for row highlighting
                            'value': None
                        }
                        return external_url, selected_cell
                    else:
                        # Click on value column - highlight specific cell
                        cell_value = data[row].get(column)
                        if cell_value and str(cell_value).strip():
                            selected_cell = {
                                'row': row,
                                'column': column,
                                'value': cell_value
                            }
                            return external_url, selected_cell
        
        raise dash.exceptions.PreventUpdate

    @app.callback(
        Output('crude-comparison-table', 'style_data_conditional'),
        [Input('selected-cell-store', 'data'),
         Input('is-combined-mode', 'data')],
        [State('crude-comparison-table', 'data')]
    )
    def update_table_styles(selected_cell, is_combined, current_data):
        default_styles = [
            {"if": {"row_index": "odd"}, "backgroundColor": "#f9f9f9"},
            {"if": {"column_id": "CrudeOil"}, "color": "#1f3263"},
            {"if": {"column_id": [str(year) for year in range(2007, 2025)]}, "cursor": "pointer"},
        ]
    
        if selected_cell and current_data:
            numeric_columns = [col for col in (current_data[0].keys() if current_data else []) if col != "CrudeOil"]
            selected_row = selected_cell['row']
            selected_col = selected_cell['column']
            
            # Check if it's a row highlight (CrudeOil click) or cell highlight (value click)
            if selected_col == 'row':
                # Highlight entire row - like fig1 (light blue background)
                style_conditions = [
                    # Dim all other rows
                    {"if": {"row_index": "odd"}, "backgroundColor": "#f5f5f5", "opacity": "0.5"},
                    {"if": {"row_index": "even"}, "backgroundColor": "#ffffff", "opacity": "0.5"},
                    # Highlight the selected row
                    {"if": {"row_index": selected_row}, "backgroundColor": "#e6f3ff", "opacity": "1", "fontWeight": "600"},
                    # CrudeOil column styling
                    {"if": {"column_id": "CrudeOil"}, "color": "#1f3263", "cursor": "pointer"},
                    {"if": {"column_id": "CrudeOil", "row_index": selected_row}, "color": "#1f3263", "backgroundColor": "#e6f3ff", "fontWeight": "600"},
                    # Year columns styling
                    {"if": {"column_id": numeric_columns}, "cursor": "pointer"},
                    {"if": {"column_id": numeric_columns, "row_index": selected_row}, "color": "#1f3263", "backgroundColor": "#e6f3ff", "fontWeight": "600"},
                ]
            else:
                # Highlight specific cell and dim others
                style_conditions = [
                    # Dim all cells
                    {"if": {"row_index": "odd"}, "backgroundColor": "#f5f5f5", "opacity": "0.4"},
                    {"if": {"row_index": "even"}, "backgroundColor": "#ffffff", "opacity": "0.4"},
                    # Highlight the selected cell
                    {"if": {"row_index": selected_row, "column_id": selected_col}, 
                     "color": "#1f3263", 
                     "backgroundColor": "#e6f3ff", 
                     "fontWeight": "bold", 
                     "border": "2px solid #1f3263", 
                     "opacity": "1",
                     "cursor": "pointer"},
                    # Keep CrudeOil column visible but dimmed
                    {"if": {"column_id": "CrudeOil"}, "color": "#1f3263", "cursor": "pointer", "opacity": "0.6"},
                    {"if": {"column_id": "CrudeOil", "row_index": selected_row}, "color": "#1f3263", "opacity": "0.8"},
                    # Dim other year columns
                    {"if": {"column_id": numeric_columns}, "cursor": "pointer", "opacity": "0.4"},
                ]
                
            return style_conditions
        
        return default_styles

    # Client-side callback to open the external URL in a new tab
    app.clientside_callback(
        """
        function(url) {
            if (url && url !== '') {
                window.open(url, '_blank');
            }
            return '';
        }
        """,
        Output('dummy-output', 'children'),
        Input('external-url-store', 'data')
    )
    

    # Add custom CSS for the header elements and tooltips
    app.clientside_callback(
        """
        function(n) {
            setTimeout(function() {
                // Add A/Z and SVG sort icon to CrudeOil header
                const crudeHeader = document.querySelector('.dash-header[data-dash-column="CrudeOil"]');
                if (crudeHeader && !crudeHeader.querySelector('.sort-order-container')) {
                    const sortContainer = document.createElement('div');
                    sortContainer.className = 'sort-order-container';
                    
                    const aElement = document.createElement('div');
                    aElement.className = 'sort-asc';
                    aElement.textContent = 'A';
                    aElement.title = 'Click for ascending alphabetical order';
                    aElement.onclick = function(e) {
                        e.stopPropagation();
                        const btn = document.getElementById('sort-asc-btn-hidden');
                        if (btn) btn.click();
                    };
                    
                    const zElement = document.createElement('div');
                    zElement.className = 'sort-desc';
                    zElement.textContent = 'Z';
                    zElement.title = 'Click for descending alphabetical order';
                    zElement.onclick = function(e) {
                        e.stopPropagation();
                        const btn = document.getElementById('sort-desc-btn-hidden');
                        if (btn) btn.click();
                    };
                    
                    sortContainer.appendChild(aElement);
                    sortContainer.appendChild(zElement);
                    
                    // Add SVG sort icon (same as year columns)
                    const sortIndicator = document.createElement('div');
                    sortIndicator.className = 'sort-indicator';
                    sortIndicator.title = 'Click to show sort options';
                    
                    // Add the exact SVG from your file
                    sortIndicator.innerHTML = `
                        <svg fill="#000000" viewBox="0 0 301.219 301.219" xmlns="http://www.w3.org/2000/svg">
                            <g>
                                <path d="M159.365,23.736v-10c0-5.523-4.477-10-10-10H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h139.365
                                    C154.888,33.736,159.365,29.259,159.365,23.736z"/>
                                <path d="M130.586,66.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h120.586c5.523,0,10-4.477,10-10v-10
                                    C140.586,71.213,136.109,66.736,130.586,66.736z"/>
                                <path d="M111.805,129.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h101.805c5.523,0,10-4.477,10-10v-10
                                    C121.805,134.213,117.328,129.736,111.805,129.736z"/>
                                <path d="M93.025,199.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h83.025c5.522,0,10-4.477,10-10v-10
                                    C103.025,204.213,98.548,199.736,93.025,199.736z"/>
                                <path d="M74.244,262.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h64.244c5.522,0,10-4.477,10-10v-10
                                    C84.244,267.213,79.767,262.736,74.244,262.736z"/>
                                <path d="M298.29,216.877l-7.071-7.071c-1.875-1.875-4.419-2.929-7.071-2.929c-2.652,0-5.196,1.054-7.072,2.929l-34.393,34.393
                                    V18.736c0-5.523-4.477-10-10-10h-10c-5.523,0-10,4.477-10,10v225.462l-34.393-34.393c-1.876-1.875-4.419-2.929-7.071-2.929
                                    c-2.652,0-5.196,1.054-7.071,2.929l-7.072,7.071c-3.904,3.905-3.904,10.237,0,14.142l63.536,63.536
                                    c1.953,1.953,4.512,2.929,7.071,2.929c2.559,0,5.119-0.976,7.071-2.929l63.536-63.536
                                    C302.195,227.113,302.195,220.781,298.29,216.877z"/>
                            </g>
                        </svg>
                    `;
                    
                    sortIndicator.onclick = function(e) {
                        e.stopPropagation();
                        const btn = document.getElementById('popup-menu-btn');
                        if (btn) btn.click();
                    };
                    
                    crudeHeader.appendChild(sortContainer);
                    crudeHeader.appendChild(sortIndicator);
                }
                
                // Add SVG sort icons to ALL year columns (2024, 2023, etc.)
                const yearHeaders = document.querySelectorAll('.dash-header:not([data-dash-column="CrudeOil"])');
                yearHeaders.forEach(header => {
                    if (!header.querySelector('.sort-indicator')) {
                        const sortIndicator = document.createElement('div');
                        sortIndicator.className = 'sort-indicator';
                        sortIndicator.title = 'Click to sort by maximum value (Production + Exports)';
                        
                        // Add the exact SVG from your file
                        sortIndicator.innerHTML = `
                            <svg fill="#000000" viewBox="0 0 301.219 301.219" xmlns="http://www.w3.org/2000/svg">
                                <g>
                                    <path d="M159.365,23.736v-10c0-5.523-4.477-10-10-10H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h139.365
                                        C154.888,33.736,159.365,29.259,159.365,23.736z"/>
                                    <path d="M130.586,66.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h120.586c5.523,0,10-4.477,10-10v-10
                                        C140.586,71.213,136.109,66.736,130.586,66.736z"/>
                                    <path d="M111.805,129.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h101.805c5.523,0,10-4.477,10-10v-10
                                        C121.805,134.213,117.328,129.736,111.805,129.736z"/>
                                    <path d="M93.025,199.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h83.025c5.522,0,10-4.477,10-10v-10
                                        C103.025,204.213,98.548,199.736,93.025,199.736z"/>
                                    <path d="M74.244,262.736H10c-5.523,0-10,4.477-10,10v10c0,5.523,4.477,10,10,10h64.244c5.522,0,10-4.477,10-10v-10
                                        C84.244,267.213,79.767,262.736,74.244,262.736z"/>
                                    <path d="M298.29,216.877l-7.071-7.071c-1.875-1.875-4.419-2.929-7.071-2.929c-2.652,0-5.196,1.054-7.072,2.929l-34.393,34.393
                                        V18.736c0-5.523-4.477-10-10-10h-10c-5.523,0-10,4.477-10,10v225.462l-34.393-34.393c-1.876-1.875-4.419-2.929-7.071-2.929
                                        c-2.652,0-5.196,1.054-7.071,2.929l-7.072,7.071c-3.904,3.905-3.904,10.237,0,14.142l63.536,63.536
                                        c1.953,1.953,4.512,2.929,7.071,2.929c2.559,0,5.119-0.976,7.071-2.929l63.536-63.536
                                        C302.195,227.113,302.195,220.781,298.29,216.877z"/>
                                </g>
                            </svg>
                        `;
                        
                        sortIndicator.onclick = function(e) {
                            e.stopPropagation();
                            const btn = document.getElementById('year-column-btn');
                            if (btn) btn.click();
                        };
                        
                        header.appendChild(sortIndicator);
                    }
                });
                
                // Add mouseover tooltips for Field and Nested arrows
                const fieldArrow = document.getElementById('field-arrow-btn');
                const nestedArrow = document.getElementById('nested-arrow-btn');
                
                if (fieldArrow) {
                    fieldArrow.title = 'Click to show SUM(Exports/Production Value)';
                    
                    // Make Field arrow clickable - ONLY SHOW SUM TEXT BOX, DON'T SWITCH TO COMBINED MODE
                    fieldArrow.onclick = function(e) {
                        e.stopPropagation();
                        // Only show SUM text box, don't trigger combined mode
                        const btn = document.getElementById('field-sort-btn');
                        if (btn) btn.click();
                    };
                }
                
                if (nestedArrow) {
                    nestedArrow.title = 'Click to show SUM(Exports/Production Value)';
                    
                    // Make Nested arrow clickable - ONLY SHOW SUM TEXT BOX, DON'T SWITCH TO COMBINED MODE
                    nestedArrow.onclick = function(e) {
                        e.stopPropagation();
                        // Only show SUM text box, don't trigger combined mode
                        const btn = document.getElementById('nested-sort-btn');
                        if (btn) btn.click();
                    };
                }
                
                // Handle CrudeOil cell clicks - prevent link navigation, open in new tab, and highlight row
                const crudeCells = document.querySelectorAll('.dash-cell[data-dash-column="CrudeOil"]');
                crudeCells.forEach(function(cell) {
                    // Make the entire cell clickable
                    cell.style.cursor = 'pointer';
                    
                    // Handle clicks on links inside the cell
                    const links = cell.querySelectorAll('a');
                    links.forEach(function(link) {
                        // Remove target attribute (we'll handle it ourselves)
                        link.removeAttribute('target');
                        
                        link.addEventListener('click', function(e) {
                            // Prevent default link navigation (same tab)
                            e.preventDefault();
                            
                            // Get URL and open in new tab
                            const url = link.getAttribute('href');
                            if (url) {
                                window.open(url, '_blank');
                            }
                            
                            // Don't stop propagation - let the event bubble to the cell
                            // This allows DataTable's active_cell to fire
                            // The cell click handler will then highlight the row
                        }, false); // Use bubble phase so cell click can also fire
                    });
                    
                    // Also handle clicks directly on the cell (not just the link)
                    cell.addEventListener('click', function(e) {
                        // If clicking on the cell (not the link), the active_cell will fire naturally
                        // The Python callback will handle highlighting
                    }, false);
                });
                
            }, 100);
            return '';
        }
        """,
        Output('dummy-output-2', 'children'),
        Input('crude-comparison-table', 'columns'),
        prevent_initial_call=False
    )

    @app.callback(
        Output("download-crude-comparison-csv", "data"),
        Input("crude-comparison-export-dropdown", "value"),
        [State("crude-comparison-table", "data"),
         State("crude-comparison-table", "columns")],
        prevent_initial_call=True
    )
    def export_crude_comparison_csv(export_type, data, columns):
        if not export_type or export_type != 'csv' or not data:
            raise dash.exceptions.PreventUpdate

        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Clean CrudeOil column (remove Markdown links)
        if 'CrudeOil' in df.columns:
            df['CrudeOil'] = df['CrudeOil'].apply(lambda x: re.sub(r'\[(.*?)\]\(.*?\)', r'\1', str(x)) if '[' in str(x) else x)
            
        # Get column names for sorting
        col_names = [c['id'] for c in columns]
        # Only keep columns that are in the dataframe
        col_names = [c for c in col_names if c in df.columns]
        df = df[col_names]
        
        # Rename columns to their display names
        rename_dict = {c['id']: c['name'] for c in columns}
        df = df.rename(columns=rename_dict)

        return dcc.send_data_frame(df.to_csv, "crude_comparison_export.csv", index=False)

    @app.callback(
        Output("crude-comparison-export-dropdown", "value"),
        Input("download-crude-comparison-csv", "data"),
        prevent_initial_call=True
    )
    def reset_export_dropdown(data):
        return None
    
def create_crude_comparison_dashboard(dash_app, server, url_base_pathname="/dash/crude-comparison"):
    """Create the Crude Overview dashboard"""
    dash_app.layout = create_layout(server)
    register_callbacks(dash_app, server)