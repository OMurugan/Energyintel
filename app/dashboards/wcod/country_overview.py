"""
Country Overview View
Replicates Energy Intelligence WCoD Country Overview functionality
"""
from dash import dcc, html, Input, Output, State, callback, dash_table, dash
import plotly.graph_objects as go
import pandas as pd
import os

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'Table_Country_Profile_data.csv')

# Load data from CSV once during module import
try:
    raw_df = pd.read_csv(CSV_PATH)
    raw_df.columns = raw_df.columns.str.strip()

    pivot_df = raw_df.pivot_table(
        index=['country_long_name', 'profile_url'],
        columns=['Measure Names', 'Year of Year'],
        values='Measure Values',
        aggfunc='first'
    ).reset_index()

    pivot_df.columns = ['_'.join(map(str, col)).strip('_') for col in pivot_df.columns]

    column_mapping = {
        'country_long_name': 'Country',
        'profile_url': 'Profile_URL',
        "Exports ('000 b/d)_2023": 'Exports_2023',
        "Exports ('000 b/d)_2024": 'Exports_2024',
        "Production ('000 b/d)_2023": 'Production_2023',
        "Production ('000 b/d)_2024": 'Production_2024',
        'R/P Ratio (Year)_2023': 'R_P_Ratio_2023',
        'R/P Ratio (Year)_2024': 'R_P_Ratio_2024',
        'Reserves (Billion bbl)_2023': 'Reserves_2023',
        'Reserves (Billion bbl)_2024': 'Reserves_2024'
    }
    pivot_df = pivot_df.rename(columns=column_mapping)

    numeric_columns = [
        'Exports_2023', 'Exports_2024',
        'Production_2023', 'Production_2024',
        'R_P_Ratio_2023', 'R_P_Ratio_2024',
        'Reserves_2023', 'Reserves_2024'
    ]

    for col in numeric_columns:
        pivot_df[col] = pd.to_numeric(pivot_df[col], errors='coerce').fillna(0)

    required_cols = ['Country', 'Exports_2024', 'Production_2024']
    bar_chart_data = pivot_df[required_cols + ['Profile_URL']].sort_values('Exports_2024', ascending=False).head(9)
    country_url_map = {
        row['Country']: row.get('Profile_URL', '')
        for _, row in pivot_df.iterrows() if row.get('Profile_URL')
    }
except Exception:
    # If CSV is missing or unreadable, fallback to empty structures
    pivot_df = pd.DataFrame(columns=[
        'Country', 'Profile_URL', 'Exports_2023', 'Exports_2024',
        'Production_2023', 'Production_2024',
        'R_P_Ratio_2023', 'R_P_Ratio_2024',
        'Reserves_2023', 'Reserves_2024'
    ])
    bar_chart_data = pd.DataFrame(columns=['Country', 'Exports_2024', 'Production_2024', 'Profile_URL'])
    country_url_map = {}

# Time dimension column definitions
TIME_DIMENSION_COLUMNS = [
    {"name": ["", "Year of Year"], "id": "Year_of_Year", "type": "numeric", "format": {"specifier": ",.0f"}},
    {"name": ["", "Quarter of Year"], "id": "Quarter_of_Year", "type": "numeric", "format": {"specifier": ",.0f"}},
    {"name": ["", "Month of Year"], "id": "Month_of_Year", "type": "text"},
    {"name": ["", "Day of Year"], "id": "Day_of_Year", "type": "numeric", "format": {"specifier": ",.0f"}},
]

# Base data columns
DATA_COLUMNS = [
    {"name": ["Exports", "2024"], "id": "Exports_2024", "type": "numeric", "format": {"specifier": ",.0f"}},
    {"name": ["Exports", "2023"], "id": "Exports_2023", "type": "numeric", "format": {"specifier": ",.0f"}},
    {"name": ["Production", "2024"], "id": "Production_2024", "type": "numeric", "format": {"specifier": ",.0f"}},
    {"name": ["Production", "2023"], "id": "Production_2023", "type": "numeric", "format": {"specifier": ",.0f"}},
    {"name": ["R/P Ratio", "2024"], "id": "R_P_Ratio_2024", "type": "numeric", "format": {"specifier": ",.1f"}},
    {"name": ["R/P Ratio", "2023"], "id": "R_P_Ratio_2023", "type": "numeric", "format": {"specifier": ",.1f"}},
    {"name": ["Reserves", "2024"], "id": "Reserves_2024", "type": "numeric", "format": {"specifier": ",.1f"}},
    {"name": ["Reserves", "2023"], "id": "Reserves_2023", "type": "numeric", "format": {"specifier": ",.1f"}}
]

# Data table columns (without time dimensions)
DATA_TABLE_COLUMNS = [
    {"name": ["", "Country"], "id": "Country", "type": "text", "presentation": "markdown"},
] + DATA_COLUMNS


def create_layout():
    """Create the Country Overview layout"""
    return html.Div([
        # Store for selected country
        dcc.Store(id='selected-country-store', data=None),
        # Store for profile URL to open
        dcc.Store(id='profile-url-store', data=None),
        # Store for click counter (ensures callback fires on every click)
        dcc.Store(id='click-counter-store', data=0),
        # Store for time dimension visibility (Year, Quarter, Month, Day)
        dcc.Store(id='time-dimension-visibility', data={'Year': True, 'Quarter': False, 'Month': False, 'Day': False}),
        # Hidden div to trigger URL opening via clientside callback
        html.Div(id='open-url-trigger', children=0, style={'display': 'none'}),

        html.Div([
            html.Span(
                "Click on the Country's name to view the Profile",
                style={'textAlign': 'left', 'marginBottom': '20px', 'fontSize': '13px', 'color': '#2c3e50', 'fontWeight': 'bold', 'fontStyle': 'italic'}
            )
        ]),

        # Ranking Chart Card
        # html.Div([
            html.Div([
                # html.Div([                   
                    html.H4(
                        "Ranking the world's crude oil exporters",
                        style={
                            'textAlign': 'center',
                            'marginTop': '30px',
                            'marginBottom': '20px',
                            'color': '#1b365d',
                            'fontWeight': 'bold',
                            'fontSize': '21px',
                            'fontFamily': 'Arial, sans-serif',
                            'lineHeight': '23px'
                        }
                    ),
                    html.Button(
                        '−',
                        id='chart-collapse-button',
                        n_clicks=0,
                        style={
                            'float': 'right',
                            'fontSize': '20px',
                            'fontWeight': 'bold',
                            'color': '#2c3e50',
                            'textDecoration': 'none',
                            'padding': '0 10px',
                            'border': 'none',
                            'background': 'transparent',
                            'cursor': 'pointer'
                        }
                    )
                # ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'width': '100%', 'padding': '15px', 'background': '#f8f9fa', 'borderBottom': '1px solid #dee2e6'})
            ]),
            html.Div([
                # Chart with embedded time dimension expand/collapse controls
                html.Div([
                    # Time dimension controls inside chart area - first row with icons at top right
                    html.Div([
                        html.Div([
                            html.Span("Year of Year", style={'fontSize': '12px', 'color': '#2c3e50', 'flex': '1'}),
                            html.Button(
                                '−',
                                id='toggle-year-btn',
                                n_clicks=0,
                                style={
                                    'width': '20px',
                                    'height': '20px',
                                    'padding': '0',
                                    'border': '1px solid #dee2e6',
                                    'backgroundColor': '#f8f9fa',
                                    'color': '#2c3e50',
                                    'borderRadius': '3px',
                                    'cursor': 'pointer',
                                    'fontSize': '14px',
                                    'fontWeight': 'bold',
                                    'lineHeight': '1',
                                    'display': 'flex',
                                    'alignItems': 'center',
                                    'justifyContent': 'center',
                                    'marginLeft': '8px',
                                    'flexShrink': '0'
                                }
                            )
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px', 'width': '120px'}),
                        html.Div([
                            html.Span("Quarter of Year", style={'fontSize': '12px', 'color': '#2c3e50', 'flex': '1'}),
                            html.Button(
                                '+',
                                id='toggle-quarter-btn',
                                n_clicks=0,
                                style={
                                    'width': '20px',
                                    'height': '20px',
                                    'padding': '0',
                                    'border': '1px solid #dee2e6',
                                    'backgroundColor': '#f8f9fa',
                                    'color': '#2c3e50',
                                    'borderRadius': '3px',
                                    'cursor': 'pointer',
                                    'fontSize': '14px',
                                    'fontWeight': 'bold',
                                    'lineHeight': '1',
                                    'display': 'flex',
                                    'alignItems': 'center',
                                    'justifyContent': 'center',
                                    'marginLeft': '8px',
                                    'flexShrink': '0'
                                }
                            )
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px', 'width': '130px'}),
                        html.Div([
                            html.Span("Month of Year", style={'fontSize': '12px', 'color': '#2c3e50', 'flex': '1'}),
                            html.Button(
                                '+',
                                id='toggle-month-btn',
                                n_clicks=0,
                                style={
                                    'width': '20px',
                                    'height': '20px',
                                    'padding': '0',
                                    'border': '1px solid #dee2e6',
                                    'backgroundColor': '#f8f9fa',
                                    'color': '#2c3e50',
                                    'borderRadius': '3px',
                                    'cursor': 'pointer',
                                    'fontSize': '14px',
                                    'fontWeight': 'bold',
                                    'lineHeight': '1',
                                    'display': 'flex',
                                    'alignItems': 'center',
                                    'justifyContent': 'center',
                                    'marginLeft': '8px',
                                    'flexShrink': '0'
                                }
                            )
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px', 'width': '130px'}),
                        html.Div([
                            html.Span("Day of Year", style={'fontSize': '12px', 'color': '#2c3e50', 'flex': '1'}),
                            html.Button(
                                '+',
                                id='toggle-day-btn',
                                n_clicks=0,
                                style={
                                    'width': '20px',
                                    'height': '20px',
                                    'padding': '0',
                                    'border': '1px solid #dee2e6',
                                    'backgroundColor': '#f8f9fa',
                                    'color': '#2c3e50',
                                    'borderRadius': '3px',
                                    'cursor': 'pointer',
                                    'fontSize': '14px',
                                    'fontWeight': 'bold',
                                    'lineHeight': '1',
                                    'display': 'flex',
                                    'alignItems': 'center',
                                    'justifyContent': 'center',
                                    'marginLeft': '8px',
                                    'flexShrink': '0'
                                }
                            )
                        ], style={'display': 'flex', 'alignItems': 'center', 'width': '120px'})
                    ], style={'padding': '10px 20px', 'borderBottom': '1px solid #dee2e6', 'background': '#f8f9fa', 'display': 'flex', 'justifyContent': 'flex-start', 'alignItems': 'center'}),
                    dcc.Graph(
                        id='exports-ranking-chart',
                        figure=create_ranking_chart(),
                        clickData=None,
                        style={'height': '600px'}
                    )
                ], id='chart-collapse-content', style={'padding': '0', 'background': 'white', 'border': '1px solid #dee2e6', 'borderRadius': '4px', 'overflow': 'hidden'}),
            ]),
        # ], style={'background': 'white', 'border': '1px solid #dee2e6', 'borderRadius': '4px', 'marginBottom': '30px', 'overflow': 'hidden'}),

        # Data Table Section
        html.Div([
            html.H4(
                "Leading Oil Exporting Countries",
                style={
                    'textAlign': 'center',
                    'marginTop': '30px',
                    'marginBottom': '20px',
                    'color': '#1b365d',
                    'fontWeight': 'bold',
                    'fontSize': '21px',
                    'fontFamily': 'Arial, sans-serif',
                    'lineHeight': '23px'
                }
            ),
            dash_table.DataTable(
                id='oil-data-table',
                data=[],
                columns=DATA_TABLE_COLUMNS,
                page_action='none',
                style_cell={
                    'textAlign': 'center',
                    'padding': '8px',
                    'fontSize': '12px',
                    'fontFamily': 'Arial, sans-serif',
                    'border': '1px solid #dee2e6',
                    'color': '#2c3e50'
                },
                style_header={
                    'backgroundColor': '#f8f9fa',
                    'fontWeight': 'bold',
                    'border': '1px solid #dee2e6',
                    'textAlign': 'center',
                    'fontSize': '12px',
                    'fontFamily': 'Arial, sans-serif',
                    'color': '#2c3e50'
                },
                style_data={
                    'border': '1px solid #dee2e6',
                    'backgroundColor': 'white',
                    'color': '#2c3e50'
                },
                style_cell_conditional=[
                    {
                        'if': {'column_id': 'Country'},
                        'textAlign': 'left',
                        'fontWeight': 'bold',
                        'minWidth': '150px',
                        'color': '#1b365d'
                    }
                ],
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    },
                    {
                        'if': {'filter_query': '{Country} contains ""'},
                        'backgroundColor': 'white'
                    }
                ],
                merge_duplicate_headers=True,
                sort_action='native',
                filter_action='none',
                style_table={
                    'overflowX': 'auto',
                    'border': '1px solid #dee2e6',
                    'borderRadius': '4px',
                    'backgroundColor': 'white'
                },
                cell_selectable=True
            )
        ]),

        # Footer notes
        html.Div([
            html.P(
                "Countries: Select jurisdictions are included under countries for data presentation purposes.",
                style={'fontSize': '10px', 'fontStyle': 'italic', 'marginTop': '20px', 'color': '#6c757d'}
            ),
            # html.P(
            #     "Source: Energy Intelligence | COPYRIGHT © 2001-2025 ENERGY INTELLIGENCE GROUP, INC.",
            #     style={'fontSize': '10px', 'fontStyle': 'italic', 'marginTop': '10px', 'color': '#6c757d'}
            # )
        ])
    ], className='tab-content')


def create_ranking_chart(selected_country=None, time_visibility=None):
    """Create horizontal bar chart ranking crude oil exporters"""
    if bar_chart_data.empty:
        return go.Figure()

    sorted_df = bar_chart_data[['Country', 'Exports_2024', 'Production_2024']].sort_values('Exports_2024', ascending=True).copy()
    if sorted_df.empty:
        return go.Figure()

    fig = go.Figure()
    country_list_original = sorted_df['Country'].astype(str).str.strip().tolist()
    
    # Build y-axis labels with time dimensions if visible
    country_list = country_list_original.copy()
    if time_visibility:
        year_value = 2024
        quarter_value = 4
        month_value = "December"
        day_value = 31
        
        y_labels = []
        for country in country_list_original:
            label_parts = [country]
            if time_visibility.get('Year', True):
                label_parts.append(str(year_value))
            if time_visibility.get('Quarter', False):
                label_parts.append(f"Q{quarter_value}")
            if time_visibility.get('Month', False):
                label_parts.append(month_value)
            if time_visibility.get('Day', False):
                label_parts.append(f"{day_value}")
            y_labels.append("   ".join(label_parts))
        
        # Use enhanced labels if any time dimension is visible
        if any([time_visibility.get('Year', True), time_visibility.get('Quarter', False), 
                time_visibility.get('Month', False), time_visibility.get('Day', False)]):
            country_list = y_labels

    # For color matching, use original country names
    export_colors = ['#0075A8' if country == selected_country else 'rgb(0, 117, 168)' for country in country_list_original]
    production_colors = ['#595959' if country == selected_country else 'rgb(89, 89, 89)' for country in country_list_original]

    if 'Production_2024' in sorted_df.columns:
        fig.add_trace(go.Bar(
            y=country_list,
            x=sorted_df['Production_2024'].tolist(),
            orientation='h',
            marker=dict(
                color=production_colors,
                line=dict(color=production_colors, width=1.5 if selected_country else 0.5)
            ),
            text=sorted_df['Production_2024'].apply(lambda x: f'{x:,.0f}' if pd.notna(x) else '').tolist(),
            textposition='outside',
            name='Production',
            hovertemplate='<b>%{y}</b><br>Production: %{x:,.0f} (\'000 b/d)<br>Year: 2024<extra></extra>',
            showlegend=True,
            legendgroup='production',
            offsetgroup='production',
            width=0.4
        ))

    fig.add_trace(go.Bar(
        y=country_list,
        x=sorted_df['Exports_2024'].tolist(),
        orientation='h',
        marker=dict(
            color=export_colors,
            line=dict(color=export_colors, width=1.5 if selected_country else 0.5)
        ),
        text=sorted_df['Exports_2024'].apply(lambda x: f'{x:,.0f}' if pd.notna(x) else '').tolist(),
        textposition='outside',
        name='Exports',
        hovertemplate='<b>%{y}</b><br>Exports: %{x:,.0f} (\'000 b/d)<br>Year: 2024<extra></extra>',
        showlegend=True,
        legendgroup='exports',
        offsetgroup='exports',
        width=0.4
    ))

    max_export = sorted_df['Exports_2024'].max() if len(sorted_df) else 0
    max_production = sorted_df['Production_2024'].max() if 'Production_2024' in sorted_df.columns and len(sorted_df) else 0
    max_val = max(max_export, max_production) if max(max_export, max_production) > 0 else 1000

    fig.update_layout(
        # title={
        #     'text': "Ranking the world's crude oil exporters",
        #     'x': 0.5,
        #     'xanchor': 'center',
        #     'font': {
        #         'size': 21,
        #         'family': 'Arial, sans-serif',
        #         'color': '#fe5000'
        #     }
        # },
        xaxis_title="('000 b/d)",
        yaxis_title="",
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            font=dict(size=12, family='Arial, sans-serif', color='#2c3e50'),
            bgcolor='rgba(255,255,255,0.8)',
            traceorder='normal',
            itemsizing='constant',
            bordercolor='#dee2e6',
            borderwidth=1
        ),
        height=600,
        margin=dict(l=150, r=120, t=90, b=40),
        xaxis=dict(
            range=[0, max_val * 1.2] if max_val > 0 else [0, 1000],
            showgrid=True,
            gridcolor='#E0E0E0',
            gridwidth=1,
            tickformat=',',
            zeroline=False,
            showline=True,
            linecolor='#000000',
            linewidth=1,
            title_font=dict(size=12, family='Arial, sans-serif', color='#2c3e50'),
            tickfont=dict(size=11, family='Arial, sans-serif', color='#2c3e50')
        ),
        yaxis=dict(
            categoryorder='array',
            categoryarray=country_list,
            tickfont=dict(size=11, family='Arial Black, Arial, sans-serif', color='#1b365d'),
            showline=True,
            linecolor='#000000',
            linewidth=1,
            side='left',
            type='category',
            tickmode='array',
            tickvals=country_list,
            ticktext=country_list
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='closest',
        barmode='group',
        bargap=0.1,
        bargroupgap=0.8
    )

    # Add horizontal lines after each country
    shapes = []
    num_countries = len(country_list)
    for i in range(num_countries - 1):
        # Calculate y position between countries (category positions are 0-indexed)
        y_pos = i + 0.5
        shapes.append({
            'type': 'line',
            'xref': 'x',
            'yref': 'y',
            'x0': 0,
            'y0': y_pos,
            'x1': max_val * 1.2 if max_val > 0 else 1000,
            'y1': y_pos,
            'line': {
                'color': '#E0E0E0',
                'width': 1,
                'dash': 'solid'
            },
            'layer': 'below'
        })
    
    if shapes:
        fig.update_layout(shapes=shapes)

    fig.update_traces(selector=dict(name='Exports'), legendrank=1)
    fig.update_traces(selector=dict(name='Production'), legendrank=2)

    return fig


def register_callbacks(dash_app, server):
    """Register all callbacks for Country Overview"""

    @callback(
        Output('exports-ranking-chart', 'figure'),
        [Input('current-submenu', 'data'),
         Input('selected-country-store', 'data'),
         Input('time-dimension-visibility', 'data')],
        prevent_initial_call=False
    )
    def update_ranking_chart(submenu, selected_country, time_visibility):
        """Update ranking chart with highlighting"""
        if submenu != 'country-overview':
            return go.Figure()
        return create_ranking_chart(selected_country=selected_country, time_visibility=time_visibility)

    @callback(
        [Output('oil-data-table', 'data'),
         Output('oil-data-table', 'columns')],
        Input('current-submenu', 'data'),
        prevent_initial_call=False
    )
    def update_oil_data_table(submenu):
        """Update oil data table with country statistics"""
        if submenu != 'country-overview':
            return [], []

        if pivot_df.empty:
            return [], DATA_TABLE_COLUMNS

        table_data = []
        for _, row in pivot_df.sort_values('Exports_2024', ascending=False).iterrows():
            country_name = row.get('Country', '')
            profile_url = row.get('Profile_URL', '') or country_url_map.get(country_name, '')
            table_data.append({
                'Country': f"[{country_name}]({profile_url})" if profile_url else country_name,
                'Country_Original': country_name,
                'Profile_URL': profile_url,
                'Exports_2024': row.get('Exports_2024', 0),
                'Exports_2023': row.get('Exports_2023', 0),
                'Production_2024': row.get('Production_2024', 0),
                'Production_2023': row.get('Production_2023', 0),
                'R_P_Ratio_2024': row.get('R_P_Ratio_2024', 0),
                'R_P_Ratio_2023': row.get('R_P_Ratio_2023', 0),
                'Reserves_2024': row.get('Reserves_2024', 0),
                'Reserves_2023': row.get('Reserves_2023', 0)
            })

        return table_data, DATA_TABLE_COLUMNS

    @callback(
        [Output('selected-country-store', 'data'),
         Output('profile-url-store', 'data'),
         Output('click-counter-store', 'data')],
        Input('exports-ranking-chart', 'clickData'),
        State('click-counter-store', 'data'),
        prevent_initial_call=True
    )
    def update_selected_country_from_chart(clickData, click_counter):
        if clickData and 'points' in clickData and len(clickData['points']) > 0:
            country_name = clickData['points'][0]['y']
            profile_url = country_url_map.get(country_name)
            new_counter = (click_counter or 0) + 1
            return country_name, profile_url, new_counter
        return dash.no_update, dash.no_update, click_counter

    @callback(
        [Output('selected-country-store', 'data', allow_duplicate=True),
         Output('profile-url-store', 'data', allow_duplicate=True),
         Output('click-counter-store', 'data', allow_duplicate=True)],
        [Input('oil-data-table', 'active_cell'),
         Input('oil-data-table', 'selected_rows')],
        [State('oil-data-table', 'data'),
         State('click-counter-store', 'data')],
        prevent_initial_call=True
    )
    def update_selected_country_from_table(active_cell, selected_rows, table_data, click_counter):
        if not table_data:
            return dash.no_update, dash.no_update, click_counter

        row_idx = None
        if active_cell and isinstance(active_cell, dict) and active_cell.get('row') is not None:
            row_idx = active_cell['row']
        elif selected_rows and isinstance(selected_rows, list) and len(selected_rows) > 0:
            row_idx = selected_rows[0]

        if row_idx is None or row_idx >= len(table_data):
            return dash.no_update, dash.no_update, click_counter

        row_data = table_data[row_idx]
        country = row_data.get('Country_Original', row_data.get('Country', ''))

        if isinstance(country, str) and country.startswith('[') and '](' in country:
            country = country.split('](')[0][1:]

        profile_url = row_data.get('Profile_URL') or country_url_map.get(country)

        if country:
            new_counter = (click_counter or 0) + 1
            return country, profile_url, new_counter

        return dash.no_update, dash.no_update, click_counter

    @callback(
        Output('exports-ranking-chart', 'figure', allow_duplicate=True),
        Input('selected-country-store', 'data'),
        State('current-submenu', 'data'),
        prevent_initial_call=True
    )
    def update_chart_highlight(selected_country, submenu):
        """Update chart highlighting based on selected country"""
        if submenu != 'country-overview':
            return dash.no_update
        return create_ranking_chart(selected_country=selected_country)

    @callback(
        Output('oil-data-table', 'style_data_conditional', allow_duplicate=True),
        Input('selected-country-store', 'data'),
        State('oil-data-table', 'data'),
        prevent_initial_call=True
    )
    def update_table_highlight(selected_country, table_data):
        """Update table row highlighting based on selected country"""
        style_conditions = [
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }
        ]

        if selected_country and table_data:
            for idx, row in enumerate(table_data):
                country_original = row.get('Country_Original', '')
                if country_original == selected_country:
                    style_conditions.append({
                        'if': {'row_index': idx},
                        'backgroundColor': '#FFF8DC',  # Light yellow highlight
                        'fontWeight': 'bold'
                    })
                    break

        return style_conditions

    @callback(
        [Output('chart-collapse-content', 'style'),
         Output('chart-collapse-button', 'children')],
        Input('chart-collapse-button', 'n_clicks'),
        State('chart-collapse-content', 'style'),
        prevent_initial_call=True
    )
    def toggle_chart_collapse(n_clicks, current_style):
        """Toggle chart collapse/expand"""
        if n_clicks:
            is_hidden = current_style.get('display') == 'none'
            new_style = {**current_style, 'display': 'none' if not is_hidden else 'block'}
            button_text = '+' if is_hidden else '−'
            return new_style, button_text
        return current_style, '−'

    # Initialize button icons and styles based on visibility state
    @callback(
        [Output('toggle-year-btn', 'children'),
         Output('toggle-year-btn', 'style'),
         Output('toggle-quarter-btn', 'children'),
         Output('toggle-quarter-btn', 'style'),
         Output('toggle-month-btn', 'children'),
         Output('toggle-month-btn', 'style'),
         Output('toggle-day-btn', 'children'),
         Output('toggle-day-btn', 'style')],
        Input('time-dimension-visibility', 'data'),
        prevent_initial_call=False
    )
    def update_button_icons(visibility):
        """Update button icons (+/-) and styles based on visibility state"""
        base_style = {
            'width': '20px',
            'height': '20px',
            'padding': '0',
            'border': '1px solid #dee2e6',
            'borderRadius': '3px',
            'cursor': 'pointer',
            'fontSize': '14px',
            'fontWeight': 'bold',
            'lineHeight': '1',
            'display': 'inline-flex',
            'alignItems': 'center',
            'justifyContent': 'center'
        }
        
        year_expanded = visibility.get('Year', True)
        quarter_expanded = visibility.get('Quarter', False)
        month_expanded = visibility.get('Month', False)
        day_expanded = visibility.get('Day', False)
        
        year_style = {**base_style,
            'backgroundColor': '#e7f3ff' if year_expanded else '#f8f9fa',
            'color': '#007bff' if year_expanded else '#2c3e50',
            'borderColor': '#007bff' if year_expanded else '#dee2e6'
        }
        quarter_style = {**base_style,
            'backgroundColor': '#e7f3ff' if quarter_expanded else '#f8f9fa',
            'color': '#007bff' if quarter_expanded else '#2c3e50',
            'borderColor': '#007bff' if quarter_expanded else '#dee2e6'
        }
        month_style = {**base_style,
            'backgroundColor': '#e7f3ff' if month_expanded else '#f8f9fa',
            'color': '#007bff' if month_expanded else '#2c3e50',
            'borderColor': '#007bff' if month_expanded else '#dee2e6'
        }
        day_style = {**base_style,
            'backgroundColor': '#e7f3ff' if day_expanded else '#f8f9fa',
            'color': '#007bff' if day_expanded else '#2c3e50',
            'borderColor': '#007bff' if day_expanded else '#dee2e6'
        }
        
        return (
            '−' if year_expanded else '+', year_style,
            '−' if quarter_expanded else '+', quarter_style,
            '−' if month_expanded else '+', month_style,
            '−' if day_expanded else '+', day_style
        )

    # Callbacks for time dimension toggles
    @callback(
        [Output('time-dimension-visibility', 'data', allow_duplicate=True),
         Output('toggle-year-btn', 'children', allow_duplicate=True),
         Output('toggle-year-btn', 'style', allow_duplicate=True)],
        Input('toggle-year-btn', 'n_clicks'),
        State('time-dimension-visibility', 'data'),
        prevent_initial_call=True
    )
    def toggle_year(n_clicks, visibility):
        """Toggle Year column visibility"""
        if n_clicks:
            new_visibility = visibility.copy()
            new_visibility['Year'] = not new_visibility.get('Year', True)
            is_expanded = new_visibility['Year']
            button_style = {
                'width': '20px',
                'height': '20px',
                'padding': '0',
                'border': '1px solid #007bff' if is_expanded else '#dee2e6',
                'backgroundColor': '#e7f3ff' if is_expanded else '#f8f9fa',
                'color': '#007bff' if is_expanded else '#2c3e50',
                'borderRadius': '3px',
                'cursor': 'pointer',
                'fontSize': '14px',
                'fontWeight': 'bold',
                'lineHeight': '1',
                'display': 'inline-flex',
                'alignItems': 'center',
                'justifyContent': 'center'
            }
            return new_visibility, '−' if is_expanded else '+', button_style
        return visibility, dash.no_update, dash.no_update

    @callback(
        [Output('time-dimension-visibility', 'data', allow_duplicate=True),
         Output('toggle-quarter-btn', 'children', allow_duplicate=True),
         Output('toggle-quarter-btn', 'style', allow_duplicate=True)],
        Input('toggle-quarter-btn', 'n_clicks'),
        State('time-dimension-visibility', 'data'),
        prevent_initial_call=True
    )
    def toggle_quarter(n_clicks, visibility):
        """Toggle Quarter column visibility"""
        if n_clicks:
            new_visibility = visibility.copy()
            new_visibility['Quarter'] = not new_visibility.get('Quarter', False)
            is_expanded = new_visibility['Quarter']
            button_style = {
                'width': '20px',
                'height': '20px',
                'padding': '0',
                'border': '1px solid #007bff' if is_expanded else '#dee2e6',
                'backgroundColor': '#e7f3ff' if is_expanded else '#f8f9fa',
                'color': '#007bff' if is_expanded else '#2c3e50',
                'borderRadius': '3px',
                'cursor': 'pointer',
                'fontSize': '14px',
                'fontWeight': 'bold',
                'lineHeight': '1',
                'display': 'inline-flex',
                'alignItems': 'center',
                'justifyContent': 'center'
            }
            return new_visibility, '−' if is_expanded else '+', button_style
        return visibility, dash.no_update, dash.no_update

    @callback(
        [Output('time-dimension-visibility', 'data', allow_duplicate=True),
         Output('toggle-month-btn', 'children', allow_duplicate=True),
         Output('toggle-month-btn', 'style', allow_duplicate=True)],
        Input('toggle-month-btn', 'n_clicks'),
        State('time-dimension-visibility', 'data'),
        prevent_initial_call=True
    )
    def toggle_month(n_clicks, visibility):
        """Toggle Month column visibility"""
        if n_clicks:
            new_visibility = visibility.copy()
            new_visibility['Month'] = not new_visibility.get('Month', False)
            is_expanded = new_visibility['Month']
            button_style = {
                'width': '20px',
                'height': '20px',
                'padding': '0',
                'border': '1px solid #007bff' if is_expanded else '#dee2e6',
                'backgroundColor': '#e7f3ff' if is_expanded else '#f8f9fa',
                'color': '#007bff' if is_expanded else '#2c3e50',
                'borderRadius': '3px',
                'cursor': 'pointer',
                'fontSize': '14px',
                'fontWeight': 'bold',
                'lineHeight': '1',
                'display': 'inline-flex',
                'alignItems': 'center',
                'justifyContent': 'center'
            }
            return new_visibility, '−' if is_expanded else '+', button_style
        return visibility, dash.no_update, dash.no_update

    @callback(
        [Output('time-dimension-visibility', 'data', allow_duplicate=True),
         Output('toggle-day-btn', 'children', allow_duplicate=True),
         Output('toggle-day-btn', 'style', allow_duplicate=True)],
        Input('toggle-day-btn', 'n_clicks'),
        State('time-dimension-visibility', 'data'),
        prevent_initial_call=True
    )
    def toggle_day(n_clicks, visibility):
        """Toggle Day column visibility"""
        if n_clicks:
            new_visibility = visibility.copy()
            new_visibility['Day'] = not new_visibility.get('Day', False)
            is_expanded = new_visibility['Day']
            button_style = {
                'width': '20px',
                'height': '20px',
                'padding': '0',
                'border': '1px solid #007bff' if is_expanded else '#dee2e6',
                'backgroundColor': '#e7f3ff' if is_expanded else '#f8f9fa',
                'color': '#007bff' if is_expanded else '#2c3e50',
                'borderRadius': '3px',
                'cursor': 'pointer',
                'fontSize': '14px',
                'fontWeight': 'bold',
                'lineHeight': '1',
                'display': 'inline-flex',
                'alignItems': 'center',
                'justifyContent': 'center'
            }
            return new_visibility, '−' if is_expanded else '+', button_style
        return visibility, dash.no_update, dash.no_update

    # Client-side callback to open profile URL in new tab
    dash_app.clientside_callback(
        """
        function(url, click_counter) {
            if (url && url !== '' && url !== null && url !== undefined && url !== 'None' && url !== 'null' && click_counter > 0) {
                // Always open in new tab (target=_blank)
                setTimeout(function() {
                    window.open(url, '_blank', 'noopener,noreferrer');
                }, 100);
                return click_counter; // Return counter to track changes
            }
            return click_counter || 0;
        }
        """,
        Output('open-url-trigger', 'children'),
        [Input('profile-url-store', 'data'),
         Input('click-counter-store', 'data')]
    )

