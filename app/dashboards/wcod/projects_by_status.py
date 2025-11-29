"""
Projects by Status View
Total Capacity Additions from 2025 Q1 to 2029 Q4
"""
from dash import dcc, html, Input, Output, State, callback, ALL, MATCH
import dash
import dash_table
import plotly.graph_objects as go
import pandas as pd
import os
import re
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
        # Handle checklist - filter out 'ALL' if present with other values
        if isinstance(likely_filter, list):
            # Remove 'ALL' if other values are selected
            if 'ALL' in likely_filter and len(likely_filter) > 1:
                likely_filter = [v for v in likely_filter if v != 'ALL']
            # If only 'ALL' is selected or empty list, show all (no filtering)
            if not likely_filter or (len(likely_filter) == 1 and likely_filter[0] == 'ALL'):
                likely_filter = None
        
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
    
    # Create hierarchical structure: Region -> (Project Status + Play Type)
    labels = []
    parents = []
    values = []
    hover_texts = []
    text_entries = []
    colors = []
    
    # Group by Region in the specified order
    for region in ordered_regions:
        region_df = grouped[grouped["Region"] == region]
        if region_df.empty:
            continue
        
        region_total = region_df["Production Additions"].sum()
        region_name = str(region).strip()
        region_color = REGION_COLORS.get(region_name, "#666666")
        
        # Add region as top-level node
        labels.append(region_name)
        parents.append("")
        values.append(region_total)
        hover_texts.append(
            f"<span style='color:#333333;'>Region:</span> <span style='color:#000000;'><b>{region_name}</b></span><br>"
            f"<span style='color:#333333;'>Production Additions:</span> <span style='color:#000000;'><b>{region_total:,.1f} ('000 b/d)</b></span>"
        )
        text_entries.append(f"<b>{region_name}</b>")
        colors.append(region_color)
        
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
                f"<b>Project Status ({project_status})</b><br>"
                f"<b>Play Type ({play_type})</b><br>"
                f"<b>Region ({region_name})</b>"
            )
            # Use region color for children
            colors.append(region_color)
    
    fig = go.Figure()
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
            root=dict(color="rgba(255,255,255,0)")
        )
    )
    
    fig.update_layout(
        title=dict(
            text="Total Capacity Additions (2025 Q1 - 2029 Q4) by Region",
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
    # Load data to get available regions
    treemap_df = load_treemap_data()
    regions = ['(All)']
    
    if not treemap_df.empty and "Region" in treemap_df.columns:
        unique_regions = treemap_df['Region'].dropna().unique().tolist()
        # Order regions according to REGION_ORDER
        ordered_regions = [r for r in REGION_ORDER if r in unique_regions]
        # Add any regions not in REGION_ORDER at the end
        remaining_regions = [r for r in unique_regions if r not in REGION_ORDER]
        ordered_regions.extend(sorted(remaining_regions))
        regions.extend(ordered_regions)
    
    return html.Div([
        html.Div([
            # Main visualization area (75% width)
            html.Div([
                dcc.Graph(
                    id='projects-status-treemap',
                    style={'height': '700px'},
                    config={'displayModeBar': False}
                ),
                # Project Details Table below treemap
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
                        style={'marginTop': '10px'}
                    )
                ])
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
                    html.Div([
                        # Create clickable legend items for each region
                        *[
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
                            for region in regions if region != '(All)'
                        ]
                    ])
                ], style={'marginBottom': '25px', 'padding': '15px', 'border': '1px solid #e0e0e0', 'borderRadius': '5px', 'backgroundColor': '#fafafa'}),
                
                # Hidden region filter checklist
                dcc.Checklist(
                    id='projects-status-region-filter',
                    options=[{'label': r, 'value': r} for r in regions if r != '(All)'],
                    value=[r for r in regions if r != '(All)'],  # All regions selected by default
                    style={'display': 'none'}
                ),
                
                # Store region legend item IDs for callback
                html.Div(id='region-legend-items-store', style={'display': 'none'}, 
                        children=[r for r in regions if r != '(All)']),
                
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
                            {'label': 'ALL', 'value': 'ALL'},
                            {'label': 'blank', 'value': ''},
                            {'label': 'N', 'value': 'N'},
                            {'label': 'Uncertain', 'value': 'Uncertain'},
                            {'label': 'Yes', 'value': 'Yes'}
                        ],
                        value=['Yes'],  # Default to 'Yes' only
                        style={
                            'fontSize': '12px',
                            'fontFamily': 'Arial, sans-serif'
                        },
                        inputStyle={'marginRight': '8px', 'marginLeft': '0px'},
                        labelStyle={'display': 'block', 'marginBottom': '6px', 'cursor': 'pointer'}
                    )
                ], style={'marginBottom': '25px', 'padding': '15px', 'border': '1px solid #e0e0e0', 'borderRadius': '5px', 'backgroundColor': '#fafafa'})
            ], style={'width': '25%', 'float': 'right', 'paddingLeft': '20px'}),
            
            html.Div(style={'clear': 'both'})
        ], style={'padding': '20px'})
    ], className='tab-content', style={'backgroundColor': '#f5f7fa', 'padding': '20px', 'minHeight': '100vh'})


def register_callbacks(dash_app, server):
    """Register all callbacks for Projects by Status"""
    
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
                        # Remove if already selected
                        new_values = [v for v in current_values if v != toggled_region]
                    else:
                        # Add if not selected
                        new_values = current_values + [toggled_region] if current_values else [toggled_region]
                    return new_values
            except:
                pass
        
        return current_values
    
    # Callback to update region legend item visual states
    @dash_app.callback(
        Output({'type': 'region-legend-item', 'index': MATCH}, 'style'),
        Input('projects-status-region-filter', 'value'),
        State({'type': 'region-legend-item', 'index': MATCH}, 'id'),
        prevent_initial_call=False
    )
    def update_region_legend_styles(selected_regions, item_id):
        """Update legend item styles to show which are selected"""
        if selected_regions is None:
            selected_regions = []
        
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
        if region_name and region_name in selected_regions:
            style = {**base_style, 'opacity': '1.0'}
        else:
            style = {**base_style, 'opacity': '0.3'}
        
        return [style]
    
    @dash_app.callback(
        Output('projects-status-treemap', 'figure'),
        [Input('projects-status-region-filter', 'value'),
         Input('projects-status-likely-filter', 'value')],
        prevent_initial_call=False
    )
    def update_treemap(region_filter, likely_filter):
        """Update treemap based on filters"""
        df = load_treemap_data()
        table_df = load_table_data()
        # Get unique projects (remove duplicate rows for same project)
        if not table_df.empty and "Project Name" in table_df.columns:
            # Keep only first occurrence of each project
            table_df_unique = table_df.drop_duplicates(subset=["Project Name"], keep='first')
        else:
            table_df_unique = table_df
        fig = create_treemap_figure(df=df, region_filter=region_filter, likely_filter=likely_filter, table_df=table_df_unique)
        return fig
    
    @dash_app.callback(
        [Output('projects-status-kpi-table-container', 'children'),
         Output('projects-status-table-container', 'children')],
        [Input('projects-status-region-filter', 'value'),
         Input('projects-status-likely-filter', 'value'),
         Input('projects-status-treemap', 'clickData')],
        prevent_initial_call=False
    )
    def update_tables(region_filter, likely_filter, click_data):
        """Update KPI table and project details table"""
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
        if likely_filter:
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
        if likely_filter:
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
        
        # Apply treemap click filter if available
        # New structure: Region (top level) -> Project Status + Play Type (combined, second level)
        if click_data and 'points' in click_data and len(click_data['points']) > 0:
            point = click_data['points'][0]
            if 'label' in point:
                clicked_label = point['label']
                
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
                        
                        # Filter by both Project Status and Play Type
                        if "Project Status" in filtered_table.columns:
                            filtered_table = filtered_table[filtered_table["Project Status"] == project_status]
                        if "Play Type" in filtered_table.columns:
                            filtered_table = filtered_table[filtered_table["Play Type"] == play_type]
        
        # Create KPI table
        kpi_table = create_kpi_table(filtered_kpi)
        
        # Create project details table
        details_table = create_project_details_table(filtered_table)
        
        return kpi_table, details_table


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
        page_action='native',
        page_size=50,  # Increased page size
        sort_action='native',
        filter_action='native',
        export_format='csv',  # Allow export
        export_headers='display'
    )
    
    return table
