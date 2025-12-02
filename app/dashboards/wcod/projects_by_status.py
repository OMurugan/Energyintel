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


def get_year_quarter_range():
    """Dynamically calculate min and max year/quarter from data"""
    try:
        table_df = load_table_data()
        if table_df.empty:
            # Default fallback values
            return {
                'min_year': 2025,
                'min_quarter': 1,
                'max_year': 2029,
                'max_quarter': 4,
                'min_year_quarter': '2025 Q1',
                'max_year_quarter': '2029 Q4'
            }
        
        # Check for quarter columns in format YYYY_Q1, YYYY_Q2, etc.
        quarter_cols = [col for col in table_df.columns if '_Q' in str(col)]
        
        # Also check Measure Names column for quarter values
        years_quarters = []
        if 'Measure Names' in table_df.columns:
            measure_values = table_df['Measure Names'].dropna().astype(str)
            # Extract quarter patterns like "2025_Q1"
            for val in measure_values:
                if '_Q' in val:
                    parts = val.split('_Q')
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        year = int(parts[0])
                        quarter = int(parts[1])
                        years_quarters.append((year, quarter))
        
        # Extract from column names
        for col in quarter_cols:
            if '_Q' in str(col):
                parts = str(col).split('_Q')
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    year = int(parts[0])
                    quarter = int(parts[1])
                    years_quarters.append((year, quarter))
        
        if not years_quarters:
            # Default fallback values
            return {
                'min_year': 2025,
                'min_quarter': 1,
                'max_year': 2029,
                'max_quarter': 4,
                'min_year_quarter': '2025 Q1',
                'max_year_quarter': '2029 Q4'
            }
        
        # Find min and max
        min_year, min_quarter = min(years_quarters, key=lambda x: (x[0], x[1]))
        max_year, max_quarter = max(years_quarters, key=lambda x: (x[0], x[1]))
        
        return {
            'min_year': min_year,
            'min_quarter': min_quarter,
            'max_year': max_year,
            'max_quarter': max_quarter,
            'min_year_quarter': f'{min_year} Q{min_quarter}',
            'max_year_quarter': f'{max_year} Q{max_quarter}'
        }
    except Exception as e:
        print(f"Error calculating year/quarter range: {e}")
        # Default fallback values
        return {
            'min_year': 2025,
            'min_quarter': 1,
            'max_year': 2029,
            'max_quarter': 4,
            'min_year_quarter': '2025 Q1',
            'max_year_quarter': '2029 Q4'
        }


def get_quarter_columns_list():
    """Dynamically generate list of quarter columns from min to max year/quarter"""
    try:
        range_info = get_year_quarter_range()
        min_year = range_info['min_year']
        min_quarter = range_info['min_quarter']
        max_year = range_info['max_year']
        max_quarter = range_info['max_quarter']
        
        quarter_cols = []
        current_year = min_year
        current_quarter = min_quarter
        
        while (current_year < max_year) or (current_year == max_year and current_quarter <= max_quarter):
            quarter_cols.append(f'{current_year}_Q{current_quarter}')
            current_quarter += 1
            if current_quarter > 4:
                current_quarter = 1
                current_year += 1
        
        return quarter_cols
    except Exception as e:
        print(f"Error generating quarter columns: {e}")
        # Default fallback
        return [
            '2024_Q1', '2024_Q2', '2024_Q3', '2024_Q4',
            '2025_Q1', '2025_Q2', '2025_Q3', '2025_Q4',
            '2026_Q1', '2026_Q2', '2026_Q3', '2026_Q4',
            '2027_Q1', '2027_Q2', '2027_Q3', '2027_Q4',
            '2028_Q1', '2028_Q2', '2028_Q3', '2028_Q4',
            '2029_Q1', '2029_Q2', '2029_Q3', '2029_Q4'
        ]
import json


def load_treemap_data():
    """Load treemap data from CSV"""
    csv_path = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'project_by_status', 
        'Projects by Status_Treemap_data.csv'
    )
    
    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file not found at {csv_path}")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
        # Clean column names (remove leading/trailing spaces)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        print(f"ERROR loading treemap data: {e}")
        return pd.DataFrame()


def load_table_data():
    """Load project details table data from CSV"""
    csv_path = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'project_by_status',
        'Projects by Status_Table_data.csv'
    )
    
    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file not found at {csv_path}")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        print(f"ERROR loading table data: {e}")
        return pd.DataFrame()


def load_kpi_data():
    """Load KPI table data from CSV"""
    csv_path = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'project_by_status',
        'Project by Status_KPI Table_data.csv'
    )
    
    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file not found at {csv_path}")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        print(f"ERROR loading KPI data: {e}")
        return pd.DataFrame()


def create_treemap_figure(df=None, region_filter=None, likely_filter=None, table_df=None):
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
    print(region_filter,"region_filter002")
    # Apply region filter (now handles list of regions)
    # On initial load, if region_filter is None or empty, show all regions (no filtering)
    # When regions are unselected, filter them out immediately - remove disabled regions from treemap
    if region_filter is not None:
        if isinstance(region_filter, list):
            if len(region_filter) > 0:
                # Filter to ONLY selected regions - unselected/disabled regions are removed immediately
                filtered_df = filtered_df[filtered_df["Region"].isin(region_filter)]
            # If empty list, don't filter (show all regions - initial load state)
        elif region_filter != "(All)":
            # Single region (backward compatibility)
            filtered_df = filtered_df[filtered_df["Region"] == region_filter]
    # If region_filter is None, don't filter (show all regions) - this is the default on initial load
    
    # Apply likely filter by joining with table data if available
    # CRITICAL: On initial load, if likely_filter is None or empty, show all data (no filtering)
    if likely_filter and table_df is not None:
        # Handle checklist - filter out 'ALL' if present with other values
        if isinstance(likely_filter, list):
            # Remove 'ALL' if other values are selected
            if 'ALL' in likely_filter and len(likely_filter) > 1:
                likely_filter = [v for v in likely_filter if v != 'ALL']
            # If only 'ALL' is selected or empty list, show all (no filtering)
            if not likely_filter or (len(likely_filter) == 1 and likely_filter[0] == 'ALL'):
                likely_filter = None
        
        # Only apply filter if likely_filter has actual values (not None or empty)
        if likely_filter and "Likely Go-ahead" in table_df.columns:
            # Get projects matching any of the selected filter values
            # Handle empty string for blank values
            mask = table_df["Likely Go-ahead"].isin(likely_filter)
            if '' in likely_filter:
                mask = mask | table_df["Likely Go-ahead"].isna() | (table_df["Likely Go-ahead"].astype(str).str.strip() == '')
            matching_projects = table_df[mask]
            
            # If we can match by project name or other fields, filter the treemap data
            # For now, the treemap data doesn't have project names, so we'll filter based on
            # Region, Play Type, and Project Status combination
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
                
                # Filter treemap data to only include matching combinations
                def matches_combo(row):
                    combo = (
                        str(row.get("Region", "")),
                        str(row.get("Play Type", "")),
                        str(row.get("Project Status", ""))
                    )
                    return combo in matching_combos
                
                filtered_df = filtered_df[filtered_df.apply(matches_combo, axis=1)]
    
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
    
    # Get unique regions from filtered data
    unique_regions = filtered_df["Region"].dropna().unique().tolist()
    
    # CRITICAL: If region_filter is provided, ensure all selected regions are included
    # even if they have no data after filtering (they should still appear in treemap)
    if region_filter is not None:
        if isinstance(region_filter, list) and len(region_filter) > 0:
            # Add selected regions that might not have data
            for region in region_filter:
                if region not in unique_regions:
                    unique_regions.append(region)
        elif region_filter != "(All)":
            # Single region selected
            if region_filter not in unique_regions:
                unique_regions.append(region_filter)
    
    # Order regions according to REGION_ORDER (keep only regions that exist in data or are selected)
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
    # Filter out zero values, but keep track of which regions had data
    regions_with_data = grouped[grouped["Production Additions"] > 0]["Region"].unique().tolist()
    grouped = grouped[grouped["Production Additions"] > 0]
    
    # CRITICAL: Ensure all regions that should be visible appear in grouped data
    # even if they have no data after filtering (add placeholder rows for regions with no data)
    # This ensures Africa and other regions appear in treemap even if "Likely to Go Ahead" filter removes their data
    
    # Determine which regions should be visible
    regions_to_show = []
    # CRITICAL: Handle empty list the same as None - both mean "show all regions"
    # This ensures Africa and all regions appear on initial load and subsequent updates
    if region_filter is None or (isinstance(region_filter, list) and len(region_filter) == 0):
        # region_filter is None or empty list means "show all regions" (initial load or all selected)
        # Get all regions from the original unfiltered data
        if not df.empty and "Region" in df.columns:
            regions_to_show = df["Region"].dropna().unique().tolist()
            # Order according to REGION_ORDER
            ordered_show = [r for r in REGION_ORDER if r in regions_to_show]
            remaining_show = [r for r in regions_to_show if r not in REGION_ORDER]
            regions_to_show = ordered_show + sorted(remaining_show)
    elif isinstance(region_filter, list) and len(region_filter) > 0:
        # Specific regions selected
        regions_to_show = region_filter
    elif region_filter != "(All)":
        # Single region selected
        regions_to_show = [region_filter]
    # Add placeholder rows for regions that should be visible but have no data
    if regions_to_show:
        for region in regions_to_show:
            if region not in regions_with_data:
                # Region should be visible but has no data - add a placeholder row with small positive value
                # This ensures the region appears in the treemap loop and creates a visible block
                grouped = pd.concat([
                    grouped,
                    pd.DataFrame([{
                        "Region": region,
                        "Project Status": "No Data",
                        "Play Type": "",
                        "Production Additions": 0.1  # Small positive value to make block visible
                    }])
                ], ignore_index=True)
    
    if grouped.empty:
        # If no data after filtering, check if it's because filter is empty/None (initial load)
        # In that case, use original unfiltered data to show all regions
        if region_filter is None or (isinstance(region_filter, list) and len(region_filter) == 0):
            # Re-group with all original data (no filtering)
            grouped = (
                df.groupby(["Region", "Project Status", "Play Type"])
                .agg({"Production Additions": "sum"})
                .reset_index()
            )
            grouped = grouped[grouped["Production Additions"] > 0]
        
        # If still empty after fallback, show message
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
    
    # CRITICAL: If region_filter is provided, ensure all selected regions are included
    # even if they have no data after filtering (they should still appear in treemap)
    # This ensures Africa and other selected regions appear even if "Likely to Go Ahead" filter removes their data
    # CRITICAL: Handle empty list the same as None - both mean "show all regions"
    if region_filter is not None and not (isinstance(region_filter, list) and len(region_filter) == 0):
        if isinstance(region_filter, list) and len(region_filter) > 0:
            # Add selected regions that might not have data after filtering
            for region in region_filter:
                if region not in unique_regions_in_data:
                    unique_regions_in_data.append(region)
        elif region_filter != "(All)":
            # Single region selected
            if region_filter not in unique_regions_in_data:
                unique_regions_in_data.append(region_filter)
    else:
        # region_filter is None or empty list - ensure all regions from original data are included
        if not df.empty and "Region" in df.columns:
            all_regions_from_df = df["Region"].dropna().unique().tolist()
            for region in all_regions_from_df:
                if region not in unique_regions_in_data:
                    unique_regions_in_data.append(region)
    
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
    # CRITICAL: Check if regions are in data OR selected in filter
    latin_america_in = "Latin America" in unique_regions_in_data
    middle_east_in = "Middle East" in unique_regions_in_data
    
    # Check if regions are selected in filter
    if region_filter is not None:
        if isinstance(region_filter, list):
            latin_america_in = latin_america_in or "Latin America" in region_filter
            middle_east_in = middle_east_in or "Middle East" in region_filter
        elif region_filter != "(All)":
            latin_america_in = latin_america_in or region_filter == "Latin America"
            middle_east_in = middle_east_in or region_filter == "Middle East"
    
    if latin_america_in and middle_east_in:
        region_positions["Latin America"] = dict(x=[0.0, left_col_width], y=[0.5, 1.0])
        region_positions["Middle East"] = dict(x=[0.0, left_col_width], y=[0.0, 0.5])
    elif latin_america_in:
        region_positions["Latin America"] = dict(x=[0.0, left_col_width], y=[0.0, 1.0])
    elif middle_east_in:
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
        # CRITICAL: Create position for region if it's in data OR if it's selected in filter
        # This ensures Africa and other selected regions get positions even if filtered out
        region_in_data = region in unique_regions_in_data
        region_selected = False
        if region_filter is not None:
            if isinstance(region_filter, list):
                region_selected = region in region_filter
            elif region_filter != "(All)":
                region_selected = region == region_filter
        
        if region_in_data or region_selected:
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
        # CRITICAL: Create position for region if it's in data OR if it's selected in filter
        # This ensures Africa and other selected regions get positions even if filtered out
        region_in_data = region in unique_regions_in_data
        region_selected = False
        if region_filter is not None:
            if isinstance(region_filter, list):
                region_selected = region in region_filter
            elif region_filter != "(All)":
                region_selected = region == region_filter
        
        if region_in_data or region_selected:
            x_start = right_col_start + (idx * bottom_row_width)
            x_end = right_col_start + ((idx + 1) * bottom_row_width)
            region_positions[region] = dict(
                x=[x_start, x_end],
                y=[bottom_row_y_start, bottom_row_y_end]
            )
    
    # Create figure
    fig = go.Figure()
    
    # Ensure we have regions to display - if no regions after filtering, show all regions
    if len(ordered_regions) == 0:
        # If no regions in filtered data, fall back to all unique regions from original data
        if not df.empty and "Region" in df.columns:
            unique_regions_fallback = df['Region'].dropna().unique().tolist()
            ordered_regions = [r for r in REGION_ORDER if r in unique_regions_fallback]
            remaining_regions = [r for r in unique_regions_fallback if r not in REGION_ORDER]
            ordered_regions.extend(sorted(remaining_regions))
            # Re-group with all regions
            grouped = filtered_df.groupby(["Region", "Project Status", "Play Type"], as_index=False).agg({
                "Production Additions": "sum"
            })
    # Create a separate treemap trace for each region with its specific domain
    # CRITICAL: Ensure all selected regions appear in treemap, even if they have no data after filtering
    for region in ordered_regions:
        region_df = grouped[grouped["Region"] == region]
        
        # CRITICAL: If region should be visible but has no data, the placeholder row should have been added above
        # If region_df is still empty, it means the placeholder wasn't added or was filtered out
        # In that case, skip creating the block (position is already set, but no visual block)
        if region_df.empty:
            # Determine if this region should be visible
            # CRITICAL: Handle empty list the same as None - both mean "show all regions"
            should_show = False
            if region_filter is None or (isinstance(region_filter, list) and len(region_filter) == 0):
                # region_filter is None or empty list means "show all regions" (initial load or all selected)
                # Check if this region exists in the original data
                if not df.empty and "Region" in df.columns:
                    should_show = region in df["Region"].dropna().unique().tolist()
            elif isinstance(region_filter, list) and len(region_filter) > 0:
                # Specific regions selected
                should_show = region in region_filter
            elif region_filter != "(All)":
                # Single region selected
                should_show = region == region_filter
            
            # If region should be visible but has no data, skip creating block
            # The placeholder should have been added above with 0.1 value, but if it's still empty, skip
            if should_show:
                # Region should be visible but has no data - skip creating trace
                # Position is already set above, but no block will be shown
                continue
            else:
                # Region not selected or doesn't exist, skip empty regions
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
                    colors=colors,
                    line=dict(color="white", width=1)
                ),
                tiling=dict(pad=1, packing="squarify", squarifyratio=1.0),
                maxdepth=2,
                pathbar=dict(visible=True, side="top", thickness=20, edgeshape=">"),
                domain=domain,
                root=dict(color="rgba(255,255,255,0)")
            )
        )
    
    # Get dynamic year/quarter range for title
    year_range = get_year_quarter_range()
    title_text = f"Total Capacity Additions {year_range['min_year_quarter']} - {year_range['max_year_quarter']}"
    
    fig.update_layout(
        title=dict(
            text=title_text,  # Dynamic title with year/quarter range from data
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
                
                # Store to track last clicked Project Status for toggle functionality
                dcc.Store(id='last-clicked-status-store', data=None),
                
                # KPI Table Section
                html.Div([
                    html.H4(
                        id='projects-status-kpi-title',  # Will be updated dynamically
                        children="",  # Will be set by callback
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
                            {'label': 'ALL', 'value': 'ALL'},
                            {'label': 'blank', 'value': ''},
                            {'label': 'N', 'value': 'N'},
                            {'label': 'Uncertain', 'value': 'Uncertain'},
                            {'label': 'Y', 'value': 'Yes'}  # Label shows 'Y', value matches CSV 'Yes'
                        ],
                        value=['Yes'],  # Default to 'Yes' on initial load (matches CSV data)
                        style={
                            'fontSize': '12px',
                            'fontFamily': 'Arial, sans-serif'
                        },
                        inputStyle={'marginRight': '8px', 'marginLeft': '0px'},
                        labelStyle={'display': 'block', 'marginBottom': '6px', 'cursor': 'pointer'}
                    )
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
    
    # Callback to update region filter options when page loads
    @dash_app.callback(
        [Output('projects-status-region-filter', 'options'),
         Output('projects-status-region-filter', 'value'),
         Output('region-legend-items-store', 'children')],
        Input('current-submenu', 'data'),
        prevent_initial_call=False
    )
    def update_region_filter_options(current_submenu):
        """Update region filter options when page is accessed"""
        if current_submenu != 'projects-status':
            return [], [], []
        
        # Load data to get available regions
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
        
        # CRITICAL: If no regions found in data, use REGION_ORDER as fallback
        # This ensures we always have regions available, especially on initial load
        if not regions:
            regions = REGION_ORDER.copy()
        
        options = [{'label': r, 'value': r} for r in regions]
        
        # CRITICAL FIX: Set ALL regions as selected by default on initial load
        # This ensures Africa (first item) and all other regions are visible and active
        # Use list comprehension to explicitly include ALL regions from options
        # This guarantees that every region, including the first one (Africa), is selected
        default_value = [opt['value'] for opt in options] if options else []
        
        # Final safety check: If we have regions but default_value is empty, use regions directly
        if regions and not default_value:
            default_value = list(regions)
        
        # CRITICAL: Ensure ALL regions including Africa are explicitly included
        # Double-check that all regions including Africa are in default_value
        if regions:
            for region in regions:
                if region not in default_value:
                    default_value.append(region)
        
        # CRITICAL: Explicitly ensure Africa is included if it exists in regions
        # This is a safety check specifically for Africa (first item in REGION_ORDER)
        if 'Africa' in regions and 'Africa' not in default_value:
            default_value.insert(0, 'Africa')  # Insert at beginning to match REGION_ORDER
        
        # Sort default_value to match REGION_ORDER to ensure consistent ordering
        # This helps ensure Africa (first in REGION_ORDER) is properly included
        if default_value:
            ordered_default = [r for r in REGION_ORDER if r in default_value]
            remaining = [r for r in default_value if r not in REGION_ORDER]
            default_value = ordered_default + sorted(remaining)
        
        # FINAL CRITICAL CHECK: Verify Africa is in default_value before returning
        if 'Africa' in regions and 'Africa' not in default_value:
            # Force add Africa at the beginning
            default_value = ['Africa'] + [r for r in default_value if r != 'Africa']
        
        return options, default_value, regions
    
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
            # CRITICAL: On initial load, all regions should appear active (opacity: 1.0)
            # Set initial style with opacity: 1.0 to ensure all regions are active on initial load
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
                    'border': '1px solid transparent',
                    'opacity': '1.0'  # CRITICAL: Set initial opacity to 1.0 so all regions appear active
                })
            )
        
        return legend_items
    
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
        
        trigger_id = ctx.triggered[0]['prop_id']
        # Extract region name from the pattern component ID
        if 'index' in trigger_id:
            # Parse the region name from the component ID
            import json
            try:
                # The ID is in format like: {"index":"Africa","type":"region-legend-item"}.n_clicks
                id_part = trigger_id.split('.')[0]
                id_dict = json.loads(id_part.replace("'", '"'))
                toggled_region = id_dict.get('index')
                
                if toggled_region:
                    if toggled_region in current_values:
                        # Remove if already selected - this will trigger treemap update to remove region blocks
                        new_values = [v for v in current_values if v != toggled_region]
                        # CRITICAL: If all regions are deselected, return empty list (will show all regions)
                        # Otherwise, return filtered list (will show only selected regions)
                        return new_values if len(new_values) > 0 else []
                    else:
                        # Add if not selected - this will trigger treemap update to show region blocks
                        new_values = current_values + [toggled_region] if current_values else [toggled_region]
                        return new_values
            except:
                pass
        
        return current_values
    
    # Callback to update region legend item visual states
    @dash_app.callback(
        Output({'type': 'region-legend-item', 'index': MATCH}, 'style'),
        [Input('projects-status-region-filter', 'value'),
        Input('current-submenu', 'data'),
        Input('region-legend-items-store', 'children')],
        State({'type': 'region-legend-item', 'index': MATCH}, 'id'),
        prevent_initial_call=False
    )
    def update_region_legend_styles(selected_regions, current_submenu, all_regions, item_id):
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
    
        region_name = item_id.get('index') if item_id else None
        
        # FIXED: Determine if this region should be shown as selected
        # On initial load (selected_regions is None or empty), ALL regions should be active
        # No user interaction should be required for regions to become active on initial load
        
        # CRITICAL FIX: On initial load, ALL regions including Africa must be active
        # Check if we're on initial load (selected_regions is None or empty list)
        is_initial_load = (selected_regions is None or 
                        (isinstance(selected_regions, list) and len(selected_regions) == 0))
        
        # CRITICAL: Check if selected_regions is missing Africa but all_regions has it
        # This handles the case where selected_regions is missing Africa even though all_regions includes it
        missing_africa = False
        if (selected_regions and all_regions and 
            isinstance(selected_regions, list) and isinstance(all_regions, list) and
            'Africa' in all_regions and 'Africa' not in selected_regions):
            missing_africa = True
        
        # Also check if selected_regions equals all_regions (all regions selected)
        all_selected = False
        if (selected_regions and all_regions and 
            isinstance(selected_regions, list) and isinstance(all_regions, list) and
            len(selected_regions) == len(all_regions) and
            set(selected_regions) == set(all_regions)):
            all_selected = True
        
        # On initial load OR when all regions are selected OR when Africa is missing, 
        # ALL regions should be active (opacity: 1.0)
        # This ensures Africa (first item) and all regions appear active without user clicking
        if is_initial_load or all_selected or missing_africa:
            # CRITICAL: On initial load, ALL regions including Africa should be active
            # Use all_regions if available, otherwise default to True for all regions
            if all_regions and isinstance(all_regions, list) and len(all_regions) > 0:
                # Check if this region (including Africa) is in all_regions
                is_selected = region_name in all_regions if region_name else True
            else:
                # If all_regions not available yet, default to True for all regions
                # This ensures Africa and all regions appear active on initial load
                is_selected = True
        else:
            # After user interaction: use the actual filter values
            if selected_regions and isinstance(selected_regions, list) and len(selected_regions) > 0:
                # Check if this specific region is in the selected list
                # CRITICAL: If Africa is missing from selected_regions but exists in all_regions,
                # treat it as selected (fallback to all_regions)
                if region_name == 'Africa' and all_regions and isinstance(all_regions, list) and 'Africa' in all_regions and 'Africa' not in selected_regions:
                    is_selected = True  # Force Africa to be selected if it's in all_regions
                else:
                    is_selected = region_name in selected_regions if region_name else False
            else:
                # If selected_regions becomes empty after initial load, show all as selected
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
         Input('current-submenu', 'data')],
        prevent_initial_call=False
    )
    def update_treemap(region_filter, likely_filter, current_submenu):
        """Update treemap based on filters - only loads data when page is active"""
        print(region_filter,"region_filter004")
        # Only load data if this page is currently active
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
        
        df = load_treemap_data()
        table_df = load_table_data()
        # Get unique projects (remove duplicate rows for same project)
        if not table_df.empty and "Project Name" in table_df.columns:
            # Keep only first occurrence of each project
            table_df_unique = table_df.drop_duplicates(subset=["Project Name"], keep='first')
        else:
            table_df_unique = table_df
        
        # IMPORTANT: Handle region filtering based on user selection
        # After page load, when user deselects a region, it should be immediately removed from treemap
        if isinstance(region_filter, list):
            if len(region_filter) == 0:
                # Empty list: On initial load, show all regions (no filtering)
                # After user interaction, if all regions are deselected, also show all (or could show empty)
                # For now, treat empty as "show all" to match initial load behavior
                region_filter = None
            # If region_filter has values (some regions selected), filter to ONLY those regions
            # This ensures disabled/unselected regions are immediately removed from treemap blocks
            # The filtering happens in create_treemap_figure function
        
        # IMPORTANT: On initial load, if likely_filter is None or empty, show all data (no filtering)
        # Don't apply any likely filter on initial load
        if likely_filter is None or (isinstance(likely_filter, list) and len(likely_filter) == 0):
            likely_filter = None
        # Create treemap with region filter - unselected regions will be removed immediately
        fig = create_treemap_figure(df=df, region_filter=region_filter, likely_filter=likely_filter, table_df=table_df_unique)
        return fig

    # Callback to update KPI title dynamically
    @dash_app.callback(
        Output('projects-status-kpi-title', 'children'),
        Input('current-submenu', 'data'),
        prevent_initial_call=False
    )
    def update_kpi_title(current_submenu):
        """Update KPI table title with dynamic year/quarter range"""
        if current_submenu != 'projects-status':
            return ""
        
        year_range = get_year_quarter_range()
        title_text = f"Worldwide Oil Capacity Additions {year_range['min_year_quarter'].replace(' ', '-')} - {year_range['max_year_quarter'].replace(' ', '-')} ('000 b/d)"
        return title_text

    @dash_app.callback(
        [Output('projects-status-kpi-table-container', 'children'),
         Output('projects-status-table-container', 'children'),
         Output('last-clicked-status-store', 'data')],
        [Input('projects-status-region-filter', 'value'),
         Input('projects-status-likely-filter', 'value'),
         Input('projects-status-treemap', 'clickData'),
         Input('current-submenu', 'data')],
        [State('last-clicked-status-store', 'data')],
        prevent_initial_call=False
    )
    def update_tables(region_filter, likely_filter, click_data, current_submenu, last_clicked_status):
        """Update KPI table and project details table - only loads data when page is active"""
        # Only load data if this page is currently active
        if current_submenu != 'projects-status':
            # Return empty containers if page is not active
            empty_kpi = html.Div("", style={'display': 'none'})
            empty_table = html.Div("", style={'display': 'none'})
            return empty_kpi, empty_table
        
        # Load data
        kpi_df = load_kpi_data()
        treemap_df = load_treemap_data()
        table_df = load_table_data()
        
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
        # CRITICAL: On initial load, if likely_filter is None or empty, show all data (no filtering)
        filter_values = None
        if likely_filter and (isinstance(likely_filter, list) and len(likely_filter) > 0):
            # Handle checklist - filter out 'ALL' if present with other values
            filter_values = likely_filter
            if isinstance(likely_filter, list):
                # Remove 'ALL' if other values are selected
                if 'ALL' in likely_filter and len(likely_filter) > 1:
                    filter_values = [v for v in likely_filter if v != 'ALL']
                # If only 'ALL' is selected or empty list, show all (no filtering)
                elif not likely_filter or (len(likely_filter) == 1 and likely_filter[0] == 'ALL'):
                    filter_values = None
        
        if filter_values and "Likely Go-ahead" in table_df.columns:
                # Get projects matching any of the selected filter values
                # Handle empty string for blank values
                mask = table_df["Likely Go-ahead"].isin(filter_values)
                if '' in filter_values:
                    mask = mask | table_df["Likely Go-ahead"].isna() | (table_df["Likely Go-ahead"].astype(str).str.strip() == '')
                matching_projects = table_df[mask]
                
                if not matching_projects.empty:
                    # Create matching combinations
                    matching_combos = set()
                    for _, row in matching_projects.iterrows():
                        combo = (
                            row.get("Region", ""),
                            row.get("Play Type", ""),
                            row.get("Project Status", "")
                        )
                        matching_combos.add(combo)
                    
                    # Filter treemap data
                    def matches_combo(row):
                        combo = (
                            str(row.get("Region", "")),
                            str(row.get("Play Type", "")),
                            str(row.get("Project Status", ""))
                        )
                        return combo in matching_combos
                    
                    filtered_treemap = filtered_treemap[filtered_treemap.apply(matches_combo, axis=1)]
        
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
        
        # Apply region filter to table
        if region_filter:
            if isinstance(region_filter, list):
                if len(region_filter) > 0 and "Region" in filtered_table.columns:
                    filtered_table = filtered_table[filtered_table["Region"].isin(region_filter)]
            elif region_filter != "(All)":
                if "Region" in filtered_table.columns:
                    filtered_table = filtered_table[filtered_table["Region"] == region_filter]
        
        # Apply likely filter to table
        # CRITICAL: On initial load, if likely_filter is None or empty, show all data (no filtering)
        filter_values = None
        if likely_filter and (isinstance(likely_filter, list) and len(likely_filter) > 0):
            # Handle checklist - filter out 'ALL' if present with other values
            filter_values = likely_filter
            if isinstance(likely_filter, list):
                # Remove 'ALL' if other values are selected
                if 'ALL' in likely_filter and len(likely_filter) > 1:
                    filter_values = [v for v in likely_filter if v != 'ALL']
                # If only 'ALL' is selected or empty list, show all (no filtering)
                elif not likely_filter or (len(likely_filter) == 1 and likely_filter[0] == 'ALL'):
                    filter_values = None
        
        if filter_values and "Likely Go-ahead" in filtered_table.columns:
                # Filter by any of the selected values, handling empty strings for blank
                mask = filtered_table["Likely Go-ahead"].isin(filter_values)
                # Also include rows where Likely Go-ahead is NaN or empty string if '' is in filter
                if '' in filter_values:
                    mask = mask | filtered_table["Likely Go-ahead"].isna() | (filtered_table["Likely Go-ahead"].astype(str).str.strip() == '')
                filtered_table = filtered_table[mask]
        
        # Check if a Project Status block was clicked
        clicked_project_status = None
        clicked_production_additions = None
        
        # Apply treemap click filter if available
        # New structure: Region (top level) -> Project Status + Play Type (combined, second level)
        if click_data and 'points' in click_data and len(click_data['points']) > 0:
            point = click_data['points'][0]
            
            clicked_label = None
            clicked_region = None
            clicked_value = None
            
            if 'label' in point:
                clicked_label = point['label']
            elif 'customdata' in point:
                clicked_label = point['customdata']
            
            # Get the parent (Region) from the click point
            if 'parent' in point:
                clicked_region = point['parent']
            
            # Get the exact value from the clicked block
            if 'value' in point:
                try:
                    clicked_value = float(point['value'])
                except (ValueError, TypeError):
                    clicked_value = None
            
            if clicked_label:
                # Check if clicked label is a region (top level)
                if "Region" in filtered_table.columns:
                    if clicked_label in filtered_table["Region"].values:
                        filtered_table = filtered_table[filtered_table["Region"] == clicked_label]
                
                # Check if clicked label is a combined "Project Status - Play Type" (second level)
                if " - " in clicked_label:
                    parts = clicked_label.split(" - ", 1)
                    if len(parts) == 2:
                        project_status = parts[0].strip()
                        play_type = parts[1].strip()
                        
                        # Check if this is a Project Status (not a region)
                        # Project Status values: Under Development, Onstream, Appraisal
                        if project_status in ["Under Development", "Onstream", "Appraisal"]:
                            clicked_project_status = project_status
                            
                            # Get the exact Production Additions value for this specific block
                            # Priority: 1) Use value from click point, 2) Filter by Region + Project Status + Play Type
                            if clicked_value is not None:
                                # Use the exact value from the clicked block
                                clicked_production_additions = clicked_value
                            elif clicked_region:
                                # Filter by Region + Project Status + Play Type to get exact value
                                exact_df = filtered_treemap[
                                    (filtered_treemap["Region"] == clicked_region) &
                                    (filtered_treemap["Project Status"] == project_status) &
                                    (filtered_treemap["Play Type"] == play_type)
                                ]
                                if not exact_df.empty:
                                    clicked_production_additions = float(exact_df["Production Additions"].sum())
                                else:
                                    clicked_production_additions = 0.0
                            else:
                                # Fallback: filter by Project Status + Play Type (without region)
                                status_play_df = filtered_treemap[
                                    (filtered_treemap["Project Status"] == project_status) &
                                    (filtered_treemap["Play Type"] == play_type)
                                ]
                                if not status_play_df.empty:
                                    clicked_production_additions = float(status_play_df["Production Additions"].sum())
                                else:
                                    clicked_production_additions = 0.0
                            
                        
                        # Filter table by both Project Status and Play Type
                        if "Project Status" in filtered_table.columns:
                            filtered_table = filtered_table[filtered_table["Project Status"] == project_status]
                        if "Play Type" in filtered_table.columns:
                            filtered_table = filtered_table[filtered_table["Play Type"] == play_type]
        
        # Create KPI table - show clicked status if available, otherwise show all
        # When a Project Status block is clicked, replace the Worldwide Oil Capacity Additions table
        # The title "Worldwide Oil Capacity Additions" remains unchanged
        # Toggle functionality: clicking the same status again reverts to default table
        new_clicked_status = None
        
        if clicked_project_status is not None and clicked_production_additions is not None:
            # Check if the same status was clicked again (toggle functionality)
            if last_clicked_status == clicked_project_status:
                # Same status clicked again - revert to default table
                kpi_table = create_kpi_table(filtered_kpi)
                new_clicked_status = None  # Reset to None to show default table
            else:
                # Different status clicked - show clicked status table
                try:
                    kpi_table = create_kpi_table_for_clicked_status(clicked_project_status, clicked_production_additions)
                    new_clicked_status = clicked_project_status  # Store the clicked status
                except Exception as e:
                    # Fallback to normal table if there's an error
                    print(f"Error creating clicked status table: {e}")
                    import traceback
                    traceback.print_exc()
                    kpi_table = create_kpi_table(filtered_kpi)
                    new_clicked_status = None
        else:
            # No Project Status block clicked - show default table
            # Create normal KPI table with all statuses (Worldwide Oil Capacity Additions)
            kpi_table = create_kpi_table(filtered_kpi)
            new_clicked_status = None  # Reset when no click or filter changes
        
        # Create project details table
        details_table = create_project_details_table(filtered_table)
        
        return kpi_table, details_table, new_clicked_status


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
                'if': {'filter_query': '{Project Status} = "Grand Total"'},
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
    grand_total = 0.0
    for _, row in df.iterrows():
        if "Project Status" in row and "Production Additions" in row:
            value = row['Production Additions']
            if isinstance(value, (int, float)):
                grand_total += float(value)
            table_data.append({
                "Project Status": row["Project Status"],
                "Production Additions": f"{value:,.1f}" if isinstance(value, (int, float)) else str(value)
            })
    
    # Add Grand Total row
    if grand_total > 0:
        table_data.append({
            "Project Status": "Grand Total",
            "Production Additions": f"{grand_total:,.1f}"
        })
    
    if not table_data:
        return html.Div("No KPI data available.", style={'color': '#666666', 'padding': '20px'})
    
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
                'if': {'filter_query': '{Project Status} = "Grand Total"'},
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
    
    # Prepare table data with ALL rows (no limit)
    table_data = df[all_columns].to_dict('records')
    
    # Create columns configuration
    columns = [{"name": col, "id": col} for col in all_columns]
    
    table = dash_table.DataTable(
        id='projects-status-details-table',
        columns=columns,
        data=table_data,
        style_table={
            'overflowX': 'auto',
            'overflowY': 'auto',
            'maxHeight': '600px',
            'border': '1px solid #dee2e6',
            'backgroundColor': 'white',
            'width': '100%'
        },
        style_cell={
            'textAlign': 'left',
            'padding': '8px',
            'fontSize': '11px',
            'fontFamily': 'Arial, sans-serif',
            'border': '1px solid #dee2e6',
            'color': '#2c3e50',
            'whiteSpace': 'normal',
            'height': 'auto',
            'minWidth': '100px',
            'maxWidth': '300px'
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': 'bold',
            'border': '1px solid #dee2e6',
            'textAlign': 'center',
            'fontSize': '11px',
            'fontFamily': 'Arial, sans-serif',
            'color': '#2c3e50',
            'whiteSpace': 'normal'
        },
        style_data={
            'border': '1px solid #dee2e6',
            'backgroundColor': 'white'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa'
            }
        ],
        page_action='none',  # No pagination - show all rows
        sort_action='native',
        filter_action='native'
    )
    
    return table
