"""
Latest Updates View
Latest upstream project updates
"""
import os
import pandas as pd
from dash import dcc, html, Input, Output, callback, dash_table, State, no_update, callback_context
import re

# ------------------------------------------------------------------------------
# FILE PATHS
# ------------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "project_by_latets")

CSV_PATHS = {
    "projects_table": os.path.join(DATA_DIR, "Projects_Table_data(1).csv"),
    "latest_updates": os.path.join(DATA_DIR, "Latest Updates_data.csv"),
}

# ------------------------------------------------------------------------------
# DATA LOADING FUNCTIONS
# ------------------------------------------------------------------------------
def load_csv_data(file_path, fallback_data=None, **read_kwargs):
    """Load CSV data with fallback to sample data if file not found."""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return fallback_data
    
    specified_encoding = read_kwargs.pop("encoding", None)
    if specified_encoding:
        encodings_to_try = [specified_encoding, "utf-8", "utf-8-sig", "latin-1"]
    else:
        encodings_to_try = ["utf-8", "utf-8-sig", "latin-1", "utf-16"]
    
    last_error = None
    base_kwargs = read_kwargs or {}
    
    for enc in encodings_to_try:
        try:
            kwargs = dict(base_kwargs)
            if enc:
                kwargs["encoding"] = enc
            df = pd.read_csv(file_path, **kwargs)
            print(f"✅ Loaded {os.path.basename(file_path)} (encoding={enc})")
            return df
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except Exception as e:
            if "header" in str(e).lower() or "lines" in str(e).lower():
                if "header" in base_kwargs:
                    header_val = base_kwargs["header"]
                    for alt_header in [0, 1, None]:
                        if alt_header != header_val:
                            try:
                                kwargs = dict(base_kwargs)
                                kwargs["header"] = alt_header
                                if enc:
                                    kwargs["encoding"] = enc
                                df = pd.read_csv(file_path, **kwargs)
                                print(f"✅ Loaded {os.path.basename(file_path)} (encoding={enc}, header={alt_header})")
                                return df
                            except Exception:
                                continue
            last_error = e
            continue
    
    print(f"❌ Error loading {file_path}: {last_error}")
    return fallback_data

# Load dataframes globally once
df_projects_table = load_csv_data(CSV_PATHS["projects_table"])
df_latest_updates = load_csv_data(CSV_PATHS["latest_updates"])

# Function to create clickable links
def create_link_text(comment, link_url):
    """Create markdown link text if both comment and link_url are available"""
    if pd.notna(link_url) and pd.notna(comment) and str(link_url).strip() != '':
        # Clean up the comment text
        clean_comment = str(comment).strip()
        # Return markdown formatted link
        return f"[{clean_comment}]({link_url})"
    elif pd.notna(comment):
        return str(comment).strip()
    else:
        return 'No link available'

# Pre-process dataframes to match image exactly
if df_projects_table is not None and not df_projects_table.empty:
    # Convert Likely Go-ahead to proper format
    df_projects_table['Likely Go-ahead'] = df_projects_table['Likely Go-ahead'].astype(str)
    # Map values to match image: Yes, No, Uncertain
    df_projects_table['Likely Go-ahead'] = df_projects_table['Likely Go-ahead'].str.upper().replace({
        'TRUE': 'Yes', 'FALSE': 'No', 'YES': 'Yes', 'NO': 'No', 
        'Y': 'Yes', 'N': 'No', 'UNCERTAIN': 'Uncertain'
    })
    
    df_projects_table['Project Name'] = df_projects_table['Project Name'].fillna('N/A')
    df_projects_table['Country'] = df_projects_table['Country'].fillna('N/A')
    
    # Create clickable links for "All Projects" table
    comment_col = 'Comments' if 'Comments' in df_projects_table.columns else None
    link_col = 'Comments_link' if 'Comments_link' in df_projects_table.columns else None
    
    if comment_col and link_col:
        df_projects_table['Click on the link below to go to the relevant article'] = df_projects_table.apply(
            lambda row: create_link_text(row[comment_col], row[link_col]), axis=1
        )
    elif comment_col:
        df_projects_table['Click on the link below to go to the relevant article'] = df_projects_table[comment_col].fillna('No link available')
    else:
        df_projects_table['Click on the link below to go to the relevant article'] = 'No link available'

if df_latest_updates is not None and not df_latest_updates.empty:
    # Convert Likely Go-ahead to proper format
    df_latest_updates['Likely Go-ahead'] = df_latest_updates['Likely Go-ahead'].astype(str)
    # Map values to match image: Yes, No, Uncertain
    df_latest_updates['Likely Go-ahead'] = df_latest_updates['Likely Go-ahead'].str.upper().replace({
        'TRUE': 'Yes', 'FALSE': 'No', 'YES': 'Yes', 'NO': 'No',
        'Y': 'Yes', 'N': 'No', 'UNCERTAIN': 'Uncertain'
    })
    
    df_latest_updates['Project Name'] = df_latest_updates['Project Name'].fillna('N/A')
    df_latest_updates['Country'] = df_latest_updates['Country'].fillna('N/A')
    df_latest_updates['Project Status'] = df_latest_updates['Project Status'].fillna('N/A')
    
    # Handle First Oil Year/Date - check different column names
    first_oil_col = None
    for col in ['First Oil', 'First Oil Year', 'First Oil Date']:
        if col in df_latest_updates.columns:
            first_oil_col = col
            break
    
    if first_oil_col:
        df_latest_updates['First Oil'] = df_latest_updates[first_oil_col].fillna('N/A')
    else:
        df_latest_updates['First Oil'] = 'N/A'
    
    # Create clickable links for "Updated Projects" table
    comment_col = 'Comments' if 'Comments' in df_latest_updates.columns else None
    link_col = 'Comments_link' if 'Comments_link' in df_latest_updates.columns else None
    
    if comment_col and link_col:
        df_latest_updates['Click on the link below to go to the relevant article'] = df_latest_updates.apply(
            lambda row: create_link_text(row[comment_col], row[link_col]), axis=1
        )
    elif comment_col:
        df_latest_updates['Click on the link below to go to the relevant article'] = df_latest_updates[comment_col].fillna('No link available')
    else:
        df_latest_updates['Click on the link below to go to the relevant article'] = 'No link available'


def create_layout():
    """Create the exact layout matching the image"""
    return html.Div(style={
        'backgroundColor': '#f5f5f5',
        'minHeight': '100vh',
        'padding': '12px 0',
        'margin': '0',
        'fontFamily': 'Arial, sans-serif',
    }, children=[
        html.Div(style={
            'width': '100%',
            'maxWidth': '1220px',
            'margin': '0 auto',
            'fontFamily': 'Arial, sans-serif',
            'backgroundColor': 'white',
            'border': '1px solid #d6d6d6',
            'boxShadow': 'none',
            'borderRadius': '0',
            'padding': '12px 14px 18px 14px',
        }, children=[
            # "Click here to search for key Articles" link
            html.A(
                "Click here to search for key Articles",
                href="https://www.energyintel.com/search?text=upstream%20projects",
                target="_blank",
                style={
                    'color': '#1155cc',
                    'textDecoration': 'underline',
                    'fontSize': '12px',
                    'fontFamily': 'Arial, sans-serif',
                    'fontWeight': 'normal',
                    'marginBottom': '12px',
                    'display': 'block',
                    'textAlign': 'left',
                }
            ),

            # Header section with title and filter
            html.Div(style={
                'display': 'flex',
                'justifyContent': 'space-between',
                'alignItems': 'flex-start',
                'marginBottom': '8px',
            }, children=[
                # Title section
                html.Div(children=[
                    html.H3(
                        "List of Updated Projects- Week of December 1, 2025",
                        style={
                            'color': '#ff6600',
                            'margin': '0',
                            'fontSize': '14px',
                            'fontWeight': 'bold',
                            'fontFamily': 'Arial, sans-serif',
                            'whiteSpace': 'nowrap',
                            'flexShrink': '0',
                            'paddingTop': '2px',
                        }
                    ),
                ]),
                
                # Filter container for "Likely To Go Ahead"
                html.Div(style={
                    'backgroundColor': 'white',
                    'padding': '6px 8px',
                    'border': '1px solid #cccccc',
                    'borderRadius': '0',
                    'boxShadow': 'none',
                    'minWidth': '170px',
                    'marginLeft': '16px',
                    'flexShrink': '0',
                }, children=[
                    html.Label(
                        "Likely To Go Ahead",
                        style={
                            'display': 'block',
                            'marginBottom': '4px',
                            'fontSize': '11px',
                            'fontWeight': 'normal',
                            'color': '#000000',
                            'fontFamily': 'Arial, sans-serif',
                            'whiteSpace': 'nowrap',
                        }
                    ),
                    dcc.Checklist(
                        id='filter-go-ahead',
                        options=[
                            {'label': '(All)', 'value': 'ALL'},
                            {'label': 'Y', 'value': 'Y'},
                            {'label': 'N', 'value': 'N'},
                            {'label': 'Uncertain', 'value': 'UNCERTAIN'}
                        ],
                        value=['ALL'],
                        inline=False,
                        style={
                            'fontSize': '11px',
                            'fontFamily': 'Arial, sans-serif',
                            'color': '#000000',
                        },
                        labelStyle={
                            'display': 'flex',
                            'alignItems': 'center',
                            'marginBottom': '2px',
                        },
                        inputStyle={
                            'marginRight': '5px',
                            'marginTop': '0',
                            'marginBottom': '0',
                        }
                    )
                ])
            ]),
            
            # Container for Updated Projects table that can be hidden
            html.Div(id='updated-projects-container', children=[
                # FIRST TABLE: List of Updated Projects
                dash_table.DataTable(
                    id='latest-updates-table',
                    columns=[
                        {"name": "Project Name", "id": "Project Name", "presentation": "markdown"},
                        {"name": "Likely Go-ahead", "id": "Likely Go-ahead", "presentation": "markdown"},
                        {"name": "Country", "id": "Country", "presentation": "markdown"},
                        {"name": "Project Status", "id": "Project Status", "presentation": "markdown"},
                        {"name": "First Oil", "id": "First Oil", "presentation": "markdown"},
                        {"name": "Click on the link below to go to the relevant article", "id": "Click on the link below to go to the relevant article", "presentation": "markdown"}
                    ] if df_latest_updates is not None else [],
                    data=df_latest_updates.to_dict('records') if df_latest_updates is not None else [],
                    style_table={
                        'overflowX': 'auto',
                        'overflowY': 'hidden',
                        'marginBottom': '18px',
                        'border': '1px solid #999999',
                        'borderRadius': '0',
                        'boxShadow': 'none',
                        'fontFamily': 'Arial, sans-serif',
                        'width': '100%',
                        'minWidth': '1180px',
                    },
                    style_cell={
                        'textAlign': 'left',
                        'padding': '2px 5px',
                        'fontSize': '11px',
                        'fontFamily': 'Arial, sans-serif',
                        'color': '#000000',
                        'borderBottom': '1px solid #cccccc',
                        'borderRight': '1px solid #cccccc',
                        'backgroundColor': 'white',
                        'whiteSpace': 'normal',
                        'overflow': 'hidden',
                        'textOverflow': 'ellipsis',
                        'minWidth': '90px',
                        'maxWidth': '260px',
                    },
                    style_header={
                        'backgroundColor': '#d9d9d9',
                        'fontWeight': 'bold',
                        'fontSize': '11px',
                        'fontFamily': 'Arial, sans-serif',
                        'color': '#000000',
                        'borderBottom': '2px solid #999999',
                        'borderRight': '1px solid #999999',
                        'borderTop': '1px solid #999999',
                        'borderLeft': '1px solid #999999',
                        'padding': '3px 5px',
                        'textAlign': 'left',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#ffffff'
                        },
                        {
                            'if': {'row_index': 'even'},
                            'backgroundColor': '#f8f8f8'
                        },
                        {
                            'if': {'state': 'selected'},
                            'backgroundColor': '#e6f3ff',
                            'border': 'none'
                        },
                        {
                            'if': {'column_id': 'Click on the link below to go to the relevant article'},
                            'color': '#1155cc',
                            'textDecoration': 'underline',
                            'cursor': 'pointer',
                            'whiteSpace': 'normal',
                            'lineHeight': '1.2',
                        }
                    ],
                    style_data={
                        'whiteSpace': 'normal',
                        'height': '22px',
                        'lineHeight': '1.15',
                    },
                    css=[{
                        'selector': '.dash-cell div.dash-cell-value',
                        'rule': 'display: inline; white-space: normal;'
                    }],
                    sort_action="native",
                    filter_action="none",
                    page_action="none",
                    markdown_options={"html": True, "link_target": "_blank"},
                    editable=False,
                ),
            ]),
            
            # "All Projects" title (always visible)
            html.H3(
                "All Projects",
                id='all-projects-title',
                style={
                    'color': '#ff6600',
                    'margin': '6px 0 8px 0',
                    'fontSize': '14px',
                    'fontWeight': 'bold',
                    'fontFamily': 'Arial, sans-serif',
                    'borderBottom': '1px solid #cccccc',
                    'paddingBottom': '5px',
                }
            ),
            
            # Container for All Projects table that can be hidden
            html.Div(id='all-projects-table-container', children=[
                # SECOND TABLE: All Projects
                dash_table.DataTable(
                    id='projects-table',
                    columns=[
                        {"name": "Project Name", "id": "Project Name", "presentation": "markdown"},
                        {"name": "Likely Go-ahead", "id": "Likely Go-ahead", "presentation": "markdown"},
                        {"name": "Country", "id": "Country", "presentation": "markdown"},
                        {"name": "Click on the link below to go to the relevant article", "id": "Click on the link below to go to the relevant article", "presentation": "markdown"}
                    ] if df_projects_table is not None else [],
                    data=df_projects_table.to_dict('records') if df_projects_table is not None else [],
                    style_table={
                        'overflowX': 'auto',
                        'overflowY': 'auto',
                        'height': '460px',
                        'maxHeight': '460px',
                        'border': '1px solid #999999',
                        'borderRadius': '0',
                        'boxShadow': 'none',
                        'fontFamily': 'Arial, sans-serif',
                        'width': '100%',
                        'minWidth': '1180px',
                    },
                    style_cell={
                        'textAlign': 'left',
                        'padding': '2px 5px',
                        'fontSize': '11px',
                        'fontFamily': 'Arial, sans-serif',
                        'color': '#000000',
                        'borderBottom': '1px solid #cccccc',
                        'borderRight': '1px solid #cccccc',
                        'backgroundColor': 'white',
                        'whiteSpace': 'normal',
                        'overflow': 'hidden',
                        'textOverflow': 'ellipsis',
                        'minWidth': '90px',
                        'maxWidth': '320px',
                    },
                    style_header={
                        'backgroundColor': '#d9d9d9',
                        'fontWeight': 'bold',
                        'fontSize': '11px',
                        'fontFamily': 'Arial, sans-serif',
                        'color': '#000000',
                        'borderBottom': '2px solid #999999',
                        'borderRight': '1px solid #999999',
                        'borderTop': '1px solid #999999',
                        'borderLeft': '1px solid #999999',
                        'padding': '3px 5px',
                        'textAlign': 'left',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#ffffff'
                        },
                        {
                            'if': {'row_index': 'even'},
                            'backgroundColor': '#f8f8f8'
                        },
                        {
                            'if': {'state': 'selected'},
                            'backgroundColor': '#e6f3ff',
                            'border': 'none'
                        },
                        {
                            'if': {'column_id': 'Click on the link below to go to the relevant article'},
                            'color': '#1155cc',
                            'textDecoration': 'underline',
                            'cursor': 'pointer',
                            'whiteSpace': 'normal',
                            'lineHeight': '1.2',
                        }
                    ],
                    style_data={
                        'whiteSpace': 'normal',
                        'height': '22px',
                        'lineHeight': '1.15',
                    },
                    css=[{
                        'selector': '.dash-cell div.dash-cell-value',
                        'rule': 'display: inline; white-space: normal;'
                    }],
                    sort_action="native",
                    filter_action="none",
                    page_action="none",
                    markdown_options={"html": True, "link_target": "_blank"},
                    editable=False,
                ),
            ])
        ])
    ])


def register_callbacks(dash_app, server):
    """Register all callbacks for the Upstream Projects dashboard"""
    
    @dash_app.callback(
        [Output('projects-table', 'data'),
         Output('latest-updates-table', 'data'),
         Output('updated-projects-container', 'style'),
         Output('all-projects-table-container', 'style')],
        [Input('filter-go-ahead', 'value')]
    )
    def update_dashboard_data(selected_go_ahead):
        """
        Filter both tables based on selected Likely Go-ahead values.
        
        Rules:
        1. ALL selected → show all rows in both tables
        2. Empty selection → COMPLETELY HIDE both tables (headers only, titles remain)
        3. N selected → show only rows with Likely Go-ahead = No
        4. Y selected → show only rows with Likely Go-ahead = Yes  
        5. Uncertain selected → show only rows with Likely Go-ahead = Uncertain
        6. Multiple selected → show rows matching any of the selected values
        """
        
        # Default styles - show both containers
        updated_container_style = {'display': 'block'}
        all_table_container_style = {'display': 'block'}
        
        # If nothing selected → HIDE both TABLE containers (but keep titles)
        if not selected_go_ahead:
            updated_container_style = {'display': 'none'}
            all_table_container_style = {'display': 'none'}
            return [], [], updated_container_style, all_table_container_style
        
        # If ALL selected → show all data
        if 'ALL' in selected_go_ahead:
            return (
                df_projects_table.to_dict('records') if df_projects_table is not None and not df_projects_table.empty else [],
                df_latest_updates.to_dict('records') if df_latest_updates is not None and not df_latest_updates.empty else [],
                updated_container_style,
                all_table_container_style
            )
        
        # Map checkbox values to actual data values
        value_mapping = {
            'Y': 'Yes',
            'N': 'No', 
            'UNCERTAIN': 'Uncertain'
        }
        
        # Get the actual values to filter by
        filter_values = []
        for val in selected_go_ahead:
            if val in value_mapping:
                filter_values.append(value_mapping[val])
        
        # If no valid filter values, hide both table containers
        if not filter_values:
            updated_container_style = {'display': 'none'}
            all_table_container_style = {'display': 'none'}
            return [], [], updated_container_style, all_table_container_style
        
        # Filter both dataframes
        df_filtered_projects = pd.DataFrame()
        df_filtered_updates = pd.DataFrame()
        
        if df_projects_table is not None and not df_projects_table.empty:
            df_filtered_projects = df_projects_table[
                df_projects_table['Likely Go-ahead'].isin(filter_values)
            ].copy()
        
        if df_latest_updates is not None and not df_latest_updates.empty:
            df_filtered_updates = df_latest_updates[
                df_latest_updates['Likely Go-ahead'].isin(filter_values)
            ].copy()
        
        # If filtered data is empty, hide the table containers (but titles remain visible)
        if df_filtered_projects.empty:
            all_table_container_style = {'display': 'none'}
        
        if df_filtered_updates.empty:
            updated_container_style = {'display': 'none'}
        
        return (
            df_filtered_projects.to_dict('records') if not df_filtered_projects.empty else [],
            df_filtered_updates.to_dict('records') if not df_filtered_updates.empty else [],
            updated_container_style,
            all_table_container_style
        )
    
    @dash_app.callback(
        Output('filter-go-ahead', 'value'),
        [Input('filter-go-ahead', 'value')]
    )
    def manage_checklist_selection(selected_values):
        """
        Manage the checkbox logic:
        - When ALL is selected with other options, keep only ALL
        - When all three individual options are selected, show ALL
        - When ALL is deselected, clear all selections
        """
        if not selected_values:
            return []
        
        # If ALL is selected with other options, keep only ALL
        if 'ALL' in selected_values and len(selected_values) > 1:
            # If user clicked ALL while others were selected, select only ALL
            return ['ALL']
        
        # Get individual options (excluding ALL)
        individual_options = [v for v in selected_values if v != 'ALL']
        
        # If all three individual options are selected, show ALL instead
        if set(individual_options) == {'Y', 'N', 'UNCERTAIN'}:
            return ['ALL']
        
        # If ALL is deselected (was in previous selection but not in current), clear all
        ctx = callback_context
        if ctx.triggered:
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
            if trigger_id == 'filter-go-ahead':
                # Check if ALL was previously selected but is not now
                previous_values = ctx.states.get('filter-go-ahead.value', [])
                if 'ALL' in previous_values and 'ALL' not in selected_values:
                    # User deselected ALL, so clear all
                    return []
        
        return selected_values