"""
Latest Updates View
Latest upstream project updates
"""
import pandas as pd
from dash import dcc, html, Input, Output, callback, dash_table, State, no_update, callback_context
import re
from core.data_helpers import execute_query

def create_link_text(comment, link_url, default_label="Article"):
    link_str = str(link_url).strip() if pd.notna(link_url) else ""
    comment_str = str(comment).strip() if pd.notna(comment) else ""
    
    if link_str:
        label = comment_str or default_label
        return f"[{label}]({link_str})"
    if comment_str:
        return comment_str
    return "No link available"


def _normalize_likely_goahead(series: pd.Series) -> pd.Series:
    """Normalize Likely Go-ahead values to Yes/No/Uncertain for consistent filtering."""
    normalized = series.astype(str).str.upper().replace({
        "TRUE": "Y",
        "FALSE": "N",
        "YES": "Y",
        "NO": "N",
        "Y": "Y",
        "N": "N",
        "UNCERTAIN": "UNCERTAIN",
        "NONE": "",
        "NAN": "",
        "NULL": "",
        "N/A": "",
        "NA": "",
        "": ""
    })
    return normalized


def load_latest_updates_data():
    """Load 'List of Updated Projects' table directly from the database."""
    query = """
        WITH latest_update AS (
            SELECT MAX(date_modified) AS max_date
            FROM fact_upstream_project_tracker
        ),
        week_start AS (
            SELECT date_trunc('week', max_date)::date AS wk_start
            FROM latest_update
        )

        SELECT
            a.project_name,
            a.likely_goahead,
            c.country_long_name AS country,
            a.project_status,
            yr.year AS first_oil_year,
            a.external_comment_ei_link AS article_link,
            a.external_comments AS comments,
            a.date_modified
        FROM fact_upstream_project_tracker a
        LEFT JOIN dim_country c 
            ON a.country_id = c.dim_country_id
        LEFT JOIN (
            SELECT 
                project_id,
                MIN(EXTRACT(YEAR FROM period)) AS year
            FROM fact_upstream_tracker_prod_estimates_incremental
            WHERE value IS NOT NULL
            GROUP BY project_id
        ) yr ON yr.project_id = a.project_id
        JOIN week_start w
            ON a.date_modified >= w.wk_start
        WHERE a.include = TRUE
        AND a.external_comment_ei_link IS NOT NULL
        ORDER BY a.project_name;
    """
    try:
        results = execute_query(query)
    except Exception as e:
        return pd.DataFrame()
    
    df = pd.DataFrame(results) if results else pd.DataFrame()
    if df.empty:
        return df
    
    # Normalize column names to lowercase for consistent renaming
    df.columns = df.columns.str.strip().str.lower()
    column_mapping = {
        "project_name": "Project Name",
        "likely_goahead": "Likely Go-ahead",
        "country": "Country",
        "project_status": "Project Status",
        "first_oil_year": "First Oil",
        "article_link": "Article Link",
        "comments": "Comments",
        "date_modified": "Date Modified",
    }
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    
    if "Likely Go-ahead" in df.columns:
        df["Likely Go-ahead"] = _normalize_likely_goahead(df["Likely Go-ahead"])
        df["Likely Go-ahead"] = df["Likely Go-ahead"].replace({
            "Y": "Yes",
            "N": "No",
            "UNCERTAIN": "Uncertain"
        })
    
    for col in ["Project Name", "Country", "Project Status"]:
        if col in df.columns:
            df[col] = df[col].fillna("N/A")
    
    if "First Oil" in df.columns:
        df["First Oil"] = pd.to_numeric(df["First Oil"], errors="coerce")
        df["First Oil"] = df["First Oil"].apply(lambda v: str(int(v)) if pd.notna(v) else "")
    else:
        df["First Oil"] = ""
    
    df["Click on the link below to go to the relevant article"] = df.apply(
        lambda row: create_link_text(
            row.get("Comments") or row.get("Project Name"),
            row.get("Article Link"),
            default_label=row.get("Project Name") or "Article",
        ),
        axis=1,
    )
    
    desired_cols = [
        "Project Name",
        "Likely Go-ahead",
        "Country",
        "Project Status",
        "First Oil",
        "Click on the link below to go to the relevant article",
    ]
    df = df[[c for c in desired_cols if c in df.columns]]
    return df


def load_all_projects_data():
    """Load 'All Projects' table directly from the database."""
    query = """
    SELECT
        a.project_name,
        a.likely_goahead,
        c.country_long_name AS country,
        a.external_comment_ei_link AS article_link,
        a.external_comments AS comments
    FROM fact_upstream_project_tracker a
    LEFT JOIN dim_country c 
        ON a.country_id = c.dim_country_id
    WHERE a.include = TRUE
    AND a.external_comment_ei_link IS NOT NULL
    ORDER BY a.project_name;
    """
    try:
        results = execute_query(query)
    except Exception as e:
        print(f"❌ Error loading all projects from DB: {e}")
        return pd.DataFrame()
    
    df = pd.DataFrame(results) if results else pd.DataFrame()
    if df.empty:
        return df
    
    # Normalize column names to lowercase for consistent renaming
    df.columns = df.columns.str.strip().str.lower()
    column_mapping = {
        "project_name": "Project Name",
        "likely_goahead": "Likely Go-ahead",
        "country": "Country",
        "article_link": "Article Link",
        "comments": "Comments",
    }
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    
    if "Likely Go-ahead" in df.columns:
        df["Likely Go-ahead"] = _normalize_likely_goahead(df["Likely Go-ahead"])
        df["Likely Go-ahead"] = df["Likely Go-ahead"].replace({
            "Y": "Yes",
            "N": "No",
            "UNCERTAIN": "Uncertain"
        })
    
    for col in ["Project Name", "Country"]:
        if col in df.columns:
            df[col] = df[col].fillna("N/A")
    
    df["Click on the link below to go to the relevant article"] = df.apply(
        lambda row: create_link_text(
            row.get("Comments") or row.get("Project Name"),
            row.get("Article Link"),
            default_label=row.get("Project Name") or "Article",
        ),
        axis=1,
    )
    
    desired_cols = [
        "Project Name",
        "Likely Go-ahead",
        "Country",
        "Click on the link below to go to the relevant article",
    ]
    df = df[[c for c in desired_cols if c in df.columns]]
    return df


# Load dataframes globally once from the database
df_latest_updates = load_latest_updates_data()
df_projects_table = load_all_projects_data()


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
                        id='updated-projects-title',
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
                            {'label': '(All)', 'value': 'All'},
                            {'label': '', 'value': ''},
                            {'label': 'N', 'value': 'N'},
                            {'label': 'Uncertain', 'value': 'Uncertain'},
                            {'label': 'Y', 'value': 'Y'},
                        ],
                        value=['Y'],  # Default: Y is checked
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
                    ),
                    dcc.Store(id='filter-go-ahead-previous', data=['Y'])
                ])
            ]),
            
            # Container for Updated Projects table that can be hidden
            html.Div(id='updated-projects-container', children=[
                dcc.Loading(
                    type='default',
                    color='#ff6600',
                    children=dash_table.DataTable(
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
                    )
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
                dcc.Loading(
                    type='default',
                    color='#ff6600',
                    children=dash_table.DataTable(
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
                        filter_action="none",
                        page_action="none",
                        markdown_options={"html": True, "link_target": "_blank"},
                        editable=False,
                    )
                ),
            ])
        ])
    ])


def register_callbacks(dash_app, server):
    """Register all callbacks for the Upstream Projects dashboard"""
    
    @dash_app.callback(
        [
            Output('projects-table', 'data'),
            Output('latest-updates-table', 'data'),
            Output('updated-projects-container', 'style'),
            Output('all-projects-table-container', 'style'),
            Output('filter-go-ahead', 'value'),
            Output('filter-go-ahead-previous', 'data'),
        ],
        Input('filter-go-ahead', 'value'),
        State('filter-go-ahead-previous', 'data'),
        prevent_initial_call=False
    )
    def update_dashboard_data(selected_values, previous_values):
        if selected_values is None:
            current_values = []
        else:
            if not isinstance(selected_values, list):
                current_values = [selected_values] if selected_values else []
            else:
                current_values = selected_values
        
        # Define all options
        all_options = ['All', 'Y', 'N', 'Uncertain', '']
        individual_options = ['Y', 'N', 'Uncertain', '']
        
        if previous_values is None:
            previous_values = []
        if not isinstance(previous_values, list):
            previous_values = [previous_values] if previous_values else []
        
        # Get current state
        was_all_selected = 'All' in previous_values
        is_all_selected = 'All' in current_values
        prev_individual = [opt for opt in previous_values if opt in individual_options]
        curr_individual = [opt for opt in current_values if opt in individual_options]
        
        # Determine the new final values
        new_final_values = current_values.copy()
        
        # 1. If "All" was just checked
        if not was_all_selected and is_all_selected:
            # Select all options
            new_final_values = all_options
        
        # 2. If "All" was just unchecked
        elif was_all_selected and not is_all_selected:
            # Clear all selections
            new_final_values = []
        
        # 3. If "All" was and still is selected, but individual checkboxes changed
        elif was_all_selected and is_all_selected and prev_individual != curr_individual:
            # If user unchecked some individual boxes, remove "All"
            if len(curr_individual) < len(prev_individual):
                new_final_values = curr_individual
            # If all individual boxes are checked again, keep "All"
            elif len(curr_individual) == len(individual_options):
                new_final_values = all_options
        
        # 4. If user manually checks all individual boxes
        elif not is_all_selected and len(curr_individual) == len(individual_options):
            new_final_values = all_options
        
        # Determine if we should show all data
        show_all_data = 'All' in new_final_values
        
        # Update data based on selection
        if show_all_data:
            # Show all data
            data_projects = df_projects_table.to_dict('records')
            data_updates = df_latest_updates.to_dict('records')
            updated_container_style = {'display': 'block'}
            all_container_style = {'display': 'block'}
        elif not new_final_values:
            # No selections
            data_projects = []
            data_updates = []
            updated_container_style = {'display': 'none'}
            all_container_style = {'display': 'none'}
        else:
            # Filter based on individual selections
            def filter_df(df):
                if df is None or df.empty:
                    return pd.DataFrame()
                
                # Map UI values to data values
                value_mapping = {
                    'Y': 'Yes',
                    'N': 'No',
                    'Uncertain': 'Uncertain',
                    '': ''
                }
                
                # Create mask
                mask = pd.Series(False, index=df.index)
                for value in new_final_values:
                    if value in value_mapping:
                        data_value = value_mapping[value]
                        mask |= (df['Likely Go-ahead'] == data_value)
                
                return df[mask].copy()
            
            df_filtered_projects = filter_df(df_projects_table)
            df_filtered_updates = filter_df(df_latest_updates)
            
            data_projects = df_filtered_projects.to_dict('records')
            data_updates = df_filtered_updates.to_dict('records')
            
            # Show/hide containers based on data
            if not data_projects:
                all_container_style = {'display': 'none'}
            else:
                all_container_style = {'display': 'block'}
            
            if not data_updates:
                updated_container_style = {'display': 'none'}
            else:
                updated_container_style = {'display': 'block'}
        
        # Update the previous values store
        previous_values_to_store = new_final_values.copy()
        
        return (
            data_projects,
            data_updates,
            updated_container_style,
            all_container_style,
            new_final_values,              # Current checkbox values
            previous_values_to_store       # Store for next comparison
        )

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