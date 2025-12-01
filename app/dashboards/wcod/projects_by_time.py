"""
Projects by Time View
Upstream projects over time - Tableau-style design
"""
import os
from pathlib import Path
from dash import dcc, html, Input, Output, State, callback, dash_table
import plotly.graph_objects as go
import pandas as pd
from app import db
from app.models import UpstreamProject


# Data file paths
BASE_DIR = Path(__file__).parent.parent / 'data' / 'upstream_projects'
CHART_CSV = BASE_DIR / 'Projects by Time_Chart.csv'
TABLE_CSV = BASE_DIR / 'Projects by Time_Table.csv'

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
    """Load table data from CSV"""
    try:
        # Check if file exists
        if not TABLE_CSV.exists():
            print(f"Error: Table CSV file not found at {TABLE_CSV}")
            return pd.DataFrame()
        
        # Try different encodings
        encodings = ['utf-16', 'utf-8', 'latin-1', 'utf-8-sig']
        df = None
        last_error = None
        
        for encoding in encodings:
            try:
                # Read CSV, skip first 3 rows (copyright info), use row 4 as header
                df = pd.read_csv(TABLE_CSV, sep='\t', skiprows=3, header=0, encoding=encoding)
                print(f"Successfully loaded table data with encoding: {encoding}")
                break
            except (UnicodeDecodeError, UnicodeError) as e:
                last_error = e
                continue
            except Exception as e:
                print(f"Error reading CSV with encoding {encoding}: {e}")
                last_error = e
                continue
        
        if df is None:
            print(f"Failed to load table data. Last error: {last_error}")
            return pd.DataFrame()
        
        if df.empty:
            print("Warning: Loaded table data is empty")
            return pd.DataFrame()
        
        # Strip whitespace from column names for matching
        df.columns = df.columns.str.strip()
        
        print(f"Table columns found: {list(df.columns)[:20]}")
        print(f"Total rows loaded: {len(df)}")
        
        # Select all columns we need for the table (matching the image structure)
        required_cols = [
            'Project Name',
            'Likely Go-ahead',
            'Country',
            'Region',
            'Group',
            'Field Type',
            'Field/Block',
            'Play Type',
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
            'Sulfur'
        ]
        
        # Filter to only include columns that exist
        available_cols = [col for col in required_cols if col in df.columns]
        
        if not available_cols:
            print(f"Warning: None of the required columns found. Available columns: {list(df.columns)[:20]}")
            # Return all columns if none match
            return df
        
        df = df[available_cols].copy()
        
        # Clean data - replace NaN with empty strings
        df = df.fillna('')
        
        print(f"Table data loaded successfully. Rows: {len(df)}, Columns: {len(df.columns)}")
        
        return df
    except Exception as e:
        print(f"Error loading table data: {e}")
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
                    )
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
            html.H4("Project Details", style={'marginBottom': '15px', 'fontSize': '16px', 'fontWeight': 'bold', 'fontFamily': 'Lato, sans-serif'}),
            dash_table.DataTable(
                id='projects-time-table',
                style_table={
                    'overflowX': 'auto',
                    'border': '1px solid #ddd'
                },
                style_cell={
                    'textAlign': 'left',
                    'padding': '8px',
                    'fontSize': '12px',
                    'fontFamily': 'Lato, sans-serif',
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
                    'border': '1px solid #ddd',
                    'textAlign': 'center'
                },
                style_data={
                    'border': '1px solid #ddd',
                    'whiteSpace': 'normal'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#f9f9f9'
                    }
                ],
                page_size=20,
                page_action='native',
                sort_action='native',
                filter_action='native',
                tooltip_duration=None,
                css=[{
                    'selector': '.dash-table-tooltip',
                    'rule': 'font-size: 10px !important; max-width: 400px !important; white-space: normal !important; word-wrap: break-word !important; line-height: 1.4 !important; padding: 6px 8px !important;'
                }]
            )
        ], style={'marginTop': '20px'})
    ], className='tab-content', style={'padding': '20px', 'backgroundColor': '#ffffff'})


def register_callbacks(dash_app, server):
    """Register all callbacks for Projects by Time"""
    
    @callback(
        Output('projects-time-chart', 'figure'),
        [Input('current-submenu', 'data')]
    )
    def update_chart(submenu):
        """Update projects by time chart"""
        if submenu != 'projects-time':
            return go.Figure()
        
        # Load chart data
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
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'family': 'Lato'}
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
                    'x': 0.5,
                    'xanchor': 'left',
                    'font': {'size': 16, 'color': '#333', 'family': 'Lato'},
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
            
            if likely_col and likely_filter:
                # Handle None or empty list
                if not isinstance(likely_filter, list):
                    likely_filter = [likely_filter] if likely_filter else []
                
                # If "All" is selected, don't filter
                if 'All' not in likely_filter and len(likely_filter) > 0:
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
            
            # Select only the columns to display (in the order shown in the image)
            display_cols = [
                'Project Name',
                'Likely Go-ahead',
                'Country',
                'Region',
                'Group',
                'Field Type',
                'Field/Block',
                'Play Type',
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
                'Sulfur'
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
                'Likely Go-ahead': '100px',
                'Country': '120px',
                'Region': '120px',
                'Group': '140px',
                'Field Type': '100px',
                'Field/Block': '150px',
                'Play Type': '120px',
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
            
            columns = []
            for col in available_cols:
                col_def = {'name': col, 'id': col}
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
