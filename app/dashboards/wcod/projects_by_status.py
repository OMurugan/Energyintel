"""
Projects by Status View
Total Capacity Additions from 2025 Q1 to 2029 Q4
"""
from dash import dcc, html, Input, Output, State, callback, ALL, MATCH, dash_table
import dash
import plotly.graph_objects as go
import pandas as pd
import os
import re
import json
from core.data_helpers import execute_query
import traceback


def load_treemap_data():
    """Load treemap data from the database using a pivot/unpivot query.
    Returns a DataFrame with columns: Play Type, Project Status, Region, Production Additions, max Q, min Q
    """
    try:
        print("DEBUG: load_treemap_data() called")
        query = """
            WITH unpvt AS (
                SELECT 
                    a.play_type,
                    a.project_status,
                    c.region,
                    SPLIT_PART(qcol, '_', 1)::INT AS year_num,

                    RIGHT(qcol, 1)::INT AS quarter_num,

                    val AS production_additions
                FROM fact_upstream_project_tracker a
                LEFT JOIN fact_upstream_tracker_prod_estimates est
                    ON a.project_id = est.project_id
                LEFT JOIN dim_country c
                    ON a.country_id = c.dim_country_id

                CROSS JOIN LATERAL (
                    VALUES
                        ('2025_Q1', est."2025_Q1"), ('2025_Q2', est."2025_Q2"),
                        ('2025_Q3', est."2025_Q3"), ('2025_Q4', est."2025_Q4"),

                        ('2026_Q1', est."2026_Q1"), ('2026_Q2', est."2026_Q2"),
                        ('2026_Q3', est."2026_Q3"), ('2026_Q4', est."2026_Q4"),

                        ('2027_Q1', est."2027_Q1"), ('2027_Q2', est."2027_Q2"),
                        ('2027_Q3', est."2027_Q3"), ('2027_Q4', est."2027_Q4"),

                        ('2028_Q1', est."2028_Q1"), ('2028_Q2', est."2028_Q2"),
                        ('2028_Q3', est."2028_Q3"), ('2028_Q4', est."2028_Q4"),

                        ('2029_Q1', est."2029_Q1"), ('2029_Q2', est."2029_Q2"),
                        ('2029_Q3', est."2029_Q3"), ('2029_Q4', est."2029_Q4")
                ) AS t(qcol, val)

                WHERE a.include = TRUE
            ),

            ranked AS (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY play_type, project_status, region
                        ORDER BY year_num DESC, quarter_num DESC
                    ) AS rn_max,

                    ROW_NUMBER() OVER (
                        PARTITION BY play_type, project_status, region
                        ORDER BY year_num ASC, quarter_num ASC
                    ) AS rn_min
                FROM unpvt
                WHERE production_additions IS NOT NULL
            )

            SELECT
                play_type AS "Play Type",
                project_status AS "Project Status",
                region AS "Region",

                -- Max Q
                CONCAT(
                    MAX(CASE WHEN rn_max = 1 THEN year_num END),
                    '-',
                    MAX(CASE WHEN rn_max = 1 THEN CONCAT('Q', quarter_num) END)
                ) AS "max Q",

                -- Min Q
                CONCAT(
                    MAX(CASE WHEN rn_min = 1 THEN year_num END),
                    '-',
                    MAX(CASE WHEN rn_min = 1 THEN CONCAT('Q', quarter_num) END)
                ) AS "min Q",

                SUM(production_additions) AS "Production Additions"

            FROM ranked
            GROUP BY play_type, project_status, region
            ORDER BY region, play_type, project_status;

        """

        # Execute query and log result count for debugging
        try:
            results = execute_query(query)
            row_count = len(results) if results else 0
            print(f"DEBUG: load_treemap_data() - execute_query returned {row_count} rows")
        except Exception as _e:
            print(f"ERROR: load_treemap_data() - execute_query raised: {_e}")
            raise

        df = pd.DataFrame(results) if results else pd.DataFrame()

        # Clean column names
        df.columns = df.columns.str.strip()
        # Map common lowercase column names to the exact display names expected by treemap code
        column_mapping = {}
        for col in df.columns:
            lower = col.lower().strip()
            if lower in ('play_type', 'play type'):
                column_mapping[col] = 'Play Type'
            elif lower in ('project_status', 'project status'):
                column_mapping[col] = 'Project Status'
            elif lower in ('region',):
                column_mapping[col] = 'Region'
            elif lower in ('production_additions', 'production additions', 'value'):
                column_mapping[col] = 'Production Additions'
            elif lower in ('max q', 'max_q'):
                column_mapping[col] = 'max Q'
            elif lower in ('min q', 'min_q'):
                column_mapping[col] = 'min Q'

        if column_mapping:
            df = df.rename(columns=column_mapping)

        # Ensure Production Additions is numeric
        if 'Production Additions' in df.columns:
            df['Production Additions'] = pd.to_numeric(df['Production Additions'], errors='coerce').fillna(0)

        # Normalize string columns to avoid mismatches due to whitespace/case
        for col in ['Play Type', 'Project Status', 'Region']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

        return df
    except Exception as e:
        traceback.print_exc()
        return pd.DataFrame()


def load_table_data():
    """Load project details table data from database query (fallback to empty DataFrame)."""
    try:
        query = """
        SELECT
            a.project_name AS "Project Name",
            a.likely_goahead,
            c.country_long_name AS Country,
            c.region AS Region,
            CASE
                WHEN c.opec_grp = 'opec' OR c.opec_grp = 'opec_plus' THEN 'Opec-Plus'
                ELSE 'Non-Opec-Plus'
            END AS Opec_group,
            a.field_type,
            a.field,
            a.play_type,
            a.hydrocarbon AS Hydrocarbon,
            cr.crude_name AS "Associated Crude",
            a.depth AS Depth,
            op.company_name AS Operator,
            p1.company_name AS Partner1,
            p2.company_name AS Partner2,
            p3.company_name AS Partner3,
            p4.company_name AS Partner4,
            p5.company_name AS Partner5,
            yr.year AS "First Oil Year",
            a.sanctioned AS Sanctioned,
            a.external_comments AS Comments,
            a.project_status AS "Project Status",
            a.reserves_gas_mmboe AS "Gas Reserves (mmboe)",
            a.reserves_liquids_mmbbl AS "Liquids Reserves (mmbbl)",
            (
                COALESCE(
                    NULLIF(SPLIT_PART(a.reserves_gas_mmboe, '-', 1), '')::numeric,
                    0
                )
                +
                COALESCE(
                    NULLIF(SPLIT_PART(a.reserves_liquids_mmbbl, '-', 1), '')::numeric,
                    0
                )
            ) AS "Total Reserves (mmboe)",
            a.api_cat AS API,
            a.sulfur_cat AS Sulfur,
            a.operator_pc AS "Operator Share %",
            a.partner1_pc AS "Partner1 Share %",
            a.partner2_pc AS "Partner2 Share %",
            a.partner3_pc AS "Partner3 Share %",
            a.partner4_pc AS "Partner4 Share %",
            a.partner5_pc AS "Partner5 Share %",
            est."2024_Q1",
            est."2024_Q2",
            est."2024_Q3",
            est."2024_Q4",
            est."2025_Q1",
            est."2025_Q2",
            est."2025_Q3",
            est."2025_Q4",
            est."2026_Q1",
            est."2026_Q2",
            est."2026_Q3",
            est."2026_Q4",
            est."2027_Q1",
            est."2027_Q2",
            est."2027_Q3",
            est."2027_Q4",
            est."2028_Q1",
            est."2028_Q2",
            est."2028_Q3",
            est."2028_Q4",
            est."2029_Q1",
            est."2029_Q2",
            est."2029_Q3",
            est."2029_Q4"
        FROM fact_upstream_project_tracker a
        LEFT JOIN fact_upstream_tracker_prod_estimates est 
            ON a.project_id = est.project_id
        LEFT JOIN dim_country c 
            ON a.country_id = c.dim_country_id
        LEFT JOIN dim_company op 
            ON a.operator_id = op.company_id
        LEFT JOIN dim_company p1 
            ON a.partner1_id = p1.company_id
        LEFT JOIN dim_company p2 
            ON a.partner2_id = p2.company_id
        LEFT JOIN dim_company p3 
            ON a.partner3_id = p3.company_id
        LEFT JOIN dim_company p4 
            ON a.partner4_id = p4.company_id
        LEFT JOIN dim_company p5 
            ON a.partner5_id = p5.company_id
        LEFT JOIN (
            SELECT 
                project_id,
                MIN(EXTRACT(YEAR FROM period)) AS year
            FROM fact_upstream_tracker_prod_estimates_incremental
            WHERE value IS NOT NULL 
            GROUP BY project_id
        ) yr ON yr.project_id = a.project_id
        LEFT JOIN dim_crude cr 
            ON cr.dim_crude_id = a.crude_id
        WHERE a.include = TRUE
        ORDER BY a.project_name;
        """

        results = execute_query(query)
        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results)
        column_mapping = {
            'Country': 'Country',
            'country': 'Country',
            'Region': 'Region',
            'region': 'Region',
            'Opec_group': 'Opec_group',
            'opec_group': 'Opec_group',
            'field_type': 'field_type',
            'Field Type': 'field_type',
            'field': 'field',
            'Field': 'field',
            # Normalize to display names expected by treemap code
            'play_type': 'Play Type',
            'Play Type': 'Play Type',
            'project_status': 'Project Status',
            'Project Status': 'Project Status',
            'hydrocarbon': 'Hydrocarbon',
            'Hydrocarbon': 'Hydrocarbon',
            'depth': 'Depth',
            'Depth': 'Depth',
            'operator': 'Operator',
            'Operator': 'Operator',
            'partner1': 'Partner1',
            'Partner1': 'Partner1',
            'partner2': 'Partner2',
            'Partner2': 'Partner2',
            'partner3': 'Partner3',
            'Partner3': 'Partner3',
            'partner4': 'Partner4',
            'Partner4': 'Partner4',
            'partner5': 'Partner5',
            'Partner5': 'Partner5',
            'sanctioned': 'Sanctioned',
            'Sanctioned': 'Sanctioned',
            'comments': 'Comments',
            'Comments': 'Comments',
            'api': 'API',
            'API': 'API',
            'sulfur': 'Sulfur',
            'Sulfur': 'Sulfur',
            'likely_goahead': 'likely_goahead'
        }

        df = df.rename(columns=column_mapping)
        df = df.fillna('')
        return df
    except Exception as e:
        traceback.print_exc()
        return pd.DataFrame()


# NOTE: Removed CSV-based KPI loader. KPI values are calculated dynamically
# from the treemap / project query results (see `load_treemap_data` and
# KPI aggregation logic in `update_tables`).


def create_treemap_figure(df=None, region_filter=None, likely_filter=None, table_df=None, selected_label=None):
    """Create treemap visualization for projects by status"""
    # Normalize selection to a unique key (dict with 'key') so only one block stays active
    selected_key = None
    if isinstance(selected_label, dict):
        key_val = selected_label.get("key") or selected_label.get("label")
        if key_val:
            selected_key = str(key_val).strip()
    elif selected_label is not None:
        selected_key = str(selected_label).strip()
    
    if df is None or df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No project data available.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#666666")
        )
        fig.update_layout(
            title=dict(text="Total Capacity Additions 2025 Q1 - 2029 Q4", x=0.5, xanchor="center"),
            height=700,
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=10, r=10, t=60, b=10)
        )
        return fig
    
    filtered_df = df.copy()
    
    # Normalize Region column to ensure consistent comparison
    if "Region" in filtered_df.columns:
        filtered_df["Region"] = filtered_df["Region"].astype(str).str.strip()
    
    print(f"DEBUG: create_treemap_figure - region_filter={region_filter}, type={type(region_filter)}")
    print(f"DEBUG: create_treemap_figure - unique regions in df before filter: {filtered_df['Region'].unique().tolist() if 'Region' in filtered_df.columns else 'N/A'}")
    
    # Apply region filter (now handles list of regions)
    if region_filter:
        if isinstance(region_filter, list):
            if len(region_filter) > 0:
                # Normalize region filter values for consistent comparison
                normalized_filter = [str(r).strip() for r in region_filter]
                print(f"DEBUG: create_treemap_figure - normalized_filter={normalized_filter}")
                # Filter to selected regions (keep rows where Region is in the filter list)
                filtered_df = filtered_df[filtered_df["Region"].isin(normalized_filter)]
                print(f"DEBUG: create_treemap_figure - unique regions in df after filter: {filtered_df['Region'].unique().tolist() if 'Region' in filtered_df.columns and not filtered_df.empty else 'N/A'}")
        elif region_filter != "(All)":
            # Single region (backward compatibility)
            normalized_single = str(region_filter).strip()
            filtered_df = filtered_df[filtered_df["Region"] == normalized_single]
    
    # Apply likely filter by joining with table data if available
    if likely_filter and table_df is not None:
        # Normalize checklist selection (handle 'All' sentinel)
        if isinstance(likely_filter, list):
            if 'All' in likely_filter and len(likely_filter) > 1:
                likely_filter = [v for v in likely_filter if v != 'All']
            if not likely_filter or (len(likely_filter) == 1 and likely_filter[0] == 'All'):
                likely_filter = None

        if likely_filter is not None:
            # Find likely column name in table (flexible matching)
            likely_col = None
            for col in table_df.columns:
                col_lower = col.lower()
                if 'likely' in col_lower and ('go' in col_lower or 'ahead' in col_lower):
                    likely_col = col
                    break

            if likely_col is not None:
                col_upper = table_df[likely_col].astype(str).str.upper()
                # Build mask from selected filter values (support 'Yes'/'Y', 'No'/'N', 'Uncertain', blank)
                selected_values = likely_filter if isinstance(likely_filter, list) else [likely_filter]
                mask = pd.Series(False, index=col_upper.index)
                for v in selected_values:
                    v_str = str(v).strip()
                    v_up = v_str.upper()
                    if v_up == 'ALL' or v == 'All':
                        mask |= pd.Series(True, index=col_upper.index)
                    elif v_up == '' or v_str.lower() == 'blank':
                        mask |= (col_upper == '')
                    elif v_up.startswith('Y') or v_up == 'YES':
                        mask |= col_upper.str.startswith('Y')
                    elif v_up.startswith('N'):
                        mask |= col_upper.str.startswith('N')
                    elif v_up.startswith('UNCERT') or v_up.startswith('U'):
                        mask |= col_upper.str.startswith('U')

                matching_projects = table_df[mask]
                # Debug: log matching counts to help diagnose empty treemap issues
                try:
                    print(f"DEBUG: likely_filter selected_values={selected_values}")
                    print(f"DEBUG: matching_projects count={len(matching_projects)}")
                except Exception:
                    pass

                if not matching_projects.empty:
                    # Create a set of unique combinations from matching projects
                    matching_combos = set()
                    for _, row in matching_projects.iterrows():
                        combo = (
                            row.get("Region", ""),
                            row.get("Play Type", ""),
                            row.get("Project Status", "")
                        )
                        matching_combos.add(combo)

                    try:
                        print(f"DEBUG: matching_combos count={len(matching_combos)}")
                    except Exception:
                        pass

                    # Filter treemap data to only include matching combinations
                    def matches_combo(row):
                        combo = (
                            str(row.get("Region", "")),
                            str(row.get("Play Type", "")),
                            str(row.get("Project Status", ""))
                        )
                        return combo in matching_combos

                    before_count = len(filtered_df)
                    filtered_df = filtered_df[filtered_df.apply(matches_combo, axis=1)]
                    after_count = len(filtered_df)
                    try:
                        print(f"DEBUG: filtered_df reduced from {before_count} to {after_count} by likely filter")
                    except Exception:
                        pass
    
    if filtered_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data matches the selected filters.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#666666")
        )
        fig.update_layout(
            title=dict(text="Total Capacity Additions 2025 Q1 - 2029 Q4", x=0.5, xanchor="center"),
            height=700,
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=10, r=10, t=60, b=10)
        )
        return fig
    
    # Get unique regions and order them according to REGION_ORDER
    unique_regions = filtered_df["Region"].dropna().unique().tolist()
    
    # Order regions according to REGION_ORDER (keep only regions that exist in data)
    ordered_regions = [r for r in REGION_ORDER if r in unique_regions]
    # Add any regions not in REGION_ORDER at the end
    remaining_regions = [r for r in unique_regions if r not in REGION_ORDER]
    ordered_regions.extend(sorted(remaining_regions))
    
    # Create color map for regions using predefined colors
    color_map = {}
    for region in ordered_regions:
        color_map[region] = REGION_COLORS.get(region, "#666666")
    
    # Group by Region first, then by Project Status + Play Type combination
    grouped = (
        filtered_df.groupby(["Region", "Project Status", "Play Type"])
        .agg({"Production Additions": "sum"})
        .reset_index()
    )
    print(f"DEBUG: create_treemap_figure - grouped regions before Production Additions > 0 filter: {grouped['Region'].unique().tolist() if not grouped.empty else 'empty'}")
    print(f"DEBUG: create_treemap_figure - Africa rows before Production Additions > 0 filter: {len(grouped[grouped['Region'] == 'Africa']) if not grouped.empty else 0}")
    if not grouped.empty:
        africa_before = grouped[grouped['Region'] == 'Africa']
        if not africa_before.empty:
            print(f"DEBUG: create_treemap_figure - Africa Production Additions values: {africa_before['Production Additions'].tolist()}")
    grouped = grouped[grouped["Production Additions"] > 0]
    print(f"DEBUG: create_treemap_figure - grouped regions after Production Additions > 0 filter: {grouped['Region'].unique().tolist() if not grouped.empty else 'empty'}")
    print(f"DEBUG: create_treemap_figure - Africa rows after Production Additions > 0 filter: {len(grouped[grouped['Region'] == 'Africa']) if not grouped.empty else 0}")
    
    if grouped.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available after grouping.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#666666")
        )
        fig.update_layout(
            title=dict(text="Total Capacity Additions 2025 Q1 - 2029 Q4", x=0.5, xanchor="center"),
            height=700,
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=10, r=10, t=60, b=10)
        )
        return fig
    
    # Order regions according to REGION_ORDER
    unique_regions_in_data = grouped["Region"].unique().tolist()
    ordered_regions = [r for r in REGION_ORDER if r in unique_regions_in_data]
    remaining_regions = [r for r in unique_regions_in_data if r not in REGION_ORDER]
    ordered_regions.extend(sorted(remaining_regions))
    
    # Define region positions to match original source layout:
    # Left column: Latin America (top), Middle East (bottom)
    # Right column: All other regions in original order (Africa, Asia, Europe, FSU, North America)
    region_positions = {}
    
    # Left column regions
    left_column_regions = ["Latin America", "Middle East"]
    right_column_regions = [r for r in REGION_ORDER if r not in left_column_regions]
    
    # Calculate positions for left column (50% width, split vertically)
    left_col_width = 0.5
    if "Latin America" in unique_regions_in_data and "Middle East" in unique_regions_in_data:
        region_positions["Latin America"] = dict(x=[0.0, left_col_width], y=[0.5, 1.0])
        region_positions["Middle East"] = dict(x=[0.0, left_col_width], y=[0.0, 0.5])
    elif "Latin America" in unique_regions_in_data:
        region_positions["Latin America"] = dict(x=[0.0, left_col_width], y=[0.0, 1.0])
    elif "Middle East" in unique_regions_in_data:
        region_positions["Middle East"] = dict(x=[0.0, left_col_width], y=[0.0, 1.0])
    
    # Calculate positions for right column (50% width)
    # Layout: Top row (2 columns: North America, Africa), Bottom row (3 columns: FSU, Europe, Asia)
    right_col_start = left_col_width
    right_col_width = 1.0 - right_col_start
    
    # Top row regions (split into 2 columns)
    top_row_regions = ["North America", "Africa"]
    # Bottom row regions (split into 3 columns)
    bottom_row_regions = ["FSU", "Europe", "Asia"]
    
    # Top row: Split into 2 equal columns
    top_row_y_start = 0.5
    top_row_y_end = 1.0
    top_row_width = right_col_width / 2.0
    
    for idx, region in enumerate(top_row_regions):
        if region in unique_regions_in_data:
            x_start = right_col_start + (idx * top_row_width)
            x_end = right_col_start + ((idx + 1) * top_row_width)
            region_positions[region] = dict(
                x=[x_start, x_end],
                y=[top_row_y_start, top_row_y_end]
            )
    
    # Bottom row: Split into 3 equal columns
    bottom_row_y_start = 0.0
    bottom_row_y_end = 0.5
    bottom_row_width = right_col_width / 3.0
    
    for idx, region in enumerate(bottom_row_regions):
        if region in unique_regions_in_data:
            x_start = right_col_start + (idx * bottom_row_width)
            x_end = right_col_start + ((idx + 1) * bottom_row_width)
            region_positions[region] = dict(
                x=[x_start, x_end],
                y=[bottom_row_y_start, bottom_row_y_end]
            )
    
    # Create figure
    fig = go.Figure()
    
    # Create a separate treemap trace for each region with its specific domain
    print(f"DEBUG: create_treemap_figure - Creating treemap traces for regions: {ordered_regions}")
    for region in ordered_regions:
        region_df = grouped[grouped["Region"] == region]
        if region_df.empty:
            print(f"DEBUG: create_treemap_figure - Skipping {region} - empty region_df")
            continue
        print(f"DEBUG: create_treemap_figure - Creating trace for {region} with {len(region_df)} rows")
        
        region_total = region_df["Production Additions"].sum()
        region_name = str(region).strip()
        region_color = REGION_COLORS.get(region_name, "#666666")
        
        # Create hierarchical structure for this region
        labels = [region_name]
        parents = [""]
        values = [region_total]
        hover_texts = [
            f"<span style='color:#333333;'>Region:</span> <span style='color:#000000;'><b>{region_name}</b></span><br>"
            f"<span style='color:#333333;'>Production Additions:</span> <span style='color:#000000;'><b>{region_total:,.1f} ('000 b/d)</b></span>"
        ]
        text_entries = [f"<b>{region_name}</b>"]
        colors = [region_color]
        selection_data = [
            {
                "key": f"region|{region_name}",
                "type": "region",
                "region": region_name,
                "project_status": None,
                "play_type": None,
                "label": region_name,
            }
        ]
        
        # Add combined Project Status + Play Type children
        for _, row in region_df.iterrows():
            project_status = str(row["Project Status"]).strip()
            play_type = str(row["Play Type"]).strip()
            prod_additions = row["Production Additions"]
            
            # Combine Project Status + Play Type as one label (for hierarchy)
            combined_label = f"{project_status} - {play_type}"
            
            labels.append(combined_label)
            parents.append(region_name)
            values.append(prod_additions)
            selection_data.append(
                {
                    "key": f"status|{region_name}|{project_status}|{play_type}",
                    "type": "status",
                    "region": region_name,
                    "project_status": project_status,
                    "play_type": play_type,
                    "label": combined_label,
                }
            )
            
            hover_texts.append(
                f"<span style='color:#333333;'>Region:</span> <span style='color:#000000;'><b>{region_name}</b></span><br>"
                f"<span style='color:#333333;'>Project Status:</span> <span style='color:#000000;'><b>{project_status}</b></span><br>"
                f"<span style='color:#333333;'>Play Type:</span> <span style='color:#000000;'><b>{play_type}</b></span><br>"
                f"<span style='color:#333333;'>Production Additions:</span> <span style='color:#000000;'><b>{prod_additions:,.1f} ('000 b/d)</b></span>"
            )
            # Display text in exact vertical order: Project Status, Play Type, Region
            text_entries.append(
                f"{project_status}<br>"
                f"{play_type}<br>"
                f"{region_name}"
            )
            # Use region color for children
            colors.append(region_color)
        
        # Get domain position for this region
        domain = region_positions.get(region_name, dict(x=[0.0, 1.0], y=[0.0, 1.0]))
        # Build per-node colors with alpha to implement highlight/fade behavior.
        # Some Plotly treemap traces do not accept per-node opacity reliably,
        # so we adjust the color alpha for non-selected nodes instead.
        def _hex_to_rgb(hex_color):
            """Return (r,g,b) tuple for a hex color like '#aabbcc'"""
            try:
                hex_color = str(hex_color).lstrip('#')
                if len(hex_color) == 3:
                    hex_color = ''.join([c*2 for c in hex_color])
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                return r, g, b
            except Exception:
                return 100, 100, 100

        colors_with_alpha = []
        if selected_key:
            sel_key_norm = str(selected_key).strip()
            for sel, col in zip(selection_data, colors):
                is_match = str(sel.get("key", "")).strip() == sel_key_norm
                if is_match:
                    colors_with_alpha.append(col)
                else:
                    r, g, b = _hex_to_rgb(col)
                    colors_with_alpha.append(f"rgba({r},{g},{b},0.18)")
        else:
            colors_with_alpha = colors

        # Add treemap trace for this region
        fig.add_trace(
            go.Treemap(
                labels=labels,
                parents=parents,
                values=values,
                branchvalues="total",
                hovertext=hover_texts,
                hovertemplate="%{hovertext}<extra></extra>",
                text=text_entries,
                textinfo="text",
                textfont=dict(size=12, color="#ffffff", family="Arial, sans-serif"),
                marker=dict(
                    colors=colors_with_alpha,
                    line=dict(color="white", width=1)
                ),
                customdata=selection_data,
                tiling=dict(pad=1, packing="squarify", squarifyratio=1.0),
                maxdepth=2,
                # Disable pathbar/expansion UI; keep click purely for selection
                pathbar=dict(visible=False),
                domain=domain,
                root=dict(color="rgba(255,255,255,0)")
            )
        )
    
    fig.update_layout(
        title=dict(
            text="",
            x=0.5,
            xanchor="center",
            y=0.98,
            font=dict(size=20, color="#E75224", family="Arial, sans-serif")
        ),
        height=700,
        margin=dict(l=10, r=10, t=60, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        showlegend=False,
        hovermode="closest",
        # Disable built-in expand/collapse; clicks are used only for selection
        clickmode="event+select",
        transition=dict(duration=0),
        # Preserve layout to avoid full redraw lag; selection still re-colors nodes
        uirevision="treemap-static",
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#cccccc",
            font_size=12,
            font_family="Arial, sans-serif",
            align="left"
        )
    )

    # Enforce non-zooming treemap behavior (no expand/collapse)
    fig.update_traces(
        selector=dict(type="treemap"),
        # Keep treemap non-drillable (no expand/collapse)
        pathbar=dict(visible=False),
        maxdepth=2,
        root_color="rgba(0,0,0,0)",
        branchvalues="total",
    )
    
    return fig


# Region order and color mapping (as specified)
REGION_ORDER = [
    "Africa",
    "Asia", 
    "Europe",
    "FSU",
    "Latin America",
    "Middle East",
    "North America"
]

REGION_COLORS = {
    "Africa": "#0075a8",
    "Asia": "#595959",
    "Europe": "#313b49",
    "FSU": "#7986cb",
    "Latin America": "#a6a6a6",
    "Middle East": "#bf5227",
    "North America": "#c3d297"
}

def get_region_color(region, all_regions=None):
    """Get color for a region from the predefined color map"""
    return REGION_COLORS.get(region, "#666666")


def create_layout():
    """Create the Projects by Status layout"""
    # Don't load data here - use REGION_ORDER for initial region list
    # Regions will be loaded dynamically when page is accessed
    # Use predefined REGION_ORDER for initial setup
    regions = REGION_ORDER.copy()
    
    return html.Div([
        html.Div([
            # Main visualization area (75% width)
            html.Div([
                html.Div([
                    html.H4("Total Capacity Additions 2025 Q1 - 2029 Q4", 
                           style={'marginBottom': '10px', 'fontSize': '20px', 'fontWeight': 'bold', 'fontFamily': 'Arial, sans-serif', 'color': '#E75224', 'flexGrow': 1, 'textAlign': 'center'}),
                    html.Div([
                        html.Button(
                            'Export to CSV',
                            id='btn-export-status-chart-csv',
                            n_clicks=0,
                            style={
                                'backgroundColor': 'white',
                                'color': '#2c3e50',
                                'border': '1px solid #dee2e6',
                                'padding': '5px 10px',
                                'borderRadius': '4px',
                                'cursor': 'pointer',
                                'fontSize': '12px'
                            }
                        ),
                        dcc.Download(id="download-status-chart-csv")
                    ])
                ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'paddingRight': '10px'}),
                dcc.Graph(
                    id='projects-status-treemap',
                    style={'height': '700px'},
                    config={'displayModeBar': False}
                ),
                # Loading overlay
                html.Div(
                    id='treemap-loading-overlay',
                    children=[
                        html.Div(
                            [
                                html.Div(
                                    className="spinner",
                                    style={
                                        'border': '4px solid #f3f3f3',
                                        'borderTop': '4px solid #E75224',
                                        'borderRadius': '50%',
                                        'width': '40px',
                                        'height': '40px',
                                        'animation': 'spin 1s linear infinite',
                                        'margin': '0 auto'
                                    }
                                ),
                                html.Div(
                                    "Updating...",
                                    style={
                                        'marginTop': '15px',
                                        'color': '#666666',
                                        'fontSize': '14px',
                                        'fontFamily': 'Arial, sans-serif'
                                    }
                                )
                            ],
                            style={
                                'position': 'absolute',
                                'top': '50%',
                                'left': '50%',
                                'transform': 'translate(-50%, -50%)',
                                'textAlign': 'center',
                                'zIndex': '1000'
                            }
                        )
                    ],
                    style={
                        'display': 'none',
                        'position': 'absolute',
                        'top': '0',
                        'left': '0',
                        'width': '100%',
                        'height': '100%',
                        'backgroundColor': 'rgba(255, 255, 255, 0.8)',
                        'zIndex': '999',
                        'pointerEvents': 'none'
                    }
                )
            ], style={'width': '75%', 'float': 'left', 'paddingRight': '20px', 'position': 'relative'}),
            
            # Right panel (25% width)
            html.Div([
                # Region filter temporarily removed from UI; keep hidden checklist for defaults
                dcc.Checklist(
                    id='projects-status-region-filter',
                    options=[],  # Populated by callback
                    value=None,  # None = show all regions until filter is initialized
                    style={'display': 'none'}
                ),
                # Visible region legend filter (color boxes + labels)
                html.Div([
                    html.Label(
                        "Region",
                        style={
                            'fontWeight': '600',
                            'marginBottom': '8px',
                            'display': 'block',
                            'fontSize': '13px',
                            'color': '#2c3e50',
                            'fontFamily': 'Arial, sans-serif'
                        },
                    ),
                    html.Div(
                        id='region-legend-container',
                        children=[],
                        style={
                            "maxHeight": "240px",
                            "overflowY": "auto",
                            "padding": "8px",
                            "border": "1px solid #e0e0e0",
                            "borderRadius": "6px",
                            "background": "#fafbfc",
                        },
                    ),
                ], style={'marginBottom': '16px'}),
                
                # Store to track if region filter has been initialized (prevents overwriting on subsequent updates)
                dcc.Store(id='region-filter-initialized', data=False),
                
                # Hidden div for CSS injection trigger
                html.Div(id='treemap-css-injector', style={'display': 'none'}),
                
                # Store to cache treemap dataframe (avoids repeated DB queries)
                dcc.Store(id='projects-status-treemap-store', data=[]),
                # Store to cache table data (avoids repeated DB queries)
                dcc.Store(id='projects-status-table-store', data=[]),
                # Store to hold treemap click selection (selected label). None => no selection.
                dcc.Store(id='projects-status-click-selection', data=None),
                # Store to track loading state
                dcc.Store(id='treemap-loading-state', data=False),
                
                # KPI Table Section
                html.Div([
                    html.H4(
                        "Worldwide Oil Capacity Additions",
                        style={
                            'color': '#E75224',
                            'marginBottom': '15px',
                            'fontSize': '16px',
                            'fontWeight': 'bold'
                        }
                    ),
                    html.Div(
                        id='projects-status-kpi-table-container'
                    )
                ], style={'marginBottom': '30px'}),
                
                # Likely to Go Ahead Filter (Checkbox list)
                html.Div([
                    html.Label("Likely to Go Ahead:", style={
                        'fontWeight': '600', 
                        'marginBottom': '12px', 
                        'fontSize': '13px',
                        'color': '#2c3e50',
                        'fontFamily': 'Arial, sans-serif'
                    }),
                    dcc.Checklist(
                        id='projects-status-likely-filter',
                        options=[
                            {'label': '(All)', 'value': 'All'},
                            {'label': ' ', 'value': ''},
                            {'label': 'N', 'value': 'N'},
                            {'label': 'Uncertain', 'value': 'Uncertain'},
                            {'label': 'Y', 'value': 'Y'}
                        ],
                        value=['Y'],  # Default to 'Y' only
                        style={
                            'fontSize': '12px',
                            'fontFamily': 'Arial, sans-serif'
                        },
                        inputStyle={'marginRight': '8px', 'marginLeft': '0px'},
                        labelStyle={'display': 'block', 'marginBottom': '6px', 'cursor': 'pointer'}
                    )
                    ,
                    dcc.Store(id='projects-status-likely-filter-previous', data=['Y'])
                ], style={'marginBottom': '25px', 'padding': '15px', 'border': '1px solid #e0e0e0', 'borderRadius': '5px', 'backgroundColor': '#fafafa'})
            ], style={'width': '25%', 'float': 'right', 'paddingLeft': '20px'}),
            
            html.Div(style={'clear': 'both'}),
            
            # Project Details Table - Full width below treemap and filters
            html.Div([
                html.Div([
                    html.H4("Project Details", style={'marginBottom': '0px', 'fontSize': '18px', 'fontWeight': 'bold', 'color': '#E75224', 'flexGrow': 1}),
                    html.Div([
                        html.Button(
                            'Export to CSV',
                            id='btn-export-status-table-csv',
                            n_clicks=0,
                            style={
                                'backgroundColor': 'white',
                                'color': '#2c3e50',
                                'border': '1px solid #dee2e6',
                                'padding': '5px 10px',
                                'borderRadius': '4px',
                                'cursor': 'pointer',
                                'fontSize': '12px'
                            }
                        ),
                        dcc.Download(id="download-status-table-csv")
                    ])
                ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'marginBottom': '15px'}),
                html.Div(
                    id='projects-status-table-container',
                    style={'marginTop': '10px', 'width': '100%'}
                )
            ], style={'width': '100%', 'clear': 'both', 'marginTop': '20px'})
        ], style={'padding': '20px'})
    ], className='tab-content', style={'backgroundColor': '#f5f7fa', 'padding': '20px', 'minHeight': '100vh'})


def register_callbacks(dash_app, server):
    """Register all callbacks for Projects by Status"""
    
    # Clientside callback to inject CSS for spinner animation
    dash_app.clientside_callback(
        """
        function(n) {
            if (n && !document.getElementById('treemap-spinner-style')) {
                var style = document.createElement('style');
                style.id = 'treemap-spinner-style';
                style.textContent = '@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }';
                document.head.appendChild(style);
            }
            return '';
        }
        """,
        Output('treemap-css-injector', 'children'),
        Input('current-submenu', 'data'),
        prevent_initial_call=False
    )
    
    @dash_app.callback(
        [Output('projects-status-likely-filter', 'value'),
         Output('projects-status-likely-filter-previous', 'data')],
        Input('projects-status-likely-filter', 'value'),
        State('projects-status-likely-filter-previous', 'data'),
        prevent_initial_call=False
    )
    def manage_all_checkbox(selected_values, previous_values):
        """Handle (All) checkbox behavior for the Likely-to-Go-Ahead filter"""
        if selected_values is None:
            return [], []
        
        if not isinstance(selected_values, list):
            selected_values = [selected_values] if selected_values else []
        
        all_options = ['All', 'N', 'Uncertain', 'Y', '']
        individual_options = ['N', 'Uncertain', 'Y', '']
        if previous_values is None:
            previous_values = []
        if not isinstance(previous_values, list):
            previous_values = [previous_values] if previous_values else []
        
        was_all_selected = 'All' in previous_values
        is_all_selected = 'All' in selected_values
        prev_individual = [opt for opt in previous_values if opt in individual_options]
        curr_individual = [opt for opt in selected_values if opt in individual_options]
        
        if not was_all_selected and is_all_selected:
            return all_options, all_options
        
        if was_all_selected and not is_all_selected:
            return [], []
        
        if was_all_selected and is_all_selected and prev_individual != curr_individual:
            if len(curr_individual) < len(prev_individual):
                return curr_individual, curr_individual
            elif len(curr_individual) == len(individual_options):
                return all_options, all_options
        
        if is_all_selected:
            return all_options, all_options
        
        selected_individual = [opt for opt in selected_values if opt in individual_options]
        
        if len(selected_individual) == len(individual_options):
            return all_options, all_options
        
        final_return_values = selected_individual if len(selected_individual) > 0 else (all_options if is_all_selected else [])
        return final_return_values, final_return_values

    @dash_app.callback(
        Output('projects-status-treemap-store', 'data'),
        Input('current-submenu', 'data'),
        prevent_initial_call=False
    )
    def populate_treemap_store(current_submenu):
        """Populate treemap store when page becomes active to avoid repeated DB calls"""
        if current_submenu != 'projects-status':
            return dash.no_update
        df = load_treemap_data()
        if df is None or df.empty:
            return []
        # Convert to list-of-dicts for storage
        return df.to_dict('records')

    # Callback to update region filter options when page loads
    @dash_app.callback(
        [
            Output('projects-status-region-filter', 'options'),
            Output('projects-status-region-filter', 'value', allow_duplicate=True),
            Output('region-filter-initialized', 'data'),
        ],
        [
            Input('current-submenu', 'data'),
            Input('projects-status-likely-filter', 'value'),
        ],
        State('projects-status-region-filter', 'value'),
        State('region-filter-initialized', 'data'),
        State('projects-status-treemap-store', 'data'),
        prevent_initial_call='initial_duplicate'
    )
    def update_region_filter_options(current_submenu, likely_filter, current_filter_value, is_initialized, treemap_store):
        """Update region filter options when page is accessed"""
        print(f"DEBUG: update_region_filter_options - current_submenu={current_submenu}, is_initialized={is_initialized}, current_filter_value={current_filter_value}")
        if current_submenu != 'projects-status':
            return [], dash.no_update, dash.no_update
        
        # Prefer cached treemap store if available to avoid extra DB call
        if treemap_store:
            treemap_df = pd.DataFrame(treemap_store)
        else:
            treemap_df = load_treemap_data()
        regions = []
        
        def _apply_likely_filter(df: pd.DataFrame, likely_vals):
            if df.empty or "Region" not in df.columns:
                return df
            if likely_vals is None:
                return df
            if isinstance(likely_vals, list):
                if len(likely_vals) == 0:
                    return df.iloc[0:0]
                if 'All' in likely_vals:
                    return df
            table_df = load_table_data()
            # Find likely column in table
            likely_col = None
            for col in table_df.columns:
                lc = col.lower()
                if 'likely' in lc and ('go' in lc or 'ahead' in lc):
                    likely_col = col
                    break
            if likely_col is None:
                return df
            col_upper = table_df[likely_col].astype(str).str.upper()
            filter_values = likely_vals if isinstance(likely_vals, list) else [likely_vals]
            mask = pd.Series(False, index=col_upper.index)
            for v in filter_values:
                v_str = str(v).strip()
                v_up = v_str.upper()
                if v_up == 'ALL' or v == 'All':
                    mask |= pd.Series(True, index=col_upper.index)
                elif v_up == '' or v_str.lower() == 'blank':
                    mask |= (col_upper == '')
                elif v_up.startswith('Y') or v_up == 'YES':
                    mask |= col_upper.str.startswith('Y')
                elif v_up.startswith('N'):
                    mask |= col_upper.str.startswith('N')
                elif v_up.startswith('UNCERT') or v_up.startswith('U'):
                    mask |= col_upper.str.startswith('U')
            matching_projects = table_df[mask]
            if matching_projects.empty:
                return df.iloc[0:0]
            combos = set()
            for _, row in matching_projects.iterrows():
                combos.add((str(row.get("Region", "")).strip(), str(row.get("Play Type", "")).strip(), str(row.get("Project Status", "")).strip()))
            def _match_combo(r):
                return (str(r.get("Region", "")).strip(), str(r.get("Play Type", "")).strip(), str(r.get("Project Status", "")).strip()) in combos
            filtered = df[df.apply(_match_combo, axis=1)]
            return filtered

        if not treemap_df.empty and "Region" in treemap_df.columns:
            treemap_df = _apply_likely_filter(treemap_df, likely_filter)
            unique_regions = (
                treemap_df['Region']
                .astype(str)
                .str.strip()
                .dropna()
                .unique()
                .tolist()
            )
            # Order regions according to REGION_ORDER
            ordered_regions = [r for r in REGION_ORDER if r in unique_regions]
            # Add any regions not in REGION_ORDER at the end
            remaining_regions = [r for r in unique_regions if r not in REGION_ORDER]
            ordered_regions.extend(sorted(remaining_regions))
            regions = ordered_regions
        
        # Normalize region names for consistent comparison
        regions_normalized = [str(r).strip() for r in regions]
        options = [{'label': r, 'value': r} for r in regions_normalized]
        
            # CRITICAL: Only set default_value on the very first initialization
            # Use is_initialized flag to prevent overwriting the filter value on subsequent updates
            # This ensures Africa is never removed from the filter
        if not is_initialized:
            # First initialization: Set all regions as default, including Africa
            # Build default_value in REGION_ORDER to ensure consistent ordering (use normalized regions)
            default_value = []
            for region in REGION_ORDER:
                region_normalized = str(region).strip()
                if region_normalized in regions_normalized:
                    default_value.append(region_normalized)
            # Add any remaining regions not in REGION_ORDER
            for region_norm in regions_normalized:
                if region_norm not in default_value:
                    default_value.append(region_norm)
            
            # CRITICAL: Verify Africa is included - this is essential
            # Double-check: if Africa exists in regions, it MUST be in default_value
            africa_normalized = 'Africa'.strip()
            if africa_normalized in regions_normalized:
                if africa_normalized not in default_value:
                    # Force insert Africa at the beginning
                    default_value.insert(0, africa_normalized)
                    print(f"DEBUG: update_region_filter_options - Force inserted Africa into default_value: {default_value}")
                elif default_value[0] != africa_normalized:
                    # Africa exists but not first - move it to first position
                    default_value.remove(africa_normalized)
                    default_value.insert(0, africa_normalized)
                    print(f"DEBUG: update_region_filter_options - Moved Africa to first position: {default_value}")
            else:
                print(f"DEBUG: update_region_filter_options - WARNING: Africa not found in regions_normalized: {regions_normalized}")
            
            print(f"DEBUG: update_region_filter_options - Returning initialized filter with default_value: {default_value}")
            # Mark as initialized to prevent future overwrites
            return options, default_value, True
        else:
            # If likely filter changed, reset to all available regions
            ctx = dash.callback_context
            if ctx and ctx.triggered and ctx.triggered[0].get("prop_id", "").startswith("projects-status-likely-filter"):
                return options, regions_normalized, dash.no_update

            # Otherwise intersect current selection with available regions; allow empty
            # Normalize for consistent comparison
            current_normalized = [str(v).strip() for v in (current_filter_value or [])]
            current_set = set(current_normalized)
            regions_normalized = [str(r).strip() for r in regions]
            new_values = [r for r in regions_normalized if r in current_set] if current_set else []
            
            print(f"DEBUG: update_region_filter_options - current_filter_value={current_normalized}, regions={regions_normalized}, new_values={new_values}")
            
            return options, new_values, dash.no_update
    
    # Build region legend items (color boxes + labels) that mirror the hidden checklist
    @dash_app.callback(
        Output('region-legend-container', 'children'),
        [
            Input('projects-status-region-filter', 'options'),
            Input('projects-status-region-filter', 'value'),
        ],
        prevent_initial_call=False,
    )
    def render_region_legend(options, selected_values):
        # Normalize all values for consistent comparison
        regions = [str(opt.get('value', '')).strip() for opt in (options or [])]
        selected_normalized = [str(v).strip() for v in (selected_values or [])]
        selected = set(selected_normalized)
        
        print(f"DEBUG: render_region_legend - regions={regions}, selected_values={selected_normalized}")
        
        items = []
        for region in regions:
            color = REGION_COLORS.get(region, "#666666")
            is_active = region in selected
            print(f"DEBUG: render_region_legend - region={region}, is_active={is_active}")
            item_style = {
                "display": "flex",
                "alignItems": "center",
                "cursor": "pointer",
                "padding": "6px 8px",
                "borderRadius": "6px",
                "marginBottom": "6px",
                "border": "1px solid #e0e0e0",
                "backgroundColor": "#ffffff" if is_active else "#f9f9f9",
                "opacity": 1.0 if is_active else 0.45,
                "transition": "background-color 0.15s ease, opacity 0.15s ease",
            }
            items.append(
                html.Div(
                    [
                        html.Div(
                            style={
                                "width": "16px",
                                "height": "16px",
                                "backgroundColor": color,
                                "borderRadius": "3px",
                                "marginRight": "8px",
                                "border": "1px solid #ffffff",
                                "boxShadow": "0 1px 2px rgba(0,0,0,0.2)",
                            }
                        ),
                        html.Span(
                            region,
                            style={
                                "fontSize": "12px",
                                "color": "#2c3e50",
                                "fontWeight": "600" if is_active else "500",
                                "fontFamily": "Arial, sans-serif",
                            },
                        ),
                    ],
                    id={'type': 'region-legend-item', 'value': region},
                    n_clicks=0,
                    style=item_style,
                )
            )
        return items
    
    # Toggle region selection via legend clicks (mirrors hidden checklist)
    @dash_app.callback(
        Output('projects-status-region-filter', 'value', allow_duplicate=True),
        Input({'type': 'region-legend-item', 'value': ALL}, 'n_clicks'),
        State('projects-status-region-filter', 'value'),
        State('projects-status-region-filter', 'options'),
        State('region-filter-initialized', 'data'),
        prevent_initial_call=True,
    )
    def toggle_region_from_legend(n_clicks_list, current_values, options, filter_initialized):
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update
        
        # CRITICAL: Ignore any triggers before filter is initialized to prevent race conditions
        if not filter_initialized:
            print(f"DEBUG: toggle_region_from_legend - Filter not initialized yet, ignoring toggle")
            return dash.no_update
        
        trigger = ctx.triggered[0].get("prop_id", "")
        if not trigger:
            return dash.no_update
        
        # Check if this is a real click (n_clicks > 0) or just initialization
        try:
            import json
            trigger_id = json.loads(trigger.split(".")[0].replace("'", '"'))
        except Exception:
            return dash.no_update
        
        # Extract n_clicks value from the trigger to ensure it's a real click
        trigger_prop = trigger.split(".")[-1] if "." in trigger else ""
        if trigger_prop != "n_clicks":
            return dash.no_update
        
        # Find which item was clicked by checking which n_clicks increased
        # We need to compare with previous state, but since we don't have it, we'll check if any n_clicks > 0
        clicked_index = None
        for idx, click_count in enumerate(n_clicks_list or []):
            if click_count is not None and click_count > 0:
                clicked_index = idx
                break
        
        if clicked_index is None:
            print(f"DEBUG: toggle_region_from_legend - No valid click detected (n_clicks_list={n_clicks_list}), ignoring")
            return dash.no_update
        
        # Verify the clicked item matches the trigger
        option_values = [str(opt.get("value", "")).strip() for opt in (options or [])]
        if clicked_index < len(option_values):
            clicked_region = option_values[clicked_index]
            trigger_region = trigger_id.get("value", "")
            if str(clicked_region).strip() != str(trigger_region).strip():
                print(f"DEBUG: toggle_region_from_legend - Mismatch: clicked_index={clicked_index}, clicked_region={clicked_region}, trigger_region={trigger_region}, ignoring")
                return dash.no_update
        
        region = trigger_id.get("value")
        if not region:
            return dash.no_update
        
        # Normalize region and current values for consistent comparison
        region_normalized = str(region).strip()
        current = current_values or []
        current_normalized = [str(v).strip() for v in current]
        
        print(f"DEBUG: toggle_region_from_legend - region={region_normalized}, current_values={current_normalized}, filter_initialized={filter_initialized}")
        
        if region_normalized in current_normalized:
            # Region is currently selected, so unselect it (remove from filter)
            new_values = [v for v in current_normalized if v != region_normalized]
            print(f"DEBUG: toggle_region_from_legend - unselecting {region_normalized}, new_values={new_values}")
        else:
            # Region is not currently selected, so select it (add to filter)
            new_values = current_normalized + [region_normalized]
            print(f"DEBUG: toggle_region_from_legend - selecting {region_normalized}, new_values={new_values}")
        
        # Preserve order according to options
        option_order = [str(opt.get("value", "")).strip() for opt in (options or [])]
        if option_order:
            new_values = [v for v in option_order if v in new_values]
        
        print(f"DEBUG: toggle_region_from_legend - final new_values={new_values}")
        return new_values
    
    
    # Callback to show loading overlay when treemap click selection changes
    @dash_app.callback(
        [Output('treemap-loading-overlay', 'style'),
         Output('treemap-loading-state', 'data')],
        Input('projects-status-click-selection', 'data'),
        prevent_initial_call=True
    )
    def show_loading_overlay(click_selection):
        """Show loading overlay when treemap is updating due to click"""
        return {
            'display': 'block',
            'position': 'absolute',
            'top': '0',
            'left': '0',
            'width': '100%',
            'height': '100%',
            'backgroundColor': 'rgba(255, 255, 255, 0.8)',
            'zIndex': '999',
            'pointerEvents': 'none'
        }, True
    
    # Callback to hide loading overlay when treemap update completes
    @dash_app.callback(
        [Output('treemap-loading-overlay', 'style', allow_duplicate=True),
         Output('treemap-loading-state', 'data', allow_duplicate=True)],
        Input('projects-status-treemap', 'figure'),
        State('treemap-loading-state', 'data'),
        prevent_initial_call=True
    )
    def hide_loading_overlay(figure, loading_state):
        """Hide loading overlay when treemap figure is updated"""
        # Check if figure is valid and loading state is active
        if loading_state and figure is not None:
            # Verify figure has required structure
            try:
                # Just check if figure exists, don't access properties that might not exist
                if isinstance(figure, dict) or hasattr(figure, 'data'):
                    return {
                        'display': 'none',
                        'position': 'absolute',
                        'top': '0',
                        'left': '0',
                        'width': '100%',
                        'height': '100%',
                        'backgroundColor': 'rgba(255, 255, 255, 0.8)',
                        'zIndex': '999',
                        'pointerEvents': 'none'
                    }, False
            except Exception:
                # If there's any error accessing figure properties, just return no_update
                pass
        return dash.no_update, dash.no_update

    @dash_app.callback(
        Output('projects-status-treemap', 'figure'),
        [Input('projects-status-region-filter', 'value'),
         Input('projects-status-likely-filter', 'value'),
         Input('current-submenu', 'data'),
         Input('projects-status-click-selection', 'data'),
         Input('region-filter-initialized', 'data')],  # Ensure treemap re-renders when filter is initialized
        [State('projects-status-treemap-store', 'data'),
         State('projects-status-table-store', 'data')],
        prevent_initial_call=False
    )
    def update_treemap(region_filter, likely_filter, current_submenu, selected_label, filter_initialized, treemap_store, table_store):        
        print(f"DEBUG: update_treemap triggered - current_submenu={current_submenu}, region_filter={region_filter} (type: {type(region_filter)}), likely_filter={likely_filter}, filter_initialized={filter_initialized}")
        if current_submenu != 'projects-status':
            # Return empty figure if page is not active
            fig = go.Figure()
            fig.add_annotation(
                text="",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False
            )
            fig.update_layout(
                title=dict(text="Total Capacity Additions 2025 Q1 - 2029 Q4", x=0.5, xanchor="center"),
                height=700,
                plot_bgcolor="white",
                paper_bgcolor="white",
                margin=dict(l=10, r=10, t=60, b=10)
            )
            return fig
        
        # CRITICAL: Wait for filter initialization before rendering treemap
        # This prevents race condition where treemap renders before filter is set
        # Only wait if filter is not initialized AND region_filter is None
        # Once filter_initialized is True, proceed regardless of region_filter value
        if filter_initialized is False and region_filter is None:
            print(f"DEBUG: update_treemap - Filter not initialized yet (filter_initialized={filter_initialized}, region_filter={region_filter}), waiting...")
            # Return empty figure with loading message until filter is initialized
            fig = go.Figure()
            fig.add_annotation(
                text="Loading...",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=16, color="#666666")
            )
            fig.update_layout(
                title=dict(text="Total Capacity Additions 2025 Q1 - 2029 Q4", x=0.5, xanchor="center"),
                height=700,
                plot_bgcolor="white",
                paper_bgcolor="white",
                margin=dict(l=10, r=10, t=60, b=10)
            )
            return fig
        
        # Normalize region filter values (trim/case)
        if isinstance(region_filter, list):
            region_filter = [str(r).strip() for r in region_filter]
            print(f"DEBUG: update_treemap - normalized region_filter={region_filter}")
        # If region filter empty => no regions; if None => default to all available
        if region_filter is None:
            if treemap_store:
                df_temp = pd.DataFrame(treemap_store)
            else:
                df_temp = load_treemap_data()
            if not df_temp.empty and "Region" in df_temp.columns:
                all_regions = (
                    df_temp['Region'].astype(str).str.strip().dropna().unique().tolist()
                )
                ordered_all = [r for r in REGION_ORDER if r in all_regions]
                remaining_all = [r for r in all_regions if r not in REGION_ORDER]
                ordered_all.extend(sorted(remaining_all))
                region_filter = ordered_all
        elif isinstance(region_filter, list) and len(region_filter) == 0:
            df_empty = pd.DataFrame(columns=["Region", "Project Status", "Play Type", "Production Additions"])
            return create_treemap_figure(df_empty, [], likely_filter, None, selected_label)
        if treemap_store:
            df = pd.DataFrame(treemap_store)
        else:
            df = load_treemap_data()
        
        # Load table data once (use cache if available)
        if table_store:
            cached_table_df = pd.DataFrame(table_store)
        else:
            cached_table_df = load_table_data()
        
        # Apply likely filter to treemap data before rendering
        def _apply_likely_filter(df_in: pd.DataFrame, likely_vals):
            if df_in.empty or "Region" not in df_in.columns:
                return df_in
            if likely_vals is None:
                return df_in
            if isinstance(likely_vals, list):
                if len(likely_vals) == 0:
                    return df_in.iloc[0:0]
                if 'All' in likely_vals:
                    return df_in
            # Use cached table data
            table_df = cached_table_df.copy()
            likely_col = None
            for col in table_df.columns:
                lc = col.lower()
                if 'likely' in lc and ('go' in lc or 'ahead' in lc):
                    likely_col = col
                    break
            if likely_col is None:
                return df_in
            col_upper = table_df[likely_col].astype(str).str.upper()
            filter_values = likely_vals if isinstance(likely_vals, list) else [likely_vals]
            mask = pd.Series(False, index=col_upper.index)
            for v in filter_values:
                v_str = str(v).strip()
                v_up = v_str.upper()
                if v_up == 'ALL' or v == 'All':
                    mask |= pd.Series(True, index=col_upper.index)
                elif v_up == '' or v_str.lower() == 'blank':
                    mask |= (col_upper == '')
                elif v_up.startswith('Y') or v_up == 'YES':
                    mask |= col_upper.str.startswith('Y')
                elif v_up.startswith('N'):
                    mask |= col_upper.str.startswith('N')
                elif v_up.startswith('UNCERT') or v_up.startswith('U'):
                    mask |= col_upper.str.startswith('U')
            matching_projects = table_df[mask]
            if matching_projects.empty:
                return df_in.iloc[0:0]
            combos = set()
            for _, row in matching_projects.iterrows():
                combos.add((str(row.get("Region", "")).strip(), str(row.get("Play Type", "")).strip(), str(row.get("Project Status", "")).strip()))
            def _match_combo(r):
                return (str(r.get("Region", "")).strip(), str(r.get("Play Type", "")).strip(), str(r.get("Project Status", "")).strip()) in combos
            filtered_df = df_in[df_in.apply(_match_combo, axis=1)]
            return filtered_df

        df = _apply_likely_filter(df, likely_filter)
        
        # Use cached table data if available to avoid repeated DB calls
        if table_store:
            table_df = pd.DataFrame(table_store)
        else:
            table_df = load_table_data()
            # Cache will be populated by another callback
        
        if not table_df.empty and "Project Name" in table_df.columns:
            table_df_unique = table_df.drop_duplicates(subset=["Project Name"], keep='first')
        else:
            table_df_unique = table_df
        fig = create_treemap_figure(df=df, region_filter=region_filter, likely_filter=likely_filter, table_df=table_df_unique, selected_label=selected_label)
        return fig

    # Callback to toggle treemap click selection (click same node to clear)
    @dash_app.callback(
        Output('projects-status-click-selection', 'data'),
        Input('projects-status-treemap', 'clickData'),
        State('projects-status-click-selection', 'data'),
        prevent_initial_call=True
    )
    def toggle_treemap_selection(click_data, current_selection):
        """Toggle selected treemap label. Clicking same label clears selection."""
        try:
            if not click_data or 'points' not in click_data or len(click_data.get('points', [])) == 0:
                return dash.no_update

            # Grab clicked label (support label or customdata)
            point = click_data['points'][0]
            selection_payload = None
            if isinstance(point, dict):
                cd = point.get('customdata')
                if isinstance(cd, dict) and cd.get('key'):
                    # Normalize key/label to strings for consistent downstream matching
                    selection_payload = {
                        **cd,
                        "key": str(cd.get("key")).strip() if cd.get("key") is not None else None,
                        "label": str(cd.get("label")).strip() if cd.get("label") is not None else cd.get("label"),
                    }
                elif point.get('label'):
                    selection_payload = {"key": str(point['label']).strip(), "label": str(point['label']).strip()}

            # If click produced no identifiable selection, clear to reset active/inactive state
            if selection_payload is None:
                return None

            # If same block clicked again, clear selection
            if isinstance(current_selection, dict):
                curr_key = current_selection.get("key")
            else:
                curr_key = str(current_selection).strip() if current_selection else None
            new_key = selection_payload.get("key")

            if curr_key and new_key and str(curr_key).strip() == str(new_key).strip():
                return None

            return selection_payload
        except Exception as e:
            import traceback
            print("ERROR in toggle_treemap_selection:", e)
            traceback.print_exc()
            return dash.no_update

    @dash_app.callback(
        [Output('projects-status-kpi-table-container', 'children'),
         Output('projects-status-table-container', 'children')],
        [Input('projects-status-region-filter', 'value'),
         Input('projects-status-likely-filter', 'value'),
         Input('projects-status-click-selection', 'data'),
         Input('projects-status-treemap', 'clickData'),
         Input('current-submenu', 'data')],
        [State('projects-status-treemap-store', 'data')],
        prevent_initial_call=False
    )
    def update_tables(region_filter, likely_filter, click_selection, click_data, current_submenu, treemap_store):
        """Update KPI table and project details table - only loads data when page is active"""
        # Only load data if this page is currently active
        if current_submenu != 'projects-status':
            # Return empty containers if page is not active
            empty_kpi = html.Div("", style={'display': 'none'})
            empty_table = html.Div("", style={'display': 'none'})
            return empty_kpi, empty_table
        
        # Load data
        if treemap_store:
            treemap_df = pd.DataFrame(treemap_store)
        else:
            treemap_df = load_treemap_data()
        table_df = load_table_data()
            
        # If the user has explicitly unchecked all Likely-to-Go-Ahead options
        # (i.e., the checklist value is an empty list), hide both KPI and details table.
        if isinstance(likely_filter, list) and len(likely_filter) == 0:
            empty_kpi = html.Div("", style={'display': 'none'})
            empty_table = html.Div("", style={'display': 'none'})
            return empty_kpi, empty_table
        
        # Calculate KPI data based on region filter and likely filter
        filtered_treemap = treemap_df.copy()
        
        # Apply region filter to treemap for KPI calculation
        if region_filter:
            if isinstance(region_filter, list):
                if len(region_filter) > 0:
                    filtered_treemap = filtered_treemap[filtered_treemap["Region"].isin(region_filter)]
            elif region_filter != "(All)":
                filtered_treemap = filtered_treemap[filtered_treemap["Region"] == region_filter]
        
        # Apply likely filter to treemap for KPI calculation
        if likely_filter:
        # Normalize selection and handle 'All' sentinel
            filter_values = likely_filter
            if isinstance(likely_filter, list):
                if 'All' in likely_filter and len(likely_filter) > 1:
                    filter_values = [v for v in likely_filter if v != 'All']
                if not likely_filter or (len(likely_filter) == 1 and likely_filter[0] == 'All'):
                    filter_values = None

            if filter_values is not None:
                # Find likely column name in table (flexible matching)
                likely_col = None
                for col in table_df.columns:
                    col_lower = col.lower()
                    if 'likely' in col_lower and ('go' in col_lower or 'ahead' in col_lower):
                        likely_col = col
                        break

                if likely_col is not None:
                    col_upper = table_df[likely_col].astype(str).str.upper()
                    selected_values = filter_values if isinstance(filter_values, list) else [filter_values]
                    mask = pd.Series(False, index=col_upper.index)
                    for v in selected_values:
                        v_str = str(v).strip()
                        v_up = v_str.upper()
                        if v_up == 'ALL' or v == 'All':
                            mask |= pd.Series(True, index=col_upper.index)
                        elif v_up == '' or v_str.lower() == 'blank':
                            mask |= (col_upper == '')
                        elif v_up.startswith('Y') or v_up == 'YES':
                            mask |= col_upper.str.startswith('Y')
                        elif v_up.startswith('N'):
                            mask |= col_upper.str.startswith('N')
                        elif v_up.startswith('UNCERT') or v_up.startswith('U'):
                            mask |= col_upper.str.startswith('U')

                    matching_projects = table_df[mask]
                # Debug: log matching counts to help diagnose empty KPI/treemap issues
                try:
                    print(f"DEBUG: KPI likely selected_values={selected_values}")
                    print(f"DEBUG: KPI matching_projects count={len(matching_projects)}")
                except Exception:
                    pass

                if not matching_projects.empty:
                    matching_combos = set()
                    for _, row in matching_projects.iterrows():
                        combo = (
                            row.get("Region", ""),
                            row.get("Play Type", ""),
                            row.get("Project Status", "")
                        )
                        matching_combos.add(combo)

                    try:
                        print(f"DEBUG: KPI matching_combos count={len(matching_combos)}")
                    except Exception:
                        pass

                    def matches_combo(row):
                        combo = (
                            str(row.get("Region", "")),
                            str(row.get("Play Type", "")),
                            str(row.get("Project Status", ""))
                        )
                        return combo in matching_combos

                    before_kpi = len(filtered_treemap)
                    filtered_treemap = filtered_treemap[filtered_treemap.apply(matches_combo, axis=1)]
                    after_kpi = len(filtered_treemap)
                    try:
                        print(f"DEBUG: filtered_treemap reduced from {before_kpi} to {after_kpi} by KPI likely filter")
                    except Exception:
                        pass
        
        # Calculate KPIs from filtered treemap
        if not filtered_treemap.empty:
            kpi_by_status = (
                filtered_treemap.groupby("Project Status")
                .agg({"Production Additions": "sum"})
                .reset_index()
            )
            filtered_kpi = kpi_by_status.copy()
        else:
            # If no data after filtering, use empty dataframe or show zeros
            filtered_kpi = pd.DataFrame(columns=["Project Status", "Production Additions"])
            # Add zero rows for each status
            for status in ["Under Development", "Onstream", "Appraisal"]:
                filtered_kpi = pd.concat([
                    filtered_kpi,
                    pd.DataFrame([{"Project Status": status, "Production Additions": 0.0}])
                ], ignore_index=True)
        
        # Filter table data
        filtered_table = table_df.copy()
        
        # Remove quarterly rows - keep only unique projects (use first occurrence)
        # The table has multiple rows per project (one per quarter in Measure Names)
        if "Project Name" in filtered_table.columns:
            # Filter out rows where Measure Names contains quarter info (like "2025_Q1")
            # Keep only rows where Measure Names is empty or contains non-quarter info
            if "Measure Names" in filtered_table.columns:
                # Keep rows where Measure Names is empty or doesn't match quarter pattern
                quarter_pattern = r'^\d{4}_Q[1-4]$'
                mask = ~filtered_table["Measure Names"].astype(str).str.match(quarter_pattern, na=False)
                filtered_table = filtered_table[mask]
            
            # Get unique projects (keep first occurrence)
            filtered_table = filtered_table.drop_duplicates(subset=["Project Name"], keep='first')
        
        print(f"DEBUG: region_filter: {region_filter}")
        # Apply region filter to table
        if region_filter:
            if isinstance(region_filter, list):
                if len(region_filter) > 0 and "Region" in filtered_table.columns:
                    filtered_table = filtered_table[filtered_table["Region"].isin(region_filter)]
            elif region_filter != "(All)":
                if "Region" in filtered_table.columns:
                    filtered_table = filtered_table[filtered_table["Region"] == region_filter]
        
        # Apply likely filter to table (inclusive: selections are ORed)
        if likely_filter:
            filter_values = likely_filter
            if isinstance(likely_filter, list):
                if 'All' in likely_filter and len(likely_filter) > 1:
                    filter_values = [v for v in likely_filter if v != 'All']
                if not likely_filter or (len(likely_filter) == 1 and likely_filter[0] == 'All'):
                    filter_values = None

            if filter_values is not None:
                # Find likely column name in table (flexible matching)
                likely_col = None
                for col in filtered_table.columns:
                    col_lower = col.lower()
                    if 'likely' in col_lower and ('go' in col_lower or 'ahead' in col_lower):
                        likely_col = col
                        break

                if likely_col is not None:
                    col_upper = filtered_table[likely_col].astype(str).str.upper()
                    selected_values = filter_values if isinstance(filter_values, list) else [filter_values]
                    mask = pd.Series(False, index=col_upper.index)
                    for v in selected_values:
                        v_str = str(v).strip()
                        v_up = v_str.upper()
                        if v_up == 'ALL' or v == 'All':
                            mask |= pd.Series(True, index=col_upper.index)
                        elif v_up == '' or v_str.lower() == 'blank':
                            mask |= (col_upper == '')
                        elif v_up.startswith('Y') or v_up == 'YES':
                            mask |= col_upper.str.startswith('Y')
                        elif v_up.startswith('N'):
                            mask |= col_upper.str.startswith('N')
                        elif v_up.startswith('UNCERT') or v_up.startswith('U'):
                            mask |= col_upper.str.startswith('U')

                    filtered_table = filtered_table[mask]
        
        # Check if a Project Status block was clicked.
        # Use the click_selection store as the source of truth for selection/deselection.
        clicked_project_status = None
        clicked_production_additions = None

        # Determine selection (dict with key/metadata) from store; fall back to string label
        selection = click_selection if click_selection is not None else None
        selection_type = None
        clicked_label = None
        sel_region = None
        sel_status = None
        sel_play = None

        if isinstance(selection, dict):
            selection_type = selection.get("type")
            clicked_label = selection.get("label") or selection.get("key")
            sel_region = selection.get("region")
            sel_status = selection.get("project_status")
            sel_play = selection.get("play_type")
        elif selection:
            clicked_label = str(selection).strip()

        if clicked_label:
            print(f"DEBUG: Using click selection label: {clicked_label}")

        # Apply filters / KPI based on selection type
        if selection_type == "region" and sel_region:
            if "Region" in filtered_table.columns:
                filtered_table = filtered_table[filtered_table["Region"] == sel_region]
        elif selection_type == "status":
            # Compute KPI value for the selected status (scoped to region/play type when provided)
            sel_mask = filtered_treemap["Project Status"] == sel_status if sel_status else pd.Series([False] * len(filtered_treemap))
            if sel_region:
                sel_mask = sel_mask & (filtered_treemap["Region"] == sel_region)
            if sel_play:
                sel_mask = sel_mask & (filtered_treemap["Play Type"] == sel_play)
            status_df = filtered_treemap[sel_mask]
            clicked_project_status = sel_status
            if not status_df.empty:
                clicked_production_additions = float(status_df["Production Additions"].sum())
            else:
                clicked_production_additions = 0.0
            print(f"DEBUG: Clicked status={clicked_project_status}, value={clicked_production_additions}")

            # Filter details table accordingly
            if sel_region and "Region" in filtered_table.columns:
                filtered_table = filtered_table[filtered_table["Region"] == sel_region]
            if sel_status and "Project Status" in filtered_table.columns:
                filtered_table = filtered_table[filtered_table["Project Status"] == sel_status]
            if sel_play and "Play Type" in filtered_table.columns:
                filtered_table = filtered_table[filtered_table["Play Type"] == sel_play]
        elif clicked_label:
            # Fallback for legacy string-based selection
            if "Region" in filtered_table.columns and clicked_label in filtered_table["Region"].values:
                filtered_table = filtered_table[filtered_table["Region"] == clicked_label]

            if " - " in clicked_label:
                parts = clicked_label.split(" - ", 1)
                if len(parts) == 2:
                    project_status = parts[0].strip()
                    play_type = parts[1].strip()

                    if project_status in ["Under Development", "Onstream", "Appraisal"]:
                        clicked_project_status = project_status
                        status_df = filtered_treemap[filtered_treemap["Project Status"] == project_status]
                        if not status_df.empty:
                            clicked_production_additions = float(status_df["Production Additions"].sum())
                        else:
                            clicked_production_additions = 0.0
                        print(f"DEBUG: Clicked status={clicked_project_status}, value={clicked_production_additions}")

                    if "Project Status" in filtered_table.columns:
                        filtered_table = filtered_table[filtered_table["Project Status"] == project_status]
                    if "Play Type" in filtered_table.columns:
                        filtered_table = filtered_table[filtered_table["Play Type"] == play_type]
        
        # Create KPI table - show clicked status if available, otherwise show all
        # When a Project Status block is clicked, replace the Worldwide Oil Capacity Additions table
        print(f"DEBUG: Final check - clicked_project_status={clicked_project_status}, clicked_production_additions={clicked_production_additions}")
        if clicked_project_status is not None and clicked_production_additions is not None:
            print(f"DEBUG: Creating clicked status table for {clicked_project_status}")
            # Create table with clicked status and Grand Total
            # This replaces the Worldwide Oil Capacity Additions table
            try:
                kpi_table = create_kpi_table_for_clicked_status(clicked_project_status, clicked_production_additions)
            except Exception as e:
                # Fallback to normal table if there's an error
                print(f"Error creating clicked status table: {e}")
                import traceback
                traceback.print_exc()
                kpi_table = create_kpi_table(filtered_kpi)
        else:
            # Create normal KPI table with all statuses (Worldwide Oil Capacity Additions)
            # This is the default table shown when no Project Status block is clicked
            kpi_table = create_kpi_table(filtered_kpi)
        
        # Normalize Likely Go-ahead and Sanctioned columns for display (Y->Yes, N->No)
        def _map_bool_display(series):
            return series.astype(str).str.strip().apply(
                lambda x: 'Yes' if str(x).strip().upper().startswith('Y') or str(x).strip().lower() == 'true'
                else ('No' if str(x).strip().upper().startswith('N') or str(x).strip().lower() == 'false' else x)
            )

        if filtered_table is not None and not filtered_table.empty:
            for col in filtered_table.columns:
                col_lower = col.lower()
                if 'likely' in col_lower and ('go' in col_lower or 'ahead' in col_lower):
                    filtered_table[col] = _map_bool_display(filtered_table[col])
                if col_lower == 'sanctioned':
                    filtered_table[col] = _map_bool_display(filtered_table[col])

        # Create project details table
        details_table = create_project_details_table(filtered_table)
        
        return kpi_table, details_table

    @dash_app.callback(
        Output('download-status-chart-csv', 'data'),
        Input('btn-export-status-chart-csv', 'n_clicks'),
        State('projects-status-region-filter', 'value'),
        State('projects-status-likely-filter', 'value'),
        State('projects-status-treemap-store', 'data'),
        State('projects-status-table-store', 'data'),
        prevent_initial_call=True
    )
    def export_status_chart_data(n_clicks, region_filter, likely_filter, treemap_store, table_store):
        if n_clicks > 0:
            if treemap_store:
                df = pd.DataFrame(treemap_store)
            else:
                df = load_treemap_data()
            
            if not df.empty:
                # Apply filters as in update_treemap
                # Region filter
                if region_filter:
                    if isinstance(region_filter, list):
                        if len(region_filter) > 0:
                            df = df[df["Region"].isin(region_filter)]
                    elif region_filter != "(All)":
                        df = df[df["Region"] == region_filter]
                
                # Likely filter
                if likely_filter:
                    if table_store:
                        table_df = pd.DataFrame(table_store)
                    else:
                        table_df = load_table_data()
                    
                    filter_values = likely_filter
                    if isinstance(likely_filter, list):
                        if 'All' in likely_filter and len(likely_filter) > 1:
                            filter_values = [v for v in likely_filter if v != 'All']
                        if not likely_filter or (len(likely_filter) == 1 and likely_filter[0] == 'All'):
                            filter_values = None

                    if filter_values is not None:
                        likely_col = None
                        for col in table_df.columns:
                            lc = col.lower()
                            if 'likely' in lc and ('go' in lc or 'ahead' in lc):
                                likely_col = col
                                break
                        if likely_col:
                            col_upper = table_df[likely_col].astype(str).str.upper()
                            selected_vals = filter_values if isinstance(filter_values, list) else [filter_values]
                            mask = pd.Series(False, index=col_upper.index)
                            for v in selected_vals:
                                v_str, v_up = str(v).strip(), str(v).strip().upper()
                                if v_up == 'ALL' or v == 'All':
                                    mask |= pd.Series(True, index=col_upper.index)
                                elif v_up == '' or v_str.lower() == 'blank':
                                    mask |= (col_upper == '')
                                elif v_up.startswith('Y') or v_up == 'YES':
                                    mask |= col_upper.str.startswith('Y')
                                elif v_up.startswith('N'):
                                    mask |= col_upper.str.startswith('N')
                                elif v_up.startswith('UNCERT') or v_up.startswith('U'):
                                    mask |= col_upper.str.startswith('U')
                            matching_projects = table_df[mask]
                            if not matching_projects.empty:
                                combos = set()
                                for _, row in matching_projects.iterrows():
                                    combos.add((str(row.get("Region", "")).strip(), str(row.get("Play Type", "")).strip(), str(row.get("Project Status", "")).strip()))
                                def matches_combo(r):
                                    return (str(r.get("Region", "")).strip(), str(r.get("Play Type", "")).strip(), str(r.get("Project Status", "")).strip()) in combos
                                df = df[df.apply(matches_combo, axis=1)]
                
                # Format for export
                export_df = df.rename(columns={'Production Additions': "Production Additions ('000 b/d)"})
                return dcc.send_data_frame(export_df.to_csv, "projects_status_chart_data.csv", index=False)
        return dash.no_update

    @dash_app.callback(
        Output('download-status-table-csv', 'data'),
        Input('btn-export-status-table-csv', 'n_clicks'),
        State('projects-status-region-filter', 'value'),
        State('projects-status-likely-filter', 'value'),
        State('projects-status-click-selection', 'data'),
        State('projects-status-table-store', 'data'),
        prevent_initial_call=True
    )
    def export_status_table_data(n_clicks, region_filter, likely_filter, click_selection, table_store):
        if n_clicks > 0:
            if table_store:
                df = pd.DataFrame(table_store)
            else:
                df = load_table_data()
            
            if not df.empty:
                # Apply filter logic as in update_tables
                # Unique projects
                if "Project Name" in df.columns:
                    if "Measure Names" in df.columns:
                        quarter_pattern = r'^\d{4}_Q[1-4]$'
                        df = df[~df["Measure Names"].astype(str).str.match(quarter_pattern, na=False)]
                    df = df.drop_duplicates(subset=["Project Name"], keep='first')
                
                # Region filter
                if region_filter:
                    if isinstance(region_filter, list):
                        if len(region_filter) > 0 and "Region" in df.columns:
                            df = df[df["Region"].isin(region_filter)]
                    elif region_filter != "(All)" and "Region" in df.columns:
                        df = df[df["Region"] == region_filter]
                
                # Likely filter
                if likely_filter:
                    filter_values = likely_filter
                    if isinstance(likely_filter, list):
                        if 'All' in likely_filter and len(likely_filter) > 1:
                            filter_values = [v for v in likely_filter if v != 'All']
                        if not likely_filter or (len(likely_filter) == 1 and likely_filter[0] == 'All'):
                            filter_values = None
                    if filter_values is not None:
                        likely_col = None
                        for col in df.columns:
                            lc = col.lower()
                            if 'likely' in lc and ('go' in lc or 'ahead' in lc):
                                likely_col = col
                                break
                        if likely_col:
                            col_upper = df[likely_col].astype(str).str.upper()
                            selected_vals = filter_values if isinstance(filter_values, list) else [filter_values]
                            mask = pd.Series(False, index=col_upper.index)
                            for v in selected_vals:
                                v_str, v_up = str(v).strip(), str(v).strip().upper()
                                if v_up == 'ALL' or v == 'All':
                                    mask |= pd.Series(True, index=col_upper.index)
                                elif v_up == '' or v_str.lower() == 'blank':
                                    mask |= (col_upper == '')
                                elif v_up.startswith('Y') or v_up == 'YES':
                                    mask |= col_upper.str.startswith('Y')
                                elif v_up.startswith('N'):
                                    mask |= col_upper.str.startswith('N')
                                elif v_up.startswith('UNCERT') or v_up.startswith('U'):
                                    mask |= col_upper.str.startswith('U')
                            df = df[mask]
                
                # Treemap click selection filter
                if isinstance(click_selection, dict):
                    sel_type = click_selection.get("type")
                    sel_region = click_selection.get("region")
                    sel_status = click_selection.get("project_status")
                    sel_play = click_selection.get("play_type")
                    
                    if sel_type == "region" and sel_region and "Region" in df.columns:
                        df = df[df["Region"] == sel_region]
                    elif sel_type == "status":
                        if sel_region and "Region" in df.columns:
                            df = df[df["Region"] == sel_region]
                        if sel_status and "Project Status" in df.columns:
                            df = df[df["Project Status"] == sel_status]
                        if sel_play and "Play Type" in df.columns:
                            df = df[df["Play Type"] == sel_play]

                # Map column names for export
                display_name_map = {
                    'Opec_group': 'Group',
                    'field_type': 'Field Type',
                    'field': 'Field/Block',
                    'play_type': 'Play Type',
                    'likely_goahead': 'Likely To Go Ahead',
                }
                df = df.rename(columns=display_name_map)
                
                # Format boolean columns
                def _map_export_bool(series):
                    return series.astype(str).str.strip().apply(
                        lambda x: 'Yes' if str(x).upper().startswith('Y') or str(x).lower() == 'true'
                        else ('No' if str(x).upper().startswith('N') or str(x).lower() == 'false' else x)
                    )
                for col in ['Likely To Go Ahead', 'Sanctioned']:
                    if col in df.columns:
                        df[col] = _map_export_bool(df[col])

                return dcc.send_data_frame(df.to_csv, "projects_status_table_data.csv", index=False)
        return dash.no_update


def create_kpi_table_for_clicked_status(project_status, production_additions):
    """Create KPI table for clicked Project Status with Grand Total"""
    # Format the production additions value (remove decimals if whole number)
    if isinstance(production_additions, (int, float)):
        if production_additions == int(production_additions):
            formatted_value = f"{int(production_additions):,}"
        else:
            formatted_value = f"{production_additions:,.1f}"
    else:
        formatted_value = str(production_additions)
    
    # Create table data with clicked status and Grand Total
    table_data = [
        {
            "Project Status": project_status,
            "Production Additions": formatted_value
        },
        {
            "Project Status": "Grand Total",
            "Production Additions": formatted_value
        }
    ]
    
    columns = [
        {"name": "Project Status", "id": "Project Status"},
        {"name": "Production Additions ('000 b/d)", "id": "Production Additions"}
    ]
    
    return dash_table.DataTable(
        id='projects-status-kpi-table',
        columns=columns,
        data=table_data,
        style_table={
            'overflowX': 'auto',
            'border': '1px solid #dee2e6',
            'backgroundColor': 'white'
        },
        style_cell={
            'textAlign': 'center',
            'padding': '8px',
            'fontSize': '12px',
            'fontFamily': 'Arial, sans-serif',
            'border': '1px solid #dee2e6',
            'color': '#2c3e50'
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': 'bold',
            'border': '1px solid #dee2e6',
            'textAlign': 'center',
            'fontSize': '12px',
            'fontFamily': 'Arial, sans-serif',
            'color': '#2c3e50'
        },
        style_data={
            'border': '1px solid #dee2e6',
            'backgroundColor': 'white'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa'
            },
            {
                'if': {'filter_query': "{Project Status} = 'Grand Total'"},
                'fontWeight': 'bold',
                'backgroundColor': '#e9ecef'
            }
        ],
        page_action='none',
        sort_action='native'
    )


def create_kpi_table(df):
    """Create KPI table showing worldwide capacity additions"""
    if df is None or df.empty:
        return html.Div("No KPI data available.", style={'color': '#666666', 'padding': '20px'})
    
    # Prepare table data
    table_data = []
    for _, row in df.iterrows():
        if "Project Status" in row and "Production Additions" in row:
            table_data.append({
                "Project Status": row["Project Status"],
                "Production Additions": f"{row['Production Additions']:,.1f}"
            })
    
    if not table_data:
        return html.Div("No KPI data available.", style={'color': '#666666', 'padding': '20px'})
    
    columns = [
        {"name": "Project Status", "id": "Project Status"},
        {"name": "Production Additions ('000 b/d)", "id": "Production Additions"}
    ]
    
    # Append Grand Total row
    try:
        # Attempt to compute numeric total from original df
        grand_total_val = 0.0
        if "Production Additions" in df.columns:
            grand_total_val = float(df["Production Additions"].astype(float).sum())
        elif table_data:
            # Fallback: sum values parsed from formatted strings in table_data
            for r in table_data:
                try:
                    grand_total_val += float(str(r.get("Production Additions", "0")).replace(',', ''))
                except Exception:
                    pass
    except Exception:
        grand_total_val = 0.0

    table_data.append({
        "Project Status": "Grand Total",
        "Production Additions": f"{grand_total_val:,.1f}"
    })

    return dash_table.DataTable(
        id='projects-status-kpi-table',
        columns=columns,
        data=table_data,
        style_table={
            'overflowX': 'auto',
            'border': '1px solid #dee2e6',
            'backgroundColor': 'white'
        },
        style_cell={
            'textAlign': 'center',
            'padding': '8px',
            'fontSize': '12px',
            'fontFamily': 'Arial, sans-serif',
            'border': '1px solid #dee2e6',
            'color': '#2c3e50'
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': 'bold',
            'border': '1px solid #dee2e6',
            'textAlign': 'center',
            'fontSize': '12px',
            'fontFamily': 'Arial, sans-serif',
            'color': '#2c3e50'
        },
        style_data={
            'border': '1px solid #dee2e6',
            'backgroundColor': 'white'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa'
            },
            {
                'if': {'filter_query': "{Project Status} = 'Grand Total'"},
                'fontWeight': 'bold',
                'backgroundColor': '#e9ecef'
            }
        ],
        page_action='none',
        sort_action='native'
    )


def create_project_details_table(df):
    """Create project details table with all columns and rows"""
    if df is None or df.empty:
        return html.Div("No project data available.", 
                       style={'color': '#666666', 'padding': '20px'})
    
    # Exclude columns that are not useful for display (metadata columns)
    exclude_columns = ['Source', 'Copyright', 'Measure Names', 'Measure Values']
    
    # Get all columns except excluded ones
    all_columns = [col for col in df.columns if col not in exclude_columns]
    
    if not all_columns:
        return html.Div("No displayable columns found.", style={'color': '#666666', 'padding': '20px'})
    
    # Define the new columns to add after 'Sulfur'
    new_columns_after_sulfur = [
        'Operator Share %',
        'Partner1 Share %',
        'Partner2 Share %',
        'Partner3 Share %',
        'Partner4 Share %',
        'Partner5 Share %',
        '2024_Q1', '2024_Q2', '2024_Q3', '2024_Q4',
        '2025_Q1', '2025_Q2', '2025_Q3', '2025_Q4',
        '2026_Q1', '2026_Q2', '2026_Q3', '2026_Q4',
        '2027_Q1', '2027_Q2', '2027_Q3', '2027_Q4',
        '2028_Q1', '2028_Q2', '2028_Q3', '2028_Q4',
        '2029_Q1', '2029_Q2', '2029_Q3', '2029_Q4'
    ]
    
    # Find the position of 'Sulfur' column
    sulfur_index = None
    for i, col in enumerate(all_columns):
        if col == 'Sulfur':
            sulfur_index = i
            break
    
    # Add new columns to dataframe if they don't exist
    for col in new_columns_after_sulfur:
        if col not in df.columns:
            df[col] = None  # Add as empty column
    
    # Rebuild all_columns list with new columns inserted after Sulfur
    if sulfur_index is not None:
        # Split columns at Sulfur position
        before_sulfur = all_columns[:sulfur_index + 1]  # Include Sulfur
        after_sulfur = [col for col in all_columns[sulfur_index + 1:] if col not in new_columns_after_sulfur]
        
        # Insert new columns after Sulfur
        all_columns = before_sulfur + new_columns_after_sulfur + after_sulfur
    else:
        # If Sulfur not found, append new columns at the end
        all_columns = all_columns + [col for col in new_columns_after_sulfur if col not in all_columns]
    
    # Ensure all columns exist in dataframe (add missing ones)
    for col in all_columns:
        if col not in df.columns:
            df[col] = None
    
    # Apply data formatting before creating the table
    for col in df.columns:
        if any(q in col for q in ['_Q1', '_Q2', '_Q3', '_Q4']) or 'Share %' in col:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].apply(lambda x: f'{x:,.3f}' if pd.notna(x) and x != 0 else '')
    
    bool_display_map = {
        'Y': 'Yes', 'N': 'No', 'true': 'Yes', 'false': 'No', 'True': 'Yes', 'False': 'No'
    }
    
    # Identify bool columns (likely_goahead might be display name or ID)
    for col in df.columns:
        if col.lower() in ['likely_goahead', 'sanctioned']:
            df[col] = df[col].astype(str).str.strip().map(bool_display_map).fillna(df[col])
    
    # Preserve full comments for tooltips, but shorten comments in the displayed table
    if 'Comments' in df.columns:
        original_comments = df['Comments'].copy()
        df['Comments'] = df['Comments'].astype(str).apply(lambda x: (x[:10] + '...') if len(str(x)) > 10 else x)
    else:
        original_comments = pd.Series([''] * len(df))

    # Prepare table data with ALL rows (no limit) from the modified (truncated) dataframe
    table_data = df[all_columns].to_dict('records')

    # Build display name mapping and column widths to match projects_by_time.py
    column_widths = {
        'Project Name': '180px',
        'likely_goahead': '100px',
        'Country': '120px',
        'Region': '120px',
        'Opec_group': '140px',
        'field_type': '100px',
        'field': '150px',
        'play_type': '120px',
        'Hydrocarbon': '120px',
        'Associated Crude': '140px',
        'Depth': '80px',
        'Operator': '120px',
        'Partner1': '100px',
        'Partner2': '100px',
        'Partner3': '100px',
        'Partner4': '100px',
        'Partner5': '100px',
        'First Oil Year': '100px',
        'Sanctioned': '80px',
        'Comments': '120px',
        'Project Status': '120px',
        'Gas Reserves (mmboe)': '140px',
        'Liquids Reserves (mmbbl)': '150px',
        'Total Reserves (mmboe)': '150px',
        'API': '80px',
        'Sulfur': '80px'
    }

    display_name_map = {
        'Opec_group': 'Group',
        'field_type': 'Field Type',
        'field': 'Field/Block',
        'play_type': 'Play Type',
        'likely_goahead': 'Likely To Go Ahead',
    }

    # Create columns configuration with display names and width constraints
    columns = []
    width_styles = []

    for col in all_columns:
        display_name = display_name_map.get(col, col)
        col_def = {'name': display_name, 'id': col}
        if col in column_widths:
            width = column_widths[col]
            width_styles.append({
                'if': {'column_id': col},
                'minWidth': width,
                'width': width,
                'maxWidth': width,
            })
        
        # Right align numeric columns
        numeric_cols_static = [
            'Gas Reserves (mmboe)', 'Liquids Reserves (mmbbl)', 'Total Reserves (mmboe)',
            'API', 'Sulfur', 'First Oil Year',
            'Operator Share %', 'Partner1 Share %', 'Partner2 Share %', 
            'Partner3 Share %', 'Partner4 Share %', 'Partner5 Share %'
        ]
        is_quarter = len(col) == 7 and col[4] == '_' and col[:4].isdigit() and col[5:] in ['Q1', 'Q2', 'Q3', 'Q4']
        
        if col in numeric_cols_static or is_quarter:
             width_styles.append({
                'if': {'column_id': col},
                'textAlign': 'right'
            })

        columns.append(col_def)

    # Prepare tooltip data for all columns
    tooltip_data = []
    for idx, row in df.iterrows():
        tip_row = {}
        for col in all_columns:
            if col == 'Comments':
                val = str(original_comments.loc[idx]) if idx in original_comments.index else ''
            else:
                val = str(row[col])
            
            val = val.strip()
            if val and val.lower() != 'nan' and val != 'None':
                # Only show tooltip for long values (>14 chars) or Comments
                if col == 'Comments' or len(val) > 14:
                    tip_row[col] = {'value': val, 'type': 'text'}
        tooltip_data.append(tip_row)

    table = dash_table.DataTable(
        id='projects-status-details-table',
        columns=columns,
        data=table_data,
        tooltip_data=tooltip_data,
        tooltip_duration=None,
        fixed_rows={'headers': True},
        style_table={
            'overflowX': 'auto',
            'overflowY': 'auto',
            'maxHeight': '600px',
            'border': '1px solid #ddd',
            'backgroundColor': 'white',
            'width': '100%'
        },
        style_cell={
            'textAlign': 'left',
            'padding': '8px',
            'fontSize': '12px',
            'fontFamily': 'Lato, sans-serif',
            'color': 'rgb(27, 54, 93)',
            'whiteSpace': 'nowrap',
            'height': 'auto',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
            'maxWidth': '180px'
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': 'bold',
            'fontFamily': 'Lato, sans-serif',
            'color': 'rgb(27, 54, 93)',
            'border': '1px solid #ddd',
            'textAlign': 'center'
        },
        style_data={
            'border': '1px solid #ddd',
            'whiteSpace': 'nowrap',
            'fontFamily': 'Lato, sans-serif',
            'color': 'rgb(27, 54, 93)',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f9f9f9'
            }
        ],
        style_cell_conditional=width_styles,
        sort_action='native',
        filter_action='native',
        css=[{
            'selector': '.dash-table-tooltip',
            'rule': 'font-size: 10px !important; font-family: Lato, sans-serif !important; color: rgb(27, 54, 93) !important; max-width: 400px !important; white-space: normal !important; word-wrap: break-word !important; line-height: 1.4 !important; padding: 6px 8px !important;'
        }, {
            'selector': '.dash-table-container .row:last-child',
            'rule': 'display: none !important;'
        }, {
            'selector': '.previous-page, .next-page, .first-page, .last-page, .page-number, .page-number--current',
            'rule': 'display: none !important;'
        }]
    )
    
    return table

