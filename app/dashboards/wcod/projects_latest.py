"""
Latest Updates View
Latest upstream project updates
"""
import os
import pandas as pd
from dash import dcc, html, Input, Output, callback, dash_table, State, no_update

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
        return ''

# Pre-process dataframes to match image exactly
if df_projects_table is not None and not df_projects_table.empty:
    # Convert Likely Go-ahead to proper format
    df_projects_table['Likely Go-ahead'] = df_projects_table['Likely Go-ahead'].astype(str)
    # Map values to match image: Y -> Yes, N -> No, keep Uncertain as is
    df_projects_table['Likely Go-ahead'] = df_projects_table['Likely Go-ahead'].str.upper().replace({
        'TRUE': 'Yes', 'FALSE': 'No', 'YES': 'Yes', 'NO': 'No', 'Y': 'Yes', 'N': 'No'
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
        df_projects_table['Click on the link below to go to the relevant article'] = df_projects_table[comment_col].fillna('')
    else:
        df_projects_table['Click on the link below to go to the relevant article'] = ''

if df_latest_updates is not None and not df_latest_updates.empty:
    # Convert Likely Go-ahead to proper format
    df_latest_updates['Likely Go-ahead'] = df_latest_updates['Likely Go-ahead'].astype(str)
    # Map values to match image: Y -> Yes, N -> No, keep Uncertain as is
    df_latest_updates['Likely Go-ahead'] = df_latest_updates['Likely Go-ahead'].str.upper().replace({
        'TRUE': 'Yes', 'FALSE': 'No', 'YES': 'Yes', 'NO': 'No', 'Y': 'Yes', 'N': 'No'
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
        df_latest_updates['Click on the link below to go to the relevant article'] = df_latest_updates[comment_col].fillna('')
    else:
        df_latest_updates['Click on the link below to go to the relevant article'] = ''


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
                            {'label': 'N', 'value': 'N'},
                            {'label': 'Uncertain', 'value': 'Uncertain'},
                            {'label': 'Y', 'value': 'Y'}
                        ],
                        value=[],
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
                data=[] if df_latest_updates is not None else [],
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
            
            # "All Projects" title
            html.H3(
                "All Projects",
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
            
            # SECOND TABLE: All Projects
            dash_table.DataTable(
                id='projects-table',
                columns=[
                    {"name": "Project Name", "id": "Project Name", "presentation": "markdown"},
                    {"name": "Likely Go-ahead", "id": "Likely Go-ahead", "presentation": "markdown"},
                    {"name": "Country", "id": "Country", "presentation": "markdown"},
                    {"name": "Click on the link below to go to the relevant article", "id": "Click on the link below to go to the relevant article", "presentation": "markdown"}
                ] if df_projects_table is not None else [],
                data=[] if df_projects_table is not None else [],
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
            )
        ])
    ])


def register_callbacks(dash_app, server):
    """Register all callbacks for the Upstream Projects dashboard"""
    
    @dash_app.callback(
        [Output('projects-table', 'data'),
         Output('latest-updates-table', 'data')],
        [Input('filter-go-ahead', 'value')]
    )
    def update_dashboard_data(selected_go_ahead):
        """
        Filter logic:
        - Empty selection → hide both tables (return empty lists)
        - 'ALL' selected → show all rows and check all boxes
        - 'N' selected → show only rows with Likely Go-ahead = 'No'
        - 'Y' selected → show only rows with Likely Go-ahead = 'Yes'
        - 'Uncertain' selected → show only rows with Likely Go-ahead = 'Uncertain'
        """
        
        # If nothing selected → return empty data (hide tables)
        if not selected_go_ahead or len(selected_go_ahead) == 0:
            return [], []
        
        df_projects = df_projects_table.copy() if df_projects_table is not None else pd.DataFrame()
        df_updates = df_latest_updates.copy() if df_latest_updates is not None else pd.DataFrame()
        
        # If 'ALL' in selection → show all data
        if 'ALL' in selected_go_ahead:
            return (
                df_projects.to_dict('records') if not df_projects.empty else [],
                df_updates.to_dict('records') if not df_updates.empty else []
            )
        
        # Otherwise, filter by selected values
        # Map filter values to actual dataframe values
        mapped_values = []
        for val in selected_go_ahead:
            if val == 'Y':
                mapped_values.append('Yes')
            elif val == 'N':
                mapped_values.append('No')
            elif val == 'Uncertain':
                mapped_values.append('Uncertain')
        
        # Filter both dataframes
        if mapped_values:
            if not df_projects.empty:
                df_projects = df_projects[df_projects['Likely Go-ahead'].isin(mapped_values)]
            if not df_updates.empty:
                df_updates = df_updates[df_updates['Likely Go-ahead'].isin(mapped_values)]
        
        return (
            df_projects.to_dict('records') if not df_projects.empty else [],
            df_updates.to_dict('records') if not df_updates.empty else []
        )
    
    @dash_app.callback(
        Output('filter-go-ahead', 'value'),
        Input('filter-go-ahead', 'value')
    )
    def toggle_all_go_ahead(selected_values):
        """
        Logic for (All) checkbox:
        - If (All) and other options selected → keep only (All)
        - If N, Y, Uncertain all selected → automatically select (All)
        - Otherwise → return the selected values as-is
        """
        
        if not selected_values:
            return selected_values
        
        # If 'ALL' is selected along with other options, return only 'ALL'
        if 'ALL' in selected_values and len(selected_values) > 1:
            return ['ALL']
        
        # If all individual options are selected, automatically select 'ALL'
        individuals = [v for v in selected_values if v != 'ALL']
        if set(individuals) == {'N', 'Y', 'Uncertain'}:
            return ['ALL']
        
        return selected_values
