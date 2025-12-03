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
    # Row 4: Additional level (for Price Formula - 5th header)
    destination_row = raw.iloc[0].fillna("").astype(str).str.strip().tolist()
    country_row = raw.iloc[1].fillna("").astype(str).str.strip().tolist()
    crude_row = raw.iloc[2].fillna("").astype(str).str.strip().tolist()
    pricing_row = raw.iloc[3].fillna("").astype(str).str.strip().tolist()
    
    # Check if there's a 5th header row (for Price Formula)
    has_fifth_level = False
    additional_row = []
    # Price Formula CSV has 5 header levels
    if 'Price_Formula' in csv_filename or 'Price Formula' in csv_filename:
        if len(raw) > 4:
            # Row 4 is the 5th header level for Price Formula
            has_fifth_level = True
            additional_row = raw.iloc[4].fillna("").astype(str).str.strip().tolist()
            # Data starts from row index 5
            df = raw.iloc[5:].reset_index(drop=True)
        else:
            # Data starts from row index 4
            df = raw.iloc[4:].reset_index(drop=True)
    else:
        # Other CSVs have 4 header levels
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
        
        # Get additional level if exists
        additional = ""
        if has_fifth_level and idx < len(additional_row):
            additional = additional_row[idx].strip() if additional_row[idx] else ""
        
        column_info.append({
            "id": col_id,
            "destination": dest,
            "country": country,
            "crude": crude,
            "pricing": pricing,
            "additional": additional
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


def build_html_table(df, column_info):
    """Build HTML table with 4-level headers"""
    if df is None or df.empty or not column_info:
        return html.Div("No data available")
    
    # Extract header information from column_info in order
    headers_data = []
    has_additional_level = False
    for info in column_info:
        additional = info.get('additional', '').strip()
        if additional:
            has_additional_level = True
        headers_data.append({
            'id': info['id'],
            'destination': info.get('destination', '').strip(),
            'country': info.get('country', '').strip(),
            'crude': info.get('crude', '').strip(),
            'pricing': info.get('pricing', '').strip(),
            'additional': additional
        })
    
    # Determine number of header rows (4 or 5)
    num_header_rows = 5 if has_additional_level else 4
    
    # Build header rows by calculating colspans
    # Row 1: Destination/Region
    row1_cells = [
        html.Th("", rowSpan=num_header_rows, style={
            'position': 'sticky',
            'left': 0,
            'zIndex': 5,
            'backgroundColor': 'white',
            'border': '1px solid #333',
            'borderRight': 'none',
            'padding': '8px',
            'textAlign': 'center',
            'verticalAlign': 'middle',
            'fontWeight': 'bold',
            'fontSize': '15px',
            'fontFamily': '"Benton Sans Low-DPI", Arial, Helvetica, sans-serif'
        }),
        html.Th("", rowSpan=num_header_rows, style={
            'position': 'sticky',
            'zIndex': 5,
            'backgroundColor': 'white',
            'border': '1px solid #333',
            'borderLeft': 'none',
            'padding': '8px',
            'textAlign': 'center',
            'verticalAlign': 'middle',
            'fontWeight': 'bold',
            'fontSize': '13px',
            'fontFamily': '"Benton Sans Low-DPI", Arial, Helvetica, sans-serif'
        })
    ]
    
    # Calculate colspans for destination
    i = 0
    while i < len(headers_data):
        dest = headers_data[i]['destination']
        if dest:
            # Count consecutive columns with same destination
            count = 0
            j = i
            while j < len(headers_data) and headers_data[j]['destination'] == dest:
                count += 1
                j += 1
            row1_cells.append(html.Th(
                dest,
                colSpan=count,
                style={
                    'backgroundColor': 'white',
                    'border': '1px solid #333',
                    'padding': '8px',
                    'textAlign': 'center',
                    'verticalAlign': 'middle',
                    'fontWeight': 'bold',
                    'fontSize': '15px',
                    'color': '#fe5000',
                    'fontFamily': '"Benton Sans Low-DPI", Arial, Helvetica, sans-serif'
                }
            ))
            i = j
        else:
            i += 1
    
    # Row 2: Country
    row2_cells = []
    i = 0
    while i < len(headers_data):
        country = headers_data[i]['country']
        if country:
            count = 0
            j = i
            while j < len(headers_data) and headers_data[j]['country'] == country:
                count += 1
                j += 1
            row2_cells.append(html.Th(
                country,
                colSpan=count,
                style={
                    'backgroundColor': 'white',
                    'border': '1px solid #333',
                    'padding': '8px',
                    'textAlign': 'center',
                    'verticalAlign': 'middle',
                    'fontWeight': 'bold',
                    'fontSize': '13px',
                    'color': '#1b365d',
                    'fontFamily': '"Benton Sans Low-DPI", Arial, Helvetica, sans-serif'
                }
            ))
            i = j
        else:
            i += 1
    
    # Row 3: Crude type
    row3_cells = []
    i = 0
    while i < len(headers_data):
        crude = headers_data[i]['crude']
        if crude:
            count = 0
            j = i
            while j < len(headers_data) and headers_data[j]['crude'] == crude:
                count += 1
                j += 1
            row3_cells.append(html.Th(
                crude,
                colSpan=count,
                style={
                    'backgroundColor': 'white',
                    'border': '1px solid #333',
                    'padding': '8px',
                    'textAlign': 'center',
                    'verticalAlign': 'middle',
                    'fontWeight': 'bold',
                    'fontSize': '13px',
                    'color': '#1b365d',
                    'fontFamily': '"Benton Sans Low-DPI", Arial, Helvetica, sans-serif'
                }
            ))
            i = j
        else:
            i += 1
    
    # Row 4: Pricing basis
    row4_cells = []
    for h in headers_data:
        row4_cells.append(html.Th(
            h['pricing'] if h['pricing'] else '',
            style={
                'backgroundColor': 'white',
                'border': '1px solid #333',
                'padding': '8px',
                'textAlign': 'center',
                'verticalAlign': 'middle',
                'fontWeight': 'bold',
                'fontSize': '13px',
                'color': '#1b365d',
                'fontFamily': '"Benton Sans Low-DPI", Arial, Helvetica, sans-serif'
            }
        ))
    
    # Row 5: Additional level (only for Price Formula with 5 headers)
    row5_cells = []
    if has_additional_level:
        for h in headers_data:
            row5_cells.append(html.Th(
                h['additional'] if h['additional'] else '',
                style={
                    'backgroundColor': 'white',
                    'border': '1px solid #333',
                    'padding': '8px',
                    'textAlign': 'center',
                    'verticalAlign': 'middle',
                    'fontWeight': 'bold',
                    'fontSize': '13px',
                    'color': '#1b365d',
                    'fontFamily': '"Benton Sans Low-DPI", Arial, Helvetica, sans-serif'
                }
            ))
    
    header_rows = [
        html.Tr(row1_cells),
        html.Tr(row2_cells),
        html.Tr(row3_cells),
        html.Tr(row4_cells)
    ]
    
    # Add row 5 if it exists
    if has_additional_level:
        header_rows.append(html.Tr(row5_cells))
    
    # Build data rows
    data_rows = []
    prev_year = None
    year_end_indices = []  # Track last row of each year group
    
    # First pass: identify year boundaries
    for idx, row in df.iterrows():
        current_year = str(row['Year']).strip() if pd.notna(row['Year']) else ''
        if current_year and current_year != prev_year and prev_year is not None:
            # Previous row was the last of previous year
            year_end_indices.append(idx - 1)
        prev_year = current_year if current_year else prev_year
    
    # Mark the last row as end of last year group
    if len(df) > 0:
        year_end_indices.append(len(df) - 1)
    
    prev_year = None
    
    for idx, row in df.iterrows():
        row_cells = []
        is_year_end = idx in year_end_indices
        
        # Year column
        year_val = str(row['Year']).strip() if pd.notna(row['Year']) else ''
        # Remove decimal part if present (e.g., "2025.0" -> "2025")
        if year_val:
            try:
                year_val = str(int(float(year_val)))
            except (ValueError, TypeError):
                pass  # Keep original value if conversion fails
        if year_val == prev_year:
            year_val = ''
        else:
            prev_year = year_val
        
        year_style = {
            'position': 'sticky',
            'left': 0,
            'zIndex': 3,
            'backgroundColor': '#ffffff' if idx % 2 == 0 else '#f8f9fa',
            'padding': '8px',
            'textAlign': 'left',
            'fontWeight': 'bold',
            'fontSize': '12px',
            'color': '#1b365d',
            'borderLeft': '1px solid #ddd',
            'borderRight': '1px solid #ddd',
            'fontFamily': '"Benton Sans Low-DPI", Arial, Helvetica, sans-serif'
        }
        # Only show top border for first row of year, bottom border for last row of year
        if year_val != '':
            year_style['borderTop'] = '1px solid #ddd'
        else:
            year_style['borderTop'] = 'none'
        
        if is_year_end:
            year_style['borderBottom'] = '2px solid #ddd'
        else:
            year_style['borderBottom'] = 'none'
        
        row_cells.append(html.Td(year_val, style=year_style))
        
        # Month column
        month_val = str(row['Month']).strip() if pd.notna(row['Month']) else ''
        month_style = {
            'position': 'sticky',
            'zIndex': 3,
            'backgroundColor': '#ffffff' if idx % 2 == 0 else '#f8f9fa',
            'padding': '8px',
            'textAlign': 'left',
            'fontWeight': 'bold',
            'fontSize': '12px',
            'color': '#1b365d',
            'borderRight': '1px solid #ddd',
            'fontFamily': '"Benton Sans Low-DPI", Arial, Helvetica, sans-serif'
        }
        if year_val != '':
            month_style['borderTop'] = '1px solid #ddd'
        else:
            month_style['borderTop'] = 'none'
        
        if is_year_end:
            month_style['borderBottom'] = '2px solid #ddd'
        else:
            month_style['borderBottom'] = 'none'
        
        row_cells.append(html.Td(month_val, style=month_style))
        
        # Data columns
        for h in headers_data:
            col_id = h['id']
            if col_id in df.columns:
                value = row[col_id]
                if pd.isna(value) or value == '':
                    display_value = ''
                elif isinstance(value, (int, float)):
                    display_value = f"{float(value):.2f}"
                else:
                    display_value = str(value)
            else:
                display_value = ''
            
            data_style = {
                'padding': '8px',
                'textAlign': 'right',
                'fontSize': '12px',
                'fontWeight': 'bold',
                'color': '#1b365d',
                'backgroundColor': '#ffffff' if idx % 2 == 0 else '#f8f9fa',
                'borderRight': '1px solid #ddd',
                'fontFamily': '"Benton Sans Low-DPI", Arial, Helvetica, sans-serif'
            }
            if year_val != '':
                data_style['borderTop'] = '1px solid #ddd'
            else:
                data_style['borderTop'] = 'none'
            
            if is_year_end:
                data_style['borderBottom'] = '2px solid #ddd'
            else:
                data_style['borderBottom'] = 'none'
            
            row_cells.append(html.Td(display_value, style=data_style))
        
        data_rows.append(html.Tr(row_cells))
    
    # Build complete table
    table = html.Table([
        html.Thead(header_rows),
        html.Tbody(data_rows)
    ], style={
        'width': '100%',
        'borderCollapse': 'collapse',
        'border': '1px solid #ddd',
        'fontFamily': '"Benton Sans Low-DPI", Arial, Helvetica, sans-serif',
        'tableLayout': 'auto'
    })
    
    return html.Div([
        html.Div(table, style={
            'overflowX': 'auto',
            'overflowY': 'auto',
            'maxHeight': '600px',
            'width': '100%'
        })
    ], style={'width': '100%'})


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
                        "backgroundColor": "white",
                        "border": "3px solid rgb(254, 80, 0)",
                        "padding": "10px 20px",
                        "fontWeight": "bold",
                        "fontSize": "19px",
                        "color": "rgb(78, 121, 167)",
                        "borderRadius": "5px 5px 0 0",
                        "marginRight": "10px"
                    },
                    selected_style={
                        "backgroundColor": "#f8f9fa",
                        "color": "rgb(78, 121, 167)",
                        "fontSize": "19px",
                        "border": "3px solid rgb(254, 80, 0)",
                        "padding": "10px 20px",
                        "fontWeight": "bold",
                        "borderRadius": "5px 5px 0 0",
                        "marginRight": "10px"
                    }
                ),
                dcc.Tab(
                    label="Port of Loading",
                    value="port-of-loading",
                    style={
                        "backgroundColor": "white",
                        "border": "3px solid rgb(254, 80, 0)",
                        "padding": "10px 20px",
                        "fontWeight": "bold",
                        "color": "rgb(78, 121, 167)",
                        "fontSize": "19px",
                        "borderRadius": "5px 5px 0 0",
                        "marginRight": "10px"
                    },
                    selected_style={
                        "backgroundColor": "#f8f9fa",
                        "color": "rgb(78, 121, 167)",
                        "fontSize": "19px",
                        "border": "3px solid rgb(254, 80, 0)",
                        "padding": "10px 20px",
                        "fontWeight": "bold",
                        "borderRadius": "5px 5px 0 0",
                        "marginRight": "10px"
                    }
                ),
                dcc.Tab(
                    label="Price Formula",
                    value="price-formula",
                    style={
                        "backgroundColor": "white",
                        "border": "3px solid rgb(254, 80, 0)",
                        "padding": "10px 20px",
                        "fontWeight": "bold",
                        "color": "rgb(78, 121, 167)",
                        "fontSize": "19px",
                        "borderRadius": "5px 5px 0 0"
                    },
                    selected_style={
                        "backgroundColor": "#f8f9fa",
                        "color": "rgb(78, 121, 167)",
                        "fontSize": "19px",
                        "border": "3px solid rgb(254, 80, 0)",
                        "padding": "10px 20px",
                        "fontWeight": "bold",
                        "borderRadius": "5px 5px 0 0"
                    }
                ),
            ],
            style={"marginBottom": "10px", "display": "flex", "justifyContent": "center", "backgroundColor": "white"}
        ),
        
        # Dynamic title (will be updated by callback) - below tabs, left aligned
        html.H3(
            id="price-scorecard-title",
            children="PIW SCORECARD -- COSTS TO REFINERS OF KEY FORMULA PRICED CRUDE OILS IN PRIMARY WORLD MARKETS ($/bbl)",
            style={
                'color': 'rgb(254, 80, 0)',
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
            color="rgb(254, 80, 0)",  # Match the orange-red theme
            children=[
                html.Div(
                    id="price-scorecard-table-container",
                    children=html.Div(id='price-scorecard-table'),
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
         Output('price-scorecard-table', 'children', allow_duplicate=True)],
        Input('price-scorecard-tabs', 'value'),
        State('price-scorecard-previous-tab', 'data'),
        prevent_initial_call=True
    )
    def clear_table_on_tab_change(selected_tab, previous_tab):
        """Clear table data and hide title immediately when tab changes"""
        # Only clear if tab actually changed
        if previous_tab is not None and previous_tab != selected_tab:
            # Return empty data and hide container to immediately hide old table and title
            return "", {'display': 'none'}, html.Div()
        raise PreventUpdate
    
    # Main callback to load data
    @callback(
        [Output('price-scorecard-title', 'children'),
         Output('price-scorecard-table-container', 'style'),
         Output('price-scorecard-table', 'children')],
        Input('price-scorecard-tabs', 'value'),
        prevent_initial_call=False
    )
    def update_price_scorecard(selected_tab):
        """Update price scorecard table based on selected tab"""
        if not selected_tab or selected_tab == "":
            return "PIW SCORECARD", {'display': 'none'}, html.Div()
        
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
            return "PIW SCORECARD", {'display': 'none'}, html.Div()
        
        csv_filename = tab_data['csv']
        title = tab_data['title']
        
        # Load CSV data
        df, columns, column_info = load_csv_data(csv_filename)
        
        if df is None or df.empty or not column_info:
            # Show container but with empty data
            return title, {'display': 'block'}, html.Div("No data available")
        
        # Process Year column to show only once per year group
        if 'Year' in df.columns:
            prev_year = None
            for idx in df.index:
                current_year = df.loc[idx, 'Year']
                if pd.isna(current_year) or current_year is None:
                    current_year = ''
                else:
                    # Remove decimal part if present (e.g., "2025.0" -> "2025")
                    try:
                        current_year = str(int(float(current_year)))
                    except (ValueError, TypeError):
                        current_year = str(current_year).strip()
                
                # If current year matches previous, clear it (except for first occurrence)
                if current_year == prev_year and prev_year != '':
                    df.loc[idx, 'Year'] = ''
                else:
                    prev_year = current_year
        
        # Build HTML table
        table_html = build_html_table(df, column_info)
        
        # Return with new table - container stays visible
        return title, {'display': 'block'}, table_html
