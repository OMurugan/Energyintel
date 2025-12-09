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
        fig.update_layout(height=700, plot_bgcolor="white", paper_bgcolor="white", margin=dict(l=0, r=0, t=0, b=0))
        return fig
    
    filtered_df = df.copy()
    print(f"DEBUG: region filter0001: {region_filter}")
    # Apply region filter (now handles list of regions)
    if region_filter:
        if isinstance(region_filter, list):
            if len(region_filter) > 0:
                # Filter to selected regions
                filtered_df = filtered_df[filtered_df["Region"].isin(region_filter)]
        elif region_filter != "(All)":
            # Single region (backward compatibility)
            filtered_df = filtered_df[filtered_df["Region"] == region_filter]
    
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
        fig.update_layout(height=700, plot_bgcolor="white", paper_bgcolor="white", margin=dict(l=0, r=0, t=0, b=0))
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
    grouped = grouped[grouped["Production Additions"] > 0]
    
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
        fig.update_layout(height=700, plot_bgcolor="white", paper_bgcolor="white", margin=dict(l=0, r=0, t=0, b=0))
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
    for region in ordered_regions:
        region_df = grouped[grouped["Region"] == region]
        if region_df.empty:
            continue
        
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
        if selected_label:
            for lab, col in zip(labels, colors):
                try:
                    is_match = (str(lab).strip() == str(selected_label).strip())
                except Exception:
                    is_match = False
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
                tiling=dict(pad=1, packing="squarify", squarifyratio=1.0),
                maxdepth=2,
                pathbar=dict(visible=True, side="top", thickness=20, edgeshape=">"),
                domain=domain,
                root=dict(color="rgba(255,255,255,0)")
            )
        )
    
    fig.update_layout(
        title=dict(
            text="Total Capacity Additions 2025 Q1 - 2029 Q4",
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
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#cccccc",
            font_size=12,
            font_family="Arial, sans-serif",
            align="left"
        )
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
                dcc.Graph(
                    id='projects-status-treemap',
                    style={'height': '700px'},
                    config={'displayModeBar': False}
                )
            ], style={'width': '75%', 'float': 'left', 'paddingRight': '20px'}),
            
            # Right panel (25% width)
            html.Div([
                # Region Filter (using same design as Carbon Intensity filter)
                html.Div([
                    html.Label("Region:", style={
                        'fontWeight': '600', 
                        'marginBottom': '12px', 
                        'fontSize': '13px',
                        'color': '#2c3e50',
                        'fontFamily': 'Arial, sans-serif'
                    }),
                    html.Div(
                        id='region-legend-container',
                        children=[]  # Will be populated by callback
                    )
                ], style={'marginBottom': '25px', 'padding': '15px', 'border': '1px solid #e0e0e0', 'borderRadius': '5px', 'backgroundColor': '#fafafa'}),
                
                # Hidden region filter checklist
                dcc.Checklist(
                    id='projects-status-region-filter',
                    options=[],  # Will be populated by callback
                    value=[],  # Will be populated by callback
                    style={'display': 'none'}
                ),
                
                # Store region legend item IDs for callback
                html.Div(id='region-legend-items-store', style={'display': 'none'}, children=[]),
                
                # Store to track if region filter has been initialized (prevents overwriting on subsequent updates)
                dcc.Store(id='region-filter-initialized', data=False),
                
                # Store to cache treemap dataframe (avoids repeated DB queries)
                dcc.Store(id='projects-status-treemap-store', data=[]),
                # Store to hold region selection controlled by legend
                dcc.Store(id='projects-status-region-selection', data=[]),
                # Store to hold treemap click selection (selected label). None => no selection.
                dcc.Store(id='projects-status-click-selection', data=None),
                
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
                html.H4(
                    "Project Details",
                    style={
                        'color': '#E75224',
                        'marginTop': '30px',
                        'marginBottom': '15px',
                        'fontSize': '18px',
                        'fontWeight': 'bold'
                    }
                ),
                html.Div(
                    id='projects-status-table-container',
                    style={'marginTop': '10px', 'width': '100%'}
                )
            ], style={'width': '100%', 'clear': 'both', 'marginTop': '20px'})
        ], style={'padding': '20px'})
    ], className='tab-content', style={'backgroundColor': '#f5f7fa', 'padding': '20px', 'minHeight': '100vh'})


def register_callbacks(dash_app, server):
    """Register all callbacks for Projects by Status"""
    
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
        [Output('projects-status-region-filter', 'options'),
         Output('projects-status-region-filter', 'value', allow_duplicate=True),
         Output('region-legend-items-store', 'children'),
         Output('region-filter-initialized', 'data')],
        Input('current-submenu', 'data'),
        State('projects-status-region-filter', 'value'),
        State('region-filter-initialized', 'data'),
        State('projects-status-treemap-store', 'data'),
        prevent_initial_call='initial_duplicate'
    )
    def update_region_filter_options(current_submenu, current_filter_value, is_initialized, treemap_store):
        """Update region filter options when page is accessed"""
        if current_submenu != 'projects-status':
            return [], dash.no_update, [], dash.no_update
        
        # Prefer cached treemap store if available to avoid extra DB call
        if treemap_store:
            treemap_df = pd.DataFrame(treemap_store)
        else:
            treemap_df = load_treemap_data()
        regions = []
        
        if not treemap_df.empty and "Region" in treemap_df.columns:
            unique_regions = treemap_df['Region'].dropna().unique().tolist()
            # Order regions according to REGION_ORDER
            ordered_regions = [r for r in REGION_ORDER if r in unique_regions]
            # Add any regions not in REGION_ORDER at the end
            remaining_regions = [r for r in unique_regions if r not in REGION_ORDER]
            ordered_regions.extend(sorted(remaining_regions))
            regions = ordered_regions
        
        options = [{'label': r, 'value': r} for r in regions]
        
        # CRITICAL: Only set default_value on the very first initialization
        # Use is_initialized flag to prevent overwriting the filter value on subsequent updates
        # This ensures Africa is never removed from the filter
        if not is_initialized:
            # First initialization: Set all regions as default, including Africa
            # Build default_value in REGION_ORDER to ensure consistent ordering
            default_value = []
            for region in REGION_ORDER:
                if region in regions:
                    default_value.append(region)
            # Add any remaining regions not in REGION_ORDER
            for region in regions:
                if region not in default_value:
                    default_value.append(region)
            
            # CRITICAL: Verify Africa is included - this is essential
            # Double-check: if Africa exists in regions, it MUST be in default_value
            if 'Africa' in regions:
                if 'Africa' not in default_value:
                    # Force insert Africa at the beginning
                    default_value.insert(0, 'Africa')
                elif default_value[0] != 'Africa':
                    # Africa exists but not first - move it to first position
                    default_value.remove('Africa')
                    default_value.insert(0, 'Africa')
            
            # CRITICAL: Also check if current_filter_value already has all regions
            # If so, preserve it (might have been set by another callback)
            if current_filter_value and isinstance(current_filter_value, list) and len(current_filter_value) > 0:
                # Check if current_filter_value already includes all regions (including Africa)
                if 'Africa' in current_filter_value and len(current_filter_value) == len(regions):
                    # Current value already has all regions - preserve it but ensure Africa is first
                    preserved_value = current_filter_value.copy()
                    if preserved_value[0] != 'Africa':
                        preserved_value.remove('Africa')
                        preserved_value.insert(0, 'Africa')
                    return options, preserved_value, regions, True
            # Mark as initialized to prevent future overwrites
            return options, default_value, regions, True
        else:
            # Already initialized: Only restore Africa if filter value is None/empty (unexpected state)
            # DO NOT add Africa back if user explicitly removed it by clicking
            if current_filter_value is None or (isinstance(current_filter_value, list) and len(current_filter_value) == 0):
                # CRITICAL: If filter value is None or empty after initialization, 
                # it means something reset it - restore all regions including Africa
                restored_value = []
                for region in REGION_ORDER:
                    if region in regions:
                        restored_value.append(region)
                for region in regions:
                    if region not in restored_value:
                        restored_value.append(region)
                # Ensure Africa is first
                if 'Africa' in regions and 'Africa' not in restored_value:
                    restored_value.insert(0, 'Africa')
                elif 'Africa' in restored_value and restored_value[0] != 'Africa':
                    restored_value.remove('Africa')
                    restored_value.insert(0, 'Africa')
                return options, restored_value, regions, dash.no_update
            
            # Already initialized: NEVER overwrite the filter value
            # This allows users to explicitly remove Africa by clicking, and we won't add it back
            # This ensures user interactions are respected
            print(f"DEBUG: update_region_filter_options - Already initialized, preserving current_filter_value: {current_filter_value}")
            return options, dash.no_update, regions, dash.no_update
    
    # Callback to create region legend items dynamically
    @dash_app.callback(
        Output('region-legend-container', 'children'),
        Input('region-legend-items-store', 'children'),
        prevent_initial_call=False
    )
    def create_region_legend_items(regions):
        """Create clickable legend items for regions"""
        if not regions:
            return []
        
        legend_items = []
        for region in regions:
            legend_items.append(
                html.Div([
                    html.Div(style={
                        'width': '18px',
                        'height': '18px',
                        'backgroundColor': get_region_color(region, regions),
                        'border': '2px solid white',
                        'display': 'inline-block',
                        'marginRight': '10px',
                        'verticalAlign': 'middle',
                        'boxShadow': '0 1px 3px rgba(0,0,0,0.2)'
                    }),
                    html.Span(region, style={
                        'fontSize': '12px', 
                        'verticalAlign': 'middle',
                        'fontWeight': '500',
                        'color': '#333333'
                    })
                ], id={'type': 'region-legend-item', 'index': region}, n_clicks=0, style={
                    'marginBottom': '8px', 
                    'display': 'flex', 
                    'alignItems': 'center', 
                    'cursor': 'pointer',
                    'padding': '4px 8px',
                    'borderRadius': '3px',
                    'border': '1px solid transparent'
                })
            )
        
        return legend_items
    
    # Mirror the visible checklist into the legend-driven store so the store is the single source of truth
    @dash_app.callback(
        Output('projects-status-region-selection', 'data'),
        Input('projects-status-region-filter', 'value'),
        prevent_initial_call=False
    )
    def mirror_region_to_store(checklist_value):
        if checklist_value is None:
            return []
        return checklist_value
    
    # Callback to handle Region legend clicks (similar to Carbon Intensity filter)
    @dash_app.callback(
        Output('projects-status-region-filter', 'value', allow_duplicate=True),
        [Input({'type': 'region-legend-item', 'index': ALL}, 'n_clicks')],
        State('projects-status-region-filter', 'value'),
        State('region-legend-items-store', 'children'),
        prevent_initial_call=True
    )
    def toggle_region_filter(n_clicks_list, current_values, all_regions):
        """Toggle Region filter when legend items are clicked"""
        if current_values is None:
            current_values = all_regions if all_regions else []

        ctx = dash.callback_context
        if not ctx.triggered:
            return current_values

        trigger_id = ctx.triggered[0].get('prop_id', '')
        if not trigger_id:
            return current_values

        # Extract pattern id JSON (left of ".n_clicks")
        id_part = trigger_id.split('.')[0]
        try:
            import json
            id_dict = json.loads(id_part.replace("'", '"'))
            toggled_region = id_dict.get('index')
        except Exception:
            toggled_region = None

        if toggled_region:
            if toggled_region in current_values:
                # Remove if already selected
                new_values = [v for v in current_values if v != toggled_region]
            else:
                # Add if not selected
                new_values = current_values + [toggled_region] if current_values else [toggled_region]
            return new_values

        return current_values
    
    # Callback to update region legend item visual states
    @dash_app.callback(
        Output({'type': 'region-legend-item', 'index': MATCH}, 'style'),
        [Input('projects-status-region-filter', 'value'),
         Input('current-submenu', 'data'),
         Input('region-legend-items-store', 'children')],
        State({'type': 'region-legend-item', 'index': MATCH}, 'id'),
        State('projects-status-region-selection', 'data'),
        prevent_initial_call=False
    )
    def update_region_legend_styles(selected_regions, current_submenu, all_regions, item_id, region_selection):
        """Update legend item styles to show which are selected - only when page is active"""
        # Only update styles if this page is currently active
        if current_submenu != 'projects-status':
            base_style = {
                'marginBottom': '8px', 
                'display': 'flex', 
                'alignItems': 'center', 
                'cursor': 'pointer',
                'padding': '4px 8px',
                'borderRadius': '3px',
                'border': '1px solid transparent',
                'opacity': '0.3'
            }
            return base_style
        
        base_style = {
            'marginBottom': '8px', 
            'display': 'flex', 
            'alignItems': 'center', 
            'cursor': 'pointer',
            'padding': '4px 8px',
            'borderRadius': '3px',
            'border': '1px solid transparent'
        }
        
        # Prefer region selection from the region-selection store (legend-driven)
        if region_selection and isinstance(region_selection, list) and len(region_selection) > 0:
            selected_regions = region_selection

        if selected_regions is None or (isinstance(selected_regions, list) and len(selected_regions) == 0):
            return {**base_style, 'opacity': '1.0'}

        
        if all_regions is None:
            all_regions = []
        
        region_name = item_id.get('index') if item_id else None
        
        # Determine if this region should be shown as selected
        is_selected = False
        if region_name:
            # If selected_regions has values, check if region is in it
            if isinstance(selected_regions, list) and len(selected_regions) > 0:
                is_selected = region_name in selected_regions
            # If selected_regions is empty but all_regions is available, assume all are selected
            elif isinstance(all_regions, list) and len(all_regions) > 0:
                is_selected = region_name in all_regions
            # Fallback: if both are empty, show as selected (will be corrected when values are set)
            else:
                is_selected = True
        
        if is_selected:
            style = {**base_style, 'opacity': '1.0'}
        else:
            style = {**base_style, 'opacity': '0.3'}
        
        return style
    
    @dash_app.callback(
        Output('projects-status-treemap', 'figure'),
        [Input('projects-status-region-filter', 'value'),
         Input('projects-status-likely-filter', 'value'),
         Input('current-submenu', 'data'),
         Input('projects-status-click-selection', 'data')],
        [State('projects-status-treemap-store', 'data'),
         State('projects-status-region-selection', 'data')],
        prevent_initial_call=False
    )
    def update_treemap(region_filter, likely_filter, current_submenu, selected_label, treemap_store, region_selection):        
        print(f"DEBUG: update_treemap triggered - current_submenu={current_submenu}, region_filter={region_filter}, likely_filter={likely_filter}, region_selection={region_selection}")
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
            fig.update_layout(height=700, plot_bgcolor="white", paper_bgcolor="white", margin=dict(l=0, r=0, t=0, b=0))
            return fig
        
        # If legend-driven region selection store is present, prefer it
        if region_selection and isinstance(region_selection, list) and len(region_selection) > 0:
            region_filter = region_selection

        # CRITICAL: Only handle None/empty filter on initial load
        # DO NOT add Africa back if user explicitly removed it - respect user's filter selection
        if region_filter is None or (isinstance(region_filter, list) and len(region_filter) == 0):
            # Load data to get all available regions (only for initial load when filter is None/empty)
            if treemap_store:
                df_temp = pd.DataFrame(treemap_store)
            else:
                df_temp = load_treemap_data()
            if not df_temp.empty and "Region" in df_temp.columns:
                all_regions = df_temp['Region'].dropna().unique().tolist()
                # Order according to REGION_ORDER
                ordered_all = [r for r in REGION_ORDER if r in all_regions]
                remaining_all = [r for r in all_regions if r not in REGION_ORDER]
                ordered_all.extend(sorted(remaining_all))
                region_filter = ordered_all
        if treemap_store:
            df = pd.DataFrame(treemap_store)
        else:
            df = load_treemap_data()
        table_df = load_table_data()
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
            clicked_label = None
            if isinstance(point, dict):
                clicked_label = point.get('label') or point.get('customdata') or None
            # Normalize to string
            if clicked_label is None:
                return dash.no_update

            clicked_label = str(clicked_label).strip()
            if current_selection and str(current_selection).strip() == clicked_label:
                # Clear selection
                return None
            # Set new selection
            return clicked_label
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
        [State('projects-status-treemap-store', 'data'),
         State('projects-status-region-selection', 'data')],
        prevent_initial_call=False
    )
    def update_tables(region_filter, likely_filter, click_selection, click_data, current_submenu, treemap_store, region_selection):
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
        
        # If legend-driven selection exists, prefer it
        if region_selection and isinstance(region_selection, list) and len(region_selection) > 0:
            region_filter = region_selection

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

        # Determine clicked_label from click_selection (preferred) or click_data (fallback).
        clicked_label = None
        if click_selection is not None:
            # click_selection is the normalized label stored by the toggle callback
            clicked_label = str(click_selection).strip() if click_selection else None
        else:
            # No selection in store => treat as no click (prevents stale clickData causing selection)
            clicked_label = None

        # If a selection exists, apply filters as before
        if clicked_label:
            print(f"DEBUG: Using click_selection label: {clicked_label}")
            # Check if clicked label is a region (top level)
            if "Region" in filtered_table.columns and clicked_label in filtered_table["Region"].values:
                filtered_table = filtered_table[filtered_table["Region"] == clicked_label]

            # Check if clicked label is a combined "Project Status - Play Type" (second level)
            if " - " in clicked_label:
                parts = clicked_label.split(" - ", 1)
                if len(parts) == 2:
                    project_status = parts[0].strip()
                    play_type = parts[1].strip()

                    # If it's a recognized Project Status, compute clicked KPI
                    if project_status in ["Under Development", "Onstream", "Appraisal"]:
                        clicked_project_status = project_status
                        status_df = filtered_treemap[filtered_treemap["Project Status"] == project_status]
                        if not status_df.empty:
                            clicked_production_additions = float(status_df["Production Additions"].sum())
                        else:
                            clicked_production_additions = 0.0
                        print(f"DEBUG: Clicked status={clicked_project_status}, value={clicked_production_additions}")

                    # Filter details table by both Project Status and Play Type
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
    for col in all_columns:
        display_name = display_name_map.get(col, col)
        col_def = {'name': display_name, 'id': col}
        if col in column_widths:
            col_def['minWidth'] = column_widths[col]
            col_def['maxWidth'] = column_widths[col]
        columns.append(col_def)

    # Prepare tooltip data for Comments column (show full comment on hover)
    tooltip_data = []
    for i, row in enumerate(table_data):
        tooltip_row = {}
        if 'Comments' in row:
            orig = str(original_comments.iloc[i]) if i < len(original_comments) else ''
            if orig and orig != 'nan' and orig.strip():
                tooltip_row['Comments'] = {
                    'value': orig,
                    'type': 'text'
                }
        tooltip_data.append(tooltip_row)

    table = dash_table.DataTable(
        id='projects-status-details-table',
        columns=columns,
        data=table_data,
        tooltip_data=tooltip_data,
        tooltip_duration=None,
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
            'whiteSpace': 'normal',
            'height': 'auto',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis'
        },
        style_cell_conditional=[
            {
                'if': {'column_id': 'Comments'},
                'whiteSpace': 'nowrap',
                'overflow': 'hidden',
                'textOverflow': 'ellipsis',
                'height': 'auto',
                'textAlign': 'left'
            }
        ],
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
            'whiteSpace': 'normal',
            'fontFamily': 'Lato, sans-serif',
            'color': 'rgb(27, 54, 93)'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f9f9f9'
            }
        ],
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
