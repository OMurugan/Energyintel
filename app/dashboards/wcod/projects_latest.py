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
        'backgroundColor': '#ffffff',
        'minHeight': '100vh',
        'padding': '12px 0',
        'margin': '0',
        'fontFamily': 'Times New Roman, Times, serif',
    }, children=[
        html.Div(style={
            'width': '100%',
            'maxWidth': '1220px',
            'margin': '0 auto',
            'fontFamily': 'Times New Roman, Times, serif',
            'backgroundColor': 'white',
            'border': 'none',
            'boxShadow': 'none',
            'borderRadius': '0',
            'padding': '12px 14px 18px 14px',
            'position': 'relative',
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
                    'fontFamily': 'Times New Roman, Times, serif',
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
                        "List of Updated Projects- Week of December 8, 2025",
                        style={
                            'color': '#ff6600',
                            'margin': '0',
                            'fontSize': '16px',
                            'fontWeight': 'bold',
                            'fontFamily': 'Times New Roman, Times, serif',
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
                            'fontSize': '12px',
                            'fontWeight': 'normal',
                            'color': '#000000',
                            'fontFamily': 'Times New Roman, Times, serif',
                            'whiteSpace': 'nowrap',
                        }
                    ),
                    dcc.Checklist(
                        id='filter-go-ahead',
                        options=[
                            {'label': '(All)', 'value': 'ALL'},
                            {'label': '', 'value': 'EMPTY'},
                            {'label': 'N', 'value': 'N'},
                            {'label': 'Uncertain', 'value': 'UNCERTAIN'},
                            {'label': 'Y', 'value': 'Y'},
                           
                           
                        ],
                        value=['Y'],
                        inline=False,
                        style={
                            'fontSize': '12px',
                            'fontFamily': 'Times New Roman, Times, serif',
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
            
            # Sorting controls popup (initially hidden)
            html.Div([
                html.Div([
                    html.Div("Data source order", id="popup-source-btn", 
                            style={
                                "padding": "6px 10px", 
                                "fontSize": "12px",
                                "cursor": "pointer",
                                "fontFamily": "Times New Roman, Times, serif",
                                "color": "#333",
                            }),
                    html.Div("Alphabetic", id="popup-alphabetic-btn",
                            style={
                                "padding": "6px 10px", 
                                "fontSize": "12px",
                                "cursor": "pointer",
                                "fontFamily": "Times New Roman, Times, serif",
                                "color": "#333",
                            }),
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
                           "fontFamily": "Times New Roman, Times, serif",
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
                           "fontFamily": "Times New Roman, Times, serif",
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
                "border": "1px solid #ccc",
                "borderRadius": "2px",
            }),

            # Hidden buttons for header interactions
            html.Button("Sort Ascending Click", id="sort-asc-btn-hidden", n_clicks=0, style={"display": "none"}),
            html.Button("Sort Descending Click", id="sort-desc-btn-hidden", n_clicks=0, style={"display": "none"}),
            html.Button("Popup Menu Click", id="popup-menu-btn", n_clicks=0, style={"display": "none"}),
            html.Button("Field Sort Click", id="field-sort-btn", n_clicks=0, style={"display": "none"}),
            html.Button("Nested Sort Click", id="nested-sort-btn", n_clicks=0, style={"display": "none"}),
            html.Div(id='dummy-output-clientside', style={'display': 'none'}),
            
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
                        'fontFamily': 'Times New Roman, Times, serif',
                        'width': '100%',
                        'minWidth': '1180px',
                    },
                    style_cell={
                        'textAlign': 'left',
                        'padding': '2px 5px',
                        'fontSize': '12px',
                        'fontFamily': 'Times New Roman, Times, serif',
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
                        'fontSize': '12px',
                        'fontFamily': 'Times New Roman, Times, serif',
                        'color': '#000000',
                        'borderBottom': '2px solid #999999',
                        'borderRight': '1px solid #999999',
                        'borderTop': '1px solid #999999',
                        'borderLeft': '1px solid #999999',
                        'padding': '3px 5px',
                        'textAlign': 'left',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                        'position': 'relative',
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
                    sort_action="none",
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
                    'margin': '12px 0 8px 0',
                    'fontSize': '16px',
                    'fontWeight': 'bold',
                    'fontFamily': 'Times New Roman, Times, serif',
                    'borderBottom': 'none',
                    'paddingBottom': '0',
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
                        'fontFamily': 'Times New Roman, Times, serif',
                        'width': '100%',
                        'minWidth': '1180px',
                    },
                    style_cell={
                        'textAlign': 'left',
                        'padding': '2px 5px',
                        'fontSize': '12px',
                        'fontFamily': 'Times New Roman, Times, serif',
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
                        'fontSize': '12px',
                        'fontFamily': 'Times New Roman, Times, serif',
                        'color': '#000000',
                        'borderBottom': '2px solid #999999',
                        'borderRight': '1px solid #999999',
                        'borderTop': '1px solid #999999',
                        'borderLeft': '1px solid #999999',
                        'padding': '3px 5px',
                        'textAlign': 'left',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                        'position': 'relative',
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
                    # sort_action="native",
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
        
        # Allowed values mapping
        filter_map = {
            'Y': 'YES',
            'N': 'NO',
            'UNCERTAIN': 'UNCERTAIN',
            'EMPTY': 'EMPTY'
        }
        
        # Normalize selected values
        normalized_selection = [filter_map[v] for v in selected_go_ahead if v in filter_map]
        
        # If no valid filter values, hide both table containers
        if not normalized_selection:
            updated_container_style = {'display': 'none'}
            all_table_container_style = {'display': 'none'}
            return [], [], updated_container_style, all_table_container_style
        
        def filter_df(df):
            if df is None or df.empty:
                return pd.DataFrame()
            
            col = df['Likely Go-ahead'].fillna('').astype(str)
            upper = col.str.strip().str.upper()
            
            mask = pd.Series(False, index=df.index)
            
            if 'YES' in normalized_selection:
                mask |= upper == 'YES'
            if 'NO' in normalized_selection:
                mask |= upper == 'NO'
            if 'UNCERTAIN' in normalized_selection:
                mask |= upper == 'UNCERTAIN'
            if 'EMPTY' in normalized_selection:
                mask |= ~upper.isin(['YES', 'NO', 'UNCERTAIN']) | (upper == '')
            
            return df[mask].copy()
        
        df_filtered_projects = filter_df(df_projects_table)
        df_filtered_updates = filter_df(df_latest_updates)
        
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
        
        # If ALL is selected, ensure all options are checked
        if 'ALL' in selected_values:
            return ['ALL', 'EMPTY', 'N', 'UNCERTAIN', 'Y']
        
        # Normalize to unique values (without ALL)
        allowed_values = ['EMPTY', 'N', 'UNCERTAIN', 'Y']
        individual_options = [v for v in allowed_values if v in selected_values]
        
        # If all options are selected, include ALL for clarity
        if set(individual_options) == set(allowed_values):
            return ['ALL'] + allowed_values
        
        return individual_options
    # SIMPLE CLIENTSIDE CALLBACK - This will definitely work
    dash_app.clientside_callback(
        """
        function(columns) {
            setTimeout(function() {
                // Apply A/Z and down-arrow to specific columns
                
                // Function to add A/Z and down-arrow to a header
                function addSortUI(header) {
                    // Check if already has the UI
                    if (header.querySelector('.sort-order-container')) {
                        return;
                    }
                    
                    // Create A/Z container
                    const sortContainer = document.createElement('div');
                    sortContainer.style.position = 'absolute';
                    sortContainer.style.right = '30px';
                    sortContainer.style.top = '50%';
                    sortContainer.style.transform = 'translateY(-50%)';
                    sortContainer.style.fontSize = '10px';
                    sortContainer.style.color = '#666';
                    sortContainer.style.cursor = 'pointer';
                    sortContainer.style.padding = '2px';
                    sortContainer.style.border = '1px solid transparent';
                    sortContainer.style.borderRadius = '2px';
                    sortContainer.style.lineHeight = '1';
                    sortContainer.style.textAlign = 'center';
                    sortContainer.style.display = 'flex';
                    sortContainer.style.flexDirection = 'column';
                    sortContainer.style.alignItems = 'center';
                    sortContainer.style.justifyContent = 'center';
                    sortContainer.style.height = '30px';
                    sortContainer.style.opacity = '0';
                    sortContainer.style.transition = 'opacity 0.2s ease';
                    sortContainer.style.zIndex = '2';
                    sortContainer.className = 'sort-order-container';
                    
                    // Create A button
                    const aElement = document.createElement('div');
                    aElement.textContent = 'A';
                    aElement.title = 'Click for ascending alphabetical order';
                    aElement.style.display = 'block';
                    aElement.style.lineHeight = '1';
                    aElement.style.cursor = 'pointer';
                    aElement.style.padding = '1px 2px';
                    aElement.style.borderRadius = '1px';
                    aElement.style.fontFamily = 'Times New Roman, Times, serif';
                    aElement.style.fontSize = '10px';
                    aElement.onmouseover = function() {
                        aElement.style.backgroundColor = '#d4e7ff';
                        aElement.style.fontWeight = 'bold';
                    };
                    aElement.onmouseout = function() {
                        aElement.style.backgroundColor = '';
                        aElement.style.fontWeight = '';
                    };
                    aElement.onclick = function(e) {
                        e.stopPropagation();
                        // Click header 3 times to get ascending order
                        for (let i = 0; i < 3; i++) {
                            header.click();
                        }
                    };
                    
                    // Create Z button
                    const zElement = document.createElement('div');
                    zElement.textContent = 'Z';
                    zElement.title = 'Click for descending alphabetical order';
                    zElement.style.display = 'block';
                    zElement.style.lineHeight = '1';
                    zElement.style.cursor = 'pointer';
                    zElement.style.padding = '1px 2px';
                    zElement.style.borderRadius = '1px';
                    zElement.style.fontFamily = 'Times New Roman, Times, serif';
                    zElement.style.fontSize = '10px';
                    zElement.onmouseover = function() {
                        zElement.style.backgroundColor = '#d4e7ff';
                        zElement.style.fontWeight = 'bold';
                    };
                    zElement.onmouseout = function() {
                        zElement.style.backgroundColor = '';
                        zElement.style.fontWeight = '';
                    };
                    zElement.onclick = function(e) {
                        e.stopPropagation();
                        // Click header 2 times to get descending order
                        for (let i = 0; i < 2; i++) {
                            header.click();
                        }
                    };
                    
                    sortContainer.appendChild(aElement);
                    sortContainer.appendChild(zElement);
                    header.appendChild(sortContainer);
                    
                    // Create down-arrow icon
                    const sortIndicator = document.createElement('div');
                    sortIndicator.style.position = 'absolute';
                    sortIndicator.style.right = '8px';
                    sortIndicator.style.top = '50%';
                    sortIndicator.style.transform = 'translateY(-50%)';
                    sortIndicator.style.width = '15px';
                    sortIndicator.style.height = '15px';
                    sortIndicator.style.cursor = 'pointer';
                    sortIndicator.style.opacity = '0';
                    sortIndicator.style.transition = 'opacity 0.2s ease';
                    sortIndicator.style.zIndex = '1';
                    sortIndicator.title = 'Click to show sort options';
                    sortIndicator.className = 'sort-indicator';
                    
                    // Add SVG icon
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
                    
                    sortIndicator.onmouseover = function() {
                        sortIndicator.style.opacity = '1';
                        sortIndicator.style.backgroundColor = '#e6f3ff';
                        sortIndicator.style.borderRadius = '2px';
                        sortIndicator.querySelector('svg').style.fill = '#1f3263';
                    };
                    
                    sortIndicator.onmouseout = function() {
                        sortIndicator.style.opacity = '0';
                        sortIndicator.style.backgroundColor = '';
                        sortIndicator.querySelector('svg').style.fill = '#666';
                    };
                    
                    sortIndicator.onclick = function(e) {
                        e.stopPropagation();
                        const menu = document.getElementById('sorting-controls');
                        const rect = header.getBoundingClientRect();
                        
                        menu.style.position = 'fixed';
                        menu.style.left = (rect.right - 140) + 'px';
                        menu.style.top = (rect.bottom + 4) + 'px';
                        menu.style.display = 'block';
                        
                        // Trigger popup menu button
                        const btn = document.getElementById('popup-menu-btn');
                        if (btn) btn.click();
                    };
                    
                    header.appendChild(sortIndicator);
                    
                    // Show A/Z on header hover
                    header.onmouseover = function() {
                        sortContainer.style.opacity = '1';
                        sortIndicator.style.opacity = '1';
                    };
                    
                    header.onmouseout = function() {
                        sortContainer.style.opacity = '0';
                        sortIndicator.style.opacity = '0';
                    };
                }
                
                // Add to Updated Projects table headers
                const updatedColumns = ['Project Name', 'Likely Go-ahead', 'Country', 'Project Status'];
                const updatedHeaders = document.querySelectorAll('#latest-updates-table .dash-header');
                updatedHeaders.forEach(header => {
                    const colName = header.getAttribute('data-dash-column');
                    if (updatedColumns.includes(colName)) {
                        addSortUI(header);
                    }
                });
                
                // Add to All Projects table headers
                const allColumns = ['Project Name', 'Likely Go-ahead', 'Country'];
                const allHeaders = document.querySelectorAll('#projects-table .dash-header');
                allHeaders.forEach(header => {
                    const colName = header.getAttribute('data-dash-column');
                    if (allColumns.includes(colName)) {
                        addSortUI(header);
                    }
                });
                
                // Add click outside to close menu
                document.addEventListener('click', function(e) {
                    const menu = document.getElementById('sorting-controls');
                    if (menu && menu.style.display === 'block' && !menu.contains(e.target)) {
                        menu.style.display = 'none';
                    }
                });
                
            }, 500); // Increased timeout to ensure tables are loaded
            return '';
        }
        """,
        Output('dummy-output-clientside', 'children'),
        Input('latest-updates-table', 'columns'),
        prevent_initial_call=False
    )
