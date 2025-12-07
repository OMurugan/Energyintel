"""
Projects by Time View
Upstream projects over time - Tableau-style design
"""
import os
import re
from pathlib import Path
from dash import dcc, html, Input, Output, State, callback, dash_table
import plotly.graph_objects as go
import pandas as pd
from core.data_helpers import execute_query
# from app.models import UpstreamProject


# Data file paths
BASE_DIR = Path(__file__).parent.parent / 'data' / 'upstream_projects'
CHART_CSV = BASE_DIR / 'Projects by Time_Chart.csv'
TABLE_CSV = BASE_DIR / 'Projects by Time_Table.csv'
TABLE_CSV_FALLBACK = BASE_DIR / '_Projects by Time_Table.csv'

# Region colors - exact RGB values from image
REGION_COLORS = {
    'Africa': 'rgb(0, 117, 168)',        # #0075A8
    'Asia': 'rgb(89, 89, 89)',           # #595959
    'Europe': 'rgb(49, 59, 73)',         # #313B49
    'FSU': 'rgb(121, 134, 203)',         # #7986CB
    'Latin America': 'rgb(166, 166, 166)',  # #A6A6A6
    'Middle East': 'rgb(191, 82, 39)',   # #BF5227
    'North America': 'rgb(195, 210, 151)'  # #C3D297
}

# Regions in the order they should appear in the stacked chart (bottom to top)
REGIONS = ['Africa', 'Asia', 'Europe', 'FSU', 'Latin America', 'Middle East', 'North America']


def load_chart_data():
    """Load chart data from CSV"""
    try:
        # Try different encodings
        encodings = ['utf-16', 'utf-8', 'latin-1']
        df = None
        for encoding in encodings:
            try:
                # Read CSV with tab separator, skip first 3 rows (copyright info)
                # Row 4 (index 3) has the header: Region, then Q1, Q2, Q3, Q4 for each year
                df = pd.read_csv(CHART_CSV, sep='\t', skiprows=3, header=0, encoding=encoding)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        if df is None:
            return pd.DataFrame()
        
        # The data structure: Region, Type, then quarter columns
        # Filter only "Production Additions" rows
        df = df[df.iloc[:, 1] == 'Production Additions'].copy()
        
        # Get region names from first column
        df['Region'] = df.iloc[:, 0]
        
        # Extract quarter columns (Q1 2025 to Q4 2029)
        # The header row has: Region, (empty), Q1, Q2, Q3, Q4, Q1, Q2, Q3, Q4, ...
        quarters = []
        for year in range(2025, 2030):
            for q in ['Q1', 'Q2', 'Q3', 'Q4']:
                quarters.append(f'{q}\n{year}')
        
        # Get data columns (starting from column index 2, skipping Region and empty column)
        data_dict = {}
        for idx, row in df.iterrows():
            region = row['Region']
            values = []
            # Start from column index 2 (skip Region and empty column)
            for i in range(20):  # 20 quarters total (5 years * 4 quarters)
                col_idx = i + 2
                if col_idx < len(row):
                    val = pd.to_numeric(row.iloc[col_idx], errors='coerce')
                    values.append(val if pd.notna(val) else 0)
                else:
                    values.append(0)
            data_dict[region] = values
        
        # Create DataFrame for easier handling
        chart_data = []
        for region, values in data_dict.items():
            for i, val in enumerate(values):
                chart_data.append({
                    'Region': region,
                    'Quarter': quarters[i],
                    'Year': 2025 + i // 4,
                    'QuarterNum': (i % 4) + 1,
                    'Value': val
                })
        
        return pd.DataFrame(chart_data)
    except Exception as e:
        print(f"Error loading chart data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def load_table_data():
    """Load table data from database query"""
    try:
        from core.data_helpers import execute_query
        
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
        
        print(f"DEBUG: Executing projects table database query...")
        results = execute_query(query)
        
        if not results:
            print("ERROR: Query returned no results")
            return pd.DataFrame()
        
        print(f"DEBUG: Query returned {len(results)} results")
        
        # Convert query results to DataFrame
        df = pd.DataFrame(results)
        
        print(f"DEBUG: Raw columns from query: {list(df.columns)}")
        
        # Normalize column names - convert to proper case for matching
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
            'play_type': 'play_type',
            'Play Type': 'play_type',
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
        
        # Rename columns based on mapping
        df = df.rename(columns=column_mapping)
        
        print(f"DEBUG: Normalized columns: {list(df.columns)}")
        print(f"DEBUG: Total rows loaded: {len(df)}")
        
        # Clean data
        df = df.fillna('')
        
        print(f"Table data loaded successfully. Rows: {len(df)}, Columns: {len(df.columns)}")
        
        return df
    except Exception as e:
        print(f"ERROR loading table data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def create_layout():
    """Create the Projects by Time layout matching Tableau design"""
    # Build region legend items
    region_legend_items = [
        html.Div([
            html.Div(style={
                'width': '16px',
                'height': '16px',
                'backgroundColor': REGION_COLORS[region],
                'border': '1px solid #ccc',
                'display': 'inline-block',
                'marginRight': '8px',
                'verticalAlign': 'middle'
            }),
            html.Span(region, style={
                'fontSize': '12px',
                'verticalAlign': 'middle',
                'color': 'rgb(27, 54, 93)',
                'fontFamily': 'Lato, sans-serif'
            })
        ], style={
            'display': 'flex',
            'alignItems': 'center',
            'marginBottom': '6px'
        })
        for region in REGIONS
    ]
    
    return html.Div([
        html.Div([
            # Left side - Chart
            html.Div([
                dcc.Graph(
                    id='projects-time-chart',
                    config={'displayModeBar': False}
                )
            ], style={'width': '75%', 'display': 'inline-block', 'verticalAlign': 'top'}),
            
            # Right side - Color Legend and Filters
            html.Div([
                html.Div([
                    html.H4("Region", style={'marginBottom': '10px', 'fontSize': '14px', 'fontWeight': 'bold', 'fontFamily': 'Lato, sans-serif','color': 'rgb(27, 54, 93)'}),
                    html.Div(region_legend_items)
                ], style={'marginBottom': '30px'}),
                
                html.Div([
                    html.H4("Likely To Go Ahead", style={'marginBottom': '10px', 'fontSize': '14px', 'fontWeight': 'bold', 'fontFamily': 'Lato, sans-serif','color': 'rgb(27, 54, 93)'  }),
                    dcc.Checklist(
                        id='likely-filter',
                        options=[
                            {'label': '(All)', 'value': 'All'},
                            {'label': 'N', 'value': 'N'},
                            {'label': 'Uncertain', 'value': 'Uncertain'},
                            {'label': 'Y', 'value': 'Y'}
                        ],
                        value=['Y'],
                        style={'fontSize': '12px', 'fontFamily': 'Lato, sans-serif'},
                        inputStyle={'marginRight': '5px', 'marginLeft': '5px'},
                        labelStyle={'color': 'rgb(27, 54, 93)', 'fontFamily': 'Lato, sans-serif'}
                    ),
                    dcc.Store(id='likely-filter-previous', data=['Y'])
                ])
            ], style={
                'width': '25%',
                'display': 'inline-block',
                'verticalAlign': 'top',
                'paddingLeft': '20px',
                'paddingTop': '60px'
            })
        ], style={'display': 'flex', 'marginBottom': '20px'}),
        
        # Instruction text
        html.Div([
            html.P(
                "Select a Region from the chart above to filter the below table",
                style={
                    'fontSize': '14px',
                    'fontWeight': '500',
                    'marginBottom': '15px',
                    'marginTop': '20px',
                    'fontFamily': 'Lato, sans-serif'
                }
            )
        ]),
        
        # Table
        html.Div([
            html.H4("Project Details", style={'marginBottom': '15px', 'fontSize': '16px', 'fontWeight': 'bold', 'fontFamily': 'Lato, sans-serif', 'color': '#fe5000', 'textAlign': 'left'}),
            dash_table.DataTable(
                id='projects-time-table',
                style_table={
                    'overflowX': 'auto',
                    'overflowY': 'auto',
                    'maxHeight': '600px',
                    'border': '1px solid #ddd'
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
                tooltip_duration=None,
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
        ], style={'marginTop': '20px'})
    ], className='tab-content', style={'padding': '20px', 'backgroundColor': '#ffffff'})


def register_callbacks(dash_app, server):
    """Register all callbacks for Projects by Time"""
    
    @callback(
        [Output('likely-filter', 'value'),
         Output('likely-filter-previous', 'data')],
        Input('likely-filter', 'value'),
        State('likely-filter-previous', 'data'),
        prevent_initial_call=False
    )
    def manage_all_checkbox(selected_values, previous_values):
        """Manage (All) checkbox behavior: selecting All selects all, unchecking All unchecks all"""
        if selected_values is None:
            return [], []
        
        # Ensure it's a list
        if not isinstance(selected_values, list):
            selected_values = [selected_values] if selected_values else []
        
        all_options = ['All', 'N', 'Uncertain', 'Y']
        individual_options = ['N', 'Uncertain', 'Y']
        
        # Get previous state for comparison
        if previous_values is None:
            previous_values = []
        if not isinstance(previous_values, list):
            previous_values = [previous_values] if previous_values else []
        
        # Determine what changed
        was_all_selected = 'All' in previous_values
        is_all_selected = 'All' in selected_values
        
        # Get individual options in previous and current state
        prev_individual = [opt for opt in previous_values if opt in individual_options]
        curr_individual = [opt for opt in selected_values if opt in individual_options]
        
        # If "All" was just selected (wasn't before, is now)
        if not was_all_selected and is_all_selected:
            # Select all options
            return all_options, all_options
        
        # If "All" was just deselected (was before, isn't now)
        if was_all_selected and not is_all_selected:
            # Deselect all options
            return [], []
        
        # If "All" was selected before and still is, but individual options changed
        # (user clicked an individual option while "All" was selected)
        if was_all_selected and is_all_selected and prev_individual != curr_individual:
            # If an individual option was deselected, deselect "All" and keep remaining individual options
            if len(curr_individual) < len(prev_individual):
                return curr_individual, curr_individual
            # If an individual option was selected and now all are selected, keep all
            elif len(curr_individual) == len(individual_options):
                return all_options, all_options
        
        # If "All" is currently selected and no change detected, keep all selected
        if is_all_selected:
            return all_options, all_options
        
        # Otherwise, check individual options
        selected_individual = [opt for opt in selected_values if opt in individual_options]
        
        # If all individual options are selected, also select "All"
        if len(selected_individual) == len(individual_options):
            return all_options, all_options
        
        # Return only the selected individual options
        return selected_individual, selected_individual
    
    @callback(
        Output('projects-time-chart', 'figure'),
        [Input('current-submenu', 'data'),
         Input('likely-filter', 'value')]
    )
    def update_chart(submenu, likely_filter):
        """Update projects by time chart"""
        if submenu != 'projects-time':
            return go.Figure()
        
        # Load table data to filter by "Likely To Go Ahead"
        table_df = load_table_data()
        
        # Filter table data by "Likely To Go Ahead" if filter is provided
        if not table_df.empty:
            # Try to find the column with case-insensitive matching
            likely_col = None
            for col in table_df.columns:
                col_lower = col.lower()
                if 'likely' in col_lower and ('go' in col_lower or 'ahead' in col_lower):
                    likely_col = col
                    break
            
            if likely_col:
                # Handle None or empty list
                if not likely_filter:
                    likely_filter = []
                if not isinstance(likely_filter, list):
                    likely_filter = [likely_filter] if likely_filter else []
                
                # If "All" is selected, don't filter (show all data)
                if 'All' in likely_filter:
                    # Show all data - no filtering needed
                    pass
                elif len(likely_filter) > 0:
                    # Map filter values to CSV values
                    value_mapping = {
                        'Y': ['Yes', 'Y'],
                        'N': ['No', 'N'],
                        'Uncertain': ['Uncertain']
                    }
                    
                    # Build list of values to match
                    filter_values = []
                    for v in likely_filter:
                        if v in value_mapping:
                            filter_values.extend(value_mapping[v])
                        else:
                            filter_values.append(str(v))
                    
                    # Filter by selected values
                    table_df[likely_col] = table_df[likely_col].astype(str).str.strip()
                    table_df = table_df[table_df[likely_col].isin(filter_values)].copy()
                else:
                    # No checkboxes selected - show no data
                    table_df = pd.DataFrame()
        
        # If no checkboxes are selected, return empty chart
        # Check if likely_filter is empty (no selections)
        if not likely_filter or (isinstance(likely_filter, list) and len(likely_filter) == 0):
            fig = go.Figure()
            fig.add_annotation(
                text="No data selected. Please select at least one option from 'Likely To Go Ahead' filter.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font={'size': 14, 'family': 'Lato', 'color': 'rgb(27, 54, 93)'}
            )
            fig.update_layout(
                height=500,
                plot_bgcolor='white',
                paper_bgcolor='white',
                title={
                    'text': "Projected Oil Capacity additions by Quarter ('000 b/d)",
                    'x': 0,
                    'xanchor': 'left',
                    'font': {'size': 16, 'family': 'Lato', 'color': '#fe5000'}
                }
            )
            return fig
        
        # If table_df is empty (no columns), return empty chart
        if table_df.empty or len(table_df.columns) == 0:
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for selected filters.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font={'size': 14, 'family': 'Lato', 'color': 'rgb(27, 54, 93)'}
            )
            fig.update_layout(
                height=500,
                plot_bgcolor='white',
                paper_bgcolor='white',
                title={
                    'text': "Projected Oil Capacity additions by Quarter ('000 b/d)",
                    'x': 0,
                    'xanchor': 'left',
                    'font': {'size': 16, 'family': 'Lato', 'color': '#fe5000'}
                }
            )
            return fig
        
        # Check if table has quarter columns (Q1 2025, Q2 2025, etc.)
        # First, check all columns for quarter patterns
        quarter_cols = []
        seen_cols = set()
        for col_name in table_df.columns:
            col_str = str(col_name).strip()
            # Try to match quarter patterns: Q1 2025, Q1\n2025, 2025 Q1, etc.
            matched = False
            for year in range(2025, 2030):
                for q in ['Q1', 'Q2', 'Q3', 'Q4']:
                    # Check various patterns
                    patterns = [
                        rf'^{q}\s+{year}$',
                        rf'^{q}\s*\n\s*{year}$',
                        rf'^{year}\s+{q}$',
                        rf'^{q}\s*{year}$',
                        rf'^{year}\s*{q}$',
                        rf'^{q}\.{year}$',
                        rf'^{year}\.{q}$'
                    ]
                    for pattern in patterns:
                        if re.match(pattern, col_str, re.IGNORECASE):
                            if col_name not in seen_cols:
                                quarter_cols.append((col_name, year, q))
                                seen_cols.add(col_name)
                                matched = True
                            break
                    if matched:
                        break
                if matched:
                    break
        
        # If table has quarter columns, aggregate from table data
        if quarter_cols and not table_df.empty and 'Region' in table_df.columns:
            # Aggregate capacity by region and quarter
            chart_data = []
            for region in REGIONS:
                region_data = table_df[table_df['Region'] == region] if 'Region' in table_df.columns else pd.DataFrame()
                if not region_data.empty:
                    for year in range(2025, 2030):
                        for q_num, q in enumerate(['Q1', 'Q2', 'Q3', 'Q4'], 1):
                            # Find matching quarter column
                            quarter_val = 0
                            for col_name, col_year, col_q in quarter_cols:
                                if col_year == year and col_q == q and col_name in region_data.columns:
                                    # Sum capacity for this quarter
                                    quarter_val = pd.to_numeric(region_data[col_name], errors='coerce').fillna(0).sum()
                                    break
                            
                            chart_data.append({
                                'Region': region,
                                'Quarter': f'{q}\n{year}',
                                'Year': year,
                                'QuarterNum': q_num,
                                'Value': quarter_val
                            })
                else:
                    # No data for this region, add zeros
                    for year in range(2025, 2030):
                        for q_num, q in enumerate(['Q1', 'Q2', 'Q3', 'Q4'], 1):
                            chart_data.append({
                                'Region': region,
                                'Quarter': f'{q}\n{year}',
                                'Year': year,
                                'QuarterNum': q_num,
                                'Value': 0
                            })
            
            df = pd.DataFrame(chart_data)
        elif not table_df.empty and 'Region' in table_df.columns:
            # Fallback: Check for capacity column and "First Oil Year"
            # Look for capacity-related columns
            capacity_col = None
            capacity_cols_to_check = [
                'Capacity', 'Oil Capacity', 'Production Capacity', 
                'Capacity (000 b/d)', 'Oil Capacity (000 b/d)',
                'Peak Capacity', 'Max Capacity'
            ]
            for col in table_df.columns:
                col_lower = str(col).lower()
                if any(check.lower() in col_lower for check in capacity_cols_to_check):
                    capacity_col = col
                    break
                # Also check if column name contains numbers that might be capacity
                if 'capacity' in col_lower or ('000' in col_lower and 'b/d' in col_lower):
                    capacity_col = col
                    break
            
            if capacity_col and 'First Oil Year' in table_df.columns:
                # Aggregate capacity by region and quarter using "First Oil Year"
                chart_data = []
                for region in REGIONS:
                    region_data = table_df[table_df['Region'] == region].copy()
                    if not region_data.empty:
                        for year in range(2025, 2030):
                            for q_num, q in enumerate(['Q1', 'Q2', 'Q3', 'Q4'], 1):
                                # Filter projects that start in this quarter
                                # Assume capacity is added in Q1 of "First Oil Year"
                                if q_num == 1:  # Q1 only
                                    year_data = region_data[
                                        pd.to_numeric(region_data['First Oil Year'], errors='coerce') == year
                                    ]
                                    quarter_val = pd.to_numeric(year_data[capacity_col], errors='coerce').fillna(0).sum()
                                else:
                                    quarter_val = 0
                                
                                chart_data.append({
                                    'Region': region,
                                    'Quarter': f'{q}\n{year}',
                                    'Year': year,
                                    'QuarterNum': q_num,
                                    'Value': quarter_val
                                })
                    else:
                        # No data for this region, add zeros
                        for year in range(2025, 2030):
                            for q_num, q in enumerate(['Q1', 'Q2', 'Q3', 'Q4'], 1):
                                chart_data.append({
                                    'Region': region,
                                    'Quarter': f'{q}\n{year}',
                                    'Year': year,
                                    'QuarterNum': q_num,
                                    'Value': 0
                                })
                
                df = pd.DataFrame(chart_data)
            else:
                # No quarter columns or capacity column found, use pre-aggregated chart data
                # Note: This won't be filtered by "Likely To Go Ahead"
                print("Warning: Table does not have quarter columns or capacity column. Using pre-aggregated chart data (not filtered by Likely To Go Ahead).")
                df = load_chart_data()
        else:
            # Use pre-aggregated chart data
            df = load_chart_data()
        
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No chart data available.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(
                height=500,
                plot_bgcolor='white',
                paper_bgcolor='white',
                title={
                    'text': "Projected Oil Capacity additions by Quarter ('000 b/d)",
                    'x': 0,
                    'xanchor': 'left',
                    'font': {'size': 16, 'family': 'Lato', 'color': '#fe5000'}
                }
            )
            return fig
        
        # Show all regions (no filtering)
        
        # Create quarters list for x-axis
        # Format: Show Q1, Q2, Q3, Q4 with year labels above
        quarters = []
        x_tick_labels = []
        for year in range(2025, 2030):
            for q in ['Q1', 'Q2', 'Q3', 'Q4']:
                quarters.append(f'{year}_{q}')
                x_tick_labels.append(q)
        
        # Create stacked bar chart
        fig = go.Figure()
        
        # Add a trace for each region in REVERSE order to match legend
        # In stacked bars, first added = bottom, last added = top
        # Legend shows: Africa (top), Asia, Europe, FSU, Latin America, Middle East, North America (bottom)
        # So we add: North America first (bottom), then Middle East, ..., then Africa last (top)
        for region in reversed(REGIONS):
            region_data = df[df['Region'] == region]
            if not region_data.empty:
                # Sort by year and quarter
                region_data = region_data.sort_values(['Year', 'QuarterNum'])
                values = region_data['Value'].tolist()
                
                # Pad values if needed
                while len(values) < 20:
                    values.append(0)
                
                fig.add_trace(go.Bar(
                    name=region,
                    x=quarters,
                    y=values,
                    marker=dict(
                        color=REGION_COLORS.get(region, 'rgb(128, 128, 128)'),
                        line=dict(width=0)  # No border for clean stacked appearance
                    ),
                    hovertemplate=(
                        '<span style="color:grey">Region:</span> <span style="color:black">%{fullData.name}</span><br>' +
                        '<span style="color:grey">Period:</span> <span style="color:black">%{customdata}</span><br>' +
                        '<span style="color:grey">Oil Capacity Additions(\'000 b/d):</span> <span style="color:black">%{y:,.0f}</span><extra></extra>'
                    ),
                    customdata=[f"{q.split('_')[1]} {q.split('_')[0]}" for q in quarters]
                ))
        
        # Create custom x-axis labels with year annotations
        # We'll use annotations to show years above quarters
        annotations = []
        year_positions = {}
        for i, quarter in enumerate(quarters):
            year = int(quarter.split('_')[0])
            if year not in year_positions:
                year_positions[year] = []
            year_positions[year].append(i)
        
        # Add vertical grid lines only at year boundaries
        shapes = []
        # Add vertical lines only at year boundaries (after Q4 of each year)
        # Year boundaries occur after indices 3, 7, 11, 15, 19 (after Q4 of each year)
        for i in range(21):  # 20 quarters + 1 line after the last quarter
            # Only add line if it's a year boundary (after Q4: positions 3.5, 7.5, 11.5, 15.5, 19.5)
            # or at the very end (position 19.5)
            is_year_boundary = (i > 0 and i % 4 == 0)
            
            if is_year_boundary:
                # Thicker line for year boundaries
                shapes.append({
                    'type': 'line',
                    'xref': 'x',
                    'yref': 'paper',
                    'x0': i - 0.5,
                    'y0': 0,
                    'x1': i - 0.5,
                    'y1': 1,
                    'line': {
                        'color': '#b0b0b0',
                        'width': 1.5
                    },
                    'layer': 'below'
                })
        
        # Add year annotations - positioned above quarters
        sorted_years = sorted(year_positions.keys())
        for year in sorted_years:
            positions = year_positions[year]
            # Position at the middle of the year's quarters
            x_pos = (positions[0] + positions[-1]) / 2
            annotations.append({
                'x': x_pos,
                'y': 1.02,
                'xref': 'x',
                'yref': 'paper',
                'text': str(year),
                'showarrow': False,
                'font': {'size': 13, 'color': 'rgb(27, 54, 93)', 'family': 'Lato'},
                'xanchor': 'center',
                'yanchor': 'bottom'
            })
        
        # Update layout to match Tableau style
        fig.update_layout(
                title={
                    'text': "Projected Oil Capacity additions by Quarter ('000 b/d)",
                    'x': 0,
                    'xanchor': 'left',
                    'font': {'size': 16, 'color': '#fe5000', 'family': 'Lato'},
                    'y': 0.98
                },
            xaxis={
                'title': '',
                'showgrid': False,  # Disable default grid, using custom shapes instead
                'tickmode': 'array',
                'tickvals': list(range(20)),
                'ticktext': x_tick_labels,
                'tickangle': 0,
                'showline': True,
                'linecolor': '#ccc',
                'tickfont': {'color': 'rgb(27, 54, 93)', 'size': 12, 'family': 'Lato'}
            },
            yaxis={
                'title': "'000 b/d",
                'titlefont': {'color': 'rgb(27, 54, 93)', 'size': 12, 'family': 'Lato'},
                'showgrid': True,
                'gridcolor': '#e0e0e0',
                'range': [0, 1300],
                'tickmode': 'linear',
                'tick0': 0,
                'dtick': 200,
                'showline': True,
                'linecolor': '#ccc',
                'tickfont': {'color': 'rgb(27, 54, 93)', 'size': 12, 'family': 'Lato'}
            },
            barmode='stack',
            height=500,
            plot_bgcolor='white',
            paper_bgcolor='white',
            hovermode='closest',
            hoverlabel=dict(
                bgcolor='white',
                bordercolor='#ccc',
                font_size=12
            ),
            showlegend=False,  # Legend is in the filter panel
            margin=dict(l=60, r=50, t=80, b=60),
            annotations=annotations,
            shapes=shapes
        )
        
        return fig
    
    @callback(
        [Output('projects-time-table', 'data'),
         Output('projects-time-table', 'columns'),
         Output('projects-time-table', 'tooltip_data')],
        [Input('current-submenu', 'data'),
         Input('projects-time-chart', 'clickData'),
         Input('likely-filter', 'value')],
        [State('projects-time-chart', 'figure')],
        prevent_initial_call=False
    )
    def update_table(submenu, click_data, likely_filter, figure):
        """Update projects table"""
        try:
            if submenu != 'projects-time':
                return [], [], []
            
            # Load table data
            df = load_table_data()
            
            if df.empty:
                print("Warning: Table data is empty")
                return [], [], []
            
            # Filter by clicked region from chart
            clicked_region = None
            if click_data and isinstance(click_data, dict) and 'points' in click_data and len(click_data['points']) > 0:
                point = click_data['points'][0]
                if isinstance(point, dict):
                    # Get the trace name which is the region
                    if 'fullData' in point and 'name' in point['fullData']:
                        clicked_region = point['fullData']['name']
                    elif figure and isinstance(figure, dict) and 'data' in figure:
                        # Get region from trace index
                        trace_index = point.get('curveNumber', 0)
                        if isinstance(trace_index, int) and trace_index < len(figure['data']):
                            trace_data = figure['data'][trace_index]
                            if isinstance(trace_data, dict) and 'name' in trace_data:
                                clicked_region = trace_data['name']
            
            # Apply region filter (only if clicked, otherwise show all)
            if clicked_region and 'Region' in df.columns:
                # Filter by clicked region
                df = df[df['Region'] == clicked_region].copy()
            
            # Filter by likely filter (now a list from checkboxes)
            # Try to find the column with case-insensitive matching
            likely_col = None
            for col in df.columns:
                col_lower = col.lower()
                if 'likely' in col_lower and ('go' in col_lower or 'ahead' in col_lower):
                    likely_col = col
                    print(f"Found likely column: '{col}'")
                    break
            
            if likely_col:
                # Handle None or empty list
                if not likely_filter:
                    likely_filter = []
                if not isinstance(likely_filter, list):
                    likely_filter = [likely_filter] if likely_filter else []
                
                # If "All" is selected, don't filter (show all data)
                if 'All' in likely_filter:
                    # Show all data - no filtering needed
                    pass
                elif len(likely_filter) > 0:
                    # Map filter values to CSV values
                    # CSV uses "Yes", "No", "Uncertain" but filter uses "Y", "N", "Uncertain"
                    value_mapping = {
                        'Y': ['Yes', 'Y'],
                        'N': ['No', 'N'],
                        'Uncertain': ['Uncertain']
                    }
                    
                    # Build list of values to match
                    filter_values = []
                    for v in likely_filter:
                        if v in value_mapping:
                            filter_values.extend(value_mapping[v])
                        else:
                            filter_values.append(str(v))
                    
                    # Filter by selected values - handle string matching
                    # Convert column values to string for comparison
                    df[likely_col] = df[likely_col].astype(str).str.strip()
                    before_count = len(df)
                    df = df[df[likely_col].isin(filter_values)].copy()
                    after_count = len(df)
                    print(f"Filtered by {likely_filter} (mapped to {filter_values}): {before_count} -> {after_count} rows")
                else:
                    # No checkboxes selected - show no data
                    df = pd.DataFrame()
            
            # Select only the columns to display (in the order shown in the image)
            display_cols = [
                'Project Name',
                'likely_goahead',
                'Country',
                'Region',
                'Opec_group',
                'field_type',
                'field',
                'play_type',
                'Hydrocarbon',
                'Associated Crude',
                'Depth',
                'Operator',
                'Partner1',
                'Partner2',
                'Partner3',
                'Partner4',
                'Partner5',
                'First Oil Year',
                'Sanctioned',
                'Comments',
                'Project Status',
                'Gas Reserves (mmboe)',
                'Liquids Reserves (mmbbl)',
                'Total Reserves (mmboe)',
                'API',
                'Sulfur',
                'Operator Share %',
                'Partner1 Share %',
                'Partner2 Share %',
                'Partner3 Share %',
                'Partner4 Share %',
                'Partner5 Share %',
                # Quarter columns - 2024 to 2029
                '2024_Q1', '2024_Q2', '2024_Q3', '2024_Q4',
                '2025_Q1', '2025_Q2', '2025_Q3', '2025_Q4',
                '2026_Q1', '2026_Q2', '2026_Q3', '2026_Q4',
                '2027_Q1', '2027_Q2', '2027_Q3', '2027_Q4',
                '2028_Q1', '2028_Q2', '2028_Q3', '2028_Q4',
                '2029_Q1', '2029_Q2', '2029_Q3', '2029_Q4'
            ]
            
            # Filter to only include columns that exist and are not filter columns
            available_cols = [col for col in display_cols if col in df.columns]
            
            if not available_cols:
                print("Warning: No display columns found in data")
                return [], [], []
            
            df = df[available_cols].copy()
            
            # Format numeric columns
            numeric_cols = ['Gas Reserves (mmboe)', 'Liquids Reserves (mmbbl)', 'Total Reserves (mmboe)']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    df[col] = df[col].apply(lambda x: f'{x:,.3f}' if pd.notna(x) and x != 0 else '')
            
            # Map display values for boolean and yes/no columns
            # Convert Y/N to Yes/No, true/false to Yes/No
            bool_display_map = {
                'Y': 'Yes',
                'N': 'No',
                'true': 'Yes',
                'false': 'No',
                'True': 'Yes',
                'False': 'No'
            }
            
            # Apply mapping to columns that need it
            bool_columns = ['likely_goahead', 'Sanctioned']
            for col in bool_columns:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip().map(bool_display_map).fillna(df[col])
            
            # Truncate Comments column to 10 characters with "..."
            if 'Comments' in df.columns:
                # Store original comments for tooltip
                original_comments = df['Comments'].copy()
                # Truncate to 10 characters
                df['Comments'] = df['Comments'].astype(str).apply(
                    lambda x: (x[:10] + '...') if len(x) > 10 else x
                )
            else:
                original_comments = pd.Series([''] * len(df))
            
            # Create columns definition with width settings
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
            
            # Map display names for certain columns
            display_name_map = {
                'Opec_group': 'Group',
                'field_type': 'Field Type',
                'field': 'Field/Block',
                'play_type': 'Play Type',
                'likely_goahead': 'Likely To Go Ahead',
            }
            
            columns = []
            for col in available_cols:
                display_name = display_name_map.get(col, col)
                col_def = {'name': display_name, 'id': col}
                if col in column_widths:
                    col_def['minWidth'] = column_widths[col]
                    col_def['maxWidth'] = column_widths[col]
                columns.append(col_def)
            
            # Convert to records - handle NaN values
            df = df.fillna('')
            data = df.to_dict('records')
            
            # Create tooltip data for Comments column - show full text on hover
            tooltip_data = []
            for i, row in enumerate(data):
                tooltip_row = {}
                if 'Comments' in row:
                    # Get original full comment text
                    original_comment = str(original_comments.iloc[i]) if i < len(original_comments) else ''
                    if original_comment and original_comment != 'nan' and original_comment.strip():
                        tooltip_row['Comments'] = {
                            'value': original_comment,
                            'type': 'text'
                        }
                tooltip_data.append(tooltip_row)
            
            return data, columns, tooltip_data
        except Exception as e:
            print(f"Error in update_table: {e}")
            import traceback
            traceback.print_exc()
            return [], [], []
