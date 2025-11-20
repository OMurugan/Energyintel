"""
Crude Carbon Intensity View
Carbon intensity metrics for different crude types
"""
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os
from app import db
from app.models import Crude, Country
from app import create_dash_app



def create_layout():
    """Create the Crude Carbon Intensity layout"""
    # Get unique countries from CSV for dropdown
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'Carbon Intensity.csv')
    countries = ['(All)']
    
    try:
        # Try different encodings for CSV
        df = None
        for encoding in ['utf-16', 'latin-1', 'iso-8859-1', 'cp1252']:
            try:
                df = pd.read_csv(csv_path, skiprows=1, header=0, sep='\t', encoding=encoding)
                if df.shape[1] > 2:
                    break
            except Exception:
                continue
        
        if df is not None and df.shape[1] >= 2:
            country_col = df.columns[1]
            if country_col in df.columns:
                unique_countries = df[country_col].dropna().unique().tolist()
                countries.extend(sorted([str(c).strip() for c in unique_countries if str(c).strip()]))
    except Exception:
        pass
    
    return html.Div([
        html.H3("Upstream Crude Oil Production by Carbon Intensity", style={'marginBottom': '20px'}),
        html.Div([
            html.Div([
                html.Label("Year:", style={'fontWeight': '500', 'marginBottom': '8px'}),
                dcc.Dropdown(
                    id='carbon-year-select',
                    options=[{'label': str(year), 'value': year} for year in [2022, 2021, 2020, 2019, 2018]],
                    value=2022,
                    clearable=False,
                    style={'marginBottom': '10px', 'width': '150px'}
                ),
                dcc.Checklist(
                    id='carbon-show-history',
                    options=[{'label': 'Show history', 'value': 'show'}],
                    value=[],
                    style={'marginBottom': '10px'}
                ),
                html.Label("Carbon Intensity:", style={'fontWeight': '500', 'marginBottom': '8px', 'marginTop': '10px'}),
                dcc.Checklist(
                    id='carbon-intensity-filter',
                    options=[
                        {'label': 'Very High', 'value': 'Very High'},
                        {'label': 'High', 'value': 'High'},
                        {'label': 'Medium', 'value': 'Medium'},
                        {'label': 'Low', 'value': 'Low'},
                        {'label': 'Very Low', 'value': 'Very Low'}
                    ],
                    value=['Very High', 'High', 'Medium', 'Low', 'Very Low'],
                    style={'marginBottom': '10px'}
                ),
                html.Label("Country:", style={'fontWeight': '500', 'marginBottom': '8px', 'marginTop': '10px'}),
                html.Div([
                    html.Button([
                        html.Span("▼", id='country-dropdown-icon', style={
                            'fontSize': '10px',
                            'marginRight': '5px',
                            'display': 'inline-block',
                            'transition': 'transform 0.3s',
                            'userSelect': 'none'
                        }),
                        html.Span("(All)", style={'fontSize': '12px', 'verticalAlign': 'middle'})
                    ], id='country-dropdown-header', n_clicks=0, style={
                        'cursor': 'pointer',
                        'padding': '5px 8px',
                        'border': '1px solid #ddd',
                        'borderRadius': '4px',
                        'backgroundColor': '#f8f9fa',
                        'marginBottom': '5px',
                        'width': '100%',
                        'textAlign': 'left',
                        'fontSize': '12px',
                        'color': '#2c3e50'
                    }),
                    html.Div([
                        dcc.Checklist(
                            id='carbon-country-select',
                            options=[{'label': c, 'value': c} for c in countries],  # Includes "(All)" as first option
                            value=countries,  # All countries including "(All)" by default
                            style={
                                'maxHeight': '300px',
                                'overflowY': 'auto',
                                'border': '1px solid #ddd',
                                'padding': '10px',
                                'borderRadius': '4px',
                                'backgroundColor': 'white'
                            }
                        ),
                        dcc.Store(id='country-selection-store', data=countries)  # Store previous selection
                    ], id='country-checklist-container', style={'marginBottom': '10px', 'display': 'block'})
                ]),
                html.Label("Crude list:", style={'fontWeight': '500', 'marginBottom': '8px', 'marginTop': '10px'}),
                dcc.Input(
                    id='carbon-crude-filter',
                    type='text',
                    placeholder='Filter crudes...',
                    style={'width': '100%', 'marginBottom': '10px'}
                )
            ], style={'width': '250px', 'float': 'right', 'padding': '20px', 'background': '#f9f9f9', 'borderRadius': '5px'}),
            html.Div([
                dcc.Graph(id='crude-carbon-chart', style={'height': '700px'})
            ], style={'marginRight': '280px'})
        ], style={'position': 'relative'})
    ], className='tab-content')


def create_carbon_treemap_figure(df=None, country_filter=None, crude_filter=None, intensity_filter=None):
    """Create the carbon intensity treemap figure - can be used by API or callbacks"""
    if df is None:
        df = load_carbon_data()
    
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No carbon intensity data available.",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(height=700, plot_bgcolor='white', paper_bgcolor='white')
        return fig
    
    # Apply filters
    print(f"DEBUG create_carbon_treemap_figure: Before filtering - {len(df)} rows")
    print(f"DEBUG: country_filter={country_filter}, crude_filter={crude_filter}, intensity_filter={intensity_filter}")
    
    # Handle country filter - can be list or single value
    if country_filter:
        if isinstance(country_filter, list):
            # If list contains '(All)' or is empty, show all
            if '(All)' in country_filter or len(country_filter) == 0:
                print("DEBUG: Country filter contains '(All)' or is empty, not filtering by country")
                pass  # Don't filter
            else:
                print(f"DEBUG: Filtering by countries: {country_filter}")
                df = df[df['Country'].isin(country_filter)]
                print(f"DEBUG: After country filter - {len(df)} rows")
        elif country_filter != '(All)':
            print(f"DEBUG: Filtering by single country: {country_filter}")
            df = df[df['Country'] == country_filter]
            print(f"DEBUG: After country filter - {len(df)} rows")
    else:
        print("DEBUG: No country filter, showing all countries")
    
    if crude_filter:
        print(f"DEBUG: Filtering by crude: {crude_filter}")
        df = df[df['Crude'].str.contains(crude_filter, case=False, na=False)]
        print(f"DEBUG: After crude filter - {len(df)} rows")
    
    if intensity_filter:
        print(f"DEBUG: Filtering by intensities: {intensity_filter}")
        df = df[df['Carbon Intensity'].isin(intensity_filter)]
        print(f"DEBUG: After intensity filter - {len(df)} rows")
        print(f"DEBUG: Remaining countries: {sorted(df['Country'].unique().tolist())}")
        print(f"DEBUG: Remaining intensities: {sorted(df['Carbon Intensity'].unique().tolist())}")
    
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data matches the selected filters.",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(height=700, plot_bgcolor='white', paper_bgcolor='white')
        return fig
    
    # Define color mapping based on Figure 1 legend - exact colors from Tableau visualization
    color_map = {
    "Very High": "#528DBA",
    "High":      "#0075A8",
    "Medium":    "#313B49",
    "Low":       "#595959",
    "Very Low":  "#A6A6A6"
}
    
    # Create hierarchical structure for treemap matching Tableau visualization
    # Level 1: Carbon Intensity (parent)
    # Level 2: Country (child of Carbon Intensity)  
    # Level 3: Crude (child of Country) - these are the visible blocks
    
    labels = []
    parents = []
    values = []
    colors = []
    hover_texts = []
    
    # Sort by Carbon Intensity order for consistent display (matching Figure 1 layout)
    # Order: Medium (top left), High (top right), Low (middle), Very Low (bottom left), Very High (bottom right)
    intensity_order = ['Medium', 'High', 'Low', 'Very Low', 'Very High']
    
    # Group by Carbon Intensity, then Country, then Crude
    for intensity in intensity_order:
        if intensity not in df['Carbon Intensity'].unique():
            continue
            
        intensity_df = df[df['Carbon Intensity'] == intensity]
        intensity_total = intensity_df['Production'].sum()
        
        if intensity_total == 0:
            continue
        
        # Add Carbon Intensity level (root) - not visible but needed for hierarchy
        intensity_label = intensity
        labels.append(intensity_label)
        parents.append('')
        values.append(intensity_total)
        colors.append(color_map.get(intensity, '#CCCCCC'))
        hover_texts.append(f'<b>{intensity}</b><br>Total Production: {intensity_total:,.0f} (\'000 b/d)<extra></extra>')
        
        # Add Country level - intermediate level
        # Group by country first to ensure each country appears only once per intensity
        for country in sorted(intensity_df['Country'].unique()):
            country_df = intensity_df[intensity_df['Country'] == country]
            country_total = country_df['Production'].sum()
            
            # Create unique country label by combining intensity and country to avoid ambiguity
            # This ensures each country label is unique across different intensity levels
            country_label = f"{intensity}|{country}"  # Use | as separator for uniqueness
            
            labels.append(country_label)
            parents.append(intensity_label)
            values.append(country_total)
            colors.append(color_map.get(intensity, '#CCCCCC'))
            hover_texts.append(f'<b>{country}</b><br>Production: {country_total:,.0f} (\'000 b/d)<br>Carbon Intensity: {intensity}<extra></extra>')
            
            # Add Crude level - these are the visible leaf nodes
            # Collect all crudes for this country to show in hover (matching Figure 2 format)
            crudes_list = country_df['Crude'].tolist()
            crudes_str = ', '.join(crudes_list)
            country_total_production = country_df['Production'].sum()
            
            for _, row in country_df.iterrows():
                # Format label as "Country Crude" (without colon) to match Tableau exactly
                # Make crude label unique by including country and intensity
                crude_label = f"{intensity}|{country}|{row['Crude']}"
                
                labels.append(crude_label)
                parents.append(country_label)
                values.append(row['Production'])
                colors.append(color_map.get(intensity, '#CCCCCC'))
                # Hover format matching Figure 2 exactly: Carbon Intensity, Country, Year, Production, Crudes
                hover_texts.append(
                    f'Carbon Intensity: {intensity}<br>'
                    f'Country: {country}<br>'
                    f'Year: 2022<br>'
                    f'Production: {country_total_production:,.0f} (\'000 b/d)<br>'
                    f'Crudes: {crudes_str}<extra></extra>'
                )
    
    if not labels:
        print("✗ WARNING: No labels created for treemap!")
        print(f"  DataFrame shape: {df.shape}")
        print(f"  Carbon Intensity values in df: {df['Carbon Intensity'].unique() if not df.empty else 'N/A'}")
        print(f"  Intensity filter: {intensity_filter}")
        fig = go.Figure()
        fig.add_annotation(
            text="No data to display. Check filters and CSV file.",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color='red')
        )
        fig.update_layout(height=700, plot_bgcolor='white', paper_bgcolor='white', title="No Data")
        return fig
    
    print(f"✓ Created {len(labels)} labels, {len(values)} values for treemap")
    
    # Create custom text for display (extract clean names from unique labels)
    custom_text = []
    for label in labels:
        if '|' in label:
            # Extract the last part after the last | separator for display
            custom_text.append(label.split('|')[-1])
        else:
            # Root level (intensity) - keep as is
            custom_text.append(label)
    
    # Create treemap with hierarchical structure
    # Use unique labels for the hierarchy (to avoid ambiguity)
    # Use custom_text for display
    custom_text = [label.split("|")[-1] for label in labels]

    fig = go.Figure(
        go.Treemap(
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            hovertext=hover_texts,
            hovertemplate="%{hovertext}<extra></extra>",

            text=custom_text,

            ### 🔵 CHANGED — better font
            textinfo="text",
            textfont=dict(size=10, color="#2c3e50"),

            ### 🔵 CHANGED — subtle padding like Tableau
            tiling=dict(pad=1, packing="squarify"),

            marker=dict(
                colors=colors,

                ### 🔵 CHANGED — thinner borders (1px)
                line=dict(color="white", width=1),  

                colorscale=None
            ),

            maxdepth=3,
            pathbar=dict(visible=False),
        )
    )

    ### 🔵 CHANGED — hide giant root block background
    fig.update_traces(root_color="white")

    # -------------------------------------------------------------------
    # 3️⃣ **LAYOUT — match Tableau spacing & title**
    # -------------------------------------------------------------------
    fig.update_layout(
        title=dict(
            text="Upstream Crude Oil Production by Carbon Intensity",
            x=0.5,
            xanchor="center",
            font=dict(size=18, color="#2c3e50")
        ),
        height=700,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        showlegend=False
    )

    return fig


def load_carbon_data():
    """Load and transform carbon intensity data from CSV"""
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'Carbon Intensity.csv')
    
    # Convert to absolute path
    if not os.path.isabs(csv_path):
        csv_path = os.path.abspath(csv_path)
    
    print(f"DEBUG: Loading CSV from: {csv_path}")
    print(f"DEBUG: File exists: {os.path.exists(csv_path)}")
    
    try:
        # Read CSV - it's tab-separated, skip first row (repeated headers), use second row as actual headers
        # Try different encodings
        df = None
        for encoding in ['utf-16', 'latin-1', 'iso-8859-1', 'cp1252']:
            try:
                df = pd.read_csv(csv_path, skiprows=1, header=0, sep='\t', encoding=encoding)
                if df.shape[1] > 2:  # Make sure we got multiple columns
                    print(f"DEBUG: Successfully loaded with {encoding} encoding")
                    break
            except Exception as e:
                print(f"DEBUG: Failed with {encoding}: {str(e)[:50]}")
                continue
        
        if df is None or df.shape[1] < 2:
            print("ERROR: Could not load CSV or insufficient columns")
            return pd.DataFrame()
        
        # The first two columns are Carbon Intensity and Country
        carbon_intensity_col = df.columns[0]
        country_col = df.columns[1]
        
        # Get all crude type columns (everything after Country)
        crude_columns = df.columns[2:].tolist()
        
        # Transform to long format
        data_rows = []
        for idx, row in df.iterrows():
            carbon_intensity = row[carbon_intensity_col]
            country = row[country_col]
            
            if pd.isna(carbon_intensity) or pd.isna(country):
                continue
            
            # Process each crude type column
            for crude_col in crude_columns:
                volume = row[crude_col]
                
                # Skip if volume is NaN or empty
                if pd.isna(volume) or volume == '' or str(volume).strip() == '':
                    continue
                
                # Clean volume - remove commas and convert to float
                try:
                    if isinstance(volume, str):
                        volume = volume.replace(',', '').strip()
                    volume = float(volume)
                    
                    if volume > 0:
                        # Get crude name from column header
                        crude_name = str(crude_col).strip()
                        data_rows.append({
                            'Carbon Intensity': str(carbon_intensity).strip(),
                            'Country': str(country).strip(),
                            'Crude': crude_name,
                            'Production': volume
                        })
                except (ValueError, TypeError) as e:
                    continue
        
        result_df = pd.DataFrame(data_rows)
        print(f"DEBUG: Transformed to {len(result_df)} data rows")
        if len(result_df) > 0:
            print(f"DEBUG: Carbon Intensity values: {result_df['Carbon Intensity'].unique()}")
            print(f"DEBUG: Countries: {result_df['Country'].nunique()}")
            print(f"DEBUG: Total production: {result_df['Production'].sum():,.0f}")
        return result_df
        
    except Exception as e:
        import traceback
        print(f"ERROR loading carbon data: {e}")
        traceback.print_exc()
        return pd.DataFrame()


def register_callbacks(dash_app, server):
    """Register all callbacks for Crude Carbon Intensity"""
    
    # Callback to handle country dropdown expand/collapse
    @dash_app.callback(
        [Output('country-checklist-container', 'style'),
         Output('country-dropdown-icon', 'children')],
        Input('country-dropdown-header', 'n_clicks'),
        State('country-checklist-container', 'style'),
        prevent_initial_call=False
    )
    def toggle_country_dropdown(n_clicks, current_style):
        """Toggle country checklist visibility"""
        if n_clicks is None or n_clicks == 0:
            # Default: expanded
            return {'marginBottom': '10px', 'display': 'block'}, "▼"
        
        # Toggle display based on current state
        is_visible = current_style.get('display', 'block') == 'block'
        new_display = 'none' if is_visible else 'block'
        icon = "▶" if is_visible else "▼"
        
        new_style = {**current_style, 'display': new_display}
        return new_style, icon
    
    # Callback to handle "(All)" selection - check/uncheck all countries
    @dash_app.callback(
        [Output('carbon-country-select', 'value', allow_duplicate=True),
         Output('country-selection-store', 'data')],
        Input('carbon-country-select', 'value'),
        [State('carbon-country-select', 'options'),
         State('country-selection-store', 'data')],
        prevent_initial_call=True
    )
    def handle_select_all_countries(selected_countries, country_options, previous_selection):
        """Handle (All) selection - check/uncheck all countries"""
        if selected_countries is None:
            selected_countries = []
        if previous_selection is None:
            previous_selection = []
        
        # Get all country values (excluding "(All)")
        all_country_values = [opt['value'] for opt in country_options if opt['value'] != '(All)']
        all_country_set = set(all_country_values)
        
        # Get current selection without "(All)"
        current_without_all = [c for c in selected_countries if c != '(All)']
        current_without_all_set = set(current_without_all)
        
        # Check previous selection
        previous_without_all = [c for c in previous_selection if c != '(All)']
        had_all_before = '(All)' in previous_selection
        has_all_now = '(All)' in selected_countries
        
        # Case 1: "(All)" was just checked (wasn't before, is now)
        if has_all_now and not had_all_before:
            # Select all countries including "(All)"
            new_selection = ['(All)'] + all_country_values
            return new_selection, new_selection
        
        # Case 2: "(All)" was just unchecked (was before, isn't now)
        if not has_all_now and had_all_before:
            # Deselect all countries
            return [], []
        
        # Case 3: "(All)" is currently selected but not all countries are in the list
        if has_all_now and current_without_all_set != all_country_set:
            # Ensure all countries are selected
            new_selection = ['(All)'] + all_country_values
            return new_selection, new_selection
        
        # Case 4: All countries are manually selected (without "(All)")
        if not has_all_now and current_without_all_set == all_country_set and len(current_without_all) > 0:
            # Auto-check "(All)" to keep in sync
            new_selection = ['(All)'] + all_country_values
            return new_selection, new_selection
        
        # Case 5: Some countries were deselected while "(All)" was selected
        if had_all_before and has_all_now and current_without_all_set != all_country_set:
            # Remove "(All)" since not all countries are selected
            return current_without_all, current_without_all
        
        # Case 6: Normal selection - return as is
        return selected_countries, selected_countries
    
    @dash_app.callback(
        Output('crude-carbon-chart', 'figure'),
        [Input('carbon-year-select', 'value'),
         Input('carbon-country-select', 'value'),
         Input('carbon-crude-filter', 'value'),
         Input('carbon-intensity-filter', 'value')],
        prevent_initial_call=False
    )
    def update_crude_carbon(year, country_filter, crude_filter, intensity_filter):
        """Update crude carbon intensity treemap"""
        print(f"=== CALLBACK TRIGGERED ===")
        print(f"year={year}, country={country_filter}, crude={crude_filter}, intensity={intensity_filter}")
        
        # Handle None inputs
        if country_filter is None:
            country_filter = ['(All)']
        # Ensure country_filter is a list
        if not isinstance(country_filter, list):
            country_filter = [country_filter] if country_filter else ['(All)']
        if crude_filter is None:
            crude_filter = ''
        if intensity_filter is None or len(intensity_filter) == 0:
            intensity_filter = ['Very High', 'High', 'Medium', 'Low', 'Very Low']
        
        # Load data - ALWAYS load and create chart
        try:
            df = load_carbon_data()
            print(f"✓ Loaded {len(df)} rows from CSV")
        except Exception as e:
            import traceback
            print(f"✗ ERROR loading data: {e}")
            traceback.print_exc()
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color='red')
            )
            fig.update_layout(height=700, plot_bgcolor='white', paper_bgcolor='white', title="Error Loading Data")
            return fig
        
        if df.empty:
            print("✗ DataFrame is EMPTY!")
            fig = go.Figure()
            fig.add_annotation(
                text="No data loaded from CSV file",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color='red')
            )
            fig.update_layout(height=700, plot_bgcolor='white', paper_bgcolor='white', title="No Data")
            return fig
        
        # Create the figure
        print(f"✓ Creating treemap with {len(df)} rows...")
        print(f"DEBUG: country_filter={country_filter}, intensity_filter={intensity_filter}")
        print(f"DEBUG: Available countries in data: {sorted(df['Country'].unique().tolist())}")
        print(f"DEBUG: Available intensities in data: {sorted(df['Carbon Intensity'].unique().tolist())}")
        
        # Convert country_filter list to None if it contains '(All)' or is empty or all countries selected
        country_filter_for_figure = None
        if country_filter and isinstance(country_filter, list):
            # Check if "(All)" is in the selection
            if '(All)' in country_filter:
                # "(All)" is selected - show all countries
                print("DEBUG: '(All)' detected in country_filter, showing all countries")
                country_filter_for_figure = None
            else:
                # Remove "(All)" from the list if present (shouldn't be here, but just in case)
                country_filter_clean = [c for c in country_filter if c != '(All)']
                # Get all available countries from data
                all_available_countries = sorted(df['Country'].unique().tolist())
                # If all countries are selected or list is empty, show all
                if len(country_filter_clean) == 0 or set(country_filter_clean) == set(all_available_countries):
                    print("DEBUG: All countries selected or empty list, showing all")
                    country_filter_for_figure = None
                else:
                    print(f"DEBUG: Filtering to specific countries: {country_filter_clean}")
                    country_filter_for_figure = country_filter_clean
        elif country_filter and country_filter != '(All)':
            country_filter_for_figure = country_filter
        else:
            # No filter or "(All)" - show all
            print("DEBUG: No country filter or '(All)', showing all countries")
            country_filter_for_figure = None
        
        fig = create_carbon_treemap_figure(
            df=df,
            country_filter=country_filter_for_figure,
            crude_filter=crude_filter if crude_filter else None,
            intensity_filter=intensity_filter
        )
        
        print(f"✓ Figure created: {len(fig.data)} traces")
        if len(fig.data) > 0 and hasattr(fig.data[0], 'labels'):
            print(f"✓ Labels: {len(fig.data[0].labels)}, Values: {len(fig.data[0].values) if hasattr(fig.data[0], 'values') else 0}")
        
        print(f"=== RETURNING FIGURE ===")
        return fig
def create_crude_carbon_dashboard(server, url_base_pathname="/dash/crude-carbon/"):
    """Create the Crude Carbon Intensity dashboard"""
    dash_app = create_dash_app(server, url_base_pathname)
    dash_app.layout = create_layout()
    register_callbacks(dash_app, server)
    return dash_app
