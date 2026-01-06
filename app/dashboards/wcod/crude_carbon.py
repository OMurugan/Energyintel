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
from core.data_helpers import execute_query


def create_layout():
    """Create the Crude Carbon Intensity layout"""
    # Don't load data here - load it in callbacks when page is active
    # Use default values for layout
    # Dynamically load countries from the main carbon intensity query
    try:
        query = '''
        SELECT 
            B.ci_rank AS "Carbon Intensity",
            B.country,
            STRING_AGG(B.crudeoil, ', ') AS "crude list",
            EXTRACT(YEAR FROM B.YearReported) AS "Year of YearReported",
            SUM(B.ProductionDataValue) AS ProductionDataValue
        FROM
        (
            SELECT
                country_name AS country,
                crude_name AS CrudeOil,
                yr AS YearReported,
                production_kbpd AS ProductionDataValue,
                ci_rank
            FROM fact_wcod_crude A
            LEFT JOIN dim_country GRP 
                ON A.country_id = GRP.dim_country_id
        ) B
        WHERE B.ci_rank IS NOT NULL 
        GROUP BY 
            B.country,
            B.ci_rank,
            B.YearReported
        ORDER BY 
            B.country,
            B.YearReported;
        '''
        df = execute_query(query)
        # Convert to DataFrame if needed
        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)
        # Clean column names
        df.columns = [col.strip() for col in df.columns]
        # Find the country column
        country_col = None
        for col in df.columns:
            if col.lower() == 'country':
                country_col = col
                break
        if country_col:
            countries = ['(All)'] + sorted([str(c) for c in df[country_col].dropna().unique()])
        else:
            countries = ['(All)']
    except Exception:
        countries = ['(All)']
    available_years = list(range(2006, 2025))
    default_year = 2022
    min_year = 2006
    max_year = 2024
    
    return html.Div([
        dcc.Download(id="download-carbon-intensity-csv"), # Added Download component
        html.Div([
            # Main visualization area (75% width)
            html.Div(style={'width': '75%', 'float': 'left', 'paddingRight': '20px'}, children=[ # This div wraps the title/button and chart
                html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}, children=[
                    html.Div("Upstream Crude Oil Production by Carbon Intensity", style={
                        "color": "#E75224", # Use title color from create_carbon_treemap_figure
                        "fontWeight": "bold",
                        "fontSize": "20px",
                        "fontFamily": "Arial, sans-serif",
                        "marginBottom": "5px"
                    }),
                    html.Button("Export to CSV", id='export-carbon-intensity-btn', n_clicks=0, style={'marginLeft': '12px', 'backgroundColor': 'white',
                        'color': '#2c3e50',
                        'border': '1px solid #dee2e6', 'padding': '6px 10px', 'borderRadius': '4px', 'cursor': 'pointer', 'fontSize': '12px'})
                ]),
                dcc.Graph(
                    id='crude-carbon-chart', 
                    style={'height': '700px'},
                    config={'displayModeBar': False}
                )
            ]), # Closing for the main visualization area div
            
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
                                'padding': '0px 5px',
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
                            placeholder="Select countries...",
                            optionHeight=36,
                            searchable=True,
                            clearable=True,
                            className='country-dropdown-with-checkbox'
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

        def _format_crude_list(rows):
            unique_entries = []
            for raw in rows:
                entry = str(raw).strip()
                if not entry or entry.lower() == "nan":
                    continue
                if entry not in unique_entries:
                    unique_entries.append(entry)
            return ", ".join(unique_entries)

        if "Year" in intensity_df.columns and not intensity_df["Year"].isna().all():
            try:
                year_value = int(float(intensity_df["Year"].dropna().iloc[0]))
            except (ValueError, TypeError, IndexError):
                year_value = selected_year
        else:
            year_value = selected_year

        grouped = (
            intensity_df.groupby("Country")
            .agg({
                "Production": "sum",
                "Crude list": _format_crude_list,
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
            label_style = "color:#333333;"
            value_style = "color:#000000;"

            def value_span(v):
                return f"<span style='{value_style}'><b>{v}</b></span>"

            year_display = year_value if year_value is not None else "N/A"
            production_display = f"{production_value:,.0f} ('000 b/d)"
            crudes_display = crudes_str if crudes_str else "N/A"

            hover_texts.append(
                f"<span style='{label_style}'>Carbon Intensity:</span> {value_span(intensity)}<br>"
                f"<span style='{label_style}'>Country:</span> {value_span(country_name)}<br>"
                f"<span style='{label_style}'>Year:</span> {value_span(year_display)}<br>"
                f"<span style='{label_style}'>Production:</span> {value_span(production_display)}<br>"
                f"<span style='{label_style}'>Crudes:</span> {value_span(crudes_display)}"
            )
            text_body = f"<b>{country_name}</b>"
            if crudes_str:
                text_body += "<br>" + "<br>".join([c.strip() for c in crudes_str.split(',')])
                text_body += f"<br>{intensity}"
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
                pathbar=dict(visible=True, side="top", thickness=20, edgeshape=">"),
                domain=position,
                root=dict(color="rgba(255,255,255,0)")
            )
        )

    fig.update_layout(
        # title=dict(
        #     text="Upstream Crude Oil Production by Carbon Intensity",
        #     x=0.5,
        #     xanchor="center",
        #     y=0.98,
        #     font=dict(size=20, color="#E75224", family="Arial, sans-serif")
        # ),
        height=700,
        margin=dict(l=10, r=10, t=10, b=10),
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

    try:
    
        query = """
        SELECT 
            B.ci_rank AS "Carbon Intensity",
            B.country,
            STRING_AGG(B.crudeoil, ', ') AS "crude list",
            EXTRACT(YEAR FROM B.YearReported) AS "Year of YearReported",
            SUM(B.ProductionDataValue) AS ProductionDataValue
        FROM
        (
            SELECT
                country_name AS country,
                crude_name AS CrudeOil,
                yr AS YearReported,
                production_kbpd AS ProductionDataValue,
                ci_rank
            FROM fact_wcod_crude A
            LEFT JOIN dim_country GRP 
                ON A.country_id = GRP.dim_country_id
        ) B
        WHERE B.ci_rank IS NOT NULL 
        GROUP BY 
            B.country,
            B.ci_rank,
            B.YearReported
        ORDER BY 
            B.country,
            B.YearReported;
        """
        
        print(f"DEBUG: Executing database query...")
        results = execute_query(query)
        
        if not results:
            print("ERROR: Query returned no results")
            return pd.DataFrame()
        
        # Convert query results to DataFrame (matches CSV structure)
        df = pd.DataFrame(results)
        
        # Clean column names
        df.columns = [col.strip() for col in df.columns]
        
        # Map to standard column names
        column_mapping = {}
        for col in df.columns:
            print(f"DEBUG: Column: {col}")
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
    
    # Callback for CSV export
    @dash_app.callback(
        Output('download-carbon-intensity-csv', 'data'),
        Input('export-carbon-intensity-btn', 'n_clicks'),
        State('carbon-year-display', 'children'),
        State('carbon-country-select', 'value'),
        State('carbon-crude-filter', 'value'),
        State('carbon-intensity-filter', 'value'),
        prevent_initial_call=True
    )
    def export_carbon_intensity_csv(n_clicks, year_str, country_filter, crude_filter, intensity_filter):
        if not n_clicks:
            raise dash.exceptions.PreventUpdate

        # Convert year string to int
        try:
            year = int(year_str) if year_str else 2022
        except:
            year = 2022

        # Handle None inputs for filters
        if country_filter is None:
            country_filter = ['(All)']
        if crude_filter is None:
            crude_filter = ''
        if intensity_filter is None or len(intensity_filter) == 0:
            intensity_filter = ['Very High', 'High', 'Medium', 'Low', 'Very Low']

        df = load_carbon_data()
        if df.empty:
            raise dash.exceptions.PreventUpdate

        # Apply filters to data (similar to create_carbon_treemap_figure)
        filtered_df = df.copy()
        if year is not None and "Year" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Year"] == year]
        if country_filter and isinstance(country_filter, list) and "(All)" not in country_filter:
            filtered_df = filtered_df[filtered_df["Country"].isin(country_filter)]
        if crude_filter:
            filtered_df = filtered_df[filtered_df["Crude list"].str.contains(crude_filter, case=False, na=False)]
        if intensity_filter:
            filtered_df = filtered_df[filtered_df["Carbon Intensity"].isin(intensity_filter)]

        if filtered_df.empty:
            raise dash.exceptions.PreventUpdate

        # Prepare data for CSV export - simplify crude list for CSV
        def _format_crude_list_for_csv(rows):
            unique_entries = []
            for raw in rows:
                entry = str(raw).strip()
                if not entry or entry.lower() == "nan":
                    continue
                if entry not in unique_entries:
                    unique_entries.append(entry)
            return ", ".join(unique_entries)

        # Group by Country, Carbon Intensity, and Year and aggregate
        grouped_for_csv = (
            filtered_df.groupby(["Country", "Carbon Intensity", "Year"])
            .agg({
                "Crude list": _format_crude_list_for_csv,
                "Production": "sum"
            })
            .reset_index()
        )

        # Rename columns for clarity in CSV
        grouped_for_csv = grouped_for_csv.rename(columns={
            "Country": "Country",
            "Carbon Intensity": "Carbon Intensity",
            "Year": "Year",
            "Crude list": "Crude List",
            "Production": "Production (000 b/d)"
        })

        return dcc.send_data_frame(grouped_for_csv.to_csv, filename=f"Crude_Carbon_Intensity_Data_{year}.csv")

    # Callback for proper (All) multi-select logic on the country dropdown
    @dash_app.callback(
        Output('carbon-country-select', 'value', allow_duplicate=True),
        Input('carbon-country-select', 'value'),
        State('carbon-country-select', 'options'),
        prevent_initial_call=True
    )
    def sync_all_checkbox(selected, all_options):
        if not all_options:
            return selected
        all_countries = [o['value'] for o in all_options if o['value'] != '(All)']
        selected = selected or []
        selected_set = set(selected)
        has_all = '(All)' in selected_set

        # If (All) is selected and it's the only selection, keep only (All)
        if has_all and len(selected_set) == 1:
            return ['(All)']

        # If all individual countries are selected but (All) is not, add (All)
        if set(all_countries) == selected_set and not has_all:
            return ['(All)']

        # If (All) is selected and some individual countries are deselected, remove (All)
        if has_all and not set(all_countries).issubset(selected_set):
            return [v for v in selected if v != '(All)']

        # If (All) is deselected and some individual countries are selected, keep them
        if not has_all and any(c in all_countries for c in selected_set):
            return [v for v in selected if v != '(All)']

        return selected

    # Main callback to update the chart
    @dash_app.callback(
        Output('crude-carbon-chart', 'figure'),
        [Input('carbon-year-display', 'children'),
         Input('carbon-country-select', 'value'),
         Input('carbon-crude-filter', 'value'),
         Input('carbon-intensity-filter', 'value'),
         Input('current-submenu', 'data')],
        prevent_initial_call=False
    )
    def update_crude_carbon(year_str, country_filter, crude_filter, intensity_filter, current_submenu):
        """Update crude carbon intensity treemap - only loads data when page is active"""
        # Check if page is active (for WCoD dashboard usage)
        # If used as standalone dashboard, current_submenu will be None, so always load
        if current_submenu is not None and current_submenu != 'crude-carbon':
            # Return empty figure if page is not active
            fig = go.Figure()
            fig.add_annotation(
                text="",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False
            )
            fig.update_layout(height=700, plot_bgcolor='white', paper_bgcolor='white')
            return fig
        
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
        
        # Load data only when page is active
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

def create_crude_carbon_dashboard(dash_app, server, url_base_pathname="/dash/crude-carbon/"):
    """Create the Crude Carbon Intensity dashboard"""
    # dash_app = dash.Dash(
    #     __name__,
    #     server=server,
    #     url_base_pathname=url_base_pathname,
    #     external_stylesheets=[
    #         'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
    #         'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
    #     ],
    #     suppress_callback_exceptions=True
    # )
    
    dash_app.layout = create_layout()
    register_callbacks(dash_app, server)