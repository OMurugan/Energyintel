"""
Price Scorecard for Key World Oil Grades View
Price scorecard table for key crude grades with three tabs:
- Costs to Refiners
- Port of Loading
- Price Formula
"""
import os
from dash import dcc, html, Input, Output, State, callback, dash_table
from dash.exceptions import PreventUpdate
import pandas as pd


def load_csv_data(csv_filename):
    """
    Load and parse CSV file with multi-level headers.
    
    CSV structure:
    - Row 1-2: Source/Copyright (skip)
    - Row 3: Destination/Region level (e.g., "Delivered to Rotterdam")
    - Row 4: Country level
    - Row 5: Crude type level
    - Row 6: Pricing basis level (e.g., "(f.o.b.)", "(Sidi Kerir)")
    - Row 7+: Data rows with Year and Month
    """
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'data',
        'price',
        csv_filename
    )
    
    if not os.path.exists(csv_path):
        return None, None, None
    
    # Read CSV with tab separator and no header initially
    raw = pd.read_csv(
        csv_path,
        encoding="utf-16",
        sep="\t",
        header=None,
        engine="python"
    )
    
    # Drop completely empty rows
    raw = raw.dropna(how="all")
    
    # Skip first two "Source / COPYRIGHT" rows
    raw = raw.iloc[2:].reset_index(drop=True)
    
    if len(raw) < 5:
        return None, None, None
    
    # Extract header levels
    # Row 0: Destination/Region
    # Row 1: Country
    # Row 2: Crude type
    # Row 3: Pricing basis
    destination_row = raw.iloc[0].fillna("").astype(str).str.strip().tolist()
    country_row = raw.iloc[1].fillna("").astype(str).str.strip().tolist()
    crude_row = raw.iloc[2].fillna("").astype(str).str.strip().tolist()
    pricing_row = raw.iloc[3].fillna("").astype(str).str.strip().tolist()
    
    # Data starts from row index 4
    df = raw.iloc[4:].reset_index(drop=True)
    
    # First two columns are Year and Month (no headers in header rows)
    if len(df.columns) < 2:
        return None, None, None
    
    # Build column structure for multi-level headers
    columns = []
    column_info = []
    
    # Year and Month columns (first two) - these don't have headers in the CSV
    columns.append({
        "name": ["", "Year"],
        "id": "Year",
        "type": "text"
    })
    columns.append({
        "name": ["", "Month"],
        "id": "Month",
        "type": "text"
    })
    
    # Process data columns (starting from index 2 in the raw data)
    # Note: header rows also start from index 2 (first two are empty for Year/Month)
    max_cols = min(len(df.columns), len(destination_row), len(country_row), len(crude_row), len(pricing_row))
    
    for idx in range(2, max_cols):
        # Get header values from the header rows (they start from index 2)
        dest = destination_row[idx].strip() if idx < len(destination_row) else ""
        country = country_row[idx].strip() if idx < len(country_row) else ""
        crude = crude_row[idx].strip() if idx < len(crude_row) else ""
        pricing = pricing_row[idx].strip() if idx < len(pricing_row) else ""
        
        # Skip empty columns (no country and no crude)
        if not country and not crude and not dest:
            continue
        
        # Create column ID
        col_id = f"col_{idx}"
        
        # Build multi-level header structure
        # dash_table supports 2-level headers: [level1, level2]
        # We need to organize: Destination -> Country / Crude / Pricing
        
        # Top level: Destination (if present and meaningful)
        level1 = ""
        if dest:
            dest_lower = dest.lower().strip()
            # Check if it's a meaningful destination/region
            if (dest_lower and 
                dest_lower not in ["", "source: energy intelligence", "copyright"] and
                ("delivered" in dest_lower or 
                 "port" in dest_lower or 
                 "africa" in dest_lower or 
                 "asia" in dest_lower or 
                 "europe" in dest_lower or 
                 "latin america" in dest_lower or 
                 "middle east" in dest_lower or 
                 "north america" in dest_lower or 
                 "fsu" in dest_lower or
                 "costs to refiners" in dest_lower or
                 "port of loading" in dest_lower or
                 "price formula" in dest_lower)):
                level1 = dest.strip()
        
        # Second level: Combine Country / Crude / Pricing
        level2_parts = []
        if country and country.strip():
            level2_parts.append(country.strip())
        if crude and crude.strip():
            level2_parts.append(crude.strip())
        if pricing and pricing.strip():
            level2_parts.append(pricing.strip())
        
        level2 = " / ".join(level2_parts) if level2_parts else ""
        
        # If no level1, use level2 as single level header
        if not level1:
            col_name = level2 if level2 else f"Column {idx}"
        else:
            col_name = [level1, level2] if level2 else [level1, ""]
        
        columns.append({
            "name": col_name,
            "id": col_id,
            "type": "numeric",
            "format": {"specifier": ".2f"}
        })
        
        # Add right-align styling for numeric columns in style_cell_conditional
        # This will be handled in the layout
        
        column_info.append({
            "id": col_id,
            "destination": dest,
            "country": country,
            "crude": crude,
            "pricing": pricing
        })
    
    # Rename data columns to match column IDs
    # First two are Year and Month, rest are col_2, col_3, etc.
    new_cols = ['Year', 'Month'] + [f'col_{i}' for i in range(2, len(df.columns))]
    df.columns = new_cols[:len(df.columns)]
    
    # Clean data: convert numeric columns
    for col in df.columns:
        if col not in ['Year', 'Month']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Remove rows where Year is empty or invalid
    df = df[df['Year'].astype(str).str.strip() != '']
    df = df[df['Year'].notna()]
    
    return df, columns, column_info


def create_layout():
    """Create the Price Scorecard layout with three tabs"""
    return html.Div([
        # Tabs
        dcc.Tabs(
            id="price-scorecard-tabs",
            value="costs-to-refiners",  # Default to Costs to Refiners
            persistence=False,  # Don't persist tab selection
            children=[
                dcc.Tab(
                    label="Costs to Refiners",
                    value="costs-to-refiners",
                    style={
                        "backgroundColor": "#f8f9fa",
                        "border": "2px solid #d35400",
                        "padding": "10px 20px",
                        "fontWeight": "bold",
                        "color": "#d35400",
                        "borderRadius": "5px 5px 0 0"
                    },
                    selected_style={
                        "backgroundColor": "#d35400",
                        "color": "white",
                        "border": "2px solid #d35400",
                        "padding": "10px 20px",
                        "fontWeight": "bold",
                        "borderRadius": "5px 5px 0 0"
                    }
                ),
                dcc.Tab(
                    label="Port of Loading",
                    value="port-of-loading",
                    style={
                        "backgroundColor": "#f8f9fa",
                        "border": "2px solid #d35400",
                        "padding": "10px 20px",
                        "fontWeight": "bold",
                        "color": "#d35400",
                        "borderRadius": "5px 5px 0 0"
                    },
                    selected_style={
                        "backgroundColor": "#d35400",
                        "color": "white",
                        "border": "2px solid #d35400",
                        "padding": "10px 20px",
                        "fontWeight": "bold",
                        "borderRadius": "5px 5px 0 0"
                    }
                ),
                dcc.Tab(
                    label="Price Formula",
                    value="price-formula",
                    style={
                        "backgroundColor": "#f8f9fa",
                        "border": "2px solid #d35400",
                        "padding": "10px 20px",
                        "fontWeight": "bold",
                        "color": "#d35400",
                        "borderRadius": "5px 5px 0 0"
                    },
                    selected_style={
                        "backgroundColor": "#d35400",
                        "color": "white",
                        "border": "2px solid #d35400",
                        "padding": "10px 20px",
                        "fontWeight": "bold",
                        "borderRadius": "5px 5px 0 0"
                    }
                ),
            ],
            style={"marginBottom": "10px", "display": "flex", "justifyContent": "center"}
        ),
        
        # Dynamic title (will be updated by callback) - below tabs, left aligned
        html.H3(
            id="price-scorecard-title",
            children="PIW SCORECARD -- COSTS TO REFINERS OF KEY FORMULA PRICED CRUDE OILS IN PRIMARY WORLD MARKETS ($/bbl)",
            style={
                'color': '#d35400',
                'textAlign': 'left',
                'fontSize': '18px',
                'fontWeight': 'bold',
                'textTransform': 'uppercase',
                'marginBottom': '15px',
                'marginTop': '10px',
                'paddingLeft': '10px'
            }
        ),
        
        # Store to track previous tab for detecting tab changes
        dcc.Store(id='price-scorecard-previous-tab', data=None),
        
        # Table container (initially hidden) with loading spinner
        dcc.Loading(
            id="price-scorecard-loading",
            type="circle",  # Loading spinner type
            color="#d35400",  # Match the orange-red theme
            children=[
                html.Div(
                    id="price-scorecard-table-container",
                    children=[
        dash_table.DataTable(
            id='price-scorecard-table',
            style_table={
                'overflowX': 'auto',
                'width': 'auto',
                'minWidth': '100%',
                'border': '1px solid #ddd'
            },
            style_cell={
                'textAlign': 'right',  # Default to right-align for numeric columns
                'padding': '2px 8px',
                'fontSize': '12px',
                'fontFamily': 'Lato',
                'whiteSpace': 'normal',
                'height': 'auto',
                'minWidth': '80px',
                'width': 'auto'
            },
            style_cell_conditional=[
                {
                    'if': {'column_id': 'Year'},
                    'textAlign': 'left',
                    'minWidth': '60px',
                    'width': '60px',
                    'fontSize': '12px'
                },
                {
                    'if': {'column_id': 'Month'},
                    'textAlign': 'left',
                    'minWidth': '80px',
                    'width': '80px',
                    'fontSize': '12px'
                },
                {
                    'if': {'column_id': ['Year', 'Month']},
                    'position': 'sticky',
                    'left': 0,
                    'zIndex': 1,
                    'backgroundColor': 'white'
                }
            ],
            style_data_conditional=[
                # Striped table rows - even rows (light gray)
                {
                    'if': {'row_index': 'even'},
                    'backgroundColor': '#f8f9fa'
                },
                # Striped table rows - odd rows (white)
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#ffffff'
                },
                # Year and Month columns - maintain white background for sticky columns
                {
                    'if': {'column_id': 'Year'},
                    'backgroundColor': 'white',
                    'fontWeight': 'bold',
                    'textAlign': 'left'
                },
                {
                    'if': {'column_id': 'Month'},
                    'backgroundColor': 'white',
                    'fontWeight': 'bold',
                    'textAlign': 'left'
                },
                {
                    'if': {'row_index': 'even', 'column_id': 'Year'},
                    'backgroundColor': '#f8f9fa'
                },
                {
                    'if': {'row_index': 'even', 'column_id': 'Month'},
                    'backgroundColor': '#f8f9fa'
                },
                # Add border at the end of each year group
                {
                    'if': {
                        'filter_query': '{_is_year_end} = True'
                    },
                    'borderBottom': '2px solid #ddd'
                },
                # Remove top border for Year column when it's empty (merged appearance)
                {
                    'if': {
                        'filter_query': '{Year} = ""',
                        'column_id': 'Year'
                    },
                    'borderTop': 'none',
                    'backgroundColor': 'white'
                },
                {
                    'if': {
                        'filter_query': '{Year} = ""',
                        'column_id': 'Year',
                        'row_index': 'even'
                    },
                    'backgroundColor': '#f8f9fa'
                },
                # Remove top border for all columns when Year is empty (merged appearance)
                {
                    'if': {
                        'filter_query': '{Year} = ""'
                    },
                    'borderTop': 'none'
                }
            ],
            style_header={
                'backgroundColor': 'white',
                'fontWeight': 'bold',
                'textAlign': 'center',
                'border': '1px solid #ddd',
                'color': '#1b365d',
                'fontSize': '14px',
                'height': '45px',
                'verticalAlign': 'middle',
            },
            style_header_conditional=[
                {
                    'if': {'column_id': 'Year'},
                    'position': 'sticky',
                    'left': 0,
                    'zIndex': 2,
                    'backgroundColor': 'white',
                    'fontSize': '14px',
                    'padding': '2px 8px',
                    'lineHeight': '14px'
                },
                {
                    'if': {'column_id': 'Month'},
                    'position': 'sticky',
                    'left': 0,
                    'zIndex': 2,
                    'backgroundColor': 'white',
                    'fontSize': '14px',
                    'padding': '2px 8px',
                    'lineHeight': '14px'
                }
            ],
            style_data={
                'border': '1px solid #ddd',
                'fontFamily': 'Lato',
                'fontSize': '12px',
                'fontStyle': 'normal',
                'fontWeight': 'bold',
                'textDecoration': 'none',
                'color': 'rgb(27, 54, 93)',
                'textAlign': 'left',
                'padding': '8px',
                'maxHeight': '60px'
            },
            merge_duplicate_headers=True,
            fixed_rows={'headers': True},
            fixed_columns={'headers': True, 'data': 2},
            sort_action='native',
            css=[{
                "selector": "th",
                "rule": "padding-right: 25px !important;"
            }]
        )
                    ],
                    style={'display': 'none'}  # Hidden until tab is selected
                )
            ]
        )
    ], className='tab-content')


def register_callbacks(dash_app, server):
    """Register all callbacks for Price Scorecard"""
    
    @callback(
        Output('price-scorecard-previous-tab', 'data'),
        Input('price-scorecard-tabs', 'value'),
        State('price-scorecard-previous-tab', 'data'),
        prevent_initial_call=False
    )
    def track_previous_tab(selected_tab, previous_tab):
        """Track previous tab value"""
        return selected_tab
    
    # Callback to immediately clear table data and hide title when tab changes
    @callback(
        [Output('price-scorecard-title', 'children', allow_duplicate=True),
         Output('price-scorecard-table-container', 'style', allow_duplicate=True),
         Output('price-scorecard-table', 'data', allow_duplicate=True),
         Output('price-scorecard-table', 'columns', allow_duplicate=True)],
        Input('price-scorecard-tabs', 'value'),
        State('price-scorecard-previous-tab', 'data'),
        prevent_initial_call=True
    )
    def clear_table_on_tab_change(selected_tab, previous_tab):
        """Clear table data and hide title immediately when tab changes"""
        # Only clear if tab actually changed
        if previous_tab is not None and previous_tab != selected_tab:
            # Return empty data and hide container to immediately hide old table and title
            return "", {'display': 'none'}, [], []
        raise PreventUpdate
    
    # Main callback to load data
    @callback(
        [Output('price-scorecard-title', 'children'),
         Output('price-scorecard-table-container', 'style'),
         Output('price-scorecard-table', 'data'),
         Output('price-scorecard-table', 'columns')],
        Input('price-scorecard-tabs', 'value'),
        prevent_initial_call=False
    )
    def update_price_scorecard(selected_tab):
        """Update price scorecard table based on selected tab"""
        if not selected_tab or selected_tab == "":
            return "PIW SCORECARD", {'display': 'none'}, [], []
        
        # Map tab values to CSV filenames and titles
        tab_info = {
            'costs-to-refiners': {
                'csv': 'Cost_to_Refiners.csv',
                'title': 'PIW SCORECARD -- COSTS TO REFINERS OF KEY FORMULA PRICED CRUDE OILS IN PRIMARY WORLD MARKETS ($/bbl)'
            },
            'port-of-loading': {
                'csv': 'Port_of_Loading.csv',
                'title': 'PIW SCORECARD -- CRUDE VALUES AT PORT OF LOADING ($/bbl)'
            },
            'price-formula': {
                'csv': 'Price_Formula.csv',
                'title': 'PIW SCORECARD - PRICE FORMULA ADJUSTMENT FACTORS ($/bbl)'
            }
        }
        
        tab_data = tab_info.get(selected_tab)
        if not tab_data:
            return "PIW SCORECARD", {'display': 'none'}, [], []
        
        csv_filename = tab_data['csv']
        title = tab_data['title']
        
        # Load CSV data
        df, columns, column_info = load_csv_data(csv_filename)
        
        if df is None or df.empty or not columns:
            # Show container but with empty data (loader will show)
            return title, {'display': 'block'}, [], []
        
        # Process Year column to show only once per year group (like Terminal, Country in russian_exports)
        # Also identify last row of each year group for border styling
        year_groups = []  # Track which rows are last in each year group
        
        if 'Year' in df.columns:
            prev_year = None
            
            for idx in df.index:
                current_year = df.loc[idx, 'Year']
                if pd.isna(current_year) or current_year is None:
                    current_year = ''
                else:
                    current_year = str(current_year).strip()
                
                # If current year matches previous, clear it (except for first occurrence)
                if current_year == prev_year and prev_year != '':
                    df.loc[idx, 'Year'] = ''
                else:
                    # Year changed - mark previous group's last row
                    if prev_year is not None and prev_year != '' and idx > 0:
                        year_groups.append(idx - 1)  # Previous row was last of previous year
                    prev_year = current_year
            
            # Mark the last row as end of last year group
            if len(df) > 0:
                year_groups.append(len(df) - 1)
        
        # Convert dataframe to records
        data = df.to_dict('records')
        
        # Add a flag to mark last row of each year group for border styling
        for idx, record in enumerate(data):
            record['_is_year_end'] = idx in year_groups
        
        # Clean data: replace NaN with empty strings and format numbers
        for record in data:
            for key, value in record.items():
                # Skip the internal flag used for styling
                if key == '_is_year_end':
                    continue
                if key in ['Year', 'Month']:
                    # Keep Year and Month as strings
                    if pd.isna(value):
                        record[key] = ''
                    else:
                        record[key] = str(value).strip()
                elif isinstance(value, (int, float)):
                    # Format numeric values
                    if pd.isna(value) or value != value or abs(value) == float('inf'):  # NaN or inf check
                        record[key] = ''
                    else:
                        # Format to 2 decimal places
                        record[key] = round(float(value), 2)
                else:
                    # Convert other types to string
                    if pd.isna(value):
                        record[key] = ''
                    else:
                        record[key] = str(value).strip()
        
        # Return with new data - container stays visible, loader will hide when this completes
        return title, {'display': 'block'}, data, columns
