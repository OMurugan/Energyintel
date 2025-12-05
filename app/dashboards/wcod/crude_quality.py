from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc, Input, Output, callback_context, dash_table
from core.data_helpers import execute_query
import os
import numpy as np
import dash


def _set_df_metadata(df, **metadata):
    """Attach custom metadata to a DataFrame using the attrs dict."""
    df.attrs.update(metadata)


def _get_df_metadata(df, key, default=None):
    """Retrieve custom metadata from a DataFrame."""
    return df.attrs.get(key, default)

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'CrossPlot.csv')

# ===================================
# LOAD CSV
# ===================================
def load_crossplot_data():
    """
    Load crossplot data from database using the new query.
    Returns a DataFrame with columns: CrudeOil, Country, OPEC FSU OECD, Property - Unit, SpecificationProperty, Value, unit, YearReported
    """
    query = """
    SELECT 
        core_data."CrudeOil",
        core_data."Country",
        ctry.grp AS "OPEC FSU OECD",
        core_data."Property - Unit",
        core_data."SpecificationProperty",
        core_data."Value",
        core_data.unit,
        core_data."YearReported"
    FROM 
    (
        /* ---- Assay data (excluding product yield) ---- */
        SELECT
            a.crude_name AS "CrudeOil",
            a.country_name AS "Country",
            a.country_id,
            a.product,
            (a.property || '-' || a.unit) AS "Property - Unit",
            a.property AS "SpecificationProperty",
            a.value AS "Value",
            a.unit,
            a.assay_yr AS "YearReported"
        FROM dev.fact_wcod_assays a
        WHERE a.to_be_deleted IS NULL
          AND a.property IS NOT NULL
          AND a.value IS NOT NULL
        UNION
        /* ---- Volume data for latest year ---- */
        SELECT
            prod_data.crude_name AS "CrudeOil",
            prod_data.country_name AS "Country",
            prod_data.country_id,
            '' AS product,
            'Volume-000 b/d' AS "Property - Unit",
            'Volume' AS "SpecificationProperty",
            prod_data.production_kbpd AS "Value",
            '000 b/d' AS unit,
            EXTRACT(YEAR FROM prod_data.yr)::INT AS "YearReported"
        FROM 
            (
                SELECT *
                FROM dev.fact_wcod_crude cr_dta
                WHERE to_be_deleted IS NULL 
            ) prod_data
        LEFT JOIN 
            (
                SELECT 
                    crude_name,
                    MAX(yr) AS max_yr
                FROM dev.fact_wcod_crude
                WHERE to_be_deleted IS NULL 
                GROUP BY crude_name
            ) max_yr_crude
        ON prod_data.crude_name = max_yr_crude.crude_name
        WHERE prod_data.yr = max_yr_crude.max_yr
          AND prod_data.production_kbpd IS NOT NULL
    ) AS core_data
    LEFT JOIN dev.dim_country ctry
        ON ctry.dim_country_id = core_data.country_id
    """
    
    try:
        results = execute_query(query)
        if not results:
            print("⚠️ No crossplot data found. Returning empty DataFrame.")
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        print(f"✅ Loaded {len(df)} crossplot records from database")
        return df
        
    except Exception as e:
        print(f"❌ Error loading crossplot data from database: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def load_crude_quality_table():
    """
    Load data for 'Crudes Compared by Quality' table from database.
    
    Maps properties to parent headers:
    - Gravity: gravity, API at 60 F
    - Sulfur Content: sulphur, sulfur, mercaptan sulfur
    - Pour Point: pourpoint, pour point
    - Viscosity: viscosity, viscocity
    - Barrels: barrels
    - Nickel: nickel
    - Total Acid Number: total acid number, total acidnumber
    - Vanadium: vanadium
    - Carbon Residue Conradson: carbon residue conradson, carbon residue
    - Carbon Residue Upto Waxpoint: carbon residue upto waxpoint
    - Paraffin: parafin, paraffin
    """
    query = """
    SELECT 
        a.crude_id AS crude_id,
        a.crude_name AS "Crudeoil",
        b.bsp_link AS profile_url,
        a.country_name,
        a.product,
        a.property,
        a.value AS "Value",
        a.unit,
        a.cut_point,
        a.cut_point_sort,
        a.assay_yr,
        c.crude_alias,
        COALESCE(grp.opec_grp, 'Others') AS region_group
    FROM fact_wcod_assays a
    LEFT JOIN fact_wcod_crude_bsp_links b 
           ON a.crude_id = b.crude_id
    LEFT JOIN fact_wcod_crude c 
           ON a.crude_id = c.crude_id
    LEFT JOIN dim_country grp
           ON c.country_id = grp.dim_country_id
    WHERE a.to_be_deleted IS NULL
    """
    
    try:
        # Execute query
        results = execute_query(query)
        
        if not results:
            print("⚠️ No data found for crude quality table. Returning empty DataFrame.")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        # Normalize property names (case-insensitive matching)
        # Map various property name variations to standard parent headers
        property_mapping = {
            # Gravity
            'gravity': 'Gravity',
            'api at 60 f': 'Gravity',
            'api at 60°f': 'Gravity',
            'api at 60 f.': 'Gravity',
            'api': 'Gravity',
            'api gravity': 'Gravity',
            # Sulfur Content
            'sulphur': 'Sulfur Content',
            'sulfur': 'Sulfur Content',
            'sulphur content': 'Sulfur Content',
            'sulfur content': 'Sulfur Content',
            # Pour Point
            'pourpoint': 'Pour Point',
            'pour point': 'Pour Point',
            'pour point temperature': 'Pour Point',
            # Viscosity
            'viscosity': 'Viscosity',
            'viscocity': 'Viscosity',
            'kinematic viscosity': 'Viscosity',
            'dynamic viscosity': 'Viscosity',
            # Barrels
            'barrels': 'Barrels',
            'barrels per metric ton': 'Barrels',
            # Nickel
            'nickel': 'Nickel',
            'ni': 'Nickel',
            # Total Acid Number
            'total acid number': 'Total Acid Number',
            'total acidnumber': 'Total Acid Number',
            'tan': 'Total Acid Number',
            'acid number': 'Total Acid Number',
            # Vanadium
            'vanadium': 'Vanadium',
            'v': 'Vanadium',
            # Mercaptan Sulfur (separate from Sulfur Content)
            'mercaptan sulfur': 'Mercaptan Sulfur',
            'mercaptan sulphur': 'Mercaptan Sulfur',
            # Carbon Residue (separate from Carbon Residue Conradson)
            'carbon residue': 'Carbon Residue',
            # Carbon Residue Conradson
            'carbon residue conradson': 'Carbon Residue Conradson',
            'conradson carbon residue': 'Carbon Residue Conradson',
            'conradson': 'Carbon Residue Conradson',
            # Carbon Residue Upto Waxpoint
            'carbon residue upto waxpoint': 'Carbon Residue Upto Waxpoint',
            'carbon residue up to waxpoint': 'Carbon Residue Upto Waxpoint',
            'carbon residue upto wax point': 'Carbon Residue Upto Waxpoint',
            # Cloud Point
            'cloud point': 'Cloud Point',
            'cloudpoint': 'Cloud Point',
            # Density
            'density': 'Density',
            # Gas <C4
            'gas <c4': 'Gas <C4',
            'gas c4': 'Gas <C4',
            'gas less than c4': 'Gas <C4',
            # Micro Carbon Residue
            'micro carbon residue': 'Micro Carbon Residue',
            'mcr': 'Micro Carbon Residue',
            # Reid Vapor Pressure
            'reid vapor pressure': 'Reid Vapor Pressure',
            'rvp': 'Reid Vapor Pressure',
            'reid vapour pressure': 'Reid Vapor Pressure',
            # Salt Content
            'salt content': 'Salt Content',
            'salt': 'Salt Content',
            # Vapor Pressure
            'vapor pressure': 'Vapor Pressure',
            'vapour pressure': 'Vapor Pressure',
            # Wax Point
            'wax point': 'Wax Point',
            'waxpoint': 'Wax Point',
            # Paraffin
            'parafin': 'Paraffin',
            'paraffin': 'Paraffin',
            'paraffins': 'Paraffin',  # Handle plural form
            'paraffin content': 'Paraffin',
        }
        
        # Normalize property names
        df['property_normalized'] = df['property'].astype(str).str.lower().str.strip()
        df['parent_header'] = df['property_normalized'].map(property_mapping)
        
        # Debug: show unmapped properties
        unmapped = df[df['parent_header'].isna()]['property'].unique()
        if len(unmapped) > 0:
            print(f"DEBUG: Unmapped properties (will be filtered out): {unmapped[:10]}")  # Show first 10
        
        # Filter out rows where property doesn't map to a known parent header
        df = df[df['parent_header'].notna()]
        
        print(f"DEBUG: After property mapping, {len(df)} rows remain")
        
        if df.empty:
            print("⚠️ No valid property data found after mapping. Returning empty DataFrame.")
            return pd.DataFrame(columns=['Country', 'CrudeOil'])
        
        # IMPORTANT: Filter to only include 'Crude Oil' product (not Gasoil, Residue, etc.)
        # This ensures we get the correct values for crude oil properties
        if 'product' in df.columns:
            original_count = len(df)
            df = df[df['product'].astype(str).str.strip().str.lower() == 'crude oil']
            print(f"DEBUG: Filtered to 'Crude Oil' product: {len(df)} rows remain (from {original_count})")
        
        if df.empty:
            print("⚠️ No data found for 'Crude Oil' product. Returning empty DataFrame.")
            return pd.DataFrame(columns=['Country', 'CrudeOil'])
        
        # Convert Value to numeric, handling errors
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
        
        # Remove rows with null values after conversion
        df = df[df['Value'].notna()]
        
        print(f"DEBUG: After numeric conversion, {len(df)} rows remain")
        
        if df.empty:
            print("⚠️ No valid numeric values found. Returning empty DataFrame.")
            return pd.DataFrame(columns=['Country', 'CrudeOil'])
        
        # Filter out Sulfur Content rows with "ppm" unit - we only want "% Wt"
        # Mercaptan Sulfur will have its own parent header and can have "ppm"
        if 'unit' in df.columns and 'property' in df.columns:
            original_count = len(df)
            # Remove rows where property is sulfur/sulphur and unit is ppm
            sulfur_mask = df['property'].astype(str).str.lower().str.strip().isin(['sulphur', 'sulfur', 'sulphur content', 'sulfur content'])
            ppm_mask = df['unit'].astype(str).str.lower().str.strip().str.contains('ppm', na=False)
            df = df[~(sulfur_mask & ppm_mask)]
            removed_count = original_count - len(df)
            if removed_count > 0:
                print(f"DEBUG: Removed {removed_count} Sulfur Content rows with 'ppm' unit (keeping only '% Wt')")
        
        # Create sub-header names: property name + unit (e.g., "API at 60 F", "Sulfur % Wt")
        def create_sub_header(row):
            prop = str(row['property']).strip() if pd.notna(row['property']) else ""
            unit = str(row['unit']).strip() if pd.notna(row['unit']) else ""
            prop_lower = prop.lower()
            
            # For common cases, create readable sub-headers matching CSV format
            if prop_lower in ['gravity', 'api at 60 f', 'api at 60°f', 'api at 60 f.', 'api', 'api gravity']:
                return "API at 60 F"
            elif prop_lower in ['sulphur', 'sulfur', 'sulphur content', 'sulfur content']:
                # Sulfur Content should ONLY show "% Wt", not "ppm"
                # "ppm" is only for Mercaptan Sulfur
                # Always return "% Wt" for regular sulfur content
                return "% Wt"
            elif prop_lower in ['mercaptan sulfur', 'mercaptan sulphur']:
                return unit if unit and unit.strip() else "ppm"
            elif prop_lower in ['pourpoint', 'pour point', 'pour point temperature']:
                # Check if unit contains temperature indicator
                if unit and ('c' in unit.lower() or '°c' in unit.lower() or 'celsius' in unit.lower()):
                    return "Temp. C"
                elif unit and ('f' in unit.lower() or '°f' in unit.lower() or 'fahrenheit' in unit.lower()):
                    return "Temp. F"
                return "Pour Point"
            elif prop_lower in ['viscosity', 'viscocity', 'kinematic viscosity', 'dynamic viscosity']:
                # Viscosity units should include temperature info
                # Examples: "cSt at 10 C", "cSt at 20 C", "SSU at 80 F"
                unit_str = str(unit).strip() if unit and pd.notna(unit) else ""
                cut_point = str(row.get('cut_point', '')).strip() if pd.notna(row.get('cut_point')) else ""
                
                # Check if unit already contains temperature info
                if unit_str and ('at' in unit_str.lower() or '°' in unit_str):
                    return unit_str
                
                # Try to construct from unit and cut_point
                if unit_str and cut_point:
                    # Format: "cSt at 10 C" or "SSU at 80 F"
                    if 'cst' in unit_str.lower() or 'centistokes' in unit_str.lower():
                        return f"cSt at {cut_point} C"
                    elif 'ssu' in unit_str.lower() or 'saybolt' in unit_str.lower():
                        return f"SSU at {cut_point} F"
                    else:
                        return f"{unit_str} at {cut_point}"
                elif unit_str:
                    return unit_str
                # Default fallback
                return "Viscosity"
            elif prop_lower in ['barrels', 'barrels per metric ton']:
                return unit if unit and unit.strip() else "Barrels"
            elif prop_lower in ['nickel', 'ni']:
                return unit if unit and unit.strip() else "Nickel"
            elif prop_lower in ['total acid number', 'total acidnumber', 'tan', 'acid number']:
                return unit if unit and unit.strip() else "Total Acid Number"
            elif prop_lower in ['vanadium', 'v']:
                return unit if unit and unit.strip() else "Vanadium"
            elif prop_lower == 'carbon residue':
                return "% Wt" if not unit or not unit.strip() else unit
            elif prop_lower in ['carbon residue conradson', 'conradson carbon residue', 'conradson']:
                return "% Wt" if not unit or not unit.strip() else unit
            elif prop_lower in ['carbon residue upto waxpoint', 'carbon residue up to waxpoint', 'carbon residue upto wax point']:
                return unit if unit and unit.strip() else "Carbon Residue Upto Waxpoint"
            elif prop_lower in ['cloud point', 'cloudpoint']:
                return "Temp. C" if not unit or not unit.strip() or 'c' in unit.lower() else unit
            elif prop_lower == 'density':
                # Handle different density units
                if unit and unit.strip():
                    if '15' in unit or '15 c' in unit.lower():
                        return "kg/m3 at 15 C"
                    elif '20' in unit or '20 c' in unit.lower():
                        return "kg/m3 at 20 C"
                    return unit
                return "kg/m3 at 15 C"
            elif prop_lower in ['gas <c4', 'gas c4', 'gas less than c4']:
                return "% Wt" if not unit or not unit.strip() else unit
            elif prop_lower in ['micro carbon residue', 'mcr']:
                return "% Wt" if not unit or not unit.strip() else unit
            elif prop_lower in ['reid vapor pressure', 'rvp', 'reid vapour pressure']:
                return "psi at 37.8 C" if not unit or not unit.strip() else unit
            elif prop_lower in ['salt content', 'salt']:
                return "% Wt" if not unit or not unit.strip() else unit
            elif prop_lower in ['vapor pressure', 'vapour pressure']:
                # Could be kPa or psia
                if unit and unit.strip():
                    return unit
                return "kPa"
            elif prop_lower in ['wax point', 'waxpoint']:
                return "Temp. C" if not unit or not unit.strip() or 'c' in unit.lower() else unit
            elif prop_lower in ['parafin', 'paraffin', 'paraffins', 'paraffin content']:
                # Paraffins should show "% Wt" as sub-header
                return "% Wt" if not unit or not unit.strip() else unit
            else:
                # Fallback: use property name + unit
                return f"{prop} {unit}".strip() if unit and unit.strip() else prop
        
        df['sub_header'] = df.apply(create_sub_header, axis=1)
        
        # Check if we have data to pivot
        if df.empty:
            print("⚠️ No data to pivot. Returning empty DataFrame with Country and CrudeOil columns.")
            return pd.DataFrame(columns=['Country', 'CrudeOil'])
        
        # Sort by assay_yr descending to prioritize latest data when there are duplicates
        if 'assay_yr' in df.columns:
            df = df.sort_values('assay_yr', ascending=False, na_position='last')
        
        # Preserve region_group before pivoting (if it exists)
        region_group_map = None
        if 'region_group' in df.columns:
            region_group_map = df[['country_name', 'Crudeoil', 'region_group']].drop_duplicates()
            region_group_map = region_group_map.set_index(['country_name', 'Crudeoil'])['region_group'].to_dict()
        
        # Pivot the data: Country and CrudeOil as index, properties as columns
        # Group by country_name, Crudeoil, and property to handle multiple values
        # Use 'first' to take the first value (which will be the latest assay year after sorting)
        try:
            pivot_df = df.pivot_table(
                index=['country_name', 'Crudeoil'],
                columns=['parent_header', 'sub_header'],
                values='Value',
                aggfunc='first'  # Take first value if duplicates (latest assay year after sorting)
            )
        except Exception as e:
            print(f"ERROR during pivot: {e}")
            print(f"DataFrame shape: {df.shape}")
            print(f"DataFrame columns: {list(df.columns)}")
            print(f"Required columns present: country_name={('country_name' in df.columns)}, Crudeoil={('Crudeoil' in df.columns)}, parent_header={('parent_header' in df.columns)}, sub_header={('sub_header' in df.columns)}, Value={('Value' in df.columns)}")
            return pd.DataFrame(columns=['Country', 'CrudeOil'])
        
        # Reset index to make Country and CrudeOil regular columns
        pivot_df = pivot_df.reset_index()
        
        # Add region_group back if it was preserved
        if region_group_map:
            pivot_df['region_group'] = pivot_df.set_index(['country_name', 'Crudeoil']).index.map(
                lambda x: region_group_map.get(x, 'Others')
            ).values
        
        # Debug: print structure before flattening
        print(f"DEBUG: pivot_df columns before flattening: {list(pivot_df.columns)}")
        print(f"DEBUG: pivot_df shape: {pivot_df.shape}")
        print(f"DEBUG: pivot_df is MultiIndex: {isinstance(pivot_df.columns, pd.MultiIndex)}")
        
        # Flatten MultiIndex columns if they exist
        if isinstance(pivot_df.columns, pd.MultiIndex):
            # Flatten the column MultiIndex
            # Store the mapping for later use in column_info
            flattened_cols = []
            for col_tuple in pivot_df.columns:
                if isinstance(col_tuple, tuple) and len(col_tuple) == 2:
                    parent, sub = col_tuple
                    parent = str(parent).strip() if pd.notna(parent) else ""
                    sub = str(sub).strip() if pd.notna(sub) else ""
                    # Use a special separator that's unlikely to appear in property names
                    # We'll use "|||" as separator to avoid conflicts with underscores in sub-headers
                    if parent:
                        flattened_cols.append(f"{parent}|||{sub}")
                    else:
                        flattened_cols.append(sub)
                else:
                    flattened_cols.append(str(col_tuple))
            pivot_df.columns = flattened_cols
            print(f"DEBUG: After flattening: {list(pivot_df.columns)}")
        
        # Rename index columns (country_name and Crudeoil should now be regular columns)
        if 'country_name' in pivot_df.columns:
            pivot_df = pivot_df.rename(columns={'country_name': 'Country'})
        if 'Crudeoil' in pivot_df.columns:
            pivot_df = pivot_df.rename(columns={'Crudeoil': 'CrudeOil'})
        
        # Ensure Country and CrudeOil columns exist
        if 'Country' not in pivot_df.columns:
            print(f"WARNING: 'Country' column not found after pivot. Available columns: {list(pivot_df.columns)}")
            # Try to find it with different name
            for col in pivot_df.columns:
                if 'country' in str(col).lower():
                    pivot_df = pivot_df.rename(columns={col: 'Country'})
                    print(f"Renamed '{col}' to 'Country'")
                    break
        if 'CrudeOil' not in pivot_df.columns:
            print(f"WARNING: 'CrudeOil' column not found after pivot. Available columns: {list(pivot_df.columns)}")
            # Try to find it with different name
            for col in pivot_df.columns:
                if 'crudeoil' in str(col).lower() or 'crude' in str(col).lower():
                    pivot_df = pivot_df.rename(columns={col: 'CrudeOil'})
                    print(f"Renamed '{col}' to 'CrudeOil'")
                    break
        
        # If still missing, return empty DataFrame with proper structure
        if 'Country' not in pivot_df.columns or 'CrudeOil' not in pivot_df.columns:
            print(f"ERROR: Required columns missing. Returning empty DataFrame.")
            return pd.DataFrame(columns=['Country', 'CrudeOil'])
        
        # Sort by Country and CrudeOil
        if 'Country' in pivot_df.columns and 'CrudeOil' in pivot_df.columns:
            pivot_df = pivot_df.sort_values(['Country', 'CrudeOil']).reset_index(drop=True)
        
        # Create column_info metadata for grouped headers
        column_info = []
        parent_headers = []
        sub_headers = []
        
        # Add Country and CrudeOil columns first
        column_info.append({"id": "Country", "parent": "", "sub": "Country", "original_idx": 0})
        parent_headers.append("")
        sub_headers.append("Country")
        
        column_info.append({"id": "CrudeOil", "parent": "", "sub": "CrudeOil", "original_idx": 1})
        parent_headers.append("")
        sub_headers.append("CrudeOil")
        
        # Process property columns
        col_idx = 2
        rename_dict = {}
        seen_sub_headers = {}  # Track sub-header occurrences for unique IDs
        
        for col in pivot_df.columns:
            if col in ['Country', 'CrudeOil']:
                continue
            
            # Parse column name: could be "parent|||sub" format (from MultiIndex flattening) or just "sub"
            if '|||' in col:
                # Split on our special separator
                parts = col.split('|||', 1)
                if len(parts) == 2:
                    parent, sub = parts
                    parent = str(parent).strip() if parent else ""
                    sub = str(sub).strip() if sub else ""
                else:
                    parent = ""
                    sub = str(col).strip()
            else:
                # No parent header, just sub-header
                parent = ""
                sub = str(col).strip()
            
            # Create unique ID if duplicate sub-header
            if sub in seen_sub_headers:
                seen_sub_headers[sub] += 1
                unique_id = f"{sub}_{seen_sub_headers[sub]}"
            else:
                seen_sub_headers[sub] = 0
                unique_id = sub
            
            # Store column mapping
            rename_dict[col] = unique_id
            
            column_info.append({
                "id": unique_id,
                "parent": parent,
                "sub": sub,
                "original_idx": col_idx
            })
            parent_headers.append(parent)
            sub_headers.append(sub)
            col_idx += 1
        
        # Rename columns to unique IDs
        pivot_df = pivot_df.rename(columns=rename_dict)

        # If no property columns, return early with just Country and CrudeOil
        if len(column_info) <= 2:
            print("Warning: No property columns found, returning DataFrame with only Country and CrudeOil")
            _set_df_metadata(
                pivot_df,
                column_info=column_info,
                parent_headers=parent_headers,
                sub_headers=sub_headers
            )
            return pivot_df
        
        # Try to reorder columns, but don't fail if there's an error
        try:
            # Define the desired column order based on the images
            # Order: Country, CrudeOil, then properties in specific order
            desired_parent_order = [
                "Gravity",
                "Sulfur Content", 
                "Pour Point",
                "Viscosity",
                "Barrels",
                "Mercaptan Sulfur",
                "Nickel",
                "Total Acid Number",
                "Vanadium",
                "Carbon Residue",
                "Cloud Point",
                "Carbon Residue Conradson",
                "Density",
                "Gas <C4",
                "Micro Carbon Residue",
                "Reid Vapor Pressure",
                "Salt Content",
                "Vapor Pressure",
                "Wax Point",
                "Paraffin"
            ]
            
            # Define sub-header order within each parent (for properties with multiple sub-headers)
            # Only include columns that should be displayed (matching expected output)
            desired_sub_order = {
                "Viscosity": ["cSt at 10 C", "cSt at 15.6 C", "cSt at 20 C", "cSt at 37.8 C", 
                            "cSt at 40 C", "cSt at 50 C", "cSt at 60 C", "SSU at 80 F", "SSU at 100 F"],
                # Note: "SSU at 60 F" is NOT included - it should be filtered out
                "Mercaptan Sulfur": ["ppm"],  # Only "ppm", not "% Wt"
                "Density": ["kg/m3 at 15 C", "15 C", "kg/m3 at 20 C"],
                "Vapor Pressure": ["kPa", "psia"]
            }
            
            # Reorder column_info based on desired order
            # First, ensure we have Country and CrudeOil
            ordered_column_info = []
            if len(column_info) > 0:
                ordered_column_info.append(column_info[0])  # Country
            if len(column_info) > 1:
                ordered_column_info.append(column_info[1])  # CrudeOil
            
            # Group remaining columns by parent header
            columns_by_parent = {}
            for info in column_info[2:]:  # Skip Country and CrudeOil
                parent = info.get('parent', '')
                if parent not in columns_by_parent:
                    columns_by_parent[parent] = []
                columns_by_parent[parent].append(info)
            
            # Track which parents we've added
            added_parents = set()
            
            # Sort columns within each parent by desired sub-header order
            for parent in desired_parent_order:
                if parent in columns_by_parent:
                    parent_cols = columns_by_parent[parent]
                    if parent in desired_sub_order:
                        # Filter out columns not in desired sub-header order
                        sub_order = desired_sub_order[parent]
                        # Only keep columns whose sub-header is in the desired order
                        parent_cols = [col for col in parent_cols if col['sub'] in sub_order]
                        # Sort by desired sub-header order
                        try:
                            parent_cols.sort(key=lambda x: (
                                sub_order.index(x['sub']) if x['sub'] in sub_order else len(sub_order)
                            ))
                        except Exception as e:
                            print(f"Warning: Error sorting {parent} columns: {e}")
                    ordered_column_info.extend(parent_cols)
                    added_parents.add(parent)
                    if parent == "Paraffin":
                        print(f"DEBUG: Paraffin columns found: {[col.get('sub') for col in parent_cols]}")
                else:
                    if parent == "Paraffin":
                        print(f"DEBUG: No Paraffin columns found in columns_by_parent. Available parents: {list(columns_by_parent.keys())[:10]}")
            
            # Define columns to exclude (not in desired output)
            excluded_patterns = ['kg/liter', '% wt_3', '%wt_3', 'ssu at 60 f', 'ssu at 60f']
            
            # Add any remaining columns not in desired order (in their original order)
            # But exclude unwanted columns
            for parent, cols in columns_by_parent.items():
                if parent not in added_parents:
                    # Filter out excluded columns
                    filtered_cols = []
                    for col in cols:
                        sub_header = str(col.get('sub', '')).lower()
                        parent_header = str(col.get('parent', '')).lower()
                        col_id = str(col.get('id', '')).lower()
                        
                        should_exclude = False
                        for pattern in excluded_patterns:
                            if pattern in sub_header or pattern in parent_header or pattern in col_id:
                                should_exclude = True
                                print(f"DEBUG: Excluding column - parent: '{col.get('parent')}', sub: '{col.get('sub')}', id: '{col.get('id')}'")
                                break
                        
                        if not should_exclude:
                            filtered_cols.append(col)
                    ordered_column_info.extend(filtered_cols)
            
            # Update column_info with ordered version
            column_info = ordered_column_info
            
            # Reorder DataFrame columns to match ordered column_info
            # Make sure we preserve all existing columns
            ordered_cols = []
            seen_cols = set()
            
            # Add columns in the desired order
            for info in column_info:
                col_id = info['id']
                if col_id in pivot_df.columns and col_id not in seen_cols:
                    ordered_cols.append(col_id)
                    seen_cols.add(col_id)
            
            # Define excluded column patterns
            excluded_patterns = ['kg/liter', '% wt_3', '%wt_3', 'ssu at 60 f', 'ssu at 60f']
            
            # Add any remaining columns that weren't in column_info (safety check)
            # But exclude unwanted columns
            for col in pivot_df.columns:
                if col not in seen_cols:
                    col_lower = str(col).lower()
                    should_exclude = False
                    for pattern in excluded_patterns:
                        if pattern in col_lower:
                            should_exclude = True
                            print(f"DEBUG: Excluding DataFrame column '{col}' (matches pattern '{pattern}')")
                            break
                    
                    if not should_exclude:
                        ordered_cols.append(col)
                        print(f"Warning: Column '{col}' not in column_info, adding at end")
            
            # Only reorder if we have columns
            if ordered_cols:
                pivot_df = pivot_df[ordered_cols]
            else:
                print("Warning: No columns to reorder, keeping original order")
            
            # Update original_idx to reflect new order
            for idx, info in enumerate(column_info):
                info['original_idx'] = idx
            
            # Update parent_headers and sub_headers to match ordered column_info
            parent_headers = [info.get('parent', '') for info in column_info]
            sub_headers = [info.get('sub', '') for info in column_info]
        except Exception as e:
            print(f"Warning: Error during column reordering: {e}")
            print(f"Using original column order")
            import traceback
            traceback.print_exc()
            # Keep original order if reordering fails
            # parent_headers and sub_headers are already set from earlier
        
        # Attach metadata
        _set_df_metadata(
            pivot_df,
            column_info=column_info,
            parent_headers=parent_headers,
            sub_headers=sub_headers
        )
        
        print(f"✅ Loaded {len(pivot_df)} rows for crude quality table from database")
        print(f"   Columns: {list(pivot_df.columns)[:10]}...")  # Show first 10 columns
        return pivot_df
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error loading crude quality table from database:")
        print(f"   {error_msg}")
        import traceback
        traceback.print_exc()
        print(f"\n⚠️ Returning empty DataFrame. Please check database connection and configuration.")
        return pd.DataFrame()


def create_grouped_columns(df):
    """Create columns with grouped headers for DataTable"""
    column_info = _get_df_metadata(df, "column_info")
    if df.empty or not column_info:
        return [{"name": col, "id": col} for col in df.columns]
    
    # Create a mapping from column ID to column info
    info_map = {info["id"]: info for info in column_info}
    
    columns = []
    for idx, col_id in enumerate(df.columns):
        if col_id in info_map:
            info = info_map[col_id]
            parent = info["parent"]
            sub = info["sub"]

            # Make sub-header unique by appending only invisible Unicode characters
            # This prevents merging of duplicate sub-headers in the second row
            # Each sub-header will be treated as separate even if the text is the same
            # Parent headers in the first row can still merge if they're the same
            # Encode index as invisible characters (zero-width space, non-joiner, joiner)
            # Convert index to base-4 and map to invisible chars: 0=\u200B, 1=\u200C, 2=\u200D, 3=\uFEFF
            invisible_chars = ['\u200B', '\u200C', '\u200D', '\uFEFF']  # All invisible
            index_str = ''
            temp_idx = idx
            while temp_idx > 0:
                index_str = invisible_chars[temp_idx % 4] + index_str
                temp_idx //= 4
            if not index_str:
                index_str = invisible_chars[0]
            unique_sub = f"{sub}{index_str}"  # Only invisible characters, no visible numbers

            # For Country and CrudeOil, use empty parent header to align with two-level structure
            if sub in ["Country", "CrudeOil"]:
                # Use empty string as parent to show only sub-header in second row
                display_name = ["", unique_sub]
            elif parent and parent != sub:
                # Two-level header: first row = parent, second row = sub (unique)
                display_name = [parent, unique_sub]
            else:
                # Single header row
                display_name = unique_sub

            columns.append({
                "name": display_name,
                "id": col_id
            })
        else:
            # Fallback if info not found
            columns.append({
                "name": col_id,
                "id": col_id
            })

    return columns


def process_quality_table_data(df, country_col_id, crudeoil_col_id):
    """Merge country cells visually (Tableau style)"""
    if df.empty:
        return []
    
    # Validate column IDs
    if not country_col_id or country_col_id not in df.columns:
        print(f"ERROR: country_col_id '{country_col_id}' not found in DataFrame columns: {list(df.columns)}")
        return []
    if not crudeoil_col_id or crudeoil_col_id not in df.columns:
        print(f"ERROR: crudeoil_col_id '{crudeoil_col_id}' not found in DataFrame columns: {list(df.columns)}")
        return []

    df = df.copy()

    # Normalize the country column - ensure empty strings are truly empty
    df[country_col_id] = df[country_col_id].fillna("").astype(str).str.strip()
    df[crudeoil_col_id] = df[crudeoil_col_id].fillna("").astype(str).str.strip()
    
    # Replace empty strings with None, then back to empty string to ensure consistency
    df[country_col_id] = df[country_col_id].replace("", None).fillna("")
    df[crudeoil_col_id] = df[crudeoil_col_id].replace("", None).fillna("")

    # Remove duplicate country values, keeping only the first occurrence
    prev = None
    for i in range(len(df)):
        val = str(df.at[i, country_col_id]).strip()
        if val == prev and val != "":
            df.at[i, country_col_id] = ""      # remove duplicate - use empty string
        else:
            prev = val                         # keep first
    
    # Convert to dict, ensuring empty strings are preserved
    records = df.to_dict("records")
    # Ensure empty strings are truly empty (not None)
    for record in records:
        if country_col_id in record and record[country_col_id] is None:
            record[country_col_id] = ""
        if crudeoil_col_id in record and record[crudeoil_col_id] is None:
            record[crudeoil_col_id] = ""
    
    return records



def load_yield_volume_table():
    """
    Load data for 'Crudes Compared by Product Yield' table from database.
    
    Structure:
    - Country, CrudeOil (from country_name, Crudeoil)
    - Gravity: API at 60 F (from property="Gravity", product="Crude Oil", unit="API at 60 F")
    - Barrels: Per Metric Ton (from property="Barrels", product="Crude Oil", unit="Per Metric Ton")
    - Product columns: Gasoil, Kerosene, LPG, Naphtha, Residue (from product, unit="Yield Volume")
    """
    query = """
    SELECT 
        a.crude_id AS crude_id,
        a.crude_name AS "Crudeoil",
        b.bsp_link AS profile_url,
        a.country_name,
        a.product,
        a.property,
        a.value AS "Value",
        a.unit,
        a.cut_point,
        a.cut_point_sort,
        a.assay_yr,
        c.crude_alias
    FROM fact_wcod_assays a
    LEFT JOIN fact_wcod_crude_bsp_links b 
           ON a.crude_id = b.crude_id
    LEFT JOIN fact_wcod_crude c 
           ON a.crude_id = c.crude_id
    WHERE a.to_be_deleted IS NULL
    """
    
    try:
        # Execute query
        results = execute_query(query)
        
        if not results:
            print("⚠️ No data found for yield volume table. Returning empty DataFrame.")
            return pd.DataFrame(columns=['Country', 'CrudeOil'])
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        print(f"DEBUG: Total rows from database: {len(df)}")
        
        # Convert Value to numeric
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
        df = df[df['Value'].notna()]
        
        print(f"DEBUG: Rows with valid numeric values: {len(df)}")
        
        if df.empty:
            print("⚠️ No valid numeric values found. Returning empty DataFrame.")
            return pd.DataFrame(columns=['Country', 'CrudeOil'])
        
        # Normalize product and unit names (handle NaN values)
        df['product'] = df['product'].fillna('').astype(str).str.strip()
        df['property'] = df['property'].fillna('').astype(str).str.strip()
        df['unit'] = df['unit'].fillna('').astype(str).str.strip()
        
        print(f"DEBUG: Sample products: {df['product'].value_counts().head(10).to_dict()}")
        print(f"DEBUG: Sample units: {df['unit'].value_counts().head(10).to_dict()}")
        
        # Filter for yield volume data:
        # 1. Gravity (API at 60 F) from Crude Oil product
        # 2. Barrels (Per Metric Ton) from Crude Oil product
        # 3. Product yields (Gasoil, Kerosene, LPG, Naphtha, Residue) with Yield Volume unit
        
        yield_data = []
        
        # Sort by assay_yr descending to prioritize latest data
        if 'assay_yr' in df.columns:
            df = df.sort_values('assay_yr', ascending=False, na_position='last')
        
        # Debug: show available products and units
        print(f"DEBUG: Available products: {df['product'].unique()[:10]}")
        print(f"DEBUG: Available properties: {df['property'].unique()[:10]}")
        print(f"DEBUG: Available units: {df['unit'].unique()[:20]}")
        
        # Get Gravity (API at 60 F) from Crude Oil
        gravity_data = df[
            (df['product'].str.lower().str.strip() == 'crude oil') &
            (df['property'].str.lower().str.strip().isin(['gravity', 'api', 'api at 60 f', 'api gravity', 'api at 60°f'])) &
            (df['unit'].str.contains('API at 60 F', case=False, na=False) | 
             df['unit'].str.contains('API at 60°F', case=False, na=False) |
             df['unit'].str.contains('API', case=False, na=False))
        ].copy()
        if not gravity_data.empty:
            gravity_data['parent_header'] = 'Gravity'
            gravity_data['sub_header'] = 'API at 60 F'
            # Round Value to 2 decimal places
            gravity_data['Value'] = gravity_data['Value'].round(2)
            yield_data.append(gravity_data)
            print(f"DEBUG: Found {len(gravity_data)} Gravity rows")
        else:
            print("DEBUG: No Gravity data found")
        
        # Get Barrels (Per Metric Ton) from Crude Oil
        barrels_data = df[
            (df['product'].str.lower().str.strip() == 'crude oil') &
            (df['property'].str.lower().str.strip() == 'barrels') &
            (df['unit'].str.contains('Per Metric Ton', case=False, na=False) |
             df['unit'].str.contains('per metric ton', case=False, na=False))
        ].copy()
        if not barrels_data.empty:
            barrels_data['parent_header'] = 'Barrels'
            barrels_data['sub_header'] = 'Per Metric Ton'
            # Round Value to 2 decimal places
            barrels_data['Value'] = barrels_data['Value'].round(2)
            yield_data.append(barrels_data)
            print(f"DEBUG: Found {len(barrels_data)} Barrels rows")
        else:
            print("DEBUG: No Barrels data found")
        
        # Get product yields (Gasoil, Kerosene, LPG, Naphtha, Residue) with Yield Volume unit
        # Aggregate variations:
        # - Gasoil = Light Gasoil + Heavy Gasoil + Int. Gasoil (SUM)
        # - Naphtha = Light Naphtha + Heavy Naphtha + Int. Naphtha (SUM)
        # - Residue = Heavy Residue + Light Residue (SUM)
        # - LPG and Kerosene: direct values (FIRST, not sum - take latest by assay_yr if available)
        product_mapping = {
            'Gasoil': {'patterns': ['light gasoil', 'heavy gasoil', 'int. gasoil', 'int gasoil', 'gasoil'], 'aggregate': 'sum'},  # Sum all Gasoil variations (including exact "Gasoil")
            'Kerosene': {'patterns': ['kerosene'], 'aggregate': 'first'},  # Direct value, not sum
            'LPG': {'patterns': ['lpg'], 'aggregate': 'first'},  # Direct value, not sum
            'Naphtha': {'patterns': ['light naphtha', 'heavy naphtha', 'int. naphtha', 'int naphtha', 'naphtha'], 'aggregate': 'sum'},  # Sum all Naphtha variations (including exact "Naphtha")
            'Residue': {'patterns': ['heavy residue', 'light residue', 'residue'], 'aggregate': 'sum'}  # Sum Heavy and Light Residue (also match exact "Residue")
        }
        
        for target_product, config in product_mapping.items():
            patterns = config['patterns']
            aggregate_method = config['aggregate']
            
            # Create mask to match any product name containing the pattern
            # For exact matches like "gasoil", "naphtha", "residue", match exactly or as part of compound names
            product_mask = pd.Series([False] * len(df))
            for pattern in patterns:
                product_lower = df['product'].astype(str).str.lower().str.strip()
                # Check for exact match or contains match
                if pattern in ['gasoil', 'naphtha', 'residue']:
                    # For these, match exact or as part of compound name
                    product_mask |= (product_lower == pattern) | product_lower.str.contains(pattern, case=False, na=False, regex=False)
                else:
                    # For variations like "light gasoil", match contains
                    product_mask |= product_lower.str.contains(pattern, case=False, na=False, regex=False)
            
            # Filter for Yield Volume unit only
            unit_mask = df['unit'].astype(str).str.lower().str.contains('yield volume', case=False, na=False)
            
            product_data = df[product_mask & unit_mask].copy()
            
            if not product_data.empty:
                # Sort by assay_yr descending to prioritize latest data (if available)
                if 'assay_yr' in product_data.columns:
                    product_data = product_data.sort_values('assay_yr', ascending=False, na_position='last')
                
                # Debug: Show sample data for Murban if it exists
                if 'Murban' in product_data['Crudeoil'].values:
                    murban_data = product_data[product_data['Crudeoil'] == 'Murban']
                    print(f"DEBUG: {target_product} data for Murban: {len(murban_data)} rows")
                    print(f"DEBUG: Murban {target_product} products: {murban_data['product'].unique()}")
                    print(f"DEBUG: Murban {target_product} values: {murban_data['Value'].tolist()}")
                    print(f"DEBUG: Murban {target_product} sum: {murban_data['Value'].sum()}")
                
                if aggregate_method == 'sum':
                    # For products that need summing (Gasoil, Naphtha, Residue):
                    # First, remove duplicates by (country, crude, product) - keep latest by assay_yr
                    # Then sum across different product variations (Light + Heavy + Int.)
                    if 'assay_yr' in product_data.columns:
                        # Remove duplicates, keeping latest assay_yr
                        product_data = product_data.drop_duplicates(subset=['country_name', 'Crudeoil', 'product'], keep='first')
                    
                    # Now sum across different product variations for same (country, crude)
                    aggregated = product_data.groupby(['country_name', 'Crudeoil'])['Value'].sum().reset_index()
                else:  # 'first' - take first value (latest if sorted by assay_yr)
                    # For Kerosene and LPG, remove duplicates and take first value per (country, crude)
                    if 'assay_yr' in product_data.columns:
                        # Remove duplicates, keeping latest assay_yr
                        product_data = product_data.drop_duplicates(subset=['country_name', 'Crudeoil', 'product'], keep='first')
                    # Take first value per (country, crude) - should be only one after deduplication
                    aggregated = product_data.groupby(['country_name', 'Crudeoil'])['Value'].first().reset_index()
                
                # Change parent header to "Yield Volume (%)" and sub-header to product name
                aggregated['parent_header'] = 'Yield Volume (%)'
                aggregated['sub_header'] = target_product
                # Round Value to 2 decimal places
                aggregated['Value'] = aggregated['Value'].round(2)
                # Ensure we have the same structure as other data
                aggregated = aggregated[['country_name', 'Crudeoil', 'parent_header', 'sub_header', 'Value']]
                yield_data.append(aggregated)
                print(f"DEBUG: Found {len(product_data)} {target_product} rows (variations: {product_data['product'].unique()}), {aggregate_method} to {len(aggregated)} unique crudes")
            else:
                print(f"DEBUG: No {target_product} data found with Yield Volume unit")
                # Debug: show what products exist
                product_samples = df[product_mask]
                if not product_samples.empty:
                    print(f"DEBUG: Found {len(product_samples)} rows matching '{target_product}' pattern, units: {product_samples['unit'].unique()[:5]}")
        
        if not yield_data:
            print("⚠️ No yield volume data found. Returning empty DataFrame.")
            print(f"DEBUG: yield_data list is empty. Check filters above.")
            return pd.DataFrame(columns=['Country', 'CrudeOil'])
        
        # Combine all yield data
        yield_df = pd.concat(yield_data, ignore_index=True)
        print(f"DEBUG: Combined yield_df has {len(yield_df)} rows")
        print(f"DEBUG: Unique crudes in yield_df: {yield_df['Crudeoil'].nunique()}")
        print(f"DEBUG: Parent headers in yield_df: {yield_df['parent_header'].unique()}")
        
        if yield_df.empty:
            print("⚠️ Combined yield data is empty. Returning empty DataFrame.")
            return pd.DataFrame(columns=['Country', 'CrudeOil'])
        
        # Ensure required columns exist before pivoting
        required_cols = ['country_name', 'Crudeoil', 'parent_header', 'sub_header', 'Value']
        missing_cols = [col for col in required_cols if col not in yield_df.columns]
        if missing_cols:
            print(f"ERROR: Missing required columns for pivot: {missing_cols}")
            print(f"   Available columns: {list(yield_df.columns)}")
            return pd.DataFrame(columns=['Country', 'CrudeOil'])
        
        # Pivot the data: Country and CrudeOil as index, (parent_header, sub_header) as columns
        try:
            pivot_df = yield_df.pivot_table(
                index=['country_name', 'Crudeoil'],
                columns=['parent_header', 'sub_header'],
                values='Value',
                aggfunc='first'
            )
            print(f"DEBUG: Pivot successful, shape: {pivot_df.shape}")
            print(f"DEBUG: Pivot index names: {pivot_df.index.names if hasattr(pivot_df.index, 'names') else 'No index names'}")
        except Exception as e:
            print(f"ERROR during pivot: {e}")
            print(f"   yield_df columns: {list(yield_df.columns)}")
            print(f"   yield_df shape: {yield_df.shape}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame(columns=['Country', 'CrudeOil'])
        
        # Check if pivot resulted in empty DataFrame
        if pivot_df.empty:
            print("⚠️ Pivot resulted in empty DataFrame. Returning empty DataFrame.")
            return pd.DataFrame(columns=['Country', 'CrudeOil'])
        
        # Reset index to make Country and CrudeOil regular columns
        pivot_df = pivot_df.reset_index()
        
        print(f"DEBUG: After reset_index, pivot_df shape: {pivot_df.shape}, columns: {list(pivot_df.columns)[:10]}")
        
        # Flatten MultiIndex columns if they exist
        if isinstance(pivot_df.columns, pd.MultiIndex):
            flattened_cols = []
            for col_tuple in pivot_df.columns:
                if isinstance(col_tuple, tuple) and len(col_tuple) == 2:
                    parent, sub = col_tuple
                    parent = str(parent).strip() if pd.notna(parent) else ""
                    sub = str(sub).strip() if pd.notna(sub) else ""
                    # Handle empty sub-header (for index columns like country_name, Crudeoil)
                    if not sub and parent:
                        # This is an index column, use parent name directly
                        flattened_cols.append(parent)
                    elif parent:
                        flattened_cols.append(f"{parent}|||{sub}")
                    else:
                        flattened_cols.append(sub)
                else:
                    flattened_cols.append(str(col_tuple))
            pivot_df.columns = flattened_cols
            print(f"DEBUG: After flattening, columns: {list(pivot_df.columns)[:10]}")
        
        # Rename index columns (handle both original names and flattened names)
        if 'country_name' in pivot_df.columns:
            pivot_df = pivot_df.rename(columns={'country_name': 'Country'})
        elif 'country_name|||' in pivot_df.columns:
            pivot_df = pivot_df.rename(columns={'country_name|||': 'Country'})
        elif any('country' in str(col).lower() for col in pivot_df.columns):
            # Find column with country in name
            for col in pivot_df.columns:
                if 'country' in str(col).lower() and col not in ['Country']:
                    pivot_df = pivot_df.rename(columns={col: 'Country'})
                    break
        
        if 'Crudeoil' in pivot_df.columns:
            pivot_df = pivot_df.rename(columns={'Crudeoil': 'CrudeOil'})
        elif 'Crudeoil|||' in pivot_df.columns:
            pivot_df = pivot_df.rename(columns={'Crudeoil|||': 'CrudeOil'})
        elif any('crudeoil' in str(col).lower() or 'crude' in str(col).lower() for col in pivot_df.columns):
            # Find column with crudeoil in name
            for col in pivot_df.columns:
                col_lower = str(col).lower()
                if ('crudeoil' in col_lower or 'crude' in col_lower) and col not in ['CrudeOil', 'Country']:
                    pivot_df = pivot_df.rename(columns={col: 'CrudeOil'})
                    break
        
        # Ensure Country and CrudeOil columns exist
        if 'Country' not in pivot_df.columns:
            print(f"ERROR: 'Country' column not found after reset_index. Available columns: {list(pivot_df.columns)}")
            return pd.DataFrame(columns=['Country', 'CrudeOil'])
        if 'CrudeOil' not in pivot_df.columns:
            print(f"ERROR: 'CrudeOil' column not found after reset_index. Available columns: {list(pivot_df.columns)}")
            return pd.DataFrame(columns=['Country', 'CrudeOil'])
        
        # Sort by Country and CrudeOil
        pivot_df = pivot_df.sort_values(['Country', 'CrudeOil']).reset_index(drop=True)
        
        # Create column_info metadata
        column_info = []
        parent_headers = []
        sub_headers = []
        
        # Add Country and CrudeOil columns first
        column_info.append({"id": "Country", "parent": "", "sub": "Country", "original_idx": 0})
        parent_headers.append("")
        sub_headers.append("Country")
        
        column_info.append({"id": "CrudeOil", "parent": "", "sub": "CrudeOil", "original_idx": 1})
        parent_headers.append("")
        sub_headers.append("CrudeOil")
        
        # Define desired column order
        # Structure: (parent_header, sub_header)
        # For product yields, all should be under "Yield Volume (%)" parent
        desired_order = [
            ("Gravity", "API at 60 F"),
            ("Barrels", "Per Metric Ton"),
            ("Yield Volume (%)", "Gasoil"),
            ("Yield Volume (%)", "Kerosene"),
            ("Yield Volume (%)", "LPG"),
            ("Yield Volume (%)", "Naphtha"),
            ("Yield Volume (%)", "Residue")
        ]
        
        # Process property columns - find existing columns and create column_info
        col_idx = 2
        seen_sub_headers = {}
        rename_dict = {}
        
        for parent, sub in desired_order:
            # Look for this column in the DataFrame
            col_name = None
            for col in pivot_df.columns:
                if col in ['Country', 'CrudeOil']:
                    continue
                if '|||' in col:
                    parts = col.split('|||', 1)
                    if len(parts) == 2 and parts[0] == parent and parts[1] == sub:
                        col_name = col
                        break
                elif parent == "" and col == sub:
                    col_name = col
                    break
            
            if col_name and col_name in pivot_df.columns:
                # For product yields under "Yield Volume (%)", use product name as unique ID
                # For others, use sub-header as unique ID
                if parent == "Yield Volume (%)":
                    # Use product name (sub) as unique ID for yield volume products
                    unique_id = sub
                else:
                    # Create unique ID if duplicate sub-header
                    if sub in seen_sub_headers:
                        seen_sub_headers[sub] += 1
                        unique_id = f"{sub}_{seen_sub_headers[sub]}"
                    else:
                        seen_sub_headers[sub] = 0
                        unique_id = sub
                
                # Store rename mapping
                rename_dict[col_name] = unique_id
                
                column_info.append({
                    "id": unique_id,
                    "parent": parent,
                    "sub": sub,
                    "original_idx": col_idx
                })
                parent_headers.append(parent)
                sub_headers.append(sub)
                col_idx += 1
        
        # Rename columns to match column_info IDs
        pivot_df = pivot_df.rename(columns=rename_dict)
        
        # Reorder columns to match desired order
        # Only include columns that actually exist in the DataFrame
        ordered_cols = []
        
        # Add Country and CrudeOil first if they exist
        if 'Country' in pivot_df.columns:
            ordered_cols.append('Country')
        if 'CrudeOil' in pivot_df.columns:
            ordered_cols.append('CrudeOil')
        
        # Add property columns in desired order
        for info in column_info[2:]:
            if info['id'] in pivot_df.columns and info['id'] not in ordered_cols:
                ordered_cols.append(info['id'])
        
        # Add any remaining columns that weren't in column_info
        for col in pivot_df.columns:
            if col not in ordered_cols:
                ordered_cols.append(col)
        
        # Only reorder if we have columns
        if ordered_cols:
            try:
                pivot_df = pivot_df[ordered_cols]
            except KeyError as e:
                print(f"ERROR: KeyError when reordering columns: {e}")
                print(f"   Requested columns: {ordered_cols}")
                print(f"   Available columns: {list(pivot_df.columns)}")
                # Try to create a minimal valid DataFrame
                if 'Country' in pivot_df.columns and 'CrudeOil' in pivot_df.columns:
                    pivot_df = pivot_df[['Country', 'CrudeOil']]
                else:
                    return pd.DataFrame(columns=['Country', 'CrudeOil'])
        else:
            print("WARNING: No columns to reorder")
            # If we have Country and CrudeOil, keep them at least
            if 'Country' in pivot_df.columns and 'CrudeOil' in pivot_df.columns:
                pivot_df = pivot_df[['Country', 'CrudeOil']]
            else:
                return pd.DataFrame(columns=['Country', 'CrudeOil'])
        
        # Ensure we have at least Country and CrudeOil columns
        if 'Country' not in pivot_df.columns or 'CrudeOil' not in pivot_df.columns:
            print(f"ERROR: Missing required columns. Available: {list(pivot_df.columns)}")
            return pd.DataFrame(columns=['Country', 'CrudeOil'])
        
        # Attach metadata
        _set_df_metadata(
            pivot_df,
            column_info=column_info,
            parent_headers=parent_headers,
            sub_headers=sub_headers
        )
        
        print(f"✅ Loaded {len(pivot_df)} rows for yield volume table from database")
        print(f"   Columns: {list(pivot_df.columns)[:10]}...")
        return pivot_df
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error loading yield volume table from database:")
        print(f"   {error_msg}")
        import traceback
        traceback.print_exc()
        print(f"\n⚠️ Returning empty DataFrame. Please check database connection and configuration.")
        return pd.DataFrame(columns=['Country', 'CrudeOil'])

def process_yield_table_data(df):
    """
    Process yield table data to merge country cells visually (Tableau style).
    Same logic as process_quality_table_data - country names appear once per group.
    """
    if df.empty:
        return []
    
    df = df.copy()
    
    # Find Country and CrudeOil column IDs (they might have unique IDs)
    country_col_id = None
    crudeoil_col_id = None
    
    column_info = _get_df_metadata(df, "column_info")
    if column_info:
        for info in column_info:
            if info.get('sub') == 'Country':
                country_col_id = info.get('id')
            elif info.get('sub') == 'CrudeOil':
                crudeoil_col_id = info.get('id')
    
    # Fallback: check column names directly
    if not country_col_id:
        for col in df.columns:
            if col == 'Country' or (isinstance(col, str) and 'Country' in col):
                country_col_id = col
                break
    if not crudeoil_col_id:
        for col in df.columns:
            if col == 'CrudeOil' or (isinstance(col, str) and 'CrudeOil' in col):
                crudeoil_col_id = col
                break
    
    # Normalize the country column - ensure empty strings are truly empty
    if country_col_id and country_col_id in df.columns:
        df[country_col_id] = df[country_col_id].fillna("").astype(str).str.strip()
    if crudeoil_col_id and crudeoil_col_id in df.columns:
        df[crudeoil_col_id] = df[crudeoil_col_id].fillna("").astype(str).str.strip()
    
    # Replace empty strings with None, then back to empty string to ensure consistency
    if country_col_id and country_col_id in df.columns:
        df[country_col_id] = df[country_col_id].replace("", None).fillna("")
    if crudeoil_col_id and crudeoil_col_id in df.columns:
        df[crudeoil_col_id] = df[crudeoil_col_id].replace("", None).fillna("")
    
    # Remove duplicate country values, keeping only the first occurrence
    if country_col_id and country_col_id in df.columns:
        prev = None
        for i in range(len(df)):
            val = str(df.at[i, country_col_id]).strip()
            if val == prev and val != "":
                df.at[i, country_col_id] = ""      # remove duplicate - use empty string
            else:
                prev = val                         # keep first
    
    # Convert to dict, ensuring empty strings are preserved
    records = df.to_dict("records")
    # Ensure empty strings are truly empty (not None)
    for record in records:
        for key, value in record.items():
            if value is None:
                record[key] = ""
    
    return records

def create_layout(dash_app=None):
    # Don't load data here - load it in callbacks when page is active
    # Initialize to empty DataFrames
    df = pd.DataFrame()
    quality_df = pd.DataFrame()
    
    # Find column IDs for Country and CrudeOil for sticky positioning
    # Handle both exact match and pattern match (in case of unique IDs)
    country_col_id = None
    crudeoil_col_id = None
    if not quality_df.empty:
        # First, check if columns exist directly
        if 'Country' in quality_df.columns:
            country_col_id = 'Country'
        if 'CrudeOil' in quality_df.columns:
            crudeoil_col_id = 'CrudeOil'
        
        # If not found, check metadata
        if not country_col_id or not crudeoil_col_id:
            quality_column_info = _get_df_metadata(quality_df, "column_info")
            if quality_column_info:
                for info in quality_column_info:
                    if info.get('sub') == 'Country' and not country_col_id:
                        country_col_id = info.get('id')
                    elif info.get('sub') == 'CrudeOil' and not crudeoil_col_id:
                        crudeoil_col_id = info.get('id')
        
        # Fallback: check column names directly with pattern matching
        if not country_col_id:
            for col in quality_df.columns:
                if col == 'Country' or (isinstance(col, str) and ('Country' in col or col.startswith('Country'))):
                    country_col_id = col
                    break
        if not crudeoil_col_id:
            for col in quality_df.columns:
                if col == 'CrudeOil' or (isinstance(col, str) and ('CrudeOil' in col or col.startswith('CrudeOil'))):
                    crudeoil_col_id = col
                    break
        
        # Debug: print column info
        print(f"DEBUG: quality_df columns: {list(quality_df.columns)}")
        print(f"DEBUG: country_col_id: {country_col_id}, crudeoil_col_id: {crudeoil_col_id}")
    
    # Initialize yield_df as empty - will be loaded by callback when page is active
    yield_df = pd.DataFrame()
    
    # Find column IDs for Country and CrudeOil for Yield table (for sticky positioning and styling)
    # These will be determined in the callback when data loads
    yield_country_col_id = None
    yield_crudeoil_col_id = None
    if not yield_df.empty:
        yield_column_info = _get_df_metadata(yield_df, "column_info")
        if yield_column_info:
            for info in yield_column_info:
                if info.get('sub') == 'Country':
                    yield_country_col_id = info.get('id')
                elif info.get('sub') == 'CrudeOil':
                    yield_crudeoil_col_id = info.get('id')
        # Fallback: check column names directly
        if not yield_country_col_id:
            for col in yield_df.columns:
                if col == 'Country' or (isinstance(col, str) and 'Country' in col):
                    yield_country_col_id = col
                    break
        if not yield_crudeoil_col_id:
            for col in yield_df.columns:
                if col == 'CrudeOil' or (isinstance(col, str) and 'CrudeOil' in col):
                    yield_crudeoil_col_id = col
                    break
        
    # Static dropdown options for X-axis, Y-axis, and Bubble Size
    # Based on the Property - Unit format from the crossplot query
    all_property_options = [
        {"label": "Gravity-API at 60 F", "value": "Gravity-API at 60 F"},
        {"label": "Barrels-Per Metric Ton", "value": "Barrels-Per Metric Ton"},
        {"label": "Conradson Carbon Residue-% Wt", "value": "Conradson Carbon Residue-% Wt"},
        {"label": "Hydrogen Sulfide-ppm", "value": "Hydrogen Sulfide-ppm"},
        {"label": "K Factor-UOP 375", "value": "K Factor-UOP 375"},
        {"label": "Mercaptan Sulfur-ppm", "value": "Mercaptan Sulfur-ppm"},
        {"label": "Nickel-ppm", "value": "Nickel-ppm"},
        {"label": "Pour Point-Temp. C", "value": "Pour Point-Temp. C"},
        {"label": "Reid Vapor Pressure-psi at 37.8 C", "value": "Reid Vapor Pressure-psi at 37.8 C"},
        {"label": "Sulfur Content-% Wt", "value": "Sulfur Content-% Wt"},
        {"label": "Total Acid Number-mg KOH/g", "value": "Total Acid Number-mg KOH/g"},
        {"label": "Vanadium-ppm", "value": "Vanadium-ppm"},
        {"label": "Viscosity-cSt at 10 C", "value": "Viscosity-cSt at 10 C"},
        {"label": "Viscosity-cSt at 20 C", "value": "Viscosity-cSt at 20 C"},
        {"label": "Viscosity-cSt at 40 C", "value": "Viscosity-cSt at 40 C"},
        {"label": "Volume-000 b/d", "value": "Volume-000 b/d"}
    ]
    
    # Use the same options for all three dropdowns
    x_options = all_property_options
    y_options = all_property_options
    bubble_options = all_property_options
    
    # Default values
    default_x = "Gravity-API at 60 F"
    default_y = "Sulfur Content-% Wt"
    default_bubble = "Volume-000 b/d"

    return html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.Label("Select X Axis Property",
                    style={'fontFamily': 'Lato', 'fontSize': '16px', 'lineHeight': '18px', 'color': '#fe5000', 'fontWeight': 'bold', 'fontStyle': 'normal', 'textDecoration': 'none'}),
                dcc.Dropdown(
                    id="x-axis-dropdown",
                    options=x_options,
                    value=default_x,
                    clearable=False,
                    searchable=False,
                    style={'fontSize': '12px'}
                ),
                html.Br(),
                html.Label("X Axis Range",
                    style={'fontFamily': 'Arial', 'fontSize': '11px', 'lineHeight': '12px', 'color': '#1b365d', 'fontWeight': 'bold', 'fontStyle': 'normal', 'textDecoration': 'none', 'marginBottom': '5px'}),
                html.Div([
                    html.Div([
                        dcc.Input(
                            id="x-range-min-input",
                            type="text",
                            value=0,
                            style={'display': 'inline-block'}
                        ),
                        dcc.Input(
                            id="x-range-max-input",
                            type="text",
                            value=100,
                            style={'display': 'inline-block', 'float': 'right'}
                        ),
                    ], style={'width': '386px', 'marginBottom': '10px', 'position': 'relative'}),
                    html.Div([
                        dcc.RangeSlider(
                            id="x-range-slider",
                            min=0,
                            max=100, step=0.1, value=[0, 100],
                            marks=None,
                        ),
                    ], style={'width': '386px', 'margin': '0', 'padding': '0'}),
                ], style={'width': '100%', 'position': 'relative'}),
            ], style={'width': '32%', 'display': 'inline-block'}),

            html.Div([
                html.Label("Select Y Axis Property",
                    style={'fontFamily': 'Lato', 'fontSize': '16px', 'lineHeight': '18px', 'color': '#fe5000', 'fontWeight': 'bold', 'fontStyle': 'normal', 'textDecoration': 'none'}),
                
                dcc.Dropdown(
                    id="y-axis-dropdown",
                    options=y_options,
                    value=default_y,
                    clearable=False,
                    searchable=False,
                    style={'fontSize': '12px'}
                ),
                html.Br(),
                html.Label("Y Axis Range",
                    style={'fontFamily': 'Arial', 'fontSize': '11px', 'lineHeight': '12px', 'color': '#1b365d', 'fontWeight': 'bold', 'fontStyle': 'normal', 'textDecoration': 'none', 'marginBottom': '5px'}),
                html.Div([
                    html.Div([
                        dcc.Input(
                            id="y-range-min-input",
                            type="text",
                            value=0,
                            style={'display': 'inline-block'}
                        ),
                        dcc.Input(
                            id="y-range-max-input",
                            type="text",
                            value=100,
                            style={'display': 'inline-block', 'float': 'right'}
                        ),
                    ], style={'width': '386px', 'marginBottom': '10px', 'position': 'relative'}),
                    html.Div([
                dcc.RangeSlider(
                    id="y-range-slider",
                            min=0,
                            max=100, step=0.01, value=[0, 100],
                            marks=None,
                        ),
                    ], style={'width': '386px', 'margin': '0', 'padding': '0'}),
                ], style={'width': '100%', 'position': 'relative'}),
            ], style={'width': '32%', 'display': 'inline-block', 'marginLeft': '2%'}),

            html.Div([
                html.Label("Select Bubble Size Property",
                    style={'fontFamily': 'Lato', 'fontSize': '16px', 'lineHeight': '18px', 'color': '#fe5000', 'fontWeight': 'bold', 'fontStyle': 'normal', 'textDecoration': 'none'}),
                html.Br(),
                dcc.Dropdown(
                    id="bubble-size-dropdown",
                    options=bubble_options,
                    value=default_bubble,
                    clearable=False,
                    searchable=False,
                    style={'fontSize': '12px'}
                ),
                 html.Br(),
                html.Label("Bubble Size Range",
                    style={'fontFamily': 'Arial', 'fontSize': '11px', 'lineHeight': '12px', 'color': '#1b365d', 'fontWeight': 'bold', 'fontStyle': 'normal', 'textDecoration': 'none', 'marginBottom': '5px'}),
                html.Div([
                    html.Div([
                        dcc.Input(
                            id="bubble-range-min-input",
                            type="text",
                            value=0,
                            style={'display': 'inline-block'}
                        ),
                        dcc.Input(
                            id="bubble-range-max-input",
                            type="text",
                            value=100,
                            style={'display': 'inline-block', 'float': 'right'}
                        ),
                    ], style={'width': '386px', 'marginBottom': '10px', 'position': 'relative'}),
                    html.Div([
                dcc.RangeSlider(
                    id="bubble-range-slider",
                            min=0,
                            max=100,
                    step=1,
                            value=[0, 100],
                            marks=None,
                        ),
                    ], style={'width': '386px', 'margin': '0', 'padding': '0'}),
                ], style={'width': '100%', 'position': 'relative'}),
            ], style={'width': '32%', 'display': 'inline-block', 'marginLeft': '2%'}),
        ]),

        html.Br(),

        # --------------------------------------------------
        # MAIN CONTENT (CHART + RIGHT SIDEBAR)
        # --------------------------------------------------
        html.Div([
            # Chart
            html.Div([
                dcc.Graph(
                    id='crude-quality-chart',
                    config={
                        'displayModeBar': False,
                        'displaylogo': False,
                        'modeBarButtonsToRemove': [
                            'pan2d', 'zoom2d', 'select2d', 'lasso2d',
                            'autoScale2d', 'resetScale2d',
                            'hoverClosestCartesian', 'hoverCompareCartesian',
                            'zoomIn2d', 'zoomOut2d'
                        ]
                    }
                )
            ], style={'width': '80%', 'display': 'inline-block', 'verticalAlign': 'top'}),

            # Right Sidebar
            html.Div([

                # Key
                html.Div([
                    html.Div("Key",
                        style={'fontWeight': 'bold', 'marginBottom': '8px',
                               'fontSize': '14px', 'color': '#1a1a1a'}),
                    html.Div([
                        html.Div([
                            html.Span("", style={
                                'display': 'inline-block','width': '15px','height': '15px',
                                'backgroundColor': '#313B49','marginRight': '8px'
                            }),
                            "Null"
                        ], style={'fontSize': '8pt'}),

                        html.Div([
                            html.Span("", style={
                                'display': 'inline-block','width': '15px','height': '15px',
                                'backgroundColor': '#0075A8','marginRight': '8px'
                            }),
                            "FSU"
                        ], style={'fontSize': '8pt'}),

                        html.Div([
                            html.Span("", style={
                                'display': 'inline-block','width': '15px','height': '15px',
                                'backgroundColor': '#595959','marginRight': '8px'
                            }),
                            "OECD"
                        ], style={'fontSize': '8pt'}),

                        html.Div([
                            html.Span("", style={
                                'display': 'inline-block','width': '15px','height': '15px',
                                'backgroundColor': '#7986CB','marginRight': '8px'
                            }),
                            "OPEC"
                        ], style={'fontSize': '8pt'}),

                        html.Div([
                            html.Span("", style={
                                'display': 'inline-block','width': '15px','height': '15px',
                                'backgroundColor': '#FE5000','marginRight': '8px'
                            }),
                            "Others"
                        ], style={'fontSize': '9pt'}),

                    ])
                ], style={'marginBottom': '15px'}),

                # CrudeOil Filter
                html.Div([
                    html.Div("CrudeOil",
                        style={'fontWeight': 'bold', 'marginBottom': '7px',
                               'fontSize': '14px', 'color': '#1a1a1a'}),
                    dcc.Checklist(
                        id='crude-filter-checklist-all',
                        options=[{'label': '(All)', 'value': 'all'}],
                        value=['all'],
                        style={'fontSize': '12px'}
                    ),
                    html.Div([
                        dcc.Checklist(
                            id='crude-filter-checklist-items',
                            options=[],
                            value=[],
                            style={'fontSize': '12px'}
                        )
                    ], style={'maxHeight': '300px', 'overflowY': 'auto', 'marginTop': '10px'})
                ])

            ], style={
                'width': '18%',
                'display': 'inline-block',
                'verticalAlign': 'top',
                'paddingTop': '10px',
                'marginLeft': '2%'
            })

        ]),

        # Tables Section
        html.Div([
            # First Table: Crudes Compared by Quality
            html.Div([
                html.Div([
                    html.H3(
                        "Crudes Compared by Quality",
                        style={
                            'color': '#FF6600',
                            'fontWeight': 'bold',
                            'marginBottom': '10px',
                            'fontSize': '20px'
                        }
                    ),

                    dash_table.DataTable(
                        id='crude-quality-table',
                        columns=[],  # Will be updated by callback when data loads
                        data=[],  # Will be updated by callback when data loads
                        style_table={
                            'overflowX': 'auto',
                            'overflowY': 'auto',
                            'height': '540px',
                            'border': '1px solid #CFCFCF',
                            'borderCollapse': 'separate',
                            'borderSpacing': 0,
                            'width': '100%'
                        },
                        style_cell={
                            'padding': '8px 8px',
                            'fontSize': '12px',
                            'fontFamily': 'Arial, sans-serif',
                            'border': '1px solid #E6E6E6',
                            'whiteSpace': 'normal',
                            'textAlign': 'right',
                            'backgroundColor': 'white',
                            'height': 'auto',
                            'lineHeight': '1.4'
                        },
                        style_header={
                            'backgroundColor': 'white',
                            'fontWeight': 'bold',
                            'fontSize': '12px',
                            'fontFamily': 'Arial, sans-serif',
                            'border': '1px solid #D0D0D0',
                            'borderBottom': '2px solid #D0D0D0',
                            'padding': '8px 6px',
                            'textAlign': 'center',
                            'height': 'auto'
                        },
                        style_cell_conditional=[
                            {
                                'if': {'column_id': country_col_id},
                                'position': 'sticky',
                                'left': 0,
                                'backgroundColor': 'white',
                                'zIndex': 10,
                                'textAlign': 'left',
                                'minWidth': '140px',
                                'width': '140px',
                                'fontWeight': 'bold',
                                'color': '#333',
                                'borderRight': '2px solid #D3D3D3',
                                'fontSize': '12px',
                                'padding': '8px 8px'
                            },
                            {
                                'if': {'column_id': crudeoil_col_id},
                                'position': 'sticky',
                                'left': '140px',
                                'backgroundColor': 'white',
                                'zIndex': 10,
                                'textAlign': 'left',
                                'minWidth': '170px',
                                'width': '170px',
                                'borderRight': '2px solid #D3D3D3',
                                'fontSize': '12px',
                                'padding': '8px 8px'
                            },
                        ],
                        style_header_conditional=[
                            {
                                'if': {'column_id': country_col_id},
                                'position': 'sticky',
                                'left': 0,
                                'backgroundColor': 'white',
                                'zIndex': 11,
                                'textAlign': 'left',
                                'borderRight': '2px solid #D3D3D3'
                            },
                            {
                                'if': {'column_id': crudeoil_col_id},
                                'position': 'sticky',
                                'left': '140px',
                                'backgroundColor': 'white',
                                'zIndex': 11,
                                'textAlign': 'left',
                                'borderRight': '2px solid #D3D3D3'
                            },
                        ],
                        style_data_conditional=[
                            # Apply gray background to entire row when country is not empty
                            {
                                'if': {
                                    'filter_query': f'{{{country_col_id}}} != ""'
                                },
                                'backgroundColor': '#F5F5F5'
                            },
                            # Country column styling - header rows (non-empty)
                            {
                                'if': {
                                    'filter_query': f'{{{country_col_id}}} != ""',
                                    'column_id': country_col_id
                                },
                                'fontWeight': 'bold',
                                'borderTop': '2px solid #CFCFCF',
                                'borderBottom': '1px solid #E6E6E6',
                                'verticalAlign': 'middle',
                                'padding': '10px 8px'
                            },
                            # Country column - child rows (empty country cell)
                            {
                                'if': {
                                    'filter_query': f'{{{country_col_id}}} = ""',
                                    'column_id': country_col_id
                                },
                                'borderTop': 'none',
                                'borderBottom': '1px solid #E6E6E6',
                                'backgroundColor': 'white',
                                'padding': '8px 8px'
                            },
                            # CrudeOil column - child rows (indented, when country is empty)
                            {
                                'if': {
                                    'filter_query': f'{{{country_col_id}}} = ""',
                                    'column_id': crudeoil_col_id
                                },
                                'paddingLeft': '28px',
                                'fontWeight': 'normal',
                                'backgroundColor': 'white',
                                'paddingTop': '8px',
                                'paddingBottom': '8px'
                            },
                            # CrudeOil column - header rows (when country is not empty)
                            {
                                'if': {
                                    'filter_query': f'{{{country_col_id}}} != ""',
                                    'column_id': crudeoil_col_id
                                },
                                'paddingLeft': '8px',
                                'fontWeight': 'normal',
                                'backgroundColor': '#F5F5F5',
                                'paddingTop': '10px',
                                'paddingBottom': '10px'
                            },
                            # Text alignment - Country column always left
                            {
                                'if': {
                                    'column_id': country_col_id
                                },
                                'textAlign': 'left'
                            },
                            # Text alignment - CrudeOil column always left
                            {
                                'if': {
                                    'column_id': crudeoil_col_id
                                },
                                'textAlign': 'left'
                            }
                        ],
                        merge_duplicate_headers=True,
                        filter_action="none",
                        page_action="none",
                        sort_action="native"
                    )

                ], style={'marginTop': '30px', 'marginBottom': '30px'})
            ]),


            # Second Table: Crudes Compared by Product Yield
            html.Div([
                html.H3("Crudes Compared by Product Yield", 
                       style={'color': '#FF6600', 'fontWeight': 'bold', 'marginBottom': '10px', 'fontSize': '20px'}),
                dash_table.DataTable(
                    id='yield-volume-table',
                    columns=[],  # Will be updated by callback when data loads
                    data=[],  # Will be updated by callback when data loads
                    style_table={
                        'overflowX': 'auto',
                        'overflowY': 'auto',
                        'height': '540px',
                        'border': '1px solid #CFCFCF',
                        'borderCollapse': 'separate',
                        'borderSpacing': 0,
                        'width': '100%'
                    },
                    style_cell={
                        'padding': '8px 8px',
                        'fontSize': '12px',
                        'fontFamily': 'Arial, sans-serif',
                        'border': '1px solid #E6E6E6',
                        'textAlign': 'right',
                        'minWidth': '80px',
                        'backgroundColor': 'white',
                        'height': 'auto',
                        'lineHeight': '1.4'
                    },
                    style_header={
                        'fontWeight': 'bold',
                        'fontSize': '12px',
                        'fontFamily': 'Arial, sans-serif',
                        'backgroundColor': 'white',
                        'border': '1px solid #D0D0D0',
                        'borderBottom': '2px solid #D0D0D0',
                        'textAlign': 'center',
                        'padding': '8px 6px'
                    },
                    style_cell_conditional=([
                        {
                            'if': {'column_id': yield_country_col_id},
                            'position': 'sticky',
                            'left': 0,
                            'backgroundColor': 'white',
                            'zIndex': 10,
                            'textAlign': 'left',
                            'minWidth': '140px',
                            'width': '140px',
                            'fontWeight': 'bold',
                            'color': '#333',
                            'borderRight': '2px solid #D3D3D3',
                            'fontSize': '12px',
                            'padding': '8px 8px'
                        },
                        {
                            'if': {'column_id': yield_crudeoil_col_id},
                            'position': 'sticky',
                            'left': '140px',
                            'backgroundColor': 'white',
                            'zIndex': 10,
                            'textAlign': 'left',
                            'minWidth': '170px',
                            'width': '170px',
                            'borderRight': '2px solid #D3D3D3',
                            'fontSize': '12px',
                            'padding': '8px 8px'
                        },
                    ] if yield_country_col_id and yield_crudeoil_col_id else []),
                    style_header_conditional=([
                        {
                            'if': {'column_id': yield_country_col_id},
                            'position': 'sticky',
                            'left': 0,
                            'backgroundColor': 'white',
                            'zIndex': 11,
                            'textAlign': 'left',
                            'borderRight': '2px solid #D3D3D3'
                        },
                        {
                            'if': {'column_id': yield_crudeoil_col_id},
                            'position': 'sticky',
                            'left': '140px',
                            'backgroundColor': 'white',
                            'zIndex': 11,
                            'textAlign': 'left',
                            'borderRight': '2px solid #D3D3D3'
                        },
                    ] if yield_country_col_id and yield_crudeoil_col_id else []),
                    style_data_conditional=([
                        # Apply gray background to entire row when country is not empty (country header rows)
                        {
                            'if': {
                                'filter_query': f'{{{yield_country_col_id}}} != ""'
                            },
                            'backgroundColor': '#F5F5F5',
                            'borderTop': '2px solid #CFCFCF'
                        },
                        # Country column styling - header rows (non-empty)
                        {
                            'if': {
                                'filter_query': f'{{{yield_country_col_id}}} != ""',
                                'column_id': yield_country_col_id
                            },
                            'fontWeight': 'bold',
                            'borderTop': '2px solid #CFCFCF',
                            'borderBottom': '1px solid #E6E6E6',
                            'verticalAlign': 'middle',
                            'padding': '8px 8px',
                            'backgroundColor': '#F5F5F5'
                        },
                        # Country column - child rows (empty country cell) - remove top border
                        {
                            'if': {
                                'filter_query': f'{{{yield_country_col_id}}} = ""',
                                'column_id': yield_country_col_id
                            },
                            'borderTop': 'none',
                            'borderBottom': '1px solid #E6E6E6',
                            'backgroundColor': 'white',
                            'padding': '8px 8px'
                        },
                        # All cells in child rows (when country is empty) - ensure white background
                        {
                            'if': {
                                'filter_query': f'{{{yield_country_col_id}}} = ""'
                            },
                            'backgroundColor': 'white',
                            'borderTop': 'none'
                        },
                        # CrudeOil column - child rows (indented, when country is empty)
                        {
                            'if': {
                                'filter_query': f'{{{yield_country_col_id}}} = ""',
                                'column_id': yield_crudeoil_col_id
                            },
                            'paddingLeft': '24px',
                            'fontWeight': 'normal',
                            'backgroundColor': 'white',
                            'paddingTop': '8px',
                            'paddingBottom': '8px',
                            'paddingRight': '8px'
                        },
                        # CrudeOil column - header rows (when country is not empty)
                        {
                            'if': {
                                'filter_query': f'{{{yield_country_col_id}}} != ""',
                                'column_id': yield_crudeoil_col_id
                            },
                            'paddingLeft': '8px',
                            'fontWeight': 'normal',
                            'backgroundColor': '#F5F5F5',
                            'paddingTop': '8px',
                            'paddingBottom': '8px',
                            'paddingRight': '8px'
                        },
                        # Text alignment - Country column always left
                        {
                            'if': {
                                'column_id': yield_country_col_id
                            },
                            'textAlign': 'left'
                        },
                        # Text alignment - CrudeOil column always left
                        {
                            'if': {
                                'column_id': yield_crudeoil_col_id
                            },
                            'textAlign': 'left'
                        }
                    ] if yield_country_col_id and yield_crudeoil_col_id else []),
                    merge_duplicate_headers=True,
                    filter_action="none",
                    page_action="none",
                    sort_action="native"
                )
            ], style={'marginTop': '30px', 'marginBottom': '30px'})
        ])

        ], style={'marginLeft': '10px', 'marginRight': '28px', 'padding': '20px'})
    ])


# ===================================
# DASH APP CREATION
# ===================================
def create_crude_quality_dashboard(server, url_base_pathname="/dash/crude-quality/"):

    current_dir = Path(__file__).parent
    assets_dir = current_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    dash_app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname=url_base_pathname,
        external_stylesheets=[
            'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
            'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
        ],
        suppress_callback_exceptions=True,
        assets_folder=str(assets_dir)
    )

    # --------------------------------------------------------
    # INLINE CSS INJECTION — SLIDER + TOOLTIP + HANDLE
    # --------------------------------------------------------
    css_injected = """
        <style>
        /* Prevent page scrolling, but allow table scrolling */
        html, body {
            overflow-x: hidden !important;
            overflow-y: hidden !important;
            height: 100% !important;
            min-height: 100% !important;
        }
        
        /* Support table scrolling - Dash handles sticky via DataTable props */
        #crude-quality-table .dash-table-container,
        #yield-volume-table .dash-table-container {
            position: relative !important;
            overflow-x: auto !important;
        }
        
        #crude-quality-table .dash-table-container .dash-spreadsheet-container,
        #yield-volume-table .dash-table-container .dash-spreadsheet-container {
            overflow-x: auto !important;
            overflow-y: auto !important;
        }
        
        #crude-quality-table table,
        #yield-volume-table table {
            border-collapse: separate !important;
            border-spacing: 0 !important;
            width: 100% !important;
        }
        
        /* Ensure proper table cell borders and spacing */
        #crude-quality-table td,
        #crude-quality-table th,
        #yield-volume-table td,
        #yield-volume-table th {
            border: 1px solid #E6E6E6 !important;
        }
        
        /* Remove top border for empty country cells to create grouping effect */
        #crude-quality-table tbody tr td:first-child:empty,
        #yield-volume-table tbody tr td:first-child:empty {
            border-top: none !important;
        }
        
        /* Ensure table rows have consistent spacing */
        #crude-quality-table tbody tr,
        #yield-volume-table tbody tr {
            height: auto !important;
        }
        
        /* Ensure sticky columns maintain proper background */
        #crude-quality-table .dash-table-container table thead tr th:first-child,
        #crude-quality-table .dash-table-container table tbody tr td:first-child,
        #yield-volume-table .dash-table-container table thead tr th:first-child,
        #yield-volume-table .dash-table-container table tbody tr td:first-child {
            background-color: white !important;
        }
        
        #crude-quality-table .dash-table-container table thead tr th:nth-child(2),
        #crude-quality-table .dash-table-container table tbody tr td:nth-child(2),
        #yield-volume-table .dash-table-container table thead tr th:nth-child(2),
        #yield-volume-table .dash-table-container table tbody tr td:nth-child(2) {
            background-color: white !important;
        }
        
        /* Ensure proper border rendering */
        #crude-quality-table table,
        #yield-volume-table table {
            border-collapse: separate !important;
            border-spacing: 0 !important;
        }
        
        /* === Left Handle: flat left, round right === */
        .rc-slider-handle-1 {
            width: 10px !important;
            height: 14px !important;
            background: #FFFFFF !important;
            border: 2px solid #6E6E6E !important;
            border-radius: 0 7px 7px 0 !important;  /* D faces right */
            margin-top: -6px !important;
            box-shadow: none !important;
        }

        /* === Right Handle: flat right, round left === */
        .rc-slider-handle-2 {
            width: 10px !important;
            height: 14px !important;
            background: #FFFFFF !important;
            border: 2px solid #6E6E6E !important;
            border-radius: 7px 0 0 7px !important;  /* D faces left */
            margin-top: -6px !important;
            box-shadow: none !important;
        }

        .rc-slider-handle {
            width: 10px !important;
            height: 14px !important;

            background-color: #FFFFFF !important;
            border: 2px solid #6E6E6E !important;

            margin-top: -6px !important;
            box-shadow: none !important;
            cursor: pointer !important;
        }

        .rc-slider-handle-1 {
            border-radius: 7px 0 0 7px !important;
        }
        .rc-slider-handle-2 {
            border-radius: 0 7px 7px 0 !important;
        }

        /* Hover */
        .rc-slider-handle:hover {
            border-color: #4D4D4D !important;
        }

        /* Active press */
        .rc-slider-handle:active {
            border-color: #3A3A3A !important;
        }

        .rc-slider-track,
        .rc-slider-track-1,
        .rc-slider-track-2,
        div[class*="rc-slider-track"] {
            background: #6E6E6E !important;
            height: 4px !important;
        }

        .rc-slider-rail {
            background: #D3D3D3 !important;
            height: 4px !important;
        }

        /* Tooltip */
        .rc-slider-tooltip-inner {
            background: #ffffff !important;
            color: black !important;
            border: 1px solid #999 !important;
        }

        /* Dropdown Styling */
        .Select-control {
            font-size: 12px !important;
            height: 22px !important;
            min-height: 22px !important;
            border-radius: 0 !important;
        }
        
        .Select-value-label {
            font-size: 12px !important;
            line-height: 20px !important;
            color: rgb(27, 54, 93) !important;
        }
        
        .Select-input {
            font-size: 12px !important;
            height: 20px !important;
            line-height: 20px !important;
            color: rgb(27, 54, 93) !important;
        }
        
        .Select-input > input {
            font-size: 12px !important;
            line-height: 20px !important;
            color: rgb(27, 54, 93) !important;
        }
        
        .Select-menu-outer {
            font-size: 12px !important;
            border-radius: 0 !important;
        }
        
        .Select-option {
            font-size: 12px !important;
            padding: 4px 10px !important;
        }
        
        .Select-placeholder {
            font-size: 12px !important;
            line-height: 20px !important;
            color: rgb(27, 54, 93) !important;
        }
        
        .Select--single > .Select-control .Select-value {
            font-size: 12px !important;
            line-height: 20px !important;
            color: rgb(27, 54, 93) !important;
        }
        
        .Select--single > .Select-control .Select-value .Select-value-label {
            font-size: 12px !important;
            line-height: 20px !important;
            color: rgb(27, 54, 93) !important;
        }
        
        #x-axis-dropdown .Select-control,
        #y-axis-dropdown .Select-control,
        #bubble-size-dropdown .Select-control {
            font-size: 12px !important;
            height: 22px !important;
            min-height: 22px !important;
            border-radius: 0 !important;
        }
        
        #x-axis-dropdown .Select-value-label,
        #y-axis-dropdown .Select-value-label,
        #bubble-size-dropdown .Select-value-label {
            font-size: 12px !important;
            line-height: 20px !important;
            color: rgb(27, 54, 93) !important;
        }
        
        #x-axis-dropdown .Select-input,
        #y-axis-dropdown .Select-input,
        #bubble-size-dropdown .Select-input {
            height: 20px !important;
            line-height: 20px !important;
            color: rgb(27, 54, 93) !important;
        }
        
        #x-axis-dropdown .Select-input > input,
        #y-axis-dropdown .Select-input > input,
        #bubble-size-dropdown .Select-input > input {
            color: rgb(27, 54, 93) !important;
        }
        
        /* Force all dropdown menu items to use Arial font and proper formatting */
        .Select-menu-outer *,
        .Select-menu *,
        .Select-option *,
        div[id*="dropdown"] .Select-menu-outer *,
        div[id*="dropdown"] .Select-menu * {
            font-family: Arial, Helvetica, sans-serif !important;
            font-size: 12px !important;
        }
        
        /* Ensure dropdown menu items are properly styled */
        .Select-menu-outer .Select-option,
        .Select-menu .Select-option,
        div[id*="dropdown"] .Select-menu-outer .Select-option {
            font-family: Arial, Helvetica, sans-serif !important;
            font-size: 12px !important;
            padding: 6px 10px !important;
            color: #000000 !important;
            background-color: #fff !important;
            line-height: 1.5 !important;
            white-space: nowrap !important;
        }
        
        .Select-menu-outer .Select-option:hover,
        .Select-menu .Select-option:hover {
            background-color: #f0f0f0 !important;
            color: #000000 !important;
        }
        
        .Select-menu-outer .Select-option.is-selected,
        .Select-menu .Select-option.is-selected {
            background-color: #e6f3ff !important;
            color: #000000 !important;
        }
        
        /* Range input fields - show as text by default, input box on hover */
        #x-range-min-input,
        #x-range-max-input,
        #y-range-min-input,
        #y-range-max-input,
        #bubble-range-min-input,
        #bubble-range-max-input {
            border: none !important;
            background: transparent !important;
            padding: 0 !important;
            font-size: 12px !important;
            color: #1b365d !important;
            width: auto !important;
            min-width: 150px !important;
            max-width: 80px !important;
            height: 18px !important;
            line-height: 18px !important;
            outline: none !important;
            box-shadow: none !important;
            top: 0 !important;
            vertical-align: top !important;
            margin: 0 !important;
        }
        
        #x-range-min-input,
        #y-range-min-input,
        #bubble-range-min-input {
            left: 0 !important;
            text-align: left !important;
        }
        
        #x-range-max-input,
        #y-range-max-input,
        #bubble-range-max-input {
            text-align: right !important;
            float: right !important;
            margin-right: 0 !important;
            padding-right: 0 !important;
        }
        
        /* Ensure text and number inputs have same styling */
        #x-range-min-input[type="text"],
        #x-range-min-input[type="number"],
        #x-range-max-input[type="text"],
        #x-range-max-input[type="number"],
        #y-range-min-input[type="text"],
        #y-range-min-input[type="number"],
        #y-range-max-input[type="text"],
        #y-range-max-input[type="number"],
        #bubble-range-min-input[type="text"],
        #bubble-range-min-input[type="number"],
        #bubble-range-max-input[type="text"],
        #bubble-range-max-input[type="number"] {
            vertical-align: top !important;
            margin: 0 !important;
            display: inline-block !important;
        }
        
        #x-range-min-input:hover,
        #x-range-max-input:hover,
        #y-range-min-input:hover,
        #y-range-max-input:hover,
        #bubble-range-min-input:hover,
        #bubble-range-max-input:hover {
            border: 1px solid #ccc !important;
            background: #ffffff !important;
            padding: 1px 3px !important;
        }
        
        #x-range-min-input:focus,
        #x-range-max-input:focus,
        #y-range-min-input:focus,
        #y-range-max-input:focus,
        #bubble-range-min-input:focus,
        #bubble-range-max-input:focus {
            border: 1px solid #999 !important;
            background: #ffffff !important;
            padding: 1px 3px !important;
        }
        
        /* Ensure slider containers align with inputs on both sides */
        div[id*="range-slider"] {
            margin-left: 0 !important;
            padding-left: 0 !important;
            margin-right: 0 !important;
            padding-right: 0 !important;
        }
        
        /* Ensure RangeSlider component has no margin/padding */
        .rc-slider {
            margin-left: 0 !important;
            padding-left: 0 !important;
            margin-right: 0 !important;
            padding-right: 0 !important;
        }
        
        /* Ensure slider track aligns properly */
        .rc-slider-rail {
            margin-left: 0 !important;
            margin-right: 0 !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }
        
        /* Ensure slider wrapper has proper box-sizing */
        .rc-slider {
            width: 100% !important;
            box-sizing: border-box !important;
        }
        
        /* Ensure input container has no right padding/margin for alignment */
        div:has(#x-range-min-input),
        div:has(#y-range-min-input),
        div:has(#bubble-range-min-input) {
            margin-right: 0 !important;
            padding-right: 0 !important;
        }

        </style>
        """

    # Inject CSS into index_string
    dash_app.index_string = f"""
    <!DOCTYPE html>
    <html>
        <head>
            {{%metas%}}
            <title>Crude Quality Dashboard</title>
            {{%favicon%}}
            {{%css%}}
            {css_injected}
        </head>
        <body>
            {{%app_entry%}}
            <footer>
                {{%config%}}
                {{%scripts%}}
                {{%renderer%}}
            </footer>
        </body>
    </html>
    """

    # Layout + callbacks
    dash_app.layout = create_layout(dash_app)
    register_callbacks(dash_app)

    return dash_app


# ===================================
# CALLBACKS
# ===================================
def register_callbacks(dash_app, server=None):

    @dash_app.callback(
        [
            Output('crude-quality-table', 'columns'),
            Output('crude-quality-table', 'data')
        ],
        Input('current-submenu', 'data'),
        prevent_initial_call=False
    )
    def update_quality_table(current_submenu):
        """Load and update the Crudes Compared by Quality table when page is active"""
        if current_submenu != 'crude-quality':
            return [], []
        
        try:
            # Load quality table data
            quality_df = load_crude_quality_table()
            
            if quality_df.empty:
                return [], []
            
            # Find column IDs for Country and CrudeOil for sticky positioning
            country_col_id = None
            crudeoil_col_id = None
            quality_column_info = _get_df_metadata(quality_df, "column_info")
            if quality_column_info:
                for info in quality_column_info:
                    if info.get('sub') == 'Country':
                        country_col_id = info.get('id')
                    elif info.get('sub') == 'CrudeOil':
                        crudeoil_col_id = info.get('id')
            # Fallback: check column names directly
            if not country_col_id:
                for col in quality_df.columns:
                    if col == 'Country' or (isinstance(col, str) and col.startswith('Country')):
                        country_col_id = col
                        break
            if not crudeoil_col_id:
                for col in quality_df.columns:
                    if col == 'CrudeOil' or (isinstance(col, str) and col.startswith('CrudeOil')):
                        crudeoil_col_id = col
                        break
            
            # Create columns and data
            columns = create_grouped_columns(quality_df)
            data = process_quality_table_data(quality_df, country_col_id, crudeoil_col_id)
            
            return columns, data
        except Exception as e:
            print(f"Error loading quality table data: {e}")
            import traceback
            traceback.print_exc()
            return [], []
    
    @dash_app.callback(
        [
            Output('yield-volume-table', 'columns'),
            Output('yield-volume-table', 'data')
        ],
        Input('current-submenu', 'data'),
        prevent_initial_call=False
    )
    def update_yield_table(current_submenu):
        """Load and update the Crudes Compared by Product Yield table when page is active"""
        if current_submenu != 'crude-quality':
            return [], []
        
        try:
            # Load yield table data
            yield_df = load_yield_volume_table()
            
            if yield_df.empty:
                return [], []
            
            # Create columns and data
            columns = create_grouped_columns(yield_df)
            data = process_yield_table_data(yield_df)
            
            return columns, data
        except Exception as e:
            print(f"Error loading yield table data: {e}")
            import traceback
            traceback.print_exc()
            return [], []

    @dash_app.callback(
        [
            Output('crude-filter-checklist-items', 'options'),
            Output('crude-filter-checklist-items', 'value'),
            Output('crude-filter-checklist-all', 'value')
        ],
        [
            Input('crude-filter-checklist-all', 'value'),
            Input('crude-filter-checklist-items', 'value')
        ],
        prevent_initial_call=False
    )
    def update_crude_filter_list(all_selected, current_selected):
        # Load crossplot data to get all crude oil names (preferred source)
        crude_list = []
        try:
            df = load_crossplot_data()
            print(f"DEBUG: Loaded crossplot data for crude filter, shape: {df.shape}")
            if not df.empty and "CrudeOil" in df.columns:
                crude_list = df["CrudeOil"].dropna().astype(str).str.strip()
                crude_list = crude_list[crude_list != ''].unique().tolist()
                crude_list = sorted(crude_list)  # Sort alphabetically
                print(f"DEBUG: Extracted {len(crude_list)} unique crude oils from crossplot data")
        except Exception as e:
            print(f"Error loading crossplot data for crude filter: {e}")
            import traceback
            traceback.print_exc()
        
        # Fallback to quality table if crossplot data is empty
        if not crude_list:
            print("DEBUG: Falling back to quality table data")
            try:
                quality_df = load_crude_quality_table()
                if not quality_df.empty:
                    # Find CrudeOil column
                    crudeoil_col = None
                    if 'CrudeOil' in quality_df.columns:
                        crudeoil_col = 'CrudeOil'
                    else:
                        # Check metadata for CrudeOil column ID
                        quality_column_info = _get_df_metadata(quality_df, "column_info")
                        if quality_column_info:
                            for info in quality_column_info:
                                if info.get('sub') == 'CrudeOil':
                                    crudeoil_col = info.get('id')
                                    break
                    
                    if crudeoil_col and crudeoil_col in quality_df.columns:
                        crude_list = quality_df[crudeoil_col].dropna().astype(str).str.strip()
                        crude_list = crude_list[crude_list != ''].unique().tolist()
                        crude_list = sorted(crude_list)
                        print(f"DEBUG: Extracted {len(crude_list)} crude oils from quality_df")
            except Exception as e:
                print(f"Error loading quality table for crude filter: {e}")

        options = [{'label': crude, 'value': crude} for crude in crude_list]
        print(f"DEBUG: Created {len(options)} options for crude filter checklist")

        ctx = callback_context
        trigger = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered and len(ctx.triggered) > 0 else None

        # On initial load (no trigger), return all crudes selected
        if not trigger:
            print(f"DEBUG: Initial load - returning {len(crude_list)} crudes, all selected")
            return options, crude_list, ['all']

        if trigger == 'crude-filter-checklist-all':
            if all_selected and 'all' in all_selected:
                print(f"DEBUG: 'All' selected - returning all {len(crude_list)} crudes")
                return options, crude_list, ['all']
            print(f"DEBUG: 'All' deselected - returning empty selection")
            return options, [], []

        if trigger == 'crude-filter-checklist-items':
            if not current_selected:
                print(f"DEBUG: All items deselected")
                return options, [], []
            if len(current_selected) == len(crude_list):
                print(f"DEBUG: All items selected - checking 'All' checkbox")
                return options, current_selected, ['all']
            print(f"DEBUG: Partial selection - {len(current_selected)} of {len(crude_list)} selected")
            return options, current_selected, []

        # Default: return all selected
        print(f"DEBUG: Default return - all {len(crude_list)} crudes selected")
        return options, crude_list, ['all']

    @dash_app.callback(
        [
            Output('x-range-slider', 'min'),
            Output('x-range-slider', 'max'),
            Output('x-range-slider', 'value'),
            Output('x-range-slider', 'step'),
            Output('x-range-min-input', 'value'),
            Output('x-range-max-input', 'value')
        ],
        [Input('x-axis-dropdown', 'value')]
    )
    def update_x_slider(x_prop):
        if not x_prop:
            return 0, 100, [0, 100], 0.1, 0, 100
        
        # Load quality table data
        try:
            quality_df = load_crude_quality_table()
        except Exception as e:
            print(f"Error loading quality table for x slider: {e}")
            return 0, 100, [0, 100], 0.1, 0, 100
        
        if quality_df.empty or x_prop not in quality_df.columns:
            return 0, 100, [0, 100], 0.1, 0, 100
        
        quality_df[x_prop] = pd.to_numeric(quality_df[x_prop], errors="coerce")
        quality_df = quality_df.dropna(subset=[x_prop])
        
        if len(quality_df) == 0:
            return 0, 100, [0, 100], 0.1, 0, 100
        
        min_val = float(quality_df[x_prop].min())
        max_val = float(quality_df[x_prop].max())
        step = 0.1 if (max_val - min_val) > 10 else 0.01
        
        return min_val, max_val, [min_val, max_val], step, min_val, max_val

    @dash_app.callback(
        [
            Output('y-range-slider', 'min'),
            Output('y-range-slider', 'max'),
            Output('y-range-slider', 'value'),
            Output('y-range-slider', 'step'),
            Output('y-range-min-input', 'value'),
            Output('y-range-max-input', 'value')
        ],
        [Input('y-axis-dropdown', 'value')]
    )
    def update_y_slider(y_prop):
        if not y_prop:
            return 0, 100, [0, 100], 0.01, 0, 100
        
        # Load crossplot data
        try:
            df = load_crossplot_data()
        except Exception as e:
            print(f"Error loading crossplot data for y slider: {e}")
            return 0, 100, [0, 100], 0.01, 0, 100
        
        if df.empty:
            return 0, 100, [0, 100], 0.01, 0, 100
        
        # Filter for the selected property
        y_data = df[df['Property - Unit'] == y_prop].copy()
        if y_data.empty:
            return 0, 100, [0, 100], 0.01, 0, 100
        
        y_data['Value'] = pd.to_numeric(y_data['Value'], errors="coerce")
        y_data = y_data.dropna(subset=['Value'])
        
        if len(y_data) == 0:
            return 0, 100, [0, 100], 0.01, 0, 100
        
        min_val = float(y_data['Value'].min())
        max_val = float(y_data['Value'].max())
        step = 0.1 if (max_val - min_val) > 10 else 0.01
        
        return min_val, max_val, [min_val, max_val], step, min_val, max_val

    @dash_app.callback(
        [
            Output('bubble-range-slider', 'min'),
            Output('bubble-range-slider', 'max'),
            Output('bubble-range-slider', 'value'),
            Output('bubble-range-min-input', 'value'),
            Output('bubble-range-max-input', 'value')
        ],
        [Input('bubble-size-dropdown', 'value')]
    )
    def update_bubble_slider(bubble_prop):
        if not bubble_prop:
            return 0, 100, [0, 100], 0, 100
        
        # Load crossplot data
        try:
            df = load_crossplot_data()
        except Exception as e:
            print(f"Error loading crossplot data for bubble slider: {e}")
            return 0, 100, [0, 100], 0, 100
        
        if df.empty:
            return 0, 100, [0, 100], 0, 100
        
        # Filter for the selected property
        size_data = df[df['Property - Unit'] == bubble_prop].copy()
        if size_data.empty:
            return 0, 100, [0, 100], 0, 100
        
        size_data['Value'] = pd.to_numeric(size_data['Value'], errors="coerce").fillna(40)
        size_data = size_data.dropna(subset=['Value'])
        
        if len(size_data) == 0:
            return 0, 100, [0, 100], 0, 100
        
        min_val = 0
        max_val = int(size_data['Value'].max())
        
        return min_val, max_val, [min_val, max_val], min_val, max_val

    # Bidirectional sync: X-axis input fields <-> slider
    @dash_app.callback(
        [
            Output('x-range-slider', 'value', allow_duplicate=True),
            Output('x-range-min-input', 'value', allow_duplicate=True),
            Output('x-range-max-input', 'value', allow_duplicate=True)
        ],
        [
            Input('x-range-min-input', 'value'),
            Input('x-range-max-input', 'value'),
            Input('x-range-slider', 'value')
        ],
        prevent_initial_call=True
    )
    def sync_x_range(min_input, max_input, slider_value):
        ctx = callback_context
        if not ctx.triggered:
            return [0, 100], 0, 100
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'x-range-min-input' or trigger_id == 'x-range-max-input':
            # Input changed, update slider
            if min_input is not None and max_input is not None:
                return [min_input, max_input], min_input, max_input
        elif trigger_id == 'x-range-slider':
            # Slider changed, update inputs
            if slider_value:
                return slider_value, slider_value[0], slider_value[1]
        
        return [0, 100], 0, 100

    # Bidirectional sync: Y-axis input fields <-> slider
    @dash_app.callback(
        [
            Output('y-range-slider', 'value', allow_duplicate=True),
            Output('y-range-min-input', 'value', allow_duplicate=True),
            Output('y-range-max-input', 'value', allow_duplicate=True)
        ],
        [
            Input('y-range-min-input', 'value'),
            Input('y-range-max-input', 'value'),
            Input('y-range-slider', 'value')
        ],
        prevent_initial_call=True
    )
    def sync_y_range(min_input, max_input, slider_value):
        ctx = callback_context
        if not ctx.triggered:
            return [0, 100], 0, 100
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'y-range-min-input' or trigger_id == 'y-range-max-input':
            # Input changed, update slider
            if min_input is not None and max_input is not None:
                return [min_input, max_input], min_input, max_input
        elif trigger_id == 'y-range-slider':
            # Slider changed, update inputs
            if slider_value:
                return slider_value, slider_value[0], slider_value[1]
        
        return [0, 100], 0, 100

    # Bidirectional sync: Bubble size input fields <-> slider
    @dash_app.callback(
        [
            Output('bubble-range-slider', 'value', allow_duplicate=True),
            Output('bubble-range-min-input', 'value', allow_duplicate=True),
            Output('bubble-range-max-input', 'value', allow_duplicate=True)
        ],
        [
            Input('bubble-range-min-input', 'value'),
            Input('bubble-range-max-input', 'value'),
            Input('bubble-range-slider', 'value')
        ],
        prevent_initial_call=True
    )
    def sync_bubble_range(min_input, max_input, slider_value):
        ctx = callback_context
        if not ctx.triggered:
            return [0, 100], 0, 100
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'bubble-range-min-input' or trigger_id == 'bubble-range-max-input':
            # Input changed, update slider
            if min_input is not None and max_input is not None:
                return [int(min_input), int(max_input)], min_input, max_input
        elif trigger_id == 'bubble-range-slider':
            # Slider changed, update inputs
            if slider_value:
                return slider_value, slider_value[0], slider_value[1]
        
        return [0, 100], 0, 100

    @dash_app.callback(
        Output('crude-quality-chart', 'figure'),
        [
            Input("x-axis-dropdown", "value"),
            Input("y-axis-dropdown", "value"),
            Input("bubble-size-dropdown", "value"),
            Input("x-range-slider", "value"),
            Input("y-range-slider", "value"),
            Input("bubble-range-slider", "value"),
            Input('crude-filter-checklist-items', 'value'),
        ]
    )
    def update_crude_quality(x_col, y_col, size_col, x_range, y_range, size_range, selected_crudes):

        if not x_col or not y_col or not size_col:
            fig = go.Figure()
            fig.update_layout(
                title=dict(text="Crude Oils Compared by Quality", x=0.5, font=dict(color="#FF6600", size=20)),
                height=500, plot_bgcolor="white"
            )
            return fig

        # Load crossplot data from database
        try:
            df = load_crossplot_data()
        except Exception as e:
            print(f"Error loading crossplot data: {e}")
            import traceback
            traceback.print_exc()
            df = pd.DataFrame()
        
        if df.empty:
            fig = go.Figure()
            fig.update_layout(
                title=dict(text="Crude Oils Compared by Quality", x=0.5, font=dict(color="#FF6600", size=20)),
                height=500, plot_bgcolor="white"
            )
            return fig
        
        # Filter data for the three selected properties
        # x_col, y_col, size_col are in format "Property - Unit" (e.g., "Gravity-API at 60 F")
        x_data = df[df['Property - Unit'] == x_col].copy()
        y_data = df[df['Property - Unit'] == y_col].copy()
        size_data = df[df['Property - Unit'] == size_col].copy()
        
        # For each crude, calculate the average value for each property
        # Group by CrudeOil and calculate mean, rounded to 2 decimal places
        if not x_data.empty:
            x_data = x_data.groupby('CrudeOil').agg({
                'Value': lambda x: round(x.mean(), 2),
                'Country': 'first',
                'OPEC FSU OECD': 'first'
            }).reset_index()
        if not y_data.empty:
            y_data = y_data.groupby('CrudeOil').agg({
                'Value': lambda x: round(x.mean(), 2)
            }).reset_index()
        if not size_data.empty:
            size_data = size_data.groupby('CrudeOil').agg({
                'Value': lambda x: round(x.mean(), 2)
            }).reset_index()
        
        # Merge the three datasets on CrudeOil
        plot_df = pd.DataFrame()
        if not x_data.empty and not y_data.empty:
            plot_df = x_data[['CrudeOil', 'Country', 'OPEC FSU OECD', 'Value']].rename(columns={'Value': 'x_value'})
            plot_df = plot_df.merge(
                y_data[['CrudeOil', 'Value']].rename(columns={'Value': 'y_value'}),
                on='CrudeOil',
                how='inner'
            )
            if not size_data.empty:
                plot_df = plot_df.merge(
                    size_data[['CrudeOil', 'Value']].rename(columns={'Value': 'size_value'}),
                    on='CrudeOil',
                    how='left'
                )
            else:
                plot_df['size_value'] = 40  # Default size if no data
        else:
            # No data to plot
            fig = go.Figure()
            fig.update_layout(
                title=dict(text="Crude Oils Compared by Quality", x=0.5, font=dict(color="#FF6600", size=20)),
                height=500, plot_bgcolor="white"
            )
            return fig
        
        # Fill missing size values
        plot_df['size_value'] = plot_df['size_value'].fillna(40)
        
        # Convert to numeric
        plot_df['x_value'] = pd.to_numeric(plot_df['x_value'], errors="coerce")
        plot_df['y_value'] = pd.to_numeric(plot_df['y_value'], errors="coerce")
        plot_df['size_value'] = pd.to_numeric(plot_df['size_value'], errors="coerce").fillna(40)
        
        # Drop rows where x or y are NaN
        plot_df = plot_df.dropna(subset=['x_value', 'y_value'])
        
        # Apply range filters
        plot_df = plot_df[
            (plot_df['x_value'] >= x_range[0]) & (plot_df['x_value'] <= x_range[1]) &
            (plot_df['y_value'] >= y_range[0]) & (plot_df['y_value'] <= y_range[1]) &
            (plot_df['size_value'] >= size_range[0]) & (plot_df['size_value'] <= size_range[1])
        ]
        
        # Filter by selected crudes
        if selected_crudes and len(selected_crudes) > 0:
            plot_df = plot_df[plot_df['CrudeOil'].isin(selected_crudes)]
        
        if len(plot_df) == 0:
            fig = go.Figure()
            fig.update_layout(
                title=dict(text="Crude Oils Compared by Quality", x=0.5, font=dict(color="#FF6600", size=20)),
                xaxis=dict(title=x_col, range=x_range, showgrid=False),
                yaxis=dict(title=y_col, range=y_range, showgrid=False),
                height=500, plot_bgcolor="white"
            )
            return fig
        
        # Map region from OPEC FSU OECD column
        plot_df['Region'] = plot_df['OPEC FSU OECD'].fillna('Others').str.lower()
        # Map to standard region names
        region_name_map = {
            'opec': 'OPEC',
            'fsu': 'FSU',
            'oecd': 'OECD',
            'others': 'Others',
            'null': 'Null',
            '': 'Others',
            None: 'Others'
        }
        plot_df['Region'] = plot_df['Region'].map(region_name_map).fillna('Others')
        
        color_map = {
            'Null': '#313B49',
            'FSU': '#0075A8',
            'OECD': '#595959',
            'OPEC': '#7986CB',
            'Others': '#FE5000'
        }

        fig = go.Figure()

        for region in plot_df["Region"].unique():
            grp = plot_df[plot_df["Region"] == region]
            if len(grp) == 0:
                continue
            custom = grp['size_value'].apply(lambda x: f"{x:,.0f}")
            fig.add_trace(go.Scatter(
                x=grp['x_value'], y=grp['y_value'],
                mode="markers",
                text=grp["CrudeOil"],
                customdata=custom,
                marker=dict(
                    size=np.sqrt(grp['size_value']) * 0.8,
                    color=color_map.get(region, "#444"),
                    opacity=0.8,
                    line=dict(width=1, color="white")
                ),
                hovertemplate=(
                    f"<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#787878;font-weight:normal;font-style:normal;text-decoration:none;\">Crude:</span> "
                    f"<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#000000;font-weight:bold;font-style:normal;text-decoration:none;\">%{{text}}</span><br>"
                    f"<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#787878;font-weight:normal;font-style:normal;text-decoration:none;\">{x_col}:</span> "
                    f"<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#000000;font-weight:bold;font-style:normal;textDecoration:none;\">%{{x:.1f}}</span><br>"
                    f"<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#787878;font-weight:normal;font-style:normal;text-decoration:none;\">{y_col}:</span> "
                    f"<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#000000;font-weight:bold;font-style:normal;text-decoration:none;\">%{{y:.2f}}</span><br>"
                    f"<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#787878;font-weight:normal;font-style:normal;text-decoration:none;\">{size_col}:</span> "
                    f"<span style=\"font-family:'Tahoma',arial,sans-serif;font-size:13px;color:#000000;font-weight:bold;font-style:normal;text-decoration:none;\">%{{customdata}}</span><extra></extra>"
                )
            ))

        # Set fixed axis ranges
        if "API" in x_col:
            x_axis_range = [10.0, 65.0]  # Reversed for API
            x_axis_autorange = False
        else:
            x_axis_range = [10.0, 65.0]
            x_axis_autorange = False
        
        y_axis_range = [0.00, 4.50]

        fig.update_layout(
            title=dict(text="Crude Oils Compared by Quality", x=0.5, font=dict(color="#FF6600", size=20)),
            xaxis=dict(
                title=x_col,
                range=x_axis_range,
                autorange=x_axis_autorange,
                dtick=5,
                tickmode="linear",
                showgrid=False,
                showline=True,
                linecolor="black",
                mirror=True
            ),
            yaxis=dict(
                title=y_col,
                range=y_axis_range,
                dtick=0.5,
                tickmode="linear",
                showgrid=False,
                showline=True,
                linecolor="black",
                mirror=True
            ),
            height=500,
            width=1000,
            autosize=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            showlegend=False,
            margin=dict(l=60, r=10, t=50, b=50),
            hoverlabel=dict(
                bgcolor="white",
                bordercolor="#999999",
                font_size=12,
                font_family='"Benton Sans Low-DPI", Arial, Helvetica, sans-serif',
                font_color="black",
                align="left"
            )
        )

        return fig