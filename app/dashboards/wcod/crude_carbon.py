"""
Crude Carbon Intensity View
Carbon intensity metrics for different crude types
"""
from dash import dcc, html, Input, Output, State, callback
import dash
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
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'Carbon Intensity_data.csv')
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
    
    # Year options for slider - update to include 2024
    available_years = [2024, 2023, 2022, 2021, 2020, 2019, 2018]
    min_year = min(available_years)
    max_year = max(available_years)
    
    return html.Div([
        html.Div([
            # Main visualization area (75% width)
            html.Div([
                dcc.Graph(id='crude-carbon-chart', style={'height': '700px'})
            ], style={'width': '75%', 'float': 'left', 'paddingRight': '20px'}),
            
            # Control panel (25% width)
            html.Div([
                # Year selector with arrows and slider (matching Tableau)
                html.Label("Year:", style={
                    'fontWeight': '500', 
                    'marginBottom': '8px',
                    'fontSize': '12px',
                    'color': '#2c3e50',
                    'fontFamily': 'Arial, sans-serif'
                }),
                html.Div([
                    html.Button("◄", id='carbon-year-decrement', n_clicks=0, style={
                        'width': '30px',
                        'height': '24px',
                        'border': '1px solid #ddd',
                        'backgroundColor': '#f8f9fa',
                        'cursor': 'pointer',
                        'fontSize': '12px',
                        'padding': '0',
                        'marginRight': '5px',
                        'borderRadius': '2px'
                    }),
                    dcc.Input(
                        id='carbon-year-input',
                        type='number',
                        value=2024,
                        min=min_year,
                        max=max_year,
                        step=1,
                        style={
                            'width': '60px',
                            'height': '22px',
                            'textAlign': 'center',
                            'border': '1px solid #ddd',
                            'fontSize': '12px',
                            'padding': '2px 5px'
                        }
                    ),
                    html.Button("►", id='carbon-year-increment', n_clicks=0, style={
                        'width': '30px',
                        'height': '24px',
                        'border': '1px solid #ddd',
                        'backgroundColor': '#f8f9fa',
                        'cursor': 'pointer',
                        'fontSize': '12px',
                        'padding': '0',
                        'marginLeft': '5px',
                        'borderRadius': '2px'
                    })
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px'}),
                dcc.Slider(
                    id='carbon-year-slider',
                    min=min_year,
                    max=max_year,
                    value=2024,
                    step=1,
                    marks={year: str(year) for year in available_years},
                    tooltip={"placement": "bottom", "always_visible": False}
                ),
                html.Div(id='carbon-year-display', children="2024", style={'display': 'none'}),  # Hidden store for year value
                
                # Show history checkbox
                dcc.Checklist(
                    id='carbon-show-history',
                    options=[{'label': 'Show history', 'value': 'show'}],
                    value=[],
                    style={'marginBottom': '15px', 'marginTop': '10px'}
                ),
                
                # Carbon Intensity legend with color swatches (matching Tableau)
                html.Label("Carbon Intensity:", style={
                    'fontWeight': '500', 
                    'marginBottom': '8px', 
                    'marginTop': '10px',
                    'fontSize': '12px',
                    'color': '#2c3e50',
                    'fontFamily': 'Arial, sans-serif'
                }),
                html.Div([
                    html.Div([
                        html.Div(style={
                            'width': '16px',
                            'height': '16px',
                            'backgroundColor': '#313B49',
                            'border': '1px solid #ccc',
                            'display': 'inline-block',
                            'marginRight': '8px',
                            'verticalAlign': 'middle'
                        }),
                        html.Span('Medium', style={'fontSize': '12px', 'verticalAlign': 'middle'})
                    ], style={'marginBottom': '5px', 'display': 'flex', 'alignItems': 'center'}),
                    html.Div([
                        html.Div(style={
                            'width': '16px',
                            'height': '16px',
                            'backgroundColor': '#0075A8',
                            'border': '1px solid #ccc',
                            'display': 'inline-block',
                            'marginRight': '8px',
                            'verticalAlign': 'middle'
                        }),
                        html.Span('High', style={'fontSize': '12px', 'verticalAlign': 'middle'})
                    ], style={'marginBottom': '5px', 'display': 'flex', 'alignItems': 'center'}),
                    html.Div([
                        html.Div(style={
                            'width': '16px',
                            'height': '16px',
                            'backgroundColor': '#595959',
                            'border': '1px solid #ccc',
                            'display': 'inline-block',
                            'marginRight': '8px',
                            'verticalAlign': 'middle'
                        }),
                        html.Span('Low', style={'fontSize': '12px', 'verticalAlign': 'middle'})
                    ], style={'marginBottom': '5px', 'display': 'flex', 'alignItems': 'center'}),
                    html.Div([
                        html.Div(style={
                            'width': '16px',
                            'height': '16px',
                            'backgroundColor': '#A6A6A6',
                            'border': '1px solid #ccc',
                            'display': 'inline-block',
                            'marginRight': '8px',
                            'verticalAlign': 'middle'
                        }),
                        html.Span('Very Low', style={'fontSize': '12px', 'verticalAlign': 'middle'})
                    ], style={'marginBottom': '5px', 'display': 'flex', 'alignItems': 'center'}),
                    html.Div([
                        html.Div(style={
                            'width': '16px',
                            'height': '16px',
                            'backgroundColor': '#528DBA',
                            'border': '1px solid #ccc',
                            'display': 'inline-block',
                            'marginRight': '8px',
                            'verticalAlign': 'middle'
                        }),
                        html.Span('Very High', style={'fontSize': '12px', 'verticalAlign': 'middle'})
                    ], style={'marginBottom': '5px', 'display': 'flex', 'alignItems': 'center'})
                ], style={'marginBottom': '15px', 'padding': '10px', 'border': '1px solid #ddd', 'borderRadius': '4px', 'backgroundColor': 'white'}),
                
                # Carbon Intensity filter checklist (hidden but functional)
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
                    style={'display': 'none'}  # Hidden, controlled by legend clicks if needed
                ),
                
                # Country filter
                html.Label("Country:", style={
                    'fontWeight': '500', 
                    'marginBottom': '8px', 
                    'marginTop': '10px',
                    'fontSize': '12px',
                    'color': '#2c3e50',
                    'fontFamily': 'Arial, sans-serif'
                }),
                html.Div([
                    html.Button([
                        html.Span("▼", id='country-dropdown-icon', style={
                            'fontSize': '10px',
                            'marginRight': '5px',
                            'display': 'inline-block',
                            'transition': 'transform 0.3s',
                            'userSelect': 'none'
                        }),
                        html.Span("(All)", id='country-dropdown-text', style={'fontSize': '12px', 'verticalAlign': 'middle'})
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
                        'color': '#2c3e50',
                        'fontFamily': 'Arial, sans-serif'
                    }),
                    html.Div([
                        dcc.Checklist(
                            id='carbon-country-select',
                            options=[{'label': c, 'value': c} for c in countries],
                            value=countries,
                            style={
                                'maxHeight': '300px',
                                'overflowY': 'auto',
                                'border': '1px solid #ddd',
                                'padding': '10px',
                                'borderRadius': '4px',
                                'backgroundColor': 'white',
                                'fontSize': '12px',
                                'fontFamily': 'Arial, sans-serif'
                            }
                        ),
                        dcc.Store(id='country-selection-store', data=countries)
                    ], id='country-checklist-container', style={'marginBottom': '10px', 'display': 'block'})
                ]),
                
                # Crude list filter
                html.Label("Crude list:", style={
                    'fontWeight': '500', 
                    'marginBottom': '8px', 
                    'marginTop': '10px',
                    'fontSize': '12px',
                    'color': '#2c3e50',
                    'fontFamily': 'Arial, sans-serif'
                }),
                dcc.Input(
                    id='carbon-crude-filter',
                    type='text',
                    placeholder='Filter crudes...',
                    style={
                        'width': '100%', 
                        'marginBottom': '10px',
                        'padding': '5px 8px',
                        'border': '1px solid #ddd',
                        'borderRadius': '4px',
                        'fontSize': '12px',
                        'fontFamily': 'Arial, sans-serif'
                    }
                )
            ], style={
                'width': '25%', 
                'float': 'right', 
                'padding': '20px', 
                'background': '#f9f9f9', 
                'borderRadius': '5px',
                'minHeight': '700px'
            })
        ], style={'position': 'relative', 'display': 'flex', 'width': '100%'}),
        html.Div(style={'clear': 'both'})  # Clear float
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
    # Level 1: Carbon Intensity (parent/root)
    # Level 2: Country (leaf nodes - these are the visible blocks)
    # Each country should be ONE block with all crudes listed inside
    
    labels = []
    parents = []
    values = []
    colors = []
    hover_texts = []
    country_crudes_map = {}  # Store all crudes per country for display
    
    # Sort by Carbon Intensity order for consistent display (matching Tableau layout)
    # Order: Very High, High, Medium, Low, Very Low (top to bottom)
    intensity_order = ['Very High', 'High', 'Medium', 'Low', 'Very Low']
    
    # Group by Carbon Intensity, then Country (each country is ONE block)
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
        
        # Group by country - each country becomes ONE block
        for country in sorted(intensity_df['Country'].unique()):
            country_df = intensity_df[intensity_df['Country'] == country]
            country_total = country_df['Production'].sum()
            
            # Collect all crudes for this country
            crudes_list = sorted(country_df['Crude'].unique().tolist())
            crudes_str = ', '.join(crudes_list)
            
            # Create unique country label by combining intensity and country
            country_label = f"{intensity}|{country}"
            
            # Store crudes for this country for text display
            country_crudes_map[country_label] = crudes_list
            
            # Add Country as leaf node (visible block)
            labels.append(country_label)
            parents.append(intensity_label)
            values.append(country_total)  # Total production for this country
            colors.append(color_map.get(intensity, '#CCCCCC'))
            
            # Hover format matching Tableau: Carbon Intensity, Country, Year, Production, Crudes
            # Year will be dynamic based on user selection
            hover_texts.append(
                f'Carbon Intensity: {intensity}<br>'
                f'Country: {country}<br>'
                f'Production: {country_total:,.0f} (\'000 b/d)<br>'
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
    
    # Create custom text for display - format: Country (bold), Crude names, Intensity
    custom_text = []
    for i, label in enumerate(labels):
        if '|' in label:
            parts = label.split('|')
            if len(parts) == 2:  # intensity|country - this is the visible block
                intensity_part, country_part = parts
                # Get all crudes for this country
                crudes_list = country_crudes_map.get(label, [])
                if crudes_list:
                    # Format: Country (bold), Crude names (comma-separated), Intensity level
                    crudes_str = ', '.join(crudes_list)
                    custom_text.append(f"<b>{country_part}</b><br>{crudes_str}<br>{intensity_part}")
                else:
                    custom_text.append(f"<b>{country_part}</b><br>{intensity_part}")
            else:
                custom_text.append(label.split("|")[-1])
        else:
            # Root level (intensity) - keep as is (not visible)
            custom_text.append("")

    fig = go.Figure(
        go.Treemap(
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            hovertext=hover_texts,
            hovertemplate="%{hovertext}<extra></extra>",

            text=custom_text,

            ### 🔵 CHANGED — better font with HTML support
            textinfo="text",
            textfont=dict(size=11, color="#ffffff", family="Arial, sans-serif"),  # White text - works on dark backgrounds
            # Note: Plotly doesn't support per-item text colors, so we use white which works on most dark backgrounds
            # For Low and Very Low (light backgrounds), white text may have less contrast but matches Tableau behavior

            ### 🔵 CHANGED — subtle padding like Tableau
            tiling=dict(pad=1, packing="squarify"),

            marker=dict(
                colors=colors,

                ### 🔵 CHANGED — thinner borders (1px)
                line=dict(color="white", width=1),  

                colorscale=None
            ),

            maxdepth=2,  # Only 2 levels: Carbon Intensity (root) -> Country (leaf)
            pathbar=dict(visible=False),
        )
    )

    ### 🔵 CHANGED — hide giant root block background
    fig.update_traces(root_color="white")

    # -------------------------------------------------------------------
    # 3️⃣ **LAYOUT — match Tableau spacing & title (reddish-orange)**
    # -------------------------------------------------------------------
    fig.update_layout(
        title=dict(
            text="Upstream Crude Oil Production by Carbon Intensity",
            x=0.5,
            xanchor="center",
            font=dict(size=18, color="#2c3e50", family="Arial, sans-serif")  # Dark grey to match Tableau (not reddish-orange)
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
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'Carbon Intensity_data.csv')
    
    # Convert to absolute path
    if not os.path.isabs(csv_path):
        csv_path = os.path.abspath(csv_path)
    
    print(f"DEBUG: Loading CSV from: {csv_path}")
    print(f"DEBUG: File exists: {os.path.exists(csv_path)}")
    
    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file not found at {csv_path}")
        return pd.DataFrame()
    
    try:
        # Try different encodings and separators
        df = None
        encodings = ['utf-16', 'utf-16-le', 'utf-16-be', 'utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        separators = ['\t', ',', ';']
        
        for encoding in encodings:
            for sep in separators:
                try:
                    # First, try with skiprows=1 (skip first row, use second as header)
                    test_df = pd.read_csv(csv_path, skiprows=1, header=0, sep=sep, encoding=encoding, on_bad_lines='skip', engine='python')
                    if test_df.shape[1] > 2:  # Make sure we got multiple columns
                        df = test_df
                        print(f"DEBUG: Successfully loaded with encoding={encoding}, sep='{sep}' (tab/space), skiprows=1")
                        break
                except Exception as e:
                    try:
                        # Try without skiprows (use first row as header)
                        test_df = pd.read_csv(csv_path, header=0, sep=sep, encoding=encoding, on_bad_lines='skip', engine='python')
                        if test_df.shape[1] > 2:
                            df = test_df
                            print(f"DEBUG: Successfully loaded with encoding={encoding}, sep='{sep}', header=0 (no skiprows)")
                            break
                    except Exception as e2:
                        continue
                if df is not None:
                    break
            if df is not None:
                break
        
        if df is None or df.shape[1] < 2:
            print("ERROR: Could not load CSV with any encoding/separator combination")
            print(f"DEBUG: Attempted encodings: {encodings}")
            print(f"DEBUG: Attempted separators: {separators}")
            return pd.DataFrame()
        
        print(f"DEBUG: Loaded CSV with shape: {df.shape}")
        print(f"DEBUG: Columns: {list(df.columns)}")
        
        # Clean up column names
        df.columns = df.columns.str.strip()
        
        # Try to identify Carbon Intensity and Country columns
        # Look for columns that might be named "Carbon Intensity" or similar
        carbon_intensity_col = None
        country_col = None
        
        # Try exact matches first
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if 'carbon' in col_lower and 'intensity' in col_lower:
                carbon_intensity_col = col
            elif 'country' in col_lower:
                country_col = col
        
        # If not found, use first two columns as fallback
        if carbon_intensity_col is None:
            carbon_intensity_col = df.columns[0]
            print(f"DEBUG: Using first column as Carbon Intensity: {carbon_intensity_col}")
        if country_col is None:
            country_col = df.columns[1]
            print(f"DEBUG: Using second column as Country: {country_col}")
        
        print(f"DEBUG: Using Carbon Intensity column: {carbon_intensity_col}")
        print(f"DEBUG: Using Country column: {country_col}")
        
        # Get all crude type columns (everything except Carbon Intensity and Country)
        exclude_cols = [carbon_intensity_col, country_col]
        crude_columns = [col for col in df.columns if col not in exclude_cols]
        
        print(f"DEBUG: Found {len(crude_columns)} crude columns")
        if len(crude_columns) == 0:
            print("ERROR: No crude columns found")
            return pd.DataFrame()
        
        # Transform to long format
        data_rows = []
        for idx, row in df.iterrows():
            carbon_intensity = row[carbon_intensity_col]
            country = row[country_col]
            
            if pd.isna(carbon_intensity) or pd.isna(country):
                continue
            
            # Skip if carbon intensity or country is empty string
            if str(carbon_intensity).strip() == '' or str(country).strip() == '':
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
        else:
            print("WARNING: No data rows created after transformation")
            print(f"DEBUG: Original DataFrame shape: {df.shape}")
            print(f"DEBUG: Sample of first few rows:")
            print(df.head())
        return result_df
        
    except Exception as e:
        import traceback
        print(f"ERROR loading carbon data: {e}")
        traceback.print_exc()
        return pd.DataFrame()


def register_callbacks(dash_app, server):
    """Register all callbacks for Crude Carbon Intensity"""
    
    # Callback to sync year input, slider, and buttons
    @dash_app.callback(
        [Output('carbon-year-input', 'value', allow_duplicate=True),
         Output('carbon-year-slider', 'value', allow_duplicate=True),
         Output('carbon-year-display', 'children', allow_duplicate=True)],
        [Input('carbon-year-input', 'value'),
         Input('carbon-year-slider', 'value'),
         Input('carbon-year-increment', 'n_clicks'),
         Input('carbon-year-decrement', 'n_clicks')],
        [State('carbon-year-display', 'children')],
        prevent_initial_call=True
    )
    def sync_year_controls(input_value, slider_value, inc_clicks, dec_clicks, current_year):
        """Sync year input, slider, and increment/decrement buttons"""
        ctx = dash.callback_context
        if not ctx.triggered:
            # Initial call - set default
            return 2024, 2024, "2024"
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        available_years = [2024, 2023, 2022, 2021, 2020, 2019, 2018]
        min_year = min(available_years)
        max_year = max(available_years)
        
        # Get current year value
        if current_year is None:
            current_year = 2024
        else:
            try:
                current_year = int(current_year)
            except:
                current_year = 2024
        
        if trigger_id == 'carbon-year-increment':
            new_year = min(current_year + 1, max_year)
        elif trigger_id == 'carbon-year-decrement':
            new_year = max(current_year - 1, min_year)
        elif trigger_id == 'carbon-year-input':
            new_year = input_value if input_value is not None else current_year
            new_year = max(min_year, min(new_year, max_year))
        elif trigger_id == 'carbon-year-slider':
            new_year = slider_value if slider_value is not None else current_year
        else:
            new_year = current_year
        
        # Ensure year is in available range
        new_year = max(min_year, min(new_year, max_year))
        
        return new_year, new_year, str(new_year)
    
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
        [Input('carbon-year-display', 'children'),
         Input('carbon-country-select', 'value'),
         Input('carbon-crude-filter', 'value'),
         Input('carbon-intensity-filter', 'value')],
        prevent_initial_call=False
    )
    def update_crude_carbon(year_str, country_filter, crude_filter, intensity_filter):
        """Update crude carbon intensity treemap"""
        # Convert year string to int
        try:
            year = int(year_str) if year_str else 2024
        except:
            year = 2024
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
