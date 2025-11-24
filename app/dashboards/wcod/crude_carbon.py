"""
Crude Carbon Intensity View - Fixed Block List
"""
from dash import dcc, html, Input, Output, State, callback
import dash
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import os

def create_layout():
    """Create the Crude Carbon Intensity layout"""
    # Load data to get available years
    data_df = load_carbon_data()
    countries = ['(All)']
    
    if not data_df.empty:
        unique_countries = sorted(data_df['Country'].dropna().unique().tolist())
        countries.extend(unique_countries)
        
        # Extract years from data
        if 'Year' in data_df.columns:
            year_values = data_df['Year'].dropna()
            if len(year_values) > 0:
                try:
                    year_values = pd.to_numeric(year_values, errors='coerce').dropna()
                    if len(year_values) > 0:
                        available_years = sorted(year_values.astype(int).unique().tolist(), reverse=True)
                except:
                    available_years = list(range(2006, 2025))
        else:
            available_years = list(range(2006, 2025))
    else:
        available_years = list(range(2006, 2025))
    
    # Default to 2022 if available
    if 2022 in available_years:
        default_year = 2022
    else:
        default_year = available_years[0] if available_years else 2022
    
    min_year = min(available_years) if available_years else 2006
    max_year = max(available_years) if available_years else 2024
    
    return html.Div([
        html.Div([
            # Main visualization area (75% width)
            html.Div([
                dcc.Graph(
                    id='crude-carbon-chart', 
                    style={'height': '700px'},
                    config={'displayModeBar': False}
                )
            ], style={'width': '75%', 'float': 'left', 'paddingRight': '20px'}),
            
            # Control panel (25% width)
            html.Div([
                # Year selector
                html.Div([
                    html.Label("Year:", style={
                        'fontWeight': '600', 
                        'marginBottom': '8px',
                        'fontSize': '13px',
                        'color': '#2c3e50',
                        'fontFamily': 'Arial, sans-serif'
                    }),
                    html.Div([
                        html.Button("◄", id='carbon-year-decrement', n_clicks=0, style={
                            'width': '28px',
                            'height': '28px',
                            'border': '1px solid #b3b3b3',
                            'backgroundColor': '#ffffff',
                            'cursor': 'pointer',
                            'fontSize': '12px',
                            'padding': '0',
                            'marginRight': '4px',
                            'borderRadius': '3px',
                            'color': '#333333'
                        }),
                        dcc.Input(
                            id='carbon-year-input',
                            type='number',
                            value=default_year,
                            min=min_year,
                            max=max_year,
                            step=1,
                            style={
                                'width': '70px',
                                'height': '26px',
                                'textAlign': 'center',
                                'border': '1px solid #b3b3b3',
                                'fontSize': '13px',
                                'padding': '2px 5px',
                                'fontWeight': '500',
                                'color': '#333333'
                            }
                        ),
                        html.Button("►", id='carbon-year-increment', n_clicks=0, style={
                            'width': '28px',
                            'height': '28px',
                            'border': '1px solid #b3b3b3',
                            'backgroundColor': '#ffffff',
                            'cursor': 'pointer',
                            'fontSize': '12px',
                            'padding': '0',
                            'marginLeft': '4px',
                            'borderRadius': '3px',
                            'color': '#333333'
                        })
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '8px'}),
                    dcc.Slider(
                        id='carbon-year-slider',
                        min=min_year,
                        max=max_year,
                        value=default_year,
                        step=1,
                        marks={year: "" for year in available_years},
                        tooltip={"placement": "bottom", "always_visible": False}
                    )
                ], style={'marginBottom': '20px'}),
                
                html.Div(id='carbon-year-display', children=str(default_year), style={'display': 'none'}),
                
                # Carbon Intensity legend
                html.Div([
                    html.Label("Carbon Intensity:", style={
                        'fontWeight': '600', 
                        'marginBottom': '12px', 
                        'fontSize': '13px',
                        'color': '#2c3e50',
                        'fontFamily': 'Arial, sans-serif'
                    }),
                    html.Div([
                        html.Div([
                            html.Div(style={
                                'width': '18px',
                                'height': '18px',
                                'backgroundColor': '#528DBA',
                                'border': '2px solid white',
                                'display': 'inline-block',
                                'marginRight': '10px',
                                'verticalAlign': 'middle',
                                'boxShadow': '0 1px 3px rgba(0,0,0,0.2)'
                            }),
                            html.Span('Very High', style={
                                'fontSize': '12px', 
                                'verticalAlign': 'middle',
                                'fontWeight': '500',
                                'color': '#333333'
                            })
                        ], id='intensity-very-high', n_clicks=0, style={
                            'marginBottom': '8px', 
                            'display': 'flex', 
                            'alignItems': 'center', 
                            'cursor': 'pointer',
                            'padding': '4px 8px',
                            'borderRadius': '3px',
                            'border': '1px solid transparent'
                        }),
                        
                        html.Div([
                            html.Div(style={
                                'width': '18px',
                                'height': '18px',
                                'backgroundColor': '#0075A8',
                                'border': '2px solid white',
                                'display': 'inline-block',
                                'marginRight': '10px',
                                'verticalAlign': 'middle',
                                'boxShadow': '0 1px 3px rgba(0,0,0,0.2)'
                            }),
                            html.Span('High', style={
                                'fontSize': '12px', 
                                'verticalAlign': 'middle',
                                'fontWeight': '500',
                                'color': '#333333'
                            })
                        ], id='intensity-high', n_clicks=0, style={
                            'marginBottom': '8px', 
                            'display': 'flex', 
                            'alignItems': 'center', 
                            'cursor': 'pointer',
                            'padding': '4px 8px',
                            'borderRadius': '3px',
                            'border': '1px solid transparent'
                        }),
                        
                        html.Div([
                            html.Div(style={
                                'width': '18px',
                                'height': '18px',
                                'backgroundColor': '#313B49',
                                'border': '2px solid white',
                                'display': 'inline-block',
                                'marginRight': '10px',
                                'verticalAlign': 'middle',
                                'boxShadow': '0 1px 3px rgba(0,0,0,0.2)'
                            }),
                            html.Span('Medium', style={
                                'fontSize': '12px', 
                                'verticalAlign': 'middle',
                                'fontWeight': '500',
                                'color': '#333333'
                            })
                        ], id='intensity-medium', n_clicks=0, style={
                            'marginBottom': '8px', 
                            'display': 'flex', 
                            'alignItems': 'center', 
                            'cursor': 'pointer',
                            'padding': '4px 8px',
                            'borderRadius': '3px',
                            'border': '1px solid transparent'
                        }),
                        
                        html.Div([
                            html.Div(style={
                                'width': '18px',
                                'height': '18px',
                                'backgroundColor': '#595959',
                                'border': '2px solid white',
                                'display': 'inline-block',
                                'marginRight': '10px',
                                'verticalAlign': 'middle',
                                'boxShadow': '0 1px 3px rgba(0,0,0,0.2)'
                            }),
                            html.Span('Low', style={
                                'fontSize': '12px', 
                                'verticalAlign': 'middle',
                                'fontWeight': '500',
                                'color': '#333333'
                            })
                        ], id='intensity-low', n_clicks=0, style={
                            'marginBottom': '8px', 
                            'display': 'flex', 
                            'alignItems': 'center', 
                            'cursor': 'pointer',
                            'padding': '4px 8px',
                            'borderRadius': '3px',
                            'border': '1px solid transparent'
                        }),
                        
                        html.Div([
                            html.Div(style={
                                'width': '18px',
                                'height': '18px',
                                'backgroundColor': '#A6A6A6',
                                'border': '2px solid white',
                                'display': 'inline-block',
                                'marginRight': '10px',
                                'verticalAlign': 'middle',
                                'boxShadow': '0 1px 3px rgba(0,0,0,0.2)'
                            }),
                            html.Span('Very Low', style={
                                'fontSize': '12px', 
                                'verticalAlign': 'middle',
                                'fontWeight': '500',
                                'color': '#333333'
                            })
                        ], id='intensity-very-low', n_clicks=0, style={
                            'marginBottom': '8px', 
                            'display': 'flex', 
                            'alignItems': 'center', 
                            'cursor': 'pointer',
                            'padding': '4px 8px',
                            'borderRadius': '3px',
                            'border': '1px solid transparent'
                        })
                    ])
                ], style={'marginBottom': '25px', 'padding': '15px', 'border': '1px solid #e0e0e0', 'borderRadius': '5px', 'backgroundColor': '#fafafa'}),
                
                # Hidden intensity filter
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
                    style={'display': 'none'}
                ),
                
                # Country filter
                html.Div([
                    html.Label("Country:", style={
                        'fontWeight': '600', 
                        'marginBottom': '8px',
                        'fontSize': '13px',
                        'color': '#2c3e50',
                        'fontFamily': 'Arial, sans-serif'
                    }),
                    html.Div([
                        dcc.Dropdown(
                            id='carbon-country-select',
                            options=[{'label': c, 'value': c} for c in countries],
                            value=['(All)'],
                            multi=True,
                            style={
                                'fontSize': '12px',
                                'fontFamily': 'Arial, sans-serif'
                            },
                            placeholder="Select countries..."
                        )
                    ])
                ], style={'marginBottom': '20px'}),
                
                # Crude list filter
                html.Div([
                    html.Label("Crude list:", style={
                        'fontWeight': '600', 
                        'marginBottom': '8px',
                        'fontSize': '13px',
                        'color': '#2c3e50',
                        'fontFamily': 'Arial, sans-serif'
                    }),
                    dcc.Input(
                        id='carbon-crude-filter',
                        type='text',
                        placeholder='Filter by crude name...',
                        style={
                            'width': '100%', 
                            'marginBottom': '10px',
                            'padding': '8px 10px',
                            'border': '1px solid #b3b3b3',
                            'borderRadius': '4px',
                            'fontSize': '12px',
                            'fontFamily': 'Arial, sans-serif',
                            'backgroundColor': '#ffffff'
                        }
                    )
                ])
            ], style={
                'width': '25%', 
                'float': 'right', 
                'padding': '25px', 
                'background': '#ffffff', 
                'borderRadius': '8px',
                'minHeight': '700px',
                'border': '1px solid #e0e0e0',
                'boxShadow': '0 2px 10px rgba(0,0,0,0.05)'
            })
        ], style={'position': 'relative', 'display': 'flex', 'width': '100%'}),
        html.Div(style={'clear': 'both'})
    ], className='tab-content', style={'backgroundColor': '#f5f7fa', 'padding': '20px', 'minHeight': '100vh'})

def create_carbon_treemap_figure(df=None, country_filter=None, crude_filter=None, intensity_filter=None, selected_year=None):
    """Render Tableau-style treemap with two columns (Medium + Very Low on left, others right)."""
    print(f"DEBUG create_carbon_treemap_figure: df={df.shape if df is not None else 'None'}, filters={country_filter}, {crude_filter}, {intensity_filter}, year={selected_year}")

    if df is None or df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No carbon intensity data available.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#666666")
        )
        fig.update_layout(height=700, plot_bgcolor="white", paper_bgcolor="white", margin=dict(l=0, r=0, t=0, b=0))
        return fig

    filtered_df = df.copy()

    if selected_year is not None and "Year" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Year"] == selected_year]
    if country_filter and isinstance(country_filter, list) and "(All)" not in country_filter:
        filtered_df = filtered_df[filtered_df["Country"].isin(country_filter)]
    if crude_filter:
        filtered_df = filtered_df[filtered_df["Crude list"].str.contains(crude_filter, case=False, na=False)]
    if intensity_filter:
        filtered_df = filtered_df[filtered_df["Carbon Intensity"].isin(intensity_filter)]

    if filtered_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data matches the selected filters.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#666666")
        )
        fig.update_layout(height=700, plot_bgcolor="white", paper_bgcolor="white", margin=dict(l=0, r=0, t=0, b=0))
        return fig

    color_map = {
        "Medium": "#313B49",
        "Very Low": "#A6A6A6",
        "High": "#0075A8",
        "Low": "#595959",
        "Very High": "#528DBA"
    }

    intensity_slots = {
        "Medium": dict(x=[0.0, 0.58], y=[0.45, 1.0]),
        "Very Low": dict(x=[0.0, 0.58], y=[0.0, 0.45]),
        "High": dict(x=[0.58, 1.0], y=[0.60, 1.0]),
        "Low": dict(x=[0.58, 1.0], y=[0.32, 0.60]),
        "Very High": dict(x=[0.58, 1.0], y=[0.0, 0.32]),
    }

    fig = go.Figure()
    for intensity, position in intensity_slots.items():
        intensity_df = filtered_df[filtered_df["Carbon Intensity"] == intensity]
        if intensity_df.empty:
            continue

        grouped = (
            intensity_df.groupby("Country")
            .agg({
                "Production": "sum",
                "Crude list": lambda rows: ", ".join(sorted({str(val).strip() for val in rows if str(val).strip() not in ("", "nan")})),
            })
            .reset_index()
        )
        grouped = grouped[grouped["Production"] > 0]
        grouped = grouped[grouped["Country"].astype(str).str.strip().ne("")]
        if grouped.empty:
            continue

        grouped = grouped.sort_values(["Production", "Country"], ascending=[False, True])

        labels = [intensity]
        parents = [""]
        values = [grouped["Production"].sum()]
        hover_texts = [""]
        text_entries = ["<span style='opacity:0;font-size:0px;'>.</span>"]
        colors = [color_map[intensity]]

        for _, row in grouped.iterrows():
            country_name = str(row["Country"]).strip()
            production_value = row["Production"]
            crudes_str = row["Crude list"]

            labels.append(country_name)
            parents.append(intensity)
            values.append(production_value)
            hover_texts.append(
                f"Carbon Intensity: {intensity}<br>"
                f"Country: {country_name}<br>"
                f"Production: {production_value:,.0f} ('000 b/d)<br>"
                f"Crudes: {crudes_str}"
            )
            text_body = f"<b>{country_name}</b>"
            if crudes_str:
                text_body += f"<br>{crudes_str}"
            text_entries.append(text_body)
            colors.append(color_map[intensity])

        fig.add_trace(
            go.Treemap(
                labels=labels,
                parents=parents,
                values=values,
                branchvalues="total",
                hovertext=hover_texts,
                hovertemplate="%{hovertext}<extra></extra>",
                text=text_entries,
                textinfo="text",
                textfont=dict(size=12, color="#ffffff", family="Arial, sans-serif"),
                marker=dict(
                    colors=colors,
                    line=dict(color="white", width=1)
                ),
                tiling=dict(pad=1, packing="squarify", squarifyratio=1.0),
                maxdepth=2,
                pathbar=dict(visible=False),
                domain=position,
                root=dict(color="rgba(255,255,255,0)")
            )
        )

    fig.update_layout(
        title=dict(
            text="Upstream Crude Oil Production by Carbon Intensity",
            x=0.5,
            xanchor="center",
            y=0.98,
            font=dict(size=20, color="#2c3e50", family="Arial, sans-serif")
        ),
        height=700,
        margin=dict(l=10, r=10, t=60, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        showlegend=False,
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#cccccc",
            font_size=12,
            font_family="Arial, sans-serif",
            align="left"
        )
    )

    return fig

def load_carbon_data():
    """Load and clean carbon intensity data"""
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'Carbon Intensity_data.csv')
    
    print(f"DEBUG: Loading CSV from: {csv_path}")
    print(f"DEBUG: File exists: {os.path.exists(csv_path)}")
    
    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file not found at {csv_path}")
        return pd.DataFrame()
    
    try:
        # Read CSV with proper encoding
        df = pd.read_csv(csv_path, encoding='utf-8')
        print(f"DEBUG: Loaded CSV with shape: {df.shape}")
        print(f"DEBUG: Columns: {list(df.columns)}")
        print(f"DEBUG: First few rows:\n{df.head()}")
        
        # Clean column names
        df.columns = [col.strip() for col in df.columns]
        
        # Map to standard column names
        column_mapping = {}
        for col in df.columns:
            if 'carbon' in col.lower() and 'intensity' in col.lower():
                column_mapping[col] = 'Carbon Intensity'
            elif 'country' in col.lower():
                column_mapping[col] = 'Country'
            elif 'crude' in col.lower() and 'list' in col.lower():
                column_mapping[col] = 'Crude list'
            elif 'year' in col.lower():
                column_mapping[col] = 'Year'
            elif 'production' in col.lower():
                column_mapping[col] = 'Production'
        
        df = df.rename(columns=column_mapping)
        print(f"DEBUG: After renaming - Columns: {list(df.columns)}")
        
        # Clean data
        df['Carbon Intensity'] = df['Carbon Intensity'].astype(str).str.strip()
        df['Country'] = df['Country'].astype(str).str.strip()
        df['Crude list'] = df['Crude list'].astype(str).str.strip()
        
        # Convert Production to numeric, handling errors
        df['Production'] = pd.to_numeric(df['Production'], errors='coerce')
        
        # Convert Year to numeric if it exists
        if 'Year' in df.columns:
            df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
        
        # Remove rows with missing critical data
        initial_count = len(df)
        df = df.dropna(subset=['Carbon Intensity', 'Country', 'Crude list', 'Production'])
        final_count = len(df)
        print(f"DEBUG: Removed {initial_count - final_count} rows with missing data")
        
        print(f"DEBUG: Final dataset - {len(df)} rows")
        print(f"DEBUG: Available years: {sorted(df['Year'].dropna().unique())}")
        print(f"DEBUG: Available intensities: {sorted(df['Carbon Intensity'].unique())}")
        print(f"DEBUG: Available countries: {sorted(df['Country'].unique())[:10]}...")  # First 10 countries
        
        return df
        
    except Exception as e:
        import traceback
        print(f"ERROR loading carbon data: {e}")
        traceback.print_exc()
        return pd.DataFrame()

def register_callbacks(dash_app, server):
    """Register all callbacks for Crude Carbon Intensity"""
    
    # Callback to handle Carbon Intensity legend clicks
    @dash_app.callback(
        Output('carbon-intensity-filter', 'value', allow_duplicate=True),
        [Input('intensity-very-high', 'n_clicks'),
         Input('intensity-high', 'n_clicks'),
         Input('intensity-medium', 'n_clicks'),
         Input('intensity-low', 'n_clicks'),
         Input('intensity-very-low', 'n_clicks')],
        State('carbon-intensity-filter', 'value'),
        prevent_initial_call=True
    )
    def toggle_intensity_filter(vh_clicks, h_clicks, m_clicks, l_clicks, vl_clicks, current_values):
        """Toggle Carbon Intensity filter when legend items are clicked"""
        if current_values is None:
            current_values = ['Very High', 'High', 'Medium', 'Low', 'Very Low']
        
        ctx = dash.callback_context
        if not ctx.triggered:
            return current_values
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Map trigger IDs to intensity values
        intensity_map = {
            'intensity-very-high': 'Very High',
            'intensity-high': 'High',
            'intensity-medium': 'Medium',
            'intensity-low': 'Low',
            'intensity-very-low': 'Very Low'
        }
        
        toggled_value = intensity_map.get(trigger_id)
        if toggled_value:
            if toggled_value in current_values:
                # Remove if already selected
                new_values = [v for v in current_values if v != toggled_value]
            else:
                # Add if not selected
                new_values = current_values + [toggled_value]
            return new_values
        
        return current_values
    
    # Callback to update legend item visual state based on filter
    @dash_app.callback(
        [Output('intensity-very-high', 'style'),
         Output('intensity-high', 'style'),
         Output('intensity-medium', 'style'),
         Output('intensity-low', 'style'),
         Output('intensity-very-low', 'style')],
        Input('carbon-intensity-filter', 'value'),
        prevent_initial_call=False
    )
    def update_intensity_legend_styles(selected_intensities):
        """Update legend item styles to show which are selected"""
        if selected_intensities is None:
            selected_intensities = ['Very High', 'High', 'Medium', 'Low', 'Very Low']
        
        base_style = {
            'marginBottom': '8px', 
            'display': 'flex', 
            'alignItems': 'center', 
            'cursor': 'pointer',
            'padding': '4px 8px',
            'borderRadius': '3px',
            'border': '1px solid transparent'
        }
        
        styles = {
            'Very High': {**base_style, 'opacity': '1.0' if 'Very High' in selected_intensities else '0.3'},
            'High': {**base_style, 'opacity': '1.0' if 'High' in selected_intensities else '0.3'},
            'Medium': {**base_style, 'opacity': '1.0' if 'Medium' in selected_intensities else '0.3'},
            'Low': {**base_style, 'opacity': '1.0' if 'Low' in selected_intensities else '0.3'},
            'Very Low': {**base_style, 'opacity': '1.0' if 'Very Low' in selected_intensities else '0.3'}
        }
        
        return (
            styles['Very High'],
            styles['High'],
            styles['Medium'],
            styles['Low'],
            styles['Very Low']
        )
    
    # Callback to sync year controls
    @dash_app.callback(
        [Output('carbon-year-input', 'value', allow_duplicate=True),
         Output('carbon-year-slider', 'value', allow_duplicate=True),
         Output('carbon-year-display', 'children', allow_duplicate=True)],
        [Input('carbon-year-input', 'value'),
         Input('carbon-year-slider', 'value'),
         Input('carbon-year-increment', 'n_clicks'),
         Input('carbon-year-decrement', 'n_clicks')],
        [State('carbon-year-display', 'children'),
         State('carbon-year-slider', 'min'),
         State('carbon-year-slider', 'max')],
        prevent_initial_call=True
    )
    def sync_year_controls(input_value, slider_value, inc_clicks, dec_clicks, current_year, min_year, max_year):
        """Sync year input, slider, and increment/decrement buttons"""
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        try:
            current_year = int(current_year) if current_year else 2022
        except:
            current_year = 2022
        
        if trigger_id == 'carbon-year-increment':
            new_year = min(current_year + 1, max_year)
        elif trigger_id == 'carbon-year-decrement':
            new_year = max(current_year - 1, min_year)
        elif trigger_id == 'carbon-year-input':
            new_year = max(min(int(input_value), max_year), min_year) if input_value else current_year
        elif trigger_id == 'carbon-year-slider':
            new_year = slider_value
        else:
            new_year = current_year
        
        return new_year, new_year, str(new_year)
    
    # Main callback to update the chart
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
        print(f"=== CALLBACK TRIGGERED ===")
        print(f"year={year_str}, country={country_filter}, crude={crude_filter}, intensity={intensity_filter}")
        
        # Convert year string to int
        try:
            year = int(year_str) if year_str else 2022
        except:
            year = 2022
        
        # Handle None inputs
        if country_filter is None:
            country_filter = ['(All)']
        if crude_filter is None:
            crude_filter = ''
        if intensity_filter is None or len(intensity_filter) == 0:
            intensity_filter = ['Very High', 'High', 'Medium', 'Low', 'Very Low']
        
        # Load data
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
        print(f"✓ Creating treemap with filters...")
        fig = create_carbon_treemap_figure(
            df=df,
            country_filter=country_filter,
            crude_filter=crude_filter,
            intensity_filter=intensity_filter,
            selected_year=year
        )
        
        print(f"✓ Figure created: {len(fig.data)} traces")
        print(f"=== RETURNING FIGURE ===")
        return fig

def create_crude_carbon_dashboard(server, url_base_pathname="/dash/crude-carbon/"):
    """Create the Crude Carbon Intensity dashboard"""
    from app import create_dash_app
    dash_app = create_dash_app(server, url_base_pathname)
    dash_app.layout = create_layout()
    register_callbacks(dash_app, server)
    return dash_app