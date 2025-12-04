
"""
Latest Updates View
Latest upstream project updates
"""
import os
import pandas as pd
from dash import dcc, html, Input, Output, callback, dash_table, State, no_update
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

# Pre-process dataframes
if df_projects_table is not None and not df_projects_table.empty:
    df_projects_table['Likely Go-ahead'] = df_projects_table['Likely Go-ahead'].astype(str).str.upper().replace({'TRUE': 'YES', 'FALSE': 'NO'})
    df_projects_table['Project Name'] = df_projects_table['Project Name'].fillna('N/A')
    df_projects_table['Country'] = df_projects_table['Country'].fillna('N/A')
    if 'Comments_link' in df_projects_table.columns and 'Comments' in df_projects_table.columns:
        df_projects_table['Click on the link below to go to the relevant article'] = df_projects_table.apply(
            lambda row: f"[{row['Comments']}]({row['Comments_link']})" if pd.notna(row['Comments_link']) and pd.notna(row['Comments']) else 'No link available',
            axis=1
        )
        df_projects_table = df_projects_table.drop(columns=['Comments_link', 'Source', 'Copyright', 'Title'], errors='ignore')

if df_latest_updates is not None and not df_latest_updates.empty:
    df_latest_updates['Likely Go-ahead'] = df_latest_updates['Likely Go-ahead'].astype(str).str.upper().replace({'TRUE': 'YES', 'FALSE': 'NO'})
    df_latest_updates['Project Name'] = df_latest_updates['Project Name'].fillna('N/A')
    df_latest_updates['Country'] = df_latest_updates['Country'].fillna('N/A')
    df_latest_updates['Project Status'] = df_latest_updates['Project Status'].fillna('N/A')
    df_latest_updates['First Oil Year'] = df_latest_updates['First Oil Year'].fillna('N/A')
    if 'Comments_link' in df_latest_updates.columns and 'Comments' in df_latest_updates.columns:
        df_latest_updates['Click on the link below to go to the relevant article'] = df_latest_updates.apply(
            lambda row: f"[{row['Comments']}]({row['Comments_link']})" if pd.notna(row['Comments_link']) and pd.notna(row['Comments']) else 'No link available',
            axis=1
        )
        df_latest_updates = df_latest_updates.drop(columns=['Comments_link', 'Source', 'Copyright', 'Title', 'first_day_of_week'], errors='ignore')

# Extract unique options for filters
country_options = sorted(df_projects_table['Country'].unique()) if df_projects_table is not None else []
status_options = sorted(df_projects_table['Project Status'].unique()) if df_projects_table is not None and 'Project Status' in df_projects_table.columns else []

def create_layout():
    """Create the exact layout matching the image"""
    return html.Div([
        # Main container matching the image
        html.Div([
            # TOP HEADER SECTION with blue background
            html.Div([
                html.Div([
                    html.H2(
                        "Latest Updates View",
                        style={
                            'color': 'white',
                            'margin': '0',
                            'padding': '0',
                            'fontSize': '24px',
                            'fontWeight': 'bold',
                            'fontFamily': 'Arial, sans-serif'
                        }
                    ),
                    html.P(
                        "Latest upstream project updates",
                        style={
                            'color': 'white',
                            'margin': '0',
                            'padding': '0',
                            'fontSize': '14px',
                            'fontFamily': 'Arial, sans-serif',
                            'opacity': '0.9'
                        }
                    )
                ], style={'flex': '1'}),
                
                # Search link - positioned to the right
                html.A(
                    "Click here to search for key articles",
                    href="https://www.energyintel.com/search?text=upstream%20projects",
                    target="_blank",
                    style={
                        'color': 'white',
                        'textDecoration': 'underline',
                        'fontSize': '14px',
                        'fontFamily': 'Arial, sans-serif',
                        'fontWeight': 'bold',
                        'alignSelf': 'flex-end',
                        'marginBottom': '5px'
                    }
                )
            ], style={
                'backgroundColor': '#1e3a8a',  # Dark blue from image
                'padding': '15px 20px',
                'display': 'flex',
                'justifyContent': 'space-between',
                'alignItems': 'center',
                'borderRadius': '4px 4px 0 0',
                'marginBottom': '20px'
            }),
            
            # MAIN CONTENT AREA with white background
            html.Div([
                # Header for "List of Updated Projects"
                html.Div([
                    html.H3(
                        "List of Updated Projects- Week of December 1, 2025",
                        style={
                            'color': '#1f3263',  # Dark blue text from image
                            'margin': '0 0 15px 0',
                            'fontSize': '16px',
                            'fontWeight': 'bold',
                            'fontFamily': 'Arial, sans-serif'
                        }
                    ),
                    
                    # Filter container - positioned to the right
                    html.Div([
                        html.Label(
                            "Likely To Go Ahead",
                            style={
                                'display': 'block',
                                'marginBottom': '8px',
                                'fontSize': '13px',
                                'fontWeight': 'bold',
                                'color': '#333',
                                'fontFamily': 'Arial, sans-serif'
                            }
                        ),
                        dcc.Checklist(
                            id='filter-go-ahead',
                            options=[
                                {'label': '(All)', 'value': 'ALL'},
                                {'label': 'N', 'value': 'NO'},
                                {'label': 'Uncertain', 'value': 'UNCERTAIN'},
                                {'label': 'Y', 'value': 'YES'}
                            ],
                            value=['ALL'],
                            inline=True,
                            style={
                                'fontSize': '12px',
                                'fontFamily': 'Arial, sans-serif'
                            },
                            labelStyle={
                                'marginRight': '15px',
                                'display': 'inline-block'
                            }
                        )
                    ], style={
                        'position': 'absolute',
                        'right': '20px',
                        'top': '0',
                        'backgroundColor': 'white',
                        'padding': '10px 15px',
                        'border': '1px solid #d1d5db',
                        'borderRadius': '4px',
                        'boxShadow': '0 1px 3px rgba(0,0,0,0.1)'
                    })
                ], style={
                    'position': 'relative',
                    'marginBottom': '20px',
                    'paddingRight': '300px'
                }),
                
                # FIRST TABLE: List of Updated Projects
                dash_table.DataTable(
                    id='latest-updates-table',
                    columns=[
                        {"name": "Project Name", "id": "Project Name", "presentation": "markdown"},
                        {"name": "Likely Go-ahead", "id": "Likely Go-ahead", "presentation": "markdown"},
                        {"name": "Country", "id": "Country", "presentation": "markdown"},
                        {"name": "Project Status", "id": "Project Status", "presentation": "markdown"},
                        {"name": "First Oil Year", "id": "First Oil Year", "presentation": "markdown"},
                        {"name": "Click on the link below to go to the relevant article", "id": "Click on the link below to go to the relevant article", "presentation": "markdown"}
                    ] if df_latest_updates is not None else [],
                    data=df_latest_updates.to_dict('records') if df_latest_updates is not None else [],
                    style_table={
                        'overflowX': 'auto',
                        'marginBottom': '30px',
                        'border': '1px solid #d1d5db',
                        'borderRadius': '4px',
                        'fontFamily': 'Arial, sans-serif'
                    },
                    style_cell={
                        'textAlign': 'left',
                        'padding': '8px 12px',
                        'fontSize': '12px',
                        'fontFamily': 'Arial, sans-serif',
                        'color': '#333',
                        'borderBottom': '1px solid #e5e7eb',
                        'backgroundColor': 'white'
                    },
                    style_header={
                        'backgroundColor': '#f3f4f6',
                        'fontWeight': 'bold',
                        'fontSize': '12px',
                        'fontFamily': 'Arial, sans-serif',
                        'color': '#1f3263',
                        'borderBottom': '2px solid #d1d5db',
                        'borderTop': 'none',
                        'padding': '10px 12px'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#f9fafb'
                        },
                        {
                            'if': {'state': 'selected'},
                            'backgroundColor': '#e5e7eb',
                            'border': 'none'
                        }
                    ],
                    sort_action="native",
                    filter_action="none",
                    page_action="native",
                    page_size=10,
                    markdown_options={"html": True},
                ),
                
                # Divider line
                html.Hr(style={
                    'border': 'none',
                    'height': '1px',
                    'backgroundColor': '#e5e7eb',
                    'margin': '20px 0 30px 0'
                }),
                
                # SECOND TABLE: All Projects
                html.H3(
                    "All Projects",
                    style={
                        'color': '#1f3263',
                        'margin': '0 0 15px 0',
                        'fontSize': '16px',
                        'fontWeight': 'bold',
                        'fontFamily': 'Arial, sans-serif'
                    }
                ),
                
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
                        'border': '1px solid #d1d5db',
                        'borderRadius': '4px',
                        'fontFamily': 'Arial, sans-serif'
                    },
                    style_cell={
                        'textAlign': 'left',
                        'padding': '8px 12px',
                        'fontSize': '12px',
                        'fontFamily': 'Arial, sans-serif',
                        'color': '#333',
                        'borderBottom': '1px solid #e5e7eb',
                        'backgroundColor': 'white'
                    },
                    style_header={
                        'backgroundColor': '#f3f4f6',
                        'fontWeight': 'bold',
                        'fontSize': '12px',
                        'fontFamily': 'Arial, sans-serif',
                        'color': '#1f3263',
                        'borderBottom': '2px solid #d1d5db',
                        'borderTop': 'none',
                        'padding': '10px 12px'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#f9fafb'
                        },
                        {
                            'if': {'state': 'selected'},
                            'backgroundColor': '#e5e7eb',
                            'border': 'none'
                        }
                    ],
                    sort_action="native",
                    filter_action="none",
                    page_action="native",
                    page_size=15,
                    markdown_options={"html": True},
                )
                
            ], style={
                'padding': '20px',
                'backgroundColor': 'white',
                'borderRadius': '0 0 4px 4px',
                'position': 'relative'
            })
            
        ], style={
            'maxWidth': '1200px',
            'margin': '20px auto',
            'fontFamily': 'Arial, sans-serif',
            'boxShadow': '0 4px 6px rgba(0,0,0,0.1)',
            'borderRadius': '4px',
            'overflow': 'hidden'
        })
    ], style={
        'backgroundColor': '#f3f4f6',
        'minHeight': '100vh',
        'padding': '20px',
        'margin': '0'
    })

def register_callbacks(dash_app, server):
    """Register all callbacks for the Upstream Projects dashboard"""
    
    @dash_app.callback(
        [Output('projects-table', 'data'),
         Output('latest-updates-table', 'data')],
        [Input('filter-go-ahead', 'value')]
    )
    def update_dashboard_data(selected_go_ahead):
        df_filtered_projects = df_projects_table.copy()
        df_filtered_updates = df_latest_updates.copy()

        # Apply 'Likely To Go Ahead' filter
        if selected_go_ahead and 'ALL' not in selected_go_ahead:
            mapped_go_ahead = [s.replace('Y', 'YES').replace('N', 'NO') for s in selected_go_ahead]
            df_filtered_projects = df_filtered_projects[df_filtered_projects['Likely Go-ahead'].isin(mapped_go_ahead)]
            df_filtered_updates = df_filtered_updates[df_filtered_updates['Likely Go-ahead'].isin(mapped_go_ahead)]

        return (
            df_filtered_projects.to_dict('records'),
            df_filtered_updates.to_dict('records')
        )
    
    # Callback to handle 'Select All' for 'Likely To Go Ahead'
    @dash_app.callback(
        Output('filter-go-ahead', 'value'),
        Input('filter-go-ahead', 'value')
    )
    def toggle_all_go_ahead(selected_values):
        all_options = ['N', 'Uncertain', 'Y']
        if selected_values and 'ALL' in selected_values and len(selected_values) > 1:
            return ['ALL']
        elif selected_values and 'ALL' not in selected_values and set(selected_values) == set(all_options):
            return ['ALL']
        elif not selected_values and 'ALL' not in (selected_values or []):
            return ['ALL']
        return no_update
